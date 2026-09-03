"""Il laboratorio — ADR-015. Dove JARVIS e il proprietario costruiscono oggetti.

## Che cos'e'

Una cartella del proprietario, `laboratorio.radice` (di serie
`~/JARVIS/laboratorio/`), sotto le radici consentite. Dentro, **due zone**:

    <radice>/                 del proprietario: nessun processo di JARVIS
                              la scrive, mai
    <radice>/bozze/<nome>/    di una bozza: T2 ci scrive uno script, e
                              `esegui_bozza` — con la conferma di §6.2 — lo
                              esegue in sandbox con QUELLA directory come
                              unico percorso scrivibile

Promuovere una bozza a pezzo definitivo e' `move_path` dell'allowlist, con la
sua conferma: non esiste una strada automatica dalla seconda zona alla prima.

## Perche' «vietato» era la parola sbagliata

`CLAUDE.md` mette «eseguire stringhe generate dall'LLM» fra le cose da **non
fare senza chiedere**, e ADR-006 dice «solo in sandbox». Non e' un divieto:
e' una conferma piu' una sandbox. Questo tool e' esattamente quello — un
piano con lo script risolto, l'interprete e la directory scrivibile mostrati
al proprietario, e poi `Profilo.LABORATORIO`. Il proprietario l'ha detto il 3
settembre 2026: «se dico a JARVIS di farlo, lui lo fa».

## Chi scrive, chi esegue, chi verifica

Tre ruoli, tre codici diversi, ed e' la forma di ADR-012:

    scrive      Claude Code con `llm.laboratorio_model` (opus), sotto
                `Profilo.AGENTE`: la bozza e' l'unica directory scrivibile
    esegue      questo tool, sotto `Profilo.LABORATORIO`, dopo la conferma
    verifica    `core/model3d/stl_lettore.py` — struct e numpy sul FORMATO,
                non lo script che ha scritto il file

La bozza dichiara che cosa produce in `bozza.json`; il verificatore va a
guardare se quei file ci sono e sono STL binari che tornano coi conti. Uno
script che dichiara `staffa.stl` e scrive `staffa.txt` e' `FALLITO`, non
«eseguito».
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from core.llm.untrusted import Untrusted
from core.model3d import stl_lettore
from core.model3d.parametrico import Modello, ModelloNonValido
from core.paths_policy import PathFuoriRadice, risolvi_sotto_radici
from core.sandbox.runner import (Profilo, SandboxMemoriaEsaurita,
                                 SandboxTimeout, run_sandboxed)
from core.tools.code import tronca
from core.tools.confirm import Operazione, Piano
from core.tools.model3d import TOPIC as TOPIC_ANTEPRIMA
from core.tools.registry import Tool, ToolResult, register
from core.verifica import Verifica

log = structlog.get_logger(__name__)

#: La sottocartella delle bozze, dentro la radice. E' l'unica che JARVIS scrive.
BOZZE = "bozze"
#: Il manifesto della bozza: che cosa esegue e che cosa dichiara di produrre.
MANIFESTO = "bozza.json"
#: L'origine nel marcatore `<untrusted_source>` dello stdout.
ORIGINE = "script del laboratorio"
#: Un nome di bozza o di file: niente separatori, niente `..`, niente spazi.
#: E' una regola sul NOME, e il percorso lo compone il core — l'LLM non passa
#: mai un percorso, come per `genera_modello` (invariante 34).
NOME = r"^[a-z0-9][a-z0-9._-]{0,79}$"
_NOME = re.compile(NOME)
#: Un nome di FILE nel manifesto: come sopra, ma con le maiuscole. Il nome
#: della bozza lo compone il core, minuscolo; il nome del file lo sceglie chi
#: scrive lo script, e il primo distanziale dal vivo si chiamava
#: `distanziale_10x6_M3.stl` — rifiutato per una `M`, cioe' per niente.
NOME_FILE = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"
_NOME_FILE = re.compile(NOME_FILE)
#: I flag dell'interprete. `-I` isola dall'ambiente — che e' gia' vuoto, per
#: `--clearenv` — e dalla cwd nel path; NON `-S`, perche' il venv serve.
FLAGS_INTERPRETE = ("-I",)
#: I tool di Claude Code quando scrive una bozza. Senza `Bash`: non deve
#: eseguire niente, lo esegue `esegui_bozza` dopo la conferma. ⚠️ Non e' un
#: confine (vedi `core/llm/claude_t2.py`): il confine e' `Profilo.AGENTE`.
TOOL_AGENTE = "Read,Write,Edit,Glob,Grep"


class ManifestoNonValido(ValueError):
    """`bozza.json` manca o non dice cio' che deve."""


class Manifesto(BaseModel):
    """Cio' che una bozza dichiara. Lo scrive T2 o il proprietario; lo legge
    il planner per mostrarlo e il verificatore per confrontarlo."""

    model_config = ConfigDict(extra="forbid")

    script: str = "genera.py"
    produce: list[str] = Field(min_length=1, max_length=16)
    richiesta: str = ""

    @field_validator("script")
    @classmethod
    def _script(cls, v: str) -> str:
        if not _NOME_FILE.match(v) or not v.endswith(".py"):
            raise ValueError(f"script {v!r}: un nome di file .py, senza percorso")
        return v

    @field_validator("produce")
    @classmethod
    def _produce(cls, v: list[str]) -> list[str]:
        for nome in v:
            # Solo STL, per ora: e' l'unico formato che il verificatore sa
            # rileggere. Un prodotto che non si puo' verificare non si
            # dichiara — si scrive lo stesso, e compare fra i `prodotti`.
            if not _NOME_FILE.match(nome) or not nome.endswith(".stl"):
                raise ValueError(f"produce {nome!r}: un nome di file .stl, senza percorso")
        return v


class BozzaArgs(BaseModel):
    """Cio' che l'LLM (o la radice) puo' chiedere: il NOME di una bozza.
    Nessun percorso, nessuno script, nessun interprete: li dice il manifesto,
    e li mostra il piano."""

    model_config = ConfigDict(extra="forbid")

    bozza: str = Field(pattern=NOME)
    timeout_s: float = Field(default=60.0, gt=0.0)


def etichetta(richiesta: str) -> str:
    """«una staffa per un servo SG90» -> `staffa-per-un-servo-sg90`."""
    parole = re.sub(r"[^a-z0-9]+", "-", richiesta.lower()).strip("-")
    # Articoli e preposizioni in testa, finche' ce ne sono: «della staffa»,
    # «il distanziale», «di una staffa» sono la stessa etichetta di «staffa».
    for _ in range(3):
        parole = re.sub(r"^(?:una?|un|l|il|lo|la|gli|le|i|della|del|dello|dei|delle|degli|di)-",
                        "", parole)
    return (parole[:40].rstrip("-") or "bozza")


def parlato(nome: str) -> str:
    """`2026-09-03-staffa-per-un-servo-sg90` -> «staffa per un servo sg90».
    La data e i trattini sono per il disco; a voce si dice l'etichetta."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", nome).replace("-", " ")


def fotografia(radice: Path, escludi: Path | None = None) -> dict[str, tuple[int, int]]:
    """Ogni file sotto `radice` con dimensione e mtime. E' la misura della
    regola delle due zone: prima e dopo, e la differenza e' cio' che e' stato
    toccato. `escludi` e' la bozza, che invece DEVE cambiare."""
    fuori: dict[str, tuple[int, int]] = {}
    for cartella, sotto, file in os.walk(radice):
        c = Path(cartella)
        if escludi is not None and (c == escludi or escludi in c.parents):
            sotto[:] = []
            continue
        for f in file:
            p = c / f
            try:
                st = p.lstat()
            except OSError:
                continue
            fuori[str(p.relative_to(radice))] = (st.st_size, st.st_mtime_ns)
    return fuori


def differenze(prima: dict[str, tuple[int, int]],
               dopo: dict[str, tuple[int, int]]) -> list[str]:
    """I nomi aggiunti, cambiati o tolti. Ordinati: finiscono in un referto."""
    return sorted(set(k for k in dopo if prima.get(k) != dopo[k])
                  | set(k for k in prima if k not in dopo))


class Laboratorio:
    """La cartella, e le regole sui nomi. Le impostazioni per funzione, come
    per gli altri tool: la radice si rilegge a ogni uso."""

    def __init__(self, leggi_settings: Callable[[], Any],
                 radici: Callable[[], list[Path]]) -> None:
        self._leggi = leggi_settings
        self.radici = radici

    def radice(self) -> Path:
        """Risolta SOTTO le radici consentite, o `PathFuoriRadice`."""
        return risolvi_sotto_radici(Path(self._leggi().laboratorio.radice),
                                    list(self.radici()))

    def bozze(self) -> Path:
        return self.radice() / BOZZE

    def percorso_bozza(self, nome: str) -> Path:
        if not _NOME.match(nome):
            raise ValueError(f"nome di bozza non ammesso: {nome!r}")
        p = self.bozze() / nome
        if p.resolve().parent != self.bozze().resolve():
            raise ValueError(f"la bozza {nome!r} non sta in {self.bozze()}")
        return p

    def nuova_bozza(self, richiesta: str, quando: float | None = None) -> Path:
        """`bozze/<data>-<etichetta>/`, mai sovrascritta: se esiste, `-2`."""
        giorno = time.strftime("%Y-%m-%d", time.localtime(
            time.time() if quando is None else quando))
        base = f"{giorno}-{etichetta(richiesta)}"
        self.bozze().mkdir(parents=True, exist_ok=True)
        nome, n = base, 1
        while (self.bozze() / nome).exists():
            n += 1
            nome = f"{base}-{n}"
        p = self.bozze() / nome
        p.mkdir()
        return p

    def trova_bozza(self, quale: str | None = None) -> Path | None:
        """L'ultima bozza toccata, o la piu' recente il cui nome contiene
        `quale` — normalizzato come un'etichetta, perche' e' cosi' che i nomi
        sono stati scritti. «Toccata» e' l'mtime della cartella: una bozza
        appena eseguita e' l'ultima, ed e' quella che si vuole rilanciare."""
        b = self.bozze()
        if not b.is_dir():
            return None
        candidate = sorted((p for p in b.iterdir() if p.is_dir() and _NOME.match(p.name)),
                           key=lambda p: p.stat().st_mtime, reverse=True)
        if quale and quale.strip():
            chiave = etichetta(quale)
            candidate = [p for p in candidate if chiave in p.name]
        return candidate[0] if candidate else None

    def leggi_manifesto(self, bozza: Path) -> Manifesto:
        p = bozza / MANIFESTO
        try:
            return Manifesto.model_validate(json.loads(p.read_text(encoding="utf-8")))
        except FileNotFoundError:
            raise ManifestoNonValido(f"manca {p}") from None
        except (OSError, ValueError, ValidationError) as exc:
            raise ManifestoNonValido(f"{p}: {exc}") from exc

    @staticmethod
    def interprete() -> Path:
        """L'interprete di JARVIS, venv compreso: e' cosi' che lo script trova
        `numpy` e `trimesh`. `Profilo.LABORATORIO` sa montare un venv."""
        return Path(sys.executable)


#: Le librerie opzionali di trimesh che cambiano che cosa si puo' costruire.
#: Si SONDANO, non si dichiarano: il primo giro dal vivo e' caduto su
#: `ModuleNotFoundError: manifold3d` perche' il prompt prometteva le booleane
#: e il venv non le aveva. Un prompt che elenca librerie a memoria e' un
#: prompt che mente alla prima dipendenza mancante.
_OPZIONALI = (
    ("manifold3d", "booleane (`trimesh.boolean.union/difference`, engine='manifold')"),
    ("shapely", "poligoni 2D ed estrusioni (`trimesh.creation.extrude_polygon`)"),
    ("scipy", "hull convessi e `trimesh.smoothing`"),
    ("networkx", "grafi delle facce (`mesh.split`, `facets`)"),
)


def librerie_disponibili() -> tuple[list[str], list[str]]:
    """`(presenti, assenti)` fra le opzionali, misurate nell'interprete che
    lo script usera' — che e' questo stesso venv (`Laboratorio.interprete`)."""
    presenti, assenti = [], []
    for modulo, uso in _OPZIONALI:
        (presenti if importlib.util.find_spec(modulo) else assenti).append(f"{modulo}: {uso}")
    return presenti, assenti


#: Come si dice a voce (o sul pannello) che cosa fa Claude Code con i suoi
#: tool. Sono i quattro di `TOOL_AGENTE` piu' `Bash`, che non c'e' ma potrebbe
#: comparire — e allora si vede, invece di sparire in un «usa Bash».
_VERBI_DEI_TOOL = {"Write": "scrive", "Edit": "modifica", "Read": "legge",
                   "Glob": "cerca", "Grep": "cerca", "Bash": "ESEGUE"}
#: Quanto testo di una riga del cervello finisce nel diario. Il modello
#: ragiona a paragrafi; il pannello mostra righe.
MAX_RIGA = 600


def righe_del_cervello(evento: Any) -> list[str]:
    """Le righe da mostrare per un evento del flusso di Claude Code.

    Solo dagli eventi `assistant`: il testo che il modello scrive fra un passo
    e l'altro, e i tool che chiama — «scrive genera.py», «legge BOZZA.md». E'
    cio' che il «desktop Stark» chiama il cervello sullo schermo uno, con dati
    veri (invariante 23): non una barra di avanzamento inventata, ma gli
    eventi che il processo emette davvero.
    """
    dato = getattr(evento, "dato", None) or {}
    if getattr(evento, "tipo", None) != "assistant":
        return []
    righe: list[str] = []
    for blocco in dato.get("message", {}).get("content", []) or []:
        tipo = blocco.get("type")
        if tipo == "text":
            testo = " ".join(str(blocco.get("text", "")).split())
            if testo:
                righe.append(testo if len(testo) <= MAX_RIGA else testo[:MAX_RIGA - 1] + "…")
        elif tipo == "tool_use":
            nome = str(blocco.get("name", "?"))
            ingresso = blocco.get("input") or {}
            bersaglio = (ingresso.get("file_path") or ingresso.get("pattern")
                         or ingresso.get("command") or "")
            bersaglio = Path(str(bersaglio)).name if ingresso.get("file_path") else str(bersaglio)
            verbo = _VERBI_DEI_TOOL.get(nome, f"usa {nome}")
            righe.append(f"{verbo} {bersaglio}".strip() if bersaglio else f"{verbo}")
    return righe


def compito_per_t2(richiesta: str, bozza: Path) -> str:
    """Il prompt di chi SCRIVE. Dice le regole della zona, non le ripete il
    kernel: il kernel le impone. E dice **che cosa c'e'** nell'interprete,
    sondato adesso, non ricordato."""
    presenti, assenti = librerie_disponibili()
    con = ("Librerie opzionali PRESENTI: " + "; ".join(presenti) + ".\n") if presenti else ""
    senza = ("Librerie opzionali ASSENTI — non importarle e non usare le funzioni "
             "di trimesh che le richiedono: " + "; ".join(assenti) + ".\n"
             ) if assenti else ""
    # I consigli seguono le assenze UNA per una: il 3 settembre il paragrafo
    # «senza booleane si costruisce a mano» usciva anche quando mancavano solo
    # scipy e networkx, cioe' diceva il falso appena manifold3d era entrato.
    nomi_assenti = {a.split(":")[0] for a in assenti}
    if "manifold3d" in nomi_assenti:
        senza += ("Senza booleane, un foro o una sottrazione si fanno con un "
                  "profilo scritto a mano — vertici e facce in numpy "
                  "(`trimesh.Trimesh(vertices=..., faces=...)`) o "
                  "`trimesh.creation.extrude_triangulation` — oppure con le "
                  "primitive di `trimesh.creation` (box, cylinder, annulus, cone, "
                  "icosphere, capsule) e `trimesh.util.concatenate`.\n")
    elif "shapely" in nomi_assenti:
        senza += ("Senza poligoni 2D, i profili si estrudono da una "
                  "triangolazione scritta a mano (`extrude_triangulation`).\n")
    else:
        senza += ("Con booleane e poligoni: profili 2D con `shapely` estrusi con "
                  "`trimesh.creation.extrude_polygon`, fori e tasche con "
                  "`trimesh.boolean.difference([...], engine='manifold')`, unioni "
                  "con `trimesh.boolean.union`. Dopo ogni booleana controlla "
                  "`is_watertight`.\n")
    return (
        f"Sei nel laboratorio di JARVIS, nella bozza {bozza}. La directory "
        f"corrente e' la bozza ed e' l'UNICA in cui puoi scrivere.\n\n"
        f"Richiesta del proprietario: «{richiesta}».\n\n"
        "Scrivi tre file, e nient'altro:\n"
        "1. `genera.py` — Python 3.12. Disponibili la libreria standard, "
        "`numpy` e `trimesh`. Niente rete, niente percorsi fuori dalla "
        "directory corrente, niente `input()`. Lavora in MILLIMETRI.\n"
        f"{con}{senza}"
        "Costruisci il solido, controlla `mesh.is_watertight` ed esci con "
        "codice 1 se non lo e', poi esporta con `mesh.export('<nome>.stl')` "
        "(STL binario) nella directory corrente. Stampa a video le misure "
        "d'ingombro in mm e il numero di triangoli.\n"
        "2. `bozza.json` — esattamente: {\"script\": \"genera.py\", "
        "\"produce\": [\"<nome>.stl\"], \"richiesta\": \"<la richiesta>\"}. "
        "`produce` elenca i file STL che `genera.py` scrive.\n"
        "3. `BOZZA.md` — in italiano: le misure scelte e perche', le ipotesi "
        "fatte dove la richiesta non diceva, e come va stampato (orientamento, "
        "supporti).\n\n"
        "Non eseguire niente: lo script lo esegue JARVIS dopo una conferma del "
        "proprietario. Non scrivere altri file. Rispondi con due frasi in "
        "italiano su che cosa hai progettato."
    )


def anteprima_di(stl: Path, bozza: str) -> tuple[dict[str, Any] | None, str]:
    """Il messaggio `model3d.preview` per uno STL, o `None` e il perche'.

    Una sorgente sola per le due meta' del laboratorio: il tool dopo
    un'esecuzione e l'osservatore quando il file cambia. Lo STL si rilegge
    col lettore del core e passa dal gate di `Modello`: oltre il tetto di
    vertici si DICE, non si decima (invariante 34).
    """
    try:
        pos, tri = stl_lettore.vertici(stl)
        d = pos.max(axis=0) - pos.min(axis=0)
        m = Modello(nome=stl.stem, versione=f"bozza {bozza}", params={},
                    posizioni=pos, triangoli=tri,
                    bbox=(float(d[0]), float(d[1]), float(d[2])))
    except (stl_lettore.StlIllegibile, ModelloNonValido, OSError) as exc:
        return None, f"{stl.name} non mostrata: {exc}"
    return ({"topic": TOPIC_ANTEPRIMA, "file": str(stl), **m.per_il_renderer()},
            f"{stl.name}: {m.vertici} vertici, {len(tri)} triangoli")


def register_laboratorio_tools(
    leggi_settings: Callable[[], Any],
    radici: Callable[[], list[Path]],
    pubblica: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> Laboratorio | None:
    """Registra `esegui_bozza` **se `laboratorio.enabled`** e se la radice sta
    sotto le radici consentite. Ritorna il `Laboratorio`, o `None`: spento, il
    tool non esiste — come `esegui_codice`."""
    s = leggi_settings().laboratorio
    if not bool(s.enabled):
        log.info("laboratorio_spento", motivo="laboratorio.enabled = false",
                 conseguenza="esegui_bozza non e' nell'allowlist")
        return None
    lab = Laboratorio(leggi_settings, radici)
    try:
        radice = lab.radice()
    except PathFuoriRadice as exc:
        # Fail-closed, e detto: una radice che il proprietario non ha messo
        # fra le consentite non si aggiunge da sola.
        log.error("laboratorio_fuori_dalle_radici", radice=str(s.radice),
                  errore=str(exc),
                  conseguenza="esegui_bozza non e' nell'allowlist: aggiungi la "
                              "radice a fs.allowed_roots")
        return None

    async def _piano(a: BozzaArgs) -> Piano:
        bozza = lab.percorso_bozza(a.bozza)
        if not bozza.is_dir():
            raise FileNotFoundError(f"la bozza non esiste: {bozza}")
        m = lab.leggi_manifesto(bozza)
        script = bozza / m.script
        if not script.is_file():
            raise FileNotFoundError(f"lo script dichiarato non c'e': {script}")
        py = lab.interprete()
        ops = [Operazione(
            tipo="esegui", sorgente=script, destinazione=bozza,
            dettaglio=(f"{py} {' '.join(FLAGS_INTERPRETE)} {m.script} in sandbox: "
                       f"radice vuota, senza rete, scrivibile SOLO {bozza}"))]
        for nome in m.produce:
            p = bozza / nome
            ops.append(Operazione(
                tipo="create", destinazione=p,
                dettaglio=("STL dichiarato dalla bozza; SOVRASCRIVE il file "
                           "esistente" if p.exists() else "STL dichiarato dalla bozza")))
        return Piano(tool="esegui_bozza",
                     riepilogo=(f"eseguo {m.script} nella bozza «{a.bozza}» in "
                                f"sandbox, per produrre {', '.join(m.produce)}"),
                     operazioni=tuple(ops))

    async def _anteprima(bozza: Path, prodotti: list[Path]) -> str:
        """La prima STL prodotta va al pannello, se il gate la accetta."""
        if pubblica is None:
            return "nessun pannello collegato"
        for p in prodotti:
            if not p.is_file():
                continue
            messaggio, esito = anteprima_di(p, bozza.name)
            if messaggio is None:
                return esito
            try:
                await pubblica(messaggio)
            except Exception as exc:                        # noqa: BLE001
                log.warning("anteprima_non_pubblicata", errore=repr(exc))
                return f"{p.name} non pubblicata: {type(exc).__name__}"
            return esito
        return "nessun STL prodotto"

    async def _esegui(a: BozzaArgs, piano: Piano) -> ToolResult:
        s = leggi_settings().laboratorio
        bozza = piano.operazioni[0].destinazione
        script = piano.operazioni[0].sorgente
        dichiarati = [op.destinazione for op in piano.operazioni if op.tipo == "create"]
        concesso = min(float(a.timeout_s), float(s.max_timeout_s))
        limitato = concesso < float(a.timeout_s)

        prima_bozza = fotografia(bozza)
        prima_fuori = fotografia(radice, escludi=bozza)
        try:
            rc, out, err = await run_sandboxed(
                [str(lab.interprete()), *FLAGS_INTERPRETE, script.name],
                rw_paths=[bozza],
                allowed_roots=list(lab.radici()),
                timeout=concesso,
                profilo=Profilo.LABORATORIO,
                chdir=bozza,
                lavoro_mb=int(s.tmpfs_mb),
                memoria_mb=int(s.memory_mb),
                cpu_percento=int(s.cpu_percent),
            )
        except SandboxTimeout:
            return ToolResult(ok=False,
                              error=f"lo script non e' terminato entro {concesso:g}s "
                                    "ed e' stato ucciso",
                              output={"bozza": str(bozza), "timeout_s": concesso,
                                      "timeout_limitato": limitato})
        except SandboxMemoriaEsaurita as exc:
            return ToolResult(ok=False, error=str(exc),
                              output={"bozza": str(bozza), "memoria_mb": int(s.memory_mb)})
        except Exception as exc:                            # noqa: BLE001
            log.warning("bozza_non_eseguita", errore=str(exc)[:200])
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")

        prodotti = differenze(prima_bozza, fotografia(bozza))
        fuori = differenze(prima_fuori, fotografia(radice, escludi=bozza))
        if fuori:
            # Non deve poter succedere: la sandbox monta scrivibile la sola
            # bozza. Se succede e' un guasto della sandbox, e si dice cosi'.
            log.error("laboratorio_fuori_dalla_bozza", bozza=str(bozza), fuori=fuori)
            return ToolResult(ok=False,
                              error="la sandbox ha toccato file FUORI dalla bozza, "
                                    f"e non doveva poterlo fare: {fuori}",
                              output={"bozza": str(bozza), "fuori": fuori})

        tetto = int(s.max_output_kb) * 1024
        stdout, tolti_out = tronca(out, tetto)
        stderr, tolti_err = tronca(err, tetto)
        misure: dict[str, Any] = {}
        for p in dichiarati:
            try:
                letto = stl_lettore.leggi(p)
            except (OSError, stl_lettore.StlIllegibile):
                continue
            misure[p.name] = {"triangoli": letto.triangoli,
                              "bbox_mm": list(letto.dimensioni_mm()),
                              "bytes": letto.byte}
        anteprima = await _anteprima(bozza, dichiarati) if rc == 0 else "script fallito"
        log.info("bozza_eseguita", bozza=bozza.name, rc=rc, prodotti=prodotti,
                 anteprima=anteprima)
        return ToolResult(
            ok=rc == 0,
            output={
                "bozza": str(bozza), "returncode": rc,
                "prodotti": prodotti, "misure": misure, "anteprima": anteprima,
                "untrusted": True,
                "stdout": Untrusted.da(ORIGINE, stdout).avvolto(),
                "stderr": Untrusted.da(ORIGINE, stderr).avvolto(),
                "stdout_troncato_byte": tolti_out, "stderr_troncato_byte": tolti_err,
                "timeout_s": concesso, "timeout_limitato": limitato,
                "memoria_mb": int(s.memory_mb), "cpu_percento": int(s.cpu_percent),
            },
            error=None if rc == 0 else f"lo script e' uscito con {rc}",
        )

    def _verifica(a: BozzaArgs, piano: Piano, r: ToolResult) -> Verifica:
        """I file DICHIARATI ci sono e sono STL binari che tornano coi conti.

        L'atteso viene dal PIANO congelato — i `create` che il proprietario ha
        visto e approvato — e l'osservato dal disco, con `os.stat` e con
        `stl_lettore`, che non e' lo script: e' il formato.
        """
        if not r.ok:
            return Verifica.non_verificata(
                f"esegui_bozza dichiara di non aver eseguito ({r.error}); senza "
                "uno stato di partenza non si distingue «non fatto» da «fatto "
                "e disfatto»", fonte="registry.invoke")
        attesi = [op.destinazione for op in piano.operazioni if op.tipo == "create"]
        atteso = ("presenti e leggibili come STL binario: "
                  + ", ".join(p.name for p in attesi))
        visti: list[str] = []
        assenti: list[str] = []
        illeggibili: list[str] = []
        for p in attesi:
            try:
                os.stat(p)
                stl_lettore.leggi(p)
            except FileNotFoundError:
                assenti.append(p.name)
            except (OSError, stl_lettore.StlIllegibile) as exc:
                illeggibili.append(f"{p.name} ({exc})")
            else:
                visti.append(p.name)
        if not assenti and not illeggibili:
            osservato = atteso
        else:
            parti = []
            if visti:
                parti.append("presenti e leggibili: " + ", ".join(visti))
            if assenti:
                parti.append("ASSENTI: " + ", ".join(assenti))
            if illeggibili:
                parti.append("ILLEGGIBILI: " + "; ".join(illeggibili))
            osservato = "; ".join(parti)
        return Verifica.confronta(
            atteso, osservato,
            fonte="os.stat e core/model3d/stl_lettore.py (struct + numpy.frombuffer), "
                  "riletti dal core e non dallo script")

    register(Tool(
        name="esegui_bozza",
        description=(
            "Esegue lo script di una bozza del laboratorio in sandbox — radice "
            "vuota, senza rete, con la sola cartella della bozza scrivibile — "
            "e verifica che i file STL dichiarati in bozza.json esistano e si "
            "rileggano. Prende il NOME della bozza, mai un percorso. Chiede "
            "conferma mostrando lo script, l'interprete e la cartella."
        ),
        args_schema=BozzaArgs,
        side_effect=True,
        planner=_piano,
        # Invariante 27 la blocca gia' (side_effect=True); esplicito comunque.
        gesture_allowed=False,
        handler=_esegui,
        verifica=_verifica,
    ))
    log.info("laboratorio_acceso", radice=str(radice))
    return lab
