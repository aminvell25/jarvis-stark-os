"""Il VAD misura il suono, non il convertitore. E il barge-in torna indietro.

## Tre difetti trovati collegando l'annuncio alla voce

Sono venuti fuori tutti e tre dallo stesso gesto — far dire a JARVIS le due
frasi di ripiego all'avvio — e nessuno dei tre sollevava.

**1. `VAD.energia()` non toglieva la media.** Il microfono di questa macchina
ha una polarizzazione continua di **-8470,5 su 32768**, e l'RMS calcolato senza
toglierla misura quella invece del suono:

    offset continuo             -8470,5
    RMS con la continua dentro   0,25856
    RMS senza                    0,00242
    soglia di apertura           0,01200

Ventuno volte sopra la soglia: **250 blocchi su 250** erano giudicati parlato
in cinque secondi di stanza vuota. Il gate non si chiudeva mai, quindi il
barge-in scattava all'istante ogni volta che JARVIS apriva bocca — le frasi di
ripiego morivano **prima del primo campione** — e Vosk veniva alimentato in
continuazione, che e' esattamente cio' che §7.1 chiede a questo gate di non
fare. Dopo la correzione: 46 blocchi su 250, il **18,4 %**.

**2. `_sta_parlando` diventava vero prima che si sentisse qualcosa.** Fra la
richiesta al TTS e il primo campione passa il tempo della sintesi: misurato con
EdgeTTS su questa rete, **1161 ms**. In quella finestra il barge-in poteva
scattare contro il silenzio, e scattava.

**3. `EdgeTTS.interrupt()` alzava solo una bandiera.** La bandiera si legge fra
una lettura e l'altra del decodificatore, e quella lettura non torna: misurato,
dopo il primo barge-in su dispositivo vero `parla()` **non tornava piu'** —
appesa oltre i dieci secondi di prova, col lucchetto della voce in mano. Da li'
in poi JARVIS non poteva piu' dire niente per il resto della sessione.
`LinuxAudio.interrupt()` aveva gia' scritto la regola giusta venti file piu' in
la': si uccide il processo, non si chiede al ciclo di collaborare.
"""

from __future__ import annotations

import array
import asyncio
import time

import pytest

from core.providers.health import Scelta
from core.providers.tts_local import EdgeTTS
from core.voice.pipeline import (
    BLOCCHI_BARGE_IN,
    SOGLIA_BARGE_IN,
    VAD,
    VoicePipeline,
)

#: L'offset misurato sul microfono di questa macchina.
CONTINUA = -8470


def _blocco(campioni) -> bytes:
    return array.array("h", campioni).tobytes()


class TestIlVadMisuraIlSuonoNonIlConvertitore:
    def test_una_POLARIZZAZIONE_non_e_parlato(self) -> None:
        """Un blocco perfettamente costante non contiene suono: contiene un
        numero. Prima valeva 0,258 contro una soglia di 0,012."""
        pcm = _blocco([CONTINUA] * 320)
        assert VAD.energia(pcm) < 0.001, VAD.energia(pcm)
        assert not VAD().parla(pcm)

    def test_il_parlato_SOPRA_la_polarizzazione_si_sente_ancora(self) -> None:
        """La meta' che conta di piu': togliere la continua non deve rendere
        sordo il gate. Stesso offset, con un'onda sopra."""
        import math

        onda = [CONTINUA + int(6000 * math.sin(i / 4)) for i in range(320)]
        assert VAD.energia(_blocco(onda)) > 0.012
        assert VAD().parla(_blocco(onda))

    def test_il_silenzio_VERO_resta_silenzio(self) -> None:
        assert VAD.energia(_blocco([0] * 320)) == 0.0
        assert not VAD().parla(_blocco([0] * 320))

    def test_la_stanza_MISURATA_non_apre_il_gate(self) -> None:
        """La mediana vera di questa stanza dopo la correzione, 0,00101, sta
        sotto la soglia di chiusura. Il numero e' misurato, non scelto."""
        import math

        stanza = [CONTINUA + int(33 * math.sin(i / 3)) for i in range(320)]
        e = VAD.energia(_blocco(stanza))
        assert e < 0.006, f"energia {e:.5f}: la stanza aprirebbe il gate"


class TestNienteDaInterrompereFinchNonSiSenteNiente:
    """Il barge-in contro il silenzio: `_sta_parlando` era vero durante i
    1161 ms di sintesi, quando JARVIS non era ancora udibile."""

    async def test_sta_parlando_solo_DOPO_il_primo_suono(self) -> None:
        visto_prima = []

        class _TtsLento:
            name = "lento"
            per_enunciato = False

            async def stream(self, sorgente):
                async for testo in sorgente:
                    # La sintesi: qui JARVIS non si sente ancora.
                    await asyncio.sleep(0.05)
                    visto_prima.append(pipeline._sta_parlando)
                    yield type("C", (), {"pcm": b"\x01\x02" * 160,
                                         "sample_rate": 16_000})()

            async def interrupt(self):
                return

        from tests.conftest import AudioFinto as _Audio

        s = Scelta(provider=_TtsLento(), primario=True, motivo="", annuncio=None)
        pipeline = VoicePipeline(audio=_Audio(), wake=None, stt=s, tts=s)

        async def una():
            yield "prova"

        await pipeline.parla(una())
        assert visto_prima == [False], (
            "durante la sintesi JARVIS risultava gia' parlante: il barge-in "
            "poteva scattare contro il silenzio, e scattava"
        )


class TestInterrompereNonChiedeIlPermesso:
    """`EdgeTTS.interrupt()` deve **uccidere** il decodificatore, non sperare
    che il ciclo legga una bandiera fra due letture che non tornano."""

    async def test_uccide_il_decodificatore(self) -> None:
        t = EdgeTTS()
        proc = await asyncio.create_subprocess_exec(
            "sleep", "30", stdout=asyncio.subprocess.DEVNULL)
        t._decodifica = proc
        try:
            await asyncio.wait_for(t.interrupt(), timeout=2)
            await asyncio.wait_for(proc.wait(), timeout=2)
        except asyncio.TimeoutError:                     # pragma: no cover
            proc.kill()
            pytest.fail("interrupt() non ha ucciso il decodificatore")
        assert proc.returncode is not None
        assert t._interrotto.is_set()

    async def test_NON_aspetta_il_processo(self) -> None:
        """`await proc.wait()` qui va in stallo con la lettura pendente di
        `stream()`: misurato, `interrompi()` non tornava piu'. Interrompere
        vuol dire far smettere il suono, non riscuotere il codice d'uscita."""
        t = EdgeTTS()
        proc = await asyncio.create_subprocess_exec(
            "sleep", "30", stdout=asyncio.subprocess.DEVNULL)
        t._decodifica = proc
        t0 = time.monotonic()
        await t.interrupt()
        trascorso = (time.monotonic() - t0) * 1000
        proc.kill()
        assert trascorso < 50, f"interrupt() ha impiegato {trascorso:.0f} ms"

    async def test_senza_decodificatore_non_esplode(self) -> None:
        t = EdgeTTS()
        await t.interrupt()
        assert t._interrotto.is_set()


def _forte(ampiezza: int) -> bytes:
    """Un blocco con energia nota: onda quadra sopra la continua misurata."""
    return _blocco([CONTINUA + (ampiezza if i % 2 else -ampiezza)
                    for i in range(320)])


class TestUnColpoSoloNonInterrompe:
    """Il barge-in scattava su **un blocco da 20 ms**, e il risultato era che
    JARVIS interrompeva se stesso.

    Misurato su 90 s di eco della propria voce, con lo stesso audio dato a due
    VAD in parallelo:

        PRIMA (un blocco sopra 0,012):  787 blocchi avrebbero interrotto
        DOPO  (5 blocchi sopra 0,030):  0 interruzioni

    E il controllo che rende attribuibile il numero: 90 s di stanza con JARVIS
    zitto danno **0 blocchi** sopra 0,012, quindi quelle raffiche erano tutte
    eco e non rumore ambientale.
    """

    def test_un_blocco_forte_NON_basta(self) -> None:
        v = VAD()
        assert v.parla(_forte(20_000))
        assert not v.sostenuto, "un colpo isolato interrompe ancora JARVIS"

    def test_N_blocchi_di_fila_bastano(self) -> None:
        v = VAD()
        for i in range(BLOCCHI_BARGE_IN - 1):
            v.parla(_forte(20_000))
            assert not v.sostenuto, f"ha interrotto al blocco {i + 1}"
        v.parla(_forte(20_000))
        assert v.sostenuto

    def test_una_pausa_AZZERA_il_conto(self) -> None:
        """Quattro colpi, una pausa, quattro colpi: non fanno otto."""
        v = VAD()
        for _ in range(BLOCCHI_BARGE_IN - 1):
            v.parla(_forte(20_000))
        v.parla(_blocco([CONTINUA] * 320))            # silenzio
        assert v.consecutivi == 0
        for _ in range(BLOCCHI_BARGE_IN - 1):
            v.parla(_forte(20_000))
        assert not v.sostenuto

    def test_i_DUE_gate_sono_diversi(self) -> None:
        """Un suono che apre l'ascolto (0,012) ma non arriva alla soglia del
        barge-in (0,030) non deve interrompere: e' esattamente la fascia in
        cui vive l'eco, p99 = 0,01281."""
        v = VAD()
        medio = _forte(700)                            # fra le due soglie
        e = VAD.energia(medio)
        assert 0.012 <= e < SOGLIA_BARGE_IN, f"il blocco di prova vale {e:.5f}"
        for _ in range(BLOCCHI_BARGE_IN * 3):
            assert v.parla(medio), "l'ascolto deve comunque aprirsi"
        assert not v.sostenuto, (
            "l'eco a p99 interrompe ancora: e' il caso che ha tagliato tutti "
            "gli annunci"
        )

    def test_dopo_un_barge_in_il_conto_riparte(self) -> None:
        v = VAD()
        for _ in range(BLOCCHI_BARGE_IN):
            v.parla(_forte(20_000))
        assert v.sostenuto
        v.ricomincia_a_contare()
        assert not v.sostenuto and v.consecutivi == 0


class TestIlVadConsumaUnBloccoUnaVoltaSOLA:
    """Sul ramo in cui JARVIS parla, `parla()` veniva chiamato due volte sullo
    stesso blocco: il contatore del silenzio correva al doppio della velocita'
    esattamente mentre JARVIS parlava."""

    async def test_una_chiamata_per_blocco(self, monkeypatch) -> None:
        chiamate = []
        vero = VAD.parla

        def contando(self, pcm):
            chiamate.append(1)
            return vero(self, pcm)

        monkeypatch.setattr(VAD, "parla", contando)

        blocchi = 7

        class _Audio:
            def input_stream(self, sample_rate=None):
                async def gen():
                    for _ in range(blocchi):
                        yield b"\x00\x30\x00\xd0" * 160
                return gen()

            async def play(self, *_a, **_k):
                return

            async def interrupt(self):
                return

        class _Tts:
            name = "finto"
            per_enunciato = False

            async def stream(self, sorgente):
                async for _ in sorgente:
                    pass
                return
                yield                                    # pragma: no cover

            async def interrupt(self):
                return

        s = Scelta(provider=_Tts(), primario=True, motivo="", annuncio=None)

        class _WakeMuto:
            frasi = ()

            def feed(self, _pcm):
                return None

        p = VoicePipeline(audio=_Audio(), wake=_WakeMuto(), stt=s, tts=s)
        p._sta_parlando = True                        # il ramo che sbagliava
        await asyncio.wait_for(p.run(), timeout=5)
        assert len(chiamate) == blocchi, (
            f"{len(chiamate)} chiamate per {blocchi} blocchi: l'isteresi "
            "avanza piu' in fretta di quanto passi il tempo"
        )
