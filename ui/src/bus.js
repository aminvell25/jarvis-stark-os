/* Smistamento per topic — l'unico ingresso dei dati nel renderer.
 *
 * Il renderer non chiede: riceve. `app/preload.js` espone `jarvis.onMessage`,
 * questo modulo lo divide per topic, e i componenti si iscrivono a cio' che
 * capiscono. Un solo punto di ingresso significa un solo punto in cui guardare
 * quando un dato non arriva.
 *
 * ## L'ultimo messaggio si conserva, e si riconsegna (§13)
 *
 * Il core manda una volta sola, a chi si collega, i dati che non cambiano a
 * 2,5 Hz: l'albero dei sorgenti, i fusi, l'archivio, il contenuto della
 * workspace. E' il verso giusto — il renderer non puo' CHIEDERE (§6.3) — ma
 * apre un problema che prima non esisteva: la scrivania compone un workspace
 * la prima volta che ci si entra, e un pannello nato dopo quel messaggio non
 * lo vedrebbe mai.
 *
 * Quindi il bus tiene l'ULTIMO messaggio per topic e lo riconsegna a chi si
 * iscrive dopo. Non e' una cache di comodo: e' la stessa idea che
 * `core/ws_server.py` applica gia' al proprio livello — «la UI e' senza
 * stato: il core e' l'unica fonte di verita', quindi ogni client riceve lo
 * stato completo prima di qualunque delta».
 *
 * ⚠️ **L'ultimo, non tutti.** Per un topic che e' un FLUSSO — `news.card` ne
 * manda uno per notizia — chi arriva tardi vede l'ultima carta, non le
 * precedenti. E' una perdita vera e dichiarata: conservarle tutte vorrebbe
 * dire decidere qui quanto e' lunga la memoria di ogni pannello, che e' una
 * decisione dei pannelli.
 */

export function creaBus(sorgente) {
  const iscritti = new Map(); // topic -> Set<cb>
  const perStato = new Set();
  const perOgni = new Set();
  const ultimo = new Map();   // topic -> ultimo messaggio visto

  function su(topic, cb) {
    if (!iscritti.has(topic)) iscritti.set(topic, new Set());
    iscritti.get(topic).add(cb);
    // Chi si iscrive dopo non deve restare all'oscuro di cio' che e' gia'
    // passato. Asincrono: `crea()` non ha ancora restituito quando il modulo
    // si collega, e consegnare dentro `su()` chiamerebbe `aggiorna` su un
    // pannello che si sta ancora costruendo.
    if (ultimo.has(topic)) queueMicrotask(() => cb(ultimo.get(topic)));
    return () => iscritti.get(topic).delete(cb);
  }

  /** Ogni messaggio, qualunque topic. Per la traccia e per il log dei byte. */
  function suOgni(cb) {
    perOgni.add(cb);
    return () => perOgni.delete(cb);
  }

  function suStato(cb) {
    perStato.add(cb);
    return () => perStato.delete(cb);
  }

  function pubblica(msg) {
    if (msg?.topic) ultimo.set(msg.topic, msg);
    for (const cb of iscritti.get(msg?.topic) ?? []) cb(msg);
    for (const cb of perOgni) cb(msg);
  }

  function pubblicaStato(s) {
    for (const cb of perStato) cb(s);
  }

  // La sorgente e' un argomento: in Electron e' `window.jarvis`, nei test e
  // nella galleria e' un finto. Il bus non sa quale dei due sta servendo.
  sorgente?.onMessage?.(pubblica);
  sorgente?.onStatus?.(pubblicaStato);

  return { su, suOgni, suStato, pubblica, pubblicaStato, ultimo: (t) => ultimo.get(t) };
}
