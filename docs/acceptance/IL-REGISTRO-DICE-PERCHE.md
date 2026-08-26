# Il primo comando detto davvero, e il registro che taceva

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.6, §5.7
**Rollback**: `2768263` · **Test**: 1412 → **1441**

---

## Come è emerso

Non da un test. Dal **diario**, il giorno stesso in cui è stato acceso.

Il Signore ha aperto l'app e ha detto **«apriti i pannelli telemetria»**. JARVIS
ha risposto:

> *«Vedo, Signore. Mi occupo del caricamento della telemetria.»*

E non è successo niente. Nel registro: **otto righe di `dialogo`, zero di
`azione`**. Per sapere se T0 avesse anche solo *visto* quella frase ho dovuto
eseguire il parser a mano — che è la misura di quanto il registro fosse muto.

---

## Una lettura mia, sbagliata, corretta prima di agire

Ho pensato che T1 avesse mentito: dichiara un'azione che per l'invariante 15
non può compiere. **È falso.** `config/voice-persona.md` riga 41 prescrive
esattamente quelle parole:

> *«Se ti chiede un'azione confermi di aver SENTITO, non che sia compiuta:
> "Vedo, Signore." "Me ne occupo." Mai "Fatto": non puoi verificarlo.»*

T1 ha obbedito alla lettera. La riga falsa è quella **sopra**:

> *«Non hai strumenti… Quelle azioni le fa il sistema prima di arrivare a te.»*

`pipeline.py` fa `if intent is not None: … return`. **T1 è raggiunto soltanto
quando T0 ha mancato** — cioè la premessa della persona è vera nel caso che non
capita mai, e falsa nell'unico caso in cui T1 viene usato.

⚠️ **Non l'ho riscritta.** Quel testo è Suo, e la frase giusta è una scelta di
carattere, non una correzione. La riporto e resta aperta.

---

## ① L'imperativo con il pronome attaccato

In italiano l'imperativo prende l'**enclitico**: apri/aprimi/aprila/apriti,
mostra/mostrami, chiudi/chiudilo. È la forma normale del parlato, e la
grammatica conosceva solo la nuda. In più il plurale «pannelli» non era ammesso
dove lo era «pannello» — la stessa asimmetria già corretta una volta fra
`open_panel` e `close_panel`.

**La sicurezza non viene dalla prudenza, viene dall'allowlist.** `t0_corpus.py`
tiene già «apriti cielo» e «mostrati un po' più paziente» fra le frasi da NON
rubare: restano salve perché `cielo` non è un pannello. È la stessa allowlist
che chiuse il furto di «chiudi un occhio stavolta».

**Limite dichiarato**: l'estensione si applica **solo** dove l'oggetto è
un'allowlist. Davanti alla coda di `search_files` o alla query di YouTube un
pronome in più diventa una query — ed è il difetto che quella regola ha già
avuto.

| | prima | dopo |
|---|---|---|
| «apriti i pannelli telemetria» | `None` | `open_panel {telemetria}` |
| «aprimi la telemetria» | `None` | `open_panel {telemetria}` |
| «apri i pannelli telemetria» | `None` | `open_panel {telemetria}` |
| conversazionali rubate (su 53) | **0** | **0** |
| corpus T0 | 157 verdi | 157 verdi |

## ② Il registro non sapeva dire perché non era successo niente

`esegui_t0` annotava già ciò che la grammatica riconosce. Mancava l'altra metà:
la **delega** a T1, e la **caduta** quando T1 non c'è. Ogni enunciato produce
adesso una riga con la strada che ha preso — `t0`, `t1`, `nessuna` — e, quando
non è stato riconosciuto, il testo che non ha trovato un comando.

Il testo sta nel flusso `azione` e non solo in `dialogo` di proposito: è
l'ingresso da cui si ripara la grammatica, e un registro che costringe a
incrociare due flussi per la domanda più frequente non è un registro.

**E `strada` non si deriva da `azione`**: `azione is None` non distingue
«delegato» da «caduto», ed è esattamente quella la differenza da leggere.

⚠️ **La caduta silenziosa che è stata trovata scrivendo questo.** Voce accesa,
T0 che non riconosce, T1 che non è partito: `if self._t1 is None: return`.
JARVIS taceva e **il diario non aveva la riga per dirlo**.

## ③ Il quasi-comando, e il numero che ha deciso di non dirlo

`quasi_comando()` etichetta una frase che **comincia** con un imperativo noto e
che `parse()` non ha riconosciuto. Serve a sapere quali comandi mancano senza
doverli immaginare — come `conso/` per il rate limit: la correzione che rende
misurabile la successiva.

Volevo anche **dirlo a T1**, così che smettesse di rispondere «Me ne occupo» a
un'azione che nessuno compirà. Misurato prima di scriverlo, sulle 53 frasi
conversazionali che il corpus già conteneva:

```
falsi positivi: 8 / 53 = 15,1 %
   «apriti cielo» · «chiudi un occhio stavolta» · «nascondi la delusione»
   «apri bene le orecchie» · «mostra un po' di pazienza» · …
```

**Una frase su sette** porterebbe a JARVIS un «nessun comando riconosciuto» in
mezzo a un discorso. In un registro un falso positivo si vede e non costa
niente; in bocca a JARVIS diventa un tic. **Decisione: si registra, non si
dice.** Il numero è in un test: se qualcuno allarga la tupla dei verbi, il test
lo dice invece di lasciare il commento a mentire.

---

## Verifica

### ✅ Le sei bocciature

| perturbazione | esito |
|---|---|
| via gli enclitici da `_imp()` | 7 rossi |
| torna il solo `pannello` singolare | 2 rossi |
| un verbo che nessuna regola contiene | 2 rossi |
| il motore non chiama più `_annota_instradamento` | 1 rosso |
| la caduta torna a non emettere un turno | 1 rosso |
| il quasi-comando entra nella nota a T1 | 1 rosso |

Perturbate in copia, ripristinate confrontando i byte: i tre file sono
identici agli originali.

### ✅ La suite

`1412 → 1441`, verde. Corpus T0: 157 verdi, zero frasi rubate prima e dopo.

### ✅ Il ponte, seconda conferma

Riavviando il core per rendere viva la correzione, `client_connesso` è tornato
nello stesso secondo — la riconnessione della scrivania si è ripetuta.

### ❌ NON verificato

- **La frase vera, ridetta al microfono.** «Apriti i pannelli telemetria» ora
  *si analizza* come `open_panel`, e il core gira con la correzione: che il
  pannello si apra davvero quando lo dice una voce non l'ha ancora visto
  nessuno. È **non misurabile** finché non lo dice.
- **La riga di instradamento nel diario vivo.** Provata in comportamento sui
  finti, non ancora osservata su un enunciato reale.
- **La premessa invertita della persona** resta aperta: riportata, non
  emendata.
