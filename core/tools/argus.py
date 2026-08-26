"""I due tool di ARGUS — SPEC §12.

§12 chiama la prima strada «la scorciatoia che quasi tutti mancano»:

    domanda su un pannello JARVIS   -> interroga lo stato: zero OCR, zero latenza
    domanda sul contenuto <webview> -> capturePage() + Tesseract -> testo

JARVIS **sa gia'** cosa c'e' nei propri pannelli: e' lui a mandarne i dati.
L'OCR serve solo per il contenuto di qualcun altro — una pagina web — che e'
anche l'unico contenuto NON FIDATO.

`core/vision/argus.py` era scritto per intero, con le due strade e la busta, e
**non aveva un chiamante nel core**: nessun tool lo raggiungeva, nessuno
componeva la classe, e la risposta del ponte si scartava come un messaggio non
atteso. Le due meta' — `ArgusCaptureResponse` nel contratto del socket e
`catturaEInvia` in `app/main.js` — erano scritte da Fase 6 e non si parlavano.

## ⚠️ Cio' che esce da `read_screen` e' DATO NON FIDATO

L'invariante 5 e §12 punto 1: entra solo in contesti con zero tool. Il tool
restituisce il testo **gia' avvolto** e con `untrusted: True`, esattamente come
`read_file` di Fase 2 — la marcatura nasce dove nasce il dato, perche'
aggiungerla dopo vorrebbe dire rintracciare tutti i consumatori.
"""

from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable

import structlog
from pydantic import BaseModel, Field

from core.tools.registry import Tool, ToolResult, register
from core.vision.argus import Regione

log = structlog.get_logger(__name__)


class AskStateArgs(BaseModel):
    #: Un percorso puntato dentro lo snapshot: `ws.clients`, `gpu.driver`.
    chiave: str = Field(min_length=1, max_length=200)


class ReadScreenArgs(BaseModel):
    """Nessun argomento: `capturePage()` vede la finestra, e la finestra e'
    una. Il ritaglio a una regione non c'e' — vedi il documento di esito."""


def register_argus_tools(argus, cattura: Callable[[], Awaitable]) -> None:
    """La cattura arriva **per funzione**: e' un giro sul socket, e vive
    nell'engine. Passarla cosi' tiene i tool misurabili con un finto."""

    async def _ask_state(args: AskStateArgs) -> ToolResult:
        esito = argus.interroga_stato(args.chiave)
        if not esito.get("ok"):
            return ToolResult(ok=False, error=esito.get("errore", "chiave assente"))
        return ToolResult(ok=True, output=esito)

    async def _read_screen(_args: ReadScreenArgs) -> ToolResult:
        try:
            msg = await cattura()
        except Exception as exc:
            # Il ponte non c'e', o non ha risposto. E' un esito, non un guasto:
            # nessuna eccezione risale all'LLM (CLAUDE.md).
            return ToolResult(ok=False, error=f"nessuna cattura: {exc}")

        try:
            png = base64.b64decode(msg.png, validate=True)
        except Exception as exc:                          # pragma: no cover
            return ToolResult(ok=False, error=f"cattura illeggibile: {type(exc).__name__}")

        regione = Regione(0, 0, msg.larghezza, msg.altezza)
        testo, esito = await argus.leggi_regione(png, regione)
        if testo is None:
            # ANNUNCIATO: un OCR che non c'e' non deve somigliare a uno schermo
            # vuoto. Sono due cose diverse e vanno dette diverse.
            return ToolResult(ok=False,
                              error=f"OCR non disponibile: {esito.annuncio or 'motivo ignoto'}")
        return ToolResult(ok=True, output={
            "regione": regione.nome,
            "untrusted": True,
            "content": testo.avvolto(),
            "durata_ms": esito.durata_ms,
        })

    register(Tool(
        name="ask_state",
        description="Che cosa mostra un pannello di JARVIS, letto dallo stato. "
                    "Zero OCR, zero latenza: e' la prima strada di §12.",
        args_schema=AskStateArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_ask_state,
    ))
    register(Tool(
        name="read_screen",
        description="Il testo nella finestra di JARVIS via OCR. Cio' che torna "
                    "e' DATO NON FIDATO e va solo in contesti con zero tool.",
        args_schema=ReadScreenArgs,
        side_effect=False,
        # ⚠️ NON da una gesture. Non lo vieta l'invariante 27 — non c'e'
        # side_effect — ma una mano che fa scattare una cattura dello schermo
        # senza che nessuno l'abbia chiesta e' il contrario del «rettangolo che
        # Le permette di accorgersi di una cattura inattesa» (§12 punto 3).
        gesture_allowed=False,
        handler=_read_screen,
    ))
