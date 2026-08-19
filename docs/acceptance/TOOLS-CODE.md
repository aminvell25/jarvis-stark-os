# `core/tools/code.py` — esito

**Data**: 19 agosto 2026 · **Riferimento**: ADR-006 (`PERIMETRO-E-DECISIONI.md`),
ADR-008 (`VALUTAZIONE-ARCHITETTURALE.md`)
**Test**: 400 verdi (erano 374), di cui **30** nuovi · **Precedente**: `ADR-008.md`

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
| 9 | registrato nella radice | `register_code_tool` in `core/engine.py` | 2 test + il conteggio 21 → **22** |

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

## ❌ NON VERIFICATO

1. **Nessun codice scritto da un LLM.** I frammenti li ho scritti io. Un
   modello produce cose che a un umano non vengono in mente, e il tool non è
   mai stato chiamato da T1 o T2 — la pipeline vocale non è composta e il
   router non ha ancora una strada verso questo tool.
2. **Il consumo di CPU non ha un tetto.** Tempo, memoria di lavoro, output e
   concorrenza sì; i cicli no. `while True: pass` viene ucciso dal timeout, ma
   per quei secondi occupa un core intero. `--unshare-cgroup` isola il
   namespace, non impone un limite: servirebbe un cgroup vero, che è un'altra
   decisione.
3. **La RAM del processo non ha un tetto.** `tmpfs_mb` limita il *disco* di
   lavoro. Un `[0] * 10**9` in memoria non è limitato da niente: lo fermerebbe
   l'OOM killer del kernel, che è una difesa della macchina, non nostra.
4. **`/proc` del namespace non è stato guardato.** Eredita il punto 4 di
   ADR-008. Il codice vede il `/proc` del proprio PID namespace — cosa possa
   dedurne non l'ho misurato.
5. **Nessun tetto al numero di esecuzioni nel tempo.** Il semaforo limita
   quante insieme, non quante all'ora. Il `Governor` fa questo per T2; per
   `esegui_codice` non c'è l'equivalente.
6. **`enabled` non esiste.** Gli altri sottosistemi consequenziali — voce,
   news, vision — hanno un interruttore nelle impostazioni e partono spenti
   (Fase 9). Questo tool no: è registrato sempre. Non me l'ha chiesto nessuno,
   ma è la prima cosa che aggiungerei.

---

## Riepilogo

| | |
|---|---|
| Test | **400 verdi** (erano 374), di cui **30** nuovi |
| Vincoli richiesti | **9 su 9**, ognuno con almeno un test che tenta |
| Punti di ADR-008 chiusi | **2 su 5**, uno neutralizzato, 2 aperti |
| Difetti trovati dai test | **3**, due dei quali erano nei test stessi |
| Allowlist | 21 → **22** |
| Dipendenze aggiunte | **nessuna** |
| Linguaggi eseguibili | **1** — Python, e per scelta |
