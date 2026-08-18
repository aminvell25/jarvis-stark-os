/* Processo main di Electron — SPEC §3.2 e §18.2.
 *
 * Fa due cose e nient'altro: apre la finestra e fa da ponte verso il core.
 *
 * PERCHE' IL PONTE ESISTE. Il canale col core e' un socket UNIX (§18.2), e
 * **l'API WebSocket del browser non puo' aprirlo**: verificato su Chromium,
 * `new WebSocket('ws+unix://...')` alza `DOMException: The URL's scheme must
 * be either 'ws' or 'wss'`. Solo Node puo', tramite `ws`. Quindi il renderer
 * non parla mai direttamente col core: riceve da qui, via contextBridge.
 *
 * Non e' un dettaglio di comodo. In Fase 2 la conferma umana dei tool
 * `side_effect=True` (§6.2) passera' da questo confine, e il fatto che il
 * renderer — che in Fase 6 ospitera' `<webview>` con contenuto non fidato —
 * non abbia alcuna presa diretta sul socket e' meta' della difesa.
 */

const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("node:path");
const WebSocket = require("ws");

const argv = process.argv.slice(1);
function opzione(nome) {
  const i = argv.indexOf(nome);
  return i >= 0 ? argv[i + 1] : null;
}

const SOCKET = opzione("--socket");
const SCREENSHOT = opzione("--screenshot");

if (!SOCKET) {
  console.error(
    "manca --socket. Il percorso lo conosce il core:\n" +
      "  uv run python -m core.paths_cli --socket\n" +
      "Usa `npm run app`, che lo chiede e lo passa."
  );
  app.exit(2);
}

/* ── stato del collegamento ───────────────────────────────────────────────── */

const STATI = { CONNESSO: "connesso", DISCONNESSO: "disconnesso", ATTESA: "in-riconnessione" };
let stato = STATI.DISCONNESSO;
let finestra = null;
let socket = null;
let tentativi = 0;
let timerRiconnessione = null;

function versoRenderer(canale, dato) {
  if (finestra && !finestra.isDestroyed()) finestra.webContents.send(canale, dato);
}

function cambiaStato(nuovo, dettaglio = "") {
  if (stato === nuovo) return;
  stato = nuovo;
  // Il renderer non deve MAI dedurre lo stato dall'assenza di messaggi: senza
  // questo, un core fermo e un core lento sono indistinguibili, e il pannello
  // mostrerebbe l'ultimo valore come se fosse attuale (§11.9).
  versoRenderer("jarvis:status", { stato, dettaglio });
}

/* Backoff: il core puo' non essere ancora avviato, o essere riavviato sotto.
 * Cresce fino a 5 s per non martellare il filesystem con connect() falliti. */
function ritardo() {
  return Math.min(250 * 2 ** Math.min(tentativi, 5), 5000);
}

function collega() {
  clearTimeout(timerRiconnessione);
  socket = new WebSocket(`ws+unix://${SOCKET}:/`);

  socket.on("open", () => {
    tentativi = 0;
    cambiaStato(STATI.CONNESSO, SOCKET);
  });

  socket.on("message", (grezzo) => {
    let msg;
    try {
      msg = JSON.parse(grezzo.toString());
    } catch {
      return; // un messaggio illeggibile si scarta, non fa cadere il ponte
    }
    versoRenderer("jarvis:message", msg);
  });

  socket.on("close", riprova);
  socket.on("error", (e) => riprova(e.message));
}

function riprova(dettaglio = "") {
  if (socket) {
    socket.removeAllListeners();
    socket = null;
  }
  cambiaStato(STATI.ATTESA, String(dettaglio));
  tentativi++;
  timerRiconnessione = setTimeout(collega, ritardo());
}

/* ── finestra ─────────────────────────────────────────────────────────────── */

function creaFinestra() {
  finestra = new BrowserWindow({
    show: false,
    backgroundColor: "#070b0d", // --bg-void: niente lampo bianco all'apertura
    webPreferences: {
      contextIsolation: true, // obbligatorio, §6.3
      nodeIntegration: false, // obbligatorio, §6.3
      sandbox: true, // §6.3 e invariante 6
      webviewTag: false, // Fase 6: non si allarga la superficie prima del bisogno
      preload: path.join(__dirname, "preload.js"),
    },
  });

  finestra.removeMenu();
  finestra.loadFile(path.join(__dirname, "..", "ui", "index.html"));
  finestra.once("ready-to-show", () => {
    finestra.maximize();
    finestra.show();
  });

  // Il renderer chiede lo stato all'avvio: puo' essersi collegato dopo il
  // primo `cambiaStato`, e non deve restare senza saperlo.
  ipcMain.handle("jarvis:status", () => ({ stato, socket: SOCKET }));
}

/* ── modalita' screenshot, per il ciclo di verifica §11.7 ─────────────────── */

async function scattaEEsci(destinazione) {
  // Attesa di dati veri, non un timer a caso: il pannello deve avere qualcosa
  // da mostrare, altrimenti si fotograferebbe lo stato vuoto credendolo il
  // pannello.
  const scadenza = Date.now() + 15000;
  while (Date.now() < scadenza) {
    const pronto = await finestra.webContents.executeJavaScript(
      "window.__jarvisPronto === true"
    );
    if (pronto) break;
    await new Promise((r) => setTimeout(r, 200));
  }
  const immagine = await finestra.webContents.capturePage();
  require("node:fs").writeFileSync(destinazione, immagine.toPNG());
  console.log(`scatto ${destinazione}`);
  app.exit(0);
}

app.whenReady().then(() => {
  creaFinestra();
  collega();
  if (SCREENSHOT) finestra.webContents.once("did-finish-load", () => scattaEEsci(SCREENSHOT));
});

app.on("window-all-closed", () => app.quit());
