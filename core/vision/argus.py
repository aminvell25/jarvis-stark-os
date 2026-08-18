"""ARGUS — `scope = "app"`. SPEC §12.

**Vede solo la finestra di JARVIS**, mai il resto dello schermo. Non e' una
limitazione tecnica: e' la decisione di §12, e sta scritta nel nome del modulo
piu' che nel codice, perche' l'unica cattura possibile e' `capturePage()` sul
`webContents` della finestra — non esiste in questo sistema una strada verso
lo schermo intero.

## Le due strade, e perche' la prima e' quasi sempre quella giusta

§12 la chiama «la scorciatoia che quasi tutti mancano»:

    domanda su un pannello JARVIS   -> interroga lo stato: zero OCR, zero latenza
    domanda sul contenuto <webview> -> capturePage() + Tesseract -> testo

JARVIS **sa gia'** cosa c'e' nei propri pannelli: e' lui a mandarne i dati. Il
core e' la sorgente di verita' della UI (§3.2), quindi la risposta e' gia' in
casa. L'OCR serve solo per il contenuto di qualcun altro — una pagina web — che
e' anche l'unico contenuto NON FIDATO.

## La regola inderogabile

> «Tutto cio' che ARGUS produce e' DATO NON FIDATO. Una pagina nella
> `<webview>` puo' contenere testo rivolto all'agente: e' il vettore di prompt
> injection principale.»

`leggi_regione()` restituisce un `Untrusted`, non una stringa. §12 mostra una
funzione che ritorna la busta gia' chiusa; qui torna il TIPO, che e' piu'
forte: una stringa avvolta puo' essere concatenata, spezzata o ri-avvolta senza
che nulla se ne accorga, un `Untrusted` no (`core/llm/untrusted.py`).

La strada dello stato, invece, **non e' contenuto non fidato**: e' roba nostra,
e torna come dizionario normale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from core.llm.untrusted import Untrusted
from core.vision.ocr import EsitoOcr

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Regione:
    """Il rettangolo catturato, in pixel della finestra.

    §12: «Il pannello disegna il rettangolo della regione catturata. Non e'
    decorazione: e' il controllo che Le permette di accorgersi di una cattura
    inattesa.» Per questo la regione viaggia col risultato e finisce sul bus.
    """

    x: int = 0
    y: int = 0
    larghezza: int = 0
    altezza: int = 0

    @property
    def nome(self) -> str:
        return f"{self.larghezza}x{self.altezza}+{self.x}+{self.y}"


class Argus:
    def __init__(self, ocr: Any, stato: Any = None) -> None:
        self._ocr = ocr
        # Il fornitore dello stato: la stessa funzione che alimenta
        # `state.snapshot`. Non una copia — una copia diverge.
        self._stato = stato

    # ── strada 1: costo zero ────────────────────────────────────────────────

    def interroga_stato(self, chiave: str) -> dict[str, Any]:
        """Risponde da cio' che il core gia' sa. Nessuna cattura, nessun OCR.

        `chiave` e' un percorso puntato dentro lo snapshot: `ws.clients`,
        `gpu.driver`, `settings.voice.stt_provider`. Chi chiede non deve
        conoscere la forma esatta dello snapshot, e chi risponde non deve
        indovinare cosa intendeva.
        """
        if self._stato is None:
            return {"ok": False, "errore": "nessuna sorgente di stato collegata"}
        nodo: Any = self._stato()
        for pezzo in chiave.split("."):
            if not isinstance(nodo, dict) or pezzo not in nodo:
                return {"ok": False, "errore": f"«{chiave}» non esiste nello stato"}
            nodo = nodo[pezzo]
        return {"ok": True, "chiave": chiave, "valore": nodo, "ocr": False}

    # ── strada 2: cattura e OCR, e cio' che ne esce non e' fidato ───────────

    async def leggi_regione(self, png: bytes, regione: Regione) -> tuple[Untrusted | None, EsitoOcr]:
        """Il testo dello schermo, come DATO NON FIDATO.

        Restituisce anche l'esito dell'OCR, perche' un ripiego va annunciato e
        chi chiama deve avere di che annunciarlo.
        """
        esito = await self._ocr.leggi(png)
        if not esito.ok:
            log.info("argus_ocr_non_disponibile", regione=regione.nome)
            return None, esito
        log.info("argus_letto", regione=regione.nome, caratteri=len(esito.testo),
                 ms=esito.durata_ms)
        return Untrusted.da(f"screen:{regione.nome}", esito.testo), esito
