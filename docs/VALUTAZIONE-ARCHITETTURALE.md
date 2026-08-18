# Valutazione architetturale — pre-Fase 0

**Data**: 18 agosto 2026 · **Oggetto**: `docs/SPEC.md` rev 5.0 · **Stato del codice**: zero

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
4. [ ] `ws_server.py` su `websockets.unix_serve()`, directory a 0700 — Fase 1
5. [ ] `request_id` + scadenza sul ciclo `fs.confirm_request`/`fs.confirm_response` — Fase 1
6. [ ] Caso in `tests/eval_tools.py`: conferma assente, scaduta o non correlata → `ToolResult(ok=False)` — Fase 2

---

## ADR-003 — Ciclo di vita di T1: classificare l'uscita, annunciare l'amnesia

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
