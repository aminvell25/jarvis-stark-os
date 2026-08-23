# La guardia della scrivania torna a dire la verità

**Data:** 23 agosto 2026
**Comando:** `npm run verifica:scrivania` (`app/main.js --verifica-scrivania`)
**Rollback:** `bc07a11`

## Il difetto

`verifica:scrivania` usciva **1** in ogni caso. Due criteri su tredici erano
falsi per costruzione, e nessuno dei due perché l'applicazione fosse rotta.

### ① Il criterio A di §13 contava OTTO voci d'indice

```js
const dockOk = esito.dock.length === 8 && …
```

Otto era il numero dei moduli indicizzati il giorno in cui la riga fu scritta.
Da allora sono entrati **meteo** e **globo**: i moduli indicizzati sono
**dieci**, misurati con `moduliIndicizzati()`.

```
telemetria agenti console file sorgente cartella browser news meteo globo
```

Il criterio non misurava l'indice: ricordava quanto era grande.

### ② Il criterio del fuoco leggeva un bordo che §10.5 ha tolto

```js
const leggi = (el) => el && { bordo: getComputedStyle(el).borderTopColor, … };
const fuocoOk = … conFuoco.bordo !== senzaFuoco.bordo;
```

`app.css` dichiara `.winbox { border: 0 }` — §10.5 regola 1, misurata su sette
pannelli del riferimento, **zero** dei quali ha una cornice sui quattro lati.
Senza bordo dichiarato, `borderTopColor` **ricade sul `color` ereditato**, che è
`--txt-primary` `#cdeef3` — cioè lo stesso valore di `--cy-100`, e identico sui
due pannelli. Il criterio confrontava due volte la stessa stringa.

**È il difetto peggiore dei due:** una guardia sempre rossa smette di segnalare.
Chi lanciava il comando vedeva `exit 1` e non sapeva più che cosa significasse.

## La correzione

| criterio | prima | adesso |
|---|---|---|
| indice | `dock.length === 8` | gli **id** delle tessere `[data-tipo="modulo"]` uguagliano `moduliIndicizzati()` |
| fuoco | `borderTopColor` dei due pannelli diverso | lo sfondo del **marcatore** (`::before`) uguaglia il **token dichiarato**, risolto dal foglio di stile |

Il criterio dell'indice è più forte di un conteggio: pretende che l'indice
elenchi *esattamente* i moduli indicizzati — né uno di meno (un modulo
irraggiungibile) né uno di più (una voce che apre ciò che la registry non
conosce). Un numero non lo direbbe.

Il criterio del fuoco è più forte del «devono differire»: pretende il token
`--cy-500`, non una qualunque differenza. Due colori sbagliati ma diversi
passavano il vecchio criterio.

`ui/src/app.js` espone `moduliIndicizzati` su `window.__scrivania`. È di sola
lettura, e serve perché il conto lo faccia la registry invece di un letterale.

## Misure

Rilevate nella finestra vera, massimizzata, scena `avvio`:

```
tessere [data-tipo="modulo"]   10   telemetria agenti console file sorgente
                                    cartella browser news meteo globo
moduliIndicizzati()            10   stessi id, stesso insieme
commuta e torna                tutte e dieci

marcatore col fuoco     rgb(77, 208, 225)    = --cy-500  #4dd0e1
marcatore senza fuoco   rgb(162, 173, 177)   = --icona   #a2adb1
ombra (entrambi)        rgba(0,0,0,0.18) 0px 2px 3px 0px
```

L'ombra misurata è **esattamente** §10.5 regola 4: scostamento ~2 px, raggio
~3 px, nero ad alpha ~0,18.

## I due controlli — una guardia che non fallisce non è una guardia

Il comando che passa non dimostra niente da solo. Le due rotture sono state
introdotte apposta e rimosse subito dopo:

| rottura introdotta | esito atteso | esito misurato |
|---|---|---|
| `.winbox.focus::before { background: var(--icona) }` (il fuoco non si vede più) | 1 | **1** |
| `voci()` filtra via `globo` (un modulo irraggiungibile dall'indice) | 1 | **1** |

E senza rotture: **exit 0**.

## Che cosa NON è cambiato

- **Nessun pixel.** Le modifiche a `app.css` sono soltanto commenti: la regola
  `.winbox.focus::before/::after { background: var(--cy-500) }` è quella di
  prima. Per questo **non** è stato eseguito il ciclo §11.7 — non c'è un
  componente visivo nuovo da guardare.
- **Il marcatore non raddoppia.** Un commento diceva che col fuoco «raddoppia»:
  non è mai stato vero, e non deve esserlo — §10.5 regola 3 misura i triangoli
  fra **3 e 5 px**, e `--s-1` è 4. Il doppio cadrebbe fuori dall'intervallo
  misurato. Aveva ragione il codice; il commento è stato corretto.

## Limite dichiarato

Il criterio del fuoco legge `::before`. Il marcatore è **una coppia** —
`::before` e `::after` — e la regola CSS li tratta insieme. Se qualcuno le
separasse, `::after` non sarebbe verificato. Il modo di allargare è aggiungere
la seconda lettura a `leggi()`, non fidarsi che restino accoppiati.
