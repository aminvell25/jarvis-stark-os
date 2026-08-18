# Fase 1 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 1
**Test**: 124 verdi · **Precedente**: `FASE-00.md`

Ogni criterio è riportato con l'esito e con **come** è stato verificato.
Quelli che non ho potuto verificare sono dichiarati tali, col motivo.

---

## I tre criteri di §22

### 1. «un client riceve snapshot e telemetria reale» — ✅ VERIFICATO

```bash
uv run python -m core.engine &
uv run python scripts/ws_probe.py
```

Lo `state.snapshot` arriva completo (fase, core, ws, settings, tools, gpu),
seguito da telemetria a 2,5 Hz con top-3 processi a 1 Hz.

**Che il dato sia misurato e non inventato** è verificato con una controprova
indipendente: `ws_probe.py` legge psutil nel proprio processo e stampa i due
blocchi accanto. RAM 52,5 % e temperatura 40,75 °C coincidevano.

⚠️ **Scostamento dichiarato**: il criterio nomina `websocat`, che **non è
installato** su questa macchina, e che col socket UNIX di §18.2 richiederebbe
comunque il supporto `ws+unix://`. Ho scritto `scripts/ws_probe.py` con la
libreria `websockets` già in `pyproject.toml`: zero dipendenze nuove, e resta
nel repo come strumento riusabile. La sostanza del criterio — *un client
esterno riceve snapshot e telemetria reale* — è verificata identica.

### 2. «un tool non registrato solleva» — ✅ VERIFICATO

`registry.invoke("cancella_tutto")` → `UnknownTool`, con l'elenco dei tool
registrati nel messaggio. Test: `tests/test_registry.py`.

§21.2 esponeva solo `get(name) -> Tool | None`, e un `None` non solleva: il
punto di invocazione mancava, ed è stato aggiunto (rilievo R9).

**La distinzione fra i due modi di fallire è voluta.** Un nome sconosciuto è un
errore di *instradamento* — l'allowlist è il contratto — e va rumoroso.
Argomenti invalidi o un handler che esplode sono *esiti*, e tornano come
`ToolResult(ok=False)`. Il `CLAUDE.md` vieta che un'eccezione arrivi all'LLM:
non è in contraddizione, perché la conversione avviene nel router, **Fase 4**.

### 3. «la sandbox blocca scrittura fuori radice e rete» — ✅ VERIFICATO

Test che **tentano davvero**, non che confrontano l'argv:

| Prova | Esito |
|---|---|
| `touch` dentro la radice consentita | riesce, e il file compare sull'host |
| `touch /etc/…`, `~/…`, `/usr/local/…` | `Read-only file system`, e l'host resta intatto |
| `getent hosts one.one.one.one` | fallisce |
| `socket.create_connection('1.1.1.1', 443)` | `ENETUNREACH` |
| `ip -o link` dentro il namespace | una sola interfaccia (`lo`) |
| `sleep 30` con timeout 1 s | ucciso, `SandboxTimeout` |

La prova sulla rete è una **connessione TCP reale** e non solo il fallimento
del DNS: un resolver rotto su una rete raggiungibile darebbe lo stesso esito.

---

## ❌ NON VERIFICATO — e perché

### seccomp non è applicato

§3.4 elenca `seccomp` fra le difese della sandbox. **Non c'è.**
`bwrap --seccomp FD` vuole un programma BPF compilato, e non esiste un binding
Python fra le dipendenze di §4; aggiungerne uno richiede il Suo assenso
(`CLAUDE.md`, «non fare senza chiedere»).

Alternative valutate e scartate: un BPF scritto a mano è sottilmente sbagliato
con facilità, e **un filtro che sembra funzionare ma non filtra è il caso
peggiore** — dà falsa sicurezza.

Cosa resta comunque attivo: `--unshare-all` toglie rete, IPC, PID, UTS, cgroup
e user namespace, che è ciò che conta contro la minaccia reale (codice generato
che tocca il disco o la rete), ed è verificato sopra.

Dichiarato nel codice, non lasciato al silenzio:
`core/platform/linux_sandbox.py::SECCOMP_APPLICATO = False`, con un test che
fallisce il giorno in cui qualcuno lo cambia senza aggiornare questo file.

### `/sys` dentro la sandbox è quello dell'host

Conseguenza diretta di `--ro-bind / /`, che §3.4 prescrive: bubblewrap non
offre un rimontaggio di sysfs. Quindi `ls /sys/class/net` elenca le interfacce
vere della macchina anche se il namespace di rete è vuoto.

**Non è un varco di accesso** — la rete resta irraggiungibile, provato sopra —
ma è una divulgazione di *informazione* sull'hardware. `--tmpfs /sys` la
chiuderebbe, ed è uno scostamento da §3.4 che non ho fatto senza chiederlo.
Registrato in `tests/test_sandbox_runner.py` con un test che fallirà il giorno
in cui qualcuno lo aggiunge, così che la decisione sia presa di proposito.

---

## Scostamenti dalla specifica, dichiarati

| # | Cosa | Decisione |
|---|---|---|
| **R5** | §9 presuppone una GPU discreta; questa è una APU a memoria unificata | `headroom = min(VRAM libera, RAM disponibile)`. **Recepito in SPEC rev 5.2**, §9 |
| **R6** | Il criterio nomina `websocat`, non installato | `scripts/ws_probe.py`, zero dipendenze nuove |
| **R7** | §16.1b vuole `jarvis doctor` in Fase 1, §22 non lo elenca | Fatto, coi cinque controlli che esistono |
| **R8** | seccomp | Non applicato, dichiarato sopra |
| **R9** | §21.2 non ha un punto in cui un tool sconosciuto sollevi | Aggiunto `invoke()`; `register()` rifiuta anche i nomi duplicati |
| **R10** | §21.4 chiama `psutil` dentro `ws_server.py` | Tutta la misura di sistema è dietro `Sensors`. Anche dove l'API di psutil è portabile, i suoi **modi di fallire** non lo sono: `sensors_temperatures()` non esiste su Windows (§23). Una regola netta sopravvive, una sfumata si erode |
| **R11** | §21.1 mette `core/sandbox/` fuori da `platform/`, ma l'invariante 29 vieta `bwrap` nel codice applicativo | **L'invariante vince.** L'argv e l'esecuzione bubblewrap stanno in `core/platform/linux_sandbox.py`; in `core/sandbox/policy.py` resta la validazione dei percorsi, che è neutra e vale su ogni piattaforma |

---

## Scoperte durante l'implementazione

**Il socket nasce `0o775`.** Misurato subito dopo `bind()`, con la umask di
questo sistema. È la conferma empirica di ciò che §18.2 afferma: la difesa vera
è la **directory a 0700**, e il `chmod 0600` sul socket è ridondanza, perché
fra `bind()` e `chmod()` esiste una finestra.

**`sun_path` accetta 108 byte**, misurato sul kernel. Il percorso di produzione
ne usa 34, ma il primo tentativo è fallito con `AF_UNIX path too long` da una
directory di scratch profonda — un messaggio che non dice a nessuno cosa fare.
`WsServer` ora verifica la lunghezza **prima** del bind, e i test che legano un
socket usano una fixture con radice corta: `tmp_path` di pytest include il nome
del test, e un test dal nome lungo avrebbe fallito per quello.

**Un test misurava la cosa sbagliata.** Verificavo l'isolamento di rete con
`ls /sys/class/net`, che legge il sysfs dell'host e vede le interfacce vere.
La rete *era* isolata; il test non lo stava provando. Sostituito con una
connessione TCP reale e con `ip` via netlink, che è consapevole dei namespace.

**Il criterio di Fase 0 ha trovato una violazione vera.** Il grep «nessuna
chiamata OS fuori da `platform/`» è passato da verde a rosso appena la sandbox
è esistita: `core/sandbox/policy.py` nominava `bwrap`, che l'invariante 29
vieta esplicitamente. Non era un falso positivo del controllo — era il
controllo che faceva il proprio lavoro (→ R11).

**Una corsa nel test di hot reload.** `Observer.start()` di watchdog ritorna
prima che il watch inotify sia attivo: sotto il carico della suite completa la
scrittura cadeva in quella finestra e l'evento non arrivava. In esercizio è
benigna — il file è appena stato letto dal costruttore — ed è ora documentata
in `SettingsStore.start()`. Il test non dipende più dal tempismo.

---

## Consegne

| Consegna §22 | Esito |
|---|---|
| `engine.py` | ✅ radice di composizione, chiusura ordinata su SIGINT/SIGTERM |
| `tools/registry.py` (§21.2) | ✅ + `invoke()`, nomi duplicati, invariante 27 imposto |
| `sandbox/runner.py` (bwrap dietro `platform/`) | ✅ in `platform/linux_sandbox.py` (R11) |
| `ws_server.py` (§21.4) | ✅ socket UNIX, directory 0700, socket orfano rimosso |
| `gpu_scheduler.py` (§9) | ✅ con la regola su memoria unificata |
| `jarvis doctor` (§16.1b) | ✅ cinque controlli misurati, sei `n/d` con la fase |

**Tre invarianti restano imposti dalla macchina** e non dalla disciplina:
`side_effect` ⇒ non `gesture_allowed` (27, nel registry), nessun `bwrap` fuori
da `platform/` (29, con un test che fa il grep), nessun segreto sul socket
(`_encode()` passa ogni messaggio da `SECRETS.scrub()`, e un test mette
deliberatamente una chiave nello snapshot per verificare che non esca).

## Riepilogo

| | |
|---|---|
| Test | **124 verdi** (erano 49) |
| Criteri §22 Fase 1 | **3 su 3 verificati** |
| Non verificato | **1** — seccomp, con la ragione e le alternative scartate |
| Punti aperti per la Fase 2 | il ciclo `fs.confirm_request`/`fs.confirm_response` con `request_id` e scadenza: il socket dice *chi* può parlare, non che quella risposta corrisponda a quella richiesta |
