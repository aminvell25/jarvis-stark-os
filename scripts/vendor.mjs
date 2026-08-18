/* Copia in `ui/vendor/` le librerie di terze parti che il renderer carica.
 *
 * Perche' copiare invece di puntare a node_modules: la galleria e' servita da
 * `ui/` via HTTP e l'app Electron carica da `file://`. Un percorso relativo a
 * node_modules funzionerebbe in uno solo dei due, e il ciclo §11.7 giudicherebbe
 * un rendering diverso da quello che gira. Stessa ragione dei font.
 *
 * Tutte le librerie sono in SPEC §4/§11.3, con le licenze che la specifica
 * dichiara: augmented-ui BSD-2, uPlot MIT, WinBox Apache-2.0.
 *
 *   npm run vendor
 */

import { copyFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const DEST = resolve(RADICE, "ui/vendor");

const FILE = [
  ["augmented-ui/augmented-ui.min.css", "augmented-ui.min.css", "BSD-2-Clause"],
  ["uplot/dist/uPlot.min.css", "uPlot.min.css", "MIT"],
  ["uplot/dist/uPlot.esm.js", "uPlot.esm.js", "MIT"],
  ["winbox/dist/winbox.bundle.min.js", "winbox.bundle.min.js", "Apache-2.0"],
];

await mkdir(DEST, { recursive: true });
const righe = [];
for (const [src, dst, licenza] of FILE) {
  await copyFile(resolve(RADICE, "node_modules", src), resolve(DEST, dst));
  console.log(`  ${dst}`);
  righe.push(`| \`${dst}\` | ${src.split("/")[0]} | ${licenza} |`);
}

await writeFile(
  resolve(DEST, "README.md"),
  "# Librerie di terze parti\n\n" +
    "Copiate da `node_modules` con `npm run vendor` — vedi `scripts/vendor.mjs`.\n" +
    "Non modificarle a mano: la prossima esecuzione le sovrascrive.\n\n" +
    "| File | Pacchetto | Licenza |\n|---|---|---|\n" + righe.join("\n") + "\n\n" +
    "Sono esenti dall'audit del SORGENTE (livello 2): i letterali dentro una\n" +
    "libreria di terzi non sono nostri da correggere, e la scelta di usarla e'\n" +
    "gia' stata fatta in SPEC §11.3. **Restano soggette all'audit del valore\n" +
    "calcolato (livello 1)** su ogni elemento che finisce nei nostri componenti:\n" +
    "se uPlot dipinge un asse con un colore fuori palette, l'audit lo vede.\n",
  "utf-8",
);
console.log(`\n${FILE.length} file + README in ui/vendor/`);
