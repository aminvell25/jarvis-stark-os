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
    """⚠️ Erano due test di GREP sul sorgente di `_contesto_news`, e sono
    caduti alla prima riscrittura che non toccava il comportamento. Un campo
    che segue la scrivania non si riconosce dalla stringa che lo scrive: si
    riconosce dal fatto che **cambia quando cambia la scrivania**."""

    def test_il_campo_SEGUE_la_scrivania(self, short_paths) -> None:
        from core.engine import Engine

        e = Engine(short_paths)
        e._layout._ultimo = Layout(pannelli=[_pannello(massimizzato=False)])
        assert e._contesto_news().contesto().pannello_a_schermo_intero is False
        e._layout._ultimo = Layout(pannelli=[_pannello(massimizzato=True)])
        assert e._contesto_news().contesto().pannello_a_schermo_intero is True, (
            "il campo non segue il layout: è un valore di comodo, ed è così "
            "che una regola di cortesia smette di esistere senza che nessuno "
            "se ne accorga"
        )

    def test_e_a_scrivania_MAI_VISTA_resta_ignoto(self, short_paths) -> None:
        """`None` e non `False`: «non lo so» non è «non c'è», e un `False`
        fisso farebbe passare le card sempre."""
        from core.engine import Engine
        from core.news.conoscibilita import NON_COMPOSTO

        e = Engine(short_paths)
        assert e._layout._ultimo is None
        lettura = e._contesto_news()
        assert lettura.contesto().pannello_a_schermo_intero is None
        assert lettura.conoscibilita()["pannello_a_schermo_intero"] == NON_COMPOSTO
