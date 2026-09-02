/* Il tubo piegato dentro la galleria — §17.4 ②, fetta 2 di ADR-014.
 *
 * Stesso componente e stesso pannello dell'estrusione: cambia la FORMA, e il
 * ciclo §11.7 vuole uno scatto per ciascuna. Il pezzo e' quello vero,
 * fotografato da `scripts/fixture_modello.py` attraverso il generatore del
 * core; `npm run fixtures` lo rigenera.
 *
 * ⚠️ E' il caso che porta una tolleranza sul bbox: la sezione e' un poligono
 * inscritto nel cerchio, il bbox dichiarato e' quello del cerchio pieno, e la
 * differenza ha una forma chiusa che viaggia nel messaggio. Se il gate
 * accettasse solo bbox esatti, questo scatto non esisterebbe.
 *
 * ⚠️ Il pezzo che stava qui prima era un anello ondulato su spline chiusa, ed
 * e' stato respinto GUARDANDOLO: misure risultanti invece che di progetto, e
 * un'asimmetria che si leggeva come un errore. Sta al commit `cd5dbbd`.
 */

import { MODELLO_TUBO } from "../fixtures/modello-tubo.js";
import { crea, css as cssModello, meta as metaModello } from "../../panels/modello.js";
import { fontiPronte } from "../attese.js";

export const meta = { nome: "modello-tubo", versione: metaModello.versione };
export const css = cssModello;

export async function monta(ospite) {
  ospite.style.width = "620px";
  ospite.style.height = "460px";
  const pannello = crea(ospite);
  window.__modelloTubo = pannello;
  pannello.aggiorna(MODELLO_TUBO);
  await fontiPronte();
}
