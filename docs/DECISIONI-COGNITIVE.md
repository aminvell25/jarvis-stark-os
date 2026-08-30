# Decisioni cognitive — ADR-011, 012, 013

**Scritto il 30 agosto 2026**, verificato contro il repo al commit `29737f2`.

> **Perché esistono.** `docs/STATO-DEI-PIANI.md` §4 elenca tre assenze
> strutturali, verificate in negativo: `grep` su tutto `core/` per
> `correlation_id`, `task_id`, `trace_id`, `Verification` restituisce **zero
> occorrenze**. Sono le uniche tre voci del `Research Pack v3` che si sono
> rivelate vere, e sono anche le tre che nessun documento del progetto aveva
> ancora affrontato.
>
> **Nessuna delle tre introduce una dipendenza, un servizio, un processo o un
> secondo orchestratore.** Sono tre tipi e tre punti di innesto in codice che
> esiste già.

---

## Nota comune — perché NON c'è un «Cognitive Kernel»

Il pacchetto propone `core/cognition/kernel.py` con `handle(event) ->
CognitiveOutcome`. **Non si fa, e la ragione è un invariante.**

`core/engine.py` è la radice unica di composizione. Un `kernel.py` che assembla
contesto, crea task, pianifica ed esegue diventerebbe una **seconda radice**, e
le due divergerebbero al primo che le tocca. Lo dice il pacchetto stesso alla
sua regola 6, e poi propone il file che la viola.

Inoltre l'invariante 17 — «non duplicare la gestione del contesto di T1» — vieta
esattamente la parte più attraente del disegno: uno strato che tiene il proprio
stato conversazionale accanto a quello di Claude Code.

**Quello che serve davvero non è un orchestratore: sono tre contratti.** Un modo
di ricongiungere ciò che accade (011), un modo di distinguere «eseguito» da
«verificato» (012), e un modo per proporre una composizione senza toccare il
DOM (013). Se dopo questi tre un kernel servisse ancora, allora ci sarà
l'evidenza per scriverne l'ADR. Oggi non c'è.

---

# ADR-011 — La traccia: un turno si può ricongiungere

> ### ⚠️ CORRETTO il 30 agosto 2026, prima della prima riga di codice
>
> La prima stesura diceva **sei** punti d'ingresso e ne elencava uno che **non
> esiste**. La sessione di pianificazione l'ha misurato invece di crederci, ed
> è la ragione per cui la correzione arriva prima dell'implementazione e non
> dopo.
>
> **① «Testo dalla scrivania» non esiste.** `core/ws_server.py:315-362` accetta
> cinque tipi di messaggio, provati uno per uno con `model_validate_json` —
> `RuoloMessage`, `ConfirmResponse`, `ImpostazioneMessage`,
> `ArgusCaptureResponse`, `LayoutMessage` — e il commento accanto dice perché:
> *«non un dispatch generico su topic: così un messaggio che non è esattamente
> uno dei due non ha nessuna strada per entrare»*. `app/preload.js` espone
> quattro verbi, e dichiara che restano quattro *«finché qualcuno non dice
> perché ne serve un'altra»*. `esegui_t0()` ha **un** chiamante di produzione,
> e viene dalla voce.
> **L'assenza del testo è una decisione presa, non una dimenticanza**, e
> costruirlo non appartiene a questa fetta. I punti sono **cinque**.
>
> **② Il protocollo non prende una riga di diario.** Vedi la sezione *Dove
> finisce la traccia* qui sotto.
>
> **③ Il parametro su `registry.invoke()` è opzionale, non obbligatorio**, e
> l'imposizione la fa una guardia AST. La frase «la sua assenza è un errore di
> tipo» qui sotto è stata corretta di conseguenza.
>
> Ho scritto i sei punti da un disegno invece che da una misura. È lo stesso
> errore che `docs/ANALISI-PACK-V3.md` documenta, commesso nel documento che lo
> documenta.

## Contesto

`core/diario.py:89` — `annota(flusso, **campi)` — non porta nessun
identificatore. La riga che il turno vocale scrive
(`core/engine.py:783-789`) contiene `intento`, `args`, `ok`, `da`, `strada`,
`errore`. `registry.invoke` (`core/engine.py:811-817`) non ne ha uno.

Conseguenza misurata: dato il diario di una giornata, **non esiste il modo di
rispondere alla domanda «che cosa è successo in quel turno»**. Il wake, la
trascrizione, la classificazione T0, la chiamata al tool e la riga del diario
sono cinque righe che non si toccano.

Questo blocca, in ordine: qualunque misura di comportamento
(`eval_memoria`, `eval_persona`), qualunque verifica end-to-end (ADR-012),
qualunque provenienza di una composizione (ADR-013), e la diagnosi di un turno
andato storto.

**Il pezzo esiste già, e funziona.** `core/tools/confirm.py:71` mette un
`uuid4().hex` su `Piano`, dataclass frozen, e lo propaga in `fs.confirm`
(`:110`), `fs.confirm_expired` (`:144`), `fs.result` (`core/engine.py:860`) e
nei log (`:865`, `:872`). `core/engine.py:322` fa la stessa cosa con `_catture`,
e il commento accanto dice perché: *«senza correlazione due domande vicine si
scambierebbero le risposte»*.

La correlazione nel progetto c'è. È **confinata alle conferme distruttive**.

## Opzioni

**A — Un id esplicito, passato per parametro.**
Ogni punto d'ingresso ne genera uno, e lo passa a valle come argomento.
Costa: firme cambiate in `annota()`, `invoke()`, e nei punti d'ingresso.
Rende visibile chi lo propaga e chi lo perde.

**B — `contextvars`.**
Python propaga automaticamente un `ContextVar` attraverso gli `await` dentro lo
stesso `asyncio.Task`. Zero firme cambiate.
Costa: è **implicito**. Un punto in cui la propagazione si rompe — un
`create_task` senza contesto, un `run_in_executor` — non fa rumore: produce
righe senza id, e nessuno se ne accorge finché non serve la traccia.

**C — Un bus di eventi con envelope.**
Ogni cosa che accade diventa un `Event` con `correlation_id`, `type`,
`payload`, `provenance`, come propone il pacchetto.
Costa: un secondo registro degli eventi accanto al diario, cioè una seconda
fonte di verità. Vietato senza un ADR che lo giustifichi, e non c'è.

## Analisi del compromesso

B è tentante e sarebbe la scelta di quasi tutti. Va scartata **come unica
strada** per la ragione che questo progetto applica ovunque: un difetto
silenzioso è peggiore di un difetto rumoroso. Un id che sparisce a metà catena
senza errore è precisamente il tipo di guasto che `scripts/orfani.py` esiste per
trovare, e che il diario non potrebbe rivelare — perché il diario è la cosa
rotta.

C introduce il difetto che `STATO-DEI-PIANI` documenta su tutto un altro asse:
due fonti che divergono. Il diario è già il registro; non gliene serve un
secondo.

Resta A, con **una** concessione a B che non è un compromesso ma una divisione
di responsabilità:

- **nel dato di dominio** (diario, risultato di tool, layout) l'id è
  **esplicito**, passato per parametro. ⚠️ *Corretto il 30 agosto:* su
  `Diario.annota()` il parametro è **obbligatorio** — cinque chiamanti, tutti in
  `core/engine.py`, e l'assenza è davvero un errore di tipo. Su
  `registry.invoke()` è **opzionale**, perché obbligatorio romperebbe ~60
  chiamate nei test senza aggiungere una sola prova; là l'imposizione la fa una
  **guardia AST** su `core/`, ed è un test, non uno script. Vedi *La guardia, e
  il suo punto cieco*;
- **nei log** l'id arriva da `structlog.contextvars`, perché `structlog` ha già
  quel meccanismo e legare a mano l'id a ottocento chiamate di log sarebbe
  rumore senza guadagno.

## Decisione

Si introduce **`Traccia`**, in `core/traccia.py`:

```python
@dataclass(frozen=True, slots=True)
class Traccia:
    id: str          # uuid4().hex[:12] — corto, leggibile a occhio nel diario
    origine: str     # voce | testo | gesture | protocollo | ui | avvio
    t0: float        # time.monotonic() — per la durata, non per l'ora
```

**Si genera in esattamente cinque punti**, e sono i cinque modi in cui qualcosa
comincia in questo sistema — misurati, non dedotti:

| origine | dove | oggi scrive nel diario? |
|---|---|---|
| `voce` | frase di wake → `esegui_t0()` | ✅ `engine.py:782` e `:1903` |
| `gesture` | `_gesture_intento()` → `emetti()` → `invoke_da_gesture()` | ❌ **niente.** Vedi sotto |
| `protocollo` | `_ronda_di()` → `Ronda.esegui()` | ❌ scrive in `initiatives/`, non nel diario |
| `ui` | uno dei cinque messaggi di `ws_server.py` | ✅ solo `fs.confirm_response`, `engine.py:867` |
| `avvio` | risveglio, resoconto | ✅ `engine.py:1386` |

L'elenco è chiuso e un test lo pinna: **un punto d'ingresso nuovo senza traccia
è un test rosso**, non una svista.

Si propaga per parametro a `Diario.annota()`, a `registry.invoke()`, a
`registry.invoke_da_gesture()` e a `ToolResult`. Si lega ai log con
`structlog.contextvars.bind_contextvars` al punto d'ingresso e si slega alla
fine.

## Dove finisce la traccia — e il buco che c'era già

Una traccia che muore a metà è peggio di nessuna traccia: `jarvis diario
--traccia X` che non trova niente è indistinguibile da «quel turno non è
successo». Quindi ogni origine deve avere **un** record che la porta.

**La gesture non ne ha nessuno.** `core/gestures/mapping.py:221-245`: `emetti()`
invoca il tool, trasmette su `gesture.intent`, scrive una riga di log, e **non
annota**. Oggi un gesto che apre una cartella non lascia niente nel diario. È un
buco che esisteva prima di questo ADR e che questa fetta chiude, con **una riga
nuova**: `annota("azione", da="gesture", …)`.

`FLUSSI = ("dialogo", "azione")` **non si tocca**: `da` è già il campo che nomina
l'origine — `voce`, `conferma`, `risveglio` — e `gesture` è il quarto valore, non
un flusso nuovo.

**Il protocollo, invece, il suo record ce l'ha**, e non gliene va dato un
secondo. `core/engine.py` sopra `_ronda_di` dice perché:

> *«Un'iniziativa solo quando c'è qualcosa da dire. Una ronda che non trova
> niente non è un evento: registrarla riempirebbe `initiatives/` di righe che
> nessuno legge, e il resoconto direbbe ogni giorno che JARVIS ha guardato senza
> dire mai che cosa.»*

Una riga di diario per il protocollo farebbe una delle due cose che quel
commento vieta: duplicare `initiatives/` — seconda fonte di verità — oppure
registrare le ronde vuote. **La traccia va dentro `registra_iniziativa()`**, e
`jarvis diario --traccia X` diventa una join sui due archivi che già esistono.
Un archivio nuovo non serve, e non si fa.

## La guardia, e il suo punto cieco

Con il parametro opzionale su `registry.invoke()`, l'imposizione è una guardia
AST su `core/` — la stessa macchina di `scripts/orfani.py`, 43 KB di scansione
già scritti.

⚠️ **Una guardia che cerca nodi `Call` con `func.attr == "invoke"` è cieca sul
percorso del protocollo**, ed è il difetto più pericoloso di questa fetta:

```
core/engine.py:1844    await self._ronda.esegui(p, registry.invoke, nomi_tool=…)
core/protocolli.py:225 r = await invoca(p.tool, p.args)
```

`registry.invoke` è passato **per riferimento**, non chiamato. La guardia
troverebbe tre chiamate in `core/` (`:744`, `:811`, `:1472`), le direbbe tutte
in regola, e il protocollo resterebbe senza traccia **con la guardia verde**.

È la stessa forma del difetto che `scripts/orfani.py` ha trovato in
`riavvia_dopo_guasto`: lo strumento diceva ok perché guardava dalla parte
sbagliata.

Tre requisiti, quindi, e vanno nel piano:

1. la guardia segnala `registry.invoke` e `registry.invoke_da_gesture` anche
   **in posizione non-Call** — passati come valore;
2. `Ronda.esegui()` prende la traccia e la passa a `invoca`, così il percorso
   del protocollo non è un'eccezione silenziosa;
3. la guardia copre **entrambe** le porte del registry: `invoke` e
   `invoke_da_gesture`. Una porta sola coperta è una porta sola coperta.

**`Traccia` non è un task e non è un contesto.** Non porta stato, non porta
storia, non porta obiettivi. È un identificatore e la sua origine. L'invariante
17 resta intatto perché non c'è niente da duplicare.

## Conseguenze

- Il diario diventa **ricongiungibile**: `jarvis diario --traccia abc123def456`
  restituisce le righe di un turno in ordine.
- `scripts/orfani.py` guadagna una classe di controllo nuova: una riga di diario
  senza traccia è un orfano.
- Il campo è **additivo**: le righe vecchie non ce l'hanno, e un lettore che non
  lo trova non deve rompersi. Va scritto e pinnato.
- Costo in contesto per T1: **zero**. La traccia non entra mai nel prompt.

## Alternative rifiutate

| | perché no |
|---|---|
| solo `contextvars` | la perdita di propagazione è silenziosa, e il diario è la cosa che non funzionerebbe |
| bus di eventi / `Event` envelope | seconda fonte di verità accanto al diario |
| id lungo (uuid completo) | il diario si legge a occhio; 12 caratteri esadecimali bastano per una giornata e non sfondano la riga |
| id derivato dal timestamp | due turni nello stesso millisecondo collidono, e l'ora di sistema può saltare all'indietro |
| parametro **obbligatorio** su `registry.invoke()` | romperebbe ~60 chiamate nei test — `eval_tools`, `test_confirm_e2e`, `test_registry`, `eval_mcp` — e nessuna di quelle modifiche aggiungerebbe una prova. Il costo è reale, il guadagno no |
| costruire un punto d'ingresso «testo dalla scrivania» per far tornare i sei | inventare una superficie per far tornare un documento. Il documento si corregge |

## Criterio di accettazione

1. Una frase detta al microfono produce **N righe di diario che portano tutte lo
   stesso `traccia_id`**, dal `wake_trigger` alla riga del tool.
2. Uno script ricostruisce il turno dai due archivi — `diario/` e
   `initiatives/` — e lo stampa in ordine.
   > ⚠️ *Corretto il 30 agosto, in corso d'opera:* qui c'era scritto
   > `sessions/`, e nominava l'archivio sbagliato. `sessions/` è la **cronologia
   > grezza** che alimenta il consolidamento notturno di §5.5; il registro di
   > osservazione è il **diario**, ed è quello che le altre quattro occorrenze di
   > questo ADR nominano — la sezione *Decisione* propaga a `Diario.annota()` e
   > non a `registra_turno()`, *Dove finisce la traccia* dice diario +
   > `initiatives/`, *Conseguenze* dice «il **diario** diventa ricongiungibile»,
   > e `CLAUDE.md` invariante 31 elenca «diario, `registry.invoke`,
   > `registry.invoke_da_gesture` e `ToolResult`». `registra_turno()` non è stato
   > toccato.
3. **Un gesto lascia una riga di diario**, e oggi non ne lascia nessuna.
4. **Una ronda di protocollo che cambia qualcosa porta la traccia nel record di
   `initiatives/`** — e una ronda che non cambia niente continua a non scrivere
   niente.
5. Un punto d'ingresso aggiunto senza traccia fa **fallire** un test.
6. **La guardia AST boccia `registry.invoke` passato per riferimento.** Provalo:
   togli la traccia da `Ronda.esegui` e verifica che diventi rossa. Se resta
   verde, la guardia non stava guardando.
7. Le righe di diario scritte prima di questo ADR si leggono ancora.
8. `uv run pytest -q` verde.

## Rollback

`e587a82` — l'ultimo commit prima della fetta. Il campo è additivo: togliere
`core/traccia.py` e i suoi chiamanti non invalida nessun dato scritto, e le
righe già sulla carta restano leggibili in entrambe le direzioni (misurato su 61
righe vere, `docs/acceptance/LA-TRACCIA-NON-SI-PERDE.md` §⑦).

---

# ADR-012 — «Eseguito» non è «verificato»

> ### ⚠️ CORRETTO il 30 agosto 2026, prima della prima riga di codice
>
> Quattro rilievi, tutti misurati contro il codice.
>
> **① `Esito` → `Verdetto`.** In `core/` `Esito` è già il nome di **tre** classi
> diverse — `core/protocolli.py:101`, `core/tools/confirm.py:83`,
> `core/news/collectors/base.py:76` — e `scripts/orfani.py` conta gli
> `ast.Attribute` **per nome**, con 52 nomi pubblici già definiti da due o più
> moduli. Un quarto omonimo avrebbe spostato il rinominare sui chiamanti invece
> che sulla definizione.
>
> **② Sei valori → quattro.** `ANNULLATO` e `DEGRADATO` non li emette nessuno:
> niente annulla un tool (la conferma è rifiutata o scaduta, e sono entrambe un
> blocco) e il ripiego dell'invariante 12 riguarda la **voce**, che non è un
> tool. Stessa regola applicata a `Origine` nella fetta 1.
>
> **③ Il verificatore prende il PIANO**, non solo `(args, ToolResult)`. Tutti e
> tre i tool nominati qui sotto sono `side_effect=True` e i loro percorsi
> **risolti** vivono nel piano congelato. Un verificatore che risolvesse di
> nuovo `a.path` rifarebbe ciò che §6.2 esiste per impedire — un symlink
> cambiato fra la conferma e l'esecuzione — e guarderebbe un percorso diverso da
> quello toccato, **con l'aria di aver verificato**.
>
> **④ `fs.write` e `fs.trash` non esistono**: i tool si chiamano `create_file` e
> `trash_path`. `fs.*` è lo spazio dei *topic* di §6.2, non quello dei tool.
>
> E il criterio 3 è passato da «rifiutato in revisione» a **imposto dal
> registro**: `registry._verifica` declassa a `NON_VERIFICATO` un verificatore
> la cui `fonte` nomina il proprio tool. Una regola affidata alla disciplina
> regge finché qualcuno ha fretta.
>
> Esito per criterio in `docs/acceptance/ESEGUITO-NON-E-VERIFICATO.md`.

## Contesto

`ToolResult(ok=True)` oggi significa: *la chiamata non ha sollevato
un'eccezione*. Non significa che il file sia sul disco, che l'impostazione abbia
avuto effetto, che il cestino contenga ciò che doveva contenere.

Per la maggior parte dei tool la differenza è teorica. Per tre categorie non lo
è: quelli con `side_effect=True`, quelli che passano da un processo esterno, e
quelli che il giorno in cui JARVIS agirà da solo saranno l'unica cosa che
distingue un'azione riuscita da una raccontata.

**Il pattern esiste già in tre punti, ed è la prova che il progetto ci era
arrivato per conto suo:**

| dove | che cosa fa | che cosa manca |
|---|---|---|
| `core/engine.py:563` | tiene `wake_model` (vivo) accanto a `wake_model_chiesto` (atteso). `SPEC.md` rev 5.42: *«la divergenza vale `fail`»* | vale per **un campo** |
| `core/doctor.py`, §16.1b | `ok` / `WARN` / `fail` per sottosistema | vale per **sottosistemi**, non per azioni |
| `core/protocolli.py:101` | `Esito(nome, eseguito, cambiato, frase, errore)` + `firma()` | confronta osservato con osservato-**di-prima**. Non c'è un *atteso* |
| `core/tools/files.py` `_trash` | cerca dove è finito il file e riferisce `verificato: bool` | ⚠️ *aggiunto il 30 agosto:* **e poi restituisce `ok=True` comunque**. Il quarto esempio, e il più istruttivo: il campo c'era, era corretto, e non cambiava niente. Un'osservazione che non ha effetto non è una verifica |

E vive come **prosa umana** nelle intestazioni `**Criterio:** / **Esito:**` di
`docs/acceptance/`, che `SPEC.md:2480` rende obbligatorie: *«Se non puoi
verificare un criterio, lo DICHIARI. Non lo dai per buono.»*

**Questo ADR fa una cosa sola: prende quella frase — che oggi vale per una
persona che scrive un documento — e la rende vera per il codice a runtime.**

## Il difetto sottile, e va detto prima della decisione

Un verificatore che rilegge ciò che il tool ha appena scritto **attraverso lo
stesso codice** non prova niente: prova che il codice è coerente con sé stesso.
Se `fs.write` scrive tramite un percorso sbagliato e `verifica_fs_write` legge
tramite lo stesso percorso sbagliato, il verde è una bugia con due firme.

Quindi: **il verificatore usa una fonte indipendente dove esiste**, e dove non
esiste lo **dichiara** restituendo `non_verificabile` invece di inventarsi una
prova. Un verificatore debole dichiarato vale più di un verificatore forte
finto.

## Decisione

Due tipi, in `core/verifica.py`:

```python
class Esito(StrEnum):
    RIUSCITO       = "riuscito"        # atteso e osservato coincidono
    FALLITO        = "fallito"         # divergono
    BLOCCATO       = "bloccato"        # l'utente ha detto no, o il governor
    ANNULLATO      = "annullato"
    DEGRADATO      = "degradato"       # fatto, ma per una strada di ripiego
    NON_VERIFICATO = "non_verificato"  # nessuna fonte per saperlo

@dataclass(frozen=True, slots=True)
class Verifica:
    atteso: str
    osservato: str
    esito: Esito
    fonte: str          # da dove viene l'osservazione. Mai "il tool stesso"
    quando: float
    traccia_id: str     # ADR-011
```

**La regola che rende l'ADR non decorativo:** un tool **senza** verificatore
dichiarato restituisce `NON_VERIFICATO`, **non** `RIUSCITO`.

`NON_VERIFICATO` non è un fallimento e non è un successo. È l'unico esito
onesto quando non si sa, e la sua esistenza è tutto il valore di questo
documento: senza di esso, «non lo so» collassa su «sì» e JARVIS comincia a
raccontare.

Innesto: nel **registry**, non nell'engine e non nel kernel-che-non-c'è.
`Tool` guadagna un campo opzionale `verifica: Callable[[args, ToolResult],
Verifica] | None`. `registry.invoke` lo esegue dopo la chiamata e allega
l'esito.

## Migrazione — tre tool, non tutti

Si comincia dai tre che hanno un osservabile a costo quasi zero e una fonte
indipendente vera:

| tool | atteso | fonte indipendente |
|---|---|---|
| `fs.write` | il file esiste, dimensione e mtime attesi | `os.stat` sul percorso risolto — non il buffer scritto |
| `imposta_valore` | il TOML riletto dal disco contiene il valore, **e i commenti ci sono ancora** | rilettura con `tomlkit`, confronto del testo |
| `fs.trash` | l'origine non c'è più **e** la destinazione nel cestino c'è | i due `os.path.exists`, entrambi |

Il resto dei tool resta `NON_VERIFICATO` finché qualcuno non gli scrive un
verificatore. È lo stato corretto, non un debito nascosto: `jarvis doctor` può
dire quanti tool sono verificabili e quanti no, e quel numero è una misura.

## Rapporto con l'invariante 3

**La verifica non sostituisce mai la conferma.** La conferma sta *prima*
dell'azione e la autorizza un umano; la verifica sta *dopo* e la fa la macchina.
Un tool `side_effect=True` continua a richiedere la conferma col percorso
risolto, verificatore o no. Chi legge questo ADR come «adesso che verifichiamo
possiamo confermare meno» lo ha letto al contrario.

## Criterio di accettazione

1. Un'azione di tool finisce in **`NON_VERIFICATO`** invece che in un
   `ok=True` falso — e si vede nel diario, con la sua traccia.
2. Rompendo di proposito il verificatore di `fs.write` (per esempio facendogli
   guardare il percorso sbagliato) un test diventa **rosso**. Se non diventa
   rosso, il verificatore non stava verificando.
3. Un verificatore che rilegge attraverso il tool stesso viene **rifiutato in
   revisione**: il campo `fonte` deve nominare qualcosa di diverso dal tool.
4. `jarvis doctor` riporta quanti tool hanno un verificatore.
5. `uv run pytest -q` verde.

## Rollback

`f3f06ed` — l'ultimo commit prima della fetta. Campo opzionale sul `Tool`, tipo
nuovo in un file nuovo. Si toglie senza toccare nessun chiamante che non lo usi.

---

# ADR-013 — LayoutIntent: l'LLM propone, il compositore dispone

## Contesto

`core/layout.py` — 24 KB — contiene già, scritto e collaudato:

| pezzo | riga | che cos'è |
|---|---|---|
| `Layout`, `GeometriaPannello`, `IconaLibera`, `CartellaLibera` | `:69-255` | schema pydantic **stretto** (`extra=forbid`), con validatori che rifiutano percorsi nei nomi e caratteri di controllo |
| `adatta()` | `:256` | riporta dentro l'area ciò che ne è uscito. **Non scarta** |
| `LayoutStore._metti_da_parte()` | `:378` | il file illeggibile viene rinominato e si riparte pulito, **dicendolo** |
| `LayoutStore._scrivi()` | `:454` | scrittura atomica, temporaneo più `os.replace()` |
| `LayoutMessage` | `:485` | il terzo tipo in ingresso, quello che il renderer inizia |

Il pacchetto v3 §09 chiede sette proprietà per un layout engine: schema
validation, allowed component registry, size limits, overlap rules,
deterministic fallback, provenance, rollback. **Quattro sono già lì, scritte
meglio di come le descrive il documento.**

Manca una cosa sola, e non è un motore: manca il modo di **proporre** una
composizione. Oggi `Layout` registra ciò che l'utente ha fatto con le mani. Non
esiste niente che possa dire «per questo compito servono questi pannelli».

## Il rischio, dichiarato per primo

Un LLM che emette geometria è un LLM che disegna. Un LLM che emette geometria
*valida* è un LLM che disegna e non se ne accorge. La riga che separa questo
progetto da una demo è che **l'LLM non nomina mai un pixel**.

E c'è un secondo rischio meno ovvio: una composizione che si muove da sola è
una composizione che sposta le cose sotto le dita dell'utente. La prima regola
sotto esiste per quello.

## Decisione

Si introduce **`LayoutIntent`** in `core/layout.py` — nello stesso file, perché
un secondo file sarebbe un secondo proprietario del layout:

```python
class LayoutIntent(_Stretto):
    superficie: str                  # nome della composizione, da un elenco chiuso
    traccia_id: str                  # ADR-011 — CHI l'ha causata
    pannelli_richiesti: list[str]    # nomi dal registry dei pannelli. Allowlist
    pannelli_secondari: list[str] = []
    priorita: Literal["eroe", "affiancato", "sfondo"] = "affiancato"
```

E il compilatore, deterministico:

```python
def componi(intent: LayoutIntent, area: Area, corrente: Layout) -> Layout
```

**Cinque regole, e quattro sono divieti.**

1. **La composizione manuale vince sempre.** Un pannello che l'utente ha mosso,
   ridimensionato o fissato non si tocca. `componi` lavora sullo spazio
   rimasto, e se non ne resta abbastanza **non compone**: lo dichiara.
2. **I nomi vengono dal registry dei pannelli** — invariante 2 applicata al
   layout. Un nome sconosciuto non è un pannello vuoto: è un intent rifiutato.
3. **L'intent non contiene geometria.** Niente `x`, `y`, `larghezza`, `z`.
   Se un giorno un modello ne emettesse, lo schema stretto lo rifiuta prima di
   guardarlo.
4. **Un intent rifiutato non muove un pixel** e produce un advisory dichiarato.
   Il layout precedente resta esattamente dov'era: è la stessa proprietà che
   `_metti_da_parte()` ha già per il file corrotto.
5. **Ogni composizione registra da dove viene**: `superficie` e `traccia_id`
   finiscono nel `Layout` salvato e nel diario. Senza ADR-011 questa regola non
   si può scrivere — ed è la ragione dell'ordine.

## Prima fetta: intent scritti a mano, non generati

Nella prima fetta gli intent sono **dichiarati in codice**, un elenco fisso di
tre o quattro superfici (`analisi-progetto`, `diagnostica`, `memoria`).
**Nessun LLM li tocca.**

La ragione è misurabile: il compilatore va provato contro un input che si
controlla, prima di provarlo contro un input che si negozia. Se `componi` ha un
difetto, lo si vuole trovare con un intent scritto a mano, non dedurlo da una
composizione strana la notte in cui T1 ne ha emesso uno.

Quando `componi` sarà verde su intent fissi, **allora** si scrive l'ADR che
decide chi li genera (T1? T2? T0 non può, invariante 14) e con quale grammatica.
Quel documento oggi non si può scrivere onestamente.

## Fuori perimetro — dichiarato

**Multi-monitor.** Il pacchetto lo chiama «first-class architectural
requirement». Non è in SPEC, non è in nessun ADR, e ADR-005 dice che JARVIS è
un'applicazione a schermo intero. `Area` resta un rettangolo.

Non è un rifiuto: è che **non c'è nessuna evidenza che lo richieda**, e
`ANALISI-SENIOR` §4.6③ misura questo esatto tipo di allargamento come il primo
rischio di allocazione del progetto. Se un giorno servirà, sarà un ADR suo — e
`componi(intent, area, corrente)` prende già l'area per parametro, quindi la
strada resta aperta senza costare niente oggi.

**Codice auto-modificante.** Il pacchetto lo tiene come «strategic objective».
`CLAUDE.md`, *Non fare senza chiedere*: «Eseguire stringhe generate dall'LLM».
Resta fuori. Un layout compilato da uno schema chiuso **non è** codice generato,
ed è precisamente per questo che è ammissibile.

## Criterio di accettazione

1. Un `LayoutIntent` valido con tre pannelli produce un `Layout` che li mostra,
   e la scrivania ci arriva senza che il renderer abbia scritto niente.
2. Un intent con un nome di pannello inesistente **non muove un pixel** e
   produce un advisory.
3. Un pannello che l'utente ha mosso a mano resta dov'era dopo `componi`.
4. Il `Layout` salvato porta `superficie` e `traccia_id`, e il diario ha la riga
   corrispondente con la stessa traccia.
5. L'utente può tornare alla composizione precedente.
6. Ciclo §11.7 eseguito sulla composizione risultante, checklist §11.8 riportata
   punto per punto.
7. `uv run pytest -q` verde.

## Rollback

`LayoutIntent` e `componi` sono additivi: `Layout`, `adatta` e `LayoutStore` non
cambiano firma. Togliendoli, la scrivania torna a essere solo manuale.

---

## Ordine, e perché è questo

```
ADR-011  →  ADR-012  →  ADR-013
traccia     verifica     composizione
```

011 per primo perché **012 e 013 lo citano entrambi nei propri tipi**: una
verifica che non si ritrova non serve a niente, e una composizione senza
provenienza è una composizione che nessuno può spiegare.

012 prima di 013 perché è quello che protegge dal difetto peggiore — JARVIS che
dichiara un successo che non ha provato — e perché 013 produce una superficie
visibile, cioè il tipo di lavoro che si mangia le giornate
(`ANALISI-SENIOR` §4.6①).

Se una sola delle tre si può fare: **011**.
