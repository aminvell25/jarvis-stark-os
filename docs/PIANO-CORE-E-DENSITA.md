# Piano di implementazione — nucleo e densità

> **22 agosto 2026.** Sostituisce la sequenza in cinque turni proposta il
> giorno prima, che conteneva un errore di merito (rimuovere il marchio) e tre
> errori di forma (esperimenti sovrapposti, cancello di governance in coda,
> metrica introdotta dopo il cambiamento che deve misurare).
>
> Documento operativo. Ogni turno è un prompt a sé per Claude Code, e **fra un
> turno e l'altro c'è una misura**. Non si accorpano.

---

## 0. Da dove si parte, misurato

| | entropia | dev.std | L>60 | caldo | fondo nudo |
|---|---|---|---|---|---|
| riferimento `famiglia-a/01` | **3,32** | **55,7** | **42,1 %** | **5,70 %** | **21,9 %** |
| `shots/scrivania/scrivania.png` | 1,58 | 20,1 | 9,2 % | 0,18 % | 37,8 % |
| `shots/scrivania/riposo.png` | 0,53 | 16,6 | 4,8 % | 0,29 % | 86,7 % |

Storia dell'entropia: **1,31 → 1,67 → 1,61 → 1,55 → 1,58**. Cinque giorni per
**+0,27** su **+2,01** necessari: il 13 % del cammino. Il ritmo attuale non
arriva, e il piano qui sotto serve a cambiarlo, non a proseguirlo.

---

## 1. La correzione di merito

Avevo chiesto di togliere la scritta `J.A.R.V.I.S.` dal centro del nucleo,
citando l'invariante 23 e §25.11. **Sbagliato due volte:**

- l'invariante 23 vieta i **dati** segnaposto. Un marchio non è un dato;
- `famiglia-a/12-logo-anelli-concentrici.png` — che §25.1 dichiara riferimento
  **di questo componente** — ha `J.A.R.V.I.S.` al centro, con un filetto sotto.
  Avevo giudicato l'elemento contro `famiglia-a/01`, che è lo scatto di una
  scrivania piena e non il logo.

**Il marchio resta.** §25.13 lo definisce e lo vincola. Quello che va corretto
è la sua **luminanza**, non la sua esistenza.

---

## 2. Il difetto vero, che l'errore stava nascondendo

Ci sono **due nuclei**, tutti e due dichiarati sul riferimento `12`:

| | file | costo/fotogramma | dove si vede |
|---|---|---|---|
| anelli SVG | `ui/src/anim/rings.js` | **1,39 ms** in moto, 0,14 fermo | solo in galleria e in `moduli.js` |
| nuvola di punti | `ui/src/desk/sfondo.js` | **10,36 ms** | la scrivania, sempre |

Numeri dalla testata di `sfondo.js:58-64`, protocollo DevTools, stessa
scrivania e stesse fixture.

Due fatti che vanno letti insieme:

1. **§25.6 prescriveva già gli anelli**, testualmente: «Il componente esiste:
   `ui/src/anim/rings.js` […] **Non va riscritto.** Va spostato di strato.»
   `sfondo.js` è stato scritto lo stesso, e ha sostituito la geometria
   prescritta con una nuvola.
2. La nuvola costa **il 62 % di un fotogramma** contro i 15 ms che
   l'invariante 26 assegna **in tutto** a tre motori, e di quel costo arrivano
   a schermo **122 pixel su 264 049**, cioè lo **0,05 %** del pavimento
   (`docs/acceptance/MOCKUP-SCRIVANIA-VIVA.md:106-119`).

Sette volte e mezzo il costo, per l'implementazione che si vede meno.

---

## 3. La fusione — che cosa tiene e che cosa cade

Unificare **non** vuol dire buttare `sfondo.js` e montare `rings.js`: si
perderebbe il marchio, e con lui il riferimento `12`. Vuol dire il contrario.

`sfondo.js` resta il componente montato e **tiene**:

- il marchio `J.A.R.V.I.S.` (§25.13);
- l'arco ambra `ACC0/ACC1` — è l'unico caldo della scrivania, e il caldo è a
  0,18 % contro il 5,70 % del riferimento;
- le soglie di fase `SOGLIA_FASE`, cioè il legame con `state.snapshot.fase`;
- il contratto `crea/aggiorna/stato` verso `app.js`, invariato;
- lo strato `--z-insegna: 1` e `pointer-events: none`.

**Cade** una cosa sola: la nuvola di 1 500 punti. Al suo posto la geometria di
`rings.js` — quattro anelli `ReactorRing` più la ghiera fissa, periodi
46/74/120/233 s, varchi tutti diversi, centri sfalsati.

Le nove bande di `BANDE[]` non si buttano: sono il **profilo radiale misurato
sul riferimento** e diventano i raggi e le densità degli anelli. `LOBI[]` e
`VEL[]` invece cadono con la nuvola — un lobo è una proprietà di un punto, un
anello ha un varco.

**Guadagno atteso:** 10,36 → ~1,4 ms per fotogramma, e un nucleo che si legge.
**Rischio dichiarato:** la nuvola dava un gradiente continuo, gli anelli danno
tratti netti. Sull'entropia il segno **non è ovvio**: tratti netti alzano la
deviazione standard e possono abbassare il numero di livelli distinti. È
esattamente perché non è ovvio che il turno 3 si misura da solo.

---

## 4. La sequenza

Cinque turni. Il turno 0 è un **cancello**: finché non è chiuso non parte
codice. La metrica arriva **prima** dei cambiamenti che deve misurare.

| # | Contenuto | Tocca | Effetto atteso sulla densità |
|---|---|---|---|
| **0** | Le quattro deroghe di `7dad2b8`, una per una: motivo, cosa si perde a non farle. **Zero codice.** | niente | nessuno — è un cancello |
| **1** | Misura di **occlusione** in `scripts/densita.mjs` + protocollo di misura fisso. Ri-misura lo stato attuale. | `scripts/` | nessuno — è la nuova base |
| **2** | Marchio a norma §25.13: `--icona-viva` → `--cy-700`, eccezione nominata nell'audit, ricontrollo dello scudo | `sfondo.js`, audit | ~0. È conformità |
| **3** | Fusione dei due nuclei secondo §3 qui sopra | `sfondo.js`, `rings.js` | da attribuire, misurato **da solo** |
| **4** | Cartelle scoperte / abbandono del centro libero | scena, `scrivania.js` | ricavato dal fondo nudo 37,8 % → 21,9 % |

### Perché quest'ordine e non un altro

- **Il turno 0 sta davanti perché è governance.** Un cancello messo in coda a
  un prompt con cinque richieste si evade con una frase. Il commit `7dad2b8`
  ha emendato §11.6 da cinque a sei corpi **dopo** che avevo scritto di non
  farlo: se passa senza discussione, §11.6 smette di essere una regola e
  diventa una preferenza.
- **Il turno 1 sta prima del 2 e del 3** perché una metrica introdotta dopo il
  cambiamento che deve misurare non ha una base con cui confrontarsi.
- **Il 3 e il 4 sono separati** perché il 3 cambia il componente e il 4 cambia
  la scena. Insieme, il delta di entropia non è attribuibile a nessuno dei due.
  Cinque giorni per +0,27 sono già troppi per bruciare una misura.

---

## 5. Protocollo di misura — turno 1

Senza questo, due misure non sono confrontabili e il piano non decide niente.
È la lezione di **R82**: sei test verdi e la funzione rotta, perché nessuno
arrivava fino alla finestra vera (§11.7 passo 0).

Vincolato e scritto nello script, non nel prompt:

1. **Finestra massimizzata prima del primo render.** Non dopo
   `ready-to-show`: è il difetto R87, e falsa ogni confronto perché l'area
   cambia sotto ai pannelli.
2. **Stesso insieme di pannelli**, dichiarato per nome nella fixture.
3. **Stessa scena**, stesso filtro `Alt+1…4`, stato di riposo escluso.
4. **Scatto a T+3 s** dall'ultimo evento, con le animazioni ferme: gli anelli
   girano solo con una causa, e una causa in corso cambia la misura.
5. **Due scatti per esecuzione**, e si tiene la mediana delle due misure.

### La misura di occlusione

`densita.mjs` oggi misura ciò che si vede e non sa **che cosa è coperto**. È
il motivo per cui il caldo è a 0,18 %: le cartelle manila esistono — `app`,
`config`, `core`, `docs` sono visibili in riposo — e i pannelli le coprono.

Da aggiungere, in forma di frazione e non di giudizio:

- `% del pavimento coperto da pannelli`;
- `% degli elementi caldi coperti` — conteggio sull'albero, non sui pixel;
- `% del disco del nucleo coperto`.

⚠️ **Nota sulla soglia del 5 % di visibilità del nucleo.** Era, senza che me ne
accorgessi, il **massimo teorico**: disco Ø502 = 42,0 % del pavimento, e a
~12 % di inchiostro il tetto è 5,04 %. Misurato 5,24 %. «Passa di misura»
significava in realtà «completamente scoperto». La soglia va ricalcolata come
frazione del massimo raggiungibile, non come valore assoluto.

> ### ✅ Turno 1, fatto il 23 agosto 2026 — e tre premesse di questo §5 cadono
>
> Esito completo in `docs/acceptance/OCCLUSIONE-TURNO-1.md`. Il ragionamento
> qui sopra regge; i numeri no, e vanno corretti dove qualcuno li rileggerà.
>
> **① Sono due dischi diversi.** Il Ø502 è la geometria di `rings.js`
> (`SEZIONE-25.md:178`). Sulla scrivania quel nucleo non c'è: c'è l'insegna di
> `sfondo.js`, **Ø326 = 6,93 % del pavimento**, un sesto. Il tetto non è 5,04 %:
> è 6,93 %, ed è **tutto disponibile**, perché il disco risulta coperto dai
> pannelli allo **0,0 %**.
> Ne discende un vincolo per il **turno 3**: il buco che la scena lascia aperto
> è **Ø344**, e la geometria di `rings.js` **non ci entra**.
>
> **② «Le cartelle manila esistono e i pannelli le coprono»: non esistono.** In
> tutto il DOM c'è un solo elemento caldo, dentro il globo. Le icone di §26.5
> sono `--icona`, che è freddo, e sul piano ce n'è una sola — `jf-tu3mtsr9`,
> residuo di `scripts/prova-icone.mjs`. Il caldo allo 0,2 % **non è nascosto,
> non è mai stato messo**: si ripara costruendo, non spostando.
>
> **③ «Animazioni ferme» non può voler dire «zero pixel che cambiano».** Il
> 15 % di ciò che si muove è telemetria che riceve dati: animazione CON causa,
> che l'invariante 25 non vieta. Il vincolo è l'altro pezzo — **5 568 pixel, il
> 78 % del moto, sono il nucleo**, e quello non ha causa. È il numero «prima»
> del turno 3.

---

## 6. Regole di uscita, per ogni turno

Valgono uguali dal turno 2 al turno 4:

- **Un turno = un commit.** Se il commit ne tocca due, il delta non si attribuisce.
- **Misura prima e dopo, stesso protocollo §5.** Il numero va nel messaggio di commit.
- **Rollback dichiarato**: il turno nomina il commit a cui si torna, prima di partire.
- **Se il delta è negativo, si torna indietro e si scrive perché**, in
  `docs/acceptance/`. Un cambiamento che peggiora e resta è debito che nessuno
  ha deciso di prendere.
- **Nessun emendamento a un invariante dentro un turno di implementazione.**
  Se serve, si ferma e si apre un turno di governance come il turno 0.

---

## 7. Che cosa questo piano NON risolve

Scritto qui perché non sembri completo quando non lo è.

- **`dentroArea()` non riscala** (`desk/scrivania.js:578`). Legge
  `area_larghezza`/`area_altezza` da `layout.json` e non li usa: taglia
  soltanto. Latente — non era la causa del layout schiacciato, ma morde al
  primo cambio di monitor vero.
- **L'overflow della barra** (`barra.js:78`): 737 px di campi in 178 px
  disponibili, dodici resi e tre leggibili. `up`, `rx` e `scena` sono
  irraggiungibili. La metrica dell'inchiostro premiava il riempimento e non
  sapeva niente della leggibilità.
- **Il costo del nucleo sotto carico** non è mai stato misurato: i numeri di
  §2 sono a riposo. Con T1 che genera, gli anelli girano.
- **`--cy-800` e `--cy-600`** (P1/P2) sono proposti in `DIVARIO-PREMIUM.md` e
  non scritti in `tokens.css`.
- **97 voci «non verificato»** su diciassette documenti di accettazione,
  `TOOLS-CODE.md` il più carico con dodici.
