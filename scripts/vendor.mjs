/* Copia in `ui/vendor/` le librerie di terze parti che il renderer carica.
 *
 * Perche' copiare invece di puntare a node_modules: la galleria e' servita da
 * `ui/` via HTTP e l'app Electron carica da `file://`. Un percorso relativo a
 * node_modules funzionerebbe in uno solo dei due, e il ciclo §11.7 giudicherebbe
 * un rendering diverso da quello che gira. Stessa ragione dei font.
 *
 * Tutte le librerie sono in SPEC §4/§11.3, con le licenze che la specifica
 * dichiara e che questo script rilegge da package.json a ogni esecuzione,
 * invece di fidarsi di una tabella scritta a mano che invecchia.
 *
 *   npm run vendor
 *
 * ── Specificatori nudi ─────────────────────────────────────────────────────
 * Gli addon three.js importano `'three'`, e d3-shape importa `'d3-path'`.
 * Senza bundler il browser non sa risolverli: ci pensa l'IMPORT MAP dichiarata
 * in `ui/gallery.html` e `ui/index.html`. La scelta e' in FASE-05.md, R44 —
 * un bundler metterebbe un passo di build fra il sorgente e cio' che gira, e
 * il ciclo §11.7 giudicherebbe di nuovo un file diverso da quello scritto.
 * Le voci della mappa devono restare allineate a questo elenco.
 */

import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const DEST = resolve(RADICE, "ui/vendor");

/** [pacchetto, [file dentro il pacchetto], destinazione dentro ui/vendor] */
const COPIE = [
  ["augmented-ui", ["augmented-ui.min.css"], ""],
  ["uplot", ["dist/uPlot.min.css", "dist/uPlot.esm.js"], ""],
  ["winbox", ["dist/winbox.bundle.min.js"], ""],

  // three: il core come file unico, gli addon lines/ perche' l'invariante 21
  // vieta LineBasicMaterial e senza questi il wireframe resta a 1px.
  // Da r150 in poi il build e' spezzato: `three.module.js` importa
  // `three.core.js` per percorso relativo. Copiarne uno solo da' un 404 che
  // in console sembra un problema di import map e non lo e'.
  ["three", ["build/three.module.js", "build/three.core.js"], "three"],
  [
    "three",
    [
      "examples/jsm/lines/Line2.js",
      "examples/jsm/lines/LineGeometry.js",
      "examples/jsm/lines/LineMaterial.js",
      "examples/jsm/lines/LineSegments2.js",
      "examples/jsm/lines/LineSegmentsGeometry.js",
    ],
    "three/addons/lines",
  ],

  ["animejs", ["dist/bundles/anime.esm.min.js"], ""],
  ["pixi.js", ["dist/pixi.min.mjs"], ""],

  // d3-shape: solo il sottoalbero che serve ad `arc()`. L'indice completo
  // tirerebbe quaranta moduli per una funzione sola.
  ["d3-shape", ["src/arc.js", "src/constant.js", "src/math.js", "src/path.js"], "d3-shape"],
  ["d3-path", ["src/index.js", "src/path.js"], "d3-path"],
];

async function licenza(pacchetto) {
  const p = JSON.parse(
    await readFile(resolve(RADICE, "node_modules", pacchetto, "package.json"), "utf-8")
  );
  return `${p.license} ${p.version}`;
}

await mkdir(DEST, { recursive: true });

const righe = new Map(); // pacchetto -> Set<file di destinazione>
for (const [pacchetto, file, sotto] of COPIE) {
  const cartella = sotto ? resolve(DEST, sotto) : DEST;
  await mkdir(cartella, { recursive: true });
  for (const f of file) {
    const nome = f.split("/").pop();
    await copyFile(
      resolve(RADICE, "node_modules", pacchetto, f),
      resolve(cartella, nome)
    );
    const rel = sotto ? `${sotto}/${nome}` : nome;
    console.log(`  ${rel}`);
    if (!righe.has(pacchetto)) righe.set(pacchetto, new Set());
    righe.get(pacchetto).add(rel);
  }
}

const tabella = [];
for (const [pacchetto, file] of righe) {
  tabella.push(
    `| ${[...file].map((f) => `\`${f}\``).join("<br>")} | ${pacchetto} | ${await licenza(pacchetto)} |`
  );
}

await writeFile(
  resolve(DEST, "README.md"),
  "# Librerie di terze parti\n\n" +
    "Copiate da `node_modules` con `npm run vendor` — vedi `scripts/vendor.mjs`.\n" +
    "Non modificarle a mano: la prossima esecuzione le sovrascrive.\n\n" +
    "| File | Pacchetto | Licenza |\n|---|---|---|\n" + tabella.join("\n") + "\n\n" +
    "Gli specificatori nudi (`three`, `d3-path`) li risolve l'import map in\n" +
    "`ui/gallery.html` e `ui/index.html`. Aggiungendo una libreria qui, la voce\n" +
    "va aggiunta anche li'.\n\n" +
    "Sono esenti dall'audit del SORGENTE (livello 2): i letterali dentro una\n" +
    "libreria di terzi non sono nostri da correggere, e la scelta di usarla e'\n" +
    "gia' stata fatta in SPEC §11.3. **Restano soggette all'audit del valore\n" +
    "calcolato (livello 1)** su ogni elemento che finisce nei nostri componenti:\n" +
    "se uPlot dipinge un asse con un colore fuori palette, l'audit lo vede.\n",
  "utf-8",
);
console.log(`\n${[...righe.values()].reduce((n, s) => n + s.size, 0)} file + README in ui/vendor/`);
