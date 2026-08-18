"""Attrezzatura comune.

Principio: **nessun test tocca la configurazione reale dell'utente.** Ogni
prova costruisce la propria `config_dir` in una directory temporanea e la
consegna al codice attraverso un `Paths` finto. Se una suite dipende da
`~/.config/jarvis-os/`, passa o fallisce a seconda della macchina, e allora
non sta misurando il codice.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

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
