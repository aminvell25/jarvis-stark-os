"""`jarvis doctor` — diagnosi dei sottosistemi. SPEC §16.1b.

§16.1b lo vuole **in Fase 1, non alla fine**: con core, T1, Deepgram, Vosk,
Electron e socket in gioco, rispondere a "cosa e' rotto" senza uno strumento
e' penoso, e lo strumento va costruito prima di averne bisogno.

Due regole che questo modulo si impone.

**Ogni controllo misura.** Nessun valore segnaposto: §11.9 vale anche fuori
dalla UI. `SANDBOX` esegue davvero un processo isolato, perche' verificare la
presenza dell'eseguibile direbbe "ok" su un kernel che vieta gli user
namespace — ed e' esattamente il caso che questo strumento esiste per scoprire.

Questo modulo non nomina alcuno strumento di piattaforma: chiede a
`platform.sandbox_runner().describe()` di descriversi (invariante 29).

**Cio' che non esiste ancora si dichiara `n/d`, non si tace.** Uno strumento
diagnostico che salta un sottosistema e' indistinguibile da uno che lo
dichiara sano.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from core.platform import Paths, gpu as platform_gpu, paths as platform_paths
from core.settings import SECRETS, SETTINGS_FILENAME, SettingsError, load_settings

Stato = Literal["ok", "warn", "fail", "n/d"]


@dataclass(frozen=True)
class Check:
    nome: str
    stato: Stato
    dettaglio: str


def _fmt_gib(b: int) -> str:
    return f"{b / 2**30:.1f} GB"


async def _snapshot(paths: Paths, timeout: float = 2.0) -> dict | None:
    """Lo `state.snapshot` dal core in esecuzione, `None` se non risponde."""
    from websockets.asyncio.client import unix_connect

    sock = paths.socket_path()
    if not sock.exists():
        return None
    try:
        async with unix_connect(str(sock)) as ws:
            return json.loads(await asyncio.wait_for(ws.recv(), timeout))
    except Exception:
        return None


async def _check_sandbox() -> Check:
    """Esegue davvero un processo isolato.

    Non un controllo di presenza del binario: su un kernel che vieta gli user
    namespace il binario c'e' e la sandbox non parte, ed e' esattamente il
    caso che questo strumento esiste per scoprire.
    """
    import tempfile

    from core.platform import sandbox_runner
    from core.sandbox.runner import Profilo, run_sandboxed

    try:
        with tempfile.TemporaryDirectory(prefix="jdoc-") as d:
            radice = Path(d).resolve()
            rc, _, err = await run_sandboxed(
                # `STRUMENTO`: il doctor invoca un binario dell'host e deve
                # poterlo vedere. Il profilo si dichiara sempre (ADR-008).
                ["/bin/true"], [radice], [radice], timeout=10,
                profilo=Profilo.STRUMENTO,
            )
    except FileNotFoundError as exc:
        return Check("SANDBOX", "fail", f"eseguibile assente: {exc.filename or exc}")
    except Exception as exc:
        return Check("SANDBOX", "fail", f"{type(exc).__name__}: {exc}")

    if rc != 0:
        primo = err.strip().splitlines()[0][:60] if err.strip() else "nessun dettaglio"
        return Check("SANDBOX", "fail", f"esce con {rc}: {primo}")

    descrizione = sandbox_runner([]).describe()
    stato: Stato = "ok" if "NON applicato" not in descrizione else "warn"
    return Check("SANDBOX", stato, descrizione)


def _check_settings(paths: Paths) -> Check:
    f = paths.config_dir() / SETTINGS_FILENAME
    if not f.exists():
        return Check("SETTINGS", "fail", f"{f} assente — vedi INSTALLA.md §3")
    try:
        s = load_settings(paths)
    except SettingsError as exc:
        return Check("SETTINGS", "fail", str(exc)[:70])
    chiavi = sorted(s.secrets.present())
    privato = paths.is_private(f)
    return Check(
        "SETTINGS", "ok" if privato else "warn",
        f"{'permessi privati' if privato else 'PERMESSI LARGHI'}, "
        f"chiavi: {', '.join(chiavi) if chiavi else 'nessuna'}",
    )


def _check_unit() -> Check:
    """La unit INSTALLATA e' quella del repository?

    ⚠️ **Non e' una domanda teorica, ed e' capitata DUE volte, nei due versi.**

    La prima: la copia in `~/.config/systemd/user/` era del 19 agosto e diceva
    `RestartPreventExitStatus=41`, mentre il repository era passato a `41 42`.
    Con la copia vecchia systemd avrebbe riavviato in cerchio.

    La seconda, il **28 agosto 2026**: la decisione di restare vivi in
    `degraded_llm` ha tolto il 42 dal repository, e per un'ora e' stata la copia
    INSTALLATA a portare una regola che nel repository non esisteva piu'. Questo
    controllo ha detto `fail`, il Signore ha eseguito `packaging/installa.sh`, e
    le due impronte sono tornate a coincidere. **Storia chiusa.**

    ⚠️ **E la nota che stava qui prima e' stata falsa due volte in un'ora.**
    Diceva «il repository dice `41 42`» — falso appena il 42 e' uscito — e poi
    «la copia installata risponde ancora `41 42`» — falso quattordici minuti
    dopo, cioe' appena qualcuno ha reinstallato. Una misura scritta al presente
    invecchia mentre la si scrive: quello che va fissato qui e' la REGOLA, non
    lo stato della macchina di stamattina.

    La regola: il confronto e' sull'impronta dell'**intero file** e non su una
    riga. Basta un byte, anche di commento, e questo controllo dice `fail` — ed
    e' voluto, perche' chi legge un `fail` va a guardare il diff.

    `tests/test_supervisor.py` verifica la stessa riga e resta verde: legge il
    file del REPOSITORY. Il repository non e' la macchina, e questa differenza
    non ha un test perche' non e' una proprieta' del codice — e' uno stato
    dell'installazione. Percio' sta qui.
    """
    import hashlib

    repo = Path(__file__).resolve().parent.parent / "packaging" / "jarvis-core.service"
    installata = Path.home() / ".config" / "systemd" / "user" / "jarvis-core.service"
    if not repo.exists():
        return Check("UNIT", "warn", "packaging/jarvis-core.service assente")
    if not installata.exists():
        return Check("UNIT", "warn",
                     "non installata — packaging/installa.sh")
    a = hashlib.sha256(repo.read_bytes()).hexdigest()[:8]
    b = hashlib.sha256(installata.read_bytes()).hexdigest()[:8]
    if a == b:
        return Check("UNIT", "ok", f"installata e allineata ({a})")
    return Check(
        "UNIT", "fail",
        f"INSTALLATA VECCHIA: repo {a}, installata {b} — "
        "reinstalla con packaging/installa.sh",
    )


def _check_persona(paths: Paths) -> Check:
    """La persona INSTALLATA e' quella del repository? — §5.7.

    Stessa forma di `_check_unit()`, e per la stessa ragione: la copia che
    parla vive in `~/.config/jarvis-os/` e **non ha storia git**. Nessun test
    puo' guardarla — `tests/conftest.py` spiega perche' un test che legge
    `~/.config/` passa o fallisce a seconda della macchina — quindi la guarda
    questo.

    ⚠️ Non e' teorica. Il 26 agosto 2026 §5.7 trascriveva il testo della
    persona e la trascrizione era **gia' divergente** dal file spedito: «e'
    piu'» contro «è più». §5.7 adesso rimanda al file invece di copiarlo, e
    resta questa terza copia da sorvegliare.
    """
    import hashlib

    repo = Path(__file__).resolve().parent.parent / "config" / "voice-persona.md"
    installata = paths.config_dir() / "voice-persona.md"
    if not installata.exists():
        return Check("PERSONA", "warn",
                     f"assente in {installata}: T1 parte senza persona")
    if not repo.exists():                                   # pragma: no cover
        return Check("PERSONA", "warn", "il repository non ha config/voice-persona.md")
    a = hashlib.sha256(repo.read_bytes()).hexdigest()[:12]
    b = hashlib.sha256(installata.read_bytes()).hexdigest()[:12]
    if a == b:
        return Check("PERSONA", "ok", f"identica al repository ({a})")
    return Check("PERSONA", "FAIL",
                 f"DIVERSA dal repository: repo {a}, installata {b}. "
                 f"E' la copia installata che parla.")


def _check_ws(paths: Paths, snap: dict | None) -> Check:
    sock = paths.socket_path()
    if snap is None:
        return Check("WS", "fail", f"nessuna risposta su {sock}")
    # La riservatezza della directory la giudica la piattaforma: su POSIX sono
    # i bit di modo, su Windows saranno le ACL (invariante 29).
    privata = paths.is_private(sock.parent)
    clients = snap.get("ws", {}).get("clients", "?")
    suffisso = "" if privata else "  ATTENZIONE: la directory e' la difesa (§18.2)"
    return Check("WS", "ok" if privata else "warn",
                 f"unix {sock.name}, dir "
                 f"{'privata' if privata else 'ACCESSIBILE AD ALTRI'}, "
                 f"{clients} client{suffisso}")


def _check_core(snap: dict | None) -> Check:
    if snap is None:
        return Check("CORE", "fail", "non in esecuzione (`python -m core.engine`)")
    c = snap.get("core", {})
    up = c.get("uptime_s", 0)
    return Check("CORE", "ok", f"pid {c.get('pid', '?')}, uptime {up:.0f}s, fase {snap.get('fase', '?')}")


def _check_vram(snap: dict | None) -> Check:
    g = (snap or {}).get("gpu") or None
    if g is None:
        m = platform_gpu().memory()
        if m is None:
            return Check("VRAM", "n/d", "nessuna GPU leggibile su questa piattaforma")
        g = {"driver": m.driver, "total_bytes": m.total, "used_bytes": m.used,
             "unified": m.unified, "headroom_bytes": m.free}
    unif = " (memoria unificata: headroom = min con la RAM)" if g["unified"] else ""
    return Check("VRAM", "ok",
                 f"{_fmt_gib(g['used_bytes'])}/{_fmt_gib(g['total_bytes'])} "
                 f"{g['driver']}, headroom {_fmt_gib(g['headroom_bytes'])}{unif}")


def _check_t1(snap: dict | None, imp) -> Check:
    """§16.1b riga «T1 claude».

    Spento e rotto non sono la stessa cosa, ed e' l'unica distinzione che conta
    qui: un T1 assente perche' `voice.enabled = false` e' una configurazione,
    non un guasto, e uno strumento che li confondesse manderebbe qualcuno a
    cercare un problema che non c'e'.
    """
    v = (snap or {}).get("voce")
    if v is None:
        acceso = bool(imp and imp.voice.enabled)
        return Check("T1 claude", "n/d" if not acceso else "fail",
                     "core non in esecuzione" if acceso
                     else "voce spenta (voice.enabled = false)")
    if not v["abilitata"]:
        return Check("T1 claude", "n/d", "voce spenta (voice.enabled = false)")
    if not v["t1_vivo"]:
        return Check("T1 claude", "fail", "voce accesa ma sessione non viva")
    return Check("T1 claude", "ok", "sessione persistente viva")


#: Come si CHIAMA il guasto, per ciascuna causa di degradazione — e l'etichetta
#: della riga che lo mostra.
#:
#: ⚠️ **Erano cablate**: `Check("T1 auth", "fail", f"sessione scaduta (...)")`
#: per QUALUNQUE `degraded_llm`. Dopo tre cadute non-auth `jarvis doctor`
#: stampava «[fail] T1 auth: sessione scaduta (riavvii_ripetuti)» — nome del
#: guasto sbagliato, ed etichetta sbagliata, sulla riga che questo file chiama
#: da se' «la piu' importante dello strumento».
#:
#: Era latente finche' un `degraded_llm` non-auth era un preludio all'uscita del
#: processo. **La decisione del 28 agosto 2026 — restare vivi — lo rende uno
#: stato in cui si RESTA**, e quindi uno che si legge davvero.
#:
#: Allowlist: una causa che non e' qui non prende il nome di un'altra.
CAUSE_T1: dict[str, tuple[str, str]] = {
    "auth_expired": ("T1 auth", "sessione scaduta"),
    "riavvii_ripetuti": ("T1 sessione", "la sessione cade e ricade"),
}


def _check_auth(snap: dict | None) -> Check:
    """§16.1b riga «T1 auth», e §5.6.

    E' la riga piu' importante dello strumento: quando il token scade, e'
    l'unica che dice cosa fare. E allora deve anche dire la cosa GIUSTA: vedi
    `CAUSE_T1`, e `Supervisore.AZIONI` per l'altra meta'.
    """
    a = ((snap or {}).get("voce") or {}).get("auth")
    if a is None:
        return Check("T1 auth", "n/d", "core non in esecuzione")
    if a["stato"] == "degraded_llm":
        etichetta, guasto = CAUSE_T1.get(a["motivo"], ("T1 sessione", "degradata"))
        coda = f" — {a['azione']}" if a["azione"] else ""
        return Check(etichetta, "fail", f"{guasto} ({a['motivo']}){coda}")
    return Check("T1 auth", "ok", f"nessuna scadenza rilevata, {a['riavvii']} riavvii di T1")


def _check_provider(imp, quale: str) -> Check:
    """§16.1b righe «STT» e «TTS». Si legge dalle impostazioni: e' li' che la
    scelta e' scritta, e il ripiego di §7 la cambia a runtime ANNUNCIANDOLO."""
    if imp is None:
        return Check(quale.upper(), "n/d", "impostazioni non leggibili")
    scelto = getattr(imp.voice, f"{quale}_provider")
    ripiego = getattr(imp.voice, f"fallback_{quale}")
    chiave = "deepgram_api_key" in imp.secrets.present()
    if scelto == "deepgram" and not chiave:
        return Check(quale.upper(), "warn",
                     f"deepgram richiesto ma la chiave manca: parte in {ripiego} e lo annuncia")
    return Check(quale.upper(), "ok", f"{scelto}, ripiego {ripiego}")


def _check_wake(snap: dict | None, imp) -> Check:
    """§16.1b riga «WAKE». Il modello Vosk e' un file: o c'e' o non c'e'."""
    v = (snap or {}).get("voce") or {}
    modello = Path(v.get("wake_model") or (imp.voice.wake.model if imp else ""))
    frasi = v.get("wake_frasi", len(imp.voice.wake.phrases) if imp else 0)
    if not str(modello):
        return Check("WAKE", "n/d", "nessun modello configurato")
    if not modello.exists():
        return Check("WAKE", "warn",
                     f"modello assente in {modello}: si scarica al primo avvio della voce")
    return Check("WAKE", "ok", f"vosk in {modello.name}, {frasi} frasi")


async def _check_codice(snap: dict | None, imp) -> Check:
    """ADR-009. La riga che l'utente ha chiesto: **il tetto si applica davvero?**

    Un limite che non si applica perche' manca un binario e' peggio di nessun
    limite, perche' chi ha scritto `code.memory_mb = 512` crede di averlo. Qui
    non si guarda se `systemd-run` esiste: si fa allocare della memoria oltre
    il tetto e si guarda se qualcuno la ferma. E' la stessa regola di
    `_check_sandbox` — ogni controllo MISURA.
    """
    from core.platform.linux_sandbox import limite_mancante
    from core.sandbox.runner import Profilo, SandboxMemoriaEsaurita, run_sandboxed

    c = (snap or {}).get("codice")
    acceso = c["acceso"] if c else bool(imp and imp.code.enabled)
    tetto = c["memoria_mb"] if c else (imp.code.memory_mb if imp else 512)
    cpu = c["cpu_percento"] if c else (imp.code.cpu_percent if imp else 50)

    perche = limite_mancante()
    if perche is not None:
        # `fail` anche a tool spento: acceso domani, girerebbe senza tetto.
        return Check("CODICE", "fail", f"tetti NON applicabili: {perche}")

    if c is not None and c["impostazione"] != c["acceso"]:
        return Check("CODICE", "warn",
                     f"code.enabled = {c['impostazione']} ma nell'allowlist "
                     f"e' {c['acceso']}: la registrazione non si ricarica a "
                     f"caldo, riavviare il core")

    # La prova vera: un frammento che chiede il doppio del tetto.
    quanto = int(tetto) * 2
    sorgente = (f"b=bytearray({quanto}*1024*1024)\n"
                f"[b.__setitem__(i,1) for i in range(0,len(b),4096)]\n"
                f"print('NON FERMATO')")
    try:
        rc, out, _ = await run_sandboxed(
            ["/usr/bin/python3", "-I", "-S", "-c", sorgente], [], [],
            timeout=20, profilo=Profilo.CODICE, lavoro_mb=8,
            memoria_mb=int(tetto), cpu_percento=int(cpu),
        )
    except SandboxMemoriaEsaurita:
        stato: Stato = "ok" if acceso else "n/d"
        return Check("CODICE", stato,
                     f"{'nell allowlist' if acceso else 'spento (code.enabled = false)'}, "
                     f"tetto {tetto} MB VERIFICATO fermando {quanto} MB, cpu {cpu}%")
    except Exception as exc:
        return Check("CODICE", "fail", f"{type(exc).__name__}: {str(exc)[:60]}")
    return Check("CODICE", "fail",
                 f"{quanto} MB allocati SENZA essere fermati (rc={rc}, "
                 f"{out.strip()[:20]}): il tetto di {tetto} MB non morde")


def _check_quota(snap: dict | None) -> Check:
    """§16.1b riga «QUOTA», dal Governor (§5.4)."""
    q = (snap or {}).get("quota")
    if q is None:
        return Check("QUOTA", "n/d", "core non in esecuzione")
    stato = "warn" if q["restanti"] <= 2 or q["sospeso"] else "ok"
    sosp = f", SOSPESO {q['riprova_fra_s']:.0f}s" if q["sospeso"] else ""
    return Check("QUOTA", stato,
                 f"{q['usati_nella_finestra']}/{q['max_per_finestra']} spawn T2 "
                 f"nella finestra, {q['attivi']} attivi{sosp}")


async def run_checks(paths: Paths | None = None) -> list[Check]:
    p = paths or platform_paths()
    snap = await _snapshot(p)

    # Le impostazioni si leggono anche a core spento: STT, TTS e WAKE si
    # possono diagnosticare senza che il servizio giri, ed e' proprio quando
    # non gira che qualcuno lo chiede.
    try:
        from core.settings import load_settings
        imp = load_settings(p)
    except Exception:
        imp = None

    return [
        _check_core(snap),
        _check_ws(p, snap),
        _check_settings(p),
        _check_unit(),
        _check_persona(p),
        await _check_sandbox(),
        _check_vram(snap),
        _check_t1(snap, imp),
        _check_auth(snap),
        _check_provider(imp, "stt"),
        _check_provider(imp, "tts"),
        _check_wake(snap, imp),
        _check_quota(snap),
        await _check_codice(snap, imp),
    ]


def render(checks: list[Check]) -> str:
    larghezza = max(len(c.nome) for c in checks)
    righe = [
        f"{c.nome:<{larghezza}}  {c.stato.upper():<5}  {SECRETS.scrub(c.dettaglio)}"
        for c in checks
    ]
    return "\n".join(righe)


def exit_code(checks: list[Check]) -> int:
    """0 se nulla e' rotto. `n/d` non e' un guasto: e' una fase futura."""
    return 1 if any(c.stato == "fail" for c in checks) else 0


async def main() -> int:
    checks = await run_checks()
    print(render(checks))
    return exit_code(checks)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
