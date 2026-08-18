# Librerie di terze parti

Copiate da `node_modules` con `npm run vendor` — vedi `scripts/vendor.mjs`.
Non modificarle a mano: la prossima esecuzione le sovrascrive.

| File | Pacchetto | Licenza |
|---|---|---|
| `augmented-ui.min.css` | augmented-ui | BSD-2-Clause |
| `uPlot.min.css` | uplot | MIT |
| `uPlot.esm.js` | uplot | MIT |
| `winbox.bundle.min.js` | winbox | Apache-2.0 |

Sono esenti dall'audit del SORGENTE (livello 2): i letterali dentro una
libreria di terzi non sono nostri da correggere, e la scelta di usarla e'
gia' stata fatta in SPEC §11.3. **Restano soggette all'audit del valore
calcolato (livello 1)** su ogni elemento che finisce nei nostri componenti:
se uPlot dipinge un asse con un colore fuori palette, l'audit lo vede.
