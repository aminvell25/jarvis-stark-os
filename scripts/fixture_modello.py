"""Genera la fixture del modello 3D per la galleria — §17, ADR-014.

    uv run python scripts/fixture_modello.py

⚠️ **Passa dal GENERATORE vero**, `core.model3d.estrusione`, e non da vertici
scritti a mano: una seconda implementazione dello stesso pezzo diverge alla
prima correzione, e la galleria mostrerebbe un solido che l'app non produce
piu'. Stessa ragione di `scripts/fixture_fusi.py`, che passa dal tool
`timezones` invece di rileggere tzdata per conto proprio.

E' un'istantanea per la sola galleria: nell'app il modello arriva dal core
attraverso il socket, con il file su disco accanto (invariante 1).
"""

from __future__ import annotations

import json
from pathlib import Path

from core.model3d.estrusione import DEFAULT, estrusione_45

USCITA = Path(__file__).resolve().parent.parent / "ui/src/gallery/fixtures/modello.js"

m = estrusione_45()
msg = {"topic": "model3d.preview",
       # Un percorso di ESEMPIO, e si vede che lo e': nella galleria non
       # esiste un file, e mostrare un percorso vero di questa macchina
       # metterebbe la home di qualcuno in un file versionato.
       "file": "~/.local/share/jarvis-os/workspace/modelli/estrusione_45-esempio.glb",
       **m.per_il_renderer()}

USCITA.write_text(
    "/* GENERATO da scripts/fixture_modello.py — non modificare a mano.\n"
    " *\n"
    " * Il messaggio `model3d.preview` che il core manda dopo aver scritto il\n"
    f" * file: {m.nome} {m.versione}, {m.vertici} vertici, {len(m.triangoli)} triangoli,\n"
    f" * {m.bbox[0]:g}x{m.bbox[1]:g}x{m.bbox[2]:g} mm. Prodotto dal generatore VERO —\n"
    " * `core/model3d/estrusione.py` — non scritto a mano.\n"
    " *\n"
    " * Il `file` e' un percorso di esempio: nella galleria non esiste un file,\n"
    " * e §11.9 ammette la FORMA di un dato vero, non un dato inventato.\n"
    " */\n\n"
    "export const MODELLO = " + json.dumps(msg, ensure_ascii=False, indent=2) + ";\n",
    encoding="utf-8",
)
print(f"{m.vertici} vertici, {len(m.triangoli)} triangoli, "
      f"{m.bbox[0]:g}x{m.bbox[1]:g}x{m.bbox[2]:g} mm (default: "
      f"{len(DEFAULT)} parametri) -> {USCITA}")


# ── il tubo, fetta 2 ─────────────────────────────────────────────────────────
#
# Una seconda fixture e non una seconda riga della prima: sono due FORME, e la
# galleria le monta separatamente perche' il ciclo §11.7 vuole uno scatto per
# ciascuna. Il componente che le incassa e' lo stesso.
from core.model3d.tubo import tubo_piegato  # noqa: E402

USCITA_TUBO = USCITA.parent / "modello-tubo.js"

tb = tubo_piegato()
msg_tubo = {"topic": "model3d.preview",
            "file": "~/.local/share/jarvis-os/workspace/modelli/tubo_piegato-esempio.glb",
            **tb.per_il_renderer()}

USCITA_TUBO.write_text(
    "/* GENERATO da scripts/fixture_modello.py — non modificare a mano.\n"
    " *\n"
    f" * {tb.nome} {tb.versione}: {tb.vertici} vertici, {len(tb.triangoli)} triangoli,\n"
    f" * {tb.bbox[0]:.0f}x{tb.bbox[1]:.0f}x{tb.bbox[2]:.0f} mm. Corse dritte e pieghe a\n"
    " * raggio costante: corsa, rotazione, angolo — come si programma su una\n"
    " * piegatrice. Due tappi piatti agli estremi.\n"
    " *\n"
    f" * ⚠️ Porta una TOLLERANZA sul bbox: {tb.tolleranza_mm:.3f} mm, cioe' il\n"
    f" * {tb.tolleranza_relativa * 100:.2f} % dell'ingombro. Non e' un margine di\n"
    " * comodo — la ragione, in forma chiusa, viaggia col messaggio.\n"
    " */\n\n"
    "export const MODELLO_TUBO = " + json.dumps(msg_tubo, ensure_ascii=False, indent=2) + ";\n",
    encoding="utf-8",
)
print(f"{tb.vertici} vertici, {len(tb.triangoli)} triangoli, "
      f"{tb.bbox[0]:.0f}x{tb.bbox[1]:.0f}x{tb.bbox[2]:.0f} mm -> {USCITA_TUBO}")
