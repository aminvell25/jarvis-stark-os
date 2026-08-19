/* Pannello file manager — SPEC §13, §10.2.
 *
 * Mostra il contenuto di una directory consentita, coi dati che il core manda
 * da `list_dir`. Non tocca il disco e non puo' toccarlo: l'invariante 1 dice
 * che il renderer non tocca mai il disco, e questo pannello non ha nemmeno
 * modo di chiedere un'operazione — il preload espone solo la risposta a una
 * conferma (§6.2).
 *
 * Tre stati come il pannello telemetria: collegato, vuoto, galleria.
 */

export const meta = { nome: "files", versione: "1" };

const UNITA = ["B", "KiB", "MiB", "GiB", "TiB"];

function dimensione(b) {
  if (typeof b !== "number") return "—";
  let i = 0, v = b;
  while (v >= 1024 && i < UNITA.length - 1) { v /= 1024; i++; }
  return `${i === 0 ? v : v.toFixed(1)} ${UNITA[i]}`;
}

export const css = `
.pnl-file {
  --aug-border-bg: var(--cy-900);
  --aug-bl: var(--s-3);
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: 100%;
  height: 100%;
  min-width: calc(var(--grid) * 5);
  background: var(--bg-panel);
  color: var(--txt-primary);
  font-family: var(--font-ui);
  border-radius: var(--radius);
}
.pnl-file__testa {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding: var(--s-2);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.pnl-file__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.pnl-file__radice {
  flex: 1;
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
  overflow-wrap: anywhere;
}
.pnl-file__id, .pnl-file__ctrl {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.pnl-file__corpo { overflow: auto; }
.pnl-file__riga {
  display: grid;
  grid-template-columns: var(--s-4) 1fr calc(var(--grid) - var(--s-2)) calc(var(--grid) - var(--s-3));
  gap: var(--s-2);
  align-items: baseline;
  padding: 0 var(--s-3);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  color: var(--txt-dim);
}
.pnl-file__riga:nth-child(even) { background: var(--bg-raised); }
.pnl-file__glifo { color: var(--cy-700); }
.pnl-file__nome { color: var(--txt-primary); overflow-wrap: anywhere; }
.pnl-file__cat { color: var(--cy-700); font-size: var(--t-micro); text-transform: uppercase; letter-spacing: 0.10em; }
.pnl-file__dim { text-align: right; color: var(--cy-300); }
.pnl-file__piede {
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
.pnl-file__vuoto {
  display: none;
  padding: var(--s-4);
  font-family: var(--font-mono);
  font-size: var(--t-data);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
}
.pnl-file[data-stato="vuoto"] .pnl-file__corpo { display: none; }
.pnl-file[data-stato="vuoto"] .pnl-file__vuoto { display: block; }
`;

const HTML = `
<section class="pnl-file" data-stato="vuoto" data-augmented-ui="bl-clip border">
  <header class="pnl-file__testa">
    <span class="pnl-file__etichetta">File</span>
    <span class="pnl-file__radice" data-radice>&mdash;</span>
    <span class="pnl-file__id">B02</span>
    <span class="pnl-file__ctrl">&#8863; &#8865; &#8864;</span>
  </header>
  <div class="pnl-file__corpo" data-voci></div>
  <div class="pnl-file__vuoto">NESSUNA SORGENTE COLLEGATA</div>
  <footer class="pnl-file__piede" data-piede></footer>
</section>
`;

export function crea(contenitore) {
  contenitore.innerHTML = HTML;
  const el = contenitore.querySelector(".pnl-file");
  const voci = el.querySelector("[data-voci]");
  const piede = el.querySelector("[data-piede]");
  const radice = el.querySelector("[data-radice]");

  function aggiorna(msg) {
    el.dataset.stato = "collegato";
    radice.textContent = msg.path;

    /* ⚠️ R96 — qui c'era un `innerHTML` con i NOMI DEI FILE dentro.
     *
     * Un nome di file arriva dal disco, e l'invariante 5 lo classifica come
     * dato NON FIDATO tanto quanto il contenuto. Un file chiamato con del
     * markup scriveva markup dentro l'interfaccia — e l'interfaccia ha
     * `window.jarvis`, cioe' la funzione che risponde alle conferme di §6.2.
     * Un nome ben scelto in una cartella scaricata poteva approvare da solo
     * un'operazione distruttiva che stava aspettando l'utente.
     *
     * Trovato costruendo §26.5, guardando da dove passano i nomi dei file.
     * Nessun test lo copriva: il corpus di §11.9 verifica i topic, non le
     * stringhe che ci viaggiano dentro. Adesso ce n'e' uno.
     */
    voci.replaceChildren(...(msg.voci ?? []).map((v) => {
      const riga = document.createElement("div");
      riga.className = "pnl-file__riga";
      for (const [classe, testo] of [
        ["pnl-file__glifo", v.type === "dir" ? "\u25a1" : "\u00b7"],
        ["pnl-file__nome", String(v.name ?? "")],
        ["pnl-file__cat", String(v.categoria ?? (v.type === "dir" ? "cartella" : ""))],
        ["pnl-file__dim", v.type === "dir" ? "" : dimensione(v.size)],
      ]) {
        const s = document.createElement("span");
        s.className = classe;
        s.textContent = testo;
        riga.appendChild(s);
      }
      return riga;
    }));

    const totale = (msg.voci ?? []).reduce((n, v) => n + (v.size ?? 0), 0);
    const cartelle = (msg.voci ?? []).filter((v) => v.type === "dir").length;
    piede.textContent =
      `${msg.totale} voci · ${cartelle} cartelle · ${dimensione(totale)} · sola lettura`;
  }

  function stato(s) {
    if (s === "vuoto") {
      el.dataset.stato = "vuoto";
      radice.textContent = "—";
      piede.textContent = "in attesa del core";
    }
  }

  return { el, aggiorna, stato };
}
