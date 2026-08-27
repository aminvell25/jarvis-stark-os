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
from core.llm.untrusted import ContenutoNonFidato, Untrusted

log = structlog.get_logger(__name__)

MODELLO = "sonnet"
#: I tool di Claude Code che si CHIEDONO per uno spawn T2.
#:
#: ⚠️ **Non e' un confine, e' una richiesta.** Qui c'era scritto «ristretti ma
#: reali», e la parola «confine» era sottintesa. Misurato il 27 agosto con
#: questa stessa riga di comando, `--permission-mode dontAsk`, in una copia
#: scratch:
#:
#:     Write                                        negato
#:     Bash(printf 'OK' > prova.txt && cat ...)     negato
#:     Bash(cd ... && ls -la && cat ...)            negato
#:     Bash(git add -A && git commit -m zero)       RIUSCITO
#:     Bash(echo PERIMETRO_APERTO)                  RIUSCITO
#:     Edit                                         RIUSCITO
#:
#: `echo` non compare ne' qui ne' in `permissions.allow` di
#: `.claude/settings.json`, e passa; `ls` e `cat` ci sono, e non passano. Il
#: perimetro reale **non e' nessuna delle due fonti che questo progetto
#: dichiara**: lo decide l'ambiente di Claude Code, e da qui non si enumera.
#:
#: Quello che JARVIS controlla davvero e' **che cosa chiede**, ed e' l'unica
#: leva onesta. Il confine vero degli effetti resta l'allowlist del core, con
#: la conferma di §6.2: i tool qui sopra non ci passano e non ne fanno parte.
#:
#: ⚠️ **`Edit` e' stato TOLTO**, e non serviva a nessuno: `_t2_conso` gira con
#: zero tool, `_t2_argomenti` pure, e i due `META_COMANDI` chiedono di GUARDARE
#: il log di git e i documenti in `docs/acceptance/`. Un tool di scrittura che
#: nessun chiamante usa e' superficie regalata — e il consolidamento notturno
#: l'ha avuto in mano per giorni, alle 04:00, con nessuno davanti.
TOOL_CONSENTITI = "Read,Bash(git *),Glob,Grep"
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
        su_evento=None,
    ) -> None:
        self._gov = governor
        self._radice = Path(radice)
        self._modello = modello
        self._tool = tool
        self._max_turns = max_turns
        #: §5.6. Il Governor guarda gli eventi per il rate limit; il
        #: `Supervisore` per l'autenticazione. Sono due domande diverse sullo
        #: stesso flusso, e finora la seconda non la faceva nessuno.
        self._su_evento = su_evento

    def componi(self, istruzioni: str, contenuto: Untrusted | None = None) -> str:
        """Il prompt finale, e la BARRIERA dell'invariante 5.

        Contenuto non fidato — una pagina nella webview, l'OCR di ARGUS, una
        news — puo' entrare **solo** in un contesto con zero tool. Qui non e'
        una raccomandazione: se i tool sono accesi, si solleva.

        Fail-closed come il registry di Fase 1. Chi domani aggiungera' un
        percorso nuovo senza pensarci trovera' un'eccezione al primo giro, non
        un varco silenzioso al centesimo.
        """
        if contenuto is None:
            return istruzioni
        if self._tool.strip():
            raise ContenutoNonFidato(
                f"contenuto non fidato da {contenuto.origine} verso uno spawn con "
                f'--allowedTools "{self._tool}". §12: solo in contesti con zero tool. '
                "Costruisci un ClaudeT2(tool=\"\") per leggerlo."
            )
        return f"{istruzioni}\n\n{contenuto.avvolto()}"

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
                     resume: str | None = None,
                     contenuto: Untrusted | None = None) -> AsyncIterator[Evento]:
        """Esegue e restituisce gli eventi mentre arrivano.

        Solleva `QuotaEsaurita` **prima di spawnare** se il Governor rifiuta:
        meglio un rifiuto immediato e leggibile di un processo avviato e poi
        ucciso a meta'.
        """
        # La barriera PRIMA del Governor: un prompt che non si puo' comporre
        # non deve nemmeno consumare uno slot della finestra.
        task = self.componi(task, contenuto)

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
                    if self._su_evento is not None:
                        await self._su_evento(e)
                    yield Evento(tipo=e.get("type", ""), dato=e,
                                 parent_tool_use_id=e.get("parent_tool_use_id"))
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()

    async def esegui(self, task: str, etichetta: str,
                     resume: str | None = None,
                     contenuto: Untrusted | None = None) -> Risultato:
        """Esegue fino in fondo e riassume. Non solleva su fallimento del
        compito: un T2 che non riesce e' un esito, non un guasto."""
        t0 = time.monotonic()
        r = Risultato(ok=False)
        pezzi: list[str] = []
        try:
            async for ev in self.stream(task, etichetta, resume, contenuto):
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
