# Fase 2 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 2
**Test**: 151 verdi (erano 135) · **Precedente**: `FASE-01b.md`

È la prima fase in cui JARVIS può fare danni. Tutto ciò che è stato costruito
prima — allowlist, socket con autorizzazione del kernel, isolamento — esisteva
in previsione di questo momento.

---

## I criteri di §22

### 1. «Nessun path fuori radice passa, nemmeno con `../`» — ✅ VERIFICATO

`tests/eval_paths.py`: **un corpus di 20 casi**, non tre esempi. Ogni voce
dichiara l'esito atteso e il perché.

Coperti: `..` singolo, ripetuto, in mezzo al percorso, e **dopo un segmento
inesistente** (verificato: `resolve()` risolve lessicalmente ciò che non
esiste, e `radice/nonesiste/../../esterna` cade fuori); symlink verso
l'esterno; symlink **a metà percorso**, che un controllo lessicale non vede;
percorsi assoluti; `~root/.ssh/id_rsa`; stringa vuota; byte NUL; un prefisso
che somiglia alla radice (`consentita-altro` **non** è sotto `consentita`).

**Il corpus è stato messo alla prova rompendo l'implementazione**, perché un
corpus che passa anche col codice rotto non misura nulla:

| Guasto introdotto | Esito |
|---|---|
| confronto per stringa invece che per componenti | 1 caso fallisce |
| controllo **prima** di `resolve()` | 3 test falliscono |
| radici non risolte (il difetto di §6.1) | il test dedicato fallisce |

### 2. «I tre casi Stonic, con una conferma per operazione» — ✅ / ⚠️ PARZIALE PER DEFINIZIONE

§2.3 li chiama «suite di accettazione della **v1**», non della Fase 2.

| Caso | Stato |
|---|---|
| *organizza Downloads per tipo* | ✅ **questa fase** |
| *cosa sta rallentando il PC* | ✅ già dalla Fase 1 (`top_processes`) |
| *apri YouTube e riproduci* | ⛔ **Fase 6** — `<webview>`, fuori ambito |

**Caso 1, su alberi sintetici**: 8 file in 7 cartelle, **una sola conferma**,
tutti spostati. Su rifiuto, nulla accade.

**Caso 1, sui Suoi file, in sola proposta**: su `~/Scaricati` il piano propone
**26 spostamenti in 5 cartelle** — mostrato per intero e **nessun file
toccato**. La prova a vuoto non è una simulazione a parte: è lo stesso
`planner` che l'esecuzione userebbe, chiamato senza la parte che esegue.

### 3. Il giro completo, attraverso il socket vero — ✅ VERIFICATO

`tests/test_confirm_e2e.py` avvia l'engine, apre un client sul socket UNIX
come farà Electron, e misura:

- l'approvazione esegue, e il file **si ritrova nel cestino**
- il rifiuto non esegue, e il file resta
- il percorso mostrato è **risolto**: `radice/sotto/../vero.txt` arriva come
  `radice/vero.txt` (§6.2)
- **una sola conferma per cinque spostamenti**
- una risposta con un **id inventato** non sblocca nulla
- quattro messaggi malformati di fila non fermano il canale

---

## Revisione di sicurezza

La skill `security-review` presuppone un remote `origin` che questo repository
non ha. Ho fatto la revisione a mano, in modo avversariale sul codice appena
scritto. **Tre falle trovate, tutte riprodotte prima di essere corrette**, e
tutte ora bloccate da un test.

### ① `copy_path` importava contenuti da fuori le radici — *fuga di informazioni*

`shutil.copytree` col default `symlinks=False` **dereferenzia** i symlink
dentro l'albero. Una cartella contenente un link a `/etc/hostname`, copiata,
produceva un **file vero** con quel contenuto, materializzato dentro una radice
consentita.

La validazione dei percorsi non la intercetta: il percorso copiato è
legittimo, è il *contenuto* ad arrivare da fuori. Corretto con `symlinks=True`.

### ② `read_file` caricava il file intero prima di tagliarlo

`read_bytes()[:n]` legge tutto e poi affetta: il tetto di 1 MiB non proteggeva
da nulla, e un file da qualche gigabyte fermava il core mentre lo ingoiava.
Corretto leggendo solo `max_bytes`.

### ③ Fra la conferma e l'esecuzione passano fino a due minuti

Il piano congelato protegge dal *ricalcolo* degli argomenti, ma non dal mondo
che cambia sotto. Ho aggiunto un ricontrollo immediatamente prima di agire: se
un percorso approvato non punta più dove puntava, l'operazione si ferma.

**Non chiude del tutto la finestra** — fra la verifica e la chiamata di sistema
resta un istante — ma la riduce da minuti a microsecondi, e soprattutto rende
esplicito che la finestra esiste.

### Un sospetto smentito

Temevo che `search_files` potesse uscire dalle radici attraverso una directory
symlink. **Misurato: `rglob` non attraversa i symlink di directory** in Python
3.12. Verificarlo mi ha risparmiato una correzione inutile.

---

## Scoperte durante l'implementazione

**La documentazione di Send2Trash raccomanda di violare l'invariante 4.**
Consultata via Context7 come impone il `CLAUDE.md`. La sua pagina sugli errori
propone una catena di ripiego che finisce in `os.remove(path)` —
cancellazione permanente. `trash_path` **non ha ripiego**: se il cestino non è
disponibile, l'operazione fallisce e lo dice. È esattamente il caso per cui la
regola «consulta la documentazione, non scrivere a memoria» esiste, e qui la
documentazione conteneva una trappola.

**`recuperabile: True` era un'affermazione non verificata.** La prima versione
rispondeva così senza guardare. Un file su un filesystem diverso dalla home non
va nel cestino della home ma in `.Trash-<uid>` sul mount di origine, e la
risposta era falsa. Ora si **cerca** dove è finito e si riporta il percorso —
o `verificato: false`.

**E cercarlo per nome era sbagliato.** Alla collisione la specifica XDG
rinomina inserendo un numero **prima** dell'estensione: `nota.txt` diventa
`nota 2.txt`. Si legge il registro `.trashinfo`, che conserva il percorso
originale. **E `Path=` non è sempre assoluto**: in un cestino per-mount è
relativo al punto di mount — misurato, `/tmp/x/f.txt` viene registrato come
`x/f.txt`. Sono due dettagli che si vedono solo alla seconda cancellazione e
sul secondo filesystem.

**Il doppio dei test non seguiva il Protocol.** `Paths` è cresciuto e
`FakePaths` no: il fallimento è comparso a valle, dentro un tool, come
`AttributeError`. Ho aggiunto un test che fa comparire la deriva dove si
capisce cos'è successo.

**Il divieto `rm -rf` dei Suoi permessi ha fermato me.** Volevo ripulire
`/tmp/.Trash-1000` durante una diagnosi. `.claude/settings.json` lo nega, e ha
funzionato: ho ripulito solo i residui firmati dai miei test, leggendone il
registro. I test ora si puliscono da soli — zero residui dopo tre esecuzioni.

---

## Le tre garanzie strutturali

Nessuna dipende dalla disciplina di chi scriverà il prossimo tool:

| Garanzia | Dove è imposta |
|---|---|
| un tool distruttivo **non si registra** senza un piano da mostrare | `registry.register()` |
| senza meccanismo di conferma collegato, i tool distruttivi **non girano** (fail-closed) | `registry.invoke()` |
| `side_effect` ⇒ mai `gesture_allowed` (invariante 27) | `registry.register()` |

**12 tool · 6 con conferma obbligatoria · 0 distruttivi attivabili da gesto.**

E in tutto `core/` l'unica occorrenza di `os.remove` è nel commento che spiega
perché non lo facciamo mai.

---

## Scostamenti dalla specifica, dichiarati

| # | Cosa | Decisione |
|---|---|---|
| **R19** | La documentazione di Send2Trash consiglia un ripiego che cancella | Nessun ripiego. L'operazione fallisce |
| **R20** | `_safe()` di §6.1 non risolve le radici, e le cabla come costanti | `core/paths_policy.py` le risolve e le legge dalle impostazioni |
| **R21** | La conferma va legata al piano risolto e congelato | Fatto, più il ricontrollo prima di agire |
| **R22** | Il criterio Stonic cita tre casi, uno solo è di questa fase | Dichiarato sopra |
| **R23** | Il preload guadagna la quarta funzione | Aggiunta, e il test di guardia **aggiornato**, non allentato |
| **R24** | `core/paths_policy.py` e `core/tools/confirm.py` non sono in §21.1 | Aggiunti e dichiarati |

## ❌ NON VERIFICATO

**La finestra di conferma dentro Electron, con un'operazione vera.** Il
componente passa il ciclo §11.7 e il giro completo è verificato **attraverso il
socket vero** da `test_confirm_e2e.py`, che è la prova più forte. Manca il
collegamento in `ui/src/app.js` fra `fs.confirm_request` e la finestra: è
cablaggio, non logica, ed è il primo punto da chiudere.

**La finestra fra ricontrollo e chiamata di sistema**, come sopra. Su un
sistema monoutente il rischio pratico è basso; è registrato perché esiste.

## Riepilogo

| | |
|---|---|
| Test | **151 verdi** (erano 135) |
| Criteri §22 Fase 2 | **2 su 2**, col criterio Stonic parziale per definizione di §2.3 |
| Falle trovate e corrette | **3**, tutte riprodotte prima e bloccate da un test dopo |
| Non verificato | il cablaggio della conferma nel renderer |
