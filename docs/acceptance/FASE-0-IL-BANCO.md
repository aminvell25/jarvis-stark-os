# Fase 0 — il banco che sa bocciare

**Data:** 24 agosto 2026 · **Rollback:** `500b9ef`
**Piano:** la FUI avanzata, fase 0 · **Modalità:** rapporto, non bloccante

Tre misure dichiarate aperte e mai fatte. Accese **in rapporto per un giro**:
tre criteri mai valutati prima possono dare tre rossi il primo giorno, e allora
non si sa quale guardare. Prima il numero, poi la soglia.

**Due difetti veri trovati, e il secondo è grosso.**

---

## ① Il dock — una soglia che esisteva in due documenti e non bocciava niente

`docs/design-reference/README.md` e `DIVARIO-PREMIUM.md` §7 dichiarano entrambi
**≥ 20 % di inchiostro L>50** nella fascia del dock — riferimento `01` al
26,2 %, `05` al 22,8 %. In `scripts/densita.mjs` la parola `dock` **non
compariva**. Una soglia che nessuno valuta non è una soglia: è una frase.

```
dock   2,0 % di inchiostro L>50 · soglia 20 % · riferimento 22,8-26,2 %
```

**Un decimo della soglia**, e coerente col 2,8 % che `DIVARIO §7` misurava il
19 agosto: il dock non è mai stato riempito.

### Si misura diversamente dalla barra, di proposito

La barra usa una **fascia fissa al 3,3 %** dall'alto, che è la misura *del
riferimento*: usare la nostra altezza vorrebbe dire misurare noi stessi. Il dock
no — la sua altezza è una decisione ancora in revisione, e una fascia fissa
misurerebbe mezzo dock o un dock e mezzo. Si legge il **rettangolo dichiarato**,
che `occlusione.json` porta già: il pavimento va da `alto` a `alto + altezza`, e
ciò che resta sotto è il dock.

⚠️ Senza `occlusione.json` il dock è **`null`, non `0`** — e si stampa `NON
MISURABILE`. È §11.7 regola 4 applicata il giorno dopo averla scritta: non
sapere dov'è il dock non è un esito buono.

---

## ② Le risoluzioni — e la peggiore è quella su cui misuriamo da sempre

`DIVARIO-PREMIUM.md` §10, «impatto ALTO, **costo nullo**», aperto da prima di
ogni altro documento del progetto. Il costo **non era nullo**.

### Quattro tentativi falliti, e come si è visto

Ridimensionare la finestra **non funziona su questa macchina**. In fila: misura
nel costruttore di `BrowserWindow`, `setContentSize()` prima del caricamento, di
nuovo a `ready-to-show`, di nuovo subito prima dello scatto, più `unmaximize()`
e `setMaximizable(false)`. Il renderer continuava a riportare
`window.innerWidth` **1536**.

`getContentSize()` rispondeva `1280x800` — cioè **ciò che avevamo chiesto**,
ottimisticamente — mentre il gestore di finestre non lo applicava mai.

**La prova che erano lo stesso scatto**, e non un ridimensionamento che non si
vedeva: le tre «risoluzioni» davano dev.std **34,1 / 34,1 / 34,0** ed entropia
**2,23 / 2,23 / 2,22**. Se la larghezza fosse cambiata davvero non si
somiglierebbero così. *Una misura che non cambia quando cambi la cosa misurata
sta misurando altro.*

**Lo strumento giusto è `webContents.enableDeviceEmulation`**: cambia il
viewport del renderer e non tocca la finestra, quindi il gestore non c'entra
più. Ed è anche lo strumento adatto alla domanda di §10, che è **«il layout
regge a larghezze diverse»** — il debordo di R99 — non «quanti pixel accesi ha
uno schermo più grande».

### Che cosa si è trovato

`debordaX/debordaY` erano **già raccolti** da `verifica:scrivania` — e non
entravano in **nessun** booleano del verdetto. Raccolti, stampati, mai
asseriti. Il commento accanto diceva pure perché servivano: *«un pannello che
esce dalla propria cornice si vede prima di ogni altra cosa, e a occhio, su
quattro workspace e quattordici pannelli, uno sfugge sempre»*.

| viewport | layout salvato a | pannelli che debordano |
|---|---|---|
| 1280×800 | 1536 | 1 — `news 0x4` |
| 1536×843 | 1536 | 1 — `news 0x4` (due giri, identici) |
| 1920×1140 | 1536 | 1 — `news 0x4` |
| **1536×843** | **1280** | **5 — `telemetry 65x0` · `globe 53x0` · `agents 53x0` · `news 61x24` · `files 65x0`** |

**Non è la larghezza corrente a rompere: è il rapporto fra la larghezza e quella
a cui il layout è stato salvato.** Un layout salvato **stretto** e ripristinato
**largo** lascia i pannelli alle loro dimensioni vecchie, e cinque su sei
debordano — il contenuto è disegnato per il pannello largo, il pannello è
rimasto stretto.

⚠️ È la conseguenza diretta della correzione **provata e ritirata il 23 agosto**:
`dentroArea()` legge `area_larghezza`/`area_altezza` da `layout.json` e **non li
usa** — taglia soltanto. La scala fu ritirata perché rompeva §26.9 criterio 4.
Il difetto che quella scala avrebbe chiuso **è qui, ed è misurato**: non è più
latente.

⚠️ E un difetto minore, costante a **ogni** larghezza: `news` deborda di **4 px
in verticale**, sempre. Non dipende dal viewport.

---

## ③ Il budget per motore — `DIVARIO §12`

L'invariante 26 dà **tre tetti separati** — three.js ≤ 8 ms, Pixi ≤ 3, anime.js
≤ 4 — e finora si misurava **una cosa sola**: l'intervallo fra due fotogrammi,
che col render a richiesta risponde sempre vsync e non dice quanto costa *chi*.

`performance.mark`/`measure` in `ui/src/three/scena.js` (`rendi()`) e
`ui/src/pixi/glyphs.js` (i due `app.render()`), letti a fine scatto.

```
three     5 render · mediana  1,2 ms · max 37,3 ms · tetto 8 ms
pixi      0 render · NON MISURABILE
anime     0 render · NON MISURABILE
```

⚠️ **Il `max` di 37,3 ms è il PRIMO render**, cioè compilazione degli shader e
caricamento delle texture: su cinque render il massimo *è* l'avvio. La mediana —
**1,2 ms** su un tetto di 8 — è il numero che descrive il regime. Chi accenderà
la soglia scarti il primo render, o misurerà per sempre l'avvio.

⚠️ **Zero marche non è zero costo.** Pixi e anime.js non hanno reso durante lo
scatto: i glifi non sono nella scena `avvio` e nessuna animazione con causa è
scattata nei tre secondi del protocollo. Si stampa **`NON MISURABILE`**, non
`0 ms` — §11.7 regola 4, seconda applicazione in due giorni.

---

## Che cosa NON è stato fatto

- **Le soglie non bocciano.** `dock`, debordo e budget sono in rapporto. Chi le
  accende tolga il blocco «CRITERI IN RAPPORTO» in `densita.mjs` e rimetta la
  riga dentro `falliti`.
- **`anime` non è strumentato.** I tredici punti di animazione stanno in sei
  file e ognuno vorrebbe la propria coppia di marche. Con zero render nel
  protocollo non avrebbe cambiato il numero, e strumentare sei file per leggere
  `NON MISURABILE` è lavoro speso male finché la Fase 3 non aggiunge
  l'apertura dei pannelli — che è il primo consumatore vero di quel budget.
- **La causa del debordo non è corretta**, solo misurata. Correggerla è la
  scala di `dentroArea()`, che è già stata provata e ritirata una volta: è una
  decisione, non una rifinitura, e non entra in un turno di banco.
- **Nessun ciclo §11.7**: questo turno non tocca un solo pixel: due strumenti di
  misura e un flag.
