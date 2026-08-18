"""Genera la fixture dei fusi orari per la galleria.

    uv run python scripts/fixture_fusi.py

Passa dal TOOL vero — `core.tools.geo.leggi_fusi()` — e non da un parser
scritto apposta: una seconda implementazione dello stesso formato e' una
seconda occasione di sbagliare, e diverge alla prima riga strana di tzdata.

E' un'istantanea per la sola galleria. Nell'app i fusi arrivano dall'allowlist
attraverso il socket, senza istantanee (invariante 1).
"""

from __future__ import annotations

import json
from pathlib import Path

from core.tools.geo import TABELLA, leggi_fusi

USCITA = Path(__file__).resolve().parent.parent / "ui/src/gallery/fixtures/fusi.js"

zone = leggi_fusi()
righe = ",\n  ".join(
    json.dumps({"nome": z["nome"], "lat": z["lat"], "lon": z["lon"]}, ensure_ascii=False)
    for z in zone
)
USCITA.write_text(
    "/* GENERATO da scripts/fixture_fusi.py — non modificare a mano.\n"
    f" *\n * Istantanea di {TABELLA} (pubblico dominio), letta dal tool\n"
    f" * `timezones` dell'allowlist. {len(zone)} fusi.\n */\n\n"
    f"export const FUSI = [\n  {righe},\n];\n",
    encoding="utf-8",
)
print(f"{len(zone)} fusi -> {USCITA}")
