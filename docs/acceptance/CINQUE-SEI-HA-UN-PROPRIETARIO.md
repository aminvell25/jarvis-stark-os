# §5.6 — la scadenza del token aveva due gestori, e quello che riferisce era muto

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.6, §16 · **Rollback**: `be0ce40`
**Test**: 1300 verdi (erano 1288)

---

## Il difetto, e perché era peggio di una duplicazione

`Supervisore.su_evento()` **non aveva chiamanti**. Né T1 né i due T2 gli
passavano un solo evento dello stream. Eppure è lui che:

- annuncia a voce con una voce che **non dipende da Claude** (§5.6 lo impone
  esplicitamente: se l'annuncio passasse dal modello sarebbe la prima cosa a
  non funzionare proprio quando serve);
- pubblica l'`agent.advisory`;
- fa uscire il core col codice **41**, che `RestartPreventExitStatus` nella
  unit systemd riconosce;
- risponde a `jarvis doctor` con `stato_doctor()`.

Nel frattempo T1 aveva un ramo tutto suo — una ricerca per sottostringa,
`"authentication" in json.dumps(e).lower()` — che degradava e annunciava per
conto proprio.

**Il risultato peggiore non è la duplicazione.** È che:

1. `jarvis doctor` avrebbe detto **`auth ok`** con T1 già degradato, perché il
   supervisore non lo sapeva. Lo stato riferito e lo stato vero erano due cose
   diverse — e §16.1b esiste proprio per rispondere a «cosa è rotto».
2. Il core **non sarebbe uscito col codice 41**, quindi systemd lo avrebbe
   rilanciato contro il muro: esattamente il «riavvio a ciclo» che §5.6 vieta.

---

## La cura: un proprietario, e gli altri delegano

§5.6 ha **un** proprietario, ed è il `Supervisore`. T1 e i due T2 gli passano
gli eventi `system/api_retry`; quando lui dice di aver gestito, **T1 si ferma e
tace** — annunciare due volte sarebbe due metà in disaccordo.

Il ripiego per sottostringa in T1 **resta**, e non è una svista: i test
costruiscono T1 da solo, senza supervisore, e un T1 che ignorasse un token
scaduto riproverebbe a ciclo. Ma viene **dopo** la delega, e c'è un test che lo
impone.

Per T2 la riga sta accanto a `Governor.osserva(e)`: sono due domande diverse
sullo stesso flusso — il rate limit e l'autenticazione — e finora la seconda non
la faceva nessuno.

---

## Un difetto d'ordine, trovato da un test che era già lì

Costruire il T2 dei meta-comandi accanto al `Governor` — dove sembrava
naturale — dava `AttributeError: 'Engine' object has no attribute
'_supervisore'` al primo avvio, perché il supervisore nasce venti righe più
sotto.

L'ha trovato `test_costruire_due_volte_non_esplode`, che è lì per questo. La
costruzione è stata spostata dopo il supervisore, con una riga che dice che
l'ordine non è estetico.

---

## Verifica

### ✅ Le bocciature

| perturbazione | esito |
|---|---|
| T1 non passa gli eventi al supervisore | 2 rossi |
| T1 chiama il supervisore ma **non si ferma** | 1 rosso — **dopo aver riscritto il test** |

⚠️ **La seconda non discriminava.** Il test guardava solo l'**ordine** — che
`su_evento` venisse prima del ripiego per sottostringa — e togliendo il corto
circuito l'ordine restava giusto: T1 avrebbe chiamato il supervisore *e poi*
sarebbe caduto anche nel proprio ramo, annunciando due volte. Riscritto per
imporre ciò che conta: che ci sia un `return` fra la delega e il ripiego.

> **Quinta occorrenza in questo arco** di «criterio vero per il motivo
> sbagliato» (§11.7 regola 4). Tutte trovate eseguendo la bocciatura, nessuna
> rileggendo.

### ✅ La suite

`1300 passed` (erano 1288).

### ❌ NON verificato

- **Una scadenza vera.** È lo stesso punto 2 dei NON VERIFICATI di Fase 9: il
  supervisore è provato con l'evento iniettato e la unit col codice reale; un
  OAuth che scade davvero, no.
- **Il giro dentro lo stream di T1.** La delega è provata chiamando
  `t1._su_evento` e leggendo il ramo del sorgente; far arrivare un
  `api_retry` vero richiede un processo `claude` che lo produca.
- **L'uscita 41 osservata da systemd.** Il codice è verificato come valore, e
  la unit lo dichiara; nessun servizio è uscito così in questo turno.
