/* Il pannello diario dentro la galleria.
 *
 * Le righe sono REGISTRATE da una sessione vocale vera (vedi il fixture): la
 * galleria non ha bisogno della concessione di §11.9.
 *
 * Lo stato scelto e' quello che rende il registro utile invece che decorativo:
 * una risposta troncata dal barge-in, un testo detto STIMATO, e un intento
 * senza destinazione. Un pannello con tre righe tutte verdi non mostrerebbe
 * niente di cio' per cui esiste.
 *
 * ⚠️ **Due forme NON sono in galleria, e l'invariante 23 vieta di inventarle.**
 *
 * La CADUTA, non e' in galleria: un enunciato che T0 non riconosce e che non
 * trova nemmeno T1 (`ok` falso, `errore` t1_assente). Non e' mai stata
 * registrata perche' T1 non e' mai mancato mentre qualcuno parlava. Lo scatto
 * del ciclo §11.7 quindi non puo' dire se una caduta si distingua da una
 * delega: lo dicono i test, non l'occhio.
 *
 * Il QUASI-COMANDO non compare per la stessa ragione: le uniche deleghe
 * registrate hanno `quasi_comando` nullo. Il marcatore esiste ed e' provato,
 * ma nessuno l'ha ancora visto sullo schermo.
 */

import { RIGHE } from "../fixtures/diario.js";
import { crea, css as cssDiario, meta as metaDiario } from "../../panels/diario.js";

export const meta = { nome: "diario", versione: metaDiario.versione };
export const css = cssDiario;

export async function monta(ospite) {
  ospite.style.width = "720px";
  ospite.style.height = "460px";
  const p = crea(ospite);
  window.__diario = p;
  for (const r of RIGHE) p.aggiorna(r);
}
