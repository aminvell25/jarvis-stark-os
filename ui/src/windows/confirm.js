/* Finestra di conferma — SPEC §6.2, invariante 3.
 *
 * E' l'unico punto in cui un essere umano decide se qualcosa accade davvero.
 * Tre regole ne dettano la forma, e nessuna e' estetica.
 *
 * MOSTRA IL PATH RISOLTO. §6.2 lo dice in maiuscolo: «UI mostra il PATH
 * ASSOLUTO RISOLTO, non quello richiesto». Chi conferma deve vedere dove
 * finira' l'operazione, non cosa e' stato digitato: `~/x/../../etc` e
 * `/etc` sono la stessa richiesta e leggono in modo molto diverso. Il core
 * manda gia' i percorsi risolti — questa finestra non li rielabora.
 *
 * UNA CONFERMA, PIANO COMPLETO. Per 200 file una sola domanda, ma con
 * l'elenco davanti: «mai 200 conferme; mai zero». Un elenco troncato in
 * silenzio sarebbe zero conferme travestite da una.
 *
 * L'AZIONE DISTRUTTIVA NON E' QUELLA COMODA. Il rifiuto e' il pulsante
 * predefinito e ha il focus; approvare richiede di sceglierlo.
 */

export const meta = { nome: "confirm", versione: "1" };

const ETICHETTE = {
  trash: "nel cestino",
  move: "sposta",
  copy: "copia",
  create: "crea",
  mkdir: "crea cartella",
  // ADR-015: il laboratorio. Lo script che gira, la sandbox in cui gira, e il
  // DIFF dall'ultima esecuzione — le ultime due senza percorsi, perche' e' il
  // `dettaglio` che la finestra deve mostrare.
  esegui: "esegue",
  sandbox: "sandbox",
  diff: "diff",
};

export const css = `
.cnf {
  /* Il bordo del pannello e' ciano come ogni altro pannello. Il rosso marca
     la TESTATA e il pulsante che distrugge, non il perimetro: §11.6 regola 2
     lo vuole semantico e sotto il 10% della superficie colorata, e nei
     riferimenti di famiglia-A segna intestazioni e valori critici, mai
     cornici intere. Cerchiare tutto di rosso e' decorazione con l'aria
     dell'allarme. */
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
  --aug-tl: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  /* §10.5 regola 1 — una finestra e' un GRADINO DI LUMINANZA, non una
     cornice. Dei sette pannelli misurati sul riferimento ZERO hanno un tratto
     di bordo sui quattro lati: cio' che dice dove finisce la finestra e' il
     salto contro il pavimento. Da --bg-panel (L 31) a --bg-raised (L 37), che
     e' il #1e2631 letto identico a quattro quote sul calendario: opaco e
     piatto, nessun velo. Contro il pavimento a L 19 fa +18.
     Gli angoli li chiudono i due marcatori triangolari, che stanno una volta
     sola sulla finestra in style/app.css e qui non si rifanno. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE, non una riga di testo con un
   filo sotto: sul fondo del corpo sarebbe testo, non testata. Banda piena a
   --fill-1, misurata a L 65,7 sul calendario del riferimento: contro i 37 del
   corpo e' un gradino di +29, sopra il minimo di +19 letto sui sette pannelli,
   e con la polarita' del calendario — banda piu' chiara, testo chiaro — che
   §10.5 adotta fra le tre del riferimento. Altezza e padding non si toccano, e
   non serve toccarli: misurata in galleria, la banda e' 32 px su 420 di
   finestra, il 7,62 %, dentro la forbice 6-9 % del riferimento.

   ⚠️ Il border-bottom RESTA, e cambia mestiere: non separa piu' — a 29 L di
   distanza le due superfici si separano da sole — ma dice che questa non e'
   una finestra qualunque, e' quella dell'invariante 3. Il rosso ha dovuto
   lasciare l'etichetta, dove su --fill-1 misura 3,19:1 e a 12 px non e' piu'
   leggibile, e si e' spostato sul filo, dove la soglia e' quella degli
   oggetti grafici (3:1, WCAG 1.4.11) e 3,19:1 la passa. E' la stessa mossa
   della linguetta di panels/cartella.js: il colore d'identita' scende dal
   testo al segno invece di sparire. */
.cnf__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  background: var(--fill-1);
  border-bottom: var(--line-base) solid var(--rust);
}
/* ⚠️ I testi della testa sono RITARATI sul fondo nuovo, non ereditati: la
   banda e' passata da L 31 a L 66 e ogni rapporto WCAG cambia. Su luminanza
   linearizzata, misurati su --fill-1:

     --rust         3,19:1  era l'etichetta. Sotto ogni soglia di testo.
     --txt-dim      2,73:1  erano id e controlli. A --t-micro, 8,5 px, e'
                            un ornamento che non si legge.
     --txt-primary  8,06:1  il massimo che la banda concede.
     --icona        4,31:1  quanto basta a leggerli quando si cercano.

   L'etichetta prende il rapporto piu' alto, e non e' una preferenza: e' la
   riga che dice A CHE COSA si sta rispondendo, in una finestra dove la
   risposta non si ritira. Il rosso non se ne va dalla testa, scende sul filo
   qui sopra — §11.6 regola 2 lo vuole semantico, e semantico resta.
   Il corpo non cambia registro: il suo fondo si e' mosso di 6 L, non di 35,
   e i suoi testi restano dove stavano. */
.cnf__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
/* Identificativo, tool e glifi dei controlli sono la targa della finestra,
   non il suo contenuto: --icona li tiene un gradino sotto l'etichetta, che e'
   la gerarchia giusta, ed e' anche il token dei marcatori d'angolo di §10.5
   regola 3 — il segno di servizio parla con una voce sola. */
.cnf__id, .cnf__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
.cnf__corpo { padding: var(--s-3); overflow: auto; }
.cnf__riepilogo {
  padding-bottom: var(--s-2);
  font-size: var(--t-data);
  color: var(--txt-dim);
}
.cnf__op {
  display: grid;
  grid-template-columns: calc(var(--grid) - var(--s-3)) 1fr;
  gap: var(--s-2);
  padding-bottom: var(--s-1);
  font-family: var(--font-mono);
  font-size: var(--t-data);
}
.cnf__tipo {
  text-transform: uppercase;
  letter-spacing: 0.10em;
  font-size: var(--t-micro);
  color: var(--amber);
}
.cnf__path {
  color: var(--txt-primary);
  overflow-wrap: anywhere;
}
/* Il diff dello script (ADR-015, fetta 4) e' testo a righe: senza pre-wrap
   gli a capo collassano e «+12/-3 righe» diventa una riga sola illeggibile.
   La sandbox e' una nota, non un percorso: smorzata. (Niente accenti gravi in
   questo commento: sta dentro un template literal, e uno solo lo chiude.) */
.cnf__op[data-tipo="diff"] .cnf__path { white-space: pre-wrap; }
.cnf__op[data-tipo="sandbox"] .cnf__path { color: var(--txt-dim); }
.cnf__freccia { color: var(--txt-ghost); }

.cnf__piede {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
}
.cnf__conto {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
/* Il resto NON troncato: se ci sono operazioni non elencate, si dice qui, nel
   piede, dove non si puo' scorrere via. Nel primo scatto questa riga stava nel
   corpo ed era finita fuori vista — cioe' l'elenco risultava troncato in
   silenzio, che e' esattamente cio' che §6.2 vieta: «mai zero conferme». */
.cnf__conto[data-resto="1"] { color: var(--amber); }
.cnf__bottoni { display: flex; gap: var(--s-2); }
/* ⚠️ Il fondo dei pulsanti SCENDE, ed e' una conseguenza del corpo, non un
   ritocco d'occasione: erano --bg-raised su un corpo a --bg-panel, e adesso
   il corpo E' --bg-raised — il riempimento sarebbe sparito dentro il proprio
   fondo e sarebbe rimasta una regola morta nel foglio. Stesso gradino di 6 L,
   col segno girato: L 31 sotto il corpo a L 37. Verso il basso perche' fra 37
   e 66 non c'e' nulla, e --fill-1 e' il riempimento della cella ATTIVA
   (§10.1): un pulsante non e' uno stato, e sopra --fill-1 il rosso di
   «Approva» cadrebbe a 3,19:1. Sul fondo piu' scuro i due pulsanti guadagnano
   invece contrasto — --rust da 4,92:1 a 5,30:1, --cy-300 da 9,59:1 a
   10,32:1 — e l'ordine fra loro non cambia: approvare resta la scelta che
   bisogna andare a prendere. */
.cnf__b {
  padding: var(--s-1) var(--s-3);
  background: var(--bg-panel);
  border: var(--line-base) solid var(--cy-900);
  border-radius: var(--radius);
  font-family: var(--font-ui);
  font-size: var(--t-label);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-dim);
}
.cnf__b--rifiuta { border-color: var(--cy-700); color: var(--cy-300); }
.cnf__b--approva { border-color: var(--rust); color: var(--rust); }
/* L'anello predefinito del browser e' un colore di sistema, fuori dalla
   palette. Su questa finestra il focus indica QUALE pulsante risponde a un
   invio: va visto, e va visto nel sistema. */
.cnf__b:focus-visible,
.cnf__b:focus {
  outline: var(--line-bold) solid var(--cy-500);
  outline-offset: var(--line-bold);
}
`;

const HTML = `
<section class="cnf" data-augmented-ui="tl-clip border">
  <header class="cnf__testa">
    <span class="cnf__etichetta">Conferma richiesta</span>
    <span class="cnf__id" data-id>—</span>
    <span class="cnf__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="cnf__corpo">
    <div class="cnf__riepilogo" data-riepilogo></div>
    <div data-operazioni></div>
  </div>
  <footer class="cnf__piede">
    <span class="cnf__conto" data-conto></span>
    <span class="cnf__bottoni">
      <button class="cnf__b cnf__b--rifiuta" data-rifiuta>Rifiuta</button>
      <button class="cnf__b cnf__b--approva" data-approva>Approva</button>
    </span>
  </footer>
</section>
`;

//: Quante operazioni si elencano. Oltre, si dice quante restano: un elenco di
//: duecento righe non si legge, e fingere che si legga sarebbe peggio che
//: dichiarare il resto.
const MOSTRATE = 12;

export function crea(contenitore, { rispondi } = {}) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".cnf");
  const q = (s) => el.querySelector(s);
  let richiestaCorrente = null;

  function chiudi(approvato) {
    if (!richiestaCorrente) return;
    rispondi?.(richiestaCorrente.id, approvato);
    richiestaCorrente = null;
  }

  q("[data-rifiuta]").addEventListener("click", () => chiudi(false));
  q("[data-approva]").addEventListener("click", () => chiudi(true));

  function mostra(richiesta) {
    richiestaCorrente = richiesta;
    q("[data-id]").textContent = `${richiesta.tool} · ${richiesta.id.slice(0, 8)}`;
    q("[data-riepilogo]").textContent = richiesta.riepilogo;

    const ops = richiesta.operazioni ?? [];
    /* ⚠️ **Qui c'era un `innerHTML` con dentro i PERCORSI**, ed e' la stessa
     * classe di R96 — che era stata chiusa in `panels/files.js` e non qui.
     *
     * Un percorso arriva risolto dal core, ma contiene un NOME DI FILE, e un
     * nome di file e' dato non fidato quanto il contenuto (invariante 5). Un
     * file chiamato con del markup scriveva markup **dentro il riquadro che
     * approva le operazioni distruttive** — cioe' nella finestra che ha
     * accanto `window.jarvis.confirm`. Un nome ben scelto in una cartella
     * scaricata poteva approvare da solo la cancellazione che stava
     * aspettando l'utente.
     *
     * Trovato scrivendo ADR-007, cercando dove finisse il `dettaglio` di
     * un'operazione MCP. Adesso ogni pezzo e' un nodo col suo `textContent`.
     *
     * E il `dettaglio` si mostra: un'operazione che non ha percorsi — quelle
     * MCP non ne hanno, perche' avvengono dentro un processo di terzi —
     * lasciava la riga VUOTA, e una conferma senza niente da leggere e' una
     * conferma che insegna a premere «approva». */
    q("[data-operazioni]").replaceChildren(...ops.slice(0, MOSTRATE).map((o) => {
      const riga = document.createElement("div");
      riga.className = "cnf__op";
      riga.dataset.tipo = String(o.tipo ?? "");
      const tipo = document.createElement("span");
      tipo.className = "cnf__tipo";
      tipo.textContent = ETICHETTE[o.tipo] ?? String(o.tipo ?? "");
      riga.appendChild(tipo);

      const corpo = document.createElement("span");
      corpo.className = "cnf__path";
      if (o.sorgente || o.destinazione) {
        // I percorsi arrivano gia' risolti dal core e si mostrano cosi' come
        // sono: rielaborarli qui vorrebbe dire poterli mostrare sbagliati.
        corpo.textContent = String(o.sorgente ?? o.destinazione ?? "");
        if (o.sorgente && o.destinazione) {
          const freccia = document.createElement("span");
          freccia.className = "cnf__freccia";
          freccia.textContent = " \u2192 ";
          corpo.appendChild(freccia);
          corpo.appendChild(document.createTextNode(String(o.destinazione)));
        }
      } else {
        corpo.textContent = String(o.dettaglio ?? "");
      }
      riga.appendChild(corpo);
      return riga;
    }));

    const resto = ops.length - MOSTRATE;
    const conto = q("[data-conto]");
    conto.dataset.resto = resto > 0 ? "1" : "0";
    conto.textContent = resto > 0
      ? `${ops.length} operazioni · ${resto} non elencate qui sopra · una sola conferma`
      : `${ops.length} operazioni · una sola conferma`;

    // Il rifiuto prende il focus: se qualcuno preme invio senza leggere, non
    // accade nulla.
    q("[data-rifiuta]").focus();
  }

  return { el, mostra, chiudi: () => chiudi(false) };
}
