/* Pannello meteo — SPEC-26, sul modello della striscia in basso a destra di
 * `famiglia-a/01`, e §10.2 per l'anatomia.
 *
 * ## Che cosa si prende dal riferimento e che cosa no
 *
 * Si prende la FORMA: un numero grande a sinistra, una fila di giorni a
 * destra, ognuno con un'icona del tempo e una temperatura.
 *
 * NON si prende l'altezza delle colonne. Nel riferimento le colonne dei giorni
 * hanno altezze diverse che **non codificano niente**: SAT e SUN sono
 * entrambe 70 gradi e sono alte 37 e 43 px. Copiarle sarebbe decorazione con
 * l'aria del dato, ed e' il modo esatto in cui un pannello comincia a mentire.
 *
 * NON si prende il rosso su cinque celle su sette. Nel riferimento non ha una
 * regola leggibile: non corrisponde ne' al fine settimana ne' alla temperatura
 * ne' all'icona. Qui l'accento caldo sta su **oggi**, che e' una cella su
 * sette ed e' quello che fa il calendario della stessa immagine.
 *
 * ## Le icone sono OTTO, non due
 *
 * Il riferimento ne disegna due — un sole e un sole con nuvola. Ricondurre
 * tutto il tempo a due icone e' un segnaposto travestito da icona: con la sola
 * coppia, «nebbia» e «temporale» diventerebbero entrambi «sereno». Una
 * settimana vera di Milano, misurata chiamando il tool, ne conteneva CINQUE
 * diverse. La mappa dei codici WMO sta in `core/tools/meteo.py`, chiusa, e
 * `ignoto` ha un segno suo.
 *
 * ## Invariante 23 — lo stato vuoto e' progettato, non ereditato
 *
 * Il concept non contiene un solo stato vuoto: nessun pannello dice «nessun
 * dato». E' l'unica cosa che il riferimento non puo' insegnare, ed e' la prima
 * che va disegnata. Qui gli stati sono tre e si distinguono:
 *
 *   nessuna sorgente   `meteo.enabled` falso o coordinate non impostate
 *   non raggiungibile  rete assente o servizio giu'
 *   collegato          dati veri, con l'ora in cui sono stati presi
 *
 * ⚠️ **Nessun ripiego a dati finti.** Un meteo inventato e' peggio di nessun
 * meteo, perche' qualcuno esce senza ombrello.
 *
 * ## Invariante 5 — quello che arriva dalla rete
 *
 * Nel messaggio non c'e' **nessun campo di testo** dell'API: lo schema di
 * `core/tools/meteo.py` accetta solo numeri, il nome del luogo viene dalle
 * impostazioni e la condizione e' una parola di un elenco NOSTRO. Quindi qui
 * non serve `Untrusted`: non c'e' prosa da avvolgere, e la barriera e' lo
 * schema. I nomi dei giorni li calcola il renderer, che ha un orologio.
 */

import { segno } from "../desk/segni.js";

export const meta = { nome: "meteo", versione: "1" };

//: I giorni, dall'orologio locale. Non arrivano dall'API: sarebbero l'unico
//: campo di testo di terzi in tutto il pannello.
const GIORNI = ["DOM", "LUN", "MAR", "MER", "GIO", "VEN", "SAB"];

export const css = `
.pnl-met {
  --aug-border-bg: transparent;
  --aug-tr: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 4);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}

/* ①②③ la testa e' una SUPERFICIE (§10.5 regola 2). */
.pnl-met__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  background: var(--fill-1);
}
.pnl-met__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-met__luogo {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  color: var(--icona);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pnl-met__id, .pnl-met__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--icona);
}

/* ④ il corpo: adesso a sinistra, la settimana a destra */
.pnl-met__corpo {
  display: flex;
  align-items: stretch;
  gap: var(--s-3);
  padding: var(--s-3) var(--s-2);
  overflow: hidden;
}
.pnl-met__adesso {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s-1);
  padding-right: var(--s-3);
  border-right: var(--line-hair) solid var(--cy-900);
}
/* Il numero grande: e' il dato principale, e nel riferimento e' la cosa piu'
   grande della striscia. --t-title e' il gradino piu' alto della scala. */
.pnl-met__grande {
  font-family: var(--font-mono);
  font-size: var(--t-title);
  line-height: 1;
  color: var(--txt-primary);
}
.pnl-met__grande sup {
  font-size: var(--t-micro);
  vertical-align: super;
  color: var(--icona);
}
.pnl-met__ora { color: var(--icona); }

.pnl-met__settimana {
  flex: 1;
  display: flex;
  align-items: stretch;
  gap: var(--s-1);
  min-width: 0;
}
.pnl-met__giorno {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-1);
  padding: var(--s-1) 0;
  background: var(--bg-panel);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
/* L'accento caldo su OGGI: una cella su sette, e significa qualcosa. §11.1
   vuole l'accento sempre semantico. */
.pnl-met__giorno[data-oggi] {
  background: var(--fill-1);
  color: var(--txt-primary);
}
.pnl-met__giorno[data-oggi] .pnl-met__nome { color: var(--amber); }
/* L'asta dell'escursione: dal minimo al massimo del giorno, sulla scala della
   settimana. Sta a --fill-2 (L 89) nella banda 60-120, ed e' larga poco perche'
   deve stare ACCANTO ai numeri, non sotto: il numero resta il dato esatto, la
   barra e' il confronto. */
.pnl-met__asta {
  position: absolute;
  right: var(--s-1);
  width: var(--s-1);
  background: var(--fill-2);
}
.pnl-met__giorno[data-oggi] .pnl-met__asta { background: var(--fill-3); }
.pnl-met__nome { letter-spacing: 0.10em; }
.pnl-met__icona { color: var(--icona); display: flex; }
.pnl-met__giorno[data-oggi] .pnl-met__icona { color: var(--icona-viva); }
.pnl-met__gradi { color: var(--txt-primary); }
.pnl-met__min { color: var(--txt-dim); }

/* Lo stato vuoto: dichiarato, e dice anche PERCHE'. */
.pnl-met__vuoto {
  display: none;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.08em;
  color: var(--txt-dim);
}
.pnl-met[data-stato="vuoto"] .pnl-met__corpo { display: none; }
.pnl-met[data-stato="vuoto"] .pnl-met__vuoto { display: flex; }

/* ⑤ il piede: da dove viene il dato e da quanto */
.pnl-met__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  color: var(--txt-dim);
}
`;

const HTML = `
<section class="pnl-met" data-stato="vuoto" data-augmented-ui="tr-clip border">
  <header class="pnl-met__testa">
    <span class="pnl-met__etichetta">Meteo</span>
    <span class="pnl-met__luogo" data-luogo>&mdash;</span>
    <span class="pnl-met__id">MET_E01</span>
    <span class="pnl-met__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-met__corpo">
    <div class="pnl-met__adesso">
      <span class="pnl-met__grande" data-adesso>&mdash;</span>
      <span class="pnl-met__ora" data-condizione></span>
    </div>
    <div class="pnl-met__settimana" data-settimana></div>
  </div>
  <div class="pnl-met__vuoto" data-vuoto></div>
  <footer class="pnl-met__piede">
    <span data-sorgente></span>
    <span data-freschezza></span>
  </footer>
</section>
`;

/** «3 minuti fa». Un meteo senza questo mostra numeri senza data. */
function quandoFa(secondi) {
  const d = Math.max(0, Math.round(Date.now() / 1000 - secondi));
  if (d < 90) return "adesso";
  if (d < 5400) return `${Math.round(d / 60)} min fa`;
  return `${Math.round(d / 3600)} h fa`;
}

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-met");
  const luogo = el.querySelector("[data-luogo]");
  const adesso = el.querySelector("[data-adesso]");
  const condizione = el.querySelector("[data-condizione]");
  const settimana = el.querySelector("[data-settimana]");
  const vuoto = el.querySelector("[data-vuoto]");
  const sorgente = el.querySelector("[data-sorgente]");
  const freschezza = el.querySelector("[data-freschezza]");
  let preso = null;

  /** `{ luogo, unita, adesso: {temperatura, condizione}, giorni: [...] }` */
  function aggiorna(m = {}) {
    if (!m.giorni?.length) return stato("nessun dato dalla sorgente meteo");
    el.dataset.stato = "collegato";
    luogo.textContent = m.luogo ?? "";
    adesso.innerHTML = "";
    adesso.append(document.createTextNode(String(m.adesso?.temperatura ?? "—")));
    const u = document.createElement("sup");
    u.textContent = m.unita ?? "";
    adesso.appendChild(u);
    condizione.textContent = m.adesso?.condizione ?? "";

    // ⚠️ `textContent` e nodi costruiti, mai innerHTML con interpolazione: e'
    // dato che viene dalla rete (R96, invariante 5).
    settimana.textContent = "";
    const oggi = new Date().getDay();
    /* La scala della settimana: la stessa per tutte e sette le colonne, o le
       barre non si confrontano. Un decimo di margine sopra e sotto, perche' una
       barra che tocca il bordo non si legge come un valore ma come un limite. */
    const tutte = m.giorni.flatMap((g) => [g.min, g.max]);
    const lo = Math.min(...tutte), hi = Math.max(...tutte);
    const margine = Math.max(1, (hi - lo) * 0.1);
    const scala = { min: lo - margine, max: hi + margine };
    for (const g of m.giorni) {
      const c = document.createElement("div");
      c.className = "pnl-met__giorno";
      if (g.fra === 0) c.dataset.oggi = "";
      c.title = `${g.condizione} · min ${g.min}${m.unita} · max ${g.max}${m.unita}`;
      const nome = document.createElement("span");
      nome.className = "pnl-met__nome";
      nome.textContent = GIORNI[(oggi + g.fra) % 7];
      const ic = document.createElement("span");
      ic.className = "pnl-met__icona";
      ic.appendChild(segno(g.condizione, "var(--s-4)"));
      const max = document.createElement("span");
      max.className = "pnl-met__gradi";
      max.textContent = String(g.max);
      const min = document.createElement("span");
      min.className = "pnl-met__min";
      min.textContent = String(g.min);
      /* ⚠️ L'ESCURSIONE E' UN INTERVALLO, e un intervallo si disegna.
       * Due numeri incolonnati dicono «29» e «19»; una barra dice quanto e'
       * ampia la giornata e dove sta rispetto alle altre — cioe' la stessa
       * informazione piu' il confronto, che i numeri da soli non danno.
       * La scala e' quella della settimana intera, calcolata sotto: senza, ogni
       * colonna userebbe la propria e le barre non sarebbero confrontabili, che
       * e' il solo motivo per cui una barra esiste.
       * E' anche il divario di densita' di §11.8: la banda L 60-120 il
       * riferimento la tiene al 24,7 % e questo pannello all'8,2 %. */
      const asta = document.createElement("i");
      asta.className = "pnl-met__asta";
      const alto = scala.max === scala.min ? 1 : (g.max - scala.min) / (scala.max - scala.min);
      const basso = scala.max === scala.min ? 0 : (g.min - scala.min) / (scala.max - scala.min);
      asta.style.bottom = (basso * 100).toFixed(1) + "%";
      asta.style.height = Math.max(2, (alto - basso) * 100).toFixed(1) + "%";
      c.append(nome, ic, max, min, asta);
      settimana.appendChild(c);
    }

    sorgente.textContent = m.sorgente ?? "";
    preso = m.aggiornato ?? null;
    freschezza.textContent = preso ? quandoFa(preso) : "";
  }

  /** Lo stato vuoto dice anche PERCHE': tre cause diverse, tre frasi. */
  function stato(perche) {
    el.dataset.stato = "vuoto";
    vuoto.textContent = perche;
    luogo.textContent = "—";
    sorgente.textContent = "";
    freschezza.textContent = "";
  }

  stato("nessuna posizione in settings.toml — meteo.latitude e meteo.longitude");

  // La freschezza avanza da sola: la causa e' che il tempo passa, ed e'
  // esattamente il dato che il campo dichiara (invariante 25 regge).
  setInterval(() => {
    if (preso) freschezza.textContent = quandoFa(preso);
  }, 30_000);

  return { el, aggiorna, stato };
}
