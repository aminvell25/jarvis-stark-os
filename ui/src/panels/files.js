/* Pannello file manager — SPEC §13, §10.2.
 *
 * Mostra il contenuto di una directory consentita, coi dati che il core manda
 * da `list_dir`. Non tocca il disco e non puo' toccarlo: l'invariante 1 dice
 * che il renderer non tocca mai il disco, e questo pannello non ha nemmeno
 * modo di chiedere un'operazione — il preload espone solo la risposta a una
 * conferma (§6.2).
 *
 * Tre stati come il pannello telemetria: collegato, vuoto, galleria.
 */

export const meta = { nome: "files", versione: "1" };

const UNITA = ["B", "KiB", "MiB", "GiB", "TiB"];

function dimensione(b) {
  if (typeof b !== "number") return "—";
  let i = 0, v = b;
  while (v >= 1024 && i < UNITA.length - 1) { v /= 1024; i++; }
  return `${i === 0 ? v : v.toFixed(1)} ${UNITA[i]}`;
}

export const css = `
/* §10.5 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
 *
 * Il corpo passa da --bg-panel (L 31) a --bg-raised (L 37): e' il valore
 * misurato sul corpo del calendario del riferimento, identico a quattro
 * quote, opaco e piatto. Contro il pavimento a L 19 fa +18, ed e' tutto
 * quello che serve a dire dove finisce il pannello. Non c'e' un border da
 * togliere — qui non ce n'e' mai stato uno — e non se ne aggiunge: dei sette
 * pannelli misurati, ZERO hanno un tratto sui quattro lati. Gli angoli li
 * chiudono i due marcatori triangolari di app.css, scritti una volta sola
 * sulla finestra e non diciotto volte nei componenti.
 *
 * ⚠️ Qui c'era scritto che --aug-border-bg doveva RESTARE a --cy-900, perche'
 * toglierlo lo fa ripiegare su currentColor. La premessa e' vera, la
 * conclusione no: fra «lasciarlo acceso» e «cancellarlo» c'e' il terzo caso,
 * cioe' spegnerne l'inchiostro. Lo scatto ha deciso — l'anello misurava 4 px
 * pieni di --cy-900 su tutti e quattro i lati, che e' la cornice di §10.5 e
 * non la sagoma di §10.2: la sagoma e' il CLIP, e il clip resta. */
.pnl-file {
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
  --aug-bl: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* La testa e' una SUPERFICIE, non una riga di testo con un filo sotto
   (§10.5 regola 2). Banda piena a --fill-1: L 66 contro i 37 del corpo,
   +29 L, sopra i +19 che la regola chiede. Il border-bottom hairline se
   n'e' andato perche' diceva col tratto quello che ora dice il gradino, e
   due segni per la stessa separazione sono uno di troppo. L'altezza non si
   tocca: stesso padding, stessa riga di griglia. */
.pnl-file__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  background: var(--fill-1);
}
/* ⚠️ I colori QUI DENTRO sono ritarati sul fondo nuovo, non ereditati.
 * Da L 31 a L 66 il contrasto si dimezza, e i due token che stavano qui non
 * reggono piu': --txt-dim scende da 4,53:1 a 2,73:1 e --txt-ghost a 1,82:1,
 * che non e' testo scarso, e' testo che non c'e'. Rapporto WCAG su luminanza
 * linearizzata, misurato su --fill-1:
 *
 *   etichetta   --cy-300       6,21:1   resta: e' l'accento, e regge
 *   radice      --txt-primary  8,06:1   il percorso e' il NOME della
 *                                       sorgente, e i nomi in questo
 *                                       pannello sono --txt-primary (vedi
 *                                       __nome nel corpo). A --t-micro,
 *                                       8,5 px, vuole il margine piu' largo
 *                                       che la palette abbia.
 *   id, ctrl    --icona        4,31:1   marche tecniche, non dati: un
 *                                       gradino sotto, come nel corpo.
 *
 * Il corpo non e' toccato: il suo fondo si e' mosso di 6 L, non di 35. */
.pnl-file__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-file__radice {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-primary);
  overflow-wrap: anywhere;
}
.pnl-file__id, .pnl-file__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
/* ⚠️ IL CORPO E' MANILA, come nel pannello cartella — ed e' la stessa cosa
   detta due volte perche' e' la stessa cosa: un elenco di file dentro una
   radice E' un contenitore, e nel riferimento un contenitore e' manila.
   §26.5 chiama --manila il colore delle «cartelle e contenitori»: applicarlo
   qui non e' allargarne il significato, e' usarlo dove gia' vale.
   La polarita' si rovescia come in cartella.js: --bg-void su --manila fa
   6,12:1, mentre --txt-primary su --manila farebbe 1,68:1. */
/* ⚠️ IL CALDO SEGUE IL CONTENUTO, non il riquadro — e la differenza si e'
   vista misurando. Col corpo intero a manila questo pannello portava il caldo
   della scrivania a 7,9 %, sopra il tetto di 6 % di §11.8, e la maggior parte
   di quella superficie era **vuota**: la radice mostrata ha una voce sola.
   Una superficie calda grande quanto il riquadro dice «qui c'e' un
   contenitore»; una calda quanto le sue righe dice anche **quanto contiene**,
   ed e' la seconda cosa che serve. Un contenitore vuoto resta un contenitore —
   §26.5, «zero e' uno stato esplicito» — e lo dice il conteggio nel piede, non
   una macchia di colore.
   Il corpo torna freddo; le righe sono manila. */
.pnl-file__corpo { overflow: auto; }
.pnl-file__riga {
  display: grid;
  grid-template-columns: var(--s-4) 1fr calc(var(--grid) - var(--s-2)) calc(var(--grid) - var(--s-3));
  gap: var(--s-2);
  align-items: baseline;
  padding: 0 var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-dim);
}
/* ⚠️ La zebratura si INVERTE, ed e' una conseguenza, non un ritocco: le
   righe pari stavano a --bg-raised su un corpo a --bg-panel, e adesso il
   corpo E' --bg-raised — la riga sarebbe sparita dentro il proprio fondo, e
   una regola morta nel foglio e' peggio di nessuna regola. Stesso gradino di
   6 L, col segno girato: L 31 sotto il corpo a L 37. Verso il basso e non
   verso l'alto perche' fra 37 e 66 non c'e' niente, e --fill-1 e' il
   riempimento della cella ATTIVA (§10.1): metterlo su una riga su due
   direbbe che meta' dell'elenco e' selezionata. */
/* La zebra si inverte una seconda volta, con la superficie: su manila un fondo
   piu' scuro e' quello che stacca, e --manila-viva e' il gradino chiaro che
   §26.5 riserva alla cartella sotto il puntatore — non a una riga su due. */
.pnl-file__riga { background: var(--manila); color: var(--bg-void); }
/* La zebra sparisce: fra --manila e --manila-viva ci sono 33 punti di L, che
   sono cinque volte i sei punti che la ricetta di panels/tabella.js prescrive.
   A separare due righe basta un filetto del colore del corpo.
   ⚠️ Un FILETTO e non un margine: --line-hair vale 0,5 px ed e' una larghezza
   di linea, non una spaziatura. Usarlo come margine ha fatto scattare l'audit
   ventiquattro volte — §11.8 vuole le spaziature multiple di 4 o dalla scala
   --s-*, e ha ragione: un mezzo pixel di margine e' un valore che non
   appartiene a nessuna scala. */
.pnl-file__riga + .pnl-file__riga { border-top: var(--line-hair) solid var(--bg-raised); }
.pnl-file__riga:hover { background: var(--manila-viva); }
.pnl-file__glifo { color: var(--bg-panel); }
.pnl-file__nome { color: var(--bg-void); overflow-wrap: anywhere; }
.pnl-file__cat { color: var(--bg-panel); font-size: var(--t-micro); text-transform: uppercase; letter-spacing: 0.10em; }
.pnl-file__dim { text-align: right; color: var(--bg-panel); }
.pnl-file__piede {
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-file__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-file[data-stato="vuoto"] .pnl-file__corpo { display: none; }
.pnl-file[data-stato="vuoto"] .pnl-file__vuoto { display: block; }
`;

const HTML = `
<section class="pnl-file" data-stato="vuoto" data-augmented-ui="bl-clip border">
  <header class="pnl-file__testa">
    <span class="pnl-file__etichetta">File</span>
    <span class="pnl-file__radice" data-radice>&mdash;</span>
    <span class="pnl-file__id">B02</span>
    <span class="pnl-file__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-file__corpo" data-voci></div>
  <div class="pnl-file__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-file__piede" data-piede></footer>
</section>
`;

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-file");
  const voci = el.querySelector("[data-voci]");
  const piede = el.querySelector("[data-piede]");
  const radice = el.querySelector("[data-radice]");

  function aggiorna(msg) {
    el.dataset.stato = "collegato";
    radice.textContent = msg.path;

    /* ⚠️ R96 — qui c'era un `innerHTML` con i NOMI DEI FILE dentro.
     *
     * Un nome di file arriva dal disco, e l'invariante 5 lo classifica come
     * dato NON FIDATO tanto quanto il contenuto. Un file chiamato con del
     * markup scriveva markup dentro l'interfaccia — e l'interfaccia ha
     * `window.jarvis`, cioe' la funzione che risponde alle conferme di §6.2.
     * Un nome ben scelto in una cartella scaricata poteva approvare da solo
     * un'operazione distruttiva che stava aspettando l'utente.
     *
     * Trovato costruendo §26.5, guardando da dove passano i nomi dei file.
     * Nessun test lo copriva: il corpus di §11.9 verifica i topic, non le
     * stringhe che ci viaggiano dentro. Adesso ce n'e' uno.
     */
    voci.replaceChildren(...(msg.voci ?? []).map((v) => {
      const riga = document.createElement("div");
      riga.className = "pnl-file__riga";
      for (const [classe, testo] of [
        ["pnl-file__glifo", v.type === "dir" ? "\u25a1" : "\u00b7"],
        ["pnl-file__nome", String(v.name ?? "")],
        ["pnl-file__cat", String(v.categoria ?? (v.type === "dir" ? "cartella" : ""))],
        ["pnl-file__dim", v.type === "dir" ? "" : dimensione(v.size)],
      ]) {
        const s = document.createElement("span");
        s.className = classe;
        s.textContent = testo;
        riga.appendChild(s);
      }
      return riga;
    }));

    const totale = (msg.voci ?? []).reduce((n, v) => n + (v.size ?? 0), 0);
    const cartelle = (msg.voci ?? []).filter((v) => v.type === "dir").length;
    piede.textContent =
      `${msg.totale} voci · ${cartelle} cartelle · ${dimensione(totale)} · sola lettura`;
  }

  function stato(s) {
    if (s === "vuoto") {
      el.dataset.stato = "vuoto";
      radice.textContent = "—";
      piede.textContent = "in attesa del core";
    }
  }

  return { el, aggiorna, stato };
}
