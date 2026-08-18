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
    "gestures",   # Fase 7
    "news",       # Fase 8
    # §13 — la scrivania. `chrome` e' barra + dock: sono componenti visivi
    # come gli altri, e senza passare da qui l'invariante 18 su quei due file
    # sarebbe una promessa invece di un controllo.
    "console", "chrome",
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
                # L'ULTIMA riga di stderr e' la versione di node e non dice
                # niente: la riga utile e' quella dell'errore. Col messaggio
                # sbagliato questo test dice «rotto» senza dire dove, e il
                # difetto tipico — un backtick dentro un commento CSS, che
                # chiude il template literal del foglio di stile — si cerca a
                # mano. E' successo sei volte.
                righe = [x for x in r.stderr.splitlines() if "Error" in x]
                guasti.append(
                    f"{f.relative_to(RADICE)}: "
                    f"{righe[0] if righe else r.stderr.strip()[:200]}"
                )
    assert not guasti, "moduli non caricabili:\n" + "\n".join(guasti)


def test_ogni_pannello_espone_una_testa_e_un_gruppo_di_controlli():
    """Il contratto su cui si regge la cornice di §13.

    `ui/src/desk/cornice.js` trova la testa del pannello e ne fa la maniglia
    del trascinamento, e trova il gruppo `⊟ ⊡ ⊠` e lo trasforma in tre
    controlli veri. Lo fa per convenzione di nomi — `__testa`, `__ctrl` — che
    tutti e quattordici i componenti seguono gia'.

    Una convenzione che nessuno verifica dura fino al prossimo componente. Qui
    diventa un contratto: un pannello senza testa non si potrebbe trascinare,
    e uno senza controlli mostrerebbe una finestra che non si chiude.
    """
    import re as _re

    guasti = []
    for nome in COMPONENTI:
        if nome in {"conforme", "non-conforme", "chrome"}:
            continue          # non sono pannelli: non hanno un'anatomia §10.2
        sorgente = None
        for base in ("panels", "css3d", "pixi", "anim"):
            p = RADICE / "ui/src" / base / f"{nome}.js"
            if p.exists():
                sorgente = p
                break
        if sorgente is None:
            continue          # componente montato da un altro file: gia' coperto
        testo = sorgente.read_text(encoding="utf-8")
        teste = len(_re.findall(r'class="[^"]*__testa', testo))
        ctrl = len(_re.findall(r'class="[^"]*__ctrl', testo))
        if teste != 1 or ctrl != 1:
            guasti.append(f"{sorgente.name}: {teste} teste, {ctrl} gruppi di controlli")
    assert not guasti, (
        "la cornice di §13 non troverebbe cosa agganciare:\n" + "\n".join(guasti)
    )


def test_nessun_backtick_dentro_i_fogli_di_stile():
    """Il difetto piu' ripetuto di tutto il progetto, reso impossibile.

    Ogni componente porta il proprio CSS in un template literal:

        export const css = `
        /* un commento che nomina `overflow` */      <- lo CHIUDE qui
        ...

    Un backtick dentro un commento CSS termina la stringa. Il modulo smette di
    caricarsi, la pagina resta bianca, e l'errore in console parla di una riga
    che non c'entra niente. E' successo SETTE volte fra la Fase 1b e §13.

    `test_ogni_modulo_del_renderer_si_carica_come_esm` lo vede gia', ma dice
    solo «SyntaxError»: questo dice il file, la riga e cosa togliere.
    """
    guasti = []
    for f in sorted((RADICE / "ui/src").rglob("*.js")):
        testo = f.read_text(encoding="utf-8")
        i = testo.find("export const css = `")
        if i < 0:
            continue
        inizio = i + len("export const css = `")
        if not testo[inizio:inizio + 1] == "\n":
            # Una riga sola: e' una COMPOSIZIONE di altri fogli, non un foglio
            # — `ui/src/gallery/mounts/chrome.js` unisce barra e dock. Li' i
            # backtick sono la sintassi, non un commento.
            continue
        fine = testo.find("\n`;", inizio)
        if fine < 0:
            guasti.append(f"{f.relative_to(RADICE)}: il foglio non si chiude")
            continue
        for n, riga in enumerate(testo[inizio:fine].splitlines(), 1):
            if "`" in riga:
                riga_vera = testo[:inizio].count(chr(10)) + n
                guasti.append(
                    f"{f.relative_to(RADICE)}:{riga_vera}: backtick nel CSS "
                    f"-> {riga.strip()[:70]}"
                )
    assert not guasti, (
        "un backtick qui chiude il template literal e il modulo non si "
        "carica:\n" + "\n".join(guasti)
    )


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

    # ⚠️ E lo STESSO CSP. Non e' simmetria: i glifi PixiJS hanno passato tutta
    # la Fase 5 in galleria e in Electron non sono mai partiti, perche' Pixi v8
    # genera codice con `new Function()` e la galleria non aveva un CSP che lo
    # vietasse. Una galleria piu' permissiva dell'app fa passare il ciclo §11.7
    # a componenti che nell'app non funzionano — cioe' esattamente il
    # fallimento che §11.7 esiste per evitare.
    cspg = re.search(r'Content-Security-Policy"\s*\n?\s*content="([^"]+)"', galleria)
    assert cspg, "CSP assente da ui/gallery.html"
    assert cspg.group(1) == csp.group(1), (
        "la galleria e l'app hanno CSP diversi: la galleria giudicherebbe "
        "componenti che nell'app non partono"
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


# ── §13 · la scrivania ───────────────────────────────────────────────────────
#
# La disposizione e' dichiarata come CELLE su una griglia (`moduli.js`), non
# come pixel: i pixel li calcola la scrivania dall'area vera. Una griglia si
# puo' verificare — buchi e sovrapposizioni sono aritmetica — e §11.6 regola 3
# («uno schermo mezzo vuoto non sembrera' mai JARVIS») smette di essere
# un'opinione.


def _moduli() -> dict:
    """Il registro di §13, letto dal modulo VERO."""
    return json.loads(_node("""
      import { COLONNE, RIGHE, MODULI, WORKSPACE, composizione, moduliDelDock }
        from './ui/src/desk/moduli.js';
      console.log(JSON.stringify({
        colonne: COLONNE, righe: RIGHE,
        workspace: WORKSPACE,
        dock: moduliDelDock().map((m) => m.id),
        moduli: MODULI.map((m) => ({ id: m.id, ws: m.ws, cella: m.cella,
                                     modulo: !!m.modulo, suRichiesta: !!m.suRichiesta })),
        composizioni: WORKSPACE.map((w) => composizione(w.n).map((m) => m.id)),
      }));
    """))


def test_il_dock_ha_gli_otto_moduli_di_13():
    """La tabella di §13 ha otto righe. Ne' sette ne' nove."""
    r = _moduli()
    assert r["dock"] == [
        "telemetria", "agenti", "console",     # 01 sistema
        "file", "sorgente",                    # 02 file
        "browser", "news",                     # 03 web
        "globo",                               # 04 3D
    ]


def test_ogni_workspace_e_pieno_e_senza_sovrapposizioni():
    """§11.6 regola 3, resa aritmetica.

    Ogni cella della griglia di ogni workspace deve essere coperta ESATTAMENTE
    una volta: due pannelli sulla stessa cella si nasconderebbero a vicenda, e
    una cella scoperta e' il buco che fa sembrare finto uno schermo.
    """
    r = _moduli()
    guasti = []
    for w in r["workspace"]:
        copertura = {}
        for m in r["moduli"]:
            if m["ws"] != w["n"] or m["suRichiesta"]:
                continue
            c, riga, dc, dr = m["cella"]
            assert 0 <= c and c + dc <= r["colonne"], f"{m['id']} esce dalla griglia"
            assert 0 <= riga and riga + dr <= r["righe"], f"{m['id']} esce dalla griglia"
            for x in range(c, c + dc):
                for y in range(riga, riga + dr):
                    copertura.setdefault((x, y), []).append(m["id"])
        doppie = {k: v for k, v in copertura.items() if len(v) > 1}
        vuote = [
            (x, y) for x in range(r["colonne"]) for y in range(r["righe"])
            if (x, y) not in copertura
        ]
        if doppie:
            guasti.append(f"WS0{w['n']} sovrapposizioni: {doppie}")
        if vuote:
            guasti.append(f"WS0{w['n']} celle scoperte: {vuote}")
    assert not guasti, "\n".join(guasti)


def test_ogni_workspace_ha_almeno_due_pannelli():
    """Un workspace a un pannello e' la scrivania della Fase 1b col dock."""
    r = _moduli()
    for w, comp in zip(r["workspace"], r["composizioni"]):
        assert len(comp) >= 2, f"WS0{w['n']} ha {len(comp)} pannelli"


def test_i_nomi_che_si_dicono_a_voce_trovano_un_pannello():
    """Cross-lingua: la grammatica T0 e il registro della scrivania.

    `core/llm/grammar.py` elenca i pannelli che «apri il ...» riconosce. Ogni
    nome di quell'elenco deve trovare un modulo, o la frase entra, diventa un
    `ui.intent`, arriva alla scrivania e non apre niente — un comando che
    fallisce in silenzio.

    ⚠️ `impostazioni` e' l'ECCEZIONE DICHIARATA: la grammatica lo accetta dalla
    Fase 3, `ui/src/panels/settings.js` e' un file vuoto, e §13 non lo elenca
    fra gli otto moduli. Il test lo fissa come noto invece di lasciarlo
    scoprire a voce.
    """
    grammatica = (RADICE / "core/llm/grammar.py").read_text(encoding="utf-8")
    m = re.search(r'_PANNELLI = r"([^"]+)"', grammatica)
    assert m, "il gruppo _PANNELLI non e' piu' dove ci si aspetta"
    nomi = set(m.group(1).split("|"))

    esito = json.loads(_node("""
      import { modulo } from './ui/src/desk/moduli.js';
      const nomi = %s;
      console.log(JSON.stringify(nomi.filter((n) => !modulo(n))));
    """ % json.dumps(sorted(nomi))))
    assert esito == ["impostazioni"], (
        f"nomi che la voce accetta e che non aprono nessun pannello: {esito}"
    )


@pytest.mark.parametrize(
    "x,y,atteso",
    [
        (2, 500, "sinistra"),
        (1918, 500, "destra"),
        (900, 42, "alto"),
        (900, 1020, "basso"),
        (900, 500, None),          # in mezzo: nessun aggancio
    ],
)
def test_l_aggancio_al_bordo_e_a_meta(x: int, y: int, atteso):
    """§13: «trascinamento al bordo → aggancia a meta'». Quattro meta'."""
    esito = json.loads(_node(f"""
      import {{ zonaAggancio }} from './ui/src/desk/cornice.js';
      const area = {{ sinistra: 0, alto: 40, larghezza: 1920, altezza: 990 }};
      const z = zonaAggancio({x}, {y}, area);
      console.log(JSON.stringify(z));
    """))
    if atteso is None:
        assert esito is None
        return
    assert esito["nome"] == atteso
    # Una meta' vera: o mezza larghezza o mezza altezza, mai un quarto.
    assert (esito["w"] == 960 and esito["h"] == 990) or \
           (esito["w"] == 1920 and esito["h"] == 495), esito


def test_le_scorciatoie_dichiarate_sono_quelle_di_13():
    """La tabella di §13, meno le due che parlerebbero al core.

    Il modulo dichiara ANCHE cio' che non fa. Una mancanza dichiarata e' una
    decisione; una taciuta e' un difetto che si scopre premendo un tasto.
    """
    esito = json.loads(_node("""
      import { SCORCIATOIE, NON_REALIZZATE } from './ui/src/desk/tastiera.js';
      console.log(JSON.stringify({
        fatte: SCORCIATOIE.map((s) => s.tasti),
        no: NON_REALIZZATE.map((s) => s.tasti),
      }));
    """))
    assert esito["fatte"] == ["Alt+H", "Alt+T", "Alt+1", "Alt+2", "Alt+3", "Alt+4"]
    assert esito["no"] == ["Alt+Spazio", "Esc"]
