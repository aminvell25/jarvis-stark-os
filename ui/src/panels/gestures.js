/* Pannello gesture — SPEC §14.
 *
 * Mostra i ventuno landmark della mano tracciata, la cadenza vera, il gesto in
 * corso e **il conteggio dell'isteresi**: quanti fotogrammi mancano perche' il
 * gesto conti.
 *
 * ── E' anche l'indicatore di telecamera accesa ─────────────────────────────
 * §12 lo dice per il rettangolo di ARGUS e vale identico qui: «non e'
 * decorazione, e' il controllo che Le permette di accorgersi di una cattura
 * inattesa». Finche' la telecamera e' accesa questo pannello lo dice, con
 * l'accento caldo — l'unico posto in cui lo usa, perche' e' l'unica cosa che
 * qui significhi qualcosa.
 *
 * ── Quello che NON arriva mai qui ──────────────────────────────────────────
 * Nessun fotogramma. Dal core escono solo landmark normalizzati, e il pannello
 * disegna quelli. Non c'e' un'anteprima video: se ci fosse, l'immagine della
 * stanza attraverserebbe il socket, verrebbe composta dal renderer — che dalla
 * Fase 6 ospita contenuto non fidato — e finirebbe in un buffer GPU condiviso
 * con una pagina web.
 *
 * ── L'isteresi si VEDE ─────────────────────────────────────────────────────
 * Cinque tacche che si riempiono. E' l'unico modo di capire, guardando, perche'
 * un gesto non e' scattato: non e' stato tenuto abbastanza.
 */

export const meta = { nome: "gestures", versione: "1" };

const NS = "http://www.w3.org/2000/svg";
const FRAME_ISTERESI = 5;   // §14

/** Le connessioni fra landmark, come le definisce MediaPipe. */
const OSSA = [
  [0, 1], [1, 2], [2, 3], [3, 4],             // pollice
  [0, 5], [5, 6], [6, 7], [7, 8],             // indice
  [0, 9], [9, 10], [10, 11], [11, 12],        // medio
  [0, 13], [13, 14], [14, 15], [15, 16],      // anulare
  [0, 17], [17, 18], [18, 19], [19, 20],      // mignolo
  [5, 9], [9, 13], [13, 17],                  // il palmo
];

export const css = `
.pnl-ges {
  --aug-tr: var(--s-3);
  --aug-bl: var(--s-3);
  /* §10.5 — la cornice se ne va, la sagoma resta.
   *
   * Dei sette pannelli misurati sul riferimento, ZERO hanno un tratto di
   * bordo sui quattro lati. Questo ne aveva uno: non una border: CSS, ma
   * l'anello di augmented-ui, che lo screenshot ha misurato a 4 px pieni di
   * --cy-900 su tutti e quattro i lati (otto pixel di dispositivo a scala 2).
   *
   * La parola che lo accende sta nel markup, accanto ai tagli a 45 gradi, e
   * di qui non si tocca. Si toglie l'INCHIOSTRO, non l'anello: transparent
   * qui e' assenza, non un colore scelto — la stessa lettura che l'audit da'
   * a rgba(0,0,0,0). L'anello continua a esistere e a non dipingere nulla.
   *
   * Non e' pulizia formale: l'anello dipinge SOPRA i figli, e con la testata
   * diventata chiara mangiava 4 px di banda su tre lati. Provato in pagina
   * prima di scrivere, e la banda incassata si vedeva. */
  --aug-border-bg: transparent;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  /* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA contro il
     pavimento, non una cornice. Con --bg-panel (L 31) il gradino sul
     pavimento (L 19) era di 12; --bg-raised e' il #1e2631 misurato identico
     a quattro quote sul corpo del calendario, e porta il gradino a +18. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE.
 *
 * Una riga di testo su fondo uguale al corpo non e' una testata: e' testo.
 * --fill-1 sta a L 66 sul corpo a L 37, cioe' +29, sopra i +19 che la regola
 * chiede, ed e' la polarita' del calendario (+30 L, testo chiaro) — quella
 * che il riferimento ha in tre versioni e che §10.5 sceglie.
 *
 * Il border-bottom hairline se ne va: la superficie separa da sola, e la
 * linea sarebbe una seconda separazione per la stessa giuntura. L'altezza
 * non si tocca. */
.pnl-ges__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
/* ⚠️ I testi qui dentro sono RITARATI, perche' il fondo sotto di loro e'
 * passato da L 31 a L 66 e il contrasto si e' rovesciato. Rapporti WCAG
 * misurati su --fill-1: --txt-ghost 1,82:1 (illeggibile), --txt-dim 2,73:1,
 * --icona 4,31:1, --cy-300 6,21:1, --icona-viva 7,11:1, --txt-primary 8,06:1.
 * Cambia solo cio' che sta sulla banda: il corpo del pannello ha un altro
 * fondo e i suoi testi non c'entrano. */
.pnl-ges__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  /* Era --cy-300, che sul fondo vecchio dava 10,2:1 e su questo scende a
     6,21: l'etichetta perderebbe il primato sulla riga proprio dove la
     banda la mette in evidenza. --txt-primary lo riprende a 8,06:1 — e' il
     nome del pannello, dev'essere l'inchiostro piu' fermo della testata. */
  color: var(--txt-primary);
}
.pnl-ges__id, .pnl-ges__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  /* Era --txt-dim: 2,73:1, sotto ogni soglia — su una banda chiara sarebbe
     stato il difetto piu' visibile del pannello. --icona da' 4,31:1, che e'
     la quota di un identificativo e dei tre glifi di controllo: si leggono
     e restano un gradino sotto l'etichetta. */
  color: var(--icona);
}
.pnl-ges__ctrl { letter-spacing: 0.16em; }

/* La riga della telecamera. L'accento caldo qui SIGNIFICA: sta riprendendo.
   La sua linea sotto RESTA: §10.5 toglie la CORNICE, non le giunture fra due
   parti dello stesso pannello. */
.pnl-ges__camera {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-ges__spia {
  width: var(--s-2);
  height: var(--s-2);
  background: var(--txt-ghost);
}
.pnl-ges[data-camera="accesa"] .pnl-ges__spia { background: var(--rust); }
.pnl-ges[data-camera="accesa"] .pnl-ges__stato-camera { color: var(--rust); }
/* Un margine automatico spingerebbe a destra, ma l'audit legge il valore
   CALCOLATO — 146,594 px — e giustamente lo rifiuta: non e' multiplo di 4.
   Lo spazio lo fa crescere l'elemento di mezzo, che e' anche piu' onesto. */
.pnl-ges__stato-camera { flex: 1; }

.pnl-ges__corpo { position: relative; display: grid; min-height: 0; overflow: hidden; }
.pnl-ges__svg { display: block; width: 100%; height: 100%; min-width: 0; min-height: 0; }
.pnl-ges__osso {
  fill: none;
  stroke: var(--cy-700);
  stroke-width: var(--line-base);
  vector-effect: non-scaling-stroke;
}
.pnl-ges__nodo { fill: var(--cy-300); }
.pnl-ges__nodo[data-punta="1"] { fill: var(--cy-100); }

.pnl-ges__vuoto {
  display: none;
  place-content: center;
  padding: var(--s-4);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-ges[data-stato="vuoto"] .pnl-ges__svg { display: none; }
.pnl-ges[data-stato="vuoto"] .pnl-ges__vuoto { display: grid; }

/* Anche la linea sopra il piede resta, e per la stessa ragione: divide due
   parti del pannello, non chiude un lato. */
.pnl-ges__piede {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-ges__gesto { color: var(--cy-300); letter-spacing: 0.10em; }
/* Le cinque tacche dell'isteresi: si vede QUANTO manca. */
.pnl-ges__isteresi { display: flex; gap: var(--s-1); }
.pnl-ges__tacca {
  width: var(--s-3);
  height: var(--line-bold);
  background: var(--cy-900);
}
.pnl-ges__tacca[data-piena="1"] { background: var(--cy-500); }
`;

function elSvg(nome, attributi = {}) {
  const e = document.createElementNS(NS, nome);
  for (const [k, v] of Object.entries(attributi)) e.setAttribute(k, v);
  return e;
}

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-ges";
  radice.dataset.augmentedUi = "tr-clip bl-clip border";
  radice.dataset.stato = "vuoto";
  radice.dataset.camera = "spenta";
  radice.innerHTML = `
    <div class="pnl-ges__testa">
      <span class="pnl-ges__etichetta">Gesture</span>
      <span class="pnl-ges__id">GES_K11 · ver ${meta.versione}</span>
      <span class="pnl-ges__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-ges__camera">
      <i class="pnl-ges__spia"></i>
      <span class="pnl-ges__stato-camera">telecamera spenta</span>
      <span class="pnl-ges__cadenza"></span>
    </div>
    <div class="pnl-ges__corpo">
      <div class="pnl-ges__vuoto">
        NESSUNA MANO IN CAMPO<br>nessun fotogramma lascia il core
      </div>
    </div>
    <div class="pnl-ges__piede">
      <span class="pnl-ges__gesto">—</span>
      <span class="pnl-ges__isteresi"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const corpo = radice.querySelector(".pnl-ges__corpo");
  const svg = elSvg("svg", {
    class: "pnl-ges__svg",
    preserveAspectRatio: "xMidYMid meet",
    "aria-hidden": "true",
  });
  corpo.insertBefore(svg, corpo.firstChild);

  const tacche = radice.querySelector(".pnl-ges__isteresi");
  for (let i = 0; i < FRAME_ISTERESI; i++) {
    const t = document.createElement("i");
    t.className = "pnl-ges__tacca";
    tacche.appendChild(t);
  }

  function disegnaMani(mani) {
    svg.replaceChildren();

    // Il viewBox si adatta alla MANO, non al fotogramma. Una mano occupa un
    // decimo dell'inquadratura: disegnarla su un riquadro 0..100 la lascerebbe
    // grande come un francobollo in mezzo al vuoto — e' quello che faceva la
    // prima versione, e si vede solo guardando lo screenshot.
    const tutti = mani.flatMap((m) => m.punti);
    const xs = tutti.map((p) => 1 - p[0]);
    const ys = tutti.map((p) => p[1]);
    const margine = 0.06;
    const x0 = Math.min(...xs) - margine;
    const y0 = Math.min(...ys) - margine;
    const w = Math.max(...xs) - Math.min(...xs) + margine * 2;
    const h = Math.max(...ys) - Math.min(...ys) + margine * 2;
    const lato = Math.max(w, h);
    svg.setAttribute("viewBox",
      `${x0.toFixed(4)} ${y0.toFixed(4)} ${lato.toFixed(4)} ${lato.toFixed(4)}`);
    // I raggi seguono la scala del riquadro: con un viewBox che cambia, un
    // raggio costante sarebbe un pallino diverso a ogni fotogramma.
    const r = lato * 0.018;

    for (const m of mani) {
      // I landmark sono normalizzati 0..1; il viewBox e' 0..100. La X si
      // SPECCHIA: la telecamera guarda l'utente, e senza specchio la mano
      // destra comparirebbe a sinistra.
      const px = (p) => [1 - p[0], p[1]];
      for (const [a, b] of OSSA) {
        const [x1, y1] = px(m.punti[a]);
        const [x2, y2] = px(m.punti[b]);
        svg.appendChild(elSvg("path", {
          class: "pnl-ges__osso",
          d: `M${x1.toFixed(4)},${y1.toFixed(4)}L${x2.toFixed(4)},${y2.toFixed(4)}`,
        }));
      }
      for (const [i, p] of m.punti.entries()) {
        const [x, y] = px(p);
        const punta = [4, 8, 12, 16, 20].includes(i);
        svg.appendChild(elSvg("circle", {
          class: "pnl-ges__nodo",
          "data-punta": punta ? "1" : "0",
          cx: x.toFixed(4), cy: y.toFixed(4), r: (punta ? r * 1.6 : r).toFixed(4),
        }));
      }
    }
  }

  return {
    radice,
    /** @param {{topic:string}} msg  `gesture.frame` */
    aggiorna(msg) {
      if (msg?.topic !== "gesture.frame") return;

      const accesa = Boolean(msg.camera_accesa);
      radice.dataset.camera = accesa ? "accesa" : "spenta";
      radice.querySelector(".pnl-ges__stato-camera").textContent =
        accesa ? "TELECAMERA ACCESA" : "telecamera spenta";
      radice.querySelector(".pnl-ges__cadenza").textContent =
        accesa
          ? `${(msg.fps ?? 0).toFixed(1)} fps · inferenza ${(msg.ms ?? 0).toFixed(1)} ms`
          : "";

      const mani = msg.mani ?? [];
      radice.dataset.stato = mani.length ? "pieno" : "vuoto";
      if (mani.length) disegnaMani(mani);

      radice.querySelector(".pnl-ges__gesto").textContent =
        msg.gesto ? `${msg.gesto}` : (mani.length ? "nessun gesto" : "—");
      for (const [i, t] of [...tacche.children].entries()) {
        t.dataset.piena = i < (msg.isteresi ?? 0) ? "1" : "0";
      }
    },
  };
}
