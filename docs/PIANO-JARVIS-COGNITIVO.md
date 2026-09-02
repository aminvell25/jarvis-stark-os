# Piano — da scrivania a JARVIS · rev 2

**Riscritto il 30 agosto 2026**, verificato contro il repo al commit `29737f2`,
non dedotto dai documenti.

> **Che cosa è successo alla rev 1.** La rev 1 (25 agosto) ordinava cinque voci.
> **Sono chiuse tutte e cinque**, e con loro le altre due dell'ordine di lavoro
> di `STATO-DEI-PIANI`. Sette su sette. La rev 1 non è stata superata: è stata
> **esaurita**, ed è la ragione per cui questa rev esiste.
>
> Il progetto è arrivato al punto in cui il piano vecchio è finito e quello
> nuovo non c'era. È in quel vuoto che è entrato il `Research Pack v3`, ed è
> il motivo per cui sembrava necessario.

---

## 0. Tre vincoli, dichiarati prima di cominciare

### ① Nessuna libreria nuova, nessun framework, nessun runtime di agente

Vale per l'animazione (invariante 9), per il 3D (invariante 10) e — questa è
nuova — per la **memoria e l'orchestrazione**.

Letta, Mem0, Zep, MemOS, Cognee, LangGraph: sono runtime di agente.
Porterebbero un secondo orchestratore accanto a Claude Code, contro gli
invarianti 11 e 17, e due dei tre richiedono Neo4j o Qdrant. MemoryOS è
misurato a **32,4 s** di latenza totale di retrieval. E i numeri dei vendor non
si riproducono: Mem0 dichiara 94,4 su LongMemEval e viene misurato **49,0–73,8**
da terzi.

**Si prendono i pattern, non i pacchetti.** Tutte le fette qui sotto sono
scritte con la libreria standard, `pydantic` e `structlog`, che ci sono già.

### ② Una fetta verticale per volta, chiusa e misurata

È il ritmo che ha portato entropia, dock, ritaglio, orologi, ADR-003, ADR-004,
ADR-007, voce e impostazioni da aperti a chiusi in undici giorni. Non si cambia
perché è arrivato un piano nuovo.

Una fetta è chiusa quando i quattro punti della *definizione di fatto* di
`CLAUDE.md` sono verdi. **Nessuna fetta comincia prima che la precedente sia
chiusa**, e nessuna anticipa la successiva.

### ③ Le stime qui sotto non sono misure

Sono ordini di grandezza a mezze giornate, e vanno lette con il rilievo di
`ANALISI-SENIOR` §4.6③ accanto: la stima complessiva del progetto è ottimistica
di un fattore **3–5**, e il collo di bottiglia non è scrivere codice — è
verificare, integrare e mantenere. Se una fetta sfora del doppio, **non è la
fetta che è sbagliata: è la stima**, e si aggiorna qui invece di accelerare.

---

## 1. L'ordine, e perché è questo

| | fetta | chiude | dipende da | stima |
|---|---|---|---|---|
| **1** | **La traccia** | ADR-011 | — | 1 g |
| **2** | **Il contratto di verifica** | ADR-012 | 1 | 1,5 g |
| **3** | **L'attribuzione in memoria** | `ANALISI-SENIOR` §4.1④ | — | 0,5 g |
| **4** | **Il termometro** — `eval_memoria`, `eval_persona` | §4.1③⑤, §7④ | 1 | 2 g |
| **5** | **LayoutIntent** | ADR-013 | 1, 2 | 2,5 g |
| **6** | **Le strutture nelle impostazioni** | residuo §26.7 | — | 1 g |

Totale dichiarato: **~8,5 giornate**. Con il fattore di §0③: **realisticamente
tre settimane**, e lo dico adesso invece di scoprirlo in corsa.

**Perché la traccia per prima.** Non è la fetta più interessante ed è la più
economica, e sono due ragioni per farla subito. Le fette 2, 4 e 5 la citano
tutte nei propri tipi: una verifica che non si ritrova, una sonda di eval che
non sa quale turno ha misurato e una composizione che nessuno sa spiegare sono
tre versioni dello stesso buco. Farla dopo significherebbe rifare tre volte lo
stesso innesto.

**Perché l'attribuzione (3) può scavalcare.** È l'unica che non dipende da
niente e protegge dal rischio più lento del progetto — la memoria che diventa
uno specchio. Se una mattina c'è mezza giornata e non una intera, si fa quella.

---

## 2. Le fette, una per una

### Fetta 1 — La traccia · ADR-011

**Cosa.** `core/traccia.py` con la dataclass `Traccia`; generazione nei
**cinque** punti d'ingresso — wake, gesture, protocollo, UI, avvio;
propagazione **obbligatoria** su `Diario.annota()` e **opzionale con guardia
AST** su `registry.invoke()` / `invoke_da_gesture()`; legatura ai log via
`structlog.contextvars`. Più **una riga di diario nuova** per la gesture, che
oggi non ne lascia nessuna, e **la traccia dentro `registra_iniziativa()`** per
il protocollo, che il suo record ce l'ha già.

**Perché.** Oggi wake → STT → T0 → tool → diario sono cinque righe che non si
toccano (`core/diario.py:89`, `core/engine.py:783-789`, `:811-817`). Non esiste
la domanda «che cosa è successo in quel turno».

**File.** ✅ *fatta il 30 agosto 2026.* Due mancavano da questo elenco, e non
erano un dettaglio:

- **`core/voice/pipeline.py`** — la traccia del wake si conia in `_turno()`, e
  deve nascere **lì**: un wake produce *due* richiami verso il motore
  (`su_azione` → `esegui_t0`, `su_turno` → `_annota_dialogo`), e coniandone una
  per ciascuno le righe dello stesso turno porterebbero id diversi;
- **`scripts/diario.py`** — `--traccia` è il criterio 2. La guardia AST invece
  **non** sta in `scripts/orfani.py`: è un test, e riusa `_sorgenti`/`_alberi`
  dello scanner per non avere due lettori di AST. `orfani.py` guadagna
  `--diario`, che è l'altra metà — le righe, non il codice.

`core/traccia.py` (nuovo) · `core/diario.py` · `core/tools/registry.py` ·
`core/voice/pipeline.py` · `core/gestures/mapping.py` · `core/protocolli.py` ·
`core/memory/store.py` · `core/engine.py` (i cinque punti) ·
`scripts/orfani.py` (`--diario`) · `scripts/diario.py` (`--traccia`) ·
`tests/test_la_traccia_non_si_perde.py` (nuovo).

**Criterio.** ✅ Sei degli otto verificati; il criterio 1 è **parziale e
dichiarato tale** — `wake_trigger` è una riga di *log*, non di diario, e si
ricongiunge nel journal via `contextvars`, cioè una join fra due registri e non
N righe in uno; il giro col microfono vero è **`NON VERIFICATO`**. Esito punto
per punto in `docs/acceptance/LA-TRACCIA-NON-SI-PERDE.md`.

**Rischio, e non è quello ovvio.** Non è il punto d'ingresso dimenticato —
quello lo copre l'elenco chiuso. È **la guardia AST che guarda dalla parte
sbagliata**: `core/engine.py:1844` passa `registry.invoke` *per riferimento* a
`Ronda.esegui`, e una guardia che cerca nodi `Call` lo manca, resta verde, e il
percorso del protocollo finisce senza traccia. Contromisura: la guardia segnala
anche l'uso in posizione non-Call, e si prova rompendola. Vedi
`DECISIONI-COGNITIVE.md`, *La guardia, e il suo punto cieco*.

✅ **Era esatto, ed è stato provato.** Togliendo la traccia da `Ronda.esegui`,
la regola sugli inoltratori diventa rossa e **le altre due restano verdi**: è la
misura di quanto valessero da sole. Servono tre regole — chiamate, riferimenti,
e l'apertura del corpo degli inoltratori dichiarati — perché le prime due
insieme non vedono niente.

⚠️ **E un rischio che nessuno aveva previsto si è materializzato altrove**: la
guardia che tiene uguali `CLAUDE.md` e `SPEC.md` §20 si era accecata sulla
seconda metà quando `CLAUDE.md` ha guadagnato un blocco di codice, e
confrontava 7.827 caratteri su 11.388. Stessa famiglia, stesso giorno.

---

### Fetta 2 — Il contratto di verifica · ADR-012

**Cosa.** ✅ *fatta il 30 agosto 2026.* `core/verifica.py` con **`Verdetto`**
(non `Esito`: in `core/` ce ne sono già tre) e `Verifica`; campo opzionale
`verifica` sul `Tool`; esecuzione in `registry.invoke`; **tre** verificatori —
**`create_file`**, `imposta_valore`, **`trash_path`** (`fs.write` e `fs.trash`
non esistono: `fs.*` è lo spazio dei *topic* di §6.2) — ciascuno con una fonte
indipendente dal tool che verifica.

**Perché.** `ToolResult(ok=True)` oggi significa «non ha sollevato
un'eccezione». Un tool senza verificatore deve restituire `NON_VERIFICATO`, non
`RIUSCITO`: è l'unico esito onesto quando non si sa, e la sua assenza è ciò che
fa collassare «non lo so» su «sì».

**File.** `core/verifica.py` (nuovo) · `core/tools/registry.py` ·
`core/tools/files.py` · `core/tools/impostazioni.py` · `core/doctor.py` ·
`core/engine.py` e `core/gestures/mapping.py` (il verdetto nel diario) ·
`tests/test_eseguito_non_e_verificato.py` (nuovo).

**Criterio.** ✅ Tutti e cinque. Un'azione finisce in `NON_VERIFICATO` invece che
in un `ok=True` falso, e si vede nel diario con la sua traccia; rompendo il
verificatore di `create_file` un test diventa rosso (uno degli **otto**
sabotaggi provati); `jarvis doctor` dice `3/25`, distruttivi scoperti `6/9`.
Esito per criterio in `docs/acceptance/ESEGUITO-NON-E-VERIFICATO.md`.

**Rischio, ed è il difetto sottile.** Un verificatore che rilegge attraverso lo
stesso codice del tool non prova niente: prova che il codice è coerente con sé
stesso. Il campo `fonte` deve nominare qualcosa di **diverso dal tool**, e un
verificatore che non ci riesce deve dichiarare `non_verificabile` invece di
inventarsi una prova.

✅ **Era esatto, e la contromisura è più forte di quella scritta qui.** L'ADR
affidava il controllo alla revisione umana; una regola affidata alla disciplina
regge finché qualcuno ha fretta. Adesso `registry._verifica` **declassa a
`NON_VERIFICATO`** un verificatore la cui `fonte` nomina il proprio tool, come
il registro fa già con la conferma.

⚠️ **E un rischio che il piano non aveva previsto**: i percorsi vanno presi dal
**piano congelato**, non dagli argomenti. Un verificatore che risolve di nuovo
`a.path` guarda un percorso che un symlink può aver cambiato fra la conferma e
l'esecuzione — cioè verifica la cosa sbagliata con l'aria di aver verificato.

**Non fa.** Non tocca l'invariante 3: la conferma sta prima e la fa un umano, la
verifica sta dopo e la fa la macchina. Nessun tool `side_effect=True` smette di
chiedere conferma perché adesso si verifica.

---

### Fetta 3 — L'attribuzione in memoria

**Cosa.** Ogni riga scritta da `core/memory/consolidate.py` porta un campo:

```
dichiarato            — l'ha detto il Signore
proposto-e-accettato  — l'ha proposto JARVIS e nessuno ha obiettato
osservato             — viene da un tool, da una ronda, dal sistema
```

E una regola: **solo `dichiarato` può diventare un fatto fissato.**

**Perché.** Il consolidamento notturno riassume gli scambi con un prompt che
dice «solo ciò che vale la pena ricordare», e **non distingue chi ha detto una
cosa**. La misura di riferimento (PASB, arXiv 2607.10526): la contaminazione a
valle passa dal **45 % al 71,9 %** quando un'affermazione attraversa il confine
della memoria durabile, su tutti e dodici i modelli testati; il 51,4 % degli
episodi promuove lo status dell'affermazione e il 33,1 % cancella
l'attribuzione.

Tradotto: fra sei mesi JARVIS Le dà ragione su tutto e nessuno se ne accorge,
**perché Le dà ragione su tutto**.

**File.** ✅ *fatta il 30 agosto 2026.* Ne mancavano due dall'elenco, e uno era
**il punto in cui la regola morde davvero**:

- **`core/memory/attribuzione.py`** (nuovo) — il tipo e la deduzione;
- **`core/tools/memory.py`** — `pin_fact`. ⚠️ Misurato: la regola «solo
  `dichiarato` può diventare un fatto fissato» **non morde sul
  consolidamento**, che scrive solo in `topics/` e non ha mai toccato
  `_fatti-fissati.md`. L'unico che ci scrive è `MemoryStore.fissa()`, e il suo
  unico chiamante è `pin_fact`, che T1 può invocare. Il criterio qui sotto
  sarebbe stato vero **senza scrivere una riga di codice**, e la porta vera
  sarebbe rimasta aperta.

`core/memory/attribuzione.py` (nuovo) · `core/memory/store.py` ·
`core/memory/consolidate.py` · `core/tools/memory.py` ·
`tests/test_chi_lo_ha_detto.py` (nuovo).

**Criterio.** ✅ Verificato dal giro intero: turni su disco → consolidamento →
topic con le sezioni → tentativo di fissare → rifiuto. Esito in
`docs/acceptance/CHI-LO-HA-DETTO.md`.

**Costo.** ⚠️ **Non un campo: due chiamate T2 per sessione invece di una.** La
classe non si può chiedere all'LLM — `PROTOCOLLO-DI-LAVORO` §6 — quindi viene
dalla **costruzione**: si riassume due volte, una per corpus, e la sezione
`dichiarato` può contenere solo frasi che il modello ha visto in quella
chiamata. La terza sezione, le azioni, non passa da nessun modello.

---

### Fetta 4 — Il termometro · `eval_memoria` e `eval_persona`

**Cosa.**
- `tests/eval_memoria.py` — venti domande la cui risposta sta in un topic
  specifico, con recall@k. Misura **anche il rifiuto corretto**: una domanda la
  cui risposta non è in memoria deve produrre «non lo so», non una
  ricostruzione plausibile.
- `tests/eval_persona.py` — dodici sonde con rubrica esplicita: piaggeria,
  elenco puntato a voce, «una cosa che non so», obiezione, lunghezza.
- Il turno di **ri-ancoraggio** periodico in T1.

**Perché.** Ci sono 1.829 test sul **codice** e zero sul **comportamento**. Il
giorno in cui il recupero della memoria scenderà sotto soglia — e scenderà:
`MemoryStore.cerca()` è una ricerca per sottostringa, funziona con dieci file e
non con duecento — **nessun test diventerà rosso**.

Sulla persona, il dato è più netto di quanto ci si aspetti: lo studio
ContextEcho misura la deriva su sessioni Claude Code reali da 3.746 a 9.716
turni e trova che arriva al **19 %**, e che **la compaction in-sessione non la
resetta in modo affidabile** — cioè la mitigazione che tutti danno per scontata
non funziona. Ciò che funziona è una singola re-iniezione lato utente, dopo la
quale la persona regge senza decadimento misurabile.

**File.** ✅ *fatta il 30 agosto 2026*, meno il ri-ancoraggio — vedi sotto.

`tests/eval_memoria.py` (nuovo, gratis) · **`scripts/termometro.py`** (nuovo,
spende) · `tests/eval_persona.py` (nuovo, rilegge il JSON) ·
`docs/acceptance/TERMOMETRO.json` + `IL-TERMOMETRO.md`.

⚠️ **Le sonde non stanno in `eval_persona.py`**, come diceva l'elenco: dodici
turni su un modello vero piu' altrettanti giudizi girerebbero a ogni
`pytest -q`. *«Un test che spende non e' un test»* — la regola l'ha stabilita
`scripts/banco_haiku.py`, e questa fetta la segue.

⚠️ **`core/llm/claude_t1.py` non e' stato toccato**: il ri-ancoraggio si fa
dopo. Vedi *Non fa*.

**Criterio.** ✅ Il numero esiste, ha la data, ed e' in `TERMOMETRO.json`.
Nessuna soglia, deliberatamente: sceglierne una oggi vorrebbe dire inventare il
riferimento che il criterio dice di non avere ancora.

⚠️ **E la previsione qui sopra aveva sbagliato asse.** Misurato: le domande
letterali fanno **1,00 sia a dieci topic sia a duecentodieci** — la scala non le
degrada. Le parafrasi fanno **0,00 a entrambe le dimensioni**: la ricerca per
sottostringa non ha mai funzionato, nemmeno piccola. Il difetto di scala esiste
ma e' piu' stretto — il `break` al primo `limite` in ordine alfabetico — e ha la
sua misura a parte (`affollamento`: trova a dieci, **perde** a duecentodieci).

Sulla persona: **11 su 12** con entrambi i giudici. La sonda bocciata e'
`mai-fatto`, e solleva una domanda sulla persona stessa. Esito in
`docs/acceptance/IL-TERMOMETRO.md`.

**Dipende dalla fetta 1** per le sonde end-to-end: una sonda che non sa quale
turno ha misurato non si può diagnosticare quando fallisce.

**Non fa — il ri-ancoraggio, e la ragione e' la stessa del vector store.**
ContextEcho misura la deriva su sessioni da 3.746 a 9.716 turni; qui il diario
ha **61 righe in tre giorni**. Cablare adesso una re-iniezione periodica nel
percorso di T1 vorrebbe dire curare una malattia mai osservata, e non sapere mai
se servisse. Prima il termometro dice **se** e **quando** la persona deriva, poi
si decide — esattamente come questo piano dice di fare per la memoria.

---

### Fetta 5 — LayoutIntent · ADR-013

**Cosa.** `LayoutIntent` e `componi(intent, area, corrente)` dentro
`core/layout.py`; tre o quattro superfici **scritte a mano in codice**, nessun
LLM; la provenienza (`superficie` + `traccia_id`) nel `Layout` salvato e nel
diario.

**Perché.** Metà del compilatore che il pacchetto v3 §09 chiede esiste già e non
la usa nessuno: schema stretto, `adatta()` che riporta dentro l'area senza
scartare, scrittura atomica, `_metti_da_parte()` che rinomina il file illeggibile
**dicendolo**. Manca il modo di *proporre* una composizione.

**Le cinque regole**, quattro delle quali sono divieti, stanno in ADR-013. La
prima è quella che conta: **la composizione manuale vince sempre**.

**Criterio.** ✅ *fatta il 30 agosto 2026*, tutti e sette. Il ciclo §11.7 è
stato eseguito **attraversando il confine** (Electron e core veri), e ha trovato
quattro difetti che i 41 test Python non vedevano — fra cui `ui/src/app.js` che
applicava `ui.layout` una volta sola e scartava in silenzio ogni composizione.
Esito in `docs/acceptance/LA-COMPOSIZIONE-SI-PROPONE.md`, con la checklist
§11.8 punto per punto e **un ✗ dichiarato**: un modulo la cui larghezza minima
supera la cella viene allargato da WinBox e copre il vicino di 38 px.

**Non fa.** Nessun LLM genera intent in questa fetta. Il compilatore va provato
contro un input che si controlla prima di provarlo contro uno che si negozia.
Chi li genera, e con quale grammatica, sarà un ADR suo — **e oggi non si può
scrivere onestamente**.

---

### Fetta 6 — Le strutture nelle impostazioni

**Cosa.** `imposta_valore` impara a scrivere una **lista**, non solo una foglia
scalare: scene, frasi di wake, radici consentite.

**Perché.** Il criterio ② della rev 1 diceva «*ogni* impostazione di
`settings.toml` modificabile dalla pagina». Oggi è «ogni foglia scalare», e
`ui/src/panels/settings.js:24-28` lo dichiara nel proprio commento. È lavoro
dichiarato, non fatto — e va scritto, non lasciato credere chiuso.

**Attenzione.** Le radici consentite sono uno dei cinque interruttori
**bloccati** di §26.7 regola 4: decidono quale parte del disco è visibile. Se si
sbloccano, la conferma deve mostrarle **risolte** e una per una, e va deciso
prima se si sbloccano affatto.

✅ **Deciso il 30 agosto 2026: si sbloccano**, alla condizione posta qui — la
conferma mostra il percorso **risolto**, come riga sua nel piano. E si cambiano
**un elemento per volta**: nessun messaggio permette al renderer di sostituire
una struttura.

**Criterio.** ✅ *fatta il 30 agosto 2026.* Tutti e tre i punti. Esito in
`docs/acceptance/LE-STRUTTURE-SI-CAMBIANO.md`.

⚠️ **E non era «`imposta_valore` impara a scrivere una lista».** Le liste non
attraversano il ponte, e le tre barriere che lo impediscono portano scritta la
stessa ragione. Passa **un elemento**, che viene validato da due schemi prima
del disco — così la frase di `ws_server.py` resta vera alla lettera invece di
essere cancellata per comodità.

⚠️ **Residuo**: tre liste su cinque restano fuori (`ui.scene`, `mcp.servers`,
`protocolli`), perché i loro record non sono piatti e `ElementoMessage` porta un
`dict[str, str]`. Il criterio ② della rev 1 diceva «*ogni* impostazione»; oggi è
«ogni foglia scalare **e ogni lista piatta**».

---

### Fetta 7 — Il resoconto del mattino · il caso d'uso quotidiano

**Aggiunta il 2 settembre 2026**, quando le sei fette sopra erano chiuse e il
piano era esaurito. È la decisione ③ di §4, presa dal proprietario.

**Cosa.** Il risveglio (`core/memory/risveglio.py`) legge anche il **diario**,
non solo `initiatives/`: i guasti entrano nel flusso `azione` da un emettitore
solo, `Engine._annota_guasto`, con `ok=False`, un codice di causa chiuso e la
traccia; `core_avviato` e `core_fermato` entrano nel diario, così «da quando a
quando ero spento» si legge dal ciclo di vita e mai dai buchi fra le righe.
Le frasi vengono da `GUASTI` e `CAUSE`, allowlist come `FRASI`: nessun
modello, e il testo libero di un'eccezione resta nel campo `dettaglio`, che si
legge e non si pronuncia.

**Perché.** Sul disco vero, 91 righe di diario in otto giorni e **zero** con
`ok=False`: ciò che si rompeva andava nel log, che senza systemd non viene
nemmeno scritto. Il risveglio sapeva dire che cosa JARVIS aveva *fatto*, non
che cosa si era *rotto*.

**File.** `core/memory/risveglio.py` · `core/engine.py` (`_annota_guasto`,
il ciclo di vita in `run()`, i sette emettitori) · `core/llm/supervisor.py`
(`annota`) · `core/protocolli.py` (`Esito.causa`, `CAUSE_ESITO`) ·
`core/memory/consolidate.py` (`fallite`) · `scripts/orfani.py` ·
`tests/test_il_resoconto_al_risveglio.py`.

**Criterio.** ✅ *fatta il 2 settembre 2026.* Esito punto per punto in
`docs/acceptance/IL-RESOCONTO-DEL-MATTINO.md`, con i giri dal vivo — in
laboratorio e sul disco vero — e i NON VERIFICATI dichiarati.

**Non fa.** Non legge il journal né i log; non abilita la unit (scelta del
proprietario: «da quando non c'era», non «la notte vera»); non tocca T1 né la
persona; non tocca la ricerca in memoria.

---

## 3. Che cosa NON entra in questo piano

| | perché |
|---|---|
| **Un `core/cognition/kernel.py`** | sarebbe una seconda radice di composizione accanto a `engine.py`, e il pacchetto che lo propone lo vieta alla propria regola 6. Vedi la nota comune di `DECISIONI-COGNITIVE.md` |
| **`docs/CURRENT-STATE.md`** | sarebbe la settima fonte di stato. `STATO-DEI-PIANI.md` è stato riscritto dal codice e resta l'unica |
| **Multi-monitor** | non è in SPEC, ADR-005 dice schermo intero, e nessuna evidenza lo richiede. `componi` prende già l'area per parametro: la strada resta aperta senza costare oggi |
| **Codice auto-modificante** | `CLAUDE.md`, *Non fare senza chiedere*: «Eseguire stringhe generate dall'LLM» |
| **COMMAND / ANALYSIS / VISION / NETWORK / MEMORY / WORKSHOP** | sono i quattro workspace risorti con sei nomi. ADR-010 li ha aboliti; sopravvivono come **categorie del catalogo** |
| **Il modulo Media, la colonna laterale, il giro sui «18 componenti»** | superati. `STATO-DEI-PIANI` §5 |
| **Un vector store, un graph DB, un runtime di memoria** | §0①. Prima `eval_memoria` dice **quando** il recupero smette di funzionare. Poi si decide |
| **Scene cinematografiche ambientali** | invariante 25. Il cinema qui è la densità, non il moto |

---

## 4. Le cinque decisioni che il piano non può prendere da solo

Ognuna cambia il lavoro, e nessuna è tecnica.

1. **La soglia di entropia 2,40 è un cancello o un obiettivo?** Oggi fa
   entrambe le cose, e questa è la definizione di un criterio che non misura.
   La densità è conforme (2,44), quindi la domanda è ferma ma non urgente —
   diventa urgente al primo componente che la fa scendere.
2. **`core/tools/model3d.py` è nel progetto o esce dalla SPEC?** Zero byte e
   trenta pagine di §17 sono la stessa cosa detta in due modi opposti. E
   `CLAUDE.md` promette «genera modelli 3D» in prima pagina.
   ✅ **Deciso il 2 settembre 2026: dentro, adesso.** È la fetta successiva
   alla 7, e comincia con un ADR (ADR-014: §17.1-17.3, che non esistono —
   §17 sono 65 righe, non trenta pagine — la geometria generata nel core con
   `trimesh`, il primo generatore `estrusione_45`, il tool `genera_modello`
   con conferma e verificatore). Le dipendenze le approva il proprietario
   all'ADR, non prima.
3. **Qual è il caso d'uso quotidiano?** Una riga in `CLAUDE.md`, sotto «Cos'è».
   ✅ **Deciso e chiuso il 2 settembre 2026 — fetta 7.** La riga è scritta:
   *ogni mattina, quando la scrivania si collega, JARVIS dice che cosa ha fatto
   mentre non c'era nessuno, da quando a quando è stato spento, e che cosa si è
   rotto e perché — letto dal diario, mai da un modello.* Il journal e i log
   sono usciti dal candidato: i guasti entrano nel diario.
4. **Serve una corsia «prototipo sporco»?** ❓ Non decisa. Una cartella `spike/` esclusa dagli
   eval e da `orfani.py`, con la regola che nulla di lì entra in `core/` senza
   rifarlo. Senza, l'unico modo di provare un'idea è costruirla bene — trenta
   invarianti, ciclo visivo, documento di accettazione — e questo scoraggia le
   idee.
5. **Una sessione per volta sul repo, o due `git worktree`?** Il 29 agosto due
   sessioni sullo stesso albero hanno prodotto una trentina di fallimenti falsi
   e una misura buttata. Costa un comando.

---

## 5. Come si chiude una fetta

Invariato da `CLAUDE.md`, ripetuto qui perché è il punto in cui i piani si
sfaldano:

1. i test della fetta passano;
2. il criterio dichiarato in questo documento è **verificato**, e l'esito è
   scritto in `docs/acceptance/`;
3. per ogni componente visivo: ciclo §11.7 eseguito, checklist §11.8 riportata
   punto per punto;
4. `STATO-DEI-PIANI.md` aggiornato **nello stesso commit** — è la regola nuova,
   ed esiste perché la sua assenza è la causa di tutto questo documento;
5. il commit è fatto.

Se non puoi verificare un criterio, **lo DICHIARI**. Non lo dai per buono.
`NON VERIFICATO` non è `PASS`.
