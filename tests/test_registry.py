"""core/tools/registry — SPEC §21.2, invarianti 2 e 27."""

from __future__ import annotations

import asyncio

import pytest
from pathlib import Path

from pydantic import BaseModel

from core.tools.confirm import Operazione, Piano
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
    set_confirm_hook,
)


class Args(BaseModel):
    x: int


async def _ok(a: Args) -> ToolResult:
    return ToolResult(ok=True, output=a.x * 2)


async def _esplode(_a: Args) -> ToolResult:
    raise RuntimeError("guasto interno del tool")


async def _piano(_a: Args) -> Piano:
    """Piano minimo. Dalla Fase 2 un tool con `side_effect` non si registra
    senza: e' il registry a non permettere che ci si dimentichi la conferma."""
    return Piano(tool="prova", riepilogo="una operazione",
                 operazioni=(Operazione(tipo="prova", sorgente=Path("/tmp/x")),))


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
            register(_tool(side_effect=True, gesture_allowed=True, planner=_piano))

    def test_side_effect_senza_gesture_va_bene(self) -> None:
        register(_tool(side_effect=True, gesture_allowed=False, planner=_piano))
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
        assert set(d) == {"name", "description", "side_effect", "gesture_allowed",
                          "verificabile"}
        assert "handler" not in d
        # ADR-012 criterio 4: il conto dei tool che sanno dire com'e' andata
        # viaggia QUI perche' il registro vive nel processo del core e
        # `jarvis doctor` e' un altro processo. Il verificatore stesso non
        # esce: e' un callable, come l'handler.
        assert "verifica" not in d and d["verificabile"] is False


class TestInvariante3:
    """La conferma umana e' imposta dal registry, non dalla disciplina."""

    def test_side_effect_senza_planner_non_si_registra(self) -> None:
        """Senza un piano non c'e' nulla da mostrare all'utente, quindi non c'e'
        nulla da confermare: il tool non deve poter esistere."""
        with pytest.raises(ValueError, match="planner"):
            register(_tool(side_effect=True))

    def test_planner_su_un_tool_innocuo_e_un_errore(self) -> None:
        with pytest.raises(ValueError, match="nulla da far confermare"):
            register(_tool(side_effect=False, planner=_piano))

    async def test_senza_conferma_collegata_non_esegue(self) -> None:
        """FAIL-CLOSED. Dimenticare di collegare la conferma deve rendere il
        sistema inutile, non pericoloso."""
        eseguito = []

        async def h(_a, _piano=None):
            eseguito.append(1)
            return ToolResult(ok=True)

        register(_tool(side_effect=True, planner=_piano, handler=h))
        r = await invoke("prova", {"x": 1})
        assert r.ok is False and "conferma" in r.error
        assert not eseguito, "ha eseguito senza conferma"

    async def test_rifiuto_non_esegue(self) -> None:
        eseguito = []

        async def h(_a, _piano=None):
            eseguito.append(1)
            return ToolResult(ok=True)

        register(_tool(side_effect=True, planner=_piano, handler=h))
        set_confirm_hook(lambda piano: asyncio.sleep(0, "rifiutato"))
        r = await invoke("prova", {"x": 1})
        assert r.ok is False and "rifiutato" in r.error
        assert not eseguito

    async def test_approvazione_passa_il_piano_congelato_al_handler(self) -> None:
        """§6.2: si esegue il PIANO, non gli argomenti. Il handler deve
        riceverlo, o non avrebbe modo di rispettarlo."""
        visti = []

        async def h(_a, piano=None):
            visti.append(piano)
            return ToolResult(ok=True)

        register(_tool(side_effect=True, planner=_piano, handler=h))
        set_confirm_hook(lambda piano: asyncio.sleep(0, "approvato"))
        assert (await invoke("prova", {"x": 1})).ok
        assert visti[0] is not None and visti[0].operazioni[0].tipo == "prova"

    async def test_piano_vuoto_non_chiede_conferma(self) -> None:
        """Chiedere di confermare zero operazioni addestra a cliccare si'."""
        chiamate = []

        async def piano_vuoto(_a):
            return Piano(tool="prova", riepilogo="niente", operazioni=())

        async def h(_a, _piano=None):
            return ToolResult(ok=True)

        register(_tool(side_effect=True, planner=piano_vuoto, handler=h))
        set_confirm_hook(lambda p: chiamate.append(p) or asyncio.sleep(0, "approvato"))
        r = await invoke("prova", {"x": 1})
        assert r.ok and r.output["eseguite"] == 0
        assert not chiamate, "ha chiesto conferma per un piano vuoto"
