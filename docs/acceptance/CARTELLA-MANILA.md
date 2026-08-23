# Turno 6 — la superficie manila, e il posto che non c'è

> `PIANO-CORE-E-DENSITA.md` §4 turno 6: **costruire** le cartelle manila di
> §26.5 sul piano, non «scoprirle». Effetto atteso: il caldo da 0,2 % verso
> 5,7 %.

---

## Che cosa è stato costruito

`panels/cartella.js` era un pannello **freddo con un accento manila**: la
linguetta e il segno dei file. Adesso è un pannello a **superficie manila**, con
la polarità rovesciata.

| | prima | dopo |
|---|---|---|
| corpo | `--bg-raised` (L 37) | **`--manila`** (L 146) |
| testo delle voci | `--txt-primary` (L 224) | **`--bg-void`** (L 19) |
| riga sotto il puntatore | `--fill-1` | **`--manila-viva`** — §26.5 alla lettera |
| segno del file | `--manila` | `--bg-void` |
| tipo della voce | `--txt-ghost` | `--bg-panel` |

**Perché la polarità si rovescia**: `--txt-primary` su `--manila` fa **1,68:1**,
illeggibile. `--bg-void` su `--manila` fa **6,12:1**, sopra il 4,5:1 che AA
chiede a un corpo di testo. È la stessa mossa che `panels/tabella.js` fa già
sulla propria intestazione.

**Perché il caldo qui significa** (§11.6 regola 2): manila è l'identità della
cartella nel riferimento, non un colore scelto per alzare una metrica. Il
riferimento misura il proprio caldo al **5,70 %** della superficie e per due
terzi viene da **un** riquadro — `CIRCA COMPANY`, 144×97 su un'immagine larga
901, il **2,75 % da solo** — che è un pannello con la superficie manila.

## E i dati sono veri

`alimenta` deriva le voci da **`source.tree`**, che il core già pubblica:
`{files: [{path, bytes}]}`, percorsi relativi alla radice. Da lì escono le voci
di primo livello — le directory una volta sola, i file sciolti per nome.
Nessun segnaposto: l'invariante 23 non li ammette, e un elenco finto dentro una
cartella è esattamente il caso che quella regola descrive.

---

## ⚠️ Il posto non c'è, ed è misurato

La scena `avvio` non ha una cella libera che non tocchi il disco di §25.

```
pavimento   x 0-1536, y 32-815
disco       x 605-931, y 259-585
telemetry   x    4- 596  y  36-372      globe   x   4-476  y 380-716
agents      x  964-1436  y  36-372      news    x 964-1436  y 380-716
```

I rettangoli liberi e **fuori dal disco**:

| dove | dimensione | verdetto |
|---|---|---|
| sopra il disco | 368 × 223 | **troppo stretto**: la `min-width` di un pannello è 440 px |
| fra globo e disco | 129 × 336 | troppo stretto |
| fra disco e news | 33 px | troppo stretto |
| sotto i pannelli | 1536 × 98 | **troppo basso** per l'anatomia a cinque parti di §10.2, e ci sta il catalogo |

**Il turno 6 e il turno 7 sono accoppiati**, e §4 li ordina come se fossero
indipendenti. Il posto per una superficie calda lo libera la decisione sul
centro, che è il turno 7.

### E la taglia giusta è già misurata

Una cartella in una cella `[4, 2]` — 472×337 — porterebbe il corpo manila a
**~9,5 % dello schermo da sola**: oltre il tetto di 6 % della forbice di §11.8.
Il caldo che *significa* diventerebbe caldo che *riempie*.

La cella registrata è **`[4, 3, 3, 1]`** — tre colonne per una riga — che è la
taglia che avvicina la forbice invece di sfondarla. È scritta accanto alla
misura, in `moduli.js`.

---

## ⚠️ Il difetto che ha morso quindici volte, adesso ha un test

Un backtick dentro un blocco `export const css = \`…\`` **chiude il template
literal**: il modulo non si carica più e l'errore che arriva è
`SyntaxError: Unexpected identifier 'famiglia'` — il nome del file che si stava
citando in un commento. Non dice né dove né perché.

È successo **quindici volte in una giornata**, sempre allo stesso modo, sempre
trovato a mano dopo che qualcosa era già rotto. Quindici volte non è
distrazione: è una regola che manca.

`tests/test_fogli_di_stile.py` scandisce ogni blocco di stile del progetto e
nomina file, export e citazione incriminata. **Verificato che morda**: rimesso
un backtick in `cartella.js`, il test fallisce nominandolo; tolto, torna verde.

Il secondo test del file è meno ovvio e serve altrettanto: **conta i fogli
trovati**. Un controllo che non trova niente da controllare passa sempre, e il
giorno che l'espressione di apertura smettesse di combaciare nessuno se ne
accorgerebbe.

---

## Misure

| | |
|---|---|
| audit `cartella` | **0 / 0** |
| suite | **564 passed** (562 + i due dei fogli) |
| densità della scrivania | **invariata** — il pannello non è nella scena |

Il ciclo §11.7 è stato eseguito in galleria e **guardato**: superficie calda,
testo scuro leggibile, gerarchia fra nome e tipo, testa e piede freddi che
tengono l'anatomia di §10.2, percorso nel piede.

---

## Che cosa NON è stato fatto

- **Il caldo della scrivania non si è mosso**, e non poteva: il pannello non ha
  una cella nella scena `avvio`. Resta a 0,2 %. È il turno 7.
- **Le cartelle libere sul piano** (§26.5, le icone trascinate) restano zero, e
  restano una cosa dell'utente: popolarle da codice sarebbe inventare lo stato
  di qualcun altro. Il conto è comunque contro: una cartella libera vale lo
  **0,134 %** dello schermo, e per arrivare al 5,70 % ne servirebbero
  quarantadue.
- **`percorso`** viene da `msg.radice`, che `source.tree` **non pubblica**: nel
  piede resta il raggruppamento senza percorso risolto. §26.5 lo chiede per le
  cartelle che contengono file veri — va aggiunto al topic, ed è un lavoro sul
  core.
