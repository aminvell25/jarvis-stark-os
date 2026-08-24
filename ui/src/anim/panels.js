/* L'apertura del pannello — SPEC §10.3 e §10.4.
 *
 * §10.3 riga «Apertura pannello»: *«`clip-path` che si espande, 180 ms,
 * `easeOutQuart`»*. §10.4 dice pure con che cosa: `animate()` su
 * `clipPath`/`opacity`. Prescritta due volte, e questo file e' rimasto a
 * **zero byte** dalla Fase 0 fino al 24 agosto 2026.
 *
 * ## Perche' non viola l'invariante 25
 *
 * E' **classe 1** di §10.6: transitorio con causa. Comincia a un evento
 * dichiarato — qualcuno ha aperto un pannello — finisce da solo, e dopo la fine
 * il componente chiede zero fotogrammi. Nessun cancello serve.
 *
 * ⚠️ E la classe `no-animation` di WinBox **resta** (`desk/cornice.js`).
 * Spegne l'animazione *di WinBox*, che e' generica e non e' la nostra: quella
 * la guida anime.js, con la durata e la curva che §10.3 dichiara. Le due non si
 * sommano, e toglierla rimetterebbe una dissolvenza che non abbiamo scelto.
 *
 * ## Perche' `clip-path` e non `transform: scale()`
 *
 * Uno `scale` deforma il contenuto: il testo di un pannello che si apre
 * sarebbe illeggibile per 180 ms e poi scatterebbe alla dimensione giusta.
 * `clip-path` non tocca il layout — scopre un pannello gia' composto, come si
 * scopre un foglio. E' anche l'unica delle due che si puo' comporre col
 * `border-radius: 0` dell'invariante 18 senza inventare angoli.
 */

import { animate, utils } from "../../vendor/anime.esm.min.js";

export const meta = { nome: "panels", versione: "1" };

/** ms — §10.3, riga «Apertura pannello». */
export const DURATA = 180;
/** ms fra un pannello e il successivo quando ne arrivano tanti insieme. */
export const SFALSAMENTO = 45;

/** Il pannello e' gia' composto: si scopre dall'alto. `inset()` e non
 *  `polygon()` perche' i quattro lati restano dritti — invariante 18. */
const CHIUSO = "inset(0 0 100% 0)";
const APERTO = "inset(0 0 0% 0)";

/**
 * Scopre un pannello appena aperto.
 *
 * @param {HTMLElement} el      la finestra (`.winbox`), non il corpo
 * @param {number} ritardo      ms di attesa, per lo sfalsamento di una scena
 * @returns {object|null}       l'animazione, o `null` se non c'era niente da fare
 */
export function apertura(el, ritardo = 0) {
  if (!el) return null;
  /* ⚠️ Si annulla quella di prima, se c'e'.
   *
   * Aprire, chiudere e riaprire in 200 ms accodava tre animazioni sullo stesso
   * elemento, e l'ultima vinceva dopo che le altre due avevano gia' scritto.
   * `utils.remove` toglie l'elemento da ogni animazione in corso: una sola
   * timeline per pannello, che e' il criterio 3 di questa fase. */
  utils.remove(el);
  el.style.clipPath = CHIUSO;
  return animate(el, {
    clipPath: [CHIUSO, APERTO],
    duration: DURATA,
    delay: ritardo,
    ease: "outQuart",
    /* Il `clip-path` si TOGLIE alla fine, e non si lascia a `inset(0 0 0% 0)`.
     * Un clip che resta e' un contesto di compositing che resta: costa un
     * livello di composizione per sempre su ogni pannello, e non serve piu' a
     * niente appena l'animazione e' finita. */
    onComplete: () => { el.style.clipPath = ""; },
  });
}
