"""Sandbox Linux: bubblewrap — SPEC §3.4.

**Tutto cio' che sa di `bwrap` vive qui.** L'invariante 29 vieta di spargere
`bwrap` o percorsi POSIX nel codice applicativo, e §23 dice che su Windows la
sandbox non e' un adattamento ma un'implementazione diversa (Job Objects,
AppContainer o WSL2). Quindi non e' un dettaglio da isolare "per pulizia": e'
il file che il giorno di Windows si riscrive da zero, senza toccare altro.

Cio' che NON e' specifico di Linux — validare che un percorso scrivibile stia
sotto le radici consentite — sta in `core/sandbox/policy.py`, perche' vale
identico su qualunque piattaforma.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from core.sandbox.policy import resolve_rw_paths
from core.sandbox.runner import SandboxTimeout

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


def build_argv(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    chdir: Path | None = None,
) -> list[str]:
    """L'argv completo di bubblewrap."""
    if not argv:
        from core.sandbox.policy import SandboxPolicyError

        raise SandboxPolicyError("argv vuoto")

    risolti = resolve_rw_paths(rw_paths, allowed_roots)

    out = [
        BWRAP,
        # Rete, IPC, PID, UTS, cgroup e user namespace. La rete sparisce qui:
        # dentro il namespace non esiste alcuna interfaccia oltre a lo (down).
        "--unshare-all",
        # Se il core muore, il processo isolato muore con lui. Senza questo un
        # crash del core lascerebbe processi orfani in esecuzione.
        "--die-with-parent",
        # setsid(): niente terminale di controllo. Blocca l'iniezione di input
        # nel terminale del chiamante via ioctl(TIOCSTI).
        "--new-session",
        # Tutto il filesystem in sola lettura...
        "--ro-bind", "/", "/",
        # ...con /proc e /dev propri del namespace, non quelli dell'host.
        "--proc", "/proc",
        "--dev", "/dev",
        # /tmp privato: il codice generato deve poter scrivere da qualche parte,
        # e senza questo troverebbe il /tmp dell'host in sola lettura.
        "--tmpfs", "/tmp",
    ]

    # L'ordine conta: bubblewrap applica le operazioni in sequenza, quindi i
    # bind scrivibili devono venire DOPO il ro-bind di / o verrebbero coperti.
    for p in risolti:
        out += ["--bind", str(p), str(p)]

    if chdir is not None:
        out += ["--chdir", str(Path(chdir).expanduser().resolve())]

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
        return f"{BWRAP} ok, {seccomp}"

    async def run(
        self,
        argv: list[str],
        rw_paths: list[Path],
        timeout: float,
        chdir: Path | None = None,
    ) -> tuple[int, str, str]:
        completo = build_argv(argv, rw_paths, self._allowed_roots, chdir)

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
            log.warning("sandbox_timeout", argv=argv, timeout=timeout)
            raise SandboxTimeout(
                f"{argv[0]} non e' terminato entro {timeout}s ed e' stato ucciso"
            ) from None

        return (proc.returncode or 0,
                out.decode(errors="replace"),
                err.decode(errors="replace"))
