# §26.5 — «anche un layout di sole icone va rimesso», e nessuno lo prova

**Data:** 29 agosto 2026 · **Stato: buco DICHIARATO, non chiuso**

## La proprietà

`ui/src/app.js:283-287` la enuncia, ed è vera:

> ⚠️ Anche un layout con SOLE icone va rimesso. Prima la condizione guardava i
> pannelli e basta: una scrivania con la disposizione dichiarata e tre icone sul
> fondo sarebbe ripartita senza le icone, cioè §26.5 sarebbe stata rotta dal
> guardiano di §26.10 punto 1.

La guardia sta a `ui/src/app.js:303`:

```js
const roba = (layout?.pannelli?.length ?? 0) + suoFondo;
if (!roba) return;
```

## Chi NON la custodisce

**`tests/test_layout.py::test_un_layout_di_sole_icone_...`** asseriva su
`Layout.vuoto()`, un predicato Python che il renderer non chiama mai. È stato
riscritto sui campi — che è ciò che la guardia legge — ma resta un test di
forma, non di comportamento: misura il dato, non il ripristino.

**`test_10_riavviato_il_core_e_ANCORA_LI` NON la copre**, e si dimostra senza
avviare nulla: `test_11_una_cartella_aperta_si_riapre` pretende che
`esiti_icone["riavvio"]["ripristino"]["messi"]` contenga una voce `cartella.*`.
Ma `window.__layout.ripristino` si scrive **solo dopo** `if (!roba) return`, e
una cartella aperta **è** un pannello. Quindi in ogni esecuzione della fixture
`layout.pannelli` è non vuoto, e la guardia si attraversa **dai pannelli**: il
caso `pannelli == 0` non è mai esercitato.

**Nessun test JS.** `suoFondo` compare in un solo posto in tutto l'albero —
`ui/src/app.js:300-301` — verificato per grep su `ui/`, `app/`, `scripts/`.

## ⚠️ Perché è dichiarato invece che chiuso

Perché scrivere in `test_10` che copre §26.5 sarebbe stata **una ricevuta
falsa** — la stessa specie di riga corretta nel commit `f5c62a4`, dove un
annuncio dichiarava compiuta un'azione che non era ancora riuscita.

Un buco dichiarato vale più di una copertura dichiarata e assente.

## Il custode che manca, e la sua bocciatura

Va in `scripts/prova-icone.mjs`, non in un docstring: una sezione che prima
della chiusura chiude **tutti** i pannelli — cartella aperta compresa — attende
oltre `RITARDO_MS = 500` (`ui/src/desk/layout.js:24`), verifica su disco
`pannelli: []` con `icone` non vuoto, riavvia, e pretende le icone al loro
posto.

**La bocciatura che lo renderebbe un custode e non un ornamento**: in una copia,
sostituire `ui/src/app.js:303` con `const roba = (layout?.pannelli?.length ?? 0)`
— cioè togliere `+ suoFondo`. La sezione nuova deve diventare **rossa**, mentre
`test_10` e `test_11` restano verdi. Se anche il caso nuovo resta verde, non è
il custode di niente e non va scritto.

## Che cosa resta non misurabile

L'ultimo centimetro — dal messaggio `ui.layout` al pixel — non è stato visto:
la catena core → messaggio è misurata, il resto è letto nel codice.
