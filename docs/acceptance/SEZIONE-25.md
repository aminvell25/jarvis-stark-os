# §25 — Lo strato di presenza, uscita «il centro libero»

> 22 agosto 2026. Non è una fase di §22: il criterio me lo do io, e §25.9 lo
> dichiara già. Qui c'è che cosa è stato costruito, che cosa è stato misurato,
> e — per intero — che cosa **non** è verificato.

---

## 0. ⚠️ SUPERATO IL 22 AGOSTO 2026 — l'insegna ha preso il posto del nucleo

**Tutto ciò che segue descrive `desk/presenza.js`, che non esiste più.** Il
proprietario ha scelto di sostituirlo con `desk/sfondo.js`, la nuvola di punti
del mockup famiglia-d, sapendo il costo. Il documento resta perché le misure
che contiene sono l'unico posto in cui quella strada è registrata, e perché la
prossima volta che qualcuno si chiede «perché non gli anelli» la risposta deve
essere leggibile e datata.

### Che cosa cambia, misurato nel nostro albero

| | task/fotogramma |
|---|---|
| scrivania sola | 0,15 ms |
| `rings.js` al fondo, fermo | 0,14 ms |
| `rings.js` al fondo, in moto | 1,39 ms |
| `rings.js`, sotto carico | 3,05 ms |
| **`sfondo.js`, a riposo** | **4,49 ms** |
| **`sfondo.js`, sotto carico** | **4,53 ms** |

⚠️ I 4,49 ms non sono i 10,36 misurati sul mockup: **è lo stesso file, misurato
di nuovo nel nostro albero**, e la differenza sta nel contorno — là girava
insieme al resto del mockup. Va scritto perché due numeri diversi per lo stesso
file, senza una riga che dica perché, diventano un'accusa reciproca fra due
misure entrambe corrette.

Il costo dell'insegna è **costante**: non ha uno stato fermo. 4,49 ms sono il
27 % di un fotogramma a 60 Hz, per sempre, contro i 15 ms che l'invariante 26
assegna in tutto a tre motori.

### Le tre deroghe che questa scelta porta con sé

1. **Invariante 25 — animazione senza causa.** La nuvola gira sempre:
   `giro += P.vel * dt` a ogni fotogramma. La velocità è un parametro di stato,
   non un interruttore. `rings.js` invece nasceva in pausa e si muoveva solo
   con un nodo attivo in `agent.mesh`. Il test che lo imponeva è stato
   riscritto: adesso verifica l'unica cosa che resta verificabile — che il
   tasso di traffico non conti la telemetria — e dichiara la deroga invece di
   asserire il falso.
2. **§25.5 — la scala di luminanza.** Misurato sui pixel dell'insegna che
   arrivano a schermo: **massima L 255**, media 36,9; il **15,4 %** dei suoi
   pixel supera L 48 e il **5,0 %** supera L 92. §25.5 li dà come tetti
   assoluti. La causa è la somma additiva più la scritta `J.A.R.V.I.S.`, che è
   `--icona-viva` (L 219).
3. **§25.11 — nessun testo nel nucleo con i pannelli aperti.** La scritta c'è
   sempre, ed è la cosa più chiara della scrivania.

Nessuna delle tre è un difetto di implementazione: sono ciò che la nuvola **è**.
Vanno decise, non corrette di nascosto — o si abbassa la scritta e si taglia
l'ampiezza, o si emenda §25.5 e §25.11 con la ragione scritta accanto.

### Che cosa resta valido di questo documento

Le misure di densità della sezione 6, il difetto di `maximize()` della sezione
5 e la scena `avvio` col centro libero: quella non è cambiata, ed è la ragione
per cui l'insegna adesso **si vede** — 16 286 px sul pavimento libero contro i
122 che l'insegna prendeva sulla scena vecchia.

---

## 1. La decisione, e perché non è quella che §25 aveva scelto

§25 dichiara tre uscite e ne sceglie una: **il vetro**. Densità piena, e il
nucleo si legge attraverso pannelli traslucidi. La sua nota di chiusura
prevede il ripiego: *«si passa all'opzione C — il nucleo nella cella centrale,
circondato dai pannelli come in 10»*.

È quella costruita qui. Il proprietario la chiama «B, il centro libero»; §25 la
chiama «opzione C». **Le lettere non coincidono, la cosa sì** — e §25 va
corretta di conseguenza, perché due nomi per la stessa uscita sono il modo in
cui fra sei mesi si costruisce quella sbagliata.

La ragione del ripiego non è estetica, è una misura: con la scena precedente
uno strato di presenza arrivava a schermo con **122 pixel su 264.049** di
pavimento. Il vetro non è stato provato e non è stato scartato — resta aperto,
e richiede di togliere i tre fondi opachi di §25.4.

---

## 2. La misura che ha riaperto la questione

Il costo di uno strato di presenza non è una proprietà dell'idea: è
dell'implementazione. Misurato col protocollo DevTools
(`Performance.getMetrics`), dieci secondi per riga, stessa scrivania, stesse
fixture, viewport 1536×843:

| | task/fotogramma | script | layout |
|---|---|---|---|
| scrivania sola | **0,15 ms** | 0,04 | 0,03 |
| `rings.js` al fondo, **fermo** | **0,14 ms** | 0,03 | 0,03 |
| `rings.js` al fondo, **in moto** | **1,39 ms** | 0,07 | 0,34 |
| la nuvola di punti del mockup famiglia-d | **10,36 ms** | 2,60 | 0,05 |

**Sette volte e mezzo meno**, e solo mentre il sistema lavora. A riposo il
nucleo costa meno di zero rispetto al rumore: un SVG fermo non si ridipinge, ed
è esattamente la ragione per cui §25.11 prescriveva SVG.

L'intervallo fra fotogrammi non distingue niente — 16,70 ms di mediana in tutti
i casi, perché il vsync assorbe tutto. È `DIVARIO-PREMIUM.md` §12 alla lettera:
il budget di frame misura l'intervallo, non il margine.

---

## 3. Che cosa è stato costruito

| File | Cosa |
|---|---|
| `ui/src/desk/presenza.js` **(nuovo)** | monta `rings.js` **com'è** sullo strato di fondo, ne spoglia la cornice, ne riporta il tratto nella scala di §25.5, e porta lo stato di riposo di §25.7 |
| `ui/src/desk/moduli.js` | la scena `avvio` lascia libera la fascia centrale; `anelli` esce dalla scena perché **è** il nucleo; `alimentaAnelli` diventa pubblica |
| `ui/src/style/app.css` | `--z-presenza: 1` e la regola `#scrivania > .prs` |
| `ui/src/app.js` | montaggio come primo figlio, alimentazione dal bus, ricollocazione dopo la misura di barra e dock |
| `app/main.js` | **massimizza prima di caricare** (vedi §5) |
| `tests/eval_visual.py` | quattro test nuovi di §25.10, e uno riscritto |

Il componente non è stato toccato: `ui/src/anim/rings.js` è identico. §25.6 lo
chiede esplicitamente — *«Non va riscritto. Va spostato di strato»* — e il
tratto si riscrive in uno scope CSS, così lo stesso file continua a rendere
come pannello nella galleria e nel catalogo, con i colori del dato.

---

## 4. I criteri, uno per uno

### ✅ Il nucleo arriva a schermo — **82,5 %**, e la metrica era sbagliata

⚠️ **Correzione alla prima stesura di questo documento.** Avevo riportato
«5,24 % del pavimento, passa di poco». Il numero è giusto, la lettura no: il
5,24 % **non è vicino alla soglia, è vicino al tetto**.

Il nucleo è una forma a TRATTI. Misurato — stesso albero, nucleo scoperto alla
dimensione di lavoro:

```
nucleo scoperto, inchiostro totale   29 957 px
disco Ø502, area geometrica         197 923 px   ->  densita' d'inchiostro 15,1 %
pavimento libero nella scena        471 409 px   ->  tetto sul pavimento     6,36 %
```

Quindi sul pavimento il massimo raggiungibile è il **6,36 %**, e una soglia al
5 % lascia un punto di margine mentre sembra lasciarne cinque. Chi legge
«5,24 % contro 5 %» conclude che c'è spazio per peggiorare: non c'è.

La metrica giusta ha per denominatore il nucleo:

| | px |
|---|---|
| inchiostro del nucleo, scoperto | 29 957 |
| inchiostro del nucleo, nella scena | 24 713 |
| **quanto ne arriva** | **82,5 %** |

Occluso il 17,5 %, ed è la quinta colonna di `telemetria` sul bordo sinistro
del disco, dichiarata in `moduli.js`. §25.9 è stata corretta: soglia **≥ 75 %**
sull'inchiostro del nucleo, non sul pavimento.

### ✅ La scala di luminanza di §25.5

Letto dal DOM vivo, non dalla sorgente: `getComputedStyle(...).stroke` su tutti
i tratti del nucleo restituisce **un solo valore**, `rgb(18, 56, 64)` —
`--cy-900`, L 48, cioè esattamente la soglia. Mai `--cy-500`, mai `--cy-100`.

In riposo compare il secondo valore consentito da §25.7 sull'anello esterno:
`rgb(34, 116, 130)` = `--cy-700`.

⚠️ **La tabella di §25.5 chiama `--cy-700` «L ≤ 92»; misurato in Rec. 709 su
0–255 vale 100.** Il token è quello giusto, l'etichetta della soglia no. Va
corretta in §25.5, non nel codice.

### ✅ La geometria di §25.7

Letta dal DOM: disco **502 px** di lato, centro **(768, 424)**. L'area pannelli
è alta 784 px e larga 1536: 784 × 0,64 = 501,8 e il centro geometrico è
(768, 423). Coincide.

### ✅ Il riposo (`Alt+H`)

Screenshot allegato. I quattro pannelli spariscono, il nucleo resta e cresce a
531 px, e compaiono le tre righe di stato **sotto** il disco: `VOCE SPENTA`,
`00:00:26`, `21 tool in allowlist`. Nessuna sorgente nuova: il riposo si legge
da `scrivania.stato().tuttoNascosto`, che esisteva già.

⚠️ **La geometria del riposo non è quella che §25.7 descrive, e la ragione va
scritta.** §25.7 è stata scritta prima di §26.3: sotto il disco adesso c'è il
**catalogo**, che `Alt+H` non nasconde perché non è un pannello — è l'indice, e
§26.3 dice che un indice che si può seppellire smette di essere un indice. A
quota 0,86 il disco arrivava a y 761 e le tre righe cadevano a y 777..826,
dentro il catalogo che comincia a 640: erano nel DOM, al posto giusto, con il
testo giusto, e non arrivavano a un solo pixel dello scatto.

Adesso in riposo si compone il **blocco** disco + righe e lo si centra nello
spazio sopra il catalogo. Il disco cresce quanto quello spazio consente, non
quanto un numero scritto in un file.

### ✅ Il moto ha una causa

`rings.js` crea le animazioni con `autoplay: false` e `presenza.js` non chiama
mai `play()`: il moto arriva da `aggiorna({attivo})`, cioè da un nodo attivo in
`agent.mesh`. Negli scatti il sistema è inerte e il nucleo è **fermo**. Un test
lo impone sulla sorgente.

### ⚠️ La densità scende di **1,9 punti**, non di 0,7

⚠️ **Seconda correzione alla prima stesura.** Il «prima» che avevo usato era
misurato su una finestra da 800×503 schiacciata dal difetto di `maximize()`:
confrontava due finestre diverse, non due composizioni.

Rifatto con la correzione applicata, stessa finestra 1536×843, stesse fixture,
tre stati:

| | lum | dev | entropia | L>60 | 25–120 |
|---|---|---|---|---|---|
| scena a cinque pannelli, **senza** centro libero | 38,2 | 20,8 | 1,62 | **11,6 %** | 76,5 % |
| centro libero, **senza** nucleo | 34,5 | 20,3 | 1,60 | **9,7 %** | 61,1 % |
| centro libero, **con** nucleo | 34,7 | 20,2 | 1,60 | **9,7 %** | 62,5 % |

Due numeri, e il secondo è quello che conta:

1. **il vuoto costa 1,9 punti** di L>60 (11,6 → 9,7), non 0,7. Il numero
   precedente era gonfiato dal confronto fra finestre diverse.
2. **il nucleo non ne restituisce nemmeno uno** (9,7 → 9,7). E non è un
   difetto: è §25.5 che lo impone. Il tratto del nucleo è capato a `--cy-900`,
   L 48, e la metrica di densità conta i pixel **sopra L 60**. Un nucleo che
   alzasse L>60 dovrebbe essere più chiaro di quanto §25.5 consenta.

   Le due regole sono in tensione diretta, e va scritto: **lo strato di
   presenza non può contribuire alla densità di superficie, per costruzione.**
   Ciò che restituisce si vede nella banda 25–120, che sale di 1,4 punti
   (61,1 → 62,5): il nucleo riempie il registro di mezzo, non quello alto.

§25.9 criterio 3 chiede L>60 ≥ 25 %, e non era raggiunto neanche prima
(11,6 %). Il nucleo non è la causa del divario, ma lo peggiora di 1,9 punti, e
questo è il prezzo dichiarato dell'uscita scelta.

### ✅ Il costo sotto carico — 3,05 ms, sotto il tetto di 8

Lo 0,15 ms di riposo non diceva niente sul momento che conta: il nucleo si
muove **esattamente quando** T1 genera, la mesh cambia e la console scorre.
Misurato con quel carico addosso — mesh con nodi attivi a 2 Hz, advisory sul
bus, telemetria a 2,5 Hz, console aperta e scorrevole, `inMoto: true`
verificato dal DOM:

| | task/fotogramma | script | layout |
|---|---|---|---|
| riposo, nucleo fermo | 0,16 ms | 0,04 | 0,03 |
| **carico, senza nucleo** | 0,71 ms | 0,17 | 0,09 |
| **carico, nucleo in moto** | **3,05 ms** | 0,16 | 0,61 |

Il nucleo sotto carico costa **2,34 ms**, contro gli 1,39 misurati da solo: a
schermo intero si ridipinge mentre anche altro invalida il layout, e il costo
non è additivo. Il totale resta **sotto il tetto di 8 ms**, quindi il nucleo
**non va rallentato né fermato durante T1**.

⚠️ Il margine però è quello: 3,05 su 16,7 ms è il 18 % del fotogramma con
cinque pannelli aperti. Con la scrivania piena — glifi PixiJS, globo three.js e
tavola periodica insieme — la misura va rifatta, e non è stata fatta qui.

### ✅ Non regredisce

```
uv run pytest -q                                536 passed, 20 skipped
uv run pytest tests/eval_*.py tests/*corpus*.py -q     236 passed
node scripts/audit.mjs (tutti i componenti)     0 violazioni
```

⚠️ Con `TMPDIR` lungo quindici test falliscono per il limite di 108 byte di
`sun_path`, non per il codice. Si esegue con un `TMPDIR` corto.

---

## 5. Il difetto trovato per strada, e corretto

`layout.json` registrava `area_larghezza: 800, area_altezza: 503` su una
finestra che negli scatti è larga 1536. Non era un errore del ripristino, come
avevo riportato la prima volta: era che `app/main.js` chiamava `maximize()`
dentro `ready-to-show`, cioè **dopo** che il renderer aveva già composto la
scrivania su una `BrowserWindow` ancora alla dimensione predefinita, 800×600.
Tolti barra e dock: 800×503, il numero esatto nel file.

Poi la finestra si massimizzava e i pannelli restavano dov'erano, tutti nella
metà sinistra. La persistenza riproduceva fedelmente quella composizione
sbagliata a ogni avvio — ed è la vera causa del «quarto destro vuoto al 1 % di
inchiostro» che avevo attribuito prima alla composizione e poi al ripristino.

Corretto: si massimizza **prima** di caricare. Dopo la correzione il file
registra `area 1536 × 783` e i pannelli stanno dove la scena li dichiara.

---

## 6. Che cosa NON è verificato

1. **La mappa per anello di §25.6.** T0 alla ghiera, T1 al 46 s, T2 al 120 s,
   l'ascolto al 74 s: `rings.js` muove i quattro anelli **insieme** su un solo
   `attivo` e non espone una leva per anello. Farlo vorrebbe dire riscrivere il
   componente, che §25.6 vieta. In moto tutti e quattro restano a `--cy-900`:
   il massimo di §25.5 è rispettato, la distinzione per anello non c'è.
2. **«Un solo anello per volta» a L 92** (§25.5). Consegue dal punto 1.
3. **Gli stati diversi da `spento` e `attesa`.** Con `voice.enabled = false` il
   nucleo non entra mai in `ascolto`; `agent.advisory` e i nodi attivi non sono
   stati fotografati.
4. **Il vetro** (§25.9 criterio 2) e i tre `background` opachi di §25.4. Questa
   uscita non li tocca: i pannelli restano opachi, e il nucleo si legge nel
   vuoto, non attraverso.
5. **La persistenza attraverso i workspace** (§25.9 criterio 1). ADR-010 ha
   tolto i workspace: il criterio è scritto per un ambiente che non esiste più.
6. **Il budget per sottosistema** (§25.8). Ho misurato il tempo di task del
   thread principale, non tre budget separati: la misura dice quanto costa il
   nucleo in totale, non come si ripartisce.
7. **Risoluzioni diverse da 1536×843.** `DIVARIO-PREMIUM.md` §10, aperto da
   prima di questo documento.
8. **La differenza fra il banco e la finestra vera.** Le misure di pixel e di
   costo vengono dal banco Playwright, che è riproducibile; lo scatto
   `shots/scrivania/scrivania.png` viene da Electron. Le due vie rasterizzano
   il testo in modo diverso — misurato in
   `MOCKUP-SCRIVANIA-VIVA.md` §1, 622 px di differenza sul solo antialiasing.
