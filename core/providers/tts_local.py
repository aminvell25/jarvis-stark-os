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
        #: Il decodificatore in corso. Serve a `interrupt()`: una bandiera da
        #: sola non basta, perche' viene letta DOPO una lettura che puo' non
        #: tornare mai. Vedi la sua docstring.
        self._decodifica: asyncio.subprocess.Process | None = None

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
            self._decodifica = proc

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
                if self._decodifica is proc:
                    self._decodifica = None
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
        `AudioIO.interrupt()`, che uccide la riproduzione (§7.4).

        ⚠️ **La bandiera da sola non bastava, e il difetto era bloccante.**
        `stream()` la legge fra una lettura e l'altra del decodificatore: se
        quella lettura non torna — e non torna, perche' dopo il barge-in
        nessuno alimenta piu' il decodificatore e nessuno gli chiude
        l'ingresso — la bandiera non viene letta mai. Misurato: dopo il primo
        barge-in su dispositivo vero, `parla()` **non tornava piu'**, restava
        appesa oltre i dieci secondi di prova col lucchetto della voce in
        mano, e da li' in poi JARVIS non poteva piu' dire niente per il resto
        della sessione.

        La correzione e' quella che `LinuxAudio.interrupt()` ha gia' scritto
        per esteso venti file piu' in la':

            Uccidere il processo e' piu' rapido e piu' affidabile di qualunque
            flag: non richiede che il ciclo di riproduzione collabori.

        Valeva per l'altoparlante e non era stata applicata al decodificatore.
        Ucciso il processo, la lettura pendente torna vuota, il ciclo esce, e
        la bandiera resta a dire che non si deve ricominciare.
        """
        self._interrotto.set()
        proc = self._decodifica
        if proc is None or proc.returncode is not None:
            return
        self._decodifica = None
        try:
            # ⚠️ **Si uccide e non si aspetta.** `await proc.wait()` qui va in
            # stallo: `stream()` gira in un'altra corutina con una lettura
            # pendente sullo STESSO trasporto, e le due attese si bloccano a
            # vicenda — misurato, `interrompi()` non tornava piu'.
            #
            # Non serve neanche: la mietitura la fa gia' il `finally` di
            # `stream()`, che e' il proprietario del processo. Interrompere
            # vuol dire far smettere il suono, non riscuotere il codice
            # d'uscita — e §7.4 chiede che sia immediato.
            proc.kill()
        except (ProcessLookupError, AssertionError):
            pass
        log.info("decodifica_interrotta")

    async def aclose(self) -> None:
        await self.interrupt()
