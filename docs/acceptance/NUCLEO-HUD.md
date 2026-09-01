# Il nucleo rifatto sul riferimento HUD — deroghe, misure, costo del ritorno

**Data:** 1° settembre 2026 · **Rollback:** `18b2e58` (più il `git stash` del turno precedente)
**Forma:** `CANCELLO-25.5.md` e `CANCELLO-10.6.md`

---

## Che cosa è successo

Il proprietario ha portato un riferimento HUD proprio, con l'analisi forense
della sua geometria — otto sistemi concentrici, palette a otto livelli,
coreografia a cinque velocità, tutto misurato su 1024×1024 — e ha chiesto di
**rimuovere il nucleo esistente e sostituirlo**, dichiarando che dove il
riferimento e la specifica sono in contrasto vince il riferimento.

Quattro decisioni, prese esplicitamente prima di costruire:

| | |
|---|---|
| **ambito** | il **solo nucleo**. Scrivania, 19 pannelli, catalogo, finestre e core Python non si toccano. Niente React, niente Vite, niente Tauri |
| **posto e scala** | stessa dimensione e stessa posizione di prima, **Ø326**, dietro i pannelli e coperto da loro |
| **bagliore** | il riferimento vince: glow acceso, con esenzione **nominata** e **contata** |
| **lavoro precedente** | messo in `git stash`, non distrutto |

---

## L'adattamento obbligato

Il riferimento è disegnato per riempire 1024×1024; il nucleo vive in Ø326. La
scala è **0,3184**, e a quella scala i valori presi alla lettera diventano:

```
testo 11 px del riferimento    ->  3,5 px      illeggibile
mirino L1 r=13                 ->  4,1 px      invisibile
waveform 120 barre             ->  0,35 px/barra
```

**La regola, applicata ovunque:** i **raggi** si conservano come rapporti; le
**densità** si dimensionano in unità di viewBox perché cadano sui gradini veri
alla resa reale (`ui/src/hud/tipografia.js`).

Misurato: 40,2 unità di viewBox × 0,2113 = **8,50 px esatti** a schermo, cioè
`--t-micro`. A Ø326 la corona esadecimale porta **133 caratteri**; a Ø440 ne
porta 179, e il testo resta 8,5 px in entrambi i casi.

⚠️ **L'audit non sapeva misurarlo.** `getComputedStyle` su un `<text>` SVG
riporta il font-size in unità utente e le chiama `px`: il nucleo dichiarava
40,2 e l'audit lo bocciava come «non è un gradino `--t-*`». Non si è esentato —
si è insegnato all'audit a convertire e a confrontare il valore **reso**. Il
presidio resta, e adesso è giusto per ogni futuro testo dentro un viewBox.

⚠️ E la prima stesura di quella correzione **bocciava 79 elementi**: applicavo
il fattore a ogni nodo dentro l'SVG, anche a `path` e `g`, che ereditano un
corpo ma non disegnano testo. Un audit che boccia tutto è inutile quanto uno
che non boccia niente.

---

## Le cinque deroghe

### 1 · invariante 19 — zero glow, zero bloom

`feGaussianBlur` sull'anello hero L3 e su ogni strato acceso.

**Costo del ritorno:** si toglie `montaGlow()` da `ui/src/hud/strati.js` e i due
`setAttribute("filter", …)`.

⚠️ **Il pericolo non era il bagliore: era che l'audit non lo vede.**
`gallery/audit.js` controlla la proprietà CSS `filter`; `filter="url(#…)"` è un
attributo SVG e `getComputedStyle` risponde `none`. Una deroga invisibile allo
strumento che la dovrebbe contare non è una deroga, è un buco. Perciò:

- il bagliore vive in **una funzione, un id, un file**;
- `tests/test_nucleo.py::TestIlBagliore` conta i file che montano un
  `feGaussianBlur` e pretende che sia **uno solo**;
- `contaGlow()` espone il numero di elementi che brillano.

⚠️ **Sul MARCHIO il bagliore è stato tolto, e non per scelta di stile.** Il
riferimento lo prescrive; montato, `verifica:marchio` ha smesso di poter
misurare. Il criterio §25.13.5 separa l'inchiostro dallo scudo confrontando due
scatti — col nome e senza — e chiama «tratto» i pixel che si **schiariscono**.
Un bagliore schiarisce anche l'intorno: `pixelTratto` va a zero e il criterio
non ha più niente su cui misurare. Non è una regola derogabile a parole: è il
**metodo di misura** che non regge più. Fra un bagliore sul nome e la sola
guardia che lo tiene leggibile in tutti gli stati, resta la guardia.

### 2 · §25.11 — «niente three.js per il nucleo»

La sfera olografica L5: 720 punti su spirale aurea, reticolo di 6 meridiani e
7 paralleli in `Line2`, rotazione a 41 s, nutazione ±8° a 0,05 Hz, parallasse
col puntatore, punti che si gonfiano con la voce.

**Il retro attenuato è tutto l'effetto.** Il riferimento lo misura al 30-35 %:
i punti sulla faccia lontana restano visibili ma spenti, ed è quello — non i
punti in sé — a far leggere l'oggetto come una sfera TRASPARENTE invece che
come un disco di puntini.

Si calcola in JS con `vertexColors`, non in uno shader: è la strada che il
progetto ha già preso due volte (`panels/globe.js`, `panels/source.js`), e un
`ShaderMaterial` sarebbe un terzo modo di dire la stessa cosa con del GLSL da
mantenere e un colore da passare comunque come uniform per non violare
l'invariante 18. ⚠️ L'attenuazione usa la sola rotazione attorno a Y e non la
matrice completa: la nutazione inclina di ±8°, e su una rampa di luminosità
quella differenza non si vede. **Approssimazione dichiarata.**

⚠️ Il reticolo NON usa `materialiPerRuolo`: quel richiamo dà al ruolo
«costruzione» il colore `--cy-900`, che è anche il colore del corpo del disco —
reso, il reticolo non si vedeva affatto. Il materiale si costruisce con il
gradino sopra, e resta un `LineMaterial` (invariante 21) con un colore da
`tok()` (invariante 18, che in WebGL è la più facile da violare senza
accorgersene).

**Costo, misurato** — `npm run verifica:scrivania`, undici pannelli aperti:

```
tutto aperto, nessun filtro          mediana 16,7 ms · p95 16,9 · max 17,0
con il filtro 03 acceso              mediana 16,7 ms · p95 16,9 · max 17,7
col nucleo in moto, carico massimo   mediana 16,7 ms · p95 16,9 · max 17,0
```

16,7 ms è il vsync a 60 Hz: la sfera, i cinque anelli e l'onda insieme **non
tolgono un fotogramma**. Il tetto di 8 ms che l'invariante 26 dà a three.js
regge con margine, e regge perché la sfera è **un draw call** per la nuvola e
uno per il reticolo — 720 punti non costano più di 72.

**Costo del ritorno:** si cancellano `ui/src/hud/globo.js` e
`ui/src/three/math/globo-wireframe.js`, e si tolgono cinque righe da
`desk/sfondo.js`.

### 3 · invariante 25 e §10.3 — «Fondo: immobile»

Cinque velocità continue e indipendenti. `CANCELLO-10.6.md` chiama §10.3
*«l'unica riga del progetto che non è mai stata violata»*: da oggi non lo è più.

**Che cosa si perde.** Il moto non è più un segnale: prima «se gira, sta
lavorando» si leggeva da tre metri.
**Che cosa resta.** Il segnale si è spostato sull'**accensione**, che §25.5 già
governava: *se è ACCESO, sta lavorando*. Ogni strato ha la propria causa, ogni
causa è un fatto sul bus, e si accende uno per volta.

⚠️ **Il riferimento aveva il difetto dentro.** Le sue cinque velocità — 6, 12,
−8, ±20, −3 °/s — danno 60/30 = 2,000 e 120/60 = 2,000: due rapporti interi su
dieci coppie, che §10.3 vieta perché producono un riallineamento a cadenza
fissa. Lo scostamento è stato **cercato**, non scelto: fra tutte le combinazioni
a ±0,6 °/s, quella di costo minimo che tiene ogni rapporto ad almeno 0,1 da un
intero costa **0,4 °/s in tutto**, su due anelli, e lascia gli altri tre ai
valori esatti del riferimento.

```
mirino      6,0 -> 5,7 °/s     63,2 s
segmentato 12,0 -> 12,0        30,0 s   invariato
quadranti  -8,0 -> -8,0        45,0 s   invariato
vetro      20,0 -> 20,0        18,0 s   invariato
tecnico    -3,0 -> -3,1       116,1 s
```

Rapporto più vicino a un intero: **1,839** (margine 0,161), contro lo 0,065 che
il nucleo precedente accettava. Un test lo conta.

**Il prezzo, misurato.** `npm run verifica:densita`:

```
deroga     2 452 pixel (100 % del moto) sono il nucleo, che gira per deroga
§5.4       soddisfatto: fuori dalle zone dichiarate non si muove niente
```

⚠️ `scripts/densita.mjs` è stato generalizzato alla formula che
`CANCELLO-10.6.md` chiedeva — `ambiente = diversi − Σ per[zone dichiarate]` —
perché il testo precedente avrebbe stampato «§5.4 NON soddisfatto» per sempre.
Quel documento lo prevedeva parola per parola: *«oggi quella riga dice il falso
in un caso su uno»*, e un rosso che non si può spegnere prima o poi si toglie.

**Costo del ritorno:** si passa `autoplay: false` in `ui/src/hud/moto.js`.

### 4 · §10.6 — la classe 2 fuori da un pannello

L'onda vocale sta nel fondo. Le tre condizioni restano, e due sono imposte dal
codice: `SILENZIO_MS = 900` spegne il componente entro il secondo (condizione
a), e l'etichetta col picco sta nel DOM in `--font-mono` (condizione b).

### 5 · §25.5 — il tetto del nucleo

`--cy-200` (L 213) sui picchi dell'onda e sull'anello hero, sopra il tetto
`--cy-500` (L 181). Il vincolo che §25.5 difende regge: `--cy-100` (L 231, il
testo dei pannelli) resta vietato, e un test lo conta.

---

## Che cosa NON è derogato, e la prova

### Invariante 18 — zero letterali

La palette misurata è entrata in `tokens.css` **e** in SPEC §10.1, byte a byte
identici. Cinque degli otto livelli erano già nella rampa; tre no:

```
#003B52   L  48,1   == --cy-900 (48,5)                      si riusa
#205463   L  74,0   buco fra 900 e 700    ->  --cy-800
#2F6575   L  90,7   == --cy-700 (99,6)                      si riusa
#5A9AAB   L 141,6   buco fra 700 e 500    ->  --cy-600
#77C3D5   L 180,1   == --cy-500 (181,4)                     si riusa
#94E5F4   L 212,9   buco fra 300 e 200    ->  --cy-200
#FF2D2D   L  89,6   == --rust, stesso ruolo                 si riusa
```

⚠️ **E uno dei tre ha risolto un criterio.** §25.13.5 chiede al marchio fra 3,0
e 5,0 contro il composito. Misurato:

```
--cy-700  L  99,6   2,73:1   sotto il pavimento — non si legge
--cy-500  L 181,4   7,99:1   oltre il tetto — compete col dato
--cy-600  L 141,6   4,65:1   dentro la forbice
```

Fra `--cy-700` e `--cy-500` non c'era niente. La forbice si è chiusa con un
colore del riferimento, non con una deroga — ed è la ragione per cui quei tre
gradini valevano la misura. §25.13.5: **SODDISFATTO in tutti e nove gli stati**,
4,48–4,65:1, franco +4 px.

### Invariante 23 — dati veri

Il riferimento chiede `TARGET: MARK XL ARMOR`, `APOGEE: 420.5 KM`. Non ce n'è
nessuno.

| dove | che cosa | sorgente |
|---|---|---|
| lettura alta | `AGENTE` `FASE` `MESH` | `agent.mesh`, `state.snapshot` |
| lettura bassa | `CPU` `RAM` `TEMP` `VOCE` | `telemetry` 2,5 Hz, `voice.spettro` |
| corona L8 | la stessa terna in base 16 | `telemetry` |

L'esadecimale **non è un travestimento**, ed è verificabile sullo stesso scatto:
con CPU 12,4 · RAM 38,1 · TEMP 54,0 la corona porta `007C 017D 021C 000001`, e
`0x7C = 124`. Dove non c'è sorgente c'è uno stato vuoto che lo **dice**.

### Invariante 22 — geometria parametrica

`HudQuadrante` estende `ParametricComponent`, deriva la densità da
`segmentsFor()` **per ogni cerchio** — non dal raggio massimo dello strato —
dichiara `constructionLines()` e passa `qualityGate()` prima del render. Sette
configurazioni, tutte al gate.

⚠️ `tests/eval_visual.py` confrontava il NUMERO di casi col numero di classi:
sei configurazioni di una classe sola lo facevano fallire, pur essendo copertura
migliore. Adesso confronta le **classi**, che è la proprietà vera.

### Invariante 9 — anime.js, niente GSAP

`seek(0)` e `utils.set` verificati sul bundle vendorizzato, non dedotti.

### I due moti che il riferimento descrive, e che ora ci sono

**Lo scorrimento di L8.** Il riferimento è esplicito — «i caratteri scorrono,
l'anello è fermo» — e la differenza si vede: un anello che gira porta con sé
anche le tacche, e allora è una sesta rotazione invece di una riga che scorre.
Si anima `startOffset` del `textPath`, verificato sul bundle anime.js v4.5.0 e
non dedotto: una sonda ha letto `startOffset = "25%"` dopo l'animazione.

⚠️ **Si scorre di UN SOLO BLOCCO, e il testo è più lungo del tracciato.** Un
`textPath` non si avvolge: ciò che esce dalla fine sparisce invece di
ricomparire dall'inizio, e scorrere di un giro intero lascerebbe un vuoto che
avanza. Riempiendo oltre la capienza e fermando la corsa a un blocco,
l'immagine finale è identica a quella iniziale e la giuntura non si vede.

Misurato: l'offset passa da −0,67 % a −2,92 % in 6 s. Su ~133 caratteri fanno
**0,5 caratteri al secondo**, cioè `scorrimentoCarS` dichiarato.

**La lancetta di L6.** Scatta con `easeOutExpo` — «arrivo secco e assestamento,
tipico ui militare» — a intervalli fra 4 e 7 s. È un EVENTO ripetuto e non un
moto: si programma con un timer, perché una lancetta che si muove sempre non
sta cercando niente. Classe 1 di §10.6, la sola che sarebbe stata legale anche
senza la deroga 3.

⚠️ **Né l'angolo né l'intervallo vengono da `Math.random()`**, e non è
pedanteria:

1. §11.7 vuole catture ripetibili. `fissa()` azzera le rotazioni perché due
   scatti di due stati diversi differiscano per lo STATO e non per l'angolo —
   misurato, il 43 % dei pixel. Una lancetta sorteggiata rimetterebbe dentro
   proprio quella differenza;
2. §11.6 regola 6: «il varco nell'anello è un parametro con un nome, non
   `Math.random()`». Parla di geometria, ma la ragione vale qui — due valori
   sorteggiati sembrano rumore, due scelti sembrano una decisione.

L'angolo aureo dà entrambe le cose: una successione che non si ripete mai, ben
distribuita, e sempre la stessa a ogni avvio. Misurato: primo scatto a
**137,5°**, l'angolo aureo esatto; dopo `fissa()`, 0°.

⚠️ La lancetta **non è un `ParametricComponent`**, ed è una scelta con una
ragione. §11.10 governa le GEOMETRIE: forme generate, con densità derivata
dalla curvatura e bounding box da verificare. Una lancetta è due vertici e un
triangolo, senza curvatura da discretizzare — e il gate lo dice da sé: il suo
pavimento è 24 vertici, e un componente che non può passarlo per costruzione
non è un componente. I raggi vengono comunque dalla tabella, non da numeri
battuti a mano.

### Le quattro icone cardinali, e perché DICONO qualcosa

Nel riferimento sono chrome: un chip, un triangolo di avviso, un satellite, un
distintivo, messi ai punti cardinali perché riempiono. §25.11 su questo è netto
— *«il nucleo non è il posto dove mettere ciò che non sta nei pannelli»* — e
quattro forme che non significano niente sono esattamente ciò che quella riga
vieta.

Costano poco a rendere vere. Ognuna prende un fatto che il bus già porta:

| icona | dove | si accende quando |
|---|---|---|
| chip | alto | `agent.mesh`: un nodo T1, T2 o subagent sta lavorando |
| avviso | dx-basso | `agent.advisory`, o livello sopra soglia §16 |
| satellite | sx-basso | il core risponde sul socket |
| badge | sx | `voce.abilitata`: il microfono è aperto |

Misurato in galleria, cambiando un fatto per volta:

```
fixture (t1 attivo, core vivo, voce spenta)   agente ✓  avviso ✗  collegato ✓  voce ✗
dopo voce accesa                              agente ✓  avviso ✗  collegato ✓  voce ✓
dopo livello warn, t1 spento                  agente ✗  avviso ✓  collegato ✓  voce ✓
```

Ognuna cambia solo quando cambia il **proprio** fatto: è la proprietà che le
rende indicatori invece che ornamento.

⚠️ Sono **attributi**, non animazioni, e la differenza è voluta: un simbolo o
c'è o non c'è, e farlo dissolvere direbbe che il fatto è vero a metà. Gli anelli
si accendono con una rampa perché sono superfici e la rampa dice «sta
cominciando»; un'icona no.

⚠️ Il `satellite` è stato **ridisegnato dopo lo scatto**: la prima stesura aveva
corpo, due pannelli e due archi in venticinque unità, e a schermo era un grumo
di rettangoli. Un'icona a questa scala regge tre tratti, non sette.

⚠️ E il `chip` **spariva sotto la lettura in alto**: quel blocco era ancorato al
bordo di L7 (351 unità) e cresceva verso l'alto per la propria altezza,
arrivando a 433 — dentro l'anello delle icone, che sta a 422. Ancorato a L6 si
ferma a 383, un'unità sotto la guida interna. Il numero non è scelto: è dove
finisce la fascia.

### ⚠️ Il globo rendeva §25.13.5 NON MISURABILE, e l'ha nascosto per due giri

Il criterio confronta due `capturePage()` a 120 ms — uno col marchio e uno senza
— e chiama «tratto» i pixel che si schiariscono di più di 8 livelli. Fra le due
catture il ciclo del globo è fermo (lo ferma `fissa()`), ma **la tela WebGL non
ridisegna**, e quello che il compositore le legge dentro può differire di
qualche livello sui bordi antialiasati del reticolo — sopra la soglia.

Misurato: l'inchiostro del marchio risultava a **r 57 px invece che a 17**, e il
franco andava a **−36**. Peggio: il criterio è diventato **instabile** — stesse
sorgenti, stessa impronta, e due esiti diversi in due giri. Un criterio che
risponde a caso non è un criterio.

Il globo **non** si esclude dalla misura: sta sotto il nome, e il composito è
quello che c'è davvero. Si rende identico nei due fotogrammi — `rendiGlobo()`
prima di ognuna delle due catture. Verificato su due giri consecutivi: franco
+4 px, inchiostro a r 17, soddisfatto in tutti gli stati, due volte uguale.

`creaScena` ha guadagnato anche `preservaBuffer`, che **non basta da solo** ma è
la metà giusta del problema: è dichiarato per il solo nucleo, perché costa un
secondo buffer per contesto e lo chiede chi finisce dentro una misura fatta di
fotografie.

### La macchina a stati — una VISTA, non una seconda verita'

Il riferimento nomina cinque stati e li fa arrivare dal backend come
`{"type":"state","value":...}`. Prenderli cosi' avrebbe voluto dire **un topic
nuovo che dichiara uno stato che il core non ha**: il core dice fatti — quali
nodi sono attivi, se la voce e' abilitata, che livello ha la telemetria — e lo
stato e' una loro combinazione. Due sorgenti per la stessa cosa sono due
sorgenti che prima o poi divergono.

I cinque nomi si **derivano** da `attivo`, che e' gia' l'unico posto dove quei
fatti vivono. Tre presidi tengono in piedi la derivazione:

* nessun topic dichiara lo stato (`test_lo_stato_si_DERIVA_e_non_arriva_da_un_topic`);
* **un solo posto scrive `data-hud`** — `applicaHud()`, e un test conta gli
  scrittori in tutto `ui/src/`;
* l'ordine e' una **priorita'** e non un elenco.

L'ordine conta davvero: mentre JARVIS parla c'e' quasi sempre anche un T1
attivo — sta finendo di generare la frase che si sta ascoltando — e dire
«thinking» in quel momento sarebbe vero e inutile. `error` vince su tutto
perche' e' l'unico stato in cui il resto non conta.

⚠️ **«Voce spenta» NON e' un errore.** `voice.enabled = false` e' la
configurazione di partenza, non un guasto: confonderli farebbe lampeggiare in
rosso un'installazione appena fatta. Un test lo verifica.

Ogni stato muove **una cosa diversa**, non lo stesso elemento con un colore
diverso — e' la riga che il riferimento pone: «il cambio di stato deve essere
riconoscibile dalla grafica senza leggere testo».

| stato | che cosa cambia |
|---|---|
| `idle` | la coreografia di base. Nessuna regola sua: e' l'assenza degli altri quattro, e una regola per il riposo direbbe che il riposo e' acceso |
| `listening` | il cerchio del logo si accende, e gli anelli **seguono la voce**: ×(1+2A) |
| `thinking` | L8 scorre **×4**. E' la cosa piu' periferica, e «sta elaborando» non deve rubare il centro |
| `speaking` | il bagliore dell'anello hero al massimo, e l'onda al centro |
| `error` | l'anello esterno e l'icona d'avviso passano a `--rust` |

Misurato in galleria, cambiando un fatto per volta:

```
fixture (t1 attivo)     thinking   anelli x1,00   scroll x4
t1 spento               idle       anelli x1,00   scroll x1
voce accesa             listening  anelli x1,00   scroll x1
spettro MIC picco 0,8   listening  anelli x2,60   scroll x1
spettro TTS picco 0,9   speaking   anelli x2,80   scroll x1
livello critical        error      anelli x1,00   scroll x1
```

⚠️ Due difetti trovati proprio da questa misura:

1. **lo stato non si rivalutava sul TTS**: `applicaHud()` veniva chiamato PRIMA
   che `attivo.parla` fosse scritto, e derivare da cause non aggiornate da' lo
   stato di un istante fa. Il nucleo restava in «listening» mentre parlava;
2. **l'accelerazione non seguiva l'ampiezza**: cambio di stato e ampiezza erano
   trattati insieme, e `applicaHud()` usciva subito se lo stato non cambiava.
   In `listening` gli anelli restavano a ×1 per tutto l'ascolto. Sono due
   domande diverse e vanno fatte in due momenti diversi.

⚠️ Il marchio **non** cambia colore con lo stato, ed e' deliberato: §25.13.5
misura il contrasto fra il colore DICHIARATO del nome e il composito, e
cambiarlo per stato renderebbe quel criterio dipendente dallo stato. Il nome
resta il nome; e' il nucleo attorno a dirlo.

### Il contratto causale, misurato

`npm run verifica:scrivania` — la dottrina di §25.6 che la deroga NON tocca:

```
aRiposo            []            nessuno strato acceso senza causa
t1                 ["t1"]        ogni causa accende il PROPRIO strato
ascolto            ["ascolto"]
t2                 ["t2"]
subagent           ["subagent"]
t0                 []            impulso, non stato — §25.6 alla lettera
finestreDiRiposo   [0, 0]        le animazioni di stato si esauriscono
```

⚠️ `finestreDiRiposo` ha detto `[60, 60]` finché il respiro di L2 chiamava il
contatore dei fotogrammi. Quel contatore serve a **una** domanda — «c'è
un'animazione di STATO che non finisce?» — ed è la sola cosa che resta
verificabile dopo la deroga 3. Contarci dentro un moto continuo fa sì che il
numero non torni mai a zero, e il contatore smette di poter rispondere. Il
costo della rotazione si misura dove appartiene: `motoOra` e `globoOra`.

### Il ciclo §11.7 — e il nucleo che nessuno auditava

⚠️ `desk/sfondo.js` **non aveva un mount di galleria**: l'oggetto più grande
dello schermo era l'unico fuori dall'audit dei token. Adesso c'è:

```
nucleo         0 calcolate ·  0 sorgente
non-conforme   4 calcolate · 23 sorgente
```

La seconda riga è ciò che dà significato alla prima.

---

## Sei difetti trovati GUARDANDO, non leggendo

| # | che cosa si vedeva | che cos'era |
|---|---|---|
| 1 | un disco di ciano piatto | le tracce concentriche ereditavano il riempimento della fascia: un cerchio chiuso riempito è un disco. Serviva un **ruolo** separato |
| 2 | il nome illeggibile sull'anello luminoso | lo dimensionavo al 31 % del disco da una lettura a occhio; il **profilo radiale misurato** dice che L2 è il «text circle» al 13 % |
| 3 | la corona esadecimale che galleggia | il corpo del disco si fermava a L6: nel riferimento arriva fin sotto il testo |
| 4 | le letture sopra il quadrante | ancorate a una frazione di L6 invece che al bordo di L7 |
| 5 | contrasto del marchio fuori forbice, in **tre** direzioni | tre misure per trovare il gradino giusto |
| 6 | l'onda accendeva 6 strati su 7 | il globo non aveva geometria SVG: era una **circonferenza nuda**, e non poteva accendersi |

E **cinque backtick** dentro template literal CSS. Il presidio che doveva
prenderli non guardava il file: la sua regex ammetteva **un solo addendo**, e il
nucleo ne compone tre. Era verde per assenza del fenomeno. Corretto, più un
secondo test che conta i file scoperti — che ha subito trovato
`ui/src/gallery/mounts/chrome.js`, fuori copertura da sempre.

---

## Che cosa resta aperto, dichiarato

1. ⚠️ **L'entropia è SOTTO SOGLIA: 2,37 contro 2,40.** Misurata tre volte
   mentre aggiungevo contenuto — 2,34 → 2,36 → 2,37 — sale ma non arriva. Il
   nucleo è il 7 % del pavimento e l'entropia è una misura globale.
   **Non l'ho inseguita oltre**: alzare le superfici oltre ciò che il
   riferimento mostra sarebbe ottimizzare la metrica contro il disegno, ed è il
   difetto che `PIANO-FUI-ESITO.md` ha già documentato tre volte — *«le
   superfici chiare vogliono stati, e a scrivania ferma gli stati non
   accadono»*. La soglia 2,40 era tarata sul nucleo precedente.
   **`NON SODDISFATTO` non è `PASS`.**
2. ⚠️ **Il confronto per sovrapposizione col riferimento NON è stato
   eseguito**: il file dell'immagine non è sul disco. Il cancello di F1 —
   «raggi entro ±2 unità su viewBox 1024» — resta **non misurato**.
3. ⚠️ **L'onda vocale è verificata SOLO nello stato vuoto.** `voice.enabled` è
   `false` e accendere un microfono è una decisione del proprietario. Le
   condizioni (a) e (c) di §10.6 con una sorgente viva sono **NON VERIFICATE**.
   Il costo della FFT invece è misurato: **0,252 ms per blocco, 0,42 % di un
   core** a 16,7 Hz — la sonda che `PIANO-FUI-ESITO.md` chiedeva.
4. **Del riferimento non resta fuori niente** di quanto il blueprint
   descrive: geometria, palette, coreografia, globo, onda, icone, scorrimento,
   lancetta e macchina a stati sono tutti costruiti.
5. ⚠️ **Non è però una replica pixel per pixel, e non può esserlo.** Il
   riferimento è un fotogramma 1024×1024 in cui l'HUD riempie il quadro; il
   nucleo vive in Ø326 dietro i pannelli, per decisione esplicita del
   proprietario. Due differenze restano e sono strutturali: la **densità di
   micro-testo** delle corone esterne — il riferimento ne ha più bande, qui ce
   n'è una — e il fatto che il disco occupi metà del quadro invece che tutto.
   La prima si può colmare; la seconda no, senza cambiare la decisione sulla
   scala.
6. ⚠️ **§25.13.5 resta NON soddisfatto nello stato `onda`**: luminanza media
   110,1 contro il tetto di 105. È l'inviluppo sintetico con tutti e otto gli
   strati accesi insieme, che l'onda vera non produce mai; gli otto stati che
   accadono davvero stanno fra 88 e 98,7, e il contrasto regge ovunque
   (4,26–4,91, franco +7 px). Vedi la deroga 6.
7. **Il diametro non è quello di §25.7**: deroga già dichiarata il 23 agosto
   2026 in `NUCLEO-TURNO-3.md`, confermata dalla decisione di tenere il nucleo
   alla dimensione di prima.
