"""YouTube Data API v3 come sorgente news — SPEC §15.

> ⚠️ «Reuters e AP non hanno feed video gratuiti. Il notiziario video sara'
> YouTube embed nella `<webview>`.»

Da cui: questo collector produce Item il cui URL e' un video, e il pannello
browser di Fase 6 sa gia' aprirlo nell'embed. Nessun codice nuovo per la
riproduzione — quella strada esiste da §6.3.

La ricerca riusa `_cerca_su_youtube` di `core/tools/web.py`: una seconda
implementazione della stessa chiamata divergerebbe alla prima modifica, e
sarebbe un secondo posto in cui la chiave puo' finire in un log.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

import structlog

from core.llm.untrusted import Untrusted
from core.news.collectors.base import Esito, Item, rilevanza_per_parole
from core.tools.web import _cerca_su_youtube

log = structlog.get_logger(__name__)


class YouTubeCollector:
    name = "youtube"

    def __init__(self, chiave: Callable[[], str]) -> None:
        self._chiave = chiave

    def disponibile(self) -> tuple[bool, str]:
        if not self._chiave():
            return False, ("senza chiave YouTube Data API: nessun notiziario video, "
                           "il resto delle fonti continua")
        return True, "chiave presente"

    async def poll(self, topics: list[str]) -> Esito:
        esito = Esito(collector=self.name)
        ok, motivo = self.disponibile()
        if not ok:
            esito.errore = motivo
            return esito
        if not topics:
            return esito

        try:
            trovato = await asyncio.to_thread(_cerca_su_youtube, topics[0], self._chiave())
        except Exception as exc:
            esito.errore = f"YouTube non ha risposto: {type(exc).__name__}"
            log.warning("youtube_news_fallito", errore=type(exc).__name__)
            return esito

        if trovato:
            esito.item.append(Item(
                fonte=f"YouTube · {trovato['canale']}",
                url=f"https://www.youtube.com/watch?v={trovato['video_id']}",
                testo=Untrusted.da("news:youtube", trovato["titolo"]),
                pubblicato=time.time(),
            ))
        return esito

    def relevance(self, item: Item, topics: list[str]) -> float:
        return rilevanza_per_parole(item, topics)
