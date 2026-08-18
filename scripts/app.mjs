/* Avvia l'app Electron.
 *
 * Chiede il percorso del socket al core e lo passa a Electron: il codice
 * dell'app non deve sapere che cos'e' `$XDG_RUNTIME_DIR` (invariante 29).
 * Su Windows la stessa riga restituira' una named pipe senza che main.js
 * cambi.
 *
 *   npm run app
 *   npm run app -- --screenshot shots/app.png
 */

import { execFileSync, spawn } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electron from "electron";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));

let socket;
try {
  socket = execFileSync("uv", ["run", "python", "-m", "core.paths_cli", "--socket"], {
    cwd: RADICE,
    encoding: "utf-8",
  }).trim();
} catch (e) {
  console.error("impossibile chiedere il percorso del socket al core:", e.message);
  process.exit(1);
}

const figlio = spawn(
  electron,
  [resolve(RADICE, "app", "main.js"), "--socket", socket, ...process.argv.slice(2)],
  { stdio: "inherit", cwd: RADICE },
);
figlio.on("exit", (code) => process.exit(code ?? 0));
