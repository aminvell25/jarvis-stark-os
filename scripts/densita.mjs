/* Densita' di superficie di uno screenshot — SPEC §11.8, criterio aggiunto il
 * 19 agosto 2026.
 *
 * PERCHE' ESISTE. La checklist §11.8 chiede «la densita' regge il confronto con
 * l'immagine di riferimento?», e la risposta la dava l'occhio. Una revisione
 * che ha misurato i pixel ha trovato dodici componenti giudicati conformi e
 * **nove volte** sotto il riferimento in superficie riempita. Una domanda a cui
 * si risponde a occhio non e' un criterio.
 *
 * PERCHE' PLAYWRIGHT E NON UNA LIBRERIA DI IMMAGINI. Decodificare un PNG
 * vorrebbe una dipendenza nuova, e `CLAUDE.md` dice di non aggiungerne senza
 * chiedere. Playwright e' gia' fra le devDependencies per il ciclo §11.7, e un
 * browser sa decodificare i PNG meglio di qualunque libreria che potremmo
 * installare. Zero dipendenze nuove.
 *
 * USO
 *   node scripts/densita.mjs shots/scrivania/ws-01.png
 *   node scripts/densita.mjs shots/globe.png docs/design-reference/famiglia-a/10-globo-gps-locator.png
 *
 * Col secondo argomento stampa le due misure accanto. Senza, confronta con le
 * soglie di `docs/design-reference/README.md`.
 */

import { chromium } from "playwright";
import { readFileSync } from "node:fs";
import { basename } from "node:path";

/* Le soglie vengono dalla misura del riferimento, non da un'intuizione.
 * `docs/design-reference/README.md`, sezione «COSA GUARDARE». */
const SOGLIE = {
  riempito: 25, // % pixel L>60 — riferimento 42,1 %
  caldoMin: 3, // % pixel r>b+15 — riferimento 5,7 %
  caldoMax: 6,
  barra: 25, // % pixel L>50 nella fascia della barra — riferimento 28–37 %
};

/** Rec. 709. La stessa formula del criterio, in un posto solo. */
const LUMA = "0.2126*d[i] + 0.7152*d[i+1] + 0.0722*d[i+2]";

async function misura(pagina, file) {
  const b64 = readFileSync(file).toString("base64");
  return pagina.evaluate(
    async ([b64, luma]) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      c.getContext("2d").drawImage(img, 0, 0);
      const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;

      const L = new Function("d", "i", `return ${luma};`);
      const n = c.width * c.height;
      let somma = 0,
        oltre25 = 0,
        oltre60 = 0,
        oltre120 = 0,
        caldi = 0;

      // La fascia della barra: il 3,3 % superiore, che e' la misura del
      // riferimento. Non il nostro valore attuale, o misureremmo noi stessi.
      const hBarra = Math.round(c.height * 0.033);
      let barraOltre50 = 0;
      const nBarra = hBarra * c.width;

      for (let p = 0; p < n; p++) {
        const i = p * 4;
        const l = L(d, i);
        somma += l;
        if (l > 25) oltre25++;
        if (l > 60) oltre60++;
        if (l > 120) oltre120++;
        if (d[i] > d[i + 2] + 15 && l > 30) caldi++;
        if (p < nBarra && l > 50) barraOltre50++;
      }

      const pc = (x, tot = n) => Math.round((1000 * x) / tot) / 10;
      return {
        larghezza: c.width,
        altezza: c.height,
        lumMedia: Math.round((10 * somma) / n) / 10,
        nonNero: pc(oltre25),
        riempito: pc(oltre60),
        chiaro: pc(oltre120),
        caldo: pc(caldi),
        barra: pc(barraOltre50, nBarra),
      };
    },
    [b64, LUMA]
  );
}

function riga(nome, m) {
  return (
    `${nome.padEnd(34)} ${String(m.larghezza + "x" + m.altezza).padEnd(10)}` +
    ` lum ${String(m.lumMedia).padStart(5)}` +
    ` · L>25 ${String(m.nonNero).padStart(5)}%` +
    ` · L>60 ${String(m.riempito).padStart(5)}%` +
    ` · L>120 ${String(m.chiaro).padStart(5)}%` +
    ` · caldo ${String(m.caldo).padStart(4)}%` +
    ` · barra ${String(m.barra).padStart(5)}%`
  );
}

const [file, riferimento] = process.argv.slice(2);
if (!file) {
  console.error(
    "uso: node scripts/densita.mjs <screenshot.png> [riferimento.png]\n" +
      "     senza riferimento, confronta con le soglie di\n" +
      "     docs/design-reference/README.md"
  );
  process.exit(2);
}

const browser = await chromium.launch();
const pagina = await browser.newPage();

const m = await misura(pagina, file);
console.log(riga(basename(file), m));

if (riferimento) {
  const r = await misura(pagina, riferimento);
  console.log(riga(basename(riferimento), r));
}

await browser.close();

/* L'esito e' un codice di uscita, non una frase: cosi' il ciclo §11.7 puo'
 * bocciare senza che qualcuno debba leggere. */
const falliti = [];
if (m.riempito < SOGLIE.riempito)
  falliti.push(`riempito ${m.riempito}% < ${SOGLIE.riempito}%`);
if (m.caldo < SOGLIE.caldoMin)
  falliti.push(`accento caldo ${m.caldo}% < ${SOGLIE.caldoMin}%`);
if (m.caldo > SOGLIE.caldoMax)
  falliti.push(`accento caldo ${m.caldo}% > ${SOGLIE.caldoMax}%`);
if (m.barra < SOGLIE.barra)
  falliti.push(`barra ${m.barra}% < ${SOGLIE.barra}%`);

if (falliti.length) {
  console.log("\nSOTTO SOGLIA — " + falliti.join(" · "));
  process.exit(1);
}
console.log("\nDENSITA' CONFORME");
