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

# ── la mano per il pannello gesture (Fase 7) ────────────────────────────────
#
# Gli stessi landmark che il corpus usa per i test: cosi' cio' che la galleria
# DISEGNA e' cio' che il riconoscitore GIUDICA, e non due cose che si somigliano.
from tests.gesture_corpus import mano  # noqa: E402

MANO_USCITA = USCITA.parent / "mano.js"
pose = {
    "palmo_aperto": mano(dita=1.0),
    "pizzico": mano(dita=0.9, pollice_su_indice=True),
}
righe = ",\n  ".join(
    f'"{nome}": ' + json.dumps([list(p) for p in m.punti])
    for nome, m in pose.items()
)
MANO_USCITA.write_text(
    "/* GENERATO da scripts/fixture_fusi.py — non modificare a mano.\n"
    " *\n"
    " * Landmark SINTETICI, con la forma di quelli di MediaPipe: 21 terne\n"
    " * normalizzate. Sono gli stessi che `tests/gesture_corpus.py` da' al\n"
    " * riconoscitore, cosi' cio' che la galleria disegna e cio' che i test\n"
    " * giudicano sono la stessa cosa. Su una mano VERA il riconoscimento non\n"
    " * e' ancora stato verificato: vedi docs/acceptance/FASE-07.md.\n */\n\n"
    f"export const POSE = {{\n  {righe},\n}};\n",
    encoding="utf-8",
)
print(f"{len(pose)} pose -> {MANO_USCITA}")
