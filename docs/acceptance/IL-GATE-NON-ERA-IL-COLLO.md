# §15 — il pannello news era vuoto, e il gate non c'entrava

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §15 · **Rollback**: `9ea5c96`
**Test**: 1304 verdi (erano 1300) · **Misura**: `docs/acceptance/GATE-DOPO-LO-SCARTO.json`

---

## La catena, e dove stringeva davvero

```
conversazione ──> estrattore ──> gate ──> budget 3/ora ──> card
                     ↑             ↑          ↑
                  strozzava     sospettato   mai binding
```

Il pannello news vuoto è la cosa da cui è partito tutto questo arco. Il
sospetto naturale era il gate, o il budget di §15 — tre interruzioni l'ora
sembrano poche. **Erano entrambi innocenti.**

## La misura, sullo stesso scatto di feed

I due insiemi di argomenti si confrontano sugli **stessi 57 item**, presi in un
solo scatto: confrontarli su due scatti diversi misurerebbe l'ora del giorno.

| | finestre | senza argomenti | news/finestra | **news/ora** |
|---|---|---|---|---|
| **prima** (una battuta per finestra) | 215 | 162 (75 %) | 0,070 | **0,42** |
| **dopo** (battute accumulate) | 45 | 17 (38 %) | 0,222 | **1,33** |

Il tetto di §15 è **3/ora**. Non morde né prima né dopo — e per misurare il
gate senza il budget la misura gira con `max_per_ora=1000`, così ciò che si
vede è quanto il gate lascia passare, non quanto il budget consente.

**Prima della correzione JARVIS produceva una notizia ogni due ore e mezza.**
Non perché il gate fosse severo: perché tre volte su quattro non aveva
argomenti da confrontare, e senza argomenti `un_giro()` non guarda nemmeno i
feed.

## ⚠️ Raggruppare non estrae meglio: smette di buttare via

Va detto perché è il contrario di quello che sembra. Per **frase**, il percorso
a gruppi ha un richiamo più basso (0,450 contro 0,520): haiku su un gruppo
sceglie i temi dominanti e lascia cadere quelli di passaggio. Normalizzando per
frase, la resa è persino leggermente peggiore.

Il guadagno è per **unità di tempo**, e la finestra è di 600 s in entrambi i
casi. Prima quella finestra portava al modello **una battuta su undici**; adesso
le porta tutte. Non è un estrattore migliore — è un estrattore che riceve la
conversazione invece di un campione.

## Che cosa fissano i test, e che cosa no

Il numero dipende da cosa c'è nei feed a quell'ora e **non è riproducibile**:
sta in un JSON registrato, non in una `assert`. I test fissano il
**meccanismo**:

- senza argomenti non passa niente — e non è severità del gate: `un_giro()` non
  guarda nemmeno;
- più argomenti fanno passare più news;
- la rilevanza **non si divide** per il numero di argomenti, quindi una lista
  più lunga non penalizza ogni singola news. Era la prima versione, ed è già
  corretta;
- il budget di 3/ora **non morde**, e se un giorno mordesse il test diventa
  rosso e dice che il collo si è spostato.

L'ultimo è il più utile: è una tripwire sulla diagnosi, non sul numero.

## ❌ NON verificato

- **Un'altra ora del giorno.** Uno scatto, 57 item, due fonti. Alle 3 di notte
  i feed sono altri e il numero è altro.
- **Guardian e YouTube.** Composti dal turno di stamattina, ma senza chiavi non
  contribuiscono: le fonti misurate sono due, non quattro.
- **Una conversazione vera.** Gli argomenti vengono dalle 43 frasi del corpus,
  che non sono frasi sul mondo — sono frasi scritte per il parser T0. È la
  stessa provenienza dichiarata in `ARGOMENTI-IL-BANCO.md`, coi suoi limiti:
  parlando davvero di clima e di governo i numeri sarebbero più alti, e non so
  di quanto.
- **Il percorso completo dal microfono alla card.** Nessun anello di questo
  arco è stato attraversato parlando.
