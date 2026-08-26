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


class _AudioFinto:
    """Un dispositivo che non esiste: silenzio in ingresso, niente in uscita."""

    def input_stream(self, sample_rate=None):
        async def gen():
            while True:
                await asyncio.sleep(0.01)
                yield b"\x00" * 640
        return gen()

    async def play(self, *_a, **_k) -> None:
        return

    async def interrupt(self) -> None:
        return


@pytest.fixture
def motore_a_voce_accesa(short_paths, monkeypatch):
    """Un Engine con `voice.enabled = true`, e tre cose vere sostituite.

    ⚠️ **Che cosa si sostituisce, e che cosa no.** Si sostituiscono i tre
    TRASPORTI — il processo `claude`, il dispositivo audio, la rete di EdgeTTS
    — e **non** la logica che li sceglie: `costruisci_stt` e `costruisci_tts`
    restano quelli veri, quindi i test sul ripiego provano la decisione vera.

    Senza questo, e sono due difetti trovati collegando l'annuncio a voce:

    * i test **aprivano il microfono vero** (`pw-record` a ogni caso), e si
      vedeva solo come un `PytestUnraisableExceptionWarning` su un FileIO;
    * con l'annuncio collegato alla voce, i test **chiamavano la rete** —
      EdgeTTS e' un servizio Microsoft — e la suite passava da 2 s a **62**,
      cioe' due volte il tetto di `TETTO_ANNUNCIO_S`.

    Una suite che tocca la rete non e' una suite: e' un'altra cosa che puo'
    fallire per ragioni che non riguardano il codice.
    """
    import core.llm.claude_t1 as mod_t1
    import core.engine as mod_engine
    from core.providers.tts_local import EdgeTTS

    dette: list[str] = []

    async def _muto(self, sorgente):
        async for testo in sorgente:
            dette.append(testo)
        return
        yield                                            # pragma: no cover

    monkeypatch.setattr(mod_t1, "ClaudeT1", _T1Finto)
    monkeypatch.setattr(mod_engine, "platform_audio", _AudioFinto)
    monkeypatch.setattr(EdgeTTS, "stream", _muto)
    e = Engine(short_paths)
    e._store.current.voice.enabled = True
    #: Cio' che e' arrivato all'altoparlante. Non e' un dettaglio di comodo:
    #: e' l'unica differenza osservabile fra «annunciato» e «scritto in un
    #: log che nessuno guarda», che e' la domanda dell'invariante 12.
    e.dette_in_prova = dette
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
        # Il microfono si apre solo dentro l'ambiente di JARVIS: senza
        # questa riga il ciclo resta sospeso e non apre `pw-record`,
        # quindi non c'e' niente da far cadere.
        e._scrivanie_cambiate(1)
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
            self, motore_a_voce_accesa) -> None:
        """L'altra meta': uno stato che dice «caduto» sempre non e' uno stato."""
        e = motore_a_voce_accesa
        await e._gradi()
        # Il microfono si apre solo dentro l'ambiente di JARVIS: senza
        # questa riga il ciclo resta sospeso e non apre `pw-record`,
        # quindi non c'e' niente da far cadere.
        e._scrivanie_cambiate(1)
        try:
            for _ in range(5):
                await asyncio.sleep(0)
            assert e.state_snapshot()["voce"]["microfono"] == "aperto"
        finally:
            await e._spegni_gradi()

    async def test_senza_scrivania_dice_SOSPESO_non_muto(
            self, motore_a_voce_accesa) -> None:
        """⚠️ Un microfono chiuso APPOSTA non è un microfono muto.

        Chiamarlo «muto da 40 s» sarebbe un allarme per una cosa voluta, e un
        allarme che suona quando tutto va bene è il modo più rapido di far
        ignorare gli allarmi — lo stesso motivo per cui il battito non conta
        durante un turno.
        """
        e = motore_a_voce_accesa
        await e._gradi()
        try:
            for _ in range(5):
                await asyncio.sleep(0)
            assert e.state_snapshot()["voce"]["microfono"] == "sospeso: nessuna scrivania"
        finally:
            await e._spegni_gradi()

    async def test_quando_la_scrivania_arriva_torna_APERTO(
            self, motore_a_voce_accesa) -> None:
        e = motore_a_voce_accesa
        await e._gradi()
        try:
            e._scrivanie_cambiate(1)
            for _ in range(10):
                await asyncio.sleep(0)
            assert e.state_snapshot()["voce"]["microfono"] == "aperto"
            e._scrivanie_cambiate(0)
            for _ in range(10):
                await asyncio.sleep(0)
            assert e.state_snapshot()["voce"]["microfono"].startswith("sospeso")
        finally:
            await e._spegni_gradi()

    async def test_a_voce_spenta_e_SPENTO_non_caduto(self, short_paths) -> None:
        e = Engine(short_paths)
        e._store.current.voice.enabled = False
        await e._gradi()
        assert e.state_snapshot()["voce"]["microfono"] == "spento"

    async def test_lo_spegnimento_non_e_una_caduta(
            self, motore_a_voce_accesa) -> None:
        """`_spegni_gradi()` annulla il compito, e un annullamento non e' un
        guasto: segnarlo come caduta riempirebbe i log di allarmi a ogni
        chiusura, e il primo allarme vero passerebbe inosservato."""
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


class TestLAnnuncioSiSENTE:
    """Invariante 12: «il fallback va sempre ANNUNCIATO, mai silenzioso».

    Fino a ieri l'annuncio era **una riga di log**. Se nessuno guarda il
    terminale, non e' un annuncio: e' un annuncio archiviato. Adesso la frase
    passa da `VoicePipeline.annuncia()`, che non tocca nessun modello — se
    dipendesse da Claude, l'annuncio che Claude non risponde sarebbe la prima
    cosa a non funzionare.
    """

    async def test_la_frase_arriva_all_ALTOPARLANTE(
            self, motore_a_voce_accesa) -> None:
        from pydantic import SecretStr

        e = motore_a_voce_accesa
        e._store.current.secrets.deepgram_api_key = SecretStr("")
        await e._gradi()
        try:
            for _ in range(30):
                await asyncio.sleep(0.01)
                if len(e.dette_in_prova) >= 2:
                    break
            assert len(e.dette_in_prova) == 2, (
                f"detto all'altoparlante: {e.dette_in_prova}. I ripieghi sono "
                "due — ascolto locale e voce di ripiego — e vanno DETTI"
            )
            assert all("chiave" in d for d in e.dette_in_prova), e.dette_in_prova
        finally:
            await e._spegni_gradi()

    async def test_una_voce_che_NON_parte_non_chiude_il_microfono(
            self, motore_a_voce_accesa, monkeypatch) -> None:
        """La beffa esatta da evitare: collegare l'annuncio del ripiego e
        chiudere l'ascolto. `annuncia_ripieghi()` gira all'INIZIO di `run()`,
        fuori dalla rete che protegge i turni, e EdgeTTS e' di rete."""
        from pydantic import SecretStr

        from core.providers.tts_local import EdgeTTS

        async def _rotto(self, sorgente):
            raise RuntimeError("EdgeTTS: rete assente")
            yield                                        # pragma: no cover

        monkeypatch.setattr(EdgeTTS, "stream", _rotto)
        e = motore_a_voce_accesa
        e._store.current.secrets.deepgram_api_key = SecretStr("")
        await e._gradi()
        # Il microfono si apre solo dentro l'ambiente di JARVIS: senza
        # questa riga il ciclo resta sospeso e non apre `pw-record`,
        # quindi non c'e' niente da far cadere.
        e._scrivanie_cambiate(1)
        try:
            for _ in range(30):
                await asyncio.sleep(0.01)
            assert e.state_snapshot()["voce"]["microfono"] == "aperto", (
                "l'annuncio che non parte ha chiuso il microfono: e' la beffa "
                "esatta che questo collegamento doveva evitare"
            )
            assert e._voce_caduta is None
        finally:
            await e._spegni_gradi()

    async def test_T1_annuncia_PRIMA_che_la_voce_esista(
            self, motore_a_voce_accesa) -> None:
        """`ClaudeT1.start()` puo' annunciare mentre la pipeline non c'e'
        ancora, e `claude_t1.py` non logga da se': senza la riga di log quel
        ripiego sarebbe muto due volte."""
        from structlog.testing import capture_logs

        e = motore_a_voce_accesa
        assert e._voce is None
        with capture_logs() as righe:
            e._annuncia_a_voce("Signore, la sessione e' scaduta.", registra=True)
        annunci = [r for r in righe if r.get("event") == "ripiego_annunciato"]
        assert len(annunci) == 1, righe
        assert annunci[0]["detto"] is False, (
            "dice di averlo detto e non c'e' nessuno che possa dirlo"
        )


class TestLeFrasiCambianoSENZA_RIAVVIO:
    """`PhraseWake.set_frasi()` esisteva dalla Fase 3 e non aveva un solo
    chiamante: la ricarica a caldo di `settings.toml` funzionava e al wake non
    arrivava. Cambiare una frase voleva dire riavviare il core — la sesta
    volta, in due giorni, di due pezzi scritti, provati e mai congiunti.
    """

    async def test_scrivere_una_frase_la_APPLICA(self, motore_a_voce_accesa) -> None:
        from core.settings import WakePhrase

        e = motore_a_voce_accesa
        await e._gradi()
        try:
            assert "papa e a casa" in e._voce._wake.frasi
            nuove = e._store.current.model_copy(deep=True)
            nuove.voice.wake.phrases = [
                WakePhrase(say="jarvis", action="listen"),
                WakePhrase(say="buonasera jarvis", action="scene:avvio"),
            ]
            e._ricarica_frasi(e._voce._wake, nuove)
            assert set(e._voce._wake.frasi) == {"jarvis", "buonasera jarvis"}
        finally:
            await e._spegni_gradi()

    async def test_si_RIMBALZA_sul_loop_e_non_si_chiama_dal_thread(self) -> None:
        """⚠️ La parte che non si vede guardando lo schermo.

        `SettingsStore.reload()` gira sul thread di watchdog, e `set_frasi()`
        ricostruisce il `KaldiRecognizer` che `feed()` sta usando: chiamarlo di
        là sarebbe una corsa su `self._rec` — il riconoscitore sostituito a
        metà di un blocco, senza che niente sollevi.
        """
        from pathlib import Path

        sorgente = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
                    ).read_text(encoding="utf-8")
        i = sorgente.index("self._disiscrivi_frasi = self._store.subscribe(")
        blocco = sorgente[i:i + 260]
        assert "call_soon_threadsafe" in blocco, (
            "il listener chiama `set_frasi` dal thread di watchdog: e' una "
            "corsa sul riconoscitore che il ciclo sta usando"
        )

    async def test_una_frase_STORTA_non_spegne_il_microfono(
            self, motore_a_voce_accesa) -> None:
        """Un `settings.toml` sbagliato non deve rendere JARVIS sordo: ciò che
        c'era continua a valere."""
        e = motore_a_voce_accesa
        await e._gradi()
        # Il microfono si apre solo dentro l'ambiente di JARVIS: senza
        # questa riga il ciclo resta sospeso e non apre `pw-record`,
        # quindi non c'e' niente da far cadere.
        e._scrivanie_cambiate(1)
        try:
            prima = set(e._voce._wake.frasi)
            e._ricarica_frasi(e._voce._wake, object())    # non ha `.voice`
            assert set(e._voce._wake.frasi) == prima
            assert e.state_snapshot()["voce"]["microfono"] == "aperto"
        finally:
            await e._spegni_gradi()

    async def test_lo_spegnimento_SI_DISISCRIVE(self, motore_a_voce_accesa) -> None:
        """Un cambio che arrivasse dopo troverebbe un riconoscitore che non
        c'è più."""
        e = motore_a_voce_accesa
        await e._gradi()
        assert e._disiscrivi_frasi is not None
        await e._spegni_gradi()
        assert e._disiscrivi_frasi is None
