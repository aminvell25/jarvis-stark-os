/* Anelli concentrici — SPEC §10.3, §10.4, riferimento famiglia-a/12.
 *
 * Quattro `ReactorRing` composti, resi in SVG e mossi da anime.js v4.
 *
 * ── Perche' girano solo quando succede qualcosa ────────────────────────────
 * §10.3 assegna agli anelli 46/74/120/240 s per giro, e tre righe piu' sotto
 * scrive: «Nessuna animazione senza causa. L'animazione decorativa continua e'
 * il marchio del finto». L'invariante 25 lo rende regola: zero animazione
 * ambientale. Un anello che gira sempre E' animazione ambientale.
 *
 * La contraddizione si scioglie dando al movimento una causa: gli anelli sono
 * l'indicatore di stato dell'agente. Girano mentre qualcosa accade davvero, e
 * si fermano quando il sistema e' inerte. Se gira, sta lavorando — il
 * movimento diventa un dato che si legge da lontano.
 *
 * ── I periodi di §10.3 non sono utilizzabili come sono ─────────────────────
 * «46s / 74s / 120s / 240s per giro. Mai multiple tra loro» — ma 240 = 2 x 120.
 * I due anelli si riallineerebbero ogni 240 s esatti, ed e' proprio il ciclo
 * visibile che la regola vuole evitare. Tengo 46, 74, 120 e porto l'ultimo a
 * 233 s: nessun rapporto intero con gli altri tre.
 *
 * ── Perche' SVG e non three.js ─────────────────────────────────────────────
 * §22 lo prescrive, e ha ragione: sono forme piatte che devono restare nitide
 * a ogni scala, e non valgono un contesto WebGL. La geometria resta pero'
 * parametrica (§11.10) e passa il gate come qualunque componente 3D.
 */

import { animate } from "../../vendor/anime.esm.min.js";
import { ReactorRing } from "../three/components/reactor-ring.js";
import { qualityGate } from "../three/quality-gate.js";
import { versoPath } from "../three/svg.js";

export const meta = { nome: "rings", versione: "1" };

/** La composizione: raggio, varco, periodo, verso, centro sfalsato.
 *
 * E' una tabella dichiarata, non quattro chiamate sparse: cosi' si legge in
 * una volta sola che i varchi sono tutti diversi (§11.6 regola 6) e che i
 * periodi non sono multipli (§10.3).
 */
const ANELLI = [
  { outerR: 120, thickness:  8, tickCount: 90, tickMajorEvery: 10, tickLen: 3,   tickMajorLen: 6, gapStart: 0.62, gapSweep: 0.31, periodSec: 46,  verso: +1, cx:  0, cy:  0 },
  { outerR: 106, thickness:  5, tickCount: 60, tickMajorEvery:  5, tickLen: 2,   tickMajorLen: 4, gapStart: 2.35, gapSweep: 0.44, periodSec: 74,  verso: -1, cx:  4, cy: -3 },
  { outerR:  94, thickness: 12, tickCount: 72, tickMajorEvery:  6, tickLen: 4,   tickMajorLen: 9, gapStart: 3.95, gapSweep: 0.22, periodSec: 120, verso: +1, cx: -3, cy:  5 },
  { outerR:  74, thickness:  4, tickCount: 36, tickMajorEvery:  3, tickLen: 1.5, tickMajorLen: 3, gapStart: 5.30, gapSweep: 0.38, periodSec: 233, verso: -1, cx:  2, cy:  4 },
  { outerR:  58, thickness:  3, tickCount: 120, tickMajorEvery: 10, tickLen: 1, tickMajorLen: 3, gapStart: 1.15, gapSweep: 0.16, fisso: true, cx: 0, cy: 0 },
];

/* Le fasce sono ADIACENTI, con corridoi di pochi millimetri fra l'una e
 * l'altra. La prima versione le aveva distanti, e lo screenshot mostrava
 * quattro archi sottili che galleggiavano nel vuoto: §11.8 CONTENUTO, «la
 * densita' regge il confronto con l'immagine di riferimento?» — non reggeva.
 * Nel riferimento gli anelli formano un disco, non quattro cerchi.
 *
 * L'ultimo e' FISSO: e' la scala di riferimento contro cui si legge il
 * movimento degli altri quattro, come la ghiera incisa di uno strumento. Non
 * avendo animazione non ha periodo, e non conta per la regola dei rapporti
 * non interi di §10.3. */

const NS = "http://www.w3.org/2000/svg";

export const css = `
/* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
   Il fondo sale da --bg-panel (L 31) a --bg-raised (L 37): e' il valore
   misurato sul corpo del calendario del riferimento, #1e2631 identico a
   quattro quote diverse, opaco e piatto. Contro il pavimento a L 19 fa +18,
   ed e' quel salto — non un filo di bordo — a dire dove comincia il pannello.
   Dei sette pannelli misurati, zero hanno un tratto sui quattro lati. */
.pnl-anelli {
  /* §10.5 — l'anello di augmented-ui E' la cornice sui quattro lati.
     Misurato sullo scatto del contenitore radice: 4 px pieni di --cy-900 su
     TUTTI E QUATTRO i lati, cioe' esattamente il tratto che zero pannelli su
     sette hanno nel riferimento. E dipinge SOPRA i figli: con la testata
     diventata chiara ne mangiava 4 px su tre lati.
     Si toglie l'INCHIOSTRO, non l'anello — la parola che lo accende sta nel
     markup, accanto ai tagli a 45 gradi, e di li' non si tocca. «transparent»
     qui e' assenza, non un colore scelto: la stessa lettura che l'audit da' a
     rgba(0,0,0,0). Toglierlo del tutto NON spegne il tratto: augmented-ui
     ripiega su currentColor e lo riaccende a --txt-primary. */
  --aug-border-bg: transparent;
  --aug-tr: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE. Banda piena a --fill-1
   (L 66): +29 L sul corpo, oltre il gradino minimo di +19 misurato, e
   praticamente la testata del calendario, misurata a L 65,7. Una riga di
   testo su fondo uguale al corpo non e' una testata, e' testo.

   ⚠️ L'altezza NON si tocca in questo passaggio, ma va detta: misurata sullo
   scatto della galleria, la banda e' alta 27 px su un pannello di 480, cioe'
   il 5,6 % — appena SOTTO la forbice 6-9 % misurata sul riferimento. Mancano
   circa 2 px per riga di padding. Resta com'e' finche' non lo si decide per
   tutti i pannelli insieme: una testata piu' alta qui e non altrove sarebbe
   peggio di una testata bassa dappertutto.

   Il border-bottom se ne va. Serviva a separare due fondi identici; adesso a
   separare c'e' il gradino di luminanza, e il filo resterebbe solo come
   ultimo pezzo della cornice che §10.5 toglie. */
.pnl-anelli__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
/* ⚠️ I tre testi della testa vanno RITARATI: sotto non c'e' piu' L 31 ma
   L 66, e i colori scelti contro il corpo li' non valgono piu'.

   L'etichetta e' il nome del pannello, la prima cosa che si legge da lontano:
   --cy-300 reggerebbe (6,21:1) ma --txt-primary da' 8,06:1, ed e' il massimo
   disponibile su questa superficie. Su un fondo chiaro il titolo prende tutto
   il contrasto che c'e'. */
.pnl-anelli__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
/* Identificativo, versione e glifi dei controlli: --txt-dim su --fill-1
   misura 2,73:1, cioe' sotto ogni soglia — era leggibile contro il corpo, non
   contro la superficie. --icona da' 4,31:1 ed e' il ruolo esatto: si legge
   senza pretendere il peso del titolo. */
.pnl-anelli__id, .pnl-anelli__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
.pnl-anelli__ctrl { letter-spacing: 0.16em; }

.pnl-anelli__corpo {
  /* Il ritaglio non e' prudenza: la prima versione lasciava l'SVG con
     overflow visibile dentro una griglia centrata, e gli anelli uscivano dal
     pannello passando sopra il piede e oltre il bordo inferiore. Si vede
     nello screenshot, non nel codice. */
  position: relative;
  overflow: hidden;
  min-height: 0;
  display: grid;
  padding: var(--s-3);
}
/* Un elemento sostituito con rapporto d'aspetto intrinseco e quattro inset
   assoluti e' sovravincolato, e il browser scioglie il conflitto a modo suo:
   nella prima versione il disco veniva scalato sulla larghezza e usciva sopra
   e sotto. Un unico elemento di griglia che si stira nell'area gia' spaziata
   non lascia margini di interpretazione. */
.pnl-anelli__svg {
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
}
/* Tre pesi soli — §11.8 GEOMETRIA. Il contorno e' base, i tick sono hairline. */
.pnl-anelli__linea {
  fill: none;
  stroke: var(--cy-500);
  stroke-width: var(--line-base);
  vector-effect: non-scaling-stroke;
}
.pnl-anelli__costruzione {
  fill: none;
  stroke: var(--cy-700);
  stroke-width: var(--line-hair);
  vector-effect: non-scaling-stroke;
}
/* L'anello piu' esterno porta l'accento caldo SOLO quando lo stato lo
   giustifica: §11.6 regola 2, il caldo significa, non decora. */
.pnl-anelli[data-livello="warn"] .pnl-anelli__g:first-child .pnl-anelli__linea { stroke: var(--amber); }
.pnl-anelli[data-livello="critical"] .pnl-anelli__g:first-child .pnl-anelli__linea { stroke: var(--rust); }

/* La banda orizzontale che attraversa il disco e' del riferimento: li' porta
   il marchio, qui porta lo stato. Risolve anche la leggibilita' — il testo
   sopra i tick non si leggeva — mascherando gli anelli dietro un fondo pieno
   invece di sperare che non si sovrappongano.

   Il testo vive nel DOM, mai rasterizzato in WebGL o in SVG: invariante 20.
   Cosi' resta selezionabile e prende i token. */
.pnl-anelli__banda {
  position: absolute;
  left: 0; right: 0; top: 50%;
  transform: translateY(-50%);
  display: grid;
  gap: var(--s-1);
  padding: var(--s-2) var(--s-3);
  background: var(--bg-panel);
  border-top: var(--line-hair) solid var(--cy-700);
  border-bottom: var(--line-hair) solid var(--cy-700);
  pointer-events: none;
}
.pnl-anelli__riga {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s-2);
}
.pnl-anelli__stato {
  font-size: var(--t-label);
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-anelli__quanto {
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--cy-300);
}
.pnl-anelli__motivo {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-dim);
}
.pnl-anelli__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
`;

function elSvg(nome, attributi = {}) {
  const e = document.createElementNS(NS, nome);
  for (const [k, v] of Object.entries(attributi)) e.setAttribute(k, v);
  return e;
}

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-anelli";
  radice.dataset.augmentedUi = "tr-clip bl-clip border";
  radice.dataset.livello = "nominal";
  radice.innerHTML = `
    <div class="pnl-anelli__testa">
      <span class="pnl-anelli__etichetta">Stato agente</span>
      <span class="pnl-anelli__id">RNG_A01 · ver ${meta.versione}</span>
      <span class="pnl-anelli__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-anelli__corpo">
      <div class="pnl-anelli__banda">
        <div class="pnl-anelli__riga">
          <span class="pnl-anelli__stato">non collegato</span>
          <span class="pnl-anelli__quanto">--:--:--</span>
        </div>
        <div class="pnl-anelli__motivo"></div>
      </div>
    </div>
    <div class="pnl-anelli__piede">
      <span class="pnl-anelli__periodi"></span>
      <span class="pnl-anelli__conteggio"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const corpo = radice.querySelector(".pnl-anelli__corpo");
  const svg = elSvg("svg", { class: "pnl-anelli__svg", "aria-hidden": "true" });
  corpo.insertBefore(svg, corpo.firstChild);

  // Costruzione dei quattro anelli, ognuno col proprio gate.
  let raggioMax = 0;
  let vertici = 0;
  const animazioni = [];

  for (const a of ANELLI) {
    const componente = new ReactorRing(a);
    const geometria = componente.build();
    // Il gate PRIMA del render — invariante 22. Solleva, e la galleria mostra
    // l'errore invece di un anello sbagliato che sembra giusto.
    qualityGate(componente, geometria, ["linea", "costruzione"]);
    vertici += geometria.getAttribute("position").count;

    const posto = elSvg("g", { transform: `translate(${a.cx} ${a.cy})` });
    const ruota = elSvg("g", { class: "pnl-anelli__g" });
    ruota.style.transformOrigin = "0 0";

    for (const p of [...versoPath(componente.constructionLines()), ...versoPath(geometria)]) {
      ruota.appendChild(
        elSvg("path", {
          d: p.d,
          class: p.ruolo === "linea" ? "pnl-anelli__linea" : "pnl-anelli__costruzione",
        })
      );
    }
    posto.appendChild(ruota);
    svg.appendChild(posto);

    raggioMax = Math.max(raggioMax, a.outerR + Math.hypot(a.cx, a.cy));

    if (a.fisso) continue;

    // anime.js v4: `animate` restituisce l'animazione, e la si governa con
    // pause()/play(). Creata gia' in pausa: nessun anello gira finche' non
    // c'e' una causa (invariante 25).
    const an = animate(ruota, {
      rotate: 360 * a.verso,
      duration: a.periodSec * 1000,
      loop: true,
      ease: "linear",
      autoplay: false,
    });
    animazioni.push(an);
  }

  // viewBox calcolata dalla composizione, non scritta a mano: un numero
  // letterale qui smetterebbe di corrispondere al primo cambio di raggio, e
  // gli anelli si ritroverebbero tagliati senza che nulla lo segnali.
  const lato = Math.ceil(raggioMax + 2) * 2;
  svg.setAttribute("viewBox", `${-lato / 2} ${-lato / 2} ${lato} ${lato}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");

  radice.querySelector(".pnl-anelli__periodi").textContent =
    ANELLI.filter((a) => !a.fisso).map((a) => `${a.periodSec}s`).join(" · ") + " · ghiera fissa";
  radice.querySelector(".pnl-anelli__conteggio").textContent =
    `${ANELLI.length} anelli · ${vertici} vertici`;

  const elStato = radice.querySelector(".pnl-anelli__stato");
  const elQuanto = radice.querySelector(".pnl-anelli__quanto");
  const elMotivo = radice.querySelector(".pnl-anelli__motivo");

  let inMoto = false;

  function muovi(deve) {
    if (deve === inMoto) return;
    inMoto = deve;
    for (const an of animazioni) (deve ? an.play() : an.pause());
  }

  /** @param {{attivo?: boolean, stato?: string, livello?: string,
   *           motivo?: string, da_s?: number}} s */
  function aggiorna(s) {
    if (s.livello) radice.dataset.livello = s.livello;
    if (s.stato) elStato.textContent = s.stato;
    if (typeof s.da_s === "number") {
      const t = Math.max(0, Math.floor(s.da_s));
      elQuanto.textContent =
        `${String(Math.floor(t / 3600)).padStart(2, "0")}:` +
        `${String(Math.floor(t / 60) % 60).padStart(2, "0")}:` +
        `${String(t % 60).padStart(2, "0")}`;
    }
    elMotivo.textContent = s.motivo ?? "";
    muovi(Boolean(s.attivo));
  }

  return { radice, aggiorna, get inMoto() { return inMoto; } };
}
