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
};

export const css = `
.cnf {
  /* Il bordo del pannello e' ciano come ogni altro pannello. Il rosso marca
     la TESTATA e il pulsante che distrugge, non il perimetro: §11.6 regola 2
     lo vuole semantico e sotto il 10% della superficie colorata, e nei
     riferimenti di famiglia-A segna intestazioni e valori critici, mai
     cornici intere. Cerchiare tutto di rosso e' decorazione con l'aria
     dell'allarme. */
  --aug-border-bg: var(--cy-900);
  --aug-tl: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.cnf__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  border-bottom: var(--line-base) solid var(--rust);
}
.cnf__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--rust);
}
.cnf__id, .cnf__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
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
.cnf__b {
  padding: var(--s-1) var(--s-3);
  background: var(--bg-raised);
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
    q("[data-operazioni]").innerHTML = ops.slice(0, MOSTRATE).map((o) => {
      const tipo = ETICHETTE[o.tipo] ?? o.tipo;
      // I percorsi arrivano gia' risolti dal core e si mostrano cosi' come
      // sono: rielaborarli qui vorrebbe dire poterli mostrare sbagliati.
      const dest = o.destinazione
        ? `<span class="cnf__freccia"> &rarr; </span>${o.destinazione}`
        : "";
      return `<div class="cnf__op"><span class="cnf__tipo">${tipo}</span>` +
             `<span class="cnf__path">${o.sorgente ?? o.destinazione ?? ""}${dest}</span></div>`;
    }).join("");

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
