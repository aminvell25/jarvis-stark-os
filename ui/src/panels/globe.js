/* Globo tattico — SPEC §13, riferimento famiglia-a/10-globo-gps-locator.
 *
 * Tutto quello che si vede e' calcolato o letto, niente e' inventato:
 *
 *   312 fusi orari  da `/usr/share/zoneinfo/zone1970.tab`, attraverso il tool
 *                   `timezones` dell'allowlist (il renderer non tocca il disco)
 *   terminatore     dalla declinazione solare e dall'ora UTC vera (§17.4)
 *   giorno e notte  prodotto scalare fra ogni fuso e il punto subsolare
 *   inquadratura    centrata sul fuso della macchina
 *
 * Il layer degli ARCHI del riferimento non c'e', ed e' dichiarato: nessuna
 * sorgente in questo sistema produce oggi coppie di coordinate vere, e
 * inventarle sarebbe la cosa che §11.9 vieta. Arriveranno in Fase 8, quando le
 * news avranno un'origine geografica.
 */

import { creaScena, inquadra } from "../three/scena.js";
import { Fusi, Graticola, Sfera, Terminatore, illuminato, puntoSubsolare, suSfera }
  from "../three/math/globe.js";
import { qualityGate } from "../three/quality-gate.js";
import { versoBufferGeometry, versoLinee, versoSuperficie, materialiPerRuolo }
  from "../three/buffer.js";
import { tok } from "../style/tokens.js";

export const meta = { nome: "globe", versione: "1" };

export const css = `
.pnl-glb {
  --aug-tl: var(--s-3);
  --aug-br: var(--s-3);
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
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 4);
  /* §10.5 regola 1 — un pannello e' un GRADINO DI LUMINANZA, non una cornice.
     --bg-raised (L 37) contro il pavimento a L 19 sono i +18 misurati a
     quattro quote sul calendario del riferimento; --bg-panel (L 31) ne dava
     12, e a quel gradino il globo non si appoggiava a niente. Nessuna
     border: qui dentro — dei sette pannelli misurati, ZERO hanno un tratto
     che gira sui quattro lati. */
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
/* §10.5 regola 2 — la testata e' una SUPERFICIE, non una riga di testo con un
   filo sotto. --fill-1 sta a L 66: +29 sul corpo, oltre il +19 minimo
   misurato, e adotta la polarita' del calendario (banda chiara, testo chiaro).
   Il border-bottom hairline se n'e' andato perche' il gradino separa gia' da
   solo, e tenerli tutti e due era dire due volte la stessa cosa. L'altezza non
   si tocca: la banda e' identica a prima, cambia che adesso e' piena. */
.pnl-glb__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
/* Il fondo della testa e' passato da L 31 a L 66: ogni colore qui dentro andava
   rimisurato, non ereditato. --cy-300 reggerebbe (6,21:1), ma --fill-1 e' esso
   stesso un ciano desaturato e l'accento su fondo affine smette di fare
   l'accento; --txt-primary da' 8,06:1 ed e' il nome del pannello, cioe' il
   testo primario della banda. */
.pnl-glb__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
/* --txt-dim qui era sceso a 2,73:1, e a --t-micro su fondo chiaro non e' testo,
   e' sporco. --icona da' 4,31:1 ed e' il gradino sotto l'etichetta: matricola e
   versione restano subordinate senza sparire, e i tre glifi di controllo sono
   icone alla lettera — e' il token fatto per loro. */
.pnl-glb__id, .pnl-glb__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}
.pnl-glb__ctrl { letter-spacing: 0.16em; }

.pnl-glb__corpo { position: relative; display: grid; min-height: 0; overflow: hidden; }
/* La tela si prende in mano: §13 non lo chiedeva perche' fino a ieri il globo
   era un'immagine, ma un globo che non si gira mostra sempre lo stesso
   emisfero — e i 312 fusi sono trecentododici solo se si puo' vedere l'altra
   meta'. touch-action: none non e' cosmesi: senza, il browser interpreta il
   trascinamento come uno scorrimento e i pointermove smettono di arrivare a
   meta' gesto. E' lo stesso inciampo che desk/cornice.js documenta. */
.pnl-glb__tela {
  position: relative;
  min-width: 0;
  min-height: 0;
  cursor: grab;
  touch-action: none;
  /* IL CAMPO E' PIU' SCURO DELLA STANZA — e non e' una scelta di gusto.
     Lo spazio attorno al pianeta era --bg-raised, cioe' lo STESSO valore della
     scatola che lo contiene: il campo di una vista dipinto col colore del suo
     telaio. Misurato sul riferimento, non dedotto: famiglia-a/01 tiene il
     5,2 % del fotogramma sotto L 16 e sta TUTTO dentro i pannelli di globo e
     mappa (28-41 % di quelle celle); da noi il bin 0 era a 0,00 %.
     Che cosa guadagna, misurato contro il campo:
         lembo illuminato  --fill-1   1,54:1 -> 2,03:1
         fusi in ombra     --cy-700   2,82:1 -> 3,72:1
         fusi in luce      --cy-100  12,43:1 -> 16,37:1
         emisfero notturno --bg-panel 1,08:1 -> 1,22:1
     ⚠️ L'ultima riga NON e' un successo WCAG: 1,22 resta bassissimo. Il
     rapporto WCAG comprime al fondo della scala, e la cosa che si vede e' la
     separazione di luminanza, passata da 6,4 punti a 23,1. Prima il lembo in
     ombra spariva nel pannello; adesso il disco si legge. E' una cosa GUARDATA
     in shots/globe.png, non dedotta da un numero.
     Il gradino di §10.5 regola 1 resta: testata --fill-1 (L 66) e cornice
     --bg-raised (L 37) contro il pavimento (L 19). Cambia il CAMPO, che e'
     contenuto e non chrome.
     Il colore lo dipinge il CSS e non WebGL: il renderer resta alpha: true,
     come three/scena.js chiede, o l'invariante 18 cadrebbe proprio dove e'
     piu' facile non accorgersene. */
  background: var(--bg-abyss);
}
.pnl-glb__tela[data-presa] { cursor: grabbing; }
.pnl-glb__nomi { position: absolute; inset: 0; pointer-events: none; }
.pnl-glb__nome {
  position: absolute;
  transform: translate(var(--s-2), -50%);
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--cy-100);
}
.pnl-glb__nome[data-verso="sinistra"] { transform: translate(calc(-100% - var(--s-2)), -50%); }
.pnl-glb__nome[data-ruolo="sole"] { color: var(--amber); }
.pnl-glb__nome::before {
  content: "";
  position: absolute;
  left: calc(var(--s-2) * -1);
  top: 50%;
  width: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-700);
}
.pnl-glb__nome[data-verso="sinistra"]::before { left: auto; right: calc(var(--s-2) * -1); }

/* Il border-top del piede RESTA. §10.5 vieta la cornice, cioe' il tratto che
   gira intorno al pannello: questo divide due parti dello stesso pannello,
   corpo e piede, ed e' lo stesso mestiere che la superficie fa in testa. Qui
   basta un mezzo pixel perche' fra corpo e piede non c'e' gerarchia da
   dichiarare, solo un confine. */
.pnl-glb__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-glb__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-glb[data-stato="vuoto"] .pnl-glb__corpo { display: none; }
.pnl-glb[data-stato="vuoto"] .pnl-glb__vuoto { display: block; }
`;

const gradi = (v, pos, neg) =>
  `${Math.abs(v).toFixed(3)}° ${v >= 0 ? pos : neg}`;

export function crea(ospite) {
  const radice = document.createElement("div");
  radice.className = "pnl-glb";
  radice.dataset.augmentedUi = "tl-clip br-clip border";
  radice.dataset.stato = "vuoto";
  radice.innerHTML = `
    <div class="pnl-glb__testa">
      <span class="pnl-glb__etichetta">Globo tattico</span>
      <span class="pnl-glb__id">GLB_G07 · ver ${meta.versione}</span>
      <span class="pnl-glb__ctrl">⊟ ⊡ ⊠</span>
    </div>
    <div class="pnl-glb__corpo">
      <div class="pnl-glb__tela"><div class="pnl-glb__nomi"></div></div>
    </div>
    <div class="pnl-glb__vuoto">NESSUNA SORGENTE COLLEGATA</div>
    <div class="pnl-glb__piede">
      <span class="pnl-glb__utc"></span>
      <span class="pnl-glb__sole"></span>
      <span class="pnl-glb__conteggio"></span>
    </div>
  `;
  ospite.appendChild(radice);

  const tela = radice.querySelector(".pnl-glb__tela");
  const nomi = radice.querySelector(".pnl-glb__nomi");
  let scena = null;

  function disegna(zone, quando) {
    if (!zone?.length) { radice.dataset.stato = "vuoto"; return; }
    radice.dataset.stato = "pieno";
    scena?.smonta();
    nomi.replaceChildren();
    scena = creaScena(tela, { fov: 32 });
    const { THREE, scena: s3, camera } = scena;

    const sole = puntoSubsolare(quando);

    /* ⚠️ IL CORPO DELLA SFERA, e non e' un fondale: e' il dato reso superficie.
     *
     * Misurato prima di scriverlo: il pannello del globo stava al 78,3 % nella
     * banda L 25-60 — quasi tutto corpo nudo — con entropia 1,36 contro i 3,05
     * del riferimento famiglia-a/10. Una sfera di sole linee non e' un pianeta
     * visto da lontano, e' un mappamondo di fil di ferro.
     *
     * Il colore di ogni vertice lo decide `illuminato()`: lo stesso prodotto
     * scalare col punto subsolare che gia' colora i fusi. Giorno e notte
     * diventano due superfici invece di due colori di puntino, e il terminatore
     * ambra smette di essere una linea sospesa nel vuoto — separa due cose.
     *
     * --fill-1 (L 66) di giorno e --bg-panel (L 31) di notte: il giorno sta
     * nella banda 60-120, che e' dove il riferimento ha il 24,7 % e noi
     * l'8,2 %. Nessuno dei due e' un colore del dato — quelli stanno nei
     * pannelli, e questo e' un fondo. */
    const sfera = new Sfera();
    const gSfera = sfera.build();
    const nV = gSfera.conteggio;
    const colSfera = new Float32Array(nV * 3);
    const cGiorno = new THREE.Color(tok("--fill-1"));
    const cNotte = new THREE.Color(tok("--bg-panel"));
    for (let i = 0; i < nV; i++) {
      const v = gSfera.vertice(i);
      // Dalla posizione alla latitudine e longitudine: l'inversa di suSfera,
      // che mette la latitudine su y e la longitudine su (x, z).
      const r = Math.hypot(v.x, v.y, v.z) || 1;
      const lat = Math.asin(v.y / r) * (180 / Math.PI);
      const lon = Math.atan2(v.x, v.z) * (180 / Math.PI);
      const c = illuminato(lat, lon, sole) ? cGiorno : cNotte;
      colSfera[i * 3] = c.r; colSfera[i * 3 + 1] = c.g; colSfera[i * 3 + 2] = c.b;
    }
    const meshSfera = versoSuperficie(gSfera, colSfera);
    qualityGate(sfera, gSfera, [meshSfera.material]);
    /* Il corpo entra per PRIMO: un reticolo disegnato sotto la propria sfera
       non si vede, e l'ordine di inserimento e' l'ordine di disegno per
       oggetti senza test di profondita' fra loro. */
    s3.add(meshSfera);

    const graticola = new Graticola();
    const gGrat = graticola.build();
    const term = new Terminatore({}, sole);
    const gTerm = term.build();
    const fusi = new Fusi({}, zone);
    const gFusi = fusi.build();

    const mLinee = materialiPerRuolo(["linea", "costruzione"], {
      larghezza: scena.larghezza, altezza: scena.altezza,
    });
    const mSole = materialiPerRuolo(["sole"], {
      larghezza: scena.larghezza, altezza: scena.altezza,
    });
    for (const m of [...mLinee.values(), ...mSole.values()]) scena.seguiLinea(m);

    // Ogni componente passa il gate PRIMA di finire nella scena, e ognuno coi
    // suoi materiali: il limite di due di §11.10 e' per componente.
    qualityGate(graticola, gGrat, [...mLinee.values()]);
    qualityGate(term, gTerm, [...mSole.values()]);

    for (const o of versoLinee(gGrat, mLinee)) s3.add(o);
    for (const o of versoLinee(graticola.constructionLines(), mLinee)) s3.add(o);
    for (const o of versoLinee(gTerm, mSole)) s3.add(o);

    // I fusi: chiari dove e' giorno, spenti dove e' notte. Il colore e' un
    // conto, non una scelta grafica.
    const punti = versoBufferGeometry(gFusi);
    const colori = new Float32Array(zone.length * 3);
    const giorno = new THREE.Color(tok("--cy-100"));
    const notte = new THREE.Color(tok("--cy-700"));
    let illuminati = 0;
    for (const [i, z] of zone.entries()) {
      const c = illuminato(z.lat, z.lon, sole) ? (illuminati++, giorno) : notte;
      colori[i * 3] = c.r; colori[i * 3 + 1] = c.g; colori[i * 3 + 2] = c.b;
    }
    punti.setAttribute("color", new THREE.BufferAttribute(colori, 3));
    /* ⚠️ 5 e non 3: a 3 px i 312 fusi sono granelli, e un dato che non si vede
       non e' un dato. Il pannello e' 472x337 e la sfera ne occupa poco piu' di
       300: un punto da 3 px vale l'1 % del raggio.
       Con sizeAttenuation la dimensione segue la prospettiva, quindi i fusi sul
       bordo restano piu' piccoli di quelli al centro e la sfera continua a
       leggersi come una sfera. */
    const mPunti = new THREE.PointsMaterial({ size: 5, sizeAttenuation: true, vertexColors: true });
    qualityGate(fusi, gFusi, [mPunti]);
    s3.add(new THREE.Points(punti, mPunti));

    // Inquadratura centrata sul fuso di QUESTA macchina: il globo si apre su
    // dove si e', non su un meridiano scelto a caso.
    const qui = zone.find((z) => z.nome === Intl.DateTimeFormat().resolvedOptions().timeZone)
      ?? zone[0];
    const [dx, dy, dz] = suSfera(qui.lat, qui.lon, 1);
    inquadra(THREE, camera, gGrat.posizioni, { x: dx, y: dy + 0.25, z: dz }, 1.02);
    scena.invalida();
    scena.rendi();

    // Due etichette DOM, proiettate: dove siamo e dov'e' il Sole.
    const etichette = [
      { testo: `${qui.nome} · ${gradi(qui.lat, "N", "S")} ${gradi(qui.lon, "E", "O")}`,
        p: suSfera(qui.lat, qui.lon, graticola.params.radius * 1.02), ruolo: "qui" },
      { testo: `subsolare · ${gradi(sole.lat, "N", "S")} ${gradi(sole.lon, "E", "O")}`,
        p: suSfera(sole.lat, sole.lon, graticola.params.radius * 1.02), ruolo: "sole" },
    ].map((e) => {
      const el = document.createElement("span");
      el.className = "pnl-glb__nome";
      el.dataset.ruolo = e.ruolo;
      el.textContent = e.testo;
      nomi.appendChild(el);
      return { el, p: e.p };
    });

    const posiziona = () => {
      for (const e of etichette) {
        const q = scena.proietta(e.p[0], e.p[1], e.p[2]);
        e.el.dataset.verso = q.x + e.el.offsetWidth > scena.larghezza - 4 ? "sinistra" : "destra";
        e.el.style.left = `${Math.round(q.x)}px`;
        e.el.style.top = `${Math.round(q.y)}px`;
        e.el.style.display = q.davanti ? "" : "none";
      }
    };
    posiziona();
    document.fonts?.ready.then(posiziona);

    /* ── girare e avvicinare ──────────────────────────────────────────────
     *
     * Nessun OrbitControls: e' un addon che non sta in ui/vendor/ (li' ci sono
     * solo i Line2), e CLAUDE.md dice di non aggiungere dipendenze senza
     * chiedere. Servono due gradi di liberta' e un raggio — trenta righe — e
     * non valgono una dipendenza.
     *
     * La camera si muove in coordinate SFERICHE attorno al centro, non lungo
     * gli assi: e' l'unico modo per cui il globo gira senza inclinarsi e il
     * polo resta in alto. La distanza giusta l'ha gia' scelta inquadra(); qui
     * si parte da quella e la si tiene come riferimento per i limiti dello
     * zoom, invece di scegliere due numeri nuovi.
     *
     * ⚠️ I POLI SONO INTERDETTI di un margine. A phi = 0 il vettore verso
     * l'alto della camera e la direzione di vista diventano paralleli, lookAt
     * degenera e il globo fa un salto: e' la stessa singolarita' che
     * math/globe.js evita nel terminatore scegliendo l'asse meno allineato.
     *
     * ⚠️ Un grado di rotazione per un grado di CAMPO VISIVO, non per pixel:
     * cosi' il globo segue il dito alla stessa velocita' qualunque sia la
     * dimensione del pannello. Con un passo fisso in pixel, in una cella
     * piccola girerebbe piu' veloce che a schermo intero. */
    const raggioIniziale = Math.hypot(camera.position.x, camera.position.y, camera.position.z);
    const LIMITE_POLO = 0.12;
    let raggio = raggioIniziale;
    let theta = Math.atan2(camera.position.x, camera.position.z);
    let phi = Math.acos(Math.max(-1, Math.min(1, camera.position.y / raggioIniziale)));

    function inquadraDiNuovo() {
      camera.position.set(
        raggio * Math.sin(phi) * Math.sin(theta),
        raggio * Math.cos(phi),
        raggio * Math.sin(phi) * Math.cos(theta),
      );
      camera.lookAt(0, 0, 0);
      camera.updateProjectionMatrix();
      scena.invalida();
      scena.rendi();
      posiziona();
    }

    let presa = null;
    tela.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      presa = { id: e.pointerId, x: e.clientX, y: e.clientY };
      tela.setPointerCapture(e.pointerId);
      tela.dataset.presa = "";
    });
    tela.addEventListener("pointermove", (e) => {
      if (!presa || e.pointerId !== presa.id) return;
      const perPixel = (32 * Math.PI / 180) / Math.max(1, scena.altezza);
      theta -= (e.clientX - presa.x) * perPixel;
      phi = Math.max(LIMITE_POLO,
                     Math.min(Math.PI - LIMITE_POLO, phi - (e.clientY - presa.y) * perPixel));
      presa.x = e.clientX;
      presa.y = e.clientY;
      inquadraDiNuovo();
    });
    const lascia = (e) => {
      if (!presa || e.pointerId !== presa.id) return;
      presa = null;
      delete tela.dataset.presa;
    };
    tela.addEventListener("pointerup", lascia);
    tela.addEventListener("pointercancel", lascia);
    /* La rotella avvicina. I limiti sono FRAZIONI della distanza che
     * inquadra() ha calcolato: piu' vicino di 0,55 la sfera esce dal campo,
     * piu' lontano di 2,2 diventa un punto. */
    tela.addEventListener("wheel", (e) => {
      e.preventDefault();
      const passo = e.deltaY > 0 ? 1.08 : 1 / 1.08;
      raggio = Math.max(raggioIniziale * 0.55,
                        Math.min(raggioIniziale * 2.2, raggio * passo));
      inquadraDiNuovo();
    }, { passive: false });

    radice.querySelector(".pnl-glb__utc").textContent =
      `${quando.toISOString().slice(11, 19)} UTC`;
    radice.querySelector(".pnl-glb__sole").textContent =
      `sole ${gradi(sole.lat, "N", "S")} ${gradi(sole.lon, "E", "O")}`;
    radice.querySelector(".pnl-glb__conteggio").textContent =
      `${zone.length} fusi · ${illuminati} in luce · ${zone.length - illuminati} in ombra`;
  }

  return {
    radice,
    /** @param {{topic:string, zone:{nome:string,lat:number,lon:number}[]}} msg */
    aggiorna(msg) {
      if (msg?.topic !== "geo.timezones") return;
      disegna(msg.zone, msg.quando ? new Date(msg.quando) : new Date());
    },
    get scena() { return scena; },
  };
}
