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

from pathlib import Path
from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class SandboxRunner(Protocol):
    """Esegue codice generato in isolamento. Implementata in Fase 1.

    ATTENZIONE alla distinzione, che SPEC §3.4 fa esplicitamente: questa
    sandbox isola il *codice generato*. Le operazioni su file reali NON ci
    passano — girano nel core sotto allowlist con validazione dei path
    (§6.1). Sono due difese contro due minacce diverse, e confonderle le
    rende inutili entrambe.
    """

    async def run(
        self,
        argv: list[str],
        rw_paths: list[Path],
        timeout: float,
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
        """Socket di controllo fra core ed Electron.

        DIVERGENZA DICHIARATA da SPEC §21.4 e §18.2, che descrivono un
        WebSocket su TCP `127.0.0.1:8765` con token per-sessione. La
        decisione presa e' un socket UNIX: l'autorizzazione la fa il kernel
        sui permessi del file invece di un token applicativo, il che e'
        strettamente piu' forte del TCP su loopback. L'invariante 7 non e'
        violato — e' superato.

        Due conseguenze che valgono per chi implementera' la Fase 1:

        1. L'API WebSocket del browser NON puo' connettersi a un socket UNIX.
           Il renderer Electron non parlera' mai direttamente col core: la
           connessione la apre il processo main (Node) e la ponta al renderer
           via contextBridge. SPEC §3.2 gia' lo prevede.

        2. La directory che contiene il socket va creata con `RUNTIME_DIR_MODE`.
           Se nasce con permessi piu' larghi, l'intera decisione di sicurezza
           evapora in silenzio: e' il caso da non sbagliare.
        """
        ...


@runtime_checkable
class Sensors(Protocol):
    """Sensori hardware per la telemetria (SPEC §21.4) e le soglie di §16."""

    def package_temp(self) -> float | None:
        """Temperatura del package CPU in gradi Celsius, `None` se il
        sistema non la espone.

        `None` e' un esito legittimo, non un errore: su Windows psutil non
        fornisce le temperature affatto (SPEC §23) e la soglia termica di
        §16 semplicemente non scatta.
        """
        ...


#: Permessi della directory di runtime. Vive qui e non nel codice della Fase 1
#: perche' e' una politica di piattaforma, non un dettaglio del server: e'
#: questo valore a rendere vera la scelta descritta in `Paths.socket_path`.
RUNTIME_DIR_MODE = 0o700
