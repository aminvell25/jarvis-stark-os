/* Picking accelerato — SPEC §14, three-mesh-bvh.
 *
 * Il raycast di three.js prova ogni triangolo della geometria. Su una nuvola
 * di duecento punti non si nota; su una mesh vera, a ogni fotogramma e con la
 * mano che si muove, e' il costo che mangia il budget di §10.4. three-mesh-bvh
 * costruisce un albero e lo riduce di ordini di grandezza.
 *
 * ── Dove sta il confine (R55 del piano di Fase 7) ──────────────────────────
 * Il core manda coordinate NORMALIZZATE del fotogramma — due numeri fra 0 e 1
 * — e non sa nulla della scena. Qui si convertono in coordinate di clip e si
 * tira il raggio. Nessuna coordinata di scena attraversa il socket, e nessun
 * fotogramma entra nel renderer.
 *
 * ── Lo specchio ────────────────────────────────────────────────────────────
 * La telecamera guarda l'utente, quindi la sua destra e' la sinistra
 * dell'immagine. Senza `specchia`, indicare a destra muoverebbe il puntatore a
 * sinistra — e nessuno lo chiamerebbe un bug del picking.
 */

import * as THREE from "three";
import { MeshBVH, acceleratedRaycast } from "three-mesh-bvh";

// Una volta sola, all'import: da qui in poi ogni Mesh con un boundsTree usa
// il raycast accelerato senza che il chiamante debba saperlo.
THREE.Mesh.prototype.raycast = acceleratedRaycast;

export function accelera(mesh) {
  if (!mesh.geometry.boundsTree) {
    mesh.geometry.boundsTree = new MeshBVH(mesh.geometry);
  }
  return mesh;
}

export function creaPicker(camera) {
  const raggio = new THREE.Raycaster();
  // `firstHitOnly` e' il motivo per cui l'albero paga: senza, il BVH raccoglie
  // comunque tutte le intersezioni e poi le ordina.
  raggio.firstHitOnly = true;
  const punto = new THREE.Vector2();

  return {
    /** @param {number} nx 0..1 sul fotogramma · @param {number} ny 0..1 */
    punta(nx, ny, oggetti, { specchia = true } = {}) {
      const x = specchia ? 1 - nx : nx;
      // Da 0..1 dell'immagine a -1..+1 del clip space, con Y ribaltata.
      punto.set(x * 2 - 1, -(ny * 2 - 1));
      raggio.setFromCamera(punto, camera);
      const colpi = raggio.intersectObjects(oggetti, true);
      return colpi.length ? colpi[0] : null;
    },
  };
}
