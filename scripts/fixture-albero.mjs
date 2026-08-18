/* Genera la fixture dell'albero dei sorgenti per la galleria.
 *
 *   npm run fixtures
 *
 * §11.9 concede alla galleria dati finti purche' abbiano la FORMA di dati
 * veri. Qui non serve la concessione: i file sono quelli veri del progetto,
 * letti da `git ls-files`. Un elenco inventato avrebbe percorsi tutti lunghi
 * uguali e dimensioni tonde, e la nuvola risultante mentirebbe sulla forma
 * del progetto — che e' esattamente cio' che il pannello deve mostrare.
 *
 * E' una ISTANTANEA: la si rigenera quando si vuole aggiornarla. Nel core il
 * pannello riceve l'albero vero dal topic `source.tree`, senza istantanee.
 */

import { execFileSync } from "node:child_process";
import { statSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const USCITA = resolve(RADICE, "ui/src/gallery/fixtures/albero.js");

const file = execFileSync("git", ["ls-files"], { cwd: RADICE, encoding: "utf-8" })
  .trim()
  .split("\n")
  .filter(Boolean)
  .map((p) => ({ path: p, bytes: statSync(resolve(RADICE, p)).size }));

const totale = file.reduce((n, f) => n + f.bytes, 0);

await writeFile(
  USCITA,
  `/* GENERATO da scripts/fixture-albero.mjs — non modificare a mano.\n` +
  ` *\n` +
  ` * Istantanea di \`git ls-files\` con le dimensioni reali.\n` +
  ` * ${file.length} file, ${(totale / 1024).toFixed(0)} kB.\n` +
  ` */\n\n` +
  `export const ALBERO = ${JSON.stringify(file, null, 0).replace(/\},\{/g, "},\n  {").replace(/^\[/, "[\n  ").replace(/\]$/, ",\n]")};\n`,
  "utf-8",
);

console.log(`${file.length} file, ${(totale / 1024).toFixed(0)} kB -> ${USCITA}`);
