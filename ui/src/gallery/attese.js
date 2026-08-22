/* Le due attese della galleria — SPEC §11.7.
 *
 * ## Perche' esistono in un file loro
 *
 * Quattro mount le riscrivevano identiche: `globe`, `agents`, `budget` e
 * `source` aspettavano i font e uno o due fotogrammi prima di dichiararsi
 * pronti. Non e' duplicazione di comodo — e' duplicazione di una REGOLA, e una
 * regola scritta in quattro posti diverge al primo che la corregge.
 *
 * ## Perche' due fotogrammi e non uno
 *
 * Il primo fotogramma esegue le richiamate registrate PRIMA di lui; e' il
 * secondo che vede il layout con cui il primo ha finito. Un componente che
 * misura il proprio contenitore — il globo, la mesh — al primo fotogramma
 * misura ancora quello di prima, e nel caso peggiore misura un contenitore a
 * `display: none`: e' l'errore che in Fase 5 produsse una griglia 1x1.
 *
 * ## Perche' i font vanno aspettati e non ignorati
 *
 * `document.fonts.ready` non e' una gentilezza verso lo scatto: fino a quel
 * momento il testo rende con il ripiego dell'agente utente, che ha metriche
 * diverse. Chi misura un'etichetta prima misura quella sbagliata, e chi
 * fotografa prima fotografa Arial. L'audit di §11.8 boccia esattamente
 * quello.
 */

/** Un fotogramma, cioe' due — vedi sopra perche'. */
export function unFrame() {
  return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
}

/** I font caricati e il layout assestato: l'attesa completa prima di scattare. */
export async function fontiPronte() {
  await document.fonts.ready;
  await unFrame();
}
