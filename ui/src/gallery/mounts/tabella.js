/* Il pannello tabella dati dentro la galleria. */

import { ALBERO } from "../fixtures/albero.js";
import { crea, css as cssTab, meta as metaTab } from "../../panels/tabella.js";
import { fontiPronte } from "../attese.js";

export const meta = { nome: "tabella", versione: metaTab.versione };
export const css = cssTab;

/* I file sono quelli VERI di questo repository, con le dimensioni lette da
 * «git ls-files»: qui non serve l'eccezione di §11.9. */
export async function monta(ospite) {
  ospite.style.width = "700px";
  ospite.style.height = "420px";
  const p = crea(ospite);
  window.__tabella = p;
  p.aggiorna({ topic: "source.tree", files: ALBERO });
  await fontiPronte();
}
