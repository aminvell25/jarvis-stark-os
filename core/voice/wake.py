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

        self._model = (
            vosk.Model(model_path=self._model_path)
            if self._model_path
            else vosk.Model(lang=lingua)
        )
        self._rec = self._crea_recognizer()
        log.info("wake_pronto", frasi=sorted(self._frasi), lingua=lingua)

    def _crea_recognizer(self):
        import vosk

        # `[unk]` assorbe tutto cio' che non e' una frase nota: senza, Vosk
        # forzerebbe ogni rumore nella frase piu' vicina e sveglierebbe JARVIS
        # in continuazione.
        grammatica = json.dumps(list(self._frasi) + ["[unk]"])
        rec = vosk.KaldiRecognizer(self._model, self._sample_rate, grammatica)
        rec.SetWords(False)
        return rec

    def feed(self, pcm: bytes) -> Trigger | None:
        """Da' in pasto un blocco PCM. Ritorna un `Trigger` se una frase e' nota."""
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
        """
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
        """Ricarica le frasi senza ricaricare il modello.

        §7.2 mostra un `self.__init__(...)`, che rileggerebbe il modello da
        disco a ogni modifica di `settings.toml`: sono centinaia di
        millisecondi per cambiare una stringa. Il modello resta, cambia la
        grammatica.
        """
        self._frasi = {f.lower().strip(): a for f, a in frasi.items()}
        self._avvisa_delle_ombre()
        self._rec = self._crea_recognizer()
        log.info("wake_frasi_ricaricate", frasi=sorted(self._frasi))

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
        return dict(self._frasi)

    @property
    def registro(self) -> list[Trigger]:
        """I trigger di questa sessione, in ordine."""
        return list(self._registro)
