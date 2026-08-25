# Perimetro e decisioni — ADR-005, 006, 007

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

> ### ❌ **ZERO RIGHE** — verificato il 24 agosto 2026
>
> Nessun `core/mcp/`, nessun `registry.promuovi_mcp()`, nessuno dei due eval.
> Le quattro azioni in fondo: **nessuna iniziata.**
>
> È l'ADR che questo stesso documento chiama *«il singolo moltiplicatore di
> capacità più grande disponibile dentro il perimetro scelto»*. La decisione è
> presa e regge; il codice non esiste.
>
> Va **dopo** ADR-003, perché aprire una superficie nuova mentre il ciclo di
> vita di T1 ha ancora un buco significa moltiplicare anche quello.

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

- [ ] Client MCP nel core, dietro `platform/` se usa trasporti specifici.
- [ ] `registry.promuovi_mcp(server, nome_tool, side_effect)` — esplicito.
- [ ] Un eval: un server MCP che annuncia un tool non nominato → non invocabile.
- [ ] Un eval: una descrizione di tool con istruzioni iniettate → nessuna azione.

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
