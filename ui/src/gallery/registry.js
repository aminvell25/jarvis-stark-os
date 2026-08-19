/* Registro dei componenti della galleria.
 *
 * Ogni fase aggiunge una riga. Le fixture di prova restano: `conforme` e
 * `non-conforme` sono la verifica che l'audit funzioni ancora, e vanno
 * guardate a ogni giro insieme ai componenti veri. Dalla rev 5.8 c'e' anche
 * `non-conforme-banda`, che sorveglia proprio l'ampliamento della palette
 * fatto da quella revisione.
 */

import * as conforme from "./fixtures/conforme.js";
import * as nonConforme from "./fixtures/non-conforme.js";
import * as nonConformeBanda from "./fixtures/non-conforme-banda.js";
import * as agents from "./mounts/agents.js";
import * as board from "./mounts/board.js";
import * as browser from "./mounts/browser.js";
import * as cartella from "./mounts/cartella.js";
import * as budget from "./mounts/budget.js";
import * as chrome from "./mounts/chrome.js";
import * as confirm from "./mounts/confirm.js";
import * as consolePannello from "./mounts/console.js";
import * as dials from "./mounts/dials.js";
import * as files from "./mounts/files.js";
import * as gestures from "./mounts/gestures.js";
import * as globe from "./mounts/globe.js";
import * as glyphs from "./mounts/glyphs.js";
import * as news from "./mounts/news.js";
import * as periodic from "./mounts/periodic.js";
import * as planes from "./mounts/planes.js";
import * as rings from "./mounts/rings.js";
import * as source from "./mounts/source.js";
import * as telemetry from "./mounts/telemetry.js";

export const REGISTRO = new Map([
  [conforme.meta.nome, conforme],
  [nonConforme.meta.nome, nonConforme],
  [nonConformeBanda.meta.nome, nonConformeBanda],
  [telemetry.meta.nome, telemetry],
  [confirm.meta.nome, confirm],
  [files.meta.nome, files],
  [rings.meta.nome, rings],
  [dials.meta.nome, dials],
  [source.meta.nome, source],
  [agents.meta.nome, agents],
  [periodic.meta.nome, periodic],
  [glyphs.meta.nome, glyphs],
  [globe.meta.nome, globe],
  [budget.meta.nome, budget],
  [browser.meta.nome, browser],
  [planes.meta.nome, planes],
  [board.meta.nome, board],
  [gestures.meta.nome, gestures],
  [news.meta.nome, news],
  // §13
  [consolePannello.meta.nome, consolePannello],
  [chrome.meta.nome, chrome],
  // §26.5 — la cartella contenitore
  [cartella.meta.nome, cartella],
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
