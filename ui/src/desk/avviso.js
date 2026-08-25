/* Quanto dura l'accento di un `agent.advisory`, e nient'altro.
 *
 * Esiste perche' due superfici devono rispondere alla stessa domanda — il
 * nucleo in `sfondo.js` e la barra in `barra.js` — e la regola scritta in
 * `barra.js` sopra `SOGLIA_TEMP` vale identica qui: **due numeri diversi per
 * la stessa soglia sarebbero due opinioni** su quanto dura un avviso.
 *
 * Non lo esporta `sfondo.js` perche' `barra.js` finirebbe per importarlo
 * intero — anime.js, `rings.js` — anche nella galleria, che monta la barra da
 * sola in `gallery/mounts/chrome.js`. Una costante non deve trascinare un
 * motore di animazione.
 *
 * ⚠️ **Un avviso SUCCEDE, non DURA.** E' la ragione per cui questo numero e' una
 * durata e non uno stato: il livello stabile lo dicono `state.snapshot` e
 * `agent.mesh`, che sono le sorgenti che sanno anche quando rientra. L'accento
 * scade e restituisce il comando a loro senza sovrascrivere niente. */
//: Non e' uno stato: e' il tempo in cui chi stava guardando altrove fa in
//: tempo a girarsi.
export const AVVISO_MS = 2600;
