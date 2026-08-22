/* La cornice della scrivania — barra e dock — dentro la galleria.
 *
 * Barra e dock sono componenti visivi come gli altri, e §11.8 vale anche per
 * loro: se non passassero dalla galleria, l'audit dei token non li vedrebbe e
 * l'invariante 18 su quei due file sarebbe una promessa invece di un
 * controllo.
 *
 * ⚠️ **La scrivania qui e' un finto, e deve esserlo.** Una scrivania vera
 * costruirebbe quattordici pannelli dentro WinBox, che nella galleria non e'
 * nemmeno caricato. Qui si giudicano la composizione, la tipografia e i
 * colori; che i pulsanti FACCIANO qualcosa e' il criterio A di §13, e si
 * verifica nella finestra vera con `npm run verifica`.
 *
 * Lo stato scelto e' un sistema vivo: **filtro 02 acceso** (ADR-010: e' un
 * filtro, non una pagina — la barra evidenzia e il dock attenua le altre
 * categorie, e nessun pannello sparisce), sei moduli su otto aperti, T2 al
 * lavoro, RAM oltre la soglia di §16 — l'unico punto in cui compare l'accento
 * caldo, e serve a far vedere che compare solo quando significa qualcosa.
 *
 * ## §26.5 entra da qui, e non e' una comodita'
 *
 * Icone libere e cartelle sono cornice dell'ambiente quanto la barra e il
 * dock. Senza passare dalla galleria, l'audit dei token non vedrebbe
 * `desk/icone.js` e l'invariante 18 su quel file sarebbe una promessa invece
 * di un controllo — che e' esattamente la ragione per cui questo montaggio
 * esiste. Si costruiscono col codice VERO, passando da `ripristina()`: una
 * copia statica del loro markup proverebbe il markup della copia.
 */

import { crea as creaBarra, css as cssBarra } from "../../desk/barra.js";
import { crea as creaCatalogo, css as cssCatalogo } from "../../desk/catalogo.js";
import { crea as creaDock, css as cssDock } from "../../desk/dock.js";
import { crea as creaIcone, css as cssIcone } from "../../desk/icone.js";
import { CATEGORIE } from "../../desk/moduli.js";

export const meta = { nome: "chrome", versione: "1" };
export const css = `${cssBarra}\n${cssCatalogo}\n${cssDock}\n${cssIcone}`;

/** Il bus, ridotto a cio' che barra e dock usano. */
function busFinto() {
  const iscritti = new Map();
  const ogni = [];
  return {
    su(topic, cb) {
      if (!iscritti.has(topic)) iscritti.set(topic, []);
      iscritti.get(topic).push(cb);
    },
    // La barra conta i byte che passano sul socket, come fa il pannello dei
    // glifi: senza `suOgni` il campo `rx` non esisterebbe, e il montaggio
    // mostrerebbe una barra diversa da quella dell'app.
    suOgni(cb) { ogni.push(cb); },
    suStato() {},
    manda(msg) {
      for (const cb of iscritti.get(msg.topic) ?? []) cb(msg);
      for (const cb of ogni) cb(msg);
    },
  };
}

function scrivaniaFinta(stato) {
  return {
    osserva(cb) { cb(stato); return () => {}; },
    vai() {}, tutto() {}, alterna() {}, nascondiTutto() {}, affianca() {},
    apri() {}, scena() {},
  };
}

export async function monta(ospite) {
  ospite.style.width = "1600px";

  const bus = busFinto();
  const scrivania = scrivaniaFinta({
    filtro: 2,
    tuttoNascosto: false,
    aperti: ["telemetria", "agenti", "console", "file", "sorgente", "news"],
    fuoco: "file",
    // §26.6: la linguetta SCENE le elenca, e la barra dice in quale ci si trova.
    scene: [{ nome: "avvio", descrizione: "cosa vive, cosa succede, dove" },
            { nome: "briefing", descrizione: "il mattino" },
            { nome: "officina", descrizione: "3D e progetti" }],
    scena: "avvio",
  });

  creaBarra(ospite, { scrivania, bus, categorie: CATEGORIE });

  /* §26.5 — il fondo. Nell'app lo strato e' `position: fixed` sul viewport;
   * qui si ancora al blocco della galleria, o le icone finirebbero sopra la
   * cornice della pagina invece che dentro il componente. */
  const fondo = document.createElement("div");
  fondo.style.position = "relative";
  fondo.style.height = "150px";
  ospite.appendChild(fondo);
  const icone = creaIcone(fondo, { scrivania, bus });
  icone.strato.style.position = "absolute";
  await icone.ripristina({
    cartelle: [
      // Una piena e una VUOTA: zero e' uno stato esplicito (§26.5,
      // invariante 23), e va guardato come gli altri.
      { id: "cartella.1", x: 24, y: 16, etichetta: "renders", aperta: false },
      { id: "cartella.2", x: 148, y: 16, etichetta: "core", aperta: false },
    ],
    icone: [
      { tipo: "modulo", nome: "globo", x: 300, y: 20, dentro: null },
      { tipo: "file", nome: "staffa-v3.skp", x: 396, y: 20, dentro: null },
      { tipo: "modulo", nome: "periodica", x: 492, y: 20, dentro: null },
      { tipo: "file", nome: "note-di-cantiere.md", x: 0, y: 0,
        dentro: "cartella.1" },
      { tipo: "modulo", nome: "board", x: 0, y: 0, dentro: "cartella.1" },
    ],
  });
  /* §26.3: il catalogo e' la parte piu' grande della cornice, e la piu' nuova.
   * Il contenitore che lo regge nell'app riempie lo spazio libero; in galleria
   * non c'e' spazio libero, quindi lo si mette dentro un blocco alto quanto
   * basta a vederlo tutto. */
  const spazio = document.createElement("div");
  spazio.style.height = "260px";
  spazio.style.display = "flex";
  ospite.appendChild(spazio);
  creaCatalogo(spazio, { scrivania, bus });
  creaDock(ospite, { scrivania, bus });

  /* ⚠️ Si aspetta che le tessere siano ENTRATE, e non e' pignoleria.
   *
   * Il catalogo anima l'entrata con `stagger(60)` (§10.4, riga «Dock»): con
   * otto voci l'ultima parte 420 ms dopo la prima e finisce 640 ms dopo
   * l'inizio. La galleria si dichiarava `pronto` appena `monta()` ritornava, e
   * `npm run shot` fotografava li'.
   *
   * Misurato sullo scatto: delle otto tessere, sei erano ESATTAMENTE il fondo
   * della vista (#0f1418) e due a L 29 e L 23, cioe' due valori intermedi
   * dell'opacita' — la griglia colta a meta' volo. Guardando quello scatto si
   * concludeva che il componente disegnava due tessere su otto, che e' falso.
   *
   * La condizione vera non e' «e' passato abbastanza tempo»: e' «non si muove
   * piu'». Stessa forma di `fermaLaScrivania()` in `app/main.js`, e stessa
   * ragione — in questo progetto lo scatto a meta' ha gia' ingannato due volte.
   */
  await new Promise((risolvi) => {
    const scadenza = Date.now() + 4000;
    const guarda = () => {
      const tessere = [...spazio.querySelectorAll(".cat__tessera")];
      const ferme = tessere.length > 0 &&
        tessere.every((t) => getComputedStyle(t).opacity === "1");
      if (ferme || Date.now() > scadenza) risolvi();
      else requestAnimationFrame(guarda);
    };
    guarda();
  });

  /* §13 / rilievo 2: lo snapshot COMPLETO, coi campi che la barra mostra.
   * Sono i valori veri di un core acceso su questa macchina — un montaggio
   * che ne mandasse meta' fotograferebbe una barra spenta, e la barra spenta
   * e' proprio il difetto da cui questa revisione nasce. */
  bus.manda({
    topic: "state.snapshot", fase: 9,
    core: { pid: 48219, uptime_s: 15153, seccomp: false },
    ws: { socket: "/run/user/1000/jarvis-os/core.sock", clients: 2 },
    tools: new Array(21),
    quota: { attivi: 1, max_concurrent: 2, restanti: 12 },
    settings: {
      voice: { stt_provider: "deepgram", tts_provider: "deepgram" },
      llm: { backend: "claude-code" },
      fs: { allowed_roots: ["a", "b", "c"] },
      chiavi_presenti: ["deepgram_api_key", "guardian_api_key"],
    },
    voce: { abilitata: false, auth: { stato: "nominal" } },
  });
  bus.manda({
    topic: "telemetry",
    cpu_percent: 23.8, ram_percent: 92.6, package_temp_c: 47.25,
  });
  bus.manda({
    topic: "agent.mesh",
    nodi: [{ id: "t2", stato: "attivo", dettaglio: "1/2 · 14 nella finestra",
             attivo: true }],
  });
}
