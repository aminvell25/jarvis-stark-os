# La persistenza del layout — esito · §26.10 punto 1

**Data**: 19 agosto 2026 · **Riferimento**: `SPEC-26-AMBIENTE-UNICO.md` §26.5 e
§26.10, `PERIMETRO-E-DECISIONI.md` §9 · **Precedente**: `TOKENS-RIEMPIMENTO.md`
**Test**: **515 + 216** verdi (erano 476 + 216), di cui **39** nuovi

> **Seconda passata, 19 agosto.** Chiusi i «non verificato» **1, 6 e 7** con
> `scripts/prova-gesti.mjs`: eventi puntatore veri di Playwright, sull'app
> vera. Ha trovato **quattro difetti** che i test non vedevano — R83, R84,
> R85, R86 — e uno ce l'aveva la prova stessa. Vedi in fondo.

> «Un'icona trascinata sul fondo che al riavvio torna al suo posto è peggio di
> un'icona che non si può trascinare.»

Il criterio non è quindi «il file viene scritto». È che **al riavvio la
disposizione ci sia ancora**, e questo documento la verifica riavviando —
prima il core nei test, poi l'applicazione vera.

---

## I cinque vincoli

| | Vincolo | Dove | Prova |
|---|---|---|---|
| a | **Salva il core**, non il renderer | `core/layout.py` | il renderer non ha una via verso il disco: ne ha una verso il socket |
| b | **Non è un tool** | non passa dal registry | `test_non_e_nell_allowlist` |
| c | **Non tocca `settings.toml`** | `paths.data_dir()/layout.json` | file separato, JSON, 0600 |
| d | **Canale stretto, tipizzato** | `LayoutMessage`, `extra="forbid"` | 6 payload rifiutati, uno per specie |
| e | **Differito 500 ms**, debounce | `ui/src/desk/layout.js` | dieci movimenti in 200 ms → **una** scrittura |

### (b) Perché non è un tool, scritto dove serve

`tools/registry.py` è l'allowlist di ciò che **l'LLM invoca**. Questo non lo
invoca nessuno. Le due strade sbagliate si escludono da sole, e stanno scritte
nell'intestazione di `core/layout.py` perché è lì che un domani distratto le
riproporrebbe:

- `side_effect=True` → una conferma a ogni pannello spostato;
- `side_effect=False` → un tool nell'elenco che l'LLM riceve, senza motivo.

### (d) Il canale: cosa cambia, e la proprietà che lo tiene stretto

I due messaggi in ingresso esistenti sono **risposte**: portano l'`id` di una
domanda che il core ha già posto, e non se ne possono inventare. `ws_server.py`
diceva che sarebbero rimasti due «se nessuno dichiara perché ne serve un
terzo», e `test_ws_contract.py` prevedeva:

> «Il giorno in cui questo elenco conterrà un messaggio senza `id`, sarà una
> RICHIESTA, e allora il ponte avrà smesso di essere un ponte.»

Quel giorno è arrivato, e la previsione era **quasi** giusta: manca un terzo
caso. `ui.layout` non ha `id` e non è una richiesta —

> **non chiede un'operazione: dichiara uno stato dell'ambiente.**
> Il core non lo ESEGUE, lo RICORDA.

La proprietà diventa: ogni messaggio in salita è **o** una risposta con l'`id`
di una domanda già posta, **o** una dichiarazione di stato che non nomina
nessuna operazione. Il secondo ramo non è una scappatoia — è verificato:

- il ponte costruisce il messaggio **campo per campo** da un elenco fisso, e un
  test asserisce quell'elenco e vieta lo `...spread`;
- **il `topic` lo mette il ponte, non il renderer**: chi sta dall'altra parte
  sceglie dove stanno le sue finestre, non a chi parla;
- lo schema rifiuta un campo in più, un id che assomiglia a un percorso, una
  coordinata assurda.

È il pattern che erediteranno `Alt+Spazio`, `Esc`, le scene e il catalogo:
**una funzione per intenzione, coi campi che quella intenzione ha**, mai un
`manda(topic, oggetto)` generico.

### (e) Il debounce, e perché non è lui la difesa

500 ms dopo l'ultimo movimento: con un throttle si scriverebbe **durante** il
trascinamento e sul disco finirebbero venti posizioni che nessuno ha scelto.

⚠️ **Ma il freno del renderer non è una difesa.** Il renderer aspetta perché è
educato; un renderer compromesso — e in Fase 6 ne gira uno con `<webview>`
dentro — sceglie di non esserlo. Il freno che conta è nel core: un minimo di
250 ms fra due scritture, e ciò che è in eccesso **si fonde, non si perde**.
Scartare vorrebbe dire buttare l'ultima posizione di un trascinamento veloce,
che è proprio quella che l'utente sta guardando.

---

## R82 — trovato dal vivo, e sarebbe passato per buono

I sei test richiesti erano verdi. Il giro completo, no.

Metodo: scrivo a mano `telemetria` a 500,300 nel file, avvio l'applicazione,
la chiudo, rileggo il file. Se il ripristino è avvenuto, il pannello si
risalva lì; se non è avvenuto, torna alla cella dichiarata.

```
telemetria dopo il riavvio:  4 42     → NON ripristinato
```

**La prima ipotesi era che fosse il metodo di prova**, e in parte lo era:
`npm run scrivania` chiama `vai(1..4)` per fotografare i quattro workspace, e
`vai()` ricompone. Rifatto con l'applicazione in modalità normale: **stesso
esito.** Quindi il difetto c'era davvero.

Isolato con un esperimento invece che con una congettura — tolta una riga,
riprovato, rimessa:

```js
window.addEventListener("resize", affianca);   // §13
```

```
senza quella riga:  500 300  → RIPRISTINATO
con quella riga:      4  42  → cancellato entro un secondo dall'avvio
```

§13 poteva permettersela: non c'era niente da conservare, e «l'area è
cambiata» e «rimetti tutto nelle celle dichiarate» erano la stessa cosa. Con
la persistenza sono due operazioni diverse, e confonderle **cancella la
disposizione dell'utente** — la finestra si assesta dopo il caricamento, il
`resize` scatta, e `affianca()` disfa il ripristino appena fatto.

**Correzione**: il ridimensionamento ora `riadatta()` — chi è rimasto fuori
rientra, chi era dentro **non si muove di un pixel**. Ricomporre resta un
gesto esplicito, `Alt+T`. È anche ciò che §26.2 prescrive: *«nessun riordino
automatico: una pila che si riorganizza da sola è la cosa che rende un
ambiente inabitabile»*.

Un test sul sorgente impedisce che torni. ⚠️ E ha sbagliato al primo giro,
scattando sul **proprio commento** — la spiegazione di un divieto contiene per
forza la riga che vieta. Corretto togliendo i commenti prima di guardare, come
già fa il test dell'invariante 29.

---

## Il ripristino sopravvive ai cambiamenti

| Caso | Comportamento | Dove |
|---|---|---|
| pannello che non esiste più in `moduli.js` | **ignorato**, log `info` | `apri()` ritorna `null`, `ripristina()` lo conta fra gli ignorati |
| posizione fuori dall'area | **riportata dentro**, mai scartata | `adatta()` nel core, `dentroArea()` nel renderer |
| file assente | disposizione di `moduli.js`, come oggi | `carica()` → `Layout()` vuoto |
| file corrotto | rinominato `.corrotto`, si riparte, **dichiarato** | `_metti_da_parte()`, e nello snapshot |

**Due tagli, due ragioni diverse**, e non è ridondanza:

- il **core** taglia quando riceve, contro l'area che il renderer dichiara: un
  renderer che sbaglia non lascia dietro un file che il prossimo avvio dovrà
  correggere;
- il **renderer** taglia quando applica, contro l'area di **adesso**: fra due
  avvii lo schermo può essere cambiato, e il core non lo sa finché nessuno
  glielo dice.

E non basta «dentro»: la testa del pannello è la maniglia con cui lo si
riprende, quindi ne devono restare almeno 80 px a schermo. Un pannello con un
pixel visibile è irraggiungibile quanto uno fuori.

---

## Cosa si salva

Per ogni pannello aperto: `id`, posizione, dimensione, `z`, se è massimizzato.
Più la scena attiva, e l'area in cui la geometria è stata misurata.

Lo schema ha **già il posto** per le icone libere e le cartelle contenitore di
§26.5 — `IconaLibera`, `CartellaLibera` — vuoti, perché non c'è ancora chi li
produca. Aggiungere un campo a uno schema versionato dopo che il file esiste
sul disco di qualcuno costa una migrazione, e questo file esiste da oggi.

⚠️ **Una cartella dell'ambiente non è una cartella del filesystem**: nessun
percorso entra in questo schema, solo id. §26.5 lo dice, ed è la distinzione
che impedisce di cancellare qualcosa credendo di riordinare una scrivania.

---

## La verifica, dal vivo

Core fermato e riavviato col codice nuovo, `layout.json` cancellato:

```
1. layout.json prima            non esiste
2. dopo un avvio dell'app       13 pannelli · area 1536x764
                                telemetria x 4 y 42 z 11 · agenti x 644 …
3. scritto a mano 500,300 e riavviata l'app
   telemetria dopo:             500 300   → RIPRISTINATO
```

Il punto 2 prova la catena in scrittura per intero — renderer → preload →
ponte → socket → core → disco — e il punto 3 quella in lettura, compreso il
`carica()` che il core rifà a ogni client che si collega.

---

## ❌ NON VERIFICATO

1. ~~**Nessun trascinamento fatto con un mouse.**~~ ✅ **CHIUSO** con
   `scripts/prova-gesti.mjs`: eventi puntatore veri, sull'app vera, e il
   criterio 4 di §26.9 con esso. Resta vero che a muovere il puntatore è
   Playwright e non una mano: nessuno ha ancora *guardato* il trascinamento
   mentre avviene, e una prova non vede lo scatto, il ritardo percepito o il
   cursore sbagliato.
2. **Le icone libere e le cartelle non esistono.** Lo schema ha il posto, e il
   posto è vuoto. Che quei campi siano i campi giusti lo dirà il punto 5.
3. **Un solo schermo, una sola risoluzione.** 1536×827 e 1536×764. Il caso
   che `adatta()` esiste per gestire — un layout salvato su uno schermo grande
   e riaperto su uno piccolo — l'ho provato coi numeri, non cambiando monitor.
4. **Il `.corrotto` si sovrascrive.** Un solo file, non una collezione
   numerata: due guasti di fila e il primo si perde. È una scelta — una
   directory che accumula file rotti è un altro modo di riempire un disco in
   silenzio — ma è una scelta, non una proprietà verificata.
5. **Il freno del core non è stato provato sotto attacco.** Ho verificato che
   due salvataggi ravvicinati toccano il disco una volta sola e che il secondo
   non si perde. Non ho scritto un client che martelli il socket per un minuto
   per misurare quante scritture ne escono davvero.
6. ~~**`window.__layout` non è letto da nessuno.**~~ ✅ **CHIUSO**: è
   l'appiglio da cui `prova-gesti.mjs` conta le scritture verso il core.
7. ~~**`riadatta()` non ha una prova visiva.**~~ ✅ **CHIUSO**: misurato e
   **fotografato**, e la foto ha detto una cosa che i numeri non dicevano —
   vedi sopra.

### E tre nuovi, dalla seconda passata

8. **Un solo percorso di trascinamento.** Venti passi in linea retta, sempre lo
   stesso pannello, sempre a velocità costante. Non ho provato un
   trascinamento lentissimo, uno interrotto da `pointercancel`, due dita, o il
   caso in cui il puntatore esce dalla finestra mentre il tasto è premuto.
9. **L'aggancio è provato al centro di ogni bordo.** Gli angoli no: `zonaAggancio()`
   prova `sinistra` prima di `alto`, quindi l'angolo in alto a sinistra
   aggancia a sinistra. È una scelta implicita che nessuno ha deciso.
10. **R85 è corretto, ma la causa in WinBox non è stata capita fino in fondo.**
   So che la sua contabilità del ripristino divergeva dalla nostra e ho smesso
   di dipenderne. **Non** ho letto il suo sorgente per capire *quale* delle
   nostre chiamate la sporcasse. Se un giorno servisse un'altra funzione di
   WinBox che usa quella contabilità, quel lavoro va fatto.


---

# Seconda passata — il gesto, con un puntatore vero

## Perché sull'app e non sulla galleria

R82 era la **seconda** volta che un ambiente di prova più permissivo di quello
reale approvava codice rotto. La prima fu il CSP di PixiJS: i glifi giravano in
galleria, che non aveva CSP, e nell'app non partivano — **da quattro fasi**.

Quindi `scripts/prova-gesti.mjs` avvia `app/main.js` con Electron vero, socket
vero, core vero. E muove il puntatore con `page.mouse.down/move/up` di
Playwright, che entra nella pipeline di input del browser:
`dispatchEvent(new PointerEvent(...))` non prova né `setPointerCapture` né ciò
che succede fra due clic — che è esattamente dove stavano due dei quattro
difetti.

La regola è ora nel metodo, come **passo 0 di §11.7**.

## Cosa dice, adesso

| | Prova | Esito |
|---|---|---|
| 1 | premere sulla testa, muovere in 20 passi, rilasciare | ✅ il pannello è dove l'ho lasciato |
| 2 | 20 `pointermove` in ~700 ms | ✅ **una** scrittura, con l'**ultima** posizione |
| 3 | doppio clic → massimizza (1536×753); secondo → torna | ✅ a (104,314) 632, dov'era |
| 4 | trascinare entro 24 px da ciascuno dei 4 bordi | ✅ aggancia a metà, tutti e quattro |
| 5 | trascina · **chiudi l'app** · riapri | ✅ (632,384) prima, su disco, e dopo |
| 6 | ridimensionare la finestra | ✅ si muove **solo** chi era fuori |

Il punto 5 è il **criterio 4 di §26.9**, e con questo è chiuso.

## I quattro difetti che ha trovato

### R83 — l'area era congelata alla creazione della cornice

`creaCornice({ area })` e `armaManiglia(testa, cornice, area)` chiudevano sopra
un **valore**. Le zone d'aggancio e i limiti di WinBox restavano quelli di
allora: misurato, in una finestra da 1536 un pannello agganciato a sinistra
diventava largo **400** invece di 768 — la metà di uno schermo che non esisteva
più.

Nell'app non si vedeva perché `main.js` massimizza prima che la pagina carichi.
Si vede appena l'utente ridimensiona la finestra, cioè sempre, prima o poi.
Ora `misuraArea` è una funzione, e `riadatta()` rimette anche i limiti a WinBox.

### R84 — il `pointerdown` de-massimizzava dentro il doppio clic

`if (cornice.massimizzata) alterna(cornice)` in `pointerdown`. L'intenzione era
giusta — massimizzata, si riprende in mano — il momento no: scattava alla
**prima** pressione del doppio clic. Il pannello si rimpiccioliva sotto il
puntatore e il secondo clic finiva su ciò che c'era sotto; in una passata ha
premuto il `⊟` di un vicino e ha minimizzato il pannello che stavo misurando.

Un gestore di finestre riprende in mano una finestra massimizzata quando la si
**trascina**, non quando la si preme. Spostato in `pointermove`, oltre una
soglia di 4 px.

### R85 — WinBox ripristinava una geometria mai avuta

Con R84 corretto, il doppio clic massimizzava ma non tornava. Strumentato passo
per passo:

```
prima                 box (199,314) 325×112   max=false
dopo il 1º doppio     box (199,314) 325×112   max=true    dom (0,47) 1536×742
dopo il 2º doppio     box   (0,47)  800×239   max=false
```

`box.maximize(false)` riportava il pannello a **800×239**, una geometria che in
quella sessione non aveva mai avuto. WinBox tiene la propria contabilità del
ripristino, e noi gli muoviamo le finestre sotto i piedi con `move()` e
`resize()` — nel trascinamento, nell'aggancio, nel ripristino del layout. Le
due contabilità divergono.

Ora la geometria di ritorno **ce la ricordiamo noi**. Costa una riga, toglie una
dipendenza da un dettaglio interno di una libreria, ed è lo **stesso numero**
che salviamo su disco: «torna dove era» e «riapri dove l'avevi lasciato»
seguono la stessa geometria.

> Nota utile per chi legge il codice: mentre un pannello è massimizzato,
> `box.x/y/width/height` tengono la geometria di **ripristino**, non quella a
> schermo. È corretto — è quella che serve per tornare indietro, ed è quella
> che va salvata insieme al flag — ma allora «ha massimizzato?» non si chiede a
> quei numeri: si chiede al rettangolo del DOM.

### R86 — lo `z` si salvava e non si riapplicava mai

Il campo era nello schema, nel messaggio, sul disco. E nessuno lo rimetteva:
al riavvio la pila tornava nell'ordine di creazione, e un pannello portato in
cima finiva sotto. §26.2 dice *«nessun riordino automatico: una pila che si
riorganizza da sola è la cosa che rende un ambiente inabitabile»* — e riaprire
era il momento in cui si riorganizzava da sola.

Trovato in modo indiretto, ed è il modo più istruttivo: **il trascinamento non
muoveva niente**, perché la pressione finiva sul pannello rimasto sopra.

Ora `ripristina()` va in ordine di `z` crescente e usa il **fuoco**, non un
`z-index` scritto a mano: due contabilità della stessa pila sono già costate
R85.

## Un difetto ce l'aveva la prova

La prima stesura partiva da ciò che aveva lasciato l'esecuzione precedente — un
pannello già agganciato, o massimizzato, o sotto un altro — e due esecuzioni
identiche davano esiti diversi. **Una prova che dipende dai residui della prova
prima non è una prova.**

Ora mette da parte `layout.json`, lavora da zero, e lo rimette a posto alla
fine: è l'ambiente dell'utente, non materiale di consumo.

E due aggiustamenti di metodo, entrambi per essere *fedeli* e non più ostili:

- la finestra si massimizza **subito**, prima che la scrivania componga — sotto
  Playwright nasce a 800×600, e provare su una finestra più piccola di quella
  vera sarebbe di nuovo un ambiente diverso dal reale;
- il doppio clic si fa a 40 px dal bordo sinistro della testa, non al suo
  centro: `locator.dblclick()` punta al centro, e su un pannello massimizzato
  quel punto sta a metà schermo. Un utente afferra la barra dove la vede.

## `riadatta()`, guardato e non solo contato

Screenshot in `shots/gesti/riadatta-prima.png` e `-dopo.png`, finestra da
1536×752 a 1100×588.

**Ciò che i numeri dicevano**: si è mosso solo `anelli`, che era l'unico fuori,
e tutti restano raggiungibili.

**Ciò che si vede in più**: `STATO AGENTE` rientra sì, ma **solo fino alla
soglia minima** — ne restano ~95 px, e il resto è tagliato dal bordo. È la
regola che ho scritto io (`minimo_visibile = 80`: quanto basta perché la testa
sia afferrabile), applicata alla lettera. `MESH AGENTI` e `CONSOLE` restano
larghi più dell'area e sporgono a destra: `dentroArea()` limita la larghezza
all'area e la posizione, ma non impone `x + larghezza ≤ area`.

Non è un difetto rispetto a ciò che ho dichiarato — è ciò che ho dichiarato,
guardato. Ed è una decisione da rivedere quando i pannelli si vestiranno per
l'ambiente nuovo (§26.10 punto 7), perché «raggiungibile» e «usabile» non sono
la stessa cosa. **I numeri non l'avrebbero mai detto.**

## `window.__layout` adesso serve a qualcosa

Era impalcatura che nessuno leggeva. Ora è l'appiglio da cui la prova misura
**quante volte il renderer ha parlato al core** — cosa che dal DOM non si vede —
e porta anche l'esito del ripristino. Se un giorno `prova-gesti.mjs` smettesse
di leggerla, quella riga va tolta, non lasciata a invecchiare.

---

## Riepilogo

| | |
|---|---|
| Test | **515 + 216** verdi (erano 476 + 216), **39** nuovi |
| Vincoli richiesti | **5 su 5** |
| Funzioni del preload | 4 → **5**, la quinta dichiarata nel codice |
| Tipi in ingresso al core | 2 → **3**, e il terzo è il primo che il renderer INIZIA |
| Difetti trovati **dal vivo** e non dai test | **5** — R82, R83, R84, R85, R86 |
| Difetti trovati nelle prove appena scritte | **2** — una scattava sul proprio commento, l'altra dipendeva dai residui della precedente |
| «Non verificato» chiusi dalla seconda passata | **3 su 7** — 1, 6 e 7 |
| Criterio 4 di §26.9 | **chiuso** |
| Regole aggiunte al metodo §11.7 | **1** — il passo 0 |
| Tool aggiunti all'allowlist | **0**, ed è il punto |
| Dipendenze aggiunte | **nessuna** |
