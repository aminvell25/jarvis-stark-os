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
  padding: var(--s-2) var(--s-3);
  background: var(--bg-deep);
  border-bottom: var(--line-base) solid var(--cy-900);
  font-family: var(--font-ui);
  font-size: var(--t-label);
  color: var(--txt-dim);
}

/* ── stato agente ─────────────────────────────────────────────────────── */
.brr__agente {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  min-width: calc(var(--grid) * 1.6);
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

/* ── workspace ────────────────────────────────────────────────────────── */
/* flex: 1 e non margin-left: auto sulle misure: auto si risolve in un
   numero di pixel qualunque — 502,766 nel primo giro dell'audit — e §11.8
   vuole spaziature che vengano dalla scala. Lo spazio lo assorbe chi sta
   prima, e resta uno spazio, non una misura. */
.brr__ws { display: flex; gap: var(--s-1); flex: 1; }
.brr__tasto {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  background: none;
  border: var(--line-base) solid var(--cy-900);
  border-radius: var(--radius);
  padding: var(--s-1) var(--s-2);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-ghost);
  cursor: pointer;
}
.brr__tasto:hover { border-color: var(--cy-700); color: var(--txt-dim); }
.brr__tasto[aria-current="true"] {
  border-color: var(--accento);
  color: var(--accento);
}
.brr__dominio { color: var(--txt-ghost); }
.brr__tasto[aria-current="true"] .brr__dominio { color: var(--txt-dim); }

/* ── telemetria compatta ──────────────────────────────────────────────── */
.brr__misure {
  display: flex;
  gap: var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-data);
}
.brr__misura { display: flex; gap: var(--s-1); align-items: baseline; }
.brr__nome { color: var(--txt-ghost); font-size: var(--t-micro); letter-spacing: 0.10em; }
.brr__valore { color: var(--cy-300); }
.brr__misura[data-caldo] .brr__valore { color: var(--amber); }

/* ── ascolto ──────────────────────────────────────────────────────────── */
.brr__ascolto {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--txt-ghost);
  border-left: var(--line-hair) solid var(--cy-900);
  padding-left: var(--s-3);
}
.brr__ascolto[data-acceso] { color: var(--cy-500); }
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

export function crea(ospite, { scrivania, bus, workspace }) {
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

  const ws = document.createElement("nav");
  ws.className = "brr__ws";
  ws.setAttribute("aria-label", "workspace");
  const tasti = new Map();
  for (const w of workspace) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "brr__tasto";
    // L'accento del workspace arriva dal TOKEN dichiarato in `moduli.js`: la
    // barra non conosce nessun colore, sa solo dove chiederlo (invariante 18).
    b.style.setProperty("--accento", `var(${w.accento})`);
    const n = document.createElement("span");
    n.textContent = String(w.n).padStart(2, "0");
    const d = document.createElement("span");
    d.className = "brr__dominio";
    d.textContent = w.dominio;
    b.append(n, d);
    b.addEventListener("click", () => scrivania.vai(w.n));
    tasti.set(w.n, b);
    ws.appendChild(b);
  }

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

  el.append(agente, ws, misure, ascolto);
  ospite.appendChild(el);

  /* ── cio' che la barra ascolta ──────────────────────────────────────── */

  scrivania.osserva(({ workspace: n }) => {
    for (const [k, b] of tasti) b.setAttribute("aria-current", String(k === n));
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
  });

  return { el, altezza: () => el.getBoundingClientRect().height };
}
