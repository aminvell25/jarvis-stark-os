/* Il pannello news dentro la galleria.
 *
 * Le card sono NOTIZIE VERE, prese dai feed di §15 e passate dal gate, e
 * fotografate da `npm run fixtures`. La galleria non ha bisogno della
 * concessione di §11.9: questi titoli li ha scritti davvero qualcuno.
 *
 * Lo stato scelto mostra tutto: tre interruzioni consumate su tre — cioe' il
 * budget esaurito — e il ticker rosso con una fonte che non risponde. Sono le
 * due cose che spiegano il silenzio, ed e' il silenzio la parte difficile.
 */

import { CARD } from "../fixtures/news.js";
import { crea, css as cssNews, meta as metaNews } from "../../panels/news.js";

export const meta = { nome: "news", versione: metaNews.versione };
export const css = cssNews;

export async function monta(ospite) {
  ospite.style.width = "560px";
  ospite.style.height = "560px";
  const p = crea(ospite);
  window.__news = p;

  p.aggiorna({ topic: "news.argomenti", argomenti: ["temporali", "governo", "clima"] });
  for (const c of CARD.slice(0, 5)) p.aggiorna(c);
  p.aggiorna({
    topic: "agent.advisory",
    reason: "fonti news non disponibili",
    dettaglio: ["rss/Il Post: HTTPError 403", "guardian: senza chiave Open Platform"],
  });
}
