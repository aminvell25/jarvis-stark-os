"""Implementazione Linux delle interfacce di `base.py` — SPEC §23.

Solo `LinuxPaths` e `LinuxSensors` sono implementati. Sandbox e audio
appartengono alla Fase 1 e alla Fase 3: qui esistono e sollevano
`NotImplementedError`.

Uno stub che solleva e' preferibile a uno che ritorna un valore plausibile.
Il secondo fa passare i test e fallisce in esercizio, che e' il modo peggiore
di scoprire che un pezzo non c'e' ancora.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

import psutil
import structlog

log = structlog.get_logger(__name__)

_APP = "jarvis-os"

#: Chiavi di `psutil.sensors_temperatures()` che riportano il package CPU, in
#: ordine di preferenza: AMD espone `k10temp` o `zenpower`, Intel `coretemp`.
#: L'elenco viene da SPEC §21.4.
_TEMP_KEYS = ("k10temp", "coretemp", "zenpower")


def _xdg(var: str, default: Path) -> Path:
    """Legge una variabile XDG ignorando i valori relativi.

    La specifica XDG impone di trattare un percorso relativo come se la
    variabile non fosse impostata. Non e' pedanteria: senza questo controllo
    un valore relativo verrebbe risolto rispetto alla working directory del
    processo, e la working directory di T1 e' deliberatamente una directory
    vuota (SPEC §5.2). Un `XDG_CONFIG_HOME=.config` malposto farebbe cercare
    le impostazioni dentro `voice-cwd`, che deve restare vuota.
    """
    raw = os.environ.get(var, "")
    candidate = Path(raw)
    return candidate if raw and candidate.is_absolute() else default


class LinuxPaths:
    """XDG Base Directory Specification."""

    def config_dir(self) -> Path:
        return _xdg("XDG_CONFIG_HOME", Path.home() / ".config") / _APP

    def data_dir(self) -> Path:
        return _xdg("XDG_DATA_HOME", Path.home() / ".local" / "share") / _APP

    def workspace(self) -> Path:
        return Path.home() / "JARVIS"

    def runtime_dir(self) -> Path:
        """`$XDG_RUNTIME_DIR/jarvis-os`, con fallback annunciato.

        `$XDG_RUNTIME_DIR` e' la sede giusta: tmpfs, gia' 0700, ripulita al
        logout. Se manca — sessione non-systemd, cron, container spoglio — si
        ricade su una directory temporanea per uid, e lo si dichiara: SPEC §16
        vieta le degradazioni silenziose, e questa tocca la sede del socket di
        controllo, cioe' il confine di sicurezza fra core ed Electron.
        """
        raw = os.environ.get("XDG_RUNTIME_DIR", "")
        if raw and Path(raw).is_absolute():
            return Path(raw) / _APP

        fallback = Path(tempfile.gettempdir()) / f"{_APP}-{os.getuid()}"
        log.warning(
            "xdg_runtime_dir_assente",
            fallback=str(fallback),
            conseguenza="il socket di controllo nasce fuori da $XDG_RUNTIME_DIR",
        )
        return fallback

    def socket_path(self) -> Path:
        """Socket UNIX di controllo. Vedi `base.Paths.socket_path` per la
        divergenza dichiarata rispetto a SPEC §21.4."""
        return self.runtime_dir() / "core.sock"

    def is_private(self, path: Path) -> bool:
        """Vero se ne' gruppo ne' altri hanno alcun permesso.

        Solleva se il file non esiste: l'esistenza la verifica il chiamante,
        che sa se un file assente e' un errore o un caso previsto.
        """
        return not (path.stat().st_mode & 0o077)


class LinuxSensors:
    """Sensori via psutil."""

    def package_temp(self) -> float | None:
        getter = getattr(psutil, "sensors_temperatures", None)
        if getter is None:                      # non esiste su ogni piattaforma
            return None
        temps = getter()
        for key in _TEMP_KEYS:
            if entries := temps.get(key):
                return max(entry.current for entry in entries)
        return None


class LinuxSandboxRunner:
    """bubblewrap + seccomp. SPEC §3.4 — **Fase 1**."""

    async def run(
        self,
        argv: list[str],
        rw_paths: list[Path],
        timeout: float,
    ) -> tuple[int, str, str]:
        raise NotImplementedError(
            "Sandbox non cablata: bubblewrap arriva in Fase 1 (SPEC §22)."
        )


class LinuxAudioIO:
    """PipeWire. SPEC §7 — **Fase 3**."""

    async def input_stream(self, sample_rate: int) -> AsyncIterator[bytes]:
        raise NotImplementedError(
            "Ingresso audio non cablato: PipeWire arriva in Fase 3 (SPEC §22)."
        )

    async def play(self, pcm: bytes, sample_rate: int) -> None:
        raise NotImplementedError(
            "Uscita audio non cablata: PipeWire arriva in Fase 3 (SPEC §22)."
        )
