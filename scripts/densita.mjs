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
 * `docs/design-reference/README.md`, sezione «COSA GUARDARE».
 *
 * ⚠️ `L>25` NON E' PIU' UNA SOGLIA, e il perche' vale piu' della metrica.
 *
 * Era il criterio «quanta superficie non e' nera». Alla rev 5.9 le superfici
 * di base sono salite da L 18 a L 31, e `L>25` e' passata dal 16,4 % al
 * **96,9 %** su ws-01 — sopra il riferimento, che sta al 78,1 %. Da quel
 * momento non poteva piu' bocciare niente: qualunque schermata con un fondo
 * sopra L 25 la supera, compresa una schermata di un colore solo.
 *
 * **Una metrica satura e' peggio di nessuna metrica**, perche' passa sempre e
 * sembra una verifica. Resta STAMPATA come contesto — dice quanto e' alzato
 * il pavimento — e non concorre piu' al giudizio.
 *
 * Al suo posto due misure che una superficie uniforme NON puo' ingannare:
 *
 *   deviazione standard  quanto la luminanza si allontana dalla propria media.
 *                        Un fondo unico, per quanto chiaro, la tiene bassa.
 *   entropia             quanto e' distribuito l'istogramma a 16 bin, in bit.
 *                        Massimo 4 (16 bin equiprobabili), 0 se c'e' un solo
 *                        livello. Non chiede «quanto e' acceso» ma «quanto e'
 *                        ARTICOLATO», che e' la domanda che L>25 non sapeva
 *                        fare.
 */
const SOGLIE = {
  riempito: 25, // % pixel L>60 — riferimento 42,1 %
  caldoMin: 3, // % pixel r>b+15 — riferimento 5,7 %
  caldoMax: 6,
  barra: 25, // % pixel L>50 nella fascia della barra — riferimento 28–37 %
  // A meta' strada fra la nostra rev 5.7 e il piu' povero dei due riferimenti:
  //   dev.std   ws-01 5.7 = 20,3   famiglia-a/05 = 40,6   →  32
  //   entropia  ws-01 5.7 = 1,37   famiglia-a/05 = 2,85   →  2,4
  devStd: 32,
  entropia: 2.4,
};

//: L'istogramma dell'entropia. 16 bin e non 256: a 256 il rumore di
//: compressione e l'antialiasing riempirebbero decine di bin da soli e
//: l'entropia misurerebbe la qualita' del PNG invece della composizione.
const BIN = 16;

/** Rec. 709. La stessa formula del criterio, in un posto solo. */
const LUMA = "0.2126*d[i] + 0.7152*d[i+1] + 0.0722*d[i+2]";

async function misura(pagina, file) {
  const b64 = readFileSync(file).toString("base64");
  return pagina.evaluate(
    async ([b64, luma, bin]) => {
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
        sommaQuadrati = 0,
        oltre25 = 0,
        oltre60 = 0,
        oltre120 = 0,
        banda = 0,
        caldi = 0;
      const isto = new Float64Array(bin);

      // La fascia della barra: il 3,3 % superiore, che e' la misura del
      // riferimento. Non il nostro valore attuale, o misureremmo noi stessi.
      const hBarra = Math.round(c.height * 0.033);
      let barraOltre50 = 0;
      const nBarra = hBarra * c.width;

      for (let p = 0; p < n; p++) {
        const i = p * 4;
        const l = L(d, i);
        somma += l;
        sommaQuadrati += l * l;
        isto[Math.min(bin - 1, (l * bin) / 256 | 0)]++;
        if (l > 25 && l <= 120) banda++;
        if (l > 25) oltre25++;
        if (l > 60) oltre60++;
        if (l > 120) oltre120++;
        if (d[i] > d[i + 2] + 15 && l > 30) caldi++;
        if (p < nBarra && l > 50) barraOltre50++;
      }

      const pc = (x, tot = n) => Math.round((1000 * x) / tot) / 10;
      const media = somma / n;
      // varianza = E[X²] − E[X]²
      const devStd = Math.sqrt(Math.max(0, sommaQuadrati / n - media * media));
      // H = −Σ p·log₂p, in bit. I bin vuoti non contribuiscono.
      let entropia = 0;
      for (let k = 0; k < bin; k++) {
        const p = isto[k] / n;
        if (p > 0) entropia -= p * Math.log2(p);
      }
      return {
        larghezza: c.width,
        altezza: c.height,
        lumMedia: Math.round((10 * somma) / n) / 10,
        devStd: Math.round(10 * devStd) / 10,
        entropia: Math.round(100 * entropia) / 100,
        nonNero: pc(oltre25),
        banda: pc(banda),
        riempito: pc(oltre60),
        chiaro: pc(oltre120),
        caldo: pc(caldi),
        barra: pc(barraOltre50, nBarra),
      };
    },
    [b64, LUMA, BIN]
  );
}

function riga(nome, m) {
  return (
    `${nome.padEnd(30)} ${String(m.larghezza + "x" + m.altezza).padEnd(10)}` +
    ` lum ${String(m.lumMedia).padStart(5)}` +
    ` · dev ${String(m.devStd).padStart(5)}` +
    ` · H ${String(m.entropia).padStart(4)}` +
    ` · 25-120 ${String(m.banda).padStart(5)}%` +
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
// Le due misure di ARTICOLAZIONE vengono per prime: sono quelle che una
// superficie uniforme non puo' ingannare, e sono il motivo per cui L>25 e'
// stata ritirata dal giudizio (vedi SOGLIE).
if (m.entropia < SOGLIE.entropia)
  falliti.push(`entropia ${m.entropia} < ${SOGLIE.entropia} bit`);
if (m.devStd < SOGLIE.devStd)
  falliti.push(`dev.std ${m.devStd} < ${SOGLIE.devStd}`);
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
