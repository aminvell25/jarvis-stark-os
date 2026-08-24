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
 *
 * ## ⚠️ QUESTA PROVA HA UN VERDETTO, e prima non ce l'aveva
 *
 * Fino al 24 agosto 2026 stampava un JSON e usciva **0 comunque**. Fra il 22 e
 * il 24 la griglia ha smesso di scorrere del tutto — le tessere erano scese a
 * 20x20 e quarantuno ci stavano tutte nei 422 px della vista — e nessuno se
 * n'e' accorto: `scorrevole` era `false`, l'inerzia non partiva mai, e
 * `si_e_fermata` diceva **true** perche' niente si era mosso.
 *
 * E' la stessa forma di difetto della guardia sempre rossa di `c0c7b2f` e
 * della metrica satura `L>25` di `densita.mjs`: un criterio che non boccia
 * niente, e che sembra una verifica. Da qui le due regole di sotto —
 * `misurabile` prima di `soddisfatto`, e un'uscita diversa da zero.
 *
 * ## Le due trappole d'ambiente, che sono costate un'ora a testa
 *
 * 1. **La linguetta FILE legge `fs.list` dal core.** Col core spento la prova
 *    riporta `tessere: 0` e sembra rotta, mentre e' rotto l'ambiente. Si
 *    controlla che il core risponda PRIMA di dare la colpa al catalogo.
 * 2. **Scatti e suite non convivono**: `uv run pytest` e qualunque avvio di
 *    Electron condividono il socket del core vivo. Prima gli scatti, poi la
 *    suite, a Electron chiuso.
 */

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electronPath from "electron";
import { _electron as electron } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const CARTELLA = process.argv.includes("--scatti")
  ? process.argv[process.argv.indexOf("--scatti") + 1] : null;
const QUANTI = 40;

/* ── l'esito, e perche' non basta un'uscita diversa da zero ────────────────
 *
 * Dare un verdetto a questa prova non serve a niente se poi NESSUNO LA LANCIA.
 * E' esattamente cosi' che la regressione del 22 agosto e' passata due giorni:
 * il comando esisteva, il difetto era misurabile, e non lo misurava nessuno.
 *
 * Stessa forma della guardia del marchio (`densita.mjs --marchio-stati` +
 * `tests/test_nucleo.py`): la cattura resta MANUALE, perche' aprire Electron
 * dentro la suite rimetterebbe il conflitto sul socket del core vivo; e la
 * suite verifica che l'esito sia **FRESCO**, confrontando un'impronta dei
 * sorgenti. Se il catalogo cambia e nessuno rimisura, il test cade e dice
 * quale comando lanciare.
 *
 * ⚠️ **Il limite dell'impronta, dichiarato**: copre i due file qui sotto. Se
 * a far smettere di scorrere la griglia fosse un TERZO file — per esempio
 * `app.css` che ridimensiona `.cat` — la guardia non se ne accorgerebbe. Per
 * allargarla si aggiunge il file a FONTI, non si spera che basti. */
const DOVE_ESITO = "docs/acceptance/CATALOGO-SCORRIMENTO.json";
const FONTI = ["ui/src/desk/catalogo.js", "ui/src/style/tokens.css"];
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

  /* ⚠️ `misurabile` PRIMA di `si_e_fermata`, e non e' una sottigliezza.
   *
   * A nastro fermo tutte e quattro le letture valgono 0, quindi
   * `fermo === ancoraFermo` e' vero — e la prova dichiarava soddisfatto un
   * criterio sull'inerzia senza che l'inerzia fosse mai partita. Un fermo che
   * non e' mai stato in moto non e' una decelerazione riuscita: e' l'assenza
   * del fenomeno. Lo stesso rimedio del banco di §11.4, che dichiara «non
   * misurabile» invece di dare un verdetto dove la misura non vale. */
  esiti.inerzia = {
    subito, dopoUnPo, fermo, ancoraFermo,
    misurabile: subito !== 0,
    ha_scorso: subito !== 0,
    ha_continuato: dopoUnPo !== subito,
    si_e_fermata: subito !== 0 && fermo === ancoraFermo,
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

/* ── il verdetto — §26.9 criterio 3, parte per parte ──────────────────────
 *
 * «Con 40 icone la griglia scorre, l'inerzia decelera e si ferma, nessuna
 * scrollbar di sistema e' visibile nello screenshot.»
 *
 * SEI condizioni separate e non un booleano solo: una griglia che non scorre e
 * un'inerzia che non si ferma sono due difetti diversi, e un verdetto unico
 * manderebbe a cercare nel posto sbagliato. Le sei sono le quattro della
 * frase di §26.9, piu' `misurabile` — che dice se le altre valgono qualcosa —
 * e la tacca, che e' l'unico indicatore di posizione del catalogo.
 */
const c = esiti.contenuto;
const i = esiti.inerzia;

/* La tacca deve dire la QUOTA VISIBILE, non una larghezza qualunque. Se
 * mentisse, l'unico indicatore di posizione che il catalogo ha direbbe il
 * falso — e lo direbbe in modo credibile, che e' peggio del non averlo.
 * Un punto percentuale di tolleranza: la larghezza si scrive con due decimali
 * e il nastro ha un padding che il conteggio non vede. */
const taccaAttesa = (100 * c.vista) / c.contenuto;
const taccaLetta = Number.parseFloat(c.taccaLarghezza);
const taccaScarto = Number.isFinite(taccaLetta)
  ? Math.abs(taccaLetta - taccaAttesa) : Number.POSITIVE_INFINITY;

const criteri = [
  ["la griglia SCORRE",
   c.scorrevole,
   `contenuto ${c.contenuto} px contro vista ${c.vista} px con ${c.tessere} tessere` +
   (c.scorrevole ? "" : " — non c'e' niente da far scorrere, e il resto della prova non misura nulla")],
  ["l'inerzia e' MISURABILE",
   i.misurabile,
   `x dopo il rilascio ${i.subito}` +
   (i.misurabile ? "" : " — il nastro non si e' mosso: le condizioni sotto sarebbero vere per assenza")],
  ["l'inerzia CONTINUA dopo il rilascio",
   i.ha_continuato,
   `${i.subito} -> ${i.dopoUnPo}`],
  ["l'inerzia DECELERA e si ferma",
   i.si_e_fermata,
   `${i.fermo} -> ${i.ancoraFermo}`],
  ["nessuna barra di sistema nella vista",
   esiti.scrollbar.overflowVista === "hidden",
   `overflow-x della vista: ${esiti.scrollbar.overflowVista}`],
  ["la tacca dice la quota visibile",
   taccaScarto <= 1,
   `letta ${c.taccaLarghezza}, attesa ${taccaAttesa.toFixed(2)} % (${c.vista}/${c.contenuto})`],
];

console.error("");
for (const [nome, ok, dettaglio] of criteri) {
  console.error(`  ${ok ? "ok  " : "NO  "}${nome.padEnd(38)} ${dettaglio}`);
}
const falliti = criteri.filter(([, ok]) => !ok);
console.error("");
console.error(falliti.length
  ? `§26.9 criterio 3 NON SODDISFATTO — ${falliti.length} condizioni su ${criteri.length}: ` +
    falliti.map(([n]) => n).join(" · ")
  : `§26.9 criterio 3 soddisfatto — ${criteri.length} condizioni su ${criteri.length}`);

/* L'esito va in `docs/acceptance/`, VERSIONATO, e non in `shots/`, che git
 * ignora: un test che si salta quando il file manca e' un test che non c'e'. */
const impronta = createHash("sha256");
for (const f of FONTI) impronta.update(readFileSync(join(RADICE, f)));
writeFileSync(DOVE_ESITO, JSON.stringify({
  fonti: FONTI,
  impronta: impronta.digest("hex").slice(0, 16),
  soddisfatto: falliti.length === 0,
  criteri: criteri.map(([nome, ok, dettaglio]) => ({ nome, ok, dettaglio })),
  misure: esiti,
}, null, 2) + "\n");
console.error(`\n  esito      ${DOVE_ESITO}`);

process.exit(falliti.length ? 1 : 0);
