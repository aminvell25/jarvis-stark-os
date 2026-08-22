/* Guardiano dei font.
 *
 * Se un woff2 manca, il browser ricade sui font di sistema IN SILENZIO. Il
 * ciclo di SPEC §11.7 fa uno screenshot e lo giudica: con i font sbagliati
 * quel giudizio e' privo di valore, ma sembra riuscito. E' esattamente il
 * modo in cui la decisione di vendorizzare si smonterebbe da sola fra tre
 * mesi, senza che nessuno se ne accorga.
 *
 * Quindi: la galleria lo dichiara in rosso e `npm run shot` esce con codice
 * diverso da zero.
 */

import { fontiPronte } from "./attese.js";

const RICHIESTI = [
  { famiglia: "Barlow Semi Condensed", pesi: [400, 500, 600] },
  { famiglia: "IBM Plex Mono", pesi: [400, 500] },
];

export async function verificaFont() {
  await fontiPronte();
  const mancanti = [];
  for (const { famiglia, pesi } of RICHIESTI) {
    for (const peso of pesi) {
      const spec = `${peso} 12px "${famiglia}"`;
      try { await document.fonts.load(spec); } catch { /* niente */ }
      if (!document.fonts.check(spec)) mancanti.push(`${famiglia} ${peso}`);
    }
  }
  return mancanti;
}
