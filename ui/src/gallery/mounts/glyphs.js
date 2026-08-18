/* I glifi esadecimali dentro la galleria.
 *
 * I byte sono VERI: e' la codifica UTF-8 di un messaggio con la stessa forma
 * di quelli che il core mette sul socket — `source.tree` con l'albero vero del
 * progetto. Non una sequenza generata: un messaggio, i suoi byte.
 */

import { ALBERO } from "../fixtures/albero.js";
import { crea, css as cssGlifi, meta as metaGlifi } from "../../pixi/glyphs.js";

export const meta = { nome: "glyphs", versione: metaGlifi.versione };
export const css = cssGlifi;

export async function monta(ospite) {
  ospite.style.width = "840px";
  ospite.style.height = "480px";
  const pannello = await crea(ospite);
  window.__glyphs = pannello;

  const msg = JSON.stringify({ topic: "source.tree", files: ALBERO.slice(0, 40) });
  await pannello.aggiungi(new TextEncoder().encode(msg));
}
