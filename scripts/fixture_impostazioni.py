"""La fixture della pagina impostazioni, dal TEMPLATE del repository.

⚠️ **Non dal file vivo.** `~/.config/jarvis-os/settings.toml` contiene i
percorsi della home di chi lo usa, e una fixture committata che li porta
dentro li pubblica nel repository. `config/settings.toml` e' gia' nel
repository, e i suoi valori sono veri quanto gli altri: e' il file da cui
nasce quello vivo.

Per la stessa ragione le radici consentite si leggono **grezze**, come sono
scritte — `~/JARVIS` — invece che risolte: risolverle vorrebbe dire scrivere
`/home/<qualcuno>` in un file versionato.

Invariante 23: dati veri o stato vuoto esplicito. Questi sono veri.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

import tomlkit  # noqa: E402

from core.settings import Settings  # noqa: E402
from core.tools.impostazioni import BLOCCATE, chiavi_modificabili  # noqa: E402

USCITA = RADICE / "ui" / "src" / "gallery" / "fixtures" / "impostazioni.js"


def _grezzo(doc, chiave: str):
    nodo = doc
    for pezzo in chiave.split("."):
        if not isinstance(nodo, dict) or pezzo not in nodo:
            return None
        nodo = nodo[pezzo]
    return nodo


def main() -> int:
    sorgente = RADICE / "config" / "settings.toml"
    doc = tomlkit.parse(sorgente.read_text(encoding="utf-8"))
    grezzo = doc.unwrap()
    grezzo.pop("secrets", None)
    s = Settings.model_validate(grezzo)

    modificabili = chiavi_modificabili(s)
    bloccate = {}
    for chiave in sorted(BLOCCATE):
        valore = _grezzo(grezzo, chiave)
        if valore is None:
            # Una chiave con un predefinito che il template non scrive.
            nodo = s
            for pezzo in chiave.split("."):
                nodo = getattr(nodo, pezzo, None)
            valore = nodo
        bloccate[chiave] = valore

    testo = (
        "/* GENERATO da scripts/fixture_impostazioni.py — non modificare a mano.\n"
        " *\n"
        " * Dal TEMPLATE `config/settings.toml`, non dal file vivo: quello porta\n"
        " * i percorsi della home, e una fixture committata li pubblicherebbe.\n"
        " * Le radici restano scritte come nel file (`~/JARVIS`) e non risolte.\n"
        " */\n\n"
        "export const IMPOSTAZIONI = "
        + json.dumps({"modificabili": modificabili, "bloccate": bloccate,
                      "file": "~/.config/jarvis-os/settings.toml"},
                     indent=2, ensure_ascii=False)
        + ";\n"
    )
    USCITA.write_text(testo, encoding="utf-8")
    print(f"{USCITA.relative_to(RADICE)}: {len(modificabili)} modificabili, "
          f"{len(bloccate)} bloccate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
