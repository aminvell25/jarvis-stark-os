# 25. Strato di presenza — il nucleo

> Da aggiungere a `docs/SPEC.md` dopo §24. Rev proposta: **5.3**.
> Presuppone i ruoli di riempimento di `DIVARIO-PREMIUM.md` §1: senza quelli,
> il vetro sopra il nucleo diventa poltiglia. **Non è lavoro parallelo, è un
> prerequisito.**

---

## 25.1 Perché esiste

**Riferimenti visivi**: `docs/design-reference/famiglia-a/12-logo-anelli-concentrici.png`
per la forma del nucleo — anelli **concentrici** (vedi la nota qui sotto), varchi tutti
diversi. `famiglia-a/10-globo-gps-locator.png` per come un elemento centrale domina una
schermata senza svuotarla: il globo occupa il 45 % della larghezza ed è
**circondato** dal chrome, non coperto.

> ### ⚠️ «Centri sfalsati» era sbagliato — corretto il 23 agosto 2026
>
> Questa riga diceva «anelli disallineati, **centri sfalsati**», e da lì la
> tabella `ANELLI` di `ui/src/anim/rings.js` aveva preso scarti fino al 4,2 %
> del raggio, ognuno in una direzione diversa. A schermo si vedevano storti.
>
> **La misura dice il contrario.** Adattando un cerchio ai bordi di ciascuna
> banda di `famiglia-a/12` coi minimi quadrati, gli scarti dal centro stanno
> fra **0,15 e 2,08 px su un raggio di 120** — sotto l'1,7 %, e dello stesso
> ordine dell'errore della misura. Il riferimento è concentrico.
>
> Lo dicevano anche due cose già scritte, che nessuno aveva confrontato con
> questa: **§10.3 chiama quella riga «Anelli concentrici»**, e il file si
> chiama `12-logo-anelli-**concentrici**.png`.

Fino a §13 la scrivania ha **un solo strato**. Tutto ciò che si vede è un
pannello, dentro una cella, dentro un workspace. Cambiando workspace cambia
tutto, e non resta niente.

Manca la cosa che rende un ambiente *abitato* invece che consultato: un
elemento che non se ne va. Il nucleo è quello. Non è un modulo in più — è ciò
sopra cui i moduli stanno.

La conferma che questa sezione colma un buco previsto e mai riempito sta in
§10.1: la ricetta `.jarvis-panel` è **traslucida al 62 % con `backdrop-filter:
blur(16px)`**. Un pannello traslucido ha senso solo se dietro c'è qualcosa.
§10.1 è stata scritta presupponendo questo strato. È rimasta lettera morta
perché dietro non c'era nulla, e su nero opaco e traslucido sono identici.

---

## 25.2 Il modello a tre strati

`#scrivania` smette di essere il contenitore dei pannelli e diventa il
contenitore di tre figli sovrapposti.

```
#scrivania
├── .strato-presenza   z0   il nucleo — mai una finestra
├── .strato-pannelli   z1   WinBox, i 14 pannelli
└── .strato-modale     z2   la conferma di §6.2
```

Nuovi token in `tokens.css`, perché anche gli z-index sono valori letterali e
l'invariante 18 non fa eccezioni:

```css
--z-presenza: 0;
--z-pannelli: 10;
--z-modale:   100;
```

Lo strato di presenza è `pointer-events: none` per intero. Non si clicca, non
si seleziona, non riceve il fuoco. Un elemento a schermo intero che intercetta
il puntatore sotto quattordici pannelli è una fonte di difetti che non si
capiscono guardando il codice.

---

## 25.3 Il contratto del nucleo

Sette regole. Se una cade, il nucleo è tornato a essere un pannello.

1. **Non ha cornice.** Nessuna testata, nessun `⊟ ⊡ ⊠`, nessun piede tecnico.
   L'anatomia a cinque parti di §10.2 vale per i pannelli; il nucleo non è un
   pannello.
2. **Non sta nel dock.** Non si accende e non si spegne. Il dock elenca gli
   otto moduli di §13, e il nucleo non è uno di quelli.
3. **Non si può chiudere.** Nessun percorso nell'interfaccia lo rimuove.
4. **Non ha una cella.** La sua geometria non viene da `moduli.js`.
5. **Persiste attraverso i workspace.** Cambiando da 01 a 04 non si ricrea,
   non si rianima, non lampeggia. È l'unica cosa che non cambia, ed è il
   motivo per cui esiste.
6. **Mostra stato vero.** Invariante 23 senza sconti: se il core non è
   collegato, il nucleo lo dice e si ferma.
7. **Si muove solo con una causa.** Invariante 25. Vedi §25.6.

---

## 25.4 Il vetro — i tre `background` da togliere

La ricetta di §10.1 è coperta da tre mani di vernice opaca. Vanno tolte tutte
e tre, o il nucleo resterà invisibile.

| File | Riga | Oggi | Diventa |
|---|---|---|---|
| `ui/src/style/app.css` | 35 | `.winbox { background: var(--bg-panel); }` | `background: transparent;` |
| `ui/src/style/app.css` | 42 | `.winbox .wb-body { background: var(--bg-panel); }` | `background: transparent;` |
| `ui/src/panels/*.js` | — | `.pnl-xxx { background: var(--bg-panel); }` | `background: var(--vetro);` |

E il vetro entra nei token, perché §10.1 lo definisce con tre letterali che
oggi vivono solo dentro `.jarvis-panel`:

```css
--vetro:       rgba(19,33,42,.72);   /* --fill-1 al 72% */
--vetro-blur:  16px;
--vetro-sat:   145%;
```

72 % e non 62 %: con un nucleo dietro, il 62 % di §10.1 lascia passare troppo
e il testo dei pannelli densi — tavola periodica, glifi, console — perde
leggibilità. Il valore va **misurato** col criterio di §25.8, non scelto.

⚠️ **La galleria resta opaca.** `gallery.html` non ha lo strato di presenza:
un componente va giudicato per sé. Ma la variabile `--vetro` è la stessa, così
che un pannello non abbia due aspetti. La galleria dipinge un fondo pieno
`--bg-void` dietro il componente e la composizione si risolve lì.

---

## 25.5 Leggibilità — la scala che non si può violare

Il nucleo sta **sotto** il pannello, in senso letterale e di luminanza.

> ### ⚠️ Emendata il 23 agosto 2026 — la scala sale di un gradino
>
> Decisione del proprietario, motivata da una misura: il profilo radiale di
> `famiglia-a/12`, il riferimento che §25.1 assegna a questo componente, porta
> le proprie bande chiare a **media L 92–125**. Il tetto precedente — L 48 sul
> tratto a riposo — rendeva quel riferimento **irriproducibile per
> costruzione**, e il risultato si vedeva: un nucleo di soli contorni tenui,
> che leggeva come un disegno tecnico invece che come un oggetto.
>
> La scala non è stata abolita, è stata **traslata di un gradino**: ogni
> elemento sale al token successivo e le distanze restano. Il vincolo che
> conta — *il nucleo non compete col dato* — è tenuto da ciò che NON sale: il
> testo dei pannelli resta a L 224, `--cy-100` resta vietato, e la regola «un
> solo anello per volta» resta.
>
> Il cancello, con i numeri e il costo del ritorno, è in
> `docs/acceptance/CANCELLO-25.5.md`.

| Elemento | Luminanza massima | Perché |
|---|---|---|
| **Riempimento** del nucleo | **L ≤ 48** (`--cy-900`) | ⚠️ riga nuova del 23 agosto 2026. La stesura precedente non nominava il riempimento perché il nucleo non ne aveva: era fatto di soli tratti. Il riferimento invece è fatto di **superfici** — i suoi campi scuri misurano L 43,3 e 45,2 — e senza una riga che le governi la prima superficie che qualcuno aggiunge non ha un tetto |
| Tratto del nucleo, stato di riposo | **`--cy-700`, L 100** ~~L ≤ 48~~ | deve leggersi nelle fessure, non attraverso il testo. Il riferimento misura le proprie bande chiare a media 92–125: `--cy-700` è il gradino della scala che ci cade dentro |
| Tratto del nucleo, anello attivo | **`--cy-500`, L 181** ~~`--cy-700`~~ | **un solo anello per volta**, e la regola vale adesso più di prima: a riposo il nucleo è già a L 100, quindi l'anello attivo deve staccare da lì e non dal nero. ⚠️ La stesura diceva «L ≤ 92»: misurato in Rec. 709 su 0–255, `--cy-700` vale **100**. Il token è giusto, il numero no — e un numero sbagliato accanto a un token è il modo in cui qualcuno un giorno cambia il token per far tornare il numero |
| Riempimento del pannello sopra | **L ≥ 31** (`--fill-1`) | il testo ha bisogno di un fondo, non di un velo |
| Testo del pannello | L 224 (`--txt-primary`) | rapporto ≥ 7:1 sul composito |
| **Il marchio** (§25.13) | **`--cy-700`, L 100** | è un nome, non un dato. Deve leggersi e non deve vincere sul testo dei pannelli |

> **⚠️ Difetto aperto, misurato il 22 agosto 2026.** `desk/sfondo.js:177` dà al
> marchio `--icona-viva` (L 219). Contro il pavimento `--bg-void` fa **13,3:1**:
> è il testo **più luminoso dello schermo**, più del testo dei pannelli. È 2,2
> volte il tetto dell'anello attivo e 4,6 volte quello del tratto a riposo.
> `--cy-700` sullo stesso pavimento fa **3,43:1** — sopra il 3:1 che AA chiede
> a un corpo grande, che è ciò che il marchio è. Vedi §25.13.

**Il nucleo non usa mai `--cy-100`.** È il livello del testo dei pannelli, e il
dato sta nei pannelli. Un nucleo che compete col dato è decorazione, ed è il
confine con la Famiglia B.

⚠️ **`--cy-500` era vietato fino al 23 agosto 2026, e adesso è ammesso a UNA
condizione**: solo sull'anello attivo, **uno per volta**. Non è un allentamento
della regola di sopra — è la stessa regola su una scala traslata. Ciò che la
teneva non era il valore del token: era che il nucleo restasse **un gradino
sotto** il testo che gli sta davanti. `--cy-500` (L 181) contro `--txt-primary`
(L 224) quel gradino ce l'ha ancora; su un anello solo, che è una frazione della
superficie, non c'è competizione con una colonna di testo.
Il giorno che qualcuno accende due anelli insieme, la condizione è saltata e
questa riga va riletta — non aggirata.

Nessun `filter`, nessun `drop-shadow`, nessun bloom. Invariante 19 vale qui più
che altrove, perché lo sfondo è esattamente il posto dove la tentazione arriva.

---

## 25.6 Che cosa mostra, e quando si muove

**Riferimento visivo**: `famiglia-a/12-logo-anelli-concentrici.png`. Guardare
tre cose: i varchi sono tutti di ampiezza diversa, i centri non coincidono, e la
ghiera più interna è **incisa e ferma** — è la scala contro cui si legge il
movimento delle altre.

Il componente esiste: `ui/src/anim/rings.js`, quattro anelli SVG mossi da
anime.js più una ghiera fissa, periodi 46/74/120/233 s, versi alternati,
varchi tutti diversi. **Non va riscritto.** Va spostato di strato.

Anche l'alimentazione esiste: `alimentaAnelli()` in `moduli.js` compone già
`state.snapshot`, `agent.mesh` e lo stato della connessione. Si sposta in
`presenza.js` senza modifiche.

La mappa fra stato reale e movimento:

| Stato | Sorgente | Nucleo |
|---|---|---|
| Core non collegato | `bus.suStato` | **fermo**, `livello="offline"`, scritta `CORE NON COLLEGATO` |
| Inerte | nessun nodo attivo in `agent.mesh` | **fermo**. Il sistema non sta lavorando, e si vede |
| T0 in esecuzione | `agent.mesh` nodo `T0` attivo | ghiera interna, un impulso, poi ferma |
| T1 genera | `agent.mesh` nodo `T1` attivo | anello 46 s in moto |
| T2 attivo | `agent.mesh` nodi T2 | anello 120 s in moto, uno per slot |
| In ascolto | `voce.abilitata` + stato | anello 74 s in moto |
| Sopra soglia §16 | `agent.advisory` | anello esterno a `--amber`, poi `--rust` |

**Se gira, sta lavorando.** È un dato leggibile da tre metri, ed è il motivo
per cui il movimento è ammesso: non è animazione ambientale, è telemetria.

---

## 25.7 Geometria, posizione, riposo

**Dimensione**: diametro = **64 % dell'altezza** dell'area pannelli, cioè
esclusi barra e dock. Non della finestra: il nucleo appartiene alla scrivania,
non al chrome.

**Posizione**: centro geometrico dell'area pannelli. Fisso. Non segue il
puntatore, non si sposta col workspace, non ha parallasse. Un fondo che si
muove è §10.3, «Fondo: immobile».

**Riposo (`Alt+H`)**: `nascondiTutto()` esiste già in `scrivania.js`. Con lo
strato di presenza acquista un significato che oggi non ha: non «schermo
vuoto» ma **JARVIS in attesa**. In riposo, e solo in riposo:

- il nucleo può salire a `--cy-700` sull'anello attivo;
- compaiono le tre righe di stato che oggi stanno nel pannello anelli —
  stato, da quanto, motivo — a `--t-label`, centrate sotto il disco.

Non è un secondo componente. È lo stesso, con `data-riposo="1"`.

---

## 25.8 Budget — la misura viene prima

`SEZIONE-13.md` riporta mediana **16,70 ms**, cioè il vsync. Quel numero dice
«non perdo fotogrammi»; **non dice quanto margine resta**. Un renderer
agganciato al vsync mostra lo stesso valore che ne usi 4 o 16.

`backdrop-filter: blur(16px)` su quattordici pannelli a schermo intero, su una
APU a memoria unificata, è esattamente il carico che consuma un margine
sconosciuto.

**Ordine obbligato, e non è negoziabile:**

1. Strumentare con `performance.measure` il costo per sottosistema — three.js,
   PixiJS, anime.js, layout — e registrare il margine reale su WS01, che è il
   workspace più carico.
2. Accendere il nucleo **senza** `backdrop-filter`, solo con `--vetro`
   traslucido. Rimisurare.
3. Accendere il blur. Rimisurare.

**Ripiego dichiarato in anticipo**, così che sia una decisione e non una
sorpresa: se al passo 3 il margine scende sotto **4 ms**, il blur si toglie e
resta la sola trasparenza. Il nucleo si legge lo stesso; perde morbidezza, non
funzione. Un'interfaccia che salta è peggio di una meno raffinata.

---

## 25.9 Criteri di accettazione

Misurabili. Nessuno di questi si verifica a occhio.

0. **Il nucleo arriva a schermo.** ⚠️ **La metrica è cambiata il 22 agosto
   2026, e il perché vale più della soglia.**

   La prima stesura di questo criterio contava «quanti pixel del nucleo cadono
   sul pavimento libero, in percentuale del pavimento». È una metrica con un
   **tetto che nessuno vede**: il nucleo è una forma a TRATTI, non una
   superficie. Misurato — nucleo scoperto, stessa dimensione di lavoro — dipinge
   **29.957 px** su un disco di Ø502 la cui area è 197.923: il **15,1 %**. Su un
   pavimento di 471.409 px il massimo raggiungibile è quindi il **6,36 %**, e
   una soglia al 5 % sembra lasciare margine mentre ne lascia un punto.

   La metrica giusta ha per denominatore il nucleo, non il pavimento:

   > **% dell'inchiostro del nucleo che arriva a schermo** = pixel dipinti dal
   > nucleo nella scena ÷ pixel che dipingerebbe scoperto, alla stessa
   > dimensione.

   Si misura per differenza: due rendering dello stesso albero, uno col nucleo
   e uno senza, contando i pixel che nel controllo sono esattamente
   `--bg-void`. Il denominatore è lo stesso conto con i pannelli nascosti.

   **Soglia: ≥ 75 %.** Sotto, la scena non lo circonda: lo copre.

1. **Persistenza.** Screenshot dei quattro workspace: il nucleo è presente e
   identico per posizione e scala in tutti e quattro. Diff pixel dell'area
   centrale fra WS01 e WS04 con tutti i pannelli nascosti: **identici**.
2. **Il vetro funziona.** Con i pannelli aperti, l'area coperta da un pannello
   ha luminanza **maggiore** dell'area di fondo adiacente, e il tratto del
   nucleo è **rilevabile** dentro l'area del pannello — dimostra che il vetro
   non è tornato opaco per sbaglio.
3. **Densità.** Il criterio di `DIVARIO-PREMIUM.md` §2 regge: pixel L>60
   **≥ 25 %** su ogni workspace. Il nucleo non deve essere la scusa per
   svuotare la scrivania.
4. **Leggibilità.** Rapporto di contrasto del testo dei pannelli sul composito
   vetro+nucleo: **≥ 7:1** sui tre pannelli più densi — periodica, glifi,
   console.
5. **Il riposo.** `Alt+H`: il nucleo resta, i pannelli spariscono, le tre
   righe di stato compaiono. Screenshot allegato.
6. **Budget.** Margine ≥ 4 ms su WS01 col nucleo acceso, misurato per
   sottosistema e non come intervallo fra fotogrammi.

---

## 25.10 Test da scrivere

| Test | Cosa impedisce |
|---|---|
| `test_presenza_non_e_modulo` | il nucleo non compare in `REGISTRO`, non ha voce nel dock, non ha `cella` |
| `test_presenza_ferma_se_inerte` | a `agent.mesh` senza nodi attivi, **zero** animazioni in moto. È l'invariante 25 resa eseguibile |
| `test_presenza_ferma_se_scollegato` | core assente → nucleo fermo e stato dichiarato |
| `test_vetro_non_opaco` | nessun `background` opaco in `.winbox`, `.wb-body` o in un `.pnl-*` |
| `test_luminanza_nucleo` | nessun tratto del nucleo usa `--cy-500` o `--cy-100` |
| `test_presenza_sopravvive_al_workspace` | `vai(n)` non ricrea né rianima il nucleo |
| `test_z_index_dai_token` | nessun `z-index` letterale nel codice |

---

## 25.11 Cosa non fare

- **Nessuna parallasse, nessun inseguimento del puntatore.** §10.3, «Fondo:
  immobile».
- **Nessun secondo elemento di fondo.** Un nucleo più una griglia più delle
  particelle è la Famiglia B con un altro nome.
- **Niente `three.js` per il nucleo.** È SVG e deve restarlo: forme piatte,
  nitide a ogni scala, e un contesto WebGL in più su tutti e quattro i
  workspace è il costo che §25.8 sta cercando di evitare.
- ~~**Nessun testo dentro il nucleo con i pannelli aperti.**~~ **EMENDATA il 22
  agosto 2026 — vedi §25.13.** La regola era mia e l'avevo scritta senza
  guardare `famiglia-a/12`, che il §25.1 dichiara riferimento di questo stesso
  componente: al centro di quell'immagine c'è **`J.A.R.V.I.S.`** con un filetto
  sotto. La regola resta valida per il testo *di dato*; il marchio è escluso e
  vincolato da §25.13. Un dato in più dentro il nucleo resta vietato.
- **Il nucleo non è il posto dove mettere ciò che non sta nei pannelli.**
  Ogni volta che qualcosa «non trova posto», la risposta è una cella, non lo
  sfondo.

---

## 25.12 Ordine di lavoro

| # | Passo | Costo |
|---|---|---|
| 1 | Ruoli di riempimento — `DIVARIO-PREMIUM.md` §1 | **prerequisito** |
| 2 | Strumentazione del budget per sottosistema, misura di base | 0,5 g |
| 3 | Tre strati in `#scrivania`, token z-index | 0,5 g |
| 4 | `desk/presenza.js`: sposta `rings.js` di strato, sposta `alimentaAnelli()` | 0,5 g |
| 5 | Togliere i tre `background` opachi, introdurre `--vetro` | 0,5 g |
| 6 | Tarare l'opacità col criterio 4, poi il blur col criterio 6 | 1 g |
| 7 | Stato di riposo su `Alt+H` | 0,5 g |
| 8 | I sette test, i sei criteri, `SEZIONE-25.md` | 1 g |

**Totale ~4,5 giorni**, il prerequisito escluso.

---

## Nota — questo si discosta dal riferimento, e la decisione è consapevole

**Nessuna delle dodici immagini di `famiglia-a/` ha un elemento centrale dietro
ai pannelli.** `01-desktop-mcu-completo.png` è una griglia piastrellata senza
sfondo, ogni pixel occupato da un riquadro. Dove un elemento centrale esiste —
`10-globo-gps-locator.png` — è **circondato** dal chrome, non coperto: sta nello stesso piano dei pannelli, non
sotto. Il nucleo dietro appartiene al linguaggio dell'officina — Iron Man 3 —
non a quello della scrivania.

I due obiettivi si combattono: il nucleo vuole spazio libero per farsi vedere,
la densità non ne concede. **La scelta è il vetro**: densità piena, e il nucleo
si legge attraverso i pannelli e nelle fessure. È la sola delle tre uscite che
non paga in densità, ed è quella per cui §10.1 era già scritta.

Registrato qui perché fra sei mesi la domanda «perché c'è un disco dietro tutto
se il riferimento non ce l'ha» avrà una risposta datata.

**Ripiego se il vetro non regge la verifica visiva**: si passa all'opzione C —
il nucleo nella cella centrale, **circondato** dai pannelli come in `10`. È la
disposizione che il riferimento documenta davvero, costa densità e non richiede
né `backdrop-filter` né la rimozione dei fondi opachi. Va deciso al criterio 4
di §25.9, non dopo.


---

## 25.13 Il marchio — la scritta al centro

> **Aggiunta il 22 agosto 2026, dopo un errore mio.** Avevo chiesto di
> rimuovere `J.A.R.V.I.S.` dal centro citando l'invariante 23 («mai dati
> segnaposto») e §25.11. Tutte e due le citazioni erano sbagliate. Un marchio
> non è un dato: non pretende di essere una misura, non ha una sorgente, non
> può essere «vero» o «finto». E il riferimento che §25.1 assegna a questo
> componente — `famiglia-a/12-logo-anelli-concentrici.png` — porta quella
> scritta al centro, con un filetto sotto. Avevo giudicato l'elemento contro
> `famiglia-a/01`, che è lo scatto di una scrivania piena, non il logo.
> Il marchio **resta**. Quello che mancava non era il permesso: era la regola.

### 25.13.1 Che cos'è

Il marchio è **l'unico elemento della scrivania che non porta informazione**.
Esiste perché il nucleo, senza, è una forma geometrica anonima: il riferimento
lo mostra e la ragione si vede a occhio.

Ha quindi bisogno di un recinto stretto, altrimenti diventa il precedente con
cui domani qualcuno mette una seconda scritta decorativa da qualche altra parte
e la giustifica con questa sezione.

### 25.13.2 Le sette regole

| # | Regola | Perché |
|---|---|---|
| 1 | **Uno solo, in tutta l'applicazione.** | Un secondo marchio non è un marchio, è decorazione |
| 2 | **Stringa fissa, `J.A.R.V.I.S.`, non parametrica.** | Una stringa che cambia è un dato, e ricade sotto l'invariante 23 |
| 3 | **Mai in una cella, mai in un pannello, mai nella barra.** | Vive nello strato di presenza (`--z-insegna: 1`) e in nessun altro |
| 4 | **`--cy-700` (L 100), tetto invalicabile.** | §25.5. Oggi è `--icona-viva` a L 219: difetto aperto |
| 5 | **Non si muove, non respira, non pulsa.** | Invariante 25. Un nome che si muove non si legge — già scritto in `sfondo.js:163` e va tenuto |
| 6 | **Testo nel DOM, mai rasterizzato.** | Invariante 20. Oggi è conforme: `<span class="sfd__marchio">` |
| 7 | **`pointer-events: none`, non selezionabile, non è un bersaglio.** | Non è un comando e non deve sembrarlo |

### 25.13.3 Il corpo non è un gradino tipografico, ed è voluto

`sfondo.js:416` calcola il corpo come **il 56,1 % del raggio per lato**,
misurato sul riferimento, e non lo prende da `--t-*`. L'audit `&tokens=audit`
lo segnala in magenta, e ha ragione a segnalarlo: è un valore calcolato.

**È una deroga dichiarata a §11.6 regola 1, non una svista.** Un marchio non si
compone, si disegna: la sua dimensione è una proporzione della geometria che lo
contiene, esattamente come il tratto degli anelli. Un logo legato a un gradino
tipografico si stacca dagli anelli alla prima finestra di dimensione diversa.

Le due condizioni perché la deroga resti tale e non diventi un precedente:

1. **Vale solo per `.sfd__marchio`.** L'audit deve avere un'eccezione
   **nominata**, non una soglia allentata: qualunque altro elemento con corpo
   calcolato resta un errore.
2. **Il fattore `0.561` è documentato dove sta** — lo è già, `sfondo.js:410-414`
   dice da dove viene. Un fattore misurato si contesta; un fattore a occhio no.

### 25.13.4 Lo scudo dietro la scritta

`text-shadow: 0 0 22px var(--bg-void), 0 0 8px var(--bg-void)` **non viola
l'invariante 19**: l'invariante vieta la luce che non esiste, e questo è il
colore del *pavimento*, cioè un'ombra. Toglie contrasto alla nuvola che passa
sotto invece di aggiungerne alla scritta.

Va però ricontrollato quando il marchio scende a `--cy-700`: uno scudo tarato
per L 219 su una scritta a L 100 può ingoiarne i tratti sottili. La verifica è
visiva, §11.7, non una formula.

### 25.13.5 Criterio di accettazione

> Scatto della scrivania a pannelli aperti. Sul ritaglio del solo marchio:
> luminanza media **≤ 105**, contrasto WCAG contro il composito sottostante
> **≥ 3,0:1** e **≤ 5,0:1**. Il tetto superiore conta quanto quello inferiore —
> sopra 5:1 il marchio compete col testo dei pannelli, ed è la ragione vera per
> cui §25.11 lo vietava.
