/* Pannello news — SPEC §13, §15, riferimento famiglia-a/05-dashboard-news.
 *
 * Nel riferimento: lista di storie, un ticker rosso, e i numeri attorno. Qui
 * le storie sono quelle che hanno superato il gate di §15, e i numeri sono il
 * budget — quante interruzioni restano nell'ora.
 *
 * ── Ogni card dice DA DOVE VIENE ───────────────────────────────────────────
 * Non e' un dettaglio bibliografico: quel testo non e' di JARVIS. E' la stessa
 * logica del rettangolo della regione catturata di §12 e della spia della
 * telecamera di §14 — chi guarda deve sapere che sta leggendo parole di
 * qualcun altro, arrivate da sole.
 *
 * ── Il budget si vede ──────────────────────────────────────────────────────
 * Tre tacche, come l'isteresi del pannello gesture. §15 dice che senza queste
 * regole «abbandonera' la funzione in tre giorni»: mostrarne il residuo e'
 * l'unico modo di capire, guardando, perche' JARVIS non sta dicendo niente —
 * ha finito le interruzioni, non e' rotto.
 *
 * ── Il ticker rosso ────────────────────────────────────────────────────────
 * E' l'unico accento caldo del pannello, e lo porta solo quando c'e' una fonte
 * spenta o irraggiungibile. Nel riferimento il rosso e' decorazione; qui
 * significa «una sorgente non risponde» (§11.6 regola 2).
 */

export const meta = { nome: "news", versione: "1" };

const BUDGET = 3;         // §15
const MAX_CARD = 12;

export const css = `
.pnl-news {
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
.pnl-news__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-news__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-news__id, .pnl-news__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-news__ctrl { letter-spacing: 0.16em; }

/* Il budget di §15, a vista. */
.pnl-news__budget {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-bottom: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-news__tacche { display: flex; gap: var(--s-1); }
.pnl-news__tacca {
  width: var(--s-3);
  height: var(--line-bold);
  background: var(--cy-900);
}
.pnl-news__tacca[data-usata="1"] { background: var(--cy-500); }
.pnl-news__quando { flex: 1; text-align: right; }

.pnl-news__lista {
  display: grid;
  align-content: start;
  gap: var(--s-2);
  padding: var(--s-3);
  min-height: 0;
  overflow-y: auto;
}
.pnl-news__card {
  display: grid;
  gap: var(--s-1);
  padding: var(--s-2);
  background: var(--bg-raised);
  border-left: var(--line-bold) solid var(--cy-700);
  border-radius: var(--radius);
}
.pnl-news__riga {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-news__fonte { color: var(--cy-300); letter-spacing: 0.10em; }
/* Stesso inciampo del pannello gesture: un margine automatico ha un valore
   calcolato qualunque, e l'audit lo legge. Lo spazio lo fa crescere l'ora. */
.pnl-news__ora { flex: 1; }
.pnl-news__ril { color: var(--txt-ghost); }
.pnl-news__titolo {
  font-size: var(--t-label);
  line-height: 1.35;
  color: var(--txt-primary);
  user-select: text;
}
/* La provenienza. Non e' una citazione: e' un avviso. */
.pnl-news__origine {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}

.pnl-news__vuoto {
  display: none;
  place-content: center;
  padding: var(--s-4);
  text-align: center;
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-news[data-stato="vuoto"] .pnl-news__lista { display: none; }
.pnl-news[data-stato="vuoto"] .pnl-news__vuoto { display: grid; }

/* Il ticker: acceso solo quando una fonte non risponde. */
.pnl-news__ticker {
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--rust);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--rust);
}
.pnl-news__ticker:empty { display: none; }
.pnl-news__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
`;

const ora = (ts) =>
  ts ? new Date(ts * 1000).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })
     : "—";

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-news";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-news__testa">
      <span class="pnl-news__etichetta">News</span>
      <span class="pnl-news__id">NWS_L12 · ver ${meta.versione}</span>
      <span class="pnl-news__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-news__budget">
      <span>interruzioni</span>
      <span class="pnl-news__tacche"></span>
      <span class="pnl-news__resto"></span>
      <span class="pnl-news__quando"></span>
    </div>
    <div class="pnl-news__lista"></div>
    <div class="pnl-news__vuoto">
      NESSUNA NOTIZIA HA SUPERATO IL GATE<br>il silenzio e' una scelta, non un guasto
    </div>
    <div class="pnl-news__ticker"></div>
    <div class="pnl-news__piede">
      <span class="pnl-news__conteggio"></span>
      <span class="pnl-news__argomenti"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const lista = radice.querySelector(".pnl-news__lista");
  const tacche = radice.querySelector(".pnl-news__tacche");
  for (let i = 0; i < BUDGET; i++) {
    const t = document.createElement("i");
    t.className = "pnl-news__tacca";
    tacche.appendChild(t);
  }

  let usate = 0;
  let mostrate = 0;

  function card(msg) {
    const el = document.createElement("article");
    el.className = "pnl-news__card";
    el.innerHTML = `
      <div class="pnl-news__riga">
        <span class="pnl-news__fonte"></span>
        <span class="pnl-news__ora"></span>
        <span class="pnl-news__ril"></span>
      </div>
      <div class="pnl-news__titolo"></div>
      <div class="pnl-news__origine"></div>
    `;
    // `textContent` e non `innerHTML`: il titolo viene da un feed, cioe' da un
    // estraneo. Comporlo come HTML vorrebbe dire dargli un modo di scrivere
    // markup dentro l'interfaccia — non esecuzione (il CSP la vieta), ma
    // abbastanza per fingere un elemento di JARVIS.
    el.querySelector(".pnl-news__fonte").textContent = msg.fonte ?? "?";
    el.querySelector(".pnl-news__ora").textContent = ora(msg.pubblicato);
    el.querySelector(".pnl-news__ril").textContent =
      `ril ${(msg.rilevanza ?? 0).toFixed(2)}`;
    el.querySelector(".pnl-news__titolo").textContent = msg.titolo ?? "";
    el.querySelector(".pnl-news__origine").textContent =
      `testo non nostro · ${msg.origine_non_fidata ?? "origine ignota"}`;
    return el;
  }

  function aggiornaBudget() {
    for (const [i, t] of [...tacche.children].entries()) {
      t.dataset.usata = i < usate ? "1" : "0";
    }
    radice.querySelector(".pnl-news__resto").textContent =
      `${Math.max(0, BUDGET - usate)}/${BUDGET} nell'ora`;
  }

  aggiornaBudget();

  return {
    radice,
    /** @param {{topic:string}} msg  `news.card` oppure `agent.advisory` */
    aggiorna(msg) {
      if (msg?.topic === "news.card") {
        radice.dataset.stato = "pieno";
        lista.insertBefore(card(msg), lista.firstChild);
        while (lista.children.length > MAX_CARD) lista.lastChild.remove();
        mostrate += 1;
        usate = Math.min(BUDGET, usate + 1);
        aggiornaBudget();
        radice.querySelector(".pnl-news__quando").textContent =
          new Date().toLocaleTimeString("it-IT", { hour12: false });
        radice.querySelector(".pnl-news__conteggio").textContent =
          `${mostrate} card · ${lista.children.length} in lista`;
        return;
      }
      if (msg?.topic === "agent.advisory" && msg.reason === "fonti news non disponibili") {
        radice.querySelector(".pnl-news__ticker").textContent =
          (msg.dettaglio ?? []).join("  ·  ");
        return;
      }
      if (msg?.topic === "news.argomenti") {
        radice.querySelector(".pnl-news__argomenti").textContent =
          (msg.argomenti ?? []).length
            ? `argomenti: ${msg.argomenti.join(", ")}`
            : "nessun argomento attivo";
      }
    },
  };
}
