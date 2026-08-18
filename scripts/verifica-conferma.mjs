/* Verifica del giro completo della conferma, con la finestra vera.
 *
 * `test_confirm_e2e.py` prova il giro attraverso il socket. Questo prova il
 * tratto che quel test non tocca: il messaggio arriva al renderer, diventa una
 * finestra leggibile, e il clic su Approva torna al core.
 *
 * Guida Electron via CDP (`--remote-debugging-port`) invece di aggiungere una
 * modalita' di prova a `app/main.js`: un gancio di test nel processo main e'
 * superficie in piu' in un file che vale la pena tenere piccolo.
 */

import { spawn } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electron from "electron";
import { chromium } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const PORTA = 9333;
const [, , socket, uscita, azione = "approva"] = process.argv;

const figlio = spawn(
  electron,
  [resolve(RADICE, "app", "main.js"), "--socket", socket,
   `--remote-debugging-port=${PORTA}`],
  { stdio: ["ignore", "pipe", "pipe"], cwd: RADICE },
);
figlio.stderr.on("data", () => {});

const attendi = (ms) => new Promise((r) => setTimeout(r, ms));

let browser;
for (let i = 0; i < 60 && !browser; i++) {
  try { browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORTA}`); }
  catch { await attendi(500); }
}
if (!browser) { console.error("CDP non raggiungibile"); figlio.kill(); process.exit(1); }

const pagina = browser.contexts()[0].pages()[0];

// Attende che una conferma sia A SCHERMO, non che sia arrivato un messaggio.
let idConferma = null;
for (let i = 0; i < 120 && !idConferma; i++) {
  idConferma = await pagina.evaluate(() => window.__jarvisConferma).catch(() => null);
  if (!idConferma) await attendi(250);
}
if (!idConferma) { console.error("nessuna conferma a schermo"); figlio.kill(); process.exit(1); }
console.log(`CONFERMA A SCHERMO id=${idConferma}`);

// Cosa legge davvero l'utente: si estrae dal DOM, non si presume.
const mostrato = await pagina.evaluate(() => ({
  titolo: document.querySelector(".cnf__etichetta")?.textContent,
  riepilogo: document.querySelector("[data-riepilogo]")?.textContent,
  percorsi: [...document.querySelectorAll(".cnf__path")].map((e) => e.textContent.trim()),
  piede: document.querySelector("[data-conto]")?.textContent,
  bottoneConFocus: document.activeElement?.textContent,
}));
console.log("MOSTRATO " + JSON.stringify(mostrato));

await pagina.screenshot({ path: resolve(RADICE, uscita) });
console.log(`SCATTO ${uscita}`);

await pagina.click(azione === "approva" ? "[data-approva]" : "[data-rifiuta]");
console.log(`CLIC ${azione.toUpperCase()}`);

await attendi(1500);
await browser.close();
figlio.kill();
