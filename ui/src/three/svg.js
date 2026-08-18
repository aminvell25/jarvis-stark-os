/* Geometria neutra -> <path d="...">.
 *
 * SPEC §22 vuole gli anelli in SVG, non in WebGL, e ha ragione: sono forme
 * piatte, nette, che devono restare nitide a qualunque scala e non costano un
 * contesto grafico. Ma restano geometria parametrica (§11.10), quindi nascono
 * dallo stesso generatore che alimenta three.js e passano lo stesso gate.
 *
 * Due dettagli che non si vedono leggendo e si vedono guardando:
 *
 *   ASSE Y. In geometria Y cresce verso l'alto, in SVG verso il basso. Senza
 *   ribaltarlo il varco dell'anello — che §11.6 regola 6 vuole PROGETTATO —
 *   finisce specchiato rispetto al punto in cui e' stato progettato.
 *
 *   POLILINEE, non archi. Si potrebbe emettere un comando `A` e lasciare
 *   l'arco al rasterizzatore. Sarebbe piu' corto e cancellerebbe il senso di
 *   `segmentsFor()`: la densita' dalla curvatura di §11.10 regola 2 esiste
 *   per essere VISIBILE. Un arco `A` e' liscio per magia del browser; una
 *   polilinea a densita' calcolata e' liscia perche' qualcuno l'ha calcolata.
 */

const DECIMALI = 3;

function n(v) {
  // toFixed poi Number: toglie gli zeri di coda senza lasciare "120.000".
  return Number(v.toFixed(DECIMALI));
}

/** Un `d` per ogni gruppo della geometria.
 * @returns {{d: string, ruolo: string, chiuso: boolean}[]}
 */
export function versoPath(geometria) {
  const fuori = [];
  for (const g of geometria.gruppi) {
    if (g.conteggio < 2) continue;
    const pezzi = [];
    for (let i = 0; i < g.conteggio; i++) {
      const v = geometria.vertice(g.inizio + i);
      pezzi.push(`${i === 0 ? "M" : "L"}${n(v.x)},${n(-v.y)}`); // ◄ Y ribaltato
    }
    if (g.chiuso) pezzi.push("Z");
    fuori.push({ d: pezzi.join(""), ruolo: g.ruolo, chiuso: g.chiuso });
  }
  return fuori;
}

/** viewBox dal bounding box, con un margine in mm.
 *
 * Calcolata e non scritta a mano: un viewBox letterale e' un numero magico
 * che smette di corrispondere alla geometria al primo cambio di parametro,
 * e il componente si ritrova tagliato ai bordi senza che niente lo segnali.
 */
export function viewBox(geometria, margine = 0) {
  const bb = geometria.computeBoundingBox();
  const x = bb.min.x - margine;
  const y = -bb.max.y - margine; // ◄ Y ribaltato: il max diventa il minimo
  const larghezza = bb.max.x - bb.min.x + margine * 2;
  const altezza = bb.max.y - bb.min.y + margine * 2;
  return `${n(x)} ${n(y)} ${n(larghezza)} ${n(altezza)}`;
}
