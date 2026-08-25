"""Chi aziona il `Watcher` — §15, e la cadenza DEDOTTA dal tetto.

## Perche' questo file esiste

`Watcher.giro()` non aveva **un solo chiamante nel core**: solo un test e uno
script di fixture. Con `news.enabled = true` il `Watcher` si costruiva a ogni
avvio, lo snapshot diceva `giri_fatti: 0`, e nessun giro sui feed e' mai
avvenuto. Costruito e mai azionato, come i quattro tool di memoria di §13.

`Argomenti` era nello stesso stato, e il suo commento lo diceva gia':

> il giorno in cui la pipeline sara' composta bastera' passargliela.

## La cadenza, dedotta

⚠️ **§15 non dichiara ogni quanto si guardino i feed.** Dichiara una sola
frequenza: **3 interruzioni all'ora**, che e' il ritmo con cui JARVIS puo'
PARLARE, non quello con cui puo' GUARDARE. Il numero qui sotto non e' scritto
da nessuna parte, e non lo invento: lo derivo, e scrivo da che cosa.

**Il tetto superiore viene dagli argomenti.** Un argomento vive 30 minuti
(`news.topic_ttl_minutes`). Un giro piu' lento della vita di un argomento
vorrebbe dire che un argomento puo' nascere e scadere senza essere mai stato
guardato — la funzione non farebbe niente, in silenzio. Perche' ogni argomento
abbia almeno **due** occasioni: periodo <= TTL / 2.

**Il tetto inferiore viene dal budget.** Tre interruzioni all'ora fanno una
finestra di 1200 s l'una. Un giro esattamente lungo quanto la finestra da' un
solo candidato per finestra: se il gate lo scarta — poco rilevante, gia' visto,
Lei sta parlando — quella finestra e' persa fino al giro dopo. **Dimezzandola**
ce ne sono due:

    periodo = 3600 / (2 x tetto)     con tetto = 3  ->  600 s

**E un pavimento, che non viene dalla nostra aritmetica ma dall'educazione.**
Chi mettesse `max_interruptions_per_hour = 60` otterrebbe un giro ogni 30
secondi su server che non sono nostri. Sotto il minuto non si scende.

    periodo = min(max(3600 / (2 x tetto), 60), ttl / 2)

Il numero **cambia con l'impostazione**, ed e' la proprieta' che conta: non e'
una costante travestita da deduzione. Con 3/ora fa 600 s; con 6/ora, 300; con
1/ora sarebbe 1800 e il tetto degli argomenti lo riporta a 900.

## E senza argomenti non si guarda affatto

`giro()` calcola la rilevanza **contro gli argomenti**. Senza, niente puo'
essere rilevante e niente puo' passare: un giro a lista vuota e' traffico su un
server di terzi in cambio di nulla. §15 vuole che le news seguano la
conversazione, e finche' non si e' parlato non c'e' conversazione da seguire.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from core.news.feeds import Watcher
from core.news.gate import Contesto
from core.news.topics import EstrattoreLLM

log = structlog.get_logger(__name__)

#: Il pavimento dell'educazione. Vedi l'intestazione.
PERIODO_MINIMO_S = 60.0


def periodo_dei_giri(tetto_per_ora: int, ttl_minuti: int) -> float:
    """La cadenza, dai due numeri che §15 dichiara davvero.

    Solleva se i due numeri non hanno senso: un tetto a zero vorrebbe dire che
    JARVIS non puo' mai parlare, e allora guardare i feed non serve a niente —
    ed e' meglio dirlo che dividere per zero.
    """
    if tetto_per_ora <= 0:
        raise ValueError(
            f"max_interruptions_per_hour = {tetto_per_ora}: con un tetto a zero "
            "nessuna news puo' passare, e guardare i feed sarebbe traffico "
            "per niente. Spegni `news.enabled` invece."
        )
    if ttl_minuti <= 0:
        raise ValueError(f"topic_ttl_minutes = {ttl_minuti}: un argomento che "
                         "scade subito non arriva a nessun giro")
    dal_budget = 3600.0 / (2 * tetto_per_ora)
    dagli_argomenti = ttl_minuti * 60.0 / 2
    return min(max(dal_budget, PERIODO_MINIMO_S), dagli_argomenti)


class MotoreNews:
    """Tiene gli argomenti, aziona il `Watcher`, e conta i giri.

    Non decide niente su cosa passa: quello e' del `Gate`. Qui si decide solo
    **quando guardare**, e la risposta e' in `periodo_dei_giri`.
    """

    def __init__(self, watcher: Watcher, impostazioni, *,
                 contesto: Any = None, orologio=time.time) -> None:
        self._watcher = watcher
        self._periodo = periodo_dei_giri(impostazioni.max_interruptions_per_hour,
                                         impostazioni.topic_ttl_minutes)
        #: Come si chiede «che cosa sta succedendo adesso». Arriva per funzione
        #: perche' lo sa la pipeline vocale, non le news.
        self._contesto = contesto or (lambda: Contesto())
        self._orologio = orologio
        self.argomenti = EstrattoreLLM()
        self.giri = 0
        self.ultimo: float | None = None
        self._compito: asyncio.Task | None = None

    # ── gli argomenti vengono dalla conversazione (§15) ──────────────────────

    async def ascolta(self, detto: str) -> list[str]:
        """Una frase dell'utente diventa argomenti. Non solleva: siamo sul
        percorso della voce, e un'eccezione qui zittirebbe JARVIS."""
        if not detto or not detto.strip():
            return []
        try:
            await self.argomenti.aggiorna(detto)
        except Exception as exc:
            log.error("argomenti_non_estratti", errore=repr(exc))
            return []
        parole = self.argomenti.parole()
        log.info("argomenti_dalla_voce", quanti=len(parole), parole=sorted(parole))
        return parole

    # ── il ciclo ─────────────────────────────────────────────────────────────

    def stato(self) -> dict[str, Any]:
        return {
            "periodo_s": round(self._periodo, 1),
            "giri_fatti": self.giri,
            "argomenti": sorted(self.argomenti.parole()),
            "ultimo_giro": self.ultimo,
        }

    async def un_giro(self) -> bool:
        """Un giro solo. `False` se non c'era niente da guardare.

        Ritorna un bool e non il `Giro` perche' chi chiama non deve decidere
        niente su cio' che e' passato: lo ha gia' deciso il gate, e le card
        sono gia' partite dal `pubblica` del `Watcher`. Questo file decide
        **quando guardare**, non che farsene di cio' che si trova.
        """
        parole = self.argomenti.parole()
        if not parole:
            # Vedi l'intestazione: senza argomenti niente puo' essere
            # rilevante, e un giro sarebbe traffico in cambio di nulla.
            return False
        try:
            g = await self._watcher.giro(parole, self._contesto())
        except Exception as exc:
            # Un feed di terzi che si comporta male non ferma il core.
            log.error("giro_news_fallito", errore=repr(exc))
            return False
        self.giri += 1
        self.ultimo = self._orologio()
        log.info("giro_news", letti=g.letti, passati=g.passati,
                 scartati=dict(g.scartati), argomenti=len(parole))
        return True

    async def gira(self) -> None:
        """Il ciclo, finche' non lo si annulla."""
        log.info("grado_acceso", grado="news_motore",
                 periodo_s=round(self._periodo, 1))
        while True:
            await asyncio.sleep(self._periodo)
            await self.un_giro()

    def avvia(self) -> asyncio.Task:
        self._compito = asyncio.create_task(self.gira())
        return self._compito

    async def ferma(self) -> None:
        if self._compito is None:
            return
        self._compito.cancel()
        try:
            await self._compito
        except asyncio.CancelledError:
            pass
        except Exception as exc:                         # pragma: no cover
            log.error("motore_news_caduto", errore=repr(exc))
        self._compito = None
