/* La scala del testo dentro il nucleo — la regola, in un posto solo.
 *
 * ## Il problema che risolve
 *
 * Il riferimento è disegnato per 1024x1024 e dà i corpi in pixel: 11 px per la
 * telemetria e per l'anello esadecimale. Il nucleo però vive in Ø326, e un
 * `font-size` dentro un `viewBox` scala col viewBox: 11 unità rese a 0,3184
 * fanno **3,5 px**, che non è testo, è grana.
 *
 * La soluzione ovvia — scrivere `font-size: 8.5px` e sperare — non funziona:
 * dentro un SVG con viewBox quel valore è in unità di viewBox, non di schermo.
 * Si finirebbe con 8,5 unità = 2,7 px, peggio di prima.
 *
 * ## La regola
 *
 *   **Il corpo si dichiara in pixel VERI e si converte in unità di viewBox
 *   alla dimensione resa.** Il testo cade così esattamente sui gradini `--t-*`
 *   a qualunque dimensione della finestra, e l'audit lo vede come li vede
 *   ovunque.
 *
 * ⚠️ È l'inverso di quello che fa il resto del progetto, ed è voluto: altrove
 * il corpo è un token e basta, perché non c'è un viewBox in mezzo. Qui il
 * viewBox c'è, e ignorarlo significa scegliere fra un riferimento illeggibile e
 * una tipografia fuori sistema.
 *
 * ## Perché non `vector-effect`
 *
 * `non-scaling-stroke` esiste per i tratti e non ha un equivalente per il
 * testo: non c'è un `non-scaling-font`. La conversione va fatta, e va fatta
 * quando la dimensione resa è nota — cioè a ogni `misura()`.
 */

import { tokPx } from "../style/tokens.js";
import { VIEWBOX } from "./geometria.js";

/** Quanti pixel di schermo vale un'unità di viewBox, alla dimensione resa.
 * @param {number} diametroPx il lato reso dell'SVG, in pixel CSS
 */
export function scala(diametroPx) {
  if (!(diametroPx > 0)) throw new Error(`diametro non valido: ${diametroPx}`);
  return diametroPx / VIEWBOX;
}

/** Un corpo in pixel VERI -> unità di viewBox, alla dimensione resa.
 *
 * @param {number} px      il corpo voluto a schermo
 * @param {number} diametroPx il lato reso dell'SVG
 */
export function unita(px, diametroPx) {
  return px / scala(diametroPx);
}

/** Il corpo di un gradino tipografico, in unità di viewBox.
 *
 * Prende il valore dal token invece che da un numero: `--t-micro` vale 8,5 px
 * e se un giorno cambia, il testo del nucleo lo segue senza che nessuno se ne
 * ricordi.
 *
 * @param {string} token  `--t-micro`, `--t-data`, ...
 * @param {number} diametroPx
 */
export function gradino(token, diametroPx) {
  return unita(tokPx(token), diametroPx);
}

/** Quanti caratteri monospaziati stanno su una circonferenza.
 *
 * L'avanzamento di un monospaziato è ~0,6 em: è una proprietà del font, non un
 * numero scelto, ed è verificabile — `getComputedTextLength()` diviso il numero
 * di caratteri lo misura sul font vero. Qui serve una STIMA per decidere quanti
 * caratteri generare; la misura vera la fa chi disegna, dopo il primo render.
 *
 * @param {number} raggio      in unità di viewBox
 * @param {number} corpoUnita  il font-size in unità di viewBox
 * @param {number} spaziatura  letter-spacing in em
 */
export function caratteriSulGiro(raggio, corpoUnita, spaziatura = 0) {
  const avanzamento = corpoUnita * (0.6 + spaziatura);
  return Math.max(1, Math.floor((2 * Math.PI * raggio) / avanzamento));
}
