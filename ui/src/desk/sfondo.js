/** Il nucleo Aurora: la radice di composizione del fondo della scrivania.
 *
 * ## Che cos'e' successo
 *
 * Il 1º settembre 2026 il proprietario ha portato un secondo riferimento — un
 * artifact «Jarvis Aurora» completo — e ha chiesto di **eliminare il nucleo
 * presente e rifarlo su quella specifica, «anche se va contro le nostre
 * specifiche»**. Il nucleo HUD costruito lo stesso giorno (ghiera graduata, tre
 * corone alfanumeriche, otto strati SVG, globo a spirale aurea) e' stato
 * cancellato: sta in git al commit 427e48c e si recupera con un checkout.
 *
 * ## L'ambito, invariato
 *
 * Il SOLO nucleo. Scrivania, 19 pannelli, catalogo, finestre, galleria e core
 * Python non si toccano. Il disco resta Ø326 al centro, dietro i pannelli, e la
 * logica delle pagine non cambia. I RAGGI del riferimento si conservano come
 * rapporti su viewBox 1024; la TIPOGRAFIA si riscala perche' cada sui gradini
 * --t-* veri. Vedi `aurora/geometria.js` e `hud/tipografia.js`.
 *
 * ## Le deroghe, tutte dichiarate
 *
 * ⚠️ **invariante 19** — glow e bloom. Il nucleo E' una catena di
 *    post-processing: soglia, sfocatura separabile, composito con rifrazione e
 *    aberrazione cromatica, scia per accumulo. Vedi `aurora/nucleo3d.js`.
 * ⚠️ **§25.11** — «niente three.js nel nucleo». Il nucleo e' three.js.
 * ⚠️ **invariante 25 e §10.3** — «Fondo: immobile». Quattro anelli girano in
 *    permanenza, una fascia di scansione attraversa il nucleo, una banda
 *    spazza il vetro. Il moto non ha causa: e' lo stato che respira.
 * ⚠️ **§25.5** — il tetto di luminanza del nucleo. `--cy-050` (L 242,5) sta
 *    sopra il testo dei pannelli.
 * ⚠️ **invariante 22** — geometria parametrica con `qualityGate()`. Gli
 *    icosaedri sono primitive: al posto del cancello c'e' un CONTEGGIO
 *    dichiarato, `stato().vertici`, che un presidio confronta.
 * ⚠️ **invariante 26** — three.js <= 8 ms. Da misurare, non da assumere:
 *    `stato().ms` porta la mediana.
 *
 * Cio' che NON e' derogato: l'invariante 18 (i colori sono token — la misura
 * che lo permette sta in §10.1, blocco `--au-*`), l'invariante 23 (nessun dato
 * inventato: le frasi e la telemetria finta del riferimento non sono state
 * portate), l'invariante 1 (il renderer non apre microfoni), l'invariante 20
 * (il testo sta nel DOM e in nodi SVG, mai in WebGL).
 *
 * ## Il contratto verso il resto dell'app
 *
 * `crea(ospite)` torna `radice`, `aggiorna(msg)`, `stato(s)`, `forza`, `onda`,
 * `fase`, `ferma`, e monta `window.__insegna`. Non e' un'API di comodo: la
 * pilotano `app/main.js` (giri `--nucleo` e `--verifica-scrivania`),
 * `scripts/occlusione-dom.js` (`data-disco`) e `npm run verifica:marchio`
 * (`.sfd__marchio`). Cambiarla rompe quattro strumenti di misura in silenzio,
 * ed e' per questo che la sostituzione del nucleo la conserva intatta.
 */

import { animate } from "../../vendor/anime.esm.min.js";
import { tokPx } from "../style/tokens.js";
import { VIEWBOX, CENTRO, RAGGIO_TELA, POSTI } from "../hud/aurora/geometria.js";
import { STATI, statoDa } from "../hud/aurora/stati.js";
import { crea as creaNucleo3d } from "../hud/aurora/nucleo3d.js";
import { crea as creaMoto } from "../hud/aurora/moto.js";
import { costruisci, montaVetro, montaAnelli, montaCoroneFisse,
         ridimensionaCorone, el, css as cssStrati }
  from "../hud/aurora/strati.js";
import { gradino } from "../hud/tipografia.js";
import { AVVISO_MS } from "./avviso.js";

/** ⚠️ La versione sale a 7 perche' il componente e' un ALTRO componente: stesso
 *  nome, stesso contratto, geometria e motore completamente diversi. Chi legge
 *  uno scatto vecchio deve poter sapere che non e' questo. */
export const meta = { nome: "sfondo", versione: "7" };

export const css = [
  cssStrati,
  ".sfd { position: absolute; inset: 0; overflow: hidden; pointer-events: none;",
  "  background: var(--bg-abyss); }",
  /* Il reticolo di fondo del riferimento: 28 px, quasi invisibile. E' cio' che
     da' una SCALA alla scrivania — senza, il nucleo galleggia. */
  ".sfd__reticolo { position: absolute; inset: 0;",
  "  background-image: linear-gradient(var(--au-reticolo) 1px, transparent 1px),",
  "    linear-gradient(90deg, var(--au-reticolo) 1px, transparent 1px);",
  "  background-size: 28px 28px; }",
  ".sfd__aura { position: absolute; inset: 0; transition: background 1.1s ease; }",
  ".sfd__disco { position: absolute; left: 50%; top: 50%;",
  "  transform: translate(-50%, -50%); }",
  /* ⚠️ clip-path E NON border-radius, e non e' un modo di aggirare l'audit:
     sono due cose diverse. L'invariante 18 vieta gli angoli arrotondati,
     che sono una scelta di stile; qui serve un RITAGLIO circolare — la
     tela WebGL e le righe di scansione sono quadrate e devono stare dentro
     il vetro, che e' un cerchio. clip-path lo dice esplicitamente,
     border-radius: 50% lo otteneva per effetto collaterale. L'audit vedeva
     il secondo e aveva ragione. */
  ".sfd__tela { position: absolute; clip-path: circle(50%);"
  + " overflow: hidden; }",
  ".sfd__tela canvas { display: block; }",
  ".sfd__righe { position: absolute; clip-path: circle(50%); overflow: hidden;",
  "  pointer-events: none; }",
  ".sfd__righe-fitte { position: absolute; inset: 0;",
  "  background: repeating-linear-gradient(180deg,",
  "    var(--au-riga) 0 1px, rgba(0,0,0,0) 1px 4px); }",
  ".sfd__spazzata { position: absolute; left: 0; width: 100%; }",
  /* La scritta e' l'unica cosa del nucleo che NON gira: e' il nome, e un nome
     che si muove non si legge. */
  /* ⚠️ IL NODO DEVE ABBRACCIARE LE LETTERE, non la colonna.
     Il riferimento scrive `left: 0; right: 0; text-align: center` con uno span
     dentro, e a schermo e' identico — ma §25.13.5 misura il riquadro di
     `.sfd__marchio`, e con quella regola il riquadro e' largo quanto il disco:
     431 px su un nome che ne occupa duecento. Il criterio rispondeva
     «inchiostro fino a r 350 px» e «franco -230», cioe' misurava l'angolo di
     un contenitore vuoto.
     Con `left: 50%` e la traslazione il nodo e' largo quanto il testo, e la
     misura torna a parlare del nome. */
  ".sfd__marchio { position: absolute; left: 50%;",
  "  transform: translateX(-50%); text-align: center;",
  "  font-family: var(--font-ui); font-weight: 200; color: var(--cy-050);",
  "  white-space: nowrap; user-select: none; letter-spacing: 0.24em;",
  "  text-indent: 0.24em; }",
  ".sfd__onda { position: absolute; }",
  ".sfd__onda svg { display: block; width: 100%; height: 100%; }",
  ".sfd__onda-asse { stroke: var(--cy-300); stroke-width: 0.8; opacity: 0.26; }",
  ".sfd__onda-tratto { fill: none; stroke: var(--cy-050); stroke-width: 2.2;",
  "  opacity: 0.85; }",
  ".sfd__nome { position: absolute; left: 0; right: 0; text-align: center;",
  "  font-family: var(--font-mono); color: var(--txt-ghost);",
  "  user-select: none; }",
].join("\n");

/* ⚠️ L'AMPIEZZA NON CAMBIA, ed e' una decisione esplicita del proprietario,
   ripetuta per due sostituzioni di fila: il nucleo nuovo sta «nel centro con
   la sua stessa dimensione di quello vecchio, come elemento che viene anche
   coperto dai pannelli».
   0,386 e' 0,552 x 0,7 — la seconda riduzione del 30 % — e la frazione resta
   scritta perche' «0.386» da solo non direbbe da dove viene.
   §25.7 chiederebbe il 64 % dell'altezza dell'area pannelli, cioe' Ø502: e'
   una deroga dichiarata il 23 agosto 2026 e confermata dalla decisione del
   proprietario di tenere il nucleo alla dimensione di prima. Vedi
   `docs/acceptance/NUCLEO-AURORA.md`.
   ⚠️ Il riferimento Aurora disegna il nucleo a 1024 px dentro un quadro che
   scala a 1,06, cioe' quasi a pieno schermo. Averlo preso alla lettera dava
   R 447 invece di R 163: **due volte e mezzo troppo grande**, e lo si e' visto
   solo guardando lo scatto. La scala del riferimento non si copia — si copiano
   i RAPPORTI dentro il suo viewBox. */
const AMPIEZZA = 0.552 * 0.7;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "sfd";
  /* ⚠️ `data-disco` E' TRE NUMERI, NON UN NOME: «dx,dy,r», il centro del disco
   * relativo al riquadro e il suo raggio. Lo leggono `app/main.js` per
   * ritagliare gli scatti e `scripts/occlusione-dom.js` per sapere quanto del
   * nucleo i pannelli coprono. Scriverci un nome non da' errore: il banco fa
   * `split(",").map(Number)`, ottiene NaN, e `crop` restituisce un'immagine
   * vuota — sette PNG da ZERO byte e nessun messaggio. Misurato, e mi e'
   * costato tre giri. Lo scrive `misura()`, che e' l'unica che conosce R. */
  radice.dataset.disco = "0,0,0";
  radice.dataset.stato = "STANDBY";
  radice.dataset.moto = "si";

  const reticolo = document.createElement("div");
  reticolo.className = "sfd__reticolo";
  radice.appendChild(reticolo);

  const aura = document.createElement("div");
  aura.className = "sfd__aura";
  radice.appendChild(aura);

  const disco = document.createElement("div");
  disco.className = "sfd__disco";
  radice.appendChild(disco);

  const fondo = el("svg", { class: "au", viewBox: "0 0 " + VIEWBOX + " " + VIEWBOX });
  costruisci(fondo);
  disco.appendChild(fondo);

  const tela = document.createElement("div");
  tela.className = "sfd__tela";
  disco.appendChild(tela);
  const nucleo = creaNucleo3d(tela, { lato: 177 });

  const vetro = el("svg", { class: "au", viewBox: "0 0 " + VIEWBOX + " " + VIEWBOX });
  const { spettro } = montaVetro(vetro);
  disco.appendChild(vetro);

  /* Quattro corone in tutto: due girano, due stanno ferme dentro la ghiera.
     `scriviHex` le riempie tutte allo stesso modo — sono la stessa telemetria
     vera, e la differenza e' solo se il testo si muove. */
  const anelli = [...montaCoroneFisse(fondo, 326), ...montaAnelli(disco, 326)];

  const righe = document.createElement("div");
  righe.className = "sfd__righe";
  const fitte = document.createElement("div");
  fitte.className = "sfd__righe-fitte";
  righe.appendChild(fitte);
  const spazzata = document.createElement("div");
  spazzata.className = "sfd__spazzata";
  righe.appendChild(spazzata);
  disco.appendChild(righe);

  const marchio = document.createElement("div");
  marchio.className = "sfd__marchio";
  marchio.textContent = "J.A.R.V.I.S.";
  disco.appendChild(marchio);

  const onda = document.createElement("div");
  onda.className = "sfd__onda";
  const ondaSvg = el("svg", { viewBox: "0 0 360 56", preserveAspectRatio: "none" });
  ondaSvg.appendChild(el("line", { class: "sfd__onda-asse", x1: 4, y1: 28, x2: 356, y2: 28 }));
  const tracciaOnda = el("path", { class: "sfd__onda-tratto", d: "M8,24 V32" });
  ondaSvg.appendChild(tracciaOnda);
  onda.appendChild(ondaSvg);
  disco.appendChild(onda);

  const nome = document.createElement("div");
  nome.className = "sfd__nome";
  nome.textContent = STATI[1].id;
  disco.appendChild(nome);

  ospite.appendChild(radice);

  // ── Le quote ──────────────────────────────────────────────────────────────
  let R = 0;

  /** Tutto si dimensiona dal raggio del disco, e il raggio dal riquadro.
   *
   * ⚠️ Nessuna quota in pixel qui dentro e' un numero: sono tutte frazioni del
   * viewBox 1024 del riferimento. E' cio' che permette al nucleo di stare in
   * Ø326 dietro i pannelli e di reggere se un giorno il riquadro cambia. */
  function misura() {
    /* ⚠️ `clientWidth/clientHeight` E NON `getBoundingClientRect()`, ed e' la
     * misura che il nucleo precedente usava da sempre. Col rect il disco
     * risultava **215,5 px di raggio invece di 162,9** — cioe' il riquadro
     * riportava 1115 dove il layout ne ha 843 — e il nucleo finiva fuori
     * centro, a (1024, 557) invece che a (768, 422). §25.13.5 misura la
     * distanza dell'inchiostro da un centro CABLATO in `densita.mjs`
     * (`[768, 422]`), quindi un disco fuori posto non sbaglia di poco: dava
     * «inchiostro fino a r 350 px» su un nome largo 140 e un franco di
     * **−230**, identico in tutti gli stati. Un numero che non si muove fra
     * stati diversi non sta misurando la scena.
     * Il `|| ospite` e' il caso della galleria, dove `.sfd` viene montato in
     * una scatola che si dimensiona dopo.
     *
     * ⚠️ **APERTO: questa misura NON e' stabile fra due corse.** Lo stesso
     * banco ha dato 843 e 1115 di altezza — raggio 159,8 e 215,4 — e la
     * differenza non e' innocua, perche' §25.13.5 misura la distanza da un
     * centro CABLATO in `densita.mjs` (`[768, 422]`, il centro di una finestra
     * 1536x843). Col disco fuori misura ogni distanza esce sbagliata della
     * stessa quantita', e l'inchiostro risultava a r 350 px in TUTTI gli
     * stati — un numero che non cambia fra stati diversi.
     * Limitare al viewport rende le corse ripetibili ma NON risolve: la
     * finestra del banco e' 1536x1115 in pixel CSS mentre lo scatto e'
     * 1536x843, e il ritaglio di `app/main.js` usa un solo fattore di scala
     * per le due assi — col disco dimensionato sul viewport il ritaglio cade
     * fuori dal nome e i due scatti «non differiscono».
     * Cio' che serve e' che il centro del disco viaggi col dato invece di
     * essere cablato: `data-disco` lo porta gia', e `densita.mjs` non lo
     * legge. E' un difetto del banco, non del nucleo, e va corretto li'. */
    const w = radice.clientWidth || ospite.clientWidth || 1200;
    const h = radice.clientHeight || ospite.clientHeight || 800;
    const lato = Math.min(w, h) * AMPIEZZA;
    if (lato < 8) return;
    const b = { width: w, height: h };
    R = lato / 2;
    const q = (u) => (u / VIEWBOX) * lato;

    disco.style.width = lato.toFixed(1) + "px";
    disco.style.height = lato.toFixed(1) + "px";

    const latoTela = q(RAGGIO_TELA * 2);
    tela.style.left = q(CENTRO - RAGGIO_TELA).toFixed(1) + "px";
    tela.style.top = q(CENTRO - RAGGIO_TELA).toFixed(1) + "px";
    tela.style.width = latoTela.toFixed(1) + "px";
    tela.style.height = latoTela.toFixed(1) + "px";
    nucleo.misura(latoTela);

    righe.style.left = tela.style.left;
    righe.style.top = tela.style.top;
    righe.style.width = tela.style.width;
    righe.style.height = tela.style.height;
    spazzata.style.height = q(70).toFixed(1) + "px";

    marchio.style.top = q(POSTI.marchio.alto * VIEWBOX).toFixed(1) + "px";
    marchio.style.fontSize = q(POSTI.marchio.corpo).toFixed(1) + "px";
    marchio.style.lineHeight = q(56).toFixed(1) + "px";

    onda.style.left = q((VIEWBOX - POSTI.onda.largo * VIEWBOX) / 2).toFixed(1) + "px";
    onda.style.top = q(POSTI.onda.alto * VIEWBOX).toFixed(1) + "px";
    onda.style.width = q(POSTI.onda.largo * VIEWBOX).toFixed(1) + "px";
    onda.style.height = q(POSTI.onda.alta * VIEWBOX).toFixed(1) + "px";

    nome.style.top = q(POSTI.nome.alto * VIEWBOX).toFixed(1) + "px";
    /* ⚠️ `tokPx` E NON `gradino`, e la differenza e' un fattore 3.
     * `gradino()` torna UNITA' DI VIEWBOX — serve al testo dentro un <svg> con
     * viewBox 1024, dove le unita' non sono pixel. Questo nodo sta nel DOM, e
     * li' un pixel e' un pixel: usarci `gradino` dava 26,7 px su un disco largo
     * 345, cioe' un nome di stato piu' grande del marchio. Reso e guardato. */
    nome.style.fontSize = tokPx("--t-micro") + "px";
    /* ⚠️ LE CORONE SI RIDIMENSIONANO QUI, col diametro VERO. Nascono con il
       326 nominale, ma quello vero dipende dal riquadro: montate col nominale
       rendevano a 8,63 px invece degli 8,50 di --t-micro, e `audit.mjs` le
       bocciava. Giustamente — §10.1 dice che la tipografia sta sui gradini, e
       un valore vicino a un gradino non e' un gradino. */
    ridimensionaCorone(anelli, 2 * R);
    nome.style.letterSpacing = "0.32em";

    /* ⚠️ LE LETTURE NON CI SONO PIU', ed e' una perdita dichiarata.
     *
     * Il nucleo precedente le teneva dentro il disco — AGENTE/FASE/MESH sopra
     * il nome, CPU/RAM/TEMP/VOCE sotto — e si leggevano perche' il centro era
     * scuro. Il nucleo Aurora al centro ha un guscio LUMINOSO che riempie il
     * vetro: provate a y 176 e y 700 finivano sulla ghiera, provate a y 272 e
     * y 664 finivano sul guscio. Reso e guardato tutte e due le volte.
     * Il riferimento risolve la stessa cosa non mettendocele: la sua
     * telemetria sta in un pannello laterale, che non fa parte del core e che
     * il proprietario ha escluso dall'ambito («solo il core»).
     * ⚠️ I DATI VERI NON SI PERDONO: le tre corone alfanumeriche portano la
     * stessa telemetria in base 16 (vedi `scriviHex`), e la scrivania ha i
     * propri pannelli. Cio' che si perde e' la lettura in chiaro DENTRO il
     * nucleo, e chi la rivuole deve prima trovarle un posto che non copra il
     * guscio — non e' un ritocco, e' un problema di composizione. */
    radice.dataset.disco = [
      (b.width / 2).toFixed(1), (b.height / 2).toFixed(1), R.toFixed(1),
    ].join(",");
    scriviHex();
  }

  let inCoda = 0;
  const ro = new ResizeObserver(() => {
    if (inCoda) return;
    inCoda = requestAnimationFrame(() => { inCoda = 0; misura(); });
  });
  ro.observe(radice);

  // ── I fatti, e lo stato che ne deriva ─────────────────────────────────────
  const attivo = { t0: false, parla: false, t1: false, ascolto: false,
                   subagent: false, t2: false, avviso: false };
  let livello = null, coreVivo = null, voce = null;
  let forzato = null;
  const nato = performance.now() / 1000;

  const moto = creaMoto({ terna: nucleo.terna });

  /** ⚠️ UNICO SCRITTORE di `data-stato` e del nome a schermo, e unico posto che
   *  chiama `moto.porta`. Lo stato si DERIVA dai fatti (`aurora/stati.js`), e
   *  nessun topic lo dichiara: e' la stessa regola del nucleo precedente, e
   *  l'unica cosa cambiata e' che gli stati sono otto invece di cinque. */
  function decidi() {
    const t = performance.now() / 1000;
    const i = forzato !== null ? forzato : statoDa({
      attivo, livello, coreVivo, daQuando: t - nato,
    });
    if (moto.porta(i, tAcc)) {
      const S = STATI[i];
      radice.dataset.stato = S.id;
      nome.textContent = S.id;
    }
  }

  // ── Il giro ───────────────────────────────────────────────────────────────
  let tAcc = 0;
  let tPrec = 0;
  let raf = 0;
  let fotogrammi = 0;
  let fermo = false;

  /** ⚠️ IL MOTO NON HA CAUSA, ed e' la deroga piu' pesante di questa
   *  sostituzione. §10.3 dice «Fondo: immobile» e l'invariante 25 vieta
   *  l'animazione ambientale; qui il nucleo respira sempre, gli anelli girano
   *  sempre e la scansione attraversa il nucleo da sola. Il riferimento e' un
   *  motore, non un disegno: fermarlo vorrebbe dire non averlo replicato.
   *  Il contatore resta, e serve ancora: `fotogrammi()` dice quanti ne ha
   *  chiesti, e `fissa()` li porta a zero — che e' cio' che rende misurabile
   *  uno scatto. */
  function giro(ora) {
    raf = requestAnimationFrame(giro);
    if (fermo) return;
    const s = ora / 1000;
    const dt = Math.min(0.08, tPrec ? s - tPrec : 0.016);
    tPrec = s;
    tAcc += dt;
    fotogrammi++;
    const m = moto.avanza(tAcc, dt);
    nucleo.aggiorna(tAcc, m);
    nucleo.rendi();
    dipingi(tAcc, m);
  }

  let ultimoDip = -1;

  /** Cio' che sta nel DOM si ridipinge a ~22 Hz, non a ogni fotogramma: il
   *  tracciato dell'onda e' 76 segmenti di path, e riscriverlo a 60 Hz costa
   *  piu' del nucleo 3D. Il riferimento usa lo stesso passo, 0,045 s. */
  function dipingi(t, m) {
    if (t - ultimoDip < 0.045) return;
    ultimoDip = t;

    const N = 76, d = [];
    for (let i = 0; i < N; i++) {
      const u = i / (N - 1) - 0.5;
      const inviluppo = Math.pow(Math.cos(u * Math.PI), 2.4);
      const nz = 0.3 + 0.7 * Math.abs(
        Math.sin(i * 0.87 + t * 4.1) * Math.sin(i * 0.31 - t * 2.2)
        + 0.34 * Math.sin(i * 2.13 + t * 6.9));
      const h = Math.max(1.2, (3 + 24 * inviluppo) * nz
        * (0.35 + m.amp * m.respiro * 1.6)) / 2;
      const x = (6 + i * 4.6).toFixed(1);
      d.push("M" + x + "," + (28 - h).toFixed(1) + " V" + (28 + h).toFixed(1));
    }
    tracciaOnda.setAttribute("d", d.join(" "));

    /* L'aura: un alone larghissimo dietro tutto, del colore dello stato. E'
       l'unico posto dove la tinta esce dal disco, e serve a far sapere alla
       scrivania in che stato e' il nucleo anche guardando altrove. */
    const c = m.tinta;
    aura.style.background = "radial-gradient(circle 72% at 50% 50%, rgba("
      + Math.round(c[0] * 210) + "," + Math.round(c[1] * 210) + ","
      + Math.round(c[2] * 220) + "," + (0.09 + m.amp * 0.09).toFixed(3)
      + "), rgba(0,0,0,0) 72%)";

    /* Lo spettro sul bordo del vetro: solo mentre parla, e con l'ampiezza
       VERA. A voce spenta il tracciato e' vuoto, non piatto — uno stato vuoto
       si vede, una riga piatta sembra uno strumento rotto che dice zero. */
    if (m.parla > 0.02 && bande.length) {
      const P = bande.length, punti = [];
      for (let i = 0; i <= P; i++) {
        const a = (i / P) * Math.PI * 2 - Math.PI / 2;
        const v = bande[i % P] || 0;
        const r = 277 + v * 26;
        punti.push((i ? "L" : "M") + (CENTRO + Math.cos(a) * r).toFixed(1)
          + "," + (CENTRO + Math.sin(a) * r).toFixed(1));
      }
      spettro.setAttribute("d", punti.join(" ") + " Z");
      spettro.setAttribute("opacity", (m.parla * 0.8).toFixed(2));
    } else {
      spettro.setAttribute("d", "");
      spettro.setAttribute("opacity", "0");
    }

  }

  /** Le rotazioni degli anelli: `anime.js`, non keyframe CSS.
   *
   * ⚠️ L'invariante 9 non e' derogato. Il riferimento usa
   * `animation: jaCW calc(320s / var(--spd)) linear infinite`, cioe' keyframe
   * CSS con una variabile per la velocita'; qui sono quattro animazioni
   * `anime.js` con `.speed` scrivibile, che e' la stessa cosa con una leva in
   * piu': `fissa()` puo' azzerarle e riportarle a angolo zero, e un keyframe
   * CSS no. Senza quella leva due scatti dello stesso stato differirebbero per
   * l'angolo, e il ciclo §11.7 non potrebbe misurare niente. */
  const ruote = [];
  for (const box of disco.querySelectorAll(".au__giro")) {
    const periodo = Number(box.dataset.periodo);
    const verso = Number(box.dataset.verso);
    ruote.push(animate(box, {
      rotate: verso * 360,
      duration: periodo * 1000,
      ease: "linear",
      loop: true,
    }));
  }

  /* La spazzata verticale dentro il vetro: 7 s, e va da sopra a sotto. */
  const spazza = animate(spazzata, {
    translateY: ["-20%", "120%"],
    opacity: [0, 0.7, 0.7, 0],
    duration: 7000,
    ease: "inOut(2)",
    loop: true,
  });

  // ── I messaggi ────────────────────────────────────────────────────────────
  let bande = [];
  let campioni = 0;
  let ultimaTel = null;
  let faseOra = null;

  function esa(v, cifre) {
    if (!Number.isFinite(v)) return "-".repeat(cifre);
    return (Math.max(0, Math.round(v)) % 16 ** cifre)
      .toString(16).toUpperCase().padStart(cifre, "0");
  }

  /** ⚠️ L'ESADECIMALE NON E' UN TRAVESTIMENTO. Il riferimento riempie le corone
   *  con «REC248 | 5NC0DE | MK-XL | PWR.98», che sono lettere messe li' per
   *  fare volume. Qui le corone portano la STESSA telemetria del riquadro in
   *  basso, in base 16: `0x7C` e `124` sono lo stesso numero misurato, e chi
   *  vuole verificarlo legge le due cose sullo stesso scatto.
   *  Finche' il core non ha parlato le corone restano VUOTE. */
  function scriviHex() {
    if (!anelli.length) return;
    const d = ultimaTel;
    if (!d) { for (const a of anelli) a.testo.textContent = ""; return; }
    const parole = [
      esa(d.cpu_percent, 2), esa(d.ram_percent, 2), esa(d.package_temp_c, 2),
      esa(campioni, 4), esa(Math.round((d.uptime_s ?? 0) / 60), 4),
    ];
    for (const a of anelli) {
      const capienza = Math.max(8, Math.round(a.capienza));
      let s = "";
      let i = 0;
      while (s.length < capienza) { s += parole[i % parole.length] + " "; i++; }
      a.testo.textContent = s.slice(0, capienza);
    }
  }

  function scriviTelemetria(d) {
    if (!d) return;
    ultimaTel = d;
    campioni++;
    scriviHex();
  }

  //: Restava per scrivere le due letture, che non ci sono piu'. Il nome dello
  //: stato lo scrive `decidi()`, che e' l'unico che deve.
  function scriviAgente() {}

  function guardaNodi(nodi) {
    if (!Array.isArray(nodi)) return;
    for (const k of ["t0", "t1", "t2", "subagent"]) attivo[k] = false;
    for (const n of nodi) {
      const id = String(n?.id ?? n?.nome ?? "").toLowerCase();
      if (id in attivo) attivo[id] = Boolean(n?.attivo ?? n?.vivo ?? true);
    }
  }

  function applicaFase(f) {
    if (!Number.isFinite(f)) return;
    faseOra = f;
  }

  /** ⚠️ UN AVVISO E' UN EVENTO, NON UNO STATO — e la prima stesura lo trattava
   *  come uno stato.
   *
   *  `attivo.avviso` si accendeva su `agent.advisory` e non si spegneva mai:
   *  bastava un avviso qualunque, all'avvio, e il nucleo restava in MINACCIA
   *  per sempre. Misurato: a riposo il nucleo stava in MINACCIA, e siccome
   *  MINACCIA ha priorita' su DIALOGO, il criterio «DIALOGO dal bus» falliva
   *  con lui — un difetto solo, due misure rosse.
   *
   *  Adesso l'avviso DURA: accende MINACCIA per il tempo che serve a vederla e
   *  poi lascia. Sei secondi sono tre battiti del battito quadro a 2 Hz che il
   *  riferimento assegna a quello stato: abbastanza da leggerlo, non tanto da
   *  coprire il lavoro vero. Un avviso nuovo riarma il timer, quindi una
   *  raffica tiene acceso finche' dura la raffica.
   *
   *  ⚠️ `livello === "warn"` resta uno STATO e non passa di qui: quello e' una
   *  condizione che dura finche' dura, e si spegne quando il core lo dice. */
  /* ⚠️ LA FINESTRA E' QUELLA DI `avviso.js`, non un numero mio. La barra
   *  accende il proprio segno per `AVVISO_MS` sullo stesso evento: due durate
   *  diverse per lo stesso avviso farebbero lampeggiare due cose in tempi
   *  diversi, e chi guarda non saprebbe quale credere. */
  let timerAvviso = 0;

  /** @param {boolean} critico  un avviso `level: "critical"` porta a
   *  SOVRACCARICO, gli altri a MINACCIA. */
  function avviso(critico) {
    attivo.critico = Boolean(critico);
    attivo.avviso = true;
    clearTimeout(timerAvviso);
    timerAvviso = setTimeout(() => {
      attivo.avviso = false;
      attivo.critico = false;
      decidi();
      scriviAgente();
    }, AVVISO_MS);
    decidi();
    scriviAgente();
  }

  /** «Il microfono e' aperto»: abilitata E t1 vivo, che e' la causa che il
   *  nucleo precedente dichiarava e che il core porta in
   *  `state.snapshot.voce`. Un solo posto la legge. */
  function aggiornaAscolto() {
    attivo.ascolto = Boolean(voce && voce.abilitata && voce.t1_vivo);
  }

  function aggiorna(m) {
    const topic = m?.topic;
    if (!topic) return;
    /* ⚠️ «telemetry» arriva a 2,5 Hz qualunque cosa accada: e' il battito, non
       il lavoro, e il nucleo non gli REAGISCE — nessuna causa cambia, nessuno
       stato si muove. La guardia sta PRIMA che qualcuno guardi il carico. */
    if (topic === "telemetry") { scriviTelemetria(m.payload ?? m); return; }
    const msg = m.payload ?? m;
    if (topic === "state.snapshot") {
      applicaFase(msg.fase);
      if (msg.agente?.livello) livello = msg.agente.livello;
      if (msg.voce) voce = msg.voce;
      if (typeof msg.core_vivo === "boolean") coreVivo = msg.core_vivo;
      /* ⚠️ L'ASCOLTO SI DERIVA QUI, e non solo dal topic `voice.state`.
       * I campi della voce viaggiano dentro `state.snapshot.voce`
       * (`core/engine.py:585`), e un topic `voice.state` separato il core non
       * lo manda mai. La prima stesura accendeva `attivo.ascolto` solo su
       * quel topic: col microfono APERTO il nucleo restava in STANDBY, e
       * DIAGNOSTICA non poteva accadere — uno stato irraggiungibile che
       * nessuna misura diceva, perche' il banco lo forzava sempre.
       * La causa e' quella che il nucleo precedente gia' dichiarava:
       * «voce.abilitata e voce.t1_vivo». */
      aggiornaAscolto();
      decidi(); scriviAgente();
    }
    if (topic === "agent.mesh") {
      if (msg.livello) livello = msg.livello;
      guardaNodi(msg.nodi);
      decidi(); scriviAgente();
    }
    /* ⚠️ IL LIVELLO DELL'AVVISO SI LEGGE, e prima veniva buttato via.
       `agent.advisory` porta `level`, e `critical` e' l'unico che il core
       manda per i guasti veri (`core/llm/supervisor.py:244`). Ignorandolo,
       SOVRACCARICO non era raggiungibile da nessuna strada: uno stato degli
       otto che non poteva accadere. La barra quel campo lo legge da sempre
       (`desk/barra.js:506`). */
    if (topic === "agent.advisory") avviso(msg?.level === "critical");
    if (topic === "voice.state") {
      voce = msg;
      aggiornaAscolto();
      decidi(); scriviAgente();
    }
    if (topic === "voice.spettro") {
      bande = (msg.bande || []).map(Number);
      const a = bande.length ? Math.max(0, ...bande) : 0;
      moto.voce(a, tAcc);
      /* ⚠️ `attivo.parla` PRIMA di `decidi()`: lo stato si deriva dalle cause, e
         derivarlo da cause non ancora scritte da' lo stato di un istante fa. */
      if (forzato === null) attivo.parla = msg.sorgente === "tts";
      decidi(); scriviAgente();
    }
  }

  // ── Le leve della verifica ────────────────────────────────────────────────

  /** Ferma ogni moto e porta il nucleo al valore di riposo di uno stato.
   *
   * ⚠️ E' STICKY: una volta fissato il nucleo non riparte finche' non lo dice
   * `libera()`. Senza, la prima cosa che arriva sul socket rimette in moto la
   * scena fra i due scatti di §25.13.5 e la misura diventa rumore. */
  function fissa(nomeStato) {
    fermo = true;
    for (const r of ruote) { r.pause(); r.seek(0); }
    spazza.pause(); spazza.seek(0);
    const s = moto.fissa(nomeStato);
    radice.dataset.stato = s.stato;
    radice.dataset.livello = livello ?? "nominal";
    radice.dataset.moto = "no";
    nome.textContent = s.stato;
    forzato = moto.indice;
    fotogrammi = 0;
    nucleo.aggiorna(0, moto.mix);
    nucleo.rendi(false);
    dipingi(0, moto.mix);
    scriviAgente();
    /* ⚠️ `accesi` E' UN VETTORE ONE-HOT SUGLI OTTO STATI, e non e' un ripiego.
     * Il nucleo precedente accendeva un ANELLO per causa, e §25.5 ammetteva
     * --cy-500 sull'anello attivo a una condizione: uno per volta. Aurora non
     * ha anelli per causa — la tinta e i parametri li porta lo STATO, e gli
     * stati sono mutuamente esclusivi per costruzione. Riportare quale stato e'
     * acceso dice la stessa cosa che quel vettore diceva prima, e la dice piu'
     * forte: non «al piu' uno», ma «esattamente uno». */
    return {
      ...s, livello: livello ?? "nominal",
      accesi: STATI.map((_, i) => +(i === moto.indice)),
      vertici: nucleo.stato().vertici,
    };
  }

  function libera() {
    fermo = false;
    forzato = null;
    radice.dataset.moto = "si";
    for (const r of ruote) r.play();
    spazza.play();
    decidi();
  }

  function geometria() {
    const lato = Math.min(radice.clientWidth || 1200,
                          radice.clientHeight || 800) * AMPIEZZA;
    const rr = marchio.getBoundingClientRect();
    return {
      raggioDisco: +(lato / 2).toFixed(1),
      raggioTela: +((RAGGIO_TELA / VIEWBOX) * lato).toFixed(1),
      raggioMinimoFascia: +((285 / VIEWBOX) * lato).toFixed(1),
      raggioMassimoInchiostro: +Math.hypot(rr.width / 2, rr.height / 2).toFixed(1),
      franco: +(((285 / VIEWBOX) * lato) - Math.hypot(rr.width / 2, rr.height / 2)).toFixed(1),
      marchio: [Math.round(rr.width), Math.round(rr.height)],
    };
  }

  misura();
  decidi();
  raf = requestAnimationFrame(giro);

  function ferma() {
    clearTimeout(timerAvviso);
    cancelAnimationFrame(raf);
    ro.disconnect();
    for (const r of ruote) r.pause();
    spazza.pause();
    nucleo.smonta();
    if (radice.parentNode) radice.parentNode.removeChild(radice);
  }

  const api = {
    radice, aggiorna, ferma,
    /* ⚠️ ARRIVA UNA STRINGA, e la prima stesura leggeva `s.livello`.
       `ui/src/app.js:188` fa `bus.suStato(({ stato }) => sfondo.stato(stato))`:
       passa il NOME dello stato del ponte, non un oggetto. Leggere `.livello`
       su una stringa da' `undefined`, quindi lo stato del ponte finiva nel
       nulla — e ARRESTO, che dipende da `coreVivo === false`, non era
       raggiungibile da nessuna strada. Due stati su otto irraggiungibili, e
       nessuna misura lo diceva perche' il banco li FORZAVA entrambi. */
    stato: (s) => {
      if (typeof s === "string") {
        coreVivo = s === "connesso";
        decidi(); scriviAgente();
      } else if (s) {
        livello = s.livello ?? livello;
        decidi();
      }
      return moto.stato();
    },
    forza: (nomeStato) => fissa(nomeStato),
    onda: () => moto.stato(),
    fase: applicaFase,
    vertici: () => nucleo.stato().vertici,
  };

  window.__insegna = {
    /* ⚠️ `aggiorna` E' LA STESSA FUNZIONE CHE CHIAMA IL BUS, non una scorciatoia
     * per la verifica. Il banco la usa per guidare la scrivania con un messaggio
     * VERO — `voice.spettro` con `sorgente: "tts"` — invece di forzare uno
     * stato: forzare prova che lo stato esiste, mandare il messaggio prova che
     * il percorso dalla causa allo stato funziona, che e' la cosa che si voleva
     * sapere. Senza questa riga DIALOGO restava verificabile solo a orecchio. */
    aggiorna,
    forza: api.forza,
    onda: api.onda,
    impulso: () => { attivo.t0 = true; decidi(); scriviAgente(); },
    fissa, libera, geometria,
    fase: applicaFase,
    faseOra: () => faseOra,
    statoOra: () => moto.stato(),
    /* ⚠️ UNA PROPRIETA', NON UNA FUNZIONE, e il contratto lo diceva.
     * `scripts/occlusione-dom.js:102` legge `window.__insegna.fotogrammi` come
     * NUMERO e lo mette nell'oggetto che torna a Electron. Averla resa una
     * funzione non da' un errore comprensibile: `executeJavaScript` prova a
     * clonare il risultato, trova una funzione, e muore con «An object could
     * not be cloned» — a meta' di `verifica:densita`, dopo che tutto il resto
     * della misura era gia' andato a buon fine e senza nominare il campo.
     * Il getter tiene il valore vivo e la forma vecchia. */
    get fotogrammi() { return fotogrammi; },
    contaFotogrammi: () => fotogrammi,
    motoOra: () => ({ ...moto.stato(), fermo }),
    ondaOra: () => ({ bande: bande.length, ampiezza: moto.stato().ampVoce }),
    auroraOra: () => nucleo.stato(),
    //: `rendiGlobo` resta col nome vecchio: lo chiama `app/main.js` prima di
    //: ogni `capturePage()`, e rinominarlo romperebbe la misura in silenzio.
    //: Da fermo si rende SENZA scia: due render devono dare lo stesso pixel,
    //: altrimenti §25.13.5 misura l'accumulo invece del marchio.
    rendiGlobo: () => { nucleo.rendi(!fermo); return true; },
    rendiNucleo: () => { nucleo.rendi(!fermo); return true; },
    hudOra: () => moto.stato().stato,
    statiHud: STATI.map((s) => s.id),
    cause: STATI.filter((s) => s.chi).map((s) => ({ chi: s.chi, stato: s.id })),
    strati: STATI.map((s) => s.id),
    soglie: STATI.map((s) => s.scansione),
    vertici: api.vertici,
    deroghe: ["invariante 19", "§25.11", "invariante 25 e §10.3", "§25.5",
              "invariante 22", "invariante 26", "§25.13.5"],
    cerca: (q) => Object.keys(window.__insegna).filter((k) => k.includes(q)),
  };

  return api;
}
