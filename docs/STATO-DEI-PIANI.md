# Stato dei piani — 1° settembre 2026

> ## ⚠️ 1° settembre 2026 — il nucleo è stato RIFATTO sul riferimento HUD
>
> Decisione del proprietario: la replica del suo riferimento vince sulla
> specifica dove i due sono in contrasto. Il nucleo di §25 non è stato
> ritoccato — è stato **sostituito**: otto strati concentrici misurati
> (`ui/src/hud/geometria.js`), palette a otto livelli, cinque velocità
> indipendenti, telemetria vera attorno al disco, onda vocale al centro.
>
> **Ambito: il SOLO nucleo.** Scrivania, 19 pannelli, catalogo, finestre e core
> Python non sono stati toccati. Niente React, niente Vite, niente Tauri.
>
> **Le cinque deroghe, con misura e costo del ritorno, stanno in
> `docs/acceptance/NUCLEO-HUD.md`:** invariante 19 (glow, con esenzione
> nominata e **contata** da un test), §25.11 (three.js per il globo L5), invariante 25 con §10.3 «Fondo: immobile» — che
> `CANCELLO-10.6.md` chiamava *l'unica riga mai violata* — §10.6 (classe 2 fuori
> da un pannello) e il tetto di §25.5.
>
> **Che cosa NON è derogato, e ha una prova che gira:** invariante 18 (la
> palette è entrata in §10.1 come **tre gradini**, non come letterali — e uno
> dei tre ha risolto §25.13.5, che con i gradini vecchi non passava in nessuna
> direzione), invariante 23 (nessun «APOGEE: 420.5 KM»: `cpu_percent`,
> `ram_percent`, `package_temp_c`, nodi e consumo veri, in decimale **e** in
> esadecimale sulla stessa immagine), invariante 22, invariante 9, §25.13.5
> (4,48–4,65:1 in tutti e nove gli stati).
>
> **Secondo giro, 1º settembre 2026 — sette difetti trovati GUARDANDO.** Tutti
> dallo scatto, nessuno dal codice: la corona di L8 leggeva come peluria (sei
> guide a 15-18 unità con un testo alto 32 — si sovrapponevano di metà; adesso
> **tre**); la ghiera esterna non c'era (`stroke-width: 1,5` in unità di
> viewBox vale **0,48 px** alla resa); la tela dell'onda era centrata sul disco
> e disegnava la propria linea di base **sopra il nome**; le letture erano
> ancorate a `h/2` come se il nome fosse centrato, e quando l'onda è tornata in
> flusso «MESH» è finito addosso a J.A.R.V.I.S.; le tacche cardinali a
> `--cy-500` prolungavano la scritta; le corone erano **vuote** in ogni scatto
> perché senza core non ci sono eventi (invariante 23), quindi il primo difetto
> era invisibile; e alle letture mancava lo scudo di §25.13.4, così l'anello
> segmentato le tagliava a metà.
> Aggiunti in questo giro: la **ghiera graduata** che chiude lo strumento, le
> **tre corone** alfanumeriche spaziate secondo il corpo del testo, e l'onda
> come **tracciato continuo specchiato** invece che a barre — dove il blueprint
> (§6, «barre verticali simmetriche») e la foto sono in disaccordo, vince la
> foto, perché è la foto la cosa da replicare.
> ⚠️ E **sei backtick** nel template literal CSS di `sfondo.js`, il nono caso.
> `node --check` non li vede; `tests/test_fogli_di_stile.py` sì, in 0,1 s, e
> non era scattato perché non l'avevo eseguito prima di rendere.
>
> ### ⚠️ Aperto e dichiarato
>
> | | |
> |---|---|
> | **F4 — globo 3D** | ✅ fatto: 720 punti su spirale aurea, reticolo `Line2`, retro attenuato al 32 %, nutazione e parallasse. Budget **16,7 ms di mediana** col nucleo in moto a carico massimo — vsync pieno |
> | **entropia** | ✅ **2,40, soddisfatta, margine 0**. ⚠️ Questa riga diceva il falso: la chiamava un residuo «tarato sul nucleo precedente», mentre al commit `18b2e58` era **2,43 e verde** — era una regressione del nucleo nuovo. Recuperata alzando l'inchiostro e mai il fondo, in quattro passi misurati (2,37 → 2,38 → 2,39 → 2,40). Il margine è zero: la prossima cosa che scurisce il nucleo la riapre |
> | **sovrapposizione col riferimento** | ⚠️ **non eseguita** — il file dell'immagine non è sul disco. Il cancello «raggi entro ±2 unità» resta non misurato |
> | **onda vocale** | ⚠️ verificata **solo nello stato vuoto**: `voice.enabled = false`, e accendere il microfono è una decisione |
>
> **Del riferimento non resta fuori niente.** La macchina a stati
> `idle/listening/thinking/speaking/error` c'è, ed è una **vista** sulle cause
> invece di un topic che dichiara lo stato: il core dice fatti, e lo stato è una
> loro combinazione. Tre test tengono in piedi la derivazione — nessun topic la
> dichiara, un solo posto scrive `data-hud`, e l'ordine è una priorità.
>
> ⚠️ **La deroga 6 è RIENTRATA, e §25.13.5 è verde in tutti e nove gli stati**
> — contrasto 3,27-4,65:1, luminanze 67-95 contro un tetto di 105, franco
> +8,5 px. Il centro NON è luminoso: la sfumatura tiene `--cy-900` fin oltre le
> lettere, come il riferimento, e il marchio è a `--cy-600` (a `--cy-500` nel
> solo `speaking`, che è il tetto di §25.5 — non una deroga).
> Il difetto non era nel disegno: **`fissa()` non scriveva `data-hud`**, quindi
> nel banco quell'attributo restava su `idle` e ogni regola che vi si appoggia
> — anche quelle di `error` e `listening`, in foglio da giorni — non veniva mai
> resa. Un banco che non rende ciò che misura dice PASS per assenza del
> fenomeno. Adesso `fissa()` scrive gli stessi ingressi dell'app e lascia
> derivare a `statoHud()`, unico scrittore dell'attributo.
> ⚠️ **Il criterio si misura col core FERMO**: col core vivo un pannello copre
> il centro del nucleo — comportamento voluto — e i due scatti non
> differiscono. È l'opposto di `verifica:densita`, che il core lo pretende
> vivo. Il caso adesso si dichiara (`misurabile: false`) invece di far cadere
> la verifica con un `TypeError`.
>
> ⚠️ Il globo aveva reso §25.13.5 **instabile** — stesse sorgenti, esiti
> diversi — perché la tela WebGL non ridisegna fra le due catture del
> criterio. Corretto: si rende prima di ognuna. Vedi `NUCLEO-HUD.md`.
>
> Il nucleo precedente di questa sessione (sette anelli, mesh, spettrometro) è
> in `git stash`, non distrutto.

> **Perché questo documento esiste, e perché è stato riscritto.**
>
> La versione precedente era del **24 agosto** e lasciava cinque voci aperte.
> Sono state chiuse tutte fra il 25 e il 28 agosto, e il documento non è stato
> aggiornato. Fra il 24 e il 30 agosto **è rimasto in giro dicendo il falso su
> cinque punti su cinque**, ed è stato letto come se fosse corrente: il
> `JARVIS_OS_Research_Implementation_Pack_v3` — un pacchetto di pianificazione
> esterno — ne ha ricopiato le cinque voci una per una e le ha presentate come
> lo stato del repository al commit `25a9c32c`. Erano già chiuse a quel commit.
>
> **La causa non è il pacchetto: è questo file.** Un documento di stato che non
> si aggiorna è peggio di un documento di stato che non esiste, perché il primo
> viene creduto.
>
> Verificato contro il repo al commit `29737f2`, leggendo il **codice**, non i
> documenti. Ogni riga porta il file e la riga che la sostiene.

---

## 0. Come si legge questo file

È l'**unico** documento di stato corrente del progetto. Tutti gli altri piani
in `docs/` sono cronologia e portano un banner che lo dice.

Gerarchia delle fonti quando due documenti sono in disaccordo:

```
CLAUDE.md
> docs/SPEC.md (sezione corrente)
> il codice
> docs/acceptance/ (l'evidenza misurata)
> questo file
> qualunque altro piano in docs/
```

Se il codice e un documento di accettazione sono in disaccordo, **ci si ferma
e lo si dichiara**. Non si sceglie in silenzio.

Etichette usate qui:

| | |
|---|---|
| ✅ **CHIUSO** | criterio verificato, evidenza in `docs/acceptance/`, commit fatto |
| ⚠️ **RESIDUO** | la voce è chiusa, ma dentro c'è qualcosa di dichiarato aperto |
| ❌ **APERTO** | non implementato |
| 🚫 **SUPERATO** | non va più fatto, e si dice perché |
| ❓ **NON VERIFICATO** | non c'è evidenza sufficiente. **Non è la stessa cosa di ✅** |

---

## 1. Il vecchio ordine di lavoro è finito

`STATO-DEI-PIANI` del 24 agosto chiudeva con sette voci in ordine di priorità.
**Sono chiuse tutte e sette.** Questo è il fatto principale di questo
documento, ed è la ragione per cui il progetto oggi non ha un piano: quello
vecchio è esaurito.

| # | voce | esito | evidenza |
|---|---|---|---|
| 1 | Fixture dei dati vivi nel protocollo §5 | ✅ | `DENSITA.json` porta `"provenienza": "fixture:4d5edf35cfdb64af"`; `tests/test_fixture_scrivania.py`; `acceptance/FIXTURE-CHE-COSA-CONGELA.md` |
| 2 | ADR-003 completo — `transient` e `repeated` | ✅ 27–28 ago | `core/llm/claude_t1.py:50-55`, `:541`; `acceptance/ADR-003-LAMNESIA-SI-ANNUNCIA.md` |
| 3 | Voce col microfono vero | ✅ 25 ago | `acceptance/IL-GIRO-SI-CHIUDE.md` |
| 4 | Emisfero del globo `--fill-1` → `--fill-2` | ✅ | entropia da 2,21 a **2,44** |
| 5 | ADR-004 — secondi Deepgram in `conso/` | ✅ 25 ago | `core/llm/governor.py:276`, `:300`; `acceptance/ADR-004-CONTARE-PRIMA-DI-SPENDERE.md` |
| 6 | §26.7 pagina impostazioni + scrittura `tomlkit` | ✅ 25 ago | `ui/src/panels/settings.js` — 429 righe; `acceptance/LE-IMPOSTAZIONI-HANNO-EFFETTO.md` |
| 7 | ADR-007 — MCP | ✅ 25 ago | `core/mcp/`; `acceptance/ADR-007-MCP.md` |

---

## 2. Le cinque voci, una per una — con la prova

Questa sezione esiste perché le cinque voci sbagliate hanno viaggiato. Chiunque
le ritrovi altrove — nel pacchetto v3, in una vecchia copia di questo file, in
una conversazione — deve poterle chiudere qui senza rileggere il codice.

### ① ADR-003 — recovery T1 · ✅ CHIUSO 27–28 agosto

Le tre classi esistono e girano:

```
core/llm/claude_t1.py:50-55   Uscita.AUTH / TRANSIENT / REPEATED
core/llm/claude_t1.py:96-97   SOGLIA_RIPETUTI = 3 · FINESTRA_RIAVVII_S = 600.0
core/llm/claude_t1.py:478     classifica(returncode, stderr)
core/llm/claude_t1.py:522     _degrada()  — annuncia, e il degrado sopravvive a stop()
core/llm/claude_t1.py:541     riavvia_dopo_guasto() — reinietta i SOLI fatti fissati
```

**L'annuncio va prima del replay**, e l'ordine è pinnato da un test: se il
replay fallisse, l'utente ha comunque sentito che la conversazione non c'è più.

Il difetto vero era peggiore di quello dichiarato dall'ADR, ed è stato trovato
da `scripts/orfani.py`: `riavvia_dopo_guasto` **non aveva un chiamante in
produzione**, e `ask()` faceva `if not self.vivo: await self.start()` dentro il
`try` — cioè T1 moriva, la chiamata dopo ne apriva uno nuovo con la sessione
vuota, e JARVIS rispondeva con la stessa voce avendo perso tutto. Adesso le due
maniere di non essere vivo si distinguono: `_proc is None` si avvia e basta,
`returncode` non nullo passa dal riavvio che annuncia.

Prove: `tests/test_supervisor.py` (26 asserzioni),
`tests/test_t1_non_risorge_in_silenzio.py`.

> ⚠️ **RESIDUO — e va tenuto in vista.** `docs/SPEC.md` §16 lascia aperta la
> *domanda 2*: i due freni al loop di riavvio stanno in **due posti diversi**
> (`Supervisore.puo_riavviare` e la guardia dentro `ClaudeT1.ask()`), e quello
> dichiarato non è quello che gira. Inoltre la soglia «3 riavvii in 600 s» è il
> numero dell'ADR, **non una misura**: nessun esercizio, nessun dato.

### ② ADR-004 — costo dei provider vocali · ✅ CHIUSO 25 agosto

```
core/llm/governor.py:276   registra_voce(tier, provider, secondi, fallback=, esito=)
core/llm/governor.py:300   consumo_voce_mese() — aggrega dal disco, per provider
core/engine.py:211         dir_conso=self._memoria.conso   (senza, _registra usciva subito)
core/engine.py:2272        il chiamante vero
core/engine.py:574         "consumo": … — la riga arriva al pannello via state.snapshot
```

`tier` vale `stt`/`tts` per la voce e `t1`/`t2` per l'LLM: `conso/` resta **un
registro solo**. Un test verifica che le righe LLM non entrino nel conto della
voce — sommarle darebbe secondi di audio che nessuno ha pronunciato.

Prove: `tests/test_governor.py`, `tests/test_conso_vede_la_voce.py`.

> ⚠️ **RESIDUO.** Il contatore **non ha mai contato un secondo vero**: su questa
> macchina non c'è chiave Deepgram ed `edge-tts` è gratuito
> (`core/llm/governor.py:286-289`). Esiste per esserci prima che il costo
> esista. E l'**opzione C** di ADR-004 — tetto mensile che degrada al locale —
> resta «da rivalutare dopo il primo mese di misura». Nessun mese, nessuna
> rivalutazione.

### ③ §26.7 — pagina impostazioni · ✅ CHIUSA 25 agosto

`ui/src/panels/settings.js` è di **429 righe**. Il file lo dice da sé, nella
prima riga del proprio commento: *«Questo file **era** da 0 byte dalla Fase 0.»*

Rispetta l'invariante 1 per costruzione, non per disciplina: il renderer
**chiede**, `window.jarvis.impostaValore` manda una domanda al core, e di là c'è
`imposta_valore` con `side_effect=True`, che apre la conferma di §6.2 col
percorso risolto. Fra il clic e il file ci sono un'allowlist derivata dallo
schema, una validazione pydantic e un umano che dice di sì
(`core/engine.py:1471-1481`).

Cinque interruttori restano **bloccati** di proposito (§26.7 regola 4): quelli
che decidono se un sottosistema *esiste* — un microfono che si apre, del codice
che si esegue, una telecamera, quale parte del disco è visibile.

Prove: `tests/test_impostazioni_scrittura.py`, `tests/test_settings.py`,
`acceptance/SEZIONE-26-7-LA-PAGINA-IMPOSTAZIONI.md`,
`acceptance/LE-IMPOSTAZIONI-HANNO-EFFETTO.md`.

> ⚠️ **RESIDUO, e questo è il più sostanzioso dei quattro.** Le **strutture** —
> scene, frasi di wake, radici consentite — non compaiono fra le modificabili:
> `imposta_valore(chiave, valore)` sa scrivere una **foglia**, non una lista.
> Il criterio ② di `PIANO-JARVIS-COGNITIVO` chiedeva «*ogni* impostazione di
> `settings.toml` modificabile dalla pagina». Oggi è «ogni foglia scalare».
> È lavoro dichiarato, non fatto. Vedi §4③ qui sotto.

### ④ Voce col microfono vero · ✅ CHIUSA 25 agosto

`acceptance/IL-GIRO-SI-CHIUDE.md`: *«per la prima volta una frase detta da una
persona ha attraversato tutta la catena e ha mosso lo schermo»*, **offline**.
Traccia reale `wake_trigger … latenza_ms=8.19` → `t0_ui`. Mediana del wake su
24 trigger veri: **7,76 ms**. Latenza di `parse()` su 133 frasi in
`T0-CORPUS.json`, tenuta come misura distinta.

Accendere l'interruttore ha scoperto **nove difetti**, sette dei quali su nove
pezzi della catena erano rotti. Sono elencati nel documento. È la ragione per
cui accendere presto vale più che pianificare a lungo.

### ⑤ ADR-007 — MCP · ✅ CHIUSO 25 agosto

```
core/mcp/promozione.py:155   promuovi_mcp(server, nome_tool, side_effect) -> Tool
core/mcp/promozione.py:177   descrizioni incapsulate in Untrusted.da(f"mcp:{…}")
core/mcp/promozione.py:204   e i risultati anche
core/engine.py:1145-1147     self._mcp = await monta_mcp(s.mcp)
core/engine.py:587, :2351    nello snapshot e nell'arresto
```

Un nome per volta: un server non può registrare un albero di tool. Provato
contro un server **vero** (`tests/mcp_finto.py`) con sei personalità, fra cui
una che si prende `read_file` e una che inietta istruzioni.
`tests/eval_mcp.py`, `tests/test_mcp_montaggio.py`.

> ⚠️ **RESIDUO.** La spec MCP è cambiata sotto i piedi il **28 luglio 2026**:
> `core/mcp/client.py` non fa `server/discover`, `Mcp-Session-Id` è stato
> rimosso dalla spec, elicitation e sampling non ci sono. Rilievo di
> `ANALISI-SENIOR` §4.3.

---

## 3. La densità è conforme — e anche questo era scritto male

`docs/acceptance/DENSITA.json`, generato da `scripts/densita.mjs --esito`,
dichiara `"soddisfatto": true` e `"falliti": []`.

| criterio | misura | soglia | |
|---|---:|---:|---|
| entropia | **2,44** | 2,40 | ✅ margine +0,04 |
| deviazione standard | 35,0 | 32 | ✅ |
| `L>60` riempito | 28 % | 25 % | ✅ |
| caldo | 3,7 % | 3–6 % | ✅ |
| barra | 63,8 % | 25 % | ✅ |
| dock | 24,2 % | 20 % | ✅ |

> ⚠️ **Il valore 2,21 è morto.** Compare ancora nella versione precedente di
> questo file **e in `docs/ANALISI-SENIOR-2026-08-29.md` §1 e §2③**, che l'ha
> ereditato da qui invece di leggere `DENSITA.json`. È la stessa contaminazione
> che ha colpito il pacchetto v3, per la stessa causa. Da oggi:
> **`DENSITA.json` è la fonte, questo file la cita e basta.**

E resta vero ciò che la versione precedente diceva sulla soglia: **2,40 non è
il riferimento**. `SOGLIE` in `densita.mjs` dichiara la propria provenienza —
«a metà strada fra la nostra rev 5.7 e il più povero dei due riferimenti».
`famiglia-a/01` misura H 3,32 · dev 55,7. Passare 2,40 significa passare la
barra che il progetto si è dato, restando **0,88 bit** sotto il bersaglio su cui
`DIVARIO-PREMIUM` è costruito. Le due frasi vanno dette insieme.

> **Decisione da prendere** (`ANALISI-SENIOR` §10①): 2,40 è un **cancello** o un
> **obiettivo**? Oggi fa entrambe le cose, e questa è la definizione di un
> criterio che non misura.

---

## 4. Che cosa è aperto davvero — sette voci, e tre sono chiuse

Ordinate per gravità, non per costo. Erano sei; le due **assenze strutturali**
che bloccavano il resto — la traccia e il contratto di verifica — si sono
chiuse il 30 agosto, e con loro la misura della memoria. Delle sette di oggi
**quattro sono chiuse**, due portano un residuo dichiarato, e una sola è un
buco nell'architettura.

⚠️ La settima, `⑥`, è stata **aggiunta il 31 agosto**: ADR-013 non aveva una
voce qui, e il suo residuo viveva solo in un documento di accettazione. È lo
stesso modo in cui questo file ha detto il falso cinque volte su cinque fra il
24 e il 30 agosto.

### ① La traccia end-to-end · ✅ CHIUSA 30 agosto 2026

`core/diario.py:89` — `annota(flusso, **campi)` — **non porta nessun id**. La
riga vocale (`core/engine.py:783-789`) porta `intento`, `args`, `ok`, `da`,
`strada`, `errore` e nient'altro. `registry.invoke` (`core/engine.py:811-817`)
non ne ha uno. Conseguenza: **wake → STT → T0 → tool → diario non si può
ricongiungere.** Non esiste il modo di chiedere «che cosa è successo in quel
turno», e senza quello nessuna misura di comportamento è possibile.

**Il pezzo però esiste già, ed è cablato bene:**

```
core/tools/confirm.py:71     Piano.id — uuid4, su una dataclass frozen
core/tools/confirm.py:110    propagato in fs.confirm
core/engine.py:860, :865     e in fs.result e nei log
core/engine.py:322-324       _catture: dict[str, Future] — «senza correlazione
                             due domande vicine si scambierebbero le risposte»
```

Correlazione domanda → risposta **completa**, e confinata alle conferme
distruttive. È stata **generalizzata**, non reinventata → **ADR-011**.

**Com'è finita.** `core/traccia.py`, `Origine` a cinque valori, propagazione
obbligatoria su `Diario.annota()` e opzionale-con-guardia sulle due porte del
registry, `ToolResult.traccia_id` timbrato su ogni ramo — anche quelli falliti.

```
core/traccia.py                          Traccia, Origine (5 valori)
core/voice/pipeline.py  _turno()         il conio del turno vocale
core/engine.py          _gesture_intento, _imposta_da_ui,
                        _scrivanie_cambiate, _consolida_di_notte
core/protocolli.py      Ronda.esegui     inoltra la traccia a `invoca`
scripts/diario.py       --traccia ID     la ricostruzione (criterio 2)
scripts/orfani.py       --diario         una riga senza traccia è un orfano
```

Prove: `tests/test_la_traccia_non_si_perde.py` (26 test, 8 sabotaggi provati
uno per uno), `docs/acceptance/LA-TRACCIA-NON-SI-PERDE.md`.

> ⚠️ **RESIDUO, e sono quattro, dichiarati.**
> **①** Il criterio 1 è **parziale**: `wake_trigger` è una riga di *log*, non di
> diario, quindi si ricongiunge nel journal via `contextvars` — una join fra due
> registri, non N righe in uno.
> **②** **Il giro col microfono vero non è stato fatto.** `NON VERIFICATO`.
> **③** Il percorso `gesture` non è provabile dal vivo su questa macchina:
> MediaPipe non è installato, e la telecamera non si apre.
> **④** Il **consolidamento notturno** scrive in `initiatives/` con
> `"traccia": null` — dichiarato in `SENZA_TRACCIA`, non nascosto. È il passo
> più piccolo che viene dopo.

> ⚠️ **Due difetti trovati misurando, e nessuno dei due era ADR-011.**
> **①** `scripts/diario.py` **cadeva** sulle righe con `intento=None` — quelle
> che spiegano perché non è successo niente. 8 righe su 61 nel diario vero, e
> il comando moriva con uno stack trace. Anteriore ad ADR-011.
> **②** `TestGliInvariantiNonDivergono` confrontava `CLAUDE.md` con SPEC §20
> fermandosi al primo fence, e da quando `CLAUDE.md` ha un blocco di codice suo
> guardava **7.827 caratteri su 11.388**. Una divergenza dopo quel punto sarebbe
> passata inosservata — e ce n'era una.

### ② Il contratto di verifica · ✅ CHIUSO 30 agosto 2026

«Tool eseguito» ≠ «azione riuscita» ≠ «obiettivo verificato». Oggi la
distinzione vive come **prosa umana**: le intestazioni `**Criterio:** /
**Esito:**` dei documenti in `docs/acceptance/`, rese obbligatorie da
`SPEC.md:2480` — *«Se non puoi verificare un criterio, lo DICHIARI»*. Funziona
perché la scrive una persona.

A runtime il pattern esiste in **tre punti**, nella forma giusta e nello scopo
sbagliato:

| dove | forma | che cosa manca |
|---|---|---|
| `core/engine.py:563` | `wake_model` (vivo) accanto a `wake_model_chiesto` (atteso); SPEC rev 5.42: *«la divergenza vale `fail`»* | è **un campo solo** |
| `core/doctor.py` + §16.1b | `ok` / `WARN` / `fail` per sottosistema | è per **sottosistemi**, non per azioni |
| `core/protocolli.py:101` | `Esito(nome, eseguito, cambiato, frase, errore)` + `firma()` | confronta osservato con osservato-**di-prima**. Nessun campo *atteso* |
| `core/tools/files.py` `_trash` | cerca dove è finito il file e riferisce `verificato: bool` | ⚠️ **il quarto, trovato il 30 agosto: e poi restituisce `ok=True` comunque.** Il campo c'era, era corretto, e non cambiava niente |

Nessuna azione di tool poteva finire in `NON VERIFICATO` invece che in
`ok=True`. → **ADR-012**, chiuso.

**Com'è finita.** `core/verifica.py` con `Verdetto` a **quattro** valori — non
`Esito` a sei: in `core/` `Esito` è già il nome di tre classi, e due dei sei
valori non li emetteva nessuno — e `Verifica`, con `fonte` obbligata.

```
core/verifica.py                Verdetto (4 valori), Verifica
core/tools/registry.py          Tool.verifica, ToolResult.verifica,
                                _verifica() e _bloccata()
core/tools/files.py             create_file → os.stat sul percorso del PIANO
                                trash_path  → i due os.path.exists
core/tools/impostazioni.py      imposta_valore → il TOML riletto con tomlkit
core/doctor.py                  la riga VERIFICA: 3/25, distruttivi 6/9
```

La regola che lo rende non decorativo: **un tool senza verificatore torna
`NON_VERIFICATO`, non `RIUSCITO`.** E il criterio 3 è passato da «rifiutato in
revisione» a **imposto dal registro**: un verificatore la cui `fonte` nomina il
proprio tool viene declassato, perché rileggere attraverso lo stesso codice
prova solo che il codice è coerente con sé stesso.

Prove: `tests/test_eseguito_non_e_verificato.py` (24 test, 8 sabotaggi provati
uno per uno), `docs/acceptance/ESEGUITO-NON-E-VERIFICATO.md`.

> ⚠️ **RESIDUO, e sono quattro, dichiarati.**
> **①** **Sei tool distruttivi su nove restano scoperti** — `copy_path`,
> `create_folder`, `move_path`, `organize_folder`, `pin_fact`, `write_topic`.
> Dichiarano `NON_VERIFICATO`, che è lo stato corretto, e `jarvis doctor` li
> nomina uno per uno. È il debito, ed è **misurato**.
> **②** La metà «i commenti ci sono ancora» di `imposta_valore` è **debole**:
> senza un conteggio di *prima* verifica solo che non siano spariti tutti.
> Dichiarata debole invece che spacciata per forte.
> **③** Nessun verificatore è stato provato contro un guasto **reale** del
> filesystem — disco pieno, permessi tolti a metà, `os.replace` interrotto.
> Provati contro il caso riuscito e contro il non-eseguito, non contro il
> rotto-a-metà, che è quello in cui un verificatore vale di più.
> **④** Il costo di `_verifica` sul percorso dei tool in sola lettura **non è
> stato cronometrato**.

> ✅ **Quattro correzioni il 31 agosto**, dalla revisione dello stesso giorno —
> `docs/acceptance/ESEGUITO-NON-E-VERIFICATO.md` §⑧. Tre erano di questo ADR e
> nessuna era dichiarata:
> **①** l'atteso di `imposta_valore` veniva dal **referto del tool**, mentre il
> gemello `create_file` vieta esattamente questo per iscritto — due verificatori
> nello stesso ADR con regole opposte. Adesso viene dagli argomenti in entrambe
> le forme.
> **②** il controllo sull'autocertificazione stava **fuori dal `try`**: un
> verificatore che *ritorna* un non-`Verifica` alzava `AttributeError` fra la
> scrittura distruttiva e `_riferisci` — azione avvenuta, nessun `fs.result`,
> nessuna riga di diario. Non raggiungibile con i tre verificatori di oggi; il
> tipo non lo impediva.
> **③** `scripts/diario.py` non rendeva `verdetto` né `osservato` — zero
> occorrenze: il criterio 1, «si vede nel diario», era vero solo aprendo il
> JSONL a mano. Due colonne, e il verdetto che smentisce l'`ok` in maiuscolo.
> **④** `doctor` contava i verificatori **dichiarati**: tre
> `lambda: non_verificata("todo")` lo avrebbero portato da `warn` a `ok` con
> zero coperti a runtime. Adesso il registro conta i **verdetti prodotti**, e il
> check nomina chi ha girato senza mai concludere.
> Quattro sabotaggi, quattro rossi. Test **2039 → 2057**.
> ⚠️ Non provato sul registro vero: il diario di questa macchina non ha nessuna
> riga con un verdetto, perché il core non ha eseguito un tool dopo il 30 agosto.

> ⚠️ **Un difetto trovato scrivendo il verificatore.** `create_file` riferiva
> `bytes: len(a.content)` — un conto di **caratteri** sotto un nome che dice
> byte. Misurato: 52 caratteri accentati sono 62 byte sul disco. Nessuno leggeva
> quel campo, quindi era invisibile — ed è esattamente il tipo di referto che
> ADR-012 dichiara inaffidabile: il tool che parla di sé.

### ③ Le strutture nella pagina impostazioni · ⚠️ RESIDUO RISTRETTO

Era: scene, frasi di wake e radici si cambiavano solo aprendo il TOML, perché
`imposta_valore` sapeva scrivere una foglia.

**Com'è finita.** Si cambiano dalla pagina **un elemento per volta**, mai la
lista: `ElementoMessage` porta un verbo e un record, e il record passa da due
schemi — il tipo dichiarato dell'elemento e `Settings` intero — prima di
toccare il disco. Così la ragione scritta in `core/ws_server.py` — una lista
raggiungerebbe tomlkit «senza passare da nessuno schema di sezione» — resta
vera alla lettera invece di essere cancellata per comodità.

⚠️ **`fs.allowed_roots` è uscita dalle bloccate di §26.7 regola 4**, ed è una
decisione presa il 30 agosto. La condizione: la conferma mostra il percorso
**RISOLTO**, come riga sua nel piano — `~/../..` e un symlink si scrivono
uguali e arrivano altrove. La difesa che si perde è «dalla pagina non si può
nemmeno chiedere»; quella che resta è l'invariante 3.

Prove: `tests/test_le_strutture_si_cambiano.py` (41 test, 9 sabotaggi provati
uno per uno — **due non producevano rosso, e hanno scritto due test nuovi**),
`docs/acceptance/LE-STRUTTURE-SI-CAMBIANO.md`.

> ⚠️ **RESIDUO — e adesso è uno e mezzo.**
> **①** **Tre liste su cinque restano fuori**: `ui.scene`, `mcp.servers` e
> `protocolli` hanno record **annidati**, e `ElementoMessage.elemento` è un
> `dict[str, str]`. Il criterio ② della rev 1 diceva «ogni impostazione»; oggi
> è «ogni foglia scalare e ogni lista piatta».
> **②** ✅ **Chiuso il 31 agosto**, e non era una pignoleria: vedi il riquadro
> qui sotto.
> **③** ✅ **Chiuso il 31 agosto, col Signore che parla.** Una frase aggiunta
> col tool sveglia JARVIS **detta in aria**: 6 giri su 6 con voce sintetica, e
> poi `latenza=8,9 ms` con la **voce umana**, picco 0,0412 contro una soglia di
> 0,0120. Le due metà — una persona che sveglia JARVIS (25 agosto, §2④, 24
> trigger su frasi già nel file) e una frase aggiunta dalla pagina — erano
> provate separatamente; adesso sono provate **insieme**.
> ✅ **E la ripetibilità è misurata**: dieci ripetizioni guidate dal tono,
> **dieci successi**, mediana **8,54 ms** (min 7,19, max 15,71). Contro 8,97 di
> mediana della voce sintetica e 7,76 del 25 agosto.
> ✅ **E i due modi della latenza sono spiegati.** Non sono la porta
> (`AcceptWaveform` contro `FinalResult`), non è la CPU addormentata — un metro
> di taratura dice che sulla chiamata lenta era più veloce — e non è il rumore:
> silenzio digitale e rumore di stanza costano uguale. È **periodico nella
> durata dell'enunciato**: sei blocchi lenti, sei veloci, periodo 240 ms.
> Valgono 6,3 ms su una latenza di risveglio di ~1.500 ms, cioè lo 0,4 %, e non
> si toccano.
> ✅ **E il meccanismo è verificato — e NON è la potatura**, che era la mia
> ipotesi: `--prune-interval` vale 25 frame del decodificatore, cioè 750 ms, e
> portarlo a 5 lascia il disegno identico banda per banda. È
> **`--frames-per-chunk`**, il pezzo con cui si valuta la rete neurale: 24
> frame d'ingresso × 10 ms = 240 ms, e portandolo a 36 il periodo passa da 12 a
> 18 blocchi. Causale, non correlazione. Il sorgente di Vosk lo conferma:
> `SingleUtteranceNnet3IncrementalDecoder`, e il finale chiama
> `InputFinished()` → `AdvanceDecoding()` → `FinalizeDecoding()`.
> ✅ **E i 120 ms della banda cara sono il CONTESTO DESTRO della rete.** Non
> scala col pezzo perché non è del pezzo: i pezzi in attesa alla chiusura sono
> `ceil(T/p) − floor((T−R)/p)`, cioè 2 in una finestra larga `R`. Misurata
> ferma a 6 blocchi su cinque dimensioni del pezzo (24…60); previsione
> falsificabile — a pezzo 12 la bimodalità deve sparire — **confermata**
> (escursione 0,82 ms contro 6-7). E i `<TimeOffsets>` letti da `final.mdl`
> danno contesto destro **12** frame, sinistro −24.
> ⚠️ E il rumore di fondo di questa stanza tocca la soglia del VAD.

> ✅ **Il giro dal vivo con Electron è stato fatto**, e ha trovato **quattro**
> difetti con 44 test verdi: si chiedeva di approvare ciò che sarebbe stato
> rifiutato; ciò che si approvava non era ciò che si scriveva (il piano
> risolveva il percorso, il disco riceveva la stringa grezza); il doppione non
> si vedeva; e aggiungere una radice riscriveva l'intero elenco espanso,
> trasformando `~/Documenti` in un percorso assoluto. È la seconda fetta di
> fila in cui il confine trova ciò che i test non vedono.

> ✅ **E anche il RIFIUTO della conferma**, il 31 agosto. Era il quarto residuo:
> il giro approvava sempre, e che cliccare «rifiuta» lasciasse il file intatto
> era provato in Python, non attraversando la finestra. Adesso lo è — file
> **identico byte per byte**, conferma chiusa, la frase non c'è.
> ⚠️ **E ha trovato un quinto difetto.** L'operazione rifiutata non lasciava
> **nessuna riga di diario**: `_ESITO`, il gancio di §6.2, girava solo sul ramo
> approvato. Il log aveva il rifiuto, il registro che una persona rilegge no —
> e `Verdetto.BLOCCATO`, che ADR-012 ha introdotto proprio per questo caso, non
> poteva arrivarci per la via della pagina. Adesso **un piano, una risposta**,
> da qualunque origine e con qualunque esito, e `_bloccata` timbra anche la
> traccia di ADR-011, che su quel ramo nasceva `None`.

> ✅ **E il MICROFONO VERO**, il 31 agosto — l'ultimo `NON VERIFICATO` di questa
> voce. La catena intera: `imposta_valore` → conferma → tomlkit → disco →
> **inotify** → `Engine._ricarica_frasi` → `PhraseWake.set_frasi` →
> altoparlante → **aria** → microfono → VAD → Vosk → `wake_trigger`, con
> l'azione giusta. Prima con voce sintetica (15,5 ms), poi **con la voce del
> Signore** (8,9 ms). `scripts/prova_microfono.py`,
> `docs/acceptance/IL-MICROFONO-VERO.md`.
> ⚠️ **E ha trovato il sesto difetto, che era il più grave dei sei.**
> Il ricarico a caldo, attraverso l'**inotify vero**, non funzionava affatto.
> inotify manda `IN_OPEN` anche a chi **legge**, l'antirimbalzo era sul fronte
> di **salita**, e `imposta_valore` legge il TOML prima di riscriverlo: la
> lettura si mangiava la finestra e la scrittura veniva scartata. **Ogni**
> impostazione cambiata dalla pagina restava sul disco senza mai arrivare al
> processo. Due giri identici tranne una `read_text()`:
> `avvisati=[5]` contro `avvisati=[]`.
> Nessun test lo vedeva perché tutti chiamavano `store.reload()` a mano — cioè
> il residuo ② saltava esattamente il pezzo rotto, ed è **per questo** che era
> un residuo. Corretto in `core/settings.py`: una lettura non è un cambio, e
> l'antirimbalzo passa sul fronte di **discesa**.

### ④ Il modello dell'utente e l'attribuzione in memoria · ⚠️ RESIDUO

**L'attribuzione è chiusa il 30 agosto. Il profilo a slot no.**

Rilievo di `ANALISI-SENIOR` §4.1, con il numero dietro. `topics/` contiene
riassunti di sessione e una lista piatta di fatti fissati. Manca la cosa in
mezzo — un profilo a slot — e manca **l'attribuzione al confine della
memoria durabile**: il consolidamento notturno non distingue fra *ciò che
il Signore ha detto* e *ciò che JARVIS ha proposto e nessuno ha contestato*.

Misura di riferimento (PASB, arXiv 2607.10526): la contaminazione a valle passa
dal **45 % al 71,9 %** quando un'affermazione attraversa quel confine, su tutti
e dodici i modelli testati.

La cura è **un campo, non un sistema**: ogni riga consolidata porta
`dichiarato` / `proposto-e-accettato` / `osservato`, e solo la prima classe può
diventare un fatto fissato.

**Com'è finita.** ⚠️ Non era un campo: la classe non si può chiedere all'LLM
(`PROTOCOLLO-DI-LAVORO` §6), quindi viene dalla **costruzione** — il
consolidamento riassume **due volte**, una per corpus, e la sezione
`dichiarato` può contenere solo frasi che il modello ha visto in quella
chiamata. Costa due spawn T2 per sessione invece di uno.

⚠️ **E la regola non mordeva dove il piano diceva.** `Consolidatore.esegui()`
scrive solo in `topics/` e non ha mai toccato `_fatti-fissati.md`: l'unico che
ci scrive è `MemoryStore.fissa()`, chiamato da **`pin_fact`**, che T1 può
invocare. È lì il confine, ed è il passaggio che PASB descrive. Il criterio del
piano sarebbe stato vero senza scrivere una riga di codice.

```
core/memory/attribuzione.py   Attribuzione (3 valori), classifica() + la PROVA
core/memory/store.py          fissa(fatto, attribuzione) — rifiuta il resto
core/memory/consolidate.py    due riassunti + le azioni, che non passano da
                              nessun modello
core/tools/memory.py          pin_fact: deduce, e la conferma MOSTRA da dove
                              viene il fatto
```

Prove: `tests/test_chi_lo_ha_detto.py` (20 test, 8 sabotaggi provati uno per
uno), `docs/acceptance/CHI-LO-HA-DETTO.md`.

> ⚠️ **RESIDUO — e sono cinque.**
> **①** **Manca ancora il profilo a slot**, che è l'altra metà di questa voce:
> `topics/` ha riassunti e fatti fissati, e in mezzo non c'è niente.
> **②** La soglia lessicale (0,6) è **scelta, non misurata**: non esiste un
> corpus di fatti fissati su cui tararla.
> **③** Il confronto è **lessicale, non semantico**: «ne ho un paio» e «sono
> due» sono due cose diverse per questo codice. Sbaglia nella direzione che
> costa meno — rifiuta — ma sbaglia.
> **④** `pin_fact` guarda **solo la sessione di oggi**: un fatto dichiarato
> ieri risulta `osservato` e viene rifiutato.
> **⑤** Il consolidamento non è mai stato eseguito con un **T2 vero** in questa
> fetta: è misurato che i due prompt contengano corpora disgiunti — la parte
> sotto il nostro controllo — non che il modello li separi davvero.

### ⑤ La misura di quanto JARVIS ricorda e di quanto resta sé stesso · ✅ CHIUSA 30 agosto 2026

Non esistevano `tests/eval_memoria.py` né `tests/eval_persona.py`. C'erano
1.829 test sul **codice** e zero sul **comportamento**: il giorno in cui il
recupero della memoria fosse sceso sotto soglia, o la persona avesse deviato,
**nessun test sarebbe diventato rosso**. `ANALISI-SENIOR` §7④ lo elenca come uno
dei sette modi in cui il progetto muore.

**Com'è finita.** La prima lettura, in `docs/acceptance/TERMOMETRO.json`:

| | 10 topic | 210 topic |
|---|---|---|
| memoria, domande **letterali** @5 | 1,00 | 1,00 |
| memoria, domande **parafrasate** @5 | **0,00** | **0,00** |
| memoria, rifiuto corretto | 1,00 | 1,00 |
| memoria, affollamento | trova | **PERDE** |
| persona, giudice **meccanico** | — | **11/12** |
| persona, giudice **modello** | — | **11/12** |

⚠️ **La previsione «funziona con dieci file e non con duecento» aveva sbagliato
asse.** Non è la scala: le letterali reggono a duecentodieci. È la **forma** —
le parafrasi fanno 0,00 anche con dieci file, cioè la ricerca per sottostringa
non ha mai funzionato. Il difetto di scala è più stretto: il `break` al primo
`limite` in ordine alfabetico, che ha la sua riga (`affollamento`).

⚠️ **La sonda bocciata solleva una domanda sulla persona, non sul codice.** Alla
richiesta di aprire un pannello, T1 spiega di non avere strumenti invece di
confermare di aver sentito. `config/voice-persona.md` chiede entrambe le cose, e
in questo caso si contraddicono — T1 è raggiunto **solo** quando T0 ha mancato,
cioè quando l'azione non avverrà davvero. È una decisione, non una misura.

Prove: `tests/eval_memoria.py` (gratis, gira con tutto il resto),
`scripts/termometro.py --persona` (spende, una volta), `tests/eval_persona.py`
(rilegge il JSON), `docs/acceptance/IL-TERMOMETRO.md`.

> ⚠️ **RESIDUO — e sono cinque.**
> **①** **Nessuna soglia**, quindi il banco oggi non può diventare rosso per un
> peggioramento: diventa rosso solo se si rompe, o se la persona cambia sotto le
> citazioni. È il prezzo dichiarato della prima lettura.
> **②** **Il ri-ancoraggio non è stato fatto**, di proposito: ContextEcho misura
> la deriva su sessioni da 3.746 turni, qui il diario ne ha 61 in tre giorni.
> Prima il termometro, poi la cura.
> **③** La misura della persona è **rumorosa**: la sonda `dissenso` è stata
> bocciata al primo giro e promossa al secondo con la stessa rubrica. Una sola
> lettura non è una misura di deriva.
> **④** Il corpus della memoria è **sintetico** e le venti domande sono mie: i
> due topic veri di questa macchina sono privati e non si committano.
> **⑤** Dodici sonde non coprono tutta la persona: restano fuori «anticipi»,
> l'ironia, la lunghezza scelta dalla domanda, il comportamento
> all'interruzione.

### ⑥ La composizione delle superfici · ✅ CHIUSA 31 agosto — era una DERIVA, non un buco

ADR-013 è **chiuso** dal 30 agosto: `LayoutIntent` non porta geometria, la
composizione manuale vince, un intento rifiutato non muove un pixel e lo
dichiara. 41 test verdi, e il ciclo §11.7 dal vivo ha trovato quattro difetti
che quei test non vedevano.

⚠️ **Ma in esercizio l'allowlist è VUOTA, e ogni composizione viene rifiutata.**
Misurato il 31 agosto leggendo il file vero.

`Engine._pannelli_ammessi()` deriva i nomi componibili dalle **scene
dichiarate**, che è una lista chiusa che il core possiede davvero:

```python
return frozenset(p.id for s in self.settings.ui.scene for p in s.pannelli)
```

e `~/.config/jarvis-os/settings.toml` — 3.173 byte, 27 agosto — ha `[ui]` con
tre sole chiavi:

```
[ui]
target_fps = 60
grid_px = 110
gap_px = 8
```

**Nessun `[[ui.scene]]`.** Le due occorrenze della parola «scene» in quel file
sono `action = "scene:avvio"` dentro due frasi di wake, che è un altro
meccanismo — e i commenti accanto lo dicono già.

Quindi `componi()` rifiuta tutto, e lo dice dalla parte giusta: «nessuna scena
dichiarata in settings.toml», non «pannelli sconosciuti».

⚠️ **E i test restano verdi**, perché girano su `config/settings.toml` — la
configurazione **spedita col progetto**, che di scene ne dichiara tre (righe
113, 133, 143). È una funzione provata su una configurazione che sulla macchina
del Signore non è mai stata usata: il caso peggiore di test verde, perché non è
sbagliato, è solo su un altro mondo.

Era già dichiarato in `docs/acceptance/LA-COMPOSIZIONE-SI-PROPONE.md` §⑤ punto
5, per esteso. **Non era qui**: ADR-013 non aveva una voce in questa sezione, e
in §6 la riga 5 lo dà chiuso senza residui. È esattamente il modo in cui questo
documento ha detto il falso cinque volte su cinque fra il 24 e il 30 agosto —
la verità scritta in un documento di accettazione e non nel documento di stato.

> **Scelta la strada (a)**, il 31 agosto: le tre scene sono state dichiarate
> in `~/.config/jarvis-os/settings.toml`. L'altra — cambiare la sorgente
> dell'allowlist — voleva un ADR nuovo, perché il core non conosce `moduli.js`
> e `core/settings.py:276` dichiara per iscritto che non deve.

**Com'è finita.** Le tre scene del template, alla lettera, con in testa il
commento che dice a che cosa servono davvero. L'allowlist è passata da **zero a
otto** pannelli, e le tre superfici si compongono contro la configurazione vera:

```
allowlist: agenti, anelli, archivio, globo, news, periodica, sorgente, telemetria

briefing     COMPOSTA   news 0·640  telemetria 640·640  agenti 1280·480
diagnostica  COMPOSTA   telemetria 0·640  agenti 640·640  anelli 1280·480
officina     COMPOSTA   globo 0·960 (alto 1000)  sorgente 960·480  archivio 1440·480
```

⚠️ **E non era un buco nel progetto: era una DERIVA di questa macchina.**
`INSTALLA.md:44` dice `cp config/settings.toml ~/.config/jarvis-os/`, quindi
un'installazione nuova le scene le avrebbe. Il file del Signore è del **27
agosto** — nato da una copia fatta prima che §26.6 esistesse — e non è mai
stato riallineato.

E non erano le sole a mancare: confrontando le sezioni, il file di esercizio non
ha nemmeno `[code]` e `[meteo]`. Quelle due sono **inerti** — i default dello
schema coincidono con ciò che il template dichiara — ma sono la stessa cosa.

> ⚠️ **Il residuo VERO è un altro, e resta aperto.** Il `settings.toml` di
> esercizio deriva dal template ogni volta che il template guadagna una
> sezione, e **non se ne accorge nessuno**: né lo schema, che ha un default per
> tutto, né `jarvis doctor`, che le impostazioni le legge ma non le confronta
> con quelle spedite. Qui è costato una funzione che girava solo nei test per
> una settimana. Non è stato risolto: sarebbe un controllo nuovo, e non è
> quello che era stato chiesto.

**E `ui.scena_iniziale = "avvio"`**, messa subito dopo su richiesta. Decide che
cosa compone la scrivania al **primo** avvio, quando non c'è un layout salvato
da rimettere — senza, la scrivania apre *tutto*, ed è così che si è scoperto
che «aprire tutto» non è comporre: quattordici pannelli su una piastrellatura
completa diventano una cascata, e di quattordici se ne leggono due.

⚠️ **Oggi è inerte, e va detto.** `~/.local/share/jarvis-os/layout.json` esiste
(30 agosto), e `ui/src/app.js` applica la scena iniziale solo sul ramo
`!ripristinato`: il ripristino vince. La riga conta dal giorno in cui quel file
non ci fosse — un profilo nuovo, un data dir ripulito, un primo avvio vero.

Il refuso è impedito allo schema, non alla disciplina: `scena_iniziale = "avio"`
non carica affatto, e lo dice per esteso —

```
ui.scena_iniziale = 'avio' non e' fra le scene dichiarate:
['avvio', 'briefing', 'officina']
```

— che è la ragione per cui quel validatore esiste: al primo avvio si vedrebbe
solo una scrivania vuota, e nessuno collegherebbe le due cose.

**E il primo avvio è stato provato**, togliendo `layout.json` di mezzo e
lanciando core ed Electron veri — `scripts/prova-primo-avvio.mjs`, che nasce
qui perché l'effetto di quella riga **non si vede mai** su una macchina in uso:
il ripristino vince sempre, e per guardarla bisogna togliere quel file.

```
scenaCorrente : "avvio"          barra: SCENA avvio · TUTTO · 6 pannelli
visibili      : agenti, cartella, file, globo, news, telemetria
layout.json   : riscritto, scena="avvio"
```

Non è la cascata: sei finestre disposte, non quattordici a scaletta.

⚠️ **Ma la scena ne dichiara cinque e sullo schermo ce ne sono sei, e non sono
le stesse.** `anelli` — dichiarato — non compare; `file` e `cartella` — non
dichiarati — sì. `applicaScena` nasconde ciò che non è nella scena e mette in
`ignorati` ciò che `apri()` rifiuta, quindi il meccanismo per entrambe le
direzioni c'è: perché scatti qui non è stato indagato, e lo dichiaro invece di
supporlo.

Il set di pannelli è però **identico** a quello che il Signore aveva salvato —
`telemetria, globo, agenti, news, file, cartella` — quindi il primo avvio non
toglie né aggiunge niente rispetto a ciò che c'era. Il `layout.json` originale è
stato rimesso al suo posto (identico, confrontato byte per byte); quello scritto
dal primo avvio è messo da parte.

### ⑦ Il pilastro 3D è a zero byte · ❌ APERTO — e va deciso, non rimandato

```
core/tools/model3d.py              0 byte
ui/src/three/math/extrude.js       0 byte
ui/src/three/math/spline.js        0 byte
ui/src/three/components/node-graph.js  0 byte
```

`CLAUDE.md`, prima pagina, promette «genera modelli 3D». §17 della SPEC ci
dedica trenta pagine. **Zero byte e trenta pagine sono la stessa cosa detta in
due modi opposti.**

> **Decisione da prendere** (`ANALISI-SENIOR` §10⑦): `model3d.py` è nel
> progetto o esce dalla SPEC?

---

## 5. Che cosa NON va fatto — e resta superato

Invariato rispetto alla versione precedente, ripetuto qui perché è il tipo di
voce che risorge.

| | 🚫 |
|---|---|
| **I quattro workspace** | superati da ADR-010: una scrivania sola. I quattro domini sopravvivono come **categorie del catalogo**, non come pagine. ⚠️ Il pacchetto v3 li ripropone in `03_EXECUTION_PLAN` Fase 11 sotto i nomi COMMAND / ANALYSIS / VISION / NETWORK / MEMORY / WORKSHOP |
| **Il giro §11.7 sui «18 componenti»** | i componenti a schermo sono **sei**. La stima più cara di due piani, costruita su un numero sbagliato di tre volte |
| **Il modulo Media** | chiuso **come impossibile**, non rimandato: le tre radici consentite contengono zero file immagine, contati. Costruirlo significherebbe inventare contenuto — invariante 23 |
| **La colonna laterale** | **rifiutata**, misurata e scartata in `2e6d640`: «NON ENTRA — è una somma» |
| **`SPEC-25` come strada** | l'esito è stato raggiunto, l'implementazione descritta no. Il documento è storico dove contraddice il codice |

---

## 6. L'ordine di lavoro che ne esce

Il piano operativo, con le fette e i criteri, è in
**`docs/PIANO-JARVIS-COGNITIVO.md`** (rev 2). Qui solo la sequenza e il perché.

| # | cosa | perché qui |
|---|---|---|
| ~~1~~ | ~~**ADR-011 — la traccia**~~ | ✅ **chiusa il 30 agosto.** Non erano «poche righe»: otto file di `core/`, due script e una guardia AST a tre regole — perché `registry.invoke` si passa anche **per riferimento**, e una guardia che guarda solo le chiamate resta verde su un percorso scoperto |
| ~~2~~ | ~~**ADR-012 — il contratto di verifica**~~ | ✅ **chiusa il 30 agosto.** `Verdetto` a quattro valori, tre verificatori con fonte indipendente, e il criterio 3 imposto dal registro invece che dalla revisione. Il debito è contato: `jarvis doctor` dice `3/25`, distruttivi scoperti `6/9` |
| ~~3~~ | ~~**Attribuzione nel consolidamento**~~ | ✅ **chiusa il 30 agosto.** Non un campo: due riassunti, uno per corpus, perché la classe non si può chiedere all'LLM. E il confine vero non era il consolidamento ma `pin_fact` |
| ~~4~~ | ~~**`eval_memoria` e `eval_persona`**~~ | ✅ **chiusa il 30 agosto.** Prima lettura in `TERMOMETRO.json`. Il ri-ancoraggio resta fuori di proposito: prima si misura la deriva, poi si cura |
| ~~5~~ | ~~**ADR-013 — LayoutIntent**~~ | ✅ **chiusa il 30 agosto.** Il ciclo §11.7 ha trovato quattro difetti che 41 test Python non vedevano: il layout attraversa cinque confini, e i test ne guardavano uno. ⚠️ **Residuo trovato e chiuso il 31 agosto** — vedi §4⑥: in esercizio l'allowlist era vuota e ogni composizione veniva rifiutata. Era una deriva del `settings.toml` di questa macchina, non un buco: le tre scene sono state dichiarate e le tre superfici si compongono |
| ~~6~~ | ~~**Le strutture nelle impostazioni**~~ | ✅ **chiusa il 30 agosto.** Un elemento per volta, mai la lista; `fs.allowed_roots` esce dalle bloccate con il percorso RISOLTO nella conferma. Residuo: tre liste su cinque hanno record annidati e restano fuori |
| 7 | **La decisione su `model3d.py`** | non è lavoro: è una decisione. Va presa prima di trovarsi a novembre con §17 ancora a zero |

---

## 7. Fonti di questo documento

Codice al commit `29737f2` (30 agosto 2026). `docs/acceptance/` per l'evidenza
misurata. `docs/ANALISI-SENIOR-2026-08-29.md` per i rilievi §4④ e §4⑤ e per i
riferimenti bibliografici. `docs/ANALISI-PACK-V3.md` per il verdetto sul
pacchetto esterno e per la ragione per cui non va reimportato alla cieca.
