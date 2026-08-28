"""«Mai a metà frase» era spenta da un `False` scritto a mano.

`Engine._contesto_news` dichiarava:

    return Contesto(frase_in_corso=False, ...)

con la giustificazione, scritta accanto: *«il turno dell'utente è chiuso quando
il giro dei feed gira»*.

**Non è vero.** Il giro delle news sta su un timer suo — `min(max(3600/(2·tetto),
60), ttl·60/2)`, cioè 600 s con la configurazione di oggi — ed è un compito
indipendente dai turni vocali. Può scattare mentre il Signore sta parlando.

Con quel `False`, una delle cinque regole che §15 chiama «le regole senza cui
abbandonerà la funzione in tre giorni» era disattivata: il gate rispondeva
«nessuna frase a metà» sempre, e una card poteva uscire in mezzo a una frase.

Era un valore SCELTO presentato come un fatto — la forma di difetto che questo
progetto insegue da settimane, qui dentro una riga che ho scritto io stesso
poche ore prima.
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _pipeline():
    from core.providers.health import Scelta
    from core.voice.pipeline import VoicePipeline
    from tests.conftest import AudioFinto

    class _P:
        name = "finto"
        per_enunciato = False

        async def stream(self, testo):
            return
            yield                                        # pragma: no cover

        async def interrupt(self): return

    s = Scelta(provider=_P(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=AudioFinto(), wake=None, stt=s, tts=s)


class TestLaPipelineSaSeLUtenteHaUnaFraseAMeta:
    def test_in_silenzio_NON_ce_l_ha(self) -> None:
        p = _pipeline()
        assert p.frase_in_corso is False

    def test_col_gate_APERTO_sta_parlando_adesso(self) -> None:
        """Il VAD ha sentito voce e l'enunciato non è ancora chiuso."""
        p = _pipeline()
        p._gate_aperto = True
        assert p.frase_in_corso is True

    def test_e_durante_un_TURNO_lo_scambio_è_aperto(self) -> None:
        """Ha finito di parlare e JARVIS gli sta rispondendo: infilarci una
        notizia in mezzo è la stessa scortesia."""
        p = _pipeline()
        p._in_turno = True
        assert p.frase_in_corso is True

    def test_i_due_stati_sono_INDIPENDENTI(self) -> None:
        """Uno solo dei due lascerebbe scoperta metà dello scambio."""
        p = _pipeline()
        p._gate_aperto, p._in_turno = True, True
        assert p.frase_in_corso is True
        p._gate_aperto = False
        assert p.frase_in_corso is True, "il turno da solo non basta piu'"
        p._in_turno, p._gate_aperto = False, True
        assert p.frase_in_corso is True, "il gate da solo non basta piu'"


class TestIlMotoreLoCHIEDEallaVoce:
    def _src(self) -> str:
        return (RADICE / "core" / "engine.py").read_text(encoding="utf-8")

    def test_NON_e_piu_un_valore_scritto_a_mano(self, short_paths) -> None:
        """⚠️ Era un test di GREP, e la nona volta in questa sessione che ne
        scrivo uno che legge il testo invece del comportamento. Un valore fisso
        non si riconosce dalla stringa che lo scrive: si riconosce dal fatto
        che **non cambia quando cambia la voce**.
        """
        from core.engine import Engine

        class _Voce:
            frase_in_corso = False
            sta_parlando = False

        e = Engine(short_paths)
        e._voce = _Voce()
        assert e._contesto_news().contesto().frase_in_corso is False
        e._voce.frase_in_corso = True
        assert e._contesto_news().contesto().frase_in_corso is True, (
            "il campo non segue la voce: e' un valore scritto a mano, e la "
            "regola «mai a meta' frase» e' spenta"
        )

    def test_a_voce_spenta_resta_IGNOTO_ed_e_CONFIGURAZIONE(self, short_paths) -> None:
        """`None` e non `False`: senza microfono non c'è nessuno che possa
        saperlo, e l'ignoto non interrompe.

        ⚠️ E la causa è `non_composto`, **non** `ha_sollevato`: a voce spenta
        `self._voce.frase_in_corso` alzerebbe un `AttributeError` su `None`, e
        un interruttore da accendere arriverebbe a chi guarda travestito da
        difetto da inseguire.
        """
        from core.engine import Engine
        from core.news.conoscibilita import NON_COMPOSTO

        e = Engine(short_paths)
        assert e._voce is None
        s = e._voce_frase_in_corso()
        assert s.valore is None and s.causa == NON_COMPOSTO
        assert e._voce_sta_parlando() is None

    def test_una_voce_che_SOLLEVA_e_un_GUASTO_e_non_porta_via_gli_altri(
            self, short_paths) -> None:
        """⚠️ `MotoreNews` costruisce la lettura con `self._contesto()`: se la
        radice solleva non è un campo a diventare ignoto, è il giro delle news
        a morire. Tre campi che dipendono dalla voce e una sola eccezione che
        li porta via tutti non è fail-closed, è un guasto."""
        from core.engine import Engine
        from core.news.conoscibilita import HA_SOLLEVATO

        class _Rotta:
            @property
            def frase_in_corso(self):
                raise RuntimeError("pipeline in uno stato illegale")

            @property
            def sta_parlando(self):
                return True

        e = Engine(short_paths)
        e._voce = _Rotta()
        s = e._voce_frase_in_corso()
        assert s.valore is None and s.causa == HA_SOLLEVATO, (
            "un produttore rotto e una voce spenta non sono la stessa cosa: "
            "il primo si insegue, la seconda si accende"
        )
        assert e._voce_sta_parlando() is True, "l'altro campo e' caduto con lui"
        assert e._contesto_news().contesto().pannello_a_schermo_intero is None

    def test_un_valore_che_non_e_un_BOOL_vale_ignoto(self, short_paths) -> None:
        """Un attributo non inizializzato che torna `0` diventerebbe `False`
        con `bool()`, cioè un permesso."""
        from core.engine import Engine
        from core.news.conoscibilita import RISPOSTA_STORTA

        class _Storta:
            frase_in_corso = 0
            sta_parlando = ""

        e = Engine(short_paths)
        e._voce = _Storta()
        s = e._voce_frase_in_corso()
        assert s.valore is None and s.causa == RISPOSTA_STORTA

    def test_LA_VOCE_NON_INGOIA_il_guasto_di_sta_parlando(self, short_paths) -> None:
        """⚠️ Questa è una riga TOLTA, non aggiunta.

        `_voce_sta_parlando` aveva un `try/except` che rendeva `None` una
        pipeline rotta. `MotoreNews._parla_adesso` ne ha già uno che fa la
        stessa cosa e in più sa **classificarla**: ingoiando qui, un guasto
        arrivava a chi guarda travestito da voce spenta.
        """
        from core.engine import Engine

        class _Rotta:
            @property
            def sta_parlando(self):
                raise RuntimeError("pipeline in uno stato illegale")

        e = Engine(short_paths)
        e._voce = _Rotta()
        import pytest as _pytest
        with _pytest.raises(RuntimeError):
            e._voce_sta_parlando()

    def test_e_i_TRE_campi_hanno_un_produttore(self, short_paths) -> None:
        """⚠️ La prova che chiude §15: fino a ieri due dei tre erano `None` per
        sempre, e il gate non poteva lasciar passare niente qualunque cosa
        dicessero gli altri.

        Si guarda il **comportamento**, non il testo: a voce viva e scrivania
        viva nessuno dei tre campi resta ignoto.
        """
        from core.engine import Engine
        from core.layout import GeometriaPannello, Layout
        from core.news.conoscibilita import NOTO
        from core.news.motore import MotoreNews

        class _Voce:
            frase_in_corso = True
            sta_parlando = False

        class _Imp:
            max_interruptions_per_hour = 3
            topic_ttl_minutes = 30

        e = Engine(short_paths)
        e._voce = _Voce()
        e._layout._ultimo = Layout(pannelli=[
            GeometriaPannello(id="meteo", x=0, y=0, larghezza=10, altezza=10,
                              massimizzato=True)])
        m = MotoreNews(object(), _Imp(), contesto=e._contesto_news,
                       sta_parlando=e._voce_sta_parlando)
        ctx = m._contesto_adesso()
        assert (ctx.frase_in_corso, ctx.pannello_a_schermo_intero,
                ctx.sta_parlando) == (True, True, False)
        assert set(m.conoscibilita().values()) == {NOTO}, m.conoscibilita()
