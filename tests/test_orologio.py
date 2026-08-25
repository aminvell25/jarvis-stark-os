"""Che ora e', in un posto solo — e nessun pannello se lo chiede da se'.

## Perche' questo file esiste

Il core trasmette `ts` dentro `telemetry` **2,5 volte al secondo** e dentro
`agent.mesh` una volta al secondo. Nessuno lo leggeva: nove punti del renderer
chiamavano `new Date()` o `Date.now()` per sapere l'ora, cioe' chiedevano
all'orologio della macchina che DISEGNA mentre il dato accanto veniva da quella
che MISURA.

E' lo stesso difetto gia' corretto per il globo in `cb4a52b` — «le zone
venivano dal core e l'istante dal renderer, due orologi per un'immagine sola» —
lasciato in piedi in cinque pannelli e dichiarato aperto in cinque documenti di
accettazione di fila:

    Cinque orologi vivi latenti: news.js, meteo.js, console.js, lettura.js,
    calendario.js. Zero pixel oggi perche' sono fuori scena — vanno elencati
    per nome, non riscoperti il giorno in cui qualcuno li compone.

Quel giorno e' arrivato senza che nessuno componesse niente: bastava che una
scena futura aprisse uno di quei pannelli e la fixture di §11.9 avrebbe smesso
di essere riproducibile, **senza che nessun test se ne accorgesse**.

## Le due meta'

Il comportamento lo prova `TestLOrologio`, eseguendo il modulo vero con
`node --input-type=module` — lo stesso ponte di `tests/test_geometria_area.py`.

Che nessuno se la chieda da se' lo prova `TestNessunPannelloHaUnOrologioSuO`,
che e' un controllo sul SORGENTE: un confronto di comportamento non distingue
«la copia non c'e'» da «la copia c'e' e per ora dice lo stesso».
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
MODULO = RADICE / "ui" / "src" / "desk" / "orologio.js"
PANNELLI = sorted((RADICE / "ui" / "src" / "panels").glob("*.js"))

#: ⚠️ Chi misura QUANTO TEMPO PASSA continua a usare `Date.now()`, ed e' la
#: domanda giusta per quella risposta: l'orologio del core arriva a 2,5 Hz, cioe'
#: puo' essere vecchio di 400 ms, e per una durata non va bene.
#: Questi tre non sono deroghe: sono l'altro mestiere.
DUREVOLI = {
    "ui/src/desk/barra.js",       # uptime che avanza fra due snapshot
    "ui/src/desk/layout.js",      # il freno delle scritture
    "ui/src/desk/orologio.js",    # il ripiego, dichiarato, di chi possiede l'ora
}


def _nel_modulo(corpo: str) -> object:
    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    r = subprocess.run(
        ["node", "--input-type=module", "-e",
         f'import * as O from "{MODULO}";\n{corpo}'],
        capture_output=True, text=True, timeout=60, cwd=RADICE,
    )
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


class TestLOrologio:
    def test_senza_core_ripiega_e_LO_DICE(self) -> None:
        """Il ripiego non e' vietato: e' vietato che sia silenzioso.
        §11.7 regola 5 — la provenienza di una misura fa parte della misura."""
        assert _nel_modulo("console.log(JSON.stringify(O.fonte()));") == "locale"

    def test_col_core_l_ora_e_quella_del_core(self) -> None:
        got = _nel_modulo(
            "O.alimenta(1787614867.95);"
            "console.log(JSON.stringify([O.adesso(), O.fonte()]));")
        assert got == [1787614867950, "core"]

    def test_NON_torna_mai_indietro(self) -> None:
        """I messaggi possono arrivare fuori ordine, e un orologio che
        indietreggia farebbe apparire «3 min fa» dopo «adesso»."""
        got = _nel_modulo(
            "O.alimenta(2000); O.alimenta(1000);"
            "console.log(JSON.stringify(O.adesso()));")
        assert got == 2_000_000

    def test_ignora_cio_che_non_e_un_istante(self) -> None:
        """`alimenta` la riceve da `bus.suOgni`, cioe' da OGNI messaggio: la
        maggior parte non ha `ts`, e non deve succedere niente."""
        got = _nel_modulo(
            "for (const v of [undefined, null, 0, -1, NaN, Infinity, '123', {}])"
            "  O.alimenta(v);"
            "console.log(JSON.stringify(O.fonte()));")
        assert got == "locale"

    def test_l_ora_e_HH_MM_SS(self) -> None:
        got = _nel_modulo(
            "O.alimenta(1787614867.95); console.log(JSON.stringify(O.ora()));")
        assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", got), got


class TestNessunPannelloHaUnOrologioSuO:
    """La meta' che un confronto di comportamento non prova.

    Cinque documenti di accettazione hanno elencato questi orologi «per nome,
    non riscoperti dopo». Elencarli non li ha fermati. Questo li ferma.
    """

    @pytest.mark.parametrize("percorso", PANNELLI, ids=lambda p: p.name)
    def test_nessun_new_Date_o_Date_now(self, percorso: Path) -> None:
        codice = "\n".join(
            r for r in percorso.read_text(encoding="utf-8").splitlines()
            if not r.lstrip().startswith(("//", "*", "/*"))
        )
        colpevoli = re.findall(r"new Date\(\s*\)|Date\.now\(\s*\)", codice)
        assert not colpevoli, (
            f"{percorso.name} chiede l'ora alla macchina che disegna invece che "
            f"al core: {colpevoli}.\n"
            "Usa `adesso()`, `data()` o `ora()` da ui/src/desk/orologio.js. "
            "Se serve davvero una DURATA, il posto e' `desk/` e va aggiunto a "
            "DUREVOLI qui sopra, con la ragione."
        )

    def test_l_elenco_dei_durevoli_e_ancora_vero(self) -> None:
        """Un'eccezione che sopravvive al file che la giustificava smette di
        essere un'eccezione e diventa un buco."""
        for rel in DUREVOLI:
            f = RADICE / rel
            assert f.exists(), f"{rel} non esiste piu': va tolto da DUREVOLI"
            assert re.search(r"Date\.now\(\s*\)", f.read_text(encoding="utf-8")), (
                f"{rel} non usa piu' Date.now(): va tolto da DUREVOLI, o "
                "l'elenco comincia a proteggere qualcosa che non c'e'"
            )

    def test_l_orologio_e_alimentato(self) -> None:
        """Un proprietario che nessuno alimenta ripiega sempre, e allora tanto
        valeva non averlo.

        ⚠️ Sul CODICE, non sul testo. La prima stesura cercava «orologio.js» nel
        file intero e passava per via del commento che spiega la riga: un
        criterio soddisfatto da qualcosa che non e' il fenomeno, cioe' §11.7
        regola 4 commessa dentro il test che la applica.
        """
        app = "\n".join(
            r for r in (RADICE / "ui" / "src" / "app.js")
            .read_text(encoding="utf-8").splitlines()
            if not r.lstrip().startswith(("//", "*", "/*"))
        )
        assert re.search(r"import\s*\{[^}]*\balimenta\b[^}]*\}\s*from\s*"
                         r"[\"\']\./desk/orologio\.js[\"\']", app), (
            "app.js non importa `alimenta` da desk/orologio.js"
        )
        assert re.search(r"\balimenta\s*\(", app), (
            "app.js importa `alimenta` e non la chiama: `adesso()` ripiegherebbe "
            "sull'orologio locale per sempre"
        )
