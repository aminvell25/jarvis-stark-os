/* La mesh agenti dentro la galleria.
 *
 * Il messaggio ha la FORMA esatta di quello che `core/agents_mesh.py` mette
 * sul topic `agent.mesh` (§11.9, eccezione della galleria). Lo stato scelto e'
 * un sistema VIVO — T1 che genera, un T2 attivo, un subagent al lavoro —
 * perche' e' quello che mostra tutta la gamma del componente: nodi collegati,
 * nodi scollegati e cavi accesi.
 *
 * Nell'app di oggi lo stesso pannello mostra T1 e T2 «non collegato»: sono
 * composti dalla pipeline vocale, non dall'engine. Il pannello dice il vero in
 * entrambi i casi.
 */

import { crea, css as cssAgenti, meta as metaAgenti } from "../../panels/agents.js";
import { unFrame } from "../attese.js";

export const meta = { nome: "agents", versione: metaAgenti.versione };
export const css = cssAgenti;

export async function monta(ospite) {
  ospite.style.width = "780px";
  ospite.style.height = "360px";
  const pannello = crea(ospite);
  window.__agents = pannello;

  pannello.aggiorna({
    topic: "agent.mesh",
    ts: Math.floor(Date.now() / 1000),
    nodi: [
      { id: "router", tipo: "ingresso", stato: "pronto", dettaglio: "14 tool in allowlist", attivo: false },
      { id: "t0", tipo: "tier", stato: "pronto", dettaglio: "13 regole · zero LLM", attivo: false },
      { id: "t1", tipo: "tier", stato: "genera", dettaglio: "sessione persistente", attivo: true },
      { id: "t2", tipo: "tier", stato: "attivo", dettaglio: "1/2 · 14 nella finestra", attivo: true },
      { id: "argus", tipo: "subagent", stato: "inerte", dettaglio: "", attivo: false },
      { id: "edith", tipo: "subagent", stato: "inerte", dettaglio: "", attivo: false },
      { id: "forge", tipo: "subagent", stato: "al lavoro", dettaglio: "17,3 s", attivo: true },
      { id: "veronica", tipo: "subagent", stato: "inerte", dettaglio: "", attivo: false },
    ],
    archi: [
      ["router", "t0"], ["router", "t1"], ["t1", "t2"],
      ["t2", "argus"], ["t2", "edith"], ["t2", "forge"], ["t2", "veronica"],
    ],
  });
  await unFrame();
}
