/* Il contenuto di una cartella contenitore — SPEC-26 §26.5, §10.2.
 *
 * ## Perche' e' un pannello e non una finestra a parte
 *
 * §26.5 lo dice in una riga: «Aprire una cartella la mostra come **pannello**
 * — non una finestra a parte: un pannello del sistema, con l'anatomia a
 * cinque parti di §10.2.»
 *
 * Non e' un dettaglio estetico. Una finestra con una cornice propria sarebbe
 * il primo elemento dell'ambiente che non si comporta come gli altri: non
 * avrebbe i tre controlli veri di `cornice.js`, non si trascinerebbe dalla
 * testa, non finirebbe nella disposizione salvata. Passando da qui, una
 * cartella aperta e' un pannello come il globo — si sposta, si massimizza, si
 * ricorda al riavvio — e non c'e' un secondo modo di aprire una finestra che
 * col tempo diverge dal primo.
 *
 * ## ⚠️ Questa NON e' una cartella del filesystem
 *
 * §26.5, e vale la pena ripeterlo dove si vede: e' un **raggruppamento
 * dell'ambiente**. Le voci che elenca sono icone — un modulo di §13, il nome
 * di un file — e non righe di directory. Confondere le due cose e' il modo in
 * cui si cancella qualcosa credendo di riordinare una scrivania.
 *
 * Da qui due conseguenze che si vedono nel codice:
 *
 *   - **nessuna operazione distruttiva.** Non c'e' un pulsante «elimina»: il
 *     pannello mostra e apre, e togliere un'icona si fa sul fondo, dove
 *     l'icona sta. Se un giorno ci fosse, passerebbe dalla conferma di §6.2
 *     col percorso RISOLTO, come qualunque altra (invariante 3).
 *   - **il percorso nel piede e' informativo.** §26.5: «Una cartella che
 *     contenga file veri mostra il percorso risolto nel piede». Lo mostra:
 *     non lo compone, non lo naviga, non lo manda a nessuno. Arriva gia'
 *     fatto da chi ha ricevuto `fs.list`, e nel layout su disco non c'e'
 *     nessun percorso — vedi `core/layout.py`.
 *
 * ## Il conteggio c'e' SEMPRE, e zero e' uno stato
 *
 * §26.5: «Una cartella mostra quante cose contiene, sempre. Zero e' uno stato
 * esplicito, non un'assenza» — che e' l'invariante 23 detta per le cartelle.
 * Il numero sta accanto all'etichetta e non nel piede: e' la prima cosa che si
 * chiede a un contenitore, e nel piede finirebbe sotto la piega.
 */

export const meta = { nome: "cartella", versione: "1" };

export const css = `
.pnl-cart {
  --aug-border-bg: var(--cy-900);
  --aug-tr: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 2.4);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}

/* ①②③ la testa. E' anche la maniglia: la cornice di §13 la trova per nome. */
.pnl-cart__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-cart__linguetta {
  width: var(--s-3);
  height: var(--s-2);
  background: var(--manila);
  align-self: center;
}
.pnl-cart__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--manila);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* Il conteggio, che c'e' sempre. Riempito e non a contorno: e' il dato piu'
   importante della testa, e §26.3 ha misurato quanto costa dirlo col testo. */
.pnl-cart__conteggio {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  color: var(--txt-dim);
}
.pnl-cart__id, .pnl-cart__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
  letter-spacing: 0.10em;
}

/* ④ il contenuto */
.pnl-cart__corpo {
  overflow-y: auto;
  padding: var(--s-1) 0;
}
.pnl-cart__riga {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  font-size: var(--t-data);
  cursor: pointer;
  /* Uno STATO, quindi transizione CSS e mai anime.js: §26.4 lo ha gia'
     deciso per le tessere del catalogo, e vale identico qui. */
  transition: background 120ms linear;
}
.pnl-cart__riga:hover { background: var(--fill-1); }
.pnl-cart__segno {
  flex: 0 0 auto;
  width: var(--s-2);
  height: var(--s-2);
  background: var(--icona);
}
.pnl-cart__riga[data-tipo="file"] .pnl-cart__segno { background: var(--manila); }
.pnl-cart__nome {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pnl-cart__tipo {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-ghost);
}

/* Lo stato vuoto: dichiarato, non un riquadro senza niente (invariante 23). */
.pnl-cart__vuoto {
  display: none;
  align-items: center;
  justify-content: center;
  padding: var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.12em;
  color: var(--txt-ghost);
  text-align: center;
}
.pnl-cart[data-stato="vuota"] .pnl-cart__corpo { display: none; }
.pnl-cart[data-stato="vuota"] .pnl-cart__vuoto { display: flex; }

/* ⑤ il piede */
.pnl-cart__piede {
  display: flex;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  color: var(--txt-ghost);
}
.pnl-cart__percorso {
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  /* Il percorso si taglia a SINISTRA: di una directory conta la coda, e
     troncare in fondo lascerebbe leggere solo la radice, che si sa gia'. */
  direction: rtl;
  text-align: left;
}
`;

/* Il taglio a 45° sta sul vertice in ALTO A DESTRA — `tr-clip`.
 * §10.2, regola dell'asimmetria: uno o due vertici, mai zero e mai quattro.
 * Il file manager taglia in basso a sinistra; una cartella che tagliasse allo
 * stesso vertice sarebbe la sua copia storta. */
const HTML = `
<section class="pnl-cart" data-stato="vuota" data-augmented-ui="tr-clip border">
  <header class="pnl-cart__testa">
    <span class="pnl-cart__linguetta"></span>
    <span class="pnl-cart__etichetta" data-etichetta>Cartella</span>
    <span class="pnl-cart__conteggio" data-conteggio>0 voci</span>
    <span class="pnl-cart__id">D01</span>
    <span class="pnl-cart__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-cart__corpo" data-voci></div>
  <div class="pnl-cart__vuoto">VUOTA &#183; NESSUNA ICONA DENTRO</div>
  <footer class="pnl-cart__piede">
    <span data-natura></span>
    <span class="pnl-cart__percorso" data-percorso></span>
  </footer>
</section>
`;

/**
 * `apri(voce)` viene chiamata al doppio clic su una riga. Facoltativa: nella
 * galleria non c'e' niente da aprire, e il pannello si giudica lo stesso.
 */
export function crea(contenitore, { apri } = {}) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-cart");
  const etichetta = el.querySelector("[data-etichetta]");
  const conteggio = el.querySelector("[data-conteggio]");
  const voci = el.querySelector("[data-voci]");
  const natura = el.querySelector("[data-natura]");
  const percorso = el.querySelector("[data-percorso]");

  /**
   * `{ etichetta, voci: [{ tipo, nome }], radice }`.
   *
   * `radice` e' il percorso risolto della workspace, che arriva da `fs.list`.
   * Si mostra **solo se dentro c'e' almeno un file vero**: su una cartella di
   * soli moduli sarebbe un percorso che non c'entra niente con cio' che si sta
   * guardando, cioe' peggio che nessun percorso.
   */
  function aggiorna(dati = {}) {
    const dentro = Array.isArray(dati.voci) ? dati.voci : [];
    etichetta.textContent = dati.etichetta || "cartella";
    conteggio.textContent = `${dentro.length} ${dentro.length === 1 ? "voce" : "voci"}`;
    el.dataset.stato = dentro.length ? "piena" : "vuota";

    // ⚠️ `textContent`, mai `innerHTML`: il nome di un file e' dato NON FIDATO
    // (invariante 5) e arriva dal disco. Un file chiamato con del markup
    // scriverebbe dentro l'interfaccia — e l'interfaccia ha `window.jarvis`.
    voci.textContent = "";
    for (const v of dentro) {
      const riga = document.createElement("div");
      riga.className = "pnl-cart__riga";
      riga.dataset.tipo = v.tipo;
      riga.dataset.nome = v.nome;
      riga.title = `${v.nome} — doppio clic per aprire`;
      const segno = document.createElement("span");
      segno.className = "pnl-cart__segno";
      const nome = document.createElement("span");
      nome.className = "pnl-cart__nome";
      nome.textContent = v.nome;
      const tipo = document.createElement("span");
      tipo.className = "pnl-cart__tipo";
      tipo.textContent = v.tipo;
      riga.append(segno, nome, tipo);
      riga.addEventListener("dblclick", () => apri?.(v));
      voci.appendChild(riga);
    }

    const file = dentro.filter((v) => v.tipo === "file").length;
    natura.textContent = file
      ? `${file} ${file === 1 ? "file vero" : "file veri"} · raggruppamento`
      : "raggruppamento dell'ambiente";
    percorso.textContent = file && dati.radice ? String(dati.radice) : "";
  }

  return { el, aggiorna };
}
