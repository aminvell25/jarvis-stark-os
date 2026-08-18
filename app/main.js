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
// Misura del budget di frame §10.4 nella finestra VERA, con la GPU vera.
// Il numero headless di Playwright e' quello di SwiftShader e non vale.
const BENCH = argv.includes("--bench");
// Verifica dei criteri B e C di §22 nella finestra VERA: la webview viva, il
// testo selezionabile, e l'assenza di ogni via verso il filesystem.
const VERIFICA = argv.includes("--verifica");

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
    /* ARGUS (§12): la cattura la fa il PROCESSO PRINCIPALE, non il renderer.
     * Il renderer non deve poter fotografare se stesso su richiesta di
     * nessuno — dalla Fase 6 ospita contenuto non fidato — e il preload resta
     * a quattro funzioni proprio perche' questa strada non ci passa.
     *
     * `capturePage()` vede SOLO questa finestra: e' `scope = "app"` di §12,
     * imposto da cio' che l'API puo' fare, non da una regola da rispettare. */
    if (msg?.topic === "argus.capture_request") {
      catturaEInvia(msg.id);
      return;
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
      // Fase 6: il bisogno e' arrivato. `<webview>` e non `WebContentsView`
      // perche' quest'ultima e' una vista NATIVA sovrapposta alla finestra,
      // non un elemento del DOM: non puo' stare dentro un piano ruotato da
      // una `transform: rotateY()`, e il criterio di §22 chiede una webview
      // viva dentro la board 3D.
      webviewTag: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  /* ── La difesa vera non e' l'attributo del tag ──────────────────────────
   *
   * `webviewTag: true` dice soltanto che l'elemento esiste. Sono i suoi
   * ATTRIBUTI a decidere quanto e' pericoloso, e quelli li scrive il
   * renderer — che dalla Fase 6 ospita contenuto non fidato.
   *
   * Qui ogni allegamento viene intercettato e ripulito PRIMA che la webview
   * nasca: un renderer compromesso che scrivesse `<webview nodeintegration
   * preload="...">` otterrebbe una webview normale. E' la stessa forma
   * dell'allowlist del core: non si vieta cio' che si conosce, si concede
   * solo cio' che si e' deciso. */
  finestra.webContents.on("will-attach-webview", (_evento, prefs, params) => {
    delete prefs.preload;
    prefs.nodeIntegration = false;
    prefs.nodeIntegrationInSubFrames = false;
    prefs.contextIsolation = true;
    prefs.sandbox = true;
    prefs.webSecurity = true;
    prefs.allowRunningInsecureContent = false;
    // Sessione isolata, sempre: i cookie del web non stanno nella sessione
    // dell'app (§6.3).
    params.partition = "persist:jarvis";
    params.allowpopups = false;
  });

  /* Nessuna finestra nuova, da nessuno: ne' dal renderer ne' da una pagina
   * dentro una webview. Un `target=_blank` diventa niente. */
  finestra.webContents.setWindowOpenHandler(() => ({ action: "deny" }));

  /* E il renderer non naviga via da se stesso. Senza questo, un difetto nel
   * renderer potrebbe sostituire l'intera interfaccia con una pagina remota,
   * che erediterebbe il preload. */
  finestra.webContents.on("will-navigate", (evento, url) => {
    if (!url.startsWith("file://")) evento.preventDefault();
  });

  finestra.removeMenu();
  const galleria = BENCH || VERIFICA;
  finestra.loadFile(
    path.join(__dirname, "..", "ui", galleria ? "gallery.html" : "index.html"),
    BENCH ? { search: "component=budget" } : VERIFICA ? { search: "component=board" } : undefined
  );
  finestra.once("ready-to-show", () => {
    finestra.maximize();
    finestra.show();
  });

  // Il renderer chiede lo stato all'avvio: puo' essersi collegato dopo il
  // primo `cambiaStato`, e non deve restare senza saperlo.
  ipcMain.handle("jarvis:status", () => ({ stato, socket: SOCKET }));

  /* L'unico messaggio che risale verso il core (§6.2). Il ponte non lo
   * interpreta e non lo arricchisce: lo inoltra cosi' com'e', e il core lo
   * valida con pydantic e lo scarta se non e' esattamente cio' che attende.
   * Un ponte che "aggiusta" i messaggi diventa un secondo posto in cui la
   * regola vive, e i due divergono. */
  ipcMain.on("jarvis:confirm", (_evento, dato) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({
      topic: "fs.confirm_response",
      id: String(dato?.id ?? ""),
      approvato: !!dato?.approvato,
    }));
  });
}

/* ── verifica dei criteri di §22 nella finestra vera ──────────────────────── */

async function verificaEEsci() {
  const w = finestra.webContents;
  await new Promise((r) => setTimeout(r, 2500));   // la board monta e la webview carica

  const esito = await w.executeJavaScript(`(() => {
    const b = window.__board;
    const wv = b?.webview ?? null;

    // Criterio B/1: la webview e' VIVA — esiste, ha un id di webContents, e
    // ha finito di caricare qualcosa.
    const viva = !!wv && typeof wv.getWebContentsId === "function" &&
                 (() => { try { return wv.getWebContentsId() > 0; } catch { return false; } })();

    // Criterio B/2: il testo di una carta si SELEZIONA. Non "e' nel DOM":
    // si seleziona davvero, che e' cio' che rasterizzarlo in WebGL toglie.
    const corpo = document.querySelector(".brd__corpo");
    const r = document.createRange();
    r.selectNodeContents(corpo);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(r);
    const selezionato = String(sel).trim();

    // Criterio C: nessuna via verso il filesystem dal renderer.
    const chiavi = Object.keys(window.jarvis ?? {});
    return {
      webviewViva: viva,
      webviewSrc: wv ? wv.getAttribute("src") : null,
      caratteriSelezionati: selezionato.length,
      campione: selezionato.slice(0, 60),
      require: typeof window.require,
      process: typeof window.process,
      module: typeof window.module,
      preload: chiavi.sort(),
    };
  })()`);

  console.log(JSON.stringify(esito, null, 1));
  app.exit(esito.webviewViva && esito.caratteriSelezionati > 20 &&
           esito.require === "undefined" && esito.process === "undefined" ? 0 : 1);
}

/* ── ARGUS: la cattura della finestra ─────────────────────────────────────── */

async function catturaEInvia(id) {
  if (!finestra || finestra.isDestroyed()) return;
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  try {
    const immagine = await finestra.webContents.capturePage();
    const dimensione = immagine.getSize();
    socket.send(JSON.stringify({
      topic: "argus.capture_response",
      id: String(id ?? ""),
      png: immagine.toPNG().toString("base64"),
      larghezza: dimensione.width,
      altezza: dimensione.height,
    }));
  } catch (e) {
    // Una cattura fallita non deve far cadere il ponte: il core scade da solo.
    console.error("cattura fallita:", e.message);
  }
}

/* ── modalita' banco, per il criterio di §22 sul budget di §10.4 ─────────── */

async function misuraEEsci() {
  const scadenza = Date.now() + 180_000;
  while (Date.now() < scadenza) {
    const esito = await finestra.webContents.executeJavaScript(
      "window.__budget ?? null"
    );
    if (esito) {
      console.log(JSON.stringify(esito, null, 1));
      app.exit(0);
      return;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  console.error("il banco non ha prodotto una misura entro il tempo massimo");
  app.exit(1);
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
  if (BENCH) finestra.webContents.once("did-finish-load", () => misuraEEsci());
  if (VERIFICA) finestra.webContents.once("did-finish-load", () => verificaEEsci());
});

app.on("window-all-closed", () => app.quit());
