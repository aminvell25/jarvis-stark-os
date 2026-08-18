/* Renderer — SPEC §3.2, §13.
 *
 * Non tocca il disco, non apre socket, non esegue nulla: riceve da
 * `window.jarvis`, che il preload espone, e disegna. Tutto cio' che e' reale
 * accade nel core (invariante 1).
 *
 * ## Da guscio a scrivania
 *
 * Per nove fasi questo file ha montato UN pannello. Non era una dimenticanza:
 * la disposizione delle finestre e' §13, e §22 non l'ha mai assegnata a una
 * fase, quindi ogni fase la rimandava — correttamente, una fase per volta.
 *
 * Adesso compone la scrivania: barra, dock, quattro workspace, scorciatoie. La
 * composizione vera e' in `desk/`; qui restano solo i collegamenti, e la
 * finestra di conferma, che non e' cambiata di una riga — e' verificata dalla
 * Fase 2 e con §13 non c'entra niente.
 */

import { creaBus } from "./bus.js";
import { crea as creaBarra, css as cssBarra } from "./desk/barra.js";
import { css as cssCornice } from "./desk/cornice.js";
import { crea as creaDock, css as cssDock } from "./desk/dock.js";
import { MODULI, WORKSPACE, moduliDelDock } from "./desk/moduli.js";
import { creaScrivania } from "./desk/scrivania.js";
import {
  NON_REALIZZATE, SCORCIATOIE, collega as collegaTastiera,
} from "./desk/tastiera.js";
import { crea as creaConferma, css as cssConferma } from "./windows/confirm.js";

/* Un solo foglio, montato una volta. I componenti dei pannelli portano il
 * proprio CSS con se': si raccoglie dai moduli invece di elencarlo a mano, o
 * il giorno che se ne aggiunge uno il suo stile resta fuori e nessuno capisce
 * perche' quel pannello e' senza forma. */
const stile = document.createElement("style");
stile.textContent = [
  cssBarra, cssDock, cssCornice, cssConferma,
  ...new Set(MODULI.map((m) => m.componente.css).filter(Boolean)),
].join("\n");
document.head.appendChild(stile);

const bus = creaBus(window.jarvis);
const radice = document.getElementById("scrivania");

/* ─────────────────────────────────────────────────────────────────────────────
 * La scrivania — §13
 *
 * L'ORDINE CONTA. La barra e il dock si montano per primi perche' l'area
 * utile e' cio' che resta fra loro due, e i pannelli devono conoscerla prima
 * di posizionarsi: WinBox riceve i limiti alla costruzione, e con dei limiti
 * sbagliati `maximize()` finirebbe sotto il dock.
 *
 * Si MISURA, non si dichiara. Un'altezza scritta a mano sarebbe un letterale
 * (invariante 18) e sarebbe anche sbagliata al primo cambio di corpo del
 * testo: la barra e' alta quanto la sua tipografia.
 * ───────────────────────────────────────────────────────────────────────────*/

const ospiteBarra = document.createElement("div");
const ospiteDock = document.createElement("div");
radice.append(ospiteBarra, ospiteDock);

let barra = null;
let dock = null;

function misuraArea() {
  const alto = barra?.altezza() ?? 0;
  const basso = dock?.altezza() ?? 0;
  return {
    sinistra: 0,
    alto: Math.round(alto),
    larghezza: window.innerWidth,
    altezza: Math.round(window.innerHeight - alto - basso),
  };
}

const scrivania = creaScrivania({ bus, misuraArea });

barra = creaBarra(ospiteBarra, { scrivania, bus, workspace: WORKSPACE });
dock = creaDock(ospiteDock, { scrivania, bus, moduli: moduliDelDock() });
collegaTastiera(scrivania);

/* L'appiglio per la verifica. Non e' una via d'ingresso: sono funzioni che il
 * dock e la tastiera chiamano gia', e `app/main.js --verifica` le usa per
 * provare le scorciatoie di §13 nella finestra vera invece che in un test che
 * finge una finestra. */
window.__scrivania = { scrivania, scorciatoie: SCORCIATOIE, nonRealizzate: NON_REALIZZATE };

await scrivania.vai(1);

/* Segnale per il ciclo §11.7. La modalita' screenshot di `app/main.js` aspetta
 * questo prima di scattare, e la soglia non e' un capriccio: con un solo
 * campione la striscia della telemetria e' una riga piatta, e lo scatto
 * proverebbe che i dati arrivano ma non che il grafico li disegna. */
const CAMPIONI_PER_SCATTO = 12;
let visti = 0;
bus.su("telemetry", () => { if (++visti >= CAMPIONI_PER_SCATTO) window.__jarvisPronto = true; });

// Anche lo stato vuoto e' fotografabile: e' uno dei tre stati che §11.9
// richiede, e va verificato come gli altri.
bus.suStato(({ stato }) => { if (stato !== "connesso") window.__jarvisPronto = true; });
window.jarvis?.status?.().then(({ stato }) => {
  if (stato !== "connesso") window.__jarvisPronto = true;
});

/* ─────────────────────────────────────────────────────────────────────────────
 * Conferma umana — SPEC §6.2, invariante 3
 *
 * L'ultimo tratto della catena: il core propone un piano risolto, questa
 * finestra lo mostra, e la risposta torna indietro per l'unica via che il
 * preload espone.
 *
 * UNA ALLA VOLTA. Il core puo' avere piu' richieste pendenti — due tool
 * distruttivi avviati a breve distanza. Impilare due finestre di conferma
 * significa che la seconda copre la prima e qualcuno approva senza aver letto
 * quale delle due sta approvando. Si accodano.
 *
 * NESSUNA VIA D'USCITA ACCIDENTALE. La finestra non ha pulsante di chiusura:
 * si esce scegliendo. Un clic fuori o un tasto di troppo non devono poter
 * decidere. Se nessuno risponde, il core fa scadere la richiesta dopo due
 * minuti e non accade nulla — che e' il verso giusto.
 * ───────────────────────────────────────────────────────────────────────────*/

const coda = [];
let conferma = null;      // { finestra, box } mentre una e' a schermo

function mostraProssima() {
  if (conferma || coda.length === 0) return;

  const richiesta = coda.shift();
  const ospite = document.createElement("div");
  ospite.style.height = "100%";

  const finestra = creaConferma(ospite, {
    rispondi: (id, approvato) => {
      // L'UNICA cosa che il renderer manda al core. Non chiede
      // un'operazione: risponde a una domanda gia' posta, citandone l'id.
      window.jarvis?.confirm?.(id, approvato);
      conferma?.box?.close();
      conferma = null;
      window.__jarvisConferma = null;
      mostraProssima();
    },
  });

  /* La finestra si dimensiona sul PIANO, non su una costante. Una conferma
   * per un solo file dentro un riquadro da 440px e' per due terzi vuota, e
   * §11.6 regola 3 dice di rimpicciolire, non di riempire di spazio. Sopra le
   * dodici righe elencate l'altezza si ferma e il corpo scorre. */
  const RIGHE = Math.min(richiesta.operazioni?.length ?? 1, 12);
  const altezza = Math.min(440, 150 + RIGHE * 22);

  const box = new WinBox({
    class: ["jarvis-panel", "no-header", "no-animation", "no-shadow",
            "no-close", "no-min", "no-max", "no-full"],
    modal: true,          // copre il resto: e' una decisione, non una notifica
    width: 760,
    height: altezza,
    mount: ospite,
  });

  conferma = { finestra, box };
  finestra.mostra(richiesta);

  // Segnale per la verifica: dice CHE richiesta e' a schermo, non solo che
  // qualcosa lo e'.
  window.__jarvisConferma = richiesta.id;
}

bus.su("fs.confirm_request", (richiesta) => {
  coda.push(richiesta);
  mostraProssima();
});

/* Se il core cade mentre una conferma e' aperta, la finestra resta li' a
 * chiedere di approvare qualcosa che nessuno eseguira'. Si chiude, e non si
 * risponde: rispondere a un core morto non ha significato. */
bus.suStato(({ stato }) => {
  if (stato === "connesso") return;
  coda.length = 0;
  conferma?.box?.close();
  conferma = null;
  window.__jarvisConferma = null;
});
