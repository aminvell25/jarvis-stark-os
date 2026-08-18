/* Galleria dei componenti — SPEC §11.7 passo 1.
 *
 *   ?component=<nome>   un solo componente, isolato
 *   ?component=all      tutti, in griglia
 *   &grid=1             griglia --grid sovrapposta
 *   &tokens=audit       evidenzia cio' che non viene dai token
 *
 * L'esito finisce in `window.__gallery` e in `data-stato` sul body: e' cosi'
 * che `npm run shot` sa se lo scatto vale qualcosa.
 */

import { esegui } from "./audit.js";
import { verificaFont } from "./fonts-guard.js";
import { montaGriglia } from "./grid.js";
import { risolvi } from "./registry.js";

const params = new URLSearchParams(location.search);
const nome = params.get("component") ?? "all";
const conGriglia = params.get("grid") === "1";
const conAudit = params.get("tokens") === "audit";

const palco = document.getElementById("palco");
const barra = document.getElementById("barra");

function avviso(testo, livello) {
  const el = document.createElement("div");
  el.className = `avviso avviso--${livello}`;
  el.textContent = testo;
  barra.appendChild(el);
}

async function main() {
  let componenti;
  try {
    componenti = risolvi(nome);
  } catch (err) {
    avviso(err.message, "errore");
    finisci({ errore: err.message });
    return;
  }

  const stile = document.createElement("style");
  stile.textContent = componenti.map((c) => c.css).join("\n");
  document.head.appendChild(stile);

  for (const c of componenti) {
    const cella = document.createElement("div");
    cella.className = "cella";
    cella.innerHTML =
      `<div class="cella__nome" data-audit="etichetta">${c.meta.nome} · ver ${c.meta.versione}</div>` +
      c.html;
    palco.appendChild(cella);
  }

  if (conGriglia) montaGriglia(palco);

  // I font PRIMA dell'audit: senza, si misurerebbero corpi resi con un
  // ripiego, e la tipografia risulterebbe conforme per caso.
  const fontMancanti = await verificaFont();
  if (fontMancanti.length) {
    avviso(
      `FONT ASSENTI: ${fontMancanti.join(", ")}. Lo screenshot NON e' una ` +
      `verifica valida — vedi ui/src/style/fonts/README.md`,
      "errore"
    );
  }

  let esito = null;
  if (conAudit) {
    document.body.classList.add("audit-attivo");
    esito = esegui(palco);
    if (esito.totale === 0) {
      avviso("AUDIT PULITO — nessun valore fuori dai token", "ok");
    } else {
      avviso(
        `AUDIT: ${esito.calcolati.length} elementi fuori sistema, ` +
        `${esito.sorgenti.length} regole con valori letterali`,
        "errore"
      );
      // Compatto: una riga per elemento e una per selettore. L'elenco
      // completo lo stampa `npm run shot`, dove lo spazio non e' un problema
      // e non compete con la lettura del componente.
      for (const c of esito.calcolati) {
        avviso(`[${c.indice}] ${c.dove} — ` +
               c.guasti.map((g) => `${g.prop}: ${g.trovato}`).join(" · "),
               "dettaglio");
      }
      const perSelettore = new Map();
      for (const g of esito.sorgenti) {
        const k = `${g.foglio} — ${g.selettore}`;
        if (!perSelettore.has(k)) perSelettore.set(k, new Set());
        for (const l of g.letterali) perSelettore.get(k).add(l);
      }
      for (const [sel, letterali] of perSelettore) {
        avviso(`${sel} → letterali: ${[...letterali].join(", ")}`, "dettaglio");
      }
    }
  }

  finisci({
    componente: nome,
    audit: conAudit,
    fontMancanti,
    violazioniCalcolate: esito ? esito.calcolati.length : null,
    violazioniSorgente: esito ? esito.sorgenti.length : null,
    dettaglioSorgente: esito ? esito.sorgenti : [],
    dettaglioCalcolato: esito
      ? esito.calcolati.map((c) => ({ dove: c.dove, guasti: c.guasti }))
      : [],
  });
}

function finisci(riepilogo) {
  window.__gallery = riepilogo;
  document.body.dataset.stato = "pronto";
}

main().catch((err) => {
  avviso(`errore non gestito: ${err.message}`, "errore");
  finisci({ errore: String(err) });
});
