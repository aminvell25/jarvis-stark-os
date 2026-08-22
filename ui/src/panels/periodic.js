/* Tavola periodica — SPEC §11.5, riferimento famiglia-a/11-tavola-periodica-scanner.
 *
 * §11.5 lo dice meglio di come lo direi io: «sembra la cosa piu' complessa del
 * riferimento, ed e' una CSS Grid con 118 celle». Nelle UI cinematografiche
 * l'effetto viene dalla densita' e dalla coerenza, non dalla complessita'
 * tecnica del singolo pezzo.
 *
 * ── I dati sono veri, e non potrebbero esserlo di piu' ─────────────────────
 * Simboli, numeri atomici e pesi atomici standard IUPAC. Fra parentesi quadre
 * il numero di massa dell'isotopo piu' stabile, per gli elementi che un peso
 * atomico non ce l'hanno. Sono costanti fisiche: §11.9 non ha bisogno di
 * eccezioni.
 *
 * ── Dove NON seguo il riferimento ──────────────────────────────────────────
 * Nel riferimento la tavola e' quasi tutta rossa. Sarebbe accento caldo su
 * gran parte della superficie colorata, contro §11.6 regola 2 — dove il caldo
 * significa allarme o valore critico e sta sotto il 10%. Una tavola periodica
 * non ha allarmi: qui il colore dice il BLOCCO (s, p, d, f), sui quattro
 * gradini di ciano che la palette gia' ha. La forma del riferimento senza il
 * suo trattamento, come per gli anelli.
 *
 * ── La collocazione si calcola ─────────────────────────────────────────────
 * Non c'e' una tabella di 118 coordinate scritte a mano: gruppo e periodo
 * escono da una regola di venti righe. Una tabella di coordinate e' 118
 * occasioni di sbagliare una cella, e nessuna di accorgersene.
 */

export const meta = { nome: "periodic", versione: "1" };

// prettier-ignore
const SIMBOLI = [
  "H","He","Li","Be","B","C","N","O","F","Ne",
  "Na","Mg","Al","Si","P","S","Cl","Ar",
  "K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn","Ga","Ge","As","Se","Br","Kr",
  "Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd","In","Sn","Sb","Te","I","Xe",
  "Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu",
  "Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg","Tl","Pb","Bi","Po","At","Rn",
  "Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm","Bk","Cf","Es","Fm","Md","No","Lr",
  "Rf","Db","Sg","Bh","Hs","Mt","Ds","Rg","Cn","Nh","Fl","Mc","Lv","Ts","Og",
];

/** Peso atomico standard IUPAC. Negativo = numero di massa dell'isotopo piu'
 * stabile, che si stampa fra parentesi quadre. */
// prettier-ignore
const PESI = [
  1.008,4.0026,6.94,9.0122,10.81,12.011,14.007,15.999,18.998,20.180,
  22.990,24.305,26.982,28.085,30.974,32.06,35.45,39.95,
  39.098,40.078,44.956,47.867,50.942,51.996,54.938,55.845,58.933,58.693,63.546,65.38,69.723,72.630,74.922,78.971,79.904,83.798,
  85.468,87.62,88.906,91.224,92.906,95.95,-97,101.07,102.91,106.42,107.87,112.41,114.82,118.71,121.76,127.60,126.90,131.29,
  132.91,137.33,138.91,140.12,140.91,144.24,-145,150.36,151.96,157.25,158.93,162.50,164.93,167.26,168.93,173.05,174.97,
  178.49,180.95,183.84,186.21,190.23,192.22,195.08,196.97,200.59,204.38,207.2,208.98,-209,-210,-222,
  -223,-226,-227,232.04,231.04,238.03,-237,-244,-243,-247,-247,-251,-252,-257,-258,-259,-266,
  -267,-268,-269,-270,-269,-278,-281,-282,-285,-286,-289,-290,-293,-294,-294,
];

/** Gruppo e periodo, calcolati. Righe 8 e 9 della griglia sono il blocco f. */
function collocazione(z) {
  if (z === 1) return { riga: 1, col: 1, blocco: "s" };
  if (z === 2) return { riga: 1, col: 18, blocco: "p" };
  if (z <= 18) {
    const riga = z <= 10 ? 2 : 3;
    const i = z - (z <= 10 ? 2 : 10); // 1..8 dentro il periodo
    return { riga, col: i <= 2 ? i : i + 10, blocco: i <= 2 ? "s" : "p" };
  }
  if (z <= 54) {
    const riga = z <= 36 ? 4 : 5;
    const col = z - (z <= 36 ? 18 : 36);
    return { riga, col, blocco: col <= 2 ? "s" : col >= 13 ? "p" : "d" };
  }
  // Periodi 6 e 7, col blocco f staccato in fondo come in ogni tavola stampata.
  const riga = z <= 86 ? 6 : 7;
  const base = z <= 86 ? 54 : 86;
  const i = z - base; // 1..32
  if (i <= 2) return { riga, col: i, blocco: "s" };
  if (i <= 17) return { riga: riga + 2, col: i, blocco: "f" }; // 8 e 9
  return { riga, col: i - 14, blocco: i - 14 >= 13 ? "p" : "d" };
}

const BLOCCO_TOKEN = { s: "--cy-300", p: "--cy-500", d: "--cy-700", f: "--cy-900" };

export const css = `
/* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
   Dei sette pannelli misurati sul riferimento, ZERO hanno un tratto di bordo
   sui quattro lati. Il fondo sale da --bg-panel a --bg-raised: e' il #1e2631
   letto identico a quattro quote sul corpo del calendario, L 37 contro il
   pavimento a L 19. Gli angoli li chiudono i due marcatori triangolari che
   app.css mette una volta sola sulla finestra (§10.5 regola 3): qui non si
   rifanno, o sarebbero diciotto copie della stessa forma. */
.pnl-per {
  --aug-tr: var(--s-3);
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
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 6);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE, non una riga di testo.
   Banda piena a --fill-1, L 66: +29 sul corpo, oltre il gradino minimo di +19
   misurato sul calendario. L'hairline che stava qui sotto se ne va, e non per
   pulizia: due superfici a ventinove punti di distanza si separano da sole, e
   quella riga sarebbe l'ultimo pezzo rimasto della cornice che §10.5 toglie.
   L'altezza non si tocca ed era gia' a norma — 8+8 di padding piu' una riga di
   --t-label fanno ~32 px, che su un pannello alto quattro celle di griglia
   (4x110 + 3x8 = 464) e' il 6,9 %, dentro la fascia 6-9 % del riferimento. */
.pnl-per__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
/* ⚠️ I colori della testa sono ritarati, perche' il fondo sotto di loro e'
   passato da L 31 a L 66 e con lui ogni rapporto WCAG. --cy-300 reggeva anche
   qui (6,21:1), ma su una banda chiara l'etichetta e' la voce principale e
   prende il massimo che la palette offre: --txt-primary, 8,06:1. */
.pnl-per__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
/* --txt-dim sulla testa nuova misura 2,73:1, contro i 4,53:1 che aveva sul
   fondo vecchio: e' sceso sotto ogni soglia e a --t-micro non si leggerebbe.
   --icona (4,31:1) e' il token nato per questo — id, versione, unita' — e
   tiene il salto di gerarchia che c'era prima: 10,3 contro 4,5 allora, 8,1
   contro 4,3 adesso. --txt-ghost qui e' vietato: 1,82:1, illeggibile. */
.pnl-per__id, .pnl-per__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
.pnl-per__ctrl { letter-spacing: 0.16em; }

.pnl-per__griglia {
  display: grid;
  grid-template-columns: repeat(18, 1fr);
  /* Sette periodi, lo stacco, e le due righe del blocco f. Senza righe
     dichiarate, il dimensionamento automatico dava allo stacco l'altezza di un
     periodo intero, e fra il settimo periodo e i lantanidi restava una fascia
     vuota grande come una riga di elementi. */
  grid-template-rows: repeat(7, 1fr) var(--s-3) repeat(2, 1fr);
  /* --s-1 e non --line-base: un peso di LINEA usato come spaziatura da'
     1px, che non e' multiplo di 4 — §11.8 GEOMETRIA. L'ha visto l'audit,
     non io. */
  gap: var(--s-1);
  padding: var(--s-3);
  min-height: 0;
}
/* La riga vuota fra il blocco d e il blocco f: e' la stessa interruzione di
   ogni tavola stampata, e senza di lei lantanidi e attinidi sembrerebbero il
   settimo e l'ottavo periodo. */
.pnl-per__stacco { grid-column: 1 / -1; grid-row: 8; }

/* Il rimando al blocco f, nella casella del gruppo 3 dei periodi 6 e 7.
   Lasciarla vuota, come faceva la prima versione, sembra un dato mancante:
   e' la convenzione di ogni tavola stampata che dice dove sono finiti quei
   quindici elementi. */
.pnl-per__rimando {
  display: grid;
  align-content: center;
  justify-items: center;
  border-left: var(--line-base) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}

.pnl-per__cella {
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 0;
  padding: var(--s-1) 0;
  min-width: 0;
  /* ⚠️ La cella scende a --bg-panel, ed e' una conseguenza diretta della
     regola 1 applicata sopra: il corpo del pannello ha appena preso
     --bg-raised, che fino a ieri era il fondo della cella. Lasciarla dov'era faceva sparire 118 riquadri dentro
     il loro stesso pannello, 1,00:1, nessun gradino. --bg-panel e' lo STESSO
     salto di prima con la polarita' invertita — 9 punti di L, 1,08:1 — e in
     piu' rimette i tre testi sul fondo su cui erano stati tarati: tokens.css
     rev 5.10 li misura contro --bg-panel a 13,39 · 4,53 · 3,03, e su
     --bg-raised avrebbero perso mezzo punto ciascuno (12,43 · 4,21 · 2,81).
     Un riempimento di stato (--fill-1..3) sarebbe stato l'errore che
     tokens.css nomina per esteso: un riempimento dice uno STATO, non copre
     118 celle a riposo. */
  background: var(--bg-panel);
  border-left: var(--line-base) solid var(--blocco);
  border-radius: var(--radius);
}
.pnl-per__z {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  line-height: 1.1;
  color: var(--txt-ghost);
}
.pnl-per__sim {
  font-family: var(--font-ui);
  font-size: var(--t-data);
  line-height: 1.2;
  letter-spacing: 0.04em;
  color: var(--txt-primary);
}
.pnl-per__peso {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  line-height: 1.1;
  color: var(--txt-dim);
}

.pnl-per__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-per__legenda { display: flex; gap: var(--s-3); }
.pnl-per__voce { display: flex; align-items: center; gap: var(--s-1); }
.pnl-per__campione {
  width: var(--s-2);
  height: var(--line-bold);
  background: var(--blocco);
}
`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-per";
  radice.dataset.augmentedUi = "tr-clip bl-clip border";
  radice.innerHTML = `
    <div class="pnl-per__testa">
      <span class="pnl-per__etichetta">Tavola periodica</span>
      <span class="pnl-per__id">PER_E05 · ver ${meta.versione}</span>
      <span class="pnl-per__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-per__griglia"></div>
    <div class="pnl-per__piede">
      <span class="pnl-per__legenda"></span>
      <span class="pnl-per__conteggio"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const griglia = radice.querySelector(".pnl-per__griglia");
  const stacco = document.createElement("div");
  stacco.className = "pnl-per__stacco";
  griglia.appendChild(stacco);

  for (const [riga, testo] of [[6, "57–71"], [7, "89–103"]]) {
    const r = document.createElement("div");
    r.className = "pnl-per__rimando";
    r.style.gridRow = String(riga);
    r.style.gridColumn = "3";
    r.textContent = testo;
    griglia.appendChild(r);
  }

  let instabili = 0;
  for (let z = 1; z <= SIMBOLI.length; z++) {
    const { riga, col, blocco } = collocazione(z);
    const peso = PESI[z - 1];
    if (peso < 0) instabili += 1;

    const cella = document.createElement("div");
    cella.className = "pnl-per__cella";
    cella.style.setProperty("--blocco", `var(${BLOCCO_TOKEN[blocco]})`);
    cella.style.gridRow = String(riga <= 7 ? riga : riga + 1); // salta lo stacco
    cella.style.gridColumn = String(col);
    for (const [classe, contenuto] of [
      ["pnl-per__z", String(z)],
      ["pnl-per__sim", SIMBOLI[z - 1]],
      ["pnl-per__peso", peso < 0 ? `[${-peso}]` : String(peso)],
    ]) {
      const s = document.createElement("span");
      s.className = classe;
      s.textContent = contenuto;
      cella.appendChild(s);
    }
    griglia.appendChild(cella);
  }

  radice.querySelector(".pnl-per__legenda").innerHTML = ["s", "p", "d", "f"]
    .map(
      (b) =>
        `<span class="pnl-per__voce"><i class="pnl-per__campione" ` +
        `style="--blocco: var(${BLOCCO_TOKEN[b]})"></i>blocco ${b}</span>`
    )
    .join("");
  radice.querySelector(".pnl-per__conteggio").textContent =
    `${SIMBOLI.length} elementi · ${instabili} senza peso atomico standard · IUPAC`;

  return { radice, aggiorna() {} };
}
