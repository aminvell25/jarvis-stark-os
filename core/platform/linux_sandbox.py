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
import itertools
import os
import shutil
from pathlib import Path

import structlog

from core.sandbox.policy import SandboxPolicyError, resolve_rw_paths
from core.sandbox.runner import (Profilo, SandboxMemoriaEsaurita,
                                 SandboxTimeout)

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
    lavoro_mb: int | None = None,
) -> list[str]:
    """L'argv completo di bubblewrap per il profilo richiesto.

    Fail-closed su un profilo che non conosciamo: meglio non partire che
    partire col piu' permissivo.
    """
    if not argv:
        raise SandboxPolicyError("argv vuoto")
    if profilo is Profilo.STRUMENTO:
        if lavoro_mb is not None:
            raise SandboxPolicyError(
                "lavoro_mb vale solo per Profilo.CODICE: STRUMENTO scrive nei "
                "percorsi dell'host, che hanno la dimensione che hanno"
            )
        return _argv_strumento(argv, rw_paths, allowed_roots, chdir)
    if profilo is Profilo.CODICE:
        return _argv_codice(argv, rw_paths, chdir, lavoro_mb)
    if profilo is Profilo.LABORATORIO:
        return _argv_laboratorio(argv, rw_paths, allowed_roots, chdir, lavoro_mb)
    if profilo is Profilo.AGENTE:
        if lavoro_mb is not None:
            raise SandboxPolicyError(
                "lavoro_mb vale solo per CODICE e LABORATORIO: AGENTE scrive "
                "nella bozza dell'host, che ha la dimensione che ha"
            )
        return _argv_agente(argv, rw_paths, allowed_roots, chdir)
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
    lavoro_mb: int | None,
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

    # ⚠️ `--size` vale per il `--tmpfs` CHE SEGUE, e per quello soltanto: e'
    # il contratto di bubblewrap, quindi l'ordine di queste righe non e'
    # estetica. Senza, la tmpfs prende il predefinito del kernel — meta' della
    # RAM — ed e' il punto 5 dei «non verificato» di ADR-008.
    #
    # Misurato: con 8 MiB, scrivere 4 MiB riesce e scriverne 32 da' ENOSPC.
    out += ["--tmpfs", "/tmp"]
    if lavoro_mb is not None:
        if lavoro_mb < 1:
            raise SandboxPolicyError(f"lavoro_mb deve essere positivo: {lavoro_mb}")
        out += ["--size", str(int(lavoro_mb) * 1024 * 1024)]
    out += ["--tmpfs", LAVORO,
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


def albero_venv(binario: Path) -> list[tuple[Path, Path]]:
    """Come `albero_interprete`, ma un venv e' AMMESSO — e' il punto (ADR-015).

    `CODICE` rifiuta un venv perche' porterebbe dentro i site-packages del
    progetto. `LABORATORIO` li vuole: uno script che genera un solido importa
    `numpy` e `trimesh`, e sono le librerie che `pyproject.toml` ha gia'
    scelto. Si monta l'interprete VERO dietro il collegamento — con la sua
    stdlib, come per `CODICE` — e in piu' l'albero del venv, in sola lettura,
    col nome con cui verra' chiamato: e' cosi' che CPython trova `pyvenv.cfg`
    accanto a se' e da li' i site-packages.

    Chiamato con un interprete che NON e' un venv, si comporta come
    `albero_interprete`: il laboratorio funziona anche con un Python di
    sistema, solo senza le librerie.
    """
    richiesto = Path(binario).expanduser()
    if not richiesto.is_absolute():
        raise SandboxPolicyError(
            f"l'interprete va nominato per percorso assoluto: {binario}"
        )
    venv = richiesto.parent.parent
    if not (venv / "pyvenv.cfg").is_file():
        return albero_interprete(richiesto)
    reale = richiesto.resolve()
    if not reale.is_file():
        raise SandboxPolicyError(f"interprete inesistente: {binario}")
    # L'interprete vero, con la sua stdlib: e' `albero_interprete` sul
    # bersaglio risolto, che non e' un venv.
    coppie = albero_interprete(reale)
    # ⚠️ Il collegamento del venv puo' passare per un NOME INTERMEDIO che e'
    # a sua volta un collegamento: uv scrive `.venv/bin/python ->
    # .../cpython-3.12-linux-x86_64-gnu/bin/python3.12`, e quella directory e'
    # un symlink a `cpython-3.12.14-...`. Montare solo l'albero risolto lascia
    # il nome intermedio nel nulla, e bubblewrap risponde «execvp: No such
    # file or directory» — misurato. Si monta anche l'albero col nome con cui
    # il venv lo chiama, e `pyvenv.cfg` (`home = .../cpython-3.12-.../bin`)
    # torna a trovare cio' che nomina.
    if richiesto.is_symlink():
        puntato = Path(os.readlink(richiesto))
        if puntato.is_absolute():
            prefisso_puntato = puntato.parent.parent
            if prefisso_puntato != reale.parent.parent:
                coppie.append((prefisso_puntato.resolve(), prefisso_puntato))
    coppie.append((venv.resolve(), venv))
    return coppie


def _argv_laboratorio(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    chdir: Path | None,
    lavoro_mb: int | None,
) -> list[str]:
    """ADR-015. `CODICE` piu' UNA directory scrivibile: la bozza.

    Tutto cio' che `_argv_codice` decide vale anche qui — radice vuota,
    librerie di sistema in sola lettura, `--clearenv`, nessuna `HOME` — e le
    due differenze sono elencabili: l'interprete puo' essere un venv
    (`albero_venv`), e la directory di lavoro e' la bozza sull'host invece di
    una tmpfs. **Esattamente una**, sotto le radici consentite, e `chdir` o e'
    lei o non c'e': uno script del laboratorio che lavora altrove non ha
    senso, e un secondo percorso scrivibile sarebbe la seconda zona che
    ADR-015 esiste per negare.
    """
    if len(rw_paths) != 1:
        raise SandboxPolicyError(
            "Profilo.LABORATORIO vuole ESATTAMENTE una directory scrivibile, "
            f"la bozza. Richieste: {[str(p) for p in rw_paths]}"
        )
    [bozza] = resolve_rw_paths(list(rw_paths), allowed_roots)
    if not bozza.is_dir():
        raise SandboxPolicyError(f"la bozza non e' una directory: {bozza}")
    if chdir is not None and Path(chdir).expanduser().resolve() != bozza:
        raise SandboxPolicyError(
            f"in Profilo.LABORATORIO la directory di lavoro E' la bozza "
            f"({bozza}); richiesta: {chdir}"
        )

    out = [BWRAP, *_COMUNI,
           "--tmpfs", "/",
           "--proc", "/proc",
           "--dev", "/dev"]
    for d in LIBRERIE:
        if Path(d).exists():
            out += ["--ro-bind", d, d]
    for bersaglio, collegamento in SIMBOLICI:
        out += ["--symlink", bersaglio, collegamento]
    for sorgente, destinazione in albero_venv(Path(argv[0])):
        out += ["--ro-bind", str(sorgente), str(destinazione)]

    if lavoro_mb is not None:
        if lavoro_mb < 1:
            raise SandboxPolicyError(f"lavoro_mb deve essere positivo: {lavoro_mb}")
        # Come in `_argv_codice`: `--size` vale per la tmpfs CHE SEGUE, e
        # bubblewrap rifiuta di partire se non la segue — misurato, «--size
        # must be followed by --tmpfs». Qui limita `/tmp`, l'unico spazio
        # volatile: la bozza e' disco vero.
        out += ["--size", str(int(lavoro_mb) * 1024 * 1024)]
    out += ["--tmpfs", "/tmp"]
    # La bozza: l'unico `--bind` scrivibile, e la cwd. Dopo la radice vuota,
    # o ne verrebbe coperto.
    out += ["--bind", str(bozza), str(bozza),
            "--chdir", str(bozza)]

    out += ["--clearenv",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "--setenv", "PYTHONIOENCODING", "utf-8",
            "--setenv", "TMPDIR", "/tmp"]

    return out + ["--", *argv]


#: Lo stato di Claude Code: credenziali, sessioni, cronologia. Il profilo
#: `AGENTE` li monta scrivibili DA SE', per nome fisso: sono suoi, non del
#: chiamante, e un `rw_paths` che li nominasse sarebbe rifiutato dalle radici
#: consentite — giustamente, perche' non sono una cartella del proprietario.
STATO_AGENTE = (Path("~/.claude"), Path("~/.claude.json"))


def _argv_agente(
    argv: list[str],
    rw_paths: list[Path],
    allowed_roots: list[Path],
    chdir: Path | None,
) -> list[str]:
    """ADR-015. `STRUMENTO` con la rete, per Claude Code che scrive una bozza.

    Misurato il 3 settembre 2026: `claude --version` parte cosi', e da dentro
    `echo x > ~/fuori.txt` risponde «Read-only file system». E' il confine
    che `core/llm/claude_t2.py` dichiara di NON avere con `--allowedTools`:
    qui lo impone il kernel, non il prompt. L'host resta leggibile per
    intero, come in `STRUMENTO` — e' cio' che T2 ha sempre avuto — e cio'
    che cambia e' dove puo' scrivere: la bozza e il proprio stato.
    """
    risolti = resolve_rw_paths(list(rw_paths), allowed_roots)
    if len(risolti) != 1:
        raise SandboxPolicyError(
            "Profilo.AGENTE vuole ESATTAMENTE una directory scrivibile, la "
            f"bozza. Richieste: {[str(p) for p in rw_paths]}"
        )
    out = [BWRAP, *_COMUNI,
           # DOPO `--unshare-all` di `_COMUNI`: bubblewrap applica le opzioni
           # in ordine, e questa riapre la sola rete. Senza, Claude Code non
           # raggiunge il modello e il profilo isolerebbe un processo inutile.
           "--share-net",
           "--ro-bind", "/", "/",
           "--proc", "/proc",
           "--dev", "/dev",
           "--tmpfs", "/tmp"]
    for p in risolti:
        out += ["--bind", str(p), str(p)]
    for p in STATO_AGENTE:
        q = p.expanduser()
        if q.exists():
            out += ["--bind", str(q), str(q)]
    if chdir is not None:
        out += ["--chdir", str(Path(chdir).expanduser().resolve())]
    return out + ["--", *argv]


# ─────────────────────────────────────────────────────────────────────────────
# ADR-009 — il tetto di memoria e di CPU, con un cgroup vero
# ─────────────────────────────────────────────────────────────────────────────

#: `systemd-run --user --scope` mette il processo in un cgroup transitorio e
#: gli applica `MemoryMax` e `CPUQuota`. bubblewrap non sa farlo: `--unshare-
#: cgroup` isola il NAMESPACE, non impone un limite.
#:
#: Perche' non `resource.setrlimit()` prima dell'exec, che non richiederebbe
#: nulla: **misurato, un rlimit e' per PROCESSO.** Otto figli da 400 MiB
#: stanno tutti sotto un limite di 512 MiB e insieme ne allocano 3200. Un
#: `os.fork()` di tre righe scavalca la difesa. Il cgroup addebita l'albero
#: intero e li uccide in 0,07 s. Vedi ADR-009 per la tabella completa.
#:
#: Il progetto dipende gia' da systemd: `packaging/jarvis-core.service` e' un
#: servizio UTENTE, e `systemd-run --user` parla con lo stesso gestore.
#: Verificato eseguendolo annidato dentro un servizio utente transitorio.
LIMITE = "systemd-run"

#: `MemorySwapMax=0` non e' un dettaglio. **Senza, il tetto non ferma niente**:
#: misurato, con `MemoryMax=512M` e lo swap concesso, 2 GiB si allocano lo
#: stesso — il kernel scarica le pagine sugli 8 GiB di swap di questa macchina
#: e il processo continua, solo piu' lento. Con lo swap a zero muore in 0,16 s.
#:
#: `OOMPolicy=continue` non allenta niente — quando arriva, il kernel ha gia'
#: ucciso il processo — ma impedisce a systemd di FERMARE lo scope per
#: reazione, e quindi di smontare il cgroup mentre stiamo per leggerlo.
#: Misurato, ed e' la differenza fra un messaggio certo e uno probabile:
#:
#:     senza:  6 esecuzioni su 6  «ucciso dal sistema, non ho potuto confermare»
#:     con:    6 esecuzioni su 6  «superato il tetto di 256 MB, oom_kill=1»
_SENZA_SWAP = ("-p", "MemorySwapMax=0", "-p", "OOMPolicy=continue")

#: Una FETTA tutta nostra, e non e' ordine: e' l'unico posto dove il conteggio
#: degli OOM appartiene solo a noi. Vedi `oom_nella_fetta()`.
FETTA = "jarvis-codice.slice"


#: La radice dei cgroup del gestore utente. `--user --scope` crea lo scope
#: sotto `app.slice`; il glob copre le installazioni che lo mettono altrove.
def _radice_cgroup() -> Path:
    uid = os.getuid()
    return Path(f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service")


def _percorso_fetta() -> Path:
    """Dove systemd mette `FETTA`.

    Le fette si annidano secondo i trattini del NOME: `jarvis-codice.slice`
    sta dentro `jarvis.slice`, che systemd crea da sola. Non e' una nostra
    convenzione, e' come systemd costruisce l'albero — verificato guardandolo.
    """
    pezzi = FETTA.removesuffix(".slice").split("-")
    p = _radice_cgroup()
    for i in range(1, len(pezzi) + 1):
        p = p / ("-".join(pezzi[:i]) + ".slice")
    return p


def oom_nella_fetta() -> int | None:
    """Quante volte il kernel ha ucciso per memoria dentro `FETTA`, in tutto.

    ⚠️ **E' questo il contatore che regge, non quello dello scope.**

    In cgroup v2 `memory.events` e' GERARCHICO: quello di una fetta somma i
    suoi discendenti. E la fetta, a differenza dello scope, non sparisce —
    misurato, resta `active` anche quando e' vuota. Lo scope invece viene
    smontato appena si svuota, e la lettura del suo `memory.events` e' una
    corsa che si perde: e' andata bene 25 volte di fila e poi ha smesso, il che
    e' il modo peggiore in cui una difesa puo' essere sbagliata.

    Si legge PRIMA e DOPO, e la differenza e' cio' che e' successo nel mezzo.

    ⚠️ La fetta e' dedicata proprio per questo. Con lo scope sotto `app.slice`
    il conteggio comprenderebbe l'OOM di qualunque altra applicazione della
    sessione, e un editor che esaurisce la memoria diventerebbe un messaggio
    sbagliato mandato all'LLM.

    Ritorna 0 se la fetta non esiste ancora — non ha ospitato niente, quindi
    non ha ucciso niente — e `None` se non si riesce a leggere, che e' un caso
    diverso e non va confuso con zero.
    """
    f = _percorso_fetta() / "memory.events"
    if not _percorso_fetta().is_dir():
        return 0
    try:
        return int(dict(r.split() for r in f.read_text().splitlines())["oom_kill"])
    except (OSError, ValueError, KeyError):
        return None


_contatore = itertools.count()


def _nome_unit() -> str:
    """Un nome per lo scope, scelto da noi.

    Non e' cosmesi: con `--unit=` il percorso del cgroup diventa
    DETERMINISTICO, e senza sapere dove sia il cgroup non si puo' leggere
    `memory.events` — cioe' non si puo' distinguere «ha finito la memoria» da
    «e' morto». Con il nome casuale che sceglie systemd si potrebbe solo
    indovinare dal codice d'uscita, che e' proprio cio' che non basta.
    """
    return f"jarvis-codice-{os.getpid()}-{next(_contatore)}"


def limite_mancante() -> str | None:
    """Perche' il tetto non e' applicabile qui, o `None` se lo e'.

    Per `jarvis doctor`: **un limite che non si applica perche' manca un
    binario e' peggio di nessun limite**, perche' chi ha scritto
    `code.memory_mb = 512` crede di averlo.
    """
    if shutil.which(LIMITE) is None:
        return f"{LIMITE} non e' nel PATH"
    if not _radice_cgroup().is_dir():
        return f"nessun gestore systemd utente in {_radice_cgroup()}"
    controllori = (_radice_cgroup() / "cgroup.controllers").read_text().split()
    mancanti = {"memory", "cpu"} - set(controllori)
    if mancanti:
        return (f"il gestore utente non ha i controllori {sorted(mancanti)} "
                f"delegati (ha: {controllori})")
    return None


def argv_limite(unit: str, memoria_mb: int | None,
                cpu_percento: int | None) -> list[str]:
    """Il prefisso che mette bubblewrap dentro un cgroup con dei tetti.

    Fail-closed: se `systemd-run` non c'e', **solleva**. Eseguire lo stesso
    senza tetto sarebbe la peggiore delle tre possibilita' — il codice
    girerebbe senza limiti mentre la configurazione dice che ne ha uno.
    """
    if memoria_mb is not None and memoria_mb < 1:
        raise SandboxPolicyError(f"memoria_mb deve essere positivo: {memoria_mb}")
    if cpu_percento is not None and cpu_percento < 1:
        raise SandboxPolicyError(f"cpu_percento deve essere positivo: {cpu_percento}")
    perche = limite_mancante()
    if perche is not None:
        raise SandboxPolicyError(
            f"tetto di memoria richiesto ({memoria_mb} MB) ma non applicabile: "
            f"{perche}. Il codice generato non gira senza (ADR-009)"
        )

    fuori = [LIMITE, "--user", "--scope", "--quiet", f"--unit={unit}",
             f"--slice={FETTA}"]
    if memoria_mb is not None:
        fuori += ["-p", f"MemoryMax={int(memoria_mb)}M", *_SENZA_SWAP]
    if cpu_percento is not None:
        fuori += ["-p", f"CPUQuota={int(cpu_percento)}%"]
    return fuori + ["--"]


def eventi_memoria(unit: str) -> dict[str, int] | None:
    """`memory.events` dello scope, o `None` se il cgroup e' gia' sparito.

    E' la verita' del kernel, e serve perche' il codice d'uscita mente in
    entrambe le direzioni. Misurato, con lo stesso frammento che gonfia:

        oom_kill=1  max=37   rc=137     ha finito la memoria
        oom_kill=0  max=0    rc=137     `os.kill(os.getpid(), SIGKILL)`

    Stesso `rc`, due cause diverse. Il contatore le distingue; il numero no.

    ⚠️ **E' inaffidabile, e va sempre accompagnato.** Lo si legge dopo che il
    processo e' morto, e systemd smonta lo scope appena si svuota: sono andate
    bene 25 letture di fila, poi hanno cominciato a fallire tutte, senza che
    cambiasse una riga. Una difesa che funziona finche' non serve e' peggio di
    una che non c'e', quindi la risposta certa la da' `oom_nella_fetta()` e
    questa e' solo la scorciatoia per quando la corsa si vince.
    """
    radice = _radice_cgroup()
    candidati = [radice / "app.slice" / f"{unit}.scope" / "memory.events",
                 *radice.glob(f"*/{unit}.scope/memory.events")]
    for c in candidati:
        try:
            righe = c.read_text().splitlines()
            return {k: int(v) for k, v in (r.split() for r in righe)}
        except (OSError, ValueError):
            continue
    return None


def _ucciso(rc: int) -> bool:
    """Il processo e' stato terminato da un segnale, non e' uscito da solo.

    Tre forme, tutte osservate: `rc` negativo (il segnale e' arrivato a
    `systemd-run`), 137 e 143 (bubblewrap riporta il 128+N del proprio figlio).
    Quale delle tre si veda e' una corsa fra il kernel e systemd.
    """
    return rc < 0 or rc in (137, 143)


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
        perche = limite_mancante()
        tetto = (f"tetti via {LIMITE}" if perche is None
                 else f"TETTI NON APPLICABILI: {perche}")
        return f"{BWRAP} ok, {seccomp}, due profili (ADR-008), {tetto}"

    def argv(
        self,
        argv: list[str],
        rw_paths: list[Path],
        profilo: Profilo,
        chdir: Path | None = None,
    ) -> list[str]:
        return build_argv(argv, rw_paths, self._allowed_roots, profilo, chdir)

    async def run(
        self,
        argv: list[str],
        rw_paths: list[Path],
        timeout: float,
        profilo: Profilo,
        chdir: Path | None = None,
        lavoro_mb: int | None = None,
        memoria_mb: int | None = None,
        cpu_percento: int | None = None,
    ) -> tuple[int, str, str]:
        completo = build_argv(
            argv, rw_paths, self._allowed_roots, profilo, chdir, lavoro_mb
        )

        # ⚠️ L'ORDINE: il cgroup sta FUORI da bubblewrap, non dentro. Dentro
        # sarebbe inutile — il processo isolato non ha `/sys/fs/cgroup` e non
        # potrebbe imporsi nulla — e comunque un limite che si applica da se'
        # e' un limite che si puo' togliere da se'. Fuori, lo impone il gestore
        # dei cgroup, che il codice generato non puo' raggiungere: e' la stessa
        # forma dell'invariante 7, dove l'autorizzazione la da' il sistema
        # operativo e non il codice.
        unit = oom_prima = None
        if memoria_mb is not None or cpu_percento is not None:
            unit = _nome_unit()
            completo = argv_limite(unit, memoria_mb, cpu_percento) + completo
            # PRIMA di partire: la differenza col valore di dopo e' cio' che e'
            # successo nel mezzo. Letto qui e non dopo perche' dopo sarebbe una
            # fotografia senza il suo prima.
            oom_prima = oom_nella_fetta()

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

        rc = proc.returncode or 0
        if unit is not None and _ucciso(rc):
            self._forse_memoria(unit, rc, memoria_mb, argv, oom_prima)

        return (rc,
                out.decode(errors="replace"),
                err.decode(errors="replace"))

    @staticmethod
    def _forse_memoria(unit: str, rc: int, memoria_mb: int | None,
                       argv: list[str], oom_prima: int | None) -> None:
        """Solleva se il tetto ha morso. Tace se il processo e' morto d'altro.

        L'asimmetria e' voluta: quando il kernel dice che NON e' stata la
        memoria, attribuirgliela sarebbe una diagnosi sbagliata mandata
        all'LLM, che poi ci ragiona sopra. E il codice d'uscita da solo non
        distingue — 137 arriva sia dall'OOM sia da un `os.kill` scritto dal
        codice.

        Tre livelli, dal piu' preciso al piu' prudente:

          1. `memory.events` dello scope — esatto, ma spesso gia' smontato
          2. il contatore della fetta, prima e dopo — regge sempre, e la fetta
             e' nostra quindi il conteggio non comprende altre applicazioni
          3. nessuno dei due — si dice che non si e' potuto confermare
        """
        eventi = eventi_memoria(unit)
        if eventi is not None:
            if eventi.get("oom_kill", 0) == 0:
                return
            log.warning("sandbox_memoria", unit=unit, rc=rc, memoria_mb=memoria_mb,
                        fonte="scope", eventi=eventi)
            raise SandboxMemoriaEsaurita(
                f"il codice ha superato il tetto di memoria di {memoria_mb} MB "
                f"ed e' stato terminato dal kernel (oom_kill="
                f"{eventi.get('oom_kill')}, ha toccato il tetto "
                f"{eventi.get('max')} volte)"
            )

        oom_dopo = oom_nella_fetta()
        if oom_prima is not None and oom_dopo is not None:
            if oom_dopo == oom_prima:
                return                       # il kernel non ha ucciso nessuno
            log.warning("sandbox_memoria", unit=unit, rc=rc, memoria_mb=memoria_mb,
                        fonte="fetta", oom=oom_dopo - oom_prima)
            raise SandboxMemoriaEsaurita(
                f"il codice ha superato il tetto di memoria di {memoria_mb} MB "
                f"ed e' stato terminato dal kernel (oom_kill="
                f"{oom_dopo - oom_prima} nella fetta {FETTA})"
            )

        log.warning("sandbox_memoria", unit=unit, rc=rc, memoria_mb=memoria_mb,
                    fonte="nessuna", argv=argv[:1])
        raise SandboxMemoriaEsaurita(
            f"il codice e' stato ucciso dal sistema (segnale, rc={rc}) e non "
            f"ho potuto leggere il contatore del kernel per confermarlo: il "
            f"tetto di memoria era {memoria_mb} MB, ed e' la causa di gran "
            f"lunga piu' probabile"
        )
