/* La scrivania — SPEC §13.
 *
 * Tiene insieme quattro cose: **quali pannelli esistono adesso**, **in quale
 * workspace**, **dove**, e **chi glielo ha chiesto** — tastiera, dock, voce o
 * gesture. Le quattro strade finiscono tutte qui, e non in quattro punti
 * diversi che col tempo si comportano in modo leggermente diverso.
 *
 * ## I pannelli si compongono quando servono, e poi restano
 *
 * Entrare in un workspace la prima volta lo COMPONE; uscirne nasconde, non
 * distrugge. Distruggere costerebbe i dati: il core manda l'albero dei
 * sorgenti, i fusi e l'archivio **una volta sola**, a chi si collega (§6.3,
 * il renderer non puo' chiedere), e un pannello ricreato ripartirebbe dallo
 * stato vuoto per sempre. Chi nasce tardi lo copre la riconsegna del bus.
 *
 * ## «Affianca» non e' un secondo algoritmo
 *
 * `Alt+T` ri-applica la disposizione dichiarata in `moduli.js`. Un
 * affiancamento calcolato a parte sarebbe una seconda opinione su dove vanno
 * le finestre, e le due divergerebbero al primo pannello aggiunto.
 */

import { CATEGORIE, COLONNE, RIGHE, composizioneIniziale, modulo }
  from "./moduli.js";
import { aggiornaLimiti, applicaGeometria, creaCornice, geometriaDi }
  from "./cornice.js";
import { tokPx } from "../style/tokens.js";

export const meta = { nome: "scrivania", versione: "1" };

export function creaScrivania({ bus, misuraArea, suDisposizione }) {
  //: id -> { cornice, def, nascosto }
  const aperti = new Map();
  //: I MODULI che sono stati chiusi apposta — col dock, con ⊠ o a voce. Non
  //: e' lo stesso insieme di «non aperti»: un modulo mai visto si apre
  //: entrando nel suo workspace, uno chiuso apposta no, o il dock direbbe
  //: «chiuso» su un pannello che ricompare da solo.
  const chiusiDaUtente = new Set();
  /* ⚠️ ADR-010 — questo NON e' piu' un workspace: e' un filtro.
   *
   * Prima si chiamava `corrente` e valeva 1..4, e decideva che cosa fosse
   * visibile: tre quarti dei pannelli erano sempre nascosti. Adesso vale
   * `null` — nessun filtro — oppure una categoria, e non nasconde niente:
   * evidenzia. La scrivania e' una sola. */
  let filtro = null;
  /* L'area contro cui le celle dichiarate sono state applicate l'ultima volta.
   *
   * Serve a rispondere a una domanda che prima non si poteva porre: **la
   * disposizione di adesso e' ancora quella dichiarata, o e' di qualcuno?**
   * Vedi `intatta()`. */
  let areaComposizione = null;
  let tuttoNascosto = false;
  let ultimoFuoco = null;
  const osservatori = new Set();

  const area = () => misuraArea();

  /* ── dalla cella ai pixel ────────────────────────────────────────────── */

  /* ⚠️ R88 — la cascata per categoria, e perche' senza non si vede niente.
   *
   * Le celle di `moduli.js` sono quattro piastrellature COMPLETE della stessa
   * griglia, una per categoria: nate quando le categorie erano pagine, e
   * ognuna doveva riempire il proprio schermo da sola.
   *
   * Aprendole tutte insieme (ADR-010) l'ultima copre le altre. Misurato
   * guardando lo scatto: dei quattordici pannelli se ne vedevano DUE — globo e
   * tavola periodica, che sono `[0,0,5,4]` e `[5,0,7,4]`, cioe' insieme la
   * griglia intera. Sarebbe stato peggio di quattro pagine: tre quarti
   * invisibili E irraggiungibili, perche' il filtro non alza niente.
   *
   * La correzione e' una CASCATA: ogni categoria scende e scala di un passo, e
   * la griglia si calcola su un'area gia' scontata della profondita' totale,
   * cosi' tutti restano dentro. Il passo e' `--s-4` = 32 px, che e' quanto
   * basta a lasciare scoperta la TESTA del pannello sotto — la testa e' la
   * maniglia, quindi ogni strato resta afferrabile.
   *
   * E' anche la forma del riferimento: `famiglia-a/01` non e' una
   * piastrellatura, sono carte che si coprono in parte.
   */
  const PROFONDITA = CATEGORIE.length - 1;

  function geometria(cella, a = area(), categoria = 1) {
    const [c, r, dc, dr] = cella;
    const gap = tokPx("--gap");
    const passo = tokPx("--s-4");
    const scostamento = (Number(categoria) - 1) * passo;
    a = {
      ...a,
      sinistra: a.sinistra + scostamento,
      alto: a.alto + scostamento,
      larghezza: a.larghezza - PROFONDITA * passo,
      altezza: a.altezza - PROFONDITA * passo,
    };
    const larghezzaCella = a.larghezza / COLONNE;
    const altezzaCella = a.altezza / RIGHE;
    // Ogni cella rientra di meta' spazio per lato: fra due pannelli vicini lo
    // spazio e' `--gap` intero, al bordo dello schermo la meta'. Un solo
    // numero, e resta un multiplo di 4 (§11.8).
    const m = gap / 2;
    return {
      x: Math.round(a.sinistra + c * larghezzaCella + m),
      y: Math.round(a.alto + r * altezzaCella + m),
      larghezza: Math.round(dc * larghezzaCella - gap),
      altezza: Math.round(dr * altezzaCella - gap),
    };
  }

  /* ── apertura e chiusura ─────────────────────────────────────────────── */

  async function apri(id) {
    const def = modulo(id);
    if (!def) return null;
    // ADR-010: non c'e' piu' un workspace in cui «portare». Aprire un pannello
    // lo apre, e basta — sulla scrivania, che e' una sola.
    chiusiDaUtente.delete(def.id);

    const gia = aperti.get(def.id);
    if (gia) {
      gia.cornice.box.show();
      gia.cornice.box.focus();
      gia.nascosto = false;
      annuncia();
      return gia.cornice;
    }

    const cornice = await creaCornice({
      componente: def.componente,
      geometria: geometria(def.cella, area(), def.categoria),
      // La FUNZIONE, non il valore: le zone d'aggancio e i limiti di WinBox
      // devono seguire la finestra, non la finestra di quando sono nati (R83).
      misuraArea: area,
      suChiusura: () => {
        aperti.delete(def.id);
        if (def.modulo) chiusiDaUtente.add(def.id);
        annuncia();
      },
      suFuoco: () => { ultimoFuoco = def.id; },
      // §26.10 punto 1. Ogni cambio di geometria lo dice; QUANTO SPESSO
      // arrivi al core lo decide `desk/layout.js` col proprio ritardo. Qui non
      // c'e' nessun freno di proposito: chi osserva vuole sapere che e'
      // successo, e mescolare l'evento col suo smorzamento significa non poter
      // piu' cambiare idea sul secondo senza toccare il primo.
      suGeometria: () => suDisposizione?.(disposizione()),
    });
    // Il DOM non diceva quale modulo fosse una finestra: `.winbox` sono tutte
    // uguali, e l'unico modo di riconoscerle era incrociare le geometrie.
    // Serve a `scripts/prova-gesti.mjs` per afferrare la testa di UN pannello,
    // e serve a chiunque debba guardare una scrivania e capirla.
    cornice.box.window.dataset.modulo = def.id;
    def.alimenta?.(cornice.pannello, bus);
    aperti.set(def.id, { cornice, def, nascosto: false });
    ultimoFuoco = def.id;
    annuncia();
    return cornice;
  }

  function chiudi(id) {
    const v = aperti.get(modulo(id)?.id);
    if (!v) return false;
    v.cornice.box.close();          // `onclose` toglie dalla mappa e annuncia
    return true;
  }

  /**
   * Il pulsante del dock. **Tre esiti, non due** (R89).
   *
   * ⚠️ Con quattro pagine un modulo aperto era sempre visibile, e «alterna»
   * poteva voler dire soltanto apri/chiudi. Con una scrivania sola i pannelli
   * si coprono: guardando lo scatto, di quattordici se ne leggevano nove e
   * gli altri stavano sotto. Premere il pulsante di un pannello **sepolto** e
   * vederlo sparire e' la cosa piu' sbagliata che il dock possa fare — l'utente
   * lo stava cercando, non chiudendo.
   *
   *   non aperto        si apre
   *   aperto e sotto    sale in cima e prende il fuoco
   *   aperto e in cima  si chiude
   *
   * E' il comportamento di qualunque barra delle applicazioni, ed e' anche
   * l'unico che conserva la proprieta' che il dock prometteva: premendo due
   * volte si torna dove si era.
   */
  async function alterna(id) {
    const def = modulo(id);
    const v = def && aperti.get(def.id);
    if (!v) return apri(id);
    if (!v.nascosto && inCima(v)) return chiudi(def.id);
    v.cornice.box.show();
    v.nascosto = false;
    v.cornice.box.focus();
    annuncia();
    return v.cornice;
  }

  /** Nessun altro pannello visibile sta piu' in alto di questo. */
  function inCima(v) {
    const z = geometriaDi(v.cornice).z;
    for (const altro of aperti.values()) {
      if (altro === v || altro.nascosto) continue;
      if (geometriaDi(altro.cornice).z > z) return false;
    }
    return true;
  }

  /* ── il filtro ───────────────────────────────────────────────────────── */

  /**
   * ADR-010: **evidenzia una categoria, non cambia pagina.**
   *
   * Prima questa funzione componeva e scomponeva: nascondeva i pannelli degli
   * altri tre workspace e creava quelli del nuovo. Adesso non tocca la
   * visibilita' di niente — dice solo di che cosa si sta parlando, e la barra
   * e il dock lo mostrano.
   *
   * Premere due volte la stessa categoria toglie il filtro: e' l'unico modo
   * per tornare a «tutto», e senza di esso un filtro acceso non si spegne piu'.
   */
  function vai(n) {
    const num = Number(n);
    if (!CATEGORIE.some((c) => c.n === num)) return;
    filtro = filtro === num ? null : num;
    annuncia();
  }

  /** Toglie il filtro, se c'e'. */
  function tutto() {
    filtro = null;
    annuncia();
  }

  /**
   * La scrivania al primo avvio, quando non c'e' un layout da rimettere.
   *
   * Ritorna quanti ne ha aperti, per il log: aprire tredici pannelli e' la
   * cosa piu' costosa che questo ambiente fa, e vale la pena poterla contare.
   */
  async function apriIniziale() {
    for (const def of composizioneIniziale()) {
      if (chiusiDaUtente.has(def.id)) continue;
      await apri(def.id);
    }
    // Da qui in poi la disposizione e' quella dichiarata, e `intatta()` puo'
    // accorgersi di quando smette di esserlo.
    areaComposizione = area();
    annuncia();
    return aperti.size;
  }

  /* ── le azioni di §13 ────────────────────────────────────────────────── */

  function nascondiTutto() {
    tuttoNascosto = !tuttoNascosto;
    for (const v of aperti.values()) {
      // ADR-010: su tutti. Con quattro pagine «nascondi tutto» voleva dire
      // «nascondi la pagina», che era gia' un quarto di tutto.
      if (tuttoNascosto) v.cornice.box.hide();
      else v.cornice.box.show();
      v.nascosto = tuttoNascosto;
    }
    annuncia();
  }

  /**
   * Rimette ogni pannello nella propria cella dichiarata — `Alt+T`.
   *
   * ⚠️ ADR-010 cambia che cosa SIGNIFICA questa funzione. La cella non e' piu'
   * la gabbia del pannello: e' la sua posizione INIZIALE, e da li' in poi il
   * pannello si sposta e si sovrappone. `affianca()` non e' quindi «rimetti
   * ordine», e' «ricomincia da capo»: un gesto esplicito che butta via la
   * disposizione dell'utente, ed e' per questo che il ridimensionamento della
   * finestra non lo chiama piu' (R82).
   */
  function affianca() {
    const a = area();
    areaComposizione = a;
    for (const v of aperti.values()) {
      if (v.nascosto) continue;
      const g = geometria(v.def.cella, a, v.def.categoria);
      v.cornice.massimizzata = false;
      v.cornice.box.maximize(false);
      v.cornice.box.resize(g.larghezza, g.altezza);
      v.cornice.box.move(g.x, g.y);
    }
  }

  function espandi(id = ultimoFuoco) {
    const v = aperti.get(id);
    if (!v) return;
    v.cornice.massimizzata = !v.cornice.massimizzata;
    v.cornice.box.maximize(v.cornice.massimizzata);
  }

  /* ── chi glielo chiede ───────────────────────────────────────────────── */

  /**
   * Gli intenti T0 di §13, che dalla Fase 3 non avevano nessuna strada verso
   * l'interfaccia. Arrivano dal core su `ui.intent`, con gli argomenti.
   */
  async function suIntento({ intento, args = {} }) {
    switch (intento) {
      case "open_panel": return apri(args.panel);
      case "close_panel": return chiudi(args.panel);
      case "hide_all": return nascondiTutto();
      case "tile_panels": return affianca();
      // ADR-010: l'intento resta nella grammatica e nel corpus di cento frasi
      // della Fase 3 — «vai al workspace tre» e' ancora una frase che qualcuno
      // dira'. Cio' che fa e' cambiato: filtra invece di cambiare pagina.
      case "switch_workspace": return vai(args.n);
      default: return undefined;      // allowlist: il resto non fa nulla
    }
  }

  /**
   * I quattro intenti di interfaccia di §14. **Due dei quattro non si possono
   * fare**, e non per pigrizia: `sposta_pannello` e `ruota_mesh` sono
   * manipolazioni CONTINUE — vogliono sapere di quanto, istante per istante —
   * e `gesture.intent` porta un intento discreto senza coordinate. Dichiarato
   * in `SEZIONE-13.md`; farli muovere di una quantita' inventata sarebbe
   * peggio che non farli.
   */
  function suGesture(msg) {
    if (msg?.tipo !== "ui") return;
    // ADR-010: fa girare il FILTRO fra le quattro categorie e il nulla. Con
    // le pagine faceva girare le pagine; adesso non nasconde niente, e il
    // giro comprende anche «nessun filtro» — cinque stati, non quattro, o non
    // ci sarebbe modo di tornare a vedere tutto con la sola mano.
    if (msg.intento === "cambia_workspace") return vai((filtro ?? 0) % 4 + 1);
    if (msg.intento === "espandi_pannello") return espandi();
    return undefined;
  }

  /* ── la disposizione, per il core ────────────────────────────────────── */

  /**
   * Dove sta ogni pannello aperto, piu' l'area in cui e' stato misurato.
   *
   * L'area viaggia insieme perche' senza non si distingue «fuori schermo» da
   * «schermo cambiato», e il ripristino deve saper riportare dentro invece di
   * scartare.
   */
  function disposizione() {
    const a = area();
    return {
      area: { larghezza: Math.round(a.larghezza), altezza: Math.round(a.altezza) },
      // ⚠️ Anche i NASCOSTI. `Alt+H` e' uno stato transitorio dell'ambiente,
      // non una decisione da ricordare: se si filtrassero via, premere Alt+H e
      // poi muovere un pannello cancellerebbe dal disco tutti gli altri.
      pannelli: [...aperti.entries()]
        .map(([id, v]) => ({ id, ...geometriaDi(v.cornice) })),
      scena: null,
    };
  }

  /**
   * Rimette i pannelli dove erano. Ritorna cosa ha fatto, per il log.
   *
   * ⚠️ **Un pannello che non esiste piu' in `moduli.js` si IGNORA.** Un
   * ambiente che non parte perche' ricorda una finestra che e' stata tolta dal
   * codice sarebbe rotto dal proprio passato: `apri()` ritorna `null` per un
   * id sconosciuto, ed e' esattamente il ramo che serve.
   *
   * ⚠️ **Il taglio dentro l'area si rifa' qui.** Il core l'ha gia' fatto
   * quando ha ricevuto, ma contro l'area di ALLORA: fra due avvii lo schermo
   * puo' essere cambiato, e il core non lo sa finche' nessuno glielo dice.
   */
  async function ripristina(layout) {
    const a = area();
    const messi = [];
    const ignorati = [];
    /* ⚠️ R86 — in ordine di `z` CRESCENTE, e non e' un dettaglio.
     *
     * Lo `z` si salvava e non si riapplicava mai: al riavvio la pila tornava
     * nell'ordine di creazione, e un pannello che l'utente aveva portato in
     * cima finiva sotto. §26.2 dice «nessun riordino automatico: una pila che
     * si riorganizza da sola e' la cosa che rende un ambiente inabitabile» —
     * e riaprire e' il momento in cui si riorganizzava da sola.
     *
     * Trovato dalla prova coi gesti veri, e in un modo indiretto: il
     * trascinamento non muoveva niente perche' la pressione finiva sul
     * pannello sbagliato, quello rimasto sopra.
     *
     * Si riordina col FUOCO invece che scrivendo `z-index`: e' il meccanismo
     * di WinBox, che tiene il proprio contatore. Impostare lo z a mano
     * significherebbe avere due contabilita' della stessa pila, ed e' gia'
     * successo con la geometria di ripristino (R85).
     */
    const ordinati = [...(layout?.pannelli ?? [])].sort((x, y) => (x.z ?? 0) - (y.z ?? 0));
    for (const p of ordinati) {
      const cornice = await apri(p.id);
      if (!cornice) { ignorati.push(p.id); continue; }
      applicaGeometria(cornice, dentroArea(p, a));
      cornice.box.focus();
      messi.push(p.id);
    }
    // Un layout ripristinato E' la disposizione di qualcuno: da adesso il
    // ridimensionamento adatta e non ricompone, anche se per caso coincidesse
    // con le celle dichiarate.
    if (messi.length) areaComposizione = null;
    annuncia();
    return { messi, ignorati };
  }

  /** Il minimo che deve restare a schermo perche' la testa sia afferrabile. */
  const MIN_VISIBILE = 80;

  function dentroArea(p, a) {
    const larghezza = Math.min(p.larghezza, Math.round(a.larghezza));
    const altezza = Math.min(p.altezza, Math.round(a.altezza));
    return {
      ...p,
      larghezza,
      altezza,
      x: Math.max(a.sinistra, Math.min(p.x, a.sinistra + a.larghezza - MIN_VISIBILE)),
      y: Math.max(a.alto, Math.min(p.y, a.alto + a.altezza - MIN_VISIBILE)),
    };
  }

  /**
   * La disposizione di adesso e' ancora esattamente quella dichiarata?
   *
   * ⚠️ E' la domanda che distingue i due significati di «la finestra e'
   * cambiata di dimensione», e non porla e' costato due difetti opposti:
   *
   *   R82  il ridimensionamento ricomponeva SEMPRE, e cancellava la
   *        disposizione dell'utente un secondo dopo l'avvio;
   *   R87  tolta la ricomposizione, al primo avvio i pannelli restavano
   *        disposti contro l'area di prima che la finestra si massimizzasse —
   *        quattordici pannelli piccoli in un angolo di uno schermo grande.
   *
   * La distinzione vera non e' «quando»: e' **di chi e' questa disposizione**.
   * Se nessuno l'ha toccata, ricomporre non toglie niente a nessuno. Se
   * qualcuno l'ha toccata, ricomporre e' cancellargliela.
   *
   * Si risponde confrontando, non ricordando: uno stato in piu' da tenere
   * aggiornato si sarebbe disallineato al primo ramo dimenticato.
   */
  function intatta() {
    if (areaComposizione === null) return false;
    for (const v of aperti.values()) {
      const g = geometria(v.def.cella, areaComposizione, v.def.categoria);
      const ora = geometriaDi(v.cornice);
      if (ora.x !== g.x || ora.y !== g.y ||
          ora.larghezza !== g.larghezza || ora.altezza !== g.altezza) return false;
    }
    return true;
  }

  /**
   * L'area e' cambiata: chi e' finito fuori rientra, gli altri restano.
   *
   * Non tocca chi e' gia' dentro — nemmeno di un pixel. Muovere anche i
   * pannelli a posto vorrebbe dire riscrivere la disposizione a ogni
   * ridimensionamento, e con la persistenza attiva significa salvarla.
   */
  function riadatta() {
    // Nessuno ha ancora disposto niente: si ricompone, e non si sta togliendo
    // niente a nessuno. E' il caso del primo avvio, quando la finestra si
    // assesta dopo che i pannelli sono gia' nati.
    if (intatta()) return affianca();

    const a = area();
    for (const v of aperti.values()) {
      // I limiti di WinBox si rifanno SEMPRE, anche a chi non si muove: senza,
      // `maximize()` userebbe l'area di prima (R83).
      aggiornaLimiti(v.cornice, a);
      if (v.nascosto || v.cornice.massimizzata) continue;
      const ora = geometriaDi(v.cornice);
      const dentro = dentroArea(ora, a);
      if (dentro.x === ora.x && dentro.y === ora.y &&
          dentro.larghezza === ora.larghezza && dentro.altezza === ora.altezza) continue;
      v.cornice.box.resize(dentro.larghezza, dentro.altezza).move(dentro.x, dentro.y);
    }
  }

  /* ── stato, per la barra e per il dock ───────────────────────────────── */

  function stato() {
    return {
      filtro,
      tuttoNascosto,
      aperti: [...aperti.keys()],
      fuoco: ultimoFuoco,
    };
  }

  function osserva(cb) { osservatori.add(cb); cb(stato()); return () => osservatori.delete(cb); }
  function annuncia() { const s = stato(); for (const cb of osservatori) cb(s); }

  /* ⚠️ R82 — qui c'era `window.addEventListener("resize", affianca)`.
   *
   * §13 poteva permetterselo: non c'era niente da conservare, e «l'area e'
   * cambiata» e «rimetti tutto nelle celle dichiarate» erano la stessa cosa.
   * Con la persistenza sono due cose diverse, e confonderle **cancella la
   * disposizione dell'utente** — misurato, non temuto: col ripristino
   * funzionante e questa riga al suo posto, un pannello rimesso a 500,300
   * tornava a 4,42 entro un secondo dall'avvio. La finestra si assesta dopo
   * il caricamento, il resize scatta, e `affianca()` disfaceva tutto.
   *
   * Adesso il ridimensionamento ADATTA: chi e' rimasto fuori rientra, chi era
   * dentro non si muove. Ricomporre resta un gesto ESPLICITO — `Alt+T`, che
   * chiama `affianca()` — ed e' giusto che lo sia: §26.2 dice «nessun
   * riordino automatico: una pila che si riorganizza da sola e' la cosa che
   * rende un ambiente inabitabile».
   */
  window.addEventListener("resize", riadatta);

  bus.su("ui.intent", suIntento);
  bus.su("gesture.intent", suGesture);
  // Il pannello gesture non e' in nessuna composizione: comparirebbe la spia
  // di §14 per una telecamera spenta. Si apre quando la telecamera parla.
  bus.su("gesture.frame", () => { if (!aperti.has("gesture")) apri("gesture"); });

  return {
    apri, chiudi, alterna, vai, tutto, apriIniziale,
    nascondiTutto, affianca, espandi,
    stato, osserva, geometria, disposizione, ripristina, riadatta,
    // L'area utile, coi bordi. `disposizione().area` ne porta solo larghezza e
    // altezza, perche' e' la forma che il core mette giu'; chi deve puntare a
    // un bordo — l'aggancio, e la prova che lo verifica — ha bisogno anche di
    // dove quel bordo sta.
    misura: area,
    get filtro() { return filtro; },
  };
}
