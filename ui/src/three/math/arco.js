/* Estensione analitica di un arco.
 *
 * Serve alla regola 7 di §11.10 — «bounding box dichiarato e verificato» — in
 * tutti i casi in cui l'estensione NON e' 2R. Un anello completo occupa 2R su
 * entrambi gli assi e lo si dichiara a mente; un quadrante da 270 gradi no:
 * tocca il proprio raggio solo verso i punti cardinali che l'arco attraversa.
 *
 * Il conto e' in forma chiusa, mentre `build()` discretizza in corde: le due
 * strade sono indipendenti, ed e' questo che rende la verifica del gate una
 * verifica e non una tautologia. Se `build()` sbaglia una trasformazione,
 * questo file non sbaglia con lui.
 */

const TAU = Math.PI * 2;

function normalizza(a) {
  const x = a % TAU;
  return x < 0 ? x + TAU : x;
}

/** L'arco [da, a] contiene l'angolo `q`? Angoli in radianti, verso qualunque. */
export function arcoContiene(da, a, q) {
  const inizio = normalizza(Math.min(da, a));
  const ampiezza = Math.abs(a - da);
  if (ampiezza >= TAU) return true;
  const delta = normalizza(q - inizio);
  return delta <= ampiezza;
}

/** Estensione di un arco di raggio R fra due angoli, estremi inclusi.
 * @returns {{minX:number,maxX:number,minY:number,maxY:number}}
 */
export function estensioneArco(da, a, R) {
  const xs = [Math.cos(da) * R, Math.cos(a) * R];
  const ys = [Math.sin(da) * R, Math.sin(a) * R];
  // I quattro punti cardinali sono gli unici estremi possibili oltre agli
  // estremi dell'arco: e' li' che seno e coseno hanno derivata nulla.
  const cardinali = [
    [0, R, 0], [Math.PI / 2, 0, R], [Math.PI, -R, 0], [(3 * Math.PI) / 2, 0, -R],
  ];
  for (const [q, x, y] of cardinali) {
    if (arcoContiene(da, a, q)) { xs.push(x); ys.push(y); }
  }
  return {
    minX: Math.min(...xs), maxX: Math.max(...xs),
    minY: Math.min(...ys), maxY: Math.max(...ys),
  };
}
