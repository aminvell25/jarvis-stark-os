"""Un interprete che vive in un snap, montato dentro bubblewrap SENZA `snap run`.

FreeCAD su questa macchina e' `/snap/bin/freecad`, e `snap run` dentro un
namespace di bubblewrap muore misurato: «cannot create transient scope: DBus
error … Process 2 is a kernel thread». snapd vuole systemd, DBus e la sua
`snap-confine` setuid; dentro `--unshare-all` non ha niente di tutto questo.

La via che funziona, misurata il 3 settembre 2026 con FreeCAD 1.1.1: il
binario del snap eseguito direttamente, con **il base snap come radice** in
sola lettura (`/snap/core24/<rev>` al posto di `--tmpfs /`), il snap stesso e
i suoi content snap montati dove il snap se li aspetta, e l'ambiente preso da
`meta/snap.yaml` — `environment:` con `$SNAP` espanso — invece che copiato a
mano. Tutto il resto del profilo `LABORATORIO` resta: niente rete, la sola
bozza scrivibile, `HOME` in una tmpfs volatile.

⚠️ Bastano QUATTRO variabili — `LD_LIBRARY_PATH`, `LD_PRELOAD`, `PATH`,
`SNAP` — misurato togliendo le altre: FreeCAD aggiunge da solo il
`PYTHONPATH` del snap quando vede `SNAP`. Si passa comunque tutto
`environment:`, perche' e' cio' che il pacchetto dichiara di volere e non
c'e' motivo di contraddirlo su una chiave che non costa niente.

Sapere leggere un manifesto snap e' Linux: sta qui e non in `sandbox/`
(invariante 29). Su Windows FreeCAD sara' un `.exe` e questo file non
esistera'.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

#: Dove snapd monta i snap. Non e' configurabile: e' snapd.
RADICE_SNAP = Path("/snap")

#: Le variabili che nel snap puntano alla casa dell'utente e che qui vanno in
#: una tmpfs volatile: il profilo non ha una casa vera, e non deve averla.
_CASE = {"$SNAP_USER_COMMON": "/tmp", "$SNAP_USER_DATA": "/tmp",
         "$SNAP_REAL_HOME": "/tmp", "$HOME": "/tmp"}


class SnapNonTrovato(RuntimeError):
    """Il snap, il suo base o il suo comando non ci sono."""


@dataclass(frozen=True)
class Snap:
    """Cio' che serve a montare un snap dentro bubblewrap."""

    nome: str
    #: `/snap/<nome>/<revisione>`, risolto: e' la directory che il snap chiama `$SNAP`.
    radice: Path
    #: `/snap/<base>/<revisione>`, risolto: la radice del filesystem del profilo.
    base: Path
    #: Il binario da eseguire, sotto `radice`.
    comando: Path
    #: `environment:` del manifesto, con `$SNAP` e le case gia' espansi.
    ambiente: dict[str, str]
    #: I content snap: `(directory del provider, punto di montaggio sotto radice)`.
    contenuti: tuple[tuple[Path, Path], ...]


def _espandi(valore: str, radice: Path, ambiente: dict[str, str]) -> str:
    """`$SNAP`, le case, e le variabili gia' definite nel manifesto
    (`$PYTHONUSERBASE`); i riferimenti a cio' che non c'e' (`$PATH` di un
    ambiente vuoto) spariscono, e i due punti doppi con loro.

    ⚠️ Un passaggio solo, per nome intero: sostituendo `$SNAP` con una
    `replace` prima delle altre, `$SNAP_USER_COMMON` diventava
    `/snap/freecad/2337_USER_COMMON` — misurato alla prima lettura.
    """
    noti = {"SNAP": str(radice), **{k.lstrip("$"): v for k, v in _CASE.items()}, **ambiente}

    def _var(m: re.Match) -> str:
        return noti.get(m.group(1), "")

    v = re.sub(r"\$([A-Z_][A-Z0-9_]*)", _var, valore)
    if ":" in v:
        v = ":".join(p for p in v.split(":") if p)
    return v


def snap_di(comando: Path) -> tuple[str, Path] | None:
    """`(nome, radice)` se `comando` sta dentro `/snap/<nome>/<rev>/`, altrimenti `None`."""
    try:
        parti = Path(comando).resolve().relative_to(RADICE_SNAP).parts
    except ValueError:
        return None
    if len(parti) < 3:
        return None
    return parti[0], RADICE_SNAP / parti[0] / parti[1]


def trova_snap(comando: Path) -> Snap:
    """Legge `meta/snap.yaml` del snap che contiene `comando`."""
    dove = snap_di(comando)
    if dove is None:
        raise SnapNonTrovato(f"{comando} non sta sotto {RADICE_SNAP}")
    nome, radice = dove
    manifesto = radice / "meta" / "snap.yaml"
    try:
        meta = yaml.safe_load(manifesto.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SnapNonTrovato(f"{manifesto}: {exc}") from exc
    nome_base = str(meta.get("base") or "")
    if not nome_base:
        raise SnapNonTrovato(f"{nome}: il manifesto non dichiara un base snap")
    base = (RADICE_SNAP / nome_base / "current")
    if not base.is_dir():
        raise SnapNonTrovato(f"{nome}: base snap {nome_base} non installato")
    base = base.resolve()
    reale = Path(comando).resolve()
    if not reale.is_file():
        raise SnapNonTrovato(f"comando inesistente: {comando}")

    ambiente: dict[str, str] = {}
    for chiave, valore in (meta.get("environment") or {}).items():
        if str(valore) == "unset":       # convenzione di snapcraft: non impostare
            continue
        ambiente[str(chiave)] = _espandi(str(valore), radice, ambiente)
    ambiente.setdefault("SNAP", str(radice))
    ambiente["SNAP_NAME"] = nome
    ambiente["SNAP_REVISION"] = radice.name

    contenuti: list[tuple[Path, Path]] = []
    for plug in (meta.get("plugs") or {}).values():
        if not isinstance(plug, dict) or plug.get("interface") != "content":
            continue
        bersaglio = str(plug.get("target") or "")
        fornitore = str(plug.get("default-provider") or "").split(":")[0]
        if not bersaglio.startswith("$SNAP/") or not fornitore:
            continue
        sorgente = RADICE_SNAP / fornitore / "current"
        destinazione = radice / bersaglio[len("$SNAP/"):]
        # Tre plug dei temi GTK puntano allo stesso bersaglio: un montaggio.
        if sorgente.is_dir() and destinazione not in {d for _, d in contenuti}:
            contenuti.append((sorgente.resolve(), destinazione))

    return Snap(nome=nome, radice=radice, base=base, comando=reale,
                ambiente=ambiente, contenuti=tuple(contenuti))


def interprete_freecad() -> Path | None:
    """Il FreeCAD headless di questa macchina, se c'e'. Solo il snap, per
    ora: e' l'unica installazione misurata dentro il profilo. Un
    `freecadcmd` di sistema avrebbe bisogno di `/usr/share` e non e' stato
    provato — meglio dire «non c'e'» che promettere un interprete che cade."""
    p = RADICE_SNAP / "freecad" / "current" / "usr" / "bin" / "FreeCADCmd"
    return p if p.is_file() and os.access(p, os.X_OK) else None
