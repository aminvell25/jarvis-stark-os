/* I piani stratificati dentro la galleria.
 *
 * I documenti sono VERI: `docs/acceptance/*.md`, fotografati da
 * `npm run fixtures`. Il testo delle carte e' selezionabile — meta' del
 * criterio B di §22 — e lo si verifica con `getSelection()`, non a occhio.
 */

import { NOTE } from "../fixtures/note.js";
import { crea, css as cssPiani, meta as metaPiani } from "../../css3d/planes.js";

export const meta = { nome: "planes", versione: metaPiani.versione };
export const css = cssPiani;

export async function monta(ospite) {
  ospite.style.width = "900px";
  ospite.style.height = "560px";
  const p = crea(ospite);
  window.__planes = p;
  p.aggiorna({ topic: "archive.notes", note: NOTE });
  // Il fuoco sul terzo piano: con tutti allineati non si vedrebbe la
  // profondita', che e' l'unica cosa che questo componente deve mostrare.
  p.versoPiano(2);
  await new Promise((r) => setTimeout(r, 340));
}
