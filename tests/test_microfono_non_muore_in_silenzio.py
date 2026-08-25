"""Il microfono che si chiude lo dice — e un turno perso non lo chiude.

## La battuta d'arresto che questi test sorvegliano

`core/engine.py` avvia la voce con `asyncio.create_task(self._voce.run())` e
`core/voice/pipeline.py` chiama `_su_trigger()` dentro un `async for`. Nessuno
dei due, prima, aveva una rete: **un'eccezione qualunque chiudeva il microfono
per il resto della sessione, senza una parola.**

Che il guasto sia MUTO e' misurato, non supposto. Un compito che solleva mentre
qualcuno ne tiene il riferimento:

    [  300.6 ms] a 0,3 s: done=True — il core e' vivo e tiene il riferimento
    [  601.3 ms] FINE del programma
    [  605.9 ms] loop.call_exception_handler: 'Task exception was never retrieved'

L'unico messaggio arriva **dopo la fine del programma**, cioe' alla distruzione
dell'oggetto. Un core che gira per ore tenendo quel riferimento non ci arriva
mai: nei log non compare niente, e chi parla parla nel vuoto.

E le sorgenti di eccezione non sono ipotetiche: su questa macchina non c'e'
chiave Deepgram, quindi il TTS e' **EdgeTTS, che e' di rete**; T1 e' un processo
esterno; `pw-play` puo' mancare.
"""

from __future__ import annotations

import asyncio

import pytest

from core.providers.health import Scelta
from core.voice.audio_io import byte_per_blocco
from core.voice.pipeline import VoicePipeline

BLOCCO = byte_per_blocco(16_000)          # 640


class _Provider:
    def __init__(self, name: str = "finto") -> None:
        self.name = name

    async def stream(self, sorgente):
        async for _ in sorgente:
            return
        return
        yield                                            # pragma: no cover


class _AudioFinto:
    """Restituisce blocchi IRREGOLARI, come il microfono vero."""

    #: Le dimensioni misurate su `read(640)` di questa macchina.
    GRANULARITA = [640, 42, 640, 44, 42, 626, 640, 24, 44, 640, 42, 640]

    def __init__(self, ripetizioni: int = 4) -> None:
        self.aperture: list[int | None] = []
        self._ripetizioni = ripetizioni

    def input_stream(self, sample_rate=None):
        self.aperture.append(sample_rate)

        async def gen():
            for _ in range(self._ripetizioni):
                for n in self.GRANULARITA:
                    # ⚠️ Campioni che ALTERNANO, non un valore costante.
                    # Prima era `b"\x40\x30"` ripetuto, cioe' una continua
                    # pura: passava per parlato solo perche' `VAD.energia()`
                    # non toglieva la media, ed e' il difetto corretto in
                    # `test_voce_barge_in.py`. Un dato di prova che si regge
                    # su un difetto sparisce insieme al difetto.
                    yield (b"\x00\x30\x00\xd0" * (n // 4)
                           + b"\x00" * (n % 4))
        return gen()

    async def play(self, *_a, **_k) -> None:
        return


class _WakeSempre:
    """Ogni blocco e' un trigger: cosi' un turno che fallisce si vede subito."""

    class _T:
        frase = "jarvis"
        azione = "listen"
        latenza_ms = 0.1

    frasi = ("jarvis",)

    def feed(self, _pcm):
        return self._T()


def _pipeline(audio, wake, **kw) -> VoicePipeline:
    scelta = Scelta(provider=_Provider(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=audio, wake=wake, stt=scelta, tts=scelta, **kw)


class TestUnTurnoCadutoNonChiudeIlMicrofono:
    """Il difetto: `await self._su_trigger(trigger)` senza `try`. Una sola
    eccezione — EdgeTTS irraggiungibile, T1 morto — e l'`async for` finiva."""

    async def test_il_ciclo_SOPRAVVIVE_a_un_turno_che_solleva(self) -> None:
        audio = _AudioFinto()
        p = _pipeline(audio, _WakeSempre())
        cadute = 0

        async def esplode(_trigger):
            nonlocal cadute
            cadute += 1
            raise RuntimeError("EdgeTTS: rete assente")

        p._su_trigger = esplode
        await asyncio.wait_for(p.run(), timeout=5)

        assert cadute > 1, (
            f"il ciclo si e' fermato al primo turno caduto ({cadute}): il "
            "microfono resta chiuso per il resto della sessione"
        )

    async def test_l_annullamento_passa_ancora(self) -> None:
        """`CancelledError` NON e' un turno caduto: e' lo spegnimento, e
        inghiottirlo renderebbe `_spegni_gradi()` un'attesa infinita."""
        audio = _AudioFinto(ripetizioni=200)
        p = _pipeline(audio, _WakeSempre())

        async def annulla(_trigger):
            raise asyncio.CancelledError()

        p._su_trigger = annulla
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(p.run(), timeout=5)


class TestLaTrascrizioneRiceveBlocchiDellaMisura:
    """La correzione di `audio_io.py` era finita sul percorso del wake e NON su
    questo — che e' proprio quello che manda il testo fuori dalla macchina."""

    async def test_i_blocchi_sono_ESATTI_anche_qui(self) -> None:
        audio = _AudioFinto()
        visti: list[int] = []

        class _Ascolta(_Provider):
            async def stream(self, sorgente):
                async for b in sorgente:
                    visti.append(len(b))
                return
                yield                                    # pragma: no cover

        scelta = Scelta(provider=_Ascolta(), primario=True, motivo="", annuncio=None)
        p = VoicePipeline(audio=audio, wake=_WakeSempre(), stt=scelta, tts=scelta)
        await asyncio.wait_for(p._trascrivi(limite_s=0.5), timeout=5)

        assert visti, "il riconoscitore non ha ricevuto un solo blocco"
        assert set(visti) == {BLOCCO}, (
            f"dimensioni arrivate allo STT: {sorted(set(visti))}. Un blocco di "
            "lunghezza dispari spezza un campione s16 fra due chiamate"
        )

    async def test_il_rate_si_PASSA(self) -> None:
        """`core/platform/base.py` dichiara `input_stream(sample_rate)` SENZA
        valore predefinito: chiamarlo nudo funziona solo per il default
        dell'implementazione Linux, e su Windows (invariante 29) sarebbe un
        `TypeError` al primo turno."""
        audio = _AudioFinto()
        p = _pipeline(audio, _WakeSempre(), rate=16_000)
        await asyncio.wait_for(p._trascrivi(limite_s=0.3), timeout=5)

        assert audio.aperture, "nessuna apertura del dispositivo"
        assert all(r == 16_000 for r in audio.aperture), (
            f"aperture: {audio.aperture} — un `None` e' la chiamata nuda"
        )


class TestJarvisHaUnaVoceSola:
    """Due cose dette insieme non sono due cose dette: sono rumore.

    Misurato PRIMA del lucchetto, due `parla()` concorrenti davano

        ordine: A0 B0 A1 B1 A2 B2

    cioe' i frammenti di due frasi alternati nell'altoparlante. E non e' un
    caso limite: su questa macchina i ripieghi annunciati all'avvio sono DUE —
    ascolto locale e voce di ripiego — quindi e' il caso NORMALE.

    C'e' un secondo guasto sotto, piu' silenzioso: il `finally` della prima
    frase che finisce spegne `_sta_parlando` mentre la seconda sta ancora
    parlando, e da li' in poi il barge-in non risponde piu'.
    """

    async def test_due_frasi_NON_si_intrecciano(self) -> None:
        ordine: list[str] = []

        class _TtsLento:
            name = "finto"
            per_enunciato = False

            async def stream(self, sorgente):
                async for testo in sorgente:
                    for i in range(3):
                        await asyncio.sleep(0.01)
                        yield type("C", (), {"pcm": f"{testo}{i}".encode(),
                                             "sample_rate": 16_000})()

            async def interrupt(self):
                return

        class _Altoparlante:
            async def play(self, pcm, rate=None):
                ordine.append(pcm.decode())

            def input_stream(self, sample_rate=None):
                async def gen():
                    return
                    yield b""                            # pragma: no cover
                return gen()

        scelta = Scelta(provider=_TtsLento(), primario=True, motivo="",
                        annuncio=None)
        p = VoicePipeline(audio=_Altoparlante(), wake=None, stt=scelta,
                          tts=scelta)

        async def una(t):
            yield t

        await asyncio.gather(p.parla(una("A")), p.parla(una("B")))
        iniziali = "".join(o[0] for o in ordine)
        assert iniziali in ("AAABBB", "BBBAAA"), (
            f"ordine all'altoparlante: {' '.join(ordine)} — due frasi "
            "intrecciate, non due frasi"
        )
