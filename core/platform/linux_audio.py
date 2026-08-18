"""Audio Linux: PipeWire via `pw-record` e `pw-play` — SPEC §7.1, §23.

⚠️ SCOSTAMENTO DICHIARATO da §23, che propone `sounddevice`. `sounddevice`
richiede **PortAudio**, che non e' installato e la cui installazione richiede
privilegi di amministratore. `pw-record` e `pw-play` ci sono gia'.

Non e' solo una comodita'. Tre proprieta' che la scelta porta con se':

* **zero dipendenze nuove** e nessuna installazione di sistema
* **il barge-in e' una `kill()`**. Interrompere la voce non e' un flag da
  controllare in un ciclo di riproduzione: e' terminare un processo, che il
  kernel fa in microsecondi e senza collaborazione da parte nostra (§7.4)
* §23 nominava `sounddevice` come astrazione **per Windows**: lasciare a
  Windows la propria implementazione e' il progetto della piattaforma che
  funziona come previsto, non un'eccezione ad esso

La costruzione degli argomenti e' separata dall'esecuzione, come per la
sandbox: cosi' la si verifica confrontando stringhe, **senza catturare audio**.
"""

from __future__ import annotations

import array
import asyncio
import math
from collections.abc import AsyncIterator

import structlog

log = structlog.get_logger(__name__)

RECORD = "pw-record"
PLAY = "pw-play"

#: 16 kHz mono s16: e' cio' che Vosk vuole in ingresso (§7.2) ed e' abbastanza
#: per il parlato. Registrare a 48 kHz per poi ricampionare sarebbe lavoro in
#: piu' su ogni blocco, tutto il giorno.
RATE = 16_000
CHANNELS = 1
FORMAT = "s16"

#: Blocco di lettura. A 16 kHz s16 mono, 32 ms di audio: abbastanza corto da
#: non aggiungere latenza percepibile al gate VAD, abbastanza lungo da non
#: svegliare il processo mille volte al secondo.
BLOCCO = 1024


def argv_record(rate: int = RATE, channels: int = CHANNELS) -> list[str]:
    """Argomenti di cattura. Verificabile senza catturare nulla."""
    return [RECORD, "--rate", str(rate), "--channels", str(channels),
            "--format", FORMAT, "--raw", "-"]


def argv_play(rate: int = RATE, channels: int = CHANNELS) -> list[str]:
    """Argomenti di riproduzione."""
    return [PLAY, "--rate", str(rate), "--channels", str(channels),
            "--format", FORMAT, "--raw", "-"]


def tono(freq_hz: int = 880, durata_ms: int = 80, rate: int = RATE,
         ampiezza: float = 0.25) -> bytes:
    """Un tono breve, per la conferma acustica del wake (§7.2 regola 2).

    §7.2 chiede **un tono, non una voce**: una voce che dice "si'?" costa
    centinaia di millisecondi e arriva quando l'utente sta gia' parlando.

    Ha un inviluppo di attacco e rilascio di 5 ms: un'onda troncata di netto
    produce un clic udibile, che su un suono che si sentira' decine di volte al
    giorno diventa fastidioso.
    """
    n = int(rate * durata_ms / 1000)
    bordo = max(1, int(rate * 0.005))
    campioni = array.array("h")
    for i in range(n):
        inviluppo = min(1.0, i / bordo, (n - i) / bordo)
        campioni.append(int(32767 * ampiezza * inviluppo *
                            math.sin(2 * math.pi * freq_hz * i / rate)))
    return campioni.tobytes()


class LinuxAudioIO:
    """Cattura e riproduzione su PipeWire."""

    def __init__(self, rate: int = RATE, channels: int = CHANNELS) -> None:
        self._rate = rate
        self._channels = channels
        self._riproduzione: asyncio.subprocess.Process | None = None

    async def input_stream(self, sample_rate: int = RATE) -> AsyncIterator[bytes]:
        """Blocchi PCM dal microfono, finche' non si smette di iterare.

        E' sempre attivo: il wake a frasi gira in locale su questo flusso e
        **l'audio senza frase nota non lascia mai la macchina** (§18.3).
        """
        proc = await asyncio.create_subprocess_exec(
            *argv_record(sample_rate, self._channels),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        log.info("cattura_avviata", rate=sample_rate, pid=proc.pid)
        try:
            while True:
                blocco = await proc.stdout.read(BLOCCO)
                if not blocco:
                    break
                yield blocco
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            log.info("cattura_fermata")

    async def play(self, pcm: bytes, sample_rate: int = RATE) -> None:
        """Riproduce un blocco PCM. Interrompibile: il barge-in dipende da qui."""
        await self.interrupt()          # una voce sola alla volta
        proc = await asyncio.create_subprocess_exec(
            *argv_play(sample_rate, self._channels),
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._riproduzione = proc
        try:
            proc.stdin.write(pcm)
            await proc.stdin.drain()
            proc.stdin.close()
            await proc.wait()
        except (BrokenPipeError, ConnectionResetError):
            # `interrupt()` ha ucciso il processo mentre scrivevamo: e' il caso
            # normale del barge-in, non un guasto.
            pass
        finally:
            if self._riproduzione is proc:
                self._riproduzione = None

    async def interrupt(self) -> None:
        """Zittisce immediatamente. **Questo e' il barge-in** (§7.4).

        Uccidere il processo e' piu' rapido e piu' affidabile di qualunque
        flag: non richiede che il ciclo di riproduzione collabori, e il kernel
        lo fa in microsecondi.
        """
        proc = self._riproduzione
        if proc is None or proc.returncode is not None:
            return
        self._riproduzione = None
        proc.kill()
        await proc.wait()
        log.info("riproduzione_interrotta")

    @property
    def sta_riproducendo(self) -> bool:
        p = self._riproduzione
        return p is not None and p.returncode is None
