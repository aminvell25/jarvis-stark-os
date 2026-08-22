# 26. Ambiente unico — catalogo, icone libere, scene

> Da aggiungere a `docs/SPEC.md` dopo §25. Rev proposta: **5.11**.
> **Supera §13** nel modello a quattro workspace. Vedi ADR-010.

---

## 26.1 Che cosa cambia, in una riga

Da **quattro scrivanie separate** a **una sola**, con pannelli che si
sovrappongono come carte, un catalogo in basso da cui si tira fuori quello che
serve, icone che restano dove le si lascia, e JARVIS che sa disporre tutto in
una scena quando glielo si chiede.

---

## ADR-010 — Una scrivania, non quattro

### Contesto

§13 prescrive quattro workspace con dominio e accento (`01 Sistema`,
`02 File`, `03 Web`, `04 3D`), e `Alt+1…4` per passare fra loro. È stato
costruito fedelmente in `desk/scrivania.js` e `desk/moduli.js`.

All'uso si è rivelato sbagliato: quattro pagine significano che **tre quarti
del sistema è sempre invisibile**, e che ogni informazione va cercata invece
che vista. Il riferimento `famiglia-a/01` non ha pagine: ha una superficie
sola, densa, dove tutto convive.

### Decisione

**Una sola scrivania.** I quattro domini di §13 sopravvivono come
**categorie del catalogo** (§26.3), non come pagine: restano un modo di
ordinare, smettono di essere un modo di nascondere.

`Alt+1…4` non cambia pagina: **evidenzia** nel catalogo la categoria
corrispondente. La barra superiore mostra i quattro accenti come filtri, non
come schede.

### Conseguenze

- `moduli.js`: il campo `ws` diventa `categoria` e non governa più la visibilità.
- `scrivania.js`: `vai(n)` non compone e scompone — filtra.
- La cella dichiarata di ogni pannello diventa la sua **posizione iniziale**,
  non la sua gabbia: da lì in poi il pannello si sposta e si sovrappone.
- Chi apre tutto insieme ottiene una scrivania affollata. È il punto.

---

## 26.2 Pannelli sovrapposti — e l'ombra che era già scritta

### La correzione

Il riferimento **non è una griglia piastrellata**. Ingrandendo l'angolo in
basso a sinistra di `famiglia-a/01` si vede che il riproduttore video è una
**carta con ombra portata** che galleggia sopra il pannello dietro, e che il
pannello con le linguette copre il bordo del riproduttore sotto.

### La contraddizione da sciogliere

Tre righe del progetto dicono cose diverse:

| Dove | Cosa dice |
|---|---|
| Invariante 19 | «ZERO drop-shadow. Solo inset box-shadow» |
| §10.1 `.jarvis-panel` | `box-shadow: … , 0 26px 60px rgba(0,0,0,.5)` — **un'ombra portata vera** |
| `app.css` | `.winbox { box-shadow: none }` — la spegne |

§10.1 aveva ragione: senza un'ombra esterna due carte sovrapposte diventano
una macchia sola. L'invariante 19 nasceva contro il **glow** — l'alone
luminoso della Famiglia B — e ha travolto anche l'ombra, che è il contrario:
l'alone aggiunge luce che non esiste, l'ombra toglie luce dove un oggetto ne
copre un altro.

### Decisione

**L'invariante 19 si riformula così:**

> ZERO glow, ZERO bloom, ZERO alone luminoso. L'ombra portata è ammessa
> **solo** per separare due superfici sovrapposte, nera, senza colore, e con
> la ricetta di §10.1. Nessuna ombra su un elemento che non ne copre un altro.

E `app.css` smette di spegnerla.

### Come si comportano

- Il pannello che riceve il fuoco sale in cima e prende `--cy-700` sulla
  cornice (3,03:1 di contrasto, misurato).
- Gli altri restano dove sono. **Nessun riordino automatico**: una pila che si
  riorganizza da sola è la cosa che rende un ambiente inabitabile.
- L'ombra è la stessa per tutti: la profondità la dice la sovrapposizione, non
  un'ombra più grande.

---

## 26.3 Il catalogo — la barra in basso

Opzione **B** del confronto: **non ancorato a piena larghezza**. È un pannello
nella parte centro-bassa, come nel riferimento, con le cartelle che gli
galleggiano accanto.

### Anatomia, misurata su `famiglia-a/01`

```
┌ ◀ ▶  [───── percorso ─────] [── percorso ──]              ┐   🗀 C.02    🗀 H.33_1
│  ╱ MODULI ╱ FILE ╱ SCENE ╱ SISTEMA ╱                      │     .RENDERS   .CORE
│                                                            │
│   ▨  ▨  ▨  ▨  ▨  ▨  ▨  ▨  ▨  ▨  ▨  ▨  →  →  →            │   🗀 V4.22   🗀 W.24
│                                                            │     .ACC_NEW   .SHARE
│            ◤━━━━━━━━━━━━━━━━━━━━━━━◥                       │
│              💬   ✉   🔍   🕐   F°                          │
└────────────────────────────────────────────────────────────┘
```

| # | Elemento | Valore misurato |
|---|---|---|
| ① | Frecce `◀ ▶` di navigazione | |
| ② | Due campi percorso **riempiti** | `#565d63` **L 92** |
| ③ | Linguette a **separatore diagonale** | fondo L 37, testo L 96 |
| ④ | Griglia di icone, scorrevole | fondo L 17–19 |
| ⑤ | **Plinto in prospettiva** con le icone in evidenza | icone `#a2adb1` **L 171**, picchi **L 216** |
| ⑥ | Cartelle manila 2×2, **fuori** dal pannello | `#ba946f` **L 153** |

### Le quattro linguette sono le categorie — e il riferimento le ha già

Nel film le linguette dicono `ANN / MODULE / FILES / SUB F`. **`MODULE` e
`FILES` sono letteralmente due categorie di un catalogo misto.** Non è una
coincidenza da imitare: è la conferma che il modello giusto è uno solo.

| Linguetta | Contiene | Sorgente |
|---|---|---|
| `MODULI` | gli otto moduli di §13 | `moduli.js` |
| `FILE` | i file veri sotto le radici consentite | `tools/files.py` → `fs.list` |
| `SCENE` | le composizioni salvate (§26.6) | impostazioni |
| `SISTEMA` | doctor, impostazioni, cestino | registry |

Questo **unifica la barra delle applicazioni e il file manager**, che erano due
richieste separate. Sono lo stesso contenitore con due linguette.

### Le icone

**Riempite, non a contorno.** È la differenza singola più grande fra il dock
del riferimento e quello attuale:

| | icone | superficie accesa della fascia |
|---|---|---|
| dock del film | **L 171–216** | 26,2 % |
| dock di oggi (`ws-01`) | testo a L 96 | **2,8 %** |

Serve un token nuovo, perché nessuno di quelli esistenti arriva lassù senza
essere il colore del dato:

```css
--icona:      #a2adb1;   /* L 171 — riempimento delle icone del catalogo */
--icona-viva: #d4dcdf;   /* L 216 — icona sotto il puntatore o selezionata */
```

`border-radius` resta **0**: nel riferimento le icone sono appena stondate e a
quella dimensione non si legge. L'invariante 18 non si tocca per un dettaglio
che non si vede.

**Il plinto è in prospettiva** — una lastra trapezoidale, più larga davanti.
È una trasformazione CSS 3D, la stessa tecnica di §11.4 già usata per i piani
d'archivio e la board. È l'elemento che più fa leggere «sistema operativo» e
non «riga di bottoni».

#### ⚠️ Il plinto è il LANCIO RAPIDO, non l'indice — deciso il 22 agosto 2026

Questa sezione diceva il contrario, e va corretta perché la contraddizione è
diventata visibile appena i moduli sono passati da otto a nove.

La lettura precedente era: *il plinto è la barra delle applicazioni, e una
barra delle applicazioni mostra le applicazioni*. Da lì un tetto di cinque
icone — quante ne mostra il riferimento — e da lì il difetto: **con nove
moduli, i quattro fuori dal taglio non erano raggiungibili dal plinto in
nessun modo.** Non erano nascosti dietro un gesto: non c'erano.

Le uscite possibili erano tre, e la scelta è stata fatta guardando che cosa
compare a schermo:

| | che cosa fa | perché no / perché sì |
|---|---|---|
| plinto fisso col massimo che ci sta | allarga il plinto finché tutte entrano | ruba alla griglia, che §26.3 ha già dovuto difendere due volte |
| giostra **più un registro** tabellare accanto | l'elenco completo in tabella nella linguetta MODULI | gli stessi nove nomi comparirebbero **tre volte** a schermo: griglia, registro, plinto |
| **giostra sola** ✅ | quattro in vista, le altre a un giro | l'elenco completo c'è già, ed è la griglia |

**La decisione, e cambia che cosa il plinto PROMETTE:**

> Il plinto non è l'indice e non dichiara di esserlo. È il **lancio rapido**:
> ne mostra quattro per volta su una giostra, e le altre si raggiungono
> girando. L'indice completo è la **griglia**, che è sempre a schermo nella
> stessa finestra e che elenca tutto senza gesti.

Il tetto sparisce: la giostra le porta tutte. Ciò che sparisce è la *pretesa*
di mostrarle tutte insieme, che era la fonte del difetto.

⚠️ **«I preferiti» oggi sono l'ordine di dichiarazione, e va detto.** Non
esiste un modo di marcare un modulo come preferito, e inventarne uno — i più
usati, gli ultimi aperti — vorrebbe dire un criterio scelto da chi scrive il
codice invece che dall'utente, cioè un segnaposto (invariante 23). Finché quel
gesto non esiste, la giostra parte dal primo modulo dichiarato in `moduli.js`.

**La geometria, misurata:** quattro piastre in vista, passo di 80 px fra i
centri (`--s-5 + --s-3`), che con piastre da `--s-4` fa 272 px su un bordo
lontano di 399 — il **68 %**, contro il 66 % misurato sul riferimento. Le due
esterne ruotano di 34° e arretrano di 30 px, con la caduta concentrata
(esponente 1,6): con la caduta lineare le interne girano di 11° e le esterne
di 34, e a occhio sono quattro inclinazioni casuali invece di un arco.

**Tutte e quattro le piastre in vista si premono dove sono.** Non c'è una
piastra «a fuoco» che sia l'unica premibile: l'arco dice che poggiano su un
piano, non quale sia quella scelta, e una giostra in cui si preme solo il
centro costringe a due gesti per ogni lancio.

**Aperto = piastra, chiuso = simbolo nudo.** Nel riferimento le cinque icone
del plinto hanno cinque trattamenti diversi, ed è quella varietà a farlo
leggere come una barra delle *applicazioni* e non come una legenda. Da noi la
varietà non si inventa: la porta il solo fatto che una barra delle
applicazioni ha qualcosa da dire.

**I gesti:** la rotella gira di **una** piastra — la giostra ha posizioni
discrete, e un indice a 3,7 non è uno stato in cui si possa restare — e il
trascinamento gira in continuo e si aggancia alla piastra più vicina al
rilascio. È la stessa distinzione di §26.4: la fisica mentre si tocca, uno
stato discreto quando si lascia.

---

## 26.4 Scorrimento a catalogo

Quando le icone superano la larghezza disponibile, la griglia **scorre in
orizzontale**, non va a capo e non rimpicciolisce.

**Requisiti:**

1. **Trascinamento diretto**: si afferra lo sfondo della griglia e la si tira.
   `pointerdown / pointermove / pointerup`, non `drag` HTML5 — l'API nativa non
   permette di controllare l'anteprima e si comporta male con elementi resi a
   mano. `cornice.js` usa già questo schema per le finestre.
2. **Inerzia**: al rilascio il catalogo continua con la velocità dell'ultimo
   tratto e decelera. **È animazione con una causa** — la causa è il gesto —
   quindi l'invariante 25 regge. Decelerazione esponenziale, si ferma sotto
   0,05 px/ms.
3. **Nessuna barra di scorrimento di sistema.** `scrollbar-width: none` e i
   selettori `::-webkit-scrollbar`: le scrollbar native sono il tradimento più
   immediato dell'illusione, e su `app-fase9.png` si vedevano.
4. **Indicatore di posizione**: una tacca sottile sotto la griglia, larga in
   proporzione a quanto è visibile. Non una scrollbar: un indicatore.
5. **Rotellina**: scorre in orizzontale, senza `shift`.

### Quale motore, per quale pezzo

L'invariante 9 dice **un solo motore: anime.js v4**. Non significa che tutto
passi da lì: significa che nessun secondo motore esiste. Il confine è netto —
**anime.js per ciò che ha un inizio e una fine, CSS per ciò che è uno stato.**

| Cosa | Con che cosa | Perché |
|---|---|---|
| Entrata delle icone all'avvio | **anime.js** `stagger(60)` | è già prescritto: §10.4, riga «Dock» |
| Inerzia dello scorrimento | **anime.js** — bersaglio calcolato dalla velocità al rilascio, ease `out` | tiene un motore solo invece di scrivere fisica a mano in `requestAnimationFrame` |
| Apertura e chiusura del catalogo | **anime.js** su `clipPath` | stessa ricetta di WinBox, §10.4 |
| Comparsa del plinto | **anime.js** | ha un inizio e una fine |
| **Hover e pressione delle icone** | **transizione CSS**, mai anime.js | allocare un oggetto animazione a ogni passaggio del puntatore su venti icone è il modo esatto di sforare i 4 ms di §10.4 |
| Evidenza della categoria filtrata | **transizione CSS** | è uno stato, non un evento |

⚠️ Nessuna di queste è animazione ambientale: ognuna risponde a un gesto o a un
comando. L'invariante 25 regge, ma va riverificata a ogni aggiunta — il
catalogo è il posto dove la tentazione di far «respirare» qualcosa arriva per
prima.

**Budget**: il trascinamento è `transform: translateX()` su un contenitore
solo, mai `left` — cambia solo la composizione, non il layout. Deve restare
sotto i 4 ms di §10.4 assegnati ad anime.js e al layout.

---

## 26.5 Icone libere sul fondo, e cartelle contenitore

### Trascinare fuori

Un'icona trascinata **fuori** dal catalogo e lasciata sul fondo della scrivania
ci resta. Diventa un'icona libera, come le cartelle manila del riferimento.

Regole:

- L'icona nel catalogo **non sparisce**: il catalogo è l'indice, la scrivania è
  il piano di lavoro. Un indice a cui si tolgono le voci smette di essere un
  indice.
- Un'icona libera si trascina, si apre con doppio clic, si rimuove
  trascinandola sul catalogo o dal menu contestuale.
- Le icone libere stanno **sotto** i pannelli (`--z-pannelli`) e **sopra** il
  nucleo di §25 (`--z-presenza`). Un terzo valore: `--z-icone: 5`.

### Cartelle contenitore

Una cartella manila sul fondo contiene altre icone.

- Lasciare un'icona **sopra** una cartella la mette dentro. La cartella si
  illumina a `--manila` più chiaro mentre il puntatore è sopra.
- Aprire una cartella la mostra come **pannello** — non una finestra a parte:
  un pannello del sistema, con l'anatomia a cinque parti di §10.2.
- Una cartella mostra **quante cose contiene**, sempre. Zero è uno stato
  esplicito, non un'assenza (invariante 23).

⚠️ **Le cartelle del catalogo NON sono cartelle del filesystem.** Sono
raggruppamenti dell'ambiente. Una cartella che contenga file veri mostra il
**percorso risolto** nel piede, e ogni operazione distruttiva passa dalla
conferma di §6.2 come qualunque altra. Confondere le due cose è il modo in cui
si cancella qualcosa credendo di riordinare una scrivania.

### La persistenza diventa obbligatoria

Un'icona trascinata che al riavvio torna dov'era **è peggio di non poterla
trascinare**. La persistenza del layout — segnalata come mancante in
`PERIMETRO-E-DECISIONI.md` §9 e mai fatta — smette di essere un miglioramento e
diventa un **prerequisito di questa sezione**.

Per l'invariante 1 la salva il **core**, non il renderer:

- un topic `ui.layout` in scrittura verso il core;
- lo stato completo — posizione e dimensione dei pannelli, icone libere,
  contenuto delle cartelle, posizione del catalogo — nello snapshot iniziale;
- salvataggio **differito**, non a ogni pixel di trascinamento: 500 ms dopo
  l'ultimo movimento.

---

## 26.6 Le scene — e JARVIS che dispone

### Esistono già, e non sono mai state costruite

`config/settings.toml`, dalla Fase 0:

```toml
[[voice.wake.phrases]]
say = "papa e a casa"
action = "scene:welcome_home"

[[voice.wake.phrases]]
say = "jarvis buonanotte"
action = "scene:goodnight"
```

Il meccanismo che le porterebbe a destinazione — `ui.intent` dal core alla
scrivania — è già cablato e verificato alle due estremità in `SEZIONE-13.md`.
Manca solo che cosa sia una scena.

### Che cos'è una scena

Un nome, un insieme di pannelli, e per ognuno una geometria.

```toml
[[ui.scene]]
nome = "briefing"
descrizione = "il mattino: cosa è successo, cosa scotta, cosa c'è oggi"
pannelli = [
  { id = "news",       cella = [0, 0, 5, 3], z = 3 },
  { id = "telemetria", cella = [5, 0, 4, 2], z = 2 },
  { id = "agenti",     cella = [8, 1, 4, 2], z = 1 },
]
```

Le celle si **sovrappongono di proposito**: `news` occupa le colonne 0–5,
`telemetria` 5–9, `agenti` 8–12. È la composizione del riferimento, non una
griglia.

### Chi può richiamarle

| Via | Come |
|---|---|
| Voce | frase di wake → `scene:briefing` |
| Catalogo | linguetta `SCENE`, un'icona per scena |
| Tastiera | scorciatoia opzionale nelle impostazioni |
| JARVIS | T0 riconosce l'intento e pubblica `ui.intent` |

**Limite dichiarato adesso, perché è il posto dove si scivola:** JARVIS
richiama scene **dichiarate**, non ne inventa. Non calcola una disposizione,
non decide che cosa è importante. La libertà di comporre a piacere vorrebbe
dire che il renderer esegue una geometria prodotta da un LLM, e ADR-006 dice
che il codice generato non tocca l'ambiente.

Se una scena manca, si scrive — dall'interfaccia (§26.7), non a mano.

**Salvare la scena corrente** è un tool con `side_effect=True`: scrive nelle
impostazioni, quindi passa dalla conferma.

---

## 26.7 La pagina impostazioni

`ui/src/panels/settings.js` esiste come **file da 0 byte** dalla Fase 0.

### Che cosa si regola

| Sezione | Cosa |
|---|---|
| Catalogo | quali icone, in quale categoria, l'ordine, la dimensione |
| Scrivania | scena di avvio, se ricordare il layout, il nucleo di §25 |
| Scene | elenco, crea dalla disposizione attuale, rinomina, elimina |
| Voce | provider, ripiego, frasi di wake |
| Sistema | radici consentite, tetti del tool codice, interruttori |

### Come scrive

`tomlkit` è fra le dipendenze **dalla Fase 0**, col commento
«TOML in lettura E scrittura, commenti preservati». Oggi `core/settings.py` lo
usa **solo per `parse`**: la scrittura era prevista e non è mai stata fatta.

Regole:

1. Scrive il **core**, mai il renderer (invariante 1).
2. Con `tomlkit`, così che i commenti di `settings.toml` — che spiegano perché
   un valore è quello — sopravvivano alla scrittura. Sono metà del valore del
   file.
3. Un solo tool, `imposta_valore(chiave, valore)`, `side_effect=True` con
   conferma: sta scrivendo nella configurazione di un sistema che apre un
   microfono e può eseguire codice.
4. `code.enabled`, `voice.enabled`, `vision.enabled` e le radici consentite
   **non si cambiano dall'interfaccia.** Sono gli interruttori che decidono se
   un sottosistema conseguente esiste: si cambiano nel file, con un editor,
   deliberatamente. La pagina li **mostra** e dice dove cambiarli.
5. Il `SettingsStore` ha già il ricaricamento a caldo con `watchdog`: una
   scrittura si propaga da sola, senza riavvio.

---

## 26.8 Il file manager visibile

Il motore c'è ed è la parte difficile: `tools/files.py`, 19 KB, con validazione
dopo `resolve()`, solo cestino, conferma col percorso risolto.

**Riferimento strutturale**: `famiglia-c/01`, la finestra `Computer`. Se ne
prende l'**anatomia** — barra percorso a briciole, riga strumenti, albero a
sinistra, conteggio nel piede — e **mai** il trattamento. Vedi la regola di
famiglia-c in `docs/design-reference/README.md`.

Manca la parte visibile:

- albero delle radici consentite a sinistra, elenco a destra;
- selezione singola e multipla;
- rinomina in posto;
- spostamento per trascinamento, **anche verso una cartella del fondo**;
- menu contestuale: apri, rinomina, sposta, cestina, proprietà;
- ogni voce distruttiva apre la conferma di §6.2 **col percorso risolto**.

**Nessuna operazione nuova.** Ogni voce del menu chiama un tool che esiste già.
Se una manca, si aggiunge al registry — non si scrive logica di filesystem nel
renderer.

---

## 26.9 Criteri di accettazione

1. **Una scrivania.** Nessun percorso dell'interfaccia nasconde tre quarti dei
   pannelli. `Alt+1…4` filtra il catalogo e non cambia che cosa è a schermo.
2. **Sovrapposizione.** Due pannelli che si coprono restano distinguibili:
   screenshot con tre pannelli sovrapposti, e il bordo di ciascuno rilevabile.
3. **Catalogo.** Con 40 icone la griglia scorre, l'inerzia decelera e si ferma,
   **nessuna scrollbar di sistema è visibile** nello screenshot.
4. **Trascinamento fuori.** Un'icona portata sul fondo ci resta; riavviato il
   core, è ancora lì. Verificato riavviando davvero, non simulando.
5. **Cartella contenitore.** Un'icona lasciata su una cartella entra; la
   cartella dichiara quante cose contiene.
6. **Scena.** `scene:briefing` dispone tre pannelli sovrapposti. Screenshot
   allegato, confrontato con `famiglia-a/01`.
7. **Impostazioni.** Cambiare la dimensione delle icone dalla pagina riscrive
   `settings.toml` **conservando i commenti**, e l'effetto si vede senza
   riavviare.
8. **Densità.** Il criterio di `DIVARIO-PREMIUM.md` regge sulla scrivania nuova:
   entropia ≥ 2,40, L>60 ≥ 25 %, barra ≥ 25 %. Con il catalogo pieno di icone a
   L 171 e le cartelle a L 153, è la prima volta che è raggiungibile.

---

## 26.10 Ordine di lavoro

**Il grosso di questa sezione tocca lo stesso codice del giro sui 18
componenti.** Farli insieme significa rifare due volte. L'ordine sotto li
separa.

| # | Passo | Costo | Perché qui |
|---|---|---|---|
| 1 | **Persistenza del layout** — topic `ui.layout`, salvataggio nel core | 1,5 g | prerequisito di 4 e 5; senza, il trascinamento è inutile |
| 2 | ADR-010 + una scrivania sola: `ws` → `categoria`, `vai()` filtra | 1 g | il modello prima di tutto il resto |
| 3 | Ombra riabilitata, invariante 19 riformulata, `app.css` corretto | 0,5 g | è una riga, e sblocca la sovrapposizione |
| 4 | Catalogo: linguette, griglia, scorrimento con inerzia, plinto 3D | 3 g | il pezzo grosso |
| 5 | Icone libere e cartelle contenitore | 2 g | dipende da 1 e 4 |
| 6 | Scene: schema, richiamo, salva la corrente | 1,5 g | il meccanismo esiste già |
| 7 | **Il giro §11.7 sui 18 componenti** — `DIVARIO-PREMIUM.md` §2 | 4–5 g | **dopo**, o si tarano contro un ambiente che sta cambiando |
| 8 | Pagina impostazioni + scrittura TOML | 2 g | |
| 9 | File manager visibile | 2,5 g | |
| 10 | §25 strato di presenza | 4,5 g | ultimo: è il fondo, e vuole tutto il resto fermo |

**~23 giorni.**

Il punto 7 sta in mezzo di proposito: prima l'ambiente prende la sua forma,
poi i pannelli si vestono per quella forma. Al contrario si veste un manichino
delle misure sbagliate.

---

## 26.11 Cosa resta fuori, e va detto

- **Multi-schermo.** Electron su Wayland con più monitor è un progetto a sé: o
  una finestra per display, o una che li attraversa, e il modello di layout deve
  sapere dove finisce uno schermo. Si fa **dopo** che l'ambiente singolo regge.
- **JARVIS che inventa disposizioni.** Richiama scene dichiarate. Vedi §26.6.
- **Finestre di altri programmi.** ADR-005: fuori perimetro.
- **Icone di file arbitrari fuori dalle radici consentite.** Il catalogo mostra
  ciò che `tools/files.py` può raggiungere, e nient'altro.
