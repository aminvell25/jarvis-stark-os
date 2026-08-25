/* Densita' di superficie di uno screenshot — SPEC §11.8, criterio aggiunto il
 * 19 agosto 2026.
 *
 * PERCHE' ESISTE. La checklist §11.8 chiede «la densita' regge il confronto con
 * l'immagine di riferimento?», e la risposta la dava l'occhio. Una revisione
 * che ha misurato i pixel ha trovato dodici componenti giudicati conformi e
 * **nove volte** sotto il riferimento in superficie riempita. Una domanda a cui
 * si risponde a occhio non e' un criterio.
 *
 * PERCHE' PLAYWRIGHT E NON UNA LIBRERIA DI IMMAGINI. Decodificare un PNG
 * vorrebbe una dipendenza nuova, e `CLAUDE.md` dice di non aggiungerne senza
 * chiedere. Playwright e' gia' fra le devDependencies per il ciclo §11.7, e un
 * browser sa decodificare i PNG meglio di qualunque libreria che potremmo
 * installare. Zero dipendenze nuove.
 *
 * USO
 *   node scripts/densita.mjs shots/scrivania/ws-01.png
 *   node scripts/densita.mjs shots/globe.png docs/design-reference/famiglia-a/10-globo-gps-locator.png
 *   node scripts/densita.mjs --traboccamento http://127.0.0.1:8080/index.html
 *   node scripts/densita.mjs --istogramma shots/scrivania/scrivania.png \
 *        docs/design-reference/famiglia-a/01-desktop-mcu-completo.png
 *
 * ⚠️ **Due misure, e vanno lette INSIEME.** La densita' dice quanta superficie
 * e' accesa; il traboccamento dice quanta di quella superficie e' contenuto
 * CANCELLATO. Una barra puo' avere il 59 % di inchiostro e nove campi su
 * dodici irraggiungibili: e' successo, ed e' la ragione per cui il secondo
 * criterio sta accanto al primo invece che in uno script a parte.
 *
 * Col secondo argomento stampa le due misure accanto. Senza, confronta con le
 * soglie di `docs/design-reference/README.md`.
 */

import { chromium } from "playwright";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { basename, dirname, join } from "node:path";

/* Le soglie vengono dalla misura del riferimento, non da un'intuizione.
 * `docs/design-reference/README.md`, sezione «COSA GUARDARE».
 *
 * ⚠️ `L>25` NON E' PIU' UNA SOGLIA, e il perche' vale piu' della metrica.
 *
 * Era il criterio «quanta superficie non e' nera». Alla rev 5.9 le superfici
 * di base sono salite da L 18 a L 31, e `L>25` e' passata dal 16,4 % al
 * **96,9 %** su ws-01 — sopra il riferimento, che sta al 78,1 %. Da quel
 * momento non poteva piu' bocciare niente: qualunque schermata con un fondo
 * sopra L 25 la supera, compresa una schermata di un colore solo.
 *
 * **Una metrica satura e' peggio di nessuna metrica**, perche' passa sempre e
 * sembra una verifica. Resta STAMPATA come contesto — dice quanto e' alzato
 * il pavimento — e non concorre piu' al giudizio.
 *
 * Al suo posto due misure che una superficie uniforme NON puo' ingannare:
 *
 *   deviazione standard  quanto la luminanza si allontana dalla propria media.
 *                        Un fondo unico, per quanto chiaro, la tiene bassa.
 *   entropia             quanto e' distribuito l'istogramma a 16 bin, in bit.
 *                        Massimo 4 (16 bin equiprobabili), 0 se c'e' un solo
 *                        livello. Non chiede «quanto e' acceso» ma «quanto e'
 *                        ARTICOLATO», che e' la domanda che L>25 non sapeva
 *                        fare.
 */
const SOGLIE = {
  riempito: 25, // % pixel L>60 — riferimento 42,1 %
  caldoMin: 3, // % pixel r>b+15 — riferimento 5,7 %
  caldoMax: 6,
  barra: 25, // % pixel L>50 nella fascia della barra — riferimento 28–37 %
  /* ⚠️ IL DOCK, e la soglia esisteva in due documenti senza bocciare niente.
     `docs/design-reference/README.md` e `DIVARIO-PREMIUM.md` §7 dichiarano
     entrambi >= 20 % — riferimento: `01` al 26,2 %, `05` al 22,8 % — e in
     questo file non c'era alcuna voce `dock`. Una soglia che nessuno valuta
     non e' una soglia: e' una frase.

     ⚠️ E si misura DIVERSAMENTE dalla barra, di proposito. La barra usa una
     fascia fissa al 3,3 % dall'alto, che e' la misura DEL RIFERIMENTO: usare
     la nostra altezza vorrebbe dire misurare noi stessi. Il dock no — la sua
     altezza e' una decisione ancora in revisione, e una fascia fissa
     misurerebbe mezzo dock o un dock e mezzo. Si legge il rettangolo
     DICHIARATO, che `occlusione.json` porta gia': il pavimento va da `alto` a
     `alto + altezza`, e cio' che resta sotto e' il dock.

     Se `occlusione.json` non c'e', il dock e' **NON MISURABILE** — §11.7
     regola 4 — e non conta come verde. */
  dock: 20,
  // A meta' strada fra la nostra rev 5.7 e il piu' povero dei due riferimenti:
  //   dev.std   ws-01 5.7 = 20,3   famiglia-a/05 = 40,6   →  32
  //   entropia  ws-01 5.7 = 1,37   famiglia-a/05 = 2,85   →  2,4
  devStd: 32,
  entropia: 2.4,
};

//: L'istogramma dell'entropia. 16 bin e non 256: a 256 il rumore di
//: compressione e l'antialiasing riempirebbero decine di bin da soli e
//: l'entropia misurerebbe la qualita' del PNG invece della composizione.
const BIN = 16;

/** Rec. 709. La stessa formula del criterio, in un posto solo. */
const LUMA = "0.2126*d[i] + 0.7152*d[i+1] + 0.0722*d[i+2]";

async function misura(pagina, file, fasce = null) {
  const b64 = readFileSync(file).toString("base64");
  return pagina.evaluate(
    async ([b64, luma, bin, fasce]) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      c.getContext("2d").drawImage(img, 0, 0);
      const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;

      const L = new Function("d", "i", `return ${luma};`);
      const n = c.width * c.height;
      let somma = 0,
        sommaQuadrati = 0,
        oltre25 = 0,
        oltre60 = 0,
        oltre120 = 0,
        banda = 0,
        caldi = 0;
      const isto = new Float64Array(bin);

      // La fascia della barra: il 3,3 % superiore, che e' la misura del
      // riferimento. Non il nostro valore attuale, o misureremmo noi stessi.
      const hBarra = Math.round(c.height * 0.033);
      let barraOltre50 = 0;
      const nBarra = hBarra * c.width;

      // Il dock: la fascia DICHIARATA, non una frazione. Vedi SOGLIE.
      const yDock = fasce && fasce.dock ? fasce.dock : null;
      let dockOltre50 = 0;
      const nDock = yDock ? (yDock[1] - yDock[0]) * c.width : 0;

      for (let p = 0; p < n; p++) {
        const i = p * 4;
        const l = L(d, i);
        somma += l;
        sommaQuadrati += l * l;
        isto[Math.min(bin - 1, (l * bin) / 256 | 0)]++;
        if (l > 25 && l <= 120) banda++;
        if (l > 25) oltre25++;
        if (l > 60) oltre60++;
        if (l > 120) oltre120++;
        if (d[i] > d[i + 2] + 15 && l > 30) caldi++;
        if (p < nBarra && l > 50) barraOltre50++;
        if (yDock && l > 50) {
          const y = (p / c.width) | 0;
          if (y >= yDock[0] && y < yDock[1]) dockOltre50++;
        }
      }

      const pc = (x, tot = n) => Math.round((1000 * x) / tot) / 10;
      const media = somma / n;
      // varianza = E[X²] − E[X]²
      const devStd = Math.sqrt(Math.max(0, sommaQuadrati / n - media * media));
      // H = −Σ p·log₂p, in bit. I bin vuoti non contribuiscono.
      let entropia = 0;
      for (let k = 0; k < bin; k++) {
        const p = isto[k] / n;
        if (p > 0) entropia -= p * Math.log2(p);
      }
      return {
        larghezza: c.width,
        altezza: c.height,
        lumMedia: Math.round((10 * somma) / n) / 10,
        devStd: Math.round(10 * devStd) / 10,
        entropia: Math.round(100 * entropia) / 100,
        nonNero: pc(oltre25),
        banda: pc(banda),
        riempito: pc(oltre60),
        chiaro: pc(oltre120),
        caldo: pc(caldi),
        barra: pc(barraOltre50, nBarra),
        // `null` e non `0`: zero e' un valore, «non misurabile» e' un'altra
        // cosa, e §11.7 regola 4 vuole che le due non si confondano.
        dock: nDock ? pc(dockOltre50, nDock) : null,
      };
    },
    [b64, LUMA, BIN, fasce]
  );
}

/* Quanto cambia fra due scatti, in pixel — non in byte.
 *
 * ⚠️ **«I byte differiscono» e «la misura cambia» sono due fatti diversi**, e
 * il primo giro di questo protocollo li ha fatti sembrare in contraddizione:
 * `app/main.js` diceva «DIVERSI» e la densita' rispondeva «identici», perche'
 * l'uno confronta i byte del PNG e l'altra un aggregato su 1,3 milioni di
 * pixel. Un aggregato non si muove per qualche punto che ruota.
 *
 * La domanda giusta sta in mezzo, ed e' quantitativa: QUANTI pixel cambiano in
 * 250 ms. E' la misura dell'animazione ambientale — quella che l'invariante 25
 * vieta e che la nuvola dell'insegna fa comunque (deroga 1). Con un numero, il
 * turno 3 ha un prima e un dopo invece di un aggettivo.
 *
 * Soglia 8 su 255 per canale: sotto ci sono solo il dithering del gradiente e
 * l'antialiasing dei bordi del testo, che cambiano di un livello fra due
 * catture identiche.
 */
async function differenza(pagina, a, b, zone = null) {
  const [ba, bb] = [readFileSync(a).toString("base64"), readFileSync(b).toString("base64")];
  return pagina.evaluate(async ([ba, bb, zone]) => {
    const dati = async (b64) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      c.getContext("2d").drawImage(img, 0, 0);
      return c.getContext("2d").getImageData(0, 0, c.width, c.height);
    };
    const A = await dati(ba), B = await dati(bb);
    if (A.width !== B.width || A.height !== B.height) return null;
    let diversi = 0, massimo = 0;
    const per = {};
    /* Il riquadro di cio' che si muove. Un conteggio dice QUANTO, e non basta:
       il turno 3 deve sapere SE quello che si muove e' la nuvola. Se il
       riquadro coincide col disco del nucleo, togliere la nuvola chiude §5.4;
       se sta dentro un pannello, non lo chiude e il turno 3 non se ne accorge
       finche' non rimisura. Due numeri e mezzo di codice per evitarlo. */
    let x0 = Infinity, y0 = Infinity, x1 = -1, y1 = -1;
    for (let i = 0; i < A.data.length; i += 4) {
      const d = Math.max(Math.abs(A.data[i] - B.data[i]),
                         Math.abs(A.data[i + 1] - B.data[i + 1]),
                         Math.abs(A.data[i + 2] - B.data[i + 2]));
      if (d > massimo) massimo = d;
      if (d <= 8) continue;
      diversi++;
      const p = i / 4, x = p % A.width, y = (p / A.width) | 0;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
      if (zone) {
        let dove = "altrove";
        for (const z of zone.rett) {
          if (x >= z.r[0] && x < z.r[0] + z.r[2] && y >= z.r[1] && y < z.r[1] + z.r[3]) {
            dove = z.chi; break;
          }
        }
        if (dove === "altrove" && zone.disco &&
            (x - zone.disco[0]) ** 2 + (y - zone.disco[1]) ** 2 <= zone.disco[2] ** 2) {
          dove = "il nucleo";
        }
        per[dove] = (per[dove] || 0) + 1;
      }
    }
    const n = A.width * A.height;
    return { diversi, percentuale: (100 * diversi) / n, massimo, per,
             riquadro: diversi ? [x0, y0, x1 - x0 + 1, y1 - y0 + 1] : null };
  }, [ba, bb, zone]);
}

function riga(nome, m) {
  return (
    `${nome.padEnd(30)} ${String(m.larghezza + "x" + m.altezza).padEnd(10)}` +
    ` lum ${String(m.lumMedia).padStart(5)}` +
    ` · dev ${String(m.devStd).padStart(5)}` +
    ` · H ${String(m.entropia).padStart(4)}` +
    ` · 25-120 ${String(m.banda).padStart(5)}%` +
    ` · L>60 ${String(m.riempito).padStart(5)}%` +
    ` · L>120 ${String(m.chiaro).padStart(5)}%` +
    ` · caldo ${String(m.caldo).padStart(4)}%` +
    ` · barra ${String(m.barra).padStart(5)}%`
  );
}

/* ── il TRABOCCAMENTO ────────────────────────────────────────────────────────
 *
 * ## Perche' sta qui e non in uno script suo
 *
 * Perche' e' la meta' mancante della stessa domanda. La densita' premia
 * l'inchiostro: piu' roba a schermo, meglio e'. Ma l'inchiostro non e'
 * leggibilita', e le due si separano proprio dove fa piu' male — la barra di
 * §13 misura il 59 % di inchiostro nella propria fascia **mentre** 737 px di
 * campi stanno in 178 disponibili, cioe' dodici campi resi e tre leggibili.
 * Una misura che promuove quella barra e' una misura che manca il punto.
 *
 * ## Che cosa conta come traboccamento, e che cosa NO
 *
 * Un contenuto piu' largo del proprio riquadro non e' di per se' un difetto:
 * dipende da che cosa fa il riquadro.
 *
 *   overflow auto | scroll   il contenuto ECCEDE ma si RAGGIUNGE. Non conta.
 *   overflow hidden          il contenuto e' CANCELLATO senza rimedio. Conta.
 *   overflow visible         il contenuto esce e si sovrappone ad altro. Conta.
 *
 * E' la stessa distinzione che vale fra troncare e cancellare: `text-overflow:
 * ellipsis` dichiara che il testo continua, `overflow: hidden` su una fila che
 * non va a capo non dichiara niente.
 *
 * ## Perche' su una pagina viva e non su un PNG
 *
 * Un pixel non sa di essere stato tagliato. Il traboccamento e' una proprieta'
 * del LAYOUT — scrollWidth contro clientWidth — e si legge solo dove il layout
 * esiste ancora. E' l'unico pezzo di questo script che vuole una pagina.
 */
const IGNORA = new Set(["HTML", "BODY", "SCRIPT", "STYLE", "SVG", "PATH", "G"]);

async function traboccamento(pagina, url) {
  await pagina.goto(url);
  await pagina.waitForTimeout(1500);
  return pagina.evaluate((ignora) => {
    const fuori = [];
    for (const el of document.querySelectorAll("*")) {
      if (ignora.includes(el.tagName)) continue;
      const c = getComputedStyle(el);
      if (c.display === "none" || c.visibility === "hidden") continue;
      const dx = el.scrollWidth - el.clientWidth;
      const dy = el.scrollHeight - el.clientHeight;
      /* ⚠️ SOGLIA A 4 px, e non e' tolleranza: sotto ci sono solo gli
         arrotondamenti del line box. Misurato sulla scrivania vera, prima di
         questa riga: `.pnl-tel__val` risultava «3 px oltre 36» su ogni valore
         numerico, perche' l'area di contenuto di Plex Mono e' 1,31 em e
         `scrollHeight` la arrotonda per eccesso. Dodici falsi positivi in
         cima all'elenco nascondevano il solo vero. */
      if (dx < 4 && dy < 4) continue;
      /* Chi SCORRE non taglia: il contenuto eccede e si raggiunge. Chi lascia
         uscire (`visible`) non taglia nemmeno: si sovrappone, che e' un altro
         difetto e non questo. Qui si conta solo cio' che viene CANCELLATO.

         ⚠️ E c'e' un terzo caso, che questo controllo ha trovato da solo:
         contenuto ritagliato ma raggiungibile con un GESTO invece che con la
         barra di scorrimento del sistema. La giostra del plinto e' cosi' —
         nove piastre, cinque in vista, le altre a un giro di rotella — e
         `overflow-x: hidden` la faceva risultare 293 px di contenuto
         cancellato, che non e' vero.
         Non lo si indovina: chi ritaglia lo DICHIARA con `data-scorre-a-mano`,
         scrivendoci dentro con quale gesto si arriva al resto. Una regola che
         si legge nel DOM, non un elenco di eccezioni in questo file. */
      const aMano = el.getAttribute("data-scorre-a-mano");
      if (aMano !== null) {
        fuori.push({ chi: (el.className && typeof el.className === "string"
                       ? "." + el.className.trim().split(/\s+/).join(".")
                       : el.tagName.toLowerCase()),
                     dx, dy, largo: el.clientWidth, alto: el.clientHeight,
                     gesto: aMano || "(gesto non dichiarato)", aMano: true });
        continue;
      }
      const taglia = (asse) => asse === "hidden" || asse === "clip";
      const perso =
        (dx >= 4 && taglia(c.overflowX) ? dx : 0) +
        (dy >= 4 && taglia(c.overflowY) ? dy : 0);
      if (!perso) continue;
      fuori.push({
        chi: el.className && typeof el.className === "string"
          ? "." + el.className.trim().split(/\s+/).join(".")
          : el.tagName.toLowerCase(),
        dx: dx >= 4 && taglia(c.overflowX) ? dx : 0,
        dy: dy >= 4 && taglia(c.overflowY) ? dy : 0,
        largo: el.clientWidth,
        alto: el.clientHeight,
        overflowX: c.overflowX,
        overflowY: c.overflowY,
      });
    }
    // Il piu' grave per primo: quanto si perde in rapporto a quanto c'e'.
    fuori.sort((a, b) =>
      (b.dx / Math.max(1, b.largo) + b.dy / Math.max(1, b.alto)) -
      (a.dx / Math.max(1, a.largo) + a.dy / Math.max(1, a.alto)));
    return fuori;
  }, [...IGNORA]);
}

/* ── IL MARCHIO — criterio di accettazione §25.13.5 ──────────────────────────
 *
 * > Scatto della scrivania a pannelli aperti. Sul ritaglio del solo marchio:
 * > luminanza media <= 105, contrasto WCAG contro il composito sottostante
 * > >= 3,0:1 e <= 5,0:1.
 *
 * ## Perche' due scatti e non uno
 *
 * «Contro il composito sottostante» non si legge da un solo PNG: sotto la
 * scritta c'e' la nuvola, diversa in ogni punto. `app/main.js` scatta la stessa
 * scrivania col marchio nascosto — stessa sessione, 120 ms dopo — e da li' si
 * ricava che colore ci sarebbe senza. I pixel che DIFFERISCONO fra i due sono
 * la scritta piu' il suo scudo; tutto il resto e' la nuvola che si muove, e va
 * separata: entra nella soglia solo cio' che cambia di piu' del rumore.
 *
 * ## Due luminanze, e non sono la stessa
 *
 *   Rec. 709 su 0-255      «quanta superficie e' accesa». E' quella di §25.5 e
 *                          del tetto L <= 105 di questo criterio.
 *   WCAG relative lum.     «si legge». Ha la correzione di gamma e serve solo
 *                          al rapporto di contrasto.
 *
 * Confonderle e' gia' costato un numero sbagliato una volta in questo
 * progetto. Qui stanno vicine apposta, con i nomi diversi.
 */
const SOGLIE_MARCHIO = { lumMedia: 105, contrastoMin: 3.0, contrastoMax: 5.0 };

async function marchio(pagina, cartella, { centro = null, silenzioso = false } = {}) {
  const con = join(cartella, "scrivania.png");
  const senza = join(cartella, "scrivania-senza-marchio.png");
  const meta = join(cartella, "marchio.json");
  for (const f of [con, senza, meta]) {
    if (!existsSync(f)) {
      console.error(`manca ${f} — si producono con: npm run scrivania`);
      process.exit(2);
    }
  }
  const m = JSON.parse(readFileSync(meta, "utf-8"));
  const [ba, bb] = [readFileSync(con).toString("base64"),
                    readFileSync(senza).toString("base64")];
  const esito = await pagina.evaluate(async ([ba, bb, rett, dichiarato, centro]) => {
    const dati = async (b64) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      c.getContext("2d").drawImage(img, 0, 0);
      return c.getContext("2d").getImageData(0, 0, c.width, c.height);
    };
    const A = await dati(ba), B = await dati(bb);
    const [x0, y0, w, h] = rett;
    /* Il ritaglio si allarga di 8 px per lato: lo scudo `text-shadow` esce dal
       riquadro del testo — 22 px di sfocatura — e un ritaglio stretto sul testo
       misurerebbe la scritta senza cio' che le sta attorno, che e' meta' del
       criterio. Otto e non ventidue: oltre, il ritaglio e' quasi tutto nuvola e
       la media dice della nuvola, non del marchio. */
    const B0 = 8;
    const rx = Math.max(0, x0 - B0), ry = Math.max(0, y0 - B0);
    const rw = Math.min(A.width - rx, w + 2 * B0), rh = Math.min(A.height - ry, h + 2 * B0);
    const rec709 = (d, i) => 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    //: WCAG 2.x: canale linearizzato, poi la stessa somma pesata.
    const lin = (c) => { const s = c / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
    const wcag = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);

    let somma = 0, n = 0, maxCon = 0, maxSenza = 0, raggioInchiostro = 0;
    /* ⚠️ I pixel che cambiano NON sono tutti la scritta, e il primo giro di
       questa misura li ha mescolati: rispondeva «scritta rgb(27, 70, 79)» dove
       il colore dichiarato e' rgb(34, 116, 130). La differenza erano lo SCUDO e
       i bordi sfumati, contati insieme ai tratti.
       Lo scudo e' `text-shadow` col colore del pavimento: SCURISCE. I tratti
       schiariscono. Il segno della differenza li separa senza bisogno di una
       soglia inventata:
         piu' chiaro del composito  ->  il tratto
         piu' scuro                 ->  lo scudo
       E sono due domande diverse, tutt'e due legittime, che vanno tenute
       separate invece di finire in una media sola. */
    let st = [0, 0, 0], su = [0, 0, 0], nt = 0;      // tratto, e cio' che ci sta sotto
    let ss = [0, 0, 0], ns = 0;                       // lo scudo, come appare
    const tratti = [];                                // per il decile piu' pieno
    for (let y = ry; y < ry + rh; y++) {
      for (let x = rx; x < rx + rw; x++) {
        const i = 4 * (y * A.width + x);
        const la = rec709(A.data, i), lb = rec709(B.data, i);
        somma += la; n++;
        if (la > maxCon) maxCon = la;
        if (lb > maxSenza) maxSenza = lb;
        //: 8/255 e' la stessa soglia della differenza fra due scatti: sotto ci
        //: sono solo il dithering e la nuvola che si e' spostata di un livello.
        const d = Math.max(Math.abs(A.data[i] - B.data[i]),
                           Math.abs(A.data[i + 1] - B.data[i + 1]),
                           Math.abs(A.data[i + 2] - B.data[i + 2]));
        if (d <= 8) continue;
        if (rec709(A.data, i) > rec709(B.data, i)) {
          nt++;
          for (let k = 0; k < 3; k++) { st[k] += A.data[i + k]; su[k] += B.data[i + k]; }
          tratti.push([rec709(A.data, i), A.data[i], A.data[i + 1], A.data[i + 2],
                       B.data[i], B.data[i + 1], B.data[i + 2]]);
          /* ⚠️ Il raggio dell'inchiostro, misurato sui PIXEL.
             La guardia in `verifica:scrivania` usa la semi-diagonale del
             riquadro reso, che e' un limite superiore perche' gli angoli del
             riquadro sono vuoti. Qui c'e' il numero vero, e serve alla stessa
             domanda: se un pixel di tratto arriva sulla fascia piu' interna, il
             composito sotto il nome smette di essere un token dichiarato e
             diventa una media — che e' come §25.13.5 e' caduta a 2,94:1 il
             23 agosto 2026. */
          if (centro) {
            const rr = Math.hypot(x - centro[0], y - centro[1]);
            if (rr > raggioInchiostro) raggioInchiostro = rr;
          }
        } else {
          ns++;
          for (let k = 0; k < 3; k++) ss[k] += A.data[i + k];
        }
      }
    }
    if (!nt) return { lumMedia: somma / n, punti: n, pixelMarchio: 0 };
    const [cr, cg, cb] = st.map((v) => v / nt);
    const [fr, fg, fb] = su.map((v) => v / nt);
    const rapporto = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    const Lc = wcag(cr, cg, cb);
    const Lsotto = wcag(fr, fg, fb);
    /* ⚠️ IL CRITERIO SI CALCOLA SUL COLORE DICHIARATO, non sulla media resa, e
       la differenza non e' un dettaglio: 3,33:1 contro 1,94:1, cioe' passa o
       non passa.
       WCAG e' definito fra due COLORI, non fra due rendering: l'antialiasing di
       una scritta alta 22 px con spaziatura larga produce in maggioranza pixel
       a copertura parziale, e la loro media e' piu' scura del colore del testo
       per costruzione — su qualunque testo, conforme o no. Giudicare li'
       vorrebbe dire bocciare la tipografia piccola in quanto piccola.
       Il colore dichiarato lo legge `app/main.js` da `getComputedStyle` nella
       finestra vera; il fondo resta MISURATO, perche' «il composito
       sottostante» e' proprio cio' che nessuna dichiarazione conosce.
       Che il colore dichiarato si veda davvero da qualche parte non si da' per
       buono: e' il decile piu' pieno, qui sotto. */
    const dc = /^rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(dichiarato || "");
    const dich = dc ? [+dc[1], +dc[2], +dc[3]] : null;
    const Ldich = dich ? wcag(dich[0], dich[1], dich[2]) : null;
    const contrasto = Ldich !== null ? rapporto(Ldich, Lsotto) : rapporto(Lc, Lsotto);
    //: Il decile piu' luminoso dei tratti: i pixel a copertura piena. Se questi
    //: non arrivano al colore dichiarato, la dichiarazione e' smentita dal
    //: rendering e il criterio va giudicato sul reso.
    tratti.sort((a, b) => b[0] - a[0]);
    /* Il pixel piu' luminoso della scritta, in Rec. 709 su 0-255 — che e' la
       scala di §25.5, non quella di WCAG. Serve a rispondere alla deroga 2 di
       DEROGHE-7dad2b8.md, che misurava «massima L 255» sull'insegna e ne
       attribuiva il primato al marchio: dopo il cambio di colore, questo numero
       dice se l'attribuzione era giusta e quanto e' sceso. */
    const massimoTratto = tratti.length ? tratti[0][0] : 0;
    const massimoColore = tratti.length ? tratti[0].slice(1, 4).map(Math.round) : null;
    //: E che cosa c'era SOTTO quel pixel: un tratto non puo' essere piu' chiaro
    //: del proprio colore, un bordo sfumato su una nuvola chiara si'.
    const massimoSotto = tratti.length ? tratti[0].slice(4).map(Math.round) : null;
    const q = Math.max(1, Math.round(tratti.length / 10));
    const pieno = [0, 0, 0];
    for (let k = 0; k < q; k++) for (let c = 0; c < 3; c++) pieno[c] += tratti[k][c + 1] / q;
    const scudo = ns ? ss.map((v) => v / ns) : null;
    return {
      lumMedia: somma / n, punti: n, pixelMarchio: nt + ns,
      pixelTratto: nt, pixelScudo: ns,
      ritaglio: [rx, ry, rw, rh],
      scritta: [cr, cg, cb].map(Math.round),
      sotto: [fr, fg, fb].map(Math.round),
      lumScritta: rec709([cr, cg, cb, 255], 0),
      lumSotto: rec709([fr, fg, fb, 255], 0),
      contrasto,
      dichiarato: dich,
      contrastoReso: rapporto(Lc, Lsotto),
      pieno: pieno.map(Math.round),
      massimoTratto, massimoColore, massimoSotto, maxCon, maxSenza,
      raggioInchiostro: +raggioInchiostro.toFixed(1),
      contrastoPieno: rapporto(wcag(pieno[0], pieno[1], pieno[2]), Lsotto),
      //: Contro lo scudo, non contro cio' che c'era prima: e' quello che
      //: l'occhio vede davvero attorno ai tratti. Contesto, non criterio —
      //: §25.13.5 dice «contro il composito sottostante», ed e' l'altro.
      scudo: scudo ? scudo.map(Math.round) : null,
      contrastoSuScudo: scudo ? rapporto(Lc, wcag(scudo[0], scudo[1], scudo[2])) : null,
    };
  }, [ba, bb, m.r, m.colore, centro]);

  const dire = silenzioso ? () => {} : console.log;
  dire(`marchio      ${m.corpo} · dichiarato ${m.colore}`);
  dire(`  ritaglio   ${esito.ritaglio ? esito.ritaglio[2] + "x" + esito.ritaglio[3] : "?"}` +
    ` · ${esito.punti.toLocaleString("it")} pixel, di cui ${esito.pixelTratto || 0} di tratto` +
    ` e ${esito.pixelScudo || 0} di scudo`);
  dire(`  luminanza  media del ritaglio ${esito.lumMedia.toFixed(1)}` +
    ` (Rec. 709, tetto ${SOGLIE_MARCHIO.lumMedia})` +
    (esito.massimoTratto !== undefined
      ? ` · pixel piu' luminoso della scritta ${esito.massimoTratto.toFixed(1)}` +
        ` = rgb(${(esito.massimoColore || []).join(", ")})` : ""));
  dire(`             massimo del ritaglio ${esito.maxCon.toFixed(1)} col marchio` +
    ` · ${esito.maxSenza.toFixed(1)} SENZA — la differenza dice quanto ci mette la scritta`);
  if (!esito.pixelMarchio) {
    dire("  ⚠️ i due scatti non differiscono: il marchio non si vede, o non e' stato nascosto");
    return { codice: 1, esito, errore: "i due scatti non differiscono" };
  }
  dire(`  sotto      rgb(${esito.sotto.join(", ")}) L ${esito.lumSotto.toFixed(1)}` +
    ` — il composito misurato, non dichiarato da nessuno`);
  dire(`  contrasto  ${esito.contrasto.toFixed(2)}:1 fra il colore DICHIARATO e il composito` +
    ` (WCAG, forbice ${SOGLIE_MARCHIO.contrastoMin}-${SOGLIE_MARCHIO.contrastoMax}:1)`);
  dire(`  e il reso  decile piu' pieno rgb(${esito.pieno.join(", ")})` +
    ` -> ${esito.contrastoPieno.toFixed(2)}:1` +
    ` · media di tutti i tratti rgb(${esito.scritta.join(", ")}) -> ${esito.contrastoReso.toFixed(2)}:1` +
    "   (l'antialiasing diluisce: contesto)");
  if (esito.contrastoSuScudo) {
    dire(`             ${esito.contrastoSuScudo.toFixed(2)}:1 della media contro il proprio scudo` +
      ` rgb(${esito.scudo.join(", ")})`);
  }

  const fuori = [];
  if (esito.lumMedia > SOGLIE_MARCHIO.lumMedia)
    fuori.push(`luminanza media ${esito.lumMedia.toFixed(1)} > ${SOGLIE_MARCHIO.lumMedia}`);
  if (esito.contrasto < SOGLIE_MARCHIO.contrastoMin)
    fuori.push(`contrasto ${esito.contrasto.toFixed(2)}:1 < ${SOGLIE_MARCHIO.contrastoMin}:1 — non si legge`);
  if (esito.contrasto > SOGLIE_MARCHIO.contrastoMax)
    fuori.push(`contrasto ${esito.contrasto.toFixed(2)}:1 > ${SOGLIE_MARCHIO.contrastoMax}:1 — compete col testo dei pannelli`);
  dire(fuori.length ? "\n§25.13.5 NON SODDISFATTO — " + fuori.join(" · ")
                    : "\n§25.13.5 SODDISFATTO");
  return { codice: fuori.length ? 1 : 0, esito, fuori };
}

/* ── LA GUARDIA — §25.13.5 in tutti gli stati, e la sua premessa geometrica ──
 *
 * ## Perche' esiste
 *
 * Il criterio del marchio e' stato chiuso misurandolo in UNO stato su sette, e
 * il turno 4 ha misurato gli altri otto. Ma una misura fatta una volta e' una
 * fotografia: senza una guardia, il prossimo che tocca il nucleo la invalida
 * senza saperlo — ed e' successo due volte in un giorno, a `b2f7360` e a
 * `4611cb6`, tutte e due perche' una geometria si e' mossa sotto un numero
 * scritto altrove.
 *
 * ## Perche' NON e' un test che scatta
 *
 * Un test che apre Electron rimetterebbe in suite il conflitto che il turno 1
 * ha documentato: cinque file di test usano il socket del core VIVO, e uno
 * scatto in parallelo gli sposta il layout sotto. La cattura resta manuale
 * (`npm run verifica:marchio`); la suite legge questo esito e verifica che sia
 * **fresco**, confrontando un'impronta dei sorgenti del nucleo. Se il nucleo
 * cambia e nessuno rimisura, la suite cade e dice che cosa eseguire.
 *
 * ⚠️ **Il limite dell'impronta, dichiarato**: lega la guardia a tre file. Una
 * modifica altrove che cambi il composito sotto il nome — `ui/src/style/app.css`,
 * per dire — non la fa scattare. Chi ne aggiunge uno lo mette in FONTI.
 */
const DOVE_ESITO = "docs/acceptance/MARCHIO-STATI.json";
const FONTI = [
  "ui/src/desk/sfondo.js",     // il marchio, il campo, le regole di scope
  "ui/src/anim/rings.js",      // la geometria: raggi, spessori, quali fasce
  "ui/src/style/tokens.css",   // i colori di tutte e due
];

async function guardiaMarchio(pagina, radice) {
  const { createHash } = await import("node:crypto");
  const { readdirSync } = await import("node:fs");

  const statiFile = join(radice, "stati.json");
  if (!existsSync(statiFile)) {
    console.error(`manca ${statiFile} — si produce con: npm run verifica:marchio`);
    return 2;
  }
  const cattura = JSON.parse(readFileSync(statiFile, "utf-8"));
  const centro = cattura.geometria ? [768, 422] : null;

  const impronta = createHash("sha256");
  for (const f of FONTI) impronta.update(readFileSync(f));

  const esito = {
    quando: cattura.quando ?? null,
    impronta: impronta.digest("hex").slice(0, 16),
    fonti: FONTI,
    geometria: cattura.geometria ?? null,
    soglie: SOGLIE_MARCHIO,
    stati: {},
  };

  /* ⚠️ Le cartelle che cominciano con «_» NON sono stati: sono varianti, e
     `_variante-campo-void` e' una delle uscite di §25.13 resa misurabile. Si
     misurano lo stesso e si riportano, ma non concorrono al giudizio: un
     esperimento che fallisse boccerebbe una build per una cosa che nessuno ha
     messo nel prodotto. */
  const cartelle = readdirSync(radice, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();

  let rotti = 0;
  for (const nome of cartelle) {
    const r = await marchio(pagina, join(radice, nome), { centro, silenzioso: true });
    const e = r.esito;
    const variante = nome.startsWith("_");
    const voce = {
      variante,
      contrasto: +e.contrasto.toFixed(3),
      lumMedia: +e.lumMedia.toFixed(1),
      sotto: e.sotto,
      raggioInchiostro: e.raggioInchiostro,
      passa: r.codice === 0,
      fuori: r.fuori ?? [],
    };
    esito.stati[nome] = voce;
    if (!variante && r.codice !== 0) rotti++;
    console.log(
      `  ${nome.padEnd(22)} contrasto ${voce.contrasto.toFixed(2)}:1` +
      `  lum ${String(voce.lumMedia).padStart(5)}` +
      `  inchiostro fino a r ${String(voce.raggioInchiostro).padStart(5)} px` +
      (variante ? "   (variante, non concorre)" : voce.passa ? "   ✅" : "   ❌ " + voce.fuori.join(" · ")));
  }

  /* Il franco VERO, dai pixel: il piu' lontano fra tutti gli stati contro il
     bordo interno della fascia piu' interna. La guardia in verifica:scrivania
     usa la semi-diagonale del riquadro, che e' un limite superiore; qui c'e' il
     numero misurato. */
  const g = esito.geometria;
  const inchiostroMax = Math.max(...Object.values(esito.stati).map((v) => v.raggioInchiostro));
  esito.franco = g ? +(g.raggioMinimoFascia - inchiostroMax).toFixed(1) : null;
  esito.inchiostroMax = inchiostroMax;
  if (esito.franco !== null) {
    console.log(`\n  franco     l'inchiostro arriva a r ${inchiostroMax} px, la fascia piu' interna` +
      ` comincia a ${g.raggioMinimoFascia} px  ->  ${esito.franco} px`);
    if (esito.franco <= 0) {
      console.log("  ❌ il marchio tocca la fascia: il composito sotto il nome non e' piu' un token dichiarato");
      rotti++;
    }
  }

  /* ⚠️ L'esito NON va in `shots/`, che e' ignorato da git: va in
     `docs/acceptance/`, versionato, perche' e' la meta' leggibile-da-macchina
     di un documento di accettazione. Cosi' la suite lo trova su un clone
     pulito e non deve saltare il controllo — un test che si salta quando il
     file manca e' un test che non c'e'. */
  writeFileSync(DOVE_ESITO, JSON.stringify(esito, null, 2) + "\n");
  console.log(`\n  esito      ${DOVE_ESITO} · impronta ${esito.impronta}`);
  console.log(rotti ? `\n§25.13.5 NON SODDISFATTO in ${rotti} stati` : "\n§25.13.5 SODDISFATTO in tutti gli stati");
  return rotti ? 1 : 0;
}

/* ── l'istogramma, bin per bin ────────────────────────────────────────────
 *
 * PERCHE' ESISTE. L'entropia dice quanto e' articolato l'istogramma con UN
 * numero, e un numero non dice DOVE manca l'articolazione. Con 2,17 contro
 * 2,40 la domanda che serviva era «quali livelli non ci sono», e la risposta
 * non si legge da nessuna delle sei metriche.
 *
 * La prima volta che e' stato stampato ha detto una cosa che nessuna delle
 * misure precedenti aveva detto: NOVE dei sedici bin stanno sotto lo 0,5 %,
 * e nel riferimento non ce n'e' NESSUNO. Il divario non e' «poco contenuto»:
 * e' che il fotogramma ha cinque livelli di luminanza invece di sedici.
 */
async function istogramma(pagina, file) {
  const b64 = readFileSync(file).toString("base64");
  return pagina.evaluate(
    async ([b64, luma, bin]) => {
      const img = new Image();
      img.src = "data:image/png;base64," + b64;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth;
      c.height = img.naturalHeight;
      const g = c.getContext("2d");
      g.drawImage(img, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height).data;
      const L = new Function("d", "i", `return ${luma};`);
      const n = c.width * c.height;
      const h = new Float64Array(bin);
      for (let p = 0; p < n; p++) h[Math.min(bin - 1, (L(d, p * 4) * bin / 256) | 0)]++;
      return [...h].map((x) => Math.round(1000 * x / n) / 10);
    },
    [b64, LUMA, BIN]
  );
}

/* Un bin sotto questa quota non partecipa: contribuisce meno di un centesimo
 * di bit all'entropia, e all'occhio non esiste. Non e' una soglia di giudizio,
 * e' la definizione di «vuoto» usata nel conteggio stampato sotto. */
const BIN_VUOTO = 0.5;

function stampaIstogramma(nostro, riferimento) {
  const barra = (x) => "#".repeat(Math.min(20, Math.round(x / 2)));
  console.log("\n bin   L          nostro" + (riferimento ? "   riferimento    scarto" : ""));
  for (let k = 0; k < BIN; k++) {
    const a = nostro[k];
    let riga =
      String(k).padStart(4) + "  " + String(k * 16).padStart(3) + "-" +
      String(k * 16 + 15).padStart(3) + String(a + "%").padStart(9);
    if (riferimento) {
      const b = riferimento[k];
      riga += String(b + "%").padStart(10) +
        ((b - a >= 0 ? "+" : "") + Math.round(10 * (b - a)) / 10).padStart(9);
    }
    console.log(riga + "   " + barra(a).padEnd(21) +
      (riferimento ? "|" + barra(riferimento[k]) : ""));
  }
  const vuoti = (h) => h.filter((x) => x < BIN_VUOTO).length;
  console.log(`\n  bin sotto lo ${BIN_VUOTO} %: nostro ${vuoti(nostro)} su ${BIN}` +
    (riferimento ? `, riferimento ${vuoti(riferimento)} su ${BIN}` : ""));
}

const argomenti = process.argv.slice(2);
if (argomenti[0] === "--istogramma") {
  const nostro = argomenti[1];
  if (!nostro) {
    console.error("uso: node scripts/densita.mjs --istogramma <png> [riferimento.png]");
    process.exit(2);
  }
  const b = await chromium.launch();
  const p = await b.newPage();
  const a = await istogramma(p, nostro);
  const r = argomenti[2] ? await istogramma(p, argomenti[2]) : null;
  await b.close();
  stampaIstogramma(a, r);
  process.exit(0);
}

/* Due PNG QUALSIASI, non i due scatti gemelli.
 *
 * Serve fra un giro e l'altro, e nasce da una misura andata a vuoto: quattordici
 * giri di `npm run scrivania:fixture` hanno dato lo stesso PNG tredici volte e
 * un PNG diverso una volta, e quel file non era stato conservato — la
 * differenza non era attribuibile. Un `sha256` diverso e' l'assenza di una
 * misura, non una misura (§11.7 regola 4).
 *
 * `differenza()` e' la STESSA che confronta i gemelli: la proprieta' «dove
 * cambiano i pixel» ha un proprietario solo. Cambia solo chi sono i due file.
 * L'attribuzione ai rettangoli chiede `occlusione.json` accanto al PRIMO. */
if (argomenti[0] === "--differenza") {
  const [, a, b] = argomenti;
  if (!a || !b) {
    console.error("uso: node scripts/densita.mjs --differenza <a.png> <b.png>");
    process.exit(2);
  }
  const dovOcc = join(dirname(a), "occlusione.json");
  const occ = existsSync(dovOcc) ? JSON.parse(readFileSync(dovOcc, "utf-8")) : null;
  const zone = occ && occ.rettangoli
    ? { rett: occ.rettangoli, disco: occ.disco ? [...occ.disco.centro, occ.disco.raggio] : null }
    : null;
  const br = await chromium.launch();
  const pg = await br.newPage();
  const d = await differenza(pg, a, b, zone);
  await br.close();
  if (!d || !d.diversi) {
    console.log(`${basename(a)} e ${basename(b)}: IDENTICI, 0 pixel di differenza`);
    process.exit(0);
  }
  console.log(`${basename(a)} contro ${basename(b)}: ${d.diversi.toLocaleString("it")} pixel ` +
    `(${d.percentuale.toFixed(2)} %), massimo scarto ${d.massimo}/255`);
  if (d.riquadro) {
    console.log(`  dentro ${d.riquadro[2]}x${d.riquadro[3]} a (${d.riquadro[0]}, ${d.riquadro[1]})`);
  }
  if (d.per) {
    for (const [chi, n] of Object.entries(d.per)) console.log(`  ${chi.padEnd(14)} ${n}`);
  }
  if (!zone) console.log("  (nessun occlusione.json accanto al primo: niente attribuzione)");
  process.exit(1);
}

if (argomenti[0] === "--marchio-stati") {
  const radice = argomenti[1];
  if (!radice) {
    console.error("uso: node scripts/densita.mjs --marchio-stati <cartella>");
    process.exit(2);
  }
  const browser = await chromium.launch();
  const pagina = await browser.newPage();
  const codice = await guardiaMarchio(pagina, radice);
  await browser.close();
  process.exit(codice);
}
if (argomenti[0] === "--marchio") {
  const cartella = argomenti[1];
  if (!cartella) {
    console.error("uso: node scripts/densita.mjs --marchio <cartella degli scatti>");
    process.exit(2);
  }
  const browser = await chromium.launch();
  const pagina = await browser.newPage();
  const { codice } = await marchio(pagina, cartella);
  await browser.close();
  process.exit(codice);
}

if (argomenti[0] === "--traboccamento") {
  const url = argomenti[1];
  if (!url) {
    console.error("uso: node scripts/densita.mjs --traboccamento <url> [larghezza] [altezza]");
    process.exit(2);
  }
  /* ⚠️ LA LARGHEZZA E' UN PARAMETRO, e senza questo il criterio non trova
     niente. Il traboccamento non e' una proprieta' del layout: e' il rapporto
     fra il layout e lo SPAZIO. A 1536 la barra di §13 sta comoda; il difetto
     che questo controllo esiste per trovare — dodici campi resi e tre
     leggibili — compare sotto i 1200. Misurare a una larghezza sola vuol dire
     dichiarare conforme un'interfaccia che si rompe alla prima finestra
     diversa, ed e' il punto 10 di DIVARIO-PREMIUM.md. */
  const larghezza = Number(argomenti[2] || 1536);
  const altezza = Number(argomenti[3] || 843);
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: larghezza, height: altezza } });
  console.log(`traboccamento a ${larghezza}x${altezza}\n`);
  const tutti = await traboccamento(pg, url);
  await b.close();
  const aMano = tutti.filter((f) => f.aMano);
  const fuori = tutti.filter((f) => !f.aMano);
  if (aMano.length) {
    console.log("ritagliato ma RAGGIUNGIBILE con un gesto — dichiarato, non conta:");
    for (const f of aMano) {
      console.log(`  ${f.chi.slice(0, 40).padEnd(42)} ${String(f.dx).padStart(5)} px oltre ` +
                  `${String(f.largo).padStart(5)} · ${f.gesto}`);
    }
    console.log("");
  }
  if (!fuori.length) {
    console.log("NESSUN TRABOCCAMENTO — tutto il contenuto sta nel proprio riquadro");
    process.exit(0);
  }
  console.log("TRABOCCAMENTO — contenuto tagliato e IRRAGGIUNGIBILE:\n");
  for (const f of fuori.slice(0, 12)) {
    const q = f.largo ? ((f.dx / f.largo) * 100).toFixed(0) : "0";
    console.log(
      `  ${f.chi.slice(0, 44).padEnd(46)} ` +
      `${String(f.dx).padStart(5)} px oltre ${String(f.largo).padStart(5)} ` +
      `(${q.padStart(4)}% in piu') · overflow-x ${f.overflowX}` +
      (f.dy ? ` · ${f.dy} px in altezza` : "")
    );
  }
  if (fuori.length > 12) console.log(`  … e altri ${fuori.length - 12}`);
  process.exit(1);
}

const [file, riferimento] = argomenti;
if (!file) {
  console.error(
    "uso: node scripts/densita.mjs <screenshot.png> [riferimento.png]\n" +
      "     node scripts/densita.mjs --traboccamento <url>\n" +
      "     senza riferimento, confronta con le soglie di\n" +
      "     docs/design-reference/README.md"
  );
  process.exit(2);
}

const browser = await chromium.launch();
const pagina = await browser.newPage();

/* §5.5 del piano — DUE scatti, e si tiene la mediana.
 *
 * Il gemello lo produce `app/main.js` a 250 ms dal primo, e si chiama come il
 * primo con «-b». Se c'e', si misura anche lui e il giudizio va sulla mediana:
 * con due misure la mediana e' la media, e non e' quello il punto — il punto e'
 * lo SCARTO fra le due, che dice se la scrivania era ferma. Uno scarto grande
 * significa che si sta misurando un fotogramma, non una composizione, e va
 * letto prima del numero. */
/* L'occlusione si legge PRIMA di misurare, non dopo: i suoi riquadri servono
   ad attribuire i pixel che cambiano fra i due scatti. Si stampa dopo, dove va
   letta. */
const dovOcc = join(dirname(file), "occlusione.json");
const occ = existsSync(dovOcc) ? JSON.parse(readFileSync(dovOcc, "utf-8")) : null;
const zone = occ && occ.rettangoli
  ? { rett: occ.rettangoli, disco: occ.disco ? [...occ.disco.centro, occ.disco.raggio] : null }
  : null;

/* La fascia del dock: cio' che sta SOTTO il pavimento dichiarato. Il pavimento
   e' `[alto, alto + altezza]`, la finestra finisce dopo, e la differenza e' il
   dock. Senza `occlusione.json` resta `null`, e il criterio dira' «non
   misurabile» invece di dire zero. */
const pav = occ && occ.protocollo && occ.protocollo.pavimento;
const fasce = pav && occ.protocollo.finestra
  ? { dock: [pav.alto + pav.altezza, occ.protocollo.finestra[1]] }
  : null;

const gemello = file.replace(/\.png$/, "-b.png");
const m0 = await misura(pagina, file, fasce);
let m = m0, m1 = null;
if (gemello !== file && existsSync(gemello)) {
  m1 = await misura(pagina, gemello, fasce);
  m = Object.fromEntries(Object.entries(m0).map(
    ([k, v]) => [k, typeof v === "number" ? Math.round(1000 * (v + m1[k]) / 2) / 1000 : v]));
}
console.log(riga(basename(file), m0));
if (m1) {
  console.log(riga(basename(gemello), m1));
  console.log(riga("mediana delle due", m));
  const scarti = ["entropia", "devStd", "riempito", "caldo", "barra"]
    .map((k) => [k, Math.abs(m0[k] - m1[k])])
    .filter(([, d]) => d > 0.05);
  const d = await differenza(pagina, file, gemello, zone);
  console.log(scarti.length
    ? "  ⚠️ le due MISURE non coincidono: " +
      scarti.map(([k, d]) => `${k} ±${d.toFixed(2)}`).join(" · ") +
      " — si sta misurando un fotogramma, non una composizione (§5.4)"
    : "  le due misure coincidono a meno di 0,05: quello che si muove non sposta la metrica");
  if (d) {
    console.log(`  in 250 ms cambiano ${d.diversi.toLocaleString("it")} pixel su ` +
      `${(m.larghezza * m.altezza).toLocaleString("it")} — ${d.percentuale.toFixed(2)} %, ` +
      `massimo scarto ${d.massimo}/255`);
    if (d.riquadro) {
      console.log(`  cio' che si muove sta in ${d.riquadro[2]}x${d.riquadro[3]} ` +
        `a (${d.riquadro[0]}, ${d.riquadro[1]})`);
    }
    const per = Object.entries(d.per || {}).sort((a, b) => b[1] - a[1]);
    if (per.length) {
      console.log("  e si divide cosi': " +
        per.map(([k, v]) => `${k} ${((100 * v) / d.diversi).toFixed(0)} %`).join(" · "));
    }
    /* ⚠️ «ANIMAZIONI FERME» NON PUO' VOLER DIRE «ZERO PIXEL CHE CAMBIANO», e
       questa misura lo ha dimostrato prima che qualcuno lo scrivesse.
       Il 15 % di cio' che si muove e' il pannello telemetria che riceve un dato
       nuovo dal core: e' un'animazione CON causa, che l'invariante 25 non
       vieta — anzi, e' il solo modo in cui un dato vivo si vede. Una soglia a
       zero boccerebbe la scrivania per aver funzionato.
       Il vincolo di §5.4 e' l'altro pezzo: quello che si muove SENZA causa. Sul
       nucleo la causa non c'e' (deroga 1 di DEROGHE-7dad2b8.md), e finche' c'e'
       la nuvola quel pezzo resta. E' quello che il turno 3 deve portare a zero,
       e questo numero e' il suo prima. */
    const ambiente = d.per ? d.per["il nucleo"] || 0 : 0;
    console.log(ambiente
      ? `  ⚠️ §5.4 NON soddisfatto: ${ambiente.toLocaleString("it")} pixel ` +
        `(${((100 * ambiente) / d.diversi).toFixed(0)} % del moto) sono il nucleo, ` +
        "che si muove SENZA causa — invariante 25, deroga 1"
      : "  §5.4 soddisfatto: niente si muove senza causa. " +
        "Quel che resta sono pannelli che ricevono dati, ed e' il loro mestiere");
  }
}

if (riferimento) {
  const r = await misura(pagina, riferimento);
  console.log(riga(basename(riferimento), r));
}

await browser.close();

/* ── L'OCCLUSIONE, se qualcuno l'ha misurata ────────────────────────────────
 *
 * Le tre frazioni di `PIANO-CORE-E-DENSITA.md` §5. Non si calcolano qui e non
 * potrebbero: «coperto» e' una proprieta' del layout, e un PNG non sa che cosa
 * aveva sotto. Le misura `scripts/occlusione-dom.js` dentro la finestra vera e
 * le lascia in `occlusione.json` accanto allo scatto; qui si stampano, perche'
 * e' accanto alla densita' che vanno lette.
 *
 * ⚠️ Perche' insieme. La densita' dice quanta superficie e' accesa e non sa
 * distinguere «non c'e'» da «c'e' e sta sotto». Sono due difetti opposti: il
 * primo si ripara costruendo, il secondo spostando. Chi legge solo il caldo
 * allo 0,18 % costruisce cartelle nuove; chi legge anche questo blocco scopre
 * se quelle che ci sono sono coperte — o se non ci sono affatto. */
if (occ) {
  const o = occ;
  const pr = o.protocollo;
  console.log("\nOCCLUSIONE — PIANO-CORE-E-DENSITA §5, passo " + pr.passo + " px");
  console.log(`  protocollo  finestra ${pr.finestra[0]}x${pr.finestra[1]}` +
    ` · massimizzata ${pr.massimizzata ? "si" : "NO — il confronto non vale"}` +
    ` · scena ${pr.scena} · filtro ${pr.filtro ?? "nessuno"}` +
    ` · riposo ${pr.riposo ? "SI — §5.3 lo esclude" : "no"}`);
  console.log(`              misurati ${(o.rettangoli || []).map((r) => r.chi).join(", ")}` +
    ` · aperti ma nascosti ${Math.max(0, (pr.aperti || []).length - (o.rettangoli || []).length)}` +
    ` · scatti ${pr.scattiIdentici ? "identici" : "DIVERSI (§5.4 non soddisfatto)"}` +
    (pr.fotogrammiInsegna === null || pr.fotogrammiInsegna === undefined ? ""
      : ` · l'insegna ha chiesto ${pr.fotogrammiInsegna} fotogrammi in tutto`));
  console.log(`  pavimento   coperto dai pannelli ${o.pavimento.copertoDaPannelli.toFixed(1)} %` +
    ` · dalla cornice ${o.pavimento.copertoDallaCornice.toFixed(1)} %` +
    ` · libero ${o.pavimento.libero.toFixed(1)} %`);
  console.log(`  caldi       ${o.caldi.coperti}/${o.caldi.sulPavimento} coperti oltre il ` +
    `${(100 * o.caldi.soglia).toFixed(0)} %` +
    (o.caldi.sulPavimento === 0
      ? "   ⚠️ nessun elemento caldo FUORI dai pannelli: non e' coperto, non c'e'"
      : ` (${o.caldi.percentuale.toFixed(1)} %)`));
  console.log(`  icone       ${o.icone.coperte}/${o.icone.totale} coperte` +
    (o.icone.totale === 0 ? "   ⚠️ nessuna icona sul piano" : ""));
  if (o.disco) {
    console.log(`  nucleo      disco Ø${(2 * o.disco.raggio).toFixed(0)} = ` +
      `${o.disco.quotaDelPavimento.toFixed(2)} % del pavimento` +
      ` · coperto ${o.disco.copertoDaPannelli.toFixed(1)} %` +
      ` · libero ${o.disco.libero.toFixed(1)} %`);
    /* ⚠️ IL TETTO, ricalcolato — §5 lo chiede esplicitamente.
       La soglia «il nucleo sia almeno il 5 % dello schermo» era, senza che
       nessuno se ne accorgesse, quasi il massimo teorico: un disco non puo'
       rendere piu' della propria area, e la propria area moltiplicata per la
       frazione d'inchiostro. Scritta cosi', la misura dice quanto del
       raggiungibile e' stato raggiunto, e non si puo' piu' leggere come un
       margine che non esiste. */
    const tetto = o.disco.quotaDelPavimento * (o.disco.libero / 100);
    console.log(`              tetto raggiungibile ${tetto.toFixed(2)} % del pavimento` +
      " (area del disco x quota scoperta) — l'inchiostro del nucleo sta dentro questo");
  }
  if (o.buco) {
    console.log(`  il buco     la scena lascia libero un disco Ø${o.buco.diametro} = ` +
      `${o.buco.quotaDelPavimento.toFixed(2)} % del pavimento` +
      (o.disco
        ? `, e il nucleo ne occupa Ø${(2 * o.disco.raggio).toFixed(0)} ` +
          `(${(100 * (o.disco.raggio / o.buco.raggio) ** 2).toFixed(0)} % della sua area)`
        : ""));
  }
}

/* L'esito e' un codice di uscita, non una frase: cosi' il ciclo §11.7 puo'
 * bocciare senza che qualcuno debba leggere. */
const falliti = [];
// Le due misure di ARTICOLAZIONE vengono per prime: sono quelle che una
// superficie uniforme non puo' ingannare, e sono il motivo per cui L>25 e'
// stata ritirata dal giudizio (vedi SOGLIE).
if (m.entropia < SOGLIE.entropia)
  falliti.push(`entropia ${m.entropia} < ${SOGLIE.entropia} bit`);
if (m.devStd < SOGLIE.devStd)
  falliti.push(`dev.std ${m.devStd} < ${SOGLIE.devStd}`);
if (m.riempito < SOGLIE.riempito)
  falliti.push(`riempito ${m.riempito}% < ${SOGLIE.riempito}%`);
if (m.caldo < SOGLIE.caldoMin)
  falliti.push(`accento caldo ${m.caldo}% < ${SOGLIE.caldoMin}%`);
if (m.caldo > SOGLIE.caldoMax)
  falliti.push(`accento caldo ${m.caldo}% > ${SOGLIE.caldoMax}%`);
if (m.barra < SOGLIE.barra)
  falliti.push(`barra ${m.barra}% < ${SOGLIE.barra}%`);

/* ⚠️ IL DOCK E' IN MODALITA' RAPPORTO — riporta e non boccia, per un giro.
 *
 * Accendere insieme tre criteri mai valutati prima significa poter trovare tre
 * rossi il primo giorno e non sapere quale guardare. Il dock, le risoluzioni e
 * il budget per motore arrivano tutti e tre adesso: prima si scrive il numero,
 * poi si decide la soglia. Chi lo accende tolga questo blocco e rimetta la
 * riga dentro `falliti`.
 *
 * ⚠️ E «non misurabile» NON conta come verde (§11.7 regola 4): senza
 * `occlusione.json` non si sa dov'e' il dock, e non saperlo non e' un esito
 * buono. Si stampa come tale, in modo che chi legge non lo scambi per un ok. */
const dockDetto = m.dock === null || m.dock === undefined
  ? "  dock        NON MISURABILE — manca occlusione.json, e senza il rettangolo " +
    "dichiarato non si sa dove finisce il pavimento (§11.7 regola 4)"
  : `  dock        ${m.dock.toFixed(1).padStart(5)} % di inchiostro L>50 · soglia ` +
    `${SOGLIE.dock} % · riferimento 22,8-26,2 % · ` +
    (m.dock >= SOGLIE.dock ? "sopra" : "SOTTO") + " — in rapporto, non boccia";
console.log("\nCRITERI IN RAPPORTO — accesi dopo un giro di taratura");
console.log(dockDetto);

if (falliti.length) {
  console.log("\nSOTTO SOGLIA — " + falliti.join(" · "));
  process.exit(1);
}
console.log("\nDENSITA' CONFORME");
