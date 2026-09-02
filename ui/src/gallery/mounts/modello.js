/* Il modello 3D dentro la galleria.
 *
 * Il pezzo e' quello VERO, fotografato da `scripts/fixture_modello.py`
 * attraverso il generatore del core: `npm run fixtures` lo rigenera. Non e' un
 * solido inventato per la vetrina — §11.9 ammette la FORMA di un dato vero, e
 * questa e' la forma esatta del messaggio `model3d.preview`.
 */

import { MODELLO } from "../fixtures/modello.js";
import { crea, css as cssModello, meta as metaModello } from "../../panels/modello.js";
import { fontiPronte } from "../attese.js";

export const meta = { nome: "modello", versione: metaModello.versione };
export const css = cssModello;

export async function monta(ospite) {
  ospite.style.width = "620px";
  ospite.style.height = "460px";
  const pannello = crea(ospite);
  window.__modello = pannello;
  pannello.aggiorna(MODELLO);
  await fontiPronte();
}
