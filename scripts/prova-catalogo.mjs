/* Il catalogo, provato nell'app vera — §26.9 criterio 3.
 *
 *   «Con 40 icone la griglia scorre, l'inerzia decelera e si ferma, nessuna
 *   scrollbar di sistema e' visibile nello screenshot.»
 *
 * Le quaranta icone sono FILE VERI: si creano nella workspace, si misura, e si
 * tolgono. Inventare quaranta voci finte proverebbe lo scorrimento e non
 * proverebbe che il catalogo sa mostrare quello che c'e' davvero — che e' la
 * meta' interessante, visto che la linguetta FILE legge `fs.list` dal core.
 *
 * Come `prova-gesti.mjs`: Electron vero, core vero, e il puntatore mosso da
 * Playwright, che entra nella pipeline di input del browser (passo 0 di §11.7).
 */

import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electronPath from "electron";
import { _electron as electron } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const CARTELLA = process.argv.includes("--scatti")
  ? process.argv[process.argv.indexOf("--scatti") + 1] : null;
const QUANTI = 40;
const PREFISSO = "prova-catalogo-";
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

function workspace() {
  /* ⚠️ L'ULTIMA RIGA, non tutto l'output.
   *
   * `load_settings()` scrive `settings_caricate` con structlog, e structlog
   * scrive su STDOUT. Il primo giro prendeva `out.trim()` intero: il percorso
   * diventava «2026-08-19 17:13 [info] settings_caricate … /home/…/JARVIS», e
   * `mkdirSync` ha creato una directory con quel nome dentro il progetto. I
   * quaranta file sono finiti li', e la prova ha misurato UN file — quello
   * vero della workspace — concludendo che la griglia non scorre.
   *
   * Il difetto era nella prova, non nel catalogo. Ma per un quarto d'ora ha
   * detto il contrario. */
  const out = execFileSync("uv", ["run", "python", "-c",
    "from core.settings import load_settings; print(load_settings().fs.workspace)"],
    { cwd: RADICE, encoding: "utf-8" });
  const righe = out.trim().split("\n").filter((r) => r.trim());
  return righe[righe.length - 1].trim();
}

const WS = workspace();

function seminaFile() {
  mkdirSync(WS, { recursive: true });
  for (let i = 0; i < QUANTI; i++) {
    writeFileSync(join(WS, `${PREFISSO}${String(i).padStart(2, "0")}.txt`),
                  "prova del catalogo — si cancella da solo\n");
  }
}

function togliFile() {
  for (const f of readdirSync(WS)) {
    if (f.startsWith(PREFISSO)) rmSync(join(WS, f), { force: true });
  }
}

const esiti = {};
seminaFile();
process.on("exit", togliFile);

const app = await electron.launch({
  executablePath: electronPath,
  args: [join(RADICE, "app", "main.js"), "--socket",
         execFileSync("uv", ["run", "python", "-m", "core.paths_cli", "--socket"],
                      { cwd: RADICE, encoding: "utf-8" }).trim()],
  cwd: RADICE,
});
const win = await app.firstWindow();
await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
await win.waitForFunction(() => !!document.querySelector(".cat__tessera"),
                          null, { timeout: 60_000 });
await dorme(1500);

/* ── 1. quaranta icone, e la griglia scorre ─────────────────────────────── */

await win.locator('.cat__linguetta:has-text("FILE")').click();
await dorme(600);

const misura = () => win.evaluate(() => {
  const vista = document.querySelector(".cat__vista");
  const nastro = document.querySelector(".cat__nastro");
  const tacca = document.querySelector(".cat__tacca");
  return {
    tessere: nastro.querySelectorAll(".cat__tessera").length,
    vista: Math.round(vista.clientWidth),
    contenuto: Math.round(nastro.scrollWidth),
    x: Math.round(new DOMMatrix(getComputedStyle(nastro).transform).m41),
    taccaLarghezza: tacca.style.width,
  };
});

esiti.contenuto = await misura();
esiti.contenuto.scorrevole = esiti.contenuto.contenuto > esiti.contenuto.vista;

/* ── 2. il gesto, e l'inerzia che decelera e si ferma ───────────────────── */
{
  const b = await win.locator(".cat__vista").boundingBox();
  const y = b.y + b.height / 2;
  const da = { x: b.x + b.width * 0.75, y };
  const a = { x: b.x + b.width * 0.25, y };

  await win.mouse.move(da.x, da.y);
  await win.mouse.down();
  for (let i = 1; i <= 12; i++) {
    await win.mouse.move(da.x + ((a.x - da.x) * i) / 12, y);
    await dorme(10);
  }
  await win.mouse.up();

  // Subito dopo il rilascio, e poi ancora: se l'inerzia c'e', fra i due
  // istanti il nastro si e' mosso ancora; se decelera e si ferma, fra il
  // secondo e il terzo non piu'.
  const subito = (await misura()).x;
  await dorme(200);
  const dopoUnPo = (await misura()).x;
  await dorme(1200);
  const fermo = (await misura()).x;
  await dorme(400);
  const ancoraFermo = (await misura()).x;

  esiti.inerzia = {
    subito, dopoUnPo, fermo, ancoraFermo,
    ha_scorso: subito !== 0,
    ha_continuato: dopoUnPo !== subito,
    si_e_fermata: fermo === ancoraFermo,
  };
}

/* ── 3. nessuna barra di scorrimento di sistema ─────────────────────────── */

esiti.scrollbar = await win.evaluate(() => {
  const dentro = [...document.querySelectorAll(".cat, .cat *")];
  const conBarra = dentro.filter((el) => {
    const cs = getComputedStyle(el);
    const scorre = el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight;
    return scorre && (cs.overflowX === "scroll" || cs.overflowX === "auto" ||
                      cs.overflowY === "scroll" || cs.overflowY === "auto");
  }).map((el) => el.className);
  const vista = document.querySelector(".cat__vista");
  return {
    // La vista deve avere overflow HIDDEN: e' cio' che impedisce al sistema di
    // disegnare la propria barra, ed e' il punto 3 di §26.4.
    overflowVista: getComputedStyle(vista).overflowX,
    elementiCheScorrerebbero: conBarra,
  };
});

/* ── 4. il budget: il nastro si muove con transform, e costa poco ───────── */
{
  const b = await win.locator(".cat__vista").boundingBox();
  const y = b.y + b.height / 2;
  esiti.budget = await win.evaluate(async ([x0, y0]) => {
    const dt = [];
    let prima = performance.now();
    let fermo = false;
    const passo = () => {
      const ora = performance.now(); dt.push(ora - prima); prima = ora;
      if (!fermo) requestAnimationFrame(passo);
    };
    requestAnimationFrame(passo);
    // Si trascina davvero, dal codice della pagina: qui serve il COSTO del
    // movimento, e per averlo bisogna che il movimento ci sia.
    const vista = document.querySelector(".cat__vista");
    const manda = (tipo, x) => vista.dispatchEvent(new PointerEvent(tipo, {
      pointerId: 1, clientX: x, clientY: y0, bubbles: true, button: 0 }));
    manda("pointerdown", x0);
    for (let i = 0; i < 40; i++) {
      manda("pointermove", x0 - i * 6);
      await new Promise((r) => requestAnimationFrame(r));
    }
    manda("pointerup", x0 - 240);
    await new Promise((r) => setTimeout(r, 400));
    fermo = true;
    dt.sort((a, b) => a - b);
    return { frame: dt.length, mediana: +dt[dt.length >> 1].toFixed(2),
             max: +dt[dt.length - 1].toFixed(2) };
  }, [b.x + b.width * 0.8, y]);
}

if (CARTELLA) {
  mkdirSync(CARTELLA, { recursive: true });
  await win.screenshot({ path: join(CARTELLA, "catalogo-file-40.png") });
  await win.locator('.cat__linguetta:has-text("SCENE")').click();
  await dorme(400);
  await win.screenshot({ path: join(CARTELLA, "catalogo-vuoto.png") });
}

await app.close();
togliFile();
console.log(JSON.stringify(esiti));
