/* Il solido che il CORE ha generato, incassato per lo schermo — ADR-014.
 *
 * ⚠️ **Questo componente non genera niente**, e ne' il nome ne' questa riga
 * sono un dettaglio: §17.2 mette la geometria nel core, e il renderer la
 * MOSTRA. Un secondo generatore qui dentro sarebbe la seconda implementazione
 * dello stesso pezzo — «il caso peggiore non e' scrivere due volte la stessa
 * cosa: e' scriverla la seconda leggermente diversa» (PROTOCOLLO §3).
 *
 * ⚠️ **E allora perche' estende `ParametricComponent`?** Perche' l'invariante
 * 22 chiede che ogni cosa che finisce a schermo passi da `qualityGate()`, e il
 * gate giudica un componente: i suoi `params`, il suo `meta.bbox` dichiarato,
 * i suoi vertici. Qui i parametri e il bbox arrivano dal core insieme ai
 * vertici, e il gate verifica che le tre cose siano d'accordo — cioe' §11.10
 * regola 7 su un pezzo che questo file non ha calcolato. E' un controllo piu'
 * forte di quello su un componente locale, non piu' debole: la' chi dichiara e
 * chi misura sono lo stesso codice.
 *
 * L'altra meta' della verifica sta in Python: `core/tools/model3d.py` rilegge
 * il file GLB con la libreria standard e confronta l'accessor coi parametri
 * (ADR-012). Due controlli, due fonti, due linguaggi.
 *
 * Unita': millimetri, come tutto il resto del renderer.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";

/** base64 -> TypedArray. Little-endian esplicito, come lo scrive il core. */
export function decodifica(b64, Tipo) {
  const bin = atob(b64);
  const buf = new ArrayBuffer(bin.length);
  const byte = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) byte[i] = bin.charCodeAt(i);
  return new Tipo(buf);
}

/** Il messaggio `model3d.preview` -> gli array che servono qui. */
export function daPreview(msg) {
  return {
    nome: msg.nome,
    versione: msg.versione,
    params: msg.params ?? {},
    bbox: msg.bbox,
    /* La deroga al bbox, dichiarata dal core insieme alla sua ragione. Un
       tubo dichiara il cilindro CIRCOSCRITTO — la sezione e' un poligono
       inscritto — e senza questo numero il gate lo boccerebbe per una
       discretizzazione che qualcuno ha gia' calcolato in forma chiusa. */
    tolleranza: msg.bbox_tolleranza ?? 0,
    motivoTolleranza: msg.motivo_tolleranza ?? "",
    /* §11.10 regola 3 — le quote le sceglie il GENERATORE, non questo file:
       su una piastra sono i tre lati, su un tubo il diametro e il raggio di
       piega. Chi conosce il pezzo e' chi lo fa. */
    quote: msg.quote ?? [],
    posizioni: decodifica(msg.posizioni_b64, Float32Array),
    indici: decodifica(msg.indici_b64, Uint32Array),
    linee: decodifica(msg.linee_b64, Uint32Array),
  };
}

export class ModelloRicevuto extends ParametricComponent {
  /**
   * @param {object} d  l'uscita di `daPreview`
   */
  constructor(d) {
    super(
      /* I parametri sono quelli con cui il CORE l'ha generato, in mm. Il gate
         rifiuta un componente senza tabella parametri — «geometria non
         parametrica» — e qui la tabella e' vera: sono i numeri che hanno
         prodotto i vertici, non un'etichetta appiccicata dopo. */
      { ...d.params },
      { name: d.nome ?? "modello-ricevuto", version: d.versione ?? "v1",
        bbox: d.bbox, dimensioni: 3,
        /* `qualityGate()` legge `meta.bboxTolleranza` come FRAZIONE
           dell'ingombro, ed e' la stessa deroga che `math/pointcloud.js`
           dichiara: un campione discreto di una superficie continua non tocca
           i propri estremi. Qui il numero non e' scelto qui — arriva dal core
           con la sua ragione, e a zero il gate resta all'1 % predefinito. */
        ...(d.tolleranza > 0
          ? { bboxTolleranza: d.tolleranza, motivoTolleranza: d.motivoTolleranza }
          : {}) }
    );
    if (!(d.posizioni instanceof Float32Array)) {
      throw new Error("le posizioni devono arrivare come Float32Array");
    }
    if (!(d.indici instanceof Uint32Array) || d.indici.length === 0) {
      throw new Error("un solido senza indici non ha triangoli");
    }
    this.posizioni = d.posizioni;
    this.indici = d.indici;
    /* Coppie di indici: gli spigoli VERI del pezzo, non le diagonali della
       triangolazione. Il core li manda gia' scelti — §11.10 regola 3. */
    this.spigoli = d.linee ?? new Uint32Array(0);
  }

  build() {
    const n = this.posizioni.length / 3;
    return new Geometria(
      this.posizioni,
      [new Gruppo(0, n, { ruolo: "superficie" })],
      this.indici
    );
  }

  /** §11.10 regola 3 — gli spigoli, come segmenti indipendenti.
   *
   * ⚠️ **Ruolo «linea» e non «costruzione»**: qui gli spigoli sono il PEZZO,
   * non un aiuto al disegno. Su un'estrusione i profili e le generatrici sono
   * ESATTAMENTE la cosa che si guarda, e col grigio degli assi sparivano
   * sopra la faccia — misurato guardando `shots/modello.png` il 2 settembre
   * 2026.
   *
   * ⚠️ I vertici si RIPETONO, ed e' voluto: `Gruppo` descrive un intervallo
   * CONTIGUO di vertici, mentre uno spigolo unisce due indici qualunque. Un
   * gruppo da due vertici per segmento e' la forma che `versoLinee` accumula
   * in un solo `LineSegments2` — quarantotto `Line2` sarebbero quarantotto
   * draw call sullo stesso budget di 8 ms (§10.4).
   */
  constructionLines() {
    if (!this.spigoli.length) return null;
    const punti = new Float32Array(this.spigoli.length * 3);
    const gruppi = [];
    for (let s = 0; s < this.spigoli.length; s += 2) {
      for (const [k, v] of [this.spigoli[s], this.spigoli[s + 1]].entries()) {
        punti[(s + k) * 3] = this.posizioni[v * 3];
        punti[(s + k) * 3 + 1] = this.posizioni[v * 3 + 1];
        punti[(s + k) * 3 + 2] = this.posizioni[v * 3 + 2];
      }
      gruppi.push(new Gruppo(s, 2, { ruolo: "linea" }));
    }
    return new Geometria(punti, gruppi);
  }
}
