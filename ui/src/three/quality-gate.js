/* Quality gate — SPEC §11.11. Codice che gira, non una checklist da leggere.
 *
 * Due correzioni rispetto al codice di §11.11, entrambe trovate facendolo
 * girare invece che leggendolo. Le dichiaro qui perche' fra sei mesi la
 * differenza fra questo file e la specifica deve avere una spiegazione
 * scritta accanto, non da ricostruire.
 *
 * ── 1. «geometria degenere» boccia il ReactorRing di §11.10 ────────────────
 * §11.11 fallisce se una qualunque dimensione del bounding box e' zero. Ma
 * l'anello che §11.10 mostra come ESEMPIO di componente parametrico ha tutti
 * i vertici a z = 0: e' piatto per costruzione, ed e' giusto che lo sia —
 * §22 lo vuole reso in SVG. Il codice di §11.11 boccerebbe l'esempio della
 * sezione precedente.
 *
 * Correzione: la degenerazione dipende da quante dimensioni sono nulle e da
 * quante il componente ne dichiara. Un componente 2D DEVE essere piatto
 * (esattamente un asse nullo); uno 3D non deve esserlo (nessun asse nullo).
 * Cosi' il controllo diventa piu' severo, non meno: prima un componente 3D
 * degenerato su un piano passava se aveva estensione in tre assi solo per
 * caso, e un componente 2D non poteva passare affatto.
 *
 * ── 3. Un componente traslato via passava indisturbato ─────────────────────
 * §11.11 misura solo le ESTENSIONI. Un componente spostato di nove metri
 * lungo un asse ha le stesse estensioni di uno al suo posto: il gate lo
 * approvava, e il componente finiva fuori dall'inquadratura senza che niente
 * lo segnalasse. L'ha trovato `tests/eval_visual.py`, che prova il gate con
 * guasti veri invece di fidarsi.
 *
 * I componenti parametrici sono definiti attorno alla PROPRIA origine — la
 * collocazione la fa la composizione, non la geometria (vedi `anim/rings.js`).
 * Quindi il centro del bounding box deve stare vicino all'origine: piu' vicino
 * della meta' dell'ingombro del componente stesso.
 *
 * ── 2. La regola 7 di §11.10 non era imposta da nessuno ────────────────────
 * «Bounding box dichiarato e verificato.» §11.11 controlla che il bbox non
 * sia assurdo (< 5000 mm), il che intercetta una trasformazione sbagliata di
 * ordini di grandezza ma non una sbagliata del doppio. Il componente conosce
 * la propria misura attesa: la dichiara in `meta.bbox` e il gate la verifica.
 * Un fattore 2 in un raggio smette di essere invisibile.
 */

const LIMITS = { minVertices: 24, maxVertices: 20000, maxMaterials: 2, maxBBox: 5000 };

// Tolleranza sul bbox dichiarato: la discretizzazione in corde rende
// l'estensione reale un capello piu' piccola dell'arco vero. A 256 segmenti
// la freccia e' ~7.5e-5 del raggio; l'1% e' larghissimo per quello e stretto
// abbastanza per prendere qualunque errore di trasformazione.
const TOLLERANZA_BBOX = 0.01;
const TOLLERANZA_BBOX_MM = 0.1;

export function qualityGate(component, geometry, materials) {
  const fail = [];
  const n = geometry.getAttribute("position").count;
  if (n < LIMITS.minVertices) fail.push(`vertici ${n} < ${LIMITS.minVertices}`);
  if (n > LIMITS.maxVertices) fail.push(`vertici ${n} > ${LIMITS.maxVertices}`);
  if (materials.length > LIMITS.maxMaterials)
    fail.push(`materiali ${materials.length} > ${LIMITS.maxMaterials}`);

  geometry.computeBoundingBox();
  const bb = geometry.boundingBox;
  const dim = ["x", "y", "z"].map((a) => bb.max[a] - bb.min[a]);

  if (dim.some((d) => d > LIMITS.maxBBox))
    fail.push(`bbox ${dim.map((d) => d.toFixed(0))} — probabile errore di trasformazione`);
  if (dim.some((d) => !Number.isFinite(d))) fail.push("geometria con NaN");

  // Correzione 1 — vedi l'intestazione.
  const nulli = dim.filter((d) => d === 0).length;
  const dimensioni = component.meta?.dimensioni ?? 3;
  if (dimensioni === 2 && nulli !== 1)
    fail.push(
      nulli === 0
        ? "dichiarata 2D ma occupa tre assi — non e' piatta"
        : `geometria degenere: ${nulli} assi nulli su una 2D`
    );
  if (dimensioni === 3 && nulli > 0)
    fail.push(`geometria degenere: ${nulli} assi nulli su una 3D`);

  // Correzione 2 — §11.10 regola 7.
  const atteso = component.meta?.bbox;
  if (!atteso) {
    fail.push("bounding box non dichiarato — §11.10 regola 7");
  } else {
    // Un componente puo' ALZARE la tolleranza, dichiarando perche'. Il caso
    // vero e' la nuvola di punti: un campione discreto di una superficie
    // continua non tocca i propri estremi, e con poche centinaia di punti lo
    // scarto e' dell'ordine del 2%. Chiedere l'1% li' vorrebbe dire o
    // dichiarare un bbox misurato — cioe' verificare il codice con se stesso —
    // o rinunciare del tutto alla regola 7.
    const tolleranza = component.meta?.bboxTolleranza ?? TOLLERANZA_BBOX;
    for (const [i, a] of ["x", "y", "z"].entries()) {
      const scarto = Math.abs(dim[i] - atteso[a]);
      const ammesso = Math.max(TOLLERANZA_BBOX_MM, atteso[a] * tolleranza);
      if (scarto > ammesso)
        fail.push(
          `bbox.${a} misurato ${dim[i].toFixed(2)} mm, dichiarato ${atteso[a]} mm ` +
            `(scarto ${scarto.toFixed(2)} > ${ammesso.toFixed(2)})`
        );
    }
  }

  // Correzione 3 — vedi l'intestazione.
  const meta_ingombro = Math.max(...dim.filter(Number.isFinite), 0) / 2;
  for (const [i, a] of ["x", "y", "z"].entries()) {
    const centro = (bb.max[a] + bb.min[a]) / 2;
    if (Number.isFinite(centro) && Math.abs(centro) > meta_ingombro + TOLLERANZA_BBOX_MM) {
      fail.push(
        `centro fuori origine su ${a}: ${centro.toFixed(1)} mm, oltre la meta' ` +
        `dell'ingombro (${meta_ingombro.toFixed(1)} mm) — la collocazione e' della ` +
        `composizione, non della geometria`
      );
    }
    void i;
  }

  if (!component.meta?.name || !component.meta?.version)
    fail.push("componente senza name/version");
  if (!component.params || Object.keys(component.params).length === 0)
    fail.push("componente senza tabella parametri — geometria non parametrica");

  if (fail.length)
    throw new Error(
      `QUALITY GATE FALLITO — ${component.meta?.name ?? "anonimo"}\n  ` + fail.join("\n  ")
    );
  return true;
}

export { LIMITS };
