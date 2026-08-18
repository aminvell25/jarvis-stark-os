/* Contatori numerici — SPEC §10.3, §10.4.
 *
 * «Valori numerici: interpolazione del VALORE, mai del DOM.» La differenza non
 * e' accademica. Interpolare il DOM vuol dire far scorrere o dissolvere del
 * testo, e si vede che e' un effetto; interpolare il valore vuol dire che il
 * numero conta da 41,6 a 44,2 come conta uno strumento. Il secondo sembra vero
 * perche' e' quello che fa un vero strumento.
 *
 * La causa dell'animazione e' l'arrivo di un campione nuovo (invariante 25):
 * senza dato nuovo, nessun movimento.
 *
 * anime.js v4: `modifier: utils.round(n)` arrotonda il valore animato, non la
 * stringa. In v3 l'API era diversa — vale la pena ricordarlo perche' il
 * modello, lasciato a se stesso, scrive v3.
 */

import { animate, utils } from "../../vendor/anime.esm.min.js";

const DURATA_MS = 240; // sotto la soglia in cui si legge come "scatto"

/**
 * @param {(v:number)=>void} scrivi  riceve il valore a ogni frame
 * @param {{decimali?:number, durata?:number}} opzioni
 */
export function contatore(scrivi, { decimali = 0, durata = DURATA_MS } = {}) {
  const stato = { v: 0 };
  let corrente = null;

  return {
    verso(valore) {
      if (!Number.isFinite(valore)) return;
      // Un campione nuovo mentre il precedente sta ancora contando: si abbandona
      // il vecchio e si riparte da dove si era arrivati, senza salti.
      corrente?.pause();
      corrente = animate(stato, {
        v: valore,
        duration: durata,
        ease: "outQuart",
        modifier: utils.round(decimali),
        onUpdate: () => scrivi(stato.v),
      });
    },
    /** Senza animazione: per il primo campione, che non viene "da" nulla. */
    subito(valore) {
      if (!Number.isFinite(valore)) return;
      corrente?.pause();
      corrente = null;
      stato.v = Number(valore.toFixed(decimali));
      scrivi(stato.v);
    },
    get valore() { return stato.v; },
  };
}
