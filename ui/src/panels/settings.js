/* Pannello impostazioni — SPEC §26.7.
 *
 * Questo file era da 0 byte dalla Fase 0, come `core/voice/audio_io.py` prima
 * di ieri. Fino a oggi configurare JARVIS voleva dire aprire un editor.
 *
 * ## Che cosa fa, e che cosa non puo' fare
 *
 * Mostra le impostazioni e ne CHIEDE la modifica. Non scrive: l'invariante 1
 * dice che il renderer non tocca mai il disco, e qui non c'e' nemmeno un modo
 * di provarci — `window.jarvis.impostaValore` manda una domanda al core, e di
 * la' c'e' `imposta_valore`, che ha `side_effect=True` e apre la conferma di
 * §6.2 col percorso risolto. Fra il clic e il file ci sono un'allowlist
 * derivata dallo schema, una validazione pydantic e un umano che dice di si'.
 *
 * ## Le due liste, e sono due cose diverse
 *
 * - **modificabili**: le foglie scalari, derivate dal modello. Si toccano.
 * - **bloccate**: le cinque di §26.7 regola 4. Si guardano, e la pagina dice
 *   dove si cambiano. Sono gli interruttori che decidono se un sottosistema
 *   conseguente ESISTE — un microfono che si apre, del codice che si esegue,
 *   una telecamera, quale parte del disco e' visibile — e un clic distratto
 *   non e' il modo di prendere nessuna di quelle decisioni.
 *
 * Le STRUTTURE — scene, frasi di wake, radici — non compaiono fra le
 * modificabili: `imposta_valore(chiave, valore)` sa scrivere una foglia, e
 * fingere il contrario darebbe un errore a meta' scrittura invece di un
 * rifiuto. §26.7 le elenca fra cio' che la pagina regola: e' lavoro
 * dichiarato, non fatto.
 *
 * ## Perche' non c'e' un pulsante «salva»
 *
 * Il salvataggio e' gia' una domanda: la conferma di §6.2. Un «salva» che apre
 * un riquadro che chiede di confermare il salvataggio sarebbe due volte la
 * stessa domanda, e la seconda insegnerebbe a rispondere senza leggere — che
 * e' esattamente come si rende inutile una conferma.
 */

export const meta = { nome: "settings", versione: "1" };

/* Le sezioni di §26.7, nell'ordine in cui le nomina, e la radice dello schema
 * che ciascuna raccoglie. Una chiave la cui radice non e' qui finisce in
 * «Altro»: preferisco una riga fuori posto a una riga che sparisce. */
const SEZIONI = [
  { id: "ui", titolo: "Scrivania", radici: ["ui"] },
  { id: "voice", titolo: "Voce", radici: ["voice"] },
  { id: "sistema", titolo: "Sistema", radici: ["code", "fs", "llm", "vision"] },
  { id: "contenuti", titolo: "Contenuti", radici: ["news", "meteo"] },
];

/* Dove si cambia una bloccata. Non «non si puo'»: «non da qui, e si fa cosi'».
 * Un divieto senza l'alternativa e' un vicolo cieco. */
const PERCHE_BLOCCATA = {
  "voice.enabled": "apre il microfono all'avvio",
  "code.enabled": "mette esegui_codice nell'allowlist",
  "vision.enabled": "accende la telecamera",
  "fs.allowed_roots": "decide quale parte del disco JARVIS vede",
  "fs.trash_only": "invariante 4: solo cestino, mai delete permanente",
};

export const css = `
/* §10.5 — un pannello e' un GRADINO DI LUMINANZA, non una cornice: il corpo
 * passa da --bg-panel (L 31) a --bg-raised (L 37), e contro il pavimento a
 * L 19 fa +18. Niente border, niente ombra: qui non c'e' niente da separare
 * perche' non copre nient'altro (invariante 19). */
/* La testa: e' la MANIGLIA del trascinamento, e il gruppo di controlli e'
   cio' che ui/src/desk/cornice.js trasforma in tre pulsanti veri. Non e'
   decorazione — mancavano, e questo pannello non si sarebbe potuto ne'
   trascinare ne' chiudere. L'ha trovato
   eval_visual.py, il test sulla testa e i controlli, il giorno in cui il
   pannello e' entrato nell'elenco degli auditati — e ci e' entrato perche'
   quell'elenco era scritto a mano e aveva derivato. */
.pnl-set__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  background: var(--fill-1);
}
.pnl-set__etichetta {
  flex: 1;
  font-size: var(--t-label);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--txt-primary);
}
.pnl-set__id, .pnl-set__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--icona);
}

.pnl-set {
  display: flex; flex-direction: column;
  height: 100%; min-height: 0;
  background: var(--bg-raised);
  font-family: var(--font-ui);
  color: var(--txt-primary);
}
.pnl-set__corpo { flex: 1; min-height: 0; overflow-y: auto; }

.pnl-set__sezione { border-top: var(--line-hair) solid var(--cy-900); }
.pnl-set__sezione:first-child { border-top: 0; }
.pnl-set__titolo {
  padding: var(--s-2) var(--s-3) var(--s-1);
  font-size: var(--t-micro);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--txt-dim);
}

/* Le righe si alternano come le tabelle di §10.4: il fondo pieno e' cio' che
 * rende leggibile una griglia densa, e una riga su due basta a seguirla senza
 * una sola linea in piu'. */
.pnl-set__riga {
  display: grid;
  /* minmax(0, 1fr): senza il minimo a zero, una colonna 1fr non scende sotto
   * la larghezza del proprio contenuto, e la chiave — che ha gia' l'ellissi —
   * spingerebbe fuori il campo invece di accorciarsi. */
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-3);
  background: var(--bg-panel);
}
.pnl-set__riga:nth-child(odd) { background: var(--fill-1); }
.pnl-set__chiave {
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pnl-set__campo {
  background: var(--bg-void);
  border: var(--line-hair) solid var(--cy-700);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-primary);
  /* 18ch e non 14: flux-general-multi e' il valore piu' lungo che questo
   * schema contiene, e a 14 si vedeva «flux-genera» tagliato a meta' di un
   * carattere. Un valore troncato in una pagina di configurazione e' peggio di
   * un valore assente: sembra un valore. Misurato sullo scatto §11.7.
   *
   * ⚠️ Niente apici inversi in un commento QUI DENTRO: chiuderebbero il
   * template literal di export const css, e il modulo non si caricherebbe
   * piu'. Ci sono appena ricascato — due volte di fila, la seconda dentro
   * l'avvertimento stesso — e tests/test_fogli_di_stile.py lo prende in
   * 0,04 s. */
  /* ⚠️ **Nessuna larghezza fissa**, e ci sono arrivato sbagliando due volte.
   *
   * Prima 14ch, e flux-general-multi (18 caratteri) usciva tagliato. Poi 18ch,
   * e usciva tagliato lo stesso perche' ch misura il CONTENUTO e il padding se
   * lo mangia. Poi 18ch + il padding, e allora e' comparso il troncamento di
   * llm.t1_model, che di caratteri ne ha 25: avevo guardato una sezione sola e
   * chiamato «il piu' lungo dello schema» il piu' lungo di quella.
   *
   * Il valore piu' lungo di oggi e' 25 caratteri, misurato. Ma un nome di
   * modello si allunga quando ne esce uno nuovo, e una larghezza scelta oggi
   * torna a tagliare fra sei mesi, in silenzio. Il campo si dimensiona sul
   * proprio contenuto — l'attributo size, scritto in crea() — e la colonna
   * della chiave cede lo spazio: la chiave e' un identificatore prevedibile,
   * il valore e' la cosa che si sta leggendo. */
  max-width: 100%;
  text-align: right;
}
.pnl-set__campo:focus-visible { outline: var(--line-base) solid var(--cy-500); }

/* L'interruttore e' un tasto a due posizioni col suo stato scritto: una
 * casella che si distingue solo per un segno di spunta ha bisogno di essere
 * guardata da vicino, e questa pagina si legge di sfuggita. */
.pnl-set__tasto {
  background: var(--bg-void);
  border: var(--line-hair) solid var(--cy-700);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-dim);
  cursor: pointer;
  /* Il tasto porta due sole parole, ACCESO e SPENTO: qui la larghezza fissa
   * e' giusta, e tiene i due stati incolonnati invece di farli ballare. */
  width: calc(7ch + var(--s-3));
}
.pnl-set__tasto[aria-pressed="true"] { background: var(--fill-2); color: var(--txt-primary); }
.pnl-set__tasto:hover { border-color: var(--cy-500); }

/* L'esito della scrittura. Non e' decorazione: un salvataggio che fallisce in
 * silenzio lascia sullo schermo un valore che sul disco non c'e'. */
.pnl-set__riga[data-esito="scritto"] .pnl-set__chiave { color: var(--cy-300); }
.pnl-set__riga[data-esito="rifiutato"] .pnl-set__chiave { color: var(--amber); }
.pnl-set__errore {
  grid-column: 1 / -1;
  padding-top: var(--s-1);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--amber);
}

.pnl-set__ferma {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-3);
  background: var(--bg-panel);
}
.pnl-set__ferma .pnl-set__chiave { color: var(--txt-dim); }
.pnl-set__valore {
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--icona);
  text-align: right;
}
.pnl-set__motivo {
  grid-column: 1 / -1;
  font-family: var(--font-ui);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}

.pnl-set__piede {
  padding: var(--s-1) var(--s-3);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.pnl-set[data-stato="vuoto"] .pnl-set__corpo { opacity: 1; }
.pnl-set__attesa {
  padding: var(--s-3);
  font-size: var(--t-label);
  color: var(--txt-dim);
}
.pnl-set[data-stato="collegato"] .pnl-set__attesa { display: none; }
`;

const HTML = `
<section class="pnl-set" data-stato="vuoto" data-augmented-ui="bl-clip border">
  <header class="pnl-set__testa">
    <span class="pnl-set__etichetta">Impostazioni</span>
    <span class="pnl-set__id">SET_N07</span>
    <span class="pnl-set__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-set__corpo">
    <p class="pnl-set__attesa">in attesa del core</p>
    <div data-sezioni></div>
  </div>
  <footer class="pnl-set__piede" data-piede>—</footer>
</section>
`;

function radice(chiave) {
  return String(chiave).split(".")[0];
}

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-set");
  const sezioni = el.querySelector("[data-sezioni]");
  const piede = el.querySelector("[data-piede]");
  /** chiave -> la riga, per potervi scrivere l'esito quando torna. */
  const righe = new Map();

  function chiedi(chiave, valore) {
    /* L'unica strada verso il disco, e non arriva al disco: arriva a una
     * domanda. Se il ponte non c'e' — galleria — non succede niente, ed e'
     * giusto: in galleria non c'e' un core a cui chiedere. */
    window.jarvis?.impostaValore?.(chiave, valore);
  }

  function rigaScalare(chiave, valore) {
    const riga = document.createElement("div");
    riga.className = "pnl-set__riga";
    const nome = document.createElement("span");
    nome.className = "pnl-set__chiave";
    nome.textContent = chiave;
    riga.appendChild(nome);

    if (typeof valore === "boolean") {
      const t = document.createElement("button");
      t.type = "button";
      t.className = "pnl-set__tasto";
      t.setAttribute("aria-pressed", String(valore));
      t.textContent = valore ? "acceso" : "spento";
      t.addEventListener("click", () => {
        const nuovo = t.getAttribute("aria-pressed") !== "true";
        chiedi(chiave, nuovo);
      });
      riga.appendChild(t);
    } else {
      const campo = document.createElement("input");
      campo.className = "pnl-set__campo";
      campo.type = "text";
      campo.value = String(valore);
      /* La larghezza viene dal contenuto, non da un numero scelto: vedi il
       * commento di .pnl-set__campo. Il minimo tiene leggibile un campo con
       * dentro «8»; il massimo impedisce a un valore lungo di schiacciare la
       * chiave fino a farla sparire. */
      campo.size = Math.min(Math.max(String(valore).length, 6), 26);
      campo.setAttribute("aria-label", chiave);
      /* `change` e non `input`: si chiede quando l'utente ha finito di
       * scrivere, non a ogni tasto. Con `input` un campo numerico manderebbe
       * una richiesta per ogni cifra, e ognuna aprirebbe una conferma. */
      campo.addEventListener("change", () => chiedi(chiave, campo.value));
      riga.appendChild(campo);
    }
    righe.set(chiave, riga);
    return riga;
  }

  function rigaBloccata(chiave, valore) {
    const riga = document.createElement("div");
    riga.className = "pnl-set__ferma";
    const nome = document.createElement("span");
    nome.className = "pnl-set__chiave";
    nome.textContent = chiave;
    const val = document.createElement("span");
    val.className = "pnl-set__valore";
    val.textContent = Array.isArray(valore)
      ? `${valore.length} radici`
      : String(valore);
    const motivo = document.createElement("span");
    motivo.className = "pnl-set__motivo";
    motivo.textContent = PERCHE_BLOCCATA[chiave] ?? "si cambia nel file";
    riga.append(nome, val, motivo);
    return riga;
  }

  function titolo(testo) {
    const h = document.createElement("div");
    h.className = "pnl-set__titolo";
    h.textContent = testo;
    return h;
  }

  function aggiorna(msg) {
    const modificabili = msg?.modificabili ?? {};
    const bloccate = msg?.bloccate ?? {};
    el.dataset.stato = "collegato";
    righe.clear();

    const chiavi = Object.keys(modificabili).sort();
    const usate = new Set();
    const pezzi = [];

    /* ⚠️ **Le bloccate stanno PRIMA**, e l'ordine e' una decisione.
     *
     * §26.7 elenca le sezioni cominciando dal catalogo, e la prima versione
     * seguiva quell'ordine mettendo le bloccate in fondo. Guardando lo scatto
     * §11.7 non si vedevano affatto: quaranta righe modificabili le avevano
     * spinte sotto il bordo, e la parte che dice «questo NON si cambia da qui,
     * ed ecco perche'» era l'unica invisibile.
     *
     * Non sono impostazioni: sono la cornice dentro cui si legge il resto —
     * se il microfono e' aperto, se il codice puo' girare, che parte del disco
     * e' visibile. Chi apre questa pagina deve leggerle prima di toccare
     * qualunque altra cosa, non dopo averla toccata. */
    const chiavibl = Object.keys(bloccate).sort();
    if (chiavibl.length) {
      const blocco = document.createElement("div");
      blocco.className = "pnl-set__sezione";
      blocco.appendChild(titolo("Si cambiano nel file, non da qui"));
      chiavibl.forEach((k) => blocco.appendChild(rigaBloccata(k, bloccate[k])));
      pezzi.push(blocco);
    }

    for (const sez of SEZIONI) {
      const mie = chiavi.filter((k) => sez.radici.includes(radice(k)));
      if (!mie.length) continue;
      mie.forEach((k) => usate.add(k));
      const blocco = document.createElement("div");
      blocco.className = "pnl-set__sezione";
      blocco.appendChild(titolo(sez.titolo));
      mie.forEach((k) => blocco.appendChild(rigaScalare(k, modificabili[k])));
      pezzi.push(blocco);
    }

    const altre = chiavi.filter((k) => !usate.has(k));
    if (altre.length) {
      const blocco = document.createElement("div");
      blocco.className = "pnl-set__sezione";
      blocco.appendChild(titolo("Altro"));
      altre.forEach((k) => blocco.appendChild(rigaScalare(k, modificabili[k])));
      pezzi.push(blocco);
    }

    sezioni.replaceChildren(...pezzi);
    piede.textContent =
      `${chiavi.length} modificabili · ${chiavibl.length} nel file · ${msg?.file ?? "—"}`;
  }

  /** L'esito di una scrittura, dal core. Vedi `.pnl-set__errore`. */
  function esito(msg) {
    const riga = righe.get(msg?.chiave);
    if (!riga) return;
    riga.dataset.esito = msg?.ok ? "scritto" : "rifiutato";
    const vecchio = riga.querySelector(".pnl-set__errore");
    if (vecchio) vecchio.remove();
    if (msg?.ok) {
      const controllo = riga.querySelector(".pnl-set__campo, .pnl-set__tasto");
      if (controllo?.tagName === "INPUT") controllo.value = String(msg.valore);
      else if (controllo) {
        controllo.setAttribute("aria-pressed", String(!!msg.valore));
        controllo.textContent = msg.valore ? "acceso" : "spento";
      }
      return;
    }
    const p = document.createElement("span");
    p.className = "pnl-set__errore";
    /* `textContent`: il messaggio d'errore viene dal core e nomina percorsi e
     * valori. Non e' markup e non deve poterlo diventare — R96. */
    p.textContent = String(msg?.errore ?? "rifiutato");
    riga.appendChild(p);
  }

  function stato(s) {
    if (s === "vuoto") {
      el.dataset.stato = "vuoto";
      sezioni.replaceChildren();
      piede.textContent = "in attesa del core";
    }
  }

  return { el, aggiorna, esito, stato };
}
