"""Politica di isolamento — SPEC §3.4.

Si verifica confrontando stringhe, senza avviare processi: e' la ragione per
cui la politica e' separata dall'esecuzione.

L'argv di bubblewrap sta in `core/platform/linux_sandbox.py` e non in
`core/sandbox/`: l'invariante 29 vieta `bwrap` nel codice applicativo, e §23
dice che su Windows la sandbox e' un'implementazione diversa, non un
adattamento. La validazione dei percorsi resta invece neutra, in
`core/sandbox/policy.py`, perche' quella regola vale su ogni piattaforma.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.platform.linux_sandbox import SECCOMP_APPLICATO, build_argv
from core.sandbox.policy import SandboxPolicyError


@pytest.fixture
def radice(tmp_path: Path) -> Path:
    d = tmp_path / "consentita"
    d.mkdir()
    return d.resolve()


class TestIsolamento:
    def test_argomenti_obbligatori_presenti(self, radice: Path) -> None:
        argv = build_argv(["/bin/true"], [radice], [radice])
        for atteso in ("--unshare-all", "--die-with-parent", "--new-session"):
            assert atteso in argv, f"{atteso} assente: §3.4 lo richiede"

    def test_root_in_sola_lettura(self, radice: Path) -> None:
        argv = build_argv(["/bin/true"], [], [radice])
        i = argv.index("--ro-bind")
        assert argv[i + 1 : i + 3] == ["/", "/"]

    def test_i_bind_scrivibili_vengono_dopo_il_ro_bind(self, radice: Path) -> None:
        """bubblewrap applica le operazioni in sequenza: un bind scrivibile
        prima del `--ro-bind /` verrebbe sovrascritto da esso."""
        argv = build_argv(["/bin/true"], [radice], [radice])
        assert argv.index("--ro-bind") < argv.index("--bind")

    def test_il_comando_e_dopo_il_separatore(self, radice: Path) -> None:
        argv = build_argv(["/bin/echo", "--unshare-all"], [], [radice])
        assert argv[argv.index("--") + 1 :] == ["/bin/echo", "--unshare-all"]


class TestPathFuoriRadice:
    def test_rifiuta_path_esterno(self, radice: Path) -> None:
        with pytest.raises(SandboxPolicyError, match="fuori dalle radici"):
            build_argv(["/bin/true"], [Path("/etc")], [radice])

    def test_rifiuta_traversal_dopo_resolve(self, radice: Path) -> None:
        """Il controllo va DOPO `resolve()`: e' `resolve()` a togliere i `..`,
        e invertire l'ordine e' il modo classico di sbagliarlo (§6.1)."""
        with pytest.raises(SandboxPolicyError):
            build_argv(["/bin/true"], [radice / ".." / ".." / "etc"], [radice])

    def test_accetta_una_sottodirectory(self, radice: Path) -> None:
        sotto = radice / "dentro"
        sotto.mkdir()
        assert str(sotto) in build_argv(["/bin/true"], [sotto], [radice])

    def test_argv_vuoto_rifiutato(self, radice: Path) -> None:
        with pytest.raises(SandboxPolicyError, match="argv vuoto"):
            build_argv([], [], [radice])


def test_seccomp_dichiarato_non_applicato() -> None:
    """Non e' un test di comportamento: e' un promemoria che fallisce il
    giorno in cui qualcuno applica seccomp senza aggiornare la costante o
    `docs/acceptance/FASE-01.md`."""
    assert SECCOMP_APPLICATO is False
