/* I segni — SPEC-26 §26.3, «le icone».
 *
 * ## Perche' esiste questo file
 *
 * §26.3 chiede icone **riempite**, e misura la differenza: la fascia del
 * catalogo nel riferimento ha il 26,2 % di superficie accesa, la nostra ne
 * aveva il 2,8 % perche' le nostre «icone» erano testo. Il primo giro di §26.3
 * ha corretto il COLORE — `--icona` a L 171 — e ha lasciato la FORMA: quadrati
 * pieni, tutti uguali. Guardando lo scatto si vedono otto rettangoli grigi che
 * non dicono niente, e un'icona che non distingue non e' un'icona.
 *
 * ## Perche' disegnati qui e non presi da una libreria
 *
 * Un set esterno porta con se' un tratto, un raggio e una griglia che non sono
 * i nostri: il raggio zero dell'invariante 18, i tre pesi di linea di §10.1 e
 * la scala delle spaziature verrebbero da un altro sistema. E l'invariante 30
 * dice che il codice altrui resta di chi l'ha scritto anche quando e' pubblico.
 *
 * Sono forme geometriche **piene**, su una griglia 24x24, tutte con la stessa
 * logica: un ingombro che riempie, mai un contorno. Un contorno a 32 px si
 * legge come una macchia e non aggiunge inchiostro — che e' il difetto da cui
 * questo file nasce.
 *
 * ## Come si legge una forma
 *
 * Ogni segno dice **cosa mostra il pannello**, non cosa fa: la telemetria e'
 * un istogramma, la tavola periodica una griglia, il globo una sfera con un
 * meridiano. Chi guarda il catalogo sta cercando un contenuto, non un verbo.
 */

const NS = "http://www.w3.org/2000/svg";

/** Il segno di un modulo, di una voce o di un'azione. Griglia 24x24. */
export const SEGNI = {
  //: istogramma: tre barre che salgono
  telemetria: "M2 15h5v7H2zM9.5 9h5v13h-5zM17 3h5v19h-5z",
  //: tre nodi e i cavi che li tengono
  agenti: "M2 3h6v6H2zM16 3h6v6h-6zM9 15h6v6H9zM4 9h2v4H4zM18 9h2v4h-2z"
        + "M5 12h14v2H5z",
  //: il prompt di un terminale: un chevron e una riga
  console: "M2 3h20v3H2zM4 9l4 4-4 4v-3l1-1-1-1zM11 16h9v3h-9z",
  //: anelli concentrici — pieni, con il vuoto in mezzo (evenodd)
  anelli: "M12 1a11 11 0 100 22 11 11 0 100-22zm0 4a7 7 0 110 14 7 7 0 110-14z"
        + "M12 9a3 3 0 100 6 3 3 0 100-6z",
  //: un quadrante: mezzo disco e la lancetta
  quadranti: "M12 3a9 9 0 00-9 9h4a5 5 0 015-5zM12 3a9 9 0 019 9h-4a5 5 0 00-5-5z"
           + "M11 13h2v8h-2zM3 14h18v2H3z",
  //: la griglia esagonale dei glifi
  glifi: "M7 2h6l3 5-3 5H7L4 7zM15 12h6l3 5-3 5h-6l-3-5zM7 12h4l3 5-3 5H7l-3-5z",
  //: un documento con l'angolo piegato
  file: "M4 2h10l6 6v14H4zM14 2v6h6z",
  //: la nuvola di punti del core sorgente
  sorgente: "M3 4h4v4H3zM10 9h4v4h-4zM17 3h4v4h-4zM5 15h4v4H5zM15 16h4v4h-4z"
          + "M11 2h2v2h-2zM2 11h2v2H2zM20 11h2v2h-2z",
  //: i piani d'archivio: fogli sfalsati
  archivio: "M2 5h16v3H2zM4 10h16v3H4zM6 15h16v3H6z",
  //: una finestra col proprio capo
  browser: "M2 3h20v4H2zM2 9h20v12H2zm3 3h14v6H5z",
  //: un giornale: titolo e colonne
  news: "M2 3h20v5H2zM2 10h9v11H2zM13 10h9v3h-9zM13 15h9v2h-9zM13 19h9v2h-9z",
  //: la board: carte appuntate
  board: "M2 2h20v3H2zM3 7h7v7H3zM12 7h9v4h-9zM12 13h9v8h-9zM3 16h7v5H3z",
  //: una sfera con un meridiano
  globo: "M12 1a11 11 0 110 22 11 11 0 010-22zm0 3a8 8 0 100 16 8 8 0 000-16z"
       + "M11 4h2v16h-2zM4 11h16v2H4zM12 4c3 3 3 13 0 16-3-3-3-13 0-16z",
  //: la tavola periodica: una griglia di celle
  periodica: "M2 3h4v4H2zM7 3h4v4H7zM18 3h4v4h-4zM2 8h4v4H2zM7 8h4v4H7z"
           + "M12 8h4v4h-4zM18 8h4v4h-4zM2 13h4v4H2zM7 13h4v4H7zM12 13h4v4h-4z"
           + "M18 13h4v4h-4zM7 18h10v3H7z",
  //: una mano stilizzata: palmo e tre dita
  gesture: "M6 10h3V3h2v7h2V4h2v6h2V6h2v11a5 5 0 01-5 5h-4a6 6 0 01-6-6v-6h2z",

  //: una scena: carte che si coprono di proposito (§26.6)
  scena: "M2 4h12v9H2zM10 8h12v12H10z",
  //: una cartella manila, con la linguetta
  cartella: "M2 4h8l2 3h10v14H2z",

  /* ── il tempo — OTTO condizioni, non due ─────────────────────────────────
   *
   * Il riferimento ne disegna due: un sole e un sole con nuvola. Ricondurre
   * tutto il tempo a due icone e' un segnaposto travestito da icona — con la
   * sola coppia, «nebbia» e «temporale» diventano entrambi «sereno». I codici
   * WMO che Open-Meteo restituisce ne richiedono almeno otto per non mentire,
   * e una settimana vera di Milano, misurata, ne conteneva cinque diverse.
   *
   * Le chiavi sono quelle di `core/tools/meteo.py`: un test lega i due elenchi.
   */
  //: disco pieno coi raggi
  sereno: "M12 7a5 5 0 110 10 5 5 0 010-10zM11 1h2v4h-2zM11 19h2v4h-2z"
        + "M1 11h4v2H1zM19 11h4v2h-4zM3.5 5l1.5-1.5 3 3L6.5 8zM15.5 17l1.5-1.5"
        + " 3 3-1.5 1.5zM17 5l3-3 1.5 1.5-3 3zM4 18.5l3-3L8.5 17l-3 3z",
  //: sole dietro una nuvola piena
  "poco-nuvoloso": "M15 2a5 5 0 014.9 4H18a6 6 0 00-5.6-3.9zM6 12h11a4 4 0 010 8"
                 + "H6a4 4 0 010-8zM19 8a3 3 0 013 3 3 3 0 01-1.6 2.6A6 6 0 0016 10z",
  //: una nuvola sola, piena
  nuvoloso: "M7 8h9a5 5 0 010 10H7A5 5 0 017 8z",
  //: nuvola e tre strati orizzontali
  nebbia: "M7 4h9a5 5 0 010 10H7A5 5 0 017 4zM3 16h18v2H3zM6 20h12v2H6z",
  //: nuvola e due gocce corte
  pioviggine: "M7 3h9a5 5 0 010 10H7A5 5 0 017 3zM9 15h2v4H9zM14 15h2v4h-2z",
  //: nuvola e quattro gocce lunghe
  pioggia: "M7 2h9a5 5 0 010 10H7A5 5 0 017 2zM7 14h2v7H7zM11 14h2v8h-2z"
         + "M15 14h2v7h-2z",
  //: nuvola e fiocchi
  neve: "M7 2h9a5 5 0 010 10H7A5 5 0 017 2zM8 15h2v2H8zM13 15h2v2h-2z"
      + "M10.5 19h2v2h-2zM15.5 19h2v2h-2zM5.5 19h2v2h-2z",
  //: nuvola e saetta piena
  temporale: "M7 2h9a5 5 0 010 10H7A5 5 0 017 2zM13 13l-5 6h3l-1 5 5-6h-3z",
  //: il tempo che non sappiamo: un punto interrogativo pieno, non un sole
  ignoto: "M10.5 16h3v3h-3zM12 3a5 5 0 015 5c0 3-3 3.3-3 6h-3c0-3.7 3-3.7 3-6"
        + "a2 2 0 10-4 0H7a5 5 0 015-5z",

  // ── le azioni del plinto ────────────────────────────────────────────────
  //: nascondi tutto: una superficie che si abbassa
  nascondi: "M2 3h20v7H2zM2 13h20v3H2zM2 18h20v2H2z",
  //: affianca: quattro riquadri nella griglia
  affianca: "M2 2h9v9H2zM13 2h9v9h-9zM2 13h9v9H2zM13 13h9v9h-9z",
  //: togli il filtro: un imbuto pieno, aperto
  tutto: "M2 3h20l-8 9v9l-4-3v-6z",
};

/** Quando un id non ha un segno proprio: un quadrato pieno, com'era tutto. */
const GENERICO = "M4 4h16v16H4z";

/**
 * Il nodo SVG del segno `id`, dimensionato in `lato` (un valore CSS).
 *
 * `fill-rule="evenodd"` non e' un dettaglio: gli anelli e il globo sono forme
 * con un buco, e con la regola predefinita il buco si riempirebbe — un anello
 * diventerebbe un disco, che e' un segno diverso.
 */
export function segno(id, lato = "var(--s-4)") {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  /* ⚠️ `currentColor`, non un token scritto qui.
   *
   * Un glifo non ha un colore proprio: ha il colore del posto in cui sta —
   * grigio nel catalogo, manila su un'icona di file, acceso sotto il puntatore.
   * Se lo fissasse questo file, ogni contesto dovrebbe ricordarsi di
   * sovrascriverlo con una regola `svg { fill: ... }` accanto al proprio
   * `color`: **due dichiarazioni per una verita' sola**, che e' esattamente il
   * modo in cui le due si slegano.
   *
   * Ed e' successo. I pulsanti del plinto non dichiaravano `color`, quindi
   * ereditavano `buttontext` dell'agente utente — nero, che in tokens.css non
   * esiste — e con loro svg e path: **24 violazioni** all'audit, tre elementi
   * per cinque proprieta' di colore a pulsante. Con `currentColor` la regola
   * diventa una sola e vale per tutti: **il contenitore dichiara `color`**.
   */
  svg.setAttribute("fill", "currentColor");
  svg.style.width = lato;
  svg.style.height = lato;
  svg.style.flex = "0 0 auto";
  const path = document.createElementNS(NS, "path");
  path.setAttribute("d", SEGNI[id] ?? GENERICO);
  path.setAttribute("fill-rule", "evenodd");
  svg.appendChild(path);
  return svg;
}

/** C'e' un segno proprio per questo id? Serve a chi vuole saperlo, non a chi
 *  disegna: `segno()` da' comunque qualcosa. */
export function haSegno(id) {
  return Object.hasOwn(SEGNI, String(id));
}
