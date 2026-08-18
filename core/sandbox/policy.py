"""Politica della sandbox — la parte che NON dipende dalla piattaforma.

Validare che un percorso scrivibile stia sotto le radici consentite e' la
stessa regola su Linux, su Windows e ovunque. L'argv di bubblewrap no: quello
sta in `core/platform/linux_sandbox.py`, per l'invariante 29.

Che cosa isola questa sandbox, e che cosa non isola. Protegge dal **codice
generato**. Le operazioni su file reali non ci passano: girano nel core sotto
allowlist con validazione dei path (§6.1, Fase 2). Sono due difese contro due
minacce diverse, e confonderle le rende inutili entrambe.
"""

from __future__ import annotations

from pathlib import Path

from core.paths_policy import PathFuoriRadice, risolvi_tutti


class SandboxPolicyError(ValueError):
    """Una richiesta che la politica rifiuta prima di eseguire."""


def resolve_rw_paths(rw_paths: list[Path], allowed_roots: list[Path]) -> list[Path]:
    """Risolve i percorsi scrivibili e verifica che stiano sotto le radici.

    Delega a `core.paths_policy`, che dalla Fase 2 e' l'unica implementazione
    della regola: la sandbox e i tool sui file devono rifiutare esattamente gli
    stessi percorsi, e due copie divergerebbero alla prima correzione.
    """
    try:
        return risolvi_tutti(list(rw_paths), allowed_roots)
    except PathFuoriRadice as exc:
        raise SandboxPolicyError(str(exc)) from exc
