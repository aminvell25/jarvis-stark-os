/* Il pannello ciambella di ripartizione dentro la galleria. */

import { ALBERO } from "../fixtures/albero.js";
import { crea, css as cssCia, meta as metaCia } from "../../panels/ciambella.js";
import { fontiPronte, unFrame } from "../attese.js";

export const meta = { nome: "ciambella", versione: metaCia.versione };
export const css = cssCia;

/* La ripartizione e' calcolata sui file veri: il ramo di primo livello del
 * percorso, che e' un fatto del repository e non una categoria inventata. */
export async function monta(ospite) {
  ospite.style.width = "620px";
  ospite.style.height = "260px";
  const p = crea(ospite);
  window.__ciambella = p;
  p.aggiorna({ topic: "source.tree", files: ALBERO });
  await fontiPronte();
  // L'apertura dei settori dura 420 ms: senza l'attesa lo scatto coglierebbe
  // l'anello a meta' giro, ed e' gia' successo due volte in questo progetto.
  await unFrame();
}
