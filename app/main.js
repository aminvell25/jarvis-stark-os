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
// §13: uno scatto per workspace. Il ciclo §11.7 su un componente per volta non
// puo' mostrare una scrivania — la densita', l'allineamento e l'accento caldo
// si giudicano sull'insieme, che e' l'unica cosa che l'utente vede davvero.
const SCRIVANIA = opzione("--scrivania");
// §13 criterio A e B: il dock e le scorciatoie, provati nella finestra vera.
const VERIFICA_SCRIVANIA = argv.includes("--verifica-scrivania");

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

/* ⚠️ I messaggi che arrivano PRIMA che il renderer sia in ascolto.
 *
 * `collega()` parte in `app.whenReady()`, cioe' prima che la pagina abbia
 * finito di caricarsi. Il core, appena un client si collega, manda una volta
 * sola cio' che non si ripete: `state.snapshot` e — da §13 — l'albero dei
 * sorgenti, i fusi, l'archivio, il contenuto della workspace. Quei messaggi
 * partivano verso un renderer che non aveva ancora nessun ascoltatore, e
 * `webContents.send` li perdeva in silenzio.
 *
 * Non si vedeva finche' l'app montava un pannello solo: `telemetry` arriva a
 * 2,5 Hz e si ripete. Con la scrivania si e' visto subito — la barra diceva
 * OFFLINE mentre i grafici scorrevano, e meta' dei pannelli restava allo stato
 * vuoto con il core acceso.
 *
 * Il ponte tiene l'ULTIMO messaggio per topic e lo riconsegna quando la
 * pagina ha finito di caricare. Non e' un buffer che cresce, non e' una
 * seconda fonte di verita': e' la stessa cosa che il core fa a chi si collega
 * e che `ui/src/bus.js` fa a chi si iscrive tardi, applicata al tratto in
 * mezzo. Vale anche per un ricaricamento della pagina.
 */
const ultimoPerTopic = new Map();
let rendererPronto = false;

function versoRenderer(canale, dato) {
  if (canale === "jarvis:message" && dato?.topic) ultimoPerTopic.set(dato.topic, dato);
  if (!finestra || finestra.isDestroyed()) return;
  if (canale === "jarvis:message" && !rendererPronto) return;
  finestra.webContents.send(canale, dato);
}

function riconsegna() {
  rendererPronto = true;
  for (const msg of ultimoPerTopic.values()) {
    finestra.webContents.send("jarvis:message", msg);
  }
  finestra.webContents.send("jarvis:status", { stato, dettaglio: SOCKET });
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

  // Ogni caricamento, non solo il primo: dopo un ricaricamento il renderer e'
  // di nuovo senza stato, e il core non ha nessun motivo di rimandarglielo.
  finestra.webContents.on("did-finish-load", () => {
    rendererPronto = false;
    riconsegna();
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


/* ── §13: uno scatto per workspace, per il ciclo §11.7 ───────────────────── */

async function scattaScrivania(cartella) {
  const fs = require("node:fs");
  fs.mkdirSync(cartella, { recursive: true });
  await attendiPronto();

  for (let n = 1; n <= 4; n++) {
    await finestra.webContents.executeJavaScript(
      `window.__scrivania.scrivania.vai(${n})`
    );
    // Il workspace si COMPONE alla prima visita: three.js costruisce il globo,
    // PixiJS l'atlante dei glifi, e le etichette si misurano solo dopo
    // `document.fonts.ready`. Uno scatto immediato fotograferebbe una scrivania
    // a meta' e il ciclo §11.7 giudicherebbe una cosa che non esiste.
    await finestra.webContents.executeJavaScript(
      "document.fonts.ready.then(() => new Promise(r => setTimeout(r, 1200)))"
    );
    // Il numero del workspace si CHIEDE alla scrivania prima di scattare: un
    // `vai()` che non avesse ancora finito darebbe uno scatto col nome
    // sbagliato, e un nome sbagliato in `shots/` è peggio di nessuno scatto.
    const vero = await finestra.webContents.executeJavaScript(
      "window.__scrivania.scrivania.stato().workspace");
    const nome = require("node:path").join(cartella, `ws-0${vero}.png`);
    fs.writeFileSync(nome, (await finestra.webContents.capturePage()).toPNG());
    console.log(`scatto ${nome} (chiesto ${n}, a schermo ${vero})`);
  }
  app.exit(0);
}

/* ── §13 criteri A e B: il dock e le scorciatoie nella finestra vera ─────── */

async function verificaScrivaniaEEsci() {
  await attendiPronto();

  const esito = await finestra.webContents.executeJavaScript(`(async () => {
    const { scrivania, scorciatoie, nonRealizzate } = window.__scrivania;
    // Mezzo secondo, non un decimo: premere la voce di un altro workspace lo
    // COMPONE, e comporre WS02 vuol dire costruire una scena three.js e una
    // pila CSS 3D. Con un'attesa corta il secondo clic arriva mentre il primo
    // sta ancora aprendo, e il criterio boccia la latenza invece della logica.
    const passo = () => new Promise((r) => setTimeout(r, 700));
    const tasti = () => [...document.querySelectorAll(".dck__moduli .dck__tasto")];
    const premuti = () => tasti().filter((b) => b.getAttribute("aria-pressed") === "true")
                                 .map((b) => b.textContent);

    /* A — le otto voci del dock aprono e chiudono il PROPRIO modulo.
     *
     * Si guarda il modulo, non il CONTEGGIO dei pannelli aperti: premere la
     * voce di un altro workspace ci porta dentro, e portarci dentro lo
     * COMPONE — tre pannelli in piu' invece di uno. Non e' un difetto, e'
     * cio' che un dock deve fare; era il criterio a guardare la cosa
     * sbagliata, e il primo giro l'ha mostrato.
     */
    const dock = [];
    for (const b of tasti()) {
      const premuto = () => b.getAttribute("aria-pressed") === "true";
      const prima = premuto();
      b.click(); await passo();
      const dopo1 = premuto();
      b.click(); await passo();
      const dopo2 = premuto();
      // La proprieta e questa, in tutte e due le direzioni: una pressione
      // COMMUTA il modulo, due riportano dove si era. Il primo giro guardava
      // il conteggio dei pannelli aperti e sbagliava per due motivi: premere
      // la voce di un altro workspace ci porta dentro e lo COMPONE (tre
      // pannelli, non uno), e le voci gia aperte partono dallo stato opposto.
      dock.push({ voce: b.textContent, prima, commuta: dopo1 !== prima,
                  torna: dopo2 === prima });
    }

    // B — le scorciatoie. Si spara un vero KeyboardEvent sul documento: e' la
    // stessa strada che fanno i tasti veri, non una chiamata alla funzione.
    const tasto = async (code) => {
      document.dispatchEvent(new KeyboardEvent("keydown", { code, altKey: true, bubbles: true }));
      await passo();
    };
    const perTasto = [];
    for (const n of [2, 3, 4, 1]) {
      await tasto("Digit" + n);
      perTasto.push({ tasti: "Alt+" + n, workspace: scrivania.stato().workspace });
    }
    const visibili = () => [...document.querySelectorAll(".winbox")]
      .filter((w) => getComputedStyle(w).display !== "none").length;
    const primaH = visibili();
    await tasto("KeyH");
    const dopoH = visibili();
    await tasto("KeyH");
    const tornatoH = visibili();

    const geo = () => [...document.querySelectorAll(".winbox")]
      .filter((w) => getComputedStyle(w).display !== "none")
      .map((w) => w.getBoundingClientRect())
      .map((r) => [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]);
    /* Si sposta con box.move(), non con style.left: WinBox tiene in cache
     * l'ultimo valore che ha scritto e salta le scritture uguali, quindi una
     * posizione cambiata alle sue spalle non tornerebbe mai indietro — e
     * fallirebbe il criterio per un motivo che nell'uso vero non esiste. Il
     * trascinamento di cornice.js passa da box.move(), come qui. */
    const box = document.querySelector(".winbox")?.winbox;
    const primaT = JSON.stringify(geo());
    if (box) box.move(40, 60);
    await passo();
    const spostata = JSON.stringify(geo()) !== primaT;
    await tasto("KeyT");
    const dopoT = JSON.stringify(geo());

    // C — i tre controlli del pannello sono premibili, non testo.
    const controlli = [...document.querySelectorAll(".winbox [data-ctrl]")]
      .map((b) => b.tagName + ":" + b.dataset.ctrl);

    // I pannelli a schermo e cosa dicono: dati veri o stato vuoto, mai un
    // segnaposto (invariante 23). E se DEBORDANO: un pannello che esce dalla
    // propria cornice si vede prima di ogni altra cosa, e a occhio, su
    // quattro workspace e quattordici pannelli, uno sfugge sempre.
    const pannelli = [...document.querySelectorAll(".winbox .wb-body > div > *")]
      .map((p) => {
        const corpo = p.closest(".wb-body");
        return {
          classe: p.className.split(" ")[0],
          stato: p.dataset.stato ?? "—",
          debordaX: corpo.scrollWidth - corpo.clientWidth,
          debordaY: corpo.scrollHeight - corpo.clientHeight,
        };
      });

    return {
      dock,
      scorciatoie: scorciatoie.map((s) => s.tasti),
      nonRealizzate: nonRealizzate.map((s) => s.tasti),
      workspacePerTasto: perTasto,
      nascondi: { prima: primaH, dopo: dopoH, tornato: tornatoH },
      affianca: { spostata, ripristinata: primaT === dopoT },
      controlli,
      pannelli,
      preload: Object.keys(window.jarvis ?? {}).sort(),
    };
  })()`);

  /* E — il budget di §10.4 sull'insieme, non su un componente alla volta.
   *
   * `npm run bench` misura la cella di galleria che accende globo, glifi e
   * anelli insieme. Qui si misura la SCRIVANIA: quattro workspace, ognuno con
   * i propri motori, nella finestra vera e con la GPU vera.
   *
   * Si guardano gli intervalli fra fotogrammi. Con render-on-demand e
   * l'invariante 25 — zero animazione ambientale — una scrivania ferma non
   * deve costare niente: la mediana sta sul vsync e il MASSIMO dice se
   * qualcosa, ogni tanto, fa perdere un fotogramma.
   */
  const budget = [];
  for (let n = 1; n <= 4; n++) {
    await finestra.webContents.executeJavaScript(
      "window.__scrivania.scrivania.vai(" + n + ")");
    await new Promise((r) => setTimeout(r, 1500));
    budget.push(await finestra.webContents.executeJavaScript(`
      new Promise((risolvi) => {
        const dt = []; let prima = performance.now();
        const passo = () => {
          const ora = performance.now(); dt.push(ora - prima); prima = ora;
          if (dt.length < 180) requestAnimationFrame(passo);
          else {
            dt.sort((a, b) => a - b);
            risolvi({ ws: ${n}, frame: dt.length,
                      mediana: +dt[90].toFixed(2),
                      p95: +dt[170].toFixed(2),
                      max: +dt[dt.length - 1].toFixed(2) });
          }
        };
        requestAnimationFrame(passo);
      })`));
  }
  esito.budget = budget;

  console.log(JSON.stringify(esito, null, 1));

  const dockOk = esito.dock.length === 8 &&
    esito.dock.every((d) => d.commuta && d.torna);
  const wsOk = esito.workspacePerTasto.every((w, i) => w.workspace === [2, 3, 4, 1][i]);
  const hOk = esito.nascondi.dopo === 0 && esito.nascondi.tornato === esito.nascondi.prima;
  const ctrlOk = esito.controlli.length >= 3 &&
    esito.controlli.every((c) => c.startsWith("BUTTON:"));
  const tOk = esito.affianca.spostata && esito.affianca.ripristinata;
  app.exit(dockOk && wsOk && hOk && ctrlOk && tOk ? 0 : 1);
}

async function attendiPronto() {
  const scadenza = Date.now() + 30000;
  while (Date.now() < scadenza) {
    if (await finestra.webContents.executeJavaScript("window.__jarvisPronto === true")) return;
    await new Promise((r) => setTimeout(r, 200));
  }
}

app.whenReady().then(() => {
  creaFinestra();
  collega();
  if (SCREENSHOT) finestra.webContents.once("did-finish-load", () => scattaEEsci(SCREENSHOT));
  if (BENCH) finestra.webContents.once("did-finish-load", () => misuraEEsci());
  if (VERIFICA) finestra.webContents.once("did-finish-load", () => verificaEEsci());
  if (SCRIVANIA) finestra.webContents.once("did-finish-load", () => scattaScrivania(SCRIVANIA));
  if (VERIFICA_SCRIVANIA)
    finestra.webContents.once("did-finish-load", () => verificaScrivaniaEEsci());
});

app.on("window-all-closed", () => app.quit());
