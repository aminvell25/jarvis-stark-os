"""Accendere `voice.enabled` apre davvero il microfono.

## Il difetto che questi test impediscono

L'intestazione di `core/engine.py` dichiara l'avvio a gradi:

    voice.enabled       wake Vosk, STT/TTS, T1 persistente, supervisore

`_gradi()` costruiva **solo T1**. Nessun `PhraseWake`, nessuna `VoicePipeline`,
nessun dispositivo: accendere `voice.enabled` avviava un processo `claude` e
**non apriva il microfono**.

Chi avesse parlato avrebbe parlato nel vuoto — senza un errore da leggere e
senza modo di distinguere un microfono muto da un codice che non ascolta. È il
guasto che questo progetto chiama per nome da giorni: **silenzioso, e con
l'aria di funzionare**.

Lo stesso file lo aveva già trovato una volta, su un'altra riga:

> §13: la memoria di Fase 4 esisteva, era provata, e NON era registrata nella
> radice di composizione — quindi i suoi quattro tool non esistevano nel
> processo vero. Una riga mancante.

Due volte lo stesso difetto nello stesso file. Da qui in poi c'è un test.

## Perché non avvia `claude`

`ClaudeT1.start()` spawna un processo vero. Qui interessa **l'altra metà** del
grado — quella che mancava — e si sostituisce T1 con un finto: la composizione
della voce non dipende da lui, ed è proprio questa indipendenza che il primo
test verifica.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from core.engine import Engine

RADICE = Path(__file__).resolve().parent.parent


class _T1Finto:
    """Un T1 che non spawna niente."""

    vivo = True

    def __init__(self, *_a, **_k) -> None:
        self.avviato = False

    async def start(self) -> None:
        self.avviato = True

    async def stop(self) -> None:
        self.avviato = False


@pytest.fixture
def motore_a_voce_accesa(short_paths, monkeypatch):
    """Un Engine con `voice.enabled = true` e T1 sostituito."""
    import core.llm.claude_t1 as mod_t1

    monkeypatch.setattr(mod_t1, "ClaudeT1", _T1Finto)
    e = Engine(short_paths)
    e._store.current.voice.enabled = True
    return e


class TestIlGradoVoceComponeTutto:
    async def test_compone_la_PIPELINE_e_non_solo_T1(self, motore_a_voce_accesa) -> None:
        """Il difetto, alla lettera: prima qui c'era solo `_t1`."""
        e = motore_a_voce_accesa
        await e._gradi()
        try:
            assert e._voce is not None, (
                "voice.enabled = true e nessuna VoicePipeline: il microfono non "
                "si apre, e chi parla parla nel vuoto"
            )
            assert e._compito_voce is not None, (
                "la pipeline è costruita e nessuno la fa girare: `run()` non "
                "parte da sola"
            )
        finally:
            await e._spegni_gradi()

    async def test_a_voce_SPENTA_non_si_apre_niente(self, short_paths) -> None:
        """L'altra metà, e conta quanto la prima: §3.2 dice che avviare il
        servizio NON deve aprire il microfono né spawnare `claude`."""
        e = Engine(short_paths)
        e._store.current.voice.enabled = False
        await e._gradi()
        assert e._voce is None and e._compito_voce is None and e._t1 is None

    async def test_il_wake_prende_le_frasi_delle_IMPOSTAZIONI(
        self, motore_a_voce_accesa) -> None:
        """Un wake con frasi diverse da quelle scritte è un wake che risponde a
        parole che nessuno gli ha detto di ascoltare."""
        e = motore_a_voce_accesa
        attese = {f.say for f in e._store.current.voice.wake.phrases}
        await e._gradi()
        try:
            assert set(e._voce._wake.frasi) == attese
        finally:
            await e._spegni_gradi()

    async def test_lo_STT_locale_RIUSA_il_modello_del_wake(
        self, motore_a_voce_accesa) -> None:
        """`stt_local.py`: «il modello è lo stesso oggetto». Ricaricarlo costa
        284 ms misurati e 87 MiB per la stessa cosa.

        ⚠️ La chiave si TOGLIE, non si salta il test. `conftest.py` scrive una
        chiave Deepgram finta, quindi qui lo STT sarebbe il primario e questa
        proprietà non verrebbe esercitata **mai**: un criterio che si salta è
        §11.7 regola 4, e non conta come verde.
        """
        from pydantic import SecretStr

        e = motore_a_voce_accesa
        e._store.current.secrets.deepgram_api_key = SecretStr("")
        await e._gradi()
        try:
            stt = e._voce._stt.provider
            assert stt.name == "vosk", f"senza chiave lo STT è {stt.name}"
            assert stt._model is e._voce._wake.modello, (
                "lo STT locale ha caricato un secondo modello: 284 ms e 87 MiB "
                "per la stessa cosa"
            )
        finally:
            await e._spegni_gradi()

    async def test_senza_chiave_il_ripiego_si_ANNUNCIA(
        self, motore_a_voce_accesa) -> None:
        """Invariante 12: «il fallback va sempre ANNUNCIATO, mai silenzioso».
        Con la voce accesa e nessuna chiave, questo è il caso NORMALE su questa
        macchina, non un'eccezione."""
        from pydantic import SecretStr

        e = motore_a_voce_accesa
        e._store.current.secrets.deepgram_api_key = SecretStr("")
        await e._gradi()
        try:
            annunci = e._voce.annuncia_ripieghi()
            assert len(annunci) == 2, f"annunci: {annunci}"
            assert all("chiave" in a for a in annunci), annunci
        finally:
            await e._spegni_gradi()

    async def test_lo_spegnimento_ferma_la_pipeline(
        self, motore_a_voce_accesa) -> None:
        """Un compito che sopravvive al core tiene aperto il microfono dopo che
        il servizio si è fermato."""
        e = motore_a_voce_accesa
        await e._gradi()
        compito = e._compito_voce
        await e._spegni_gradi()
        assert compito.done() or compito.cancelled()


class TestAnnuncia:
    """`core/engine.py` chiamava `self._voce.annuncia(frase)` e il metodo NON
    esisteva: con la voce accesa, l'annuncio della sessione scaduta (§5.6) e
    quello dell'amnesia (ADR-003) avrebbero sollevato `AttributeError`
    **proprio mentre il sistema sta già fallendo**.
    """

    def test_il_metodo_che_il_chiamante_usa_esiste(self) -> None:
        from core.voice.pipeline import VoicePipeline

        assert hasattr(VoicePipeline, "annuncia")

    def test_il_chiamante_lo_chiama_ancora(self) -> None:
        """Se qualcuno rinominasse il metodo, il chiamante resterebbe indietro
        in silenzio: è un controllo sul sorgente, come TestR82."""
        sorgente = (RADICE / "core" / "engine.py").read_text(encoding="utf-8")
        assert re.search(r"_voce\.annuncia\(", sorgente), (
            "nessuno chiama più `annuncia`: o il nome è cambiato in un posto "
            "solo, o l'annuncio vocale di §5.6 è sparito"
        )


class TestIlTurnoSiConta:
    """ADR-004. Senza questa riga il contatore dei secondi non vedrebbe mai un
    turno, e §24.8 resterebbe aperta con un contatore che esiste e non conta."""

    def test_il_turno_arriva_al_governor(self) -> None:
        sorgente = (RADICE / "core" / "engine.py").read_text(encoding="utf-8")
        assert "registra_voce(" in sorgente, (
            "nessuno chiama registra_voce: i secondi di audio non si contano, "
            "ed è il difetto per cui ADR-004 esiste"
        )
        assert "su_turno=self._voce_su_turno" in sorgente, (
            "la pipeline non è collegata al contatore: `su_turno` resta None e "
            "il turno si perde"
        )


class TestIlMicrofonoCheMuoreLoDICE:
    """Misurato: un compito che solleva mentre qualcuno ne tiene il riferimento
    produce «Task exception was never retrieved» solo alla DISTRUZIONE
    dell'oggetto — 605,9 ms in una prova che finisce, **mai** in un core che
    gira per ore. Senza un callback, il microfono si chiude in silenzio.
    """

    async def test_la_caduta_finisce_nello_SNAPSHOT(self, motore_a_voce_accesa,
                                                    monkeypatch) -> None:
        import core.engine as mod

        class _AudioRotto:
            def input_stream(self, sample_rate=None):
                async def gen():
                    raise RuntimeError("pw-record: comando non trovato")
                    yield b""                            # pragma: no cover
                return gen()

            async def play(self, *_a, **_k):
                return

        monkeypatch.setattr(mod, "platform_audio", _AudioRotto)
        e = motore_a_voce_accesa
        await e._gradi()
        try:
            # Un giro di loop: il compito parte, solleva, e il callback scatta.
            for _ in range(5):
                await asyncio.sleep(0)
            stato = e.state_snapshot()["voce"]["microfono"]
            assert stato.startswith("caduto:"), (
                f"microfono = {stato!r}. Il compito e' morto e lo stato non lo "
                "dice: chi parla parla nel vuoto, e nei log non c'e' niente"
            )
            assert "pw-record" in stato, stato
        finally:
            await e._spegni_gradi()

    async def test_a_voce_accesa_e_tutto_a_posto_dice_APERTO(
            self, motore_a_voce_accesa, monkeypatch) -> None:
        """L'altra meta': uno stato che dice «caduto» sempre non e' uno stato."""
        import core.engine as mod

        class _AudioMuto:
            def input_stream(self, sample_rate=None):
                async def gen():
                    while True:
                        await asyncio.sleep(0.05)
                        yield b"\x00" * 640
                return gen()

            async def play(self, *_a, **_k):
                return

        monkeypatch.setattr(mod, "platform_audio", _AudioMuto)
        e = motore_a_voce_accesa
        await e._gradi()
        try:
            for _ in range(5):
                await asyncio.sleep(0)
            assert e.state_snapshot()["voce"]["microfono"] == "aperto"
        finally:
            await e._spegni_gradi()

    async def test_a_voce_spenta_e_SPENTO_non_caduto(self, short_paths) -> None:
        e = Engine(short_paths)
        e._store.current.voice.enabled = False
        await e._gradi()
        assert e.state_snapshot()["voce"]["microfono"] == "spento"

    async def test_lo_spegnimento_non_e_una_caduta(self, motore_a_voce_accesa,
                                                   monkeypatch) -> None:
        """`_spegni_gradi()` annulla il compito, e un annullamento non e' un
        guasto: segnarlo come caduta riempirebbe i log di allarmi a ogni
        chiusura, e il primo allarme vero passerebbe inosservato."""
        import core.engine as mod

        class _AudioMuto:
            def input_stream(self, sample_rate=None):
                async def gen():
                    while True:
                        await asyncio.sleep(0.05)
                        yield b"\x00" * 640
                return gen()

            async def play(self, *_a, **_k):
                return

        monkeypatch.setattr(mod, "platform_audio", _AudioMuto)
        e = motore_a_voce_accesa
        await e._gradi()
        await e._spegni_gradi()
        assert e._voce_caduta is None


class TestLeNewsNonDiconoDiEsserCollegate:
    """`Watcher.giro()` non ha un solo chiamante nel core — solo
    `tests/test_news.py` e `scripts/fixture_fusi.py`. Con `news.enabled = true`
    lo snapshot diceva `collegato: true` e nessun giro sui feed e' mai
    avvenuto: costruito e mai azionato, come i quattro tool di memoria di §13.
    """

    async def test_lo_snapshot_non_promette_notizie(self, short_paths) -> None:
        e = Engine(short_paths)
        e._store.current.news.enabled = True
        await e._gradi()
        n = e.state_snapshot()["news"]
        assert "collegato" not in n, (
            "`collegato` e' tornato: chi legge lo capisce come «le notizie "
            "arrivano», e non arrivano"
        )
        assert n["watcher_costruito"] is True
        assert n["giri_fatti"] == 0, (
            "se questo numero e' diverso da zero, qualcuno aziona finalmente "
            "il Watcher — e allora questo test va riscritto, non cancellato"
        )


class TestLAnnuncioNonSiRipete:
    """Invariante 12 chiede che il ripiego sia annunciato. Il callback che
    avevo composto ripeteva la riga che `annuncia_ripieghi()` scrive gia':
    misurato in composizione vera, **quattro righe per due ripieghi**. Chi
    legge i log conta gli annunci, e un annuncio contato doppio e' un numero
    sbagliato — la stessa specie di guasto dei due orologi e dei tre ritagli:
    una proprieta', due proprietari.
    """

    async def test_due_ripieghi_fanno_DUE_righe(self, motore_a_voce_accesa,
                                                monkeypatch) -> None:
        from pydantic import SecretStr
        from structlog.testing import capture_logs

        e = motore_a_voce_accesa
        e._store.current.secrets.deepgram_api_key = SecretStr("")
        await e._gradi()
        try:
            with capture_logs() as righe:
                frasi = e._voce.annuncia_ripieghi()
            annunci = [r for r in righe if r.get("event") == "ripiego_annunciato"]
            assert len(frasi) == 2, frasi
            assert len(annunci) == len(frasi), (
                f"{len(frasi)} ripieghi e {len(annunci)} righe di log"
            )
        finally:
            await e._spegni_gradi()
