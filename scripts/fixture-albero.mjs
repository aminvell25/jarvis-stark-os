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

/* ── le note per la board investigativa (Fase 6) ────────────────────────────
 *
 * Carte con testo VERO: i documenti di accettazione delle fasi, che esistono
 * e che qualcuno ha scritto. Una board con del lorem ipsum sarebbe la cosa
 * che §11.9 vieta al primo paragrafo. */
const { readFile, readdir } = await import("node:fs/promises");
const ACCETTAZIONE = resolve(RADICE, "docs/acceptance");
const NOTE_USCITA = resolve(RADICE, "ui/src/gallery/fixtures/note.js");

const note = [];
for (const nome of (await readdir(ACCETTAZIONE)).filter((n) => n.endsWith(".md")).sort()) {
  const testo = await readFile(resolve(ACCETTAZIONE, nome), "utf-8");
  const righe = testo.split("\n");
  const titolo = (righe.find((r) => r.startsWith("# ")) ?? nome).replace(/^#\s*/, "");
  // Il primo paragrafo vero: si saltano titolo, metadati e righe di regola.
  const corpo = righe
    .filter((r) => r.trim() && !r.startsWith("#") && !r.startsWith("---") && !r.startsWith("**Data"))
    .slice(0, 3)
    .join(" ")
    .replace(/[*`|]/g, "")
    // Via i pittogrammi: nei documenti sono legittimi, ma sono glifi a colori
    // e in un'interfaccia monocroma rompono la palette senza che l'audit li
    // veda — non sono un colore CSS, sono un font. L'estratto e' comunque un
    // troncamento, non il documento.
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, "")
    .replace(/\s{2,}/g, " ")
    .trim()
    .slice(0, 220);
  note.push({ file: nome, titolo, corpo, byte: Buffer.byteLength(testo) });
}

await writeFile(
  NOTE_USCITA,
  `/* GENERATO da scripts/fixture-albero.mjs — non modificare a mano.\n` +
  ` *\n * ${note.length} documenti veri da docs/acceptance/.\n */\n\n` +
  `export const NOTE = ${JSON.stringify(note, null, 2)};\n`,
  "utf-8",
);
console.log(`${note.length} note -> ${NOTE_USCITA}`);
