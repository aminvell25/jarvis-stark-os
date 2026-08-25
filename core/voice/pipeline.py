"""La catena vocale — SPEC §7.1.

    microfono (PipeWire)
      -> VAD a energia      gate piu' economico
      -> Vosk grammatica    ascolto continuo su frasi note (LOCALE, SEMPRE)
      -> match? no -> torna al VAD; NULLA LASCIA LA MACCHINA
                si' v
      -> azione diretta della frase          oppure
      -> STT -> T0 grammatica -> azione      oppure  T1 -> TTS in streaming
      -> altoparlante

**Il wake resta sempre locale** (invariante 13): mandare l'audio a un servizio
ventiquattr'ore al giorno sarebbe insostenibile per costo e per privacy. Vosk
apre il flusso, e solo dopo il match l'audio puo' andare in rete (§18.3).

**Il percorso piu' corto non tocca nulla.** Una frase come *«papa' e' a casa»*
porta la propria azione: si esegue in millisecondi, senza STT, senza LLM, senza
rete. E' la proprieta' che rende `offline` uno stato utilizzabile (§16).
"""

from __future__ import annotations

import array
import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

import structlog

from core.llm.grammar import Intent, parse
from core.voice.audio_io import dal_microfono
from core.providers.chunker import clause_chunks
from core.providers.health import Scelta

log = structlog.get_logger(__name__)


class VAD:
    """Gate a energia con isteresi.

    ⚠️ SCOSTAMENTO da §7.1, che indica **Silero VAD**: e' un altro modello da
    scaricare. Un gate a energia fa lo stesso mestiere — *non svegliare Vosk sul
    silenzio* — senza dipendenze.

    L'isteresi serve: una soglia secca aprirebbe e chiuderebbe a ogni respiro,
    tagliando le parole a meta'. Si apre in fretta e si chiude piano.
    """

    def __init__(self, soglia_apertura: float = 0.012, soglia_chiusura: float = 0.006,
                 coda_blocchi: int = 12) -> None:
        self._apre = soglia_apertura
        self._chiude = soglia_chiusura
        self._coda = coda_blocchi
        self._aperto = False
        self._silenzio = 0

    @staticmethod
    def energia(pcm: bytes) -> float:
        """RMS normalizzato 0-1."""
        if not pcm:
            return 0.0
        c = array.array("h")
        c.frombytes(pcm[: len(pcm) // 2 * 2])
        if not c:
            return 0.0
        return (sum(v * v for v in c) / len(c)) ** 0.5 / 32768.0

    def parla(self, pcm: bytes) -> bool:
        e = self.energia(pcm)
        if not self._aperto:
            if e >= self._apre:
                self._aperto, self._silenzio = True, 0
        else:
            if e < self._chiude:
                self._silenzio += 1
                if self._silenzio >= self._coda:
                    self._aperto = False
            else:
                self._silenzio = 0
        return self._aperto


@dataclass
class Turno:
    """Cosa e' successo, per la memoria e per la diagnosi."""

    frase_wake: str
    azione: str | None
    testo_utente: str = ""
    testo_detto: str = ""
    latenza_wake_ms: float = 0.0
    latenza_primo_suono_ms: float = 0.0


class VoicePipeline:
    def __init__(
        self,
        audio,
        wake,
        stt: Scelta,
        tts: Scelta,
        t1=None,
        su_azione: Callable[[str, dict], None] | None = None,
        su_annuncio: Callable[[str], None] | None = None,
        su_turno: Callable[[Turno], None] | None = None,
        rate: int = 16_000,
    ) -> None:
        self._audio = audio
        self._rate = rate
        self._wake = wake
        self._stt = stt
        self._tts = tts
        self._t1 = t1
        self._su_azione = su_azione
        self._su_annuncio = su_annuncio
        self._su_turno = su_turno
        self._vad = VAD()
        self._sta_parlando = False
        self._stop = asyncio.Event()

    # ── annunci di ripiego ───────────────────────────────────────────────────

    def annuncia_ripieghi(self) -> list[str]:
        """Le frasi da dire all'avvio se si parte in ripiego (invariante 12).

        Vengono da `Scelta`, che non permette di costruire un ripiego senza
        annuncio: qui si raccolgono, non si decidono.
        """
        frasi = [s.annuncio for s in (self._stt, self._tts) if s.annuncio]
        for f in frasi:
            log.warning("ripiego_annunciato", testo=f)
            if self._su_annuncio:
                self._su_annuncio(f)
        return frasi

    # ── ciclo principale ─────────────────────────────────────────────────────

    async def run(self) -> None:
        """Ascolta finche' non si ferma."""
        self.annuncia_ripieghi()
        log.info("pipeline_avviata", stt=self._stt.provider.name,
                 tts=self._tts.provider.name)
        # ⚠️ `dal_microfono` e non `input_stream` diretto: il flusso della
        # piattaforma NON garantisce la dimensione dei blocchi. Misurato sul
        # microfono di questa macchina, quaranta letture da 640 byte davano 640
        # solo 19 volte, e 42 byte — cioe' 1,3 ms di audio — tredici volte.
        # Il VAD ci calcolava sopra un'energia media senza significato e il
        # gate si apriva a caso, senza che niente sollevasse. Vedi
        # core/voice/audio_io.py.
        async for blocco in dal_microfono(self._audio, self._rate):
            if self._stop.is_set():
                break

            # BARGE-IN: se JARVIS sta parlando e qualcuno parla sopra, si
            # zittisce PRIMA di capire cosa e' stato detto. Aspettare il
            # riconoscimento costerebbe centinaia di millisecondi, e nel
            # frattempo continuerebbe a parlare addosso all'utente (§7.4).
            if self._sta_parlando and self._vad.parla(blocco):
                await self.interrompi()
                continue

            if not self._vad.parla(blocco):
                continue                      # silenzio: Vosk non si sveglia

            trigger = self._wake.feed(blocco)
            if trigger is None:
                continue                      # nulla lascia la macchina

            try:
                await self._su_trigger(trigger)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # ⚠️ UN TURNO CHE FALLISCE NON CHIUDE IL MICROFONO.
                #
                # Senza questo blocco l'eccezione risaliva fuori dall'`async
                # for`, `run()` finiva, e la scrivania restava SORDA per il
                # resto della sessione — senza un errore da leggere e senza
                # modo di distinguerla da un microfono muto.
                #
                # Le sorgenti non sono ipotetiche e sono tutte fuori dal
                # nostro controllo: il TTS di ripiego e' EdgeTTS, che e' di
                # RETE; T1 e' un processo esterno; `pw-play` puo' mancare.
                # Un turno perso e' un turno perso: non e' la fine
                # dell'ascolto.
                log.error("turno_caduto", errore=repr(exc),
                          frase=getattr(trigger, "frase", None),
                          conseguenza="turno perso, il microfono resta aperto")

    async def _su_trigger(self, trigger) -> None:
        # Conferma acustica: un tono, non una voce (§7.2 regola 2).
        from core.platform.linux_audio import tono

        await self._audio.play(tono())

        azione = trigger.azione
        if azione and azione != "listen":
            # IL PERCORSO CORTO. Nessuno STT, nessun LLM, nessuna rete.
            log.info("azione_diretta", frase=trigger.frase, azione=azione,
                     latenza_ms=round(trigger.latenza_ms, 2))
            if self._su_azione:
                # Una frase-wake diretta non ha argomenti: il dizionario vuoto
                # e' la stessa firma dell'altro percorso, non un caso speciale.
                self._su_azione(azione, {})
            if self._su_turno:
                self._su_turno(Turno(frase_wake=trigger.frase, azione=azione,
                                     latenza_wake_ms=trigger.latenza_ms))
            return

        await self._ascolta_e_rispondi(trigger)

    async def _ascolta_e_rispondi(self, trigger) -> None:
        """Dopo il wake: STT, poi T0, e solo se T0 non capisce, T1."""
        testo = await self._trascrivi()
        if not testo:
            return

        intent = parse(testo)
        if intent is not None:
            log.info("t0", testo=testo, tool=intent.tool, args=intent.args)
            # GLI ARGOMENTI, che fino a §13 si perdevano qui. `open_panel`
            # senza `{"panel": "globo"}` non e' un comando, e' una categoria:
            # chi lo riceveva sapeva che si voleva aprire qualcosa e non che
            # cosa. Trovato cablando la scrivania, che e' il primo consumatore
            # ad averne davvero bisogno.
            if self._su_azione:
                self._su_azione(intent.tool, dict(intent.args))
            if self._su_turno:
                self._su_turno(Turno(frase_wake=trigger.frase, azione=intent.tool,
                                     testo_utente=testo))
            return

        if self._t1 is None:
            return
        await self.parla(self._t1.ask(testo), trigger, testo)

    async def _trascrivi(self, limite_s: float = 8.0) -> str:
        """Un turno di trascrizione, fino al silenzio o al limite."""
        scadenza = time.monotonic() + limite_s
        pezzi: list[str] = []

        async def audio_limitato():
            # ⚠️ `dal_microfono` e non `input_stream` diretto, per la STESSA
            # ragione del ciclo principale — e questa meta' era rimasta
            # indietro. `audio_io.py` esiste perche' i blocchi della
            # piattaforma non hanno la dimensione che dichiarano: misurati,
            # 21 su 40 erano corti, e uno di lunghezza DISPARI spezza un
            # campione s16 fra due chiamate al riconoscitore. La correzione
            # era stata messa sul percorso del wake e non su questo, che e'
            # proprio quello che manda il testo fuori dalla macchina.
            #
            # E il rate si PASSA: `core/platform/base.py` dichiara
            # `input_stream(sample_rate)` SENZA valore predefinito. Qui
            # funzionava solo per il default dell'implementazione Linux, e su
            # Windows (invariante 29) sarebbe stato un `TypeError` al primo
            # turno — cioe' un guasto che non si vede finche' non si cambia
            # sistema operativo.
            async for b in dal_microfono(self._audio, self._rate):
                yield b
                if time.monotonic() > scadenza:
                    return

        async for t in self._stt.provider.stream(audio_limitato()):
            if t.is_final and t.text:
                pezzi.append(t.text)
                if t.end_of_turn:
                    break
        return " ".join(pezzi).strip()

    # ── voce ─────────────────────────────────────────────────────────────────

    async def parla(self, token, trigger=None, testo_utente: str = "") -> Turno:
        """Da' voce a un flusso di token.

        **Il chunker solo se serve** (§7.4): davanti a un TTS a enunciato
        aggrega, davanti a Flux lo si salta perche' aggiungerebbe solo latenza.
        La decisione la porta il provider in `per_enunciato`, non un `if`
        ricordato a memoria.
        """
        provider = self._tts.provider
        sorgente = clause_chunks(token) if provider.per_enunciato else token

        t0 = time.perf_counter()
        primo = None
        detto: list[str] = []
        self._sta_parlando = True
        try:
            async for chunk in provider.stream(sorgente):
                if primo is None:
                    primo = time.perf_counter()
                    log.info("primo_suono_ms", ms=round((primo - t0) * 1000))
                await self._audio.play(chunk.pcm, chunk.sample_rate)
        finally:
            self._sta_parlando = False

        turno = Turno(
            frase_wake=trigger.frase if trigger else "",
            azione=None,
            testo_utente=testo_utente,
            # §7.4: cio' che e' stato EFFETTIVAMENTE UDITO. Su Flux lo riporta
            # l'interruzione; in locale e' quanto abbiamo riprodotto.
            testo_detto=getattr(provider, "text_spoken", "") or "".join(detto),
            latenza_wake_ms=trigger.latenza_ms if trigger else 0.0,
            latenza_primo_suono_ms=(primo - t0) * 1000 if primo else 0.0,
        )
        if self._su_turno:
            self._su_turno(turno)
        return turno

    async def annuncia(self, frase: str) -> Turno:
        """Dice UNA frase, senza passare da nessun modello.

        ⚠️ Esisteva il chiamante e non esisteva il metodo: `core/engine.py`
        chiama `self._voce.annuncia(frase)` da `_parla_locale`, ed e' la via con
        cui §5.6 annuncia la sessione scaduta e ADR-003 annuncia l'amnesia.
        Con la voce accesa quella riga avrebbe sollevato `AttributeError`
        **proprio nel momento in cui il sistema sta gia' fallendo** — cioe' il
        guasto peggiore possibile nel posto peggiore possibile.

        Non passa da T1 e non e' una risposta: e' il sistema che parla di se'.
        Il TTS locale basta, ed e' il punto: se dipendesse da Claude, l'annuncio
        che Claude non risponde sarebbe la prima cosa a non funzionare.
        """
        async def una() -> AsyncIterator[str]:
            yield frase

        return await self.parla(una())

    async def interrompi(self) -> None:
        """Barge-in: silenzio immediato.

        Due passi, e l'ordine conta: prima si zittisce l'altoparlante — che e'
        una `kill()` e avviene in microsecondi — poi si dice al provider di
        smettere di produrre. L'inverso lascerebbe suonare cio' che e' gia' in
        coda nel dispositivo.
        """
        await self._audio.interrupt()
        await self._tts.provider.interrupt()
        self._sta_parlando = False
        log.info("barge_in")

    def stop(self) -> None:
        self._stop.set()
