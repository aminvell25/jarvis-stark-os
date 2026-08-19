# La persistenza del layout — esito · §26.10 punto 1

**Data**: 19 agosto 2026 · **Riferimento**: `SPEC-26-AMBIENTE-UNICO.md` §26.5 e
§26.10, `PERIMETRO-E-DECISIONI.md` §9 · **Precedente**: `TOKENS-RIEMPIMENTO.md`
**Test**: **506 + 216** verdi (erano 476 + 216), di cui **30** nuovi

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

1. **Nessun trascinamento fatto con un mouse.** Ho mosso i pannelli
   riscrivendo il file e con `move()`; il gesto vero — premere sulla testa,
   trascinare, rilasciare — non l'ho eseguito, e con esso non ho verificato
   che il debounce si comporti bene su una sequenza di `pointermove` reale.
   È il criterio 4 di §26.9, e resta aperto finché non c'è una mano.
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
6. **`window.__layout` non è letto da nessuno.** Il renderer registra quanti
   pannelli ha ripristinato e quanti ignorati, e nessun test lo guarda: la
   prova del ripristino passa dal file, non da quell'appiglio. Serve al
   prossimo passo, o va tolto.
7. **`riadatta()` non ha una prova visiva.** Il test guarda il sorgente. Che
   ridimensionando la finestra i pannelli si comportino come dico — chi era
   dentro fermo, chi era fuori rientra — l'ho ragionato, non fotografato.

---

## Riepilogo

| | |
|---|---|
| Test | **506 + 216** verdi (erano 476 + 216), **30** nuovi |
| Vincoli richiesti | **5 su 5** |
| Funzioni del preload | 4 → **5**, la quinta dichiarata nel codice |
| Tipi in ingresso al core | 2 → **3**, e il terzo è il primo che il renderer INIZIA |
| Difetti trovati **dal vivo** e non dai test | **1** — R82, che avrebbe reso inutile tutto il resto |
| Difetti trovati nel test appena scritto | **1** — scattava sul proprio commento |
| Tool aggiunti all'allowlist | **0**, ed è il punto |
| Dipendenze aggiunte | **nessuna** |
