/* Glifi esadecimali — SPEC §11.5, riferimento famiglia-a/01-desktop-mcu-completo.
 *
 * Nel riferimento sono i blocchi di esadecimale che scorrono ai bordi dello
 * schermo. Qui sono i BYTE VERI che passano sul canale core -> renderer: ogni
 * coppia di cifre e' un byte di un messaggio davvero arrivato, e la colonna
 * scorre quando ne arrivano altri. §11.9: nessun numero inventato.
 *
 * ── Perche' qui il testo NON e' nel DOM ────────────────────────────────────
 * L'invariante 20 dice che il testo vive nel DOM e non si rasterizza in WebGL,
 * e §11.8 lo chiede in checklist. Ma §11.4 — la stessa sezione che enuncia la
 * regola — assegna esplicitamente «glifi di massa e log scorrevoli» a PixiJS,
 * e §22 mette «glifi (PixiJS)» in questa fase.
 *
 * La riga che divide i due casi e' nella §11.4 stessa: il testo che si LEGGE
 * (pannelli, tabelle, documenti, etichette) deve restare selezionabile e
 * nitido, quindi DOM; una massa di mille glifi non si legge, si GUARDA — e'
 * una texture che misura quanto traffico sta passando. Mille `<span>` che
 * scorrono non stanno in 3 ms, e nessuno li selezionerebbe mai.
 *
 * E' per la stessa distinzione che le etichette del globo e della nuvola sono
 * DOM proiettato e non troika: quelle si leggono.
 */

import { Application, BitmapFont, BitmapText, Container } from "../../vendor/pixi.min.mjs";
/* ⚠️ PRIMA di qualunque `Application`. PixiJS v8 genera a runtime il codice
 * che sincronizza uniform e shader, e lo fa con `new Function()`: il CSP
 * dell'app non ha `unsafe-eval` e non deve averlo — il renderer ospita
 * `<webview>` con contenuto non fidato (Fase 6). Questo modulo sostituisce i
 * generatori con versioni interpretate; vedi `scripts/vendor.mjs`.
 *
 * Senza, in Electron `app.init()` solleva e il pannello resta a «0 byte»
 * senza un errore in console: la promessa che lo porta non la guarda nessuno.
 * E' successo, ed e' rimasto invisibile per tutta la Fase 5 perche' la
 * galleria non aveva un CSP. */
import "../../vendor/pixi-unsafe-eval/init.mjs";
import { tok } from "../style/tokens.js";

export const meta = { nome: "glyphs", versione: "1" };

const CORPO = 11;        // px, = --t-data
const PASSO_X = 20;      // px fra un byte e il successivo
const PASSO_Y = 15;
const MARGINE = 8;       // px, = --s-2

/** Le quattro eta': dal byte appena arrivato a quello che sta per uscire.
 *
 * Il gradino piu' scuro e' `--cy-700` e non `--cy-900`: misurando lo scatto,
 * le righe in `--cy-900` avevano luminanza 18 su 255 contro il fondo del
 * pannello — c'erano ma non si vedevano, e un dato che non si vede non e' un
 * dato. Il riferimento ha esadecimale leggibile, non un'ombra. */
const ETA = ["--cy-100", "--cy-300", "--cy-500", "--cy-700"];

const FONT = "glifi-mono";

export const css = `
.pnl-gly {
  --aug-bl: var(--s-3);
  --aug-border-bg: var(--cy-900);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-gly__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-gly__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-gly__id, .pnl-gly__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-gly__ctrl { letter-spacing: 0.16em; }
.pnl-gly__tela { position: relative; min-height: 0; overflow: hidden; }
.pnl-gly__tela canvas { display: block; }
.pnl-gly__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-gly__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-gly[data-stato="vuoto"] .pnl-gly__tela { display: none; }
.pnl-gly[data-stato="vuoto"] .pnl-gly__vuoto { display: block; }
`;

const esa = (b) => b.toString(16).padStart(2, "0").toUpperCase();

export async function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-gly";
  radice.dataset.augmentedUi = "bl-clip tr-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-gly__testa">
      <span class="pnl-gly__etichetta">Traffico sul canale</span>
      <span class="pnl-gly__id">HEX_F06 · ver ${meta.versione}</span>
      <span class="pnl-gly__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-gly__tela"></div>
    <div class="pnl-gly__vuoto">NESSUNA SORGENTE COLLEGATA</div>
    <div class="pnl-gly__piede">
      <span class="pnl-gly__byte">0 byte</span>
      <span class="pnl-gly__glifi"></span>
    </div>
  `;
  ospite.appendChild(radice);
  const tela = radice.querySelector(".pnl-gly__tela");

  /* Tutto il resto nasce al PRIMO byte, non all'apertura.
   *
   * Due ragioni, e la prima l'ha trovata lo screenshot: finche' il pannello e'
   * senza sorgente la tela sta a `display: none`, e misurarla da' zero — la
   * prima versione costruiva una griglia di 1x1 glifi. La seconda e' che un
   * pannello senza sorgente non deve tenere aperto un contesto WebGL. */
  let app = null;
  //: L'avvio e' UNO SOLO, e chi arriva mentre e' in corso lo aspetta.
  //:
  //: `new Application()` assegna `app` PRIMA che `app.init()` abbia
  //: finito. Nella galleria non si vedeva — il mount chiama `aggiungi` una
  //: volta e la aspetta — ma sulla scrivania i messaggi arrivano a raffica: il
  //: secondo trovava `app` non nullo, saltava l'avvio, e chiamava `render()`
  //: su un renderer che non esisteva ancora. L'eccezione finiva in una
  //: promessa che nessuno guardava, e il pannello restava a «0 byte» con il
  //: core acceso e nessun errore in console.
  let avvio = null;
  let griglia = null;
  let celle = [];
  let COLONNE = 0;
  let RIGHE = 0;
  let tinte = [];
  const buffer = [];
  let totale = 0;

  async function avvia() {
    // Il font atlante si genera a runtime dal font gia' caricato: nessun asset
    // da spedire, e resta IBM Plex Mono come tutto il resto dei numeri (§11.6
    // regola 1). Bianco nell'atlante, colorato per tinta: cosi' i colori
    // restano quelli dei token e non finiscono cotti dentro una texture.
    BitmapFont.install({
      name: FONT,
      style: {
        fontFamily: tok("--font-mono").split(",")[0].replace(/["']/g, ""),
        fontSize: CORPO,
        // BIANCO, e non e' un colore letterale: e' il neutro dell'atlante.
        // La tinta MOLTIPLICA, quindi con l'atlante nero — che e' il
        // riempimento predefinito di PixiJS — ogni tinta dava nero, e il
        // campo risultava invisibile sul fondo del pannello. I colori veri
        // arrivano dopo, da `tok()`, come tinta.
        fill: 0xffffff,
      },
      chars: "0123456789ABCDEF",
      // L'atlante va generato alla risoluzione dello schermo. Generato a 1x e
      // poi scalato a 2x dal renderer, nessun pixel del glifo risultava
      // pienamente coperto e l'intero campo si smorzava.
      resolution: Math.min(window.devicePixelRatio || 1, 2),
    });

    const { larghezza, altezza } = misura();
    COLONNE = Math.max(1, Math.floor((larghezza - MARGINE * 2) / PASSO_X));
    RIGHE = Math.max(1, Math.floor((altezza - MARGINE * 2) / PASSO_Y));

    const nuova = new Application();
    await nuova.init({
      canvas: document.createElement("canvas"),
      backgroundAlpha: 0,        // il fondo lo dipinge il CSS: invariante 18
      antialias: false,          // glifi allineati ai pixel: piu' nitidi e piu' veloci
      autoStart: false,          // niente ticker perpetuo: si rende su evento (inv. 25)
      autoDensity: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      width: larghezza,
      height: altezza,
    });
    // `app` si assegna solo ADESSO: prima di `init()` non e' utilizzabile.
    app = nuova;
    tela.appendChild(app.canvas);

    tinte = ETA.map((t) => tok(t));
    costruisciGriglia();
    osservatore.observe(tela);
  }

  /** La dimensione utile della tela, mai sotto un glifo. */
  function misura() {
    const r = tela.getBoundingClientRect();
    return {
      larghezza: Math.max(PASSO_X, Math.floor(r.width)),
      altezza: Math.max(PASSO_Y, Math.floor(r.height)),
    };
  }

  /* Tutti i glifi esistono da subito e non vengono mai creati o distrutti
   * MENTRE si scorre: scorrere vuol dire riscrivere il testo, non ricostruire
   * la scena. Si ricostruisce solo quando la griglia cambia forma. */
  function costruisciGriglia() {
    griglia?.destroy({ children: true });
    griglia = new Container();
    app.stage.addChild(griglia);
    celle = [];
    for (let riga = 0; riga < RIGHE; riga++) {
      const r2 = [];
      for (let c = 0; c < COLONNE; c++) {
        const g = new BitmapText({ text: "", style: { fontFamily: FONT, fontSize: CORPO } });
        g.x = MARGINE + c * PASSO_X;
        g.y = MARGINE + riga * PASSO_Y;
        griglia.addChild(g);
        r2.push(g);
      }
      celle.push(r2);
    }
    radice.querySelector(".pnl-gly__glifi").textContent =
      `${RIGHE * COLONNE} glifi · ${RIGHE}x${COLONNE}`;
  }

  /* §13: sulla scrivania un pannello si ridimensiona — si affianca, si
   * massimizza, si aggancia a meta'. Era l'UNICO dei quattordici componenti a
   * non sopravvivere: la griglia si misurava una volta sola all'avvio, e dopo
   * un ridimensionamento restava della forma vecchia dentro una tela nuova.
   *
   * ⚠️ La misura zero si IGNORA. WinBox nasconde con `display: none`, e li'
   * `getBoundingClientRect()` da' zero: senza questa guardia, cambiare
   * workspace ridurrebbe il campo a un glifo — che e' esattamente il difetto
   * che la Fase 5 aveva gia' trovato una volta. */
  const osservatore = new ResizeObserver(() => {
    if (app === null) return;
    const r = tela.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const { larghezza, altezza } = misura();
    const colonne = Math.max(1, Math.floor((larghezza - MARGINE * 2) / PASSO_X));
    const righe = Math.max(1, Math.floor((altezza - MARGINE * 2) / PASSO_Y));
    app.renderer.resize(larghezza, altezza);
    if (colonne === COLONNE && righe === RIGHE) { app.render(); return; }
    COLONNE = colonne;
    RIGHE = righe;
    costruisciGriglia();
    ridisegna();
  });

  function ridisegna() {
    for (let r = 0; r < RIGHE; r++) {
      const riga = buffer[buffer.length - RIGHE + r];
      // Piu' una riga e' vecchia, piu' e' spenta: l'eta' e' un dato.
      const eta = Math.min(ETA.length - 1, Math.floor(((RIGHE - 1 - r) / RIGHE) * ETA.length));
      for (let c = 0; c < COLONNE; c++) {
        const g = celle[r][c];
        g.text = riga && c < riga.length ? esa(riga[c]) : "";
        g.tint = tinte[eta];
      }
    }
    app.render();
  }

  return {
    radice,
    /** @param {Uint8Array} byte  byte VERI, non generati */
    async aggiungi(byte) {
      if (!byte?.length) return;
      radice.dataset.stato = "pieno";
      if (avvio === null) avvio = avvia();
      await avvio;
      totale += byte.length;
      for (let i = 0; i < byte.length; i += COLONNE) {
        buffer.push(byte.subarray(i, i + COLONNE));
      }
      // Il buffer non cresce all'infinito: quello che e' uscito dallo schermo
      // non serve piu' a nessuno.
      if (buffer.length > RIGHE * 2) buffer.splice(0, buffer.length - RIGHE);
      ridisegna();
      radice.querySelector(".pnl-gly__byte").textContent =
        `${totale.toLocaleString("it-IT")} byte · ${buffer.length} righe in memoria`;
    },
    smonta() { osservatore.disconnect(); app?.destroy(true, { children: true }); },
  };
}
