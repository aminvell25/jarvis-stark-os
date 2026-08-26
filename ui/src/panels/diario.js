/* Pannello diario — SPEC §3.2, §10.2, §13.
 *
 * DUE registri affiancati, e non e' una scelta di impaginazione: sono due
 * domande diverse. «Che cosa mi ha risposto» si legge in ordine di
 * conversazione; «perche' ha aperto quel pannello» si legge in ordine di
 * causa. Mescolarli produce una colonna in cui non si legge nessuna delle due.
 *
 * Anatomia a cinque parti di §10.2: etichetta in caps, id e versione,
 * controlli, contenuto vero, piede tecnico. Taglio a 45 gradi su UN vertice
 * (regola dell'asimmetria: mai zero, mai quattro), via augmented-ui.
 *
 * TRE STATI, come vuole l'invariante 23:
 *
 *   collegato  righe vere dal socket
 *   vuoto      NESSUNA RIGA in --txt-ghost, con la ragione
 *   galleria   righe REGISTRATE da una sessione vera, non inventate
 *
 * ⚠️ Il testo delle righe si scrive con textContent e mai con innerHTML: la
 * meta' «signore» e' una TRASCRIZIONE, cioe' testo che nessuno ha rivisto, e
 * comporlo come markup vorrebbe dire dargli un modo di fingersi un elemento
 * dell'interfaccia. Il CSP vieta l'esecuzione, non l'inganno.
 */

// `ora()` e non `adesso()`: la seconda restituisce i millisecondi
// dell'epoca, e nel piede si leggeva 1787773978011.
import { ora as oraDiAdesso } from "../desk/orologio.js";

export const meta = { nome: "diario", versione: "1" };

/* Quante righe si tengono per colonna. Oltre, le piu' vecchie escono: il
   registro completo vive su disco, questo e' il vetro attraverso cui lo si
   guarda. */
const MAX_RIGHE = 40;

export const css = `
.pnl-dia {
  --aug-border-bg: transparent;
  --aug-br: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  /* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE, non una riga di testo. */
.pnl-dia__testa {
  /* Griglia e non flex con margin auto: la forma con margin-left auto calcola
     un valore che non sta sulla scala di §11.8, e l'audit lo segnala a ogni
     giro. Una
     colonna elastica spinge i controlli a destra senza inventare un numero. */
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  background: var(--fill-1);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-dia__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-dia__id {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-dia__ctrl {
  justify-self: end;
  font-size: var(--t-micro);
  color: var(--icona);
  letter-spacing: 0.2em;
}

/* I due registri, affiancati e separati da un tratto: il confine si vede. */
.pnl-dia__corpo {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 0;
}
.pnl-dia__col {
  display: grid;
  grid-template-rows: auto 1fr;
  min-height: 0;
  min-width: 0;
}
.pnl-dia__col + .pnl-dia__col {
  border-left: var(--line-hair) solid var(--cy-900);
}
.pnl-dia__titolo {
  padding: var(--s-1) var(--s-2);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-dim);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-dia__flusso {
  overflow-y: auto;
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  line-height: 1.5;
}

/* ── il dialogo ─────────────────────────────────────────────────────────── */
.pnl-dia__battuta {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: var(--s-1);
  padding: var(--s-1) 0;
  align-items: baseline;
}
.pnl-dia__ora { color: var(--txt-ghost); }
.pnl-dia__chi {
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.pnl-dia__battuta[data-chi="signore"] .pnl-dia__chi { color: var(--icona); }
.pnl-dia__battuta[data-chi="jarvis"]  .pnl-dia__chi { color: var(--cy-300); }
.pnl-dia__testo {
  color: var(--txt-primary);
  overflow-wrap: anywhere;
}
/* I marcatori sono DATO, non decorazione, e stanno nel DOM.
   ⚠️ Erano due regole ::after sullo STESSO pseudo-elemento: quando una
   risposta era insieme interrotta e stimata — cioe' il caso normale col TTS
   locale — la seconda regola vinceva e **INTERROTTO spariva**. Il marcatore
   che conta di piu' era proprio quello che si perdeva, e l'ha mostrato lo
   scatto, non un test. */
.pnl-dia__marca {
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.pnl-dia__marca[data-tipo="interrotto"] { color: var(--amber); }
.pnl-dia__marca[data-tipo="stimato"] { color: var(--txt-ghost); }

/* ── le azioni ──────────────────────────────────────────────────────────── */
.pnl-dia__atto {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: var(--s-1);
  padding: var(--s-1) 0;
  align-items: baseline;
}
.pnl-dia__esito {
  font-weight: 700;
  letter-spacing: 0.08em;
}
.pnl-dia__atto[data-ok="1"] .pnl-dia__esito { color: var(--cy-300); }
.pnl-dia__atto[data-ok="0"] .pnl-dia__esito { color: var(--rust); }
.pnl-dia__intento { color: var(--txt-primary); overflow-wrap: anywhere; }
.pnl-dia__strada {
  color: var(--txt-ghost);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
/* Un intento senza destinazione e' la riga piu' utile del registro: JARVIS ha
   capito e non ha fatto niente. Non deve confondersi con un fallimento. */
.pnl-dia__atto[data-strada="nessuna"] .pnl-dia__strada { color: var(--amber); }

.pnl-dia__vuoto {
  display: none;
  padding: var(--s-2);
  font-size: var(--t-micro);
  line-height: 1.6;
  color: var(--txt-ghost);
  letter-spacing: 0.08em;
}
.pnl-dia__col[data-stato="vuoto"] .pnl-dia__vuoto { display: block; }
.pnl-dia__col[data-stato="vuoto"] .pnl-dia__flusso { display: none; }

.pnl-dia__piede {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
  border-top: var(--line-hair) solid var(--cy-900);
}
.pnl-dia__piede span:last-child { justify-self: end; }
`;

const ora = (ts) =>
  ts
    ? new Date(ts * 1000).toLocaleTimeString("it-IT", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      })
    : "--:--:--";

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-dia";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.innerHTML = `
    <div class="pnl-dia__testa">
      <span class="pnl-dia__etichetta">Diario</span>
      <span class="pnl-dia__id">DIA_R01 &middot; ver ${meta.versione}</span>
      <span class="pnl-dia__ctrl">&#8862; &#8865; &#8864;</span>
    </div>
    <div class="pnl-dia__corpo">
      <div class="pnl-dia__col" data-flusso="dialogo" data-stato="vuoto">
        <div class="pnl-dia__titolo">Dialogo</div>
        <div class="pnl-dia__flusso"></div>
        <div class="pnl-dia__vuoto">
          NESSUNA BATTUTA<br>non è stato detto nulla da quando il core è partito
        </div>
      </div>
      <div class="pnl-dia__col" data-flusso="azione" data-stato="vuoto">
        <div class="pnl-dia__titolo">Intenzioni e azioni</div>
        <div class="pnl-dia__flusso"></div>
        <div class="pnl-dia__vuoto">
          NESSUNA AZIONE<br>nessun intento è stato deciso
        </div>
      </div>
    </div>
    <div class="pnl-dia__piede">
      <span class="pnl-dia__conta-dialogo">0 battute</span>
      <span class="pnl-dia__conta-azione">0 azioni</span>
      <span class="pnl-dia__quando">--:--:--</span>
    </div>
  `;
  ospite.appendChild(radice);

  const col = {
    dialogo: radice.querySelector('[data-flusso="dialogo"]'),
    azione: radice.querySelector('[data-flusso="azione"]'),
  };
  const conta = { dialogo: 0, azione: 0 };

  function battuta(msg) {
    const el = document.createElement("div");
    el.className = "pnl-dia__battuta";
    el.dataset.chi = msg.chi === "jarvis" ? "jarvis" : "signore";
    el.dataset.interrotto = msg.interrotto ? "1" : "0";
    el.dataset.stimato = msg.chi === "jarvis" && msg.misurato === false ? "1" : "0";
    el.innerHTML = `
      <span class="pnl-dia__ora"></span>
      <span class="pnl-dia__chi"></span>
      <span class="pnl-dia__testo"></span>
    `;
    el.querySelector(".pnl-dia__ora").textContent = ora(msg.ts);
    el.querySelector(".pnl-dia__chi").textContent =
      msg.chi === "jarvis" ? "◂ jarvis" : "▸ signore";
    // textContent: e' una trascrizione, cioe' testo che nessuno ha rivisto.
    el.querySelector(".pnl-dia__testo").textContent = msg.testo ?? "";
    // I due marcatori CONVIVONO: una risposta puo' essere insieme troncata e
    // stimata, ed e' il caso normale col TTS locale.
    const testo = el.querySelector(".pnl-dia__testo");
    for (const [attivo, tipo, parola] of [
      [msg.interrotto, "interrotto", "INTERROTTO"],
      [msg.chi === "jarvis" && msg.misurato === false, "stimato", "detto stimato"],
    ]) {
      if (!attivo) continue;
      const m = document.createElement("span");
      m.className = "pnl-dia__marca";
      m.dataset.tipo = tipo;
      m.textContent = " \u2014 " + parola;
      testo.appendChild(m);
    }
    return el;
  }

  function atto(msg) {
    const el = document.createElement("div");
    el.className = "pnl-dia__atto";
    el.dataset.ok = msg.ok ? "1" : "0";
    el.dataset.strada = msg.strada ?? "?";
    el.innerHTML = `
      <span class="pnl-dia__ora"></span>
      <span class="pnl-dia__esito"></span>
      <span class="pnl-dia__intento"></span>
      <span class="pnl-dia__strada"></span>
    `;
    el.querySelector(".pnl-dia__ora").textContent = ora(msg.ts);
    el.querySelector(".pnl-dia__esito").textContent = msg.ok ? "OK" : "NO";
    const arg = msg.args && Object.keys(msg.args).length
      ? " " + Object.values(msg.args).join(" ") : "";
    el.querySelector(".pnl-dia__intento").textContent =
      (msg.intento ?? "?") + arg + (msg.errore ? " — " + msg.errore : "");
    el.querySelector(".pnl-dia__strada").textContent = msg.strada ?? "?";
    return el;
  }

  function inserisci(msg) {
    const c = col[msg.flusso];
    if (!c) return;
    const flusso = c.querySelector(".pnl-dia__flusso");
    flusso.insertBefore(msg.flusso === "dialogo" ? battuta(msg) : atto(msg),
                        flusso.firstChild);
    while (flusso.children.length > MAX_RIGHE) flusso.lastChild.remove();
    c.dataset.stato = "pieno";
    conta[msg.flusso] += 1;
    radice.querySelector(".pnl-dia__conta-dialogo").textContent =
      `${conta.dialogo} ${conta.dialogo === 1 ? "battuta" : "battute"}`;
    radice.querySelector(".pnl-dia__conta-azione").textContent =
      `${conta.azione} ${conta.azione === 1 ? "azione" : "azioni"}`;
    // L'ora la dice il core, non la macchina che disegna: desk/orologio.js.
    radice.querySelector(".pnl-dia__quando").textContent = oraDiAdesso();
  }

  return {
    radice,
    /** @param {{topic:string, flusso:string}} msg  `agent.diario` */
    aggiorna(msg) {
      if (msg?.topic !== "agent.diario") return;
      inserisci(msg);
    },
  };
}
