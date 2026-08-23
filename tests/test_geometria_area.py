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
