"""Substrato della memoria: file markdown, non un database opaco — SPEC §5.5.

```
memory_data/
├── sessions/     un .jsonl per sessione — cronologia grezza
├── topics/       note a lungo termine, un .md per argomento
├── conso/        log giornaliero token e costo
└── initiatives/  log degli eventi proattivi
```

> «Il vantaggio e' pratico prima che tecnico: quando JARVIS ricorda una cosa
> sbagliata, Lei apre il file e la corregge con un editor. Con un vector store
> opaco non puo'.»

Due progetti indipendenti sono arrivati alla stessa conclusione
(`docs/ANALISI-REPO-E-TECNOLOGIE.md` §1.1② e §1.3②), ed e' la ragione per cui
qui non c'e' nessun indice binario: **il file E' il dato**. Un indice si
aggiunge sopra, non al posto.

I fatti fissati stanno in `topics/_fatti-fissati.md` e sono **dell'utente**: il
consolidamento notturno non li tocca mai (§5.5).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

FATTI = "_fatti-fissati"


def _slug(testo: str) -> str:
    s = re.sub(r"[^\w\s-]", "", testo.lower()).strip()
    return re.sub(r"[\s_]+", "-", s)[:60] or "senza-titolo"


@dataclass(frozen=True)
class Topic:
    nome: str
    percorso: Path
    contenuto: str


class MemoryStore:
    def __init__(self, radice: Path) -> None:
        self.radice = Path(radice).expanduser().resolve()
        self.sessions = self.radice / "sessions"
        self.topics = self.radice / "topics"
        self.conso = self.radice / "conso"
        self.initiatives = self.radice / "initiatives"
        for d in (self.sessions, self.topics, self.conso, self.initiatives):
            d.mkdir(parents=True, exist_ok=True)

    # ── fatti fissati ────────────────────────────────────────────────────────

    def fissa(self, fatto: str) -> None:
        """Aggiunge un fatto. Idempotente: rifissare lo stesso non lo duplica."""
        fatto = fatto.strip()
        if not fatto or fatto in self.fatti_fissati():
            return
        f = self.topics / f"{FATTI}.md"
        if not f.exists():
            f.write_text("# Fatti fissati\n\n"
                         "Sono Suoi. Il consolidamento notturno non li tocca.\n"
                         "Si correggono aprendo questo file.\n\n", encoding="utf-8")
        with f.open("a", encoding="utf-8") as fh:
            fh.write(f"- {fatto}\n")
        log.info("fatto_fissato", fatto=fatto[:60])

    def fatti_fissati(self) -> list[str]:
        """I fatti, letti dal file **a ogni chiamata**.

        Non si tiene una copia in memoria: se l'utente corregge il file con un
        editor mentre JARVIS gira, la correzione deve valere subito. E' la
        proprieta' per cui §5.5 sceglie i markdown.
        """
        f = self.topics / f"{FATTI}.md"
        if not f.exists():
            return []
        return [r[2:].strip() for r in f.read_text(encoding="utf-8").splitlines()
                if r.startswith("- ") and r[2:].strip()]

    # ── topic ────────────────────────────────────────────────────────────────

    def scrivi_topic(self, nome: str, contenuto: str) -> Path:
        p = self.topics / f"{_slug(nome)}.md"
        p.write_text(f"# {nome}\n\n{contenuto.strip()}\n", encoding="utf-8")
        log.info("topic_scritto", nome=nome, percorso=str(p))
        return p

    def leggi_topic(self, nome: str) -> Topic | None:
        p = self.topics / f"{_slug(nome)}.md"
        if not p.exists():
            return None
        return Topic(nome=nome, percorso=p, contenuto=p.read_text(encoding="utf-8"))

    def elenca_topic(self) -> list[str]:
        return sorted(p.stem for p in self.topics.glob("*.md") if p.stem != FATTI)

    def cerca(self, query: str, limite: int = 10) -> list[Topic]:
        """Ricerca testuale sui topic. Nessun indice: sono file, e sono pochi."""
        ago = query.lower().strip()
        out = []
        for p in sorted(self.topics.glob("*.md")):
            if p.stem == FATTI:
                # I fatti fissati non entrano nella ricerca: chi costruisce un
                # contesto li mette gia' in testa, e trovarli anche qui li
                # duplicherebbe dentro il budget.
                continue
            testo = p.read_text(encoding="utf-8", errors="replace")
            if ago in testo.lower() or ago in p.stem:
                out.append(Topic(nome=p.stem, percorso=p, contenuto=testo))
            if len(out) >= limite:
                break
        return out

    # ── sessioni e iniziative ────────────────────────────────────────────────

    def registra_turno(self, sessione: str, turno: dict) -> None:
        p = self.sessions / f"{sessione}.jsonl"
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), **turno}, ensure_ascii=False) + "\n")

    def sessioni_dal(self, da: float) -> list[dict]:
        out = []
        for p in sorted(self.sessions.glob("*.jsonl")):
            for riga in p.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    t = json.loads(riga)
                except json.JSONDecodeError:
                    continue
                if t.get("ts", 0) >= da:
                    out.append({"sessione": p.stem, **t})
        return out

    def iniziative_dal(self, da: float) -> list[dict]:
        """Cio' che JARVIS ha fatto di sua iniziativa dopo `da`.

        ⚠️ **Non esisteva.** `registra_iniziativa` scriveva da agosto e la sua
        docstring diceva «visibile al risveglio»: nessuno poteva vederlo, e
        `initiatives/` era una cartella in sola scrittura. Il file il cui unico
        scopo e' essere letto al risveglio non aveva un lettore.

        Stessa forma di `sessioni_dal`: una riga malformata si salta, non fa
        cadere il risveglio.
        """
        out = []
        for p in sorted(self.initiatives.glob("*.jsonl")):
            for riga in p.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    t = json.loads(riga)
                except json.JSONDecodeError:
                    continue
                if t.get("ts", 0) > da:
                    out.append(t)
        return out

    def registra_iniziativa(self, tipo: str, dettaglio: dict) -> None:
        """Cio' che JARVIS ha fatto di propria iniziativa, visibile al risveglio."""
        giorno = time.strftime("%Y-%m-%d")
        p = self.initiatives / f"{giorno}.jsonl"
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "tipo": tipo, **dettaglio},
                               ensure_ascii=False) + "\n")
