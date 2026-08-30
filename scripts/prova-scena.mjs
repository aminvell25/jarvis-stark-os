/* La scena `briefing` sullo schermo — §26.9 criterio 6.
 *
 *   «`scene:briefing` dispone tre pannelli sovrapposti. Screenshot allegato,
 *    confrontato con `famiglia-a/01`.»
 *
 * La scena esiste in `config/settings.toml` dal giorno di §26.6 e non era mai
 * stata applicata dal vivo: `LE-FRASI-PUNTANO-A-UNA-SCENA-CHE-ESISTE.md`
 * dichiarava «non ho verificato dal vivo che la scena si applichi sullo
 * schermo». Questa prova lo fa, e misura la sovrapposizione invece di
 * guardarla.
 *
 * ⚠️ **Il core gira su una configurazione a parte.** `~/.config/jarvis-os/`
 * appartiene al Signore e non si tocca: la prova vuole una `settings.toml` che
 * dichiari le scene, e quella e' `config/settings.toml`, versionata. Chi lancia
 * questa prova passa `XDG_CONFIG_HOME` a un albero suo — vedi il README qui
 * sotto — e cosi' la prova non dipende da come e' fatta la macchina.
 *
 *   XDG_CONFIG_HOME=<albero>/cfg XDG_DATA_HOME=<albero>/dati \
 *     uv run python -m core.engine &
 *   node scripts/prova-scena.mjs [--scatti shots/scena-briefing]
 *
 * Stampa una riga JSON: `tests/test_scena.py` la legge e giudica.
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
const SCENA = "briefing";

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

/* Che cosa il core ha DICHIARATO. Se `briefing` non e' qui, la scena non e'
 * arrivata dalle impostazioni e il resto della prova non significa niente. */
const dichiarate = await win.evaluate(() => ({
  scene: window.__scrivania.scrivania.scene,
  corrente: window.__scrivania.scrivania.scenaCorrente,
}));

await win.evaluate((nome) => window.__scrivania.scrivania.scena(nome), SCENA);
// §10.3: l'apertura dura 180 ms, e la composizione le sfalsa.
await dorme(1200);

/* La geometria vera, in pixel, e SOLO di cio' che si vede.
 *
 * ⚠️ Due trappole, tutt'e due prese in pieno alla prima stesura.
 *
 * `disposizione()` include i pannelli NASCOSTI di proposito (§26.10: `Alt+H` e'
 * transitorio e filtrarli cancellerebbe dal disco tutti gli altri), e
 * `applicaScena` **nasconde** cio' che non e' nella scena invece di chiuderlo —
 * chiudere costerebbe i dati e sarebbe distruttivo. Quindi chiedere la
 * disposizione dopo una scena restituisce anche i tre pannelli dell'avvio.
 *
 * E `.winbox[hidden]` non dice niente: WinBox nasconde in CSS, non con
 * l'attributo. Si guarda `display`, che e' cio' che decide se un pixel c'e'. */
const disposti = await win.evaluate(() => {
  const visibile = new Set([...document.querySelectorAll(".winbox")]
    .filter((e) => getComputedStyle(e).display !== "none"
                   && e.getBoundingClientRect().width > 0)
    .map((e) => e.dataset.modulo));
  const d = window.__scrivania.scrivania.disposizione();
  const r = (p) => ({ id: p.id, x: p.x, y: p.y, w: p.larghezza, h: p.altezza, z: p.z });
  return {
    area: d.area,
    pannelli: d.pannelli.filter((p) => visibile.has(p.id)).map(r),
    nascosti: d.pannelli.filter((p) => !visibile.has(p.id)).map((p) => p.id),
  };
});

const sovrapposte = [];
for (let i = 0; i < disposti.pannelli.length; i++) {
  for (let j = i + 1; j < disposti.pannelli.length; j++) {
    const a = disposti.pannelli[i], b = disposti.pannelli[j];
    const dx = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
    const dy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
    if (dx > 0 && dy > 0) {
      sovrapposte.push({ a: a.id, b: b.id, larghezza: dx, altezza: dy,
                         sopra: a.z === b.z ? null : (a.z > b.z ? a.id : b.id) });
    }
  }
}

const aSchermo = await win.evaluate(() => ({
  finestre: [...document.querySelectorAll(".winbox")]
    .filter((e) => getComputedStyle(e).display !== "none")
    .map((e) => e.dataset.modulo),
}));

if (CARTELLA) {
  mkdirSync(CARTELLA, { recursive: true });
  await win.screenshot({ path: join(CARTELLA, "scena.png") });
}

const corrente = await win.evaluate(() => window.__scrivania.scrivania.scenaCorrente);
await app.close();

console.log(JSON.stringify({
  chiesta: SCENA,
  dichiarate: dichiarate.scene,
  scena_prima: dichiarate.corrente,
  scena_dopo: corrente,
  disposti,
  sovrapposte,
  a_schermo: aSchermo,
}));
