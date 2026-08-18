"""TTS primario: Deepgram Flux — SPEC §7.4.

⚠️ **NON VERIFICATO**, per la stessa ragione di `stt_deepgram`: nessuna chiave.

**`per_enunciato = False`, ed e' il punto di §7.4.** Flux accetta i token
direttamente e determina i confini internamente: metterci davanti il chunker
**aggiunge solo latenza**. La pipeline lo legge da questo attributo invece di
ricordarselo.

`interrupt()` riporta `text_spoken` — **cio' che l'utente ha effettivamente
udito**. Va conservato: senza, JARVIS crede di aver detto una frase che nessuno
ha sentito (§7.4).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from urllib.parse import urlencode

import structlog

from core.providers.base import AudioChunk

log = structlog.get_logger(__name__)

ENDPOINT = "wss://api.deepgram.com/v2/speak"


class DeepgramTTS:
    name = "deepgram"
    per_enunciato = False          # §7.4: token diretti, niente chunker

    def __init__(self, api_key: str, sample_rate: int = 16_000,
                 voce: str = "aura-2-thalia-en") -> None:
        self._key = api_key
        self._sample_rate = sample_rate
        self._voce = voce
        self._ws = None
        self.text_spoken: str = ""

    def url(self) -> str:
        return f"{ENDPOINT}?{urlencode({'model': self._voce, 'encoding': 'linear16', 'sample_rate': str(self._sample_rate)})}"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._key}"}

    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]:
        import asyncio

        from websockets.asyncio.client import connect

        async with connect(self.url(), additional_headers=self.headers()) as ws:
            self._ws = ws

            async def invia() -> None:
                async for tok in text:
                    # I token uno per uno, senza aggregare: e' il senso di Flux.
                    await ws.send(json.dumps({"type": "Speak", "text": tok}))
                await ws.send(json.dumps({"type": "Flush"}))

            compito = asyncio.create_task(invia())
            try:
                async for msg in ws:
                    if isinstance(msg, bytes):
                        yield AudioChunk(pcm=msg, sample_rate=self._sample_rate)
                    else:
                        e = json.loads(msg)
                        if e.get("type") == "Cleared" and (t := e.get("text_spoken")):
                            self.text_spoken = t
            finally:
                compito.cancel()
                self._ws = None

    async def flush(self) -> None:
        if self._ws is not None:
            await self._ws.send(json.dumps({"type": "Flush"}))

    async def interrupt(self) -> None:
        """Barge-in. La risposta porta `text_spoken`: cio' che e' stato UDITO."""
        if self._ws is not None:
            await self._ws.send(json.dumps({"type": "Clear"}))

    async def aclose(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
