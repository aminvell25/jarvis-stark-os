# §13 — La scrivania · esito dei criteri

**Data**: 19 agosto 2026 · **Riferimento**: `docs/SPEC.md` §13
**Test**: 351 verdi (erano 331) + 207 negli eval · **Precedente**: `FASE-09.md`

⚠️ **Non è una fase di §22.** §22 non ha mai assegnato §13 a una fase, e il
nome di questo documento lo dice: `SEZIONE-13`, non `FASE-10`. Il criterio di
accettazione me lo sono dato io (R68) — come per la Fase 9, che era l'altra
senza criterio.

Per nove fasi `ui/src/app.js` ha montato **un pannello**. Non era una
dimenticanza: la disposizione delle finestre è §13, ogni fase la rimandava
correttamente, e nessuna la prendeva. Questo è il lavoro che mancava perché
JARVIS smettesse di essere una finestra.

---

## I cinque criteri che mi sono dato

### 1. Le otto voci del dock — ✅ VERIFICATO nella finestra vera

`npm run verifica:scrivania`, che preme davvero gli otto pulsanti:

```
Telemetria     commuta=True torna=True     File manager   commuta=True torna=True
Mesh agenti    commuta=True torna=True     Core sorgente  commuta=True torna=True
Console        commuta=True torna=True     Browser        commuta=True torna=True
News           commuta=True torna=True     Globo tattico  commuta=True torna=True
```

**Il criterio ha sbagliato due volte prima di essere giusto**, ed entrambe le
volte l'errore era mio, non del codice:

- guardava il **conteggio** dei pannelli aperti. Ma premere la voce di un
  altro workspace ci porta dentro e lo COMPONE: tre pannelli in più, non uno.
  È ciò che un dock deve fare;
- aspettava 260 ms fra un clic e l'altro. Comporre WS02 vuol dire costruire
  una scena three.js e una pila CSS 3D: il secondo clic arrivava mentre il
  primo stava ancora aprendo, e bocciava la latenza invece della logica.

La proprietà giusta è una sola: **una pressione commuta il modulo, due
riportano dove si era.**

### 2. Le scorciatoie realizzabili di §13 — ✅ VERIFICATO, e due dichiarate

Provate con `KeyboardEvent` veri sul documento, non chiamando le funzioni:

| §13 | esito |
|---|---|
| `Alt+1…4` workspace | ✅ `[('Alt+2', 2), ('Alt+3', 3), ('Alt+4', 4), ('Alt+1', 1)]` |
| `Alt+H` nascondi tutto | ✅ 6 pannelli → 0 → 6 |
| `Alt+T` affianca | ✅ spostata, e ri-affiancata torna alla geometria dichiarata |
| doppio clic barra → massimizza | ✅ sulla testa del pannello (R72) |
| trascinamento al bordo → aggancia a metà | ✅ quattro metà, `zonaAggancio()` sotto test |
| `Alt+Spazio` ascolto | ❌ **dichiarata** — vedi R70 |
| `Esc` interrompe il TTS | ❌ **dichiarata** — vedi R70 |

Il preload resta a **quattro funzioni**: `['confirm','onMessage','onStatus','status']`.

### 3. Ogni pannello dice il vero — ✅ VERIFICATO, quattordici su quattordici

| Pannello | Sorgente | Stato misurato |
|---|---|---|
| telemetria | `telemetry` | collegato — CPU/RAM/temp/liberi veri |
| quadranti | `telemetry` | pieno |
| mesh agenti | `agent.mesh` | pieno — 8 nodi, T1 «non collegato» perché lo è |
| anelli | `state.snapshot` + `agent.mesh` | «voce spenta · 21 tool», uptime vero |
| glifi | ogni messaggio del socket | pieno — 44,7 kB di traffico vero |
| console | ogni messaggio del socket | collegato |
| **file** | `fs.list` **(nuovo)** | collegato — 1 voce, ed è quello che c'è |
| **sorgente** | `source.tree` **(nuovo)** | pieno — 284 file, 11,9 MB |
| **archivio** | `archive.notes` **(nuovo)** | pieno — 11 documenti |
| browser | `web.open` | vuoto — «nessuna pagina aperta» |
| news | `news.card` | vuoto — «il silenzio è una scelta, non un guasto» |
| board | da `archive.notes` | pieno |
| globo | `geo.timezones` **(nuovo)** | pieno — 312 fusi, 144 in luce |
| tavola periodica | costanti IUPAC | 118 elementi |

Nessun segnaposto. I due pannelli vuoti di WS03 **lo sono davvero**: nessuna
pagina è stata aperta e il gate news non ha fatto passare niente.

### 4. Ciclo §11.7 sui quattro workspace — ✅ ESEGUITO, e ha trovato sei difetti

`npm run scrivania`, quattro scatti in `shots/scrivania/`, **guardati**. La
checklist §11.8 è più sotto. I sette difetti che ha trovato sono la parte che
conta, e nessuno di essi era visibile in galleria.

### 5. Budget di frame di §10.4 sull'insieme — ✅ MISURATO, vedi «La misura»

---

## I sette difetti che solo la scrivania poteva mostrare

### ① I glifi PixiJS non erano MAI partiti in Electron

Il più grave, e il più istruttivo.

```
Error: Current environment does not allow unsafe-eval,
       please use pixi.js/unsafe-eval module to enable support.
```

PixiJS v8 **genera a runtime** il codice che sincronizza uniform e shader, con
`new Function()`. Il CSP di `ui/index.html` non ha `unsafe-eval` — e **non
deve averlo**: il renderer ospita `<webview>` con contenuto non fidato (Fase
6), e lì `unsafe-eval` trasforma un'iniezione nel DOM in esecuzione di codice.

Il pannello ha passato tutto il ciclo §11.7 della Fase 5 e in Electron ha
sempre mostrato «0 byte», **senza un errore in console**: l'eccezione finiva in
una promessa che nessuno guardava.

Perché è rimasto invisibile per quattro fasi: **`ui/gallery.html` non aveva
nessun CSP**. Una galleria più permissiva dell'app fa passare il ciclo §11.7 a
componenti che nell'app non funzionano — cioè esattamente il fallimento che
§11.7 esiste per evitare.

**Due correzioni, e la seconda vale più della prima:**

1. `pixi.js/unsafe-eval` vendorizzato. Quel modulo importa le classi
   dall'albero `lib/` non impacchettato mentre noi carichiamo il bundle:
   sarebbero due copie diverse delle stesse classi. `scripts/vendor.mjs`
   riscrive i soli import che escono da `unsafe-eval/` e li punta al bundle.
2. **La galleria ha adesso lo STESSO CSP dell'app**, e
   `tests/eval_visual.py` verifica che restino uguali.

### ② Il ponte perdeva i messaggi che arrivano una volta sola

La barra diceva **OFFLINE** mentre i grafici scorrevano.

`collega()` parte in `app.whenReady()`, prima che la pagina finisca di
caricarsi. Il core, appena un client si collega, manda una volta sola
`state.snapshot` e — da §13 — l'albero dei sorgenti, i fusi, l'archivio, la
workspace. Quei messaggi partivano verso un renderer senza ascoltatori, e
`webContents.send` li perdeva **in silenzio**.

Non si vedeva con un pannello solo: `telemetry` arriva a 2,5 Hz e si ripete.

Il ponte tiene l'ultimo messaggio per topic e lo riconsegna a `did-finish-load`
— la stessa cosa che il core fa a chi si collega e che il bus fa a chi si
iscrive tardi, applicata al tratto in mezzo.

### ③ PixiJS partiva due volte

`new Application()` assegna la variabile **prima** che `app.init()` finisca. In
galleria il mount chiama `aggiungi` una volta e la aspetta; sulla scrivania i
messaggi arrivano a raffica, il secondo trovava l'oggetto non nullo, saltava
l'avvio e chiamava `render()` su un renderer che non esisteva.

### ④ La board investigativa usciva dal proprio pannello

Le carte sono posizionate in **pixel dal centro** — scelta di Fase 6, giudicata
in una cella da 1100×620. Sulla scrivania il pannello ha la forma che gli dà il
workspace: le carte in alto e in basso finivano fuori.

Adesso `adatta()` misura l'ingombro vero e rimpicciolisce finché ci sta (mai
ingrandisce). Legarlo a `requestAnimationFrame` dopo il disegno **non
bastava** — il pannello può essere ancora largo zero quando i dati arrivano, e
allora la misura non vale niente e non viene più ripetuta. Lo fa un
`ResizeObserver`, che parla quando c'è qualcosa da misurare.

### ⑤ Due pannelli debordavano dalla propria cornice

Trovati **misurando**, non a occhio: `scrollWidth − clientWidth` su tutti e
quattordici, su tutti e quattro i workspace.

```
prima:  pnl-file dx=176   pnl-news dx=66   pnl-tel dy=54
dopo:   14 pannelli, 0 debordano
```

- `pnl-file` e `pnl-news`: le celle erano più strette della `min-width` che i
  pannelli dichiarano. **La larghezza di una cella dipende dallo schermo, la
  `min-width` no**: su un 1536 una colonna vale 128 px, e un pannello che ne
  chiede 550 ne vuole cinque.
- `pnl-tel`: la riga `1fr` di una CSS Grid non scende sotto il proprio
  contenuto — il minimo predefinito è `auto`, non zero. `min-height: 0`.

### ⑥ Le barre di scorrimento erano nostre per metà

La correzione iniziale (R76) dichiarava **entrambe** le API: le proprietà
standard `scrollbar-width`/`scrollbar-color` e gli pseudo-elementi
`::-webkit-scrollbar`. Da Chromium 121 le due cose non convivono — se le
standard sono presenti, gli pseudo-elementi vengono ignorati in blocco.

Non dà nessun errore: dà dieci righe di CSS che non girano. Misurato nella
finestra vera, con le righe vere di un pannello costretto a scorrere:

```
prima:  altezza barra 10 px   scrollbar-width: thin   (larghezza di Chromium)
dopo:   altezza barra  8 px   = --s-2
```

I colori erano giusti **per caso** — arrivavano da `scrollbar-color` — ma la
forma no: la barra standard ha il cursore dalle estremità arrotondate, e
`border-radius` su di lei non si può scrivere. L'invariante 18 dice che il
raggio è sempre zero.

Adesso resta una sola API, e i pixel si leggono invece di guardarli:

```
x:     0…3      4        5…7                8…11
       corpo    #103038  #0a1014            #123840
                hairline --bg-deep (pista)  --cy-900 (cursore)
```

Ogni pixel è un token, e il cursore ha lo stesso colore dalla prima riga
all'ultima: nessun arrotondamento. `tests/eval_visual.py` impedisce che le due
API tornino insieme.

### ⑦ Sette backtick dentro i fogli di stile

Un backtick in un commento CSS chiude il template literal che contiene il
foglio, e il modulo smette di caricarsi. È successo **sette volte** fra la Fase
1b e oggi. Adesso c'è un test col proprio nome che dice il file, la riga e cosa
togliere — e il messaggio del test generico non stampa più la versione di
Node al posto dell'errore.

---

## Tre cose che non erano difetti della scrivania ma che la scrivania ha scoperto

**I quattro tool di memoria della Fase 4 non erano registrati.** `recall`,
`list_topics`, `pin_fact`, `write_topic` esistevano, erano provati, e
`register_memory_tools` non era mai stato chiamato in `core/engine.py`: nel
processo vero **non esistevano**. Una riga mancante nella radice di
composizione, trovata cercando chi potesse produrre l'archivio.

**Il gate news non aveva la memoria.** `Gate(max_per_ora=...)` senza
`MemoryStore`: «non parlarmene più» (§15 regola 5) non sopravviveva al
riavvio. Il file markdown c'era, nessuno lo leggeva.

**Cinque intenti T0 non hanno una destinazione.** `set_volume`, `mute`,
`brief_me`, `needs_attention`, `doctor` sono nella grammatica dalla Fase 3 e
non sono né azioni della scrivania né tool. `esegui_t0` li **rifiuta**
dicendolo, e un test fissa l'elenco: un intento nuovo senza destinazione fa
fallire lì, non in esercizio.

E una quarta, minore: cinque immagini di `docs/design-reference/` risultavano
cancellate nel working tree da una pulizia di una sessione precedente.
Ripristinate da git; `npm run check:refs` torna coerente.

---

## La composizione, dichiarata

§13 dà i domini dei workspace e gli otto moduli del dock. **Non dice quale
pannello vada dove**: è una decisione, ed è in `ui/src/desk/moduli.js`, in un
posto solo.

| WS | Dominio | Accento | Moduli §13 | Arredo |
|---|---|---|---|---|
| **01** | Sistema e telemetria | `--cy-500` | telemetria, mesh agenti, console | quadranti, anelli, glifi |
| **02** | File e progetti | `--cy-300` | file manager, core sorgente | piani d'archivio |
| **03** | Web e ricerca | `--cy-700` | browser, news | board investigativa |
| **04** | 3D e modelli | `--amber` | globo tattico | tavola periodica |

**Modulo e arredo sono due cose diverse**, e sono due domande diverse: «è
acceso?» e «com'è disposta la stanza?». Il dock possiede lo stato dei moduli —
un modulo chiuso resta chiuso, o il dock mentirebbe. L'arredo appartiene alla
composizione: entrare in un workspace la compone.

Le celle sono dichiarate su una griglia 12×4 e i pixel li calcola la scrivania
dall'area vera. Perciò «affianca» (`Alt+T`) **non è un secondo algoritmo**: è
ri-applicare la disposizione dichiarata. E un test verifica che ogni cella di
ogni workspace sia coperta **esattamente una volta** — buchi e sovrapposizioni
sono aritmetica, e §11.6 regola 3 smette di essere un'opinione.

---

## Checklist §11.8, punto per punto sui quattro workspace

| | WS01 | WS02 | WS03 | WS04 |
|---|---|---|---|---|
| Due font, cinque corpi, ogni numero in mono | ✅ | ✅ | ✅ | ✅ |
| Un solo accento caldo, sempre semantico | ✅ nessuno: niente è oltre soglia | ✅ nessuno | ✅ chip delle carte | ✅ terminatore solare |
| Densità — nessuno schermo mezzo vuoto | ✅ 6 pannelli | ⚠️ file manager vuoto **perché la cartella lo è** | ⚠️ browser e news vuoti **finché non si usano** | ✅ |
| Dati veri o stato vuoto esplicito | ✅ | ✅ | ✅ | ✅ |
| Zero glow, zero bloom, zero drop-shadow | ✅ | ✅ | ✅ | ✅ |
| Asimmetria: uno o due angoli tagliati | ✅ | ✅ | ✅ | ✅ |
| Fondo immobile | ✅ | ✅ | ✅ | ✅ |
| Nessun pannello deborda | ✅ misurato | ✅ | ✅ | ✅ |

Le due caselle gialle **non sono difetti da correggere**: `~/JARVIS` su questa
macchina contiene una cartella, e nessuno ha aperto una pagina. Un pannello che
si riempisse per far bella figura violerebbe l'invariante 23. Ciò che ho
corretto è la CORNICE — il file manager non occupa più 800 px di vuoto, e la
board non deborda.

---

## La misura

`npm run verifica:scrivania` misura anche gli intervalli fra fotogrammi nella
finestra vera, su ognuno dei quattro workspace, 180 fotogrammi ciascuno. Con
render-on-demand e l'invariante 25 — zero animazione ambientale — una scrivania
ferma non deve costare niente.

| Workspace | mediana | p95 | max |
|---|---|---|---|
| **01** sistema · uPlot + PixiJS + anime.js + SVG | **16,70 ms** | 19,10 | 33,60 |
| **02** file · three.js + CSS 3D | **16,70 ms** | 17,70 | 34,20 |
| **03** web · webview + CSS 3D | **16,70 ms** | 21,70 | 31,70 |
| **04** 3D · three.js + CSS Grid | **16,70 ms** | 17,30 | 25,20 |

**La mediana è 16,70 su tutti e quattro**, cioè il vsync: la scrivania non
consuma il proprio fotogramma, lo aspetta. È la stessa lettura della Fase 5, e
qui vale per l'insieme invece che per un componente alla volta.

Il **massimo** dice l'altra metà: uno o due fotogrammi persi ogni tre secondi.
Cadono dove ci si aspetta — l'arrivo della telemetria a 2,5 Hz ridisegna uPlot,
i quadranti e i glifi nello stesso istante. Non è un'animazione: è un dato che
arriva, e §10.3 vuole che si muova solo per quello.

⚠️ È una misura a scrivania **ferma**, che è lo stato normale. Sotto carico —
T1 che genera, ARGUS che cattura, news che arrivano insieme — non l'ho fatta.

| | |
|---|---|
| Pannelli vivi contemporaneamente | **6** (WS01) |
| Motori accesi insieme | uPlot, PixiJS, anime.js, SVG, CSS 3D, three.js |
| Traffico letto dai glifi | 44,7 kB reali in ~2 minuti |
| Pannelli che debordano | **0 su 14** |
| Voci del dock che commutano | **8 su 8** |
| Funzioni del preload | **4**, invariate |

---

## Scostamenti dalla specifica, dichiarati

### ⚠️ Il tray della barra non c'è

§13 lo nomina. Non ci sarebbe niente da metterci — nessuna icona di notifica
esiste in questo sistema — e un riquadro vuoto in alto a destra sarebbe il
segnaposto che l'invariante 23 vieta.

### ⚠️ La console è metà

§13 dice «comandi reali con trace». La **traccia** c'è ed è completa, e non
nasconde niente: i campioni di telemetria non elencati sono **contati** nel
piede. L'**ingresso** no: sarebbe una richiesta verso il core, e il preload non
la consente. Il piede lo dichiara, invece di mostrare un prompt che non manda
niente da nessuna parte.

### ⚠️ «apri le impostazioni» non apre niente

La grammatica T0 accetta `impostazioni` dalla Fase 3, `ui/src/panels/settings.js`
è un file vuoto, e §13 non lo elenca fra gli otto moduli. Un test fissa questa
come **l'unica** eccezione nota: ogni altro nome che si può dire a voce trova
un pannello.

### ⚠️ Due gesture di §14 su quattro non si possono fare

`sposta_pannello` e `ruota_mesh` sono manipolazioni **continue** — vogliono
sapere di quanto, istante per istante — e `gesture.intent` porta un intento
discreto senza coordinate. `cambia_workspace` e `espandi_pannello` sono
collegate. Farne muovere due di una quantità inventata sarebbe peggio che non
farle.

### ⚠️ Due tool nuovi nell'allowlist

`source_tree` e `archive_notes`, sola lettura, **senza parametro path**, radice
cablata all'installazione. La radice del progetto non è fra le `allowed_roots`
e non deve diventarlo: quella lista è ciò su cui i tool possono anche
SCRIVERE. La difesa è strutturale, come per `timezones`: non c'è input che
possa spostare la radice altrove, perché non c'è input.

Allowlist: **15 → 21** (2 di introspezione + 4 di memoria mai registrati).

---

## ❌ NON VERIFICATO

1. **La voce che apre un pannello.** `esegui_t0` pubblica `ui.intent` con gli
   argomenti e la scrivania lo consuma: verificato **alle due estremità**, in
   Python e nel renderer. Il microfono in mezzo no — `voice.enabled` è falso e
   la `VoicePipeline` non è composta nell'engine.
2. **Le gesture verso la scrivania.** Stessa forma: il consumatore c'è e i due
   intenti collegati sono provati, ma `vision.enabled` è falso e nessun
   `gesture.intent` è mai arrivato dal vivo.
3. **Il trascinamento e l'aggancio con un mouse vero.** `zonaAggancio()` è
   verificata come funzione su cinque punti; il gesto completo —
   pointerdown/move/up sulla testa di un pannello — l'ho scritto e non l'ho
   provato con una mano.
4. **Risoluzioni diverse da 1536×839.** Le celle sono frazioni dell'area, ma le
   `min-width` dei pannelli no: su uno schermo più stretto qualche cella
   tornerebbe sotto la soglia. Il criterio del debordamento lo direbbe subito;
   non l'ho eseguito ad altre dimensioni.
5. **Il budget di §10.4 sotto carico.** Misurato su una scrivania **ferma**,
   che è lo stato normale (invariante 25). Con T1 che genera, ARGUS che cattura
   e le news che arrivano tutte insieme, no.
6. **La board e i piani su un archivio grande.** Undici documenti; con
   trecento, `adatta()` rimpicciolirebbe fino a rendere illeggibili le carte.

---

## Riepilogo

| | |
|---|---|
| Test | **351 verdi** (erano 331) + **207** negli eval |
| Pannelli sulla scrivania | **14**, tutti con una sorgente dichiarata |
| Topic che nessuno pubblicava | 4 → **0** |
| Difetti trovati dal ciclo §11.7 | **7**, nessuno visibile in galleria |
| Difetti trovati nel core, di rimbalzo | **3** |
| Criteri che mi sono dato | **5 su 5** |
| Scorciatoie di §13 | **5 su 7**, le altre due dichiarate col motivo |
