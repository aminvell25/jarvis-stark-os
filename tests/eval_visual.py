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

# I componenti che devono risultare puliti all'audit. Le due fixture
# `non-conforme*` sono escluse apposta — esistono per PROVARE che l'audit vede
# le violazioni — e `budget` pure: e' un banco di misura, non un componente da
# giudicare.
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


def test_nessun_backtick_dentro_i_template_letterali():
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


def test_una_sola_api_per_le_barre_di_scorrimento():
    """Le due API delle barre di scorrimento non convivono.

    Da Chromium 121, se `scrollbar-width` o `scrollbar-color` sono impostate,
    gli pseudo-elementi `::-webkit-scrollbar` vengono IGNORATI in blocco.

    Dichiararle entrambe non da' nessun errore: da' dieci righe di CSS che non
    girano. Misurato nella finestra vera, la barra risultava alta 10 px invece
    degli 8 di `--s-2` — la larghezza che Chromium da' a `thin` — e col
    cursore dalle estremita' arrotondate, che l'invariante 18 vieta e che con
    le proprieta' standard non si puo' quadrare.

    Qui vale `::-webkit-scrollbar`: Electron e' Chromium e basta. Le standard
    servono a Firefox, che questo codice non lo esegue mai.
    """
    css = (RADICE / "ui/src/style/app.css").read_text(encoding="utf-8")
    senza_commenti = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    standard = re.search(r"\bscrollbar-(width|color)\s*:", senza_commenti)
    webkit = "::-webkit-scrollbar" in senza_commenti
    assert not (standard and webkit), (
        "app.css dichiara sia le proprieta' standard delle barre di "
        f"scorrimento ({standard.group(0) if standard else ''}) sia gli "
        "pseudo-elementi ::-webkit-scrollbar: Chromium ignora i secondi, e "
        "quelle regole non girano."
    )
    assert webkit, "nessuna regola per le barre: tornerebbero grigie di sistema"


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
@pytest.mark.parametrize("immagine,dev,entropia", [
    ("01-desktop-mcu-completo", 55.7, 3.32),
    ("05-dashboard-news", 40.6, 2.85),
    ("10-globo-gps-locator", 41.9, 3.05),
])
def test_le_misure_di_densita_riproducono_i_riferimenti(immagine, dev, entropia):
    """Rev 5.10 — chi verifica il verificatore.

    `L>25` e' stata ritirata dal giudizio perche' era salita al 96,9 % ed era
    satura: passava sempre, e una metrica che passa sempre sembra una verifica
    senza esserlo. Al suo posto deviazione standard ed entropia
    dell'istogramma a 16 bin.

    Le soglie — dev.std 32, entropia 2,40 — stanno a meta' strada fra la
    nostra rev 5.7 e il piu' povero dei riferimenti. **Sono numeri che
    dipendono dall'implementazione**: cambiare il numero di bin, o passare a
    una luminanza gamma invece che Rec. 709, sposterebbe tutto e le soglie
    diventerebbero arbitrarie senza che nessuno se ne accorga.

    Questo test ancora l'implementazione ai valori misurati sulle tre immagini
    di riferimento, che non cambiano mai.
    """
    r = subprocess.run(
        ["node", "scripts/densita.mjs",
         f"docs/design-reference/famiglia-a/{immagine}.png"],
        cwd=RADICE, capture_output=True, text=True, timeout=300,
    )
    riga = r.stdout.splitlines()[0]
    misurato = {
        "dev": float(re.search(r"dev\s+([\d.]+)", riga).group(1)),
        "H": float(re.search(r"H\s+([\d.]+)", riga).group(1)),
    }
    assert abs(misurato["dev"] - dev) < 0.15, f"{riga}\natteso dev {dev}"
    assert abs(misurato["H"] - entropia) < 0.02, f"{riga}\nattesa entropia {entropia}"


@pytest.mark.slow
def test_ogni_soglia_boccia_noi_e_almeno_un_riferimento_la_raggiunge():
    """Due proprieta', e una soglia che non le ha entrambe non serve a niente.

      **boccia noi**       sopra il nostro valore di oggi, o non boccerebbe
                           mai nulla — e' esattamente il difetto per cui
                           `L>25` e' stata ritirata
      **raggiungibile**    almeno uno dei tre riferimenti la supera, o e' un
                           desiderio e verra' abbassata al primo fastidio

    ⚠️ **Trovato da questo test**: la soglia `L>60 ≥ 25 %` viene da
    `famiglia-a/01` (42,1 %), ma `famiglia-a/05` misura **24,0 %** e la
    mancherebbe di un punto. Resta a 25 — l'ha fissata `README.md` e le altre
    due immagini la superano — ma non e' vero che «il riferimento la
    raggiunge»: la raggiungono due su tre. Dichiarato in
    `docs/acceptance/TOKENS-RIEMPIMENTO.md`.
    """
    sorgente = (RADICE / "scripts" / "densita.mjs").read_text(encoding="utf-8")
    soglie = {
        n: float(v) for n, v in
        re.findall(r"^\s*(devStd|entropia|riempito):\s*([\d.]+)", sorgente, re.M)
    }
    #  nome        noi (ws-01 5.10)   i tre riferimenti: 01, 10, 05
    CASI = [("devStd", 19.1, [55.7, 41.9, 40.6]),
            ("entropia", 1.29, [3.32, 3.05, 2.85]),
            ("riempito", 6.0, [42.1, 34.8, 24.0])]
    for nome, nostro, riferimenti in CASI:
        assert soglie[nome] > nostro, (
            f"la soglia {nome} = {soglie[nome]} non e' sopra il nostro "
            f"{nostro}: non boccerebbe niente, come L>25"
        )
        raggiungono = [r for r in riferimenti if r >= soglie[nome]]
        assert raggiungono, (
            f"nessuno dei tre riferimenti raggiunge {nome} = {soglie[nome]}: "
            f"e' un desiderio, non una soglia"
        )


@pytest.mark.slow
def test_l_audit_non_ha_APERTO_la_banda_media():
    """Rev 5.8 — il controllo dell'ampliamento.

    Aggiungere `--fill-1..3` e `--manila` alla famiglia "colore" allarga
    l'insieme dei colori ammessi. La domanda che segue e' di QUANTO: di
    quattro colori, o di tutta la banda in cui stanno? Fra L 40 e L 150 ci
    sono decine di migliaia di grigi, e battere a mano quello che «sta
    bene» e' esattamente cio' che l'invariante 18 vieta — ed esattamente cio'
    che il passo dei 18 componenti sara' tentato di fare.

    La fixture usa tre grigi inventati in quella banda e un letterale UGUALE a
    `--fill-1`. I tre grigi devono cadere a tutti e due i livelli; il quarto
    solo al livello 2, perche' il valore calcolato ormai sta nella palette — ed
    e' la dimostrazione piu' pulita del perche' il livello 2 esiste.
    """
    r = subprocess.run(
        ["node", "scripts/audit.mjs", "non-conforme-banda"],
        cwd=RADICE, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    e = json.loads(r.stdout.strip().splitlines()[-1])[0]

    calcolate = {g["trovato"]
                 for c in (e.get("dettaglioCalcolato") or [])
                 for g in c["guasti"] if g["prop"] == "background-color"}
    sorgente = {g["selettore"] for g in (e.get("dettaglioSorgente") or [])
                if g["prop"] == "background-color"}

    for atteso in ("rgb(41, 52, 58)", "rgb(61, 79, 87)", "rgb(71, 101, 111)"):
        assert atteso in calcolate, (
            f"{atteso} e' un grigio inventato nella banda dei riempimenti e "
            f"l'audit non lo vede piu': l'ampliamento della rev 5.9 ha aperto "
            f"la banda invece dei sei colori"
        )
    assert {".fx-banda__a", ".fx-banda__b", ".fx-banda__c"} <= sorgente

    assert "rgb(50, 70, 79)" not in calcolate, (
        "il letterale uguale a --fill-1 NON deve cadere al livello 1: calcola "
        "a un colore che sta nella palette. Se cade, il livello 1 sta "
        "segnalando i riempimenti leciti e il passo dopo si fermera' subito"
    )
    assert ".fx-banda__d" in sorgente, (
        "il letterale uguale a --fill-1 e' sfuggito anche al livello 2: "
        "l'invariante 18 dice «zero valori letterali», non «valori che stanno "
        "nella palette», e senza il livello 2 nessuno lo verifica"
    )


@pytest.mark.slow
def test_le_DUE_regole_sull_ombra_cadono_separatamente():
    """Rev 5.13 — l'invariante 19 riformulata, e le sue due metà verificabili.

    Per due fasi la regola era una sola, decisa sul rilievo R2: «un'ombra
    esterna e' ammessa se SCURISCE». Era una toppa su una contraddizione —
    l'invariante vietava ogni drop-shadow, §10.1 ne dichiarava una, `app.css`
    la spegneva — e ADR-010 l'ha resa insostenibile: con i pannelli che si
    sovrappongono l'ombra e' cio' che li tiene distinguibili.

    Adesso le regole sono due, e questa prova che cadono per ragioni diverse:

      alone      un'ombra piu' CHIARA del fondo — il glow della Famiglia B
      tinta      un'ombra piu' scura del fondo ma COLORATA

    ⚠️ Il secondo caso e' costato due tentativi. `rgba(0,40,90)` e
    `rgba(0,20,60)` cadevano sulla prima regola, non sulla seconda: sono piu'
    chiari di `--bg-void`, perche' il canale blu pesa poco ma a 60 vale gia'
    meta' della luminanza del fondo. Un caso di prova che non prova la regola
    per cui e' stato scritto e' peggio di nessun caso.
    """
    r = subprocess.run(
        ["node", "scripts/audit.mjs", "non-conforme"],
        cwd=RADICE, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    e = json.loads(r.stdout.strip().splitlines()[-1])[0]
    ombre = {g["trovato"].split(")")[0] + ")": g["atteso"]
             for c in (e.get("dettaglioCalcolato") or [])
             for g in c["guasti"] if g["prop"] == "box-shadow"}

    alone = next((v for k, v in ombre.items() if "77, 208, 225" in k), None)
    tinta = next((v for k, v in ombre.items() if "0, 8, 40" in k), None)
    assert alone and "SCURIRE" in alone, f"l'alone ciano non e' segnalato: {ombre}"
    assert tinta and "NERA" in tinta, (
        f"l'ombra blu SCURA non cade sulla regola della tinta: {ombre}. "
        f"Se cade su quella dell'alone, il caso di prova e' troppo chiaro e "
        f"la regola nuova resta non provata"
    )


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
      import { COLONNE, RIGHE, MODULI, CATEGORIE, dellaCategoria,
               composizioneIniziale, moduliDelDock }
        from './ui/src/desk/moduli.js';
      console.log(JSON.stringify({
        colonne: COLONNE, righe: RIGHE,
        categorie: CATEGORIE,
        dock: moduliDelDock().map((m) => m.id),
        moduli: MODULI.map((m) => ({ id: m.id, categoria: m.categoria,
                                     cella: m.cella, modulo: !!m.modulo,
                                     suRichiesta: !!m.suRichiesta })),
        perCategoria: CATEGORIE.map((c) => dellaCategoria(c.n).map((m) => m.id)),
        iniziale: composizioneIniziale().map((m) => m.id),
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


def test_ogni_categoria_copre_la_griglia_senza_buchi():
    """§11.6 regola 3, resa aritmetica — e riscritta da ADR-010.

    Si chiamava `test_ogni_workspace_e_pieno_e_senza_sovrapposizioni`, e
    chiedeva che ogni cella di ogni **workspace** fosse coperta esattamente una
    volta. Aveva ragione finche' i workspace erano pagine.

    Con una scrivania sola le celle non sono piu' gabbie: sono **posizioni
    iniziali**, e i pannelli di categorie diverse si sovrappongono di proposito
    (§26.2). La proprieta' che resta, e che vale ancora la pena imporre, e' che
    la disposizione dichiarata di **una categoria** sia leggibile: nessun buco,
    nessuna coppia di pannelli della stessa categoria che nasce uno sopra
    l'altro.
    """
    r = _moduli()
    guasti = []
    for c in r["categorie"]:
        copertura = {}
        for m in r["moduli"]:
            if m["categoria"] != c["n"] or m["suRichiesta"]:
                continue
            col, riga, dc, dr = m["cella"]
            assert 0 <= col and col + dc <= r["colonne"], f"{m['id']} esce dalla griglia"
            assert 0 <= riga and riga + dr <= r["righe"], f"{m['id']} esce dalla griglia"
            for x in range(col, col + dc):
                for y in range(riga, riga + dr):
                    copertura.setdefault((x, y), []).append(m["id"])
        doppie = {k: v for k, v in copertura.items() if len(v) > 1}
        vuote = [
            (x, y) for x in range(r["colonne"]) for y in range(r["righe"])
            if (x, y) not in copertura
        ]
        if doppie:
            guasti.append(f"categoria 0{c['n']} sovrapposizioni: {doppie}")
        if vuote:
            guasti.append(f"categoria 0{c['n']} celle scoperte: {vuote}")
    assert not guasti, "\n".join(guasti)


def test_le_categorie_si_sovrappongono_fra_loro_ED_E_IL_PUNTO():
    """L'altra meta' di ADR-010, enunciata invece che subita.

    Se le quattro categorie NON si sovrapponessero, vorrebbe dire che ognuna
    occupa un quarto di griglia — cioe' che i quattro workspace sono
    sopravvissuti come quadranti, e la pagina si sarebbe solo rimpicciolita.
    """
    r = _moduli()
    per_cella = {}
    for m in r["moduli"]:
        if m["suRichiesta"]:
            continue
        col, riga, dc, dr = m["cella"]
        for x in range(col, col + dc):
            for y in range(riga, riga + dr):
                per_cella.setdefault((x, y), set()).add(m["categoria"])
    condivise = [k for k, v in per_cella.items() if len(v) > 1]
    assert len(condivise) > r["colonne"] * r["righe"] // 2, (
        f"solo {len(condivise)} celle su {r['colonne'] * r['righe']} sono "
        f"condivise fra categorie: la scrivania e' ancora quattro pagine, "
        f"messe una accanto all'altra"
    )


def test_ogni_categoria_ha_almeno_due_pannelli():
    """Una categoria a un pannello non e' una categoria, e' un pannello."""
    r = _moduli()
    for c, elenco in zip(r["categorie"], r["perCategoria"]):
        assert len(elenco) >= 2, f"categoria 0{c['n']} ha {len(elenco)} pannelli"


def test_la_composizione_iniziale_e_TUTTO_meno_i_su_richiesta():
    """ADR-010: «chi apre tutto insieme ottiene una scrivania affollata. E' il
    punto.» All'avvio la scelta la facciamo noi, e la facciamo su una misura
    del budget di frame — vedi `docs/acceptance/ADR-010.md`.

    ⚠️ `gesture` resta fuori: comparirebbe la spia di §14 accesa per una
    telecamera spenta.
    """
    r = _moduli()
    attesi = [m["id"] for m in r["moduli"] if not m["suRichiesta"]]
    assert r["iniziale"] == attesi
    assert "gesture" not in r["iniziale"]


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


def test_anche_app_main_js_e_sorvegliato_sui_backtick() -> None:
    """Il buco del test qui sopra, trovato battendoci dentro la settima volta.

    `test_nessun_backtick_dentro_i_template_letterali` guarda i fogli di stile
    di `ui/src`. Ma lo stesso guasto — un backtick dentro un commento chiude il
    template literal e il modulo non parte — vive identico in `app/main.js`,
    dove `executeJavaScript` porta interi programmi dentro un template.
    Li' e' successo
    due volte in questo progetto, e nessuno guardava.

    Il controllo e' grossolano di proposito: si contano i backtick e si chiede
    che siano PARI. Un template aperto e mai chiuso e' dispari, ed e'
    esattamente il guasto. Contare le coppie senza capire la sintassi non
    trova ogni errore possibile, ma trova questo — e questo e' quello che
    succede davvero.
    """
    for f in ("app/main.js", "app/preload.js", "scripts/prova-gesti.mjs"):
        testo = (RADICE / f).read_text(encoding="utf-8")
        # I backtick dentro una stringa normale non contano: qui non ce ne sono
        # e se un giorno ce ne fossero il test lo direbbe, il che va bene.
        assert testo.count("`") % 2 == 0, (
            f"{f}: numero DISPARI di backtick — un template literal resta "
            f"aperto, e il file non si carica"
        )
