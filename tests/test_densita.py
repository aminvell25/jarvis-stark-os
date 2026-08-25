"""I sei criteri di densità sono guardati da qualcuno — e la misura è FRESCA.

## Perché questo file esiste

Fino al 25 agosto 2026 entropia, deviazione standard, `L>60`, caldo, barra e
dock erano misurati **a mano** e guardati da **nessuno**:
`npm run verifica:scrivania` controlla dock, debordo, ombre e fuoco, non la
densità. Il margine dell'entropia è **0,04** su una soglia di 2,40 — il quarto
atterraggio nei centesimi di questo progetto, dopo il marchio (3,01/3,00), il
piano (2,428/2,40) e `--txt-primary` (4,536/4,50).

Con quel margine, **la prima superficie che qualcuno tocca lo rompe in
silenzio**. Gli altri cinque criteri hanno spazio — dev +2,8, `L>60` +3,0 — ed
è proprio l'entropia a essere sul filo.

## Perché non apre niente

Come `test_nucleo.py` per il marchio, `test_catalogo.py` per lo scorrimento e
`test_orologio.py` per l'ora: la cattura resta manuale — `npm run
verifica:densita` apre Electron, e uno scatto dentro la suite rimette il
conflitto sul socket del core vivo. Qui si verifica che l'esito sia **fresco**:
un'impronta dei sorgenti viaggia dentro il file, e se non combacia qualcuno ha
toccato una superficie senza rimisurare.

**Un esito vecchio è peggio di nessun esito, perché sembra una verifica.**

## E la provenienza

L'esito deve venire dalla **fixture**, mai da una scrivania viva. §11.9
condizione 4: «una misura di fixture non si confronta MAI con una misura viva».
Una soglia giudicata su dati vivi è giudicata sul rumore — è la ragione per cui
la fixture esiste.

⚠️ `shots/scrivania/` non è più prodotta da nessuno: era vecchia di cinque ore e
dava ancora 2,21 — il numero di prima di tre turni di lavoro — e chi lanciava il
comando vecchio leggeva quello. `npm run scrivania` scrive adesso in
`shots/scrivania-viva/`, che dice da sé che cos'è, e ogni riga di `densita.mjs`
porta `VIVA` oppure `fixture:<impronta>`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ESITO = RADICE / "docs" / "acceptance" / "DENSITA.json"

#: I sei criteri, col nome che l'esito usa. Il settimo — il dock — è in
#: rapporto e non boccia: `scripts/densita.mjs` lo dichiara, e questo test non
#: gli dà un verdetto che quel file non gli dà.
CRITERI = ("entropia", "devStd", "riempito", "caldo", "barra")


def _esito() -> dict:
    assert ESITO.exists(), (
        "manca docs/acceptance/DENSITA.json.\n"
        "Si produce con: npm run verifica:densita\n"
        "(apre Electron in modo fixture: non serve il core acceso)"
    )
    return json.loads(ESITO.read_text(encoding="utf-8"))


class TestLaDensitaEGuardata:
    def test_l_esito_esiste(self) -> None:
        _esito()

    def test_la_misura_descrive_i_sorgenti_di_ADESSO(self) -> None:
        """La metà che conta. Senza, questo file direbbe che la scrivania era
        densa *un giorno*, e il margine di 0,04 sull'entropia sparirebbe alla
        prima superficie toccata senza che nessuno se ne accorga.
        """
        d = _esito()
        fonti = sorted(
            p for cartella in ("ui/src", "ui")
            for p in (RADICE / cartella).rglob("*")
            if p.is_file()
            and p.suffix in {".js", ".css", ".html"}
            and "vendor" not in p.parts
            and (cartella != "ui" or p.parent == RADICE / "ui")
        )
        h = hashlib.sha256()
        for f in fonti:
            h.update(f.read_bytes())
        assert h.hexdigest()[:16] == d["impronta"], (
            "una superficie è cambiata dopo l'ultima misura di densità.\n"
            f"impronta nell'esito {d['impronta']}, sorgenti adesso "
            f"{h.hexdigest()[:16]} ({len(fonti)} file).\n"
            "Rimisura: npm run verifica:densita"
        )

    def test_la_misura_viene_dalla_FIXTURE(self) -> None:
        """§11.9 condizione 4. Una soglia giudicata su dati vivi è giudicata
        sul rumore: due sessioni davano `L>60` 26,1 % e 25,3 %, ed è per questo
        che la fixture esiste."""
        d = _esito()
        assert str(d["provenienza"]).startswith("fixture:"), (
            f"l'esito viene da «{d['provenienza']}», non dalla registrazione. "
            "Il comando è `npm run verifica:densita`, non `npm run scrivania`"
        )

    def test_tutti_e_cinque_i_criteri(self) -> None:
        """Uno per uno, col nome: quale è caduto si legge dal fallimento."""
        d = _esito()
        assert d["soddisfatto"], "densità sotto soglia:\n  " + "\n  ".join(d["falliti"])

    def test_nessun_margine_e_negativo(self) -> None:
        """`soddisfatto` da solo si fida di chi l'ha scritto. I margini si
        ricalcolano qui dalle misure e dalle soglie che l'esito porta con sé."""
        d = _esito()
        for nome in CRITERI:
            if nome == "caldo":
                assert d["soglie"]["caldoMin"] <= d["misure"]["caldo"] <= d["soglie"]["caldoMax"], (
                    f"caldo {d['misure']['caldo']} fuori da "
                    f"[{d['soglie']['caldoMin']}, {d['soglie']['caldoMax']}]"
                )
                continue
            atteso = {"entropia": "entropia", "devStd": "devStd",
                      "riempito": "riempito", "barra": "barra"}[nome]
            assert d["misure"][nome] >= d["soglie"][atteso], (
                f"{nome} {d['misure'][nome]} sotto {d['soglie'][atteso]}"
            )

    def test_il_margine_dell_entropia_e_DICHIARATO(self) -> None:
        """Non è un divieto: è una cosa che chi legge deve poter sapere.

        0,04 su 2,40 è lo 0,2 % del valore. Gli altri cinque criteri passano con
        spazio; questo no. Il giorno in cui diventasse negativo il test sopra
        cade — ma il giorno in cui si assottiglia ancora, nessuno se ne
        accorgerebbe se il numero non fosse scritto.
        """
        d = _esito()
        assert "entropia" in d["margini"], "l'esito non dichiara i margini"
        assert d["margini"]["entropia"] >= 0, (
            f"margine dell'entropia {d['margini']['entropia']}: sotto soglia"
        )
