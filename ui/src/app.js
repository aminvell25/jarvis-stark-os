/* Renderer — SPEC §3.2.
 *
 * Non tocca il disco, non apre socket, non esegue nulla: riceve da
 * `window.jarvis`, che il preload espone, e disegna. Tutto cio' che e' reale
 * accade nel core (invariante 1).
 */

import { creaBus } from "./bus.js";
import { crea as creaTelemetria, css as cssTelemetria } from "./panels/telemetry.js";
import { crea as creaConferma, css as cssConferma } from "./windows/confirm.js";

const stile = document.createElement("style");
stile.textContent = cssTelemetria + cssConferma;
document.head.appendChild(stile);

const bus = creaBus(window.jarvis);
const contenitore = document.createElement("div");
// WinBox monta questo nodo nel proprio body: senza altezza piena il pannello
// si ferma al suo contenuto e sotto resta spazio morto, che §11.6 regola 3
// vieta espressamente.
contenitore.style.height = "100%";
const pannello = creaTelemetria(contenitore);

/* WinBox come cornice, senza la sua testata: il pannello porta gia' l'anatomia
 * a cinque parti di §10.2, e una seconda barra di titolo la duplicherebbe.
 * Lo spostamento delle finestre e' gestione dell'ambiente: §13, non Fase 1b.
 *
 * Le tre classi non sono estetica, sono tre regole:
 *   no-header      il pannello ha gia' la sua (§10.2)
 *   no-animation   §10.3, nessuna animazione senza causa: WinBox anima l'apertura
 *   no-shadow      invariante 19, la profondita' viene dal contrasto
 *
 * `noheader: true` NON esiste come opzione: WinBox lo fa con una classe, e
 * l'opzione sbagliata veniva ignorata in silenzio. Se ne e' accorto il ciclo
 * §11.7 guardando lo screenshot, non il codice. */
new WinBox({
  // Radice predefinita (il body): con una radice personalizzata WinBox non
  // centra, e `x: "center"` finiva in alto a sinistra senza dirlo.
  class: ["jarvis-panel", "no-header", "no-animation", "no-shadow"],
  x: "center",
  y: "center",
  width: 720,
  height: 420,
  mount: contenitore,
});

/* Il pannello resta dove WinBox lo mette. Ne' `x: "center"` ne' `.move()`
 * lo centrano con questa versione, e non insisto: la disposizione delle
 * finestre — agganci, affiancamento, workspace — e' §13, una fase a se'.
 * Fase 1b deve provare che i dati arrivano, non arredare la scrivania. */

/* Segnale per il ciclo §11.7. La modalita' screenshot di app/main.js aspetta
 * questo prima di scattare, e la soglia non e' un capriccio: con un solo
 * campione la striscia e' una riga piatta, e lo scatto proverebbe che i dati
 * arrivano ma non che il grafico li disegna. */
const CAMPIONI_PER_SCATTO = 12;
let visti = 0;

bus.su("telemetry", (msg) => {
  pannello.aggiorna(msg);
  if (++visti >= CAMPIONI_PER_SCATTO) window.__jarvisPronto = true;
});

function vuoto() {
  pannello.stato("vuoto");
  // Anche lo stato vuoto e' fotografabile: e' uno dei tre stati che §11.9
  // richiede, e va verificato come gli altri.
  window.__jarvisPronto = true;
}

bus.suStato(({ stato }) => {
  if (stato !== "connesso") vuoto();
});

// Chi si registra dopo il primo cambio di stato non deve restarne all'oscuro.
window.jarvis?.status?.().then(({ stato }) => {
  if (stato !== "connesso") vuoto();
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
