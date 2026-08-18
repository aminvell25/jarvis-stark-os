"""Telemetria e trasporto verso Electron — SPEC §21.4 e §18.2.

Il canale e' un **socket UNIX**, non TCP: §18.2 spiega perche'. Qui contano
tre dettagli operativi che la specifica indica e che e' facile sbagliare.

**La directory e' la difesa, non il socket.** Misurato: dopo `bind()` il socket
nasce `0o775` con la umask di questo sistema. Il `chmod 0600` che segue chiude
la porta, ma fra i due c'e' una finestra. Cio' che regge davvero e' la
directory a `RUNTIME_DIR_MODE`: un socket permissivo dentro una directory non
attraversabile resta irraggiungibile.

**Il socket orfano.** Dopo un crash il file resta sul filesystem e `bind()`
fallisce con `EADDRINUSE`. Va rimosso prima di legarsi.

**La lunghezza del percorso.** `sun_path` accetta 108 byte. Il percorso di
produzione ne usa 34, ma una directory temporanea profonda lo supera, e
l'errore del kernel — "AF_UNIX path too long" — non dice a nessuno cosa fare.
Si verifica prima.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import structlog
from websockets.asyncio.server import ServerConnection, unix_serve
from websockets.exceptions import ConnectionClosed

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from core.platform import MAX_SOCKET_PATH, RUNTIME_DIR_MODE, Paths, Sensors
from core.settings import SECRETS

log = structlog.get_logger(__name__)

FAST_HZ, SLOW_HZ = 2.5, 1.0

#: Soglie di §16. Superarle emette su `agent.advisory`; nessuna soglia agisce
#: senza annunciarlo.
SOGLIA_TEMP_C = 75.0
SOGLIA_RAM_PCT = 90.0

StateProvider = Callable[[], dict[str, Any]]
InboundHandler = Callable[[dict[str, Any]], Any]


class ConfirmResponse(BaseModel):
    """L'UNICO messaggio che il core accetta in ingresso.

    Il canale non e' un canale di comandi: e' la risposta a una domanda che il
    core ha posto. `extra="forbid"` e un solo `topic` ammesso tengono la
    superficie in ingresso grande quanto serve e non un byte di piu'.
    """

    model_config = ConfigDict(extra="forbid")

    topic: Literal["fs.confirm_response"]
    id: str = Field(min_length=1, max_length=64)
    approvato: bool


def sample_fast(sensors: Sensors) -> dict[str, Any]:
    mem = sensors.memory()
    return {
        "topic": "telemetry",
        "ts": time.time(),
        "cpu_percent": sensors.cpu_percent(),
        "ram_percent": mem.percent,
        "ram_available_bytes": mem.available,
        "package_temp_c": sensors.package_temp(),
    }


def make_advisory(t: dict[str, Any], top3: list[dict]) -> dict[str, Any] | None:
    temp = t.get("package_temp_c")
    if temp is not None and temp > SOGLIA_TEMP_C:
        return {"topic": "agent.advisory", "level": "critical",
                "reason": f"package_temp>{SOGLIA_TEMP_C:.0f}C", "top3": top3}
    if t["ram_percent"] > SOGLIA_RAM_PCT:
        return {"topic": "agent.advisory", "level": "warn",
                "reason": f"ram>{SOGLIA_RAM_PCT:.0f}%"}
    return None


def _encode(msg: dict[str, Any]) -> str:
    """Serializza e **oscura ogni segreto noto** prima di mettere in rete.

    Difesa in profondita': lo `state_provider` non deve mettere chiavi nello
    snapshot, e un test lo verifica. Ma questa e' l'ultima riga prima del
    filo, e una fase futura che aggiunga un campo distratto non deve poter
    far uscire una chiave. Costa qualche `str.replace` ogni 400 ms.
    """
    return SECRETS.scrub(json.dumps(msg, default=str))


class WsServer:
    def __init__(self, state_provider: StateProvider, sensors: Sensors,
                 paths: Paths, on_confirm: InboundHandler | None = None) -> None:
        self._state_provider = state_provider
        self._sensors = sensors
        self._paths = paths
        self._on_confirm = on_confirm
        self._clients: set[ServerConnection] = set()
        self._server = None

    async def broadcast(self, msg: dict[str, Any]) -> None:
        """Manda a tutti i client collegati. Chi e' caduto viene saltato."""
        testo = _encode(msg)
        for ws in list(self._clients):
            try:
                await ws.send(testo)
            except ConnectionClosed:
                self._clients.discard(ws)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def socket_path(self) -> Path:
        return self._paths.socket_path()

    def _prepara_socket(self) -> Path:
        sock = self.socket_path
        raw = str(sock).encode()
        if len(raw) >= MAX_SOCKET_PATH:
            raise ValueError(
                f"il percorso del socket occupa {len(raw)} byte, il limite di "
                f"sun_path e' {MAX_SOCKET_PATH}: {sock}"
            )
        sock.parent.mkdir(parents=True, exist_ok=True)
        # mkdir(mode=...) non applica il modo se la directory esiste gia', e la
        # umask puo' comunque toglierne bit. Il chmod esplicito non e' ridondante.
        sock.parent.chmod(RUNTIME_DIR_MODE)
        sock.unlink(missing_ok=True)                 # socket orfano da un crash
        return sock

    async def _invia(self, ws: ServerConnection) -> None:
        # La UI e' senza stato: il core e' l'unica fonte di verita', quindi
        # ogni client riceve lo stato completo prima di qualunque delta.
        await ws.send(_encode({"topic": "state.snapshot", **self._state_provider()}))

        top3: list[dict] = []
        ultimo_lento = 0.0
        while True:
            t = sample_fast(self._sensors)
            ora = time.time()
            if ora - ultimo_lento >= 1.0 / SLOW_HZ:
                top3 = [asdict(p) for p in self._sensors.top_processes(3)]
                ultimo_lento = ora
                t["top3"] = top3
            await ws.send(_encode(t))
            if (adv := make_advisory(t, top3)) is not None:
                await ws.send(_encode(adv))
            await asyncio.sleep(1.0 / FAST_HZ)

    async def _riceve(self, ws: ServerConnection) -> None:
        """Legge dal client. Accetta un solo tipo di messaggio (§6.2).

        Un messaggio malformato si SCARTA e si registra: non chiude la
        connessione e non solleva. Un client che sbaglia a parlare non deve
        poter fermare la telemetria.
        """
        async for grezzo in ws:
            try:
                msg = ConfirmResponse.model_validate_json(grezzo)
            except (ValidationError, ValueError) as exc:
                log.warning("messaggio_in_ingresso_scartato", errore=str(exc)[:120])
                continue
            if self._on_confirm is not None:
                self._on_confirm(msg.id, msg.approvato)

    async def _handler(self, ws: ServerConnection) -> None:
        self._clients.add(ws)
        log.info("client_connesso", totale=len(self._clients))
        try:
            # Le due direzioni sono indipendenti: se il client smette di
            # ascoltare, la lettura non deve restare appesa, e viceversa.
            await asyncio.gather(self._invia(ws), self._riceve(ws))
        except ConnectionClosed:
            return
        finally:
            self._clients.discard(ws)
            log.info("client_disconnesso", totale=len(self._clients))

    async def __aenter__(self) -> WsServer:
        sock = self._prepara_socket()
        self._server = await unix_serve(self._handler, str(sock)).__aenter__()
        os.chmod(sock, 0o600)          # ridondanza: la difesa e' la directory
        log.info("ws_in_ascolto", socket=str(sock),
                 modo_dir=oct(RUNTIME_DIR_MODE))
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._server is not None:
            await self._server.__aexit__(*exc)
            self._server = None
        self.socket_path.unlink(missing_ok=True)
        log.info("ws_fermato")
