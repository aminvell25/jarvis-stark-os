/* Il pannello lettura numerica dentro la galleria. */

import { crea, css as cssLet, meta as metaLet } from "../../panels/lettura.js";
import { fontiPronte } from "../attese.js";

export const meta = { nome: "lettura", versione: metaLet.versione };
export const css = cssLet;

/* La forma ESATTA di «state.snapshot», coi valori dello scatto
 * «shots/scrivania/scrivania.png»: fase 9, ventuno tool, tre radici, quota 0/2.
 * E' l'eccezione della galleria (§11.9): dati finti, struttura vera. */
const SNAPSHOT = {
  topic: "state.snapshot",
  fase: 9,
  core: { pid: 98286, uptime_s: 21 },
  tools: Array.from({ length: 21 }, (_, i) => ({ nome: "tool_" + i })),
  ws: { clients: 1 },
  settings: {
    fs: { allowed_roots: ["/home/aminvell/JARVIS", "/home/aminvell/Scaricati", "/tmp/jarvis"] },
    chiavi_presenti: [],
    voice: { stt_provider: "deepgram" },
    llm: { backend: "claude_code" },
  },
  quota: { attivi: 0, max_concurrent: 2, restanti: 15 },
  voce: { abilitata: false, t1_vivo: false, auth: { stato: "ok" } },
};

export async function monta(ospite) {
  ospite.style.width = "560px";
  ospite.style.height = "260px";
  const p = crea(ospite);
  window.__lettura = p;
  p.aggiorna(SNAPSHOT);
  await fontiPronte();
}
