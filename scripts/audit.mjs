/* Audit di piu' componenti in UNA sessione di browser.
 *
 *   node scripts/audit.mjs rings dials source ...
 *
 * `npm run shot` apre un browser per componente: nove componenti sono nove
 * avvii di Chromium, e in un test diventano quaranta secondi di attesa che
 * nessuno guarda. Qui il browser si apre una volta e la pagina si ricarica.
 *
 * Stampa una riga JSON per componente su stdout: `tests/eval_visual.py` la
 * legge. Nessuna interpretazione qui — chi giudica e' il test.
 */

import { chromium } from "playwright";

import { PORTA, avvia } from "./serve.mjs";

const componenti = process.argv.slice(2);
if (componenti.length === 0) {
  console.error("uso: node scripts/audit.mjs <componente> [componente...]");
  process.exit(2);
}

const server = await avvia();
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

const esiti = [];
for (const nome of componenti) {
  const errori = new Set();
  const suConsole = (m) => { if (m.type() === "error") errori.add(m.text()); };
  const suErrore = (e) => errori.add(String(e));
  const suRisposta = (r) => { if (r.status() >= 400) errori.add(`404 ${r.url()}`); };
  page.on("console", suConsole);
  page.on("pageerror", suErrore);
  page.on("response", suRisposta);

  try {
    await page.goto(
      `http://127.0.0.1:${PORTA}/gallery.html?component=${encodeURIComponent(nome)}&tokens=audit`,
      { waitUntil: "load" }
    );
    await page.waitForSelector('body[data-stato="pronto"]', { timeout: 120_000 });
    const r = await page.evaluate(() => window.__gallery);
    esiti.push({ nome, ...r, errori: [...errori] });
  } catch (e) {
    esiti.push({ nome, errore: String(e), errori: [...errori] });
  } finally {
    page.off("console", suConsole);
    page.off("pageerror", suErrore);
    page.off("response", suRisposta);
  }
}

await browser.close();
server.close();

console.log(JSON.stringify(esiti));
