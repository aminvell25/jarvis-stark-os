/* Le scorciatoie di §13 — in un posto solo.
 *
 * ⚠️ §13, verbatim: «Scorciatoie **interne all'app**, gestite dal renderer.
 * Non registri scorciatoie globali di sistema». Qui c'e' un `keydown` sul
 * documento e nient'altro: nessuna `globalShortcut` di Electron, che
 * intercetterebbe i tasti anche mentre JARVIS non e' a fuoco e li toglierebbe
 * a ogni altro programma.
 *
 * ## Due delle sette non ci sono, ed e' scritto
 *
 * | §13 | qui |
 * |---|---|
 * | `Alt+H` nasconde tutti i pannelli | ✅ |
 * | `Alt+T` affianca | ✅ |
 * | `Alt+1…4` workspace interno | ✅ |
 * | doppio clic barra → massimizza | ✅ (in `cornice.js`) |
 * | trascinamento al bordo → aggancia | ✅ (in `cornice.js`) |
 * | `Alt+Spazio` ascolto senza frase-wake | ❌ |
 * | `Esc` interrompe il TTS | ❌ |
 *
 * Le due mancanti sono richieste VERSO il core, e il preload espone quattro
 * funzioni di cui l'unica in uscita puo' soltanto *rispondere* a una domanda
 * gia' posta (§6.3). Aggiungerne una quinta, oggi, aprirebbe un canale verso
 * un sottosistema che non gira — la `VoicePipeline` non e' composta
 * nell'engine — e sarebbe una superficie in piu' senza niente dall'altra
 * parte. Il canale si aggiungera' quando avra' un consumatore, e quel giorno
 * sara' verificabile.
 *
 * NON si riusa `Esc` per qualcos'altro. Un tasto che in §13 significa una cosa
 * e nel codice ne fa un'altra e' peggio di un tasto che non fa niente.
 */

export const meta = { nome: "tastiera", versione: "1" };

/**
 * Le scorciatoie realizzabili, come dati. Sono una TABELLA e non una catena di
 * `if` perche' cosi' si possono verificare: `app/main.js --verifica` le legge
 * da `window.__scrivania.scorciatoie` e le confronta con §13.
 */
export const SCORCIATOIE = [
  { tasti: "Alt+H", codice: "KeyH", azione: "nascondi tutti i pannelli" },
  { tasti: "Alt+T", codice: "KeyT", azione: "affianca" },
  { tasti: "Alt+1", codice: "Digit1", azione: "workspace 01" },
  { tasti: "Alt+2", codice: "Digit2", azione: "workspace 02" },
  { tasti: "Alt+3", codice: "Digit3", azione: "workspace 03" },
  { tasti: "Alt+4", codice: "Digit4", azione: "workspace 04" },
];

//: Quelle che §13 elenca e che non si possono fare senza allargare il preload.
//: Stanno qui, e non in un commento sparso, perche' `--verifica` le mostra:
//: una mancanza dichiarata e' una decisione, una mancanza taciuta e' un bug.
export const NON_REALIZZATE = [
  { tasti: "Alt+Spazio", azione: "ascolto senza frase-wake",
    perche: "richiesta verso il core: il preload non la consente (§6.3)" },
  { tasti: "Esc", azione: "interrompe il TTS",
    perche: "richiesta verso il core: il preload non la consente (§6.3)" },
];

export function collega(scrivania, bersaglio = document) {
  function suTasto(e) {
    if (!e.altKey || e.ctrlKey || e.metaKey) return;

    switch (e.code) {
      case "KeyH": scrivania.nascondiTutto(); break;
      case "KeyT": scrivania.affianca(); break;
      case "Digit1": case "Digit2": case "Digit3": case "Digit4":
        scrivania.vai(Number(e.code.slice(-1)));
        break;
      default: return;                  // allowlist: il resto passa oltre
    }
    // Solo per i tasti che abbiamo davvero consumato: fermare tutto
    // toglierebbe ad altri elementi combinazioni che non ci riguardano.
    e.preventDefault();
  }

  bersaglio.addEventListener("keydown", suTasto);
  return () => bersaglio.removeEventListener("keydown", suTasto);
}
