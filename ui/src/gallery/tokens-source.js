/* La verita' di base dell'audit.
 *
 * L'audit non contiene una lista di colori scritta a mano: la ricava da
 * tokens.css a ogni caricamento. Se domani si aggiunge un token, l'audit lo
 * conosce senza che nessuno lo aggiorni — ed e' l'unico modo perche' non
 * diventi obsoleto in silenzio, che e' come muoiono i linter fatti in casa.
 *
 * Nota importante sul perimetro: tokens.css dichiara anche valori LETTERALI,
 * per esempio la ricetta del vetro di `.jarvis-panel`
 * (`background: rgba(14,19,21,.62)`). Non e' una violazione: il commento di
 * §10.1 dice "NESSUN valore letterale ALTROVE". tokens.css e' il luogo dove i
 * letterali sono legittimi, perche' e' la sorgente. Quindi la verita' di base
 * e' TUTTO cio' che tokens.css dichiara, custom property e letterali insieme.
 */

const E_TOKENS = /tokens\.css(\?|$)/;

/** Fogli esenti dall'audit del SORGENTE, con la ragione di ciascuno. */
export const FOGLI_ESENTI = [
  { test: E_TOKENS, perche: "e' la sorgente di verita': i letterali qui sono leciti" },
  {
    test: /gallery\/chrome\.css(\?|$)/,
    perche: "arredo della galleria, strumento di sviluppo: non e' un componente e non viene spedito",
  },
];

export function foglioEsente(sheet) {
  const href = sheet.href || "";
  return FOGLI_ESENTI.find((r) => r.test.test(href)) ?? null;
}

/** Legge tokens.css e restituisce custom property + letterali dichiarati. */
export function leggiTokens() {
  const sheet = [...document.styleSheets].find((s) => E_TOKENS.test(s.href || ""));
  if (!sheet) {
    throw new Error(
      "tokens.css non e' fra i fogli di stile: l'audit non ha verita' di base " +
        "e rifiuta di girare. Un audit senza riferimento direbbe che tutto va bene."
    );
  }

  const custom = new Map();      // "--cy-500" -> "#4dd0e1"
  const letterali = new Set();   // ogni valore non-custom dichiarato in tokens.css

  for (const rule of sheet.cssRules) {
    if (!(rule instanceof CSSStyleRule)) continue;
    for (const prop of rule.style) {
      const valore = rule.style.getPropertyValue(prop).trim();
      if (prop.startsWith("--")) custom.set(prop, valore);
      else letterali.add(valore);
    }
  }
  return { custom, letterali };
}

/** Divide le custom property per famiglia, dal prefisso del nome. */
export function categorizza(custom) {
  const per = (pred) =>
    new Map([...custom].filter(([nome]) => pred(nome)));

  return {
    colore: per((n) =>
      /^--(bg|cy|txt)-/.test(n) || n === "--amber" || n === "--rust"),
    linea: per((n) => n.startsWith("--line-")),
    spazio: per((n) => /^--s-\d$/.test(n) || n === "--gap"),
    corpo: per((n) => n.startsWith("--t-")),
    famiglia: per((n) => n.startsWith("--font-")),
    raggio: per((n) => n === "--radius"),
  };
}
