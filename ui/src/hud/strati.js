/* Dalla geometria all'SVG — gli otto strati dell'HUD.
 *
 * Questo file DISEGNA e non decide: i raggi, le velocità e i dettagli stanno
 * in `geometria.js`, i corpi del testo li calcola `tipografia.js`, i colori
 * escono dai token. Qui c'è solo il montaggio.
 *
 * ## Perché SVG e non canvas
 *
 * Sono forme piatte che devono restare nitide a qualunque scala, e SVG le
 * tiene vettoriali fino al rasterizzatore. Un canvas le cuocerebbe a una
 * risoluzione, e il testo dell'anello L8 smetterebbe di essere testo —
 * invariante 20.
 *
 * ## I gruppi, e perché sono tre per strato
 *
 *     [data-strato]     l'opacità della FASE — chi la tocca è uno solo
 *       .hud__ruota     la rotazione — idem
 *         .hud__base    la geometria a riposo
 *         .hud__acceso  la stessa geometria, sopra, a opacità zero
 *
 * Una proprietà, un padrone. È la regola che questo progetto ha già pagato due
 * volte con animazioni che si sovrascrivevano a vicenda senza dire niente.
 */

import { HudQuadrante } from "../three/components/hud-quadrante.js";
import { qualityGate } from "../three/quality-gate.js";
import { versoPath } from "../three/svg.js";
import { CENTRO, RAGGIO_MAX, STRATI, VIEWBOX } from "./geometria.js";
import { caratteriSulGiro, gradino } from "./tipografia.js";

const NS = "http://www.w3.org/2000/svg";

function el(nome, attributi = {}) {
  const e = document.createElementNS(NS, nome);
  for (const [k, v] of Object.entries(attributi)) e.setAttribute(k, String(v));
  return e;
}

export const css = `
.hud__svg {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: block;
  overflow: visible;
}
/* I tre pesi di §11.8, e non un quarto. non-scaling-stroke tiene il tratto in
   pixel di schermo: un hairline che scalasse col viewBox sparirebbe a finestra
   piccola e diventerebbe un bordo a finestra grande. */
.hud__linea, .hud__costruzione {
  vector-effect: non-scaling-stroke;
  fill: none;
}
.hud__linea { stroke-width: var(--line-base); }
.hud__costruzione { stroke-width: var(--line-hair); }
/* La fascia è una SUPERFICIE: ha area, e per questo pesa più di un tratto.
   Nessun contorno sopra — un bordo su una superficie piena la fa leggere come
   una targa incollata invece che come un pezzo dell'oggetto. */
.hud__fascia { stroke: none; }
/* Il campo di una fascia: la superficie sotto i segmenti. Un gradino sotto di
   loro e uno sopra il campo generale — sono tre livelli, e il riferimento li
   ha tutti e tre. */
/* ⚠️ --cy-700 (L 100) e non --cy-800 (L 74), e il numero l'ha scelto una
   MISURA. Col gradino più scuro il nucleo scendeva a entropia 2,34 contro la
   soglia di 2,40, e il riferimento non è d'accordo: il suo profilo radiale
   tocca **L 110-117** sulle bande, non 74. Un nucleo di superfici scure legge
   come un disegno tecnico — che è la cosa che §11.8 CONTENUTO chiede di non
   fare. */
.hud__campoFascia { stroke: none; fill: var(--cy-700); }

/* ⚠️ LA GERARCHIA È SOLO LUMINOSITÀ, mai tinta — è la regola d'oro misurata
   sul riferimento: un solo hue, ciano. Ogni strato prende il proprio gradino
   dalla rampa, e il più esterno non è il più chiaro: il più chiaro è L3, che
   il riferimento chiama «il più luminoso dell'HUD». */
[data-strato="mirino"] .hud__linea { stroke: var(--cy-800); }
[data-strato="mirino"] .hud__costruzione { stroke: var(--cy-700); }
[data-strato="logo"] .hud__linea { stroke: var(--cy-600); }
[data-strato="segmentato"] .hud__fascia { fill: var(--cy-200); }
[data-strato="segmentato"] .hud__linea { stroke: var(--cy-700); }
[data-strato="quadranti"] .hud__linea { stroke: var(--cy-700); }
[data-strato="quadranti"] .hud__costruzione { stroke: var(--cy-800); }
[data-strato="vetro"] .hud__fascia { fill: var(--cy-500); }
[data-strato="vetro"] .hud__linea { stroke: var(--cy-700); }
[data-strato="tecnico"] .hud__linea { stroke: var(--cy-800); }
[data-strato="tecnico"] .hud__costruzione { stroke: var(--cy-800); }

/* Il campo di L6: il riferimento lo misura all-8 % di opacità. È una
   superficie e non un tratto, quindi ha area e pesa: resta il gradino più
   scuro della rampa. */
.hud__campo { fill: var(--cy-900); stroke: none; }
/* Il campo sotto il nome: un gradino sotto il campo generale, e non è un
   ripiego — nel riferimento il centro è più scuro di tutto ciò che gli sta
   attorno, ed è esattamente ciò che un nome chiede al proprio fondo. */
.hud__campo--nome { fill: var(--bg-panel); }
/* La fascia esterna, sotto la corona esadecimale: quasi il pavimento. Nel
   riferimento quel testo sta su un fondo scurissimo, ed è ciò che lo fa
   leggere come inciso invece che come stampato sopra. */
.hud__campo--bordo { fill: var(--bg-panel); }

/* Le linee di costruzione — assi e quote — non sono decorazione: dicono
   rispetto a che cosa un quadrante è graduato. Stanno un gradino sotto la
   propria geometria, sempre. */
.hud__assi { stroke: var(--cy-900); stroke-width: var(--line-hair); fill: none;
             vector-effect: non-scaling-stroke; }

/* Lo strato acceso: la stessa geometria sopra, tenuta a zero finché una causa
   non la chiama. Una sola opacità da animare, invece di un colore — che
   anime.js non interpola dentro una stroke. */
.hud__acceso { opacity: 0; }
.hud__acceso .hud__linea { stroke: var(--cy-200); }
.hud__acceso .hud__costruzione { stroke: var(--cy-500); }
.hud__acceso .hud__fascia { fill: var(--cy-200); }

/* Il testo sull'anello L8 e le letture. Monospaziato, come ogni numero del
   progetto — §11.6 regola 1. Il corpo lo scrive JS in unità di viewBox, perché
   dentro un viewBox un font-size in px non è in px: vedi tipografia.js. */
/* La lancetta è la cosa più chiara di L6, e deve esserlo: è un indicatore, e
   un indicatore che non stacca dal proprio quadrante non indica. Sta a
   --cy-200 come i picchi dell'onda — sono le due cose del nucleo che dicono
   «adesso», e §25.5 le ammette a quel gradino per deroga dichiarata. */
.hud__lancetta-gambo {
  stroke: var(--cy-200);
  stroke-width: var(--line-base);
  vector-effect: non-scaling-stroke;
  fill: none;
}
.hud__lancetta-punta { fill: var(--cy-200); stroke: none; }

.hud__hex {
  font-family: var(--font-mono);
  fill: var(--cy-700);
  stroke: none;
  letter-spacing: 0.16em;
  user-select: none;
  pointer-events: none;
}
`;

/* ⚠️ Quali strati sono un QUADRANTE e quali no.
 *
 * Il globo è three.js (F4) e l'anello esadecimale è testo: nessuno dei due
 * passa da `HudQuadrante`. Gli altri sei sì, ed è dichiarato qui invece che
 * dedotto da un campo, perché «questo strato è fatto così» è una scelta di
 * composizione e va letta in un colpo d'occhio. */
const FASCE = {
  segmentato: (s) => ({ su: s.r[0], spessore: s.fascia, dash: s.dash }),
  vetro: (s) => ({ su: s.r[1], spessore: s.r[1] - s.r[0], segmenti: s.archiSolidi,
                   campo: s.campoPieno }),
  quadranti: (s) => ({ ...s.fasciaCampo, campo: true, segmenti: [] }),
  tecnico: (s) => ({ ...s.fasciaCampo, campo: true, segmenti: [] }),
};
/* Solo `hex` non è un quadrante: porta TESTO, e il testo non si genera con
   una tabella di raggi. Il globo sì — la sua graduazione è piatta, e i punti
   3D che F4 gli mette dentro sono un'altra cosa che vive in un altro strato. */
const NON_QUADRANTI = new Set(["hex"]);

/** Costruisce gli strati SVG dentro `svg`. Non anima niente.
 *
 * @returns {{gruppi: Map, ruote: Map, accesi: Map, testoHex: SVGElement|null,
 *            vertici: number}}
 */
/* ⚠️ IL BAGLIORE — la deroga 1, e va montata in un posto solo.
 *
 * L'invariante 19 dice «ZERO glow, ZERO bloom, ZERO alone luminoso», e §11.6
 * regola 5 la ripete: «la luminosità viene dal contrasto contro il nero. Il
 * momento in cui aggiunge un `filter: drop-shadow` o un bloom, scivola nella
 * Famiglia B». Il proprietario ha derogato: il riferimento HUD ha il bagliore,
 * e senza non è quel riferimento.
 *
 * ⚠️ **L'AUDIT NON VEDE I FILTRI SVG, e questo è il pericolo vero.**
 * `gallery/audit.js` controlla la proprietà CSS `filter`; un
 * `filter="url(#glow)"` è un ATTRIBUTO SVG, e `getComputedStyle` risponde
 * `none`. Passerebbe in silenzio — che è peggio di essere bocciato, perché
 * domani qualcuno ne mette un secondo su un pannello e nessuno se ne accorge.
 *
 * Quindi il bagliore vive QUI, in una funzione sola, con un id solo, e
 * `tests/test_nucleo.py` conta quanti elementi lo usano. Una deroga che si può
 * contare è una deroga; una che si diffonde è un cambio di regola preso senza
 * deciderlo.
 *
 * La ricetta è quella misurata sul riferimento: `stdDeviation 3` su un viewBox
 * 1024, cioè lo 0,3 % del lato. Non è un alone largo — è il velo che stacca il
 * tratto dal fondo, e a occhio si legge come «acceso» invece che come «sfocato».
 */
const GLOW = "hud-glow";

function montaGlow(svg) {
  const defs = el("defs");
  const filtro = el("filter", {
    id: GLOW,
    // Il riquadro del filtro deve essere più largo dell'oggetto, o il velo
    // viene tagliato al bordo e si vede la cucitura.
    x: "-50%", y: "-50%", width: "200%", height: "200%",
    filterUnits: "objectBoundingBox",
  });
  const sfoca = el("feGaussianBlur", { in: "SourceGraphic", stdDeviation: 3, result: "velo" });
  const fondi = el("feMerge");
  // Il velo SOTTO e l'originale SOPRA: al contrario il tratto risulterebbe
  // sfocato invece che circondato, e §11.8 lo chiamerebbe blur indistinto.
  fondi.appendChild(el("feMergeNode", { in: "velo" }));
  fondi.appendChild(el("feMergeNode", { in: "SourceGraphic" }));
  filtro.append(sfoca, fondi);
  defs.appendChild(filtro);
  svg.appendChild(defs);
}

/** Quanti elementi usano il bagliore. La deroga si CONTA — vedi il commento. */
export function contaGlow(radice) {
  return radice.querySelectorAll(`[filter="url(#${GLOW})"]`).length;
}

export function costruisci(svg, { acceso = true } = {}) {
  svg.setAttribute("viewBox", `0 0 ${VIEWBOX} ${VIEWBOX}`);
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  montaGlow(svg);

  const gruppi = new Map();
  const ruote = new Map();
  const scatti = new Map();
  const accesi = new Map();
  let vertici = 0;

  /* Il campo interno: la superficie sotto tutto, fino al bordo di L6. Senza,
     gli otto strati leggono come cerchi che galleggiano — è la stessa misura
     che il nucleo precedente aveva già fatto sul proprio riferimento: «fra una
     fascia e l'altra non c'è VUOTO, c'è una superficie più scura». */
  /* ⚠️ IL CORPO ARRIVA FIN SOTTO LA CORONA ESADECIMALE, e la prima stesura lo
   * fermava a L6 (r=301).
   *
   * Reso e guardato, l'anello di testo galleggiava nel vuoto a settanta unità
   * dal bordo del disco: nel riferimento quel testo sta SOPRA il corpo, che
   * arriva fino a lui. È lo stesso difetto che il nucleo precedente aveva già
   * pagato una volta — «il difetto dei nostri corridoi non era la larghezza:
   * era che si vedeva il pavimento attraverso».
   *
   * Due campi e non uno: la fascia esterna è più scura di quella interna,
   * perché nel riferimento il testo esadecimale sta su quasi-nero mentre i
   * quadranti stanno su un fondo acceso. Un campo unico o annerirebbe i
   * quadranti o schiarirebbe il testo. */
  const l8 = STRATI.find((s) => s.id === "hex");
  svg.appendChild(el("circle", {
    class: "hud__campo hud__campo--bordo", cx: CENTRO, cy: CENTRO,
    r: l8.r[1],
  }));
  svg.appendChild(el("circle", {
    class: "hud__campo", cx: CENTRO, cy: CENTRO,
    r: STRATI.find((s) => s.id === "vetro").r[1],
  }));

  /* ⚠️ IL CAMPO SOTTO IL NOME È PIÙ SCURO, e la ragione è il MARCHIO.
   *
   * Il campo generale sta a --cy-900 (L 48,5), che è il gradino giusto per una
   * superficie di fondo. Ma il nome ci vive sopra, e §25.13.5 gli chiede fra
   * 3,0:1 e 5,0:1 contro il composito. Misurato con il campo unico:
   *
   *     composito sotto il nome  L 64,5
   *     marchio --cy-700         2,18:1     NON PASSA — non si legge
   *
   * E non si può rispondere alzando il marchio: --cy-700 è il tetto di
   * §25.13.2 regola 4, e il gradino sopra (--cy-500) dà 5,95:1 — misurato, e
   * sfonda il TETTO di 5,0, cioè un marchio che compete col testo dei
   * pannelli. La forbice si raggiunge dal FONDO, non dalla scritta.
   *
   * È la stessa correzione che il nucleo precedente aveva già fatto una volta,
   * con le stesse parole e per lo stesso motivo. Il raggio è il bordo interno
   * di L3, cioè esattamente il limite entro cui il nome è dimensionato: le due
   * quote si derivano dallo stesso posto, o divergono. */
  const l3 = STRATI.find((s) => s.id === "segmentato");
  svg.appendChild(el("circle", {
    class: "hud__campo hud__campo--nome", cx: CENTRO, cy: CENTRO,
    r: l3.r[0] - l3.fascia,
  }));

  for (const s of STRATI) {
    /* ⚠️ TRE GRUPPI ANNIDATI, e ognuno ha UNA proprietà e un padrone solo.
     *
     *     posto    la traslazione al centro e l'opacità della FASE
     *       scatto la rotazione a SCATTI — L1 aggancia ogni ~6 s
     *         ruota la rotazione CONTINUA
     *
     * Due rotazioni sullo stesso nodo si sovrascriverebbero a vicenda senza
     * dire niente, e sarebbe la terza volta che questo progetto lo paga. Con
     * due gruppi si sommano, che è quello che serve: lo scatto è uno scarto
     * sopra un moto che continua. */
    const posto = el("g", { "data-strato": s.id, transform: `translate(${CENTRO} ${CENTRO})` });
    const scatto = el("g", { class: "hud__scatto" });
    scatto.style.transformOrigin = "0 0";
    const ruota = el("g", { class: "hud__ruota" });
    ruota.style.transformOrigin = "0 0";
    scatto.appendChild(ruota);
    posto.appendChild(scatto);
    svg.appendChild(posto);
    gruppi.set(s.id, posto);
    ruote.set(s.id, ruota);
    scatti.set(s.id, scatto);

    if (NON_QUADRANTI.has(s.id)) { accesi.set(s.id, null); continue; }

    const componente = new HudQuadrante({
      name: `hud-${s.id}`,
      raggi: s.r,
      tacche: s.tacche,
      tratteggio: s.tratteggio,
      archiParziali: s.archiParziali,
      varco: s.varco,
      fascia: FASCE[s.id] ? FASCE[s.id](s) : null,
    });
    const geometria = componente.build();
    // Il gate PRIMA del render — invariante 22. Solleva, e la galleria mostra
    // l'errore invece di uno strato sbagliato che sembra giusto.
    qualityGate(componente, geometria, ["linea", "costruzione"]);
    vertici += geometria.getAttribute("position").count;

    /* I tracciati si fondono per RUOLO: `versoPath` torna un `d` per gruppo, e
       centoquarantotto tacche sono centoquarantotto nodi. Un `d` può contenere
       più sottotracciati e il rasterizzatore li disegna identici. Su otto
       strati che ruotano a ogni fotogramma, la differenza è fra ~500 nodi e 16. */
    const perRuolo = new Map();
    for (const t of versoPath(geometria)) {
      // Tre ruoli e tre classi: contorno, dettaglio, superficie. Ridurli a due
      // è ciò che ha fatto uscire il nucleo come un disco pieno.
      const k = t.ruolo === "fascia" ? "fascia"
        : t.ruolo === "campo" ? "campoFascia"
        : t.ruolo === "linea" ? "linea" : "costruzione";
      perRuolo.set(k, (perRuolo.get(k) ?? "") + t.d);
    }
    const disegna = (dentro, suffisso) => {
      for (const [ruolo, d] of perRuolo)
        dentro.appendChild(el("path", { d, class: `hud__${ruolo}${suffisso}` }));
    };

    const base = el("g", { class: "hud__base" });
    disegna(base, "");
    /* Solo dove il riferimento lo mette: «glow forte» su L3, e sullo strato
       acceso di chiunque. Non su tutto — un bagliore ovunque non è un
       bagliore, è nebbia, ed è la Famiglia B con un altro nome. */
    if (s.glow) base.setAttribute("filter", `url(#${GLOW})`);
    ruota.appendChild(base);

    // Gli assi di costruzione stanno FUORI dalla rotazione: sono la quota
    // contro cui si legge il movimento, e una quota che gira non è una quota.
    const assi = componente.constructionLines();
    if (assi) {
      const g = el("g", { class: "hud__assi-g" });
      for (const t of versoPath(assi)) g.appendChild(el("path", { d: t.d, class: "hud__assi" }));
      posto.insertBefore(g, scatto);
    }

    if (acceso) {
      const sopra = el("g", { class: "hud__acceso" });
      disegna(sopra, "");
      // Lo strato ACCESO brilla sempre: è il segnale, ed è l'unico posto in cui
      // il bagliore porta un'informazione invece che un'atmosfera.
      sopra.setAttribute("filter", `url(#${GLOW})`);
      ruota.appendChild(sopra);
      accesi.set(s.id, sopra);
    } else {
      accesi.set(s.id, null);
    }
  }

  // La lancetta va DOPO gli strati: è un indicatore, e un indicatore che
  // finisse sotto il proprio quadrante non si vedrebbe.
  const lancetta = montaLancetta(svg);

  return { gruppi, ruote, scatti, accesi, vertici, lancetta, testoHex: null };
}

/** La lancetta di L6 — il marcatore che «cerca».
 *
 * ⚠️ NON è un `ParametricComponent`, ed è una scelta con una ragione, non una
 * scorciatoia. §11.10 governa le GEOMETRIE: forme generate, con una densità
 * derivata dalla curvatura e un bounding box da verificare. Una lancetta è due
 * vertici e un triangolo: non ha curvatura da discretizzare, e il gate lo dice
 * da sé — il suo pavimento è 24 vertici, e un componente che non può passarlo
 * per costruzione non è un componente.
 *
 * Quello che conta lo si tiene lo stesso: i raggi vengono dalla tabella, non
 * da numeri battuti qui. Il giorno che L6 si sposta, la lancetta lo segue.
 *
 * Il gruppo esterno esiste per la rotazione: una proprietà, un padrone. La
 * lancetta ruota, la punta no — e se ruotassero insieme sullo stesso nodo si
 * sovrascriverebbero, che è il difetto che questo progetto ha già pagato due
 * volte.
 */
export function montaLancetta(svg) {
  const s = STRATI.find((x) => x.id === "vetro");
  const [dentro, fuori] = s.r;

  const perno = el("g", {
    class: "hud__lancetta",
    transform: `translate(${CENTRO} ${CENTRO})`,
  });
  const ruota = el("g");
  ruota.style.transformOrigin = "0 0";

  // Il gambo: dal bordo interno della fascia a quello esterno. Verso l'alto,
  // perché è da lì che si contano gli angoli in questo HUD.
  ruota.appendChild(el("path", {
    class: "hud__lancetta-gambo",
    d: `M0,${-dentro} L0,${-fuori}`,
  }));
  /* La punta: un triangolo sul bordo esterno. Largo un ventesimo della fascia
     per lato — una frazione, non un numero: a Ø326 fa un paio di pixel, e su
     una finestra più grande cresce con tutto il resto. */
  const mezzo = (fuori - dentro) / 20;
  ruota.appendChild(el("path", {
    class: "hud__lancetta-punta",
    d: `M${-mezzo},${-fuori + mezzo * 2} L${mezzo},${-fuori + mezzo * 2} L0,${-fuori} Z`,
  }));

  perno.appendChild(ruota);
  svg.appendChild(perno);
  return ruota;
}

/** L'anello alfanumerico L8: un `textPath` su una guida circolare.
 *
 * ⚠️ Il corpo si dà in unità di viewBox e va ricalcolato a ogni resize: dentro
 * un viewBox `font-size: 8.5px` non fa 8,5 pixel. Vedi `tipografia.js`.
 *
 * ⚠️ Nasce VUOTO. Il contenuto lo scrive chi monta, dai numeri veri del bus —
 * invariante 23. Finché il core non ha parlato non c'è niente da leggere, e non
 * c'è niente scritto.
 */
export function montaHex(svg, diametroPx) {
  const s = STRATI.find((x) => x.id === "hex");
  const r = s.guidaTesto;
  const id = "hud-guida-hex";

  const defs = el("defs");
  // Due semiarchi: un cerchio intero in un comando solo non esiste in SVG.
  defs.appendChild(el("path", {
    id,
    d: `M${CENTRO - r},${CENTRO} a${r},${r} 0 1,1 ${2 * r},0 a${r},${r} 0 1,1 ${-2 * r},0`,
    fill: "none",
  }));

  const testo = el("text", { class: "hud__hex", "aria-hidden": "true" });
  testo.style.fontSize = gradino("--t-micro", diametroPx).toFixed(1);
  const tp = document.createElementNS(NS, "textPath");
  tp.setAttribute("href", `#${id}`);
  tp.setAttribute("startOffset", "0");
  testo.appendChild(tp);

  svg.append(defs, testo);
  return {
    nodo: tp,
    testo,
    /** Quanti caratteri stanno sul giro, alla dimensione resa. */
    capienza: (px) => caratteriSulGiro(r, gradino("--t-micro", px), 0.16),
    /** Il corpo va rifatto a ogni resize, o il testo cambia dimensione reale. */
    ridimensiona: (px) => {
      testo.style.fontSize = gradino("--t-micro", px).toFixed(1);
    },
  };
}

export { RAGGIO_MAX, VIEWBOX };
