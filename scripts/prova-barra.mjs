/* Il livello della barra torna indietro da solo — T4 del piano della fixture.
 *
 *   node scripts/prova-barra.mjs
 *
 * ## Che cosa provava, e perche' nessuno se n'era accorto
 *
 * `barra.js` scriveva `degraded` su un `agent.advisory` critico e non lo
 * toglieva piu' nessuno: l'unico altro scrittore era `state.snapshot`, che
 * arriva UNA volta per sessione. La sorgente e' `package_temp_c > 75` valutata
 * a 2,5 Hz — **un campione** inchiodava la barra per tutta la sessione.
 * `DEBORDO-R99.md` riporta «barra passata a DEGRADED (temp 55 °C)»: 55 e'
 * SOTTO la soglia, ed era il latch, non la temperatura.
 *
 * ## Perche' la galleria e non la scrivania viva
 *
 * Perche' il difetto **non e' misurabile** dove sta il dato vero. Servirebbe
 * far salire il processore sopra i 75 °C al momento giusto: un criterio che
 * dipende dal meteo dentro il case non e' un criterio. Il montaggio `chrome`
 * ha gia' un bus finto con `manda()`, e la galleria e' il posto che §11.7
 * assegna alla verifica dei componenti.
 *
 * ⚠️ **La fixture di misura non puo' vedere questo.** La registrazione
 * `4d5edf35cfdb64af` ha `avvisiCritici: 0` — misurato, non supposto — quindi
 * riproducendola il ramo non si percorre mai. Ed era prevedibile prima:
 * il Δ del latch e' ~560 px su 1 294 848, lo **0,043 %**, sotto la precisione
 * con cui `densita.mjs` stampa. Una prova a pixel avrebbe dichiarato
 * «soddisfatto» qualunque cosa fosse successa.
 *
 * ## L'ordine dei criteri
 *
 * `MISURABILE` prima di tutto, come in `prova-catalogo.mjs`: se l'advisory non
 * cambia niente, «torna a nominal» e' vero **per assenza del fenomeno**, che e'
 * §11.7 regola 4 e non conta come verde.
 */

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

import { PORTA, avvia } from "./serve.mjs";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const DOVE_ESITO = "docs/acceptance/BARRA-AVVISO.json";
/* ⚠️ Il limite dell'impronta, dichiarato: copre questi tre. Se a rompere il
   ritorno fosse un quarto file — per esempio un montaggio che smette di
   mandare `state.snapshot` — la guardia non se ne accorgerebbe. Si allarga
   aggiungendo il file, non sperando che basti. */
const FONTI = ["ui/src/desk/barra.js", "ui/src/desk/avviso.js",
               "ui/src/gallery/mounts/chrome.js"];
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

const server = await avvia();
const browser = await chromium.launch();
const pagina = await browser.newPage({ viewport: { width: 1920, height: 1080 } });

const errori = [];
pagina.on("pageerror", (e) => errori.push(String(e)));
pagina.on("console", (m) => { if (m.type() === "error") errori.push(m.text()); });

await pagina.goto(`http://127.0.0.1:${PORTA}/gallery.html?component=chrome`,
                  { waitUntil: "networkidle" });
/* ⚠️ NON `waitForFunction` con una stringa: il CSP della galleria e' quello
   dell'app — `script-src 'self'` con l'hash, senza `unsafe-eval` — e valutare
   una stringa lo viola. Playwright riporta l'EvalError e la prova muore prima
   di misurare. Si aspetta con `evaluate`, che passa una funzione. */
for (let i = 0; i < 150; i++) {
  if (await pagina.evaluate(() => window.__chrome !== undefined)) break;
  await dorme(100);
}
if (!(await pagina.evaluate(() => window.__chrome !== undefined))) {
  console.error("il montaggio `chrome` non ha esposto window.__chrome in 15 s");
  process.exit(2);
}

const livello = () => pagina.evaluate(
  () => document.querySelector(".brr").dataset.livello);
const scritta = () => pagina.evaluate(
  () => document.querySelector(".brr__livello").textContent);
const manda = (msg) => pagina.evaluate((m) => window.__chrome.bus.manda(m), msg);
const AVVISO_MS = await pagina.evaluate(() => window.__chrome.AVVISO_MS);

const m = {};
m.avvisoMs = AVVISO_MS;
m.aRiposo = await livello();

// ① l'accento si accende
await manda({ topic: "agent.advisory", level: "critical", livello: "critical" });
m.subitoDopo = await livello();
m.scrittaDopo = await scritta();

// ② e si spegne da solo. `+ 300` perche' `barra.js` arma il timer a
//    `AVVISO_MS + 20`: si aspetta il timer, non la durata.
await dorme(AVVISO_MS + 300);
m.dopoLAttesa = await livello();

// ③ un advisory NON critico non deve toccare niente (§16: e' rumore, non una
//    notizia). Senza questo, «l'accento si accende» passerebbe anche se la
//    barra reagisse a qualunque advisory.
await manda({ topic: "agent.advisory", level: "warning" });
m.dopoUnoNonCritico = await livello();

// ④ il livello STABILE resta di chi lo sa: dopo che l'accento e' scaduto, la
//    barra deve tornare a cio' che `state.snapshot` ha detto per ultimo — e se
//    quello e' `degraded`, ci deve RESTARE. E' l'altra meta' del difetto: un
//    accento a tempo che cancellasse lo stato vero sarebbe lo stesso errore al
//    contrario.
await manda({
  topic: "state.snapshot", fase: 9,
  core: { pid: 48219, uptime_s: 15153 },
  voce: { abilitata: false, auth: { stato: "degraded_llm" } },
});
m.stabileDegradato = await livello();
await manda({ topic: "agent.advisory", level: "critical" });
await dorme(AVVISO_MS + 300);
m.dopoLAttesaConStabileDegradato = await livello();

await browser.close();
await new Promise((r) => server.close(r));

const criteri = [
  ["nessun errore di console", errori.length === 0, errori.join(" · ") || "nessuno"],
  ["a riposo la barra dice nominal", m.aRiposo === "nominal", m.aRiposo],
  ["l'accento e' MISURABILE",
   m.subitoDopo === "degraded" && m.subitoDopo !== m.aRiposo,
   `${m.aRiposo} -> ${m.subitoDopo}` +
   (m.subitoDopo === m.aRiposo
     ? " — l'advisory non ha cambiato niente: i criteri sotto sarebbero veri per assenza"
     : "")],
  ["la scritta segue il dato", m.scrittaDopo === "degraded", m.scrittaDopo],
  [`l'accento SCADE dopo ${AVVISO_MS} ms`, m.dopoLAttesa === "nominal",
   `${m.subitoDopo} -> ${m.dopoLAttesa}` +
   (m.dopoLAttesa === "degraded" ? " — il latch e' ancora li'" : "")],
  ["un advisory non critico non tocca niente", m.dopoUnoNonCritico === "nominal",
   m.dopoUnoNonCritico],
  ["state.snapshot puo' dire degraded", m.stabileDegradato === "degraded",
   m.stabileDegradato],
  ["e l'accento non lo cancella scadendo",
   m.dopoLAttesaConStabileDegradato === "degraded",
   m.dopoLAttesaConStabileDegradato],
];

console.error("");
for (const [nome, ok, dettaglio] of criteri) {
  console.error(`  ${ok ? "ok  " : "NO  "}${nome.padEnd(40)} ${dettaglio}`);
}
const falliti = criteri.filter(([, ok]) => !ok);
console.error("");
console.error(falliti.length
  ? `IL LIVELLO NON TORNA INDIETRO — ${falliti.length} condizioni su ${criteri.length}: ` +
    falliti.map(([n]) => n).join(" · ")
  : `il livello torna indietro da solo — ${criteri.length} condizioni su ${criteri.length}`);

const impronta = createHash("sha256");
for (const f of FONTI) impronta.update(readFileSync(join(RADICE, f)));
writeFileSync(join(RADICE, DOVE_ESITO), JSON.stringify({
  _: "GENERATO da scripts/prova-barra.mjs — non modificare a mano",
  fonti: FONTI,
  impronta: impronta.digest("hex").slice(0, 16),
  soddisfatto: falliti.length === 0,
  criteri: criteri.map(([nome, ok, dettaglio]) => ({ nome, ok, dettaglio })),
  misure: m,
}, null, 2) + "\n");
console.error(`\n  esito      ${DOVE_ESITO}`);

process.exit(falliti.length ? 1 : 0);
