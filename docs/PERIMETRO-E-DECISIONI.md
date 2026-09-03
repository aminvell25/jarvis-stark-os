> ## 🟡 CORRENTE per gli ADR, SUPERATA la roadmap — 30 agosto 2026
>
> **ADR-005** (schermo intero) e **ADR-006** (sandbox per il codice generato)
> sono correnti e autoritativi.
> **ADR-007 (MCP) è CHIUSO dal 25 agosto 2026** — `core/mcp/`,
> `docs/acceptance/ADR-007-MCP.md`.
>
> ⚠️ **La sezione «Roadmap che ne esce» è SUPERATA.** La riga 9 dice ancora
> «MCP — zero righe», e non è più vero da cinque giorni. Non pianificare da
> quella tabella.
>
> Stato corrente del progetto: **`docs/STATO-DEI-PIANI.md`**.
> Piano corrente: **`docs/PIANO-JARVIS-COGNITIVO.md`** (rev 2).
>
> **ADR-014 (il pilastro 3D) è APPROVATO il 3 settembre 2026** — tutte e tre
> le scelte — e la prima fetta è chiusa:
> `docs/acceptance/MODELLO-3D-ESTRUSIONE.md`. SPEC §17.1-17.3 sono correnti.
>
> **ADR-015 (il laboratorio) è PROPOSTO il 3 settembre 2026** e aspetta
> quattro decisioni del proprietario, elencate in fondo all'ADR. Cambia il
> confine di sicurezza — un terzo profilo di sandbox — e per questo si ferma
> prima del codice, come `PROTOCOLLO-DI-LAVORO` §11 chiede.

# Perimetro e decisioni — ADR-005, 006, 007, 014, 015

**Data**: 19 agosto 2026 · **Stato**: decise · **Rev SPEC di riferimento**: 5.2

Tre decisioni prese il 19 agosto in risposta a una proposta di ampliamento del
progetto verso un ambiente desktop completo. Sono registrate qui perché
**nessuna delle tre era scritta da nessuna parte**, ed erano rimaste in una
conversazione. Il progetto ha una regola contro il silenzio — `FASE-01.md`,
«dichiarato nel codice, non lasciato al silenzio» — e vale anche per le
decisioni che *non* si prendono.

La proposta chiedeva: gestione delle finestre altrui, apertura di programmi,
lettura dell'intero schermo, esecuzione di comandi di sistema generati
dall'LLM, orchestrazione MCP, widget Plasma con tema blur.

---

## ADR-005 — JARVIS resta un'applicazione a schermo intero

### Contesto

`CLAUDE.md`, seconda riga: «Un'applicazione desktop a schermo intero… **Fuori
dalla sua finestra non tocca nulla.**» La proposta la contraddice frontalmente.

Tecnicamente la strada esisteva ed era praticabile. Per memoria, e perché non
torni fra tre mesi come idea nuova:

| Capacità richiesta | Come si sarebbe fatta |
|---|---|
| Spostare, ridimensionare, chiudere finestre altrui | **KWin scripting su D-Bus** — il metodo di `kdotool`, che genera uno script KWin al volo, lo carica via D-Bus, lo esegue, lo cancella. Plasma 6, Wayland e X11 |
| Aprire programmi | D-Bus activation `org.freedesktop.Application`, o allowlist di voci `.desktop` |
| Vedere l'intero schermo | `xdg-desktop-portal` ScreenCast + PipeWire, con consenso utente per sessione |
| Notifiche di sistema | `org.freedesktop.Notifications` |
| Controllo media | MPRIS2 |
| Volume, luminosità | PipeWire / D-Bus |
| JARVIS come livello di fondo | Electron **non** supporta `wlr-layer-shell`. Si sarebbe fatto con una regola finestra di KWin: *Keep Below*, *No Border*, *All Desktops*, *Skip Taskbar/Pager* |

### Opzioni

**A. Restare applicazione a schermo intero.** Nessun accesso fuori dalla
finestra. Ogni invariante resta intatta, zero lavoro architetturale nuovo.

**B. Strato desktop su KDE.** JARVIS resta Electron ma diventa il livello di
fondo della sessione Plasma e controlla finestre e schermo via D-Bus e portal.
~6–8 settimane. Richiede di riscrivere la seconda riga di `CLAUDE.md` e §12.

**C. Desktop environment completo.** Compositor proprio, wlroots o Smithay.
Electron non può fare il compositor: un secondo processo in C o Rust. Mesi, e
manutenzione permanente.

### Analisi del compromesso

L'attrattiva di B era reale, e conteneva un regalo tecnico: con JARVIS come
livello di fondo e l'effetto blur di KWin sulle altre finestre, si vedrebbe
JARVIS sfocato *attraverso* Konsole, Firefox, l'IDE — l'effetto vetro di §25
prodotto dal compositor, **a costo zero per il renderer**, che chiuderebbe il
rischio di budget di §25.8.

Contro: B introduce una superficie verso l'intero sistema in un processo che
già ospita `<webview>` con contenuto non fidato. E KWin e D-Bus sono Linux:
l'invariante 29 prevede Windows, quindi tutto quello strato avrebbe una
controparte Windows che è un progetto a sé — o una dichiarazione che non
esisterà.

### Decisione

**Opzione A.** JARVIS resta un'applicazione a schermo intero.

### Conseguenze

- `CLAUDE.md` **non va toccato**. La seconda riga resta vera.
- §12 ARGUS resta `scope="app"`. Continua a leggere la finestra di JARVIS —
  **inclusa la `<webview>`**, quindi «estrarre dati da una schermata aperta»
  funziona per qualunque pagina si apra dentro JARVIS.
- Restano fuori: controllo di finestre altrui, apertura di programmi esterni,
  cattura dell'intero schermo, widget Plasma.
- L'effetto vetro si ottiene comunque, dentro casa, con §25.
- Il regalo del blur di KWin è perso. È il prezzo della decisione.

### Azioni

- [ ] Aggiungere a `ANALISI-REPO-E-TECNOLOGIE.md` la sezione «Valutate e
      scartate»: KWin scripting, `xdg-desktop-portal` ScreenCast, MPRIS2,
      `wlr-layer-shell`, widget Plasma. Con il **perché**, non solo il nome.

---

## ADR-006 — Il codice generato dall'LLM gira solo in sandbox

### Contesto

La proposta: «L'LLM integrato ha un accesso profondo all'OS… l'AI genera ed
esegue comandi di sistema reali».

`CLAUDE.md`, *Non fare senza chiedere*: **«Eseguire stringhe generate
dall'LLM»**. È il divieto più netto del documento. Cancellarlo cancella anche
l'invariante 2 (allowlist), la 3 (conferma umana col path risolto) e la 4 (solo
cestino), e rende inutile la sandbox costruita e verificata in Fase 1.

**L'aggravante è concreta, non teorica.** Nel sistema entrano già `<webview>`,
feed RSS, e — con ADR-007 — descrizioni di tool MCP. Sono tutti dato non fidato,
ed è il motivo per cui `llm/untrusted.py` esiste. Un sistema che esegue comandi
generati, con quel materiale in ingresso, è a una stringa iniettata da un
comando distruttivo.

### Opzioni

**A. Solo tool tipati.** L'LLM sceglie un tool registrato e riempie argomenti
tipati. Il codice che costruisce il comando lo scrive un umano, una volta.

**B. Comandi generati, solo in sandbox.** L'LLM genera codice, ma gira dentro
bubblewrap: niente rete, niente scrittura fuori radice, timeout.

**C. Comandi generati sul sistema vero, con conferma.**

### Analisi del compromesso

Il modello di A ha un nome e un esempio: **`kdotool` genera uno script KWin da
argomenti tipati.** Lo genera il programma, non un LLM da testo libero. È
esattamente ciò che `tools/registry.py` fa già.

C è stata scartata: con quattro sorgenti di dato non fidato in ingresso, la
conferma umana resta l'unica difesa, e una conferma che compare venti volte al
giorno si preme per abitudine.

B è A **più** una valvola per il calcolo genuino — trasformare dati, verificare
un'ipotesi — che non ha senso trasformare in venti tool separati.

### Decisione

**Opzione B**, letta rigorosamente:

1. Ogni azione con effetto sul mondo passa da un **tool registrato** con schema
   pydantic e flag `side_effect`. Nessuna eccezione.
2. Il codice generato gira **solo** in sandbox, e in sandbox **non può toccare
   nulla**: né disco fuori dalla sua tmpfs, né rete, né il desktop.
3. Manca una capacità? **Si scrive un tool.** Non si chiede all'LLM di
   improvvisare.

### Conseguenze

- Estendere il sistema è più lento, e questo è il costo accettato.
- La sandbox passa da infrastruttura senza consumatori a superficie attiva —
  vedi il rilievo qui sotto, che è la conseguenza più urgente di questo ADR.
- `tools/files.py` resta l'unica via verso il disco reale, con cestino e
  conferma, dentro `allowed_roots`.

### ⚠️ Rilievo aperto — la sandbox non blocca la lettura

`FASE-01.md` verifica che la sandbox blocchi **scrittura fuori radice** e
**rete**. Non blocca la **lettura**: §3.4 prescrive `--ro-bind / /`, quindi il
codice isolato vede l'intero filesystem in sola lettura.

Finché `run_sandboxed()` aveva **un solo chiamante** — `core/doctor.py:76`, un
health check — era irrilevante. Con un tool che esegue codice generato diventa
questo:

```python
print(open('~/.config/jarvis-os/secrets.toml').read())
```

Il `chmod 0600` non protegge: la sandbox gira **come lo stesso utente**. Il
`deny` in `.claude/settings.json` protegge Claude Code, non il runtime. E lo
stdout del processo isolato torna dritto nel contesto dell'LLM.

**Servono due profili di sandbox, non uno.** Il profilo «strumento» resta come
oggi. Il profilo «codice generato» monta solo l'interprete, la stdlib e una
tmpfs di lavoro: nessun pezzo di `$HOME`. È uno scostamento da §3.4 e va
motivato in un ADR proprio.

### Azioni

- [x] **ADR-008 — due profili di sandbox.** ✅ Fatto il 19 agosto 2026, prima
      che esistesse un chiamante. Cinque criteri verificati eseguendo, e il
      controllo: col profilo vecchio rimesso al suo posto **12 test su 23
      cadono**. Esito in `docs/acceptance/ADR-008.md`.
- [x] `core/tools/code.py` — ✅ fatto il 19 agosto 2026, **dopo** ADR-008.
      `esegui_codice(sorgente, timeout_s)`, `side_effect=False`, solo Python
      — ADR-008 non ha provato `albero_interprete()` su altri interpreti, e un
      tool non si appoggia a una cosa non provata. Esito in
      `docs/acceptance/TOOLS-CODE.md`.
- [x] Lo stdout del codice generato passa da `llm/untrusted.py`: ✅ stdout e
      stderr tornano avvolti in `<untrusted_source origin="codice generato">`,
      con la busta che non si può chiudere da dentro.
- [x] **ADR-009 — tetto di RAM e di CPU.** ✅ Fatto il 19 agosto 2026. Il
      timeout limitava il tempo e non la memoria: misurato, 2 GiB si allocano
      in 0,49 s. Un cgroup via `systemd-run`, scelto misurando anche
      `resource.setrlimit()`, che otto `os.fork()` scavalcano. Esito in
      `docs/acceptance/TOOLS-CODE.md`.
- [x] **`code.enabled = false` di serie.** ✅ Come voce e vision: spento, il
      tool non è nell'allowlist e non compare nell'elenco che l'LLM riceve.

---

## ADR-007 — MCP: i server propongono, il registry dispone

> ### ✅ **FATTO** — 25 agosto 2026
>
> `core/mcp/` esiste: `client.py` (JSON-RPC 2.0 su stdio, **senza dipendenze
> nuove**), `promozione.py` (il cancello), `montaggio.py` (l'ultimo miglio).
> Le quattro azioni sono chiuse, e i due eval girano contro un **server vero**
> — `tests/mcp_finto.py` è un processo separato, non un mock.
>
> Parte **spento**: `mcp.enabled` è predefinito `false` ed è la sesta chiave
> bloccata di §26.7 — accenderla avvia programmi di terzi, e si fa scrivendo
> nel file.
>
> Esito misurato in `docs/acceptance/ADR-007-MCP.md`.
>
> ⚠️ La condizione era «dopo ADR-003», ed è rispettata: ADR-003 è chiuso dal
> 25 agosto.

### Contesto

La proposta chiede orchestrazione MCP per far dialogare JARVIS con strumenti di
programmazione, domotica e browser.

MCP è **ortogonale ad ADR-005**: un server MCP non ha bisogno che JARVIS
controlli il desktop. È il singolo moltiplicatore di capacità più grande
disponibile dentro il perimetro scelto.

E la corrispondenza è quasi 1:1: `tools/registry.py` è un'allowlist con schemi
tipati; MCP è un'allowlist con schemi tipati su un trasporto.

### Il rischio

Montando un server MCP, i suoi tool entrerebbero nel sistema **senza passare
dalla revisione**. L'invariante 2 dice «solo i tool registrati esistono», e un
server che ne annuncia quaranta la aggirerebbe in un colpo.

Secondo rischio, distinto: le **descrizioni** dei tool MCP sono testo di terzi
che finisce nel contesto dell'LLM. È una classe di attacco documentata.

### Decisione

1. **I server MCP propongono, il registry dispone.** Un tool MCP non è
   invocabile finché non è stato **nominato** nell'allowlist locale, col suo
   `side_effect` e la sua conferma. L'invariante 2 regge.
2. Le descrizioni dei tool MCP passano da `llm/untrusted.py`, come le news.
3. Un server MCP che cambia il proprio elenco di tool non ne guadagna: i nuovi
   restano non invocabili finché un umano non li nomina.

### Azioni

- [x] Client MCP nel core — `core/mcp/client.py`. Non dietro `platform/`: il
      trasporto è uno stdio JSON-RPC, e `create_subprocess_exec` non è una
      chiamata specifica di piattaforma (il controllo dell'invariante 29
      guarda `bwrap`, `psutil`, `st_mode`, `/proc/` — nulla di questo).
- [x] `promuovi_mcp(server, nome_tool, side_effect)` — in `core/mcp/promozione.py`
      e non nel registry: il registry non deve sapere che cosa sia un server.
- [x] Eval: un tool annunciato e non nominato **non è invocabile**.
- [x] Eval: una descrizione con istruzioni iniettate **non produce nessuna azione**,
      e la busta non si chiude da dentro.

---
---

## ADR-014 — Il pilastro 3D: la geometria vive nel core, il renderer la mostra

> ### ✅ **APPROVATO E FATTO** — proposto il 2, approvato e chiuso il 3 settembre 2026
>
> La decisione «dentro, adesso» l'ha presa il proprietario il 2 settembre
> (`STATO-DEI-PIANI.md` §4⑦); le tre scelte di «Decisione» — le dipendenze,
> «solo GLB con i metri nel file», il perimetro — le ha approvate il 3.
> `trimesh 5.1.0` e `numpy` sono in `pyproject.toml`, SPEC §17.1-17.3 sono
> correnti, l'invariante 22 è emendato e il **34** è scritto.
>
> Esito misurato in `docs/acceptance/MODELLO-3D-ESTRUSIONE.md` e
> `docs/acceptance/MODELLO-3D-TUBO.md`: dalla frase al file, con la conferma
> vera sul socket, il verdetto `RIUSCITO` nel diario e il pezzo a schermo.
> Quattro difetti trovati **guardando lo scatto**, due dai presìdi che
> c'erano già, e — nella fetta 2 — un commento **falso** trovato misurando
> ciò che affermava.
>
> ⚠️ Restano fuori, come dichiarato: SketchUp via MCP, `bpy`, i generativi, i
> kernel CAD, e ogni formato oltre il GLB finché non c'è un consumatore.

### Contesto

`CLAUDE.md` promette in prima pagina «genera modelli 3D». Misurato il 2
settembre 2026: `core/tools/model3d.py` è **0 byte** dal 18 agosto;
`ui/src/three/math/extrude.js`, `math/spline.js` e
`components/node-graph.js` sono 0 byte; nessun `.py` nomina `model3d`;
`docs/SPEC.md` §17 sono **65 righe**, non «trenta pagine», e passano dal
titolo a §17.4 — **§17.1, 17.2 e 17.3 non esistono**. `trimesh` e `pygltflib`
non sono installati; `numpy` c'è solo come dipendenza transitiva di
mediapipe, non dichiarata in `pyproject.toml`.

Ciò che invece esiste, ed è reale: la pipeline §11.10 nel renderer —
`ParametricComponent` con `segmentsFor()` dalla curvatura, `qualityGate()` a
dodici controlli (`LIMITS.maxVertices = 20000`), `Line2` per le linee,
`Geometria` con `Float32Array` e `Uint32Array` per gli indici — e il
generatore ① di §17.4, `math/pointcloud.js`. E nel core il pattern dei tool
distruttivi: `Tool` con `planner`, `Piano` congelato col percorso risolto, la
conferma di §6.2, il verificatore di ADR-012 con `fonte` indipendente
(`core/tools/files.py::_verifica_create_file` è il modello).

Due fatti che cambiano il disegno rispetto a §17.4:

- **T2 non attraversa il registro dei tool** (`core/llm/claude_t2.py`), e T1
  ha zero tool per invariante 15. L'unica strada da una frase a un tool è T0
  → `registry.invoke`. «Solo via T2» non esiste.
- **Il ponte in salita ha sette verbi fissati** (`tests/test_ws_contract.py`)
  e `app/preload.js` vieta per iscritto un `manda(topic, oggetto)` generico.
  Un mesh che sale dal renderer al core sarebbe il primo messaggio in
  ingresso a payload libero.

### Il rischio, dichiarato per primo

`ANALISI-SENIOR` §4.6①: il 3D è «il ciclo più gratificante» e per questo il
più pericoloso — sei mesi di componenti che non controllano nulla. La
contromisura è nel criterio: **un** giro §11.7 oltre il primo scatto, il file
su disco come verità, e un tetto di stima dichiarato (3,5 giornate; col
fattore 3-5× del progetto, **10-18**). Se sfora del doppio si aggiorna la
stima, non il ritmo.

E §17.4 contiene una contraddizione da sciogliere, non da ereditare: ② e ③
prescrivono `THREE.CatmullRomCurve3` ed `ExtrudeGeometry`, mentre §11.10
regola 5 dice «mai geometrie standard», ed è la regola che `eval_visual.py`
ha appena applicato al nucleo.

### Opzioni

**A — la geometria nasce nel renderer** (`ParametricComponent`), e per
scriverla su disco sale al core attraverso il ponte. Contro l'invariante 1
nello spirito (il renderer decide che cosa finisce sul disco), contro la
lettera di `preload.js`, e il verificatore di ADR-012 guarderebbe un
passthrough. **Scartata.**

**B — la geometria nasce nel core** (numpy), il core la scrive con `trimesh`
e la **pubblica** come `model3d.preview`; il renderer la incassa in un
`ParametricComponent` che non genera niente e passa il `qualityGate()`. Una
sola implementazione del generatore; zero modifiche al ponte in ingresso; il
file è la verità e la preview è una vista dello stesso buffer. È il pattern di
news, globo e meteo: il core possiede il dato, il pannello lo rende.
Costo dichiarato: `segmentsFor()` avrà un gemello Python quando arriverà il
tubo (fetta 2), una riga duplicata in due linguaggi e inchiodata da un test
che passa per `node`. **Scelta.**

**C — un kernel CAD nel renderer** (Replicad, Manifold, in WASM): geometria
corretta, B-Rep vero — e generata nel posto sbagliato per B, con un secondo
motore accanto a three.js dentro il renderer. **Rimandata** a un ADR quando
servirà STEP o una booleana.

### Decisione

**Tre scelte, e tutt'e tre chiedono un sì.**

1. **Dipendenze.** Entrano `trimesh` (MIT, puro Python: esporta GLB con la
   sola numpy, valida `is_watertight` ed `euler_number`) e `numpy`
   **dichiarata** — oggi c'è per caso. **Non** entra `pygltflib`: il
   verificatore legge il GLB con `struct` e `json` della libreria standard,
   ed è indipendente dallo scrittore proprio per questo. `trimesh` non è un
   secondo motore 3D (invariante 10): non apre un contesto GL, non ha una
   scena, non vive nel renderer — è I/O e validazione, come `send2trash` per
   i file.
2. **Il file, e le unità.** Solo **GLB** nella prima fetta, con `min`/`max`
   obbligatori sull'accessor `POSITION`: è ciò che rende forte il
   verificatore. Millimetri ovunque nel core e nel renderer; **metri nel
   file**, perché glTF lo prescrive e un visualizzatore esterno deve vedere
   il pezzo grande quanto è: la conversione ×0,001 sta **solo** all'export,
   e i parametri in mm restano in `asset.extras`. STL e OBJ quando esiste un
   consumatore (invariante 23 vale anche per i formati).
3. **Il perimetro.** Fuori, con la ragione: **SketchUp via MCP** (pollici,
   sandbox AST, `build_model` non transazionale — è la fase successiva, non
   questa); **`bpy`** (GPL, ~300 MB, e il rendering headless non serve: la
   preview è three.js); **TRELLIS** e i generativi (vertici che nessun
   parametro spiega: contro l'invariante 22 nello spirito e il 23 nella
   lettera); **Replicad / Manifold / build123d** (opzione C).
   `math/extrude.js` e `math/spline.js` si **cancellano**: erano il piano di
   generare nel renderer. `node-graph.js` si cancella con loro, salvo
   obiezione: nessun generatore di §17.4 lo nomina.

**Una regola nuova, proposta come invariante 34** — speculare al 33:
**l'LLM propone i parametri di un generatore dell'allowlist, mai una
geometria.** `genera_modello` ha `forma` da un catalogo chiuso e parametri in
mm con un tetto di **20.000 vertici** — `LIMITS.maxVertices` del gate, §11.11
— oltre il quale è `ok=False` con la ragione, mai una decimazione silenziosa.

**E un emendamento all'invariante 22**, da scrivere in `CLAUDE.md` e nella
copia di SPEC §20 all'approvazione: «il generatore vive nel core; il
componente ricevuto estende `ParametricComponent` e passa `qualityGate()`
prima del render». Il gate resta obbligatorio e giudica per *duck typing* ciò
che il core **dichiara** (`bbox`, `params`) contro ciò che **manda**; che i
vertici siano *giusti* lo dicono il verificatore Python (accessor contro
parametri) e `trimesh` (`is_watertight`). Due controlli, due fonti.

### Prima fetta: `estrusione_45`, non il tubo

Il generatore ③ di §17.4 per tre ragioni misurabili: il bbox è **analitico**
dai parametri (regola 7 senza tolleranza, cioè senza verificare il codice con
sé stesso, che è il problema che `pointcloud.js` racconta); la topologia è
verificabile (un solido con foro passante ha `euler_number == 0` ed è
`is_watertight`); 32 vertici e 64 triangoli che il verificatore ricava
**dagli argomenti**. Sagoma: rettangolo `larghezza × altezza`, quattro
smussi a 45° di misura **diversa** (§11.10 regola 4), foro rettangolare
centrale anch'esso smussato, estruso per `profondita`. Anelli a otto vertici,
cappe come strisce di quadrilateri, niente triangolazione generica.

La catena, tutta con pezzi che esistono: frase T0 (`genera(mi)? un'estrusione
[di N mm]`, regola ancorata prima di `search_files`; `genera` **non** entra in
`VERBI_DI_COMANDO`) → `registry.invoke("genera_modello")` → planner → `Piano`
con `Operazione(tipo="create", destinazione=<risolto>)` sotto
`fs.workspace/modelli/<forma>-<AAAAMMGG-HHMMSS>.glb` — **nessun argomento
`path`**, come `timezones` — → `fs.confirm_request` → sì → `trimesh.Trimesh(v,
f, process=False).export(file_type="glb")` sul percorso **del piano** →
verificatore → `fs.result` e la riga di diario col verdetto (già automatiche)
→ `pubblica({"topic": "model3d.preview", …})` → il pannello `modello` si apre
al primo messaggio, come `gesture`.

Il verificatore, `fonte` = «intestazione GLB letta con `struct` e accessor
`POSITION` del chunk JSON, sul percorso risolto del piano»: `os.stat` → magic
`glTF`, versione 2, `length == st_size`; `accessors[POSITION].count == 32`;
`min`/`max` = bbox analitico ×0,001 a ±0,01 mm. Atteso dagli **argomenti**,
osservato dal **disco**, percorso dal **piano** — le tre regole di ADR-012.

File: `core/model3d/{parametrico,estrusione,glb_lettore}.py` (un test impone
che `glb_lettore` **non importi** `trimesh`), `core/tools/model3d.py`, una
riga in `core/engine.py` ~370; `ui/src/three/components/modello-ricevuto.js`,
`ui/src/panels/modello.js` sul modello di `globe.js` (stato vuoto esplicito),
voce 20 in `ui/src/desk/moduli.js` (`categoria: 4`, `suRichiesta`,
`fuoriPiastrellatura`: la categoria 4 è già piastrellata per intero),
`scripts/fixture_modello.py` → fixture di galleria dall'uscita **vera**;
`tests/test_model3d.py`, i casi invalidi in `tests/eval_tools.py`,
`tests/test_intenti_hanno_una_strada.py`, `tests/t0_corpus.py`,
`tests/eval_visual.py`; `docs/acceptance/MODELLO-3D-ESTRUSIONE.md`;
`pyproject.toml`; SPEC §17.1-17.3 da PROPOSTE a correnti;
`STATO-DEI-PIANI.md` nello stesso commit.

### Criterio di accettazione

1. «genera un'estrusione» → `fs.confirm_request` con un percorso assoluto
   sotto `fs.workspace/modelli/`; il rifiuto dà `BLOCCATO` e **nessun file**.
2. L'approvazione dà un file su disco e `RIUSCITO` nel diario, con la
   traccia del turno ereditata.
3. **Sabotaggio**: troncare il file dopo la scrittura → `FALLITO`. Un
   verificatore che non ha mai bocciato non è un verificatore.
4. La `fonte` non nomina il tool, e `registry._verifica` non lo declassa.
5. `glb_lettore` non importa `trimesh` (AST).
6. Il buffer ricevuto passa `qualityGate()` in Node, **e** il gate spara se
   si moltiplica `x` per 2.
7. Scatto di galleria con la checklist §11.8 punto per punto, e **un** solo
   giro oltre il primo.
8. `jarvis doctor`: verificatori da 3/25 a **4/26**.

**NON VERIFICATO in partenza, dichiarato**: il GLB aperto in un visualizzatore
esterno o in `gltf-validator` (non nel repo); la conformità glTF oltre
intestazione e accessor; il budget di frame sulla scrivania piena col nucleo
Aurora finché non gira `npm run scrivania` col pannello aperto.

### Rollback

Il commit precedente. Le due dipendenze escono da `pyproject.toml` e
`uv.lock`; i file `.glb` generati stanno sotto `fs.workspace/modelli/` e si
buttano col cestino (invariante 4). §17.1-17.3 tornano PROPOSTE.

### Azioni — nell'ordine, e la prima non è mia

1. ✅ **Il proprietario dice sì o no** alle tre scelte di «Decisione» — sì a
   tutte e tre, 3 settembre 2026.
2. ✅ `pyproject.toml`: `trimesh 5.1.0`, `numpy`; `uv lock`.
3. ✅ `core/model3d/` e il tool, con i test e i sabotaggi 3-5.
4. ✅ Il pannello, la fixture, lo scatto, il gate in Node (6-7).
5. ✅ La grammatica e il corpus.
6. ✅ Accettazione, SPEC §17 corrente, `CLAUDE.md` (invariante 22 emendato,
   invariante 34) con la copia in §20, `STATO-DEI-PIANI.md`, commit.

⚠️ **La fetta 2 — il tubo — è stata scritta due volte e poi TOLTA lo stesso
giorno.** Prima una spline chiusa che non era un pezzo, poi un tubo piegato
che lo era e restava senza un uso. Il caso d'uso del 3D, chiesto finalmente
al proprietario, è **prop e meccanica da stampare**: un elmo e le staffe che
ci vanno dentro. Restano la `tolleranza_mm` con la ragione obbligatoria e le
**quote scelte dal generatore**; se n'è andata la metà Python di
`segmentsFor()`, che senza un generatore curvo era «provata mai congiunta».

⚠️ **Questo ADR aveva scritto l'avvertimento e non l'ha seguito.** La sezione
«Il rischio, dichiarato per primo» dice che il 3D è «il ciclo più gratificante
e per questo il più pericoloso», e la contromisura era un tetto di giri §11.7 —
che è la cosa sbagliata da contare. La contromisura giusta era la domanda che
`PIANO-JARVIS-COGNITIVO` §4③ pone per il resoconto del mattino: **a che cosa
serve, quotidianamente**. Non è stata posta qui, e sono costate due fette.

---

## ADR-015 — Il laboratorio: JARVIS scrive codice che genera oggetti, e lo esegue dopo conferma, in una sandbox con un solo percorso scrivibile

> ### ✅ **APPROVATO E FATTO** — 3 settembre 2026
>
> Le quattro decisioni in fondo sono state prese dal proprietario lo stesso
> giorno — `~/JARVIS/laboratorio`, `opus` in un'impostazione separata, le due
> zone, `python` prima di FreeCAD e Blender — e la prima fetta è nel codice:
> `docs/acceptance/IL-LABORATORIO.md`, con le misure dal vivo. ⚠️ **Il primo
> criterio ha cambiato il disegno**: T2 non è «senza `Bash`», è sotto
> bubblewrap (`Profilo.AGENTE`) con la sola bozza scrivibile, perché
> `--allowedTools` non è un confine e `core/llm/claude_t2.py` l'aveva già
> misurato. E il manifesto della bozza è `bozza.json`, non `BOZZA.md`: un
> atteso si legge da uno schema, non da una prosa.
>
> Nasce da una correzione del proprietario. Avevo scritto che «eseguire
> codice generato dall'LLM è vietato»: **è falso**. `CLAUDE.md` riga 104 lo
> mette fra le cose da *non fare senza chiedere*, e ADR-006 dice che gira
> *solo in sandbox*. Chiedere e isolare non sono un divieto: sono le due
> condizioni. Il tool esiste già — `esegui_codice`, ADR-006 — ed è spento
> per configurazione, non per principio.
>
> Il proprietario vuole un **laboratorio**: una cartella in cui lui modifica
> e crea oggetti a mano, e in cui JARVIS fa lo stesso su richiesta —
> scrivendo il codice che li genera ed eseguendolo. Con una condizione sul
> modello: chi scrive quel codice **non è Haiku**. È un modello da lavoro,
> Sonnet o Opus.

### Contesto

Ciò che esiste già, e che questo ADR compone senza inventare:

| pezzo | dove | che cosa fa oggi |
|---|---|---|
| `esegui_codice` | `core/tools/code.py` | esegue Python generato in `Profilo.CODICE`: radice vuota, niente `$HOME`, niente rete, **nessun percorso scrivibile**. `side_effect=False` proprio perché non può toccare niente. Spento (`code.enabled=false`) |
| i due profili di sandbox | `core/sandbox/runner.py`, ADR-008 | `STRUMENTO` (host in sola lettura, rw sotto le radici consentite) e `CODICE` (tmpfs vuota). Nessun predefinito: chi chiama deve scegliere |
| T2 | `core/llm/claude_t2.py` | un processo Claude Code per compito, `t2_model = "sonnet"` in `settings.toml`, tool di Claude Code ristretti ma reali, **ogni spawn passa dal Governor** (invariante 16) |
| T1 | `core/llm/claude_t1.py` | Haiku, persistente, **zero tool** (invariante 15). È la voce, e non deve mai scrivere codice: già così |
| la conferma | `core/tools/confirm.py`, §6.2 | un `Piano` congelato col percorso risolto, una risposta sola, un umano che dice sì |
| il verificatore | ADR-012 | `atteso` dagli argomenti, `osservato` dal disco, `fonte` diversa dal tool |
| il pilastro 3D | ADR-014 | `genera_modello` con un catalogo chiuso di forme. **Resta**: è la strada rapida e sicura per un pezzo noto |

Due fatti che vincolano il disegno:

- **T2 non attraversa il registro dei tool di JARVIS.** Un file che T2 scrive
  col proprio `Write` non passa dalla conferma di §6.2 — lo dice
  l'intestazione di `claude_t2.py`. Se T2 scrive nella cartella in cui il
  proprietario lavora a mano, può sovrascrivere un file suo senza che nessuno
  l'abbia chiesto.
- **`Profilo.CODICE` non ha percorsi scrivibili per costruzione**, e
  `run_sandboxed` rifiuta di dargliene uno. Un laboratorio produce *file* —
  uno STL, uno script, un disegno — e con quel profilo non li può produrre.

### Il rischio, dichiarato per primo

Il rischio non è il codice che gira: ADR-006 e ADR-008 hanno già la sandbox,
ed è misurata. Il rischio è **la cartella condivisa**: due mani sugli stessi
file, una delle quali è un modello. Il giorno in cui JARVIS «sistema» un file
che il proprietario stava modellando a mano, il laboratorio ha perso il suo
senso. La difesa non può essere un prompt: dev'essere il filesystem.

### Opzioni

**A — T2 fa tutto.** Uno spawn Claude Code con `Bash`, nella cartella del
laboratorio: scrive lo script e lo esegue. Il codice generato girerebbe
**sull'host**, fuori da ogni profilo, contro ADR-006. E il `Write` di T2
toccherebbe i file del proprietario. **Scartata.**

**B — `esegui_codice` così com'è.** Lo script gira in `CODICE` e torna solo
stdout. Un pezzo da 100 KB di STL in base64 su stdout, riletto da `untrusted`,
è possibile e brutto — e il laboratorio non avrebbe file, cioè non sarebbe un
laboratorio. **Scartata.**

**C — tre pezzi, ognuno al suo posto.** T2 **scrive** (modello da lavoro,
cwd in una sottocartella di bozze, tool di Claude Code senza `Bash`); JARVIS
**propone** l'esecuzione con un tool `side_effect=True` e la conferma di
§6.2 mostra lo script e la cartella; un **terzo profilo** di sandbox esegue,
con un solo percorso scrivibile: la cartella di quella bozza. **Scelta.**

### Decisione

**① La cartella.** `~/JARVIS/laboratorio/`, visibile — un laboratorio in
cui si lavora a mano non può stare sotto `~/.local/share`. Entra in
`fs.allowed_roots`, quindi `list_dir`, `read_file` e `create_file` ci
lavorano già con le regole di sempre. Non contiene stato di JARVIS, che è la
condizione di `engine.py` per una radice.

Dentro, due zone con due regole:

```
~/JARVIS/laboratorio/            del proprietario: JARVIS legge, non scrive
~/JARVIS/laboratorio/bozze/      di JARVIS: una sottocartella per compito,
                                 <data>-<etichetta>/, ed è l'UNICO posto
                                 in cui T2 e la sandbox scrivono
```

Un oggetto che passa dalle bozze alla cartella del proprietario ci passa con
`move_path` — cioè con una conferma, come qualunque spostamento.

**② Il terzo profilo: `Profilo.LABORATORIO`.** È `CODICE` — radice vuota,
interprete e librerie di sistema, niente `$HOME`, niente `/etc`, **niente
rete** — più **una** sola cosa: la cartella della bozza montata in scrittura.
`run_sandboxed` la ammette come unico `rw_paths`, e rifiuta qualunque altro.
I tetti di ADR-009 — tempo, RAM, CPU, memoria di lavoro — valgono uguali.
Le librerie disponibili sono quelle dell'interprete di JARVIS: `numpy` e
`trimesh` ci sono già.

**③ Chi scrive: T2, con un modello da lavoro.** Un'impostazione nuova,
`llm.laboratorio_model`, predefinita `"opus"` — separata da `t2_model`
perché il consolidamento notturno può restare su Sonnet e il laboratorio no.
Lo spawn passa dal Governor come tutti; cwd = la sottocartella della bozza;
tool di Claude Code `Read`, `Write`, `Edit`, `Glob`, `Grep` — **non `Bash`**:
T2 può scrivere lo script, non eseguirlo. La cartella del proprietario è
leggibile (è nella radice) e la sua scrittura è impedita da ciò che T2 non
ha, non da un prompt. T1 resta com'è: Haiku, zero tool, voce.

> ⚠️ **Da provare, non da assumere**: T2 dentro `Profilo.STRUMENTO` con
> `rw_paths = [bozza, ~/.claude]` renderebbe l'impossibilità di scrivere
> altrove una proprietà del filesystem invece che dell'elenco dei tool.
> Claude Code sotto bubblewrap non è mai stato eseguito qui: è il primo
> criterio di accettazione, e se fallisce si dichiara e si resta all'elenco
> dei tool.

**④ Chi esegue: JARVIS, dopo il sì.** Un tool `esegui_bozza`,
`side_effect=True`, `gesture_allowed=False`. Il planner mostra nella
conferma **il percorso risolto dello script, l'interprete e la cartella in
cui può scrivere** — così «non fare senza chiedere» diventa una domanda con
il codice sotto gli occhi. Il verificatore (ADR-012): `atteso` = i file che
lo script dichiara di produrre, dagli argomenti; `osservato` = `os.stat` nella
cartella della bozza; per uno STL, l'intestazione binaria e il conteggio dei
triangoli letti con `struct` — ogni vertice, non un'intestazione dichiarata.
Ogni esecuzione è una riga di diario con traccia e verdetto.

**⑤ Gli interpreti, in ordine.** `python` per primo: è l'unico su cui
`albero_interprete()` è provata (ADR-008, punto 2 dei suoi non verificati).
`freecadcmd` e `blender -b -P` sono le due braccia che il proprietario ha
descritto, e **rientrano da questa porta** — come binari dentro il profilo,
non come `bpy` importato da Python, che è ciò che ADR-014 ha escluso e resta
escluso. Ciascuno entra solo dopo che il profilo è provato su di lui.

**⑥ Che cosa cambia nelle regole, e che cosa no.**
`CLAUDE.md` riga 104 non cambia: la conferma **è** il chiedere. ADR-006 non
cambia: `LABORATORIO` è una sandbox. L'invariante 34 si **delimita**: vale per
`genera_modello`, che resta la strada rapida per un pezzo del catalogo; il
laboratorio è l'altra strada, aperta, e la sua sicurezza sta nella conferma
col codice visibile e nel profilo, non nell'allowlist delle forme.
`esegui_codice` resta com'è, per il calcolo che non produce file.

### Prima fetta

Dalla voce alla bozza: «costruisci nel laboratorio una staffa per un servo
SG90» → T0 riconosce `laboratorio` con la coda libera → Governor → T2
(`laboratorio_model`) in `bozze/<data>-staffa-sg90/` scrive `genera.py` e un
`BOZZA.md` che dichiara i file che produrrà → JARVIS propone `esegui_bozza`
→ conferma con lo script → `Profilo.LABORATORIO` → `staffa-sg90.stl` nella
bozza → verificatore → diario → `model3d.preview` nel pannello, attraverso un
lettore STL nel core. Il proprietario apre la bozza con il suo CAD, o la
sposta nella propria cartella con `move_path`.

File: `core/sandbox/runner.py` (il profilo), `core/platform/linux_sandbox.py`
(il bind), `core/tools/laboratorio.py` (il tool e il verificatore),
`core/llm/claude_t2.py` (cwd e tool per lo spawn di laboratorio),
`core/settings.py` (`laboratorio_model`, la radice), `core/llm/grammar.py`
(la regola), `core/model3d/stl_lettore.py` (solo libreria standard),
`tests/test_laboratorio.py`, `docs/acceptance/IL-LABORATORIO.md`,
`STATO-DEI-PIANI.md` nello stesso commit.

### Criterio di accettazione

1. **Claude Code sotto bubblewrap**: T2 avviato in `STRUMENTO` con la sola
   bozza scrivibile completa un compito. Se non ci riesce, si dichiara e si
   resta all'elenco dei tool senza `Bash`.
2. Uno script nella bozza che tenta di scrivere **fuori** dalla bozza fallisce
   dentro `LABORATORIO`, e l'errore è nel diario.
3. Lo stesso script **senza rete**: una `urlopen` fallisce.
4. La conferma mostra il percorso risolto dello script e della cartella; il
   rifiuto non lascia nessun file nuovo.
5. **Sabotaggio**: uno script che dichiara `staffa.stl` e scrive
   `staffa.txt` → `FALLITO`.
6. Il file del proprietario in `laboratorio/` è **byte per byte identico**
   dopo un compito di T2 e un'esecuzione, misurato.
7. La riga di diario porta la traccia del turno vocale e il verdetto.
8. `jarvis doctor` conta il verificatore nuovo.

**NON VERIFICATO in partenza, dichiarato**: `freecadcmd` e `blender` nel
profilo (fetta successiva, ciascuno con la propria misura); il costo in
token di uno spawn Opus per bozza; il caso in cui T2 non scriva il
`BOZZA.md` (allora non c'è atteso, e il tool risponde `NON_VERIFICATO`).

### Rollback

Il commit precedente. Il profilo, il tool e l'impostazione escono;
`~/JARVIS/laboratorio/` resta al proprietario, che ci lavora a mano
comunque.

### Le quattro decisioni — prese dal proprietario il 3 settembre 2026

1. **La cartella**: `~/JARVIS/laboratorio/`, visibile. → `laboratorio.radice`,
   e deve stare fra `fs.allowed_roots`: il tool la chiede, non la prende.
2. **Il modello**: `llm.laboratorio_model = "opus"`, separato da `t2_model`
   (Sonnet, che resta al consolidamento). **Mai haiku**, e lo schema lo
   rifiuta.
3. **La regola delle due zone**: T2 e la sandbox scrivono **solo** in
   `bozze/`, mai sui file del proprietario; promuovere un oggetto è un
   `move_path` con conferma. → `Profilo.AGENTE` per chi scrive,
   `Profilo.LABORATORIO` per chi esegue, e la fotografia della radice prima e
   dopo, che finisce nel diario se cambiasse.
4. **L'ordine degli interpreti**: `python` subito; FreeCAD e Blender dopo,
   ciascuno quando il profilo è provato su di lui. → fatto `python`, col venv
   di JARVIS in sola lettura.

### Esito del criterio

Otto criteri: sette **PASS** misurati, l'ottavo (`jarvis doctor`) vale per
costruzione e non è stato eseguito dal vivo. La tabella, le bocciature e i
tre giri dal vivo — con il primo script caduto su `manifold3d` che il prompt
prometteva e il venv non aveva — sono in `docs/acceptance/IL-LABORATORIO.md`.
`manifold3d` e `shapely` sono state chieste come dipendenze nuove e
**approvate dal proprietario lo stesso giorno**: le booleane e i profili 2D
girano dentro `Profilo.LABORATORIO`, misurato.

---

## Cosa sopravvive della proposta, dentro il perimetro

| Indicazione | Esito |
|---|---|
| Controllo vocale | ✅ **fatto e spento.** Fase 9 ha unito le due radici di composizione: `VoicePipeline` è composta nell'engine, condizionata da `voice.enabled`, predefinito `false`. Resta da accendere e verificare col microfono vero |
| Screen-aware | ✅ parziale: ARGUS `scope="app"` legge la finestra di JARVIS, `<webview>` inclusa |
| MCP | ✅ ADR-007 |
| Manipolare file, creare cartelle | ✅ `tools/files.py`, con cestino e conferma |
| Dashboard HUD | ✅ 18 componenti, meglio di qualunque plasmoide |
| Metafora scrivania: finestre | ✅ `cornice.js` + `scrivania.js` |
| **Icone e cestino sul fondo** | ⚠️ **mancano.** `trash_only=true` è nel core, ma non esiste un pannello cestino né icone sullo strato di fondo. Sono compatibili col perimetro e assenti |
| Menu di avvio | ⚠️ manca. Il dock elenca gli otto moduli; non c'è un punto d'ingresso per il resto |
| Controllo finestre altrui, aprire programmi, screen-aware globale | ❌ ADR-005 |
| Comandi di sistema generati | ❌ ADR-006 |
| Widget Plasma, tema blur di KWin | ❌ ADR-005. Sarebbe stata una retrocessione: §10 e §11 producono già un risultato migliore |

---

## Roadmap che ne esce

| # | Cosa | Costo | Perché in questa posizione |
|---|---|---|---|
| 1 | Risoluzioni non verificate (`SEZIONE-13.md` §4) · etichetta budget news | 30 min | rischio aperto, costo nullo |
| 2 | ~~**ADR-008 — profilo sandbox per codice generato**~~ | ✅ fatto | il rischio nuovo e' chiuso: `docs/acceptance/ADR-008.md` |
| 3 | ~~`tools/code.py` sopra il profilo nuovo~~ | ✅ fatto | dopo il 2, come doveva essere: `docs/acceptance/TOOLS-CODE.md` |
| 3b | ~~**ADR-009 — tetto di RAM e CPU, e `code.enabled`**~~ | ✅ fatto | il timeout non limitava la memoria: 2 GiB in 0,49 s |
| 4 | Token di riempimento — `DIVARIO-PREMIUM.md` §1 | 1 g | prerequisito di 5, 6 e 7 |
| 5 | Regole di riempimento su 18 componenti + ciclo §11.7 | 4–5 g | **l'80 % del divario visivo** |
| 6 | §25 strato di presenza | 4,5 g | dipende da 4 |
| 7 | Pannelli vuoti, `--manila`, barra e dock come bande | 2,5 g | dipende da 4 |
| 8 | ⏳ Accendere la voce: `enabled = true`, verifica col microfono | 0,5 g | **mai fatto**: il codice c'è dalla Fase 9, `voice.enabled = false`. È l'unica voce che non dipende da nient'altro |
| 9 | ❌ MCP — ADR-007 | 3 g | **zero righe** |
| 10 | ⚠️ Pannello cestino, icone e menu d'avvio | 1,5 g | icone libere e cartelle ✅ (`3f86f25`, §26.5); **il pannello cestino non esiste** |

~~**~19 giorni.**~~

> ### Esito verificato il 24 agosto 2026
>
> 1 ✅ · 2 ✅ · 3 ✅ · 3b ✅ · 4 ✅ · 5 ⚠️ *(«18 componenti» sono **sei**, `d3d8978`)*
> · 6 ✅ · 7 ✅ · 8 ⏳ · 9 ❌ · 10 ⚠️
>
> Restano tre voci aperte, e la 8 costa mezza giornata.
> Quadro completo: `docs/STATO-DEI-PIANI.md`.

I punti 2 e 3 vanno per primi non perché siano i più importanti, ma perché sono
gli unici che aprono una superficie nuova. Il 5 è quello che si vede.

---

## Nota su una correzione

La prima stesura di questa roadmap contava **2 giorni** per «comporre
`VoicePipeline` nell'engine», sulla fede di `SEZIONE-13.md`, che la dichiara
non composta. Leggendo `core/engine.py` risulta che **Fase 9 l'ha già fatto** —
l'intestazione del file lo dichiara per esteso — e che l'ostacolo residuo è
solo l'interruttore `voice.enabled`, predefinito `false` per fail-closed.

Mezza giornata, non due. Registrato perché un documento di accettazione può
invecchiare in poche ore quando il progetto si muove a questa velocità, e il
codice resta l'unica fonte che non mente.
