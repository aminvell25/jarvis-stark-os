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

import { COLONNE, RIGHE, WORKSPACE, composizione, modulo } from "./moduli.js";
import { creaCornice } from "./cornice.js";
import { tokPx } from "../style/tokens.js";

export const meta = { nome: "scrivania", versione: "1" };

export function creaScrivania({ bus, misuraArea }) {
  //: id -> { cornice, def, nascosto }
  const aperti = new Map();
  //: I MODULI che sono stati chiusi apposta — col dock, con ⊠ o a voce. Non
  //: e' lo stesso insieme di «non aperti»: un modulo mai visto si apre
  //: entrando nel suo workspace, uno chiuso apposta no, o il dock direbbe
  //: «chiuso» su un pannello che ricompare da solo.
  const chiusiDaUtente = new Set();
  let corrente = 1;
  let tuttoNascosto = false;
  let ultimoFuoco = null;
  const osservatori = new Set();

  const area = () => misuraArea();

  /* ── dalla cella ai pixel ────────────────────────────────────────────── */

  function geometria(cella, a = area()) {
    const [c, r, dc, dr] = cella;
    const gap = tokPx("--gap");
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

  async function apri(id, { porta = true } = {}) {
    const def = modulo(id);
    if (!def) return null;
    if (porta && def.ws !== corrente) await vai(def.ws);

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
      geometria: geometria(def.cella),
      area: area(),
      suChiusura: () => {
        aperti.delete(def.id);
        if (def.modulo) chiusiDaUtente.add(def.id);
        annuncia();
      },
      suFuoco: () => { ultimoFuoco = def.id; },
    });
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

  async function alterna(id) {
    return aperti.has(modulo(id)?.id) ? chiudi(id) : apri(id);
  }

  /* ── workspace ───────────────────────────────────────────────────────── */

  async function vai(n) {
    const num = Number(n);
    if (!WORKSPACE.some((w) => w.n === num)) return;
    corrente = num;
    tuttoNascosto = false;

    for (const v of aperti.values()) {
      if (v.def.ws === num) { v.cornice.box.show(); v.nascosto = false; }
      else v.cornice.box.hide();
    }

    // La composizione del workspace: cio' che manca si crea, cio' che e' stato
    // chiuso torna — ma solo se e' ARREDO. Un modulo chiuso resta chiuso: il
    // dock possiede il suo stato, e un modulo che tornasse da solo farebbe
    // mentire il dock.
    for (const def of composizione(num)) {
      if (aperti.has(def.id)) continue;
      if (def.modulo && chiusiDaUtente.has(def.id)) continue;
      await apri(def.id, { porta: false });
    }
    annuncia();
  }

  /* ── le azioni di §13 ────────────────────────────────────────────────── */

  function nascondiTutto() {
    tuttoNascosto = !tuttoNascosto;
    for (const v of aperti.values()) {
      if (v.def.ws !== corrente) continue;
      if (tuttoNascosto) v.cornice.box.hide();
      else v.cornice.box.show();
      v.nascosto = tuttoNascosto;
    }
    annuncia();
  }

  function affianca() {
    const a = area();
    for (const v of aperti.values()) {
      if (v.def.ws !== corrente || v.nascosto) continue;
      const g = geometria(v.def.cella, a);
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
    if (msg.intento === "cambia_workspace") return vai(corrente % 4 + 1);
    if (msg.intento === "espandi_pannello") return espandi();
    return undefined;
  }

  /* ── stato, per la barra e per il dock ───────────────────────────────── */

  function stato() {
    return {
      workspace: corrente,
      tuttoNascosto,
      aperti: [...aperti.keys()],
      fuoco: ultimoFuoco,
    };
  }

  function osserva(cb) { osservatori.add(cb); cb(stato()); return () => osservatori.delete(cb); }
  function annuncia() { const s = stato(); for (const cb of osservatori) cb(s); }

  // Il ridimensionamento della finestra ricompone: le celle sono in frazioni
  // dell'area, e l'area e' cambiata. Non e' un'animazione — e' la stessa
  // disposizione, misurata di nuovo.
  window.addEventListener("resize", affianca);

  bus.su("ui.intent", suIntento);
  bus.su("gesture.intent", suGesture);
  // Il pannello gesture non e' in nessuna composizione: comparirebbe la spia
  // di §14 per una telecamera spenta. Si apre quando la telecamera parla.
  bus.su("gesture.frame", () => { if (!aperti.has("gesture")) apri("gesture"); });

  return {
    apri, chiudi, alterna, vai, nascondiTutto, affianca, espandi,
    stato, osserva, geometria,
    get workspace() { return corrente; },
  };
}
