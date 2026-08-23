/* Geometria neutra -> three.js. L'unico file di `three/` che importa three.
 *
 * E' deliberato: `component.js`, `geometry.js`, `quality-gate.js`, `svg.js` e
 * ogni generatore in `math/` e `components/` restano puri, e quindi girano in
 * Node. `tests/eval_visual.py` puo' costruire ogni geometria e passarla al
 * gate senza un contesto WebGL — che in un test headless non ci sarebbe, e che
 * renderebbe la verifica della geometria dipendente da una GPU.
 *
 * ── Perche' Line2 e non LineSegments/LineBasicMaterial ─────────────────────
 * Invariante 21, e non e' una preferenza: `LineBasicMaterial.linewidth` viene
 * IGNORATO da quasi tutte le implementazioni OpenGL. Con quel materiale ogni
 * linea resta a 1px e il pilastro «hairline con densita' variabile» di §11.1
 * non si vede. Line2 disegna strisce di triangoli e lo spessore lo rispetta.
 *
 * Il prezzo e' `LineMaterial.resolution`: lo shader converte lo spessore da
 * pixel a clip space e per farlo deve sapere quanto e' grande il viewport.
 * Se nessuno gliela dice resta (0,0) e le linee spariscono. Va aggiornata a
 * ogni ridimensionamento — `aggiornaRisoluzione()`.
 */

import * as THREE from "three";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";

import { tok } from "../style/tokens.js";

/** Geometria neutra -> BufferGeometry, per i Points. */
export function versoBufferGeometry(geometria) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(geometria.posizioni, 3));
  // Gli indici viaggiano con la geometria quando c'e' una superficie: senza,
  // i triangoli non esistono e il mesh disegna una nuvola di vertici.
  if (geometria.indici) g.setIndex(new THREE.BufferAttribute(geometria.indici, 1));
  return g;
}

/** Il mesh di un gruppo «superficie».
 *
 * ⚠️ Sta accanto a `versoLinee` e non dentro: una superficie e una linea non si
 * disegnano con la stessa primitiva, e mescolarle in una funzione sola
 * vorrebbe dire un ramo che sceglie — cioe' due funzioni scritte in una.
 *
 * Il colore per vertice non lo decide questo modulo: lo passa chi monta,
 * perche' e' un DATO. Sul globo e' il prodotto scalare col punto subsolare,
 * cioe' giorno e notte.
 */
export function versoSuperficie(geometria, colori) {
  if (!geometria.gruppi.some((g) => g.ruolo === "superficie")) return null;
  const g = versoBufferGeometry(geometria);
  if (colori) g.setAttribute("color", new THREE.BufferAttribute(colori, 3));
  return new THREE.Mesh(
    g,
    new THREE.MeshBasicMaterial({
      vertexColors: Boolean(colori),
      side: THREE.FrontSide,
    })
  );
}

/** Un materiale per ruolo, mai piu' di due — §11.10 regola 6. */
export function materialiPerRuolo(ruoli, { larghezza, altezza }) {
  const stile = {
    linea: { colore: tok("--cy-500"), spessore: 1 },
    costruzione: { colore: tok("--cy-900"), spessore: 0.5 },
    // Il terminatore solare: accento caldo perche' significa qualcosa —
    // dove finisce il giorno — ed e' una linea sola, cioe' una frazione
    // trascurabile della superficie (§11.6 regola 2).
    sole: { colore: tok("--amber"), spessore: 1 },
  };
  const fuori = new Map();
  for (const r of ruoli) {
    const s = stile[r];
    if (!s) throw new Error(`ruolo senza stile dichiarato: ${r}`);
    const m = new LineMaterial({ color: new THREE.Color(s.colore), linewidth: s.spessore });
    m.resolution.set(larghezza, altezza);
    fuori.set(r, m);
  }
  return fuori;
}

export function aggiornaRisoluzione(materiali, larghezza, altezza) {
  for (const m of materiali.values()) m.resolution.set(larghezza, altezza);
}

/** Geometria neutra -> oggetti three.js pronti da aggiungere alla scena.
 *
 * I gruppi da due vertici — i tick, i raggi, le quote — finiscono TUTTI in un
 * solo LineSegments2 invece che in un Line2 ciascuno. Quarantotto tick sono
 * quarantotto draw call altrimenti, e il budget di §10.4 e' 8 ms per l'intera
 * scena three.js, non per componente.
 */
export function versoLinee(geometria, materiali) {
  const oggetti = [];
  const segmenti = new Map(); // ruolo -> numeri accumulati

  for (const g of geometria.gruppi) {
    if (g.conteggio < 2) continue;
    const punti = [];
    for (let i = 0; i < g.conteggio; i++) {
      const v = geometria.vertice(g.inizio + i);
      punti.push(v.x, v.y, v.z);
    }
    if (g.chiuso) {
      const p = geometria.vertice(g.inizio);
      punti.push(p.x, p.y, p.z);
    }

    if (g.conteggio === 2) {
      if (!segmenti.has(g.ruolo)) segmenti.set(g.ruolo, []);
      segmenti.get(g.ruolo).push(...punti);
      continue;
    }

    const lg = new LineGeometry();
    lg.setPositions(punti);
    const linea = new Line2(lg, materiale(materiali, g.ruolo));
    linea.computeLineDistances();
    oggetti.push(linea);
  }

  for (const [ruolo, punti] of segmenti) {
    const sg = new LineSegmentsGeometry();
    sg.setPositions(punti);
    oggetti.push(new LineSegments2(sg, materiale(materiali, ruolo)));
  }

  return oggetti;
}

function materiale(materiali, ruolo) {
  const m = materiali.get(ruolo);
  if (!m) throw new Error(`nessun materiale per il ruolo "${ruolo}"`);
  return m;
}
