"""TTS di ripiego su Microsoft Edge — `edge-tts`.

⚠️ **SCOSTAMENTO DALL'INVARIANTE 12, DELIBERATO E DA RICORDARE.**

§4 e l'invariante 12 prevedono **Kokoro**, che e' offline. Su indicazione del
proprietario del progetto il ripiego e' `edge-tts`, che non richiede chiave e
non richiede modelli scaricati — ma **vive in rete**.

Conseguenza: l'invariante 12 dice che il ripiego scatta anche su *«rete
assente»*, e §16 elenca `offline` fra gli stati funzionanti. **Con questo
provider, senza rete JARVIS resta muto.** Continuano a funzionare wake a frasi,
T0, file e telemetria — e *«papa' e' a casa»* esegue lo stesso, perche' quel
percorso non tocca ne' rete ne' modelli remoti. Si perde la voce, e l'annuncio
di degradazione diventa **visivo** (§16 prevede gia' ambra piu' indicatore).

Sintetizza per **enunciato**: `per_enunciato = True`, quindi la pipeline gli
mette davanti il chunker (§7.4). Davanti a Deepgram Flux non deve andarci.

Uscita: `edge-tts` produce MP3, `pw-play --raw` vuole PCM. Si decodifica con
GStreamer, che c'e' gia' sul sistema — misurato: primo PCM 15 ms dopo l'inizio
dell'ingresso, e non e' quindi la parte lenta della catena.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog

from core.providers.base import AudioChunk

log = structlog.get_logger(__name__)

VOCE_DEFAULT = "it-IT-DiegoNeural"
RATE = 16_000


def _argv_decodifica(rate: int = RATE) -> list[str]:
    return ["gst-launch-1.0", "-q", "fdsrc", "fd=0", "!", "decodebin", "!",
            "audioconvert", "!", "audioresample", "!",
            f"audio/x-raw,format=S16LE,rate={rate},channels=1", "!", "fdsink", "fd=1"]


class EdgeTTS:
    name = "edge"
    per_enunciato = True          # §7.4: serve il chunker davanti

    def __init__(self, voce: str = VOCE_DEFAULT, rate: int = RATE) -> None:
        self._voce = voce
        self._rate = rate
        self._interrotto = asyncio.Event()

    async def _sintetizza(self, testo: str) -> AsyncIterator[bytes]:
        import edge_tts

        async for pezzo in edge_tts.Communicate(testo, self._voce).stream():
            if pezzo["type"] == "audio":
                yield pezzo["data"]

    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]:
        """Un enunciato per volta: sintesi, decodifica, PCM."""
        self._interrotto.clear()
        async for enunciato in text:
            if self._interrotto.is_set():
                return
            if not enunciato.strip():
                continue

            proc = await asyncio.create_subprocess_exec(
                *_argv_decodifica(self._rate),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            async def alimenta() -> None:
                try:
                    async for mp3 in self._sintetizza(enunciato):
                        proc.stdin.write(mp3)
                        await proc.stdin.drain()
                except Exception as exc:
                    log.error("edge_tts_fallito", errore=str(exc))
                finally:
                    if proc.stdin.can_write_eof():
                        proc.stdin.write_eof()

            compito = asyncio.create_task(alimenta())
            try:
                while True:
                    pcm = await proc.stdout.read(4096)
                    if not pcm:
                        break
                    if self._interrotto.is_set():
                        break
                    yield AudioChunk(pcm=pcm, sample_rate=self._rate)
            finally:
                compito.cancel()
                # `returncode` puo' essere gia' stato letto dal reaper di
                # asyncio: uccidere e attendere di nuovo produce
                # "exit status already read" su stderr. Si prova, e se il
                # processo e' gia' andato non e' un errore.
                try:
                    if proc.returncode is None:
                        proc.kill()
                        await proc.wait()
                except (ProcessLookupError, AssertionError):
                    pass

    async def flush(self) -> None:
        return None

    async def interrupt(self) -> None:
        """Barge-in: smette di produrre. Il silenzio immediato lo fa
        `AudioIO.interrupt()`, che uccide la riproduzione (§7.4)."""
        self._interrotto.set()

    async def aclose(self) -> None:
        await self.interrupt()
