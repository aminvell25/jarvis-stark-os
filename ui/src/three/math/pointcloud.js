/* Nuvola di punti sferica — SPEC §17.4 ①, riferimento famiglia-a/06 «SERVER TRACE».
 *
 * ── L'inversione che quasi tutti sbagliano ─────────────────────────────────
 * Campionare theta e phi uniformemente addensa ai poli, perche' i paralleli
 * vicini al polo sono corti e ricevono lo stesso numero di punti dell'equatore.
 * L'inversione `phi = acos(2u - 1)` distribuisce per AREA. E' il pezzo di
 * matematica che vale la sezione, e §17.4 la scrive per esteso.
 *
 * ── Dove mi allontano da §17.4, e perche' ──────────────────────────────────
 * §17.4 prende `u` da `Math.random()`, e §11.10 regola 4 lo concede: «tranne
 * le nuvole di punti, dove la casualita' e' la specifica». Ma §13 mette in
 * Fase 5 il modulo «Core sorgente — file reali del progetto», e allora la
 * nuvola puo' essere qualcosa di meglio di una forma: una MAPPA.
 *
 * Qui `u` viene dall'hash del percorso del file. Stessa distribuzione uniforme,
 * stessa inversione, ma:
 *   — ogni punto e' un file vero, che si puo' nominare;
 *   — la posizione e' stabile fra un render e l'altro, quindi un file che si
 *     sposta nella nuvola si e' spostato DAVVERO, e non e' rumore.
 *
 * E la latitudine non e' casuale: ogni cartella di primo livello occupa una
 * FASCIA, di area proporzionale a quanti file contiene. Cosi' la densita'
 * resta uniforme su tutta la sfera — l'area per file e' la stessa ovunque — e
 * insieme si legge la forma del progetto: una fascia larga e' un sottosistema
 * grande. Una nuvola casuale sarebbe stata decorazione con l'aspetto di un
 * dato, cioe' esattamente cio' che §11.9 vieta.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";

const TAU = Math.PI * 2;

/** FNV-1a a 32 bit. Deterministico, veloce, e senza dipendenze.
 *
 * Non e' crittografia e non deve esserlo: serve solo che due percorsi diversi
 * finiscano quasi sempre in posti diversi, e che lo stesso percorso finisca
 * sempre nello stesso posto.
 */
export function hash32(testo, seme = 0x811c9dc5) {
  let h = seme >>> 0;
  for (let i = 0; i < testo.length; i++) {
    h ^= testo.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** L'hash portato in [0, 1). */
const unita = (testo, seme) => hash32(testo, seme) / 0x100000000;

export class PointCloud extends ParametricComponent {
  /**
   * @param {object} p       parametri geometrici
   * @param {{path:string, bytes:number}[]} elenco  i file veri
   *
   * L'elenco NON sta nei parametri: la tabella dei parametri di §11.10 deve
   * restare leggibile in una schermata, e millecinquecento percorsi la
   * renderebbero illeggibile senza aggiungere nulla. I parametri descrivono
   * la FORMA; l'elenco e' il contenuto.
   */
  constructor(p = {}, elenco = []) {
    const radius = p.radius ?? 200;
    const flattenY = p.flattenY ?? 0.45;
    super(
      { radius, flattenY, count: elenco.length },
      {
        name: p.name ?? "point-cloud",
        version: "v1",
        dimensioni: 3,
        bbox: { x: 2 * radius, y: 2 * radius * flattenY, z: 2 * radius },
        // Un campione discreto di una superficie continua non tocca i propri
        // estremi: con qualche centinaio di punti il massimo |x| resta sotto R
        // di circa 2/N. La tolleranza e' dichiarata qui, con il suo perche',
        // invece di essere aggirata dichiarando un bbox misurato.
        bboxTolleranza: 0.05,
      }
    );
    if (elenco.length < 8)
      throw new Error(`nuvola con ${elenco.length} file: troppo pochi per una distribuzione`);
    this.elenco = elenco;
    this._fasce = fasce(elenco);
  }

  /** Le fasce di latitudine, una per cartella di primo livello. */
  get fasce() { return this._fasce; }

  build() {
    const { radius, flattenY } = this.params;
    const a = new Float32Array(this.elenco.length * 3);

    for (const [i, f] of this.elenco.entries()) {
      const fascia = this._fasce.get(radice(f.path));
      // u dentro la fascia, non su tutta la sfera: cos(phi) e' la variabile
      // uniforme per area, quindi si interpola LI', non su phi.
      const u = fascia.cosDa + (fascia.cosA - fascia.cosDa) * unita(f.path, 0x811c9dc5);
      const phi = Math.acos(Math.min(1, Math.max(-1, u)));   // ◄ inversione §17.4
      const theta = TAU * unita(f.path, 0x9e3779b1);

      a[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      a[i * 3 + 1] = radius * Math.cos(phi) * flattenY;
      a[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);
    }

    return new Geometria(a, [new Gruppo(0, this.elenco.length, { ruolo: "punti" })]);
  }

  /** Equatore e meridiano — §11.10 regola 3.
   *
   * Senza, la nuvola e' una macchia: non si capisce dove sia l'asse ne' quanto
   * sia schiacciata. Con, si legge come un oggetto orientato.
   */
  constructionLines() {
    const { radius, flattenY } = this.params;
    const seg = this.segmentsFor(radius);
    const punti = [];
    const gruppi = [];

    let p = punti.length / 3;
    for (let i = 0; i < seg; i++) {
      const t = (i / seg) * TAU;
      punti.push(Math.cos(t) * radius, 0, Math.sin(t) * radius);
    }
    gruppi.push(new Gruppo(p, seg, { chiuso: true, ruolo: "costruzione" }));

    p = punti.length / 3;
    for (let i = 0; i < seg; i++) {
      const t = (i / seg) * TAU;
      punti.push(Math.cos(t) * radius, Math.sin(t) * radius * flattenY, 0);
    }
    gruppi.push(new Gruppo(p, seg, { chiuso: true, ruolo: "costruzione" }));

    return new Geometria(new Float32Array(punti), gruppi);
  }
}

/** La cartella di primo livello di un percorso. */
export function radice(percorso) {
  const i = percorso.indexOf("/");
  return i === -1 ? "." : percorso.slice(0, i);
}

/** Fasce di cos(phi) proporzionali al numero di file: area per file costante.
 *
 * Ordinate per nome e non per dimensione: l'ordine deve essere stabile, o
 * aggiungere un file in `docs/` sposterebbe tutto `core/` da un'altra parte.
 */
export function fasce(elenco) {
  const conteggi = new Map();
  for (const f of elenco) {
    const r = radice(f.path);
    conteggi.set(r, (conteggi.get(r) ?? 0) + 1);
  }
  const totale = elenco.length;
  const fuori = new Map();
  let cursore = 1; // cos(phi) va da +1 (polo nord) a -1 (polo sud)
  for (const nome of [...conteggi.keys()].sort()) {
    const quota = (conteggi.get(nome) / totale) * 2;
    fuori.set(nome, {
      nome,
      conteggio: conteggi.get(nome),
      cosDa: cursore,
      cosA: cursore - quota,
    });
    cursore -= quota;
  }
  return fuori;
}
