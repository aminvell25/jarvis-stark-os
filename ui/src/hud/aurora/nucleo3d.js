/** Il nucleo Aurora: tre gusci deformati da rumore, e la catena che li accende.
 *
 * ## Che cos'e', e perche' esiste in questa forma
 *
 * Il riferimento portato il 1º settembre 2026 non e' un disegno: e' un motore.
 * La forma non e' modellata, e' CALCOLATA a ogni fotogramma da un rumore FBM
 * sulla normale, e cio' che si vede — creste, fronti d'onda, scarti — sono
 * termini distinti sommati allo spostamento radiale. Copiare la sola geometria
 * darebbe una palla ferma.
 *
 * ## Le deroghe, tutte in questo file
 *
 * ⚠️ **Invariante 19 — zero glow, zero bloom.** Qui il bloom e' una catena di
 * quattro passaggi: soglia, sfocatura separabile, composito con rifrazione e
 * aberrazione cromatica, e scia per accumulo. Non e' un effetto aggiunto sopra:
 * il composito NON e' additivo, applica una curva di tono
 * `c / (c + 0.82) * 1.62`, e senza di lei i gusci additivi saturano a bianco.
 * Togliere il bloom significa riscrivere anche il modo in cui i gusci si
 * sommano.
 *
 * ⚠️ **§25.11 — niente three.js nel nucleo.** Il nucleo E' three.js.
 *
 * ⚠️ **Invariante 22 — geometria parametrica con qualityGate.** Gli
 * icosaedri sono primitive di three.js e la densita' la fissa `detail`, non
 * `segmentsFor()`. La verifica che resta e' un CONTEGGIO dichiarato:
 * `stato().vertici` dice quanti sono, e il presidio confronta quel numero con
 * quello atteso. Un cancello dichiarato vale piu' di un cancello finto.
 *
 * ⚠️ **Invariante 26 — three.js <= 8 ms.** Con quattro passaggi a tela piena
 * piu' due a meta' risoluzione, il budget e' da MISURARE, non da assumere:
 * `stato().ms` porta la mediana degli ultimi fotogrammi.
 *
 * Tutte e quattro sono state autorizzate esplicitamente: «anche se va contro le
 * nostre specifiche». Costo e ritorno in `docs/acceptance/NUCLEO-AURORA.md`.
 */

import * as THREE from "three";
import { tok } from "../../style/tokens.js";
import { GUSCI } from "./stati.js";

/** Rumore a valore, tre dimensioni, quattro ottave.
 *
 * ⚠️ Sta in un array di righe e non in un template literal, e non e' pignoleria:
 * il GLSL cita spesso `vec3(...)` e in questo repository un backtick dentro un
 * literal ha chiuso il modulo nove volte. Un array di stringhe non ha quel
 * modo di rompersi. */
const RUMORE = [
  "vec3 jhash(vec3 p){ p = vec3(dot(p,vec3(127.1,311.7,74.7)), dot(p,vec3(269.5,183.3,246.1)), dot(p,vec3(113.5,271.9,124.6))); return -1.0+2.0*fract(sin(p)*43758.5453123); }",
  "float jnoise(vec3 p){ vec3 i=floor(p); vec3 f=fract(p); vec3 u=f*f*(3.0-2.0*f);",
  " return mix(mix(mix(dot(jhash(i+vec3(0.,0.,0.)),f-vec3(0.,0.,0.)), dot(jhash(i+vec3(1.,0.,0.)),f-vec3(1.,0.,0.)),u.x),",
  "                mix(dot(jhash(i+vec3(0.,1.,0.)),f-vec3(0.,1.,0.)), dot(jhash(i+vec3(1.,1.,0.)),f-vec3(1.,1.,0.)),u.x),u.y),",
  "            mix(mix(dot(jhash(i+vec3(0.,0.,1.)),f-vec3(0.,0.,1.)), dot(jhash(i+vec3(1.,0.,1.)),f-vec3(1.,0.,1.)),u.x),",
  "                mix(dot(jhash(i+vec3(0.,1.,1.)),f-vec3(0.,1.,1.)), dot(jhash(i+vec3(1.,1.,1.)),f-vec3(1.,1.,1.)),u.x),u.y),u.z); }",
  "float jfbm(vec3 p){ float a=0.5; float s=0.0; for(int k=0;k<4;k++){ s+=a*jnoise(p); p*=2.03; a*=0.5; } return s; }",
].join("\n");

/** Lo spostamento radiale, termine per termine.
 *
 * Ogni riga di `d +=` e' una cosa che il nucleo sa fare, e si accende da sola:
 * il rumore di fondo, la fascia di scansione, lo scatto di MINACCIA,
 * l'increspatura di SOVRACCARICO, i fronti d'onda delle sillabe, l'urto del
 * cambio di stato. Sommarle invece di sceglierne una e' la ragione per cui due
 * stati diversi non sembrano lo stesso stato con un colore diverso. */
const VERTEX = [
  RUMORE,
  "uniform float uTempo; uniform float uAmp; uniform float uFase; uniform float uFreq; uniform float uFreqK; uniform float uSpinta;",
  "uniform float uScan; uniform float uScatto; uniform float uOver; uniform float uCollasso; uniform float uNascita;",
  "uniform vec4 uSil; uniform vec4 uSilAmp; uniform float uParla; uniform float uUrto;",
  "varying float vD; varying vec3 vN; varying vec3 vP; varying float vScan; varying float vOver; varying float vRip; varying float vUrto;",
  "void main(){",
  "  vec3 n = normalize(position);",
  "  float f = jfbm(n * (uFreq * uFreqK) + vec3(uFase, uTempo * 0.4, uFase * 0.5));",
  "  float d = f * (uSpinta + uAmp * 0.32 * (1.0 - uParla * 0.62)) + uAmp * 0.07 * (1.0 - uParla * 0.7);",
  "  float band = 1.0 - smoothstep(0.0, 0.16, abs(n.y - uScan));",
  "  vScan = band;",
  "  d += band * 0.13;",
  "  float jt = jnoise(vec3(floor(uTempo * 9.0), n.x * 3.0, n.z * 3.0)) * uScatto;",
  "  d += jt * 0.06;",
  "  float rip = sin(dot(n, vec3(7.0, 5.0, 9.0)) * 9.0 - uTempo * 22.0) * uOver;",
  "  d += rip * 0.05;",
  "  vOver = uOver;",
  "  float geo = acos(clamp(dot(n, vec3(0.0, 0.0, 1.0)), -1.0, 1.0));",
  "  float onda = 0.0;",
  "  for (int q = 0; q < 4; q++) {",
  "    float eta = uSil[q];",
  "    if (eta < 0.0) continue;",
  "    float fronte = eta * 4.2;",
  "    float anello = exp(-pow((geo - fronte) * 3.4, 2.0));",
  "    float vita = exp(-eta * 2.1);",
  "    onda += anello * vita * uSilAmp[q];",
  "  }",
  "  float urto = 0.0;",
  "  if (uUrto >= 0.0) {",
  "    float fr = uUrto * 3.1;",
  "    urto = exp(-pow((geo - fr) * 2.4, 2.0)) * exp(-uUrto * 1.5) * 1.6;",
  "  }",
  "  vUrto = urto;",
  "  d += urto * 0.17;",
  "  vRip = onda * uParla;",
  "  d += vRip * 0.150;",
  "  float forma = sin(geo * 9.0 - uTempo * 3.0) * 0.5 + sin(geo * 21.0 + uTempo * 1.4) * 0.28;",
  "  d += forma * uParla * uAmp * 0.022;",
  "  vD = d;",
  "  vec3 p = position * (1.0 - uCollasso * 0.94) * uNascita + n * d * (1.0 - uCollasso * 0.8);",
  "  vN = normalize(normalMatrix * n);",
  "  vec4 mv = modelViewMatrix * vec4(p, 1.0);",
  "  vP = mv.xyz;",
  "  gl_Position = projectionMatrix * mv;",
  "}",
].join("\n");

const FRAG_GUSCIO = [
  "uniform float uOp; uniform vec3 uTinta; uniform vec3 uCaldo; uniform float uBagliore; uniform float uParla;",
  "varying float vD; varying vec3 vN; varying vec3 vP; varying float vScan; varying float vOver; varying float vRip; varying float vUrto;",
  "void main(){",
  "  float fres = pow(1.0 - abs(dot(normalize(vN), normalize(-vP))), 2.2);",
  "  float k = clamp(abs(vD) * 3.4, 0.0, 1.0);",
  "  vec3 col = mix(uTinta, uCaldo, fres);",
  "  col = mix(col, vec3(0.72, 0.62, 1.0), pow(fres, 3.0) * 0.55);",
  "  col = mix(col, vec3(1.0), vScan * 0.85);",
  "  col = mix(col, vec3(1.0), vOver * 0.6);",
  "  col = mix(col, vec3(0.94, 1.0, 1.0), clamp(vRip * 1.5, 0.0, 0.9));",
  "  col = mix(col, vec3(1.0), clamp(vUrto * 0.9, 0.0, 0.92));",
  "  float a = (fres * 0.85 * (1.0 - uParla * 0.42) + k * 0.22 + vScan * 0.5 + vOver * 0.16 + clamp(vRip, 0.0, 1.0) * 0.62 + clamp(vUrto, 0.0, 1.0) * 0.7) * uOp;",
  "  gl_FragColor = vec4(col * (0.55 + uBagliore * 0.8), a);",
  "}",
].join("\n");

const FRAG_RETICOLO = [
  "uniform float uOp; uniform vec3 uTinta; uniform vec3 uCaldo; uniform float uRet;",
  "varying float vD; varying float vScan; varying float vOver; varying float vRip; varying float vUrto;",
  "void main(){",
  "  float k = clamp(abs(vD) * 4.0, 0.0, 1.0);",
  "  vec3 c = mix(uTinta, uCaldo, k);",
  "  c = mix(c, vec3(1.0), max(max(vScan * 0.8, vOver * 0.5), max(clamp(vRip * 1.6, 0.0, 0.95), clamp(vUrto * 1.2, 0.0, 0.95))));",
  "  gl_FragColor = vec4(c, (0.06 + 0.30 * k + vScan * 0.4 + clamp(vRip, 0.0, 1.0) * 0.5 + clamp(vUrto, 0.0, 1.0) * 0.55) * uOp * (0.4 + uRet * 1.4));",
  "}",
].join("\n");

const VS_QUAD = "varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }";

/** Il colore di un token come terna 0..1 per lo shader. */
function terna(nome) {
  const s = tok(nome).trim();
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(s)
    || /rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(s);
  if (!m) return [0, 0, 0];
  const base = s.startsWith("#") ? 16 : 10;
  return [1, 2, 3].map((i) => parseInt(m[i], base) / 255);
}

export function crea(ospite, { lato = 177 } = {}) {
  const renderer = new THREE.WebGLRenderer({
    alpha: true, antialias: true, preserveDrawingBuffer: true,
  });
  const rapporto = Math.min(window.devicePixelRatio || 1, 2);
  renderer.setPixelRatio(rapporto);
  renderer.domElement.style.display = "block";
  ospite.appendChild(renderer.domElement);

  const scena = new THREE.Scene();
  /* 38° e la camera a (0, 0.7, 3.5): il riferimento guarda i gusci da poco
     sopra l'equatore, ed e' cio' che rende visibile la fascia di scansione
     quando attraversa il polo. Di fronte non si vedrebbe passare. */
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0.7, 3.5);
  camera.lookAt(0, 0, 0);

  const daButtare = [];
  const tieni = (o) => { daButtare.push(o); return o; };

  const gusci = GUSCI.map((cfg, k) => {
    const geo = tieni(new THREE.IcosahedronGeometry(cfg.raggio, 4));
    const uni = {
      uTempo: { value: 0 }, uAmp: { value: 0 }, uFase: { value: cfg.fase },
      uFreqK: { value: cfg.freqK }, uOp: { value: cfg.opacita },
      uFreq: { value: 1.9 }, uSpinta: { value: 0.14 },
      uTinta: { value: new THREE.Vector3(0.14, 0.58, 0.86) },
      uCaldo: { value: new THREE.Vector3(0.72, 0.98, 1.0) },
      uBagliore: { value: 0.62 },
      uScan: { value: -2 }, uScatto: { value: 0 }, uOver: { value: 0 },
      uCollasso: { value: 0 }, uNascita: { value: 1 }, uRet: { value: 0.3 },
      uSil: { value: new THREE.Vector4(-9, -9, -9, -9) },
      uSilAmp: { value: new THREE.Vector4(0, 0, 0, 0) },
      uParla: { value: 0 }, uUrto: { value: -1 },
    };
    const mat = tieni(new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: uni, vertexShader: VERTEX, fragmentShader: FRAG_GUSCIO,
    }));
    const g = new THREE.Group();
    g.add(new THREE.Mesh(geo, mat));
    if (cfg.reticolo) {
      /* Il reticolo solo sul guscio interno: sui tre diventa una nuvola di
         segmenti in cui non si legge piu' nessuna superficie. */
      const mr = tieni(new THREE.ShaderMaterial({
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
        uniforms: uni, vertexShader: VERTEX, fragmentShader: FRAG_RETICOLO,
      }));
      g.add(new THREE.LineSegments(tieni(new THREE.WireframeGeometry(geo)), mr));
    }
    scena.add(g);
    return { g, uni, velocita: 0.08 + k * 0.05, vertici: geo.attributes.position.count };
  });

  // ── La catena ────────────────────────────────────────────────────────────
  const quadScena = new THREE.Scene();
  const quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const quad = new THREE.Mesh(tieni(new THREE.PlaneGeometry(2, 2)), null);
  quadScena.add(quad);

  const matSoglia = tieni(new THREE.ShaderMaterial({
    uniforms: { tD: { value: null }, uSoglia: { value: 0.16 } }, vertexShader: VS_QUAD,
    fragmentShader: "uniform sampler2D tD; uniform float uSoglia; varying vec2 vUv; void main(){ vec4 c = texture2D(tD, vUv); float l = dot(c.rgb, vec3(0.299,0.587,0.114)); float k = max(0.0, l - uSoglia) / max(l, 1e-4); gl_FragColor = vec4(c.rgb * k, 1.0); }",
  }));
  const matSfoca = tieni(new THREE.ShaderMaterial({
    uniforms: { tD: { value: null }, uDir: { value: new THREE.Vector2(1, 0) },
                uTexel: { value: new THREE.Vector2(1, 1) } }, vertexShader: VS_QUAD,
    fragmentShader: [
      "uniform sampler2D tD; uniform vec2 uDir; uniform vec2 uTexel; varying vec2 vUv;",
      "void main(){ vec2 o = uDir * uTexel;",
      "  vec4 s = texture2D(tD, vUv) * 0.2270270270;",
      "  s += texture2D(tD, vUv + o * 1.3846153846) * 0.3162162162;",
      "  s += texture2D(tD, vUv - o * 1.3846153846) * 0.3162162162;",
      "  s += texture2D(tD, vUv + o * 3.2307692308) * 0.0702702703;",
      "  s += texture2D(tD, vUv - o * 3.2307692308) * 0.0702702703;",
      "  gl_FragColor = s; }",
    ].join("\n"),
  }));
  const matComp = tieni(new THREE.ShaderMaterial({
    transparent: true,
    uniforms: { tBase: { value: null }, tBloom: { value: null },
                uInt: { value: 1.35 }, uRifr: { value: 1 }, uAber: { value: 1 } },
    vertexShader: VS_QUAD,
    fragmentShader: [
      "uniform sampler2D tBase; uniform sampler2D tBloom; uniform float uInt; uniform float uRifr; uniform float uAber; varying vec2 vUv;",
      "void main(){",
      "  vec2 ctr = vUv - 0.5;",
      "  float r = length(ctr) * 2.0;",
      "  vec2 dir = r > 0.0001 ? ctr / (r * 0.5) : vec2(0.0);",
      "  float lente = pow(clamp(r, 0.0, 1.0), 3.4) * uRifr;",
      "  vec2 uvR = vUv - dir * lente * 0.030;",
      "  vec2 uvG = vUv - dir * lente * 0.038;",
      "  vec2 uvB = vUv - dir * lente * 0.047;",
      "  float ab = pow(clamp(r, 0.0, 1.0), 2.2) * uAber * 0.006;",
      "  vec4 b;",
      "  b.r = texture2D(tBase, uvR - dir * ab).r;",
      "  b.g = texture2D(tBase, uvG).g;",
      "  b.b = texture2D(tBase, uvB + dir * ab).b;",
      "  b.a = texture2D(tBase, uvG).a;",
      "  vec3 g;",
      "  g.r = texture2D(tBloom, uvR - dir * ab * 1.6).r;",
      "  g.g = texture2D(tBloom, uvG).g;",
      "  g.b = texture2D(tBloom, uvB + dir * ab * 1.6).b;",
      "  g *= uInt;",
      "  vec3 c = b.rgb * 1.7 + g;",
      "  c = c / (c + vec3(0.82)) * 1.62;",
      "  float bordo = smoothstep(0.72, 0.99, r) * (1.0 - smoothstep(0.99, 1.0, r));",
      "  c += vec3(0.34, 0.72, 0.88) * bordo * 0.10 * uRifr;",
      "  c *= 1.0 - 0.32 * pow(clamp(r * 0.75, 0.0, 1.0), 2.8);",
      "  float a = clamp(max(max(c.r, c.g), c.b) * 1.35 + b.a * 0.4, 0.0, 1.0);",
      "  gl_FragColor = vec4(c, a);",
      "}",
    ].join("\n"),
  }));
  const matScia = tieni(new THREE.ShaderMaterial({
    transparent: true,
    uniforms: { tNuovo: { value: null }, tVecchio: { value: null }, uDecadi: { value: 0.88 } },
    vertexShader: VS_QUAD,
    fragmentShader: [
      "uniform sampler2D tNuovo; uniform sampler2D tVecchio; uniform float uDecadi; varying vec2 vUv;",
      "void main(){ vec4 n = texture2D(tNuovo, vUv); vec4 o = texture2D(tVecchio, vUv);",
      "  gl_FragColor = max(n, o * uDecadi); }",
    ].join("\n"),
  }));

  let rtA = null, rtB = null, rtC = null, rtT1 = null, rtT2 = null;
  let sciaFlip = false;
  let W = 0;
  const tempi = [];

  function misura(px) {
    const nuovo = Math.max(32, Math.round(px));
    if (nuovo === W) return;
    W = nuovo;
    renderer.setSize(W, W, false);
    renderer.domElement.style.width = W + "px";
    renderer.domElement.style.height = W + "px";
    const R = Math.round(W * rapporto);
    const mezzo = { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, format: THREE.RGBAFormat };
    for (const rt of [rtA, rtB, rtC, rtT1, rtT2]) if (rt) rt.dispose();
    rtA = new THREE.WebGLRenderTarget(R, R, { ...mezzo, depthBuffer: true });
    rtB = new THREE.WebGLRenderTarget(Math.round(R / 2), Math.round(R / 2), mezzo);
    rtC = new THREE.WebGLRenderTarget(Math.round(R / 2), Math.round(R / 2), mezzo);
    rtT1 = new THREE.WebGLRenderTarget(R, R, mezzo);
    rtT2 = new THREE.WebGLRenderTarget(R, R, mezzo);
    /* ⚠️ LA SFOCATURA E' UNA FRAZIONE DELLA TELA, NON DUE PIXEL.
       Il riferimento scrive `2 / W` con W = 556: due pixel, cioe' lo 0,36 %
       della larghezza. Copiarlo alla lettera su una tela da 177 px da' l'1,1 %
       — tre volte tanto — e a quel punto i tre gusci si fondono in un anello
       luminoso unico. Reso e guardato: la struttura spariva.
       Qui il numero resta la FRAZIONE del riferimento a qualunque scala. */
    const FRAZIONE_SFOCATURA = 2 / 556;
    matSfoca.uniforms.uTexel.value.set(FRAZIONE_SFOCATURA, FRAZIONE_SFOCATURA);
  }

  /** Scrive negli uniform i valori del mescolatore. Non rende: rendere e'
   *  un'altra decisione, e la prende chi conta i fotogrammi. */
  function aggiorna(t, m) {
    for (let k = 0; k < gusci.length; k++) {
      const s = gusci[k], u = s.uni;
      u.uTempo.value = t;
      u.uAmp.value = m.amp;
      u.uFreq.value = m.freq;
      u.uSpinta.value = m.spinta;
      u.uBagliore.value = m.bagliore;
      u.uTinta.value.set(m.tinta[0], m.tinta[1], m.tinta[2]);
      u.uCaldo.value.set(m.caldo[0], m.caldo[1], m.caldo[2]);
      u.uScan.value = m.scanY;
      u.uScatto.value = m.scatto;
      u.uOver.value = m.sovraccarico;
      u.uCollasso.value = m.collasso;
      u.uNascita.value = Math.min(1, Math.max(0.02, m.nascita * 1.35 - k * 0.35));
      u.uRet.value = m.reticolo;
      u.uParla.value = m.parla;
      u.uUrto.value = m.urto;
      const sy = m.sillabe, sa = m.ampSillabe;
      u.uSil.value.set(sy[0], sy[1], sy[2], sy[3]);
      u.uSilAmp.value.set(sa[0], sa[1], sa[2], sa[3]);
      /* La deriva di SOVRACCARICO: i tre gusci perdono il passo l'uno
         dall'altro, ed e' l'unico posto dove le loro rotazioni divergono. */
      const deriva = m.sovraccarico * (k - 1) * 0.55;
      s.g.rotation.y = t * s.velocita * m.rotazione * (k % 2 ? -1 : 1)
        + deriva * Math.sin(t * 3.1);
      s.g.rotation.x = Math.sin(t * 0.16 + k) * 0.14 + deriva * 0.4;
    }
  }

  function passa(mat, destinazione) {
    quad.material = mat;
    renderer.setRenderTarget(destinazione);
    renderer.clear();
    renderer.render(quadScena, quadCam);
  }

  function rendi() {
    if (!rtA) return;
    const t0 = performance.now();
    renderer.setRenderTarget(rtA);
    renderer.clear();
    renderer.render(scena, camera);

    matSoglia.uniforms.tD.value = rtA.texture;
    passa(matSoglia, rtB);
    matSfoca.uniforms.tD.value = rtB.texture;
    matSfoca.uniforms.uDir.value.set(1, 0);
    passa(matSfoca, rtC);
    matSfoca.uniforms.tD.value = rtC.texture;
    matSfoca.uniforms.uDir.value.set(0, 1);
    passa(matSfoca, rtB);

    const nuovo = sciaFlip ? rtT1 : rtT2;
    const vecchio = sciaFlip ? rtT2 : rtT1;
    sciaFlip = !sciaFlip;
    matComp.uniforms.tBase.value = rtA.texture;
    matComp.uniforms.tBloom.value = rtB.texture;
    passa(matComp, nuovo);

    matScia.uniforms.tNuovo.value = nuovo.texture;
    matScia.uniforms.tVecchio.value = vecchio.texture;
    passa(matScia, null);

    const ms = performance.now() - t0;
    tempi.push(ms);
    if (tempi.length > 120) tempi.shift();
  }

  function mediana() {
    if (!tempi.length) return null;
    const v = [...tempi].sort((a, b) => a - b);
    return +v[Math.floor(v.length / 2)].toFixed(2);
  }

  return {
    tela: renderer.domElement,
    misura, aggiorna, rendi,
    terna,
    stato: () => ({
      lato: W,
      gusci: gusci.length,
      vertici: gusci.reduce((s, g) => s + g.vertici, 0),
      passaggi: 5,
      ms: mediana(),
      fotogrammi: tempi.length,
    }),
    smonta() {
      for (const rt of [rtA, rtB, rtC, rtT1, rtT2]) if (rt) rt.dispose();
      daButtare.forEach((o) => o.dispose && o.dispose());
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    },
  };
}
