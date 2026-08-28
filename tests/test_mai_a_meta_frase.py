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

    def test_NON_e_piu_un_valore_scritto_a_mano(self) -> None:
        s = self._src()
        corpo = s.split("def _contesto_news", 1)[1].split("\n    def ", 1)[0]
        # Via la docstring: spiega il difetto corretto e lo NOMINA, e un test
        # che cercasse la stringa nuda sarebbe rosso per la spiegazione invece
        # che per il codice. Ottava volta in questa sessione.
        corpo = corpo.split('"""', 2)[-1]
        assert "frase_in_corso=False" not in corpo, (
            "il valore fisso e' tornato: la regola «mai a meta' frase» e' spenta"
        )
        assert "frase_in_corso=self._voce_frase_in_corso()" in corpo

    def test_a_voce_spenta_resta_IGNOTO(self, short_paths) -> None:
        """`None` e non `False`, come gli altri due campi: senza microfono non
        c'è nessuno che possa saperlo, e l'ignoto non interrompe."""
        from core.engine import Engine

        e = Engine(short_paths)
        assert e._voce is None
        assert e._voce_frase_in_corso() is None
        assert e._voce_sta_parlando() is None

    def test_una_voce_che_SOLLEVA_vale_ignoto_e_non_porta_via_gli_altri(
            self, short_paths) -> None:
        """⚠️ `MotoreNews` costruisce il contesto con `base = self._contesto()`:
        se la radice solleva non è un campo a diventare ignoto, è il giro delle
        news a morire. Tre campi che dipendono dalla voce e una sola eccezione
        che li porta via tutti non è fail-closed, è un guasto."""
        from core.engine import Engine

        class _Rotta:
            @property
            def frase_in_corso(self):
                raise RuntimeError("pipeline in uno stato illegale")

            @property
            def sta_parlando(self):
                return True

        e = Engine(short_paths)
        e._voce = _Rotta()
        assert e._voce_frase_in_corso() is None
        assert e._voce_sta_parlando() is True, "l'altro campo e' caduto con lui"

    def test_un_valore_che_non_e_un_BOOL_vale_ignoto(self, short_paths) -> None:
        """Un attributo non inizializzato che torna `0` diventerebbe `False`
        con `bool()`, cioè un permesso."""
        from core.engine import Engine

        class _Storta:
            frase_in_corso = 0
            sta_parlando = ""

        e = Engine(short_paths)
        e._voce = _Storta()
        assert e._voce_frase_in_corso() is None
        assert e._voce_sta_parlando() is None

    def test_e_i_TRE_campi_hanno_un_produttore(self) -> None:
        """⚠️ La prova che chiude §15: fino a ieri due dei tre erano `None` per
        sempre, e il gate non poteva lasciar passare niente qualunque cosa
        dicessero gli altri."""
        s = self._src()
        corpo = s.split("def _contesto_news", 1)[1].split(
            "\n    def ", 1)[0].split('"""', 2)[-1]
        for campo in ("frase_in_corso=", "pannello_a_schermo_intero="):
            assert campo in corpo, f"{campo} non e' dichiarato"
            assert f"{campo}None" not in corpo, f"{campo} e' ancora ignoto per sempre"
        assert "sta_parlando=self._voce_sta_parlando," in s, (
            "il terzo arriva per funzione al MotoreNews, non dal Contesto"
        )
