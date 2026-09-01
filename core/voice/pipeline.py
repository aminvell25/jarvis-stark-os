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
from structlog.contextvars import bound_contextvars

from core.llm.grammar import Intent, parse, quasi_comando
from core.llm.sistema import nota_di_interruzione
from core.voice.audio_io import dal_microfono
from core.voice.spettro import bande as bande_di
from core.providers.chunker import clause_chunks
from core.providers.health import Scelta
from core.traccia import Origine, Traccia

log = structlog.get_logger(__name__)


#: Oltre quanti secondi un turno non e' «in corso» ma **appeso**.
#:
#: Non e' scelto: e' la somma dei tetti gia' dichiarati degli stadi che
#: possono stallare — la cattura (`_trascrivi(limite_s=8.0)`), la `recv` dello
#: STT (`stt_deepgram.TETTO_RECV_S = 20`), e una riga di T1
#: (`ClaudeT1.ask(timeout=90)`). Nessuno di quei numeri nasce qui.
#:
#: ⚠️ Resta fuori il tempo di PARLARE, che dipende dalla lunghezza della
#: risposta. Non e' una svista: a 150 parole al minuto — la costante di §15 —
#: centodiciotto secondi sono **295 parole**, e `config/voice-persona.md`
#: chiede «una o due frasi». Una risposta che sfora questo tetto ha gia'
#: violato la persona, e il battito che se ne accorge dice una cosa vera.
TETTO_TURNO_S = 8.0 + 20.0 + 90.0

#: Quanti blocchi CONSECUTIVI di suono forte fanno un barge-in. A 20 ms
#: l'uno, cinque sono **100 ms**: un colpo isolato non basta piu'.
#:
#: Misurato su 90 s di eco della voce di JARVIS: 43 raffiche sopra la soglia
#: d'ascolto, di cui 18 da un blocco, 9 da due, 8 da tre, 5 da quattro. Con
#: cinque ne restavano tre — 8, 19 e 23 blocchi — ed e' per quelle che serve
#: anche `SOGLIA_BARGE_IN`. Da solo, N non bastava.
BLOCCHI_BARGE_IN = 5

#: La soglia che vale SOLO mentre JARVIS parla, e non e' quella d'ascolto.
#:
#: Il gate d'ascolto deve sentire una voce da lontano, quindi apre a 0,012. Il
#: barge-in deve distinguere una voce **dall'eco della propria**, che e' un
#: problema diverso e piu' facile: l'eco e' attenuato.
#:
#: Misurato, 4500 blocchi di eco su 90 s:
#:
#:     p50 0,00214  ·  p90 0,00655  ·  p99 0,01281  ·  MAX 0,02444
#:     sopra 0,012 -> 72 blocchi        sopra 0,030 -> ZERO
#:
#: Controllo: 90 s di stanza con JARVIS zitto danno **0 blocchi** sopra 0,012.
#: Quindi le 43 raffiche erano tutte eco, e non rumore ambientale.
#:
#: ⚠️ 0,030 e' calibrato sull'eco, che e' misurato. **Quanto forte arrivi una
#: voce vera a questo microfono non e' misurato**, e se il barge-in non
#: rispondesse quando Lei parla, e' questo il numero da abbassare. Alzare il
#: volume degli altoparlanti alza anche l'eco: allora va rimisurato.
SOGLIA_BARGE_IN = 0.030


#: Un blocco su tre va allo spettro. Il core ne produce cinquanta al secondo
#: (20 ms l'uno) e l'occhio non distingue oltre i venti: calcolarli tutti
#: sarebbe tre volte il costo per un'onda identica.
PASSO_SPETTRO = 3


class VAD:
    """Gate a energia con isteresi.

    ⚠️ SCOSTAMENTO da §7.1, che indica **Silero VAD**: e' un altro modello da
    scaricare. Un gate a energia fa lo stesso mestiere — *non svegliare Vosk sul
    silenzio* — senza dipendenze.

    L'isteresi serve: una soglia secca aprirebbe e chiuderebbe a ogni respiro,
    tagliando le parole a meta'. Si apre in fretta e si chiude piano.
    """

    def __init__(self, soglia_apertura: float = 0.012, soglia_chiusura: float = 0.006,
                 coda_blocchi: int = 12,
                 soglia_barge_in: float = SOGLIA_BARGE_IN,
                 blocchi_barge_in: int = BLOCCHI_BARGE_IN) -> None:
        self._apre = soglia_apertura
        self._chiude = soglia_chiusura
        self._coda = coda_blocchi
        self._aperto = False
        self._silenzio = 0
        # Il gate dell'ascolto e quello del barge-in NON sono lo stesso gate,
        # e questo e' il punto: vedi `SOGLIA_BARGE_IN`.
        self._barge = soglia_barge_in
        self._n_barge = blocchi_barge_in
        self._consecutivi = 0

    @staticmethod
    def energia(pcm: bytes) -> float:
        """RMS della sola componente ALTERNATA, normalizzato 0-1.

        ⚠️ **La media si toglie, e non e' un raffinamento.** Prima non si
        toglieva, e il numero che ne usciva misurava la polarizzazione
        continua del convertitore invece del suono. Misurato sul microfono di
        questa macchina, stanza in quiete:

            offset continuo   -8470,5 su 32768
            RMS con la continua dentro   0,25856
            RMS senza                    0,00242
            soglia di apertura           0,01200

        Ventuno volte sopra la soglia, quindi **il 100 % dei blocchi era
        giudicato parlato** — 250 su 250 in cinque secondi di stanza vuota. Il
        gate non si chiudeva mai, e due cose ne seguivano:

        * il barge-in scattava all'istante ogni volta che JARVIS apriva bocca.
          Misurato: le due frasi di ripiego all'avvio morivano **prima del
          primo campione**, `barge_in` due volte e `primo_suono_ms = 0,0`.
          Con questo difetto JARVIS non poteva finire una frase.
        * Vosk veniva alimentato in continuazione, che e' esattamente cio' che
          §7.1 chiede a questo gate di NON fare. Invisibile, perche' Vosk
          scarta da se' l'audio che non contiene una frase nota.

        Una causa sola, due guasti, e nessuno dei due sollevava. Togliere la
        media e' un passaggio in piu' sui 320 campioni del blocco: misurato,
        **+0,0126 ms** misurati (0,0078 -> 0,0203) su un blocco che dura 20 ms.
        """
        if not pcm:
            return 0.0
        c = array.array("h")
        c.frombytes(pcm[: len(pcm) // 2 * 2])
        if not c:
            return 0.0
        media = sum(c) / len(c)
        return (sum((v - media) ** 2 for v in c) / len(c)) ** 0.5 / 32768.0

    def parla(self, pcm: bytes) -> bool:
        e = self.energia(pcm)
        # Il conteggio del barge-in avanza QUI e non in un secondo metodo:
        # cosi' esiste un solo posto che consuma il blocco, e chiamarne due
        # sarebbe far avanzare l'isteresi due volte per lo stesso blocco —
        # difetto che c'era, sul ramo in cui JARVIS sta parlando.
        self._consecutivi = self._consecutivi + 1 if e >= self._barge else 0
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

    @property
    def consecutivi(self) -> int:
        """Quanti blocchi di fila sono stati abbastanza forti. Serve ai log:
        un barge-in che non dice perche' e' scattato non si puo' tarare."""
        return self._consecutivi

    @property
    def sostenuto(self) -> bool:
        """Qualcuno sta parlando SOPRA a JARVIS — non e' JARVIS che si sente.

        Vale solo dopo `parla()`, che e' l'unico a consumare il blocco.
        """
        return self._consecutivi >= self._n_barge

    def ricomincia_a_contare(self) -> None:
        """Dopo un barge-in il conteggio riparte da zero: la coda del suono
        che ha appena interrotto non deve interrompere anche la frase dopo."""
        self._consecutivi = 0


@dataclass
class Turno:
    """Cosa e' successo, per la memoria e per la diagnosi."""

    frase_wake: str
    azione: str | None
    #: Per DOVE e' passato l'enunciato: `t0` se la grammatica l'ha riconosciuto,
    #: `t1` se e' stato delegato al modello, `nessuna` se non l'ha preso
    #: nessuno — il caso che fino a oggi spariva senza lasciare una riga.
    #:
    #: Non si deriva da `azione`: `azione is None` non distingue «delegato» da
    #: «caduto», ed e' proprio quella la differenza che si vuole leggere.
    strada: str = "t1"
    #: Il verbo imperativo con cui l'enunciato cominciava, quando la grammatica
    #: NON l'ha riconosciuto. E' un'etichetta di diagnosi, non un intento: vedi
    #: `grammar.quasi_comando`, e il 15,1 % di falsi positivi misurato li'.
    quasi_comando: str | None = None
    testo_utente: str = ""
    testo_detto: str = ""
    latenza_wake_ms: float = 0.0
    latenza_primo_suono_ms: float = 0.0
    #: ⚠️ **I due numeri che ADR-004 chiede, e che non esistevano.**
    #:
    #: `registra_voce` riceveva `latenza_wake_ms` come «secondi STT» e
    #: `latenza_primo_suono_ms` come «secondi TTS». Sono **latenze**: una
    #: sessione da 12,5 s sarebbe comparsa in `conso/` come 0,00002 s, e
    #: `latenza_wake_ms` non e' nemmeno il tempo dal parlato — e' il costo di
    #: UNA `AcceptWaveform` (`wake.py:97`).
    #:
    #: Questi sono durate di audio: byte contati sul flusso, diviso
    #: `rate * 2` (s16 mono). Sono cio' che un fornitore fattura.
    secondi_ascoltati: float = 0.0
    secondi_detti: float = 0.0
    #: §7.4. Vero quando il Signore ha parlato sopra e la voce si e' fermata.
    interrotto: bool = False
    #: Se `testo_detto` sia una MISURA (`text_spoken` del provider) o un
    #: limite superiore (il testo mandato al sintetizzatore). Non e' un
    #: dettaglio: cambia che cosa si puo' affermare al modello.
    detto_misurato: bool = False
    #: ADR-011. L'id del turno, coniato in `_turno()` e uguale per TUTTE le
    #: righe che quel turno produce — la riga di `esegui_t0`, le due di
    #: `dialogo`, quella dell'instradamento.
    #:
    #: ⚠️ **Vuoto per gli annunci, di proposito.** `annuncia()` da' voce a una
    #: frase che il sistema dice di se' — il ripiego di §12, l'amnesia di
    #: ADR-003, il resoconto al risveglio — e non ha un turno che la causi.
    #: Meglio una stringa vuota che si dichiara di un id inventato che
    #: fingerebbe un'origine.
    traccia_id: str = ""


class VoicePipeline:
    def __init__(
        self,
        audio,
        wake,
        stt: Scelta,
        tts: Scelta,
        t1=None,
        su_azione: Callable[[str, dict, Traccia], None] | None = None,
        su_annuncio: Callable[[str], None] | None = None,
        ricostruisci_tts=None,
        ascolto_consentito: bool = True,
        su_turno: Callable[[Turno], None] | None = None,
        su_spettro: Callable[[list[float], str, int], None] | None = None,
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
        #: Le bande dello spettro, per l'onda del nucleo (§11.5 Fase 3).
        #: `None` e' il caso normale: senza scrivania collegata nessuno le
        #: guarda, e calcolarle sarebbe lavoro sul percorso caldo per niente.
        self._su_spettro = su_spettro
        #: Un blocco su `PASSO_SPETTRO`. DUE contatori e non uno: i due rami —
        #: microfono e altoparlante — possono essere attivi insieme durante un
        #: barge-in, e un contatore condiviso farebbe saltare blocchi all'uno
        #: per colpa dell'altro.
        self._n_spettro_mic = 0
        self._n_spettro_tts = 0
        self._vad = VAD()
        self._sta_parlando = False
        #: I secondi di audio mandati allo STT nell'ultimo turno, in attesa
        #: di essere messi nel `Turno`. Vedi `_trascrivi`.
        self._ultimi_secondi_ascoltati = 0.0
        #: Quando il gate VAD si e' aperto, per la latenza di risveglio.
        self._gate_a = 0.0
        #: ⚠️ **Il battito.** `microfono: aperto` nello snapshot riportava
        #: l'INTENZIONE — «il grado voce e' stato acceso» — non lo stato.
        #: Il 26 agosto il ciclo e' rimasto fermo **un'ora** con `pw-record`
        #: bloccato in `anon_pipe_write` (pipe piena, nessuno legge) e lo
        #: snapshot ha continuato a dire «aperto». Chi parlava parlava nel
        #: vuoto, e l'unico modo di accorgersene e' stato dirlo a voce.
        self._ultimo_blocco = 0.0
        #: Vero mentre si sta servendo un turno. Durante un turno il ciclo
        #: principale NON legge — `_su_trigger` e' atteso dentro il `async
        #: for` — e un turno puo' durare fino al timeout di T1: senza questa
        #: bandiera il battito griderebbe al lupo a ogni conversazione.
        self._in_turno = False
        #: Quando il turno in corso e' cominciato. Serve a `muto_da`: senza,
        #: la sospensione dell'allarme non ha una fine.
        self._turno_da = 0.0
        #: Il turno in corso, che dal 27 agosto gira per conto suo invece di
        #: bloccare il ciclo audio. Se ne tiene il riferimento per fermarlo
        #: alla chiusura: un compito che nessuno attende puo' essere raccolto
        #: a meta'.
        self._compito_turno: asyncio.Task | None = None
        #: §7.4: l'interruzione appena avvenuta, e cio' che il Signore ha
        #: udito. Vive fra un turno e il successivo, ed e' l'unica cosa che
        #: attraversa quel confine.
        self._interrotto = False
        self._udito_parziale: tuple[str, bool] | None = None
        #: Come si costruisce il ripiego quando il primario cade a caldo.
        #: Arriva per funzione dalla radice di composizione: la pipeline non
        #: deve sapere che cosa sia `costruisci_tts`.
        self._ricostruisci_tts = ricostruisci_tts
        self._stop = asyncio.Event()
        #: **Il microfono si apre solo dentro l'ambiente di JARVIS.**
        #: Il core gira sotto systemd ventiquattro ore; l'app no. Senza questo
        #: cancello JARVIS ascolta e risponde anche a finestra chiusa, che non
        #: e' cio' che «un ambiente cognitivo dentro il quale JARVIS vive»
        #: vuol dire.
        #:
        #: Quando si chiude, il flusso viene **chiuso davvero** e `pw-record`
        #: termina: scartare i blocchi lasciandolo aperto terrebbe accesa la
        #: spia del microfono del sistema operativo, e la spia e' l'unica cosa
        #: che il Signore vede senza chiedere.
        #:
        #: Il valore iniziale lo decide la radice di composizione, non questa
        #: classe: qui vale `True` perche' una pipeline costruita da sola —
        #: nei test, in un banco — non deve dipendere da una scrivania.
        self._consentito = asyncio.Event()
        if ascolto_consentito:
            self._consentito.set()
        #: Se il gate d'ascolto era aperto al blocco precedente. Serve a
        #: vedere il momento in cui si CHIUDE, che e' quando Vosk va chiuso.
        self._gate_aperto = False
        #: JARVIS ha UNA voce, e due cose dette insieme non sono due cose
        #: dette: sono rumore. Misurato senza lucchetto, due `parla()`
        #: concorrenti danno `A0 B0 A1 B1 A2 B2` — i frammenti di due frasi
        #: alternati nell'altoparlante. E il `finally` del primo che finisce
        #: spegne `_sta_parlando` mentre il secondo sta ancora parlando,
        #: cioe' il barge-in smette di funzionare a meta' della seconda frase.
        #:
        #: Non e' un caso limite: su questa macchina i ripieghi annunciati
        #: all'avvio sono DUE — Vosk e EdgeTTS — quindi e' il caso normale.
        self._voce_libera = asyncio.Lock()

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
        """Ascolta finche' non si ferma, e **solo quando e' consentito**.

        Il ciclo interno possiede UN'apertura del microfono. Uscirne chiude il
        flusso, e con lui `pw-record`: e' cosi' che «non si ascolta fuori
        dall'ambiente» diventa una proprieta' del sistema operativo invece di
        una promessa del codice.

        ⚠️ **Un flusso che finisce da solo non e' una sospensione.** Se il
        ciclo interno ritorna mentre l'ascolto e' ancora consentito, il
        microfono e' morto: si esce, come faceva prima questa funzione. Senza
        questa distinzione un microfono guasto diventerebbe un ciclo infinito
        che riapre `pw-record` per sempre.
        """
        self.annuncia_ripieghi()
        log.info("pipeline_avviata", stt=self._stt.provider.name,
                 tts=self._tts.provider.name)
        # ⚠️ **Il turno non e' piu' figlio del ciclo.**
        #
        # Finche' stava dentro l'`async for`, annullare `run()` annullava anche
        # il turno: era la stessa pila. Adesso e' un compito a se', e senza
        # queste righe una pipeline annullata lascerebbe dietro un turno vivo
        # che continua a parlare con il microfono gia' chiuso.
        #
        # **E i due modi di finire non sono lo stesso.** Se veniamo annullati,
        # si annulla anche lui. Se il ciclo finisce da solo — microfono morto,
        # ascolto revocato — lo si ASPETTA: tagliare a meta' una risposta gia'
        # cominciata perche' il flusso in ingresso e' finito sarebbe peggio del
        # guasto. L'attesa e' limitata da cio' che limita il turno stesso: i
        # tetti di §7.5, e `stop()` che lo annulla comunque.
        try:
            await self._cicla()
        except BaseException:
            await self._ferma_il_turno(annulla=True)
            raise
        await self._ferma_il_turno(annulla=False)

    async def _ferma_il_turno(self, *, annulla: bool) -> None:
        t = self._compito_turno
        self._compito_turno = None
        if t is None or t.done():
            return
        if annulla:
            t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            if not annulla:
                raise
        except Exception:
            # `_turno` non solleva gia' di suo; se lo facesse, la ragione per
            # cui la pipeline si sta chiudendo conta di piu'.
            pass

    def _spettro(self, pcm: bytes, sorgente: str, rate: int) -> None:
        """Manda le bande a chi le guarda. Un blocco su `PASSO_SPETTRO`.

        ⚠️ **STA SUL PERCORSO CALDO DELLA VOCE**, ed e' la ragione delle tre
        difese:

        1. **non fa niente se nessuno guarda.** `_su_spettro` e' `None` finche'
           `engine.py` non lo aggancia, e lo aggancia solo con la voce accesa;
        2. **calcola un blocco su tre.** Misurato: 0,252 ms per blocco, cioe'
           **0,42 % di un core** a 16,7 Hz — la sonda che `PIANO-FUI-ESITO.md`
           chiedeva prima di ammettere una FFT;
        3. **non solleva mai.** Un'onda che non si disegna e' un peccato; una
           che zittisce JARVIS perche' una lista era corta e' un guasto.
        """
        if self._su_spettro is None:
            return
        if sorgente == "tts":
            self._n_spettro_tts += 1
            if self._n_spettro_tts % PASSO_SPETTRO:
                return
        else:
            self._n_spettro_mic += 1
            if self._n_spettro_mic % PASSO_SPETTRO:
                return
        try:
            self._su_spettro(bande_di(pcm, rate), sorgente, rate)
        except Exception as exc:                       # pragma: no cover
            log.debug("spettro_non_pubblicato", errore=repr(exc))

    async def _cicla(self) -> None:
        while not self._stop.is_set():
            if not self._consentito.is_set():
                log.info("ascolto_sospeso", perche="nessuna scrivania collegata")
                # Il battito non deve gridare al lupo mentre il microfono e'
                # chiuso APPOSTA: `muto_da()` legge questo.
                self._ultimo_blocco = 0.0
                await self._consentito.wait()
                continue
            await self._un_ciclo_di_ascolto()
            if not self._stop.is_set() and self._consentito.is_set():
                break

    def consenti(self, si: bool) -> None:
        """Apre o chiude il microfono. Idempotente."""
        if si == self._consentito.is_set():
            return
        log.info("ascolto_consentito" if si else "ascolto_revocato")
        self._consentito.set() if si else self._consentito.clear()

    @property
    def ascolta(self) -> bool:
        return self._consentito.is_set()

    @property
    def sta_parlando(self) -> bool:
        """Se JARVIS ha voce in uscita **adesso** — §15, regola 2.

        Esiste perche' il motore proattivo deve saperlo, e l'unico modo era
        leggere `_sta_parlando` da fuori: un campo privato letto da un altro
        modulo non e' un contratto, e' una coincidenza che regge finche'
        nessuno lo rinomina.

        ⚠️ **Vero dal primo campione che si SENTE**, non dalla richiesta al
        TTS: fra le due passa il tempo della sintesi — misurato 1161 ms con
        EdgeTTS su questa rete — e in quella finestra non c'e' ancora niente
        da interrompere. Vedi il commento dentro `parla()`. Chi legge questa
        proprieta' per decidere se interrompere legge quindi la cosa giusta:
        se e' `False` perche' la sintesi non ha ancora prodotto un campione,
        una news che passa non sta parlando sopra a nessuno.
        """
        return self._sta_parlando

    @property
    def frase_in_corso(self) -> bool:
        """Se il Signore ha una frase a meta' — §15, «mai a meta' frase».

        ⚠️ **Esiste perche' quel campo era un valore scritto a mano.**
        `Engine._contesto_news` dichiarava `frase_in_corso=False` fisso, con la
        giustificazione «il turno dell'utente e' chiuso quando il giro dei feed
        gira». Non e' vero: il giro delle news sta su un timer suo, indipendente
        dai turni, e puo' scattare mentre il Signore parla. Con quel `False` una
        delle cinque regole di §15 era spenta, e una card poteva uscire in mezzo
        a una frase.

        Sono due stati, e servono tutt'e due:

            `_gate_aperto`   il VAD ha sentito voce e l'enunciato non e' ancora
                             chiuso — sta parlando ADESSO
            `_in_turno`      ha finito di parlare e JARVIS gli sta rispondendo:
                             lo scambio e' aperto, e infilarci una notizia in
                             mezzo e' la stessa scortesia

        ⚠️ Non copre il Signore che parla senza che il VAD apra — voce bassa,
        microfono lontano. Li' resta ignoto quanto prima, e il gate non
        interrompe lo stesso perche' l'ignoto vale come divieto.
        """
        return self._gate_aperto or self._in_turno

    async def _un_ciclo_di_ascolto(self) -> None:
        """Un'apertura del microfono, dal primo blocco alla chiusura."""
        # ⚠️ `dal_microfono` e non `input_stream` diretto: il flusso della
        # piattaforma NON garantisce la dimensione dei blocchi. Misurato sul
        # microfono di questa macchina, quaranta letture da 640 byte davano 640
        # solo 19 volte, e 42 byte — cioe' 1,3 ms di audio — tredici volte.
        # Il VAD ci calcolava sopra un'energia media senza significato e il
        # gate si apriva a caso, senza che niente sollevasse. Vedi
        # core/voice/audio_io.py.
        async for blocco in dal_microfono(self._audio, self._rate):
            if self._stop.is_set() or not self._consentito.is_set():
                break

            # UN SOLO passaggio del VAD per blocco. Prima erano due sul
            # ramo in cui JARVIS parla, e il secondo faceva avanzare
            # l'isteresi una seconda volta sullo stesso blocco: il contatore
            # del silenzio correva al doppio della velocita' esattamente
            # mentre JARVIS parlava.
            self._ultimo_blocco = time.monotonic()
            parlato = self._vad.parla(blocco)

            # L'onda del nucleo, dal blocco che il VAD ha appena consumato.
            # DOPO il VAD: se questa riga sollevasse — non puo', `_spettro` non
            # solleva — il gate avrebbe gia' deciso.
            self._spettro(blocco, "mic", self._rate)

            # BARGE-IN: se JARVIS sta parlando e qualcuno parla sopra, si
            # zittisce PRIMA di capire cosa e' stato detto. Aspettare il
            # riconoscimento costerebbe centinaia di millisecondi, e nel
            # frattempo continuerebbe a parlare addosso all'utente (§7.4).
            #
            # ⚠️ `sostenuto` e non `parlato`: un blocco solo da 20 ms bastava,
            # e il risultato era che JARVIS **interrompeva se stesso**. Vedi
            # `BLOCCHI_BARGE_IN` e `SOGLIA_BARGE_IN` per i numeri misurati.
            if self._sta_parlando and self._vad.sostenuto:
                log.info("barge_in_sostenuto", blocchi=self._vad.consecutivi,
                         soglia=SOGLIA_BARGE_IN)
                await self.interrompi()
                continue

            # ⚠️ **Il ciclo continua a leggere, ma non sveglia.**
            #
            # Un turno alla volta: un secondo risveglio mentre il primo e'
            # ancora in corso non e' una richiesta nuova, e' l'eco di JARVIS
            # che rientra dal microfono. Il VAD sopra ha gia' fatto la sua
            # parte — il barge-in — e questo `continue` e' cio' che tiene la
            # voce di JARVIS fuori da Vosk.
            #
            # E soprattutto: **si legge lo stesso**. E' l'unica riga che conta
            # per la sordita' del 26 e del 27 agosto — finche' i blocchi
            # vengono consumati, `pw-record` non riempie la pipe.
            if self._in_turno:
                continue

            if parlato:
                if not self._gate_aperto:
                    # Il primo blocco con voce dentro. E' l'unico `audio_in`
                    # che abbia senso come origine della latenza di risveglio:
                    # i blocchi di silenzio prima non contengono la frase.
                    self._gate_a = time.monotonic()
                self._gate_aperto = True
                trigger = self._wake.feed(blocco)
            elif self._gate_aperto:
                # ⚠️ QUI mancava tutto, ed e' il difetto per cui dire «jarvis»
                # non faceva niente. Kaldi chiude un enunciato quando SENTE il
                # silenzio, e la riga qui sotto — `continue` sul silenzio — e'
                # precisamente quello che gli toglieva. Misurato: lo stesso
                # audio sintetico da' `jarvis` se passa intero e NIENTE se
                # passa dal gate. Vedi `PhraseWake.chiudi()`.
                self._gate_aperto = False
                trigger = self._wake.chiudi()
            else:
                continue                      # silenzio: Vosk non si sveglia

            if trigger is None:
                continue                      # nulla lascia la macchina

            # ⚠️ **UN COMPITO, non un `await`.**
            #
            # `await self._su_trigger(...)` stava DENTRO questo `async for`:
            # per tutta la durata del turno il ciclo non leggeva, `pw-record`
            # riempiva la pipe e si bloccava in `anon_pipe_write`. Con un
            # turno appeso la sordita' era permanente (27 agosto, quattro
            # minuti misurati); con un turno lungo e legittimo era temporanea
            # ma reale, e al ritorno il ciclo trovava audio stantio.
            #
            # Il tetto di `TETTO_TURNO_S` rendeva la sordita' finita. Questo la
            # toglie.
            self._in_turno = True
            self._turno_da = time.monotonic()
            self._compito_turno = asyncio.create_task(
                self._turno(self._con_apertura(trigger)))

    async def _turno(self, trigger) -> None:
        """Un turno, per conto suo. Non solleva mai verso il ciclo audio.

        ⚠️ **Qui nasce la traccia del turno vocale, e nasce UNA VOLTA SOLA**
        (ADR-011). Il punto e' questo e non `_su_trigger` perche' un wake
        produce **due** richiami verso il motore — `su_azione`, che finisce in
        `esegui_t0`, e `su_turno`, che finisce in `_annota_dialogo` e
        `_annota_instradamento` — e se ognuno coniasse il proprio id le righe
        dello stesso turno porterebbero identificatori diversi. Sarebbe una
        traccia che non ricongiunge niente: esattamente il difetto da chiudere,
        con l'aggravante di sembrare chiuso.

        `bound_contextvars` lega l'id ai LOG per la durata del turno, e li'
        soltanto: `merge_contextvars` e' gia' in testa alla catena
        (`core/log.py`), quindi `wake_trigger`, `traversata` e `t0_tool` lo
        portano senza che nessuna delle ottocento chiamate di log cambi. Nel
        dominio, invece, viaggia per parametro — vedi `core/traccia.py`.
        """
        traccia = Traccia.nuova(Origine.VOCE)
        try:
            with bound_contextvars(traccia=traccia.id, origine=str(traccia.origine)):
                await self._su_trigger(trigger, traccia)
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
        finally:
            self._in_turno = False

    def _con_apertura(self, trigger):
        """Attacca al trigger il momento in cui il gate si e' aperto.

        Il `PhraseWake` non lo sa — vede blocchi, non il gate — e la pipeline
        si': e' lei che tiene il VAD. Attaccarlo qui evita di far conoscere il
        VAD al riconoscitore.

        ⚠️ **Non solleva mai.** Siamo sul percorso della voce, e la
        strumentazione non ha il diritto di zittire JARVIS: un trigger che non
        e' un dataclass — un finto di un test, o una forma futura — torna
        com'e', senza latenza di risveglio, che e' esattamente lo zero
        riconoscibile che `latenza_risveglio_ms` dichiara.

        Trovato subito: tre test passano un trigger finto, e il primo giro ha
        dato «turno_caduto» tre volte con il microfono che restava aperto e
        nessuna azione — cioe' il guasto silenzioso, prodotto da una riga
        aggiunta per MISURARE i guasti silenziosi.
        """
        import dataclasses

        try:
            return dataclasses.replace(trigger, aperto_a=self._gate_a)
        except TypeError:
            return trigger

    async def _su_trigger(self, trigger, traccia) -> None:
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
                self._su_azione(azione, {}, traccia)
            if self._su_turno:
                self._su_turno(Turno(frase_wake=trigger.frase, azione=azione,
                                     latenza_wake_ms=trigger.latenza_ms,
                                     traccia_id=traccia.id))
            return

        await self._ascolta_e_rispondi(trigger, traccia)

    async def _ascolta_e_rispondi(self, trigger, traccia) -> None:
        """Dopo il wake: STT, poi T0, e solo se T0 non capisce, T1.

        ⚠️ **I sei segmenti di §7.5 erano tutti senza cronometro.** Adesso il
        turno emette **una riga sola** — `traversata` — con i tempi monotoni
        di ciascun passaggio, invece di righe sparse che non si possono
        rimettere in fila. Una riga per turno e' anche cio' che si puo'
        contare: N turni, N righe.
        """
        t_wake = time.monotonic()
        testo = await self._trascrivi()
        t_finale = time.monotonic()
        if not testo:
            log.info("traversata", esito="nessun testo",
                     risveglio_ms=round(trigger.latenza_risveglio_ms, 1),
                     stt_ms=round((t_finale - t_wake) * 1000, 1),
                     secondi_audio=round(self._ultimi_secondi_ascoltati, 2))
            return

        intent = parse(testo)
        t_parse = time.monotonic()
        log.info("traversata", esito="t0" if intent else "t1",
                 frase=trigger.frase,
                 # Le due latenze di §7.5, SEPARATE: la prima e' locale e
                 # offline, la seconda e' il parser. Mediarle non descrive
                 # niente.
                 risveglio_ms=round(trigger.latenza_risveglio_ms, 1),
                 parse_ms=round((t_parse - t_finale) * 1000, 3),
                 stt_ms=round((t_finale - t_wake) * 1000, 1),
                 secondi_audio=round(self._ultimi_secondi_ascoltati, 2),
                 stt_provider=self._stt.provider.name,
                 tool=intent.tool if intent else None)
        if intent is not None:
            log.info("t0", testo=testo, tool=intent.tool, args=intent.args)
            # GLI ARGOMENTI, che fino a §13 si perdevano qui. `open_panel`
            # senza `{"panel": "globo"}` non e' un comando, e' una categoria:
            # chi lo riceveva sapeva che si voleva aprire qualcosa e non che
            # cosa. Trovato cablando la scrivania, che e' il primo consumatore
            # ad averne davvero bisogno.
            if self._su_azione:
                self._su_azione(intent.tool, dict(intent.args), traccia)
            if self._su_turno:
                self._su_turno(Turno(frase_wake=trigger.frase, azione=intent.tool,
                                     strada="t0", testo_utente=testo,
                                     traccia_id=traccia.id))
            return

        quasi = quasi_comando(testo)
        if self._t1 is None:
            # ⚠️ **Qui l'enunciato cadeva senza lasciare traccia.** Voce accesa,
            # T0 che non riconosce, T1 che non e' partito: JARVIS taceva e il
            # diario non aveva la riga per dirlo. Adesso il turno esiste lo
            # stesso — con la sua strada dichiarata `nessuna`, che e' l'unica
            # cosa che spiega il silenzio a chi rilegge.
            if self._su_turno:
                self._su_turno(Turno(frase_wake=trigger.frase, azione=None,
                                     strada="nessuna", quasi_comando=quasi,
                                     testo_utente=testo,
                                     traccia_id=traccia.id,
                                     secondi_ascoltati=self._ultimi_secondi_ascoltati))
            self._ultimi_secondi_ascoltati = 0.0
            log.warning("enunciato_caduto", motivo="t1_assente", quasi=quasi)
            return
        nota = None
        if self._udito_parziale is not None:
            udito, misurato = self._udito_parziale
            self._udito_parziale = None       # una volta sola
            nota = nota_di_interruzione(udito, misurato)
        await self.parla(self._t1.ask(testo, nota=nota), trigger, testo, quasi=quasi,
                         traccia=traccia)

    async def _trascrivi(self, limite_s: float = 8.0) -> str:
        """Un turno di trascrizione, fino al silenzio o al limite.

        Conta i **byte effettivamente mandati** al provider e li lascia in
        `self._ultimi_secondi_ascoltati`: e' il numero che ADR-004 chiede, ed
        e' misurabile solo qui — piu' a valle si conoscono le latenze, non le
        durate.
        """
        scadenza = time.monotonic() + limite_s
        pezzi: list[str] = []
        byte_mandati = 0

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
            nonlocal byte_mandati
            async for b in dal_microfono(self._audio, self._rate):
                byte_mandati += len(b)
                yield b
                if time.monotonic() > scadenza:
                    return

        async for t in self._stt.provider.stream(audio_limitato()):
            if t.is_final and t.text:
                pezzi.append(t.text)
                if t.end_of_turn:
                    break
        # s16 mono: due byte per campione.
        self._ultimi_secondi_ascoltati = byte_mandati / (self._rate * 2)
        log.info("stt_audio", secondi=round(self._ultimi_secondi_ascoltati, 2),
                 provider=self._stt.provider.name, byte=byte_mandati)
        return " ".join(pezzi).strip()

    # ── voce ─────────────────────────────────────────────────────────────────

    async def parla(self, token, trigger=None, testo_utente: str = "",
                    quasi: str | None = None, *, traccia=None) -> Turno:
        """Da' voce a un flusso di token.

        **Il chunker solo se serve** (§7.4): davanti a un TTS a enunciato
        aggrega, davanti a Flux lo si salta perche' aggiungerebbe solo latenza.
        La decisione la porta il provider in `per_enunciato`, non un `if`
        ricordato a memoria.
        """
        provider = self._tts.provider
        self._interrotto = False
        detto: list[str] = []

        async def _tracciato(sorgente_vera):
            """Ciò che il sintetizzatore ha davvero TIRATO dal flusso.

            ⚠️ `detto` era dichiarata e **mai riempita**: `testo_detto` valeva
            `getattr(provider, "text_spoken", "") or "".join(detto)`, e con il
            TTS locale — che non ha `text_spoken` — il risultato era la stringa
            vuota. Ogni turno locale finiva in `sessions/` con il campo
            `jarvis` a vuoto, e la metà di §7.4 dichiarata «fatta» lo era solo
            per Deepgram, che su questa macchina non ha mai girato.

            È un **limite superiore** di ciò che è stato udito, non una misura:
            fra l'ultimo token tirato e l'ultimo campione riprodotto c'è la
            coda del sintetizzatore. La differenza è dichiarata nella nota che
            va a T1 (`core/llm/sistema.py`).
            """
            async for pezzo in sorgente_vera:
                detto.append(pezzo)
                yield pezzo

        sorgente = (clause_chunks(_tracciato(token)) if provider.per_enunciato
                    else _tracciato(token))

        t0 = time.perf_counter()
        primo = None
        byte_detti, rate_detto = 0, self._rate
        # ⚠️ Il lucchetto sta QUI e non nei chiamanti: «chi sta parlando» e'
        # una proprieta' della pipeline, e lasciarla ai chiamanti vorrebbe
        # dire tante opinioni quanti sono — che e' il difetto che questo
        # progetto ha gia' pagato coi tre ritagli e i due orologi.
        #
        # `interrompi()` NON lo prende, ed e' voluto: uccide l'altoparlante e
        # ferma il provider, cosi' l'`async for` qui sotto finisce e il
        # lucchetto si libera da solo. Prenderlo la' sarebbe un abbraccio
        # mortale proprio nel momento in cui serve il silenzio.
        # ⚠️ **UN flusso per enunciato, non uno per blocco.**
        #
        # `play()` apre un processo di riproduzione a ogni chiamata, e un TTS
        # in streaming produce blocchi piccoli: misurato su EdgeTTS, **142
        # blocchi da 29 ms per 4,08 s di parlato**, e **85 ms di processo per
        # 29 ms di audio** — 2,9 volte il tempo reale. Quattro secondi di frase
        # uscivano in dodici, a pezzi.
        #
        # Non l'ha trovato un test: l'ha trovato un orecchio. «Robotico,
        # ostruito e lento» e' il suono di 142 flussi separati, ed e' la prova
        # che il percorso della voce non era mai stato ASCOLTATO fino in fondo.
        #
        # Con un flusso solo: **1,02x**. L'uscita si apre al PRIMO blocco,
        # perche' e' li' che si conosce il sample rate.
        uscita = None
        async with self._voce_libera:
            try:
                async for chunk in self._con_ripiego(provider, sorgente):
                    if uscita is None:
                        uscita = await self._audio.apri_uscita(chunk.sample_rate)
                    if primo is None:
                        primo = time.perf_counter()
                        log.info("primo_suono_ms", ms=round((primo - t0) * 1000))
                        # ⚠️ QUI, non prima del ciclo. Fra la richiesta al TTS
                        # e il primo campione passa il tempo della sintesi:
                        # misurato con EdgeTTS su questa rete, **1161 ms**. In
                        # quella finestra `_sta_parlando` era gia' vero e
                        # JARVIS non si sentiva ancora, quindi il barge-in
                        # poteva scattare contro il SILENZIO — e scattava:
                        # la prima delle due frasi di ripiego moriva prima del
                        # primo campione, ogni volta.
                        #
                        # Non c'e' niente da interrompere finche' non si sente
                        # niente: chi parla in quella finestra non sta parlando
                        # sopra a JARVIS, sta solo parlando.
                        self._sta_parlando = True
                    byte_detti += len(chunk.pcm)
                    rate_detto = chunk.sample_rate or rate_detto
                    await uscita.scrivi(chunk.pcm)
                    # ⚠️ DOPO la scrittura all'altoparlante, non prima: fra i
                    # due c'e' il suono che esce, e nessun calcolo di contorno
                    # deve mettersi in mezzo. La sorgente e' «tts» perche' e'
                    # cio' che distingue «JARVIS parla» da «qualcuno parla».
                    self._spettro(chunk.pcm, "tts", rate_detto)
            finally:
                # Chiudere PRIMA di abbassare `_sta_parlando`: fra l'ultimo
                # blocco scritto e la fine della riproduzione passa il tempo di
                # ciò che è ancora in coda, e in quella finestra JARVIS sta
                # ancora parlando davvero — le regole 2 e 3 di §15 leggono
                # proprio quel flag.
                #
                # ⚠️ **E l'abbassamento sta in un `finally` SUO.** L'ordine qui
                # sopra è giusto, ma metterli in sequenza rendeva la seconda
                # riga SALTABILE: `chiudi()` attende che la coda del
                # dispositivo si svuoti, e in quella finestra un `cancel()` —
                # `_ferma_il_turno(annulla=True)`, `stop()` — o un errore di
                # riproduzione portano via l'abbassamento.
                #
                # Misurato: la bandiera resta `True` col lucchetto della voce
                # già libero, cioè per il resto della sessione. §15 regola 2 la
                # legge, e da lì **nessuna card passa più, mai** — senza un
                # errore da leggere, perché `conoscibilita()` la dichiara
                # `noto`: il campo dice un fatto, e il fatto è falso.
                try:
                    if uscita is not None:
                        await uscita.chiudi()
                finally:
                    self._sta_parlando = False

        turno = Turno(
            frase_wake=trigger.frase if trigger else "",
            azione=None,
            strada="t1",
            quasi_comando=quasi,
            testo_utente=testo_utente,
            # §7.4: cio' che e' stato EFFETTIVAMENTE UDITO. Su Flux lo riporta
            # l'interruzione; in locale e' quanto abbiamo riprodotto.
            testo_detto=getattr(provider, "text_spoken", "") or "".join(detto),
            interrotto=self._interrotto,
            detto_misurato=bool(getattr(provider, "text_spoken", "")),
            traccia_id=traccia.id if traccia is not None else "",
            latenza_wake_ms=trigger.latenza_ms if trigger else 0.0,
            latenza_primo_suono_ms=(primo - t0) * 1000 if primo else 0.0,
            secondi_ascoltati=self._ultimi_secondi_ascoltati,
            secondi_detti=byte_detti / (rate_detto * 2),
        )
        # Consumati: il turno successivo non deve ereditare i secondi di
        # questo. Un contatore che non si azzera conta due volte.
        self._ultimi_secondi_ascoltati = 0.0
        if turno.interrotto:
            # ⚠️ Solo se e' stata interrotta davvero. Una nota a ogni turno
            # diventerebbe rumore, e il rumore si ignora.
            self._udito_parziale = (turno.testo_detto, turno.detto_misurato)
            log.info("interruzione_da_riferire",
                     udito=len(turno.testo_detto), misurato=turno.detto_misurato)

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

    def muto_da(self, adesso: float | None = None) -> float | None:
        """Da quanti secondi non arriva un blocco. `None` se non e' mai partito.

        Restituisce **zero** durante un turno: in quel momento il ciclo non
        legge per costruzione, e chiamarlo «muto» sarebbe una diagnosi
        sbagliata di un funzionamento corretto.

        ⚠️ **Ma non per sempre, e questo mancava.**

        Il 27 agosto alle 00:55:19 un turno e' partito e non e' mai finito: lo
        STT di Deepgram non aveva un tetto sulla `recv`. Il ciclo audio si e'
        fermato, `pw-record` ha riempito la pipe e si e' bloccato in
        `anon_pipe_write` — misurato, **zero byte in tre secondi** — e lo
        snapshot ha continuato a dire «aperto» perche' eravamo «in un turno».

        Il battito scritto il giorno prima per scoprire i microfoni muti era
        **cieco esattamente nel caso che lo produce**: la bandiera che gli
        impedisce di gridare al lupo durante una conversazione gli impediva
        anche di vedere una conversazione che non finisce.

        `TETTO_TURNO_S` non e' un numero scelto: e' la **somma dei tetti gia'
        dichiarati** degli stadi che possono stallare. Oltre quella somma un
        turno non e' «in corso», e' appeso.
        """
        if not self._ultimo_blocco:
            return None
        ora = adesso if adesso is not None else time.monotonic()
        if self._in_turno and (ora - self._turno_da) < TETTO_TURNO_S:
            return 0.0
        return ora - self._ultimo_blocco

    # ⚠️ **`_sorveglia_barge_in` e' stato TOLTO, non dimenticato.**
    #
    # Esisteva per una ragione sola: il ciclo audio era bloccato dentro
    # `await self._su_trigger(...)`, quindi mentre JARVIS parlava nessuno
    # leggeva il microfono e il barge-in del ciclo — che c'e' da sempre, poche
    # righe sopra — non poteva scattare. La toppa era un SECONDO lettore, con
    # un secondo `pw-record` e un secondo VAD.
    #
    # Adesso il turno gira per conto suo e il ciclo non si ferma mai: il
    # barge-in torna dov'era stato progettato, con le stesse soglie. I due VAD
    # erano **identici** — `SOGLIA_BARGE_IN` e `BLOCCHI_BARGE_IN` sono i
    # default di `VAD()` — quindi non si perde nessuna taratura.
    #
    # Un microfono, un lettore.

    async def _con_ripiego(self, provider, sorgente):
        """Il flusso del TTS, e **il ripiego quando cade mentre parla**.

        ⚠️ **Questo mancava, e ha prodotto il silenzio.** L'invariante 12 e la
        riga Deepgram di §16 — «chiave invalida, 429, rete → ricade sul locale
        e lo annuncia» — erano imposti **solo all'avvio**: `costruisci_tts()`
        sceglie una volta, guardando se la chiave c'e'. Un provider che
        fallisce **mentre** parla non era previsto da nessuno.

        Misurato il 26 agosto 2026, alla prima chiave Deepgram vera: tre turni
        di fila, `wake` riconosciuto, STT riuscito, T1 che risponde — e poi
        `turno_caduto` con un HTTP 400. Chi parlava ha sentito il tono di
        conferma e **nient'altro**, tre volte, senza un annuncio. E' il guasto
        silenzioso nella sua forma piu' pura, dentro il meccanismo che esiste
        per impedirlo.

        Si ripiega **solo se non e' ancora uscito un suono**: a meta' frase i
        token sono gia' stati consumati e rigenerarli e' impossibile. In quel
        caso si annuncia il guasto e si perde il turno — che e' un turno perso
        detto, non un silenzio.
        """
        primo_arrivato = False
        try:
            async for chunk in provider.stream(sorgente):
                primo_arrivato = True
                yield chunk
            return
        except Exception as exc:
            if primo_arrivato or self._ricostruisci_tts is None or not self._tts.primario:
                raise
            log.error("tts_caduto", provider=provider.name, errore=repr(exc)[:160])

        nuova = self._ricostruisci_tts()
        self._tts = nuova
        # ANNUNCIATO, mai silenzioso: e' l'invariante 12, e questa riga e'
        # l'unica differenza fra «degradato» e «rotto».
        if nuova.annuncio:
            self._annuncia_dopo(nuova.annuncio)
        log.warning("ripiego_a_caldo", da=provider.name, a=nuova.provider.name,
                    annuncio=nuova.annuncio)
        async for chunk in nuova.provider.stream(sorgente):
            yield chunk

    def _annuncia_dopo(self, frase: str) -> None:
        """L'annuncio del ripiego non puo' partire da dentro `parla()`: il
        lucchetto della voce e' preso, e aspetterebbe se stesso."""
        import asyncio as _a

        async def _poi() -> None:
            await _a.sleep(0)
            await self.annuncia(frase)

        _a.create_task(_poi())

    async def interrompi(self) -> None:
        """Barge-in: silenzio immediato.

        Due passi, e l'ordine conta: prima si zittisce l'altoparlante — che e'
        una `kill()` e avviene in microsecondi — poi si dice al provider di
        smettere di produrre. L'inverso lascerebbe suonare cio' che e' gia' in
        coda nel dispositivo.
        """
        # ⚠️ **La stessa specie, e il posto peggiore in cui averla.** Le tre
        # righe di stato stavano dopo i due `await`, quindi un provider che
        # solleva — `TTSDeepgram.interrupt()` fa un `ws.send`, e un websocket
        # caduto solleva — le portava via tutte e tre. Misurato: la bandiera
        # resta alzata proprio nell'istante in cui il Signore ha parlato SOPRA
        # a JARVIS, ed è lo stato che dice «sta ancora parlando» per sempre.
        #
        # Che il barge-in sia AVVENUTO è vero comunque: il Signore ha parlato.
        # Che il provider l'abbia confermato è un'altra cosa, e la dice
        # l'eccezione che continua a propagare.
        try:
            await self._audio.interrupt()
            await self._tts.provider.interrupt()
        finally:
            self._interrotto = True
            self._sta_parlando = False
            self._vad.ricomincia_a_contare()
        log.info("barge_in")

    def stop(self) -> None:
        self._stop.set()
        # ⚠️ Senza questa riga `run()` resterebbe appeso su `_consentito.wait()`
        # per sempre: fermare una pipeline a microfono chiuso non finirebbe
        # mai, e la chiusura del core andrebbe in timeout.
        self._consentito.set()
        # E il turno in volo: adesso non e' piu' dentro il ciclo, quindi
        # uscire dal ciclo non lo ferma piu' da solo.
        if self._compito_turno is not None and not self._compito_turno.done():
            self._compito_turno.cancel()
