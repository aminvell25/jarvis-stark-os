"""Implementazione Linux delle interfacce di `base.py` — SPEC §23.

`LinuxPaths`, `LinuxSensors` e `LinuxGpu` sono implementati. La sandbox vive
in `linux_sandbox.py`, separata perche' e' il file che Windows riscrive da
zero. L'audio e' Fase 3 e qui solleva `NotImplementedError`.

Uno stub che solleva e' preferibile a uno che ritorna un valore plausibile.
Il secondo fa passare i test e fallisce in esercizio, che e' il modo peggiore
di scoprire che un pezzo non c'e' ancora.
"""

from __future__ import annotations

import os
import tempfile
from urllib.parse import unquote
from pathlib import Path
from typing import AsyncIterator

import psutil
import structlog

from core.platform.base import GpuMemory, MemoryInfo, ProcessInfo

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
        """Socket UNIX di controllo. SPEC §18.2; il perche' e le conseguenze
        stanno in `base.Paths.socket_path`."""
        return self.runtime_dir() / "core.sock"

    def _punto_di_mount(self, p: Path) -> Path:
        p = p.resolve()
        dev = p.stat().st_dev
        while p != p.parent and p.parent.stat().st_dev == dev:
            p = p.parent
        return p

    def trash_dir_for(self, path: Path) -> Path | None:
        """Regola XDG. Misurata su questa macchina: `~/JARVIS` va nel cestino
        della home, `/tmp/...` va in `/tmp/.Trash-<uid>/`."""
        try:
            p = Path(path).expanduser().resolve()
            riferimento = p if p.exists() else p.parent
            if riferimento.stat().st_dev == Path.home().stat().st_dev:
                return self.data_home_trash()
            return self._punto_di_mount(riferimento) / f".Trash-{os.getuid()}"
        except OSError:
            return None

    def find_trashed(self, original: Path) -> Path | None:
        """Cerca nel registro XDG l'elemento il cui `Path=` e' `original`.

        Il formato di `<nome>.trashinfo` e':

            [Trash Info]
            Path=/home/utente/file.txt      (percorso-codificato)
            DeletionDate=2026-08-18T13:00:00

        ⚠️ **`Path=` non e' sempre assoluto.** Nel cestino della home lo e';
        in un cestino per-mount (`<mount>/.Trash-<uid>`) la specifica XDG
        consente di registrarlo RELATIVO al punto di mount, e in pratica e'
        cosi': `Path=cartella/file.txt`. Misurato — un file in
        `/tmp/x/f.txt` viene registrato come `x/f.txt`. Confrontarlo sempre
        con l'assoluto non trova mai nulla su un filesystem diverso dalla
        home, ed e' il caso in cui questo codice serve di piu'.

        Si prende il piu' recente, perche' lo stesso percorso puo' essere
        stato cestinato piu' volte.
        """
        cestino = self.trash_dir_for(original)
        if cestino is None:
            return None
        atteso = str(Path(original).expanduser().resolve())
        migliore, quando = None, ""
        try:
            for info in (cestino / "info").glob("*.trashinfo"):
                percorso, data = None, ""
                for riga in info.read_text(encoding="utf-8", errors="replace").splitlines():
                    if riga.startswith("Path="):
                        percorso = unquote(riga[5:].strip())
                    elif riga.startswith("DeletionDate="):
                        data = riga[13:].strip()
                if percorso is None:
                    continue
                # Relativo -> lo si ancora al punto di mount, che e' il
                # genitore della directory di cestino.
                assoluto = (
                    percorso if percorso.startswith("/")
                    else str((cestino.parent / percorso).resolve())
                )
                if assoluto == atteso and data >= quando:
                    quando = data
                    candidato = cestino / "files" / info.name[: -len(".trashinfo")]
                    migliore = candidato if candidato.exists() else None
        except OSError:
            return None
        return migliore

    def data_home_trash(self) -> Path:
        return _xdg("XDG_DATA_HOME", Path.home() / ".local" / "share") / "Trash"

    def is_private(self, path: Path) -> bool:
        """Vero se ne' gruppo ne' altri hanno alcun permesso.

        Solleva se il file non esiste: l'esistenza la verifica il chiamante,
        che sa se un file assente e' un errore o un caso previsto.
        """
        return not (path.stat().st_mode & 0o077)


class LinuxSensors:
    """Misura di sistema via psutil.

    La cache dei `Process` e' persistente e non e' un'ottimizzazione: SPEC
    §21.4 documenta che `process_iter` ricrea gli oggetti a ogni giro e
    azzera il contatore di `cpu_percent`, che diventa quindi inaffidabile.
    Riusare gli stessi oggetti e' l'unico modo per leggere un numero vero.
    """

    def __init__(self) -> None:
        self._proc_cache: dict[int, psutil.Process] = {}
        # Innesca il contatore aggregato: senza questa chiamata la PRIMA
        # lettura di cpu_percent() torna 0.0, che sembra un sistema a riposo.
        psutil.cpu_percent(None)

    def cpu_percent(self) -> float:
        return psutil.cpu_percent(None)

    def memory(self) -> MemoryInfo:
        vm = psutil.virtual_memory()
        return MemoryInfo(total=vm.total, available=vm.available, percent=vm.percent)

    def top_processes(self, n: int = 3) -> list[ProcessInfo]:
        vivi: set[int] = set()
        for p in psutil.process_iter(["pid"]):
            pid = p.info["pid"]
            vivi.add(pid)
            if pid not in self._proc_cache:
                try:
                    proc = psutil.Process(pid)
                    proc.cpu_percent(None)          # innesca il contatore
                    self._proc_cache[pid] = proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        for morto in set(self._proc_cache) - vivi:
            self._proc_cache.pop(morto, None)

        righe: list[ProcessInfo] = []
        for pid, proc in list(self._proc_cache.items()):
            try:
                righe.append(ProcessInfo(pid=pid, name=proc.name(),
                                         cpu=proc.cpu_percent(None)))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._proc_cache.pop(pid, None)
        righe.sort(key=lambda r: r.cpu, reverse=True)
        return righe[:n]

    def package_temp(self) -> float | None:
        getter = getattr(psutil, "sensors_temperatures", None)
        if getter is None:                      # non esiste su ogni piattaforma
            return None
        temps = getter()
        for key in _TEMP_KEYS:
            if entries := temps.get(key):
                return max(entry.current for entry in entries)
        return None


#: Classe PCI delle GPU AMD integrate. Le discrete si presentano come
#: 0x030000 ("VGA compatible controller"), le integrate come 0x038000
#: ("Display controller").
_PCI_CLASS_DISPLAY_CONTROLLER = 0x038000


class LinuxGpu:
    """Memoria GPU da sysfs (`amdgpu`). Nessun `nvidia-smi` in Fase 1.

    Come si riconosce la memoria unificata. Non esiste un flag del kernel che
    lo dica, quindi si usano due segnali:

    1. la classe PCI `0x038000` — le AMD integrate si presentano cosi'
    2. `vis_vram_total == vram_total` — su una APU tutta la memoria e' visibile
       dalla CPU perche' E' RAM di sistema (indizio piu' debole: con
       Resizable BAR anche una discreta puo' presentarsi cosi')

    **Nel dubbio si assume unificata.** Sbagliare in questa direzione fa
    rifiutare un caricamento che sarebbe entrato; sbagliare nell'altra manda
    il sistema in swap con `gpu_scheduler` che riporta verde (§9, rev 5.2).
    """

    _RADICE = Path("/sys/class/drm")

    def _leggi(self, dev: Path, nome: str) -> int | None:
        try:
            return int((dev / nome).read_text().strip())
        except (OSError, ValueError):
            return None

    def _dispositivi(self) -> list[Path]:
        try:
            schede = sorted(self._RADICE.glob("card[0-9]*"))
        except OSError:
            return []
        return [c / "device" for c in schede
                if (c / "device" / "mem_info_vram_total").exists()]

    def memory(self) -> GpuMemory | None:
        for dev in self._dispositivi():
            total = self._leggi(dev, "mem_info_vram_total")
            used = self._leggi(dev, "mem_info_vram_used")
            if total is None or used is None:
                continue

            driver = "sconosciuto"
            try:
                for riga in (dev / "uevent").read_text().splitlines():
                    if riga.startswith("DRIVER="):
                        driver = riga.split("=", 1)[1]
            except OSError:
                pass

            pci_class = None
            try:
                pci_class = int((dev / "class").read_text().strip(), 16)
            except (OSError, ValueError):
                pass
            vis = self._leggi(dev, "mem_info_vis_vram_total")

            if pci_class is None and vis is None:
                unified = True                       # nessun segnale: prudenza
            else:
                unified = (pci_class == _PCI_CLASS_DISPLAY_CONTROLLER
                           or (vis is not None and vis == total))

            return GpuMemory(total=total, used=used, unified=unified, driver=driver)

        log.info("gpu_non_leggibile", radice=str(self._RADICE))
        return None


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
