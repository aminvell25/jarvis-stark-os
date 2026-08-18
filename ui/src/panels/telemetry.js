/* Pannello telemetria — SPEC §10.2, §11.5, §13.
 *
 * Anatomia a cinque parti di §10.2: etichetta in caps, id/versione, controlli,
 * contenuto reale, piede tecnico. Taglio a 45° su UN vertice (regola
 * dell'asimmetria: mai zero, mai quattro), via augmented-ui.
 *
 * TRE STATI, non due. L'invariante 23 vuole dati veri o stato vuoto esplicito:
 *
 *   collegato  valori reali dal socket
 *   vuoto      NESSUNA SORGENTE COLLEGATA in --txt-ghost (§11.9)
 *   galleria   dati finti ma strutturalmente veri — l'unica eccezione di §11.9
 *
 * La sorgente arriva per ARGOMENTO. Non c'e' un ramo `if` che cambi
 * comportamento fra galleria e app: girerebbe un componente diverso da quello
 * verificato, e il ciclo §11.7 giudicherebbe la cosa sbagliata.
 */

import uPlot from "../../vendor/uPlot.esm.js";
import { tok } from "../style/tokens.js";

export const meta = { nome: "telemetry", versione: "1" };

const CAMPIONI = 120; // 48 s a 2,5 Hz
const SOGLIA_RAM = 90; // §16
const SOGLIA_TEMP = 75; // §16


export const css = `
.pnl-tel {
  --aug-border-bg: var(--cy-900);
  --aug-br: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  /* Riempie chi lo ospita: dentro WinBox e' la finestra, nella galleria e' la
     cella. Una larghezza fissa lasciava mezzo pannello vuoto dentro WinBox. */
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-tel__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-tel__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-tel__id, .pnl-tel__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-tel__ctrl { letter-spacing: 0.16em; }
.pnl-tel__corpo {
  display: grid;
  grid-template-rows: auto 1fr auto;
  padding: var(--s-3);
  /* Senza, la riga 1fr non puo' scendere sotto il proprio contenuto — in
     CSS Grid il minimo predefinito e' auto, non zero — e il pannello
     deborda della differenza. Sulla scrivania di §13 il pannello ha
     l'altezza che gli da' il workspace, non quella che vorrebbe: 54 px
     fuori, misurati, e una barra di scorrimento dove non serve. */
  min-height: 0;
}
/* La riga occupa tutta la larghezza. Prima le tre metriche stavano a
   sinistra e i due terzi a destra restavano vuoti: §11.8 CONTENUTO, "la
   densita' regge il confronto con l'immagine di riferimento?" — non
   reggeva. §11.6 regola 3: un pannello con poco da dire si rimpicciolisce,
   non si riempie di spazio. Qui il pannello aveva da dire di piu' di quanto
   mostrasse: ram_available_bytes arriva dal core a ogni messaggio e non
   veniva usato. */
.pnl-tel__metriche {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding-bottom: var(--s-2);
}
.pnl-tel__m { display: flex; align-items: baseline; gap: var(--s-1); }
.pnl-tel__nome {
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-dim);
}
.pnl-tel__val {
  font-family: var(--font-mono);
  font-size: var(--t-title);
  line-height: 1;
  color: var(--cy-500);
}
.pnl-tel__val[data-critico="1"] { color: var(--rust); }
.pnl-tel__unita {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-tel__grafico { min-height: calc(var(--grid) + var(--s-3)); }
.pnl-tel__proc {
  padding-top: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
}
.pnl-tel__riga {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-dim);
}
.pnl-tel__riga span:last-child { color: var(--cy-300); }
.pnl-tel__piede {
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-tel__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-tel[data-stato="vuoto"] .pnl-tel__corpo { display: none; }
.pnl-tel[data-stato="vuoto"] .pnl-tel__vuoto { display: block; }

/* uPlot dipinge su canvas, ma crea anche DOM, e quel DOM porta la tipografia
   e i colori della LIBRERIA. Il livello 1 dell'audit li ha visti al primo
   scatto: "system-ui" su sette elementi e un "rgba(0,0,0,.07)" sulla
   selezione. §11.6 regola 1 dice che i due font sono il 40% dell'effetto —
   una libreria che ne infila un terzo dentro un pannello lo smonta.

   Non si tocca ui/vendor/: quei file si riscrivono a ogni "npm run vendor".
   Si sovrascrive qui, dove la regola e' nostra. */
.pnl-tel .uplot, .pnl-tel .uplot * { font-family: var(--font-mono); }
.pnl-tel .u-wrap, .pnl-tel .u-over, .pnl-tel .u-under { border-radius: var(--radius); }
.pnl-tel .u-axis { color: var(--txt-ghost); }
.pnl-tel .u-select { background: transparent; }
`;

const HTML = `
<section class="pnl-tel" data-stato="vuoto" data-augmented-ui="br-clip border">
  <header class="pnl-tel__testa">
    <span class="pnl-tel__etichetta">Telemetria</span>
    <span class="pnl-tel__id">A01 &middot; ver ${meta.versione}</span>
    <span class="pnl-tel__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-tel__corpo">
    <div class="pnl-tel__metriche">
      <div class="pnl-tel__m"><span class="pnl-tel__nome">cpu</span
        ><span class="pnl-tel__val" data-m="cpu">&mdash;</span
        ><span class="pnl-tel__unita">%</span></div>
      <div class="pnl-tel__m"><span class="pnl-tel__nome">ram</span
        ><span class="pnl-tel__val" data-m="ram">&mdash;</span
        ><span class="pnl-tel__unita">%</span></div>
      <div class="pnl-tel__m"><span class="pnl-tel__nome">temp</span
        ><span class="pnl-tel__val" data-m="temp">&mdash;</span
        ><span class="pnl-tel__unita">&deg;C</span></div>
      <div class="pnl-tel__m"><span class="pnl-tel__nome">libera</span
        ><span class="pnl-tel__val" data-m="libera">&mdash;</span
        ><span class="pnl-tel__unita">GiB</span></div>
    </div>
    <div class="pnl-tel__grafico"></div>
    <div class="pnl-tel__proc"></div>
  </div>
  <div class="pnl-tel__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-tel__piede"></footer>
</section>
`;

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-tel");
  const val = (m) => el.querySelector(`[data-m="${m}"]`);
  const proc = el.querySelector(".pnl-tel__proc");
  const piede = el.querySelector(".pnl-tel__piede");
  const grafico = el.querySelector(".pnl-tel__grafico");

  const xs = [], cpu = [], ram = [];

  const plot = new uPlot(
    {
      width: 1,
      height: 1,
      // Nessuna animazione e nessun cursore: §10.3 vieta il movimento senza
      // causa, e uPlot non anima per scelta dell'autore (§11.3).
      cursor: { show: false },
      legend: { show: false },
      scales: { y: { range: [0, 100] } },
      axes: [
        { show: false },
        { stroke: tok("--txt-ghost"), grid: { stroke: tok("--cy-900"), width: 1 },
          ticks: { show: false }, font: `10px ${tok("--font-mono")}`, size: 28 },
      ],
      series: [
        {},
        { stroke: tok("--cy-500"), width: 1, points: { show: false } },
        { stroke: tok("--cy-700"), width: 1, points: { show: false } },
      ],
    },
    [xs, cpu, ram],
    grafico,
  );

  function ridimensiona() {
    const r = grafico.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) plot.setSize({ width: r.width, height: r.height });
  }
  const ro = new ResizeObserver(ridimensiona);
  ro.observe(grafico);
  ridimensiona();

  function numero(v, cifre = 1) {
    return typeof v === "number" ? v.toFixed(cifre) : "—";
  }

  function aggiorna(t) {
    el.dataset.stato = "collegato";

    val("cpu").textContent = numero(t.cpu_percent);
    val("ram").textContent = numero(t.ram_percent);
    val("temp").textContent = numero(t.package_temp_c);
    val("libera").textContent =
      typeof t.ram_available_bytes === "number"
        ? (t.ram_available_bytes / 2 ** 30).toFixed(1)
        : "—";

    // L'accento caldo e' SEMANTICO, non decorativo (§11.6 regola 2): compare
    // solo oltre le soglie di §16.
    val("ram").dataset.critico = t.ram_percent > SOGLIA_RAM ? "1" : "0";
    val("temp").dataset.critico =
      typeof t.package_temp_c === "number" && t.package_temp_c > SOGLIA_TEMP ? "1" : "0";

    xs.push(xs.length ? xs[xs.length - 1] + 1 : 0);
    cpu.push(t.cpu_percent ?? null);
    ram.push(t.ram_percent ?? null);
    while (xs.length > CAMPIONI) { xs.shift(); cpu.shift(); ram.shift(); }
    plot.setData([xs, cpu, ram]);

    if (Array.isArray(t.top3) && t.top3.length) {
      proc.innerHTML = t.top3
        .map((p) => `<div class="pnl-tel__riga"><span>${p.name}</span><span>${p.cpu.toFixed(0)}%</span></div>`)
        .join("");
    }

    const ora = new Date(((t.ts ?? Date.now() / 1000) * 1000)).toLocaleTimeString("it-IT");
    piede.textContent = `${xs.length}/${CAMPIONI} campioni · ${ora} · 0x${(t.ts | 0).toString(16)}`;
  }

  function stato(s) {
    if (s === "vuoto") {
      el.dataset.stato = "vuoto";
      piede.textContent = "in attesa del core";
    }
  }

  return { el, aggiorna, stato, distruggi: () => { ro.disconnect(); plot.destroy(); } };
}
