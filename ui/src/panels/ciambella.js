/* Ciambella di ripartizione — riferimento famiglia-a/04 e 05.
 *
 * ## Che cosa porta il riferimento
 *
 * In «04» la ciambella «META DATA 18.07» sta a x 258..330, y 118..190: 72 px di
 * lato. In «05» quella dei mercati sta a x 545..620. Misurate su entrambe:
 *
 * 1. **E' un ANELLO, non un disco.** Il foro vale circa il 55 % del raggio, e
 *    ci sta dentro il totale. Un disco pieno non ha un posto in cui dire
 *    quanto fa la somma.
 *
 * 2. **I settori sono separati da un VARCO**, non da un bordo. Nel riferimento
 *    fra due settori c'e' il fondo, un paio di gradi. Un tratto di contorno
 *    su un settore da 8 gradi lo cancella.
 *
 * 3. **C'e' un varco anche nell'anello**, in alto: la ciambella non si chiude.
 *    E' la stessa asimmetria dichiarata di §11.6 regola 6 — un parametro con
 *    un nome, non «Math.random()».
 *
 * 4. **La legenda e' a fianco e porta il valore**, non solo il nome: una
 *    legenda senza numeri costringe a stimare l'angolo a occhio, che e' la
 *    cosa che una ciambella fa peggio di una barra. Il numero la salva.
 *
 * 5. **Un solo settore e' caldo**, ed e' quello che significa qualcosa. Gli
 *    altri stanno nella famiglia fredda, distinti per luminanza e non per
 *    tinta: cinque tinte sarebbero cinque significati (§11.6 regola 2).
 *
 * ## Il generatore e' d3-shape, come per i quadranti
 *
 * «arc()» e' gia' vendorizzato e lo usa «panels/dials.js». Scrivere a mano il
 * path di un settore anulare vorrebbe dire riscrivere quel codice con un bug
 * in piu' sui grandi archi.
 */

import { animate } from "../../vendor/anime.esm.min.js";

import arc from "../../vendor/d3-shape/arc.js";

export const meta = { nome: "ciambella", versione: "1" };

const TAU = Math.PI * 2;

/** La geometria, in un posto solo. Raggi in unita' del viewBox. */
const R_ESTERNO = 50;
const R_INTERNO = 28;          // 56 % — il foro del riferimento
const VARCO_SETTORE = 0.018;   // rad fra due settori
const VARCO_ANELLO = 0.22;     // rad, l'asimmetria dichiarata
const VARCO_INIZIO = -Math.PI / 2 + VARCO_ANELLO / 2;

/** La scala dei riempimenti: CINQUE gradini di luminanza nella stessa famiglia
 *  fredda, e nessuno di piu'.
 *
 *  ⚠️ Il sesto era --cy-900, e non si vedeva. Misurato sul componente vivo:
 *  1,22:1 contro il corpo del pannello a --bg-raised. Non e' un'opinione — e'
 *  la misura che il progetto ha gia' scritto due volte: tokens.css registra
 *  --cy-900 a 1,30:1 sul corpo, e app.css spiega che e' esattamente per questo
 *  che il marcatore del pannello col fuoco usa --cy-700 e non --cy-900. Un
 *  token che non puo' portare un marcatore da 4 px non puo' portare un settore.
 *
 *  Il danno era doppio, e il secondo era peggio del primo: invisibile era anche
 *  il CAMPIONE della sua riga di legenda, e il punto 4 dell'intestazione dice
 *  che il campione «e' la sola cosa che lega la riga al settore». Una riga che
 *  dichiara 0,3 % senza poter dire QUALE settore e' non e' una legenda.
 *
 *  ⚠️ E NON BASTAVA TOGLIERE IL SESTO. Rimisurati tutti i token contro il
 *  corpo a --bg-raised, non contro --bg-panel: il 3,04:1 che tokens.css
 *  attribuisce a --cy-700 e' misurato sul fondo VECCHIO (L 31), e §10.5 ha
 *  portato il corpo a L 37. Su questo fondo --cy-700 vale 2,82:1 e --fill-3
 *  2,74:1 — entrambi sotto la soglia, entrambi nella rampa che avevo appena
 *  scritto. Un fondo piu' chiaro toglie contrasto invece di darlo, ed e' la
 *  stessa correzione che tokens.css racconta di aver dovuto fare sui testi.
 *
 *  I token che sul corpo a L 37 stanno sopra 3:1, misurati sul componente vivo:
 *
 *    --cy-100   12,43:1      --icona    6,65:1
 *    --cy-300    9,59:1      --txt-dim  4,93:1
 *    --cy-500    8,30:1
 *
 *  La rampa e' quella, e scende in modo monotono. Gli ultimi due non sono
 *  ciano ma grigi FREDDI, e non e' un ripiego: la rampa va dal ciano saturo al
 *  grigio via via piu' spento man mano che la fetta si assottiglia, e nessuno
 *  dei due e' un accento caldo, quindi nessun settore finge di significare
 *  attenzione. Sono anche i due token che il progetto destina a un SEGNO su un
 *  pannello — il riempimento di un'icona e il testo secondario — che e'
 *  esattamente cio' che un settore e'. */
const SCALA = ["--cy-100", "--cy-300", "--cy-500", "--icona", "--txt-dim"];

export const css = `
.pnl-cia {
  --aug-tl: var(--s-3);
  --aug-border-bg: transparent;
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
.pnl-cia__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
.pnl-cia__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-cia__id, .pnl-cia__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  white-space: nowrap;
  color: var(--icona);
}
.pnl-cia__ctrl { letter-spacing: 0.16em; }

/* L'anello a sinistra, la legenda a destra: «auto 1fr», cosi' l'anello prende
   l'altezza e la legenda tutto il resto della larghezza. Sopra e sotto no —
   una ciambella con la legenda sotto costringe l'occhio a saltare due volte. */
.pnl-cia__corpo {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: var(--s-4);
  padding: var(--s-3);
  min-height: 0;
}
.pnl-cia__anello { position: relative; display: grid; min-height: 0; height: 100%; }
.pnl-cia__svg { display: block; width: 100%; height: 100%; min-width: 0; min-height: 0; }
.pnl-cia__settore { stroke: none; }
/* Il settore sotto il puntatore non cambia colore — cambierebbe significato.
   Si stacca dal fondo di mezzo grado, uscendo appena dal centro. */
.pnl-cia__settore { transition: transform 120ms linear; transform-origin: 50% 50%; }
.pnl-cia__settore:hover { transform: scale(1.03); }

/* Il totale nel foro. DOM sopra l'SVG: invariante 20, il testo non si
   rasterizza. */
.pnl-cia__centro {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  pointer-events: none;
}
.pnl-cia__totale {
  font-family: var(--font-mono);
  font-size: var(--t-title);
  line-height: 1;
  color: var(--cy-100);
  font-variant-numeric: tabular-nums;
}
/* Solo l'unita', non «kB in totale»: il foro e' largo il 56 % del raggio e tre
   parole ci vanno a capo. Che sia un totale lo dice il posto in cui sta — al
   centro dell'anello — e lo ripete il piede. */
.pnl-cia__unita {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}

.pnl-cia__legenda {
  display: grid;
  align-content: center;
  gap: var(--s-1);
  min-width: 0;
}
.pnl-cia__voce {
  display: grid;
  grid-template-columns: var(--s-2) 1fr auto auto;
  align-items: baseline;
  gap: var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-dim);
}
.pnl-cia__voce:hover { color: var(--txt-primary); }
/* Il campione: un quadrato pieno, raggio zero. E' la sola cosa che lega la
   riga al settore, quindi e' pieno e non un contorno. */
.pnl-cia__campione {
  width: var(--s-2);
  height: var(--s-2);
  border-radius: var(--radius);
}
.pnl-cia__nome { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.pnl-cia__val {
  text-align: right;
  font-variant-numeric: tabular-nums;
  color: var(--txt-primary);
}
/* ⚠️ nowrap e una larghezza minima: senza, «71,7 %» andava a capo e la
   percentuale finiva su due righe alte 8,5 px — una legenda in cui il numero si
   spezza e' peggio di una legenda senza numero. 6ch e' la larghezza del caso
   piu' lungo («100,0 %») nel mono a --t-micro. */
.pnl-cia__quota {
  min-width: 6ch;
  text-align: right;
  white-space: nowrap;
  font-size: var(--t-micro);
  color: var(--txt-ghost);
  font-variant-numeric: tabular-nums;
}
.pnl-cia__val { white-space: nowrap; }

.pnl-cia__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  white-space: nowrap;
  overflow: hidden;
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-cia__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-cia[data-stato="vuoto"] .pnl-cia__corpo { display: none; }
.pnl-cia[data-stato="vuoto"] .pnl-cia__vuoto { display: block; }
`;

const NS = "http://www.w3.org/2000/svg";
const elSvg = (nome, attributi = {}) => {
  const e = document.createElementNS(NS, nome);
  for (const [k, v] of Object.entries(attributi)) e.setAttribute(k, v);
  return e;
};

const HTML = `
<section class="pnl-cia" data-stato="vuoto" data-augmented-ui="tl-clip br-clip border">
  <header class="pnl-cia__testa">
    <span class="pnl-cia__etichetta">Ripartizione sorgenti</span>
    <span class="pnl-cia__id">CIA_R05 &middot; ver ${meta.versione}</span>
    <span class="pnl-cia__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-cia__corpo">
    <div class="pnl-cia__anello">
      <div class="pnl-cia__centro">
        <span class="pnl-cia__totale">&mdash;</span>
        <span class="pnl-cia__unita">kB</span>
      </div>
    </div>
    <div class="pnl-cia__legenda"></div>
  </div>
  <div class="pnl-cia__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-cia__piede">
    <span data-conteggio></span>
    <span data-varco></span>
  </footer>
</section>
`;

const ramoDi = (p) => (String(p).includes("/") ? String(p).split("/")[0] : "radice");
const dec = (n, cifre) => Number(n).toLocaleString("it-IT",
  { minimumFractionDigits: cifre, maximumFractionDigits: cifre });
const kB = (b) => dec(b / 1024, b < 1024 * 100 ? 1 : 0);

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-cia");
  const ospiteAnello = el.querySelector(".pnl-cia__anello");
  const legenda = el.querySelector(".pnl-cia__legenda");
  const generatore = arc();

  let apertura = null;

  const svg = elSvg("svg", {
    class: "pnl-cia__svg",
    viewBox: `${-R_ESTERNO - 2} ${-R_ESTERNO - 2} ${(R_ESTERNO + 2) * 2} ${(R_ESTERNO + 2) * 2}`,
    preserveAspectRatio: "xMidYMid meet",
    "aria-hidden": "true",
  });
  ospiteAnello.insertBefore(svg, ospiteAnello.firstChild);

  function aggiorna(msg) {
    const voci = Array.isArray(msg?.files) ? msg.files : null;
    if (!voci || !voci.length) return;
    el.dataset.stato = "pieno";

    // Ripartizione per ramo di primo livello. E' un conto sui dati veri, non
    // una categoria inventata: il ramo e' il primo segmento del percorso.
    const per = new Map();
    for (const v of voci) {
      const k = ramoDi(v.path);
      per.set(k, (per.get(k) ?? 0) + (Number(v.bytes) || 0));
    }
    const totale = [...per.values()].reduce((s, n) => s + n, 0);
    // I primi cinque, e il resto in una voce sola che DICE di essere il resto.
    // Sei settori su una ciambella da 100 px sono il massimo leggibile.
    const ordinate = [...per.entries()].sort((a, b) => b[1] - a[1]);
    // Quattro rami piu' il resto: CINQUE fette, quante sono le tinte che si
    // vedono. Prima erano cinque piu' il resto, e la sesta prendeva il gradino
    // che non c'e' piu'. Il numero di fette lo decide la scala, non il caso.
    const VISIBILI = SCALA.length - 1;
    const primi = ordinate.slice(0, VISIBILI);
    const restoVal = ordinate.slice(VISIBILI).reduce((s, [, n]) => s + n, 0);
    const fette = restoVal > 0
      ? [...primi, [`altri ${ordinate.length - VISIBILI} rami`, restoVal]]
      : primi;

    svg.replaceChildren();
    legenda.replaceChildren();

    const arcoUtile = TAU - VARCO_ANELLO;
    /* I settori si APRONO in senso orario dal varco, e la causa e' che sono
     * arrivati dati nuovi (invariante 25): un anello che compare fatto non dice
     * di essersi ricalcolato, e questo pannello si ricalcola a ogni
     * source.tree. Si anima UN numero — la frazione di apertura — e i cinque
     * path si rigenerano da lui: e' la stessa forma con cui i quadranti
     * ridisegnano il proprio arco a ogni campione, e tiene i 4 ms di §10.4
     * perche' non tocca il layout.
     * L'animazione si annulla se ne parte un'altra: due aperture sovrapposte
     * scriverebbero lo stesso attributo con due valori. */
    const geometrie = [];
    let a0 = VARCO_INIZIO;
    for (const [i, [nome, valore]] of fette.entries()) {
      const ampiezza = (valore / totale) * arcoUtile;
      const token = SCALA[Math.min(i, SCALA.length - 1)];
      const p = elSvg("path", { class: "pnl-cia__settore", fill: `var(${token})` });
      svg.appendChild(p);
      geometrie.push({ p, da: a0, ampiezza });
      a0 += ampiezza;

      const riga = document.createElement("div");
      riga.className = "pnl-cia__voce";
      const campione = document.createElement("span");
      campione.className = "pnl-cia__campione";
      campione.style.background = `var(${token})`;
      const n = document.createElement("span");
      n.className = "pnl-cia__nome";
      // textContent: il nome del ramo viene dal disco (invariante 5).
      n.textContent = nome;
      const val = document.createElement("span");
      val.className = "pnl-cia__val";
      val.textContent = `${kB(valore)} kB`;
      const quota = document.createElement("span");
      quota.className = "pnl-cia__quota";
      quota.textContent = `${dec(valore / totale * 100, 1)} %`;
      riga.append(campione, n, val, quota);
      legenda.appendChild(riga);
    }

    const disegnaFino = (t) => {
      for (const g of geometrie) {
        // Il varco fra due settori si toglie dalla FINE, non si aggiunge:
        // aggiungendolo la somma degli angoli non farebbe piu' il giro.
        const fine = g.da + g.ampiezza * t - VARCO_SETTORE;
        g.p.setAttribute("d", generatore({
          innerRadius: R_INTERNO,
          outerRadius: R_ESTERNO,
          startAngle: g.da,
          endAngle: Math.max(g.da, fine),
        }) ?? "");
      }
    };
    apertura?.pause();
    const stato = { t: 0 };
    disegnaFino(0);
    apertura = animate(stato, {
      t: 1,
      duration: 420,
      ease: "out(3)",
      onUpdate: () => disegnaFino(stato.t),
      onComplete: () => { disegnaFino(1); apertura = null; },
    });

    el.querySelector(".pnl-cia__totale").textContent = kB(totale);
    el.querySelector("[data-conteggio]").textContent =
      `${voci.length} file · ${per.size} rami · ${fette.length} settori`;
    el.querySelector("[data-varco]").textContent =
      `varco ${dec(VARCO_ANELLO * 180 / Math.PI, 1)}° · foro ${dec(R_INTERNO / R_ESTERNO * 100, 0)} %`;
  }

  return { el, radice: el, aggiorna };
}
