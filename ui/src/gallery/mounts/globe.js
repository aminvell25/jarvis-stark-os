/* Il globo dentro la galleria.
 *
 * I 312 fusi sono quelli VERI di tzdata, fotografati da `npm run fixtures`
 * attraverso il tool `timezones`. L'istante e' fissato — non `new Date()` —
 * perche' due scatti a ore diverse darebbero terminatori diversi e il
 * confronto fra un giro e l'altro del ciclo §11.7 non direbbe piu' niente.
 */

import { FUSI } from "../fixtures/fusi.js";
import { crea, css as cssGlobo, meta as metaGlobo } from "../../panels/globe.js";
import { fontiPronte } from "../attese.js";

export const meta = { nome: "globe", versione: metaGlobo.versione };
export const css = cssGlobo;

export async function monta(ospite) {
  ospite.style.width = "720px";
  ospite.style.height = "520px";
  const pannello = crea(ospite);
  window.__globe = pannello;
  pannello.aggiorna({
    topic: "geo.timezones",
    zone: FUSI,
    quando: "2026-08-18T14:05:00Z",
  });
  await fontiPronte();
}
