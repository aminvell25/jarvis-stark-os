/* Pannello console — SPEC §13, §10.2.
 *
 * §13 lo elenca fra gli otto moduli — «comandi reali con trace», Fase 1b — e
 * §21.1 lo nomina nell'albero. Il file esisteva ed era **vuoto**: e' l'unico
 * modulo della tabella che non era mai stato costruito.
 *
 * ## Meta' si puo' fare oggi, meta' no, e si dice quale
 *
 * La **traccia** si puo': il bus vede gia' tutto cio' che il sistema fa, e
 * questo pannello lo mette in fila. L'**ingresso** — digitare un comando — no:
 * sarebbe una richiesta verso il core, e il preload espone quattro funzioni di
 * cui l'unica in uscita puo' soltanto rispondere a una domanda gia' posta
 * (§6.3). Il piede lo dichiara, invece di mostrare un prompt che non manda
 * niente da nessuna parte.
 *
 * ## Niente sparisce in silenzio
 *
 * La telemetria arriva a 2,5 Hz: elencarla riempirebbe la traccia di se
 * stessa e ci nasconderebbe dentro le tre righe che contano. Non si scarta di
 * nascosto — si CONTA, e il conteggio sta nel piede. Una traccia che tace su
 * cio' che ha lasciato fuori e' peggio di una traccia lunga.
 *
 * ## ⚠️ Solo `textContent`
 *
 * E' l'unico pannello che mostra TUTTO cio' che passa sul bus, e li' dentro
 * passa anche il titolo di una `news.card`, cioe' testo che viene da un feed
 * RSS (invariante 5). Costruire queste righe con `innerHTML` vorrebbe dire
 * lasciare che un titolo di giornale scriva markup nella nostra interfaccia.
 * Il DOM e' un contesto senza tool, quindi mostrarlo va bene; interpretarlo
 * no.
 */

export const meta = { nome: "console", versione: "1" };

/** Quante righe restano in vista. Oltre, la piu' vecchia esce. */
const RIGHE = 400;

//: I topic che scorrono troppo per essere elencati. Non spariscono: si
//: contano, e il conteggio e' nel piede.
const A_VOLUME = new Set(["telemetry"]);

/** Come si riassume ogni topic in una riga sola. */
const SINTESI = {
  "state.snapshot": (m) =>
    `fase ${m.fase} · pid ${m.core?.pid} · ${m.tools?.length ?? 0} tool · ` +
    `${m.ws?.clients ?? 0} client`,
  "agent.mesh": (m) =>
    `${(m.nodi ?? []).filter((n) => n.attivo).length}/${(m.nodi ?? []).length} nodi attivi`,
  "agent.advisory": (m) =>
    [m.reason, m.action, ...(m.dettaglio ?? [])].filter(Boolean).join(" · "),
  "ui.intent": (m) =>
    `${m.intento} ${JSON.stringify(m.args ?? {})}`,
  "gesture.intent": (m) => `${m.tipo} · ${m.intento}`,
  "gesture.frame": (m) => `${m.mani ?? 0} mani · ${m.gesto ?? "—"}`,
  "web.open": (m) => m.url ?? "",
  "news.card": (m) => `${m.fonte ?? ""} · ${m.titolo ?? ""}`,
  "news.argomenti": (m) => (m.argomenti ?? []).join(", "),
  "fs.list": (m) => `${m.path} · ${m.totale ?? 0} voci`,
  "fs.confirm_request": (m) =>
    `${m.riepilogo ?? ""} · ${(m.operazioni ?? []).length} operazioni`,
  "source.tree": (m) => `${(m.files ?? []).length} file`,
  "archive.notes": (m) => `${(m.note ?? []).length} documenti`,
  "geo.timezones": (m) => `${(m.zone ?? []).length} fusi`,
};

//: Quali righe portano l'unico accento caldo (§11.6 regola 2: sempre
//: semantico, mai decorativo).
const CALDI = new Set(["agent.advisory"]);

export const css = `
.pnl-con {
  --aug-border-bg: var(--cy-900);
  --aug-tr: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 4);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-con__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-con__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-con__id, .pnl-con__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
/* column-reverse, e non e' un trucco: e' come si legge un log.
 *
 * Le righe si accumulano dal BASSO. Con l'ordine normale una traccia appena
 * cominciata sarebbe quattordici righe in cima e trecento pixel di vuoto
 * sotto — §11.6 regola 3, «uno schermo mezzo vuoto non sembrera' mai JARVIS».
 * Cosi' il vuoto sta sopra, dove un terminale ce l'ha sempre avuto, e lo
 * scorrimento resta ancorato in fondo senza toccare scrollTop.
 *
 * margin-top: auto avrebbe fatto lo stesso, e l'audit l'avrebbe bocciato: si
 * risolve in un numero di pixel qualunque, che non viene da nessuna scala. */
.pnl-con__corpo {
  display: flex;
  flex-direction: column-reverse;
  justify-content: flex-start;
  overflow: auto;
  padding: var(--s-1) 0;
}
.pnl-con__riga {
  display: grid;
  grid-template-columns: calc(var(--grid) / 2) calc(var(--grid) * 1.2) 1fr;
  gap: var(--s-2);
  align-items: baseline;
  padding: 0 var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-primary);
  white-space: nowrap;
}
.pnl-con__riga:nth-child(odd) { background: var(--bg-raised); }
.pnl-con__ora { color: var(--txt-ghost); }
.pnl-con__topic {
  color: var(--cy-700);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pnl-con__det { overflow: hidden; text-overflow: ellipsis; }
.pnl-con__riga[data-caldo] .pnl-con__topic,
.pnl-con__riga[data-caldo] .pnl-con__det { color: var(--amber); }
.pnl-con__piede {
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-con__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-con[data-stato="vuoto"] .pnl-con__corpo { display: none; }
.pnl-con[data-stato="vuoto"] .pnl-con__vuoto { display: block; }
`;

const HTML = `
<section class="pnl-con" data-stato="vuoto" data-augmented-ui="tr-clip border">
  <header class="pnl-con__testa">
    <span class="pnl-con__etichetta">Console</span>
    <span class="pnl-con__id">A03</span>
    <span class="pnl-con__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-con__corpo" data-righe></div>
  <div class="pnl-con__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-con__piede" data-piede></footer>
</section>
`;

function orario(ts) {
  const d = typeof ts === "number" ? new Date(ts * 1000) : new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, "0")).join(":");
}

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-con");
  const corpo = el.querySelector("[data-righe]");
  const piede = el.querySelector("[data-piede]");

  let eventi = 0;
  let volume = 0;
  const topicVisti = new Set();

  function piedeAggiornato() {
    const parti = [`${eventi} eventi`, `${topicVisti.size} topic`];
    if (volume) parti.push(`${volume} campioni di telemetria non elencati`);
    // La meta' che non c'e', detta. Un prompt che non manda niente sarebbe
    // peggio: sembrerebbe rotto invece di assente.
    parti.push("ingresso comandi non collegato");
    piede.textContent = parti.join(" · ");
  }

  function aggiorna(msg) {
    const topic = msg?.topic;
    if (!topic) return;
    topicVisti.add(topic);

    if (A_VOLUME.has(topic)) {
      volume++;
      piedeAggiornato();
      return;
    }

    // Un topic che non conosciamo NON si nasconde: e' esattamente cio' che una
    // traccia serve a far vedere. Si mostra col suo nome e con le chiavi che
    // porta, che e' quanto basta per accorgersene.
    const sintesi = SINTESI[topic];
    const dettaglio = sintesi
      ? sintesi(msg)
      // `topic` e `ts` sono la busta, non il contenuto: elencarli direbbe
      // solo che il messaggio e' un messaggio.
      : Object.keys(msg).filter((k) => k !== "topic" && k !== "ts").join(" ");

    const riga = document.createElement("div");
    riga.className = "pnl-con__riga";
    if (CALDI.has(topic)) riga.dataset.caldo = "";
    for (const [classe, testo] of [
      ["pnl-con__ora", orario(msg.ts)],
      ["pnl-con__topic", topic],
      ["pnl-con__det", String(dettaglio ?? "")],
    ]) {
      const s = document.createElement("span");
      s.className = classe;
      // ⚠️ textContent, mai innerHTML: vedi l'intestazione. Qui dentro passa
      // anche il titolo di un feed RSS.
      s.textContent = testo;
      riga.appendChild(s);
    }

    // In testa al DOM, che con `column-reverse` vuol dire in fondo a schermo.
    // La piu' vecchia esce dall'altro capo.
    corpo.insertBefore(riga, corpo.firstChild);
    while (corpo.childElementCount > RIGHE) corpo.removeChild(corpo.lastChild);

    eventi++;
    el.dataset.stato = "collegato";
    piedeAggiornato();
  }

  function stato(s) {
    if (s === "vuoto") {
      el.dataset.stato = "vuoto";
      piede.textContent = "in attesa del core";
    }
  }

  piedeAggiornato();
  return { el, radice: el, aggiorna, stato };
}
