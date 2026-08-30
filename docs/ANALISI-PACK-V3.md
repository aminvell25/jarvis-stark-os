# Verdetto sul JARVIS_OS_Research_Implementation_Pack_v3

**30 agosto 2026.** Verificato contro il repo al commit `29737f2`.

> **Perché questo documento esiste e non va cancellato.** Un pacchetto di
> pianificazione esterno, ben scritto e dall'aria autorevole, ha dichiarato
> aperte **cinque voci su otto** che erano già chiuse. Se qualcuno lo ritrova
> fra tre mesi senza questo file accanto, lo reimporta — e Claude Code va a
> «chiudere» cinque cose chiuse, riscrivendole peggio, perché il documento gli
> dice che non esistono.
>
> Questo file è la memoria di com'è andata. **Il pacchetto non va copiato in
> `docs/`.** Le tre cose che vale sono già state estratte, e stanno in
> `DECISIONI-COGNITIVE.md`, `PIANO-JARVIS-COGNITIVO.md` e
> `PROTOCOLLO-DI-LAVORO.md`.

---

## 1. Il difetto, e non è nel pacchetto

Il pacchetto dichiara di aver auditato l'HEAD `25a9c32c`. **È vero**: quel
commit esiste, è del 29 agosto alle 16:11, ed era a due commit dall'attuale.

Ma non ha letto il codice a quel commit. Ha letto `docs/STATO-DEI-PIANI.md`
del **24 agosto**, e ne ha ricopiato le cinque voci aperte una per una:
①②③④⑤ del piano vecchio sono diventate A–E del suo audit, nello stesso ordine.
Quattro erano già chiuse *prima* del commit che dice di aver auditato; la quinta
il giorno dopo.

**La causa non è il pacchetto: è il file che ha letto.** `STATO-DEI-PIANI.md`
non veniva aggiornato dal 24 agosto mentre il repo chiudeva sette voci. Un
documento di stato che non si aggiorna è peggio di uno che non esiste, perché
il primo viene creduto.

L'ironia, che vale come lezione: il pacchetto contiene, alla propria regola 1
del §06, la frase *«Never assume a plan document describes the current
implementation»*. L'ha violata scrivendola.

**Contromisura, già presa:** `CLAUDE.md`, *Definizione di «fatto»*, punto 4 —
`STATO-DEI-PIANI.md` si aggiorna **nello stesso commit** che chiude una voce.

---

## 2. Le otto criticità, con l'esito

| | criticità dichiarata | esito |
|---|---|---|
| 🔴 1 | **Cognitive Kernel** — manca un contratto stato→task→azione→verifica | ✅ **VERA.** `grep` su `core/` per `task_id`, `correlation_id`, `Verification`: zero. → ADR-011, ADR-012 |
| 🔴 2 | **Recovery T1** — «un riavvio non deve diventare falsa continuità» | ❌ **FALSA, chiusa 27–28 ago.** `core/llm/claude_t1.py:50-55` tre classi, `:541` `riavvia_dopo_guasto()`, l'annuncio **prima** del replay. 26 asserzioni |
| 🟠 3 | **Verification** — «tool executed ≠ goal verified» | ✅ **VERA**, e il pacchetto la formula bene. Esistono tre frammenti nella forma giusta e nello scopo sbagliato → ADR-012 |
| 🟠 4 | **Memory provenance** — «da dove arriva questa informazione?» | ⚠️ **VERA ma mal posta.** La domanda utile non è *da dove*, è **chi l'ha detta**. `ANALISI-SENIOR` §4.1④ ha il numero dietro (45 % → 71,9 %) e la cura giusta → fetta 3 |
| 🟠 5 | **Voice reale** — «va verificato col microfono vero» | ❌ **FALSA, chiusa 25 ago.** `acceptance/IL-GIRO-SI-CHIUDE.md`, offline, wake a 8,19 ms, nove difetti trovati accendendolo |
| 🟠 6 | **Cost accounting** | ❌ **FALSA, chiusa 25 ago.** `core/llm/governor.py:276` `registra_voce()`, `:300` `consumo_voce_mese()`, chiamante a `core/engine.py:2272` |
| 🟠 7 | **Settings** — «deve rispettare la separazione core/renderer» | ❌ **FALSA, chiusa 25 ago** — e la separazione che chiede è scritta nell'intestazione del file. `settings.js` sono **429 righe**, non 0 byte |
| 🟡 8 | **MCP** — «solo dopo governance e verification» | ❌ **FALSA, chiuso 25 ago.** `core/mcp/`, `promuovi_mcp()` un nome per volta, `Untrusted.da()`, due eval contro un server vero con sei personalità ostili |

**Tre su otto.** E delle tre, due erano già coperte meglio da
`docs/ANALISI-SENIOR-2026-08-29.md`, che ha le misure e le fonti.

Da aggiungere, e nessuno dei due documenti ce l'aveva: **`core/diario.py:89`
`annota()` non porta nessun id** — wake → STT → T0 → tool → diario non si
ricongiunge. È diventata la fetta 1.

---

## 3. Che cosa il pacchetto porta di suo

Una cosa, e vale il pacchetto intero.

**`09_DYNAMIC_DESKTOP_AND_LAYOUT_ENGINE.md`** — la distinzione fra **guscio
persistente** e **composizione dinamica delle superfici**, con la pipeline
`LayoutIntent → validatore → compilatore → renderer → rollback`. È il primo
documento che dà una forma governabile a «l'LLM compone la scrivania» senza
rompere l'invariante 1.

E la parte migliore, che il pacchetto non sapeva: **metà del compilatore esiste
già.** `core/layout.py` ha schema stretto, `adatta()` che riporta dentro l'area
senza scartare, scrittura atomica e `_metti_da_parte()` che rinomina il file
illeggibile dicendolo. Quattro delle sette proprietà che il documento chiede
sono lì, scritte meglio di come le descrive.

→ **ADR-013**.

Buono anche `06_CLAUDE_OPERATING_PROTOCOL.md`: gerarchia delle fonti, condizioni
di stop, resoconto di fine turno. Ma è, all'80 %, la formalizzazione di ciò che
il progetto già fa. Estratto in `docs/PROTOCOLLO-DI-LAVORO.md`.

---

## 4. Dove contraddice il progetto — quattro punti

**① `docs/CURRENT-STATE.md` sarebbe la settima fonte di stato, e nasce falsa.**
Il pacchetto vieta le fonti duplicate alla propria regola 5 del §06 e poi ne
propone una, sbagliata su cinque voci. **Non adottato**: `STATO-DEI-PIANI.md` è
stato riscritto dal codice e resta l'unica.

**② `03_EXECUTION_PLAN` Fase 11 resuscita i quattro workspace.** «Primary views:
COMMAND · ANALYSIS · VISION · NETWORK · MEMORY · WORKSHOP». Aggiunge la clausola
«semantic modes, not separate desktops», ma ADR-010 li ha aboliti e §26 li ha
trasformati in categorie del catalogo. È una contraddizione **interna** al
pacchetto, e un lettore prende la riga, non la clausola. **Non adottato.**

**③ Multi-monitor come «first-class architectural requirement».** Non è in SPEC,
ADR-005 dice schermo intero, nessun ADR lo prevede. È esattamente
l'allargamento che `ANALISI-SENIOR` §4.6③ misura come primo rischio di
allocazione del progetto. **Fuori perimetro, dichiarato in ADR-013** — con la
nota che `componi(intent, area, corrente)` prende già l'area per parametro,
quindi la strada resta aperta senza costare niente oggi.

**④ «Self-modifying code remains a strategic objective».** `CLAUDE.md`, *Non
fare senza chiedere*: «Eseguire stringhe generate dall'LLM». **Fuori.** Un
layout compilato da uno schema chiuso non è codice generato — ed è precisamente
per questo che ADR-013 è ammissibile e questo no.

**⑤ Fuori elenco: `core/cognition/kernel.py`.** Sarebbe una seconda radice di
composizione accanto a `engine.py`, contro la regola 6 dello stesso pacchetto e
contro l'invariante 17 per la parte che tiene il proprio contesto. **Non
adottato**, e la ragione per esteso è nella nota comune di
`DECISIONI-COGNITIVE.md`.

---

## 5. La tabella del merge — che cosa è stato fatto di ogni file

| file del pacchetto | destino | dove è finito |
|---|---|---|
| `09_DYNAMIC_DESKTOP` | **adottato** | ADR-013 in `DECISIONI-COGNITIVE.md` |
| `02_TARGET_ARCHITECTURE` §3 (contratti) | **adottato, riscritto** — si generalizza `Piano.id` e il pattern `chiesto`/`vivo`, non si creano tipi da zero | ADR-011, ADR-012 |
| `04_EVALUATION` §10–11 (metriche, red line) | **adottato** | `PIANO-JARVIS-COGNITIVO` fetta 4 |
| `06_CLAUDE_OPERATING_PROTOCOL` | **adottato** | `PROTOCOLLO-DI-LAVORO.md` |
| `07_GAPS` §2 (rischi) | **adottato** | `PIANO-JARVIS-COGNITIVO` §0 e §3 |
| `00_MASTER_BRIEF`, `05`, `08` | **fusi**, non aggiunti | `PIANO-JARVIS-COGNITIVO` rev 2 |
| `01_CURRENT_STATE_AUDIT`, `CURRENT-STATE` | **NON copiati** — falsi su cinque voci | riscritti dal codice in `STATO-DEI-PIANI.md` |
| `03_EXECUTION_PLAN` fasi 0–2, 5, 7–10 | **scartate** — lavoro già fatto | — |
| `03_EXECUTION_PLAN` fase 11 | **scartata** — contraddice ADR-010 | — |

---

## 6. La lezione, in una riga

Un documento di pianificazione vale quanto la freschezza della fonte che ha
letto. Questo ne ha letta una di sei giorni e ha prodotto un piano per un
repository che non esisteva più.

**La contromisura non è diffidare dei documenti esterni: è tenere aggiornato il
proprio.**

> ⚠️ E vale anche per casa nostra: `docs/ANALISI-SENIOR-2026-08-29.md`, che è
> un documento molto migliore di questo pacchetto, ha ereditato **dalla stessa
> fonte** il valore di entropia 2,21 — morto da tre giorni, perché
> `DENSITA.json` dice **2,44** e `soddisfatto: true`. Un'analisi che misura
> tutto il resto dal vivo ha sbagliato l'unico numero che ha copiato da un
> documento.
