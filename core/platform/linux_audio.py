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
        #: Il volume DI JARVIS (0-100), applicato come guadagno sul PCM.
        #: Vedi `AudioIO.volume`: il mixer del sistema non si tocca.
        self._volume = 100

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

    # ── il volume, che e' DI JARVIS e non del sistema ───────────────────────

    @property
    def volume(self) -> int:
        return self._volume

    def imposta_volume(self, livello: int) -> int:
        """Satura invece di rifiutare: «volume 250» e' un'iperbole, non un
        errore, e il corpus T0 lo dice gia' (`("volume 250", ..., 100)`)."""
        self._volume = max(0, min(100, int(livello)))
        log.info("volume_jarvis", livello=self._volume)
        return self._volume

    def _con_guadagno(self, pcm: bytes) -> bytes:
        """Il guadagno sul PCM a 16 bit con segno.

        A volume pieno restituisce **lo stesso oggetto**: il caso normale non
        paga niente, e il barge-in di §7.4 ha un budget di 200 ms che non va
        speso a moltiplicare campioni per uno.

        A volume zero non si riproduce affatto — vedi `play`. Qui si tratta
        solo il caso intermedio.
        """
        if self._volume >= 100:
            return pcm
        import array

        campioni = array.array("h")
        campioni.frombytes(pcm[:len(pcm) - len(pcm) % 2])
        fattore = self._volume / 100
        for i, c in enumerate(campioni):
            campioni[i] = int(c * fattore)
        return campioni.tobytes()

    async def apri_uscita(self, sample_rate: int = RATE) -> "_Uscita":
        """UN processo per enunciato, invece di uno per blocco. Vedi il
        Protocol in `core/platform/base.py` per la misura che lo impone."""
        await self.interrupt()                # una voce sola alla volta
        if self._volume == 0:
            # Vedi `play()`: non si paga un processo per scrivere silenzio.
            log.info("riproduzione_saltata", perche="volume 0")
            return _Uscita(None, self)
        proc = await asyncio.create_subprocess_exec(
            *argv_play(sample_rate, self._channels),
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._riproduzione = proc
        return _Uscita(proc, self)

    async def play(self, pcm: bytes, sample_rate: int = RATE) -> None:
        """Riproduce un blocco PCM. Interrompibile: il barge-in dipende da qui."""
        await self.interrupt()          # una voce sola alla volta
        if self._volume == 0:
            # ⚠️ Non si riproduce silenzio: si NON riproduce.
            #
            # La regola resta, la giustificazione era sbagliata. Diceva che
            # «`sta_riproducendo` resterebbe vero e le regole 2 e 3 di §15
            # leggono quello»: §15 legge una bandiera della pipeline, e questo
            # strato non e' nella catena. La ragione vera e' piu' semplice e sta
            # in `AudioIO.apri_uscita` di `base.py`: **85 ms di processo per 29
            # ms di audio**, misurati. Non si paga un processo per scrivere zeri
            # che nessuno sentira'.
            log.info("riproduzione_saltata", perche="volume 0")
            return
        pcm = self._con_guadagno(pcm)
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

    # ⚠️ **Qui c'era `sta_riproducendo`, ed e' stata TOLTA.**
    #
    # Nessun lettore in tutto il repository, e quattro punti scritti — questo
    # file, il changelog di §5.29, due atti di accettazione e due docstring di
    # test — affermavano che «le regole 2 e 3 di §15 leggono proprio quello».
    # **Falso, e misurato**: §15 legge `VoicePipeline.sta_parlando`, una
    # bandiera due piani piu' su, e questo strato non compare in nessun punto
    # della catena.
    #
    # E non deve comparirci. «JARVIS sta parlando?» e' un fatto della pipeline;
    # farlo dipendere dallo stato di un processo di un altro strato e'
    # precisamente cio' che `Engine._contesto_news` ha gia' tolto una volta
    # («un campo privato di un altro modulo»). In piu' un processo `pw-play`
    # aperto non vuol dire «si sente»: `imposta_volume(0)` a meta' frase lo
    # lascia aperto con dentro campioni tutti a zero.
    #
    # `interrupt()` guarda `self._riproduzione` da se': non serviva a nessuno.

class _Uscita:
    """Un flusso di riproduzione aperto. Si scrive e si chiude.

    Non solleva su un processo ucciso: il barge-in di §7.4 **e'** un processo
    ucciso a meta' scrittura, e trattarlo come un guasto vorrebbe dire un
    traceback ogni volta che qualcuno interrompe JARVIS.
    """

    def __init__(self, proc, io: "LinuxAudioIO") -> None:
        self._proc = proc
        self._io = io

    @property
    def aperta(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def scrivi(self, pcm: bytes) -> None:
        if not self.aperta:
            return
        try:
            self._proc.stdin.write(self._io._con_guadagno(pcm))
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass                              # interrotto: e' il caso normale

    async def chiudi(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.returncode is None:
                self._proc.stdin.close()
                await self._proc.wait()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if self._io._riproduzione is self._proc:
                self._io._riproduzione = None
            self._proc = None
