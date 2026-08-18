"""Operazioni su file reali — SPEC §6.1, invarianti 1, 3, 4, 5.

Le operazioni vivono nel core, non in Electron: un renderer con accesso al
disco e contenuti web in `<webview>` e' inaccettabile (§6.1).

Tre regole che questo modulo non puo' aggirare, perche' non sono scritte qui:

* i percorsi passano da `core.paths_policy` — la stessa regola della sandbox
* i tool con `side_effect` non si registrano senza `planner`, e non si eseguono
  senza conferma: lo impone `core.tools.registry`
* **nessun `delete`**. Solo `send2trash`, e senza ripiego (vedi `_trash`)

Le radici arrivano dalle impostazioni a OGNI chiamata, non alla registrazione:
`settings.toml` si ricarica a caldo (Fase 0) e una copia presa all'avvio
resterebbe indietro.
"""

from __future__ import annotations

import shutil
import time
from collections.abc import Callable
from pathlib import Path

import structlog
from pydantic import BaseModel, Field
from send2trash import send2trash

from core.paths_policy import PathFuoriRadice, e_una_radice, risolvi_sotto_radici
from core.platform import Paths, paths as platform_paths
from core.settings import Settings
from core.tools.confirm import Operazione, Piano
from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

#: Tetto di `read_file`. Un file da 2 GB non entra in un `ToolResult`, e il
#: tentativo bloccherebbe il core mentre lo legge.
MAX_LETTURA = 1024 * 1024

#: Estensione -> cartella, per `organize_folder`. Minuscolo, punto incluso.
CATEGORIE: dict[str, str] = {
    **{e: "Immagini" for e in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".heic", ".bmp", ".tiff")},
    **{e: "Documenti" for e in (".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".epub")},
    **{e: "Fogli" for e in (".xls", ".xlsx", ".ods", ".csv")},
    **{e: "Audio" for e in (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".opus")},
    **{e: "Video" for e in (".mp4", ".mkv", ".avi", ".mov", ".webm")},
    **{e: "Archivi" for e in (".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst")},
    **{e: "Codice" for e in (".py", ".js", ".ts", ".rs", ".go", ".c", ".h", ".cpp", ".sh", ".json", ".toml", ".yaml", ".yml")},
    **{e: "Modelli" for e in (".stl", ".obj", ".glb", ".gltf", ".step", ".stp", ".3mf", ".ply")},
}
CATEGORIA_ALTRO = "Altro"


def categoria(p: Path) -> str:
    return CATEGORIE.get(p.suffix.lower(), CATEGORIA_ALTRO)


# ─────────────────────────────────────────────────────────────────────────────
# Schemi
# ─────────────────────────────────────────────────────────────────────────────


class PathArgs(BaseModel):
    path: str


class ReadFileArgs(BaseModel):
    path: str
    max_bytes: int = Field(default=MAX_LETTURA, ge=1, le=MAX_LETTURA)


class SearchArgs(BaseModel):
    query: str = Field(min_length=1)
    root: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class CreateFileArgs(BaseModel):
    path: str
    content: str = ""


class DuePathArgs(BaseModel):
    source: str
    destination: str


class OrganizeArgs(BaseModel):
    path: str


# ─────────────────────────────────────────────────────────────────────────────
# Registrazione
# ─────────────────────────────────────────────────────────────────────────────


def register_file_tools(
    leggi_settings: Callable[[], Settings],
    leggi_paths: Callable[[], "Paths"] | None = None,
) -> None:
    """Registra gli otto tool di §6.1.

    `leggi_settings` e' una funzione e non un valore: le impostazioni si
    ricaricano a caldo, e le radici consentite vanno lette al momento dell'uso.
    """

    leggi_paths = leggi_paths or platform_paths

    def radici() -> list[Path]:
        return list(leggi_settings().fs.allowed_roots)

    def risolvi(p: str | Path) -> Path:
        return risolvi_sotto_radici(p, radici())

    # ── sola lettura ─────────────────────────────────────────────────────────

    async def _list_dir(a: PathArgs) -> ToolResult:
        d = risolvi(a.path)
        if not d.is_dir():
            return ToolResult(ok=False, error=f"non e' una directory: {d}")
        voci = []
        for f in sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                st = f.stat()
                voci.append({
                    "name": f.name,
                    "type": "dir" if f.is_dir() else "file",
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "categoria": categoria(f) if f.is_file() else None,
                })
            except OSError:
                continue          # un file sparito mentre elencavamo non e' un errore
        return ToolResult(ok=True, output={"path": str(d), "voci": voci, "totale": len(voci)})

    async def _read_file(a: ReadFileArgs) -> ToolResult:
        f = risolvi(a.path)
        if not f.is_file():
            return ToolResult(ok=False, error=f"non e' un file: {f}")
        # Si legge SOLO il necessario. `read_bytes()[:n]` carica prima il file
        # intero: su un file da qualche gigabyte il core si ferma mentre lo
        # ingoia, e il tetto non serve a nulla.
        with f.open("rb") as fh:
            dati = fh.read(a.max_bytes)
        testo = dati.decode("utf-8", errors="replace")
        # INVARIANTE 5: il contenuto di un file e' DATO NON FIDATO. In Fase 2
        # non c'e' ancora un LLM che lo riceva, ma la marcatura nasce qui:
        # aggiungerla dopo significherebbe rintracciarne tutti i consumatori.
        return ToolResult(ok=True, output={
            "path": str(f),
            "untrusted": True,
            "content": f"<untrusted_source path={str(f)!r}>\n{testo}\n</untrusted_source>",
            "bytes": len(dati),
            "troncato": f.stat().st_size > a.max_bytes,
        })

    async def _search_files(a: SearchArgs) -> ToolResult:
        basi = [risolvi(a.root)] if a.root else radici()
        ago = a.query.lower()
        trovati: list[dict] = []
        for base in basi:
            base = Path(base)
            if not base.is_dir():
                continue
            for f in base.rglob("*"):
                if len(trovati) >= a.limit:
                    break
                if ago in f.name.lower():
                    try:
                        trovati.append({"path": str(f), "type": "dir" if f.is_dir() else "file",
                                        "size": f.stat().st_size if f.is_file() else None})
                    except OSError:
                        continue
        return ToolResult(ok=True, output={"query": a.query, "trovati": trovati,
                                           "totale": len(trovati), "limite_raggiunto": len(trovati) >= a.limit})

    async def _stat_path(a: PathArgs) -> ToolResult:
        p = risolvi(a.path)
        if not p.exists():
            return ToolResult(ok=False, error=f"non esiste: {p}")
        st = p.stat()
        return ToolResult(ok=True, output={
            "path": str(p), "type": "dir" if p.is_dir() else "file",
            "size": st.st_size, "mtime": st.st_mtime,
            "categoria": categoria(p) if p.is_file() else None,
            "e_una_radice": e_una_radice(p, radici()),
        })

    def verifica_piano_ancora_valido(piano: Piano) -> str | None:
        """Ricontrolla il piano congelato immediatamente prima di agire.

        Il piano porta percorsi risolti al momento della proposta. Fra la
        conferma e adesso possono essere passati due minuti, e un percorso puo'
        essere stato sostituito da un symlink che punta fuori: l'utente avrebbe
        letto e approvato una cosa, e ne accadrebbe un'altra.

        Non chiude del tutto la finestra — fra questo controllo e la chiamata
        di sistema resta un istante — ma la riduce da minuti a microsecondi, e
        soprattutto rende ESPLICITO che la finestra esiste.

        Ritorna il motivo del rifiuto, o `None` se il piano regge ancora.
        """
        for op in piano.operazioni:
            for percorso in (op.sorgente, op.destinazione):
                if percorso is None:
                    continue
                try:
                    if percorso.exists() and percorso.resolve() != percorso:
                        return (f"{percorso} non punta piu' dove puntava quando "
                                f"e' stata data la conferma")
                    risolvi(percorso)
                except PathFuoriRadice as exc:
                    return str(exc)
        return None

    # ── con effetti: planner + handler ───────────────────────────────────────

    async def _piano_create_file(a: CreateFileArgs) -> Piano:
        p = risolvi(a.path)
        return Piano(tool="create_file", riepilogo=f"crea un file di {len(a.content)} caratteri",
                     operazioni=(Operazione(tipo="create", destinazione=p,
                                            dettaglio=f"{len(a.content)} caratteri"),))

    async def _create_file(a: CreateFileArgs, piano: Piano) -> ToolResult:
        if (motivo := verifica_piano_ancora_valido(piano)):
            return ToolResult(ok=False, error=f"il piano non e' piu' valido: {motivo}")
        p = piano.operazioni[0].destinazione
        if p.exists():
            return ToolResult(ok=False, error=f"esiste gia': {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a.content, encoding="utf-8")
        return ToolResult(ok=True, output={"path": str(p), "bytes": len(a.content)})

    async def _piano_create_folder(a: PathArgs) -> Piano:
        p = risolvi(a.path)
        return Piano(tool="create_folder", riepilogo="crea una cartella",
                     operazioni=(Operazione(tipo="mkdir", destinazione=p),))

    async def _create_folder(a: PathArgs, piano: Piano) -> ToolResult:
        if (motivo := verifica_piano_ancora_valido(piano)):
            return ToolResult(ok=False, error=f"il piano non e' piu' valido: {motivo}")
        p = piano.operazioni[0].destinazione
        if p.exists():
            return ToolResult(ok=False, error=f"esiste gia': {p}")
        p.mkdir(parents=True)
        return ToolResult(ok=True, output={"path": str(p)})

    def _piano_due_path(tipo: str, etichetta: str):
        async def piano(a: DuePathArgs) -> Piano:
            s, d = risolvi(a.source), risolvi(a.destination)
            return Piano(tool=f"{tipo}_path", riepilogo=f"{etichetta} un elemento",
                         operazioni=(Operazione(tipo=tipo, sorgente=s, destinazione=d),))
        return piano

    async def _move_path(a: DuePathArgs, piano: Piano) -> ToolResult:
        if (motivo := verifica_piano_ancora_valido(piano)):
            return ToolResult(ok=False, error=f"il piano non e' piu' valido: {motivo}")
        op = piano.operazioni[0]
        if not op.sorgente.exists():
            return ToolResult(ok=False, error=f"non esiste: {op.sorgente}")
        if op.destinazione.exists():
            return ToolResult(ok=False, error=f"la destinazione esiste gia': {op.destinazione}")
        if e_una_radice(op.sorgente, radici()):
            return ToolResult(ok=False, error=f"{op.sorgente} e' una radice consentita: non si sposta")
        op.destinazione.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(op.sorgente), str(op.destinazione))
        return ToolResult(ok=True, output={"da": str(op.sorgente), "a": str(op.destinazione)})

    async def _copy_path(a: DuePathArgs, piano: Piano) -> ToolResult:
        if (motivo := verifica_piano_ancora_valido(piano)):
            return ToolResult(ok=False, error=f"il piano non e' piu' valido: {motivo}")
        op = piano.operazioni[0]
        if not op.sorgente.exists():
            return ToolResult(ok=False, error=f"non esiste: {op.sorgente}")
        if op.destinazione.exists():
            return ToolResult(ok=False, error=f"la destinazione esiste gia': {op.destinazione}")
        op.destinazione.parent.mkdir(parents=True, exist_ok=True)
        if op.sorgente.is_dir():
            # symlinks=True COPIA I LINK COME LINK. Con il default (False)
            # `copytree` DEREFERENZIA i symlink dentro l'albero: un link a
            # /etc/hostname dentro la cartella copiata diventerebbe un file
            # vero col contenuto di /etc/hostname, materializzato dentro una
            # radice consentita. Misurato, non ipotizzato: e' una fuga di
            # informazioni che la validazione dei percorsi non intercetta,
            # perche' il percorso COPIATO e' legittimo.
            shutil.copytree(op.sorgente, op.destinazione, symlinks=True)
        else:
            shutil.copy2(op.sorgente, op.destinazione)
        return ToolResult(ok=True, output={"da": str(op.sorgente), "a": str(op.destinazione)})

    async def _piano_trash(a: PathArgs) -> Piano:
        p = risolvi(a.path)
        quanti = sum(1 for _ in p.rglob("*")) if p.is_dir() else 0
        dettaglio = f"cartella con {quanti} elementi" if p.is_dir() else "file"
        return Piano(tool="trash_path", riepilogo="sposta nel cestino",
                     operazioni=(Operazione(tipo="trash", sorgente=p, dettaglio=dettaglio),))

    async def _trash(a: PathArgs, piano: Piano) -> ToolResult:
        if (motivo := verifica_piano_ancora_valido(piano)):
            return ToolResult(ok=False, error=f"il piano non e' piu' valido: {motivo}")
        p = piano.operazioni[0].sorgente
        if not p.exists():
            return ToolResult(ok=False, error=f"non esiste: {p}")
        if e_una_radice(p, radici()):
            return ToolResult(ok=False, error=f"{p} e' una radice consentita: non si cestina")
        try:
            send2trash(str(p))
        except Exception as exc:
            # NESSUN RIPIEGO. La documentazione di Send2Trash raccomanda una
            # catena che finisce in `os.remove()`, cioe' cancellazione
            # permanente: l'invariante 4 la vieta, e §6.1 spiega perche' —
            # un agente che sbaglia deve poter essere annullato. Se il cestino
            # non e' disponibile, l'operazione FALLISCE e lo dice.
            log.error("cestino_fallito", path=str(p), errore=str(exc))
            return ToolResult(
                ok=False,
                error=f"impossibile spostare nel cestino ({type(exc).__name__}: {exc}). "
                      f"Il file NON e' stato toccato: non esiste una cancellazione "
                      f"di ripiego (invariante 4).",
            )
        # Dove e' finito, VERIFICATO. La prima versione rispondeva
        # `recuperabile: True` senza guardare, e su un filesystem diverso dalla
        # home la risposta era falsa: il file va in `.Trash-<uid>` sul mount di
        # origine, non nel cestino della home.
        # Si CERCA dove e' finito, leggendo il registro del cestino. La prima
        # versione cercava per nome e falliva alla seconda cancellazione dello
        # stesso file: XDG rinomina inserendo un numero prima dell'estensione.
        piattaforma = leggi_paths()
        cestino = piattaforma.trash_dir_for(p)
        ritrovato = piattaforma.find_trashed(p)
        dentro = str(ritrovato) if ritrovato else None
        return ToolResult(ok=True, output={
            "cestinato": str(p),
            "cestino": str(cestino) if cestino else None,
            "recuperabile_da": dentro,
            "verificato": dentro is not None,
        })

    async def _piano_organize(a: OrganizeArgs) -> Piano:
        d = risolvi(a.path)
        if not d.is_dir():
            raise PathFuoriRadice(f"non e' una directory: {d}")
        operazioni = []
        for f in sorted(d.iterdir(), key=lambda x: x.name.lower()):
            if not f.is_file():
                continue                      # le cartelle esistenti si lasciano
            cat = categoria(f)
            dest = d / cat / f.name
            if dest == f or dest.exists():
                continue
            operazioni.append(Operazione(tipo="move", sorgente=f, destinazione=dest,
                                         dettaglio=cat))
        per_cat = sorted({o.dettaglio for o in operazioni})
        return Piano(
            tool="organize_folder",
            riepilogo=f"{len(operazioni)} file in {len(per_cat)} cartelle: {', '.join(per_cat) or '—'}",
            operazioni=tuple(operazioni),
        )

    async def _organize(a: OrganizeArgs, piano: Piano) -> ToolResult:
        if (motivo := verifica_piano_ancora_valido(piano)):
            return ToolResult(ok=False, error=f"il piano non e' piu' valido: {motivo}")
        # §6.2: per 200 file UNA conferma, gia' data. Qui si esegue il piano
        # congelato, file per file, e un fallimento singolo non ferma il resto.
        fatte, fallite = 0, []
        for op in piano.operazioni:
            try:
                op.destinazione.parent.mkdir(parents=True, exist_ok=True)
                if op.destinazione.exists():
                    fallite.append({"path": str(op.sorgente), "motivo": "destinazione occupata"})
                    continue
                shutil.move(str(op.sorgente), str(op.destinazione))
                fatte += 1
            except OSError as exc:
                fallite.append({"path": str(op.sorgente), "motivo": str(exc)})
        return ToolResult(ok=not fallite, output={"spostati": fatte, "falliti": fallite},
                          error=None if not fallite else f"{len(fallite)} spostamenti falliti")

    # ── allowlist ────────────────────────────────────────────────────────────

    def reg(nome, descr, schema, handler, planner=None, side_effect=False):
        register(Tool(name=nome, description=descr, args_schema=schema,
                      side_effect=side_effect, gesture_allowed=False,
                      planner=planner, handler=handler))

    reg("list_dir", "Elenca il contenuto di una directory consentita.", PathArgs, _list_dir)
    reg("read_file", "Legge un file di testo. Il contenuto e' dato non fidato.", ReadFileArgs, _read_file)
    reg("search_files", "Cerca file per nome nelle radici consentite.", SearchArgs, _search_files)
    reg("stat_path", "Metadati di un file o di una cartella.", PathArgs, _stat_path)

    reg("create_file", "Crea un file.", CreateFileArgs, _create_file, _piano_create_file, True)
    reg("create_folder", "Crea una cartella.", PathArgs, _create_folder, _piano_create_folder, True)
    reg("move_path", "Sposta un file o una cartella.", DuePathArgs, _move_path,
        _piano_due_path("move", "sposta"), True)
    reg("copy_path", "Copia un file o una cartella.", DuePathArgs, _copy_path,
        _piano_due_path("copy", "copia"), True)
    reg("trash_path", "Sposta nel cestino. Mai cancellazione permanente.", PathArgs, _trash,
        _piano_trash, True)
    reg("organize_folder", "Ordina i file di una cartella per tipo.", OrganizeArgs, _organize,
        _piano_organize, True)
