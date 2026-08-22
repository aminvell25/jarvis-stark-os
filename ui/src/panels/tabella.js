/* Tabella dati densa — riferimento famiglia-a/03, i pannelli IP.
 *
 * ## Che cosa porta il riferimento, misurato su «03»
 *
 * La tabella «SUBNETS_V.02» sta a x 663..893, y 425..540: 230 x 115 px, cioe'
 * il 25,5 % x 20,4 % dello schermo. Le righe sono alte 8 px su 115, cioe'
 * quattordici righe in un pannello alto un quinto di schermo. Da qui tutto:
 *
 * 1. **L'intestazione e' una banda PIENA e CHIARA**, con il testo scuro sopra.
 *    E' l'unico posto della tabella in cui la polarita' si rovescia, e per
 *    questo l'occhio ci torna quando ha perso il filo delle colonne.
 *
 * 2. **La zebra e' un gradino di sei punti di L**, non un colore. Nel
 *    riferimento le righe alternano #0e1319 e #131a21: si vede che sono righe
 *    e non si vede la riga. Con dieci punti diventa un motivo che compete col
 *    dato.
 *
 * 3. **I numeri sono allineati a DESTRA e in mono.** E' l'unica ragione per
 *    cui una colonna di byte si legge senza contare le cifre.
 *
 * 4. **Una riga sola e' selezionata**, con un riempimento pieno. Non un bordo:
 *    un bordo su una riga alta 8 px la fa sembrare due righe.
 *
 * 5. **Il piede porta i totali.** Nel riferimento sono tre numeri in fondo
 *    alla colonna, allineati con essa. Un totale che non sta sotto la propria
 *    colonna e' una didascalia.
 *
 * ## I dati sono i file veri di questo repository
 *
 * «source.tree» porta «{path, bytes}» per 255 file, con le dimensioni vere
 * lette da «git ls-files». La percentuale e la classe le calcola il pannello:
 * sono derivate, non inventate.
 */

export const meta = { nome: "tabella", versione: "1" };

const RIGHE_MAX = 400;

/** Le colonne, dichiarate in un posto solo: intestazione, allineamento e come
 *  si legge il valore da una voce. «peso» e' la frazione di larghezza. */
const COLONNE = [
  { id: "path", et: "percorso", peso: 6, num: false, val: (v) => v.path },
  { id: "ramo", et: "ramo", peso: 2, num: false, val: (v) => ramoDi(v.path) },
  { id: "bytes", et: "byte", peso: 2, num: true, val: (v) => intero(v.bytes) },
  { id: "quota", et: "quota", peso: 2, num: true, val: (v, t) => `${quota(v.bytes / t * 100, 2)} %` },
];

const ramoDi = (p) => (String(p).includes("/") ? String(p).split("/")[0] : "·");
const intero = (n) => Number(n).toLocaleString("it-IT");
/* La virgola decimale non e' un vezzo: tutto il resto del pannello usa
   toLocaleString("it-IT") e due separatori diversi nella stessa riga si leggono
   come due unita' diverse. */
const quota = (n, cifre) => Number(n).toLocaleString("it-IT",
  { minimumFractionDigits: cifre, maximumFractionDigits: cifre });

export const css = `
.pnl-tab {
  --aug-tr: var(--s-3);
  --aug-border-bg: transparent;
  display: grid;
  grid-template-rows: auto 1fr;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 4);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-tab__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
.pnl-tab__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-tab__id, .pnl-tab__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  white-space: nowrap;
  color: var(--icona);
}
.pnl-tab__ctrl { letter-spacing: 0.16em; }

/* ① L'INTESTAZIONE ROVESCIA LA POLARITA'. E' l'unica banda chiara del corpo, e
   serve a ritrovare le colonne. «position: sticky» la tiene ferma mentre le 255
   righe scorrono: una tabella in cui l'intestazione se ne va non ha colonne, ha
   numeri.

   ⚠️ --icona, non --fill-3. Con --fill-3 (L 103) sotto un testo --bg-void il
   rovescio misurava 3,33:1 su glifi da 8,5 px: sotto il 4,5 che AA chiede al
   testo piccolo, cioe' la banda che «serve a ritrovare le colonne» non
   superava la soglia per cui esiste. --icona (L 171) porta la stessa coppia a
   7,23:1, ed e' anche la banda rovesciata che questo sistema ha gia': le
   piastre del plinto sono --icona col simbolo a --bg-void. Una polarita'
   rovesciata, un token. */
.pnl-tab__intestazione {
  position: sticky;
  top: 0;
  z-index: 2;
  display: grid;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-3);
  background: var(--icona);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--bg-void);
}
/* ⚠️ INTESTAZIONE, RIGHE E PIEDE STANNO NELLO STESSO CONTENITORE, e la prima
   stesura li aveva fuori. Sembrava identico e non lo era: il corpo scorre,
   quindi ha una barra di scorrimento, e la barra si mangia larghezza. Misurato
   in galleria: contenitore 700 px, larghezza utile 685 — quindici px.
   Intestazione e piede stavano fuori e si risolvevano su 700, le righe dentro
   su 685: la STESSA dichiarazione grid-template-columns produceva DUE griglie
   diverse, e le colonne numeriche allineate a destra scivolavano di 13-15 px.
   Il piede diceva 17.087.101 tredici pixel a destra della colonna che stava
   sommando, cioe' era la didascalia che il punto 5 dell'intestazione vieta.
   E non si aggiusta col padding: la barra e' larga 15 px in galleria (nessuna
   regola ::-webkit-scrollbar in chrome.css) e 8 px nell'app (app.css la porta a
   --s-2), quindi un compenso scritto a mano sarebbe giusto in un posto solo.
   Un contenitore solo, e le tre griglie tornano una. */
.pnl-tab__corpo {
  display: flex;
  flex-direction: column;
  overflow: auto;
  min-height: 0;
}
/* Spinge il piede in fondo quando le righe non bastano a riempire. */
.pnl-tab__righe { flex: 1 0 auto; }
.pnl-tab__riga {
  display: grid;
  gap: var(--s-2);
  padding: 0 var(--s-3);
  align-items: baseline;
  font-family: var(--font-mono);
  font-size: var(--t-data);
  line-height: 1.5;
  color: var(--txt-dim);
  cursor: default;
}
/* ② SEI PUNTI DI L, non un colore. --bg-panel su --bg-raised misura 1,08:1:
   si vede che sono righe, non si vede la riga. */
.pnl-tab__riga:nth-child(odd) { background: var(--bg-panel); }
.pnl-tab__riga:hover { background: var(--fill-1); color: var(--txt-primary); }
/* ④ La riga scelta: un RIEMPIMENTO, non un bordo. Su una riga alta 16 px un
   bordo ne fa sembrare due. */
.pnl-tab__riga[aria-selected="true"] { background: var(--fill-2); color: var(--txt-primary); }
/* ③ I numeri a destra. Sono l'unica ragione per cui una colonna di byte si
   legge senza contare le cifre. */
.pnl-tab__c { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.pnl-tab__c[data-num] { text-align: right; font-variant-numeric: tabular-nums; }
.pnl-tab__riga[aria-selected="true"] .pnl-tab__c[data-num] { color: var(--cy-100); }
/* La colonna che porta il dato principale prende il testo primario: in una
   tabella tutta a --txt-dim non si capisce che cosa si sta guardando. */
.pnl-tab__c:first-child { color: var(--txt-primary); }

/* ⑤ Il piede e' ALLINEATO ALLE COLONNE: usa la stessa griglia, quindi ogni
   totale sta sotto la propria colonna. */
.pnl-tab__piede {
  position: sticky;
  bottom: 0;
  z-index: 2;
  display: grid;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  /* Opaco, perche' adesso le righe gli scorrono sotto. Senza, i totali si
     leggerebbero sovrapposti all'ultima riga. */
  background: var(--bg-raised);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-tab__piede span[data-num] { text-align: right; }

.pnl-tab__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-tab[data-stato="vuoto"] .pnl-tab__corpo,
.pnl-tab[data-stato="vuoto"] .pnl-tab__intestazione,
.pnl-tab[data-stato="vuoto"] .pnl-tab__piede { display: none; }
.pnl-tab[data-stato="vuoto"] .pnl-tab__vuoto { display: block; }
`;

const HTML = `
<section class="pnl-tab" data-stato="vuoto" data-augmented-ui="tr-clip bl-clip border">
  <header class="pnl-tab__testa">
    <span class="pnl-tab__etichetta">Albero sorgenti</span>
    <span class="pnl-tab__id">TAB_S03 &middot; ver ${meta.versione}</span>
    <span class="pnl-tab__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-tab__corpo">
    <div class="pnl-tab__intestazione"></div>
    <div class="pnl-tab__righe"></div>
    <footer class="pnl-tab__piede"></footer>
  </div>
  <div class="pnl-tab__vuoto">NESSUNA SORGENTE COLLEGATA</div>
</section>
`;

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-tab");
  const intestazione = el.querySelector(".pnl-tab__intestazione");
  const righe = el.querySelector(".pnl-tab__righe");
  const piede = el.querySelector(".pnl-tab__piede");

  // Una sola dichiarazione della griglia, riusata da intestazione, righe e
  // piede: tre grid-template-columns diversi sono tre tabelle che si somigliano.
  const colonne = COLONNE.map((c) => `${c.peso}fr`).join(" ");
  for (const e of [intestazione, piede]) e.style.gridTemplateColumns = colonne;

  for (const c of COLONNE) {
    const s = document.createElement("span");
    s.textContent = c.et;
    if (c.num) s.dataset.num = "";
    intestazione.appendChild(s);
  }

  let scelta = null;

  function aggiorna(msg) {
    const voci = Array.isArray(msg?.files) ? msg.files : null;
    if (!voci || !voci.length) return;
    el.dataset.stato = "pieno";
    const totale = voci.reduce((s, v) => s + (Number(v.bytes) || 0), 0);
    // Il piu' grande in cima: una tabella ordinata per nome nasconde proprio
    // la cosa che si guarda una tabella di dimensioni per sapere.
    const ordinate = [...voci].sort((a, b) => (b.bytes || 0) - (a.bytes || 0))
                              .slice(0, RIGHE_MAX);

    righe.replaceChildren();
    for (const [i, v] of ordinate.entries()) {
      const r = document.createElement("div");
      r.className = "pnl-tab__riga";
      r.style.gridTemplateColumns = colonne;
      r.setAttribute("aria-selected", "false");
      r.dataset.i = String(i);
      for (const c of COLONNE) {
        const s = document.createElement("span");
        s.className = "pnl-tab__c";
        if (c.num) s.dataset.num = "";
        // textContent: i percorsi vengono dal disco (invariante 5).
        s.textContent = String(c.val(v, totale));
        r.appendChild(s);
      }
      r.addEventListener("click", () => {
        scelta?.setAttribute("aria-selected", "false");
        scelta = r;
        r.setAttribute("aria-selected", "true");
      });
      righe.appendChild(r);
    }

    // La riga piu' grande e' scelta di serie: la tabella si apre su cio' per
    // cui la si apre, invece di aspettare un clic per dire qualcosa.
    scelta = righe.firstElementChild;
    scelta?.setAttribute("aria-selected", "true");

    piede.replaceChildren();
    for (const [j, c] of COLONNE.entries()) {
      const s = document.createElement("span");
      if (c.num) s.dataset.num = "";
      s.textContent = j === 0 ? `${voci.length} file`
        : j === 1 ? `${new Set(voci.map((v) => ramoDi(v.path))).size} rami`
        : j === 2 ? intero(totale)
        : `${quota(100, 2)} %`;
      piede.appendChild(s);
    }
  }

  return { el, radice: el, aggiorna, get scelta() { return scelta?.dataset.i ?? null; } };
}
