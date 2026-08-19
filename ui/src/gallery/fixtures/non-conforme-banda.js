/* Fixture NON CONFORME — la BANDA MEDIA. Deve illuminarsi di magenta.
 *
 * Esiste per una ragione sola, ed e' una ragione nata con la rev 5.8.
 *
 * Aggiungere `--fill-1..3` e `--manila` alla famiglia "colore" dell'audit
 * AMPLIA l'insieme dei colori ammessi. La domanda che segue e': di quanto?
 * Di quattro colori, o di tutta la banda di luminanza in cui stanno?
 *
 * La differenza non e' accademica. Fra L 30 e L 100 ci sono decine di
 * migliaia di grigi, e il modo piu' facile di riempire una superficie e'
 * battere a mano quello che «sta bene»: e' esattamente cio' che l'invariante
 * 18 vieta, ed e' esattamente cio' che il passo dei 18 componenti sara'
 * tentato di fare.
 *
 * Qui dentro ogni fondo e' un grigio inventato in quella banda. Nessuno di
 * essi e' un token. Tutti devono essere segnalati — dal LIVELLO 1 perche' il
 * valore calcolato non e' in palette, e dal LIVELLO 2 perche' e' scritto come
 * letterale invece che come `var()`.
 *
 * ⚠️ L'ultima regola e' il caso piu' insidioso: `#32464f` E' esattamente
 * `--fill-1`. Il livello 1 non la vedra' mai. Se un giorno il livello 2
 * smettesse di funzionare, questa riga resterebbe l'unica a dirlo.
 *
 * Non e' un componente reale ne' un esempio da imitare.
 */

export const meta = { nome: "non-conforme-banda", versione: "1.0" };

export const violazioniAttese = [
  { prop: "background-color", punto: "§11.8 COLORE — grigio inventato a L 50" },
  { prop: "background-color", punto: "§11.8 COLORE — grigio inventato a L 76" },
  { prop: "background-color", punto: "§11.8 COLORE — grigio inventato a L 95" },
  { prop: "background-color", punto: "§11.8 COLORE — letterale uguale a --fill-1" },
];

export const css = `
.fx-banda {
  display: grid;
  gap: var(--s-2);
  padding: var(--s-3);
  width: calc(var(--grid) * 4);
  background: var(--bg-panel);
  border: var(--line-base) solid var(--cy-900);
  font-family: var(--font-ui);
  font-size: var(--t-data);
  color: var(--txt-primary);
}
.fx-banda__cella { padding: var(--s-2); }

/* ① L 50 — sta fra --bg-raised (37) e --fill-1 (66), e non e' nessuno dei due */
.fx-banda__a { background: #29343a; }

/* ② L 76 — sta fra --fill-1 (66) e --fill-2 (89) */
.fx-banda__b { background: #3d4f57; }

/* ③ L 95 — sta fra --fill-2 (89) e --fill-3 (103) */
.fx-banda__c { background: #47656f; }

/* ④ Il caso insidioso: E' --fill-1, battuto a mano. Il livello 1 lo vede
      calcolare a rgb(50,70,79) e lo lascia passare, perche' quel colore ora
      STA nella palette. Solo leggendo la regola si vede che e' un letterale.
      L'invariante 18 dice "zero valori letterali", non "valori che stanno
      nella palette", ed e' qui che la differenza si tocca con mano. */
.fx-banda__d { background: #32464f; }
`;

export const html = `
<section class="fx-banda">
  <div class="fx-banda__cella fx-banda__a">grigio inventato · L 50</div>
  <div class="fx-banda__cella fx-banda__b">grigio inventato · L 76</div>
  <div class="fx-banda__cella fx-banda__c">grigio inventato · L 95</div>
  <div class="fx-banda__cella fx-banda__d">letterale uguale a --fill-1 · L 66</div>
</section>
`;
