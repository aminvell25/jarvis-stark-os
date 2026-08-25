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
import { crea as creaIcone, css as cssIcone } from "./desk/icone.js";
import { CATEGORIE, MODULI, SCENE, moduliIndicizzati } from "./desk/moduli.js";
import { crea as creaCatalogo, css as cssCatalogo } from "./desk/catalogo.js";
import { creaPersistenza } from "./desk/layout.js";
import { misuraAnime } from "./anim/budget.js";
import { alimenta } from "./desk/orologio.js";
import { crea as creaSfondo, css as cssSfondo } from "./desk/sfondo.js";
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
  cssSfondo, cssBarra, cssDock, cssCatalogo, cssCornice, cssIcone, cssConferma,
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
/* Il catalogo sta IN MEZZO, e il suo contenitore riempie lo spazio libero con
 * `pointer-events: none`: cosi' il catalogo si appoggia al fondo — opzione B
 * di §26.3, un pannello centro-basso e non una barra ancorata — senza che
 * l'area vuota rubi i clic ai pannelli che gli stanno sotto. */
const ospiteCatalogo = document.createElement("div");
ospiteCatalogo.className = "cat-ospite";
const ospiteDock = document.createElement("div");
radice.append(ospiteBarra, ospiteCatalogo, ospiteDock);

/* §26.5 — il fondo della scrivania sta nel BODY, non in `#scrivania`.
 *
 * `#scrivania > *` vale `--z-cornice`, cioe' SOPRA i pannelli: e' la barra, il
 * catalogo, il dock. Le icone libere devono stare sotto (`--z-icone`, 5), e un
 * figlio non puo' scendere sotto una regola che il padre gli impone. */
const ospiteIcone = document.createElement("div");
document.body.appendChild(ospiteIcone);

let barra = null;
let dock = null;
let catalogo = null;
let icone = null;

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

/* §26.10 punto 1 — la disposizione sopravvive al riavvio.
 *
 * Il ritardo sta qui e non nella scrivania: la scrivania dice CHE COSA e'
 * cambiato, questo decide QUANDO dirlo al core. Se il ponte non c'e' — la
 * galleria, un test — non si manda niente e la scrivania funziona uguale. */
const persistenza = creaPersistenza({
  invia: (d) => window.jarvis?.salvaLayout?.(d),
});
const scrivania = creaScrivania({
  bus, misuraArea, suDisposizione: persistenza.suDisposizione,
  // Il fondo nasce dopo, e cambia da solo: si legge quando serve, come si fa
  // gia' con le altezze di barra e dock.
  fondo: () => icone?.stato() ?? { icone: [], cartelle: [] },
});

/* ─────────────────────────────────────────────────────────────────────────────
 * L'insegna — §25
 *
 * PRIMO FIGLIO della scrivania, e non nel body: `--z-icone` (5) e i winbox (da
 * 11) vivono dentro #scrivania, e il fondo deve stare sotto tutti e due. Il
 * livello glielo da' `app.css` sulla classe `.sfd`, perche' la regola
 * universale `#scrivania > *` ne dichiara uno per tutti (vedi il commento li').
 *
 * ⚠️ Si iscrive a OGNI topic, e non e' pigrizia: l'insegna reagisce al
 * TRAFFICO, cioe' e' l'unico componente a cui interessa che qualcosa passi e
 * non che cosa. Il filtro su «telemetry» sta dentro il modulo, dove c'e'
 * scritto perche' — arriva a 2,5 Hz qualunque cosa accada, quindi e' il
 * battito e non il lavoro.
 * ───────────────────────────────────────────────────────────────────────────*/

const sfondo = creaSfondo(radice);
radice.insertBefore(sfondo.radice, radice.firstChild);
bus.suOgni((m) => sfondo.aggiorna(m));
/* L'orologio della scrivania lo alimenta il CORE. `telemetry` porta `ts` 2,5
   volte al secondo e `agent.mesh` un'altra volta al secondo: nove punti del
   renderer chiedevano l'ora alla macchina che disegna invece che a quella che
   misura. `alimenta` ignora i messaggi senza `ts`, quindi qui basta darle
   tutto — vedi desk/orologio.js. */
bus.suOgni((m) => alimenta(m?.ts));

/* §26.9 criterio 7, LA META' CHE MANCAVA.
 *
 * «Cambiare la dimensione delle icone dalla pagina riscrive settings.toml
 * conservando i commenti, e **l'effetto si vede senza riavviare**.» La prima
 * meta' e' stata chiusa con la pagina impostazioni; questa e' la seconda.
 *
 * Il difetto era di quelli che questo progetto nomina per nome: `ui.grid_px`
 * esisteva nello schema dalla Fase 0 e **non lo leggeva nessuno**, mentre
 * tokens.css dichiarava `--grid: 110px`. Due proprietari per la stessa
 * misura, che coincidevano per caso — entrambi 110 — e che al primo cambio si
 * sarebbero separati in silenzio: la pagina avrebbe scritto 128 nel file, il
 * file lo avrebbe riletto a caldo, e sullo schermo non sarebbe cambiato
 * niente.
 *
 * tokens.css resta il PREDEFINITO e non si tocca (e' legato a §10.1 byte a
 * byte): qui si sovrascrive la proprieta' su `:root`, che e' esattamente cio'
 * per cui una custom property esiste.
 *
 * ⚠️ Non tocca la geometria dei pannelli: `scrivania.js` calcola le celle da
 * `area.larghezza / COLONNE`, non da `--grid`. Questo token e' la scala della
 * CORNICE — tessere del catalogo, minimi di `cornice.js` — ed e' quella che
 * §26.7 chiama «la dimensione delle icone». */
const SCALA = [["grid_px", "--grid"], ["gap_px", "--gap"]];

function applicaScala(ui) {
  for (const [chiave, token] of SCALA) {
    const v = ui?.[chiave];
    // Un valore assente non e' zero, e uno non finito non e' una misura: in
    // entrambi i casi resta il predefinito di tokens.css. Sovrascriverlo con
    // `NaNpx` spegnerebbe mezza interfaccia senza un errore da leggere.
    if (typeof v !== "number" || !Number.isFinite(v) || v <= 0) continue;
    const atteso = `${v}px`;
    if (document.documentElement.style.getPropertyValue(token) === atteso) continue;
    document.documentElement.style.setProperty(token, atteso);
  }
}

bus.su("state.snapshot", (m) => applicaScala(m?.settings?.ui));

/* Il budget di anime.js (invariante 26, 4 ms) non lo misurava nessuno: si
   avvolge il tick globale del motore, una volta sola. Vedi anim/budget.js. */
misuraAnime();
bus.suStato(({ stato }) => sfondo.stato(stato));

/* Chiudendo la finestra si perderebbe l'ultimo mezzo secondo. `pagehide` e non
 * `beforeunload`: il secondo non e' garantito, e su una finestra a schermo
 * intero che si chiude col compositore non arriva. */
window.addEventListener("pagehide", () => persistenza.adesso());

barra = creaBarra(ospiteBarra, { scrivania, bus, categorie: CATEGORIE });

/* §26.5 — il fondo si monta PRIMA del catalogo: il catalogo gli consegna il
 * gesto di estrazione, e vuole avere qualcuno a cui consegnarlo. Non ha
 * bisogno dell'area utile — la misura quando serve. */
icone = creaIcone(ospiteIcone, {
  scrivania, bus,
  // Stessa strada dei pannelli: si dice CHE COSA e' cambiato, e il ritardo lo
  // mette `desk/layout.js`.
  suCambio: () => persistenza.suDisposizione(scrivania.disposizione()),
});
/* §26.3 — il catalogo prende dal dock l'INDICE dei moduli e le azioni; il dock
 * resta la striscia di stato. Sta fra la barra e il dock, dentro `#scrivania`,
 * quindi sopra i pannelli: un indice che si puo' seppellire smette di essere
 * un indice. */
catalogo = creaCatalogo(ospiteCatalogo, {
  scrivania, bus, estrazione: icone.estrazione,
});
dock = creaDock(ospiteDock, { scrivania, bus });
collegaTastiera(scrivania);


/* L'appiglio per la verifica. Non e' una via d'ingresso: sono funzioni che il
 * dock e la tastiera chiamano gia', e `app/main.js --verifica` le usa per
 * provare le scorciatoie di §13 nella finestra vera invece che in un test che
 * finge una finestra.
 *
 * `moduliIndicizzati` e' di sola LETTURA, e sta qui per una ragione precisa:
 * `verifica:scrivania` pretendeva OTTO voci d'indice, scritte come letterale.
 * I moduli intanto sono diventati dieci — meteo e globo — e il criterio A di
 * §13 e' passato dal misurare l'indice al ricordarsi quanto era grande il
 * giorno in cui fu scritto. Con la sorgente esposta, il conto lo fa la
 * registry: se domani arriva l'undicesimo, il criterio lo sa. */
window.__scrivania = {
  scrivania, icone, scorciatoie: SCORCIATOIE, nonRealizzate: NON_REALIZZATE,
  moduliIndicizzati,
};

/* La leva del modo di misura (§11.9, seconda eccezione), gemella di
 * `window.__insegna.fissa()`. La aziona `app/main.js` **solo** con `--fixture`;
 * `npm run app` non la chiama mai. */
window.__barra = { fissa: () => barra?.fissa() };

/* ADR-010 — una scrivania sola: si apre TUTTO.
 *
 * Prima era `vai(1)`, che componeva il primo dei quattro workspace e lasciava
 * invisibili gli altri tre quarti. Adesso non c'e' un primo workspace, e la
 * scrivania affollata e' quello che si vede — come nel riferimento.
 *
 * Se poi arriva un layout salvato, `ripristina()` rimette ognuno dove l'utente
 * l'aveva lasciato: qui si stabilisce solo CHE COSA c'e', non dove. */
await scrivania.apriIniziale();

/* L'appiglio della persistenza, per `scripts/prova-gesti.mjs`.
 *
 * Non e' una via d'ingresso: e' di sola lettura e non fa accadere niente. Sta
 * qui perche' quante volte il renderer ha parlato al core NON si vede dal DOM,
 * e il debounce su una sequenza vera di `pointermove` e' proprio la cosa che
 * il banco sintetico non copriva.
 *
 * ⚠️ Un'impalcatura che nessuno usa e' un'impalcatura che nessuno aggiorna:
 * se un giorno `prova-gesti.mjs` smettesse di leggerla, questa riga va tolta,
 * non lasciata li' a invecchiare. */
window.__layout = { persistenza, ripristino: null };

/* §26.6 — le scene dichiarate a mano arrivano dal core.
 *
 * ⚠️ La scrivania si compone PRIMA, con la scena predefinita di `moduli.js`:
 * aspettare questo messaggio vorrebbe dire uno schermo nero finche' il core
 * non risponde, e col core spento non si comporrebbe mai. Se poi le
 * impostazioni nominano una scena iniziale DIVERSA da quella gia' a schermo,
 * si ricompone — succede una volta, all'avvio, e solo su una macchina che ha
 * scritto quella riga. */
bus.su("ui.scene", async (m) => {
  scrivania.dichiaraScene(m.scene, m.iniziale);
  if (m.iniziale && m.iniziale !== scrivania.scenaCorrente && !ripristinato) {
    await scrivania.scena(m.iniziale);
  }
});

/* Il ripristino. Il core SPINGE `ui.layout` alla connessione — il renderer non
 * lo chiede, invariante 1 — e il bus lo riconsegna anche a chi si iscrive dopo.
 *
 * Un layout vuoto vale «non c'e' niente da ricordare»: si resta con la
 * disposizione di `moduli.js`, che e' cio' che succedeva prima di questo passo.
 * Vale per il primo avvio, per il file assente e per il file corrotto: tre
 * cause diverse, un solo comportamento, e nessuna di esse impedisce di partire. */
let ripristinato = false;
bus.su("ui.layout", async (layout) => {
  // ⚠️ Anche un layout con SOLE icone va rimesso. Prima la condizione guardava
  // i pannelli e basta: una scrivania con la disposizione dichiarata e tre
  // icone sul fondo sarebbe ripartita senza le icone, cioe' §26.5 sarebbe
  // stata rotta dal guardiano di §26.10 punto 1.
  if (ripristinato) return;
  ripristinato = true;
  /* §26.5 — IL FONDO DICHIARATO E' UN DEFAULT, e va deciso QUI.
   *
   * Non nella scena: `apriIniziale()` compone prima che il layout arrivi, e
   * a quel punto il pavimento e' vuoto per forza. Una scena che posasse li'
   * rimetterebbe anche le icone che l'utente aveva tolto — misurato:
   * `prova-icone.mjs` rimuove `agenti` trascinandola sul catalogo, e al
   * riavvio tornava, nove icone prima della chiusura e dieci dopo.
   *
   * Quindi si aspetta il layout, e il default vale solo se il layout non
   * porta nessun fondo: un piano mai apparecchiato, non un piano sgombrato. */
  const suoFondo = (layout?.icone?.length ?? 0) + (layout?.cartelle?.length ?? 0);
  if (!suoFondo) await icone.posa(SCENE[0]?.fondo);

  const roba = (layout?.pannelli?.length ?? 0) + suoFondo;
  if (!roba) return;
  // PRIMA il fondo: una cartella aperta e' un pannello, e `ripristina()` lo
  // cerchera' nel registro. Se non c'e' ancora, lo ignora come un modulo tolto.
  const fondo = await icone.ripristina(layout);
  const esito = await scrivania.ripristina(layout);
  window.__layout.ripristino = {
    ...esito, ...fondo, ricevuti: layout.pannelli.length,
  };
  if (esito.ignorati.length) {
    // Livello info, non warning: un pannello tolto da `moduli.js` e' una
    // decisione di chi scrive il codice, non un guasto da segnalare.
    console.info("layout: pannelli ignorati perche' non esistono piu'",
                 esito.ignorati);
  }
});

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
