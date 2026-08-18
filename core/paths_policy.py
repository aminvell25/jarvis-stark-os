"""La regola piu' critica del progetto, in un posto solo.

*Un percorso e' consentito se, DOPO essere stato risolto, sta dentro una delle
radici consentite.*

Sembra una riga e ha quattro insidie, tutte verificate sul campo e coperte da
`tests/eval_paths.py`:

1. **Il controllo va dopo `resolve()`.** E' `resolve()` a eliminare i `..`, e
   invertire l'ordine e' il modo classico di sbagliare (§6.1).
2. **Anche le RADICI vanno risolte.** §6.1 non lo fa. Se una radice fosse un
   symlink — comune per `~/Documenti` su home cifrate o dischi separati — il
   confronto fra un path risolto e una radice non risolta fallirebbe SEMPRE, e
   nessun percorso sarebbe mai consentito. E' un difetto che non si vede su una
   macchina dove le radici sono directory vere: compare altrove.
3. **`resolve()` segue i symlink**, ed e' cio' che vogliamo: un link dentro una
   radice che punta a `/etc` risolve a `/etc` e viene respinto.
4. **`resolve()` puo' sollevare.** Un byte NUL nel percorso alza `ValueError`.
   Va catturato, o l'eccezione risale invece di diventare un rifiuto.

Le radici arrivano SEMPRE dal chiamante, mai da costanti di modulo: la sorgente
di verita' e' `settings.fs.allowed_roots`, gia' validata dalla Fase 0.
"""

from __future__ import annotations

from pathlib import Path


class PathFuoriRadice(ValueError):
    """Un percorso che, risolto, cade fuori dalle radici consentite."""


def radici_risolte(roots: list[Path]) -> list[Path]:
    """Le radici, espanse e risolte. Vedi insidia 2."""
    return [Path(r).expanduser().resolve() for r in roots]


def _dentro(p: Path, radici: list[Path]) -> bool:
    return any(p == r or r in p.parents for r in radici)


def risolvi_sotto_radici(path: str | Path, roots: list[Path]) -> Path:
    """Risolve `path` e verifica che stia sotto una radice.

    Solleva `PathFuoriRadice` se non ci sta, o se il percorso non e'
    rappresentabile — un byte NUL, un nome troppo lungo. **Il rifiuto e' lo
    stesso in entrambi i casi**: cio' che non si puo' verificare non si accetta.
    """
    radici = radici_risolte(roots)
    if not radici:
        raise PathFuoriRadice("nessuna radice consentita configurata")

    try:
        risolto = Path(path).expanduser().resolve()
    except (ValueError, OSError) as exc:
        raise PathFuoriRadice(f"percorso non rappresentabile: {exc}") from exc

    if not _dentro(risolto, radici):
        raise PathFuoriRadice(
            f"{risolto} e' fuori dalle radici consentite: "
            f"{', '.join(map(str, radici))}"
        )
    return risolto


def risolvi_tutti(paths: list[str | Path], roots: list[Path]) -> list[Path]:
    return [risolvi_sotto_radici(p, roots) for p in paths]


def e_una_radice(path: str | Path, roots: list[Path]) -> bool:
    """Vero se `path` E' una radice, non solo dentro una.

    Serve ai tool distruttivi: cestinare `~/JARVIS` e' consentito dalla regola
    dei percorsi — una radice sta dentro se stessa — ma non e' mai cio' che
    l'utente intende. Il divieto sta nel tool, non qui: questa e' una domanda
    sui percorsi, non una politica.
    """
    try:
        risolto = Path(path).expanduser().resolve()
    except (ValueError, OSError):
        return False
    return risolto in radici_risolte(roots)
