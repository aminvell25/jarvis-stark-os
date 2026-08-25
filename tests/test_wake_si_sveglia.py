"""Dire «jarvis» sveglia JARVIS.

## Il difetto, e perche' nessuno lo aveva visto

Il ciclo di `pipeline.py` dava a Vosk solo i blocchi che il gate d'ascolto
giudicava parlato:

    if not parlato:
        continue                      # silenzio: Vosk non si sveglia

Ma **Kaldi chiude un enunciato quando sente il silenzio**, ed e' esattamente
quello che quella riga gli toglieva. Il riconoscitore restava a meta' di una
frase che non finiva mai.

Misurato sullo stesso audio sintetico, «Jarvis.»:

    audio intero, silenzio compreso              trigger: 'jarvis'
    solo i blocchi che il VAD lascia passare     NESSUN trigger

Nutrirlo di silenzio dopo la chiusura del gate funziona, ma serve tanto
silenzio: su quattro frasi, K=25 blocchi non basta e K=40 si' — **800 ms**
appesi a un dettaglio interno di Kaldi, che cambia col modello. Chiedere il
finale quando il gate si chiude e' deterministico, e la frase si riconosce
240 ms dopo che si e' smesso di parlare invece che dopo 800.

Il guasto era **invisibile**: nessuna eccezione, nessun log, e nessuno gli
aveva mai parlato. La catena era stata provata su blocchi, latenze e assenza
di falsi trigger — tutto vero, e nessuna di quelle misure poteva scoprirlo.
Serviva una frase.
"""

from __future__ import annotations

import array
import asyncio

from core.providers.health import Scelta
from core.voice.pipeline import VoicePipeline


def _rumoroso(n: int = 320) -> bytes:
    """Un blocco che il VAD giudica parlato."""
    return array.array("h", [12_000 if i % 2 else -12_000
                             for i in range(n)]).tobytes()


def _silenzio(n: int = 320) -> bytes:
    return array.array("h", [0] * n).tobytes()


class _WakeContato:
    """Registra come il ciclo lo interroga: blocchi nutriti e chiusure."""

    frasi = ("jarvis",)

    class _T:
        frase = "jarvis"
        azione = "scene:welcome_home"
        latenza_ms = 0.1

    def __init__(self, chiude_con_trigger: bool = True) -> None:
        self.nutriti = 0
        self.chiusure = 0
        self._con_trigger = chiude_con_trigger

    def feed(self, _pcm):
        self.nutriti += 1
        return None                     # come Vosk a meta' di un enunciato

    def chiudi(self):
        self.chiusure += 1
        return self._T() if self._con_trigger else None


def _pipeline(blocchi, wake, azioni):
    class _Audio:
        def input_stream(self, sample_rate=None):
            async def gen():
                for b in blocchi:
                    yield b
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
            yield                                        # pragma: no cover

        async def interrupt(self):
            return

    s = Scelta(provider=_Tts(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=_Audio(), wake=wake, stt=s, tts=s,
                         su_azione=lambda a, args: azioni.append(a))


class TestIlGateCHIUDElEnunciato:
    async def test_alla_chiusura_del_gate_si_chiede_il_finale(self) -> None:
        """Il difetto alla lettera: prima il silenzio faceva `continue` e
        nessuno diceva mai a Vosk che la frase era finita."""
        wake = _WakeContato()
        azioni: list[str] = []
        # parlato, poi abbastanza silenzio da far chiudere il gate
        blocchi = [_rumoroso()] * 10 + [_silenzio()] * 30
        await asyncio.wait_for(_pipeline(blocchi, wake, azioni).run(), timeout=5)

        assert wake.chiusure >= 1, (
            "nessuna chiusura: Vosk resta a meta' di una frase che non "
            "finisce mai, e dire «jarvis» non fa niente"
        )
        assert azioni == ["scene:welcome_home"], azioni

    async def test_il_silenzio_PURO_non_chiude_niente(self) -> None:
        """L'altra meta': senza che il gate si sia mai aperto non c'e' nessun
        enunciato da chiudere, e chiedere il finale a ogni blocco di silenzio
        sarebbe lavoro inutile a 50 Hz per sempre."""
        wake = _WakeContato()
        azioni: list[str] = []
        await asyncio.wait_for(
            _pipeline([_silenzio()] * 40, wake, azioni).run(), timeout=5)
        assert wake.chiusure == 0 and wake.nutriti == 0

    async def test_si_chiude_UNA_volta_sola_per_enunciato(self) -> None:
        """Trenta blocchi di silenzio dopo una frase sono un enunciato solo."""
        wake = _WakeContato(False)
        azioni: list[str] = []
        blocchi = [_rumoroso()] * 10 + [_silenzio()] * 30
        await asyncio.wait_for(_pipeline(blocchi, wake, azioni).run(), timeout=5)
        assert wake.chiusure == 1, f"{wake.chiusure} chiusure per una frase"

    async def test_due_frasi_fanno_DUE_chiusure(self) -> None:
        wake = _WakeContato(False)
        azioni: list[str] = []
        blocchi = ([_rumoroso()] * 10 + [_silenzio()] * 30) * 2
        await asyncio.wait_for(_pipeline(blocchi, wake, azioni).run(), timeout=5)
        assert wake.chiusure == 2, f"{wake.chiusure} chiusure per due frasi"

    async def test_il_parlato_arriva_ancora_a_Vosk(self) -> None:
        """La meta' che conta di piu': non rompere il caso buono."""
        wake = _WakeContato(False)
        azioni: list[str] = []
        await asyncio.wait_for(
            _pipeline([_rumoroso()] * 12, wake, azioni).run(), timeout=5)
        assert wake.nutriti == 12


class TestConIlRiconoscitoreVERO:
    """La prova che avrebbe scoperto il difetto il primo giorno.

    Tutto cio' che sta sopra gira su un finto, e un finto non sa che Kaldi
    vuole il silenzio: e' proprio la specie di prova che era gia' stata
    scritta — blocchi, latenze, nessun falso trigger — e che non poteva
    scoprire niente. Serviva una frase.

    ⚠️ **Provenienza dell'audio, e conta.** `tests/fixtures/wake-jarvis.pcm.gz`
    e' la parola «Jarvis» **sintetizzata da edge-tts**, non una voce umana.
    Prova che la catena gate -> Vosk -> trigger funziona da capo a fondo; NON
    prova che riconosca Lei. Il file esiste perche' edge-tts e' di rete e
    questa prova deve girare offline.

    ⚠️ **Se il modello Vosk non c'e', questo test si SALTA**, e un test saltato
    non e' un test verde (§11.7 regola 4). Il modello non sta nel repo: 87 MiB.
    """

    def _pcm(self) -> bytes:
        import gzip
        import hashlib
        import json
        from pathlib import Path

        radice = Path(__file__).resolve().parent / "fixtures"
        pcm = gzip.decompress((radice / "wake-jarvis.pcm.gz").read_bytes())
        meta = json.loads((radice / "wake-jarvis.json").read_text(encoding="utf-8"))
        assert hashlib.sha256(pcm).hexdigest() == meta["sha256_pcm"], (
            "l'audio non e' quello registrato: l'impronta non combacia"
        )
        return pcm

    async def test_una_frase_VERA_sveglia_JARVIS(self) -> None:
        import pytest

        from core.settings import load_settings

        s = load_settings()
        modello = str(s.voice.wake.model)
        if not __import__("pathlib").Path(modello).exists():
            pytest.skip(f"modello Vosk assente: {modello} — SALTATO, non verde")

        from core.voice.wake import PhraseWake

        visti: list[str] = []
        wake = PhraseWake({f.say: f.action for f in s.voice.wake.phrases},
                          model_path=modello,
                          su_trigger=lambda t: visti.append(t.frase))
        pcm = self._pcm() + b"\x00" * 16_000      # mezzo secondo, e non un secondo
        blocchi = [pcm[i:i + 640] for i in range(0, len(pcm) - 639, 640)]
        azioni: list[str] = []
        await asyncio.wait_for(_pipeline(blocchi, wake, azioni).run(), timeout=60)

        assert visti == ["jarvis"], (
            f"trigger: {visti}. Con il gate che affama Vosk del silenzio "
            "questa lista e' vuota, ed e' il difetto per cui dire «jarvis» "
            "non faceva niente"
        )
