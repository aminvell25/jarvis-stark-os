# Il nucleo Aurora — sette deroghe, quel che regge, e il costo del ritorno

**1º settembre 2026.** Il proprietario ha portato un secondo riferimento: un
artifact `Jarvis Aurora.html`, completo e funzionante, e ha chiesto di
**eliminare il nucleo presente e ricrearlo su quella specifica, «anche se va
contro le nostre specifiche»**.

Il nucleo HUD costruito il giorno prima — ghiera graduata, tre corone
alfanumeriche, otto strati SVG, globo a spirale aurea — è stato **cancellato**.
Sta in git al commit `427e48c` e si recupera con un `git checkout`; il
documento che lo descrive, `NUCLEO-HUD.md`, resta in `docs/acceptance/` perché
racconta misure ancora vere sul metodo.

---

## Che cosa dice il riferimento, misurato

Non è un disegno: è un **motore**. La forma non è modellata, è calcolata a ogni
fotogramma da un rumore FBM sulla normale di tre icosaedri, e ciò che si vede —
creste, fronti d'onda, scarti, fasce di scansione — sono termini distinti
sommati allo spostamento radiale.

| | |
|---|---|
| **otto stati** | AVVIO · STANDBY · DIAGNOSTICA · ANALISI · DIALOGO · MINACCIA · SOVRACCARICO · ARRESTO, ciascuno con tinta, frequenza, spinta, respiro, rotazione, guadagno, bagliore |
| **tre gusci** | icosaedri `detail 4`, raggi 1,00 / 1,06 / 1,12, fasi 0 / 1,7 / 3,4, opacità 1,00 / 0,78 / 0,52 |
| **cinque passaggi** | scena → soglia → sfocatura separabile (due assi) → composito con rifrazione e aberrazione → scia per accumulo |
| **quattro anelli** | periodi 320 / 520 / 260 / 200 s, due orari e due antiorari |
| **55 colori** | scritti a mano nel riferimento |

---

## Le sei deroghe

### 1 · invariante 19 — zero glow, zero bloom

Il nucleo **è** una catena di post-processing. Non è un effetto aggiunto sopra:
il composito non è additivo, applica una curva di tono `c / (c + 0,82) × 1,62`,
e senza quella curva i tre gusci additivi saturano a bianco. Togliere il bloom
significa riscrivere anche il modo in cui i gusci si sommano.

**Costo del ritorno:** riscrittura del composito e ritaratura dei tre `uOp`.

### 2 · §25.11 — «niente three.js per il nucleo»

Il nucleo è three.js. Non c'è una versione SVG di un rumore FBM valutato per
vertice a 60 Hz.

**Costo del ritorno:** il nucleo non esiste.

### 3 · invariante 25 e §10.3 — «Fondo: immobile»

Quattro anelli girano in permanenza, una fascia di scansione attraversa il
nucleo in DIAGNOSTICA, una banda spazza il vetro ogni 7 s, i gusci respirano
sempre. **Il moto non ha causa: è lo stato che respira.**

⚠️ È la deroga più pesante: `CANCELLO-10.6.md` chiamava §10.3 *«l'unica riga
del progetto che non è mai stata violata»*. Ha ceduto una prima volta col
nucleo HUD e cede di nuovo qui, più a fondo.

**Costo del ritorno:** il contatore dei fotogrammi resta, e `fissa()` li porta a
zero — è ciò che rende ancora misurabile uno scatto.

### 4 · §25.5 — il tetto di luminanza del nucleo

`--cy-050` (#dff7ff, L 242,5) sta **sopra `--cy-100`**, cioè sopra il testo dei
pannelli, che §25.5 dichiarava il tetto invalicabile. È la luce calda del
riferimento: fronti d'onda, creste illuminate, marchio.

**Costo del ritorno:** un gradino della rampa, e il nucleo perde il suo caldo.

### 5 · invariante 22 — geometria parametrica con `qualityGate()`

Gli icosaedri sono primitive di three.js: la densità la fissa `detail`, non
`segmentsFor()`. `HudQuadrante` e `GloboWireframe`, che il gate lo passavano,
sono stati cancellati con il nucleo che li usava.

⚠️ **Al posto del cancello c'è un conteggio DICHIARATO:** `auroraOra().vertici`
riporta i vertici resi, e `test_nucleo.py::TestIlCancelloSostituito` verifica
che il conteggio esista e che il livello di suddivisione sia ancora 4. Un
cancello dichiarato più debole vale più di uno finto — ma è **più debole**, e va
scritto qui perché non sembri equivalente.

### 6 · invariante 26 — three.js ≤ 8 ms

Cinque passaggi, tre gusci, 4 500 vertici. **Misurato, non assunto:**

```
nucleo three.js: mediana 0,2 ms su 120 fotogrammi · tetto 8
                 3 gusci, 4500 vertici, 5 passaggi, tela 177 px

scrivania piena, nucleo in moto, carico massimo (verifica:densita):
three   4 render · costruzione 7,9 ms · poi mediana 0,5 ms · max 2,2 ms · dentro
```

⚠️ **Passa, e con margine — ma solo a questa scala.** La tela è 177 px perché
il disco è Ø326; a pieno schermo i cinque passaggi costerebbero ~10 volte tanto.
Il numero vale per la composizione attuale, non per il componente.

⚠️ **`npm run bench` NON lo vede**: quel giro apre il componente-banco della
galleria, dove il nucleo non c'è, e riportava `three: 0,3 ms` misurando
un'altra scena. La misura vera l'aggiunge `npm run nucleo`.

### 7 · §25.13.5 — la forbice di contrasto del marchio

**Misurato il 2 settembre 2026, e rosso in tutti e nove gli stati.**

```
             contrasto   luminanza    (forbice 3,0-5,0 · tetto 105)
  riposo       15,71:1      37,4      ❌ contrasto
  offline      15,64:1      35,0      ❌ contrasto
  onda         15,43:1      40,7      ❌ contrasto
  ascolto      10,91:1     103,0      ❌ contrasto
  franco   l'inchiostro arriva a r 66,1 px, la fascia interna a 119,9  ->  +53,8
  centro   [1024, 558] px CSS, viewport 2048x1115, da data-disco
```

Il riferimento fa il nome **quasi bianco** — `#eafbff`, qui `--cy-050` — su un
centro scuro. §25.13.5 capa il contrasto a 5,0 perché un marchio più contrastato
del testo dei pannelli compete col dato. Le due cose non stanno insieme, e non
c'è un gradino intermedio che le concili: a `--cy-600` il nome tornerebbe nella
forbice e smetterebbe di essere il nome del riferimento.

⚠️ **Il franco invece è POSITIVO: +39,3 px.** L'inchiostro non arriva sulla
fascia interna, quindi il composito sotto il nome resta un colore dichiarato e
non una media — che è la parte di §25.13.5 che protegge dalla misura ambigua, e
quella regge.

⚠️ **Il riferimento ha anche un GLOW sul nome** (`text-shadow 0 0 10px / 0 0
30px`) che **non è stato portato**, e non per prudenza: un alone sul marchio
rende §25.13.5 *non misurabile*, perché il criterio separa l'inchiostro dallo
scudo confrontando due scatti e chiamando «tratto» i pixel che si schiariscono.
Con un alone quella separazione non esiste più. Fra un bagliore e una misura
che funziona, resta la misura.

**Costo del ritorno:** il marchio a `--cy-600`, e il nome smette di essere la
cosa più chiara del nucleo.

#### ✅ La misura è RIPETIBILE, e il centro non è più cablato

Due esecuzioni consecutive danno numeri identici: *inchiostro a r 66,1 px,
franco +53,8, contrasto 10,9–15,7:1*. I numeri qui sopra vengono dalla prima
misura ripetibile.

Ci sono voluti due interventi, e sono di natura diversa.

**① Il centro del disco era CABLATO** in `scripts/densita.mjs`: `[768, 422]`,
il centro di una finestra 1536×843. Era giusto il giorno in cui è stato
scritto, e il guaio è come ha smesso di esserlo — non con un errore, ma
continuando a rispondere. Col disco fuori da quella posizione ogni distanza
usciva sbagliata **della stessa quantità**, e il referto diceva *inchiostro a
r 350 px* in tutti e nove gli stati. Un numero identico fra stati che mostrano
cose diverse è l'unico segno che c'era.

Adesso arriva da `data-disco` — che il DOM dichiara già, e che
`occlusione-dom.js` legge da mesi — e viaggia dentro `stati.json` insieme al
**viewport**, perché i pixel CSS e quelli dello scatto possono non coincidere:
misurato, la finestra è 2048×1115 CSS e lo scatto 2048×1115, ma nulla lo
garantisce, e un centro convertito con un solo fattore sbaglierebbe su una
sola asse — il modo più silenzioso di sbagliare.

Il referto porta la provenienza (`"da": "data-disco"`), e
`test_nucleo.py::TestIlCentroNonEPiuCABLATO` boccia se torna a essere un
ripiego. Il ripiego resta — una misura che manca è peggio di una che assume —
ma **annuncia di essere un ripiego**.

**② La vera causa della flakiness era il CORE ACCESO.** Con il core vivo la
scena di avvio popola i pannelli, e uno di essi copre il centro del nucleo —
comportamento voluto, il nucleo sta dietro i pannelli — ma allora i due scatti
non differiscono e non c'è niente da misurare. **§25.13.5 si misura col core
FERMO**, ed è l'opposto di `verifica:densita`, che il core lo pretende vivo.

#### Tre difetti che impedivano di misurarlo

Prima di poter dire «rosso» ho dovuto far tornare vero il numero. Le prime tre
misure dicevano *inchiostro fino a r 350 px* su un nome largo 140, con franco
**−230**, **identico in tutti gli stati** — e un numero che non cambia fra stati
diversi non sta misurando la scena.

| # | che cos'era | come si vedeva |
|---|---|---|
| 1 | **la scia rendeva il fotogramma non idempotente**: `max(nuovo, vecchio × 0,88)` fra due buffer alternati, quindi due render dello stesso stato danno immagini diverse | il criterio confronta due scatti a 120 ms e chiamava «inchiostro» l'intero nucleo. Da fermo la scia è spenta: non c'è moto da rappresentare |
| 2 | **il riquadro del marchio era il contenitore**, non le lettere: `left: 0; right: 0` dà un nodo largo quanto il disco — 431 px per un nome che ne occupa 140 | il criterio misurava l'angolo di un blocco vuoto |
| 3 | **il disco era fuori centro**: misuravo con `getBoundingClientRect()` invece di `clientWidth/clientHeight`, e il riquadro riportava 1115 dove il layout ne ha 843. Raggio 215,5 invece di 162,9, centro a (1024, 557) invece che a (768, 422) — e quel centro `densita.mjs` **lo ha cablato** | ogni distanza era sbagliata della stessa quantità, quindi costante |

---

## Che cosa NON è derogato, e la prova

### Invariante 18 — zero letterali

Il riferimento portava **55 colori scritti a mano**. Misurati in Rec. 709,
**54 cadono entro ~10 L da un gradino che §10.1 aveva già**:

```
#05080a  L   7,5   == --bg-abyss (7,6)      si riusa
#111719  L  21,9   == --bg-void (19,2)      si riusa
#2b3439  L  50,4   == --cy-900 (48,5)       si riusa
#46707d  L 104,0   == --fill-3 (103,0)      si riusa
#6b8a94  L 132,1   == --txt-ghost (125,3)   si riusa
#8fc2d0  L 184,2   == --cy-500 (181,4)      si riusa
#7fe0f4  L 204,8   == --cy-300 (200,4)      si riusa
#7ff0fc  L 216,8   == --cy-200 (212,9)      si riusa
#cfe8f0  L 227,3   == --cy-100 (231,3)      si riusa
#dff7ff  L 242,5   sopra tutto      ->  --cy-050
```

Le **otto tinte di stato** sono un caso a parte e sono entrate come famiglia
`--au-*`: la tinta di Aurora è un blu a ~210°, il ciano del progetto sta a
~192°, e cinque delle otto finivano a distanza 62-96 in RGB dal gradino più
vicino — cioè gli stati smettevano di distinguersi, che è l'unica cosa che una
tinta di stato deve fare. Gli otto **caldi** invece cadono tutti sulla rampa e
non hanno preso token.

Più due veli con l'alfa dentro — `--au-reticolo` e `--au-riga` — perché vivono
in `linear-gradient(colore 1px, transparent 1px)`, dove il colore sta dentro la
funzione e non c'è un elemento a cui dare un'opacità.

**Totale: undici token nuovi per 55 colori.** `test_nucleo.py` verifica che nel
nucleo non rientri un solo letterale.

### Invariante 23 — nessun dato inventato

Il riferimento riempie le corone con `REC248 | 5NC0DE | MK-XL | PWR.98` e fa
parlare JARVIS con un copione — *«Buonasera signore. Tutti i sistemi sono
operativi.»* — le cui sillabe sono contate sulle vocali.

**Niente di tutto questo è stato portato.** Le corone portano la stessa
telemetria del bus in base 16; e i fronti d'onda delle sillabe partono quando
**l'ampiezza vera sale di scatto** — un attacco misurato sullo spettro TTS
(`core/voice/spettro.py`) invece che previsto da un testo. Dove non c'è
sorgente, lo stato è vuoto e si vede.

Gli otto stati si derivano dai fatti che il bus porta già: nessun topic nuovo,
nessuna seconda fonte di verità.

| stato | causa vera |
|---|---|
| AVVIO | i primi 2,8 s dopo il montaggio |
| STANDBY | niente di attivo |
| DIAGNOSTICA | `attivo.ascolto` |
| ANALISI | `attivo.t1 \| t2 \| subagent` |
| DIALOGO | `attivo.parla` |
| MINACCIA | livello `warn`, o `agent.advisory` |
| SOVRACCARICO | livello `critical` |
| ARRESTO | `offline`, o il core non risponde |

### Invariante 20 — il testo non si rasterizza

Marchio, nome dello stato e corone stanno nel DOM e in nodi SVG. Nella tela
WebGL non c'è un carattere.

### Invariante 9 — anime.js, niente GSAP

Il riferimento usa keyframe CSS con una variabile per la velocità. Qui sono
quattro animazioni `anime.js`, e la differenza è una leva: `fissa()` può
azzerarle e riportarle ad angolo zero, un keyframe CSS no. Senza quella leva due
scatti dello stesso stato differirebbero per l'angolo.

---

## Sei difetti trovati GUARDANDO

| # | che cosa si vedeva | che cos'era |
|---|---|---|
| 1 | **sette PNG da zero byte**, senza un messaggio | `data-disco` è **tre numeri**, «dx,dy,r», e ci avevo scritto un nome. Il banco fa `split(",").map(Number)`, ottiene NaN, e `crop` restituisce un'immagine vuota |
| 2 | il nucleo **due volte e mezzo** troppo grande | il riferimento disegna a 1024 in un quadro che scala a 1,06, cioè quasi a pieno schermo. La scala del riferimento non si copia: si copiano i rapporti dentro il suo viewBox |
| 3 | il nome dello stato più grande del marchio | `gradino()` torna **unità di viewBox**, e l'avevo usato come pixel su un nodo del DOM: 26,7 px su un disco largo 345 |
| 4 | le letture accavallate alla ghiera, poi al guscio | provate a y 176/700 e a y 272/664. Il riferimento non ne ha: la sua telemetria sta in un pannello laterale, fuori ambito. **Tolte** — vedi sotto |
| 5 | i tre gusci fusi in **un anello unico** | la sfocatura del bloom è `2 / W` con W = 556, cioè lo 0,36 % della tela. Su 177 px diventa l'1,1 %: tre volte tanto |
| 6 | la galleria chiedeva un modulo **cancellato** | `tipografia.js` importava `./geometria.js` con percorso relativo, e i grep su «hud/geometria» non lo vedevano. Il server di sviluppo non mandava header di cache, quindi il browser teneva i moduli vecchi e l'errore sembrava un fantasma |

---

## Che cosa resta aperto, dichiarato

1. ⚠️ **Le letture in chiaro dentro il nucleo NON ci sono più.** AGENTE/FASE/
   MESH e CPU/RAM/TEMP/VOCE stavano nel nucleo precedente e si leggevano perché
   il centro era scuro; il guscio Aurora è luminoso e riempie il vetro. I dati
   veri non si perdono — le corone li portano in base 16 e la scrivania ha i
   propri pannelli — ma **la lettura in chiaro sì**. Chi la rivuole deve prima
   trovarle un posto che non copra il guscio: è un problema di composizione,
   non un ritocco.
2. ⚠️ **§25.13.5 è stato MISURATO ed è rosso in tutti e nove gli stati**:
   contrasto 11,5-15,7:1 contro un tetto di 5,0. È la deroga 7, qui sopra, con
   i numeri. Il franco però è positivo (+39,3 px).
3. ⚠️ **Il confronto per sovrapposizione col riferimento non è stato
   eseguito**: `Jarvis Aurora.html` è un artifact impacchettato, non
   un'immagine, e non c'è un fotogramma da sovrapporre.
4. ✅ **La densità è stata rimisurata, ed è MIGLIORATA: entropia 2,55.** Il
   nucleo HUD l'aveva riportata a 2,40 con margine zero; il commit di partenza
   `18b2e58` stava a 2,43. Aurora arriva a **2,55** (riempito 27,5, devStd
   37,6) — margine **+0,15**. Il guscio luminoso su corridoi neri e i quattro
   anelli danno all'istogramma le due gobbe che il nucleo HUD aveva perso.
5. ⚠️ **DIAGNOSTICA e DIALOGO sono verificati solo nello stato vuoto**:
   `voice.enabled` è `false`, e accendere il microfono è una decisione.
