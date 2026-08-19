/* Il pannello cartella dentro la galleria — §26.5.
 *
 * Lo stato scelto e' quello che mette alla prova tutto insieme: **icone di
 * due nature nello stesso contenitore**. §26.5 dice che una cartella
 * dell'ambiente puo' contenere moduli di §13 e file veri, e che quando
 * contiene file veri il piede mostra il percorso RISOLTO. Con soli moduli
 * quella riga non comparirebbe e il pannello si giudicherebbe a meta'.
 *
 * ⚠️ Il nome del terzo file e' scelto apposta: contiene i caratteri che un
 * `innerHTML` interpreterebbe. Nella galleria non c'e' un attaccante — c'e' un
 * CONTROLLO, che vale finche' qualcuno lo guarda: se un giorno quel nome
 * comparisse spezzato o sparisse, il pannello avrebbe smesso di usare
 * `textContent`. E' lo stesso mestiere delle fixture `non-conforme`.
 */

import { crea, css as cssCartella, meta as metaCartella } from "../../panels/cartella.js";

export const meta = { nome: "cartella", versione: metaCartella.versione };
export const css = cssCartella;

export async function monta(ospite) {
  ospite.style.width = "420px";
  ospite.style.height = "300px";
  const p = crea(ospite);
  window.__cartella = p;
  p.aggiorna({
    etichetta: "renders",
    voci: [
      { tipo: "modulo", nome: "Globo tattico" },
      { tipo: "modulo", nome: "Tavola periodica" },
      { tipo: "file", nome: "staffa-v3.skp" },
      { tipo: "file", nome: "relazione Q3 (bozza).pdf" },
      { tipo: "file", nome: "<b>non-e-markup</b>.txt" },
      { tipo: "file", nome: "sezione-longitudinale-rev07.dxf" },
    ],
    radice: "/home/aminvell/JARVIS",
  });
}
