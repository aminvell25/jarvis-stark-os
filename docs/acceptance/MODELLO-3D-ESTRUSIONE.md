# Il pilastro 3D — `estrusione_45`, la prima fetta

**Data**: 3 settembre 2026 · **Riferimento**: ADR-014
(`docs/PERIMETRO-E-DECISIONI.md`), `docs/SPEC.md` §17.1-17.4, invarianti 1, 3,
22 (emendato), 23, 27, **34** (nuovo) · **Rollback**: il commit precedente;
`trimesh` e `numpy` escono da `pyproject.toml`, §17.1-17.3 tornano proposte ·
**Test**: 2125 → **2166** passati (2199 raccolti, 25 saltati, 41 nuovi)

---

## Il difetto, contato prima di scrivere

`core/tools/model3d.py` era **0 byte dal 18 agosto**. `CLAUDE.md` prometteva
«genera modelli 3D» in prima pagina; `docs/SPEC.md` §17 erano **65 righe** —
non «trenta pagine», come due documenti di piano ripetevano — e saltavano dal
titolo a §17.4: **§17.1, 17.2 e 17.3 non sono mai esistite**. Nessun `.py`
nominava `model3d`. Tre `.js` del pilastro erano a zero byte.

Due fatti misurati prima di disegnare, ed entrambi hanno cambiato il piano di
§17.4: **T2 non attraversa il registro dei tool**, e il ponte in salita ha
sette verbi fissati con un divieto scritto di aggiungerne uno generico. Perciò
la geometria va nel core e la strada è T0, non «via T2» — che non esiste.

## Le tre decisioni, approvate dal proprietario

### ① `trimesh`, senza `pygltflib`

`trimesh 5.1.0` (MIT, puro Python) scrive il GLB e conferma la topologia;
`numpy` passa da dipendenza per caso — trascinata da mediapipe — a dichiarata.
**`pygltflib` non entra**, ed è la scelta che rende forte il verificatore: il
GLB si rilegge con `struct` e `json` della libreria standard, quindi la fonte
di ADR-012 è **il formato**, non una seconda libreria che sa di glTF.
`trimesh` non è un secondo motore 3D: non apre un contesto GL, non ha una
scena, non vive nel renderer.

### ② Millimetri ovunque, metri nel file

glTF 2.0 prescrive i metri e un visualizzatore esterno deve vedere il pezzo
grande quanto è. La conversione ×0,001 sta in **una funzione sola**,
`_scrivi_glb`; i parametri in millimetri viaggiano in `asset.extras`, dove si
leggono e **non si credono** — il verificatore usa i `min`/`max`
dell'accessor, che non passano da lì.

### ③ La geometria vive nel core

Il renderer riceve `model3d.preview` e **mostra**. Zero modifiche al ponte in
ingresso, una sola implementazione di ogni generatore, e il file come verità.
Costo dichiarato: quando arriverà il tubo (fetta 2), `segmentsFor()` avrà un
gemello Python da inchiodare con un test cross-language.

## Che cosa è `estrusione_45`, e perché per primo

Non il tubo, e le tre ragioni sono del **verificatore** più che della forma:

| | |
|---|---|
| bbox | **analitico** dai parametri: gli smussi tagliano verso l'interno e non spostano gli estremi. §11.10 regola 7 diventa un'uguaglianza, non un «entro il 2 %» |
| topologia | `is_watertight` **e** `euler_number == 0` — 32 vertici, 96 spigoli, 64 triangoli, genere 1. Le risponde `trimesh`, non il nostro codice |
| conteggi | **chiusi**: 32 e 64 sempre. Il verificatore li ricava dagli argomenti |

Sagoma rettangolare con **quattro smussi a 45° di misura diversa** (§11.10
regola 4, imposta: quattro smussi uguali sono un rifiuto con la ragione) e
foro passante anch'esso smussato.

---

## Verifica

### ✅ Dalla frase al file, dal vivo

Core vero, socket vero, una scrivania finta che risponde alla conferma come
`app/main.js`:

```
FRASE     "genera un'estrusione"
T0        genera_modello {'forma': 'estrusione_45'}
CONFERMA  genera un solido «estrusione_45» e lo scrive
          create  /home/…/jarvis-os/workspace/modelli/estrusione_45-20260903-000715.glb
          120x80x12 mm, 32 vertici, 64 triangoli, GLB
          risposto: approva
ESITO     ok=True verdetto=riuscito
OSSERVATO …estrusione_45-20260903-000715.glb e' un GLB 2 coerente, 32 vertici, 120x80x12 mm
PREVIEW   estrusione-45 v1 · 32 vert · 64 tri · {'x': 120.0, 'y': 80.0, 'z': 12.0} mm
```

Il file sul disco, **2172 byte**, e una terza fonte che non è né il tool né il
verificatore — `libmagic` di sistema:

```
estrusione_45-20260903-000715.glb: glTF binary model, version 2, length 2172 bytes
```

Riletto con la sola libreria standard: 32 vertici, 119,999997 × 79,999998 ×
12,0 mm (l'errore è del `float32` diviso per mille, tre ordini di grandezza
sotto la tolleranza di 0,01 mm), extras `estrusione-45` in mm.

Il diario, due righe con la traccia del turno:

```
00:07:16   ok  genera_modello   via tool        riuscito
00:07:16   ok  genera_modello   via tool     {'forma': 'estrusione_45'}   riuscito
```

### ✅ Il rifiuto non lascia niente

```
CONFERMA  genera un solido «estrusione_45» e lo scrive
          risposto: rifiuta
ESITO     ok=False verdetto=bloccato operazione rifiutato
file dopo il rifiuto: 1   (lo stesso di prima)
```

⚠️ Al primo tentativo la scrivania finta mandava `{"ok": …}` invece di
`{"approvato": …}` e la conferma **scadeva**: `ConfirmResponse` ha
`extra="forbid"`, e il messaggio storto non è entrato. Era il mio arnese a
sbagliare, e la severità del ponte ha fatto esattamente il suo mestiere.

### ✅ Il verificatore boccia

Tre sabotaggi in `tests/test_model3d.py`, ciascuno con un rosso:

| sabotaggio | verdetto |
|---|---|
| il file troncato dopo la scrittura | `FALLITO` — «non si puo' rileggere» |
| un pezzo di misura diversa scritto al suo posto | `FALLITO` — «200x80x12» |
| il tool non esegue (nome occupato) | `NON_VERIFICATO`, non `FALLITO` |

E la `fonte` non nomina il proprio tool — «intestazione GLB letta con struct e
accessor POSITION del chunk JSON, sul percorso risolto del piano» — quindi
`registry._verifica` non la declassa. Un test AST impone che `glb_lettore`
**non importi** `trimesh` né `numpy`.

### ✅ Il gate, in Node e senza WebGL

`ModelloRicevuto` passa `qualityGate()` con 32 vertici, 192 indici, 48
spigoli e il bbox 120×80×12 **dichiarato dal core**. È in
`tests/eval_visual.py`, che deriva la copertura dalle classi che estendono
`ParametricComponent`: un componente nuovo non può restare fuori.

### ✅ Il ciclo §11.7, e i quattro difetti che solo lo scatto ha mostrato

`npm run shot -- modello` — audit **0 elementi fuori sistema, 0 regole con
letterali**, font tutti caricati. Guardando `shots/modello.png`:

1. **Il pezzo usciva dal riquadro.** `inquadra()` calcolava la distanza
   sull'ingombro **frontale** (120×80) mentre il gruppo era già ruotato: la
   diagonale di un solido girato è più larga della sua faccia. Non era un
   margine da alzare, era l'ingombro sbagliato. Adesso si inquadra su vertici
   già ruotati.
2. **Gli spigoli sparivano.** Erano di ruolo `costruzione` — `--cy-900` a
   mezzo pixel, il grigio degli assi — sopra una faccia `--fill-2`, e il pezzo
   era una silhouette piatta. Sono il **pezzo**, non un aiuto al disegno:
   ruolo `linea`.
3. **Il percorso nel piede diventava «…glb./=»**: con `direction: rtl` la
   punteggiatura si riordina. Adesso il piede mostra le ultime due parti e il
   percorso risolto sta nell'attributo `title`.
4. **Le quote stavano sugli angoli** invece che a metà degli spigoli, dove si
   scrivono in un disegno tecnico, e senza fondo sparivano sopra la faccia.

### ✅ Due difetti trovati dai presìdi che c'erano già

- **`eval_tools`**: `genera_modello({"path": "/tmp/x.glb"})` **riusciva**.
  Pydantic scarta in silenzio i campi che non conosce, e il file finiva
  comunque nella workspace — quindi non era una falla, era peggio in un modo
  sottile: chi aveva chiesto quel percorso riceveva `ok=True`. Per un tool la
  cui intera storia di sicurezza è «non esiste un argomento path», accettarlo
  e ignorarlo è la risposta sbagliata. `extra="forbid"`, e gli altri schemi di
  `core/tools/` non ce l'hanno.
- **`scripts/orfani.py`**: `Modello.bbox_combacia` era «provata, mai
  congiunta». Il posto in cui serviva era la **costruzione**: un modello che
  dichiara un bbox diverso dai propri vertici mente su sé stesso, e il
  verificatore userebbe quel numero come atteso.

⚠️ **E il backtick nel foglio di stile è successo due volte nello stesso
file.** Un backtick dentro il template literal del CSS lo chiude e il modulo
non si carica. La guardia `tests/test_fogli_di_stile.py` l'ha preso entrambe;
la seconda volta l'ho scoperto perché avevo lanciato lo scatto prima del test.

### ✅ Le misure

```
uv run pytest -q -p no:cacheprovider     → 2166 passati, 25 saltati (2199 raccolti)
npm run shot -- modello                  → audit pulito, font tutti caricati
npm run verifica:densita                 → CONFORME, entropia 2,55, impronta rinfrescata
uv run python scripts/orfani.py          → 5 sospetti, nessuno nuovo
jarvis doctor (verificatori)             → 4/26, distruttivi coperti 4/10 (erano 3/25 e 3/9)
```

La densità è stata **rimisurata**, non dedotta: toccare `ui/src` cambia
l'impronta dei sorgenti, e il presidio lo dice.

### Criterio / Esito, punto per punto

| # | criterio (ADR-014) | esito |
|---|---|---|
| 1 | conferma col percorso assoluto sotto `fs.workspace/modelli/`; rifiuto → `BLOCCATO`, nessun file | ✅ dal vivo, sopra |
| 2 | approvazione → file su disco, `RIUSCITO` nel diario con la traccia | ✅ due righe citate |
| 3 | sabotaggio: file troncato → `FALLITO` | ✅ e un secondo sabotaggio, il pezzo sbagliato |
| 4 | la `fonte` non nomina il tool | ✅ test |
| 5 | `glb_lettore` non importa `trimesh` | ✅ test AST |
| 6 | il buffer ricevuto passa il gate, e il gate spara se si altera | ✅ `eval_visual`, tre guasti |
| 7 | scatto di galleria con la checklist §11.8 | ✅ e quattro difetti corretti |
| 8 | `jarvis doctor`: da 3/25 a 4/26 | ✅ |

### ❌ NON verificato, dichiarato

- **Il GLB in un visualizzatore esterno o in `gltf-validator`.** Non sono nel
  repo. Ciò che si sa: `libmagic` lo riconosce come glTF binary v2, e
  l'intestazione e l'accessor POSITION tornano. La conformità glTF **oltre**
  quei due punti non è misurata.
- **Il budget di frame dell'invariante 26 sulla scrivania piena**, col nucleo
  Aurora in moto e il pannello aperto. In galleria il pannello rende a
  richiesta e non entra in `npm run scrivania`, perché è `suRichiesta`: la
  misura vera vuole un giro con il pannello aperto sulla scrivania, e non è
  stata fatta.
- **La finestra Electron vera**: il giro ha usato una scrivania finta che
  manda lo stesso `client.ruolo` e la stessa `fs.confirm_response` di
  `app/main.js`. La conferma disegnata da `ui/src/windows/confirm.js` non è
  stata guardata per questo tool.
- **Il pannello che si apre da solo** al primo `model3d.preview`: la riga c'è
  in `desk/scrivania.js` accanto a quella delle gesture, e dal vivo non è
  stata osservata.
