/* Barra superiore — SPEC §13.
 *
 * §13, verbatim: «stato agente (nominal/degraded/offline), workspace 01–04 col
 * proprio accento, telemetria compatta, indicatore di ascolto, tray».
 *
 * ## L'accento porta informazione, non decora
 *
 * §13: «Workspace con dominio, non numeri vuoti… cosi' che la barra porti
 * informazione invece di contarli». Ogni workspace ha il proprio colore E il
 * proprio dominio scritto accanto: `02 FILE E PROGETTI` dice due cose in uno
 * spazio in cui `2` non ne diceva nessuna.
 *
 * ## ADR-010 l'aveva SVUOTATA, e si misura
 *
 * I quattro pulsanti di workspace erano l'unico contenuto lassu'. Diventati
 * filtri, di serie sono tutti spenti, e l'inchiostro della fascia e' sceso a
 * **5,2 %** contro il 25 % che il riferimento tiene — mezza barra era spazio
 * vuoto fra i filtri e `cpu`.
 *
 * La correzione non e' decorare: e' **mostrare cio' che gia' arriva e non si
 * vedeva**. `state.snapshot` porta fase, PID, uptime, numero di tool
 * nell'allowlist, client collegati, provider vocale, backend LLM, chiavi
 * presenti, radici consentite e quota T2 — dieci fatti veri che vivevano solo
 * dentro `jarvis doctor`. I byte sul socket li conta il renderer, come fa gia'
 * il pannello dei glifi.
 *
 * Le celle sono **riempite**, ed e' la stessa lezione delle icone di §26.3:
 * nel riferimento la barra e' una fila continua di riquadri accesi, non testo
 * su fondo scuro. Il testo da solo non fa densita' — misurato due volte.
 *
 * ## I domini delle categorie si accorciano, e la ragione va detta
 *
 * §13 vuole «workspace con dominio, non numeri vuoti». Il dominio resta, in
 * una parola: `01 SISTEMA` invece di `01 SISTEMA E TELEMETRIA`. Quello per
 * esteso e' nel `title`, e i 600 px risparmiati sono quelli in cui adesso
 * stanno undici campi veri. Un dominio lungo che occupa il posto di dieci
 * fatti non porta piu' informazione: ne porta meno.
 *
 * ## Il tray non c'e', ed e' una decisione
 *
 * §13 lo nomina. Non ci sarebbe niente da metterci: nessuna icona di notifica
 * esiste in questo sistema, e un riquadro vuoto in alto a destra sarebbe il
 * segnaposto che l'invariante 23 vieta. Dichiarato in `SEZIONE-13.md`.
 *
 * ## L'indicatore di ascolto dice la verita', che oggi e' «spento»
 *
 * `voice.enabled` e' falso di serie (Fase 9), quindi la riga dice ASCOLTO
 * SPENTO. Mostrare un microfono acceso perche' sta bene sarebbe la cosa
 * peggiore in tutta l'interfaccia.
 */

export const meta = { nome: "barra", versione: "1" };

export const css = `
.brr {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-1) var(--s-2);
  background: var(--bg-deep);
  border-bottom: var(--line-base) solid var(--cy-900);
  font-family: var(--font-ui);
  font-size: var(--t-label);
  color: var(--txt-dim);
}

/* ── i campi dello stato: riquadri RIEMPITI, non testo ────────────────────
 *
 * --fill-1 e' L 66, cioe' sopra la soglia con cui si misura l'inchiostro
 * della fascia. Il testo dentro NON puo' essere --txt-ghost: misurato,
 * 1,82:1 contro il riempimento, cioe' illeggibile. --icona da' 4,31:1 per
 * l'etichetta e --txt-primary 8,06:1 per il valore, che e' il verso giusto —
 * l'etichetta si legge, il valore si vede. */
/* ⚠️ RAGGIUNGIBILI, non solo presenti — e «overflow: hidden» non e' un
   troncamento, e' una CANCELLAZIONE SENZA RIMEDIO.
   Misurato con «node scripts/densita.mjs --traboccamento», che esiste per
   questo: a 1280 px la fila di campi eccede di 187 px su 541 (il 35 % in
   piu'), a 1024 di 437 su 285 (il 153 %), a 900 di 567 su 161 (il 352 %). Cioe'
   «up», «rx» e «scena» — l'uptime, i byte sul socket e la composizione a
   schermo — su una finestra da 1024 non esistono, e non c'e' nessun gesto che
   li riporti.
   Un campo che si vede solo per l'etichetta e' peggio di un campo che non c'e';
   un campo che non si vede affatto lo e' di piu'.
   «auto» e non «scroll»: la barra compare solo alle larghezze in cui i campi
   davvero non stanno — a 1536 non c'e'. E non porta niente di estraneo: la
   barra di scorrimento e' gia' nella palette, app.css la riporta per tutta
   l'app.
   Lo scatto e' PER CAMPO perche' i campi sono unita' indivisibili: fermarsi a
   meta' di «rx 11.0 kB» rimetterebbe in scena lo stesso difetto in piccolo. */
.brr__campi {
  display: flex;
  flex: 1;
  gap: var(--s-1);
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x proximity;
}
.brr__campi > * { scroll-snap-align: start; }
.brr__campo {
  display: flex;
  align-items: baseline;
  gap: var(--s-1);
  /* Padding orizzontale di UN passo, non due: misurato, con --s-2 i campi
     occupavano 838 px in 797 disponibili e l'ultimo — la scena — restava
     tagliato a meta'. Un campo di stato che si vede solo per l'etichetta e'
     peggio di un campo che non c'e'. */
  padding: var(--s-1);
  background: var(--fill-1);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.brr__et { color: var(--icona); text-transform: uppercase; }
.brr__vl { color: var(--txt-primary); }
/* Un campo che non ha ancora un valore resta SPENTO invece di mostrare un
   trattino su un riquadro acceso: acceso vuol dire «questo dato c'e'». */
.brr__campo[data-vuoto] { background: var(--bg-raised); }
.brr__campo[data-vuoto] .brr__vl { color: var(--txt-ghost); }

/* ── stato agente ─────────────────────────────────────────────────────── */
.brr__agente {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-1) var(--s-2);
  background: var(--fill-1);
  border-radius: var(--radius);
}
.brr__spia {
  width: var(--s-2);
  height: var(--s-2);
  background: var(--txt-ghost);
  border-radius: var(--radius);
}
.brr__livello {
  font-family: var(--font-mono);
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-ghost);
}
.brr[data-livello="nominal"] .brr__spia { background: var(--cy-500); }
.brr[data-livello="nominal"] .brr__livello { color: var(--cy-500); }
.brr[data-livello="degraded"] .brr__spia { background: var(--amber); }
.brr[data-livello="degraded"] .brr__livello { color: var(--amber); }

/* ── le quattro categorie ─────────────────────────────────────────────── */
/* ADR-010: sono FILTRI, non schede. Quindi aria-pressed e non aria-current:
   il secondo dichiara «questa e' la pagina in cui sei», e non e' piu' vero —
   non si cambia pagina, perche' non ci sono pagine. Un lettore di schermo che
   dicesse «pagina corrente» direbbe una cosa falsa. */
/* flex: 1 e non margin-left: auto sulle misure: auto si risolve in un
   numero di pixel qualunque — 502,766 nel primo giro dell'audit — e §11.8
   vuole spaziature che vengano dalla scala. Lo spazio lo assorbe chi sta
   prima, e resta uno spazio, non una misura. */
.brr__cat { display: flex; gap: var(--s-1); }
.brr__tasto {
  display: flex;
  align-items: baseline;
  gap: var(--s-1);
  background: var(--fill-1);
  border: 0;
  border-bottom: var(--line-bold) solid var(--cy-900);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-ghost);
  cursor: pointer;
}
/* Il filtro spento e' comunque un riquadro ACCESO: e' una voce del sistema,
   non un pulsante disabilitato. Acceso lo dice l'accento sul bordo basso, che
   e' il colore della categoria e non un grigio in piu'. */
.brr__tasto { color: var(--icona); }
.brr__tasto:hover { border-bottom-color: var(--cy-700); color: var(--icona-viva); }
.brr__tasto[aria-pressed="true"] {
  background: var(--fill-3);
  border-bottom-color: var(--accento);
  color: var(--bg-void);
}
.brr__dominio { color: var(--txt-primary); }
.brr__tasto[aria-pressed="true"] .brr__dominio { color: var(--bg-void); }

/* ── telemetria compatta ──────────────────────────────────────────────── */
.brr__misure {
  display: flex;
  gap: var(--s-1);
  font-family: var(--font-mono);
  font-size: var(--t-data);
}
.brr__misura {
  display: flex;
  gap: var(--s-1);
  align-items: baseline;
  padding: var(--s-1) var(--s-2);
  background: var(--fill-1);
  border-radius: var(--radius);
}
.brr__nome { color: var(--icona); font-size: var(--t-micro); letter-spacing: 0.10em; }
.brr__valore { color: var(--txt-primary); }
.brr__misura[data-caldo] { background: var(--amber); }
.brr__misura[data-caldo] .brr__nome,
.brr__misura[data-caldo] .brr__valore { color: var(--bg-void); }

/* ── ascolto ──────────────────────────────────────────────────────────── */
.brr__ascolto {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--icona);
  background: var(--fill-1);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  white-space: nowrap;
}
.brr__ascolto[data-acceso] { background: var(--cy-700); color: var(--bg-void); }
`;

//: §16: le soglie oltre cui una misura diventa una notizia. Le stesse del
//: pannello telemetria — due numeri diversi per la stessa soglia sarebbero
//: due opinioni su quando preoccuparsi.
const SOGLIA_RAM = 90;
const SOGLIA_TEMP = 75;
const SOGLIA_CPU = 90;

const MISURE = [
  ["cpu", "cpu_percent", "%", SOGLIA_CPU],
  ["ram", "ram_percent", "%", SOGLIA_RAM],
  ["temp", "package_temp_c", "°C", SOGLIA_TEMP],
];

/* I campi dello stato, e da dove viene ognuno.
 *
 * ⚠️ **Nessuno e' inventato**: sono tutti dentro `state.snapshot`, che il core
 * manda a chi si collega e che fino a ieri finiva solo dentro `jarvis doctor`.
 * L'unico calcolato qui e' `rx`, ed e' onesto che lo sia — quanti byte sono
 * passati sul socket lo sa solo chi li ha ricevuti.
 *
 * `da(m)` ritorna `null` quando il dato non c'e': il riquadro resta spento
 * invece di mostrare un trattino su un fondo acceso. Acceso vuol dire «questo
 * dato c'e'» (invariante 23).
 */
const CAMPI = [
  { id: "fase", et: "fase", da: (m) => m.fase },
  { id: "pid", et: "pid", da: (m) => m.core?.pid },
  { id: "tool", et: "tool", da: (m) => m.tools?.length },
  { id: "client", et: "cli", da: (m) => m.ws?.clients },
  { id: "radici", et: "radici", da: (m) => m.settings?.fs?.allowed_roots?.length },
  { id: "chiavi", et: "chiavi", da: (m) => m.settings?.chiavi_presenti?.length },
  { id: "stt", et: "stt", da: (m) => m.settings?.voice?.stt_provider },
  { id: "llm", et: "llm", da: (m) => m.settings?.llm?.backend },
  { id: "t2", et: "t2",
    da: (m) => (m.quota ? `${m.quota.attivi}/${m.quota.max_concurrent}` : null) },
];

/** `hh:mm:ss` da secondi. Il tempo si dice cosi', non in secondi a sei cifre. */
function orologio(s) {
  const n = Math.max(0, Math.round(s));
  const p = (x) => String(x).padStart(2, "0");
  return `${p((n / 3600) | 0)}:${p(((n / 60) | 0) % 60)}:${p(n % 60)}`;
}

/** Byte in una forma che sta in una cella. */
function peso(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} kB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

export function crea(ospite, { scrivania, bus, categorie }) {
  const el = document.createElement("header");
  el.className = "brr";
  el.dataset.livello = "offline";

  const agente = document.createElement("div");
  agente.className = "brr__agente";
  const spia = document.createElement("span");
  spia.className = "brr__spia";
  const livello = document.createElement("span");
  livello.className = "brr__livello";
  livello.textContent = "offline";
  agente.append(spia, livello);

  const cat = document.createElement("nav");
  cat.className = "brr__cat";
  cat.setAttribute("aria-label", "categorie");
  const tasti = new Map();
  for (const c of categorie) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "brr__tasto";
    // L'accento della categoria arriva dal TOKEN dichiarato in `moduli.js`: la
    // barra non conosce nessun colore, sa solo dove chiederlo (invariante 18).
    b.style.setProperty("--accento", `var(${c.accento})`);
    b.setAttribute("aria-pressed", "false");
    b.title = `filtra: ${c.dominio} — di nuovo per togliere il filtro`;
    const n = document.createElement("span");
    n.textContent = String(c.n).padStart(2, "0");
    const d = document.createElement("span");
    d.className = "brr__dominio";
    // La prima parola del dominio. Quello per esteso resta nel `title`: §13
    // vuole un dominio e non un numero vuoto, e una parola e' un dominio —
    // i 600 px risparmiati sono quelli in cui stanno i nove campi di stato.
    d.textContent = c.dominio.split(" ")[0];
    b.append(n, d);
    b.addEventListener("click", () => scrivania.vai(c.n));
    tasti.set(c.n, b);
    cat.appendChild(b);
  }

  /* I campi dello stato. Si costruiscono tutti adesso e spenti: comparire uno
   * per volta man mano che i dati arrivano farebbe saltare la barra a ogni
   * messaggio, e con essa l'area utile che i pannelli hanno gia' misurato. */
  const campi = document.createElement("div");
  campi.className = "brr__campi";
  const celle = new Map();
  const cella = (id, etichetta) => {
    const c = document.createElement("span");
    c.className = "brr__campo";
    c.dataset.campo = id;
    c.dataset.vuoto = "";
    const e = document.createElement("span");
    e.className = "brr__et";
    e.textContent = etichetta;
    const v = document.createElement("span");
    v.className = "brr__vl";
    v.textContent = "—";
    c.append(e, v);
    celle.set(id, { cella: c, valore: v });
    campi.appendChild(c);
    return c;
  };
  for (const c of CAMPI) cella(c.id, c.et);
  // Due che non vengono da `state.snapshot` e non possono venirci: l'uptime
  // avanza da solo, e i byte li conta chi li riceve.
  cella("up", "up");
  cella("rx", "rx");
  // §26.6 — quale composizione e' a schermo. Sta in barra perche' e' lo stato
  // dell'AMBIENTE, come il filtro: il catalogo dice quali scene esistono,
  // questo dice in quale ci si trova.
  cella("scena", "scena");

  const scrivi = (id, v) => {
    const r = celle.get(id);
    if (!r) return;
    if (v === undefined || v === null || v === "") {
      r.valore.textContent = "—";
      r.cella.dataset.vuoto = "";
      return;
    }
    r.valore.textContent = String(v);
    delete r.cella.dataset.vuoto;
  };

  const misure = document.createElement("div");
  misure.className = "brr__misure";
  const valori = new Map();
  for (const [nome, , unita] of MISURE) {
    const m = document.createElement("span");
    m.className = "brr__misura";
    const et = document.createElement("span");
    et.className = "brr__nome";
    et.textContent = nome;
    const v = document.createElement("span");
    v.className = "brr__valore";
    v.textContent = `—${unita}`;
    m.append(et, v);
    valori.set(nome, { riquadro: m, valore: v });
    misure.appendChild(m);
  }

  const ascolto = document.createElement("div");
  ascolto.className = "brr__ascolto";
  ascolto.textContent = "ascolto spento";

  el.append(agente, cat, campi, misure, ascolto);
  ospite.appendChild(el);

  /* ── cio' che la barra ascolta ──────────────────────────────────────── */

  scrivania.osserva(({ filtro, scena }) => {
    for (const [k, b] of tasti) b.setAttribute("aria-pressed", String(k === filtro));
    scrivi("scena", scena);
  });

  /* L'uptime avanza da solo fra due snapshot. Non e' animazione senza causa
   * (invariante 25): la causa e' che il tempo passa, ed e' esattamente il dato
   * che il campo dichiara. Un secondo, non un fotogramma. */
  let uptimeBase = null;
  let uptimeDa = 0;
  const battito = setInterval(() => {
    if (uptimeBase === null) return;
    scrivi("up", orologio(uptimeBase + (Date.now() - uptimeDa) / 1000));
  }, 1000);

  /* ⚠️ La leva del modo di MISURA — §11.9, seconda eccezione.
   *
   * Ferma il battito e riscrive `up` con l'uptime **del campione**, cioe' quello
   * che la registrazione contiene. Senza, due riproduzioni della stessa
   * sessione mostrano due uptime diversi, perche' quel campo non misura la
   * sessione: misura da quanto e' aperta la finestra.
   *
   * E' la forma gia' accettata di `window.__insegna.fissa()` in `desk/sfondo.js`,
   * che `app/main.js` aziona per congelare il nucleo negli scatti per stato.
   * Non falsifica niente: scrive il numero che il core ha mandato, invece di
   * quello che l'orologio locale ha aggiunto dopo.
   *
   * ⚠️ Non vale fuori dalla misura. Dal vivo la causa e' che il tempo passa, e
   * il commento qui sopra ha ragione. */
  function fissa() {
    clearInterval(battito);
    if (uptimeBase !== null) scrivi("up", orologio(uptimeBase));
    return { up: uptimeBase };
  }

  /* I byte sul socket: li conta chi li riceve. Stessa sorgente del pannello
   * dei glifi — `suOgni`, cioe' tutto il traffico, telemetria compresa. */
  let byte = 0;
  const codifica = new TextEncoder();
  bus.suOgni((m) => {
    byte += codifica.encode(JSON.stringify(m)).length;
    scrivi("rx", peso(byte));
  });

  bus.su("telemetry", (m) => {
    for (const [nome, campo, unita, soglia] of MISURE) {
      const v = m[campo];
      const r = valori.get(nome);
      if (typeof v !== "number") continue;
      r.valore.textContent = `${v.toFixed(1)}${unita}`;
      // L'unico accento caldo, e sempre semantico (§11.6 regola 2).
      if (v >= soglia) r.riquadro.dataset.caldo = "";
      else delete r.riquadro.dataset.caldo;
    }
  });

  bus.su("state.snapshot", (m) => {
    for (const c of CAMPI) scrivi(c.id, c.da(m));
    if (typeof m.core?.uptime_s === "number") {
      uptimeBase = m.core.uptime_s;
      uptimeDa = Date.now();
      scrivi("up", orologio(uptimeBase));
    }
    const scaduta = m.voce?.auth?.stato === "degraded_llm";
    el.dataset.livello = scaduta ? "degraded" : "nominal";
    livello.textContent = scaduta ? "degraded" : "nominal";
    const accesa = Boolean(m.voce?.abilitata);
    ascolto.textContent = accesa ? "in ascolto" : "ascolto spento";
    if (accesa) ascolto.dataset.acceso = "";
    else delete ascolto.dataset.acceso;
  });

  bus.su("agent.advisory", (m) => {
    if (m.level !== "critical") return;
    el.dataset.livello = "degraded";
    livello.textContent = "degraded";
  });

  bus.suStato(({ stato }) => {
    if (stato === "connesso") return;
    // Offline non e' degraded: degraded vuol dire che JARVIS c'e' e funziona
    // peggio, offline che non c'e'. §16 le tiene distinte, e la barra pure.
    el.dataset.livello = "offline";
    livello.textContent = "offline";
    for (const [, r] of valori) {
      r.valore.textContent = "—";
      delete r.riquadro.dataset.caldo;
    }
    // I campi si SPENGONO: col core scollegato non sono vecchi, sono ignoti.
    // L'uptime si ferma, perche' non sappiamo piu' da quanto e' acceso.
    uptimeBase = null;
    for (const id of celle.keys()) if (id !== "scena") scrivi(id, null);
  });

  return { el, altezza: () => el.getBoundingClientRect().height, fissa };
}
