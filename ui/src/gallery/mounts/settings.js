/* La pagina impostazioni dentro la galleria — §26.7.
 *
 * I valori sono VERI: vengono da `config/settings.toml`, il template del
 * repository, passato per la stessa `chiavi_modificabili()` che alimenta la
 * pagina viva. Invariante 23: dati veri, e non un elenco inventato che
 * sembrerebbe giusto.
 *
 * ⚠️ Dal template e non dal file vivo, perche' quello porta i percorsi della
 * home. Vedi `scripts/fixture_impostazioni.py`.
 *
 * Lo stato scelto mostra la cosa difficile: una riga **rifiutata**, col
 * messaggio che il core manderebbe davvero. Una pagina impostazioni si guarda
 * quando funziona; si giudica quando dice di no.
 */

import { IMPOSTAZIONI } from "../fixtures/impostazioni.js";
import { crea, css as cssSet, meta as metaSet } from "../../panels/settings.js";

export const meta = { nome: "settings", versione: metaSet.versione };
export const css = cssSet;

export async function monta(ospite) {
  ospite.style.width = "460px";
  /* Alto abbastanza da mostrare TUTTO senza scorrere: la galleria serve a
   * guardare il componente, e un ciclo §11.7 che ne vede due terzi verifica
   * due terzi. Nella scrivania il pannello e' alto quanto la sua cella e il
   * corpo scorre — la barra e' quella di app.css, non quella di sistema. */
  ospite.style.height = "1620px";
  const p = crea(ospite);
  window.__impostazioni = p;

  p.aggiorna(IMPOSTAZIONI);
  /* L'esito di un rifiuto vero: `Field(ge=1)` su `ui.grid_px`. Il testo e'
   * quello che `imposta()` compone, non una parafrasi. */
  p.esito({
    topic: "ui.impostazione",
    chiave: "ui.grid_px",
    ok: false,
    errore: "ui.grid_px = 0 non e' valido: Input should be greater than or equal to 1",
  });
  p.esito({ topic: "ui.impostazione", chiave: "ui.target_fps", ok: true, valore: 60 });
}
