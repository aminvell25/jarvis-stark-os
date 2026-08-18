/* Ciclo di verifica visiva — SPEC §11.7 passo 2.
 *
 *   npm run shot -- <componente> [--pulito] [--grid]
 *
 * Usa l'API di Playwright e non la CLI `playwright screenshot` per due motivi
 * che contano davvero:
 *
 *   deviceScaleFactor 2 — `--line-hair` e' 0.5px. A scala 1 un bordo di mezzo
 *   pixel viene antialiasato in una riga sbiadita, e si finirebbe a giudicare
 *   la finezza delle linee su un artefatto del campionamento. La CLI non
 *   espone il parametro.
 *
 *   attesa dei font ed errori — serve leggere `window.__gallery` dopo che i
 *   font hanno caricato, e serve intercettare gli errori di console.
 *
 * Esce con codice != 0 quando lo scatto NON e' una verifica valida:
 * errore di console, font assente, o violazioni dove non ne erano attese.
 * Uno screenshot di una pagina rotta non deve sembrare un successo.
 */

import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

import { PORTA, avvia } from "./serve.mjs";

const argv = process.argv.slice(2);
const componente = argv.find((a) => !a.startsWith("--")) ?? "all";
const pulitoAtteso = argv.includes("--pulito");
const conGriglia = argv.includes("--grid");

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const USCITA = resolve(RADICE, "shots", `${componente}.png`);

const url =
  `http://127.0.0.1:${PORTA}/gallery.html` +
  `?component=${encodeURIComponent(componente)}&tokens=audit` +
  (conGriglia ? "&grid=1" : "");

await mkdir(resolve(RADICE, "shots"), { recursive: true });

const server = await avvia();
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 2,
});

// Un Set: browser e rete segnalano lo stesso 404 su piu' canali, e cinque
// font mancanti diventerebbero quindici righe che dicono la stessa cosa.
const errori = new Set();
page.on("console", (m) => {
  if (m.type() !== "error") return;
  const url = m.location()?.url;
  errori.add(url ? `risorsa non caricata — ${url}` : m.text());
});
page.on("pageerror", (e) => errori.add(String(e)));
page.on("response", (r) => {
  if (r.status() >= 400) errori.add(`risorsa non caricata — ${r.url()}`);
});

let codice = 0;
try {
  await page.goto(url, { waitUntil: "load" });
  // 120 s e non 20: il banco del budget misura centinaia di frame, e in
  // headless — dove si rende in software — ci mette piu' che sulla macchina.
  // Per tutti gli altri componenti la soglia non si avvicina nemmeno.
  await page.waitForSelector('body[data-stato="pronto"]', { timeout: 120_000 });

  const r = await page.evaluate(() => window.__gallery);
  await page.screenshot({ path: USCITA, fullPage: true });

  console.log(`\nscatto     ${USCITA}`);
  console.log(`componente ${r.componente}`);

  if (r.errore) { console.error(`ERRORE      ${r.errore}`); codice = 1; }

  if (r.fontMancanti?.length) {
    console.error(`FONT ASSENTI ${r.fontMancanti.join(", ")}`);
    console.error("             lo scatto NON e' una verifica valida.");
    console.error("             vedi ui/src/style/fonts/README.md");
    codice = 1;
  } else {
    console.log("font       tutti caricati");
  }

  const tot = (r.violazioniCalcolate ?? 0) + (r.violazioniSorgente ?? 0);
  console.log(`audit      ${r.violazioniCalcolate} elementi fuori sistema, ` +
              `${r.violazioniSorgente} regole con letterali`);
  for (const c of r.dettaglioCalcolato ?? [])
    for (const g of c.guasti)
      console.log(`  calcolato ${c.dove} { ${g.prop}: ${g.trovato} } atteso ${g.atteso}`);
  for (const g of r.dettaglioSorgente ?? [])
    console.log(`  sorgente  ${g.selettore} { ${g.prop} } letterali: ${g.letterali.join(", ")}`);

  if (pulitoAtteso && tot > 0) {
    console.error(`ATTESO PULITO, trovate ${tot} violazioni.`);
    codice = 1;
  }
  if (!pulitoAtteso && tot === 0 && componente.startsWith("non-")) {
    console.error("ATTESE VIOLAZIONI, l'audit non ne ha trovate: audit rotto.");
    codice = 1;
  }

  if (errori.size) {
    console.error(`ERRORI DI CONSOLE (${errori.size}):`);
    for (const e of errori) console.error(`           ${e}`);
    codice = 1;
  }
} finally {
  await browser.close();
  server.close();
}

console.log(codice === 0 ? "esito      OK\n" : "esito      FALLITO\n");
process.exit(codice);
