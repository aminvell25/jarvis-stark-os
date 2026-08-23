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

import { animate, stagger, utils } from "../../vendor/anime.esm.min.js";
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
const ONDA_MS = 900;
//: Quanto sta acceso ogni anello al passaggio del guscio. Corto: e' un
//: passaggio, non un'accensione.
const GUSCIO_MS = 260;
//: La luce che una fase non raggiunta lascia accesa. Un sedicesimo.
const SPENTO = 0.0625;
//: Quanto ci mette un anello a prendere velocita', e a perderla. Un anello che
//: parte gia' alla sua velocita' e' un fotogramma saltato: la partenza SI VEDE,
//: ed e' meta' di cio' che dice «adesso sta lavorando». Frenare piu' lentamente
//: che accelerare e' come si ferma una massa che gira.
const AVVIO_MS = 900;
const ARRESTO_MS = 1400;

export const css = cssDisegno + `
/* ⚠️ IL TRATTO DEL NUCLEO NON E' QUELLO DEL PANNELLO, e la differenza e' §25.5.
   Un pannello e' un dato che si legge, e il suo tratto sta a --cy-500 (L 181).
   Lo strato di presenza sta DIETRO il lavoro: §25.5 gli capa il tratto a
   riposo a L <= 48, e --cy-900 vale esattamente 48,5.
   ⚠️ Questa regola era gia' esistita, in presenza.js. Quel file e' stato
   cancellato e la regola se n'e' andata con lui, in silenzio: nessun test
   parlava di lei. Adesso uno la conta — tests/test_nucleo.py. */
/* Il corpo del disco. §25.5 riga «riempimento del nucleo»: L <= 48, e --cy-900
   vale 48,5 — il token che cade sul campo scuro misurato del riferimento
   (L 43,3). E' una superficie, quindi ha area: pesa piu' di un tratto, ed e' la
   ragione per cui §25.5 ha una riga sua dal 23 agosto 2026. */
/* ⚠️ --bg-panel (L 30,7) e non --cy-900 (L 48,5), e la ragione e' il MARCHIO.
   §25.5 ammetterebbe --cy-900: il tetto del riempimento e' L 48. Ma il nome
   vive li' sopra, e §25.13.5 gli chiede fra 3,0:1 e 5,0:1 contro il composito.
   Misurato, con la scala emendata:
     campo --cy-900   composito L 46,8   marchio 2,40:1   NON PASSA
     campo --bg-panel composito L ~30    marchio 3,4:1    passa
   E non si puo' rispondere alzando il marchio: --cy-700 e' il tetto di
   §25.13.2 regola 4, e il gradino sopra (--cy-500) darebbe 7,0:1 contro questo
   fondo — sfonda il TETTO di 5,0, cioe' un marchio che compete col testo dei
   pannelli. Fra --cy-700 e --cy-500 non c'e' nessun token: la forbice si
   raggiunge dal fondo, non dalla scritta.
   Il campo resta piu' scuro delle fasce, e non e' un ripiego: nel riferimento
   il campo interno (L 43,3) e le fasce scure (L 45,2) sono quasi pari, qui e'
   un gradino sotto — e un centro piu' scuro sotto un nome e' esattamente cio'
   che un nome chiede. */
.sfd .pnl-anelli__campo { fill: var(--bg-panel); }
.sfd .pnl-anelli__linea {
  /* §25.5 emendata il 23 agosto 2026: il tratto a riposo sale da --cy-900
     (L 48) a --cy-700 (L 100). La ragione e' misurata — le bande chiare del
     riferimento stanno a media 92-125 — e sta in
     docs/acceptance/CANCELLO-25.5.md. */
  stroke: var(--cy-700);
  /* ⚠️ LA FASCIA E' PIENA, e non e' una preferenza: e' la misura del
     riferimento. famiglia-a/12, profilo radiale sul raggio del disco:
       0,125-0,475  campo scuro   L 43,3  rgb(20, 42, 49)
       0,483-0,742  banda chiara  L 116
       0,750-0,875  banda scura   L 45,2  rgb(19, 43, 51)
       0,883-0,983  banda esterna L 91,6
     Non sono contorni: sono SUPERFICI, con il dettaglio piu' chiaro sopra. Un
     nucleo di soli tratti legge come un disegno tecnico — wireframe — e il
     riferimento non e' un disegno tecnico, e' un oggetto.
     Il contorno che ReactorRing produce e' gia' chiuso (arco esterno, raccordo,
     arco interno a ritroso, Z): riempirlo non aggiunge geometria, quindi
     l'invariante 22 non e' toccato.
     --bg-panel vale L 30,7 e rgb(19, 33, 42): e' il token piu' vicino al campo
     scuro misurato, e sta sotto il tetto di §25.5 come ci sta il tratto. La
     fascia scura e il tratto piu' chiaro sopra sono la STRUTTURA del
     riferimento; la sua ampiezza di luminanza no — vedi il documento di
     accettazione, perche' quella tocca §25.5 e non si decide qui. */
  fill: var(--cy-900);
}
.sfd .pnl-anelli__costruzione { stroke: var(--cy-700); }
/* Lo strato acceso: la stessa geometria, a --cy-700, tenuta a zero finche' una
   causa non la chiama. §25.5 lo ammette per UN anello per volta, ed e' cio' che
   sia l'accensione sia il guscio dell'onda rispettano.
   Niente riempimento: acceso vuol dire che il DETTAGLIO si illumina — il bordo
   e le tacche — non che la fascia diventa un'altra superficie. */
.sfd .pnl-anelli__acceso { opacity: 0; }
/* L'anello che lavora: --cy-500 (L 181), ammesso da §25.5 dal 23 agosto 2026 a
   UNA condizione — uno per volta. A riposo il nucleo sta gia' a L 100, quindi
   l'acceso deve staccare da li' e non dal nero: --cy-700 sopra --cy-700 non si
   vedrebbe affatto. */
.sfd .pnl-anelli__linea--acceso,
.sfd .pnl-anelli__costruzione--acceso {
  fill: none;
  stroke: var(--cy-500);
  vector-effect: non-scaling-stroke;
}
.sfd .pnl-anelli__linea--acceso { stroke-width: var(--line-base); }
.sfd .pnl-anelli__costruzione--acceso { stroke-width: var(--line-hair); }
/* L'accento caldo, e SOLO dove significa — §25.6 ultima riga, §11.6 regola 2.
   La nuvola portava un arco ambra sempre acceso: era la trascrizione di una
   misura sul riferimento, ma un colore che c'e' sempre non dice piu' niente.
   Qui l'ambra compare quando il livello lo giustifica, e allora si guarda. */
.sfd[data-livello="warn"] [data-anello="0"] .pnl-anelli__linea,
.sfd[data-livello="warn"] [data-anello="0"] .pnl-anelli__linea--acceso { stroke: var(--amber); }
.sfd[data-livello="critical"] [data-anello="0"] .pnl-anelli__linea,
.sfd[data-livello="critical"] [data-anello="0"] .pnl-anelli__linea--acceso { stroke: var(--rust); }
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
  /* ⚠️ LO SCUDO E' TARATO SUL FONDO, e il fondo e' cambiato il 23 agosto 2026.
     Con §25.5 emendata il nucleo ha un corpo pieno a --cy-900 sotto la scritta,
     dove prima c'era il pavimento. Misurato: il composito sotto il marchio e'
     passato da L 20,4 a L 65,7, e il contrasto del nome da 3,39:1 a 1,77:1 —
     sotto il 3,0 che §25.13.5 chiede, cioe' non si legge piu'.
     La risposta non e' alzare il marchio: §25.13.2 regola 4 lo fissa a
     --cy-700, e il gradino sopra (--cy-500) darebbe 5,18:1, che sfonda il
     TETTO di 5,0 — un marchio che compete col testo dei pannelli, che e' la
     ragione vera per cui §25.11 lo vietava.
     La risposta e' lo scudo, che §25.13.4 dichiara ammesso proprio per questo:
     e' il colore del PAVIMENTO, toglie contrasto a cio' che passa sotto invece
     di aggiungerne alla scritta. Tre veli invece di due, e piu' larghi: il
     fondo sotto il nome torna dov'era, e il nome resta il token che §25.13
     gli assegna. */
  text-shadow:
    0 0 34px var(--bg-void),
    0 0 18px var(--bg-void),
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
  const { animazioni, gruppi, accesi, raggi } = costruisciDisco(svg, { acceso: true, campo: true });

  /* ⚠️ Il contatore dei fotogrammi e' il criterio dell'invariante 25 reso
     misurabile: «zero animazione ambientale» si verifica contando quanti
     fotogrammi il componente chiede QUANDO NON STA SUCCEDENDO NIENTE. Lo
     alimentano le animazioni di stato, che a riposo non girano.
     Lo legge `scripts/occlusione-dom.js` a ogni scatto. */
  let fotogrammi = 0;
  const conta = () => { fotogrammi++; };

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

  /* ⚠️ UN ANELLO NON PARTE ALLA SUA VELOCITA': ci arriva.
   *
   * E' la meta' di cio' che il movimento deve dire. Un anello che passa da
   * fermo a 46 s per giro in un fotogramma non si vede partire — si vede solo
   * che a un certo punto stava gia' girando, e l'informazione «adesso questo
   * sta lavorando» la si perde proprio nell'istante in cui nasce. Con una
   * rampa, la partenza E' l'evento.
   *
   * Frena piu' lentamente di quanto accelera perche' e' cosi' che si ferma una
   * massa che gira, e perche' la fine di un lavoro e' meno urgente del suo
   * inizio.
   *
   * anime.js governa la velocita' dell'animazione di rotazione tramite la
   * propria `speed` — verificato sul bundle v4.5.0, non dedotto: e' una
   * proprieta' scrivibile, il valore di riposo e' 1. La rotazione resta
   * `autoplay: false` in `costruisciDisco`, quindi finche' nessuno chiama
   * `play()` non gira niente. */
  const rampe = gruppi.map(() => null);
  const velocita = gruppi.map(() => ({ v: 0 }));

  function muoviAnello(i, deve) {
    if (deve === inMoto[i]) return;
    inMoto[i] = deve;
    const an = animazioni[i];
    if (!an) return;
    rampe[i]?.pause();
    if (deve) { an.speed = Math.max(0.001, velocita[i].v); an.play(); }
    rampe[i] = animate(velocita[i], {
      v: deve ? 1 : 0,
      duration: deve ? AVVIO_MS : ARRESTO_MS,
      ease: deve ? "out(2)" : "inOut(2)",
      onUpdate: () => { conta(); an.speed = Math.max(0.001, velocita[i].v); },
      onComplete: () => { if (!deve) an.pause(); },
    });

    /* L'anello che lavora si ACCENDE, ed e' §25.5: «anello attivo --cy-700,
       uno solo per volta». Lo strato acceso e' una seconda copia sovrapposta,
       e la transizione e' una sola opacita' — vedi costruisciDisco. */
    animate(accesi[i], {
      opacity: deve ? 1 : 0,
      duration: deve ? AVVIO_MS : ARRESTO_MS,
      ease: "out(2)",
      onUpdate: conta,
    });
  }

  /** Riapplica le cause agli anelli. Chiamata a ogni fatto nuovo, mai a tempo. */
  function componi() {
    for (let i = 0; i < CAUSE.length; i++) {
      const c = CAUSE[i];
      // La ghiera non ruota: la sua causa produce un impulso, non un moto.
      if (!animazioni[i]) continue;
      muoviAnello(i, Boolean(attivo[c.chi]));
      gruppi[i].dataset.attivo = attivo[c.chi] ? "si" : "no";
    }
    radice.dataset.moto = inMoto.some(Boolean) ? "si" : "no";
  }

  /* ── La fase ────────────────────────────────────────────────────────────
   *
   * ⚠️ L'opacita' del gruppo `posto` e' della FASE e di nessun altro. L'onda e
   * l'accensione lavorano su altre due proprieta' di altri due nodi — vedi
   * `costruisciDisco`. Due animazioni sulla stessa opacita' si sovrascrivono a
   * vicenda senza dire niente, ed e' un difetto che questo progetto ha gia'
   * pagato due volte. */
  let faseOra = null;

  function applicaFase(n) {
    if (typeof n !== "number" || n === faseOra) return;
    const prima = faseOra;
    faseOra = n;
    for (let i = 0; i < SOGLIA_FASE.length; i++) {
      animate(gruppi[i], {
        opacity: n >= SOGLIA_FASE[i] ? 1 : SPENTO,
        duration: 420,
        // Il primo dato non e' un cambiamento: la fase iniziale si posa, non
        // si anima. Animarla farebbe leggere l'avvio come un evento.
        ease: prima === null ? "linear" : "out(3)",
        onUpdate: conta,
      });
    }
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
  /* ⚠️ Il guscio e' uno STAGGER, non un calcolo di distanza per fotogramma.
   *
   * La stesura precedente valutava una gaussiana sul raggio di ogni anello a
   * ogni fotogramma, dentro un ciclo scritto a mano. Faceva la stessa cosa e
   * costava un ciclo proprio: anime.js sa gia' ritardare N bersagli l'uno
   * rispetto all'altro, ed e' il motore unico dell'invariante 9.
   * L'ordine dei bersagli e' dal MOZZO al bordo — `accesi` e' in ordine di
   * anello, dal piu' esterno, quindi si rovescia: la direzione dice da dove
   * viene la cosa, e viene dal centro, dove sta il core.
   *
   * ⚠️ E accende UN ANELLO PER VOLTA, che e' esattamente il tetto di §25.5:
   * il guscio non e' un lampo su tutta l'insegna, e non lo e' nemmeno nel
   * numero di anelli che porta a --cy-700 insieme. */
  const dalMozzo = [...accesi].reverse();

  function onda() {
    animate(dalMozzo, {
      opacity: [0, 1, 0],
      duration: GUSCIO_MS,
      delay: stagger(ONDA_MS / dalMozzo.length),
      ease: "inOut(2)",
      onUpdate: conta,
      /* Chi e' acceso perche' sta lavorando resta acceso: il guscio passa
         SOPRA lo stato, non al posto suo. Senza questa riga un'onda spegnerebbe
         l'anello che sta girando, cioe' direbbe il falso. */
      onComplete: () => {
        for (let i = 0; i < accesi.length; i++) {
          if (inMoto[i]) accesi[i].style.opacity = "1";
        }
      },
    });
  }

  function impulso(i) {
    // Un colpo secco su un anello solo: T0 non «dura», succede.
    animate(accesi[i], {
      opacity: [0, 1, 0],
      duration: 420,
      ease: "out(4)",
      onUpdate: conta,
    });
  }

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

  /* ── Il ciclo che NON c'e' ──────────────────────────────────────────────
   *
   * ⚠️ E' la differenza con la stesura a nuvola, e vale piu' di qualunque
   * ottimizzazione: qui un ciclo proprio non esiste affatto. Ogni movimento e'
   * un'animazione di anime.js con una durata dichiarata, che parte su un fatto
   * e finisce da sola; la rotazione degli anelli e' anche lei di anime.js e
   * nasce in pausa. A scrivania inerte questo componente costa ZERO.
   *
   * La stesura precedente aveva un `requestAnimationFrame` scritto a mano che
   * valutava una gaussiana per anello a ogni fotogramma. Faceva la stessa cosa,
   * e violava l'invariante 9 nella sostanza: due motori di animazione, uno dei
   * quali scritto qui dentro. Adesso il motore e' uno solo.
   */

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
  requestAnimationFrame(() => misura(true));
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
      ro.disconnect();
      for (const an of animazioni) if (an) an.pause();
      for (const r of rampe) r?.pause();
    },
  };
}
