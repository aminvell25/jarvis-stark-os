/* Quadrante graduato dell'HUD — SPEC §11.10, riferimento in design-reference.
 *
 * ## Perché UN componente e non otto
 *
 * Gli strati L1, L2, L4, L7 del riferimento sono la stessa cosa con parametri
 * diversi: uno o più cerchi concentrici, tacche a 1/N di giro, archi parziali,
 * tratteggi. Otto componenti sarebbero otto tabelle di parametri che dicono la
 * stessa cosa, otto `build()` da tenere allineati e otto occasioni di
 * divergere.
 *
 * `ReactorRing` resta per ciò che sa fare meglio — la fascia larga con un varco
 * netto e le tacche dentro (L3, L6) — e questo copre il resto. Due componenti,
 * non otto e non uno solo che fa tutto male.
 *
 * ## L'invariante 22 al completo
 *
 *   1. parametri con unità (unità di viewBox), mai numeri magici in build()
 *   2. densità dalla curvatura via `segmentsFor()`  <- qui sotto, per OGNI cerchio
 *   3. linee di costruzione preservate              <- gli assi cardinali
 *   4. asimmetria progettata, non casuale           <- gli archi parziali sono parametri
 *   5. Float32Array                                 <- Geometria lo impone
 *   6. massimo due materiali                        <- linea + costruzione
 *   7. bounding box dichiarato e verificato         <- dal raggio massimo
 *
 * ⚠️ La densità viene dal raggio del SINGOLO cerchio, non dal massimo dello
 * strato. Un cerchio da r=127 e uno da r=216 hanno curvature diverse, e dare a
 * entrambi i segmenti del più grande spreca vertici sul piccolo mentre darli
 * del più piccolo poligonalizza il grande. È la regola 2 presa alla lettera, e
 * si vede: un cerchio a 32 segmenti fissi è la firma del generato male.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";

const TAU = Math.PI * 2;

export class HudQuadrante extends ParametricComponent {
  /**
   * @param {object} p
   * @param {number[]} p.raggi        i cerchi concentrici, in unità di viewBox
   * @param {object}  [p.tacche]      {su, quante, lunghe} — graduazioni a 1/N
   * @param {object}  [p.tratteggio]  {su, dash:[on, off]} — traccia interrotta
   * @param {object[]}[p.archiParziali] [{su, da, ampiezza}] in radianti
   * @param {object}  [p.varco]       {da, ampiezza} — l'interruzione del cerchio INTERNO
   */
  constructor(p = {}) {
    const raggi = p.raggi ?? [100];
    // La fascia può stare più in fuori dei cerchi: il bounding box lo sa.
    const rMax = Math.max(...raggi, p.fascia?.su ?? 0);
    super(
      {
        // I raggi non stanno nei parametri come array: §11.10 vuole una
        // tabella leggibile, e un array di sei numeri lo è. Ma il gate legge
        // `Object.keys(params).length`, e un componente senza parametri non
        // passa: si dichiarano anche le grandezze derivate, che sono quelle
        // che il bounding box usa.
        raggioMax: rMax,
        raggioMin: Math.min(...raggi),
        cerchi: raggi.length,
        tacche: p.tacche?.quante ?? 0,
        tacchePiu: p.tacche?.lunghe ?? 0,
        archi: (p.archiParziali ?? []).length,
      },
      {
        name: p.name ?? "hud-quadrante",
        version: "v1",
        dimensioni: 2,
        // Dal PARAMETRO, non misurato dai vertici: se lo derivassi dal ciclo
        // di build() il gate verificherebbe il codice contro se stesso.
        bbox: { x: 2 * rMax, y: 2 * rMax, z: 0 },
      }
    );
    this.raggi = [...raggi];
    this.tacche = p.tacche ?? null;
    this.tratteggio = p.tratteggio ?? null;
    this.archiParziali = p.archiParziali ?? [];
    /* ⚠️ IL VARCO STA SUL CERCHIO INTERNO, SEMPRE, e non è una preferenza di
       composizione: è ciò che tiene vero il bounding box dichiarato.
       Un varco sul cerchio ESTERNO gli toglierebbe un punto cardinale — quello
       di L2 cade a 4,45-4,87 rad e inghiotte 3π/2 — e l'ingombro non varrebbe
       più 2R su entrambi gli assi. Il gate lo direbbe, ma parlando di bounding
       box invece che di composizione: cioè nel posto sbagliato.
       Nel riferimento il varco di L2 sta in basso, dove passa la waveform, ed è
       il cerchio interno quello che l'onda attraversa. */
    this.varco = p.varco ?? null;
    /* La fascia: {su, spessore, dash} oppure {su, spessore, segmenti}.
       È il pezzo che il riferimento chiama «anello segmentato» (L3) e
       «quadrante vetro» (L6), e non è un tratto spesso: è una SUPERFICIE. */
    this.fascia = p.fascia ?? null;

    if (this.tacche && !raggi.includes(this.tacche.su))
      throw new Error(
        `le tacche stanno su r=${this.tacche.su}, che non è fra i cerchi ` +
        `[${raggi}]: una graduazione senza il proprio cerchio è frangia`
      );
    if (this.tacche && this.tacche.lunghe >= this.tacche.su)
      throw new Error("le tacche sono più lunghe del proprio raggio");
    for (const a of this.archiParziali) {
      if (!raggi.includes(a.su))
        throw new Error(`arco parziale su r=${a.su}, che non è fra i cerchi`);
      if (a.ampiezza <= 0 || a.ampiezza >= TAU)
        throw new Error(`ampiezza d'arco fuori scala: ${a.ampiezza} rad`);
    }
  }

  /** Un cerchio chiuso, o un arco. `da`/`ampiezza` in radianti. */
  _arco(punti, gruppi, raggio, da = 0, ampiezza = TAU, ruolo = "linea") {
    const chiuso = ampiezza >= TAU - 1e-9;
    const seg = this.segmentsFor(raggio, ampiezza);   // ◄ regola 2, per cerchio
    const p0 = punti.length / 3;
    const n = chiuso ? seg : seg + 1;
    for (let i = 0; i < n; i++) {
      const a = da + (i / seg) * ampiezza;
      punti.push(Math.cos(a) * raggio, Math.sin(a) * raggio, 0);
    }
    gruppi.push(new Gruppo(p0, n, { chiuso, ruolo }));
  }

  /* ⚠️ IL DASH SI ADATTA ALLA CIRCONFERENZA, e non è pedanteria.
   *
   * Il riferimento dà per L3 `dasharray "42 14 8 14"`, cioè un motivo lungo 78
   * unità. La circonferenza a r=112 è 703,7: **9,02 motivi**. Lasciato così, il
   * motivo non chiude — l'ultimo segmento si accavalla al primo, e in un anello
   * che ruota quella giuntura passa davanti agli occhi ogni giro.
   *
   * Si tiene il RAPPORTO fra i tratti — che è ciò che si vede — e si scala il
   * passo perché i motivi entrino un numero intero di volte. A 9 motivi il
   * passo diventa 78,2 invece di 78: uno scarto dello 0,3 %, invisibile, in
   * cambio di una giuntura che non c'è.
   */
  _segmentiDiFascia() {
    const f = this.fascia;
    if (f.segmenti) return f.segmenti;               // già dichiarati a mano
    const circonferenza = TAU * f.su;
    const motivo = f.dash.reduce((a, b) => a + b, 0);
    const quanti = Math.max(1, Math.round(circonferenza / motivo));
    const passo = TAU / quanti;                       // in radianti, esatto
    const fuori = [];
    for (let m = 0; m < quanti; m++) {
      let a = m * passo;
      for (let i = 0; i < f.dash.length; i += 2) {
        const acceso = (f.dash[i] / motivo) * passo;
        const spento = (f.dash[i + 1] / motivo) * passo;
        fuori.push({ da: a, ampiezza: acceso });
        a += acceso + spento;
      }
    }
    return fuori;
  }

  /** Un segmento di fascia: arco esterno, raccordo, arco interno a ritroso.
   *
   * Un contorno chiuso e non due archi: così il segmento ha due spallette
   * nette e il riempimento del CSS ha qualcosa da riempire. Due archi
   * lascerebbero una forma aperta, e `fill` su una forma aperta la chiude per
   * la via più corta — cioè con una corda, non con un raccordo radiale.
   */
  _fascia(punti, gruppi, raggio, spessore, da, ampiezza, ruolo = "fascia") {
    const dentro = raggio - spessore;
    const seg = this.segmentsFor(raggio, ampiezza);
    const p0 = punti.length / 3;
    for (let i = 0; i <= seg; i++) {
      const a = da + (i / seg) * ampiezza;
      punti.push(Math.cos(a) * raggio, Math.sin(a) * raggio, 0);
    }
    for (let i = seg; i >= 0; i--) {
      const a = da + (i / seg) * ampiezza;
      punti.push(Math.cos(a) * dentro, Math.sin(a) * dentro, 0);
    }
    /* ⚠️ RUOLO «fascia», NON «linea» — e la distinzione l'ha imposta uno scatto.
       Con lo stesso ruolo, il `fill` che serve alla fascia colpiva anche le
       tracce concentriche dello stesso strato: erano cerchi CHIUSI, e un
       cerchio chiuso riempito è un disco. Il nucleo è uscito come una macchia
       di ciano piatto, e nessun test poteva dirlo — il gate guarda i vertici,
       non chi li colora.
       Un ruolo separato è la forma dichiarata della differenza: una fascia è
       una SUPERFICIE, una traccia è un CONTORNO, e il CSS le distingue per
       nome invece che per fortuna. */
    gruppi.push(new Gruppo(p0, punti.length / 3 - p0, { chiuso: true, ruolo }));
  }

  build() {
    const punti = [];
    const gruppi = [];

    // ⚠️ IL CERCHIO PIÙ ESTERNO PER PRIMO, e sempre intero: è quello che
    // definisce il bounding box dichiarato. Se fosse un arco parziale il bbox
    // non varrebbe più 2R su entrambi gli assi, e il gate lo direbbe — nel
    // posto sbagliato, cioè sul bounding box invece che sulla composizione.
    const rInterno = this.params.raggioMin;
    for (const r of this.raggi) {
      if (this.tratteggio && r === this.tratteggio.su) continue;  // lo fa sotto
      if (this.varco && r === rInterno) {
        // Tutto il giro tranne il varco: un arco solo, con due spallette nette.
        this._arco(punti, gruppi, r, this.varco.da + this.varco.ampiezza,
                   TAU - this.varco.ampiezza);
        continue;
      }
      this._arco(punti, gruppi, r);
    }

    // Il tratteggio: archi corti alternati a vuoti. Si genera come geometria e
    // non come `stroke-dasharray`, perché il dash CSS non sa niente del raggio
    // e con `non-scaling-stroke` la lunghezza dei trattini cambierebbe con la
    // finestra — cioè il ritmo del tratteggio non sarebbe più quello disegnato.
    if (this.tratteggio) {
      const { su, dash } = this.tratteggio;
      const passo = (dash[0] + dash[1]) / su;          // in radianti
      const quanti = Math.max(4, Math.round(TAU / passo));
      const acceso = (dash[0] / (dash[0] + dash[1])) * (TAU / quanti);
      for (let i = 0; i < quanti; i++)
        this._arco(punti, gruppi, su, (i / quanti) * TAU, acceso, "linea");
    }

    /* Le graduazioni, verso l'INTERNO dal proprio cerchio.
     *
     * ⚠️ La prima stesura le mandava in fuori, e il gate l'ha presa: le tacche
     * del globo sporgevano di 7 unità oltre r=237 e il bounding box misurava
     * 488 contro i 474 dichiarati. Non era un problema di dichiarazione — era
     * che le tacche uscivano dall'anello.
     *
     * Verso l'interno è anche come le disegna il riferimento, e come
     * `ReactorRing` le fa da sempre: «tick DENTRO la fascia. Se sporgono oltre
     * il bordo finiscono nel vuoto fra un anello e l'altro, e invece di
     * graduare sembrano frangia.» */
    if (this.tacche) {
      const { su, quante, lunghe } = this.tacche;
      for (let i = 0; i < quante; i++) {
        const a = (i / quante) * TAU;
        const p0 = punti.length / 3;
        punti.push(Math.cos(a) * su, Math.sin(a) * su, 0);
        punti.push(Math.cos(a) * (su - lunghe), Math.sin(a) * (su - lunghe), 0);
        gruppi.push(new Gruppo(p0, 2, { ruolo: "costruzione" }));
      }
    }

    // Gli archi parziali: l'asimmetria progettata di §11.6 regola 6. Sono
    // parametri con un nome, non `Math.random()`.
    for (const a of this.archiParziali)
      this._arco(punti, gruppi, a.su, a.da, a.ampiezza, "linea");

    /* Il CAMPO della fascia: l'anello pieno, sotto i segmenti.
     *
     * ⚠️ Mancava, e l'ha trovato una MISURA: senza, il nucleo scendeva a
     * entropia **2,35** contro la soglia di 2,40. Il riferimento non è fatto di
     * tracce su un fondo scuro — il suo profilo radiale tocca L 75-117 su quasi
     * tutto il raggio — e un nucleo di soli contorni legge come un disegno
     * tecnico, che è esattamente la cosa che §11.8 CONTENUTO chiede di non
     * fare. Il blueprint lo dice per L6: «riempimento ciano 8 % opacità».
     * Ha ruolo proprio perché è una terza superficie: più scura dei segmenti,
     * più chiara del campo generale. */
    if (this.fascia?.campo)
      this._fascia(punti, gruppi, this.fascia.su, this.fascia.spessore, 0, TAU, "campo");

    // La fascia segmentata — contorni CHIUSI, che il CSS riempie.
    if (this.fascia) for (const s of this._segmentiDiFascia())
      this._fascia(punti, gruppi, this.fascia.su, this.fascia.spessore, s.da, s.ampiezza);

    return new Geometria(new Float32Array(punti), gruppi);
  }

  /** Gli assi cardinali — §11.10 regola 3.
   *
   * Sono la quota del disegno meccanico: dicono dove sono lo zero e i quarti.
   * Senza, un quadrante graduato è un cerchio con dei trattini e non si capisce
   * rispetto a che cosa siano graduati.
   *
   * Vanno dal cerchio più interno al più esterno e non dal centro: al centro
   * c'è il marchio, e quattro raggi che gli passano sotto sono rumore — è la
   * stessa correzione che `ReactorRing` ha già fatto una volta.
   */
  constructionLines() {
    const punti = [];
    const gruppi = [];
    const r0 = this.params.raggioMin;
    const r1 = this.params.raggioMax;
    for (let k = 0; k < 4; k++) {
      const a = (k / 4) * TAU;
      const p0 = punti.length / 3;
      punti.push(Math.cos(a) * r0, Math.sin(a) * r0, 0);
      punti.push(Math.cos(a) * r1, Math.sin(a) * r1, 0);
      gruppi.push(new Gruppo(p0, 2, { ruolo: "costruzione" }));
    }
    return new Geometria(new Float32Array(punti), gruppi);
  }
}
