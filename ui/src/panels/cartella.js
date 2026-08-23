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
  /* §10.5 — l'anello di augmented-ui E' la cornice sui quattro lati.
     Misurato sullo scatto del contenitore radice: 4 px pieni di --cy-900 su
     TUTTI E QUATTRO i lati, cioe' esattamente il tratto che zero pannelli su
     sette hanno nel riferimento. E dipinge SOPRA i figli: con la testata
     diventata chiara ne mangiava 4 px su tre lati.
     Si toglie l'INCHIOSTRO, non l'anello — la parola che lo accende sta nel
     markup, accanto ai tagli a 45 gradi, e di li' non si tocca. «transparent»
     qui e' assenza, non un colore scelto: la stessa lettura che l'audit da' a
     rgba(0,0,0,0). Toglierlo del tutto NON spegne il tratto: augmented-ui
     ripiega su currentColor e lo riaccende a --txt-primary. */
  --aug-border-bg: transparent;
  --aug-tr: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 2.4);
  /* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
     Dei sette pannelli misurati sul riferimento nessuno ha un tratto di bordo
     sui quattro lati: cio' che dice dove finisce la cartella e' il salto di
     fondo contro il pavimento. Da --bg-panel (L 31) a --bg-raised (L 37), che
     e' il #1e2631 letto identico a quattro quote sul calendario — opaco e
     piatto, senza velo ne backdrop-filter. Contro il pavimento a L 19 fa +18.
     Gli angoli li chiudono i marcatori triangolari della finestra (app.css):
     esistono una volta sola per tutti i pannelli e qui non si rifanno. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}

/* ①②③ la testa. E' anche la maniglia: la cornice di §13 la trova per nome.
 *
 * §10.5 regola 2 — una testata e' una SUPERFICIE, non una riga con una linea
 * sotto: una riga di testo sul fondo del corpo non e' una testata, e' testo.
 * --fill-1 sta a L 66 contro i 37 del corpo, cioe' +29: dentro la polarita'
 * del calendario (+30 L, testo chiaro) che §10.5 adotta fra le tre del
 * riferimento, e ben oltre il +19 minimo misurato.
 *
 * Il border-bottom hairline se ne va perche' era la seconda meta' di una
 * separazione che ora e' gia' fatta: due segni per lo stesso confine sono uno
 * di troppo. Padding e corpo del testo non si toccano — la banda deve restare
 * il 6-9 % dell'altezza del pannello, e quella quota la fissa il padding. */
.pnl-cart__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  background: var(--fill-1);
}
/* La linguetta resta --manila anche sulla superficie nuova, dove misura
   3,26:1. Come TESTO sarebbe sotto ogni soglia, ma questo e' un blocco pieno:
   per un oggetto grafico la richiesta e' 3:1 (WCAG 1.4.11) e la passa. E'
   voluto che sopravviva qui — e' il segno che dice «cartella», ed e' l'unico
   punto della testa in cui il colore dei contenitori regge il fondo nuovo. */
.pnl-cart__linguetta {
  width: var(--s-3);
  height: var(--s-2);
  background: var(--manila);
  align-self: center;
}
/* L'etichetta era --manila, che su --fill-1 crolla a 3,26:1: la parola che si
   legge per prima sarebbe la meno leggibile della testa. Passa a --txt-primary
   (8,06:1). L'identita' manila non si perde, si sposta di due millimetri a
   sinistra: sta nella linguetta, che e' il segno e non la didascalia. */
.pnl-cart__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* Il conteggio, che c'e' sempre. Riempito e non a contorno: e' il dato piu'
   importante della testa, e §26.3 ha misurato quanto costa dirlo col testo.
   Era --txt-dim, che sulla superficie nuova scende a 2,73:1 — e un numero lo
   si legge di sfuggita, non lo si decifra. --cy-300 misura 6,21:1 ed e' il
   ciano dei dati vivi: dice «questo e' un numero» dove --txt-primary direbbe
   soltanto «questo e' testo», e non ruba il primo posto all'etichetta. */
.pnl-cart__conteggio {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  color: var(--cy-300);
}
/* Id e controlli sono la targa del pannello, non il suo contenuto: --icona
   misura 4,31:1 su --fill-1, quanto basta per leggerli quando si cercano e non
   abbastanza per rubare l'occhio quando non si cercano. --txt-dim, che c'era
   prima, sulla banda a L 66 vale 2,73:1 e sarebbe un ornamento illeggibile. */
.pnl-cart__id, .pnl-cart__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
  letter-spacing: 0.10em;
}

/* ④ il contenuto */
/* ⚠️ IL CORPO E' UNA SUPERFICIE MANILA, e la polarita' si rovescia.
 *
 * Fino al 23 agosto 2026 la cartella portava --manila solo sulla linguetta e
 * sul segno dei file: un accento su un pannello freddo come tutti gli altri.
 * Il riferimento fa il contrario. Misurato su famiglia-a/01: il suo caldo e'
 * il **5,70 %** della superficie, e per due terzi viene da UN riquadro — CIRCA
 * COMPANY, 144x97 su un'immagine larga 901, cioe' il 2,75 % da solo — che e'
 * un pannello con la **superficie** manila, non un pannello con un accento.
 * Da noi il caldo sta allo 0,2 %, e DIVARIO-PREMIUM.md §0 lo chiama la
 * differenza singola piu' grande dopo il contenuto fotografico.
 *
 * Una superficie a L 146 non regge il testo chiaro: --txt-primary (L 224) su
 * --manila fa 1,68:1. La polarita' si rovescia — testo scuro su fondo caldo —
 * ed e' la stessa mossa che panels/tabella.js fa gia' sulla propria
 * intestazione. --bg-void su --manila misura **6,12:1**, sopra il 4,5:1 che AA
 * chiede a un corpo di testo.
 *
 * ⚠️ Il caldo qui SIGNIFICA (§11.6 regola 2): manila e' l'identita' della
 * cartella nel riferimento, non una decorazione scelta per alzare una metrica.
 * Un pannello che non fosse una cartella non puo' prendersi questa superficie.
 */
.pnl-cart__corpo {
  overflow-y: auto;
  padding: var(--s-1) 0;
  background: var(--manila);
  color: var(--bg-void);
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
/* Sotto il puntatore la cartella «si illumina a --manila piu' chiaro» — §26.5
   alla lettera, e --manila-viva esiste in tokens.css apposta. Su superficie
   calda --fill-1 sarebbe un salto di temperatura, non di stato. */
.pnl-cart__riga:hover { background: var(--manila-viva); }
.pnl-cart__segno {
  flex: 0 0 auto;
  width: var(--s-2);
  height: var(--s-2);
  background: var(--bg-panel);
}
/* Il segno si inverte con la superficie: su fondo manila un quadrato manila
   non si vede. Il file prende il colore del testo, la cartella resta fredda —
   la distinzione fra i due tipi resta, letta al contrario. */
.pnl-cart__riga[data-tipo="file"] .pnl-cart__segno { background: var(--bg-void); }
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
  /* --txt-ghost e' tarato sul fondo freddo e su manila sparisce. --bg-panel
     (L 31) fa 4,79:1 sul caldo: leggibile quando lo si cerca, e un gradino
     sotto il nome del file, che e' la gerarchia che serve. */
  color: var(--bg-panel);
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

/* ⑤ il piede — e il suo border-top RESTA, §10.5 non lo tocca.
   Quel che §10.5 ha smontato e' la CORNICE: un tratto che gira intorno e
   ridisegna un confine che il gradino di luminanza gia' dichiara. Questa linea
   non gira intorno a niente, sta dentro il pannello e divide due sue parti —
   il contenuto dal referto. Toglierla non semplificherebbe la sagoma, farebbe
   galleggiare il percorso in fondo all'elenco come se fosse una voce. */
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
