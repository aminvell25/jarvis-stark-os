"""Web e YouTube — SPEC §6.3. Tutti in SOLA LETTURA.

Aprire una pagina non cambia nulla sul disco dell'utente: `side_effect=False`,
nessuna conferma di §6.2. Ma **e' l'unico tool di JARVIS che porta in casa
contenuto di qualcun altro**, e questo modulo fa due cose per non far finta di
niente:

  1. **Valida lo schema con un'allowlist** (invariante 2): solo `https`. Non un
     elenco di schemi vietati — `javascript:`, `data:`, `file:` — che sarebbe
     una denylist, cioe' un elenco destinato a essere incompleto. Solo `https`
     esiste; tutto il resto non e' previsto.

  2. **Restituisce l'URL RISOLTO**, che il pannello mostra in barra. E' la
     stessa disciplina di §6.2 sui path: cio' che accade dev'essere cio' che si
     legge. Un accorciatore o un redirect si vedono nella barra, non nel
     comando.

⚠️ **Il contenuto della pagina non passa da qui.** Non lo leggiamo, non lo
riassumiamo, non lo diamo a nessun LLM. Quando servira' — ARGUS, §12 — passera'
da `core/llm/untrusted.py`, che e' l'unica strada.

## La chiave YouTube

La ricerca vera richiede la Data API v3. Senza chiave si apre la pagina dei
risultati e **lo si annuncia**, come il ripiego vocale di §7.4: mai un
silenzio, mai fingere che sia andata come chiesto.

⚠️ **La chiave sta nella query string della richiesta.** Quell'URL non viene
mai registrato ne' restituito: `log` riceve solo la query dell'utente, e il
`ToolResult` solo l'esito.
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from collections.abc import Awaitable
from typing import Any, Callable

import structlog
from pydantic import BaseModel, Field

from core.settings import Settings
from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

#: Allowlist, non denylist. Vedi l'intestazione.
SCHEMI = ("https",)

RICERCA_YOUTUBE = "https://www.youtube.com/results?search_query="
API_YOUTUBE = "https://www.googleapis.com/youtube/v3/search"
TIMEOUT_S = 6.0


class OpenWebArgs(BaseModel):
    url: str = Field(min_length=4, max_length=2048)


class YouTubeArgs(BaseModel):
    query: str = Field(default="", max_length=200)


def valida_url(grezzo: str) -> str:
    """L'URL risolto, o solleva con un motivo leggibile.

    `urlsplit` non normalizza da solo: `HTTPS://ESEMPIO.IT` e
    `https://esempio.it` devono diventare la stessa cosa, o la barra del
    pannello mostrerebbe una forma e il browser ne caricherebbe un'altra.
    """
    p = urllib.parse.urlsplit(grezzo.strip())
    if p.scheme.lower() not in SCHEMI:
        raise ValueError(
            f"schema '{p.scheme or '(nessuno)'}' non ammesso: solo {', '.join(SCHEMI)}"
        )
    if not p.hostname:
        raise ValueError("URL senza host")
    # Credenziali nell'autorita': un `https://utente:segreto@host/` finirebbe
    # nella barra del pannello e in qualunque registro. Non e' un caso d'uso
    # di questo sistema.
    if p.username or p.password:
        raise ValueError("credenziali nell'URL non ammesse")
    return urllib.parse.urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), p.path, p.query, p.fragment)
    )


def _cerca_su_youtube(query: str, chiave: str) -> dict[str, Any]:
    """Una GET alla Data API v3. Bloccante: la chiama `asyncio.to_thread`.

    `urllib` e non un client HTTP: serve una richiesta sola, e aggiungere una
    dipendenza per questo vorrebbe dire chiederlo (CLAUDE.md, «non fare senza
    chiedere»).
    """
    parametri = urllib.parse.urlencode(
        {"part": "snippet", "type": "video", "maxResults": "1", "q": query, "key": chiave}
    )
    # ⚠️ Questa stringa contiene la chiave. Non finisce in nessun log.
    with urllib.request.urlopen(f"{API_YOUTUBE}?{parametri}", timeout=TIMEOUT_S) as r:
        dati = json.loads(r.read().decode("utf-8"))
    voci = dati.get("items") or []
    if not voci:
        return {}
    return {
        "video_id": voci[0]["id"]["videoId"],
        "titolo": voci[0]["snippet"]["title"],
        "canale": voci[0]["snippet"]["channelTitle"],
    }


def register_web_tools(
    settings: Callable[[], Settings],
    pubblica: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> None:
    """Le impostazioni arrivano per funzione, non per valore.

    La chiave puo' comparire dopo l'avvio — `SettingsStore` ricarica a caldo —
    e un tool che l'avesse letta una volta sola resterebbe convinto di non
    averla per sempre.

    `pubblica` chiude la catena: il tool decide, il pannello mostra. Senza,
    i tool funzionano lo stesso e restituiscono il loro esito — e' cosi' che
    i test li provano senza un socket.
    """

    async def _annuncia(msg: dict[str, Any]) -> None:
        if pubblica is not None:
            await pubblica(msg)

    async def _open_web(args: OpenWebArgs) -> ToolResult:
        try:
            url = valida_url(args.url)
        except ValueError as exc:
            return ToolResult(ok=False, error=str(exc))
        log.info("web_apri", host=urllib.parse.urlsplit(url).hostname)
        await _annuncia({"topic": "web.open", "url": url})
        return ToolResult(ok=True, output={"url": url})

    async def _youtube(args: YouTubeArgs) -> ToolResult:
        query = args.query.strip()
        ricerca = RICERCA_YOUTUBE + urllib.parse.quote_plus(query)

        if not query:
            esito = {"modo": "ricerca_aperta", "url": "https://www.youtube.com", "query": ""}
            await _annuncia({"topic": "web.open", "url": esito["url"]})
            return ToolResult(ok=True, output=esito)

        chiave = settings().secrets.youtube_api_key.get_secret_value()
        if not chiave:
            # Ripiego ANNUNCIATO: la differenza fra aprire la ricerca e far
            # partire il video dev'essere detta, non subita in silenzio.
            esito = {
                "modo": "ricerca_aperta", "url": ricerca, "query": query,
                "annuncio": (
                    "Senza chiave YouTube Data API non posso far partire il video: "
                    "apro la ricerca."
                ),
            }
            await _annuncia({"topic": "web.open", **esito})
            return ToolResult(ok=True, output=esito)

        try:
            trovato = await asyncio.to_thread(_cerca_su_youtube, query, chiave)
        except Exception as exc:
            log.warning("youtube_ricerca_fallita", errore=type(exc).__name__)
            esito = {
                "modo": "ricerca_aperta", "url": ricerca, "query": query,
                "annuncio": (
                    f"La ricerca YouTube non ha risposto ({type(exc).__name__}): "
                    "apro la pagina dei risultati."
                ),
            }
            await _annuncia({"topic": "web.open", **esito})
            return ToolResult(ok=True, output=esito)

        if not trovato:
            esito = {
                "modo": "ricerca_aperta", "url": ricerca, "query": query,
                "annuncio": f"Nessun video per «{query}»: apro la ricerca.",
            }
            await _annuncia({"topic": "web.open", **esito})
            return ToolResult(ok=True, output=esito)

        log.info("youtube_trovato", query=query, video_id=trovato["video_id"])
        esito = {"modo": "riproduzione", "query": query, **trovato}
        await _annuncia({"topic": "youtube.play", **trovato})
        return ToolResult(ok=True, output=esito)

    register(Tool(
        name="open_web",
        description="Apre una pagina https in un pannello browser. Restituisce l'URL risolto.",
        args_schema=OpenWebArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_open_web,
    ))
    register(Tool(
        name="youtube_search",
        description=(
            "Cerca un video su YouTube e lo fa partire. Senza chiave Data API "
            "apre la pagina dei risultati e lo annuncia."
        ),
        args_schema=YouTubeArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_youtube,
    ))
