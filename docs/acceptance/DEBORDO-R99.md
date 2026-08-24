# I cinque pannelli che debordavano

**Data:** 24 agosto 2026 · **Rollback:** `d3d8978`

La Fase 0 li aveva trovati e non corretti: un layout salvato a 1280 e
ripristinato a 1536 lasciava **cinque pannelli su sei** col contenuto fuori dal
proprio corpo — `telemetry 65x0`, `globe 53x0`, `agents 53x0`, `news 61x24`,
`files 65x0`.

## La causa: `dentroArea()` taglia e non alza mai

`min-width` è dichiarata **in pixel** nel CSS di ogni componente
(`calc(var(--grid) * 5)` = 550 px per `telemetria`), e `--grid` è una costante:
non dipende dal viewport. A 1280 la cella vale 106 px e cinque colonne fanno
533 — **sotto il minimo**. Il ripristino riporta quel 533 a 1536, dove
`dentroArea()` lo taglia se serve ma **non lo alza mai**, e 533 resta 533. È
R99 alla lettera: *una cella troppo stretta non stringe il pannello, lo fa
debordare*.

## La correzione: mai sotto il minimo dichiarato

`applicaGeometria()` alza la geometria al minimo del componente prima di
scriverla.

⚠️ **Alzare al minimo non è scalare.** La scala fu provata e ritirata il 23
agosto perché spostava la disposizione dell'utente quando nessuno aveva
cambiato schermo. Questo tocca **solo i pannelli già rotti**, e del minimo
indispensabile: chi sta sopra il proprio minimo non si muove di un pixel.

## Tre difetti trovati strada facendo

**① Tre scrittori per la stessa verità.** `applicaGeometria` non era l'unica via:
`riadatta()`, `applicaScena()` e `affianca()` scrivevano `box.resize()` diretto.
Quindi ogni ridimensionamento della finestra disfaceva quello che il ripristino
aveva appena aggiustato — `telemetria` tornava da 550 a 485 al primo `resize`.
Adesso in `scrivania.js` non resta **nessuno** scrittore diretto.

**② Il minimo si chiedeva all'oggetto sbagliato.** `cornice.pannello?.radice`
esiste solo su **tre pannelli su sei**: `telemetry`, `files` e `cartella` non
ritornano `radice` da `crea()`. Chiederlo a loro dava `undefined`, quindi minimo
zero, quindi nessuna protezione — **proprio sui due che debordavano di 65 px**.
Adesso il minimo si legge dal DOM, che c'è sempre, prendendo il massimo fra
l'ospite della cornice e il suo primo figlio.

**③ La `min-width` sta sul pannello, non sulla finestra.** Impostare la finestra
al minimo del corpo lascerebbe il corpo sotto il minimo, e il pannello
deborderebbe lo stesso — di poco, che è il modo peggiore di sbagliare perché non
si vede. Si misura lo scarto fra i due, su questa finestra, adesso.

## E `news`, che debordava di 4 px a ogni larghezza

Non era il layout: la finestra è alta 164 e il contenuto ne voleva **168**.
Quattro pixel costanti, raccolti da mesi senza che nessun criterio li guardasse.

Stavano nello stato vuoto: `padding: var(--s-4)`, **32 px sopra e sotto** un
messaggio che `place-content: center` centra già. Non centrano niente di più:
aggiungono altezza. A `--s-3` il debordo va a zero e il pannello **resta nella
cella che la scena gli ha dato** invece di crescerle addosso.

⚠️ La prima correzione era una `min-height` di 176. Funzionava sul debordo e
rompeva un altro criterio: `affianca` non tornava più identico, perché il
pannello cresceva da 164 a 176 e la cella della scena è 164. **Ritirata.**

## Esito

```
viewport     debordano
1280x800     nessuno
1536x843     nessuno        (anche col layout salvato a 1280)
1920x1140    nessuno
```

## La guardia — e il primo posto in cui l'ho messa era sbagliato

`verifica:scrivania` **adesso boccia**. Ma la prima stesura leggeva i pannelli
insieme a tutto il resto, cioè **dopo** che la prova preme Alt+T: `affianca()`
ricompone dalle celle, e su una scrivania ricomposta il debordo non esiste per
costruzione. Verificato togliendo il minimo: **la guardia restava verde mentre
cinque pannelli erano rotti**.

È §11.7 regola 4 al rovescio — non *«il criterio è vero per assenza del
fenomeno»* ma *«il criterio guarda dove il fenomeno non passa»*. Adesso legge
**prima di toccare qualunque cosa**, sullo stato ripristinato.

**Controllo**: tolto il minimo, `verifica:scrivania` esce **1** e nomina tutti e
cinque. Rimesso, esce **0**.

⚠️ **Limite dichiarato**: la stessa asserzione dentro `--scrivania` stampa
`R99 — 5 pannelli…` ma **non propaga il codice di uscita**: né `app.exit(1)`, né
`process.exitCode`, né `process.exit(1)` arrivano al processo padre da quella
via. Non ne conosco la causa. La guardia che boccia è quindi
`verifica:scrivania`; nello scatto il numero si stampa e si legge.

E `scripts/app.mjs` aveva un difetto suo: `figlio.on("exit", (code) =>
process.exit(code ?? 0))` trasformava in **successo** ogni figlio ucciso da un
segnale, perché in quel caso `code` è `null`. Corretto.

## Le misure

Tre giri, fondo pulito: dev.std **34,0** · entropia **2,21** · `L>60` **25,3–25,4 %**
· caldo 3,8 % · barra 63,3 %. Suite **572 passed**.

⚠️ `L>60` sta 0,3 punti sotto la sessione precedente (25,6–25,75 %), con margine
+0,3 sulla soglia. **Non ne conosco la causa**: fra i due gruppi la barra è
passata da `NOMINAL` ad `DEGRADED` (temp 55 °C), che cambia un chip di colore, e
i dati vivi si muovono. Lo scrivo invece di attribuirlo.
