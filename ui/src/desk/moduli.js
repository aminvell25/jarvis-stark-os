/* Il registro della scrivania — SPEC §13, **superato da ADR-010**.
 *
 * §13 da' due cose e non una terza: da' **gli otto moduli** del dock e **i
 * quattro workspace** col proprio dominio e il proprio accento; non dice quale
 * pannello vada dove. Quella e' una decisione, ed e' presa qui, in un posto
 * solo, dove si puo' leggere tutta insieme.
 *
 * ## ADR-010 — i quattro workspace diventano quattro CATEGORIE
 *
 * Quattro pagine significano che **tre quarti del sistema e' sempre
 * invisibile**, e che ogni informazione va cercata invece che vista. Il
 * riferimento `famiglia-a/01` non ha pagine: ha una superficie sola, densa,
 * dove tutto convive.
 *
 * I quattro domini sopravvivono come **categorie**: restano un modo di
 * ordinare e smettono di essere un modo di nascondere. `categoria` non governa
 * piu' la visibilita' di niente — la usano il filtro della barra e, quando
 * arrivera' (§26.3), le linguette del catalogo.
 *
 * ## Moduli e arredo sono due cose diverse
 *
 *   MODULO   una delle otto voci di §13. Ha un pulsante nel dock, e il dock
 *            POSSIEDE il suo stato: aperto o chiuso, e chiuso resta finche'
 *            non lo si riapre. Un modulo che tornasse da solo farebbe mentire
 *            il dock.
 *
 *   ARREDO   fa parte della composizione del workspace. Entrare in un
 *            workspace lo compone; chiudere un pezzo fa spazio adesso, non per
 *            sempre.
 *
 * Non e' una distinzione estetica: sono due domande diverse — «e' acceso?» e
 * «com'e' disposta la stanza?» — e trattarle uguale rende sbagliata una delle
 * due.
 *
 * ## Le celle, e perche' non sono pixel
 *
 * Ogni pannello dichiara `[colonna, riga, colonne, righe]` su una griglia di
 * COLONNE x RIGHE. I pixel li calcola `scrivania.js` dall'area vera. Cosi' la
 * composizione non dipende dalla risoluzione, e «affianca» (`Alt+T`, §13) non
 * ha bisogno di un secondo algoritmo: e' ri-applicare la disposizione
 * dichiarata.
 *
 * ## Come si alimenta ogni pannello
 *
 * Quasi tutti prendono un topic e lo passano ad `aggiorna`. Tre no, e la
 * differenza e' vera, non un dettaglio:
 *
 *   anelli   non hanno un topic: mostrano lo STATO dell'agente, che va
 *            composto da `state.snapshot` e `agent.mesh`
 *   glifi    vogliono i BYTE, non un messaggio: e' un log esadecimale del
 *            traffico, e il traffico e' cio' che passa sul socket
 *   board    vuole `board.cards`, che nessuno pubblica: si compone da
 *            `archive.notes`, che invece esiste
 */

import * as anelli from "../anim/rings.js";
import * as board from "../css3d/board.js";
import * as piani from "../css3d/planes.js";
import * as agenti from "../panels/agents.js";
import * as browser from "../panels/browser.js";
import * as consolePannello from "../panels/console.js";
import * as quadranti from "../panels/dials.js";
import * as file from "../panels/files.js";
import * as gesture from "../panels/gestures.js";
import * as globo from "../panels/globe.js";
import * as meteo from "../panels/meteo.js";
import * as news from "../panels/news.js";
import * as periodica from "../panels/periodic.js";
import * as sorgente from "../panels/source.js";
import * as cartella from "../panels/cartella.js";
import * as telemetria from "../panels/telemetry.js";
import * as glifi from "../pixi/glyphs.js";

/** La griglia su cui sono dichiarate le celle. */
export const COLONNE = 12;
export const RIGHE = 4;

/**
 * Le quattro categorie — i workspace di §13, che ADR-010 ha smesso di usare
 * come pagine.
 *
 * L'accento non e' decorazione. §13: «Workspace con dominio, non numeri
 * vuoti… cosi' che la barra porti informazione invece di contarli». Vale
 * identico per una categoria: dice di che cosa parla un pannello, non dove
 * sta.
 */
export const CATEGORIE = [
  { n: 1, dominio: "Sistema e telemetria", accento: "--cy-500" },
  { n: 2, dominio: "File e progetti", accento: "--cy-300" },
  { n: 3, dominio: "Web e ricerca", accento: "--cy-700" },
  { n: 4, dominio: "3D e modelli", accento: "--amber" },
];

/* ── come si alimenta un pannello ────────────────────────────────────────── */

/** Il caso normale: uno o piu' topic, dritti ad `aggiorna`. */
function daTopic(...topic) {
  return (pannello, bus) => {
    for (const t of topic) bus.su(t, (msg) => pannello.aggiorna(msg));
  };
}

/**
 * Gli anelli mostrano lo stato dell'agente (§16), che non e' un topic: e' il
 * riassunto di due messaggi diversi. Si compone qui e non nel pannello, perche'
 * il pannello e' un componente e questa e' una decisione dell'ambiente.
 *
 * ⚠️ **Esportata perche' la usa anche lo strato di presenza** (§25.6: «Anche
 * l'alimentazione esiste… Si sposta in presenza.js senza modifiche»). Il
 * nucleo e il pannello «Stato agente» sono lo STESSO componente in due
 * contesti, e devono leggere lo stesso stato dallo stesso posto: due copie di
 * questa funzione sarebbero due verita' che il primo cambiamento separa.
 */
export function alimentaAnelli(pannello, bus) {
  const stato = { livello: "nominal", attivo: false, stato: "—", motivo: "", da_s: 0 };

  bus.su("state.snapshot", (m) => {
    stato.da_s = Math.round(m.core?.uptime_s ?? 0);
    const auth = m.voce?.auth?.stato;
    stato.livello = auth === "degraded_llm" ? "degraded" : "nominal";
    stato.stato = m.voce?.abilitata
      ? (m.voce?.t1_vivo ? "T1 in ascolto" : "T1 non vivo")
      : "voce spenta";
    stato.motivo = `${m.tools?.length ?? 0} tool in allowlist`;
    pannello.aggiorna(stato);
  });

  bus.su("agent.mesh", (m) => {
    const attivi = (m.nodi ?? []).filter((n) => n.attivo);
    stato.attivo = attivi.length > 0;
    if (attivi.length) stato.motivo = attivi.map((n) => n.id).join(" · ");
    pannello.aggiorna(stato);
  });

  bus.suStato(({ stato: s }) => {
    if (s === "connesso") return;
    // Il core non c'e': gli anelli si fermano e lo dicono. Continuare a
    // girare mostrerebbe un sistema vivo che non e' vivo — invariante 25 e
    // invariante 23 dicono la stessa cosa da due lati.
    pannello.aggiorna({ ...stato, attivo: false, livello: "offline",
                        stato: "core non collegato", motivo: "" });
  });
}

/**
 * I glifi sono un log dei BYTE che passano sul socket. Nella galleria e' la
 * codifica di un messaggio vero; qui sono i messaggi veri, tutti.
 */
function alimentaGlifi(pannello, bus) {
  const codifica = new TextEncoder();
  // TUTTO cio' che passa, telemetria compresa. La prima versione la saltava —
  // «sarebbero sempre gli stessi byte» — e il pannello restava a 0 byte con il
  // core acceso: un log del traffico che esclude il 95% del traffico non e' un
  // log del traffico, e il ciclo §11.7 l'ha mostrato al primo scatto.
  bus.suOgni((msg) => pannello.aggiungi(codifica.encode(JSON.stringify(msg))));
}

/**
 * La board vuole `board.cards`; il core pubblica `archive.notes`. La forma e'
 * la stessa a meno del nome e dell'`url` della carta viva — che oggi non ha un
 * produttore, e la carta lo dichiara invece di inventarlo.
 */
function alimentaBoard(pannello, bus) {
  bus.su("archive.notes", (m) =>
    pannello.aggiorna({ topic: "board.cards", note: m.note }));
}

/* ── il registro ─────────────────────────────────────────────────────────── */

/**
 * `id` e' il nome che si dice a voce: sono le stesse parole del gruppo
 * `_PANNELLI` in `core/llm/grammar.py`, e «apri il globo» deve trovare questa
 * riga. `alias` copre le forme che la grammatica accetta e che non sono l'id.
 */
export const MODULI = [
  // ── 01 · Sistema e telemetria ──────────────────────────────────────────
  {
    id: "telemetria", etichetta: "Telemetria", categoria: 1, modulo: true,
    cella: [0, 0, 5, 2], componente: telemetria,
    // Due topic: la telemetria a 2,5 Hz e lo snapshot, che porta il consumo
    // vocale del mese (ADR-004). Il pannello smista su .
    alimenta: daTopic("telemetry", "state.snapshot"),
  },
  {
    id: "agenti", etichetta: "Mesh agenti", categoria: 1, modulo: true,
    cella: [5, 0, 4, 2], componente: agenti, alimenta: daTopic("agent.mesh"),
  },
  {
    id: "console", etichetta: "Console", categoria: 1, modulo: true,
    cella: [0, 3, 5, 1], componente: consolePannello,
    // Tutto: e' una traccia, e una traccia che scegliesse cosa mostrare non
    // servirebbe a scoprire niente.
    alimenta: (p, bus) => bus.suOgni((m) => p.aggiorna(m)),
  },
  {
    id: "anelli", etichetta: "Reattore", categoria: 1,
    cella: [9, 0, 3, 2], componente: anelli, alimenta: alimentaAnelli,
  },
  {
    id: "quadranti", etichetta: "Quadranti", categoria: 1,
    cella: [0, 2, 5, 1], componente: quadranti, alimenta: daTopic("telemetry"),
  },
  {
    id: "glifi", etichetta: "Glifi", categoria: 1,
    cella: [5, 2, 7, 2], componente: glifi, alimenta: alimentaGlifi,
  },

  // ── 02 · File e progetti ───────────────────────────────────────────────
  {
    id: "file", etichetta: "File manager", categoria: 2, modulo: true,
    // Cinque colonne, e ci si e' arrivati misurando: tre e quattro stanno
    // sotto la `min-width` che il pannello dichiara (5 x --grid = 550 px), e
    // su uno schermo da 1536 il debordamento era di 176 e di 48 px. La
    // larghezza di una cella dipende dallo schermo, la min-width no: vince
    // la seconda, o il pannello si scrolla in orizzontale per sempre.
    cella: [0, 0, 5, 4], componente: file, alimenta: daTopic("fs.list"),
  },
  {
    id: "sorgente", etichetta: "Core sorgente", categoria: 2, modulo: true,
    cella: [5, 0, 7, 2], componente: sorgente, alimenta: daTopic("source.tree"),
  },
  /* ⚠️ LA CARTELLA E' UN MODULO, e i suoi dati sono VERI.
   *
   * §26.5: «una cartella che contenga file veri mostra il percorso risolto nel
   * piede». Qui i file arrivano da `source.tree`, che il core gia' pubblica —
   * `{files: [{path, bytes}]}`, percorsi relativi alla radice del progetto — e
   * da li' si ricavano le voci di primo livello: le directory una volta sola,
   * i file sciolti per nome. Nessun dato inventato: l'invariante 23 non ammette
   * segnaposto, e un elenco finto in una cartella e' proprio il caso che quella
   * regola descrive.
   *
   * `cella` e' 3 colonne per 1 riga e non di piu', ed e' una misura: il caldo
   * del riferimento sta al 5,70 % della superficie e la forbice di §11.8 e'
   * 3-6 %. Una cartella in una cella [4, 2] porterebbe il corpo manila a
   * ~9,5 % dello schermo da sola, cioe' oltre il tetto — il caldo che significa
   * diventerebbe caldo che riempie. */
  {
    id: "cartella", etichetta: "Cartella", categoria: 2, modulo: true,
    cella: [4, 3, 3, 1], componente: cartella,
    alimenta: (pannello, bus) => bus.su("source.tree", (msg) => {
      const file = Array.isArray(msg?.files) ? msg.files : [];
      const cime = new Map();
      for (const f of file) {
        const [testa, ...resto] = String(f.path).split("/");
        if (!cime.has(testa)) cime.set(testa, resto.length > 0);
      }
      pannello.aggiorna({
        etichetta: "sorgenti",
        percorso: msg?.radice ?? null,
        voci: [...cime].map(([nome, dentro]) => ({ nome, tipo: dentro ? "cartella" : "file" })),
      });
    }),
  },
  {
    id: "archivio", etichetta: "Piani d'archivio", categoria: 2, alias: ["piani"],
    cella: [5, 2, 7, 2], componente: piani, alimenta: daTopic("archive.notes"),
  },

  // ── 03 · Web e ricerca ─────────────────────────────────────────────────
  {
    id: "browser", etichetta: "Browser", categoria: 3, modulo: true,
    /* Senza pagina aperta questo pannello e' una barra dell'indirizzo vuota:
       otto colonne per una riga di testo. Meta' larghezza finche' non c'e'
       niente dentro — §11.6 regola 3. */
    cella: [0, 0, 8, 2], cellaRidotta: [0, 0, 4, 2], componente: browser,
    alimenta: daTopic("web.open", "youtube.play"),
  },
  {
    id: "news", etichetta: "News", categoria: 3, modulo: true,
    /* §11.6 regola 3 e `DIVARIO-PREMIUM.md` §5: a gate chiuso questo pannello
       dice due righe, e due righe non valgono quattro colonne per quattro
       righe. Metà larghezza quando `data-stato` e' `vuoto`. */
    cella: [8, 0, 4, 4], cellaRidotta: [8, 0, 2, 4], componente: news,
    alimenta: daTopic("news.card", "news.argomenti", "agent.advisory"),
  },
  {
    id: "meteo", etichetta: "Meteo", categoria: 3, modulo: true,
    // Cella larga e bassa: e' una striscia, come nel riferimento.
    cella: [0, 3, 6, 1], componente: meteo, alimenta: daTopic("weather.forecast"),
    /* ⚠️ FUORI dalla piastrellatura della categoria, e va dichiarato.
     *
     * Le celle delle quattro categorie sono quattro piastrellature COMPLETE
     * della stessa griglia: erano la disposizione di quando le categorie erano
     * pagine, ed e' la ragione per cui aprirle insieme produceva una cascata
     * (R88). Adesso compongono le SCENE, e la cella di un modulo e' solo la
     * sua posizione iniziale quando lo si apre da solo.
     *
     * Per i moduli dichiarati da §13 la piastrellatura resta e un test la
     * impone — e' documentazione di come nacquero. Per quelli aggiunti dopo
     * non ha piu' senso: `meteo` e' una striscia e non ha un quarto di griglia
     * da riempire. */
    fuoriPiastrellatura: true,
  },
  {
    id: "board", etichetta: "Board", categoria: 3,
    cella: [0, 2, 8, 2], componente: board, alimenta: alimentaBoard,
  },

  // ── 04 · 3D e modelli ──────────────────────────────────────────────────
  {
    id: "globo", etichetta: "Globo tattico", categoria: 4, modulo: true,
    cella: [0, 0, 5, 4], componente: globo, alimenta: daTopic("geo.timezones"),
  },
  {
    id: "periodica", etichetta: "Tavola periodica", categoria: 4,
    cella: [5, 0, 7, 4], componente: periodica, alimenta: () => {},
  },

  // ── fuori composizione ─────────────────────────────────────────────────
  //
  // Le gesture aprono la telecamera. Il pannello esiste ed e' verificato, ma
  // non sta in nessun workspace di serie: comparirebbe la spia di §14 per una
  // telecamera che nessuno ha chiesto di accendere. Si apre da solo quando
  // arriva il primo `gesture.frame`, cioe' quando `vision.enabled` e' vero.
  {
    id: "gesture", etichetta: "Gesture", categoria: 1, suRichiesta: true,
    cella: [5, 2, 4, 2], componente: gesture, alimenta: daTopic("gesture.frame"),
  },
];

const PER_ID = new Map(MODULI.map((m) => [m.id, m]));
for (const m of MODULI) for (const a of m.alias ?? []) PER_ID.set(a, m);

/** Il modulo che si chiama cosi', oppure `undefined`. Accetta gli alias. */
export function modulo(id) {
  return PER_ID.get(String(id ?? "").toLowerCase());
}

/** I pannelli di una categoria, nell'ordine di dichiarazione. */
export function dellaCategoria(n) {
  return MODULI.filter((m) => m.categoria === n && !m.suRichiesta);
}

/* ── §26.6 — le scene ────────────────────────────────────────────────────────
 *
 * ## Perche' ce n'e' una QUI e non solo in `settings.toml`
 *
 * §26.6 dichiara le scene nelle impostazioni, ed e' giusto: una scena e'
 * intenzione umana, e accanto ci va scritto perche'. Ma la composizione di
 * PARTENZA non puo' dipendere da un file di configurazione aggiornato — al
 * primo avvio su una macchina nuova non esiste, e la scrivania si comporrebbe
 * da sola. Quindi la scena `avvio` sta nel codice, e le impostazioni la
 * possono SOSTITUIRE per nome oltre che aggiungerne altre.
 *
 * Una sola regola per la fusione: **a parita' di nome vince chi l'ha scritta a
 * mano.** Un valore predefinito che scavalca una decisione dell'utente e' un
 * valore predefinito rotto.
 *
 * ## Perche' una scena e non «apri tutto»
 *
 * ADR-010 diceva «si apre tutto, e la scrivania affollata e' il punto». La
 * misura ha detto altro: le celle qui sotto sono quattro piastrellature
 * COMPLETE della stessa griglia, una per categoria, e aprirle insieme produce
 * una CASCATA diagonale in cui di quattordici pannelli se ne leggono due —
 * peggio delle quattro pagine che ADR-010 aveva tolto.
 *
 * Il difetto non erano le pagine: era che **niente componeva**. La cella
 * dichiarata accanto a ogni modulo resta la sua posizione quando lo si apre da
 * solo; la composizione della scrivania la decide una scena.
 */
export const SCENE = [
  {
    nome: "avvio",
    descrizione: "cosa vive, cosa succede, dove — il resto a un clic dal catalogo",
    /* ⚠️ IL FONDO — §26.5, e fino al 24 agosto 2026 non c'era.
     *
     * La sezione e' specificata, `desk/icone.js` la disegna da giorni e sul
     * piano c'era **una** icona, residuo di `prova-icone.mjs`. Una scena e'
     * una disposizione DICHIARATA: dichiara quali pannelli si aprono, e da
     * qui anche che cosa e' posato sul piano di lavoro.
     *
     * ⚠️ Non sono segnaposto. Ogni voce rimanda a un modulo REGISTRATO in
     * MODULI: la stessa cosa che il catalogo indicizza, non una copia finta.
     * E la duplicazione col catalogo e' voluta, non un difetto — §26.5 la
     * mette per prima: «l'icona nel catalogo NON sparisce, il catalogo e'
     * l'indice e la scrivania e' il piano di lavoro».
     *
     * La fila sta sul bordo basso del pavimento, a destra del catalogo: e'
     * l'unica striscia larga che nessun pannello e nessun disco occupano —
     * misurata, 1536x96 a partire da y 716 sullo schermo.
     *
     * ⚠️ y 700, e ci si e' arrivati per due misure. A 668 il pannello
     * `file` — che occupa 844..1436 in x e finisce a y 715 — ne copriva OTTO
     * su dieci: si vedevano le etichette e non le piastre. Contate
     * dall'occlusione, 19 icone su 21 coperte. Un'icona che non si vede non e'
     * un oggetto posato, e' un oggetto perso.
     * A 716 le icone ci stavano, ma il core le riportava a 703: `adatta()`
     * taglia contro l'area dichiarata, e 716 piu' l'altezza dell'icona la
     * sfonda. Una coordinata che il core corregge non e' una coordinata: e'
     * una richiesta. */
    fondo: {
      icone: ["telemetria", "agenti", "console", "file", "sorgente",
              "cartella", "browser", "news", "meteo", "globo"]
        .map((nome, k) => ({ tipo: "modulo", nome, x: 756 + k * 68, y: 700 })),
      cartelle: [],
    },
    /* ⚠️ IL CENTRO E' LIBERO, ed e' la ragione di questa disposizione.
     *
     * §25 dichiara tre uscite per lo strato di presenza. Questa e' quella che
     * il riferimento documenta davvero: in `famiglia-a/10` l'elemento
     * centrale e' **circondato** dal chrome, non coperto — §25.1 lo cita per
     * esteso. I quattro pannelli stanno ai due lati; in mezzo non c'e' un
     * pannello, c'e' il nucleo (`desk/presenza.js`).
     *
     * La stesura precedente componeva cinque pannelli con due sovrapposizioni
     * volute e riempiva tutta la larghezza. Era una composizione migliore
     * della cascata che l'aveva preceduta, ma non lasciava un pixel al fondo:
     * misurato sul mockup di famiglia-d, uno strato di presenza sotto quella
     * scena arrivava a schermo con **122 pixel su 264.049**. Uno sfondo dietro
     * cose che lo nascondono non si vede, per quanto poco costi.
     *
     * ## Perche' `anelli` non c'e' piu'
     *
     * Perche' E' il nucleo. Lo stesso componente, spostato di strato (§25.6:
     * «Non va riscritto. Va spostato di strato»). Tenerlo anche come pannello
     * nella scena vorrebbe dire la stessa informazione due volte, una delle
     * due in un riquadro. Resta nel catalogo: chi lo vuole come pannello lo
     * apre, e allora ci sono davvero due letture — una di fondo e una di
     * dettaglio, che e' un'altra cosa dal duplicato.
     *
     * ## La geometria, e l'occlusione che resta
     *
     * Il nucleo e' largo il 64 % dell'altezza dell'area (§25.7): su 1536x843
     * fa **502 px**, centrato in x = 768. La griglia e' di 12 colonne da
     * 128 px, quindi servirebbero **quattro colonne libere al centro**
     * (512 px) e quattro per lato. Ma `telemetria` dichiara `min-width` di 5
     * colonne (550 px) e in quattro **non entra**: R99 — una cella troppo
     * stretta non stringe il pannello, lo fa DEBORDARE.
     *
     * Quindi la banda alta ha 5 colonne a sinistra e 4 a destra, e il nucleo
     * resta coperto dalla quinta colonna di `telemetria` per **123 px** del
     * proprio bordo sinistro, nella sola meta' superiore: circa il 10 % del
     * disco. E' l'occlusione minima che questa griglia consente, ed e'
     * dichiarata invece di essere scoperta guardando lo scatto.
     *
     * ⚠️ Le `min-width` non si indovinano: telemetria 5 colonne (550 px),
     * globo, agenti e news 4 (440 px). Un test le impone. */
    pannelli: [
      { id: "telemetria", cella: [0, 0, 5, 2], z: 1 },
      { id: "globo", cella: [0, 2, 4, 2], z: 1 },
      { id: "agenti", cella: [8, 0, 4, 2], z: 1 },
      /* ⚠️ Le news si stringono a una riga, e il file manager prende l'altra.
         Misurato: il pannello news occupa il 12,3 % dello schermo e mostra il
         proprio stato vuoto, perche' il Watcher e' costruito e non gira —
         `news.card` non esce mai. Dodici punti di schermo per due righe di
         testo sono il posto piu' caro della scrivania.
         Il file manager ci mette 452 file veri da `fs.list`, e la sua
         superficie e' manila per la stessa ragione della cartella: §26.5
         chiama --manila il colore di «cartelle e contenitori», e un elenco di
         file dentro una radice e' un contenitore.
         Il caldo del riferimento e' 5,70 % ed e' SPARSO — celle al 10-38 % in
         tutta l'immagine — mentre il nostro stava in un blocco solo, saturo al
         70 %. Questo lo mette anche dall'altra parte dello schermo. */
      /* ⚠️ QUI NON C'E' `cellaRidotta`, ed e' una misura, non una dimenticanza.
       *
       * §11.6 regola 3 dice che un pannello con poco da dire si rimpicciolisce,
       * e il meccanismo c'e' (`scrivania.js`, `osservaSuperficie`). Provato su
       * questa cella: `news` scende da 472 a 232 px, e il metro lo boccia —
       *
       *     pavimento nudo   29,0 %  ->  32,4 %
       *     L>60             26,1 %  ->  24,4 %   SOTTO la soglia di 25
       *     entropia          2,23   ->   2,18
       *
       * In una scena CURATA la contrazione non restituisce spazio a nessuno:
       * lascia un buco, e il buco costa piu' di quanto il pannello vuoto
       * valesse. La regola vale dove la dimensione la decide il modulo — cioe'
       * quando lo si apre dal catalogo — non dove l'ha decisa chi ha composto.
       * Chi vorra' contrarre anche qui dia prima la cella liberata a qualcuno. */
      { id: "news", cella: [8, 2, 4, 1], z: 1 },
      { id: "file", cella: [7, 3, 5, 1], z: 1 },
      /* ⚠️ LA CARTELLA STA SOPRA IL DISCO, e la cella e' il risultato di due
         misure sbagliate prima di quella giusta.
         Il turno 6 aveva concluso che nella scena non c'era posto, contando una
         min-width di 440 px — che e' quella di TELEMETRIA, non della cartella:
         la sua e' calc(--grid * 2.4) = 264, e nel varco sopra il disco, largo
         368, ci sta.
         La prima cella provata era [4, 3, 4, 1], sotto il disco: misurata, il
         disco passava da 0,0 % a 6,7 % coperto, e lo scatto mostrava il
         CATALOGO sopra meta' del pannello — i nomi dei file illeggibili. Due
         difetti che nessun ragionamento aveva previsto e uno sguardo ha visto
         subito.
         Questa cella e' una riga sola, sopra il disco: y 36-200 contro un disco
         che comincia a 259. Misurato: disco coperto 0,0 %, caldo 3,2 %. */
      { id: "cartella", cella: [5, 0, 3, 1], z: 1 },
    ],
  },
];

/**
 * Che cosa c'e' sulla scrivania la PRIMA volta, quando non c'e' un layout
 * salvato da rimettere: i pannelli della scena iniziale.
 *
 * ⚠️ **Non e' piu' «tutto».** Vedi il commento di `SCENE`: aprire tutto non e'
 * comporre, e la misura sullo scatto lo ha mostrato. Cio' che non e' nella
 * scena non e' nascosto — e' CHIUSO, e sta nel catalogo, che e' l'indice
 * sempre a schermo. E' la differenza fra i quattro workspace di prima, che
 * nascondevano senza dirlo, e una composizione da cui si esce con un clic.
 */
export function composizioneIniziale(scena = SCENE[0]) {
  return (scena?.pannelli ?? [])
    .map((p) => ({ ...modulo(p.id), cella: p.cella, z: p.z }))
    .filter((m) => m.id);
}

/** Gli otto moduli di §13, nell'ordine dichiarato.
 *
 * Si chiamava `moduliIndicizzati` finche' l'indice stava nel dock. Da §26.3 sta
 * nel catalogo, e il nome vecchio avrebbe mandato a cercarlo dove non e' piu'.
 */
export function moduliIndicizzati() {
  return MODULI.filter((m) => m.modulo);
}
