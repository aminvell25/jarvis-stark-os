"""Il watcher — SPEC §15, il pezzo che tiene insieme la catena.

    conversazione → [estrattore] → [watcher] → [gate] → [budget] → card + voce

Il motore **non sa nulla delle sorgenti**: itera i collector registrati, e
aggiungerne una vuol dire aggiungere un file (§15).

## Cosa esce di qui

Due cose, e sono diverse:

  `news.card`      cio' che passa il gate: va nel pannello e, se c'e' voce,
                   in una menzione breve
  `agent.advisory` le fonti che non rispondono e i collector spenti per
                   mancanza di chiave — §16, «nessuna soglia agisce senza
                   annunciarlo»

La seconda esiste perche' una funzione che tace puo' tacere per due motivi
opposti: non e' successo niente, oppure e' rotta. Senza l'annuncio, la prima
cosa che si fa e' spegnerla.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.news.collectors.base import Esito, come_dizionario
from core.news.gate import Contesto, Gate

log = structlog.get_logger(__name__)


@dataclass
class Giro:
    """L'esito di un passaggio sui collector. Numeri, non impressioni."""

    letti: int = 0
    passati: int = 0
    scartati: dict[str, int] = field(default_factory=dict)
    errori: list[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)


class Watcher:
    def __init__(self, collectors: list[Any], gate: Gate,
                 pubblica: Callable[[dict], Awaitable[None]] | None = None) -> None:
        self._collectors = list(collectors)
        self._gate = gate
        self._pubblica = pubblica

    async def _annuncia(self, msg: dict) -> None:
        if self._pubblica is not None:
            await self._pubblica(msg)

    async def giro(self, argomenti: list[str], contesto: Contesto,
                   adesso: float | None = None) -> Giro:
        g = Giro()
        ora = adesso if adesso is not None else time.time()

        for c in self._collectors:
            ok, motivo = c.disponibile()
            if not ok:
                # Spento per mancanza di chiave: e' uno stato normale, e va
                # detto una volta — non e' un errore da ripetere a ogni giro.
                g.errori.append(f"{c.name}: {motivo}")
                continue

            esito: Esito = await c.poll(argomenti)
            g.letti += len(esito.item)
            if esito.errore:
                g.errori.append(f"{c.name}: {esito.errore}")
            for f in esito.fonti_in_errore:
                g.errori.append(f"{c.name}/{f}")

            for item in esito.item:
                # La rilevanza la calcola il COLLECTOR — puo' sapere cose sulla
                # propria sorgente — e il gate decide. Due responsabilita'
                # separate: chi misura non decide.
                valutato = type(item)(**{**item.__dict__,
                                         "rilevanza": c.relevance(item, argomenti)})
                d = self._gate.valuta(valutato, argomenti, contesto, ora)
                if d.passa:
                    g.passati += 1
                    await self._annuncia({"topic": "news.card", **come_dizionario(d.item)})
                else:
                    g.scartati[d.motivo] = g.scartati.get(d.motivo, 0) + 1

        if g.errori:
            await self._annuncia({
                "topic": "agent.advisory",
                "level": "warn",
                "reason": "fonti news non disponibili",
                "dettaglio": g.errori,
            })

        log.info("giro_news", letti=g.letti, passati=g.passati,
                 scartati=sum(g.scartati.values()), errori=len(g.errori),
                 restanti=self._gate.restanti(ora))
        return g
