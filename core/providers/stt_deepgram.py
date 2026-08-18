"""STT primario: Deepgram Flux — SPEC §7.3, invariante 12.

⚠️ **NON VERIFICATO.** La chiave Deepgram non e' presente su questa macchina
(`~/.config/jarvis-os/secrets.toml` non esiste), quindi questo codice non e'
mai stato eseguito contro il servizio vero. E' scritto secondo §7.3 e verificato
solo nella forma: costruzione dell'URL, intestazioni, parsing degli eventi.

Le tre trappole che §7.3 elenca sono rispettate nel codice:

1. `flux-general-en` **non** accetta `language_hint`: si usa
   `flux-general-multi`, che supporta l'italiano
2. `eager_eot` genera risposte speculative e costa **+50-70% chiamate LLM**:
   resta spento salvo richiesta esplicita nelle impostazioni
3. con audio containerizzato non si specificano `encoding` e `sample_rate`:
   qui l'audio e' PCM grezzo, quindi si specificano entrambi

Si usa `websockets`, gia' fra le dipendenze, invece di `deepgram-sdk`: una
dipendenza in meno e il protocollo resta leggibile in questo file.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from urllib.parse import urlencode

import structlog

from core.providers.base import Transcript

log = structlog.get_logger(__name__)

ENDPOINT = "wss://api.deepgram.com/v2/listen"
MODELLO = "flux-general-multi"


class DeepgramSTT:
    name = "deepgram"

    def __init__(self, api_key: str, sample_rate: int = 16_000,
                 eot_threshold: float = 0.7, eager_eot: bool = False,
                 modello: str = MODELLO) -> None:
        self._key = api_key
        self._sample_rate = sample_rate
        self._eot = eot_threshold
        self._eager = eager_eot
        self._modello = modello
        self._ws = None

    def url(self) -> str:
        p = {
            "model": self._modello,
            "encoding": "linear16",          # trappola 3: audio grezzo
            "sample_rate": str(self._sample_rate),
            "language_hint": "it",           # trappola 1: solo su *-multi
            "eot_threshold": str(self._eot),
        }
        if self._eager:
            # trappola 2: acceso solo se qualcuno lo chiede davvero
            p["eager_eot_threshold"] = "0.5"
        return f"{ENDPOINT}?{urlencode(p)}"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._key}"}

    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]:
        import asyncio

        from websockets.asyncio.client import connect

        async with connect(self.url(), additional_headers=self.headers()) as ws:
            self._ws = ws

            async def invia() -> None:
                async for blocco in audio:
                    await ws.send(blocco)

            compito = asyncio.create_task(invia())
            try:
                async for grezzo in ws:
                    try:
                        e = json.loads(grezzo)
                    except (TypeError, json.JSONDecodeError):
                        continue
                    if t := _traduci(e):
                        yield t
            finally:
                compito.cancel()
                self._ws = None

    async def aclose(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


def _traduci(e: dict) -> Transcript | None:
    """Da evento Deepgram a `Transcript`. Isolato per poterlo verificare
    senza rete, che e' l'unica parte di questo file che si puo' provare."""
    tipo = e.get("type", "")
    if tipo not in {"TurnInfo", "Results", "Transcript"}:
        return None
    testo = (e.get("transcript")
             or e.get("channel", {}).get("alternatives", [{}])[0].get("transcript", ""))
    if not testo:
        return None
    return Transcript(
        text=testo.strip(),
        is_final=bool(e.get("is_final") or e.get("event") == "EndOfTurn"),
        confidence=float(e.get("confidence", 1.0)),
        end_of_turn=e.get("event") in {"EndOfTurn", "TurnResumed"} or bool(e.get("speech_final")),
    )
