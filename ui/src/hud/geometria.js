/* La griglia costruttiva dell'HUD — misurata, non scelta.
 *
 * Ogni numero qui viene dall'analisi forense dell'immagine di riferimento:
 * profilo radiale e clustering su 1024x1024, centro (512, 512). Il documento
 * che li porta è `docs/design-reference/`; questo file è la loro forma
 * eseguibile.
 *
 * ## Perché una tabella e non otto chiamate sparse
 *
 * Perché si legge in una volta sola che i varchi sono tutti diversi (§11.6
 * regola 6) e che i periodi non sono multipli fra loro (§10.3). Sparsi nei
 * componenti, quei due fatti non li verificherebbe nessuno — e il riferimento
 * li ha entrambi.
 *
 * ## ⚠️ LO SPAZIO DI MISURA È IL viewBox, NON LO SCHERMO
 *
 * Il riferimento è disegnato per riempire un fotogramma 1024x1024. Il nucleo
 * di JARVIS OS vive in Ø326, dietro i pannelli. Il rapporto è **0,3184**, e a
 * quella scala i valori del riferimento presi alla lettera diventano:
 *
 *     testo 11 px          ->  3,5 px      illeggibile
 *     mirino r=13          ->  4,1 px      invisibile
 *     waveform 120 barre   ->  0,35 px/barra
 *
 * La regola di adattamento, che vale in tutto il nucleo:
 *
 *   **I RAGGI si conservano come rapporti** (tolleranza ±2 unità su 1024).
 *   **LE DENSITÀ si dimensionano in unità di viewBox** perché cadano sui
 *   gradini veri alla resa reale — vedi `tipografia.js`.
 *
 * Conservare i raggi e riscalare le densità è ciò che tiene la COMPOSIZIONE
 * del riferimento rendendo leggibile il contenuto. Il contrario — riscalare i
 * raggi per far entrare il testo — produrrebbe un altro oggetto.
 *
 * ## Perché gli spessori NON sono quelli del riferimento
 *
 * Il riferimento dà `strokeWidth: 9` per L3. Qui gli spessori vengono dai tre
 * pesi di `tokens.css` con `vector-effect: non-scaling-stroke`, che è §11.8 e
 * l'invariante 18: tre pesi, mai un quarto.
 *
 * Le fasce larghe non sono tratti spessi: sono **superfici**, e si disegnano
 * come contorni chiusi riempiti. È la stessa lezione che il nucleo precedente
 * aveva già pagato — «non sono contorni: sono SUPERFICI, con il dettaglio più
 * chiaro sopra. Un nucleo di soli tratti legge come un disegno tecnico».
 */

//: Il lato del quadrato di misura. Ogni raggio qui dentro è in queste unità.
export const VIEWBOX = 1024;

//: Il centro. Non è 512 per caso: è metà di VIEWBOX, e scriverlo derivato
//: significa che cambiando il lato non resta un 512 orfano da qualche parte.
export const CENTRO = VIEWBOX / 2;

/* ⚠️ I PERIODI, e il difetto che stava NEL RIFERIMENTO — §10.3.
 *
 * Il riferimento dà cinque velocità in gradi al secondo: 6, 12, −8, ±20, −3.
 * Prese alla lettera **non sono utilizzabili**, e la ragione è la stessa che
 * `anim/rings.js` aveva già incontrato in §10.3, dove «46/74/120/240» portava
 * 240 = 2×120:
 *
 *     mirino 6 °/s   ->  60,0 s per giro
 *     segmentato 12  ->  30,0 s          60/30 = 2,000 esatto
 *     tecnico 3      -> 120,0 s         120/60 = 2,000 esatto
 *
 * Due rapporti interi su dieci coppie. Anelli in rapporto intero si
 * riallineano a cadenza fissa, e il ciclo visibile è esattamente ciò che la
 * regola esiste per evitare: dopo un minuto l'occhio riconosce la ripetizione
 * e l'HUD smette di sembrare vivo.
 *
 * Lo scostamento è stato **cercato**, non scelto: fra tutte le combinazioni a
 * ±0,6 °/s, questa è quella di costo minimo che tiene ogni rapporto ad almeno
 * 0,1 da un intero. Costa **0,4 °/s in tutto**, su due anelli soli, e gli altri
 * tre restano ai valori esatti del riferimento.
 *
 *   mirino      6,0 -> 5,7 °/s     63,2 s
 *   segmentato 12,0 -> 12,0        30,0 s     invariato
 *   quadranti  −8,0 -> −8,0        45,0 s     invariato
 *   vetro      20,0 -> 20,0        18,0 s     invariato
 *   tecnico    −3,0 -> −3,1       116,1 s
 *
 * Il rapporto più vicino a un intero è adesso 1,839 (mirino/tecnico): 0,161 di
 * margine, contro lo 0,065 che il nucleo precedente accettava fra 233 s e 46 s.
 * Un test lo conta — `tests/test_nucleo.py` — perché un numero che qualcuno
 * «arrotonda per pulizia» rimette il difetto senza che nulla lo dica.
 */
export const GRADI_AL_SECONDO = {
  mirino: 5.7,      // L1 — era 6,0: 60 s era il doppio esatto di L3
  segmentato: 12.0, // L3 — invariato
  quadranti: -8.0,  // L4 — invariato
  vetro: 20.0,      // L6 — invariato
  tecnico: -3.1,    // L7 — era −3,0: 120 s era il doppio esatto di L1
};
/* Gli otto strati, dal centro verso il bordo.
 *
 * `r` è il raggio in unità di viewBox. Dove uno strato ha più cerchi, `r` è un
 * elenco: sono tracce distinte, non un intervallo.
 *
 * ⚠️ **NESSUNA CIRCONFERENZA NUDA.** È la regola 3 del riferimento, ed è la
 * differenza fra un HUD e un diagramma: ogni anello porta graduazioni,
 * segmenti, tacche, archi o dati. Un cerchio con un tratto uniforme e niente
 * sopra è sbagliato — e nella tabella si vede, perché ogni riga ha almeno un
 * campo di dettaglio.
 */
export const STRATI = [
  {
    id: "mirino",                       // L1
    r: [13, 23, 32],
    tacche: { su: 23, quante: 4, lunghe: 6 },   // le quattro cardinali
    tratteggio: { su: 32, dash: [3, 5] },
    peso: "hair",
    ruota: "mirino",
    //: Lo scatto di aggancio: il riferimento lo dà «ogni ~6 s», e non è una
    //: rotazione — è un evento con un'easing secca. Vedi `moto.js`.
    scattoOgniS: 6,
  },
  {
    id: "logo",                         // L2
    r: [66, 81],
    varco: { da: 4.45, ampiezza: 0.42 },        // in basso, come il riferimento
    peso: "hair",
    //: Non ruota: inquadra il nome, e un nome che gira non si legge.
    respiroHz: 0.3,
    respiroAmpiezza: 0.08,
  },
  {
    id: "segmentato",                   // L3 — l'anello hero, il più luminoso
    r: [112],
    fascia: 9,
    dash: [42, 14, 8, 14],
    peso: "base",
    ruota: "segmentato",
    glow: true,
    audio: 2.0,                          // velocità ×(1 + 2A)
  },
  {
    id: "quadranti",                    // L4
    r: [127, 146, 160, 176, 201, 216],
    tacche: { su: 176, quante: 72, lunghe: 8 },  // 1/72 di giro
    //: Anche L4 ha una superficie, fra la traccia a 176 e quella a 201: nel
    //: profilo radiale del riferimento quella zona sta a L 75-95, non a 48.
    /* ⚠️ Le fasce si allargano DOVE IL PROFILO DEL RIFERIMENTO E' CHIARO.
       Misurato sul suo profilo radiale, la zona fra il 46 % e il 69 % del
       raggio e' la piu' luminosa di tutto l'HUD — picchi a 110-117 — mentre
       la mia ci arrivava a 45. Erano fasce sottili su un fondo che scendeva. */
    /* ⚠️ Stretta, non larga. Con 40 unita' questa fascia toccava quella di L5
       e le due leggevano come una sola banda: il riferimento le tiene separate
       da un corridoio scuro, ed e' quel corridoio a farle leggere come DUE. */
    fasciaCampo: { su: 216, spessore: 18 },
    archiParziali: [
      { su: 146, da: 0.35, ampiezza: 1.9 },
      { su: 201, da: 3.6, ampiezza: 1.2 },
    ],
    peso: "hair",
    ruota: "quadranti",
  },
  {
    id: "globo",                        // L5 — l'unico strato davvero 3D
    r: [237],
    /* ⚠️ HA ANCHE UNA GRADUAZIONE SVG, e non è un segnaposto in attesa del 3D.
       Il riferimento mette la sfera dentro un anello graduato: l'anello è
       piatto e la sfera no, e sono due cose. La graduazione si disegna in SVG
       come tutte le altre — nitida a ogni scala, e accendibile come strato.
       F4 aggiunge i punti e il reticolo dentro, in three.js.
       Senza, questo strato sarebbe una circonferenza NUDA, che il riferimento
       non ammette, e non potrebbe accendersi: l'onda ne accendeva sei su
       sette, e `eval_visual` l'ha visto. */
    tacche: { su: 237, quante: 48, lunghe: 7 },
    //: Il retro attenuato è ciò che fa leggere la sfera come trasparente
    //: invece che come un disco di punti.
    retro: 0.32,
    /* ⚠️ LA SFERA E' DECENTRATA, e nel riferimento si vede subito: sta nel
       quadrante di sinistra, non al centro. Non e' un vezzo di composizione —
       una sfera centrata finisce esattamente dietro il nome, e i suoi punti
       piu' fitti (quelli del fronte) rendono la scritta illeggibile. Misurato
       sul riferimento: il centro della sfera sta a circa un ottavo del raggio
       a sinistra e un poco in alto. */
    scostamento: { x: -0.13, y: -0.04 },
    //: La corona attorno al globo e' chiara nel riferimento: e' l'inizio della
    //: zona piu' luminosa dell'HUD (46-69 % del raggio).
    fasciaCampo: { su: 237, spessore: 12 },
    punti: 720,
    meridiani: 6,
    paralleli: 3,
    periodoS: 41,                        // rotY, e non ha rapporto con gli altri
    nutazione: { gradi: 8, hz: 0.05 },
    audio: 0.5,
  },
  {
    id: "vetro",                        // L6 — la banda spessa con i blocchi
    r: [257, 301],
    //: L'anello pieno sotto i due archi. Il blueprint lo misura all'8 % di
    //: opacità; qui è un gradino della rampa, che è la stessa cosa detta con
    //: un token invece che con un'opacità (invariante 18).
    campoPieno: true,
    /* ⚠️ Il campo di L6 NON copre tutta la fascia. Con 257->301 pieni, questa
       banda e quella di L5 si toccavano e leggevano come un unico anello teal
       largo un quinto del raggio — che e' il difetto che ha fatto sembrare il
       nucleo un disco uniforme. Il riferimento tiene le bande separate da
       corridoi scuri, e sono i corridoi a farle contare. */
    campoSpessore: 16,
    archiSolidi: [
      { da: 0.0, ampiezza: 1.22 },       // ~70°
      { da: 3.14, ampiezza: 1.22 },      // opposto
    ],
    lancetta: { minS: 4, maxS: 7 },
    peso: "base",
    ruota: "vetro",
    audio: 1.5,
  },
  {
    id: "tecnico",                      // L7
    r: [318, 325, 340, 351],
    tacche: { su: 340, quante: 144, lunghe: 6 },  // 1/144 di giro
    //: Larga, non un filo: il riferimento porta 102 di luminanza al 69 % del
    //: raggio, e una fascia di sette unita' non ci arriva.
    fasciaCampo: { su: 351, spessore: 16 },
    marcatori: 8,
    peso: "hair",
    ruota: "tecnico",
  },
  {
    id: "hex",                          // L8 — testo e icone
    r: [384, 460],
    /* ⚠️ TRE CORONE DI TESTO, non una — e la differenza l'ha misurata il
       profilo radiale. Fra il 69 % e l'88 % del raggio il riferimento sta fra
       60 e 100 di luminanza; con una corona sola il mio stava fra 30 e 43.
       Li' la luce non viene da una superficie: la fanno le migliaia di
       caratteri, che a distanza si fondono. Una fascia piena leggerebbe come un
       anello dipinto invece che come dati.
       I tre raggi non sono equidistanti: nel riferimento le corone si
       infittiscono verso l'esterno, ed e' quello a dare la profondita'. */
    /* Sei corone, dal 72 % all'89 % del raggio. La prima stesura partiva dal
       76 % e lasciava scoperto il 72-75 %, dove il riferimento sta a 75-100:
       misurato, li' il mio profilo cadeva a 48. Le corone si infittiscono verso
       l'esterno, ed e' quello a dare la profondita'. */
    /* ⚠️ TRE CORONE, NON SEI, e il numero e' il corpo del testo diviso la banda.
     * Le sei precedenti stavano a 15-18 unita' l'una dall'altra: alla resa vera
     * sono 4,8-5,7 px, e il testo e' alto 8,5 px (--t-micro). Si sovrapponevano
     * di quasi meta', e la corona alfanumerica di L8 leggeva come peluria
     * invece che come caratteri — reso e guardato il 1º settembre 2026, col
     * core vivo, perche' a core spento la banda e' vuota per l'invariante 23 e
     * il difetto non si vedeva affatto.
     * Il passo minimo e' 8,5 px x 1,2 = 10,2 px = 32 unita'. La banda che il
     * blueprint da' a L8 e' 384-460, larga 76: 76/32 = 2,4, quindi tre guide. */
    guideTesto: [392, 424, 456],
    guidaTesto: 430,
    scorrimentoCarS: 0.5,                // un carattere ogni 2 s
    /* ⚠️ LE QUATTRO ICONE DICONO QUALCOSA, e nel riferimento no.
     *
     * Lì sono chrome: un chip, un satellite, un triangolo di avviso, un
     * distintivo, messi ai punti cardinali perché riempiono. §25.11 su questo
     * è netto — «il nucleo non è il posto dove mettere ciò che non sta nei
     * pannelli» — e quattro forme che non significano niente sono esattamente
     * ciò che quella riga vieta.
     *
     * Costano poco a rendere vere: ogni icona prende un fatto che il bus già
     * porta, e si accende quando quel fatto è vero. L'aspetto resta quello del
     * riferimento; la differenza è che adesso guardarle serve a qualcosa.
     *
     * `a` è in radianti ORARI DAL VERTICE — 0 in alto, pi greco in basso. Non
     * è la convenzione matematica (0 a destra, antiorario): è quella con cui
     * si leggono i quadranti, ed è la stessa con cui è disegnata la lancetta.
     * Scriverlo qui perché le due non divergano al primo che aggiunge un'icona.
     */
    icone: [
      { a: 0,    nome: "chip",      chi: "agente",
        perche: "agent.mesh: un nodo T1 o T2 sta lavorando" },
      { a: 2.36, nome: "avviso",    chi: "avviso",
        perche: "agent.advisory, o livello sopra soglia §16" },
      { a: 3.93, nome: "satellite", chi: "collegato",
        perche: "il core risponde sul socket" },
      { a: 4.71, nome: "badge",     chi: "voce",
        perche: "voce.abilitata: il microfono è aperto" },
    ],
    peso: "hair",
  },
];

/** Uno strato per id. Solleva se non c'è: un id sbagliato deve fermarsi qui,
 *  non produrre uno strato vuoto che sembra un problema di render. */
export function strato(id) {
  const s = STRATI.find((x) => x.id === id);
  if (!s) throw new Error(`strato inesistente: ${id} — vedi ui/src/hud/geometria.js`);
  return s;
}

/** Il raggio più esterno che la composizione occupa. Serve alla viewBox e a
 *  chi deve sapere quanto spazio chiede il nucleo, senza ricopiare 460. */
export const RAGGIO_MAX = Math.max(...STRATI.flatMap((s) => s.r));
