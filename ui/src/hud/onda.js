/* L'onda vocale al centro dell'HUD — §11.5 Fase 3, §10.6 classe 2.
 *
 * ## Che cosa mostra, e da dove viene
 *
 * Le ampiezze delle bande di frequenza dell'audio VERO che passa dal core: il
 * microfono mentre JARVIS ascolta, il PCM del TTS mentre parla. Il calcolo sta
 * in `core/voice/spettro.py` e arriva sul bus come `voice.spettro`.
 *
 * ⚠️ **Qui NON si apre nessun microfono.** La Web Audio API farebbe il lavoro
 * in tre righe e sarebbe la strada sbagliata: il renderer aprirebbe un secondo
 * dispositivo audio accanto a quello che il core ha gia' aperto, cioe' una
 * seconda fonte di verita' sull'audio (CLAUDE.md, «non fare senza chiedere»),
 * e l'invariante 1 dice che le operazioni reali le possiede il core. Sul filo
 * viaggiano numeri, non un secondo flusso.
 *
 * ## E' una DEROGA di posto, non di natura
 *
 * §10.6 ammette la classe 2 — «continuo governato da una sorgente viva» —
 * **solo nel contenuto di un pannello**, e scrive che il fondo non si tocca.
 * Questo componente sta nel fondo. La deroga e' in `docs/acceptance/NUCLEO-HUD.md`.
 *
 * Le tre condizioni restano, e due sono imposte da questo file:
 *
 *   **(a) falsificabilita'.** Tolta la sorgente, il moto si ferma entro un
 *   secondo. Non e' una promessa: `SILENZIO_MS` la impone qui dentro, e il
 *   componente smette di chiedere fotogrammi. E' la condizione che distingue
 *   questo da uno screensaver.
 *
 *   **(b) leggibilita' da fermo.** Il valore si legge come NUMERO in
 *   monospace, e il numero sta nel DOM — non dentro la tela. Chi monta lo
 *   mette dove vuole; `desk/sfondo.js` lo mette con le altre letture.
 *
 *   **(c) attribuzione.** I pixel che si muovono cadono dentro il rettangolo
 *   della tela, che `scripts/densita.mjs` sa attribuire.
 *
 * ## Lo stato vuoto e' meta' del componente
 *
 * `voice.enabled` parte a `false`: il caso NORMALE, appena installato, e' che
 * non ci sia nessuna sorgente. Un'onda che in quel caso disegnasse delle
 * barrette sarebbe dato inventato — invariante 23 — ed e' la ragione per cui
 * questo file ha uno stato vuoto esplicito prima ancora di avere un disegno.
 */

import { tok } from "../style/tokens.js";

export const meta = { nome: "onda", versione: "1" };

//: Dopo quanto silenzio la sorgente si dichiara morta. §10.6 condizione (a)
//: chiede «entro un secondo»: 900 ms lascia il margine perche' il decadimento
//: FINISCA dentro il secondo, invece di cominciare li'.
const SILENZIO_MS = 900;

//: La costante di tempo con cui una barra insegue il proprio valore. Il core
//: manda ~17 campioni al secondo: senza filtro l'onda scatta a gradini di
//: 60 ms e si legge come un difetto. 80 ms e' abbastanza da smussare il
//: gradino e troppo poco da inventare una forma che non c'era.
//: ⚠️ E' un filtro sul segnale, DICHIARATO: l'altezza di una barra e' il valore
//: vero, in ritardo di un'ottantina di millisecondi. Non e' un inviluppo che
//: modella le barre a piacere — quello sarebbe dato finto.
const INSEGUIMENTO_MS = 80;

//: Quanto scende al secondo quando la sorgente tace. Deve portare a zero dentro
//: `SILENZIO_MS` da qualunque altezza, o la condizione (a) sarebbe vera sulla
//: carta e falsa a schermo.
const DECADIMENTO_AL_S = 1 / (SILENZIO_MS / 1000);

export const css = `
.hud__onda {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: block;
  pointer-events: none;
}
`;

export class Onda {
  /**
   * @param {HTMLCanvasElement} tela
   * @param {{bande?: number, specchiata?: boolean}} opzioni
   */
  constructor(tela, { bande = 32, specchiata = true } = {}) {
    if (!tela || tela.tagName !== "CANVAS") throw new Error("Onda vuole un <canvas>");
    this.tela = tela;
    this.ctx = tela.getContext("2d");
    this.bande = bande;
    this.specchiata = specchiata;

    //: `obiettivo` e' l'ultimo campione arrivato, `mostrato` e' cio' che si
    //: vede. Due array e non uno: con uno solo il filtro scriverebbe sopra il
    //: dato, e il valore vero sarebbe perso dopo un fotogramma. Chi vuole
    //: sapere che cosa e' arrivato deve poterlo leggere.
    this.obiettivo = new Float32Array(bande);
    this.mostrato = new Float32Array(bande);

    this._anello = 0;
    this._ultimo = 0;
    this._ultimoCampione = 0;
    this._viva = false;
    this._picco = 0;
    this._sorgente = "";
    this._w = 0; this._h = 0; this._rapporto = 1;
  }

  /** Il campione nuovo. E' l'API che il riferimento chiede: un array di
   *  frequenze, e i picchi si animano da soli.
   *  @param {ArrayLike<number>} bande ampiezze 0..1
   *  @param {string} sorgente "mic" oppure "tts" */
  imposta(bande, sorgente = "") {
    if (!bande || typeof bande.length !== "number") return;
    const n = Math.min(this.bande, bande.length);
    for (let i = 0; i < n; i++) {
      const v = Number(bande[i]);
      this.obiettivo[i] = Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0;
    }
    // Se il core manda meno bande di quante ne disegniamo, le mancanti vanno a
    // ZERO e non restano all'ultimo valore: una barra ferma su un vecchio
    // campione racconta un suono che non c'e' piu'.
    for (let i = n; i < this.bande; i++) this.obiettivo[i] = 0;

    this._ultimoCampione = performance.now();
    this._picco = Math.max(...this.obiettivo);
    this._sorgente = sorgente;
    this._viva = true;
    this._avvia();
  }

  /** Nessuna sorgente. Stato vuoto esplicito, e il ciclo si spegne. */
  spegni() {
    this.obiettivo.fill(0);
    this._ultimoCampione = 0;
    this._viva = false;
    this._sorgente = "";
    // Il ciclo resta acceso finche' il decadimento non ha portato a zero: si
    // VEDE l'onda morire, ed e' la prova visiva della condizione (a).
    this._avvia();
  }

  /** L'etichetta di §10.6 condizione (b), per chi la mostra nel DOM. */
  etichetta() {
    if (!this._viva) return "ASSENTE";
    return `${this._sorgente === "tts" ? "TTS" : "MIC"} ${(this._picco * 100).toFixed(0)} %`;
  }

  misura(larghezza, altezza) {
    const r = Math.min(window.devicePixelRatio || 1, 2);
    this._w = Math.max(1, Math.round(larghezza));
    this._h = Math.max(1, Math.round(altezza));
    this._rapporto = r;
    this.tela.width = Math.round(this._w * r);
    this.tela.height = Math.round(this._h * r);
    this.tela.style.width = this._w + "px";
    this.tela.style.height = this._h + "px";
    this._disegna();
  }

  /** Le leve per la verifica. */
  stato() {
    return {
      viva: this._viva,
      gira: Boolean(this._anello),
      picco: +this._picco.toFixed(3),
      bande: this.bande,
      sorgente: this._sorgente,
      silenzioMs: SILENZIO_MS,
      obiettivo: [...this.obiettivo].map((v) => +v.toFixed(3)),
    };
  }

  ferma() {
    if (!this._anello) return;
    cancelAnimationFrame(this._anello);
    this._anello = 0;
    this._ultimo = 0;
  }

  /* ⚠️ Il ciclo esiste SOLO finche' c'e' qualcosa da mostrare: nasce a
   * `imposta()` e si spegne da solo quando la sorgente tace e le barre sono
   * tornate a zero. A voce spenta — il caso normale — costa esattamente zero. */
  _avvia() {
    if (this._anello || document.visibilityState === "hidden") return;
    this._ultimo = 0;
    this._anello = requestAnimationFrame((t) => this._passo(t));
  }

  _passo(ora) {
    const dt = this._ultimo ? Math.min(100, ora - this._ultimo) / 1000 : 0;
    this._ultimo = ora;

    // La sorgente e' morta? §10.6 condizione (a), imposta qui e non promessa.
    if (this._viva && this._ultimoCampione &&
        ora - this._ultimoCampione > SILENZIO_MS) this.spegni();

    let vivo = false;
    const k = dt > 0 ? 1 - Math.exp((-dt * 1000) / INSEGUIMENTO_MS) : 0;
    for (let i = 0; i < this.bande; i++) {
      let m = this.mostrato[i];
      if (!this._viva) m = Math.max(0, m - DECADIMENTO_AL_S * dt);
      else m += (this.obiettivo[i] - m) * k;
      if (m < 0.001) m = 0;
      this.mostrato[i] = m;
      if (m > 0) vivo = true;
    }

    this._disegna();
    if (!vivo && !this._viva) { this.ferma(); return; }
    this._anello = requestAnimationFrame((t) => this._passo(t));
  }

  /* ⚠️ NESSUN INVILUPPO, e la riga e' deliberata.
   *
   * Nel riferimento l'onda si assottiglia ai bordi, e la strada breve sarebbe
   * moltiplicare le barre per una finestra: l'aspetto tornerebbe e l'altezza di
   * ogni barra smetterebbe di essere il valore misurato. Sarebbe la stessa
   * specie di bugia di `scrambleText`, rifiutata in `PIANO-FUI-ESITO.md`: «un
   * valore che arriva carattere per carattere racconta una gradualita' che non
   * e' successa».
   *
   * La simmetria si ottiene senza toccare i valori: le bande si dispongono DAL
   * CENTRO VERSO I BORDI e si specchiano. Ogni barra compare due volte, alla
   * stessa altezza, e nessun numero viene distorto. Le bande alte — quelle piu'
   * silenziose in una voce — finiscono ai bordi da sole, e l'assottigliamento
   * del riferimento viene fuori dal segnale invece che da una moltiplicazione.
   */
  _disegna() {
    const { ctx } = this;
    const w = this._w, h = this._h;
    if (!ctx || w < 2 || h < 2) return;

    ctx.setTransform(this._rapporto, 0, 0, this._rapporto, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const mezzo = h / 2;
    const colonne = this.specchiata ? this.bande * 2 : this.bande;
    const passo = w / colonne;
    const tratto = Math.max(1, passo * 0.55);

    ctx.fillStyle = tok(this._viva ? "--cy-200" : "--cy-800");

    for (let c = 0; c < colonne; c++) {
      // Dal centro verso i bordi: la banda 0 (la piu' grave) sta in mezzo.
      const b = this.specchiata ? Math.abs(c - (colonne - 1) / 2) | 0 : c;
      const v = this.mostrato[Math.min(b, this.bande - 1)];
      const x = c * passo + (passo - tratto) / 2;
      // ⚠️ Un pixel di altezza minima anche a zero: la linea di base e' parte
      // dello strumento, non un valore. Senza, a sorgente spenta l'onda sparisce
      // del tutto e non si distingue da un componente rotto — che e' l'opposto
      // di uno stato vuoto ESPLICITO.
      const alto = Math.max(1, v * (mezzo - 1));
      ctx.fillRect(x, mezzo - alto, tratto, alto * 2);
    }
  }
}
