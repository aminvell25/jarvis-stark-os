"""Un turno che non finisce rende JARVIS sordo, e il battito non lo vedeva.

Il 27 agosto alle 00:55:19 un turno è partito. La cattura è finita alle
00:55:27. Poi più niente — per **quattro minuti**, finché non l'ho guardato.

Misurato in quel momento:

    pw-record 888553   anon_pipe_write   0 byte in 3 s
    snapshot           "microfono": "aperto"

Sono **due difetti incastrati**, e il secondo nasconde il primo.

**① Lo STT non aveva un tetto.** `async for grezzo in ws` su un socket che
tace senza chiudersi aspetta per sempre. E il danno non resta lì:
`_su_trigger` è atteso DENTRO l'`async for` del microfono, quindi un turno
appeso ferma il ciclo audio, `pw-record` riempie la pipe e si blocca.

**② Il battito era cieco esattamente nel caso che lo produce.** La bandiera
`_in_turno`, scritta il giorno prima perché il battito non gridasse al lupo a
ogni conversazione, gli impediva anche di vedere una conversazione che non
finisce. L'avevo scritto io, e non gli avevo messo una fine.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.voice.pipeline import TETTO_TURNO_S


def _sorgente(nome: str) -> str:
    return (Path(__file__).resolve().parent.parent / nome).read_text(encoding="utf-8")


def _senza_commenti(s: str) -> str:
    """Il CODICE, non i commenti: quattro volte in questa sessione un mio test
    ha letto una spiegazione invece di una riga vera."""
    fuori = []
    for r in s.splitlines():
        t = r.split("#", 1)[0] if not r.lstrip().startswith("#:") else ""
        fuori.append(t)
    return "\n".join(fuori)


class TestLoSTTdeveAvereUnTetto:
    def test_la_recv_e_sotto_wait_for(self) -> None:
        """`async for grezzo in ws` non ha un tetto: un socket muto che non si
        chiude appende il turno per sempre."""
        s = _senza_commenti(_sorgente("core/providers/stt_deepgram.py"))
        assert "asyncio.wait_for(ws.recv()" in s.replace("\n", " ").replace("  ", " ") or \
               "wait_for(ws.recv()" in " ".join(s.split())
        assert "async for grezzo in ws" not in s

    def test_il_tetto_e_lo_STESSO_del_TTS(self) -> None:
        """Stesso tipo di socket, stesso fornitore, stessa rete: la misura che
        ha prodotto il venti — «il primo suono sta fra 3,6 e 14,0 s» — descrive
        anche questo. Non è simmetria estetica."""
        from core.providers.stt_deepgram import TETTO_RECV_S as stt
        from core.providers.tts_deepgram import TETTO_RECV_S as tts

        assert stt == tts == 20.0

    def test_il_silenzio_del_fornitore_si_ANNUNCIA(self) -> None:
        """Un turno chiuso in silenzio è indistinguibile da «non ha capito»."""
        s = _senza_commenti(_sorgente("core/providers/stt_deepgram.py"))
        assert '"stt_muto"' in s or "'stt_muto'" in s


class TestIlBattitoNonEPiuCiecoDuranteUnTurno:
    """La bandiera che gli impediva di gridare al lupo gli impediva anche di
    vedere il lupo."""

    def _pipeline(self):
        from core.providers.health import Scelta
        from core.voice.pipeline import VoicePipeline
        from tests.conftest import AudioFinto

        class _P:
            name = "finto"
            per_enunciato = False

            async def stream(self, testo):
                return
                yield                                    # pragma: no cover

            async def interrupt(self): return

        s = Scelta(provider=_P(), primario=True, motivo="", annuncio=None)
        return VoicePipeline(audio=AudioFinto(), wake=None, stt=s, tts=s)

    def test_un_turno_NORMALE_sospende_l_allarme(self) -> None:
        p = self._pipeline()
        p._ultimo_blocco = 1000.0
        p._in_turno = True
        p._turno_da = 1000.0
        assert p.muto_da(adesso=1000.0 + TETTO_TURNO_S - 1) == 0.0

    def test_un_turno_APPESO_no(self) -> None:
        """Il caso vero: quattro minuti dentro lo stesso turno."""
        p = self._pipeline()
        p._ultimo_blocco = 1000.0
        p._in_turno = True
        p._turno_da = 1000.0
        muto = p.muto_da(adesso=1000.0 + 240.0)
        assert muto == pytest.approx(240.0), (
            f"muto_da = {muto}: un turno di quattro minuti è appeso, non in corso"
        )

    def test_il_tetto_e_la_SOMMA_dei_tetti_dichiarati(self) -> None:
        """Non un numero scelto. Se uno degli stadi cambia il proprio tetto,
        questo test dice che la somma non lo segue più."""
        from core.providers.stt_deepgram import TETTO_RECV_S

        cattura = 8.0                        # `_trascrivi(limite_s=8.0)`
        t1 = 90.0                            # `ClaudeT1.ask(timeout=90.0)`
        assert TETTO_TURNO_S == cattura + TETTO_RECV_S + t1

    def test_i_due_tetti_veri_ESISTONO_ancora(self) -> None:
        """⚠️ La somma sopra sarebbe una bugia se i due numeri fossero
        cambiati sotto: qui si leggono dove vivono davvero."""
        assert "limite_s: float = 8.0" in _sorgente("core/voice/pipeline.py")
        assert "timeout: float = 90.0" in _sorgente("core/llm/claude_t1.py")

    def test_fuori_da_un_turno_non_cambia_niente(self) -> None:
        p = self._pipeline()
        p._ultimo_blocco = 1000.0
        p._in_turno = False
        assert p.muto_da(adesso=1042.0) == pytest.approx(42.0)

    def test_e_il_turno_TIMBRA_quando_comincia(self) -> None:
        s = _senza_commenti(_sorgente("core/voice/pipeline.py"))
        assert "self._turno_da = time.monotonic()" in s


# ── il turno fuori dal ciclo: due proprietà che i commenti dichiaravano e
#    nessun test imponeva. Trovate eseguendo le bocciature ③ e ④.

class _Audio:
    """Un microfono che non finisce e che CEDE il controllo fra i blocchi,
    come fa uno vero."""

    def __init__(self) -> None:
        self.letti = 0

    def input_stream(self, sample_rate=None):
        async def gen():
            while True:
                self.letti += 1
                yield b"\x00\x30\x00\xd0" * 160
                await asyncio.sleep(0)
        return gen()

    async def play(self, *_a, **_k): return


class _AudioFinito(_Audio):
    def __init__(self, quanti: int = 12) -> None:
        super().__init__()
        self._quanti = quanti

    def input_stream(self, sample_rate=None):
        async def gen():
            for _ in range(self._quanti):
                self.letti += 1
                yield b"\x00\x30\x00\xd0" * 160
                await asyncio.sleep(0)
        return gen()


class _WakeSempre:
    frasi = ("jarvis",)

    class _T:
        frase, azione, latenza_ms = "jarvis", "listen", 0.1

    def feed(self, _pcm):
        return self._T()


def _pipeline_con(audio, wake):
    from core.providers.health import Scelta
    from core.voice.pipeline import VoicePipeline

    class _P:
        name = "finto"
        per_enunciato = False

        async def stream(self, testo):
            return
            yield                                        # pragma: no cover

        async def interrupt(self): return

    s = Scelta(provider=_P(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=audio, wake=wake, stt=s, tts=s)


class TestUnTurnoAllaVolta:
    async def test_un_secondo_risveglio_NON_apre_un_secondo_turno(self) -> None:
        """⚠️ Con il turno fuori dal ciclo, il ciclo continua a leggere anche
        mentre JARVIS parla — ed è il suo stesso eco che rientra dal microfono.
        Senza questo freno ogni blocco di eco diventerebbe un turno nuovo.
        """
        a, w = _Audio(), _WakeSempre()
        p = _pipeline_con(a, w)
        aperti = 0

        async def turno(_t):
            nonlocal aperti
            aperti += 1
            await asyncio.sleep(3600)

        p._su_trigger = turno
        compito = asyncio.create_task(p.run())
        for _ in range(80):
            await asyncio.sleep(0)
        assert a.letti > 20, "il ciclo non sta leggendo"
        assert aperti == 1, f"{aperti} turni insieme: l'eco di JARVIS ne apre uno per blocco"
        p.stop()
        compito.cancel()
        try:
            await compito
        except asyncio.CancelledError:
            pass


class TestLeDueUsciteNonSonoLaStessa:
    async def test_l_uscita_NORMALE_aspetta_il_turno(self) -> None:
        """Il microfono che finisce non deve tagliare a metà una risposta già
        cominciata: sarebbe peggio del guasto."""
        p = _pipeline_con(_AudioFinito(), _WakeSempre())
        aperti = chiusi = 0

        async def turno(_t):
            nonlocal aperti, chiusi
            aperti += 1
            # Abbastanza lento da essere ancora in volo quando il flusso
            # finisce: è quello il caso da provare.
            for _ in range(20):
                await asyncio.sleep(0)
            chiusi += 1

        p._su_trigger = turno
        await asyncio.wait_for(p.run(), timeout=3)
        assert aperti >= 1
        assert chiusi == aperti, (
            f"{aperti - chiusi} turni troncati dall'uscita del ciclo: il "
            "microfono che finisce non deve tagliare a metà una risposta"
        )

    async def test_l_ANNULLAMENTO_invece_lo_porta_via(self) -> None:
        p = _pipeline_con(_Audio(), _WakeSempre())
        partito = asyncio.Event()

        async def turno(_t):
            partito.set()
            await asyncio.sleep(3600)

        p._su_trigger = turno
        compito = asyncio.create_task(p.run())
        for _ in range(40):
            await asyncio.sleep(0)
        assert partito.is_set()
        t = p._compito_turno
        compito.cancel()
        with pytest.raises(asyncio.CancelledError):
            await compito
        assert t.cancelled(), "il turno è sopravvissuto alla pipeline annullata"
