/* Il catalogo — SPEC-26 §26.3 e §26.4.
 *
 * ## Che cos'e', e perche' non e' un altro dock
 *
 * §26.3 lo dice in una riga: **unifica la barra delle applicazioni e il file
 * manager**, che erano due richieste separate. Sono lo stesso contenitore con
 * due linguette. Il dock di §13 gli cede l'indice dei moduli e le azioni, e
 * resta la striscia di stato.
 *
 * ## Opzione B: un pannello, non una barra a piena larghezza
 *
 * Il riferimento `famiglia-a/01` non ha una barra ancorata in fondo: ha un
 * pannello nella parte centro-bassa, con le cartelle che gli galleggiano
 * accanto. Quello e' il modello scelto.
 *
 * ## Perche' sta nella cornice e non fra i pannelli
 *
 * Il catalogo e' l'INDICE dell'ambiente, e un indice che si puo' seppellire
 * smette di essere un indice — e' la stessa ragione per cui §26.5 dice che
 * un'icona tirata fuori non sparisce dal catalogo. Quindi vive in
 * `#scrivania`, che sta sopra i pannelli (`--z-cornice` in `app.css`), e non
 * in una finestra WinBox.
 *
 * ⚠️ Il suo contenitore ha `pointer-events: none` e solo il catalogo lo
 * riprende: senza, meta' schermo diventerebbe una lastra invisibile che
 * intercetta i clic destinati ai pannelti sotto.
 *
 * ## L'anatomia, MISURATA sul riferimento (non stimata)
 *
 * `scripts/profilo.mjs` da' i bordi leggendo i profili di luminanza. Su
 * `famiglia-a/01`, 901x563 — e questi numeri sono passati da una verifica
 * indipendente che ne ha **smentiti quattro** della prima stesura:
 *
 *   pannello     x 153..495, y 445..~549   ->  343 x ~105 px
 *                                              **38,1 % x ~18,7 % dello schermo**
 *
 *   ①②  testa: frecce e due campi percorso RIEMPITI   y 450..456    6,8 %
 *   ③   linguette a separatore diagonale              y 461..469    8,7 %
 *   ④   griglia di tessere, scorrevole                y 470..526   53 %
 *   ⑤   plinto in PROSPETTIVA con cinque icone        y 527..549   24 %
 *
 * ⚠️ **Non c'e' un piede.** Sotto il plinto c'e' il bordo del pannello.
 *
 * ⚠️ **Le percentuali sono dell'altezza del PANNELLO, mai pixel.** I due
 * schermi hanno proporzioni diverse — 1,600 contro 1,822 — quindi Kx = 1,705 e
 * Ky = 1,497 NON sono lo stesso numero: ogni rapporto trasferito viene
 * moltiplicato per 1,139. Il pannello del riferimento e' 3,33:1; a frazioni
 * invariate da noi diventa **3,79:1**, e chi copiasse il 3,33 sbaglierebbe.
 *
 * ## Quattro numeri smentiti, e vale la pena dire quali
 *
 *   il bordo sinistro non e' 146 — quello e' il pannello video accanto; e' 153
 *   il bordo destro non e' 488 — 488..493 e' la CANALETTA della barra di
 *     scorrimento (23/71 pixel pieni), il bordo vero e' 494-495
 *   il bordo alto non e' 447 — 447 e' gia' l'incasso scuro DENTRO la cornice
 *   il pannello **NON e' centrato**: centro a x=324 contro i 450,5 dello
 *     schermo, margini 17 % a sinistra e 45 % a destra, rapporto 1 : 2,65
 *
 * I primi due si compensavano — 146..488 e 153..495 danno entrambi 343 px — e
 * la larghezza sopravviveva a due errori. Il CENTRO no.
 *
 * ⚠️ L'altezza del pannello non e' misurabile con certezza: sotto y=512 il
 * fondo del pannello e il fondo della scrivania distano **1-3 livelli su 255**.
 * Le letture indipendenti danno da 103 a 110 px (18,3-19,5 %). Si prende il
 * centro della banda e lo si DICHIARA, invece di fingere un numero solo.
 *
 * ## Dove finisce la griglia e comincia il plinto e' una SCELTA
 *
 * Le icone stanno SOPRA la lastra e sconfinano nella fascia della griglia, per
 * cui esistono due tagli entrambi coerenti: griglia 66 % + lastra sola 10 %,
 * oppure griglia 53 % + plinto-con-icone 24 %. Non sono intercambiabili — e'
 * il secondo, e va detto che e' una scelta.
 *
 * ## Il primo giro era due volte troppo grande
 *
 * Misurato sul nostro scatto, 1536x843: il pannello era **64,5 % x 26,7 %**,
 * cioe' **1,69 volte piu' largo e 1,40 piu' alto**. E la ripartizione interna
 * era rovesciata: plinto 32 % (41 % contando il piede, che il riferimento non
 * ha) contro il 24 %, griglia **39 %** contro 53 %. Il plinto si mangiava la
 * griglia, e la causa erano le icone con l'etichetta di testo sotto.
 *
 * Il ⑥ del riferimento — le cartelle manila fuori dal pannello — e' §26.5, e
 * vive in `desk/icone.js`. Il catalogo gli cede le icone e non le perde: §26.5
 * dice che «l'icona nel catalogo NON sparisce», perche' un indice a cui si
 * tolgono le voci smette di essere un indice.
 *
 * ## Le icone sono RIEMPITE, e la differenza e' misurata
 *
 * Fascia del catalogo nel riferimento: 26,2 % di superficie accesa. Nostro
 * dock di oggi: 2,8 %. Non e' una questione di gusto — le nostre «icone» sono
 * testo a L 96, le sue sono forme piene a L 171-216. Da qui i due token nuovi.
 */

import { animate, stagger, utils } from "../../vendor/anime.esm.min.js";

import { moduliIndicizzati } from "./moduli.js";
import { segno } from "./segni.js";

export const meta = { nome: "catalogo", versione: "1" };

/** Le quattro linguette di §26.3. `pronta` dice se ha davvero un contenuto. */
export const LINGUETTE = [
  { id: "moduli", etichetta: "MODULI", pronta: true },
  { id: "file", etichetta: "FILE", pronta: true },
  // §26.6: le composizioni dichiarate. Ne esiste sempre almeno una — quella
  // di avvio, che `moduli.js` porta con se'.
  { id: "scene", etichetta: "SCENE", pronta: true },
  // §26.7 esiste come sezione, non come contenuto. Si dichiara vuota invece di
  // sparire — invariante 23, e una linguetta che compare fra due passi sposta
  // tutte le altre sotto il dito di chi la stava usando.
  { id: "sistema", etichetta: "SISTEMA", pronta: false },
];

/** I comandi dell'AMBIENTE. Non sono contenuti, e per questo NON stanno piu'
 *  sul plinto: stanno nella riga delle linguette, dove il riferimento lascia
 *  meta' riga vuota. Il plinto e' la barra delle applicazioni, e una barra
 *  delle applicazioni mostra applicazioni. */
const AZIONI = [
  { id: "nascondi", etichetta: "nascondi tutto", tasto: "Alt+H",
    fai: (s) => s.nascondiTutto() },
  { id: "affianca", etichetta: "affianca", tasto: "Alt+T",
    fai: (s) => s.affianca() },
  { id: "tutto", etichetta: "togli il filtro", tasto: "Alt+1…4",
    fai: (s) => s.tutto() },
];

/* ⑤ IL PLINTO E' LA BARRA DELLE APPLICAZIONI.
 *
 * §26.3 lo scriveva gia' e non lo avevamo costruito: «plinto in prospettiva
 * con le icone IN EVIDENZA». Nel riferimento sono cinque, poggiate sul
 * pavimento in prospettiva, e sono l'unica cosa piena e chiara del catalogo.
 * La griglia sopra e' l'INDICE completo e scorrevole; il plinto e' cio' che
 * sta in primo piano.
 *
 * ⚠️ **Cambiano con la linguetta.** La nav appena sopra dice la categoria, e
 * la categoria decide quali icone stanno sul pavimento: MODULI mostra i
 * moduli, FILE i file, SCENE le composizioni. Cinque come il riferimento —
 * oltre, il pavimento smetterebbe di essere un primo piano e diventerebbe una
 * seconda griglia.
 */
/* ⚠️ NESSUN TETTO, e la ragione e' una DECISIONE del 22 agosto 2026.
 *
 * Erano cinque perche' cinque ne mostra il riferimento. Ma cinque e' quello che
 * ci STA, non quello che c'e': con nove moduli, i quattro fuori dal taglio non
 * erano raggiungibili dal plinto in nessun modo.
 *
 * La correzione non e' allargare il plinto — sarebbe rubare alla griglia, che
 * e' il difetto che §26.3 ha gia' corretto due volte. E' che il plinto smette
 * di dover contenere tutto: ne mostra QUATTRO e le altre si raggiungono
 * girando. L'elenco completo e' la griglia, che c'e' gia'.
 *
 * Il proprietario ha scelto fra tre uscite: giostra piu' un registro tabellare
 * accanto (il mockup di famiglia-d), plinto fisso col massimo che ci sta, e
 * **giostra sola**. Ha scelto la terza: un registro accanto a una griglia che
 * elenca gia' le stesse nove voci le farebbe comparire tre volte a schermo. */
const PLINTO_MAX = Infinity;

/* ── LA GIOSTRA — §26.3, il plinto ───────────────────────────────────────────
 *
 * Quattro piastre in vista su un ARCO, e le altre si raggiungono girando.
 *
 * ⚠️ Le quattro della finestra si premono TUTTE dove sono. Non c'e' una
 * piastra «a fuoco» che sia l'unica premibile: l'arco dice che poggiano su un
 * piano, non quale sia quella scelta — e una giostra in cui si puo' premere
 * solo il centro costringe a due gesti per ogni lancio.
 */
/* ⚠️ LA PIASTRA E' PASSATA DA 32 A 64 px, e con lei tutta la giostra.
 *
 * I 32 px erano dichiarati sbagliati da questo stesso file: «40 px su 901» e'
 * il 4,4 % della larghezza, e il 4,4 % dei nostri 1536 fa 68. Trasferendo il
 * pixel invece della frazione se n'era preso meno della meta', proprio sulla
 * misura che il file chiama «la differenza singola piu' grande fra noi e lui».
 * Il numero vive adesso in un posto solo, `--piastra` su `.cat`, perche' e'
 * anche l'unita' di passo della giostra e il ritaglio della scena.
 *
 * ⚠️ E CINQUE PIASTRE DA 68 NON CI STANNO. E' aritmetica, non un'opinione:
 * `.cat__scena` misura **316 px** (il 75 % dei 423,5 di `.cat`, misurato) e
 * cinque piastre larghe 72 — 64 di glifo piu' due varchi da --s-1 — ne
 * vorrebbero almeno 360. Delle due misure del riferimento una doveva cedere.
 * Cede «cinque», e la ragione e' che i cinque venivano da un CONTEGGIO delle
 * icone del riferimento, mentre il lato viene da una FRAZIONE della sua
 * larghezza — e `docs/design-reference/README.md` dice che si trasferisce la
 * frazione.
 *
 * ⚠️ E LE CINQUE SONO TORNATE, senza allargare niente. Il compromesso di sopra
 * — «delle due misure una deve cedere» — nasceva dal 64, e il 64 nasceva da un
 * 4,4 % che non si riproduce (vedi il commento su --piastra). Col lato vero,
 * 32, l'aritmetica cambia segno: cinque piastre a passo 68 fanno 4x68 + 32 =
 * **304 px sui 316** della lastra, il 96 %, e ne restano 12 di margine.
 * Non e' una scelta di composizione presa qui: e' il vincolo che spariva.
 *
 * Il passo: il riferimento ha varco/lato 1,35 (passo 47 su lato 20). A 68 il
 * nostro e' 1,12, a 92 — con quattro piastre — sarebbe 1,88. Cinque e' anche
 * il CONTEGGIO del riferimento, quindi delle tre misure due combaciano e la
 * terza sbaglia di 0,23; con quattro ne combacerebbe una e la terza
 * sbaglierebbe di 0,53. */
const FINESTRA = 5;
//: px fra i centri di due piastre contigue. Non piu' 0,625 x piastra: quel
//: modello dava 52, cioe' cinque piastre su 240 px dei 316 disponibili — la
//: fila tornerebbe vuota, che e' la critica da cui questa sezione nasce. 68
//: riempie il 96 % della lastra ed e' multiplo di 4.
const PASSO = 68;
//: px in piu' attorno a quella al centro. La fila non e' a passo costante: la
//: piastra al centro ha piu' aria, ed e' cosi' che si vede QUALE e' al centro
//: senza doverla schiarire.
//: ⚠️ NON scala con la piastra, e il vincolo e' il RITAGLIO. La scena e'
//: larga 316: la piastra esterna ha il centro a PASSO + APERTURA e il bordo a
//: 36 px oltre, e deve stare dentro 158. 104 + 16 + 36 = 156. Portata a 32
//: come il resto — 104 + 32 + 36 = 172 — le due piastre esterne uscivano
//: tagliate di 14 px, visto sullo scatto.
const APERTURA = 16;
//: gradi di cui una piastra si volta appena lascia il centro. NON scala: e'
//: un angolo, e un angolo non ha una lunghezza da moltiplicare.
const GIRO = 38;
//: px di allontanamento per passo, fino a FUGA_PASSI passi.
const FUGA = 52;
const FUGA_PASSI = 3;

//: Sotto questa velocita' l'inerzia si ferma (§26.4 punto 2).
const FERMO_PX_MS = 0.05;
//: Quanto lontano porta la velocita' al rilascio. Non e' fisica: e' il tempo
//: equivalente di volo, ed e' l'unico numero che decide se il gesto «tira».
const VOLO_MS = 320;

/* R95 — lo stesso `pointerdown` deve saper distinguere due gesti.
 *
 * Premere una tessera comincia SIA lo scorrimento del nastro (§26.4 punto 1)
 * SIA l'estrazione dell'icona (§26.5): sono la stessa pressione sullo stesso
 * elemento, e non si puo' chiedere all'utente di dichiarare quale intende.
 *
 * ## R98 — la prima regola era «piu' verticale che orizzontale», ed era sbagliata
 *
 * Sembrava ovvia: il nastro scorre in orizzontale, quindi un movimento piu'
 * verticale non puo' voler dire «scorri». Con un puntatore vero non funziona.
 * Misurato: prima tessera del catalogo, a x=331; punto di rilascio a x=1106,
 * y=252. Il gesto e' `dx=+775, dy=-416` — **piu' orizzontale che verticale**,
 * eppure e' inequivocabilmente «tira fuori quell'icona e mettila lassu'». La
 * regola non scattava, il nastro scorreva, e non nasceva nessuna icona.
 *
 * La regola giusta e' quella che §26.5 usa a parole: **il gesto ESCE dal
 * nastro.** Non un rapporto fra due numeri — una soglia geografica: il
 * puntatore supera il bordo alto o basso della vista di piu' di
 * `SOGLIA_ESTRAZIONE`. Uno scorrimento resta dentro la fascia per costruzione,
 * quindi le due cose non si possono confondere; e la soglia impedisce che una
 * sbandata di due pixel durante una scorsa veloce tiri fuori un'icona.
 *
 * ⚠️ Deciso per l'estrazione, il nastro TORNA dov'era. Senza, il gesto
 * lascerebbe il catalogo scorso di qualche pixel per un movimento che non
 * voleva scorrere niente. */
const SOGLIA_ESTRAZIONE = 12;

/* Quanto deve muoversi il dito perche' una pressione sul plinto diventi un
 * giro invece di un lancio. E' lo stesso numero e la stessa ragione di
 * `SOGLIA_TRASCINO` in `desk/icone.js`: sotto questa soglia il gesto e' un
 * clic, e premere una piastra non deve mai far girare la giostra di un pixel
 * mentre lo si fa. */
const SOGLIA_GIRO = 4;

export const css = `
/* ⚠️ L'OSPITE dev'essere un box vero.
   Il primo giro gli dava display:contents, che gli toglie il box — e con
   esso lo z-index che app.css da' a #scrivania > *. Il catalogo veniva
   disegnato DIETRO i quattordici pannelli, cioe' non si vedeva affatto. */
.cat-ospite {
  flex: 1;
  display: flex;
  pointer-events: none;
}

/* Il contenitore non deve rubare i clic ai pannelli che gli stanno sotto:
   e' largo quanto la scrivania e alto quanto lo spazio libero.

   ⚠️ NON centrato, e non e' una svista. Misurato sul riferimento: il pannello
   ha il centro a x=324 su 901, cioe' 126 px a sinistra del centro schermo,
   con margini del 17 % a sinistra e del 45 % a destra — rapporto 1 : 2,65.
   Quel 45 % non e' spazio sprecato: e' dove il riferimento tiene le cartelle
   manila, cioe' esattamente il fondo di §26.5. Un catalogo centrato le
   spingerebbe fuori campo o sotto i pannelli.

   Si dichiara col padding e non con justify-content: center piu' un margine
   auto: auto si risolve in un numero di pixel qualunque, e §11.8 vuole
   misure che vengano da una scala o da una frazione dichiarata. */
.cat-ancora {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  padding-left: 17%;
  pointer-events: none;
  padding-bottom: var(--s-2);
}
.cat-ancora > * { pointer-events: auto; }

/* 5,5 x --grid = 605 px su 1536 = 39,4 %, contro il 38,0 % misurato sul
   riferimento. Era 9 x --grid = 990 px, cioe' il 64,5 %. */
.cat {
  /* ⚠️ Poi ridotto del 30 %: 5,5 x 0,7 = 3,85 x --grid = 423,5 px, il 27,6 %
     della scrivania. La frazione resta SCRITTA nel calc invece di essere
     risolta a mano — §11.8 chiede misure che vengano da una scala o da una
     frazione dichiarata, e «3.85» da solo non direbbe da dove viene. */
  width: calc(var(--grid) * 5.5 * 0.7);
  /* Il lato della piastra del plinto. Sta qui e non in tre posti perche' e'
     anche il ritaglio della scena e il centraggio della piastra — una verita'
     sola.

     ⚠️ IL 4,4 % NON SI RIPRODUCE, e i 32 px di due giri fa erano giusti.
     Rimisurato sul riferimento con un righello invece che a occhio: nella
     fascia del plinto di famiglia-a/01, a soglia L>50 e L>60, si contano
     stabilmente CINQUE gruppi di larghezze [20, 15, 19, 20, 21] px, mediana
     20 su 901 = **2,22 %** della larghezza. Il 4,4 % era il doppio del vero, e
     su quel numero il plinto era stato portato da 32 a 64: le piastre sono
     diventate il 4,23 % misurato sullo scatto, cioe' quasi il doppio del
     riferimento, ed e' la ragione per cui a occhio erano troppo grandi.
     Il 2,22 % di 1536 fa 34 px; --s-4 e' 32, cioe' il 2,08 %: 0,14 punti di
     scarto contro i 2,01 che il 64 lasciava aperti. */
  --piastra: var(--s-4);
  display: flex;
  flex-direction: column;
  background: var(--bg-panel);
  border: var(--line-base) solid var(--cy-900);
  border-radius: var(--radius);
  font-family: var(--font-ui);
}

/* ① ② la testa: frecce e i due campi percorso RIEMPITI */
/* La testa del riferimento e' alta 7 px su 107, cioe' il 6,5 %: due campi
   riempiti e le frecce, senza padding verticale. L'altezza la fa la riga di
   testo, non lo spazio intorno. */
.cat__testa {
  display: flex;
  align-items: stretch;
  gap: var(--s-1);
  padding: 0 var(--s-1);
  border-bottom: var(--line-hair) solid var(--cy-900);
  line-height: 1.4;
}
.cat__freccia {
  background: none;
  border: var(--line-hair) solid var(--cy-900);
  border-radius: var(--radius);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  padding: 0 var(--s-1);
  cursor: pointer;
}
.cat__freccia:hover { color: var(--icona-viva); border-color: var(--cy-700); }
.cat__percorso {
  background: var(--fill-3);
  color: var(--bg-void);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  padding: 0 var(--s-2);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* Le proporzioni del riferimento: il campo lungo circa il 70 % della testa,
   il corto il 30 %. */
.cat__percorso--lungo { flex: 7; }
.cat__percorso--corto { flex: 3; }
/* Lo stato e la versione stanno nella riga delle LINGUETTE, a destra: nel
   riferimento le linguette occupano solo la meta' sinistra, e quello spazio
   li' e' l'unico posto in cui ci stanno senza allungare il pannello. */
/* flex: 1 e non margin-left: auto. auto si risolve in un numero di pixel
   qualunque — 76,95 al primo giro dell'audit — e §11.8 vuole spaziature che
   vengano dalla scala. Lo spazio lo assorbe questo elemento, e resta uno
   spazio: non diventa una misura. E' la stessa correzione gia' fatta in
   barra.js. */
.cat__stato {
  flex: 1;
  align-self: center;
  text-align: right;
  padding-right: var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  color: var(--txt-dim);
}

/* ③ le linguette, a separatore diagonale come nel riferimento */
/* ⚠️ A 423,5 px la fascia andava su TRE righe, e non per un errore di
   spaziatura: i figli sommano 421,8 su 421,9 disponibili. Con «flex: 1» i due
   campi di stato venivano compressi a 73,8 px, il secondo ne aveva bisogno di
   52 per la propria riga piu' lunga, e finiva a capo — l'altezza della fascia
   non la decideva piu' il line box ma il testo che si spezzava, e passava da
   24,8 a 34,4 px.
   «flex: 1 0 auto» cresce quando c'e' spazio e non scende sotto il proprio
   contenuto quando non c'e'. Quello che manca lo prende lo scorrimento qui
   sotto: le linguette stanno PRIME nel DOM, quindi a riposo si vedono tutte e
   quattro e sono i due campi — che sono LETTURE, non comandi — a cadere oltre
   il bordo. E' la priorita' giusta. */
.cat__stato { flex: 1 0 auto; white-space: nowrap; }
.cat__linguette {
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x proximity;
}
.cat__linguette > * { scroll-snap-align: start; }
.cat__linguette {
  display: flex;
  align-items: stretch;
  background: var(--bg-raised);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.cat__linguetta {
  position: relative;
  background: none;
  border: 0;
  border-radius: var(--radius);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.14em;
  /* 8,4 % di 107 px sono 9: una riga di micro e uno spazio per lato. */
  padding: 0 var(--s-2);
  line-height: 1.6;
  cursor: pointer;
}
/* Il separatore diagonale: una linea inclinata fra una linguetta e l'altra,
   disegnata col bordo di uno pseudo-elemento ruotato. Non un carattere: un
   glifo dipenderebbe dal font e si disallineerebbe al primo cambio di corpo. */
.cat__linguetta + .cat__linguetta::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-left: var(--line-hair) solid var(--cy-900);
  transform: rotate(20deg);
}
.cat__linguetta[aria-selected="true"] { color: var(--icona); background: var(--fill-1); }
.cat__linguetta[data-vuota] { color: var(--txt-ghost); }
.cat__linguetta:hover { color: var(--icona-viva); }

/* ④ la griglia: scorre in orizzontale, e la barra la disegna nessuno */
/* ⚠️ LA GRIGLIA CEDE LO SBALZO DELLE PIASTRE, e senza questa riga le ultime
   tessere ci finiscono sotto.
   Il plinto e' alto --s-4 ma le piastre poggiano sul suo bordo LONTANO e
   crescono verso l'alto: sfondano nella fascia di sopra di quanto sono alte.
   Visto sullo scatto della finestra vera — le piastre coprivano la terza riga
   di tessere — e non nel DOM, dove sono due elementi che non si toccano perche'
   stanno in due contenitori diversi.
   Si cede il BOX, non il contenuto: un padding in fondo a un contenuto che
   scorre libera l'ultima colonna e lascia quelle di mezzo dov'erano. Le stesse
   due misure da cui nasce lo sbalzo: --piastra + --s-1.

   ⚠️ Ed e' successo di nuovo, il 23 agosto 2026, per la ragione che questa
   riga avrebbe dovuto impedire: il margine era scritto --s-4 + --s-1, cioe'
   con la misura della piastra COPIATA invece che riferita. Portata la piastra
   a --s-5, il margine e' rimasto a 36 e le piastre sono tornate a coprire la
   seconda riga di tessere — visto sullo scatto, 25 px di sovrapposizione.
   Adesso il margine legge --piastra, che e' lo stesso valore da cui nasce
   lo sbalzo: una verita' sola, e la prossima volta si muovono insieme. */
.cat__vista {
  position: relative;
  overflow: hidden;
  height: calc(var(--grid) * 0.8);
  margin-bottom: calc(var(--piastra) + var(--s-1));
  background: var(--bg-void);
  cursor: grab;
  touch-action: pan-y;
}
.cat__vista[data-presa] { cursor: grabbing; }
/* Il nastro impila in COLONNE e va a capo verso destra.
   Con tessere da 20 px in una vista alta 84 una riga sola le lasciava nuotare
   in mezzo al vuoto; il riferimento e' un mosaico su piu' righe. Cosi' e'
   mosaico E resta scorrimento ORIZZONTALE, che e' cio' che §26.4 prescrive:
   le colonne crescono verso destra, mai verso il basso. */
.cat__nastro {
  display: flex;
  flex-direction: column;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: var(--s-1);
  padding: var(--s-1);
  height: 100%;
  will-change: transform;
}
/* ⚠️ L'INVERSIONE, misurata sui riquadri corrispondenti.
 *
 *                griglia                icone plinto      cartelle
 *   riferimento  #0e1319 L 18, 0,0 %>L90   15,2 %>L90     31,2 %>L90
 *   nostro       #336276 L 89, 6,9 %>L90    3,1 %>L90     non esistevano
 *
 * Avevamo messo il colore nella GRIGLIA e lasciato spente le ICONE. Il
 * riferimento fa il contrario: la griglia e' un fondo quasi nero su cui il
 * contenuto poggia, e tutta la luce sta nelle icone e nelle cartelle.
 *
 * Quindi il fondo della tessera scende a --bg-panel (L 31) e sale a --fill-1
 * (L 66) SOLO sotto il puntatore o quando e' selezionata: **una per volta**,
 * non tutte. Accendere ogni tessera e' come non accenderne nessuna.
 *
 * ⚠️ E le tessere diventano PICCOLE E MOLTE. Il riferimento ne ha ~40 da
 * 28x14 px; noi ne avevamo otto da 100x70, e con otto voci lo scorrimento a
 * inerzia di §26.4 non aveva motivo di esistere. 20 px piu' 4 di gap fanno 24
 * per tessera: **venticinque in vista** su 603 px.
 *
 * ⚠️ **I 20 px sono SBAGLIATI, e il perche' e' una regola generale** (22
 * agosto 2026). «28x14 px» e' misurato su un pannello catalogo largo 342 in
 * un'immagine larga 901; il nostro pannello e' largo 605. Il numero da
 * trasferire non e' il pixel, e' la FRAZIONE: 28 / 342 = 8,2 % della
 * larghezza, che da noi fa **50 px**, e 14 / 105 = 13 % dell'altezza della
 * griglia. Trasferendo il pixel si e' preso meno della meta' — e nello stesso
 * passaggio il rettangolo 2:1 e' diventato un quadrato, che e' un secondo
 * errore nella stessa riga.
 *
 * Non le ho ridimensionate qui: 50x33 e' una decisione sulla griglia, e in
 * questo passaggio e' stata presa una decisione sul PLINTO. Sta scritto perche'
 * il prossimo giro parta dal numero giusto invece che da questo.
 * La regola sta in docs/design-reference/README.md, «un numero in pixel del
 * riferimento non e' un bersaglio».
 *
 * Il nome se ne va dalla tessera — a 20 px non ci sta, e il riferimento non
 * ne ha — e resta in title e aria-label. E' la stessa scelta gia' fatta
 * per il plinto: togliere il testo non e' togliere l'informazione. */
.cat__tessera {
  flex: 0 0 auto;
  /* ⚠️ 48x32, e prima erano 20x20 — la correzione che il commento qui sopra
     aveva dichiarato e rinviato («50x33 e' una decisione sulla griglia»).
     Il numero da trasferire e' la FRAZIONE: 28/342 = 8,2 % della larghezza,
     che sui nostri 605 fa 50, e 14/105 = 13 % dell'altezza fa 33.
     Dalla scala si prendono 48 = --s-4 + --s-3 e 32 = --s-4: rapporto 1,5:1
     contro l'1,52:1 del riferimento, e nessun letterale. I 20 px quadrati
     erano due errori nella stessa riga — meno della meta' della misura, e un
     rettangolo 2:1 diventato quadrato. */
  width: calc(var(--s-4) + var(--s-3));
  height: var(--s-4);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-panel);
  border: var(--line-hair) solid var(--cy-900);
  border-radius: var(--radius);
  /* ⚠️ padding: 0 esplicito e tipografia dichiarata anche senza testo.
     Tolto il nome, il <button> tornava al padding dell'agente utente (1px 6px,
     fuori dalla scala) e ad Arial 13,33 px, e con lui il suo svg e il suo
     path: e' lo stesso difetto dei pulsanti del plinto, e l'audit l'ha visto
     subito tutte e due le volte. Un elemento senza parole ha comunque una
     tipografia e una spaziatura. */
  padding: 0;
  color: var(--icona);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  cursor: pointer;
  /* §26.4: hover e pressione sono STATI, quindi transizione CSS e mai
     anime.js — allocare un oggetto animazione a ogni passaggio del puntatore
     su venticinque icone e' il modo esatto di sforare i 4 ms di §10.4. */
  transition: background 120ms linear, color 120ms linear;
}
.cat__tessera:hover { background: var(--fill-1); color: var(--icona-viva); }
.cat__tessera[aria-pressed="true"] { background: var(--fill-1); color: var(--icona-viva); }
.cat__tessera[data-fuori] { color: var(--txt-dim); }
.cat__segno { display: flex; color: inherit; }

.cat__vuoto {
  display: flex;
  align-items: center;
  padding: var(--s-3);
  color: var(--txt-dim);
  font-family: var(--font-mono);
  font-size: var(--t-data);
}

/* L'indicatore di posizione: una tacca, non una barra di scorrimento. */
.cat__indicatore {
  height: var(--line-bold);
  background: var(--bg-raised);
}
.cat__tacca {
  display: block;
  height: 100%;
  background: var(--cy-700);
  will-change: transform;
}

/* ⑤ il plinto, in PROSPETTIVA — una lastra piu' larga davanti.
   E' la stessa tecnica di §11.4 gia' usata per i piani d'archivio e la board:
   CSS 3D, non three.js, perche' il testo deve restare nel DOM (invariante 20). */
/* Il plinto vale il **24,3 %** dell'altezza del pannello nel riferimento, e ne
   valeva il 41 % da noi: si mangiava la griglia, che invece deve valerne il
   53 %. La differenza era tutta nelle icone da 32 px con l'etichetta di testo
   sotto — che il riferimento NON ha: cinque icone, nessuna parola. */
/* ⚠️ La PROSPETTIVA e' misurata, non scelta a occhio. Lo svaso del
   riferimento (vicino/lontano) vale 1,13-1,15; con perspective: 4 x --grid
   e una lastra alta ~40 px se ne ottiene 1,077, cioe' la meta'. Il valore che
   riproduce lo svaso dentro il budget del 24 % e' ~249 px = 2,25 x --grid.
   Il primo giro azzeccava lo svaso per il motivo sbagliato: la lastra era alta
   63,5 px, cioe' il plinto sforava. */
/* ⚠️ IL PLINTO DICHIARA LA PROPRIA ALTEZZA, e prima gliela dava il contenuto.
   Da quando le piastre sono fuori dal flusso — appese al filo lontano — dentro
   non c'e' piu' niente che occupi spazio, e il plinto collassava a 4 px di
   padding: la lastra restava alta come un filo e nello scatto si vedeva solo
   il bordo ciano, con le piastre poggiate sul nulla.
   --s-4 meno il padding fa 28 px di lastra, che ruotati di 52° ne proiettano
   17: il 7,3 % dell'altezza del pannello, contro l'8,4 % misurato sul
   riferimento. Ed e' anche il motivo per cui le piastre possono essere alte
   quanto vogliono senza rubare spazio alla griglia. */
.cat__plinto {
  position: relative;
  height: var(--s-4);
  perspective: calc(var(--grid) * 2.25);
  padding-top: var(--s-1);
  border-top: var(--line-hair) solid var(--cy-900);
}
/* ⚠️ Il trapezio si allarga scendendo, perche' e' un pavimento in prospettiva.
   Il bordo LONTANO e' il **75 %** del pannello, non il 66 % che la stesura
   precedente aveva letto: con 17 % di inset il pavimento risultava piu'
   STRETTO delle piastre che ci stanno sopra, ed e' il genere di errore che si
   vede solo mettendo un righello sul riferimento. 12,5 % da' il 75 % per
   costruzione; lo svaso lo fa la prospettiva.

   ⚠️ E LA LUCE VIENE DA DAVANTI. Campionato sul ritaglio del riferimento:
   bordo lontano L 51, corpo L 59 -> 65, bordo vicino L 71. Il gradiente va
   quindi dal buio in fondo alla luce davanti. Le stesure precedenti avevano il
   corpo piatto a --fill-1 con l'accento sul bordo LONTANO — esattamente al
   rovescio — ed e' per questo che il trapezio non si leggeva come un pavimento
   ma come una fascia storta.
   ⚠️ E la coppia di token NON e' --bg-raised -> --bg-deep, che pure sarebbe
   nel verso giusto. Misurata a schermo: 37 e 30 contro un pannello a 31, cioe'
   un pavimento che non si vede — nello scatto restava solo il filo ciano del
   bordo lontano, e le piastre poggiavano sul nulla. La rampa del riferimento
   e' 51 -> 71, venti punti di salita; --bg-raised (37) -> --fill-1 (66) ne fa
   ventinove ed e' la sola coppia di token che copre quel salto.
   Nessun ciano nel corpo: nel riferimento il pavimento non ha un solo pixel di
   accento — il ciano sta sul filo, e li' basta. */
.cat__lastra {
  position: absolute;
  left: 12.5%;
  right: 12.5%;
  top: var(--s-1);
  bottom: 0;
  background: linear-gradient(to bottom, var(--bg-raised), var(--fill-1));
  border-top: var(--line-base) solid var(--cy-300);
  transform: rotateX(52deg);
  transform-origin: top center;
}
/* Cinque icone che OCCUPANO la lastra, non tre perse in mezzo. La lastra e'
   il 66 % del pannello: 5 x 32 px piu' quattro varchi da 32 fanno 288 su 399,
   cioe' il 72 % del suo bordo lontano. */
/* ⚠️ DUE ELEMENTI, e la ragione e' una regola del motore: **un overflow
   diverso da visible forza transform-style: flat**. Una fila messa a scorrere
   dentro il plinto perde la Z delle piastre, ed e' per questo che la prima
   stesura era una fila piatta appoggiata a un pavimento in prospettiva — due
   linguaggi nello stesso mezzo centimetro.
   Quindi: «.cat__scena» RITAGLIA e dichiara la prospettiva, «.cat__azioni»
   dentro tiene la profondita' e non ritaglia niente.

   ⚠️ Il bordo alto della scena e' NEGATIVO di --s-5: le piastre si alzano
   sopra il plinto — e' quello sbalzo a farle leggere come poggiate sul
   pavimento invece che stampate dentro — e un ritaglio a filo le
   decapiterebbe. */
.cat__scena {
  position: absolute;
  /* ⚠️ Il ritaglio segue la LASTRA, non il pannello, e con lo stesso inset del
     12,5 %. Con la scena larga quanto il pannello si vedevano sette piastre su
     nove — misurato, centri da 355 a 701 su una lastra che finisce a 631 — e
     due galleggiavano fuori dal pavimento, sul fondo del catalogo. Una piastra
     che non poggia su niente non e' una barra delle applicazioni, e' un'icona
     smarrita. */
  left: 12.5%; right: 12.5%; bottom: 0;
  top: calc(var(--piastra) * -1);
  overflow: hidden;
  perspective: calc(var(--grid) * 2.25);
  pointer-events: none;
}
/* ⚠️ NON PIU' UN FLEX. Le piastre stanno tutte allo STESSO punto — il centro
   della fila — e da li' ognuna si sposta col proprio transform. Nel flusso la
   posizione la decideva il layout e la profondita' non poteva entrarci; cosi'
   posizione, giro e profondita' sono una dichiarazione sola, cioe' una cosa
   sola da animare. */
/* ⚠️ LE PIASTRE POGGIANO SUL BORDO LONTANO, e la prima stesura le ancorava al
   fondo del plinto: galleggiavano sopra il pavimento con un varco in mezzo, e
   una piastra che non poggia su niente non e' una barra delle applicazioni, e'
   un'icona smarrita. Il bordo LONTANO del trapezio e' il suo lato ALTO — la
   lastra ruota di 52° attorno al proprio bordo superiore, che quindi resta
   dov'e' — cioe' il bordo alto del plinto.
   La riga qui e' un'ALTEZZA ZERO posata li': le piastre hanno «bottom: 0» e
   crescono verso l'alto, sfondando la scena, che per questo comincia --s-5
   piu' su. */
.cat__azioni {
  position: absolute;
  left: 0; right: 0;
  top: var(--piastra);
  height: 0;
  transform-style: preserve-3d;
  pointer-events: auto;
  cursor: grab;
  touch-action: none;
}
.cat__azioni[data-presa] { cursor: grabbing; }

/* Le frecce stanno FUORI dalla scena, o girerebbero con lei. Si spengono agli
   estremi: una freccia che non porta da nessuna parte e' un bersaglio che
   mente. */
.cat__gira {
  position: absolute;
  bottom: var(--s-3);
  background: none;
  border: 0;
  border-radius: var(--radius);
  padding: 0 var(--s-1);
  color: var(--icona);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  cursor: pointer;
  transition: color 120ms linear;
}
.cat__gira[data-verso="-1"] { left: var(--s-1); }
.cat__gira[data-verso="1"] { right: var(--s-1); }
.cat__gira:hover { color: var(--icona-viva); }
.cat__gira[disabled] { color: var(--txt-ghost); cursor: default; }
/* ⚠️ Nessuna etichetta sotto l'icona: nel riferimento le cinque icone del
   plinto sono forme e basta. Il nome resta nel title, insieme alla
   scorciatoia — il testo non sparisce, cambia posto. Cosi' il plinto sta nel
   24 % che gli spetta invece di rubarlo alla griglia.
   Il contrasto che aveva reso illeggibili le etichette (--txt-ghost sulla
   lastra: 1,82:1, misurato) non e' piu' un problema perche' non c'e' piu'
   testo sulla lastra. */
/* I comandi dell'ambiente, nella riga delle linguette. */
.cat__comandi {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding-right: var(--s-2);
}
.cat__comando {
  background: none;
  border: 0;
  border-radius: var(--radius);
  padding: 0;
  display: flex;
  align-items: center;
  cursor: pointer;
  /* Anche il COLORE va dichiarato, non solo famiglia e corpo: tolta
     l'etichetta il pulsante ereditava buttontext dell'agente utente, cioe'
     nero, e con lui i suoi svg e path. Ventiquattro violazioni all'audit per
     una proprieta' che sembrava non servire perche' non c'e' testo. */
  color: var(--txt-dim);
  transition: color 120ms linear;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
}
.cat__comando:hover { color: var(--icona-viva); }

/* ⚠️ APERTO = PIASTRA, CHIUSO = SIMBOLO NUDO.
   Nel riferimento le cinque icone del plinto hanno cinque trattamenti diversi
   — due piastre piene col simbolo scuro, un simbolo chiaro nudo, un filo di
   contorno, un disco scuro con l'anello chiaro — ed e' quella varieta' che la
   fa leggere come una barra delle APPLICAZIONI e non come una legenda.
   Da noi la varieta' non si inventa: la porta il solo fatto che una barra
   delle applicazioni ha qualcosa da dire. Il primo giro aveva reso tutte le
   piastre uguali e piu' chiare quando aperte, cioe' la stessa forma con due
   luminanze: e' proprio l'errore che §26.3 dichiara per il dock vecchio,
   «otto quadrati grigi uguali non distinguono niente». */
/* ⚠️ APERTO NON SI DICE PIU' SCHIARENDO, ed e' un cambio rispetto al primo
   giro della giostra: li' la piastra chiusa era un simbolo nudo e quella
   aperta una piastra chiara. Adesso **tutte** le piastre sono piene e chiare,
   quindi schiarirne una di piu' non direbbe niente — direbbe solo «questa e'
   un po' piu' chiara», che a 32 px non e' una lettura.
   Lo dice un filo sul bordo ALTO, a --cy-500: e' il token con cui questo
   sistema dice gia' «questo e' quello corrente» — il marcatore del pannello
   col fuoco in app.css, la cella di oggi nel calendario — e ripetere la stessa
   frase con lo stesso colore e' l'opposto di aggiungere un segno nuovo. */
.cat__azione[aria-pressed="true"] {
  border-top: var(--line-bold) solid var(--cy-500);
}
.cat__azione[data-fuori] { color: var(--txt-dim); }

/* ⚠️ Famiglia e corpo restano dichiarati anche senza testo. Tolta
   l'etichetta, il pulsante e i suoi discendenti — svg, path — tornavano ad
   Arial 13,33 px, cioe' fuori dal sistema tipografico: l'audit lo ha visto
   subito. Un elemento senza parole ha comunque una tipografia. */
.cat__azione {
  position: absolute;
  bottom: 0;
  left: 50%;
  margin-left: calc(var(--piastra) * -0.5);
  transform-origin: center center;
  will-change: transform;
  /* ⚠️ POLARITA' ROVESCIATA, ed e' l'unica della scrivania insieme
     all'intestazione delle tabelle: piastra chiara col simbolo scuro. E' quello
     che fa staccare la fascia dal resto — nel riferimento il plinto e' l'unica
     zona in cui il fondo e' piu' chiaro del segno — e senza, otto simboli
     grigi su un pavimento grigio sono una legenda, non una barra.
     Il gradiente e' verticale e brevissimo: --icona-viva (L 219) sopra,
     --icona (L 171) sotto. Non e' decorazione, e' la stessa luce del pavimento
     letta su un oggetto che gli sta sopra. */
  background: linear-gradient(to bottom, var(--icona-viva), var(--icona));
  border: 0;
  border-top: var(--line-bold) solid transparent;
  border-radius: var(--radius);
  padding: 0 var(--s-1);
  cursor: pointer;
  display: flex;
  align-items: center;
  color: var(--bg-void);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  /* L'ombra e' ammessa qui e quasi in nessun altro posto: la piastra COPRE il
     pavimento, che e' l'unico caso che l'invariante 19 concede (§10.1), e la
     ricetta e' quella misurata — 2 px di scostamento, 3 di raggio, alpha 0,18. */
  box-shadow: var(--ombra-contatto);
  transition: filter 120ms linear;
}
.cat__azione:hover { filter: brightness(1.12); }

`;

/* ── il componente ───────────────────────────────────────────────────────── */

/**
 * `estrazione` e' il ponte verso `desk/icone.js` (§26.5): tre chiamate —
 * `inizia`, `muovi`, `lascia` — e nient'altro. Il catalogo riporta un GESTO e
 * non sa che cosa sia un'icona libera; che cosa ne esca lo decide chi possiede
 * il fondo della scrivania. Facoltativo: nella galleria non c'e' un fondo, e
 * il catalogo si giudica lo stesso.
 */
export function crea(ospite, { scrivania, bus, estrazione }) {
  const ancora = document.createElement("div");
  ancora.className = "cat-ancora";
  const el = document.createElement("section");
  el.className = "cat";
  ancora.appendChild(el);

  /* ① ② testa */
  const testa = document.createElement("header");
  testa.className = "cat__testa";
  for (const [glifo, etichetta] of [["◀", "indietro"], ["▶", "avanti"]]) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__freccia";
    b.textContent = glifo;
    b.title = etichetta;
    b.setAttribute("aria-label", etichetta);
    // ⚠️ La navigazione a cronologia e' del file manager (§26.8, punto 9).
    // Le frecce ci sono perche' l'anatomia del riferimento le ha; oggi
    // scorrono il nastro, che e' l'unica cosa vera che possono fare.
    b.addEventListener("click", () => scorriDi(glifo === "◀" ? 240 : -240));
    testa.appendChild(b);
  }
  const percorso = document.createElement("span");
  percorso.className = "cat__percorso cat__percorso--lungo";
  percorso.textContent = "—";
  const percorsoCorto = document.createElement("span");
  percorsoCorto.className = "cat__percorso cat__percorso--corto";
  percorsoCorto.textContent = "—";
  testa.append(percorso, percorsoCorto);

  /* Lo stato di T2 sta con le linguette e non nella testa: la testa del
   * riferimento e' due campi riempiti e le frecce, nient'altro. */
  const stato = document.createElement("span");
  stato.className = "cat__stato";
  stato.textContent = "T2 inerte";

  /* ③ linguette */
  const nav = document.createElement("nav");
  nav.className = "cat__linguette";
  nav.setAttribute("aria-label", "categorie del catalogo");
  const linguette = new Map();
  for (const l of LINGUETTE) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__linguetta";
    b.textContent = l.etichetta;
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", "false");
    if (!l.pronta) b.dataset.vuota = "";
    b.addEventListener("click", () => apri(l.id));
    linguette.set(l.id, b);
    nav.appendChild(b);
  }
  /* I comandi dell'ambiente, prima del conteggio: il plinto non e' piu' il
   * loro posto. */
  const comandi = document.createElement("div");
  comandi.className = "cat__comandi";
  for (const a of AZIONI) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__comando";
    b.title = `${a.etichetta} — ${a.tasto}`;
    b.setAttribute("aria-label", `${a.etichetta} (${a.tasto})`);
    b.dataset.azione = a.id;
    b.appendChild(segno(a.id, "var(--s-3)"));
    b.addEventListener("click", () => a.fai(scrivania));
    comandi.appendChild(b);
  }
  nav.append(comandi, stato);

  /* ④ griglia */
  const vista = document.createElement("div");
  vista.className = "cat__vista";
  const nastro = document.createElement("div");
  nastro.className = "cat__nastro";
  vista.appendChild(nastro);
  const indicatore = document.createElement("div");
  indicatore.className = "cat__indicatore";
  const tacca = document.createElement("span");
  tacca.className = "cat__tacca";
  indicatore.appendChild(tacca);

  /* ⑤ plinto */
  const plinto = document.createElement("div");
  plinto.className = "cat__plinto";
  const lastra = document.createElement("div");
  lastra.className = "cat__lastra";
  /* La scena RITAGLIA e dichiara la prospettiva; le azioni dentro tengono la
     profondita'. Due elementi e non uno: vedi il commento nel foglio. */
  const scena = document.createElement("div");
  scena.className = "cat__scena";
  /* ⚠️ Il ritaglio e' VOLUTO e il resto si raggiunge: si dichiara, cosi'
     `densita.mjs --traboccamento` non lo conta come contenuto cancellato.
     Senza, la giostra risultava 293 px di piastre buttate via — che e' proprio
     il difetto che quel controllo esiste per trovare, e sarebbe stato un falso
     positivo capace di nascondere quelli veri. */
  scena.dataset.scorreAMano = "rotella, trascinamento o le due frecce";
  const azioni = document.createElement("div");
  // Il pavimento nasce vuoto: chi ci sale lo decide la linguetta.
  azioni.className = "cat__azioni";
  scena.appendChild(azioni);
  //: Le frecce stanno FUORI dalla scena, o girerebbero con lei.
  const frecce = [-1, 1].map((verso) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat__gira";
    b.dataset.verso = String(verso);
    b.textContent = verso < 0 ? "\u25c2" : "\u25b8";
    b.title = verso < 0 ? "indietro" : "avanti";
    b.setAttribute("aria-label", b.title);
    b.addEventListener("click", () => vaA(Math.round(giostra.indice) + verso, true));
    return b;
  });
  plinto.append(lastra, scena, ...frecce);

  /* ⚠️ Il PIEDE non c'e' piu'. Il riferimento non ne ha uno: sotto il plinto
   * c'e' il bordo del pannello e basta, e quei 43 px erano un sesto
   * dell'altezza spesi per due righe di testo. Cio' che diceva non si perde,
   * cambia posto: il conteggio e la versione vanno **nella riga delle
   * linguette**, a destra, dove il riferimento lascia meta' riga vuota. */
  const conteggio = document.createElement("span");
  conteggio.className = "cat__stato";
  nav.appendChild(conteggio);

  el.append(testa, nav, vista, indicatore, plinto);
  ospite.appendChild(ancora);

  /* ── il contenuto delle linguette ────────────────────────────────────── */

  let attiva = "moduli";
  let fileVisti = [];
  let apertiOra = new Set();
  let filtroOra = null;
  let sceneOra = [];
  let scenaOra = null;

  function voci() {
    if (attiva === "moduli") {
      return moduliIndicizzati().map((m) => ({
        id: m.id, etichetta: m.etichetta, categoria: m.categoria,
        tipo: "modulo", segno: m.id, acceso: apertiOra.has(m.id),
        fai: () => scrivania.alterna(m.id),
      }));
    }
    if (attiva === "scene") {
      // §26.6: «Catalogo: linguetta SCENE, un'icona per scena.»
      return sceneOra.map((s) => ({
        id: s.nome, etichetta: s.nome, tipo: "scena", segno: "scena",
        // Categoria 1: una scena non appartiene a un dominio, e il filtro
        // delle categorie non deve poterla spegnere.
        categoria: 0, acceso: s.nome === scenaOra,
        titolo: s.descrizione,
        fai: () => scrivania.scena(s.nome),
      }));
    }
    if (attiva === "file") {
      return fileVisti.map((v) => ({
        id: v.nome, etichetta: v.nome,
        segno: v.cartella ? "cartella" : "file",
        categoria: 2, tipo: "file", acceso: false,
        // Aprire un file e' del file manager (§26.8, punto 9). Qui la voce
        // porta al pannello che sa farlo, invece di fingere un'operazione.
        fai: () => scrivania.apri("file"),
      }));
    }
    return [];
  }

  function vuotoDi(id) {
    if (id === "file") return "nessun file: la workspace non e' leggibile";
    if (id === "scene") return "nessuna scena dichiarata in settings.toml";
    return "doctor, impostazioni e cestino — §26.7, non ancora costruiti";
  }

  /**
   * Aggiorna cio' che e' GIA' a schermo: acceso/spento e dentro/fuori filtro.
   *
   * ⚠️ Non ricostruisce. Il primo giro rifaceva l'intera griglia a ogni
   * `osserva()` — cioe' a ogni pannello che si apre, si chiude o prende il
   * fuoco — e con quarantuno tessere significava distruggere e ricreare
   * quarantuno nodi decine di volte al minuto. Si perdevano il fuoco della
   * tastiera e lo stato di hover, e il pulsante che si stava premendo veniva
   * staccato dal documento a meta' del clic: `--verifica-scrivania` lo ha
   * scoperto misurando otto voci che non commutavano mai.
   *
   * Il contenuto si ridisegna solo quando CAMBIA — linguetta nuova, elenco di
   * file nuovo — e lo stato si aggiorna sul posto.
   */
  function aggiorna() {
    for (const b of nastro.querySelectorAll(".cat__tessera")) {
      if (attiva === "moduli") {
        b.setAttribute("aria-pressed", String(apertiOra.has(b.dataset.voce)));
      }
      if (attiva === "scene") {
        b.setAttribute("aria-pressed", String(b.dataset.voce === scenaOra));
      }
      if (filtroOra && Number(b.dataset.categoria) !== filtroOra) b.dataset.fuori = "";
      else delete b.dataset.fuori;
    }
    // Il pavimento e' la barra delle applicazioni: se un modulo si apre o si
    // chiude, l'icona lo dice. Si aggiorna SUL POSTO (R90) e non si ridisegna:
    // ridisegnare qui rifarebbe l'animazione a ogni pannello che prende il
    // fuoco, e sarebbe animazione senza causa (invariante 25).
    for (const b of azioni.querySelectorAll(".cat__azione")) {
      if (attiva === "moduli")
        b.setAttribute("aria-pressed", String(apertiOra.has(b.dataset.voce)));
      if (attiva === "scene")
        b.setAttribute("aria-pressed", String(b.dataset.voce === scenaOra));
    }
    conteggio.textContent = testoConteggio();
  }

  function testoConteggio() {
    const n = nastro.querySelectorAll(".cat__tessera").length;
    return `${n} in ${attiva}` + (filtroOra ? ` · 0${filtroOra}` : "") +
      ` · CAT_A01 ver ${meta.versione}`;
  }

  function disegna() {
    nastro.textContent = "";
    const elenco = voci();
    if (!elenco.length) {
      const v = document.createElement("div");
      v.className = "cat__vuoto";
      // Invariante 23: uno stato vuoto ESPLICITO, che dice anche perche'.
      v.textContent = vuotoDi(attiva);
      nastro.appendChild(v);
    }
    for (const voce of elenco) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cat__tessera";
      b.dataset.voce = voce.id;
      b.dataset.tipo = voce.tipo;
      if (voce.titolo) b.title = voce.titolo;
      b.dataset.categoria = String(voce.categoria);
      b.setAttribute("aria-pressed", String(voce.acceso));
      if (filtroOra && voce.categoria !== filtroOra) b.dataset.fuori = "";
      // §26.3 / rilievo 3: un GLIFO, non un quadrato pieno. Otto quadrati
      // grigi uguali non distinguono niente, e un'icona che non distingue non
      // e' un'icona — visto sullo scatto, non dedotto.
      b.title = voce.titolo ? `${voce.etichetta} — ${voce.titolo}` : voce.etichetta;
      b.setAttribute("aria-label", voce.etichetta);
      const s = document.createElement("span");
      s.className = "cat__segno";
      /* Il glifo cresce con la tessera: 24 px in un riquadro alto 32,
         che lascia --s-1 di aria sopra e sotto. A --s-4 toccherebbe i
         bordi, a --s-3 resterebbe il tratto in miniatura di prima. */
      s.appendChild(segno(voce.segno ?? voce.id, "calc(var(--s-3) + var(--s-2))"));
      b.appendChild(s);
      b.addEventListener("click", () => voce.fai());
      nastro.appendChild(b);
    }
    conteggio.textContent = testoConteggio();
    limita();
    misuraTacca();
  }

  /**
   * Le icone del pavimento: le prime `PLINTO_MAX` della categoria attiva.
   *
   * ⚠️ Sono le stesse VOCI della griglia, non un secondo elenco. Due sorgenti
   * per la stessa cosa divergono al primo filtro aggiunto a una sola — e' la
   * ragione per cui il dock ha ceduto l'indice al catalogo invece di tenerne
   * una copia (§26.3).
   *
   * Solo il glifo, nessuna parola: il riferimento non mette testo sul plinto.
   * Il nome resta in `title` e in `aria-label` — togliere il testo non e'
   * togliere l'informazione.
   */
  function disegnaPlinto(elenco) {
    azioni.textContent = "";
    for (const voce of elenco.slice(0, PLINTO_MAX)) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cat__azione";
      b.dataset.voce = voce.id;
      b.title = voce.titolo ? `${voce.etichetta} — ${voce.titolo}` : voce.etichetta;
      b.setAttribute("aria-label", voce.etichetta);
      b.setAttribute("aria-pressed", String(voce.acceso));
      if (filtroOra && voce.categoria && voce.categoria !== filtroOra)
        b.dataset.fuori = "";
      /* ⚠️ 32 px, e il riferimento ne vorrebbe 68. «40 px su 901» e' il
         4,4 % della larghezza, e il 4,4 % di 1536 fa 68: trasferendo il pixel
         invece della frazione se n'e' preso meno della meta', proprio sulla
         misura che questo file chiama «la differenza singola piu' grande fra
         noi e lui». Sta scritto e non e' corretto qui: la piastra e' anche
         l'unita' di passo della giostra, e cambiarla cambia la geometria di
         §26.3 — e' una decisione, non una rifinitura. */
      b.appendChild(segno(voce.segno ?? voce.id, "var(--piastra)"));
      /* ⚠️ IL CLIC CENTRA **E** APRE, non solo centra. Una barra delle
         applicazioni da cui premere un'applicazione non la apre non e' una
         barra delle applicazioni: e' un carosello. Chi preme una piastra
         laterale vuole quel modulo, e portarla al centro e' come ci si arriva,
         non che cosa si e' chiesto. */
      b.addEventListener("click", () => {
        const i = [...azioni.children].indexOf(b);
        if (i >= 0) vaA(i - (Math.min(FINESTRA, azioni.childElementCount) - 1) / 2, true);
        voce.fai();
      });
      azioni.appendChild(b);
    }
    return [...azioni.children];
  }

  /* ── la giostra ───────────────────────────────────────────────────────────
   *
   * Quattro piastre in vista, le altre a un giro di rotella. Lo stato e' UN
   * numero — l'indice della prima piastra della finestra — e tutto il resto si
   * ricalcola da lui: una cosa sola da animare, una sola da salvare, e nessuna
   * possibilita' che posizione e profondita' finiscano fuori fase.
   */
  const giostra = { indice: 0 };
  let giro = null;
  let fuocoCache = 0;

  /** La distanza del punto di fuga, letta dal CSS: e' li' che e' dichiarata. */
  function prospettiva() {
    if (!fuocoCache)
      fuocoCache = parseFloat(getComputedStyle(scena).perspective) || 360;
    return fuocoCache;
  }

  const passo = () => PASSO;

  /** L'ultima posizione in cui la finestra puo' cominciare. */
  const ultimoPrimo = () => Math.max(0, azioni.childElementCount - FINESTRA);

  /**
   * Dispone le piastre: le quattro della finestra in vista, il resto spento.
   *
   * ⚠️ Il ciclo tocca OGNI figlio a OGNI passata, e non e' una ridondanza: una
   * piastra aggiunta dopo l'ultima esecuzione conserverebbe l'`opacity` inline
   * che aveva, e resterebbe visibile senza essere premibile. Le due
   * dichiarazioni si scrivono insieme perche' dicono la stessa cosa.
   */
  function disponi() {
    const p = [...azioni.children];
    const P = passo();
    const F = prospettiva();
    // La finestra e' centrata sulla lastra: il suo centro cade fra la seconda
    // e la terza piastra, cioe' a (FINESTRA - 1) / 2 passi dalla prima.
    //
    // ⚠️ L'ANCORA NON E' LA PIASTRA AL CENTRO. Ancorando a quella, con
    // l'indice a 0 tutte le altre finiscono a destra: la fila esce dal
    // pavimento da un lato e lascia mezzo trapezio vuoto. Il centro della
    // scena e' il centro della FILA VISIBILE, e la piastra al centro lo
    // dichiara con l'apertura e col giro, non con la posizione.
    const mezza = (Math.min(FINESTRA, p.length) - 1) / 2;
    for (let i = 0; i < p.length; i++) {
      const el = p[i];
      const dalCentro = (i - giostra.indice) - mezza;
      const verso = Math.sign(dalCentro);
      // 0 sulla piastra al centro, 1 appena la si lascia: e' un interruttore
      // morbido, non una rampa — «appena lascia il centro» e' letterale.
      const fuori = Math.min(Math.abs(dalCentro) * 2, 1);
      const passi = Math.min(Math.abs(dalCentro), FUGA_PASSI);
      const z = -passi * FUGA;
      /* La x si compensa per la profondita': una piastra a z rende x·F/(F−z),
         quindi per un varco proiettato costante bisogna chiedere x·(F+|z|)/F.
         Senza, le piastre lontane si SOVRAPPONGONO — misurato con la x
         lineare: varchi 4,2 · −2,5 · 3,4, cioe' due su otto compenetrate. */
      const x = (dalCentro * P + verso * fuori * APERTURA) * ((F + Math.abs(z)) / F);
      el.style.transform =
        `translate3d(${x.toFixed(1)}px, 0, ${z.toFixed(1)}px) ` +
        `rotateY(${(-verso * fuori * GIRO).toFixed(1)}deg)`;
      /* ⚠️ Nessuna opacita' e nessun pointer-events da spegnere: a ritagliare
         ci pensa `.cat__scena` con il proprio overflow. Una piastra fuori dal
         ritaglio non e' visibile e non e' premibile perche' non c'e', non
         perche' qualcuno la spenga — una verita' sola invece di due
         dichiarazioni che possono restare indietro l'una sull'altra. */
    }
    for (const b of frecce) {
      const v = Number(b.dataset.verso);
      b.disabled = v < 0 ? giostra.indice <= 0 : giostra.indice >= ultimoPrimo();
    }
  }

  /** Porta la finestra a cominciare da `n`, con o senza animazione. */
  function vaA(n, animato) {
    const bersaglio = Math.max(0, Math.min(ultimoPrimo(), n));
    // Due animazioni sullo stesso indice scriverebbero due valori nello stesso
    // fotogramma, e vincerebbe l'ultima a caso.
    giro?.pause();
    if (!animato || bersaglio === giostra.indice) {
      giostra.indice = bersaglio;
      disponi();
      return;
    }
    giro = animate(giostra, {
      indice: bersaglio,
      duration: 320,
      ease: "out(2)",
      onUpdate: disponi,
    });
  }

  /* La rotella gira di UNA piastra, non di pixel: la giostra ha posizioni
     discrete, e un indice a 3,7 non e' uno stato in cui si possa restare. */
  azioni.addEventListener("wheel", (e) => {
    if (azioni.childElementCount <= FINESTRA) return;
    const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (!d) return;
    e.preventDefault();
    vaA(Math.round(giostra.indice) + Math.sign(d), true);
  }, { passive: false });

  /* Il trascinamento gira in continuo e al rilascio si aggancia alla piastra
     piu' vicina: durante la presa l'indice frazionario e' legittimo, perche' e'
     il dito a tenerlo li'. E' la stessa distinzione del nastro (§26.4): la
     fisica mentre si tocca, uno stato discreto quando si lascia. */
  let presaGiostra = null;
  azioni.addEventListener("pointerdown", (e) => {
    if (e.button !== 0 || azioni.childElementCount <= FINESTRA) return;
    presaGiostra = { x: e.clientX, da: giostra.indice, mosso: false };
    azioni.dataset.presa = "";
    azioni.setPointerCapture(e.pointerId);
  });
  azioni.addEventListener("pointermove", (e) => {
    if (!presaGiostra) return;
    const dx = e.clientX - presaGiostra.x;
    if (Math.abs(dx) > SOGLIA_GIRO) presaGiostra.mosso = true;
    giro?.pause();
    giostra.indice = Math.max(0, Math.min(ultimoPrimo(), presaGiostra.da - dx / passo()));
    disponi();
  });
  function rilasciaGiostra(e) {
    if (!presaGiostra) return;
    const mosso = presaGiostra.mosso;
    presaGiostra = null;
    delete azioni.dataset.presa;
    azioni.releasePointerCapture?.(e.pointerId);
    // Aggancio alla piastra piu' vicina. Se non ci si e' mossi era un clic, e
    // il clic e' della piastra: non lo si intercetta qui.
    if (mosso) vaA(Math.round(giostra.indice), true);
  }
  azioni.addEventListener("pointerup", rilasciaGiostra);
  azioni.addEventListener("pointercancel", rilasciaGiostra);

  /**
   * Il cambio di linguetta sul pavimento — §10.4, con anime.js.
   *
   * Le vecchie scendono e svaniscono, le nuove salgono a scalare. Non e'
   * decorazione e non viola l'invariante 25: **la causa e' il clic sulla
   * linguetta**, ed e' l'unica cosa che fa partire questa animazione. Al primo
   * disegno l'uscita si salta, perche' non c'e' niente da cui uscire.
   *
   * `stagger(45)` e non i 60 di §10.4: quello e' il valore del dock, che aveva
   * otto voci. Qui ce ne sono al massimo cinque, e a 60 l'ultima arriverebbe
   * 300 ms dopo la prima — un ritardo che si legge come lentezza invece che
   * come sequenza.
   */
  function cambiaPlinto() {
    const elenco = voci();
    const vecchie = [...azioni.children];
    const entra = () => {
      const nuove = disegnaPlinto(elenco);
      // La finestra torna in testa: dopo un cambio di linguetta l'indice di
      // prima non significa piu' niente, e restare al quinto elemento di un
      // elenco che ne ha tre e' uno stato senza senso.
      giostra.indice = 0;
      disponi();
      if (!nuove.length) return;
      /* ⚠️ Si anima la SOLA opacita', e SOLO su chi la giostra ha lasciato in
         vista. Non piu' la y: la posizione adesso e' della giostra, e
         scriverla qui vorrebbe dire due sorgenti per lo stesso `transform`.
         Ed e' proprio quello che era successo con l'opacita': l'animazione
         girava su TUTTE le piastre nuove e le riportava a 1, quindi le cinque
         fuori dalla finestra restavano visibili e non premibili — misurato sul
         DOM, nove piastre a opacity 1 e quattro sole con pointer-events. La
         regola e' una: una proprieta', un padrone.
         Da quando a ritagliare e' `.cat__scena`, l'opacita' non e' piu' di
         nessuno: si anima su tutte, e chi e' fuori dal ritaglio non si vede
         comunque. */
      animate(nuove, {
        opacity: [0, 1],
        duration: 240, delay: stagger(45), ease: "out(3)",
      });
    };
    if (!vecchie.length) { entra(); return; }
    animate(vecchie, {
      opacity: [1, 0],
      duration: 140, delay: stagger(25), ease: "in(2)",
      onComplete: entra,
    });
  }

  function apri(id) {
    attiva = id;
    for (const [k, b] of linguette) b.setAttribute("aria-selected", String(k === id));
    porta(0, false);
    disegna();
    entrata();
    cambiaPlinto();
  }

  /* ── §26.4: lo scorrimento ───────────────────────────────────────────── */

  let x = 0;               // la posizione del nastro, in px (transform)
  let animazione = null;

  const massimoScorrimento = () =>
    Math.min(0, vista.clientWidth - nastro.scrollWidth);

  function porta(nuovo, animato) {
    x = Math.max(massimoScorrimento(), Math.min(0, nuovo));
    // ⚠️ `transform`, mai `left`: cambia solo la composizione e non il layout,
    // ed e' la ragione per cui questo sta dentro i 4 ms di §10.4.
    utils.set(nastro, { x });
    misuraTacca();
    return x;
  }

  function limita() { porta(x, false); }

  function scorriDi(dx) { fermaInerzia(); porta(x + dx, false); }

  function misuraTacca() {
    const visibile = vista.clientWidth;
    const totale = Math.max(nastro.scrollWidth, 1);
    const frazione = Math.min(1, visibile / totale);
    const scorso = massimoScorrimento() === 0 ? 0 : x / massimoScorrimento();
    tacca.style.width = `${(frazione * 100).toFixed(2)}%`;
    utils.set(tacca, { x: `${(scorso * (1 - frazione) * 100 / frazione).toFixed(2)}%` });
  }

  function fermaInerzia() {
    if (animazione) { animazione.pause(); animazione = null; }
  }

  /* Il trascinamento diretto: `pointer*`, non `drag` HTML5.
   *
   * §26.4 punto 1: l'API nativa non permette di controllare l'anteprima e si
   * comporta male con elementi resi a mano. `cornice.js` usa gia' questo
   * schema per le finestre. */
  let presa = null;
  //: Un'estrazione finita dentro il catalogo produrrebbe un `click` sulla
  //: tessera da cui era partita, cioe' aprirebbe il pannello che l'utente
  //: stava solo provando a tirare fuori. Si ingoia il clic successivo.
  let sopprimiClic = false;

  vista.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    fermaInerzia();
    presa = { id: e.pointerId, x0: e.clientX, y0: e.clientY, xIniziale: x,
              campioni: [{ t: e.timeStamp, x: e.clientX }], mosso: false,
              tessera: e.target.closest?.(".cat__tessera") ?? null,
              estraendo: false };
    vista.setPointerCapture(e.pointerId);
    vista.dataset.presa = "";
  });

  /** La voce che una tessera rappresenta, nella forma che §26.5 mette giu'. */
  function voceDi(tessera) {
    if (!tessera) return null;
    return {
      tipo: tessera.dataset.tipo ?? "modulo",
      nome: tessera.dataset.voce,
      etichetta: tessera.textContent.trim(),
    };
  }

  vista.addEventListener("pointermove", (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    const dx = e.clientX - presa.x0;
    const dy = e.clientY - presa.y0;

    if (presa.estraendo) { estrazione.muovi(e.clientX, e.clientY); return; }

    // R98 — il puntatore e' USCITO dalla fascia del nastro. Uno scorrimento ci
    // resta dentro per costruzione: e' l'unica forma che non puo' avere.
    const fascia = vista.getBoundingClientRect();
    const uscito = fascia.top - e.clientY > SOGLIA_ESTRAZIONE ||
                   e.clientY - fascia.bottom > SOGLIA_ESTRAZIONE;
    if (estrazione && presa.tessera && uscito) {
      presa.estraendo = true;
      porta(presa.xIniziale, false);        // il nastro non doveva scorrere
      estrazione.inizia(voceDi(presa.tessera), e.clientX, e.clientY);
      return;
    }

    if (Math.abs(dx) > 3) presa.mosso = true;
    porta(presa.xIniziale + dx, false);
    presa.campioni.push({ t: e.timeStamp, x: e.clientX });
    // Bastano gli ultimi campioni: la velocita' che conta e' quella del
    // tratto finale, non la media di tutto il gesto.
    if (presa.campioni.length > 6) presa.campioni.shift();
  });

  const rilascia = (e) => {
    if (!presa || e.pointerId !== presa.id) return;
    if (presa.estraendo) {
      presa = null;
      sopprimiClic = true;
      delete vista.dataset.presa;
      estrazione.lascia(e.clientX, e.clientY);
      return;
    }
    const c = presa.campioni;
    const primo = c[0];
    const ultimo = c[c.length - 1];
    const dt = ultimo.t - primo.t;
    const v = dt > 0 ? (ultimo.x - primo.x) / dt : 0;   // px/ms
    const mosso = presa.mosso;
    presa = null;
    delete vista.dataset.presa;
    // Un clic fermo non e' un lancio: senza questa soglia ogni pressione
    // partirebbe con una velocita' di rumore.
    if (!mosso || Math.abs(v) < FERMO_PX_MS) return;
    lancia(v);
  };
  vista.addEventListener("pointerup", rilascia);
  vista.addEventListener("pointercancel", rilascia);
  // In cattura: deve arrivare prima del gestore della tessera, non dopo.
  vista.addEventListener("click", (e) => {
    if (!sopprimiClic) return;
    sopprimiClic = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);

  /**
   * L'inerzia (§26.4 punto 2), con anime.js.
   *
   * Il bersaglio si calcola dalla velocita' al rilascio; la decelerazione la
   * fa l'ease, che e' esattamente il motivo per cui l'invariante 9 vuole un
   * motore solo: scrivere la fisica a mano in `requestAnimationFrame` sarebbe
   * un secondo motore di animazione senza chiamarlo cosi'.
   *
   * ⚠️ **Ha una causa** — il gesto — quindi l'invariante 25 regge.
   */
  function lancia(v) {
    const bersaglio = Math.max(massimoScorrimento(), Math.min(0, x + v * VOLO_MS));
    if (bersaglio === x) return;
    animazione = animate(nastro, {
      x: bersaglio,
      duration: Math.min(900, Math.abs(bersaglio - x) * 2.2 + 180),
      ease: "out(3)",
      onUpdate: () => { x = utils.get(nastro, "x", false); misuraTacca(); },
      onComplete: () => { animazione = null; },
    });
  }

  // §26.4 punto 5: la rotellina scorre in orizzontale, senza `shift`.
  vista.addEventListener("wheel", (e) => {
    e.preventDefault();
    fermaInerzia();
    porta(x - (Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY), false);
  }, { passive: false });

  /** L'entrata delle icone: `stagger`, come prescrive §10.4 riga «Dock». */
  function entrata() {
    const tessere = [...nastro.querySelectorAll(".cat__tessera")];
    if (!tessere.length) return;
    animate(tessere, {
      opacity: [0, 1],
      duration: 220,
      delay: stagger(60),
      ease: "out(2)",
    });
  }

  /* ── cio' che il catalogo ascolta ────────────────────────────────────── */

  scrivania.osserva(({ aperti, filtro, scene, scena }) => {
    apertiOra = new Set(aperti);
    filtroOra = filtro;
    // L'ELENCO delle scene puo' cambiare — arriva dal core dopo l'avvio — e
    // allora la griglia va rifatta; la scena CORRENTE e' uno stato, e si
    // aggiorna sul posto (R90).
    const cambiato = (scene ?? []).map((s) => s.nome).join(" ") !==
                     sceneOra.map((s) => s.nome).join(" ");
    sceneOra = scene ?? [];
    scenaOra = scena ?? null;
    if (cambiato && attiva === "scene") { disegna(); return; }
    // Il filtro della barra evidenzia la categoria QUI: ADR-010 dice
    // «Alt+1…4 evidenzia nel catalogo la categoria corrispondente», e questo
    // e' il catalogo. Si AGGIORNA, non si ridisegna.
    aggiorna();
  });

  bus.su("fs.list", (m) => {
    // La forma del messaggio e' quella del tool `list_dir`, la stessa che
    // legge `panels/files.js`: `{ path, voci: [{ name, type, size }], totale }`.
    fileVisti = (m.voci ?? []).map((v) => ({
      nome: String(v.name ?? "?"), cartella: v.type === "dir",
    }));
    percorso.textContent = String(m.path ?? "—");
    const n = m.totale ?? fileVisti.length;
    percorsoCorto.textContent = `${n} ${n === 1 ? "voce" : "voci"}`;
    if (attiva === "file") disegna();
  });



  bus.su("agent.mesh", (m) => {
    const nodo = (m.nodi ?? []).find((n) => n.id === "t2");
    stato.textContent = `T2 ${nodo?.stato ?? "inerte"}`;
  });

  window.addEventListener("resize", () => { limita(); misuraTacca(); });

  apri("moduli");

  return {
    el, ancora,
    get attiva() { return attiva; },
    get scorrimento() { return x; },
    apri, scorriDi, disegna,
    altezza: () => Math.round(el.getBoundingClientRect().height),
  };
}
