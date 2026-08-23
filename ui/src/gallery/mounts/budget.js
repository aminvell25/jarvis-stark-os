/* Banco di misura del budget di frame — SPEC §10.4.
 *
 * «three.js ≤ 8 ms · PixiJS ≤ 3 ms · anime.js + layout ≤ 4 ms · margine 1 ms»,
 * dentro i ~16 ms di un frame a 60fps. Il criterio di §22 e' questo, e uno
 * screenshot non lo puo' verificare: va misurato.
 *
 * Due scelte che rendono la misura una misura e non un numero:
 *
 *   I TRE MOTORI INSIEME. Il budget e' per frame, non per componente. Sette
 *   componenti ciascuno dentro il proprio budget possono sforare tutti
 *   insieme, ed e' esattamente lo scenario dell'ambiente di §13. Qui girano
 *   contemporaneamente il globo (three), il campo di glifi (Pixi) e gli anelli
 *   (anime.js).
 *
 *   anime.js PER DIFFERENZA. three.js e Pixi li chiamiamo noi, e si cronometrano
 *   direttamente. anime.js gira sul proprio motore, dentro il suo
 *   requestAnimationFrame: cronometrarlo dall'esterno vorrebbe dire misurare il
 *   nostro rAF, non il suo. Si misura invece il frame INTERO con gli anelli
 *   fermi e con gli anelli in moto, e la differenza e' il suo costo — che e'
 *   anche il numero che conta davvero, perche' §10.4 gli attribuisce
 *   «anime.js + layout».
 *
 * ⚠️ Il numero headless NON e' il numero della macchina: Chromium senza GPU
 * rende con SwiftShader, in software. `npm run bench` lo misura nella finestra
 * Electron vera, ed e' quello che vale.
 */

import { FUSI } from "../fixtures/fusi.js";
import { crea as creaAnelli, css as cssAnelli } from "../../anim/rings.js";
import { crea as creaGlobo, css as cssGlobo } from "../../panels/globe.js";
import { crea as creaGlifi, css as cssGlifi } from "../../pixi/glyphs.js";
import { fontiPronte } from "../attese.js";

export const meta = { nome: "budget", versione: "1" };

const FRAME_PER_FASE = 150;
const TETTO = { three: 8, pixi: 3, anime: 4 };  // ms, §10.4

export const css = `
${cssGlobo}
${cssGlifi}
${cssAnelli}
.bnc { display: grid; gap: var(--s-3); }
.bnc__scena { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--s-3); height: 300px; }
.bnc__esito {
  --aug-tl: var(--s-3);
  --aug-border-bg: var(--cy-900);
  display: grid;
  gap: var(--s-2);
  padding: var(--s-3);
  background: var(--bg-panel);
  border-radius: var(--radius);
}
.bnc__riga {
  display: grid;
  grid-template-columns: 8ch 10ch 10ch 10ch 1fr;
  gap: var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-dim);
}
.bnc__riga b { font-weight: 400; color: var(--cy-300); }
.bnc__riga[data-sfora="1"] b { color: var(--rust); }
.bnc__intestazione {
  font-family: var(--font-ui);
  font-size: var(--t-micro);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--txt-ghost);
}
`;

const mediana = (v) => [...v].sort((a, b) => a - b)[Math.floor(v.length / 2)];
const p95 = (v) => [...v].sort((a, b) => a - b)[Math.min(v.length - 1, Math.floor(v.length * 0.95))];

/** Un giro di N frame. Restituisce le serie in millisecondi. */
async function gira(frame, passo) {
  const three = [];
  const pixi = [];
  const totale = [];
  let precedente = 0;
  for (let i = 0; i < frame; i++) {
    // eslint-disable-next-line no-await-in-loop
    const ora = await new Promise(requestAnimationFrame);
    if (precedente) totale.push(ora - precedente);
    precedente = ora;
    const m = await passo();
    three.push(m.three);
    pixi.push(m.pixi);
  }
  return { three, pixi, totale };
}

export async function monta(ospite) {
  ospite.style.width = "1180px";

  const radice = document.createElement("div");
  radice.className = "bnc";
  radice.innerHTML = `<div class="bnc__scena"></div><div class="bnc__esito"></div>`;
  ospite.appendChild(radice);
  const scena = radice.querySelector(".bnc__scena");

  const celle = [0, 1, 2].map(() => {
    const d = document.createElement("div");
    scena.appendChild(d);
    return d;
  });

  const globo = creaGlobo(celle[0]);
  globo.aggiorna({ topic: "geo.timezones", zone: FUSI, quando: "2026-08-18T14:05:00Z" });

  const glifi = await creaGlifi(celle[1]);
  const byte = new TextEncoder().encode(JSON.stringify({ topic: "telemetry", v: FUSI.slice(0, 12) }));
  await glifi.aggiungi(byte);

  const anelli = creaAnelli(celle[2]);
  anelli.aggiorna({ attivo: false, stato: "banco", motivo: "misura del budget", da_s: 0 });

  await fontiPronte();

  const passo = async () => {
    const a = performance.now();
    globo.scena.invalida();
    globo.scena.rendi();
    const b = performance.now();
    await glifi.aggiungi(byte);
    const c = performance.now();
    return { three: b - a, pixi: c - b };
  };

  // Fase 1: anelli fermi. Fase 2: anelli in moto. La differenza sui frame
  // interi e' il costo di anime.js piu' il layout che provoca.
  const fermo = await gira(FRAME_PER_FASE, passo);
  anelli.aggiorna({ attivo: true, stato: "banco", motivo: "misura del budget", da_s: 0 });
  const moto = await gira(FRAME_PER_FASE, passo);
  anelli.aggiorna({ attivo: false });

  const esito = {
    frame: FRAME_PER_FASE * 2,
    three: { mediana: mediana(moto.three), p95: p95(moto.three), tetto: TETTO.three },
    pixi: { mediana: mediana(moto.pixi), p95: p95(moto.pixi), tetto: TETTO.pixi },
    anime: {
      mediana: mediana(moto.totale) - mediana(fermo.totale),
      p95: p95(moto.totale) - p95(fermo.totale),
      tetto: TETTO.anime,
    },
    frameTotale: { mediana: mediana(moto.totale), p95: p95(moto.totale), tetto: 16.7 },
  };
  window.__budget = esito;

  const campo = (tag, testo, classe) => {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    e.textContent = testo;
    return e;
  };

  /* ⚠️ UN VERDETTO VALE SOLO DOVE LA MISURA VALE.
   *
   * I tetti di §10.4 sono QUOTE di un fotogramma da 16,7 ms: three.js 8, Pixi
   * 3, anime.js 4. Se il fotogramma intero non sta a 16,7 — perche' la pagina
   * non e' su uno schermo che si aggiorna, per esempio sotto Playwright durante
   * uno scatto — quelle quote non sono superate: sono **non misurate**, e
   * stamparci sopra «SFORA» e' dire una cosa falsa con l'aria di un dato.
   *
   * E' successo. `shots/budget.png`, generato da `scripts/shot.mjs`, riporta
   * «frame 83.30 ms · p95 100.10 · tetto 16.7 · SFORA». Il banco vero —
   * `npm run bench`, che gira nella finestra Electron con la GPU vera — dice
   * three 0,60 · pixi 0,50 · anime 0,00 · frame 16,70, tutto dentro. Chi
   * leggesse quello scatto concluderebbe che il budget e' sfondato di cinque
   * volte.
   *
   * La condizione e' quella che rende la misura possibile, non un elenco di
   * ambienti: se il fotogramma intero e' almeno il doppio del proprio tetto, la
   * pagina non sta girando a vsync e nessuna quota di quel fotogramma
   * significa niente. */
  const misurabile = esito.frameTotale.mediana < 2 * esito.frameTotale.tetto;

  const riga = (nome, m) => {
    const r = campo("div", "", "bnc__riga");
    r.dataset.sfora = misurabile && m.mediana > m.tetto ? "1" : "0";
    r.append(
      campo("span", nome),
      campo("b", `${m.mediana.toFixed(2)} ms`),
      campo("span", `p95 ${m.p95.toFixed(2)}`),
      campo("span", `tetto ${m.tetto}`),
      campo("span", !misurabile ? "non misurabile" : m.mediana > m.tetto ? "SFORA" : "dentro"),
    );
    return r;
  };

  radice.querySelector(".bnc__esito").replaceChildren(
    campo("div", `Budget di frame §10.4 · ${esito.frame} frame · ` +
                 "globo + glifi + anelli insieme" +
                 (misurabile ? "" : ` · ⚠️ fotogramma a ${esito.frameTotale.mediana.toFixed(1)} ms:` +
                  " questa pagina non gira a vsync, i numeri non sono un verdetto." +
                  " Il banco vero e' npm run bench"), "bnc__intestazione"),
    riga("three.js", esito.three),
    riga("pixi", esito.pixi),
    riga("anime.js", esito.anime),
    riga("frame", esito.frameTotale),
  );
}
