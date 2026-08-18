/* Smistamento per topic — l'unico ingresso dei dati nel renderer.
 *
 * Il renderer non chiede: riceve. `app/preload.js` espone `jarvis.onMessage`,
 * questo modulo lo divide per topic, e i componenti si iscrivono a cio' che
 * capiscono. Un solo punto di ingresso significa un solo punto in cui guardare
 * quando un dato non arriva.
 */

export function creaBus(sorgente) {
  const iscritti = new Map(); // topic -> Set<cb>
  const perStato = new Set();

  function su(topic, cb) {
    if (!iscritti.has(topic)) iscritti.set(topic, new Set());
    iscritti.get(topic).add(cb);
    return () => iscritti.get(topic).delete(cb);
  }

  function suStato(cb) {
    perStato.add(cb);
    return () => perStato.delete(cb);
  }

  function pubblica(msg) {
    for (const cb of iscritti.get(msg?.topic) ?? []) cb(msg);
  }

  function pubblicaStato(s) {
    for (const cb of perStato) cb(s);
  }

  // La sorgente e' un argomento: in Electron e' `window.jarvis`, nei test e
  // nella galleria e' un finto. Il bus non sa quale dei due sta servendo.
  sorgente?.onMessage?.(pubblica);
  sorgente?.onStatus?.(pubblicaStato);

  return { su, suStato, pubblica, pubblicaStato };
}
