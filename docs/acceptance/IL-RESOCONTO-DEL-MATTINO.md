# Il resoconto del mattino — il caso d'uso quotidiano

**Data**: 2 settembre 2026 · **Riferimento**: `CLAUDE.md` «Il caso d'uso
quotidiano», `docs/PIANO-JARVIS-COGNITIVO.md` fetta 7, `docs/SPEC.md` §5.5
· **Rollback**: il commit precedente a questo · **Test**: 2071 → **2122** passati
(2147 raccolti, 25 saltati, **51** test nuovi)

---

## Il difetto, misurato prima di scrivere una riga

Il risveglio (`core/memory/risveglio.py`, `Engine._resoconto_al_risveglio`)
leggeva **una sorgente su tre**: solo `initiatives/`. Sapeva dire che cosa
JARVIS aveva *fatto* — due frasi, `protocollo` e `consolidamento` — e non che
cosa si era *rotto*. I guasti andavano soltanto su structlog: `grado_parziale`,
`ripiego_annunciato`, `voce_caduta`, `t1_degradato`, il consolidamento saltato
per quota, `protocollo_senza_tool`, `mcp_non_montato`. E structlog, senza
systemd, non viene nemmeno scritto: `jarvis-core.service` è `disabled`, il
journal aveva 1 riga in 3 giorni, nessun file di log su disco.

Sul disco vero, prima di questa fetta:

| | |
|---|---|
| righe di diario in 8 giorni | **91** — 58 `dialogo`, 33 `azione` |
| righe con `ok=False` | **0** |
| righe con un `verdetto` | **0** |
| `core_avviato` / `core_fermato` | righe di **log**, non di diario |
| lettori del diario in `core/` | **nessuno** (`core/diario.py:128`) |

Il candidato scritto in `CLAUDE.md` diceva «legge il diario, il journal e i
log». Il journal e i log sono usciti: il diario è l'unico registro che una
persona rilegge, e un guasto che vale la pena dire al mattino vale la pena
scriverlo lì.

## Le tre decisioni

### ① Un emettitore solo, nel registro che c'è già

Nessun file «guasti», nessun ADR: accendersi, spegnersi e fallire sono azioni
del sistema con esito, e il flusso `azione` del diario è il loro registro.
`Engine._annota_guasto(traccia, tipo, *, errore, strada, **campi)` scrive
`ok=False`, `intento=<tipo>`, `errore=<codice chiuso>`, la traccia — o
`da="referto"` quando chi riferisce non conosce il turno, dichiarato in
`scripts/orfani.py`. Sette emettitori:

| tipo | dove | `errore` ∈ |
|---|---|---|
| `ripiego_voce` | `_gradi`, dopo `costruisci_stt/tts` | `Motivo.CHIAVE_ASSENTE`, `Motivo.ERRORE` |
| `microfono_caduto` | `_voce_e_finita` → `_riferisci_microfono` | `flusso finito`, `eccezione` |
| `t1_degradato` | `Supervisore.riferisci` / `su_evento`, via `annota` | `EventoT1.value` |
| `consolidamento` | `_consolida_di_notte` → `_riferisci_consolidamento` | `quota`, `caduto` |
| `protocollo` | `_ronda_di` | `CAUSE_ESITO` di `core/protocolli.py` |
| `mcp` | `_gradi`, dopo `monta_mcp` | `non montato`, `promozione fallita` |
| `resoconto` | `_resoconto_al_risveglio`, ramo `except` | `caduto` |

Più tre tipi **derivati**, che il lettore deduce da righe che il registro
scriveva già e nessuno rileggeva: `comando_fallito` (`ok=False`),
`comando_smentito` (`verdetto == "fallito"`, ADR-012), `senza_risposta`
(`errore == "t1_assente"`).

Che cosa **non** è un guasto: `grado_spento` per configurazione,
`Motivo.CONFIGURATO`, il no del Signore a una conferma (`operazione
rifiutato/scaduto`), `non_verificato`, il resoconto stesso, il ciclo di vita.
E `engine.py:2088` resta vero alla lettera: il protocollo che **gira** ha il
suo record in `initiatives/`; qui entra solo quello che **non** gira, che
iniziativa non è.

### ② Nessun modello, nemmeno per il «perché»

La causa pronunciata viene da `CAUSE[tipo]`, un elenco chiuso di codici → parole,
tenuto uguale ai suoi produttori da tre test (`EventoT1`, `Motivo`,
`CAUSE_ESITO`). Il testo libero — `repr(exc)`, `r.error` — va nel campo
`dettaglio`: si legge con `scripts/diario.py --azioni` o `--traccia ID`, e non
si pronuncia. Una causa fuori tabella si dice «per una ragione che è nel
diario», che è vero e non spiega — meglio di una spiegazione inventata.

### ③ «Spento» si legge dal ciclo di vita, mai dai buchi

`core_avviato` (prima di `_gradi()`: una scrivania può collegarsi mentre si
accendono) e `core_fermato` (dopo `_spegni_gradi()`, con `scrivi` perché il
socket sta chiudendo) entrano nel diario con la traccia dell'avvio. L'ultimo
evento del ciclo di vita prima di questo avvio decide: un `core_fermato` è uno
spegnimento pulito, un `core_avviato` è un processo morto senza dirlo — e
allora si dice l'ultima cosa scritta e che lo spegnimento non è registrato
(invariante 23). Dieci ore di silenzio possono essere JARVIS acceso e muto:
dai buchi non si deduce niente.

Variante scelta dal proprietario: **«da quando non c'era»**. La unit resta
disabilitata; il resoconto copre l'intervallo dall'ultimo timbro. Se un giorno
la unit venisse abilitata non cambia una riga di codice: cambia l'accettazione.

---

## Verifica

### ✅ I test — 51 nuovi, e i vecchi restano verdi

`tests/test_il_resoconto_al_risveglio.py` (17 → 58), `tests/test_supervisor.py`
(+5), `tests/test_i_protocolli_dichiarati.py` (+5), `tests/test_engine.py`
(il ciclo di vita nel diario, con traccia). I sei presìdi esistenti su
`_resoconto_al_risveglio`, `_consolida_di_notte` e `_ronda_di` sono passati
senza essere toccati.

```
uv run pytest -q -p no:cacheprovider     → 2122 passati, 25 saltati
uv run python scripts/orfani.py          → 0 sospetti nuovi (baseline rigenerata: 561 → 568 definizioni)
```

### ✅ Le nove bocciature — ognuna un rosso

| sabotaggio | esito |
|---|---|
| una frase tolta da `GUASTI` | 1 rosso |
| il taglio `> da` diventa `>=` | 1 rosso |
| il guasto scritto con `ok=True` | **verde alla prima stesura**, 2 rossi alla seconda — vedi sotto |
| «spento» senza `core_fermato` | 1 rosso |
| `core_fermato` prima di `_spegni_gradi()` | 1 rosso |
| pronunciare `ripiego_voce` | 1 rosso |
| il supervisore non annota il riavvio | 1 rosso |
| ripetere il ripiego di questo avvio | 1 rosso |
| il protocollo che non gira senza riga | 1 rosso |

⚠️ **L'ottava volta.** Il terzo sabotaggio è restato verde: il test cercava
`ok=False` nel corpo di `_annota_guasto`, e la **docstring** lo nomina. Il
togli-commenti di questo file toglie i `#`, non le docstring. Adesso il test
scarta la docstring **e** scrive davvero due righe su un diario con i metodi
veri di `Engine`, come fa `tests/test_la_traccia_non_si_perde.py`.

### ✅ In laboratorio — config e dati temporanei, `claude` fuori dal PATH

`XDG_CONFIG_HOME`, `XDG_DATA_HOME` e `XDG_RUNTIME_DIR` su cartelle proprie
(⚠️ il runtime dir **corto**, `/tmp/jlab-run`: il primo tentativo è morto su
`sun_path` a 132 byte contro 108), un protocollo dichiarato su `/root` (fuori
dalle radici), una sessione di ieri da consolidare, e una scrivania **finta**
che manda `client.ruolo` come fa `app/main.js`.

Primo avvio, dopo 2 s:

```
22:56:28   ok  core_avviato     via core
22:56:28   NO  consolidamento   via memoria   — caduto
22:56:30   NO  protocollo       via protocollo  — senza risposta
22:56:30   ok  resoconto_al_risveglio via diario
  «Signore, qualcosa non e' andato mentre non c'era: non ho messo in ordine gli
   appunti perche' qualcosa e' caduto a meta' e il protocollo ronda impossibile
   non e' potuto girare perche' il suo strumento non ha risposto.»
```

`SIGTERM`, tre secondi, secondo avvio:

```
22:56:38   ok  core_fermato     via core
22:56:41   ok  core_avviato     via core
22:56:44   NO  protocollo       via protocollo  — senza risposta
22:56:44   ok  resoconto_al_risveglio via diario
  «Signore, sono stato spento da oggi alle 22:56 a oggi alle 22:56. E c'e'
   qualcosa che non e' andato: il protocollo ronda impossibile non e' potuto
   girare perche' il suo strumento non ha risposto.»            spento_s=2,98
```

`scripts/orfani.py --diario`: 8 righe, **8 tracciate**, 0 orfane. La riga del
consolidamento porta la traccia `PROTOCOLLO` coniata prima di `conso.esegui()`.

### ✅ Sul disco VERO — config e dati del Signore, voce accesa, T1 avviato

Stesso giro con il core avviato come lo avvia systemd, `claude-haiku-4-5`
come T1, Deepgram primario (chiave valida: nessun ripiego).

```
22:57:45   ok  core_avviato     via core
22:57:48   ok  resoconto_al_risveglio via diario
  «Signore, non ho registrato lo spegnimento: l'ultima cosa che ho scritto e'
   di oggi alle 12:50, e mi sono riacceso oggi alle 22:57. Per il resto,
   niente da riferire.»                                       spento_s=36420
22:58:02   ok  core_fermato     via core
22:58:09   ok  core_avviato     via core
22:58:12   ok  resoconto_al_risveglio via diario
  «Signore, sono stato spento da oggi alle 22:58 a oggi alle 22:58. Per il
   resto, niente da riferire.»                                spento_s=6,65
22:58:27   ok  core_fermato     via core
```

La prima frase è **vera e nuova**: il core di stamattina non ha lasciato
`core_fermato` perché quella riga non esisteva ancora, e il resoconto lo dice
invece di inventare un orario. `scripts/orfani.py --diario` sul diario vero:
45 tracciate, 61 vecchie, 9 dichiarate, **0 orfane**.

### Due difetti trovati DAL VIVO, non dai test

**Il primo avvio di sempre diceva «non ho registrato lo spegnimento».** Con il
diario vuoto e nessun timbro, `avviato_a > da` era vero e non c'era nessuna
riga prima: il resoconto parlava di un processo mai esistito. Adesso, senza
righe prima di questo avvio, non c'è uno spegnimento di cui parlare.

**Una sessione non consolidata per T2 caduto non lasciava nessun guasto.**
`Consolidatore.esegui()` la copriva con un advisory di un istante e tornava
`eseguito: True, topic: 0`: due turni letti, zero appunti, e il mattino dopo
niente. Adesso conta `fallite`, e il motore la riferisce come `caduto`.

### Criterio / Esito

| # | criterio | esito |
|---|---|---|
| 1 | la riga in `CLAUDE.md` è scritta e la copia in SPEC §20 è uguale | ✅ `tests/test_tokens.py` |
| 2 | ogni tipo emesso ha una frase, provato col sabotaggio | ✅ 1 rosso |
| 3 | nessun modello nel compositore, nemmeno per la causa | ✅ test esistente + `CAUSE` chiuso |
| 4 | `core_avviato` / `core_fermato` sul disco vero | ✅ righe delle 22:57-22:58 |
| 5 | orari veri nella frase | ✅ «da oggi alle 22:58 a oggi alle 22:58», 6,65 s |
| 6 | A — protocollo che non gira | ✅ in laboratorio, `senza risposta` |
| 7 | B — ripiego del provider vocale | ❌ **NON VERIFICATO dal vivo**: la chiave Deepgram è valida, nessun ripiego. Provato nei test |
| 8 | C — consolidamento saltato | ✅ in laboratorio, come `caduto` (T2 assente); `quota` **NON VERIFICATO** dal vivo: `max_t2_spawns_per_hour` ha `ge=1` |
| 9 | D — T1 degradato | ❌ **NON VERIFICATO dal vivo**. Provato nei test del supervisore |

### ❌ NON verificato, dichiarato

- **La pronuncia.** Il resoconto è stato scritto e mandato alla voce; che gli
  orari «22:58» si sentano bene dal TTS nessuno l'ha ascoltato.
- **`microfono_caduto`, `mcp`, `resoconto` caduto** dal vivo.
- **La scrivania vera.** Il giro ha usato una scrivania finta che manda lo
  stesso `client.ruolo` di `app/main.js`; la finestra Electron non è stata
  aperta, e il pannello del diario resta una coda viva: mostra la frase di
  adesso, non i guasti di ieri.
- **Il modello Vosk assente** uccide il core in `_gradi()`: fuori portata del
  resoconto, resta `jarvis doctor`.
- **Un guasto che persiste** — l'auth scaduta da tre giorni — si dice una
  volta sola, per disegno: lo stato è del doctor e della voce di T1.
