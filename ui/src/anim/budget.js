/* Chi e' strumentato, e la misura di anime.js — invariante 26.
 *
 * ## Il difetto che questo file chiude
 *
 * §10.4 da' tre budget separati: three.js <= 8 ms, Pixi <= 3, anime.js <= 4.
 * `app/main.js` li leggeva da `performance.getEntriesByType("measure")` e per
 * due motori su tre stampava:
 *
 *     pixi   0 render · NON MISURABILE — nessuna marca, e zero marche non e'
 *            zero costo (§11.7 regola 4)
 *     anime  0 render · NON MISURABILE — nessuna marca …
 *
 * La riga era giusta per **anime.js**, che nessuno marcava, e **sbagliata per
 * Pixi**, che `ui/src/pixi/glyphs.js` marca da sempre: zero marche li' voleva
 * dire che il motore non aveva reso in quella scena, cioe' **assenza del
 * fenomeno**, non assenza della misura. Sono le due cose che §11.7 regola 4
 * esiste per non confondere, confuse dal rapporto che quella regola cita.
 *
 * Quindi due mezze correzioni:
 *
 *   1. `dichiara()` — chi sa misurarsi lo dice, e il rapporto puo' distinguere
 *      «non ha reso» da «non e' strumentato». Senza questo elenco la domanda
 *      non e' rispondibile da un file di misure vuoto.
 *   2. `misuraAnime()` — anime.js viene marcato per davvero.
 *
 * ## Perche' si avvolge `engine.update`
 *
 * anime.js v4 esporta `engine`, che e' il tick globale: **un** posto per tutte
 * le animazioni, invece di una marca per animazione. E il motore si ferma da
 * solo quando non c'e' niente da animare — `pause`/`wake` — quindi la marca
 * segue il lavoro vero e non il vsync, come il render a richiesta di three.js.
 *
 * ⚠️ `engine.update` e' un dettaglio interno del vendor. Se un aggiornamento lo
 * rinominasse, l'avvolgitura smetterebbe di misurare **in silenzio** e si
 * tornerebbe a zero marche credendo che sia zero costo. Per questo
 * `misuraAnime()` non dichiara «anime» se non trova la funzione: meglio un
 * «NON STRUMENTATO» rumoroso che uno zero che sembra un successo.
 */

import { engine } from "../../vendor/anime.esm.min.js";

/** I motori che sanno misurarsi. Lo legge `app/main.js` dalla pagina. */
export function dichiara(nome) {
  const w = globalThis;
  w.__motori = w.__motori ?? {};
  w.__motori[nome] = true;
}

/** Avvolge il tick di anime.js. Idempotente: chiamarla due volte non
 *  raddoppia le marche. */
export function misuraAnime() {
  if (typeof engine?.update !== "function") return false;
  if (engine.__misurato) return true;
  const originale = engine.update.bind(engine);
  engine.update = function misurata(...argomenti) {
    performance.mark("anime:da");
    const esito = originale(...argomenti);
    performance.measure("anime", "anime:da");
    return esito;
  };
  engine.__misurato = true;
  dichiara("anime");
  return true;
}
