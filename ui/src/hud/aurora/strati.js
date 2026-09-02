/** Gli strati SVG attorno al nucleo Aurora: ghiera, anelli, settori, vetro.
 *
 * ## La regola di adattamento, di nuovo
 *
 * Il riferimento e' disegnato per un quadro 1024x1024 in cui il nucleo riempie
 * tutto. Qui vive in Ø326, dietro i pannelli. **I raggi si conservano come
 * rapporti** (viewBox 1024, gli stessi numeri del riferimento); **la
 * tipografia si dimensiona in unita' di viewBox** perche' cada sui gradini
 * --t-* veri alla resa. A Ø326 il testo da 12,5 px del riferimento diventerebbe
 * 4 px: illeggibile. Vedi `hud/tipografia.js`.
 *
 * ## Che cosa NON e' stato portato
 *
 * ⚠️ Le stringhe del riferimento — «REC248 | 5NC0DE | MK-XL | PWR.98» e le
 * cifre esadecimali — sono decorazione, e l'invariante 23 le vieta. Le corone
 * portano lo stesso testo che portavano prima: gli eventi veri del diario, in
 * base 16. Dove non ci sono eventi la corona e' VUOTA, e si vede.
 */

import { CENTRO, VIEWBOX } from "./geometria.js";
import { gradino, caratteriSulGiro } from "../tipografia.js";

const NS = "http://www.w3.org/2000/svg";

export function el(nome, attributi = {}) {
  const e = document.createElementNS(NS, nome);
  for (const [k, v] of Object.entries(attributi)) e.setAttribute(k, String(v));
  return e;
}

/** Da gradi (0 = alto, orario) a un punto sul cerchio di raggio r. */
function punto(gradi, r) {
  const a = (gradi - 90) * Math.PI / 180;
  return [CENTRO + Math.cos(a) * r, CENTRO + Math.sin(a) * r];
}

/** Un settore anulare fra due raggi, da un angolo all'altro. */
function settore(da, a, dentro, fuori) {
  const [x1, y1] = punto(da, fuori);
  const [x2, y2] = punto(a, fuori);
  const [x3, y3] = punto(a, dentro);
  const [x4, y4] = punto(da, dentro);
  const lungo = ((a - da) % 360 + 360) % 360 > 180 ? 1 : 0;
  return "M" + x1.toFixed(1) + "," + y1.toFixed(1)
    + " A" + fuori + "," + fuori + " 0 " + lungo + " 1 " + x2.toFixed(1) + "," + y2.toFixed(1)
    + " L" + x3.toFixed(1) + "," + y3.toFixed(1)
    + " A" + dentro + "," + dentro + " 0 " + lungo + " 0 " + x4.toFixed(1) + "," + y4.toFixed(1)
    + " Z";
}

/** Un arco aperto, per i tratti spessi e le linee di contorno. */
function arco(da, a, r) {
  const [x1, y1] = punto(da, r);
  const [x2, y2] = punto(a, r);
  const lungo = ((a - da) % 360 + 360) % 360 > 180 ? 1 : 0;
  return "M" + x1.toFixed(1) + "," + y1.toFixed(1)
    + " A" + r + "," + r + " 0 " + lungo + " 1 " + x2.toFixed(1) + "," + y2.toFixed(1);
}

/** Gli otto settori del quadrante, misurati sul riferimento.
 *
 * ⚠️ Non sono otto uguali: quattro larghi (56-67°) a opacita' alta e quattro
 * stretti (16-18°) quasi trasparenti. L'asimmetria e' cio' che fa leggere il
 * quadrante come uno STRUMENTO orientato invece che come una rosetta. */
const SETTORI = [
  { da: 288, a: 346, chiaro: false, op: 0.23 },
  { da: 351, a: 418, chiaro: false, op: 0.14 },
  { da: 62, a: 80, chiaro: true, op: 0.06 },
  { da: 100, a: 118, chiaro: true, op: 0.06 },
  { da: 122, a: 178, chiaro: false, op: 0.22 },
  { da: 182, a: 244, chiaro: false, op: 0.13 },
  { da: 248, a: 264, chiaro: true, op: 0.06 },
  { da: 284, a: 300, chiaro: true, op: 0.06 },
];

export const css = [
  ".au { position: absolute; inset: 0; display: block; }",
  ".au__ghiera { fill: url(#au-ghiera); }",
  ".au__fondo { fill: var(--bg-abyss); opacity: 0.85; }",
  ".au__orlo { fill: none; stroke: var(--cy-900); stroke-width: 3.5; opacity: 0.6; }",
  ".au__riflesso { fill: none; opacity: 0.35; }",
  ".au__velo { fill: none; stroke: var(--icona); stroke-width: 3.2; opacity: 0.06; }",
  ".au__solco { fill: none; stroke: var(--bg-abyss); stroke-width: 25; opacity: 0.5; }",
  ".au__filo { fill: none; stroke: var(--cy-300); stroke-width: 3.2; opacity: 0.14; }",
  ".au__cresta { fill: none; stroke: var(--cy-100); stroke-width: 3.8; opacity: 0.34; }",
  ".au__grana { fill: none; stroke: var(--cy-500); stroke-width: 19; opacity: 0.1; }",
  ".au__banda { fill: none; stroke: var(--cy-500); stroke-width: 220; opacity: 0.2; }",
  ".au__banda--tenue { stroke: var(--cy-300); stroke-width: 63; opacity: 0.08; }",
  ".au__settore { stroke: none; fill: var(--cy-300); }",
  ".au__settore--chiaro { fill: var(--cy-500); }",
  ".au__tratteggio { fill: none; stroke: var(--cy-050); stroke-width: 208; }",
  ".au__contorno { fill: none; stroke: var(--cy-050); stroke-width: 5; opacity: 0.5; }",
  ".au__contorno--interno { stroke-width: 4.4; opacity: 0.44; }",
  ".au__anello { fill: none; stroke: var(--cy-300); stroke-width: 38; opacity: 0.1; }",
  ".au__bordo { fill: none; stroke: var(--cy-100); stroke-width: 3.2; opacity: 0.3; }",
  ".au__bordo--dentro { opacity: 0.26; }",
  ".au__hex { font-family: var(--font-mono); fill: var(--cy-300); stroke: none;",
  "  user-select: none; pointer-events: none; }",
  ".au__hex--fitto { fill: var(--cy-100); }",
  ".au__vetro { fill: url(#au-vetro); }",
  ".au__vetro-orlo { fill: none; stroke: var(--bg-abyss); stroke-width: 19; opacity: 0.62; }",
  ".au__vetro-filo { fill: none; stroke: var(--cy-100); stroke-width: 4.4; opacity: 0.34; }",
  ".au__vetro-dentro { fill: none; stroke: var(--cy-300); stroke-width: 3.2; opacity: 0.08; }",
  ".au__spettro { fill: none; stroke: var(--cy-050); stroke-width: 5; opacity: 0; }",
  ".au__giro { position: absolute; transform-origin: 50% 50%; will-change: transform; }",
  ".au__giro svg { display: block; }",
  ".au__punteggiato { fill: none; stroke: var(--cy-100); }",
  ".au__punteggiato--forte { stroke: var(--cy-050); }",
].join("\n");

/** Gli strati fissi, dal fondo fino al bordo del vetro. */
export function costruisci(svg) {
  const defs = el("defs");
  /* Cinque fermate e non due: la ghiera del riferimento non e' un disco scuro,
     e' metallo, e il metallo si legge dalla NON monotonia — schiarisce al 72 %
     e torna a scurire sul bordo. Con due fermate diventa una vignetta. */
  const g = el("radialGradient", { id: "au-ghiera", cx: "38%", cy: "30%", r: "82%" });
  for (const [off, colore] of [
    ["0", "--bg-void"], ["0.42", "--bg-void"], ["0.72", "--bg-deep"],
    ["0.9", "--bg-void"], ["1", "--bg-abyss"],
  ]) g.appendChild(el("stop", { offset: off, "stop-color": "var(" + colore + ")" }));
  defs.appendChild(g);
  svg.appendChild(defs);

  svg.appendChild(el("circle", { class: "au__fondo", cx: CENTRO, cy: CENTRO, r: 502 }));
  svg.appendChild(el("circle", { class: "au__ghiera", cx: CENTRO, cy: CENTRO, r: 470 }));
  svg.appendChild(el("circle", { class: "au__orlo", cx: CENTRO, cy: CENTRO, r: 470 }));
  svg.appendChild(el("circle", { class: "au__velo", cx: CENTRO, cy: CENTRO, r: 459 }));
  svg.appendChild(el("circle", { class: "au__solco", cx: CENTRO, cy: CENTRO, r: 450 }));
  svg.appendChild(el("circle", { class: "au__filo", cx: CENTRO, cy: CENTRO, r: 450 }));
  svg.appendChild(el("path", { class: "au__cresta", d: arco(295, 65, 450) }));
  svg.appendChild(el("circle", {
    class: "au__grana", cx: CENTRO, cy: CENTRO, r: 443,
    "stroke-dasharray": "3.2 17.8",
  }));

  svg.appendChild(el("circle", { class: "au__banda", cx: CENTRO, cy: CENTRO, r: 320 }));
  svg.appendChild(el("circle", {
    class: "au__banda au__banda--tenue", cx: CENTRO, cy: CENTRO, r: 345,
  }));

  for (const s of SETTORI) {
    svg.appendChild(el("path", {
      class: "au__settore" + (s.chiaro ? " au__settore--chiaro" : ""),
      d: settore(s.da, s.a, 285, 355), opacity: s.op,
    }));
  }

  /* I tre tratteggi pesanti: sono il riferimento, e sono TRE con opacita'
     decrescente (0,19 / 0,15 / 0,06) perche' il quadrante ha un davanti e un
     dietro. Quattro uguali lo appiattirebbero. */
  const pesanti = [[122, 178, 0.19], [182, 240, 0.15], [288, 344, 0.06]];
  for (const [da, a, op] of pesanti) {
    svg.appendChild(el("path", {
      class: "au__tratteggio", d: arco(da, a, 320),
      "stroke-dasharray": "3.8 15.7", opacity: op,
    }));
  }

  for (const [da, a, r, dentro] of [[295, 65, 354, false], [300, 60, 286, true],
                                    [115, 245, 354, false], [120, 240, 286, true]]) {
    svg.appendChild(el("path", {
      class: "au__contorno" + (dentro ? " au__contorno--interno" : ""), d: arco(da, a, r),
    }));
  }

  svg.appendChild(el("circle", { class: "au__anello", cx: CENTRO, cy: CENTRO, r: 361 }));
  svg.appendChild(el("circle", { class: "au__bordo", cx: CENTRO, cy: CENTRO, r: 355 }));
  svg.appendChild(el("circle", {
    class: "au__bordo au__bordo--dentro", cx: CENTRO, cy: CENTRO, r: 285,
  }));
  return svg;
}

/** Il vetro sopra la tela WebGL, e la traccia dello spettro. */
export function montaVetro(svg) {
  const defs = el("defs");
  const g = el("radialGradient", { id: "au-vetro", cx: "50%", cy: "50%", r: "50%" });
  /* Sei fermate, e l'opacita' sale verso il BORDO: e' un vetro visto da dentro,
     non una luce. Il picco a 0,9 e' il bordo della lente. */
  for (const [off, tokenColore, op] of [
    ["0", "--cy-500", "0.015"], ["0.72", "--cy-500", "0.05"],
    ["0.81", "--cy-300", "0.17"], ["0.9", "--cy-200", "0.3"],
    ["0.97", "--cy-050", "0.28"], ["1", "--cy-300", "0.2"],
  ]) {
    g.appendChild(el("stop", {
      offset: off, "stop-color": "var(" + tokenColore + ")", "stop-opacity": op,
    }));
  }
  defs.appendChild(g);
  svg.appendChild(defs);
  svg.appendChild(el("circle", { class: "au__vetro", cx: CENTRO, cy: CENTRO, r: 278 }));
  svg.appendChild(el("circle", { class: "au__vetro-orlo", cx: CENTRO, cy: CENTRO, r: 281.5 }));
  const orlo = el("circle", { class: "au__vetro-filo", cx: CENTRO, cy: CENTRO, r: 277 });
  svg.appendChild(orlo);
  const spettro = el("path", { class: "au__spettro", d: "" });
  svg.appendChild(spettro);
  svg.appendChild(el("circle", { class: "au__vetro-dentro", cx: CENTRO, cy: CENTRO, r: 212 }));
  return { orlo, spettro };
}

/** I quattro anelli che girano, ciascuno col proprio periodo e verso.
 *
 * ⚠️ 320 / 520 / 260 / 200 secondi. I rapporti fra i periodi non sono interi
 * — 320/520 = 0,615, 260/200 = 1,3 — e la ragione e' la stessa di sempre: due
 * periodi in rapporto intero tornano insieme, e allora il moto ha una FASE
 * riconoscibile invece di sembrare continuo. Sono i numeri del riferimento e
 * per una volta erano gia' giusti.
 */
export const ANELLI = [
  { id: "a1", lato: 880, r: 425, verso: 1, periodo: 320, testo: true, fitto: false },
  { id: "a2", lato: 792, r: 383, verso: 1, periodo: 520, testo: true, fitto: true },
  { id: "a3", lato: 692, r: 320, verso: -1, periodo: 260, testo: false },
  { id: "a4", lato: 452, r: 219, verso: -1, periodo: 200, testo: false },
];

export function montaAnelli(radice, diametroPx) {
  const nodi = [];
  for (const a of ANELLI) {
    const box = document.createElement("div");
    box.className = "au__giro";
    box.dataset.anello = a.id;
    const off = (VIEWBOX - a.lato) / 2;
    box.style.left = (off / VIEWBOX * 100) + "%";
    box.style.top = (off / VIEWBOX * 100) + "%";
    box.style.width = (a.lato / VIEWBOX * 100) + "%";
    box.style.height = (a.lato / VIEWBOX * 100) + "%";
    const svg = el("svg", {
      viewBox: off + " " + off + " " + a.lato + " " + a.lato,
      width: "100%", height: "100%",
    });
    if (a.testo) {
      const defs = el("defs");
      const d = "M" + CENTRO + "," + (CENTRO - a.r)
        + " A" + a.r + "," + a.r + " 0 1 1 " + CENTRO + "," + (CENTRO + a.r)
        + " A" + a.r + "," + a.r + " 0 1 1 " + CENTRO + "," + (CENTRO - a.r);
      defs.appendChild(el("path", { id: "au-giro-" + a.id, d, fill: "none" }));
      svg.appendChild(defs);
      const corpo = gradino("--t-micro", diametroPx);
      const t = el("text", { class: "au__hex" + (a.fitto ? " au__hex--fitto" : "") });
      t.style.fontSize = corpo.toFixed(1) + "px";
      t.style.letterSpacing = a.fitto ? "0.10em" : "0.18em";
      t.setAttribute("opacity", a.fitto ? "0.7" : "0.22");
      const tp = el("textPath", { href: "#au-giro-" + a.id, startOffset: "1%" });
      t.appendChild(tp);
      svg.appendChild(t);
      nodi.push({ anello: a, testo: tp, capienza: caratteriSulGiro(a.r, corpo, a.fitto ? 0.10 : 0.18) });
    } else {
      /* I due anelli senza testo sono TACCHE: un tratteggio fitto e uno rado
         sovrapposti. Il rado ha un tratto solo lungo tutto il giro — e' un
         indice, e si vede passare. */
      const [fitto, rado] = a.id === "a3"
        ? [[45, "6.4 82.5", 0.38], [96, "8.3 790", 0.44]]
        : [[3.2, "9.5 28.6", 0.2], [22, "5 1088", 0.3]];
      for (const [w, dash, op] of [fitto, rado]) {
        svg.appendChild(el("circle", {
          class: "au__punteggiato" + (op > 0.35 ? " au__punteggiato--forte" : ""),
          cx: CENTRO, cy: CENTRO, r: a.r, "stroke-width": w,
          "stroke-dasharray": dash, opacity: op,
        }));
      }
    }
    box.appendChild(svg);
    radice.appendChild(box);
    nodi[nodi.length - 1] = nodi[nodi.length - 1] || null;
    box.dataset.periodo = String(a.periodo);
    box.dataset.verso = String(a.verso);
  }
  return nodi.filter(Boolean);
}
