/* Modello 3D — SPEC §17.1, ADR-014.
 *
 * Il pezzo che il CORE ha generato e scritto su disco. Qui non si genera
 * niente e non si tocca il disco: arriva `model3d.preview` con i vertici, gli
 * indici e gli spigoli, e questo pannello li mostra. La verita' e' il file, e
 * il piede ne porta il percorso RISOLTO — lo stesso che l'utente ha
 * approvato nella conferma di §6.2.
 *
 * ⚠️ **Stato vuoto esplicito, non un pezzo di esempio.** L'invariante 23 non
 * ammette segnaposto: finche' nessuno ha chiesto un modello, questo pannello
 * dice che non ce n'e' uno e come chiederlo. Un cubo di prova sarebbe la cosa
 * piu' facile da mettere qui, ed e' esattamente cio' che §11.9 vieta.
 *
 * Due materiali, come §11.10 regola 6: la faccia e gli spigoli. La faccia da
 * sola e' una silhouette — `MeshBasicMaterial` non ha luci — e sono gli
 * spigoli in `Line2` a far leggere la forma.
 */

import { creaScena, inquadra } from "../three/scena.js";
import { ModelloRicevuto, daPreview } from "../three/components/modello-ricevuto.js";
import { qualityGate } from "../three/quality-gate.js";
import { versoBufferGeometry, versoLinee, materialiPerRuolo } from "../three/buffer.js";
import { tok } from "../style/tokens.js";

export const meta = { nome: "modello", versione: "1" };

export const css = `
.pnl-mdl {
  --aug-tl: var(--s-3);
  --aug-br: var(--s-3);
  /* Come il globo: l'anello di augmented-ui e' la cornice sui quattro lati, e
     §10.5 la vieta. Si toglie l'inchiostro, non l'anello. */
  --aug-border-bg: transparent;
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  /* §10.5 regola 1 — il pannello e' un gradino di luminanza sul pavimento. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-mdl__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
.pnl-mdl__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-mdl__id, .pnl-mdl__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
.pnl-mdl__ctrl { letter-spacing: 0.16em; }

.pnl-mdl__corpo { position: relative; display: grid; min-height: 0; overflow: hidden; }
/* Il campo e' piu' scuro della stanza, per la stessa ragione misurata sul
   globo: uno spazio dipinto col colore del proprio telaio non e' un campo. Il
   colore lo mette il CSS e non WebGL — il renderer resta alpha: true, o
   l'invariante 18 cadrebbe dove e' piu' facile non accorgersene. */
.pnl-mdl__tela {
  position: relative;
  min-width: 0;
  min-height: 0;
  cursor: grab;
  touch-action: none;
  background: var(--bg-abyss);
}
.pnl-mdl__tela[data-presa] { cursor: grabbing; }

.pnl-mdl__quote { position: absolute; inset: 0; pointer-events: none; }
.pnl-mdl__quota {
  position: absolute;
  transform: translate(-50%, -50%);
  padding: 0 var(--s-1);
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--cy-100);
  /* La quota sta SOPRA il pezzo, e senza un fondo si legge sul campo e
     sparisce sulla faccia. Il fondo e' quello del CAMPO — nessun colore
     nuovo, invariante 18 — cosi' dove il pezzo non c'e' l'etichetta non si
     vede affatto, e dove c'e' si stacca. */
  background: var(--bg-abyss);
}

.pnl-mdl__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
/* ⚠️ Qui c'era direction: rtl per far ellissare la TESTA del percorso e
   tenere il nome del file. Guardato nello scatto: la coda diventava
   «…glb./=» — con quella regola i segni di punteggiatura si riordinano, e
   quello che si legge non e' piu' il percorso. Adesso il piede mostra le
   ultime due parti, che sono l'informazione (dove e come si chiama), e il
   percorso RISOLTO intero sta nell'attributo title: e' quello che l'utente
   ha approvato nella conferma, e non si perde. */
.pnl-mdl__file {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pnl-mdl__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  line-height: 1.7;
  color: var(--txt-ghost);
}
.pnl-mdl__come { display: block; color: var(--cy-300); }
.pnl-mdl[data-stato="vuoto"] .pnl-mdl__corpo { display: none; }
.pnl-mdl[data-stato="vuoto"] .pnl-mdl__vuoto { display: block; }
.pnl-mdl[data-stato="vuoto"] .pnl-mdl__piede { visibility: hidden; }
`;

const mm = (v) => `${Number(v).toFixed(v % 1 ? 1 : 0)}`;

/** Le posizioni viste da fermo, cioe' con la rotazione del gruppo gia' dentro.
 *
 * Serve a `inquadra()`, che vuole l'ingombro di cio' che la camera vedra': un
 * solido girato occupa la propria diagonale, non la propria faccia. */
function ruotate(THREE, posizioni, rotazione) {
  const fuori = new Float32Array(posizioni.length);
  const v = new THREE.Vector3();
  for (let i = 0; i < posizioni.length; i += 3) {
    v.set(posizioni[i], posizioni[i + 1], posizioni[i + 2]).applyEuler(rotazione);
    fuori[i] = v.x; fuori[i + 1] = v.y; fuori[i + 2] = v.z;
  }
  return fuori;
}

/* ⚠️ **Qui c'era un rientro delle quote dentro la tela, ed e' stato TOLTO.**
 *
 * L'avevo scritto guardando lo scatto del tubo: la quota della profondita'
 * sembrava cadere sotto il bordo del riquadro. Misurando i rettangoli con e
 * senza — `getBoundingClientRect` di ogni quota contro quello della propria
 * tela — le quote fuori sono **zero in entrambi i casi**: quella quota sta a
 * tre pixel dal bordo, e tre pixel dentro sono dentro.
 *
 * Era codice corretto per un difetto che non c'era, cioe' una riga che non
 * scatta mai. §11.7 regola 4 vale in tutt'e due i versi: non si dichiara
 * verde cio' che non si e' misurato, e non si dichiara riparato cio' che non
 * era rotto. Se un giorno una forma nuova mandera' una quota fuori, sara' uno
 * scatto a dirlo e il rientro tornera' con la misura dietro.
 */

/* ⚠️ **Qui c'era `puntiQuota()`, che annotava sempre i tre lati del bounding
 * box, ed e' stato TOLTO.** Su una piastra funzionava — il bbox e' il pezzo —
 * e su un tubo piegato no: quei tre numeri sono un RISULTATO (177,6 x 113,1 x
 * 153,6) appesi a tre angoli che stanno nel vuoto. Un disegno di un tubo
 * scrive il diametro e il raggio di piega, che sono i numeri che si ordinano.
 *
 * Chi conosce il pezzo e' chi lo genera, e adesso le quote arrivano dal core
 * dentro `model3d.preview`, gia' scritte e gia' ancorate. Questo file le
 * proietta e basta — che e' tutto quello che il renderer puo' sapere.
 */

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-mdl";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-mdl__testa">
      <span class="pnl-mdl__etichetta">Modello 3D</span>
      <span class="pnl-mdl__id">MDL_F17 · ver ${meta.versione}</span>
      <span class="pnl-mdl__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-mdl__corpo">
      <div class="pnl-mdl__tela"><div class="pnl-mdl__quote"></div></div>
    </div>
    <div class="pnl-mdl__vuoto">
      NESSUN MODELLO GENERATO
      <span class="pnl-mdl__come">di' «genera un'estrusione»</span>
    </div>
    <div class="pnl-mdl__piede">
      <span class="pnl-mdl__file"></span>
      <span class="pnl-mdl__misura"></span>
      <span class="pnl-mdl__conteggio"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const tela = radice.querySelector(".pnl-mdl__tela");
  const quote = radice.querySelector(".pnl-mdl__quote");
  let scena = null;
  let corrente = null;
  let giroY = -0.6;
  let giroX = -0.42;

  function disegna(msg) {
    let d;
    try {
      d = daPreview(msg);
    } catch (e) {
      // Un messaggio storto non e' un pannello rotto: e' uno stato vuoto con
      // una riga nel giornale di bordo. §11.9 — mai un pezzo inventato al suo
      // posto.
      console.error("model3d.preview illeggibile", e);
      radice.dataset.stato = "vuoto";
      return;
    }
    corrente = { ...d, file: msg.file, triangoli: msg.triangoli };
    radice.dataset.stato = "pieno";
    scena?.smonta();
    quote.replaceChildren();
    scena = creaScena(tela, { fov: 34 });
    const { THREE, scena: s3, camera } = scena;

    const componente = new ModelloRicevuto(d);
    const geometria = componente.build();
    const spigoli = componente.constructionLines();

    /* ⚠️ Ruolo «linea», non «costruzione», e la differenza si e' VISTA nello
     * scatto: `costruzione` e' `--cy-900` a mezzo pixel — il grigio degli assi
     * e delle quote di riferimento — e sopra una faccia `--fill-2` gli spigoli
     * sparivano, lasciando una silhouette piatta. Questi spigoli non sono un
     * aiuto al disegno: sono il pezzo. */
    const materiali = materialiPerRuolo(["linea"], {
      larghezza: scena.larghezza, altezza: scena.altezza,
    });
    for (const m of materiali.values()) scena.seguiLinea(m);

    /* La faccia. `MeshBasicMaterial` non ha luci — nel progetto non ce ne sono,
       e non e' una mancanza: §10 costruisce il volume col contrasto, non con
       l'illuminazione. Il pezzo si legge perche' gli spigoli ci passano sopra. */
    const materialeFaccia = new THREE.MeshBasicMaterial({
      color: new THREE.Color(tok("--fill-2")),
      side: THREE.DoubleSide,
    });
    // Esattamente due materiali — §11.10 regola 6.
    qualityGate(componente, geometria, [materialeFaccia, ...materiali.values()]);

    const gruppo = new THREE.Group();
    gruppo.add(new THREE.Mesh(versoBufferGeometry(geometria), materialeFaccia));
    for (const o of versoLinee(spigoli, materiali)) gruppo.add(o);
    s3.add(gruppo);

    applicaGiro(gruppo);
    /* ⚠️ **Si inquadra DOPO aver girato, e su vertici GIRATI.**
     * Guardato nello scatto del 2 settembre 2026: il pezzo usciva dal
     * riquadro in alto e a destra. `inquadra()` calcolava la distanza
     * sull'ingombro FRONTALE — 120x80 — mentre il gruppo era gia' ruotato di
     * 0,6 e 0,42 radianti, e la diagonale di un parallelepipedo girato e'
     * piu' larga della sua faccia. Non e' un margine da alzare: e' l'ingombro
     * sbagliato. */
    inquadra(THREE, camera, ruotate(THREE, geometria.posizioni, gruppo.rotation),
             { x: 0, y: 0, z: 1 }, 1.18);
    scena.rendi();
    aggiornaQuote();
    piede();

    /* Si prende in mano, come il globo: un pezzo che non si gira mostra sempre
       la stessa faccia, e un'estrusione vista di fronte e' un rettangolo. */
    let presa = null;
    tela.addEventListener("pointerdown", (e) => {
      presa = { x: e.clientX, y: e.clientY, gy: giroY, gx: giroX };
      tela.dataset.presa = "1";
      tela.setPointerCapture(e.pointerId);
    });
    tela.addEventListener("pointermove", (e) => {
      if (!presa) return;
      giroY = presa.gy + (e.clientX - presa.x) * 0.008;
      giroX = Math.max(-1.4, Math.min(1.4, presa.gx + (e.clientY - presa.y) * 0.008));
      applicaGiro(gruppo);
      scena.rendi();
      aggiornaQuote();
    });
    for (const ev of ["pointerup", "pointercancel"]) {
      tela.addEventListener(ev, () => { presa = null; delete tela.dataset.presa; });
    }

    function applicaGiro(g) {
      g.rotation.set(giroX, giroY, 0);
      // `invalida()` e non un render diretto: la scena rende A RICHIESTA, e
      // senza questa riga il primo giro sarebbe l'unico a vedersi.
      scena.invalida();
    }

    function aggiornaQuote() {
      /* Le tre quote dell'ingombro, sui vertici veri del bounding box. Sono
         DATI — i millimetri che il core ha generato — non decorazione: §11.10
         regola 3 le chiama quote, e senza un pezzo a schermo non ha scala. */
      quote.replaceChildren();
      for (const q of corrente.quote ?? []) {
        const v = new THREE.Vector3(...q.punto).applyEuler(gruppo.rotation);
        const s = scena.proietta(v.x, v.y, v.z);
        if (!s.davanti) continue;
        const el = document.createElement("span");
        el.className = "pnl-mdl__quota";
        el.textContent = q.testo;
        el.style.left = `${s.x}px`;
        el.style.top = `${s.y}px`;
        quote.appendChild(el);
      }
    }
  }

  function piede() {
    if (!corrente) return;
    const b = corrente.bbox;
    const file = radice.querySelector(".pnl-mdl__file");
    const percorso = corrente.file ?? "";
    // Le ultime due parti: la cartella e il nome. Il percorso RISOLTO intero
    // resta nel `title` — e' quello che l'utente ha approvato (§6.2).
    file.textContent = percorso.split("/").slice(-2).join("/");
    file.title = percorso;
    radice.querySelector(".pnl-mdl__misura").textContent =
      `${mm(b.x)} × ${mm(b.y)} × ${mm(b.z)} mm`;
    radice.querySelector(".pnl-mdl__conteggio").textContent =
      `${corrente.posizioni.length / 3} vert · ${corrente.triangoli ?? corrente.indici.length / 3} tri`;
  }

  return {
    radice,
    aggiorna(msg) {
      if (msg?.topic && msg.topic !== "model3d.preview") return;
      if (!msg?.posizioni_b64) { radice.dataset.stato = "vuoto"; return; }
      disegna(msg);
    },
    smonta() { scena?.smonta(); },
  };
}
