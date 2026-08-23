/* L'insegna — SPEC §25, riferimento famiglia-a/12-logo-anelli-concentrici.
 *
 * ## La fusione: un nucleo solo, due montaggi
 *
 * Fino al 23 agosto 2026 questo file disegnava una NUVOLA di punti su canvas, e
 * `anim/rings.js` disegnava cinque anelli in SVG. Erano due nuclei — due
 * implementazioni della stessa idea di §25 — e ogni modifica ne allineava una
 * sola. La nuvola aveva anche due difetti che nessun ritocco poteva togliere:
 *
 *   1. **girava sempre**, cioe' animazione ambientale, che l'invariante 25
 *      vieta. Non era un interruttore mancante: la nuvola NON AVEVA uno stato
 *      fermo, perche' la sua presenza veniva dal movimento;
 *   2. **costava 4,49 ms per fotogramma a riposo** — il 27 % di un fotogramma a
 *      60 Hz, per sempre, contro i 15 ms che l'invariante 26 assegna in tutto a
 *      tre motori.
 *
 * Adesso la geometria e' una sola — `costruisciDisco()` in `anim/rings.js` — e
 * i montaggi sono due: il pannello di §10.3, che e' un dato da leggere, e
 * questa insegna, che e' presenza. Il costo a riposo e' zero: senza una causa
 * non c'e' nessun ciclo acceso.
 *
 * ⚠️ **Che cosa si e' perso con la nuvola, dichiarato.** La bassa discrepanza
 * ad angolo d'oro, il profilo radiale misurato su nove ripiani, la somma
 * additiva e il dito che apriva la nuvola sul vuoto: erano tre idee giuste per
 * un oggetto che non esiste piu'. La misura che le motivava —
 * `famiglia-a/12` — descrive un LOGO di anelli concentrici, ed e' quello che
 * §25.1 assegna a questo componente. La stesura a punti e' in
 * `docs/acceptance/NUCLEO-TURNO-3.md`, con i suoi numeri.
 *
 * ## La mappa fra stato reale e movimento — §25.6 alla lettera
 *
 * Non e' un cursore fra due estremi ne' una tabella di stati inventata qui:
 * ogni anello ha la PROPRIA causa, e la causa e' un fatto sul bus.
 *
 *   anello 46 s   nodo t1 attivo in agent.mesh
 *   anello 74 s   voce.abilitata e voce.t1_vivo — «in ascolto»
 *   anello 120 s  nodo t2 attivo
 *   anello 233 s  un subagent attivo   (§25.6 non lo nomina: vedi CAUSE)
 *   ghiera fissa  nodo t0 attivo — un impulso, poi ferma
 *   anello esterno  --amber sopra soglia §16, poi --rust
 *
 * **Se gira, sta lavorando.** Non e' animazione ambientale: e' telemetria che
 * si legge da tre metri.
 *
 * ## Il contratto verso il resto dell'app
 *
 * `crea(ospite)` torna `radice`, `aggiorna(msg)` e `stato(s)`: le tre cose che
 * `app.js` usa, immutate dalla stesura a nuvola. `fase()` accende dal mozzo
 * verso il bordo, `onda()` e' un EVENTO e non uno stato, e `window.__insegna`
 * espone le leve per la verifica. La classe della radice e' `.sfd` perche' e'
 * quella che `app.css` porta al livello 1 — senza, il selettore universale
 * della scrivania la manderebbe davanti a tutto.
 *
 * ## ⚠️ Il diametro NON e' quello di §25.7, ed e' una deroga dichiarata
 *
 * §25.7 chiede «diametro = 64 % dell'altezza dell'area pannelli», cioe' Ø502
 * sulla finestra di misura. **Non ci entra.** Il buco che la scena `avvio`
 * lascia libero fra i quattro pannelli e' Ø344 — misurato, non stimato:
 * `scripts/occlusione-dom.js` cerca il raggio massimo attorno al centro che
 * nessun pannello tocca. A Ø502 il nucleo sarebbe coperto, che e' esattamente
 * la cosa che il centro libero era stato scelto per evitare.
 * L'ampiezza resta quella misurata dell'insegna — AMPIEZZA qui sotto, Ø326 —
 * che sta nel buco con il 90 % di riempimento e risulta coperta allo 0,0 %.
 * §25.7 NON e' emendata: emendare una sezione dentro un turno di
 * implementazione e' proprio cio' che le regole di uscita del piano vietano.
 * La deroga sta in `docs/acceptance/NUCLEO-TURNO-3.md` e aspetta una decisione.
 */

import { costruisciDisco, cssDisegno } from "../anim/rings.js";

export const meta = { nome: "sfondo", versione: "4" };

/* ⚠️ UNA COSTANTE, non due letterali. L'ampiezza dell'insegna e' il raggio del
   disegno, e va scritta in un posto solo perche' il giorno che si cambia il
   dito punterebbe a un raggio diverso da quello disegnato senza che nulla lo
   dica. 0,386 e' 0,552 x 0,7: la seconda riduzione del 30 %, e la frazione
   resta scritta perche' «0.386» da solo non direbbe da dove viene. */
const AMPIEZZA = 0.552 * 0.7;

/* ⚠️ LE CAUSE, una per anello — §25.6.
 *
 * L'indice e' quello di ANELLI in `anim/rings.js`: 0 e' il piu' esterno.
 * `chi` e' la chiave con cui si interroga lo stato composto, non un nome
 * decorativo: chi legge questa tabella sa gia' che cosa deve succedere perche'
 * quell'anello si muova.
 *
 * ⚠️ L'anello 233 s §25.6 non lo assegna: la sua riga dice «T2 attivo — anello
 * 120 s in moto, UNO PER SLOT», e gli slot oltre il primo non hanno un anello
 * nominato. Gli si da' i subagent, che sono cio' che un T2 spawna: e' la
 * lettura piu' vicina alla riga, ed e' segnata come lettura e non come regola.
 */
const CAUSE = [
  { chi: "t1",       perche: "agent.mesh: nodo t1 attivo" },
  { chi: "ascolto",  perche: "voce.abilitata e voce.t1_vivo" },
  { chi: "t2",       perche: "agent.mesh: nodo t2 attivo" },
  { chi: "subagent", perche: "agent.mesh: un subagent attivo (lettura di §25.6)" },
  { chi: "t0",       perche: "agent.mesh: nodo t0 attivo — un impulso, poi ferma" },
];

/* ⚠️ SOGLIE DI FASE, DAL MOZZO VERSO IL BORDO. `state.snapshot.fase` dice
   quanto del core e' costruito, e l'insegna si costruisce nello stesso ordine.
   L'indice e' quello di ANELLI, quindi la ghiera interna (4) e' la prima ad
   accendersi e l'anello esterno (0) l'ultimo.
   Una fase sotto soglia non NASCONDE l'anello: lo porta a un sedicesimo di
   luce. Un anello assente direbbe che l'insegna e' piu' piccola; uno spento
   dice che manca qualcosa da accendere, che e' cio' che una fase non raggiunta
   significa. Il core sta a FASE 9 (core/engine.py), quindi a regime sono tutti
   accesi e la scala si vede solo durante l'avvio. */
const SOGLIA_FASE = [9, 7, 5, 3, 1];

//: Quanto dura il viaggio del guscio, dal mozzo al bordo. Sotto il mezzo
//: secondo non si legge come un percorso, sopra il secondo e mezzo diventa
//: un'animazione che si guarda invece di un fatto che si nota.
const ONDA_S = 0.9;
//: Quanto e' spesso il guscio, in frazioni di raggio. Stretto: un guscio largo
//: accende tutto insieme, e allora e' un lampo — che e' un sussulto, non un
//: fatto che si propaga.
const ONDA_SPESSORE = 0.18;
//: La luce che una fase non raggiunta lascia accesa. Un sedicesimo.
const SPENTO = 0.0625;

export const css = cssDisegno + `
/* ⚠️ IL TRATTO DEL NUCLEO NON E' QUELLO DEL PANNELLO, e la differenza e' §25.5.
   Un pannello e' un dato che si legge, e il suo tratto sta a --cy-500 (L 181).
   Lo strato di presenza sta DIETRO il lavoro: §25.5 gli capa il tratto a
   riposo a L <= 48, e --cy-900 vale esattamente 48,5.
   ⚠️ Questa regola era gia' esistita, in presenza.js. Quel file e' stato
   cancellato e la regola se n'e' andata con lui, in silenzio: nessun test
   parlava di lei. Adesso uno la conta — tests/test_nucleo.py. */
.sfd .pnl-anelli__linea { stroke: var(--cy-900); }
.sfd .pnl-anelli__costruzione { stroke: var(--cy-900); }
/* L'accento caldo, e SOLO dove significa — §25.6 ultima riga, §11.6 regola 2.
   La nuvola portava un arco ambra sempre acceso: era la trascrizione di una
   misura sul riferimento, ma un colore che c'e' sempre non dice piu' niente.
   Qui l'ambra compare quando il livello lo giustifica, e allora si guarda. */
.sfd[data-livello="warn"] [data-anello="0"] .pnl-anelli__linea { stroke: var(--amber); }
.sfd[data-livello="critical"] [data-anello="0"] .pnl-anelli__linea { stroke: var(--rust); }
/* ⚠️ Il disco si centra DA SOLO, fuori dal flusso, e non con la griglia di
   .sfd. La griglia con place-items: center centra un figlio solo; con due —
   il disco e la scritta — ne fa due righe, e il disco finirebbe sopra il
   marchio invece che dietro. La tela della stesura precedente non aveva il
   problema perche' era inset: 0, cioe' gia' fuori dal flusso.
   Le due traslazioni sono l'una la meta' del proprio lato: e' il centro esatto
   a qualunque dimensione, senza sapere quale sia. */
.sfd__disco {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: block;
  overflow: visible;
}
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
/* La scritta e' l'unica cosa dell'insegna che NON gira: e' il nome, e un nome
   che si muove non si legge.

   ⚠️ Lo scudo dietro la scritta e' del colore del PAVIMENTO, non di una luce:
   toglie contrasto alla nuvola che le passa dietro invece di aggiungerne. Non
   e' l'alone che l'invariante 19 vieta — quello aggiunge luce che non esiste —
   ma resta un'ombra su un elemento che non ne copre un altro, che §10.1 ammette
   solo per separare due superfici. Qui le due superfici ci sono, e sono la
   scritta e gli anelli: senza scudo il nome non si legge nei punti in cui una
   tacca gli passa sotto. */
.sfd__marchio {
  position: relative;
  font-family: var(--font-ui);
  font-weight: 600;
  /* ⚠️ --cy-700 e non --icona-viva, ed e' §25.13.2 regola 4 — il tetto di
     §25.5, che e' invalicabile e non una preferenza.
     --icona-viva vale L 219 in Rec. 709. Su un elemento che lo scudo isola dal
     fondo, quel valore da solo spiegava il massimo a 255 misurato sull'insegna
     (DEROGHE-7dad2b8.md, deroga 2). --cy-700 vale L 100, e la tabella di §25.5
     lo chiama «L <= 92»: l'etichetta della soglia e' imprecisa, il token e'
     quello giusto — SEZIONE-25.md:171 lo dichiara gia'.
     Il tetto superiore conta quanto quello inferiore: sopra 5:1 di contrasto il
     marchio competerebbe col testo dei pannelli, ed e' la ragione vera per cui
     §25.11 lo vietava. Il criterio di §25.13.5 misura entrambi i lati. */
  color: var(--cy-700);
  white-space: nowrap;
  /* §25.13.2 regola 7 — «non selezionabile, non e' un bersaglio». Mancava.
     Lo strato .sfd porta gia' pointer-events: none, e sembrava bastare: non si
     puo' puntare il marchio. Ma una selezione che PARTE altrove lo attraversa
     lo stesso, e Ctrl+A lo prende comunque — la scritta finirebbe negli
     appunti di chi copiava un valore da un pannello. Non e' testo da leggere
     due volte: e' un marchio. */
  user-select: none;
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

  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "sfd__disco");
  svg.setAttribute("aria-hidden", "true");

  const marchio = document.createElement("span");
  marchio.className = "sfd__marchio";
  marchio.textContent = "J.A.R.V.I.S.";
  radice.append(svg, marchio);

  /* La geometria e' quella del pannello, non una copia: `costruisciDisco` sta
     in `anim/rings.js` ed e' l'unico posto dove i cinque anelli esistono.
     Le animazioni nascono in pausa — autoplay: false — quindi montare
     l'insegna non mette in moto niente. */
  const { animazioni, gruppi, raggi } = costruisciDisco(svg);

  /* ── Le cause ─────────────────────────────────────────────────────────── */
  const attivo = { t0: false, t1: false, t2: false, subagent: false, ascolto: false };
  const inMoto = gruppi.map(() => false);
  /* ⚠️ Quando qualcuno impone una causa a mano, i fatti del bus NON la
     sovrascrivono. Sembra ovvio e non lo era: la prima stesura lasciava che
     `decidi()` ricalcolasse `attivo.ascolto` dalla voce subito dopo, quindi
     `forza("ascolto")` durava un'istruzione e poi spariva.
     Non e' un difetto della leva, e' un difetto del nucleo: due scrittori
     sullo stesso campo, che e' la stessa forma dell'errore gia' visto sulle
     piastre del plinto con `opacity`. Un campo, un padrone — e qui il padrone
     e' chi ha parlato per ultimo, dichiarato in una variabile che si vede. */
  let forzato = null;

  function muoviAnello(i, deve) {
    if (deve === inMoto[i]) return;
    inMoto[i] = deve;
    const an = animazioni[i];
    if (an) (deve ? an.play() : an.pause());
  }

  /** Riapplica le cause agli anelli. Chiamata a ogni fatto nuovo, mai a tempo. */
  function componi() {
    for (let i = 0; i < CAUSE.length; i++) {
      const c = CAUSE[i];
      // La ghiera non ruota: la sua causa produce un impulso, non un moto.
      if (!animazioni[i]) continue;
      muoviAnello(i, Boolean(attivo[c.chi]));
    }
    radice.dataset.moto = inMoto.some(Boolean) ? "si" : "no";
  }

  /* ── La fase ──────────────────────────────────────────────────────────── */
  const luce = SOGLIA_FASE.map(() => 1);        // dove sta adesso
  const luceB = SOGLIA_FASE.map(() => 1);       // dove deve arrivare
  let faseOra = null;

  function applicaFase(n) {
    if (typeof n !== "number" || n === faseOra) return;
    faseOra = n;
    for (let i = 0; i < SOGLIA_FASE.length; i++) luceB[i] = n >= SOGLIA_FASE[i] ? 1 : SPENTO;
    svegliati();
  }

  /* ── L'onda: un EVENTO, non uno stato ──────────────────────────────────
   *
   * Lo stato e' una condizione che DURA. Un agente che cambia stato e una fase
   * che avanza non durano: SUCCEDONO, una volta. Un parametro non puo' dirlo —
   * un parametro che poi torna indietro da solo mente per tutto il tempo in cui
   * sta fuori posto.
   *
   * ⚠️ L'onda e' un GUSCIO DI LUCE che parte dal mozzo e attraversa gli anelli
   * verso il bordo. La direzione dice da dove viene: dal centro, che e' dove
   * sta il core. Un lampo su tutta l'insegna sarebbe un sussulto; un guscio che
   * viaggia e' un fatto che si propaga.
   */
  let ondaDa = -9;                              // istante dell'ultimo guscio
  let impulsoDa = -9, impulsoQuale = -1;        // il colpo secco su un anello solo

  function onda() { ondaDa = ora(); svegliati(); }
  function impulso(i) { impulsoDa = ora(); impulsoQuale = i; svegliati(); }

  const statiNodi = new Map();
  let nodiVisti = false;
  function guardaNodi(nodi) {
    if (!Array.isArray(nodi)) return;
    let cambiati = 0;
    const visto = { t0: false, t1: false, t2: false, subagent: false };
    for (const nd of nodi) {
      const id = String(nd?.id ?? nd?.nome ?? "");
      if (!id) continue;
      const stato = String(nd.stato ?? (nd.attivo ? "attivo" : "inerte"));
      if (statiNodi.has(id) && statiNodi.get(id) !== stato) cambiati++;
      statiNodi.set(id, stato);
      if (!nd.attivo) continue;
      if (id === "t0" || id === "t1" || id === "t2") visto[id] = true;
      else if (nd.tipo === "subagent" || nd.kind === "subagent") visto.subagent = true;
    }
    if (!forzato) {
      // La ghiera: T0 non «dura», succede. Il passaggio da fermo ad attivo e'
      // un impulso; restare attivo non e' un secondo impulso.
      if (visto.t0 && !attivo.t0) impulso(4);
      attivo.t0 = visto.t0;
      attivo.t1 = visto.t1;
      attivo.t2 = visto.t2;
      attivo.subagent = visto.subagent;
      componi();
    }
    // Il PRIMO elenco non produce onda: non e' un cambiamento, e' il primo
    // dato. E tre nodi che si muovono insieme fanno UN'onda sola — l'onda dice
    // «qualcosa e' cambiato nella mesh», tre sovrapposte direbbero confusione.
    if (!nodiVisti) { nodiVisti = true; return; }
    if (cambiati) onda();
  }

  /* ── Il ciclo, e il fatto che NON giri quando non c'e' niente da fare ───
   *
   * ⚠️ E' la differenza con la stesura a nuvola, e vale piu' di qualunque
   * ottimizzazione: qui il ciclo non esiste a riposo. Si sveglia quando cambia
   * una fase o arriva un'onda, porta le opacita' dove devono stare, e si
   * spegne. A scrivania inerte questo componente costa ZERO per fotogramma.
   * La rotazione degli anelli non passa di qui: la governa anime.js, ed e'
   * anche lei in pausa finche' non c'e' una causa.
   */
  const avvio = performance.now();
  const ora = () => (performance.now() - avvio) / 1000;
  let rAF = 0;
  let ultimo = performance.now();

  function svegliati() { if (!rAF) { ultimo = performance.now(); rAF = requestAnimationFrame(passo); } }

  function bagliore(i, t) {
    let v = 0;
    const e = t - ondaDa;
    if (e >= 0 && e <= ONDA_S * 1.6) {
      // Il guscio va dal mozzo (0) al bordo (1) in ONDA_S secondi.
      const d = (e / ONDA_S) - (1 - raggi[i]);
      v += 0.9 * Math.exp(-((d / ONDA_SPESSORE) ** 2));
    }
    if (i === impulsoQuale) {
      const f = t - impulsoDa;
      if (f >= 0 && f <= 0.6) v += 0.9 * Math.exp(-((f / 0.16) ** 2));
    }
    return v;
  }

  /* ⚠️ Il contatore non e' diagnostica: e' il criterio dell'invariante 25 reso
     misurabile. «Zero animazione ambientale» si verifica in un modo solo —
     contando i fotogrammi che il componente chiede QUANDO NON STA SUCCEDENDO
     NIENTE. La nuvola ne chiedeva 60 al secondo per sempre; questo si assesta e
     smette. Lo legge `scripts/occlusione-dom.js` a ogni scatto, cosi' il giorno
     che qualcuno rimette un ciclo continuo il numero lo dice da solo. */
  let fotogrammi = 0;

  function passo() {
    rAF = 0;
    fotogrammi++;
    const adesso = performance.now();
    let dt = (adesso - ultimo) / 1000;
    ultimo = adesso;
    if (dt > 0.05) dt = 0.05;
    const t = ora();

    let vivo = false;
    const q = Math.min(1, dt * 6);
    for (let i = 0; i < gruppi.length; i++) {
      luce[i] += (luceB[i] - luce[i]) * q;
      /* ⚠️ SI AGGANCIA AL BERSAGLIO, non ci si avvicina soltanto. Uno
         smorzamento esponenziale non arriva mai: misurato in finestra vera,
         mezzo secondo dopo il salto a fase 9 tre anelli stavano a 0,85 invece
         che a 1, e il ciclo continuava a chiedere fotogrammi per due secondi
         buoni dopo ogni cambio. Due difetti in uno — un valore che non e'
         quello dichiarato, e un ciclo che non finisce.
         Sotto il centesimo la differenza non si vede: la si chiude e si smette
         di girare. Il numero e' la soglia di visibilita', non una tolleranza. */
      if (Math.abs(luceB[i] - luce[i]) < 0.01) luce[i] = luceB[i];
      else vivo = true;
      const b = bagliore(i, t);
      if (b > 0.01) vivo = true;
      gruppi[i].style.opacity = Math.min(1, luce[i] + b).toFixed(3);
    }
    if (vivo) rAF = requestAnimationFrame(passo);
  }

  /* ── La misura ────────────────────────────────────────────────────────
   *
   * ⚠️ E' UN NO-OP SE NULLA E' CAMBIATO, e serve contro un anello di
   * retroazione del ResizeObserver: la richiamata cambia la dimensione del
   * disco e il corpo della scritta, cioe' due cose che possono rimettere in
   * discussione il riquadro osservato. Un observer che si risveglia da solo non
   * emette nessun errore in console: blocca il thread e la pagina resta nera,
   * ed e' il difetto piu' difficile da vedere perche' non lascia traccia.
   */
  let wPrec = 0, hPrec = 0;
  function misura(forza) {
    const w = radice.clientWidth || ospite.clientWidth || 1200;
    const h = radice.clientHeight || ospite.clientHeight || 800;
    if (!forza && w === wPrec && h === hPrec) return;
    wPrec = w; hPrec = h;
    const R = (Math.min(w, h) / 2) * AMPIEZZA;
    svg.style.width = (2 * R).toFixed(1) + "px";
    svg.style.height = (2 * R).toFixed(1) + "px";
    /* ⚠️ IL DISCO SI DICHIARA NEL DOM, e non e' un vezzo: e' la sola forma in
       cui una misura esterna puo' saperlo senza copiare AMPIEZZA in un secondo
       file. La regola e' quella che il catalogo ha gia' con
       `data-scorre-a-mano`: chi conosce un fatto lo scrive dove si legge,
       invece di farlo indovinare a chi misura.
       Tre numeri in pixel CSS, relativi al riquadro di `.sfd`: centro x, centro
       y, raggio. Lo legge `scripts/occlusione-dom.js` per la frazione di disco
       coperta dai pannelli (PIANO-CORE-E-DENSITA §5). */
    radice.dataset.disco = [w / 2, h / 2, R].map((v) => v.toFixed(1)).join(",");
    /* La scritta e' larga il 56,1 % del raggio per lato — la quota misurata sul
       riferimento. Si arriva misurando invece di derivare una formula: il passo
       fra i corpi non ha un gradino da insegna (§11.6), e un valore corretto a
       occhio sarebbe un valore letterale non contestabile. */
    let fs = R * 0.15;
    marchio.style.fontSize = fs.toFixed(1) + "px";
    const largo = marchio.getBoundingClientRect().width;
    if (largo > 4) {
      fs *= (0.561 * 2 * R) / largo;
      marchio.style.fontSize = fs.toFixed(1) + "px";
    }
  }

  /* ── L'ingresso dei dati ─────────────────────────────────────────────── */
  let voce = null, livello = null, coreVivo = null;

  function aggiorna(m) {
    const topic = m?.topic;
    // «telemetry» arriva a 2,5 Hz qualunque cosa accada: e' il battito, non il
    // lavoro. Un nucleo che reagisse al battito direbbe sempre la stessa cosa.
    if (!topic || topic === "telemetry") return;
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
    if (topic === "agent.advisory") {
      // §25.6 ultima riga: sopra soglia §16 l'anello esterno passa all'ambra.
      // Il livello lo porta il messaggio; senza, «warn» e' il minimo che un
      // advisory significhi.
      livello = msg.livello ?? "warn";
      decidi();
      onda();
    }
    if (topic === "voice.state") { voce = msg; decidi(); }
  }

  /* Che cosa il nucleo mostra, dedotto dai fatti e non da un cursore.
   * `data-stato` resta perche' e' la leva con cui la verifica guarda il nucleo
   * senza aspettare che il core produca l'evento. */
  function decidi() {
    const spento = Boolean(voce && voce.abilitata === false);
    const offline = livello === "offline" || coreVivo === false;
    if (!forzato) {
      attivo.ascolto = Boolean(!spento && !offline && voce && voce.abilitata && voce.t1_vivo);
    }
    radice.dataset.livello = offline ? "offline" : (livello ?? "nominal");
    radice.dataset.stato = spento ? "spento"
      : offline ? "offline"
      : attivo.t1 ? "t1"
      : attivo.t2 ? "t2"
      : attivo.ascolto ? "ascolto"
      : "inerte";
    componi();
  }

  /** Impone una causa a mano, per la verifica. `forza(null)` restituisce il
   *  comando ai fatti del bus. */
  function forza(chi) {
    forzato = chi && chi in attivo ? chi : null;
    for (const k of Object.keys(attivo)) attivo[k] = false;
    if (forzato) attivo[forzato] = true;
    if (forzato === "t0") impulso(4);
    decidi();
  }

  function stato(s) {
    if (!s) return;
    if (typeof s === "string") { forza(s in attivo ? s : null); return; }
    if (s.voce) voce = s.voce;
    if (s.livello) livello = s.livello;
    if (typeof s.core_vivo === "boolean") coreVivo = s.core_vivo;
    decidi();
  }

  /* La richiamata differita di un fotogramma: cosi' non scrive nel layout mentre
     il motore lo sta ancora calcolando, che e' l'altra meta' dell'anello. */
  let inCoda = 0;
  const ro = new ResizeObserver(() => {
    if (inCoda) return;
    inCoda = requestAnimationFrame(() => { inCoda = 0; misura(); });
  });
  ro.observe(radice);
  requestAnimationFrame(() => { misura(true); passo(); });
  decidi();

  /* Le leve, guardabili senza aspettare che il core produca l'evento: una fase
     avanza una volta per rilascio e un nodo cambia stato quando gli pare. Non
     falsificano niente — chiamano le stesse funzioni del bus, e «causeOra» dice
     sempre quali anelli si stanno vedendo in moto. */
  window.__insegna = {
    forza, onda, impulso,
    fase: (n) => applicaFase(n),
    get faseOra() { return faseOra; },
    get statoOra() { return radice.dataset.stato; },
    get fotogrammi() { return fotogrammi; },
    get causeOra() { return CAUSE.map((c, i) => ({ ...c, moto: inMoto[i] })); },
    soglie: [...SOGLIA_FASE],
    cause: CAUSE.map((c) => c.chi),
  };

  return {
    radice, aggiorna, stato, forza, onda,
    fase: (n) => applicaFase(n),
    // Le corone, per chi vuole verificare la geometria senza leggere il file:
    // getBoundingClientRect su un gruppo SVG ruotato non risponde il raggio.
    vertici: CAUSE.map((c, i) => ({ ...c, raggio: raggi[i], soglia: SOGLIA_FASE[i] })),
    ferma() {
      cancelAnimationFrame(rAF);
      ro.disconnect();
      for (const an of animazioni) if (an) an.pause();
    },
  };
}
