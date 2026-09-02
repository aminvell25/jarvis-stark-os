/** Il mescolatore: da otto stati discreti a un insieme di numeri continui.
 *
 * ## Perche' esiste
 *
 * Gli stati cambiano di scatto, il nucleo no. Ogni parametro insegue il proprio
 * bersaglio con `lerp(a, b, min(1, dt * k))`, e i tre k diversi non sono un
 * dettaglio: la tinta arriva veloce perche' il cambio di stato deve leggersi
 * subito, il sovraccarico e il collasso arrivano lenti perche' sono
 * TRANSIZIONI e vederle e' il loro contenuto.
 *
 * ## L'inviluppo, e che cos'e' vero
 *
 * ⚠️ In DIALOGO e DIAGNOSTICA l'inviluppo E' LA VOCE: arriva da
 * `voice.spettro`, che il core calcola sul PCM vero (`core/voice/spettro.py`).
 * Negli altri sei stati e' una funzione del tempo — non un dato travestito da
 * dato, ma il RESPIRO del nucleo, che e' cio' che quello stato ha da dire. La
 * distinzione la dichiara `stato().sorgente`, che vale «voce» o «respiro»: chi
 * guarda una misura sa sempre quale dei due sta guardando.
 *
 * ⚠️ I FRONTI D'ONDA delle sillabe non vengono da un copione. Il riferimento ne
 * aveva uno — «Buonasera signore», con le sillabe contate sulle vocali — e non
 * e' stato portato: l'invariante 23 vieta i dati segnaposto. Qui un fronte
 * parte quando l'ampiezza VERA sale di scatto, che e' l'attacco di una sillaba
 * misurato invece che previsto.
 */

import { STATI, INSEGUIMENTO } from "./stati.js";

/** Quanti fronti d'onda possono coesistere. Quattro e' il numero del
 *  riferimento, ed e' anche la larghezza di un `vec4`: cambiarlo vuol dire
 *  cambiare lo shader. */
const FRONTI = 4;

/** Sopra questa salita di ampiezza in un campione si dichiara un attacco.
 *  0,085 su 0..1 a ~17 Hz: misurato sul parlato, sotto prende il respiro fra
 *  una parola e l'altra, sopra perde le sillabe atone. */
const SOGLIA_ATTACCO = 0.085;

/** Due attacchi piu' vicini di cosi' sono lo stesso attacco. La sillaba piu'
 *  breve del riferimento dura 0,121 s. */
const MIN_FRA_ATTACCHI = 0.09;

export function crea({ terna }) {
  const m = {
    tinta: terna(STATI[1].tinta), caldo: terna(STATI[1].caldo),
    freq: 1.9, spinta: 0.14, respiro: 0.2, rotazione: 0.3, bagliore: 0.3,
    amp: 0, scanY: -2, scatto: 0, sovraccarico: 0, collasso: 0,
    nascita: 0.02, reticolo: 0.3, parla: 0,
    sillabe: [-9, -9, -9, -9], ampSillabe: [0, 0, 0, 0], urto: -1,
  };
  //: I bersagli dei colori si risolvono UNA volta per stato, non a ogni
  //: fotogramma: `tok()` legge dal DOM, e leggerlo a 60 Hz per otto colori
  //: costa piu' di tutto il resto del mescolatore messo insieme.
  const colori = STATI.map((s) => ({ tinta: terna(s.tinta), caldo: terna(s.caldo) }));

  let indice = 1;
  let daQuando = 0;
  let ampVoce = 0;
  let ampPrec = 0;
  let ultimoAttacco = -9;
  const fronti = [];

  function porta(nuovo, t) {
    if (nuovo === indice) return false;
    indice = nuovo;
    daQuando = t;
    fronti.length = 0;
    return true;
  }

  /** L'ampiezza dallo spettro vero, 0..1. La chiama chi riceve
   *  `voice.spettro`; se non la chiama nessuno resta a zero, e lo stato vuoto
   *  si vede. */
  function voce(a, t) {
    const v = Math.max(0, Math.min(1, a));
    if (v - ampPrec > SOGLIA_ATTACCO && t - ultimoAttacco > MIN_FRA_ATTACCHI) {
      ultimoAttacco = t;
      fronti.unshift({ nato: t, amp: Math.min(1, 0.5 + v * 0.7) });
      if (fronti.length > FRONTI) fronti.length = FRONTI;
    }
    ampPrec = v;
    ampVoce = v;
  }

  /** Il respiro dei sei stati che non hanno una voce da seguire.
   *
   * ⚠️ Non e' telemetria: e' la firma di moto dello stato, e il riferimento la
   * da' stato per stato. AVVIO sale, STANDBY oscilla lentissimo, ANALISI batte
   * a tre frequenze incommensurabili, MINACCIA e' un battito quadro a 2 Hz,
   * SOVRACCARICO e' fuori scala, ARRESTO decade a zero. */
  function respiro(t) {
    const eta = t - daQuando;
    switch (indice) {
      case 0: {
        const p = Math.min(1, eta / 3.4);
        return 0.10 + 0.7 * p * (0.6 + 0.4 * Math.abs(Math.sin(t * 5.2)));
      }
      case 1: return 0.08 + 0.14 * (0.5 + 0.5 * Math.sin(t * 0.48));
      case 2: return 0.18 + 0.22 * (0.5 + 0.5 * Math.sin(t * 1.4));
      case 3: return 0.22 + 0.4 * Math.abs(Math.sin(t * 3.4) * Math.sin(t * 1.13))
                     + 0.12 * Math.sin(t * 9);
      case 4: return 0.06 + Math.min(0.62, ampVoce * 1.4 * 0.46);
      case 5: {
        const battito = (t * 2) % 1;
        return 0.14 + 0.86 * Math.pow(Math.max(0, 1 - battito * 4.2), 1.6);
      }
      case 6: return 0.55 + 0.45 * Math.abs(Math.sin(t * 7.3) * Math.sin(t * 2.9))
                     + 0.1 * Math.sin(t * 19);
      default: {
        const p = Math.min(1, eta / 4.2);
        return (0.4 + 0.3 * Math.sin(t * 1.6)) * (1 - p);
      }
    }
  }

  function avanza(t, dt) {
    const S = STATI[indice];
    const eta = t - daQuando;

    const env = indice === 2 ? 0.18 + ampVoce * 0.44 : respiro(t);
    /* Tre costanti di attacco e non una: gli stati d'allarme devono scattare,
       il dialogo deve seguire la voce, gli altri devono respirare. */
    const k = (indice === 5 || indice === 6) ? 0.34 : indice === 4 ? 0.22 : 0.13;
    m.amp = m.amp * (1 - k) + env * S.guadagno * k;

    const f = Math.min(1, dt * INSEGUIMENTO.normale);
    const lento = Math.min(1, dt * INSEGUIMENTO.lento);
    const nas = Math.min(1, dt * INSEGUIMENTO.nascita);
    const lerp = (a, b, q) => a + (b - a) * q;
    const C = colori[indice];
    for (let i = 0; i < 3; i++) {
      m.tinta[i] = lerp(m.tinta[i], C.tinta[i], f);
      m.caldo[i] = lerp(m.caldo[i], C.caldo[i], f);
    }
    m.freq = lerp(m.freq, S.freq, f);
    m.spinta = lerp(m.spinta, S.spinta, f);
    m.respiro = lerp(m.respiro, S.respiro, f);
    m.rotazione = lerp(m.rotazione, S.rotazione, f);
    m.bagliore = lerp(m.bagliore, S.bagliore, f);

    /* L'urto: ogni cambio di stato manda un fronte dal polo verso l'osservatore,
       e dura 1,6 s. E' cio' che rende un cambio di stato un EVENTO invece che
       una dissolvenza. */
    m.urto = eta < 1.6 ? eta : -1;

    //: La fascia di scansione esiste solo in DIAGNOSTICA; altrove torna a -2,
    //: che nello shader vuol dire «fuori dalla sfera».
    m.scanY = S.scandisce ? Math.sin(t * 0.85) * 1.05 : lerp(m.scanY, -2, f);
    m.scatto = lerp(m.scatto, S.scatto || 0, f);
    m.sovraccarico = lerp(m.sovraccarico, S.sovraccarico || 0, lento);
    m.reticolo = lerp(m.reticolo, S.reticolo ? 1 : 0.3, f);
    m.parla = lerp(m.parla, S.parla ? 1 : 0, f);
    m.nascita = lerp(m.nascita, S.nascita ? Math.min(1, eta / 2.8) : 1, nas);
    m.collasso = lerp(m.collasso, S.collasso ? Math.min(1, eta / 4.2) : 0, lento);

    for (let q = 0; q < FRONTI; q++) {
      const fr = fronti[q];
      const et = fr ? t - fr.nato : -9;
      //: Oltre 0,9 s il fronte e' uscito dalla sfera e non si vede piu'.
      m.sillabe[q] = (fr && et <= 0.9) ? et : -9;
      m.ampSillabe[q] = (fr && et <= 0.9) ? fr.amp : 0;
    }
    while (fronti.length && t - fronti[fronti.length - 1].nato > 0.9) fronti.pop();

    return m;
  }

  /** Azzera ogni moto e porta il mescolatore al valore di riposo dello stato.
   *  Serve al ciclo §11.7: due scatti dello stesso stato devono differire per
   *  lo stato, non per l'angolo. */
  /** I nomi che il banco di misura usa da prima di Aurora.
   *
   * ⚠️ Non sono un ripiego: `app/main.js`, `verifica:marchio` e
   * `verifica:scrivania` pilotano il nucleo con «riposo», «t1», «parla»,
   * «onda» da settembre, e sono QUATTRO strumenti. Rinominarli tutti insieme
   * al nucleo avrebbe mescolato due cambiamenti in un commit solo, e il giorno
   * che una misura fosse cambiata non si sarebbe saputo per quale dei due.
   * Gli alias costano otto righe e tengono separate le due cose. */
  const ALIAS = {
    riposo: "STANDBY", inerte: "STANDBY",
    t0: "AVVIO", avvio: "AVVIO",
    ascolto: "DIAGNOSTICA",
    t1: "ANALISI", t2: "ANALISI", subagent: "ANALISI", pensa: "ANALISI",
    parla: "DIALOGO", onda: "DIALOGO",
    warn: "MINACCIA", avviso: "MINACCIA",
    critical: "SOVRACCARICO",
    offline: "ARRESTO",
  };

  function fissa(nome) {
    const cercato = ALIAS[nome] || nome;
    const i = STATI.findIndex((s) => s.id === cercato);
    if (i >= 0) { indice = i; }
    const S = STATI[indice];
    const C = colori[indice];
    daQuando = -1e6;
    fronti.length = 0;
    ampVoce = 0; ampPrec = 0;
    m.tinta = [...C.tinta]; m.caldo = [...C.caldo];
    m.freq = S.freq; m.spinta = S.spinta; m.respiro = S.respiro;
    m.rotazione = S.rotazione; m.bagliore = S.bagliore;
    m.amp = S.guadagno * 0.35;
    m.scanY = S.scandisce ? 0 : -2;
    m.scatto = 0; m.sovraccarico = S.sovraccarico || 0;
    m.collasso = S.collasso ? 1 : 0;
    m.nascita = 1; m.reticolo = S.reticolo ? 1 : 0.3;
    m.parla = S.parla ? 1 : 0; m.urto = -1;
    m.sillabe = [-9, -9, -9, -9]; m.ampSillabe = [0, 0, 0, 0];
    return stato();
  }

  function stato() {
    return {
      stato: STATI[indice].id,
      indice,
      sorgente: (indice === 4 || indice === 2) ? "voce" : "respiro",
      amp: +m.amp.toFixed(4),
      ampVoce: +ampVoce.toFixed(4),
      fronti: fronti.length,
      /* ⚠️ `scan` E' IL CONTENUTO DI DIAGNOSTICA, non un dettaglio del
       * mescolatore. E' la quota della fascia luminosa sull'asse Y della
       * sfera: -2 vuol dire «fuori», e fra -1,05 e +1,05 vuol dire che sta
       * attraversando. Senza questo campo lo stato si puo' verificare solo
       * per NOME — «dice DIAGNOSTICA» — che e' la cosa che il nome dice di
       * se' e non una misura. */
      scan: +m.scanY.toFixed(3),
      rotazione: +m.rotazione.toFixed(3),
      collasso: +m.collasso.toFixed(3),
      nascita: +m.nascita.toFixed(3),
    };
  }

  return { mix: m, porta, voce, avanza, fissa, stato, get indice() { return indice; } };
}
