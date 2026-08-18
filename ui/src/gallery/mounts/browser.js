/* Il pannello browser dentro la galleria.
 *
 * `<webview>` esiste solo in Electron, e la galleria gira in Chromium: qui si
 * giudicano la cornice, la barra dell'indirizzo e la tipografia, che sono
 * nostre. La webview VIVA e' il criterio B di §22 e si verifica nella finestra
 * vera — dichiarato in FASE-06.md.
 *
 * L'URL e l'annuncio sono quelli veri del ripiego senza chiave Data API: e'
 * lo stato in cui il sistema si trova oggi su questa macchina.
 */

import { crea, css as cssWeb, meta as metaWeb } from "../../panels/browser.js";

export const meta = { nome: "browser", versione: metaWeb.versione };
export const css = cssWeb;

export async function monta(ospite) {
  ospite.style.width = "820px";
  ospite.style.height = "460px";
  const pannello = crea(ospite);
  window.__browser = pannello;
  pannello.aggiorna({
    topic: "web.open",
    url: "https://www.youtube.com/results?search_query=synthwave",
    annuncio:
      "Senza chiave YouTube Data API non posso far partire il video: apro la ricerca.",
  });
}
