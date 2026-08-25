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
import * as calendario from "./mounts/calendario.js";
import * as ciambella from "./mounts/ciambella.js";
import * as chrome from "./mounts/chrome.js";
import * as lettura from "./mounts/lettura.js";
import * as tabella from "./mounts/tabella.js";
import * as confirm from "./mounts/confirm.js";
import * as consolePannello from "./mounts/console.js";
import * as dials from "./mounts/dials.js";
import * as files from "./mounts/files.js";
import * as impostazioni from "./mounts/settings.js";
import * as gestures from "./mounts/gestures.js";
import * as globe from "./mounts/globe.js";
import * as glyphs from "./mounts/glyphs.js";
import * as meteo from "./mounts/meteo.js";
import * as news from "./mounts/news.js";
import * as periodic from "./mounts/periodic.js";
import * as planes from "./mounts/planes.js";
import * as rings from "./mounts/rings.js";
import * as source from "./mounts/source.js";
import * as telemetry from "./mounts/telemetry.js";

export const REGISTRO = new Map([
  /* ⚠️ I QUATTRO ARCHETIPI STRUTTURALI stanno in CIMA, e non e' una
     preferenza: sono i quattro modi di mostrare un dato che il sistema non
     aveva — una griglia mensile, una tabella densa, una lettura grande, una
     ripartizione — e chi apre la galleria per capire come si fa un pannello
     deve trovarli prima dei componenti che ne sono casi particolari. */
  [calendario.meta.nome, calendario],
  [tabella.meta.nome, tabella],
  [lettura.meta.nome, lettura],
  [ciambella.meta.nome, ciambella],
  [conforme.meta.nome, conforme],
  [nonConforme.meta.nome, nonConforme],
  [nonConformeBanda.meta.nome, nonConformeBanda],
  [telemetry.meta.nome, telemetry],
  [confirm.meta.nome, confirm],
  [files.meta.nome, files],
  [impostazioni.meta.nome, impostazioni],
  [rings.meta.nome, rings],
  [dials.meta.nome, dials],
  [source.meta.nome, source],
  [agents.meta.nome, agents],
  [periodic.meta.nome, periodic],
  [glyphs.meta.nome, glyphs],
  [globe.meta.nome, globe],
  /* ⚠️ `chrome` PRIMA di `budget`, e l'ordine non e' una preferenza.
     `budget` e' un banco di misura: gira 300 fotogrammi con three.js e PixiJS
     accesi insieme e in anteprima **non finisce**, quindi tutto cio' che lo
     segue in questo elenco non si monta mai. Chi cerca un componente e non lo
     trova pensa che sia rotto, e il colpevole e' due righe piu' su. */
  [chrome.meta.nome, chrome],
  [budget.meta.nome, budget],
  [browser.meta.nome, browser],
  [planes.meta.nome, planes],
  [board.meta.nome, board],
  [gestures.meta.nome, gestures],
  [news.meta.nome, news],
  // §13
  [consolePannello.meta.nome, consolePannello],
  // §26.5 — la cartella contenitore
  [cartella.meta.nome, cartella],
  // §26 — il meteo
  [meteo.meta.nome, meteo],
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
