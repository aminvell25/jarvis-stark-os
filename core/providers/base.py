"""Contratti dei provider vocali — SPEC §21.3.

Sono `Protocol` per la stessa ragione di `core/platform/base.py`: le
implementazioni non hanno nulla da ereditare, solo un contratto da rispettare,
e il chiamante non deve sapere quale sta usando.

E' cio' che rende possibile il ripiego di §7.3: la pipeline chiede uno
`STTProvider`, e il fatto che dietro ci sia Deepgram o Vosk non cambia una riga
del codice che lo consuma.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Transcript:
    text: str
    is_final: bool
    confidence: float = 1.0
    #: Il modello ritiene che il turno sia finito. Deepgram Flux lo determina
    #: nativamente; in locale lo deduce il VAD (§7.3).
    end_of_turn: bool = False


@dataclass(frozen=True)
class AudioChunk:
    pcm: bytes
    sample_rate: int


@runtime_checkable
class STTProvider(Protocol):
    name: str

    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        ...

    async def aclose(self) -> None:
        ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    #: `True` se il provider vuole ENUNCIATI (serve il chunker), `False` se
    #: accetta i token diretti. E' la distinzione di §7.4, resa un dato invece
    #: che una convenzione: cosi' la pipeline non deve ricordarsi chi e' chi.
    per_enunciato: bool

    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]:
        ...

    async def flush(self) -> None:
        ...

    async def interrupt(self) -> None:
        ...

    async def aclose(self) -> None:
        ...
