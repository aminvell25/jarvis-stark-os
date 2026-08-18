"""core/ws_server — SPEC §21.4 e §18.2."""

from __future__ import annotations

import asyncio
import json
import stat

import pytest
from websockets.asyncio.client import unix_connect

from core.platform import RUNTIME_DIR_MODE
from core.settings import SECRETS
from core.ws_server import SOGLIA_RAM_PCT, SOGLIA_TEMP_C, WsServer, make_advisory
from tests.conftest import FakeSensors


async def _attendi(condizione, timeout: float = 5.0) -> bool:
    """Attende che `condizione()` sia vera.

    Non `sleep(0.1)`: il server si accorge di una disconnessione solo al `send`
    successivo, che con FAST_HZ=2.5 puo' arrivare 0,4 s dopo. Un'attesa fissa
    tarata sul caso medio produce un test che passa sulla propria macchina e
    fallisce a caso altrove.
    """
    scadenza = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < scadenza:
        if condizione():
            return True
        await asyncio.sleep(0.02)
    return condizione()


async def _leggi(sock, n: int) -> list[dict]:
    async with unix_connect(str(sock)) as ws:
        return [json.loads(await asyncio.wait_for(ws.recv(), 10)) for _ in range(n)]


class TestTrasporto:
    async def test_snapshot_poi_telemetria(self, short_paths) -> None:
        """Criterio di §22: un client esterno riceve snapshot e telemetria."""
        srv = WsServer(lambda: {"prova": True}, FakeSensors(), short_paths)
        async with srv:
            msgs = await _leggi(srv.socket_path, 3)
        assert msgs[0]["topic"] == "state.snapshot" and msgs[0]["prova"] is True
        assert all(m["topic"] == "telemetry" for m in msgs[1:])

    async def test_la_telemetria_riporta_i_valori_misurati(self, short_paths) -> None:
        srv = WsServer(dict, FakeSensors(cpu=33.0, ram_percent=44.0, temp=51.0),
                       short_paths)
        async with srv:
            t = (await _leggi(srv.socket_path, 2))[1]
        assert (t["cpu_percent"], t["ram_percent"], t["package_temp_c"]) == (33.0, 44.0, 51.0)

    async def test_conta_i_client(self, short_paths) -> None:
        srv = WsServer(dict, FakeSensors(), short_paths)
        async with srv:
            assert srv.client_count == 0
            async with unix_connect(str(srv.socket_path)) as ws:
                await ws.recv()
                assert await _attendi(lambda: srv.client_count == 1)
            assert await _attendi(lambda: srv.client_count == 0)


class TestSicurezzaDelSocket:
    async def test_directory_a_0700(self, short_paths) -> None:
        """§18.2: la directory e' la difesa, non i permessi del socket."""
        srv = WsServer(dict, FakeSensors(), short_paths)
        async with srv:
            modo = stat.S_IMODE(srv.socket_path.parent.stat().st_mode)
        assert modo == RUNTIME_DIR_MODE

    async def test_socket_a_0600(self, short_paths) -> None:
        srv = WsServer(dict, FakeSensors(), short_paths)
        async with srv:
            assert stat.S_IMODE(srv.socket_path.stat().st_mode) == 0o600

    async def test_socket_rimosso_alla_chiusura(self, short_paths) -> None:
        srv = WsServer(dict, FakeSensors(), short_paths)
        async with srv:
            assert srv.socket_path.exists()
        assert not srv.socket_path.exists()

    async def test_socket_orfano_non_blocca_lavvio(self, short_paths) -> None:
        """Dopo un crash il file resta e `bind()` darebbe EADDRINUSE."""
        sock = short_paths.socket_path()
        sock.parent.mkdir(parents=True, exist_ok=True)
        sock.write_text("residuo di un crash")
        srv = WsServer(dict, FakeSensors(), short_paths)
        async with srv:
            assert srv.socket_path.is_socket()

    async def test_percorso_troppo_lungo_e_un_errore_chiaro(self, tmp_path) -> None:
        """`sun_path` accetta 108 byte; oltre, il kernel dice solo "AF_UNIX
        path too long", che non aiuta nessuno."""
        from tests.conftest import FakePaths

        profondo = tmp_path / ("x" * 90) / ("y" * 60)
        with pytest.raises(ValueError, match="sun_path"):
            async with WsServer(dict, FakeSensors(), FakePaths(profondo)):
                pass


class TestNessunSegretoSulFilo:
    async def test_una_chiave_nello_snapshot_viene_oscurata(self, short_paths) -> None:
        """Difesa in profondita': lo `state_provider` non deve mettere chiavi
        nello snapshot, ma se una fase futura lo facesse per distrazione, non
        deve poter uscire dal socket."""
        CHIAVE = "dg_chiave_che_non_deve_uscire_0f9e"
        SECRETS.register(CHIAVE)
        srv = WsServer(lambda: {"config": f"token={CHIAVE}"}, FakeSensors(), short_paths)
        async with srv:
            async with unix_connect(str(srv.socket_path)) as ws:
                grezzo = await asyncio.wait_for(ws.recv(), 10)
        assert CHIAVE not in grezzo
        assert "REDACTED" in grezzo


class TestSoglie:
    def test_temperatura_critica(self) -> None:
        a = make_advisory({"package_temp_c": SOGLIA_TEMP_C + 1, "ram_percent": 10.0}, [])
        assert a["level"] == "critical"

    def test_ram_alta(self) -> None:
        a = make_advisory({"package_temp_c": 40.0, "ram_percent": SOGLIA_RAM_PCT + 1}, [])
        assert a["level"] == "warn"

    def test_nessuna_soglia_superata(self) -> None:
        assert make_advisory({"package_temp_c": 40.0, "ram_percent": 10.0}, []) is None

    def test_temperatura_assente_non_scatta(self) -> None:
        """Su Windows psutil non espone le temperature (§23): `None` non deve
        essere confuso con "freddo" ne' far scattare l'allarme."""
        assert make_advisory({"package_temp_c": None, "ram_percent": 10.0}, []) is None
