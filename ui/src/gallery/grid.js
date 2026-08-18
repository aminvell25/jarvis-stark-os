/* Griglia di riferimento sovrapponibile — `&grid=1`.
 *
 * Il passo viene da `--grid` di tokens.css, non da un numero scritto qui:
 * una griglia di controllo che non usa il token che dovrebbe controllare
 * mentirebbe al primo cambio di token.
 */

export function montaGriglia(radice) {
  const passo = getComputedStyle(document.documentElement)
    .getPropertyValue("--grid").trim();
  const strato = document.createElement("div");
  strato.setAttribute("data-audit", "griglia");   // esente dall'audit
  strato.className = "griglia-riferimento";
  strato.style.setProperty("--passo", passo);
  radice.appendChild(strato);
  return strato;
}
