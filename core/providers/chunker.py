"""Chunker per il TTS a enunciato — SPEC §7.4.

**Va SOLO davanti al TTS a enunciato, mai davanti a Deepgram Flux.**

§7.4 lo dice di Kokoro; il ripiego oggi e' `edge-tts`, ma la ragione non
cambia ed e' quella che conta: Flux accetta i token direttamente e determina i
confini internamente — aggregare **aggiunge solo latenza** — mentre un
sintetizzatore a enunciato, senza chunker, aspetterebbe la fine della frase.

La regola e': *chunker davanti al TTS a enunciato, mai davanti a Flux.*

Il dettaglio che vale piu' di tutti: **il primo frammento ha soglia dimezzata**.
Cio' che l'orecchio percepisce come reattivita' non e' la durata totale della
risposta: e' QUANDO JARVIS comincia a parlare.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

_BOUNDARY = re.compile(r"[.!?…](?:\s|$)|[;:](?:\s|$)|,(?:\s|$)")
MIN_CHARS, MAX_CHARS = 40, 220


async def clause_chunks(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    """Aggrega i token in frammenti pronunciabili."""
    buf, first = "", True
    threshold = MIN_CHARS // 2
    async for tok in tokens:
        buf += tok
        m = None
        if len(buf) >= threshold:
            for m in _BOUNDARY.finditer(buf):
                pass
        if (m and len(buf) >= threshold) or len(buf) >= MAX_CHARS:
            cut = m.end() if m else MAX_CHARS
            chunk, buf = buf[:cut].strip(), buf[cut:]
            if chunk:
                yield chunk
                if first:
                    first, threshold = False, MIN_CHARS
    if buf.strip():
        yield buf.strip()
