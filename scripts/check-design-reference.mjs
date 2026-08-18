/* Coerenza fra docs/design-reference/README.md e le immagini presenti.
 *
 * Il README e' la mappa che dice a ogni sessione quale famiglia seguire e a
 * cosa serve ciascuna immagine (SPEC §11.7 passo 4). Una mappa che elenca un
 * file inesistente, o che tace su un file presente, e' peggio di nessuna
 * mappa: la si legge e ci si fida.
 */

import { readFile, readdir } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RADICE = resolve(fileURLToPath(new URL("../docs/design-reference", import.meta.url)));

const testo = await readFile(resolve(RADICE, "README.md"), "utf-8");
const citate = new Set([...testo.matchAll(/`([\w.-]+\.png)`/g)].map((m) => m[1]));

let guasti = 0;
for (const famiglia of ["famiglia-a", "famiglia-b"]) {
  const presenti = new Set(
    (await readdir(resolve(RADICE, famiglia))).filter((f) => f.endsWith(".png"))
  );
  const mancanti = [...presenti].filter((f) => !citate.has(f));
  const fantasmi = [...citate].filter(
    (f) => !presenti.has(f) && f.startsWith(famiglia === "famiglia-a" ? "0" : "0")
  );

  console.log(`${famiglia}: ${presenti.size} immagini`);
  for (const f of mancanti) {
    console.error(`  PRESENTE MA NON CITATA nel README: ${f}`);
    guasti++;
  }
  void fantasmi;   // i nomi si ripetono fra le due famiglie: vedi sotto
}

// I nomi si ripetono fra famiglia-a e famiglia-b (01-…, 02-…), quindi il
// controllo inverso va fatto sull'unione, non per famiglia.
const tutte = new Set();
for (const famiglia of ["famiglia-a", "famiglia-b"])
  for (const f of await readdir(resolve(RADICE, famiglia)))
    if (f.endsWith(".png")) tutte.add(f);

for (const f of citate) {
  if (!tutte.has(f)) {
    console.error(`  CITATA NEL README MA ASSENTE: ${f}`);
    guasti++;
  }
}

console.log(guasti === 0
  ? "README coerente con le immagini presenti."
  : `${guasti} incoerenze.`);
process.exit(guasti === 0 ? 0 : 1);
