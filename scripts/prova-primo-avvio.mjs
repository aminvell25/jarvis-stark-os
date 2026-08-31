/* Il PRIMO avvio: senza `layout.json`, che cosa apre la scrivania — §26.6.
 *
 *   mv ~/.local/share/jarvis-os/layout.json{,.da-parte}
 *   XDG_CONFIG_HOME=<albero>/cfg uv run python -m core.engine &
 *   node scripts/prova-primo-avvio.mjs [scatto.png]
 *
 * `ui.scena_iniziale` decide che cosa si compone quando non c'e' niente da
 * rimettere. E' l'unica riga di `settings.toml` il cui effetto **non si vede
 * mai** su una macchina in uso: `ui/src/app.js` la applica solo sul ramo
 * `!ripristinato`, e un `layout.json` sul disco vince sempre. Provarla vuol
 * dire togliere quel file, ed e' per questo che serve un arnese apposta invece
 * di guardare uno screenshot qualunque.
 *
 * ⚠️ **La differenza che misura.** Senza `scena_iniziale` la scrivania apre
 * TUTTO — quattordici pannelli, ognuno con la propria cella su una
 * piastrellatura completa, che diventano una cascata diagonale in cui se ne
 * leggono due. Con la riga, si apre la scena dichiarata. Il numero di finestre
 * visibili distingue i due casi senza doverli guardare.
 *
 * Stampa una riga JSON con la scena corrente, i pannelli visibili e la loro
 * geometria.
 */
import { execFileSync } from "node:child_process";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electronPath from "electron";
import { _electron as electron } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

const socket = execFileSync(
  "uv", ["run", "python", "-m", "core.paths_cli", "--socket"],
  { cwd: RADICE, encoding: "utf-8" }).trim();

const app = await electron.launch({
  executablePath: electronPath,
  args: [join(RADICE, "app", "main.js"), "--socket", socket],
  cwd: RADICE,
});
const win = await app.firstWindow();
await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
await win.waitForFunction(() => !!window.__scrivania?.scrivania, null,
                          { timeout: 60_000 });
// La scena iniziale arriva con `state.snapshot`, non col primo frame.
await dorme(4000);

const stato = await win.evaluate(() => {
  // ⚠️ **Visibile per davvero**, non «presente nel DOM»: la scrivania costruisce
  // le finestre di tutti i moduli e ne nasconde la maggior parte, quindi
  // contare i `.winbox` direbbe sempre quattordici.
  const visibile = new Set([...document.querySelectorAll(".winbox")]
    .filter((e) => getComputedStyle(e).display !== "none"
                   && e.getBoundingClientRect().width > 0)
    .map((e) => e.dataset.modulo));
  const d = window.__scrivania.scrivania.disposizione();
  return {
    scenaCorrente: window.__scrivania.scrivania.scenaCorrente ?? null,
    quanti: visibile.size,
    visibili: [...visibile].sort(),
    pannelli: d.pannelli.filter((p) => visibile.has(p.id))
      .map((p) => ({ id: p.id, x: p.x, y: p.y, w: p.larghezza, h: p.altezza }))
      .sort((a, b) => a.y - b.y || a.x - b.x),
  };
});

if (process.argv[2]) await win.screenshot({ path: resolve(process.argv[2]) });
await app.close();
console.log(JSON.stringify(stato, null, 1));
