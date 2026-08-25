"""ADR-007 nel processo vero — l'ultimo miglio.

Gli eval di `eval_mcp.py` provano il cancello. Questo prova che il cancello è
**montato**: che `settings.toml` accende dei server, che i tool nominati
diventano invocabili, e che quelli non nominati no.

Senza, `client.py` e `promozione.py` sarebbero una libreria che nessuno chiama.
È il difetto incontrato cinque volte in due giorni — i quattro tool di memoria
di §13, il `Watcher` delle news, `_gradi()` che componeva solo T1,
`PhraseWake.set_frasi()`, l'azione vocale su un topic morto. Ogni volta: due
pezzi scritti, provati, e mai congiunti.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core.mcp.montaggio import monta
from core.settings import McpServer, McpSettings, McpToolPromosso
from core.tools import registry

FINTO = Path(__file__).resolve().parent / "mcp_finto.py"


def _server(nome: str, personalita: str, promossi=()) -> McpServer:
    return McpServer(
        nome=nome,
        comando=[sys.executable, str(FINTO), personalita],
        promossi=[McpToolPromosso(tool=t, side_effect=se) for t, se in promossi],
    )


@pytest.fixture
def pulito():
    registry.clear()
    yield
    registry.clear()


class TestSpentoNonAvviaNIENTE:
    async def test_predefinito_spento(self) -> None:
        """Come voce, codice e vision: montare un server MCP vuol dire avviare
        un programma di terzi, e non si fa per distrazione."""
        assert McpSettings().enabled is False

    async def test_con_enabled_falso_nessun_processo(self, pulito) -> None:
        m = await monta(McpSettings(enabled=False,
                                    servers=[_server("a", "onesto", [("ping", False)])]))
        assert m.server == [] and m.promossi == []
        assert registry.names() == []


class TestAccesoMONTA:
    async def test_il_tool_nominato_diventa_invocabile(self, pulito) -> None:
        m = await monta(McpSettings(enabled=True,
                                    servers=[_server("a", "onesto", [("somma", False)])]))
        try:
            assert registry.names() == ["mcp_a_somma"]
            esito = await registry.invoke("mcp_a_somma", {"a": 20, "b": 22})
            assert esito.ok and "42" in esito.output["contenuto"]
        finally:
            await m.ferma()

    async def test_quello_NON_nominato_resta_fuori(self, pulito) -> None:
        """`ping` è annunciato quanto `somma`. Il file ne nomina uno."""
        m = await monta(McpSettings(enabled=True,
                                    servers=[_server("a", "onesto", [("somma", False)])]))
        try:
            assert registry.get("mcp_a_ping") is None
            assert "ping" in m.server[0].nomi_annunciati()
        finally:
            await m.ferma()

    async def test_un_server_senza_promossi_e_uno_stato_UTILE(self, pulito) -> None:
        """Si avvia, si guarda cosa propone, e non se ne usa niente: è come si
        guarda un server prima di fidarsene."""
        m = await monta(McpSettings(enabled=True, servers=[_server("a", "onesto")]))
        try:
            assert len(m.server) == 1
            assert m.server[0].nomi_annunciati() == {"ping", "somma"}
            assert registry.names() == []
        finally:
            await m.ferma()


class TestUnGuastoNONfermaJARVIS:
    async def test_un_server_che_non_parte_e_REGISTRATO_non_sollevato(
            self, pulito) -> None:
        cattivo = McpServer(nome="rotto",
                            comando=[sys.executable, "/non/esiste/mai.py"],
                            promossi=[])
        m = await monta(McpSettings(enabled=True, servers=[cattivo]))
        try:
            assert m.server == []
            assert len(m.guasti) == 1 and m.guasti[0]["server"] == "rotto"
        finally:
            await m.ferma()

    async def test_gli_ALTRI_server_si_montano_lo_stesso(self, pulito) -> None:
        cattivo = McpServer(nome="rotto", comando=[sys.executable, "/non/esiste.py"])
        m = await monta(McpSettings(
            enabled=True,
            servers=[cattivo, _server("buono", "onesto", [("ping", False)])]))
        try:
            assert [s.nome for s in m.server] == ["buono"]
            assert registry.names() == ["mcp_buono_ping"]
        finally:
            await m.ferma()

    async def test_una_promozione_impossibile_e_un_GUASTO_non_un_crollo(
            self, pulito) -> None:
        """Il file nomina un tool che il server non annuncia — un refuso, o un
        server che è cambiato sotto. Si registra e si tira avanti."""
        m = await monta(McpSettings(
            enabled=True,
            servers=[_server("a", "onesto", [("somma", False), ("inesistente", False)])]))
        try:
            assert registry.names() == ["mcp_a_somma"]
            assert len(m.guasti) == 1 and m.guasti[0]["tool"] == "inesistente"
        finally:
            await m.ferma()

    async def test_uno_schema_illeggibile_e_un_GUASTO(self, pulito) -> None:
        m = await monta(McpSettings(
            enabled=True,
            servers=[_server("a", "illeggibile", [("complicato", False)])]))
        try:
            assert registry.names() == []
            assert len(m.guasti) == 1 and "array" in m.guasti[0]["errore"]
        finally:
            await m.ferma()


class TestLaCatenaEATTACCATA:
    """Le giunzioni: schema, radice di composizione, spegnimento, snapshot."""

    def _engine_py(self) -> str:
        return (Path(__file__).resolve().parent.parent / "core" / "engine.py"
                ).read_text(encoding="utf-8")

    def test_la_radice_di_composizione_lo_monta(self) -> None:
        s = self._engine_py()
        assert "monta_mcp(s.mcp)" in s, (
            "nessuno monta i server: `client.py` e `promozione.py` sarebbero "
            "una libreria che nessuno chiama"
        )

    def test_lo_spegnimento_FERMA_i_server(self) -> None:
        """Sono processi figli: senza, sopravviverebbero al core."""
        s = self._engine_py()
        dopo = s.split("async def _spegni_gradi", 1)[1].split("\n    async def", 1)[0]
        assert "self._mcp.ferma()" in dopo

    def test_lo_snapshot_dice_anche_i_GUASTI(self) -> None:
        s = self._engine_py()
        assert '"mcp": (self._mcp.stato()' in s
        montaggio = (Path(__file__).resolve().parent.parent / "core" / "mcp"
                     / "montaggio.py").read_text(encoding="utf-8")
        assert '"guasti"' in montaggio, (
            "un montaggio fallito che non lascia traccia è un tool che non c'è "
            "senza che nessuno sappia perché"
        )

    def test_mcp_enabled_NON_si_cambia_dall_interfaccia(self) -> None:
        """Sesta bloccata di §26.7: accenderla avvia programmi di terzi.

        ⚠️ Si legge il `Settings` VERO invece di costruirne uno a mano. La
        prima versione lo componeva campo per campo ed è caduta su
        `llm.t1_cwd`, che non c'entra niente con MCP: un test che riscrive lo
        schema si rompe ogni volta che lo schema cresce, e la sua rottura non
        dice nulla di ciò che sorveglia.
        """
        from core.settings import load_settings
        from core.tools.impostazioni import BLOCCATE, chiavi_bloccate, chiavi_modificabili

        assert "mcp.enabled" in BLOCCATE
        s = load_settings()
        assert "mcp.enabled" not in chiavi_modificabili(s)
        assert chiavi_bloccate(s)["mcp.enabled"] is False

    def test_i_server_non_sono_MODIFICABILI_dalla_pagina(self) -> None:
        """`mcp.servers` è una struttura: `imposta_valore` scrive foglie, e
        offrirla produrrebbe un errore a metà scrittura invece di un rifiuto.
        Un comando che a un server MCP si aggiunge cliccando sarebbe la strada
        più corta per montarne uno ostile."""
        from core.settings import load_settings
        from core.tools.impostazioni import chiavi_modificabili

        assert "mcp.servers" not in chiavi_modificabili(load_settings())
