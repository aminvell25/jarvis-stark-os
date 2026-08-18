/* Quadrante radiale — SPEC §11.5, riferimento famiglia-a/11-tavola-periodica-scanner.
 *
 * Nel riferimento sono i piccoli strumenti circolari sparsi nella colonna di
 * sinistra: una scala graduata su un arco aperto, e dentro un numero. Qui la
 * scala e' geometria parametrica, il riempimento del valore lo disegna
 * `d3-shape` (§11.5), e il numero vive nel DOM (invariante 20).
 *
 * ── La convenzione degli angoli ────────────────────────────────────────────
 * `_validate()` di §11.10 rifiuta i parametri negativi, e ha ragione: un
 * raggio negativo e' quasi sempre un errore. Ma un quadrante cresce in senso
 * ORARIO, che in coordinate matematiche e' un verso negativo. Invece di
 * introdurre un parametro negativo con un nome storto, la convenzione e'
 * dichiarata qui: si parte da `startDeg` e si SOTTRAE `sweepDeg`. Cosi' i
 * parametri restano positivi e il verso e' scritto una volta sola.
 *
 * ── Perche' il valore non e' geometria ─────────────────────────────────────
 * L'arco che si riempie cambia a ogni campione, dieci volte al secondo. Se
 * fosse geometria parametrica passerebbe dal gate dieci volte al secondo, e
 * il gate diventerebbe una tassa invece di un controllo. La geometria e' la
 * SCALA — che non cambia mai — e il valore e' un `<path>` ridisegnato.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";
import { estensioneArco } from "../math/arco.js";

const RAD = Math.PI / 180;

export class RadialDial extends ParametricComponent {
  constructor(p = {}) {
    const outerR = p.outerR ?? 60;
    const startDeg = p.startDeg ?? 225;
    const sweepDeg = p.sweepDeg ?? 270;
    const e = estensioneArco(startDeg * RAD, (startDeg - sweepDeg) * RAD, outerR);

    super(
      {
        outerR,                                  // mm — raggio della scala
        trackWidth: p.trackWidth ?? 6,           // mm — spessore della fascia graduata
        startDeg,                                // gradi, da +X in senso antiorario
        sweepDeg,                                // gradi, SOTTRATTI: il quadrante e' orario
        tickCount: p.tickCount ?? 40,
        tickMajorEvery: p.tickMajorEvery ?? 5,
        tickLen: p.tickLen ?? 2.5,               // mm, verso l'interno
        tickMajorLen: p.tickMajorLen ?? 5,       // mm
      },
      {
        name: p.name ?? "radial-dial",
        version: "v1",
        dimensioni: 2,
        // Regola 7. Qui NON e' 2R: un arco aperto tocca il proprio raggio solo
        // verso i cardinali che attraversa. Il conto e' in forma chiusa in
        // `math/arco.js`, indipendente dal ciclo di build().
        bbox: { x: e.maxX - e.minX, y: e.maxY - e.minY, z: 0 },
      }
    );

    if (this.params.sweepDeg <= 0 || this.params.sweepDeg > 360)
      throw new Error(`sweepDeg fuori da (0, 360]: ${this.params.sweepDeg}`);
    if (this.params.tickMajorLen > this.params.trackWidth)
      throw new Error(
        `tickMajorLen ${this.params.tickMajorLen} > trackWidth ${this.params.trackWidth}: ` +
        "i tick uscirebbero dalla fascia"
      );
  }

  /** L'angolo, in radianti, corrispondente a una frazione 0..1 della scala. */
  angoloPer(frazione) {
    const { startDeg, sweepDeg } = this.params;
    return (startDeg - sweepDeg * Math.min(1, Math.max(0, frazione))) * RAD;
  }

  build() {
    const { outerR, trackWidth, sweepDeg, tickCount, tickMajorEvery, tickLen, tickMajorLen } =
      this.params;
    const innerR = outerR - trackWidth;
    const arco = sweepDeg * RAD;
    const seg = this.segmentsFor(outerR, arco);   // ◄ densita' dalla curvatura

    const punti = [];
    const gruppi = [];

    // Le due guide della fascia: esterna e interna. Aperte, non chiuse — un
    // quadrante ha due estremi, e chiuderlo lo trasformerebbe in un settore.
    for (const R of [outerR, innerR]) {
      const inizio = punti.length / 3;
      for (let i = 0; i <= seg; i++) {
        const a = this.angoloPer(i / seg);
        punti.push(Math.cos(a) * R, Math.sin(a) * R, 0);
      }
      gruppi.push(new Gruppo(inizio, seg + 1, { ruolo: R === outerR ? "linea" : "costruzione" }));
    }

    // Graduazione: dal bordo interno verso l'esterno, dentro la fascia.
    for (let i = 0; i <= tickCount; i++) {
      const a = this.angoloPer(i / tickCount);
      const lungo = i % tickMajorEvery === 0 ? tickMajorLen : tickLen;
      const p = punti.length / 3;
      punti.push(Math.cos(a) * innerR, Math.sin(a) * innerR, 0);
      punti.push(Math.cos(a) * (innerR + lungo), Math.sin(a) * (innerR + lungo), 0);
      gruppi.push(new Gruppo(p, 2, { ruolo: "costruzione" }));
    }

    return new Geometria(new Float32Array(punti), gruppi);
  }

  /** I due fermi di inizio e fine scala — §11.10 regola 3.
   *
   * Sono le tacche che dicono dove la scala comincia e dove finisce, e senza
   * di loro un quadrante fermo a zero non si distingue da uno rotto.
   */
  constructionLines() {
    const { outerR, trackWidth } = this.params;
    const punti = [];
    const gruppi = [];
    for (const f of [0, 1]) {
      const a = this.angoloPer(f);
      const p = punti.length / 3;
      punti.push(Math.cos(a) * (outerR - trackWidth * 2), Math.sin(a) * (outerR - trackWidth * 2), 0);
      punti.push(Math.cos(a) * outerR, Math.sin(a) * outerR, 0);
      gruppi.push(new Gruppo(p, 2, { ruolo: "costruzione" }));
    }
    return new Geometria(new Float32Array(punti), gruppi);
  }
}
