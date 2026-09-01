/* Lo strato L5 — la sfera olografica, in three.js.
 *
 * ## ⚠️ Questo file È la deroga 2, e va detto qui prima che altrove
 *
 * §25.11 dice: «Niente three.js per il nucleo. È SVG e deve restarlo», e
 * «nessun secondo elemento di fondo». La deroga è del proprietario, del
 * 1° settembre 2026, ed è in `docs/acceptance/NUCLEO-HUD.md`. Non è un
 * fraintendimento della sezione: la sezione dice esattamente questo.
 *
 * Cio' che la deroga NON copre, e che qui si tiene per intero:
 *
 *   — **invariante 21**: le linee sono `Line2` + `LineMaterial`, mai
 *     `LineBasicMaterial` — `linewidth` viene ignorato quasi ovunque;
 *   — **invariante 22**: la geometria è `GloboWireframe`, che estende
 *     `ParametricComponent`, deriva la densità da `segmentsFor()` e passa dal
 *     `qualityGate()` PRIMA di arrivare qui;
 *   — **invariante 18**: i colori escono da `tok()`. Un `0x77c3d5` scritto qui
 *     sarebbe il valore letterale più facile da non vedere di tutto il
 *     progetto, perché l'audit del DOM non entra in WebGL;
 *   — **§11.10 regola 6**: due materiali, e sono due.
 *
 * ## Il retro attenuato, che è tutto l'effetto
 *
 * Il riferimento lo misura al 30-35 %: i punti sulla faccia lontana restano
 * visibili ma spenti. È quello — non i punti in sé — a far leggere l'oggetto
 * come una sfera TRASPARENTE invece che come un disco di puntini. Senza, la
 * nuvola è una macchia e la rotazione non si vede.
 *
 * Si calcola in JS e non in uno shader, ed è la scelta che il progetto ha già
 * fatto due volte: `panels/globe.js` e `panels/source.js` colorano i punti con
 * `vertexColors`. Un `ShaderMaterial` sarebbe un terzo modo di dire la stessa
 * cosa, con del GLSL da mantenere e un colore da passare comunque come uniform
 * per non violare l'invariante 18.
 *
 * ⚠️ **È un'approssimazione, dichiarata.** L'attenuazione usa la sola
 * rotazione attorno a Y, non la matrice completa: la nutazione inclina di ±8°,
 * e su una rampa di luminosità quella differenza non si vede. Il conto esatto
 * sarebbe 720 moltiplicazioni di matrice per fotogramma invece di 720
 * moltiplicazioni scalari — pagate per una differenza sotto la soglia
 * dell'occhio.
 *
 * ## Il ciclo, che è la parte cara
 *
 * `scena.js` rende A RICHIESTA, apposta. Qui la scena non è ferma — la sfera
 * gira, ed è la deroga 3 — quindi il ciclo c'è e costa. Tre cose lo tengono
 * onesto: si ferma a finestra nascosta, conta i propri fotogrammi, e il costo
 * si misura per motore (`scena.rendi()` mette già una `performance.measure`).
 * Il tetto è 8 ms, invariante 26. Se sfonda si abbassa `count`, non il tetto.
 */

import * as THREE from "three";

import { LineMaterial } from "three/addons/lines/LineMaterial.js";

import { versoBufferGeometry, versoLinee } from "../three/buffer.js";
import { GloboWireframe } from "../three/math/globo-wireframe.js";
import { qualityGate } from "../three/quality-gate.js";
import { creaScena, inquadra } from "../three/scena.js";
import { tok } from "../style/tokens.js";
import { STRATI, VIEWBOX } from "./geometria.js";

export const meta = { nome: "globo", versione: "1" };

//: Da dove si guarda. Una sfera vista dall'equatore è un disco: si perdono i
//: paralleli, cioè metà del reticolo che dice che è una sfera.
const SGUARDO = { x: 0.14, y: 0.30, z: 1 };

//: La parallasse col puntatore, in radianti, e quanto insegue. Il riferimento
//: dà ±0,15 rad e lerp 0,05: abbastanza da far sentire la profondità, troppo
//: poco perché l'occhio la legga come un oggetto che risponde al mouse.
const PARALLASSE = 0.15;
const INSEGUIMENTO = 0.05;

export const css = `
/* Lo strato della sfera: sopra il corpo del disco e sotto il nome, e non
   intercetta niente. Nessun fondo dichiarato — il renderer nasce con alpha, e
   il fondo lo dipinge l'SVG sotto. Un fondo qui sarebbe un colore scritto in
   WebGL, cioè un letterale che l'audit non vedrebbe mai. */
.hud__globo {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  overflow: hidden;
}
`;

/** Monta la sfera dentro `ospite`. Non parte da sola: chiamare `avvia()`. */
export function crea(ospite) {
  const s = STRATI.find((x) => x.id === "globo");

  const radice = document.createElement("div");
  radice.className = "hud__globo";
  ospite.appendChild(radice);

  /* ⚠️ `preservaBuffer: true`, e non e' un'ottimizzazione al contrario.
     Il nucleo finisce dentro `verifica:marchio`, che misura §25.13.5
     confrontando due `capturePage()`. Senza il buffer preservato la tela si
     svuota fra i due e la differenza conta il globo come se fosse la scritta:
     misurato, l'inchiostro risultava a r 56,9 px invece che a 17.
     Il costo e' un secondo buffer per questo contesto — uno solo, e in cambio
     una misura che si puo' fare. */
  const scena = creaScena(radice, { fov: 34, preservaBuffer: true });
  const { scena: s3, camera } = scena;

  const componente = new GloboWireframe({
    radius: s.r[0], count: s.punti,
    meridiani: s.meridiani, paralleli: s.paralleli,
  });
  const geometria = componente.build();
  const costruzione = componente.constructionLines();

  /* ⚠️ IL RETICOLO NON PRENDE `materialiPerRuolo`, e la ragione è uno scatto.
   *
   * Quel richiamo dà al ruolo «costruzione» il colore --cy-900, che è il
   * gradino più scuro della rampa. È giusto per una linea di quota dentro un
   * pannello chiaro; qui il reticolo cade sopra il corpo del disco, che è
   * ANCH'ESSO --cy-900, e reso non si vedeva affatto.
   *
   * Il materiale si costruisce quindi qui, con il gradino sopra. Resta un
   * `LineMaterial` — invariante 21, `linewidth` viene ignorato da quasi tutte
   * le implementazioni OpenGL su `LineBasicMaterial` — e resta un colore da
   * `tok()`, cioè da `tokens.css`: l'invariante 18 non ha eccezioni in WebGL,
   * dove sarebbero anche le più difficili da vedere.
   *
   * `seguiLinea` non è facoltativo: lo shader converte lo spessore da pixel a
   * clip space e per farlo deve sapere quanto è grande il viewport. Se nessuno
   * gliela dice, `resolution` resta (0,0) e le linee spariscono. */
  const materialeLinee = new LineMaterial({
    color: new THREE.Color(tok("--cy-800")),
    linewidth: 0.5,
  });
  const materiali = new Map([["costruzione", materialeLinee]]);
  scena.seguiLinea(materialeLinee);

  /* ⚠️ I COLORI SI LEGGONO UNA VOLTA, non a ogni fotogramma. `tok()` fa un
     `getComputedStyle` sul documento: chiamarlo 720 volte per fotogramma
     sarebbe un reflow al secondo per un valore che non cambia mai. */
  const davanti = new THREE.Color(tok("--cy-500"));
  const dietro = new THREE.Color(tok("--cy-900"));

  const punti = versoBufferGeometry(geometria);
  const colori = new Float32Array(componente.params.count * 3);
  punti.setAttribute("color", new THREE.BufferAttribute(colori, 3));

  const materialePunti = new THREE.PointsMaterial({
    size: 4.0, sizeAttenuation: true, vertexColors: true, transparent: false,
  });

  // Esattamente due materiali — §11.10 regola 6 — e il gate PRIMA del render.
  qualityGate(componente, geometria, [materialePunti, ...materiali.values()]);

  /* ⚠️ UN PIVOT SOLO, e ruota lui. Ruotare i due oggetti separatamente
     vorrebbe dire due scritture di matrice per fotogramma che devono restare
     d'accordo: il giorno che una prende un angolo diverso, i punti scivolano
     rispetto al reticolo e sembra un difetto di geometria. */
  const perno = new THREE.Group();
  perno.add(new THREE.Points(punti, materialePunti));
  for (const o of versoLinee(costruzione, materiali)) perno.add(o);
  s3.add(perno);

  inquadra(THREE, camera, geometria.posizioni, SGUARDO);

  /* ── L'attenuazione del retro ─────────────────────────────────────────── */
  const pos = geometria.posizioni;
  const raggio = componente.params.radius;

  function tingi(angolo) {
    const sa = Math.sin(angolo), ca = Math.cos(angolo);
    for (let i = 0, n = componente.params.count; i < n; i++) {
      const x = pos[i * 3], z = pos[i * 3 + 2];
      // La z dopo la rotazione attorno a Y: positiva = verso chi guarda.
      const zr = -x * sa + z * ca;
      // 0 sul retro, 1 sul fronte. `retro` è la quota che il riferimento
      // misura: il punto più lontano non sparisce, resta al 32 %.
      const t = s.retro + (1 - s.retro) * ((zr / raggio + 1) / 2);
      colori[i * 3] = dietro.r + (davanti.r - dietro.r) * t;
      colori[i * 3 + 1] = dietro.g + (davanti.g - dietro.g) * t;
      colori[i * 3 + 2] = dietro.b + (davanti.b - dietro.b) * t;
    }
    punti.getAttribute("color").needsUpdate = true;
  }

  /* ── Il ciclo ─────────────────────────────────────────────────────────── */
  let anello = 0, ultimo = 0, fotogrammi = 0, vuole = false;
  let angolo = 0, tempo = 0, ampiezza = 0;
  let mouseX = 0, mouseY = 0, curX = 0, curY = 0;

  function passo(ora) {
    anello = requestAnimationFrame(passo);
    // Il delta e non un incremento fisso: a 30 Hz un incremento per fotogramma
    // farebbe girare la sfera a metà velocità, e il periodo dichiarato
    // smetterebbe di essere il periodo vero.
    const dt = ultimo ? Math.min(100, ora - ultimo) / 1000 : 0;
    ultimo = ora;
    tempo += dt;

    angolo = (angolo + dt * (Math.PI * 2 / s.periodoS)) % (Math.PI * 2);
    perno.rotation.y = angolo;

    // La nutazione: l'asse oscilla, e senza la sfera gira come una trottola
    // perfetta — che è l'unica cosa che in natura non fa.
    const nut = (s.nutazione.gradi * Math.PI / 180) *
                Math.sin(tempo * Math.PI * 2 * s.nutazione.hz);

    // La parallasse insegue il puntatore invece di saltarci: `INSEGUIMENTO` è
    // la frazione di distanza colmata per fotogramma, ed è ciò che la fa
    // leggere come inerzia e non come aggancio.
    curX += (mouseX - curX) * INSEGUIMENTO;
    curY += (mouseY - curY) * INSEGUIMENTO;
    perno.rotation.x = nut + curY * PARALLASSE;
    perno.rotation.z = curX * PARALLASSE * 0.4;

    // I punti si gonfiano con la voce: ×(1 + 0,5·A), come il riferimento.
    materialePunti.size = 4.0 * (1 + s.audio * ampiezza);

    tingi(angolo);
    scena.invalida();
    if (scena.rendi()) fotogrammi++;
  }

  function avvia() {
    vuole = true;
    if (anello || document.visibilityState === "hidden") return;
    ultimo = 0;
    anello = requestAnimationFrame(passo);
  }

  //: Sospende senza dimenticare che qualcuno vuole il moto: è ciò che
  //: distingue «la finestra è coperta» da «non c'è più ragione di girare».
  function sospendi() {
    if (!anello) return;
    cancelAnimationFrame(anello);
    anello = 0;
    ultimo = 0;
  }

  function ferma() { vuole = false; sospendi(); }

  /* ⚠️ TORNA ALL'ANGOLO ZERO, e serve al ciclo §11.7.
   *
   * Fermare non basta: ferma DOVE si trova. Due scatti di due stati diversi si
   * ritroverebbero la sfera a due angoli diversi, e le immagini non sarebbero
   * confrontabili — è lo stesso difetto che gli anelli avevano già mostrato,
   * misurato al 43 % dei pixel. */
  function azzera() {
    sospendi();
    angolo = 0; tempo = 0; curX = 0; curY = 0; ampiezza = 0;
    perno.rotation.set(0, 0, 0);
    materialePunti.size = 4.0;
    tingi(0);
    scena.invalida();
    scena.rendi();
  }

  const suVisibilita = () => {
    if (document.visibilityState === "hidden") sospendi();
    else if (vuole) avvia();
  };
  document.addEventListener("visibilitychange", suVisibilita);

  /* La parallasse legge il puntatore sulla FINESTRA, non sul componente: lo
     strato ha `pointer-events: none` e non riceverebbe niente. `passive` perché
     non si annulla mai nulla, e senza il browser lo segnala. */
  const suMouse = (e) => {
    mouseX = (e.clientX / window.innerWidth) * 2 - 1;
    mouseY = (e.clientY / window.innerHeight) * 2 - 1;
  };
  window.addEventListener("pointermove", suMouse, { passive: true });

  /** Il riquadro, in pixel CSS. Lo detta il disco: la sfera è una frazione
   *  dichiarata del suo diametro, non una dimensione propria. */
  function misura(diametroPx) {
    const lato = Math.max(1, Math.round(diametroPx * (2 * s.r[0]) / VIEWBOX));
    radice.style.width = lato + "px";
    radice.style.height = lato + "px";
    scena.invalida();
    scena.rendi();
  }

  tingi(0);

  /* ⚠️ RIDISEGNA SU RICHIESTA, e serve a una misura che senza non si puo' fare.
   *
   * §25.13.5 confronta DUE `capturePage()` a 120 ms di distanza — uno col
   * marchio e uno senza — e chiama «tratto» i pixel che si schiariscono. Fra le
   * due catture il ciclo del globo e' fermo (lo ferma `fissa()`), ma la tela
   * WebGL non ridisegna: quello che il compositore le legge dentro puo'
   * differire di qualche livello sui bordi antialiasati del reticolo, e la
   * soglia di 8 livelli della misura non basta a scartarli.
   *
   * Misurato: l'inchiostro del marchio risultava a r 57 px invece che a 17, e
   * il criterio e' diventato INSTABILE — stesse sorgenti, esiti diversi fra due
   * giri. Un criterio che risponde a caso non e' un criterio.
   *
   * Non si esclude il globo dalla misura: sta SOTTO il nome, e il composito e'
   * quello che c'e' davvero. Si rende identico nei due fotogrammi. */
  function rendi() {
    scena.invalida();
    scena.rendi();
  }

  return {
    radice, misura, avvia, ferma, azzera, rendi,
    /** L'ampiezza della voce, 0..1 — i punti si gonfiano. */
    ampiezza(a) { ampiezza = Math.min(1, Math.max(0, Number(a) || 0)); },
    /** Le leve per la verifica. */
    stato() {
      return {
        fotogrammi, gira: Boolean(anello), vuole,
        angolo: +angolo.toFixed(4), periodoS: s.periodoS,
        punti: componente.params.count, retro: s.retro,
      };
    },
    smonta() {
      ferma();
      document.removeEventListener("visibilitychange", suVisibilita);
      window.removeEventListener("pointermove", suMouse);
      materialePunti.dispose();
      for (const m of materiali.values()) m.dispose();
      scena.smonta();
      radice.remove();
    },
  };
}
