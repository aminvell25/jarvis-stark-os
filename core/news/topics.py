"""Estrattore di argomenti — SPEC §15.

> conversazione → **[estrattore argomenti]** (haiku, batch 60s, effort low)
> → [watcher feed] → [gate rilevanza] → [budget]

Legge la CONVERSAZIONE — testo Suo — e produce le parole con cui il watcher
filtrera' i feed.

## ⚠️ Perche' rifiuta il contenuto non fidato

Se un giorno qualcuno desse in pasto all'estrattore anche il testo delle news
«per migliorare gli argomenti», si chiuderebbe un anello:

    articolo ostile → diventa un argomento → decide quali altri articoli
    superano il gate → altri articoli ostili → …

E' l'avvelenamento del ciclo di retroazione. Non somiglia a un attacco mentre
lo si scrive — somiglia a un miglioramento — ed e' esattamente per questo che
va reso impossibile invece che sconsigliato.

`estrai()` **solleva** davanti a un `Untrusted`, con la stessa arma di Fase 6.

## Il batch

§15 dice «batch 60s»: gli argomenti non si ricalcolano a ogni frase. Costa un
turno di LLM ogni minuto invece di uno per frase, e soprattutto evita che una
singola battuta faccia cambiare tutto cio' che JARVIS considera interessante.
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.llm.untrusted import ContenutoNonFidato, Untrusted

log = structlog.get_logger(__name__)

#: §15: «argomenti scaduti dopo 30 minuti».
SCADENZA_S = 30 * 60
BATCH_S = 60
MAX_ARGOMENTI = 8
MIN_LUNGHEZZA = 4

#: Parole che compaiono in ogni conversazione e non distinguono niente. Un
#: argomento «cosa» farebbe passare qualunque notizia.
FERME = frozenset("""
alla alle allo agli anche ancora avere bene come cosa dalla dalle dallo dagli
degli deve della delle dello dentro dopo dove durante essere fare fatto fatta
fosse grazie insieme intanto invece letto loro meno mentre molto niente nella
nelle nello negli oggi ogni oltre pero però perche perché piu più poco poi
prima proprio quale quando quanto quella quelle quello questa queste questo
qualcosa sempre senza solo sono stata stato stesso subito tanto tutta tutte
tutti tutto ultima ultimo vedere verso volta volte ciao jarvis
interessa interessante piace piaciuto sentito visto detto parlato
""".split())

#: Un argomento non e' una parola qualunque: e' una cosa di cui si parla. Senza
#: analisi grammaticale — che vorrebbe una dipendenza — l'euristica migliore e'
#: che gli argomenti utili tornano PIU' DI UNA VOLTA, o sono lunghi.
MIN_OCCORRENZE = 2
MIN_LUNGHEZZA_SINGOLA = 8


@dataclass(frozen=True)
class Argomento:
    parola: str
    peso: float = 1.0
    visto: float = field(default_factory=time.time)

    def scaduto(self, adesso: float | None = None, scadenza: float = SCADENZA_S) -> bool:
        return (adesso or time.time()) - self.visto > scadenza


def _controlla_fidato(testo: Any) -> str:
    """La barriera di R60. Una riga, e chiude l'anello di retroazione."""
    if isinstance(testo, Untrusted):
        raise ContenutoNonFidato(
            f"l'estrattore di argomenti ha ricevuto contenuto non fidato da "
            f"{testo.origine}. §15: gli argomenti vengono dalla CONVERSAZIONE. "
            "Se li estraesse dalle news, un articolo ostile potrebbe scegliere "
            "quali altri articoli La raggiungono."
        )
    return str(testo)


def estrai_locale(conversazione: str, massimo: int = MAX_ARGOMENTI,
                  adesso: float | None = None) -> list[Argomento]:
    """L'estrattore senza LLM: parole notevoli per frequenza.

    §15 vuole haiku, e l'implementazione con LLM e' `EstrattoreLLM`. Questa e'
    il ripiego che gira sempre — senza rete, senza quota, senza attesa — ed e'
    anche cio' che i test usano per misurare il resto della catena senza
    dipendere da un modello.
    """
    testo = _controlla_fidato(conversazione).lower()
    conteggi: dict[str, int] = {}
    for p in re.findall(r"[a-zàèéìòóù']{%d,}" % MIN_LUNGHEZZA, testo):
        if p in FERME:
            continue
        conteggi[p] = conteggi.get(p, 0) + 1

    # Una parola detta una volta sola e corta e' rumore: «letto», «europa» in
    # una frase di passaggio. Una detta due volte, o lunga, e' un argomento.
    notevoli = {
        p: n for p, n in conteggi.items()
        if n >= MIN_OCCORRENZE or len(p) >= MIN_LUNGHEZZA_SINGOLA
    } or conteggi

    ordinate = sorted(notevoli.items(), key=lambda kv: (-kv[1], kv[0]))[:massimo]
    massimo_conteggio = ordinate[0][1] if ordinate else 1
    # `adesso` e non `time.time()` dentro il dataclass: la scadenza dei trenta
    # minuti di §15 e il batch dei sessanta secondi devono leggere lo STESSO
    # orologio, o l'uno misura il tempo dei test e l'altro quello vero. L'ha
    # trovato il test della scadenza.
    ora = adesso if adesso is not None else time.time()
    return [Argomento(parola=p, peso=n / massimo_conteggio, visto=ora) for p, n in ordinate]


class EstrattoreLLM:
    """§15: haiku, batch 60 s, effort low.

    L'LLM arriva per funzione e non per import: T1 e T2 vivono nella pipeline
    vocale, che non e' composta nell'engine (lo si e' visto in Fase 5 con la
    mesh agenti). Cosi' i test lo misurano con un finto, e il giorno in cui la
    pipeline sara' composta bastera' passargliela.
    """

    def __init__(self, chiedi: Callable[[str], Awaitable[str]] | None = None,
                 batch_s: float = BATCH_S) -> None:
        self._chiedi = chiedi
        self._batch_s = batch_s
        self._ultimo = 0.0
        self._argomenti: list[Argomento] = []

    def argomenti_a(self, adesso: float | None = None) -> list[Argomento]:
        """Quelli non scaduti a un dato istante — §15, trenta minuti.

        L'istante e' un ARGOMENTO e non `time.time()` dentro il metodo: la
        prima versione lo leggeva da sola, e `aggiorna(adesso=X)` restituiva
        argomenti timbrati a X ma filtrati sull'orologio vero — due orologi
        nella stessa chiamata, e una lista sempre vuota nei test. Un solo
        orologio, e chi chiama decide quale.
        """
        return [a for a in self._argomenti if not a.scaduto(adesso)]

    @property
    def argomenti(self) -> list[Argomento]:
        return self.argomenti_a()

    def parole(self) -> list[str]:
        return [a.parola for a in self.argomenti]

    async def aggiorna(self, conversazione: str, adesso: float | None = None) -> list[Argomento]:
        """Ricalcola, non piu' spesso di una volta per batch."""
        testo = _controlla_fidato(conversazione)
        ora = adesso if adesso is not None else time.time()
        if ora - self._ultimo < self._batch_s and self._argomenti:
            return self.argomenti_a(ora)
        self._ultimo = ora

        if self._chiedi is None:
            self._argomenti = estrai_locale(testo, adesso=ora)
            log.info("argomenti_estratti", modo="locale", quanti=len(self._argomenti))
            return self.argomenti_a(ora)

        try:
            risposta = await self._chiedi(testo)
        except Exception as exc:
            # Ripiego ANNUNCIATO nei log: l'estrattore non deve mai fermare la
            # catena, ma nemmeno far finta di aver usato il modello.
            log.warning("estrattore_llm_fallito", errore=type(exc).__name__)
            self._argomenti = estrai_locale(testo, adesso=ora)
            return self.argomenti_a(ora)

        parole = [p.strip().lower() for p in re.split(r"[,\n;]+", risposta) if p.strip()]
        self._argomenti = [
            Argomento(parola=p, visto=ora)
            for p in parole[:MAX_ARGOMENTI]
            if len(p) >= MIN_LUNGHEZZA and p not in FERME
        ]
        log.info("argomenti_estratti", modo="llm", quanti=len(self._argomenti))
        return self.argomenti_a(ora)
