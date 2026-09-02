/** Gli otto stati operativi del nucleo Aurora, e le cause vere che li accendono.
 *
 * ## Da dove vengono questi numeri
 *
 * Dal riferimento che il proprietario ha portato il 1º settembre 2026: un
 * artifact completo con otto stati, ciascuno con la propria tinta, frequenza di
 * rumore, spinta, respiro, rotazione, guadagno e bagliore. Non sono scelte di
 * stile fatte qui: sono la specifica, e si copiano.
 *
 * ⚠️ **I COLORI NON SONO LETTERALI.** L'invariante 18 e' l'unico che questa
 * sostituzione NON deroga, e costa poco: le otto tinte sono `--au-*` e gli otto
 * caldi cadono sulla rampa che c'era gia'. La misura che lo giustifica sta in
 * §10.1, sopra il blocco `--au-*`.
 *
 * ## Perche' otto stati e non i cinque di prima
 *
 * Il nucleo precedente derivava cinque stati — idle, listening, thinking,
 * speaking, error — da `attivo` e `livello`. Aurora ne chiede otto, e gli otto
 * si derivano dagli **stessi fatti**: nessun topic nuovo, nessuna seconda fonte
 * di verita', nessun dato inventato.
 *
 *     AVVIO         i primi secondi dopo il montaggio
 *     STANDBY       niente di attivo
 *     DIAGNOSTICA   attivo.ascolto — il microfono e' aperto e sta scandendo
 *     ANALISI       attivo.t1 | attivo.t2 | attivo.subagent
 *     DIALOGO       attivo.parla — il TTS sta parlando
 *     MINACCIA      livello warn, oppure attivo.avviso
 *     SOVRACCARICO  livello critical
 *     ARRESTO       offline, o il core non risponde
 *
 * ⚠️ Le frasi finte del riferimento — «Buonasera signore», la telemetria
 * MK-XL, i contatti in avvicinamento — NON sono state portate. L'invariante 23
 * regge: DIALOGO e' guidato dallo spettro TTS vero, che arriva gia' su
 * `voice.spettro`, e dove non c'e' sorgente lo stato e' vuoto e lo dichiara.
 */

/** L'ordine e' quello del riferimento, e l'indice e' identita': lo shader e la
 *  macchina a stati lo usano come chiave. Non si riordina. */
export const STATI = [
  {
    id: "AVVIO", indice: 0, chi: null,
    tinta: "--au-avvio", caldo: "--cy-050",
    freq: 1.6, spinta: 0.10, respiro: 0.4, rotazione: 2.4, guadagno: 0.5,
    bagliore: 0.9, scansione: 3,
    nascita: true,
    detto: "ASSEMBLAGGIO GUSCI",
  },
  {
    id: "STANDBY", indice: 1, chi: null,
    tinta: "--au-standby", caldo: "--cy-500",
    freq: 1.1, spinta: 0.05, respiro: 0.18, rotazione: 0.28, guadagno: 0.12,
    bagliore: 0.24, scansione: 16,
    detto: "RESPIRO PROFONDO",
  },
  {
    id: "DIAGNOSTICA", indice: 2, chi: "ascolto",
    tinta: "--au-diagnostica", caldo: "--cy-200",
    freq: 2.0, spinta: 0.11, respiro: 0.3, rotazione: 0.9, guadagno: 0.4,
    bagliore: 0.55, scansione: 4,
    scandisce: true,
    detto: "SCANSIONE POLARE",
  },
  {
    id: "ANALISI", indice: 3, chi: "pensa",
    tinta: "--au-analisi", caldo: "--cy-200",
    freq: 3.6, spinta: 0.22, respiro: 0.35, rotazione: 3.4, guadagno: 0.45,
    bagliore: 0.78, scansione: 2,
    reticolo: true,
    detto: "RETICOLO ATTIVO",
  },
  {
    id: "DIALOGO", indice: 4, chi: "parla",
    tinta: "--au-dialogo", caldo: "--cy-050",
    freq: 1.9, spinta: 0.11, respiro: 0.9, rotazione: 1.1, guadagno: 0.38,
    bagliore: 0.52, scansione: 6,
    parla: true,
    detto: "SILLABE SCANDITE",
  },
  {
    id: "MINACCIA", indice: 5, chi: "avviso",
    tinta: "--au-minaccia", caldo: "--amber",
    freq: 3.0, spinta: 0.26, respiro: 0.95, rotazione: 2.6, guadagno: 1.3,
    bagliore: 0.95, scansione: 1.1,
    scatto: 1,
    detto: "AMBRA · BATTITO SECCO",
  },
  {
    id: "SOVRACCARICO", indice: 6, chi: null,
    tinta: "--au-sovraccarico", caldo: "--cy-050",
    freq: 4.6, spinta: 0.44, respiro: 1.0, rotazione: 5.0, guadagno: 1.8,
    bagliore: 1.6, scansione: 0.55,
    sovraccarico: 1, scatto: 0.6,
    detto: "INSTABILE · BIANCO",
  },
  {
    id: "ARRESTO", indice: 7, chi: null,
    tinta: "--au-arresto", caldo: "--cy-600",
    freq: 1.4, spinta: 0.06, respiro: 0.2, rotazione: 0.15, guadagno: 0.2,
    bagliore: 0.16, scansione: 22,
    collasso: true,
    detto: "COLLASSO AL PUNTO",
  },
];

/** I tre gusci: raggio, sfasamento, moltiplicatore di frequenza, opacita'.
 *
 * ⚠️ Tre e non uno, e la differenza si vede solo in movimento: i raggi
 * differiscono del 6 % e le fasi di 1,7 radianti, quindi le creste di rumore
 * non coincidono mai e la superficie legge come spessore invece che come
 * membrana. Con un guscio solo il nucleo torna a essere una palla. */
export const GUSCI = [
  { raggio: 1.00, fase: 0.0, freqK: 1.00, opacita: 1.00, reticolo: true },
  { raggio: 1.06, fase: 1.7, freqK: 1.21, opacita: 0.78 },
  { raggio: 1.12, fase: 3.4, freqK: 1.63, opacita: 0.52 },
];

/** Quanto ci mette il mescolatore ad arrivare allo stato nuovo, per secondo.
 *  Il riferimento usa `min(1, dt * 3.2)` su tutto tranne il sovraccarico e il
 *  collasso, che sono piu' lenti perche' sono TRANSIZIONI, non stati. */
export const INSEGUIMENTO = { normale: 3.2, lento: 2.24, nascita: 2.56 };

/** Deriva lo stato Aurora dai fatti che il bus porta gia'.
 *
 * ⚠️ UNICO DEDUTTORE. Come la `statoHud()` che sostituisce, questa funzione e'
 * l'unico posto dove i fatti diventano uno stato, e l'ordine e' una PRIORITA'
 * — non un elenco. Mentre JARVIS parla puo' esserci un T1 attivo: dire
 * «ANALISI» sarebbe vero e inutile.
 *
 * @param {object} f  { attivo, livello, coreVivo, daQuando }
 * @returns {number}  l'indice in STATI
 */
export function statoDa({ attivo = {}, livello = null, coreVivo = null, daQuando = Infinity }) {
  if (livello === "offline" || coreVivo === false) return 7; // ARRESTO
  if (livello === "critical") return 6;                       // SOVRACCARICO
  if (livello === "warn" || attivo.avviso) return 5;          // MINACCIA
  //: L'avvio vince sul resto solo finche' dura davvero: 2,8 s e' il tempo che
  //: il riferimento da' all'innesto dei gusci, e oltre non ha piu' niente da
  //: mostrare.
  if (daQuando < 2.8) return 0;                               // AVVIO
  if (attivo.parla) return 4;                                 // DIALOGO
  if (attivo.ascolto) return 2;                               // DIAGNOSTICA
  if (attivo.t1 || attivo.t2 || attivo.subagent) return 3;    // ANALISI
  return 1;                                                    // STANDBY
}
