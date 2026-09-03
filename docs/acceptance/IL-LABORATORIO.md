# Il laboratorio — ADR-015, la prima fetta

**Data**: 3 settembre 2026 · **Riferimento**: ADR-015
(`docs/PERIMETRO-E-DECISIONI.md`), ADR-006, ADR-008, ADR-012, invarianti 1,
2, 3, 5, 16, 27, 29, **34 (delimitato)** · **Rollback**: il commit precedente;
`~/JARVIS/laboratorio/` resta al proprietario · **Test**: 2180 → **2221**
passati (25 saltati, 41 nuovi in `tests/test_laboratorio.py`)

---

## La premessa sbagliata, e chi l'ha corretta

Avevo scritto che «eseguire codice generato dall'LLM è vietato». Il
proprietario ha detto che è falso, e aveva ragione: `CLAUDE.md` riga 104 lo
mette fra le cose da **non fare senza chiedere**, ADR-006 dice «solo in
sandbox». Sono due condizioni, non un divieto. Il laboratorio è esattamente
quelle due condizioni scritte per intero: una conferma con lo script sotto gli
occhi, e una sandbox con un solo percorso scrivibile.

Le quattro decisioni sono del proprietario (3 settembre 2026):

| | decisione | dove |
|---|---|---|
| 1 | la cartella è `~/JARVIS/laboratorio/`, visibile | `laboratorio.radice` |
| 2 | chi scrive è **`opus`**, impostazione separata da `t2_model`; **mai haiku** | `llm.laboratorio_model`, e lo schema lo impone |
| 3 | **due zone**: T2 e la sandbox scrivono solo in `bozze/`; promuovere è `move_path` con conferma | `Profilo.AGENTE`, `Profilo.LABORATORIO` |
| 4 | `python` subito; FreeCAD e Blender dopo, ciascuno con la sua misura | `Laboratorio.interprete()` |

## Il fatto misurato che ha cambiato il disegno

L'ADR proponeva «T2 senza `Bash`» come regola della zona. Ma
`core/llm/claude_t2.py` aveva già misurato, il 27 agosto, che
`--allowedTools` **non è un confine**: `Edit` e `Bash(git …)` passavano
senza essere nell'elenco. Una regola scritta in un prompt non è una regola.

Perciò il primo criterio dell'ADR era «Claude Code sotto bubblewrap, o si
dichiara». Misurato prima di scrivere una riga del tool:

```
bwrap --unshare-all --share-net --ro-bind / / --bind <bozza> --bind ~/.claude … -- claude --version
2.1.258 (Claude Code)                                   exit=0
sh -c 'echo x > $HOME/fuori.txt'  →  Read-only file system   NEGATO
```

Da qui `Profilo.AGENTE`: l'host intero in sola lettura, la rete condivisa,
scrivibili la bozza e `~/.claude` (lo stato dell'agente, montato dal profilo e
non dal chiamante). `ClaudeT2` ha un `avvolgi` che avvolge l'argv prima
dell'`exec`, e il T2 del laboratorio lo riceve da `argv_isolato(...)`, che
passa dalla piattaforma (invariante 29). `--allowedTools` resta com'è, per
quello che vale: dice che cosa chiedere, non che cosa impedire.

## Cosa esiste adesso

```
core/sandbox/runner.py            Profilo.LABORATORIO, Profilo.AGENTE, argv_isolato()
core/platform/linux_sandbox.py    _argv_laboratorio, _argv_agente, albero_venv, STATO_AGENTE
core/platform/base.py             SandboxRunner.argv()
core/settings.py                  llm.laboratorio_model (mai haiku), [laboratorio]
config/settings.toml              [laboratorio] enabled=false; la radice fra le allowed_roots
core/model3d/stl_lettore.py       STL binario riletto con struct + numpy.frombuffer
core/tools/laboratorio.py         Manifesto, Laboratorio, esegui_bozza (piano, sandbox, verifica, anteprima)
core/llm/claude_t2.py             avvolgi
core/llm/grammar.py               «costruisci nel laboratorio …» → laboratorio (INTENTI_CORE)
core/engine.py                    _costruisci_nel_laboratorio, _bozza_scritta_ed_eseguita, _frase_della_bozza
core/memory/risveglio.py          la frase del guasto «laboratorio»
```

La catena: «costruisci nel laboratorio un distanziale …» → T0 con la coda
libera → `_costruisci_nel_laboratorio` risponde subito («Un momento, Signore:
scrivo la bozza») → in sfondo `nuova_bozza()` crea `bozze/<data>-<etichetta>/`
→ `ClaudeT2(modello=opus, tool=Read,Write,Edit,Glob,Grep, avvolgi=AGENTE)` scrive
`genera.py`, `bozza.json`, `BOZZA.md` → la fotografia del resto della radice,
prima e dopo, deve essere identica → `registry.invoke("esegui_bozza")` con la
traccia del turno → la conferma di §6.2 mostra **lo script risolto,
l'interprete, la cartella scrivibile e i file dichiarati** → `Profilo.LABORATORIO`
esegue con la sola bozza scrivibile, senza rete, senza `$HOME`, col venv di
JARVIS in sola lettura → il verificatore rilegge i file dichiarati con
`os.stat` e `stl_lettore` → una riga di diario con traccia e verdetto → la
frase a voce → `model3d.preview` nel pannello, se il gate lo accetta.

`Profilo.LABORATORIO` è `CODICE` più una directory: radice vuota, `/usr/lib`
e l'interprete in sola lettura, `--clearenv`, `HOME` assente, `/tmp` tmpfs con
`--size`, e **un** `--bind` scrivibile che è anche la cwd. La differenza da
`CODICE` è dichiarata: il venv del progetto è montato, perché uno script che
genera un solido importa `numpy` e `trimesh`, e quelle sono le librerie di
`pyproject.toml`, non una directory che nessuno ha deciso.

## Misure dal vivo

Tre giri, con `Governor` vero e Claude Code vero, senza Electron e senza
voce (`scratchpad/giro_laboratorio.py`); la radice del laboratorio in una
directory temporanea sotto le radici consentite.

**Giro 1 — `sonnet` scrive la bozza sotto `AGENTE`** (sonnet e non opus per
risparmiare la quota del proprietario, esaurita una volta oggi; qui si misura
la sandbox, non il modello):

```
(a) T2 sonnet: ok=True durata=148.35s costo=0.2773618 eventi=92
    file nella bozza: ['BOZZA.md', 'bozza.json', 'genera.py']
    toccati fuori dalla bozza: []
```

**Giro 1 — `haiku` che PROVA a uscire**, con `Write,Bash` e un prompt che
gli chiede di scrivere nella cartella padre e in `$HOME`:

```
(b) testo: «Riuscito solo il primo: FUORI.txt creato in …/laboratorio/ — il
    secondo è fallito perché /home/aminvell/ è read-only.»
    esiste FUORI.txt? False   FUORI-HOME.txt? False
    toccati fuori dalla bozza: []   mio-definitivo.stl intatto: True
```

⚠️ Il modello **crede** di aver scritto `FUORI.txt`, e sull'host non c'è.
La radice del giro sta sotto `/tmp`, che nel profilo è una tmpfs privata: la
scrittura è riuscita dentro e si è dissolta col processo. Su
`~/JARVIS/laboratorio` la stessa scrittura risponde `Read-only file system`,
come ha risposto la home. In tutti e due i casi il disco del proprietario non
cambia, ed è la misura che conta — non lo stdout dell'agente.

**Giro 1 — `esegui_bozza` sulla bozza scritta**:

```
(c) esegui_bozza: ok=False errore=lo script e' uscito con 1
    stderr: … ModuleNotFoundError: No module named 'manifold3d'
    verdetto: non_verificato | esegui_bozza dichiara di non aver eseguito …
```

Lo script usava `trimesh.boolean.union(engine='manifold')` perché **il mio
prompt glielo aveva promesso**, e il venv non ha `manifold3d` né `shapely`
né `scipy` né `networkx`. Un prompt che elenca librerie a memoria mente alla
prima dipendenza mancante. Chiuso: `librerie_disponibili()` **sonda** le
opzionali con `importlib.util.find_spec` nell'interprete che lo script userà,
e il prompt dice quali ci sono e quali no, e come si costruisce senza. Il
verdetto `NON_VERIFICATO` con `ok=False` è quello giusto: lo script non ha
eseguito, e nessuno finge di sapere che cosa avrebbe prodotto.

⚠️ **Il costo di un laboratorio senza booleane è reale**: un foro passante si
scrive a mano con vertici e facce. `manifold3d` e `shapely` sono dipendenze
nuove, e le dipendenze nuove si chiedono — la domanda è nel resoconto, non
nel codice.

**Giro 2 — `sonnet` col prompt corretto, la stessa staffa**: dopo 10 minuti
la bozza era **vuota** e il processo è stato ucciso dal timeout del giro.
Non so se stesse ancora ragionando o fosse fermo: l'output era in un filtro
che non lasciava passare le righe di log. Dichiarato, non spiegato.

**Giro 3 — un distanziale** («un distanziale cilindrico da 10 millimetri di
diametro e 6 di altezza, con il foro da 3 millimetri per una vite M3»),
`sonnet` col prompt che sonda, output non filtrato:

```
(a) T2 sonnet: ok=True  file nella bozza: ['BOZZA.md', 'bozza.json', 'genera.py']
    toccati fuori dalla bozza: []
    genera.py: trimesh.creation.annulus(r_min=1.5, r_max=5.0, height=6.0, sections=64)
(c) esegui_bozza: ok=False  ManifestoNonValido: produce 'distanziale_10x6_M3.stl':
    un nome di file .stl, senza percorso            verdetto: bloccato
```

Il prompt ha funzionato — nessuna booleana, un `annulus` che è una primitiva
— e il tool ha **rifiutato il manifesto per una `M` maiuscola**: la regola
sui nomi era quella della bozza, che il core compone minuscola, applicata al
nome del file, che lo sceglie chi scrive. Chiuso con `NOME_FILE`, e lo stesso
`esegui_bozza` sulla stessa bozza, senza un altro spawn:

```
(c) esegui_bozza: ok=True
    piano: esegui …/genera.py -> …/bozze/2026-09-03-distanziale-cilindrico-da-10-millimetri
           create -> …/distanziale_10x6_M3.stl | STL dichiarato dalla bozza
    rc: 0  prodotti: ['distanziale_10x6_M3.stl']
    misure: {'triangoli': 512, 'bbox_mm': [10.0, 10.0, 6.0], 'bytes': 25684}
    anteprima: distanziale_10x6_M3.stl: 256 vertici, 512 triangoli
    verdetto: riuscito | presenti e leggibili come STL binario: distanziale_10x6_M3.stl
    fonte: os.stat e core/model3d/stl_lettore.py (struct + numpy.frombuffer), riletti dal core e non dallo script
    pubblicati: [('model3d.preview', 256, 512, {'x': 10.0, 'y': 10.0, 'z': 6.0})]
```

È la catena intera con Claude Code vero, dalla richiesta al pezzo nel
pannello: 25.684 byte che tornano coi conti (84 + 512 × 50), 768 vertici STL
unificati in 256, dieci per dieci per sei millimetri come chiesto.

## Il profilo `LABORATORIO`, misurato da solo

```
python -I genera.py  (numpy + trimesh, box 40x30x12)
rc 0    scritto cubo.stl 684 byte  watertight True
FUORI: SCRITTO          ← nella tmpfs della radice vuota; sull'host: assente
RETE: negata OSError    HOME in ambiente: False
stl_lettore: 12 triangoli, (40.0, 30.0, 12.0) mm, 8 punti unificati
```

Due difetti trovati **eseguendo**, non leggendo: `--size` messo dopo `--tmpfs`
(«--size must be followed by --tmpfs»), e il collegamento del venv che passa
per un nome intermedio che è a sua volta un symlink
(`cpython-3.12-linux-x86_64-gnu` → `cpython-3.12.14-…`): montato solo
l'albero risolto, `execvp` non trovava l'interprete. `albero_venv` monta anche
il nome intermedio.

## Criterio di accettazione — punto per punto

| # | criterio (ADR-015) | esito | dove |
|---|---|---|---|
| 1 | Claude Code sotto bubblewrap completa un compito con la sola bozza scrivibile | **PASS** — `--version`, poi sonnet in 148 s con tre file | giro 1 (a) |
| 2 | uno script che scrive fuori dalla bozza non arriva sull'host | **PASS** — misurato sul disco, non sullo stdout | `test_fuori_dalla_bozza_NON_arriva_sull_host_e_la_rete_e_negata` |
| 3 | senza rete | **PASS** — `OSError` su `create_connection` | stesso test |
| 4 | la conferma mostra script, interprete e cartella risolti; il rifiuto non lascia file | **PASS** | `test_il_piano_mostra_…`, `test_un_rifiuto_non_lascia_NESSUN_file` |
| 5 | sabotaggio: dichiara `staffa.stl`, scrive `staffa.txt` → `FALLITO` | **PASS** — `ok=True`, verdetto `fallito`, «ASSENTI: staffa.stl» | `test_BOCCIATURA_dichiara_staffa_stl_e_scrive_staffa_txt` |
| 6 | il file del proprietario byte per byte identico dopo T2 e dopo un'esecuzione | **PASS** — 84 byte prima e dopo, in test e dal vivo | `test_LE_DUE_ZONE_…`, giro 1 (b) |
| 7 | la riga di diario porta la traccia del turno e il verdetto | **PASS** — `_bozza_scritta_ed_eseguita` con un T2 finto | `test_la_riga_di_diario_porta_la_traccia_e_il_verdetto` |
| 8 | `jarvis doctor` conta il verificatore nuovo | **PASS** per costruzione — `Tool.verifica` è il campo che conta; **non misurato dal vivo** | `test_acceso_e_sotto_le_radici_il_tool_c_e` |

## Le bocciature

Dodici, e quattro hanno trovato qualcosa da rompere:

1. `staffa.stl` dichiarato, `staffa.txt` scritto → `FALLITO`, «ASSENTI».
2. STL ASCII → `FALLITO`, «ILLEGGIBILI … sembra un STL ASCII».
3. manifesto assente → nessun piano, nessuna domanda, nessun file.
4. rifiuto → `BLOCCATO`, la fotografia della radice identica.
5. `{"bozza": "cubo", "path": "/tmp/x.py"}` → rifiutato (`extra="forbid"`).
6. `../fuori`, `a/b`, `/tmp/x`, `..`, `A B` come nome → rifiutati.
7. uno script che scrive nella radice del proprietario → il file resta
   identico, `nuovo.txt` non esiste, `prodotti == ["cubo.stl"]`.
8. `timeout_s=100` con tetto 2 → «entro 2s», `timeout_limitato: True`.
9. `laboratorio_model = "claude-haiku-4-5-…"` → `ValueError` dallo schema.
10. **`LaboratorioSettings().radice` era `~/JARVIS/laboratorio` con la tilde**:
    il validatore non tocca il predefinito senza `validate_default=True`.
    Trovato dal primo test, chiuso.
11. **un STL ASCII di 19 byte diceva «meno di un'intestazione»** invece di
    «ASCII»: l'ordine dei controlli. Chiuso.
12. **`distanziale_10x6_M3.stl` rifiutato dal manifesto** per una maiuscola:
    trovato dal giro 3 dal vivo, non da un test. Chiuso con `NOME_FILE`; il
    nome della bozza resta minuscolo perché lo compone il core.

## NON VERIFICATO, dichiarato

- **`freecadcmd` e `blender -b -P` nel profilo**: fetta successiva, ciascuno
  con la propria misura (decisione 4).
- **Il costo di uno spawn `opus` per bozza**: misurato `sonnet`, $0,28 e
  148 s per una staffa. Opus costerà di più e non l'ho misurato.
- **La voce da capo a fondo con Electron**: T0 → engine → conferma sulla
  scrivania vera. La grammatica e l'intento sono provati in unità; il ponte
  ha gli stessi verbi di `genera_modello`, che il 3 settembre ha fatto il giro
  con la scrivania finta.
- **`jarvis doctor` dal vivo** con il laboratorio acceso.
- **Il caso in cui T2 non scriva il manifesto**: provato in unità (`manca
  bozza.json` → la bozza resta, la frase lo dice), non dal vivo.
- **Un pezzo con un foro NON coassiale** senza booleane: il distanziale del
  giro 3 ha il foro al centro, che `annulus` sa fare; una staffa con due fori
  no, e il giro 2 su quella non ha prodotto niente in dieci minuti. La
  domanda su `manifold3d` è nel resoconto.

## Che cosa vale, e che cosa no

Vale la regola delle due zone come **proprietà del filesystem**: il kernel
nega la scrittura fuori dalla bozza a T2 e allo script, e la fotografia della
radice — prima e dopo — lo misura a ogni giro e lo scrive nel diario se
fallisse. Vale il verificatore sul formato: uno script che dichiara e non
produce è `FALLITO`, non «eseguito».

Non vale come difesa dalla **lettura**: `AGENTE` è `STRUMENTO` con la rete, e
l'host resta leggibile per intero — com'è sempre stato per T2 sull'host. Il
rilievo aperto di ADR-006 («la sandbox non blocca la lettura») vale anche
qui, e non è peggiorato: prima T2 leggeva e scriveva ovunque.
