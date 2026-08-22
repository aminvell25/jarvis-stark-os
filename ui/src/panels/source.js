/* Core sorgente — SPEC §13 («file reali del progetto», Fase 5),
 * riferimento famiglia-a/06-access-server-trace-archive.png, riquadro
 * «SERVER TRACE».
 *
 * Ogni punto e' un file vero del progetto. La posizione viene dall'hash del
 * percorso (vedi `three/math/pointcloud.js`), la fascia di latitudine dalla
 * cartella di primo livello, il colore dalla dimensione del file. Niente e'
 * casuale e niente e' inventato: §11.9.
 *
 * ── I due materiali ────────────────────────────────────────────────────────
 * §11.10 regola 6 ne concede due, e sono esattamente due: `PointsMaterial` per
 * i file, `LineMaterial` per equatore e meridiano. Le linee usano `Line2`
 * perche' l'invariante 21 lo impone — con `LineBasicMaterial` lo spessore
 * verrebbe ignorato e resterebbero a 1px su qualunque schermo.
 *
 * ── Perche' il colore e non la dimensione del punto ────────────────────────
 * `PointsMaterial` ha una dimensione sola per tutti i punti: variarla per file
 * richiederebbe uno shader scritto a mano, e uno shader vuole i colori come
 * letterali — l'invariante 18 al primo passo falso. I colori per vertice, che
 * il materiale standard supporta, vengono invece dalla palette dei token.
 *
 * ── Il testo ───────────────────────────────────────────────────────────────
 * Nessuna etichetta e' rasterizzata in WebGL (invariante 20). I nomi dei file
 * piu' grandi sono `<span>` posizionati proiettando il punto 3D sullo schermo:
 * restano selezionabili, nitidi e presi dai token.
 */

import { creaScena, inquadra } from "../three/scena.js";
import { PointCloud } from "../three/math/pointcloud.js";
import { qualityGate } from "../three/quality-gate.js";
import { versoBufferGeometry, versoLinee, materialiPerRuolo } from "../three/buffer.js";
import { tok } from "../style/tokens.js";

export const meta = { nome: "source", versione: "1" };

/** Fasce di dimensione, in byte, e il token che le colora.
 *
 * Cinque gradini come i corpi tipografici: la palette ha cinque passi di
 * ciano e non serve inventarne altri.
 */
const SCALA = [
  { fino: 1_024, token: "--cy-900" },
  { fino: 4_096, token: "--cy-700" },
  { fino: 16_384, token: "--cy-500" },
  { fino: 65_536, token: "--cy-300" },
  { fino: Infinity, token: "--cy-100" },
];

const ETICHETTE = 3; // quanti file nominare: i piu' grandi

export const css = `
.pnl-src {
  /* §10.5 — l'anello di augmented-ui E' la cornice sui quattro lati.
     Misurato sullo scatto del contenitore radice: 4 px pieni di --cy-900 su
     TUTTI E QUATTRO i lati, cioe' esattamente il tratto che zero pannelli su
     sette hanno nel riferimento. E dipinge SOPRA i figli: con la testata
     diventata chiara ne mangiava 4 px su tre lati.
     Si toglie l'INCHIOSTRO, non l'anello — la parola che lo accende sta nel
     markup, accanto ai tagli a 45 gradi, e di li' non si tocca. «transparent»
     qui e' assenza, non un colore scelto: la stessa lettura che l'audit da' a
     rgba(0,0,0,0). Toglierlo del tutto NON spegne il tratto: augmented-ui
     ripiega su currentColor e lo riaccende a --txt-primary. */
  --aug-border-bg: transparent;
  --aug-tr: var(--s-3);
  --aug-bl: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  /* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
     Il corpo del riferimento sta a L 37 contro il pavimento a L 19, misurato
     #1e2631 a quattro quote diverse del calendario: e' --bg-raised esatto.
     Con --bg-panel (L 31) il salto era +12, meta' di quello misurato, e da
     ADR-010 i pannelli si sovrappongono: dodici punti non bastano a dire dove
     finisce uno e comincia quello sotto. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}

/* §10.5 regola 2 — la testata e' una SUPERFICIE, non una riga di testo con un
   filo sotto. Banda piena a --fill-1 (L 65,7, la luminanza misurata sulla
   testata del calendario): +29 L sul corpo, oltre il minimo di +19 richiesto.
   Si adotta la polarita' del calendario, testo chiaro su banda chiara — e'
   una scelta dichiarata in §10.5, non una misura.

   Il border-bottom hairline se ne va, e non per pulizia: separava due fondi
   IDENTICI, quindi era l'unica cosa che diceva dove finiva la testa. Adesso
   lo dice il gradino, e un filo in piu' sarebbe una cornice che ricomincia da
   un lato solo.

   Il padding non si tocca: la regola misura l'altezza della banda, il 6-9 %
   del pannello, e quella la fa il padding di adesso. */
.pnl-src__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}

/* ⚠️ I colori qui sotto sono ritarati sul fondo NUOVO. Il fondo della testa
   passa da L 31 a L 66: ogni rapporto misurato prima della rev 5.16 non vale
   piu', e due dei tre erano sotto soglia. */
.pnl-src__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  /* Era --cy-300, che su --fill-1 misura 6,20:1 e passerebbe. Ma l'etichetta
     e' cio' che si legge di sbieco su un pannello in secondo piano, e sulla
     banda nuova --txt-primary da' 8,06:1. Il ciano non si perde: resta dove
     porta un dato, cioe' la legenda delle fasce e i nomi dei file. */
  color: var(--txt-primary);
}
.pnl-src__id, .pnl-src__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  /* Era --txt-dim: su --fill-1 crolla a 2,73:1, ed e' testo a 8,5 px — cioe'
     illeggibile due volte. --icona da' 4,31:1 ed e' il token giusto anche di
     significato: matricola, versione e i tre glifi di controllo sono segni di
     servizio, non dati, e --icona e' il riempimento dei segni. */
  color: var(--icona);
}
.pnl-src__ctrl { letter-spacing: 0.16em; }

.pnl-src__corpo {
  position: relative;
  display: grid;
  grid-template-columns: 1fr auto;
  min-height: 0;
  overflow: hidden;
}
.pnl-src__tela { position: relative; min-width: 0; min-height: 0; overflow: hidden; }

/* Le etichette: DOM sopra la tela, posizionate proiettando il punto 3D. */
.pnl-src__nomi { position: absolute; inset: 0; pointer-events: none; }
.pnl-src__nome {
  position: absolute;
  transform: translate(var(--s-2), -50%);
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--cy-100);
}
.pnl-src__nome[data-verso="sinistra"] { transform: translate(calc(-100% - var(--s-2)), -50%); }
.pnl-src__nome::before {
  content: "";
  position: absolute;
  left: calc(var(--s-2) * -1);
  top: 50%;
  width: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-700);
}
.pnl-src__nome[data-verso="sinistra"]::before { left: auto; right: calc(var(--s-2) * -1); }

/* La legenda delle fasce: e' il dato che rende leggibile la nuvola, e da'
   densita' a una colonna che altrimenti sarebbe vuota (§11.6 regola 3). */
.pnl-src__fasce {
  display: grid;
  align-content: start;
  gap: var(--s-1);
  padding: var(--s-3);
  border-left: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-src__fascia { display: flex; justify-content: space-between; gap: var(--s-3); }
.pnl-src__fascia b { font-weight: 400; color: var(--cy-300); }

.pnl-src__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-src__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-src[data-stato="vuoto"] .pnl-src__corpo { display: none; }
.pnl-src[data-stato="vuoto"] .pnl-src__vuoto { display: block; }
`;

const byte = (n) =>
  n >= 1_048_576 ? `${(n / 1_048_576).toFixed(1)} MB`
  : n >= 1_024 ? `${(n / 1_024).toFixed(1)} kB`
  : `${n} B`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-src";
  radice.dataset.augmentedUi = "tr-clip bl-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-src__testa">
      <span class="pnl-src__etichetta">Core sorgente</span>
      <span class="pnl-src__id">SRC_C03 · ver ${meta.versione}</span>
      <span class="pnl-src__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-src__corpo">
      <div class="pnl-src__tela"><div class="pnl-src__nomi"></div></div>
      <div class="pnl-src__fasce"></div>
    </div>
    <div class="pnl-src__vuoto">NESSUNA SORGENTE COLLEGATA</div>
    <div class="pnl-src__piede">
      <span class="pnl-src__conteggio"></span>
      <span class="pnl-src__peso"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const tela = radice.querySelector(".pnl-src__tela");
  const nomi = radice.querySelector(".pnl-src__nomi");
  const elFasce = radice.querySelector(".pnl-src__fasce");

  let scena = null;
  let etichette = [];

  function disegna(elenco) {
    if (!elenco?.length) { radice.dataset.stato = "vuoto"; return; }
    radice.dataset.stato = "pieno";

    scena?.smonta();
    nomi.replaceChildren();
    scena = creaScena(tela, { fov: 34 });
    const { THREE, scena: s3, camera } = scena;

    const componente = new PointCloud({}, elenco);
    const geometria = componente.build();
    const costruzione = componente.constructionLines();

    const materiali = materialiPerRuolo(["costruzione"], {
      larghezza: scena.larghezza, altezza: scena.altezza,
    });
    for (const m of materiali.values()) scena.seguiLinea(m);

    const punti = versoBufferGeometry(geometria);
    const colori = new Float32Array(elenco.length * 3);
    const c = new THREE.Color();
    for (const [i, f] of elenco.entries()) {
      c.set(tok(SCALA.find((s) => f.bytes <= s.fino).token));
      colori[i * 3] = c.r; colori[i * 3 + 1] = c.g; colori[i * 3 + 2] = c.b;
    }
    punti.setAttribute("color", new THREE.BufferAttribute(colori, 3));

    const materialePunti = new THREE.PointsMaterial({
      size: 4.5, sizeAttenuation: true, vertexColors: true, transparent: false,
    });
    // Esattamente due materiali — §11.10 regola 6.
    qualityGate(componente, geometria, [materialePunti, ...materiali.values()]);

    s3.add(new THREE.Points(punti, materialePunti));
    for (const o of versoLinee(costruzione, materiali)) s3.add(o);

    // Sguardo leggermente dall'alto, come nel riferimento: da un punto di
    // vista equatoriale una sfera schiacciata sembra un disco.
    //
    // La distanza si CALCOLA dall'ingombro e dal campo visivo, non si sceglie
    // a occhio. Nella prima versione era un multiplo del raggio scritto a
    // mano: la nuvola usciva da tutti e quattro i lati.
    inquadra(THREE, camera, geometria.posizioni, { x: 0.5, y: 0.42, z: 1 });
    scena.invalida();
    scena.rendi();

    // Etichette: i tre file piu' grandi. Il testo resta nel DOM.
    const indici = elenco
      .map((f, i) => [i, f])
      .sort((a, b) => b[1].bytes - a[1].bytes)
      .slice(0, ETICHETTE);
    etichette = indici.map(([i, f]) => {
      const el = document.createElement("span");
      el.className = "pnl-src__nome";
      // Il percorso intero e' lungo quanto mezzo pannello e passa sopra la
      // legenda. Le ultime due parti bastano a riconoscere il file.
      el.textContent = `${f.path.split("/").slice(-2).join("/")} · ${byte(f.bytes)}`;
      nomi.appendChild(el);
      return { el, i };
    });
    posiziona(geometria);
    // Di nuovo quando i font sono pronti: `offsetWidth` misurato col font di
    // ripiego da' una larghezza diversa, e l'etichetta piu' lunga sbordava
    // proprio perche' era stata misurata prima che arrivasse IBM Plex Mono.
    document.fonts?.ready.then(() => posiziona(geometria));

    // La legenda: cartelle, conteggio e ampiezza della fascia.
    elFasce.replaceChildren(
      ...[...componente.fasce.values()].map((f) => {
        const r = document.createElement("div");
        r.className = "pnl-src__fascia";
        // R96: `f.nome` e' il nome di una directory dell'installazione, e
        // arriva dal disco. Stessa regola del file manager — `textContent`,
        // mai `innerHTML`: l'origine e' meno esposta, la classe del dato e' la
        // stessa, e due regole diverse per lo stesso dato si dimenticano.
        const nome = document.createElement("span");
        nome.textContent = f.nome;
        const conteggio = document.createElement("b");
        conteggio.textContent = String(f.conteggio);
        r.append(nome, conteggio);
        return r;
      })
    );

    const totale = elenco.reduce((n, f) => n + f.bytes, 0);
    radice.querySelector(".pnl-src__conteggio").textContent =
      `${elenco.length} file · ${componente.fasce.size} radici`;
    radice.querySelector(".pnl-src__peso").textContent =
      `${byte(totale)} · sfera r${componente.params.radius} mm`;
  }

  function posiziona(geometria) {
    for (const e of etichette) {
      const v = geometria.vertice(e.i);
      const p = scena.proietta(v.x, v.y, v.z);
      // Il ribaltamento si decide sulla larghezza MISURATA dell'etichetta,
      // non su una frazione della tela: una soglia fissa lascia passare
      // proprio le etichette lunghe, che sono quelle che sbordano.
      const largo = e.el.offsetWidth;
      const aSinistra = p.x + largo > scena.larghezza - 4;
      e.el.dataset.verso = aSinistra ? "sinistra" : "destra";
      e.el.style.left = `${Math.round(p.x)}px`;
      e.el.style.top = `${Math.round(p.y)}px`;
      e.el.style.display = p.davanti ? "" : "none";
    }
  }

  return {
    radice,
    /** @param {{topic:string, files:{path:string,bytes:number}[]}} msg */
    aggiorna(msg) {
      if (msg?.topic !== "source.tree") return;
      disegna(msg.files);
    },
    get scena() { return scena; },
  };
}
