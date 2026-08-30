/* Una modifica fatta appena prima di uscire sopravvive? N ripetizioni.
 *
 * Isola la domanda dal resto: si mette in coda UNA scrittura con un marcatore,
 * non si aspetta il debounce, e si chiude. Due modi di chiudere a confronto.
 */
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, renameSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import electronPath from "electron";
import { _electron as electron } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const LAYOUT = join(homedir(), ".local/share/jarvis-os/layout.json");
const DA_PARTE = `${LAYOUT}.prova-flush`;
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));
const MARCATORE = 137;
const N = Number(process.argv[2] ?? 8);

function statoPulito() {
  if (existsSync(DA_PARTE)) rmSync(DA_PARTE);
  if (existsSync(LAYOUT)) renameSync(LAYOUT, DA_PARTE);
}
function rimettiAPosto() {
  if (!existsSync(DA_PARTE)) return;
  rmSync(LAYOUT, { force: true });
  renameSync(DA_PARTE, LAYOUT);
}
function socketDelCore() {
  return execFileSync("uv", ["run", "python", "-m", "core.paths_cli", "--socket"],
                      { cwd: RADICE, encoding: "utf-8" }).trim();
}
async function avvia() {
  const app = await electron.launch({
    executablePath: electronPath,
    args: [join(RADICE, "app", "main.js"), "--socket", socketDelCore()],
    cwd: RADICE,
  });
  const win = await app.firstWindow();
  await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
  await win.waitForFunction(() => !!window.__scrivania?.icone, null, { timeout: 60_000 });
  await dorme(1500);
  return { app, win };
}
async function metteInCoda(win) {
  return win.evaluate((m) => {
    const s = window.__scrivania.scrivania;
    const d = s.disposizione();
    if (!d.pannelli.length) return { messo: false };
    d.pannelli[0].x = m; d.pannelli[0].y = m;
    window.__layout.persistenza.azzera();
    window.__layout.persistenza.suDisposizione(d);
    return { messo: true };
  }, MARCATORE);
}
function arrivato() {
  if (!existsSync(LAYOUT)) return false;
  const l = JSON.parse(readFileSync(LAYOUT, "utf-8"));
  return (l.pannelli ?? []).some((p) => p.x === MARCATORE && p.y === MARCATORE);
}

statoPulito();
process.on("exit", rimettiAPosto);
const esiti = { playwright: [], vera: [] };

for (let i = 0; i < N; i++) {
  {
    const { app, win } = await avvia();
    await metteInCoda(win);
    await app.close();
    await dorme(1500);
    esiti.playwright.push(arrivato());
    rmSync(LAYOUT, { force: true });
  }
  {
    const { app, win } = await avvia();
    await metteInCoda(win);
    await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].close());
    await dorme(1500);
    esiti.vera.push(arrivato());
    try { await app.close(); } catch { /* gia' chiusa */ }
    rmSync(LAYOUT, { force: true });
  }
  console.error(`coppia ${i + 1}/${N}`);
}

rimettiAPosto();
const conta = (a) => `${a.filter(Boolean).length}/${a.length} arrivati`;
console.log(JSON.stringify({
  playwright: conta(esiti.playwright), vera: conta(esiti.vera), esiti,
}, null, 2));
