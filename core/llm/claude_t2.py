"""T2 — spawn effimero per le operazioni lunghe. SPEC §5.3, invariante 16.

Differenze da T1, e nessuna e' casuale:

| | T1 | T2 |
|---|---|---|
| processo | persistente | effimero, uno per compito |
| cwd | `voice-cwd` **vuota** | radice del progetto |
| tool | **nessuno** (`--allowedTools ""`) | ristretti, ma reali |
| costo d'avvio | pagato una volta | ~2,4 s a ogni spawn, accettabile su compiti da minuti |
| Governor | **riservato, mai in coda** | **ogni spawn ci passa** |

La cwd e' la radice del progetto **di proposito**: T2 fa lavoro vero e deve
vedere `CLAUDE.md` e i quattro subagent in `.claude/agents/`. T1 gira da una
directory vuota per la ragione opposta — non deve caricare la costituzione a
ogni frase detta a voce (§5.2).

⚠️ **`--permission-mode dontAsk` NON scavalca la conferma umana di §6.2.**
Riguarda i tool DI CLAUDE CODE dentro il suo processo. I tool di JARVIS con
`side_effect=True` vivono in `core/tools/registry.py`, e T2 non li attraversa:
per toccare un file attraverso JARVIS servirebbe comunque la conferma. I due
"permessi" si somigliano nel nome e non nella sostanza, ed e' il tipo di
somiglianza che genera un varco se nessuno la scrive.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from core.llm.governor import Governor, QuotaEsaurita

log = structlog.get_logger(__name__)

MODELLO = "sonnet"
#: Ristretti ma reali. Nessun tool di scrittura distruttiva: cancellare passa
#: dall'allowlist del core, che chiede conferma (§6.1).
TOOL_CONSENTITI = "Read,Edit,Bash(git *),Glob,Grep"
MAX_TURNS = 20


@dataclass
class Evento:
    tipo: str
    dato: dict
    #: `null` = messaggio del processo principale; valorizzato = di un subagent
    #: (§5.3). E' l'unico modo di distinguerli nello stream.
    parent_tool_use_id: str | None = None

    @property
    def da_subagent(self) -> bool:
        return self.parent_tool_use_id is not None


@dataclass
class Risultato:
    ok: bool
    testo: str = ""
    session_id: str | None = None
    costo_usd: float | None = None
    durata_s: float = 0.0
    errore: str | None = None
    eventi: int = 0
    subagent: set[str] = field(default_factory=set)


class ClaudeT2:
    """Operazioni lunghe. **Ogni spawn passa dal Governor** (invariante 16)."""

    def __init__(
        self,
        governor: Governor,
        radice: Path,
        modello: str = MODELLO,
        tool: str = TOOL_CONSENTITI,
        max_turns: int = MAX_TURNS,
    ) -> None:
        self._gov = governor
        self._radice = Path(radice)
        self._modello = modello
        self._tool = tool
        self._max_turns = max_turns

    def argv(self, task: str, resume: str | None = None) -> list[str]:
        """L'invocazione di §5.3. Verificabile senza avviare nulla."""
        a = ["claude", "-p", task,
             "--output-format", "stream-json", "--verbose",
             "--model", self._modello,
             "--allowedTools", self._tool,
             "--permission-mode", "dontAsk",
             "--max-turns", str(self._max_turns),
             # §5.3: senza questo il testo dei subagent non arriva nello stream.
             "--forward-subagent-text"]
        if resume:
            a += ["--resume", resume]
        return a

    async def stream(self, task: str, etichetta: str,
                     resume: str | None = None) -> AsyncIterator[Evento]:
        """Esegue e restituisce gli eventi mentre arrivano.

        Solleva `QuotaEsaurita` **prima di spawnare** se il Governor rifiuta:
        meglio un rifiuto immediato e leggibile di un processo avviato e poi
        ucciso a meta'.
        """
        async with self._gov.spawn(etichetta):
            proc = await asyncio.create_subprocess_exec(
                *self.argv(task, resume), cwd=str(self._radice),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            log.info("t2_processo", etichetta=etichetta, pid=proc.pid,
                     modello=self._modello)
            try:
                async for riga in proc.stdout:
                    try:
                        e = json.loads(riga)
                    except json.JSONDecodeError:
                        continue
                    # Il Governor guarda ogni evento: e' cosi' che vede il
                    # rate limit senza che nessuno debba ricordarsi di dirglielo.
                    self._gov.osserva(e)
                    yield Evento(tipo=e.get("type", ""), dato=e,
                                 parent_tool_use_id=e.get("parent_tool_use_id"))
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()

    async def esegui(self, task: str, etichetta: str,
                     resume: str | None = None) -> Risultato:
        """Esegue fino in fondo e riassume. Non solleva su fallimento del
        compito: un T2 che non riesce e' un esito, non un guasto."""
        t0 = time.monotonic()
        r = Risultato(ok=False)
        pezzi: list[str] = []
        try:
            async for ev in self.stream(task, etichetta, resume):
                r.eventi += 1
                if ev.da_subagent:
                    r.subagent.add(ev.parent_tool_use_id)
                if ev.tipo == "assistant":
                    for blocco in ev.dato.get("message", {}).get("content", []):
                        if blocco.get("type") == "text":
                            pezzi.append(blocco["text"])
                elif ev.tipo == "result":
                    r.session_id = ev.dato.get("session_id")
                    r.costo_usd = ev.dato.get("total_cost_usd")
                    r.ok = not ev.dato.get("is_error", False)
                    self._gov.registra_risultato(etichetta, ev.dato)
        except QuotaEsaurita as exc:
            r.errore = str(exc)
            return r
        except Exception as exc:
            r.errore = f"{type(exc).__name__}: {exc}"
            log.error("t2_fallito", etichetta=etichetta, errore=r.errore)
            return r
        finally:
            r.durata_s = round(time.monotonic() - t0, 2)
            r.testo = "".join(pezzi).strip()
        return r
