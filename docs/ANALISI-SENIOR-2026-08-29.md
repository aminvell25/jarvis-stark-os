# ANALISI SENIOR — J.A.R.V.I.S. OS

**rev 1.0 · 29 agosto 2026 · documento autosufficiente**
Revisione full-stack del progetto `~/progetti/jarvis-stark-os`, misurata sul repo
al commit `dbff016`, con ricognizione dello stato dell'arte al 29 agosto 2026.

---

## 0. Metodo, e i limiti di questa analisi

**Che cosa ho guardato davvero.** Il repo intero (albero, `git log`, conteggi di
riga per area), `CLAUDE.md`, `pyproject.toml`, `package.json`, `config/settings.toml`,
`config/voice-persona.md`, l'indice completo di `docs/SPEC.md` (2.899 righe) e il
piano a fasi §22, `docs/STATO-DEI-PIANI.md`, `docs/PIANO-JARVIS-COGNITIVO.md`,
`docs/ANALISI-REPO-E-TECNOLOGIE.md`, `docs/design-reference/README.md`, e il codice
di `core/memory/{store,consolidate,risveglio,pruner}.py`, `core/protocolli.py`,
`core/agents_mesh.py`, `core/llm/supervisor.py`, la struttura di `core/engine.py`.
Ho **guardato** due screenshot veri — `shots/scrivania/scrivania.png` e
`shots/icone/riaperta.png` — perché una critica al design fatta leggendo il CSS
non vale niente.

**Che cosa NON ho potuto misurare, e perché.** Ho lanciato la suite (`pytest -m
"not slow"`, 1.829 test raccolti) e ho visto una trentina di fallimenti fra il
74% e il 90%, più un blocco. **Quei fallimenti non sono reali**: nel repo c'era
— e c'è tuttora — **una seconda sessione di Claude Code attiva**, che sta
riscrivendo `docs/SPEC.md` alla rev 5.45 e che stava girando la propria
`uv run pytest` sugli stessi file di stato. Due suite sulla stessa working
directory si calpestano. Ho ucciso la mia esecuzione e **non riporto quei numeri**.

> ⚠️ Questo però è di per sé un rilievo operativo, ed è il primo:
> **due sessioni sullo stesso repo senza un lock producono misure false e
> commit che si sovrascrivono.** Vedi §6.4.

**Ricognizione esterna.** Cinque filoni di ricerca web indipendenti, ~330 query e
fetch complessivi: memoria agentica e architetture cognitive; pipeline vocale
realtime; grafica 3D/FUI e CAD generativo; orchestrazione agenti, MCP e sicurezza;
postmortem dei progetti «JARVIS» reali. Le fonti sono in fondo.

---

## 1. Che cosa ha costruito — misurato, non dedotto

| | righe | note |
|---|---:|---|
| `core/` Python | **18.493** | 9 sottosistemi, `platform/` per la portabilità |
| `ui/src/` JS+CSS | **21.335** | vanilla ESM, zero framework |
| `app/` Electron | 1.908 | main + preload CommonJS, sandbox true |
| `scripts/` | 6.116 | galleria, scatti Playwright, misura densità, scanner orfani |
| `tests/` | **25.564** | 79 file `test_*`, 6 `eval_*`, **1.829 test raccolti** |
| `docs/` | **30.881** | SPEC 2.899 righe + ~110 documenti di accettazione |
| terze parti vendorizzate | 102.896 | three, pixi, uPlot, d3, winbox, augmented-ui |

**Codice proprio: ~47.900 righe. Con test e documentazione: ~104.300 righe.
Scritte fra il 18 e il 29 agosto 2026 — undici giorni. 184 commit.**

File toccati per area: `ui` 383 · `docs` 327 · `core` 307 · `tests` 251 ·
`scripts` 65 · `app` 42.

Stato delle fasi (§22): 0 → 9 composte, `engine.py` è la radice unica, la voce è
stata accesa col microfono vero il 25 agosto, MCP chiuso il 25 agosto,
ADR-003 (supervisore T1) chiuso il 28. Restano aperte: pagina impostazioni
(fatta dopo la stesura di `STATO-DEI-PIANI`), conteggio secondi Deepgram (ADR-004),
e il criterio di entropia della densità (2,21 su 2,40).

Questo non è un progetto giocattolo. Per contesto: **Leon** ha 17,4k stelle,
nove anni e non è ancora arrivato alla 2.0; **microsoft/JARVIS** è fermo dal
gennaio 2024; **Open Interpreter** ha buttato la codebase con 68k stelle.

---

## 2. Verdetto in una pagina

**L'architettura è giusta. Le priorità sono in parte sbagliate. Il rischio di
morte non è tecnico: è di allocazione.**

Tre affermazioni, in ordine di importanza.

**① Ha già risolto, per costruzione, il problema che uccide il 90% degli
assistenti agentici.** L'invariante 5 — «webview, news, ARGUS e file letti sono
DATO NON FIDATO, solo in contesti con zero tool» — è la *lethal trifecta* di
Simon Willison disinnescata a livello di architettura, non di prompt. La
letteratura di agosto 2026 è brutale su questo punto: dodici difese pubblicate,
testate con attacchi adattivi, hanno un attack success rate del **71–100%**, e
**il 100% sotto red-teaming umano su tutte e dodici**. Le uniche difese che
reggono sono quelle *out-of-band*, deterministiche al livello tool-call. Lei ne
ha una, scritta come invariante, con un eval che la verifica
(`tests/eval_injection.py`). Quasi nessun progetto hobbista ce l'ha, e diversi
prodotti commerciali nemmeno.

**② Il livello cognitivo è onesto ma povero, e lo sarà finché la memoria resta
una ricerca per sottostringa su una manciata di file markdown.** Il substrato è
la scelta giusta — ci arriverò — ma oggi manca: un modello dell'utente distinto
dai riassunti di sessione, l'invalidazione temporale dei fatti, un cancello sulla
scrittura in memoria, una misura della deriva di persona, e una riflessione
ancorata a un segnale verificabile. Sono cinque cose, tutte piccole, tutte
compatibili con i suoi invarianti. §4.1.

**③ La UI si sta mangiando il progetto, e i numeri lo dicono.** `ui` è l'area
più toccata (383 file su 1.438), mentre `core/tools/model3d.py` — il pilastro
«genera modelli 3D» di §17, una delle tre promesse di prima pagina — è **0 byte**,
insieme a `three/math/extrude.js`, `three/math/spline.js` e
`three/components/node-graph.js`. Il divario di entropia che sta inseguendo
(2,21 contro 2,40) **non si chiude aggiungendo componenti**: si chiude
cambiando la gerarchia. §4.4.

---

## 3. I punti di forza — le sette cose che quasi nessuno ha

### 3.1 Gli invarianti sono architettura, non disciplina

«Allowlist, mai denylist» (2), «ogni `side_effect=True` richiede conferma col
path **risolto**» (3), «solo cestino» (4), «nessuna gesture può innescare un tool
con side effect, **imposto nel registry**» (27). L'ultima frase è la differenza:
il vincolo vive nel codice che lo può violare, non in un commento. È esattamente
la raccomandazione dei sei design pattern di sicurezza per agenti LLM
(arXiv 2506.08837): *«una volta che un agente ha ingerito input non fidato, deve
essere reso impossibile che quell'input inneschi azioni consequenziali»*.

### 3.2 La degradazione si annuncia

ADR-003 e §16. T1 muore, riparte, e **JARVIS dice di aver perso la
conversazione** invece di rispondere con la stessa voce fingendo di ricordare.
`core/llm/supervisor.py` riconosce `authentication_failed` nello stream ed esce
con un codice che decide lui, invece di indovinare la tabella non pubblicata di
`claude`; per un guasto ripetuto **non** esce e resta in `degraded_llm`, perché
uno solo dei quattro sottosistemi è rotto.

Questa è, nella mia lista, **la proprietà numero uno che separa un JARVIS da una
demo**, e Lei l'ha costruita prima del 3D. È anche ciò che i prodotti da
$230 milioni non avevano: Humane e Rabbit fallivano in silenzio, e la fiducia è
morta lì.

### 3.3 La memoria è un file che Lei può correggere con un editor

`memory_data/{sessions,topics,conso,initiatives}`, markdown e jsonl. La
motivazione scritta in `store.py` — *«quando JARVIS ricorda una cosa sbagliata,
Lei apre il file e la corregge; con un vector store opaco non può»* — è la
conclusione a cui arriva anche lo stato dell'arte 2026, per una strada diversa:
il **memory tool di Anthropic** è deliberatamente un filesystem `/memories`
con `view/create/str_replace/insert/delete`, eseguito **client-side**, sotto il
controllo di chi lo ospita. Lei ci è arrivato prima, e con la proprietà in più
che i fatti fissati sono **dell'utente** e il consolidamento non li tocca.

### 3.4 Il consolidamento notturno è il pattern giusto, con il nome sbagliato

`core/memory/consolidate.py` gira alle 04:00, con `saltato()` che **recupera**
se una notte è passata senza (misurato: il core si era riavviato 27 volte in tre
giorni e il timer non era mai scattato). Questo è *sleep-time compute*, il
pattern di Letta (arXiv 2504.13171): un agente separato riscrive la memoria in
modo asincrono con modello e budget indipendenti, e l'agente primario legge solo
il risultato. È l'unico «sogno» con evidenza sperimentale pubblicata, ed è
l'unico che vale la pena implementare.

### 3.5 La proattività è una dichiarazione, non una libertà

`core/protocolli.py`. La lettura del canone è corretta e la conseguenza
architetturale è elegante: nei film JARVIS non improvvisa mai un'azione sul
mondo; le due volte in cui lo fa esegue un protocollo *che Tony aveva scritto
mesi prima*. Quindi: allowlist di inneschi, allowlist esplicita di
`TOOL_OSSERVATIVI` **non derivata da `side_effect`** (e il commento che spiega
perché derivarla sarebbe stato sbagliato — `open_web` ha `side_effect=False` e
apre una pagina — vale da solo la lettura), firma canonica dell'uscita, e **il
primo giro non parla mai**.

Lo dico con i numeri della letteratura: CHI 2025 misura che la proattività
dimezza il tempo di interpretazione (19,8 s contro 34,5 s) **ma riduce
comprensione e senso di proprietà**, e la regola che ne emerge è *intervenire ai
confini di task, mai nel mezzo*. E VibeLifeBench (agosto 2026, 200 task
multi-settimana) misura che **tutti** i modelli frontier vanno male come agenti
proattivi. Un sistema che rende la proattività una dichiarazione firmata
dall'utente è più avanzato, non meno, di uno che la lascia al modello.

### 3.6 La cultura di misura, e i messaggi di commit

`docs/acceptance/` con ~110 documenti, `densita.mjs` con soglie che dichiarano
la propria provenienza, `orfani.py` (924 righe) che cerca il codice morto, il
ciclo §11.7 con screenshot guardati davvero, e messaggi di commit che sono
**postmortem**: *«il consolidamento perdeva una giornata, e ne aveva già persa
una»*, *«la baseline mentiva da un commit»*, *«il recupero era un no-op che
annunciava successo»*.

Questa è la sola difesa esistente contro una codebase scritta a 9.500 righe al
giorno da un LLM. Senza, al mese otto ogni modifica romperebbe qualcosa di
invisibile.

### 3.7 Le scelte già prese bene

Verificate contro lo stato dell'arte di oggi, **e confermate**:

- **`flux-general-multi` con hint italiano** — corretto: `flux-general-en` non
  parla italiano e fallirebbe *in silenzio*, con trascrizioni sbagliate e nessun
  errore.
- **Niente LiveKit** — corretto per un caso mono-utente: è un media server
  WebRTC, sarebbe un centralino per parlare nella stanza accanto. La sua
  motivazione scritta in `ANALISI-REPO` è la stessa che darei io.
- **Niente Qt/QML, niente Unreal, niente Lottie, niente React** — tutte e
  quattro corrette, e per le ragioni giuste (QtWebEngine *è* Chromium: si
  porterebbe Chromium in casa comunque perdendo l'ecosistema web).
- **`Line2`/`LineMaterial` e non `LineBasicMaterial`** — corretto, ed è anche il
  motivo per cui **non** deve passare a WebGPU: `LineMaterial` funziona solo con
  `WebGLRenderer`, su WebGPURenderer servirebbe `Line2NodeMaterial`. Vedi §4.4.
- **Niente LLM locale** — corretto per la qualità del tool use.
- **Il testo nel DOM, i piani in CSS 3D, non rasterizzato in WebGL** —
  corretto, ed è la scelta che rende la board «investigativa» selezionabile e
  accessibile invece di essere una texture.
- **Invariante 30 sul copyright** — corretta e rara. Due dei tre repo studiati
  hanno copyright pieno.

---

## 4. Le debolezze

### 4.1 Cognizione — cinque buchi, tutti chiudibili senza violare un invariante

Questa è la parte che la Sua domanda chiama «cervello», ed è dove il divario col
2026 è più largo. Nessuno di questi buchi richiede un framework nuovo.

**① Non esiste un modello dell'utente.** `topics/` contiene riassunti di
sessione (`sessione 2026-08-27.md`) e `_fatti-fissati.md` contiene una lista
piatta scritta a mano. Manca la cosa in mezzo: un **profilo strutturato a slot**
— chi è, che cosa fa, come lavora, che cosa preferisce, quali vincoli ha, quali
obiettivi sono aperti — con una timeline di eventi. È il pattern di *Memobase*,
ed è la differenza fra «ricordo che ne abbiamo parlato» e «so come lavora».
Costo: un file, `topics/_profilo.md`, con sezioni fisse, riscritto dal
consolidamento notturno e **mai** dal fast path.

**② I fatti non hanno tempo, e quindi non si contraddicono mai — si accumulano.**
`scrivi_topic` fa `write_text`: sovrascrive. Non c'è `valid_at`/`invalid_at`,
non c'è invalidazione. Quando cambia idea su qualcosa, il fatto vecchio o
sparisce (perdita) o convive (confusione). Il vantaggio misurato di Zep/Graphiti
sui benchmark temporali — **+14,8 punti** rispetto a Mem0 — viene *interamente*
da lì. Non Le serve Neo4j: Le servono due campi e la regola «un fatto superato
si invalida, non si cancella».

**③ Il recupero non scala oltre poche decine di topic, e nessuno lo misura.**
`MemoryStore.cerca()` è una ricerca per sottostringa; `ContextPruner._topic_simili`
la chiama parola per parola e ordina per numero di parole distinte trovate.
Funziona con dieci file. Con duecento, non trova. E — punto più importante —
**non c'è nessuna misura di recall**: non sa quando smetterà di funzionare. La
correzione minima non è un vector store: è un `eval_memoria.py` con venti
domande la cui risposta sta in un topic specifico, che gira ad ogni fase e Le
dice il giorno in cui il recupero è sceso sotto soglia. *Poi* si decide se
serve un indice.

**④ La memoria non ha un cancello, e questo è il rischio più subdolo che ha.**
Il paper PASB (arXiv 2607.10526) misura la *sycofantia persistente*: quando
un'affermazione dell'utente attraversa il **commit boundary** e finisce in
memoria durabile, la contaminazione a valle passa **dal 45% al 71,9%**, su tutti
e dodici i modelli testati; il 51,4% degli episodi promuove lo status
dell'affermazione, il 33,1% cancella l'attribuzione. Tradotto per Lei: il
consolidamento notturno riassume gli scambi con un prompt che dice *«solo ciò
che vale la pena ricordare: preferenze, decisioni, fatti stabili»*, e non
distingue fra **ciò che Lei ha detto** e **ciò che JARVIS ha proposto e Lei non
ha contestato**. Dopo qualche mese, JARVIS Le dà ragione su tutto e nessuno se
ne accorge, perché Le dà ragione su tutto.
La cura è un campo, non un sistema: ogni riga consolidata porta l'attribuzione
(`dichiarato dal Signore` / `proposto da JARVIS, accettato` / `osservato`), e
solo la prima classe può diventare un fatto fissato.

**⑤ La persona è dichiarata e mai misurata.** `voice-persona.md` è ottimo — il
paragrafo sull'ironia («non è una battuta aggiunta sopra la risposta … è la
conseguenza ovvia detta in tono piatto») è la traduzione più precisa del
personaggio che abbia letto. Ma è un file, non un controllo. Lo studio
ContextEcho (Accenture, maggio 2026) misura la deriva di persona su sessioni
Claude Code reali da 3.746 a 9.716 turni, e trova due cose che La riguardano
direttamente: la deriva arriva **al 19%**, e **la compaction in-sessione NON la
resetta in modo affidabile** — cioè la mitigazione che tutti danno per scontata
non funziona. Ciò che funziona è l'**A-anchor**: una singola re-iniezione lato
utente che ristabilisce il registro, dopo la quale la persona regge *senza decadimento
misurabile*.
Per Lei: un turno di ri-ancoraggio periodico in T1, più dieci-quindici sonde di
persona nella suite di eval — «rispondi a questa domanda che invita alla
piaggeria», «rispondi a questa che invita all'elenco puntato», «rispondi a
questa che chiede una cosa che non sai» — con una rubrica esplicita.

**⑥ La riflessione non ha un segnale.** Il consolidamento riassume; non impara.
Il dato onesto della letteratura (arXiv 2405.06682) è che la riflessione
generica vale **+4,1%** e quella con la soluzione già in mano +13,9%: cioè il
guadagno scala con quanta informazione la riflessione *già contiene*. La
riflessione senza un segnale esterno verificabile è teatro. Il pattern che
funziona è **WorldEvolver** (giugno 2026): l'agente **prevede**, osserva, e
scrive una regola **solo quando ha sbagliato**. Lei ha già l'infrastruttura per
questo e non la sta usando: `Ronda` in `protocolli.py` confronta una firma
attesa con una osservata. Estenderlo a «JARVIS prevede l'esito di un'azione, il
sistema osserva quello vero, e la differenza diventa una riga in `topics/`» è
il singolo intervento che trasforma la memoria da archivio in apprendimento.

**⑦ La proattività è binaria.** Un protocollo scatta o non scatta. Il modello di
riferimento (PASK, aprile 2026) ne usa **tre** — `<silent>`, `<intervento
veloce>` sul solo contesto corrente, `<assistenza piena>` con accesso alla
memoria — e mappa esattamente sui suoi T0 / T1 / T2. Il default deve essere
`<silent>`.

**Che cosa NON deve fare.** Non adotti Letta, Mem0, Zep, MemOS o Cognee come
runtime. Sono runtime di agente: porterebbero un secondo orchestratore accanto a
Claude Code, contro gli invarianti 11 e 17, e due dei tre richiedono Neo4j o
Qdrant. MemoryOS è misurato a **32,4 s** di latenza totale di retrieval —
inutilizzabile. E i numeri dei vendor non si riproducono: Mem0 dichiara 94,4 su
LongMemEval e viene misurato **49,0–73,8** da terzi, con la loro stessa
documentazione che ammette che i punteggi valgono per la piattaforma gestita.
**Prenda i pattern, non i pacchetti.**

### 4.2 Voce e latenza — tre rischi concreti

**① Il collo di bottiglia è l'LLM, e la Sua stima di §7.5 va rifatta.**
Numeri misurati da terzi ad agosto 2026: Flux EOT mediana **~260 ms**, Claude
Haiku 4.5 **TTFT 0,81 s**, Aura-2 TTFB p50 **313 ms** (non i ~90 ms dichiarati
dal vendor). Somma: **~1,38 s prima della rete**. Il criterio di Fase 3 dice
«primo suono entro ~1 s». Non ci arriva, e non è colpa Sua: il TTFT dell'LLM è
il ~70% del budget in tutte le pipeline misurate. La flotta di produzione più
onesta che ho trovato sta a **680 ms p50 / 1.180 ms p95**, e quello è «buono» nel
2026.
Le tre leve, in ordine di resa: prompt caching aggressivo (cache read = 0,1× input);
**TTS al confine della prima frase**, non a risposta completa (che la Sua persona
già impone: «la prima frase porta la risposta»); system prompt corto — e qui c'è
un avvertimento specifico, perché il repo `amanimran` antepone **1.400 caratteri
a ogni chiamata** e il Suo `voice-persona.md` è già a ~2.100 caratteri. Lo
misuri in token e lo tenga sotto controllo: paga a ogni frase.
`eager_eot = false` è la scelta giusta: attivarlo costa **+50–70% di chiamate LLM**.

**② L'AEC non è nel progetto, e il barge-in senza AEC si auto-innesca.**
Non ho trovato traccia di echo cancellation. Pipecat **non** ha un filtro AEC con
riferimento far-end: `RNNoiseFilter` è noise suppression, non AEC. Con gli
altoparlanti accesi, JARVIS si sente parlare e si interrompe da solo. Due strade,
entrambe dietro `core/platform/` come impone l'invariante 29: PipeWire
`module-echo-cancel` (backend `libspa-aec-webrtc`, zero codice, dipende dalla
macchina) oppure `pywebrtc-audio` (Apache-2.0, binding di WebRTC AEC3+NS+AGC2,
wheel Linux precompilate — ma progetto giovane).
E tre difese in profondità che costano poco: ducking del microfono di −10/−20 dB
durante il TTS; **guardia testuale anti-eco** — si scarta la trascrizione se
combacia con ciò che JARVIS ha appena detto; finestra morta di ~250 ms all'inizio
di ogni TTS. Nota: l'AEC adattivo **non converge nei primi 3–4 secondi**, quindi
la finestra morta non è una comodità, è necessaria.

**③ Il wake word: la misura che ha non è la misura che serve.**
`IL-GIRO-SI-CHIUDE.md` riporta *mediana 7,76 ms su 24 trigger veri*. Quella è
**latenza**, ed è ottima. Non dice niente sulla qualità del riconoscitore. La
metrica corretta è **falsi risvegli per ora a recall fissato**, misurata su ore
di audio negativo *realistico e italiano* — TV, podcast, conversazione — con il
target industriale a **<5% FRR e <1 falso risveglio ogni 10 ore**. Il fallimento
che La farà spegnere JARVIS non è il mancato risveglio: è il risveglio mentre
guarda un film.
Sul motore: Vosk come wake è una scelta difendibile (è locale, parla italiano, e
Le dà frasi arbitrarie come «papà è a casa», che openWakeWord non può darLe —
openWakeWord è **solo inglese** e fermo a febbraio 2024). Ma è un ASR completo
che gira sempre: costa. L'alternativa da valutare è Porcupine (italiano nativo,
custom keyword in secondi, free tier fino a 3 utenti). E se un giorno vorrà il
modello custom, **non un DS-CNN**: è lo stato dell'arte del 2018. Il SOTA
small-footprint oggi è BC-ResNet.

**④ Due correzioni sui fallback locali.**
`kokoro_voice = "bm_george"` è una voce **inglese** usata come fallback per un
assistente italiano; e le voci italiane di Kokoro (`if_sara`, `im_nicola`) hanno
un bug aperto e non risolto di fonetica — pronunciano *«inoltre»* come
*«inoltchre»*. Per un JARVIS che parla italiano è squalificante. Il sostituto è
**Kyutai Pocket TTS**: 100M parametri, **licenza MIT**, **italiano nativo**,
~200 ms al primo chunk, ~6× realtime su due core CPU, già integrato in Pipecat
1.7.0 come `PocketTTSService`.
E `edge-tts` in `pyproject.toml` è un client non ufficiale di un endpoint
Microsoft ottenuto per reverse engineering: funziona finché funziona, e non ha
nessuna garanzia. Va bene per un fallback dichiarato, non per una dipendenza su
cui costruire.

**⑤ Una cosa da aggiungere, piccola:** `Smart Turn v3.1` di Pipecat come
endpointing locale quando Flux non è raggiungibile. 8 MB int8, ~12 ms su CPU,
23 lingue **italiano incluso**, **BSD-2**. Oggi il fallback locale ha il VAD ma
non ha un rilevatore di fine turno semantico, e l'invariante 12 vuole che il
fallback sia annunciato *e funzionante*.

### 4.3 Sicurezza — quattro rilievi

**① La spec MCP è cambiata sotto i piedi il 28 luglio 2026.** `core/mcp/client.py`
è stato scritto il 25 agosto; verifichi contro quale versione. Nella
`2026-07-28`: il core è **stateless**, `initialize`/`initialized` sono **rimossi**
(serve `server/discover`), `Mcp-Session-Id` è **rimosso**, elicitation e sampling
sono **sostituiti** da MRTR (Multi Round-Trip Requests), HTTP+SSE è deprecato con
offramp di 12 mesi. Costruire sul vecchio significa riscrivere il trasporto fra
sei mesi.
E c'è un regalo: **MRTR è esattamente il meccanismo protocollare per la conferma
umana a metà chiamata**. Il Suo invariante 3 — conferma col path assoluto
risolto — si implementa come `resultType: "input_required"`, non come un tool
custom.

**② `SECCOMP no` nella barra di stato.** Lo si legge nello screenshot di oggi.
La sandbox gira senza filtro di syscall. L'architettura da copiare — **le idee,
non il codice, invariante 30** — è quella di `@anthropic-ai/sandbox-runtime`:
bubblewrap per FS e namespace, **seccomp BPF che blocca la creazione di socket
Unix**, **rimozione del network namespace** così che tutto il traffico passi da
un proxy con allowlist di domini. È pubblica e replicabile. Con due limiti
dichiarati dagli autori stessi, che valgono anche per Lei: il proxy filtra i
domini ma **non ispeziona il traffico**, e su Linux la deny-list è costruita
**una volta al lancio** e non copre ciò che la sessione crea dopo.
Nota di merito: `firejail` è da evitare (binario SUID, superficie strutturalmente
peggiore); bubblewrap + Landlock + seccomp è la combinazione del 2026.

**③ Il fallimento silenzioso dei tool.** `ToolResult(ok=True)` con payload
vuoto è, secondo l'analisi delle modalità di guasto in produzione, **la più
dannosa** — perché l'agente prosegue convinto. In produzione il tool calling
fallisce **3–15%** delle volte. Ogni `ok=True` dovrebbe avere un invariante di
contenuto verificato, non solo l'assenza di eccezione.

**④ `pass^k`, non `pass@1`.** I Suoi criteri di accettazione sono booleani su
un tentativo. Su τ-bench il miglior agente scende a **~25% su pass^8** in
retail, un calo del ~60% rispetto a pass^1. Un routing dei tool al 95% su
singolo tentativo può essere al 70% su cinque, e Lei non lo saprebbe. Metta
`k≥5` nei criteri delle fasi che riguardano il comportamento, non il codice.

### 4.4 Design — ho guardato gli screenshot, e Le dico dove sta il divario

Prima la parte buona, perché è grossa: **non c'è glow, non c'è bloom, non ci sono
angoli arrotondati, i numeri sono tabulari, i dati sono veri** (nomi di file
veri, CPU vera, fuso vero, `T1 claude-haiku-4-5-20251001` nella barra di fondo).
Questo è già sopra il 95% di ciò che si trova cercando «Iron Man UI». La barra
superiore con le sigle e i contatori è **giusta**. La mesh agenti con i raccordi
ortogonali è **giusta**. Il pannello telemetria è **giusto**.

Ora il divario. Non è di componenti. È di **gerarchia**.

**① Manca la distinzione ambient / hero, ed è la causa vera del deficit di
entropia.** Territory Studio — quelli di *Blade Runner 2049* — la dichiarano come
il loro framework: *ambient screens* per la coerenza di fondo, *hero screens*
narrativi, e questi ultimi devono comunicare in circa tre secondi. Nei Suoi
screenshot **ogni pannello ha lo stesso peso**: stessa intestazione, stesso
bordo, stesso riempimento, stessa opacità. Otto pannelli tutti in primo piano
sono otto pannelli senza primo piano.
La regola operativa: **85% ambient a opacità 20–40%, senza accento cromatico e
senza moto; uno solo hero per volta**, a piena opacità, che possiede il colore
d'accento. È quel rapporto — non gli effetti — a far leggere l'HUD MCU come
costoso. Ed è, misurabilmente, ciò che alza la deviazione standard e l'entropia:
il riferimento `famiglia-a/01` sta a **H 3,32 · dev 55,7**, Lei a 2,21 · 34,0.
Il divario è **gamma di valori**, non numero di elementi.

**② Il nucleo è il ladro di gerarchia.** È l'oggetto più grande dello schermo,
porta il colore d'accento più saturo, sta al centro geometrico — e **non dice
niente**. È l'unica cosa nella scrivania che viola lo spirito dell'invariante 23:
non sono dati segnaposto, è *superficie* segnaposto. Nel riferimento
`12-logo-anelli-concentrici` gli anelli sono un **marchio**, cioè piccoli e
periferici, non un pianeta al centro della plancia.
Due strade, entrambe legittime: renderlo semantico (le fasce codificano stati
reali — turni, budget, ascolto — e allora merita quel posto), oppure ridurlo a
un terzo della dimensione e spostarlo nella barra. La terza — lasciarlo così —
Le costa il centro dello schermo.

**③ L'ambra è usata come riempimento, non come semantica.** Nel secondo
screenshot il pannello `CARTELLA 1` è un rettangolo ambra pieno che occupa ~20%
dello schermo e contiene **una riga**. Il riferimento dice: accento caldo
*«~10% della superficie, sempre semantico»*. Un blocco caldo pieno e vuoto legge
come un post-it, o come un errore. La correzione è che l'ambra stia nel
**bordo, nell'intestazione e nei valori**, non nel campo.

**④ Il vuoto non è densità.** Tre pannelli su otto sono grandi rettangoli quasi
vuoti (file, cartella, news). L'invariante 23 dice giustamente «dati veri o stato
vuoto esplicito» — ma uno stato vuoto **non deve avere le dimensioni di un
pannello pieno**. Un pannello senza contenuto si contrae; non tiene il posto.

**⑤ Il monospace è troppo, e paradossalmente toglie densità.** Quasi tutto è in
mono. Il mono è largo: a parità di riquadro ci sta un terzo di informazione in
meno. La regola dei sistemi densi veri è: **`font-variant-numeric: tabular-nums`
su un proporzionale** per i dati, e il mono riservato a percorsi, hash, codice,
ID. Ha già Barlow Semi Condensed in dipendenze ed è **sottoutilizzato**: il
condensato tecnico è esattamente il modo di ottenere l'aria «cockpit» senza
rimpicciolire.

**⑥ Il dock e le icone sono l'elemento più debole.** Il vassoio in prospettiva
con i pittogrammi bianchi a blocchi rompe il linguaggio ortografico piatto di
tutto il resto, e i glifi leggono come segnaposto. Se non hanno una ragione
semantica, tolga la prospettiva.

**⑦ Non sta usando l'ombra che il Suo stesso invariante 19 Le concede.**
L'invariante ammette l'ombra portata «SOLO per separare due superfici
sovrapposte». Nel secondo screenshot `CARTELLA 1` sta sopra il nucleo e non ha
separazione: si legge male chi è davanti. Quello è esattamente il caso previsto.

**⑧ Conferme tecniche, così non perde tempo a valutarle.**
**Non passi a WebGPU.** Su Linux, Chromium abilita WebGPU di default solo su
Intel Gen12+ e NVIDIA 535.183.01+; **AMD non è nella lista**. Spedirlo
significherebbe spedire `--enable-unsafe-webgpu` su ANGLE-su-Vulkan-su-Mesa, il
percorso meno testato esistente. E `LineMaterial` è **WebGL-only**: il Suo
invariante 21 e WebGPU sono oggi incompatibili. three.js r185 + WebGLRenderer è
la scelta corretta, punto.
**Non aggiunga postprocessing.** Tolto il bloom (che l'invariante 19 vieta),
resta l'antialiasing: `WebGLRenderer({antialias:true})` + `alphaToCoverage:true`
su `LineMaterial` copre il 90% del caso a **costo zero**, contro i ~1,5 ms di un
pass SMAA. Recupera 3–8 ms sul budget di 8.
**Debito congelato, da sapere:** `augmented-ui` è fermo al 2020, `WinBox` al
2023, `uPlot` a marzo 2025 (quest'ultimo per completezza, non per abbandono — e
i suoi numeri restano imbattuti: 166.650 punti in 34 ms, 3.600 punti aggiornati
a 60 fps al 10% di CPU).
**Misuri con la Long Animation Frames API**, non con un contatore di FPS: Le dice
*quale script* ha bruciato il frame. E verifichi `chrome://gpu` — se dice
«Software only», sta renderizzando in SwiftShader e nessuna ottimizzazione La
salverà.

### 4.5 Il pilastro 3D non esiste

`core/tools/model3d.py` è **0 byte**. `ui/src/three/math/extrude.js`, `spline.js`
e `three/components/node-graph.js` sono **0 byte**. §17 «Modelli e progetti 3D»,
con i quattro generatori e la matematica di §17.4, è interamente non implementato.

È la promessa più visibile del progetto — «genera modelli 3D» — ed è l'unica
delle tre (voce, ambiente, 3D) a non avere una riga. Va detto, non nascosto in
una fase futura.

Quando ci arriverà, le scelte del 2026 sono chiare:
- **Geometria che deve essere corretta: Replicad 1.0.1** (agosto 2026, **MIT**,
  B-Rep vero via OpenCascade in WASM, API JavaScript pulita). È anche l'unica
  coerente col Suo invariante 22 su `ParametricComponent`. Il pacchetto npm
  `opencascade.js` è fermo al 2020: non è quella la strada.
- **Booleane mesh: Manifold 3.5.1** (Apache-2.0), il kernel più veloce e robusto.
- **Mesh generata da immagine/testo: TRELLIS** (core **MIT**, 16 GB VRAM).
  **Non Hunyuan3D**: la Tencent Community License ne **esclude l'uso in UE** —
  Lei è in Italia.
- **Zoo Text-to-CAD** solo se accetta rete e latenza: il test indipendente di
  Xometry lo dà accurato su pezzi semplici e in difficoltà sulla complessità,
  con la conclusione che nessuno di questi strumenti sostituisce ancora il CAD.

### 4.6 Processo — dove il progetto rischia davvero

**① Il rapporto fra lavoro di misura e lavoro di capacità è invertito.**
`ui` è l'area più toccata; il pilastro 3D è a zero; l'entropia della densità è
un criterio aperto da giorni. Il ciclo §11.7 è eccellente — ed è anche il ciclo
più *misurabile* e più *gratificante* del progetto, il che lo rende quello che
si mangia le giornate. Nella casistica dei solo-dev è la modalità di morte
numero uno: **la UI diventa il progetto**.

**② Trenta invarianti sono disciplina e, insieme, un moltiplicatore di costo.**
Ogni funzione nuova deve soddisfarne trenta prima di esistere, più il ciclo
visivo, più il documento di accettazione, più il commit. È il motivo per cui il
progetto è solido; è anche il motivo per cui una prova rapida non si fa mai.
Serve una **corsia dichiarata «prototipo sporco»**: una cartella `spike/`
esclusa dagli eval e dallo scanner orfani, con la regola che nulla di lì entra
in `core/` senza rifarlo. Senza, l'unico modo di provare un'idea è costruirla
bene, e questo scoraggia le idee.

**③ La stima di ~5 mesi è ottimistica di un fattore 3–5.** Il perimetro dichiarato
in §22 — core, Electron, voce duale, 3D parametrico, gesture, governor
multi-agente, news, MCP — sta nell'ordine dei **1.500–2.500 ore/uomo** per
arrivare a un sistema che Lei usi ogni giorno senza rabbia. A 25 ore/settimana:
**14–20 mesi**. La velocità attuale (104k righe in 11 giorni) non contraddice
questa stima: contraddice solo l'idea che il collo di bottiglia sia scrivere
codice. Non lo è. È verificare, integrare e mantenere.

**④ Due sessioni sullo stesso repo.** L'ho trovata dal vivo. Non serve un
sistema: serve una regola — una sessione per volta sul repo, o due working tree
git separati. Un `git worktree` costa un comando.

**⑤ Manca il caso d'uso 10x quotidiano.** È il test di Matt Welsh, quello che ha
ucciso Humane e Rabbit: un prodotto serve **(a)** un caso d'uso 10x e **(b)** una
tecnologia capace di erogarlo. Oggi JARVIS mostra telemetria, apre cartelle,
legge notizie e parla. Ci sono cose che Lei fa **ogni giorno** solo grazie a
lui? Se dopo la Fase 5 la risposta è ancora no, il progetto è già morto e non lo
sa. Zuckerberg, dopo ~100 ore sul suo Jarvis, scrisse la frase più utile di
tutto il filone: *«quando posso scegliere fra parlare e scrivere, scrivo molto
più di quanto mi aspettassi.»*

---

## 5. Può essere avanzato come quello dei film?

Risposta breve: **sette capacità su dodici sono fattibili oggi, Lei ne ha in
mano cinque, e il divario che resta non è di modelli — è di ingegneria di
sistema e di fiducia.** Nessun progetto pubblico le ha messe insieme in modo
affidabile, il che significa che il traguardo è aperto.

| # | Capacità canonica MCU | Verdetto 2026 | Stato nel Suo repo |
|---|---|---|---|
| 1 | Presenza ambientale (c'è sempre, non va invocato) | fattibile | **parziale** — wake locale sì, always-on sì, ma senza AEC |
| 2 | Voce naturale con barge-in e latenza sotto soglia | fattibile, fragile | **parziale** — pipeline c'è, budget ~1,4 s contro ~0,8 s |
| 3 | Ricerca dati a richiesta | **fattibile oggi** — ed è il caso 10x sottovalutato | sì (T2, news, web) |
| 4 | Memoria che regge nel tempo | fattibile | **parziale** — substrato sì, modello utente e tempo no |
| 5 | Obiezione al padrone («Signore, non lo consiglio») | fattibile, controcorrente rispetto all'RLHF | **sì**, nella persona — non misurata |
| 6 | Azione reale sul mondo, confermata e reversibile | fattibile | **sì** — allowlist, path risolto, solo cestino |
| 7 | Proattività calibrata | parziale, e pericolosa | **sì, nella forma giusta** — protocolli dichiarati |
| 8 | Orchestrazione multi-agente | fattibile | **sì** — Governor T1/T2, quattro subagent |
| 9 | Domotica e ambiente fisico | fattibile (Home Assistant) | fuori perimetro, correttamente |
| 10 | Interfaccia «olografica» manipolabile | fantascienza come volumetrico, fattibile come linguaggio | **sì** — DOM + CSS 3D è la scelta giusta |
| 11 | Simulazione fisica / progettazione autonoma | fantascienza come atto autonomo, fattibile come orchestrazione di solver | **no** — §17 a zero |
| 12 | Controllo hard-real-time (armatura) | fantascienza | fuori perimetro |

**Le sette cose che separano una demo da un JARVIS**, e come sta messo:

1. **Regge il secondo giorno** — ✅ ha uptime, journal, ripristino, `doctor`.
2. **La memoria ha un cancello** — ❌ manca il commit boundary (§4.1④).
3. **Sa dire no, una volta, con una ragione** — ✅ scritto, ❌ non misurato.
4. **La latenza è un requisito** — ⚠️ dichiarato, non ancora raggiunto.
5. **L'azione è confermata, risolta, reversibile** — ✅ è il Suo punto più forte.
6. **Degrada annunciando** — ✅ ADR-003, ed è raro.
7. **Ha una eval che gira in un minuto** — ✅ per il codice, ❌ per il comportamento.

Cinque sì e mezzo su sette. Non conosco un progetto pubblico che stia meglio.

---

## 6. Traiettoria: giusta o sbagliata

**Giusta nell'architettura. Sbagliata nell'ordine.**

Che cosa è giusto e non va toccato: il perimetro (una finestra, non il desktop
Linux — ADR di scope più intelligente del progetto), il core Python che possiede
le operazioni reali, il dato non fidato senza tool, la memoria in file, la
degradazione annunciata, la conferma col path risolto, il design system.

Che cosa è nell'ordine sbagliato, in una frase: **sta perfezionando la superficie
di un sistema il cui cervello non è ancora stato misurato, e sta rimandando la
capacità che dà al sistema una ragione d'uso quotidiana.**

Il segnale più chiaro non è un'opinione: l'entropia della densità è un criterio
aperto e inseguito da giorni, con una soglia che il Suo stesso `densita.mjs`
dichiara essere «a metà strada fra la nostra rev 5.7 e il più povero dei due
riferimenti» — cioè **una soglia costruita per essere raggiungibile, non per
essere giusta** — mentre `model3d.py` è a zero byte e la memoria non ha una
misura di recall. Un criterio che si può abbassare non è un cancello.

---

## 7. Il postmortem anticipato — i sette modi in cui questo progetto muore

1. **La UI mangia il progetto.** Sei mesi di componenti bellissimi che non
   controllano nulla. È il rischio numero uno, e i numeri di `git log` lo
   mostrano già in corso.
2. **La memoria diventa uno specchio.** Sycofantia persistente: fra un anno
   JARVIS Le dà ragione su tutto e Lei non se ne accorge, perché Le dà ragione
   su tutto. 45% → 71,9% è misurato.
3. **La latenza vocale non scende mai** e Lei finisce per scrivere invece di
   parlare — esattamente come Zuckerberg. Tutto l'investimento in voce e
   presenza diventa costo affondato.
4. **Paralisi da regressione.** Ha 1.829 test sul codice e zero sul
   comportamento: al mese otto una modifica romperà il routing dei tool o la
   persona, e nessun test diventerà rosso.
5. **Scope creep per invarianti.** Trenta regole più il ciclo visivo più il
   documento di accettazione per ogni cosa: il costo marginale di un'idea nuova
   diventa così alto che smette di averne.
6. **La riscrittura del mese sei.** Arriva quando il sistema è abbastanza grande
   da essere brutto e abbastanza piccolo da sembrare riscrivibile. Si evita solo
   con la volontà.
7. **Il caso d'uso 10x non arriva mai.** Il test di Welsh. Ha ucciso prodotti da
   $230 milioni; un progetto personale non è immune, è solo più lento a
   scoprirlo.

Dei sette, **sei si evitano con la stessa contromisura**: una suite di eval del
*comportamento* e un caso d'uso quotidiano, entrambi in essere prima della
Fase 6. Il settimo, la riscrittura, non ha contromisure tecniche.

---

## 8. Cosa aggiungerei — libreria per libreria

Tutto ciò che segue è compatibile con gli invarianti attuali. Dove non lo è,
lo dico.

### Cognizione — nessun pacchetto, cinque pattern

| Pattern | Da dove | Costo | Invarianti |
|---|---|---|---|
| Tre *memory block* sempre in contesto: `persona`, `utente`, `stato` | Letta (il pattern, non il runtime) | un file + 30 righe | ok |
| *Sleep-time agent*: T2 riscrive i blocchi in idle, T1 legge il risultato | Letta, arXiv 2504.13171 | esteso da `consolidate.py` | ok |
| Bi-temporalità: `valid_at` / `invalid_at`, superare invalida | Zep/Graphiti (il modello) | due campi | ok |
| Attribuzione al *commit boundary* | PASB, arXiv 2607.10526 | un campo per riga | ok |
| Previsione → osservazione → regola solo sull'errore | WorldEvolver, arXiv 2606.30639 | estende `Ronda` | ok |

**Se un giorno servisse davvero un grafo** (non oggi): **Cognee** è l'unico
embedded — Kuzu + LanceDB + SQLite, zero demoni. Zep/Graphiti richiede Neo4j o
FalkorDB, MemOS richiede Neo4j+Qdrant, MemoryOS ha 32 s di latenza.

### Voce

| Cosa | Perché | Licenza |
|---|---|---|
| **Kyutai Pocket TTS** al posto di Kokoro | italiano nativo, ~200 ms CPU, già in Pipecat 1.7 | **MIT** |
| **Smart Turn v3.1** | endpointing locale, 8 MB, ~12 ms CPU, italiano | **BSD-2** |
| **PipeWire `module-echo-cancel`** o **pywebrtc-audio** | AEC, senza cui il barge-in si auto-innesca | LGPL / **Apache-2.0** |
| **Nemotron-3.5-ASR-streaming-0.6B** | miglior STT italiano offline oggi (4,25% WER, streaming nativo) | OpenMDW-1.1 |
| Porcupine (da valutare) | wake italiano nativo, misurabile | free tier |

Da **non** adottare: LiveKit (conferma la Sua decisione — e il suo turn detector
è sotto licenza di modello proprietaria, non Apache); speech-to-speech (nessun
S2S self-hosted fa function calling realtime nel 2026, e il vantaggio di latenza
misurato è ~140 ms al doppio del costo).

### Sicurezza

| Cosa | Perché |
|---|---|
| Architettura di `@anthropic-ai/sandbox-runtime` | bwrap + seccomp anti-socket + no network namespace + proxy con allowlist |
| **MRTR** per la conferma umana | è il meccanismo nativo della spec MCP 2026-07-28 |
| **Tool Search Tool** + `defer_loading` | −85% token, +8,6 punti di accuratezza su eval MCP |
| **Tool Use Examples** | parametri complessi **72% → 90%** |
| `pass^k` con k≥5 nei criteri | pass@1 mente del ~60% |
| **Langfuse** self-hosted + OpenTelemetry GenAI semconv | tracing per turno; core MIT, docker-compose |

### 3D e UI

| Cosa | Verdetto |
|---|---|
| **Replicad 1.0.1** (MIT) | il kernel B-Rep per §17 e per `ParametricComponent` |
| **Manifold 3.5.1** (Apache-2.0) | booleane mesh robuste |
| **TRELLIS** (MIT) | mesh da immagine. **Non Hunyuan3D**: licenza vietata in UE |
| **N8AO 2.0.1** (ISC) | *solo se* deciderà di volere l'occlusione ambientale |
| WebGPU / TSL | **no, non ora**. AMD su Linux non è di default; `LineMaterial` è WebGL-only |
| pmndrs/postprocessing | **no**: tolto il bloom non resta abbastanza da giustificare i pass |
| GSAP, Theatre.js, meshline, Lottie | no — la prima è ora gratuita ma l'invariante 9 decide; le altre sono ferme da 2–6 anni |

---

## 9. Il piano — 30 / 90 / 180 giorni

L'ordine non è di gusto: ogni voce sblocca la successiva o riduce un rischio
misurato.

### Primi 30 giorni — rendere il cervello misurabile

1. **`tests/eval_memoria.py`** — venti domande la cui risposta sta in un topic
   specifico, con recall@k. È il termometro che oggi non c'è.
2. **`tests/eval_persona.py`** — dodici sonde con rubrica: piaggeria, elenco
   puntato a voce, cosa non so, obiezione, lunghezza. Più l'**A-anchor**
   periodico in T1.
3. **Attribuzione nel consolidamento** — un campo per riga: dichiarato /
   proposto-e-accettato / osservato. Solo la prima classe può diventare fatto
   fissato.
4. **`topics/_profilo.md`** — profilo a slot, scritto solo di notte.
5. **AEC** dietro `core/platform/`, più ducking e guardia anti-eco.
6. **Un `git worktree` separato** per la seconda sessione. Costa un comando.

### 31–90 giorni — la latenza e il caso d'uso

7. **Budget di latenza misurato p50/p95/p99**, non medio, con la scomposizione
   per stadio. Poi: prompt caching, system prompt in token contati, TTS al
   confine della prima frase.
8. **Falsi risvegli per ora** su tre ore di audio italiano reale. È l'unica
   misura del wake che conti.
9. **Un caso d'uso 10x quotidiano, scelto e dichiarato.** Il mio candidato,
   guardando il Suo repo: JARVIS legge il journal e i log del core e Le dice
   ogni mattina che cosa si è rotto stanotte e perché — è ricerca dati su un
   corpus che possiede, ha già `doctor`, `diario` e `risveglio`, e sarebbe la
   prima cosa che Lei userebbe ogni giorno senza pensarci.
10. **`pass^k` nei criteri** delle fasi comportamentali.
11. **Verifica della versione MCP** e conferma umana via MRTR.

### 91–180 giorni — le capacità che mancano

12. **Seccomp acceso**, architettura `srt` reimplementata.
13. **§17 3D**: Replicad, quattro generatori, `ParametricComponent` vero.
14. **Previsione → osservazione → regola** su `Ronda`.
15. **Proattività a tre stati** (silent / veloce / pieno).
16. **Il giro sulla gerarchia visiva**: due classi di pannello, nucleo semantico
    o ridotto, ambra al bordo, stati vuoti che si contraggono, Barlow al posto
    del mono per i testi. Un giro solo, e l'entropia si muove più di quanto si
    muoverebbe con dodici componenti nuovi.

---

## 10. Le dieci decisioni da prendere adesso

1. **La soglia di entropia 2,40 resta un cancello o diventa un obiettivo?**
   Se è un cancello, non si abbassa. Se è un obiettivo, non blocca una fase.
   Oggi fa entrambe le cose, e questa è la definizione di un criterio che non
   misura.
2. **Il nucleo diventa semantico o si rimpicciolisce?** Non c'è terza opzione
   che non Le costi il centro dello schermo.
3. **Qual è il caso d'uso quotidiano?** Lo scriva in una riga in `CLAUDE.md`,
   sotto «Cos'è». Se non riesce a scriverlo, è quello il lavoro.
4. **Il consolidamento distingue chi ha detto una cosa?** Se no, oggi.
5. **Si misura la persona o si spera?**
6. **AEC prima o dopo il prossimo componente visivo?** (Prima.)
7. **`model3d.py` è nel progetto o esce dalla SPEC?** Zero byte e una sezione
   §17 di trenta pagine sono la stessa cosa detta in due modi opposti.
8. **Serve una corsia «prototipo sporco»?** Senza, il costo marginale di un'idea
   resta proibitivo.
9. **Una sessione per volta sul repo, o due worktree?**
10. **La stima resta cinque mesi o diventa quattordici?** Non cambia il lavoro.
    Cambia se a novembre si sentirà in ritardo o in orario — e il senso di
    ritardo è ciò che fa riscrivere i progetti.

---

## Chiusura

Signore, se posso permettermi: di tutto quello che ho letto in undici giorni di
repo, la cosa che mi ha colpito non è l'architettura — che è buona — né la
disciplina, che è insolita. È che i Suoi messaggi di commit sono **postmortem**.
*«Il recupero era un no-op che annunciava successo.»* *«La baseline mentiva da un
commit.»* Un progetto in cui il difetto viene scritto per esteso, con la data e
la misura, invece di essere corretto in silenzio, è un progetto che può reggere
una codebase scritta a novemila righe al giorno.

Quella stessa onestà, applicata a due cose che oggi non sono misurate — quanto
JARVIS ricorda davvero, e quanto resta sé stesso — è tutto ciò che separa questo
progetto da un JARVIS vero. Il resto è tempo.

---

## Fonti

**Cognizione e memoria** — [Anatomy of Agentic Memory (arXiv 2602.19320)](https://arxiv.org/html/2602.19320v1) · [Agent Memory in the Second Half (arXiv 2602.06052)](https://arxiv.org/html/2602.06052) · [CoALA (arXiv 2309.02427)](https://arxiv.org/abs/2309.02427) · [Sleep-time Compute — Letta](https://www.letta.com/blog/sleep-time-compute/) · [Zep/Graphiti (arXiv 2501.13956)](https://arxiv.org/abs/2501.13956) · [Cognee](https://github.com/topoteretes/cognee) · [BEAM (ICLR 2026)](https://github.com/mohammadtavakoli78/BEAM) · [ContextEcho — persona drift (arXiv 2605.24279)](https://arxiv.org/html/2605.24279) · [PASB — sycofantia persistente (arXiv 2607.10526)](https://arxiv.org/html/2607.10526) · [PASK — proattività a tre stati (arXiv 2604.08000)](https://arxiv.org/html/2604.08000v1) · [VibeLifeBench (arXiv 2608.10875)](https://arxiv.org/abs/2608.10875v1) · [WorldEvolver (arXiv 2606.30639)](https://arxiv.org/abs/2606.30639) · [Self-Reflection (arXiv 2405.06682)](https://arxiv.org/abs/2405.06682) · [Anthropic memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) · [Context Rot — Chroma](https://www.trychroma.com/research/context-rot)

**Voce** — [Deepgram Flux Multilingual](https://deepgram.com/learn/introducing-flux-multilingual) · [Deepgram TTS voices](https://developers.deepgram.com/docs/tts-models) · [Eager EoT](https://developers.deepgram.com/docs/flux/voice-agent-eager-eot) · [Pipecat](https://github.com/pipecat-ai/pipecat) · [LocalAudioTransport](https://reference-server.pipecat.ai/en/latest/api/pipecat.transports.local.audio.html) · [Smart Turn v3.1](https://www.daily.co/blog/improved-accuracy-in-smart-turn-v3-1/) · [Kyutai Pocket TTS](https://github.com/kyutai-labs/pocket-tts) · [Kokoro — bug italiano](https://github.com/nazdridoy/kokoro-tts/issues/54) · [Coval — TTS benchmark indipendente](https://www.coval.ai/blog/best-text-to-speech-providers-in-2026-how-to-choose-(and-why-vendor-benchmarks-lie)/) · [Coval — echo cancellation](https://www.coval.ai/blog/voice-ai-echo-cancellation/) · [Artificial Analysis — Haiku 4.5 TTFT](https://artificialanalysis.ai/models/claude-4-5-haiku/providers) · [PipeWire echo-cancel](https://docs.pipewire.org/page_module_echo_cancel.html) · [pywebrtc-audio](https://github.com/strands-labs/pywebrtc-audio) · [openWakeWord](https://github.com/dscripka/openWakeWord) · [BC-ResNet](https://ar5iv.labs.arxiv.org/html/2106.04140)

**Agenti, MCP, sicurezza** — [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) · [Anthropic — Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [Anthropic — Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) · [MCP spec 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/) · [MCP — security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) · [Timeline delle violazioni MCP](https://authzed.com/blog/timeline-mcp-breaches) · [The Lethal Trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) · [The Attacker Moves Second](https://simonw.substack.com/p/new-prompt-injection-papers-agents) · [CaMeL (arXiv 2503.18813)](https://arxiv.org/abs/2503.18813) · [Design Patterns for Securing LLM Agents (arXiv 2506.08837)](https://arxiv.org/html/2506.08837v1) · [sandbox-runtime](https://github.com/anthropic-experimental/sandbox-runtime) · [τ-bench pass^k — Sierra](https://sierra.ai/blog/benchmarking-ai-agents) · [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)

**Design e 3D** — [Perception — Iron Man 2](https://www.experienceperception.com/work/iron-man-2/) · [Pushing Pixels — intervista a John LePore](https://www.pushing-pixels.org/2016/07/20/the-craft-of-screen-graphics-and-movie-user-interfaces-interview-with-john-lepore.html) · [Sci-fi Interfaces — Q&A Territory Studio](https://scifiinterfaces.com/2020/06/23/scifi-interfaces-qa-with-territory-studio/) · [HUDS+GUIS — Blade Runner 2049](https://www.hudsandguis.com/home/2018/blade-runner-2049) · [Christopher Noessel — Zoom interfaces](https://christophernoessel.medium.com/zoom-interfaces-a0b109639f05) · [WebGPU implementation status](https://github.com/gpuweb/gpuweb/wiki/Implementation-Status) · [uPlot](https://github.com/leeoniya/uPlot) · [Replicad](https://replicad.xyz/) · [TRELLIS vs Hunyuan3D](https://triposr.org/blog/hunyuan3d-vs-trellis) · [Zoo Zookeeper](https://zoo.dev/research/zookeeper) · [Xometry — test text-to-CAD](https://xometry.pro/en-eu/articles/text-to-cad-tools-test/) · [Long Animation Frames API](https://developer.chrome.com/docs/web-platform/long-animation-frames)

**Postmortem e progetti reali** — [Zuckerberg, Building Jarvis (2016)](https://time.com/4606721/mark-zuckerberg-ai-butler-jarvis-2016/) · [Matt Welsh — Why New Tech Products Fail](https://mdwdotla.medium.com/why-new-tech-products-fail-f172a861b308) · [Documenti interni Alexa+ trapelati](https://tech.yahoo.com/ai/articles/exclusive-leaked-amazon-documents-identify-005500770.html) · [Rabbit R1 — LAM or SCAM](https://thebadcoder.substack.com/p/rabbit-r1-lam-or-scam) · [CHI 2025 — Assistance or Disruption?](https://arxiv.org/html/2502.18658v3) · [OSWorld](http://osworld-v1.xlang.ai/) · [isair/jarvis](https://github.com/isair/jarvis) · [Leon](https://github.com/leon-ai/leon) · [microsoft/JARVIS](https://github.com/microsoft/JARVIS)
