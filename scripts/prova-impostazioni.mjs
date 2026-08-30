/* Le strutture dalla pagina, dal vivo — §26.7, ciclo §11.7 passo 0 regola 2.
 *
 * `tests/test_le_strutture_si_cambiano.py` prova il core; il ciclo di galleria
 * prova il pannello. Nessuno dei due attraversa il confine, e §11.7 dice che
 * «cio' che attraversa un confine si prova attraversando quel confine»: qui il
 * giro passa da renderer, preload, ponte, socket, core, conferma e disco.
 *
 * ⚠️ **La fetta 5 ha trovato quattro difetti proprio qui**, con 41 test verdi:
 * fra questi `nascosto` che cadeva nella TERZA copia campo-per-campo fra
 * renderer e core. Questa prova esiste perche' quella lezione non valga una
 * volta sola.
 *
 *   XDG_CONFIG_HOME=<albero>/cfg XDG_DATA_HOME=<albero>/dati \
 *     uv run python -m core.engine &
 *   node scripts/prova-impostazioni.mjs <socket> <cartella-scatti>
 *
 * Guida Electron via CDP come `scripts/verifica-conferma.mjs`, e per la stessa
 * ragione: un gancio di prova dentro `app/main.js` sarebbe superficie in piu'
 * in un file che vale la pena tenere piccolo.
 *
 * Stampa una riga JSON per passo. L'ultima porta l'esito.
 */
import { spawn } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electron from "electron";
import { chromium } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const PORTA = 9334;
const [, , socket, cartella, impostazioni] = process.argv;
/** Il file com'e' adesso. Serve al passo del RIFIUTO: «non e' cambiato niente»
 *  si dimostra confrontando, non guardando l'assenza di un errore. */
const suDisco = () => (impostazioni ? readFileSync(impostazioni, "utf-8") : null);
const attendi = (ms) => new Promise((r) => setTimeout(r, ms));

const figlio = spawn(
  electron,
  [resolve(RADICE, "app", "main.js"), "--socket", socket,
   `--remote-debugging-port=${PORTA}`],
  { stdio: ["ignore", "pipe", "pipe"], cwd: RADICE },
);
figlio.stderr.on("data", () => {});

let browser;
for (let i = 0; i < 60 && !browser; i++) {
  try { browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORTA}`); }
  catch { await attendi(500); }
}
if (!browser) { console.error("CDP non raggiungibile"); figlio.kill(); process.exit(1); }
const pagina = browser.contexts()[0].pages()[0];
await pagina.waitForFunction(() => !!window.jarvis?.impostaElemento, null,
                             { timeout: 60_000 });
await attendi(2500);
if (cartella) mkdirSync(resolve(RADICE, cartella), { recursive: true });

/* Il ponte esiste? E' il primo fatto: se `impostaElemento` non fosse esposta,
 * tutto il resto direbbe soltanto che il core funziona. */
console.log(JSON.stringify({
  passo: "ponte",
  verbi: await pagina.evaluate(() => Object.keys(window.jarvis).sort()),
}));

/** Un giro: chiede dal RENDERER, legge la conferma, e risponde.
 *
 * `azione` e' «approva» o «rifiuta». Il secondo caso e' l'invariante 3 dal lato
 * che conta di piu': una conferma serve a poter dire di NO, e un no che scrive
 * lo stesso non e' una conferma.
 */
async function giro(nome, chiave, operazione, elemento, scatto,
                    azione = "approva") {
  await pagina.evaluate(([k, o, e]) => {
    window.__esitoImpostazione = null;
    window.jarvis.impostaElemento(k, o, e);
  }, [chiave, operazione, elemento]);

  let id = null;
  for (let i = 0; i < 120 && !id; i++) {
    id = await pagina.evaluate(() => window.__jarvisConferma).catch(() => null);
    if (!id) await attendi(250);
  }
  if (!id) {
    console.log(JSON.stringify({ passo: nome, errore: "nessuna conferma a schermo" }));
    return false;
  }

  /* ⚠️ **Cio' che l'utente LEGGE**, estratto dal DOM e non presunto. Per
   * `fs.allowed_roots` e' la condizione a cui quella chiave e' uscita dalle
   * bloccate di §26.7: la conferma deve mostrare il percorso RISOLTO. */
  const mostrato = await pagina.evaluate(() => ({
    riepilogo: document.querySelector("[data-riepilogo]")?.textContent?.trim(),
    percorsi: [...document.querySelectorAll(".cnf__path")]
      .map((e) => e.textContent.trim()),
    righe: [...document.querySelectorAll(".cnf__op, .cnf__riga")]
      .map((e) => e.textContent.replace(/\s+/g, " ").trim()).slice(0, 6),
  }));
  console.log(JSON.stringify({ passo: nome, id, mostrato }));

  if (scatto && cartella) {
    await pagina.screenshot({ path: join(resolve(RADICE, cartella), scatto) });
  }
  const prima = suDisco();
  await pagina.click(azione === "rifiuta" ? "[data-rifiuta]" : "[data-approva]");
  await attendi(2000);
  if (azione === "rifiuta") {
    console.log(JSON.stringify({
      passo: `${nome}/dopo-il-rifiuto`,
      fileIdentico: prima !== null && prima === suDisco(),
      confermaChiusa: !(await pagina.evaluate(() => !!window.__jarvisConferma)),
    }));
  }
  return true;
}

await giro("frase-di-wake", "voice.wake.phrases", "aggiungi",
           { say: "jarvis buongiorno", action: "scene:avvio" },
           "conferma-frase.png");

/* La radice: il caso per cui la conferma mostra il percorso risolto. Si manda
 * un percorso STORTO — con un `..` dentro — e si guarda che cosa legge chi
 * approva. */
/* ⚠️ Una cartella NUOVA, non una gia' consentita: dal 30 agosto il piano
 * rifiuta un doppione **senza aprire la conferma**, e chiedere `~/Scaricati`
 * per una via storta proverebbe quel rifiuto invece del percorso risolto. */
/* ⚠️ Nel temporaneo del sistema, non accanto al repository: la prima stesura
 * usava `resolve(RADICE, "..")` e lasciava cartelle nella cartella dei
 * progetti del Signore. Una prova che sporca fuori dal proprio albero e' una
 * prova che qualcuno dovra' pulire a mano. */
const nuova = join(tmpdir(), `jarvis-prova-radice-${process.pid}`);
mkdirSync(nuova, { recursive: true });
const storta = join(nuova, "sotto", "..", ".");
mkdirSync(join(nuova, "sotto"), { recursive: true });
await giro("radice-storta", "fs.allowed_roots", "aggiungi",
           { valore: storta }, "conferma-radice.png");

/* ⚠️ **Il NO.** Fino al 31 agosto il giro dal vivo approvava sempre, e che
 * «rifiuta» lasciasse il file intatto era provato solo in Python
 * (`test_confirm_e2e.py`), senza attraversare la finestra. Una conferma serve a
 * poter dire di no: se il no non si prova, si e' provata meta' dell'invariante
 * 3 — e per giunta la meta' che non protegge niente. */
await giro("frase-rifiutata", "voice.wake.phrases", "aggiungi",
           { say: "jarvis questa no", action: "listen" },
           "conferma-rifiutata.png", "rifiuta");

/* E il rifiuto dell'altra specie: una lista che la pagina non offre non deve
 * nemmeno far nascere una conferma. */
await pagina.evaluate(() => {
  window.jarvis.impostaElemento("ui.scene", "aggiungi", { valore: "x" });
});
await attendi(2500);
console.log(JSON.stringify({
  passo: "lista-non-offerta",
  confermaAperta: await pagina.evaluate(() => !!window.__jarvisConferma),
}));

await browser.close();
figlio.kill();
