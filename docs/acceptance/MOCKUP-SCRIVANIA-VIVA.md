# Mockup «Scrivania viva» — misura e scarti

> Progetto Claude Design `9ade4e1a-f5ce-4eb4-8b4a-1a790b1a44d2`, file
> `Scrivania viva.dc.html`. Letto il 21 agosto 2026 attraverso il connettore
> Claude Design.
>
> **Questo documento non implementa niente.** Estrae le decisioni di layout,
> le traduce nei token esistenti dove esistono, propone i token dove non
> esistono, e dichiara ciò che va rifiutato. Che cosa adottare è una decisione
> del proprietario, non di questo passaggio.

Il PNG esportato è `docs/design-reference/famiglia-d/01-scrivania-viva.png`.
La regola della famiglia D è in `docs/design-reference/README.md`.

---

## 0. Che cos'è davvero il file

`Scrivania viva.dc.html` è un guscio di quaranta righe. Non contiene un
disegno: contiene un `<x-import>` che monta `jarvis/avvia-scrivania.js`, il
quale finge `window.jarvis` — le stesse cinque funzioni di `app/preload.js` —
e poi importa `jarvis/src/app.js`.

Cioè: **il mockup è il nostro renderer**, alimentato da fixture invece che dal
socket. Non è un'immagine da imitare, è il nostro codice più un delta. Il
delta, misurato file per file, è tutto qui:

| | Che cos'è |
|---|---|
| `src/desk/sfondo.js` | **nuovo** — l'insegna di §25, uno strato di presenza dietro i pannelli |
| `src/app.js` | +3 blocchi: importa, monta l'insegna come primo figlio, la iscrive al bus |
| `src/style/app.css` | +1 token `--z-insegna: 1` e +1 regola `#scrivania > .sfd` |
| `src/panels/calendario.js` | **nuovo** — non montato dalla scrivania, vive in galleria |
| `src/panels/tabella.js` | **nuovo** — idem |
| `src/panels/ciambella.js` | **nuovo** — idem |
| `src/panels/lettura.js` | **nuovo** — idem |

`tokens.css` e `desk/moduli.js` sono **identici ai nostri**, commento per
commento: il mockup non ha spostato un token né una cella, e la scena `avvio`
è la nostra. Questo è il fatto più importante del documento, perché significa
che la differenza di densità misurata sotto **non viene da una disposizione
diversa**.

### Come è stato prodotto il PNG, e che cosa non copre

Il canvas di Claude Design non è fotografabile da qui. Il PNG è un rendering
**locale**: albero `ui/` di questo repository, più i tre delta di `sfondo.js`,
`app.js` e `app.css` applicati; le stesse fixture di `avvia-scrivania.js`;
viewport 1536×843, la stessa dello scatto con cui viene confrontato; scatto
preso solo dopo `__jarvisPronto` **e** dopo che ogni tessera del catalogo è a
opacità piena, perché in questa sessione una galleria fotografata a metà
animazione ha già prodotto una diagnosi sbagliata.

Non è coperto: il wrapper `support.js` del canvas e il suo pannello Tweaks.
La copia locale di `sfondo.js` ha i commenti in prosa accorciati; ogni
costante numerica, selettore e corpo di funzione è verbatim.

---

## 1. La misura

`node scripts/densita.mjs`, tre immagini, stessa metrica.

| | lum | dev.std | entropia | L>60 | L>120 | caldo | barra |
|---|---|---|---|---|---|---|---|
| `famiglia-a/01` — riferimento | 68,7 | **55,7** | **3,32** | **42,1 %** | **17,4 %** | **5,70 %** | 28,4 % |
| `famiglia-d/01` — il mockup | 38,2 | 20,8 | 1,62 | 11,6 % | 1,3 % | 0,50 % | 60,9 % |
| `shots/scrivania/scrivania.png` — noi | 35,1 | 19,6 | 1,61 | 10,3 % | 1,0 % | 0,20 % | 63,3 % |
| soglia | — | 32 | 2,40 | 25 % | — | 3–6 % | 25 % |

### Il mockup NON batte la scrivania attuale sulla densità

Entropia **+0,01**. Deviazione standard **+1,2**. L>60 **+1,3 punti**. Caldo
**+0,3 punti**. Quattro differenze marginali — e le ho scomposte tutte, perché
un punto e mezzo può essere un progresso o può essere rumore, e a occhio non si
distingue.

**Il caldo, pixel per pixel.** Delta totale 3 196 px su 1 294 848:

| dove | mockup | noi | delta | causa |
|---|---|---|---|---|
| dentro il globo | 2 261 | 2 273 | **−12** | il terminatore: identico |
| nella barra | 830 | 208 | +622 | vedi sotto |
| sul fondo libero a destra e in basso | 1 768 | 27 | **+1 741** | le cartelle manila |

Le cartelle vengono dalla **fixture**: `fs.list` del mockup elenca nove
directory di workspace, la nostra macchina ne ha una. Misurati i pixel vicini a
`--manila` `#b48d64`: 1 735 nel mockup contro 645 nostri, e 645 px è
esattamente **una** cartella. Non è una decisione di layout, è un dato diverso.

I 622 px della barra sono distribuiti **uniformemente su tutte e dodici le
bande** — 4·70·62·84·75·86·95·92·50·55·96·61 contro
0·12·6·19·22·22·33·30·16·10·30·8 — cioè non c'è un elemento caldo in più da
nessuna parte: sono le stesse etichette con un antialiasing più caldo. È
l'artefatto delle due vie di cattura: il nostro scatto esce da una finestra
Electron, il mockup da un Chromium headless, e i due rasterizzano il testo in
modo diverso.

> ⚠️ **Conseguenza sul metodo.** A queste grandezze `caldo` misura anche la via
> di cattura. Le due immagini non sono confrontabili sotto il mezzo punto
> percentuale, e nessuna delle differenze della tabella sopra viene da una
> decisione di disegno.

Il mockup risolve **altro**, non la densità. Che cosa risolva è la sezione 2.

### La misura decisiva: l'insegna non si vede

Reso una seconda volta lo stesso albero con l'insegna **spenta** (controllo),
e confrontati i due PNG pixel per pixel sui soli punti che nel controllo sono
esattamente `--bg-void` `#0f1418`, cioè il pavimento nudo:

```
pavimento nudo nel controllo : 264 049 px = 22,0 % dello schermo
  di cui cambiati dall'insegna:     122 px =  0,05 % del pavimento
                                            0,01 % dello schermo
  luminanza media dei pixel accesi: 45,7 · massima 165
```

**Centoventidue pixel.** L'insegna disegna 3 523 punti e ne arrivano
centoventidue allo schermo: la scena `avvio` la copre per il 99,95 %.

La causa è geometrica e si legge nel file: il raggio è
`min(larghezza, altezza) / 2 × 0,552 × 0,7`, cioè `843 / 2 × 0,386 = 163 px`,
centrato nell'area utile — che i cinque pannelli della scena occupano per
intero. Anche la scritta `J.A.R.V.I.S.`, larga il 56,1 % del raggio per lato,
è interamente sotto `MESH AGENTI`.

§25.1 cita `famiglia-a/10`: lì il globo «occupa il 45 % della larghezza ed è
**circondato** dal chrome, non coperto». Il mockup fa l'opposto della propria
premessa. Non perché l'insegna sia sbagliata — perché **nessuno ha cambiato la
scena per farle posto**, e `moduli.js` è identico al nostro.

---

## 2. Che cosa il mockup risolve davvero, e che noi non sapevamo

Confronto delle bande verticali d'inchiostro (L>25), dodici bande da 128 px:

| banda | 0–128 | …centro… | 1024–1152 | 1152–1280 | 1280–1408 | 1408–1536 |
|---|---|---|---|---|---|---|
| `famiglia-d/01` | 63,4 % | 80–87 % | 87,1 % | 86,5 % | **86,5 %** | 19,7 % |
| `shots/scrivania` | 62,8 % | 80–87 % | 86,3 % | 27,7 % | **1,0 %** | 1,0 % |

Il quarto destro della **nostra** scrivania è vuoto; quello del mockup no. E
la scena è la stessa, riga per riga.

La causa non è il disegno. È il ripristino del layout:

```
/home/aminvell/.local/share/jarvis-os/layout.json
  area salvata: 800 × 503 · scena: avvio
  globo        4  36     telemetria 484 36     agenti 364 380
  anelli     720  36     news       720 380
```

Il file registra `area_larghezza: 800`, `area_altezza: 503`, e poi
`ripristina()` **rimette le coordinate assolute su un'area di 1536 × 843
senza riscalarle**. I pannelli si accalcano nella metà sinistra perché sono
posati dove stavano in una finestra grande poco più di un quarto.

Il mockup non ha un `ui.layout` da ripristinare, quindi mostra la scena
dichiarata — ed è così che il difetto è saltato fuori.

> ⚠️ **Correzione a quanto riportato prima.** Il «quarto destro vuoto» che
> avevo attribuito alla composizione è un difetto del ripristino: l'area di
> riferimento viene salvata e non viene usata. La scena `avvio`, applicata a
> 1536 px, arriva a 1436. Non è lavoro di questo passaggio, ma va scritto qui
> perché è il mockup ad averlo reso visibile.

---

## 3. Gli scarti, uno per uno

Per ognuno: quale **decisione di layout** esprime, a quale **token** il suo
valore corrisponde, e — se non corrisponde a nessuno — la **proposta**.

### S1 · Lo strato di presenza (`desk/sfondo.js`)

**Decisione.** Uno strato a schermo intero, primo figlio di `#scrivania`,
`pointer-events: none`, sotto le icone (5) e i pannelli (10+). Non è un
pannello: nessuna testa, nessun `⊟ ⊡ ⊠`, nessuna cella, non si chiude. È il
contratto in sette punti di §25.3, rispettato punto per punto.

**Gerarchia.** Lo stato dell'agente si legge dalla **forma** e non da
un'etichetta: sette stati dichiarati (`spento`, `offline`, `attesa`,
`ascolto`, `pensa`, `parla`, `tool`), ognuno con la propria fonte sul bus, e la
leva principale è la **compostezza** — la nuvola si stringe, non accelera. Le
nove bande radiali si accendono per **fase**: `state.snapshot.fase` decide
quante corone sono vive, dal mozzo verso il bordo.

**Token.** `--z-insegna: 1` non è colore, spaziatura né tipografia:
l'invariante 18 non lo riguarda, ed è la stessa nota che `app.css` porta già
per `--z-icone`, `--z-aggancio`, `--z-cornice`, `--z-trascino`. La scritta usa
`--font-ui` e `--icona-viva`: conforme.

**Non conforme:** quattro colori letterali, un `text-shadow`, e la rotazione.
Vedi sezione 4 e sezione 5.

### S2 · Il calendario (`panels/calendario.js`)

**Decisione, ed è quella che il README chiede da due giorni.** La cella di un
calendario è una **superficie**, non un riquadro con un numero dentro:

| | token | L |
|---|---|---|
| cella del mese | `--fill-2` | 89 |
| fine settimana | `--fill-1` | 66 |
| fuori dal mese | `--bg-deep` | 30 |
| oggi, una su quarantadue | `--cy-500` | 181 |
| banda dei giorni | `--fill-1` | 66 |

Il numero è `--t-title` in basso a destra — «una quota, come su un disegno
tecnico» — e occupa circa mezza cella. Il confine fra i due mesi è un
**gradino di luminanza**, non un bordo: §10.5 applicata dentro un pannello.

**Tutti i valori sono token. Zero letterali.** È esattamente il riquadro che
`docs/design-reference/README.md` indica come sorgente del 42 % di superficie
riempita, e qui è già costruito.

### S3 · La tabella densa (`panels/tabella.js`)

**Decisione.** Cinque regole, tutte misurate sul riferimento `famiglia-a/03`:

1. l'intestazione **rovescia la polarità** — fondo `--icona` (L 171), testo
   `--bg-void`, misurato 7,23:1. È l'unica banda chiara del corpo, e serve a
   ritrovare le colonne dopo aver perso il filo;
2. la zebra è un gradino di **sei punti di L** — `--bg-panel` su
   `--bg-raised`, 1,08:1: si vede che sono righe e non si vede la riga;
3. i numeri a destra, in mono, `tabular-nums`;
4. la riga scelta è un **riempimento** (`--fill-2`), mai un bordo;
5. il piede usa la **stessa griglia** delle righe, quindi ogni totale sta
   sotto la propria colonna.

Zero letterali. `position: sticky` su intestazione e piede.

### S4 · La ciambella (`panels/ciambella.js`)

**Decisione.** Anello e non disco (foro al 56 % del raggio, con il totale
dentro); varco fra i settori invece di un contorno; **varco dichiarato** di
0,22 rad in cima, che è l'asimmetria progettata di §11.6 regola 6; legenda a
fianco **col valore**, non solo il nome.

**Token.** La scala dei riempimenti è cinque gradini della stessa famiglia
fredda — `--cy-100`, `--cy-300`, `--cy-500`, `--icona`, `--txt-dim` — scelti
misurando il contrasto sul corpo a `--bg-raised` e scartando `--cy-900`
(1,22:1) e `--cy-700` (2,82:1). Nessun settore è caldo, quindi nessuno finge
di significare attenzione. `d3-shape` e `anime.js` sono già dipendenze:
invariante 9 e invariante 10 intatte.

### S5 · La lettura grande (`panels/lettura.js`)

**Decisione.** Il numero **è** il pannello: cifre raggruppate col punto,
chiave fra quadre a destra e piccola, riga di provenienza sotto in `--t-micro`.
Una lettura senza provenienza è un fatto senza fonte.

**Token — ed è l'unica evasione tipografica di tutto il mockup.** Il corpo del
numero è `calc(var(--t-title) * 2.4)` = **48 px**. §11.6 regola 1 fissa cinque
gradini: 8,5 / 11 / 12 / 14 / 20. Il file lo dichiara apertamente e dice
perché. Vedi la proposta P4.

### S6 · Le cartelle manila visibili

**Non è una decisione di layout.** Le due cartelle in basso a destra del PNG
vengono dalla fixture `fs.list`, che elenca nove directory; la workspace vera
ne ha una. Il delta di caldo (0,20 → 0,50 %) è tutto qui.

---

## 4. I token che non esistono — proposte, non scritture

I quattro colori della nuvola sono letterali in testa a `sfondo.js`:

```js
const COL = ["#1c5f6b", "#3f97a6", "#8fdfe9", "#c9a227"];
```

Misurati in Rec. 709 su 0–255 e confrontati con l'intera tabella dei token:

| letterale | L | token più vicino | distanza RGB | L del token | esito |
|---|---|---|---|---|---|
| `#8fdfe9` | 207 | `--cy-300` `#7fdbe8` | **17** | 200 | **nessun token nuovo** |
| `#1c5f6b` | 82 | `--fill-2` `#336276` | 26 | 89 | proposta P1 |
| `#3f97a6` | 133 | `--txt-ghost` `#66838a` | 52 | 125 | proposta P2 |
| `#c9a227` | 161 | `--manila` `#b48d64` | 68 | 146 | **rifiutato**, P3 |

### P1 · `--cy-800: #1c5f6b` — L 82

**Perché.** La rampa fredda salta: `--cy-900` L 48, `--cy-700` L 100,
`--cy-500` L 181. Fra il primo e il secondo c'è un gradino di 52 punti, ed è
proprio la banda in cui vive il velo di una nuvola additiva: `--cy-900` è
invisibile sul corpo di un pannello (1,30:1, misurato in `tokens.css`) e
`--cy-700` è già un tratto. Il letterale sta esattamente a metà.

**Contro.** Un token nuovo per un solo consumatore è un token che nessuno
manutiene. Se l'insegna non si adotta, questa proposta cade con lei.

### P2 · `--cy-600: #3f97a6` — L 133

**Perché.** Stesso ragionamento, gradino successivo: fra `--cy-700` (100) e
`--cy-500` (181) ci sono 81 punti. Il token più vicino in RGB è `--txt-ghost`,
che è **grigio freddo** e non ciano: usarlo qui direbbe «testo terziario»
dentro un disegno che non è testo.

**Contro.** Lo stesso di P1, e in più: due token nuovi nella stessa rampa la
portano da cinque gradini a sette, e §10.1 tiene le rampe corte apposta.

### P3 · L'oro `#c9a227` — **da rifiutare**

Non ha un token vicino e non deve averlo. È un caldo saturo a L 161, e §11.1
riserva il caldo all'**attenzione** con un token solo, `--amber`. Un secondo
caldo è un secondo significato: chi vede l'arco ambra dell'insegna e la cella
ambra del meteo deve poter dedurre la stessa cosa dai due. Se l'arco
dell'insegna deve restare caldo, usi `--amber` (L 185); se non deve significare
attenzione, non sia caldo.

### P4 · Il sesto corpo tipografico

`calc(var(--t-title) * 2.4)` = 48 px in `lettura.js`. Due strade, ed è una
decisione di §11.6, non di un pannello:

- **`--t-display: 48px`** come sesto gradino dichiarato, e allora la
  moltiplicazione sparisce e il valore è contestabile in un posto solo;
- **rifiutare** e tenere `--t-title` (20 px), accettando che la nostra lettura
  grande sia meno grande di quella del riferimento — che a 901 px di larghezza
  usava 28 px, cioè il 3,1 % della larghezza; il nostro `--t-title` su 1536 è
  l'1,3 %.

Il file del mockup scrive: «chi trovasse questa moltiplicazione e volesse un
sesto gradino nella scala di §11.6 avrebbe ragione». È il modo giusto di
sollevare la questione, e resta una questione aperta.

---

## 5. Che cosa ho rifiutato, e perché

### R1 · La rotazione continua — invariante 25, e costa 10,2 ms per fotogramma

L'insegna gira sempre: `giro += P.vel * dt` a ogni fotogramma, senza che sia
successo niente. Il file la difende come stato — «lo stato è una condizione che
dura» — ma l'invariante 25 non distingue: *nessuna animazione senza causa, zero
animazione ambientale*.

Misurato con `Performance.getMetrics` del protocollo DevTools, dieci secondi di
osservazione per ciascuno, stessa scrivania, stesse fixture, stesso viewport:

| | task | script | layout |
|---|---|---|---|
| con l'insegna | **10,36 ms/fotogramma** | 2,60 | 0,05 |
| senza (controllo) | **0,20 ms/fotogramma** | 0,04 | 0,04 |

**Cinquanta volte.** L'insegna da sola prende il 61 % di un fotogramma a 60 Hz,
e l'invariante 26 assegna in tutto 15 ms a tre motori (three.js ≤8, Pixi ≤3,
anime.js ≤4). L'intervallo fra fotogrammi non lo mostra — mediana 16,70 ms in
entrambi i casi, perché il vsync assorbe tutto: è esattamente il difetto che
`DIVARIO-PREMIUM.md` §12 descrive, «il budget di frame misura l'intervallo,
non il margine».

Il numero da tenere a mente è l'altro: **la nostra scrivania a riposo costa
0,20 ms per fotogramma con cinque pannelli aperti**, globo three.js e glifi
PixiJS compresi. È l'invariante 25 che funziona, ed è la cosa che l'insegna
spenderebbe.

### R2 · I quattro colori letterali — invariante 18

Vedi sezione 4. Uno dei quattro si riconduce a un token esistente; per gli
altri tre la decisione è del proprietario.

### R3 · Il `text-shadow` sulla scritta — invariante 19

```css
text-shadow: 0 0 22px var(--bg-void), 0 0 8px var(--bg-void);
```

Non è un glow: il colore è il **pavimento**, quindi toglie luce invece di
aggiungerne, ed esiste per tenere leggibile la scritta mentre la nuvola le
passa dietro. Ma l'invariante 19, come è scritta oggi, ammette l'ombra **solo
per separare due superfici sovrapposte**, e la scritta non copre niente: è
sopra la nuvola, sullo stesso strato. O si dichiara l'eccezione — «uno
schermo scuro dietro un testo, dello stesso colore del fondo, non è un'ombra» —
o la regola la vieta.

### R4 · La telemetria del mockup è sintetizzata

`avvia-scrivania.js` lo dichiara nel proprio commento, e la dichiarazione è
ciò che §11.9 chiede. Va comunque scritto qui, perché il PNG resta:
**`cpu 5.0 %`, `ram 30.3 %`, `temp 48.7 °C` in `famiglia-d/01` sono inventati.**
Tutto il resto del mockup no — i 312 fusi, l'albero dei sorgenti, le note
d'archivio e la mesh vengono dal repository.

### R5 · I quattro pannelli nuovi non sono nel file misurato

`calendario`, `tabella`, `ciambella` e `lettura` esistono nel progetto ma
`moduli.js` non li importa: non compaiono in `Scrivania viva`, e quindi **non
entrano in nessuno dei numeri della sezione 1**. Sono valutati qui per il
codice, non per la resa. Chi volesse la loro densità deve prima decidere se e
dove entrano nella scena — che è la stessa decisione, ancora aperta, di cui
l'insegna ha bisogno per essere visibile.

---

## 6. Che cosa NON ho potuto verificare

Dichiarato, come chiede la definizione di «fatto».

1. **Il mockup reso dal canvas di Claude Design.** Ho reso localmente; il
   guscio `.dc.html` non contiene disegno, ma il wrapper `support.js` del
   canvas e il pannello Tweaks non erano nel giro.
2. **Che ogni file di `jarvis/src/**` coincida col nostro.** Ho confrontato
   `tokens.css`, `desk/moduli.js`, `src/app.js` e `style/app.css` per intero —
   identici a meno dei delta elencati — e ho dedotto il resto dall'elenco dei
   percorsi, che combacia con il nostro albero tranne i sette file dichiarati.
3. **I sei stati dell'insegna diversi da `spento`.** Con `voice.enabled = false`
   l'insegna resta in `spento`, ed è l'unico stato nel PNG. `ascolto`, `pensa`,
   `tool`, la fase e l'onda non sono stati fotografati.
4. **Il budget per motore di §10.4.** Ho misurato il tempo di task del thread
   principale, non tre budget separati: la misura dice quanto costa l'insegna
   *in totale*, non come si ripartisce fra canvas 2D, three.js e Pixi.
5. **La resa a risoluzioni diverse da 1536×843.** È il punto 10 di
   `DIVARIO-PREMIUM.md`, aperto da prima di questo documento.
6. **Il confronto sotto il mezzo punto percentuale.** Le due immagini escono
   da due vie di cattura diverse — finestra Electron contro Chromium headless
   — e la scomposizione della sezione 1 mostra che l'antialiasing del testo da
   solo sposta il `caldo` di 622 px. Per confrontare davvero servirebbe lo
   stesso motore di cattura per entrambe.

---

## 8. La barra del mockup

> Letta il 22 agosto 2026 su richiesta del proprietario. **Descrizione, non
> adozione**: qui non si implementa niente, si dice che cosa fa.

Due cose in questo progetto si chiamano «barra»: la fascia di stato in alto
(`desk/barra.js`, §13) e il catalogo in basso, che §26.3 intitola *«Il
catalogo — la barra in basso»*. Il mockup ha cambiato **tutte e due**, in
misura molto diversa. Il vocabolario della richiesta — linguette, campi
percorso, plinto, griglia, scorrimento a inerzia, cartelle manila — è quello
di §26.3, quindi il catalogo ha la parte lunga; la fascia in alto ha una
modifica sola, ed è importante.

`desk/icone.js` — le cartelle manila — è **identico al nostro**: stessa
semina 2×2 dalle sottocartelle vere, stesso conteggio sempre presente, stessa
linguetta al 45 %. Le quattro cartelle che si vedono nel PNG vengono dalla
fixture, che elenca nove directory; la nostra macchina ne ha una.

---

### 8.1 La fascia in alto — una riga, e i campi tornano raggiungibili

L'unica differenza, e non è cosmetica:

| | nostro | mockup |
|---|---|---|
| `.brr__campi` | `overflow: hidden` | `overflow-x: auto` · `overflow-y: hidden` · `scroll-snap-type: x proximity` |
| ogni campo | — | `scroll-snap-align: start` |

**Che cosa fa.** I dodici campi di stato — `fase pid tool cli radici chiavi stt
llm t2 up rx scena` — scorrono in orizzontale quando non ci stanno, con lo
scatto per campo. La barra di scorrimento compare solo alle larghezze in cui
serve, e `app.css` l'ha già riportata nella palette per tutta l'app.

**Perché.** Il commento del mockup porta la misura: *737 px di campi in 178
disponibili, dodici resi e tre leggibili*, con `up`, `rx` e `scena`
irraggiungibili per sempre. `overflow: hidden` su una fila che non va a capo
non è un troncamento, è una **cancellazione senza rimedio**: il campo non è
piccolo, non c'è. Lo scatto per campo perché «rx 11.0 kB» fermato a metà
rimetterebbe in scena lo stesso difetto.

È un difetto **nostro**, presente oggi in [barra.js:78](ui/src/desk/barra.js:78).

---

### 8.2 Il catalogo — azione per azione

Il pannello passa da `calc(var(--grid) * 5.5)` = 605 px a
`calc(var(--grid) * 5.5 * 0.7)` = **423,5 px**, il 27,6 % della scrivania. La
frazione resta scritta nel `calc` invece di essere risolta a mano, così si
legge da dove viene.

**① Frecce ◂ ▸** — invariate.

**② Campi percorso** — la polarità torna indietro:

| | fondo | testo |
|---|---|---|
| nostro | `--fill-3` (L 103) | `--bg-void` |
| mockup | `--bg-deep` + filo `--cy-900` | `--txt-primary` |

La ragione data è di gerarchia, non di gusto: erano la superficie più accesa
del pannello e portano un percorso e un conteggio, mentre la griglia — che è
il soggetto — era la più scura. Il riferimento li ha chiari, ma là anche la
griglia è piena: la banda accesa non era l'unica cosa illuminata. Nel mockup
la polarità rovesciata resta **una sola per pannello** e va sul contenuto,
cioè sull'intestazione del registro.

**③ Linguette** — le stesse quattro (`MODULI FILE SCENE SISTEMA`, l'ultima
dichiarata non pronta). Cambia il comportamento della fascia: i due campi di
stato passano da `flex: 1` a `flex: 1 0 auto; white-space: nowrap`, e la
fascia scorre in orizzontale con lo scatto per voce. Misurato: a 423,5 px la
somma dei figli è 421,8 su 421,9, e con `flex: 1` i campi venivano compressi a
73,8 px, andavano su **tre righe** e l'altezza della fascia non la decideva
più la tipografia ma il testo che si spezzava. Con lo scorrimento le linguette
stanno prime nel DOM e restano visibili; a cadere oltre il bordo sono i due
campi, che sono **letture**, non comandi.

**④ Griglia** — due misure rifatte:

| | nostro | mockup | perché |
|---|---|---|---|
| altezza | `--grid * 0.8` = 88 px | `--grid + --s-4` = 142 px | il riferimento dà il 69,5 % del pannello, non il 53 % |
| tessera | 20×20 | **48×32**, rapporto 3:2 | 28 px nel riferimento è l'**8,2 % della larghezza** di un pannello da 342, non un valore assoluto: sul nostro da 605 vale 50 px |

Il mockup lo dichiara come un errore doppio della stesura precedente — una
percentuale trasferita come pixel, e un rettangolo reso quadrato — «ed è la
ragione per cui la nostra griglia sembra un francobollo in un angolo».

**⑤ Il registro** — la novità più grande, e non è una tessera più grande: è
una **tabella densa** che sostituisce la griglia nella sola linguetta `MODULI`.

```
pos │ applicazione   │ stato  │ gruppo
 01 │ Telemetria     │ aperta │ SIS
 02 │ Mesh agenti    │ —      │ SIS
```

- intestazione **sticky**, polarità rovesciata su `--icona` con testo
  `--bg-void`;
- colonne a passi della scala assoluta — 32 / 1fr / 56 / 104 — e non derivate
  da `--grid`, perché `--grid` cambia col pannello: derivandole, la colonna
  dello stato misurava 45,8 px e «aperta» rendeva «aper…», cioè la parola che
  porta lo stato era l'unica troncata;
- zebra a `--bg-panel` (lo stesso gradino di `panels/tabella.js`), hover
  rovesciato a `--fill-1`;
- `aria-pressed="true"` sulle righe dei moduli aperti, con la cella dello
  stato su una piastra `--cy-500`;
- le righe fuori dal filtro corrente scendono a `--txt-dim` (`data-fuori`);
- un clic sulla riga **lancia** il modulo;
- nessun colore dichiarato sui figli: stato e gruppo si distinguono per
  **peso** e **opacità**, che sono monotoni su qualunque fondo — il colore per
  elemento non sopravvive al rovesciamento dell'hover.

Due dettagli che vengono da una misura e non da un'intenzione:

- **scorre in VERTICALE** (`overflow-y: auto`), al contrario del nastro delle
  tessere che scorre in orizzontale. Nove righe fanno 248 px in una vista di
  142, e con lo scorrimento orizzontale cinque applicazioni su nove erano
  tagliate fuori e irraggiungibili. Il verso lo decide la forma del contenuto.
- **altezza 104 px** (`--s-5 + --s-4 + --s-2`) per mostrare quattro righe più
  il filo della quinta: a 96 px se ne vedevano tre e mezza, e a sei su nove
  «un elenco che si mostra quasi tutto non è un elenco che invita a scorrere —
  è uno che sembra completo e non lo è».
- **`margin-bottom` di 36 px** (`--s-4 + --s-1`) per cedere lo sbalzo del
  plinto. Misurato: dodici collisioni, la riga «File manager» coperta per
  intero, 40×30 px, illeggibile **e** non premibile. Il primo tentativo era un
  `padding-bottom`, ed è il meccanismo sbagliato — un padding in fondo a un
  contenuto che scorre libera l'ultima riga e lascia quelle di mezzo dov'erano.

**⑥ Il plinto** — da fila fissa a **giostra**.

| | nostro | mockup |
|---|---|---|
| quante voci | `PLINTO_MAX = 5` | `Infinity` |
| disposizione | fila centrata, `gap: --s-4` | finestra di **4** su un arco, passo 96 px |
| profondità | nessuna | le due esterne voltate di **34°** e allontanate di **30 px**, caduta con esponente 1,6 |
| navigazione | nessuna | rotella = una piastra · trascinamento continuo con aggancio al rilascio · frecce |
| animazione | scambio con `stagger(45)` in uscita e in entrata | `animate` sull'**indice**, 320 ms `outQuad`, e `disponi()` ricolloca |

La ragione del tetto tolto è la definizione stessa: *«il plinto è la barra
delle applicazioni, e una barra delle applicazioni mostra TUTTE le
applicazioni: quando non ci stanno, scorre»*. Con nove moduli, i quattro fuori
dal taglio non erano raggiungibili da nessuna parte.

L'arco non è decorazione ed è dichiarato: le quattro della finestra **si
premono tutte dove sono** — non c'è una piastra «a fuoco», perché l'arco dice
che poggiano su un piano, non quale sia quella scelta. L'esponente 1,6 esiste
perché con la caduta lineare le interne giravano di 11° e le esterne di 34, e
a occhio sembravano quattro inclinazioni casuali invece di un arco.

Le piastre **non sono tutte uguali**, ed è la stessa lezione che §26.3 aveva
già scritto per il dock vecchio: *aperto adesso = piastra, chiuso = simbolo
nudo*. La varietà non si inventa, la porta il fatto che una barra delle
applicazioni ha qualcosa da dire.

Il pavimento in prospettiva è stato rimisurato per intero:

| | nostro | mockup | misura |
|---|---|---|---|
| larghezza del bordo lontano | 17 % di inset | **12,5 %** | il trapezio del riferimento è largo il 75 % del pannello, non il 66 % |
| altezza prima della rotazione | 12 px (7,4 proiettati, 4,3 %) | **28 px** (`--s-4 - --s-1`), 14,8 proiettati, 7,3 % | il riferimento ne dà l'8,4 % |
| gradiente | `--fill-1` piatto + filo `--cy-700` | `--bg-raised` → `--fill-1`, filo vicino `--fill-3` | campionato: lontano L 51, corpo L 59→65, vicino L 71 |

Il verso della luce era **rovesciato** nelle due stesure precedenti — accento
sul bordo lontano e corpo che scuriva scendendo — «ed è per questo che il
trapezio non si leggeva come un pavimento». E le icone escono dal flusso: sono
appese al filo lontano e sforano di 28 px verso l'alto, così il plinto dichiara
la propria altezza (`--s-3`) e smette di mangiare la griglia.

**⑦ Scorrimento a inerzia** — **invariato**. `FERMO_PX_MS` e la fisica del
nastro restano dov'erano, e il commento del mockup lo dice: quella regola vale
per il nastro delle tessere, che cresce in colonne verso destra. Il registro
introduce un secondo scorrimento, verticale, e **non** è inerziale: un elenco
di righe non è una striscia.

**⑧ Cartelle manila** — invariate, vedi sopra.

---

### 8.3 Quali stati ha

| dove | stati |
|---|---|
| linguetta | `moduli` · `file` · `scene` · `sistema` (dichiarata non pronta) |
| tessera | normale · hover · `aria-pressed` (aperto) · `data-fuori` (fuori dal filtro) |
| riga del registro | normale · zebra · hover rovesciato · `aria-pressed` con piastra `--cy-500` · `data-fuori` |
| piastra del plinto | dentro la finestra · fuori (sfuma a `SFUMA = 0.5`) · aperta (piastra) · chiusa (simbolo nudo) · fuori dal filtro |
| giostra | ferma · in animazione (320 ms) · **in presa**, con indice frazionario legittimo perché è il dito a tenerlo lì |
| stato vuoto | `WORKSPACE NON LEGGIBILE` · `NESSUNA SCENA IN SETTINGS.TOML` · `§26.7 · DOCTOR, IMPOSTAZIONI, CESTINO — NON COSTRUITI` |

Gli stati vuoti restano tre e restano espliciti, ma diventano **maiuscoli e
telegrafici**: erano prosa minuscola in un pannello che altrove parla per
sigle. E `MODULI` non ne ha più uno, perché non ha più un vuoto: ha il
registro.

---

### 8.4 Cosa mostra che la nostra non mostra

1. **L'elenco completo dei nove moduli**, con stato e gruppo, in una lettura
   sola. Da noi la linguetta `MODULI` mostra nove tessere di solo glifo.
2. **Tutte e nove le applicazioni sul plinto.** Da noi sono cinque, e le altre
   quattro dal plinto non si raggiungono.
3. **Lo stato come parola** — «aperta» — e non solo come stato premuto.
4. **La posizione nel plinto** (colonna `pos`): quanto lontano sta
   un'applicazione dalla finestra di quattro.
5. In alto: `up`, `rx` e `scena`, che alle larghezze strette da noi spariscono.

### 8.5 Cosa fa la nostra che quella non fa

Poco, ed è onesto dirlo. Le due condividono per intero il gesto di estrazione,
le linguette, le frecce, l'inerzia del nastro e gli stati vuoti. Resta una
cosa sola:

- **l'animazione di scambio del plinto** al cambio di filtro — uscita e
  entrata con `stagger(45)`. Il mockup l'ha sostituita con `disponi()`, che
  ricolloca invece di rientrare. Le due dicono cose diverse: la nostra annuncia
  «il plinto è cambiato», quella del mockup dice «sei qui dentro un elenco».
  Non è una perdita netta, è una scelta fra due messaggi.

### 8.6 Dove differisce da §26.3

| §26.3 | nostro | mockup | verdetto |
|---|---|---|---|
| linguette a separatore diagonale, 8,7 % dell'altezza | sì | sì, **più lo scorrimento** | il mockup aggiunge, non contraddice |
| due campi percorso **riempiti** nella testa | `--fill-3` su testo scuro | campi scuri con filo | **si discosta dalla lettera**, e argomenta: il riferimento li ha chiari perché ha anche la griglia piena |
| griglia scorrevole, 53 % dell'altezza | 88 px, tessere 20×20 | 142 px, tessere 48×32 | il mockup è **più vicino** alla misura del riferimento (69,5 % contro 53 % della prima lettura) |
| plinto in prospettiva con cinque icone | cinque, fila piatta | **nove**, giostra su arco, finestra di quattro | tensione dichiarata: vedi sotto |
| scorrimento a catalogo con inerzia (§26.4) | sì | sì, invariato, **più** uno verticale non inerziale nel registro | coerente |
| cartelle manila fuori dal pannello | sì | identico | nessuna differenza |

**La tensione da decidere, e non la decido io.** §26.3 dice che il plinto è la
barra delle applicazioni; il mockup ne trae che deve mostrarle tutte, e per
mostrarle tutte in 423 px le fa scorrere quattro per volta. Ma una barra delle
applicazioni che ne mostra quattro su nove **non le mostra tutte**: le rende
raggiungibili, che è un'altra cosa. La compensazione è il registro — l'elenco
completo sta lì, e il plinto diventa la parte «calda» di quell'elenco.

È una risposta coerente. È anche un pezzo di interfaccia in più da mantenere,
e sposta il catalogo verso il file manager di famiglia-c e via da
`famiglia-a/01`, dove la fascia bassa è una griglia densa e basta. La scelta
fra «plinto che scorre + registro» e «plinto fisso che mostra il massimo che
ci sta» è di chi ci lavora, non di questo documento.

---

## 7. In una riga

Il mockup **non risolve la densità** — la sposta di un punto su quattro
metriche e per ragioni di fixture. Risolve una cosa diversa e più profonda:
dà alla scrivania uno **strato che non se ne va**, con lo stato letto dalla
forma. Ma così com'è quello strato è invisibile — 122 pixel su 264 049 di
pavimento — e costa 10,2 ms per fotogramma a una scrivania che a riposo ne
costa 0,20.

Le due cose non si risolvono con una correzione di stile: si risolvono
decidendo se la **scena** deve aprirsi per lasciarlo vedere. Finché la scena
resta questa, l'insegna paga tutto e non si vede.
