# Turno 1 — la misura di occlusione e il protocollo

> **`docs/PIANO-CORE-E-DENSITA.md` §5.** La misura arriva prima dei cambiamenti
> che deve misurare. Questo turno non cambia niente di ciò che si vede: aggiunge
> il modo di dire se un cambiamento ha funzionato, e ricalcola la linea di
> partenza con quel modo.

---

## Il risultato in tre righe

1. **Il centro libero funziona alla lettera**: il disco del nucleo è coperto
   dai pannelli allo **0,0 %**. Non «quasi»: zero su 20 832 punti campionati.
2. **Il caldo non è coperto — non c'è.** Sulla scrivania esiste **un solo**
   elemento caldo in tutto il DOM, ed è dentro il pannello globo. Fuori dai
   pannelli: nessuno. §5 supponeva cartelle manila nascoste sotto i pannelli;
   non ci sono cartelle manila.
3. **Il 78 % di ciò che si muove è il nucleo**, e si muove senza causa. Il
   resto sono pannelli che ricevono dati, ed è il loro mestiere.

---

## Che cosa è stato costruito

| dove | che cosa |
|---|---|
| `scripts/occlusione-dom.js` | **nuovo.** Non è un modulo: è un'espressione, valutata dentro la finestra viva. Le tre frazioni di §5 più due che la misura stessa ha reso necessarie |
| `app/main.js` | il protocollo §5 dentro `--scrivania`: T+3 s, due scatti, la valutazione, `occlusione.json` |
| `scripts/densita.mjs` | legge il gemello e ne fa la mediana; misura quanti pixel cambiano e **dove**; stampa l'occlusione accanto alla densità |
| `ui/src/desk/sfondo.js` | `data-disco` — chi disegna il disco ne dichiara centro e raggio |
| `ui/src/desk/cornice.js` | `data-pannello` — ogni cornice dice come si chiama |

### Perché la misura sta nella finestra e non nello script

Perché **«coperto» è una proprietà del layout**, e un PNG non sa che cosa aveva
sotto. È §11.7 passo 0 applicato a una metrica invece che a un componente. Lo
script legge il risultato dal file che la finestra lascia accanto allo scatto.

### Perché `elementFromPoint` e non la geometria dei rettangoli

Perché coprire non è una relazione fra rettangoli: è il risultato dell'ordine di
pittura, degli strati, delle trasformazioni e dei ritagli. Riscriverla qui
sarebbe duplicare il browser e sbagliare in un caso su venti — con una
duplicazione **muta**, che risponde con sicurezza anche quando ha torto.

⚠️ **Il limite, dichiarato nel file**: `elementFromPoint` salta ciò che ha
`pointer-events: none`. Oggi nessun pannello è così; il giorno che un velo a
schermo intero passasse gli eventi, questa misura direbbe «scoperto» a torto.

---

## La linea di partenza, con questo protocollo

Finestra 1536×843, massimizzata (verificato con `finestra.isMaximized()`, non
dedotto), scena `avvio`, nessun filtro, riposo escluso, quattro pannelli —
`agenti`, `globo`, `news`, `telemetria` — T+3 s, passo di campionamento 2 px,
mediana di due scatti a 250 ms.

### Densità

```
mediana   lum 34.4 · dev 20.25 · H 1.58 · 25-120 61.2% · L>60 9.2% · L>120 1.0%
          caldo 0.2% · barra 63.3%
```

Sotto soglia su quattro criteri su sei: entropia 1,58 < 2,4 · dev.std 20,25 < 32
· riempito 9,2 % < 25 % · caldo 0,2 % < 3 %.

### Occlusione — le tre frazioni di §5

| | misurato | su |
|---|---|---|
| **% del pavimento coperto da pannelli** | **56,61 %** | 300 288 punti |
| — coperto dalla cornice (barra, dock, catalogo) | 7,06 % | |
| — libero | 36,33 % | |
| **% degli elementi caldi coperti** | **0 su 0** | conteggio sull'albero |
| **% del disco del nucleo coperto** | **0,0 %** | 20 832 punti |

Le tre del pavimento sommano a 100,00: non è una coincidenza fortunata, è il
controllo che ha trovato il difetto descritto più sotto.

### Due misure che §5 non chiedeva e che sono servite subito

| | misurato |
|---|---|
| icone libere sul piano, coperte | **0 su 1** |
| il buco che la scena lascia aperto | disco **Ø344** = 7,73 % del pavimento |
| quanto ne occupa il nucleo | **Ø326**, il 90 % della sua area |

---

## Le tre premesse di §5 che la misura smentisce

### ① «Il disco è Ø502, il 42,0 % del pavimento»

**Sono due dischi diversi, e §5 ha usato quello sbagliato.**

Il Ø502 sta in `SEZIONE-25.md:178` ed è la geometria di **`rings.js`**, il
nucleo dello strato di presenza: `784 × 0,64 = 501,8`. Ma sulla scrivania quel
nucleo non c'è: c'è l'insegna di `sfondo.js`, il cui raggio è
`min(w,h)/2 × 0,552 × 0,7`, cioè **Ø326 — il 6,93 % del pavimento**, un sesto.

La conseguenza pesa sul **turno 3**: la fusione vorrebbe riportare la geometria
di `rings.js`, e **Ø502 non entra nel buco che la scena lascia aperto**, che è
Ø344. O si muovono i pannelli, o il nucleo fuso resta coperto in parte — che è
esattamente la cosa che il centro libero era stato deciso per evitare.

### ② «La soglia del 5 % era quasi il massimo teorico»

Giusto il ragionamento, sbagliato il numero: partiva da 42 % del pavimento. Col
disco vero il tetto è **6,93 %**, e va letto insieme al fatto che il disco è
scoperto al 100 % — cioè **il tetto è tutto disponibile**. Da qui una cosa che
il turno 4 deve sapere: se il nucleo rende poco, non è perché è coperto. È
perché è **piccolo e tenue**. Spostare pannelli non lo aiuterà.

Lo script adesso stampa il tetto accanto alla misura, ricalcolato ogni volta
come `area del disco × quota scoperta`, così non può più tornare a sembrare un
margine che non esiste.

### ③ «Le cartelle manila esistono e i pannelli le coprono»

**Non esistono.** In tutto il DOM della scrivania c'è **un** elemento caldo
(`r > b + 15`, la stessa definizione della densità), ed è `.pnl-glb__nome`
dentro il globo. Fuori dai pannelli: zero.

Le icone libere di §26.5 non sono calde — si dipingono a `--icona`, che è
freddo. E sul piano ce n'è **una sola**, che si chiama `jf-tu3mtsr9`: è un
residuo di `scripts/prova-icone.mjs`, che lascia le proprie cartelle nel layout
vero.

Per la leva ③ del piano generale cambia la diagnosi: il caldo allo 0,2 % **non
è nascosto sotto i pannelli, non è mai stato messo**. Si ripara costruendo, non
spostando — ed è il difetto meno caro dei due.

---

## §5.4 non è soddisfatto, e la misura dice di preciso perché

Il protocollo chiede lo scatto «con le animazioni ferme». I due scatti a 250 ms
**non coincidono**, e adesso si sa di quanto e dove:

```
in 250 ms cambiano 7 142 pixel su 1 294 848 — 0,55 %, massimo scarto 175/255
si divide cosi': il nucleo 78 % · telemetry 15 % · altrove 6 % · agents 0 %
```

Su quattro esecuzioni: **0,49 – 0,64 %**, con la quota del nucleo fra il **71 e
il 94 %**. È rumore di campionamento su un'animazione continua, non instabilità
della misura: tutti gli aggregati (lum, dev, H, L>60, caldo, barra) e tutte le
frazioni di occlusione sono risultati **identici** in tutte e quattro.

### E «animazioni ferme» non può voler dire «zero pixel che cambiano»

Il 15 % che si muove è il pannello telemetria che riceve un dato nuovo dal core.
È animazione **con** causa, che l'invariante 25 non vieta — è il solo modo in
cui un dato vivo si vede. Una soglia a zero boccerebbe la scrivania per aver
funzionato.

Il vincolo vero è l'altro pezzo: ciò che si muove **senza** causa. Oggi è il
nucleo, ed è la deroga 1 di `DEROGHE-7dad2b8.md`. Lo script lo isola e lo
stampa da solo: **5 568 pixel, il 78 % del moto**. È il numero «prima» del
turno 3, e il turno 3 lo deve portare a zero.

---

## I difetti trovati dentro la misura stessa

Nessuno di questi si vedeva leggendo il codice. Li ha trovati il primo giro,
perché i numeri non tornavano.

| # | difetto | come si è visto | fatto |
|---|---|---|---|
| 1 | `closest("#scrivania")` prendeva **anche `#scrivania`**, che è il pavimento: `<main>` a schermo intero, quindi `elementFromPoint` lo restituisce ovunque non ci sia altro | «cornice 43,3 % del pavimento» e «disco coperto dalla cornice al 100 %» — cioè pavimento nudo letto come cornice, e il disco **libero** letto come **coperto**. Il difetto rendeva impossibile la risposta giusta, non la sbagliava di poco | selettore `#scrivania > *` |
| 2 | «massimizzata» dedotta confrontando `innerWidth` con `screen.availWidth`: 1536 contro 1920, che sono la stessa cosa in unità separate dal fattore di scala 1,25 | rispondeva **`false`** su una finestra massimizzata davvero | la risposta la dà `finestra.isMaximized()` in `app/main.js`; in pagina restano i due numeri grezzi e `devicePixelRatio` |
| 3 | «i byte differiscono» e «la misura cambia» stampate come se fossero lo stesso fatto | `main.js` diceva «DIVERSI», `densita.mjs` «identici», nella stessa esecuzione | due frasi distinte, e in mezzo il numero che mancava: quanti pixel cambiano |
| 4 | i pannelli erano tutti «(senza titolo)»: WinBox ha una `.wb-title`, ma i nostri pannelli usano la propria testa e quella resta vuota | l'attribuzione del moto non distingueva quattro pannelli su quattro | `data-pannello` in `cornice.js`, su `box.window` — non `box.dom`, che non esiste |
| 5 | uno zero fra elementi caldi non si distingueva da un predicato rotto | `0/0` poteva voler dire entrambe le cose | si elencano anche i caldi **dentro** i pannelli: se il predicato ne trova uno, funziona |

---

## Un fatto sul protocollo, non sul codice

**`npm run scrivania` e la suite non si possono eseguire insieme.** Il turno l'ha
scoperto rompendo: `tests/test_layout.py::TestIconeVere::test_10_riavviato_il_core_e_ANCORA_LI`
è fallito una volta, e da solo passa. La fixture usa il **socket del core vivo**
(`platform_paths().socket_path()`), lo stesso a cui si collega l'app dello
scatto: mentre la suite verifica che le icone sopravvivano al riavvio, l'app
scrive il proprio layout sopra il loro.

Rieseguita a scrivania chiusa: **557 passed**.

---

## Che cosa NON è stato verificato

- **`elementFromPoint` con `pointer-events: none`** — il limite è dichiarato nel
  file ma non è meccanizzato: nessun test fallisce se domani un velo trasparente
  agli eventi coprisse la scrivania.
- **La soglia del 50 % per «coperto»** è dichiarata, non tarata: nessun elemento
  caldo sul piano l'ha ancora messa alla prova, perché non ce ne sono.
- **Il passo di 2 px** è stato scelto e scritto, non confrontato con 1 px su
  questa scena.
- **Il residuo `jf-tu3mtsr9`** resta sul piano: toglierlo è un cambiamento allo
  stato dell'utente, e questo turno non ne fa.
- **`sfondo.js` e `catalogo.js` non passano da `scripts/audit.mjs`**: non sono
  registrati in galleria. Le due modifiche di questo turno sono attributi
  `data-`, non stile, ma resta che l'audit su di loro non gira — ed è la stessa
  lacuna che `DEROGHE-7dad2b8.md` segnala per l'eccezione di `.sfd__marchio`.
