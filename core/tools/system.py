"""Tool di sistema — tutti in SOLA LETTURA.

Sono i due che §7.6 gia' instrada da T0 (`"come sta la cpu"`, `"cosa sta
rallentando"`) e che alimentano il pannello telemetria di §13.

Nessuno tocca il disco: le operazioni su file sono `core/tools/files.py`,
**Fase 2**. Qui non si anticipa.

Entrambi sono `gesture_allowed=True` perche' `side_effect=False`: leggere lo
stato del sistema non cambia nulla, e l'invariante 27 riguarda le azioni.
"""

from __future__ import annotations

from dataclasses import asdict

import structlog
from pydantic import BaseModel, Field

from core.platform import Sensors
from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)


class SystemStatusArgs(BaseModel):
    """Nessun argomento: lo stato e' lo stato."""


class TopProcessesArgs(BaseModel):
    n: int = Field(default=3, ge=1, le=20)


def register_system_tools(sensors: Sensors) -> None:
    """Registra i tool di sistema legandoli a un `Sensors`.

    I sensori arrivano per argomento invece di essere importati: e' cosi' che
    i test misurano un sistema finto senza toccare quello vero, ed e' cosi'
    che l'invariante 29 resta intatto — nessun modulo fuori da `platform/`
    sceglie da solo come si legge una CPU.
    """

    async def _system_status(_args: SystemStatusArgs) -> ToolResult:
        mem = sensors.memory()
        return ToolResult(
            ok=True,
            output={
                "cpu_percent": sensors.cpu_percent(),
                "ram_percent": mem.percent,
                "ram_available_bytes": mem.available,
                "ram_total_bytes": mem.total,
                "package_temp_c": sensors.package_temp(),
            },
        )

    async def _top_processes(args: TopProcessesArgs) -> ToolResult:
        return ToolResult(
            ok=True,
            output=[asdict(p) for p in sensors.top_processes(args.n)],
        )

    register(Tool(
        name="system_status",
        description="Uso di CPU e memoria, e temperatura del package se il sistema la espone.",
        args_schema=SystemStatusArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_system_status,
    ))
    register(Tool(
        name="top_processes",
        description="I processi che consumano piu' CPU, in ordine decrescente.",
        args_schema=TopProcessesArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_top_processes,
    ))
