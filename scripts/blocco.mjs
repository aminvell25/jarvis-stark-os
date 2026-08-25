/* Un solo Electron per volta — e non e' prudenza, e' una misura.
 *
 * ## Il numero
 *
 * Otto giri di `npm run scrivania:fixture` lanciati uno dietro l'altro senza
 * pausa hanno dato **sette PNG diversi**, con differenze fino al **76 % del
 * fotogramma** e un giro a 41 render di three.js invece di 5. Gli stessi giri
 * con otto secondi di pausa: **identici, sei su sei, 5 render ogni volta**.
 *
 * La causa e' la contesa: l'Electron precedente non ha ancora rilasciato GPU e
 * CPU, la scrivania compone sotto carico e lo scatto prende un fotogramma non
 * assestato. Con la finestra che nemmeno arriva a massimizzarsi: misurato uno
 * scatto a **1514x821** invece di 1536x843, cioe' una misura di densita' fatta
 * su una scrivania di un'altra dimensione.
 *
 * E' anche la spiegazione della deviazione «1 su 16» che
 * `FIXTURE-DI-MISURA.md` aveva dichiarato **non attribuita**: stessa firma, un
 * conteggio di render fuori scala.
 *
 * ## Perche' un file e non una nota nel protocollo
 *
 * «Mai insieme: scatti e suite» sta scritto in tre documenti di accettazione, e
 * oggi l'ho violato due volte in dieci minuti — una guardia rossa e uno scatto
 * a 1514x821, **entrambi verdi al secondo tentativo con una pausa**. Un vincolo
 * che chiede di ricordarsene non e' un vincolo: e' un'abitudine, e le abitudini
 * si perdono esattamente quando si e' di fretta.
 *
 * ## ⚠️ Perche' NON lo prendono le prove
 *
 * Il primo giro lo aveva messo anche in `prova-icone.mjs`, `prova-gesti.mjs`,
 * `prova-contrazione.mjs` e `prova-catalogo.mjs`, che aprono un Electron vero
 * come gli scatti. **Ha rotto la suite**: da 65 s a 240 s, con venti errori.
 * Quelle prove girano dentro pytest, che gia' le esegue una per volta; il
 * blocco le metteva in coda con se' stesse, e l'attesa scadeva dentro la
 * fixture di pytest.
 *
 * Ritirato da li'. Il blocco copre i comandi che MISURANO — `npm run
 * scrivania`, `scrivania:fixture`, `verifica:scrivania`, `nucleo`,
 * `marchio:stati`, tutti attraverso `scripts/app.mjs` — e la serializzazione
 * delle prove resta di pytest, che ce l'ha per costruzione.
 *
 * Resta scoperto un caso: lanciare uno scatto MENTRE gira la suite. Il blocco
 * non lo vede, perche' la suite non lo prende. Il protocollo «mai insieme»
 * resta scritto, e questa volta con il numero accanto.
 *
 * ## Dove sta
 *
 * Accanto al socket, cioe' in `$XDG_RUNTIME_DIR/jarvis-os/` a 0700
 * (invariante 7): non e' raggiungibile dalla rete e sparisce al riavvio.
 *
 * ⚠️ **Un lock orfano si rimuove, non blocca per sempre.** Se il pid dentro non
 * e' vivo il file e' un residuo di un processo ucciso, e un blocco che
 * sopravvive a chi lo teneva impedirebbe di lavorare invece di proteggere una
 * misura.
 */

import { existsSync, openSync, readFileSync, unlinkSync, writeSync } from "node:fs";
import { dirname, join } from "node:path";

/** Prende il blocco accanto a `socket`, mettendosi in CODA se e' occupato.
 *
 * ⚠️ Aspetta invece di fallire subito, e la ragione e' un rosso finto misurato:
 * un `prova-icone.mjs` appena finito ha ancora il proprio nodo in chiusura, il
 * pid nel lock risulta vivo per una frazione di secondo, e la prova successiva
 * moriva con «c'e' gia' un Electron in corso» mentre non ce n'era piu' nessuno.
 * Un blocco che trasforma una corsa in un fallimento e' peggio della corsa: il
 * fallimento sembra un difetto del codice.
 */
export function prendi(socket, { attesaMs = 90_000, passoMs = 500 } = {}) {
  const scadenza = Date.now() + attesaMs;
  for (;;) {
    const esito = _prova(socket);
    if (esito.preso || Date.now() >= scadenza) return esito;
    // Attesa attiva e non `setTimeout`: `prendi` e' chiamata prima di
    // qualunque `await` in script che sono sincroni fin qui, e renderla
    // asincrona vorrebbe dire propagare un `await` in cinque file.
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, passoMs);
  }
}

function _prova(socket) {
  const dove = join(dirname(socket), "scatto.lock");
  const scrivi = () => writeSync(openSync(dove, "wx"), String(process.pid));
  try {
    scrivi();
  } catch {
    const chi = existsSync(dove) ? readFileSync(dove, "utf-8").trim() : "?";
    let vivo = false;
    try { process.kill(Number(chi), 0); vivo = true; } catch { vivo = false; }
    if (vivo) return { preso: false, chi };
    console.error(`  blocco  rimosso un ${dove} orfano del pid ${chi}`);
    try { unlinkSync(dove); } catch { /* corsa con un altro: chi vince, vince */ }
    try { scrivi(); } catch { return { preso: false, chi: "?" }; }
  }
  let lasciato = false;
  return {
    preso: true,
    lascia() {
      if (lasciato) return;
      lasciato = true;
      try { unlinkSync(dove); } catch { /* gia' sparito */ }
    },
  };
}

/** Il messaggio, in un posto solo: cinque script lo stampano. */
export function spiega(chi) {
  return `c'e' gia' un Electron di JARVIS in corso (pid ${chi}).\n` +
    "Due insieme si contendono la GPU e la misura non vale: sette PNG diversi " +
    "su otto giri, e uno scatto a 1514x821 invece di 1536x843.";
}
