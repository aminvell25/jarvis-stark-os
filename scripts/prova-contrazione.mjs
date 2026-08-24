/* La contrazione di §11.6 regola 3, provata nell'app VERA.
 *
 * Tre domande, e la terza e' quella che conta:
 *   1. un pannello vuoto aperto dal catalogo nasce alla cella RIDOTTA?
 *   2. quando arriva il contenuto torna alla cella PIENA?
 *   3. se l'utente lo ha ridimensionato a mano, la contrazione lo LASCIA STARE?
 */
import { execFileSync } from "node:child_process";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import electronPath from "electron";
import { _electron as electron } from "playwright";
const R = resolve(fileURLToPath(new URL("..", import.meta.url)));
const app = await electron.launch({
  executablePath: electronPath,
  args: [join(R, "app", "main.js"), "--socket",
    execFileSync("uv", ["run", "python", "-m", "core.paths_cli", "--socket"],
                 { cwd: R, encoding: "utf-8" }).trim()],
  cwd: R,
});
const win = await app.firstWindow();
await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
await win.waitForFunction(() => !!window.__scrivania, null, { timeout: 60000 });
await new Promise((r) => setTimeout(r, 4000));

const rett = () => win.evaluate(() => {
  const w = document.querySelector('.winbox[data-modulo="browser"]');
  if (!w) return null;
  const b = w.getBoundingClientRect();
  const p = w.querySelector(".pnl-web");
  return { l: Math.round(b.width), a: Math.round(b.height),
           x: Math.round(b.x), stato: p?.dataset.stato ?? "?" };
});

const esiti = {};
/* ⚠️ Si CHIUDE prima di aprire. Il layout persistito ricorda la dimensione che
 * l'esecuzione precedente ha lasciato, e senza questa riga la prova misura il
 * proprio giro di ieri invece della contrazione — successo al primo tentativo:
 * tutte e quattro le letture davano 700x400, cioe' il ridimensionamento a mano
 * della prova stessa. */
await win.evaluate(() => window.__scrivania.scrivania.chiudi("browser"));
await new Promise((r) => setTimeout(r, 600));
await win.evaluate(() => window.__scrivania.scrivania.apri("browser"));
await new Promise((r) => setTimeout(r, 1200));
esiti.vuoto = await rett();

// 2. arriva una pagina: torna piena
await win.evaluate(() => {
  const p = document.querySelector('.winbox[data-modulo="browser"] .pnl-web');
  if (p) p.dataset.stato = "pieno";
});
await new Promise((r) => setTimeout(r, 800));
esiti.pieno = await rett();

// 3. l'utente lo ridimensiona, poi si svuota: NON si tocca
await win.evaluate(() => {
  document.querySelector('.winbox[data-modulo="browser"]').winbox.resize(700, 400);
});
await new Promise((r) => setTimeout(r, 400));
esiti.dopoLaMano = await rett();
await win.evaluate(() => {
  const p = document.querySelector('.winbox[data-modulo="browser"] .pnl-web');
  if (p) p.dataset.stato = "vuoto";
});
await new Promise((r) => setTimeout(r, 800));
esiti.manoRispettata = await rett();

console.log(JSON.stringify(esiti));
await app.close();

/* ── il verdetto — §11.6 regola 3 ────────────────────────────────────────── */
const PIENA = 952, RIDOTTA = 472;      // [0,0,8,2] e [0,0,4,2] su 1536 px
const tolleranza = (a, b) => Math.abs(a - b) <= 8;
const criteri = [
  ["il pannello VUOTO nasce alla cella ridotta",
   tolleranza(esiti.vuoto?.l, RIDOTTA),
   `${esiti.vuoto?.l} px, attesi ~${RIDOTTA}`],
  ["arrivato il contenuto torna alla cella piena",
   tolleranza(esiti.pieno?.l, PIENA),
   `${esiti.pieno?.l} px, attesi ~${PIENA}`],
  ["la mano dell'utente cambia la dimensione",
   esiti.dopoLaMano?.l === 700 && esiti.dopoLaMano?.a === 400,
   `${esiti.dopoLaMano?.l}x${esiti.dopoLaMano?.a}, attesi 700x400`],
  ["e svuotandosi NON si contrae: la mano vince",
   esiti.manoRispettata?.l === 700 && esiti.manoRispettata?.a === 400,
   `${esiti.manoRispettata?.l}x${esiti.manoRispettata?.a}, attesi 700x400 — ` +
   "un pannello che l'utente ha dimensionato e' suo"],
];
console.error("");
for (const [n, ok, d] of criteri) console.error(`  ${ok ? "ok  " : "NO  "}${n.padEnd(48)} ${d}`);
const caduti = criteri.filter(([, ok]) => !ok);
console.error("");
console.error(caduti.length
  ? `§11.6 regola 3 NON SODDISFATTA — ${caduti.length} su ${criteri.length}: ` +
    caduti.map(([n]) => n).join(" · ")
  : `§11.6 regola 3 soddisfatta — ${criteri.length} condizioni su ${criteri.length}`);
process.exit(caduti.length ? 1 : 0);
