/* Board investigativa — SPEC §11.4, riferimento famiglia-a/09-board-investigativa-3d.
 *
 * Carte a profondita' e angoli diversi, non in griglia, con chip-etichetta
 * rossi. E' il secondo dei due motivi che §11.4 assegna al CSS 3D, e per la
 * stessa ragione del primo: le carte contengono testo, immagini e — qui — una
 * `<webview>` viva. In three.js sarebbe tutto rasterizzato, sfocato e
 * inselezionabile, e la webview non ci starebbe affatto.
 *
 * ── Il criterio di §22 ─────────────────────────────────────────────────────
 * «La board 3D contiene testo selezionabile e una `<webview>` viva.» Sono due
 * cose e si verificano separatamente: la selezione con `getSelection()`, la
 * webview nella finestra Electron vera (nella galleria l'elemento non esiste,
 * e il pannello lo dichiara invece di fingere).
 *
 * ── Le posizioni sono progettate, non casuali ──────────────────────────────
 * §11.6 regola 6: l'asimmetria e' un parametro con un nome. La tabella qui
 * sotto e' quella tabella. `Math.random()` darebbe una board diversa a ogni
 * apertura, cioe' nessuna memoria di dove sta una carta — che e' esattamente
 * cio' che serve a una board.
 *
 * ── clip-path annidato (R50) ───────────────────────────────────────────────
 * Come per i piani: `.brd__carta` porta la trasformazione 3D, `.brd__faccia`
 * dentro di lei porta il taglio a 45 gradi. Fonderli appiattirebbe tutto.
 */

export const meta = { nome: "board", versione: "1" };

/** Dove sta ogni carta. Sei posti, nessuno allineato all'altro. */
const POSTI = [
  { x: -320, y: -150, z: 60, ry: 12, rx: -4, larghezza: 300 },
  { x: 40, y: -190, z: -120, ry: -8, rx: 5, larghezza: 280 },
  { x: 330, y: -60, z: 20, ry: -16, rx: -3, larghezza: 300 },
  { x: -360, y: 130, z: -90, ry: 14, rx: 6, larghezza: 280 },
  { x: -20, y: 160, z: 100, ry: -5, rx: -6, larghezza: 320 },
  // La carta viva e' piu' alta delle altre — contiene un riquadro, non tre
  // righe — e va collocata piu' in su, o esce dal palco. Lo screenshot la
  // mostrava tagliata dal bordo inferiore.
  { x: 320, y: 96, z: -40, ry: -13, rx: 4, larghezza: 300 },
];

export const css = `
.brd {
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 6);
  background: var(--bg-deep);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
  --aug-tr: var(--s-3);
  --aug-border-bg: var(--cy-900);
}
.brd__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.brd__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.brd__id, .brd__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.brd__ctrl { letter-spacing: 0.16em; }

.brd__palco {
  position: relative;
  perspective: 2000px;
  transform-style: preserve-3d;
  min-height: 0;
  overflow: hidden;
}
.brd__carta {
  position: absolute;
  top: 50%;
  left: 50%;
  width: var(--larghezza);
  transform-style: preserve-3d;
  /* --scala la calcola adatta() dopo il disegno: la disposizione delle
     carte e' in pixel dal centro, e su una scrivania la cornice non ha piu'
     la dimensione della cella di galleria. Senza, le carte in alto e in basso
     escono dal pannello — si e' visto al primo scatto di §13. */
  transform: translate(-50%, -50%)
             scale(var(--scala, 1))
             translate3d(var(--x), var(--y), var(--z))
             rotateY(var(--ry)) rotateX(var(--rx));
  will-change: transform;
}
.brd__faccia {
  display: grid;
  gap: var(--s-2);
  padding: var(--s-3);
  background: var(--bg-panel);
  border: var(--line-hair) solid var(--cy-700);
  border-radius: var(--radius);
}
/* Il chip-etichetta rosso del riferimento. E' l'unico caldo della board, ed e'
   semantico: dice a quale fase appartiene la carta. Sei chip su una board di
   sei carte restano molto sotto il 10% della superficie (§11.6 regola 2). */
.brd__chip {
  justify-self: start;
  padding: 0 var(--s-1);
  background: var(--rust);
  color: var(--bg-void);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.16em;
}
.brd__titolo {
  font-size: var(--t-label);
  line-height: 1.3;
  color: var(--txt-primary);
}
.brd__corpo {
  font-size: var(--t-micro);
  line-height: 1.5;
  color: var(--txt-dim);
  user-select: text;
}
.brd__quota {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding-top: var(--s-1);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}

/* La carta viva. Il riquadro ha un'altezza sua: una webview senza altezza
   esplicita collassa a zero dentro una griglia. */
.brd__vivo { height: calc(var(--grid) * 1.2); background: var(--bg-void); overflow: hidden; }
.brd__vivo webview { width: 100%; height: 100%; border: 0; display: flex; }
.brd__assente {
  display: grid;
  place-content: center;
  height: 100%;
  padding: var(--s-2);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}

.brd__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.brd__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.brd[data-stato="vuoto"] .brd__palco { display: none; }
.brd[data-stato="vuoto"] .brd__vuoto { display: block; }
`;

/** Come in `panels/browser.js`: `<webview>` si riconosce dai suoi metodi. */
function webviewDisponibile() {
  const e = document.createElement("webview");
  return typeof e.loadURL === "function" || typeof e.getWebContentsId === "function";
}

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "brd";
  radice.dataset.augmentedUi = "tr-clip bl-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="brd__testa">
      <span class="brd__etichetta">Board investigativa</span>
      <span class="brd__id">BRD_J10 · ver ${meta.versione}</span>
      <span class="brd__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="brd__palco"></div>
    <div class="brd__vuoto">NESSUNA CARTA SUL TAVOLO</div>
    <div class="brd__piede">
      <span class="brd__conteggio"></span>
      <span class="brd__vivastato"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const palco = radice.querySelector(".brd__palco");
  const disponibile = webviewDisponibile();
  let wv = null;

  function carta(posto, dentro) {
    const el = document.createElement("div");
    el.className = "brd__carta";
    for (const [k, v] of Object.entries(posto)) {
      if (k === "larghezza") el.style.setProperty("--larghezza", `${v}px`);
      else el.style.setProperty(`--${k}`, k === "x" || k === "y" || k === "z" ? `${v}px` : `${v}deg`);
    }
    const faccia = document.createElement("div");
    faccia.className = "brd__faccia";
    faccia.dataset.augmentedUi = "tl-clip border";
    faccia.append(...dentro);
    el.appendChild(faccia);
    palco.appendChild(el);
    return el;
  }

  function testo(tag, classe, contenuto) {
    const e = document.createElement(tag);
    e.className = classe;
    e.textContent = contenuto;
    return e;
  }

  /** La riga di quota in fondo a una carta: due campi, nessun markup. */
  function quota(sinistra, destra) {
    const q = document.createElement("div");
    q.className = "brd__quota";
    q.append(testo("span", "", sinistra), testo("span", "", destra));
    return q;
  }

  /**
   * Rimpicciolisce la scena finche' ci sta, e mai la ingrandisce.
   *
   * La disposizione delle carte e' in pixel dal centro (`POSTI`): e' una scelta
   * di Fase 6, giudicata in una cella da 1100x620. Sulla scrivania il pannello
   * ha la forma che gli da' il workspace, e una board che deborda non e' una
   * board — e' un difetto che si vede prima di ogni altra cosa.
   *
   * Si misura l'ingombro VERO delle carte, non quello calcolato dalle
   * costanti: l'altezza di una carta dipende da quanto testo porta.
   */
  function adatta() {
    const carte = [...palco.children];
    if (!carte.length) return;
    palco.style.setProperty("--scala", "1");
    const p = palco.getBoundingClientRect();
    if (p.width < 1 || p.height < 1) return;      // pannello nascosto
    let alto = Infinity, basso = -Infinity, sx = Infinity, dx = -Infinity;
    for (const c of carte) {
      const r = c.getBoundingClientRect();
      alto = Math.min(alto, r.top); basso = Math.max(basso, r.bottom);
      sx = Math.min(sx, r.left); dx = Math.max(dx, r.right);
    }
    const scala = Math.min(1, p.height / (basso - alto), p.width / (dx - sx));
    palco.style.setProperty("--scala", String(Math.floor(scala * 100) / 100));
  }

  /* Ogni volta che il palco cambia dimensione, e non solo quando arrivano i
   * dati. Legare l'adattamento a `requestAnimationFrame` dopo il disegno
   * sembrava bastare e non bastava: il pannello puo' essere ancora largo zero
   * quando i dati arrivano — nasce dentro WinBox, e su un'altra scrivania
   * nasce nascosto — e allora la misura non vale niente e non viene piu'
   * ripetuta. L'osservatore non ha questo problema: parla quando c'e'
   * qualcosa da misurare. */
  const osservatore = new ResizeObserver(() => adatta());
  osservatore.observe(palco);

  function disegna(note, url) {
    if (!note?.length) { radice.dataset.stato = "vuoto"; return; }
    radice.dataset.stato = "pieno";
    palco.replaceChildren();

    // Cinque carte di testo, e la sesta viva.
    const quante = Math.min(note.length, POSTI.length - 1);
    for (let i = 0; i < quante; i++) {
      const n = note[i];
      carta(POSTI[i], [
        testo("span", "brd__chip", n.file.replace(/\.md$/, "").replace("FASE-", "F")),
        testo("div", "brd__titolo", n.titolo),
        testo("div", "brd__corpo", n.corpo),
        quota(`${(n.byte / 1024).toFixed(1)} kB`, `carta ${i + 1}`),
      ]);
    }

    const vivo = document.createElement("div");
    vivo.className = "brd__vivo";
    if (disponibile) {
      wv = document.createElement("webview");
      wv.setAttribute("partition", "persist:jarvis");
      wv.setAttribute("allowpopups", "false");
      wv.setAttribute("src", url);
      vivo.appendChild(wv);
    } else {
      vivo.appendChild(
        testo("div", "brd__assente", "<webview> esiste solo dentro Electron")
      );
    }
    carta(POSTI[POSTI.length - 1], [
      testo("span", "brd__chip", "LIVE"),
      testo("div", "brd__titolo", "Sorgente viva"),
      vivo,
      // ⚠️ R96 — `url` arriva da `web.open`, e non e' nostro. `hostname` non
      // puo' contenere `<`, ma la regola non e' «questo valore e' innocuo»: e'
      // «in innerHTML entrano solo costanti del modulo». La prima formulazione
      // richiede di indovinare bene ogni volta, e una volta e' andata storta.
      quota(new URL(url).hostname, `carta ${POSTI.length}`),
    ]);

    radice.querySelector(".brd__conteggio").textContent =
      `${quante + 1} carte · ${POSTI.length} posti dichiarati`;
    radice.querySelector(".brd__vivastato").textContent =
      disponibile ? "webview viva" : "webview non disponibile fuori da Electron";
  }

  return {
    radice,
    /** @param {{topic:string, note:object[], url:string}} msg */
    aggiorna(msg) {
      if (msg?.topic !== "board.cards") return;
      disegna(msg.note, msg.url);
      // Due fotogrammi: il primo per il layout delle carte, il secondo perche'
      // `getBoundingClientRect` misuri l'altezza vera del testo. L'osservatore
      // copre il resto — questa e' la volta in cui i dati CAMBIANO.
      requestAnimationFrame(() => requestAnimationFrame(adatta));
    },
    adatta,
    smonta() { osservatore.disconnect(); },
    get webview() { return wv; },
  };
}
