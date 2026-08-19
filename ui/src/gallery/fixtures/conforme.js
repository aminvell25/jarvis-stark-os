/* Fixture CONFORME — deve essere INVISIBILE all'audit.
 *
 * Non e' un componente reale: la Fase 0b non ne prevede. E' la meta' che
 * dimostra che l'audit non e' un generatore di falsi positivi. Un audit che
 * boccia tutto e' inutile quanto uno che non boccia niente, e senza questa
 * fixture non ci sarebbe modo di distinguere i due casi.
 *
 * Segue l'anatomia a cinque parti di SPEC §10.2:
 *   ① etichetta in caps  ② id/versione  ③ controlli
 *   ④ contenuto          ⑤ piede tecnico
 * con taglio a 45° su UN solo vertice (§10.2, regola dell'asimmetria).
 *
 * I dati sono finti per costruzione ma hanno la FORMA di dati veri, come
 * SPEC §11.9 consente alla sola galleria: lunghezze realistiche, numeri non
 * tondi, timestamp plausibili.
 */

export const meta = { nome: "conforme", versione: "1.0" };

export const css = `
.fx-conforme {
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: calc(var(--grid) * 4);
  background: var(--bg-panel);
  border: var(--line-base) solid var(--cy-900);
  border-radius: var(--radius);
  font-family: var(--font-ui);
  color: var(--txt-primary);
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - var(--s-3)),
                     calc(100% - var(--s-3)) 100%, 0 100%);
}
.fx-conforme__testa {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: var(--s-2);
  border-bottom: var(--line-hair) solid var(--cy-900);
}
.fx-conforme__etichetta {
  font-size: var(--t-label);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--cy-300);
}
.fx-conforme__ver {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-dim);
}
.fx-conforme__corpo { padding: var(--s-3); }
.fx-conforme__riga {
  display: flex;
  justify-content: space-between;
  padding-bottom: var(--s-1);
  font-size: var(--t-data);
}
.fx-conforme__nome { color: var(--txt-dim); }
.fx-conforme__valore { font-family: var(--font-mono); color: var(--cy-500); }
.fx-conforme__valore--critico { color: var(--rust); }

/* I tre riempimenti di STATO della rev 5.9, piu' manila, usati come fondi.
 *
 * E' la meta' che dimostra che l'audit non e' diventato un ostacolo per chi
 * fa la cosa giusta: background: var(--fill-1) deve risultare pulito. Se un
 * giorno smettesse di esserlo, il passo dei 18 componenti si fermerebbe alla
 * prima riga, e la fixture lo dice prima che succeda. La sua opposta e'
 * non-conforme-banda, dove gli stessi fondi sono grigi inventati. */
.fx-conforme__banda { display: grid; grid-template-columns: repeat(3, 1fr); }
.fx-conforme__q {
  padding: var(--s-1);
  font-size: var(--t-micro);
  font-family: var(--font-mono);
  color: var(--txt-primary);
}
.fx-conforme__q--1 { background: var(--fill-1); }
.fx-conforme__q--2 { background: var(--fill-2); }
.fx-conforme__q--3 { background: var(--fill-3); }
.fx-conforme__q--m { background: var(--manila); color: var(--bg-void); }
/* I due token del catalogo (rev 5.14), usati come si deve: un riempimento
   pieno e la sua versione viva. */
.fx-conforme__q--i { background: var(--icona); color: var(--bg-void); }
.fx-conforme__q--iv { background: var(--icona-viva); color: var(--bg-void); }
.fx-conforme__piede {
  padding: var(--s-2);
  border-top: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  color: var(--txt-ghost);
}
`;

export const html = `
<section class="fx-conforme jarvis-panel">
  <header class="fx-conforme__testa">
    <span class="fx-conforme__etichetta">Vettore di prova</span>
    <span class="fx-conforme__ver">A02 · ver 3</span>
  </header>
  <div class="fx-conforme__corpo">
    <div class="fx-conforme__riga">
      <span class="fx-conforme__nome">campione</span>
      <span class="fx-conforme__valore">1 284</span>
    </div>
    <div class="fx-conforme__riga">
      <span class="fx-conforme__nome">deriva</span>
      <span class="fx-conforme__valore">0,0417</span>
    </div>
    <div class="fx-conforme__riga">
      <span class="fx-conforme__nome">soglia</span>
      <span class="fx-conforme__valore fx-conforme__valore--critico">87,3</span>
    </div>
  </div>
  <div class="fx-conforme__banda">
    <span class="fx-conforme__q fx-conforme__q--1">fill 1 · 66</span>
    <span class="fx-conforme__q fx-conforme__q--2">fill 2 · 89</span>
    <span class="fx-conforme__q fx-conforme__q--3">fill 3 · 103</span>
    <span class="fx-conforme__q fx-conforme__q--m">manila · 146</span>
    <span class="fx-conforme__q fx-conforme__q--i">icona · 171</span>
    <span class="fx-conforme__q fx-conforme__q--iv">viva · 219</span>
  </div>
  <footer class="fx-conforme__piede">1920&times;1080 &middot; 04:12:33 &middot; 0x7f2a</footer>
</section>
`;
