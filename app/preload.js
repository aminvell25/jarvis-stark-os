/* Preload — l'unica superficie che il renderer vede del mondo esterno.
 *
 * SPEC §6.3: «Il preload espone SOLO un bridge tipizzato verso il WebSocket.
 * Mai `require`, `fs`, `child_process`.»
 *
 * Tre funzioni, tutte in RICEZIONE. Il renderer non puo' inviare nulla al
 * core, e in Fase 1b non ne ha motivo. Quando in Fase 2 servira' — la
 * risposta a `fs.confirm_request` — sara' una quarta funzione aggiunta di
 * proposito, con la sua giustificazione, non una porta gia' aperta.
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
});
