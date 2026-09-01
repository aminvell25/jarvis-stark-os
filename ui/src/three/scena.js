/* La scena three.js minima, condivisa dai componenti 3D.
 *
 * Tre cose che ogni componente 3D rifarebbe uguale, e una che quasi tutti
 * sbagliano:
 *
 *   1. il renderer con `alpha: true` e nessun colore di sfondo. Il fondo lo
 *      dipinge il CSS del pannello, cioe' un token: se lo dipingesse WebGL
 *      sarebbe un valore letterale, e l'invariante 18 cadrebbe proprio nel
 *      punto in cui e' piu' facile non accorgersene.
 *
 *   2. il ridimensionamento, che deve aggiornare anche `LineMaterial.resolution`
 *      — e' questa la cosa che quasi tutti sbagliano. Senza, le linee spesse
 *      restano della larghezza calcolata per il viewport precedente, e a un
 *      certo punto spariscono.
 *
 *   3. il render A RICHIESTA. Un `requestAnimationFrame` perpetuo su una scena
 *      ferma e' animazione ambientale mascherata da architettura: consuma il
 *      budget di §10.4 per non mostrare nulla di nuovo, e su un portatile si
 *      sente. Si rende quando cambia qualcosa.
 *
 * `proietta()` esiste per le etichette: l'invariante 20 vuole il testo nel DOM,
 * quindi il testo non entra nella scena — e' la scena che dice al DOM dove
 * mettersi.
 */

import * as THREE from "three";

import { dichiara } from "../anim/budget.js";

//: three.js sa misurarsi: `rendi()` marca ogni render. Dirlo permette al
//: rapporto di §10.4 di distinguere «non ha reso» da «non e' strumentato».
dichiara("three");

/** Colloca la camera perche' TUTTI i vertici entrino nell'inquadratura.
 *
 * Prende i vertici e non il bounding box, e la differenza si vede. Un box che
 * contiene una sfera ha gli spigoli vuoti: inquadrare il box vuol dire
 * inquadrare quello spazio che nessun vertice occupa, e l'oggetto resta
 * piccolo in mezzo al pannello. Nella nuvola dei sorgenti gli spigoli distano
 * 294 mm dal centro mentre nessun punto supera i 200.
 *
 * Il conto e' esatto, punto per punto: perche' un vertice sia dentro il
 * frustum serve  distanza >= |scostamento laterale| / tan(semiapertura) +
 * profondita' lungo l'asse di vista. Il massimo su tutti i vertici e' la
 * distanza minima che li contiene tutti.
 *
 * @param {Float32Array} posizioni  x,y,z per vertice
 * @param {{x:number,y:number,z:number}} direzione  da dove si guarda
 */
export function inquadra(THREE, camera, posizioni, direzione, margine = 1.06) {
  if (!posizioni.length) throw new Error("inquadra() senza vertici");

  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
  const v = new THREE.Vector3();
  for (let i = 0; i < posizioni.length; i += 3) {
    v.set(posizioni[i], posizioni[i + 1], posizioni[i + 2]);
    min.min(v);
    max.max(v);
  }
  const centro = min.clone().add(max).multiplyScalar(0.5);

  const avanti = new THREE.Vector3(direzione.x, direzione.y, direzione.z).normalize();
  const destra = new THREE.Vector3().crossVectors(avanti, new THREE.Vector3(0, 1, 0)).normalize();
  const alto = new THREE.Vector3().crossVectors(destra, avanti).normalize();

  const fovV = (camera.fov * Math.PI) / 180;
  const fovH = 2 * Math.atan(Math.tan(fovV / 2) * camera.aspect);
  const tanH = Math.tan(fovH / 2);
  const tanV = Math.tan(fovV / 2);

  let distanza = 0;
  for (let i = 0; i < posizioni.length; i += 3) {
    v.set(posizioni[i], posizioni[i + 1], posizioni[i + 2]).sub(centro);
    const p = v.dot(avanti);
    distanza = Math.max(
      distanza,
      Math.abs(v.dot(destra)) / tanH + p,
      Math.abs(v.dot(alto)) / tanV + p
    );
  }
  distanza *= margine;

  camera.position.copy(centro).addScaledVector(avanti, distanza);
  camera.lookAt(centro);
  camera.updateProjectionMatrix();
  return distanza;
}

export function creaScena(ospite, { fov = 38, vicino = 1, lontano = 4000,
                                    preservaBuffer = false } = {}) {
  /* ⚠️ `preservaBuffer` ESISTE PER IL CICLO §11.7, e senza c'e' una misura che
   * non si puo' fare.
   *
   * Con `preserveDrawingBuffer: false` — il default di WebGL, e quello giusto
   * per le prestazioni — il buffer di disegno si puo' svuotare dopo che il
   * compositore l'ha letto. Rendere a richiesta va benissimo finche' a
   * guardare e' un occhio: la pagina si ridipinge e la scena ricompare.
   *
   * Ma §25.13.5 si misura con DUE `capturePage()` a 120 ms di distanza — uno
   * col marchio e uno senza — e la differenza dice quali pixel sono la
   * scritta. Se fra i due la tela WebGL si svuota, quella differenza contiene
   * anche l'intera scena 3D, e il criterio misura il globo credendo di
   * misurare il nome. Successo: l'inchiostro del marchio risultava a r 56,9 px
   * invece che a 17, e il franco andava a -35,9.
   *
   * Costa memoria — un secondo buffer per contesto — e per questo NON e' il
   * default: lo chiede chi finisce dentro una misura fatta di fotografie.
   */
  const renderer = new THREE.WebGLRenderer({
    alpha: true, antialias: true, preserveDrawingBuffer: preservaBuffer,
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.domElement.style.display = "block";
  renderer.domElement.style.width = "100%";
  renderer.domElement.style.height = "100%";
  ospite.appendChild(renderer.domElement);

  const scena = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(fov, 1, vicino, lontano);

  const materialiLinea = new Set();
  let larghezza = 0;
  let altezza = 0;
  let sporco = true;

  function misura() {
    const r = ospite.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width));
    const h = Math.max(1, Math.round(r.height));
    if (w === larghezza && h === altezza) return false;
    larghezza = w;
    altezza = h;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    for (const m of materialiLinea) m.resolution.set(w, h);
    sporco = true;
    return true;
  }

  const osservatore = new ResizeObserver(() => { if (misura()) rendi(); });
  osservatore.observe(ospite);
  misura();

  /* ⚠️ La misura e' PER MOTORE, ed e' `DIVARIO-PREMIUM.md` §12.
   *
   * L'invariante 26 da' tre budget separati — three.js <= 8 ms, Pixi <= 3,
   * anime.js <= 4 — e finora si misurava una cosa sola: l'intervallo fra due
   * fotogrammi, che con il render a richiesta risponde sempre vsync e non dice
   * quanto costa CHI. `performance.measure` mette il costo dove nasce, e chi
   * legge somma per motore invece di indovinare.
   *
   * Costa una `performance.mark` per render, cioe' niente su un motore che
   * rende solo quando qualcosa cambia. */
  function rendi() {
    if (!sporco) return false;
    sporco = false;
    performance.mark("three:da");
    renderer.render(scena, camera);
    performance.measure("three", "three:da");
    return true;
  }

  /** Un punto della scena -> pixel dentro `ospite`, per le etichette DOM. */
  const _v = new THREE.Vector3();
  function proietta(x, y, z) {
    _v.set(x, y, z).project(camera);
    return {
      x: (_v.x * 0.5 + 0.5) * larghezza,
      y: (-_v.y * 0.5 + 0.5) * altezza,
      davanti: _v.z < 1,
    };
  }

  return {
    THREE, renderer, scena, camera,
    get larghezza() { return larghezza; },
    get altezza() { return altezza; },
    /** Registra un LineMaterial perche' la sua `resolution` resti aggiornata. */
    seguiLinea(materiale) { materialiLinea.add(materiale); materiale.resolution.set(larghezza, altezza); },
    invalida() { sporco = true; },
    rendi,
    proietta,
    smonta() {
      osservatore.disconnect();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
