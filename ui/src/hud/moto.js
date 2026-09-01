/* La coreografia dell'HUD — cinque velocità indipendenti, e perché.
 *
 * ## Il principio, che è del riferimento e non mio
 *
 * «Il realismo nasce dalla **sovrapposizione di moti lenti indipendenti**, non
 * da un unico moto complesso.» Cinque anelli che girano a velocità scorrelate
 * producono una figura che non si ripete; uno solo che gira, per quanto
 * elaborato, è uno spinner.
 *
 * ## ⚠️ Questo file È la deroga più pesante del turno
 *
 * L'invariante 25 vieta l'animazione ambientale e §10.3 dice «Fondo: immobile».
 * `CANCELLO-10.6.md` chiama quella riga *«l'unica riga del progetto che non è
 * mai stata violata»*. Da oggi non lo è più: qui gli anelli girano senza causa.
 *
 * La deroga è del proprietario ed è in `docs/acceptance/NUCLEO-HUD.md`. Cio'
 * che si perde va detto: il moto non è più un segnale. Prima «se gira, sta
 * lavorando» si leggeva da tre metri; adesso girano tutti, sempre, e il segnale
 * si sposta sull'ACCENSIONE — che §25.5 già governava, e che resta.
 *
 * ## Che cosa NON è derogato
 *
 * L'invariante 9: il motore è anime.js v4 e nessun altro. Non c'è un
 * `requestAnimationFrame` scritto a mano in questo file, e non deve
 * essercene: una rotazione fatta a mano accanto a un motore di animazione è
 * il secondo motore che l'invariante vieta, con un altro nome.
 *
 * ## Il fermo è APPICCICOSO, e non è un dettaglio
 *
 * `fissa()` ferma tutto e riporta ogni rotazione a zero, per il ciclo §11.7:
 * due scatti di due stati diversi devono differire per lo STATO e non per
 * l'angolo. E resta fermo finché qualcuno non chiama `libera()`.
 *
 * ⚠️ Nella stesura precedente non lo era, e il difetto si vedeva solo in
 * finestra vera: `app.js` chiama `sfondo.stato()` a ogni cambio di
 * connessione, quella chiamata rimetteva in moto il disco, e bastava un
 * messaggio del bus fra il fermo e lo scatto. Misurato: **43 % dei pixel
 * diversi** fra due stati che dovevano differire per un anello.
 */

import { animate, utils } from "../../vendor/anime.esm.min.js";
import { GRADI_AL_SECONDO, STRATI } from "./geometria.js";

//: Quanto dura lo scatto d'aggancio di L1. `easeOutExpo` — arrivo secco con
//: assestamento — è l'easing che il riferimento nomina per esteso, ed è quello
//: che fa leggere il movimento come «ui militare» invece che come una
//: transizione. In anime.js v4 si scrive `out(6)`, che è la stessa curva.
const SCATTO_MS = 620;

//: Di quanto aggancia, in gradi. Un quarto di giro è troppo — sembra che
//: l'anello salti — e cinque gradi non si vedono. Dodici è l'ampiezza in cui
//: lo scatto si legge come un aggancio e non come un sussulto.
const SCATTO_GRADI = 12;

/** Monta la coreografia sugli strati già costruiti.
 *
 * @param {{ruote: Map, scatti: Map, gruppi: Map}} strati da `costruisci()`
 * @param {() => void} conta  incrementa il contatore dei fotogrammi
 */
export function crea({ ruote, scatti, gruppi }, conta = () => {}) {
  const rotazioni = new Map();
  const respiri = [];
  let fissato = false;
  let temporizzatore = 0;

  /* ── Le rotazioni continue ──────────────────────────────────────────────
   *
   * Una per strato che ne dichiara una. Il verso è nel segno dei gradi: il
   * riferimento alterna orario e antiorario, ed è metà di ciò che rende la
   * figura non ripetitiva — cinque anelli che girano tutti nello stesso verso
   * leggono come un vortice, non come strumenti indipendenti. */
  for (const [chi, gradi] of Object.entries(GRADI_AL_SECONDO)) {
    const nodo = ruote.get(chi);
    if (!nodo) continue;
    const periodoMs = (360 / Math.abs(gradi)) * 1000;
    rotazioni.set(chi, animate(nodo, {
      rotate: 360 * Math.sign(gradi),
      duration: periodoMs,
      loop: true,
      ease: "linear",
      // ⚠️ Nasce IN MOTO — è la deroga. Il default di anime.js è già questo;
      // scriverlo esplicito serve a chi cerca dove il fondo ha smesso di
      // essere immobile: è questa riga.
      autoplay: true,
    }));
  }

  /* ── Il respiro di L2 ───────────────────────────────────────────────────
   *
   * Il riferimento gli dà 0,3 Hz e ±8 % di opacità. Non è una rotazione: è
   * l'unico strato che pulsa, e pulsa perché inquadra il nome — il cerchio
   * attorno a un nome che respira dice «acceso» senza dire altro. */
  for (const s of STRATI) {
    if (!s.respiroHz) continue;
    const nodo = gruppi.get(s.id);
    if (!nodo) continue;
    respiri.push(animate(nodo, {
      opacity: [1, 1 - s.respiroAmpiezza],
      duration: (1 / s.respiroHz) * 500,   // mezzo ciclo: l'alternanza lo chiude
      loop: true,
      alternate: true,
      ease: "inOut(2)",
      /* ⚠️ NON chiama `conta`, e la riga è deliberata.
       *
       * Quel contatore serve a UNA domanda: «c'è un'animazione di STATO che non
       * finisce?» — un'accensione bloccata, una fase che non si posa, un'onda
       * che non si esaurisce. È la sola cosa che resta verificabile dopo la
       * deroga 3, e `app/main.js` la misura come «dopo l'impulso si ferma».
       *
       * Il respiro è moto CONTINUO, e continuo è per definizione: contarlo lì
       * dentro fa sì che il numero non torni mai a zero, e il contatore smette
       * di poter rispondere alla propria domanda. Misurato: 30 fotogrammi in
       * mezzo secondo dopo la fine dell'impulso, con l'impulso già finito.
       *
       * Il costo della rotazione continua non sparisce — si misura dove
       * appartiene: `window.__insegna.motoOra` e `.globoOra`. */
    }));
  }

  /* ── Lo scatto d'aggancio di L1 ─────────────────────────────────────────
   *
   * ⚠️ È un EVENTO, non un moto: comincia, finisce, e dopo la fine non chiede
   * più un fotogramma. È classe 1 di §10.6 — la sola classe che sarebbe stata
   * legale anche senza la deroga — e per questo si programma con un timer
   * invece che con un `loop: true`: un anello che «aggancia» in continuazione
   * non aggancia niente.
   */
  const strato1 = STRATI.find((s) => s.id === "mirino");
  let angoloScatto = 0;

  function aggancia() {
    const nodo = scatti.get("mirino");
    if (!nodo || fissato) return;
    angoloScatto += SCATTO_GRADI;
    animate(nodo, {
      rotate: angoloScatto,
      duration: SCATTO_MS,
      // `out(6)` è easeOutExpo: quasi tutta la corsa nei primi fotogrammi, poi
      // l'assestamento. È ciò che il riferimento chiede per esteso.
      ease: "out(6)",
      onUpdate: conta,
    });
  }

  function programmaScatto() {
    clearTimeout(temporizzatore);
    if (fissato || !strato1?.scattoOgniS) return;
    temporizzatore = setTimeout(() => { aggancia(); programmaScatto(); },
                                strato1.scattoOgniS * 1000);
  }
  programmaScatto();

  return {
    /** Ferma tutto e riporta ogni rotazione a zero. Resta fermo.
     *
     * `seek(0)` riporta la proprietà animata al valore iniziale — verificato
     * sul bundle anime.js v4.5.0, non dedotto. Senza l'azzeramento il fermo
     * lascerebbe gli anelli dove capita, e due catture non sarebbero
     * confrontabili.
     */
    fissa() {
      fissato = true;
      clearTimeout(temporizzatore);
      for (const a of rotazioni.values()) { a.pause(); a.seek(0); }
      for (const a of respiri) { a.pause(); a.seek(0); }
      // Lo scatto torna anche lui all'origine: fa parte dell'angolo.
      angoloScatto = 0;
      const n = scatti.get("mirino");
      if (n) utils.set(n, { rotate: 0 });
    },

    /** Toglie il fermo. La leva esplicita: nessun fatto del bus lo toglie. */
    libera() {
      fissato = false;
      for (const a of rotazioni.values()) a.play();
      for (const a of respiri) a.play();
      programmaScatto();
    },

    /** Per la verifica: che cosa sta girando, e a che angolo. */
    stato() {
      return {
        fissato,
        rotazioni: [...rotazioni.keys()],
        periodiS: Object.fromEntries(
          Object.entries(GRADI_AL_SECONDO).map(([k, g]) => [k, +(360 / Math.abs(g)).toFixed(1)])),
        versi: Object.fromEntries(
          Object.entries(GRADI_AL_SECONDO).map(([k, g]) => [k, Math.sign(g)])),
        angoloScatto,
      };
    },

    ferma() {
      clearTimeout(temporizzatore);
      for (const a of rotazioni.values()) a.pause();
      for (const a of respiri) a.pause();
    },
  };
}
