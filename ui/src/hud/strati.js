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
/* ⚠️ --cy-700 (L 100), e ci sono voluti due giri e due misure.
   Con --cy-800 (L 74) il profilo si fermava a 45 dove il riferimento sta a
   100; con --cy-600 (L 142) e' salito a 135-158 dove il riferimento sta a
   88-117 — troppo, dall'altra parte. --cy-700 cade dentro la forbice misurata.
   E' la banda a fare la luce dell'HUD, non il centro. */
/* ⚠️ --cy-600: e' l'ultima superficie ampia che stava sotto il secchio dei
   chiari di §5 (L>120), e con lei l'entropia arriva a soglia. La progressione
   e' misurata un passo per volta — 2,37 con le linee dei quadranti, 2,38 con
   quelle del tecnico, 2,39 con le corone di L8, e questa e' l'ultima.
   Nessuna di queste righe schiarisce il CAMPO: i corridoi fra gli anelli
   restano scuri, che e' cio' che rende leggibile la struttura e insieme cio'
   che tiene alta la varianza. Si alza l'inchiostro, non il fondo. */
.hud__campoFascia { stroke: none; fill: var(--cy-600); }

/* ⚠️ LA GERARCHIA È SOLO LUMINOSITÀ, mai tinta — è la regola d'oro misurata
   sul riferimento: un solo hue, ciano. Ogni strato prende il proprio gradino
   dalla rampa, e il più esterno non è il più chiaro: il più chiaro è L3, che
   il riferimento chiama «il più luminoso dell'HUD». */
/* ⚠️ Il mirino sta SOTTO il nome, e deve cedergli il passo. Sul campo acceso
   i suoi due gradini precedenti facevano un grumo chiaro proprio dove cadono le
   lettere centrali: il nome e' la prima cosa che il riferimento fa leggere, e
   un reticolo che gli compete lo cancella. */
/* ⚠️ --cy-700 SUL RETICOLO, e non e' un ripensamento estetico: e' il
   meccanismo con cui §25.13.5 si chiude senza artefatti. Il criterio misura il
   composito sotto i tratti del nome, e sotto il nome c'e' L1. A --cy-900 il
   reticolo aveva lo stesso valore del suo fondo — invisibile, e composito
   fermo a L 48, contrasto 7,56:1 contro un tetto di 5,0. Le alternative che ho
   provato e scartato: un disco chiaro sotto il nome passa la misura (4,10:1,
   8 stati su 9) ma mette al centro una macchia pallida che il riferimento non
   ha; scurire l'inchiostro lo porta sotto il gradino che §25.13.2 gli assegna.
   Il reticolo alza il composito ED e' un dettaglio che il riferimento mostra:
   e' l'unico rimedio che non paga in fedelta'. */
[data-strato="mirino"] .hud__linea { stroke: var(--cy-700); }
[data-strato="mirino"] .hud__costruzione { stroke: var(--cy-800); }
[data-strato="logo"] .hud__linea { stroke: var(--cy-600); }
/* ⚠️ --cy-500 e non --cy-200: il picco misurato era 155 contro i 117 del
   riferimento. Resta l'anello piu' luminoso dell'HUD — che e' cio' che il
   riferimento gli chiede — ma alla luminanza giusta. */
[data-strato="segmentato"] .hud__fascia { fill: var(--cy-500); }
[data-strato="segmentato"] .hud__linea { stroke: var(--cy-700); }
/* ⚠️ UN GRADINO PIU' CHIARO SULLE LINEE DEI QUADRANTI E DEL TECNICO, e la
   misura che lo chiede e' §5 della densita'.
   Il nucleo nuovo riempie MENO del vecchio: contro il commit 18b2e58,
   riempito 28,0 -> 26,6 %, devStd 34,9 -> 34,3, ed entropia 2,43 -> 2,37,
   cioe' sotto la soglia di 2,40 che prima era verde. Il nucleo vecchio erano
   cinque anelli chiari su nero — un istogramma con due gobbe lontane; questo
   ha molta piu' struttura ma quasi tutta in una banda media, e una banda sola
   e' poca entropia.
   La cura che serve anche alla REPLICA e' la stessa: linee piu' chiare sopra
   corridoi che restano scuri. Il riferimento e' fatto cosi' — tratti netti su
   nero, non una massa uniforme. Il campo NON si tocca: schiarirlo alzerebbe il
   riempimento e abbasserebbe la varianza, che e' il contrario. */
[data-strato="quadranti"] .hud__linea { stroke: var(--cy-600); }
[data-strato="quadranti"] .hud__costruzione { stroke: var(--cy-800); }
/* ⚠️ --cy-700 e non --cy-500: misurato, al 51-57 % del raggio il mio
   profilo stava a 133 contro i 70-95 del riferimento, e questi due archi
   erano la causa — coprono 140 gradi di circonferenza, quindi pesano sulla
   media molto piu' di quanto sembrino. */
[data-strato="vetro"] .hud__fascia { fill: var(--cy-600); }
[data-strato="vetro"] .hud__linea { stroke: var(--cy-600); }
[data-strato="tecnico"] .hud__linea { stroke: var(--cy-600); }
[data-strato="tecnico"] .hud__costruzione { stroke: var(--cy-800); }

/* Il campo di L6: il riferimento lo misura all-8 % di opacità. È una
   superficie e non un tratto, quindi ha area e pesa: resta il gradino più
   scuro della rampa. */
.hud__campo { fill: var(--cy-900); stroke: none; }
/* Il campo sotto il nome: un gradino sotto il campo generale, e non è un
   ripiego — nel riferimento il centro è più scuro di tutto ciò che gli sta
   attorno, ed è esattamente ciò che un nome chiede al proprio fondo. */
/* La luce del centro. Sostituisce il campo scuro che stava sotto il nome: nel
   riferimento il centro e' acceso, non spento. */
.hud__centro-luce { fill: url(#hud-centro); stroke: none; }
/* La fascia esterna, sotto la corona esadecimale: quasi il pavimento. Nel
   riferimento quel testo sta su un fondo scurissimo, ed è ciò che lo fa
   leggere come inciso invece che come stampato sopra. */
.hud__campo--bordo { fill: var(--bg-panel); }
/* ⚠️ GLI SPESSORI SONO IN UNITA' DI VIEWBOX, e il fattore e' 0,318.
   La prima stesura della ghiera aveva stroke-width 1,5, che sembra un filo
   sottile e alla resa vera e' 0,48 px: mezzo pixel, cioe' niente. Reso e
   guardato, la ghiera non c'era. Il minimo utile e' 1 px pieno, quindi 3,2
   unita'; qui si sta a 4 per i fili e a 3 per le tacche fitte, che il
   riferimento tiene piu' leggere dei fili.
   E' la stessa specie del difetto delle corone di L8: una quota scritta in
   unita' e mai riportata alla scala a cui si guarda. */
.hud__ghiera-campo { fill: var(--bg-void); stroke: none; }
.hud__ghiera-filo { fill: none; stroke: var(--cy-700); stroke-width: 4; }
.hud__ghiera-tacca { stroke: var(--cy-800); stroke-width: 3; }
/* ⚠️ --cy-600 e non --cy-500: le due tacche cardinali orizzontali cadono alla
   stessa altezza del marchio, e a --cy-500 erano abbastanza chiare da leggersi
   come il PROLUNGAMENTO della scritta — un frego che attraversa J.A.R.V.I.S.
   da parte a parte. Misurato sulla riga y-1 dello scatto: (62,172,184) contro
   un fondo di (14,20,24) due righe sopra. Restano le piu' forti della ghiera,
   che e' il loro compito, ma sotto la scritta. */
.hud__ghiera-tacca--forte { stroke: var(--cy-600); stroke-width: 5; }
/* Un gradino sopra il bordo: e' il fondo su cui le tre corone di testo
   si staccano, non una fascia che si veda per conto suo. */
/* ⚠️ TORNATO A --bg-panel, e la ragione e' che la misura mi aveva ingannato.
   Alzando questo fondo a --cy-800 lo scarto medio dal profilo del riferimento
   e' sceso da 25,4 a 19,4 — e l'immagine e' PEGGIORATA: la corona e' diventata
   un disco teal uniforme con del testo sopra.
   Il profilo radiale e' una misura a UNA dimensione: dice la media a ogni
   raggio, non il contrasto fra bande adiacenti. Cio' che fa leggere il
   riferimento come anelli impilati sono i VUOTI SCURI fra le fasce, e
   riempiendoli si guadagna sulla media e si perde l'oggetto.
   La metrica resta un controllo; non e' un bersaglio. */
.hud__campo--corona { fill: var(--bg-panel); }

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
/* Le icone: line-art, cioe' contorno e niente riempimento. Spente stanno al
   gradino del reticolo — ci sono, non chiamano; accese salgono a --cy-200 come
   la lancetta e i picchi dell'onda, che sono le altre due cose del nucleo che
   dicono «adesso». */
.hud__icona-tratto {
  fill: none;
  /* --cy-700 e non --cy-800: guardato allo scatto, al gradino sotto le icone
     spente non si leggevano affatto — e un simbolo che non si vede non dice
     nemmeno «no». La distinzione fra spento e acceso la fanno il gradino E il
     peso del tratto, che sono due segnali invece di uno. */
  stroke: var(--cy-700);
  stroke-width: var(--line-hair);
  vector-effect: non-scaling-stroke;
  stroke-linejoin: round;
}
.hud__icona[data-acceso="si"] .hud__icona-tratto {
  stroke: var(--cy-200);
  stroke-width: var(--line-base);
}

.hud__lancetta-gambo {
  stroke: var(--cy-200);
  stroke-width: var(--line-base);
  vector-effect: non-scaling-stroke;
  fill: none;
}
.hud__lancetta-punta { fill: var(--cy-200); stroke: none; }

/* ⚠️ --cy-600 e non --cy-700, per due ragioni che vanno nella stessa
   direzione. Il riferimento: nella foto la corona alfanumerica e' una delle
   cose che si leggono meglio, non un fondo. La densita': le tre corone di L8
   sono la superficie di testo piu' estesa del nucleo, e a --cy-700 (L 99,6)
   stavano tutte appena SOTTO il secchio dei chiari che §5 conta a L>120 —
   migliaia di pixel che non contavano ne' come scuro ne' come chiaro.
   Resta sotto il tetto di §25.5, che e' --cy-500. */
.hud__hex {
  font-family: var(--font-mono);
  fill: var(--cy-600);
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
  vetro: (s) => ({ su: s.r[1], spessore: s.r[1] - s.r[0],
                   spessoreCampo: s.campoSpessore,
                   segmenti: s.archiSolidi, campo: s.campoPieno }),
  quadranti: (s) => ({ ...s.fasciaCampo, campo: true, segmenti: [] }),
  globo: (s) => ({ ...s.fasciaCampo, campo: true, segmenti: [] }),
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
  /* ⚠️ LA GHIERA, e serve a CHIUDERE lo strumento.
   *
   * Il corpo del disco finisce a 460 unita' su 512, quindi l'ultimo 10 % del
   * viewBox restava pagina vuota e la corona alfanumerica galleggiava sul
   * fondo: reso e guardato il 1º settembre 2026, il nucleo leggeva come un
   * disegno appoggiato invece che come un oggetto con un bordo. Nel
   * riferimento quella fascia c'e' ed e' scura, e il testo esadecimale sta
   * DENTRO di lei.
   * Non allarga l'ingombro di un pixel: il viewBox e' sempre 1024 e il posto
   * era gia' suo. Le due tacche lunghe ai poli orizzontali sono i riferimenti
   * di lettura del riferimento, non decorazione: danno un alto e un basso a
   * un oggetto che gira. */
  svg.appendChild(el("circle", {
    class: "hud__ghiera-campo", cx: CENTRO, cy: CENTRO, r: 500,
  }));
  for (let a = 0; a < 360; a += 5) {
    const rad = (a - 90) * Math.PI / 180;
    const cardinale = a % 90 === 0;
    const dentro = cardinale ? 466 : 472;
    svg.appendChild(el("line", {
      class: "hud__ghiera-tacca" + (cardinale ? " hud__ghiera-tacca--forte" : ""),
      x1: CENTRO + Math.cos(rad) * dentro, y1: CENTRO + Math.sin(rad) * dentro,
      x2: CENTRO + Math.cos(rad) * 482, y2: CENTRO + Math.sin(rad) * 482,
    }));
  }
  for (const r of [464, 496]) {
    svg.appendChild(el("circle", {
      class: "hud__ghiera-filo", cx: CENTRO, cy: CENTRO, r,
    }));
  }
  svg.appendChild(el("circle", {
    class: "hud__campo hud__campo--bordo", cx: CENTRO, cy: CENTRO,
    r: l8.r[1],
  }));
  /* ⚠️ LA CORONA ESTERNA E' LUMINOSA NEL RIFERIMENTO, e la mia era buia.
   *
   * Misurato sul profilo radiale: fra il 69 % e l'88 % del raggio il
   * riferimento sta fra 60 e 100, mentre il mio stava fra 30 e 43. E' la zona
   * delle bande di micro-testo, e li' la luce non viene da una superficie: la
   * fanno le MIGLIAIA di caratteri, che a distanza si fondono in un grigio
   * chiaro.
   *
   * Una superficie piena non basterebbe e sarebbe anche sbagliata: leggerebbe
   * come un anello dipinto invece che come dati. Serve il testo, e serve DENSO
   * — vedi `montaHex`, che da oggi monta tre corone invece di una. La
   * superficie qui sotto e' solo il gradino su cui quel testo si stacca. */
  svg.appendChild(el("circle", {
    class: "hud__campo hud__campo--corona", cx: CENTRO, cy: CENTRO,
    r: l8.r[1] - 6,
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
  /* ⚠️ IL CENTRO E' LUMINOSO, e sfuma verso il bordo. E' la cosa che piu' di
   * ogni altra fa somigliare il nucleo al riferimento, e per due giri l'avevo
   * al contrario: il mio centro era la parte PIU' SCURA.
   *
   * Nel riferimento il disco e' un campo teal acceso al centro che si spegne
   * verso la corona esterna. Non e' un cerchio pieno con sopra dei contorni:
   * e' una sorgente, e gli anelli ci stanno DENTRO.
   *
   * ⚠️ **E' la deroga 6, dichiarata in NUCLEO-HUD.md.** §25.5 capa il
   * riempimento del nucleo, e una sfumatura che al centro arriva a --cy-600
   * (L 142) sfonda quel tetto su una superficie grande. Il vincolo che quella
   * riga difende — il nucleo non compete col dato — resta tenuto da cio' che
   * NON sale: --cy-100 (L 231), il livello del testo dei pannelli, resta
   * vietato, e un test lo conta.
   *
   * Le fermate sono token, non colori: `stop-color` accetta `var()`, e senza
   * questo l'invariante 18 cadrebbe proprio dove si vede di piu'. */
  const l3 = STRATI.find((s) => s.id === "segmentato");
  const l6r = STRATI.find((s) => s.id === "vetro").r[1];
  /* ⚠️ IL CENTRO NON E' UNA SORGENTE, e il giro precedente aveva esagerato.
   *
   * Misurato sul profilo radiale del riferimento, il centro (r < 20 %) sta fra
   * L 30 e 60, con una punta a 75. Il mio, con la sfumatura, stava a 75-90: piu'
   * chiaro del riferimento, e per giunta monotono.
   *
   * Nel riferimento **le cose luminose sono gli ANELLI**, non il centro: il
   * profilo oscilla — banda chiara, banda scura, banda chiara — con i picchi
   * (110-117) fra il 46 % e il 69 % del raggio. Un centro acceso con una rampa
   * che scende produce un ALONE con dei cerchi sopra; le bande alternate
   * producono anelli impilati, che e' l'oggetto.
   *
   * La sfumatura resta, ma stretta e scura: serve a staccare il campo del nome
   * dal fondo, non a illuminarlo. */
  const defsC = el("defs");
  const grad = el("radialGradient", {
    id: "hud-centro", cx: "50%", cy: "50%", r: "50%",
  });
  /* ⚠️ LA FERMATA E' AL 58 %, E LE LETTERE FINISCONO AL 51 %. Non e' un
   * arrotondamento: §25.13.5 misura il composito sotto i tratti, e con la
   * caduta che cominciava a 0 % le due estremita' del nome — la «J» e la «S» —
   * arrivavano gia' su --bg-panel (L 31) mentre il centro stava su --cy-900
   * (L 48). Il contrasto saliva a 8,4:1 contro un tetto di 5,0, e il rimedio
   * che avevo provato — un disco chiaro sotto il nome — faceva passare la
   * misura e comparire una macchia pallida al centro che il riferimento non
   * ha. Tenere --cy-900 fino a oltre le lettere e' la stessa correzione senza
   * l'artefatto: il fondo del nome torna uniforme a L 48, che e' il valore su
   * cui la forbice si era chiusa a 4,65:1. */
  grad.appendChild(el("stop", { offset: "0%", "stop-color": "var(--cy-900)" }));
  grad.appendChild(el("stop", { offset: "58%", "stop-color": "var(--cy-900)" }));
  grad.appendChild(el("stop", { offset: "100%", "stop-color": "var(--bg-panel)" }));
  defsC.appendChild(grad);
  svg.appendChild(defsC);
  svg.appendChild(el("circle", {
    class: "hud__centro-luce", cx: CENTRO, cy: CENTRO,
    r: STRATI.find((s) => s.id === "vetro").r[1],
  }));
  /* ⚠️ IL CAMPO SOTTO IL NOME sta a mezza luminanza, e non e' una scelta di
   * stile: e' l'unico modo di avere insieme le due cose che il riferimento
   * mostra e il criterio pretende.
   *
   * Il riferimento fa il nome quasi bianco. Su un campo scuro quel bianco da'
   * 8,4:1, e §25.13.5 capa a 5,0 — il tetto esiste perche' un marchio piu'
   * contrastato del testo dei pannelli compete col dato. Abbassare il nome lo
   * allontana dal riferimento; alzare TUTTO il centro sfonda l'altro vincolo,
   * la luminanza media (misurato: 110 contro 105).
   *
   * Un disco piccolo e chiaro solo dove cadono le lettere risolve entrambi:
   * il contrasto scende perche' il fondo sale, e la luminanza media del
   * ritaglio resta bassa perche' la superficie chiara e' piccola. Ed e' cio'
   * che il riferimento mostra — il centro e' piu' chiaro dei corridoi che lo
   * circondano, non di tutto il disco. */

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
  // Le icone per ultime: sono simboli, e un simbolo sotto un quadrante non si
  // legge.
  const icone = montaIcone(svg);

  return { gruppi, ruote, scatti, accesi, vertici, lancetta, icone, testoHex: null };
}

/* ⚠️ LE QUATTRO ICONE — line-art, e nessuna e' un ParametricComponent.
 *
 * Vale la stessa ragione della lancetta: §11.10 governa le GEOMETRIE generate,
 * con densita' derivata dalla curvatura e bounding box da verificare. Un chip
 * e' un rettangolo e sei trattini. Non c'e' curvatura da discretizzare, e il
 * gate lo dice da se' — il suo pavimento e' 24 vertici.
 *
 * Cio' che conta si tiene lo stesso: **ogni forma e' una frazione di `lato`**,
 * mai un numero battuto qui. Un'icona con dentro un `12` smetterebbe di
 * combaciare col resto al primo cambio di scala, e nessuno se ne accorgerebbe
 * finche' non la guarda da vicino.
 *
 * Il vocabolario e' quello del riferimento: tratti sottili, angoli retti,
 * nessun riempimento. Line-art vuol dire che si legge per contorno.
 */
const ICONE = {
  /** Il chip: un quadrato con i piedini. Dice che un agente sta lavorando. */
  chip: (l) => {
    const m = l * 0.34;                     // mezzo lato del corpo
    const p = l * 0.16;                     // quanto sporge un piedino
    const d = [`M${-m},${-m} L${m},${-m} L${m},${m} L${-m},${m} Z`];
    // Tre piedini per lato, alle quote 1/4, 1/2, 3/4 — cosi' restano
    // equidistanti a qualunque `lato`.
    for (const k of [-0.5, 0, 0.5]) {
      const q = m * k * 1.2;
      d.push(`M${-m},${q} L${-m - p},${q}`, `M${m},${q} L${m + p},${q}`,
             `M${q},${-m} L${q},${-m - p}`, `M${q},${m} L${q},${m + p}`);
    }
    // Il quadratino interno: e' cio' che lo fa leggere come un chip e non come
    // una scatola.
    d.push(`M${-m * 0.4},${-m * 0.4} L${m * 0.4},${-m * 0.4} L${m * 0.4},${m * 0.4} L${-m * 0.4},${m * 0.4} Z`);
    return d.join("");
  },

  /** Il triangolo di avviso, con la barra. Dice che c'e' qualcosa da guardare. */
  avviso: (l) => {
    const m = l * 0.5;
    return `M0,${-m} L${m},${m * 0.72} L${-m},${m * 0.72} Z` +
           `M0,${-m * 0.34} L0,${m * 0.2}` +
           `M0,${m * 0.42} L0,${m * 0.48}`;
  },

  /** Il satellite: corpo, due pannelli, e l'onda che scende. Dice che il core
   *  risponde — e l'onda e' la parte che lo dice, non il corpo. */
  satellite: (l) => {
    /* ⚠️ RIDISEGNATO dopo lo scatto: la prima stesura aveva corpo, due pannelli
       e due archi in venticinque unità, e a schermo era un grumo di rettangoli.
       Un'icona a questa scala regge tre tratti, non sette. Restano il corpo, i
       pannelli come DUE LINEE — non due scatole — e un arco solo. */
    const c = l * 0.16, w = l * 0.48;
    return `M${-c},${-c} L${c},${-c} L${c},${c} L${-c},${c} Z` +
           `M${-w},${-c * 1.6} L${-c},${-c * 1.6}` +
           `M${-w},${c * 1.6} L${-c},${c * 1.6}` +
           `M${w},${-c * 1.6} L${c},${-c * 1.6}` +
           `M${w},${c * 1.6} L${c},${c * 1.6}` +
           `M${-l * 0.3},${l * 0.42} A${l * 0.42},${l * 0.42} 0 0 0 ${l * 0.3},${l * 0.42}`;
  },

  /** Il distintivo: uno scudo. Dice che il microfono e' aperto. */
  badge: (l) => {
    const m = l * 0.42;
    return `M0,${-m} L${m},${-m * 0.5} L${m},${m * 0.3} L0,${m} L${-m},${m * 0.3} L${-m},${-m * 0.5} Z` +
           `M${-m * 0.4},0 L${-m * 0.12},${m * 0.36} L${m * 0.45},${-m * 0.34}`;
  },
};

/** Monta le quattro icone cardinali di L8.
 *
 * ⚠️ **NON RUOTANO CON L'ANELLO**, e non e' un dettaglio: un'icona capovolta
 * non e' piu' un'icona. Nel riferimento stanno dritte, e ci stanno perche' sono
 * simboli e non decorazione radiale. Ognuna ha il proprio gruppo, traslato al
 * proprio punto cardinale e mai ruotato.
 *
 * L'angolo e' in radianti ORARI DAL VERTICE — vedi la tabella. La conversione
 * sta qui in un posto solo: `(sin a, -cos a)`, che con la y in giu' dell'SVG
 * mette lo zero in alto.
 */
export function montaIcone(svg) {
  const s = STRATI.find((x) => x.id === "hex");
  // Le icone stanno fra le due guide di L8, dove il riferimento le mette: la
  // corona esadecimale corre piu' dentro, e non si accavallano.
  const raggio = (s.r[0] + s.r[1]) / 2;
  //: Il lato dell'icona: una frazione della fascia che la contiene, non un
  //: numero. La fascia e' larga (460 - 384) = 76 unita', e un simbolo che ne
  //: occupa i due terzi si legge senza toccare i bordi.
  const lato = (s.r[1] - s.r[0]) * 0.66;

  const fuori = new Map();
  for (const ic of s.icone) {
    const disegna = ICONE[ic.nome];
    if (!disegna) throw new Error(`icona senza disegno: ${ic.nome}`);
    const x = CENTRO + Math.sin(ic.a) * raggio;
    const y = CENTRO - Math.cos(ic.a) * raggio;
    const g = el("g", {
      class: "hud__icona",
      "data-icona": ic.nome,
      "data-chi": ic.chi,
      transform: `translate(${x.toFixed(2)} ${y.toFixed(2)})`,
    });
    g.appendChild(el("path", { class: "hud__icona-tratto", d: disegna(lato) }));
    svg.appendChild(g);
    fuori.set(ic.chi, g);
  }
  return fuori;
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
  const raggi = s.guideTesto ?? [s.guidaTesto];

  const defs = el("defs");
  const nodi = [];
  for (const [k, r] of raggi.entries()) {
    const id = `hud-guida-hex-${k}`;
    // Due semiarchi: un cerchio intero in un comando solo non esiste in SVG.
    defs.appendChild(el("path", {
      id,
      d: `M${CENTRO - r},${CENTRO} a${r},${r} 0 1,1 ${2 * r},0 a${r},${r} 0 1,1 ${-2 * r},0`,
      fill: "none",
    }));
    const testo = el("text", {
      class: k === 2 ? "hud__hex" : "hud__hex hud__hex--minore",
      "aria-hidden": "true",
    });
    testo.style.fontSize = gradino("--t-micro", diametroPx).toFixed(1);
    const tp = document.createElementNS(NS, "textPath");
    tp.setAttribute("href", `#${id}`);
    tp.setAttribute("startOffset", "0");
    testo.appendChild(tp);
    svg.appendChild(testo);
    nodi.push({ tp, testo, r });
  }
  svg.insertBefore(defs, svg.firstChild);

  return {
    /* La corona di mezzo resta il portante principale: e' quella che
       `desk/sfondo.js` gia' pilota, e cambiarne il nome avrebbe rotto il
       chiamante per un guadagno nullo. */
    nodo: nodi[Math.min(2, nodi.length - 1)].tp,
    /** Tutte e tre, per chi le vuole riempire con blocchi diversi. */
    nodi: nodi.map((n) => n.tp),
    capienza: (px) => caratteriSulGiro(raggi[Math.min(2, raggi.length - 1)],
                                       gradino("--t-micro", px), 0.04),
    /** La capienza di ciascuna: i raggi sono diversi, e i caratteri pure. */
    capienze: (px) => raggi.map((r) =>
      caratteriSulGiro(r, gradino("--t-micro", px), 0.04)),
    ridimensiona: (px) => {
      for (const n of nodi) n.testo.style.fontSize = gradino("--t-micro", px).toFixed(1);
    },
  };
}

export { RAGGIO_MAX, VIEWBOX };
