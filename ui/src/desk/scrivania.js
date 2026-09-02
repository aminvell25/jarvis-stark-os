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

import { dentroArea } from "./geometria-area.js";
import { CATEGORIE, COLONNE, RIGHE, SCENE, composizioneIniziale, modulo }
  from "./moduli.js";
import { aggiornaLimiti, applicaGeometria, creaCornice, geometriaDi }
  from "./cornice.js";
import { tokPx } from "../style/tokens.js";
import { apertura, SFALSAMENTO } from "../anim/panels.js";

export const meta = { nome: "scrivania", versione: "1" };

/**
 * `fondo` e' cio' che sta SOTTO i pannelli — icone libere e cartelle, §26.5 —
 * e arriva come funzione perche' nasce dopo la scrivania e cambia da solo. La
 * scrivania non sa che cosa sia un'icona: sa che la disposizione dell'ambiente
 * non e' fatta solo di finestre, e che chi la mette giu' la vuole intera.
 */
export function creaScrivania({ bus, misuraArea, suDisposizione,
                                fondo = () => ({ icone: [], cartelle: [] }) }) {
  //: id -> { cornice, def, nascosto }
  const aperti = new Map();
  //: I MODULI che sono stati chiusi apposta — col dock, con ⊠ o a voce. Non
  //: e' lo stesso insieme di «non aperti»: un modulo mai visto si apre
  //: entrando nel suo workspace, uno chiuso apposta no, o il dock direbbe
  //: «chiuso» su un pannello che ricompare da solo.
  const chiusiDaUtente = new Set();
  /* Il ritardo dell'apertura, che UNA SOLA funzione scrive: `applicaScena`.
   * Fuori da una scena vale zero — chi apre un pannello dal catalogo lo vuole
   * subito, e sfalsare un pannello solo vorrebbe dire farlo aspettare per
   * niente. */
  let ritardoApertura = 0;
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

  /* ── i moduli che non stanno in `moduli.js` (R94) ─────────────────────────
   *
   * `moduli.js` e' un registro STATICO, scritto a mano: e' giusto che lo sia,
   * perche' e' una decisione di composizione. Una cartella di §26.5 nasce
   * mentre il sistema gira, e non puo' stare li'.
   *
   * La strada scartata era una `apriCartella()` accanto ad `apri()`: sarebbe
   * stato un SECONDO modo di fare una finestra, e i due sarebbero divergiti al
   * primo comportamento aggiunto a uno solo — la geometria salvata, il
   * ripristino, `alterna`, il conteggio del dock. Invece si aggiunge una voce
   * al registro, e da li' in poi una cartella e' un pannello come gli altri.
   *
   * Si consulta PRIMA la mappa dinamica: un id dinamico non puo' coprire un
   * modulo dichiarato, perche' la sua forma — `cartella.N` — non e' un id che
   * `moduli.js` usi. */
  const dinamici = new Map();

  function def(id) {
    const k = String(id ?? "").toLowerCase();
    return dinamici.get(k) ?? modulo(k);
  }

  /** Aggiunge un modulo al volo. Ri-registrare lo stesso id lo SOSTITUISCE. */
  function registra(d) {
    dinamici.set(String(d.id), d);
    return d;
  }

  /** Lo toglie. Il pannello eventualmente aperto NON si chiude qui: chiudere
   *  e' una decisione di chi possiede la cosa, e questa e' solo l'anagrafe. */
  function dimentica(id) { return dinamici.delete(String(id)); }

  /* ── §26.6 — le scene ───────────────────────────────────────────────────
   *
   * Le predefinite stanno in `moduli.js` perche' la composizione di partenza
   * non puo' dipendere da un file di configurazione aggiornato; quelle scritte
   * a mano arrivano dal core con `ui.scene`. **A parita' di nome vince chi
   * l'ha scritta**: un predefinito che scavalca una decisione dell'utente e'
   * un predefinito rotto.
   */
  let scene = [...SCENE];
  let scenaIniziale = SCENE[0]?.nome ?? null;
  let scenaCorrente = null;
  //: id -> { cella, passi } con cui il pannello e' stato composto adesso.
  const composizione = new Map();

  function dichiaraScene(elenco, iniziale) {
    const perNome = new Map(SCENE.map((s) => [s.nome, s]));
    for (const s of elenco ?? []) {
      if (s?.nome && Array.isArray(s.pannelli)) perNome.set(s.nome, s);
    }
    scene = [...perNome.values()];
    if (iniziale && perNome.has(iniziale)) scenaIniziale = iniziale;
    annuncia();
    return scene;
  }

  const scenaDetta = (nome) => scene.find((s) => s.nome === String(nome ?? ""));

  /**
   * Applica una scena. Ritorna cosa ha fatto, per il log e per la verifica.
   *
   * ⚠️ **Cio' che non e' nella scena si NASCONDE, non si chiude.** Chiudere
   * costerebbe i dati — il core manda l'albero dei sorgenti, i fusi e
   * l'archivio una volta sola, a chi si collega — e soprattutto sarebbe
   * distruttivo: richiamare una scena e ritrovarsi senza il pannello su cui si
   * stava lavorando e' la cosa che rende un ambiente inabitabile. Nascosto si
   * riapre col catalogo e torna dov'era.
   *
   * ⚠️ **In ordine di `z` CRESCENTE**, con lo stesso meccanismo di
   * `ripristina()`: la pila si ordina col FUOCO, che e' il contatore di
   * WinBox, invece di scrivere `z-index` a mano. Due contabilita' della stessa
   * pila divergono, ed e' gia' successo (R85, R86).
   */
  async function applicaScena(nome) {
    const s = scenaDetta(nome);
    if (!s) return null;
    const a = area();
    const dentro = new Set(s.pannelli.map((p) => String(p.id)));

    for (const [id, v] of aperti) {
      if (dentro.has(id) || v.nascosto) continue;
      v.cornice.box.hide();
      v.nascosto = true;
    }

    const messi = [];
    const ignorati = [];
    let k = 0;
    for (const p of [...s.pannelli].sort((x, y) => (x.z ?? 0) - (y.z ?? 0))) {
      ritardoApertura = k++ * SFALSAMENTO;
      // La cella della SCENA, non quella dichiarata dal modulo, e senza
      // cascata: la composizione e' gia' fatta a mano.
      composizione.set(String(p.id),
        { cella: p.cella, cellaRidotta: p.cellaRidotta, passi: 0 });
      const cornice = await apri(p.id);
      if (!cornice) { composizione.delete(String(p.id)); ignorati.push(p.id); continue; }
      /* ⚠️ Anche per un pannello GIA' aperto. `apri()` legge cella e scalini
       * solo quando la cornice nasce; richiamare una scena su una scrivania
       * gia' composta non farebbe nascere niente, e `affianca()` avrebbe
       * continuato a rimettere i pannelli nella composizione precedente. */
      const v = aperti.get(String(p.id));
      if (v) { v.cella = p.cella; v.passi = 0; }
      const g = geometria(p.cella, a, 0);
      cornice.massimizzata = false;
      cornice.box.maximize(false);
      applicaGeometria(cornice, g);
      cornice.box.show();
      cornice.box.focus();
      messi.push(p.id);
    }
    tuttoNascosto = false;
    scenaCorrente = s.nome;
    ritardoApertura = 0;
    // Una scena E' una disposizione dichiarata: da qui `intatta()` puo'
    // accorgersi di quando smette di esserlo, e il ridimensionamento ricompone
    // invece di limitarsi ad adattare.
    areaComposizione = a;
    // E adesso che l'area c'e', i pannelli vuoti possono contrarsi:
    // `intatto()` ha finalmente un metro contro cui rispondere.
    for (const v of aperti.values()) v.applicaSuperficie?.();
    annuncia();
    return { scena: s.nome, messi, ignorati };
  }

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

  /**
   * `passi` e' quanti scalini di cascata: `def.categoria - 1` per un pannello
   * aperto da solo, **ZERO per un pannello di una scena**.
   *
   * ⚠️ E' la correzione della cascata, non la sua rimozione. Una scena e' una
   * composizione fatta a mano: le sue celle si sovrappongono di proposito, e
   * scalarle di categoria le sposterebbe fuori dalla composizione. La cascata
   * serve ancora a chi apre un pannello dal catalogo mentre una scena e' a
   * schermo — li' due celle identiche coinciderebbero, e uno dei due
   * sparirebbe esattamente sotto l'altro.
   */
  function geometria(cella, a = area(), passi = 0) {
    const [c, r, dc, dr] = cella;
    const gap = tokPx("--gap");
    const passo = tokPx("--s-4");
    const scostamento = Math.max(0, Number(passi) || 0) * passo;
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
    /* ⚠️ SI ARROTONDANO I BORDI, NON LA POSIZIONE E LA MISURA SEPARATAMENTE.
     *
     * La stesura precedente faceva `x = round(sinistra + c*cella + m)` e
     * `larghezza = round(dc*cella - gap)`: due arrotondamenti indipendenti
     * sulla stessa quota. Due pannelli adiacenti finivano cosi' a condividere
     * un bordo che dipende da come cadono DUE frazioni invece di una, e fra
     * loro poteva restare un pixel di troppo o di meno — mai in modo grave,
     * mai in modo verificabile, e diverso a ogni larghezza di finestra.
     *
     * Qui si calcolano i due BORDI e la misura si deriva. La proprieta' che
     * questo compra e' esatta e si dimostra: il bordo destro della cella c e'
     * `round(s + (c+dc)*cella - m)`, il bordo sinistro della cella successiva
     * e' `round(s + (c+dc)*cella + m)`, e fra i due c'e' sempre `2m = gap`
     * ESATTI, qualunque sia la parte frazionaria di `cella`. Con due
     * arrotondamenti indipendenti quella somma non e' garantita.
     *
     * Non e' il difetto che faceva fallire `affianca.ripristinata` — quello era
     * il criterio, e sta nel commit precedente. E' la stessa specie di
     * fragilita' trovata guardando quel difetto: una quota che si compone da
     * due numeri arrotondati a parte. */
    const x1 = Math.round(a.sinistra + c * larghezzaCella + m);
    const x2 = Math.round(a.sinistra + (c + dc) * larghezzaCella - m);
    const y1 = Math.round(a.alto + r * altezzaCella + m);
    const y2 = Math.round(a.alto + (r + dr) * altezzaCella - m);
    return { x: x1, y: y1, larghezza: x2 - x1, altezza: y2 - y1 };
  }

  /* ── apertura e chiusura ─────────────────────────────────────────────── */

  /* ── §11.6 regola 3: un pannello che ha poco da dire si RIMPICCIOLISCE ──
   *
   * «Se un pannello ha poco da dire, lo rimpicciolisca — non lo riempia di
   * spazio.» `DIVARIO-PREMIUM.md` §5 lo chiama «la cosa che piu' fa sembrare
   * finto l'insieme, piu' di qualunque scelta cromatica», e chiede che la
   * regola stia in `moduli.js`. Ci sta: e' `cellaRidotta`.
   *
   * ⚠️ IL PANNELLO NON DECIDE QUANTO E' GRANDE, e non decide nemmeno di
   * contrarsi. Dichiara di essere VUOTO — `data-stato="vuoto"`, che ciambella,
   * tabella, news e source scrivono gia' da sempre — e la scrivania decide che
   * cosa farne. Una verita' sola, e sta gia' dove stava: aggiungere un
   * `superficie()` accanto a `data-stato` sarebbe stata una seconda
   * dichiarazione della stessa cosa, cioe' il modo esatto in cui le due si
   * slegano.
   *
   * ⚠️ E si contrae solo un pannello INTATTO. Un pannello che l'utente ha
   * spostato o ridimensionato a mano e' suo: rimpicciolirlo perche' si e'
   * svuotato sarebbe la stessa cosa di R82 — una regola dell'ambiente che
   * cancella una decisione della persona un secondo dopo che l'ha presa. */
  function osservaSuperficie(v) {
    const radice = v.cornice.pannello?.radice;
    if (!radice) return;
    /* ⚠️ LA CELLA RIDOTTA VIENE DALLA STESSA FONTE DELLA CELLA PIENA, e non da
     * una qualunque.
     *
     * La prima stesura faceva `composizione.get(id)?.cellaRidotta ??
     * def.cellaRidotta`: se una scena dichiarava la cella piena e NON quella
     * ridotta, il ripiego prendeva quella del MODULO — che appartiene a
     * un'altra composizione. Misurato: `news` finiva a [964, 36, 232, 679],
     * cioe' una colonna alta tutta la scrivania in un punto che nessuno aveva
     * chiesto, e L>60 crollava a 22,75 %.
     *
     * Una cella piena e una ridotta prese da due posti diversi non sono due
     * dimensioni della stessa cosa: sono due layout mescolati. Se chi ha
     * composto la scena non ha dichiarato la ridotta, la risposta e' «non si
     * contrae», non «si contrae altrove». */
    const dallaScena = composizione.get(v.def.id);
    const ridotta = dallaScena ? dallaScena.cellaRidotta : v.def.cellaRidotta;
    if (!ridotta) return;
    const piena = v.cella;
    /* `appenaNato`: al momento della nascita il pannello non puo' essere stato
     * toccato da nessuno, e chiedere `intatto()` li' non ha senso — anzi fa
     * danno, perche' `areaComposizione` puo' non coincidere con `area()` per
     * uno scarto di arrotondamento e la contrazione non parte mai. Misurato:
     * aprendo `browser` dal catalogo il pannello nasceva a 952 px, cioe' la
     * cella piena, con `data-stato="vuoto"` gia' scritto. */
    const applica = ({ appenaNato = false } = {}) => {
      const vuoto = radice.dataset.stato === "vuoto";
      const voluta = vuoto ? ridotta : piena;
      if (String(voluta) === String(v.cella)) return;
      if (!appenaNato && !intatto(v)) return;        // l'ha toccato l'utente
      v.cella = voluta;
      const g = geometria(voluta, areaComposizione ?? area(), v.passi);
      applicaGeometria(v.cornice, g);
    };
    new MutationObserver(applica).observe(radice, {
      attributes: true, attributeFilter: ["data-stato"],
    });
    /* ⚠️ E si tiene la funzione, perche' l'osservatore da solo NON BASTA.
     *
     * Un pannello nasce gia' vuoto — `news.js` scrive `data-stato="vuoto"`
     * mentre costruisce il DOM — quindi non c'e' nessuna mutazione da
     * osservare. E la chiamata immediata qui sotto cade quando
     * `areaComposizione` e' ancora `null`, cioe' prima che la scena finisca:
     * `intatto()` risponde `false` e non fa niente.
     * Misurato: al primo giro il rettangolo di news restava 472 px, cioe' la
     * cella piena, mentre la contrazione era scritta e sembrava attiva.
     * Percio' `applicaScena()` la richiama quando l'area c'e'. */
    v.applicaSuperficie = applica;
    applica({ appenaNato: true });
  }

  async function apri(id) {
    const d = def(id);
    if (!d) return null;
    // ADR-010: non c'e' piu' un workspace in cui «portare». Aprire un pannello
    // lo apre, e basta — sulla scrivania, che e' una sola.
    chiusiDaUtente.delete(d.id);

    const gia = aperti.get(d.id);
    if (gia) {
      gia.cornice.box.show();
      gia.cornice.box.focus();
      gia.nascosto = false;
      annuncia();
      return gia.cornice;
    }

    // Cella e scalini con cui questo pannello e' stato composto. Si ricordano
    // perche' `affianca()` e `intatta()` devono poterli rifare identici: una
    // scena e un'apertura dal catalogo compongono con numeri diversi, e
    // dedurli dopo vorrebbe dire indovinare da dove veniva il pannello.
    const cella = composizione.get(d.id)?.cella ?? d.cella;
    const passi = composizione.get(d.id)?.passi ?? (Number(d.categoria) || 1) - 1;

    const cornice = await creaCornice({
      componente: d.componente,
      geometria: geometria(cella, area(), passi),
      // Cio' che il componente vuole sapere alla nascita e non e' un dato.
      // Oggi lo usa solo il pannello cartella di §26.5.
      opzioni: d.opzioni,
      // La FUNZIONE, non il valore: le zone d'aggancio e i limiti di WinBox
      // devono seguire la finestra, non la finestra di quando sono nati (R83).
      misuraArea: area,
      suChiusura: () => {
        aperti.delete(d.id);
        if (d.modulo) chiusiDaUtente.add(d.id);
        // Un modulo dinamico ha un proprietario, e vuole saperlo: una
        // cartella chiusa non e' piu' «aperta» nel layout, e il suo pannello
        // non va piu' aggiornato. Il registro statico non ne ha bisogno —
        // nessuno possiede il globo.
        d.suChiusura?.();
        annuncia();
      },
      suFuoco: () => { ultimoFuoco = d.id; },
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
    cornice.box.window.dataset.modulo = d.id;
    d.alimenta?.(cornice.pannello, bus);
    const voce = { cornice, def: d, nascosto: false, cella, passi };
    aperti.set(d.id, voce);
    osservaSuperficie(voce);
    /* §10.3: il pannello si SCOPRE. La causa e' che qualcuno l'ha aperto —
     * classe 1 di §10.6, comincia a un evento e finisce da sola.
     * `ritardoApertura` lo mette `applicaScena`: sei pannelli che arrivano
     * tutti nello stesso fotogramma non sono una composizione che si compone,
     * sono un lampo. §10.4 sanziona gia' `stagger` per il dock. */
    apertura(cornice.box.window, ritardoApertura);
    ultimoFuoco = d.id;
    annuncia();
    return cornice;
  }

  function chiudi(id) {
    const v = aperti.get(def(id)?.id);
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
    const d = def(id);
    const v = d && aperti.get(d.id);
    if (!v) return apri(id);
    if (!v.nascosto && inCima(v)) return chiudi(d.id);
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
   * ⚠️ **E' una SCENA, non «apri tutto».** Aprire tutto non e' comporre: le
   * celle di `moduli.js` sono quattro piastrellature complete della stessa
   * griglia, e aprirle insieme produce una cascata diagonale in cui di
   * quattordici pannelli se ne leggono due. Misurato sullo scatto, non temuto.
   *
   * Ritorna quanti ne ha aperti, per il log.
   */
  async function apriIniziale() {
    const esito = await applicaScena(scenaIniziale);
    if (!esito) {
      // Nessuna scena: si torna al comportamento di prima. Non deve succedere
      // — `moduli.js` ne dichiara una — ma un ambiente che non apre niente
      // perche' manca una riga di configurazione sarebbe peggio di una
      // cascata.
      for (const def of composizioneIniziale()) {
        if (chiusiDaUtente.has(def.id)) continue;
        await apri(def.id);
      }
      areaComposizione = area();
      annuncia();
    }
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
    /* ⚠️ **E lo si RIFERISCE al core**, che prima non lo sapeva.
     *
     * `nascondiTutto` cambiava `v.nascosto` e chiamava `annuncia()`, che parla
     * alla scrivania e non al core: il file del layout restava con
     * `nascosto: false` su tutti. Da ADR-013 quel campo decide se un pannello
     * e' un muro per la composizione — misurato attraversando il confine il 30
     * agosto: «nascondi tutto» sgombrava lo schermo, il core non se ne
     * accorgeva, e la superficie veniva rifiutata per mancanza di spazio.
     *
     * ⚠️ Residuo dichiarato: `nascosto` finisce sul disco e `ripristina()` non
     * lo riapplica, quindi un pannello nascosto alla chiusura torna visibile
     * al riavvio e il file lo dice nascosto finche' la scrivania non riferisce
     * di nuovo. `Alt+H` resta uno stato di sessione, come dice §26.10. */
    suDisposizione?.(disposizione());
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
      const g = geometria(v.cella, a, v.passi);
      v.cornice.massimizzata = false;
      v.cornice.box.maximize(false);
      applicaGeometria(v.cornice, g);   // il minimo dichiarato vale anche qui
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
      // §26.6 — «Voce: frase di wake -> scene:briefing». Il core traduce la
      // frase in un intento; qui si applica la scena DICHIARATA che porta quel
      // nome, e se non c'e' non succede niente: JARVIS richiama scene
      // dichiarate, non ne inventa.
      case "scene": return applicaScena(args.nome ?? args.scena);
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
      /* ⚠️ Anche SINISTRA e ALTO, e senza erano meta' area.
         Pannelli e icone sono in coordinate di FINESTRA; larghezza e altezza
         descrivono il PAVIMENTO. Il core tagliava contro [0, altezza - minimo],
         cioe' una banda traslata in su di quanto e' alta la barra: ammetteva
         una posizione dentro la barra e ne spostava una buona in fondo al
         pavimento. Il difetto si e' visto quando il dock e' cresciuto di otto
         pixel — vedi core/layout.py::adatta. */
      area: {
        sinistra: Math.round(a.sinistra),
        alto: Math.round(a.alto),
        larghezza: Math.round(a.larghezza),
        altezza: Math.round(a.altezza),
      },
      // ⚠️ Anche i NASCOSTI. `Alt+H` e' uno stato transitorio dell'ambiente,
      // non una decisione da ricordare: se si filtrassero via, premere Alt+H e
      // poi muovere un pannello cancellerebbe dal disco tutti gli altri.
      // ⚠️ `nascosto` viaggia, e i nascosti restano nell'elenco: il core ha
      // bisogno di sapere che ci sono (o li cancellerebbe dal disco) E che non
      // si vedono (o la composizione di ADR-013 li conta come muri). Due fatti
      // diversi, due campi.
      pannelli: [...aperti.entries()]
        .map(([id, v]) => ({ id, ...geometriaDi(v.cornice),
                             nascosto: !!v.nascosto })),
      // §26.5. Vengono da fuori perche' la scrivania non possiede il fondo, e
      // vanno QUI perche' quello che si mette giu' dev'essere UNO stato: due
      // messaggi separati potrebbero arrivare disallineati, e al riavvio si
      // vedrebbe una cartella senza le icone che conteneva.
      ...fondo(),
      // §26.6 — quale composizione e' a schermo. Il campo esisteva gia' nello
      // schema del core e valeva sempre `null`: adesso ha un produttore.
      scena: scenaCorrente,
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
      /* ⚠️ **E si rispetta `nascosto`**, che prima non esisteva.
       *
       * Da ADR-013 il layout porta anche quali pannelli non si vedono, e una
       * composizione li tiene (regola 1: non si toccano). Senza questa riga
       * `ripristina()` li **riapriva tutti**: il Signore diceva «nascondi
       * tutto», chiedeva una superficie, e si ritrovava i sei pannelli di
       * prima sopra i tre nuovi. Misurato attraversando il confine il 30
       * agosto — cinque sovrapposizioni, tutte fra un pannello composto e uno
       * che era stato nascosto.
       *
       * Il fuoco si da' PRIMA di nascondere: serve a rimettere la pila
       * nell'ordine di `z` (R86), e vale anche per chi non si vede. */
      const v = aperti.get(p.id);
      if (v && p.nascosto) { v.cornice.box.hide(); v.nascosto = true; }
      messi.push(p.id);
    }
    // Un layout ripristinato E' la disposizione di qualcuno: da adesso il
    // ridimensionamento adatta e non ricompone, anche se per caso coincidesse
    // con le celle dichiarate.
    if (messi.length) areaComposizione = null;
    annuncia();
    return { messi, ignorati };
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
  /** Un pannello e' INTATTO se sta ancora dove la composizione l'ha messo.
   *
   * Serve per pannello e non solo per l'insieme: la contrazione di §26/§11.6
   * regola 3 deve poter rimpicciolire UN pannello vuoto senza chiedere che
   * nessun altro sia stato toccato. Se l'utente l'ha spostato o ridimensionato
   * a mano, quel pannello non si tocca — e questa e' la riga che lo impedisce.
   */
  /* ⚠️ L'AREA DI RIFERIMENTO E' UN PARAMETRO, e le due domande sono diverse.
   *
   * `intatta()` chiede «la COMPOSIZIONE e' ancora come e' stata composta», e il
   * metro giusto e' l'area di allora — `areaComposizione`.
   * `intatto(v)` chiede «questo pannello l'ha toccato l'utente», e il metro
   * giusto e' l'area di ADESSO: dopo un ridimensionamento della finestra i
   * pannelli sono stati riadattati, e confrontarli con l'area di prima
   * risponderebbe «toccati» su tutti.
   * Misurato: col metro sbagliato un pannello contratto non tornava mai pieno
   * — `browser` restava a 472 px anche con `data-stato="pieno"`. */
  function intatto(v, rif = area()) {
    if (!rif) return false;
    const g = geometria(v.cella, rif, v.passi);
    const ora = geometriaDi(v.cornice);
    return ora.x === g.x && ora.y === g.y &&
           ora.larghezza === g.larghezza && ora.altezza === g.altezza;
  }

  function intatta() {
    if (areaComposizione === null) return false;
    for (const v of aperti.values()) if (!intatto(v, areaComposizione)) return false;
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
      /* ⚠️ `applicaGeometria` e non `box.resize` diretto, e la ragione e' la
         stessa di sempre: due scrittori della stessa verita' divergono.
         Questa riga scriveva la geometria SENZA passare dal minimo dichiarato,
         quindi ogni ridimensionamento della finestra disfaceva quello che il
         ripristino aveva appena aggiustato. Misurato: telemetria ripristinata
         a 550 px tornava a 485 al primo `resize`, e debordava di 65. */
      applicaGeometria(v.cornice, dentro);
    }
  }

  /* ── stato, per la barra e per il dock ───────────────────────────────── */

  function stato() {
    return {
      filtro,
      tuttoNascosto,
      aperti: [...aperti.keys()],
      fuoco: ultimoFuoco,
      // §26.6: la linguetta SCENE del catalogo elenca queste, e la barra dice
      // qual e' quella a schermo.
      scene: scene.map((s) => ({ nome: s.nome, descrizione: s.descrizione ?? "" })),
      scena: scenaCorrente,
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
    // §26.5 — un modulo che nasce mentre il sistema gira (R94).
    registra, dimentica,
    // §26.6 — le composizioni dichiarate.
    scena: applicaScena, dichiaraScene,
    get scene() { return scene; },
    get scenaCorrente() { return scenaCorrente; },
    stato, osserva, geometria, disposizione, ripristina, riadatta,
    // L'area utile, coi bordi. `disposizione().area` ne porta solo larghezza e
    // altezza, perche' e' la forma che il core mette giu'; chi deve puntare a
    // un bordo — l'aggancio, e la prova che lo verifica — ha bisogno anche di
    // dove quel bordo sta.
    misura: area,
    get filtro() { return filtro; },
  };
}
