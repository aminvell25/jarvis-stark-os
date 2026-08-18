/* Il pannello console dentro la galleria.
 *
 * I messaggi hanno la FORMA esatta di quelli che passano sul socket (§11.9,
 * eccezione della galleria): sono i topic veri, con i campi veri, nell'ordine
 * in cui arriverebbero — prima lo stato, poi la mesh, poi cio' che succede.
 *
 * Lo stato scelto mostra tutta la gamma: un `agent.advisory` — l'unica riga
 * che porta l'accento caldo — un `ui.intent` con i suoi argomenti, e un
 * `news.card` col titolo di una notizia, che e' testo NON FIDATO e serve a far
 * vedere che il pannello lo mostra senza interpretarlo.
 */

import { crea, css as cssConsole, meta as metaConsole } from "../../panels/console.js";

export const meta = { nome: "console", versione: metaConsole.versione };
export const css = cssConsole;

const T = Math.floor(Date.now() / 1000) - 40;

const TRAFFICO = [
  { topic: "state.snapshot", ts: T, fase: 9, core: { pid: 48219 },
    tools: new Array(21), ws: { clients: 2 } },
  { topic: "geo.timezones", ts: T + 1, zone: new Array(312) },
  { topic: "source.tree", ts: T + 1, files: new Array(272) },
  { topic: "archive.notes", ts: T + 1, note: new Array(11) },
  { topic: "fs.list", ts: T + 2, path: "/home/aminvell/JARVIS", totale: 24 },
  { topic: "agent.mesh", ts: T + 3,
    nodi: [{ attivo: true }, { attivo: false }, { attivo: false }, { attivo: true },
           { attivo: false }, { attivo: false }, { attivo: false }, { attivo: false }] },
  { topic: "ui.intent", ts: T + 9, intento: "switch_workspace", args: { n: 3 } },
  { topic: "web.open", ts: T + 11,
    url: "https://www.youtube.com/results?search_query=synthwave" },
  { topic: "news.argomenti", ts: T + 18, argomenti: ["temporali", "governo", "clima"] },
  // Titolo da un feed: e' dato NON FIDATO (invariante 5), e il pannello lo
  // mette nel DOM con `textContent`. Se usasse `innerHTML`, un titolo di
  // giornale potrebbe scrivere markup dentro l'interfaccia.
  { topic: "news.card", ts: T + 19, fonte: "ANSA",
    titolo: "Temporali dopo il caldo, parla l'esperto" },
  { topic: "agent.advisory", ts: T + 24, level: "warning",
    reason: "fonti news non disponibili",
    dettaglio: ["rss/Il Post: HTTPError 403"] },
  { topic: "ui.intent", ts: T + 31, intento: "open_panel", args: { panel: "globo" } },
  { topic: "gesture.intent", ts: T + 33, tipo: "ui", intento: "espandi_pannello" },
  // Un topic che il pannello non conosce: deve comparire lo stesso, col nome e
  // con le chiavi che porta. Una traccia che nasconde cio' che non capisce non
  // serve a scoprire niente.
  { topic: "sketchup.export", ts: T + 36, file: "staffa-v3.skp", pollici: 3.5 },
];

export async function monta(ospite) {
  ospite.style.width = "820px";
  ospite.style.height = "420px";
  const p = crea(ospite);
  window.__console = p;

  /* Tre giri, con gli orari che avanzano. Un sistema acceso da qualche minuto
   * ha una traccia PIENA, ed e' in quello stato che il pannello si giudica:
   * quattordici righe in cima e il resto vuoto direbbero del mount, non del
   * componente (§11.6 regola 3). */
  for (let giro = 0; giro < 3; giro++) {
    for (const m of TRAFFICO) p.aggiorna({ ...m, ts: m.ts + giro * 47 });
  }
  // Il volume che NON si elenca, e che il piede conta: senza queste, il
  // pannello non mostrerebbe la parte piu' facile da sbagliare.
  for (let i = 0; i < 96; i++) p.aggiorna({ topic: "telemetry", ts: T + i });
}
