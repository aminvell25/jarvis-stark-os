/* Preload — l'unica superficie che il renderer vede del mondo esterno.
 *
 * SPEC §6.3: «Il preload espone SOLO un bridge tipizzato verso il WebSocket.
 * Mai `require`, `fs`, `child_process`.»
 *
 * CINQUE funzioni. Tre in ricezione, due in invio.
 *
 * `confirm()` e' la quarta, aggiunta di proposito e non per comodita': §6.2
 * vuole che l'utente veda il path risolto e risponda, e questa e' la sola via
 * per cui quella risposta torna al core.
 *
 * ## `salvaLayout()` e' la quinta, e la dichiarazione e' questa
 *
 * Il test in `tests/test_ws_contract.py` esiste per far fallire la suite
 * finche' qualcuno non dice perche' ne serve un'altra. §26.10 punto 1: senza
 * persistenza, un'icona trascinata sul fondo che al riavvio torna al suo
 * posto e' peggio di un'icona che non si puo' trascinare.
 *
 * ⚠️ **E' il primo canale che il renderer INIZIA.** Le altre due in uscita —
 * `confirm` e la cattura di ARGUS — sono RISPOSTE: portano l'identificativo di
 * una domanda che il core ha gia' posto, e non se ne possono inventare. Questa
 * no. La proprieta' che la tiene innocua e' un'altra, ed e' scritta anche in
 * `core/layout.py`:
 *
 *   **Non chiede un'operazione: dichiara uno stato dell'ambiente.**
 *   Il core non la ESEGUE, la RICORDA. Non nomina un percorso, non nomina un
 *   tool, non ha un campo libero, e il topic non lo sceglie il renderer.
 *
 * E' il pattern che erediteranno Alt+Spazio, Esc, le scene e il catalogo:
 * **una funzione per intenzione, coi campi che quella intenzione ha**, mai un
 * `manda(topic, oggetto)` generico. Un canale generico e' una superficie
 * grande quanto la fantasia di chi ci scrive sopra.
 *
 * Cosa NON puo' fare, ed e' il punto: non puo' CHIEDERE un'operazione. Un
 * renderer compromesso — e in Fase 6 ospita `<webview>` con contenuto non
 * fidato — non ha modo di far accadere nulla che l'utente non stia gia'
 * guardando; col layout, il peggio che ottiene e' una scrivania disposta male
 * al prossimo avvio.
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

  /**
   * Manda al core la disposizione dell'ambiente (§26.10 punto 1).
   *
   * I campi si copiano UNO PER UNO e si convertono qui: quello che passa e'
   * cio' che questa firma nomina, non quello che il chiamante ha
   * nell'oggetto. Un `{...layout}` lascerebbe passare qualunque chiave, e il
   * `extra="forbid"` del core farebbe fallire il salvataggio invece di
   * proteggere — cioe' la difesa si trasformerebbe in un guasto.
   *
   * ⚠️ `icone[].nome` porta un nome di FILE, che e' dato non fidato: e' una
   * ETICHETTA e non un percorso, e ne' questo ponte ne' il core lo trattano
   * mai come tale. Non si accorcia e non si ripulisce qui: chi decide che cosa
   * e' accettabile e' lo schema di `core/layout.py`, in un posto solo. Qui si
   * garantisce soltanto che sia una stringa.
   */
  /**
   * Chiede al core di cambiare UNA impostazione (§26.7).
   *
   * ⚠️ **Chiede, non scrive.** Il renderer non tocca il disco (invariante 1):
   * di la' c'e' `imposta_valore`, che ha `side_effect=True` e apre la conferma
   * di §6.2. Quello che parte da qui e' una domanda, e la risposta la da'
   * l'utente in un riquadro che mostra il percorso risolto.
   *
   * Il valore si restringe qui ai tre tipi che una foglia di `settings.toml`
   * puo' avere. Un oggetto o un array che passassero di qui sarebbero un modo
   * di riscrivere una STRUTTURA — le radici consentite, per dire — con un
   * messaggio che dichiara di cambiare uno scalare.
   */
  impostaValore: (chiave, valore) =>
    ipcRenderer.send("jarvis:impostazione", {
      chiave: String(chiave ?? ""),
      valore:
        typeof valore === "boolean" || typeof valore === "number"
          ? valore
          : String(valore ?? ""),
    }),

  /**
   * Chiede al core di aggiungere o togliere UN elemento da una lista di
   * `settings.toml` (§26.7, il residuo delle strutture).
   *
   * ⚠️ **Un verbo suo, e non un `impostaValore` allargato.** Il commento di
   * `impostaValore` qui sopra dichiara perche' un array non passa di la': «un
   * oggetto o un array che passassero di qui sarebbero un modo di riscrivere
   * una STRUTTURA — le radici consentite, per dire — con un messaggio che
   * dichiara di cambiare uno scalare». Quella frase resta vera perche' quel
   * canale non cambia: questo e' un altro canale, che dichiara cio' che fa.
   *
   * E non porta MAI l'elenco: porta un verbo e un record, i cui campi si
   * copiano uno per uno come tutto il resto che attraversa il ponte.
   */
  impostaElemento: (chiave, operazione, elemento) =>
    ipcRenderer.send("jarvis:elemento", {
      chiave: String(chiave ?? ""),
      operazione: operazione === "togli" ? "togli" : "aggiungi",
      elemento: Object.fromEntries(
        Object.entries(elemento ?? {})
          .slice(0, 8)
          .map(([k, v]) => [String(k).slice(0, 32), String(v ?? "").slice(0, 512)])),
    }),

  salvaLayout: (layout) =>
    ipcRenderer.send("jarvis:layout", {
      area: {
        sinistra: Number(layout?.area?.sinistra) | 0,
        alto: Number(layout?.area?.alto) | 0,
        larghezza: Number(layout?.area?.larghezza) | 0,
        altezza: Number(layout?.area?.altezza) | 0,
      },
      pannelli: (Array.isArray(layout?.pannelli) ? layout.pannelli : []).map((p) => ({
        id: String(p?.id ?? ""),
        x: Number(p?.x) | 0,
        y: Number(p?.y) | 0,
        larghezza: Number(p?.larghezza) | 0,
        altezza: Number(p?.altezza) | 0,
        z: Number(p?.z) | 0,
        massimizzato: !!p?.massimizzato,
        // ADR-013: senza questo, `nascosto` non attraversa il ponte e il core
        // non distingue un pannello che si vede da uno nascosto con Alt+H.
        nascosto: !!p?.nascosto,
      })),
      icone: (Array.isArray(layout?.icone) ? layout.icone : []).map((i) => ({
        tipo: i?.tipo === "file" ? "file" : "modulo",
        nome: String(i?.nome ?? ""),
        x: Number(i?.x) | 0,
        y: Number(i?.y) | 0,
        dentro: i?.dentro == null ? null : String(i.dentro),
      })),
      cartelle: (Array.isArray(layout?.cartelle) ? layout.cartelle : []).map((c) => ({
        id: String(c?.id ?? ""),
        x: Number(c?.x) | 0,
        y: Number(c?.y) | 0,
        etichetta: String(c?.etichetta ?? ""),
        aperta: !!c?.aperta,
      })),
      scena: layout?.scena == null ? null : String(layout.scena),
    }),
});
