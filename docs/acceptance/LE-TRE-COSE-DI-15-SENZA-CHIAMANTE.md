# §15 — le tre cose che erano scritte e non collegate

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §15 · **Rollback**: `d5b73ff`
**Test**: 1223 verdi (erano 1201)

---

## Come sono state trovate: una scansione, non una lettura

Il difetto ricorrente di questo progetto ha un nome — «due pezzi scritti,
provati, mai uniti» — e finora l'ho trovato ogni volta per caso. Questa volta
l'ho cercato: uno script su tutto `core/` che, per ogni definizione pubblica,
conta i richiami **fuori dal proprio modulo e fuori dai test**.

**487 definizioni pubbliche, 22 senza chiamanti.** Delle 22, tre erano difetti
veri di §15 e sono chiuse qui; le altre sono callback di libreria
(`on_any_event`), metodi usati per attributo (`R.pianifica`), o classi di
protocollo. L'elenco completo resta nello script, e vale la pena rifarlo
all'inizio di ogni fase.

---

## ① «Non parlarmene più» — la regola che viveva sulla carta

§15 elenca cinque regole «senza cui abbandonerà la funzione in tre giorni».
Quattro avevano una strada. La quinta no: `Gate.silenzia()` esisteva, scriveva
il file markdown, era persistente, ed **era chiamata soltanto dai suoi test**.

### La strada, e perché è una terza allowlist

`esegui_t0` aveva due destinazioni: gli intenti di interfaccia, che finiscono
sul socket, e i tool del registro, che passano dalla conferma. «Non parlarmene
più» non è né l'uno né l'altro — tocca lo stato del gate, che vive nel core.

Nasce `grammar.INTENTI_CORE`, la **terza allowlist**. Non un ramo che lascia
passare il resto: chi aggiunge un intento senza metterlo lì trova il rifiuto di
`esegui_t0`, non un varco.

⚠️ **Il test che sorvegliava le due strade l'ha scoperta da solo.** Aggiungendo
l'intento senza aggiornarlo, `test_le_due_strade_sono_due_allowlist` è diventato
rosso e ha detto esattamente quale intento non aveva destinazione. È il suo
mestiere, e stavolta l'ha fatto prima che me ne accorgessi io.

### Due forme, perché si dice in due modi

**Anaforica** — «non parlarmene più» — chiude ciò di cui si stava parlando:
le parole che hanno fatto passare l'ultima card, calcolate al momento della
pubblicazione. **Esplicita** — «basta parlare di clima» — nomina la cosa.

Se non c'è né l'una né l'altra, **lo dice**: «non ho niente da chiudere, non Le
ho ancora detto nulla». Il silenzio non è un esito.

### Perché NON passa dalla conferma di §6.2 — e la dichiaro

L'invariante 3 esiste per le operazioni irreversibili sui file **di chi usa il
sistema**: mostra il path risolto perché una cancellazione non si annulla.

Qui non si tocca niente dell'utente. Si scrive una preferenza che ha appena
pronunciato, dentro la memoria di JARVIS, e si annulla cancellando una riga da
un file markdown. Chiedere «confermi di voler chiudere l'argomento?» a chi ha
appena detto «non parlarmene più» sarebbe attrito nel punto esatto in cui §15
esiste per toglierlo. **La conferma è la frase.**

Ciò che resta è la responsabilità, e non è negoziabile: **si annuncia a voce e
si scrive nel log**, come i ripieghi dell'invariante 12. C'è un test.

### I pattern sono stretti, e c'è un motivo misurato

«Basta» è fra le parole più comuni della lingua. Una regola larga qui ruberebbe
a T1 frasi come «basta così, grazie» — che è precisamente il guasto silenzioso
che `t0_corpus.py` sorveglia dalla Fase 3. Serve sempre un verbo di parola
(parlare, sentire, dire) o il sostantivo «argomento».

Aggiunte al corpus **5 frasi di comando e 8 contro-esempi**.

⚠️ **I contro-esempi stanno in una lista separata**, `CONVERSAZIONALI_NEWS`, e
la ragione è un vincolo: `eval_argomenti.py` importa `CONVERSAZIONALI`, e
`HAIKU-RISPOSTE.json` congela 215 risposte del modello su quelle 43 frasi,
costate 11,3 USD nozionali. Aggiungerne una lì renderebbe la misura incompleta
e non rifacibile senza rispendere. I test di T0 usano le due liste insieme.

---

## ② Le tre sorgenti di §15 erano una

§15 elenca **RSS, Guardian e YouTube**. La radice di composizione costruiva
`RssCollector()` e basta: `GuardianCollector` e `YouTubeCollector` erano
scritti, provati contro un finto, e senza un chiamante nel core.

Comporli non costa nulla anche senza chiavi — ed è il punto. `disponibile()`
risponde di no, il `Watcher` lo mette fra gli errori del giro e lo **annuncia
una volta** su `agent.advisory`. Prima di oggi la sorgente semplicemente non
esisteva, e «spenta per mancanza di chiave» e «mai costruita» erano
indistinguibili dall'esterno — che è la stessa specie di silenzio contro cui
§15 mette il motivo su ogni scarto del gate.

La chiave arriva **per funzione**: `SettingsStore` ricarica a caldo, e un
collector che l'avesse letta una volta sola resterebbe convinto di non averla
per sempre. Ha un test.

⚠️ **Le chiamate di rete restano non verificate**: nessuna delle due chiavi è
presente su questa macchina. È lo stesso punto 1 dei NON VERIFICATI di Fase 8,
e non si chiude componendo — si chiude con una chiave.

---

## ③ `scarta_doppioni` non era una giunzione mancante: era un duplicato

Lo script l'aveva segnalata come orfana con **zero test**. Prima di collegarla
ho misurato: **tre giri di fila sui feed veri, 2 card, 0 ripetizioni.** Il gate
tiene già `_visti` e risponde «già proposto».

**Cancellata invece che collegata.** Due deduplicatori sono peggio di uno, e il
secondo avrebbe consumato il budget di §15 contando come «viste» notizie che il
gate non ha mai fatto uscire.

È la differenza che lo script da solo non sa fare: un orfano può essere un pezzo
da collegare o un pezzo da togliere, e a deciderlo è la misura.

---

## Verifica

### ✅ Le bocciature

- **Tolto l'esecutore** (`if grammar.INTENTI_CORE` neutralizzato):
  `test_l_intento_ha_un_ESECUTORE` rosso.
- **Allargato il pattern** a `\bbasta\b`: **5 test rossi**, fra cui due del
  corpus T0 — «basta così grazie» rubata a T1, che è esattamente il guasto che
  il corpus sorveglia.

⚠️ Il primo tentativo di questa seconda perturbazione **non ha modificato
nulla**: la sostituzione non ha trovato il pattern e i test sono restati verdi.
Rifatta con un `assert` sulla presenza della stringa prima di sostituire — è la
seconda volta in questo progetto che una perturbazione silenziosamente non si
applica, e la lezione è che anche la bocciatura va verificata.

- Perturbazioni annullate con **copie in scratch**, mai con `git checkout`.

### ✅ La suite

`1223 passed` (erano 1201).

### ❌ NON verificato

- **Il giro vero della frase dal microfono.** «Non parlarmene più» è provata
  come intento e come esecuzione, non pronunciata.
- **Guardian e YouTube dal vivo.** Senza chiavi.
- **Il file `topics/` riletto da un core riavviato davvero.** La persistenza è
  provata costruendo due `Gate` sullo stesso store, non con due processi.
