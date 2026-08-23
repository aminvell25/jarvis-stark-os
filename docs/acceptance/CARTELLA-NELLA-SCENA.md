# Turno 7 — il caldo entra nella forbice, e il centro resta libero

> `PIANO-CORE-E-DENSITA.md` §4 turno 7: *«abbandono del centro libero,
> misurato»*. **Non è stato necessario abbandonarlo.**

---

## Il risultato

| | prima | dopo | riferimento |
|---|---|---|---|
| **caldo** | 0,2 % | **3,2 %** ✅ | 5,70 % |
| entropia | 1,76 | **1,93** | 3,32 |
| `L>60` | 12,5 % | **16,45 %** | 42,1 % |
| dev.std | 22,6 | **28,9** | 55,7 |
| `L>120` | 1,0 % | **3,9 %** | — |
| **disco coperto** | 0,0 % | **0,0 %** | — |

**Il caldo è dentro la forbice 3–6 % per la prima volta**, e da
`node scripts/densita.mjs` è sparito dalla lista dei criteri falliti. Restano
entropia, dev.std e riempito.

+0,17 di entropia in un turno. Per contesto, `PIANO-CORE-E-DENSITA.md` §9 conta
**+0,38 in sei giorni**.

---

## Due celle sbagliate prima di quella giusta

### ① Il turno 6 aveva concluso «non c'è posto». Aveva torto, e su un numero

Contava una `min-width` di **440 px** — che è quella di **telemetria**, non
della cartella. La cartella dichiara `calc(var(--grid) * 2.4)` = **264 px**, e
nel varco sopra il disco, largo **368**, ci sta.

Il turno 6 aveva letto la min-width di un altro pannello e concluso per tutti.

### ② La prima cella provata, `[4, 3, 4, 1]`, sotto il disco

Misurata: il disco passava da **0,0 % a 6,7 %** coperto. E lo scatto mostrava
un secondo difetto che nessun numero aveva segnalato: **il catalogo copre metà
del pannello**, e i nomi dei file diventano illeggibili.

Due difetti, uno visto da una misura e uno da uno sguardo. È il motivo per cui
§11.7 mette lo sguardo **dopo** la misura invece che al posto suo.

### ③ La cella tenuta, `[5, 0, 3, 1]`, sopra il disco

Una riga sola, `x 604–956 · y 36–200`, contro un disco che comincia a
**y 259**. Il centro libero di §25 resta libero, e non serve nessuna decisione
sul suo abbandono.

---

## Che cosa il pannello mostra

Dati veri da `source.tree`: `.gitignore`, `.python-version`, `CLAUDE.md`,
`INSTALLA.md`, `PRIMO-PROMPT.md`… testa `SORGENTI · 20 voci`, piede
`9 file veri · raggruppamento`. Nessun segnaposto.

**Guardato** (§11.7): superficie calda leggibile, testo scuro, gerarchia fra
nome e tipo, testa e piede freddi che tengono l'anatomia di §10.2.

---

## Misure

Suite **564 passed**. Occlusione: pavimento coperto dai pannelli 61,6 %,
cornice 7,1 %, libero 31,3 % — il pavimento nudo scende da 36,5 % a 31,3 %, che
è la seconda cosa che il piano generale chiede (riferimento 21,9 %).

---

## Che cosa NON è stato fatto

- **Il caldo è a 3,2 %, il riferimento a 5,70 %.** Siamo nella forbice, non al
  bersaglio. La differenza è un'altra superficie manila, e nella scena non c'è
  un secondo varco: il prossimo passo tocca la composizione, non i colori.
- **Entropia 1,93 contro 2,40** di soglia e **3,32** del riferimento. Il grosso
  di quella distanza è contenuto fotografico, che `DIVARIO-PREMIUM.md` §6
  dichiara irraggiungibile senza un modulo Media.
- **Le cartelle libere sul piano** restano zero, e restano una cosa dell'utente.
- **`percorso` resta senza percorso risolto**: `source.tree` non pubblica la
  radice. §26.5 lo chiede, ed è un lavoro sul core.
- **`verifica:scrivania` esce 1** per i due difetti preesistenti già aperti —
  il conteggio del dock, adesso 10 invece di 8, e la cornice col fuoco identica
  a quella senza.
