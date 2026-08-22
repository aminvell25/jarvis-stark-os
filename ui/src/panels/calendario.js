/* Calendario mensile — riferimento famiglia-a/01, il pannello centrale.
 *
 * ## Che cosa porta il riferimento, misurato
 *
 * Il calendario di «01» sta a x 340..667, y 232..435 — 327 x 203 px su uno
 * schermo di 901, cioe' il 36,3 % x 36,1 %. Dentro:
 *
 *   intestazione dei giorni   14 px su 203 = 6,9 %, banda PIENA
 *   griglia                   7 colonne x 6 righe, celle di 46 x 31
 *   varchi                    un filo, non uno spazio: le celle si toccano
 *
 * Tre cose lo fanno leggere, e sono tutte e tre misurabili:
 *
 * 1. **La cella e' una SUPERFICIE, non un riquadro con un numero dentro.**
 *    Nel riferimento ogni giorno del mese e' un rettangolo pieno a L 89-103;
 *    i giorni fuori dal mese scendono a L 30-37. Il confine fra i due mesi non
 *    e' un bordo: e' un gradino di luminanza, la stessa regola di §10.5.
 *
 * 2. **Il numero e' GRANDE e sta in basso a destra.** Occupa circa meta'
 *    l'altezza della cella. Centrato sarebbe un'etichetta; in basso a destra
 *    e' una quota, come su un disegno tecnico.
 *
 * 3. **Una sola cella e' calda.** Nel riferimento e' rosso scuro, ed e' una
 *    su quarantadue: il 2,4 % della superficie. §11.6 regola 2 concede il 10 %,
 *    e qui basta molto meno perche' e' l'unica.
 *
 * ## I dati sono veri, e lo sono per costruzione
 *
 * Un calendario non ha bisogno di una sorgente: il mese corrente e' un dato,
 * e oggi e' oggi. L'invariante 23 e' rispettata senza chiedere niente al core.
 * L'unica cosa che arriva da fuori sono i SEGNI sui giorni — «aggiorna()»
 * accetta un elenco di date con un'etichetta — e finche' non arriva, la fascia
 * dei segni dichiara di essere vuota invece di sparire.
 */

export const meta = { nome: "calendario", versione: "1" };

const GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"];
/* Quante righe di impegno stanno in una cella prima che il resto diventi un
 * conteggio. La cella e' alta 48 px e --t-micro rende a 11: due righe piu' il
 * numero in basso a destra ci stanno, tre no. */
const RIGHE_CELLA = 2;

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
              "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

export const css = `
.pnl-cal {
  --aug-tl: var(--s-3);
  --aug-br: var(--s-3);
  --aug-border-bg: transparent;
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 3);
  background: var(--bg-raised);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-cal__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
.pnl-cal__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-cal__id, .pnl-cal__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  white-space: nowrap;
  color: var(--icona);
}
.pnl-cal__ctrl { letter-spacing: 0.16em; }

/* ① l'intestazione dei giorni: una banda PIENA, 6,9 % dell'altezza.
   --fill-1 e non --fill-2: la banda dei giorni e' servizio, non stato, e a
   L 89 competerebbe con le celle del mese. */
/* ⚠️ NESSUN VARCO, e la prima stesura ci metteva --line-hair.
   Un peso di LINEA usato come spaziatura e' la stessa confusione che l'audit
   ha gia' bocciato una volta in questo progetto: §11.8 vuole spaziature dalla
   scala --s-*, e 0,5 px non e' un gradino di nessuna scala.
   Il riferimento dice «un filo, non uno spazio: le celle si toccano», e il
   filo non e' un varco: e' il GRADINO DI LUMINANZA fra due celle vicine —
   --fill-2 contro --fill-1 contro --bg-deep. E' §10.5 applicata dentro un
   pannello, ed e' la ragione per cui questo calendario non ha bisogno di una
   sola riga di bordo. */
.pnl-cal__giorni {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
  padding: 0 var(--s-3);
  background: var(--bg-raised);
}
.pnl-cal__giorno {
  padding: var(--s-1) var(--s-2);
  background: var(--fill-1);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--icona);
}
/* Il fine settimana e' un dato, non una decorazione: sabato e domenica hanno
   un peso diverso in qualunque calendario, e qui lo dice il testo.
   Si distingue SALENDO, non scendendo. --txt-dim su --fill-1 misura 3,19:1, e
   tokens.css chiama «illeggibile» esattamente questa coppia: il giorno festivo
   sarebbe stato l'unica etichetta della banda sotto soglia, accanto a --icona
   che sta a 4,31. --txt-primary da' 8,06 ed e' anche la lettura giusta — il
   fine settimana non e' un giorno spento. */
.pnl-cal__giorno[data-festivo] { color: var(--txt-primary); }

/* ② la griglia. «1fr» sulle righe: le sei righe si spartiscono cio' che
   resta, e la cella non ha un'altezza scritta a mano — cambia col pannello. */
.pnl-cal__griglia {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-auto-rows: 1fr;
  gap: 0;
  padding: 0 var(--s-3) var(--s-3);
  min-height: 0;
}
.pnl-cal__cella {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  padding: var(--s-1);
  background: var(--fill-2);
  border-radius: var(--radius);
  min-height: 0;
  overflow: hidden;
}
/* Fuori dal mese: si scende di due gradini, non si sbiadisce. L'opacita'
   smorzerebbe anche il numero e la cella sembrerebbe rotta invece che altrui. */
.pnl-cal__cella[data-fuori] { background: var(--bg-deep); }
.pnl-cal__cella[data-festivo] { background: var(--fill-1); }
/* OGGI, e una sola volta.
   ⚠️ NON --rust, e la prima stesura lo usava. Nel riferimento la cella accesa
   e' un rosso SCURO, e --rust (L 130) e' un rosso acceso: ma il punto non e' la
   luminanza, e' il significato. §11.6 regola 2 riserva il caldo all'ATTENZIONE,
   e oggi non e' un allarme — e' «sei qui». Il token di «questo e' quello
   corrente» in questo sistema e' --cy-500: lo usa il marcatore del pannello col
   fuoco in app.css, ed e' la stessa frase detta due volte nello stesso modo. */
.pnl-cal__cella[data-oggi] { background: var(--cy-500); }
/* Un giorno con un segno: il filo in alto, non un secondo fondo. Il fondo
   dice a quale mese appartiene la cella, e non puo' dire anche questo. */
.pnl-cal__cella[data-segnato] { box-shadow: inset 0 var(--line-bold) 0 var(--cy-500); }

/* ⚠️ UNA REGOLA SOLA, e la prima stesura ne aveva quattro.
   Avevo scelto il colore del numero stato per stato — fondo del mese, festivo,
   fuori mese, oggi — e tre volte su quattro e' uscito bene per caso. Il caso
   che non lo era e' il piu' comune: la cella normale del mese, venti su
   quarantadue, aveva --bg-void su --fill-2, cioe' 2,78:1 a corpo 20 px. Sotto
   anche il 3:1 del testo grande, e sul contenuto principale del pannello.
   La polarita' era rovesciata proprio dove pesa: la cella PIU' CHIARA
   (--fill-2, L 89) aveva il numero SCURO, e quella piu' scura (--fill-1, L 66)
   quello chiaro.
   La regola non si scrive piu' per stato ma per LUMINANZA DEL FONDO: chiaro su
   tutto, e --bg-void soltanto dove il fondo e' una banda accesa. Oggi e'
   l'unico caso — --cy-500, dove misura 10,08.
   Misurato dopo: mese 5,40 · festivo 8,06 · fuori 4,10 · oggi 10,08. */
.pnl-cal__n {
  font-family: var(--font-mono);
  /* Il numero occupa circa mezza cella, come nel riferimento. --t-title e' il
     gradino piu' alto della scala di §11.6: oltre non si va senza dichiarare
     un gradino nuovo. */
  font-size: var(--t-title);
  line-height: 1;
  color: var(--txt-primary);
}
.pnl-cal__cella[data-fuori] .pnl-cal__n { color: var(--txt-ghost); }
.pnl-cal__cella[data-oggi] .pnl-cal__n { color: var(--bg-void); }
/* Gli impegni stanno in alto a SINISTRA, il numero in basso a destra: le due
   cose non si incontrano mai, ed e' la ragione per cui il numero e' finito la'
   invece che al centro. La cella e' alta 48 px e a --t-micro ci stanno due
   righe: oltre, il conteggio dice quante ne restano. */
.pnl-cal__impegni {
  position: absolute;
  top: var(--s-1);
  left: var(--s-1);
  right: var(--s-1);
  display: grid;
  gap: 0;
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.06em;
  color: var(--txt-primary);
  pointer-events: none;
}
.pnl-cal__imp {
  display: flex;
  gap: var(--s-1);
  align-items: baseline;
  overflow: hidden;
  white-space: nowrap;
}
/* L'ORA prima del testo: in un elenco di impegni l'ora e' la chiave con cui si
   cerca, il testo e' il contenuto. Un impegno senza ora non mostra un trattino
   — non ha un'ora, e lo dice tacendo.

   ⚠️ NESSUN COLORE QUI DENTRO, e ci sono arrivato al terzo giro.

   L'ora e il conteggio dichiaravano il proprio colore — --cy-300 e --txt-dim —
   ed e' la stessa causa che avevo gia' corretto due volte sul numero del
   giorno: un colore per ELEMENTO invece che derivato dal fondo. Misurato,
   «+1» sulla cella di oggi faceva 1,68:1: l'unica cosa che dice «questo giorno
   ne ha altri» era invisibile proprio sulla cella che il pannello accende.

   E qui non si aggiusta scegliendo un colore migliore, perche' NON ESISTE:
   la cella di oggi e' --cy-500 e vuole testo scuro, la cella del mese e'
   --fill-2 e vuole testo chiaro. Un token solo non puo' superare 4,5:1 su
   entrambe. Per questo il colore lo dichiara UN elemento — .pnl-cal__impegni,
   che ha le sue quattro varianti di stato — e tutto quello che sta dentro
   eredita.

   La gerarchia fra ora e testo si fa quindi SENZA colore, ed e' l'unico modo
   che regge su quattro fondi diversi: il PESO. §11.3 dichiara Plex Mono in 400
   e 500, e 500 e' l'ora. Il conteggio si stacca con la spaziatura. */
.pnl-cal__ora { flex: 0 0 auto; font-weight: 500; }
.pnl-cal__testo { overflow: hidden; text-overflow: ellipsis; }
.pnl-cal__piu { letter-spacing: 0.14em; }
.pnl-cal__cella[data-fuori] .pnl-cal__impegni { color: var(--txt-dim); }
.pnl-cal__cella[data-oggi] .pnl-cal__impegni { color: var(--bg-void); }

/* La cella si puo' scegliere: e' il QUI di «aggiungi un impegno». Il segno e'
   un contorno interno, non un fondo — il fondo dice gia' a quale mese
   appartiene la cella, e non puo' dire anche questo. */
.pnl-cal__cella { cursor: pointer; }
.pnl-cal__cella[data-scelta] { outline: var(--line-bold) solid var(--cy-300); outline-offset: calc(var(--line-bold) * -1); }

/* ⑤ La riga di inserimento — riferimento famiglia-a/03, «SEARCH CONFIGURATION»:
   campi su fondo scuro dentro una banda, e un comando a destra. Compare solo
   quando una cella e' scelta: un modulo sempre aperto sotto un calendario e'
   spazio speso per un'azione che non si sta facendo (§11.6 regola 3). */
.pnl-cal__forma {
  display: none;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-2) var(--s-3);
  background: var(--fill-1);
}
.pnl-cal[data-scelta] .pnl-cal__forma { display: flex; }
.pnl-cal__quando {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-primary);
  white-space: nowrap;
}
.pnl-cal__campo {
  background: var(--bg-void);
  border: var(--line-hair) solid var(--cy-700);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-primary);
}
.pnl-cal__campo:focus-visible { outline: var(--line-base) solid var(--cy-500); }
.pnl-cal__campo::placeholder { color: var(--txt-ghost); }
.pnl-cal__campo--ora { width: 7ch; text-align: center; }
.pnl-cal__campo--testo { flex: 1; min-width: 0; }
.pnl-cal__tasto {
  background: var(--icona);
  border: 0;
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--bg-void);
  cursor: pointer;
  white-space: nowrap;
}
.pnl-cal__tasto:hover { background: var(--icona-viva); }
.pnl-cal__tasto[data-ruolo="via"] { background: var(--bg-raised); color: var(--amber); }
.pnl-cal__tasto[data-ruolo="via"]:hover { background: var(--bg-deep); }

.pnl-cal__piede {
  display: flex;
  justify-content: space-between;
  gap: var(--s-3);
  white-space: nowrap;
  overflow: hidden;
  padding: var(--s-2) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
`;

const HTML = `
<section class="pnl-cal" data-augmented-ui="tl-clip br-clip border">
  <header class="pnl-cal__testa">
    <span class="pnl-cal__etichetta">Calendario</span>
    <span class="pnl-cal__id">CAL_M06 &middot; ver ${meta.versione}</span>
    <span class="pnl-cal__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-cal__giorni"></div>
  <div class="pnl-cal__griglia"></div>
  <div class="pnl-cal__forma">
    <span class="pnl-cal__quando" data-quando></span>
    <input class="pnl-cal__campo pnl-cal__campo--ora" data-ora type="text"
           inputmode="numeric" maxlength="5" placeholder="hh:mm" aria-label="ora">
    <input class="pnl-cal__campo pnl-cal__campo--testo" data-testo type="text"
           maxlength="80" placeholder="impegno" aria-label="impegno">
    <button type="button" class="pnl-cal__tasto" data-aggiungi>aggiungi</button>
    <button type="button" class="pnl-cal__tasto" data-ruolo="via" data-svuota>svuota</button>
  </div>
  <footer class="pnl-cal__piede">
    <span data-mese></span>
    <span data-segni></span>
  </footer>
</section>
`;

/** «AAAA-MM-GG» da una Date locale. Non «toISOString()»: quello passa per UTC
 *  e sposta di un giorno chi vive a est di Greenwich dopo le 22. */
function chiave(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-` +
         `${String(d.getDate()).padStart(2, "0")}`;
}

/**
 * `opzioni.suImpegni` e' l'unica cosa che esce da questo pannello: viene
 * chiamata quando un giorno cambia. NON scrive niente da nessuna parte —
 * l'invariante 1 dice che il renderer non tocca il disco, e un calendario che
 * salvasse da solo sarebbe la prima crepa. Chi vuole ricordarli li manda al
 * core per la propria strada, come fa `desk/layout.js` con la disposizione.
 */
export function crea(contenitore, opzioni = {}) {
  const fuori = opzioni.suImpegni;
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-cal");
  const intestazione = el.querySelector(".pnl-cal__giorni");
  const griglia = el.querySelector(".pnl-cal__griglia");

  for (const [i, g] of GIORNI.entries()) {
    const s = document.createElement("span");
    s.className = "pnl-cal__giorno";
    if (i >= 5) s.dataset.festivo = "";
    s.textContent = g;
    intestazione.appendChild(s);
  }

  const celle = new Map();          // chiave -> elemento
  //: chiave -> [{ora: "hh:mm"|null, testo}]. Un ELENCO, non un segno: un
  //: giorno con due impegni e' il caso normale, non l'eccezione.
  const impegni = new Map();
  let scelta = null;                // la chiave della cella scelta, o null

  function disegna(quando = new Date()) {
    griglia.replaceChildren();
    celle.clear();
    const anno = quando.getFullYear();
    const mese = quando.getMonth();
    const oggi = chiave(new Date());

    // Il lunedi' e' il primo giorno: getDay() lo mette a 1 e la domenica a 0.
    const primo = new Date(anno, mese, 1);
    const scarto = (primo.getDay() + 6) % 7;
    // Sei righe SEMPRE. Un calendario che cambia altezza fra maggio e giugno
    // fa saltare tutto cio' che gli sta sotto.
    const inizio = new Date(anno, mese, 1 - scarto);

    for (let i = 0; i < 42; i++) {
      const d = new Date(inizio.getFullYear(), inizio.getMonth(), inizio.getDate() + i);
      const k = chiave(d);
      const c = document.createElement("div");
      c.className = "pnl-cal__cella";
      c.dataset.data = k;
      if (d.getMonth() !== mese) c.dataset.fuori = "";
      else if ((d.getDay() + 6) % 7 >= 5) c.dataset.festivo = "";
      if (k === oggi) c.dataset.oggi = "";
      const n = document.createElement("span");
      n.className = "pnl-cal__n";
      n.textContent = String(d.getDate());
      c.appendChild(n);
      c.addEventListener("click", () => scegli(k));
      griglia.appendChild(c);
      celle.set(k, c);
    }

    el.querySelector("[data-mese]").textContent =
      `${MESI[mese]} ${anno}`;
    if (scelta && !celle.has(scelta)) scelta = null;
    applicaImpegni();
  }

  /** Gli impegni di un giorno, ordinati per ora. Chi non ha un'ora va in fondo:
   *  un impegno senza ora non e' a mezzanotte, e' senza ora. */
  function delGiorno(k) {
    return [...(impegni.get(k) ?? [])].sort((a, b) =>
      (a.ora ?? "99:99").localeCompare(b.ora ?? "99:99"));
  }

  function applicaImpegni() {
    for (const [k, c] of celle) {
      const vecchio = c.querySelector(".pnl-cal__impegni");
      if (vecchio) vecchio.remove();
      if (k === scelta) c.dataset.scelta = "";
      else delete c.dataset.scelta;

      const elenco = delGiorno(k);
      if (!elenco.length) { delete c.dataset.segnato; continue; }
      c.dataset.segnato = "";

      const box = document.createElement("div");
      box.className = "pnl-cal__impegni";
      for (const imp of elenco.slice(0, RIGHE_CELLA)) {
        const r = document.createElement("div");
        r.className = "pnl-cal__imp";
        if (imp.ora) {
          const o = document.createElement("span");
          o.className = "pnl-cal__ora";
          o.textContent = imp.ora;
          r.appendChild(o);
        }
        const t = document.createElement("span");
        t.className = "pnl-cal__testo";
        // textContent: il testo lo scrive una persona o arriva da un file,
        // cioe' e' dato non fidato (invariante 5).
        t.textContent = imp.testo;
        r.appendChild(t);
        box.appendChild(r);
      }
      if (elenco.length > RIGHE_CELLA) {
        const piu = document.createElement("div");
        piu.className = "pnl-cal__piu";
        piu.textContent = `+${elenco.length - RIGHE_CELLA}`;
        box.appendChild(piu);
      }
      c.appendChild(box);
      c.title = elenco.map((i) => `${i.ora ? i.ora + " " : ""}${i.testo}`).join("\n");
    }
    piedeAggiornato();
  }

  function piedeAggiornato() {
    const dentro = [...impegni.keys()].filter((k) => celle.has(k))
      .reduce((s, k) => s + delGiorno(k).length, 0);
    const totale = [...impegni.values()].reduce((s, v) => s + v.length, 0);
    const oggiN = new Date().getDate();
    el.querySelector("[data-segni]").textContent = totale
      ? `oggi ${oggiN} · ${dentro}/${totale} impegni nel mese`
      : `oggi ${oggiN} · nessun impegno`;
  }

  /* ── scegliere un giorno ──────────────────────────────────────────────── */

  const forma = el.querySelector(".pnl-cal__forma");
  const campoOra = forma.querySelector("[data-ora]");
  const campoTesto = forma.querySelector("[data-testo]");

  function scegli(k) {
    // Ripremere la cella scelta la deseleziona: la riga di inserimento si
    // chiude senza dover cercare un pulsante per chiuderla.
    scelta = scelta === k ? null : k;
    if (scelta) {
      el.dataset.scelta = "";
      const d = new Date(scelta + "T00:00:00");
      forma.querySelector("[data-quando]").textContent =
        `${GIORNI[(d.getDay() + 6) % 7]} ${d.getDate()} ${MESI[d.getMonth()]}`;
      campoTesto.focus();
    } else {
      delete el.dataset.scelta;
    }
    applicaImpegni();
  }

  /** «9», «930», «9:30», «09.30» -> «09:30». Vuoto o non interpretabile ->
   *  null, che vuol dire «senza ora» e non «mezzanotte». */
  function oraNormale(v) {
    const cifre = String(v ?? "").replace(/\D/g, "");
    if (!cifre) return null;
    const h = cifre.length <= 2 ? Number(cifre) : Number(cifre.slice(0, cifre.length - 2));
    const m = cifre.length <= 2 ? 0 : Number(cifre.slice(-2));
    if (!Number.isFinite(h) || h > 23 || m > 59) return null;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

  function aggiungi() {
    const testo = campoTesto.value.trim();
    if (!scelta || !testo) return;
    const elenco = impegni.get(scelta) ?? [];
    elenco.push({ ora: oraNormale(campoOra.value), testo: testo.slice(0, 80) });
    impegni.set(scelta, elenco);
    campoOra.value = "";
    campoTesto.value = "";
    campoTesto.focus();
    applicaImpegni();
    fuori?.({ data: scelta, impegni: delGiorno(scelta) });
  }

  function svuota() {
    if (!scelta) return;
    impegni.delete(scelta);
    applicaImpegni();
    fuori?.({ data: scelta, impegni: [] });
  }

  forma.querySelector("[data-aggiungi]").addEventListener("click", aggiungi);
  forma.querySelector("[data-svuota]").addEventListener("click", svuota);
  // Invio aggiunge: e' il gesto che una riga di inserimento ha sempre avuto, e
  // costringere al mouse per ogni impegno rende la funzione inutilizzabile.
  for (const campo of [campoOra, campoTesto]) {
    campo.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); aggiungi(); }
      if (e.key === "Escape") { e.preventDefault(); scegli(scelta); }
    });
  }

  disegna();

  return {
    el, radice: el,
    /** Gli impegni possono arrivare anche da fuori — dal core, da un file, da
     *  un'altra sessione. Sostituiscono quelli che ci sono: due sorgenti per la
     *  stessa data si fonderebbero in un elenco che nessuno ha scritto. */
    aggiorna(msg) {
      const voci = msg?.impegni ?? msg?.segni;
      if (!Array.isArray(voci)) return;
      impegni.clear();
      for (const v of voci) {
        const k = String(v.data ?? "");
        if (!k) continue;
        const elenco = impegni.get(k) ?? [];
        elenco.push({
          ora: oraNormale(v.ora),
          testo: String(v.testo ?? v.etichetta ?? "").slice(0, 80),
        });
        impegni.set(k, elenco);
      }
      applicaImpegni();
    },
    /** Per la verifica e per chi vuole rileggerli tutti. */
    get impegni() {
      return [...impegni.entries()].flatMap(([data, v]) =>
        v.map((i) => ({ data, ora: i.ora, testo: i.testo })));
    },
    /** Per la verifica: quante celle, quante fuori mese, quale e' oggi. */
    get stato() {
      return {
        celle: celle.size,
        fuori: [...celle.values()].filter((c) => "fuori" in c.dataset).length,
        oggi: [...celle.values()].filter((c) => "oggi" in c.dataset).length,
      };
    },
  };
}
