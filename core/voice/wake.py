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
    quando: float
    latenza_ms: float


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

    def set_frasi(self, frasi: dict[str, str]) -> None:
        """Ricarica le frasi senza ricaricare il modello.

        §7.2 mostra un `self.__init__(...)`, che rileggerebbe il modello da
        disco a ogni modifica di `settings.toml`: sono centinaia di
        millisecondi per cambiare una stringa. Il modello resta, cambia la
        grammatica.
        """
        self._frasi = {f.lower().strip(): a for f, a in frasi.items()}
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
