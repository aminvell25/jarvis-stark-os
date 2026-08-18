"""core/engine — la radice di composizione."""

from __future__ import annotations

import asyncio

import pytest

from core.engine import Engine
from core.settings import SECRETS
from core.tools import registry
from tests.conftest import SECRETS_TOML


@pytest.fixture
def engine(short_paths) -> Engine:
    return Engine(short_paths)


class TestComposizione:
    def test_registra_i_tool_di_sistema(self, engine: Engine) -> None:
        assert registry.names() == ["system_status", "top_processes"]

    def test_costruire_due_volte_non_esplode(self, short_paths) -> None:
        """La radice di composizione POSSIEDE l'allowlist: ricostruirla la
        ridefinisce, non ci accumula sopra un doppione."""
        Engine(short_paths)
        Engine(short_paths)
        assert registry.names() == ["system_status", "top_processes"]

    def test_carica_le_impostazioni(self, engine: Engine) -> None:
        assert engine.settings.llm.backend == "claude_code"


class TestSnapshot:
    def test_ha_le_sezioni_attese(self, engine: Engine) -> None:
        snap = engine.state_snapshot()
        assert set(snap) >= {"fase", "core", "ws", "settings", "tools", "gpu"}
        assert snap["fase"] == 1

    def test_espone_i_tool_senza_handler(self, engine: Engine) -> None:
        assert {t["name"] for t in engine.state_snapshot()["tools"]} == {
            "system_status", "top_processes"
        }

    def test_le_chiavi_compaiono_per_nome_non_per_valore(self, engine: Engine) -> None:
        chiave = SECRETS_TOML.split('"')[1]
        SECRETS.register(chiave)
        import json

        grezzo = json.dumps(engine.state_snapshot(), default=str)
        assert "deepgram_api_key" in grezzo, "il NOME deve esserci"
        assert chiave not in grezzo, "il VALORE non deve esserci"

    def test_dichiara_seccomp(self, engine: Engine) -> None:
        assert engine.state_snapshot()["core"]["seccomp"] is False


class TestCicloDiVita:
    async def test_avvio_e_chiusura_ordinata(self, engine: Engine) -> None:
        task = asyncio.create_task(engine.run())
        sock = engine.state_snapshot()["ws"]["socket"]
        from pathlib import Path

        for _ in range(200):
            if Path(sock).is_socket():
                break
            await asyncio.sleep(0.02)
        assert Path(sock).is_socket(), "il socket non e' stato creato"

        engine._stop.set()
        await asyncio.wait_for(task, timeout=10)
        assert not Path(sock).exists(), "il socket non e' stato rimosso"
