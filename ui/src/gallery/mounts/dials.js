/* I quadranti dentro la galleria.
 *
 * Importa il pannello VERO e gli manda messaggi con la FORMA di quelli del
 * topic `telemetry`: percentuali non tonde, temperatura plausibile, timestamp
 * coerente (§11.9, eccezione della galleria).
 *
 * L'ultimo campione porta la RAM sopra la soglia di §16: e' l'unico modo di
 * far vedere in uno screenshot che l'accento caldo esiste e che compare solo
 * quando significa qualcosa.
 */

import { crea, css as cssDials, meta as metaDials } from "../../panels/dials.js";

export const meta = { nome: "dials", versione: metaDials.versione };
export const css = cssDials;

export async function monta(ospite) {
  ospite.style.width = "620px";
  ospite.style.height = "240px";
  const pannello = crea(ospite);
  window.__dials = pannello;

  const t = Math.floor(Date.now() / 1000);
  pannello.aggiorna({
    topic: "telemetry", ts: t - 1,
    cpu_percent: 23.8, ram_percent: 61.4, package_temp_c: 47.25,
  });
  pannello.aggiorna({
    topic: "telemetry", ts: t,
    cpu_percent: 71.2, ram_percent: 92.6, package_temp_c: 68.9,
  });

  // I contatori interpolano il valore per 240 ms. Senza questa attesa lo
  // scatto coglie un numero di passaggio — 88,8 al posto di 92,6 — cioe' un
  // valore che non e' mai esistito. Il ciclo §11.7 deve giudicare uno stato
  // fermo, non un fotogramma di transizione.
  await new Promise((r) => setTimeout(r, 400));
}
