# Turno 2 — il marchio a norma §25.13

> **`docs/PIANO-CORE-E-DENSITA.md`, turno 2.** Una riga di colore, secondo il
> piano. Ne sono venute quattro: la regola 4 era quella dichiarata, la 7 non era
> soddisfatta e nessuno l'aveva verificata, l'eccezione dell'audit di §25.13.3
> non esisteva, e il criterio di accettazione §25.13.5 non aveva un modo di
> essere misurato.

---

## Le sette regole di §25.13.2, una per una

| # | Regola | Prima | Ora |
|---|---|---|---|
| 1 | uno solo in tutta l'applicazione | ✅ | ✅ una sola `crea()`, in `desk/sfondo.js` |
| 2 | stringa fissa, non parametrica | ✅ | ✅ `marchio.textContent = "J.A.R.V.I.S."` |
| 3 | mai in una cella, in un pannello, nella barra | ✅ | ✅ figlio di `.sfd`, `--z-insegna` |
| 4 | **`--cy-700`, tetto invalicabile** | ❌ `--icona-viva`, L 219 | ✅ `--cy-700`, L 100 |
| 5 | non si muove, non respira, non pulsa | ✅ | ✅ l'unica scrittura è `fontSize` al ridimensionamento |
| 6 | testo nel DOM, mai rasterizzato | ✅ | ✅ `<span>` |
| 7 | `pointer-events: none`, **non selezionabile** | ⚠️ metà | ✅ aggiunto `user-select: none` |

### La regola 7 era soddisfatta a metà, e sembrava intera

`.sfd` porta `pointer-events: none`, quindi il marchio non si può puntare — ed
è questo che faceva sembrare la regola rispettata. Ma **una selezione che parte
altrove lo attraversa lo stesso**, e `Ctrl+A` lo prende comunque: la scritta
finiva negli appunti di chi copiava un valore da un pannello. Un marchio non è
testo da portarsi via. Aggiunto `user-select: none`.

---

## §25.13.3 — l'eccezione dell'audit esisteva solo come pretesa

La sezione chiede che il corpo calcolato di `.sfd__marchio` sia ammesso da
**un'eccezione nominata, non da una soglia allentata**. Prima di questo turno,
`grep marchio` su `scripts/audit.mjs` e `ui/src/gallery/audit.js` non trovava
niente: la deroga era tollerata da un audit che non guardava.

Adesso è una riga sola, in `ui/src/gallery/audit.js`:

```js
const MARCHIO = ".sfd__marchio";
if (corpo && !corpiAmmessi.has(corpo) && !el.matches(MARCHIO))
```

### Che sia NOMINATA è verificato, non affermato

Due `<span>` identici, stesso corpo calcolato di 22,4 px, stessa famiglia, uno
solo con la classe. L'audit vero, chiamato con `esegui(document.body)`:

```
{ "marchio": [],
  "altro":   [{ "prop": "font-size", "trovato": "22.4px",
                "atteso": "uno dei gradini --t-* (l'unica eccezione e' .sfd__marchio, §25.13.3)" }] }
```

E l'eccezione non ha allentato nulla: `audit.mjs non-conforme` continua a
bocciare **tre** corpi calcolati (17 px, 17 px, 22 px) e `audit.mjs conforme`
resta a 0 violazioni su 0.

---

## §25.13.5 — il criterio di accettazione, misurato

> Luminanza media ≤ 105, contrasto WCAG contro il composito sottostante fra
> 3,0:1 e 5,0:1.

Non c'era un modo di misurarlo. Adesso c'è: `node scripts/densita.mjs --marchio
shots/scrivania`, che legge i due scatti che `app/main.js` produce nella stessa
sessione — uno normale e uno col marchio a `visibility: hidden`.

```
marchio      22.4px · dichiarato rgb(34, 116, 130)
  ritaglio   199x43 · 8557 pixel, di cui 948 di tratto e 159 di scudo
  luminanza  media del ritaglio 25.6 (tetto 105) · pixel piu' luminoso della scritta 122.5
             massimo del ritaglio 122.5 col marchio · 105.4 SENZA
  sotto      rgb(17, 25, 29) L 23.6 — il composito misurato, non dichiarato da nessuno
  contrasto  3.30:1 fra il colore DICHIARATO e il composito (forbice 3-5:1)
  e il reso  decile piu' pieno rgb(38, 117, 130) -> 3.34:1
             media di tutti i tratti rgb(29, 78, 88) -> 1.93:1  (l'antialiasing diluisce)

§25.13.5 SODDISFATTO
```

### Perché due scatti

«Contro il composito sottostante» non si legge da un solo PNG: sotto la scritta
c'è la nuvola, diversa in ogni punto. L'unico modo di sapere che colore ci
sarebbe senza il marchio è guardare la stessa scrivania col marchio nascosto,
nella stessa sessione. `visibility: hidden` e non `display: none`: il secondo
toglierebbe l'elemento dal flusso e la griglia di `.sfd` ricomporrebbe,
cambiando proprio ciò che si vuole misurare.

I pixel che differiscono si dividono per **segno**, e non per una soglia
inventata: più chiari del composito sono i tratti, più scuri sono lo scudo
(`text-shadow` col colore del pavimento).

### ⚠️ Il punto di metodo: 3,30:1 o 1,93:1, e la differenza è passa/non passa

Il primo giro di questa misura ha risposto **1,94:1 — non soddisfatto**,
mediando tutti i pixel accesi. Il numero era vero e la domanda sbagliata.

WCAG è definito fra **due colori**, non fra due rendering. Una scritta alta
22 px con spaziatura larga produce in maggioranza pixel a copertura parziale, e
la loro media è più scura del colore del testo **per costruzione, su qualunque
testo**: giudicare lì significa bocciare la tipografia piccola in quanto
piccola. Il criterio si calcola quindi sul colore dichiarato — letto da
`getComputedStyle` nella finestra vera, non scritto a mano — contro un fondo che
resta **misurato**, perché «il composito sottostante» è proprio ciò che nessuna
dichiarazione conosce.

Che il colore dichiarato si veda davvero non è dato per buono: il **decile più
pieno** dei tratti rende `rgb(38, 117, 130)` contro `rgb(34, 116, 130)`
dichiarato. La dichiarazione è confermata dai pixel.

Entrambi i numeri restano stampati, con i nomi diversi.

---

## §25.13.4 — lo scudo non ingoia i tratti

La sezione avvertiva: uno scudo tarato per L 219 su una scritta a L 100 può
ingoiarne i tratti sottili, e la verifica è visiva, non una formula.

**Guardato, a 5× sul ritaglio.** `J.A.R.V.I.S.` è interamente leggibile: tutte
le aste, tutte le curve e tutti i punti sono continui, e lo scudo legge come un
alone scuro che stacca la scritta dalla nuvola senza mangiarne i bordi. Non
serve ritarare.

---

## Che cosa questo turno chiude della deroga 2

`DEROGHE-7dad2b8.md` attribuiva a due sorgenti il superamento di §25.5 —
massima L 255 sull'insegna — e la prima era il marchio.

**Quella metà è chiusa**: il colore del marchio è `--cy-700`, e il decile pieno
lo conferma a L ~101.

Resta l'altra metà, e la misura la vede: **nel ritaglio del marchio, senza il
marchio, il massimo è ancora L 105,4** — è la nuvola, che somma in
`globalCompositeOperation = "lighter"` e supera il tetto da sola. La chiude il
turno 3, insieme alla nuvola.

⚠️ **Un limite del metodo, dichiarato.** Il pixel più luminoso col marchio è
L 122,5, `rgb(76, 134, 145)`: **più alto di entrambi gli estremi** — il colore
del testo e il fondo misurato 120 ms dopo. Non è attribuibile con due scatti,
perché fra l'uno e l'altro la nuvola si è spostata e il fondo campionato non è
quello che c'era davvero sotto quel pixel. **Le medie su ~950 pixel sono
robuste** — il moto si media — **i singoli picchi no**. Il numero è stampato
come contesto, non come criterio.

---

## Che cosa NON è stato verificato

- **Il contrasto è vicino al bordo inferiore**: 3,30:1 su una forbice che
  comincia a 3,0. Il fondo varia fra le esecuzioni — `rgb(17, 23, 28)` e
  `rgb(17, 25, 29)` — perché la nuvola si muove, e il rapporto oscilla fra 3,30
  e 3,33. **Dopo il turno 3 il composito cambia e questo criterio va rimisurato**:
  se il nucleo nuovo è più scuro il contrasto sale verso il tetto di 5:1, che
  boccia quanto il pavimento.
- **`user-select: none` non è coperto da un test.** Nessuna prova fallisce se
  domani sparisce.
- **La regola 1** — uno solo in tutta l'applicazione — è verificata da `grep`
  oggi, non da un test.
- **`sfondo.js` continua a non passare da `scripts/audit.mjs`**: non è
  registrato in galleria, quindi l'eccezione nominata protegge un componente che
  l'audit non visita comunque. È scritta perché §25.13.3 la pretende e perché il
  giorno che lo strato di presenza entrerà in galleria dovrà esserci già.

---

## Misure di contorno

La densità non si muove: `L>60` 9,2 → 9,3 %, `caldo` 0,2 % invariato, entropia
1,58 invariata — dentro il rumore fra due esecuzioni. Era atteso: il marchio è
183×27 px, l'1,4 % di un pavimento da 1536×783.

Suite: **557 passed**. Audit: `conforme` 0/0, `non-conforme` 4 calcolate e 23
sorgente, come prima.
