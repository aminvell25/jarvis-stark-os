"""core/paths_cli — la finestrella da cui il lato Electron chiede i percorsi."""

from __future__ import annotations

import subprocess
import sys

from core.paths_cli import CAMPI
from core.platform import paths as platform_paths


def _esegui(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "core.paths_cli", *args],
        capture_output=True, text=True,
    )


class TestCli:
    def test_stampa_il_socket_e_coincide_con_paths(self) -> None:
        r = _esegui("--socket")
        assert r.returncode == 0
        assert r.stdout.strip() == str(platform_paths().socket_path())

    def test_ogni_campo_e_raggiungibile(self) -> None:
        for nome in CAMPI:
            r = _esegui(f"--{nome}")
            assert r.returncode == 0, f"--{nome} fallisce"
            assert r.stdout.strip(), f"--{nome} non stampa nulla"

    def test_senza_argomenti_e_un_errore(self) -> None:
        assert _esegui().returncode != 0

    def test_stampa_una_riga_sola(self) -> None:
        """Il chiamante fa `.trim()` su tutto lo stdout: una seconda riga —
        un warning, un log — glielo romperebbe."""
        assert len(_esegui("--socket").stdout.strip().splitlines()) == 1
