"""core/tools/registry — SPEC §21.2, invarianti 2 e 27."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from core.tools.registry import (
    DuplicateTool,
    Tool,
    ToolResult,
    UnknownTool,
    describe_all,
    get,
    invoke,
    names,
    register,
)


class Args(BaseModel):
    x: int


async def _ok(a: Args) -> ToolResult:
    return ToolResult(ok=True, output=a.x * 2)


async def _esplode(_a: Args) -> ToolResult:
    raise RuntimeError("guasto interno del tool")


def _tool(nome: str = "prova", **kw) -> Tool:
    base = dict(name=nome, description="d", args_schema=Args,
                side_effect=False, handler=_ok)
    return Tool(**{**base, **kw})


class TestAllowlist:
    async def test_tool_non_registrato_solleva(self) -> None:
        """Criterio di §22 Fase 1. Un nome sconosciuto e' un errore di
        instradamento, non un esito: l'allowlist e' il contratto."""
        with pytest.raises(UnknownTool, match="inesistente"):
            await invoke("inesistente")

    async def test_tool_registrato_esegue(self) -> None:
        register(_tool())
        assert (await invoke("prova", {"x": 21})).output == 42

    def test_nome_duplicato_rifiutato(self) -> None:
        """Sovrascrivere in silenzio e' il modo in cui si perde un tool."""
        register(_tool())
        with pytest.raises(DuplicateTool):
            register(_tool())

    def test_get_non_solleva(self) -> None:
        assert get("assente") is None

    def test_names_ordinati(self) -> None:
        register(_tool("zeta"))
        register(_tool("alfa"))
        assert names() == ["alfa", "zeta"]


class TestInvariante27:
    def test_side_effect_non_puo_essere_gesture(self) -> None:
        with pytest.raises(ValueError, match="invariante 27"):
            register(_tool(side_effect=True, gesture_allowed=True))

    def test_side_effect_senza_gesture_va_bene(self) -> None:
        register(_tool(side_effect=True, gesture_allowed=False))
        assert get("prova").side_effect is True

    def test_gesture_senza_side_effect_va_bene(self) -> None:
        register(_tool(side_effect=False, gesture_allowed=True))
        assert get("prova").gesture_allowed is True


class TestNessunaEccezioneRisale:
    """CLAUDE.md: nessuna eccezione propaga; `ToolResult(ok=False, error=...)`."""

    async def test_argomenti_invalidi(self) -> None:
        register(_tool())
        r = await invoke("prova", {"x": "non un numero"})
        assert r.ok is False and "argomenti non validi" in r.error

    async def test_argomento_mancante(self) -> None:
        register(_tool())
        r = await invoke("prova", {})
        assert r.ok is False

    async def test_handler_che_esplode(self) -> None:
        register(_tool(handler=_esplode))
        r = await invoke("prova", {"x": 1})
        assert r.ok is False and "RuntimeError" in r.error


class TestDescrizione:
    def test_non_espone_gli_handler(self) -> None:
        """`describe_all` finisce in `state.snapshot`, cioe' sul socket."""
        register(_tool())
        d = describe_all()[0]
        assert set(d) == {"name", "description", "side_effect", "gesture_allowed"}
        assert "handler" not in d
