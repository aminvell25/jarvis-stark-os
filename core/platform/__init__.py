"""Isolamento delle chiamate specifiche di piattaforma — invariante 29.

Il resto del core importa da qui e non da `linux.py`: il giorno in cui serve
Windows si scrive `windows.py` e si estende `_impl()`, senza toccare una riga
di codice applicativo.
"""

from __future__ import annotations

import sys
from pathlib import Path

from core.platform.base import (
    MAX_SOCKET_PATH,
    RUNTIME_DIR_MODE,
    AudioIO,
    Gpu,
    GpuMemory,
    MemoryInfo,
    Paths,
    ProcessInfo,
    SandboxRunner,
    Sensors,
)


def _unsupported(component: str):
    raise NotImplementedError(
        f"{component} non ha un'implementazione per la piattaforma "
        f"{sys.platform!r}. SPEC §23: Linux e' il target attuale, Windows e' "
        f"previsto e va scritto in core/platform/windows.py."
    )


def paths() -> Paths:
    """L'implementazione di `Paths` per questa piattaforma."""
    if sys.platform.startswith("linux"):
        from core.platform.linux import LinuxPaths

        return LinuxPaths()
    _unsupported("Paths")


def scrivi_atomico(percorso: Path, testo: str) -> None:
    """Scrittura per rinomina, coi permessi conservati. Invariante 29.

    Una funzione e non una classe: non ha stato, e `Paths` e' gia' il posto
    delle DOMANDE sul filesystem — dove sta una cosa — mentre questa e' un
    modo di scriverci.
    """
    if sys.platform.startswith("linux"):
        from core.platform.linux import scrivi_atomico_linux

        return scrivi_atomico_linux(percorso, testo)
    _unsupported("scrivi_atomico")


def sensors() -> Sensors:
    """L'implementazione di `Sensors` per questa piattaforma."""
    if sys.platform.startswith("linux"):
        from core.platform.linux import LinuxSensors

        return LinuxSensors()
    _unsupported("Sensors")


def audio() -> AudioIO:
    """L'implementazione di `AudioIO` per questa piattaforma."""
    if sys.platform.startswith("linux"):
        from core.platform.linux_audio import LinuxAudioIO

        return LinuxAudioIO()
    _unsupported("AudioIO")


def gpu() -> Gpu:
    """L'implementazione di `Gpu` per questa piattaforma."""
    if sys.platform.startswith("linux"):
        from core.platform.linux import LinuxGpu

        return LinuxGpu()
    _unsupported("Gpu")


def sandbox_runner(allowed_roots: list[Path]) -> SandboxRunner:
    """L'implementazione di `SandboxRunner` per questa piattaforma."""
    if sys.platform.startswith("linux"):
        from core.platform.linux_sandbox import LinuxSandboxRunner

        return LinuxSandboxRunner(allowed_roots)
    _unsupported("SandboxRunner")


def interprete_freecad() -> Path | None:
    """Il FreeCAD headless di questa piattaforma, se c'e' (ADR-015, fetta 5).
    Su Linux e' il snap; su Windows sara' un `.exe`, e questo nome non cambia."""
    if sys.platform.startswith("linux"):
        from core.platform.linux_snap import interprete_freecad as _linux

        return _linux()
    return None


__all__ = [
    "MAX_SOCKET_PATH",
    "RUNTIME_DIR_MODE",
    "AudioIO",
    "Gpu",
    "GpuMemory",
    "MemoryInfo",
    "Paths",
    "ProcessInfo",
    "SandboxRunner",
    "Sensors",
    "audio",
    "gpu",
    "interprete_freecad",
    "paths",
    "sandbox_runner",
    "sensors",
]
