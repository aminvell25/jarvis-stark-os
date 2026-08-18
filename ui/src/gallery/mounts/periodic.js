/* La tavola periodica dentro la galleria.
 *
 * Nessun dato finto: simboli, numeri atomici e pesi IUPAC sono costanti
 * fisiche. E' l'unico componente della fase che non ha bisogno ne' di una
 * sorgente collegata ne' dell'eccezione di §11.9.
 */

import { crea, css as cssPeriodic, meta as metaPeriodic } from "../../panels/periodic.js";

export const meta = { nome: "periodic", versione: metaPeriodic.versione };
export const css = cssPeriodic;

export async function monta(ospite) {
  ospite.style.width = "1180px";
  ospite.style.height = "560px";
  crea(ospite);
}
