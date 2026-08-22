/* Il trascinamento, provato con eventi puntatore VERI — §26.9 criterio 4.
 *
 * ## Perche' l'app e non la galleria
 *
 * R82 ha mostrato che i sei test possono essere verdi mentre il giro completo
 * e' rotto: `resize -> affianca()` cancellava il ripristino, e nessun test lo
 * vedeva perche' nessuno arrivava fino alla finestra vera. E' la SECONDA volta
 * in questo progetto, dopo il CSP di PixiJS — la galleria non ne aveva uno, i
 * glifi ci giravano, e nell'app non partivano da quattro fasi.
 *
 * La regola che se ne ricava: **un ambiente di prova piu' permissivo di quello
 * reale approva codice che nel reale e' rotto.** Quindi qui si avvia
 * `app/main.js` con Electron vero, socket vero, core vero.
 *
 * ## Perche' Playwright e non un finto evento
 *
 * `element.dispatchEvent(new PointerEvent(...))` e' una simulazione a livello
 * JS: non passa da `setPointerCapture`, non genera `pointercancel`, e non
 * prova niente sul comportamento reale. `page.mouse.down/move/up` di
 * Playwright entra nella pipeline di input del browser — e' la stessa strada
 * di un mouse.
 *
 *   node scripts/prova-gesti.mjs [--scatti shots/gesti]
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

//: Il pannello su cui si lavora. `console` sta nel workspace 1, e' largo e la
//: sua testa e' una maniglia comoda.
const MODULO = "console";
const dorme = (ms) => new Promise((r) => setTimeout(r, ms));

/* ⚠️ Lo stato di partenza dev'essere NOTO.
 *
 * La prima stesura partiva da quello che aveva lasciato l'esecuzione
 * precedente: un pannello gia' agganciato, o massimizzato, o sotto un altro. I
 * risultati cambiavano fra due esecuzioni identiche — e una prova che dipende
 * dai residui della prova prima non e' una prova.
 *
 * Il layout dell'utente si mette DA PARTE e si rimette a posto alla fine: e'
 * il suo ambiente, non materiale di consumo. */
const DA_PARTE = `${LAYOUT}.prova`;
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
  /* ⚠️ SUBITO, e prima di aspettare i pannelli.
   *
   * Sotto Playwright la finestra nasce a 800x600 e il `maximize()` di
   * `main.js` non si applica. Una prova su una finestra piu' piccola di quella
   * vera sarebbe di nuovo un ambiente diverso dal reale — la lezione di R82 e
   * del CSP di PixiJS.
   *
   * E va fatto PRIMA che la scrivania componga: `armaManiglia()` e WinBox
   * chiudono sopra l'area al momento in cui la cornice nasce. Massimizzare
   * dopo produrrebbe zone d'aggancio calcolate su un'area che non esiste
   * piu' — un difetto vero (R83), ma non quello che questa prova sta
   * misurando, e sarebbe un difetto che nell'app non si presenta perche' li'
   * la finestra e' gia' grande quando i pannelli nascono. */
  await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].maximize());
  await dorme(300);
  // Non un'attesa a tempo: si aspetta che la scrivania esista e che il
  // pannello sia montato. Con un tempo si coglierebbe la composizione a meta',
  // ed e' successo due volte in questo progetto.
  /* ⚠️ IL MODULO SI APRE QUI, e prima non serviva.
     Sotto ADR-010 la scrivania apriva TUTTO all'avvio, quindi «console» era
     gia' a schermo e bastava aspettarlo. Da quando §26.6 compone una SCENA,
     all'avvio ci sono i quattro pannelli dichiarati e nient'altro: questa
     attesa restava appesa sessanta secondi su un pannello che nessuno aveva
     aperto, e la prova moriva prima di provare qualcosa.
     Il difetto non e' della prova: e' che la prova dava per scontata una
     regola che e' cambiata. Aprirlo esplicitamente e' anche piu' onesto —
     dice CHE COSA sta misurando invece di ereditarlo dalla composizione. */
  await win.waitForFunction(() => !!window.__scrivania?.scrivania, null,
                            { timeout: 60_000 });
  await win.evaluate((m) => window.__scrivania.scrivania.apri(m), MODULO);
  await win.waitForFunction(
    (m) => !!document.querySelector(`[data-modulo="${m}"] .crn-maniglia`),
    MODULO, { timeout: 60_000 });
  await win.waitForFunction(() => !!window.__layout?.persistenza, null,
                            { timeout: 60_000 });
  await dorme(1200);            // la finestra si assesta: e' li' che R82 colpiva
  return { app, win };
}

const geometria = (win, id = MODULO) => win.evaluate((m) => {
  const s = window.__scrivania.scrivania;
  const d = s.disposizione();
  // `misura()` e non `d.area`: quest'ultima porta solo larghezza e altezza,
  // che e' la forma che il core mette giu'. Per puntare a un bordo serve
  // sapere anche dove il bordo sta.
  return { pannello: d.pannelli.find((p) => p.id === m), area: s.misura() };
}, id);

/** Il gesto vero: premere, muovere in `passi`, rilasciare. */
async function trascina(win, da, a, passi = 20, msPerPasso = 15) {
  await win.mouse.move(da.x, da.y);
  await win.mouse.down();
  for (let i = 1; i <= passi; i++) {
    await win.mouse.move(da.x + ((a.x - da.x) * i) / passi,
                         da.y + ((a.y - da.y) * i) / passi);
    await dorme(msPerPasso);
  }
  await win.mouse.up();
}

async function testaDi(win, id = MODULO) {
  const b = await win.locator(`[data-modulo="${id}"] .crn-maniglia`).boundingBox();
  if (b) return b;
  // Non basta sapere che manca: serve sapere PERCHE'. Una finestra
  // minimizzata, nascosta o chiusa danno tutte `null`, e sono tre difetti
  // diversi.
  const stato = await win.evaluate((m) => {
    const w = document.querySelector(`[data-modulo="${m}"]`);
    if (!w) return { c_e: false };
    const cs = getComputedStyle(w);
    return { c_e: true, classi: w.className, display: cs.display,
             visibility: cs.visibility, rect: w.getBoundingClientRect().toJSON() };
  }, id);
  throw new Error(`testa di ${id} non afferrabile: ${JSON.stringify(stato)}`);
}

statoPulito();
process.on("exit", rimettiAPosto);

const esiti = {};

/* Ogni sezione va a fondo per conto suo.
 *
 * Con un'eccezione che sfugge si vede UN guasto per esecuzione, e ogni
 * esecuzione costa un minuto di Electron. Cosi' una sola passata da' il quadro
 * intero — compreso il caso in cui il guasto di una sezione sia la causa del
 * guasto della successiva, che e' proprio quello che si vuole vedere. */
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

/* ══ 1 e 2 — il gesto completo, e il debounce su una sequenza VERA ══════════ */

const { app, win } = await avvia();
finestraCorrente = win;
await sezione("gesto", async () => {
  // Preparazione, non oggetto della prova: il pannello va portato in cima, o
  // la pressione finirebbe su quello che gli sta sopra. Un utente lo
  // clicchera'; qui lo si chiede alla scrivania, cosi' la preparazione non
  // dipende dalla cosa che si sta misurando.
  await win.evaluate((m) => window.__scrivania.scrivania.apri(m), MODULO);
  await dorme(300);
  await win.evaluate(() => window.__layout.persistenza.azzera());
  const prima = await geometria(win);
  const partenza = await win.evaluate((m) => {
    const w = document.querySelector(`[data-modulo="${m}"]`);
    return { classi: w.className, rect: w.getBoundingClientRect().toJSON() };
  }, MODULO);
  const t = await testaDi(win);
  const da = { x: t.x + t.width / 2, y: t.y + t.height / 2 };
  const a = { x: da.x + 260, y: da.y - 180 };

  const t0 = Date.now();
  await trascina(win, da, a);
  const durata = Date.now() - t0;

  const dopoIlGesto = await geometria(win);
  await dorme(900);                       // oltre il ritardo di 500 ms
  const misura = await win.evaluate(() => ({
    scritture: window.__layout.persistenza.scritture.length,
    ultimo: window.__layout.persistenza.ultimoInvio,
  }));

  const atteso = { x: prima.pannello.x + (a.x - da.x), y: prima.pannello.y + (a.y - da.y) };
  const inviato = misura.ultimo?.pannelli?.find((p) => p.id === MODULO);

  return {
    partenza,
    durata_ms: durata,
    prima: { x: prima.pannello.x, y: prima.pannello.y },
    dopo: { x: dopoIlGesto.pannello.x, y: dopoIlGesto.pannello.y },
    atteso,
    // Tolleranza di 2 px: il puntatore si muove per interi e la presa e'
    // calcolata sul rettangolo del DOM, non sulle coordinate di WinBox.
    dove_lo_lascio: Math.abs(dopoIlGesto.pannello.x - atteso.x) <= 2 &&
                    Math.abs(dopoIlGesto.pannello.y - atteso.y) <= 2,
    scritture: misura.scritture,
    ultima_posizione_inviata: inviato ? { x: inviato.x, y: inviato.y } : null,
    inviata_e_l_ultima: !!inviato && inviato.x === dopoIlGesto.pannello.x &&
                        inviato.y === dopoIlGesto.pannello.y,
  };
});

/* ══ 3 — doppio clic: massimizza, e poi torna DOVE ERA ═════════════════════ */
/* ⚠️ PRIMA dell'aggancio, e non dopo.
 *
 * Nella prima passata veniva dopo, e il pannello ci arrivava gia' agganciato a
 * meta' schermo: «massimizza» e «era gia' largo quanto lo schermo» diventavano
 * indistinguibili, e «torna dove era» misurava il ritorno da uno stato che non
 * era quello che avevo creduto di preparare. Una prova va fatta da uno stato
 * che si conosce. */
await sezione("doppioClic", async () => {
  // Prima lo si porta in un posto riconoscibile, cosi' «torna dove era» non si
  // confonde con «torna nella cella dichiarata».
  const t0 = await testaDi(win);
  await trascina(win, { x: t0.x + t0.width / 2, y: t0.y + t0.height / 2 },
                 { x: 420, y: 330 }, 10, 10);
  await dorme(250);
  const prima = (await geometria(win)).pannello;

  /* Si fa doppio clic a SINISTRA della testa, non al suo centro.
   *
   * `locator.dblclick()` punta al centro dell'elemento, e la testa e' larga
   * quanto il pannello: quando il pannello e' massimizzato il centro sta a
   * meta' schermo, e appena il primo `pointerdown` lo rimpicciolisce quel
   * punto non e' piu' sopra la testa. Il secondo clic finirebbe su un altro
   * pannello — nella prima passata di questa prova ha premuto il ⊟ di un
   * vicino e ha minimizzato quello che stavo misurando. Un utente afferra la
   * barra dove la vede, non dove sta il suo centro geometrico. */
  const stato = () => win.evaluate((m) => {
    const w = document.querySelector(`[data-modulo="${m}"]`);
    const d = window.__scrivania.scrivania.disposizione();
    const p = d.pannelli.find((x) => x.id === m);
    const r = w.getBoundingClientRect();
    return { box: p && { x: p.x, y: p.y, w: p.larghezza, h: p.altezza,
                         max: p.massimizzato },
             dom: { x: r.x | 0, y: r.y | 0, w: r.width | 0, h: r.height | 0 },
             classi: w.className };
  }, MODULO);

  const passi = [];
  const doppioSullaTesta = async (etichetta) => {
    const t = await testaDi(win);
    passi.push({ etichetta: `${etichetta}: testa a`, x: t.x | 0, y: t.y | 0,
                 w: t.width | 0, h: t.height | 0 });
    await win.mouse.dblclick(t.x + 40, t.y + t.height / 2);
    await dorme(500);
    passi.push({ etichetta, ...(await stato()) });
  };

  passi.push({ etichetta: "prima", ...(await stato()) });
  await doppioSullaTesta("dopo il 1o doppio clic");
  const massimizzato = (await geometria(win)).pannello;
  /* ⚠️ Il rettangolo dal DOM, non da `box.width`.
   *
   * Mentre e' massimizzato WinBox tiene in `x/y/width/height` la geometria di
   * RIPRISTINO — ed e' giusto: e' quella che serve per tornare indietro, ed e'
   * quella che salviamo insieme al flag. Ma allora «ha massimizzato?» non si
   * puo' chiedere a quei numeri: si chiede a cio' che si vede. */
  const rettMax = await win.evaluate((m) =>
    document.querySelector(`[data-modulo="${m}"]`).getBoundingClientRect().toJSON(), MODULO);

  await doppioSullaTesta("dopo il 2o doppio clic");
  const tornato = (await geometria(win)).pannello;

  const { area } = await geometria(win);
  return {
    passi,
    prima: { x: prima.x, y: prima.y, larghezza: prima.larghezza },
    massimizzato: { larghezza: massimizzato.larghezza, altezza: massimizzato.altezza,
                    flag: massimizzato.massimizzato },
    tornato: { x: tornato.x, y: tornato.y, larghezza: tornato.larghezza },
    reso_massimizzato: { larghezza: Math.round(rettMax.width),
                         altezza: Math.round(rettMax.height) },
    // ≥ 95 % dell'area: WinBox massimizza dentro i propri `top/bottom`, che
    // tengono conto della barra e del dock, e non coincidono al pixel con
    // l'area che la scrivania dichiara.
    ha_massimizzato: rettMax.width >= area.larghezza * 0.95 &&
                     rettMax.height >= area.altezza * 0.95,
    torna_dove_era: Math.abs(tornato.x - prima.x) <= 2 &&
                    Math.abs(tornato.y - prima.y) <= 2 &&
                    Math.abs(tornato.larghezza - prima.larghezza) <= 2,
  };
});

/* ══ 4 — l'aggancio al bordo, come GESTO ═══════════════════════════════════ */
await sezione("aggancio", async () => {
  const { area } = await geometria(win);
  const bordi = {
    sinistra: { x: area.sinistra + 8, y: area.alto + area.altezza / 2 },
    destra: { x: area.sinistra + area.larghezza - 8, y: area.alto + area.altezza / 2 },
    alto: { x: area.sinistra + area.larghezza / 2, y: area.alto + 8 },
    basso: { x: area.sinistra + area.larghezza / 2, y: area.alto + area.altezza - 8 },
  };
  const fuori = {};
  for (const [nome, punto] of Object.entries(bordi)) {
    const t = await testaDi(win);
    await trascina(win, { x: t.x + t.width / 2, y: t.y + t.height / 2 }, punto, 12, 10);
    await dorme(250);
    const { pannello, area: a } = await geometria(win);
    const metaL = Math.round(a.larghezza / 2);
    const metaH = Math.round(a.altezza / 2);
    fuori[nome] = {
      x: pannello.x, y: pannello.y,
      larghezza: pannello.larghezza, altezza: pannello.altezza,
      area: { sinistra: a.sinistra, alto: a.alto,
              larghezza: a.larghezza, altezza: a.altezza },
      meta_attesa: { larghezza: metaL, altezza: metaH },
      // ±2 px: le meta' si arrotondano, e un'area dispari non si divide in due
      // interi uguali.
      agganciato:
        (nome === "sinistra" && Math.abs(pannello.larghezza - metaL) <= 2 &&
         Math.abs(pannello.x - a.sinistra) <= 2) ||
        (nome === "destra" && Math.abs(pannello.larghezza - (a.larghezza - metaL)) <= 2 &&
         Math.abs(pannello.x - (a.sinistra + metaL)) <= 2) ||
        (nome === "alto" && Math.abs(pannello.altezza - metaH) <= 2 &&
         Math.abs(pannello.y - a.alto) <= 2) ||
        (nome === "basso" && Math.abs(pannello.altezza - (a.altezza - metaH)) <= 2 &&
         Math.abs(pannello.y - (a.alto + metaH)) <= 2),
    };
  }
  return fuori;
});

/* ══ 6 — riadatta(): chi era dentro non si muove, chi era fuori rientra ════ */
await sezione("riadatta", async () => {
  const t = await testaDi(win);
  // Lo si porta vicino al bordo destro, ma NON agganciato: fuori dalla soglia
  // di 24 px, o il rilascio lo aggancerebbe e la prova misurerebbe altro.
  await trascina(win, { x: t.x + t.width / 2, y: t.y + t.height / 2 },
                 { x: 1400, y: 400 }, 10, 10);
  await dorme(900);

  const prima = await geometria(win);
  const tutti = (g) => g.reduce((m, p) => (m[p.id] = { x: p.x, y: p.y }, m), {});
  const primaTutti = tutti((await win.evaluate(
    () => window.__scrivania.scrivania.disposizione())).pannelli);

  if (CARTELLA) {
    mkdirSync(CARTELLA, { recursive: true });
    await win.screenshot({ path: join(CARTELLA, "riadatta-prima.png") });
  }

  // La finestra si restringe: e' il caso che `riadatta()` esiste per gestire.
  const nuova = { width: 1100, height: 700 };
  await app.evaluate(({ BrowserWindow }, d) => {
    const w = BrowserWindow.getAllWindows()[0];
    w.unmaximize(); w.setSize(d.width, d.height);
  }, nuova);
  await dorme(1200);

  const dopo = await geometria(win);
  const dopoTutti = tutti((await win.evaluate(
    () => window.__scrivania.scrivania.disposizione())).pannelli);

  if (CARTELLA) await win.screenshot({ path: join(CARTELLA, "riadatta-dopo.png") });

  const mossi = Object.keys(primaTutti).filter(
    (id) => dopoTutti[id] && (dopoTutti[id].x !== primaTutti[id].x ||
                              dopoTutti[id].y !== primaTutti[id].y));
  /* ⚠️ «Fuori» si misura sull'AREA UTILE e su TUTTI E QUATTRO i bordi, e la
     prima stesura guardava solo destra e basso, contro la larghezza della
     FINESTRA.
     Il caso che scopriva il difetto: restringendo la finestra la barra guadagna
     la propria barra di scorrimento e cresce di 4 px, quindi il bordo ALTO
     dell'area scende da 32 a 36. I pannelli posati a filo di quel bordo — nella
     scena di avvio sono due, telemetria e agenti — vengono spinti giu' di 4 px
     da `dentroArea`, che fa esattamente il proprio mestiere. Erano fuori: sopra
     il bordo nuovo. Il predicato non lo vedeva e li contava come «mossi senza
     motivo», cioe' bocciava la funzione per aver funzionato.
     E si misura sull'area e non sulla finestra perche' fra le due c'e' il
     chrome: usare la finestra vuol dire sbagliare di quanto sono alti barra e
     dock, che e' proprio l'ordine di grandezza del difetto da distinguere. */
  const A = dopo.area;
  const erano_fuori = Object.keys(primaTutti).filter(
    (id) => primaTutti[id].x + 80 > A.sinistra + A.larghezza ||
            primaTutti[id].y + 80 > A.alto + A.altezza ||
            primaTutti[id].x < A.sinistra ||
            primaTutti[id].y < A.alto);

  return {
    area_prima: prima.area, area_dopo: dopo.area,
    mossi, erano_fuori,
    // Chi si e' mosso dev'essere un sottoinsieme di chi era fuori: nessuno che
    // stava a posto e' stato toccato.
    solo_chi_era_fuori: mossi.every((id) => erano_fuori.includes(id)),
    tutti_dentro: Object.values(dopoTutti).every(
      (p) => p.x <= nuova.width - 80 && p.y <= nuova.height - 80),
  };
});

/* ══ 5 — il giro completo: trascina, CHIUDI, riapri ════════════════════════ */

const bersaglio = { x: 300, y: 260 };
await sezione("primaDellaChiusura", async () => {
  const t = await testaDi(win);
  await trascina(win, { x: t.x + t.width / 2, y: t.y + t.height / 2 }, bersaglio, 12, 10);
  await dorme(1000);
  return (await geometria(win)).pannello;
});
await app.close();
await dorme(1500);

const suDisco = JSON.parse(readFileSync(LAYOUT, "utf-8"))
  .pannelli.find((p) => p.id === MODULO) ?? null;

const secondo = await avvia();
finestraCorrente = secondo.win;
await sezione("giroCompleto", async () => {
  const dopo = (await geometria(secondo.win)).pannello;
  const ripristino = await secondo.win.evaluate(() => window.__layout.ripristino);
  return {
    prima_della_chiusura: esiti.primaDellaChiusura,
    su_disco: suDisco && { x: suDisco.x, y: suDisco.y },
    dopo_la_riapertura: { x: dopo.x, y: dopo.y },
    ripristino,
    // ±4 px: fra i due avvii l'area puo' differire di un pixel — la barra e il
    // dock si misurano dopo il caricamento dei font — e il taglio dentro l'area
    // sposta di conseguenza.
    e_dove_l_ho_lasciato: Math.abs(dopo.x - esiti.primaDellaChiusura.x) <= 4 &&
                          Math.abs(dopo.y - esiti.primaDellaChiusura.y) <= 4,
  };
});
if (CARTELLA) await secondo.win.screenshot({ path: join(CARTELLA, "riaperta.png") });
await secondo.app.close();

rimettiAPosto();
console.log(JSON.stringify(esiti));
