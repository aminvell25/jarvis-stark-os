/* Il pannello calendario dentro la galleria. */

import { crea, css as cssCal, meta as metaCal } from "../../panels/calendario.js";
import { unFrame } from "../attese.js";

export const meta = { nome: "calendario", versione: metaCal.versione };
export const css = cssCal;

/* Con impegni VERI: le date di consegna delle fasi che stanno in
 * docs/acceptance/ di questo repository, piu' un giorno con due voci per far
 * vedere il caso che la cella deve reggere — due righe e il conteggio del
 * resto. Il pannello non li salva: chiama suImpegni e chi vuole ricordarli li
 * manda al core per la propria strada (invariante 1). */
export async function monta(ospite) {
  /* 720 e non 520: con celle da 65 px il testo di un impegno resta in quattro
   * caratteri dopo l'ora, e un impegno troncato a «cicl…» non e' un impegno.
   * A 720 la cella e' 95 px e ne restano dieci. La misura che conta non e' la
   * larghezza del pannello: e' quanti caratteri restano dopo «hh:mm ». */
  ospite.style.width = "720px";
  ospite.style.height = "420px";
  const oggi = new Date();
  const g = (n) => {
    const d = new Date(oggi.getFullYear(), oggi.getMonth(), n);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-` +
           `${String(d.getDate()).padStart(2, "0")}`;
  };
  const p = crea(ospite, { suImpegni: (e) => { window.__ultimoImpegno = e; } });
  window.__calendario = p;
  p.aggiorna({
    impegni: [
      { data: g(oggi.getDate()), ora: "09:30", testo: "ciclo 11.7 sul plinto" },
      { data: g(oggi.getDate()), ora: "15:00", testo: "audit token" },
      { data: g(oggi.getDate()), ora: "18:45", testo: "commit fase" },
      { data: g(oggi.getDate() + 2), ora: "11:00", testo: "bench budget frame" },
      { data: g(oggi.getDate() - 3), ora: null, testo: "acceptance FASE-09" },
      { data: g(oggi.getDate() + 6), ora: "08:00", testo: "riletture reference" },
    ],
  });
  await unFrame();
}
