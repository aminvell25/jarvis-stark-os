"""Eval visivo — SPEC §22, tabella degli eval: «ogni componente passa quality
gate e checklist §11.8», da Fase 5.

⚠️ **Questo file verifica il SOTTOINSIEME MECCANICO della §11.8**, e la
distinzione e' il punto piu' importante del modulo.

Si verificano qui:
  · ogni geometria parametrica passa `qualityGate()`
  · il gate SPARA su una geometria deliberatamente sbagliata
  · l'audit dei token e' pulito su ogni componente (livelli 1 e 2 di Fase 0b:
    colori, spaziature multiple di 4, corpi, raggio, ombre esterne)
  · ogni modulo del renderer si carica davvero come ESM
  · l'impronta CSP e la import map di `ui/index.html` sono allineate

NON si verificano qui, e sono riportati a mano in `docs/acceptance/FASE-05.md`
guardando gli screenshot:
  · la densita' regge il confronto con l'immagine di riferimento
  · l'accento caldo sta sotto il 10% della superficie colorata
  · ogni animazione risponde a un evento reale

Una checklist che finge di essere automatica su punti di giudizio e' peggio di
una dichiarata a meta': darebbe verde a un componente che nessuno ha guardato,
ed e' esattamente il fallimento che §11.7 esiste per evitare.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent

# I componenti che devono risultare puliti all'audit. `non-conforme` e' escluso
# apposta — esiste per PROVARE che l'audit vede le violazioni — e `budget` pure:
# e' un banco di misura, non un componente da giudicare.
COMPONENTI = [
    "conforme", "telemetry", "confirm", "files",
    "rings", "dials", "source", "agents", "periodic", "glyphs", "globe",
    # Fase 6. `browser` e `board` contengono una `<webview>`, che fuori da
    # Electron non esiste: qui si giudica la cornice — cornice, barra,
    # tipografia, carte — e la webview VIVA e' il criterio B di §22, che si
    # verifica nella finestra vera con `npm run verifica`.
    "browser", "planes", "board",
]

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node non disponibile"
)


def _node(codice: str) -> str:
    """Esegue un modulo ESM al volo, dalla radice del progetto."""
    r = subprocess.run(
        ["node", "--no-warnings", "--input-type=module", "-e", codice],
        cwd=RADICE, capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        raise AssertionError(f"node ha fallito:\n{r.stderr.strip()}")
    return r.stdout.strip()


def test_ogni_geometria_passa_il_gate():
    """§11.10 e §11.11 su tutti i componenti parametrici della fase.

    Gira in Node e non nel browser: la geometria e il gate non dipendono da
    three.js (vedi `ui/src/three/geometry.js`), quindi non serve un contesto
    WebGL — che in un test headless sarebbe software, lento e diverso da
    quello vero.
    """
    uscita = _node("""
      import { ReactorRing } from './ui/src/three/components/reactor-ring.js';
      import { RadialDial } from './ui/src/three/components/radial-dial.js';
      import { PointCloud } from './ui/src/three/math/pointcloud.js';
      import { Graticola, Terminatore, Fusi, puntoSubsolare } from './ui/src/three/math/globe.js';
      import { qualityGate } from './ui/src/three/quality-gate.js';
      import { ALBERO } from './ui/src/gallery/fixtures/albero.js';
      import { FUSI } from './ui/src/gallery/fixtures/fusi.js';

      const sole = puntoSubsolare(new Date('2026-08-18T14:05:00Z'));
      const casi = [
        ['reactor-ring', new ReactorRing()],
        ['radial-dial', new RadialDial()],
        ['point-cloud', new PointCloud({}, ALBERO)],
        ['globe-graticule', new Graticola()],
        ['globe-terminator', new Terminatore({}, sole)],
        ['globe-timezones', new Fusi({}, FUSI)],
      ];
      const esito = casi.map(([nome, c]) => {
        const g = c.build();
        qualityGate(c, g, ['linea', 'costruzione']);
        return { nome, vertici: g.getAttribute('position').count };
      });
      console.log(JSON.stringify(esito));
    """)
    esito = json.loads(uscita)
    assert len(esito) == 6
    for c in esito:
        assert c["vertici"] >= 24, c


@pytest.mark.parametrize(
    "guasto,atteso",
    [
        ("for (let i=0;i<g.posizioni.length;i+=3) g.posizioni[i] *= 2;", "bbox.x"),
        ("for (let i=0;i<g.posizioni.length;i+=3) g.posizioni[i+2] += 9000;", "centro fuori origine"),
        ("g.posizioni[0] = NaN;", "NaN"),
    ],
)
def test_il_gate_spara_su_una_geometria_sbagliata(guasto: str, atteso: str):
    """Un controllo che non ha mai bocciato nulla non e' un controllo.

    Tre guasti veri: un fattore due su un asse, una traslazione fuori scala,
    un NaN. Il gate deve vederli TUTTI, e il messaggio deve dire quale.
    """
    uscita = _node(f"""
      import {{ ReactorRing }} from './ui/src/three/components/reactor-ring.js';
      import {{ qualityGate }} from './ui/src/three/quality-gate.js';
      class Rotto extends ReactorRing {{
        build() {{ const g = super.build(); {guasto} return g; }}
      }}
      const c = new Rotto();
      try {{
        qualityGate(c, c.build(), []);
        console.log('NESSUN ERRORE');
      }} catch (e) {{ console.log(e.message); }}
    """)
    assert "NESSUN ERRORE" not in uscita, "il gate non ha visto il guasto"
    assert atteso in uscita, uscita


def test_ogni_modulo_del_renderer_si_carica_come_esm():
    """Ogni `.js` sotto `ui/src/` deve essere ESM valido.

    Non e' pedanteria: un backtick dentro un commento CSS chiude il template
    literal che contiene il foglio di stile, e il modulo smette di caricarsi.
    E' successo tre volte in questa fase, e ogni volta il sintomo era una
    pagina bianca con un errore in console che sembrava un altro problema.

    `node --check` su un `.js` lo analizza come CommonJS e non basta: la copia
    con estensione `.mjs` forza l'analisi come modulo.
    """
    import tempfile

    file = sorted(p for p in (RADICE / "ui/src").rglob("*.js"))
    assert len(file) > 15, "l'albero del renderer sembra vuoto: controllo inutile"

    guasti = []
    with tempfile.TemporaryDirectory() as tmp:
        for f in file:
            copia = Path(tmp) / (f.stem + ".mjs")
            copia.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
            r = subprocess.run(
                ["node", "--check", str(copia)], capture_output=True, text=True
            )
            if r.returncode != 0:
                guasti.append(f"{f.relative_to(RADICE)}: {r.stderr.splitlines()[-1]}")
    assert not guasti, "moduli non caricabili:\n" + "\n".join(guasti)


def test_impronta_csp_allineata_alla_import_map():
    """Il CSP di `ui/index.html` autorizza la import map per IMPRONTA.

    Modificare la mappa senza aggiornare l'impronta non da' un errore di
    sintassi: da' una finestra vuota e una riga in console. Il test rende
    impossibile spedirlo, e nel messaggio c'e' l'impronta da incollare.
    """
    html = (RADICE / "ui/index.html").read_text(encoding="utf-8")
    m = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
    assert m, "import map assente da ui/index.html"

    impronta = "sha256-" + base64.b64encode(
        hashlib.sha256(m.group(1).encode("utf-8")).digest()
    ).decode("ascii")

    csp = re.search(r'Content-Security-Policy"\s*\n?\s*content="([^"]+)"', html)
    assert csp, "CSP assente da ui/index.html"
    assert impronta in csp.group(1), (
        f"il CSP non autorizza la import map attuale.\n"
        f"impronta da inserire in script-src: '{impronta}'"
    )

    # E la galleria deve dichiarare la STESSA mappa, o giudicherebbe moduli
    # risolti diversamente da come li risolve l'app.
    galleria = (RADICE / "ui/gallery.html").read_text(encoding="utf-8")
    mg = re.search(r'<script type="importmap">(.*?)</script>', galleria, re.S)
    assert mg, "import map assente da ui/gallery.html"
    assert json.loads(mg.group(1)) == json.loads(m.group(1)), (
        "galleria e app risolvono i moduli in modo diverso"
    )


@pytest.mark.slow
def test_audit_dei_token_pulito_su_ogni_componente():
    """Il sottoinsieme MECCANICO di §11.8, su ogni componente della galleria.

    Un solo browser per tutti: nove avvii di Chromium sarebbero quaranta
    secondi di attesa.
    """
    r = subprocess.run(
        ["node", "scripts/audit.mjs", *COMPONENTI],
        cwd=RADICE, capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    esiti = json.loads(r.stdout.strip().splitlines()[-1])

    guasti = []
    for e in esiti:
        if e.get("errore"):
            guasti.append(f"{e['nome']}: {e['errore']}")
            continue
        if e.get("errori"):
            guasti.append(f"{e['nome']}: errori di console {e['errori'][:2]}")
        if e.get("fontMancanti"):
            guasti.append(f"{e['nome']}: font assenti {e['fontMancanti']}")
        totale = (e.get("violazioniCalcolate") or 0) + (e.get("violazioniSorgente") or 0)
        if totale:
            guasti.append(
                f"{e['nome']}: {totale} violazioni — "
                f"{e.get('dettaglioCalcolato')} {e.get('dettaglioSorgente')}"
            )
    assert not guasti, "\n".join(guasti)


@pytest.mark.slow
def test_l_audit_vede_ancora_le_violazioni():
    """La fixture non conforme deve ancora illuminarsi.

    E' il controllo del controllo: se l'audit smettesse di vedere, tutti i
    test qui sopra diventerebbero verdi per il motivo sbagliato.
    """
    r = subprocess.run(
        ["node", "scripts/audit.mjs", "non-conforme"],
        cwd=RADICE, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    e = json.loads(r.stdout.strip().splitlines()[-1])[0]
    totale = (e.get("violazioniCalcolate") or 0) + (e.get("violazioniSorgente") or 0)
    assert totale > 0, "l'audit non vede piu' le violazioni della fixture non conforme"
