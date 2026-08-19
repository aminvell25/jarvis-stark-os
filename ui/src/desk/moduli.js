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
import * as news from "../panels/news.js";
import * as periodica from "../panels/periodic.js";
import * as sorgente from "../panels/source.js";
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
 */
function alimentaAnelli(pannello, bus) {
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
    cella: [0, 0, 5, 2], componente: telemetria, alimenta: daTopic("telemetry"),
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
  {
    id: "archivio", etichetta: "Piani d'archivio", categoria: 2, alias: ["piani"],
    cella: [5, 2, 7, 2], componente: piani, alimenta: daTopic("archive.notes"),
  },

  // ── 03 · Web e ricerca ─────────────────────────────────────────────────
  {
    id: "browser", etichetta: "Browser", categoria: 3, modulo: true,
    cella: [0, 0, 8, 2], componente: browser,
    alimenta: daTopic("web.open", "youtube.play"),
  },
  {
    id: "news", etichetta: "News", categoria: 3, modulo: true,
    cella: [8, 0, 4, 4], componente: news,
    alimenta: daTopic("news.card", "news.argomenti", "agent.advisory"),
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

/**
 * Che cosa c'e' sulla scrivania la PRIMA volta, quando non c'e' un layout
 * salvato da rimettere.
 *
 * ⚠️ **Non e' piu' «il workspace 1».** Con una scrivania sola non esiste un
 * primo workspace, ed esiste invece una domanda che prima non si poteva porre:
 * quanto ne apriamo?
 *
 * ADR-010 dice «chi apre tutto insieme ottiene una scrivania affollata: e' il
 * punto», e parla della scelta dell'utente. All'avvio la scelta la facciamo
 * noi, e la facciamo su una misura: **con tutti e tredici i pannelli aperti il
 * budget di frame di §10.4 regge** — vedi `docs/acceptance/ADR-010.md`. Quindi
 * si apre tutto, e la scrivania affollata e' quello che si vede al primo
 * avvio, come nel riferimento.
 *
 * Restano fuori solo i pannelli `suRichiesta`: `gesture` comparirebbe con la
 * spia di §14 accesa per una telecamera spenta.
 */
export function composizioneIniziale() {
  return MODULI.filter((m) => !m.suRichiesta);
}

/** Gli otto moduli di §13, nell'ordine dichiarato.
 *
 * Si chiamava `moduliIndicizzati` finche' l'indice stava nel dock. Da §26.3 sta
 * nel catalogo, e il nome vecchio avrebbe mandato a cercarlo dove non e' piu'.
 */
export function moduliIndicizzati() {
  return MODULI.filter((m) => m.modulo);
}
