/* La nuvola dei sorgenti dentro la galleria.
 *
 * Qui non serve l'eccezione di §11.9: i file sono quelli VERI del progetto,
 * fotografati da `npm run fixtures`. La nuvola che si guarda nello screenshot
 * e' la forma reale di questo repository.
 */

import { ALBERO } from "../fixtures/albero.js";
import { crea, css as cssSource, meta as metaSource } from "../../panels/source.js";

export const meta = { nome: "source", versione: metaSource.versione };
export const css = cssSource;

export async function monta(ospite) {
  ospite.style.width = "700px";
  ospite.style.height = "460px";
  const pannello = crea(ospite);
  window.__source = pannello;
  pannello.aggiorna({ topic: "source.tree", files: ALBERO });
  // I font PRIMA di misurare le etichette, e due frame perche' il
  // ResizeObserver misuri la tela: senza, la proiezione userebbe una
  // dimensione di zero e larghezze di testo sbagliate.
  await document.fonts.ready;
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
}
