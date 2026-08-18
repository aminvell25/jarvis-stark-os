/* La board investigativa dentro la galleria.
 *
 * Carte con testo VERO dai documenti di accettazione, e la sesta carta con la
 * sorgente viva. Fuori da Electron la webview non esiste e la carta lo
 * dichiara: e' lo stato onesto, non un segnaposto.
 */

import { NOTE } from "../fixtures/note.js";
import { crea, css as cssBoard, meta as metaBoard } from "../../css3d/board.js";

export const meta = { nome: "board", versione: metaBoard.versione };
export const css = cssBoard;

export async function monta(ospite) {
  ospite.style.width = "1100px";
  ospite.style.height = "620px";
  const b = crea(ospite);
  window.__board = b;
  b.aggiorna({
    topic: "board.cards",
    note: NOTE,
    url: "https://www.youtube-nocookie.com/embed/videoseries?list=PL",
  });
}
