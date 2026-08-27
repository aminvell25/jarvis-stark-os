"""«Nessuna card è mai passata dal gate in esercizio», e non poteva.

`core/news/gate.py` legge `Contesto.pannello_a_schermo_intero` prima di
decidere, e tratta l'ignoto come **divieto** — fail-closed, ed è corretto. Ma
quel campo non aveva un produttore: `_contesto_news` non lo dichiarava affatto,
quindi valeva `None` a ogni giro.

    §15, regola 3: «mai con un pannello a schermo intero»
    stato reale:   None per sempre
    conseguenza:   il gate non ha MAI potuto lasciar passare niente

`docs/acceptance/FASE-08.md` lo porta a verbale come non verificato, e
`LE-NEWS-GIRANO.md` dichiara «nessuna card è mai passata dal gate in esercizio».
Non era il gate a essere severo: era un campo senza sorgente.

## E il produttore non è stato scritto: c'era già

`GeometriaPannello.massimizzato` esiste da §26.2. La scrivania lo riempie da
WinBox (`ui/src/desk/cornice.js`, `massimizzato: !!b.max`), il messaggio
`ui.layout` lo porta, pydantic lo valida, `LayoutStore` lo salva su disco.

Mancava **il lettore**. È la stessa famiglia di difetto degli ultimi trenta
commit, applicata a §15.

⚠️ E non serve una soglia. Non si stima quanta area copra un pannello: lo dice
la scrivania. Una soglia sarebbe stata un numero scelto per rispondere a una
domanda a cui qualcuno rispondeva già.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from core.layout import GeometriaPannello, Layout, LayoutStore


def _store() -> LayoutStore:
    return LayoutStore(Path(tempfile.mkdtemp()) / "layout.json")


def _pannello(**kw) -> GeometriaPannello:
    base = {"id": "globo", "x": 0, "y": 0, "larghezza": 10, "altezza": 10}
    return GeometriaPannello(**{**base, **kw})


class TestLoStatoVieneDallaSCRIVANIA:
    def test_finche_nessuno_ha_riferito_e_IGNOTO(self) -> None:
        """`None` e non `False`: «non lo so» non è «non c'è», e sull'ignoto §15
        tace. Un `False` di comodo farebbe parlare JARVIS sopra un pannello a
        schermo intero che nessuno gli ha ancora descritto."""
        assert _store().a_schermo_intero() is None

    def test_nessun_pannello_massimizzato(self) -> None:
        s = _store()
        s.salva(Layout(pannelli=[_pannello(), _pannello(id="news")]))
        assert s.a_schermo_intero() is False

    def test_uno_solo_basta(self) -> None:
        s = _store()
        s.salva(Layout(pannelli=[_pannello(), _pannello(id="news", massimizzato=True)]))
        assert s.a_schermo_intero() is True

    def test_una_scrivania_VUOTA_non_e_ignota(self) -> None:
        """Nessun pannello aperto è un'informazione, non un'assenza di
        informazione: lì si può parlare."""
        s = _store()
        s.salva(Layout(pannelli=[]))
        assert s.a_schermo_intero() is False


class TestLaSTROZZATURAnonRitardaIlSAPERE:
    """⚠️ `MIN_INTERVALLO_S` esiste per non martellare il disco, e non ha niente
    a che vedere con il sapere.

    Sotto la soglia il layout resta in attesa di essere SCRITTO, ma è già lo
    stato vero della scrivania. Leggendo dopo la strozzatura, `a_schermo_intero`
    sarebbe indietro di un trascinamento — cioè sbagliata proprio mentre
    l'utente sta lavorando.
    """

    def test_un_salva_STROZZATO_aggiorna_lo_stato_lo_stesso(self) -> None:
        s = _store()
        assert s.salva(Layout(pannelli=[_pannello()]), ora=100.0) is True
        # Subito dopo: sotto `MIN_INTERVALLO_S`, quindi non tocca il disco.
        scritto = s.salva(
            Layout(pannelli=[_pannello(massimizzato=True)]), ora=100.0)
        assert scritto is False, "questo test non prova più la strozzatura"
        assert s.a_schermo_intero() is True, (
            "lo stato è indietro di un salvataggio: il gate deciderebbe sul "
            "pannello di prima"
        )


class TestIlMotoreLoRICEVE:
    def test_il_contesto_lo_DICHIARA(self) -> None:
        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        corpo = s.split("def _contesto_news", 1)[1].split("\n    def ", 1)[0]
        codice = "\n".join(r.split("#", 1)[0] for r in corpo.splitlines())
        codice = codice.split('"""', 2)[-1]
        assert "pannello_a_schermo_intero=self._layout.a_schermo_intero()" in codice

    def test_e_NON_e_un_valore_di_comodo(self) -> None:
        """Un `False` fisso farebbe passare le card sempre, ed è esattamente il
        modo in cui una regola di cortesia smette di esistere senza che nessuno
        se ne accorga."""
        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        corpo = s.split("def _contesto_news", 1)[1].split("\n    def ", 1)[0]
        assert "pannello_a_schermo_intero=False" not in corpo
        assert "pannello_a_schermo_intero=None" not in corpo
