/* Gli anelli dentro la galleria.
 *
 * Importa il componente VERO e gli da' uno stato con la FORMA di uno stato
 * vero — §11.9, l'unica eccezione concessa. Lo stato scelto e' «attivo»:
 * uno screenshot non mostra il movimento, ma mostra la composizione, ed e'
 * quella che il ciclo §11.7 deve giudicare.
 */

import { crea, css as cssAnelli, meta as metaAnelli } from "../../anim/rings.js";

export const meta = { nome: "rings", versione: metaAnelli.versione };
export const css = cssAnelli;

export async function monta(ospite) {
  ospite.style.width = "480px";
  ospite.style.height = "480px";
  const anelli = crea(ospite);
  // Appiglio per la verifica del MOVIMENTO, che uno screenshot non mostra:
  // `tests/eval_visual.py` lo usa per fermare gli anelli e controllare che si
  // fermino davvero. Solo nella galleria — l'app non lo espone.
  window.__anelli = anelli;
  anelli.aggiorna({
    attivo: true,
    stato: "T1 genera",
    livello: "nominal",
    motivo: "turno vocale · 3 subagent in coda",
    da_s: 1 * 3600 + 6 * 60 + 41,
  });
}
