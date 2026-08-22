/* Profili di luminanza riga per riga e colonna per colonna — per MISURARE un
 * riferimento invece di stimarlo a occhio.
 *
 *   node scripts/profilo.mjs <file.png> [x0 y0 x1 y1]
 *
 * Stampa, per la regione indicata, la luminanza media di ogni riga e di ogni
 * colonna. I bordi di un pannello sono picchi: una hairline chiara su fondo
 * scuro si vede come un massimo locale netto, e da li' si leggono le
 * proporzioni vere.
 *
 * Rec. 709 su 0-255, la stessa di `densita.mjs`: e' «quanta superficie e'
 * accesa», non il contrasto WCAG. Confonderle e' l'errore di DIVARIO §3.
 */
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const [file, ...r] = process.argv.slice(2);
if (!file) { console.error("uso: node scripts/profilo.mjs <png> [x0 y0 x1 y1]"); process.exit(2); }

const browser = await chromium.launch();
const page = await browser.newPage();
const b64 = readFileSync(file).toString("base64");

const out = await page.evaluate(async ([b64, reg]) => {
  const img = new Image();
  img.src = "data:image/png;base64," + b64;
  await img.decode();
  const c = document.createElement("canvas");
  c.width = img.naturalWidth; c.height = img.naturalHeight;
  c.getContext("2d").drawImage(img, 0, 0);
  const [x0, y0, x1, y1] = reg.length === 4
    ? reg.map(Number) : [0, 0, img.naturalWidth, img.naturalHeight];
  const d = c.getContext("2d").getImageData(x0, y0, x1 - x0, y1 - y0).data;
  const w = x1 - x0, h = y1 - y0;
  const L = (i) => 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
  const righe = [], colonne = new Float64Array(w);
  for (let y = 0; y < h; y++) {
    let s = 0;
    for (let x = 0; x < w; x++) { const l = L(((y * w) + x) * 4); s += l; colonne[x] += l; }
    righe.push(+(s / w).toFixed(2));
  }
  return { dim: [img.naturalWidth, img.naturalHeight], regione: [x0, y0, x1, y1],
           righe, colonne: [...colonne].map((s) => +(s / h).toFixed(2)) };
}, [b64, r]);

await browser.close();

/** I massimi locali che superano la mediana di `k` volte la deviazione. */
function picchi(v, k = 2.0) {
  const ord = [...v].sort((a, b) => a - b);
  const med = ord[ord.length >> 1];
  const dev = Math.sqrt(v.reduce((s, x) => s + (x - med) ** 2, 0) / v.length) || 1;
  const fuori = [];
  for (let i = 1; i < v.length - 1; i++)
    if (v[i] - med > k * dev && v[i] >= v[i - 1] && v[i] >= v[i + 1])
      fuori.push({ i, v: v[i] });
  return { mediana: +med.toFixed(2), dev: +dev.toFixed(2), picchi: fuori };
}

console.log(JSON.stringify({
  dim: out.dim, regione: out.regione,
  righe: picchi(out.righe), colonne: picchi(out.colonne),
  profiloRighe: out.righe, profiloColonne: out.colonne,
}));
