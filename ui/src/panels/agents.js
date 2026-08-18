/* Mesh agenti — SPEC §13, riferimento famiglia-a/04-analisi-armatura-grafo-nodi.
 *
 * Nel riferimento i nodi sono capsule orizzontali etichettate, collegate da
 * cavi sottili che corrono in orizzontale e verticale con raccordi. Qui i nodi
 * sono i tre tier, il router e i quattro subagent di §5.3, e lo stato lo manda
 * il core sul topic `agent.mesh`.
 *
 * ── Layout fisso, non a forze ──────────────────────────────────────────────
 * §11.5 concede «d3-force o layout fisso». Force sarebbe la scelta sbagliata
 * due volte: una simulazione a molle si assesta muovendosi, cioe' e'
 * animazione ambientale (invariante 25); e con otto nodi che non cambiano mai
 * topologia il risultato sarebbe una disposizione diversa a ogni apertura,
 * quando invece la memoria di dove sta un nodo e' meta' dell'utilita' del
 * pannello.
 *
 * ── Nodi nel DOM, cavi in SVG ──────────────────────────────────────────────
 * I nodi portano testo, quindi vivono nel DOM (invariante 20). I cavi sono
 * geometria pura e stanno in un SVG sotto di essi, ridisegnato dalle posizioni
 * MISURATE dei nodi: cosi' la griglia decide il layout e i cavi la seguono,
 * invece di avere due sistemi di coordinate che si contraddicono al primo
 * ridimensionamento.
 */

export const meta = { nome: "agents", versione: "1" };

const NS = "http://www.w3.org/2000/svg";

/** Il layout fisso, dichiarato in un posto solo.
 *
 * Quattro colonne, e T2 ha la sua: nella prima versione stava incolonnato con
 * T0 e T1, e il cavo T1 -> T2 diventava un moncone verticale di otto pixel fra
 * due riquadri adiacenti. Con T2 in colonna propria ogni arco corre in
 * orizzontale, che e' anche come corre il flusso: router, tier, spawn,
 * subagent. Chi non e' in tabella finisce nell'ultima colonna. */
const LAYOUT = { router: 0, t0: 1, t1: 1, t2: 2 };
const COLONNE = 4;

const SMUSSO = 8; // px del raccordo a 45 gradi, come i vertici dei pannelli

export const css = `
.pnl-agn {
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
.pnl-agn__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-agn__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-agn__id, .pnl-agn__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-agn__ctrl { letter-spacing: 0.16em; }

.pnl-agn__corpo {
  position: relative;
  display: grid;
  grid-template-columns: auto auto 1fr 1fr;
  align-items: center;
  gap: var(--s-3) var(--s-4);
  padding: var(--s-3);
  min-height: 0;
}
.pnl-agn__cavi { position: absolute; inset: 0; pointer-events: none; }
.pnl-agn__cavo {
  fill: none;
  stroke: var(--cy-900);
  stroke-width: var(--line-base);
}
.pnl-agn__cavo[data-vivo="1"] { stroke: var(--cy-500); }

.pnl-agn__colonna { display: grid; gap: var(--s-2); align-content: center; }

.pnl-agn__nodo {
  position: relative;
  display: grid;
  gap: var(--s-1);
  padding: var(--s-2);
  background: var(--bg-raised);
  border: var(--line-hair) solid var(--cy-900);
  border-left: var(--line-bold) solid var(--cy-700);
  border-radius: var(--radius);
}
.pnl-agn__nodo[data-attivo="1"] { border-left-color: var(--cy-300); }
.pnl-agn__nodo[data-scollegato="1"] {
  background: transparent;
  border-left-color: var(--txt-ghost);
}
.pnl-agn__nome {
  font-size: var(--t-label);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-agn__nodo[data-scollegato="1"] .pnl-agn__nome { color: var(--txt-dim); }
.pnl-agn__stato {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--cy-300);
}
.pnl-agn__nodo[data-scollegato="1"] .pnl-agn__stato { color: var(--txt-ghost); }
.pnl-agn__dettaglio {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}

.pnl-agn__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-agn__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-agn[data-stato="vuoto"] .pnl-agn__corpo { display: none; }
.pnl-agn[data-stato="vuoto"] .pnl-agn__vuoto { display: block; }
`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-agn";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-agn__testa">
      <span class="pnl-agn__etichetta">Mesh agenti</span>
      <span class="pnl-agn__id">MSH_D04 · ver ${meta.versione}</span>
      <span class="pnl-agn__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-agn__corpo"></div>
    <div class="pnl-agn__vuoto">NESSUNA SORGENTE COLLEGATA</div>
    <div class="pnl-agn__piede">
      <span class="pnl-agn__conteggio"></span>
      <span class="pnl-agn__ora">--:--:--</span>
    </div>
  `;
  ospite.appendChild(radice);

  const corpo = radice.querySelector(".pnl-agn__corpo");
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "pnl-agn__cavi");
  corpo.appendChild(svg);

  const colonne = Array.from({ length: COLONNE }, () => {
    const c = document.createElement("div");
    c.className = "pnl-agn__colonna";
    corpo.appendChild(c);
    return c;
  });

  const elementi = new Map(); // id -> elemento del nodo
  let archi = [];
  let vivi = new Set();

  const osservatore = new ResizeObserver(() => cavi());
  osservatore.observe(corpo);

  function nodo(n) {
    const el = document.createElement("div");
    el.className = "pnl-agn__nodo";
    el.dataset.attivo = n.attivo ? "1" : "0";
    el.dataset.scollegato = n.stato === "non collegato" ? "1" : "0";
    el.innerHTML =
      `<span class="pnl-agn__nome">${n.id}</span>` +
      `<span class="pnl-agn__stato">${n.stato}</span>` +
      (n.dettaglio ? `<span class="pnl-agn__dettaglio">${n.dettaglio}</span>` : "");
    return el;
  }

  /** Un cavo ortogonale con due raccordi a 45 gradi. */
  function orizzontale(a, b) {
    const mx = Math.round((a.x + b.x) / 2);
    if (Math.abs(b.y - a.y) < SMUSSO * 2) return `M${a.x},${a.y}L${b.x},${b.y}`;
    const s = Math.sign(b.y - a.y);
    return (
      `M${a.x},${a.y}` +
      `L${mx - SMUSSO},${a.y}` +
      `L${mx},${a.y + s * SMUSSO}` +
      `L${mx},${b.y - s * SMUSSO}` +
      `L${mx + SMUSSO},${b.y}` +
      `L${b.x},${b.y}`
    );
  }

  function cavi() {
    const base = corpo.getBoundingClientRect();
    svg.setAttribute("viewBox", `0 0 ${Math.round(base.width)} ${Math.round(base.height)}`);
    svg.replaceChildren();
    for (const [da, a] of archi) {
      const ea = elementi.get(da);
      const eb = elementi.get(a);
      if (!ea || !eb) continue;
      const ra = ea.getBoundingClientRect();
      const rb = eb.getBoundingClientRect();
      const p = document.createElementNS(NS, "path");
      p.setAttribute("class", "pnl-agn__cavo");
      p.dataset.vivo = vivi.has(da) && vivi.has(a) ? "1" : "0";

      p.setAttribute(
        "d",
        orizzontale(
          { x: Math.round(ra.right - base.left), y: Math.round(ra.top + ra.height / 2 - base.top) },
          { x: Math.round(rb.left - base.left), y: Math.round(rb.top + rb.height / 2 - base.top) }
        )
      );
      svg.appendChild(p);
    }
  }

  function aggiorna(msg) {
    if (msg?.topic !== "agent.mesh") return;
    radice.dataset.stato = "pieno";

    elementi.clear();
    for (const c of colonne) c.replaceChildren();
    vivi = new Set(msg.nodi.filter((n) => n.stato !== "non collegato").map((n) => n.id));

    for (const n of msg.nodi) {
      const el = nodo(n);
      elementi.set(n.id, el);
      colonne[LAYOUT[n.id] ?? COLONNE - 1].appendChild(el);
    }
    archi = msg.archi;
    cavi();

    const collegati = vivi.size;
    radice.querySelector(".pnl-agn__conteggio").textContent =
      `${msg.nodi.length} nodi · ${collegati} collegati · ${msg.archi.length} archi`;
    if (typeof msg.ts === "number") {
      radice.querySelector(".pnl-agn__ora").textContent =
        new Date(msg.ts * 1000).toLocaleTimeString("it-IT", { hour12: false });
    }
  }

  return { radice, aggiorna, smonta: () => osservatore.disconnect() };
}
