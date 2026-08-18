"""Interfacce OS-specifiche — SPEC §23, invariante 29 del CLAUDE.md.

Ogni chiamata che cambia fra Linux e Windows passa da qui. Nel codice
applicativo non compaiono mai `bwrap`, percorsi POSIX, nomi di sensori
del kernel o API audio: compaiono questi Protocol.

Sono `Protocol` e non classi base astratte per due motivi. Le implementazioni
non hanno nulla da ereditare — solo un contratto da rispettare. E un Protocol
si verifica staticamente senza che l'implementazione debba importare questo
modulo, il che tiene `linux.py` e `windows.py` indipendenti l'uno dall'altro.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Protocol, runtime_checkable


@dataclass(frozen=True)
class MemoryInfo:
    """RAM di sistema, in byte."""

    total: int
    available: int
    percent: float


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu: float


@dataclass(frozen=True)
class GpuMemory:
    """Memoria della GPU, in byte.

    `unified=True` quando la GPU e' integrata e la sua memoria e' un carveout
    della RAM di sistema. In quel caso `total` NON e' capacita' aggiuntiva:
    e' la stessa RAM vista da un'altra angolazione, e chi decide se ammettere
    un modello deve saperlo (§9, e la nota APU della rev 5.2).
    """

    total: int
    used: int
    unified: bool
    driver: str

    @property
    def free(self) -> int:
        return max(0, self.total - self.used)


@runtime_checkable
class SandboxRunner(Protocol):
    """Esegue codice generato in isolamento. Implementata in Fase 1.

    ATTENZIONE alla distinzione, che SPEC §3.4 fa esplicitamente: questa
    sandbox isola il *codice generato*. Le operazioni su file reali NON ci
    passano — girano nel core sotto allowlist con validazione dei path
    (§6.1). Sono due difese contro due minacce diverse, e confonderle le
    rende inutili entrambe.
    """

    def describe(self) -> str:
        """Una riga per `jarvis doctor`: che cosa isola, e come.

        La piattaforma descrive se stessa perche' il doctor non deve sapere
        che cos'e' bubblewrap: su Windows la stessa riga parlera' di Job
        Objects senza che il chiamante cambi (invariante 29).
        """
        ...

    async def run(
        self,
        argv: list[str],
        rw_paths: list[Path],
        timeout: float,
        chdir: Path | None = None,
    ) -> tuple[int, str, str]:
        """Esegue `argv` senza rete e senza D-Bus, con scrittura consentita
        solo dentro `rw_paths`. Ritorna `(returncode, stdout, stderr)`.

        Non solleva su uscita non-zero del processo ospitato: un comando che
        fallisce e' un risultato, non un errore dell'infrastruttura.
        """
        ...


@runtime_checkable
class AudioIO(Protocol):
    """Ingresso e uscita audio. Implementata in Fase 3."""

    async def input_stream(self, sample_rate: int) -> AsyncIterator[bytes]:
        """Flusso PCM dal microfono, a blocchi.

        E' sempre attivo: il wake a frasi gira in locale su questo flusso e
        l'audio senza frase nota non lascia mai la macchina (SPEC §18.3).
        """
        ...

    async def play(self, pcm: bytes, sample_rate: int) -> None:
        """Riproduce un blocco PCM. Deve poter essere interrotto: il barge-in
        dipende da questo (SPEC §7.4)."""
        ...


@runtime_checkable
class Paths(Protocol):
    """Dove vivono configurazione, dati, workspace e socket di controllo.

    Su Linux sono XDG; su Windows saranno `%APPDATA%` e una named pipe. Il
    fatto che `socket_path()` restituisca un `Path` non implica che sia un
    file POSIX: su Windows sara' `\\\\.\\pipe\\jarvis-os`, che si rappresenta
    ugualmente come Path e si apre con un'API diversa — nascosta anch'essa
    dietro questa interfaccia.
    """

    def config_dir(self) -> Path:
        """Dove stanno `settings.toml` e `secrets.toml` (SPEC §8)."""
        ...

    def data_dir(self) -> Path:
        """Dati persistenti: modelli Vosk, memoria, `voice-cwd` di T1."""
        ...

    def workspace(self) -> Path:
        """Radice scrivibile di JARVIS (`~/JARVIS`, SPEC §6.1)."""
        ...

    def runtime_dir(self) -> Path:
        """Directory volatile per gli oggetti di runtime, socket compreso.

        Deve essere privata dell'utente e non sopravvivere al riavvio.
        """
        ...

    def trash_dir_for(self, path: Path) -> Path | None:
        """La directory di cestino che accoglierebbe `path`, se determinabile.

        Serve a MISURARE invece di affermare. Dopo aver cestinato qualcosa, il
        tool deve poter dire dove e' finito e verificarlo: rispondere
        "recuperabile: si'" senza guardare e' esattamente il tipo di
        affermazione che questo progetto non accetta altrove (§11.9).

        E' semantica di piattaforma, non di applicazione. Su Linux la
        specifica XDG usa il cestino della home per i file sullo stesso mount
        e una directory `.Trash-<uid>` sul mount di origine per gli altri —
        misurato: un file su /tmp finisce in `/tmp/.Trash-1000/files/`. Su
        Windows sara' il Cestino, che ha regole diverse.

        `None` se non e' determinabile: e' un esito, non un errore.
        """
        ...

    def find_trashed(self, original: Path) -> Path | None:
        """Dove si trova ORA cio' che stava in `original`, dopo il cestino.

        Non si indovina dal nome: alla collisione la specifica XDG rinomina
        inserendo un numero PRIMA dell'estensione — `nota.txt` diventa
        `nota 2.txt` — e un confronto sul nome fallisce alla seconda
        cancellazione dello stesso file. Il registro del cestino conserva il
        percorso originale: si legge quello.

        `None` se non ritrovabile. Il tool lo riporta come
        `verificato: false` invece di affermare che il file e' recuperabile.
        """
        ...

    def is_private(self, path: Path) -> bool:
        """Vero se `path` e' leggibile SOLO dal proprietario.

        Sta qui e non in `core/settings.py` perche' la riservatezza di un file
        e' semantica di piattaforma, non di applicazione: su POSIX sono i bit
        di modo, su Windows sono le ACL, e `st_mode & 0o077` su Windows non
        significa nulla. Scriverlo in settings.py sarebbe stato il primo
        percorso POSIX sparso nel codice applicativo — esattamente cio' che
        l'invariante 29 vieta.

        Aggiunta durante l'implementazione, non prevista nel piano: SPEC §8
        chiede permessi 0600 su `secrets.toml` senza dire chi li verifica.
        """
        ...

    def socket_path(self) -> Path:
        """Socket UNIX di controllo fra core ed Electron — SPEC §18.2.

        Su questo canale viaggia la conferma umana dei tool `side_effect=True`
        (§6.2), cioe' l'invariante 3. Con un socket UNIX l'autorizzazione la fa
        il kernel sui permessi del filesystem, prima che una riga di codice
        applicativo giri; con TCP su loopback l'avrebbe fatta un token che il
        codice deve ricordarsi di verificare.

        Due cose che valgono per chi implementera' la Fase 1:

        1. L'API WebSocket del browser NON puo' connettersi a un socket UNIX.
           Il renderer Electron non parlera' mai direttamente col core: la
           connessione la apre il processo main (Node) e la ponta al renderer
           via contextBridge. SPEC §3.2 lo prevede, ma qui smette di essere una
           scelta e diventa un vincolo.

        2. La directory che contiene il socket va creata con `RUNTIME_DIR_MODE`.
           E' LEI la difesa, non i permessi del socket: il modo con cui `bind()`
           crea il file dipende dalla umask, e fra `bind()` e `chmod()` c'e' una
           finestra. Un socket permissivo in una directory non attraversabile
           resta irraggiungibile; il contrario no.
        """
        ...


@runtime_checkable
class Sensors(Protocol):
    """Misura del sistema: telemetria (§21.4) e soglie di §16.

    ⚠️ SCOSTAMENTO DICHIARATO da §21.4, che chiama `psutil` direttamente dentro
    `core/ws_server.py`. Tutta la misura di sistema sta invece dietro questa
    interfaccia, per una ragione pratica: anche dove l'API di psutil e'
    portabile, i suoi MODI DI FALLIRE non lo sono — `sensors_temperatures()`
    non esiste su Windows (§23) e `AccessDenied` si presenta diversamente.

    Una regola netta ("nessun psutil fuori da platform/") sopravvive; una
    sfumata ("psutil si', tranne le temperature") si erode alla terza sessione.
    """

    def cpu_percent(self) -> float:
        """Uso CPU aggregato, 0-100. Prima chiamata compresa: chi implementa
        deve innescare il contatore all'avvio, non restituire 0.0."""
        ...

    def memory(self) -> MemoryInfo:
        ...

    def top_processes(self, n: int = 3) -> list[ProcessInfo]:
        """I primi `n` processi per uso CPU."""
        ...

    def package_temp(self) -> float | None:
        """Temperatura del package CPU in gradi Celsius, `None` se il
        sistema non la espone.

        `None` e' un esito legittimo, non un errore: su Windows psutil non
        fornisce le temperature affatto (SPEC §23) e la soglia termica di
        §16 semplicemente non scatta.
        """
        ...


@runtime_checkable
class Gpu(Protocol):
    """Memoria della GPU, per il controllo di ammissione di §9.

    Su Linux si legge da `/sys/class/drm/*/device/mem_info_*` (amdgpu) o da
    `nvidia-smi`; su Windows sarebbe DXGI o WMI. Stessa ragione di
    `Sensors.package_temp`: l'invariante 29.
    """

    def memory(self) -> GpuMemory | None:
        """`None` se nessuna GPU e' leggibile — che e' un esito, non un errore:
        una macchina senza GPU discreta ne' iGPU leggibile e' legittima, e §9
        deve poter dire "non misurabile" invece di inventare un numero."""
        ...


#: Permessi della directory di runtime. Vive qui e non nel codice della Fase 1
#: perche' e' una politica di piattaforma, non un dettaglio del server: e'
#: questo valore a rendere vera la scelta descritta in `Paths.socket_path`.
RUNTIME_DIR_MODE = 0o700

#: Lunghezza massima del percorso di un socket UNIX, in byte. E' il campo
#: `sun_path` di `struct sockaddr_un`, misurato su questo kernel. Oltre questa
#: soglia `bind()` fallisce con "AF_UNIX path too long", che e' un messaggio
#: che non dice a nessuno cosa fare. Il percorso di produzione ne usa 34, ma
#: una directory temporanea profonda lo supera con facilita': va verificato
#: PRIMA del bind, non scoperto dopo.
MAX_SOCKET_PATH = 108


class Ocr(Protocol):
    """Riconoscimento del testo in un'immagine — §12, isolato per §23.

    Su Linux e' il binario `tesseract`; su Windows sara' un altro eseguibile o
    l'API di sistema. Chi chiama non deve saperlo (invariante 29).

    `disponibile()` esiste perche' l'assenza dell'OCR e' uno stato NORMALE e
    va annunciata, non un guasto da scoprire al primo uso.
    """

    nome: str

    def disponibile(self) -> bool: ...

    async def leggi(self, png: bytes, lingua: str = ...) -> Any: ...


class HandTracker(Protocol):
    """Tracciamento delle mani — §14, isolato per §23 e per §4.

    §4 mette MediaPipe fra le dipendenze con «roadmap incerta (#6068)» e dice
    di isolarlo dietro un'interfaccia. Questo e' quell'interfaccia: cio' che
    esce sono landmark NORMALIZZATI, mai fotogrammi, e chi li riceve non sa
    ne' quale libreria li ha prodotti ne' quanto e' grande l'immagine.

    `avvia()` accende la telecamera, `ferma()` la rilascia — e sono due
    chiamate distinte perche' l'accensione dev'essere un atto esplicito
    (piano di Fase 7, R53).
    """

    nome: str

    def disponibile(self) -> bool: ...

    def avvia(self) -> None: ...

    def ferma(self) -> None: ...

    def fotogrammi(self, quanti: int | None = ...) -> Any: ...
