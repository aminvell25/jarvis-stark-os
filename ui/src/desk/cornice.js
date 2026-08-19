/* La cornice di una finestra — SPEC §13, §10.2.
 *
 * Sta fra WinBox e il pannello, e risolve due cose che nessuno dei due puo'
 * risolvere da solo.
 *
 * ## 1. Non c'e' niente da trascinare
 *
 * I pannelli montano con la classe `no-header`: la testata di WinBox e'
 * nascosta perche' il pannello porta gia' la propria (§10.2 ①②③), e due barre
 * di titolo sovrapposte sono un duplicato che si vede.
 *
 * Ma §13 vuole «doppio clic barra -> massimizza» e «trascinamento al bordo ->
 * aggancia a meta'», e con `no-header` non esiste nessuna barra su cui farlo.
 * Quindi **la testa del pannello diventa la maniglia**. WinBox resta per cio'
 * che sa fare — posizione, dimensione, ordine di sovrapposizione, modale — e
 * il trascinamento lo fa questo modulo, che sa anche dove sono i bordi.
 *
 * ## 2. Quattordici pannelli mostrano tre controlli che non fanno niente
 *
 * `⊟ ⊡ ⊠` sono nell'anatomia di §10.2 e ogni pannello li disegna. Nella
 * galleria e' giusto che siano inerti: non c'e' nessuna finestra da
 * minimizzare. Su una scrivania sono il mockup contro cui §10.2 mette in
 * guardia.
 *
 * La cornice se ne APPROPRIA: monta il pannello, trova il suo `__ctrl` e ne
 * sostituisce il contenuto con tre controlli veri. Una sola implementazione,
 * **zero pannelli toccati**, e la galleria continua a mostrare il componente
 * esattamente com'e'.
 *
 * Il contratto — una testa e un gruppo di controlli per pannello — non e'
 * un'assunzione: `tests/eval_visual.py` lo verifica su ogni componente
 * registrato.
 */

import { tokPx } from "../style/tokens.js";

export const meta = { nome: "cornice", versione: "1" };

/** Quanto vicino al bordo deve arrivare il puntatore perche' scatti l'aggancio. */
const SOGLIA_AGGANCIO = 24;

/** Le classi di WinBox, e ognuna e' una regola, non un gusto. */
const CLASSI = [
  "jarvis-panel",
  "no-header",       // §10.2: la testata ce l'ha gia' il pannello
  "no-animation",    // invariante 25: nessuna animazione senza causa
  "no-shadow",       // invariante 19: la profondita' viene dal contrasto
];

export const css = `
/* I tre controlli, al posto del testo inerte del pannello. Ereditano corpo,
   famiglia e colore dal loro contenitore: e' il pannello a decidere come si
   vedono, la cornice decide solo che funzionino. */
.crn-ctrl {
  background: none;
  border: 0;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
  line-height: 1;
}
.crn-ctrl + .crn-ctrl { margin-left: var(--s-1); }
.crn-ctrl:hover { color: var(--cy-300); }
.crn-ctrl:focus-visible { outline: var(--line-base) solid var(--cy-500); }

/* La testa diventa una maniglia. touch-action:none non e' cosmesi: senza,
   il browser interpreta il trascinamento come uno scorrimento e i
   pointermove smettono di arrivare a meta' gesto. */
.crn-maniglia { cursor: move; touch-action: none; user-select: none; }

/* L'anteprima dell'aggancio: dove finira' il pannello se lo lascio adesso.
   Nessuna transizione — compare e sparisce, come una decisione. */
.crn-aggancio {
  position: fixed;
  z-index: 9;
  pointer-events: none;
  border: var(--line-bold) solid var(--cy-700);
  background: var(--bg-deep);
  opacity: 0.45;
}
.crn-aggancio[hidden] { display: none; }
`;

/* ── l'anteprima, una sola per scrivania ─────────────────────────────────── */

let _anteprima = null;

function anteprima() {
  if (!_anteprima) {
    _anteprima = document.createElement("div");
    _anteprima.className = "crn-aggancio";
    _anteprima.hidden = true;
    document.body.appendChild(_anteprima);
  }
  return _anteprima;
}

/* ── geometria dell'aggancio ─────────────────────────────────────────────── */

/**
 * Il rettangolo su cui si aggancia il puntatore, oppure `null`.
 *
 * §13 dice «aggancia a meta'»: quattro meta', una per bordo. Gli angoli non
 * fanno quarti — sarebbe una regola in piu' da indovinare mentre si trascina,
 * e il bordo orizzontale ha la precedenza perche' e' quello che si cerca.
 */
export function zonaAggancio(x, y, area, soglia = SOGLIA_AGGANCIO) {
  const { sinistra, alto, larghezza, altezza } = area;
  const destra = sinistra + larghezza;
  const basso = alto + altezza;
  const meta = { larghezza: Math.round(larghezza / 2), altezza: Math.round(altezza / 2) };

  if (x - sinistra <= soglia)
    return { x: sinistra, y: alto, w: meta.larghezza, h: altezza, nome: "sinistra" };
  if (destra - x <= soglia)
    return { x: sinistra + meta.larghezza, y: alto, w: larghezza - meta.larghezza,
             h: altezza, nome: "destra" };
  if (y - alto <= soglia)
    return { x: sinistra, y: alto, w: larghezza, h: meta.altezza, nome: "alto" };
  if (basso - y <= soglia)
    return { x: sinistra, y: alto + meta.altezza, w: larghezza,
             h: altezza - meta.altezza, nome: "basso" };
  return null;
}

/* ── la cornice ──────────────────────────────────────────────────────────── */

/**
 * Monta un componente in una finestra vera.
 *
 * `componente.crea()` puo' essere asincrona — i glifi PixiJS lo sono — quindi
 * lo e' anche questa. Un `await` su un valore che non e' una promessa non
 * costa nulla, e un ramo che distingue i due casi si sbaglia una volta sola.
 */
export async function creaCornice({ componente, geometria, area, suChiusura, suFuoco,
                                    suGeometria }) {
  const ospite = document.createElement("div");
  // WinBox monta questo nodo nel proprio corpo: senza altezza piena il
  // pannello si ferma al suo contenuto e sotto resta spazio morto, che §11.6
  // regola 3 vieta espressamente.
  ospite.style.height = "100%";
  const pannello = await componente.crea(ospite);

  const box = new WinBox({
    class: CLASSI,
    x: geometria.x,
    y: geometria.y,
    width: geometria.larghezza,
    height: geometria.altezza,
    // I limiti dell'area utile. Li conosce WinBox, quindi `maximize()` si
    // ferma sotto la barra e sopra il dock senza che nessuno glielo ricordi.
    top: area.alto,
    bottom: Math.round(window.innerHeight - area.alto - area.altezza),
    left: area.sinistra,
    right: Math.round(window.innerWidth - area.sinistra - area.larghezza),
    mount: ospite,
    onclose: () => { suChiusura?.(); return false; },
    // Il fuoco cambia lo z-index — WinBox fa `z-index: ++E` — quindi anche
    // guadagnare il fuoco e' un cambio di disposizione da ricordare: §26.2
    // dice che la pila non si riordina da sola, e allora va salvata com'e'.
    onfocus: () => { suFuoco?.(); suGeometria?.(); },
    onmove: () => suGeometria?.(),
    onresize: () => suGeometria?.(),
    onmaximize: () => suGeometria?.(),
    onminimize: () => suGeometria?.(),
  });

  const testa = ospite.querySelector('[class*="__testa"]');
  const ctrl = ospite.querySelector('[class*="__ctrl"]');
  const cornice = { box, pannello, ospite, testa, massimizzata: false };

  if (ctrl) armaControlli(ctrl, cornice);
  if (testa) armaManiglia(testa, cornice, area);

  return cornice;
}

/**
 * La geometria di una cornice, nella forma che il core sa mettere giu'.
 *
 * Legge le proprieta' pubbliche di WinBox invece di misurare il DOM: `x`, `y`,
 * `width`, `height` e `index` sono cio' che WinBox considera vero, e durante
 * un'animazione il DOM e quelle proprieta' non coincidono. Salvare il DOM
 * significherebbe salvare un fotogramma di mezzo.
 */
export function geometriaDi(cornice) {
  const b = cornice.box;
  return {
    x: Math.round(b.x) | 0,
    y: Math.round(b.y) | 0,
    larghezza: Math.round(b.width) | 0,
    altezza: Math.round(b.height) | 0,
    z: Math.round(b.index) | 0,
    massimizzato: !!b.max,
  };
}

/**
 * Rimette una cornice dove era. Il contrario di `geometriaDi()`.
 *
 * L'ordine conta: prima posizione e dimensione, poi la massimizzazione.
 * Al contrario, `maximize()` salverebbe come «dimensione precedente» quella
 * che c'era prima del ripristino, e uscendo da massimizzato il pannello
 * tornerebbe alla cella di `moduli.js` invece che dove l'utente l'aveva messo.
 */
export function applicaGeometria(cornice, g) {
  cornice.box.resize(g.larghezza, g.altezza).move(g.x, g.y);
  if (g.massimizzato) {
    cornice.massimizzata = true;
    cornice.box.maximize(true);
  }
}

/* ── i tre controlli ─────────────────────────────────────────────────────── */

//: Glifo, etichetta e azione. Gli stessi tre segni che il pannello disegna
//: gia': la cornice li rende premibili, non li reinventa.
const CONTROLLI = [
  ["⊟", "riduci", (c) => c.box.minimize()],
  ["⊡", "ingrandisci", (c) => alterna(c)],
  ["⊠", "chiudi", (c) => c.box.close()],
];

function armaControlli(ctrl, cornice) {
  ctrl.textContent = "";
  for (const [glifo, etichetta, azione] of CONTROLLI) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "crn-ctrl";
    b.dataset.ctrl = etichetta;
    b.textContent = glifo;
    b.title = etichetta;
    b.setAttribute("aria-label", etichetta);
    // `pointerdown` fermato qui: la testa che sta sotto e' la maniglia del
    // trascinamento, e senza questo un clic su ⊠ comincerebbe a trascinare.
    b.addEventListener("pointerdown", (e) => e.stopPropagation());
    b.addEventListener("click", () => azione(cornice));
    ctrl.appendChild(b);
  }
}

function alterna(cornice) {
  cornice.massimizzata = !cornice.massimizzata;
  cornice.box.maximize(cornice.massimizzata);
}

/* ── trascinamento e aggancio ────────────────────────────────────────────── */

function armaManiglia(testa, cornice, area) {
  testa.classList.add("crn-maniglia");
  const { box } = cornice;
  let presa = null;

  testa.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    // Massimizzata: si riprende in mano, come farebbe qualunque gestore di
    // finestre. Restare fermi sarebbe l'unica cosa che sorprende.
    if (cornice.massimizzata) alterna(cornice);
    const r = box.window.getBoundingClientRect();
    presa = { id: e.pointerId, dx: e.clientX - r.left, dy: e.clientY - r.top };
    testa.setPointerCapture(e.pointerId);
    box.focus();
    e.preventDefault();
  });

  testa.addEventListener("pointermove", (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    const x = limita(e.clientX - presa.dx, area.sinistra,
                     area.sinistra + area.larghezza - 1);
    const y = limita(e.clientY - presa.dy, area.alto,
                     area.alto + area.altezza - 1);
    box.move(x, y);

    const zona = zonaAggancio(e.clientX, e.clientY, area);
    const a = anteprima();
    if (zona) {
      Object.assign(a.style, {
        left: `${zona.x}px`, top: `${zona.y}px`,
        width: `${zona.w}px`, height: `${zona.h}px`,
      });
      a.hidden = false;
    } else {
      a.hidden = true;
    }
  });

  const rilascia = (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    const zona = zonaAggancio(e.clientX, e.clientY, area);
    presa = null;
    anteprima().hidden = true;
    if (zona) {
      box.resize(zona.w, zona.h);
      box.move(zona.x, zona.y);
    }
  };
  testa.addEventListener("pointerup", rilascia);
  testa.addEventListener("pointercancel", rilascia);

  // §13: doppio clic sulla barra massimizza. Sulla NOSTRA barra, che e' la
  // testa del pannello, perche' quella di WinBox non c'e'.
  testa.addEventListener("dblclick", (e) => {
    if (e.target.closest("[data-ctrl]")) return;
    alterna(cornice);
  });
}

function limita(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

/** Il passo della griglia di §10.1, per chi compone le geometrie. */
export function passo() {
  return tokPx("--grid");
}
