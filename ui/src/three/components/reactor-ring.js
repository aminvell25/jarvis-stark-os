/* Anello reattore — SPEC §11.10, riferimento famiglia-a/12-logo-anelli-concentrici.
 *
 * Il riferimento e' il logo: anelli concentrici a centri SFALSATI, tick a
 * lunghezza variabile, un varco netto in uno degli anelli. Quel render ha il
 * glow; io prendo la forma e non il trattamento, come dice
 * docs/design-reference/README.md.
 *
 * Un componente = UN anello, centrato sull'origine. La composizione a quattro
 * anelli la fa `anim/rings.js`: cosi' ogni anello ha i suoi parametri, la sua
 * versione e passa il gate da solo. Un unico componente «gruppo di anelli»
 * avrebbe una tabella parametri con ventiquattro voci e un bounding box che
 * non dice piu' niente.
 *
 * I «centri sfalsati» del riferimento sono POSIZIONE, non forma: li mette la
 * composizione con una traslazione. Tenerli nella geometria vorrebbe dire che
 * ogni anello ruota attorno a un centro che non e' il proprio, e invece di
 * girare oscillerebbe.
 *
 * ── L'asimmetria e' un parametro con un nome ───────────────────────────────
 * §11.6 regola 6: «Il varco nell'anello e' un parametro con un nome, non
 * Math.random()». `gapStart` e `gapSweep` sono in radianti e stanno nella
 * tabella. Due anelli con lo stesso varco sembrano un errore di copia; due
 * varchi scelti a caso sembrano rumore. Vanno decisi.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";

const TAU = Math.PI * 2;
const CARDINALI = [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2];

export class ReactorRing extends ParametricComponent {
  constructor(p = {}) {
    super(
      {
        outerR: p.outerR ?? 120,          // mm
        thickness: p.thickness ?? 8,      // mm
        tickCount: p.tickCount ?? 48,
        tickLen: p.tickLen ?? 3,          // mm, DENTRO la fascia
        tickMajorEvery: p.tickMajorEvery ?? 6,
        tickMajorLen: p.tickMajorLen ?? 6,
        gapStart: p.gapStart ?? 0.62,     // rad — l'asimmetria e' PROGETTATA
        gapSweep: p.gapSweep ?? 0.31,     // rad
        periodSec: p.periodSec ?? 46,     // s per giro — §10.3
      },
      {
        name: p.name ?? "reactor-ring",
        version: "v1",
        dimensioni: 2,
        // Regola 7: dichiarato dal PARAMETRO, non misurato dai vertici.
        // Se lo derivassi dal ciclo di build() il gate verificherebbe il
        // codice contro se stesso, e un errore di trasformazione passerebbe.
        bbox: { x: 2 * (p.outerR ?? 120), y: 2 * (p.outerR ?? 120), z: 0 },
      }
    );

    // Il bbox dichiarato vale 2R su entrambi gli assi solo se l'anello tocca
    // ancora tutti e quattro i punti cardinali. Un varco che ne inghiotte uno
    // farebbe fallire il gate con un messaggio sul bounding box, cioe' nel
    // posto sbagliato: meglio dirlo qui, dove si sceglie il varco.
    const { gapStart, gapSweep } = this.params;
    for (const c of CARDINALI) {
      for (const giro of [-TAU, 0, TAU]) {
        const a = c + giro;
        if (a > gapStart && a < gapStart + gapSweep) {
          throw new Error(
            `il varco [${gapStart}, ${(gapStart + gapSweep).toFixed(3)}] rad copre il ` +
            `punto cardinale ${c.toFixed(3)} rad: l'anello non tocca piu' il proprio ` +
            `raggio su un asse e il bounding box dichiarato non vale piu'`
          );
        }
      }
    }
    if (this.params.thickness >= this.params.outerR)
      throw new Error("thickness >= outerR: l'anello non ha un foro");
    // I tick sono graduazioni SULLA fascia, come sul riferimento. Se sporgono
    // oltre il bordo interno finiscono nel vuoto fra un anello e l'altro, e
    // invece di graduare sembrano frangia.
    if (this.params.tickMajorLen > this.params.thickness)
      throw new Error(
        `tickMajorLen ${this.params.tickMajorLen} > thickness ${this.params.thickness}: ` +
        "i tick uscirebbero dalla fascia"
      );
  }

  build() {
    const {
      outerR, thickness, tickCount, tickLen, tickMajorEvery, tickMajorLen,
      gapStart, gapSweep,
    } = this.params;

    const innerR = outerR - thickness;
    const arco = TAU - gapSweep;
    const seg = this.segmentsFor(outerR, arco);   // ◄ densita' dalla curvatura
    const a0 = gapStart + gapSweep;

    const punti = [];
    const gruppi = [];

    // Un solo contorno chiuso: arco esterno, raccordo radiale, arco interno a
    // ritroso, e la chiusura la mette l'adattatore. Cosi' il varco ha due
    // spallette nette invece di due archi che finiscono nel vuoto.
    const inizio = punti.length / 3;
    for (let i = 0; i <= seg; i++) {
      const a = a0 + (i / seg) * arco;
      punti.push(Math.cos(a) * outerR, Math.sin(a) * outerR, 0);
    }
    for (let i = seg; i >= 0; i--) {
      const a = a0 + (i / seg) * arco;
      punti.push(Math.cos(a) * innerR, Math.sin(a) * innerR, 0);
    }
    gruppi.push(new Gruppo(inizio, punti.length / 3 - inizio, { chiuso: true, ruolo: "linea" }));

    // Tick DENTRO la fascia, dal bordo interno verso l'esterno, saltati nel
    // varco: l'interruzione deve leggersi come un varco, non come un anello a
    // cui manca un pezzo di bordo.
    for (let i = 0; i < tickCount; i++) {
      const a = (i / tickCount) * TAU;
      if (a > gapStart && a < gapStart + gapSweep) continue;
      const lungo = i % tickMajorEvery === 0 ? tickMajorLen : tickLen;
      const r0 = innerR;
      const r1 = innerR + lungo;
      const p = punti.length / 3;
      punti.push(Math.cos(a) * r0, Math.sin(a) * r0, 0);
      punti.push(Math.cos(a) * r1, Math.sin(a) * r1, 0);
      gruppi.push(new Gruppo(p, 2, { ruolo: "costruzione" }));
    }

    return new Geometria(new Float32Array(punti), gruppi);
  }

  /** La circonferenza primitiva a meta' fascia — §11.10 regola 3.
   *
   * E' la linea di costruzione del disegno meccanico: il cerchio su cui si
   * quotano i denti di un ingranaggio o i fori di una flangia. Non ha varco,
   * perche' e' una quota e non un pezzo, e passa DIETRO il varco dell'anello:
   * e' quello che fa leggere il varco come una mancanza voluta.
   *
   * La prima versione tirava invece due raggi dal centro alle spallette del
   * varco. Guardata nello screenshot era rumore: quattro anelli davano otto
   * raggi che attraversavano tutto il disco ad angoli scorrelati, e sembravano
   * casuali — cioe' esattamente cio' che §11.6 regola 6 vieta.
   */
  constructionLines() {
    const { outerR, thickness } = this.params;
    const primitiva = outerR - thickness / 2;
    const seg = this.segmentsFor(primitiva);
    const punti = [];
    for (let i = 0; i < seg; i++) {
      const a = (i / seg) * TAU;
      punti.push(Math.cos(a) * primitiva, Math.sin(a) * primitiva, 0);
    }
    return new Geometria(new Float32Array(punti), [
      new Gruppo(0, seg, { chiuso: true, ruolo: "costruzione" }),
    ]);
  }
}
