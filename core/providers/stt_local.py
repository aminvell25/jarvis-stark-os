"""STT locale su Vosk — il ripiego di §7.3.

⚠️ SCOSTAMENTO DICHIARATO da §7.3, che indica `faster-whisper base int8`.

Vosk e' gia' caricato per il wake a frasi (§7.2): usarlo anche per la
trascrizione continua costa **zero download in piu'** e resta **offline**, che
e' la proprieta' che l'invariante 12 chiede al ripiego. faster-whisper sarebbe
piu' accurato e costerebbe un modello in piu' da scaricare.

Il modello e' lo stesso oggetto: qui si crea un secondo riconoscitore, **senza
grammatica**, perche' la trascrizione deve poter dire qualunque cosa mentre il
wake deve poter dire solo le frasi note.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import structlog

from core.providers.base import Transcript

log = structlog.get_logger(__name__)


class VoskSTT:
    name = "vosk"

    def __init__(self, modello=None, lingua: str = "it", sample_rate: int = 16_000) -> None:
        import vosk

        vosk.SetLogLevel(-1)
        self._model = modello if modello is not None else vosk.Model(lang=lingua)
        self._sample_rate = sample_rate
        self._rec = vosk.KaldiRecognizer(self._model, sample_rate)
        self._rec.SetWords(False)

    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        async for blocco in audio:
            if self._rec.AcceptWaveform(blocco):
                testo = json.loads(self._rec.Result()).get("text", "").strip()
                if testo:
                    # Vosk chiude un segmento sul silenzio: e' il suo modo di
                    # dire "il turno e' finito", e in locale sostituisce la
                    # turn detection nativa di Flux (§7.3).
                    yield Transcript(text=testo, is_final=True, end_of_turn=True)
            else:
                parziale = json.loads(self._rec.PartialResult()).get("partial", "").strip()
                if parziale:
                    yield Transcript(text=parziale, is_final=False)

    async def aclose(self) -> None:
        return None
