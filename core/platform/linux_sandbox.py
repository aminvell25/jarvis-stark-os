"""Sandbox Linux: bubblewrap — SPEC §3.4.

**Tutto cio' che sa di `bwrap` vive qui.** L'invariante 29 vieta di spargere
`bwrap` o percorsi POSIX nel codice applicativo, e §23 dice che su Windows la
sandbox non e' un adattamento ma un'implementazione diversa (Job Objects,
AppContainer o WSL2). Quindi non e' un dettaglio da isolare "per pulizia": e'
il file che il giorno di Windows si riscrive da zero, senza toccare altro.

Cio' che NON e' specifico di Linux — validare che un percorso scrivibile stia
sotto le radici consentite — sta in `core/sandbox/policy.py`, perche' vale
identico su qualunque piattaforma. E anche QUALE isolamento serve
(`Profilo`, in `core/sandbox/runner.py`): su Windows i due profili avranno lo
stesso significato e un'implementazione diversa.

## Due argv, non uno (ADR-008)

`STRUMENTO` e' quello della Fase 1: `--ro-bind / /`, l'host intero in sola
lettura. Va bene per gli strumenti che invoca JARVIS, scritti da un umano.

`CODICE` parte da una radice VUOTA e ci monta solo cio' che serve a far
partire un interprete. Il motivo sta in ADR-008 e si riassume cosi': con
`--ro-bind / /` il codice generato legge `~/.config/jarvis-os/secrets.toml` e
lo stampa, e lo stdout torna nel contesto dell'LLM. Il `chmod 0600` non
protegge, perche' la sandbox gira come lo stesso utente.

⚠️ Le due funzioni non si fondono in una con dei rami. Un argv di sicurezza si
legge dall'inizio alla fine e si deve poter dire cosa monta senza seguire dei
`if`: due funzioni corte sono verificabili, una lunga con quattro condizioni no.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from core.sandbox.policy import SandboxPolicyError, resolve_rw_paths
from core.sandbox.runner import Profilo, SandboxTimeout

log = structlog.get_logger(__name__)

BWRAP = "bwrap"

#: ⚠️ §3.4 elenca `seccomp` fra le difese. **Non e' applicato in Fase 1.**
#:
#: `bwrap --seccomp FD` vuole un programma BPF compilato, e non esiste un
#: binding Python fra le dipendenze di §4. La decisione con le alternative
#: valutate e' in `docs/acceptance/FASE-01.md`: `--unshare-all` toglie gia'
#: rete, IPC, PID, UTS, cgroup e user namespace, che e' cio' che conta contro
#: la minaccia reale; un filtro di syscall scritto male sarebbe peggio di
#: nessun filtro, perche' darebbe falsa sicurezza.
SECCOMP_APPLICATO = False


#: La directory di lavoro del profilo `CODICE`, dentro la sandbox. E' una
#: tmpfs: esiste finche' il processo vive e non tocca il disco dell'host. Cio'
#: che il codice produce torna per **stdout**, che passa da `llm/untrusted.py`.
LAVORO = "/lavoro"

#: Le librerie di sistema, in sola lettura. Bastano queste due piu' l'albero
#: dell'interprete: verificato eseguendo, non dedotto — CPython parte cosi',
#: SENZA `/etc`, perche' col symlink `/lib -> usr/lib` ricreato il loader
#: trova le sue librerie nel percorso predefinito.
LIBRERIE = ("/usr/lib", "/usr/lib64")

#: I collegamenti di primo livello che una radice `--tmpfs /` cancella. Su una
#: distribuzione con `/usr` unificato sono symlink, e senza di essi il loader
#: cerca in `/lib/...` una directory che non esiste piu'.
SIMBOLICI = (("usr/lib", "/lib"), ("usr/lib64", "/lib64"), ("usr/bin", "/bin"))

#: Le prime opzioni sono le stesse per tutti e due i profili: sono le difese
#: che non dipendono da che cosa si monta.
_COMUNI = [
    # Rete, IPC, PID, UTS, cgroup e user namespace. La rete sparisce qui:
    # dentro il namespace non esiste alcuna interfaccia oltre a lo (down).
    "--unshare-all",
    # Se il core muore, il processo isolato muore con lui. Senza questo un
    # crash del core lascerebbe processi orfani in esecuzione.
    "--die-with-parent",
    # setsid(): niente terminale di controllo. Blocca l'iniezione di input
    # nel terminale del chiamante via ioctl(TIOCSTI).
    "--new-session",
]


def build_argv(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    profilo: Profilo,
    chdir: Path | None = None,
) -> list[str]:
    """L'argv completo di bubblewrap per il profilo richiesto.

    Fail-closed su un profilo che non conosciamo: meglio non partire che
    partire col piu' permissivo.
    """
    if not argv:
        raise SandboxPolicyError("argv vuoto")
    if profilo is Profilo.STRUMENTO:
        return _argv_strumento(argv, rw_paths, allowed_roots, chdir)
    if profilo is Profilo.CODICE:
        return _argv_codice(argv, rw_paths, chdir)
    raise SandboxPolicyError(f"profilo di sandbox sconosciuto: {profilo!r}")


def _argv_strumento(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    chdir: Path | None,
) -> list[str]:
    """Il profilo della Fase 1. Invariato: e' verificato in `FASE-01.md`."""
    risolti = resolve_rw_paths(rw_paths, allowed_roots)

    out = [BWRAP, *_COMUNI,
           # Tutto il filesystem in sola lettura...
           "--ro-bind", "/", "/",
           # ...con /proc e /dev propri del namespace, non quelli dell'host.
           "--proc", "/proc",
           "--dev", "/dev",
           # /tmp privato: senza questo si troverebbe il /tmp dell'host in
           # sola lettura.
           "--tmpfs", "/tmp"]

    # L'ordine conta: bubblewrap applica le operazioni in sequenza, quindi i
    # bind scrivibili devono venire DOPO il ro-bind di / o verrebbero coperti.
    for p in risolti:
        out += ["--bind", str(p), str(p)]

    if chdir is not None:
        out += ["--chdir", str(Path(chdir).expanduser().resolve())]

    return out + ["--", *argv]


def albero_interprete(binario: Path) -> list[tuple[Path, Path]]:
    """Che cosa montare perche' QUESTO interprete parta, e nient'altro.

    Ritorna coppie `(sorgente sull'host, destinazione nella sandbox)`.

    Il percorso si RISOLVE: `.venv/bin/python3` e' un collegamento, e montare
    il collegamento senza il suo bersaglio da' un file che punta al nulla.
    Ma si monta ANCHE col nome che il chiamante ha usato, perche' e' quel nome
    che finisce in `execvp`: la prima versione montava solo il bersaglio
    risolto e bubblewrap rispondeva `execvp /usr/bin/python3: No such file or
    directory`. L'argv del chiamante non si riscrive alle sue spalle.

    Due casi per l'albero, e sono due perche' la realta' ne ha due:

      sotto /usr   basta il file: la stdlib e le `.so` stanno gia' in
                   `/usr/lib`, che si monta comunque
      altrove      si monta l'albero dell'interprete (`<prefisso>` di
                   `<prefisso>/bin/python`), che contiene binario e stdlib

    ⚠️ Il secondo caso e' quello di uv, che tiene i suoi Python in
    `~/.local/share/uv/python/...`. E' l'unico pezzo di `$HOME` che questo
    profilo monta, in sola lettura e per percorso esatto: contiene un
    interprete e la sua stdlib, non segreti. Chi vuole zero `$HOME` passa un
    interprete di sistema. Dichiarato in ADR-008.
    """
    richiesto = Path(binario).expanduser()
    # L'ORDINE conta. Un percorso relativo si rifiuta perche' e' relativo, non
    # perche' non esiste: dentro la sandbox la cwd e' una tmpfs vuota, quindi
    # non indica niente nemmeno quando fuori indicava qualcosa. Controllando
    # prima l'esistenza, `bin/python3` usciva con «interprete inesistente», che
    # manda a cercare il problema dalla parte sbagliata.
    if not richiesto.is_absolute():
        raise SandboxPolicyError(
            f"l'interprete va nominato per percorso assoluto: {binario}"
        )
    reale = richiesto.resolve()
    if not reale.is_file():
        raise SandboxPolicyError(f"interprete inesistente: {binario}")
    # ⚠️ Un venv NON e' un interprete autonomo: e' un albero di puntatori.
    # Chiamato col percorso del venv, CPython cerca `pyvenv.cfg` e `lib/`
    # accanto a se' e non li trova — montarli vorrebbe dire portare dentro
    # anche i site-packages del progetto, cioe' piu' superficie, non meno.
    # Misurato: "Could not find platform independent libraries <prefix>".
    if (richiesto.parent.parent / "pyvenv.cfg").is_file():
        raise SandboxPolicyError(
            f"{binario} e' l'interprete di un venv, e un venv non e' "
            f"autonomo: il profilo CODICE monta un interprete e la sua "
            f"stdlib, non i site-packages di un progetto. Usare {reale}"
        )

    coppie = [(reale, reale)]
    if richiesto.is_absolute() and richiesto != reale:
        # Il nome con cui verra' chiamato. Le directory intermedie che
        # bubblewrap crea per arrivarci restano VUOTE: non e' una finestra
        # sull'albero vero, e' un file solo in mezzo al nulla.
        coppie.append((reale, richiesto))

    prefisso = reale.parent.parent
    if prefisso not in (Path("/usr"), Path("/")):
        coppie.append((prefisso, prefisso))
    return coppie


def _argv_codice(
    argv: list[str],
    rw_paths: list[Path],
    chdir: Path | None,
) -> list[str]:
    """ADR-008. Radice vuota, e dentro solo cio' che si puo' elencare.

    `--tmpfs /` e' l'allowlist del filesystem: cio' che non e' montato non
    esiste. Una denylist di percorsi da nascondere sarebbe una lista di
    sconfitte gia' subite — il file dimenticato e' quello che si perde.
    """
    if rw_paths:
        raise SandboxPolicyError(
            "Profilo.CODICE non ammette percorsi scrivibili sull'host: il "
            f"risultato torna per stdout. Richiesti: {[str(p) for p in rw_paths]}"
        )
    if chdir is not None:
        raise SandboxPolicyError(
            f"Profilo.CODICE lavora in {LAVORO}, una tmpfs: una directory "
            f"dell'host non esiste li' dentro. Richiesta: {chdir}"
        )

    out = [BWRAP, *_COMUNI,
           # La radice e' VUOTA. Tutto il resto e' cio' che ci rimettiamo
           # dentro, una riga per volta.
           "--tmpfs", "/",
           "--proc", "/proc",
           "--dev", "/dev"]

    for d in LIBRERIE:
        if Path(d).exists():
            out += ["--ro-bind", d, d]
    for bersaglio, collegamento in SIMBOLICI:
        out += ["--symlink", bersaglio, collegamento]

    for sorgente, destinazione in albero_interprete(Path(argv[0])):
        out += ["--ro-bind", str(sorgente), str(destinazione)]

    out += ["--tmpfs", "/tmp",
            "--tmpfs", LAVORO,
            "--chdir", LAVORO]

    # ⚠️ `--clearenv` e non un filtro: l'ambiente del core porta con se' il
    # PATH, la lingua, e qualunque variabile che un giorno conterra' una
    # chiave. Si riparte da zero e si rimette solo cio' che serve.
    #
    # HOME resta ASSENTA di proposito. Con HOME impostata `expanduser("~")`
    # darebbe una directory vera e scrivibile; senza, restituisce `~` e ogni
    # tentativo di elencare «la home» fallisce — che e' esattamente cio' che
    # deve succedere al codice generato.
    out += ["--clearenv",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "--setenv", "PYTHONIOENCODING", "utf-8",
            "--setenv", "TMPDIR", "/tmp"]

    return out + ["--", *argv]


class LinuxSandboxRunner:
    """`SandboxRunner` via bubblewrap.

    Le radici scrivibili arrivano dalle impostazioni (`fs.allowed_roots`) e non
    sono cablate qui: e' il chiamante a sapere quali sono, e questo oggetto a
    non poterle allargare.
    """

    def __init__(self, allowed_roots: list[Path]) -> None:
        self._allowed_roots = allowed_roots

    def describe(self) -> str:
        """Riga per `jarvis doctor`. La piattaforma descrive se stessa: cosi'
        il doctor non deve sapere che cos'e' bubblewrap."""
        seccomp = "unshare-all + seccomp" if SECCOMP_APPLICATO else (
            "unshare-all attivo — seccomp NON applicato (Fase 1)")
        return f"{BWRAP} ok, {seccomp}, due profili (ADR-008)"

    async def run(
        self,
        argv: list[str],
        rw_paths: list[Path],
        timeout: float,
        profilo: Profilo,
        chdir: Path | None = None,
    ) -> tuple[int, str, str]:
        completo = build_argv(argv, rw_paths, self._allowed_roots, profilo, chdir)

        proc = await asyncio.create_subprocess_exec(
            *completo,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            # `--die-with-parent` non basta: il parent siamo noi e siamo vivi.
            # Si uccide bubblewrap, e i suoi figli muoiono con lui perche' sono
            # nel suo PID namespace — ucciso il PID 1 di quel namespace, il
            # kernel termina tutto il resto.
            proc.kill()
            await proc.wait()
            log.warning("sandbox_timeout", argv=argv, timeout=timeout,
                        profilo=profilo.value)
            raise SandboxTimeout(
                f"{argv[0]} non e' terminato entro {timeout}s ed e' stato ucciso"
            ) from None

        return (proc.returncode or 0,
                out.decode(errors="replace"),
                err.decode(errors="replace"))
