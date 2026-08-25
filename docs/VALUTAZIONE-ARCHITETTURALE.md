# Valutazione architetturale — pre-Fase 0

**Data**: 18 agosto 2026 · **Oggetto**: `docs/SPEC.md` rev 5.0 · **Stato del codice**: zero

> ### Esito verificato il 24 agosto 2026
>
> **ADR-001 ✅** (`.python-version` 3.12, `requires-python = ">=3.12,<3.13"`) ·
> **ADR-002 ✅** (socket UNIX, `request_id`) · **ADR-008 ✅** · **ADR-009 ✅**
> · **ADR-003 ❌ a metà** · **ADR-004 ❌ non fatto**.
>
> Le correzioni minori 1, 2, 3 e 6 sono chiuse. La **4** no: `config/settings.toml`
> ha ancora lo stesso nome del file operativo di `~/.config/` — le due copie
> divergeranno, ed era proprio questo il rilievo.
>
> Quadro completo: `docs/STATO-DEI-PIANI.md`.

Documento di lavoro. Non sostituisce la SPEC: la sottopone a verifica prima che
esista codice, che è l'unico momento in cui le correzioni costano poco.

---

# PARTE 0 — Diagnosi dell'ambiente

Anticipazione manuale di `jarvis doctor` (§16.1b), che nascerà in Fase 1.

## Prerequisiti (INSTALLA.md §4)

| Voce | Stato | Rilevato |
|---|---|---|
| `claude` | ok | 2.1.234 (richiesto ≥ 2.1.205) |
| `node` | ok | v24.14.1 (richiesto ≥ 20) |
| `uv` | ok | 0.12.5 |
| `npm` | ok | 11.18.0 |
| `git` | ok | 2.51.0 |
| `bubblewrap` | ok | 0.11.0 — sandbox `exec` di Fase 1 praticabile |
| **`python3`** | **ROSSO** | **3.13.7 — la SPEC richiede 3.12, MediaPipe non va oltre 3.12** |
| **Barlow Semi Condensed** | **ROSSO** | assente |
| **IBM Plex Mono** | **ROSSO** | assente |
| `tesseract` | assente | serve solo in Fase 6 (ARGUS) |

## Stato del repository

| Voce | Stato | Nota |
|---|---|---|
| **repo git** | **ROSSO** | **non inizializzato.** Il punto 4 della "definizione di fatto" è irraggiungibile |
| `CLAUDE.md`, `docs/SPEC.md`, `ANALISI` | ok | identici ai sorgenti in `workshop/files/` |
| `.claude/agents/` | ok | forge, argus, edith, veronica |
| `docs/design-reference/famiglia-a/` | ok | 12/12 immagini attese dal README |
| `pyproject.toml`, `core/`, `tokens.css` | assenti | consegne Fase 0 — atteso |
| `ui/gallery.html` | assente | consegna Fase 0b — atteso |
| `docs/acceptance/` | assente | richiesta dalla definizione di fatto |
| nome cartella | WARN | `jarvis-stark-os`; SPEC §21.1 e INSTALLA dicono `jarvis-os` |

## Configurazione utente (INSTALLA.md §3 — non eseguita)

`~/.config/jarvis-os/{settings.toml, secrets.toml, voice-persona.md}`,
`~/.local/share/jarvis-os/voice-cwd/` e `~/JARVIS/` sono **tutti assenti**.

Conseguenza diretta: il criterio di accettazione della Fase 0 — *"caricamento,
validazione, hot reload di `settings.toml`"* — non è verificabile finché il
passo 3 di INSTALLA.md non viene eseguito.

---

# PARTE 1 — Valutazione del progetto

## 1.1 Requisiti, come li legge l'architettura

**Funzionali**: parlare e ascoltare in italiano; eseguire operazioni reali su
cartelle reali; incassare web e YouTube vivi; generare geometria 3D; osservare
il proprio schermo; riportare lo stato del sistema.

**Non funzionali** — sono questi a dettare la forma:

| Requisito | Valore | Da dove viene |
|---|---|---|
| Latenza frase-comando | ~30 ms, **offline** | §7.5 |
| Latenza primo suono in conversazione | 0,6–1,3 s | §7.5 |
| Frame budget | three.js ≤8ms · Pixi ≤3ms · anime.js ≤4ms a 60fps | §10.4 |
| Scala | **un utente, una macchina, zero rete** | §1 |
| Disponibilità | degradazione annunciata, mai silenziosa | §16 |
| Costo ricorrente | solo Deepgram; LLM già nell'abbonamento | §24.8 |

Il quarto rigo è quello che va tenuto in mente leggendo il resto: **non esiste
un problema di scala orizzontale.** Non ci sono repliche, code distribuite,
failover fra nodi. Ogni complessità che si giustificherebbe solo con "e se
avessimo diecimila utenti" qui è puro costo. La SPEC lo ha capito, e questa è
la sua qualità principale.

## 1.2 Le tre decisioni portanti — sono corrette

**① T1 come processo persistente.** Non è un'ottimizzazione, è un requisito.
La misura di §5.2 lo dimostra: 2,41 s mediani di costo fisso per `claude -p` a
freddo, di cui ~2,2 s sono spawn di Node, portachiavi OAuth e handshake. Un
processo per turno metterebbe 2,5–3 s prima del primo suono contro un budget di
1,3 s. **Approvato senza riserve** — con la conseguenza, non ancora affrontata,
della §2.3 qui sotto.

**② Il core Python possiede le operazioni reali.** Un renderer che ospita
`<webview>` con contenuto arbitrario e ha accesso al disco è indifendibile. La
separazione è la difesa vera, non la marcatura `<untrusted_source>` — che §18.1
qualifica correttamente come "il minimo, non sufficiente". **Approvato.**

**③ Allowlist tipizzata, non denylist.** Lo spazio dei comandi dannosi è
infinito e componibile; quello dei comandi utili è finito e si scrive.
Il controllo di `_safe()` **dopo** `resolve()` (§6.1) è il dettaglio che conta:
è `resolve()` a eliminare i `..`, e invertirlo è il modo classico di sbagliare.
**Approvato.**

## 1.3 Il modello a tre tier — dove sta il valore reale

| Tier | Latenza | Dipende da rete | Dipende da LLM |
|---|---|---|---|
| **T0** | <10 ms | ❌ | ❌ |
| T1 | 300–900 ms | ✅ | ✅ |
| T2 | 5 s – minuti | ✅ | ✅ |

La colonna che conta non è la prima: sono le ultime due. **T0 è l'unico tier che
sopravvive a tutto**, ed è ciò che rende `degraded_llm` e `offline` (§16) stati
utilizzabili invece che eufemismi per "rotto". Con la rete staccata e il token
scaduto, *"papà è a casa"* continua a funzionare. Questa è la proprietà più
preziosa dell'intero progetto e vale la disciplina che costa.

L'osservazione di §7.6 nota 2 — `parse()` ritorna `None`, non solleva — è la
scelta giusta. Il rischio da sorvegliare con `t0_corpus.py` non è che il parser
manchi un comando: è che **ne rubi uno a T1**, perché la regola `search_files`
è deliberatamente permissiva e sta in fondo alla lista. Il corpus con 20 frasi
conversazionali che devono dare `None` copre esattamente questo. Tenerlo.

## 1.4 I punti su cui la specifica non è ancora chiusa

Sono quattro. Nessuno invalida il progetto; tutti costano di più se affrontati
dopo. Ciascuno ha un ADR in Parte 2.

**A — Chi ha l'autorità di confermare un `side_effect=True`.**
L'invariante 3 dice *"richiede conferma umana"*. Il flusso di §6.2 la instrada
sul WebSocket. La §18.2 prescrive un *"token per-sessione"*. Ma
l'implementazione di riferimento di §21.4 (`ws_server.py`) apre
`websockets.serve(...)` su `127.0.0.1:8765` **senza alcuna verifica del token**.
Come scritta, l'autorità di confermare una cancellazione appartiene a *chiunque
riesca ad aprire una socket verso la porta 8765* — cioè a qualunque processo
dell'utente. L'invariante è dichiarato al posto giusto (il core) ma non è ancora
imposto lì. → **ADR-002**

**B — Cosa succede quando T1 muore per una causa diversa dalla scadenza OAuth.**
La §5.6 tratta magistralmente il caso auth: niente riavvio a ciclo, annuncio
vocale locale, `degraded_llm`. Ma quel percorso è specifico. Un OOM, uno stream
che si desincronizza, una `read` bloccata: `Restart=always` rilancia, la
sessione riparte **vuota**, e §5.5 dice che il `ContextPruner` esiste anche
"per reiniettare i fatti fissati quando la sessione viene ricreata" — senza dire
chi lo rileva, chi li reinietta e cosa sente l'utente. Il modo di fallire è il
peggiore possibile: JARVIS continua a parlare, con la stessa voce, avendo
dimenticato tutto, **senza dirlo**. Contraddice §16 ("nessuna soglia agisce
senza annunciarlo"). → **ADR-003**

**C — L'unico costo reale non è misurato.**
Il Governor accumula `total_cost_usd` in `conso/YYYY-MM-DD.jsonl` (§5.4). Ma
quel campo misura l'LLM, che è **già pagato dall'abbonamento**. La §24.8
riconosce che Deepgram è "la sola voce di costo ricorrente del progetto" e che
non è stata stimata. Il sistema quindi conta con precisione ciò che non gli
costa e non conta ciò che gli costa. → **ADR-004**

**D — Python 3.12 non è sulla macchina, e Fase 7 ci sbatte contro.**
Il sistema ha solo 3.13.7. La §4 registra che MediaPipe supporta Python ≤3.12.
Oggi è una riga in `pyproject.toml`; alla Fase 7, con dieci settimane di core
scritto su 3.13, è una migrazione. → **ADR-001**

## 1.5 Contesa di risorse — un rilievo minore ma reale

La §9 modella bene la GPU: quattro consumatori, la scena 3D è il principale,
regola dura di rifiutare il caricamento senza headroom invece di spillare in RAM.

C'è però un secondo tipo di contesa non modellato: **la quota dell'abbonamento**.
Il Governor la gestisce fra T1 e T2 (T1 riservato, max 2 T2 concorrenti, 15
spawn/ora). Ma il consolidamento notturno di §5.5 gira alle 04:00 come processo
T2 e attinge allo stesso pool. Se la finestra è esaurita o il token è scaduto
nella notte, il consolidamento **non gira e nessuno lo sa**: `mark_run(now())`
sta in fondo alla funzione, quindi lo stato resta coerente e riproverà, ma il
silenzio viola la regola di §16. Un `agent.advisory` di livello `warn` su
consolidamento saltato chiude il buco a costo nullo.

## 1.6 Il piano a fasi — giudizio

Il sequenziamento è corretto e in due punti è migliore della media:

- **La Fase 0b prima della Fase 5.** Due giorni di galleria e ciclo di verifica
  visiva spesi *prima* delle cinque settimane di componenti. Senza, ogni
  componente 3D costa tre o quattro giri di correzione. Si ripaga con margine.
- **Gli eval che girano all'inizio di ogni fase, non alla fine.** È l'unico
  modo per accorgersi che la sessione della Fase 5 ha rotto qualcosa della
  Fase 2. Con Claude Code che scrive il codice, questo smette di essere buona
  pratica e diventa l'unico strumento di controllo che Lei ha.

**Il rischio concentrato è la Fase 5**: cinque settimane su ventitré, cioè il
30% del piano, e l'unica fase il cui esito non è binario — un componente può
"funzionare" ed essere sbagliato. Le mitigazioni ci sono tutte (quality gate,
checklist §11.8, ciclo §11.7). Una sola osservazione sulla stima: il ciclo
§11.7 richiede di **guardare** lo screenshot a ogni iterazione, e quel costo per
componente non compare nelle stime. Non lo cambi: lo sappia.

---

# PARTE 2 — Decisioni

## ADR-001 — Python 3.12 gestito da uv, non dal sistema

**Stato**: Proposto · **Decide**: Lei · **Blocca**: Fase 0

### Contesto
La macchina ha solo `/usr/bin/python3.13`. SPEC §4 dichiara Python 3.12 e
registra che MediaPipe (§14, Fase 7) non ha wheel oltre 3.12. `uv` ha già
`cpython-3.12.14` nella sua cache locale.

### Opzioni

**A — Pin a 3.12 gestito da uv** *(raccomandata)*
`requires-python = ">=3.12,<3.13"` in `pyproject.toml` più `uv python pin 3.12`.
Complessità bassa, indipendente dal Python di sistema, riproducibile.
Contro: il venv non usa l'interprete di sistema (che è ciò che si vuole).

**B — Sviluppare su 3.13 e affrontare MediaPipe alla Fase 7**
Complessità nulla oggi, alta dopo. Costo: dieci settimane di core da rivalidare,
o rinuncia alle gesture.

**C — Rinunciare a MediaPipe, restare su 3.13**
Elimina il vincolo ma anche la Fase 7. Da considerare solo se le gesture
risultassero marginali all'uso — decisione da prendere con dati, non oggi.

### Decisione
**Opzione A.** Il vincolo è noto ora e costa una riga; scoperto alla Fase 7
costa una migrazione. Nessuna ragione per rinviare.

### Conseguenze
Ogni comando di sviluppo passa da `uv run`. Il `pyproject.toml` della Fase 0
diventa il punto in cui il vincolo è scritto una volta sola.

### Azioni
1. [ ] `uv python pin 3.12` nella root del repo
2. [ ] `requires-python = ">=3.12,<3.13"` in `pyproject.toml` (Fase 0)
3. [ ] Un test che fallisce se `sys.version_info[:2] != (3, 12)`

---

## ADR-002 — La conferma di `side_effect=True` è imposta nel core

**Stato**: **Accettato — opzione B** · **Deciso il** 18 ago 2026 ·
**Recepito in** SPEC rev 5.1 (§3.2, §16.1b, §18.2, §21.4) e invariante 7

### Contesto
Invariante 3: ogni tool `side_effect=True` richiede conferma umana col path
assoluto risolto. §6.2 instrada la conferma sul WebSocket. §18.2 prescrive un
token per-sessione. **L'implementazione di riferimento di §21.4 non lo verifica**:
`websockets.serve(handler, "127.0.0.1", 8765)` accetta qualunque client locale.

L'invariante è quindi dichiarato nel posto giusto ma imposto nel posto sbagliato
— di fatto nel renderer, che è l'unico componente che oggi mostra la finestra di
conferma. Un renderer è il posto sbagliato per un'autorità di sicurezza:
è il componente che ospita `<webview>` con contenuto non fidato.

### Opzioni

**A — Token per-sessione + correlazione della conferma nel core** *(raccomandata)*
Il core genera un token all'avvio, lo scrive in un file 0600 sotto
`$XDG_RUNTIME_DIR`, e lo rifiuta come primo messaggio se assente o errato. Ogni
`fs.confirm_request` porta un `request_id` con scadenza; il core esegue **solo**
se riceve una `fs.confirm_response` con `request_id` valido, non scaduto, dal
client autenticato che l'ha ricevuta. Complessità: bassa. Familiarità: alta.

**B — Socket unix con permessi di filesystem invece di TCP**
Più forte: l'autorizzazione la fa il kernel. Ma Electron parla WebSocket su TCP
senza attriti e su socket unix no, e §23 vuole portabilità Windows dove il
modello cambia. Complessità media, guadagno marginale sul caso d'uso reale.

**C — Lasciare com'è**
Complessità nulla. Su una macchina personale monoutente il rischio pratico è
basso. Ma l'invariante 3 diventa una convenzione, e le convenzioni si erodono
alla terza sessione di Claude Code che tocca `ws_server.py`.

### Analisi del compromesso
Il vero argomento non è "un attaccante locale". È che **un invariante non imposto
dalla macchina è un invariante che decadrà**. La §14 lo ha già capito per le
gesture — invariante 27: *"imposto nel registry, non lasciato alla disciplina"*.
Qui vale lo stesso principio, applicato al canale.

### Decisione

**Opzione B — socket UNIX.** Avevo raccomandato la A; il proprietario del
progetto ha scelto la B, e la scelta è migliore della mia raccomandazione su
ciò che conta di più.

Il mio argomento contro la B era il costo di integrazione con Electron. È
reale ma è **una tantum**, e paga una proprietà permanente: con la A
l'invariante 3 resta difeso da codice che deve ricordarsi di verificare un
token; con la B lo difende il kernel, prima che una riga di codice
applicativo giri. Avevo pesato il costo di scrittura più della garanzia
ottenuta — che è il compromesso sbagliato per un invariante di sicurezza in
un sistema pensato per durare anni.

### Conseguenze

Più facile: l'invariante 3 smette di dipendere dalla disciplina del codice.
Non esiste una porta da esporre per sbaglio.

Più difficile: **l'API `WebSocket` del browser non può aprire un socket UNIX.**
Il renderer non parlerà mai direttamente col core — la connessione la apre il
processo main di Electron e la ponta via `contextBridge`. §3.2 lo prevedeva
già, ma smette di essere una scelta e diventa un vincolo.

Da rivedere: su Windows l'equivalente è una named pipe con ACL. Sta dietro
`platform.Paths.socket_path()` (invariante 29), quindi è un file nuovo, non
una modifica sparsa.

### Azioni
1. [x] `Paths.runtime_dir()` e `Paths.socket_path()` — Fase 0
2. [x] `RUNTIME_DIR_MODE = 0o700` in `platform/base.py`, perché il valore stia
       nel codice e non nella memoria di chi scriverà il server — Fase 0
3. [x] SPEC §3.2, §16.1b, §18.2, §21.4 e invariante 7 aggiornati — rev 5.1
4. [x] `ws_server.py` su `websockets.unix_serve()`, directory a 0700 — ✅ verificato il 24 ago 2026
5. [x] `request_id` + scadenza sul ciclo `fs.confirm_request`/`fs.confirm_response` — ✅ verificato
6. [x] Caso in `tests/eval_tools.py`: conferma assente, scaduta o non correlata → `ToolResult(ok=False)` — ✅

> **ADR-002 è chiuso.** Le tre caselle sopra erano rimaste vuote pur essendo il
> lavoro fatto: spuntate il 24 agosto 2026 dopo verifica nel codice, non dedotte.

---

## ADR-003 — Ciclo di vita di T1: classificare l'uscita, annunciare l'amnesia

> ### ❌ **FATTO A METÀ — ed è il difetto peggiore ancora aperto** (24 ago 2026)
>
> `core/llm/supervisor.py` **esiste** e riconosce **solo la classe `auth`**:
> `AUTH_ERRORS = {"authentication_failed", "oauth_org_not_allowed"}`,
> `motivo = "auth_expired"`. Le classi **`transient` e `repeated` non ci sono**,
> e con loro non c'è né il replay dei fatti fissati né l'annuncio.
>
> Quindi il modo di fallire che questo stesso ADR definisce *«il peggiore che
> questo sistema possa avere»* è aperto tale e quale: T1 muore per OOM, crash o
> stream desincronizzato, `Restart=always` lo rilancia, la sessione riparte
> **vuota**, e JARVIS continua a rispondere con la stessa voce avendo perso la
> conversazione — **senza dirlo.** Contraddice §16.
>
> È il percorso che si prende **ogni volta che T1 non muore per scadenza
> OAuth**, cioè in tutti i casi tranne quello già coperto.
>
> Azioni 1, 2, 3, 4 qui sotto: **nessuna eseguita.**

**Stato**: Proposto · **Decide**: Lei · **Blocca**: Fase 3 (T1) e Fase 4 (memoria)

### Contesto
§5.6 tratta la scadenza OAuth: rilevata su `system/api_retry`, ferma il loop di
riavvio, annuncia. Eccellente — ed è il caso più probabile.

Restano gli altri: OOM, stream desincronizzato, `read` bloccata, crash del
runtime Node. Lì `Restart=always` rilancia e la sessione riparte **senza
contesto**. §5.5 assegna al `ContextPruner` il compito di reiniettare i fatti
fissati "quando la sessione viene ricreata", ma non specifica chi rileva la
ricreazione né cosa sente l'utente.

Il modo di fallire è il peggiore che questo sistema possa avere: **JARVIS
continua a rispondere, con la stessa voce e la stessa persona, avendo perso la
conversazione, e non lo dice.** Un errore rumoroso è recuperabile; questo no.
Contraddice §16: *"nessuna soglia agisce senza annunciarlo"*.

### Opzioni

**A — Supervisore con classificazione dell'uscita + replay annunciato** *(raccomandata)*
Tre classi di uscita:
`auth` → `degraded_llm`, nessun riavvio (già in §5.6);
`transient` (OOM, crash, stream rotto) → riavvio con backoff, replay dei soli
fatti fissati, **e un annuncio breve** — *"Signore, ho dovuto riavviare la
sessione. Ho conservato le Sue preferenze, non la conversazione."*;
`repeated` (N riavvii nella finestra) → `degraded_llm` e stop.

**B — Riavvio silenzioso con replay completo del contesto**
Tenta di ricostruire la conversazione dai `sessions/*.jsonl`. Contro: viola
frontalmente l'invariante 17 (non duplicare la gestione del contesto di T1) e
produce due gestori in disaccordo — il rischio che §5.5 già segnala.

**C — Nessun riavvio automatico: qualunque morte di T1 porta a `degraded_llm`**
Massima onestà, minima complessità. Contro: un crash transitorio muta JARVIS
fino a un intervento manuale, e T0 da solo non è una conversazione.

### Analisi del compromesso
B è esclusa da un invariante esistente. Fra A e C il criterio è: quanto costa
un falso `degraded_llm`? Su un sistema che Lei usa quotidianamente, molto. A
recupera automaticamente **e** paga il prezzo dell'onestà con una frase.
Il replay dei soli fatti fissati — mai della conversazione — mantiene
l'invariante 17 intatto: il contesto conversazionale resta di Claude Code, i
fatti fissati restano dell'utente.

### Decisione
**Opzione A.**

### Conseguenze
Più facile: il comportamento di T1 sotto guasto diventa specificato e testabile.
Più difficile: serve un contatore di riavvii con finestra temporale, e la frase
di annuncio deve passare dal **TTS locale** — se T1 è morto, il percorso vocale
non può dipendere da lui (stessa proprietà già sfruttata da §5.6).
Da rivedere: se in esercizio i riavvii `transient` risultassero rari, la soglia
`repeated` va abbassata.

### Azioni
1. [ ] `core/llm/supervisor.py`: classificazione `auth` / `transient` / `repeated`
2. [ ] Replay **solo** dei fatti fissati dal `ContextPruner`, mai dei turni
3. [ ] Annuncio via TTS locale + `agent.advisory` livello `warn`
4. [ ] Test: uccidere T1 con SIGKILL → riavvio, replay, annuncio; ripetere N volte → `degraded_llm`

---

## ADR-004 — `conso/` misura anche Deepgram

> ### ❌ **NON FATTO** — verificato il 24 agosto 2026
>
> `core/llm/governor.py` scrive `conso/`, ma **nessun conteggio di secondi per
> provider**: né `seconds`, né `fallback`, né la riga nel pannello telemetria.
>
> Il sistema quindi conta ancora con precisione **ciò che non gli costa** — i
> token dell'abbonamento — e non conta **l'unica cosa che gli costa.** La
> domanda aperta di §24.8 resta aperta esattamente com'era il 18 agosto.
>
> Costo: basso. Il dato lo produce già la pipeline vocale, va solo contato.

**Stato**: Proposto · **Decide**: Lei · **Blocca**: Fase 3 (voce)

### Contesto
Il Governor accumula `total_cost_usd` dagli eventi `result` dello stream in
`memory_data/conso/YYYY-MM-DD.jsonl` (§5.4). Quel campo misura l'LLM, che
l'abbonamento copre già. §24.8: Deepgram è *"la sola voce di costo ricorrente
del progetto"* e non è stata stimata.

Il sistema misura con precisione ciò che non gli costa, e non misura ciò che
gli costa.

### Opzioni

**A — Estendere `conso/` con i secondi di audio per provider** *(raccomandata)*
Ogni sessione STT e ogni sintesi TTS registra durata, provider e se era il
fallback. Il pannello telemetria mostra i minuti del mese accanto ai token.
Complessità: bassa — il dato lo produce già la pipeline, va solo contato.

**B — Consultare la dashboard Deepgram a mano, una volta al mese**
Costo nullo. Contro: il dato arriva a fine mese, disaccoppiato da cosa l'ha
generato, e non può innescare un `agent.advisory`.

**C — Tetto mensile che degrada al locale al superamento**
Va oltre la misura: introduce una politica. Prematuro senza un mese di dati
reali, ma diventa possibile — e facile — una volta adottata A.

### Decisione
**Opzione A**, con C rivalutata dopo il primo mese di misura.

### Conseguenze
Più facile: la domanda aperta §24.8 si chiude da sola con l'uso, e il conteggio
dei minuti in fallback locale dice quanto Deepgram è realmente affidabile sulla
Sua rete — un dato che nessun'altra fonte Le dà. Più difficile: il contatore
deve reggere il fallback a metà sessione senza perdere né duplicare secondi.

### Azioni
1. [ ] `conso/` registra `{provider, tier, seconds, fallback: bool}` per sessione voce
2. [ ] Pannello telemetria: minuti Deepgram della finestra corrente
3. [ ] Dopo un mese: stimare il costo, poi decidere su un tetto (opzione C)

---

## Correzioni minori — nessun ADR necessario

| # | Rilievo | Azione |
|---|---|---|
| 1 | `git init` non eseguito: il punto 4 della definizione di fatto è irraggiungibile | eseguire INSTALLA.md passo 1 e 5 |
| 2 | Font Barlow Semi Condensed e IBM Plex Mono assenti: `tokens.css` (Fase 0) si regge su di essi e il ciclo §11.7 validerebbe un render sbagliato | installarli **prima** della Fase 0 |
| 3 | INSTALLA.md §3 non eseguito: il criterio di accettazione di `core/settings.py` non è verificabile | eseguire prima della Fase 0 |
| 4 | `config/settings.toml` nel repo ha lo stesso nome del file operativo di `~/.config/`: due copie che divergeranno | rinominare in `settings.toml.example`, come già fa `secrets.toml.example` |
| 5 | Consolidamento notturno saltato per quota o auth non emette nulla — viola §16 | `agent.advisory` livello `warn` su consolidamento non eseguito |
| 6 | `docs/acceptance/` non esiste | crearla in Fase 0 |
| 7 | Cartella `jarvis-stark-os`; SPEC §21.1 e INSTALLA dicono `jarvis-os` | cosmetico — allineare o annotarlo nella SPEC |

---

## ADR-008 — Due profili di sandbox, non uno

> ⚠️ Scritto il **19 agosto 2026**, dopo la Fase 9 e §13, non prima della Fase 0
> come il resto di questo documento. Sta qui perché è una decisione
> architetturale e questo è dove vivono; la sua origine è il **rilievo aperto**
> di ADR-006 in `PERIMETRO-E-DECISIONI.md`.

### Contesto

ADR-006 ha deciso che il codice generato dall'LLM gira **solo** in sandbox. La
sandbox esiste dalla Fase 1 e `FASE-01.md` verifica, eseguendo davvero, che
blocchi **scrittura fuori radice** e **rete**.

Non blocca la **lettura**. §3.4 prescrive `--ro-bind / /`: il processo isolato
vede l'intero filesystem in sola lettura.

Finché `run_sandboxed()` aveva **un solo chiamante** — `core/doctor.py`, che
esegue `/bin/true` per accertare che bubblewrap parta — era irrilevante. Con un
tool che esegue codice generato diventa questo:

```python
print(open('/home/utente/.config/jarvis-os/secrets.toml').read())
```

Il `chmod 0600` non protegge: la sandbox gira **come lo stesso utente**. Il
`deny` in `.claude/settings.json` protegge Claude Code mentre scrive il
progetto, non il runtime. E lo stdout del processo isolato torna dritto nel
contesto dell'LLM.

**Misurato su questa macchina, non dedotto.** Col profilo attuale, da dentro la
sandbox: `secrets.toml` esiste ed è leggibile, `~/.ssh` è leggibile, `$HOME`
elenca 52 voci. Il rischio non è teorico.

### Opzioni

**A. Un profilo solo, più stretto.** Togliere `--ro-bind / /` per tutti.
Rompe il profilo «strumento»: `jarvis doctor` e i futuri strumenti di sistema
hanno bisogno di vedere i binari che invocano.

**B. Un profilo solo, con una denylist di percorsi.** `--tmpfs` sopra
`~/.config`, `~/.ssh`, `~/.aws`… Una denylist è una lista di sconfitte già
subite: il file che dimentichi è quello che perdi. L'invariante 2 dice la
stessa cosa per i tool, e vale identico qui.

**C. Due profili.** «strumento» resta com'è; «codice generato» parte da una
radice **vuota** e ci monta solo ciò che serve a far partire un interprete.

### Analisi del compromesso

C costa un parametro in più su `run_sandboxed()` e un secondo argv da
mantenere. In cambio, la domanda «che cosa può leggere il codice generato?» ha
una risposta che si legge in dieci righe invece che dedursi da ciò che *non*
è stato escluso.

La differenza fra B e C è la stessa fra denylist e allowlist, ed è già stata
decisa una volta in questo progetto: **`--tmpfs /` è l'allowlist del
filesystem.** Ciò che non è montato non esiste, e non c'è un elenco da tenere
aggiornato.

### Decisione

**Opzione C.** Due profili, e il profilo è un argomento **obbligatorio**.

| | `STRUMENTO` | `CODICE` |
|---|---|---|
| Per | `jarvis doctor`, strumenti di sistema noti | codice generato dall'LLM |
| Radice | `--ro-bind / /` — tutto in sola lettura | `--tmpfs /` — **vuota** |
| Monta | tutto l'host, ro | `/usr/lib`, `/usr/lib64`, l'albero dell'interprete |
| `/etc` | quello dell'host | **niente** |
| `$HOME` | visibile, ro | **inesistente** |
| Ambiente | ereditato | `--clearenv` |
| Scrittura | `rw_paths` sotto le radici consentite | **nessuna** — solo una tmpfs volatile |
| Ritorno | file sull'host + stdout | **solo stdout** |

Non c'è un valore predefinito. Un chiamante che dimentica il profilo non
compila, invece di ricevere il più permissivo — la stessa forma del gancio di
conferma, che se non è collegato rende inerti i tool distruttivi.

**Nessun percorso scrivibile con `CODICE`.** Passarne uno solleva
`SandboxPolicyError` prima di eseguire: il risultato del codice generato torna
per stdout, che passa da `llm/untrusted.py`, e non per un file sull'host.

### Conseguenze

- **Scostamento da §3.4**, che prescrive `--ro-bind / /` per il profilo `exec`.
  Motivato qui; §3.4 descrive un profilo solo perché è stata scritta prima di
  ADR-006.
- **L'interprete può vivere dentro `$HOME`.** Su questa macchina il Python del
  venv è gestito da uv e sta in `~/.local/share/uv/python/…`. «Nessun pezzo di
  `$HOME`» diventa allora: *nessun pezzo di `$HOME` tranne l'albero
  dell'interprete che il chiamante nomina, montato in sola lettura e per
  percorso esatto.* Quell'albero contiene un interprete e la sua stdlib, non
  segreti. Chi vuole zero `$HOME` passa un interprete di sistema.
- **Zero `/etc`, e non per prudenza: misurato.** CPython parte senza
  `/etc/ld.so.cache` perché con `/lib → usr/lib` ricreato il loader trova le
  librerie nel percorso predefinito. Se un giorno servisse, sarà **un file**
  aggiunto di proposito, non `/etc` intero.
- `SECCOMP_APPLICATO` resta `False` per entrambi i profili: ADR-008 non lo
  cambia, e `FASE-01.md` lo dichiara già.

### Azioni

- [x] `Profilo` in `core/sandbox/runner.py` — neutro rispetto alla piattaforma:
      *quale* isolamento serve è una decisione di politica, *come* si ottiene è
      di piattaforma (invariante 29).
- [x] `build_argv_codice()` in `core/platform/linux_sandbox.py`.
- [x] Test che TENTANO davvero, con il **controllo**: ogni test rieseguito col
      profilo vecchio deve fallire, o non sta provando niente.
- [x] `core/tools/code.py` — **solo dopo** questo ADR, mai prima.

---

## ADR-009 — Il tetto di memoria è un cgroup, non un rlimit

> ⚠️ Scritto il **19 agosto 2026**, subito dopo ADR-008. Nasce dal punto 3 dei
> «non verificato» di `docs/acceptance/TOOLS-CODE.md`.

### Contesto

`TOOLS-CODE.md` dichiarava: *«La RAM del processo non ha un tetto. `tmpfs_mb`
limita il disco di lavoro. Un `[0] * 10**9` in memoria non è limitato da
niente: lo fermerebbe l'OOM killer del kernel, che è una difesa della macchina,
non nostra.»*

Il punto era vero ma sottovalutato, e la ragione è nel confronto col vicino di
casa. Per la CPU, il timeout **è** una rete: `while True: pass` costa un core
per qualche secondo e poi muore. Per la memoria non lo è, perché **il timeout
limita il tempo e allocare non ne richiede.**

**Misurato su questa macchina, non dedotto:**

```
2 GiB allocati e TOCCATI, dentro il profilo CODICE, senza tetto:  0,49 s
```

Il timeout predefinito del tool è 5 s. Non sarebbe mai intervenuto: quando
scatta, la memoria è finita da quattro secondi e mezzo.

E questa macchina è una APU a **memoria unificata**. Quando la RAM finisce,
l'OOM killer del kernel sceglie la vittima con la propria euristica, non con la
nostra: può prendersi il core di JARVIS, il compositor, o la sessione desktop
intera — mentre il processo che ha causato il problema è il più piccolo dei
tre. «Lo fermerebbe l'OOM killer» non era una difesa: era la descrizione del
danno.

### Opzioni

**A. `resource.setrlimit()` prima dell'exec di bubblewrap.** Il limite si
eredita attraverso `execve` e arriva al Python isolato. Nessuna dipendenza
nuova, nessun binario esterno.

**B. `systemd-run --user --scope -p MemoryMax= -p CPUQuota=` attorno a
bubblewrap.** Un cgroup vero. Il progetto dipende già da systemd: la Fase 9
installa `jarvis-core.service` come servizio **utente**, e `systemd-run --user`
parla con lo stesso gestore.

### Analisi del compromesso — misurata, non discussa

Tutte e due sono state eseguite prima di scegliere, con lo stesso profilo
`CODICE` e lo stesso codice sotto misura. Il limite era 512 MiB.

| prova | `RLIMIT_AS` | `RLIMIT_DATA` | cgroup |
|---|---|---|---|
| 2 GiB in un processo, toccati | ferma a 448 MiB, 0,15 s | ferma a 448 MiB, 0,13 s | uccide, 0,16 s |
| **otto `fork()` da 400 MiB** | **PASSA — 3200 MiB** | **PASSA — 3200 MiB** | uccide, 0,07 s |
| **2 GiB `MAP_SHARED`, toccati** | ferma | **PASSA — 2 GiB scritti** | uccide |
| 4 GiB riservati, 1 pagina toccata | **UCCIDE** — falso positivo | passa | passa |
| programma onesto (31 MiB di picco) | passa | passa | passa |
| tetto alla CPU | — | — | **25% → un quarto dei giri** |
| latenza aggiunta | 0 | 0 | **+5,5 ms** (12,2 → 17,7 ms) |
| messaggio all'LLM | `MemoryError` | `MemoryError` | nessuno: `rc=137`, stderr vuoto |

Le due righe in grassetto decidono.

**Un rlimit è per PROCESSO.** Otto figli da 400 MiB stanno tutti sotto un
limite di 512 e insieme ne allocano 3200. Sono tre righe di `os.fork()`, e le
scriverebbe chiunque stia parallelizzando un calcolo — non serve malizia per
scavalcare la difesa, basta distrazione.

**`RLIMIT_DATA` non vede la memoria condivisa.** Copre il break e le mappature
anonime private; `mmap.mmap(-1, n)` in Python è `MAP_SHARED` per impostazione
predefinita, e ci sono passati 2 GiB scritti fino all'ultima pagina.

**`RLIMIT_AS` uccide chi non ha fatto niente di male.** Limita lo spazio di
indirizzamento *virtuale*: 4 GiB riservati e una pagina toccata sono 4 KiB di
memoria vera e un processo morto. Un tetto che uccide il lavoro legittimo viene
alzato al primo fastidio, e da lì non protegge più nulla.

Il cgroup non ha nessuno dei tre difetti, e in più chiude gratis il punto 2 —
la CPU — che con un rlimit avrebbe richiesto un'altra decisione.

### Decisione

**Opzione B.** `systemd-run --user --scope` attorno a bubblewrap, con
`MemoryMax`, `MemorySwapMax=0`, `CPUQuota` e una fetta dedicata.

Il cgroup sta **fuori** da bubblewrap, non dentro. Dentro sarebbe inutile — il
processo isolato non ha `/sys/fs/cgroup` — e comunque un limite che si applica
da sé è un limite che si può togliere da sé. Fuori, lo impone il gestore dei
cgroup, che il codice generato non può raggiungere: la stessa forma
dell'invariante 7, dove l'autorizzazione la dà il sistema operativo e non il
codice.

**Fail-closed.** Se `systemd-run` non c'è, o il gestore utente non ha delegati
i controllori `memory` e `cpu`, chiedere un tetto **solleva**. Eseguire lo
stesso senza tetto sarebbe la peggiore delle tre possibilità: chi ha scritto
`code.memory_mb = 512` crede di averlo. `jarvis doctor` ha una riga che lo
verifica, e la verifica **allocando oltre il tetto**, non guardando il `PATH`.

### Conseguenze

- **`MemorySwapMax=0` non è un dettaglio: senza, il tetto non ferma niente.**
  Misurato — con `MemoryMax=512M` e gli 8 GiB di swap di questa macchina, 2 GiB
  si allocano lo stesso, solo più lentamente. È l'unica riga senza la quale
  tutto il resto è teatro.

- **La tmpfs di lavoro pesa sullo stesso tetto.** Le sue pagine sono addebitate
  al cgroup: con `MemoryMax=32M` e `tmpfs_mb=64`, scrivere 48 MiB in `/lavoro`
  fa uccidere il processo — e il codice riceverebbe «limite di memoria
  superato» per aver usato lo spazio di lavoro che gli abbiamo dato. Lo schema
  rifiuta `memory_mb < tmpfs_mb + 64`; il margine è misurato (CPython nudo
  occupa 7 MiB in questo profilo, un programma onesto 31 al picco).

- **Il codice d'uscita non basta a riconoscere l'OOM**, e sbaglia in entrambe
  le direzioni: `137` arriva sia dal kernel che uccide, sia da un
  `os.kill(os.getpid(), SIGKILL)` scritto dal codice, sia da un `sys.exit(137)`.
  La verità sta in `memory.events` del cgroup. La diagnosi è a tre livelli:
  `memory.events` dello scope se si riesce a leggerlo, altrimenti il contatore
  della **fetta** prima/dopo, altrimenti si dichiara che non si è potuto
  confermare.

- **La fetta dedicata `jarvis-codice.slice` non è ordine.** In cgroup v2
  `memory.events` è gerarchico, e lo scope viene smontato appena si svuota —
  una lettura che è andata bene 25 volte di fila e poi ha cominciato a fallire
  sempre, che è il modo peggiore in cui una difesa può essere sbagliata. Il
  contatore della fetta invece regge, perché la fetta resta `active` anche
  vuota. Sotto `app.slice` comprenderebbe l'OOM di qualunque altra
  applicazione della sessione; dentro una fetta nostra conta solo noi.

- **`OOMPolicy=continue` non allenta niente.** Quando arriva, il kernel ha già
  ucciso il processo; impedisce solo a systemd di fermare lo scope per
  reazione, e quindi di smontare il cgroup mentre stiamo per leggerlo.

- **Windows.** `systemd-run` non esiste: `memoria_mb` e `cpu_percento` sono
  **politica** e stanno in `core/sandbox/runner.py` — «il codice generato non
  supera N megabyte e mezzo core» si dirà identico — mentre il cgroup è
  implementazione e sta in `platform/`. Là sarà un Job Object. Invariante 29,
  e il test che la impone adesso vieta anche `systemd-run`, `MemoryMax`,
  `CPUQuota` e `/sys/fs/` fuori da `platform/`.

- **+5,5 ms per esecuzione.** Un'unità transitoria si crea via DBus. Su un tool
  che già costa 12 ms di bubblewrap è il 45% in più di un tempo che nessuno
  aspetta.

### Azioni

- [x] `memoria_mb` e `cpu_percento` su `run_sandboxed()`, e
      `SandboxMemoriaEsaurita` accanto a `SandboxTimeout`.
- [x] `argv_limite()`, `oom_nella_fetta()` e `eventi_memoria()` in
      `core/platform/linux_sandbox.py`.
- [x] `code.memory_mb` e `code.cpu_percent` nelle impostazioni, col controllo
      che `memory_mb` stia sopra `tmpfs_mb`.
- [x] Riga `CODICE` in `jarvis doctor`, che **misura** allocando oltre il tetto.
- [x] Test che allocano davvero, comprese le due evasioni che escludono A.

---

# Sintesi

La rev 5.0 è una specifica solida. Le tre decisioni portanti — T1 persistente,
core proprietario delle operazioni reali, allowlist tipizzata — sono corrette e
motivate da misure, non da preferenze. Il modello a tre tier produce una
proprietà che vale la disciplina che costa: **T0 sopravvive a qualunque guasto.**

I quattro punti aperti hanno tutti la stessa forma: un invariante **dichiarato**
nel posto giusto e non ancora **imposto** lì. La conferma umana vive nel
renderer invece che nel core — *chiuso in rev 5.1: il socket UNIX la sposta nel
kernel*. Il riavvio di T1 è specificato per il caso più
probabile e non per gli altri. Il costo misurato è quello che non si paga.
Il vincolo Python è scritto nella SPEC e non nell'ambiente.

Nessuno dei quattro è caro adesso. Tutti e quattro lo diventano dopo.

**Prima della Fase 0**: correzioni minori 1, 2, 3 — sono prerequisiti, non
decisioni. **In Fase 0**: ADR-001. **In Fase 1**: ADR-002.
**In Fase 3**: ADR-003 e ADR-004.
