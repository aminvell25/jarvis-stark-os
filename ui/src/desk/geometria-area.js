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

/** Lo stesso, per un'icona libera: e' un oggetto piu' piccolo di un pannello,
 *  e non ha una testa da afferrare — basta che si veda.
 *
 *  ⚠️ Stava in `desk/icone.js` con scritto accanto «stesso numero e stessa
 *  ragione del MIN_VISIBILE dei pannelli». **Non era lo stesso numero**: 40
 *  contro 80, e il commento affermava un'uguaglianza falsa. La ragione e'
 *  davvero la stessa; il numero no, e adesso stanno vicini dove si vede. */
export const MIN_VISIBILE_ICONA = 40;

/** LA REGOLA, in un posto solo: un punto riportato dentro l'area.
 *
 * ## Perche' esiste
 *
 * Fino al 25 agosto 2026 questa aritmetica era scritta in TRE posti — qui per i
 * pannelli, in `desk/icone.js` per le icone, in `core/layout.py::adatta` per il
 * disco — e i tre non erano d'accordo su due assi diversi:
 *
 *   - sullo SPAZIO: il core tagliava contro `[0, altezza - min]` invece che
 *     `[alto, alto + altezza - min]`, cioe' una banda traslata di quanto e'
 *     alta la barra. Chiuso in `16f802b`.
 *   - sul MINIMO: il renderer usava 40 per le icone, il core 80 per tutto.
 *     Restava una fascia di 40 px in cui il renderer accettava una posizione e
 *     il core la spostava.
 *
 * Dentro il renderer adesso il proprietario e' uno. Attraverso il confine col
 * core non si puo' importare, e allora l'accordo si **misura**:
 * `tests/test_geometria_area.py::TestITreRitagliSonoUNO` fa girare la stessa
 * tabella di casi nei due linguaggi e confronta i risultati. */
export function dentroPunto(x, y, a, minimo = MIN_VISIBILE) {
  return {
    x: Math.round(Math.max(a.sinistra, Math.min(x, a.sinistra + a.larghezza - minimo))),
    y: Math.round(Math.max(a.alto, Math.min(y, a.alto + a.altezza - minimo))),
  };
}

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
  // Un pannello e' un punto piu' una dimensione: il punto lo fa `dentroPunto`,
  // la dimensione qui. Prima le due righe del punto erano scritte a mano, ed e'
  // il posto da cui la copia di `icone.js` era nata.
  return { ...p, larghezza, altezza, ...dentroPunto(p.x, p.y, a) };
}
