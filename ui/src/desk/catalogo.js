/* Il catalogo — SPEC-26 §26.3 e §26.4.
 *
 * ## Che cos'e', e perche' non e' un altro dock
 *
 * §26.3 lo dice in una riga: **unifica la barra delle applicazioni e il file
 * manager**, che erano due richieste separate. Sono lo stesso contenitore con
 * due linguette. Il dock di §13 gli cede l'indice dei moduli e le azioni, e
 * resta la striscia di stato.
 *
 * ## Opzione B: un pannello, non una barra a piena larghezza
 *
 * Il riferimento `famiglia-a/01` non ha una barra ancorata in fondo: ha un
 * pannello nella parte centro-bassa, con le cartelle che gli galleggiano
 * accanto. Quello e' il modello scelto.
 *
 * ## Perche' sta nella cornice e non fra i pannelli
 *
 * Il catalogo e' l'INDICE dell'ambiente, e un indice che si puo' seppellire
 * smette di essere un indice — e' la stessa ragione per cui §26.5 dice che
 * un'icona tirata fuori non sparisce dal catalogo. Quindi vive in
 * `#scrivania`, che sta sopra i pannelli (`--z-cornice` in `app.css`), e non
 * in una finestra WinBox.
 *
 * ⚠️ Il suo contenitore ha `pointer-events: none` e solo il catalogo lo
 * riprende: senza, meta' schermo diventerebbe una lastra invisibile che
 * intercetta i clic destinati ai pannelti sotto.
 *
 * ## L'anatomia, misurata sul riferimento
 *
 *   ①  frecce di navigazione
 *   ②  due campi percorso RIEMPITI — L 92, sono la cosa piu' chiara della testa
 *   ③  linguette a separatore diagonale — fondo L 37, testo L 96
 *   ④  griglia di tessere, scorrevole in orizzontale
 *   ⑤  plinto in PROSPETTIVA con le icone in evidenza — L 171, picchi L 216
 *
 * Il ⑥ del riferimento — le cartelle manila 2x2 fuori dal pannello — e' il
 * punto 5 di §26.10 e non c'e' ancora.
 *
 * ## Le icone sono RIEMPITE, e la differenza e' misurata
 *
 * Fascia del catalogo nel riferimento: 26,2 % di superficie accesa. Nostro
 * dock di oggi: 2,8 %. Non e' una questione di gusto — le nostre «icone» sono
 * testo a L 96, le sue sono forme piene a L 171-216. Da qui i due token nuovi.
 */

import { animate, stagger, utils } from "../../vendor/anime.esm.min.js";

import { moduliIndicizzati } from "./moduli.js";

export const meta = { nome: "catalogo", versione: "1" };

/** Le quattro linguette di §26.3. `pronta` dice se ha davvero un contenuto. */
export const LINGUETTE = [
  { id: "moduli", etichetta: "MODULI", pronta: true },
  { id: "file", etichetta: "FILE", pronta: true },
  // §26.6 e §26.7: esistono come sezioni, non come contenuti. Si dichiarano
  // vuote invece di sparire — invariante 23, e una linguetta che compare fra
  // due passi sposta tutte le altre sotto il dito di chi la stava usando.
  { id: "scene", etichetta: "SCENE", pronta: false },
  { id: "sistema", etichetta: "SISTEMA", pronta: false },
];

/** Le azioni sul plinto: agiscono sull'AMBIENTE, non sono contenuti. */
const AZIONI = [
  { id: "nascondi", etichetta: "nascondi tutto", tasto: "Alt+H",
    fai: (s) => s.nascondiTutto() },
  { id: "affianca", etichetta: "affianca", tasto: "Alt+T",
    fai: (s) => s.affianca() },
  { id: "tutto", etichetta: "togli il filtro", tasto: "Alt+1…4",
    fai: (s) => s.tutto() },
];

//: Sotto questa velocita' l'inerzia si ferma (§26.4 punto 2).
const FERMO_PX_MS = 0.05;
//: Quanto lontano porta la velocita' al rilascio. Non e' fisica: e' il tempo
//: equivalente di volo, ed e' l'unico numero che decide se il gesto «tira».
const VOLO_MS = 320;

export const css = `
/* ⚠️ L'OSPITE dev'essere un box vero.
   Il primo giro gli dava display:contents, che gli toglie il box — e con
   esso lo z-index che app.css da' a #scrivania > *. Il catalogo veniva
   disegnato DIETRO i quattordici pannelli, cioe' non si vedeva affatto. */
.cat-ospite {
  flex: 1;
  display: flex;
  pointer-events: none;
}

/* Il contenitore non deve rubare i clic ai pannelli che gli stanno sotto:
   e' largo quanto la scrivania e alto quanto lo spazio libero. */
.cat-ancora {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  pointer-events: none;
  padding-bottom: var(--s-2);
}
.cat-ancora > * { pointer-events: auto; }

.cat {
  width: calc(var(--grid) * 9);
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border: var(--line-base) solid var(--cy-900);
  border-radius: var(--radius);
  font-family: var(--font-ui);
}

/* ① ② la testa: frecce e i due campi percorso RIEMPITI */
.cat__testa {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.cat__freccia {
  background: none;
  border: var(--line-hair) solid var(--cy-900);
  border-radius: var(--radius);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  padding: 0 var(--s-1);
  cursor: pointer;
}
.cat__freccia:hover { color: var(--icona-viva); border-color: var(--cy-700); }
.cat__percorso {
  background: var(--fill-3);
  color: var(--bg-void);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  padding: 0 var(--s-2);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.cat__percorso--lungo { flex: 1; }
.cat__percorso--corto { width: calc(var(--grid) * 1.5); }
.cat__stato {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}

/* ③ le linguette, a separatore diagonale come nel riferimento */
.cat__linguette {
  display: flex;
  align-items: stretch;
  background: var(--bg-raised);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.cat__linguetta {
  position: relative;
  background: none;
  border: 0;
  border-radius: var(--radius);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.14em;
  padding: var(--s-1) var(--s-3);
  cursor: pointer;
}
/* Il separatore diagonale: una linea inclinata fra una linguetta e l'altra,
   disegnata col bordo di uno pseudo-elemento ruotato. Non un carattere: un
   glifo dipenderebbe dal font e si disallineerebbe al primo cambio di corpo. */
.cat__linguetta + .cat__linguetta::before {
  content: "";
  position: absolute;
  left: 0;
  top: var(--s-1);
  bottom: var(--s-1);
  border-left: var(--line-hair) solid var(--cy-900);
  transform: rotate(20deg);
}
.cat__linguetta[aria-selected="true"] { color: var(--icona); background: var(--fill-1); }
.cat__linguetta[data-vuota] { color: var(--txt-ghost); }
.cat__linguetta:hover { color: var(--icona-viva); }

/* ④ la griglia: scorre in orizzontale, e la barra la disegna nessuno */
.cat__vista {
  position: relative;
  overflow: hidden;
  height: calc(var(--grid) * 0.8);
  background: var(--bg-void);
  cursor: grab;
  touch-action: pan-y;
}
.cat__vista[data-presa] { cursor: grabbing; }
.cat__nastro {
  display: flex;
  gap: var(--s-1);
  padding: var(--s-2);
  height: 100%;
  will-change: transform;
}
.cat__tessera {
  flex: 0 0 auto;
  width: calc(var(--grid) * 0.9);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: var(--fill-1);
  border: var(--line-hair) solid var(--cy-900);
  border-radius: var(--radius);
  padding: var(--s-1);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  text-align: left;
  cursor: pointer;
  /* §26.4: hover e pressione sono STATI, quindi transizione CSS e mai
     anime.js — allocare un oggetto animazione a ogni passaggio del puntatore
     su venti icone e' il modo esatto di sforare i 4 ms di §10.4. */
  transition: background 120ms linear, color 120ms linear;
}
.cat__tessera:hover { background: var(--fill-2); color: var(--icona-viva); }
.cat__tessera[aria-pressed="true"] { background: var(--fill-2); color: var(--icona); }
.cat__tessera[data-fuori] { color: var(--txt-ghost); }
.cat__segno {
  display: block;
  width: var(--s-3);
  height: var(--s-3);
  background: var(--icona);
}
.cat__tessera[data-fuori] .cat__segno { background: var(--txt-ghost); }
.cat__tessera:hover .cat__segno { background: var(--icona-viva); }
.cat__vuoto {
  display: flex;
  align-items: center;
  padding: var(--s-3);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-data);
}

/* L'indicatore di posizione: una tacca, non una barra di scorrimento. */
.cat__indicatore {
  height: var(--line-bold);
  background: var(--bg-raised);
}
.cat__tacca {
  display: block;
  height: 100%;
  background: var(--cy-700);
  will-change: transform;
}

/* ⑤ il plinto, in PROSPETTIVA — una lastra piu' larga davanti.
   E' la stessa tecnica di §11.4 gia' usata per i piani d'archivio e la board:
   CSS 3D, non three.js, perche' il testo deve restare nel DOM (invariante 20). */
.cat__plinto {
  position: relative;
  perspective: calc(var(--grid) * 4);
  padding-top: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
}
.cat__lastra {
  position: absolute;
  left: 18%;
  right: 18%;
  top: var(--s-2);
  bottom: 0;
  background: var(--fill-1);
  border-top: var(--line-base) solid var(--cy-700);
  transform: rotateX(52deg);
  transform-origin: top center;
}
.cat__azioni {
  position: relative;
  display: flex;
  justify-content: center;
  gap: var(--s-4);
  padding: var(--s-2) var(--s-3) var(--s-3);
}
.cat__azione {
  background: none;
  border: 0;
  border-radius: var(--radius);
  padding: 0;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s-1);
  color: var(--txt-ghost);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  transition: color 120ms linear;
}
.cat__azione svg { fill: var(--icona); transition: fill 120ms linear; }
.cat__azione:hover { color: var(--icona-viva); }
.cat__azione:hover svg { fill: var(--icona-viva); }

.cat__piede {
  display: flex;
  justify-content: space-between;
  padding: var(--s-1) var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
`;

/* ── i segni delle azioni ─────────────────────────────────────────────────
 *
 * Forme geometriche RIEMPITE, disegnate qui e non prese da una libreria di
 * icone: §26.3 chiede icone piene, e un set esterno porterebbe con se' un
 * tratto, un raggio e una griglia che non sono i nostri. Tre azioni, tre
 * forme che dicono cosa fanno senza pittogrammi da indovinare.
 */
const SEGNI = {
  // nascondi tutto: una superficie che si abbassa
  nascondi: "M2 3h20v7H2zM2 13h20v3H2zM2 18h20v2H2z",
  // affianca: quattro riquadri nella griglia
  affianca: "M2 2h9v9H2zM13 2h9v9h-9zM2 13h9v9H2zM13 13h9v9h-9z",
  // togli il filtro: un imbuto pieno, aperto
  tutto: "M2 3h20l-8 9v9l-4-3v-6z",
};

function segno(id) {
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "20");
  svg.setAttribute("height", "20");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(NS, "path");
  path.setAttribute("d", SEGNI[id]);
  svg.appendChild(path);
  return svg;
}

/* ── il componente ───────────────────────────────────────────────────────── */

export function crea(ospite, { scrivania, bus }) {
  const ancora = document.createElement("div");
  ancora.className = "cat-ancora";
  const el = document.createElement("section");
  el.className = "cat";
  ancora.appendChild(el);

  /* ① ② testa */
  const testa = document.createElement("header");
  testa.className = "cat__testa";
  for (const [glifo, etichetta] of [["◀", "indietro"], ["▶", "avanti"]]) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__freccia";
    b.textContent = glifo;
    b.title = etichetta;
    b.setAttribute("aria-label", etichetta);
    // ⚠️ La navigazione a cronologia e' del file manager (§26.8, punto 9).
    // Le frecce ci sono perche' l'anatomia del riferimento le ha; oggi
    // scorrono il nastro, che e' l'unica cosa vera che possono fare.
    b.addEventListener("click", () => scorriDi(glifo === "◀" ? 240 : -240));
    testa.appendChild(b);
  }
  const percorso = document.createElement("span");
  percorso.className = "cat__percorso cat__percorso--lungo";
  percorso.textContent = "—";
  const percorsoCorto = document.createElement("span");
  percorsoCorto.className = "cat__percorso cat__percorso--corto";
  percorsoCorto.textContent = "—";
  const stato = document.createElement("span");
  stato.className = "cat__stato";
  stato.textContent = "T2 inerte";
  testa.append(percorso, percorsoCorto, stato);

  /* ③ linguette */
  const nav = document.createElement("nav");
  nav.className = "cat__linguette";
  nav.setAttribute("aria-label", "categorie del catalogo");
  const linguette = new Map();
  for (const l of LINGUETTE) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__linguetta";
    b.textContent = l.etichetta;
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", "false");
    if (!l.pronta) b.dataset.vuota = "";
    b.addEventListener("click", () => apri(l.id));
    linguette.set(l.id, b);
    nav.appendChild(b);
  }

  /* ④ griglia */
  const vista = document.createElement("div");
  vista.className = "cat__vista";
  const nastro = document.createElement("div");
  nastro.className = "cat__nastro";
  vista.appendChild(nastro);
  const indicatore = document.createElement("div");
  indicatore.className = "cat__indicatore";
  const tacca = document.createElement("span");
  tacca.className = "cat__tacca";
  indicatore.appendChild(tacca);

  /* ⑤ plinto */
  const plinto = document.createElement("div");
  plinto.className = "cat__plinto";
  const lastra = document.createElement("div");
  lastra.className = "cat__lastra";
  const azioni = document.createElement("div");
  azioni.className = "cat__azioni";
  for (const a of AZIONI) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__azione";
    b.title = `${a.etichetta} — ${a.tasto}`;
    b.dataset.azione = a.id;
    const et = document.createElement("span");
    et.textContent = a.etichetta;
    b.append(segno(a.id), et);
    b.addEventListener("click", () => a.fai(scrivania));
    azioni.appendChild(b);
  }
  plinto.append(lastra, azioni);

  const piede = document.createElement("footer");
  piede.className = "cat__piede";
  const conteggio = document.createElement("span");
  const versione = document.createElement("span");
  versione.textContent = `CAT_A01 · ver ${meta.versione}`;
  piede.append(conteggio, versione);

  el.append(testa, nav, vista, indicatore, plinto, piede);
  ospite.appendChild(ancora);

  /* ── il contenuto delle linguette ────────────────────────────────────── */

  let attiva = "moduli";
  let fileVisti = [];
  let apertiOra = new Set();
  let filtroOra = null;

  function voci() {
    if (attiva === "moduli") {
      return moduliIndicizzati().map((m) => ({
        id: m.id, etichetta: m.etichetta, categoria: m.categoria,
        acceso: apertiOra.has(m.id),
        fai: () => scrivania.alterna(m.id),
      }));
    }
    if (attiva === "file") {
      return fileVisti.map((v) => ({
        id: v.nome, etichetta: (v.cartella ? "▸ " : "") + v.nome,
        categoria: 2, acceso: false,
        // Aprire un file e' del file manager (§26.8, punto 9). Qui la voce
        // porta al pannello che sa farlo, invece di fingere un'operazione.
        fai: () => scrivania.apri("file"),
      }));
    }
    return [];
  }

  function vuotoDi(id) {
    if (id === "file") return "nessun file: la workspace non e' leggibile";
    if (id === "scene") return "nessuna scena salvata — §26.6, non ancora costruito";
    return "doctor, impostazioni e cestino — §26.7, non ancora costruiti";
  }

  /**
   * Aggiorna cio' che e' GIA' a schermo: acceso/spento e dentro/fuori filtro.
   *
   * ⚠️ Non ricostruisce. Il primo giro rifaceva l'intera griglia a ogni
   * `osserva()` — cioe' a ogni pannello che si apre, si chiude o prende il
   * fuoco — e con quarantuno tessere significava distruggere e ricreare
   * quarantuno nodi decine di volte al minuto. Si perdevano il fuoco della
   * tastiera e lo stato di hover, e il pulsante che si stava premendo veniva
   * staccato dal documento a meta' del clic: `--verifica-scrivania` lo ha
   * scoperto misurando otto voci che non commutavano mai.
   *
   * Il contenuto si ridisegna solo quando CAMBIA — linguetta nuova, elenco di
   * file nuovo — e lo stato si aggiorna sul posto.
   */
  function aggiorna() {
    for (const b of nastro.querySelectorAll(".cat__tessera")) {
      if (attiva === "moduli") {
        b.setAttribute("aria-pressed", String(apertiOra.has(b.dataset.voce)));
      }
      if (filtroOra && Number(b.dataset.categoria) !== filtroOra) b.dataset.fuori = "";
      else delete b.dataset.fuori;
    }
    conteggio.textContent = testoConteggio();
  }

  function testoConteggio() {
    const n = nastro.querySelectorAll(".cat__tessera").length;
    return `${n} ${n === 1 ? "voce" : "voci"} in ${attiva}` +
      (filtroOra ? ` · filtro 0${filtroOra}` : "");
  }

  function disegna() {
    nastro.textContent = "";
    const elenco = voci();
    if (!elenco.length) {
      const v = document.createElement("div");
      v.className = "cat__vuoto";
      // Invariante 23: uno stato vuoto ESPLICITO, che dice anche perche'.
      v.textContent = vuotoDi(attiva);
      nastro.appendChild(v);
    }
    for (const voce of elenco) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cat__tessera";
      b.dataset.voce = voce.id;
      b.dataset.categoria = String(voce.categoria);
      b.setAttribute("aria-pressed", String(voce.acceso));
      if (filtroOra && voce.categoria !== filtroOra) b.dataset.fuori = "";
      const s = document.createElement("span");
      s.className = "cat__segno";
      const et = document.createElement("span");
      et.textContent = voce.etichetta;
      b.append(s, et);
      b.addEventListener("click", () => voce.fai());
      nastro.appendChild(b);
    }
    conteggio.textContent = testoConteggio();
    limita();
    misuraTacca();
  }

  function apri(id) {
    attiva = id;
    for (const [k, b] of linguette) b.setAttribute("aria-selected", String(k === id));
    porta(0, false);
    disegna();
    entrata();
  }

  /* ── §26.4: lo scorrimento ───────────────────────────────────────────── */

  let x = 0;               // la posizione del nastro, in px (transform)
  let animazione = null;

  const massimoScorrimento = () =>
    Math.min(0, vista.clientWidth - nastro.scrollWidth);

  function porta(nuovo, animato) {
    x = Math.max(massimoScorrimento(), Math.min(0, nuovo));
    // ⚠️ `transform`, mai `left`: cambia solo la composizione e non il layout,
    // ed e' la ragione per cui questo sta dentro i 4 ms di §10.4.
    utils.set(nastro, { x });
    misuraTacca();
    return x;
  }

  function limita() { porta(x, false); }

  function scorriDi(dx) { fermaInerzia(); porta(x + dx, false); }

  function misuraTacca() {
    const visibile = vista.clientWidth;
    const totale = Math.max(nastro.scrollWidth, 1);
    const frazione = Math.min(1, visibile / totale);
    const scorso = massimoScorrimento() === 0 ? 0 : x / massimoScorrimento();
    tacca.style.width = `${(frazione * 100).toFixed(2)}%`;
    utils.set(tacca, { x: `${(scorso * (1 - frazione) * 100 / frazione).toFixed(2)}%` });
  }

  function fermaInerzia() {
    if (animazione) { animazione.pause(); animazione = null; }
  }

  /* Il trascinamento diretto: `pointer*`, non `drag` HTML5.
   *
   * §26.4 punto 1: l'API nativa non permette di controllare l'anteprima e si
   * comporta male con elementi resi a mano. `cornice.js` usa gia' questo
   * schema per le finestre. */
  let presa = null;
  vista.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    fermaInerzia();
    presa = { id: e.pointerId, x0: e.clientX, xIniziale: x,
              campioni: [{ t: e.timeStamp, x: e.clientX }], mosso: false };
    vista.setPointerCapture(e.pointerId);
    vista.dataset.presa = "";
  });

  vista.addEventListener("pointermove", (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    const dx = e.clientX - presa.x0;
    if (Math.abs(dx) > 3) presa.mosso = true;
    porta(presa.xIniziale + dx, false);
    presa.campioni.push({ t: e.timeStamp, x: e.clientX });
    // Bastano gli ultimi campioni: la velocita' che conta e' quella del
    // tratto finale, non la media di tutto il gesto.
    if (presa.campioni.length > 6) presa.campioni.shift();
  });

  const rilascia = (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    const c = presa.campioni;
    const primo = c[0];
    const ultimo = c[c.length - 1];
    const dt = ultimo.t - primo.t;
    const v = dt > 0 ? (ultimo.x - primo.x) / dt : 0;   // px/ms
    const mosso = presa.mosso;
    presa = null;
    delete vista.dataset.presa;
    // Un clic fermo non e' un lancio: senza questa soglia ogni pressione
    // partirebbe con una velocita' di rumore.
    if (!mosso || Math.abs(v) < FERMO_PX_MS) return;
    lancia(v);
  };
  vista.addEventListener("pointerup", rilascia);
  vista.addEventListener("pointercancel", rilascia);

  /**
   * L'inerzia (§26.4 punto 2), con anime.js.
   *
   * Il bersaglio si calcola dalla velocita' al rilascio; la decelerazione la
   * fa l'ease, che e' esattamente il motivo per cui l'invariante 9 vuole un
   * motore solo: scrivere la fisica a mano in `requestAnimationFrame` sarebbe
   * un secondo motore di animazione senza chiamarlo cosi'.
   *
   * ⚠️ **Ha una causa** — il gesto — quindi l'invariante 25 regge.
   */
  function lancia(v) {
    const bersaglio = Math.max(massimoScorrimento(), Math.min(0, x + v * VOLO_MS));
    if (bersaglio === x) return;
    animazione = animate(nastro, {
      x: bersaglio,
      duration: Math.min(900, Math.abs(bersaglio - x) * 2.2 + 180),
      ease: "out(3)",
      onUpdate: () => { x = utils.get(nastro, "x", false); misuraTacca(); },
      onComplete: () => { animazione = null; },
    });
  }

  // §26.4 punto 5: la rotellina scorre in orizzontale, senza `shift`.
  vista.addEventListener("wheel", (e) => {
    e.preventDefault();
    fermaInerzia();
    porta(x - (Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY), false);
  }, { passive: false });

  /** L'entrata delle icone: `stagger`, come prescrive §10.4 riga «Dock». */
  function entrata() {
    const tessere = [...nastro.querySelectorAll(".cat__tessera")];
    if (!tessere.length) return;
    animate(tessere, {
      opacity: [0, 1],
      duration: 220,
      delay: stagger(60),
      ease: "out(2)",
    });
  }

  /* ── cio' che il catalogo ascolta ────────────────────────────────────── */

  scrivania.osserva(({ aperti, filtro }) => {
    apertiOra = new Set(aperti);
    filtroOra = filtro;
    // Il filtro della barra evidenzia la categoria QUI: ADR-010 dice
    // «Alt+1…4 evidenzia nel catalogo la categoria corrispondente», e questo
    // e' il catalogo. Si AGGIORNA, non si ridisegna.
    aggiorna();
  });

  bus.su("fs.list", (m) => {
    // La forma del messaggio e' quella del tool `list_dir`, la stessa che
    // legge `panels/files.js`: `{ path, voci: [{ name, type, size }], totale }`.
    fileVisti = (m.voci ?? []).map((v) => ({
      nome: String(v.name ?? "?"), cartella: v.type === "dir",
    }));
    percorso.textContent = String(m.path ?? "—");
    const n = m.totale ?? fileVisti.length;
    percorsoCorto.textContent = `${n} ${n === 1 ? "voce" : "voci"}`;
    if (attiva === "file") disegna();
  });



  bus.su("agent.mesh", (m) => {
    const nodo = (m.nodi ?? []).find((n) => n.id === "t2");
    stato.textContent = `T2 ${nodo?.stato ?? "inerte"}`;
  });

  window.addEventListener("resize", () => { limita(); misuraTacca(); });

  apri("moduli");

  return {
    el, ancora,
    get attiva() { return attiva; },
    get scorrimento() { return x; },
    apri, scorriDi, disegna,
    altezza: () => Math.round(el.getBoundingClientRect().height),
  };
}
