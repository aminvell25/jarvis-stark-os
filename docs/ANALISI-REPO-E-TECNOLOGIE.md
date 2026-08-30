> ## 🟢 CORRENTE — 30 agosto 2026
>
> **Autoritativo** per l'elenco delle tecnologie **valutate e SCARTATE**
> (Qt/QML, Unreal, Lottie, GSAP, React, Vue). `CLAUDE.md` lo cita: non
> riproporle. A quell'elenco si aggiungono, da `PIANO-JARVIS-COGNITIVO` rev 2
> §0①, i **runtime di agente e di memoria** — Letta, Mem0, Zep, MemOS, Cognee,
> LangGraph: se ne prendono i pattern, non i pacchetti.
>
> ⚠️ **Superata la voce 8**, «workspace con colore e dominio»: il campo `ws` è
> diventato `categoria` e non governa più la visibilità (ADR-010). L'idea
> sopravvive come modo di ordinare il catalogo, non come pagina.
>
> Stato corrente del progetto: **`docs/STATO-DEI-PIANI.md`**.

# Analisi repository e tecnologie — addendum alla rev 5.0

> ### ✅ Esito verificato il 24 agosto 2026 — **8 adozioni su 10**
>
> Contro il repo, non dedotto: `core/memory/consolidate.py` ①, `store.py` ②,
> `conso/` ③, `core/news/collectors/` ④, `core/doctor.py` ⑤, le frasi T0 ⑥,
> la suite a 572 test ⑦, LiveKit studiato e non adottato ⑩. **Invariante 30
> scritta**, `CLAUDE.md` riga 95.
>
> Due non adottate, per ragioni diverse:
> - **⑧ workspace con colore e dominio — SUPERATA da ADR-010.** Non c'è più un
>   workspace: `ws` è diventato `categoria` e non governa la visibilità.
>   L'idea sopravvive come modo di ordinare il catalogo (§26.3), non come pagina.
> - **⑨ bridge Telegram — non iniziato**, ed è corretto: era dichiarata «v2».
>
> Quadro completo: `docs/STATO-DEI-PIANI.md`.

**Agosto 2026.** Tre repository esaminati, sei tecnologie valutate. Le sezioni della specifica da aggiornare sono indicate alla fine.

---

# PARTE 1 — I tre repository

## 1.1 `Grominet95/jarvis-OS` — il più utile dei tre

74 commit, sistema funzionante, francese. Python 41,7% / JS 25,7% / HTML 14% / CSS 12,7%.

⚠️ **Prima di tutto, il vincolo che conta**: la licenza è **Proprietary Source License — © 2026 Barthélemy Houot, all rights reserved**. Può studiarne l'architettura — **le idee non sono coperte da copyright** — ma **non può copiarne il codice**, nemmeno una funzione. Lo tratti come si tratta un articolo: si impara, non si trascrive.

### Le sei idee che valgono davvero

**① Consolidamento notturno della memoria — "AutoDream"**

La loro trovata migliore. Ogni notte un `ConsolidationAgent` ripassa le sessioni recenti e fonde le informazioni rilevanti nei *topic* a lungo termine. Loro lo chiamano l'equivalente del sonno.

**Perché è superiore al nostro `ContextPruner`**: il nostro è *reattivo* — pota quando il budget token è saturo, e quello che perde è perso. Il loro è *programmato*, gira quando nessuno sta usando il sistema, e ha tutto il tempo di ragionare su cosa vale la pena conservare. Potatura sotto pressione contro consolidamento a mente fredda: non è lo stesso lavoro.

**Da adottare.** E.D.I.T.H. acquisisce un passaggio notturno.

**② Memoria in markdown, non in un database opaco**

`sessions/` (jsonl per sessione), `topics/` (note a lungo termine scritte dall'assistente), `conso/`, `initiatives/`. Tutto su file, tutto ispezionabile, tutto versionabile con git.

Il vantaggio non è tecnico ma pratico: quando JARVIS ricorda una cosa sbagliata, Lei apre il file e la corregge con un editor. Con un vector store opaco, non può.

**Da adottare.**

**③ Log giornaliero di consumo — `conso/`**

Token e costo, per giorno. Dato il Governor (§5.4) e la quota dell'abbonamento, questo Le serve per sapere quando la finestra sta per chiudersi *prima* che si chiuda. **Da adottare.**

**④ Collector pluggabili per il motore proattivo**

`proactive/collectors/` con un file per sorgente (meteo, news). Aggiungere un collector = aggiungere un file.

Più pulito del nostro modulo news monolitico (§15). **Da adottare come pattern.**

**⑤ Bridge Telegram — accesso mobile**

Stesso LLM, stessa memoria, stessi strumenti, dal telefono. Autorizzazione a un solo `OWNER_ID`; qualunque altro account riceve un rifiuto e non viene processato.

Per JARVIS è ovvio in retrospettiva: risolve il problema "e quando non sono alla scrivania?" senza costruire un'app mobile. Costo di implementazione basso. **Da valutare per la v2** — non è nel percorso critico, ma è il primo candidato quando la v1 sta in piedi.

⚠️ Con una condizione: il bot Telegram è **un secondo canale d'ingresso non fidato**. Deve passare dalla stessa allowlist e dalle stesse conferme umane. Un `side_effect=True` confermato via Telegram è una conferma legittima solo perché l'owner ID è verificato — ma il perimetro va scritto, non assunto.

**⑥ `jarvis doctor` — stato di tutti i componenti**

Un comando che riporta lo stato di ogni sottosistema. Compare anche nel terzo repository (`jarvis --doctor`): quando due progetti indipendenti convergono sulla stessa cosa, è un segnale.

Con la nostra architettura — core, T1 persistente, Deepgram, Vosk, Electron, WebSocket — la diagnosi "cosa è rotto" senza uno strumento è penosa. **Da adottare, in Fase 1.**

### LiveKit Agents — la decisione da prendere

Usano **LiveKit Agents** per la pipeline vocale: STT + LLM + TTS orchestrati, turn detection, barge-in. È un framework di produzione per agenti vocali real-time, e ha **supporto di prima classe per Deepgram Flux** — la classe `STTv2` si collega proprio all'endpoint `/listen/v2`.

Noi la stiamo scrivendo a mano (§7).

**Il caso a favore**: potrebbe togliere una o due settimane dalla Fase 3, e barge-in e turn detection sono precisamente i punti dove le implementazioni artigianali sbagliano.

**Il caso contro**, che ritengo decisivo: LiveKit è costruito per **audio di rete multi-partecipante**. Porta WebRTC, un server (cloud o self-hosted) e un modello a stanze. Il Suo caso è una persona, una macchina, un microfono, zero rete. Sarebbe montare un centralino per parlare nella stanza accanto.

**Raccomandazione**: non adottarlo, ma **rubarne il modello di turn-taking**. Se però alla Fase 3 il barge-in Le costa più di tre giorni di debug, si fermi e lo rivaluti — a quel punto il calcolo cambia.

### Da non copiare

Il **riconoscimento facciale** per la sequenza di risveglio (una foto di riferimento, scan biometrico all'avvio). Cinematografico, ma è decorazione con una webcam e una dipendenza di visione in più. Salti.

---

## 1.2 `krrish612/jarvis-linux` — segnale basso, e tre bandiere rosse

1.506 commit, 3 stelle. Devo essere schietto: **questo repository non è un modello da seguire.**

**Bandiera rossa ①** — L'URL di clone nel README punta a un utente diverso (`Turbo31150`) dal proprietario del repository (`krrish612`), e la firma finale è "Built by Franck Delmas". È un fork con il README dell'originale intatto. Non sta guardando il progetto di chi lo pubblica.

**Bandiera rossa ②** — Le metriche in vetrina misurano **inventario, non capacità**: "600+ agenti", "2.500+ script", "2.658 comandi vocali", "87 tool MCP", "19 database", "53 tabelle". Sono numeri che crescono da soli. Un sistema con 2.658 comandi vocali non ha 2.658 capacità: ha un dizionario. E `TASKS_DOMINATION.json`, `TASKS_DOMINATION_V2.json`, `WORKLOG_MEGA.md` nella root non sono organizzazione, sono accumulo.

**Bandiera rossa ③** — Il dominio è un altro: cluster multi-GPU a 6 schede, trading algoritmico su MEXC Futures, automazione LinkedIn. Il suo JARVIS è un ambiente desktop personale. La sovrapposizione è quasi nulla.

### L'unica cosa che vale

Il **color routing** dei canali browser: rosso = social, blu = trading e tecnica, giallo = generazione contenuti, verde = automazione. Un codice cromatico che assegna un significato semantico ai canali.

Trasposto al Suo caso: **i workspace 01–04 di §13 potrebbero avere un colore e un dominio**, invece di essere numeri vuoti. Piccola idea, ma coerente con un'interfaccia dove ogni elemento porta informazione.

Il resto lo lasci.

---

## 1.3 `amanimran786/jarvis-ai` — quattro idee buone, architettura opposta

208 commit, macOS, local-first su Ollama. Direzione **contraria alla Sua** (loro: locale di default, cloud come escalation; Lei: Claude Code, nessun LLM locale). Ma quattro cose meritano.

⚠️ **Nessun file LICENSE nella root.** In assenza di licenza esplicita vale il copyright pieno: **tutti i diritti riservati**. Vale lo stesso vincolo del primo repo — idee sì, codice no.

**① "Always-On Brain Core" — e l'avvertimento che porta con sé**

`jarvis_core_brain.py` carica identità, progetti, preferenze e roadmap da note del vault e **antepone ~1400 caratteri di contesto a ogni chiamata al modello**. Loro stessi scrivono che "svolge per Jarvis lo stesso ruolo che CLAUDE.md svolge per Claude Code".

Valida il nostro `voice-persona.md` (§5.7). Ma il numero è un avvertimento: **1400 caratteri × ogni turno**. Il nostro sta sotto i 250 token proprio per questo. Non lasci che cresca — è il tipo di file che si gonfia di dieci righe al mese senza che nessuno se ne accorga, e paga a ogni frase.

**② Vault Obsidian in markdown come substrato di memoria**

Convergono con il primo repository: memoria in file markdown leggibili. Due progetti indipendenti, stessa conclusione. **Conferma l'adozione di §1.1②.**

**③ Meta-comandi: "brief me", "what needs my attention", "what's my status"**

Comandi che non chiedono una cosa ma **un riassunto dello stato**. Fanno fan-out parallelo su calendario, task, vault, codice e ricerca.

È esattamente ciò che rende un assistente diverso da una chat: non risponde soltanto, **riporta**. E si mappa perfettamente sul nostro T0 → T2: la frase è deterministica (grammatica), l'esecuzione è un fan-out di subagent.

**Da adottare**: aggiunga `"riassumimi la giornata"` / `"cosa richiede la mia attenzione"` come frasi T0 che innescano un fan-out T2.

**④ Suite di eval delle capacità**

`capability_evals.py`, `evals.py`, `eval_delta.py`, `capability_parity.py`. Misurano se il sistema fa ancora quello che faceva.

Con Claude Code che scrive il codice, questo passa da buona pratica a **necessità**: è l'unico modo per accorgersi che una sessione ha rotto qualcosa che funzionava tre fasi fa. Estenda il `t0_corpus.py` (§7.6) a una suite vera.

**Da non prendere**: tutto lo stack Ollama e la flotta Qwen3 — contraddice la Sua decisione sui modelli locali. E le lingue del repo dicono HTML 95,4% / Python 4,6%: artefatti generati non ignorati, sintomo di igiene del repository. Il nostro `.gitignore` già li esclude.

---

# PARTE 2 — Le tecnologie proposte

## 2.1 Qt / PySide6 + QML — la sola alternativa seria, e va comunque scartata

Merita una risposta onesta, non liquidatoria. Qt Quick/QML è ottimo per interfacce fluide, cerchi concentrici animati e grafica vettoriale in tempo reale. E il terzo repository usa davvero PySide6 per il desktop. Non è una proposta ingenua.

**Ma c'è un argomento che chiude la questione**: Lei ha bisogno di **YouTube e pagine web dentro l'ambiente** (§6.3). In Qt questo si fa con **QtWebEngine — che è Chromium**. Quindi si porterebbe Chromium in casa comunque, perdendo in cambio l'intero ecosistema web: augmented-ui, uPlot, three.js, WinBox, anime.js diventerebbero tutti inutilizzabili, e andrebbero riscritti in QML.

Peso di Chromium **e** riscrittura da zero. Il peggio dei due mondi.

Aggiunga che i riferimenti visivi di §11 sono tutti raggiungibili in CSS — anzi, augmented-ui esiste apposta — e che QML non ha nulla di equivalente a `clip-path`, e la decisione si chiude.

**Verdetto: no.** Sarebbe la scelta giusta per un HUD embedded senza contenuti web. Non è il Suo caso.

## 2.2 Unreal Engine + UMG — no, e non di poco

L'idea che UMG dia "una resa identica ai film" è comprensibile ma rovesciata: **le UI di Iron Man sono state fatte in After Effects e Illustrator**, da studi di motion design, non in un motore di gioco. Il riferimento non viene da dove si pensa.

Nel merito: runtime di gigabyte, C++ o Blueprint, nessun DOM, nessun testo selezionabile, nessuna `<webview>`, packaging complesso, e tempi di build che trasformano un ciclo di iterazione di trenta secondi in uno di dieci minuti. Il ciclo di verifica visiva di §11.7 — scrivi, rendi, screenshot, correggi — diventerebbe impraticabile.

**Verdetto: no.** È lo strumento sbagliato di un ordine di grandezza.

## 2.3 Lottie — l'unica proposta genuinamente nuova, con una domanda scomoda

Lottie esporta animazioni vettoriali da After Effects in JSON leggero e le riproduce a runtime. La descrizione è corretta ed è tecnologia reale e ottima.

**La domanda scomoda: da dove vengono i file JSON?**

Lottie non *crea* animazioni: le *riproduce*. Servono due cose che oggi non ha: After Effects, e qualcuno che sappia animare in After Effects. Se non le ha, finirebbe a scaricare Lottie gratuite da librerie online — che sono generiche, spesso colorate e arrotondate, e violano frontalmente §11.9 (mai decorazione senza dato) e §10.3 (nessuna animazione senza causa).

E sarebbe un **terzo runtime di animazione** accanto ad anime.js e al ticker di Pixi. Contro l'invariante 9 del `CLAUDE.md`.

**Verdetto: no per la v1.** Con **una sola eccezione**: se Lei ha After Effects e vuole animare a mano la boot sequence, quello è il caso d'uso legittimo — è un'animazione one-shot, complessa, che gira una volta all'avvio e non compete per il frame budget. In quel caso, `lottie-web` solo per quel file. Ma anime.js v4 con `svg.createDrawable()` fa già il disegno progressivo dei contorni, che è esattamente l'effetto della boot sequence. Provi prima quello.

## 2.4 GSAP — la ridiscuto onestamente

Lo ha nominato tre volte. Merita una risposta pulita invece di un rinvio.

**GSAP non è inferiore ad anime.js.** È più maturo, ha timeline più potenti, e dall'aprile 2025 è gratuito con tutti i plugin. Se l'avesse indicato come prioritario al posto di anime.js, avrei costruito la §10.4 su GSAP senza obiezioni.

Il motivo per cui è fuori **non è la qualità: è l'unicità.** Due motori di animazione che scrivono nello stesso frame budget producono jank difficile da diagnosticare, perché ognuno vede solo la propria metà del lavoro.

**Quindi: uno solo. Lei ha scelto anime.js, e resta.** Se cambia idea, si **sostituisce** — non si aggiunge. Cambiare adesso costa poco (non c'è ancora codice); cambiarlo alla Fase 5 costa una settimana.

## 2.5 Electron + React/Vue

Electron: **già adottato** (§3.1), e per la ragione giusta — motore WebGL di Chromium in una finestra applicativa normale.

React o Vue: **no**, per il motivo già in specifica. Il reconciler aggiunge overhead su una scena che gira a 60fps accanto a inferenza ML, e l'invariante "non introdurre React" è nel `CLAUDE.md` proprio perché è la dipendenza che si insinua da sola.

## 2.6 Three.js / WebGL

Già nello stack, con gli addon che contano (`Line2`/`LineMaterial`, three-globe, troika, three-mesh-bvh). Nessun cambiamento.

---

# PARTE 3 — Cosa adottare, in sintesi

| # | Idea | Da | Dove va | Fase |
|---|---|---|---|---|
| 1 | Consolidamento notturno della memoria | Grominet95 | SPEC §5.5 | 4 |
| 2 | Memoria in file markdown ispezionabili | entrambi | SPEC §5.5 | 4 |
| 3 | Log giornaliero token e costo | Grominet95 | SPEC §5.4 | 1 |
| 4 | Collector pluggabili | Grominet95 | SPEC §15 | 8 |
| 5 | `jarvis doctor` | entrambi | SPEC §16 | **1** |
| 6 | Meta-comandi "riassumimi la giornata" | amanimran | SPEC §7.6 + §13 | 3 |
| 7 | Suite di eval delle capacità | amanimran | SPEC §22 | 1 in poi |
| 8 | ~~Workspace con colore e dominio~~ | krrish612 | ~~SPEC §13~~ | ❌ **superata da ADR-010** |
| 9 | Bridge Telegram | Grominet95 | SPEC v2 | ⏳ v2, non iniziato |
| 10 | Turn-taking: studiare LiveKit, non adottarlo | Grominet95 | SPEC §7 nota | ✅ |

**Esito**: 1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ · 5 ✅ · 6 ✅ · 7 ✅ · 8 ❌ superata · 9 ⏳ · 10 ✅

**Scartate**: Qt/QML, Unreal UMG, Lottie, GSAP, React/Vue, riconoscimento facciale, stack Ollama, tutto l'impianto multi-GPU.

## Il vincolo che vale per tutti e tre

Un repository ha licenza **proprietaria esplicita**, un altro **nessuna licenza** — che significa copyright pieno. Il terzo dichiara MIT nel README ma è un fork con attribuzione confusa.

**Conclusione operativa**: da nessuno dei tre può copiare codice. Le idee di questo documento sono descritte a livello architetturale proprio per questo — sono concetti, non implementazioni. Le faccia scrivere a Claude Code da zero, partendo dalla descrizione.

Aggiunga questa riga al `CLAUDE.md`:

```markdown
30. **Non copiare codice da repository di terzi** studiati come riferimento.
    Le idee architetturali si reimplementano da zero; il codice altrui,
    anche se pubblico su GitHub, resta coperto da copyright salvo licenza
    permissiva esplicita e verificata.
```

## Il commento che vale più delle dieci idee

Signore, li ha guardati tutti e tre. Noti cosa hanno in comune: **nessuno dei tre ha un design system.**

Il primo ha un'architettura solida e un'interfaccia amministrativa funzionale. Il terzo ha una memoria a quattro livelli notevole e un'UI PySide6 anonima. Il secondo ha 2.500 script e nessuna interfaccia degna di nota.

La §10 e la §11 della Sua specifica — token, quality gate, checklist di rifiuto, ciclo di verifica visiva — **non hanno equivalenti in nessuno dei tre**. È l'unica parte del Suo progetto che non sta imitando nulla.

È anche l'unica ragione per cui il risultato potrebbe somigliare alle immagini che mi ha mandato, invece che a un altro pannello di amministrazione con un nome ambizioso.
