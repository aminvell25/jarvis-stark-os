/* Audit dei token — `&tokens=audit`.
 *
 * DUE LIVELLI, e servono entrambi.
 *
 * Livello 1 (valore calcolato) legge `getComputedStyle`. Vede tutto: stili
 * inline, stili impostati da JS, cascata risolta. Ma NON puo' distinguere
 * `var(--cy-500)` da un `#4dd0e1` battuto a mano, perche' entrambi calcolano
 * a `rgb(77, 208, 225)`.
 *
 * Livello 2 (sorgente della regola) legge `document.styleSheets`. Vede come
 * il valore e' stato SCRITTO. L'invariante 18 non dice "usa valori che stanno
 * nella palette", dice "zero valori letterali": e' verificabile solo cosi'.
 * Con il solo livello 1 l'invariante 18 resterebbe una convenzione.
 *
 * REGOLA DELLE OMBRE (decisione sul rilievo R2, vedi docs/acceptance).
 * L'invariante 19 del CLAUDE.md dice "solo inset box-shadow", ma §10.1 —
 * che e' copiata verbatim — contiene un'ombra ESTERNA nera in `.jarvis-panel`.
 * Applicare l'invariante alla lettera farebbe fallire a tokens.css il proprio
 * audit. La lettura adottata:
 *
 *   Un'ombra esterna e' ammessa solo se SCURISCE. Un'ombra che schiarisce e'
 *   un alone e va bocciata; un'ombra piu' scura del fondo e' profondita'.
 *   `filter: drop-shadow` resta vietato senza eccezioni: box-shadow non si
 *   propaga al contenuto, drop-shadow si', ed e' quello il vettore del glow
 *   della Famiglia B.
 */

import { categorizza, foglioEsente, leggiTokens } from "./tokens-source.js";

const MARCA = "data-audit";           // gli elementi dell'audit non si autoauditano

/* ── utilita' di colore ──────────────────────────────────────────────────── */

let _probe;
function probe() {
  if (!_probe) {
    _probe = document.createElement("span");
    _probe.setAttribute(MARCA, "probe");
    _probe.style.display = "none";
    document.body.appendChild(_probe);
  }
  return _probe;
}

/** Porta qualunque notazione di colore alla forma canonica del browser. */
export function canonizzaColore(valore) {
  const el = probe();
  el.style.color = "";
  el.style.color = valore;
  if (!el.style.color) return null;              // non era un colore
  return getComputedStyle(el).color;
}

function componenti(rgb) {
  const m = rgb.match(/-?[\d.]+/g);
  if (!m) return null;
  const [r, g, b] = m.map(Number);
  return { r, g, b, a: m.length > 3 ? Number(m[3]) : 1 };
}

/** Luminanza relativa WCAG, 0 = nero, 1 = bianco. */
export function luminanza(rgb) {
  const c = componenti(rgb);
  if (!c) return 0;
  const lin = (v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
}

function alpha(rgb) {
  return componenti(rgb)?.a ?? 1;
}

/** Divide su virgole di primo livello, ignorando quelle dentro `rgba(...)`. */
export function dividiVirgole(testo) {
  const parti = [];
  let livello = 0, corrente = "";
  for (const ch of testo) {
    if (ch === "(") livello++;
    else if (ch === ")") livello--;
    if (ch === "," && livello === 0) { parti.push(corrente.trim()); corrente = ""; }
    else corrente += ch;
  }
  if (corrente.trim()) parti.push(corrente.trim());
  return parti;
}

const numero = (v) => parseFloat(v);
const eZero = (v) => numero(v) === 0;

/* ── livello 1: valore calcolato ─────────────────────────────────────────── */

const PROP_COLORE = ["color", "background-color", "border-top-color",
  "border-right-color", "border-bottom-color", "border-left-color"];
const PROP_SPAZIO = ["padding-top", "padding-right", "padding-bottom", "padding-left",
  "margin-top", "margin-right", "margin-bottom", "margin-left",
  "row-gap", "column-gap"];
const PROP_LINEA = ["border-top-width", "border-right-width",
  "border-bottom-width", "border-left-width"];
const PROP_RAGGIO = ["border-top-left-radius", "border-top-right-radius",
  "border-bottom-left-radius", "border-bottom-right-radius"];

export function creaAuditCalcolato(tokens) {
  const cat = categorizza(tokens.custom);

  const coloriAmmessi = new Set();
  for (const v of cat.colore.values()) {
    const c = canonizzaColore(v); if (c) coloriAmmessi.add(c);
  }
  for (const v of tokens.letterali) {           // la ricetta del vetro di §10.1
    const c = canonizzaColore(v); if (c) coloriAmmessi.add(c);
  }
  coloriAmmessi.add("rgba(0, 0, 0, 0)");        // trasparente: assenza, non scelta

  const spaziAmmessi = new Set([...cat.spazio.values()].map(numero));
  const lineeAmmesse = new Set([...cat.linea.values()].map(numero));
  const corpiAmmessi = new Set([...cat.corpo.values()].map(numero));
  const famiglieAmmesse = [...cat.famiglia.values()].map((v) =>
    v.split(",")[0].trim().replace(/^["']|["']$/g, "").toLowerCase());

  const fondoPagina = luminanza(
    canonizzaColore(tokens.custom.get("--bg-void") || "#000") || "rgb(0,0,0)");

  return function auditaElemento(el) {
    const cs = getComputedStyle(el);
    const guasti = [];
    const guasto = (prop, trovato, atteso) => guasti.push({ prop, trovato, atteso });

    for (const p of PROP_COLORE) {
      const v = cs.getPropertyValue(p);
      if (v && !coloriAmmessi.has(v)) guasto(p, v, "un colore di tokens.css");
    }

    for (const p of PROP_SPAZIO) {
      const v = cs.getPropertyValue(p);
      if (!v) continue;
      const n = numero(v);
      // `normal` (gap iniziale fuori da flex/grid), `auto`: non sono lunghezze
      // e non esprimono alcuna decisione di spaziatura. Senza questo controllo
      // NaN % 4 !== 0 e' vero e OGNI elemento risulta violare. E' il falso
      // positivo che la fixture conforme ha scoperto al primo giro: un audit
      // che boccia tutto e' inutile quanto uno che non boccia niente.
      if (Number.isNaN(n)) continue;
      if (n === 0 || spaziAmmessi.has(n)) continue;
      if (n % 4 !== 0) guasto(p, v, "multiplo di 4 (§11.8), meglio la scala --s-*");
    }

    for (const p of PROP_LINEA) {
      const v = cs.getPropertyValue(p);
      if (v && !Number.isNaN(numero(v)) && !eZero(v) && !lineeAmmesse.has(numero(v)))
        guasto(p, v, "--line-hair | --line-base | --line-bold");
    }

    for (const p of PROP_RAGGIO) {
      const v = cs.getPropertyValue(p);
      if (v && !eZero(v)) guasto(p, v, "0 — invariante 18, --radius e' sempre zero");
    }

    const corpo = numero(cs.fontSize);
    if (corpo && !corpiAmmessi.has(corpo))
      guasto("font-size", cs.fontSize, "uno dei cinque gradini --t-*");

    const fam = (cs.fontFamily.split(",")[0] || "").trim()
      .replace(/^["']|["']$/g, "").toLowerCase();
    if (fam && !famiglieAmmesse.includes(fam))
      guasto("font-family", cs.fontFamily, "--font-ui oppure --font-mono");

    if (/drop-shadow/i.test(cs.filter))
      guasto("filter", cs.filter, "nessun drop-shadow — invariante 19, senza eccezioni");

    if (cs.boxShadow && cs.boxShadow !== "none") {
      for (const ombra of dividiVirgole(cs.boxShadow)) {
        if (/\binset\b/.test(ombra)) continue;            // inset: sempre lecita
        const col = ombra.match(/(rgba?\([^)]*\)|#[0-9a-f]{3,8})/i)?.[0];
        if (!col) continue;
        const canon = canonizzaColore(col);
        if (!canon || alpha(canon) === 0) continue;
        if (luminanza(canon) > fondoPagina)
          guasto("box-shadow", ombra,
            "un'ombra esterna deve SCURIRE; questa schiarisce ed e' un alone (inv. 19)");
      }
    }
    return guasti;
  };
}

/* ── livello 2: sorgente della regola ────────────────────────────────────── */

const PROP_SORVEGLIATE = new Set(["color", "background", "background-color",
  "border", "border-color", "border-width", "border-top", "border-right",
  "border-bottom", "border-left", "border-radius", "font", "font-size",
  "font-family", "padding", "margin", "gap", "row-gap", "column-gap",
  "box-shadow", "filter",
  ...PROP_COLORE, ...PROP_SPAZIO, ...PROP_LINEA, ...PROP_RAGGIO]);

const NOMI_COLORE = /\b(aqua|black|blue|cyan|fuchsia|gray|grey|green|lime|magenta|maroon|navy|olive|orange|purple|red|silver|teal|white|yellow)\b/i;

/** I letterali dentro un valore CSS. Vuoto = il valore viene tutto da token. */
export function letteraliIn(valore) {
  const senzaVar = valore.replace(/var\(\s*--[\w-]+\s*\)/g, "·");
  const trovati = [];
  const cerca = (re) => { for (const m of senzaVar.matchAll(re)) trovati.push(m[0]); };
  cerca(/#[0-9a-f]{3,8}\b/gi);
  cerca(/\b(?:rgba?|hsla?|hwb|lab|lch|color)\([^)]*\)/gi);
  cerca(new RegExp(NOMI_COLORE.source, "gi"));
  for (const m of senzaVar.matchAll(/(?<![\w.#-])(\d*\.?\d+)(px|rem|em|pt|vh|vw)\b/gi))
    if (parseFloat(m[1]) !== 0) trovati.push(m[0]);
  return trovati;
}

export function auditaSorgenti() {
  const guasti = [];
  for (const sheet of document.styleSheets) {
    if (foglioEsente(sheet)) continue;
    let regole;
    try { regole = sheet.cssRules; } catch { continue; }   // foglio d'altra origine
    for (const rule of regole) {
      if (!(rule instanceof CSSStyleRule)) continue;
      for (const prop of rule.style) {
        if (!PROP_SORVEGLIATE.has(prop)) continue;
        const valore = rule.style.getPropertyValue(prop);
        const letterali = letteraliIn(valore);
        if (letterali.length)
          guasti.push({ selettore: rule.selectorText, prop, valore, letterali,
                        foglio: sheet.href?.split("/").pop() ?? "<inline>" });
      }
    }
  }
  return guasti;
}

/* ── esecuzione e resa ───────────────────────────────────────────────────── */

export function esegui(radice) {
  const tokens = leggiTokens();
  const auditaElemento = creaAuditCalcolato(tokens);

  const calcolati = [];
  for (const el of radice.querySelectorAll("*")) {
    if (el.closest(`[${MARCA}]`)) continue;               // arredo dell'audit
    const guasti = auditaElemento(el);
    if (!guasti.length) continue;
    const indice = calcolati.length + 1;
    calcolati.push({ el, guasti, dove: descrivi(el), indice });
    el.classList.add("audit-violazione");
    el.appendChild(marcatore(indice, guasti.length));
  }

  const sorgenti = auditaSorgenti();
  return { calcolati, sorgenti, totale: calcolati.length + sorgenti.length };
}

/** Un identificatore leggibile dell'elemento, per il rapporto testuale. */
function descrivi(el) {
  const cls = [...el.classList].filter((c) => !c.startsWith("audit-"));
  return el.tagName.toLowerCase() + (cls.length ? "." + cls.join(".") : "");
}

/* Sull'elemento va solo un INDICE, non l'elenco delle violazioni.
 *
 * La prima versione stampava ogni guasto in un riquadro sopra l'elemento. Lo
 * screenshot del ciclo §11.7 lo ha smentito subito: con quattro elementi
 * annidati i riquadri si accavallavano e coprivano il componente, cioe' la
 * cosa che il ciclo esiste per farmi GUARDARE. Con venti componenti in Fase 5
 * sarebbe stato inservibile.
 *
 * Ora: il contorno magenta dice DOVE, la barra in alto dice COSA. Lo
 * screenshot resta leggibile e il componente resta giudicabile.
 */
function marcatore(indice, quanti) {
  const b = document.createElement("span");
  b.setAttribute(MARCA, "marcatore");
  b.className = "audit-marcatore";
  b.textContent = `${indice}·${quanti}`;
  b.title = `violazione ${indice}: ${quanti} guasti — dettaglio nella barra`;
  return b;
}
