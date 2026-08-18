"""JARVIS che guarda se stesso — SOLA LETTURA, per §13.

⚠️ **Non e' in §21.1.** Lo aggiungo qui e lo dichiaro in `SEZIONE-13.md`.

Due moduli della scrivania mostrano il PROGETTO, non i file dell'utente:

    Core sorgente (§13)     la forma vera di questo repository
    Piani d'archivio (§11.5) i documenti di accettazione delle fasi

Fino a oggi li alimentavano due istantanee generate da `npm run fixtures`, e i
commenti di quegli script dichiaravano gia' l'intenzione: «nel core il pannello
riceve l'albero vero dal topic `source.tree`». Questo modulo e' quel produttore.

## Perche' un modulo a parte, e non `list_dir`

**La radice del progetto non e' fra le `allowed_roots`, e non deve diventarlo.**
`allowed_roots` e' l'elenco delle cartelle su cui i tool possono anche
SCRIVERE, spostare e cestinare: metterci dentro il codice di JARVIS
significherebbe dargli la possibilita' di modificarsi. La difesa non e' che
nessuno lo farebbe: e' che quella radice non e' in elenco.

## Perche' e' sicuro leggere fuori dalle radici consentite

**Nessuno dei due tool ha un parametro `path`.** La radice e' una costante del
modulo, ricavata dalla posizione del file sorgente, quindi non esiste input che
possa spostarla altrove. E' la stessa sicurezza strutturale di
`core/tools/geo.py`, che non ha un path proprio perche' non deve poterlo avere.
Una validazione si dimentica; un argomento che non esiste, no.

Entrambi `side_effect=False`: nessuna conferma (§6.2), nessuna deroga
all'invariante 3. Entrambi `gesture_allowed=False`: §14 non ha un gesto che li
chieda, e l'allowlist delle gesture si tiene minima per costruzione.

## Le due uscite, e perche' sono diverse

`leggi_albero()` e `leggi_note()` sono funzioni pure ed esportate. Il TOOL le
avvolge — e avvolge il corpo delle note in `<untrusted_source>`, come fa
`read_file`, perche' un `ToolResult` puo' finire nel contesto di un LLM. Il
messaggio per il PANNELLO lo compone `core/engine.py` dalle stesse funzioni, in
chiaro, perche' li' l'unico consumatore e' il DOM.

Nessuno dei due apre la busta dell'altro: sono due lettori della stessa
sorgente, non una catena.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

#: Costante, non argomento: vedi l'intestazione. `parents[2]` perche' questo
#: file sta in `<radice>/core/tools/introspect.py`.
RADICE = Path(__file__).resolve().parents[2]
ACCETTAZIONE = RADICE / "docs" / "acceptance"

#: Cartelle che non fanno parte del progetto: dipendenze scaricate, cache,
#: uscite di lavoro. Sono le stesse di `.gitignore` piu' `.git`, e senza di
#: esse la nuvola dei sorgenti mostrerebbe la forma di `node_modules`.
SALTA = frozenset({
    ".git", "__pycache__", ".venv", "node_modules", "dist", "shots",
    ".pytest_cache", ".ruff_cache", ".mypy_cache",
})

#: Mai in elenco, nemmeno per nome (§18.3, e `.claude/settings.json` ne vieta
#: la lettura). Un elenco di file non e' un segreto, ma non c'e' ragione di
#: farci comparire il nome di quello che contiene le chiavi.
SALTA_FILE = frozenset({"secrets.toml"})

#: Tetto ai file elencati. Un albero che crescesse senza limite riempirebbe un
#: messaggio del socket, e la nuvola di §17.4 satura molto prima.
MAX_FILE = 4000

#: Caratteri dell'estratto di ogni nota. Le carte di §11.5 mostrano un
#: paragrafo, non il documento.
ESTRATTO = 220


class VuotoArgs(BaseModel):
    """Nessun argomento: la radice e' una sola, ed e' una costante."""


# ── albero dei sorgenti ──────────────────────────────────────────────────────

def leggi_albero(radice: Path = RADICE) -> list[dict[str, Any]]:
    """`[{path, bytes}]` dei file del progetto, percorsi relativi alla radice.

    `os.walk` e non `rglob` perche' serve POTARE: `rglob` scenderebbe dentro
    `node_modules` per poi scartarne i risultati, e li' ci sono decine di
    migliaia di file.
    """
    fuori: list[dict[str, Any]] = []
    for cartella, sotto, file in os.walk(radice):
        sotto[:] = sorted(d for d in sotto if d not in SALTA)
        base = Path(cartella)
        for nome in sorted(file):
            if nome in SALTA_FILE:
                continue
            p = base / nome
            try:
                # `lstat`: un collegamento simbolico si misura per quello che
                # e', senza seguirlo fuori dalla radice.
                byte = p.lstat().st_size
            except OSError:
                continue
            fuori.append({"path": str(p.relative_to(radice)), "bytes": byte})
            if len(fuori) >= MAX_FILE:
                log.warning("albero_troncato", tetto=MAX_FILE)
                return fuori
    return fuori


# ── documenti d'archivio ─────────────────────────────────────────────────────

def _estratto(testo: str) -> str:
    """Il primo paragrafo vero: niente titoli, metadati, righe di regola.

    Stessa estrazione di `scripts/fixture-albero.mjs`, che e' nostra. I
    pittogrammi si tolgono: nei documenti sono legittimi, ma sono glifi a
    colori e in un'interfaccia monocroma rompono la palette senza che l'audit
    li veda — non sono un colore CSS, sono un font.
    """
    righe = [
        r for r in testo.split("\n")
        if r.strip() and not r.startswith("#") and not r.startswith("---")
        and not r.startswith("**Data")
    ]
    corpo = " ".join(righe[:3])
    corpo = "".join(
        c for c in corpo
        if c not in "*`|" and not (0x1F300 <= ord(c) <= 0x1FAFF)
        and not (0x2600 <= ord(c) <= 0x27BF) and ord(c) != 0xFE0F
    )
    return " ".join(corpo.split())[:ESTRATTO]


def leggi_note(cartella: Path = ACCETTAZIONE) -> list[dict[str, Any]]:
    """`[{file, titolo, corpo, byte}]` dei documenti di accettazione.

    Cartella assente o vuota: lista vuota, non un errore. E' lo stato di
    un'installazione senza documenti, e i pannelli hanno gia' il proprio stato
    vuoto per dirlo (invariante 23).
    """
    if not cartella.is_dir():
        return []
    note: list[dict[str, Any]] = []
    for p in sorted(cartella.glob("*.md")):
        try:
            testo = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.warning("nota_non_leggibile", file=p.name, errore=str(exc)[:80])
            continue
        titolo = next(
            (r.lstrip("# ").strip() for r in testo.split("\n") if r.startswith("# ")),
            p.name,
        )
        note.append({
            "file": p.name,
            "titolo": titolo,
            "corpo": _estratto(testo),
            "byte": len(testo.encode("utf-8")),
        })
    return note


# ── allowlist ────────────────────────────────────────────────────────────────

def register_introspect_tools() -> None:
    async def _albero(_args: VuotoArgs) -> ToolResult:
        try:
            file = leggi_albero()
        except OSError as exc:
            # Nessuna eccezione arriva all'LLM — stile codice di CLAUDE.md.
            return ToolResult(ok=False, error=f"albero non leggibile: {exc}")
        return ToolResult(ok=True, output={
            "radice": str(RADICE),
            "totale": len(file),
            "bytes": sum(f["bytes"] for f in file),
            "files": file,
        })

    async def _note(_args: VuotoArgs) -> ToolResult:
        note = leggi_note()
        # INVARIANTE 5: il corpo e' contenuto di un file, e un `ToolResult` puo'
        # finire nel contesto di un LLM. Si marca qui, alla sorgente, come fa
        # `read_file`: marcarlo dopo vorrebbe dire rintracciarne i consumatori.
        avvolte = [
            {**n, "corpo": f"<untrusted_source path={n['file']!r}>\n"
                           f"{n['corpo']}\n</untrusted_source>"}
            for n in note
        ]
        return ToolResult(ok=True, output={
            "cartella": str(ACCETTAZIONE),
            "untrusted": True,
            "note": avvolte,
        })

    register(Tool(
        name="source_tree",
        description=(
            "Elenco dei file del progetto JARVIS con la loro dimensione, per "
            "il modulo Core sorgente. Sola lettura, nessun argomento."
        ),
        args_schema=VuotoArgs,
        side_effect=False,
        gesture_allowed=False,
        handler=_albero,
    ))
    register(Tool(
        name="archive_notes",
        description=(
            "Titolo ed estratto dei documenti di accettazione delle fasi. "
            "Il corpo e' dato non fidato. Sola lettura, nessun argomento."
        ),
        args_schema=VuotoArgs,
        side_effect=False,
        gesture_allowed=False,
        handler=_note,
    ))
