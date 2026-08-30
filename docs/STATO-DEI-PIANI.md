# Stato dei piani — 30 agosto 2026

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

## 4. Che cosa è aperto davvero — quattro voci

Ordinate per gravità, non per costo. Erano sei; le prime due si sono chiuse il
30 agosto — la traccia e il contratto di verifica — e quelle erano le due
**assenze strutturali** che bloccavano il resto. Le quattro che restano sono
lavoro, non buchi nell'architettura.

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

> ⚠️ **Un difetto trovato scrivendo il verificatore.** `create_file` riferiva
> `bytes: len(a.content)` — un conto di **caratteri** sotto un nome che dice
> byte. Misurato: 52 caratteri accentati sono 62 byte sul disco. Nessuno leggeva
> quel campo, quindi era invisibile — ed è esattamente il tipo di referto che
> ADR-012 dichiara inaffidabile: il tool che parla di sé.

### ③ Le strutture non sono modificabili dalla pagina impostazioni · ❌ APERTO

Residuo di §26.7, sopra. Scene, frasi di wake e radici consentite si cambiano
ancora aprendo il TOML. `imposta_valore` sa scrivere una foglia.

Non è urgente e non blocca niente, ma **il criterio ② del piano precedente
diceva «ogni impostazione», e non è soddisfatto.** Va scritto qui, non lasciato
credere chiuso.

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

### ⑥ Il pilastro 3D è a zero byte · ❌ APERTO — e va deciso, non rimandato

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
| 5 | **ADR-013 — LayoutIntent** | metà del compilatore è già in `core/layout.py` e non la usa nessuno |
| 6 | **Le strutture nelle impostazioni** | chiude il residuo di §26.7 |
| 7 | **La decisione su `model3d.py`** | non è lavoro: è una decisione. Va presa prima di trovarsi a novembre con §17 ancora a zero |

---

## 7. Fonti di questo documento

Codice al commit `29737f2` (30 agosto 2026). `docs/acceptance/` per l'evidenza
misurata. `docs/ANALISI-SENIOR-2026-08-29.md` per i rilievi §4④ e §4⑤ e per i
riferimenti bibliografici. `docs/ANALISI-PACK-V3.md` per il verdetto sul
pacchetto esterno e per la ragione per cui non va reimportato alla cieca.
