/* Fixture NON CONFORME — deve illuminarsi di magenta.
 *
 * Ogni violazione e' deliberata e annotata col punto di SPEC §11.8 che
 * infrange. Serve come test di regressione dell'audit: se un giorno una di
 * queste righe smette di essere segnalata, l'audit si e' rotto.
 *
 * Non e' un componente reale ne' un esempio da imitare.
 */

export const meta = { nome: "non-conforme", versione: "1.0" };

export const violazioniAttese = [
  { prop: "border-radius", punto: "§11.8 GEOMETRIA — border-radius e' 0 ovunque?" },
  { prop: "color",         punto: "§11.8 COLORE — tutti i colori da tokens.css?" },
  { prop: "font-size",     punto: "§11.8 TIPOGRAFIA — solo i cinque gradini?" },
  { prop: "padding",       punto: "§11.8 GEOMETRIA — ogni spaziatura multiplo di 4?" },
  { prop: "box-shadow",    punto: "§11.8 COLORE — zero glow (invariante 19)" },
  { prop: "border-width",  punto: "§11.8 GEOMETRIA — pesi di linea solo hair/base/bold" },
  { prop: "box-shadow",    punto: "§11.8 COLORE — ombra portata COLORATA (inv. 19, rev 5.13)" },
];

export const css = `
.fx-rotta {
  /* ① GEOMETRIA: border-radius deve essere 0 — invariante 18 */
  border-radius: 6px;

  /* ② GEOMETRIA: 13px non e' multiplo di 4 e non e' nella scala --s-* */
  padding: 13px;

  /* ③ GEOMETRIA: 3px non e' fra hair (0.5) / base (1) / bold (2).
        E il colore e' la dimostrazione piu' pulita del perche' serve il
        livello 2: #1f6b78 E' esattamente --cy-700. Il livello 1 non lo
        segnalera' mai — calcola a rgb(31,107,120), che sta nella palette.
        Solo leggendo la REGOLA si vede che e' un letterale. L'invariante 18
        dice "zero valori letterali", non "valori che stanno nella palette". */
  border: 3px solid #1f6b78;

  /* ④ COLORE: letterale fuori palette. Il livello 1 lo vede perche' non e'
        un colore di tokens.css; il livello 2 lo vede perche' non e' un var(). */
  color: #00ffcc;
  background: #14202b;

  /* ⑤ COLORE: ombra ESTERNA che SCHIARISCE — e' un alone, cioe' Famiglia B.
        Da confrontare con l'ombra esterna NERA di .jarvis-panel, che scurisce
        ed e' invece ammessa. E' la distinzione decisa sul rilievo R2. */
  box-shadow: 0 0 24px rgba(77, 208, 225, 0.55);

  /* ⑥ TIPOGRAFIA: 17px non e' uno dei cinque gradini --t-* */
  font-size: 17px;
  font-family: "Comic Sans MS", cursive;

  width: 440px;
}
.fx-rotta__ombra {
  /* ⑧ COLORE: un'ombra esterna piu' SCURA del fondo — quindi passa il
        controllo di R2, che chiedeva solo «scurisce» — ma e' BLU.
        L'invariante 19 riformulata (rev 5.13) la vuole nera e senza tinta:
        un'ombra colorata dice da dove viene una luce che non c'e', che e'
        l'errore della Famiglia B fatto al contrario, ed e' una quarta tinta
        contro le tre di §11.6.
        ⚠️ I primi due tentativi — rgba(0,40,90) e rgba(0,20,60) — cadevano sul
        controllo VECCHIO: sono piu' CHIARI di --bg-void, perche' il canale blu
        pesa 0,0722 ma a 60 vale gia' meta' della luminanza del fondo. Un caso
        di prova che non prova la regola per cui e' stato scritto e' peggio di
        nessun caso. Misurato: rgb(0,8,40) sta a L 0,00327 contro lo 0,00668
        del fondo — scurisce — e ha 40 livelli di tinta. */
  box-shadow: 0 20px 40px rgba(0, 8, 40, 0.6);
  background: var(--bg-raised);
  padding: var(--s-2);
}
.fx-rotta__num {
  /* ⑦ TIPOGRAFIA: un numero che non e' in --font-mono */
  font-family: Georgia, serif;
  font-size: 22px;
  color: magenta;
}
`;

export const html = `
<section class="fx-rotta">
  <div>Pannello deliberatamente fuori sistema</div>
  <div class="fx-rotta__num">1284</div>
  <div class="fx-rotta__ombra">ombra portata blu</div>
</section>
`;
