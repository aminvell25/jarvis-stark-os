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


class SandboxPolicyError(ValueError):
    """Una richiesta che la politica rifiuta prima di eseguire."""


def _sotto_radice(p: Path, radici: list[Path]) -> bool:
    return any(p == r or r in p.parents for r in radici)


def resolve_rw_paths(rw_paths: list[Path], allowed_roots: list[Path]) -> list[Path]:
    """Risolve i percorsi scrivibili e verifica che stiano sotto le radici.

    Il controllo avviene **dopo `resolve()`**, come in §6.1: e' `resolve()` a
    eliminare i `..`, e invertire l'ordine e' il modo classico di sbagliare
    questo controllo.
    """
    radici = [Path(r).expanduser().resolve() for r in allowed_roots]
    risolti: list[Path] = []
    for raw in rw_paths:
        p = Path(raw).expanduser().resolve()
        if not _sotto_radice(p, radici):
            raise SandboxPolicyError(
                f"{p} e' fuori dalle radici consentite: {', '.join(map(str, radici))}"
            )
        risolti.append(p)
    return risolti
