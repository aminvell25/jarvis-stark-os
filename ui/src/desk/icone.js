/* Il fondo della scrivania — SPEC-26 §26.5.
 *
 * Icone libere e cartelle contenitore: cio' che l'utente tira fuori dal
 * catalogo e lascia sul piano di lavoro.
 *
 * ## Il catalogo e' l'INDICE, la scrivania e' il piano
 *
 * §26.5 lo mette per primo, e da li' discende tutto il resto: **l'icona nel
 * catalogo non sparisce.** Un indice a cui si tolgono le voci smette di essere
 * un indice, e la voce tolta non si saprebbe piu' dove ritrovarla. Quindi
 * quello che accade trascinando fuori non e' uno spostamento: e' una COPIA
 * sul fondo, che rimanda alla stessa cosa.
 *
 * Da qui la forma dell'identita': un'icona non ha un id proprio, e' la coppia
 * `(tipo, nome)` — vedi `core/layout.py`, R92. La stessa voce trascinata fuori
 * due volte e' la stessa icona, non due.
 *
 * ## Tre piani, e questo e' il piu' basso che si veda
 *
 * §26.5: «Le icone libere stanno sotto i pannelli e sopra il nucleo di §25.»
 * Lo strato ha `z-index: var(--z-icone)` (5), sta nel `body` e **non** dentro
 * `#scrivania`, che e' la cornice e va sopra i pannelli.
 *
 * ⚠️ Lo strato ha `pointer-events: none` e solo le icone lo riprendono: senza,
 * un rettangolo invisibile grande quanto lo schermo intercetterebbe ogni clic
 * destinato ai pannelli sotto. E' lo stesso inciampo che il catalogo ha gia'
 * avuto col proprio contenitore.
 *
 * ## Cio' che si ha in mano si vede sempre
 *
 * Mentre si trascina, l'icona non e' disegnata al proprio piano ma a
 * `--z-trascino`, sopra tutto. Al proprio piano sparirebbe dietro il primo
 * pannello attraversato, e si trascinerebbe alla cieca.
 *
 * ## Chi crea una cartella? (R93)
 *
 * §26.5 descrive che cosa fa una cartella e non dice mai da dove nasce. Senza
 * una risposta, meta' della sezione — «lasciare un'icona sopra una cartella la
 * mette dentro» — non e' raggiungibile.
 *
 * La risposta e' il **menu contestuale**, che §26.5 nomina gia' come una delle
 * due strade per togliere un'icona («si rimuove trascinandola sul catalogo o
 * dal menu contestuale»). Esiste quindi nel modello della sezione: qui crea,
 * oltre a togliere. Non un pulsante sul plinto — quelle sono le azioni
 * sull'AMBIENTE (nascondi, affianca, filtro), e «crea una cartella qui» ha un
 * QUI che solo il puntatore conosce.
 */

import * as pannelloCartella from "../panels/cartella.js";
import { tokPx } from "../style/tokens.js";

import { modulo } from "./moduli.js";

export const meta = { nome: "icone", versione: "1" };

//: Quanto deve muoversi il puntatore perche' una pressione diventi un
//: trascinamento. Sotto, e' un clic — e un doppio clic non deve mai spostare
//: l'icona di un pixel mentre lo si fa.
export const SOGLIA_TRASCINO = 4;

//: Quanto di un'icona resta a schermo quando l'area si stringe. Stesso numero
//: e stessa ragione del `MIN_VISIBILE` dei pannelli: cio' che non si vede non
//: si riprende.
const MIN_VISIBILE = 40;

export const css = `
/* Lo strato. Copre la scrivania e non tocca nessun evento: lo riprendono solo
   le icone, e solo loro. */
.ico-fondo {
  position: fixed;
  inset: 0;
  z-index: var(--z-icone);
  pointer-events: none;
}
.ico-fondo > * { pointer-events: auto; }

/* ── un'icona libera ─────────────────────────────────────────────────────── */

.ico {
  position: absolute;
  width: calc(var(--grid) * 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s-1);
  padding: var(--s-1);
  background: none;
  border: var(--line-hair) solid transparent;
  border-radius: var(--radius);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  text-align: center;
  cursor: grab;
  touch-action: none;
  user-select: none;
  transition: background 120ms linear, color 120ms linear;
}
.ico:hover { background: var(--fill-1); color: var(--icona-viva); }
.ico:focus-visible { outline: var(--line-base) solid var(--cy-500); }
.ico[data-preso] { cursor: grabbing; }

/* Il segno e' RIEMPITO, come le tessere del catalogo: §26.3 ha misurato che
   la differenza fra il riferimento e noi e' tutta li'. */
.ico__segno {
  width: var(--s-4);
  height: var(--s-4);
  background: var(--icona);
  transition: background 120ms linear;
}
.ico:hover .ico__segno { background: var(--icona-viva); }
.ico[data-tipo="file"] .ico__segno { background: var(--manila); }
.ico__nome {
  width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ── una cartella contenitore ────────────────────────────────────────────── */

.ico-cart {
  position: absolute;
  width: calc(var(--grid) * 0.9);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0;
  background: none;
  border: 0;
  border-radius: var(--radius);
  cursor: grab;
  touch-action: none;
  user-select: none;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  text-align: left;
}
.ico-cart[data-preso] { cursor: grabbing; }
/* La linguetta della cartella manila del riferimento: un rettangolo corto
   sopra il corpo, sfalsato a sinistra. */
.ico-cart__linguetta {
  width: 45%;
  height: var(--s-2);
  background: var(--manila);
  transition: background 120ms linear;
}
.ico-cart__corpo {
  display: flex;
  flex-direction: column;
  gap: var(--s-1);
  padding: var(--s-2);
  background: var(--manila);
  color: var(--bg-void);
  transition: background 120ms linear;
}
/* §26.5: «La cartella si illumina a --manila piu' chiaro mentre il puntatore
   e' sopra». Vale sia col puntatore libero sia con un'icona in mano, e sono
   due cose diverse: la seconda dice «se lascio adesso, entra qui». */
.ico-cart:hover .ico-cart__linguetta,
.ico-cart:hover .ico-cart__corpo,
.ico-cart[data-sopra] .ico-cart__linguetta,
.ico-cart[data-sopra] .ico-cart__corpo { background: var(--manila-viva); }
.ico-cart[data-sopra] { outline: var(--line-bold) solid var(--manila-viva); }
.ico-cart__nome {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  text-transform: uppercase;
}
/* Il conteggio: SEMPRE, e zero e' uno stato (§26.5, invariante 23). */
.ico-cart__conteggio { letter-spacing: 0.10em; }
.ico-cart__nome[contenteditable] {
  background: var(--bg-void);
  color: var(--txt-primary);
  outline: var(--line-base) solid var(--cy-500);
  text-transform: none;
}

/* ── quello che si ha in mano ────────────────────────────────────────────── */

.ico-mano {
  position: fixed;
  z-index: var(--z-trascino);
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s-1);
  padding: var(--s-1);
  background: var(--bg-raised);
  border: var(--line-base) solid var(--cy-700);
  border-radius: var(--radius);
  color: var(--icona-viva);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  max-width: calc(var(--grid) * 1.2);
}
.ico-mano[hidden] { display: none; }
.ico-mano__segno {
  width: var(--s-4);
  height: var(--s-4);
  background: var(--icona);
}
.ico-mano__nome {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* Cosa succede se lascio adesso. Tre esiti, tre stati, nessuna parola. */
.ico-mano[data-esito="rimuovi"] { border-color: var(--amber); color: var(--amber); }
.ico-mano[data-esito="cartella"] { border-color: var(--manila-viva); }

/* Il catalogo diventa il bersaglio di rimozione. §26.5: «si rimuove
   trascinandola sul catalogo». Il coinvolgimento e' a SENSO UNICO e passa da
   un attributo sul body: questo modulo non entra nel DOM del catalogo, e il
   catalogo non sa che questo modulo esiste. */
body[data-trascino="rimuovi"] .cat { border-color: var(--amber); }

/* ── il menu contestuale ─────────────────────────────────────────────────── */

.ico-menu {
  position: fixed;
  z-index: var(--z-trascino);
  min-width: calc(var(--grid) * 1.4);
  display: flex;
  flex-direction: column;
  background: var(--bg-raised);
  border: var(--line-base) solid var(--cy-700);
  border-radius: var(--radius);
  padding: var(--s-1) 0;
}
.ico-menu[hidden] { display: none; }
.ico-menu__voce {
  background: none;
  border: 0;
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-3);
  text-align: left;
  cursor: pointer;
  color: var(--txt-primary);
  font-family: var(--font-ui);
  font-size: var(--t-data);
  transition: background 120ms linear;
}
.ico-menu__voce:hover { background: var(--fill-2); }
.ico-menu__titolo {
  padding: var(--s-1) var(--s-3);
  color: var(--txt-ghost);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
`;

/* ── il componente ───────────────────────────────────────────────────────── */

const chiave = (tipo, nome) => `${tipo} ${nome}`;

/**
 * `suCambio()` viene chiamata a ogni modifica del fondo: e' la stessa strada
 * che i pannelli percorrono con `suGeometria`, e finisce nel debounce di
 * `desk/layout.js`. Qui non c'e' nessun freno di proposito.
 */
export function crea(ospite, { scrivania, bus, suCambio } = {}) {
  const strato = document.createElement("div");
  strato.className = "ico-fondo";
  ospite.appendChild(strato);

  const mano = document.createElement("div");
  mano.className = "ico-mano";
  mano.hidden = true;
  const manoSegno = document.createElement("span");
  manoSegno.className = "ico-mano__segno";
  const manoNome = document.createElement("span");
  manoNome.className = "ico-mano__nome";
  mano.append(manoSegno, manoNome);
  document.body.appendChild(mano);

  const menu = document.createElement("div");
  menu.className = "ico-menu";
  menu.hidden = true;
  document.body.appendChild(menu);

  //: chiave -> { tipo, nome, x, y, dentro, el }
  const icone = new Map();
  //: id -> { id, x, y, etichetta, aperta, el }
  const cartelle = new Map();
  //: id della cartella -> il pannello aperto, per aggiornarlo sul posto.
  const pannelli = new Map();
  //: L'ultima radice vista da `fs.list`. E' il percorso RISOLTO che §26.5
  //: vuole nel piede di una cartella che contenga file veri — e non sta nel
  //: layout: nel layout non finisce nessun percorso (`core/layout.py`).
  let radice = null;
  let trascino = null;
  let prossimaCartella = 1;

  const avvisa = () => suCambio?.();

  /* ── etichette ────────────────────────────────────────────────────────── */

  /** Come si chiama una voce. Per un modulo lo sa `moduli.js`; per un file, e'
   *  il nome del file — che e' dato NON FIDATO e non viene mai interpretato. */
  function etichettaDi(tipo, nome) {
    if (tipo !== "modulo") return nome;
    return modulo(nome)?.etichetta ?? nome;
  }

  /* ── disegno ──────────────────────────────────────────────────────────── */

  function nuovoElementoIcona(ic) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "ico";
    el.dataset.tipo = ic.tipo;
    el.dataset.nome = ic.nome;
    const segno = document.createElement("span");
    segno.className = "ico__segno";
    const nome = document.createElement("span");
    nome.className = "ico__nome";
    el.append(segno, nome);
    el.addEventListener("pointerdown", (e) => prendi(e, { icona: ic }));
    el.addEventListener("dblclick", () => apriIcona(ic));
    el.addEventListener("contextmenu", (e) => menuIcona(e, ic));
    strato.appendChild(el);
    return el;
  }

  function nuovoElementoCartella(c) {
    const el = document.createElement("div");
    el.className = "ico-cart";
    el.dataset.cartella = c.id;
    el.tabIndex = 0;
    const linguetta = document.createElement("span");
    linguetta.className = "ico-cart__linguetta";
    const corpo = document.createElement("span");
    corpo.className = "ico-cart__corpo";
    const nome = document.createElement("span");
    nome.className = "ico-cart__nome";
    const conteggio = document.createElement("span");
    conteggio.className = "ico-cart__conteggio";
    corpo.append(nome, conteggio);
    el.append(linguetta, corpo);
    el.addEventListener("pointerdown", (e) => prendi(e, { cartella: c }));
    el.addEventListener("dblclick", () => apriCartella(c));
    el.addEventListener("contextmenu", (e) => menuCartella(e, c));
    strato.appendChild(el);
    return el;
  }

  /**
   * Rimette a posto cio' che e' gia' a schermo. **Non ricostruisce.**
   *
   * ⚠️ E' la lezione di R90, presa la prima volta invece che la seconda: il
   * catalogo rifaceva la propria griglia a ogni cambio di stato, e perdeva il
   * fuoco, l'hover e il pulsante che si stava premendo. Qui i nodi si creano
   * quando l'icona nasce e si distruggono quando muore; in mezzo si aggiornano
   * sul posto.
   */
  function disegna() {
    for (const ic of icone.values()) {
      if (!ic.el) ic.el = nuovoElementoIcona(ic);
      // Un'icona dentro una cartella non sta sul fondo: la si vede aprendo la
      // cartella. `hidden` e non `remove()`, perche' tornera' fuori.
      ic.el.hidden = !!ic.dentro;
      ic.el.style.left = `${ic.x}px`;
      ic.el.style.top = `${ic.y}px`;
      const etichetta = etichettaDi(ic.tipo, ic.nome);
      ic.el.querySelector(".ico__nome").textContent = etichetta;
      ic.el.title = `${etichetta} — doppio clic per aprire`;
    }
    for (const c of cartelle.values()) {
      if (!c.el) c.el = nuovoElementoCartella(c);
      c.el.style.left = `${c.x}px`;
      c.el.style.top = `${c.y}px`;
      const n = dentroLa(c.id).length;
      c.el.querySelector(".ico-cart__nome").textContent = c.etichetta;
      // §26.5: il conteggio c'e' SEMPRE, e zero e' uno stato esplicito.
      c.el.querySelector(".ico-cart__conteggio").textContent =
        n === 0 ? "vuota · 0" : `${n} ${n === 1 ? "voce" : "voci"}`;
      c.el.title = `${c.etichetta} — ${n === 0 ? "vuota" : `${n} dentro`}`;
    }
    for (const [id, p] of pannelli) aggiornaPannello(id, p);
  }

  function dentroLa(id) {
    return [...icone.values()].filter((i) => i.dentro === id);
  }

  /* ── il trascinamento ─────────────────────────────────────────────────── */

  function prendi(e, cosa) {
    if (e.button !== 0) return;
    const el = cosa.icona?.el ?? cosa.cartella?.el;
    const r = el.getBoundingClientRect();
    trascino = {
      ...cosa,
      id: e.pointerId,
      x0: e.clientX, y0: e.clientY,
      dx: e.clientX - r.left, dy: e.clientY - r.top,
      mosso: false,
      origine: "fondo",
    };
    el.setPointerCapture(e.pointerId);
    el.dataset.preso = "";
    e.preventDefault();
  }

  function muoviInterno(e) {
    if (!trascino || e.pointerId !== trascino.id || trascino.origine !== "fondo") return;
    if (!trascino.mosso &&
        Math.hypot(e.clientX - trascino.x0, e.clientY - trascino.y0) < SOGLIA_TRASCINO)
      return;
    trascino.mosso = true;
    muovi(e.clientX, e.clientY);
  }

  function rilasciaInterno(e) {
    if (!trascino || e.pointerId !== trascino.id || trascino.origine !== "fondo") return;
    const el = trascino.icona?.el ?? trascino.cartella?.el;
    delete el.dataset.preso;
    if (!trascino.mosso) { trascino = null; return; }   // era un clic
    lascia(e.clientX, e.clientY);
  }

  document.addEventListener("pointermove", muoviInterno);
  document.addEventListener("pointerup", rilasciaInterno);
  document.addEventListener("pointercancel", rilasciaInterno);

  /* ── che cosa c'e' sotto il puntatore ─────────────────────────────────── */

  /**
   * Si misura sui rettangoli, non con `elementFromPoint`.
   *
   * ⚠️ Durante un trascinamento il puntatore e' CATTURATO dall'elemento che si
   * sta muovendo — o, per l'estrazione, dalla vista del catalogo — e
   * `elementFromPoint` risponderebbe sull'elemento in mano invece che su
   * quello sotto. I rettangoli non hanno questo problema.
   */
  function bersaglio(x, y) {
    for (const c of cartelle.values()) {
      if (trascino?.cartella === c) continue;      // una cartella non entra in se'
      const r = c.el.getBoundingClientRect();
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom)
        return { tipo: "cartella", cartella: c };
    }
    const cat = document.querySelector(".cat");
    if (cat) {
      const r = cat.getBoundingClientRect();
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom)
        return { tipo: "catalogo" };
    }
    return { tipo: "fondo" };
  }

  /**
   * Che cosa accade lasciando qui. Dipende da DOVE si era preso:
   *
   *   dal fondo    sul catalogo -> si rimuove (§26.5)
   *   dal catalogo sul catalogo -> non succede niente: e' un gesto annullato
   *
   * Un'estrazione lasciata a meta' non deve togliere l'icona dall'indice: e'
   * il primo modo in cui un utente prova un gesto nuovo.
   */
  function esitoDi(b) {
    if (b.tipo === "cartella") return "cartella";
    if (b.tipo === "catalogo")
      return trascino?.origine === "catalogo" ? "annulla" : "rimuovi";
    return "fondo";
  }

  function muovi(x, y) {
    if (!trascino) return;
    const b = bersaglio(x, y);
    const esito = esitoDi(b);
    mano.hidden = false;
    mano.style.left = `${x - trascino.dx}px`;
    mano.style.top = `${y - trascino.dy}px`;
    mano.dataset.esito = esito;
    manoNome.textContent = trascino.voce
      ? trascino.voce.etichetta
      : trascino.icona
        ? etichettaDi(trascino.icona.tipo, trascino.icona.nome)
        : (trascino.cartella?.etichetta ?? "");
    // Cio' che si sta muovendo si nasconde al proprio piano: e' in mano.
    const el = trascino.icona?.el ?? trascino.cartella?.el;
    if (el) el.style.visibility = "hidden";

    for (const c of cartelle.values()) {
      if (b.cartella === c) c.el.dataset.sopra = "";
      else delete c.el.dataset.sopra;
    }
    document.body.dataset.trascino = esito;
  }

  function ripulisciMano() {
    mano.hidden = true;
    delete mano.dataset.esito;
    delete document.body.dataset.trascino;
    for (const c of cartelle.values()) delete c.el.dataset.sopra;
    const el = trascino?.icona?.el ?? trascino?.cartella?.el;
    if (el) el.style.visibility = "";
  }

  function lascia(x, y) {
    if (!trascino) return;
    const b = bersaglio(x, y);
    const esito = esitoDi(b);
    const t = trascino;
    ripulisciMano();
    trascino = null;

    if (esito === "annulla") return;

    if (esito === "rimuovi") {
      if (t.icona) togliIcona(t.icona);
      else if (t.cartella) togliCartella(t.cartella);
      return;
    }

    const posizione = dentroArea(x - t.dx, y - t.dy);

    if (esito === "cartella") {
      // Una cartella non si mette dentro un'altra: §26.5 dice «una cartella
      // contiene altre icone», non altre cartelle, e l'annidamento porterebbe
      // con se' un albero, un percorso e la domanda «dove sono adesso».
      if (t.cartella) { t.cartella.x = posizione.x; t.cartella.y = posizione.y; }
      else {
        const ic = assicura(t.icona ?? t.voce);
        ic.dentro = b.cartella.id;
      }
      disegna();
      avvisa();
      return;
    }

    if (t.cartella) { t.cartella.x = posizione.x; t.cartella.y = posizione.y; }
    else {
      const ic = assicura(t.icona ?? t.voce);
      ic.dentro = null;
      ic.x = posizione.x;
      ic.y = posizione.y;
    }
    disegna();
    avvisa();
  }

  /** L'icona esiste gia' (la si stava spostando) oppure nasce adesso. */
  function assicura(voce) {
    const k = chiave(voce.tipo, voce.nome);
    let ic = icone.get(k);
    if (!ic) {
      ic = { tipo: voce.tipo, nome: voce.nome, x: 0, y: 0, dentro: null, el: null };
      icone.set(k, ic);
    }
    return ic;
  }

  function dentroArea(x, y) {
    const a = scrivania?.misura?.() ?? {
      sinistra: 0, alto: 0, larghezza: window.innerWidth, altezza: window.innerHeight,
    };
    return {
      x: Math.round(Math.max(a.sinistra,
                             Math.min(x, a.sinistra + a.larghezza - MIN_VISIBILE))),
      y: Math.round(Math.max(a.alto,
                             Math.min(y, a.alto + a.altezza - MIN_VISIBILE))),
    };
  }

  /* ── l'estrazione dal catalogo ────────────────────────────────────────── */

  /**
   * Le tre chiamate che il catalogo fa mentre si tira fuori un'icona.
   *
   * Il catalogo non sa che cosa sia un'icona libera: riporta un gesto —
   * comincia, si muove, si lascia — e da qui in poi decide questo modulo. E'
   * la stessa forma con cui `scrivania.js` riceve gli intenti dalla voce e
   * dalle gesture: quattro strade, un punto solo dove finiscono.
   */
  const estrazione = {
    inizia(voce, x, y) {
      /* `dx`/`dy` a zero: l'icona che NASCE adesso pende dal puntatore, e li'
       * si posera'. Per un'icona gia' sul fondo sono lo scarto fra il punto
       * afferrato e l'angolo, perche' quella deve restare ferma sotto il dito
       * mentre la si sposta. Due gesti diversi, due ancoraggi diversi. */
      trascino = { voce, id: -1, dx: 0, dy: 0, mosso: true, origine: "catalogo" };
      muovi(x, y);
    },
    muovi(x, y) { if (trascino?.origine === "catalogo") muovi(x, y); },
    lascia(x, y) { if (trascino?.origine === "catalogo") lascia(x, y); },
    annulla() {
      if (trascino?.origine !== "catalogo") return;
      ripulisciMano();
      trascino = null;
    },
  };

  /* ── aprire ───────────────────────────────────────────────────────────── */

  function apriIcona(ic) {
    if (ic.tipo === "modulo") return scrivania?.apri(ic.nome);
    // §26.8, punto 9: aprire un FILE e' del file manager, che non c'e'
    // ancora. La voce porta al pannello che sapra' farlo, invece di fingere
    // un'operazione che nessuno esegue. E' la stessa scelta gia' fatta dalle
    // tessere della linguetta FILE del catalogo.
    return scrivania?.apri("file");
  }

  /**
   * Apre una cartella come PANNELLO (§26.5).
   *
   * Passa da `scrivania.registra()` e poi da `scrivania.apri()`, cioe' dalla
   * stessa strada di ogni altro pannello: cosi' la cartella si trascina dalla
   * testa, ha i tre controlli veri, entra nella disposizione salvata e si
   * riapre al riavvio. Un'apertura tutta sua sarebbe un secondo modo di fare
   * una finestra, e i due divergerebbero.
   */
  async function apriCartella(c) {
    scrivania?.registra({
      id: c.id,
      etichetta: c.etichetta,
      categoria: 2,               // File e progetti
      // La cella e' la posizione INIZIALE (ADR-010), non una gabbia: un
      // rettangolo piccolo in mezzo, che poi l'utente sposta dove vuole.
      cella: [4, 1, 4, 2],
      componente: pannelloCartella,
      opzioni: { apri: (voce) => apriIcona(voce) },
      alimenta: (p) => { pannelli.set(c.id, p); aggiornaPannello(c.id, p); },
      suChiusura: () => {
        pannelli.delete(c.id);
        c.aperta = false;
        scrivania?.dimentica(c.id);
        avvisa();
      },
    });
    const cornice = await scrivania?.apri(c.id);
    if (!cornice) return null;
    c.aperta = true;
    avvisa();
    return cornice;
  }

  function aggiornaPannello(id, p) {
    const c = cartelle.get(id);
    if (!c || !p) return;
    p.aggiorna({
      etichetta: c.etichetta,
      voci: dentroLa(id).map((i) => ({
        tipo: i.tipo, nome: etichettaDi(i.tipo, i.nome), rif: i,
      })),
      radice,
    });
  }

  /* ── togliere ─────────────────────────────────────────────────────────── */

  function togliIcona(ic) {
    ic.el?.remove();
    icone.delete(chiave(ic.tipo, ic.nome));
    disegna();
    avvisa();
  }

  /**
   * Togliere una cartella non toglie cio' che conteneva.
   *
   * ⚠️ Le icone tornano sul FONDO, accanto a dov'era la cartella. Farle sparire
   * insieme al contenitore sarebbe una cancellazione mascherata da riordino, ed
   * e' esattamente l'errore contro cui §26.5 mette in guardia quando distingue
   * le cartelle dell'ambiente da quelle del filesystem.
   */
  function togliCartella(c) {
    let i = 0;
    const passo = tokPx("--s-5");
    for (const ic of dentroLa(c.id)) {
      const p = dentroArea(c.x + (i % 3) * passo, c.y + Math.floor(i / 3) * passo);
      ic.dentro = null;
      ic.x = p.x;
      ic.y = p.y;
      i++;
    }
    if (pannelli.has(c.id)) scrivania?.chiudi(c.id);
    scrivania?.dimentica(c.id);
    c.el?.remove();
    cartelle.delete(c.id);
    disegna();
    avvisa();
  }

  /* ── il menu contestuale ──────────────────────────────────────────────── */

  function mostraMenu(x, y, titolo, voci) {
    menu.textContent = "";
    const t = document.createElement("div");
    t.className = "ico-menu__titolo";
    t.textContent = titolo;
    menu.appendChild(t);
    for (const [etichetta, fai] of voci) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "ico-menu__voce";
      b.textContent = etichetta;
      b.addEventListener("click", () => { chiudiMenu(); fai(); });
      menu.appendChild(b);
    }
    menu.hidden = false;
    // Si misura DOPO averlo mostrato: un menu nascosto ha rettangolo zero, e
    // finirebbe sempre a filo del bordo.
    const r = menu.getBoundingClientRect();
    menu.style.left = `${Math.min(x, window.innerWidth - r.width)}px`;
    menu.style.top = `${Math.min(y, window.innerHeight - r.height)}px`;
  }

  function chiudiMenu() { menu.hidden = true; }

  document.addEventListener("pointerdown", (e) => {
    if (!menu.hidden && !menu.contains(e.target)) chiudiMenu();
  }, true);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") chiudiMenu();
  });

  function menuIcona(e, ic) {
    e.preventDefault();
    e.stopPropagation();
    mostraMenu(e.clientX, e.clientY, etichettaDi(ic.tipo, ic.nome), [
      ["apri", () => apriIcona(ic)],
      ["rimuovi dalla scrivania", () => togliIcona(ic)],
    ]);
  }

  function menuCartella(e, c) {
    e.preventDefault();
    e.stopPropagation();
    mostraMenu(e.clientX, e.clientY, c.etichetta, [
      ["apri", () => apriCartella(c)],
      ["rinomina", () => rinomina(c)],
      ["rimuovi (le icone tornano sul fondo)", () => togliCartella(c)],
    ]);
  }

  /**
   * Il fondo della scrivania: tutto cio' che non e' un pannello, la cornice o
   * un'icona. Si riconosce per esclusione e non per bersaglio positivo, perche'
   * lo strato ha `pointer-events: none` e il clic arriva a qualunque cosa ci
   * sia sotto — che al primo avvio e' `#scrivania`, ma domani potrebbe essere
   * il nucleo di §25.
   */
  const NON_E_IL_FONDO = ".winbox, .brr, .dock, .cat, .ico, .ico-cart, .ico-menu";

  document.addEventListener("contextmenu", (e) => {
    if (e.target.closest(NON_E_IL_FONDO)) return;
    e.preventDefault();
    const p = dentroArea(e.clientX, e.clientY);
    mostraMenu(e.clientX, e.clientY, "scrivania", [
      ["nuova cartella qui", () => nuovaCartella(p.x, p.y)],
    ]);
  });

  function rinomina(c) {
    const nome = c.el?.querySelector(".ico-cart__nome");
    if (!nome) return;
    nome.contentEditable = "plaintext-only";
    nome.textContent = c.etichetta;
    nome.focus();
    getSelection()?.selectAllChildren(nome);
    const fine = () => {
      nome.contentEditable = "false";
      // Il taglio a 64 e' quello dello schema (`core/layout.py`): tagliare qui
      // significa che l'utente vede subito quanto ne e' entrato, invece di
      // scoprirlo al prossimo avvio quando il core rifiuta.
      c.etichetta = (nome.textContent ?? "").trim().slice(0, 64) || c.etichetta;
      disegna();
      avvisa();
    };
    nome.addEventListener("blur", fine, { once: true });
    nome.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); nome.blur(); }
    });
  }

  function nuovaCartella(x, y) {
    while (cartelle.has(`cartella.${prossimaCartella}`)) prossimaCartella++;
    const id = `cartella.${prossimaCartella}`;
    const c = { id, x, y, etichetta: `cartella ${prossimaCartella}`,
                aperta: false, el: null };
    cartelle.set(id, c);
    disegna();
    avvisa();
    return c;
  }

  /* ── verso il core, e dal core ────────────────────────────────────────── */

  /** La forma che `core/layout.py` accetta. Niente `el`, niente percorsi. */
  function stato() {
    return {
      icone: [...icone.values()].map((i) => ({
        tipo: i.tipo, nome: i.nome, x: i.x, y: i.y, dentro: i.dentro ?? null,
      })),
      cartelle: [...cartelle.values()].map((c) => ({
        id: c.id, x: c.x, y: c.y, etichetta: c.etichetta, aperta: !!c.aperta,
      })),
    };
  }

  /**
   * Rimette il fondo come era. Va chiamata **prima** di `scrivania.ripristina()`:
   * un pannello-cartella salvato si riapre solo se la sua cartella esiste gia'.
   *
   * ⚠️ Un'icona il cui `dentro` nomina una cartella che non c'e' piu' finisce
   * SUL FONDO invece di sparire. E' la stessa regola del pannello tolto da
   * `moduli.js`: un ambiente non deve perdere roba perche' ricorda male.
   */
  async function ripristina(layout) {
    for (const c of layout?.cartelle ?? []) {
      if (!/^cartella\.\d+$/.test(String(c.id))) continue;
      cartelle.set(c.id, {
        id: c.id, x: c.x | 0, y: c.y | 0,
        etichetta: String(c.etichetta ?? "") || c.id,
        aperta: !!c.aperta, el: null,
      });
    }
    for (const i of layout?.icone ?? []) {
      if (i.tipo !== "modulo" && i.tipo !== "file") continue;
      const dentro = cartelle.has(i.dentro) ? i.dentro : null;
      icone.set(chiave(i.tipo, i.nome), {
        tipo: i.tipo, nome: String(i.nome), x: i.x | 0, y: i.y | 0, dentro, el: null,
      });
    }
    disegna();
    // Le cartelle che erano aperte si riaprono. Dopo il disegno, perche'
    // `apriCartella` registra un modulo che `scrivania.ripristina()` cerchera'.
    for (const c of cartelle.values()) if (c.aperta) await apriCartella(c);
    return { icone: icone.size, cartelle: cartelle.size };
  }

  bus?.su("fs.list", (m) => {
    radice = m?.path ?? null;
    for (const [id, p] of pannelli) aggiornaPannello(id, p);
  });

  // L'area cambia: chi e' finito fuori rientra. Stessa regola dei pannelli —
  // chi era dentro non si muove di un pixel (R82).
  window.addEventListener("resize", () => {
    let cambiato = false;
    for (const cosa of [...icone.values(), ...cartelle.values()]) {
      if (cosa.dentro) continue;
      const p = dentroArea(cosa.x, cosa.y);
      if (p.x === cosa.x && p.y === cosa.y) continue;
      cosa.x = p.x;
      cosa.y = p.y;
      cambiato = true;
    }
    if (cambiato) { disegna(); avvisa(); }
  });

  return {
    strato, estrazione, stato, ripristina,
    nuovaCartella, apriCartella, disegna,
    get icone() { return [...icone.values()]; },
    get cartelle() { return [...cartelle.values()]; },
  };
}
