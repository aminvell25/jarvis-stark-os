"""Attrezzatura comune.

Principio: **nessun test tocca la configurazione reale dell'utente.** Ogni
prova costruisce la propria `config_dir` in una directory temporanea e la
consegna al codice attraverso un `Paths` finto. Se una suite dipende da
`~/.config/jarvis-os/`, passa o fallisce a seconda della macchina, e allora
non sta misurando il codice.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from core.platform.base import MemoryInfo, ProcessInfo

REPO = Path(__file__).resolve().parent.parent

SECRETS_TOML = """\
deepgram_api_key = "dg_chiave_di_prova_NON_REALE_9f3a"
guardian_api_key = ""
youtube_api_key  = ""
"""


class FakePaths:
    """`Paths` radicato in una directory temporanea."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def config_dir(self) -> Path:
        return self._root / "config"

    def data_dir(self) -> Path:
        return self._root / "data"

    def workspace(self) -> Path:
        return self._root / "JARVIS"

    def runtime_dir(self) -> Path:
        return self._root / "run"

    def socket_path(self) -> Path:
        return self.runtime_dir() / "core.sock"

    def is_private(self, path: Path) -> bool:
        return not (path.stat().st_mode & 0o077)

    def trash_dir_for(self, path: Path) -> Path | None:
        # Delega alla regola vera: i test cestinano file veri, e un cestino
        # finto direbbe che sono recuperabili senza che lo siano.
        from core.platform.linux import LinuxPaths

        return LinuxPaths().trash_dir_for(path)

    def find_trashed(self, original: Path) -> Path | None:
        from core.platform.linux import LinuxPaths

        return LinuxPaths().find_trashed(original)


@pytest.fixture
def paths(tmp_path: Path) -> FakePaths:
    """Config dir popolata col `config/settings.toml` REALE del repository.

    Usare il file spedito e non una copia ridotta significa che se qualcuno
    aggiunge una chiave al file di configurazione senza aggiungerla allo
    schema, i test lo scoprono subito: `extra="forbid"` la respinge.
    """
    p = FakePaths(tmp_path)
    p.config_dir().mkdir(parents=True)
    shutil.copy(REPO / "config" / "settings.toml", p.config_dir() / "settings.toml")
    (p.config_dir() / "secrets.toml").write_text(SECRETS_TOML, encoding="utf-8")
    for name in ("settings.toml", "secrets.toml"):
        (p.config_dir() / name).chmod(0o600)
    return p


@pytest.fixture(autouse=True)
def _clean_secret_registry():
    """Il registro dei segreti e' globale: va svuotato fra un test e l'altro,
    altrimenti una chiave registrata da un test oscura l'output di un altro e
    produce fallimenti che sembrano stregoneria."""
    from core.settings import SECRETS

    SECRETS.clear()
    yield
    SECRETS.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Attrezzatura per il socket e per la misura
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def short_paths():
    """`Paths` con radice CORTA, per i test che legano un socket UNIX.

    `tmp_path` di pytest produce percorsi come
    `/tmp/pytest-of-utente/pytest-42/test_un_nome_lungo0/`, e sommato a
    `run/core.sock` supera facilmente i 108 byte di `sun_path`. Il fallimento
    che ne segue — "AF_UNIX path too long" — non dice a nessuno cosa fare, e
    dipenderebbe dalla lunghezza del NOME del test: la specie peggiore di test
    fragile.
    """
    with tempfile.TemporaryDirectory(prefix="jt-") as d:
        root = Path(d)
        p = FakePaths(root)
        p.config_dir().mkdir(parents=True)
        shutil.copy(REPO / "config" / "settings.toml", p.config_dir() / "settings.toml")
        (p.config_dir() / "secrets.toml").write_text(SECRETS_TOML, encoding="utf-8")
        for name in ("settings.toml", "secrets.toml"):
            (p.config_dir() / name).chmod(0o600)
        yield p


class FakeSensors:
    """`Sensors` deterministico: i test misurano numeri scelti, non la macchina."""

    def __init__(self, cpu: float = 12.5, ram_percent: float = 40.0,
                 temp: float | None = 55.0, available: int = 8 * 2**30) -> None:
        self._cpu, self._ram, self._temp, self._avail = cpu, ram_percent, temp, available

    def cpu_percent(self) -> float:
        return self._cpu

    def memory(self) -> MemoryInfo:
        return MemoryInfo(total=16 * 2**30, available=self._avail, percent=self._ram)

    def top_processes(self, n: int = 3) -> list[ProcessInfo]:
        return [ProcessInfo(pid=1000 + i, name=f"proc{i}", cpu=90.0 - i)
                for i in range(n)]

    def package_temp(self) -> float | None:
        return self._temp


@pytest.fixture(autouse=True)
def _clean_registry():
    """Il registro dei tool e' globale: va svuotato fra un test e l'altro."""
    from core.tools import registry

    registry.clear()
    yield
    registry.clear()
