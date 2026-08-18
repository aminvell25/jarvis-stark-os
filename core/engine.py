"""Radice di composizione del core — SPEC §3.2.

Costruisce il mondo in un ordine solo e lo tiene in piedi: impostazioni,
piattaforma, allowlist, scheduler GPU, server.

Che cosa NON c'e', e non e' una dimenticanza: router, memoria, Governor, T1 e
T2 sono Fase 4; wake, STT e TTS sono Fase 3; le operazioni su file sono
Fase 2. Il `CLAUDE.md` dice di lavorare una fase per volta.
"""

from __future__ import annotations

import asyncio
import os
import signal
import time
from typing import Any

import structlog

from core.gpu_scheduler import GpuScheduler
from core.platform import Paths, gpu as platform_gpu, paths as platform_paths, sensors as platform_sensors
from core.platform.linux_sandbox import SECCOMP_APPLICATO
from core.settings import Settings, SettingsStore
from core.agents_mesh import snapshot as mesh_snapshot
from core.llm import grammar
from core.tools import registry
from core.tools.confirm import ConfirmBroker
from core.tools.files import register_file_tools
from core.tools.geo import register_geo_tools
from core.tools.web import register_web_tools
from core.tools.system import register_system_tools
from core.ws_server import WsServer

log = structlog.get_logger(__name__)

FASE = 1


class Engine:
    """Il core in esecuzione."""

    def __init__(self, paths: Paths | None = None) -> None:
        self._paths = paths or platform_paths()
        self._avvio = time.monotonic()

        self._store = SettingsStore(self._paths)
        self._sensors = platform_sensors()
        self._gpu_scheduler = GpuScheduler(platform_gpu(), self._sensors)

        # La radice di composizione POSSIEDE l'allowlist: e' lei a decidere
        # che cosa esiste. Svuotare prima di registrare rende l'avvio
        # idempotente senza nascondere i doppioni dentro una fase.
        registry.clear()
        register_system_tools(self._sensors)
        register_geo_tools()
        # `pubblica` chiude la catena tool -> socket -> pannello. Il WS
        # nasce dopo, quindi si passa una lambda e non il metodo.
        register_web_tools(lambda: self._store.current,
                           lambda msg: self._ws.broadcast(msg))
        register_file_tools(lambda: self._store.current, lambda: self._paths)

        self._ws = WsServer(
            self.state_snapshot, self._sensors, self._paths,
            on_confirm=lambda rid, ok: self._broker.rispondi(rid, ok),
            mesh_provider=self.agents_mesh,
        )

        # Il broker pubblica sul socket, e il registry gli chiede il permesso
        # prima di ogni tool distruttivo. Senza questo collegamento i tool con
        # side_effect NON funzionano (fail-closed): e' il verso giusto.
        self._broker = ConfirmBroker(self._ws.broadcast)
        registry.set_confirm_hook(self._broker.richiedi)
        self._stop = asyncio.Event()

    # ── stato ────────────────────────────────────────────────────────────────

    @property
    def settings(self) -> Settings:
        return self._store.current

    @property
    def uptime_s(self) -> float:
        return time.monotonic() - self._avvio

    def agents_mesh(self) -> dict[str, Any]:
        """Il grafo degli agenti per il pannello di §13.

        T1 e T2 non sono composti qui — vivono nella pipeline vocale — e la
        mesh lo dice: `non collegato`, non `inerte`. La differenza e' quella
        fra «non c'e'» e «c'e' e non sta facendo niente», e su un pannello di
        stato e' l'informazione principale.
        """
        return mesh_snapshot(
            regole_t0=len(grammar.regole()),
            tool_registrati=len(registry.describe_all()),
        )

    def state_snapshot(self) -> dict[str, Any]:
        """Lo stato completo per un client che si collega.

        ⚠️ **Nessun segreto.** Le chiavi compaiono per NOME, mai per valore:
        `Secrets.present()` restituisce i nomi valorizzati. Il rimando a
        `settings.model_dump()` porterebbe con se' i `SecretStr`, ed e' il
        modo esatto in cui una chiave finirebbe sul filo.
        """
        s = self.settings
        misura = self._gpu_scheduler.headroom()
        gpu_mem = misura[1]
        return {
            "fase": FASE,
            "core": {
                "pid": os.getpid(),
                "uptime_s": round(self.uptime_s, 1),
                "seccomp": SECCOMP_APPLICATO,
            },
            "ws": {
                "socket": str(self._ws.socket_path),
                "clients": self._ws.client_count,
            },
            "settings": {
                "voice": {
                    "stt_provider": s.voice.stt_provider,
                    "tts_provider": s.voice.tts_provider,
                    "fallback_on_error": s.voice.fallback_on_error,
                },
                "llm": {"backend": s.llm.backend, "t1_model": s.llm.t1_model},
                "fs": {
                    "workspace": str(s.fs.workspace),
                    "allowed_roots": [str(p) for p in s.fs.allowed_roots],
                    "trash_only": s.fs.trash_only,
                },
                "ui": {"target_fps": s.ui.target_fps, "grid_px": s.ui.grid_px},
                "chiavi_presenti": sorted(s.secrets.present()),   # NOMI, non valori
            },
            "tools": registry.describe_all(),
            "gpu": (
                {
                    "driver": gpu_mem.driver,
                    "total_bytes": gpu_mem.total,
                    "used_bytes": gpu_mem.used,
                    "unified": gpu_mem.unified,
                    "headroom_bytes": misura[0],
                }
                if gpu_mem is not None
                else None
            ),
        }

    # ── ciclo di vita ────────────────────────────────────────────────────────

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._chiedi_stop, sig)

        self._store.start()
        try:
            async with self._ws:
                log.info(
                    "core_avviato",
                    fase=FASE,
                    pid=os.getpid(),
                    socket=str(self._ws.socket_path),
                    tool=registry.names(),
                    seccomp=SECCOMP_APPLICATO,
                )
                await self._stop.wait()
        finally:
            self._store.stop()
            log.info("core_fermato", uptime_s=round(self.uptime_s, 1))

    def _chiedi_stop(self, sig: signal.Signals) -> None:
        log.info("segnale_ricevuto", segnale=sig.name)
        self._stop.set()


async def main() -> None:
    await Engine().run()


if __name__ == "__main__":
    asyncio.run(main())
