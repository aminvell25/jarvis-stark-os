/* Icone libere e cartelle contenitore, nell'app vera — §26.9 criteri 4 e 5.
 *
 *   4. «Un'icona portata sul fondo ci resta; riavviato il core, e' ancora li'.
 *      Verificato riavviando davvero, non simulando.»
 *   5. «Un'icona lasciata su una cartella entra; la cartella dichiara quante
 *      cose contiene.»
 *
 * E §26.5: «anche un layout di SOLE icone va rimesso» — la sezione 8. Non e'
 * un corollario del criterio 4: li' la prova apre una cartella, e una cartella
 * aperta E' un pannello, quindi il ramo senza pannelli non veniva mai preso.
 *
 * ## Passo 0 di §11.7, di nuovo
 *
 * Electron vero, core vero, puntatore di Playwright — che entra nella pipeline
 * di input del browser invece di fingere un evento in JavaScript. La regola
 * viene da R82 e dal CSP di PixiJS: **un ambiente di prova piu' permissivo di
 * quello reale approva codice che nel reale e' rotto.**
 *
 * Qui conta il doppio. Meta' di §26.5 e' fatta di cose che un test senza
 * puntatore non puo' nemmeno esprimere: che l'estrazione non scorra il nastro,
 * che l'icona in mano stia sopra i pannelli mentre li attraversa, che la
 * cartella si accenda quando ci passi sopra con qualcosa in mano.
 *
 *   node scripts/prova-icone.mjs [--scatti shots/icone]
 *
 * Stampa una riga JSON: `tests/test_layout.py` la legge e giudica.
 */

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import electronPath from "electron";
import { _electron as electron } from "playwright";

const RADICE = resolve(fileURLToPath(new URL("..", import.meta.url)));
const CARTELLA = process.argv.includes("--scatti")
  ? process.argv[process.argv.indexOf("--scatti") + 1] : null;
const LAYOUT = join(homedir(), ".local/share/jarvis-os/layout.json");
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

/* Lo stato di partenza dev'essere NOTO: il layout dell'utente si mette da
 * parte e si rimette a posto alla fine. E' il suo ambiente, non materiale di
 * consumo — e una prova che dipende dai residui di quella prima non e' una
 * prova (lezione di `prova-gesti.mjs`). */
const DA_PARTE = `${LAYOUT}.prova-icone`;
function statoPulito() {
  if (existsSync(DA_PARTE)) rmSync(DA_PARTE);
  if (existsSync(LAYOUT)) renameSync(LAYOUT, DA_PARTE);
}
function rimettiAPosto() {
  if (!existsSync(DA_PARTE)) return;
  rmSync(LAYOUT, { force: true });
  renameSync(DA_PARTE, LAYOUT);
}

function socketDelCore() {
  return execFileSync("uv", ["run", "python", "-m", "core.paths_cli", "--socket"],
                      { cwd: RADICE, encoding: "utf-8" }).trim();
}

async function avvia() {
  const app = await electron.launch({
    executablePath: electronPath,
    args: [join(RADICE, "app", "main.js"), "--socket", socketDelCore()],
    cwd: RADICE,
  });
  const win = await app.firstWindow();
  // Subito, e prima di aspettare la scrivania: sotto Playwright la finestra
  // nasce a 800x600 e il `maximize()` di `main.js` non si applica.
  await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
  await dorme(300);
  await win.waitForFunction(() => !!document.querySelector(".cat__tessera"),
                            null, { timeout: 60_000 });
  await win.waitForFunction(() => !!window.__scrivania?.icone, null,
                            { timeout: 60_000 });
  await dorme(1500);          // la finestra si assesta: e' li' che R82 colpiva
  return { app, win };
}

/** Il gesto vero: premere, muovere a passi, rilasciare. */
async function trascina(win, da, a, { passi = 20, ms = 15, aMeta } = {}) {
  await win.mouse.move(da.x, da.y);
  await win.mouse.down();
  for (let i = 1; i <= passi; i++) {
    await win.mouse.move(da.x + ((a.x - da.x) * i) / passi,
                         da.y + ((a.y - da.y) * i) / passi);
    await dorme(ms);
    if (aMeta && i === passi - 1) await aMeta();
  }
  await win.mouse.up();
}

/**
 * Un punto di FONDO vero: dove il clic non finisce su un pannello o sulla
 * cornice. Si cerca invece di sceglierlo a mano, perche' quanto fondo resti
 * libero dipende dalla cascata di R88 e dalla dimensione dello schermo — e un
 * punto scritto qui sarebbe giusto su questa macchina e sbagliato altrove.
 *
 * ⚠️ R97, e la sua chiusura. Con la CASCATA — tredici pannelli aperti tutti
 * insieme, ognuno sulla propria piastrellatura — la scansione non trovava un
 * solo punto scoperto: il fondo esisteva solo sotto ai pannelli, e si
 * raggiungeva con `Alt+H`.
 *
 * Con la scena di avvio di §26.6 il fondo torna: cinque pannelli composti a
 * mano lasciano scoperti il quadrante in basso a sinistra e le fasce ai lati
 * del catalogo — che e' esattamente dove il riferimento mette le cartelle
 * manila. La prova continua a passare da `Alt+H` per la parte che vuole
 * spazio certo, ma **misura entrambi i casi** e li dichiara: se un domani la
 * composizione tornasse a coprire tutto, si vedrebbe da questo numero.
 */
function fondoLibero(win, evita = []) {
  return win.evaluate((giaPresi) => {
    const CORNICE = ".winbox, .brr, .dck, .cat, .ico, .ico-cart, .ico-menu";
    const lontano = (x, y) =>
      giaPresi.every((p) => Math.hypot(p.x - x, p.y - y) > 140);
    // Dal basso a destra verso l'alto: e' dove la cascata lascia scoperto.
    for (let y = window.innerHeight - 120; y > 120; y -= 40) {
      for (let x = window.innerWidth - 80; x > 80; x -= 40) {
        const el = document.elementFromPoint(x, y);
        if (el && !el.closest(CORNICE) && lontano(x, y)) return { x, y };
      }
    }
    return null;
  }, evita);
}

const fondo = (win) => win.evaluate(() => window.__scrivania.icone.stato());

statoPulito();
process.on("exit", rimettiAPosto);

const esiti = {};
let finestraCorrente = null;

async function sezione(nome, f) {
  try { esiti[nome] = await f(); }
  catch (e) { esiti[nome] = { errore: String(e).slice(0, 400) }; }
  if (CARTELLA && finestraCorrente) {
    mkdirSync(CARTELLA, { recursive: true });
    try { await finestraCorrente.screenshot({ path: join(CARTELLA, `${nome}.png`) }); }
    catch { /* la finestra puo' essere gia' chiusa */ }
  }
}

const { app, win } = await avvia();
finestraCorrente = win;

/* ══ 1 — trascinare fuori, e l'indice che NON perde la voce ════════════════ */

let posto = null;
await sezione("estrazione", async () => {
  const prima = await win.evaluate(() => ({
    tessere: document.querySelectorAll(".cat__tessera").length,
    scorrimento: window.__scrivania && Math.round(
      new DOMMatrix(getComputedStyle(document.querySelector(".cat__nastro"))
        .transform).m41),
  }));
  const tessera = win.locator(".cat__tessera").first();
  const voce = await tessera.getAttribute("data-voce");
  const b = await tessera.boundingBox();
  /* R97 — si lascia SOPRA un pannello, di proposito: e' cio' che succede a chi
   * prova il gesto per la prima volta su una scrivania piena. L'icona deve
   * finire sul fondo lo stesso, sotto quel pannello. L'unico posto in cui non
   * deve finire e' il catalogo, che significa «annulla». */
  posto = await win.evaluate(() => {
    const cat = document.querySelector(".cat").getBoundingClientRect();
    const p = { x: Math.round(window.innerWidth * 0.72),
                y: Math.round(window.innerHeight * 0.3) };
    if (p.x >= cat.left && p.x <= cat.right && p.y >= cat.top && p.y <= cat.bottom)
      p.y = Math.round(cat.top / 2);
    return p;
  });

  let inMano = null;
  await trascina(win,
    { x: b.x + b.width / 2, y: b.y + b.height / 2 }, posto,
    { passi: 22, ms: 14, aMeta: async () => {
      // Cio' che si ha in mano dev'essere VISIBILE mentre attraversa i
      // pannelli: al proprio piano sparirebbe dietro il primo che incontra.
      inMano = await win.evaluate(() => {
        const m = document.querySelector(".ico-mano");
        if (!m || m.hidden) return null;
        const cs = getComputedStyle(m);
        const wb = document.querySelector(".winbox");
        return { z: Number(cs.zIndex), esito: m.dataset.esito,
                 zPannello: wb ? Number(getComputedStyle(wb).zIndex) : null };
      });
    } });
  await dorme(400);

  const dopo = await win.evaluate(() => ({
    tessere: document.querySelectorAll(".cat__tessera").length,
    scorrimento: Math.round(new DOMMatrix(
      getComputedStyle(document.querySelector(".cat__nastro")).transform).m41),
    icone: document.querySelectorAll(".ico").length,
  }));
  const stato = await fondo(win);
  const icona = stato.icone.find((i) => i.nome === voce) ?? null;
  const sepolta = await win.evaluate(() => {
    const e = document.querySelector(".ico");
    const r = e.getBoundingClientRect();
    const sopra = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return { coperta_da: sopra?.closest(".winbox") ? "un pannello" : "niente" };
  });

  return {
    voce,
    icona,
    // R97: lasciata sopra un pannello, l'icona ESISTE e sta sotto di esso.
    sepolta,
    // §26.5: «L'icona nel catalogo NON sparisce: il catalogo e' l'indice.»
    indice_intatto: dopo.tessere === prima.tessere,
    // R95: il gesto verticale non deve aver scorso il nastro.
    nastro_fermo: dopo.scorrimento === prima.scorrimento,
    in_mano: inMano,
    sopra_i_pannelli: !!inMano && inMano.z > (inMano.zPannello ?? 0),
    a_schermo: dopo.icone === 1,
    dove_lho_lasciata: !!icona &&
      Math.abs(icona.x - posto.x) <= 8 && Math.abs(icona.y - posto.y) <= 8,
  };
});

/* ══ 2 — l'icona sta SOTTO i pannelli ══════════════════════════════════════ */

await sezione("sottoIPannelli", async () => {
  return win.evaluate(() => {
    const strato = document.querySelector(".ico-fondo");
    const wb = [...document.querySelectorAll(".winbox")]
      .filter((w) => getComputedStyle(w).display !== "none");
    const zIcone = Number(getComputedStyle(strato).zIndex);
    const zPannelli = wb.map((w) => Number(getComputedStyle(w).zIndex));
    // La prova che conta non e' il numero: e' che un punto DENTRO un pannello
    // risponda «pannello» e non «icona».
    const r = wb[0].getBoundingClientRect();
    const sopra = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return {
      z_icone: zIcone,
      z_pannello_minimo: Math.min(...zPannelli),
      sotto: zIcone < Math.min(...zPannelli),
      // Lo strato non ruba i clic: un punto qualunque del fondo non risponde
      // «strato delle icone».
      strato_trasparente: getComputedStyle(strato).pointerEvents === "none",
      dentro_un_pannello_risponde: sopra?.closest(".winbox") ? "pannello"
        : sopra?.closest(".ico-fondo") ? "icone" : "altro",
    };
  });
});

/* ══ 3 — spostarla sul fondo ═══════════════════════════════════════════════
 *
 * R97: da qui in poi serve fondo scoperto, e sulla scrivania piena non ce n'e'.
 * Si usa `Alt+H` — «nascondi tutto», §13 — che e' come ci arriva un utente.
 * Il catalogo NON si nasconde: e' cornice, non un pannello, e serve ancora. */

await sezione("scoprireIlFondo", async () => {
  const prima = await fondoLibero(win);
  await win.evaluate(() => window.__scrivania.scrivania.nascondiTutto());
  await dorme(500);
  const dopo = await fondoLibero(win);
  return {
    con_i_pannelli: prima, con_alt_h: dopo,
    // La misura di R97, dichiarata invece che dedotta.
    fondo_scoperto_a_scrivania_piena: prima !== null,
    catalogo_ancora_li: await win.evaluate(() => !!document.querySelector(".cat")),
  };
});

await sezione("spostamento", async () => {
  const b = await win.locator(".ico").first().boundingBox();
  const meta = await fondoLibero(win, [posto]);
  if (!meta) throw new Error("nessun secondo punto di fondo libero");
  await trascina(win, { x: b.x + b.width / 2, y: b.y + b.height / 2 }, meta,
                 { passi: 16, ms: 12 });
  await dorme(400);
  const stato = await fondo(win);
  const i = stato.icone[0];
  return {
    verso: meta, icona: { x: i.x, y: i.y },
    // Il punto afferrato resta sotto il dito: si confronta lo SCARTO fra il
    // punto preso e l'angolo, non l'angolo col puntatore.
    e_dove_lho_lasciata:
      Math.abs(i.x - (meta.x - (b.x + b.width / 2 - b.x))) <= 12 &&
      Math.abs(i.y - (meta.y - (b.y + b.height / 2 - b.y))) <= 12,
  };
});

/* ══ 4 — la cartella contenitore ═══════════════════════════════════════════ */

await sezione("cartella", async () => {
  // Il menu contestuale sul fondo: e' la risposta a «chi crea una cartella?»
  // (R93), e §26.5 lo nomina gia' per togliere un'icona.
  const dove = await fondoLibero(win, [posto, esiti.spostamento?.verso].filter(Boolean));
  if (!dove) throw new Error("nessun punto di fondo libero per la cartella");
  await win.mouse.click(dove.x, dove.y, { button: "right" });
  await dorme(250);
  const menu = await win.evaluate(() => {
    const m = document.querySelector(".ico-menu");
    return { visibile: !!m && !m.hidden,
             voci: [...m.querySelectorAll(".ico-menu__voce")].map((b) => b.textContent) };
  });
  await win.locator('.ico-menu__voce:has-text("nuova cartella")').click();
  await dorme(300);

  const nata = await fondo(win);

  // Adesso il gesto di §26.9 punto 5: l'icona lasciata SOPRA la cartella.
  const ico = await win.locator(".ico").first().boundingBox();
  const cart = await win.locator(".ico-cart").first().boundingBox();
  let acceso = null;
  await trascina(win,
    { x: ico.x + ico.width / 2, y: ico.y + ico.height / 2 },
    { x: cart.x + cart.width / 2, y: cart.y + cart.height / 2 },
    { passi: 18, ms: 14, aMeta: async () => {
      // §26.5: «La cartella si illumina a --manila piu' chiaro mentre il
      // puntatore e' sopra.» Si guarda il colore CALCOLATO, non la classe.
      acceso = await win.evaluate(() => {
        const c = document.querySelector(".ico-cart");
        const corpo = c.querySelector(".ico-cart__corpo");
        return { sopra: "sopra" in c.dataset,
                 fondo: getComputedStyle(corpo).backgroundColor,
                 esito: document.querySelector(".ico-mano")?.dataset.esito };
      });
    } });
  await dorme(400);

  /* ⚠️ Il puntatore va portato VIA prima di misurare il colore a riposo.
   * La prima stesura misurava subito dopo il rilascio, col mouse ancora sulla
   * cartella: `:hover` era attivo e il colore «a riposo» risultava identico a
   * quello acceso. Il difetto era nella misura, non nel CSS — ma per un giro
   * ha detto che la cartella non si illumina. */
  await win.mouse.move(20, 20);
  await dorme(300);
  const spento = await win.evaluate(() => getComputedStyle(
    document.querySelector(".ico-cart__corpo")).backgroundColor);
  const stato = await fondo(win);
  const dichiarato = await win.evaluate(() =>
    document.querySelector(".ico-cart__conteggio").textContent);

  return {
    menu,
    cartella_nata: nata.cartelle.length === 1 && nata.cartelle[0],
    acceso_mentre_ci_passo: acceso,
    fondo_a_riposo: spento,
    si_illumina: !!acceso && acceso.sopra && acceso.fondo !== spento,
    dentro: stato.icone.filter((i) => i.dentro).map((i) => i.nome),
    // §26.9 punto 5: «la cartella dichiara quante cose contiene».
    conteggio_dichiarato: dichiarato,
    /* …e l'icona che e' entrata non e' piu' sul fondo.
     *
     * ⚠️ SI CONTA PER IDENTITA', non in totale, e la prima stesura contava in
     * totale. Funzionava finche' sul fondo c'era una sola icona — quella
     * estratta dal catalogo. Da quando §26.5 semina le cartelle manila dalle
     * sottocartelle VERE della workspace, sul fondo ce n'e' almeno un'altra, e
     * il conteggio totale non tornera' mai a zero: la prova bocciava «e'
     * entrata E rimasta fuori» mentre l'icona era regolarmente entrata e
     * quella rimasta era un'altra.
     * La domanda giusta non e' «quante icone ci sono», e' «quella la' e'
     * ancora qui?». */
    sparita_dal_fondo: await win.evaluate((nomi) =>
      [...document.querySelectorAll(".ico")]
        .filter((e) => !e.hidden && nomi.includes(e.dataset.nome)).length,
      stato.icone.filter((i) => i.dentro).map((i) => i.nome)),
  };
});

/* ══ 5 — la cartella si apre come PANNELLO, con l'anatomia di §10.2 ════════ */

await sezione("aperturaCartella", async () => {
  const c = await win.locator(".ico-cart").first().boundingBox();
  await win.mouse.dblclick(c.x + c.width / 2, c.y + c.height / 2);
  await dorme(700);
  return win.evaluate(() => {
    const p = document.querySelector(".pnl-cart");
    if (!p) return { aperto: false };
    const finestra = p.closest(".winbox");
    return {
      aperto: true,
      // Un PANNELLO del sistema, non una finestra a parte: sta dentro WinBox,
      // e la cornice di §13 gli ha messo i tre controlli veri.
      dentro_winbox: !!finestra,
      modulo: finestra?.dataset.modulo ?? null,
      controlli: [...p.querySelectorAll(".crn-ctrl")].map((b) => b.dataset.ctrl),
      maniglia: !!p.querySelector(".crn-maniglia"),
      // Le cinque parti di §10.2.
      etichetta: p.querySelector(".pnl-cart__etichetta")?.textContent,
      conteggio: p.querySelector(".pnl-cart__conteggio")?.textContent,
      id: p.querySelector(".pnl-cart__id")?.textContent,
      piede: p.querySelector(".pnl-cart__piede")?.textContent.trim(),
      righe: [...p.querySelectorAll(".pnl-cart__riga")]
        .map((r) => r.dataset.nome),
      // La geometria del pannello-cartella entra nella disposizione salvata,
      // come quella di ogni altro pannello.
      nella_disposizione: window.__scrivania.scrivania.disposizione()
        .pannelli.some((x) => x.id === finestra?.dataset.modulo),
    };
  });
});

/* ══ 6 — togliere: trascinare sul catalogo ═════════════════════════════════ */

await sezione("rimozione", async () => {
  /* Serve una seconda icona sul fondo: la prima e' dentro la cartella.
   *
   * ⚠️ Si tira SOPRA la fascia, non sotto. Il primo giro la portava in basso a
   * destra, e non nasceva niente: il gesto usciva dal nastro solo all'ultimo
   * passo, e cosa succeda in quel caso limite e' una domanda diversa da quella
   * che questa sezione sta ponendo. Il caso limite resta un «non verificato»
   * dichiarato, invece di mescolarsi con la rimozione. */
  const dove = await win.evaluate(() => ({
    x: Math.round(window.innerWidth * 0.3),
    y: Math.round(window.innerHeight * 0.35),
  }));
  const tessera = win.locator(".cat__tessera").nth(1);
  const voce = await tessera.getAttribute("data-voce");
  const b = await tessera.boundingBox();
  await trascina(win, { x: b.x + b.width / 2, y: b.y + b.height / 2 }, dove,
                 { passi: 20, ms: 14 });
  await dorme(400);
  const prima = (await fondo(win)).icone.length;

  const ico = await win.locator(`.ico[data-nome="${voce}"]`).boundingBox();
  const cat = await win.locator(".cat").boundingBox();
  let avvisa = null;
  await trascina(win,
    { x: ico.x + ico.width / 2, y: ico.y + ico.height / 2 },
    { x: cat.x + cat.width / 2, y: cat.y + cat.height / 2 },
    { passi: 18, ms: 14, aMeta: async () => {
      avvisa = await win.evaluate(() => ({
        esito: document.querySelector(".ico-mano")?.dataset.esito,
        corpo: document.body.dataset.trascino,
        bordoCatalogo: getComputedStyle(document.querySelector(".cat")).borderTopColor,
      }));
    } });
  await dorme(400);
  const dopo = (await fondo(win)).icone.length;
  return { voce, prima, dopo, avvisa, tolta: dopo === prima - 1 };
});

/**
 * Le stesse icone, negli stessi posti. Serve a DUE riavvii — quello di §26.9
 * punto 4 e quello di §26.5 — e per questo sta qui invece che dentro una
 * sezione.
 *
 * ⚠️ La tolleranza di 4 px non e' generosita': il core fa passare le
 * coordinate da `adatta()` contro l'area dichiarata, e uno scarto di qualche
 * pixel e' il taglio che funziona, non un errore.
 */
const uguali = (a, b) => a.length === b.length && a.every((x, i) =>
  x.tipo === b[i].tipo && x.nome === b[i].nome &&
  Math.abs(x.x - b[i].x) <= 4 && Math.abs(x.y - b[i].y) <= 4 &&
  x.dentro === b[i].dentro);

/* ══ 7 — il riavvio VERO ═══════════════════════════════════════════════════ */

const primaDellaChiusura = await fondo(win);
await app.close();
await dorme(1800);

const suDisco = existsSync(LAYOUT)
  ? JSON.parse(readFileSync(LAYOUT, "utf-8")) : null;

const secondo = await avvia();
finestraCorrente = secondo.win;
await sezione("riavvio", async () => {
  const dopo = await fondo(secondo.win);
  const ripristino = await secondo.win.evaluate(() => window.__layout.ripristino);
  const aSchermo = await secondo.win.evaluate(() => ({
    icone: [...document.querySelectorAll(".ico")].filter((e) => !e.hidden).length,
    cartelle: document.querySelectorAll(".ico-cart").length,
    conteggio: document.querySelector(".ico-cart__conteggio")?.textContent ?? null,
  }));
  return {
    prima_della_chiusura: primaDellaChiusura,
    su_disco: suDisco && { icone: suDisco.icone, cartelle: suDisco.cartelle },
    dopo_la_riapertura: dopo,
    a_schermo: aSchermo,
    ripristino,
    icone_uguali: uguali(primaDellaChiusura.icone, dopo.icone),
    cartelle_uguali: primaDellaChiusura.cartelle.length === dopo.cartelle.length &&
      primaDellaChiusura.cartelle.every((c, i) =>
        c.id === dopo.cartelle[i].id && c.etichetta === dopo.cartelle[i].etichetta),
    // §26.9 punto 4, la parte che conta: l'icona e' ANCORA li'.
    e_ancora_li: uguali(primaDellaChiusura.icone, dopo.icone) &&
                 aSchermo.cartelle === primaDellaChiusura.cartelle.length,
  };
});

if (CARTELLA) {
  mkdirSync(CARTELLA, { recursive: true });
  await secondo.win.screenshot({ path: join(CARTELLA, "riaperta.png") });
}

/* ══ 8 — §26.5: un layout di SOLE icone si rimette ═══════════════════════ */

/* ⚠️ Perche' la sezione 7 NON copre §26.5, e questa si'.
 *
 * `ui/src/app.js` decide il ripristino con
 * `(layout?.pannelli?.length ?? 0) + suoFondo`, e il secondo termine e' li'
 * perche' una scrivania di sole icone non riparta vuota. Nella sezione 7 quel
 * termine non serve MAI: la prova apre una cartella, e una cartella aperta E'
 * un pannello — misurato a HEAD, `riavvio.ripristino.ricevuti: 7`. La guardia
 * si attraversa sempre dai pannelli, e togliere `+ suoFondo` lascerebbe la
 * sezione 7 verde. Il ramo `pannelli == 0` non era mai stato preso.
 *
 * ⚠️ **Chi scrive il layout quando i pannelli si chiudono.** Leggendo il
 * codice sembra nessuno: `chiudi()` fa `box.close()`, e `onclose` chiama
 * `suChiusura()` e `annuncia()` — che avvisa gli OSSERVATORI, non la
 * persistenza. La prima stesura di questa sezione aggiungeva percio' un gesto
 * sul fondo per far scattare la scrittura. **La bocciatura lo ha smentito**:
 * togliendo il gesto, su disco arriva `pannelli: []` lo stesso.
 *
 * Percio' il gesto e' stato tolto — un passo che non porta carico e' un passo
 * che mente — e al suo posto la sezione MISURA chi scrive: chiude prima i
 * moduli, poi la cartella, e registra `persistenza.scritture` dopo ognuna
 * delle due. E' quel numero, non un ragionamento, a dire da dove viene la
 * scrittura con zero pannelli dentro.
 */

//: `ui/src/desk/layout.js`: il debounce del salvataggio. Ripetuto qui perche'
//: l'attesa dev'essere OLTRE quel numero, e un'attesa che non dica contro cosa
//: aspetta e' un numero magico.
const RITARDO_MS = 500;

/* Si chiude in DUE tempi — prima i moduli, poi la cartella — perche' la
 * domanda «chi scrive?» ha una risposta diversa nei due casi, e una chiusura
 * sola le confonderebbe. `azzera()` esiste apposta: una prova misura un gesto,
 * non tutta la sessione. */
const chiusuraModuli = await secondo.win.evaluate(() => {
  const s = window.__scrivania.scrivania;
  window.__layout.persistenza.azzera();
  const chiesti = [...s.stato().aperti];
  const cartelle = chiesti.filter((id) => id.startsWith("cartella."));
  for (const id of chiesti) if (!cartelle.includes(id)) s.chiudi(id);
  return { chiesti, cartelle, restano: s.stato().aperti };
});
await dorme(RITARDO_MS + 400);
const scrittureDeiModuli = await secondo.win.evaluate(
  () => window.__layout.persistenza.scritture);

const chiusura = await secondo.win.evaluate(() => {
  const s = window.__scrivania.scrivania;
  for (const id of [...s.stato().aperti]) s.chiudi(id);
  return { restano: s.stato().aperti };
});
await dorme(RITARDO_MS + 400);
const scritture = await secondo.win.evaluate(
  () => window.__layout.persistenza.scritture);

const primaDelTerzo = await fondo(secondo.win);
const fondoSuDisco = existsSync(LAYOUT)
  ? JSON.parse(readFileSync(LAYOUT, "utf-8")) : null;

await secondo.app.close();
await dorme(1800);

const terzo = await avvia();
finestraCorrente = terzo.win;
await sezione("soloIlFondo", async () => {
  const dopo = await fondo(terzo.win);
  // `?? null`: sotto la bocciatura di §26.5 la guardia torna indietro e
  // `ripristino` non viene MAI scritto. Senza questo, la chiave sparirebbe dal
  // JSON e la prova cadrebbe con un KeyError invece che con la sua asserzione.
  const ripristino = await terzo.win.evaluate(
    () => window.__layout.ripristino ?? null);
  const aSchermo = await terzo.win.evaluate(() => ({
    icone: [...document.querySelectorAll(".ico")].filter((e) => !e.hidden).length,
    cartelle: document.querySelectorAll(".ico-cart").length,
  }));
  return {
    chiusura: {
      ...chiusuraModuli, ...chiusura,
      // Le due misure che dicono CHI scrive. Non un commento: un numero.
      scritture_dei_moduli: scrittureDeiModuli,
      scritture,
    },
    su_disco: fondoSuDisco && {
      // `pannelli` sta QUI e non nella sezione 7: e' il campo che dimostra che
      // il caso e' stato prodotto davvero, non descritto.
      pannelli: fondoSuDisco.pannelli,
      icone: fondoSuDisco.icone,
      cartelle: fondoSuDisco.cartelle,
    },
    prima_della_chiusura: primaDelTerzo,
    dopo_la_riapertura: dopo,
    a_schermo: aSchermo,
    ripristino,
    icone_uguali: uguali(primaDelTerzo.icone, dopo.icone),
  };
});

await terzo.app.close();

rimettiAPosto();
console.log(JSON.stringify(esiti));
