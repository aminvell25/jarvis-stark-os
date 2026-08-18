/* ParametricComponent — SPEC §11.10.
 *
 * «Nessun vertice e' mai scritto a mano.» Ogni oggetto nasce da una funzione
 * generatrice con tabella di parametri dichiarata. Come in CAD reale: non si
 * disegna una flangia, la si parametrizza.
 *
 * Le sette regole di §11.10, e dove sono imposte:
 *   1. parametri con unita' (mm), mai numeri magici in build()  → convenzione
 *   2. densita' dalla curvatura: segmentsFor() obbligatoria      → qui
 *   3. linee di costruzione preservate                          → constructionLines()
 *   4. asimmetria progettata, non casuale                       → _validate()
 *   5. Float32Array, mai geometrie standard                     → Geometria
 *   6. massimo due materiali                                    → quality-gate
 *   7. bounding box dichiarato e verificato                     → meta.bbox + gate
 *
 * La regola 7 e' la sola che il gate puo' imporre solo se il componente
 * collabora: per questo `bbox` e' obbligatorio nel meta, e non un extra che
 * si puo' dimenticare. Un componente senza bbox dichiarato non passa il gate.
 */

export class ParametricComponent {
  /**
   * @param {object} params  tabella dei parametri, in mm
   * @param {object} meta    { name, version, bbox: {x,y,z}, dimensioni?: 2|3 }
   */
  constructor(params, meta) {
    this.params = Object.freeze({ ...params });
    this.meta = Object.freeze({ unit: "mm", dimensioni: 3, ...meta });
    this._validate();
  }

  _validate() {
    for (const [k, v] of Object.entries(this.params)) {
      if (typeof v === "number" && !Number.isFinite(v))
        throw new Error(`parametro non finito: ${k}`);
      if (typeof v === "number" && v < 0 && !k.startsWith("offset"))
        throw new Error(`parametro negativo non ammesso: ${k}=${v}`);
    }
    if (this.meta.dimensioni !== 2 && this.meta.dimensioni !== 3)
      throw new Error(`meta.dimensioni deve essere 2 o 3, non ${this.meta.dimensioni}`);
  }

  /** Densita' di segmenti dalla CURVATURA, non costante — §11.10 regola 2.
   *
   * `targetChordMm` e' la freccia massima ammessa fra la corda e l'arco: piu'
   * il raggio e' grande, piu' segmenti servono per la stessa finezza. Un
   * cerchio a 32 segmenti fissi e' la firma del generato male, e si vede: i
   * raggi grandi diventano poligoni.
   */
  segmentsFor(radius, arcAngle = Math.PI * 2, targetChordMm = 1.2) {
    return Math.max(8, Math.min(256, Math.ceil((radius * arcAngle) / targetChordMm)));
  }

  /** @returns {import("./geometry.js").Geometria} */
  build() { throw new Error("build() va implementato"); }

  /** Linee di costruzione — §11.10 regola 3.
   *
   * Assi, raggi, quote: cio' che distingue un pezzo ingegnerizzato da una
   * forma. Null quando il componente non ne ha, non quando ci si e' dimenticati.
   */
  constructionLines() { return null; }
}
