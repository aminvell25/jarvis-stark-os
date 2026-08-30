"""L'LLM propone, il compositore dispone — ADR-013.

`core/layout.py` registrava cio' che l'utente aveva fatto con le mani. Non
esisteva niente che potesse dire «per questo compito servono questi pannelli».

## Il rischio, dichiarato per primo

Un LLM che emette geometria e' un LLM che disegna. Un LLM che emette geometria
**valida** e' un LLM che disegna e non se ne accorge. La riga che separa questo
progetto da una demo e' che l'LLM non nomina mai un pixel — e in questa fetta
non nomina nemmeno un pannello: gli intent sono **scritti a mano** in
`SUPERFICI`, e nessun modello li tocca.

## Le cinque regole, e quattro sono divieti

    1. la composizione manuale VINCE SEMPRE
    2. i nomi vengono da un'allowlist
    3. l'intent non contiene geometria
    4. un intent rifiutato NON MUOVE UN PIXEL, e lo dichiara
    5. ogni composizione registra da dove viene

⚠️ **Due correzioni ad ADR-013, misurate contro il codice.**

**① Il «registry dei pannelli» non esiste nel core.** L'elenco sta in
`ui/src/desk/moduli.js`, e `core/settings.py:276` dichiara per iscritto la
decisione OPPOSTA: «il core non conosce `moduli.js` e non deve: e' interfaccia.
Un id sconosciuto lo IGNORA il renderer». L'allowlist e' quindi **i pannelli
dichiarati nelle scene di `settings.toml`** — una lista chiusa che il core
possiede davvero, senza duplicare niente.

**② `componi` non restituisce un `Layout`, ma una `Composizione`.** La regola 4
vuole che un rifiuto porti con se' il motivo, e un `Layout` da solo non puo'.
Restituirne uno vuoto sarebbe peggio: chi chiama non distinguerebbe «composto a
vuoto» da «rifiutato».
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.layout import (
    SUPERFICI,
    Area,
    Composizione,
    GeometriaPannello,
    Layout,
    LayoutIntent,
    LayoutStore,
    componi,
    intento,
)
from core.llm.grammar import INTENTI_CORE, parse

#: Un'allowlist di prova: i pannelli che le scene di `config/settings.toml`
#: dichiarano davvero. Non inventata — letta.
AMMESSI = frozenset({"news", "telemetria", "agenti", "globo", "periodica",
                     "archivio", "sorgente", "anelli", "console"})
AREA = Area(sinistra=0, alto=48, larghezza=1920, altezza=900)


def _traccia() -> str:
    return "abc123def456"


# ── ① il tipo: la regola 3 la impone lo SCHEMA, non la disciplina ────────────


class TestLIntentNonPuoPortareGeometria:
    @pytest.mark.parametrize("campo", ["x", "y", "larghezza", "altezza", "z"])
    def test_nessun_campo_di_geometria_entra(self, campo: str) -> None:
        """⚠️ **Non e' una convenzione da ricordare: e' il tipo che non
        l'accetta.** `_Stretto` ha `extra="forbid"`, quindi il giorno in cui un
        modello emettesse un pixel lo schema lo rifiuta **prima di guardarlo**.
        """
        with pytest.raises(ValidationError):
            LayoutIntent(superficie="x", traccia_id=_traccia(),
                         pannelli_richiesti=["news"], **{campo: 10})

    def test_i_campi_sono_esattamente_cinque(self) -> None:
        assert set(LayoutIntent.model_fields) == {
            "superficie", "traccia_id", "pannelli_richiesti",
            "pannelli_secondari", "priorita"}

    def test_la_traccia_e_obbligatoria(self) -> None:
        """ADR-011 → ADR-013: una composizione senza provenienza e' una
        composizione che nessuno puo' spiegare."""
        with pytest.raises(ValidationError):
            LayoutIntent(superficie="x", pannelli_richiesti=["news"])

    def test_le_superfici_sono_scritte_a_MANO(self) -> None:
        """Nella prima fetta gli intent sono dichiarati in codice. Il
        compilatore va provato contro un input che si controlla, prima di
        provarlo contro uno che si negozia."""
        assert set(SUPERFICI) == {"diagnostica", "briefing", "officina"}
        for nome in SUPERFICI:
            i = intento(nome, _traccia())
            assert i.superficie == nome and i.traccia_id == _traccia()

    def test_una_superficie_inventata_non_si_costruisce(self) -> None:
        with pytest.raises(KeyError):
            intento("inventata", _traccia())


# ── ② la composizione ────────────────────────────────────────────────────────


class TestUnIntentValidoCompone:
    """Criterio 1."""

    def test_i_pannelli_chiesti_ci_sono_tutti(self) -> None:
        c = componi(intento("diagnostica", _traccia()), AREA, Layout(), AMMESSI)
        assert not c.rifiutata
        assert {p.id for p in c.layout.pannelli} == {"telemetria", "agenti",
                                                     "anelli"}

    def test_stanno_DENTRO_l_area(self) -> None:
        c = componi(intento("officina", _traccia()), AREA, Layout(), AMMESSI)
        for p in c.layout.pannelli:
            assert p.x >= AREA.sinistra and p.y >= AREA.alto
            assert p.x + p.larghezza <= AREA.sinistra + AREA.larghezza + 1
            assert p.y + p.altezza <= AREA.alto + AREA.altezza + 1

    def test_non_si_sovrappongono(self) -> None:
        """La griglia di occupazione serve a questo: due pannelli composti
        insieme non devono coprirsi, o la composizione automatica sarebbe
        peggiore di quella manuale."""
        c = componi(intento("diagnostica", _traccia()), AREA, Layout(), AMMESSI)
        p = c.layout.pannelli
        for i in range(len(p)):
            for j in range(i + 1, len(p)):
                a, b = p[i], p[j]
                separati = (a.x + a.larghezza <= b.x or b.x + b.larghezza <= a.x
                            or a.y + a.altezza <= b.y or b.y + b.altezza <= a.y)
                assert separati, f"{a.id} copre {b.id}"

    def test_e_DETERMINISTICO(self) -> None:
        """Nessun LLM, nessun caso: due giri con lo stesso input danno lo stesso
        pixel. E' cio' che rende il compilatore provabile."""
        uno = componi(intento("briefing", _traccia()), AREA, Layout(), AMMESSI)
        due = componi(intento("briefing", _traccia()), AREA, Layout(), AMMESSI)
        assert uno.layout.model_dump() == due.layout.model_dump()


class TestLaComposizioneManualeVinceSempre:
    """Regola 1, e criterio 3."""

    def test_un_pannello_mosso_a_mano_resta_dov_era(self) -> None:
        manuale = Layout(pannelli=[GeometriaPannello(
            id="diario", x=100, y=100, larghezza=300, altezza=200, z=9)])
        c = componi(intento("diagnostica", _traccia()), AREA, manuale, AMMESSI)
        d = next(p for p in c.layout.pannelli if p.id == "diario")
        assert (d.x, d.y, d.larghezza, d.altezza, d.z) == (100, 100, 300, 200, 9)

    def test_se_non_c_e_spazio_NON_compone(self) -> None:
        """«`componi` lavora sullo spazio rimasto, e se non ne resta abbastanza
        **non compone**: lo dichiara.»"""
        pieno = Layout(pannelli=[GeometriaPannello(
            id="diario", x=0, y=48, larghezza=1920, altezza=900, z=1)])
        c = componi(intento("diagnostica", _traccia()), AREA, pieno, AMMESSI)
        assert c.rifiutata and "spazio" in c.motivo

    def test_e_TUTTO_O_NIENTE(self) -> None:
        """Comporre una meta' lascerebbe la scrivania in uno stato che nessuno
        ha chiesto: ne' quello di prima ne' quello proposto."""
        quasi = Layout(pannelli=[GeometriaPannello(
            id="diario", x=0, y=48, larghezza=1500, altezza=900, z=1)])
        c = componi(intento("diagnostica", _traccia()), AREA, quasi, AMMESSI)
        assert c.rifiutata, "con questo spazio ci stava solo il primo"


class TestUnNomeSconosciutoEUnIntentRifiutato:
    """Regola 2 e criterio 2."""

    def test_non_muove_un_pixel(self) -> None:
        prima = Layout(pannelli=[GeometriaPannello(
            id="diario", x=10, y=60, larghezza=200, altezza=150)])
        c = componi(LayoutIntent(superficie="finta", traccia_id=_traccia(),
                                 pannelli_richiesti=["inesistente"]),
                    AREA, prima, AMMESSI)
        assert c.rifiutata and c.layout is None, (
            "un nome sconosciuto non e' un pannello vuoto: e' un intent "
            "rifiutato, e il layout precedente resta esattamente dov'era"
        )

    def test_e_produce_un_ADVISORY_dichiarato(self) -> None:
        c = componi(LayoutIntent(superficie="finta", traccia_id=_traccia(),
                                 pannelli_richiesti=["inesistente"]),
                    AREA, Layout(), AMMESSI)
        a = c.advisory()
        assert a["topic"] == "agent.advisory"
        assert a["reason"] == "composizione_rifiutata"
        assert a["traccia"] == _traccia() and a["superficie"] == "finta"
        assert "inesistente" in a["dettaglio"]

    def test_anche_un_SECONDARIO_sconosciuto_rifiuta_tutto(self) -> None:
        c = componi(LayoutIntent(superficie="finta", traccia_id=_traccia(),
                                 pannelli_richiesti=["news"],
                                 pannelli_secondari=["inesistente"]),
                    AREA, Layout(), AMMESSI)
        assert c.rifiutata

    def test_lo_stesso_pannello_due_volte_si_rifiuta(self) -> None:
        c = componi(LayoutIntent(superficie="finta", traccia_id=_traccia(),
                                 pannelli_richiesti=["news"],
                                 pannelli_secondari=["news"]),
                    AREA, Layout(), AMMESSI)
        assert c.rifiutata and "due volte" in c.motivo


class TestLaProvenienzaSiRegistra:
    """Regola 5 e criterio 4."""

    def test_il_layout_composto_porta_superficie_e_traccia(self) -> None:
        c = componi(intento("briefing", _traccia()), AREA, Layout(), AMMESSI)
        assert c.layout.superficie == "briefing"
        assert c.layout.traccia_id == _traccia()

    def test_un_layout_MANUALE_non_li_porta(self) -> None:
        """`None` e' il caso normale: l'ha disposto l'utente con le mani."""
        assert Layout().superficie is None and Layout().traccia_id is None

    def test_i_campi_sono_ADDITIVI(self, tmp_path: Path) -> None:
        """Un `layout.json` scritto prima di questa fetta non li ha, e deve
        continuare a caricarsi — stessa regola della traccia in ADR-011."""
        p = tmp_path / "layout.json"
        p.write_text(json.dumps({
            "versione": 1,
            "pannelli": [{"id": "diario", "x": 1, "y": 2,
                          "larghezza": 300, "altezza": 200, "z": 0,
                          "massimizzato": False}],
            "icone": [], "cartelle": [], "scena": None,
        }), encoding="utf-8")
        l = LayoutStore(p).carica()
        assert l.pannelli[0].id == "diario"
        assert l.superficie is None and l.traccia_id is None


class TestSiTornaIndietro:
    """Criterio 5."""

    def test_la_composizione_precedente_si_rimette(self, tmp_path: Path) -> None:
        store = LayoutStore(tmp_path / "layout.json")
        manuale = Layout(pannelli=[GeometriaPannello(
            id="diario", x=100, y=100, larghezza=300, altezza=200, z=9)],
            area_larghezza=1920, area_altezza=900, area_alto=48)
        store.salva(manuale)

        c = componi(intento("diagnostica", _traccia()), AREA,
                    store.carica(), AMMESSI)
        assert store.componi_e_salva(c)
        assert store.carica().superficie == "diagnostica"

        prima = store.ripristina()
        assert prima is not None
        assert store.carica().superficie is None
        assert [p.id for p in store.carica().pannelli] == ["diario"]

    def test_senza_una_precedente_non_si_torna(self, tmp_path: Path) -> None:
        assert LayoutStore(tmp_path / "layout.json").ripristina() is None

    def test_un_intent_rifiutato_non_si_SALVA(self, tmp_path: Path) -> None:
        """Regola 4, dal lato del disco: se non compone, non scrive."""
        store = LayoutStore(tmp_path / "layout.json")
        rifiutata = Composizione(layout=None, motivo="no", superficie="x",
                                 traccia_id=_traccia())
        assert store.componi_e_salva(rifiutata) is False
        assert not store.percorso.exists()


# ── ③ la strada dalla voce ───────────────────────────────────────────────────


class TestLaVoceCiArriva:
    def test_i_due_intenti_sono_nell_allowlist(self) -> None:
        assert {"componi_superficie", "ripristina_layout"} <= INTENTI_CORE

    @pytest.mark.parametrize("frase,atteso", [
        ("componi la superficie diagnostica", "diagnostica"),
        ("prepara superficie briefing", "briefing"),
        ("disponi la superficie officina", "officina"),
    ])
    def test_la_grammatica_le_riconosce(self, frase: str, atteso: str) -> None:
        i = parse(frase)
        assert i is not None and i.tool == "componi_superficie"
        assert i.args["nome"] == atteso

    def test_e_il_ritorno_indietro(self) -> None:
        i = parse("rimetti com'era")
        assert i is not None and i.tool == "ripristina_layout"

    def test_la_regola_e_ANCORATA_alla_parola_superficie(self) -> None:
        """⚠️ La forma corta — `componi (?P<s>\\w+)` — prenderebbe «prepara il
        caffe'» come una richiesta di comporre la superficie «caffe'»: un
        intento rifiutato, quindi un advisory, per una frase che non chiedeva
        niente. Un'ancora costa due sillabe e toglie l'intera classe di falsi
        positivi — ed e' la scelta che §7.6 ha gia' fatto per le scene."""
        for innocente in ("prepara il caffe", "componi il numero",
                          "disponi le tue cose"):
            i = parse(innocente)
            assert i is None or i.tool != "componi_superficie", innocente


# ── ④ il giro intero: dalla frase alla scrivania ─────────────────────────────


def _intercetta(engine) -> list[dict]:
    """Prende il posto del socket: si guarda COSA sarebbe partito."""
    inviati: list[dict] = []

    async def falso(msg: dict) -> None:
        inviati.append(msg)

    engine._ws.broadcast = falso        # type: ignore[method-assign]
    return inviati


@pytest.fixture
def motore(short_paths):
    from core.engine import Engine

    e = Engine(short_paths)
    # La scrivania ha riferito quanto e' grande il pavimento: senza, comporre
    # vorrebbe dire inventare una geometria, e il motore si rifiuta.
    e._layout.salva(Layout(area_larghezza=1920, area_altezza=900,
                           area_sinistra=0, area_alto=48))
    return e


class TestIlGiroIntero:
    """Criterio 1: «la scrivania ci arriva **senza che il renderer abbia
    scritto niente**»."""

    async def test_una_frase_compone_e_la_scrivania_riceve(self, motore) -> None:
        from core.traccia import Origine, Traccia

        inviati = _intercetta(motore)
        t = Traccia.nuova(Origine.VOCE)
        esito = await motore.esegui_t0(parse("componi la superficie diagnostica"), t)

        assert esito["ok"], esito
        layout = [m for m in inviati if m.get("topic") == "ui.layout"]
        assert layout, "la scrivania non ha ricevuto niente"
        assert layout[-1]["superficie"] == "diagnostica"
        assert layout[-1]["traccia_id"] == t.id, (
            "il Layout salvato porta la traccia del turno che l'ha causata "
            "(criterio 4)"
        )
        assert {p["id"] for p in layout[-1]["pannelli"]} == {
            "telemetria", "agenti", "anelli"}

    async def test_e_il_diario_ha_la_riga_con_la_STESSA_traccia(
        self, motore
    ) -> None:
        """⚠️ **Una riga sola.** `esegui_t0` la scrive gia', con questa traccia e
        con `args={"nome": ...}`: aggiungerne una seconda in
        `_componi_superficie` farebbe cio' che il commento sopra `_ronda_di`
        vieta — due record dello stesso fatto, che divergono al primo che li
        tocca."""
        import asyncio

        from core.traccia import Origine, Traccia

        _intercetta(motore)
        t = Traccia.nuova(Origine.VOCE)
        await motore.esegui_t0(parse("componi la superficie briefing"), t)
        await asyncio.sleep(0)

        righe = [r for r in motore._diario.leggi(flusso="azione")
                 if r.get("intento") == "componi_superficie"]
        assert len(righe) == 1, "una sola riga, non due"
        assert righe[0]["traccia"] == t.id
        assert righe[0]["args"] == {"nome": "briefing"}

    async def test_una_superficie_ignota_non_muove_un_pixel(self, motore) -> None:
        from core.traccia import Origine, Traccia

        inviati = _intercetta(motore)
        prima = motore._layout.carica().model_dump()
        esito = await motore.esegui_t0(
            parse("componi la superficie inventata"), Traccia.nuova(Origine.VOCE))

        assert not esito["ok"]
        assert not [m for m in inviati if m.get("topic") == "ui.layout"]
        assert motore._layout.carica().model_dump() == prima

    async def test_senza_area_NON_si_compone(self, short_paths) -> None:
        """Comporre senza sapere quanto e' grande lo schermo vorrebbe dire
        inventare una geometria — cioe' cio' che ADR-013 esiste per impedire,
        commesso dal core invece che da un modello."""
        from core.engine import Engine
        from core.traccia import Origine, Traccia

        e = Engine(short_paths)
        _intercetta(e)
        esito = await e.esegui_t0(parse("componi la superficie diagnostica"),
                                  Traccia.nuova(Origine.VOCE))
        assert not esito["ok"] and "area" in esito["error"]

    async def test_si_torna_indietro_dalla_voce(self, motore) -> None:
        from core.traccia import Origine, Traccia

        inviati = _intercetta(motore)
        t = Traccia.nuova(Origine.VOCE)
        await motore.esegui_t0(parse("componi la superficie officina"), t)
        assert motore._layout.carica().superficie == "officina"

        esito = await motore.esegui_t0(parse("rimetti com'era"), t)
        assert esito["ok"], esito
        assert motore._layout.carica().superficie is None
        assert inviati[-1]["topic"] == "ui.layout"

    async def test_l_allowlist_sono_le_SCENE_dichiarate(self, motore) -> None:
        """⚠️ La correzione ① ad ADR-013: non `moduli.js`, ma le scene che
        l'utente ha scritto nel proprio `settings.toml`."""
        ammessi = motore._pannelli_ammessi()
        dichiarati = {p.id for s in motore.settings.ui.scene for p in s.pannelli}
        assert ammessi == dichiarati and ammessi


class TestLeSuperficiNonNasconoMORTE:
    """⚠️ **Trovato dal giro intero, non da una rilettura.**

    `SUPERFICI` sta nel codice; l'allowlist viene dal `settings.toml`. Niente
    impediva a una superficie scritta a mano di nominare un pannello che
    nessuna scena dichiara — e `diagnostica` lo faceva, con `console`: nasceva
    rifiutata, e nessuno se ne sarebbe accorto finche' qualcuno non l'avesse
    chiesta a voce.
    """

    def test_ogni_pannello_e_dichiarato_nel_config_SPEDITO(self) -> None:
        import tomllib

        RADICE = Path(__file__).resolve().parent.parent
        conf = tomllib.loads(
            (RADICE / "config" / "settings.toml").read_text(encoding="utf-8"))
        dichiarati = {p["id"] for s in conf.get("ui", {}).get("scene", [])
                      for p in s.get("pannelli", [])}
        assert dichiarati, "il config spedito non dichiara nessuna scena"
        for nome, s in SUPERFICI.items():
            chiesti = set(s["pannelli_richiesti"]) | set(s.get("pannelli_secondari", []))
            fuori = chiesti - dichiarati
            assert not fuori, (
                f"la superficie «{nome}» nomina {sorted(fuori)}, che nessuna "
                f"scena di config/settings.toml dichiara: nascerebbe rifiutata"
            )

    def test_e_infatti_si_compongono_tutte(self) -> None:
        import tomllib

        RADICE = Path(__file__).resolve().parent.parent
        conf = tomllib.loads(
            (RADICE / "config" / "settings.toml").read_text(encoding="utf-8"))
        ammessi = frozenset(p["id"] for s in conf["ui"]["scene"]
                            for p in s["pannelli"])
        for nome in SUPERFICI:
            c = componi(intento(nome, _traccia()), AREA, Layout(), ammessi)
            assert not c.rifiutata, f"«{nome}»: {c.motivo}"


class TestUnAllowlistVuotaLoDICE:
    """Il `settings.toml` di questa macchina non ha nessuna scena."""

    def test_il_motivo_manda_dalla_parte_GIUSTA(self) -> None:
        c = componi(intento("briefing", _traccia()), AREA, Layout(), frozenset())
        assert c.rifiutata
        assert "nessuna scena" in c.motivo and "[[ui.scene]]" in c.motivo, (
            "«pannelli sconosciuti» manderebbe a cercare il difetto nei nomi "
            "invece che nella configurazione"
        )
