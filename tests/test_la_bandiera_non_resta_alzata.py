"""«JARVIS sta parlando» poteva restare vero per il resto della sessione.

## Il difetto

`VoicePipeline._sta_parlando` è l'unico produttore del campo `sta_parlando` di
§15, e si abbassa in due posti. In entrambi l'abbassamento stava **dopo** un
`await`, in sequenza e non in un `finally` suo:

    parla()       await uscita.chiudi()   →  self._sta_parlando = False
    interrompi()  await ...interrupt()    →  self._sta_parlando = False

`chiudi()` attende che la coda del dispositivo si svuoti — è `await proc.wait()`
su `pw-play`. In quella finestra bastano un `cancel()` (`_ferma_il_turno`,
`stop()`) o un errore di riproduzione perché la riga di sotto non venga mai
eseguita. Misurato:

    annullato dentro chiudi()   sta_parlando=True   lucchetto_preso=False
    chiudi() SOLLEVA            sta_parlando=True   lucchetto_preso=False

Il lucchetto della voce è già libero: il turno è morto, e la bandiera è rimasta
alzata. Da lì `Engine._voce_sta_parlando` la legge a ogni giro dei feed, e §15
regola 2 risponde «sta parlando» — **nessuna card passa più, mai**.

## Perché non lo vede nessuno

⚠️ `MotoreNews.conoscibilita()`, scritta ieri proprio per rendere leggibile un
gate che non lascia passare niente, in questo caso dichiara i tre campi `noto`.
E ha ragione: il produttore c'è, non ha sollevato, ha risposto un `bool`. **Il
campo dice un fatto, e il fatto è falso.** Quello strumento vede un produttore
che manca o che è rotto; non vede un produttore che mente. Per questo la
garanzia deve stare nel codice e non nell'osservabilità.

## E in `interrompi()` è la stessa specie nel posto peggiore

Il barge-in è l'istante in cui il Signore ha parlato **sopra** a JARVIS.
`TTSDeepgram.interrupt()` fa un `ws.send`, e un websocket caduto solleva: le tre
righe di stato sparivano tutte e tre. Misurato: `sta_parlando=True` dopo un
`interrompi()` fallito.
"""

from __future__ import annotations

import asyncio

import pytest

from core.providers.health import Scelta
from core.voice.pipeline import VoicePipeline

from tests.conftest import AudioFinto


class _Tts:
    """Un TTS che produce un blocco solo: serve ad alzare la bandiera."""

    name = "finto"
    per_enunciato = False

    async def stream(self, sorgente):
        async for _ in sorgente:
            yield type("C", (), {"pcm": b"\x01\x02" * 160, "sample_rate": 16_000})()

    async def interrupt(self) -> None:
        return


async def _una():
    yield "prova"


def _pipeline(audio) -> VoicePipeline:
    s = Scelta(provider=_Tts(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=audio, wake=None, stt=s, tts=s)


# ⚠️ Le uscite finte «lente» e «rotte» stanno QUI e non in `tests/conftest.py`.
# Il finto condiviso non deve imparare a mentire: un `AudioFinto` che chiude
# senza attendere è giusto per tutti gli altri test, ed è proprio la ragione per
# cui nessuno di loro poteva trovare questo difetto.


class _UscitaLenta:
    """Come `_Uscita`: `chiudi()` attende che la coda si svuoti."""

    aperta = True

    async def scrivi(self, pcm: bytes) -> None:
        return

    async def chiudi(self) -> None:
        await asyncio.sleep(5.0)                      # `await proc.wait()`


class _UscitaRotta(_UscitaLenta):
    async def chiudi(self) -> None:
        raise OSError("pw-play sparito mentre si chiudeva")


class _Audio(AudioFinto):
    def __init__(self, uscita) -> None:
        super().__init__()
        self._classe = uscita

    async def apri_uscita(self, sample_rate: int = 16_000):
        u = self._classe()
        self.uscite.append(u)
        return u


class TestLaBandieraSiAbbassaSEMPRE:
    """`sta_parlando` è l'unico produttore del campo di §15: se resta alzata
    per sbaglio, il gate è chiuso per sempre e nessuno può vederlo."""

    async def test_un_ANNULLAMENTO_dentro_chiudi_non_la_lascia_alzata(self) -> None:
        """La via d'ingresso vera: `_ferma_il_turno(annulla=True)` e `stop()`
        annullano il compito del turno, e possono farlo mentre la coda del
        dispositivo si sta svuotando."""
        p = _pipeline(_Audio(_UscitaLenta))
        t = asyncio.create_task(p.parla(_una()))
        await asyncio.sleep(0.15)
        assert p.sta_parlando is True, (
            "la misura non è dentro la finestra: senza la bandiera alzata "
            "questo test non prova niente"
        )

        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        assert p.sta_parlando is False, (
            "la bandiera è rimasta alzata dopo un turno morto: §15 regola 2 "
            "risponderà «sta parlando» per il resto della sessione"
        )
        assert p._voce_libera.locked() is False, (
            "il lucchetto è ancora preso: allora il turno non è morto e questo "
            "test sta misurando un'altra cosa"
        )

    async def test_un_ERRORE_di_chiusura_non_la_lascia_alzata(self) -> None:
        """Non solo l'annullamento. `_Uscita.chiudi()` cattura `BrokenPipeError`
        e `ConnectionResetError` e nient'altro: un `OSError` diverso passa.

        ⚠️ Distingue dal test sopra il caso NON annullamento, e impedisce che
        qualcuno «risolva» catturando il solo `CancelledError`.
        """
        p = _pipeline(_Audio(_UscitaRotta))
        with pytest.raises(OSError):
            await p.parla(_una())
        assert p.sta_parlando is False

    async def test_e_l_eccezione_ARRIVA_lo_stesso_a_chi_la_deve_vedere(self) -> None:
        """⚠️ La cura più pigra — ingoiare l'eccezione — passerebbe i due test
        sopra e trasformerebbe un guasto della riproduzione in silenzio.

        `parla()` gira dentro il ciclo del microfono: un errore che sparisce lì
        è un altoparlante rotto di cui non si accorge nessuno.
        """
        p = _pipeline(_Audio(_UscitaRotta))
        with pytest.raises(OSError, match="pw-play sparito"):
            await p.parla(_una())

    async def test_nel_BARGE_IN_e_lo_stesso_e_conta_di_piu(self) -> None:
        """L'istante in cui il Signore ha parlato SOPRA a JARVIS.

        `TTSDeepgram.interrupt()` fa un `ws.send`: un websocket caduto solleva,
        e le tre righe di stato stavano tutte dopo quell'`await`.
        """
        class _TtsRotto:
            name = "finto"
            per_enunciato = False

            async def stream(self, sorgente):
                if False:                                   # pragma: no cover
                    yield

            async def interrupt(self) -> None:
                raise ConnectionResetError("il websocket è caduto")

        s = Scelta(provider=_TtsRotto(), primario=True, motivo="", annuncio=None)
        p = VoicePipeline(audio=AudioFinto(), wake=None, stt=s, tts=s)
        p._sta_parlando = True

        with pytest.raises(ConnectionResetError):
            await p.interrompi()

        assert p.sta_parlando is False, (
            "dopo un barge-in fallito JARVIS risulta ancora parlante: è il "
            "momento peggiore in cui quel campo possa mentire"
        )
        assert p._interrotto is True, (
            "il barge-in è AVVENUTO comunque: il Signore ha parlato, e che il "
            "provider non l'abbia confermato è un'altra cosa"
        )


class TestPerchePoiNonLoVEDENESSUNO:
    """⚠️ Il limite dichiarato dello strumento scritto ieri.

    `conoscibilita()` distingue un produttore che manca da uno che è rotto. Un
    produttore che **mente** è `noto` come qualunque altro — e deve esserlo:
    dire il contrario vorrebbe dire un secondo produttore che controlla il
    primo. È la ragione per cui la garanzia sta nel `finally` e non nello stato.
    """

    def test_una_bandiera_incastrata_e_indistinguibile_da_una_vera(self) -> None:
        from core.news.conoscibilita import NOTO, Lettura, Sguardo, guarda

        class _Incastrata:
            sta_parlando = True          # la bandiera rimasta alzata
            frase_in_corso = False       # e nessun turno in volo: è morto

        lettura = Lettura({
            "sta_parlando": guarda(lambda: _Incastrata.sta_parlando),
            "frase_in_corso": guarda(lambda: _Incastrata.frase_in_corso),
            "pannello_a_schermo_intero": Sguardo(False, NOTO),
        })
        assert set(lettura.conoscibilita().values()) == {NOTO}
        assert lettura.contesto().motivo_del_no() == "sta parlando"
