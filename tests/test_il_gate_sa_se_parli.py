"""§15, regola 2 — il gate sa se Lei sta parlando, e si vede da dove lo sa.

## Il difetto

`Contesto.sta_parlando` è un tri-stato apposta: `None` non è `False`, vuol
dire **non lo so**, e allora non si interrompe. Giusto — ma il campo non aveva
un produttore. `docs/acceptance/FASE-08.md` lo dichiarava fra i punti NON
verificati:

> oggi il core non sa se Lei sta parlando, quindi in esercizio **non
> interromperebbe mai**

Un tri-stato senza produttore non è una precauzione: è un divieto permanente
travestito da precauzione. Il motore proattivo taceva **per costruzione**, e
nessuna card era mai passata dal gate in esercizio.

## Che cosa fissano questi test

Non che il gate sia prudente — quello lo misura già `tests/test_news.py`. Qui
si misura **la giunzione**: che lo stato vero arrivi dalla pipeline vocale al
gate, per funzione, e che i tre modi di non saperlo restino tutti e tre un no.

    VoicePipeline.sta_parlando --(funzione)--> MotoreNews --> Contesto --> Gate

⚠️ Ciò che rende questi test capaci di **bocciare** e non solo di descrivere:
il caso `False` deve far uscire una card davvero. Un test che verificasse solo
i quattro casi che tacciono passerebbe anche cancellando l'intera giunzione —
è esattamente lo stato da cui si parte.
"""

from __future__ import annotations

import asyncio

import pytest

from core.llm.untrusted import Untrusted
from core.news.collectors.base import Esito, Item, rilevanza_per_parole
from core.news.feeds import Watcher
from core.news.gate import Contesto, Gate
from core.news.motore import MotoreNews

TITOLO = "Il clima cambia più in fretta del previsto"


class _Impostazioni:
    max_interruptions_per_hour = 3
    topic_ttl_minutes = 30


class _CollettoreFinto:
    """Una sorgente che risponde sempre, con un URL nuovo a ogni giro.

    L'URL cambia perché `Item.id` ne deriva: due giri sullo stesso URL sono
    la stessa notizia, e il gate risponderebbe «già proposto» — un motivo di
    rifiuto giusto che però nasconderebbe quello che qui si vuole misurare.
    """

    name = "finto"

    def __init__(self) -> None:
        self.giri = 0

    def disponibile(self) -> tuple[bool, str]:
        return True, ""

    async def poll(self, topics: list[str]) -> Esito:
        self.giri += 1
        return Esito(collector=self.name, item=[
            Item(fonte="finta",
                 url=f"https://esempio.invalido/{self.giri}",
                 testo=Untrusted.da("news:finta", TITOLO)),
        ])

    def relevance(self, item: Item, topics: list[str]) -> float:
        return rilevanza_per_parole(item, topics)


async def _chiedi_clima(prompt: str) -> str:
    """L'estrattore finto. Deterministico: questi test non misurano haiku.

    «clima» è nella battuta detta più sotto, quindi passa l'allowlist di
    `EstrattoreLLM._dalla_risposta`, che ammette solo parole pronunciate.
    """
    return "clima"


def _tutto_il_resto_e_noto() -> Contesto:
    """Il contesto che la radice di composizione dichiara.

    ⚠️ `sta_parlando` **non è qui**: lo riempie `MotoreNews`, e questi test
    esistono per verificare che sia l'unico a farlo.
    """
    return Contesto(pannello_a_schermo_intero=False, frase_in_corso=False)


async def _motore(sta_parlando=None, contesto=_tutto_il_resto_e_noto):
    """Un motore vero, con `Watcher` e `Gate` veri, e un argomento in memoria.

    Niente doppioni del gate: se la decisione la prendesse un finto, questi
    test misurerebbero il finto.
    """
    cards: list[dict] = []

    async def pubblica(msg: dict) -> None:
        cards.append(msg)

    collettore = _CollettoreFinto()
    watcher = Watcher([collettore], Gate(None), pubblica)
    m = MotoreNews(watcher, _Impostazioni(), contesto=contesto,
                   sta_parlando=sta_parlando, chiedi=_chiedi_clima)
    # Senza argomenti `un_giro()` non guarda affatto i feed: la lista vuota
    # è un rifiuto che verrebbe prima del gate, e nasconderebbe la misura.
    assert await m.ascolta("mi dici come va il clima") == ["clima"]
    return m, cards


def _uscite(cards: list[dict]) -> list[dict]:
    return [c for c in cards if c.get("topic") == "news.card"]


class TestQuandoLoStatoSiSA:
    """I due casi in cui la funzione risponde davvero."""

    async def test_se_JARVIS_parla_la_news_NON_esce(self) -> None:
        """§15, regola 2. La news è rilevante, il budget è libero, il resto
        del contesto è noto: l'unica cosa che la trattiene è la voce."""
        m, cards = await _motore(sta_parlando=lambda: True)
        assert await m.un_giro() is True, "il giro deve avvenire lo stesso"
        assert _uscite(cards) == [], (
            "una card è uscita mentre JARVIS stava parlando: §15, regola 2"
        )

    async def test_se_JARVIS_TACE_la_news_ESCE(self) -> None:
        """⚠️ **Il test che boccia.** Gli altri quattro casi tacciono, e
        tacerebbero anche a giunzione cancellata — cioè nello stato da cui si
        parte. Solo questo distingue «prudente» da «muto per costruzione»."""
        m, cards = await _motore(sta_parlando=lambda: False)
        assert await m.un_giro() is True
        uscite = _uscite(cards)
        assert len(uscite) == 1, (
            f"con la voce zitta e tutto il resto noto la news doveva uscire: "
            f"{cards}"
        )
        assert uscite[0]["titolo"] == TITOLO


class TestITreModiDiNonSapere:
    """Fail-closed: non esserci, sollevare, non tornare un `bool`.

    Tutti e tre valgono `None`, e `None` è un divieto.
    """

    async def test_la_funzione_ASSENTE_lascia_lo_stato_ignoto(self) -> None:
        """Lo stato del core fino a oggi. Nessuno l'ha collegata, e il gate
        non deve interrompere per questo — ma deve *poterlo dire*."""
        m, cards = await _motore(sta_parlando=None)
        assert await m.un_giro() is True
        assert _uscite(cards) == []
        assert m.stato()["voce_collegata"] is False

    async def test_senza_lettore_la_radice_puo_ancora_DICHIARARE(self) -> None:
        """Il rovescio della medaglia, dichiarato invece che scoperto.

        Senza lettore il campo non viene azzerato d'ufficio: resta quello che
        la radice di composizione mette nel `Contesto`. Azzerarlo toglierebbe
        alla radice il diritto di dichiarare ciò che sa, e aggiungerebbe un
        secondo produttore invece di toglierne uno. Con un lettore collegato,
        invece, vince il lettore — vedi `test_la_funzione_VINCE_sul_contesto`.
        """
        def dichiarato() -> Contesto:
            return Contesto(sta_parlando=False, pannello_a_schermo_intero=False,
                            frase_in_corso=False)

        m, cards = await _motore(sta_parlando=None, contesto=dichiarato)
        assert await m.un_giro() is True
        assert len(_uscite(cards)) == 1

    async def test_la_funzione_che_SOLLEVA_non_apre_la_bocca(self) -> None:
        """Un lettore rotto toglie il permesso di parlare; non ferma il motore.

        Le due metà contano entrambe: se l'eccezione fermasse il giro, il
        risultato sarebbe lo stesso silenzio ma per un guasto diverso, e i
        feed smetterebbero di essere guardati senza che si veda.
        """
        def rotta() -> bool:
            raise RuntimeError("la pipeline non risponde")

        m, cards = await _motore(sta_parlando=rotta)
        assert await m.un_giro() is True, "un lettore rotto non ferma il giro"
        assert _uscite(cards) == []

    async def test_la_funzione_che_torna_None(self) -> None:
        """«Non lo so» detto esplicitamente vale quanto non essere collegati."""
        m, cards = await _motore(sta_parlando=lambda: None)
        assert await m.un_giro() is True
        assert _uscite(cards) == []

    @pytest.mark.parametrize("valore", [0, "", [], 0.0])
    async def test_un_valore_FALSY_che_non_e_un_bool_non_e_uno_stato(
            self, valore: object) -> None:
        """⚠️ `isinstance(r, bool)` e non `bool(r)`.

        Un lettore che tornasse `0` o `""` — un campo non ancora
        inizializzato, un finto costruito male — con `bool()` diventerebbe
        `False`, cioè «è zitto, interrompi pure». Il dubbio deve costare il
        silenzio, mai una parola.
        """
        m, cards = await _motore(sta_parlando=lambda: valore)
        assert await m.un_giro() is True
        assert _uscite(cards) == [], (
            f"{valore!r} è stato letto come «non sta parlando»"
        )


class TestChiDecideDavvero:
    """Da dove viene quel bool, e quando viene letto."""

    async def test_la_funzione_VINCE_sul_contesto(self) -> None:
        """Un solo produttore per il campo.

        Se il `Contesto` di partenza potesse dire la sua, ci sarebbero due
        posti da guardare per sapere chi ha deciso — ed è il difetto che
        questa giunzione chiude. Qui il contesto è ottimista e la funzione
        dice di no: deve vincere la funzione.
        """
        def ottimista() -> Contesto:
            return Contesto(sta_parlando=False, pannello_a_schermo_intero=False,
                            frase_in_corso=False)

        m, cards = await _motore(sta_parlando=lambda: True, contesto=ottimista)
        assert await m.un_giro() is True
        assert _uscite(cards) == [], (
            "un `Contesto` ottimista ha aperto il gate mentre la voce parlava"
        )

    async def test_si_rilegge_a_OGNI_giro(self) -> None:
        """Letto una volta sola in costruzione, lo stato sarebbe una fotografia
        vecchia quanto l'avvio del core: JARVIS parla e tace di continuo."""
        letture: list[bool] = []

        def voce() -> bool:
            letture.append(True)
            return len(letture) == 1          # parla al primo giro, poi tace

        m, cards = await _motore(sta_parlando=voce)
        await m.un_giro()
        assert _uscite(cards) == [], "primo giro: parlava"
        await m.un_giro()
        assert len(_uscite(cards)) == 1, "secondo giro: taceva, e non è uscito nulla"
        assert len(letture) == 2, "la funzione va chiamata a ogni giro"

    async def test_lo_snapshot_dice_se_la_voce_e_COLLEGATA(self) -> None:
        """Senza questa riga «non è passata nessuna news» e «nessuno ha
        collegato lo stato della voce, quindi non ne passerà mai nessuna»
        sono lo stesso snapshot — ed è così che il difetto è sopravvissuto."""
        muto, _ = await _motore(sta_parlando=None)
        collegato, _ = await _motore(sta_parlando=lambda: False)
        assert muto.stato()["voce_collegata"] is False
        assert collegato.stato()["voce_collegata"] is True


class TestLaPipelineLoDiceInPUBBLICO:
    """L'altra metà della giunzione: chi produce lo stato.

    Leggere `_sta_parlando` da un altro modulo non è un contratto, è una
    coincidenza che regge finché nessuno lo rinomina.
    """

    def test_esiste_una_proprieta_pubblica(self) -> None:
        from core.voice.pipeline import VoicePipeline

        assert isinstance(VoicePipeline.__dict__.get("sta_parlando"), property), (
            "senza una proprietà pubblica l'unico modo di sapere se JARVIS "
            "parla è leggere un campo privato da fuori"
        )

    async def test_e_VERA_mentre_la_voce_esce_e_falsa_dopo(self) -> None:
        """Con un TTS vero-abbastanza: la proprietà segue la riproduzione.

        ⚠️ Si guarda al SECONDO blocco. Sul primo la bandiera si alza solo
        dopo che il blocco è stato scritto: fra la richiesta al TTS e il primo
        campione passa il tempo della sintesi, e in quella finestra non c'è
        ancora niente da interrompere.
        """
        from core.providers.health import Scelta
        from core.voice.pipeline import VoicePipeline

        from tests.conftest import AudioFinto

        visto: list[bool] = []

        class _Tts:
            name = "finto"
            per_enunciato = False

            async def stream(self, sorgente):
                async for _ in sorgente:
                    for _n in range(3):
                        yield type("C", (), {"pcm": b"\x01\x02" * 160,
                                             "sample_rate": 16_000})()
                        visto.append(p.sta_parlando)

            async def interrupt(self) -> None:
                return

        s = Scelta(provider=_Tts(), primario=True, motivo="", annuncio=None)
        p = VoicePipeline(audio=AudioFinto(), wake=None, stt=s, tts=s)

        async def una():
            yield "prova"

        assert p.sta_parlando is False
        await p.parla(una())
        assert visto[1:] == [True, True], (
            f"la proprietà non ha seguito la riproduzione: {visto}"
        )
        assert p.sta_parlando is False, "finita la frase, la bandiera si abbassa"

    async def test_la_giunzione_INTERA_dalla_voce_al_gate(self) -> None:
        """Pipeline vera, motore vero, gate vero, e nessun bool scritto a mano.

        Mentre `parla()` riproduce, un giro dei feed non deve far uscire
        niente; finita la frase, lo stesso giro deve farla uscire. È l'unico
        test qui che non contiene un `lambda: True` — la verità viene da chi
        la produce.
        """
        from core.providers.health import Scelta
        from core.voice.pipeline import VoicePipeline

        from tests.conftest import AudioFinto

        durante: list[int] = []

        class _Tts:
            name = "finto"
            per_enunciato = False

            async def stream(self, sorgente):
                async for _ in sorgente:
                    yield type("C", (), {"pcm": b"\x01\x02" * 160,
                                         "sample_rate": 16_000})()
                    # Qui la bandiera è alzata: il primo blocco è stato scritto.
                    await m.un_giro()
                    durante.append(len(_uscite(cards)))
                    yield type("C", (), {"pcm": b"\x03\x04" * 160,
                                         "sample_rate": 16_000})()

            async def interrupt(self) -> None:
                return

        s = Scelta(provider=_Tts(), primario=True, motivo="", annuncio=None)
        p = VoicePipeline(audio=AudioFinto(), wake=None, stt=s, tts=s)
        m, cards = await _motore(sta_parlando=lambda: p.sta_parlando)

        async def una():
            yield "prova"

        await p.parla(una())
        assert durante == [0], "una card è uscita mentre JARVIS parlava"

        await m.un_giro()
        assert len(_uscite(cards)) == 1, (
            "finita la frase la news non è uscita: la giunzione porta solo il no"
        )


class TestNonSiToccanoLeAltreREGOLE:
    """§15 ha cinque regole. Questa modifica ne serve **una**."""

    async def test_la_frase_a_META_resta_un_divieto(self) -> None:
        """«Mai a metà frase». La voce tace, e non basta."""
        def a_meta() -> Contesto:
            return Contesto(pannello_a_schermo_intero=False, frase_in_corso=True)

        m, cards = await _motore(sta_parlando=lambda: False, contesto=a_meta)
        assert await m.un_giro() is True
        assert _uscite(cards) == []

    async def test_il_pannello_a_schermo_intero_resta_un_divieto(self) -> None:
        """La regola 3, intatta."""
        def pieno() -> Contesto:
            return Contesto(pannello_a_schermo_intero=True, frase_in_corso=False)

        m, cards = await _motore(sta_parlando=lambda: False, contesto=pieno)
        assert await m.un_giro() is True
        assert _uscite(cards) == []

    async def test_il_budget_di_TRE_allora_non_si_muove(self) -> None:
        """Aprire la strada alla voce non allarga il tetto: al quarto giro
        con la voce zitta il budget deve mordere."""
        m, cards = await _motore(sta_parlando=lambda: False)
        for _ in range(4):
            await m.un_giro()
        assert len(_uscite(cards)) == 3, (
            f"il tetto di §15 è 3/ora: uscite {len(_uscite(cards))}"
        )


class TestNienteAttributiScrittiDaFUORI:
    """La forma della giunzione, non solo il suo effetto."""

    def test_lo_stato_arriva_per_FUNZIONE(self) -> None:
        """Un attributo scritto da fuori sarebbe una fotografia: chi lo scrive
        decide *quando*, e nessuno sa se è ancora vero al giro dopo."""
        import inspect

        firma = inspect.signature(MotoreNews.__init__)
        p = firma.parameters["sta_parlando"]
        assert p.kind is inspect.Parameter.KEYWORD_ONLY
        assert p.default is None, "il default deve essere «non collegata»"

    def test_il_core_non_legge_il_campo_privato_della_pipeline(self) -> None:
        """`_voce._sta_parlando` letto da un altro modulo è la coincidenza che
        questa modifica sostituisce. Qui si controlla solo i file di §15: la
        radice di composizione la cabla un altro passaggio."""
        from pathlib import Path

        radice = Path(__file__).resolve().parent.parent
        for nome in ("core/news/motore.py", "core/news/gate.py"):
            s = (radice / nome).read_text(encoding="utf-8")
            assert "_voce._sta_parlando" not in s, nome


class TestUnGiroNonMuoreMai:
    """Il percorso resta quello di prima: le news non fermano il core."""

    async def test_un_contesto_che_solleva_non_ferma_il_motore(self) -> None:
        def rotto():
            raise RuntimeError("contesto non disponibile")

        m, cards = await _motore(sta_parlando=lambda: False, contesto=rotto)
        assert await m.un_giro() is False, "il giro fallisce, e lo dice"
        assert _uscite(cards) == []
        assert m.giri == 0

    async def test_il_ciclo_continua_dopo_un_lettore_rotto(self) -> None:
        """Due giri di fila con la funzione rotta: nessuna eccezione esce."""
        def rotta() -> bool:
            raise ValueError("no")

        m, _ = await _motore(sta_parlando=rotta)
        await asyncio.gather(m.un_giro(), m.un_giro())
        assert m.giri == 2
