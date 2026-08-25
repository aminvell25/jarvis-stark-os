/* Che ora e', in un posto solo.
 *
 * ## Perche' esiste
 *
 * Il core trasmette `ts` dentro `telemetry` — **2,5 volte al secondo** — e
 * dentro `agent.mesh`. Nessuno lo leggeva. Nove punti del renderer chiamavano
 * `new Date()` o `Date.now()` per sapere l'ora, cioe' **l'orologio della
 * macchina che disegna**, mentre il dato accanto veniva da quella che misura.
 *
 * E' lo stesso difetto gia' corretto per il globo in `cb4a52b`: le zone
 * venivano dal core e l'istante dal renderer — due orologi per un'immagine
 * sola — e il piede stampava `HH:MM:SS UTC` come se appartenesse al dato.
 *
 * ## Che cosa cambia in pratica
 *
 * Nel modo di misura di §11.9 la scrivania e' alimentata da una
 * REGISTRAZIONE: `telemetry.ts` e' quello di allora, quindi ogni orologio che
 * legge di qui e' **fermo e riproducibile**, senza bisogno di una leva
 * `fissa()` per ciascuno. Le cinque derive latenti — `news`, `meteo`,
 * `console`, `lettura`, `calendario` — smettono di essere derive perche'
 * smettono di avere una sorgente propria.
 *
 * ⚠️ **Non e' un orologio ad alta risoluzione.** Fra due campioni di telemetria
 * passano 400 ms, quindi `adesso()` puo' essere vecchio di quel tanto. Per
 * un'ora sullo schermo e' esatto; per misurare una durata **non si usa**, e
 * infatti chi misura quanto tempo passa — l'uptime della barra, il freno di
 * `desk/layout.js` — continua a usare `Date.now()`, che e' la domanda giusta
 * per quella risposta.
 *
 * ⚠️ **Il ripiego e' DICHIARATO, non silenzioso.** Finche' il primo campione
 * non arriva — o col core scollegato — `adesso()` torna all'orologio locale, e
 * `fonte()` lo dice. Un pannello che volesse distinguere puo' chiedere; nessuno
 * puo' credere che venga dal core senza che sia vero.
 */

//: L'ultimo istante che il core ha dichiarato, in millisecondi. `null` finche'
//: non ne arriva uno.
let ms = null;

/** Accetta il `ts` di un messaggio del core. Ignora tutto il resto.
 *
 * ⚠️ **Non torna mai indietro.** Un `ts` piu' vecchio di quello che si ha si
 * scarta: i messaggi possono arrivare fuori ordine, e un orologio che
 * indietreggia farebbe apparire «3 min fa» dopo «adesso». Se il core davvero
 * tornasse indietro sarebbe un difetto del core, e non e' questo il posto in
 * cui nasconderlo.
 */
export function alimenta(ts) {
  if (typeof ts !== "number" || !Number.isFinite(ts) || ts <= 0) return;
  const q = ts * 1000;
  if (ms === null || q > ms) ms = q;
}

/** L'istante di adesso in millisecondi: del core se lo si sa, locale se no. */
export function adesso() {
  return ms ?? Date.now();
}

/** Lo stesso, come `Date`. */
export function data() {
  return new Date(adesso());
}

/** `HH:MM:SS`, il formato che tutti i piedi tecnici usano gia'. */
export function ora(opzioni = {}) {
  return data().toLocaleTimeString("it-IT", { hour12: false, ...opzioni });
}

/** «core» o «locale». Perche' la provenienza di una misura fa parte della
 *  misura — §11.7 regola 5 — e vale anche per un'ora. */
export function fonte() {
  return ms === null ? "locale" : "core";
}

/** Solo per i test: rimette lo stato iniziale. */
export function scorda() {
  ms = null;
}
