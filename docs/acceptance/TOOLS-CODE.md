# `core/tools/code.py` — esito

**Data**: 19 agosto 2026 · **Riferimento**: ADR-006 (`PERIMETRO-E-DECISIONI.md`),
ADR-008 e **ADR-009** (`VALUTAZIONE-ARCHITETTURALE.md`)
**Test**: **446 verdi** (erano 404), di cui **42** nuovi in questa passata · **Precedente**: `ADR-008.md`

> ⚠️ La prima stesura di questo documento diceva «400 verdi». Erano **404**:
> 395 passati, 3 falliti e 6 in errore per il limite di istanze `inotify`
> dell'utente (102 su 128 le teneva la sessione desktop), che non c'entrava
> col tool. Il numero giusto è quello che pytest raccoglie, non quello che
> passa.

> **Seconda passata, 19 agosto**: i punti 2, 3 e 6 dei «non verificato» qui
> sotto sono stati chiusi. Vedi **ADR-009** e la sezione omonima più giù.

`esegui_codice(sorgente, timeout_s)`. Solo Python, in `Profilo.CODICE`.
È il primo chiamante reale del profilo, ed è arrivato **dopo** che il profilo
era verificato — l'ordine che ADR-008 chiedeva.

---

## I nove vincoli

| # | Vincolo | Come è imposto | Test |
|---|---|---|---|
| 1 | `side_effect=False`, `planner=None` | in `CODICE` non c'è effetto da confermare, e `register()` rifiuta un planner senza `side_effect` | `test_non_ha_effetti_e_non_ha_piano` |
| 2 | `gesture_allowed=False` **esplicito** | l'invariante 27 non copre i tool senza `side_effect`: qui non scatterebbe | `test_nessuna_gesture_puo_eseguire_codice` + `test_invoke_da_gesture_lo_rifiuta_davvero` |
| 3 | tetto alla tmpfs | `--size` prima del `--tmpfs`, da `settings.code.tmpfs_mb` | 3 test, fra cui **superarlo** |
| 4 | tetto all'output | `tronca()` in byte, sul confine del carattere | 4 test |
| 5 | stdout non fidato | `Untrusted.da(...).avvolto()`, invariante 5 | 2 test |
| 6 | timeout limitato | `min(richiesto, max_timeout_s)`, e dichiarato | 3 test |
| 7 | interprete risolto una volta | `@cache`, rifiuta i venv | 3 test |
| 8 | concorrenza | semaforo asyncio da `max_concurrent` | 2 test, uno con 10 insieme |
| 9 | registrato nella radice | `register_code_tool` in `core/engine.py` | 2 test + il conteggio, che ora **dipende dall'interruttore** |
| 10 | tetto di RAM e di CPU | cgroup via `systemd-run`, fuori da bubblewrap (ADR-009) | 28 test, fra cui le due **evasioni** |
| 11 | `code.enabled`, spento di serie | il tool non si registra: non esiste | 6 test |

---

## La minaccia di ADR-006, eseguita attraverso il tool

ADR-008 ha provato il profilo passando frammenti a `run_sandboxed()`. Qui la
stessa prova percorre la **strada vera** — allowlist, `invoke()`, tetti,
marcatore — perché è quella che percorrerà l'LLM. Una difesa verificata un
livello più sotto di dove vive è una difesa verificata altrove.

| Tentativo, dal tool | Esito |
|---|---|
| `print(open('~/.config/jarvis-os/secrets.toml').read())` | ✅ `FERMATO FileNotFoundError` |
| `os.listdir(os.path.expanduser('~'))` | ✅ `FERMATO` |
| `socket.create_connection(('1.1.1.1', 443))` | ✅ `FERMATO` |
| scrittura in una directory dell'host | ✅ `FERMATO`, e il file non compare |

E il tool gira davvero, nel processo vero:

```
esegui_codice  sorgente="import statistics; print(statistics.mean([2,4,6]))"
→ ok True
  stdout <untrusted_source origin="codice generato"> 4 </untrusted_source>
  {'returncode': 0, 'untrusted': True, 'stdout_troncato_byte': 0,
   'timeout_s': 5.0, 'timeout_limitato': False, 'lavoro_mb': 64}
```

---

## Cosa risulta ora chiuso di ADR-008

| # | «Non verificato» di ADR-008 | Adesso |
|---|---|---|
| 1 | **Nessun chiamante reale** | ✅ **CHIUSO.** `esegui_codice` esiste, è nell'allowlist, e le prove di segregazione passano dalla sua strada |
| 2 | Solo CPython | ⚠️ **RESTA APERTO, e per scelta.** Il tool esegue *solo* Python, proprio perché `albero_interprete()` non è provata altrove. Il buco non è stato chiuso: gli è stato tolto il chiamante |
| 3 | Solo questa macchina | ❌ resta aperto, invariato |
| 4 | Solo lettura del filesystem | ❌ resta aperto, invariato — `/proc` del namespace e canali laterali non sono stati guardati |
| 5 | **Tenuta sotto carico** | ✅ **CHIUSO.** Tetto alla tmpfs verificato superandolo (`ENOSPC`), e dieci esecuzioni concorrenti con la sovrapposizione misurata |

Due chiusi, uno neutralizzato togliendogli il chiamante, due invariati.

---

## Tre cose trovate dai test, non progettate

### ① `-I` non basta: i site-packages di sistema entravano

Il test diceva «niente site-packages» e falliva: `sys.path` conteneva
`/usr/lib/python3/dist-packages`, che arriva col mount di `/usr/lib`.

Non è un varco — è sola lettura, e ADR-008 monta `/usr/lib` perché lì c'è la
stdlib — ma è **superficie che nessuno aveva deciso di dare**. Il profilo dice
«l'interprete e la stdlib»: aggiunto `-S`, che è ciò che rende vera quella
frase.

### ② Il mio test della concorrenza misurava la cosa sbagliata

Falliva dicendo «6 esecuzioni insieme» col limite a 2. Non era il semaforo: era
il cronometro. Misuravo attorno a `invoke()`, che **ritorna dopo aver atteso**
il semaforo — quindi tutti e sei gli intervalli partivano subito e si
sovrapponevano anche mentre quattro erano in coda.

Adesso è il codice isolato a scrivere i propri istanti: si misura **quando ha
girato**, non quando qualcuno ha chiesto che girasse. Con la misura giusta il
massimo è 2.

### ③ `invoke_da_gesture` solleva, non restituisce `ok=False`

Il mio test si aspettava un `ToolResult` negativo. Il registry solleva
`GestureVietata` — ed è la scelta giusta: un `ToolResult` negativo è un esito
che il chiamante può ignorare, un'eccezione no. Un intento di gesture verso un
tool vietato è un errore di cablaggio, non un caso normale. Ho corretto il
test, non il registry.

---

## Decisioni di progetto

**I tetti sono politica, non parametri.** Il timeout che arriva dall'LLM è un
desiderio; quanto ne ottiene lo decide `settings.code`. Nessuno dei quattro
tetti è alzabile da chi chiama.

**Una troncatura dichiarata.** `stdout_troncato_byte` è sempre nel risultato, e
nel testo resta un rigo che lo dice. Un'uscita tagliata in silenzio è peggio di
un errore: chi legge crede di avere il risultato intero e ci ragiona sopra.

**Il sorgente passa per argomento, non per file.** Niente file da scrivere,
niente percorso da validare, niente residuo.

**Un semaforo per limite, non uno solo.** Le impostazioni si ricaricano a
caldo: cambiare `max_concurrent` deve poter avere effetto senza riavviare.

---

## ADR-009 — il tetto di memoria, e perché non era quello che credevo

Il punto 3 diceva «la RAM non ha un tetto» e lasciava intendere che il timeout
facesse da rete. **Non ne fa.** Il timeout limita il TEMPO, e allocare non ne
richiede: misurato, **2 GiB in 0,49 s**, contro un timeout predefinito di 5.
Quando sarebbe scattato, la memoria era finita da quattro secondi e mezzo. E su
una APU a memoria unificata l'OOM killer sceglie la vittima con la propria
euristica: può prendersi il core di JARVIS o la sessione desktop invece del
processo isolato.

Le due strade sono state **misurate entrambe** prima di scegliere, come per
`--size`. La tabella completa è in ADR-009; qui le due righe che decidono:

| prova, limite 512 MiB | `RLIMIT_AS` | `RLIMIT_DATA` | cgroup |
|---|---|---|---|
| **otto `fork()` da 400 MiB** | **PASSA — 3200 MiB** | **PASSA — 3200 MiB** | uccide, 0,07 s |
| **2 GiB `MAP_SHARED`, toccati** | ferma | **PASSA — 2 GiB scritti** | uccide |
| 4 GiB riservati, 1 pagina usata | **UCCIDE** un onesto | passa | passa |
| tetto alla CPU | — | — | 25% → **un quarto dei giri** |

**Un rlimit è per processo.** Tre righe di `os.fork()` lo scavalcano, e le
scriverebbe chiunque stia parallelizzando un calcolo: non serve malizia, basta
distrazione. Il cgroup addebita l'albero intero. E chiude gratis il punto 2, la
CPU, che era la condizione posta.

### Quattro cose trovate misurando

**① Senza `MemorySwapMax=0` il tetto non ferma niente.** Con `MemoryMax=512M` e
gli 8 GiB di swap di questa macchina, 2 GiB si allocano lo stesso — il kernel
li scarica su disco e il processo continua, solo più lento. È l'unica riga
senza la quale tutto il resto è teatro.

**② Il codice d'uscita sbaglia in tutte e due le direzioni.** `137` arriva sia
dall'OOM del kernel, sia da un `os.kill(os.getpid(), SIGKILL)` scritto dal
codice, sia da un `sys.exit(137)`. Attribuire la memoria a chi non l'ha
esaurita è una diagnosi sbagliata mandata all'LLM, che poi ci ragiona sopra.
La verità sta in `memory.events`, e due test verificano proprio i casi che NON
devono diventare un errore di memoria.

**③ La lettura «giusta» ha funzionato 25 volte e poi ha smesso.** Il
`memory.events` dello scope è andato bene 25 volte di fila — abbastanza da
sembrare deterministico — e poi ha cominciato a fallire *sempre*, senza che
cambiasse una riga: systemd smonta lo scope appena si svuota, ed è una corsa.
Anche tenere aperto il descrittore non salva: dopo la rimozione la `read()`
dà `ENODEV`. La risposta stabile è il contatore **della fetta**, che in cgroup
v2 è gerarchico e non sparisce — e la fetta è dedicata (`jarvis-codice.slice`)
perché sotto `app.slice` conterebbe anche l'OOM dell'editor dell'utente.

Una difesa che funziona finché non serve è peggio di una che non c'è.

**④ La tmpfs di lavoro pesa sullo stesso tetto.** Con `MemoryMax=32M` e
`tmpfs_mb=64`, scrivere 48 MiB in `/lavoro` fa uccidere il processo — e il
codice riceverebbe «limite di memoria superato» per aver usato lo spazio di
lavoro che gli abbiamo dato. Lo schema adesso rifiuta quella configurazione:
non è stretta, è rotta.

---

## L'interruttore — punto 6

`code.enabled = false`, come `voice` e `vision`. Spento, il tool **non esiste**:
non è registrato, quindi non compare nell'elenco che l'LLM riceve e non c'è
niente da rifiutare. La differenza fra una porta chiusa a chiave e un muro è
che della prima si vede la maniglia, e un modello che la vede prova ad aprirla.

Il conteggio dell'allowlist adesso **dipende dall'interruttore** — 21 spento,
22 acceso — e lo legge dallo stesso posto da cui lo legge l'engine. Un `== 22`
fisso sarebbe rimasto verde anche il giorno in cui l'interruttore avesse
smesso di funzionare, che è il caso peggiore possibile per questo tool.

⚠️ **Asimmetria dichiarata**: i tetti si rileggono a ogni chiamata, la
registrazione no. Accendere `code.enabled` richiede il riavvio del core. È la
stessa asimmetria che in §13 ha fatto sembrare inefficace un cambio di
categoria nel file manager, e qui è dalla parte giusta.

---

## Un difetto trovato nel test dell'invariante 29

Estendendo il divieto a `systemd-run` e `cgroup`, il controllo ha accusato
`core/settings.py`, che quelle cose non le chiama: la parola «cgroup» era in un
**messaggio d'errore dentro una f-string**.

Da Python 3.12 (PEP 701) il testo letterale di una f-string non è più un token
`STRING` ma `FSTRING_MIDDLE`, e il filtro «togli commenti e stringhe» lo
lasciava passare come se fosse codice. Il test scansionava prosa da quando il
progetto è passato a 3.12, e nessuno se n'era accorto perché fino a ieri
nessuna f-string aveva nominato una cosa vietata.

---

## ❌ NON VERIFICATO

1. **Nessun codice scritto da un LLM.** I frammenti li ho scritti io. Un
   modello produce cose che a un umano non vengono in mente, e il tool non è
   mai stato chiamato da T1 o T2 — la pipeline vocale non è composta e il
   router non ha ancora una strada verso questo tool. **Invariato, ed è il più
   importante dei sei.**
2. ~~**Il consumo di CPU non ha un tetto.**~~ ✅ **CHIUSO** con ADR-009:
   `CPUQuota` è arrivata insieme al cgroup che serviva per la memoria, ed è
   verificata misurando — al 25% il ciclo stretto fa un quarto dei giri.
3. ~~**La RAM del processo non ha un tetto.**~~ ✅ **CHIUSO** con ADR-009:
   `MemoryMax` + `MemorySwapMax=0`, verificato allocando davvero, comprese le
   due evasioni che escludono `resource.setrlimit()`.
4. **`/proc` del namespace non è stato guardato.** Eredita il punto 4 di
   ADR-008. Invariato.
5. **Nessun tetto al numero di esecuzioni nel tempo.** Il semaforo limita
   quante insieme, non quante all'ora. Il `Governor` fa questo per T2; per
   `esegui_codice` non c'è l'equivalente. Invariato.
6. ~~**`enabled` non esiste.**~~ ✅ **CHIUSO**: c'è, è `false` nello schema e
   nel file spedito, e spento il tool non è nell'allowlist.

### E sei nuovi, aperti da ADR-009

7. **Il contatore della fetta può confondere due esecuzioni nostre.** È
   dedicato, quindi nessun'altra applicazione lo sporca, ma con
   `max_concurrent = 2` due esecuzioni insieme condividono la fetta: se una
   esaurisce la memoria mentre l'altra muore di segnale per un'altra ragione,
   la seconda riceve il messaggio della prima. Il primo livello della diagnosi
   — `memory.events` dello scope — non ha questo difetto, ma è quello che si
   perde. Non l'ho provocato apposta.
8. **`systemd-run` provato solo qui.** systemd 257, cgroup v2 puro, controllori
   `memory` e `cpu` delegati al gestore utente. Su una distribuzione senza
   delega, o con cgroup v1, `limite_mancante()` dice di no e il tool non parte
   — che è il comportamento voluto — ma non l'ho eseguito su una macchina così.
9. **Il tetto non è mai stato provato dentro `jarvis-core.service`.** Ho
   verificato che `systemd-run --user --scope` funziona **annidato** dentro un
   servizio utente transitorio, che è la stessa forma; il servizio vero non
   l'ho avviato per questa prova.
10. **I +5,5 ms per esecuzione sono misurati a vuoto.** Mediana 12,2 → 17,7 ms
    su otto esecuzioni banali, con la macchina scarica. Sotto carico, e con due
    esecuzioni concorrenti, non li ho rimisurati.
11. **La riga `CODICE` del doctor alloca il doppio del tetto ogni volta.** Con
    il predefinito sono 1 GiB toccati a ogni `jarvis doctor`, per ~150 ms. È
    voluto — «ogni controllo misura» — ma su una macchina già in affanno è
    proprio il momento peggiore per chiedere un giga.
12. **Nessuna prova che il tetto protegga la SESSIONE.** Ho verificato che il
    processo isolato viene fermato; non ho verificato la conseguenza che
    motiva tutto, cioè che con il tetto attivo una macchina sotto pressione non
    perda il compositor. Provarlo vorrebbe dire portare davvero questa macchina
    sull'orlo dell'OOM, e non l'ho fatto.

---

## Riepilogo

| | |
|---|---|
| Test | **446 verdi** (erano 404), **42** nuovi qui, **72** in tutto sul tool |
| Vincoli richiesti | **11 su 11**, ognuno con almeno un test che tenta |
| Punti di ADR-008 chiusi | **2 su 5**, uno neutralizzato, 2 aperti |
| «Non verificato» di questo documento chiusi | **3 su 6** — 2, 3 e 6 |
| Strade misurate prima di scegliere | **3** — `RLIMIT_AS`, `RLIMIT_DATA`, cgroup |
| Difetti trovati dai test | **6**, **quattro** dei quali erano nei test stessi |
| Allowlist | 21 spento, **22** acceso |
| Dipendenze aggiunte | **nessuna** — `systemd-run` era già un presupposto (Fase 9) |
| Linguaggi eseguibili | **1** — Python, e per scelta |
| Predefinito | **spento** |
