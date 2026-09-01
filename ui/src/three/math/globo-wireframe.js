/* La sfera olografica del nucleo — L5, l'unico strato davvero 3D.
 *
 * ## Che cos'e', e che cosa NON e'
 *
 * E' una FORMA: un reticolo sferico che da' profondita' al disco. Non mostra
 * niente, e la riga va scritta prima delle altre perche' il giorno che a
 * qualcuno venisse voglia di appenderci dei numeri quella persona deve trovare
 * scritto che qui non ci vanno.
 *
 * L'invariante 23 vieta i **dati** segnaposto, non le forme: un anello con un
 * varco non e' un dato finto, e nemmeno un reticolo. Diventerebbe dato finto
 * nell'istante in cui uno di questi punti pretendesse di essere un file, un
 * nodo o un satellite senza esserlo. Se un giorno servisse una sfera che dice
 * qualcosa esiste gia' ed e' un'altra: `three/math/pointcloud.js` mappa i file
 * veri del progetto.
 *
 * ## L'angolo d'oro, e perche' non `Math.random()`
 *
 * La spirale di Fibonacci distribuisce per AREA come l'inversione
 * `phi = acos(2u - 1)` di §17.4, ma senza sorteggio:
 *
 *     z_i     = 1 - (2i + 1) / N          uniforme in cos(phi)
 *     theta_i = i * angolo aureo          equidistribuito, bassa discrepanza
 *
 * Due proprieta' che il sorteggio non ha, e qui contano tutte e due:
 *
 *   1. **e' deterministica.** La sfera gira in continuo: con punti sorteggiati
 *      ogni ricostruzione — un resize, un rimontaggio — ne produrrebbe una
 *      diversa, e si vedrebbe come uno sfarfallio senza causa;
 *   2. **non fa grumi.** `Math.random()` su una sfera lascia buchi e
 *      addensamenti visibili gia' a poche centinaia di punti, e a schermo
 *      leggono come un difetto di render invece che come una distribuzione.
 *
 * §11.10 regola 4 concede il sorteggio alle nuvole di punti. Concedere non e'
 * prescrivere: qui non serve, e cio' che non serve non si prende.
 */

import { ParametricComponent } from "../component.js";
import { Geometria, Gruppo } from "../geometry.js";

const TAU = Math.PI * 2;

//: L'angolo aureo in radianti: pi (3 - sqrt 5). Scritto come formula e non
//: come 2.39996 perche' il numero da solo non direbbe da dove viene, e chi lo
//: trovasse fra sei mesi non saprebbe se e' esatto o arrotondato a caso.
const ANGOLO_AUREO = Math.PI * (3 - Math.sqrt(5));

export class GloboWireframe extends ParametricComponent {
  constructor(p = {}) {
    const radius = p.radius ?? 237;
    super(
      {
        radius,                          // unita' di viewBox, come tutto l'HUD
        count: p.count ?? 720,
        meridiani: p.meridiani ?? 6,
        paralleli: p.paralleli ?? 3,     // per emisfero, equatore escluso
      },
      {
        name: p.name ?? "globo-wireframe",
        version: "v1",
        dimensioni: 3,
        bbox: { x: 2 * radius, y: 2 * radius, z: 2 * radius },
        /* Un campione discreto di una superficie continua non tocca i propri
           estremi. Per la spirale aurea lo scarto e' calcolabile e non stimato:
           l'estensione in z vale 2R(1 - 1/N) per costruzione, e su x e y dipende
           da quanto vicino a zero cade il theta del punto piu' equatoriale.
           **Misurato a N=720: 0,139 %**, dentro l'1 % che il gate ammette gia'
           di suo. Il 3 % non serve a N=720 e c'e' perche' `count` e' un
           parametro: lo scarto cresce come 1/N, e sotto i duecento punti
           supererebbe l'1 %. */
        bboxTolleranza: 0.03,
      }
    );
    if (this.params.count < 64)
      throw new Error(
        `sfera con ${this.params.count} punti: sotto il centinaio la spirale ` +
        "aurea si vede come spirale invece che come superficie"
      );
    if (this.params.meridiani < 2)
      throw new Error("meno di due meridiani non orientano niente");
  }

  build() {
    const { radius, count } = this.params;
    const a = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      // z uniforme in [-1, 1]: e' cos(phi), la variabile che distribuisce per
      // AREA. Il mezzo passo (2i + 1) tiene i due estremi simmetrici, cosi' la
      // sfera non e' piu' densa a un polo che all'altro.
      const z = 1 - (2 * i + 1) / count;
      const r = Math.sqrt(Math.max(0, 1 - z * z));
      const theta = i * ANGOLO_AUREO;
      a[i * 3] = radius * r * Math.cos(theta);
      a[i * 3 + 1] = radius * z;
      a[i * 3 + 2] = radius * r * Math.sin(theta);
    }
    return new Geometria(a, [new Gruppo(0, count, { ruolo: "punti" })]);
  }

  /** Il reticolo: meridiani e paralleli — §11.10 regola 3.
   *
   * Senza, una nuvola sferica e' una macchia: non si legge dove sia l'asse ne'
   * da che parte stia girando. Con, la rotazione diventa visibile — ed e' il
   * reticolo, non i punti, a dire che l'oggetto e' una sfera e non un disco.
   *
   * La densita' di ogni cerchio viene da `segmentsFor()` sul PROPRIO raggio,
   * non su quello della sfera: un parallelo vicino al polo e' corto e non ha
   * bisogno degli stessi segmenti dell'equatore. E' §11.10 regola 2 alla
   * lettera — la densita' dalla curvatura, non una costante per tutti.
   */
  constructionLines() {
    const { radius, meridiani, paralleli } = this.params;
    const punti = [];
    const gruppi = [];

    const cerchio = (raggio, y, asse) => {
      if (raggio <= 0) return;
      const seg = this.segmentsFor(raggio);
      const p = punti.length / 3;
      for (let i = 0; i < seg; i++) {
        const t = (i / seg) * TAU;
        const c = Math.cos(t) * raggio;
        const s = Math.sin(t) * raggio;
        // `asse` dice su quale piano gira: "y" e' un parallelo (orizzontale),
        // un numero e' l'angolo del piano di un meridiano attorno all'asse Y.
        if (asse === "y") punti.push(c, y, s);
        else punti.push(c * Math.cos(asse), s, c * Math.sin(asse));
      }
      gruppi.push(new Gruppo(p, seg, { chiuso: true, ruolo: "costruzione" }));
    };

    // I meridiani passano per i poli: mezzo giro basta a coprirli tutti, ed e'
    // il motivo per cui l'angolo va da 0 a pi greco e non a 2 pi.
    for (let m = 0; m < meridiani; m++) cerchio(radius, 0, (m / meridiani) * Math.PI);

    // L'equatore, poi i paralleli simmetrici. Distribuiti in LATITUDINE e non
    // in altezza: paralleli equispaziati in y si accalcano ai poli, che e' lo
    // stesso errore dell'inversione mancata sui punti.
    cerchio(radius, 0, "y");
    for (let k = 1; k <= paralleli; k++) {
      const lat = (k / (paralleli + 1)) * (Math.PI / 2);
      const y = radius * Math.sin(lat);
      const r = radius * Math.cos(lat);
      cerchio(r, y, "y");
      cerchio(r, -y, "y");
    }

    return new Geometria(new Float32Array(punti), gruppi);
  }
}
