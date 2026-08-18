/* Il pannello gesture dentro la galleria.
 *
 * I landmark sono SINTETICI e generati dallo stesso codice che alimenta
 * `tests/gesture_corpus.py` (§11.9, eccezione della galleria): cosi' cio' che
 * si guarda qui e cio' che i test giudicano sono la stessa cosa.
 *
 * Lo stato scelto e' quello che mostra tutto: telecamera ACCESA, una mano in
 * campo, un pizzico riconosciuto e l'isteresi a tre tacche su cinque — cioe'
 * il gesto non e' ancora scattato. E' il momento che rende visibile la regola
 * di §14, e uno screenshot con l'isteresi piena non lo mostrerebbe.
 */

import { POSE } from "../fixtures/mano.js";
import { crea, css as cssGesture, meta as metaGesture } from "../../panels/gestures.js";

export const meta = { nome: "gestures", versione: metaGesture.versione };
export const css = cssGesture;

export async function monta(ospite) {
  ospite.style.width = "460px";
  ospite.style.height = "520px";
  const p = crea(ospite);
  window.__gestures = p;
  p.aggiorna({
    topic: "gesture.frame",
    camera_accesa: true,
    fps: 20.0,
    ms: 8.5,
    mani: [{ lato: "Right", punti: POSE.pizzico }],
    gesto: "sposta_pannello",
    isteresi: 3,
  });
}
