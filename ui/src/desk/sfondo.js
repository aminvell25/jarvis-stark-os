/* L'insegna — SPEC §25, riferimento famiglia-a/12-logo-anelli-concentrici.
 *
 * ## Che cos'e' cambiato, e perche'
 *
 * Le stesure precedenti erano SVG: cinque anelli torniti con le loro tacche,
 * ruotati da anime.js. Il difetto non stava nei valori — erano misurati sul
 * riferimento — stava nel fatto che un anello e' un OGGETTO, e un oggetto ha un
 * bordo. Un bordo che gira legge come un ingranaggio, e un ingranaggio dietro
 * una scrivania e' un ornamento che si muove.
 *
 * Il riferimento non mostra ingranaggi: mostra una NUVOLA di punti addensati su
 * corone. Non ha bordi, quindi non c'e' niente che possa leggere come
 * meccanico, e la presenza viene dalla densita' e non dalla rotazione.
 *
 * ## Le tre cose che la fanno funzionare
 *
 * ⚠️ 1. BASSA DISCREPANZA, non reticolo e non sorteggio. Le giaciture avanzano
 * di ANGOLO D'ORO (2π/φ² = 137,508°): ogni punto cade nel varco piu' largo
 * lasciato da tutti i precedenti, quindi la copertura e' uniforme come una
 * griglia ma non ha ne' righe ne' raggi allineati. E' la disposizione dei semi
 * in un girasole — nessuno sospetta un sorteggio, e nessuno vede una griglia.
 * Reticolo e sciame sembrano gli estremi di un unico asse (ordine contro caso)
 * e non lo sono: questa e' la terza distribuzione, ed e' quella giusta.
 * Il raggio esce da una van der Corput in base 2 e viene fissato al montaggio:
 * dopo, non si estrae piu' niente. Il caso non e' attenuato — non c'e'.
 *
 * ⚠️ 2. IL PROFILO MISURATO E' DIVENTATO DENSITA'. La luminanza di ogni banda
 * dice quanti punti porta, non quanto e' chiara: le bande forti sono nuvole
 * fitte, i varchi un velo. Nove ripiani — cinque bande e i quattro varchi fra
 * loro, che non sono vuoti: nella foto il metallo fra due bande ha comunque una
 * sua luce, e portarla a zero darebbe cinque anelli staccati invece di un pezzo
 * solo.
 *
 * ⚠️ 3. SOMMA ADDITIVA. Dove i punti si sovrappongono la luce si accumula: il
 * centro di una banda e' chiaro perche' ci sono piu' punti, non perche'
 * qualcuno lo abbia schiarito. In source-over mille punti tenui restano tenui e
 * la banda e' un velo piatto.
 *
 * ## Perche' un canvas e non l'SVG
 *
 * Cinquemila nodi SVG sono cinquemila elementi nel documento e cinquemila
 * riscritture di attributo per fotogramma. Non e' una questione di velocita': e'
 * che l'editor del progetto poi vede cinquemila figli dove c'e' UNA insegna.
 *
 * ## Il contratto verso il resto dell'app
 *
 * `crea(ospite)` torna un oggetto con `radice`, `aggiorna(msg)` e `stato(s)`:
 * sono le tre cose che `app.js` usa, e sono le stesse che usava lo strato di
 * presenza che questo file sostituisce. `fase()` accende dal mozzo verso il
 * bordo, `onda()` e' un EVENTO e non uno stato, e `window.__insegna` espone le
 * leve per la verifica. La classe della radice e' `.sfd` perche' e' quella che
 * `app.css` porta al livello 1 — senza, il selettore universale della scrivania
 * la manderebbe davanti a tutto.
 *
 * ## ⚠️ Che cosa questa scelta COSTA, misurato
 *
 * Va scritto qui perche' non si scopra di nuovo fra sei mesi. Misurato col
 * protocollo DevTools, dieci secondi, stessa scrivania e stesse fixture:
 *
 *   scrivania sola                       0,15 ms per fotogramma
 *   rings.js al fondo, fermo             0,14 ms
 *   rings.js al fondo, in moto           1,39 ms
 *   **questa nuvola**                    **10,36 ms**
 *
 * Cioe' il 62 % di un fotogramma a 60 Hz, contro i 15 ms che l'invariante 26
 * assegna in tutto a tre motori. E' una decisione presa sapendo il numero: la
 * nuvola non e' l'implementazione economica dell'insegna, e' quella che il
 * riferimento chiede. Se un giorno il budget diventa stretto, la leva e' il
 * conteggio dei punti — la costante 1500 qui sotto — non la forma.
 */

import { tok } from "../style/tokens.js";

export const meta = { nome: "sfondo", versione: "3" };

/* Il profilo radiale misurato sul riferimento: nove ripiani alternati fra banda
   e varco. Il terzo numero e' la luminanza, che qui e' la densita'. */
const BANDE = [
  [0.40, 0.46, 0.90],
  [0.46, 0.52, 0.12],
  [0.52, 0.60, 0.50],
  [0.60, 0.64, 0.12],
  [0.64, 0.74, 0.78],
  [0.74, 0.78, 0.10],
  [0.78, 0.86, 0.34],
  [0.86, 0.90, 0.10],
  [0.90, 0.99, 0.60],
];

/* Lobi per anello e velocita' propria. Un varco accende e spegne: a cinquemila
   punti sono cinquemila interruttori, cioe' scintillio. Un lobo e' un coseno —
   la luminosita' sale e scende lungo la corona e il disegno SCORRE. Stessa
   informazione, ed e' la differenza fra un quadrante e una nuvola. */
const LOBI = [3, 1, 4, 1, 5, 1, 3, 1, 6];
const VEL  = [0.24, -0.38, 0.62, -0.15, 1.0, -0.47, 0.31, -0.19, 0.55];

/* ⚠️ SOGLIE DI FASE, dal mozzo verso il bordo. `state.snapshot.fase` dice
   quanto del core e' costruito, e l'insegna si costruisce nello stesso ordine.
   Una banda sotto soglia non si nasconde: scende a un sedicesimo di luce. Una
   banda assente direbbe che l'insegna e' piu' piccola; una spenta dice che
   manca qualcosa da accendere, che e' cio' che una fase non raggiunta
   significa. */
const SOGLIA_FASE = [1, 2, 3, 4, 5, 6, 7, 8, 9];

/* ⚠️ I QUATTRO COLORI SONO TOKEN, non valori.
 *
 * La stesura da cui questo file viene li aveva scritti in esadecimale —
 * #1c5f6b, #3f97a6, #8fdfe9, #c9a227 — e l'invariante 18 non fa eccezioni per
 * il canvas: e' esattamente il caso per cui `style/tokens.js` esiste, e per cui
 * lo usano gia' i materiali three.js e gli sprite PixiJS.
 *
 * Misurati, i quattro letterali non corrispondevano a nessun token: 26, 52 e 68
 * di distanza RGB dal piu' vicino, e solo #8fdfe9 cadeva vicino a --cy-300
 * (17). Quindi non e' una sostituzione uno a uno — e' la stessa STRUTTURA
 * cromatica ridetta con la palette del progetto: tre gradini freddi che
 * dicono la luminanza della banda, piu' l'ambra dell'accento.
 *
 * L'ambra sta solo nell'arco misurato: §11.1 la riserva all'attenzione, e
 * spenderla altrove brucerebbe il solo colore che il sistema ha per dire
 * «guarda qui».
 *
 * ⚠️ E la luminanza che si vede NON e' quella del token: la somma e' additiva e
 * le alfe stanno fra 0,08 e 0,85, quindi cio' che arriva a schermo e' molto
 * piu' basso. Il valore da confrontare con le soglie di §25.5 e' quello
 * MISURATO sullo scatto, non quello dichiarato qui. */
const COL = ["--cy-900", "--cy-700", "--cy-300", "--amber"];
const ACC0 = 5.20, ACC1 = 5.95;   // l'arco ambra, radianti

/* ⚠️ UNA COSTANTE, non due letterali. L'ampiezza dell'insegna serve in due
   posti — il raggio del disegno e la conversione del puntatore in unita' di
   raggio — e con il numero scritto due volte il giorno che se ne cambia uno il
   dito punta a un raggio diverso da quello disegnato, senza che nulla lo dica.
   0,386 e' 0,552 x 0,7: la seconda riduzione del 30 %, e la frazione resta
   scritta perche' «0.386» da solo non direbbe da dove viene. */
const AMPIEZZA = 0.552 * 0.7;

const LUCE = 4.00;                // da dove viene la luce, radianti

export const css = `
/* ⚠️ L'insegna sta DENTRO la scrivania come primo figlio, non nel body. Nel
   body con z-index 0 non si vedeva: quel livello la metteva nello stesso strato
   di pittura dei fratelli a z-index auto, e li' vince l'ordine del DOM — la
   scialuppa opaca della scrivania viene dopo, e' a schermo intero e ha
   --bg-void come fondo, quindi le dipingeva sopra.
   Dentro la scrivania quella scialuppa e' un ANTENATO, e il fondo di un
   antenato sta sempre sotto i suoi figli. Il livello vero glielo da' app.css
   sulla classe .sfd, perche' «#scrivania > *» ne dichiara uno per tutti. */
.sfd {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  display: grid;
  place-items: center;
}
.sfd__tela {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
/* La scritta e' l'unica cosa dell'insegna che NON gira e non respira: e' il
   nome, e un nome che si muove non si legge.

   ⚠️ Lo scudo dietro la scritta e' del colore del PAVIMENTO, non di una luce:
   toglie contrasto alla nuvola che le passa dietro invece di aggiungerne. Non
   e' l'alone che l'invariante 19 vieta — quello aggiunge luce che non esiste —
   ma resta un'ombra su un elemento che non ne copre un altro, che §10.1 ammette
   solo per separare due superfici. Qui le due superfici ci sono, e sono la
   scritta e la nuvola: senza scudo il nome non si legge nei punti in cui una
   banda fitta gli passa sotto. */
.sfd__marchio {
  position: relative;
  font-family: var(--font-ui);
  font-weight: 600;
  color: var(--icona-viva);
  white-space: nowrap;
  letter-spacing: 0.3em;
  text-indent: 0.3em;
  text-shadow:
    0 0 22px var(--bg-void),
    0 0 8px var(--bg-void);
}
`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "sfd";

  const tela = document.createElement("canvas");
  tela.className = "sfd__tela";
  const x = tela.getContext("2d");

  const marchio = document.createElement("span");
  marchio.className = "sfd__marchio";
  marchio.textContent = "J.A.R.V.I.S.";
  radice.append(tela, marchio);

  const PHI = Math.PI * (3 - Math.sqrt(5));
  const fermo = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── I punti, generati una volta ─────────────────────────────────────── */
  const anel = [], a0f = [], rcf = [], rof = [], fase_ = [], dim = [];
  for (let b = 0; b < BANDE.length; b++) {
    const [r0, r1, v] = BANDE[b];
    const rm = (r0 + r1) / 2;
    /* ⚠️ 1500 e non 2200. In vetrina la nuvola era l'unica cosa che girava e
       teneva 103 fps; sulla scrivania divide il fotogramma con globo, anelli,
       quadranti, telemetria e news. 5165 punti sono circa quarantamila chiamate
       trascendenti per fotogramma piu' un velo a piena tela e ventiquattro
       passate additive: da solo sta dentro il budget, in compagnia no.
       A 1500 sono ~3500 punti, e la nuvola non perde nulla — la densita' che si
       vede e' quella DOPO la somma additiva, e le sovrapposizioni scalano col
       quadrato, non col conteggio. */
    const n = Math.max(30, Math.round(v * 1500 * rm));
    for (let k = 0; k < n; k++) {
      // Van der Corput in base 2: la banda si riempie dal centro verso i bordi
      // in modo sempre uniforme, a qualunque punto ci si fermi.
      let u = 0, den = 2;
      for (let m = k + 1; m > 0; m >>= 1, den *= 2) if (m & 1) u += 1 / den;
      const t = u * 2 - 1;
      // Profilo trasversale: fitto al centro, sfumato ai bordi. E' il bordo
      // sfumato la cosa che distingue una nuvola da un anello.
      const off = Math.sign(t) * Math.pow(Math.abs(t), 1.7) * 0.5;
      anel.push(b);
      a0f.push((k * PHI) % (Math.PI * 2));
      rcf.push(rm);
      rof.push(off * (r1 - r0));
      // La fase del respiro dipende dalla GIACITURA: punti vicini respirano
      // quasi insieme, quindi il respiro e' un'onda che percorre l'anello. Una
      // fase per punto sarebbe un tremolio, ed e' il rumore da evitare.
      fase_.push(((k * PHI) % (Math.PI * 2)) * 2 + b * 1.3);
      dim.push(1.0 + (anel.length % 7) * 0.09);
    }
  }
  const NP = anel.length;
  const px = new Float32Array(NP), py = new Float32Array(NP);
  const vx = new Float32Array(NP), vy = new Float32Array(NP);

  /* 24 secchi: 4 colori per 6 gradini di alfa. Alfa per punto sarebbero
     cinquemila cambi di stato del contesto per fotogramma. La scala e' bassa
     perche' la somma e' additiva: il valore che conta e' quello DOPO la
     sovrapposizione, non quello del singolo punto. */
  const ALFE = [0.08, 0.16, 0.28, 0.42, 0.60, 0.85];
  const stili = [], secchi = [];
  for (const c of COL) for (const a of ALFE) { stili.push(velo(c, a)); secchi.push([]); }

  /* ── Gli stati ──────────────────────────────────────────────────────────
   *
   * §25 verbatim: «gli anelli ruotano come un caricamento che in base al suo
   * stato reagisce». Lo stato non e' un cursore fra due estremi: e' una voce
   * dichiarata, con la propria fonte sul bus, perche' di un valore 0,83 non si
   * puo' dire a che cosa corrisponda.
   *
   * ⚠️ La COMPOSTEZZA e' la leva principale, non la velocita'. Una nuvola che
   * gira piu' in fretta dice «di corsa»; una nuvola che si STRINGE dice
   * «attenta», ed e' quello che serve per l'ascolto. A compostezza 1 le nuvole
   * diventano corone nette, a 0,2 si allargano fino a compenetrarsi — e resta
   * nebbia senza che nulla si muova a caso.
   *
   * ⚠️ «telemetry» NON si conta come traffico. Arriva a 2,5 Hz qualunque cosa
   * accada: e' il battito, non il lavoro, e contarlo darebbe un tasso costante,
   * cioe' un'insegna che dice sempre la stessa cosa.
   */
  const STATI = {
    spento:  { coer: 0.20, vel: 0.03, spaz: 0.25, k: 8,  c: 9.0, scia: 0.10, fonte: "voce.abilitata falso" },
    offline: { coer: 0.30, vel: 0.05, spaz: 0.30, k: 10, c: 8.5, scia: 0.14, fonte: "livello offline o core spento" },
    attesa:  { coer: 0.55, vel: 0.10, spaz: 0.70, k: 16, c: 7.5, scia: 0.28, fonte: "voce accesa, T1 non vivo" },
    ascolto: { coer: 1.00, vel: 0.18, spaz: 1.60, k: 34, c: 6.0, scia: 0.40, fonte: "voce.abilitata e voce.t1_vivo" },
    pensa:   { coer: 0.75, vel: 0.34, spaz: 2.60, k: 26, c: 6.5, scia: 0.48, fonte: "agent.advisory sul bus" },
    // Nessun topic di sintesi vocale: il core non pubblica quando parla.
    parla:   { coer: 0.62, vel: 0.26, spaz: 2.00, k: 22, c: 7.0, scia: 0.42, fonte: null },
    // Nessun topic di esecuzione tool: si vede il risultato, non l'esecuzione.
    tool:    { coer: 0.85, vel: 0.42, spaz: 3.20, k: 30, c: 6.2, scia: 0.52, fonte: null },
  };

  /* ── Il dito ─────────────────────────────────────────────────────────────
   *
   * ⚠️ L'INSEGNA NON PUO' RICEVERE I PUNTATORI. Ha pointer-events: none, ed e'
   * giusto: sta sotto tutto e intercettare i clic dei pannelli sarebbe un
   * difetto grave. Quindi non basta ascoltare su di lei — non le arriva niente.
   * Si ascolta sul DOCUMENTO, e si guarda che cosa c'e' sotto il cursore:
   * elementFromPoint torna l'elemento piu' in alto che RICEVE i puntatori, cioe'
   * esattamente la domanda «c'e' un pannello qui?».
   *
   * Perche' solo sul vuoto: il dito e' un'affordance, e un'affordance che
   * risponde mentre si sta usando un pannello promette che il fondo sia
   * interattivo quando non lo e'. Sul vuoto invece e' vero — non c'e' altro con
   * cui interagire.
   */
  const dito = { x: 9, y: 9, dentro: false };
  /* ⚠️ NON SI ANNUSANO LE CLASSI, si usa un fatto STRUTTURALE. La prima
     stesura cercava «winbox|barra|dock|cat|ic|cnf|pnl» nel className risalendo,
     e mancava proprio le finestre: WinBox marca «winbox» e «wb-body», e nessuna
     delle due ha il trattino dove la regex lo pretendeva — un pannello dentro
     una finestra risultava campo libero. Un elenco di prefissi va inoltre
     tenuto aggiornato a mano, e il giorno che qualcuno aggiunge un pannello con
     un altro prefisso il difetto torna senza che nessuno lo veda.
     Il fatto invece non cambia: l'insegna e' il PRIMO FIGLIO di #scrivania, e
     tutto il resto — barra, catalogo, dock, finestre — sono suoi fratelli
     SUCCESSIVI. Quindi basta risalire fino al figlio diretto della scrivania e
     guardare se e' lei. Niente da aggiornare, e non si puo' sbagliare.
     Chi non passa affatto per la scrivania (le icone stanno nel body) non e'
     campo libero: il vuoto e' la scrivania nuda, non «qualunque cosa non sia un
     pannello». */
  function libero(el) {
    const scr = document.getElementById("scrivania");
    if (!scr) return false;
    for (let n = el; n && n !== document.body; n = n.parentElement) {
      if (n.parentElement === scr) return n === radice;
      if (n === scr) return true;
    }
    return false;
  }
  function segui(e) {
    const sotto = document.elementFromPoint(e.clientX, e.clientY);
    if (!sotto || !libero(sotto)) { dito.dentro = false; return; }
    const r = radice.getBoundingClientRect();
    const lato = Math.min(r.width, r.height) * AMPIEZZA;
    // In unita' del disegno: il ciclo lavora in raggi, non in pixel.
    dito.x = (e.clientX - (r.left + r.width / 2)) / lato;
    dito.y = (e.clientY - (r.top + r.height / 2)) / lato;
    dito.dentro = true;
  }
  document.addEventListener("pointermove", segui, { passive: true });
  document.addEventListener("pointerleave", () => { dito.dentro = false; });

  const P = { coer: 0.55, vel: 0.10, spaz: 0.70, k: 16, c: 7.5, scia: 0.28 };
  const B = { ...P };                       // il bersaglio: P ci arriva scivolando
  let nomeStato = "attesa";
  let forzato = null;
  radice.dataset.stato = "attesa";

  /* ── La fase ─────────────────────────────────────────────────────────── */
  const acc = new Float32Array(BANDE.length).fill(1);
  const accB = new Float32Array(BANDE.length).fill(1);
  let faseOra = null;

  function applicaFase(n) {
    if (typeof n !== "number" || n === faseOra) return;
    faseOra = n;
    for (let b = 0; b < BANDE.length; b++) accB[b] = n >= SOGLIA_FASE[b] ? 1 : 0.06;
  }

  /* ── L'onda: un EVENTO, non uno stato ─────────────────────────────────
   *
   * Lo stato e' una condizione che DURA. Un agente che cambia stato e una fase
   * che avanza non durano: SUCCEDONO, una volta. Un parametro non puo' dirlo —
   * un parametro che poi torna indietro da solo mente per tutto il tempo in cui
   * sta fuori posto.
   *
   * ⚠️ L'onda e' un GUSCIO DI LUCE che parte dal mozzo e attraversa la nuvola
   * verso il bordo. La direzione dice da dove viene: dal centro, che e' dove
   * sta il core. Un lampo su tutta l'insegna sarebbe un sussulto; un guscio che
   * viaggia e' un fatto che si propaga.
   */
  let ondaT = -9;
  function onda() { ondaT = tOra; }

  const statiNodi = new Map();
  let nodiVisti = false;
  function guardaNodi(nodi) {
    if (!Array.isArray(nodi)) return;
    let cambiati = 0;
    for (const nd of nodi) {
      const id = nd?.id ?? nd?.nome;
      if (!id) continue;
      const ora = String(nd.stato ?? (nd.attivo ? "attivo" : "inerte"));
      if (statiNodi.has(id) && statiNodi.get(id) !== ora) cambiati++;
      statiNodi.set(id, ora);
    }
    // Il PRIMO elenco non produce onda: non e' un cambiamento, e' il primo
    // dato. E tre nodi che si muovono insieme fanno UN'onda sola — l'onda dice
    // «qualcosa e' cambiato nella mesh», tre sovrapposte direbbero confusione.
    if (!nodiVisti) { nodiVisti = true; return; }
    if (cambiati) onda();
  }

  /* ── Il ciclo ────────────────────────────────────────────────────────── */
  let R = 320, S = 0, dpr = 1;
  let giro = 0, spaz = 0, tOra = 0, ultimo = performance.now();
  let traf = 0, contati = 0;

  /* ⚠️ MISURA E' UN NO-OP SE NULLA E' CAMBIATO, e serve contro un anello di
     retroazione del ResizeObserver: la richiamata cambia tela.width/height e il
     corpo della scritta, cioe' due cose che possono rimettere in discussione il
     riquadro osservato. Un observer che si risveglia da solo non emette nessun
     errore in console: blocca il thread e la pagina resta nera, ed e' il difetto
     piu' difficile da vedere perche' non lascia traccia.
     Il guardiano e' una condizione, non un debounce: se le misure sono le stesse
     non c'e' niente da rifare, e allora rifarlo e' sempre sbagliato. */
  let wPrec = 0, hPrec = 0, dprPrec = 0;
  function misura(forza) {
    const w = radice.clientWidth || ospite.clientWidth || 1200;
    const h = radice.clientHeight || ospite.clientHeight || 800;
    const d = Math.min(2, window.devicePixelRatio || 1);
    if (!forza && w === wPrec && h === hPrec && d === dprPrec) return;
    wPrec = w; hPrec = h; dprPrec = d;
    dpr = Math.min(2, window.devicePixelRatio || 1);
    S = Math.min(w, h);
    tela.width = Math.round(w * dpr);
    tela.height = Math.round(h * dpr);
    /* ⚠️ 0,552 e non 0,92 — il 60 % di prima. A tutta ampiezza la nuvola
       arrivava a filo dei fianchi della scrivania e leggeva come un fondale, non
       come un'insegna: una cosa che tocca i bordi non ha piu' una forma, ha una
       cornice. Ridotta, torna a essere un oggetto POSATO dietro i pannelli, e i
       pannelli hanno intorno il vuoto che gli serve. Poi ridotta una seconda
       volta del 30 %: il fattore sta in AMPIEZZA, in testa al file. */
    R = (S * dpr) / 2 * AMPIEZZA;
    /* ⚠️ IL DISCO SI DICHIARA NEL DOM, e non e' un vezzo: e' la sola forma in
       cui una misura esterna puo' saperlo senza copiare AMPIEZZA in un secondo
       file. La regola e' quella che il catalogo ha gia' con
       `data-scorre-a-mano`: chi conosce un fatto lo scrive dove si legge,
       invece di farlo indovinare a chi misura.
       Tre numeri in pixel CSS, relativi al riquadro di `.sfd`: centro x, centro
       y, raggio. Il centro e' quello della tela — `x.translate(w/2, h/2)` piu'
       sotto — e resta scritto lo stesso, perche' il nucleo che verra' potrebbe
       non essere centrato e chi misura non deve accorgersene.
       Lo legge `scripts/occlusione-dom.js` per la frazione di disco coperta
       dai pannelli (PIANO-CORE-E-DENSITA §5). */
    radice.dataset.disco = [w / 2, h / 2, R / dpr].map((v) => v.toFixed(1)).join(",");
    /* La scritta e' larga il 56,1 % del raggio per lato — la quota misurata sul
       riferimento. Si arriva misurando invece di derivare una formula: il passo
       fra i corpi non ha un gradino da insegna (§11.6), e un valore corretto a
       occhio sarebbe un valore letterale non contestabile. */
    let fs = (R / dpr) * 0.15;
    marchio.style.fontSize = fs.toFixed(1) + "px";
    const largo = marchio.getBoundingClientRect().width;
    if (largo > 4) {
      fs *= (0.561 * 2 * (R / dpr)) / largo;
      marchio.style.fontSize = fs.toFixed(1) + "px";
    }
  }

  function passo() {
    const ora = performance.now();
    let dt = (ora - ultimo) / 1000;
    ultimo = ora;
    if (dt > 0.05) dt = 0.05;
    tOra += dt;

    // Il traffico decade da solo: e' un tasso, non un totale.
    traf += (Math.min(1, contati / 6) - traf) * Math.min(1, dt * 2);
    contati = 0;

    // I parametri SCIVOLANO verso il bersaglio. Un cambio di stato che li
    // sostituisse di colpo farebbe scattare cinquemila punti insieme: uno
    // scatto e' il vocabolario dell'onda, e non va speso per una condizione.
    const q = Math.min(1, dt * 2.4);
    for (const kk of ["coer", "vel", "spaz", "k", "c", "scia"]) P[kk] += (B[kk] - P[kk]) * q;
    for (let b = 0; b < BANDE.length; b++) acc[b] += (accB[b] - acc[b]) * Math.min(1, dt * 3);

    giro += P.vel * (1 + traf * 0.5) * dt;
    spaz += P.spaz * dt;

    /* Velo: si TOGLIE alfa. Dipingere un rettangolo di fondo su una tela
       trasparente accumula opacita' e fa comparire il quadrato attorno al pezzo.
       Il nero qui non e' un colore scelto: `destination-out` usa solo l'alfa, e
       il canale cromatico non entra nel risultato. */
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.globalCompositeOperation = "destination-out";
    x.fillStyle = "rgba(0,0,0," + (1 - P.scia).toFixed(3) + ")";
    x.fillRect(0, 0, tela.width, tela.height);
    x.globalCompositeOperation = "source-over";
    x.translate(tela.width / 2, tela.height / 2);

    for (const s of secchi) s.length = 0;
    const TAU = Math.PI * 2;
    const larg = (1 - P.coer) * 2.4 + 0.5;
    const resp = (1 - P.coer) * 0.5 + 0.1;
    const angSp = spaz % TAU;
    const dOnda = tOra - ondaT;
    const guscio = dOnda < 1.8 ? 0.34 + dOnda * 0.42 : -9;
    const forzaOnda = dOnda < 1.8 ? (1 - dOnda / 1.8) * 1.7 : 0;

    for (let i = 0; i < NP; i++) {
      const b = anel[i];
      const a = a0f[i] + giro * VEL[b];
      const rr = rcf[i] + rof[i] * larg * (1 + resp * Math.sin(spaz * 0.7 + fase_[i]));
      let bx = Math.cos(a) * rr, by = Math.sin(a) * rr;

      if (dito.dentro) {
        /* ⚠️ IL DITO SPOSTA IL BERSAGLIO, NON IL PUNTO. Spostare il punto lo
           strappa dalla molla e al rilascio rimbalza; spostare il bersaglio fa
           APRIRE la nuvola e richiudersi da sola, con il tempo della molla. E'
           la stessa scelta del catalogo: si anima la causa, non l'effetto. */
        const dx = bx - dito.x, dy = by - dito.y;
        const d = Math.hypot(dx, dy);
        if (d < 0.34 && d > 1e-4) {
          const f = ((0.34 - d) / 0.34) * 0.5;
          bx += (dx / d) * f; by += (dy / d) * f;
        }
      }

      // Molla semi-implicita: a k = 34 l'Euler esplicito a 60 Hz esplode.
      vx[i] += (P.k * (bx - px[i]) - P.c * vx[i]) * dt;
      vy[i] += (P.k * (by - py[i]) - P.c * vy[i]) * dt;
      px[i] += vx[i] * dt;
      py[i] += vy[i] * dt;

      const wx = px[i], wy = py[i];
      let ang = Math.atan2(wy, wx);
      if (ang < 0) ang += TAU;

      const lobo = 0.30 + 0.70 * Math.pow(
        0.5 + 0.5 * Math.cos(LOBI[b] * (a0f[i] - spaz * 0.35 * VEL[b])), 1.4);

      let dA = Math.abs(ang - angSp);
      if (dA > Math.PI) dA = TAU - dA;
      const lamp = Math.exp(-(dA * dA) / 0.09);

      let al = (0.34 + 0.66 * Math.pow(Math.max(0, Math.cos(ang - LUCE)), 1.4))
             * lobo * (1 + lamp * 0.9) * acc[b];
      if (forzaOnda > 0) {
        const d = Math.hypot(wx, wy) - guscio;
        al *= 1 + Math.exp(-(d * d) / 0.004) * forzaOnda;
      }
      if (al <= 0.02) continue;
      if (al > 1) al = 1;

      const v = BANDE[b][2];
      let ci = v >= 0.7 ? 2 : v >= 0.4 ? 1 : 0;
      if (ci === 2 && ang > ACC0 && ang < ACC1) ci = 3;
      let ai = (al * ALFE.length) | 0;
      if (ai >= ALFE.length) ai = ALFE.length - 1;
      secchi[ci * ALFE.length + ai].push(wx * R, wy * R, dim[i] * (1 + lamp * 0.35) * dpr);
    }

    x.globalCompositeOperation = "lighter";
    for (let s = 0; s < secchi.length; s++) {
      const q2 = secchi[s];
      if (!q2.length) continue;
      x.fillStyle = stili[s];
      for (let j = 0; j < q2.length; j += 3) {
        const d = q2[j + 2];
        x.fillRect(q2[j] - d / 2, q2[j + 1] - d / 2, d, d);
      }
    }
    x.globalCompositeOperation = "source-over";

    if (!fermo) rAF = requestAnimationFrame(passo);
  }

  /** Da NOME DI TOKEN a `rgba(...)`. Il valore viene da tokens.css, sempre. */
  function velo(nomeToken, a) {
    const n = parseInt(tok(nomeToken).slice(1), 16);
    return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }

  /* ── L'ingresso dei dati ─────────────────────────────────────────────── */
  let voce = null, livello = null, coreVivo = null;

  function aggiorna(m) {
    const topic = m?.topic;
    if (!topic || topic === "telemetry") return;
    contati++;
    const msg = m.payload ?? m;
    if (topic === "state.snapshot") {
      applicaFase(msg.fase);
      if (msg.agente?.livello) livello = msg.agente.livello;
      if (msg.voce) voce = msg.voce;
      if (typeof msg.core_vivo === "boolean") coreVivo = msg.core_vivo;
      decidi();
    }
    if (topic === "agent.mesh") {
      if (msg.livello) livello = msg.livello;
      guardaNodi(msg.nodi);
      decidi();
    }
    if (topic === "agent.advisory") { forza("pensa"); setTimeout(() => forza(null), 2600); }
    if (topic === "voice.state") { voce = msg; decidi(); }
  }

  function decidi() {
    if (forzato) return applica(forzato);
    if (voce && voce.abilitata === false) return applica("spento");
    if (livello === "offline" || coreVivo === false) return applica("offline");
    if (voce && voce.abilitata && voce.t1_vivo) return applica("ascolto");
    applica("attesa");
  }

  function applica(nome) {
    const st = STATI[nome];
    if (!st || nome === nomeStato) return;
    nomeStato = nome;
    radice.dataset.stato = nome;
    for (const kk of ["coer", "vel", "spaz", "k", "c", "scia"]) B[kk] = st[kk];
  }

  /** Impone uno stato a mano, o torna alla deduzione dal bus con null. */
  function forza(nome) {
    forzato = nome && STATI[nome] ? nome : null;
    if (forzato) applica(forzato); else decidi();
  }

  function stato(s) {
    if (!s) return;
    if (typeof s === "string") { applica(STATI[s] ? s : "attesa"); return; }
    if (s.voce) voce = s.voce;
    if (s.livello) livello = s.livello;
    decidi();
  }

  let rAF = 0;
  /* La richiamata differita di un fotogramma: cosi' non scrive nel layout mentre
     il motore lo sta ancora calcolando, che e' l'altra meta' dell'anello. */
  let inCoda = 0;
  const ro = new ResizeObserver(() => {
    if (inCoda) return;
    inCoda = requestAnimationFrame(() => { inCoda = 0; misura(); });
  });
  ro.observe(radice);
  requestAnimationFrame(() => { misura(true); passo(); });

  /* Le leve, guardabili senza aspettare che il core produca l'evento: una fase
     avanza una volta per rilascio e un nodo cambia stato quando gli pare. Non
     falsificano niente — chiamano le stesse funzioni del bus, e «statoOra» dice
     sempre quale voce della tabella si sta vedendo. */
  window.__insegna = {
    forza, onda,
    fase: (n) => applicaFase(n),
    get faseOra() { return faseOra; },
    get statoOra() { return nomeStato; },
    get punti() { return NP; },
    soglie: [...SOGLIA_FASE],
    stati: Object.keys(STATI),
  };

  return {
    radice, aggiorna, stato, forza, onda,
    fase: (n) => applicaFase(n),
    // Le corone misurate, per chi vuole verificare la geometria senza leggere
    // il file: getBoundingClientRect su una nuvola non dice niente.
    vertici: BANDE.map(([r0, r1, v]) => ({ r0, r1, densita: v })),
    ferma() {
      cancelAnimationFrame(rAF);
      ro.disconnect();
      // Gli ascolti stanno sul DOCUMENTO, quindi non se ne vanno con la radice.
      document.removeEventListener("pointermove", segui);
    },
  };
}
