/* Il pannello meteo dentro la galleria.
 *
 * I dati hanno la forma ESATTA che `core/tools/meteo.py` produce, e i valori
 * sono quelli VERI misurati chiamando il tool su Milano: 25 gradi, nuvoloso, e
 * una settimana con cinque condizioni diverse — temporale, nebbia, nuvoloso,
 * pioggia, poco-nuvoloso. Serve a far vedere perche' le due icone del
 * riferimento non bastavano: con quelle, cinque di questi sette giorni
 * direbbero la stessa cosa.
 */

import { crea, css as cssMeteo, meta as metaMeteo } from "../../panels/meteo.js";

export const meta = { nome: "meteo", versione: metaMeteo.versione };
export const css = cssMeteo;

export async function monta(ospite) {
  ospite.style.width = "660px";
  ospite.style.height = "180px";
  const p = crea(ospite);
  window.__meteo = p;
  p.aggiorna({
    luogo: "Milano",
    unita: "°C",
    adesso: { temperatura: 25, condizione: "nuvoloso", giorno: false },
    giorni: [
      { fra: 0, condizione: "temporale", max: 29, min: 19 },
      { fra: 1, condizione: "temporale", max: 24, min: 19 },
      { fra: 2, condizione: "nebbia", max: 29, min: 20 },
      { fra: 3, condizione: "nuvoloso", max: 29, min: 21 },
      { fra: 4, condizione: "pioggia", max: 29, min: 20 },
      { fra: 5, condizione: "temporale", max: 28, min: 19 },
      { fra: 6, condizione: "poco-nuvoloso", max: 29, min: 20 },
    ],
    aggiornato: Math.floor(Date.now() / 1000) - 240,
    sorgente: "open-meteo.com",
  });
}
