/* Dock inferiore — SPEC §13.
 *
 * §13, verbatim: «gli otto moduli, indicatore T2 attivo, azioni rapide».
 *
 * ## Otto, ne' sette ne' nove
 *
 * Sono le otto righe della tabella dei moduli di §13. Il dock non elenca tutto
 * cio' che sta a schermo: gli anelli, i quadranti, i glifi, la board e i piani
 * sono ARREDO del workspace, non moduli. Un dock che elencasse anche quelli
 * risponderebbe a due domande diverse — «cosa posso accendere?» e «cosa c'e'
 * a schermo?» — e non risponderebbe bene a nessuna delle due.
 *
 * ## Lo stato del pulsante e' lo stato vero
 *
 * Acceso = il pannello e' aperto adesso. Non «l'ho premuto»: la scrivania
 * annuncia, il dock ridisegna. Se un pannello si chiude col suo ⊠, il dock lo
 * sa senza che nessuno glielo dica.
 *
 * ## Le azioni rapide sono le scorciatoie, col mouse
 *
 * `Alt+H` e `Alt+T` sono in §13 e sono azioni della scrivania, non richieste
 * al core: si possono fare, e averle anche col mouse non aggiunge nessuna
 * superficie. Le altre due scorciatoie di §13 — `Alt+Spazio` e `Esc` —
 * parlerebbero al core, e non ci sono: vedi `SEZIONE-13.md`.
 */

export const meta = { nome: "dock", versione: "1" };

export const css = `
.dck {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--bg-deep);
  border-top: var(--line-base) solid var(--cy-900);
  font-family: var(--font-ui);
}
/* Vedi barra.js: lo spazio lo assorbe chi sta prima. margin-left: auto
   si risolve in un numero di pixel qualunque, e l'audit lo boccia — a
   ragione, perche' non viene da nessuna scala. */
.dck__moduli { display: flex; gap: var(--s-1); flex: 1; }
.dck__tasto {
  background: none;
  border: var(--line-base) solid var(--cy-900);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-ghost);
  cursor: pointer;
  white-space: nowrap;
}
.dck__tasto:hover { border-color: var(--cy-700); color: var(--txt-dim); }
.dck__tasto[aria-pressed="true"] {
  border-color: var(--cy-500);
  color: var(--cy-300);
  background: var(--bg-raised);
}
.dck__tasto:focus-visible { outline: var(--line-base) solid var(--cy-500); }

.dck__ws {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
  padding-right: var(--s-2);
  border-right: var(--line-hair) solid var(--cy-900);
}

.dck__azioni { display: flex; gap: var(--s-1); }
.dck__t2 {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding-left: var(--s-3);
  border-left: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-ghost);
}
.dck__t2[data-attivo] { color: var(--cy-500); }
.dck__spia {
  width: var(--s-2);
  height: var(--s-2);
  background: var(--txt-ghost);
  border-radius: var(--radius);
}
.dck__t2[data-attivo] .dck__spia { background: var(--cy-500); }
`;

//: Le azioni rapide. Sono le scorciatoie di §13 che si possono fare, con lo
//: stesso nome che hanno li'.
const AZIONI = [
  ["nascondi", "Alt+H", (s) => s.nascondiTutto()],
  ["affianca", "Alt+T", (s) => s.affianca()],
];

export function crea(ospite, { scrivania, bus, moduli }) {
  const el = document.createElement("footer");
  el.className = "dck";

  const etichettaWs = document.createElement("span");
  etichettaWs.className = "dck__ws";

  const contenitore = document.createElement("nav");
  contenitore.className = "dck__moduli";
  contenitore.setAttribute("aria-label", "moduli");
  const tasti = new Map();
  for (const m of moduli) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "dck__tasto";
    b.textContent = m.etichetta;
    b.title = `${m.etichetta} — workspace ${String(m.ws).padStart(2, "0")}`;
    b.setAttribute("aria-pressed", "false");
    b.addEventListener("click", () => scrivania.alterna(m.id));
    tasti.set(m.id, b);
    contenitore.appendChild(b);
  }

  const azioni = document.createElement("div");
  azioni.className = "dck__azioni";
  for (const [nome, tasto, fai] of AZIONI) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "dck__tasto";
    b.textContent = nome;
    b.title = tasto;
    b.addEventListener("click", () => fai(scrivania));
    azioni.appendChild(b);
  }

  const t2 = document.createElement("div");
  t2.className = "dck__t2";
  const spia = document.createElement("span");
  spia.className = "dck__spia";
  const testoT2 = document.createElement("span");
  testoT2.textContent = "T2 inerte";
  t2.append(spia, testoT2);

  el.append(etichettaWs, contenitore, azioni, t2);
  ospite.appendChild(el);

  scrivania.osserva(({ workspace, aperti }) => {
    etichettaWs.textContent = `WS ${String(workspace).padStart(2, "0")}`;
    const attivi = new Set(aperti);
    for (const [id, b] of tasti) b.setAttribute("aria-pressed", String(attivi.has(id)));
  });

  bus.su("agent.mesh", (m) => {
    const nodo = (m.nodi ?? []).find((n) => n.id === "t2");
    const attivo = Boolean(nodo?.attivo);
    if (attivo) t2.dataset.attivo = "";
    else delete t2.dataset.attivo;
    // Il dettaglio del nodo dice quante sessioni e quante nella finestra: e'
    // il conto del Governor, non un'etichetta.
    testoT2.textContent = nodo
      ? `T2 ${nodo.stato}${nodo.dettaglio ? ` · ${nodo.dettaglio}` : ""}`
      : "T2 non collegato";
  });

  bus.suStato(({ stato }) => {
    if (stato === "connesso") return;
    delete t2.dataset.attivo;
    testoT2.textContent = "T2 non collegato";
  });

  return { el, altezza: () => el.getBoundingClientRect().height };
}
