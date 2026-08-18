"""The Guardian Open Platform — SPEC §15.

> «l'unica API news gratuita seria: **corpo completo**»

Gratis **con chiave**. Su questa macchina la chiave non c'e' — non esiste
nemmeno `settings.toml` — quindi il collector si dichiara non disponibile e lo
ANNUNCIA, invece di restituire zero notizie facendo sembrare che il mondo sia
fermo. E' la stessa regola del ripiego vocale di §7.4 e di YouTube in Fase 6.

Il corpo completo e' il motivo per cui vale la chiave: RSS da' un sommario di
due righe, e un gate di rilevanza su due righe e' quasi un gate sul titolo.
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

import structlog

from core.llm.untrusted import Untrusted
from core.news.collectors.base import Esito, Item, rilevanza_per_parole
from core.news.collectors.rss import TIMEOUT_S, USER_AGENT, _quando

log = structlog.get_logger(__name__)

API = "https://content.guardianapis.com/search"
MAX_ITEM = 20


def _cerca(query: str, chiave: str) -> list[dict[str, Any]]:
    """Una GET alla Open Platform. Bloccante: la chiama `asyncio.to_thread`."""
    parametri = urllib.parse.urlencode({
        "q": query or "news",
        "page-size": str(MAX_ITEM),
        "show-fields": "trailText,bodyText",
        "order-by": "newest",
        "api-key": chiave,
    })
    # ⚠️ Questa stringa contiene la chiave: non finisce in nessun log.
    richiesta = urllib.request.Request(f"{API}?{parametri}",
                                       headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(richiesta, timeout=TIMEOUT_S) as r:
        dati = json.loads(r.read().decode("utf-8"))
    return dati.get("response", {}).get("results", [])


class GuardianCollector:
    name = "guardian"

    def __init__(self, chiave: Callable[[], str]) -> None:
        # Per funzione e non per valore: `SettingsStore` ricarica a caldo, e un
        # collector che avesse letto la chiave una volta sola resterebbe
        # convinto di non averla per sempre.
        self._chiave = chiave

    def disponibile(self) -> tuple[bool, str]:
        if not self._chiave():
            return False, ("senza chiave Guardian Open Platform: la fonte col corpo "
                           "completo resta spenta, RSS continua a funzionare")
        return True, "chiave presente"

    async def poll(self, topics: list[str]) -> Esito:
        esito = Esito(collector=self.name)
        ok, motivo = self.disponibile()
        if not ok:
            esito.errore = motivo          # ANNUNCIATO, non silenzioso
            return esito

        try:
            risultati = await asyncio.to_thread(
                _cerca, " OR ".join(topics[:4]), self._chiave()
            )
        except Exception as exc:
            esito.errore = f"Guardian non ha risposto: {type(exc).__name__}"
            log.warning("guardian_fallito", errore=type(exc).__name__)
            return esito

        for r in risultati:
            campi = r.get("fields", {}) or {}
            titolo = r.get("webTitle", "")
            corpo = campi.get("trailText") or campi.get("bodyText", "")
            url = r.get("webUrl", "")
            if not titolo or not url:
                continue
            esito.item.append(Item(
                fonte="The Guardian",
                url=url,
                testo=Untrusted.da("news:guardian", f"{titolo}\n{corpo[:2000]}"),
                pubblicato=_quando(r.get("webPublicationDate", "")),
            ))
        log.info("guardian_letto", item=len(esito.item))
        return esito

    def relevance(self, item: Item, topics: list[str]) -> float:
        return rilevanza_per_parole(item, topics)
