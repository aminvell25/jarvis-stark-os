"""Esecuzione isolata — punto d'ingresso neutro rispetto alla piattaforma.

Il codice applicativo chiama `run_sandboxed()` e non sa che cosa lo esegua.
Su Linux e' bubblewrap (`core/platform/linux_sandbox.py`); su Windows sara'
altro. Invariante 29.

## Due profili, e il profilo si dichiara (ADR-008)

**Quale** isolamento serve e' una decisione di politica e sta qui; **come** lo
si ottiene e' di piattaforma e sta in `platform/`. Per questo `Profilo` vive in
questo file e non accanto a bubblewrap: su Windows i due profili avranno lo
stesso significato e un'implementazione diversa.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class SandboxTimeout(RuntimeError):
    """Il processo isolato non e' terminato entro il tempo concesso."""


class SandboxMemoriaEsaurita(RuntimeError):
    """Il processo isolato ha superato il tetto di memoria e il kernel l'ha ucciso.

    E' un'eccezione e non un `returncode`, per la stessa ragione di
    `SandboxTimeout`: il processo non ha prodotto un risultato, e' stato
    interrotto. Un chiamante che leggesse solo `rc` vedrebbe `137` e direbbe
    all'LLM «uscito con 137», che sembra un difetto del suo codice.

    ⚠️ Il codice d'uscita **non basta** a riconoscere questo caso: misurato,
    lo stesso frammento esce a volte con `137` (il kernel uccide il processo
    dentro il namespace) e a volte con `SIGTERM` (systemd ferma lo scope), e
    `os.kill(os.getpid(), SIGKILL)` scritto dal codice da' `137` identico. La
    verita' sta in `memory.events` del cgroup, non nel numero.
    """


class Profilo(str, Enum):
    """Quanto stretto deve essere l'isolamento.

    ⚠️ **Non c'e' un valore predefinito**, ed e' voluto: `run_sandboxed()` lo
    esige. Un chiamante che se lo dimentica non parte, invece di ricevere il
    piu' permissivo. E' la stessa forma del gancio di conferma in
    `tools/registry.py` — se non lo colleghi i tool distruttivi diventano
    inerti, non liberi.
    """

    #: Come dalla Fase 1: `--ro-bind / /`, l'host intero in sola lettura, e i
    #: percorsi di `rw_paths` scrivibili sotto le radici consentite.
    #:
    #: Per gli strumenti che JARVIS invoca e che ha scritto un umano: il
    #: `jarvis doctor` di §16.1b, e i comandi di sistema noti. Vedono il
    #: filesystem perche' devono trovare i binari che chiamano.
    STRUMENTO = "strumento"

    #: ADR-008. Radice VUOTA (`--tmpfs /`) con dentro solo l'interprete, la sua
    #: stdlib e le librerie di sistema. Nessun `$HOME`, nessun `/etc`, nessun
    #: percorso scrivibile sull'host: cio' che il codice produce torna per
    #: stdout, e lo stdout passa da `llm/untrusted.py`.
    #:
    #: Per il codice generato dall'LLM (ADR-006). Qui la domanda «cosa puo'
    #: leggere?» ha una risposta che si elenca, invece di dedursi da cio' che
    #: non e' stato escluso.
    CODICE = "codice"


async def run_sandboxed(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    timeout: float,
    profilo: Profilo,
    chdir: Path | None = None,
    lavoro_mb: int | None = None,
    memoria_mb: int | None = None,
    cpu_percento: int | None = None,
) -> tuple[int, str, str]:
    """Esegue `argv` in isolamento. Ritorna `(returncode, stdout, stderr)`.

    `profilo` e' **posizionale e obbligatorio**: vedi `Profilo`.

    `lavoro_mb` limita la directory di lavoro di `Profilo.CODICE`. E' una
    POLITICA e non un dettaglio di bubblewrap — «l'area di lavoro non supera N
    megabyte» si dira' identico su Windows — quindi sta qui e non in
    `platform/`. Senza, la tmpfs prende il predefinito del kernel, meta' della
    RAM: codice generato che scrive in un ciclo esaurisce la macchina. Con
    `STRUMENTO` non ha senso e viene rifiutato.

    `memoria_mb` e `cpu_percento` sono il tetto di RAM e di CPU del processo
    (ADR-009). Anche questi sono POLITICA: «il codice generato non supera N
    megabyte e mezzo core» si dira' identico su Windows, dove sara' un Job
    Object invece di un cgroup. Chiederli su una piattaforma che non sa
    imporli e' un errore, non un ripiego silenzioso: **un tetto che non si
    applica e' peggio di nessun tetto**, perche' chi legge la configurazione
    crede di averlo.

    Il timeout non li sostituisce e non ci prova: limita il TEMPO. Misurato su
    questa macchina, 2 GiB si allocano in 0,49 s — nessun timeout utile
    scatterebbe mai, e l'esaurimento della RAM e' immediato.

    Un'uscita diversa da zero del processo ospitato **non solleva**: e' un
    risultato, non un guasto dell'infrastruttura. Sollevano solo il timeout e
    `SandboxPolicyError`, se la richiesta e' inammissibile — e con
    `Profilo.CODICE` e' inammissibile qualunque percorso scrivibile.
    """
    from core.platform import sandbox_runner

    return await sandbox_runner(allowed_roots).run(
        argv, rw_paths, timeout, profilo, chdir, lavoro_mb, memoria_mb, cpu_percento
    )
