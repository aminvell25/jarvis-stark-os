/* La persistenza della disposizione — §26.10 punto 1.
 *
 * Tre righe di mestiere e una decisione.
 *
 * ## Perche' un debounce e non un throttle
 *
 * Con un throttle si scriverebbe **durante** il trascinamento: una posizione
 * intermedia ogni N ms, e sul disco finirebbero venti stati che nessuno ha
 * scelto. Il debounce aspetta che il movimento FINISCA, e quello che va giu' e'
 * dove l'utente ha lasciato la finestra — che e' l'unica posizione che
 * significhi qualcosa.
 *
 * ## Perche' questo ritardo non e' una difesa
 *
 * ⚠️ Lo dichiara anche `core/layout.py`, e vale la pena ripeterlo dai due lati
 * del confine: **il freno che conta e' quello del core.** Questo sta qui
 * perche' e' educato non parlare a vuoto; un renderer compromesso — e in Fase 6
 * ne gira uno con `<webview>` dentro — sceglie semplicemente di non esserlo. Il
 * core ha il proprio minimo fra due scritture e non si fida di questo numero.
 */

//: §26.5: «salvataggio differito, non a ogni pixel di trascinamento: 500 ms
//: dopo l'ultimo movimento».
export const RITARDO_MS = 500;

/**
 * Collega la scrivania al canale verso il core.
 *
 * `invia` e' `window.jarvis.salvaLayout` — una funzione per intenzione, coi
 * campi che quella intenzione ha. Si passa dall'esterno perche' i test la
 * sostituiscono, e perche' un modulo che va a prendersi da solo un oggetto
 * globale non si puo' provare senza un browser.
 */
export function creaPersistenza({ invia, ritardo = RITARDO_MS, ora = () => Date.now() }) {
  let attesa = null;
  let ultima = null;
  //: Quando e' partito ogni invio, e che cosa portava. Non e' impalcatura da
  //: togliere: e' l'unico posto da cui si puo' misurare «venti pointermove in
  //: 300 ms producono UNA scrittura, e contiene l'ULTIMA posizione». Dal DOM
  //: si vede dove sta un pannello, non quante volte lo si e' detto al core.
  //:
  //: Ci arriva `scripts/prova-gesti.mjs` attraverso `window.__layout`.
  const scritture = [];
  let ultimoInvio = null;

  function suDisposizione(disposizione) {
    ultima = disposizione;
    if (attesa !== null) clearTimeout(attesa);
    attesa = setTimeout(scrivi, ritardo);
  }

  function scrivi() {
    attesa = null;
    if (ultima === null) return;
    const d = ultima;
    ultima = null;
    scritture.push({ t: ora(), pannelli: d?.pannelli?.length ?? 0 });
    ultimoInvio = d;
    invia(d);
  }

  /** Manda subito cio' che era in attesa. Per la chiusura della finestra. */
  function adesso() {
    if (attesa !== null) { clearTimeout(attesa); scrivi(); }
  }

  return {
    suDisposizione, adesso,
    get scritture() { return [...scritture]; },
    get ultimoInvio() { return ultimoInvio; },
    /** Azzera il contatore: una prova misura un gesto, non tutta la sessione. */
    azzera() { scritture.length = 0; ultimoInvio = null; },
  };
}
