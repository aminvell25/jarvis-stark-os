"""Allowlist tipizzata — SPEC §21.2, invariante 2.

**Solo i tool registrati esistono.** Non c'e' un elenco di cose vietate: c'e'
un elenco di cose che ci sono. I comandi utili sono finiti e si enumerano,
quelli dannosi sono infiniti e componibili, quindi una denylist e' una lista
di sconfitte gia' subite.

Due vincoli sono imposti QUI e non lasciati alla disciplina:

* invariante 27 — un tool `side_effect=True` non puo' essere `gesture_allowed`
* nome unico — registrare due volte lo stesso nome e' un errore, non una
  sostituzione: sovrascrivere in silenzio e' il modo in cui si perde un tool
  senza che nessuno se ne accorga
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

log = structlog.get_logger(__name__)


class ToolResult(BaseModel):
    """L'esito di un tool. **Mai un'eccezione verso il chiamante.**"""

    ok: bool
    output: Any = None
    error: str | None = None


class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]
    side_effect: bool
    gesture_allowed: bool = False
    handler: Callable[[Any], Awaitable[ToolResult]]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UnknownTool(LookupError):
    """Nome non presente nell'allowlist."""


class DuplicateTool(ValueError):
    """Nome gia' registrato."""


_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> None:
    if tool.side_effect and tool.gesture_allowed:
        raise ValueError(
            f"{tool.name}: un tool con side_effect non puo' essere "
            f"gesture_allowed (invariante 27). Il vincolo e' imposto nel "
            f"registry proprio per non dipendere dalla disciplina."
        )
    if tool.name in _REGISTRY:
        raise DuplicateTool(
            f"{tool.name} e' gia' registrato. Registrare due volte lo stesso "
            f"nome non sostituisce: e' un errore."
        )
    _REGISTRY[tool.name] = tool
    log.debug("tool_registrato", nome=tool.name, side_effect=tool.side_effect)


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def names() -> list[str]:
    return sorted(_REGISTRY)


def describe_all() -> list[dict[str, Any]]:
    """Descrizione dei tool per `state.snapshot`. **Mai gli handler.**"""
    return [
        {
            "name": t.name,
            "description": t.description,
            "side_effect": t.side_effect,
            "gesture_allowed": t.gesture_allowed,
        }
        for t in sorted(_REGISTRY.values(), key=lambda t: t.name)
    ]


async def invoke(name: str, args: dict[str, Any] | None = None) -> ToolResult:
    """Esegue un tool dell'allowlist.

    **Solleva `UnknownTool` se il nome non e' registrato**, e questa e' l'unica
    eccezione che esce di qui. La distinzione e' voluta:

    * un nome sconosciuto e' un errore di INSTRADAMENTO — l'allowlist e' il
      contratto, e chiedere qualcosa che non c'e' significa che il chiamante e'
      rotto o ostile. Va rumoroso.
    * argomenti invalidi o un handler che fallisce sono ESITI: il chiamante
      deve poterli leggere e reagire, quindi tornano come `ToolResult(ok=False)`.

    ⚠️ Il `CLAUDE.md` impone che nessuna eccezione arrivi all'LLM. Non e' in
    contraddizione: `invoke()` e' l'API interna. La conversione di `UnknownTool`
    in `ToolResult` avviene al confine con l'LLM, cioe' nel router — **Fase 4**.
    """
    tool = _REGISTRY.get(name)
    if tool is None:
        raise UnknownTool(
            f"{name!r} non e' nell'allowlist. Registrati: {', '.join(names()) or '(nessuno)'}"
        )

    try:
        parsed = tool.args_schema.model_validate(args or {})
    except ValidationError as exc:
        return ToolResult(ok=False, error=f"argomenti non validi: {exc}")

    try:
        return await tool.handler(parsed)
    except Exception as exc:                      # nessuna eccezione risale
        log.error("tool_fallito", nome=name, errore=str(exc), exc_info=True)
        return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")


def clear() -> None:
    """Svuota il registro. **Solo per i test.**"""
    _REGISTRY.clear()
