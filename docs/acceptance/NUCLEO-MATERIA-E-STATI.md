> ## 🔴 STORICO — il nucleo che questo documento misura NON ESISTE PIÙ
>
> Il 2 settembre 2026 il nucleo è stato rifatto sul riferimento «Aurora»: otto
> stati, tre gusci deformati da rumore FBM, catena di post-processing. Tutto
> quello che sta qui sotto — geometria, strati, criteri, numeri — misura un
> oggetto **cancellato**. Il codice sta in git e si recupera con un checkout.
>
> **Lo stato corrente è in `docs/acceptance/NUCLEO-AURORA.md`.**
>
> ⚠️ Questo documento **non si cancella** e non è un rifiuto: è il registro di
> ciò che è stato misurato e perché, ed è citato da 1 altri file. La
> «definizione di fatto» di CLAUDE.md poggia su questi referti. Serve però il
> cartello: fra il 24 e il 30 agosto un documento di stato ha detto il falso su
> cinque voci su cinque, **ed è stato creduto** — e la cura non è cancellare, è
> dire da quando una cosa non vale più.

# Il nucleo: materia invece di wireframe, e gli stati su anime.js

> Richiesta del proprietario, 23 agosto 2026: *«gli dai personalità e movenza
> dei cerchi che si mettono in moto, non voglio l'effetto wireframe, guarda
> attentamente il png presente già nelle reference, e usa per le animazioni
> degli stati anime.js»*.
>
> Il nucleo resta quello: stessa geometria, stesse cause di §25.6. Cambia di che
> cosa è fatto e come si muove.

---

## Il riferimento, misurato — non descritto

`docs/design-reference/famiglia-a/12-logo-anelli-concentrici.png`, 296×296,
centro (147,4 · 147,7), disco di raggio 120. Profilo radiale, normalizzato:

| r/R | media L | max L | rgb medio |
|---|---|---|---|
| 0,125–0,475 | **43,3** | 254 | `rgb(20, 42, 49)` |
| 0,483–0,742 | **116** | 247 | `rgb(134,192,207)` / `rgb(60,125,145)` |
| 0,750–0,875 | **45,2** | 243 | `rgb(19, 43, 51)` |
| 0,883–0,983 | **91,6** | 249 | `rgb(58,104,115)` |

**Il riferimento è fatto di superfici, non di contorni**: fasce piene scure con
il dettaglio chiaro sopra. E la sua palette cade quasi esattamente sulla nostra:
`rgb(20,42,49)` ≈ `--cy-900` (L 48,5), `rgb(60,125,145)` ≈ `--cy-700` (L 99,6).

Il nostro nucleo era **tutto a L 48,5, solo tratti, nessun riempimento**. Da lì
l'effetto wireframe: non è una questione di stile, è che mancava la materia.

---

## ① La fascia si riempie

`ReactorRing` produce già **un contorno chiuso** — arco esterno, raccordo
radiale, arco interno a ritroso, `Z` — perché il varco abbia due spallette
nette. Riempirlo non aggiunge geometria: **l'invariante 22 non è toccato**, e
non c'è una riga di forma scritta a mano.

```css
.sfd .pnl-anelli__linea { stroke: var(--cy-900); fill: var(--bg-panel); }
```

`--bg-panel` vale L 30,7 e `rgb(19,33,42)`: è il token più vicino al campo scuro
misurato, e sta sotto il tetto di §25.5 come ci sta il tratto. Le tacche restano
a `--cy-900` e adesso si vedono, perché hanno una superficie più scura sotto —
che è esattamente la struttura del riferimento.

## ② Lo strato acceso è una seconda copia, non un cambio di colore

§25.5 ammette un anello a `--cy-700`, **uno solo per volta**. Passare dal riposo
all'acceso è quindi una transizione di *colore*, e un colore non si anima bene:
`color-mix` dentro una `stroke` non è interpolabile, e animare un token
vorrebbe dire scrivere un secondo valore accanto a quello di `tokens.css`.

Due copie sovrapposte, la seconda a opacità zero, riducono la transizione a
**una opacità** — che anime.js interpola nativamente, che l'audit non vede come
un valore fuori dai token, e che lascia **ogni proprietà a un padrone solo**:

| nodo | proprietà | padrone |
|---|---|---|
| `posto[data-anello]` | `opacity` | la fase |
| `ruota` | `rotate` | la rotazione |
| `acceso` | `opacity` | l'accensione e il guscio |

Costa il doppio dei nodi di tracciato, che sono geometria statica: memoria, non
lavoro per fotogramma.

## ③ Un anello non parte alla sua velocità: ci arriva

È la metà di ciò che il movimento deve dire. Un anello che passa da fermo a
46 s/giro in un fotogramma **non si vede partire** — si vede solo che a un certo
punto stava già girando, e l'informazione «adesso questo sta lavorando» si perde
proprio nell'istante in cui nasce.

`animation.speed` di anime.js v4 governa la rampa — **verificato sul bundle
v4.5.0, non dedotto**: è scrivibile, il valore di riposo è 1. Avvio 900 ms in
`out(2)`, arresto 1400 ms in `inOut(2)`: si frena più lentamente di quanto si
accelera, come si ferma una massa che gira.

## ④ Il guscio è uno `stagger`, non una gaussiana per fotogramma

La stesura precedente valutava una gaussiana sul raggio di ogni anello a ogni
fotogramma, dentro un `requestAnimationFrame` scritto a mano. Faceva la stessa
cosa e **violava l'invariante 9 nella sostanza**: due motori di animazione, uno
dei quali dentro questo file.

Adesso è `animate(dalMozzo, { opacity: [0,1,0], delay: stagger(ONDA_MS/5) })`.
L'ordine dei bersagli è dal mozzo al bordo, perché la direzione dice da dove
viene la cosa — dal centro, dove sta il core. E accende **un anello per volta**,
che è il tetto di §25.5 letto anche sul numero di anelli accesi insieme.

⚠️ `onComplete` rimette a 1 gli anelli che stavano girando: **il guscio passa
sopra lo stato, non al posto suo**. Senza quella riga un'onda spegnerebbe
l'anello che sta lavorando, cioè direbbe il falso.

Le quattro API v4 usate — array di keyframe, `stagger`, bersaglio-oggetto con
`onUpdate`, `onComplete` — sono state **verificate in una pagina vera** prima di
scriverle, come `CLAUDE.md` prescrive per anime.js.

---

## Le misure

Ritaglio del disco, raggio 163 px, profilo radiale per anello.

| banda | riposo | `t1` attivo | onda a metà |
|---|---|---|---|
| anello 46 s (0) | media 31,7 · max **47,7** | media **41,4** · max **96,2** | 31,7 · 47,7 |
| anello 74 s (1) | 25,6 · 48,5 | 25,6 · 48,5 | 25,6 · 48,5 |
| anello 120 s (2) | 28,9 · 47,7 | 28,9 · 47,7 | media **35,1** · max **96,4** |
| anello 233 s (3) | 27,9 · 48,5 | 27,9 · 48,5 | 27,9 · 48,5 |
| ghiera (4) | 35,5 · 99,4 | 35,5 · 99,4 | 35,5 · 99,4 |

- **A riposo nessun tratto supera L 48,5** — il tetto di §25.5, rispettato al
  decimo.
- **Con `t1` attivo si accende esattamente un anello**, e proprio quello che
  §25.6 assegna a `t1`. «Un solo anello per volta» non è una promessa: è nella
  tabella.
- Il max 99,4 della ghiera è il **marchio**, che vive lì in mezzo ed è a
  `--cy-700` per §25.13.

Invariante 25, misurato in finestra vera dopo il passaggio ad anime.js:
**`fotogrammiInUnSecondoDiRiposo: 0`**. Il motore idla quando non c'è nulla da
muovere, esattamente come il ciclo scritto a mano che sostituisce.

§25.13.5 rimisurato dopo il cambio di fondo: **3,39:1**, dentro la forbice 3–5.
Suite: **561 passed**.

---

## Il ciclo §11.7 di questo componente — `npm run nucleo`

⚠️ **Il nucleo ha quattro stati che a immagine ferma sono indistinguibili**:
fermo e in moto sono lo stesso pixel, e l'anello acceso lo si vede solo mentre
una causa è viva. Uno scatto solo di questo componente è un componente **non
verificato**.

`npm run nucleo` forza le cause una per volta — le stesse funzioni che chiama il
bus — e fotografa: `nucleo-riposo`, `t1-parte`, `t1-acceso`, `t2-acceso`,
`onda`, `fase-3`, `fase-9`. Il ritaglio è il disco dichiarato in `data-disco`,
non un riquadro scritto a mano: se il nucleo cambia raggio, il ritaglio lo
segue.

**Guardati.** A riposo il disco legge come un oggetto: fasce piene con le tacche
sopra, non un disegno tecnico. Con `t1` l'anello esterno stacca. Nell'onda si
vede il guscio a metà strada, con l'anello di mezzo acceso e gli altri fermi.

---

## Due difetti trovati guardando, non leggendo

| difetto | come si è visto | fatto |
|---|---|---|
| `capturePage(riquadro)` **non onora le coordinate della pagina** su questa piattaforma: col riquadro `{586, 240, 364×364}` — verificato sui numeri, centro del disco — tornava la fascia di schermo sopra il nucleo | l'immagine conteneva un pannello invece del disco | si cattura tutto e si ritaglia con `NativeImage.crop` |
| il modo `--nucleo` **non applicava la scena**: nove pannelli aperti, e «CORE SORGENTE» esattamente sopra il disco | il ritaglio era giusto e la scrivania sbagliata | si applica `avvio` e si nasconde tutto: il nucleo si fotografa scoperto, che è anche il riposo di §25.7 |

Il primo è la ragione per cui §11.7 mette lo sguardo **dopo** la misura: i
numeri del riquadro erano tutti giusti.

---

## ⚠️ Che cosa separa ancora il nostro dal riferimento, e perché non l'ho fatto

Due cose, e sono la stessa: **§25.5**.

| | riferimento | noi a riposo |
|---|---|---|
| bande chiare | media **92–125** | 25,6–35,5 |
| picchi (tacche, bordi) | **250** | **48,5** |
| campo interno | 43,3 | 22,6 (vuoto) |

§25.5 capa il tratto del nucleo a riposo a **L ≤ 48** e vieta `--cy-500` e
`--cy-100` — *«sono i colori del dato, e il dato sta nei pannelli»*. Le bande
chiare del riferimento stanno **sopra** quel tetto, e i suoi picchi lo stanno di
cinque volte. Riprodurle vorrebbe dire emendare §25.5, e le regole di uscita del
piano vietano di emendare una regola dentro un turno di implementazione.

Il **campo interno vuoto** è la terza differenza, e quella non è bloccata da
§25.5: un riempimento a L ≤ 48 sarebbe ammesso. Non l'ho messo per un motivo
misurato: il marchio è a `--cy-700` e il suo contrasto contro il pavimento è
**3,39:1** su una forbice che comincia a 3,0. Su un corpo a `--bg-panel` il
calcolo dà **3,07:1** — dentro per quattro centesimi. Un criterio che passa per
quattro centesimi non è passato, è in bilico, e non lo si mette in bilico senza
che qualcuno lo decida.

**Nessuna di queste tre è stata fatta.** Sono la scelta che resta, ed è del
proprietario.

---

## Che cosa NON è stato verificato

- **`--rust` su `critical`** e **`--amber` su `warn`**: regole CSS che nessuna
  esecuzione ha esercitato. Il livello è restato `nominal`.
- **La rampa di avvio** è verificata come *effetto* (`t1-parte` a 420 ms), non
  come curva: nessuna misura campiona la velocità nel tempo.
- **Il costo per fotogramma di anime.js sugli anelli in moto** non è misurato.
  A riposo è zero, e quello sì.
- **Il residuo `jf-tu3mtsr9`** resta sul piano.
- I due difetti **preesistenti** di `verifica:scrivania` — dock a 9 invece di 8,
  e cornice col fuoco identica a quella senza — restano aperti e non sono di
  questo lavoro.
