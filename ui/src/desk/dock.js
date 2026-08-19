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
/* ADR-010: fuori dal filtro, non fuori dalla scrivania. Solo il colore del
   testo scende — niente opacita', che smorzerebbe anche il bordo e farebbe
   sembrare il pulsante disattivato invece che di un'altra categoria. */

.dck__filtro {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
  padding-right: var(--s-2);
  border-right: var(--line-hair) solid var(--cy-900);
}

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

export function crea(ospite, { scrivania, bus }) {
  /* ⚠️ §26.3 — il dock ha CEDUTO l'indice al catalogo.
   *
   * Aveva gli otto moduli e le due azioni rapide. Adesso l'indice dei moduli
   * e' la linguetta MODULI del catalogo, e le azioni stanno sul suo plinto:
   * §26.3 dice che il catalogo «unifica la barra delle applicazioni e il file
   * manager», e due elenchi degli stessi otto moduli a schermo sarebbero due
   * posti in cui la stessa verita' puo' divergere.
   *
   * Quello che resta e' STATO, non comandi: dove siamo (il filtro) e che cosa
   * sta facendo il sistema (T2). Una striscia sottile, non una barra.
   *
   * Il criterio A di §13 — «le otto voci aprono e chiudono il proprio
   * modulo» — non e' stato cancellato: si e' SPOSTATO sul catalogo, e
   * `--verifica-scrivania` lo prova li'.
   */
  const el = document.createElement("div");
  el.className = "dck";

  const etichettaFiltro = document.createElement("span");
  etichettaFiltro.className = "dck__filtro";

  const t2 = document.createElement("div");
  t2.className = "dck__t2";
  const spia = document.createElement("span");
  spia.className = "dck__spia";
  const testoT2 = document.createElement("span");
  testoT2.textContent = "T2 inerte";
  t2.append(spia, testoT2);

  el.append(etichettaFiltro, t2);
  ospite.appendChild(el);

  scrivania.osserva(({ filtro, aperti }) => {
    etichettaFiltro.textContent =
      (filtro ? `FILTRO ${String(filtro).padStart(2, "0")}` : "TUTTO") +
      ` · ${aperti.length} pannelli`;
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
