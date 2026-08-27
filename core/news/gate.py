"""Gate e budget — SPEC §15.

> **Le regole senza cui abbandonera' la funzione in tre giorni**: 3
> interruzioni/ora max · mai mentre Lei parla o con un pannello a pieno
> schermo · mai a metà frase · argomenti scaduti dopo 30 minuti · *«non
> parlarmene più»* chiude l'argomento in modo persistente.

Quella riga e' il vero contenuto della fase. Trovare notizie e' facile;
**non dirle** e' la parte difficile, ed e' l'unica che decide se la funzione
resta accesa dopo tre giorni.

## Cio' che non so vale come un no

Le regole 2 e 3 dipendono da stati che il core non produce da solo. La
tentazione sarebbe trattare «non lo so» come «via libera», perche' altrimenti
in questa configurazione non passa mai niente.

E' la tentazione sbagliata. **Uno stato ignoto vale come un divieto**: se non
so se sta parlando, non La interrompo. Fail-closed come il registry di Fase 1,
la conferma di Fase 2 e la barriera di Fase 6 — in un sistema che parla da
solo, la modalita' silenziosa e' quella sicura.

### Chi riempie i tre campi, oggi

Un tri-stato senza produttore e' un divieto permanente travestito da
precauzione, quindi vale la pena scrivere chi risponde e chi no:

  `sta_parlando`               **c'e'**: `VoicePipeline.sta_parlando`, che la
                               radice di composizione passa a `MotoreNews` per
                               funzione (vedi `MotoreNews._parla_adesso`)
  `frase_in_corso`             lo dichiara la radice di composizione insieme al
                               resto del `Contesto`
  `pannello_a_schermo_intero`  ⚠️ **nessun produttore.** Finche' resta cosi',
                               questo campo da solo tiene chiuso il gate in
                               esercizio, qualunque cosa dicano gli altri due.

Il terzo punto e' un difetto dichiarato, non una regola: la regola e' che
l'ignoto non interrompa, ed e' giusta. Che sia ignoto per SEMPRE, invece, e'
un pezzo che manca.

## Perche' il budget e' una finestra scorrevole

Tre all'ora contate su un'ora solare darebbero tre annunci alle 10:58 e altri
tre alle 11:02: sei in quattro minuti, e formalmente dentro il budget. La
finestra scorrevole conta le ultime tre interruzioni davvero.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.news.collectors.base import Item

log = structlog.get_logger(__name__)

#: §15, tutte e cinque.
MAX_PER_ORA = 3
FINESTRA_S = 3600.0
RILEVANZA_MINIMA = 0.15
#: Il nome del topic in `memory_data/topics/` che tiene gli argomenti chiusi.
TOPIC_SILENZIO = "news-silenziati"


@dataclass(frozen=True)
class Contesto:
    """Cosa sta succedendo adesso, per le regole 2 e 3 di §15.

    `None` NON vuol dire falso: vuol dire **non lo so**, e allora non si
    interrompe. Il campo esiste apposta come tri-stato invece che come bool
    con un default comodo.
    """

    sta_parlando: bool | None = None
    pannello_a_schermo_intero: bool | None = None
    #: `True` quando l'utente ha una frase a meta' — §15, «mai a meta' frase».
    frase_in_corso: bool | None = None

    def motivo_del_no(self) -> str | None:
        for valore, ignoto, detto in (
            (self.sta_parlando, "non so se sta parlando", "sta parlando"),
            (self.pannello_a_schermo_intero, "non so se c'e' un pannello a schermo intero",
             "c'e' un pannello a schermo intero"),
            (self.frase_in_corso, "non so se ha una frase a meta'", "ha una frase a meta'"),
        ):
            if valore is None:
                return ignoto
            if valore:
                return detto
        return None


@dataclass
class Decisione:
    passa: bool
    motivo: str
    item: Item | None = None


class Gate:
    """Le cinque regole di §15, in un posto solo.

    `store` e' il `MemoryStore` di Fase 4: «non parlarmene piu'» finisce in un
    file markdown che sopravvive al riavvio e che Lei puo' aprire e correggere
    con un editor — la stessa proprieta' che §5.5 chiede alla memoria.
    """

    def __init__(self, store: Any | None = None, max_per_ora: int = MAX_PER_ORA,
                 rilevanza_minima: float = RILEVANZA_MINIMA) -> None:
        self._store = store
        self._max = max_per_ora
        self._minima = rilevanza_minima
        self._interruzioni: list[float] = []
        self._visti: set[str] = set()
        self._silenziati: set[str] = self._carica_silenziati()

    # ── regola 5: persistente ────────────────────────────────────────────────

    def _carica_silenziati(self) -> set[str]:
        if self._store is None:
            return set()
        t = self._store.leggi_topic(TOPIC_SILENZIO)
        if t is None:
            return set()
        return {
            r.strip("- ").strip().lower()
            for r in t.contenuto.splitlines()
            if r.strip().startswith("-")
        }

    def silenzia(self, argomento: str) -> None:
        """«Non parlarmene piu'». Persistente, e leggibile a occhio nudo."""
        self._silenziati.add(argomento.strip().lower())
        if self._store is not None:
            righe = "\n".join(f"- {a}" for a in sorted(self._silenziati))
            self._store.scrivi_topic(
                TOPIC_SILENZIO,
                "# Argomenti chiusi\n\n"
                "Scritti da «non parlarmene piu'» (§15). Si tolgono cancellando\n"
                "la riga: e' un file, ed e' questo il punto.\n\n" + righe + "\n",
            )
        log.info("argomento_silenziato", argomento=argomento)

    @property
    def silenziati(self) -> set[str]:
        return set(self._silenziati)

    # ── regola 1: la finestra scorrevole ─────────────────────────────────────

    def _nella_finestra(self, adesso: float) -> list[float]:
        self._interruzioni = [t for t in self._interruzioni if adesso - t < FINESTRA_S]
        return self._interruzioni

    def restanti(self, adesso: float | None = None) -> int:
        return max(0, self._max - len(self._nella_finestra(adesso or time.time())))

    # ── la decisione ─────────────────────────────────────────────────────────

    def valuta(self, item: Item, argomenti: list[str], contesto: Contesto,
               adesso: float | None = None) -> Decisione:
        """Passa o no, e **sempre col motivo**.

        Il motivo non e' cortesia: senza, «non mi dice mai niente» e «non
        succede niente» sono indistinguibili, e la prima cosa che si fa con
        una funzione che tace e' spegnerla.
        """
        ora = adesso if adesso is not None else time.time()

        if item.id in self._visti:
            return Decisione(False, "gia' proposto")

        testo = item.testo.grezzo().lower()
        for chiuso in self._silenziati:
            if chiuso and chiuso in testo:
                return Decisione(False, f"argomento chiuso: «{chiuso}»")

        if item.rilevanza < self._minima:
            return Decisione(False, f"rilevanza {item.rilevanza:.2f} < {self._minima:.2f}")

        # Regole 2 e 3, con l'ignoto che vale come un no.
        if (motivo := contesto.motivo_del_no()) is not None:
            return Decisione(False, motivo)

        if len(self._nella_finestra(ora)) >= self._max:
            return Decisione(
                False,
                f"budget esaurito: {self._max} interruzioni nell'ultima ora",
            )

        # Da qui passa, e il conteggio si muove SOLO adesso: contarlo prima
        # vorrebbe dire consumare il budget con notizie che non sono uscite.
        self._interruzioni.append(ora)
        self._visti.add(item.id)
        log.info("news_passata", fonte=item.fonte, rilevanza=round(item.rilevanza, 2),
                 restanti=self.restanti(ora))
        return Decisione(True, "ammessa", item=item)
