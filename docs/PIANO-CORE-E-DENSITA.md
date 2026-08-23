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

Il turno 0 è un **cancello**: finché non è chiuso non parte codice. La metrica
arriva **prima** dei cambiamenti che deve misurare.

> **Aggiornato il 23 agosto 2026, ore 13.** La sequenza era di cinque turni;
> ne sono stati eseguiti sette, tre dei quali non erano scritti qui. Il turno 4
> è stato **riscritto**: la sua premessa — «le cartelle esistono e i pannelli le
> coprono» — è stata smentita dal turno 1, e ciò che era «scoprire» è diventato
> «costruire», che è un altro lavoro e sta ora al 6.

| # | Contenuto | Tocca | Effetto atteso sulla densità |
|---|---|---|---|
| **0** ✅ | Le quattro deroghe di `7dad2b8`, una per una: motivo, cosa si perde a non farle. **Zero codice.** | niente | fatto 23 ago — `DEROGHE-7dad2b8.md`, uscita C |
| **1** ✅ | Misura di **occlusione** in `scripts/densita.mjs` + protocollo di misura fisso. Ri-misura lo stato attuale. | `scripts/` | fatto 23 ago — `OCCLUSIONE-TURNO-1.md` |
| **2** ✅ | Marchio a norma §25.13: `--icona-viva` → `--cy-700`, eccezione nominata nell'audit, ricontrollo dello scudo | `sfondo.js`, audit | fatto 23 ago — `MARCHIO-TURNO-2.md`, §25.13.5 a 3,40:1 |
| **3** ✅ | Fusione dei due nuclei secondo §3 qui sopra | `sfondo.js`, `rings.js` | fatto 23 ago — `NUCLEO-TURNO-3.md`. Moto senza causa 5 568 px → **0**; L>60 9,3 % → 9,2 % |
| **3b** ✅ | *Non pianificato.* Materia invece di wireframe, stati ad anime.js | `sfondo.js`, `rings.js` | fatto 23 ago — `NUCLEO-MATERIA-E-STATI.md` (`ece4289`) |
| **3c** ✅ | *Non pianificato.* Cancello di governance su §25.5 — la scala trasla di un gradino | niente | fatto 23 ago — `CANCELLO-25.5.md` (`e4851ae`), zero codice |
| **3d** ✅ | *Non pianificato.* Scala alzata + campo interno; marchio rimesso in piedi dal fondo | `sfondo.js`, `rings.js`, test | fatto 23 ago — `NUCLEO-SCALA-ALZATA.md` (`b2f7360`). Entropia 1,57 → **1,69** |
| **4** ✅ | **Il marchio negli STATI** — §25.13.5 misurata in tutti e sette gli stati di §25.6, non solo a riposo | `sfondo.js`, `app/main.js` | fatto 23 ago — `MARCHIO-TUTTI-GLI-STATI.md`. **Non è rotta**: nove stati, tutti 3,04:1. Densità invariata |
| **5** ✅ | La guardia dentro `verifica:scrivania` | `package.json`, `densita.mjs`, test | fatto 23 ago — `GUARDIA-MARCHIO.md`. Impronta dei sorgenti: se il nucleo cambia e nessuno rimisura, la suite cade |
| **6** ✅ | **Costruire** le cartelle manila di §26.5 sul piano (non «scoprirle») | `panels/cartella.js`, `moduli.js` | fatto 23 ago — `CARTELLA-MANILA.md`. Superficie manila, dati veri da `source.tree` |
| **7** ✅ | ~~Abbandono del centro libero~~ — **non è servito** | `moduli.js`, scena | fatto 23 ago — `CARTELLA-NELLA-SCENA.md`. Caldo 0,2 → **3,2 %**, entropia 1,76 → **1,93**, disco ancora coperto allo 0,0 % |

> ⚠️ **Tre turni su dieci non erano nel piano** — 3b, 3c, 3d. Sono buoni turni,
> tutti e tre con misura e commit separati, e 3c è persino un cancello fatto
> bene. Ma un piano che scopre tre passi dopo che sono avvenuti non li ha
> ordinati: li ha ratificati. Vale la pena notarlo mentre è ancora piccolo.

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

---

## 8. ⚠️ ~~§25.13.5 si rompe nello stato T0~~ — misurato: non si rompe

> ### ✅ Chiuso dal turno 4, 23 agosto 2026 — e tre premesse di questa sezione cadono
>
> Misurati **nove stati**, non simulati: tutti **3,04:1**, col composito sotto
> il nome a `rgb(19, 33, 42)` = `--bg-panel` esatto. T0 compreso.
>
> | questa sezione dice | misurato |
> |---|---|
> | §25.13.5 chiusa a 3,01:1 | **3,04:1** |
> | il marchio è largo 183 px | **137 px** |
> | le lettere estreme stanno sopra la ghiera | **no**, 9,3 px di franco |
>
> La sezione è calibrata su `b2f7360`; `4611cb6` ha reso la larghezza del nome
> **derivata** dal raggio del campo, e da lì l'inchiostro non arriva più alla
> ghiera. Il `massimo del ritaglio 96,1 SENZA marchio` citato come prova sta
> nell'**angolo del ritaglio**, non sotto le lettere: il contrasto si calcola sui
> soli pixel di tratto, che si fermano a r 64,1 px contro i 73,4 della ghiera.
>
> La simulazione era giusta nel metodo e applicata a una geometria superata.
> Esito completo, guardia meccanizzata e misura del campo:
> `docs/acceptance/MARCHIO-TUTTI-GLI-STATI.md`.

---

## 8bis. Il testo originale della sezione, per memoria

> **23 agosto 2026.** Motivo per cui il turno 4 è stato riscritto e messo
> davanti a tutto il resto.

`b2f7360` chiude §25.13.5 a **3,01:1** su un minimo di 3,00. Un centesimo.
Quel valore è stato misurato in **uno solo** dei sette stati che §25.6 elenca:
il riposo.

`CAUSE[4] = "t0"` è la **ghiera interna**, `ANELLI[4]`
(`outerR 58 · thickness 3`). Con il disco a Ø325,8 centrato in (768, 422) —
numeri da `occlusione.json` — quella ghiera cade a **r 74,7–78,8 px**, e il
marchio è largo 183 px, cioè ±91,5 px. Le lettere estreme ci stanno **sopra**.
Lo conferma la misura del progetto stesso: `massimo del ritaglio 96,1 SENZA
marchio` è quella ghiera a `--cy-700`.

Quando T0 va, la ghiera passa a **`--cy-500`, L 181**.

**Simulazione**, sui due PNG di `shots/scrivania/`, ricolorando i pixel della
ghiera con la stessa copertura α e ricalcolando il WCAG del colore dichiarato
contro il composito — la catena è calibrata sul valore del progetto, perché a
riposo riproduce `rgb(19, 34, 43)`, L 31,5, 3,01:1 esatti:

| ipotesi di accensione | px | % dell'inchiostro | sotto L | contrasto |
|---|---|---|---|---|
| riposo (riprodotto) | — | — | 31,5 | **3,01:1** ✅ |
| ghiera 55–58 unità | 313 | 6,1 % | 33,5 | **2,94:1** ❌ |
| ghiera + tacche 55–61 | 317 | 6,1 % | 33,5 | **2,94:1** ❌ |
| tutto il ciano del ritaglio | 1 079 | 6,1 % | 33,5 | **2,94:1** ❌ |

Le tre ipotesi coincidono perché **tutti** i pixel ciani che stanno sotto
l'inchiostro del marchio sono già dentro la fascia della ghiera. Il risultato
non dipende da come si sceglie la maschera.

**Riserve, dichiarate.** È una simulazione su uno scatto a riposo, non uno
scatto preso con T0 acceso, e assume che l'impulso cambi **solo il colore**. Se
alza anche l'opacità o lo spessore, peggiora. Il numero vero è a uno screenshot
di distanza, ed è esattamente ciò che il turno 4 deve produrre.

**Ma il difetto non è T0.** T0 è solo la prima cosa che si è provata. Un
criterio con un centesimo di margine si rompe con qualunque cosa cambi il
composito, e il nucleo ha sette stati per cambiarlo. La domanda del turno 4 non
è «T0 rompe?» ma «in quale stato §25.13.5 regge, e con quanto margine».

**L'uscita che nessuno ha preso.** `NUCLEO-SCALA-ALZATA.md` scrive «non c'è un
altro token più scuro con cui rispondere», e considera solo `--bg-deep`.
`--bg-void` vale **L 19**, undici punti sotto `--bg-panel`: sotto il nome darebbe
**≈3,4:1** — aritmetica, non misura — cioè resterebbe dentro la forbice **anche
sotto T0**. Campo a `--bg-void` = campo invisibile = uscita 3 di quel documento,
e quel documento la giudica la più costosa. Non lo è: costa **la quota di +0,12
che il campo porta da solo**, e quella quota non è mai stata misurata. Si misura
in una riga: rendere due volte, con e senza campo.

---

## 9. Tabella di marcia — dove siamo il 23 agosto 2026

**Densità**, storia completa (`scripts/densita.mjs`, protocollo §5 dal turno 1):

| | ent | dev | L>60 | caldo | fondo nudo |
|---|---|---|---|---|---|
| riferimento `famiglia-a/01` | **3,32** | **55,7** | **42,1 %** | **5,70 %** | **21,9 %** |
| 18 ago | 1,31 | — | — | — | — |
| 19 ago | 1,67 → 1,61 → 1,55 | — | — | — | — |
| 22 ago | 1,58 | 20,1 | 9,2 % | 0,18 % | 37,8 % |
| 23 ago, turni 0–3 | 1,57 | — | 9,2 % | 0,2 % | — |
| **23 ago, dopo `b2f7360`** | **1,69** | — | **10,0 %** | 0,2 % | — |
| 23 ago, dopo `fa31575` | 1,76 | 22,6 | 12,5 % | 0,2 % | — |
| **23 ago, dopo `2eab331`** | **1,93** | **28,9** | **16,45 %** | **3,2 %** ✅ | **31,3 %** |

> **Aggiornato a fine giornata.** Sei giorni per **+0,62** su +2,01: il **31 %**
> del cammino, ed è la prima volta che una giornata sola ne porta **+0,36** —
> tanto quanto i cinque precedenti messi insieme. Il **caldo è entrato nella
> forbice** (3,2 % su 3–6 %) e non è più fra i criteri falliti; restano
> entropia, dev.std e riempito. Il **fondo nudo** è sceso da 37,8 % a 31,3 %
> contro i 21,9 % del riferimento.

~~Sei giorni per **+0,38** su **+2,01** necessari: il **19 %** del cammino.~~ Il
ritmo è migliorato — `b2f7360` da solo vale +0,12, cioè un terzo di tutto ciò
che sei giorni hanno prodotto — ma il grosso della distanza resta, e non sta nel
nucleo: sta nel **caldo (0,2 % contro 5,7 %)** e nel **fondo nudo**.

**Il nucleo è chiuso**, salvo la conformità del turno 4: un solo componente,
zero fotogrammi a riposo, budget invariato a 16,7 ms, geometria dal riferimento.

**Quello che non è stato ancora toccato**, in ordine di resa attesa:

| | stato | dove sta scritto |
|---|---|---|
| Cartelle manila sul piano | `--manila` e `--manila-viva` esistono in `tokens.css`, `desk/icone.js` le disegna, **sul piano ce n'è zero** | §26.5 |
| Il caldo in generale | 0,2 % contro 5,70 %. Un solo elemento caldo in tutto il DOM, dentro il globo | `DIVARIO-PREMIUM.md` §0 |
| Il fondo nudo | 37,8 % contro 21,9 % | idem |
| `--cy-800` e `--cy-600` (P1/P2) | proposti, mai scritti in `tokens.css` | `DIVARIO-PREMIUM.md` |
| ~~`dentroArea()` non riscala~~ | ✅ **provata e ritirata il 23 ago**: la scala rompe §26.9 criterio 4, perché `area_*` è il **pavimento** e non lo schermo — si muove per una finestra non massimizzata o un dock più alto. Isolata in `geometria-area.js` e fissata da quattro prove: `LAYOUT-PERSISTENTE.md` punto 11 | §7 |
| Traboccamento della barra | `barra.js:78` — 737 px di campi in 178 px | §7 |
| ~~Costo del nucleo **sotto carico**~~ | ✅ **misurato il 23 ago**: quattro anelli in moto insieme sulla scrivania piena — mediana **16,70 ms**, p95 16,80, max 17,80, cioè indistinguibile dal riposo e migliore del caso col filtro (p95 17,10, max 22,40). La nuvola costava 4,49 ms **a riposo** | §7 |
