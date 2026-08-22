/* Grande lettura numerica — riferimento famiglia-a/03, la fascia in alto.
 *
 * ## Il numero e' il pannello
 *
 * In «03» la lettura «209. 054. - 205. 579. 265. 287 [ECI-5]» sta a
 * x 322..660, y 30..70: 338 x 40 px. Le cifre sono alte **28 px su 40**, cioe'
 * il 70 % dell'altezza del pannello, e sotto corre una riga di micro a 8 px.
 * Non e' un pannello con un numero grande dentro: e' un numero, con
 * un'etichetta.
 *
 * Tre cose, misurate:
 *
 * 1. **Le cifre sono RAGGRUPPATE.** Nel riferimento i gruppi sono separati da
 *    un punto e da uno spazio. Un numero di dodici cifre senza gruppi non si
 *    legge, si conta — ed e' la ragione per cui il raggruppamento e' l'unica
 *    cosa non decorativa in una lettura grande.
 *
 * 2. **La chiave e' fra parentesi quadre, a destra e piccola.** Dice di che
 *    cosa e' quel numero, e non compete con lui.
 *
 * 3. **La riga sotto e' la PROVENIENZA**, in micro: nel riferimento e'
 *    «00: 81: 00 11112». Una lettura senza provenienza e' un fatto senza
 *    fonte, e §11.9 lo vieta.
 *
 * ## ⚠️ La scala tipografica non ha un gradino di DISPLAY, e va detto
 *
 * §11.6 regola 1 fissa cinque corpi: 8,5 / 11 / 12 / 14 / 20. Il piu' grande
 * e' --t-title, 20 px, che nel riferimento e' il corpo dei NUMERI DI UNA
 * CELLA del calendario, non di una lettura. Il numero grande di «03» sta a
 * 28 px su un'immagine larga 901: e' il 3,1 % della larghezza, che sui nostri
 * 1536 fa 48 px.
 *
 * La prima stesura lo derivava qui — «calc(var(--t-title) * 2.4)» — e aveva
 * ragione sul numero e torto sul posto: una moltiplicazione dentro un
 * componente e' un gradino che nessuno puo' contestare perche' nessuno lo
 * vede. L'audit infatti la leggeva come 48 px letterali e la bocciava.
 * Adesso e' **--t-display**, il sesto gradino, dichiarato in tokens.css con
 * accanto la misura da cui viene. Chi volesse tornare a cinque riporti questa
 * riga a --t-title sapendo che perde il 3,1 % misurato.
 */

import { contatore } from "../anim/counters.js";

export const meta = { nome: "lettura", versione: "1" };

/** hh:mm:ss da secondi. */
function orologio(s) {
  const n = Math.max(0, Math.round(s));
  const p = (x) => String(x).padStart(2, "0");
  return `${p((n / 3600) | 0)}:${p(((n / 60) | 0) % 60)}:${p(n % 60)}`;
}

/** Raggruppa a tre cifre col punto, come nel riferimento. */
function gruppi(n) {
  return String(Math.max(0, Math.round(n))).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export const css = `
.pnl-let {
  --aug-br: var(--s-3);
  --aug-border-bg: transparent;
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-let__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
.pnl-let__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-let__id, .pnl-let__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  white-space: nowrap;
  color: var(--icona);
}
.pnl-let__ctrl { letter-spacing: 0.16em; }

.pnl-let__corpo {
  display: grid;
  align-content: center;
  gap: var(--s-2);
  padding: var(--s-3);
  min-height: 0;
}
/* Il RITAGLIO ORIZZONTALE sta sulla riga, non sul numero: vedi
   .pnl-let__valore. */
.pnl-let__riga {
  display: flex;
  align-items: baseline;
  gap: var(--s-3);
  overflow: hidden;
}
/* La lettura PRINCIPALE. Vedi l'intestazione per il perche' del fattore. */
.pnl-let__valore {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--t-display);
  /* ⚠️ NON line-height: 1, e non e' una preferenza tipografica.
     Plex Mono ha un'area di contenuto di ~1,31 em: a interlinea 1 la riga e'
     alta esattamente 1 em e le cifre sporgono di 15 px, e l'overflow: hidden
     che stava qui per tagliare in ORIZZONTALE tagliava anche in verticale —
     misurato, otto px in cima e sette sotto sul numero da 48. Il rapporto e'
     del font, non del corpo, quindi rimpicciolire non lo avrebbe risolto.
     1,35 contiene l'area di contenuto con un margine, e vale per entrambe le
     letture perche' la seconda cambia solo il corpo.
     Il ritaglio orizzontale sale sulla RIGA, che e' il posto giusto: e' lei che
     ha una larghezza da rispettare, il numero no. */
  line-height: 1.35;
  letter-spacing: 0.02em;
  color: var(--cy-100);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
/* La seconda lettura sta un gradino sotto: due numeri della stessa taglia
   sarebbero due pannelli in uno. */
.pnl-let__riga[data-rango="2"] .pnl-let__valore {
  font-size: var(--t-title);
  color: var(--cy-300);
}
/* La chiave: fra quadre, piccola, a destra. Dice di che cosa e' il numero. */
.pnl-let__chiave {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--icona);
  white-space: nowrap;
}
.pnl-let__unita {
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-ghost);
}
/* La provenienza: sotto, in micro, sempre presente. */
.pnl-let__fonte {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
  border-top: var(--line-hair) solid var(--cy-900);
  padding-top: var(--s-1);
}
/* Le tacche di stato: la stessa fila di --fill-1 della barra, qui a dire
   quali campi della lettura sono vivi. Un riquadro spento vuol dire «questo
   dato non c'e'», mai un trattino su fondo acceso (invariante 23). */
.pnl-let__campi {
  display: flex;
  gap: var(--s-1);
  flex-wrap: wrap;
}
.pnl-let__campo {
  display: flex;
  align-items: baseline;
  gap: var(--s-1);
  padding: var(--s-1);
  background: var(--fill-1);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.pnl-let__campo[data-vuoto] { background: var(--bg-raised); }
.pnl-let__et { color: var(--icona); text-transform: uppercase; }
.pnl-let__vl { color: var(--txt-primary); }
.pnl-let__campo[data-vuoto] .pnl-let__vl { color: var(--txt-ghost); }

.pnl-let__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  white-space: nowrap;
  overflow: hidden;
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-let__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-let[data-stato="vuoto"] .pnl-let__corpo { display: none; }
.pnl-let[data-stato="vuoto"] .pnl-let__vuoto { display: block; }
`;

const HTML = `
<section class="pnl-let" data-stato="vuoto" data-augmented-ui="br-clip border">
  <header class="pnl-let__testa">
    <span class="pnl-let__etichetta">Lettura core</span>
    <span class="pnl-let__id">LET_C01 &middot; ver ${meta.versione}</span>
    <span class="pnl-let__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-let__corpo">
    <div class="pnl-let__riga" data-rango="1">
      <span class="pnl-let__valore" data-v="uptime">--:--:--</span>
      <span class="pnl-let__chiave">[uptime]</span>
    </div>
    <div class="pnl-let__riga" data-rango="2">
      <span class="pnl-let__valore" data-v="rx">0</span>
      <span class="pnl-let__unita">byte sul socket</span>
      <span class="pnl-let__chiave">[rx]</span>
    </div>
    <div class="pnl-let__campi"></div>
    <div class="pnl-let__fonte" data-fonte></div>
  </div>
  <div class="pnl-let__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-let__piede">
    <span data-conteggio></span>
    <span data-ora>--:--:--</span>
  </footer>
</section>
`;

/** I campi della lettura, e da dove viene ognuno. Nessuno e' inventato: sono
 *  gli stessi di «state.snapshot» che la barra mostra in alto. */
const CAMPI = [
  { id: "pid", et: "pid", da: (m) => m.core?.pid },
  { id: "fase", et: "fase", da: (m) => m.fase },
  { id: "tool", et: "tool", da: (m) => m.tools?.length },
  { id: "radici", et: "radici", da: (m) => m.settings?.fs?.allowed_roots?.length },
  { id: "t2", et: "t2", da: (m) => (m.quota ? `${m.quota.attivi}/${m.quota.max_concurrent}` : null) },
];

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-let");
  const campi = el.querySelector(".pnl-let__campi");
  const celle = new Map();

  for (const c of CAMPI) {
    const s = document.createElement("span");
    s.className = "pnl-let__campo";
    s.dataset.vuoto = "";
    const e = document.createElement("span");
    e.className = "pnl-let__et";
    e.textContent = c.et;
    const v = document.createElement("span");
    v.className = "pnl-let__vl";
    v.textContent = "—";
    s.append(e, v);
    campi.appendChild(s);
    celle.set(c.id, { cella: s, valore: v });
  }

  const v = (k) => el.querySelector(`[data-v="${k}"]`);

  /* I byte CONTANO, non saltano — e la causa e' che e' arrivato un messaggio
   * (invariante 25). E' lo stesso contatore che i quadranti usano per il
   * proprio numero: anime.js e' l'unico motore (invariante 9), e scrivere qui
   * una seconda interpolazione a mano sarebbe un secondo motore senza dirlo.
   *
   * ⚠️ Il primo valore si scrive SUBITO. Contare da zero al primo messaggio
   * sarebbe un'animazione senza causa: il contatore non aveva un valore
   * precedente da cui muoversi, ne aveva soltanto l'assenza. */
  const contaByte = contatore((n) => { v("rx").textContent = gruppi(n); },
                              { decimali: 0 });
  let primo = true;
  let byte = 0;
  let messaggi = 0;
  let base = null;
  let da = 0;

  // L'uptime avanza fra due snapshot. Non e' animazione senza causa
  // (invariante 25): la causa e' che il tempo passa, ed e' il dato stesso.
  setInterval(() => {
    if (base === null) return;
    v("uptime").textContent = orologio(base + (Date.now() - da) / 1000);
  }, 1000);

  function scrivi(id, valore) {
    const r = celle.get(id);
    if (!r) return;
    if (valore === undefined || valore === null || valore === "") {
      r.valore.textContent = "—";
      r.cella.dataset.vuoto = "";
      return;
    }
    r.valore.textContent = String(valore);
    delete r.cella.dataset.vuoto;
  }

  return {
    el, radice: el,
    /** Accetta «state.snapshot»; conta i byte di QUALUNQUE messaggio. */
    aggiorna(msg) {
      messaggi += 1;
      byte += new TextEncoder().encode(JSON.stringify(msg ?? {})).length;
      if (primo) { contaByte.subito(byte); primo = false; } else { contaByte.verso(byte); }
      el.querySelector("[data-conteggio]").textContent =
        `${messaggi} ${messaggi === 1 ? "messaggio" : "messaggi"} · ${gruppi(byte)} B`;
      el.querySelector("[data-ora]").textContent =
        new Date().toLocaleTimeString("it-IT", { hour12: false });

      if (msg?.topic !== "state.snapshot") return;
      el.dataset.stato = "pieno";
      for (const c of CAMPI) scrivi(c.id, c.da(msg));
      if (typeof msg.core?.uptime_s === "number") {
        base = msg.core.uptime_s;
        da = Date.now();
        v("uptime").textContent = orologio(base);
      }
      el.querySelector("[data-fonte]").textContent =
        `core · pid ${msg.core?.pid ?? "?"} · ${msg.ws?.clients ?? 0} client sul socket ` +
        `· ${msg.settings?.llm?.backend ?? "llm ignoto"}`;
    },
  };
}
