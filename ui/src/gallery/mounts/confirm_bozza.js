/* La finestra di conferma con un piano del LABORATORIO (ADR-015, fetta 4).
 *
 * Lo stesso componente di `confirm.js`, con la seconda forma di piano che
 * la finestra deve saper disegnare: quattro operazioni, due delle quali SENZA
 * percorsi — la sandbox e il diff — perche' e' il `dettaglio` che va sotto gli
 * occhi, e la finestra mostra il dettaglio solo dove non c'e' un percorso.
 *
 * Il piano e' VERO: `registry.pianifica("esegui_bozza")` il 3 settembre 2026
 * sulla staffa per l'SG90 scritta da opus, eseguita una volta, poi con due
 * righe cambiate a mano — lo spessore da 3,0 a 3,5 mm e il gioco dell'asola
 * da 0,2 a 0,3 — che e' la modifica che un proprietario fa davvero prima di
 * ristampare. L'id e' quello del piano; i percorsi sono quelli del
 * laboratorio del proprietario.
 */
import { crea, css as cssConferma, meta as metaConferma } from "../../windows/confirm.js";

export const meta = { nome: "confirm-bozza", versione: metaConferma.versione };
export const css = cssConferma;

const BOZZA = "/home/aminvell/JARVIS/laboratorio/bozze/2026-09-03-staffa-per-un-servo-sg90";
const PY = "/home/aminvell/progetti/jarvis-stark-os/.venv/bin/python -I genera.py";

const DIFF = [
  "script CAMBIATO dall'ultima esecuzione (oggi alle 12:36), che era riuscita: +2/-2 righe",
  "--- genera.py (eseguito)",
  "+++ genera.py (adesso)",
  "@@ -20,9 +20,9 @@",
  " ",
  " # --- parametri di progetto (mm) ------------------------------------------",
  "-T = 3.0          # spessore delle pareti (piastre e squadrette)",
  "+T = 3.5          # spessore delle pareti (piastre e squadrette)",
  " ",
  " CORPO_L = 22.8   # lunghezza corpo SG90 (asse delle alette)",
  " CORPO_W = 12.2   # larghezza corpo SG90",
  "-GIOCO = 0.2      # gioco per lato sull'asola del corpo",
  "+GIOCO = 0.3      # gioco per lato sull'asola del corpo",
  " ",
  " ASOLA_X = CORPO_L + 2 * GIOCO      # 23.2 mm",
].join("\n");

export async function monta(ospite) {
  ospite.style.width = "720px";
  ospite.style.height = "520px";
  const finestra = crea(ospite, { rispondi: () => {} });
  finestra.mostra({
    id: "c2e1ef3bf20947378b4341c68b4eabc7",
    tool: "esegui_bozza",
    riepilogo: "eseguo genera.py nella bozza «2026-09-03-staffa-per-un-servo-sg90» in "
      + "sandbox, per produrre staffa_sg90.stl — script CAMBIATO dall'ultima esecuzione "
      + "(oggi alle 12:36), che era riuscita: +2/-2 righe",
    operazioni: [
      { tipo: "esegui", sorgente: `${BOZZA}/genera.py`, destinazione: BOZZA, dettaglio: PY },
      { tipo: "sandbox", sorgente: null, destinazione: null,
        dettaglio: `${PY}: radice vuota, senza rete, scrivibile SOLO ${BOZZA}` },
      { tipo: "diff", sorgente: null, destinazione: null, dettaglio: DIFF },
      { tipo: "create", sorgente: null, destinazione: `${BOZZA}/staffa_sg90.stl`,
        dettaglio: "STL dichiarato dalla bozza; SOVRASCRIVE il file esistente" },
    ],
  });
}
