/* Pannello telemetria — SPEC §10.2, §11.5, §13.
 *
 * Anatomia a cinque parti di §10.2: etichetta in caps, id/versione, controlli,
 * contenuto reale, piede tecnico. Taglio a 45° su UN vertice (regola
 * dell'asimmetria: mai zero, mai quattro), via augmented-ui.
 *
 * TRE STATI, non due. L'invariante 23 vuole dati veri o stato vuoto esplicito:
 *
 *   collegato  valori reali dal socket
 *   vuoto      NESSUNA SORGENTE COLLEGATA in --txt-ghost (§11.9)
 *   galleria   dati finti ma strutturalmente veri — l'unica eccezione di §11.9
 *
 * La sorgente arriva per ARGOMENTO. Non c'e' un ramo `if` che cambi
 * comportamento fra galleria e app: girerebbe un componente diverso da quello
 * verificato, e il ciclo §11.7 giudicherebbe la cosa sbagliata.
 */

import uPlot from "../../vendor/uPlot.esm.js";
import { tok } from "../style/tokens.js";

export const meta = { nome: "telemetry", versione: "1" };

const CAMPIONI = 120; // 48 s a 2,5 Hz
const SOGLIA_RAM = 90; // §16
const SOGLIA_TEMP = 75; // §16


export const css = `
.pnl-tel {
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
  --aug-br: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  /* Riempie chi lo ospita: dentro WinBox e' la finestra, nella galleria e' la
     cella. Una larghezza fissa lasciava mezzo pannello vuoto dentro WinBox. */
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  /* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
     Il corpo sale da --bg-panel (L 31) a --bg-raised (L 37): e' il valore
     misurato sul corpo del calendario del riferimento, #1e2631 identico a
     quattro quote, +18 L sul pavimento. Opaco e piatto — nel concept non c'e'
     un solo pannello traslucido, e sotto questo c'e' comunque il pavimento. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE, non una riga di testo con un
   filo sotto. Banda piena a --fill-1, e misurata sullo scatto della galleria:
   L 65,0 contro il corpo a L 36,9, cioe' un gradino di +28,1 — sopra il minimo
   di +19 letto sui pannelli del riferimento, e con la stessa polarita' del
   calendario (banda piu' chiara del corpo, testo chiaro sopra).
   Il border-bottom hairline se ne va: era l'ultimo tratto superstite della
   cornice che §10.5 ha smontato, e due superfici a 28 L di distanza si
   separano gia' da sole. L'altezza non si tocca e non serve toccarla — la
   banda misura 27 px su 420 di pannello, il 6,4 %, dentro il 6-9 % di §10.5. */
.pnl-tel__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  background: var(--fill-1);
}
/* ⚠️ I testi qui dentro sono RITARATI sul fondo nuovo, non ereditati.
   Erano scelti contro L 31; contro L 66 i loro rapporti WCAG crollano —
   --cy-300 da 10,5:1 a 6,21:1, --txt-dim da 4,53:1 a 2,73:1, cioe' sotto ogni
   soglia leggibile. Il caso peggiore e' --txt-ghost, che qui varrebbe 1,82:1:
   sulla testata non entra piu'. Il corpo del pannello non cambia registro,
   quindi i suoi testi restano dove sono. */
.pnl-tel__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  /* E' il nome del pannello, la prima cosa che si legge: prende il rapporto
     piu' alto disponibile sulla banda, 8,06:1. Il ciano perde qui il suo
     senso — su --fill-1 non e' piu' l'unica cosa accesa, e' solo un testo
     con 2 punti di contrasto in meno. */
  color: var(--txt-primary);
}
.pnl-tel__id, .pnl-tel__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  /* Id, versione e glifi di controllo sono servizio, non dato: --icona
     (4,31:1) li tiene leggibili e un gradino sotto l'etichetta, che e' la
     gerarchia giusta. E' anche il token dei marcatori d'angolo di §10.5
     regola 3, quindi il segno di servizio parla con una voce sola. */
  color: var(--icona);
}
.pnl-tel__ctrl { letter-spacing: 0.16em; }
.pnl-tel__corpo {
  display: grid;
  grid-template-rows: auto 1fr auto;
  padding: var(--s-3);
  /* Senza, la riga 1fr non puo' scendere sotto il proprio contenuto — in
     CSS Grid il minimo predefinito e' auto, non zero — e il pannello
     deborda della differenza. Sulla scrivania di §13 il pannello ha
     l'altezza che gli da' il workspace, non quella che vorrebbe: 54 px
     fuori, misurati, e una barra di scorrimento dove non serve. */
  min-height: 0;
}
/* La riga occupa tutta la larghezza. Prima le tre metriche stavano a
   sinistra e i due terzi a destra restavano vuoti: §11.8 CONTENUTO, "la
   densita' regge il confronto con l'immagine di riferimento?" — non
   reggeva. §11.6 regola 3: un pannello con poco da dire si rimpicciolisce,
   non si riempie di spazio. Qui il pannello aveva da dire di piu' di quanto
   mostrasse: ram_available_bytes arriva dal core a ogni messaggio e non
   veniva usato. */
.pnl-tel__metriche {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding-bottom: var(--s-2);
}
.pnl-tel__m { display: flex; align-items: baseline; gap: var(--s-1); }
.pnl-tel__nome {
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-dim);
}
.pnl-tel__val {
  font-family: var(--font-mono);
  font-size: var(--t-title);
  line-height: 1;
  color: var(--cy-500);
}
.pnl-tel__val[data-critico="1"] { color: var(--rust); }
.pnl-tel__unita {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-tel__grafico { min-height: calc(var(--grid) + var(--s-3)); }
.pnl-tel__proc {
  padding-top: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
}
.pnl-tel__riga {
  position: relative;
  display: flex;
  justify-content: space-between;
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-primary);
}
/* Le righe alternate, la ricetta di panels/tabella.js: sei punti di L, non un
   colore. Si vede che sono righe, non si vede la riga. */
.pnl-tel__riga:nth-child(odd) { background: var(--bg-panel); }
/* ⚠️ LA QUOTA E' IL DATO, disegnato. Larga quanto la CPU del processo, dietro
   il testo: --fill-2 (L 89) sta nella banda 60-120 che il riferimento tiene al
   24,7 % e noi all'8,2 %, ed e' li' che sta il divario di densita'.
   position: absolute e non un gradiente: un gradiente porterebbe due colori
   letterali dentro una dichiarazione, e l'audit di §11.8 ha ragione a bocciarli.
   La larghezza la scrive il componente in percentuale — e' un valore CALCOLATO
   da un dato, non un letterale di stile. */
.pnl-tel__quota {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: var(--fill-2);
}
/* Il processo che consuma PIU' CPU sale a --fill-3.
 *
 * tokens.css definisce --fill-3 «evidenza dentro una griglia densa», e tre
 * righe di processi sono la griglia piu' densa del pannello. Oggi le tre
 * quote hanno lo stesso colore e la piu' pesante si distingue solo per
 * lunghezza: a due processi vicini — 21 % e 19 % — sono due barre quasi
 * uguali, e QUALE sia il primo e' esattamente l'informazione per cui si
 * guarda questo elenco.
 *
 * L'attributo lo mette il componente misurando il massimo, non l'ordine in
 * cui arrivano: l'ordinamento lo fa gia' core/platform/linux.py, ma un
 * secondo lettore che dipende da quell'ordine e' un secondo posto da cui
 * rompere la stessa cosa. Qui il fatto «e' il piu' pesante» ha un proprietario
 * solo, e sta dove si disegna. */
.pnl-tel__quota[data-primo] { background: var(--fill-3); }
.pnl-tel__riga span { position: relative; }
.pnl-tel__riga span:last-child { color: var(--cy-100); }
.pnl-tel__piede {
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-tel__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-tel[data-stato="vuoto"] .pnl-tel__corpo { display: none; }
.pnl-tel[data-stato="vuoto"] .pnl-tel__vuoto { display: block; }

/* uPlot dipinge su canvas, ma crea anche DOM, e quel DOM porta la tipografia
   e i colori della LIBRERIA. Il livello 1 dell'audit li ha visti al primo
   scatto: "system-ui" su sette elementi e un "rgba(0,0,0,.07)" sulla
   selezione. §11.6 regola 1 dice che i due font sono il 40% dell'effetto —
   una libreria che ne infila un terzo dentro un pannello lo smonta.

   Non si tocca ui/vendor/: quei file si riscrivono a ogni "npm run vendor".
   Si sovrascrive qui, dove la regola e' nostra. */
.pnl-tel .uplot, .pnl-tel .uplot * { font-family: var(--font-mono); }
.pnl-tel .u-wrap, .pnl-tel .u-over, .pnl-tel .u-under { border-radius: var(--radius); }
.pnl-tel .u-axis { color: var(--txt-ghost); }
.pnl-tel .u-select { background: transparent; }
`;

const HTML = `
<section class="pnl-tel" data-stato="vuoto" data-augmented-ui="br-clip border">
  <header class="pnl-tel__testa">
    <span class="pnl-tel__etichetta">Telemetria</span>
    <span class="pnl-tel__id">A01 &middot; ver ${meta.versione}</span>
    <span class="pnl-tel__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-tel__corpo">
    <div class="pnl-tel__metriche">
      <div class="pnl-tel__m"><span class="pnl-tel__nome">cpu</span
        ><span class="pnl-tel__val" data-m="cpu">&mdash;</span
        ><span class="pnl-tel__unita">%</span></div>
      <div class="pnl-tel__m"><span class="pnl-tel__nome">ram</span
        ><span class="pnl-tel__val" data-m="ram">&mdash;</span
        ><span class="pnl-tel__unita">%</span></div>
      <div class="pnl-tel__m"><span class="pnl-tel__nome">temp</span
        ><span class="pnl-tel__val" data-m="temp">&mdash;</span
        ><span class="pnl-tel__unita">&deg;C</span></div>
      <div class="pnl-tel__m"><span class="pnl-tel__nome">libera</span
        ><span class="pnl-tel__val" data-m="libera">&mdash;</span
        ><span class="pnl-tel__unita">GiB</span></div>
    </div>
    <div class="pnl-tel__grafico"></div>
    <div class="pnl-tel__proc"></div>
  </div>
  <div class="pnl-tel__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-tel__piede"></footer>
</section>
`;

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-tel");
  const val = (m) => el.querySelector(`[data-m="${m}"]`);
  const proc = el.querySelector(".pnl-tel__proc");
  const piede = el.querySelector(".pnl-tel__piede");
  const grafico = el.querySelector(".pnl-tel__grafico");

  const xs = [], cpu = [], ram = [];

  const plot = new uPlot(
    {
      width: 1,
      height: 1,
      // Nessuna animazione e nessun cursore: §10.3 vieta il movimento senza
      // causa, e uPlot non anima per scelta dell'autore (§11.3).
      cursor: { show: false },
      legend: { show: false },
      scales: { y: { range: [0, 100] } },
      axes: [
        { show: false },
        { stroke: tok("--txt-ghost"), grid: { stroke: tok("--cy-900"), width: 1 },
          ticks: { show: false }, font: `10px ${tok("--font-mono")}`, size: 28 },
      ],
      /* ⚠️ AREE, non fili — e l'ordine e' parte del disegno.
       *
       * Una traccia di carico e' una quantita' nel tempo, e una quantita' si
       * legge per AREA prima che per linea: la stessa ragione per cui piu'
       * sotto la quota di CPU di un processo e' una barra. Con due fili su un
       * riquadro da 570x180 quel riquadro resta vuoto — misurato, il pannello
       * telemetria e' fra i piu' scuri della scrivania — e il divario di
       * §11.8 e' esattamente superficie nella banda L 60-120.
       *
       * ⚠️ La RAM va disegnata PRIMA della CPU, e non e' un dettaglio: uPlot
       * disegna le serie nell'ordine in cui sono dichiarate, e un riempimento
       * opaco copre chi lo precede. La RAM e' quasi sempre la piu' alta, quindi
       * messa dopo cancellerebbe la CPU. Messa prima, la CPU ci sta dentro e si
       * leggono tutt'e due.
       * Per questo i dati arrivano come [xs, ram, cpu] e non [xs, cpu, ram].
       *
       * I riempimenti stanno un gradino sotto il proprio tratto — --fill-1
       * sotto --cy-700, --fill-2 sotto --cy-500 — cosi' la linea resta la cosa
       * precisa e l'area la cosa che si vede da lontano. */
      series: [
        {},
        { stroke: tok("--cy-700"), fill: tok("--fill-1"), width: 1, points: { show: false } },
        { stroke: tok("--cy-500"), fill: tok("--fill-2"), width: 1, points: { show: false } },
      ],
    },
    [xs, ram, cpu],
    grafico,
  );

  function ridimensiona() {
    const r = grafico.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) plot.setSize({ width: r.width, height: r.height });
  }
  const ro = new ResizeObserver(ridimensiona);
  ro.observe(grafico);
  ridimensiona();

  function numero(v, cifre = 1) {
    return typeof v === "number" ? v.toFixed(cifre) : "—";
  }

  function aggiorna(t) {
    el.dataset.stato = "collegato";

    val("cpu").textContent = numero(t.cpu_percent);
    val("ram").textContent = numero(t.ram_percent);
    val("temp").textContent = numero(t.package_temp_c);
    val("libera").textContent =
      typeof t.ram_available_bytes === "number"
        ? (t.ram_available_bytes / 2 ** 30).toFixed(1)
        : "—";

    // L'accento caldo e' SEMANTICO, non decorativo (§11.6 regola 2): compare
    // solo oltre le soglie di §16.
    val("ram").dataset.critico = t.ram_percent > SOGLIA_RAM ? "1" : "0";
    val("temp").dataset.critico =
      typeof t.package_temp_c === "number" && t.package_temp_c > SOGLIA_TEMP ? "1" : "0";

    xs.push(xs.length ? xs[xs.length - 1] + 1 : 0);
    cpu.push(t.cpu_percent ?? null);
    ram.push(t.ram_percent ?? null);
    while (xs.length > CAMPIONI) { xs.shift(); cpu.shift(); ram.shift(); }
    plot.setData([xs, ram, cpu]);

    if (Array.isArray(t.top3) && t.top3.length) {
      /* ⚠️ `textContent`, mai `innerHTML`: il nome di un processo e' DATO NON
       * FIDATO (invariante 5). Arriva dal sistema operativo, e un eseguibile
       * puo' chiamarsi con del markup dentro — che finirebbe scritto
       * nell'interfaccia, e l'interfaccia ha `window.jarvis`.
       * Fino al 23 agosto 2026 questa riga era `innerHTML` con `${p.name}`
       * interpolato dentro. `panels/cartella.js` evitava gia' lo stesso difetto
       * sui nomi dei file, con la stessa motivazione scritta accanto: qui non
       * c'era arrivata.
       *
       * ⚠️ E LA QUOTA E' UNA SUPERFICIE, non un numero accanto a un nome.
       * `TOKENS-RIEMPIMENTO.md` dichiara da giorni che nessun componente usa i
       * riempimenti di stato e che «e' il passo dopo, ed e' tutto il valore»:
       * il divario di densita' col riferimento e' 16,5 punti di superficie
       * nella banda L 60-120, e una riga di testo non ne porta nessuno.
       * La barra dietro la riga E' il dato — larga quanto la CPU che il
       * processo usa — quindi non e' decorazione che riempie: e' il numero
       * detto due volte, una da leggere e una da vedere. */
      proc.textContent = "";
      /* Il massimo si misura, non si deduce dalla posizione. E si accende solo
       * se c'e' davvero un consumo: con tutti i processi a zero non esiste un
       * «piu' pesante», e accenderne uno direbbe una cosa falsa. */
      const massimo = Math.max(...t.top3.map((p) => p.cpu));
      let primoDato = false;
      for (const p of t.top3) {
        const riga = document.createElement("div");
        riga.className = "pnl-tel__riga";
        const quota = document.createElement("i");
        quota.className = "pnl-tel__quota";
        if (massimo > 0 && p.cpu === massimo && !primoDato) {
          quota.dataset.primo = "";           // a parimerito, uno solo
          primoDato = true;
        }
        quota.style.width = Math.max(0, Math.min(100, p.cpu)).toFixed(1) + "%";
        const nome = document.createElement("span");
        nome.textContent = p.name;
        const val = document.createElement("span");
        val.textContent = p.cpu.toFixed(0) + "%";
        riga.append(quota, nome, val);
        proc.appendChild(riga);
      }
    }

    const ora = new Date(((t.ts ?? Date.now() / 1000) * 1000)).toLocaleTimeString("it-IT");
    piede.textContent = `${xs.length}/${CAMPIONI} campioni · ${ora} · 0x${(t.ts | 0).toString(16)}`;
  }

  function stato(s) {
    if (s === "vuoto") {
      el.dataset.stato = "vuoto";
      piede.textContent = "in attesa del core";
    }
  }

  return { el, aggiorna, stato, distruggi: () => { ro.disconnect(); plot.destroy(); } };
}
