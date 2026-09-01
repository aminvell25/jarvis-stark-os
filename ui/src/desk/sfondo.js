/* Il nucleo — SPEC §25, rifatto sul riferimento HUD misurato.
 *
 * ## Che cos'è cambiato, e perché
 *
 * Fino al 31 agosto 2026 questo file montava cinque anelli concentrici col
 * marchio al centro. Il proprietario ha portato un riferimento proprio, con
 * l'analisi forense della sua geometria — otto sistemi concentrici, palette a
 * otto livelli, coreografia a cinque velocità — e ha chiesto di sostituirlo.
 *
 * Le cinque deroghe che ne seguono stanno in `docs/acceptance/NUCLEO-HUD.md`,
 * con la misura e il costo del ritorno. In breve, perché chi legge questo file
 * le trovi qui:
 *
 *   1. **invariante 19** — glow e bloom, con esenzione NOMINATA nell'audit per
 *      il solo nucleo;
 *   2. **§25.11** — three.js per il globo L5;
 *   3. **invariante 25** e **§10.3** «Fondo: immobile» — cinque velocità
 *      continue. §10.3 era l'unica riga del progetto mai violata;
 *   4. **§10.6** — la waveform, che è classe 2, sta nel fondo e non in un
 *      pannello;
 *   5. **§25.5** — `--cy-200` sta sopra il tetto `--cy-500`.
 *
 * Cio' che NON è derogato: invariante 18 (la palette è entrata in `tokens.css`
 * come tre gradini, non come letterali), invariante 23 (la telemetria è quella
 * vera del bus, nessun «APOGEE: 420.5 KM»), invariante 9 (anime.js, niente
 * GSAP), invariante 22 (ogni geometria passa dal `qualityGate`), invariante 20
 * (il testo è nel DOM o in nodi SVG veri), invariante 1 (il PCM resta nel core).
 *
 * ## La scala, che è il vincolo di tutto
 *
 * Il riferimento è disegnato per 1024x1024. Il nucleo vive in Ø326, dietro i
 * pannelli, e resta lì: la logica delle pagine non cambia. I RAGGI si
 * conservano come rapporti; le DENSITÀ si dimensionano perché il testo cada sui
 * gradini veri. Vedi `hud/geometria.js` e `hud/tipografia.js`.
 *
 * ## Il contratto verso il resto dell'app
 *
 * `crea(ospite)` torna `radice`, `aggiorna(msg)`, `stato(s)`, `forza`, `onda`,
 * `fase`, `ferma`, e monta `window.__insegna`. Non è un'API di comodo: la
 * pilotano `app/main.js` (giro `--nucleo`, `--verifica-scrivania`),
 * `scripts/occlusione-dom.js` (`data-disco`) e `npm run verifica:marchio`.
 * Cambiarla significa rompere quattro strumenti di misura in silenzio.
 */

import { animate, stagger } from "../../vendor/anime.esm.min.js";
import { STRATI } from "../hud/geometria.js";
import { crea as creaMoto } from "../hud/moto.js";
import { crea as creaGlobo, css as cssGlobo } from "../hud/globo.js";
import { Onda, css as cssOnda } from "../hud/onda.js";
import { costruisci, css as cssStrati, montaHex } from "../hud/strati.js";

export const meta = { nome: "sfondo", versione: "6" };

/* ⚠️ LE CAUSE, una per strato — §25.6 portata sugli otto strati del riferimento.
 *
 * La dottrina cambia UN VERBO rispetto a prima, e il verbo è tutto:
 *
 *     prima   se GIRA, sta lavorando
 *     adesso  se è ACCESO, sta lavorando
 *
 * Con la rotazione continua (deroga 3) il moto non è più un segnale: girano
 * tutti, sempre. Ma ogni strato ha ancora la propria causa, ogni causa è
 * ancora un fatto sul bus, e l'accensione è ancora **una per volta** — che è
 * il tetto che §25.5 pone e che la deroga non tocca.
 *
 * ⚠️ `hex` non ha una causa, e non è una dimenticanza: quello strato porta
 * DATI, non stato. Accenderlo direbbe che il dato «sta lavorando», che non
 * vuol dire niente.
 */
const CAUSE = [
  { chi: "t0",       strato: "mirino",     perche: "agent.mesh: nodo t0 — un impulso, poi ferma",
    impulso: true },
  { chi: "parla",    strato: "logo",       perche: "voice.spettro dal TTS: JARVIS sta parlando" },
  { chi: "t1",       strato: "segmentato", perche: "agent.mesh: nodo t1 attivo" },
  { chi: "ascolto",  strato: "quadranti",  perche: "voce.abilitata e voce.t1_vivo" },
  { chi: "subagent", strato: "globo",      perche: "agent.mesh: un subagent attivo" },
  { chi: "t2",       strato: "vetro",      perche: "agent.mesh: nodo t2 attivo" },
  { chi: "avviso",   strato: "tecnico",    perche: "agent.advisory, o livello sopra soglia §16" },
];

/* Le soglie di fase, DAL MOZZO VERSO IL BORDO. `state.snapshot.fase` dice
   quanto del core è costruito, e il nucleo si costruisce nello stesso ordine.
   Una fase sotto soglia non NASCONDE lo strato: lo porta a un sedicesimo di
   luce. Uno strato assente direbbe che il nucleo è più piccolo; uno spento
   dice che manca qualcosa da accendere. */
const SOGLIA_FASE = {
  mirino: 1, logo: 2, segmentato: 3, quadranti: 5,
  globo: 6, vetro: 7, tecnico: 8, hex: 9,
};
const SPENTO = 0.0625;
const ACCENSIONE_MS = 620;
const SPEGNIMENTO_MS = 1100;
const ONDA_MS = 900;
const GUSCIO_MS = 260;

/* ⚠️ L'AMPIEZZA NON CAMBIA, ed è una decisione esplicita del proprietario: il
   nucleo nuovo sta «nel centro con la sua stessa dimensione di quello vecchio,
   come elemento che viene anche coperto dai pannelli».
   0,386 è 0,552 × 0,7 — la seconda riduzione del 30 % — e la frazione resta
   scritta perché «0.386» da solo non direbbe da dove viene.
   §25.7 chiederebbe il 64 % dell'altezza dell'area pannelli, cioè Ø502: è una
   deroga già dichiarata il 23 agosto 2026 in `NUCLEO-TURNO-3.md`, e non si
   tocca qui. */
const AMPIEZZA = 0.552 * 0.7;

export const css = cssStrati + cssOnda + cssGlobo + `
/* Il nucleo sta DENTRO la scrivania come primo figlio, non nel body: nel body
   con z-index 0 finirebbe nello stesso strato di pittura dei fratelli, e lì
   vince l'ordine del DOM — la scialuppa opaca della scrivania viene dopo, è a
   schermo intero e ha il pavimento come fondo. */
.sfd {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}
/* Il blocco centrale: il nome, e sotto l'onda. Fuori dal flusso, centrato da
   sé: due traslazioni ciascuna metà del proprio lato è il centro esatto a
   qualunque dimensione, senza sapere quale sia. */
.sfd__centro {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: grid;
  justify-items: center;
  gap: var(--s-1);
}
/* La scritta è l'unica cosa del nucleo che NON gira: è il nome, e un nome che
   si muove non si legge. */
.sfd__marchio {
  position: relative;
  font-family: var(--font-ui);
  font-weight: 600;
  /* ⚠️ --cy-600, E NON È IL GRADINO CHE §25.13.2 NOMINA. Ci sono volute tre
     misure, e il valore l'ha scelto il criterio, non io.
     §25.13.2 regola 4 fissa il marchio a --cy-700. Con il nucleo HUD sotto la
     scritta c'è il reticolo L1, che è lì per disegno — il riferimento ce l'ha —
     e alza il composito a L 45. Misurato, in tutti e nove gli stati:

       --cy-700  L  99,6   2,73:1   sotto il pavimento di 3,0 — non si legge
       --cy-500  L 181,4   7,99:1   oltre il tetto di 5,0 — compete col dato
       --cy-600  L 141,6   4,65:1   ✅ dentro la forbice

     Fra --cy-700 e --cy-500 non c'era niente: il gradino che risolve è uno dei
     TRE che la palette misurata del riferimento ha portato in §10.1. La
     forbice si è chiusa con un colore del riferimento stesso, non con una
     deroga — ed è la ragione per cui quei tre gradini valevano la misura.

     §25.13.2 regola 4 va quindi riletta: nomina un token dove intendeva una
     FORBICE, e il token giusto dipende da che cosa passa sotto il nome. Il
     criterio che conta è §25.13.5, che misura, ed è verde. */
  color: var(--cy-600);
  white-space: nowrap;
  user-select: none;
  letter-spacing: 0.3em;
  text-indent: 0.3em;
  /* ⚠️ LO SCUDO, e §25.13.4 lo dichiara ammesso proprio per questo caso.
   *
   * Il nome è largo abbastanza da passare sopra i cerchi di L1 (r 13-32) e L2
   * (r 66-81): l'inchiostro arriva a 82 unità. Misurato, quelle tracce
   * portavano il composito sotto la scritta a L 51,3 e il contrasto a 2,71:1,
   * sotto il 3,0 che §25.13.5 chiede.
   *
   * La risposta non è alzare il marchio — §25.13.2 regola 4 lo fissa a
   * --cy-700, e il gradino sopra dà 5,95:1, che sfonda il tetto. E non è
   * togliere i cerchi, che sono il riferimento.
   *
   * ⚠️ **NON È L'ALONE CHE L'INVARIANTE 19 VIETA**, ed è la distinzione che
   * conta: un alone AGGIUNGE luce attorno a un elemento, questo ne TOGLIE. È
   * del colore del pavimento, e l'audit lo distingue misurando la luminanza
   * contro il fondo pagina — che è --bg-void.
   *
   * Tre veli invece di uno: uno solo con lo stesso raggio avrebbe un bordo
   * netto e si vedrebbe come un'ombra; tre di raggio decrescente sfumano. */
  text-shadow:
    0 0 34px var(--bg-void),
    0 0 18px var(--bg-void),
    0 0 8px var(--bg-void);
  /* ⚠️ IL BAGLIORE SUL NOME È STATO TOLTO, e la ragione è misurata.
   *
   * Il riferimento lo prescrive: «glow text-shadow 0 0 6px #77C3D5AA». L'ho
   * montato, e verifica:marchio ha smesso di poter misurare: il criterio
   * §25.13.5 separa l'inchiostro dallo scudo confrontando due scatti — col
   * nome e senza — e chiamando «tratto» i pixel che si SCHIARISCONO. Un
   * bagliore schiarisce anche tutto l'intorno, e la separazione fra ciò che è
   * la scritta e ciò che le sta attorno smette di esistere: pixelTratto va a
   * zero e il criterio non ha più niente su cui misurare il contrasto.
   *
   * Non è una regola che si può derogare a parole: è il METODO di misura che
   * non regge più. Fra un bagliore sul nome e la sola guardia che tiene il
   * marchio leggibile in tutti gli stati, resta la guardia.
   *
   * Il bagliore resta dove il riferimento lo chiama «forte» e dove si misura:
   * sugli strati SVG (hud/strati.js), contati da test_nucleo.py.
   *
   * ⚠️ Chi volesse rimetterlo deve prima insegnare a scripts/densita.mjs a
   * distinguere l'inchiostro dal proprio alone — e allora sarà una misura
   * nuova, non una riga di CSS. */
}

/* ⚠️ Le due letture: fondo pieno, e non è decorazione. Sopra una fascia a
   --cy-700 un testo a --txt-dim non si legge, e non è un problema del colore
   del testo: è un problema di che cosa gli passa sotto. È la stessa soluzione
   che la banda di pnl-anelli usa da sempre — «mascherando gli anelli dietro un
   fondo pieno invece di sperare che non si sovrappongano». */
.sfd__lettura {
  position: absolute;
  display: grid;
  padding: 0 var(--s-1);
  background: var(--bg-void);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.14em;
  color: var(--txt-dim);
  user-select: none;
  white-space: nowrap;
}
.sfd__lettura--alto { left: 50%; transform: translate(-50%, -100%); }
.sfd__lettura--basso { left: 50%; transform: translate(-50%, 0); }
.sfd__riga { display: flex; justify-content: space-between; gap: var(--s-3); }
.sfd__chiave { color: var(--txt-ghost); }
.sfd__valore { color: var(--cy-600); }
/* Lo stato vuoto si LEGGE: non è un valore mancante, è una riga che dice che
   il core non ha ancora parlato. Invariante 23, seconda metà. */
.sfd__lettura[data-vuoto="si"] .sfd__valore { color: var(--txt-ghost); }
`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "sfd";

  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "hud__svg");
  svg.setAttribute("aria-hidden", "true");
  radice.appendChild(svg);

  const { gruppi, ruote, scatti, accesi, vertici, lancetta, icone } =
    costruisci(svg, { acceso: true });
  const hex = montaHex(svg, 326);

  /* ⚠️ LA SFERA STA SOPRA L'SVG, e non è una scelta di z-index: è una
     conseguenza. Il corpo del disco è un cerchio OPACO fino a L8 — serve a far
     leggere il nucleo come un oggetto invece che come anelli sospesi — quindi
     una sfera disegnata sotto non si vedrebbe affatto.
     Sopra, il canvas ha alpha e dipinge solo punti e reticolo: le corone
     restano visibili fra un punto e l'altro, ed è così che il riferimento la
     mostra — un reticolo che attraversa i quadranti, non un fondo dietro. */
  const globo = creaGlobo(radice);

  /* ── Le letture, e perché NON dicono «APOGEE: 420.5 KM» ─────────────────
   *
   * Il riferimento mette qui `TARGET: MARK XL ARMOR`, `DISTANCE`, `VELOCITY`,
   * `APOGEE`, `PERIGEE`, `ALTITUDE`. Sono dati inventati, e l'invariante 23 li
   * vieta: §11.9 chiama i dati finti «la causa singola più frequente di UI
   * generata che sembra finta».
   *
   * Il blueprint stesso lo dice, ed è la sua riga migliore: quei testi
   * «diventano **stato reale del sistema**». TARGET è il task attivo, DISTANCE
   * e VELOCITY sono latenze, APOGEE/PERIGEE/ALTITUDE sono CPU/RAM/temperatura.
   * Qui è esattamente quello che sono.
   *
   * ⚠️ Nascono col trattino, non con uno zero: uno zero direbbe «CPU allo zero
   * per cento», che è un'altra cosa da «il core non ha ancora parlato». */
  function creaLettura(classe, chiavi) {
    const el = document.createElement("div");
    el.className = "sfd__lettura " + classe;
    el.dataset.vuoto = "si";
    const valori = new Map();
    for (const k of chiavi) {
      const riga = document.createElement("div");
      riga.className = "sfd__riga";
      const c = document.createElement("span");
      c.className = "sfd__chiave";
      c.textContent = k;
      const v = document.createElement("span");
      v.className = "sfd__valore";
      v.textContent = "—";
      riga.append(c, v);
      el.appendChild(riga);
      valori.set(k, v);
    }
    radice.appendChild(el);
    return { el, valori };
  }

  const alto = creaLettura("sfd__lettura--alto", ["AGENTE", "FASE", "MESH"]);
  const basso = creaLettura("sfd__lettura--basso", ["CPU", "RAM", "TEMP", "VOCE"]);

  const centro = document.createElement("div");
  centro.className = "sfd__centro";
  const marchio = document.createElement("span");
  marchio.className = "sfd__marchio";
  marchio.textContent = "J.A.R.V.I.S.";
  centro.appendChild(marchio);

  /* L'onda sotto il nome, dentro il campo. È la classe 2 di §10.6 nel fondo —
     deroga 4 — e a sorgente spenta costa zero fotogrammi. */
  const tela = document.createElement("canvas");
  tela.className = "hud__onda";
  tela.setAttribute("aria-hidden", "true");
  centro.appendChild(tela);
  const onda2 = new Onda(tela, { bande: 32, specchiata: true });

  radice.appendChild(centro);

  /* ⚠️ Il contatore dei fotogrammi è l'invariante 25 reso misurabile, e dal
     31 agosto 2026 NON dirà più zero a riposo: è la deroga che si vede nella
     misura. Nasconderla sarebbe stato il modo di prendersela senza pagarla.
     Conta le animazioni di STATO — accensioni, fase, onda — che sono quelle
     che devono esaurirsi; la rotazione continua è dichiarata a parte, in
     `moto.stato()`. Lo legge `scripts/occlusione-dom.js`. */
  let fotogrammi = 0;
  const conta = () => { fotogrammi++; };
  let faseOra = null;

  const moto = creaMoto({ gruppi, ruote, scatti, lancetta }, conta);

  /* ── L'accensione, che è dove il segnale si è spostato ────────────────── */
  const attivo = Object.fromEntries(CAUSE.map((c) => [c.chi, false]));
  const inLuce = new Map(CAUSE.map((c) => [c.strato, false]));
  let forzato = null;

  function accendi(strato, deve) {
    if (inLuce.get(strato) === deve) return;
    inLuce.set(strato, deve);
    const nodo = accesi.get(strato);
    if (!nodo) return;
    animate(nodo, {
      opacity: deve ? 1 : 0,
      duration: deve ? ACCENSIONE_MS : SPEGNIMENTO_MS,
      ease: deve ? "out(2)" : "inOut(2)",
      onUpdate: conta,
    });
  }

  /* ⚠️ LE ICONE SI ACCENDONO SU UN FATTO, non su un'atmosfera.
   *
   * Nel riferimento le quattro icone cardinali sono chrome. Qui ognuna dice una
   * cosa che il bus porta gia', e §25.11 lo pretende — «il nucleo non è il
   * posto dove mettere ciò che non sta nei pannelli».
   *
   * Sono ATTRIBUTI e non animazioni, e la differenza è voluta: un'icona è un
   * simbolo, e un simbolo o c'è o non c'è. Farla dissolvere direbbe che il
   * fatto è vero a metà. Gli anelli si accendono con una rampa perché sono
   * superfici e la rampa dice «sta cominciando»; un'icona no.
   */
  function accendiIcone() {
    const acceso = {
      agente: Boolean(attivo.t1 || attivo.t2 || attivo.subagent),
      avviso: Boolean(attivo.avviso),
      // ⚠️ `coreVivo === false` e non `!coreVivo`: `null` vuol dire «il core non
      // ha ancora detto niente», che non è «il core non c'è». Il satellite
      // resta spento finché non arriva un fatto, e non lampeggia all'avvio.
      collegato: coreVivo === true,
      voce: Boolean(voce && voce.abilitata),
    };
    for (const [chi, nodo] of icone)
      nodo.setAttribute("data-acceso", acceso[chi] ? "si" : "no");
    return acceso;
  }

  function componi() {
    for (const c of CAUSE) {
      // Una causa d'impulso non tiene acceso niente: il suo strato lampeggia e
      // torna al buio da solo. T0 non «dura», succede — §25.6 alla lettera.
      if (!c.impulso) accendi(c.strato, Boolean(attivo[c.chi]));
      gruppi.get(c.strato)?.setAttribute("data-attivo", attivo[c.chi] ? "si" : "no");
    }
    accendiIcone();
    radice.dataset.acceso = [...inLuce.values()].some(Boolean) ? "si" : "no";
    /* `data-moto` dice sempre «si», ed è la deroga dichiarata nel DOM: chi
       misura la trova senza leggere questo file. */
    radice.dataset.moto = moto.stato().fissato ? "no" : "si";
  }

  function impulso(strato) {
    const nodo = accesi.get(strato);
    if (!nodo) return;
    animate(nodo, { opacity: [0, 1, 0], duration: 420, ease: "out(4)", onUpdate: conta });
  }

  /* L'onda: un guscio di luce dal mozzo al bordo. È uno STAGGER, non un calcolo
     per fotogramma — anime.js sa già ritardare N bersagli, ed è il motore unico
     dell'invariante 9. La direzione dice da dove viene: dal centro. */
  const dalMozzo = CAUSE.map((c) => accesi.get(c.strato)).filter(Boolean);

  function onda() {
    animate(dalMozzo, {
      opacity: [0, 1, 0],
      duration: GUSCIO_MS,
      delay: stagger(ONDA_MS / Math.max(1, dalMozzo.length)),
      ease: "inOut(2)",
      onUpdate: conta,
      // Chi è acceso perché sta lavorando resta acceso: il guscio passa SOPRA
      // lo stato, non al posto suo.
      onComplete: () => {
        for (const c of CAUSE)
          if (inLuce.get(c.strato)) accesi.get(c.strato).style.opacity = "1";
      },
    });
  }

  /* ── La misura ─────────────────────────────────────────────────────────
   * ⚠️ È UN NO-OP SE NULLA È CAMBIATO, e serve contro un anello di retroazione
   * del ResizeObserver: la richiamata cambia la dimensione del disco e il corpo
   * della scritta, cioè due cose che possono rimettere in discussione il
   * riquadro osservato. Un observer che si risveglia da solo non emette nessun
   * errore: blocca il thread e la pagina resta nera. */
  let wPrec = 0, hPrec = 0;
  function misura(forza) {
    const w = radice.clientWidth || ospite.clientWidth || 1200;
    const h = radice.clientHeight || ospite.clientHeight || 800;
    if (!forza && w === wPrec && h === hPrec) return;
    wPrec = w; hPrec = h;
    const R = (Math.min(w, h) / 2) * AMPIEZZA;
    const lato = (2 * R).toFixed(1);
    svg.style.width = lato + "px";
    svg.style.height = lato + "px";
    hex.ridimensiona(2 * R);

    /* Il disco si dichiara nel DOM: è la sola forma in cui una misura esterna
       può saperlo senza copiare AMPIEZZA in un secondo file. Tre numeri in
       pixel CSS relativi a `.sfd`: centro x, centro y, raggio.
       Lo legge `scripts/occlusione-dom.js`. */
    radice.dataset.disco = [w / 2, h / 2, R].map((v) => v.toFixed(1)).join(",");

    /* ⚠️ IL NOME NON STA DENTRO L2, e la prosa del blueprint qui è imprecisa.
     *
     * ⚠️ IL NOME STA DENTRO L3, e ci sono volute due letture per arrivarci.
     *
     * La prima stesura lo faceva largo il 31 % del disco, da una lettura a
     * occhio dell'immagine. Reso e guardato, il risultato era illeggibile: le
     * lettere centrali cadevano sull'anello segmentato — quello che il
     * riferimento chiama «il più luminoso dell'HUD» — e ci sparivano dentro.
     *
     * A decidere è il **profilo radiale misurato**, che è il documento e non
     * l'impressione: marca L2 come «text circle» al 13 % del raggio e L3 come
     * «seg. ring» al 22 %. Un nome largo il 31 % sfonderebbe il secondo, e la
     * riga «cerchio che inquadra il logo» non vorrebbe più dire niente.
     *
     * Quindi: **l'anello luminoso CIRCONDA il nome**, non ci passa sopra. Il
     * limite è il bordo interno di L3, e il nome ci sta dentro con un filo di
     * campo attorno — un nome che tocca il proprio contorno non ci sta sopra,
     * ci sta incastrato.
     *
     * ⚠️ **Il confronto per sovrapposizione NON è stato eseguito**: il file
     * dell'immagine non è sul disco, quindi il cancello che il piano prevedeva
     * per F1 resta **non misurato**. Chi salva il riferimento in
     * `docs/design-reference/` può verificare questa lettura invece di
     * crederle. `NON VERIFICATO` non è `PASS`. */
    /* ⚠️ TERZA LETTURA, e questa l'ha decisa la MISURA invece dell'occhio.
     *
     *   1ª  larghezza 31 % del disco, letta a occhio sull'immagine
     *       -> il nome cadeva sull'anello luminoso L3 e spariva;
     *   2ª  dentro il bordo interno di L3 (r=103)
     *       -> attraversava L2 (r 66-81), e il composito sotto la scritta
     *          saliva a L 50,7: contrasto **2,72:1**, sotto il 3,0 di §25.13.5.
     *          Nemmeno lo scudo bastava — l'ha spostato di 0,01;
     *   3ª  dentro il bordo interno di L2 (r=66).
     *
     * Ed è quello che il blueprint diceva dall'inizio: L2 è «la circonferenza
     * che **inquadra** il logo». Ci sono volute due misure per credergli.
     *
     * Il nome è piccolo, e va detto: su Ø326 fa una quarantina di pixel. Non è
     * un difetto di questa scelta, è la conseguenza della decisione di tenere
     * il nucleo alla dimensione di prima — a Ø800 lo stesso rapporto darebbe
     * un centinaio di pixel. La geometria del riferimento è quella. */
    const perUnita = (2 * R) / 1024;
    const l2 = STRATI.find((s) => s.id === "logo");
    const limiteR = l2.r[0] * perUnita;
    let fs = R * 0.15;
    marchio.style.fontSize = fs.toFixed(1) + "px";
    const largo = marchio.getBoundingClientRect().width;
    if (largo > 4) {
      fs *= (1.72 * limiteR) / largo;
      marchio.style.fontSize = fs.toFixed(1) + "px";
    }
    /* Le letture si ancorano al bordo di L6, appena dentro la corona
       esadecimale: fuori dal campo del nome e sopra le fasce, dove il fondo
       pieno le rende leggibili. Il blocco alto cresce verso l'ALTO — `top` è il
       bordo superiore, e un blocco ancorato sopra ricadrebbe dentro per tutta
       la propria altezza. */
    /* L'onda è larga il 132 % del raggio del campo e alta un terzo: è la
       proporzione del riferimento, dove sotto il nome c'è un nastro basso e
       largo, non un istogramma. Le due quote sono frazioni del campo, non
       numeri: se la composizione degli anelli cambia, l'onda la segue. */
    globo.misura(2 * R);
    onda2.misura(Math.max(8, Math.round(limiteR * 1.32)),
                 Math.max(6, Math.round(limiteR * 0.34)));

    // La corona si rifà: la capienza dipende dal riquadro, che è appena cambiato.
    scriviHex();
    /* ⚠️ Ancorate al bordo di L7, non a una frazione di L6: guardato allo
       scatto, a 0,62 e 0,42 i due riquadri coprivano il quadrante interno e
       l'anello luminoso, cioè le due cose più dense del nucleo. Fuori da L7
       stanno sulla fascia scura, che è dove il riferimento mette i propri. */
    /* ⚠️ ANCORATE A L6, non a L7, e la correzione l'ha imposta uno scatto.
       Con l'ancoraggio al bordo di L7 (351 unità) il blocco cresceva verso
       l'alto per la propria altezza — tre righe, un'ottantina di unità — e
       arrivava a 433: dentro l'anello delle icone, che sta a 422. Il chip in
       cima spariva sotto la lettura.
       A L6 (301) il blocco si ferma a 383, un'unità sotto la guida interna
       delle icone. Il numero non è scelto: è dove finisce la fascia. */
    const l6b = STRATI.find((s) => s.id === "vetro");
    const bordo = l6b.r[l6b.r.length - 1] * perUnita;
    alto.el.style.top = (h / 2 - bordo).toFixed(1) + "px";
    basso.el.style.top = (h / 2 + bordo).toFixed(1) + "px";

    const r = centro.getBoundingClientRect();
    const angolo = Math.hypot(r.width / 2, r.height / 2);
    if (angolo > limiteR * 0.94) {
      fs *= (limiteR * 0.94) / angolo;
      marchio.style.fontSize = fs.toFixed(1) + "px";
    }
  }

  /* ── La fase ────────────────────────────────────────────────────────────
   * ⚠️ L'opacità del gruppo `posto` è della FASE e di nessun altro. Lo scatto e
   * l'accensione lavorano su altre due proprietà di altri due nodi: una
   * proprietà, un padrone. Due animazioni sulla stessa opacità si
   * sovrascrivono a vicenda senza dire niente, ed è un difetto che questo
   * progetto ha già pagato due volte. */
  function applicaFase(n) {
    if (typeof n !== "number" || n === faseOra) return;
    const prima = faseOra;
    faseOra = n;
    for (const [id, soglia] of Object.entries(SOGLIA_FASE)) {
      const nodo = gruppi.get(id);
      if (!nodo) continue;
      animate(nodo, {
        opacity: n >= soglia ? 1 : SPENTO,
        duration: 420,
        // Il primo dato non è un cambiamento: la fase iniziale si posa, non si
        // anima. Animarla farebbe leggere l'avvio come un evento.
        ease: prima === null ? "linear" : "out(3)",
        onUpdate: conta,
      });
    }
  }

  /* ── L'ingresso dei dati ─────────────────────────────────────────────── */
  let voce = null, livello = null, coreVivo = null;

  function aggiorna(m) {
    const topic = m?.topic;
    if (!topic) return;
    /* ⚠️ «telemetry» arriva a 2,5 Hz qualunque cosa accada: è il battito, non
       il lavoro, e il nucleo non gli REAGISCE — nessuna causa cambia. La
       guardia sta PRIMA che qualcuno guardi il carico: un battito che entra e
       poi viene scartato ha comunque attraversato il componente, e il giorno
       che qualcuno aggiunge una riga sopra la guardia il moto comincia a
       seguire un tasso costante senza che nulla lo dica. */
    if (topic === "telemetry") { scriviTelemetria(m.payload ?? m); return; }
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
    if (topic === "agent.advisory") { decidi(); onda(); }
    if (topic === "voice.state") { voce = msg; decidi(); }
    if (topic === "voice.spettro") {
      onda2.imposta(msg.bande, msg.sorgente);
      // I punti si gonfiano con la voce — ×(1 + 0,5·A), come il riferimento.
      globo.ampiezza(Math.max(0, ...(msg.bande || [0]).map(Number)));
      basso.el.dataset.vuoto = "no";
      basso.valori.get("VOCE").textContent = onda2.etichetta();
      // «parla» è il ramo TTS: è l'unico caso in cui la sorgente è JARVIS.
      if (!forzato) { attivo.parla = msg.sorgente === "tts"; componi(); scriviAgente(); }
    }
  }

  /* ⚠️ L'ESADECIMALE NON È UN TRAVESTIMENTO.
   *
   * Il riferimento porta una stringa di cifre lunga tutta la corona esterna, e
   * la tentazione è riempirla di caratteri a caso. Qui è la stessa telemetria
   * del riquadro in basso, in base 16: `0x7C` e `124` sono lo stesso numero
   * misurato. Chi vuole verificarlo legge le due cose sullo stesso scatto, ed è
   * apposta.
   *
   * Finché il core non ha parlato la corona resta VUOTA. Uno stato vuoto si
   * vede ed è onesto; una stringa inventata no. */
  function esa(v, cifre) {
    if (!Number.isFinite(v)) return "-".repeat(cifre);
    return (Math.max(0, Math.round(v)) % 16 ** cifre)
      .toString(16).toUpperCase().padStart(cifre, "0");
  }

  let campioni = 0;

  function scriviTelemetria(d) {
    if (!d) return;
    const cpu = Number(d.cpu_percent), ram = Number(d.ram_percent);
    const tmp = d.package_temp_c == null ? null : Number(d.package_temp_c);
    basso.el.dataset.vuoto = "no";
    basso.valori.get("CPU").textContent = Number.isFinite(cpu) ? cpu.toFixed(1) + " %" : "—";
    basso.valori.get("RAM").textContent = Number.isFinite(ram) ? ram.toFixed(1) + " %" : "—";
    /* La temperatura può NON ESISTERE: `package_temp()` torna None su una
       macchina senza quel sensore. «N/D» è lo stato vuoto di quella riga, e non
       uno zero — uno zero direbbe che il processore è a zero gradi. */
    basso.valori.get("TEMP").textContent = tmp === null ? "N/D" : tmp.toFixed(1) + " C";

    campioni++;
    scriviHex(
      esa(Number.isFinite(cpu) ? cpu * 10 : NaN, 4) +
      esa(Number.isFinite(ram) ? ram * 10 : NaN, 4) +
      esa(tmp === null ? NaN : tmp * 10, 4) +
      esa(campioni, 6));
  }

  /** La stringa sulla corona: si ripete finché copre il cerchio.
   *  Quanti caratteri stiano sul giro lo dice `tipografia.js` dal raggio e dal
   *  corpo — non un numero scritto a mano, che al primo resize sarebbe falso.
   *
   *  ⚠️ IL BLOCCO SI RICORDA, e serve a due cose diverse che sembrano una.
   *  La prima: un dato può arrivare PRIMA che il riquadro sia noto — nella
   *  galleria succede sempre, perché il mount alimenta il componente nello
   *  stesso turno in cui lo crea, e `misura()` gira al fotogramma dopo. Senza
   *  memoria quel dato andrebbe perso, e con un `capienza(0)` il componente
   *  solleva: «diametro non valido: 0», che è come l'ho scoperto.
   *  La seconda: a ogni resize la capienza cambia, e la stringa va rifatta —
   *  altrimenti resta lunga per la finestra di prima. */
  let ultimoHex = "";

  function scriviHex(blocco) {
    if (blocco) ultimoHex = blocco;
    if (!ultimoHex) return;
    const diametro = 2 * ((Math.min(wPrec, hPrec) / 2) * AMPIEZZA);
    if (!(diametro > 0)) return;          // il riquadro non è ancora noto
    const quanti = hex.capienza(diametro);
    /* ⚠️ SI RIEMPIE OLTRE LA CAPIENZA, di un blocco intero, e serve allo
       scorrimento: un `textPath` non si avvolge, e ciò che esce dalla fine del
       tracciato sparisce invece di ricomparire all'inizio. Con un blocco di
       margine, il tracciato ha glifi sopra per tutta la corsa. */
    const ripetizione = ultimoHex + " ";
    let s = ripetizione;
    while (s.length < quanti + ripetizione.length) s += ripetizione;
    hex.nodo.textContent = s;
    // La capienza cambia col riquadro: lo scorrimento si rifà sui numeri nuovi.
    moto.scorriHex(hex.nodo, ripetizione.length, quanti);
  }

  function scriviAgente() {
    const nome = attivo.t1 ? "T1" : attivo.t2 ? "T2"
      : attivo.subagent ? "SUB" : attivo.parla ? "TTS"
      : attivo.ascolto ? "ASCOLTO" : "INERTE";
    alto.el.dataset.vuoto = "no";
    alto.valori.get("AGENTE").textContent = nome;
    alto.valori.get("FASE").textContent = faseOra === null ? "—" : String(faseOra);
  }

  const statiNodi = new Map();
  let nodiVisti = false;
  function guardaNodi(nodi) {
    if (!Array.isArray(nodi) || forzato) return;
    let cambiati = 0;
    const visto = { t0: false, t1: false, t2: false, subagent: false };
    for (const nd of nodi) {
      const id = String(nd?.id ?? nd?.nome ?? "");
      if (!id) continue;
      const s = String(nd.stato ?? (nd.attivo ? "attivo" : "inerte"));
      if (statiNodi.has(id) && statiNodi.get(id) !== s) cambiati++;
      statiNodi.set(id, s);
      if (!nd.attivo) continue;
      if (id === "t0" || id === "t1" || id === "t2") visto[id] = true;
      else if (nd.tipo === "subagent" || nd.kind === "subagent") visto.subagent = true;
    }
    if (visto.t0 && !attivo.t0) impulso("mirino");
    Object.assign(attivo, visto);
    alto.el.dataset.vuoto = "no";
    alto.valori.get("MESH").textContent =
      `${nodi.filter((n) => n.attivo).length}/${nodi.length}`;
    componi();
    // Il PRIMO elenco non produce onda: non è un cambiamento, è il primo dato.
    if (!nodiVisti) { nodiVisti = true; return; }
    if (cambiati) onda();
  }

  function decidi() {
    const spento = Boolean(voce && voce.abilitata === false);
    const offline = livello === "offline" || coreVivo === false;
    if (!forzato) {
      attivo.ascolto = Boolean(!spento && !offline && voce?.abilitata && voce?.t1_vivo);
      attivo.avviso = offline || (livello !== null && livello !== "nominal");
    }
    radice.dataset.livello = offline ? "offline" : (livello ?? "nominal");
    radice.dataset.stato = spento ? "spento"
      : offline ? "offline"
      : attivo.t1 ? "t1" : attivo.t2 ? "t2"
      : attivo.parla ? "parla" : attivo.ascolto ? "ascolto" : "inerte";
    if (spento || offline) onda2.spegni();
    basso.valori.get("VOCE").textContent = onda2.etichetta();
    componi();
    scriviAgente();
  }

  function stato(s) {
    if (!s) return;
    if (typeof s === "string") { forza(s in attivo ? s : null); return; }
    if (s.voce) voce = s.voce;
    if (s.livello) livello = s.livello;
    if (typeof s.core_vivo === "boolean") coreVivo = s.core_vivo;
    decidi();
  }

  /** Impone una causa a mano, per la verifica. `forza(null)` restituisce il
   *  comando ai fatti del bus.
   *
   *  ⚠️ Rimette in moto SOLO se nessuno ha fissato: `forza` arriva anche dal
   *  bus — `app.js` la chiama a ogni cambio di connessione — e un messaggio
   *  che sfonda un fermo voluto rende la cattura di §11.7 un sondaggio. */
  function forza(chi) {
    forzato = chi && chi in attivo ? chi : null;
    for (const k of Object.keys(attivo)) attivo[k] = false;
    if (forzato) attivo[forzato] = true;
    if (forzato === "t0") impulso("mirino");
    if (!moto.stato().fissato) { moto.libera(); globo.avvia(); }
    decidi();
  }

  /** Toglie il fermo. La leva esplicita. */
  function libera() { moto.libera(); globo.avvia(); componi(); }

  /* ⚠️ FISSA IL CASO PEGGIORE, invece di rincorrerlo.
   *
   * L'impulso di T0 è `opacity: [0, 1, 0]` in 420 ms: il picco sta nei primi
   * fotogrammi, e `capturePage()` costa fra 50 e 150 ms. Rincorrerlo con
   * un'attesa dà un fotogramma a caso — e un criterio misurato su un fotogramma
   * a caso non è un criterio, è un sondaggio.
   *
   * Porta gli strati accesi al proprio ESTREMO e ferma tutto. Non falsifica
   * niente: **1 è il picco di `[0, 1, 0]`**, quindi si misura il caso peggiore.
   *
   * ⚠️ E AZZERA le rotazioni: due catture di due stati diversi devono
   * differire per lo STATO e non per l'angolo. */
  function fissa(nome) {
    moto.fissa();
    globo.azzera();
    for (const [id] of inLuce) inLuce.set(id, false);
    for (const c of CAUSE) {
      const nodo = accesi.get(c.strato);
      if (!nodo) continue;
      nodo.style.opacity = String(nome === "onda" ? 1 : (c.chi === nome ? 1 : 0));
    }
    radice.dataset.stato = nome === "riposo" ? "inerte" : nome;
    radice.dataset.livello =
      nome === "offline" ? "offline" : nome === "warn" ? "warn"
      : nome === "critical" ? "critical" : "nominal";
    radice.dataset.moto = "no";
    return {
      stato: radice.dataset.stato,
      livello: radice.dataset.livello,
      accesi: CAUSE.map((c) => +(accesi.get(c.strato)?.style.opacity ?? 0)),
    };
  }

  function geometria() {
    const rr = marchio.getBoundingClientRect();
    const b = radice.getBoundingClientRect();
    const R = (Math.min(b.width, b.height) / 2) * AMPIEZZA;
    /* ⚠️ LO STESSO LIMITE CHE USA `misura()`, e la prima stesura ne riportava
       un altro: dimensionava il nome contro il bordo interno di L3 e poi
       dichiarava quello di L2. Il criterio ne usciva con un franco di **−6 px**
       su un nome che stava benissimo dov'era — cioè misurava una cosa e ne
       vincolava un'altra.
       Due letture dello stesso limite sono due opinioni: si deriva. */
    const l2g = STRATI.find((s) => s.id === "logo");
    const campoPx = l2g.r[0] * ((2 * R) / 1024);
    const inchiostro = Math.hypot(rr.width / 2, rr.height / 2);
    return {
      raggioDisco: +R.toFixed(1),
      raggioMinimoFascia: +campoPx.toFixed(1),
      raggioMassimoInchiostro: +inchiostro.toFixed(1),
      franco: +(campoPx - inchiostro).toFixed(1),
      marchio: [Math.round(rr.width), Math.round(rr.height)],
    };
  }

  let inCoda = 0;
  const ro = new ResizeObserver(() => {
    if (inCoda) return;
    inCoda = requestAnimationFrame(() => { inCoda = 0; misura(); });
  });
  ro.observe(radice);
  requestAnimationFrame(() => misura(true));
  decidi();
  globo.avvia();

  window.__insegna = {
    forza, onda, impulso, fissa, libera, geometria,
    fase: applicaFase,
    get faseOra() { return faseOra; },
    get statoOra() { return radice.dataset.stato ?? "inerte"; },
    get fotogrammi() { return fotogrammi; },
    /* ⚠️ `moto` NON dice più quello che diceva. Prima significava «questo
       anello sta girando»; con la deroga girano tutti e la risposta sarebbe
       sempre `true`, cioè nessuna informazione. Adesso è un alias di `acceso`,
       che è dove il segnale si è spostato. Resta col vecchio nome perché
       `app/main.js` lo interroga. */
    get causeOra() {
      return CAUSE.map((c) => ({
        ...c, acceso: inLuce.get(c.strato), moto: inLuce.get(c.strato),
      }));
    },
    get motoOra() { return moto.stato(); },
    //: La lancetta, per la verifica: dove punta e quante volte ha cercato.
    cerca: () => moto.stato().scattiLancetta,
    //: Quali icone sono accese, per chi verifica che dicano un fatto e non
    //: un'atmosfera.
    get iconeOra() {
      return Object.fromEntries([...icone].map(([chi, n]) =>
        [chi, n.getAttribute("data-acceso") === "si"]));
    },
    get ondaOra() { return onda2.stato(); },
    get globoOra() { return globo.stato(); },
    //: Ridisegna la tela WebGL. La chiama `app/main.js` prima di ogni
    //: cattura di §25.13.5: senza, i due scatti differiscono sul reticolo
    //: del globo e la misura conta quello come se fosse la scritta.
    rendiGlobo: () => globo.rendi(),
    /* ⚠️ Le soglie di TUTTI gli strati, in ordine di DOM — non solo di quelli
       che hanno una causa. Chi le legge (`app/main.js`) le confronta con le
       opacità lette dal documento, che sono otto: sette soglie contro otto
       opacità è un confronto fra due cose diverse, e falliva sempre. */
    soglie: [...gruppi.keys()].map((id) => SOGLIA_FASE[id]),
    cause: CAUSE.map((c) => c.chi),
    //: La deroga, dichiarata dove chi misura la trova.
    deroghe: ["invariante 19 glow", "§25.11 three.js nel fondo",
              "invariante 25 e §10.3 rotazione continua",
              "§10.6 classe 2 fuori da un pannello", "§25.5 --cy-200"],
    get strati() { return [...gruppi.keys()]; },
    vertici,
  };

  return {
    radice, aggiorna, stato, forza, onda,
    fase: applicaFase,
    vertici: [],
    ferma() { ro.disconnect(); moto.ferma(); onda2.ferma(); globo.smonta(); },
  };
}
