/* La cornice della scrivania — barra e dock — dentro la galleria.
 *
 * Barra e dock sono componenti visivi come gli altri, e §11.8 vale anche per
 * loro: se non passassero dalla galleria, l'audit dei token non li vedrebbe e
 * l'invariante 18 su quei due file sarebbe una promessa invece di un
 * controllo.
 *
 * ⚠️ **La scrivania qui e' un finto, e deve esserlo.** Una scrivania vera
 * costruirebbe quattordici pannelli dentro WinBox, che nella galleria non e'
 * nemmeno caricato. Qui si giudicano la composizione, la tipografia e i
 * colori; che i pulsanti FACCIANO qualcosa e' il criterio A di §13, e si
 * verifica nella finestra vera con `npm run verifica`.
 *
 * Lo stato scelto e' un sistema vivo: workspace 02 corrente, sei moduli su
 * otto aperti, T2 al lavoro, RAM oltre la soglia di §16 — l'unico punto in cui
 * compare l'accento caldo, e serve a far vedere che compare solo quando
 * significa qualcosa.
 */

import { crea as creaBarra, css as cssBarra } from "../../desk/barra.js";
import { crea as creaDock, css as cssDock } from "../../desk/dock.js";
import { WORKSPACE, moduliDelDock } from "../../desk/moduli.js";

export const meta = { nome: "chrome", versione: "1" };
export const css = `${cssBarra}\n${cssDock}`;

/** Il bus, ridotto a cio' che barra e dock usano. */
function busFinto() {
  const iscritti = new Map();
  return {
    su(topic, cb) {
      if (!iscritti.has(topic)) iscritti.set(topic, []);
      iscritti.get(topic).push(cb);
    },
    suStato() {},
    manda(msg) { for (const cb of iscritti.get(msg.topic) ?? []) cb(msg); },
  };
}

function scrivaniaFinta(stato) {
  return {
    osserva(cb) { cb(stato); return () => {}; },
    vai() {}, alterna() {}, nascondiTutto() {}, affianca() {},
  };
}

export async function monta(ospite) {
  ospite.style.width = "1600px";

  const bus = busFinto();
  const scrivania = scrivaniaFinta({
    workspace: 2,
    tuttoNascosto: false,
    aperti: ["telemetria", "agenti", "console", "file", "sorgente", "news"],
    fuoco: "file",
  });

  creaBarra(ospite, { scrivania, bus, workspace: WORKSPACE });
  creaDock(ospite, { scrivania, bus, moduli: moduliDelDock() });

  bus.manda({
    topic: "state.snapshot", fase: 9,
    voce: { abilitata: false, auth: { stato: "nominal" } },
  });
  bus.manda({
    topic: "telemetry",
    cpu_percent: 23.8, ram_percent: 92.6, package_temp_c: 47.25,
  });
  bus.manda({
    topic: "agent.mesh",
    nodi: [{ id: "t2", stato: "attivo", dettaglio: "1/2 · 14 nella finestra",
             attivo: true }],
  });
}
