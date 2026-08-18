/* Piani stratificati — SPEC §11.4, riferimento famiglia-a/08-archivio-piani-stratificati.
 *
 * Documenti su piani Z traslucidi, con una filmstrip sotto. Nel riferimento
 * sono schede d'archivio; qui sono i documenti di accettazione delle fasi, che
 * esistono davvero e che qualcuno ha scritto (§11.9).
 *
 * ── Perche' CSS 3D e non three.js ──────────────────────────────────────────
 * §11.4 lo chiama «l'errore da non fare»: mettere in WebGL i documenti dei
 * piani stratificati sembra la scelta piu' 3D ed e' sbagliata. Rasterizzare il
 * testo lo rende sfocato, non selezionabile, costoso da aggiornare, e rende
 * impossibile incassarci dentro una `<webview>`.
 *
 * Il compositore di Chromium gestisce questi piani sulla GPU: costo quasi
 * zero, e il testo resta testo.
 *
 * ── La trappola del clip-path (R50) ────────────────────────────────────────
 * §11.3 lo avverte: `clip-path` crea uno stacking context e APPIATTISCE le
 * trasformazioni 3D. Ogni pannello di JARVIS usa augmented-ui, cioe'
 * clip-path. Quindi l'elemento augmented sta ANNIDATO dentro quello
 * trasformato, mai fuso con esso: `.pia__piano` porta la transform, e
 * `.pia__foglio` dentro di lui porta il taglio a 45 gradi.
 *
 * ── L'animazione ha una causa ──────────────────────────────────────────────
 * I piani si muovono solo quando si sceglie un documento: un clic. Invariante
 * 25 — nessuna animazione ambientale, nessuna deriva continua nel fondo.
 */

import { animate } from "../../vendor/anime.esm.min.js";

export const meta = { nome: "planes", versione: "1" };

/* La scalinatura. La prima versione teneva i piani quasi sovrapposti e
 * scartati di 26 px: nello screenshot erano una pila illeggibile, col testo
 * dei piani dietro che attraversava quelli davanti. Il riferimento ha quattro
 * o cinque piani che arretrano in diagonale, ben staccati — la profondita' si
 * legge perche' ogni piano ha un pezzo di se' scoperto. */
const PASSO_Z = 200;   // px di arretramento fra un piano e il successivo
const SCARTO_X = 148;  // px verso destra
const SCARTO_Y = 34;   // px verso l'alto
const VISIBILI = 5;    // oltre il quinto non si distingue piu' niente

export const css = `
.pia {
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
  --aug-tl: var(--s-3);
  --aug-border-bg: var(--cy-900);
}
.pia__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pia__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pia__id, .pia__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pia__ctrl { letter-spacing: 0.16em; }

/* Il palco: prospettiva e conservazione del 3D — §11.4 verbatim. */
.pia__palco {
  position: relative;
  perspective: 2400px;
  transform-style: preserve-3d;
  min-height: 0;
  overflow: hidden;
}
.pia__piano {
  position: absolute;
  top: 50%;
  left: var(--s-5);
  width: calc(var(--grid) * 3);
  transform-style: preserve-3d;
  /* L'origine sta a sinistra: la pila cresce verso destra come nel
     riferimento, invece di espandersi dai due lati del centro. */
  transform: translateY(-50%)
             translate3d(var(--x), var(--y), var(--z))
             rotateY(var(--ry));
  transform-origin: left center;
  will-change: transform;
}
/* ANNIDATO dentro il trasformato: il taglio a 45 gradi sta qui, la
   trasformazione sta sopra. Fondere i due appiattirebbe il 3D. */
.pia__foglio {
  display: grid;
  gap: var(--s-2);
  padding: var(--s-3);
  /* Il fondo e' un TOKEN, non la ricetta del vetro copiata a mano: quel
     letterale e' lecito solo dentro tokens.css, che e' la sorgente.
     La traslucenza dei piani di §11.4 la da' l'opacita' del piano, che
     e' anche il segnale di profondita'. L'ha visto l'audit. */
  background: var(--bg-panel);
  border: var(--line-hair) solid var(--cy-700);
  border-radius: var(--radius);
}
.pia__piano[data-fuoco="1"] .pia__foglio { border-color: var(--cy-300); }
.pia__nome {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-dim);
}
.pia__titolo {
  font-size: var(--t-body);
  line-height: 1.25;
  color: var(--txt-primary);
}
.pia__corpo {
  font-size: var(--t-label);
  line-height: 1.45;
  color: var(--txt-dim);
  user-select: text;
}
.pia__quota {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding-top: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}

/* La filmstrip: e' il riferimento, ed e' anche il comando. */
.pia__strip {
  display: flex;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  overflow-x: auto;
}
.pia__mini {
  flex: 0 0 auto;
  padding: var(--s-1) var(--s-2);
  background: var(--bg-raised);
  border: var(--line-hair) solid var(--cy-900);
  border-bottom: var(--line-bold) solid var(--cy-900);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
  cursor: pointer;
}
.pia__mini[data-fuoco="1"] {
  border-bottom-color: var(--cy-300);
  color: var(--cy-100);
}
.pia__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pia__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pia[data-stato="vuoto"] .pia__palco { display: none; }
.pia[data-stato="vuoto"] .pia__vuoto { display: block; }
`;

const kb = (n) => `${(n / 1024).toFixed(1)} kB`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pia";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pia__testa">
      <span class="pia__etichetta">Archivio stratificato</span>
      <span class="pia__id">ARC_I09 · ver ${meta.versione}</span>
      <span class="pia__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pia__palco"></div>
    <div class="pia__vuoto">NESSUN DOCUMENTO COLLEGATO</div>
    <div class="pia__strip"></div>
    <div class="pia__piede">
      <span class="pia__conteggio"></span>
      <span class="pia__profondita"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const palco = radice.querySelector(".pia__palco");
  const strip = radice.querySelector(".pia__strip");
  let piani = [];
  let fuoco = 0;

  function colloca(animato) {
    // Ordine a giostra: il documento a fuoco e' SEMPRE il primo, gli altri
    // arretrano dietro di lui e riprendono dall'inizio. Cosi' la posizione
    // dice la distanza dal fuoco e non l'indice nell'elenco, e il piano in
    // primo piano non finisce mai sepolto sotto i suoi vicini.
    for (const [i, p] of piani.entries()) {
      const k = (i - fuoco + piani.length) % piani.length;
      const dentro = k < VISIBILI;
      const stile = {
        "--x": `${k * SCARTO_X}px`,
        "--y": `${-k * SCARTO_Y}px`,
        "--z": `${-k * PASSO_Z}px`,
        "--ry": `${k === 0 ? 0 : -15}deg`,
      };
      p.el.dataset.fuoco = k === 0 ? "1" : "0";
      p.chip.dataset.fuoco = k === 0 ? "1" : "0";
      p.el.style.display = dentro ? "" : "none";
      p.el.style.zIndex = String(piani.length - k);
      // Il primo e' pieno, gli altri arretrano anche in luce. Sotto 0,3 il
      // testo non si legge piu' e il piano diventa una superficie: e' voluto.
      const opacita = k === 0 ? 1 : Math.max(0.26, 0.82 - k * 0.18);

      if (!animato) {
        for (const [kk, v] of Object.entries(stile)) p.el.style.setProperty(kk, v);
        p.el.style.opacity = String(opacita);
        continue;
      }
      // La causa e' il clic. 260 ms, come l'apertura dei pannelli di §10.3.
      animate(p.el, { ...stile, opacity: opacita, duration: 260, ease: "outQuart" });
    }
    radice.querySelector(".pia__profondita").textContent =
      `fuoco ${fuoco + 1}/${piani.length} · ${VISIBILI} piani visibili · passo ${PASSO_Z} px in Z`;
  }

  function disegna(note) {
    if (!note?.length) { radice.dataset.stato = "vuoto"; return; }
    radice.dataset.stato = "pieno";
    palco.replaceChildren();
    strip.replaceChildren();

    piani = note.map((n, i) => {
      const el = document.createElement("div");
      el.className = "pia__piano";
      el.innerHTML = `
        <div class="pia__foglio" data-augmented-ui="tr-clip border">
          <div class="pia__nome">${n.file}</div>
          <div class="pia__titolo">${n.titolo}</div>
          <div class="pia__corpo">${n.corpo}</div>
          <div class="pia__quota"><span>${kb(n.byte)}</span><span>piano ${i + 1}</span></div>
        </div>`;
      palco.appendChild(el);

      const chip = document.createElement("button");
      chip.className = "pia__mini";
      chip.type = "button";
      chip.textContent = n.file.replace(/\.md$/, "");
      chip.addEventListener("click", () => { fuoco = i; colloca(true); });
      strip.appendChild(chip);

      return { el, chip };
    });

    radice.querySelector(".pia__conteggio").textContent =
      `${note.length} documenti · ${kb(note.reduce((s, n) => s + n.byte, 0))}`;
    colloca(false);
  }

  return {
    radice,
    /** @param {{topic:string, note:object[]}} msg */
    aggiorna(msg) {
      if (msg?.topic !== "archive.notes") return;
      disegna(msg.note);
    },
    /** Per la verifica: sposta il fuoco come farebbe un clic. */
    versoPiano(i) { fuoco = Math.max(0, Math.min(piani.length - 1, i)); colloca(true); },
  };
}
