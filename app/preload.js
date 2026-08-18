/* Preload — l'unica superficie che il renderer vede del mondo esterno.
 *
 * SPEC §6.3: «Il preload espone SOLO un bridge tipizzato verso il WebSocket.
 * Mai `require`, `fs`, `child_process`.»
 *
 * QUATTRO funzioni. Tre in ricezione, e dalla Fase 2 una sola in invio.
 *
 * `confirm()` e' la quarta, aggiunta di proposito e non per comodita': §6.2
 * vuole che l'utente veda il path risolto e risponda, e questa e' la sola via
 * per cui quella risposta torna al core. Un test in `tests/test_ws_contract.py`
 * sorveglia questo elenco: una quinta funzione fara' fallire la suite finche'
 * qualcuno non dichiarera' perche' serve.
 *
 * Cosa NON puo' fare, ed e' il punto: non puo' CHIEDERE un'operazione. Puo'
 * solo rispondere si' o no a una domanda che il core ha gia' posto, citandone
 * l'identificativo. Un renderer compromesso — e in Fase 6 ospitera'
 * `<webview>` con contenuto non fidato — non ha modo di far accadere nulla
 * che l'utente non stia gia' guardando.
 *
 * L'oggetto socket non esce mai di qui: se uscisse, il renderer potrebbe
 * mandare qualunque cosa al core, e in Fase 6 il renderer ospitera'
 * `<webview>` con contenuto non fidato.
 */

const { contextBridge, ipcRenderer } = require("electron");

function ascolta(canale, cb) {
  const listener = (_evento, dato) => cb(dato);
  ipcRenderer.on(canale, listener);
  return () => ipcRenderer.removeListener(canale, listener);
}

contextBridge.exposeInMainWorld("jarvis", {
  /** Messaggi dal core. Ritorna la funzione per smettere di ascoltare. */
  onMessage: (cb) => ascolta("jarvis:message", cb),

  /** Cambi di stato del collegamento: connesso / disconnesso / in-riconnessione. */
  onStatus: (cb) => ascolta("jarvis:status", cb),

  /** Stato corrente, per chi si registra dopo il primo cambio. */
  status: () => ipcRenderer.invoke("jarvis:status"),

  /**
   * Risponde a una `fs.confirm_request`. L'unica cosa che il renderer manda.
   * `requestId` viene dalla richiesta: non se ne possono inventare.
   */
  confirm: (requestId, approvato) =>
    ipcRenderer.send("jarvis:confirm", { id: String(requestId), approvato: !!approvato }),
});
