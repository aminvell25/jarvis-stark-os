/* Geometria neutra — il formato che ogni ParametricComponent produce.
 *
 * Perche' non una THREE.BufferGeometry direttamente, che sarebbe la cosa
 * ovvia: SPEC §22 vuole gli anelli in SVG, §11.10 li mostra costruiti in
 * three.js, e §11.11 giudica chiamando `getAttribute("position")` e
 * `computeBoundingBox()`. I tre punti non stanno insieme.
 *
 * Questa classe espone ESATTAMENTE quei due metodi, cosi' il quality gate di
 * §11.11 gira verbatim su di lei per duck typing, e due adattatori sottili la
 * portano dove serve: `buffer.js` in three.js, `svg.js` in un <path>.
 *
 * L'effetto collaterale vale da solo: non dipendendo da three, la geometria e
 * il gate girano in Node. `tests/eval_visual.py` li verifica senza WebGL, in
 * millisecondi invece che in secondi, e senza un contesto grafico che in CI
 * non esisterebbe.
 *
 * Unita': millimetri (CLAUDE.md, stile codice).
 */

/** Un gruppo di vertici contigui che forma UNA polilinea.
 *
 * Serve perche' un anello con un varco e' una polilinea sola, mentre
 * quarantotto tick sono quarantotto segmenti separati: senza questa
 * informazione l'adattatore SVG li unirebbe in un unico tratto a zig-zag, e
 * three.js dovrebbe scegliere fra Line2 e LineSegments2 tirando a indovinare.
 */
export class Gruppo {
  constructor(inizio, conteggio, { chiuso = false, ruolo = "linea" } = {}) {
    this.inizio = inizio;       // indice del primo VERTICE (non del float)
    this.conteggio = conteggio; // quanti vertici
    this.chiuso = chiuso;       // l'ultimo si ricongiunge al primo
    this.ruolo = ruolo;         // "linea" | "costruzione" | "punti"
  }
}

export class Geometria {
  /**
   * @param {Float32Array} posizioni  x,y,z per vertice — §11.10 regola 5
   * @param {Gruppo[]} gruppi         se omesso: un solo gruppo su tutto
   */
  constructor(posizioni, gruppi = null) {
    if (!(posizioni instanceof Float32Array)) {
      // §11.10 regola 5 non e' un consiglio: un Array normale di numeri
      // diventa una copia in piu' e un cast a ogni upload sulla GPU.
      throw new Error("le posizioni devono essere un Float32Array");
    }
    if (posizioni.length % 3 !== 0) {
      throw new Error(`posizioni non multiple di 3: ${posizioni.length}`);
    }
    this.posizioni = posizioni;
    this.conteggio = posizioni.length / 3;
    this.gruppi = gruppi ?? [new Gruppo(0, this.conteggio)];
    this.boundingBox = null;
  }

  /* I due metodi che §11.11 chiama. Le firme sono quelle di three.js perche'
   * il gate non deve sapere quale delle due geometrie sta giudicando. */

  getAttribute(nome) {
    if (nome !== "position") return undefined;
    return { array: this.posizioni, itemSize: 3, count: this.conteggio };
  }

  computeBoundingBox() {
    const p = this.posizioni;
    if (p.length === 0) {
      this.boundingBox = { min: { x: 0, y: 0, z: 0 }, max: { x: 0, y: 0, z: 0 } };
      return this.boundingBox;
    }
    const min = { x: Infinity, y: Infinity, z: Infinity };
    const max = { x: -Infinity, y: -Infinity, z: -Infinity };
    // Ciclo esplicito e non reduce: un NaN in ingresso deve ARRIVARE al gate
    // come NaN, non essere scartato da un confronto che lo ignora. §11.11 ha
    // un controllo apposta, e serve che scatti.
    for (let i = 0; i < p.length; i += 3) {
      for (const [k, a] of [["x", 0], ["y", 1], ["z", 2]]) {
        const v = p[i + a];
        if (v < min[k] || Number.isNaN(v)) min[k] = v;
        if (v > max[k] || Number.isNaN(v)) max[k] = v;
      }
    }
    this.boundingBox = { min, max };
    return this.boundingBox;
  }

  /** Il vertice i come oggetto — per gli adattatori, non per il render loop. */
  vertice(i) {
    return {
      x: this.posizioni[i * 3],
      y: this.posizioni[i * 3 + 1],
      z: this.posizioni[i * 3 + 2],
    };
  }
}
