/* Registro dei componenti della galleria.
 *
 * Le fasi successive aggiungono una riga qui. Oggi contiene solo le due
 * fixture di prova: la Fase 0b non prevede componenti reali.
 */

import * as conforme from "./fixtures/conforme.js";
import * as nonConforme from "./fixtures/non-conforme.js";
import * as telemetry from "./mounts/telemetry.js";

export const REGISTRO = new Map([
  [conforme.meta.nome, conforme],
  [nonConforme.meta.nome, nonConforme],
  [telemetry.meta.nome, telemetry],
]);

export function risolvi(nome) {
  if (nome === "all") return [...REGISTRO.values()];
  const c = REGISTRO.get(nome);
  if (!c) {
    throw new Error(
      `componente "${nome}" non registrato. Disponibili: ` +
        [...REGISTRO.keys()].join(", ")
    );
  }
  return [c];
}
