/* La geometria di un pannello contro l'area che lo ospita — e la scala fra due
 * schermi.
 *
 * ## Perche' sta in un file suo
 *
 * Perche' e' una funzione PURA in mezzo a un file che non lo e', e perche'
 * `LAYOUT-PERSISTENTE.md` punto 11 diceva che la sua scelta si sarebbe potuta
 * verificare solo «al primo cambio di monitor vero». Non era vero: bastava
 * poterla chiamare senza una finestra intorno. Un test che apra due schermi non
 * esiste; uno che chiami una funzione con due aree diverse costa niente.
 */

/** Il minimo che deve restare a schermo perche' la testa sia afferrabile. */
export const MIN_VISIBILE = 80;

/** Riporta dentro l'area una geometria che ne e' uscita: TAGLIA, non scala.
 *
 * ## ⚠️ La scala e' stata provata il 23 agosto 2026, e ritirata
 *
 * `LAYOUT-PERSISTENTE.md` punto 11 dichiarava latente il fatto che questa
 * funzione tagli: *«un layout salvato su 2560x1440 e riaperto su 1366x768 non
 * diventa un layout piu' piccolo, diventa una pila di pannelli schiacciati
 * contro il bordo sinistro»*. E notava che `core/layout.py` salva
 * `area_larghezza` e `area_altezza` che nessuno legge.
 *
 * Scritta la scala — proporzionale, solo quando l'area salvata differisce da
 * quella di adesso — ha rotto un criterio di accettazione dichiarato:
 * §26.9 criterio 4, *«riaperta l'app, il pannello e' dove l'ho lasciato»*.
 * Misurato: lasciato in (632, 385), riaperto in (883, 493). I fattori
 * ricostruiti sono kx 1,397 e ky 1,306, cioe' un'area salvata di circa
 * **1099x600**.
 *
 * **Il difetto non era la scala: era il segnale.** `area_larghezza` e
 * `area_altezza` non sono lo SCHERMO, sono il PAVIMENTO — l'area fra barra e
 * dock, che `app.js` calcola come `innerHeight - barra - dock`. Quel numero si
 * muove per ragioni che non hanno niente a che vedere con un cambio di
 * monitor: una finestra non ancora massimizzata, un dock piu' alto perche' ci
 * sono piu' pannelli. Scalare su un segnale che cambia da solo significa
 * spostare la disposizione dell'utente quando nessuno ha cambiato schermo — che
 * e' esattamente il difetto R82 che questo file esiste per non rifare.
 *
 * Perche' la scala funzioni servirebbe salvare la dimensione della FINESTRA,
 * che cambia solo quando cambia lo schermo. Il campo non c'e', e aggiungerlo e'
 * un lavoro sul core: `core/layout.py` scrive quello che il renderer gli manda.
 * Fino ad allora si taglia, e adesso si taglia **sapendo perche'**.
 */
export function dentroArea(p, a) {
  const larghezza = Math.min(p.larghezza, Math.round(a.larghezza));
  const altezza = Math.min(p.altezza, Math.round(a.altezza));
  return {
    ...p,
    larghezza,
    altezza,
    x: Math.max(a.sinistra, Math.min(p.x, a.sinistra + a.larghezza - MIN_VISIBILE)),
    y: Math.max(a.alto, Math.min(p.y, a.alto + a.altezza - MIN_VISIBILE)),
  };
}
