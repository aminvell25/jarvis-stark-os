/* Quadranti radiali sul carico reale — SPEC §11.5, §13.
 *
 * Riferimento: famiglia-a/11-tavola-periodica-scanner.png, gli strumenti
 * circolari della colonna di sinistra.
 *
 * Tre quadranti su tre grandezze VERE, dal topic `telemetry` che il core
 * pubblica da Fase 1: psutil, non numeri inventati (§11.9). Senza sorgente il
 * pannello mostra lo stato vuoto, non uno zero finto — uno zero e' un valore,
 * e mentirebbe.
 *
 * Le soglie sono quelle di §16, le stesse del pannello telemetria: l'accento
 * caldo compare quando significa qualcosa (§11.6 regola 2), e prima di allora
 * il pannello e' interamente freddo.
 *
 * Divisione del lavoro:
 *   scala graduata  geometria parametrica, passata dal gate una volta sola
 *   arco del valore d3-shape, ridisegnato a ogni campione (§11.5)
 *   numero          DOM, contato da anime.js (invariante 20, §10.3)
 */

import arc from "../../vendor/d3-shape/arc.js";
import { contatore } from "../anim/counters.js";
import { RadialDial } from "../three/components/radial-dial.js";
import { qualityGate } from "../three/quality-gate.js";
import { versoPath, viewBox } from "../three/svg.js";

export const meta = { nome: "dials", versione: "1" };

const SOGLIA_RAM = 90;   // §16
const SOGLIA_TEMP = 75;  // §16
const PREAVVISO = 10;    // punti sotto la soglia: giallo prima del rosso

/** I tre strumenti. `max` e' il fondo scala, non un valore osservato. */
const QUADRANTI = [
  { chiave: "cpu_percent",    etichetta: "CPU",  unita: "%",  max: 100, decimali: 1, soglia: null },
  { chiave: "ram_percent",    etichetta: "RAM",  unita: "%",  max: 100, decimali: 1, soglia: SOGLIA_RAM },
  { chiave: "package_temp_c", etichetta: "PKG",  unita: "°C", max: 100, decimali: 1, soglia: SOGLIA_TEMP },
];

const NS = "http://www.w3.org/2000/svg";
const RAD = Math.PI / 180;

/* La fascia del valore sta DENTRO la graduazione, ed e' SOTTILE.
 *
 * La prima versione la faceva spessa sette millimetri: nello screenshot era
 * l'elemento piu' pesante del pannello e i quadranti sembravano un cruscotto,
 * non uno strumento. Famiglia A ha bordi hairline, mai spessi. */
const VALORE_ESTERNO = 51;
const VALORE_INTERNO = 48;

export const css = `
.pnl-dials {
  --aug-border-bg: var(--cy-900);
  --aug-tl: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 4);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-dials__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-dials__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-dials__id, .pnl-dials__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-dials__ctrl { letter-spacing: 0.16em; }

.pnl-dials__corpo {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: var(--s-3);
  padding: var(--s-3);
  min-height: 0;
}
.pnl-dials__q {
  position: relative;
  display: grid;
  min-height: 0;
}
.pnl-dials__svg { display: block; width: 100%; height: 100%; min-width: 0; min-height: 0; }

.pnl-dials__scala {
  fill: none;
  stroke: var(--cy-700);
  stroke-width: var(--line-base);
  vector-effect: non-scaling-stroke;
}
.pnl-dials__grad {
  fill: none;
  stroke: var(--cy-700);
  stroke-width: var(--line-hair);
  vector-effect: non-scaling-stroke;
}
/* Il valore resta FREDDO. Il caldo tocca solo l'eccedenza oltre la soglia di
   §16 e il numero: nella prima versione l'intero arco diventava rosso e due
   quadranti su tre erano interamente caldi — molto oltre il 10% della
   superficie colorata che §11.6 regola 2 concede. Colorare solo l'eccedenza
   costa meno superficie e dice di piu': si vede QUANTO si e' oltre. */
.pnl-dials__valore { fill: var(--cy-500); stroke: none; }
.pnl-dials__eccesso { fill: var(--rust); stroke: none; }
.pnl-dials__soglia {
  fill: none;
  stroke: var(--amber);
  stroke-width: var(--line-base);
  vector-effect: non-scaling-stroke;
  opacity: 0;
}
.pnl-dials__q[data-livello="warn"] .pnl-dials__soglia,
.pnl-dials__q[data-livello="critical"] .pnl-dials__soglia { opacity: 1; }

/* Il numero e' DOM sovrapposto all'SVG: invariante 20. */
.pnl-dials__centro {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  pointer-events: none;
}
.pnl-dials__num {
  font-family: var(--font-mono);
  font-size: var(--t-title);
  line-height: 1;
  color: var(--cy-500);
}
.pnl-dials__q[data-livello="warn"] .pnl-dials__num { color: var(--amber); }
.pnl-dials__q[data-livello="critical"] .pnl-dials__num { color: var(--rust); }
.pnl-dials__unita {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-dials__nome {
  margin-top: var(--s-1);
  font-size: var(--t-micro);
  letter-spacing: 0.16em;
  color: var(--txt-dim);
}

.pnl-dials__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-dials__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-dials[data-stato="vuoto"] .pnl-dials__corpo { display: none; }
.pnl-dials[data-stato="vuoto"] .pnl-dials__vuoto { display: block; }
`;

function elSvg(nome, attributi = {}) {
  const e = document.createElementNS(NS, nome);
  for (const [k, v] of Object.entries(attributi)) e.setAttribute(k, v);
  return e;
}

/* d3-shape misura gli angoli da mezzogiorno in senso orario; la geometria
 * parametrica li misura da +X in senso antiorario. La conversione sta qui,
 * scritta una volta: theta = pi/2 - alfa. Senza, l'arco del valore parte dal
 * posto giusto solo per i quadranti che cominciano a ore dodici. */
const versoD3 = (alfaRad) => Math.PI / 2 - alfaRad;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-dials";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-dials__testa">
      <span class="pnl-dials__etichetta">Carico sistema</span>
      <span class="pnl-dials__id">DIAL_B02 · ver ${meta.versione}</span>
      <span class="pnl-dials__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-dials__corpo"></div>
    <div class="pnl-dials__vuoto">NESSUNA SORGENTE COLLEGATA</div>
    <div class="pnl-dials__piede">
      <span class="pnl-dials__ora">--:--:--</span>
      <span class="pnl-dials__conteggio"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const corpo = radice.querySelector(".pnl-dials__corpo");
  const strumenti = [];
  let vertici = 0;

  const generatore = arc();

  for (const q of QUADRANTI) {
    const cella = document.createElement("div");
    cella.className = "pnl-dials__q";
    cella.dataset.livello = "nominal";
    cella.innerHTML = `
      <div class="pnl-dials__centro">
        <span class="pnl-dials__num">—</span>
        <span class="pnl-dials__unita">${q.unita}</span>
        <span class="pnl-dials__nome">${q.etichetta}</span>
      </div>
    `;
    corpo.appendChild(cella);

    const componente = new RadialDial({ name: `radial-dial-${q.etichetta.toLowerCase()}` });
    const geometria = componente.build();
    qualityGate(componente, geometria, ["linea", "costruzione"]); // ◄ prima del render
    vertici += geometria.getAttribute("position").count;

    const svg = elSvg("svg", { class: "pnl-dials__svg", "aria-hidden": "true" });
    // viewBox dall'estensione VERA della geometria, non da un quadrato di
    // lato 2R: un quadrante da 270 gradi non occupa il fondo, e un quadrato
    // gli lascerebbe sotto una fascia vuota che nessun dato riempie. Il
    // margine copre il segno di soglia, che sporge di 4 mm.
    svg.setAttribute("viewBox", viewBox(geometria, 8));
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    const riempimento = elSvg("path", { class: "pnl-dials__valore" });
    const eccesso = elSvg("path", { class: "pnl-dials__eccesso" });
    svg.appendChild(riempimento);
    svg.appendChild(eccesso);

    // Il segno della soglia di §16, sulla scala. Senza, il cambio di colore
    // sarebbe un fatto senza un dove: si vedrebbe che qualcosa e' cambiato ma
    // non rispetto a cosa.
    if (q.soglia != null) {
      const a = componente.angoloPer(q.soglia / q.max);
      const r0 = componente.params.outerR;
      const r1 = componente.params.outerR + 4;
      svg.appendChild(
        elSvg("path", {
          class: "pnl-dials__soglia",
          d: `M${(Math.cos(a) * r0).toFixed(3)},${(-Math.sin(a) * r0).toFixed(3)}` +
             `L${(Math.cos(a) * r1).toFixed(3)},${(-Math.sin(a) * r1).toFixed(3)}`,
        })
      );
    }
    for (const p of [...versoPath(geometria), ...versoPath(componente.constructionLines())]) {
      svg.appendChild(
        elSvg("path", { d: p.d, class: p.ruolo === "linea" ? "pnl-dials__scala" : "pnl-dials__grad" })
      );
    }
    cella.insertBefore(svg, cella.firstChild);

    const elNum = cella.querySelector(".pnl-dials__num");
    const conta = contatore((v) => { elNum.textContent = v.toFixed(q.decimali); },
                            { decimali: q.decimali });

    strumenti.push({ q, cella, componente, riempimento, eccesso, conta, generatore, primo: true });
  }

  const elOra = radice.querySelector(".pnl-dials__ora");
  const elConteggio = radice.querySelector(".pnl-dials__conteggio");
  elConteggio.textContent = `${QUADRANTI.length} quadranti · ${vertici} vertici`;

  let campioni = 0;

  function aggiorna(msg) {
    if (msg?.topic !== "telemetry") return;
    campioni += 1;
    radice.dataset.stato = "pieno";

    for (const s of strumenti) {
      const valore = msg[s.q.chiave];
      if (typeof valore !== "number") continue;

      const frazione = Math.min(1, Math.max(0, valore / s.q.max));
      const soglia = s.q.soglia;
      const fSoglia = soglia == null ? 1 : soglia / s.q.max;
      const settore = (da, a) =>
        a <= da
          ? null
          : s.generatore({
              innerRadius: VALORE_INTERNO,
              outerRadius: VALORE_ESTERNO,
              startAngle: versoD3(s.componente.angoloPer(da)),
              endAngle: versoD3(s.componente.angoloPer(a)),
            });

      s.riempimento.setAttribute("d", settore(0, Math.min(frazione, fSoglia)) ?? "");
      s.eccesso.setAttribute("d", settore(fSoglia, frazione) ?? "");

      s.cella.dataset.livello =
        soglia == null ? "nominal"
        : valore > soglia ? "critical"
        : valore > soglia - PREAVVISO ? "warn"
        : "nominal";

      // Il primo campione non viene "da" nessun valore: mostrarlo contando da
      // zero sarebbe un'animazione senza causa.
      if (s.primo) { s.conta.subito(valore); s.primo = false; } else { s.conta.verso(valore); }
    }

    if (typeof msg.ts === "number") {
      elOra.textContent = new Date(msg.ts * 1000).toLocaleTimeString("it-IT", { hour12: false });
    }
    elConteggio.textContent =
      `${QUADRANTI.length} quadranti · ${vertici} vertici · ${campioni} campioni`;
  }

  return { radice, aggiorna };
}
