/* La superficie composta sullo schermo — ADR-013 criterio 6, ciclo §11.7.
 *
 * §11.7 passo 0 regola 2: «cio' che attraversa un confine si prova
 * attraversando quel confine. Il layout tocca renderer, preload, ponte, socket,
 * core e disco». I test Python di `test_la_composizione_si_propone.py` guardano
 * cio' che il core MANDA; questa prova guarda cio' che la scrivania FA.
 *
 * ⚠️ La differenza non e' teorica: alla prima stesura erano tutti verdi e lo
 * schermo non cambiava. `ui/src/app.js` applicava `ui.layout` **una volta
 * sola** — il guardiano del ripristino d'avvio — e scartava in silenzio la
 * composizione che arrivava dopo. E' esattamente il difetto che il passo 0
 * elenca fra i due che gli hanno dato origine.
 *
 *   XDG_CONFIG_HOME=<albero>/cfg XDG_DATA_HOME=<albero>/dati \
 *     uv run python scripts/prova_superficie.py diagnostica &
 *   node scripts/prova-superficie.mjs [--scatti shots/superficie]
 *
 * Stampa una riga JSON: `tests/test_la_composizione_si_propone.py` la legge.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import electronPath from "electron";
import { _electron as electron } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const CARTELLA = process.argv.includes("--scatti")
  ? process.argv[process.argv.indexOf("--scatti") + 1] : null;
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

function socketDelCore() {
  return execFileSync("uv", ["run", "python", "-m", "core.paths_cli", "--socket"],
                      { cwd: RADICE, encoding: "utf-8" }).trim();
}

const app = await electron.launch({
  executablePath: electronPath,
  args: [join(RADICE, "app", "main.js"), "--socket", socketDelCore()],
  cwd: RADICE,
});
const win = await app.firstWindow();
await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
await win.waitForFunction(() => !!window.__scrivania?.scrivania, null, { timeout: 60_000 });
await dorme(1500);

/* Com'era PRIMA. Senza questo, «i pannelli composti ci sono» non distingue una
 * composizione arrivata da tre finestre che c'erano gia'. */
const leggi = () => win.evaluate(() => {
  const visibile = new Set([...document.querySelectorAll(".winbox")]
    .filter((e) => getComputedStyle(e).display !== "none"
                   && e.getBoundingClientRect().width > 0)
    .map((e) => e.dataset.modulo));
  const d = window.__scrivania.scrivania.disposizione();
  const r = (p) => ({ id: p.id, x: p.x, y: p.y, w: p.larghezza, h: p.altezza, z: p.z });
  return {
    area: d.area,
    pannelli: d.pannelli.filter((p) => visibile.has(p.id)).map(r),
    visibili: [...visibile],
  };
});

const prima = await leggi();

/* Il core compone da solo, tre secondi dopo che la scrivania si e' collegata:
 * lo fa `scripts/prova_superficie.py`, dicendo la frase. Qui si aspetta. */
await dorme(9000);
const dopo = await leggi();

const sovrapposte = [];
for (let i = 0; i < dopo.pannelli.length; i++) {
  for (let j = i + 1; j < dopo.pannelli.length; j++) {
    const a = dopo.pannelli[i], b = dopo.pannelli[j];
    const dx = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
    const dy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
    if (dx > 0 && dy > 0) sovrapposte.push({ a: a.id, b: b.id, dx, dy });
  }
}

/* I pannelli composti stanno DENTRO l'area? Il compilatore lo garantisce in
 * Python; qui lo si guarda dove i pixel esistono davvero. */
const fuoriArea = dopo.pannelli.filter((p) =>
  p.x < dopo.area.sinistra || p.y < dopo.area.alto
  || p.x + p.w > dopo.area.sinistra + dopo.area.larghezza + 2
  || p.y + p.h > dopo.area.alto + dopo.area.altezza + 2).map((p) => p.id);

if (CARTELLA) {
  mkdirSync(CARTELLA, { recursive: true });
  await win.screenshot({ path: join(CARTELLA, "superficie.png") });
}
await app.close();

console.log(JSON.stringify({
  prima: { visibili: prima.visibili, pannelli: prima.pannelli.length },
  dopo: { visibili: dopo.visibili, pannelli: dopo.pannelli },
  area: dopo.area,
  sovrapposte,
  fuori_area: fuoriArea,
  cambiato: JSON.stringify(prima.pannelli) !== JSON.stringify(dopo.pannelli),
}));
