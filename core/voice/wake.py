"""Wake a frasi personalizzate — SPEC §7.2, invariante 13.

**Sempre locale, anche con Deepgram primario.** Mandare l'audio a un servizio
ventiquattr'ore al giorno sarebbe insostenibile per costo e per privacy: Vosk
apre il flusso, e solo dopo il match l'audio va in rete (§7.1, §18.3).

Perche' Vosk e non openWakeWord: openWakeWord lavora su wake word **addestrate**,
Vosk con grammatica vincolata accetta una **lista chiusa di frasi** e ignora il
resto. Le frasi diventano configurazione, non un modello da riaddestrare.

Il guadagno non ovvio (§7.2): una frase puo' essere **direttamente un comando**.
*«papa' e' a casa»* esegue una scena in ~30 ms, senza STT ne' LLM, e funziona
**offline** — quel percorso non tocca ne' rete ne' modelli remoti.

Le tre regole di §7.2 sono vincoli, non consigli:

1. frasi di almeno due parole tranne il nome — le monosillabiche generano falsi
   positivi continui. Imposto in `core/settings.py`, non qui
2. conferma acustica breve: **un tono, non una voce** (`linux_audio.tono`)
3. **log locale dei trigger** con timestamp: se JARVIS si sveglia da solo, deve
   poter capire perche'
"""

from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

#: Vosk parla su stderr a ogni caricamento. Meno di zero = muto.
_LIVELLO_LOG_VOSK = -1


@dataclass(frozen=True)
class Trigger:
    """Un riconoscimento, col suo momento. Va nel registro locale."""

    frase: str
    azione: str
    #: ⚠️ **Orologio di parete** (`time.time()`), perche' va nel registro
    #: locale dei trigger, che si legge fra giorni. Non e' confrontabile con
    #: un `time.monotonic()`: vedi `riconosciuto_a`.
    quando: float
    #: ⚠️ **Non e' la latenza di risveglio.** E' il costo di UNA
    #: `AcceptWaveform` o di un `FinalResult()` — microsecondi di CPU, non il
    #: tempo dal parlato. Il nome inganna e resta per compatibilita' con cio'
    #: che gia' lo legge; il numero vero e' `latenza_risveglio_ms`.
    latenza_ms: float
    #: `time.monotonic()` del blocco che ha aperto il gate VAD, cioe' il primo
    #: campione in cui c'era voce. Zero se chi costruisce non lo sa.
    aperto_a: float = 0.0
    #: `time.monotonic()` del riconoscimento. Esiste **solo** per stare sullo
    #: stesso orologio di `aperto_a`.
    #:
    #: ⚠️ La prima stesura sottraeva `aperto_a` da `quando`, che e' l'orologio
    #: di PARETE. Il primo giro dal vivo ha stampato
    #: `risveglio_ms=1787690347540.0` — cinquantasei anni — e nessun test
    #: l'aveva visto, perche' i test costruiscono `Trigger` a mano e passano
    #: due numeri della stessa scala. **Due orologi nella stessa sottrazione**:
    #: e' la terza volta in questo progetto, dopo i due di `argomenti_a()` e i
    #: due di `estrai_locale()`.
    riconosciuto_a: float = 0.0

    @property
    def latenza_risveglio_ms(self) -> float:
        """`audio_in -> wake riconosciuta`. Questa e' la latenza di §7.5.

        Zero quando manca uno dei due capi: meglio uno zero riconoscibile di un
        numero che descrive un'altra cosa — o di un'era geologica.
        """
        if not self.aperto_a or not self.riconosciuto_a:
            return 0.0
        return (self.riconosciuto_a - self.aperto_a) * 1000


def frasi_oscurate(frasi) -> dict[str, list[str]]:
    """Quali frasi ne rendono irraggiungibili altre, perche' ne sono un PREFISSO.

    ⚠️ **Misurato dal vivo, non dedotto.** Con `jarvis` fra le frasi, il giro
    del 26 agosto ha registrato:

        wake_trigger  azione=listen  frase=jarvis
        stt_audio     provider=vosk  secondi=7.68
        t0            testo=silenzio tool=mute

    `jarvis silenzio` **e' una frase di wake configurata** con azione `mute`, e
    la strada corta di §7.2 — nessuno STT, nessuna rete, ~5 ms — **non e' stata
    presa**: Kaldi ha chiuso l'enunciato su `jarvis`, che da solo e' gia' una
    frase valida, e il resto e' finito nella trascrizione. Sono costati 7,68 s
    di ascolto al posto di cinque millisecondi, e l'esito e' stato quello
    giusto **per caso**, perche' «silenzio» e' anche un comando T0.

    Delle quattro frasi configurate, **tre erano irraggiungibili** e nessuno lo
    sapeva: il sistema rispondeva lo stesso, per un'altra strada.

    Non solleva e non toglie niente: §7.2 regola 1 vieta il risveglio a parola
    singola, e la regola **non e' imposta** da nessuna parte — imporla adesso
    spegnerebbe l'unica frase che apre l'ascolto. Si dice, e la decisione resta
    a chi legge.
    """
    ombre: dict[str, list[str]] = {}
    for corta in frasi:
        oscurate = [f for f in frasi
                    if f != corta and f.startswith(corta + " ")]
        if oscurate:
            ombre[corta] = sorted(oscurate)
    return ombre


class PhraseWake:
    """Riconoscimento vincolato a una lista chiusa di frasi.

    Il modello si scarica da se' al primo uso in `~/.cache/vosk/`
    (`$VOSK_MODEL_PATH` per spostarlo): non serve procurarselo a mano, ed e'
    il motivo per cui questa fase non ha richiesto un download manuale.
    """

    def __init__(
        self,
        frasi: dict[str, str],
        sample_rate: int = 16_000,
        lingua: str = "it",
        model_path: str | Path | None = None,
        su_trigger: Callable[[Trigger], None] | None = None,
    ) -> None:
        import vosk

        vosk.SetLogLevel(_LIVELLO_LOG_VOSK)
        self._frasi = {f.lower().strip(): a for f, a in frasi.items()}
        self._avvisa_delle_ombre()
        self._sample_rate = sample_rate
        self._lingua = lingua
        self._model_path = str(model_path) if model_path else None
        self._su_trigger = su_trigger
        self._registro: list[Trigger] = []
        #: Se un enunciato e' cominciato e non e' ancora stato chiuso. Il cambio
        #: di frasi entra **solo a bandiera bassa**: vedi `feed()` e `chiudi()`.
        self._enunciato_aperto = False
        #: Il cambio di frasi **chiesto e non ancora applicato**. Una casella,
        #: non una coda: se ne arrivano tre prima del blocco successivo vale
        #: l'ultima, perche' e' l'unica che descrive il file su disco adesso.
        #:
        #: ⚠️ **`deque(maxlen=1)` e non un attributo azzerato a mano.**
        #: `append` e `popleft` sono una sola chiamata C che non rilascia il
        #: GIL, quindi un deposito che arriva **fra** la lettura e
        #: l'azzeramento non si perde. `x = self._p; self._p = None` quella
        #: finestra ce l'ha, ed e' proprio il thread di watchdog di
        #: `settings.toml` a poterci cadere dentro.
        self._pendenti: deque[dict[str, str]] = deque(maxlen=1)

        self._model = (
            vosk.Model(model_path=self._model_path)
            if self._model_path
            else vosk.Model(lang=lingua)
        )
        self._rec = self._crea_recognizer(self._frasi)
        #: Le frasi che il riconoscitore **vivo** conosce davvero. Coincide con
        #: `self._frasi` tranne nella finestra fra un `set_frasi()` e il blocco
        #: che lo applica — e dopo un cambio che non si e' potuto costruire.
        self._frasi_vive = dict(self._frasi)
        log.info("wake_pronto", frasi=sorted(self._frasi), lingua=lingua)

    def _crea_recognizer(self, frasi: dict[str, str]):
        """Un riconoscitore nuovo sul modello gia' caricato.

        ⚠️ **Le frasi si passano, non si leggono da `self`.** Costruire la
        grammatica da `self._frasi` significherebbe che il riconoscitore vivo
        e le frasi dichiarate non possono divergere — e devono, per la finestra
        in cui un cambio e' chiesto e non ancora applicato.
        """
        import vosk

        # `[unk]` assorbe tutto cio' che non e' una frase nota: senza, Vosk
        # forzerebbe ogni rumore nella frase piu' vicina e sveglierebbe JARVIS
        # in continuazione.
        #
        # ⚠️ E tiene la lista NON VUOTA, che e' la seconda ragione, misurata:
        # `KaldiRecognizer(m, 16000, "[]")` **non solleva, termina il processo
        # con SIGSEGV**. Con `[unk]` in fondo la lista vuota non esiste, nemmeno
        # con un `settings.toml` senza una sola frase.
        grammatica = json.dumps(list(frasi) + ["[unk]"])
        rec = vosk.KaldiRecognizer(self._model, self._sample_rate, grammatica)
        rec.SetWords(False)
        return rec

    def feed(self, pcm: bytes) -> Trigger | None:
        """Da' in pasto un blocco PCM. Ritorna un `Trigger` se una frase e' nota.

        ⚠️ **Il cambio di frasi si applica QUI, prima del blocco**, ed e'
        l'unico punto in cui il riconoscitore si puo' sostituire senza
        toglierlo di mano a chi lo sta usando. Vedi `set_frasi()`.
        """
        # ⚠️ **Solo al confine, non a ogni blocco.**
        #
        # Qui c'era `self._applica_il_cambio_chiesto()` nudo, e la docstring di
        # `chiudi()` prometteva «il cambio aspetta il primo blocco del prossimo
        # enunciato». Non era vero: si applicava a OGNI blocco, anche a meta' di
        # una frase gia' cominciata, e il riconoscitore nuovo riceveva solo la
        # coda. Misurato col modello vero su 93 blocchi registrati: depositando
        # il cambio in **59 posizioni su 93** la frase di richiamo spariva,
        # senza una sola eccezione e con `wake_frasi_applicate` nei log.
        #
        # Non era una regressione — prima il riconoscitore si sostituiva
        # all'istante e l'enunciato si perdeva sempre — ma la garanzia scritta
        # era nuova ed era falsa. Adesso e' vera.
        if not self._enunciato_aperto:
            self._applica_il_cambio_chiesto()
        self._enunciato_aperto = True
        t0 = time.perf_counter()
        if not self._rec.AcceptWaveform(pcm):
            return None
        return self._riconosci(json.loads(self._rec.Result()).get("text", ""), t0)

    def chiudi(self) -> Trigger | None:
        """Chiude l'enunciato in corso e riconosce cio' che conteneva.

        ⚠️ **Senza questo metodo il wake non si svegliava mai**, e il guasto
        era invisibile perche' nessuno gli aveva ancora parlato.

        Kaldi chiude un enunciato quando **sente il silenzio**. Il ciclo di
        `pipeline.py` toglie a Vosk esattamente quello: `if not parlato:
        continue` gli fa arrivare solo i blocchi che il gate d'ascolto giudica
        parlato. Misurato, stessa frase sintetica:

            audio intero, silenzio compreso        trigger: 'jarvis'
            solo i blocchi che il VAD lascia passare       NESSUN trigger

        Continuare a nutrirlo di silenzio dopo la chiusura del gate funziona,
        ma serve tanto silenzio: misurato su quattro frasi, K=25 blocchi non
        basta e K=40 si', cioe' **800 ms** appesi a un dettaglio interno di
        Kaldi. Chiedere il finale e' deterministico e non dipende da quanto
        silenzio il riconoscitore voglia: la frase si riconosce **quando il
        gate si chiude**, cioe' 240 ms dopo che si e' smesso di parlare.

        ⚠️ **Qui un cambio di frasi in attesa NON si applica**, di proposito:
        il finale deve uscire dal riconoscitore che ha ricevuto l'audio.
        Sostituirlo un istante prima di chiedergli il finale butterebbe via
        l'enunciato appena detto — la frase di richiamo che l'utente ha
        pronunciato mentre il file cambiava. Il cambio aspetta il primo blocco
        del prossimo enunciato, che e' il confine piu' pulito che ci sia.

        L'enunciato in corso passa pero' per l'elenco **dichiarato** — vedi
        `_riconosci()` — e questo si': una frase appena cancellata dal file non
        sveglia JARVIS un'ultima volta perche' l'audio era gia' dentro Kaldi,
        e una frase a cui e' cambiata l'azione esce con l'azione nuova.
        """
        # L'enunciato finisce qui: da adesso un cambio in attesa puo' entrare.
        self._enunciato_aperto = False
        t0 = time.perf_counter()
        return self._riconosci(json.loads(self._rec.FinalResult()).get("text", ""), t0)

    def _riconosci(self, testo: str, t0: float) -> Trigger | None:
        """La parte comune fra `feed()` e `chiudi()`: una sola opinione su che
        cosa sia una frase nota."""
        testo = testo.strip().lower()
        if not testo or testo == "[unk]" or testo not in self._frasi:
            return None

        trigger = Trigger(
            frase=testo,
            azione=self._frasi[testo],
            quando=time.time(),
            riconosciuto_a=time.monotonic(),
            latenza_ms=(time.perf_counter() - t0) * 1000,
        )
        self._registro.append(trigger)
        # Regola 3 di §7.2. Non e' telemetria: e' l'unico modo di rispondere a
        # "perche' si e' svegliato mentre guardavo un film".
        log.info("wake_trigger", frase=trigger.frase, azione=trigger.azione,
                 latenza_ms=round(trigger.latenza_ms, 2))
        if self._su_trigger:
            self._su_trigger(trigger)
        return trigger

    def _avvisa_delle_ombre(self) -> None:
        """Dice quali frasi sono irraggiungibili. All'ingresso e a ogni
        ricarica a caldo, perche' e' scrivendo `settings.toml` che si crea
        un'ombra senza accorgersene."""
        for corta, oscurate in frasi_oscurate(self._frasi).items():
            log.warning(
                "frase_wake_oscurata", prefisso=corta, irraggiungibili=oscurate,
                perche="Kaldi puo' chiudere l'enunciato sulla frase corta, che "
                       "e' gia' valida: le lunghe non arrivano mai alla strada "
                       "corta di §7.2",
            )

    def set_frasi(self, frasi: dict[str, str]) -> None:
        """Chiede altre frasi di richiamo. Il modello non si ricarica.

        §7.2 mostra un `self.__init__(...)`, che rileggerebbe il modello da
        disco a ogni modifica di `settings.toml`: **206 ms misurati** per
        cambiare una stringa. Il modello resta, cambia la grammatica.

        ⚠️ **Il riconoscitore non si sostituisce qui.** Chi chiama questo
        metodo e' — misurato in `engine.py` — il thread di watchdog che ha
        visto cambiare `settings.toml`, e `feed()` sta usando `self._rec` sul
        ciclo audio: assegnarlo di la' vorrebbe dire togliere il riconoscitore
        di mano a chi lo sta usando, a meta' di un blocco e senza che niente
        sollevi. La richiesta si **deposita**, e `feed()` la applica al proprio
        inizio — fra un blocco e l'altro, mai dentro.

        ⚠️ **E non c'e' un lock, di proposito.** Il ciclo audio ha 20 ms per
        blocco: farlo aspettare che un altro thread finisca di costruire una
        grammatica significherebbe far riempire la pipe di `pw-record`, che e'
        il difetto da cui viene la sordita' del 26 e del 27 agosto. Il deposito
        e' un `append` atomico; il ciclo lo raccoglie quando gli fa comodo.

        Cio' che cambia **subito** e' l'elenco dichiarato — `frasi`, le ombre,
        `_riconosci()` — perche' chi ha appena tolto una frase dal file non
        deve vederla svegliare JARVIS un'altra volta. Cio' che cambia al blocco
        successivo e' la grammatica di Kaldi: `frasi_vive` dice a che punto e'.
        """
        chieste = {f.lower().strip(): a for f, a in frasi.items()}
        # ⚠️ La normalizzazione sta PRIMA del deposito: una chiave che non e'
        # una stringa solleva qui, sul thread di chi ha scritto il file, dove
        # c'e' ancora un `except` che possa dirlo. Depositata, sarebbe
        # esplosa dentro il ciclo audio.
        self._frasi = chieste
        self._avvisa_delle_ombre()
        self._pendenti.append(chieste)
        log.info("wake_frasi_chieste", frasi=sorted(chieste),
                 quando="al primo blocco di parlato che arriva")

    def _applica_il_cambio_chiesto(self) -> None:
        """Sostituisce il riconoscitore, se qualcuno ha chiesto altre frasi.

        Fra un blocco e l'altro, mai dentro: e' l'invariante che rende
        `set_frasi()` chiamabile da un altro thread senza un lock.

        **Costa poco, e la misura e' il motivo per cui sta qui dentro**:
        `KaldiRecognizer` con la grammatica delle quattro frasi vive costa
        **0,08 ms mediani** (0,31 nel peggiore di dieci giri) contro **0,311
        ms** di un `AcceptWaveform` — un quarto di blocco, dentro un budget di
        20 ms. A ricaricarsi sarebbe il modello, e quello costa 206 ms: e'
        precisamente cio' che `set_frasi()` non fa.

        ⚠️ **Non solleva mai.** Se la grammatica nuova non si costruisce, il
        riconoscitore di prima resta vivo e le frasi tornano a essere le sue:
        un `settings.toml` storto rende JARVIS ignaro della frase nuova, non
        sordo. E il blocco in mano al chiamante non si perde: `feed()`
        prosegue e lo passa al riconoscitore che c'e'.
        """
        try:
            chieste = self._pendenti.popleft()
        except IndexError:
            return                        # nessuno ha chiesto niente
        try:
            nuovo = self._crea_recognizer(chieste)
        except Exception as exc:
            # ⚠️ `self._frasi` torna indietro. `set_frasi()` l'ha gia' cambiato
            # — chi scrive il file deve poter leggere cio' che ha chiesto — ma
            # se il riconoscitore non lo puo' seguire, tenerlo avanti farebbe
            # due opinioni diverse su quali frasi siano vive: `_riconosci()`
            # cercherebbe in un elenco che Kaldi non puo' produrre, e il
            # risultato sarebbe un trigger che non arriva **senza un errore da
            # leggere** — la specie di silenzio che questo file combatte.
            self._frasi = dict(self._frasi_vive)
            log.error("wake_frasi_non_applicate", errore=repr(exc),
                      chieste=sorted(chieste), restano=sorted(self._frasi_vive),
                      conseguenza="resta vivo il riconoscitore di prima: "
                                  "JARVIS ignora la frase nuova, non e' sordo")
            return
        self._rec = nuovo
        self._frasi_vive = dict(chieste)
        log.info("wake_frasi_applicate", frasi=sorted(chieste))

    @property
    def modello_caricato_da(self) -> str | None:
        """Il percorso da cui il modello VIVO e' stato caricato.

        ⚠️ **Non e' `settings.voice.wake.model`.** Quello e' cio' che il file
        CHIEDE adesso; questo e' cio' con cui il riconoscitore sta ascoltando.
        Le due divergono appena qualcuno cambia il modello in `settings.toml`, e
        **la divergenza dura fino al riavvio**: `set_frasi()` non ricarica il
        modello di proposito — 206 ms misurati — e nessun'altra strada lo fa.

        Prima di questa proprieta' la radice non aveva modo di sapere con quale
        modello stesse ascoltando, e lo snapshot rispondeva con l'impostazione:
        cambiava all'istante mentre il riconoscitore continuava con quello di
        prima, per sempre e senza dirlo.

        ⚠️ **Si chiamava `percorso_modello`, e quel nome NASCONDEVA un orfano.**
        `core/gestures/tracker.py:97` ha una funzione con lo stesso nome, censita
        come orfana benigna; `scripts/orfani.py` conta i richiami **per nome**, e
        appena la radice ha cominciato a leggere questa proprieta' anche quella
        e' sembrata avere un chiamante di fuori — ed e' sparita dall'elenco.
        Misurato: `170 -> 167` orfani con una definizione in piu'.
        """
        return self._model_path

    @property
    def modello(self):
        """Il modello Vosk caricato, per chi ne vuole un secondo riconoscitore.

        `core/providers/stt_local.py` lo dice: «Il modello e' lo stesso oggetto:
        qui si crea un secondo riconoscitore, senza ricaricarlo». Ricaricarlo
        costerebbe 284 ms misurati e 87 MiB di RAM in piu' per la stessa cosa.

        Senza questo accessore la radice di composizione non aveva modo di
        passarlo, e `VoskSTT()` ne avrebbe aperto uno suo.
        """
        return self._model

    @property
    def frasi(self) -> dict[str, str]:
        """Le frasi **dichiarate**: cio' che l'ultimo `set_frasi()` ha chiesto."""
        return dict(self._frasi)

    @property
    def frasi_vive(self) -> dict[str, str]:
        """Le frasi con cui il riconoscitore vivo **e' stato costruito**.

        Diverge da `frasi` per la finestra fra un `set_frasi()` e il primo
        blocco del prossimo enunciato che lo applica — e resta indietro se
        quella grammatica non si e' potuta costruire, ma in quel caso `frasi`
        torna indietro con lei: le due si separano solo mentre si aspetta.

        ⚠️ **«Costruito con» non vuol dire «riconoscibile».** Qui c'era scritto
        «che il riconoscitore conosce DAVVERO», ed e' piu' di quanto questa
        proprieta' possa sapere: Kaldi **scarta in silenzio** le parole fuori
        dal vocabolario del modello e costruisce lo stesso la grammatica, senza
        sollevare e senza dirlo su un canale che questo processo legga.

        Misurato il 27 agosto catturando il descrittore 2, dove Vosk scrive
        dal C:

            'papà è a casa'      IGNORATE: 'papà', 'è'
            'jarvis buonasera!'  IGNORATE: 'buonasera!'
            'jarvis, luci'       IGNORATE: 'jarvis,'
            'jarvis zxqwkkrt'    IGNORATE: 'zxqwkkrt'

        e in tutti e quattro i casi `frasi_vive` le dichiarava vive. `_riconosci()`
        pretende poi il match esatto sulla stringa dichiarata — che a Kaldi manca
        di una parola — quindi **la frase e' morta e il sistema si dice sano**.
        E' il caso di chi scrive nel file la frase-esempio di questo modulo con
        gli accenti veri invece che `papa e a casa` come in `config/settings.toml`:
        la scena non parte mai e non c'e' una riga da leggere che lo spieghi.

        Chiudere il buco vuol dire confrontare la grammatica chiesta con quella
        che il riconoscitore ha davvero accettato, e Vosk non la espone: resta
        **aperto e dichiarato**, non risolto da questa docstring piu' onesta.
        """
        return dict(self._frasi_vive)

    @property
    def registro(self) -> list[Trigger]:
        """I trigger di questa sessione, in ordine."""
        return list(self._registro)
