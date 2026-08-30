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

const crypto = require("node:crypto");
/* Uno solo, di modulo. Erano tre `const fs` locali piu' due `require` in
   linea, e un aiutante di modulo non ne vedeva nessuno: `impronta` falliva con
   `ReferenceError`, e il `catch` che c'era prima lo restituiva come `null` —
   cioe' come «nessuna provenienza», che e' proprio cio' che §11.7 regola 5
   vieta di lasciar passare. */
const fs = require("node:fs");
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
// Il giro §11.7 del nucleo: gli stati attivi non si vedono nello scatto normale.
const NUCLEO = opzione("--nucleo");
// §25.13.5 in tutti gli stati di §25.6, non solo a riposo — turno 4.
const MARCHIO_STATI = opzione("--marchio-stati");
// Un pannello solo, ingrandito, coi dati veri: il caso in mezzo fra la
// galleria (un componente, dati finti) e la scrivania (tutto insieme).
const PANNELLO = opzione("--pannello");
// §13 criterio A e B: il dock e le scorciatoie, provati nella finestra vera.
const VERIFICA_SCRIVANIA = argv.includes("--verifica-scrivania");
/* Il modo di MISURA — §11.9, seconda eccezione. Il socket lo sceglie
 * `scripts/app.mjs`: qui si sa soltanto che la sorgente e' una registrazione, e
 * si cambiano di conseguenza l'attesa e le leve di congelamento. */
const FIXTURE = argv.includes("--fixture");
/* ⚠️ LA RISOLUZIONE, e finora ce n'era UNA sola.
 *
 * `DIVARIO-PREMIUM.md` §10 e' aperto da prima di ogni altro documento del
 * progetto, con l'etichetta «impatto ALTO, costo NULLO»: ogni misura di
 * densita', ogni ciclo §11.7, ogni criterio di §26.9 e' stato verificato a
 * 1536x843 e a nient'altro. Le celle sono frazioni, ma le `min-width` dei
 * moduli sono PIXEL: a 1280 la colonna vale 106 px e `telemetria` ne dichiara
 * 550, ed e' R99 — una cella troppo stretta non stringe il pannello, lo fa
 * DEBORDARE.
 *
 * `--dimensione LxA` mette la finestra a una misura esatta invece di
 * massimizzarla. Vale la stessa ragione per cui `maximize()` sta PRIMA del
 * caricamento: il renderer misura l'area utile una volta, e se la misura
 * dopo, la compone sulla dimensione sbagliata. */
const DIMENSIONE = (() => {
  const v = opzione("--dimensione");
  if (!v) return null;
  const m = /^(\d{3,5})x(\d{3,5})$/.exec(v.trim());
  if (!m) {
    console.error(`--dimensione vuole LxA, per esempio 1280x800 — ricevuto "${v}"`);
    process.exit(2);
  }
  return [Number(m[1]), Number(m[2])];
})();

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
//: Quando e' arrivato l'ultimo messaggio dal socket. Serve al modo fixture per
//: sapere che la registrazione e' finita.
let ultimoMessaggioMs = 0;
let rendererPronto = false;

function versoRenderer(canale, dato) {
  if (canale === "jarvis:message") ultimoMessaggioMs = Date.now();
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
  /* ⚠️ **Il costruttore puo' sollevare, e la catena moriva li'.**
   *
   * `riprova()` programma `collega()` con un timer. Se il socket non esiste
   * nell'istante del tentativo — cioe' ESATTAMENTE la finestra in cui il core
   * si sta riavviando — `new WebSocket` solleva in modo sincrono,
   * l'eccezione esce dal callback del timer, e **nessuno programma il
   * tentativo successivo**: la scrivania resta scollegata per sempre, con la
   * finestra viva e vuota.
   *
   * Misurato il 26 agosto: il core riavviato alle 22:35, e alle 22:47 la
   * scrivania non si era ancora ricollegata — zero `client_connesso` nel
   * journal per dodici minuti, mentre il diario si riempiva su disco. Il
   * pannello mostrava il vuoto e il registro era pieno: due strade per lo
   * stesso dato, e una delle due interrotta in silenzio. */
  try {
    socket = new WebSocket(`ws+unix://${SOCKET}:/`);
  } catch (e) {
    riprova(`connessione non aperta: ${e.message}`);
    return;
  }

  socket.on("open", () => {
    tentativi = 0;
    cambiaStato(STATI.CONNESSO, SOCKET);
    /* Il microfono del core si apre SOLO quando l'app c'e'. Il core gira
     * sotto systemd ventiquattro ore, l'app no: senza questa riga JARVIS
     * ascolta e risponde a finestra chiusa.
     *
     * Si manda a ogni `open`, riconnessioni comprese: il core dimentica il
     * ruolo quando la connessione cade, e una scrivania che si ricollega
     * senza ridichiararsi resterebbe muta.
     *
     * La finestra NASCOSTA resta collegata, quindi resta in ascolto: e' cio'
     * che serve a un assistente a cui si parla senza guardarlo. */
    socket.send(JSON.stringify({ topic: "client.ruolo", ruolo: "scrivania" }));
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
    /* La dimensione va DICHIARATA nel costruttore, non imposta dopo: con
       `setContentSize()` su una finestra gia' nata, `isMaximized()` continuava
       a rispondere `true` e la finestra restava a 1536x843 in tutti e tre i
       giri. Misurato, non dedotto: `occlusione.json` riportava `finestra
       [1536, 843]` con `--dimensione 1280x800`. */
    ...(DIMENSIONE ? { width: DIMENSIONE[0], height: DIMENSIONE[1] } : {}),
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

  /* ⚠️ SI MASSIMIZZA PRIMA DI CARICARE, e non e' un dettaglio di avvio.
   *
   * Prima `maximize()` stava dentro `ready-to-show`, cioe' DOPO che il
   * renderer aveva gia' composto la scrivania. Il renderer misura l'area
   * utile con `misuraArea()` e ci posa sopra la scena: la misurava su una
   * BrowserWindow ancora alla sua dimensione predefinita, 800x600, che tolti
   * barra e dock fa **800x503**. Poi la finestra si massimizzava e i pannelli
   * restavano dov'erano — tutti nella meta' sinistra di uno schermo largo il
   * doppio.
   *
   * Non e' dedotto: e' il numero scritto in `layout.json`, «area_larghezza:
   * 800, area_altezza: 503», su una finestra che nello scatto e' 1536 di
   * larghezza. La persistenza poi RIPRODUCEVA fedelmente quella composizione
   * sbagliata a ogni avvio, ed e' il motivo per cui il quarto destro della
   * scrivania risultava vuoto al 1 % di inchiostro.
   *
   * Massimizzata prima, la prima misura del renderer e' gia' quella vera.
   * `show: false` regge: una finestra nascosta si massimizza lo stesso. */
  if (DIMENSIONE) {
    /* `setContentSize` e non `setSize`: la seconda comprende la decorazione
       della finestra, che su Linux dipende dal window manager. Cio' che si
       misura e' il contenuto. E `unmaximize()` prima, perche' su questo window
       manager una finestra nasce massimizzata se lo era l'ultima. */
    finestra.unmaximize();
    finestra.setContentSize(DIMENSIONE[0], DIMENSIONE[1]);
  } else {
    finestra.maximize();
  }

  const galleria = BENCH || VERIFICA;
  finestra.loadFile(
    path.join(__dirname, "..", "ui", galleria ? "gallery.html" : "index.html"),
    BENCH ? { search: "component=budget" } : VERIFICA ? { search: "component=board" } : undefined
  );
  finestra.once("ready-to-show", () => {
    finestra.show();
    /* ⚠️ E si RIMETTE dopo lo show, perche' il window manager ha l'ultima
       parola. Misurato: con la dimensione dichiarata nel costruttore E
       `setContentSize()` prima del caricamento, `occlusione.json` riportava
       ancora `finestra [1536, 843]` e `massimizzata: true`. Chi massimizza non
       e' Electron: e' il gestore di finestre, e lo fa quando la finestra
       compare. L'unico posto in cui l'ultima parola torna a noi e' dopo. */
    assicuraDimensione();
  });

  /* ⚠️ **Gli errori del renderer non li leggeva nessuno.**
   *
   * Un pannello che non si apriva spariva in silenzio: il core scriveva
   * `t0_ui` e considerava il lavoro fatto, il ponte non guardava, e la
   * console del renderer vive dentro una finestra che nessuno apre. Per
   * diagnosticare «non mi apre il pannello telemetria» non c'era una sola
   * riga da leggere in nessun posto.
   *
   * Solo avvisi ed errori: inoltrare anche il resto renderebbe il registro
   * dell'app illeggibile, e un registro illeggibile e' un registro che non si
   * legge. La firma di `console-message` e' cambiata fra le versioni di
   * Electron — prima posizionale, poi un oggetto — e si accettano entrambe. */
  /* ⚠️ **Un renderer che muore non lasciava una riga.** L'app si e' chiusa
   * tre volte in una sera senza scrivere niente: `console-message` non copre
   * il caso in cui il processo che scriveva e' proprio quello morto. */
  finestra.webContents.on("render-process-gone", (_e, d) => {
    console.error(`[renderer] processo morto: ${d?.reason} (exitCode ${d?.exitCode})`);
  });
  finestra.on("unresponsive", () => console.error("[renderer] non risponde"));
  finestra.on("closed", () => console.error("[finestra] chiusa"));

  finestra.webContents.on("console-message", (...a) => {
    const d = (a[0] && typeof a[0] === "object" && "level" in a[0]) ? a[0] : null;
    const livello = d ? d.level : a[1];
    const testo = d ? d.message : a[2];
    const riga = d ? d.lineNumber : a[3];
    const dove = d ? d.sourceId : a[4];
    const grave = livello === "error" || livello === "warning" || Number(livello) >= 2;
    if (grave) console.error(`[renderer] ${testo}  (${dove}:${riga})`);
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

  /* §26.7 — una modifica alle impostazioni verso il core.
   *
   * ⚠️ Il `topic` lo mette il ponte, come per gli altri due: chi sta
   * dall'altra parte puo' scegliere QUALE impostazione cambiare, non a chi
   * parlare. E il valore si ricostruisce per tipo — questo e' l'ultimo posto
   * nostro prima del filo, e il preload gira dalla parte sbagliata del
   * confine. */
  ipcMain.on("jarvis:impostazione", (_evento, dato) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    const v = dato?.valore;
    socket.send(JSON.stringify({
      topic: "ui.imposta",
      chiave: String(dato?.chiave ?? ""),
      valore: typeof v === "boolean" || typeof v === "number" ? v : String(v ?? ""),
    }));
  });

  /* §26.10 punto 1 — la disposizione dell'ambiente verso il core.
   *
   * ⚠️ **Il `topic` lo mette il ponte, non il renderer.** E' la riga che
   * impedisce a questo canale di diventare un «manda questo al core»
   * generico: chi sta dall'altra parte puo' scegliere DOVE stanno le sue
   * finestre, non A CHI parla. Stessa forma di `jarvis:confirm` qui sopra.
   *
   * I campi si ricostruiscono per nome, come nel preload. Non e' ridondanza
   * inutile: il preload gira nel processo del renderer e in un'ipotesi di
   * compromissione e' dalla parte sbagliata del confine. Questo e' l'ultimo
   * posto nostro prima del filo. */
  ipcMain.on("jarvis:layout", (_evento, dato) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    const pannelli = Array.isArray(dato?.pannelli) ? dato.pannelli : [];
    socket.send(JSON.stringify({
      topic: "ui.layout",
      area_larghezza: Number(dato?.area?.larghezza) | 0,
      area_altezza: Number(dato?.area?.altezza) | 0,
      // Dove COMINCIA il pavimento: senza, il core taglia contro una banda
      // traslata di quanto e' alta la barra. Vedi core/layout.py::adatta.
      area_sinistra: Number(dato?.area?.sinistra) | 0,
      area_alto: Number(dato?.area?.alto) | 0,
      pannelli: pannelli.map((p) => ({
        id: String(p?.id ?? ""),
        x: Number(p?.x) | 0,
        y: Number(p?.y) | 0,
        larghezza: Number(p?.larghezza) | 0,
        altezza: Number(p?.altezza) | 0,
        z: Number(p?.z) | 0,
        massimizzato: !!p?.massimizzato,
        // ⚠️ **La TERZA copia campo-per-campo dello stesso elenco**, e qui
        // `nascosto` cadeva. `ui/src/desk/scrivania.js` lo produce,
        // `app/preload.js` lo ricopia, e questo lo ricopiava ancora — tre
        // punti da tenere allineati a mano per un campo solo.
        //
        // Misurato il 30 agosto attraversando il confine: il renderer mandava
        // `nascosto: true` su tutti e sei i pannelli, il core ne riceveva sei
        // `false`, e la composizione di ADR-013 veniva rifiutata «per mancanza
        // di spazio» contro pannelli che non si vedevano. Nessun test lo
        // vedeva: ognuna delle tre copie era corretta da sola.
        nascosto: !!p?.nascosto,
      })),
      icone: (Array.isArray(dato?.icone) ? dato.icone : []).map((i) => ({
        tipo: i?.tipo === "file" ? "file" : "modulo",
        nome: String(i?.nome ?? ""),
        x: Number(i?.x) | 0,
        y: Number(i?.y) | 0,
        dentro: i?.dentro == null ? null : String(i.dentro),
      })),
      cartelle: (Array.isArray(dato?.cartelle) ? dato.cartelle : []).map((c) => ({
        id: String(c?.id ?? ""),
        x: Number(c?.x) | 0,
        y: Number(c?.y) | 0,
        etichetta: String(c?.etichetta ?? ""),
        aperta: !!c?.aperta,
      })),
      scena: dato?.scena == null ? null : String(dato.scena),
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
  fs.writeFileSync(destinazione, immagine.toPNG());
  console.log(`scatto ${destinazione}`);
  app.exit(0);
}


/* La dimensione va RIMESSA, e piu' di una volta.
 *
 * Su questo gestore di finestre una finestra torna massimizzata da sola: con la
 * misura dichiarata nel costruttore, imposta prima del caricamento E rimessa a
 * `ready-to-show`, `occlusione.json` riportava ancora `finestra [1536, 843]` e
 * `massimizzata: true` — mentre a `ready-to-show` `getContentSize()` diceva
 * 1280x800. Fra lo show e la misura qualcuno la riapre.
 *
 * `setMaximizable(false)` toglie al gestore la leva, e la chiamata si ripete
 * subito prima di misurare. Ritorna cio' che ha OTTENUTO, non cio' che ha
 * chiesto: se le due non coincidono la misura va letta sapendolo. */
function assicuraDimensione() {
  if (!DIMENSIONE) return null;
  /* ⚠️ NON si ridimensiona la finestra: non funziona, ed e' misurato.
   *
   * Quattro tentativi in fila — misura nel costruttore, `setContentSize()`
   * prima del caricamento, di nuovo a `ready-to-show`, di nuovo subito prima
   * dello scatto, piu' `unmaximize()` e `setMaximizable(false)` — e il
   * renderer continuava a riportare `window.innerWidth` 1536.
   * `getContentSize()` rispondeva 1280x800 **ottimisticamente**, cioe' cio'
   * che avevamo chiesto, mentre il gestore di finestre non lo applicava mai.
   * La prova che erano lo stesso scatto: le tre risoluzioni davano dev.std
   * 34,1 / 34,1 / 34,0 ed entropia 2,23 / 2,23 / 2,22 — se la larghezza fosse
   * cambiata davvero, non si somiglierebbero cosi'.
   *
   * `enableDeviceEmulation` cambia il VIEWPORT del renderer e non tocca la
   * finestra: il gestore non c'entra piu'. E' anche lo strumento giusto per la
   * domanda di §10, che e' «il layout regge a larghezze diverse» — cioe' il
   * DEBORDO di R99 — non «quanti pixel accesi ha uno schermo piu' grande». */
  finestra.webContents.enableDeviceEmulation({
    screenPosition: "desktop",
    screenSize: { width: DIMENSIONE[0], height: DIMENSIONE[1] },
    viewSize: { width: DIMENSIONE[0], height: DIMENSIONE[1] },
    deviceScaleFactor: 0,
    viewPosition: { x: 0, y: 0 },
    scale: 1,
  });
  return { chiesta: DIMENSIONE };
}

/* ⚠️ Nessun `catch` che ritorni `null`. Un'impronta assente in
 * `occlusione.json` sarebbe indistinguibile da una misura senza provenienza, e
 * §11.7 regola 5 esiste per non averne: se il filo non si legge, il modo
 * fixture non deve produrre un esito che sembra buono. */
function impronta(f) {
  return crypto.createHash("sha256")
    .update(fs.readFileSync(f)).digest("hex").slice(0, 16);
}


/* ── §13: uno scatto per workspace, per il ciclo §11.7 ───────────────────── */

async function scattaScrivania(cartella) {
  /* In modo fixture si aspetta il SILENZIO invece dei 12 campioni: la
   * registrazione e' finita quando smette di arrivare roba. Vedi
   * `attendiSilenzio`. */
  if (FIXTURE) {
    await attendiSilenzio();
    // Il silenzio dei dati non e' la scena ferma: vedi `attendiScenaFerma`.
    await attendiScenaFerma();
  }
  /* ⚠️ IL DEBORDO BOCCIA QUI, e non in `verifica:scrivania`.
   *
   * L'assertion messa la' non vede il difetto per cui era scritta: quel
   * comando preme Alt+T e legge i pannelli DOPO, cioe' su una scrivania gia'
   * ricomposta dalle celle — dove il debordo non c'e' per costruzione.
   * Verificato togliendo il minimo: la guardia restava verde.
   * §11.7 regola 4 al contrario — non «il criterio e' vero per assenza del
   * fenomeno», ma «il criterio guarda dove il fenomeno non passa».
   *
   * Qui invece si misura lo STATO RIPRISTINATO, che e' esattamente dove il
   * difetto vive: un layout salvato stretto e riaperto largo. */
  let debordano = [];
  if (DIMENSIONE) {
    /* Un momento perche' il renderer ricomponga: `misuraArea()` gira su
       `resize`, e la scena si riadatta dopo. */
    await new Promise((r) => setTimeout(r, 1200));
    const vero = await finestra.webContents.executeJavaScript(
      "[window.innerWidth, window.innerHeight]");
    console.log(`  viewport    chiesto ${DIMENSIONE.join("x")} · ottenuto ${vero.join("x")}` +
      (vero[0] === DIMENSIONE[0] ? "" : " · NON APPLICATO"));
    /* R99: una cella troppo stretta non stringe il pannello, lo fa DEBORDARE.
       E' la domanda di §10, e si misura sul corpo di ogni pannello a schermo. */
    const deb = await finestra.webContents.executeJavaScript(`
      [...document.querySelectorAll(".winbox")]
        .filter((w) => getComputedStyle(w).display !== "none")
        .map((w) => {
          const c = w.querySelector(".wb-body");
          const r = c.firstElementChild?.firstElementChild ?? c.firstElementChild;
          const st = r ? getComputedStyle(r) : null;
          return { chi: w.dataset.modulo || w.dataset.pannello || "(senza nome)",
                   x: c.scrollWidth - c.clientWidth,
                   y: c.scrollHeight - c.clientHeight,
                   largo: Math.round(w.getBoundingClientRect().width),
                   min: st ? Math.round(Number.parseFloat(st.minWidth) || 0) : 0,
                   corpo: Math.round(c.clientWidth),
                   vuole: r ? Math.round(r.scrollWidth) : 0,
                   vuoleY: r ? Math.round(r.scrollHeight) : 0,
                   altaFinestra: Math.round(w.getBoundingClientRect().height) };
        })
        .filter((d) => d.x > 0 || d.y > 0)`);
    debordano = deb;
    console.log(deb.length
      ? `  DEBORDANO   ${deb.length} pannelli su ${vero[0]} px:\n` +
        deb.map((d) => `                ${d.chi.padEnd(11)} deborda ${d.x}x${d.y} · ` +
          `finestra ${d.largo} · corpo ${d.corpo} · min dichiarato ${d.min} · ` +
          `il contenuto ne vuole ${d.vuole}x${d.vuoleY} · finestra alta ${d.altaFinestra}`).join("\n")
      : `  debordo     nessuno a ${vero[0]} px`);
  }
  /* ⚠️ IL BUDGET PER MOTORE — `DIVARIO-PREMIUM.md` §12, aperto.
   *
   * L'invariante 26 da' tre tetti separati, e finora si misurava una cosa
   * sola: l'intervallo fra due fotogrammi. Con il render a richiesta quella
   * misura risponde sempre vsync e non dice quanto costa CHI. Adesso
   * `three/scena.js` e `pixi/glyphs.js` marcano il proprio render, e qui si
   * leggono le marche.
   *
   * ⚠️ Zero marche NON vuol dire zero costo: vuol dire che quel motore non ha
   * reso, che e' un'altra cosa (§11.7 regola 4). Si stampa «non misurabile». */
  const budget = await finestra.webContents.executeJavaScript(`(() => {
    const per = {};
    for (const e of performance.getEntriesByType("measure")) {
      (per[e.name] ||= []).push(e.duration);
    }
    const r = {};
    for (const [k, v] of Object.entries(per)) {
      /* ⚠️ IL PRIMO RENDER NON E' UN FOTOGRAMMA, e va separato SENZA sparire.
         Misurato sul globo, in ordine cronologico:
             [433 ms, 48.7]  [488, 3.1]  [551, 4.0]  [576, 0.5]  [577, 0]
         Il primo compila gli shader e carica i buffer; tutti gli altri stanno
         sotto i 4 ms contro un tetto di 8. Giudicare il tetto di §10.4 — che e'
         un budget di FOTOGRAMMA — sul costo della costruzione teneva «SFORA»
         acceso per sempre su un numero che non tornera' mai, cioe' un allarme
         permanente: quelli si smettono di leggere, ed e' lo stesso difetto di
         un test inchiodato a una coordinata.
         Il primo resta stampato. Escluderlo in silenzio sarebbe barare. */
      const primo = v[0];
      const resto = v.slice(1).sort((a, b) => a - b);
      const dopo = resto.length ? resto : v;
      r[k] = { n: v.length,
               primo: +primo.toFixed(2),
               mediana: +dopo[dopo.length >> 1].toFixed(2),
               max: +dopo[dopo.length - 1].toFixed(2),
               somma: +v.reduce((a, b) => a + b, 0).toFixed(1) };
    }
    // Chi sa misurarsi lo dichiara — vedi ui/src/anim/budget.js. Senza questo
    // elenco un file di misure vuoto non distingue «il motore non ha reso» da
    // «il motore non e' strumentato», che e' §11.7 regola 4.
    r.__strumentati = window.__motori ?? {};
    return r;
  })()`);
  const TETTI = { three: 8, pixi: 3, anime: 4 };
  const strumentati = budget.__strumentati ?? {};
  delete budget.__strumentati;
  console.log("  budget      per motore (§10.4, invariante 26) — in rapporto, non boccia");
  for (const [nome, tetto] of Object.entries(TETTI)) {
    const b = budget[nome];
    if (b) {
      console.log(`              ${nome.padEnd(6)} ${String(b.n).padStart(4)} render · ` +
        `costruzione ${String(b.primo).padStart(5)} ms · poi mediana ` +
        `${String(b.mediana).padStart(4)} ms · max ${String(b.max).padStart(5)} ms · ` +
        `tetto ${tetto} ms · ${b.max <= tetto ? "dentro" : "SFORA"}`);
      continue;
    }
    /* ⚠️ DUE ESITI DIVERSI, e prima erano lo stesso.
       «Zero marche» diceva NON MISURABILE anche per Pixi, che e' strumentato da
       sempre: li' zero marche vuol dire che il motore non ha reso in questa
       scena — assenza del FENOMENO — e non assenza della misura. Sono le due
       cose che §11.7 regola 4 esiste per non confondere, confuse dal rapporto
       che quella regola cita. */
    console.log(strumentati[nome]
      ? `              ${nome.padEnd(6)}    0 render · non ha reso in questa scena ` +
        "— strumentato, quindi lo zero e' una misura"
      : `              ${nome.padEnd(6)}    0 render · NON STRUMENTATO — nessuna ` +
        "marca nel codice, e zero marche non e' zero costo (§11.7 regola 4)");
  }
  /* ADR-010 — UNA scrivania, quindi UNO scatto.
   *
   * Prima questa funzione girava fra i quattro workspace e ne fotografava uno
   * per ciascuno: era il ciclo §11.7 applicato a quattro pagine. Le pagine non
   * ci sono piu', e quattro scatti della stessa scrivania sarebbero quattro
   * copie dello stesso file.
   *
   * Restano due stati da guardare, e sono due stati veri: la scrivania
   * intera, e la scrivania con un filtro acceso — dove cambia la barra e
   * cambia il dock, e NON cambia che cosa e' a schermo. E' esattamente il
   * criterio 1 di §26.9, ed e' una cosa che si giudica guardandola.
   */
  const path = require("node:path");
  fs.mkdirSync(cartella, { recursive: true });
  await attendiPronto();

  /* §5.2 e §5.3 del piano — stesso insieme di pannelli, stessa scena. NON si
     spera: si impone.
     La scrivania ripristina il layout SALVATO, che e' l'ultimo che qualcuno ha
     lasciato — e «qualcuno» comprende gli altri script. Misurato: dopo un giro
     di `npm run verifica:scrivania`, che apre tutto, questo scatto e' passato
     da 4 pannelli a 9 senza che nulla lo dicesse, e le due misure sarebbero
     finite nello stesso documento come se fossero confrontabili.
     Applicare la scena dichiarata prima di scattare costa una riga e toglie di
     mezzo l'intera classe di errore. Il nome della scena e' quello di
     `desk/moduli.js`, ed e' cio' che §5.2 chiama «dichiarato per nome». */
  /* La scena da comporre prima dello scatto. §26.9 criterio 6 vuole
 * `scene:briefing` a schermo, e questo era un letterale: il modo di scatto
 * sapeva comporre una scena sola, quella dell'avvio. Il nome resta il valore
 * predefinito, cosi' ogni scatto gia' preso continua a valere.
 *
 * ⚠️ La scena dev'essere DICHIARATA — `config/settings.toml`, §26.6 — e chi
 * la dichiara e' il core: un nome che il core non ha mandato non compone
 * niente, e `--verifica-scrivania` lo dice invece di scattare una scrivania
 * qualunque. */
const SCENA = opzione("--scena") ?? "avvio";
  await finestra.webContents.executeJavaScript(
    `window.__scrivania.scrivania.scena(${JSON.stringify(SCENA)})`);

  await fermaLaScrivania();
  if (FIXTURE) {
    /* La leva gemella di `window.__insegna.fissa()`: ferma il battito
     * dell'uptime e riscrive `up` con quello del CAMPIONE. Senza, due
     * riproduzioni della stessa registrazione mostrano due uptime diversi,
     * perche' quel campo non misura la sessione — misura da quanto e' aperta
     * la finestra. */
    const b = await finestra.webContents.executeJavaScript(
      "JSON.stringify(window.__barra?.fissa?.() ?? null)");
    console.log(`  barra       fissata · ${b}`);
  }
  /* §5.4 del piano — T+3 s dall'ultimo evento. `fermaLaScrivania` aspetta che
     le GEOMETRIE non cambino piu', che e' un'altra cosa: un pannello fermo puo'
     avere dentro un contatore che sale, un globo che finisce di comporsi, un
     carattere che arriva. Tre secondi non sono un numero scelto bene: sono il
     numero che il protocollo dichiara, ed e' il fatto che sia SEMPRE lo stesso
     a rendere confrontabili due misure. */
  await new Promise((r) => setTimeout(r, 3000));

  /* §5.5 — DUE scatti, e la mediana. Con due misure la mediana e' la media, e
     non e' quello il punto: il punto e' che due scatti a 250 ms di distanza
     dicono anche se la scrivania era davvero ferma. Se i byte coincidono non si
     muoveva niente; se differiscono, §5.4 non e' soddisfatto e il numero va
     letto sapendolo. Oggi differiscono — la nuvola dell'insegna gira senza
     causa, deroga 1 di DEROGHE-7dad2b8.md — e questa riga e' il modo in cui la
     deroga si vede in ogni misura invece di stare in un documento. */
  const uno = path.join(cartella, "scrivania.png");
  const scattoUno = await finestra.webContents.capturePage();
  const primo = scattoUno.toPNG();
  fs.writeFileSync(uno, primo);
  await new Promise((r) => setTimeout(r, 250));
  const gemello = path.join(cartella, "scrivania-b.png");
  const scattoDue = await finestra.webContents.capturePage();
  const secondo = scattoDue.toPNG();
  fs.writeFileSync(gemello, secondo);
  const fermi = primo.equals(secondo);

  /* §25.13.5 — il criterio di accettazione del marchio, e vuole DUE scatti.
   *
   * «Contrasto WCAG contro il composito sottostante» non si puo' leggere da un
   * solo scatto: sotto la scritta c'e' la nuvola, che e' diversa in ogni punto.
   * L'unico modo di sapere che colore ci sarebbe senza il marchio e' guardare
   * la stessa scrivania col marchio nascosto — stessa sessione, stesso istante
   * a 250 ms, cosi' che sotto ci sia la stessa nuvola e non un'altra.
   *
   * `visibility: hidden` e non `display: none`: il secondo toglierebbe
   * l'elemento dal flusso e la griglia di `.sfd` ricomporrebbe, cambiando cio'
   * che sta sotto. Il primo lascia tutto dov'e' e smette solo di dipingere. */
  const senza = path.join(cartella, "scrivania-senza-marchio.png");
  const rettMarchio = await finestra.webContents.executeJavaScript(`
    (() => {
      const m = document.querySelector(".sfd__marchio");
      if (!m) return null;
      const r = m.getBoundingClientRect();
      const c = getComputedStyle(m);
      m.style.visibility = "hidden";
      return { r: [r.left, r.top, r.width, r.height].map(Math.round),
               colore: c.color, corpo: c.fontSize, ombra: c.textShadow };
    })()`);
  if (rettMarchio) {
    await new Promise((r) => setTimeout(r, 120));
    fs.writeFileSync(senza, (await finestra.webContents.capturePage()).toPNG());
    await finestra.webContents.executeJavaScript(
      'document.querySelector(".sfd__marchio").style.visibility = ""');
    fs.writeFileSync(path.join(cartella, "marchio.json"),
      JSON.stringify(rettMarchio, null, 2) + "\n");
    console.log(`scatto ${senza} (marchio nascosto) — riquadro ` +
      `${rettMarchio.r[2]}x${rettMarchio.r[3]} a (${rettMarchio.r[0]}, ${rettMarchio.r[1]})`);
  } else {
    console.log("nessun .sfd__marchio: §25.13.5 non si puo' misurare");
  }

  /* La misura di occlusione — PIANO-CORE-E-DENSITA §5. Sta qui e non in
     `densita.mjs` per la ragione di §11.7 passo 0: «coperto» e' una proprieta'
     del LAYOUT, e il layout esiste solo dentro la finestra vera. Un PNG non sa
     che cosa aveva sotto. Lo script la legge da questo file. */
  const occlusione = await finestra.webContents.executeJavaScript(
    fs.readFileSync(path.join(__dirname, "..", "scripts", "occlusione-dom.js"), "utf-8"));
  occlusione.protocollo.scattiIdentici = fermi;
  occlusione.protocollo.budget = budget;
  /* §5.1 — e la risposta la sa solo Electron. Dalla pagina, «massimizzata» si
     puo' solo indovinare confrontando `innerWidth` con `screen.availWidth`, che
     su questo schermo sono 1536 e 1920: due unita' diverse separate dal fattore
     di scala 1,25, e il confronto rispondeva «no» su una finestra massimizzata.
     Qui e' un fatto, non una deduzione. */
  occlusione.protocollo.massimizzata = finestra.isMaximized();
  /* ⚠️ LA PROVENIENZA VIAGGIA COL NUMERO — §11.7 regola 5.
   *
   * «Un numero senza la sua sorgente non e' un numero: non si sa con che cosa
   * si puo' confrontare.» Chi legge questo file deve poter dire, senza chiedere
   * a nessuno, se la misura viene da una sessione viva o da una registrazione,
   * e da quale. Due numeri di provenienza diversa non si sottraggono.
   *
   * E la versione del renderer, perche' una fixture fissa i DATI e non il
   * renderer: un aggiornamento di driver o di font sposta il numero senza che
   * nel repo cambi niente. */
  occlusione.protocollo.fonte = FIXTURE
    ? { tipo: "registrazione", file: "docs/acceptance/SESSIONE-SCRIVANIA.jsonl",
        impronta: impronta(path.join(__dirname, "..", "docs", "acceptance",
                                     "SESSIONE-SCRIVANIA.jsonl")) }
    : { tipo: "viva", quando: new Date().toISOString() };
  occlusione.protocollo.renderer = {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    dpr: occlusione.protocollo.scala,
  };
  const dove = path.join(cartella, "occlusione.json");
  fs.writeFileSync(dove, JSON.stringify(occlusione, null, 2) + "\n");

  const quanti = occlusione.rettangoli.length;
  console.log(`scatto ${uno} (${quanti} pannelli a schermo su ` +
    `${occlusione.protocollo.aperti.length} aperti, scena ${SCENA}, nessun filtro)`);
  console.log(`scatto ${gemello} — ${fermi ? "identico: scrivania ferma"
    : "DIVERSO dal primo: qualcosa si muoveva, §5.4 non e' soddisfatto. " +
      "DOVE lo dice `node scripts/densita.mjs`, che il confronto fra i due " +
      "scatti ce l'ha gia' e sa attribuirlo ai rettangoli"}`);
  console.log(`occlusione ${dove}: pavimento coperto ` +
    `${occlusione.pavimento.copertoDaPannelli.toFixed(1)} %, ` +
    `caldi coperti ${occlusione.caldi.coperti}/${occlusione.caldi.sulPavimento}, ` +
    `icone coperte ${occlusione.icone.coperte}/${occlusione.icone.totale}, ` +
    `disco coperto ${occlusione.disco ? occlusione.disco.copertoDaPannelli.toFixed(1) + " %" : "(nessun data-disco)"}`);

  // Col filtro acceso: la barra evidenzia, il dock attenua, i pannelli NON si
  // muovono. Che l'ultima parte sia vera lo dice il confronto fra i due file.
  await finestra.webContents.executeJavaScript(
    "window.__scrivania.scrivania.vai(2)");
  await new Promise((r) => setTimeout(r, 400));
  const due = path.join(cartella, "scrivania-filtro-02.png");
  fs.writeFileSync(due, (await finestra.webContents.capturePage()).toPNG());
  console.log(`scatto ${due} (filtro 02)`);

  if (debordano.length) {
    console.log(`\nR99 — ${debordano.length} pannelli hanno il contenuto fuori ` +
      "dal proprio corpo: " + debordano.map((d) => d.chi).join(" · "));
    /* ⚠️ `app.exit` e non `process.exit`, ed e' l'OPPOSTO di quello che questo
       commento diceva fino al 25 agosto 2026.
       La riga precedente sceglieva `process.exit(1)` dichiarando «misurato, con
       app.exit(1) il processo padre riceveva comunque 0». Rimisurato mettendo
       un'uscita finta proprio qui e leggendo il codice nel padre:
           process.exit(7)                 -> il padre riceve 0
           app.exit(7)                     -> il padre riceve 7
           process.exitCode = 7; app.quit() -> il padre riceve 0
       Il figlio riportava `code=0` malgrado la stampa, cioe' la guardia
       stampava «R99 — 5 pannelli» e usciva verde: un criterio che non boccia,
       proprio quello che DEBORDO-R99.md dichiarava come limite senza saperne
       la causa. Ma nemmeno `app.exit` bastava, e il `return` qui sotto e' la
       meta' che mancava: senza, si prosegue fino a `app.exit(0)` due righe piu'
       giu' e la SECONDA uscita vince. Misurato anche questo — col `return`
       l'uscita e' 1, senza e' 0 — ed e' la ragione per cui la misura originale
       aveva concluso «app.exit(1) da' 0»: era vero, e la causa non era
       `app.exit`. */
    app.exit(1);
    return;
  }
  app.exit(0);
}

/* ── §25.13.5 in TUTTI gli stati — turno 4 ──────────────────────────────────
 *
 * ⚠️ Il criterio del marchio e' stato chiuso misurandolo in UNO dei sette stati
 * che §25.6 elenca: il riposo. Un criterio verificato in uno stato su sette non
 * e' verificato — e con quattro centesimi di margine sopra il minimo, qualunque
 * cosa cambi il composito sotto il nome lo rompe.
 *
 * Questo modo e' il gemello di `--scrivania`: stessa scena, stesso protocollo
 * §5, **pannelli aperti** come §25.13.5 pretende. Per ogni stato scrive nella
 * propria cartella i tre file che `densita.mjs --marchio` gia' legge, cosi' la
 * metrica resta UNA — non se ne scrive una seconda qui dentro.
 *
 * Gli stati sono quelli di §25.6, piu' due voci che stati non sono e che sono
 * marcate come tali:
 *   onda                 e' un evento; qui vale come INVILUPPO, tutti gli
 *                        anelli accesi insieme — cosa che il guscio non fa mai,
 *                        ma e' il suo estremo;
 *   _variante-campo-void non e' uno stato: e' la terza uscita di §25.13
 *                        (`NUCLEO-SCALA-ALZATA.md`) resa misurabile. Serve a
 *                        sapere quanto vale il campo, che nessuno aveva
 *                        misurato prima di giudicarla la piu' costosa.
 */
const STATI_MARCHIO = ["riposo", "t0", "t1", "ascolto", "t2", "subagent", "offline", "warn", "onda"];

async function scattaMarchioStati(radice) {
  const path = require("node:path");
  fs.mkdirSync(radice, { recursive: true });
  await attendiPronto();
  await finestra.webContents.executeJavaScript(
    'window.__scrivania.scrivania.scena("avvio")');
  await fermaLaScrivania();
  await new Promise((r) => setTimeout(r, 3000));

  const geo = await finestra.webContents.executeJavaScript("window.__insegna.geometria()");
  console.log("geometria: " + JSON.stringify(geo));

  /** I tre file che `--marchio` legge, per uno stato. */
  async function coppia(cartella) {
    fs.mkdirSync(cartella, { recursive: true });
    fs.writeFileSync(path.join(cartella, "scrivania.png"),
      (await finestra.webContents.capturePage()).toPNG());
    const m = await finestra.webContents.executeJavaScript(`
      (() => {
        const s = document.querySelector(".sfd__marchio");
        const r = s.getBoundingClientRect();
        const c = getComputedStyle(s);
        s.style.visibility = "hidden";
        return { r: [r.left, r.top, r.width, r.height].map(Math.round),
                 colore: c.color, corpo: c.fontSize, ombra: c.textShadow };
      })()`);
    await new Promise((r) => setTimeout(r, 120));
    fs.writeFileSync(path.join(cartella, "scrivania-senza-marchio.png"),
      (await finestra.webContents.capturePage()).toPNG());
    await finestra.webContents.executeJavaScript(
      'document.querySelector(".sfd__marchio").style.visibility = ""');
    fs.writeFileSync(path.join(cartella, "marchio.json"), JSON.stringify(m, null, 2) + "\n");
    return m;
  }

  const esito = { geometria: geo, stati: {} };
  for (const stato of STATI_MARCHIO) {
    const fissato = await finestra.webContents.executeJavaScript(
      `window.__insegna.fissa(${JSON.stringify(stato)})`);
    await new Promise((r) => setTimeout(r, 300));
    await coppia(path.join(radice, stato));
    esito.stati[stato] = fissato;
    console.log(`stato ${stato}: livello ${fissato.livello}, accesi [${fissato.accesi}]`);
  }

  /* ⚠️ NON e' uno stato: e' la terza uscita di §25.13 resa misurabile.
     `NUCLEO-SCALA-ALZATA.md` la giudica «la piu' costosa» senza averla mai
     misurata, e `PIANO-CORE-E-DENSITA.md` §8 chiede di misurarla prima di
     scartarla. Il campo passa a --bg-void, che e' il colore del pavimento:
     invisibile. Da qui si legge quanto vale il corpo del disco in densita' —
     una riga di stile iniettata, non una modifica al componente. */
  await finestra.webContents.executeJavaScript(`
    (() => {
      const st = document.createElement("style");
      st.id = "prova-campo-void";
      st.textContent = ".sfd .pnl-anelli__campo { fill: var(--bg-void); }";
      document.head.appendChild(st);
    })()`);
  await finestra.webContents.executeJavaScript('window.__insegna.fissa("riposo")');
  await new Promise((r) => setTimeout(r, 300));
  await coppia(path.join(radice, "_variante-campo-void"));
  await finestra.webContents.executeJavaScript(
    'document.getElementById("prova-campo-void").remove()');
  console.log("variante _variante-campo-void: campo a --bg-void");

  fs.writeFileSync(path.join(radice, "stati.json"), JSON.stringify(esito, null, 2) + "\n");
  app.exit(0);
}

/* ── §11.7 per il nucleo: gli stati che uno scatto normale non puo' mostrare ─
 *
 * ⚠️ La checklist §11.8 si guarda su un'immagine, e il nucleo ha quattro stati
 * che a immagine ferma sono indistinguibili: fermo e in moto sono lo stesso
 * pixel, e l'anello acceso lo si vede solo mentre una causa e' viva. Uno scatto
 * solo di questo componente e' un componente non verificato.
 *
 * Quindi si forzano le cause una per volta — le stesse funzioni che chiama il
 * bus, non una scorciatoia — e si fotografa ciascuna. Il ritaglio e' il disco
 * dichiarato in `data-disco`, non un riquadro scritto a mano: se il nucleo
 * cambia raggio, il ritaglio lo segue.
 */
async function scattaNucleo(cartella) {
  const path = require("node:path");
  fs.mkdirSync(cartella, { recursive: true });
  await attendiPronto();
  /* ⚠️ IL NUCLEO SI FOTOGRAFA SCOPERTO, e la prima stesura di questo modo non
     lo faceva: senza applicare la scena restavano aperti tutti e nove i
     pannelli, e «CORE SORGENTE» stava esattamente sopra il disco. Il ritaglio
     era giusto — centro (768, 421.5), raggio 162.9, verificato sui numeri — ed
     era la SCRIVANIA a essere sbagliata. Il difetto si vede solo guardando
     l'immagine, che e' il passo che §11.7 mette dopo la misura.
     Alt+H (`nascondiTutto`) e' anche lo stato di riposo di §25.7: il nucleo
     senza niente davanti e' esattamente cio' che questa verifica deve mostrare. */
  await finestra.webContents.executeJavaScript(`
    (async () => {
      const s = window.__scrivania.scrivania;
      await s.scena("avvio");
      if (!s.stato().tuttoNascosto) s.nascondiTutto();
    })()`);
  await fermaLaScrivania();
  await new Promise((r) => setTimeout(r, 1200));

  const riquadro = await finestra.webContents.executeJavaScript(`(() => {
    const s = document.querySelector(".sfd");
    if (!s || !s.dataset.disco) return null;
    const b = s.getBoundingClientRect();
    const [dx, dy, r] = s.dataset.disco.split(",").map(Number);
    const m = Math.round(r * 1.12);              // un dito di margine attorno
    return { x: Math.round(b.left + dx - m), y: Math.round(b.top + dy - m),
             width: 2 * m, height: 2 * m };
  })()`);
  if (!riquadro) { console.error("nessun .sfd con data-disco"); app.exit(2); return; }
  /* ⚠️ Si cattura TUTTO e si ritaglia dopo, invece di passare il riquadro a
     `capturePage`. Misurato: col riquadro {x:586, y:240, 364x364} — che e'
     esattamente il disco, verificato sui numeri — l'immagine tornata conteneva
     la fascia di schermo SOPRA il nucleo. Il ritaglio di `capturePage` non
     risponde alle coordinate della pagina su questa piattaforma, e non c'e'
     modo di accorgersene se non guardando il risultato.
     `NativeImage.crop` lavora sui pixel dell'immagine, che qui sono anche i
     pixel CSS — la cattura intera misura 1536x843, come la finestra. */
  const scatta = async (nome) => {
    const f = path.join(cartella, nome + ".png");
    const intera = await finestra.webContents.capturePage();
    const s = intera.getSize();
    const k = s.width / (await finestra.webContents.executeJavaScript("window.innerWidth"));
    const r = {
      x: Math.round(riquadro.x * k), y: Math.round(riquadro.y * k),
      width: Math.round(riquadro.width * k), height: Math.round(riquadro.height * k),
    };
    fs.writeFileSync(f, intera.crop(r).toPNG());
    console.log("scatto " + f);
  };

  const leva = (js) => finestra.webContents.executeJavaScript(js);
  const attendi = (ms) => new Promise((r) => setTimeout(r, ms));

  await leva("window.__insegna.forza(null)");
  await attendi(1600);
  console.log("livello del nucleo:", await leva('document.querySelector(".sfd").dataset.livello'),
    "· stato:", await leva('document.querySelector(".sfd").dataset.stato'));
  await scatta("nucleo-riposo");

  // A meta' della rampa d'avvio: e' l'istante in cui la partenza si vede.
  await leva("window.__insegna.forza('t1')");
  await attendi(420);
  await scatta("nucleo-t1-parte");
  await attendi(1400);
  await scatta("nucleo-t1-acceso");

  await leva("window.__insegna.forza('t2')");
  await attendi(1600);
  await scatta("nucleo-t2-acceso");

  // Il guscio, colto mentre attraversa: a meta' del viaggio.
  await leva("window.__insegna.forza(null)");
  await attendi(1800);
  await leva("window.__insegna.onda()");
  await attendi(460);
  await scatta("nucleo-onda");

  await leva("window.__insegna.forza(null); window.__insegna.fase(3)");
  await attendi(1200);
  await scatta("nucleo-fase-3");

  await leva("window.__insegna.fase(9)");
  await attendi(1200);
  await scatta("nucleo-fase-9");

  app.exit(0);
}

/* Si aspetta che la scrivania sia FERMA, non un tempo.
 *
 * Il primo avvio compone: three.js costruisce il globo, PixiJS l'atlante dei
 * glifi, le etichette si misurano dopo `document.fonts.ready`, e WinBox
 * posiziona le finestre. Con un'attesa a tempo lo scatto puo' cogliere la
 * scrivania a meta': in questo progetto e' successo due volte, una con un
 * pannello ancora sopra gli altri.
 *
 * La condizione vera non e' «e' passato abbastanza»: e' «non si muove piu'».
 */
async function fermaLaScrivania() {
  await finestra.webContents.executeJavaScript(`
    document.fonts.ready.then(() => new Promise((risolvi) => {
      const geometrie = () => [...document.querySelectorAll(".winbox")]
        .filter((w) => getComputedStyle(w).display !== "none")
        .map((w) => { const r = w.getBoundingClientRect();
          return [r.x | 0, r.y | 0, r.width | 0, r.height | 0].join(","); })
        .join(" | ");
      const scadenza = Date.now() + 12000;
      let prima = "";
      const guarda = () => {
        const ora = geometrie();
        // Uguale al giro prima E non vuota: due pannelli fermi a zero non
        // sono una scrivania ferma, sono una scrivania che non c'e' ancora.
        if ((ora === prima && ora !== "") || Date.now() > scadenza) {
          setTimeout(risolvi, 600);        // un respiro per l'ultimo disegno
          return;
        }
        prima = ora;
        setTimeout(guarda, 150);
      };
      guarda();
    }))
  `);
}

/* ── un pannello solo, ingrandito, nella finestra vera ──────────────────── */

/**
 * `npm run app -- --pannello <id> <file>`
 *
 * Il ciclo §11.7 giudica un componente per volta in galleria, e la scrivania
 * lo giudica nell'insieme. Manca il caso in mezzo: UN pannello, con i dati
 * veri del core, grande abbastanza da leggerlo. E' quello che serve quando si
 * vuole guardare da vicino una cosa sola.
 */
async function scattaPannello(id, destinazione) {
  await attendiPronto();
  const esito = await finestra.webContents.executeJavaScript(`(async () => {
    const s = window.__scrivania.scrivania;
    const c = await s.apri(${JSON.stringify(id)});
    if (!c) return { errore: "modulo sconosciuto: " + ${JSON.stringify(id)} };
    s.espandi(${JSON.stringify(id)});
    await new Promise((r) => setTimeout(r, 400));
    const pan = c.ospite.firstElementChild;
    const r = c.box.window.getBoundingClientRect();
    return {
      workspace: s.stato().workspace,
      stato: pan?.dataset.stato ?? "—",
      riquadro: [Math.round(r.x), Math.round(r.y),
                 Math.round(r.width), Math.round(r.height)],
    };
  })()`);

  if (esito.errore) { console.error(esito.errore); app.exit(2); return; }
  await new Promise((r) => setTimeout(r, 900));
  const [x, y, w, h] = esito.riquadro;
  const img = await finestra.webContents.capturePage({ x, y, width: w, height: h });
  fs.writeFileSync(destinazione, img.toPNG());
  console.log(`scatto ${destinazione} — ${id} su ws0${esito.workspace}, stato ${esito.stato}`);
  app.exit(0);
}

/* ── §13 criteri A e B: il dock e le scorciatoie nella finestra vera ─────── */

async function verificaScrivaniaEEsci() {
  await attendiPronto();

  /* ⚠️ IL DEBORDO SI LEGGE ADESSO, prima di toccare qualunque cosa.
   *
   * La prima stesura lo leggeva insieme a tutto il resto, cioe' DOPO che la
   * prova aveva premuto Alt+T: `affianca()` ricompone dalle celle, e su una
   * scrivania ricomposta il debordo non c'e' per costruzione. Verificato
   * togliendo il minimo dichiarato: la guardia restava verde mentre cinque
   * pannelli avevano il contenuto fuori.
   * E' §11.7 regola 4 al rovescio — non «il criterio e' vero per assenza del
   * fenomeno», ma «il criterio guarda dove il fenomeno non passa». Qui si
   * guarda lo stato RIPRISTINATO, che e' dove vive. */
  const debordoIniziale = await finestra.webContents.executeJavaScript(`
    [...document.querySelectorAll(".winbox")]
      .filter((w) => getComputedStyle(w).display !== "none")
      .map((w) => {
        const c = w.querySelector(".wb-body");
        return { chi: w.dataset.modulo || "(senza nome)",
                 x: c.scrollWidth - c.clientWidth,
                 y: c.scrollHeight - c.clientHeight };
      })
      .filter((d) => d.x > 0 || d.y > 0)`);

  const esito = await finestra.webContents.executeJavaScript(`(async () => {
    const { scrivania, scorciatoie, nonRealizzate, moduliIndicizzati } =
      window.__scrivania;
    // Mezzo secondo, non un decimo: premere la voce di un altro workspace lo
    // COMPONE, e comporre WS02 vuol dire costruire una scena three.js e una
    // pila CSS 3D. Con un'attesa corta il secondo clic arriva mentre il primo
    // sta ancora aprendo, e il criterio boccia la latenza invece della logica.
    const passo = () => new Promise((r) => setTimeout(r, 700));
    /* ⚠️ §26.3 — l'indice sta nel CATALOGO, non piu' nel dock.
     *
     * Il criterio A di §13 — «le otto voci aprono e chiudono il proprio
     * modulo» — non e' stato cancellato quando il dock ha ceduto l'indice: si
     * e' spostato qui, sulla linguetta MODULI. Cancellarlo sarebbe stato il
     * modo piu' comodo di far tornare i conti. */
    /* [data-tipo="modulo"] e non solo [data-voce]: la linguetta FILE e la
     * linguetta SCENE mettono tessere nello stesso nastro, e il criterio A
     * parla dell'INDICE DEI MODULI. */
    const tasti = () =>
      [...document.querySelectorAll('.cat__tessera[data-tipo="modulo"]')];
    const premuti = () => tasti().filter((b) => b.getAttribute("aria-pressed") === "true")
                                 .map((b) => b.textContent);

    /* A — le otto voci dell'INDICE aprono e chiudono il PROPRIO modulo.
     *
     * Si guarda il modulo, non il CONTEGGIO dei pannelli aperti — con ADR-010
     * sono sempre quattordici, e un conteggio non direbbe piu' niente.
     */
    const dock = [];
    for (const b of tasti()) {
      const premuto = () => b.getAttribute("aria-pressed") === "true";
      const prima = premuto();
      b.click(); await passo();
      const dopo1 = premuto();
      b.click(); await passo();
      const dopo2 = premuto();
      /* ADR-010 + R89: le pressioni sono TRE, non due.
       *
       * Con una scrivania sola un modulo aperto puo' essere sepolto, e allora
       * la prima pressione lo ALZA invece di chiuderlo — l'utente lo stava
       * cercando. Quindi da uno stato «aperto e sotto» servono: alza, chiude,
       * riapre. La proprieta' che resta, ed e' quella che conta, e' che il
       * pulsante torni sempre a dire la verita' su cio' che c'e' a schermo.
       */
      b.click(); await passo();
      const dopo3 = premuto();
      dock.push({ id: b.dataset.voce, voce: b.textContent, prima,
                  commuta: dopo1 !== prima || dopo2 !== dopo1,
                  torna: dopo3 === dopo1 || dopo2 === prima });
    }

    // B — le scorciatoie. Si spara un vero KeyboardEvent sul documento: e' la
    // stessa strada che fanno i tasti veri, non una chiamata alla funzione.
    const tasto = async (code) => {
      document.dispatchEvent(new KeyboardEvent("keydown", { code, altKey: true, bubbles: true }));
      await passo();
    };
    /* ADR-010: Alt+1…4 FILTRA e non cambia pagina, quindi si verificano due
     * cose invece di una: che il filtro cambi, e che il numero di pannelli a
     * schermo NON cambi. La seconda e' il criterio 1 di §26.9 — «nessun
     * percorso dell'interfaccia nasconde tre quarti dei pannelli». */
    const aSchermo = () => [...document.querySelectorAll(".winbox")]
      .filter((w) => getComputedStyle(w).display !== "none").length;
    const perTasto = [];
    for (const n of [2, 3, 4, 1]) {
      const prima = aSchermo();
      await tasto("Digit" + n);
      perTasto.push({ tasti: "Alt+" + n, filtro: scrivania.stato().filtro,
                      pannelliPrima: prima, pannelliDopo: aSchermo() });
    }
    // E premuto due volte lo stesso, il filtro si toglie: senza, un filtro
    // acceso non si spegne piu'.
    await tasto("Digit1");
    perTasto.push({ tasti: "Alt+1 di nuovo", filtro: scrivania.stato().filtro,
                    pannelliPrima: aSchermo(), pannelliDopo: aSchermo() });
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

    /* ADR-010 punto 3 — l'ombra e il segno del fuoco, misurati.
     *
     * §26.9 criterio 2: «due pannelli che si coprono restano distinguibili».
     *
     * ⚠️ Qui si leggeva borderTopColor, e §10.5 il bordo l'ha tolto
     * (border: 0). Con nessun bordo dichiarato quella proprieta' ricade sul
     * color ereditato — --txt-primary, cioe' #cdeef3 — IDENTICO sui due
     * pannelli. Il criterio confrontava due volte lo stesso numero, quindi era
     * falso per costruzione: verifica:scrivania usciva 1 comunque, e una
     * guardia sempre rossa smette di segnalare.
     *
     * Adesso si legge il segno che il fuoco cambia davvero: lo sfondo del
     * MARCATORE d'angolo (::before), che passa da --icona a --cy-500. E non
     * ci si accontenta che i due differiscano — si pretende il token
     * DICHIARATO, risolto dal foglio di stile invece che scritto qui. */
    const conFuoco = document.querySelector(".winbox.focus");
    const senzaFuoco = document.querySelector(".winbox:not(.focus)");
    const leggi = (el) => el && {
      marcatore: getComputedStyle(el, "::before").backgroundColor,
      ombra: getComputedStyle(el).boxShadow,
    };
    /* Il token risolto in rgb(...), per confrontarlo con un valore calcolato:
     * getPropertyValue renderebbe #4dd0e1, che non e' la stessa stringa. */
    const risolvi = (tok) => {
      const d = document.createElement("div");
      d.style.backgroundColor = "var(" + tok + ")";   // niente backtick: siamo DENTRO un template literal
      document.body.appendChild(d);
      const c = getComputedStyle(d).backgroundColor;
      d.remove();
      return c;
    };
    const cornici = {
      conFuoco: leggi(conFuoco), senzaFuoco: leggi(senzaFuoco),
      atteso: { conFuoco: risolvi("--cy-500"), senzaFuoco: risolvi("--icona") },
    };

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
      // L'indice ATTESO viene dalla registry, non da un numero scritto a mano.
      indice: moduliIndicizzati().map((m) => m.id),
      scorciatoie: scorciatoie.map((s) => s.tasti),
      nonRealizzate: nonRealizzate.map((s) => s.tasti),
      workspacePerTasto: perTasto,
      nascondi: { prima: primaH, dopo: dopoH, tornato: tornatoH },
      affianca: {
        spostata, ripristinata: primaT === dopoT,
        // Se non torna, si deve poter vedere DOVE non torna: un booleano
        // falso non dice se sia un pannello o quattordici.
        diverse: JSON.parse(primaT).map((g, i) => [i, g, JSON.parse(dopoT)[i]])
          .filter(([, a, b]) => JSON.stringify(a) !== JSON.stringify(b))
          .slice(0, 4),
      },
      controlli,
      cornici,
      pannelli,
      preload: Object.keys(window.jarvis ?? {}).sort(),
    };
  })()`);

  /* E — il budget di §10.4 sull'insieme, non su un componente alla volta.
   *
   * `npm run bench` misura la cella di galleria che accende globo, glifi e
   * anelli insieme. Qui si misura la SCRIVANIA — e da ADR-010 la scrivania e'
   * UNA, con tutto aperto insieme: three.js, PixiJS, CSS 3D, due webview e
   * anime.js nello stesso fotogramma. E' la misura che decide se «si apre
   * tutto» sia difendibile o solo una frase.
   *
   * Si guardano gli intervalli fra fotogrammi. Con render-on-demand e
   * l'invariante 25 — zero animazione ambientale — una scrivania ferma non
   * deve costare niente: la mediana sta sul vsync e il MASSIMO dice se
   * qualcosa, ogni tanto, fa perdere un fotogramma.
   *
   * Due misure e non una: a riposo, e con un filtro acceso. La seconda serve a
   * verificare che filtrare non costi — se costasse, vorrebbe dire che sta
   * ricomponendo qualcosa, cioe' che non e' un filtro.
   */
  const budget = [];
  const misuraFrame = (etichetta) => finestra.webContents.executeJavaScript(`
      new Promise((risolvi) => {
        const dt = []; let prima = performance.now();
        const passo = () => {
          const ora = performance.now(); dt.push(ora - prima); prima = ora;
          if (dt.length < 180) requestAnimationFrame(passo);
          else {
            dt.sort((a, b) => a - b);
            risolvi({ quando: ${JSON.stringify(etichetta)}, frame: dt.length,
                      mediana: +dt[90].toFixed(2),
                      p95: +dt[170].toFixed(2),
                      max: +dt[dt.length - 1].toFixed(2) });
          }
        };
        requestAnimationFrame(passo);
      })`);

  await new Promise((r) => setTimeout(r, 1500));
  budget.push(await misuraFrame("tutto aperto, nessun filtro"));
  budget.push({
    pannelli: await finestra.webContents.executeJavaScript(
      "window.__scrivania.scrivania.stato().aperti.length"),
  });
  await finestra.webContents.executeJavaScript(
    "window.__scrivania.scrivania.vai(3)");
  await new Promise((r) => setTimeout(r, 800));
  budget.push(await misuraFrame("con il filtro 03 acceso"));

  /* ⚠️ IL COSTO DEL NUCLEO SOTTO CARICO — mai misurato fino al 23 agosto 2026.
   *
   * `PIANO-CORE-E-DENSITA.md` §9 lo elenca fra le cose non toccate: «i numeri
   * sono tutti a riposo». E a riposo il numero e' zero per costruzione — il
   * nucleo non chiede un fotogramma finche' non c'e' una causa, e la verifica
   * qui sopra lo conta.
   *
   * Ma «a riposo costa zero» non dice quanto costa quando lavora, ed e' la sola
   * domanda che l'invariante 26 pone davvero: il budget e' 15 ms in tutto per
   * tre motori, e il nucleo li spende quando gira.
   *
   * Si misura mettendolo in moto — quattro anelli insieme, che e' piu' di
   * quanto §25.6 permetta in una volta sola — sulla scrivania piena. E' il caso
   * PEGGIORE, non quello tipico, ed e' quello che un tetto vuole sapere. */
  await finestra.webContents.executeJavaScript(`
    (() => {
      const i = window.__insegna;
      if (!i) return null;
      for (const c of ["t1", "ascolto", "t2", "subagent"]) i.forza(c);
      // forza tiene una causa sola: per averle tutte e quattro insieme si
      // chiedono le rotazioni direttamente, che e' il carico massimo possibile.
      i.fissa("onda");
      return true;
    })()`);
  await new Promise((r) => setTimeout(r, 1200));
  budget.push(await misuraFrame("col nucleo in moto, carico massimo"));
  await finestra.webContents.executeJavaScript("window.__insegna.forza(null)");

  esito.budget = budget;

  /* ── Il nucleo di §25.6: se gira, sta lavorando ─────────────────────────
   *
   * ⚠️ Questo blocco esiste perche' «gli anelli girano solo con una causa» non
   * si vede in una schermata. Una fotografia del nucleo fermo e una del nucleo
   * in moto sono la stessa immagine; l'unica differenza sta nel TEMPO, e il
   * ciclo §11.7 fotografa. Qui si guarda invece la sola cosa che distingue le
   * due: si toglie ogni causa e si conta che nessun anello sia in moto, poi se
   * ne mette una e si conta che si muova quello giusto — quello che §25.6
   * assegna a quella causa, non «uno qualsiasi».
   *
   * Le leve sono le stesse funzioni che chiama il bus (`window.__insegna`), non
   * una scorciatoia: forzare «t1» fa esattamente quello che fa un nodo t1
   * attivo in agent.mesh. */
  esito.nucleo = await finestra.webContents.executeJavaScript(`(async () => {
    const ins = window.__insegna;
    if (!ins) return { errore: "window.__insegna non c'e'" };
    /* La separazione fra l'inchiostro del marchio e la fascia piu' interna.
       E' cio' che rende §25.13.5 invariante negli stati: se il nome sta tutto
       dentro il campo, sotto di lui c'e' un token dichiarato e nessuna regola
       di stato lo tocca, perche' tutte vivono su [data-anello]. */
    const respiro = () => new Promise((r) => setTimeout(r, 260));
    const moti = () => ins.causeOra.filter((c) => c.moto).map((c) => c.chi);
    const out = { soglie: ins.soglie, cause: ins.cause };
    out.geometria = ins.geometria();

    ins.forza(null); await respiro();
    out.aRiposo = moti();
    const f0 = ins.fotogrammi;

    for (const chi of ["t1", "ascolto", "t2", "subagent"]) {
      ins.forza(chi); await respiro();
      out[chi] = moti();
    }

    // T0 non «dura»: succede. Non deve mettere in moto nessun anello, deve
    // chiedere qualche fotogramma e poi smettere.
    ins.forza(null); await respiro();
    const f1 = ins.fotogrammi;
    ins.forza("t0"); await respiro();
    out.t0 = moti();
    const f2 = ins.fotogrammi;
    /* ⚠️ «Si e' fermato» si misura DOPO, non intorno. Contare i fotogrammi in
       una finestra che comincia mezzo secondo prima della fine dell'impulso
       conta la coda dell'impulso e risponde «sei» a qualunque durata di
       finestra — allungarla non li toglie, sono gia' dentro. La domanda giusta
       vuole una finestra che comincia quando il fenomeno e' finito. */
    await new Promise((r) => setTimeout(r, 1000));
    const f3 = ins.fotogrammi;
    await new Promise((r) => setTimeout(r, 500));
    out.dopoLImpulsoSiFerma = ins.fotogrammi - f3;
    out.impulsoChiedeFotogrammi = f2 - f1;
    out.codaDellImpulso = f3 - f2;

    // La fase accende dal mozzo verso il bordo: a fase 3 devono restare accesi
    // solo gli anelli con soglia <= 3, cioe' i due piu' interni.
    const assestato = () => new Promise((r) => setTimeout(r, 1200));
    ins.fase(3); await assestato();
    const svg = document.querySelector(".sfd__disco");
    out.opacitaAFase3 = [...svg.querySelectorAll("[data-anello]")]
      .map((g) => +(+g.style.opacity).toFixed(2));
    ins.fase(9); await assestato();
    out.opacitaAFase9 = [...svg.querySelectorAll("[data-anello]")]
      .map((g) => +(+g.style.opacity).toFixed(2));

    /* A riposo, quanti fotogrammi chiede in un secondo intero: e' l'invariante
       25 reso un numero. Una nuvola che gira sempre ne chiederebbe una
       sessantina; qui deve essere zero.
       ⚠️ DUE FINESTRE, E SI TIENE LA MINORE — e non e' prudenza, e' una
       correzione. Con una sola finestra la misura ha risposto **87** una volta
       su tre: non un ciclo acceso, ma un evento vero del bus — un advisory, un
       nodo che cambia — caduto dentro il secondo sbagliato. La leva forza
       ferma le cause forzate, non il core.
       Un'animazione ambientale gira in ENTRAMBE le finestre; un evento cade in
       una sola. Il minimo distingue le due cose, che e' esattamente la domanda
       dell'invariante 25: non «si e' mosso qualcosa», ma «si muove qualcosa
       SENZA causa». */
    ins.forza(null);
    await new Promise((r) => setTimeout(r, 1200));
    const fA = ins.fotogrammi;
    await new Promise((r) => setTimeout(r, 1000));
    const finestraUno = ins.fotogrammi - fA;
    const fB = ins.fotogrammi;
    await new Promise((r) => setTimeout(r, 1000));
    const finestraDue = ins.fotogrammi - fB;
    out.finestreDiRiposo = [finestraUno, finestraDue];
    out.fotogrammiInUnSecondoDiRiposo = Math.min(finestraUno, finestraDue);
    out.fotogrammiInTutto = ins.fotogrammi;
    return out;
  })()`);

  console.log(JSON.stringify(esito, null, 1));

  /* ⚠️ Qui c'era `=== 8`, e i moduli indicizzati sono diventati DIECI: il
   * criterio A di §13 e' stato rosso da quando sono entrati meteo e globo, e
   * non perche' l'indice fosse rotto — perche' il numero era una fotografia.
   *
   * Adesso il conto lo fa `moduliIndicizzati()`, e si verifica la cosa che
   * conta davvero: che l'indice elenchi ESATTAMENTE i moduli indicizzati, ne'
   * uno di meno (un modulo irraggiungibile) ne' uno di piu' (una voce che apre
   * qualcosa che la registry non conosce). Un conteggio non lo direbbe. */
  const idsIndice = [...esito.indice].sort().join(",");
  const idsTessere = esito.dock.map((d) => d.id).sort().join(",");
  const dockOk = esito.dock.length > 0 && idsTessere === idsIndice &&
    esito.dock.every((d) => d.commuta && d.torna);
  const attesi = [2, 3, 4, 1, null];
  const wsOk = esito.workspacePerTasto.every(
    (w, i) => w.filtro === attesi[i] && w.pannelliDopo === w.pannelliPrima);
  const hOk = esito.nascondi.dopo === 0 && esito.nascondi.tornato === esito.nascondi.prima;
  const ctrlOk = esito.controlli.length >= 3 &&
    esito.controlli.every((c) => c.startsWith("BUTTON:"));
  const tOk = esito.affianca.spostata && esito.affianca.ripristinata;
  /* L'ombra c'e' su tutti e il fuoco si distingue. Le due condizioni sono
   * separate: un'ombra che manca e un marcatore che non cambia sono due
   * difetti diversi, e un solo booleano li confonderebbe. */
  const ombraOk = !!esito.cornici.conFuoco &&
    esito.cornici.conFuoco.ombra !== "none" &&
    esito.cornici.senzaFuoco?.ombra !== "none";
  /* ⚠️ IL DEBORDO ADESSO BOCCIA — e prima era raccolto e basta.
   *
   * `debordaX`/`debordaY` stavano in `esito.pannelli` da mesi, stampati e mai
   * asseriti, col commento accanto che diceva pure perche' servivano: «un
   * pannello che esce dalla propria cornice si vede prima di ogni altra cosa».
   * La Fase 0 del piano FUI ne ha trovati CINQUE su sei, e nessun criterio era
   * rosso. Un numero raccolto e non giudicato non e' una misura: e' un
   * appunto. */
  const debordoOk = debordoIniziale.length === 0;

  const cor = esito.cornici;
  const fuocoOk = !!cor.conFuoco && !!cor.senzaFuoco &&
    cor.conFuoco.marcatore === cor.atteso.conFuoco &&
    cor.senzaFuoco.marcatore === cor.atteso.senzaFuoco &&
    cor.conFuoco.marcatore !== cor.senzaFuoco.marcatore;
  /* §25.6 — una causa per anello, e nessun moto senza causa. Le tre condizioni
     sono separate perche' sono tre difetti diversi: un nucleo che gira sempre,
     un nucleo che non gira mai, e un nucleo che gira ma muove l'anello di
     un'altra causa. */
  const n = esito.nucleo ?? {};
  const nucleoFermo = Array.isArray(n.aRiposo) && n.aRiposo.length === 0 &&
    n.fotogrammiInUnSecondoDiRiposo === 0;
  const nucleoGira = ["t1", "ascolto", "t2", "subagent"]
    .every((chi) => Array.isArray(n[chi]) && n[chi].length === 1 && n[chi][0] === chi);
  const nucleoImpulso = Array.isArray(n.t0) && n.t0.length === 0 &&
    n.impulsoChiedeFotogrammi > 0 && n.dopoLImpulsoSiFerma === 0;
  /* Valori ESATTI, non «piu' di mezzo»: le opacita' si agganciano al bersaglio
     e la finestra d'attesa e' piu' lunga del transitorio, quindi non c'e'
     ragione di accontentarsi di una disuguaglianza. A fase 3 restano accesi i
     due anelli con soglia <= 3 — i due piu' interni — e gli altri stanno al
     sedicesimo di luce, che arrotondato a due cifre e' 0,06. */
  /* ⚠️ Il franco e' la guardia vera di §25.13.5, ed e' piu' forte del contrasto:
     vale in tutti gli stati insieme invece che in quello fotografato. Se il
     marchio arriva a toccare la fascia piu' interna, il composito sotto il nome
     smette di essere un token dichiarato e diventa una media — ed e' cosi' che
     il criterio e' caduto a 2,94:1 il 23 agosto 2026. */
  const franco = (n.geometria || {}).franco;
  const nucleoFranco = typeof franco === "number" && franco > 0;

  const nucleoFase =
    JSON.stringify(n.opacitaAFase3) === JSON.stringify([0.06, 0.06, 0.06, 1, 1]) &&
    JSON.stringify(n.opacitaAFase9) === JSON.stringify([1, 1, 1, 1, 1]);

  if (!debordoOk) {
    console.log(`\nR99 — ${debordoIniziale.length} pannelli hanno il contenuto ` +
      "fuori dal proprio corpo, allo stato ripristinato: " +
      debordoIniziale.map((d) => `${d.chi} ${d.x}x${d.y}`).join(" · "));
  }
  app.exit(debordoOk && dockOk && wsOk && hOk && ctrlOk && tOk && ombraOk && fuocoOk &&
           nucleoFermo && nucleoGira && nucleoImpulso && nucleoFase &&
           nucleoFranco ? 0 : 1);
}

/* ⚠️ In modo fixture NON si aspetta `attendiPronto`.
 *
 * Quella funzione aspetta 12 campioni di `telemetry`, cioe' un punto
 * all'INIZIO dello stream: con una registrazione da 172 campioni si
 * fotograferebbe il grafico a un dodicesimo, e quanti ne siano arrivati al
 * momento dello scatto dipenderebbe da un polling a 200 ms.
 *
 * Si aspetta invece il SILENZIO: la registrazione e' finita quando smette di
 * arrivare roba. 1500 ms regge con margine — il buco piu' largo dentro lo
 * stream e' il periodo della telemetria, 400 ms. */
async function attendiSilenzio(quiete = 1500, scadenza = 180000) {
  const fine = Date.now() + scadenza;
  while (Date.now() < fine) {
    if (ultimoMessaggioMs && Date.now() - ultimoMessaggioMs >= quiete) return true;
    await new Promise((r) => setTimeout(r, 100));
  }
  console.log("  ⚠️ la registrazione non e' mai andata in silenzio");
  return false;
}

/**
 * Aspetta che la SCENA si fermi, non che i dati tacciano.
 *
 * ⚠️ `attendiSilenzio()` guarda l'ultimo messaggio arrivato dal riproduttore.
 * E' il silenzio dell'INGRESSO: i pannelli si compongono, si animano e il dock
 * si riempie DOPO. Fra il silenzio dei dati e la scena ferma passa un tempo
 * che dipende dal carico della macchina, e lo scatto cadeva la' dentro.
 *
 * Misurato il 27 agosto — cinque giri sugli stessi identici sorgenti, nessun
 * altro Electron in competizione:
 *
 *     entropia  2,300  2,320  2,335  2,430  2,335   (soglia 2,4)
 *     riempito  23,10  23,70  24,30  28,00  24,30   (soglia 25)
 *     dock      18,2   18,2   12,6   24,2   12,6    (soglia 20)
 *
 * **Uno su cinque passava.** Il dock che oscilla fra 12,6 e 24,2 non e' rumore
 * della metrica: e' la scrivania fotografata a meta' composizione. Ogni numero
 * di §11.9 misurato prima di questa riga descrive il momento dello scatto,
 * non il disegno — e un «DENSITA' CONFORME» valeva un lancio di moneta.
 *
 * ## Perche' la FIRMA e non i pixel
 *
 * Confrontare due scatti byte a byte non converge mai: gli orologi vivi
 * cambiano un pixel al secondo per sempre. Si confronta invece cio' che varia
 * davvero fra un giro e l'altro — **quali pannelli sono aperti, dove, quanto
 * grandi, e quante voci ha il dock** — che e' esattamente la sorgente della
 * dispersione qui sopra.
 */
async function attendiScenaFerma(uguali = 2, passo = 400, scadenza = 25000) {
  const fine = Date.now() + scadenza;
  let vista = null;
  let stabili = 0;
  while (Date.now() < fine) {
    const firma = await finestra.webContents.executeJavaScript(`
      JSON.stringify({
        pannelli: [...document.querySelectorAll(".winbox")]
          .filter((w) => getComputedStyle(w).display !== "none")
          .map((w) => {
            const r = w.getBoundingClientRect();
            return [w.dataset.modulo || w.dataset.pannello || "?",
                    Math.round(r.x), Math.round(r.y),
                    Math.round(r.width), Math.round(r.height)];
          })
          .sort(),
        dock: document.querySelectorAll(".dock *[data-modulo]").length,
      })`);
    if (firma === vista) {
      if (++stabili >= uguali) return true;
    } else {
      stabili = 0;
      vista = firma;
    }
    await new Promise((r) => setTimeout(r, passo));
  }
  console.log("  ⚠️ la scena non si e' mai fermata: lo scatto non e' attribuibile");
  return false;
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
  /* ⚠️ In modo fixture ci si collega DOPO che la pagina ha caricato.
   *
   * `versoRenderer` scarta i messaggi finche' `rendererPronto` e' falso e poi
   * `riconsegna()` ne rimanda **uno per topic**: quanti campioni di telemetria
   * cadono in quella finestra dipende da quanto ci mette la pagina a caricare.
   * E' la sorgente di non determinismo piu' grossa del giro, e colpisce insieme
   * `rx`, la lunghezza del grafico e `xs.length/120` nel piede.
   *
   * L'ordine regge da solo: `creaFinestra()` registra il proprio
   * `did-finish-load` prima di questo, e i listener partono nell'ordine di
   * registrazione — quando `collega` parte, `rendererPronto` e' gia' vero.
   *
   * Fuori dalla misura NON vale: dal vivo il buffer di `ultimoPerTopic` e' la
   * scelta giusta, e il commento che lo motiva sta poco sopra. */
  if (FIXTURE) finestra.webContents.once("did-finish-load", collega);
  else collega();
  if (SCREENSHOT) finestra.webContents.once("did-finish-load", () => scattaEEsci(SCREENSHOT));
  if (BENCH) finestra.webContents.once("did-finish-load", () => misuraEEsci());
  if (VERIFICA) finestra.webContents.once("did-finish-load", () => verificaEEsci());
  if (SCRIVANIA) finestra.webContents.once("did-finish-load", () => scattaScrivania(SCRIVANIA));
  if (NUCLEO) finestra.webContents.once("did-finish-load", () => scattaNucleo(NUCLEO));
  if (MARCHIO_STATI) finestra.webContents.once("did-finish-load", () => scattaMarchioStati(MARCHIO_STATI));
  if (VERIFICA_SCRIVANIA)
    finestra.webContents.once("did-finish-load", () => verificaScrivaniaEEsci());
  if (PANNELLO)
    finestra.webContents.once("did-finish-load",
      () => scattaPannello(PANNELLO, opzione("--in") ?? "shots/pannello.png"));
});

app.on("window-all-closed", () => app.quit());
