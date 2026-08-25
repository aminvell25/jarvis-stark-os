/* Avvia l'app Electron.
 *
 * Chiede il percorso del socket al core e lo passa a Electron: il codice
 * dell'app non deve sapere che cos'e' `$XDG_RUNTIME_DIR` (invariante 29).
 * Su Windows la stessa riga restituira' una named pipe senza che main.js
 * cambi.
 *
 *   npm run app
 *   npm run app -- --screenshot shots/app.png
 */

import { execFileSync, spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electron from "electron";

import { prendi, spiega } from "./blocco.mjs";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));

/* ── il modo di MISURA — §11.9, seconda eccezione ──────────────────────────
 *
 * Con `--fixture` la scrivania non si collega al core: si collega a un socket
 * di RIPRODUZIONE che emette una sessione registrata. Serve perche' due
 * sessioni vive davano `L>60` 26,1 % e 25,3 % e la differenza non era
 * attribuibile a niente.
 *
 * ⚠️ Il flag va scritto DOPO `--`: `npm run scrivania -- --fixture`. Senza, npm
 * lo prende per configurazione propria e non lo inoltra — e il comando
 * misurerebbe la scrivania VIVA credendo di misurare la fixture, che e' il
 * guasto peggiore possibile. Per questo esiste anche `npm run scrivania:fixture`,
 * che lo scrive giusto e ha una cartella d'uscita sua. */
const FIXTURE = process.argv.includes("--fixture");
const FILO = join(RADICE, "docs", "acceptance", "SESSIONE-SCRIVANIA.jsonl");
const PROVENIENZA = join(RADICE, "docs", "acceptance", "SESSIONE-SCRIVANIA.json");

function chiediPercorso(campo) {
  return execFileSync("uv", ["run", "python", "-m", "core.paths_cli", campo], {
    cwd: RADICE, encoding: "utf-8",
  }).trim();
}

let socket;
let riproduttore = null;

if (FIXTURE) {
  /* Se il filo manca o non combacia, si esce PRIMA di aprire Electron. Non si
   * ripiega sul core vivo: produrrebbe una misura contaminata etichettata come
   * fixture, cioe' il peggiore degli esiti. */
  if (!existsSync(FILO) || !existsSync(PROVENIENZA)) {
    console.error("manca la registrazione. Col core acceso:  npm run registra");
    process.exit(2);
  }
  const attesa = JSON.parse(readFileSync(PROVENIENZA, "utf-8")).impronta;
  const vera = createHash("sha256").update(readFileSync(FILO)).digest("hex").slice(0, 16);
  if (vera !== attesa) {
    console.error(`la registrazione e' stata modificata: impronta ${vera}, ` +
      `il resoconto dice ${attesa}.\nRifalla:  npm run registra`);
    process.exit(2);
  }
  socket = chiediPercorso("--socket-riproduzione");
  /* `--velocita` esiste perche' il piano chiede di CONFRONTARE 1x e 10x, non di
   * sceglierne uno a priori: se i PNG coincidono il giro passa da ~80 s a ~15,
   * se non coincidono si resta a 1x e si scrive che cosa differiva. Senza
   * questo inoltro il confronto non e' eseguibile, e un confronto non
   * eseguibile e' un criterio non misurabile (§11.7 regola 4). */
  const iv = process.argv.indexOf("--velocita");
  const velocita = iv >= 0 ? process.argv[iv + 1] : null;
  riproduttore = spawn("uv",
    ["run", "python", resolve(RADICE, "scripts", "riproduttore.py"),
     "--da", FILO, "--socket", socket,
     ...(velocita ? ["--velocita", velocita] : [])],
    { cwd: RADICE, stdio: ["ignore", "pipe", "inherit"] });
  /* ⚠️ Si aspetta la RIGA su stdout, non l'esistenza del file: fra `bind()` e
   * `chmod 0600` c'e' una finestra, e collegarsi dentro quella finestra e'
   * esattamente cio' che la disciplina del socket esiste per impedire. */
  await new Promise((ok, no) => {
    const scadenza = setTimeout(() => no(new Error("il riproduttore non ha detto «pronto»")), 20000);
    let visto = "";
    riproduttore.stdout.on("data", (d) => {
      visto += d.toString();
      if (visto.includes("pronto ")) { clearTimeout(scadenza); ok(); }
    });
    riproduttore.on("exit", (c) => { clearTimeout(scadenza); no(new Error(`riproduttore uscito ${c}`)); });
  }).catch((e) => { console.error(e.message); process.exit(2); });
  console.log(`  fixture     ${attesa} · ${FILO.replace(RADICE + "/", "")}`);
} else {
  try {
    socket = chiediPercorso("--socket");
  } catch (e) {
    console.error("impossibile chiedere il percorso del socket al core:", e.message);
    process.exit(1);
  }
}

/* Un solo Electron per volta: la ragione, misurata, sta in scripts/blocco.mjs. */
const blocco = prendi(socket);
if (!blocco.preso) {
  console.error(spiega(blocco.chi));
  // Il riproduttore e' gia' partito: se ne va con noi, o resta a tenere il
  // socket e il prossimo giro trova un file orfano al posto di un server.
  if (riproduttore && !riproduttore.killed) riproduttore.kill("SIGTERM");
  process.exit(2);
}

const figlio = spawn(
  electron,
  [resolve(RADICE, "app", "main.js"), "--socket", socket, ...process.argv.slice(2)],
  { stdio: "inherit", cwd: RADICE },
);
/* ⚠️ Un figlio ucciso da un SEGNALE riporta `code === null`, e `?? 0` lo
   trasformava in successo: qualunque comando che finisse male usciva verde.
   Con un segnale l'esito e' 1, non 0. */
function chiudiTutto(codice) {
  blocco.lascia();
  if (riproduttore && !riproduttore.killed) riproduttore.kill("SIGTERM");
  process.exit(codice);
}
for (const seg of ["SIGINT", "SIGTERM"]) process.on(seg, () => chiudiTutto(1));
figlio.on("exit", (code, segnale) => chiudiTutto(code ?? (segnale ? 1 : 0)));
