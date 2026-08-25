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
    # §26.5 — la cartella contenitore. `chrome` copre anche lo strato
    # delle icone libere, che e' cornice dell'ambiente come barra e dock.
    "cartella", "meteo",
    # §26 — i quattro archetipi strutturali
    "calendario", "tabella", "lettura", "ciambella",
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
      import { COLONNE, RIGHE, MODULI, CATEGORIE, SCENE, dellaCategoria,
               composizioneIniziale, moduliIndicizzati }
        from './ui/src/desk/moduli.js';
      console.log(JSON.stringify({
        colonne: COLONNE, righe: RIGHE,
        categorie: CATEGORIE,
        dock: moduliIndicizzati().map((m) => m.id),
        moduli: MODULI.map((m) => ({ id: m.id, categoria: m.categoria,
                                     cella: m.cella, modulo: !!m.modulo,
                                     suRichiesta: !!m.suRichiesta,
                                     fuoriPiastrellatura: !!m.fuoriPiastrellatura })),
        perCategoria: CATEGORIE.map((c) => dellaCategoria(c.n).map((m) => m.id)),
        iniziale: composizioneIniziale().map((m) => m.id),
        scene: SCENE.map((s) => ({ nome: s.nome, pannelli: s.pannelli })),
        // La `min-width` che ogni componente dichiara nel proprio foglio, in
        // unita' di --grid. E' la misura che una cella di scena deve
        // rispettare, e leggerla dal SORGENTE e' l'unico modo di non
        // ricopiarla a mano in due posti.
        minGrid: Object.fromEntries(MODULI.map((m) => {
          const css = m.componente.css ?? '';
          const g = css.match(/min-width:\\s*calc\\(var\\(--grid\\)\\s*\\*\\s*([\\d.]+)\\)/);
          return [m.id, g ? Number(g[1]) : 0];
        })),
      }));
    """))


# ── §26.5 — icone libere e cartelle contenitore ──────────────────────────────


def test_in_innerHTML_entrano_solo_costanti_del_modulo():
    """R96, trovato costruendo §26.5 e non da un test.

    `ui/src/panels/files.js` interpolava `v.name` dentro `innerHTML`. Un nome di
    file arriva dal disco, e l'invariante 5 lo classifica dato NON FIDATO
    quanto il contenuto: un file chiamato con del markup scriveva markup dentro
    l'interfaccia — e l'interfaccia ha `window.jarvis`, cioe' la funzione che
    risponde alle conferme di §6.2. Un nome ben scelto, in una cartella
    scaricata, poteva approvare da solo una richiesta gia' a schermo.

    ## La regola, e perche' e' questa e non «niente innerHTML»

    Ogni pannello costruisce il proprio SCHELETRO con `innerHTML` da un
    template che interpola `meta.versione` e nient'altro: quello e' un
    letterale del nostro sorgente, e vietarlo costringerebbe a riscrivere
    quattordici componenti senza guadagnare un grammo di sicurezza.

    Il confine giusto e' quindi: **dentro un `innerHTML` possono entrare solo
    identificatori dichiarati al primo livello del modulo.** Un parametro —
    `msg`, `v`, `url`, `f` — e' per definizione roba che arriva da fuori, e non
    entra. Non serve sapere caso per caso da dove venga un valore, ed e'
    esattamente la valutazione che e' andata storta la prima volta.
    """
    guasti = []
    for f in sorted((RADICE / "ui/src").rglob("*.js")):
        testo = f.read_text(encoding="utf-8")
        # Cio' che il modulo dichiara al primo livello: `const X`, `let X`,
        # `function X`, `class X` e gli import. L'indentazione zero e' il
        # discrimine, e in questo albero e' affidabile.
        modulo = set(re.findall(
            r"^(?:export\s+)?(?:const|let|var|function|class)\s+(\w+)",
            testo, re.MULTILINE))
        modulo |= set(re.findall(r"^import\s+\*\s+as\s+(\w+)", testo, re.MULTILINE))
        modulo |= set(re.findall(r"^import\s*\{([^}]*)\}", testo, re.MULTILINE)
                      and re.findall(r"(\w+)(?:\s+as\s+\w+)?\s*(?:,|$)",
                                     " ".join(re.findall(r"^import\s*\{([^}]*)\}",
                                                         testo, re.MULTILINE)))
                      or [])
        for m in re.finditer(r"innerHTML\s*\+?=\s*`", testo):
            chiusura = testo.find("`", m.end())
            corpo = testo[m.end():chiusura]
            riga = testo[: m.start()].count(chr(10)) + 1
            for espressione in re.findall(r"\$\{([^}]*)\}", corpo):
                for radice_id in re.findall(r"[A-Za-z_$][\w$]*", espressione):
                    if radice_id in modulo or radice_id in {
                        "true", "false", "null", "undefined", "toFixed",
                        "String", "Number", "Math", "JSON", "new", "typeof",
                    }:
                        continue
                    # Le proprieta' dopo un punto non sono identificatori
                    # liberi: conta la radice dell'espressione.
                    if re.search(rf"\.\s*{re.escape(radice_id)}\b", espressione):
                        continue
                    guasti.append(
                        f"{f.relative_to(RADICE)}:{riga}: ${{{espressione.strip()[:40]}}}"
                        f" — «{radice_id}» non e\' del modulo"
                    )
    assert not guasti, (
        "in innerHTML entra un valore che non e' una costante del modulo: se "
        "viene dal disco, dalla rete o da un feed e' iniezione di markup nel "
        "renderer (invariante 5)\n" + "\n".join(sorted(set(guasti)))
    )


def test_le_icone_libere_stanno_sotto_i_pannelli():
    """§26.5: «sotto i pannelli (`--z-pannelli`) e sopra il nucleo di §25».

    `--z-pannelli` e' 10 — dove WinBox comincia — e `--z-presenza` e' 0. Un
    numero fuori da quella fessura non e' un dettaglio estetico: sopra, le
    icone coprirebbero le finestre; sotto, sparirebbero dietro il fondo di §25
    il giorno in cui arrivera'.
    """
    css = (RADICE / "ui/src/style/app.css").read_text(encoding="utf-8")
    m = re.search(r"--z-icone:\s*(\d+)", css)
    assert m, "app.css non dichiara --z-icone"
    assert 0 < int(m.group(1)) < 10, f"--z-icone = {m.group(1)}"

    icone = (RADICE / "ui/src/desk/icone.js").read_text(encoding="utf-8")
    assert "z-index: var(--z-icone)" in icone, (
        "lo strato non usa il valore dichiarato: due numeri per lo stesso "
        "piano divergono al primo che qualcuno cambia"
    )
    # E non deve poter rubare i clic ai pannelli che gli stanno sotto: e' lo
    # stesso inciampo che il contenitore del catalogo ha gia' avuto.
    assert "pointer-events: none" in icone


def test_una_cartella_si_apre_come_gli_ALTRI_pannelli():
    """R94 — una sola strada per fare una finestra.

    Una `apriCartella()` che costruisse la propria cornice sarebbe un SECONDO
    modo di aprire un pannello, e i due divergerebbero al primo comportamento
    aggiunto a uno solo: la geometria salvata, il ripristino, `alterna`, il
    conteggio del dock. `desk/icone.js` passa dal registro dinamico della
    scrivania e da li' in poi una cartella e' un pannello come il globo.
    """
    icone = (RADICE / "ui/src/desk/icone.js").read_text(encoding="utf-8")
    assert "new WinBox" not in icone
    assert "creaCornice" not in icone
    assert "scrivania?.registra(" in icone

    scrivania = (RADICE / "ui/src/desk/scrivania.js").read_text(encoding="utf-8")
    for nome in ("function registra(", "function dimentica(", "function def("):
        assert nome in scrivania, f"la scrivania non espone {nome}"


def test_il_fondo_manda_al_core_ESATTAMENTE_i_campi_dello_schema():
    """Il renderer non inventa campi, e il core non ne riceve di ignoti.

    `core/layout.py` ha `extra="forbid"`: una chiave in piu' non e' un campo
    ignorato, e' un messaggio RIFIUTATO — cioe' la disposizione che smette di
    salvarsi, in silenzio, per tutti quanti.
    """
    import ast

    icone = (RADICE / "ui/src/desk/icone.js").read_text(encoding="utf-8")
    corpo = icone[icone.index("function stato()"):]
    corpo = corpo[: corpo.index("\n  }")]
    campi_icona = set(re.findall(r"(\w+):\s*(?:!!)?i\.", corpo))
    campi_cartella = set(re.findall(r"(\w+):\s*(?:!!)?c\.", corpo))

    sorgente = (RADICE / "core/layout.py").read_text(encoding="utf-8")
    albero = ast.parse(sorgente)

    def campi(classe: str) -> set[str]:
        nodo = next(n for n in albero.body
                    if isinstance(n, ast.ClassDef) and n.name == classe)
        return {s.target.id for s in nodo.body if isinstance(s, ast.AnnAssign)}

    assert campi_icona == campi("IconaLibera"), campi_icona
    assert campi_cartella == campi("CartellaLibera"), campi_cartella


def test_estrarre_e_scorrere_si_distinguono_per_DIREZIONE():
    """R95 — lo stesso `pointerdown` comincia due gesti diversi.

    Premere una tessera comincia sia lo scorrimento del nastro (§26.4) sia
    l'estrazione dell'icona (§26.5).

    ⚠️ R98 — la prima regola era «piu' verticale che orizzontale», e col
    puntatore vero non funzionava: `dx=+775, dy=-416` e' un gesto piu'
    orizzontale che verticale ed e' inequivocabilmente un'estrazione. La regola
    giusta e' geografica e non trigonometrica: **il puntatore esce dalla fascia
    del nastro.** Uno scorrimento ci resta dentro per costruzione.

    Senza soglia, una sbandata di due pixel tirerebbe fuori un'icona.
    """
    cat = (RADICE / "ui/src/desk/catalogo.js").read_text(encoding="utf-8")
    m = re.search(r"const SOGLIA_ESTRAZIONE = (\d+)", cat)
    assert m, "il catalogo non dichiara una soglia di estrazione"
    assert int(m.group(1)) >= 8, "una soglia troppo bassa e' nessuna soglia"
    codice = re.sub(r"/\*.*?\*/|//[^\n]*", "", cat, flags=re.S)
    assert "Math.abs(dy) > Math.abs(dx)" not in codice, (
        "e' tornata la regola del rapporto fra dx e dy: R98 l'ha misurata "
        "sbagliata con un puntatore vero"
    )
    assert "fascia.top - e.clientY > SOGLIA_ESTRAZIONE" in codice, (
        "manca la regola dell'uscita dalla fascia: senza, un trascinamento "
        "obliquo scorre il nastro invece di tirare fuori l'icona"
    )
    # Deciso per l'estrazione, il nastro torna dov'era.
    assert "porta(presa.xIniziale, false)" in cat


def test_il_catalogo_ha_le_proporzioni_del_riferimento():
    """§26.3 — la barra delle applicazioni era il doppio del riferimento.

    Misurato su `famiglia-a/01` (901x563) con `scripts/profilo.mjs`, e passato
    da una verifica indipendente che ha smentito quattro numeri della prima
    lettura (bordo sinistro 153 e non 146, destro 495 e non 488 — 488..493 e'
    la canaletta della barra di scorrimento — bordo alto 445 e non 447, e il
    pannello NON e' centrato):

        pannello   343 x ~105 px   ->   38,1 % x ~18,7 % dello schermo

    Il nostro era 990 x 225 su 1536x843, cioe' **64,5 % x 26,7 %**: 1,69 volte
    piu' largo e 1,40 piu' alto.

    ⚠️ Si controlla la LARGHEZZA e non l'altezza: la larghezza e' dichiarata in
    CSS e si calcola dal sorgente, l'altezza e' la somma di sei fasce di testo
    e dipende dal font caricato. L'altezza la misura il ciclo §11.7 sullo
    scatto, che e' il posto dove si guarda.
    """
    css = (RADICE / "ui/src/desk/catalogo.js").read_text(encoding="utf-8")
    # La larghezza e' un PRODOTTO di frazioni dichiarate, non un numero solo:
    # «calc(var(--grid) * 5.5 * 0.7)». Si moltiplicano tutte, cosi' il giorno
    # che qualcuno ne aggiunge una il test la vede invece di leggere la prima.
    m = re.search(r"\.cat \{[^}]*?width:\s*calc\(var\(--grid\)((?:\s*\*\s*[\d.]+)+)\)",
                  css, re.S)
    assert m, "il catalogo non dichiara una larghezza in unita' di --grid"
    grid = 110          # --grid, da tokens.css
    fattori = [float(x) for x in re.findall(r"[\d.]+", m.group(1))]
    larghezza = grid
    for f in fattori:
        larghezza *= f
    frazione = larghezza / 1536

    """⚠️ LA BANDA E' CAMBIATA IL 22 AGOSTO 2026, e va letto prima di crederci.

    Fino a quel giorno era 34-43 %, cioe' il 38,1 % del riferimento con un
    margine. Il catalogo dichiarava «--grid * 5.5» = 605 px = **39,4 %**: in
    banda, e per costruzione.

    Poi il proprietario ha scelto di ridurlo del 30 % (istruzione C3), e
    423,5 px sono il **27,6 %**: fuori banda, e piu' LONTANO dal riferimento di
    quanto fosse prima. Non e' una deriva scoperta dopo — e' una decisione, e
    questo test smette di misurare la fedelta' al riferimento per misurare la
    fedelta' alla decisione.

    La banda resta stretta perche' serve ancora a bocciare il difetto da cui
    nasce: il catalogo a 990 px, cioe' il 64,5 %, che si mangiava mezza
    scrivania. Chi volesse tornare al riferimento tolga il fattore 0.7 e
    rimetta 0.34-0.43 qui: e' un numero in un posto solo."""
    assert 0.25 <= frazione <= 0.30, (
        f"il catalogo occupa il {frazione:.1%} della larghezza dello schermo; "
        "la decisione del 22 agosto 2026 lo mette al 27,6 %, e il riferimento "
        "ne occupa il 38,1 % — vedi il commento qui sopra"
    )


def test_il_catalogo_non_e_centrato_come_il_riferimento():
    """Il riferimento ha il pannello a x 153..495 su 901: margine sinistro
    17 %, destro 45 %, rapporto 1 : 2,65.

    Non e' un dettaglio di gusto: quel 45 % e' dove il riferimento tiene le
    cartelle manila, cioe' il fondo di §26.5. Un catalogo centrato le
    spingerebbe sotto i pannelli o fuori campo.
    """
    css = (RADICE / "ui/src/desk/catalogo.js").read_text(encoding="utf-8")
    ancora = re.search(r"\.cat-ancora \{(.*?)\}", css, re.S)
    assert ancora, "manca la regola .cat-ancora"
    corpo = ancora.group(1)
    assert "justify-content: center" not in corpo, (
        "il catalogo e' tornato centrato: il riferimento non lo e', e il "
        "margine destro e' il posto delle cartelle di §26.5"
    )
    assert re.search(r"padding-left:\s*\d+%", corpo), (
        "il decentramento va dichiarato come frazione, non con un margine auto"
    )


def test_il_plinto_non_porta_parole():
    """Nel riferimento le cinque icone del plinto sono forme e basta.

    Le etichette di testo sotto le icone erano la causa per cui il plinto
    valeva il 32 % dell'altezza del pannello invece del 24 %, rubando lo
    spazio alla griglia — che nel riferimento ne vale il 53 % e da noi ne
    valeva il 39 %.

    Il nome non sparisce: passa a `title` e ad `aria-label`.
    """
    src = (RADICE / "ui/src/desk/catalogo.js").read_text(encoding="utf-8")
    corpo = src[src.index("function disegnaPlinto("):]
    corpo = corpo[: corpo.index("return [...azioni.children]")]
    assert "createTextNode" not in corpo
    # L'unico `textContent` ammesso e' quello che SVUOTA il pavimento.
    assegnazioni = re.findall(r"(\w+)\.textContent\s*=\s*(.+)", corpo)
    for chi, cosa in assegnazioni:
        assert chi == "azioni" and cosa.strip().startswith('""'), (
            f"un'icona del plinto porta di nuovo del testo: {chi}.textContent = {cosa}"
        )
    for atteso in ("b.title", "aria-label"):
        assert atteso in corpo, f"tolto il testo, manca {atteso}"


def test_il_plinto_e_la_barra_delle_applicazioni():
    """La richiesta, alla lettera: «le icone che stanno sopra a quel pavimento,
    usando anime.js devi poter cambiare quelle icone in base a quella nav che
    sta poco sopra».

    §26.3 lo scriveva gia' e non era stato costruito: «plinto in prospettiva
    con le icone IN EVIDENZA». Il plinto mostrava invece tre comandi
    dell'AMBIENTE — nascondi tutto, affianca, togli il filtro — che con la
    categoria non c'entrano niente e sono passati nella riga delle linguette.

    ⚠️ Il pavimento e la griglia leggono la **stessa** funzione `voci()`. Due
    elenchi della stessa cosa divergono al primo filtro aggiunto a uno solo:
    e' la ragione per cui il dock aveva ceduto l'indice al catalogo invece di
    tenerne una copia.
    """
    src = (RADICE / "ui/src/desk/catalogo.js").read_text(encoding="utf-8")
    codice = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)

    assert "function cambiaPlinto()" in codice
    # Cambia linguetta -> ripopola il pavimento.
    apri = codice[codice.index("function apri(id)"):]
    apri = apri[: apri.index("\n  }")]
    assert "cambiaPlinto()" in apri, (
        "cambiare linguetta non ripopola il pavimento: le icone non seguono "
        "la categoria"
    )
    # Una sola sorgente per griglia e pavimento.
    cambia = codice[codice.index("function cambiaPlinto()"):]
    cambia = cambia[: cambia.index("function apri(id)")]
    assert "voci()" in cambia, "il pavimento ha un elenco suo, diverso dalla griglia"

    # anime.js, non una transizione CSS: e' un evento, non uno stato (§26.4).
    assert "animate(" in cambia and "stagger(" in cambia, (
        "il cambio di icone non passa da anime.js"
    )
    # E ha una CAUSA: parte dal clic, non da un timer (invariante 25).
    assert "setInterval" not in cambia and "setTimeout" not in cambia


def test_il_catalogo_non_ha_un_piede():
    """Il riferimento non ne ha uno: sotto il plinto c'e' il bordo del
    pannello. I nostri 19,5 px di piede erano un dodicesimo dell'altezza spesi
    per due righe che si dicono altrove — il conteggio e la versione stanno
    nella riga delle linguette, dove il riferimento lascia meta' riga vuota.
    """
    src = (RADICE / "ui/src/desk/catalogo.js").read_text(encoding="utf-8")
    assert ".cat__piede" not in src, "il piede e' tornato"
    assert "cat__stato" in src, "il conteggio non ha piu' un posto"


def test_l_indice_ha_gli_otto_moduli_di_13_piu_quelli_dichiarati_dopo():
    """La tabella di §13 ha otto righe, e restano otto.

    ⚠️ L'elenco non e' piu' CHIUSO a otto: §26 ne aggiunge — `meteo` e' il
    primo. Il test resta utile lo stesso, e in una forma migliore: **gli otto
    di §13 devono esserci tutti e nell'ordine**, e cio' che si aggiunge dopo
    va aggiunto QUI insieme alla sezione che lo introduce. Un modulo che
    comparisse senza toccare questa riga sarebbe entrato nell'indice senza che
    nessuno lo abbia deciso.

    Si chiamava `test_il_dock_ha_...`: da §26.3 l'indice sta nel catalogo.
    """
    r = _moduli()
    OTTO = [
        "telemetria", "agenti", "console",     # 01 sistema
        "file", "sorgente",                    # 02 file
        "browser", "news",                     # 03 web
        "globo",                               # 04 3D
    ]
    DOPO = ["meteo"]                           # §26
    assert [m for m in r["dock"] if m in OTTO] == OTTO
    assert sorted(set(r["dock"]) - set(OTTO)) == sorted(DOPO), (
        "un modulo e' entrato nell'indice senza passare da questa riga"
    )


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
            # `fuoriPiastrellatura`: i moduli aggiunti DOPO §13 non hanno un
            # quarto di griglia da riempire — la piastrellatura era la
            # disposizione di quando le categorie erano pagine, e le scene
            # l'hanno sostituita (§26.6). Chi la dichiara lo dice nel registro.
            if (m["categoria"] != c["n"] or m["suRichiesta"]
                    or m["fuoriPiastrellatura"]):
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


def test_la_composizione_iniziale_e_una_SCENA():
    """§26.6, e la correzione di ADR-010.

    ADR-010 diceva «si apre tutto, e la scrivania affollata e' il punto». La
    misura ha detto altro: le celle di `moduli.js` sono quattro piastrellature
    COMPLETE della stessa griglia, una per categoria, e aprirle insieme produce
    una **cascata diagonale** in cui di quattordici pannelli se ne leggono due.
    Peggio delle quattro pagine che ADR-010 aveva tolto.

    Il difetto non erano le pagine: era che **niente componeva**. La
    disposizione predefinita e' adesso una scena, e questo test impedisce che
    torni a essere «tutto».
    """
    r = _moduli()
    assert r["scene"], "nessuna scena predefinita: la scrivania si comporrebbe da sola"
    iniziale = r["scene"][0]
    assert r["iniziale"] == [p["id"] for p in iniziale["pannelli"]]
    tutti = [m["id"] for m in r["moduli"] if not m["suRichiesta"]]
    assert len(r["iniziale"]) < len(tutti), (
        "la composizione iniziale e' di nuovo TUTTO: e' una cascata, non una "
        "composizione"
    )
    # `gesture` resta fuori: comparirebbe la spia di §14 accesa per una
    # telecamera spenta.
    assert "gesture" not in r["iniziale"]


def test_ogni_cella_di_scena_rispetta_la_min_width_del_pannello():
    """R99 — la cella non stringe il pannello: lo fa DEBORDARE.

    Trovato guardando lo scatto. Il primo giro della scena di avvio metteva
    `console` e `anelli` negli angoli bassi, larghi due colonne: `console`
    dichiara `min-width: calc(var(--grid) * 4)`, cioe' 440 px contro i 256 di
    due colonne, ed e' finito sotto il catalogo; `anelli` ne dichiara 3 ed e'
    uscito dallo schermo a destra.

    ⚠️ La conseguenza vale oltre questa scena: **la fascia bassa ai lati del
    catalogo non puo' ospitare nessun pannello.** Il catalogo e' largo 9
    colonne su 12 e centrato, quindi ai lati restano 2 colonne, e la min-width
    piu' piccola di tutto il sistema e' 3. Quella fascia e' il fondo di §26.5,
    dove stanno le icone libere e le cartelle — che e' esattamente dove il
    riferimento le mette.

    La larghezza di una colonna dipende dallo schermo; la min-width no. Qui si
    misura sullo schermo su cui l'ambiente gira davvero.
    """
    LARGHEZZA = 1536      # la finestra massimizzata su questa macchina
    GRID = 110            # --grid, da tokens.css
    r = _moduli()
    colonna = LARGHEZZA / r["colonne"]

    guasti = []
    for scena in r["scene"]:
        for p in scena["pannelli"]:
            minimo = r["minGrid"].get(p["id"], 0) * GRID
            larghezza = p["cella"][2] * colonna
            if minimo and larghezza < minimo:
                guasti.append(
                    f"scena «{scena['nome']}»: {p['id']} in {p['cella'][2]} "
                    f"colonne = {larghezza:.0f} px, ma ne dichiara {minimo:.0f}"
                )
    assert not guasti, (
        "una cella troppo stretta non stringe il pannello, lo fa debordare "
        "sotto il catalogo o fuori dallo schermo:\n" + "\n".join(guasti)
    )


# ── §25 — lo strato di presenza ─────────────────────────────────────────────
#
# I test che §25.10 dichiara, per la parte che si puo' verificare leggendo la
# sorgente. Quelli che vogliono un browser vivo — «ferma se inerte», «ferma se
# scollegato» — stanno nel ciclo §11.7 e l'esito e' in
# `docs/acceptance/SEZIONE-25.md`.


def _sorgente(percorso: str) -> str:
    return (RADICE / percorso).read_text(encoding="utf-8")


def test_l_insegna_non_e_un_modulo():
    """§25.3 regole 2 e 4, e §25.10 riga uno.

    Il nucleo non ha una voce nel catalogo, non ha una cella e non si apre.
    Se un giorno qualcuno lo registrasse come modulo — sembra comodo, si
    aprirebbe e si chiuderebbe come tutto il resto — smetterebbe di essere il
    fondo e diventerebbe il quindicesimo pannello.
    """
    r = _moduli()
    ids = {m["id"] for m in r["moduli"]}
    assert "sfondo" not in ids and "insegna" not in ids, (
        "l'insegna e' finita nel registro dei moduli: §25.3 regola 2 dice che "
        "non sta nel dock, e regola 4 che non ha una cella"
    )
    fonte = _sorgente("ui/src/desk/sfondo.js")
    # `cella:` con i due punti, cioe' la PROPRIETA. La parola da sola compare
    # nei commenti — «nella cella centrale che la scena lascia libera» — ed e'
    # li' che c'e' scritto perche' il nucleo una cella non ce l'ha.
    assert "cella:" not in fonte, (
        "sfondo.js dichiara una cella: la geometria dell'insegna viene da "
        "§25.7 (64 % dell'altezza dell'area), non dalla griglia dei pannelli"
    )


def test_l_insegna_non_usa_i_colori_del_dato():
    """§25.5, e §25.10 riga «test_luminanza_nucleo».

    «Il nucleo non usa mai --cy-500 ne' --cy-100. Sono i colori del dato, e il
    dato sta nei pannelli. Un nucleo che compete col dato e' decorazione, ed e'
    il confine con la Famiglia B.»

    L'insegna dipinge su canvas, quindi i colori non passano dal CSS: li legge
    da `style/tokens.js`, che e' la stessa strada dei materiali three.js e degli
    sprite PixiJS. Qui si verifica **due** cose, e la seconda vale piu' della
    prima:

    1. la palette e' fatta di NOMI DI TOKEN e non di esadecimali. La stesura da
       cui questo file viene ne aveva quattro scritti a mano, e l'invariante 18
       non fa eccezioni per il canvas;
    2. fra quei token non ci sono `--cy-500` ne' `--cy-100`.
    """
    fonte = _sorgente("ui/src/desk/sfondo.js")
    import re as _re
    # Un esadecimale a sei cifre fuori dai commenti: e' cosi' che la palette
    # era scritta prima.
    codice = _re.sub(r"/\*.*?\*/", "", fonte, flags=_re.S)
    codice = _re.sub(r"//.*", "", codice)
    esa = _re.findall(r"#[0-9a-fA-F]{6}", codice)
    assert not esa, (
        f"colori letterali nel codice dell'insegna: {esa}. L'invariante 18 non "
        "fa eccezioni per il canvas: si legge da style/tokens.js"
    )
    for vietato in ("--cy-500", "--cy-100"):
        assert vietato not in codice, (
            f"l'insegna usa {vietato}: §25.5 lo vieta senza eccezioni, sono i "
            "colori del dato e il dato sta nei pannelli"
        )


def test_il_livello_dell_insegna_viene_da_un_token():
    """§25.10 riga «test_z_index_dai_token».

    E c'e' una ragione in piu' del principio: `#scrivania > *` alza OGNI figlio
    a --z-cornice, quindi senza una regola dedicata il fondo finirebbe davanti
    a tutto. Il mockup di famiglia-d l'ha misurato con elementsFromPoint.
    """
    css = _sorgente("ui/src/style/app.css")
    assert "--z-insegna:" in css, "il livello dell'insegna non e' un token"
    assert "#scrivania > .sfd { z-index: var(--z-insegna); }" in css, (
        "manca la regola che riporta l'insegna sotto i pannelli: la regola "
        "universale #scrivania > * la alzerebbe a --z-cornice"
    )
    # `z-index:` con i due punti, cioe' la DICHIARAZIONE. La parola da sola
    # compare nel commento del foglio, ed e' li' che c'e' scritto perche' il
    # livello non lo dichiara questo file.
    fonte = _sorgente("ui/src/desk/sfondo.js")
    assert "z-index:" not in fonte, (
        "sfondo.js dichiara un z-index per conto suo: il livello sta in "
        "app.css con gli altri, o sono due verita'"
    )


def test_il_traffico_dell_insegna_non_conta_il_battito():
    """⚠️ **Questo test e\' cambiato di significato, e va detto.**

    Fino al 22 agosto 2026 verificava l\'invariante 25 sullo strato di
    presenza: `rings.js` creava le animazioni con `autoplay: false` e nulla le
    faceva partire se non un nodo attivo in `agent.mesh`. Se girava, stava
    lavorando.

    L\'insegna che l\'ha sostituito **gira sempre**: `giro += P.vel * dt` a ogni
    fotogramma, e la velocita\' e\' un parametro di stato, non un interruttore.
    E\' una deroga consapevole all\'invariante 25, decisa dal proprietario e
    registrata in `docs/acceptance/SEZIONE-25.md`; un test che asserisse il
    contrario sarebbe verde e falso.

    Quello che resta verificabile — e che rende il moto un DATO invece che un
    ornamento — e\' che il tasso di traffico **non conti la telemetria**: quella
    arriva a 2,5 Hz qualunque cosa accada, quindi contarla darebbe un tasso
    costante, cioe\' un\'insegna che dice sempre la stessa cosa.
    """
    fonte = _sorgente("ui/src/desk/sfondo.js")
    assert 'topic === "telemetry"' in fonte and "contati++" in fonte, (
        "l'insegna conta ogni messaggio come traffico: con la telemetria a "
        "2,5 Hz il tasso e' costante e il moto non dice piu' niente"
    )
    i = fonte.index("contati++")
    assert 'topic === "telemetry"' in fonte[:i], (
        "il filtro sulla telemetria deve venire PRIMA del conteggio, o il "
        "battito entra comunque nel tasso"
    )


def test_la_scena_di_avvio_lascia_LIBERO_il_centro():
    """§25, uscita «il centro libero» — e SUPERA la regola che stava qui.

    Fino al 22 agosto 2026 questo test chiedeva l'opposto: che almeno due
    pannelli della scena si sovrapponessero, perche' §26.6 vuole «una
    composizione, non una piastrellatura» e una piastrellatura perfetta e' il
    difetto speculare della cascata.

    La regola non era sbagliata, era incompleta: diceva come NON deve stare
    una scena senza dire attorno a che cosa. §25 lo dice — attorno al nucleo,
    che nel riferimento `famiglia-a/10` e' «circondato dal chrome, non
    coperto» (§25.1, verbatim). Una scena che lascia libero il centro non e'
    una piastrellatura: e' una composizione con un vuoto voluto, ed e' il
    vuoto a impedire la griglia.

    E la misura che ha imposto il cambio: con la scena precedente lo strato di
    presenza arrivava a schermo con **122 pixel su 264.049** di pavimento. Uno
    sfondo dietro cose che lo nascondono non si vede, per quanto poco costi.

    Qui si verifica il vuoto, non la sua estetica:

    1. il punto centrale dell'area non e' coperto da nessun pannello, in
       nessuna riga della griglia;
    2. le colonne libere in TUTTE le righe sono almeno tre, cioe' la fascia
       libera attraversa la scena da cima a fondo e non e' una tasca;
    3. quella fascia copre almeno il 70 % del diametro del nucleo, che §25.7
       fissa al 64 % dell'altezza dell'area. Non il 100 %: la griglia e' di 12
       colonne e `telemetria` ne pretende 5 per la propria min-width, quindi
       una banda centrale di 4 colonne esatte non e' costruibile. L'occlusione
       che resta e' dichiarata in `moduli.js`.
    """
    LARGHEZZA = 1536      # la finestra massimizzata su questa macchina
    ALTEZZA_AREA = 783    # misurata: 843 meno barra e dock
    r = _moduli()
    colonne, righe = r["colonne"], r["righe"]
    avvio = r["scene"][0]

    #: Le colonne coperte, riga per riga.
    coperte = [set() for _ in range(righe)]
    for p in avvio["pannelli"]:
        c0, r0, dc, dr = p["cella"]
        for riga in range(r0, min(righe, r0 + dr)):
            coperte[riga].update(range(c0, min(colonne, c0 + dc)))

    libere = set(range(colonne))
    for riga in coperte:
        libere -= riga

    # 1. il centro: x = larghezza/2 cade sul confine fra le colonne 5 e 6 di 12,
    #    e il nucleo sta li'. Devono essere libere tutte e due, o il centro
    #    geometrico del nucleo e' sotto un pannello.
    centro = {colonne // 2 - 1, colonne // 2}
    assert centro <= libere, (
        f"il centro della scena e' coperto: colonne libere {sorted(libere)}, "
        f"servono almeno {sorted(centro)} — §25.7 mette il nucleo nel centro "
        "geometrico dell'area, e li' non ci puo' essere un pannello"
    )

    # 2. la fascia libera attraversa tutta l'altezza
    assert len(libere) >= 3, (
        f"solo {len(libere)} colonne libere in tutte le righe: il vuoto e' una "
        "tasca, non una fascia, e il nucleo ne resterebbe fuori per meta'"
    )

    # 3. quanto del nucleo ci sta dentro
    fascia = len(libere) * (LARGHEZZA / colonne)
    diametro = ALTEZZA_AREA * 0.64          # §25.7
    assert fascia >= diametro * 0.70, (
        f"la fascia libera e' {fascia:.0f} px e il nucleo ne misura "
        f"{diametro:.0f}: ne resterebbe coperto piu' del 30 %, e §25.1 chiede "
        "«circondato, non coperto»"
    )


def test_i_nomi_che_si_dicono_a_voce_trovano_un_pannello():
    """Cross-lingua: la grammatica T0 e il registro della scrivania.

    `core/llm/grammar.py` elenca i pannelli che «apri il ...» riconosce. Ogni
    nome di quell'elenco deve trovare un modulo, o la frase entra, diventa un
    `ui.intent`, arriva alla scrivania e non apre niente — un comando che
    fallisce in silenzio.

    ⚠️ `impostazioni` **era** l'eccezione dichiarata: la grammatica lo accetta
    dalla Fase 3 e `ui/src/panels/settings.js` era un file da 0 byte. Il test
    lo teneva fissato come debito noto invece di lasciarlo scoprire a voce.

    **Il debito e' chiuso** (§26.7, 25 ago 2026): il pannello esiste, e la lista
    delle eccezioni e' vuota. E' il modo in cui questo test ha fatto il proprio
    mestiere — non impedendo il buco, ma impedendo che si dimenticasse.
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
    assert esito == [], (
        f"nomi che la voce accetta e che non aprono nessun pannello: {esito}. "
        "Una frase che entra, diventa un `ui.intent`, arriva alla scrivania e "
        "non apre niente e' un comando che fallisce in silenzio."
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
