/* Pannello browser — SPEC §6.3, riferimento famiglia-a/07-griglia-9up-con-web-incassato.
 *
 * Nel riferimento le pagine web sono DENTRO i riquadri, con la barra
 * dell'indirizzo visibile. §11.1 lo nota come dettaglio decisivo: «nel desktop
 * Iron Man 2 sono incassate pagine web reali — la barra URL di YouTube e'
 * visibile in uno dei riquadri». Non e' un'approssimazione dell'effetto, e'
 * l'effetto.
 *
 * ── La barra mostra l'URL RISOLTO ──────────────────────────────────────────
 * Stessa disciplina di §6.2 sui percorsi: cio' che accade dev'essere cio' che
 * si legge. L'URL non arriva da qui — lo valida e lo normalizza
 * `core/tools/web.py` — e questo pannello mostra quello che il core ha
 * deciso, non quello che l'utente ha detto. Un accorciatore o un redirect si
 * vedono nella barra.
 *
 * ── YouTube senza script di terzi ──────────────────────────────────────────
 * §6.3 dice di usare l'IFrame Player API e non il DOM di youtube.com, «il DOM
 * cambia, l'API no». Il contratto dell'IFrame API sono i PARAMETRI dell'URL di
 * embed: caricare `youtube-nocookie.com/embed/<id>?autoplay=1&enablejsapi=1`
 * nella webview e' usare quell'API. Caricare invece il loader
 * `youtube.com/iframe_api` vorrebbe dire allargare il CSP della finestra a
 * `script-src https://www.youtube.com`, cioe' far eseguire script di terzi
 * nel documento che ospita il preload. Non vale il prezzo.
 *
 * ── Fuori da Electron ──────────────────────────────────────────────────────
 * `<webview>` esiste solo in Electron. Nella galleria il pannello mostra uno
 * stato esplicito invece di fingere: §11.9 vale anche per se stessi.
 */

export const meta = { nome: "browser", versione: "1" };

const PARTIZIONE = "persist:jarvis";
const EMBED = "https://www.youtube-nocookie.com/embed/";

export const css = `
.pnl-web {
  --aug-tl: var(--s-3);
  --aug-br: var(--s-3);
  --aug-border-bg: var(--cy-900);
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 4);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-web__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-web__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-web__id, .pnl-web__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-web__ctrl { letter-spacing: 0.16em; }

/* La barra dell'indirizzo. Il testo e' selezionabile: chi vuole controllare
   dove sta andando deve poterlo copiare. */
.pnl-web__barra {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
  background: var(--bg-raised);
}
.pnl-web__schema {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--cy-700);
}
.pnl-web__url {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-primary);
  user-select: text;
}
.pnl-web__fase {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-dim);
}
.pnl-web[data-fase="carica"] .pnl-web__fase { color: var(--amber); }
.pnl-web[data-fase="errore"] .pnl-web__fase { color: var(--rust); }

.pnl-web__tela { position: relative; min-height: 0; overflow: hidden; }
.pnl-web__tela webview { width: 100%; height: 100%; border: 0; display: flex; }

.pnl-web__vuoto {
  display: none;
  place-content: center;
  justify-items: center;
  gap: var(--s-2);
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  text-align: center;
  color: var(--txt-ghost);
}
.pnl-web[data-stato="vuoto"] .pnl-web__tela { display: none; }
.pnl-web[data-stato="vuoto"] .pnl-web__vuoto { display: grid; }

.pnl-web__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
/* L'annuncio del ripiego: quando non si e' fatto cio' che era stato chiesto,
   si dice. Stessa regola del ripiego vocale di §7.4. */
.pnl-web__annuncio {
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--amber);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--amber);
}
.pnl-web__annuncio:empty { display: none; }
`;

/** `<webview>` esiste solo in Electron, e si riconosce dai suoi metodi. */
export function webviewDisponibile() {
  const e = document.createElement("webview");
  return typeof e.loadURL === "function" || typeof e.getWebContentsId === "function";
}

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-web";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.dataset.fase = "inerte";
  radice.innerHTML = `
    <div class="pnl-web__testa">
      <span class="pnl-web__etichetta">Browser</span>
      <span class="pnl-web__id">WEB_H08 · ver ${meta.versione}</span>
      <span class="pnl-web__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-web__barra">
      <span class="pnl-web__schema">https</span>
      <span class="pnl-web__url">—</span>
      <span class="pnl-web__fase">inerte</span>
    </div>
    <div class="pnl-web__tela"></div>
    <div class="pnl-web__vuoto">
      <span>NESSUNA PAGINA APERTA</span>
      <span class="pnl-web__perche"></span>
    </div>
    <div class="pnl-web__annuncio"></div>
    <div class="pnl-web__piede">
      <span class="pnl-web__sessione">partizione ${PARTIZIONE}</span>
      <span class="pnl-web__tempo"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const tela = radice.querySelector(".pnl-web__tela");
  const elUrl = radice.querySelector(".pnl-web__url");
  const elFase = radice.querySelector(".pnl-web__fase");
  const elAnnuncio = radice.querySelector(".pnl-web__annuncio");
  const elTempo = radice.querySelector(".pnl-web__tempo");
  const elPerche = radice.querySelector(".pnl-web__perche");

  const disponibile = webviewDisponibile();
  if (!disponibile) {
    elPerche.textContent = "<webview> esiste solo dentro Electron";
  }

  let wv = null;
  let t0 = 0;

  function fase(nome) {
    radice.dataset.fase = nome;
    elFase.textContent = nome;
  }

  function apri(url) {
    elUrl.textContent = url;
    if (!disponibile) { radice.dataset.stato = "vuoto"; fase("inerte"); return; }

    radice.dataset.stato = "pieno";
    if (wv === null) {
      wv = document.createElement("webview");
      // Gli stessi attributi che §6.3 prescrive. Il processo principale li
      // riscrive comunque in `will-attach-webview`: qui sono la dichiarazione,
      // li' sono la garanzia.
      wv.setAttribute("partition", PARTIZIONE);
      wv.setAttribute("allowpopups", "false");
      wv.addEventListener("did-start-loading", () => { t0 = performance.now(); fase("carica"); });
      wv.addEventListener("did-stop-loading", () => {
        fase("pronto");
        elTempo.textContent = `${Math.round(performance.now() - t0)} ms`;
      });
      wv.addEventListener("did-fail-load", (e) => {
        // -3 e' ERR_ABORTED: succede a ogni redirect e non e' un guasto.
        if (e.errorCode === -3) return;
        fase("errore");
        elTempo.textContent = `${e.errorCode} ${e.errorDescription ?? ""}`.trim();
      });
      tela.appendChild(wv);
    }
    wv.setAttribute("src", url);
  }

  return {
    radice,
    /** @param {{topic:string}} msg  `web.open` oppure `youtube.play` */
    aggiorna(msg) {
      if (msg?.topic === "web.open") {
        elAnnuncio.textContent = msg.annuncio ?? "";
        apri(msg.url);
        return;
      }
      if (msg?.topic === "youtube.play") {
        elAnnuncio.textContent = msg.annuncio ?? "";
        // I parametri SONO l'IFrame Player API: nessuno script di terzi nel
        // documento che ospita il preload.
        apri(`${EMBED}${encodeURIComponent(msg.video_id)}?autoplay=1&enablejsapi=1&rel=0`);
        elUrl.textContent = `${EMBED}${msg.video_id} · ${msg.titolo ?? ""}`.trim();
      }
    },
    get webview() { return wv; },
  };
}
