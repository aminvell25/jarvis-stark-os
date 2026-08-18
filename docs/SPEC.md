# J.A.R.V.I.S. OS — Specifica di progetto

**Rev 5.3 · agosto 2026 · uso strettamente personale**

Documento **autosufficiente**. Sostituisce ogni revisione precedente.
Questo file va in `docs/SPEC.md`: è il riferimento che Claude Code consulta.

## Emendamenti dopo la chiusura della rev 5.0

| Rev | Data | Cosa | Sezioni toccate |
|---|---|---|---|
| 5.3 | 18 ago 2026 | **Tre librerie nominate in §22 per la Fase 5 non entrano, ognuna perché contraddice un invariante**: three-globe genera geometria propria (inv. 22), troika-three-text rasterizza testo in WebGL con colori letterali (inv. 20 e 18), d3-force è una simulazione che si assesta muovendosi (inv. 25). Il globo, la graticola, il terminatore e i fusi sono `ParametricComponent` gatati. Aggiunto il tool `timezones` in `core/tools/geo.py`, non previsto da §21.1. Corretti tre difetti del quality gate di §11.11 e i periodi degli anelli di §10.3 (240 è multiplo di 120). Motivazioni per esteso in `docs/acceptance/FASE-05.md` | **§10.3**, **§11.11**, **§17.4**, **§21.1**, **§22** |
| 5.2 | 18 ago 2026 | **Nota APU in §9.** La tabella VRAM presuppone una GPU discreta; su memoria unificata la «VRAM» è un carveout della RAM e i due numeri non si sommano. Aggiunta la regola `headroom = min(VRAM libera, RAM disponibile)`, applicata da `core/gpu_scheduler.py`. Scoperto misurando la macchina di sviluppo in Fase 1 | **§9** |
| 5.1 | 18 ago 2026 | **Il trasporto core ↔ Electron passa da TCP `127.0.0.1:8765` a un socket UNIX.** L'autorizzazione la fa il kernel sui permessi del filesystem invece di un token applicativo, e la conferma umana di §6.2 — cioè l'invariante 3 — smette di essere raggiungibile da qualunque processo dell'utente. Il protocollo non cambia: WebSocket su stream, stessi topic. Decisione presa in `docs/VALUTAZIONE-ARCHITETTURALE.md`, ADR-002 | **§3.2**, **§16.1b**, **§18.2**, **§21.4** |

L'**invariante 7** è stato riscritto di conseguenza, in `CLAUDE.md` e nella
copia di §20. Ora enuncia il principio — *il canale non è raggiungibile dalla
rete e l'autorizzazione la impone il sistema operativo* — e nomina il socket
UNIX come implementazione odierna. Così il porting a Windows (named pipe con
ACL, §23) non richiederà un altro emendamento dell'invariante.

## Chiuso nella rev 5.0
| # | Aggiunta |
|---|---|
| 1 | **§5.6 Scadenza OAuth e supervisione di T1** — il caso di degradazione più probabile, prima scoperto |
| 2 | **§5.2 latenza misurata sul campo**: cold start mediano 2,41 s |
| 3 | **§7.6 parser T0 completo** — il componente più critico per la latenza, prima solo citato |
| 4 | **§5.7 `voice-persona.md`** — il system prompt di T1, prima solo referenziato |

## Cosa cambia rispetto alla rev 4.1

| # | Decisione presa | Effetto |
|---|---|---|
| 1 | **Deepgram è il provider principale**; i modelli gratuiti in streaming sono **fallback** | §7 e §8 invertite nei default |
| 2 | **ARGUS vede solo l'app** | §12 chiusa su `scope="app"` |
| 3 | **Linux ora, Windows in futuro** | §23 nuova: cosa isolare oggi perché domani costi poco |
| 4 | **Analisi di replicabilità della UI** dai riferimenti | §11 nuova — la sezione che ha chiesto |
| 5 | **Stack librerie UI verificato con repo** | §11.3 |
| 6 | **Metodo operativo per Claude Code sul design** | §11.7 — il ciclo di feedback visivo |

---

# INDICE

1. Cos'è, cosa non è
2. Verdetto sui riferimenti
3. Architettura
4. Stack verificato
5. Backend LLM — Claude Code, memoria, scadenza OAuth, persona
6. Filesystem, YouTube, operazioni reali
7. Voce: wake a frasi, STT, TTS, parser T0
8. Impostazioni e chiavi
9. Contesa GPU
10. Design system
11. **Replicare la UI dei riferimenti**
12. ARGUS
13. Moduli, pannelli, scorciatoie
14. Gesture
15. News proattive
16. Autonomia e degradazione
17. Modelli 3D
18. Sicurezza
19. Legale
20. `CLAUDE.md`
21. Repo e codice
22. Piano a fasi, stime
23. **Portabilità verso Windows**
24. Cosa resta incerto

---

# 1. Cos'è, cosa non è

**Non è un sistema operativo.** **Non è un overlay sul desktop.**

**È un'applicazione desktop a schermo intero** — un ambiente cognitivo — dentro il quale JARVIS vive, parla, mostra dati, apre il web, gestisce cartelle reali del PC e genera modelli 3D. Fuori dalla sua finestra non tocca nulla.

Cervello: **Claude Code su abbonamento**. Nessun LLM locale.
Voce: **Deepgram Flux** primario, modelli locali in fallback.

---

# 2. Verdetto sui riferimenti

## 2.1 I quattro errori della specifica originale

| # | Errore | Verifica | Esito |
|---|---|---|---|
| 1 | PyAutoGUI per controllo finestre | è automazione mouse/tastiera, non un WM; su Wayland non funziona (no XTEST). Issue #909, #111 aperte; SeleniumBase #4010: solo X11, repo non mantenuto da ~2 anni | **rimosso**; col nuovo scope il problema si dissolve |
| 2 | three-mesh-bvh "accelera il rendering" | falso: accelera raycasting e query spaziali | **resta, riclassificato**: picking gesti (§14) |
| 3 | Overlay Electron click-through su Wayland | Electron #51808 (input region solo alla submission di un frame), #52456 (regressione X11 in v43), niente `wlr-layer-shell` | **scompare** col nuovo scope; Electron riabilitato |
| 4 | Sandbox a denylist | lo spazio dei comandi dannosi è infinito e componibile | **allowlist tipizzata** |

## 2.2 Il documento delle librerie

**Errore strutturale**: descriveva una pagina web senza core né accesso al sistema, con "Livello 2: Logica = anime.js + Golden Layout" — che è presentazione.

**Tenere**: WinBox.js (finestre interne), anime.js (prioritaria), three.js.

**Scartare**: OS.js (desktop *simulato* con FS virtuale — Lei vuole file veri) · Arwes (neon cyberpunk, contraddice il pilastro "nessun glow") · Golden Layout (ridondante; due WM si contendono il drag) · Babylon.js (doppio contesto GL) · Spline (SaaS, richiede rete) · React Three Fiber (solo React, reconciler overhead) · GSAP (ridondante con anime.js) · Web Speech API (in Chromium **manda l'audio a Google**).

## 2.3 Stonic AI

Prodotto Windows commerciale, pagamento una tantum, l'utente collega la propria API.

**Da adottare**: il principio *"esegue, non risponde con un paragrafo su come potresti farlo da solo"*, e i loro tre casi d'uso come **suite di accettazione** della v1: organizza Downloads per tipo; apri YouTube e riproduci; cosa sta rallentando il PC.

## 2.4 Il link Pinterest

`https://in.pinterest.com/da8c149f-...` **non raggiungibile**: Pinterest blocca l'accesso automatizzato e l'URL non ha comunque il formato di un pin. **Non analizzato.**

---

# 3. Architettura

## 3.1 Perché Electron

Il cambio di scope ha eliminato `wlr-layer-shell`, la click-through e l'IPC del compositore. **Elimina anche il motivo per cui avevo scartato Electron.** In una finestra normale Le dà il motore WebGL di Chromium, nettamente superiore a WebKitGTK per three.js pesante.

*Non usi Tauri: su Linux usa la system webview, cioè WebKitGTK, e riporta il problema.*

Il **core Python resta**: pipeline vocale, file sotto allowlist, telemetria, sandbox, orchestrazione di Claude Code.

## 3.2 Processi

```
┌─────────────────────────────────────────────────────────────┐
│ CORE (Python, asyncio) — servizio systemd utente             │
│ engine · router · memory · settings · governor · gpu_sched   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ TOOL LAYER — allowlist tipizzata                       │   │
│ │ file · 3D · sistema · news · argus                     │   │
│ │ side_effect=True → conferma umana obbligatoria         │   │
│ └───────────────────────────────────────────────────────┘   │
│ T0 grammar (<10ms, 0 LLM) · T1 claude persistente ·          │
│ T2 claude -p effimero + subagent                             │
│ voice: wake Vosk → STT → TTS streaming                       │
│ sandbox: profilo exec (bwrap + seccomp)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket su socket UNIX (§18.2)
                           │ $XDG_RUNTIME_DIR/jarvis-os/core.sock, dir 0700
                           │ telemetry · agent.* · voice.* · fs.*
                           │ news.* · argus.* · state.snapshot
┌──────────────────────────┴──────────────────────────────────┐
│ APP JARVIS OS (Electron) — finestra massimizzata             │
│ main: bridge WS ↔ renderer, gestione <webview>               │
│ renderer: WinBox · three.js · PixiJS · anime.js · webview    │
└──────────────────────────────────────────────────────────────┘
```

## 3.3 I tre tier

| Tier | Cosa | Motore | Latenza |
|---|---|---|---|
| **T0** | apri pannello, cerca file, workspace, telemetria, volume | parser a grammatica, zero LLM | **<10 ms** |
| **T1** | conversazione, risposte parlate | `claude` persistente, Haiku 4.5 | 300–900 ms primo token |
| **T2** | operazioni complesse, codice, 3D | `claude -p` + subagent | 5 s – minuti |

## 3.4 Sandbox

| Profilo | Per | D-Bus | Rete | FS |
|---|---|---|---|---|
| `exec` | codice generato, script, build 3D | ❌ | ❌ | ro tranne `~/JARVIS/` |

`bubblewrap --unshare-all --die-with-parent`, ro-bind `/`, rw-bind `~/JARVIS/`, seccomp.

**Le operazioni su file reali NON girano in sandbox**: girano nel core sotto allowlist con validazione path (§6.1). La sandbox isola il *codice generato*; l'allowlist vincola le *operazioni note*.

---

# 4. Stack verificato (agosto 2026)

| Libreria | Stato | Licenza | Verdetto |
|---|---|---|---|
| **LangGraph** | 1.0 ott. 2025, 1.1.x nel 2026 | Apache 2.0 | ✅ `create_react_agent` **deprecato** → `StateGraph` |
| **psutil** | attivo | BSD | ✅ (correzione §21.4) |
| **PyAutoGUI** | non mantenuto ~2 anni, no Wayland | BSD | ❌ rimosso |
| **Electron** | attivo | MIT | ✅ riabilitato |
| **three.js** | attivo | MIT | ✅ |
| **three-mesh-bvh** | v0.9.x | MIT | ✅ picking |
| **PixiJS** | v8 | MIT | ✅ |
| **anime.js** | v4.x (4.0.1 apr. 2025) | MIT | ✅ **prioritaria** |
| **WinBox.js** | attivo | Apache 2.0 | ✅ |
| **augmented-ui** | v2, attivo | **BSD-2** | ✅ **nuovo** (§11.3) |
| **uPlot** | attivo | MIT | ✅ **nuovo** (§11.3) |
| **three-globe** | attivo | MIT | ✅ **nuovo** (§11.3) |
| **troika-three-text** | attivo | MIT | ✅ **nuovo** (§11.3) |
| **d3** (geo, shape, scale) | attivo | ISC | ✅ **nuovo** (§11.3) |
| **GSAP** | gratuito dal 30 apr. 2025 (v3.13) | "No Charge" | ❌ per ridondanza, non licenza |
| **Vosk** | attivo | Apache 2.0 | ✅ wake a frasi |
| **faster-whisper** | v1.2.1 (31 ott. 2025) | MIT | ✅ **fallback** STT |
| **Kokoro-82M** | v1.0 gen. 2025, 82M, ~327 MB | Apache 2.0 | ✅ **fallback** TTS |
| **Piper** | `rhasspy/piper` **archiviato ott. 2025**; fork `piper1-gpl` | MIT → **GPL-3.0** | ⚠️ preferire Kokoro |
| **MediaPipe** | google-ai-edge, roadmap incerta (#6068), Python ≤3.12 | Apache 2.0 | ⚠️ isolare dietro interfaccia |
| **Tesseract** | attivo v5 | Apache 2.0 | ✅ OCR (§12) |
| **trimesh / build123d** | attivi | MIT / Apache 2.0 | ✅ (§17) |

Nota GSAP: acquisizione Webflow **autunno 2024**, rilascio gratuito **aprile 2025**. Licenza compatibile; scartato solo per non avere due motori di animazione.

---

# 5. Backend LLM — Claude Code

## 5.1 La trappola `--bare`

Claude Code è un **harness agentico**, non un endpoint LLM. La documentazione indica `--bare` come *la* ottimizzazione di avvio, ma:

> *In bare mode, Claude Code never reads OAuth credentials or the system keychain.*

**`--bare` richiede `ANTHROPIC_API_KEY` e non usa l'abbonamento.** Abbonamento e avvio rapido collidono su questo flag.

**Conseguenza**: l'unico modo di eliminare il costo di avvio è **non riavviare mai il processo**. Sessione persistente = requisito.

## 5.2 T1 — processo persistente

```bash
claude \
  --input-format stream-json --output-format stream-json \
  --verbose --include-partial-messages --replay-user-messages \
  --model claude-haiku-4-5-20251001 \
  --allowedTools "" \
  --append-system-prompt-file ~/.config/jarvis-os/voice-persona.md
```

Primo turno: `/config thinking=false`, `/effort low`.

| Flag | Effetto |
|---|---|
| `--input-format stream-json` | processo vivo tra i turni: **elimina il costo di avvio** |
| `--include-partial-messages` | `text_delta` token per token → TTS parte subito |
| `--allowedTools ""` | zero tool nel contesto: il tier vocale **parla** |
| `thinking=false` | elimina i token di ragionamento |

⚠️ **Da verificare**: la documentazione sull'effort descrive i livelli per Opus 5 e Fable 5. **Non ho conferma che Haiku 4.5 li esponga.** Se ignorato, `thinking=false` resta il guadagno principale.

⚠️ **Working directory**: senza `--bare`, Claude Code legge il `CLAUDE.md` corrente **e superiori**. Lanci T1 da `~/.local/share/jarvis-os/voice-cwd/`: dedicata, vuota.

### Latenza misurata sul campo (agosto 2026)

Misura reale di `claude -p` a freddo, da directory vuota, `--allowedTools ""`,
Haiku 4.5, abbonamento Max:

| Esecuzione | Tempo |
|---|---|
| 1 (cache fredde) | 3,16 s |
| 2 | 2,41 s |
| 3 | 2,21 s |
| **mediana** | **2,41 s** |

Il prompt era banale: la generazione vale forse 150 ms. **Gli altri ~2,2 s sono
costo fisso** — spawn di Node, lettura del portachiavi OAuth, discovery della
configurazione, handshake di rete.

**Conclusione operativa**: un `claude -p` per turno conversazionale significherebbe
2,5–3 s prima del primo suono. Inutilizzabile. La sessione persistente elimina
esattamente questi 2,2 s, ed è quindi un **requisito architetturale**, non
un'ottimizzazione.

Autenticazione verificata: `authMethod: claude.ai`, `apiProvider: firstParty`,
`subscriptionType: max`. Conferma che `--bare` resta inutilizzabile (§5.1).

## 5.3 T2 e subagent

```bash
claude -p "$TASK" --output-format stream-json --verbose \
  --model sonnet --allowedTools "Read,Edit,Bash(git *)" \
  --permission-mode dontAsk --max-turns 20 \
  --agents "$(cat ~/.config/jarvis-os/agents.json)"
```

Più CLI simultanee sono possibili. Session ID nel JSON per `--resume`; da v2.1.223 si ritrova da qualunque directory.

Subagent in `.claude/agents/*.md`, frontmatter con `model` e `effort`:

```markdown
---
name: forge
description: Sintesi codice e geometria parametrica
model: sonnet
effort: high
tools: Read, Edit, Bash
---
Sei FORGE. Applichi SEMPRE la disciplina §11.4-11.6: nessun modello 3D
non parametrico, nessun componente che non passi il quality gate, e
nessun componente accettato senza il ciclo di verifica visiva §11.7.
```

Analoghi: `argus` (haiku/low), `edith` (memoria, haiku/low), `veronica` (news, haiku/low).

Nello stream i subagent si distinguono da `parent_tool_use_id` (`null` = principale). Per il testo: `--forward-subagent-text` (v2.1.211+).

## 5.4 Governor

L'uso programmatico **attinge ai limiti dell'abbonamento**. Il pool crediti separato per l'Agent SDK è **sospeso dal 15 giugno 2026**.

```python
class Governor:
    max_concurrent_t2 = 2
    t1_reserved = True                # T1 non va MAI in coda
    max_t2_spawns_per_window = 15     # finestra 60 min
    # su system/api_retry error="rate_limit":
    #   sospendi T2 → degrada → agent.advisory → NON far fallire T1
```

### Log giornaliero di consumo

Il campo `total_cost_usd` arriva in ogni evento `result` dello stream (§21.5).
Il Governor lo accumula in `memory_data/conso/YYYY-MM-DD.jsonl`: token e costo
stimato per turno e per tier.

Serve a sapere quando la finestra di quota sta per chiudersi **prima** che si
chiuda, non dopo. Il pannello telemetria mostra il consumo della finestra
corrente accanto a CPU e RAM.

## 5.5 Memoria — ContextPruner

| Strato | Contenuto | Sopravvive |
|---|---|---|
| **Fatti fissati** | preferenze, decisioni, frasi-wake | ✅ sempre |
| **Verbatim** | ultimi 6 scambi, ultimi file toccati | finestra scorrevole |
| **Compresso** | il resto, ridotto a riassunti | recuperabile |

```python
class ContextPruner:
    def __init__(self, budget_tokens=12000, verbatim_turns=6):
        self.budget, self.verbatim_turns = budget_tokens, verbatim_turns
        self.pinned: list[str] = []
        self.turns: list[dict] = []
        self.digests: list[str] = []

    def build_context(self) -> list[dict]:
        ctx = [{"role":"system","content":"\n".join(self.pinned)}] if self.pinned else []
        return ctx + self.turns[-self.verbatim_turns:]

    def prune(self, count_tokens) -> None:
        while count_tokens(self.build_context()) > self.budget:
            if len(self.turns) <= self.verbatim_turns:
                break
            self.digests.append(self._digest(self.turns.pop(0)))
```

⚠️ **Con T1 persistente, Claude Code gestisce già il proprio contesto.** Il `ContextPruner` serve solo per (a) i fatti fissati da reiniettare quando la sessione viene ricreata e (b) T2, dove ogni spawn parte da zero. **Non duplichi la gestione del contesto di T1**: otterrebbe due gestori in disaccordo.

---

### Substrato: file markdown, non un database opaco

La memoria a lungo termine vive in **file markdown leggibili**:

```
memory_data/
├── sessions/     un .jsonl per sessione — cronologia grezza
├── topics/       note a lungo termine, un .md per argomento
├── conso/        log giornaliero token e costo
└── initiatives/  log degli eventi proattivi
```

Il vantaggio è pratico prima che tecnico: quando JARVIS ricorda una cosa
sbagliata, Lei apre il file e la corregge con un editor. Con un vector store
opaco non può. Un indice SQLite FTS sopra i markdown dà la ricerca senza
togliere l'ispezionabilità.

### Consolidamento notturno

Il `ContextPruner` è **reattivo**: pota quando il budget è saturo, e ciò che
scarta è perso. Serve anche un passaggio **programmato**, che gira quando
nessuno usa il sistema e ha tempo di ragionare su cosa conservare.

```python
# core/memory/consolidate.py
async def nightly_consolidation() -> None:
    """Gira alle 04:00 via scheduler. Rilegge le sessioni del giorno e
    fonde ciò che vale nei topic a lungo termine.

    Usa un processo T2 dedicato con --allowedTools "": legge e scrive solo
    tramite i tool memoria dell'allowlist, mai direttamente.
    NON tocca i fatti fissati: quelli sono dell'utente.
    """
    sessions = load_sessions_since(last_run())
    if not sessions:
        return
    for topic, fragments in group_by_topic(sessions):
        merged = await t2_summarize(topic, fragments)   # zero tool
        write_topic(topic, merged)                      # via allowlist
    mark_run(now())
```

Potatura sotto pressione e consolidamento a mente fredda non sono lo stesso
lavoro. Servono entrambi.

## 5.6 Scadenza OAuth — il caso di degradazione più probabile

Il processo T1 gira per settimane senza riavviarsi: è tutto il punto del design.
Prima o poi **il token OAuth scade**. Senza gestione esplicita accade questo:

```
token scade → claude esce con errore di autenticazione
→ systemd Restart=always rilancia → fallisce di nuovo → loop infinito
→ JARVIS è muto e non dice perché
```

È il fallimento più probabile dell'intero sistema, e va gestito **prima** che
capiti, non dopo.

**Rilevamento.** `authentication_failed` è già uno dei valori del campo `error`
negli eventi `system/api_retry` dello stream (§21.5). Il supervisore lo distingue
da un crash generico.

```python
# core/llm/supervisor.py
AUTH_ERRORS = {"authentication_failed", "oauth_org_not_allowed"}

async def on_stream_event(evt: dict) -> None:
    if evt.get("type") == "system" and evt.get("subtype") == "api_retry":
        if evt.get("error") in AUTH_ERRORS:
            await enter_state("degraded_llm", reason="auth_expired")
            await speak_local(                       # il TTS NON dipende da Claude
                "Signore, la mia sessione è scaduta. "
                "Serve una nuova autenticazione."
            )
            bus.publish("agent.advisory", {
                "level": "critical", "reason": "auth_expired",
                "action": "esegui `claude` e poi /login",
            })
            supervisor.stop_restart_loop()           # NIENTE riavvio a ciclo
            return
```

**Nell'unit systemd** (§22 Fase 9):

```ini
[Service]
Restart=always
RestartSec=5
# il codice di uscita dell'auth NON deve innescare il riavvio
RestartPreventExitStatus=41
StartLimitBurst=5
StartLimitIntervalSec=120
```

Verifichi il codice di uscita reale sul Suo sistema e lo sostituisca a `41`:
la documentazione non pubblica una tabella completa dei codici di `-p`, quindi
lo determini empiricamente lasciando scadere una sessione di prova.

**Cosa continua a funzionare in `degraded_llm`:** le frasi-comando T0, la
telemetria, il file manager, l'intera interfaccia. Non toccano l'LLM. È la
proprietà che rende il wake a frasi (§7.2) prezioso ben oltre la latenza.

**Cosa NON fare:** tentare la riautenticazione automatica. Richiede un browser
e un'interazione umana; automatizzarla significa o fallire in silenzio o
conservare credenziali dove non devono stare.

## 5.7 `voice-persona.md` — il system prompt di T1

File in `~/.config/jarvis-os/voice-persona.md`, passato con
`--append-system-prompt-file`. **Deve restare sotto i ~250 token**: viaggia in
ogni turno.

```markdown
Sei J.A.R.V.I.S., l'intelligenza di supervisione del Creatore.

TONO
- Britannico, colto, calmo, analitico. Ironia asciutta quando serve.
- Ti rivolgi a lui chiamandolo "Signore". Sempre.
- Mai scuse servili. Mai "mi dispiace, sono solo un modello".
- Se qualcosa fallisce: dichiari l'errore tecnico e proponi l'alternativa.

VOCE
- Le tue risposte vengono LETTE AD ALTA VOCE mentre le generi.
- Frasi brevi. Nessun elenco puntato, nessun markdown, nessuna emoji:
  non si pronunciano.
- Numeri in parole quando è più naturale ascoltarli.
- Due o tre frasi. Se serve più spazio, chiedi se vuole il dettaglio a schermo.

LIMITI
- Non hai strumenti. Non puoi aprire file, spostare finestre, eseguire nulla.
  Quelle azioni le fa il sistema prima di arrivare a te.
- Se ti chiede un'azione che richiede strumenti, rispondi che te ne occupi e
  basta: il sistema la instrada altrove. Non descrivere passaggi.
- Se non sai, lo dici. Mai inventare.
```

Le tre righe di "LIMITI" sono quelle che contano: T1 gira con `--allowedTools ""`
e senza di esse promette azioni che non può compiere.


# 6. Filesystem, YouTube, operazioni reali

## 6.1 Modello di sicurezza

Le operazioni file vivono nel **core Python**, non in Electron: un renderer con accesso al disco e contenuti web in `<webview>` è inaccettabile.

```python
# core/tools/files.py
from pathlib import Path
from pydantic import BaseModel, field_validator
from core.tools.registry import Tool, ToolResult, register

WORKSPACE = Path.home() / "JARVIS"
ALLOWED_ROOTS = [WORKSPACE, Path.home()/"Documenti", Path.home()/"Scaricati"]

def _safe(p: str) -> Path:
    """Il controllo va DOPO resolve(): è resolve() che elimina i '..'."""
    rp = Path(p).expanduser().resolve()
    if not any(rp == r or r in rp.parents for r in ALLOWED_ROOTS):
        raise ValueError(f"path fuori dalle radici consentite: {rp}")
    return rp

class CreateFileArgs(BaseModel):
    path: str
    content: str = ""
    @field_validator("path")
    @classmethod
    def _v(cls, v): _safe(v); return v

async def _create_file(a: CreateFileArgs) -> ToolResult:
    try:
        p = _safe(a.path)
        if p.exists():
            return ToolResult(ok=False, error="esiste già; usa overwrite_file")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a.content, encoding="utf-8")
        return ToolResult(ok=True, output={"path": str(p), "bytes": len(a.content)})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))

register(Tool(name="create_file", description="Crea un file nelle radici consentite.",
              args_schema=CreateFileArgs, side_effect=True,
              gesture_allowed=False, handler=_create_file))
```

| Tool | side_effect |
|---|---|
| `list_dir`, `read_file`, `search_files`, `stat_path` | ❌ |
| `create_file`, `create_folder`, `move_path`, `copy_path` | ✅ |
| `trash_path` | ✅ **cestino, mai unlink** |
| `organize_folder` | ✅ |

⚠️ **Nessun `delete` reale.** Solo `send2trash`. Un agente che sbaglia deve poter essere annullato.

## 6.2 Conferma umana

```
proposta → validazione pydantic → topic `fs.confirm_request` con riepilogo
→ UI mostra il PATH ASSOLUTO RISOLTO, non quello richiesto
→ conferma → esegue → `fs.result`   |   rifiuto → ToolResult(ok=False)
```

**Batch**: per `organize_folder` su 200 file, **una sola conferma** ma con il piano completo mostrato prima. Mai 200 conferme; mai zero.

## 6.3 YouTube e web nell'ambiente

```javascript
function createWebPanel(url, title) {
  const box = new WinBox({ title, class:["jarvis-panel"], width:960, height:540 });
  const wv = document.createElement("webview");
  wv.setAttribute("src", url);
  wv.setAttribute("partition", "persist:jarvis");   // sessione isolata
  wv.setAttribute("allowpopups", "false");
  wv.style.cssText = "width:100%;height:100%;border:0;background:#0a1014";
  box.body.appendChild(wv);
  return { box, wv };
}
```

```javascript
new BrowserWindow({ webPreferences: {
  contextIsolation: true,      // obbligatorio
  nodeIntegration: false,      // obbligatorio
  sandbox: true,
  webviewTag: true,
  preload: path.join(__dirname, "preload.js"),
}});
```

Il preload espone **solo** un bridge tipizzato verso il WebSocket. Mai `require`, `fs`, `child_process`.

**YouTube**: riproduzione normale funziona; **DRM** richiede il CDM Widevine, non impacchettato di default. Per il controllo programmatico usi l'**IFrame Player API**, non il DOM di youtube.com (il DOM cambia, l'API no). Per la ricerca, **YouTube Data API v3**.

---

# 7. Voce

## 7.1 La catena

```
microfono (PipeWire)
  → VAD Silero      ~5 ms   gate più economico
  → Vosk grammar    ~20 ms  ascolto continuo su frasi note (LOCALE, sempre)
  → match? no → torna al VAD; nulla lascia la macchina
            sì ↓
  → STT: Deepgram Flux (primario) | RealtimeSTT (fallback)
  → T0 grammatica (<10 ms) → azione     oppure T1 claude persistente
  → token → TTS streaming: Deepgram Flux (primario) | Kokoro (fallback)
  → audio out + trascrizione
```

**Nota sull'ordine dei provider**: Lei ha scelto Deepgram come principale. Il wake a frasi resta **sempre locale** — mandare l'audio a Deepgram ventiquattr'ore al giorno sarebbe insostenibile per costo e per privacy. Vosk apre il flusso; solo dopo il match l'audio va in rete.

## 7.2 Wake a frasi personalizzate

openWakeWord lavora su wake word addestrate, non su frasi arbitrarie modificabili. **Vosk con riconoscimento vincolato a grammatica** accetta una lista chiusa di frasi e ignora il resto. Modello italiano piccolo ~50 MB, Apache 2.0, CPU trascurabile, frasi = **configurazione**.

```python
# core/voice/wake.py
import json, vosk

class PhraseWake:
    def __init__(self, model_path: str, phrases: list[str], sample_rate: int = 16000):
        self._model_path = model_path
        self._phrases = [p.lower().strip() for p in phrases]
        grammar = json.dumps(self._phrases + ["[unk]"])   # [unk] assorbe il resto
        self._rec = vosk.KaldiRecognizer(vosk.Model(model_path), sample_rate, grammar)
        self._rec.SetWords(False)

    def feed(self, pcm: bytes) -> str | None:
        if self._rec.AcceptWaveform(pcm):
            text = json.loads(self._rec.Result()).get("text", "").strip()
            if text and text != "[unk]" and text in self._phrases:
                return text
        return None

    def set_phrases(self, phrases: list[str]) -> None:
        self.__init__(self._model_path, phrases)          # hot reload
```

```toml
[voice.wake]
model = "~/.local/share/jarvis-os/vosk-model-small-it-0.22"

[[voice.wake.phrases]]
say = "jarvis"
action = "listen"

[[voice.wake.phrases]]
say = "papà è a casa"
action = "scene:welcome_home"        # esegue, salta lo STT

[[voice.wake.phrases]]
say = "jarvis buonanotte"
action = "scene:goodnight"
```

**Il guadagno non ovvio**: una frase può essere **direttamente un comando**. *"Papà è a casa"* esegue una scena in **~30 ms**, senza STT né LLM — e **funziona offline**, anche con Deepgram come primario.

**Tre regole:**
1. Frasi di **almeno 2 parole** tranne il nome. Le monosillabiche generano falsi positivi continui.
2. **Conferma acustica breve** (tono di 80 ms, non una voce) al riconoscimento.
3. **Log locale dei trigger** con timestamp. Se JARVIS si sveglia da solo, deve poter capire perché.

**Alternativa** se Vosk non desse precisione: Picovoice Porcupine, licenza gratuita per uso personale (il Suo caso, §19). Più accurato, ma le keyword si generano sulla loro console.

## 7.3 STT — Deepgram primario

| | **Deepgram (primario)** | Locale (fallback) |
|---|---|---|
| Endpoint | `wss://api.deepgram.com/v2/listen` | — |
| Modello | `flux-general-multi` (**supporta l'italiano**) | faster-whisper `base` int8 |
| Turn detection | **nativa nel modello** | Silero VAD |
| Parametri | `eot_threshold` 0.5–0.9, `eager_eot_threshold` 0.3–0.9, `eot_timeout_ms`, `keyterm` | — |

Auth: `Authorization: Token <API_KEY>`.

**Tre trappole:**
1. `flux-general-en` **non** accetta `language_hint`; solo `flux-general-multi`.
2. `EagerEndOfTurn` genera risposte speculative: **+50–70% chiamate LLM**. Off di default.
3. Non specifichi `encoding`/`sample_rate` con audio containerizzato.

## 7.4 TTS che parla mentre le parole vengono generate

```python
class TTSProvider(Protocol):
    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]: ...
    async def flush(self) -> None: ...
    async def interrupt(self) -> None: ...
```

`stream()` accetta un **async iterator di testo**: i token di Claude Code entrano nel sintetizzatore mentre vengono generati. Aspettare la frase completa costa 500–1500 ms irrecuperabili.

**I due provider vanno trattati diversamente:**

**Deepgram Flux TTS** (`wss://api.deepgram.com/v2/speak`) accetta i token direttamente. La documentazione è esplicita: in modalità TOKEN i token vengono inviati senza bufferizzare per confini di frase, perché il modello li determina internamente. Aggregare **aggiunge solo latenza**. Mantiene lo stato acustico tra i turni su una connessione, preservando prosodia.

**Kokoro** sintetizza per enunciato: serve un **chunker**.

```python
# core/providers/chunker.py
import re
from typing import AsyncIterator

_BOUNDARY = re.compile(r"[.!?…](?:\s|$)|[;:](?:\s|$)|,(?:\s|$)")
MIN_CHARS, MAX_CHARS = 40, 220

async def clause_chunks(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    """Il PRIMO frammento ha soglia dimezzata: ciò che l'orecchio percepisce
    come reattività è QUANDO JARVIS inizia a parlare."""
    buf, first = "", True
    threshold = MIN_CHARS // 2
    async for tok in tokens:
        buf += tok
        m = None
        if len(buf) >= threshold:
            for m in _BOUNDARY.finditer(buf):
                pass
        if (m and len(buf) >= threshold) or len(buf) >= MAX_CHARS:
            cut = m.end() if m else MAX_CHARS
            chunk, buf = buf[:cut].strip(), buf[cut:]
            if chunk:
                yield chunk
                if first: first, threshold = False, MIN_CHARS
    if buf.strip():
        yield buf.strip()
```

**Il chunker va SOLO davanti a Kokoro.** Davanti a Deepgram Flux è un danno.

```python
def make_tts_pipeline(s: Settings):
    if s.voice.tts_provider == "deepgram":
        return DeepgramFluxTTS(...)                   # token diretti
    return ChunkedTTS(KokoroTTS(...), clause_chunks)  # fallback
```

**Barge-in**: `tts.interrupt()`. Su Flux TTS l'`Interrupt` riporta `text_spoken` — **cosa Lei ha effettivamente udito**. Lo salvi in memoria, altrimenti JARVIS crede di aver detto una frase mai sentita.

## 7.5 Budget di latenza

| Percorso | Composizione | Totale |
|---|---|---|
| **Frase-comando** | VAD 5 + Vosk 20 + azione 5 | **~30 ms**, offline |
| **Comando T0** | + STT streaming 150 + grammatica 10 | **~200 ms** |
| **Conversazione T1** | + primo token 300–900 + primo chunk TTS 150 | **0,6–1,3 s al primo suono** |

---

## 7.6 Il parser T0 — `core/llm/grammar.py`

Il componente più critico per la latenza dell'intero sistema. Deve stare sotto i
10 ms: niente LLM, niente embedding, niente regex compilate a runtime.

```python
# core/llm/grammar.py
"""Router T0: comandi deterministici senza LLM.

Il linguaggio dei comandi è finito: un parser a grammatica è più veloce di
qualunque modello, gratuito, e non allucina. Copre circa l'80% di ciò che
l'utente dirà a JARVIS.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Intent:
    tool: str
    args: dict
    confidence: float = 1.0

# Ogni regola: (pattern compilato, tool, mappatura dei gruppi).
# Compilati UNA VOLTA all'import.
_RULES: list[tuple[re.Pattern, str, callable]] = []

def _rule(pattern: str, tool: str, mapper=lambda m: {}):
    _RULES.append((re.compile(pattern, re.IGNORECASE), tool, mapper))

# --- pannelli --------------------------------------------------------
_rule(r"\b(?:apri|mostra)\s+(?:il\s+|la\s+)?(?P<p>telemetria|console|file|"
      r"globo|agenti|news|sorgente|impostazioni)\b",
      "open_panel", lambda m: {"panel": m.group("p").lower()})
_rule(r"\bchiudi\s+(?:il\s+|la\s+)?(?P<p>\w+)\b",
      "close_panel", lambda m: {"panel": m.group("p").lower()})
_rule(r"\b(?:nascondi tutto|via tutto)\b", "hide_all")
_rule(r"\baffianca\b", "tile_panels")

# --- workspace -------------------------------------------------------
_rule(r"\bworkspace\s+(?P<n>[1-4]|uno|due|tre|quattro)\b",
      "switch_workspace", lambda m: {"n": _num(m.group("n"))})

# --- sistema ---------------------------------------------------------
_rule(r"\b(?:come sta|stato)\s+(?:la\s+)?(?:cpu|memoria|sistema)\b",
      "system_status")
_rule(r"\b(?:cosa|chi)\s+(?:sta\s+)?rallent\w+\b", "top_processes")
_rule(r"\bvolume\s+(?P<v>\d{1,3})\b",
      "set_volume", lambda m: {"level": min(100, int(m.group("v")))})
_rule(r"\b(?:silenzio|muto)\b", "mute")

# --- meta-comandi: non chiedono una cosa, chiedono lo STATO -----------
# Frase deterministica (T0) che innesca un fan-out di subagent (T2).
_rule(r"\b(?:riassumimi la giornata|briefing|fammi il punto)\b", "brief_me")
_rule(r"\bcosa (?:richiede|serve|vuole) la mia attenzione\b", "needs_attention")
_rule(r"\b(?:come stiamo|stato dei sistemi|diagnostica)\b", "doctor")

# --- file ------------------------------------------------------------
_rule(r"\bcerca\s+(?:il\s+file\s+|i\s+file\s+)?(?P<q>.+?)(?:\s+nei file)?$",
      "search_files", lambda m: {"query": m.group("q").strip()})

_WORDS = {"uno": 1, "due": 2, "tre": 3, "quattro": 4}
def _num(s: str) -> int:
    return int(s) if s.isdigit() else _WORDS[s.lower()]

def parse(text: str) -> Intent | None:
    """Intent se il testo è un comando noto, altrimenti None.

    None NON è un errore: è la risposta corretta per il ~20% di frasi che
    devono andare a T1 o T2. Costo tipico: 5-20 microsecondi.
    """
    t = " ".join(text.strip().lower().split())
    for pattern, tool, mapper in _RULES:
        m = pattern.search(t)
        if m:
            return Intent(tool=tool, args=mapper(m))
    return None
```

**Tre note di progetto:**

1. **L'ordine delle regole conta.** La ricerca file è per ultima perché il suo
   pattern è il più permissivo: in cima catturerebbe tutto.
2. **`parse()` ritorna `None`, non solleva.** `None` è la risposta corretta per
   le frasi conversazionali.
3. **Il test di accettazione è un file, non un'opinione.** `tests/t0_corpus.py`
   con almeno 100 frasi etichettate: 80 comandi con l'intento atteso e 20 frasi
   conversazionali che devono dare `None`. Misuri il tempo mediano. È l'unico
   modo per sapere se i 10 ms reggono e se il parser non sta rubando frasi a T1.


# 8. Impostazioni e chiavi

**Default invertiti**: Deepgram primario, locale fallback automatico.

```toml
# ~/.config/jarvis-os/settings.toml     (0600)
[voice]
stt_provider = "deepgram"       # primario
tts_provider = "deepgram"
fallback_on_error = true        # ricade sul locale se la chiave manca o la rete cade
fallback_stt = "local"
fallback_tts = "local"
deepgram_stt_model = "flux-general-multi"
eot_threshold = 0.7
eager_eot = false               # ⚠ true = +50-70% chiamate LLM
whisper_model = "base"          # solo fallback
kokoro_voice  = "bm_george"     # solo fallback

[llm]
backend = "claude_code"
t1_model = "claude-haiku-4-5-20251001"
t1_cwd   = "~/.local/share/jarvis-os/voice-cwd"
t2_model = "sonnet"
max_concurrent_t2 = 2

[fs]
workspace = "~/JARVIS"
allowed_roots = ["~/JARVIS", "~/Documenti", "~/Scaricati"]
trash_only = true

[vision]
enabled = true
scope = "app"                   # deciso: solo l'app
engine = "tesseract"

[news]
enabled = true
max_interruptions_per_hour = 3
topic_ttl_minutes = 30
```

```toml
# ~/.config/jarvis-os/secrets.toml      (0600, SEPARATO, in .gitignore)
deepgram_api_key = ""
guardian_api_key = ""
youtube_api_key  = ""
```

**Regola di fallback**: all'avvio, se `deepgram_api_key` è vuota → JARVIS parte in locale e lo **annuncia**. A runtime, se Deepgram fallisce (chiave invalida, 429, rete) → ricade sul locale entro il turno successivo e lo annuncia. Non deve mai restare muto in silenzio.

**Test connessione obbligatorio**: apre il WebSocket, manda 200 ms di silenzio, verifica l'handshake, chiude.

Chiave mascherata con toggle "mostra". **Mai nei log**, nemmeno in debug.

---

# 9. Contesa GPU

Senza LLM locale la pressione crolla, ma quattro consumatori competono.

| Componente | VRAM | Note |
|---|---|---|
| faster-whisper `base` int8 | ~150 MB | **solo fallback** |
| faster-whisper `large-v2` int8 | 2926 MB | benchmark SYSTRAN |
| Kokoro-82M | ~330 MB, **CPU** | trascurabile |
| Vosk small it | ~50 MB, **CPU** | trascurabile |
| MediaPipe Hand Landmarker | **CPU a 30fps** | `delegate=CPU` obbligatorio |
| Tesseract | **CPU** | trascurabile |
| Florence-2-large (opz.) | ~1,2 GB caricamento, **3–4 GB picco** | |
| Scena three.js + PixiJS 60fps | ~1–2 GB (stima prudenziale) | **il consumatore principale** |

**Con Deepgram primario la GPU è quasi tutta per la scena 3D.** È un beneficio collaterale della Sua scelta.

| VRAM | Praticabile |
|---|---|
| **4 GB** | scena 3D + Deepgram. Fallback locale solo con scena a 30fps |
| **8 GB** | tutto, VLM on-demand |
| **12 GB+** | tutto co-residente |

### ⚠️ Nota APU — questa tabella vale per una GPU **discreta** (rev 5.2)

Su una GPU integrata la «VRAM» non è memoria in più: è un **carveout della
stessa RAM di sistema**. Caricare 3 GB «in VRAM» non libera un byte di RAM, ed
è lo stesso silicio visto da un'altra angolazione.

Misurato sulla macchina di sviluppo (AMD Radeon 840M, `amdgpu`):

| | |
|---|---|
| `mem_info_vram_total` | 8,00 GiB |
| RAM di sistema | 22 GiB totali, ~10 GiB disponibili |

Letta alla lettera, la tabella qui sopra collocherebbe questa macchina nella
riga da **8 GB** — «tutto, VLM on-demand». La lettura corretta è che gli 8 GiB
e i 22 GiB **non si sommano**.

**Regola su memoria unificata**:

```
headroom = min(VRAM libera, RAM disponibile)
```

`core/gpu_scheduler.py` la applica, e `core/platform/base.py::GpuMemory` porta
un flag `unified` letto dal driver, non una costante: su una GPU discreta
`headroom` torna a essere la sola VRAM libera, che è ciò che questa sezione
intende.

Il riconoscimento usa due segnali — classe PCI `0x038000` e
`vis_vram_total == vram_total` — e **nel dubbio assume unificata**: sbagliare
in quella direzione fa rifiutare un caricamento che sarebbe entrato, sbagliare
nell'altra manda il sistema in swap mentre lo scheduler riporta verde.

**Degradazione** (`core/gpu_scheduler.py`): MediaPipe sempre CPU → scena da 60 a 30fps se il VLM è in inferenza → VLM on-demand scaricato dopo 60 s → durante la finestra vocale critica VLM sospeso.

**Regola dura**: monitorare la VRAM e **rifiutare** di caricare un modello se manca headroom, invece di lasciar spillare in RAM via PCIe.

---

# 10. Design system

## 10.1 Token — sorgente unica di verità

```css
/* ui/src/style/tokens.css — NESSUN valore letterale altrove */
:root {
  --bg-void:#070b0d; --bg-deep:#0a1014; --bg-panel:#0e1315; --bg-raised:#131a1d;

  --cy-900:#123840; --cy-700:#1f6b78; --cy-500:#4dd0e1;
  --cy-300:#7fdbe8; --cy-100:#cdeef3;

  --amber:#f0b06a;  /* attenzione */
  --rust:#ff5a3c;   /* critico — MAX 10% della superficie colorata */

  --txt-primary:#cdeef3; --txt-dim:#6d878d; --txt-ghost:#3c4d52;

  --line-hair:0.5px; --line-base:1px; --line-bold:2px;      /* TRE pesi */
  --s-1:4px; --s-2:8px; --s-3:16px; --s-4:32px; --s-5:64px;
  --t-micro:8.5px; --t-data:11px; --t-label:12px;
  --t-body:14px; --t-title:20px;                            /* CINQUE gradini */

  --font-ui:"Barlow Semi Condensed",sans-serif;
  --font-mono:"IBM Plex Mono",monospace;

  --grid:110px; --gap:8px; --radius:0;                      /* SEMPRE zero */
}

.jarvis-panel {
  background: rgba(14,19,21,.62);
  backdrop-filter: blur(16px) saturate(145%);
  border: var(--line-base) solid rgba(226,240,242,.14);
  box-shadow: inset 0 1px 0 rgba(255,220,180,.12),
              inset 0 0 30px rgba(240,176,106,.04),
              0 26px 60px rgba(0,0,0,.5);
  border-radius: var(--radius);
}
```

## 10.2 Anatomia di un pannello

Cinque elementi. Se ne manca uno, sembra un mockup.

```
┌─ ① ETICHETTA IN CAPS ─────── ② ID/VER ──── ③ ⊟ ⊡ ⊠ ┐
│   ④ contenuto REALE                                   │
│ ⑤ 1920×1080 · 04:12:33 · 0x7f2a         ◺ taglio 45° │
└───────────────────────────────────────────────────────┘
```

**Regola dell'asimmetria**: taglio a 45° su **uno o due vertici, mai zero e mai quattro**.

## 10.3 Movimento

| Elemento | Comportamento |
|---|---|
| Anelli concentrici | **46s / 74s / 120s / 240s** per giro. Mai multiple tra loro |
| Boot sequence | contorni disegnati una linea alla volta |
| Apertura pannello | `clip-path` che si espande, 180 ms, `easeOutQuart` |
| Valori numerici | interpolazione del valore, mai del DOM |
| Fondo | **immobile** |

**Nessuna animazione senza causa.** L'animazione decorativa continua è il marchio del finto.

## 10.4 anime.js — API e budget di frame

anime.js **v4**, ESM: `import { animate, createTimeline, stagger, svg, utils } from 'animejs'`.

| Elemento | API |
|---|---|
| Boot sequence | `svg.createDrawable()` + `createTimeline()` |
| Apertura/chiusura WinBox | `animate()` su `clipPath`/`opacity`, hook `onminimize`/`onmaximize`/`onclose` |
| Anelli | `animate(el,{rotate:360,duration:46000,loop:true,ease:'linear'})` |
| Contatori | `animate(obj,{value:n,modifier:utils.round(1)})` |
| Dock | `stagger(60)` |

**Dove NON usarlo**: mai nel render loop di three.js; mai per i glifi PixiJS (usano il ticker GPU); mai due engine.

**Budget di frame (~16 ms)**: three.js ≤ 8 ms · PixiJS ≤ 3 ms · anime.js + layout ≤ 4 ms · margine 1 ms.

---

# 11. Replicare la UI dei riferimenti

## 11.1 Analisi dei riferimenti

Ho analizzato diciotto immagini. Si dividono in **due famiglie**, e la distinzione è la cosa più importante di questa sezione.

### Famiglia A — information design cinematografico (la maggioranza)

Desktop Iron Man 2/3, schede archivio, board investigativa, globo GPS, tavola periodica.

| Caratteristica | Osservazione |
|---|---|
| Fondo | blu-nero quasi puro, mai grigio |
| Luminosità | dal **contrasto** contro il nero, **mai da bloom o glow** |
| Densità | estrema. Lo spazio vuoto è raro e sempre intenzionale |
| Tipografia | condensata per i titoli, **monospace per ogni numero** |
| Bordi | hairline, mai spessi |
| Accento caldo | rosso-arancio, **~10% della superficie**, sempre semantico (allarme, valore critico) |
| Contenuto | dati veri, pagine web vere, video veri incassati |
| Etichette | `ver 12`, `A02`, `QUERY COMPLETE`, coordinate, hex |

Osservazione decisiva: nel desktop Iron Man 2 sono incassate **pagine web reali** — la barra URL di YouTube è visibile in uno dei riquadri. Il Suo approccio con `<webview>` (§6.3) è esattamente quello, non un'approssimazione.

Due motivi ricorrenti che vale la pena isolare:
- **Piani stratificati in prospettiva** (schede archivio): documenti e immagini su piani Z traslucidi, con filmstrip di miniature sotto.
- **Board investigativa in spazio 3D libero**: carte a profondità e angoli diversi, non in griglia, con chip-etichetta rossi.

### Famiglia B — asset motion-graphics da stock

Il "digital counter tool" con i contatori circolari.

**Questa famiglia contraddice la Famiglia A e il Suo stesso pilastro.** Ha bloom, alone, saturazione. È decorazione, non informazione: quei quadranti non mostrano nulla di vero.

**Deve scegliere.** Il mio consiglio è netto: **Famiglia A**. È più difficile da imitare male, invecchia meglio, e soprattutto è coerente con un sistema che mostra dati reali. Se prende gli anelli della Famiglia B, li prenda come *forma* — tick, archi segmentati, quadranti — e li renda senza glow, con dati veri dentro.

## 11.2 Si può replicare? Sì — ma il codice è il 30%

**Verdetto tecnico: sì, integralmente.** Non c'è nulla in quelle immagini che il web moderno non renda. Nessuna richiede tecnologie esotiche.

**Ma il vero contenuto di quelle interfacce non è tecnologico.** Il 70% è:
- disciplina tipografica (due font, cinque corpi, mai deroghe)
- densità informativa (schermi pieni di dati veri)
- un solo accento cromatico usato con parsimonia semantica
- zero decorazione senza funzione

Le librerie della §11.3 Le danno il 30%. Il resto lo dà la §11.6 e il metodo della §11.7. Chi installa augmented-ui e si ferma lì ottiene un template cyberpunk, non un JARVIS.

## 11.3 Stack librerie — verificato

Tutti i repository sono stati verificati ad agosto 2026.

### Chrome dei pannelli

**augmented-ui** — CSS puro, licenza BSD-2, ~93% di compatibilità browser. Risolve il problema esatto degli angoli tagliati e delle cornici irregolari senza elementi extra, immagini o clip-path calcolati a mano. Il progetto lo descrive così: la Sci-Fi tradizionale sul web richiede elementi extra per ogni taglio, ruotati e posizionati per coprire gli angoli; augmented-ui elimina tutto questo con poche custom property.

- Repo: `https://github.com/propjockey/augmented-ui`
- Docs + editor visuale: `https://augmented-ui.com/docs/`
- CDN: `https://unpkg.com/augmented-ui@2/augmented-ui.min.css`

```html
<div class="jarvis-panel" data-augmented-ui="tl-clip br-clip border">
```

⚠️ **Attenzione**: `clip-path` crea un nuovo stacking context e appiattisce le trasformazioni 3D. Se un pannello augmented deve stare su un piano 3D (§11.5), l'elemento augmented va **annidato dentro** quello trasformato, non fuso con esso.

**Alternativa più leggera**: `https://github.com/MYRWYR/CSS-sci-fi-ui`. Meno potente, ma se Le basta il taglio a 45° i token della §10.1 con `clip-path` a mano bastano.

### Grafici e dati densi

**uPlot** — MIT. È la scelta corretta per le strisce di telemetria: aggiornando 3.600 punti a 60fps usa **il 10% di CPU e 12,3 MB di RAM**; le librerie canvas successive più veloci (Chart.js ed ECharts) usano rispettivamente 40%/77 MB e 70%/85 MB. Regge lo streaming a 60fps fino a circa 100k punti in vista.

- Repo: `https://github.com/leeoniya/uPlot`
- Demo streaming: `https://leeoniya.github.io/uPlot/demos/sine-stream.html`

Nota di progetto perfettamente allineata alla Sua §10.3: uPlot **non ha transizioni né animazioni**, per scelta dichiarata dell'autore — le considera distrazioni. Esattamente la Sua regola.

**D3** (ISC) per tutto ciò che uPlot non fa: quadranti radiali, archi segmentati, tavole periodiche, grafi a nodi. Usi i moduli separati, non il bundle: `d3-shape`, `d3-scale`, `d3-geo`, `d3-array`.

### 3D

**three.js** più questi addon:

| Necessità | Soluzione | Perché |
|---|---|---|
| Linee di spessore controllato | **`Line2` / `LineSegments2` / `LineMaterial`** da `three/addons/lines/` | ⚠️ **critico**: `LineBasicMaterial.linewidth` è ignorato su quasi tutte le piattaforme. Senza questi addon il Suo wireframe sarà sempre a 1px, e il pilastro "0.5px con densità variabile" resta lettera morta |
| " versione modulare | **three-fatline** `https://github.com/vasturiano/three-fatline` | modularizzazione degli stessi file |
| " alternativa a mesh | **meshline** `https://github.com/utsuboco/THREE.MeshLine` | strip di triangoli billboard invece di GL_LINE; supporta larghezza variabile lungo la linea |
| Globo tattico con archi | **three-globe** `https://github.com/vasturiano/three-globe` | fa esattamente il globo del riferimento: layer di archi che si alzano dalla superficie collegando coordinate, con altitudine, dash e risoluzione di curva configurabili |
| Proiezione ortografica | **d3-geo** `geoOrthographic()` | **sostituisce la matematica a mano della §17.4**: è già implementata, testata e con il clipping dell'emisfero |
| Etichette testuali nel 3D | **troika-three-text** `https://github.com/protectwise/troika` | testo SDF nitido a qualunque zoom. `TextGeometry` nativo è pesante e brutto |
| Picking gesti e hover | **three-mesh-bvh** | raycast accelerato di ordini di grandezza |

Documentazione ufficiale delle linee spesse: `https://threejs.org/docs/pages/Line2.html`, `https://threejs.org/docs/pages/LineMaterial.html`, esempio `https://threejs.org/examples/#webgl_lines_fat`.

### Massa dati e testo

**PixiJS v8** per i glifi esadecimali scorrevoli e i log di calcolo: migliaia di elementi sulla GPU invece che nel DOM.

**Effetto "decodifica" del testo**: ~30 righe custom, oppure `baffle.js`. Non serve una dipendenza per questo.

### Font — la scelta che conta più delle librerie

| Ruolo | Font | Fonte |
|---|---|---|
| Interfaccia, titoli | **Barlow Semi Condensed** (400/500/600) | Google Fonts |
| Ogni dato e coordinata | **IBM Plex Mono** (400/500) | Google Fonts / IBM |

Se vuole avvicinarsi all'Eurostile Extended dei film, alternative gratuite: **Michroma**, **Chakra Petch**, **Saira Condensed**, **Share Tech Mono**.

⚠️ **Eviti Orbitron.** È il font che grida "sci-fi da template" più di qualunque altro. È la firma visiva del progetto amatoriale.

## 11.4 La regola architetturale: WebGL o DOM?

Questa è la decisione tecnica che distingue un'implementazione da senior da una da principiante, e i riferimenti la impongono.

| Motivo nei riferimenti | Tecnologia | Perché |
|---|---|---|
| Wireframe, globo, nuvole di punti, anelli reattore | **three.js (WebGL)** | geometria pura |
| Glifi di massa, log scorrevoli | **PixiJS (WebGL)** | migliaia di sprite |
| Pannelli, tabelle, tavola periodica, liste | **DOM + CSS** | è testo: deve essere selezionabile e nitido |
| **Piani stratificati con documenti** | **DOM + CSS 3D** (`transform-style: preserve-3d`, `perspective`) | ◄ contengono testo e immagini |
| **Board investigativa in spazio 3D** | **DOM + CSS 3D** | ◄ carte con foto, video, testo |
| Web e YouTube incassati | **`<webview>` Electron** | contenuto vero |

**L'errore da non fare**: mettere in three.js le carte della board investigativa e i documenti dei piani stratificati. Sembra la scelta "più 3D", ed è sbagliata. Rasterizzare testo in WebGL lo rende sfocato, non selezionabile, costoso da aggiornare, e rende impossibile incassare una `<webview>`.

CSS 3D fa la stessa cosa con testo reale, `<video>` reali e `<webview>` reali dentro i piani:

```css
.stage-3d { perspective: 2400px; transform-style: preserve-3d; }
.plane {
  position: absolute;
  transform-style: preserve-3d;
  transform: translate3d(var(--x), var(--y), var(--z))
             rotateY(var(--ry)) rotateX(var(--rx));
  will-change: transform;
}
```

Il compositore di Chromium le gestisce sulla GPU. Costo: quasi zero.

## 11.5 Dai riferimenti ai componenti

Mappa concreta di cosa costruire e con cosa.

| Componente | Fonte visiva | Tecnologia | Fase |
|---|---|---|---|
| Griglia pannelli con angoli tagliati | tutti | augmented-ui + token | 1b |
| Strisce telemetria live | desktop MCU | uPlot | 1b |
| Tavola periodica | riferimento chimico | **CSS Grid** — il pezzo più impressionante è il più banale | 5 |
| Quadranti radiali con tick | HUD, contatori | D3 `d3-shape` arc + SVG | 5 |
| Anelli reattore concentrici | logo, HUD | SVG + anime.js (46/74/120/240 s) | 5 |
| Globo con archi | GPS locator | three-globe + d3-geo | 5 |
| Nuvola di punti sferica | server trace | three.js `Points` + inversione `acos(2u−1)` (§17.4) | 5 |
| Grafo a nodi | mesh agenti | D3 `d3-force` o layout fisso + SVG | 5 |
| Piani stratificati documenti | archivio | **CSS 3D** + filmstrip | 6 |
| Board investigativa | board Iron Man 3 | **CSS 3D** + chip-etichetta | 6 |
| Web e video incassati | desktop MCU | `<webview>` | 6 |
| Log esadecimali scorrevoli | tutti | PixiJS | 5 |
| Equalizzatore vocale | GPS locator | uPlot o canvas custom su dati veri del microfono | 3 |

Nota sulla tavola periodica: sembra la cosa più complessa del riferimento, ed è **una CSS Grid con 118 celle**. È istruttivo — nelle UI cinematografiche l'effetto viene dalla densità e dalla coerenza, non dalla complessità tecnica di ogni pezzo.

## 11.6 Le sei regole che fanno la differenza

Le librerie non bastano. Queste sì.

1. **Due font, cinque corpi, nessuna deroga.** Ogni numero in monospace. È il 40% dell'effetto.
2. **Un solo accento caldo, sempre semantico.** Il rosso significa allarme o valore critico. Non decora mai. Massimo 10% della superficie colorata.
3. **Densità.** Uno schermo mezzo vuoto non sembrerà mai JARVIS. Se un pannello ha poco da dire, lo rimpicciolisca — non lo riempia di spazio.
4. **Dati veri.** Vedi §11.9. È la causa singola più frequente di UI generata che "sembra finta".
5. **Zero glow.** La luminosità viene dal contrasto contro il nero. Il momento in cui aggiunge `filter: drop-shadow` o un bloom in post-processing, scivola nella Famiglia B.
6. **Asimmetria progettata.** Uno o due angoli tagliati per pannello, mai zero e mai quattro. Velocità di rotazione non multiple. Il varco nell'anello è un parametro con un nome, non `Math.random()`.

## 11.7 Come far lavorare Claude Code sul design

Questo è il metodo, ed è la risposta operativa alla Sua richiesta di non ottenere risultati brutti o banali.

**Il problema di fondo**: Claude Code scrive componenti visivi **alla cieca**. Non vede il risultato. Senza un ciclo di feedback produce codice plausibile e brutto, e non ha modo di accorgersene.

**La soluzione: una galleria di componenti più un ciclo di verifica visiva.**

### Passo 1 — la galleria

Prima di qualunque componente, costruisca `ui/gallery.html`: una pagina che rende **ogni componente isolato**, con il quality gate attivo, dati finti-ma-strutturalmente-veri, e una griglia di riferimento sovrapponibile.

```
ui/gallery.html
  ?component=reactor-ring     → un solo componente, isolato
  ?component=all              → tutti, in griglia
  &grid=1                     → griglia 110px sovrapposta
  &tokens=audit               → evidenzia ogni valore NON proveniente da tokens.css
```

`&tokens=audit` è il pezzo che vale la pena scrivere: uno script che scorre il CSS calcolato e colora di magenta ogni elemento con un colore, una spaziatura o un corpo che non corrisponde a un token. Un componente conforme è invisibile all'audit; uno abusivo si illumina.

### Passo 2 — il ciclo di verifica

Con Playwright (o Puppeteer) Claude Code chiude il cerchio da solo:

```bash
# in package.json
"shot": "playwright screenshot --viewport-size=1920,1080 \
         'http://localhost:5173/gallery.html?component=$1' shots/$1.png"
```

Il ciclo che deve girare per **ogni** componente:

```
1. FORGE scrive il componente
2. lo rende nella galleria
3. screenshot con Playwright
4. FORGE GUARDA lo screenshot
5. lo confronta con la checklist §11.8 e con l'immagine di riferimento
6. se un solo punto fallisce → RISCRIVE, non rattoppa
7. ripete fino a conformità
```

Il passo 4 è quello che cambia tutto. Claude Code **può vedere le immagini**. Uno screenshot del proprio output più l'immagine di riferimento nello stesso contesto trasformano la generazione da cieca a iterativa.

### Passo 3 — prompt con riferimento ancorato

Non chieda mai "fai un pannello telemetria bello". Chieda:

> Costruisci il componente `telemetry-strip` in `ui/src/panels/telemetry.js`.
> Riferimento visivo: `docs/design-reference/desktop-mcu-02.png`, riquadro in basso a destra.
> Vincoli: solo token da `tokens.css`; uPlot per la serie; dati veri dal topic `telemetry` del WebSocket; anatomia a cinque parti §10.2; taglio a 45° sul solo vertice in basso a destra.
> Poi: rendilo in `gallery.html?component=telemetry-strip&tokens=audit`, fai lo screenshot, guardalo, verifica la checklist §11.8 punto per punto e riporta l'esito di ciascuno. Se un punto fallisce, riscrivi.

### Passo 4 — cosa mettere nel repo

```
docs/design-reference/
├── README.md              # la §11 di questo documento
├── famiglia-a/            # i riferimenti da seguire
└── famiglia-b/            # marcati "NON SEGUIRE — contiene glow"
```

Le immagini di riferimento nel repo, con il README che spiega quale famiglia seguire, sono ciò che rende ripetibile il risultato tra una sessione e l'altra.

## 11.8 Checklist di rifiuto

Un solo ✗ significa **riscrivere**, non aggiustare.

```
GEOMETRIA
□ border-radius è 0 ovunque?
□ taglio a 45° su 1–2 vertici (mai 0, mai 4)?
□ ogni spaziatura è multiplo di 4?
□ pesi di linea solo hair/base/bold?

COLORE
□ tutti i colori da tokens.css? (audit magenta pulito)
□ accento caldo < 10% della superficie colorata?
□ tinte totali ≤ 3?
□ zero gradienti fuori dalla ricetta del vetro?
□ ZERO drop-shadow, ZERO bloom, ZERO glow?

TIPOGRAFIA
□ solo i cinque gradini?
□ tutti i numeri in --font-mono?
□ etichette caps con letter-spacing ≥ .10em?
□ niente sotto 8.5px, corpo mai sotto 14px?

CONTENUTO
□ i dati sono VERI?
□ etichetta + ID/versione + piede tecnico presenti?
□ almeno un valore numerico monospace?
□ la densità regge il confronto con l'immagine di riferimento?

MOVIMENTO
□ ogni animazione risponde a un evento reale?
□ zero animazione ambientale nel fondo?
□ solo anime.js?

TECNOLOGIA
□ il testo è nel DOM, non rasterizzato in WebGL?
□ le linee 3D usano Line2/LineMaterial, non LineBasicMaterial?
□ i numeri vivono in uPlot o SVG, non in canvas custom improvvisato?
```

## 11.9 Divieto di dati finti

| Vietato | Obbligatorio |
|---|---|
| `Lorem ipsum` | testo reale dal contesto |
| `Item 1`, `Elemento 2` | nomi veri da filesystem o API |
| `100`, `50%`, `1000` | valori da psutil, API, filesystem |
| Timestamp inventati | `time.time()` |
| Grafici con dati casuali | serie reali dal ring buffer |

**Se un pannello non ha ancora la sua fonte**, mostri lo stato vuoto — `NESSUNA SORGENTE COLLEGATA` in `--txt-ghost`. Uno stato vuoto onesto sembra un sistema in costruzione; dati finti sembrano un giocattolo.

*(Unica eccezione: la galleria di §11.7, dove i dati sono finti per costruzione ma devono avere la **forma** di dati veri — lunghezze di stringa realistiche, numeri non tondi, timestamp plausibili.)*

## 11.10 Disciplina 3D — nessuna geometria non parametrica

**Nessun vertice è mai scritto a mano.** Ogni oggetto nasce da una funzione generatrice con tabella di parametri dichiarata. Come in CAD reale: non si disegna una flangia, la si parametrizza.

```javascript
// ui/src/three/component.js
export class ParametricComponent {
  constructor(params, meta) {
    this.params = Object.freeze({ ...params });
    this.meta = { unit: "mm", ...meta };
    this._validate();
  }
  _validate() {
    for (const [k, v] of Object.entries(this.params)) {
      if (typeof v === "number" && !Number.isFinite(v))
        throw new Error(`parametro non finito: ${k}`);
      if (typeof v === "number" && v < 0 && !k.startsWith("offset"))
        throw new Error(`parametro negativo non ammesso: ${k}=${v}`);
    }
  }
  /** Densità di segmenti dalla CURVATURA, non costante. */
  segmentsFor(radius, arcAngle = Math.PI * 2, targetChordMm = 1.2) {
    return Math.max(8, Math.min(256, Math.ceil((radius*arcAngle)/targetChordMm)));
  }
  build() { throw new Error("build() va implementato"); }
  constructionLines() { return null; }
}
```

```javascript
export class ReactorRing extends ParametricComponent {
  constructor(p = {}) {
    super({
      outerR: p.outerR ?? 120, thickness: p.thickness ?? 8,
      tickCount: p.tickCount ?? 48,
      gapStart: p.gapStart ?? 0.62,      // rad — l'asimmetria è PROGETTATA
      gapSweep: p.gapSweep ?? 0.31,
      periodSec: p.periodSec ?? 46,
    }, { name: "reactor-ring", version: "v1" });
  }
  build() {
    const { outerR, thickness, gapStart, gapSweep } = this.params;
    const innerR = outerR - thickness;
    const seg = this.segmentsFor(outerR);          // ◄ densità da curvatura
    const pts = [];
    for (let i = 0; i <= seg; i++) {
      const a = (i / seg) * Math.PI * 2;
      if (a > gapStart && a < gapStart + gapSweep) continue;
      pts.push(Math.cos(a)*outerR, Math.sin(a)*outerR, 0);
      pts.push(Math.cos(a)*innerR, Math.sin(a)*innerR, 0);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pts), 3));
    return g;
  }
}
```

**Le sette regole:**
1. Parametri dichiarati con unità (mm). Mai numeri magici in `build()`.
2. Densità dalla curvatura: `segmentsFor()` obbligatoria. Un cerchio a 32 segmenti fissi è la firma del generato male.
3. Linee di costruzione preservate: distinguono un pezzo ingegnerizzato da una forma.
4. Asimmetria progettata, non casuale. `Math.random()` nella geometria è vietato (tranne le nuvole di punti, dove la casualità *è* la specifica).
5. `BufferGeometry` con `Float32Array`. Mai geometrie standard.
6. Massimo due materiali: linea wireframe, faccia semitrasparente.
7. Bounding box dichiarato e verificato.

## 11.11 Quality gate — codice che gira

```javascript
// ui/src/three/quality-gate.js
const LIMITS = { minVertices:24, maxVertices:20000, maxMaterials:2, maxBBox:5000 };

export function qualityGate(component, geometry, materials) {
  const fail = [];
  const n = geometry.getAttribute("position").count;
  if (n < LIMITS.minVertices) fail.push(`vertici ${n} < ${LIMITS.minVertices}`);
  if (n > LIMITS.maxVertices) fail.push(`vertici ${n} > ${LIMITS.maxVertices}`);
  if (materials.length > LIMITS.maxMaterials)
    fail.push(`materiali ${materials.length} > ${LIMITS.maxMaterials}`);

  geometry.computeBoundingBox();
  const bb = geometry.boundingBox;
  const dim = ["x","y","z"].map(a => bb.max[a] - bb.min[a]);
  if (dim.some(d => d > LIMITS.maxBBox))
    fail.push(`bbox ${dim.map(d=>d.toFixed(0))} — probabile errore di trasformazione`);
  if (dim.some(d => d === 0)) fail.push("geometria degenere");
  if (dim.some(d => !Number.isFinite(d))) fail.push("geometria con NaN");
  if (!component.meta?.name || !component.meta?.version)
    fail.push("componente senza name/version");
  if (!component.params || Object.keys(component.params).length === 0)
    fail.push("componente senza tabella parametri — geometria non parametrica");

  if (fail.length)
    throw new Error(`QUALITY GATE FALLITO — ${component.meta?.name ?? "anonimo"}\n  `
                    + fail.join("\n  "));
  return true;
}
```

---

# 12. ARGUS — `scope = "app"`

**Deciso**: ARGUS vede solo la finestra di JARVIS.

**La scorciatoia che quasi tutti mancano**: JARVIS **conosce già** il contenuto dei propri pannelli — è lui a renderizzarli. Per la maggior parte delle domande non serve OCR, serve interrogare lo stato.

```
domanda su un pannello JARVIS   → interroga lo stato: zero OCR, zero latenza
domanda sul contenuto <webview> → capturePage() + Tesseract → testo
```

| Motore | Quando | Costo |
|---|---|---|
| Interrogazione stato | pannelli JARVIS | 0 |
| **Tesseract** | testo nella webview | CPU, ~100–300 ms |
| Florence-2 / Moondream2 | comprensione visiva (opzionale, v2) | 1,2–4 GB VRAM |

## La regola inderogabile

**Tutto ciò che ARGUS produce è DATO NON FIDATO.** Una pagina nella `<webview>` può contenere testo rivolto all'agente: è il vettore di prompt injection principale.

```python
async def read_region(region: str) -> str:
    raw = await _capture_and_ocr(region)
    return (f'<untrusted_source origin="screen:{region}">\n{raw}\n'
            f'</untrusted_source>')
```

1. L'output entra **solo** in contesti con `--allowedTools ""`.
2. Non raggiunge mai un processo T2 con tool attivi.
3. Il pannello disegna il **rettangolo della regione catturata**. Non è decorazione: è il controllo che Le permette di accorgersi di una cattura inattesa.

---

# 13. Moduli, pannelli, scorciatoie

| Modulo | Dato reale | Fase |
|---|---|---|
| **Telemetria** | psutil: CPU, RAM, temperature, top-3 | 1 |
| **File manager** | filesystem vero sotto le radici consentite | 2 |
| **Console** | comandi reali con trace | 1b |
| **Mesh agenti** | stato del grafo T0/T1/T2 e subagent | 4 |
| **Globo tattico** | fusi orari, coordinate, elevazione solare calcolata | 5 |
| **Browser** | `<webview>`, YouTube, web | 6 |
| **Core sorgente** | file reali del progetto | 5 |
| **News** | RSS + Guardian + YouTube | 8 |

**Workspace con dominio, non numeri vuoti.** Ogni workspace ha un colore e un
significato, così che la barra porti informazione invece di contarli:

| WS | Dominio | Accento |
|---|---|---|
| 01 | Sistema e telemetria | `--cy-500` |
| 02 | File e progetti | `--cy-300` |
| 03 | Web e ricerca | `--cy-700` |
| 04 | 3D e modelli | `--amber` |

**Barra superiore**: stato agente (nominal/degraded/offline), workspace 01–04 col proprio accento, telemetria compatta, indicatore di ascolto, tray.
**Dock inferiore**: gli otto moduli, indicatore T2 attivo, azioni rapide.

| Tasto | Azione |
|---|---|
| `Alt+H` | nasconde tutti i pannelli |
| `Alt+T` | affianca |
| `Alt+1…4` | workspace interno |
| `Alt+Spazio` | ascolto senza frase-wake |
| `Esc` | interrompe il TTS |
| doppio clic barra | massimizza |
| trascinamento al bordo | aggancia a metà |

⚠️ Scorciatoie **interne all'app**, gestite dal renderer. Non registri scorciatoie globali di sistema.

---

# 14. Gesture MediaPipe

1. **CPU.** 30fps su CPU, `delegate=CPU` esplicito.
2. **Stessa allowlist dei comandi vocali.** Una gesture emette un intento sul bus, come T0.
3. **Nessuna gesture può innescare un tool con `side_effect=True`.** Un falso positivo è indistinguibile da un comando. Il vincolo è **imposto nel registry**, non lasciato alla disciplina.

| Gesto | Intento | Ammesso |
|---|---|---|
| pizzico + trascina | sposta pannello | ✅ |
| rotazione a due mani | ruota mesh 3D | ✅ |
| palmo aperto | espandi pannello | ✅ |
| spinta laterale | cambia workspace | ✅ |
| *(qualsiasi)* | crea, sposta, cestina file | ❌ |

**Isteresi**: gesto stabile per 5 frame (~166 ms). **Picking**: three-mesh-bvh.

---

# 15. News proattive

| Fonte | Costo | Note |
|---|---|---|
| **RSS/Atom** (ANSA, Il Post, BBC, Reuters) | **gratis, illimitato** | la base |
| **The Guardian Open Platform** | gratis con chiave | l'unica API news gratuita seria: **corpo completo** |
| **GNews** | free tier limitato | italiano incluso |
| **NewsAPI.org** | free **solo sviluppo**, 100/giorno | ⚠️ licenza free **vieta la produzione** |
| **YouTube Data API v3** | gratis, quota | **video** |

⚠️ **Reuters e AP non hanno feed video gratuiti.** Il notiziario video sarà YouTube embed nella `<webview>`.

```
conversazione → [estrattore argomenti] (haiku, batch 60s, effort low)
              → [watcher feed] → [gate rilevanza] → [budget]
              → [card news] + menzione vocale breve
```

**Collector pluggabili.** Non un modulo news monolitico: un file per sorgente
in `core/news/collectors/`, ognuno con la stessa interfaccia. Aggiungere una
sorgente = aggiungere un file.

```python
# core/news/collectors/base.py
class Collector(Protocol):
    name: str
    async def poll(self, topics: list[str]) -> list[Item]: ...
    def relevance(self, item: Item, topics: list[str]) -> float: ...
```

Collector iniziali: `rss.py`, `guardian.py`, `youtube.py`. Il motore proattivo
non sa nulla delle sorgenti: itera i collector registrati.

**Le regole senza cui abbandonerà la funzione in tre giorni**: 3 interruzioni/ora max · mai mentre Lei parla o con un pannello a pieno schermo · mai a metà frase · argomenti scaduti dopo 30 minuti · *"non parlarmene più"* chiude l'argomento in modo persistente.

**Il rischio**: un titolo è testo controllato da terzi. Stesse regole di §12 — contesti con zero tool, marcatura, mai verso T2 con tool attivi.

---

# 16. Autonomia e degradazione

| Soglia | Condizione | Azione |
|---|---|---|
| Termica | package > 75 °C | diagnostica critica + top-3 |
| Memoria | RAM > 90% | proposta chiusura processi |
| Quota LLM | rate limit da `api_retry` | sospende T2, **non fa fallire T1** |
| Contesto | budget token saturo | potatura (§5.5) |
| VRAM | headroom insufficiente | **rifiuta** il caricamento (§9) |
| Deepgram | chiave invalida, 429, rete | **ricade sul locale** e lo annuncia |
| **OAuth T1** | `authentication_failed` | **niente riavvio a ciclo**: `degraded_llm`, annuncio vocale, istruzione a schermo (§5.6) |

Ogni soglia emette su `agent.advisory`. **Nessuna soglia agisce senza annunciarlo.**

## 16.1b `jarvis doctor` — diagnosi di tutti i sottosistemi

Con core, T1 persistente, Deepgram, Vosk, Electron e WebSocket in gioco,
rispondere a "cosa e' rotto" senza uno strumento e' penoso. Da implementare
in **Fase 1**, non alla fine.

```
$ jarvis doctor
CORE          ok      pid 4412, uptime 3d 14h
WS            ok      unix core.sock, dir 0700, 2 client
T1 claude     ok      sessione viva 3d, ultimo turno 12s fa
T1 auth       ok      claude.ai / max
STT           ok      deepgram flux-general-multi
TTS           ok      deepgram flux
WAKE          ok      vosk it, 4 frasi, 7 trigger oggi
QUOTA         WARN    13/15 spawn T2 nella finestra
VRAM          ok      2.1/8.0 GB
```

Stesso contenuto sul topic `agent.advisory` e nel pannello telemetria, e
raggiungibile a voce con la frase T0 `"come stiamo"` (§7.6).

| Stato | Cosa funziona | Segnale |
|---|---|---|
| `nominal` | tutto | — |
| `degraded_voice` | Deepgram giù → fallback locale attivo | ambra + annuncio |
| `degraded_llm` | frasi-comando, T0, file, telemetria | ambra + *"opero in modalità ridotta"* |
| `offline` | frasi-comando, T0, file locali | rosso |

**Proprietà preziosa**: grazie al wake a frasi, anche in `offline` JARVIS risponde a *"papà è a casa"* — quel percorso non tocca né rete né LLM.

---

# 17. Modelli e progetti 3D

| Formato | Libreria |
|---|---|
| glTF/GLB, OBJ, STL, PLY | **trimesh**, **pygltflib** |
| STEP / BREP / CAD parametrico | **build123d** (Apache 2.0) o CadQuery |
| Rendering headless, thumbnail | **Blender via `bpy`** (GPL-2.0+) o **pyrender** |

## 17.4 Matematica dei quattro generatori

**① Nuvola di punti sferica uniforme.** L'errore classico è campionare θ e φ uniformemente: addensa ai poli. Corretto: inversione `acos(2u − 1)`.

```javascript
export class PointCloud extends ParametricComponent {
  constructor(p = {}) {
    super({ count: p.count ?? 4000, radius: p.radius ?? 200,
            flattenY: p.flattenY ?? 0.45 },
           { name: "point-cloud", version: "v1" });
  }
  build() {
    const { count, radius, flattenY } = this.params;
    const a = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = 2 * Math.PI * Math.random();
      const phi = Math.acos(2 * Math.random() - 1);   // ◄ uniforme
      a[i*3]   = radius * Math.sin(phi) * Math.cos(theta);
      a[i*3+1] = radius * Math.cos(phi) * flattenY;
      a[i*3+2] = radius * Math.sin(phi) * Math.sin(theta);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(a, 3));
    return g;
  }
}
```

**② Spline Catmull-Rom** — `THREE.CatmullRomCurve3` chiusa, estrusa in tubo wireframe. Passa **esattamente** per i punti di controllo. Segmenti da `segmentsFor()` sulla lunghezza della curva.

**③ Estrusioni asimmetriche** — `THREE.ExtrudeGeometry` su sagome 2D ad angoli netti tagliati a 45°, con foro centrale. Stesso motivo del taglio dei pannelli: coerenza 2D/3D.

**④ `BufferGeometry` con `Float32Array`.** Sempre.

**Il globo** — usi **`d3.geoOrthographic()`** invece di implementarla. Se preferisce a mano:

```javascript
// x = R·cos φ·sin(λ − λ₀)   y = −R·sin φ
// visibile se cos φ · cos(λ − λ₀) > 0
function orthographic(latDeg, lonDeg, lon0Deg, R) {
  const phi = latDeg * Math.PI / 180, dl = (lonDeg - lon0Deg) * Math.PI / 180;
  return { x: R*Math.cos(phi)*Math.sin(dl), y: -R*Math.sin(phi),
           visible: Math.cos(phi)*Math.cos(dl) > 0 };
}
```

L'elevazione solare deriva dalla **declinazione stagionale e dall'angolo orario** — nessun valore inventato. Anche il sole è un dato vero.

## SketchUp via MCP

Integrabile come tool di FORGE, con questi limiti da progettare:
1. **Nessun `import`** (validazione AST). 2. **Nessun accesso al filesystem.** 3. **Unità in pollici** — conversione dal mm. 4. **Sandbox AST.** 5. **`build_model` non è transazionale**: dopo un fallimento ispezioni `model_snapshot.totals`, non assuma lo stato pulito. 6. **Materiali duplicati falliscono in silenzio** (`SU_ERROR_PARTIAL_SUCCESS`): verifichi il conteggio in `model_snapshot.materials` dopo ogni `add_materials`.

**L'I/O resta nel core Python; SketchUp è solo motore geometrico.**

---

# 18. Sicurezza

## 18.1 Prompt injection

OWASP lo colloca in cima ai rischi LLM. Nei test Gray Swan/Shade il tasso di successo sale dal 4,7% (1 tentativo) al **63% (100 tentativi)**.

**Vettore principale**: la `<webview>` e l'output di ARGUS.

1. **Isolamento dei tool** — contenuto non fidato solo in contesti con zero tool. *Questa è la difesa vera.*
2. **`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.**
3. **Allowlist + conferma umana** su ogni `side_effect=True`.
4. **Solo cestino, mai delete.**
5. Marcatura `<untrusted_source>`. Il minimo, non sufficiente.

## 18.2 Trasporto core ↔ Electron — socket UNIX

**Non TCP, nemmeno su loopback.** Il canale è un **socket UNIX** in
`$XDG_RUNTIME_DIR/jarvis-os/core.sock`, dentro una directory a `0700`.

**Perché.** Su questo canale viaggia la conferma umana dei tool
`side_effect=True` (§6.2), cioè l'invariante 3. Con TCP su `127.0.0.1`
l'autorizzazione a rispondere *«sì, cancella»* apparterrebbe a **qualunque
processo dell'utente capace di aprire una socket verso quella porta**, e la
sola difesa sarebbe un token applicativo che il codice deve ricordarsi di
verificare. Con un socket UNIX la verifica la fa il **kernel**, sui permessi
del filesystem, prima che una riga di codice applicativo giri.

È lo stesso principio dell'invariante 27 sulle gesture: *imposto dalla
macchina, non lasciato alla disciplina*. Un invariante che il sistema non
impone decade alla terza sessione che tocca quel file.

**Il varco vero sono i permessi della directory, non quelli del socket.** Il
modo con cui `bind()` crea il file dipende dalla `umask`, e fra `bind()` e
`chmod()` esiste una finestra. La difesa che regge è la **directory a `0700`**:
un socket permissivo dentro una directory non attraversabile resta
irraggiungibile. Il `chmod 0600` sul socket è ridondanza, non la difesa.

**Il protocollo non cambia**, cambia solo l'ascoltatore: WebSocket su stream,
stessi topic, stessi messaggi JSON. Lato Python `websockets.unix_serve()`;
lato Electron il processo **main** con uno URL `ws+unix://`.

⚠️ **Conseguenza architetturale, da non scoprire in Fase 1b**: l'API
`WebSocket` del browser **non può** aprire un socket UNIX. Il renderer non
parlerà mai direttamente col core: la connessione la apre il processo **main**
e la espone al renderer via `contextBridge`. §3.2 lo prevedeva già («main:
bridge WS ↔ renderer»), ma smette di essere una scelta e diventa un vincolo.

**Niente token per-sessione.** Sarebbe servito col TCP. Col socket UNIX
aggiunge un meccanismo da mantenere e nessuna garanzia in più.

**Non esiste una porta da esporre per sbaglio.** È la proprietà migliore di
questa scelta, ed è il motivo per cui supera l'invariante 7 invece di
violarlo: `0.0.0.0` non è più un errore possibile, è un'opzione che non c'è.

**Windows** (§23): l'equivalente è una **named pipe** (`\\.\pipe\jarvis-os`)
con una ACL che concede il solo utente corrente. Per questo `socket_path()`
sta dietro `platform.Paths` e non è una costante nel codice.

## 18.3 Privacy

Il microfono è sempre attivo per il wake. **VAD e Vosk girano localmente**: l'audio senza frase nota **non lascia mai la macchina** e non viene salvato. Questo vale **anche con Deepgram primario** — solo dopo il match l'audio va in rete. Indicatore di ascolto sempre visibile, kill-switch a un clic, log dei trigger ispezionabile.

---

# 19. Legale — uso personale

**Marchi.** Il diritto dei marchi disciplina l'**uso nel commercio**: impedire confusione tra prodotti offerti al pubblico. Un progetto privato, non distribuito, non pubblicizzato **non è uso nel commercio**. Rischio pratico prossimo a zero.

**Voce.** Il right of publicity riguarda anch'esso lo sfruttamento commerciale. Per uso privato il quadro è molto più permissivo.

**L'unica condizione che conta:**

> Il momento in cui pubblica il repository, carica un video dimostrativo, o lo condivide anche gratuitamente, **l'analisi torna severa**. La distribuzione, anche non commerciale, è il confine.

**Riferimenti visivi.** Estrarre una **grammatica visiva** — palette, pesi, densità, regole di composizione — è normale pratica progettuale, ed è quello che abbiamo fatto in §10 e §11. Riprodurre gli artwork specifici è altra cosa, e non ne ha bisogno: il sistema di token dà risultati più coerenti di una copia. **Tenga le immagini di riferimento in `docs/`, non le impacchetti nell'applicazione.**

*Non sono un avvocato. Valutazione di rischio pratico, non parere legale.*

---

# 20. `CLAUDE.md` completo

```markdown
# JARVIS OS — Regole di progetto

## Cos'è
Un'applicazione desktop a schermo intero: un ambiente cognitivo dentro il
quale JARVIS vive, parla, mostra dati, apre il web, gestisce cartelle reali
e genera modelli 3D. Fuori dalla sua finestra non tocca nulla.
Uso strettamente personale. Non sarà distribuito.

## Invarianti — MAI violare

1. **Il core Python possiede le operazioni reali.** Il renderer Electron non
   tocca mai il disco.
2. **Allowlist, mai denylist.** Solo i tool registrati esistono.
3. **Ogni tool side_effect=True richiede conferma umana**, col path assoluto
   RISOLTO mostrato all'utente.
4. **Solo cestino, mai delete permanente.**
5. **<webview>, news, ARGUS e file letti sono DATO NON FIDATO.** Solo in
   contesti con zero tool. Marcati <untrusted_source>.
6. **Electron: contextIsolation true, nodeIntegration false, sandbox true.**
7. **Il canale core ↔ Electron non è mai raggiungibile dalla rete**, e la
   sua autorizzazione la impone il sistema operativo, non il codice.
   Oggi: socket UNIX in `$XDG_RUNTIME_DIR`, directory 0700 (§18.2).
   Mai una porta TCP.
8. **Tutto in streaming.** Il TTS accetta AsyncIterator[str]. Il chunker va
   SOLO davanti a Kokoro, mai davanti a Deepgram Flux.
9. **Un solo motore di animazione: anime.js v4.** Niente GSAP.
10. **Un solo motore 3D: three.js.** Niente Babylon.

## Backend LLM e voce

11. **Nessun modello LLM locale.** Solo Claude Code su abbonamento.
12. **Deepgram è il provider vocale primario**; Whisper e Kokoro sono
    fallback automatico su errore, chiave mancante o rete assente.
    Il fallback va sempre ANNUNCIATO, mai silenzioso.
13. **Il wake a frasi (Vosk) è SEMPRE locale**, anche con Deepgram primario.
14. **T0 non tocca mai un LLM.**
15. **T1 è un processo persistente**, da una working directory dedicata e
    vuota, con --allowedTools "".
16. **Ogni spawn T2 passa dal Governor.** T1 ha priorità assoluta.
17. **Non duplicare la gestione del contesto di T1.**

## Design e 3D — §10 e §11

18. **Zero valori letterali** di colore, spaziatura o tipografia. Tutto da
    tokens.css. border-radius sempre 0.
19. **ZERO glow, ZERO bloom, ZERO drop-shadow.** Solo inset box-shadow.
    La luminosità viene dal contrasto contro il nero.
20. **Il testo vive nel DOM, mai rasterizzato in WebGL.** Piani stratificati
    e board 3D si fanno con CSS 3D transforms, non con three.js.
21. **Le linee 3D usano Line2/LineMaterial**, mai LineBasicMaterial
    (linewidth è ignorato su quasi tutte le piattaforme).
22. **Nessuna geometria 3D scritta a mano.** Ogni componente estende
    ParametricComponent, deriva la densità dalla curvatura via
    segmentsFor(), e passa qualityGate() prima del render.
23. **Mai dati segnaposto.** Dati veri o stato vuoto esplicito.
24. **Ogni componente passa dal ciclo di verifica visiva §11.7**: rendi in
    gallery.html, screenshot con Playwright, GUARDA lo screenshot,
    verifica la checklist §11.8 punto per punto. Una violazione =
    riscrivere, non rattoppare.
25. **Nessuna animazione senza causa.** Zero animazione ambientale.
26. **Budget di frame: three.js ≤8ms, Pixi ≤3ms, anime.js ≤4ms.**

## Gesture

27. **Nessuna gesture può innescare un tool con side_effect=True.**
    Imposto nel registry, non lasciato alla disciplina.
28. **MediaPipe su CPU** (delegate=CPU esplicito).

## Portabilità

29. **Linux è il target attuale, Windows è previsto.** Ogni chiamata
    specifica di piattaforma (sandbox, audio, path, temperature) sta
    dietro un'interfaccia in core/platform/. Mai `bwrap` o percorsi
    POSIX sparsi nel codice applicativo.

## Stile codice

- Python 3.12, asyncio, type hints ovunque, pydantic per gli schema.
- Nessuna eccezione propaga all'LLM: ToolResult(ok=False, error=...).
- structlog, mai print. Le chiavi API MAI nei log.
- Unità: millimetri nel 3D, pixel nella UI, pollici solo verso SketchUp.

## Non fare senza chiedere
- Aggiungere dipendenze non elencate.
- Introdurre React.
- Eseguire stringhe generate dall'LLM.
- Toccare file fuori dalle radici consentite.
```

---

# 21. Repo e codice

## 21.1 Struttura

```
jarvis-os/
├── CLAUDE.md
├── pyproject.toml
├── config/{default.toml, settings.schema.json}
├── core/
│   ├── engine.py  router.py  memory.py  settings.py  ws_server.py
│   ├── gpu_scheduler.py
│   ├── platform/                 # ◄ isolamento OS (§23)
│   │   ├── base.py               # Protocol: Sandbox, Audio, Paths, Sensors
│   │   ├── linux.py              # bwrap, PipeWire, XDG
│   │   └── windows.py            # (futuro) Job Objects, WASAPI, %APPDATA%
│   ├── llm/{grammar.py, claude_t1.py, claude_t2.py, governor.py}
│   ├── providers/
│   │   ├── base.py  registry.py  chunker.py  health.py
│   │   ├── stt_deepgram.py  stt_local.py
│   │   └── tts_deepgram.py  tts_local.py
│   ├── voice/{wake.py, pipeline.py, audio_io.py}
│   ├── tools/{registry.py, files.py, system.py, model3d.py, web.py}
│   ├── sandbox/{runner.py, policy.py}
│   ├── vision/{argus.py, ocr.py}
│   ├── gestures/{tracker.py, mapping.py}
│   └── news/{feeds.py, topics.py, gate.py}
├── app/{main.js, preload.js, package.json}
├── ui/
│   ├── gallery.html              # ◄ galleria componenti (§11.7)
│   └── src/
│       ├── style/tokens.css      # ◄ sorgente unica di verità
│       ├── bus.js
│       ├── anim/{boot.js, panels.js, rings.js, counters.js}
│       ├── windows/{winbox.js, browser.js, confirm.js}
│       ├── three/
│       │   ├── component.js      # ParametricComponent
│       │   ├── quality-gate.js
│       │   ├── math/{pointcloud.js, spline.js, extrude.js, globe.js}
│       │   └── components/{reactor-ring.js, node-graph.js, ...}
│       ├── css3d/{planes.js, board.js}    # ◄ piani stratificati, board
│       ├── pixi/
│       └── panels/{telemetry.js, files.js, console.js, agents.js,
│                   globe.js, browser.js, source.js, news.js, settings.js}
├── .claude/agents/{forge.md, argus.md, edith.md, veronica.md}
├── security/  packaging/
└── docs/
    ├── design-reference/{README.md, famiglia-a/, famiglia-b/}
    └── acceptance/
```

## 21.2 Allowlist tipizzata

```python
# core/tools/registry.py
from typing import Any, Callable, Awaitable
from pydantic import BaseModel

class ToolResult(BaseModel):
    ok: bool
    output: Any = None
    error: str | None = None

class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]
    side_effect: bool
    gesture_allowed: bool = False
    handler: Callable[[BaseModel], Awaitable[ToolResult]]
    model_config = {"arbitrary_types_allowed": True}

_REGISTRY: dict[str, Tool] = {}

def register(tool: Tool) -> None:
    # il vincolo gesture è IMPOSTO qui
    if tool.side_effect and tool.gesture_allowed:
        raise ValueError("un tool con side_effect non può essere gesture_allowed")
    _REGISTRY[tool.name] = tool

def get(name: str) -> Tool | None: return _REGISTRY.get(name)
```

## 21.3 Protocol dei provider

```python
# core/providers/base.py
from typing import Protocol, AsyncIterator
from dataclasses import dataclass

@dataclass
class Transcript:
    text: str; is_final: bool; confidence: float = 1.0; end_of_turn: bool = False

@dataclass
class AudioChunk:
    pcm: bytes; sample_rate: int

class STTProvider(Protocol):
    name: str
    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]: ...
    async def aclose(self) -> None: ...

class LLMProvider(Protocol):
    name: str
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]: ...
    async def aclose(self) -> None: ...

class TTSProvider(Protocol):
    name: str
    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]: ...
    async def flush(self) -> None: ...
    async def interrupt(self) -> None: ...
    async def aclose(self) -> None: ...
```

## 21.4 Telemetria — versione corretta

⚠️ Le revisioni precedenti avevano **due bug reali**: `process_iter` su tutti i processi 2,5 volte al secondo (1000 letture di `/proc`/s per tre righe), e `cpu_percent` inaffidabile perché `process_iter` ricrea gli oggetti `Process`, azzerando il contatore.

```python
# core/ws_server.py
import asyncio, json, time, psutil
from websockets.asyncio.server import unix_serve
from websockets.exceptions import ConnectionClosed

from core.platform import RUNTIME_DIR_MODE, paths as platform_paths

FAST_HZ, SLOW_HZ = 2.5, 1.0
_proc_cache: dict[int, psutil.Process] = {}

def _package_temp() -> float | None:
    temps = getattr(psutil, "sensors_temperatures", lambda: {})()
    for key in ("k10temp", "coretemp", "zenpower"):
        if temps.get(key): return max(t.current for t in temps[key])
    return None

def _top3_cpu() -> list[dict]:
    """Cache persistente: cpu_percent è affidabile solo su oggetti riusati."""
    alive = set()
    for p in psutil.process_iter(["pid"]):
        pid = p.info["pid"]; alive.add(pid)
        if pid not in _proc_cache:
            try:
                _proc_cache[pid] = psutil.Process(pid)
                _proc_cache[pid].cpu_percent(None)      # innesca il contatore
            except psutil.NoSuchProcess:
                continue
    for pid in set(_proc_cache) - alive: _proc_cache.pop(pid, None)
    rows = []
    for pid, proc in list(_proc_cache.items()):
        try:
            rows.append({"pid":pid, "name":proc.name(), "cpu":proc.cpu_percent(None)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            _proc_cache.pop(pid, None)
    rows.sort(key=lambda d: d["cpu"], reverse=True)
    return rows[:3]

def sample_fast() -> dict:
    vm = psutil.virtual_memory()
    return {"topic":"telemetry", "ts":time.time(),
            "cpu_percent":psutil.cpu_percent(None),
            "ram_percent":vm.percent, "package_temp_c":_package_temp()}

def make_advisory(t, top3):
    temp = t.get("package_temp_c")
    if temp is not None and temp > 75:
        return {"topic":"agent.advisory","level":"critical",
                "reason":"package_temp>75C","top3":top3}
    if t["ram_percent"] > 90:
        return {"topic":"agent.advisory","level":"warn","reason":"ram>90%"}
    return None

async def _handler(ws, state_provider):
    # la UI è stateless, il core è l'unica fonte di verità
    await ws.send(json.dumps({"topic":"state.snapshot", **state_provider()}))
    top3, last_slow = [], 0.0
    try:
        while True:
            t = sample_fast(); now = time.time()
            if now - last_slow >= 1.0 / SLOW_HZ:
                top3, last_slow = _top3_cpu(), now
                t["top3"] = top3
            await ws.send(json.dumps(t))
            if (adv := make_advisory(t, top3)): await ws.send(json.dumps(adv))
            await asyncio.sleep(1.0 / FAST_HZ)
    except ConnectionClosed:
        return

async def main(state_provider, paths=None):
    """Ascolta su un socket UNIX, non su TCP. Il perché è in §18.2."""
    paths = paths or platform_paths()
    sock = paths.socket_path()

    # mkdir(mode=...) NON applica il modo se la directory esiste già, e la
    # umask puo' comunque toglierne bit: il chmod esplicito non e' ridondante.
    # E' questa directory la difesa vera, non i permessi del socket (§18.2).
    sock.parent.mkdir(parents=True, exist_ok=True)
    sock.parent.chmod(RUNTIME_DIR_MODE)                    # 0700

    # Un socket orfano da un crash precedente fa fallire il bind con EADDRINUSE.
    sock.unlink(missing_ok=True)

    async with unix_serve(lambda ws: _handler(ws, state_provider), str(sock)):
        sock.chmod(0o600)                                  # ridondanza, non difesa
        await asyncio.Future()
```

## 21.5 Router e stream di Claude Code

```python
# core/router.py — LangGraph 1.x
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    text: str; tier: Literal["t0","t1","t2"] | None
    result: dict | None; steps: int

MAX_STEPS = 6

def normalize(s): return {"text": s["text"].strip().lower(), "steps": 0}

def classify(s):
    """T0: parser a grammatica, NON un LLM. Sotto i 10 ms."""
    t = s["text"]
    if any(k in t for k in ("apri","chiudi","pannello","cerca file",
                            "cartella","volume","cpu","memoria")): return {"tier":"t0"}
    if any(k in t for k in ("scrivi","codice","genera","modello",
                            "organizza","analizza")): return {"tier":"t2"}
    return {"tier":"t1"}

def route(s) -> Literal["t0","t1","t2"]: return s["tier"]

async def t0(s): return {"result":{"ok":True}, "steps":s["steps"]+1}
async def t1(s): return {"result":{"streamed":True}, "steps":s["steps"]+1}
async def t2(s): return {"result":{"spawned":True}, "steps":s["steps"]+1}

def build_router():
    g = StateGraph(AgentState)
    for n, f in (("normalize",normalize),("classify",classify),
                 ("t0",t0),("t1",t1),("t2",t2)): g.add_node(n, f)
    g.add_edge(START,"normalize"); g.add_edge("normalize","classify")
    g.add_conditional_edges("classify", route, {"t0":"t0","t1":"t1","t2":"t2"})
    for n in ("t0","t1","t2"): g.add_edge(n, END)
    return g.compile()
```

```python
# core/llm/claude_t1.py — parsing dello stream
async for line in proc.stdout:
    evt = json.loads(line)
    if evt.get("type") == "stream_event":
        delta = evt.get("event", {}).get("delta", {})
        if delta.get("type") == "text_delta":
            yield delta["text"]                    # → dritto al TTS
    elif evt.get("type") == "system" and evt.get("subtype") == "api_retry":
        bus.publish("agent.advisory", {"level":"warn","reason":evt["error"],
                                       "retry_ms":evt["retry_delay_ms"]})
    elif evt.get("type") == "result":
        session_id, cost = evt["session_id"], evt.get("total_cost_usd")
```

---

# 22. Piano a fasi e stime

### FASE 0 — Scaffold · 2 gg
> Repo secondo §21.1, `CLAUDE.md` con §20, Python 3.12 con uv, `core/settings.py`. **`ui/src/style/tokens.css` con §10.1, completo, prima di qualunque componente.** **`core/platform/base.py`** coi Protocol OS-specifici (§23).

**Criterio**: pytest verde; i token esistono prima di ogni CSS; nessuna chiamata OS fuori da `platform/`.

### FASE 0b — Galleria · 2 gg · **NUOVA**
> `ui/gallery.html` con routing `?component=`, `&grid=1`, `&tokens=audit`. Script Playwright `npm run shot`. Le immagini di riferimento in `docs/design-reference/` con README che distingue Famiglia A da Famiglia B.

**Criterio**: un componente di prova non conforme si illumina di magenta nell'audit. Lo screenshot si genera con un comando.

### FASE 1 — Core, allowlist, sandbox, telemetria · 1,5 sett.
> `engine.py`, `tools/registry.py` (§21.2), `sandbox/runner.py` (bwrap dietro `platform/linux.py`), `ws_server.py` (§21.4), `gpu_scheduler.py` (§9).

**Criterio**: `websocat` riceve snapshot e telemetria reale. Un tool non registrato solleva. La sandbox blocca scrittura fuori radice e rete.

### FASE 1b — Fetta verticale · 3 gg
> Finestra Electron massimizzata, un pannello WinBox con augmented-ui e token, collegato al WebSocket, con una striscia uPlot che mostra CPU/RAM reali.

**Criterio**: catena core → WS → Electron → pannello. Il pannello supera la checklist §11.8 col ciclo §11.7.

### FASE 2 — Filesystem reale · 2 sett.
> `tools/files.py` (§6.1), validazione post-`resolve()`, solo cestino, conferma §6.2 col path risolto, pannello file manager.

**Criterio**: i tre casi Stonic funzionano con una conferma per operazione. Nessun path fuori radice passa, nemmeno con `../`.

### FASE 3 — Voce · 3 sett.
> Wake Vosk (§7.2). **Deepgram Flux primario** STT e TTS, fallback locale automatico e annunciato. T1 persistente (§5.2). Chunker solo davanti a Kokoro. Barge-in con `text_spoken` in memoria.

**Criterio**: *"papà è a casa"* esegue in **~30 ms offline**; conversazione col **primo suono entro ~1 s**; staccando la rete il fallback si attiva e viene annunciato; barge-in entro 200 ms.

### FASE 4 — T2, Governor, subagent, memoria · 1,5 sett.
> `claude_t2.py`, `governor.py`, i quattro subagent, `router.py`, `memory.py` (senza duplicare il contesto di T1).

**Criterio**: operazione lunga in T2 mentre T1 risponde. Su rate limit T2 si sospende, T1 sopravvive.

### FASE 5 — Ambiente 3D e design · 5 sett.
> `ParametricComponent` e `qualityGate` **prima** di qualunque componente. Poi: anelli (SVG+anime.js), globo (three-globe+d3-geo), nuvole di punti, grafo a nodi (D3), tavola periodica (CSS Grid), glifi (PixiJS). Linee 3D **solo** con `Line2`/`LineMaterial`. Etichette 3D con troika.

**Criterio**: 60fps dentro il budget §10.4. Ogni componente ha parametri, versione, supera il gate **e il ciclo di verifica visiva**. Zero dati segnaposto.

### FASE 6 — Web, YouTube, CSS 3D, ARGUS · 2,5 sett.
> `<webview>` in pannello (§6.3). IFrame Player API. YouTube Data API. **Piani stratificati e board investigativa in CSS 3D** (§11.4). ARGUS `scope="app"` (§12).

**Criterio**: *"apri YouTube e metti synthwave"* funziona. La board 3D contiene testo selezionabile e una `<webview>` viva. Il renderer resta senza accesso al filesystem.

### FASE 7 — Gesture · 2 sett.
> MediaPipe CPU, isteresi 5 frame, solo `gesture_allowed`. Picking con three-mesh-bvh.

### FASE 8 — News · 1,5 sett.
> RSS + Guardian + YouTube, estrattore, gate, budget. Contenuto news solo in contesti con zero tool.

**Criterio**: budget 3/ora rispettato. Test di injection: un contenuto con istruzioni iniettate non produce alcuna azione.

### Suite di eval — trasversale, da Fase 1 in poi

Con Claude Code che scrive il codice, gli eval passano da buona pratica a
**necessità**: sono l'unico modo per accorgersi che una sessione ha rotto
qualcosa che funzionava tre fasi fa.

| File | Cosa misura | Da |
|---|---|---|
| `tests/t0_corpus.py` | 100 frasi etichettate: intento e latenza mediana | Fase 3 |
| `tests/eval_tools.py` | ogni tool dell'allowlist su input validi e invalidi | Fase 2 |
| `tests/eval_paths.py` | nessun path fuori radice passa, nemmeno con `..` | Fase 2 |
| `tests/eval_injection.py` | contenuto con istruzioni iniettate non produce azioni | Fase 6 |
| `tests/eval_visual.py` | ogni componente passa quality gate e checklist §11.8 | Fase 5 |

Gira all'**inizio** di ogni fase, non solo alla fine: è così che scopre le
regressioni della fase precedente.

### FASE 9 — Packaging · 3 gg
> Unit systemd utente. `jarvis-voice.service` con **`Restart=always`**.

## Stime

| Fase | Effort |
|---|---|
| 0 Scaffold + token + platform | 2 gg |
| 0b Galleria e ciclo visivo | 2 gg |
| 1 Core, allowlist, sandbox, telemetria | 1,5 sett. |
| 1b Fetta verticale | 3 gg |
| 2 Filesystem reale | 2 sett. |
| 3 Voce | 3 sett. |
| 4 T2, Governor, memoria | 1,5 sett. |
| 5 Ambiente 3D e design | 5 sett. |
| 6 Web, CSS 3D, ARGUS | 2,5 sett. |
| 7 Gesture | 2 sett. |
| 8 News | 1,5 sett. |
| 9 Packaging | 3 gg |
| **Totale** | **~5 mesi** |

I due giorni della Fase 0b si ripagano da soli nella Fase 5: senza il ciclo di verifica visiva, ogni componente 3D richiede tre o quattro giri di correzione manuale.

---

# 23. Portabilità verso Windows

Lei ha detto: Linux ora, Windows in futuro. **Non costruisca per Windows adesso** — sarebbe lavoro speculativo. Ma quattro cose vanno isolate oggi, perché isolarle dopo costa dieci volte tanto.

```python
# core/platform/base.py
from typing import Protocol
from pathlib import Path

class SandboxRunner(Protocol):
    async def run(self, argv: list[str], rw_paths: list[Path],
                  timeout: float) -> tuple[int, str, str]: ...

class AudioIO(Protocol):
    async def input_stream(self, sample_rate: int): ...
    async def play(self, pcm: bytes, sample_rate: int) -> None: ...

class Paths(Protocol):
    def config_dir(self) -> Path: ...
    def data_dir(self) -> Path: ...
    def workspace(self) -> Path: ...

class Sensors(Protocol):
    def package_temp(self) -> float | None: ...
```

| Area | Linux (oggi) | Windows (domani) | Rischio se non isolata |
|---|---|---|---|
| **Sandbox** | `bubblewrap` + seccomp | Job Objects, AppContainer, o WSL2 | **alto** — è la differenza più grande. `bwrap` non esiste su Windows e non ha un equivalente diretto |
| **Audio** | PipeWire | WASAPI (via `sounddevice`) | medio — `sounddevice` astrae quasi tutto |
| **Path** | XDG (`~/.config`, `~/.local/share`) | `%APPDATA%`, `%LOCALAPPDATA%` | basso se usa `Paths` da subito |
| **Temperature** | `psutil.sensors_temperatures()` | **non disponibile** su Windows in psutil; servirebbe LibreHardwareMonitor o WMI | basso — degradi a `None` |

**Cosa funziona già su entrambi**: Electron, three.js, tutto il renderer, Claude Code CLI, Deepgram, Vosk, Kokoro, faster-whisper, MediaPipe, il WebSocket, l'allowlist.

**In pratica**: il renderer è già portabile al 100%. Del core, il 90% lo è. Il 10% che non lo è vive in `core/platform/` — e se rispetta l'invariante 29 del `CLAUDE.md`, il giorno che vuole Windows scrive un solo file nuovo.

⚠️ **La sandbox resta il punto duro.** Se Windows diventasse prioritario, valuti se il profilo `exec` Le serve davvero o se può sostituirlo con un container Docker/Podman, che è portabile. Ma non lo faccia adesso: su Linux `bwrap` è più leggero e più sicuro.

---

# 24. Cosa resta incerto

1. **Se Haiku 4.5 supporti i cinque livelli di effort.** La documentazione li descrive per Opus 5 e Fable 5. Lo misuri.
2. ~~La latenza di avvio~~ — **misurata**: mediana 2,41 s a freddo (§5.2). Resta da misurare **il primo token sulla sessione persistente**, che è il numero che conta davvero. Atteso 300–900 ms; se superasse 1,5 s il vantaggio del design si assottiglia e va rivalutato.
3. **La precisione di Vosk sulle Sue frasi**, in italiano, col Suo microfono e la Sua stanza. **Almeno 20 ripetizioni per frase** prima di fidarsi.
4. **Il link Pinterest non è stato analizzato** — bloccato ai fetch automatici.
5. **Il costo VRAM della scena 3D a 60fps**: nessuna fonte primaria lo quantifica. La stima 1–2 GB è prudenziale.
6. **MediaPipe**: la preoccupazione sulla roadmap viene da un issue tracker, non da una dichiarazione ufficiale.
7. **Valutazione legale**: non sono un avvocato.
8. **Il costo mensile Deepgram con uso quotidiano.** Non l'ho stimato: dipende da quante ore di audio genera. Lo monitori dal primo mese — è la sola voce di costo ricorrente del progetto, dato che l'LLM è già nel Suo abbonamento.
