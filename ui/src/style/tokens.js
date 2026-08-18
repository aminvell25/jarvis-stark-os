/* Lettura dei token a runtime — invariante 18.
 *
 * Il CSS usa `var(--cy-500)` e il problema non si pone. WebGL e canvas si': un
 * materiale three.js e uno sprite PixiJS vogliono un colore come VALORE, e la
 * strada breve — scrivere 0x4dd0e1 nel sorgente — e' esattamente il valore
 * letterale che l'invariante 18 vieta. Sarebbe anche il modo piu' rapido per
 * ritrovarsi, fra sei mesi, con due palette che divergono di un digit.
 *
 * Qui i token si leggono da `tokens.css` attraverso il CSSOM, cioe' dalla
 * stessa sorgente che colora il DOM. Cambiare un token cambia il 3D.
 *
 * `tok()` SOLLEVA se il token non esiste. Un `getPropertyValue` che non trova
 * nulla restituisce stringa vuota, e una stringa vuota data a THREE.Color
 * diventa nero: il componente resterebbe invisibile sul fondo nero e sembrerebbe
 * un problema di camera o di luce. Meglio un errore col nome del token.
 */

export function tok(nome) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  if (!v) throw new Error(`token inesistente: ${nome} — vedi ui/src/style/tokens.css`);
  return v;
}

/** Il valore numerico di un token dimensionale, in px. `--s-3` -> 16. */
export function tokPx(nome) {
  const v = tok(nome);
  const n = Number.parseFloat(v);
  if (!Number.isFinite(n)) throw new Error(`token non numerico: ${nome} = ${v}`);
  return n;
}
