"""`dentroArea()` — il taglio, e la scala provata e ritirata.

`docs/acceptance/LAYOUT-PERSISTENTE.md` punto 11, del 22 agosto 2026:

    «un layout salvato su 2560x1440 e riaperto su 1366x768 non diventa un
    layout piu' piccolo, diventa una pila di pannelli schiacciati contro il
    bordo sinistro, ciascuno largo quanto lo schermo. […] Resta latente, e
    mordera' al primo cambio di monitor vero — che e' l'unico modo di
    verificarla.»

**Non era l'unico modo**, e provarla e' costato meno di un monitor: bastava
spostare la funzione in un modulo suo — e' pura, prende una geometria e un'area
e torna una geometria.

⚠️ **La scala e' stata scritta, misurata e ritirata.** Usava `area_larghezza` e
`area_altezza`, che `core/layout.py` salva e nessuno leggeva. Ha rotto §26.9
criterio 4 — «riaperta l'app, il pannello e' dove l'ho lasciato»: lasciato in
(632, 385), riaperto in (883, 493).

Il difetto non era la scala: era il SEGNALE. Quei due campi non sono lo
schermo, sono il PAVIMENTO — l'area fra barra e dock — e si muovono per ragioni
che con un cambio di monitor non c'entrano: una finestra non ancora
massimizzata, un dock piu' alto. Scalare su un segnale che cambia da solo
sposta la disposizione dell'utente quando nessuno ha cambiato schermo, che e'
il difetto R82 rifatto.

Questi test adesso **fissano il taglio**: descrivono cosa fa, compreso il caso
che il documento chiamava difetto, cosi' che chi riproverà la scala sappia da
dove ripartire — e sappia che serve la dimensione della FINESTRA, non del
pavimento.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from core.layout import (
    MINIMO_ICONA,
    MINIMO_PANNELLO,
    GeometriaPannello,
    IconaLibera,
    Layout,
    adatta,
)

RADICE = Path(__file__).resolve().parent.parent
MODULO = RADICE / "ui" / "src" / "desk" / "geometria-area.js"


def chiama(p: dict, a: dict) -> dict:
    """Esegue `dentroArea` nel vero modulo, senza DOM e senza browser."""
    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    src = (
        f'import {{ dentroArea }} from "{MODULO}";\n'
        f"console.log(JSON.stringify(dentroArea("
        f"{json.dumps(p)}, {json.dumps(a)})));"
    )
    r = subprocess.run(
        ["node", "--input-type=module", "-e", src],
        capture_output=True, text=True, timeout=60, cwd=RADICE,
    )
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


AREA_PICCOLA = {"sinistra": 0, "alto": 32, "larghezza": 1366, "altezza": 700}
AREA_GRANDE = {"larghezza": 2560, "altezza": 1440}


class TestDentroArea:
    def test_TAGLIA_e_lo_fa_come_dichiarato(self) -> None:
        """Il comportamento di oggi, fissato — compreso cio' che
        `LAYOUT-PERSISTENTE.md` punto 11 chiama difetto.

        Un pannello largo 1200 salvato su uno schermo grande resta largo 1200
        su un'area larga 1366: quasi tutto lo schermo, incollato al bordo. E'
        il comportamento vero, e sta scritto qui perche' chi lo cambiera' debba
        cambiare anche questo test — invece di scoprirlo dopo.
        """
        g = chiama({"x": 1300, "y": 800, "larghezza": 1200, "altezza": 600}, AREA_PICCOLA)
        assert g["larghezza"] == 1200
        assert g["altezza"] == 600
        assert g["x"] == AREA_PICCOLA["larghezza"] - 80
        assert g["y"] == AREA_PICCOLA["alto"] + AREA_PICCOLA["altezza"] - 80

    def test_chi_sta_dentro_NON_si_muove(self) -> None:
        """La meta' che conta di piu': un pannello gia' dentro l'area passa
        intatto. E' §26.2 — «nessun riordino automatico» — e ogni tentativo di
        scalare deve continuare a passare di qui.
        """
        p = {"x": 300, "y": 200, "larghezza": 500, "altezza": 400}
        assert chiama(p, AREA_PICCOLA) == {**p}

    def test_resta_sempre_afferrabile(self) -> None:
        """Ottanta pixel di testa a schermo: cio' che non si vede non si
        riprende."""
        g = chiama({"x": 9000, "y": 9000, "larghezza": 400, "altezza": 300}, AREA_PICCOLA)
        assert g["x"] == AREA_PICCOLA["larghezza"] - 80
        assert g["y"] == AREA_PICCOLA["alto"] + AREA_PICCOLA["altezza"] - 80

    def test_piu_grande_dell_area_viene_capato(self) -> None:
        g = chiama({"x": 0, "y": 32, "larghezza": 5000, "altezza": 5000}, AREA_PICCOLA)
        assert g["larghezza"] == AREA_PICCOLA["larghezza"]
        assert g["altezza"] == AREA_PICCOLA["altezza"]


# ── i tre ritagli sono uno ───────────────────────────────────────────────────


def _nel_modulo(sorgente: str) -> object:
    """Esegue un frammento dentro il modulo VERO e ne legge il JSON."""
    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    r = subprocess.run(
        ["node", "--input-type=module", "-e",
         f'import * as G from "{MODULO}";\n{sorgente}'],
        capture_output=True, text=True, timeout=60, cwd=RADICE,
    )
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


#: Le aree su cui si confronta. La prima e' la scrivania vera con il dock di
#: oggi; la seconda ha il dock cresciuto di otto pixel — e' la differenza che
#: ha fatto emergere il difetto; la terza e' un'area senza barra, cioe' il caso
#: in cui i due ritagli COINCIDEVANO anche prima e che quindi non provava
#: niente.
AREE = [
    {"sinistra": 0, "alto": 32, "larghezza": 1536, "altezza": 783},
    {"sinistra": 0, "alto": 32, "larghezza": 1536, "altezza": 775},
    {"sinistra": 0, "alto": 0, "larghezza": 1366, "altezza": 768},
]
#: I punti: dentro, sui due bordi, appena oltre, e molto oltre in entrambi i
#: versi. `-40` e `9999` non sono decorazione: sono i due lati che `max` e
#: `min` trattano separatamente.
PUNTI = [(300, 200), (0, 0), (-40, -40), (700, 700), (720, 745),
         (1500, 800), (9999, 9999)]


class TestITreRitagliSonoUNO:
    """La stessa tabella, fatta girare nei due linguaggi.

    Dentro il renderer il proprietario adesso e' uno: `dentroPunto` in
    `geometria-area.js`, che `desk/icone.js` importa invece di ricopiare.
    Attraverso il confine col core non si puo' importare — e allora l'accordo
    non si afferma, si **misura**.

    Prima di questo test i tre ritagli divergevano su DUE assi:

    - lo SPAZIO: il core tagliava contro `[0, altezza - min]` invece di
      `[alto, alto + altezza - min]`, una banda traslata di quanto e' alta la
      barra (chiuso in `16f802b`);
    - il MINIMO: il renderer usava 40 per le icone, il core 80 per tutto —
      una fascia di 40 px in cui il renderer accettava e il core spostava.

    Il secondo asse nessuno l'aveva visto perche' `desk/icone.js` scriveva
    accanto al proprio 40: «stesso numero e stessa ragione del MIN_VISIBILE dei
    pannelli». Era falso, e un commento che afferma un'uguaglianza e' esattamente
    cio' che questo test sostituisce.
    """

    def test_le_due_soglie_sono_gli_stessi_numeri(self) -> None:
        js = _nel_modulo(
            "console.log(JSON.stringify([G.MIN_VISIBILE, G.MIN_VISIBILE_ICONA]));")
        assert js == [MINIMO_PANNELLO, MINIMO_ICONA], (
            f"il renderer usa {js}, il core [{MINIMO_PANNELLO}, {MINIMO_ICONA}]"
        )

    def test_un_ICONA_finisce_dove_dice_il_renderer(self) -> None:
        casi = [(a, x, y) for a in AREE for (x, y) in PUNTI]
        js = _nel_modulo(
            "const casi = " + json.dumps([[a, x, y] for a, x, y in casi]) + ";\n"
            "console.log(JSON.stringify(casi.map(([a, x, y]) =>"
            " G.dentroPunto(x, y, a, G.MIN_VISIBILE_ICONA))));"
        )
        for (a, x, y), atteso in zip(casi, js):
            d = adatta(
                Layout(icone=[IconaLibera(tipo="file", nome="x.txt", x=x, y=y)]),
                a["larghezza"], a["altezza"],
                sinistra=a["sinistra"], alto=a["alto"],
            ).icone[0]
            assert (d.x, d.y) == (atteso["x"], atteso["y"]), (
                f"area {a}, punto ({x}, {y}): core ({d.x}, {d.y}), "
                f"renderer ({atteso['x']}, {atteso['y']})"
            )

    def test_un_PANNELLO_finisce_dove_dice_il_renderer(self) -> None:
        """Stessa tabella, l'altra soglia — e passando da `dentroArea`, cioe'
        dalla funzione che i pannelli usano davvero."""
        casi = [(a, x, y) for a in AREE for (x, y) in PUNTI]
        js = _nel_modulo(
            "const casi = " + json.dumps([[a, x, y] for a, x, y in casi]) + ";\n"
            "console.log(JSON.stringify(casi.map(([a, x, y]) =>"
            " G.dentroArea({ x, y, larghezza: 400, altezza: 300 }, a))));"
        )
        for (a, x, y), atteso in zip(casi, js):
            p = GeometriaPannello(id="telemetria", x=x, y=y,
                                  larghezza=400, altezza=300, z=1, massimizzato=False)
            d = adatta(Layout(pannelli=[p]), a["larghezza"], a["altezza"],
                       sinistra=a["sinistra"], alto=a["alto"]).pannelli[0]
            assert (d.x, d.y) == (atteso["x"], atteso["y"]), (
                f"area {a}, punto ({x}, {y}): core ({d.x}, {d.y}), "
                f"renderer ({atteso['x']}, {atteso['y']})"
            )

    def test_icone_js_NON_ha_piu_una_copia_della_regola(self) -> None:
        """La meta' che un confronto di risultati non prova: che la seconda
        implementazione sia sparita davvero, invece di essere rimasta uguale
        per ora. Un controllo sul SORGENTE, come `TestR82`.
        """
        sorgente = (RADICE / "ui" / "src" / "desk" / "icone.js").read_text(encoding="utf-8")
        assert "dentroPunto" in sorgente, "icone.js non usa il proprietario della regola"
        assert "const MIN_VISIBILE" not in sorgente, (
            "icone.js ha di nuovo una soglia sua: e' da li' che le due sono "
            "divergite, con accanto un commento che diceva che erano uguali"
        )
