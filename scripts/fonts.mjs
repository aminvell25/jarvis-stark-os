/* Vendorizza i cinque woff2 nel repository.
 *
 * Perche' copiarli invece di puntare a node_modules: il ciclo di verifica
 * visiva di SPEC §11.7 fa uno screenshot e lo giudica. Se i font vengono da
 * uno stato esterno, lo stesso componente rende diversamente su una macchina
 * diversa e il giudizio non e' riproducibile.
 *
 * I pesi sono quelli di §11.3 (Barlow 400/500/600, Plex Mono 400/500), non una
 * scelta arbitraria. Sottoinsieme `latin`: il progetto e' in italiano e
 * l'inglese tecnico, e i sottoinsiemi ulteriori sono peso senza lettori.
 *
 *   npm run fonts
 */

import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const DEST = resolve(RADICE, "ui/src/style/fonts");

const FAMIGLIE = [
  { pkg: "@fontsource/barlow-semi-condensed", slug: "barlow-semi-condensed", pesi: [400, 500, 600] },
  { pkg: "@fontsource/ibm-plex-mono", slug: "ibm-plex-mono", pesi: [400, 500] },
];

await mkdir(DEST, { recursive: true });

const licenze = [];
let copiati = 0;

for (const { pkg, slug, pesi } of FAMIGLIE) {
  const base = resolve(RADICE, "node_modules", pkg);
  for (const peso of pesi) {
    const src = resolve(base, "files", `${slug}-latin-${peso}-normal.woff2`);
    const dst = resolve(DEST, `${slug}-${peso}.woff2`);
    await copyFile(src, dst);
    console.log(`  ${slug}-${peso}.woff2`);
    copiati++;
  }
  licenze.push(`### ${pkg}\n\n` + (await readFile(resolve(base, "LICENSE"), "utf-8")).trim());
}

// La licenza accanto ai file, non solo nel README: chi trova i woff2 fra sei
// mesi deve poter sapere sotto quali termini stanno li'.
await writeFile(
  resolve(DEST, "OFL.txt"),
  "I font in questa directory sono SIL Open Font License 1.1.\n" +
    "Copiati da npm con `npm run fonts` — vedi scripts/fonts.mjs.\n\n" +
    licenze.join("\n\n---\n\n") + "\n",
  "utf-8",
);

console.log(`\n${copiati} woff2 + OFL.txt in ui/src/style/fonts/`);
