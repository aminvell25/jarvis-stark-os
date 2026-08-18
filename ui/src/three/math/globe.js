/* Globo tattico — SPEC §13, §17.4, riferimento famiglia-a/10-globo-gps-locator.
 *
 * §13 chiede al globo «fusi orari, coordinate, elevazione solare calcolata».
 * Tre componenti parametrici, tutti gatati:
 *
 *   Graticola    meridiani e paralleli, la struttura
 *   Terminatore  il cerchio massimo che separa il giorno dalla notte
 *   Fusi         un punto per fuso orario VERO di tzdata
 *
 * ── Perche' non three-globe, che §22 nomina ────────────────────────────────
 * L'invariante 22 e' netto: «Ogni componente estende ParametricComponent,
 * deriva la densita' dalla curvatura via segmentsFor(), e passa qualityGate()
 * prima del render». three-globe genera la propria geometria dentro di se':
 * non passa da nessuna delle tre cose. E cio' per cui vale davvero — il layer
 * degli archi — non ha una sorgente di coordinate vere in questo sistema
 * (FASE-05.md, R39). Restavano un pacchetto da 25 MB con diciotto dipendenze
 * e una sfera con texture.
 *
 * ── Perche' nessuna texture della Terra ────────────────────────────────────
 * Le immagini che three-globe spedisce negli esempi non hanno una licenza
 * dichiarata nel pacchetto, e la regola 30 di CLAUDE.md vuole licenza esplicita
 * e VERIFICATA. Al posto della fotografia ci sono i 312 fusi orari veri: dove
 * la gente tiene l'ora, i continenti si disegnano da soli. E' un dato, non un
 * ornamento.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";

const TAU = Math.PI * 2;
const RAD = Math.PI / 180;

/** lat/lon in gradi -> punto sulla sfera. Nord = +Y, Greenwich = +Z. */
export function suSfera(latDeg, lonDeg, R) {
  const la = latDeg * RAD;
  const lo = lonDeg * RAD;
  return [R * Math.cos(la) * Math.sin(lo), R * Math.sin(la), R * Math.cos(la) * Math.cos(lo)];
}

/* ── Posizione del Sole ─────────────────────────────────────────────────────
 *
 * §17.4: «L'elevazione solare deriva dalla declinazione stagionale e
 * dall'angolo orario — nessun valore inventato. Anche il sole e' un dato vero».
 *
 * Declinazione con la formula di Cooper: e' approssimata a meno di mezzo grado,
 * che su un globo di 200 mm vale sotto un millimetro. Una libreria di
 * effemeridi darebbe piu' cifre e nessuna differenza visibile.
 */
export function puntoSubsolare(quando = new Date()) {
  const inizio = Date.UTC(quando.getUTCFullYear(), 0, 0);
  const giorno = (quando.getTime() - inizio) / 86_400_000;
  const declinazione = 23.44 * Math.sin(((360 / 365.24) * (giorno + 284)) * RAD);
  const oreUTC =
    quando.getUTCHours() + quando.getUTCMinutes() / 60 + quando.getUTCSeconds() / 3600;
  // A mezzogiorno UTC il Sole e' sul meridiano di Greenwich; ogni ora sono 15
  // gradi verso ovest.
  const longitudine = -(oreUTC - 12) * 15;
  return { lat: declinazione, lon: ((longitudine + 540) % 360) - 180 };
}

export class Graticola extends ParametricComponent {
  constructor(p = {}) {
    const radius = p.radius ?? 200;
    super(
      {
        radius,
        passoMeridiani: p.passoMeridiani ?? 15, // gradi
        passoParalleli: p.passoParalleli ?? 15,
      },
      {
        name: "globe-graticule",
        version: "v1",
        dimensioni: 3,
        bbox: { x: 2 * radius, y: 2 * radius, z: 2 * radius },
      }
    );
    if (360 % this.params.passoMeridiani !== 0)
      throw new Error(`passoMeridiani ${this.params.passoMeridiani} non divide 360`);
  }

  build() {
    const { radius, passoMeridiani, passoParalleli } = this.params;
    const punti = [];
    const gruppi = [];

    for (let lon = -180; lon < 180; lon += passoMeridiani) {
      const seg = this.segmentsFor(radius, Math.PI);
      const p = punti.length / 3;
      for (let i = 0; i <= seg; i++) {
        punti.push(...suSfera(-90 + (180 * i) / seg, lon, radius));
      }
      gruppi.push(new Gruppo(p, seg + 1, { ruolo: "costruzione" }));
    }

    for (let lat = -90 + passoParalleli; lat < 90; lat += passoParalleli) {
      // Densita' dalla curvatura VERA del parallelo: vicino ai poli il raggio
      // e' piccolo e servono meno segmenti. Un passo costante li' sprecherebbe
      // vertici, e all'equatore ne darebbe troppo pochi.
      const r = radius * Math.cos(lat * RAD);
      const seg = this.segmentsFor(Math.max(1, r));
      const p = punti.length / 3;
      for (let i = 0; i < seg; i++) {
        punti.push(...suSfera(lat, -180 + (360 * i) / seg, radius));
      }
      gruppi.push(new Gruppo(p, seg, { chiuso: true, ruolo: lat === 0 ? "linea" : "costruzione" }));
    }

    return new Geometria(new Float32Array(punti), gruppi);
  }

  /** L'asse polare, che dice dove sta il nord. */
  constructionLines() {
    const { radius } = this.params;
    const a = new Float32Array([0, -radius * 1.12, 0, 0, radius * 1.12, 0]);
    return new Geometria(a, [new Gruppo(0, 2, { ruolo: "costruzione" })]);
  }
}

export class Terminatore extends ParametricComponent {
  /** @param {{lat:number, lon:number}} sole  punto subsolare VERO */
  constructor(p = {}, sole = { lat: 0, lon: 0 }) {
    const radius = p.radius ?? 200;
    const n = suSfera(sole.lat, sole.lon, 1); // normale del cerchio massimo
    // Estensione analitica di un cerchio massimo di normale n:
    // lungo l'asse e vale 2R*sqrt(1 - (n.e)^2). Forma chiusa, indipendente
    // dal ciclo di build(): e' cosi' che la regola 7 verifica qualcosa.
    const est = (i) => 2 * radius * Math.sqrt(Math.max(0, 1 - n[i] * n[i]));
    super(
      { radius, latSole: sole.lat, lonSole: sole.lon + 180 },  // +180: mai negativo
      {
        name: "globe-terminator",
        version: "v1",
        dimensioni: 3,
        bbox: { x: est(0), y: est(1), z: est(2) },
      }
    );
    this._n = n;
  }

  build() {
    const { radius } = this.params;
    const n = this._n;
    // Due versori ortogonali alla normale. Il primo si costruisce dal vettore
    // cardinale MENO allineato a n: usarne uno fisso darebbe un prodotto
    // vettoriale degenere quando il Sole ci passa sopra, due volte l'anno.
    const asse = Math.abs(n[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
    const u = normalizza(prodotto(n, asse));
    const v = normalizza(prodotto(n, u));

    const seg = this.segmentsFor(radius);
    const a = new Float32Array(seg * 3);
    for (let i = 0; i < seg; i++) {
      const t = (i / seg) * TAU;
      const c = Math.cos(t) * radius;
      const s = Math.sin(t) * radius;
      a[i * 3] = u[0] * c + v[0] * s;
      a[i * 3 + 1] = u[1] * c + v[1] * s;
      a[i * 3 + 2] = u[2] * c + v[2] * s;
    }
    // Ruolo "sole" e non "linea": il terminatore ha un materiale suo, caldo,
    // perche' e' l'unica cosa nel globo che significhi qualcosa di diverso
    // dalla struttura.
    return new Geometria(a, [new Gruppo(0, seg, { chiuso: true, ruolo: "sole" })]);
  }
}

export class Fusi extends ParametricComponent {
  /** @param {{nome:string, lat:number, lon:number}[]} zone  tzdata VERA */
  constructor(p = {}, zone = []) {
    const radius = p.radius ?? 200;
    super(
      { radius, count: zone.length, quota: p.quota ?? 1.004 },
      {
        name: "globe-timezones",
        version: "v1",
        dimensioni: 3,
        bbox: { x: 2 * radius, y: 2 * radius, z: 2 * radius },
        // Come per la nuvola di punti: i fusi non arrivano ai poli — il piu'
        // a nord e' sotto gli 80 gradi — quindi l'estensione su Y resta
        // qualche punto percentuale sotto il diametro. Dichiarato, non
        // aggirato misurando.
        bboxTolleranza: 0.06,
      }
    );
    if (zone.length < 8) throw new Error(`solo ${zone.length} fusi: sorgente non collegata`);
    this.zone = zone;
  }

  build() {
    const { radius, quota } = this.params;
    const a = new Float32Array(this.zone.length * 3);
    for (const [i, z] of this.zone.entries()) {
      const p = suSfera(z.lat, z.lon, radius * quota); // appena sopra la superficie
      a[i * 3] = p[0]; a[i * 3 + 1] = p[1]; a[i * 3 + 2] = p[2];
    }
    return new Geometria(a, [new Gruppo(0, this.zone.length, { ruolo: "punti" })]);
  }
}

function prodotto(a, b) {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}
function normalizza(a) {
  const n = Math.hypot(a[0], a[1], a[2]);
  return [a[0] / n, a[1] / n, a[2] / n];
}

/** Il Sole e' sopra l'orizzonte in questo punto? Prodotto scalare col
 * versore subsolare: e' il conto piu' semplice che esista, ed e' esatto. */
export function illuminato(latDeg, lonDeg, sole) {
  const p = suSfera(latDeg, lonDeg, 1);
  const s = suSfera(sole.lat, sole.lon, 1);
  return p[0] * s[0] + p[1] * s[1] + p[2] * s[2] > 0;
}
