"""Esecuzione isolata — punto d'ingresso neutro rispetto alla piattaforma.

Il codice applicativo chiama `run_sandboxed()` e non sa che cosa lo esegua.
Su Linux e' bubblewrap (`core/platform/linux_sandbox.py`); su Windows sara'
altro. Invariante 29.
"""

from __future__ import annotations

from pathlib import Path


class SandboxTimeout(RuntimeError):
    """Il processo isolato non e' terminato entro il tempo concesso."""


async def run_sandboxed(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    timeout: float,
    chdir: Path | None = None,
) -> tuple[int, str, str]:
    """Esegue `argv` in isolamento. Ritorna `(returncode, stdout, stderr)`.

    Un'uscita diversa da zero del processo ospitato **non solleva**: e' un
    risultato, non un guasto dell'infrastruttura. Sollevano solo il timeout e
    `SandboxPolicyError`, se la richiesta e' inammissibile.
    """
    from core.platform import sandbox_runner

    return await sandbox_runner(allowed_roots).run(argv, rw_paths, timeout, chdir)
