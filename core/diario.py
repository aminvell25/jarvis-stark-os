"""Il diario: che cosa e' stato detto, e che cosa e' stato fatto — due flussi.

## Perche' esiste

Il 26 agosto 2026 il blocco A dell'attraversamento vocale ha prodotto sei
risvegli per cinque comandi, e uno dei cinque — «apri il pannello telemetria» —
non e' arrivato affatto. **Non ho potuto spiegare perche'**: il journal registra
`traversata esito=t1`, ma non registra **che cosa lo STT ha capito**, e senza
quella riga non si distingue un comando trascritto male da una regola T0 che non
ha morso.

Il testo c'era, in `sessions/<giorno>.jsonl`, e ci sono arrivato per caso. Ma
quel file e' la **cronologia grezza** che §5.5 usa per il consolidamento
notturno: ha un solo scopo, e chiedergli anche di essere lo strumento di
diagnosi vorrebbe dire due letture della stessa domanda.

## I due flussi, e perche' sono due

    dialogo   cio' che e' stato DETTO — da chi, con che parole
    azione    cio' che il sistema ha DECISO e FATTO — e con che esito

Sono domande diverse. «Che cosa mi ha risposto» si guarda in ordine di
conversazione; «perche' ha aperto quel pannello» si guarda in ordine di causa.
Mescolarli produce un registro in cui nessuna delle due si legge.

Ogni evento va **su disco e sul socket**: su disco perche' un numero che vive
solo in un terminale non si confronta col mese prossimo, sul socket perche' §3.2
dice che il core e' la sorgente di verita' della UI, e la scrivania deve poterlo
mostrare senza chiederlo.

⚠️ **Il diario NON e' la memoria.** `sessions/` alimenta il consolidamento di
§5.5 e vive quanto la memoria; il diario e' uno strumento di osservazione e si
puo' cancellare senza perdere nulla di cio' che JARVIS sa.
"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

#: I due flussi. Una allowlist, non una convenzione: un flusso scritto male
#: renderebbe illeggibile il registro senza che nessuno se ne accorga.
FLUSSI = ("dialogo", "azione")

#: Il topic su cui la scrivania ascolta.
TOPIC = "agent.diario"


class Diario:
    """Append-only, un file al giorno, due flussi.

    `pubblica` arriva per funzione: il diario non deve sapere che cosa sia un
    socket, e i test lo misurano senza aprirne uno.
    """

    def __init__(self, radice: Path,
                 pubblica: Callable[[dict], Awaitable[None]] | None = None) -> None:
        self.radice = Path(radice)
        self.radice.mkdir(parents=True, exist_ok=True)
        self._pubblica = pubblica

    def _file(self, quando: float) -> Path:
        return self.radice / f"{time.strftime('%Y-%m-%d', time.localtime(quando))}.jsonl"

    def scrivi(self, flusso: str, traccia: str | None, **campi: Any) -> dict:
        """Una riga. Non solleva: siamo sul percorso della voce, e un disco
        pieno non deve zittire JARVIS.

        ⚠️ **`traccia` e' POSIZIONALE e obbligatoria** (ADR-011), e sui cinque
        chiamanti — tutti in `core/engine.py` — costa cinque parole. E' l'unico
        posto del contratto in cui l'assenza puo' essere un errore di tipo:
        `registry.invoke` la prende opzionale, perche' li' obbligarla
        romperebbe una sessantina di chiamate nei test senza aggiungere una
        prova, e l'imposizione la fa una guardia AST.

        `traccia=None` si **scrive**, e va scritto solo dove c'e' una ragione
        firmata in `tests/test_la_traccia_non_si_perde.py`: una riga che nasce
        senza origine e' un fatto da dichiarare, non una dimenticanza da
        lasciar passare.
        """
        if flusso not in FLUSSI:
            # Fail-closed sul NOME, come il registry sui tool: un flusso
            # inventato non entra nel registro, e lo si dice.
            log.error("diario_flusso_ignoto", flusso=flusso, ammessi=FLUSSI)
            return {}
        ora = time.time()
        # ⚠️ **La chiave c'e' SEMPRE, anche quando vale `None`**, ed e' cio' che
        # tiene additivo il campo. Tre stati, non due:
        #
        #     chiave assente   riga scritta PRIMA di ADR-011
        #     "traccia": null  il produttore ha dichiarato di non averne una
        #     "traccia": "..." l'origine si ricongiunge
        #
        # Omettendola quando e' nulla, «vecchia» e «dichiarata senza» si
        # confonderebbero, e `scripts/orfani.py --diario` non potrebbe piu'
        # distinguere una riga d'archivio da un produttore che ha smesso di
        # passarla.
        # La stringa vuota e' `None`: `Turno.traccia_id` vale `""` per gli
        # annunci, e una riga con `"traccia": ""` sarebbe un terzo stato che
        # non significa niente — ne' «vecchia», ne' «dichiarata senza», ne' un
        # id. Si normalizza qui, in un posto solo, invece che a ogni chiamante.
        riga = {"ts": ora, "flusso": flusso, "traccia": traccia or None, **campi}
        try:
            with self._file(ora).open("a", encoding="utf-8") as f:
                f.write(json.dumps(riga, ensure_ascii=False) + "\n")
        except Exception as exc:
            log.error("diario_non_scritto", errore=repr(exc))
        return riga

    async def annota(self, flusso: str, traccia: str | None, **campi: Any) -> None:
        """Scrive **e** manda alla scrivania. Vedi `scrivi` per la traccia."""
        riga = self.scrivi(flusso, traccia, **campi)
        if riga and self._pubblica is not None:
            try:
                await self._pubblica({"topic": TOPIC, **riga})
            except Exception as exc:                      # pragma: no cover
                log.error("diario_non_pubblicato", errore=repr(exc))

    # ── lettura ──────────────────────────────────────────────────────────────
    #
    # Fino al 2 settembre 2026 in `core/` NESSUNO leggeva il diario: la
    # produzione usava solo `annota()`, e `leggi()` e `giorni()` avevano un solo
    # lettore, `scripts/diario.py`. Adesso un lettore c'e', ed e' il risveglio:
    # `core/memory/risveglio.py::righe_dal` rilegge i giorni dall'ultimo
    # resoconto per dire che cosa si e' rotto e da quando a quando JARVIS era
    # spento. Il pannello della scrivania resta una coda VIVA: riceve
    # `agent.diario` mentre le righe si scrivono, non apre nessun file e non sa
    # chiedere un giorno. Riaprendo l'app, il diario di ieri non si vede.
    #
    # ⚠️ E `leggi` non sarebbe MAI comparsa fra i sospetti di `scripts/orfani.py`
    # nemmeno quando era orfana davvero, per
    # una ragione diversa dal conteggio per nome chiuso il 29 agosto: `leggi` e'
    # dichiarato da `Ocr` (`core/platform/base.py:342`), e lo scanner scusa per
    # NOME NUDO ogni metodo omonimo di un membro di protocollo, senza verificare
    # che la classe implementi quel protocollo. Misurato: `_classifica` su
    # `Diario.leggi` **senza alcun chiamante** torna
    # `implementazione_di_protocollo` — benigno, con una spiegazione falsa,
    # perche' `Diario` non e' un `Ocr`. E' un difetto dello strumento di misura,
    # e va chiuso in un turno suo.

    def leggi(self, giorno: str | None = None, flusso: str | None = None,
              limite: int = 200) -> list[dict]:
        """Le ultime righe di un giorno. `None` = oggi."""
        g = giorno or time.strftime("%Y-%m-%d")
        p = self.radice / f"{g}.jsonl"
        if not p.exists():
            return []
        fuori = []
        for riga in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(riga)
            except json.JSONDecodeError:
                continue
            if flusso is None or d.get("flusso") == flusso:
                fuori.append(d)
        return fuori[-limite:]

    def giorni(self) -> list[str]:
        return sorted(p.stem for p in self.radice.glob("*.jsonl"))
