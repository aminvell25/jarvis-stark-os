"""Isolamento delle chiamate specifiche di piattaforma — invariante 29.

Il resto del core importa da qui e non da `linux.py`: il giorno in cui serve
Windows si scrive `windows.py` e si estende `_impl()`, senza toccare una riga
di codice applicativo.
"""

from __future__ import annotations

import sys

from core.platform.base import (
    RUNTIME_DIR_MODE,
    AudioIO,
    Paths,
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


def sensors() -> Sensors:
    """L'implementazione di `Sensors` per questa piattaforma."""
    if sys.platform.startswith("linux"):
        from core.platform.linux import LinuxSensors

        return LinuxSensors()
    _unsupported("Sensors")


__all__ = [
    "RUNTIME_DIR_MODE",
    "AudioIO",
    "Paths",
    "SandboxRunner",
    "Sensors",
    "paths",
    "sensors",
]
