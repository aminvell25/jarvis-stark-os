# J.A.R.V.I.S. OS — Specifica di progetto

**Rev 5.41 · agosto 2026 · uso strettamente personale**

Documento **autosufficiente**. Sostituisce ogni revisione precedente.
Questo file va in `docs/SPEC.md`: è il riferimento che Claude Code consulta.

## Emendamenti dopo la chiusura della rev 5.0

| Rev | Data | Cosa | Sezioni toccate |
|---|---|---|---|
| 5.41 | 29 ago 2026 | **La conferma di §6.2 aveva due meta' promesse e mai mantenute, e sono l'unico posto dove una persona agisce su una credenza falsa a proposito di operazioni DISTRUTTIVE.** ① **`fs.result` non esisteva**: la stringa compariva in tutto il repository solo in due righe di PROSA — il diagramma di §6.2 e quello di `core/tools/confirm.py`. Il Signore approvava di spostare duecento file, la finestra si chiudeva al clic, e cio' che accadeva dopo non tornava indietro; se il ventesimo file non si muoveva, per la scrivania era andata bene. Adesso l'esito va sul socket con lo STESSO id della domanda, e nel diario come atto `azione` — nessuna forma nuova da rendere. ② **La scadenza era silenziosa**: il TTL vive nel core e non ne usciva niente, quindi la finestra restava a schermo a chiedere di approvare qualcosa che nessuno avrebbe piu' eseguito, e il clic finiva in `conferma_ignorata`. Adesso il core annuncia `fs.confirm_expired` e la scrivania chiude QUELLA finestra. ⚠️ **Il conto alla rovescia NON si fa nel renderer**: `scade_fra_s` viaggiava sul filo e in `ui/` non lo nominava nessuno — zero `setTimeout` in 310 righe — e farne un contatore metterebbe un secondo produttore dello stesso fatto, in disaccordo col primo appena la scheda va in pausa. Il campo e' TOLTO | **§6.2**, invariante 3 |
| 5.40 | 29 ago 2026 | **`stderr=PIPE` era aperto e non lo leggeva nessuno**, e ci stavano due difetti. ① **Trecento kilobyte fermano T1 per sempre**: il tubo di Linux tiene 64 KiB, asyncio ne pompa altrettanti nel proprio `StreamReader` anche senza lettori, e poi il controllo di flusso mette in pausa, il tubo si riempie e il figlio si blocca sulla `write`. **Misurato**: 200 000 byte passano, 300 000 no; e con un `ClaudeT1` vero, A/B sul solo lettore, *senza* BLOCCATO a 8 s contro *con* 11 ms. Il guasto e' silenzioso — `ask()` va in timeout, JARVIS degrada, riavvia, e il processo nuovo si ferma allo stesso punto. ② **Due criteri di rilevamento auth su tre erano irraggiungibili**: `classifica` ne ha tre — `returncode == 41`, «authentication» e «unauthorized» nello stderr — e `riavvia_dopo_guasto` la chiamava con UN argomento. Misurato su un figlio che muore dicendo `Unauthorized` con `returncode 1`: `auth` con la cura, **`transient` com'era** — cioe' un token scaduto preso per un guasto passeggero e riprovato in ciclo, che e' cio' che §5.6 vieta. Cura: un lettore per processo che tiene la CODA (`TETTO_STDERR = 65 536`, un tubo pieno), chiuso col processo, e l'attesa dell'EOF prima di classificare — altrimenti si legge un buffer a meta' proprio quando i byte mancanti sono quelli che spiegano la morte | **§5.6**, **ADR-003** |
| 5.39 | 28 ago 2026 | **La degradazione non-auth di T1 ha un proprietario, ed e' `ClaudeT1`.** Il `Supervisore` ne tiene il REFERTO — bus, `stato_doctor()`, contatore di vita — e lo riceve per notifica su un canale suo (`riferisci(EventoT1)`), diverso da quello dell'auth. **Misurato prima**: dopo tre riavvii veri di T1 `jarvis doctor` diceva `nominal, riavvii: 0` e sul bus non arrivava niente — §5.6 «due meta', e quella che riferisce era muta» a ruoli invertiti. ⚠️ **Un buco di §5.6 sull'altra strada di rilevamento**: §5.6 osserva lo STREAM, ma un token che scade fra due turni fa MORIRE il processo, e li' non arrivava niente — zero advisory, zero uscita 41, doctor a `nominal`. ⚠️ **`ClaudeT1` non era conforme ad ADR-003**: finestra di 5 minuti invece di 10, soglia al QUARTO guasto invece che al terzo, orologio non monotono — e il test che la fissava passava per caso. ⚠️ **Il cancello dell'auth si chiudeva sullo STATO**, quindi una degradazione non-auth spegneva §5.6, e la rev 5.38 lo rendeva permanente: adesso le due cause sono due campi indipendenti e `stato` e' derivato. **`Supervisore.su_riavvio` e' TOLTA** con classifica, `puo_riavviare`, la reiniezione, le due frasi doppie e le due costanti — proprieta' MIGRATE prima della cancellazione. ⚠️ Resta aperto: `classifica` non riceve lo `stderr`, e `stderr` e' un `PIPE` che nessuno legge | **§5.6**, **§16.1b**, **ADR-003** |
| 5.38 | 28 ago 2026 | **Decisione: per i riavvii ripetuti di T1 il core RESTA VIVO.** Il codice d'uscita 42 e' tolto — dal supervisore, dalla unit systemd e dai test che lo fissavano. §5.6 e §16.1b dichiaravano gia' che in `degraded_llm` restano vivi frasi-comando, T0, file e telemetria: uscire spegneva tre sottosistemi sani perche' il quarto non partiva. L'uscita 41 per l'autenticazione NON e' toccata, e resta l'unico codice su cui il core si ferma. ⚠️ **Il freno del loop non era mai stato il 42** — e non e' nemmeno `Supervisore.puo_riavviare`, come la prima stesura di questa riga diceva: misurato, ha **un solo lettore in `core/`**, ed e' `su_riavvio`, che non ha chiamanti. Il freno che GIRA e' `ClaudeT1._degradato` piu' la guardia di `ask()`, dentro il processo — funziona anche col core avviato a mano, fuori da systemd. ⚠️ **La unit installata va reinstallata**: `_check_unit` confronta l'impronta dell'intero file e dira' `fail` finche' non si esegue `packaging/installa.sh` | **§16**, §5.6, §16.1b, ADR-003 |
| 5.37 | 28 ago 2026 | **«JARVIS sta parlando» poteva restare vero per il resto della sessione, e nessuno poteva vederlo.** In `parla()` e in `interrompi()` l'abbassamento di `_sta_parlando` stava DOPO un `await`, in sequenza: `chiudi()` attende che la coda del dispositivo si svuoti — `await proc.wait()` su `pw-play` — e in quella finestra un `cancel()` o un errore di riproduzione portavano via la riga di sotto. **Misurato**: bandiera `True` col lucchetto della voce gia' libero, cioe' per sempre, e da li' §15 regola 2 chiude il gate a ogni giro. ⚠️ **E `conoscibilita()`, scritta il giorno prima proprio per questo, dichiara i tre campi `noto`** — e ha ragione: vede un produttore che manca o che e' rotto, non uno che mente. Percio' la garanzia sta in un `finally` annidato e non nell'osservabilita'. Nel barge-in e' la stessa specie nel posto peggiore: `TTSDeepgram.interrupt()` fa un `ws.send`, e un websocket caduto portava via tutte e tre le righe di stato. **`LinuxAudioIO.sta_riproducendo` e' TOLTA**: zero lettori, e quattro punti scritti affermavano il falso su di lei. **ADR-003 rientrava dalla porta accanto**: `_degrada()` chiama `stop()`, che azzera `_proc`, quindi al turno dopo la guardia era falsa e `ask()` apriva una sessione VUOTA in silenzio — l'amnesia che ADR-003 esiste per vietare, per la strada piu' frequente (il timeout). E la frase «ho conservato le Sue preferenze» era doppiamente falsa: niente era stato riavviato, e `fatti_fissati` non era cablato. ⚠️ **`Supervisore.su_riavvio` resta un orfano dichiarato APERTO**: cablarlo accende `esci(42)` contro §5.6 e §16.1b, e la decisione non si prende dentro un turno di implementazione. ⚠️ **Quella decisione e' stata presa il giorno dopo, rev 5.38**: il 42 non c'e' piu', quindi il blocco descritto qui non esiste piu' — resta aperta solo la domanda di PROPRIETA' | **§15**, **§7.4**, **ADR-003**, §5.6 |
| 5.36 | 27 ago 2026 | **§3.4 descriveva una sandbox che non esiste piu'.** «ro-bind `/`, rw-bind `~/JARVIS/`» e' il disegno della Fase 1; **ADR-008 l'ha sostituito** con una radice vuota (`--tmpfs /`, solo l'interprete) e nessuno ha corretto la tabella. Oggi il codice generato non scrive fuori dalla propria tmpfs — piu' stretto di cio' che §3.4 prometteva, quindi non e' un buco di sicurezza: e' una **specifica che mente su cio' che il codice fa**. Trovato rispondendo alla domanda «perche' la workspace sta fuori dal progetto?»: la giustificazione data — «e' l'unico percorso scrivibile della sandbox» — veniva da questa riga, ed era la specifica e non il codice. `~/JARVIS` resta cio' che `fs.workspace` dichiara: la prima radice consentita, dove lavorano i tool di file di §6.1 | **§3.4** |
| 5.35 | 27 ago 2026 | **Una flotta di sei agenti, una revisione avversariale, e sette difetti chiusi — quasi tutti «scritto, provato, mai congiunto».** ⚠️ **§11.9 non era misurabile**: cinque giri sugli stessi sorgenti davano entropia 2,300–2,430 (soglia 2,4), riempito 23,10–28,00 (soglia 25), dock 12,6–24,2 (soglia 20) — **uno su cinque passava**, e il giro che passava era il profilo committato in `2745cb2`. Lo scatto aspettava il silenzio dei DATI, non la scena ferma: il dock veniva fotografato mentre si riempiva. Con `attendiScenaFerma()` cinque giri danno numeri identici alla terza cifra, e da qui un numero di §11.9 descrive il disegno invece del momento dello scatto. ⚠️ **§15 — il gate non poteva lasciar passare NIENTE**: `Contesto.pannello_a_schermo_intero` non aveva un produttore e `None` vale come divieto. Il produttore non e' stato scritto — `GeometriaPannello.massimizzato` esiste da §26.2, la scrivania lo riempie da WinBox e pydantic lo valida: mancava il **lettore**. Idem per `sta_parlando`, che ora arriva per FUNZIONE e si legge a ogni giro: passarne il valore lo fisserebbe a «zitto». **§16 — le chiavi potevano finire nei log**: nessun `structlog.configure()` in `core/`, quindi `redact_secrets` non era installato da nessuna parte. La revisione ha poi trovato che si giudicava con `str()` mentre entrambi i renderer stampano con `repr()`. **§7.2 — le frasi di richiamo cambiano a caldo**, e il cambio aspetta il confine dell'enunciato: la garanzia era scritta in `chiudi()` e non era imposta, e col modello vero un deposito a meta' enunciato faceva sparire la frase in **59 posizioni su 93**. **§5.3 — `--allowedTools` non e' un confine, e' una richiesta**: misurato, `Bash(echo ...)` passa senza comparire in nessuna delle due allowlist dichiarate, mentre `ls` e `cat` che ci sono non passano. `Edit` tolto: non serviva a nessuno dei tre chiamanti. **§3.2 — il pannello diario** rende le tre forme di un'azione; il ciclo §11.7 ha bocciato la prima stesura, che ripeteva la stessa frase due volte. E lo **scanner degli orfani** torna nel repo, con una baseline e la risoluzione degli alias che gli mancava. 1508 -> 1648 test | **§11.9**, **§15**, **§16**, **§7.2**, **§5.3**, **§3.2** |
| 5.34 | 27 ago 2026 | **§5.5 — `initiatives/` era una cartella in sola scrittura.** La docstring di `registra_iniziativa` dice «visibile al risveglio» dalla Fase 4, e **nessuno leggeva**: il file il cui unico scopo e' essere letto al risveglio non aveva un lettore. Adesso `MemoryStore.iniziative_dal()` e `core/memory/risveglio.py`, e quando la scrivania si collega JARVIS dice cosa ha fatto mentre non c'era. ⚠️ **Il resoconto NON passa da un modello**: e' composto dai dati con una tabella di frasi, e non e' un risparmio — cio' che JARVIS dice di aver FATTO non deve poter essere inventato. Il riassunto di una conversazione lo fa un modello; il rendiconto delle proprie azioni no. Un test confronta i tipi di iniziativa che il core registra davvero con la tabella delle frasi, e diventa rosso invece di lasciare a JARVIS qualcosa che non sa raccontare. «Niente da riferire» si dice lo stesso — il silenzio non e' un resoconto — ma **al piu' una volta al giorno**: il confine e' `PERIODO_S` di §5.5, non un numero nuovo, perche' l'unica cosa che JARVIS fa da solo ha periodo giornaliero. ⚠️ Due difetti trovati **dal vivo**: la riga finiva nel diario due volte (mia + quella del turno che la pronuncia -> flusso `azione`, che e' un fatto diverso da `dialogo` e resta anche a voce spenta), e il resoconto non deve dipendere da `self._voce`, o con la voce spenta — la predefinita di §7.1 — il risveglio sarebbe muto. Provato: primo avvio 1 resoconto, secondo avvio 0. 1491 -> 1508 test | **§5.5**, **§3.2** |
| 5.33 | 27 ago 2026 | **§5.5 — la memoria aveva la meta' in uscita vuota, e tre difetti la tenevano cosi'.** `topics/` e `initiatives/` erano a **zero file** su un sistema in esercizio da giorni. **① Un'attesa invece di un recupero**: `_consolida_di_notte` dormiva fino alle 04:00, e un `asyncio.sleep()` non sopravvive a un riavvio del processo — misurato, **27 riavvii in tre giorni**, e in sette giorni nemmeno uno scatto, solo il timer armato. Adesso `Consolidatore.saltato()` legge il timbro su disco all'avvio; `PERIODO_S = 24 h` non e' scelto, e' il periodo che §5.5 dichiara. **② Due T2 costruiti e azzerati nella STESSA funzione**: `Engine.__init__` costruiva `_t2_meta` e `_t2_conso` e centoquaranta righe dopo li rimetteva a `None`, con un commento che descriveva una composizione spostata da tempo. Quindi **`brief_me` e `needs_attention` non hanno mai potuto spawnare nulla — dal commit che li ha collegati** (`92c0ec4`, «nessun intento senza strada»): la strada c'era e finiva su un null. **③ Il motivo di un consolidamento fallito non arrivava nel journal**, solo sull'advisory: con la scrivania scollegata spariva, ed e' sparito davvero. ✅ **Prima notte attraversata**: `topics/sessione-2026-08-26.md` scritto da un modello vero, `initiatives/2026-08-27.jsonl` con 38 turni, 0,153 USD, 44,4 s. Il riassunto ha isolato da solo il difetto STT della sera prima. ⚠️ Una sessione su due non consolidata, motivo **ignoto**: e' esattamente cio' che ③ rende leggibile la prossima volta. 1477 -> 1491 test | **§5.5**, **§7.6** |
| 5.32 | 27 ago 2026 | **«Jarvis non mi sente»: un turno appeso rende JARVIS sordo, e il battito era cieco proprio li'.** Alle 00:55:19 un turno e' partito, la cattura e' finita alle 00:55:27, e poi piu' niente per **quattro minuti**. Misurato: `pw-record` in `anon_pipe_write`, **zero byte in tre secondi**, e lo snapshot che diceva `"microfono": "aperto"`. **① Lo STT non aveva un tetto**: `async for grezzo in ws` su un socket che tace senza chiudersi aspetta per sempre. `stt_deepgram.py` non conteneva **un solo** `wait_for`, mentre il TTS gemello ne aveva uno dal 26 agosto. Adesso `TETTO_RECV_S = 20.0`, **lo stesso numero e per la stessa misura**: stesso socket, stesso fornitore, stessa rete. **② Il danno non resta nel provider**: `_su_trigger` e' atteso DENTRO l'`async for` del microfono, quindi un turno appeso ferma il ciclo audio e la pipe si riempie. **③ Il battito del 26 agosto era cieco nel caso che lo produce**: la bandiera `_in_turno`, scritta perche' non gridasse al lupo a ogni conversazione, gli impediva di vedere una conversazione che non finisce — l'avevo scritta io e non le avevo dato una fine. Adesso `TETTO_TURNO_S = 118 s`, che **non e' scelto**: e' la somma dei tetti gia' dichiarati — cattura 8, `recv` STT 20, una riga di T1 90. Resta fuori il tempo di parlare, e non e' una svista: a 150 parole al minuto sono **295 parole**, e la persona chiede «una o due frasi». ⚠️ **Difetto architetturale APERTO e non corretto**: il ciclo audio si ferma per TUTTO il turno, quindi anche una risposta lunga e legittima riempie la pipe. Il tetto rende la sordita' temporanea, non la elimina | **§7.5**, **§7.3**, **§16** |
| 5.31 | 26 ago 2026 | **§18.3 emendata su richiesta esplicita: il microfono e' attivo SOLO dentro l'ambiente di JARVIS.** Diceva «sempre attivo per il wake», e lo era: il core gira sotto systemd ventiquattro ore e JARVIS rispondeva a finestra chiusa. Il segnale e' la **connessione della scrivania**, non la visibilita': nascosta va bene. Conta solo chi si **dichiara** scrivania — `ruolo` e' un `Literal`, quindi `ws_probe.py` non accende niente; se bastasse una connessione qualunque sarebbe una denylist travestita. ⚠️ Il flusso si **chiude davvero**: `pw-record` termina e la spia del microfono si spegne — scartare i blocchi terrebbe accesa la spia, che e' l'unica cosa che l'utente vede senza chiedere. Il perimetro che ne risulta e' piu' STRETTO di prima. Nello snapshot il microfono dice «sospeso: nessuna scrivania», **prima** del battito: un microfono chiuso apposta non e' un microfono muto, e un allarme che suona quando tutto va bene e' il modo piu' rapido di far ignorare gli allarmi. ⚠️ Trovato **eseguendo la bocciatura**: `len(aperture) == 1` provava che il flusso non si era RIAPERTO, non che si fosse CHIUSO — la proprieta' dichiarata non era provata da nessuno, e ora c'e' un contatore di chiusure. E i test della pipeline perdevano un compito con un generatore infinito quando fallivano: la suite non falliva, si **appendeva**. 1441 -> 1457 test | **§18.3**, **§7.1** |
| 5.30 | 26 ago 2026 | **Il primo comando detto davvero al microfono, e il registro che taceva.** Il Signore ha detto «apriti i pannelli telemetria»; JARVIS ha risposto «Vedo, Signore. Mi occupo del caricamento della telemetria» e non e' successo niente. Nel diario **otto righe di `dialogo` e zero di `azione`**: per sapere se T0 avesse anche solo visto la frase ho dovuto eseguire il parser a mano. **§7.6 nota 4 — l'imperativo prende l'enclitico**: apri/aprimi/aprila/apriti, e il plurale «pannelli» non era ammesso dov'era «pannello». Si allarga solo dove l'oggetto e' un'allowlist, ed e' quella a salvare «apriti cielo» — non la prudenza. **§7.6 nota 5 — ogni enunciato lascia una riga** con la strada presa (`t0`/`t1`/`nessuna`); `strada` non si deriva da `azione`, che non distingue «delegato» da «caduto». Trovata scrivendolo: `if self._t1 is None: return` faceva sparire l'enunciato senza una riga. **Il quasi-comando si registra e NON si dice**: misurati 8 falsi positivi su 53 frasi conversazionali = **15,1 %**, una su sette porterebbe a JARVIS un «nessun comando riconosciuto» dentro un discorso. ⚠️ **T1 non ha mentito**: «Me ne occupo» e' la frase che §5.7 gli PRESCRIVE. Falsa e' la riga sopra — «quelle azioni le fa il sistema prima di arrivare a te» — perche' T1 e' raggiunto soltanto quando T0 ha mancato. Difetto **aperto**, non emendato: il testo e' dell'utente. 1441 test (erano 1412), corpus T0 157 verdi, zero frasi rubate prima e dopo | **§7.6**, **§5.7** |
| 5.29 | 26 ago 2026 | **Cinque punti chiusi in cinque commit, tutti della stessa famiglia: pezzi scritti, provati, mai congiunti.** Trovati con una **scansione** invece che per caso — uno script che per ogni definizione pubblica di `core/` conta i richiami fuori dal modulo e fuori dai test: 487 definizioni, 22 orfane. **§7.6 — i cinque intenti senza esecutore** (`bedb995`, `92c0ec4`): `set_volume`, `mute`, `brief_me`, `needs_attention`, `doctor` erano nella grammatica dalla Fase 3 e `esegui_t0` li rifiutava; JARVIS riconosceva la frase e non faceva niente, indistinguibile da «non mi ha sentito». Nasce `INTENTI_CORE`, terza allowlist. Il volume e' **di JARVIS e non del sistema** — guadagno sul PCM, perche' il mixer di PipeWire e' fuori dalla sua finestra — e a volume 0 non si riproduce affatto, o `sta_riproducendo` resterebbe vero e le regole 2 e 3 di §15 leggono quello. Aggiunto `unmute`, che mancava. Con «non parlarmene piu'» (§15 regola 5) l'insieme degli intenti senza destinazione e' **vuoto**. **§5.5 — la memoria girava a vuoto** (`436b009`): `registra_turno` senza chiamanti (`sessions/` vuota), `Consolidatore.esegui` senza scheduler, `contesto_per_t2` senza chiamanti. Si nascondevano a vicenda: azionando il consolidatore non avrebbe trovato niente da consolidare. ⚠️ **Da oggi la trascrizione va su disco** — non l'audio, §18.3 resta vero. E collegando `contesto_per_t2` e' venuto fuori che **non poteva funzionare**: passava il compito INTERO a `cerca()`, che e' per sottostringa. **§12 — ARGUS senza chiamanti** (`be0ce40`): la classe, `ArgusCaptureResponse` (validata e scartata, `on_capture` non passato) e `catturaEInvia` in `app/main.js`. Due tool: `ask_state` — la «scorciatoia che quasi tutti mancano», costo zero — e `read_screen`, che torna gia' avvolto. Un id per richiesta e un timeout di 5 s, perche' il ponte **non risponde affatto** se la finestra e' distrutta. **§5.6 — due gestori e quello che riferisce era muto** (`9ea5c96`): `Supervisore.su_evento` non riceveva un evento, quindi `jarvis doctor` avrebbe detto `auth ok` con T1 gia' degradato e il core non sarebbe uscito col codice 41. Adesso un proprietario solo, e T1 tace quando lui ha gestito. **§15 — il gate non era il collo** (`78d6000`): misurato sullo stesso scatto di 57 item, **0,42 news/ora prima, 1,33 dopo**, con un tetto di 3 che non morde ne' prima ne' dopo. A strozzare era la lista di argomenti, vuota nel **75 %** dei casi. ⚠️ Raggruppare **non estrae meglio**: per frase il richiamo scende (0,450 contro 0,520); il guadagno e' per unita' di tempo, perche' la finestra portava al modello una battuta su undici. 1304 test verdi (erano 1223). **Quinta occorrenza di §11.7 regola 4** in questo arco — un test vero per il motivo sbagliato, trovato eseguendo la bocciatura. Restano **11 orfani**, e tre sono veri: `Governor.riprendi` (T2 sospeso non riprende mai), `GpuScheduler.can_admit` (§16 «rifiuta il caricamento» non e' imposto), `gestures.emetti` (le gesture non producono intenti nel core). ⚠️ **UNA FRASE DI QUESTA RIGA E' FALSA, corretta alla rev 5.37**: «a volume 0 non si riproduce affatto, o `sta_riproducendo` resterebbe vero e le regole 2 e 3 di §15 leggono quello». §15 legge `VoicePipeline.sta_parlando`, una bandiera della pipeline; `LinuxAudioIO` non e' mai stato nella catena e `sta_riproducendo` non aveva un solo lettore. La REGOLA resta e la giustificazione cambia: non si paga un processo per scrivere silenzio (85 ms di processo per 29 ms di audio) | **§5.5**, **§5.6**, **§7.6**, **§12**, **§15** |
| 5.28 | 26 ago 2026 | **Il «batch» di §15 adesso ACCUMULA — e nella stessa riga c'era un secondo difetto piu' grave.** `if ora - self._ultimo < self._batch_s and self._argomenti` faceva due cose sbagliate: **scartava** le battute dentro la finestra invece di rimandarle (con 600 s, fino a dieci minuti di conversazione persi per estrazione), e **`and self._argomenti` spegneva il limitatore** quando l'estrazione non trovava niente — 162 spawn su 215 danno lista vuota — cosi' ogni battuta faceva uno spawn: **dieci battute in dieci secondi, dieci spawn** contro un tetto di 15/ora. I due si nascondevano a vicenda. Cura unica: il cancello e' `_ultimo` (da quanto non si chiede), non `_argomenti` (se si e' trovato qualcosa). **Misura richiesta, prima e dopo: battute al modello 2/11 → 11/11, perse 9 → 0.** ⚠️ **La formula della cadenza NON e' toccata**: era giusta, il difetto era a valle. Forma di accumulo scelta: **la seconda** — prima battuta subito, le altre a fine finestra — che conserva la latenza dopo un silenzio e lascia valida la misura di haiku su frasi singole; prezzo dichiarato: due ingressi di produzione da misurare invece di uno. **Tetto della coda**: dichiarato NON derivabile dai nostri numeri (150 parole/min, 7 caratteri/parola vengono da fuori come il pavimento di 60 s), ma la moltiplicazione e' nostra e **segue il batch** — 10 500 caratteri a 600 s, 2 625 a 150 s. Al superamento **si manda in anticipo e lo si annuncia**, mai si scarta; al peggio 12 spawn/ora contro 15. **Haiku rimisurato sul percorso nuovo** (45 spawn a gruppi di 5, 2,21 USD): **0,833 · 0,889 · 0,900 · 0,909 · 1,000** — sopra la barra con piu' margine del percorso a frase singola (0,833 contro 0,733), nudo 0,526 (il filtro conta meno ma conta), richiamo 0,450. `MAX_ARGOMENTI = 8` **non morde** (massimo 6), il TTL non cambia (la lista si sostituisce), e `rilevanza_per_parole` non presume una lista corta. **Lista vuota: da 75 % a 38 %** — e' il numero che spiega il pannello news vuoto. Gate NON rimisurato di proposito | **§15** |
| 5.27 | 26 ago 2026 | **Haiku supera la barra — e a reggerla e' il FILTRO, non il modello. E il «batch» di §15 SCARTA invece di accumulare.** La barra `3(1-P) < 1` → `P > 2/3` era stata dichiarata prima di misurare e poi applicata **solo al locale**: haiku era collegato perche' il locale non ci arriva, senza che la sua precisione fosse mai misurata. Misurato su **cinque giri, 215 spawn, 11,3 USD nozionali**: **0,733 · 0,769 · 0,800 · 0,917 · 1,000** — cinque su cinque sopra la barra, il peggiore di 0,066. Le risposte GREZZE sono congelate in `HAIKU-RISPOSTE.json` e la metrica si **ricalcola da li'** col parser di produzione, cosi' non puo' invecchiare. ⚠️ **Haiku NUDO sta a 0,249 di media**, sotto la barra in tutti i giri: il modello risponde in prosa («(riga vuota)», «Attendete, ho notato che...») invece della riga vuota richiesta, e senza il filtro estrattivo quelle parole diventerebbero argomenti. Il filtro era nato per l'invariante 2 contro un modello che inventa; regge anche la precisione, e togliendolo la barra cade con lui. ⚠️ **Il richiamo e' il prezzo**: 0,520 contro 0,800 del locale — cinque attesi non li trova MAI in cinque giri. Per la politica dichiarata (la precisione e' il cancello) e' la direzione giusta, non e' gratis. ⚠️ **DIFETTO NOTO, non corretto**: `EstrattoreLLM` non accumula. `MotoreNews.ascolta` passa **una battuta sola** e dentro la finestra le altre vengono **scartate**. A 60 s si perdeva poco; portando il batch a 600 s (rev 5.25) l'ho reso dieci volte peggiore. Percio' la misura frase-per-frase E' il percorso di produzione. Fissato in `TestIlBatchSCARTAinveceDiACCUMULARE`, la cui prima stesura **non discriminava** — era vera per il limitatore di frequenza, non per lo scarto: terza occorrenza di §11.7 regola 4 in questo arco. E `git checkout`, `git restore`, `git reset --hard` passano nei `deny` di `.claude/settings.json`: su lavoro non committato sono irreversibili come `rm -rf` | **§15**, §11.7 |
| 5.26 | 26 ago 2026 | **Il caso che la regola degli argomenti perde non e' il sostantivo nudo: e' la COORDINAZIONE — e il banco non puo' misurarla.** «di intelligenza artificiale e semiconduttori» da' **solo `intelligenza`**: `artificiale` segue un sostantivo, `semiconduttori` una congiunzione, e cadono i due termini piu' specifici. Misurato sul corpus: **zero frasi su 43 contengono una coordinazione** — non poche, nessuna — con il rilevatore controllato su nove prove (cinque coordinazioni vere, quattro copule `e'`, che dopo il taglio dell'apostrofo si scrivono come la congiunzione). Lo zero e' fissato come **tripwire**: se il corpus un giorno ne conterra' una, il test diventa rosso e chiede di riprendere la decisione. ⚠️ **Il rimedio piu' economico e' un non-fatto**: ereditare l'introduttore attraverso la congiunzione non cambia un solo esito sul banco e non recupera nemmeno quella frase, perche' la catena si e' gia' rotta su `artificiale`. L'unica regola che la recupera — catena aperta anche attraverso le parole piene — il banco la misura: **precisione 0,410 → 0,365, richiamo 0,800 → 0,950**, e per la politica dichiarata prima di misurare (la precisione e' il cancello) **non si adotta**; resta misurata in `catena_larga`. Il banco **non e' stato allargato** con frasi scritte per l'occasione: sarebbe il sovradattamento da cui l'importazione protegge. E **due numeri erano invecchiati** in `topics.py` (0,421 invece di 0,410; 0,155 invece di 0,136, quest'ultimo trovato dalla guardia e non da una rilettura): `TestINumeriCITATI` confronta ogni cifra citata nei sorgenti con le cinque quantita' che il banco calcola | **§15** |
| 5.25 | 26 ago 2026 | **La regola degli argomenti non era grammatica, era la LUNGHEZZA — e adesso c'e' un banco.** `n >= 2 or len(p) >= 8` su una frase sola ha tutti i conteggi a 1, quindi l'`or` collassa a «e' lunga»: `clima` (5) e `governo` (7) cadevano, `pensando` (8) passava. La diagnosi precedente — «tiene un verbo e perde i sostantivi» — era un aneddoto su tre frasi con i falsi positivi invisibili. Nasce `tests/eval_argomenti.py`: le **43 frasi conversazionali di `t0_corpus.py` importate e non copiate**, scritte per una proprieta' ORTOGONALE e quindi non scegliibili per far passare la regola; metrica **precisione e richiamo micro-mediati**, perche' 28 frasi su 43 hanno attesa vuota ed e' li' che un falso positivo si vede. Misurato: **0,171 → 0,410 di precisione, richiamo 0,700 → 0,800**. La regola nuova tiene le parole **introdotte da un articolo o una preposizione** (`INTRODUCONO`, una allowlist come `FERME`, mai una denylist di desinenze); l'apostrofo **esce** dalla classe di token (`un'email` era UNA parola di 8 lettere, `perche'` sfuggiva a `FERME`); il ripiego `or conteggi` **cade**, e costava 0,136 di precisione (la rev diceva 0,155: numero invecchiato, corretto dalla guardia della rev 5.26). La soglia di H1 **non esiste**: nessun valore da 2 a 8 sposta la precisione fuori da 0,157–0,173. ⚠️ **Haiku e' COLLEGATO, e la decisione viene dalla misura**: barra dichiarata prima — `3(1-P) < 1` → `P > 2/3` — e il locale riparato arriva a 0,410, con errori residui che sono sintagmi regolari («la luce», «la fantasia») indistinguibili per forma da «il bagno». **§15 «batch 60s» e' EMENDATO**: 60 s vorrebbero dire 60 spawn/ora contro il tetto di 15 del Governor, quindi **batch = periodo dei giri** (600 s con 3/ora, 6 spawn/ora) — nessun numero nuovo. La risposta del modello e' filtrata **estrattivamente**: solo parole pronunciate, allowlist che si costruisce da sola. Giro vero sui feed veri: gli argomenti vecchi facevano passare **0 item su 57**, i nuovi **2**. Esito in `docs/acceptance/ARGOMENTI-IL-BANCO.md` | **§15**, invariante 2 |
| 5.24 | 25 ago 2026 | **§15 non dice ogni quanto si guardino i feed, e adesso il numero e' DEDOTTO.** `Watcher.giro()` non aveva un solo chiamante nel core: il `Watcher` si costruiva a ogni avvio e `giri_fatti` restava **0**. §15 dichiara una sola frequenza — 3 interruzioni/ora — che e' il ritmo con cui JARVIS puo' PARLARE, non quello con cui puo' GUARDARE. Il periodo dei giri si ricava da due vincoli: il **budget** da' una finestra di 1200 s e dimezzarla le da' due occasioni invece di una (`3600 / (2 x tetto)`), gli **argomenti** vivono 30 minuti e un giro piu' lento della loro vita li farebbe scadere senza mai guardarli (`<= ttl/2`); piu' un pavimento di **60 s** che non viene dall'aritmetica ma dall'educazione verso server di terzi. Con 3/ora fa **600 s**, e **cambia con l'impostazione** — non e' una costante travestita da deduzione. E **senza argomenti non si guarda affatto**: `giro()` misura la rilevanza contro gli argomenti, quindi a lista vuota un giro e' traffico in cambio di nulla. Gli argomenti vengono dalla CONVERSAZIONE, come §15 chiede, e la card che passa si dice anche a voce. ⚠️ L'estrattore **haiku** di §15 resta non collegato: il suo batch e' 60 s e il tetto T2 e' 15 spawn/ora — servirebbe una decisione, non una riga. Esito in `docs/acceptance/LE-NEWS-GIRANO.md` | **§15**, §22 Fase 9 |
| 5.23 | 25 ago 2026 | **Il campo del globo era dipinto col colore del suo telaio.** Lo spazio attorno al pianeta era `--bg-raised`, cioe' lo STESSO valore della scatola che lo contiene: l'emisfero in ombra dava **1,08:1** contro il campo e il lembo spariva. L'istogramma a 16 bin diceva la stessa cosa da un altro lato — `famiglia-a/01` tiene il **5,15 %** del fotogramma sotto L 16 e noi lo **0,00 %**, e nel riferimento quel nero sta TUTTO dentro i pannelli di globo e mappa (28-41 % di quelle celle, dominante `#03080c` a L 7,2). Nasce `--bg-abyss` `#05080b` (L 8), **suolo di una VISTA e non un gradino della rampa**. Misurato dopo: emisfero in ombra 1,08 -> **1,22:1** (il rapporto WCAG comprime al fondo della scala; la separazione di luminanza passa da 6,4 a **23,1 punti**, e il disco si legge), lembo illuminato 1,54 -> 2,03, `--cy-100` sul campo 12,43 -> 16,37. I 312 fusi NON stanno sul campo ma sulla sfera, a 3,04:1, invariati. **§10.5 regola 1 non e' rotta, e' misurata**: il gradino campo -> scrivania e' **11,5 punti nel riferimento e 11,6 da noi** — famiglia-a inverte il gradino sotto il globo esattamente cosi'. Entropia **2,203 -> 2,394** su una fixture con pavimento di rumore 0,00; dev.std 33,99 -> 34,86; `L>60`, caldo e barra invariati. Restano **0,006** sotto la soglia di 2,40, dichiarati | **§10.1**, §11.8 |
| 5.22 | 25 ago 2026 | **§11.9 prende una seconda eccezione — il modo di MISURA — e §11.7 una regola 5.** Due sessioni di `npm run scrivania` davano `L>60` 26,1 % e 25,3 % e la differenza non era attribuibile: la telemetria arriva a 2,5 Hz e le due serie uPlot sono AREE PIENE a L 66 e L 89, cioe' sopra la soglia, alte quanto `cpu_percent`, su un pannello che e' il 16,5 % dello schermo. Il modo di misura puo' alimentare la scrivania da una REGISTRAZIONE di una sessione vera — mai da valori generati — con impronta versionata, comando proprio, e il divieto di confrontare un numero di fixture con uno vivo. La sorgente resta FUORI dall'applicazione: un socket di riproduzione, invarianti 1 e 7 intatte. E §11.7 regola 5: **la provenienza di una misura fa parte della misura** — quattro misure contaminate in due giorni avevano tutte il numero giusto e il confronto nullo | **§11.9**, **§11.7**, invariante 23 |
| 5.21 | 24 ago 2026 | **§10.6 — le tre classi di moto, e §11.7 regola 4.** L'invariante 25 aveva due parole, «con causa» e «ambientale», e ne servivano tre: l'equalizzatore vocale di §11.5 e la `<webview>` viva di §6.3 sono **prescritte** e il loro stesso banco le boccerebbe, perche' non hanno un inizio e una fine — hanno una **sorgente**. La classe 2, «continuo governato da una sorgente viva», e' ammessa **solo nel contenuto di un pannello**, con tre condizioni gia' misurabili (falsificabilita' su due finestre da un secondo, leggibilita' del valore da uno scatto fermo, attribuzione dei pixel mossi al rettangolo dichiarato) e un tetto di **due sorgenti e 15 % del fotogramma**, che e' una scelta e non una misura. **Il fondo non si tocca**: §10.3 resta assoluta. E §11.7 prende una **regola 4**: un criterio su un fenomeno dichiara prima che il fenomeno e' avvenuto, e gli esiti sono tre — `non misurabile` **non conta come verde**. Cinque occorrenze finora, l'ultima `si_e_fermata` vera perche' il nastro non si era mai mosso | **§10.6**, **§11.7**, invariante 25 |
| 5.20 | 23 ago 2026 | **La scala di §25.5 sale di un gradino, e il marchio passa per un centesimo.** Cancello di governance separato e senza codice (`e4851ae`), poi l'implementazione (`b2f7360`): tratto a riposo `--cy-700` (L 100), anello attivo `--cy-500` (L 181) **a un anello per volta**, riempimento delle fasce `--cy-900`, campo interno `--bg-panel`. Motivo misurato: il profilo radiale di `famiglia-a/12` porta le bande chiare a L 92-125, e il tetto L 48 rendeva il riferimento irriproducibile **per costruzione**. Cio' che NON sale tiene il vincolo: testo dei pannelli a L 224, `--cy-100` vietato. Costo: §25.13.5 e' caduta a 1,77:1 ed e' stata rimessa **dal fondo** a **3,01:1** su un minimo di 3,00. **⚠️ Misurata in UN solo stato su sette**: simulata in T0 da' 2,94:1, cioe' rotta — vedi `PIANO-CORE-E-DENSITA.md` §8. Densita': entropia 1,57 → **1,69**, L>60 9,2 → **10,0 %** | §25.5, §25.13 |
| 5.19 | 23 ago 2026 | **Un nucleo solo.** Erano due implementazioni dello stesso riferimento `famiglia-a/12`: gli anelli SVG di `anim/rings.js` (1,39 ms) e una nuvola di 1 500 punti in `desk/sfondo.js` (**10,36 ms**, il 62 % di un fotogramma, per 122 px a schermo su 264 049). §25.6 prescriveva gli anelli e diceva «non va riscritto»: e' stato riscritto lo stesso. La fusione tiene marchio, arco ambra, soglie di fase e contratto; cade la nuvola. Moto senza causa **5 568 px → 0**. Poi materia invece di wireframe e stati ad anime.js (`ece4289`) | §25.6, invarianti 25 e 26 |
| 5.18 | 23 ago 2026 | **§25.13 — il marchio.** `J.A.R.V.I.S.` al centro del nucleo non e' un dato segnaposto e l'invariante 23 non lo tocca: `famiglia-a/12`, il riferimento che §25.1 assegna a questo componente, **ha quella scritta**. La riga della `12` nel README delle referenze ne elencava tre cose su quattro e l'omissione e' costata la richiesta di rimuoverlo. §25.11 «nessun testo nel nucleo» **emendata**: vale per il testo di dato, non per il marchio. Sette regole di recinto, deroga **dichiarata** a §11.6 regola 1 sul corpo calcolato (eccezione **nominata** nell'audit, non soglia allentata), criterio §25.13.5 con forbice 3–5:1 meccanizzato in `densita.mjs --marchio` | §25.11, §25.13, §11.6 |
| 5.17 | 23 ago 2026 | **La misura di occlusione, e tre premesse che cadono.** «Coperto» e' una proprieta' del layout, non del PNG: `scripts/occlusione-dom.js` la valuta con `elementFromPoint` nella finestra viva, `app/main.js` applica il protocollo (massimizzata **prima** del primo render, T+3 s, due scatti). Smentite: ① il disco della scrivania e' Ø326 e non Ø502, coperto allo **0,0 %**; ② **le cartelle manila non esistono** — il caldo allo 0,2 % non e' nascosto, non e' mai stato messo; ③ «animazioni ferme» ≠ «zero pixel che cambiano», il 15 % del moto e' telemetria con causa. Cinque difetti trovati **dentro la misura stessa**, fra cui `closest("#scrivania")` che prendeva il pavimento | §11.7, §11.8 |
| 5.16 | 20 ago 2026 | **§10.5, il linguaggio delle finestre — e la cornice che il riferimento non ha.** Misurati sette pannelli di `famiglia-a/01`: **zero** hanno una cornice sui quattro lati. Tre non hanno nessun tratto di bordo, due ce l'hanno su un lato solo, il calendario e' asimmetrico. Un pannello e' un **gradino di luminanza** (corpo L 37 = `--bg-raised`, misurato `#1e2631` identico a quattro quote) e i suoi angoli si chiudono con **marcatori triangolari** su due vertici opposti. La testata e' una **superficie** al 6-9 % dell'altezza con +19 L sul corpo, non una riga di testo. `.jarvis-panel` perde i due `inset` caldi — erano **alone**, che l'invariante 19 vieta — la trasparenza e il `backdrop-filter`, e l'ombra scende da `0 26px 60px α.5` a `0 2px 3px α.18`, che e' l'unica misurata nel concept | **§10.1**, **§10.5**, §10.2 |
| 5.14 | 19 ago 2026 | **Il catalogo (§26.3), e i due token che gli servono.** `--icona` (L 171) e `--icona-viva` (L 216), misurati sul plinto di `famiglia-a/01`: sono l'unica cosa piena e chiara della scrivania, ed e' la differenza piu' grande col dock di oggi — nel riferimento la fascia del catalogo ha il **26,2 %** di superficie accesa, la nostra il **2,8 %**, perche' le nostre «icone» sono TESTO a L 96. Nessuno dei token esistenti arriva lassu' senza essere il colore del dato. Il catalogo prende dal dock l'indice dei moduli e le azioni: il dock resta la striscia di stato | **§10.1**, §13 |
| 5.13 | 19 ago 2026 | **L'invariante 19 riformulata: vieta l'ALONE, non l'ombra.** Tre righe del progetto dicevano cose diverse — l'invariante vietava ogni drop-shadow, §10.1 dichiarava un'ombra portata nera in `.jarvis-panel`, e `app.css` la spegneva con `box-shadow: none`. §10.1 aveva ragione: l'invariante nasceva contro il **glow** della Famiglia B e aveva travolto anche l'ombra, che e' il contrario — l'alone aggiunge luce che non esiste, l'ombra toglie luce dove un oggetto ne copre un altro. Con ADR-010 la contraddizione e' diventata insostenibile. L'ombra e' riaccesa in tutti e due i posti in cui era spenta, il pannello col fuoco prende `--cy-700` sulla cornice, e l'audit impone le due meta' verificabili: **scurisce** e **non ha tinta**. Misurato col controllo: senza ombra i pixel sopra ogni bordo stanno a 30,7 piatto, con ombra scendono a 28,8 → 27,8. ⚠️ Trovato riallineando le copie: **`CLAUDE.md` e §20 erano divergenti da diverse fasi** — a §20 mancavano 39 righe, fra cui l'invariante 30 sul copyright. Un test le tiene uguali, come per §10.1. Esito in `docs/acceptance/ADR-010.md` | **§20**, §11.8, §10.1 |
| 5.12 | 19 ago 2026 | **ADR-010 — una scrivania sola, e §13 e' superata nel modello a quattro workspace.** I quattro domini diventano **categorie**: `Alt+1…4` filtra e non cambia pagina, e il numero di pannelli a schermo NON cambia — verificato, 14 prima e 14 dopo ogni pressione. La cella dichiarata diventa la posizione INIZIALE e non la gabbia. Misurato prima di decidere che cosa si apre all'avvio: con **tutti e quattordici** i pannelli aperti insieme — three.js, PixiJS, CSS 3D, due webview, anime.js — la mediana del frame e' **16,7 ms**, cioe' il vsync, e il filtro non costa niente. Tre difetti trovati **guardando lo scatto** e non dai test: **R87** al primo avvio i pannelli restavano disposti contro l'area di prima che la finestra si massimizzasse, **R88** le quattro piastrellature complete si coprivano e dei quattordici pannelli se ne vedevano DUE, **R89** il pulsante del dock di un pannello sepolto lo chiudeva invece di alzarlo. Esito in `docs/acceptance/ADR-010.md` | **§13**, §11.6 |
| 5.11 | 19 ago 2026 | **§11.7 guadagna un passo 0: l'ambiente della prova non puo' essere piu' permissivo di quello vero.** Un criterio che si ferma al confine di un sottosistema prova META' del giro — successo due volte: il CSP di PixiJS (i glifi giravano in galleria, che non aveva CSP, e nell'app non partivano da quattro fasi) e **R82** (sei test verdi sulla persistenza mentre `resize → affianca()` cancellava il ripristino un secondo dopo l'avvio). La prova del trascinamento avvia ora `app/main.js` con Electron e core veri e muove il puntatore con Playwright, che entra nella pipeline di input del browser. Quattro difetti trovati cosi': **R83** area congelata alla creazione della cornice, **R84** il `pointerdown` de-massimizzava dentro il doppio clic, **R85** WinBox ripristinava una geometria mai avuta, **R86** lo `z` si salvava e non si riapplicava. Esito in `docs/acceptance/LAYOUT-PERSISTENTE.md` | **§11.7** |
| 5.10 | 19 ago 2026 | **La tipografia ritarata sul fondo nuovo, e `L>25` ritirata dal giudizio.** Alzare `--bg-panel` a L 31 aveva fatto attraversare tre soglie WCAG (R81): `--txt-dim` 4,90 → 4,30, `--cy-700` 3,06 → 2,68, `--txt-ghost` 2,12 → 1,86. Adesso `#708b91` · `#227482` · `#556e75`, cioe' **4,53 · 3,04 · 3,03** sul corpo del pannello, verificati col rapporto WCAG su luminanza LINEARIZZATA e **guardati** negli scatti. E `scripts/densita.mjs` guadagna **deviazione standard** ed **entropia** dell'istogramma a 16 bin: `L>25` era passata al 96,9 % ed e' satura — una metrica che passa sempre e sembra una verifica e' peggio di nessuna metrica, quindi resta stampata come contesto e non concorre piu'. Le due misure nuove dicono che dalla 5.7 alla 5.9 l'articolazione della scrivania e' **scesa** (entropia 1,34 → 1,25), che e' la stessa diagnosi vista da un terzo angolo | **§10.1**, §11.8 |
| 5.9 | 19 ago 2026 | **La 5.8 aveva tirato la leva sbagliata.** I sei riempimenti erano sei, e i due piu' bassi (`--fill-1` L 31, `--fill-2` L 37) erano **duplicati di `--bg-panel` e `--bg-raised` alla luminanza giusta**: bastava spostare le superfici di BASE. La misura lo diceva gia' — il **71,2 %** della scrivania e' `--bg-panel` e solo il **2,4 %** e' il fondo che la 5.8 aveva alzato. Adesso `--bg-deep` `#1a1f23` (L 30, misurato sulla barra del riferimento), `--bg-panel` `#13212a` (L 31), `--bg-raised` `#1e2631` (L 37), e **tre** riempimenti di stato (L 66 · 89 · 103) piu' `--manila`. ⚠️ Il riferimento **non ha una scala monotona**: ha un pavimento, una banda di superficie e riempimenti di stato, e barra e pannello stanno nella stessa banda — la barra si distingue per densita' d'inchiostro, non per fondo. Scritto nel commento di §10.1 perche' non venga "corretto". Un test impone l'ordine `--bg-void < --bg-deep <= --bg-panel < --bg-raised`. Tre soglie WCAG attraversate e **dichiarate**, non aggiustate: `TOKENS-RIEMPIMENTO.md` | **§10.1** |
| 5.8 | 19 ago 2026 | **§10.1 guadagna i sei ruoli di riempimento, e il fondo si alza.** Una revisione che ha misurato i pixel (`docs/DIVARIO-PREMIUM.md`) ha trovato che fra `--bg-raised` (L 25) e `--cy-500` (L 181) non esisteva **un solo token usato come superficie**: il salto di 156 punti di luminanza lo faceva un bordo da un pixel, e l'insieme legge come un wireframe invece che come una plancia. Il riferimento vive per intero in quella banda — 42,1 % di pixel riempiti contro il nostro 4,5 %. Aggiunti `--fill-1..5` e `--manila`, coi valori **misurati** su `famiglia-a/01`, e `--bg-void` da `#070b0d` (L 10) a `#0f1418` (L 19), che e' il fondo del riferimento: un nero meno assoluto AUMENTA il contrasto percepito degli elementi chiari. ⚠️ I 18 componenti **non** sono stati toccati — e' il passo dopo, e va fatto col ciclo §11.7. Un test lega ora `tokens.css` a questa sezione byte a byte. Esito in `docs/acceptance/TOKENS-RIEMPIMENTO.md` | **§10.1**, §11.8 |
| 5.7 | 19 ago 2026 | **Le due radici di composizione diventano una** (§3.2): l'engine compone voce, T1, Governor, news e ARGUS, ma **a gradi** — gli interruttori sono predefiniti a `false` NELLO SCHEMA, perche' un servizio che accende il microfono per il fatto di essere stato installato sarebbe la peggiore sorpresa del progetto. **§5.6 capovolto**: il codice di uscita per il token scaduto non si scopre empiricamente da una tabella che nessuno pubblica — lo emette il supervisore (`USCITA_AUTH = 41`), e `RestartPreventExitStatus` funziona per costruzione. Due errori nello snippet systemd di §5.6, trovati da `systemd-analyze verify`: `StartLimit*` va in `[Unit]` e non in `[Service]`, dove systemd lo ignora in silenzio; `ProtectHome=read-write` non esiste. La unit e' `jarvis-core.service` e non `jarvis-voice.service` (§3.2 batte il nome di §22), con `Alias`. Consuntivo in `docs/acceptance/FASE-09.md` | **§3.2**, **§5.6**, **§16.1b**, **§21.1**, **§22** |
| 5.6 | 18 ago 2026 | **Le news si innestano sulla barriera di Fase 6, non ne aprono una parallela**: `Item.testo` e' un `Untrusted`, e l'eval di injection passa da 39 a 51 casi coi vettori di un feed. **L'estrattore di argomenti RIFIUTA il contenuto non fidato**: se leggesse le news, un articolo ostile potrebbe iniettare i propri argomenti e da li' scegliere quali altri articoli superano il gate. Nel gate uno stato IGNOTO vale come un divieto — in un sistema che parla da solo, la modalita' silenziosa e' quella sicura. Delle quattro fonti RSS che §15 nomina ne rispondono **due**: Il Post da' 403 anche con User-Agent, e l'URL di Reuters non esiste piu' — entrambe annunciate invece che silenziate | **§15**, **§21.1**, **§22** |
| 5.5 | 18 ago 2026 | **§22 non dichiarava un criterio per la Fase 7**: l'ho dichiarato io, derivandolo dai quattro punti di §14, e in `FASE-07.md` e' segnato come mio. **L'invariante 27 era imposto a meta'**: `register()` rifiutava un tool `side_effect` dichiarato `gesture_allowed`, ma nulla impediva a un percorso gesture di invocare `trash_path`. Aggiunto `registry.invoke_da_gesture()`, fail-closed, unica via delle gesture verso i tool. Misurato: l'inferenza MediaPipe sta in **8,3 ms**, e i 30 fps di §14.1 non li limita il modello ma **l'auto-esposizione della telecamera** — 12,5 fps con poca luce, 30,0 con posa corta. L'isteresi di «5 frame (~166 ms)» presuppone quei 30 fps: a 12,5 vale 400 ms | **§14**, **§21.1**, **§22** |
| 5.4 | 18 ago 2026 | **L'invariante 5 diventa un tipo.** `core/llm/untrusted.py`: il contenuto non fidato non e' una stringa marcata ma un `Untrusted` che non si concatena, non compare nei log e non puo' chiudere la propria busta dall'interno; `ClaudeT2` lo RIFIUTA se i tool non sono vuoti, e il parser T0 lo rifiuta del tutto — una pagina che contenga un comando valido non deve poter diventare un'azione. Aggiunti `core/tools/web.py` (due tool `side_effect=False`) e `core/vision/{argus,ocr}.py`, non previsti da §21.1. Il contratto in ingresso del socket passa da uno a due messaggi, entrambi risposte con `id`. Motivazioni per esteso in `docs/acceptance/FASE-06.md` | **§6.3**, **§12**, **§21.1**, **§21.4** |
| 5.3 | 18 ago 2026 | **Tre librerie nominate in §22 per la Fase 5 non entrano, ognuna perché contraddice un invariante**: three-globe genera geometria propria (inv. 22), troika-three-text rasterizza testo in WebGL con colori letterali (inv. 20 e 18), d3-force è una simulazione che si assesta muovendosi (inv. 25). Il globo, la graticola, il terminatore e i fusi sono `ParametricComponent` gatati. Aggiunto il tool `timezones` in `core/tools/geo.py`, non previsto da §21.1. Corretti tre difetti del quality gate di §11.11 e i periodi degli anelli di §10.3 (240 è multiplo di 120). Motivazioni per esteso in `docs/acceptance/FASE-05.md` | **§10.3**, **§11.11**, **§17.4**, **§21.1**, **§22** |
| 5.2 | 18 ago 2026 | **Nota APU in §9.** La tabella VRAM presuppone una GPU discreta; su memoria unificata la «VRAM» è un carveout della RAM e i due numeri non si sommano. Aggiunta la regola `headroom = min(VRAM libera, RAM disponibile)`, applicata da `core/gpu_scheduler.py`. Scoperto misurando la macchina di sviluppo in Fase 1 | **§9** |
| 5.1 | 18 ago 2026 | **Il trasporto core ↔ Electron passa da TCP `127.0.0.1:8765` a un socket UNIX.** L'autorizzazione la fa il kernel sui permessi del filesystem invece di un token applicativo, e la conferma umana di §6.2 — cioè l'invariante 3 — smette di essere raggiungibile da qualunque processo dell'utente. Il protocollo non cambia: WebSocket su stream, stessi topic. Decisione presa in `docs/VALUTAZIONE-ARCHITETTURALE.md`, ADR-002 | **§3.2**, **§16.1b**, **§18.2**, **§21.4** |

L'**invariante 7** è stato riscritto di conseguenza, in `CLAUDE.md` e nella
copia di §20. Ora enuncia il principio — *il canale non è raggiungibile dalla
rete e l'autorizzazione la impone il sistema operativo* — e nomina il socket
UNIX come implementazione odierna. Così il porting a Windows (named pipe con
ACL, §23) non richiederà un altro emendamento dell'invariante.

## Chiuso nella rev 5.0
| # | Aggiunta |
|---|---|
| 1 | **§5.6 Scadenza OAuth e supervisione di T1** — il caso di degradazione più probabile, prima scoperto |
| 2 | **§5.2 latenza misurata sul campo**: cold start mediano 2,41 s |
| 3 | **§7.6 parser T0 completo** — il componente più critico per la latenza, prima solo citato |
| 4 | **§5.7 `voice-persona.md`** — il system prompt di T1, prima solo referenziato |

## Cosa cambia rispetto alla rev 4.1

| # | Decisione presa | Effetto |
|---|---|---|
| 1 | **Deepgram è il provider principale**; i modelli gratuiti in streaming sono **fallback** | §7 e §8 invertite nei default |
| 2 | **ARGUS vede solo l'app** | §12 chiusa su `scope="app"` |
| 3 | **Linux ora, Windows in futuro** | §23 nuova: cosa isolare oggi perché domani costi poco |
| 4 | **Analisi di replicabilità della UI** dai riferimenti | §11 nuova — la sezione che ha chiesto |
| 5 | **Stack librerie UI verificato con repo** | §11.3 |
| 6 | **Metodo operativo per Claude Code sul design** | §11.7 — il ciclo di feedback visivo |

---

# INDICE

1. Cos'è, cosa non è
2. Verdetto sui riferimenti
3. Architettura
4. Stack verificato
5. Backend LLM — Claude Code, memoria, scadenza OAuth, persona
6. Filesystem, YouTube, operazioni reali
7. Voce: wake a frasi, STT, TTS, parser T0
8. Impostazioni e chiavi
9. Contesa GPU
10. Design system
11. **Replicare la UI dei riferimenti**
12. ARGUS
13. Moduli, pannelli, scorciatoie
14. Gesture
15. News proattive
16. Autonomia e degradazione
17. Modelli 3D
18. Sicurezza
19. Legale
20. `CLAUDE.md`
21. Repo e codice
22. Piano a fasi, stime
23. **Portabilità verso Windows**
24. Cosa resta incerto

---

# 1. Cos'è, cosa non è

**Non è un sistema operativo.** **Non è un overlay sul desktop.**

**È un'applicazione desktop a schermo intero** — un ambiente cognitivo — dentro il quale JARVIS vive, parla, mostra dati, apre il web, gestisce cartelle reali del PC e genera modelli 3D. Fuori dalla sua finestra non tocca nulla.

Cervello: **Claude Code su abbonamento**. Nessun LLM locale.
Voce: **Deepgram Flux** primario, modelli locali in fallback.

---

# 2. Verdetto sui riferimenti

## 2.1 I quattro errori della specifica originale

| # | Errore | Verifica | Esito |
|---|---|---|---|
| 1 | PyAutoGUI per controllo finestre | è automazione mouse/tastiera, non un WM; su Wayland non funziona (no XTEST). Issue #909, #111 aperte; SeleniumBase #4010: solo X11, repo non mantenuto da ~2 anni | **rimosso**; col nuovo scope il problema si dissolve |
| 2 | three-mesh-bvh "accelera il rendering" | falso: accelera raycasting e query spaziali | **resta, riclassificato**: picking gesti (§14) |
| 3 | Overlay Electron click-through su Wayland | Electron #51808 (input region solo alla submission di un frame), #52456 (regressione X11 in v43), niente `wlr-layer-shell` | **scompare** col nuovo scope; Electron riabilitato |
| 4 | Sandbox a denylist | lo spazio dei comandi dannosi è infinito e componibile | **allowlist tipizzata** |

## 2.2 Il documento delle librerie

**Errore strutturale**: descriveva una pagina web senza core né accesso al sistema, con "Livello 2: Logica = anime.js + Golden Layout" — che è presentazione.

**Tenere**: WinBox.js (finestre interne), anime.js (prioritaria), three.js.

**Scartare**: OS.js (desktop *simulato* con FS virtuale — Lei vuole file veri) · Arwes (neon cyberpunk, contraddice il pilastro "nessun glow") · Golden Layout (ridondante; due WM si contendono il drag) · Babylon.js (doppio contesto GL) · Spline (SaaS, richiede rete) · React Three Fiber (solo React, reconciler overhead) · GSAP (ridondante con anime.js) · Web Speech API (in Chromium **manda l'audio a Google**).

## 2.3 Stonic AI

Prodotto Windows commerciale, pagamento una tantum, l'utente collega la propria API.

**Da adottare**: il principio *"esegue, non risponde con un paragrafo su come potresti farlo da solo"*, e i loro tre casi d'uso come **suite di accettazione** della v1: organizza Downloads per tipo; apri YouTube e riproduci; cosa sta rallentando il PC.

## 2.4 Il link Pinterest

`https://in.pinterest.com/da8c149f-...` **non raggiungibile**: Pinterest blocca l'accesso automatizzato e l'URL non ha comunque il formato di un pin. **Non analizzato.**

---

# 3. Architettura

## 3.1 Perché Electron

Il cambio di scope ha eliminato `wlr-layer-shell`, la click-through e l'IPC del compositore. **Elimina anche il motivo per cui avevo scartato Electron.** In una finestra normale Le dà il motore WebGL di Chromium, nettamente superiore a WebKitGTK per three.js pesante.

*Non usi Tauri: su Linux usa la system webview, cioè WebKitGTK, e riporta il problema.*

Il **core Python resta**: pipeline vocale, file sotto allowlist, telemetria, sandbox, orchestrazione di Claude Code.

## 3.2 Processi

```
┌─────────────────────────────────────────────────────────────┐
│ CORE (Python, asyncio) — servizio systemd utente             │
│ engine · router · memory · settings · governor · gpu_sched   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ TOOL LAYER — allowlist tipizzata                       │   │
│ │ file · 3D · sistema · news · argus                     │   │
│ │ side_effect=True → conferma umana obbligatoria         │   │
│ └───────────────────────────────────────────────────────┘   │
│ T0 grammar (<10ms, 0 LLM) · T1 claude persistente ·          │
│ T2 claude -p effimero + subagent                             │
│ voice: wake Vosk → STT → TTS streaming                       │
│ sandbox: profilo exec (bwrap + seccomp)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket su socket UNIX (§18.2)
                           │ $XDG_RUNTIME_DIR/jarvis-os/core.sock, dir 0700
                           │ telemetry · agent.* · voice.* · fs.*
                           │ news.* · argus.* · state.snapshot
┌──────────────────────────┴──────────────────────────────────┐
│ APP JARVIS OS (Electron) — finestra massimizzata             │
│ main: bridge WS ↔ renderer, gestione <webview>               │
│ renderer: WinBox · three.js · PixiJS · anime.js · webview    │
└──────────────────────────────────────────────────────────────┘
```

## 3.3 I tre tier

| Tier | Cosa | Motore | Latenza |
|---|---|---|---|
| **T0** | apri pannello, cerca file, workspace, telemetria, volume | parser a grammatica, zero LLM | **<10 ms** |
| **T1** | conversazione, risposte parlate | `claude` persistente, Haiku 4.5 | 300–900 ms primo token |
| **T2** | operazioni complesse, codice, 3D | `claude -p` + subagent | 5 s – minuti |

## 3.4 Sandbox

| Profilo | Per | D-Bus | Rete | FS |
|---|---|---|---|---|
| `exec` | codice generato, script, build 3D | ❌ | ❌ | ro tranne `~/JARVIS/` |

`bubblewrap --unshare-all --die-with-parent`, ro-bind `/`, rw-bind `~/JARVIS/`, seccomp.

> ### ⚠️ Le due righe qui sopra descrivono un disegno SUPERATO (rev 5.36)
>
> **ADR-008 le ha sostituite** e nessuno le ha corrette: `core/sandbox/runner.py`
> usa una **radice vuota** — `--tmpfs /` con dentro solo l'interprete e la sua
> libreria — e **non lega `~/JARVIS/` in scrittura**. Oggi il codice generato non
> scrive da nessuna parte fuori dalla propria tmpfs, che e' piu' stretto di cio'
> che questa tabella promette.
>
> Trovato il 27 agosto rispondendo alla domanda «perche' la workspace sta fuori
> dal progetto?»: la giustificazione che avevo dato — «e' l'unico percorso
> scrivibile della sandbox» — veniva da qui, ed era **la specifica, non il
> codice**.
>
> `~/JARVIS` resta cio' che `fs.workspace` dichiara: la prima delle radici
> consentite, la cartella su cui lavorano i tool di file di §6.1 e che il
> pannello file mostra. Non ha piu' niente a che vedere con la sandbox.

**Le operazioni su file reali NON girano in sandbox**: girano nel core sotto allowlist con validazione path (§6.1). La sandbox isola il *codice generato*; l'allowlist vincola le *operazioni note*.

---

# 4. Stack verificato (agosto 2026)

| Libreria | Stato | Licenza | Verdetto |
|---|---|---|---|
| **LangGraph** | 1.0 ott. 2025, 1.1.x nel 2026 | Apache 2.0 | ✅ `create_react_agent` **deprecato** → `StateGraph` |
| **psutil** | attivo | BSD | ✅ (correzione §21.4) |
| **PyAutoGUI** | non mantenuto ~2 anni, no Wayland | BSD | ❌ rimosso |
| **Electron** | attivo | MIT | ✅ riabilitato |
| **three.js** | attivo | MIT | ✅ |
| **three-mesh-bvh** | v0.9.x | MIT | ✅ picking |
| **PixiJS** | v8 | MIT | ✅ |
| **anime.js** | v4.x (4.0.1 apr. 2025) | MIT | ✅ **prioritaria** |
| **WinBox.js** | attivo | Apache 2.0 | ✅ |
| **augmented-ui** | v2, attivo | **BSD-2** | ✅ **nuovo** (§11.3) |
| **uPlot** | attivo | MIT | ✅ **nuovo** (§11.3) |
| **three-globe** | attivo | MIT | ✅ **nuovo** (§11.3) |
| **troika-three-text** | attivo | MIT | ✅ **nuovo** (§11.3) |
| **d3** (geo, shape, scale) | attivo | ISC | ✅ **nuovo** (§11.3) |
| **GSAP** | gratuito dal 30 apr. 2025 (v3.13) | "No Charge" | ❌ per ridondanza, non licenza |
| **Vosk** | attivo | Apache 2.0 | ✅ wake a frasi |
| **faster-whisper** | v1.2.1 (31 ott. 2025) | MIT | ✅ **fallback** STT |
| **Kokoro-82M** | v1.0 gen. 2025, 82M, ~327 MB | Apache 2.0 | ✅ **fallback** TTS |
| **Piper** | `rhasspy/piper` **archiviato ott. 2025**; fork `piper1-gpl` | MIT → **GPL-3.0** | ⚠️ preferire Kokoro |
| **MediaPipe** | google-ai-edge, roadmap incerta (#6068), Python ≤3.12 | Apache 2.0 | ⚠️ isolare dietro interfaccia |
| **Tesseract** | attivo v5 | Apache 2.0 | ✅ OCR (§12) |
| **trimesh / build123d** | attivi | MIT / Apache 2.0 | ✅ (§17) |

Nota GSAP: acquisizione Webflow **autunno 2024**, rilascio gratuito **aprile 2025**. Licenza compatibile; scartato solo per non avere due motori di animazione.

---

# 5. Backend LLM — Claude Code

## 5.1 La trappola `--bare`

Claude Code è un **harness agentico**, non un endpoint LLM. La documentazione indica `--bare` come *la* ottimizzazione di avvio, ma:

> *In bare mode, Claude Code never reads OAuth credentials or the system keychain.*

**`--bare` richiede `ANTHROPIC_API_KEY` e non usa l'abbonamento.** Abbonamento e avvio rapido collidono su questo flag.

**Conseguenza**: l'unico modo di eliminare il costo di avvio è **non riavviare mai il processo**. Sessione persistente = requisito.

## 5.2 T1 — processo persistente

```bash
claude \
  --input-format stream-json --output-format stream-json \
  --verbose --include-partial-messages --replay-user-messages \
  --model claude-haiku-4-5-20251001 \
  --allowedTools "" \
  --append-system-prompt-file ~/.config/jarvis-os/voice-persona.md
```

Primo turno: `/config thinking=false`, `/effort low`.

| Flag | Effetto |
|---|---|
| `--input-format stream-json` | processo vivo tra i turni: **elimina il costo di avvio** |
| `--include-partial-messages` | `text_delta` token per token → TTS parte subito |
| `--allowedTools ""` | zero tool nel contesto: il tier vocale **parla** |
| `thinking=false` | elimina i token di ragionamento |

⚠️ **Da verificare**: la documentazione sull'effort descrive i livelli per Opus 5 e Fable 5. **Non ho conferma che Haiku 4.5 li esponga.** Se ignorato, `thinking=false` resta il guadagno principale.

⚠️ **Working directory**: senza `--bare`, Claude Code legge il `CLAUDE.md` corrente **e superiori**. Lanci T1 da `~/.local/share/jarvis-os/voice-cwd/`: dedicata, vuota.

### Latenza misurata sul campo (agosto 2026)

Misura reale di `claude -p` a freddo, da directory vuota, `--allowedTools ""`,
Haiku 4.5, abbonamento Max:

| Esecuzione | Tempo |
|---|---|
| 1 (cache fredde) | 3,16 s |
| 2 | 2,41 s |
| 3 | 2,21 s |
| **mediana** | **2,41 s** |

Il prompt era banale: la generazione vale forse 150 ms. **Gli altri ~2,2 s sono
costo fisso** — spawn di Node, lettura del portachiavi OAuth, discovery della
configurazione, handshake di rete.

**Conclusione operativa**: un `claude -p` per turno conversazionale significherebbe
2,5–3 s prima del primo suono. Inutilizzabile. La sessione persistente elimina
esattamente questi 2,2 s, ed è quindi un **requisito architetturale**, non
un'ottimizzazione.

Autenticazione verificata: `authMethod: claude.ai`, `apiProvider: firstParty`,
`subscriptionType: max`. Conferma che `--bare` resta inutilizzabile (§5.1).

## 5.3 T2 e subagent

```bash
claude -p "$TASK" --output-format stream-json --verbose \
  --model sonnet --allowedTools "Read,Edit,Bash(git *)" \
  --permission-mode dontAsk --max-turns 20 \
  --agents "$(cat ~/.config/jarvis-os/agents.json)"
```

Più CLI simultanee sono possibili. Session ID nel JSON per `--resume`; da v2.1.223 si ritrova da qualunque directory.

Subagent in `.claude/agents/*.md`, frontmatter con `model` e `effort`:

```markdown
---
name: forge
description: Sintesi codice e geometria parametrica
model: sonnet
effort: high
tools: Read, Edit, Bash
---
Sei FORGE. Applichi SEMPRE la disciplina §11.4-11.6: nessun modello 3D
non parametrico, nessun componente che non passi il quality gate, e
nessun componente accettato senza il ciclo di verifica visiva §11.7.
```

Analoghi: `argus` (haiku/low), `edith` (memoria, haiku/low), `veronica` (news, haiku/low).

Nello stream i subagent si distinguono da `parent_tool_use_id` (`null` = principale). Per il testo: `--forward-subagent-text` (v2.1.211+).

## 5.4 Governor

L'uso programmatico **attinge ai limiti dell'abbonamento**. Il pool crediti separato per l'Agent SDK è **sospeso dal 15 giugno 2026**.

```python
class Governor:
    max_concurrent_t2 = 2
    t1_reserved = True                # T1 non va MAI in coda
    max_t2_spawns_per_window = 15     # finestra 60 min
    # su system/api_retry error="rate_limit":
    #   sospendi T2 → degrada → agent.advisory → NON far fallire T1
```

### Log giornaliero di consumo

Il campo `total_cost_usd` arriva in ogni evento `result` dello stream (§21.5).
Il Governor lo accumula in `memory_data/conso/YYYY-MM-DD.jsonl`: token e costo
stimato per turno e per tier.

Serve a sapere quando la finestra di quota sta per chiudersi **prima** che si
chiuda, non dopo. Il pannello telemetria mostra il consumo della finestra
corrente accanto a CPU e RAM.

## 5.5 Memoria — ContextPruner

| Strato | Contenuto | Sopravvive |
|---|---|---|
| **Fatti fissati** | preferenze, decisioni, frasi-wake | ✅ sempre |
| **Verbatim** | ultimi 6 scambi, ultimi file toccati | finestra scorrevole |
| **Compresso** | il resto, ridotto a riassunti | recuperabile |

```python
class ContextPruner:
    def __init__(self, budget_tokens=12000, verbatim_turns=6):
        self.budget, self.verbatim_turns = budget_tokens, verbatim_turns
        self.pinned: list[str] = []
        self.turns: list[dict] = []
        self.digests: list[str] = []

    def build_context(self) -> list[dict]:
        ctx = [{"role":"system","content":"\n".join(self.pinned)}] if self.pinned else []
        return ctx + self.turns[-self.verbatim_turns:]

    def prune(self, count_tokens) -> None:
        while count_tokens(self.build_context()) > self.budget:
            if len(self.turns) <= self.verbatim_turns:
                break
            self.digests.append(self._digest(self.turns.pop(0)))
```

⚠️ **Con T1 persistente, Claude Code gestisce già il proprio contesto.** Il `ContextPruner` serve solo per (a) i fatti fissati da reiniettare quando la sessione viene ricreata e (b) T2, dove ogni spawn parte da zero. **Non duplichi la gestione del contesto di T1**: otterrebbe due gestori in disaccordo.

---

### Substrato: file markdown, non un database opaco

La memoria a lungo termine vive in **file markdown leggibili**:

```
memory_data/
├── sessions/     un .jsonl per sessione — cronologia grezza
├── topics/       note a lungo termine, un .md per argomento
├── conso/        log giornaliero token e costo
└── initiatives/  log degli eventi proattivi
```

Il vantaggio è pratico prima che tecnico: quando JARVIS ricorda una cosa
sbagliata, Lei apre il file e la corregge con un editor. Con un vector store
opaco non può. Un indice SQLite FTS sopra i markdown dà la ricerca senza
togliere l'ispezionabilità.

### Consolidamento notturno

Il `ContextPruner` è **reattivo**: pota quando il budget è saturo, e ciò che
scarta è perso. Serve anche un passaggio **programmato**, che gira quando
nessuno usa il sistema e ha tempo di ragionare su cosa conservare.

```python
# core/memory/consolidate.py
async def nightly_consolidation() -> None:
    """Gira alle 04:00 via scheduler. Rilegge le sessioni del giorno e
    fonde ciò che vale nei topic a lungo termine.

    Usa un processo T2 dedicato con --allowedTools "": legge e scrive solo
    tramite i tool memoria dell'allowlist, mai direttamente.
    NON tocca i fatti fissati: quelli sono dell'utente.
    """
    sessions = load_sessions_since(last_run())
    if not sessions:
        return
    for topic, fragments in group_by_topic(sessions):
        merged = await t2_summarize(topic, fragments)   # zero tool
        write_topic(topic, merged)                      # via allowlist
    mark_run(now())
```

Potatura sotto pressione e consolidamento a mente fredda non sono lo stesso
lavoro. Servono entrambi.

## 5.6 Scadenza OAuth — il caso di degradazione più probabile

Il processo T1 gira per settimane senza riavviarsi: è tutto il punto del design.
Prima o poi **il token OAuth scade**. Senza gestione esplicita accade questo:

```
token scade → claude esce con errore di autenticazione
→ systemd Restart=always rilancia → fallisce di nuovo → loop infinito
→ JARVIS è muto e non dice perché
```

È il fallimento più probabile dell'intero sistema, e va gestito **prima** che
capiti, non dopo.

**Rilevamento.** `authentication_failed` è già uno dei valori del campo `error`
negli eventi `system/api_retry` dello stream (§21.5). Il supervisore lo distingue
da un crash generico.

```python
# core/llm/supervisor.py
AUTH_ERRORS = {"authentication_failed", "oauth_org_not_allowed"}

async def on_stream_event(evt: dict) -> None:
    if evt.get("type") == "system" and evt.get("subtype") == "api_retry":
        if evt.get("error") in AUTH_ERRORS:
            await enter_state("degraded_llm", reason="auth_expired")
            await speak_local(                       # il TTS NON dipende da Claude
                "Signore, la mia sessione è scaduta. "
                "Serve una nuova autenticazione."
            )
            bus.publish("agent.advisory", {
                "level": "critical", "reason": "auth_expired",
                "action": "esegui `claude` e poi /login",
            })
            supervisor.stop_restart_loop()           # NIENTE riavvio a ciclo
            return
```

**Nell'unit systemd** (§22 Fase 9):

```ini
[Service]
Restart=always
RestartSec=5
# il codice di uscita dell'auth NON deve innescare il riavvio
RestartPreventExitStatus=41
StartLimitBurst=5
StartLimitIntervalSec=120
```

Verifichi il codice di uscita reale sul Suo sistema e lo sostituisca a `41`:
la documentazione non pubblica una tabella completa dei codici di `-p`, quindi
lo determini empiricamente lasciando scadere una sessione di prova.

**Cosa continua a funzionare in `degraded_llm`:** le frasi-comando T0, la
telemetria, il file manager, l'intera interfaccia. Non toccano l'LLM. È la
proprietà che rende il wake a frasi (§7.2) prezioso ben oltre la latenza.

**Cosa NON fare:** tentare la riautenticazione automatica. Richiede un browser
e un'interazione umana; automatizzarla significa o fallire in silenzio o
conservare credenziali dove non devono stare.

## 5.7 `voice-persona.md` — il system prompt di T1

**Il testo vive in `config/voice-persona.md`, e questa sezione non lo
trascrive.** Passato con `--append-system-prompt-file`.

> ⚠️ **Fino al 26 agosto 2026 §5.7 lo trascriveva, e le due copie erano già
> divergenti**: SPEC scriveva «è più naturale», il file `e' piu' naturale`.
> Nessun test lo rilevava, nessun controllo d'installazione, e la copia che
> parla — quella in `~/.config/` — non ha storia git. La cura non è
> confrontare due copie: è **non averne due**. `tests/test_la_persona_e_il_barge_in_ricorda.py`
> si rompe se questa sezione ricomincia a trascriverla.

La terza copia — `~/.config/jarvis-os/voice-persona.md`, quella che il core
legge davvero — non può essere verificata da un test (`tests/conftest.py`
spiega perché un test che legge `~/.config/` passa o fallisce a seconda della
macchina). La controlla **`jarvis doctor`**, con la stessa forma con cui
controlla la unit systemd installata: non è una proprietà del codice, è uno
stato dell'installazione.

### Il budget dei token — deroga dichiarata

La stesura precedente imponeva «**sotto i ~250 token**: viaggia in ogni turno».
Il testo del 26 agosto 2026 **sfonda quel tetto**, e le tre cose vanno dette in
ordine:

**① La premessa era falsa.** T1 è un processo **persistente**
(`--input-format stream-json`, §5.2): `--append-system-prompt-file` è un flag
passato **una volta**, all'avvio del processo, e `ask()` scrive sullo stdin
soltanto il messaggio dell'utente. La persona **non può** viaggiare a ogni
turno, perché non esiste il meccanismo per rimandarla. Il tetto era tarato
sulla paura sbagliata.

**② Il numero di token è NON MISURABILE con gli strumenti di questo progetto.**
Nessun tokenizer è fra le dipendenze e non se ne aggiunge uno di soppiatto
(`CLAUDE.md`). Ho provato a leggerlo da `usage` del CLI: è dominato da
`cache_creation_input_tokens`, che fra esecuzioni **identiche** ha oscillato fra
**13 082 e 16 643**. Un delta di duecento token non si estrae da quel rumore.

Ciò che è misurato, e che è un rapporto e non un conteggio:

| | vecchia | nuova | rapporto |
|---|---|---|---|
| byte | 946 | 2 393 | **2,53×** |
| parole | 152 | 399 | **2,63×** |

**③ Il vincolo vero non è il costo, ed è quello che resta in piedi.** Un system
prompt lungo su Haiku **diluisce l'aderenza**: più righe ci sono, meno pesa
ciascuna. Questa è una deroga **dichiarata**, non un tetto sforato in silenzio,
e la sua verifica non è un conteggio — è se JARVIS suona come JARVIS. Si misura
parlandogli.

### Che cosa la stesura del 26 agosto corregge

- **«l'intelligenza di supervisione del Creatore»** — «Creatore» è lessico di
  Ultron e Visione. JARVIS dice «Signore».
- **«rispondi che te ne occupi e basta»** — istruiva a dichiarare un esito che
  T1 non può verificare: se l'instradamento fallisce, JARVIS ha mentito.
  Contraddiceva «Se non sai, lo dici» tre righe sotto, e §16.
- **«Ironia asciutta quando serve»** — troppo vago per produrre alcunché.
  Adesso c'è la meccanica dell'ironia e la sua collocazione: dopo la risposta,
  mai al posto della risposta.
- **«Due o tre frasi»** — sbagliato come regola. Una domanda che chiede una
  spiegazione deve ottenerla intera. Sostituito da un criterio di giudizio.
- Aggiunte: **anticipare**, **dissentire**, la conseguenza dello streaming (la
  prima frase è già pronunciata prima che il modello finisca), e la regola sul
  contenuto non fidato — T1 ha zero strumenti ma **riceve** testo di notizie e
  di pagine web.

Le righe di **LIMITI** sono quelle che contano: T1 gira con `--allowedTools ""`
e senza di esse promette azioni che non può compiere.

# 6. Filesystem, YouTube, operazioni reali

## 6.1 Modello di sicurezza

Le operazioni file vivono nel **core Python**, non in Electron: un renderer con accesso al disco e contenuti web in `<webview>` è inaccettabile.

```python
# core/tools/files.py
from pathlib import Path
from pydantic import BaseModel, field_validator
from core.tools.registry import Tool, ToolResult, register

WORKSPACE = Path.home() / "JARVIS"
ALLOWED_ROOTS = [WORKSPACE, Path.home()/"Documenti", Path.home()/"Scaricati"]

def _safe(p: str) -> Path:
    """Il controllo va DOPO resolve(): è resolve() che elimina i '..'."""
    rp = Path(p).expanduser().resolve()
    if not any(rp == r or r in rp.parents for r in ALLOWED_ROOTS):
        raise ValueError(f"path fuori dalle radici consentite: {rp}")
    return rp

class CreateFileArgs(BaseModel):
    path: str
    content: str = ""
    @field_validator("path")
    @classmethod
    def _v(cls, v): _safe(v); return v

async def _create_file(a: CreateFileArgs) -> ToolResult:
    try:
        p = _safe(a.path)
        if p.exists():
            return ToolResult(ok=False, error="esiste già; usa overwrite_file")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(a.content, encoding="utf-8")
        return ToolResult(ok=True, output={"path": str(p), "bytes": len(a.content)})
    except Exception as e:
        return ToolResult(ok=False, error=str(e))

register(Tool(name="create_file", description="Crea un file nelle radici consentite.",
              args_schema=CreateFileArgs, side_effect=True,
              gesture_allowed=False, handler=_create_file))
```

| Tool | side_effect |
|---|---|
| `list_dir`, `read_file`, `search_files`, `stat_path` | ❌ |
| `create_file`, `create_folder`, `move_path`, `copy_path` | ✅ |
| `trash_path` | ✅ **cestino, mai unlink** |
| `organize_folder` | ✅ |

⚠️ **Nessun `delete` reale.** Solo `send2trash`. Un agente che sbaglia deve poter essere annullato.

## 6.2 Conferma umana

```
proposta → validazione pydantic → topic `fs.confirm_request` con riepilogo
→ UI mostra il PATH ASSOLUTO RISOLTO, non quello richiesto
→ conferma → esegue → `fs.result`   |   rifiuto → ToolResult(ok=False)
```

**Batch**: per `organize_folder` su 200 file, **una sola conferma** ma con il piano completo mostrato prima. Mai 200 conferme; mai zero.

## 6.3 YouTube e web nell'ambiente

```javascript
function createWebPanel(url, title) {
  const box = new WinBox({ title, class:["jarvis-panel"], width:960, height:540 });
  const wv = document.createElement("webview");
  wv.setAttribute("src", url);
  wv.setAttribute("partition", "persist:jarvis");   // sessione isolata
  wv.setAttribute("allowpopups", "false");
  wv.style.cssText = "width:100%;height:100%;border:0;background:#0a1014";
  box.body.appendChild(wv);
  return { box, wv };
}
```

```javascript
new BrowserWindow({ webPreferences: {
  contextIsolation: true,      // obbligatorio
  nodeIntegration: false,      // obbligatorio
  sandbox: true,
  webviewTag: true,
  preload: path.join(__dirname, "preload.js"),
}});
```

Il preload espone **solo** un bridge tipizzato verso il WebSocket. Mai `require`, `fs`, `child_process`.

**YouTube**: riproduzione normale funziona; **DRM** richiede il CDM Widevine, non impacchettato di default. Per il controllo programmatico usi l'**IFrame Player API**, non il DOM di youtube.com (il DOM cambia, l'API no). Per la ricerca, **YouTube Data API v3**.

---

# 7. Voce

## 7.1 La catena

```
microfono (PipeWire)
  → VAD Silero      ~5 ms   gate più economico
  → Vosk grammar    ~20 ms  ascolto continuo su frasi note (LOCALE, sempre)
  → match? no → torna al VAD; nulla lascia la macchina
            sì ↓
  → STT: Deepgram Flux (primario) | RealtimeSTT (fallback)
  → T0 grammatica (<10 ms) → azione     oppure T1 claude persistente
  → token → TTS streaming: Deepgram Flux (primario) | Kokoro (fallback)
  → audio out + trascrizione
```

**Nota sull'ordine dei provider**: Lei ha scelto Deepgram come principale. Il wake a frasi resta **sempre locale** — mandare l'audio a Deepgram ventiquattr'ore al giorno sarebbe insostenibile per costo e per privacy. Vosk apre il flusso; solo dopo il match l'audio va in rete.

## 7.2 Wake a frasi personalizzate

openWakeWord lavora su wake word addestrate, non su frasi arbitrarie modificabili. **Vosk con riconoscimento vincolato a grammatica** accetta una lista chiusa di frasi e ignora il resto. Modello italiano piccolo ~50 MB, Apache 2.0, CPU trascurabile, frasi = **configurazione**.

```python
# core/voice/wake.py
import json, vosk

class PhraseWake:
    def __init__(self, model_path: str, phrases: list[str], sample_rate: int = 16000):
        self._model_path = model_path
        self._phrases = [p.lower().strip() for p in phrases]
        grammar = json.dumps(self._phrases + ["[unk]"])   # [unk] assorbe il resto
        self._rec = vosk.KaldiRecognizer(vosk.Model(model_path), sample_rate, grammar)
        self._rec.SetWords(False)

    def feed(self, pcm: bytes) -> str | None:
        if self._rec.AcceptWaveform(pcm):
            text = json.loads(self._rec.Result()).get("text", "").strip()
            if text and text != "[unk]" and text in self._phrases:
                return text
        return None

    def set_phrases(self, phrases: list[str]) -> None:
        self.__init__(self._model_path, phrases)          # hot reload
```

```toml
[voice.wake]
model = "~/.local/share/jarvis-os/vosk-model-small-it-0.22"

[[voice.wake.phrases]]
say = "jarvis"
action = "listen"

[[voice.wake.phrases]]
say = "papà è a casa"
action = "scene:welcome_home"        # esegue, salta lo STT

[[voice.wake.phrases]]
say = "jarvis buonanotte"
action = "scene:goodnight"
```

**Il guadagno non ovvio**: una frase può essere **direttamente un comando**. *"Papà è a casa"* esegue una scena in **~30 ms**, senza STT né LLM — e **funziona offline**, anche con Deepgram come primario.

**Tre regole:**
1. Frasi di **almeno 2 parole** tranne il nome. Le monosillabiche generano falsi positivi continui.
2. **Conferma acustica breve** (tono di 80 ms, non una voce) al riconoscimento.
3. **Log locale dei trigger** con timestamp. Se JARVIS si sveglia da solo, deve poter capire perché.

**Alternativa** se Vosk non desse precisione: Picovoice Porcupine, licenza gratuita per uso personale (il Suo caso, §19). Più accurato, ma le keyword si generano sulla loro console.

## 7.3 STT — Deepgram primario

| | **Deepgram (primario)** | Locale (fallback) |
|---|---|---|
| Endpoint | `wss://api.deepgram.com/v2/listen` | — |
| Modello | `flux-general-multi` (**supporta l'italiano**) | faster-whisper `base` int8 |
| Turn detection | **nativa nel modello** | Silero VAD |
| Parametri | `eot_threshold` 0.5–0.9, `eager_eot_threshold` 0.3–0.9, `eot_timeout_ms`, `keyterm` | — |

Auth: `Authorization: Token <API_KEY>`.

**Tre trappole:**
1. `flux-general-en` **non** accetta `language_hint`; solo `flux-general-multi`.
2. `EagerEndOfTurn` genera risposte speculative: **+50–70% chiamate LLM**. Off di default.
3. Non specifichi `encoding`/`sample_rate` con audio containerizzato.

## 7.4 TTS che parla mentre le parole vengono generate

```python
class TTSProvider(Protocol):
    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]: ...
    async def flush(self) -> None: ...
    async def interrupt(self) -> None: ...
```

`stream()` accetta un **async iterator di testo**: i token di Claude Code entrano nel sintetizzatore mentre vengono generati. Aspettare la frase completa costa 500–1500 ms irrecuperabili.

**I due provider vanno trattati diversamente:**

**Deepgram Flux TTS** (`wss://api.deepgram.com/v2/speak`) accetta i token direttamente. La documentazione è esplicita: in modalità TOKEN i token vengono inviati senza bufferizzare per confini di frase, perché il modello li determina internamente. Aggregare **aggiunge solo latenza**. Mantiene lo stato acustico tra i turni su una connessione, preservando prosodia.

**Kokoro** sintetizza per enunciato: serve un **chunker**.

```python
# core/providers/chunker.py
import re
from typing import AsyncIterator

_BOUNDARY = re.compile(r"[.!?…](?:\s|$)|[;:](?:\s|$)|,(?:\s|$)")
MIN_CHARS, MAX_CHARS = 40, 220

async def clause_chunks(tokens: AsyncIterator[str]) -> AsyncIterator[str]:
    """Il PRIMO frammento ha soglia dimezzata: ciò che l'orecchio percepisce
    come reattività è QUANDO JARVIS inizia a parlare."""
    buf, first = "", True
    threshold = MIN_CHARS // 2
    async for tok in tokens:
        buf += tok
        m = None
        if len(buf) >= threshold:
            for m in _BOUNDARY.finditer(buf):
                pass
        if (m and len(buf) >= threshold) or len(buf) >= MAX_CHARS:
            cut = m.end() if m else MAX_CHARS
            chunk, buf = buf[:cut].strip(), buf[cut:]
            if chunk:
                yield chunk
                if first: first, threshold = False, MIN_CHARS
    if buf.strip():
        yield buf.strip()
```

**Il chunker va SOLO davanti a Kokoro.** Davanti a Deepgram Flux è un danno.

```python
def make_tts_pipeline(s: Settings):
    if s.voice.tts_provider == "deepgram":
        return DeepgramFluxTTS(...)                   # token diretti
    return ChunkedTTS(KokoroTTS(...), clause_chunks)  # fallback
```

**Barge-in**: `tts.interrupt()`. Su Flux TTS l'`Interrupt` riporta `text_spoken` — **cosa Lei ha effettivamente udito**. Lo salvi in memoria, altrimenti JARVIS crede di aver detto una frase mai sentita.

> ⚠️ **Quella metà è fatta, l'altra no — chiusa il 26 agosto 2026.**
> `text_spoken` finisce in `sessions/`, ma `ClaudeT1._drena()` consuma la
> generazione abbandonata e la **scarta**: dal punto di vista del modello quella
> risposta è stata detta per intero. Al turno dopo JARVIS può dire «come Le
> dicevo» di una spiegazione mai udita, e memoria su disco e sessione di T1
> tengono due versioni diverse della stessa conversazione.
>
> La cura è una **cornice di sistema** (`core/llm/sistema.py`) anteposta al
> turno successivo **solo dopo un'interruzione**: dichiara in italiano di non
> essere parole del Signore, e `<sistema_jarvis>` è neutralizzato dentro il
> contenuto non fidato — un titolo di giornale non può prendere la voce del
> core.
>
> Col TTS locale `text_spoken` non esiste: ciò che si sa è il testo **mandato
> al sintetizzatore**, un limite superiore. La cornice lo dice («al più
> questo, e forse meno») invece di affermare più del dato.


## 7.5 Budget di latenza

| Percorso | Composizione | Totale |
|---|---|---|
| **Frase-comando** | VAD 5 + Vosk 20 + azione 5 | **~30 ms**, offline |
| **Comando T0** | + STT streaming 150 + grammatica 10 | **~200 ms** |
| **Conversazione T1** | + primo token 300–900 + primo chunk TTS 150 | **0,6–1,3 s al primo suono** |

---

## 7.6 Il parser T0 — `core/llm/grammar.py`

Il componente più critico per la latenza dell'intero sistema. Deve stare sotto i
10 ms: niente LLM, niente embedding, niente regex compilate a runtime.

```python
# core/llm/grammar.py
"""Router T0: comandi deterministici senza LLM.

Il linguaggio dei comandi è finito: un parser a grammatica è più veloce di
qualunque modello, gratuito, e non allucina. Copre circa l'80% di ciò che
l'utente dirà a JARVIS.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Intent:
    tool: str
    args: dict
    confidence: float = 1.0

# Ogni regola: (pattern compilato, tool, mappatura dei gruppi).
# Compilati UNA VOLTA all'import.
_RULES: list[tuple[re.Pattern, str, callable]] = []

def _rule(pattern: str, tool: str, mapper=lambda m: {}):
    _RULES.append((re.compile(pattern, re.IGNORECASE), tool, mapper))

# --- pannelli --------------------------------------------------------
_rule(r"\b(?:apri|mostra)\s+(?:il\s+|la\s+)?(?P<p>telemetria|console|file|"
      r"globo|agenti|news|sorgente|impostazioni)\b",
      "open_panel", lambda m: {"panel": m.group("p").lower()})
_rule(r"\bchiudi\s+(?:il\s+|la\s+)?(?P<p>\w+)\b",
      "close_panel", lambda m: {"panel": m.group("p").lower()})
_rule(r"\b(?:nascondi tutto|via tutto)\b", "hide_all")
_rule(r"\baffianca\b", "tile_panels")

# --- workspace -------------------------------------------------------
_rule(r"\bworkspace\s+(?P<n>[1-4]|uno|due|tre|quattro)\b",
      "switch_workspace", lambda m: {"n": _num(m.group("n"))})

# --- sistema ---------------------------------------------------------
_rule(r"\b(?:come sta|stato)\s+(?:la\s+)?(?:cpu|memoria|sistema)\b",
      "system_status")
_rule(r"\b(?:cosa|chi)\s+(?:sta\s+)?rallent\w+\b", "top_processes")
_rule(r"\bvolume\s+(?P<v>\d{1,3})\b",
      "set_volume", lambda m: {"level": min(100, int(m.group("v")))})
_rule(r"\b(?:silenzio|muto)\b", "mute")

# --- meta-comandi: non chiedono una cosa, chiedono lo STATO -----------
# Frase deterministica (T0) che innesca un fan-out di subagent (T2).
_rule(r"\b(?:riassumimi la giornata|briefing|fammi il punto)\b", "brief_me")
_rule(r"\bcosa (?:richiede|serve|vuole) la mia attenzione\b", "needs_attention")
_rule(r"\b(?:come stiamo|stato dei sistemi|diagnostica)\b", "doctor")

# --- file ------------------------------------------------------------
_rule(r"\bcerca\s+(?:il\s+file\s+|i\s+file\s+)?(?P<q>.+?)(?:\s+nei file)?$",
      "search_files", lambda m: {"query": m.group("q").strip()})

_WORDS = {"uno": 1, "due": 2, "tre": 3, "quattro": 4}
def _num(s: str) -> int:
    return int(s) if s.isdigit() else _WORDS[s.lower()]

def parse(text: str) -> Intent | None:
    """Intent se il testo è un comando noto, altrimenti None.

    None NON è un errore: è la risposta corretta per il ~20% di frasi che
    devono andare a T1 o T2. Costo tipico: 5-20 microsecondi.
    """
    t = " ".join(text.strip().lower().split())
    for pattern, tool, mapper in _RULES:
        m = pattern.search(t)
        if m:
            return Intent(tool=tool, args=mapper(m))
    return None
```

**Tre note di progetto:**

1. **L'ordine delle regole conta.** La ricerca file è per ultima perché il suo
   pattern è il più permissivo: in cima catturerebbe tutto.
2. **`parse()` ritorna `None`, non solleva.** `None` è la risposta corretta per
   le frasi conversazionali.
3. **Il test di accettazione è un file, non un'opinione.** `tests/t0_corpus.py`
   con almeno 100 frasi etichettate: 80 comandi con l'intento atteso e 20 frasi
   conversazionali che devono dare `None`. Misuri il tempo mediano. È l'unico
   modo per sapere se i 10 ms reggono e se il parser non sta rubando frasi a T1.

⚠️ **Il blocco qui sopra e' una TRACCIA, non lo stato del file.** Ha ancora
`close_panel` con `\w+`, che e' il furto poi corretto («chiudi un occhio
stavolta»). Le regole vive stanno in `core/llm/grammar.py` e si leggono da li';
qui restano solo i principi che sopravvivono a una riscrittura. E' la stessa
deroga dichiarata per §5.7 e la persona: una specifica che trascrive un file
diverge, e la divergenza non si vede.

**4. L'imperativo prende il pronome ENCLITICO.** apri/aprimi/aprila/apriti,
mostra/mostrami, chiudi/chiudilo: e' la forma normale del parlato italiano, e
un comando che non risponde a «aprimi la telemetria» viene letto come un
guasto. Si allarga **solo dove l'oggetto e' un'allowlist**: davanti a un
oggetto a testo libero — la coda di `search_files`, la query di YouTube — un
pronome in piu' diventa una query. Il corpus tiene «apriti cielo» e «mostrati
un po' piu' paziente» fra le frasi da non rubare, e restano salve perche'
`cielo` non e' un pannello: la sicurezza viene dall'allowlist, non dalla
prudenza.

**5. Cio' che T0 NON riconosce lascia una riga.** Ogni enunciato produce una
riga di `azione` nel diario con la strada che ha preso — `t0`, `t1`, `nessuna`
— e, quando non e' stato riconosciuto, il testo che non ha trovato un comando.
Non si deriva da `azione`: `azione is None` non distingue «delegato» da
«caduto». `quasi_comando()` etichetta le frasi che **cominciano** con un
imperativo noto: e' cosi' che il corpus dei comandi mancanti cresce da solo
invece di essere immaginato.

⚠️ **Quell'etichetta non entra nel contesto di T1.** Misurato sulle 53 frasi
conversazionali del corpus: 8 falsi positivi, il **15,1 %**. Una frase su sette
porterebbe a JARVIS un «nessun comando riconosciuto» in mezzo a un discorso.

⚠️ **E la persona di §5.7 dice a T1 una cosa che non e' vera.** «Quelle azioni
le fa il sistema prima di arrivare a te»: T1 e' raggiunto **soltanto** quando
T0 ha mancato, quindi la premessa vale nel caso che non capita mai. Il primo
comando detto al microfono — «apriti i pannelli telemetria» — ha avuto in
risposta «Me ne occupo», che la persona prescrive, per un'azione che nessuno
avrebbe compiuto. Difetto **aperto**: il testo e' dell'utente e la frase giusta
e' una scelta di carattere, non una correzione.


# 8. Impostazioni e chiavi

**Default invertiti**: Deepgram primario, locale fallback automatico.

```toml
# ~/.config/jarvis-os/settings.toml     (0600)
[voice]
stt_provider = "deepgram"       # primario
tts_provider = "deepgram"
fallback_on_error = true        # ricade sul locale se la chiave manca o la rete cade
fallback_stt = "local"
fallback_tts = "local"
deepgram_stt_model = "flux-general-multi"
eot_threshold = 0.7
eager_eot = false               # ⚠ true = +50-70% chiamate LLM
whisper_model = "base"          # solo fallback
kokoro_voice  = "bm_george"     # solo fallback

[llm]
backend = "claude_code"
t1_model = "claude-haiku-4-5-20251001"
t1_cwd   = "~/.local/share/jarvis-os/voice-cwd"
t2_model = "sonnet"
max_concurrent_t2 = 2

[fs]
workspace = "~/JARVIS"
allowed_roots = ["~/JARVIS", "~/Documenti", "~/Scaricati"]
trash_only = true

[vision]
enabled = true
scope = "app"                   # deciso: solo l'app
engine = "tesseract"

[news]
enabled = true
max_interruptions_per_hour = 3
topic_ttl_minutes = 30
```

```toml
# ~/.config/jarvis-os/secrets.toml      (0600, SEPARATO, in .gitignore)
deepgram_api_key = ""
guardian_api_key = ""
youtube_api_key  = ""
```

**Regola di fallback**: all'avvio, se `deepgram_api_key` è vuota → JARVIS parte in locale e lo **annuncia**. A runtime, se Deepgram fallisce (chiave invalida, 429, rete) → ricade sul locale entro il turno successivo e lo annuncia. Non deve mai restare muto in silenzio.

**Test connessione obbligatorio**: apre il WebSocket, manda 200 ms di silenzio, verifica l'handshake, chiude.

Chiave mascherata con toggle "mostra". **Mai nei log**, nemmeno in debug.

---

# 9. Contesa GPU

Senza LLM locale la pressione crolla, ma quattro consumatori competono.

| Componente | VRAM | Note |
|---|---|---|
| faster-whisper `base` int8 | ~150 MB | **solo fallback** |
| faster-whisper `large-v2` int8 | 2926 MB | benchmark SYSTRAN |
| Kokoro-82M | ~330 MB, **CPU** | trascurabile |
| Vosk small it | ~50 MB, **CPU** | trascurabile |
| MediaPipe Hand Landmarker | **CPU a 30fps** | `delegate=CPU` obbligatorio |
| Tesseract | **CPU** | trascurabile |
| Florence-2-large (opz.) | ~1,2 GB caricamento, **3–4 GB picco** | |
| Scena three.js + PixiJS 60fps | ~1–2 GB (stima prudenziale) | **il consumatore principale** |

**Con Deepgram primario la GPU è quasi tutta per la scena 3D.** È un beneficio collaterale della Sua scelta.

| VRAM | Praticabile |
|---|---|
| **4 GB** | scena 3D + Deepgram. Fallback locale solo con scena a 30fps |
| **8 GB** | tutto, VLM on-demand |
| **12 GB+** | tutto co-residente |

### ⚠️ Nota APU — questa tabella vale per una GPU **discreta** (rev 5.2)

Su una GPU integrata la «VRAM» non è memoria in più: è un **carveout della
stessa RAM di sistema**. Caricare 3 GB «in VRAM» non libera un byte di RAM, ed
è lo stesso silicio visto da un'altra angolazione.

Misurato sulla macchina di sviluppo (AMD Radeon 840M, `amdgpu`):

| | |
|---|---|
| `mem_info_vram_total` | 8,00 GiB |
| RAM di sistema | 22 GiB totali, ~10 GiB disponibili |

Letta alla lettera, la tabella qui sopra collocherebbe questa macchina nella
riga da **8 GB** — «tutto, VLM on-demand». La lettura corretta è che gli 8 GiB
e i 22 GiB **non si sommano**.

**Regola su memoria unificata**:

```
headroom = min(VRAM libera, RAM disponibile)
```

`core/gpu_scheduler.py` la applica, e `core/platform/base.py::GpuMemory` porta
un flag `unified` letto dal driver, non una costante: su una GPU discreta
`headroom` torna a essere la sola VRAM libera, che è ciò che questa sezione
intende.

Il riconoscimento usa due segnali — classe PCI `0x038000` e
`vis_vram_total == vram_total` — e **nel dubbio assume unificata**: sbagliare
in quella direzione fa rifiutare un caricamento che sarebbe entrato, sbagliare
nell'altra manda il sistema in swap mentre lo scheduler riporta verde.

**Degradazione** (`core/gpu_scheduler.py`): MediaPipe sempre CPU → scena da 60 a 30fps se il VLM è in inferenza → VLM on-demand scaricato dopo 60 s → durante la finestra vocale critica VLM sospeso.

**Regola dura**: monitorare la VRAM e **rifiutare** di caricare un modello se manca headroom, invece di lasciar spillare in RAM via PCIe.

---

# 10. Design system

## 10.1 Token — sorgente unica di verità

```css
/* ui/src/style/tokens.css — NESSUN valore letterale altrove */
:root {
  /* ⚠️ NON E' UNA SCALA MONOTONA, ed e' cosi' di proposito.
     Il riferimento (docs/design-reference/famiglia-a/01) ha TRE registri, non
     una rampa continua:

       PAVIMENTO        L 19        la scrivania, e nient'altro
       BANDA DI SUPERFICIE  L 30-37 barra, dock, pannelli, rilievi
       RIEMPIMENTI DI STATO L 66-146 solo dove c'e' uno STATO da dire

     Barra e pannello stanno nella STESSA banda: nel riferimento la barra si
     distingue per densita' d'inchiostro — decine di micro-etichette su una
     linea di base — non per il fondo. Chi trovasse --bg-deep (30) quasi
     uguale a --bg-panel (31) e volesse "sistemare" la rampa distruggerebbe
     proprio la cosa misurata. */
  /* Il suolo di una VISTA, non una superficie della scrivania.
     Misurato sul riferimento, non scelto: `famiglia-a/01` tiene il 5,2 % del
     fotogramma sotto L 16, e sta TUTTO nei pannelli di globo e mappa — 28-41 %
     di quelle celle — col dominante #03080c a L 7,2. Da noi il bin 0 era
     VUOTO.
     Non e' un gradino della rampa delle superfici e non ci partecipa: sta
     sotto il pavimento perche' una finestra sullo spazio e' piu' scura della
     stanza da cui la si guarda. Chi lo usasse per una superficie di chrome
     romperebbe il gradino di §10.5 regola 1. */
  --bg-abyss:#05080b;                                     /* L   8 suolo di vista */
  --bg-void:#0f1418;                                      /* L  19 pavimento  */
  --bg-deep:#1a1f23; --bg-panel:#13212a; --bg-raised:#1e2631;  /* L 30 31 37 */

  /* RIEMPIMENTI DI STATO — tre, non sei.
     La prima stesura (rev 5.8) ne dichiarava sei, e i due piu' bassi erano
     duplicati di --bg-panel e --bg-raised alla luminanza giusta: la leva era
     la superficie di base, non un token nuovo accanto a essa. La misura lo ha
     detto — il 71,2 % della scrivania e' --bg-panel e solo il 2,4 % e' il
     fondo. Un riempimento non si mette dove c'e' gia' una superficie: si mette
     dove c'e' uno stato da mostrare. */
  --fill-1:#32464f;   /* L  66  cella attiva, intestazione di tabella        */
  --fill-2:#336276;   /* L  89  pannello acceso, selezione                   */
  --fill-3:#4d6d78;   /* L 103  evidenza dentro una griglia densa            */
  --manila:#b48d64;   /* L 146  cartelle e contenitori                       */
  /* La cartella ILLUMINATA — §26.5: «si illumina a --manila piu' chiaro
     mentre il puntatore e' sopra». Stessa tinta, non un colore nuovo: i
     rapporti G/R e B/R sono identici a --manila (0,782 e 0,555), e la
     luminanza sale di 33 punti. Non e' --amber (L 185, B/R 0,442): quello
     e' l'accento caldo di §11.1 e significa ATTENZIONE, non «il puntatore
     e' qui». */
  --manila-viva:#dcac7a;  /* L 179  cartella sotto il puntatore            */

  /* ICONE DEL CATALOGO — §26.3. Sono l'unica cosa piena e chiara della
     scrivania, e la differenza piu' grande col dock di oggi: nel riferimento
     la fascia del catalogo ha il 26,2 % di superficie accesa, la nostra il
     2,8 %, perche' le nostre icone sono TESTO a L 96 e le sue sono forme
     RIEMPITE. Nessuno dei token esistenti arriva lassu' senza essere il
     colore del dato. */
  --icona:#a2adb1;      /* L 171  riempimento dell'icona                      */
  --icona-viva:#d4dcdf; /* L 219  sotto il puntatore, o selezionata           */

  --cy-900:#123840; --cy-700:#227482; --cy-500:#4dd0e1;
  --cy-300:#7fdbe8; --cy-100:#cdeef3;

  --amber:#f0b06a;  /* attenzione */
  --rust:#ff5a3c;   /* critico — MAX 10% della superficie colorata */

  /* ⚠️ RITARATI DUE VOLTE, e la seconda l'ha imposta §10.5.
     Prima erano scelti contro --bg-panel a L 18; a L 31 tre soglie WCAG erano
     cadute (R81) e li avevamo rifatti: 4,53 · 3,04 · 3,03.
     Poi §10.5 ha portato il corpo del pannello da --bg-panel (L 31) a
     --bg-raised (L 37), che e' il valore MISURATO sul riferimento — e un fondo
     piu' chiaro toglie contrasto invece di darlo. Misurato: --txt-dim era
     sceso a 4,21:1 (sotto il 4,5 di AA) e --txt-ghost a 2,81:1 (sotto il 3,0).
     Il caso che decideva era lo STATO VUOTO: «NESSUNA SORGENTE COLLEGATA» sta
     in --txt-ghost, ed e' l'unica cosa che l'invariante 23 pretende si legga
     quando non ci sono dati. Adesso, sul corpo a L 37: 4,93 · 3,04 · 3,76. */
  --txt-primary:#cdeef3; --txt-dim:#7d979d; --txt-ghost:#66838a;

  --line-hair:0.5px; --line-base:1px; --line-bold:2px;      /* TRE pesi */
  --s-1:4px; --s-2:8px; --s-3:16px; --s-4:32px; --s-5:64px;
  --t-micro:8.5px; --t-data:11px; --t-label:12px;
  --t-body:14px; --t-title:20px;
  /* ⚠️ IL SESTO GRADINO, aggiunto il 22 agosto 2026 — e §11.6 diceva CINQUE.
     Non e' una deroga di comodo: e' la misura che mancava. Il riferimento
     famiglia-a/03 porta una lettura numerica alta 28 px su un'immagine larga
     901, cioe' il **3,1 % della larghezza**; sui nostri 1536 fa 48. Nessuno dei
     cinque gradini ci arriva — il piu' alto, --t-title, e' il corpo dei numeri
     di UNA CELLA del calendario, non di una lettura che occupa il pannello.
     Il pannello che lo chiede (panels/lettura.js) lo derivava come
     «calc(--t-title * 2.4)»: la stessa cifra, ma nascosta dentro un componente
     e invisibile all'audit, che infatti la bocciava come 48 px letterali.
     Un gradino dichiarato si puo' contestare; una moltiplicazione dentro un
     file no. Chi volesse tornare a cinque tolga questo e riporti la lettura a
     --t-title, sapendo che perde il 3,1 % misurato.

     ⚠️ **E' RISERVATO: UNA SOLA DICHIARAZIONE IN TUTTO IL SISTEMA.** Deciso il
     23 agosto 2026, chiudendo il cancello di governance di
     `docs/acceptance/DEROGHE-7dad2b8.md`. Il difetto vero della prima stesura
     non era il numero — 48 px sono misurati — era che un gradino nascosto
     dentro un componente **non si puo' contestare**: per trovarlo bisognava
     leggere quel file. Un token si vede; un token con un tetto non si diffonde.
     Il tetto lo impone un test che CONTA i consumatori
     (`tests/test_tokens.py`), non una raccomandazione: il secondo pannello che
     ne avesse bisogno fa cadere la build, e allora e' un'altra decisione, non
     un'abitudine presa senza accorgersene.
     Consumatore unico, oggi: `ui/src/panels/lettura.js`. */
  --t-display:48px;                        /* SEI gradini — il sesto RISERVATO */

  --font-ui:"Barlow Semi Condensed",sans-serif;
  --font-mono:"IBM Plex Mono",monospace;

  --grid:110px; --gap:8px; --radius:0;                      /* SEMPRE zero */

  /* ⚠️ L'OMBRA DI CONTATTO, ed e' un token perche' era gia' scritta due volte.
     §10.1 la misura sul riferimento — l'unica ombra portata misurabile nel
     concept, quella del riquadro video: scostamento ~2 px, raggio ~3 px, nero
     ad alpha ~0,18 — e l'invariante 19 la ammette SOLO dove una superficie ne
     copre un'altra. La usa `.jarvis-panel` qui sotto, e la usa la piastra del
     plinto, che poggia sul pavimento in prospettiva.
     Finche' viveva come letterale in due posti, l'audit la lasciava passare
     nel primo (e' in questo file) e la bocciava nel secondo — cioe' la regola
     dipendeva da dove era scritta invece che da che cos'era. */
  --ombra-contatto: 0 2px 3px rgba(0,0,0,.18);
}

/* ⚠️ RIFATTO SULLA MISURA, rev 5.16. La stesura precedente aveva tre difetti
   che l'analisi del concept ha reso visibili tutti insieme:

   1. DUE ALONI INTERNI CALDI (inset … rgba(255,220,180,.12) e
      rgba(240,176,106,.04)). Sono esattamente l'ALONE che l'invariante 19
      vieta — luce che non esiste, aggiunta dentro il pannello. Rev 5.13 ha
      riformulato l'invariante per ammettere l'OMBRA e vietare l'alone: queste
      due righe erano dalla parte sbagliata della distinzione.

   2. FONDO SEMITRASPARENTE piu' `backdrop-filter`. Misurato sul riferimento,
      il corpo di un pannello e' OPACO e PIATTO: #1e2631 identico a quattro
      quote diverse del calendario, che e' esattamente --bg-raised. Il velo
      sfocato non c'e' da nessuna parte, e il filtro non aveva effetto
      visibile perche' sotto il pannello c'e' il pavimento.

   3. OMBRA DIECI VOLTE TROPPO GRANDE. L'unica ombra portata misurabile nel
      concept — quella del riquadro video — ha scostamento ~2 px, raggio ~3 px
      e nero ad alpha ~0,18. La nostra era 0 26px 60px alpha 0,5.

   Il bordo se ne va del tutto: vedi §10.5. Un pannello si distingue per il
   GRADINO DI LUMINANZA contro il pavimento, non per una cornice. */
.jarvis-panel {
  background: var(--bg-raised);
  box-shadow: var(--ombra-contatto);
  border-radius: var(--radius);
}
```






## 10.2 Anatomia di un pannello

Cinque elementi. Se ne manca uno, sembra un mockup.

```
┌─ ① ETICHETTA IN CAPS ─────── ② ID/VER ──── ③ ⊟ ⊡ ⊠ ┐
│   ④ contenuto REALE                                   │
│ ⑤ 1920×1080 · 04:12:33 · 0x7f2a         ◺ taglio 45° │
└───────────────────────────────────────────────────────┘
```

**Regola dell'asimmetria**: taglio a 45° su **uno o due vertici, mai zero e mai quattro**.

## 10.3 Movimento

| Elemento | Comportamento |
|---|---|
| Anelli concentrici | **46s / 74s / 120s / 240s** per giro. Mai multiple tra loro |
| Boot sequence | contorni disegnati una linea alla volta |
| Apertura pannello | `clip-path` che si espande, 180 ms, `easeOutQuart` |
| Valori numerici | interpolazione del valore, mai del DOM |
| Fondo | **immobile** |

**Nessuna animazione senza causa.** L'animazione decorativa continua è il marchio del finto.

## 10.4 anime.js — API e budget di frame

anime.js **v4**, ESM: `import { animate, createTimeline, stagger, svg, utils } from 'animejs'`.

| Elemento | API |
|---|---|
| Boot sequence | `svg.createDrawable()` + `createTimeline()` |
| Apertura/chiusura WinBox | `animate()` su `clipPath`/`opacity`, hook `onminimize`/`onmaximize`/`onclose` |
| Anelli | `animate(el,{rotate:360,duration:46000,loop:true,ease:'linear'})` |
| Contatori | `animate(obj,{value:n,modifier:utils.round(1)})` |
| Dock | `stagger(60)` |

**Dove NON usarlo**: mai nel render loop di three.js; mai per i glifi PixiJS (usano il ticker GPU); mai due engine.

**Budget di frame (~16 ms)**: three.js ≤ 8 ms · PixiJS ≤ 3 ms · anime.js + layout ≤ 4 ms · margine 1 ms.

---

## 10.5 Il linguaggio delle finestre — misurato, non dedotto

> **Aggiunto nella rev 5.16**, dopo aver misurato pixel per pixel sette
> pannelli di `famiglia-a/01`. Fino a qui ogni pannello aveva una cornice da
> un pixel sui quattro lati: **nel riferimento non ce l'ha nessuno.**

### Il conteggio che ha deciso

| pannelli misurati | cornice sui 4 lati |
|---|---|
| BUSINESS, globo, banner video | **nessun tratto di bordo** |
| mappa, player video | un lato solo |
| calendario | asimmetrica: 7 px a sinistra, 3 a destra, 0 sopra e sotto |
| **totale con cornice su quattro lati** | **zero su sette** |

### Le cinque regole

**1. Un pannello e' un GRADINO DI LUMINANZA, non una cornice.** Il corpo sta a
**L 37** contro il pavimento a L 19: +18. Misurato `#1e2631` sul calendario,
identico a quattro quote — cioe' esattamente `--bg-raised`, opaco e piatto.
Nessuna trasparenza, nessun `backdrop-filter`.

**2. La testata e' una SUPERFICIE.** Una banda piena, il **6-9 %** dell'altezza
del pannello, con un gradino di almeno **+19 L** sul corpo. Misurata a L 65,7
sul calendario: la luminanza di `--fill-1`. Una riga di testo su fondo uguale
al corpo non e' una testata — e' testo.

⚠️ Il riferimento ha **tre polarita'** e non ne sceglie una: BUSINESS +68 L col
testo scuro su chiaro, calendario +30 L col testo chiaro, mappa **−19 L**, cioe'
piu' scura del proprio corpo. Si adotta la seconda: e' quella che regge la
tipografia che abbiamo, e le altre due andrebbero riscritte pannello per
pannello. **E' una scelta, non una misura.**

**3. Gli angoli si chiudono con MARCATORI, non con una cornice.** Triangoli
pieni di 3-5 px su **due vertici opposti**, chiari sul fondo del pannello
(rapporto di luminanza fino a ×2,8 misurato sul calendario). Non sostituiscono
il taglio a 45° di §10.2: quello e' la sagoma, questi sono il segno.

**4. L'ombra e' PICCOLA.** L'unica misurabile del concept: scostamento ~2 px,
raggio ~3 px, nero ad alpha ~0,18. Vale l'invariante 19 come riformulata nella
rev 5.13 — l'ombra separa due superfici sovrapposte, l'alone aggiunge luce che
non c'e'.

**5. Nessun alone, nemmeno DENTRO.** I due `inset` caldi che `.jarvis-panel`
portava dalla Fase 0 erano alone a tutti gli effetti, e sono stati tolti.

### Cosa NON si prende dal riferimento

Il concept **non contiene un solo stato vuoto**: nessun pannello dice «nessun
dato», nessuno mostra un elenco a zero elementi, nessuno un errore. E'
l'unica cosa che non puo' insegnare, ed e' la prima che l'invariante 23 impone
di disegnare. Lo stato vuoto lo progettiamo noi, ogni volta.

---

## 10.6 Le tre classi di moto

> **Aggiunta nella rev 5.21** come cancello di governance separato, senza codice,
> nella forma di `e4851ae`. Il documento con la misura e il costo è
> `docs/acceptance/CANCELLO-10.6.md`.

L'invariante 25 ha **due parole** — «con causa» e «ambientale» — e ne servono
**tre**. Un equalizzatore alimentato dal microfono vero non ha un inizio e una
fine: ha una **sorgente**. Una pagina web viva dentro una `<webview>` nemmeno.
Sono due cose che §11.5 e §6.3 **prescrivono**, e che oggi il loro stesso banco
boccerebbe — non perché siano decorazione, ma perché non c'è una parola per
dirle.

| | Definizione | Dove è ammessa |
|---|---|---|
| **1 · transitorio con causa** | comincia a un evento dichiarato, **finisce da solo**, e dopo la fine il componente chiede zero fotogrammi | ovunque |
| **2 · continuo governato da una sorgente viva** | continua **finché e solo finché** una sorgente esterna produce campioni | **solo nel contenuto di un pannello** |
| **3 · ambientale** | sopravvive alla rimozione di ogni sorgente dichiarata | **mai** |

⚠️ **Il fondo non si tocca.** §10.3 «Fondo: immobile» resta assoluta. Barra,
dock, catalogo, cornice e strato di presenza oltre ciò che §25.6 già assegna
restano fermi. È l'unica riga del progetto che non è mai stata violata, e questa
sezione non la sfiora.

### Le tre condizioni della classe 2

Tutte e tre sono **già misurabili** con strumenti che esistono. Un moto continuo
che non le soddisfa tutte è di classe 3, cioè vietato.

**(a) Falsificabilità contro la sorgente.** Tolta la sorgente, il moto si ferma
entro un secondo. È il test che `app/main.js` esegue già sul nucleo: **due
finestre da un secondo, si tiene la minore**. Il perché di due e non una sta
scritto lì: un'animazione ambientale gira in entrambe, un evento cade in una
sola.

**(b) Leggibilità da fermo.** Uno **scatto singolo** deve permettere di leggere
il valore come **numero in `--font-mono`**. Se l'informazione esiste solo nel
movimento, è decorazione travestita da dato. Il riferimento lo fa già: sotto
`VOICE EQUALIZER` in `famiglia-a/10` ci sono `12:48.14`, `60 Hz`, `220 VOLTS`.

**(c) Attribuzione.** I pixel che cambiano fra i due scatti a 250 ms cadono
**dentro il rettangolo del componente che ha dichiarato la sorgente, e da
nessun'altra parte**:

```
ambiente = diversi − Σ per[zone con sorgente viva dichiarata]      soglia: 0
```

`scripts/densita.mjs` attribuisce già per zona e `scripts/occlusione-dom.js`
emette già i rettangoli. Oggi quella riga tratta il nucleo come caso
particolare; domani direbbe il vero in tutti i casi invece che in uno.

### Il tetto

**Al massimo due sorgenti di classe 2 visibili insieme, e la somma dei loro
rettangoli ≤ 15 % del fotogramma.** Una sorgente va bene, dodici sono uno
screensaver.

⚠️ **Il 15 % non viene da nessun riferimento: è una scelta, non una misura** —
nella stessa forma della polarità della testata in §10.5 regola 2. Chi la
cambia cambi anche questa riga.

---

# 11. Replicare la UI dei riferimenti

## 11.1 Analisi dei riferimenti

Ho analizzato diciotto immagini. Si dividono in **due famiglie**, e la distinzione è la cosa più importante di questa sezione.

### Famiglia A — information design cinematografico (la maggioranza)

Desktop Iron Man 2/3, schede archivio, board investigativa, globo GPS, tavola periodica.

| Caratteristica | Osservazione |
|---|---|
| Fondo | blu-nero quasi puro, mai grigio |
| Luminosità | dal **contrasto** contro il nero, **mai da bloom o glow** |
| Densità | estrema. Lo spazio vuoto è raro e sempre intenzionale |
| Tipografia | condensata per i titoli, **monospace per ogni numero** |
| Bordi | hairline, mai spessi |
| Accento caldo | rosso-arancio, **~10% della superficie**, sempre semantico (allarme, valore critico) |
| Contenuto | dati veri, pagine web vere, video veri incassati |
| Etichette | `ver 12`, `A02`, `QUERY COMPLETE`, coordinate, hex |

Osservazione decisiva: nel desktop Iron Man 2 sono incassate **pagine web reali** — la barra URL di YouTube è visibile in uno dei riquadri. Il Suo approccio con `<webview>` (§6.3) è esattamente quello, non un'approssimazione.

Due motivi ricorrenti che vale la pena isolare:
- **Piani stratificati in prospettiva** (schede archivio): documenti e immagini su piani Z traslucidi, con filmstrip di miniature sotto.
- **Board investigativa in spazio 3D libero**: carte a profondità e angoli diversi, non in griglia, con chip-etichetta rossi.

### Famiglia B — asset motion-graphics da stock

Il "digital counter tool" con i contatori circolari.

**Questa famiglia contraddice la Famiglia A e il Suo stesso pilastro.** Ha bloom, alone, saturazione. È decorazione, non informazione: quei quadranti non mostrano nulla di vero.

**Deve scegliere.** Il mio consiglio è netto: **Famiglia A**. È più difficile da imitare male, invecchia meglio, e soprattutto è coerente con un sistema che mostra dati reali. Se prende gli anelli della Famiglia B, li prenda come *forma* — tick, archi segmentati, quadranti — e li renda senza glow, con dati veri dentro.

## 11.2 Si può replicare? Sì — ma il codice è il 30%

**Verdetto tecnico: sì, integralmente.** Non c'è nulla in quelle immagini che il web moderno non renda. Nessuna richiede tecnologie esotiche.

**Ma il vero contenuto di quelle interfacce non è tecnologico.** Il 70% è:
- disciplina tipografica (due font, sei corpi dal 22 agosto 2026, mai deroghe)
- densità informativa (schermi pieni di dati veri)
- un solo accento cromatico usato con parsimonia semantica
- zero decorazione senza funzione

Le librerie della §11.3 Le danno il 30%. Il resto lo dà la §11.6 e il metodo della §11.7. Chi installa augmented-ui e si ferma lì ottiene un template cyberpunk, non un JARVIS.

## 11.3 Stack librerie — verificato

Tutti i repository sono stati verificati ad agosto 2026.

### Chrome dei pannelli

**augmented-ui** — CSS puro, licenza BSD-2, ~93% di compatibilità browser. Risolve il problema esatto degli angoli tagliati e delle cornici irregolari senza elementi extra, immagini o clip-path calcolati a mano. Il progetto lo descrive così: la Sci-Fi tradizionale sul web richiede elementi extra per ogni taglio, ruotati e posizionati per coprire gli angoli; augmented-ui elimina tutto questo con poche custom property.

- Repo: `https://github.com/propjockey/augmented-ui`
- Docs + editor visuale: `https://augmented-ui.com/docs/`
- CDN: `https://unpkg.com/augmented-ui@2/augmented-ui.min.css`

```html
<div class="jarvis-panel" data-augmented-ui="tl-clip br-clip border">
```

⚠️ **Attenzione**: `clip-path` crea un nuovo stacking context e appiattisce le trasformazioni 3D. Se un pannello augmented deve stare su un piano 3D (§11.5), l'elemento augmented va **annidato dentro** quello trasformato, non fuso con esso.

**Alternativa più leggera**: `https://github.com/MYRWYR/CSS-sci-fi-ui`. Meno potente, ma se Le basta il taglio a 45° i token della §10.1 con `clip-path` a mano bastano.

### Grafici e dati densi

**uPlot** — MIT. È la scelta corretta per le strisce di telemetria: aggiornando 3.600 punti a 60fps usa **il 10% di CPU e 12,3 MB di RAM**; le librerie canvas successive più veloci (Chart.js ed ECharts) usano rispettivamente 40%/77 MB e 70%/85 MB. Regge lo streaming a 60fps fino a circa 100k punti in vista.

- Repo: `https://github.com/leeoniya/uPlot`
- Demo streaming: `https://leeoniya.github.io/uPlot/demos/sine-stream.html`

Nota di progetto perfettamente allineata alla Sua §10.3: uPlot **non ha transizioni né animazioni**, per scelta dichiarata dell'autore — le considera distrazioni. Esattamente la Sua regola.

**D3** (ISC) per tutto ciò che uPlot non fa: quadranti radiali, archi segmentati, tavole periodiche, grafi a nodi. Usi i moduli separati, non il bundle: `d3-shape`, `d3-scale`, `d3-geo`, `d3-array`.

### 3D

**three.js** più questi addon:

| Necessità | Soluzione | Perché |
|---|---|---|
| Linee di spessore controllato | **`Line2` / `LineSegments2` / `LineMaterial`** da `three/addons/lines/` | ⚠️ **critico**: `LineBasicMaterial.linewidth` è ignorato su quasi tutte le piattaforme. Senza questi addon il Suo wireframe sarà sempre a 1px, e il pilastro "0.5px con densità variabile" resta lettera morta |
| " versione modulare | **three-fatline** `https://github.com/vasturiano/three-fatline` | modularizzazione degli stessi file |
| " alternativa a mesh | **meshline** `https://github.com/utsuboco/THREE.MeshLine` | strip di triangoli billboard invece di GL_LINE; supporta larghezza variabile lungo la linea |
| Globo tattico con archi | **three-globe** `https://github.com/vasturiano/three-globe` | fa esattamente il globo del riferimento: layer di archi che si alzano dalla superficie collegando coordinate, con altitudine, dash e risoluzione di curva configurabili |
| Proiezione ortografica | **d3-geo** `geoOrthographic()` | **sostituisce la matematica a mano della §17.4**: è già implementata, testata e con il clipping dell'emisfero |
| Etichette testuali nel 3D | **troika-three-text** `https://github.com/protectwise/troika` | testo SDF nitido a qualunque zoom. `TextGeometry` nativo è pesante e brutto |
| Picking gesti e hover | **three-mesh-bvh** | raycast accelerato di ordini di grandezza |

Documentazione ufficiale delle linee spesse: `https://threejs.org/docs/pages/Line2.html`, `https://threejs.org/docs/pages/LineMaterial.html`, esempio `https://threejs.org/examples/#webgl_lines_fat`.

### Massa dati e testo

**PixiJS v8** per i glifi esadecimali scorrevoli e i log di calcolo: migliaia di elementi sulla GPU invece che nel DOM.

**Effetto "decodifica" del testo**: ~30 righe custom, oppure `baffle.js`. Non serve una dipendenza per questo.

### Font — la scelta che conta più delle librerie

| Ruolo | Font | Fonte |
|---|---|---|
| Interfaccia, titoli | **Barlow Semi Condensed** (400/500/600) | Google Fonts |
| Ogni dato e coordinata | **IBM Plex Mono** (400/500) | Google Fonts / IBM |

Se vuole avvicinarsi all'Eurostile Extended dei film, alternative gratuite: **Michroma**, **Chakra Petch**, **Saira Condensed**, **Share Tech Mono**.

⚠️ **Eviti Orbitron.** È il font che grida "sci-fi da template" più di qualunque altro. È la firma visiva del progetto amatoriale.

## 11.4 La regola architetturale: WebGL o DOM?

Questa è la decisione tecnica che distingue un'implementazione da senior da una da principiante, e i riferimenti la impongono.

| Motivo nei riferimenti | Tecnologia | Perché |
|---|---|---|
| Wireframe, globo, nuvole di punti, anelli reattore | **three.js (WebGL)** | geometria pura |
| Glifi di massa, log scorrevoli | **PixiJS (WebGL)** | migliaia di sprite |
| Pannelli, tabelle, tavola periodica, liste | **DOM + CSS** | è testo: deve essere selezionabile e nitido |
| **Piani stratificati con documenti** | **DOM + CSS 3D** (`transform-style: preserve-3d`, `perspective`) | ◄ contengono testo e immagini |
| **Board investigativa in spazio 3D** | **DOM + CSS 3D** | ◄ carte con foto, video, testo |
| Web e YouTube incassati | **`<webview>` Electron** | contenuto vero |

**L'errore da non fare**: mettere in three.js le carte della board investigativa e i documenti dei piani stratificati. Sembra la scelta "più 3D", ed è sbagliata. Rasterizzare testo in WebGL lo rende sfocato, non selezionabile, costoso da aggiornare, e rende impossibile incassare una `<webview>`.

CSS 3D fa la stessa cosa con testo reale, `<video>` reali e `<webview>` reali dentro i piani:

```css
.stage-3d { perspective: 2400px; transform-style: preserve-3d; }
.plane {
  position: absolute;
  transform-style: preserve-3d;
  transform: translate3d(var(--x), var(--y), var(--z))
             rotateY(var(--ry)) rotateX(var(--rx));
  will-change: transform;
}
```

Il compositore di Chromium le gestisce sulla GPU. Costo: quasi zero.

## 11.5 Dai riferimenti ai componenti

Mappa concreta di cosa costruire e con cosa.

| Componente | Fonte visiva | Tecnologia | Fase |
|---|---|---|---|
| Griglia pannelli con angoli tagliati | tutti | augmented-ui + token | 1b |
| Strisce telemetria live | desktop MCU | uPlot | 1b |
| Tavola periodica | riferimento chimico | **CSS Grid** — il pezzo più impressionante è il più banale | 5 |
| Quadranti radiali con tick | HUD, contatori | D3 `d3-shape` arc + SVG | 5 |
| Anelli reattore concentrici | logo, HUD | SVG + anime.js (46/74/120/240 s) | 5 |
| Globo con archi | GPS locator | three-globe + d3-geo | 5 |
| Nuvola di punti sferica | server trace | three.js `Points` + inversione `acos(2u−1)` (§17.4) | 5 |
| Grafo a nodi | mesh agenti | D3 `d3-force` o layout fisso + SVG | 5 |
| Piani stratificati documenti | archivio | **CSS 3D** + filmstrip | 6 |
| Board investigativa | board Iron Man 3 | **CSS 3D** + chip-etichetta | 6 |
| Web e video incassati | desktop MCU | `<webview>` | 6 |
| Log esadecimali scorrevoli | tutti | PixiJS | 5 |
| Equalizzatore vocale | GPS locator | uPlot o canvas custom su dati veri del microfono | 3 |

Nota sulla tavola periodica: sembra la cosa più complessa del riferimento, ed è **una CSS Grid con 118 celle**. È istruttivo — nelle UI cinematografiche l'effetto viene dalla densità e dalla coerenza, non dalla complessità tecnica di ogni pezzo.

## 11.6 Le sei regole che fanno la differenza

Le librerie non bastano. Queste sì.

1. **Due font, sei corpi, nessuna deroga.** Il sesto — `--t-display`, 48 px — è del 22 agosto 2026: è il 3,1 % della larghezza misurato sulla lettura numerica di `famiglia-a/03`, e nessuno dei cinque ci arrivava. **È RISERVATO: una sola dichiarazione in tutto il sistema**, imposta da un test che conta i consumatori — decisione del 23 agosto 2026, `docs/acceptance/DEROGHE-7dad2b8.md`. Ogni numero in monospace. È il 40% dell'effetto.
2. **Un solo accento caldo, sempre semantico.** Il rosso significa allarme o valore critico. Non decora mai. Massimo 10% della superficie colorata.
3. **Densità.** Uno schermo mezzo vuoto non sembrerà mai JARVIS. Se un pannello ha poco da dire, lo rimpicciolisca — non lo riempia di spazio.
4. **Dati veri.** Vedi §11.9. È la causa singola più frequente di UI generata che "sembra finta".
5. **Zero glow.** La luminosità viene dal contrasto contro il nero. Il momento in cui aggiunge `filter: drop-shadow` o un bloom in post-processing, scivola nella Famiglia B.
6. **Asimmetria progettata.** Uno o due angoli tagliati per pannello, mai zero e mai quattro. Velocità di rotazione non multiple. Il varco nell'anello è un parametro con un nome, non `Math.random()`.

## 11.7 Come far lavorare Claude Code sul design

Questo è il metodo, ed è la risposta operativa alla Sua richiesta di non ottenere risultati brutti o banali.

**Il problema di fondo**: Claude Code scrive componenti visivi **alla cieca**. Non vede il risultato. Senza un ciclo di feedback produce codice plausibile e brutto, e non ha modo di accorgersene.

**La soluzione: una galleria di componenti più un ciclo di verifica visiva.**

### Passo 0 — l'ambiente della prova non può essere più permissivo di quello vero

> **Aggiunto il 19 agosto 2026 (rev 5.11), dopo che è successo due volte.**

Un criterio che si ferma al confine di un sottosistema prova **metà del giro**.
La prova deve percorrere la strada che percorrerà l'utente, dall'inizio alla
fine, nell'ambiente in cui girerà davvero.

Le due volte:

| | Cosa sembrava | Cosa era |
|---|---|---|
| **CSP di PixiJS** | i glifi giravano in galleria | `gallery.html` non aveva CSP; l'app sì, e bloccava `unsafe-eval`. I glifi non partivano **da quattro fasi** |
| **R82** | sei test verdi sulla persistenza | `resize → affianca()` cancellava il ripristino un secondo dopo l'avvio. Nessun test arrivava fino alla finestra vera |

In tutte e due, l'ambiente di prova era **più permissivo** di quello reale, e
ha approvato codice che nel reale era rotto.

**Le tre regole che ne seguono:**

1. **La galleria prova un componente, non il sistema.** Va benissimo per
   l'audit dei token e per la §11.8, e non basta per niente che attraversi più
   di un sottosistema. La galleria ha lo stesso CSP dell'app — un test lo
   impone — proprio perché la differenza era invisibile.
2. **Ciò che attraversa un confine si prova attraversando quel confine.** Il
   layout tocca renderer, preload, ponte, socket, core e disco: la sua prova
   avvia `app/main.js` con Electron vero e core vero
   (`scripts/prova-gesti.mjs`), e riavvia davvero invece di simulare.
3. **Un gesto si prova come gesto.** `zonaAggancio()` era verificata come
   funzione su cinque punti e non aveva mai visto un trascinamento. Playwright
   genera eventi puntatore che entrano nella pipeline di input del browser;
   `dispatchEvent(new PointerEvent(...))` no, e non prova né
   `setPointerCapture` né ciò che succede fra due clic.
4. **Un criterio su un fenomeno dichiara prima che il fenomeno è avvenuto.**
   Un nastro che non si è mai mosso si è anche fermato; una superficie che non
   esiste non è mai fuori scala; zero elementi su zero sono tutti coperti. In
   tutti e tre i casi il criterio passa **per assenza del fenomeno**, e da quel
   momento non può più bocciare niente.

   Gli esiti sono quindi **tre e non due**: `soddisfatto`, `non soddisfatto`,
   **`non misurabile`**. Il terzo non è una via di mezzo ed è il più
   importante: dice che la prova non ha visto ciò di cui doveva parlare, e
   **non conta come verde**.

   In pratica ogni criterio su un fenomeno porta accanto la propria condizione
   di misurabilità, e la condizione si asserisce **per prima**:

   ```
   l'inerzia e' MISURABILE          x != 0 dopo il rilascio
   l'inerzia CONTINUA               subito != dopoUnPo
   l'inerzia DECELERA e si ferma    fermo == ancoraFermo
   ```

   Vale in particolare per **soglie di copertura, conteggi su insiemi vuoti e
   misure di tempo sotto un tetto**: sono i tre posti in cui l'assenza somiglia
   di più al successo. Cinque occorrenze finora: `si_e_fermata` vera a nastro
   fermo, la soglia «nucleo ≥ 5 %» che era il massimo teorico, «0/0 elementi
   caldi», il banco di §11.4 che dava un verdetto dove il fotogramma non è
   misurabile, il CSP di PixiJS che la galleria non aveva.
5. **La provenienza di una misura fa parte della misura.** Un numero senza la
   sua sorgente non è un numero: non si sa con che cosa si può confrontare.

   Ogni valore dichiarato porta accanto **da dove viene** — quale scatto, quale
   sessione, e se la sorgente era viva o registrata. Due numeri di provenienza
   diversa **non si sottraggono**, e un delta fra loro non esiste.

   È la riga che avrebbe impedito quattro misure contaminate in due giorni: le
   miniature del modulo Media, il ritaglio del marchio contro `b2f7360`, lo
   scatto con la CPU all'1,7 % invece del 3,6 %, e la barra rimasta `DEGRADED`.
   In tutti e quattro i casi il numero era giusto e il **confronto** era nullo.

**E una prova deve controllare il proprio stato di partenza.** La prima
stesura di `prova-gesti.mjs` partiva da ciò che aveva lasciato l'esecuzione
precedente, e due esecuzioni identiche davano risultati diversi. Una prova che
dipende dai residui della prova prima non è una prova.

### Passo 1 — la galleria

Prima di qualunque componente, costruisca `ui/gallery.html`: una pagina che rende **ogni componente isolato**, con il quality gate attivo, dati finti-ma-strutturalmente-veri, e una griglia di riferimento sovrapponibile.

```
ui/gallery.html
  ?component=reactor-ring     → un solo componente, isolato
  ?component=all              → tutti, in griglia
  &grid=1                     → griglia 110px sovrapposta
  &tokens=audit               → evidenzia ogni valore NON proveniente da tokens.css
```

`&tokens=audit` è il pezzo che vale la pena scrivere: uno script che scorre il CSS calcolato e colora di magenta ogni elemento con un colore, una spaziatura o un corpo che non corrisponde a un token. Un componente conforme è invisibile all'audit; uno abusivo si illumina.

### Passo 2 — il ciclo di verifica

Con Playwright (o Puppeteer) Claude Code chiude il cerchio da solo:

```bash
# in package.json
"shot": "playwright screenshot --viewport-size=1920,1080 \
         'http://localhost:5173/gallery.html?component=$1' shots/$1.png"
```

Il ciclo che deve girare per **ogni** componente:

```
1. FORGE scrive il componente
2. lo rende nella galleria
3. screenshot con Playwright
4. FORGE GUARDA lo screenshot
5. lo confronta con la checklist §11.8 e con l'immagine di riferimento
6. se un solo punto fallisce → RISCRIVE, non rattoppa
7. ripete fino a conformità
```

Il passo 4 è quello che cambia tutto. Claude Code **può vedere le immagini**. Uno screenshot del proprio output più l'immagine di riferimento nello stesso contesto trasformano la generazione da cieca a iterativa.

### Passo 3 — prompt con riferimento ancorato

Non chieda mai "fai un pannello telemetria bello". Chieda:

> Costruisci il componente `telemetry-strip` in `ui/src/panels/telemetry.js`.
> Riferimento visivo: `docs/design-reference/desktop-mcu-02.png`, riquadro in basso a destra.
> Vincoli: solo token da `tokens.css`; uPlot per la serie; dati veri dal topic `telemetry` del WebSocket; anatomia a cinque parti §10.2; taglio a 45° sul solo vertice in basso a destra.
> Poi: rendilo in `gallery.html?component=telemetry-strip&tokens=audit`, fai lo screenshot, guardalo, verifica la checklist §11.8 punto per punto e riporta l'esito di ciascuno. Se un punto fallisce, riscrivi.

### Passo 4 — cosa mettere nel repo

```
docs/design-reference/
├── README.md              # la §11 di questo documento
├── famiglia-a/            # i riferimenti da seguire
└── famiglia-b/            # marcati "NON SEGUIRE — contiene glow"
```

Le immagini di riferimento nel repo, con il README che spiega quale famiglia seguire, sono ciò che rende ripetibile il risultato tra una sessione e l'altra.

## 11.8 Checklist di rifiuto

Un solo ✗ significa **riscrivere**, non aggiustare.

```
GEOMETRIA
□ border-radius è 0 ovunque?
□ taglio a 45° su 1–2 vertici (mai 0, mai 4)?
□ ogni spaziatura è multiplo di 4?
□ pesi di linea solo hair/base/bold?

COLORE
□ tutti i colori da tokens.css? (audit magenta pulito)
□ accento caldo < 10% della superficie colorata?
□ tinte totali ≤ 3?
□ zero gradienti fuori dalla ricetta del vetro?
□ ZERO alone luminoso, ZERO bloom, ZERO glow?
□ ogni ombra portata è NERA e sta su qualcosa che copre? (inv. 19, rev 5.13)

TIPOGRAFIA
□ solo i sei gradini?
□ tutti i numeri in --font-mono?
□ etichette caps con letter-spacing ≥ .10em?
□ niente sotto 8.5px, corpo mai sotto 14px?

CONTENUTO
□ i dati sono VERI?
□ etichetta + ID/versione + piede tecnico presenti?
□ almeno un valore numerico monospace?
□ la densità regge il confronto con l'immagine di riferimento?

MOVIMENTO
□ ogni animazione risponde a un evento reale?
□ zero animazione ambientale nel fondo?
□ solo anime.js?

TECNOLOGIA
□ il testo è nel DOM, non rasterizzato in WebGL?
□ le linee 3D usano Line2/LineMaterial, non LineBasicMaterial?
□ i numeri vivono in uPlot o SVG, non in canvas custom improvvisato?
```

## 11.9 Divieto di dati finti

| Vietato | Obbligatorio |
|---|---|
| `Lorem ipsum` | testo reale dal contesto |
| `Item 1`, `Elemento 2` | nomi veri da filesystem o API |
| `100`, `50%`, `1000` | valori da psutil, API, filesystem |
| Timestamp inventati | `time.time()` |
| Grafici con dati casuali | serie reali dal ring buffer |

**Se un pannello non ha ancora la sua fonte**, mostri lo stato vuoto — `NESSUNA SORGENTE COLLEGATA` in `--txt-ghost`. Uno stato vuoto onesto sembra un sistema in costruzione; dati finti sembrano un giocattolo.

*(Prima eccezione: la galleria di §11.7, dove i dati sono finti per costruzione ma devono avere la **forma** di dati veri — lunghezze di stringa realistiche, numeri non tondi, timestamp plausibili.)*

### La seconda eccezione — il modo di MISURA

> **Aggiunta nella rev 5.22** come cancello di governance separato, senza
> codice, nella forma di `e4851ae`. Il documento con la misura e il costo è
> `docs/acceptance/CANCELLO-11.9.md`.

**Non è un dataset: è un modo.** Una misura di densità confronta due fotogrammi,
e finché la telemetria legge la CPU vera due fotogrammi non sono confrontabili:
misurato, due sessioni di `npm run scrivania` danno `L>60` **26,1 %** e
**25,3 %**, e la differenza non è attribuibile a niente. Quattro misure sono già
state contaminate così.

Il modo di misura può quindi alimentare la scrivania da una **registrazione**,
e vale **solo** con tutte queste condizioni:

1. **I dati sono REGISTRATI da una sessione vera, mai generati.** Nessun valore
   è inventato, nessuno è ritoccato: l'invariante 23 non si sfiora. Non è la
   concessione della galleria — è una cosa diversa, ed è per questo che ha una
   riga sua.
2. **La registrazione è versionata e porta un'impronta**, e un test verifica che
   il file non sia stato toccato a mano.
3. **Il modo è impossibile da raggiungere per sbaglio**: un comando proprio, una
   cartella d'uscita propria, e la provenienza scritta dentro l'esito.
4. **Una misura di fixture non si confronta MAI con una misura viva.** Sono due
   popolazioni, e mescolarle è il difetto che questa sezione esiste per
   impedire.
5. **La sorgente resta fuori dall'applicazione.** Il renderer riceve da un
   socket che non controlla, come sempre: l'invariante 1 non si tocca, e
   l'invariante 7 vale identica per il riproduttore — socket UNIX in
   `$XDG_RUNTIME_DIR`, directory 0700, mai una porta.

⚠️ **La fixture compra delta attribuibili dentro una baseline, non
comparabilità fra baseline diverse.** Rifare la registrazione **azzera** la
baseline, e tutto ciò che era stato misurato prima va rimisurato.

⚠️ **E una fixture fissa i DATI, non il renderer.** Un aggiornamento di driver o
di font sposta il numero senza che nel repo cambi niente.

## 11.10 Disciplina 3D — nessuna geometria non parametrica

**Nessun vertice è mai scritto a mano.** Ogni oggetto nasce da una funzione generatrice con tabella di parametri dichiarata. Come in CAD reale: non si disegna una flangia, la si parametrizza.

```javascript
// ui/src/three/component.js
export class ParametricComponent {
  constructor(params, meta) {
    this.params = Object.freeze({ ...params });
    this.meta = { unit: "mm", ...meta };
    this._validate();
  }
  _validate() {
    for (const [k, v] of Object.entries(this.params)) {
      if (typeof v === "number" && !Number.isFinite(v))
        throw new Error(`parametro non finito: ${k}`);
      if (typeof v === "number" && v < 0 && !k.startsWith("offset"))
        throw new Error(`parametro negativo non ammesso: ${k}=${v}`);
    }
  }
  /** Densità di segmenti dalla CURVATURA, non costante. */
  segmentsFor(radius, arcAngle = Math.PI * 2, targetChordMm = 1.2) {
    return Math.max(8, Math.min(256, Math.ceil((radius*arcAngle)/targetChordMm)));
  }
  build() { throw new Error("build() va implementato"); }
  constructionLines() { return null; }
}
```

```javascript
export class ReactorRing extends ParametricComponent {
  constructor(p = {}) {
    super({
      outerR: p.outerR ?? 120, thickness: p.thickness ?? 8,
      tickCount: p.tickCount ?? 48,
      gapStart: p.gapStart ?? 0.62,      // rad — l'asimmetria è PROGETTATA
      gapSweep: p.gapSweep ?? 0.31,
      periodSec: p.periodSec ?? 46,
    }, { name: "reactor-ring", version: "v1" });
  }
  build() {
    const { outerR, thickness, gapStart, gapSweep } = this.params;
    const innerR = outerR - thickness;
    const seg = this.segmentsFor(outerR);          // ◄ densità da curvatura
    const pts = [];
    for (let i = 0; i <= seg; i++) {
      const a = (i / seg) * Math.PI * 2;
      if (a > gapStart && a < gapStart + gapSweep) continue;
      pts.push(Math.cos(a)*outerR, Math.sin(a)*outerR, 0);
      pts.push(Math.cos(a)*innerR, Math.sin(a)*innerR, 0);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pts), 3));
    return g;
  }
}
```

**Le sette regole:**
1. Parametri dichiarati con unità (mm). Mai numeri magici in `build()`.
2. Densità dalla curvatura: `segmentsFor()` obbligatoria. Un cerchio a 32 segmenti fissi è la firma del generato male.
3. Linee di costruzione preservate: distinguono un pezzo ingegnerizzato da una forma.
4. Asimmetria progettata, non casuale. `Math.random()` nella geometria è vietato (tranne le nuvole di punti, dove la casualità *è* la specifica).
5. `BufferGeometry` con `Float32Array`. Mai geometrie standard.
6. Massimo due materiali: linea wireframe, faccia semitrasparente.
7. Bounding box dichiarato e verificato.

## 11.11 Quality gate — codice che gira

```javascript
// ui/src/three/quality-gate.js
const LIMITS = { minVertices:24, maxVertices:20000, maxMaterials:2, maxBBox:5000 };

export function qualityGate(component, geometry, materials) {
  const fail = [];
  const n = geometry.getAttribute("position").count;
  if (n < LIMITS.minVertices) fail.push(`vertici ${n} < ${LIMITS.minVertices}`);
  if (n > LIMITS.maxVertices) fail.push(`vertici ${n} > ${LIMITS.maxVertices}`);
  if (materials.length > LIMITS.maxMaterials)
    fail.push(`materiali ${materials.length} > ${LIMITS.maxMaterials}`);

  geometry.computeBoundingBox();
  const bb = geometry.boundingBox;
  const dim = ["x","y","z"].map(a => bb.max[a] - bb.min[a]);
  if (dim.some(d => d > LIMITS.maxBBox))
    fail.push(`bbox ${dim.map(d=>d.toFixed(0))} — probabile errore di trasformazione`);
  if (dim.some(d => d === 0)) fail.push("geometria degenere");
  if (dim.some(d => !Number.isFinite(d))) fail.push("geometria con NaN");
  if (!component.meta?.name || !component.meta?.version)
    fail.push("componente senza name/version");
  if (!component.params || Object.keys(component.params).length === 0)
    fail.push("componente senza tabella parametri — geometria non parametrica");

  if (fail.length)
    throw new Error(`QUALITY GATE FALLITO — ${component.meta?.name ?? "anonimo"}\n  `
                    + fail.join("\n  "));
  return true;
}
```

---

# 12. ARGUS — `scope = "app"`

**Deciso**: ARGUS vede solo la finestra di JARVIS.

**La scorciatoia che quasi tutti mancano**: JARVIS **conosce già** il contenuto dei propri pannelli — è lui a renderizzarli. Per la maggior parte delle domande non serve OCR, serve interrogare lo stato.

```
domanda su un pannello JARVIS   → interroga lo stato: zero OCR, zero latenza
domanda sul contenuto <webview> → capturePage() + Tesseract → testo
```

| Motore | Quando | Costo |
|---|---|---|
| Interrogazione stato | pannelli JARVIS | 0 |
| **Tesseract** | testo nella webview | CPU, ~100–300 ms |
| Florence-2 / Moondream2 | comprensione visiva (opzionale, v2) | 1,2–4 GB VRAM |

## La regola inderogabile

**Tutto ciò che ARGUS produce è DATO NON FIDATO.** Una pagina nella `<webview>` può contenere testo rivolto all'agente: è il vettore di prompt injection principale.

```python
async def read_region(region: str) -> str:
    raw = await _capture_and_ocr(region)
    return (f'<untrusted_source origin="screen:{region}">\n{raw}\n'
            f'</untrusted_source>')
```

1. L'output entra **solo** in contesti con `--allowedTools ""`.
2. Non raggiunge mai un processo T2 con tool attivi.
3. Il pannello disegna il **rettangolo della regione catturata**. Non è decorazione: è il controllo che Le permette di accorgersi di una cattura inattesa.

---

# 13. Moduli, pannelli, scorciatoie

> ⚠️ **SUPERATA NEL MODELLO A QUATTRO WORKSPACE — ADR-010, rev 5.12.**
>
> Gli otto moduli, le scorciatoie e l'anatomia dei pannelli restano validi. I
> **quattro workspace come pagine** no: quattro pagine significano che tre
> quarti del sistema è sempre invisibile, e che ogni informazione va cercata
> invece che vista. I quattro domini sopravvivono come **categorie del
> catalogo**, `Alt+1…4` filtra invece di cambiare pagina, e la cella dichiarata
> di ogni pannello diventa la sua **posizione iniziale** e non la sua gabbia.
>
> Vedi `docs/SPEC-26-AMBIENTE-UNICO.md` e `docs/acceptance/ADR-010.md`.

| Modulo | Dato reale | Fase |
|---|---|---|
| **Telemetria** | psutil: CPU, RAM, temperature, top-3 | 1 |
| **File manager** | filesystem vero sotto le radici consentite | 2 |
| **Console** | comandi reali con trace | 1b |
| **Mesh agenti** | stato del grafo T0/T1/T2 e subagent | 4 |
| **Globo tattico** | fusi orari, coordinate, elevazione solare calcolata | 5 |
| **Browser** | `<webview>`, YouTube, web | 6 |
| **Core sorgente** | file reali del progetto | 5 |
| **News** | RSS + Guardian + YouTube | 8 |

**Workspace con dominio, non numeri vuoti.** Ogni workspace ha un colore e un
significato, così che la barra porti informazione invece di contarli:

| WS | Dominio | Accento |
|---|---|---|
| 01 | Sistema e telemetria | `--cy-500` |
| 02 | File e progetti | `--cy-300` |
| 03 | Web e ricerca | `--cy-700` |
| 04 | 3D e modelli | `--amber` |

**Barra superiore**: stato agente (nominal/degraded/offline), workspace 01–04 col proprio accento, telemetria compatta, indicatore di ascolto, tray.
**Dock inferiore**: gli otto moduli, indicatore T2 attivo, azioni rapide.

| Tasto | Azione |
|---|---|
| `Alt+H` | nasconde tutti i pannelli |
| `Alt+T` | affianca |
| `Alt+1…4` | workspace interno |
| `Alt+Spazio` | ascolto senza frase-wake |
| `Esc` | interrompe il TTS |
| doppio clic barra | massimizza |
| trascinamento al bordo | aggancia a metà |

⚠️ Scorciatoie **interne all'app**, gestite dal renderer. Non registri scorciatoie globali di sistema.

---

# 14. Gesture MediaPipe

1. **CPU.** 30fps su CPU, `delegate=CPU` esplicito.
2. **Stessa allowlist dei comandi vocali.** Una gesture emette un intento sul bus, come T0.
3. **Nessuna gesture può innescare un tool con `side_effect=True`.** Un falso positivo è indistinguibile da un comando. Il vincolo è **imposto nel registry**, non lasciato alla disciplina.

| Gesto | Intento | Ammesso |
|---|---|---|
| pizzico + trascina | sposta pannello | ✅ |
| rotazione a due mani | ruota mesh 3D | ✅ |
| palmo aperto | espandi pannello | ✅ |
| spinta laterale | cambia workspace | ✅ |
| *(qualsiasi)* | crea, sposta, cestina file | ❌ |

**Isteresi**: gesto stabile per 5 frame (~166 ms). **Picking**: three-mesh-bvh.

---

# 15. News proattive

| Fonte | Costo | Note |
|---|---|---|
| **RSS/Atom** (ANSA, Il Post, BBC, Reuters) | **gratis, illimitato** | la base |
| **The Guardian Open Platform** | gratis con chiave | l'unica API news gratuita seria: **corpo completo** |
| **GNews** | free tier limitato | italiano incluso |
| **NewsAPI.org** | free **solo sviluppo**, 100/giorno | ⚠️ licenza free **vieta la produzione** |
| **YouTube Data API v3** | gratis, quota | **video** |

⚠️ **Reuters e AP non hanno feed video gratuiti.** Il notiziario video sarà YouTube embed nella `<webview>`.

```
conversazione → [estrattore argomenti] (haiku, batch = periodo dei giri, effort low)
                 ⚠️ «batch 60s» EMENDATO nella rev 5.25: 60 s = 60 spawn/ora
                 contro il tetto di 15 del Governor. Vedi core/news/motore.py
              → [watcher feed] → [gate rilevanza] → [budget]
              → [card news] + menzione vocale breve
```

**Collector pluggabili.** Non un modulo news monolitico: un file per sorgente
in `core/news/collectors/`, ognuno con la stessa interfaccia. Aggiungere una
sorgente = aggiungere un file.

```python
# core/news/collectors/base.py
class Collector(Protocol):
    name: str
    async def poll(self, topics: list[str]) -> list[Item]: ...
    def relevance(self, item: Item, topics: list[str]) -> float: ...
```

Collector iniziali: `rss.py`, `guardian.py`, `youtube.py`. Il motore proattivo
non sa nulla delle sorgenti: itera i collector registrati.

**Le regole senza cui abbandonerà la funzione in tre giorni**: 3 interruzioni/ora max · mai mentre Lei parla o con un pannello a pieno schermo · mai a metà frase · argomenti scaduti dopo 30 minuti · *"non parlarmene più"* chiude l'argomento in modo persistente.

**Il rischio**: un titolo è testo controllato da terzi. Stesse regole di §12 — contesti con zero tool, marcatura, mai verso T2 con tool attivi.

## 15.1 Conseguenza dichiarata: **le notizie richiedono la voce accesa**

Due delle cinque regole leggono lo stato vivo della voce — «mai mentre Lei
parla» e «mai a metà frase» — e `Contesto` è un tri-stato in cui `None` vuol
dire *non lo so* e **vale come divieto**. Con `voice.enabled = false` la
pipeline non si compone, quei due campi restano ignoti a ogni giro, e **nessuna
card può passare il gate**. Non è un guasto: è fail-closed, ed è la scelta
giusta — un sistema che parla da solo tace quando non sa.

È scritto qui perché non si scopra. Una proprietà che regge per costruzione e
che nessuno ha dichiarato è una proprietà che qualcuno toglierà senza sapere di
toglierla; e all'opposto, chi vedesse zero card con le news accese passerebbe
il pomeriggio a cercare un difetto nei feed. Se un giorno una card dovesse
uscire a voce spenta, quella è una **decisione nuova** e va presa, non
scoperta.

## 15.2 Perché il gate non ha lasciato passare niente: si legge, non si indovina

Un gate fail-closed rende due situazioni indistinguibili nello stesso snapshot:
*non c'era niente di rilevante* e *non poteva passare niente*. `MotoreNews`
espone perciò la **conoscibilità** del contesto — per ogni campo che `Contesto`
dichiara, `noto` oppure il motivo dell'ignoto — e i motivi sono di due specie,
perché portano a due lavori diversi:

| specie | cause | che cosa vuol dire |
|---|---|---|
| **configurazione** | `non_prodotto`, `non_composto` | manca un pezzo o un interruttore è spento: permanente finché non lo si accende |
| **guasto** | `ha_sollevato`, `risposta_storta` | il produttore c'è e ha fallito adesso: si insegue |

⚠️ **La distinzione è per chi guarda, non per il gate.** Il gate riceve gli
stessi tre tri-stati di sempre e sull'ignoto tace, qualunque ne sia la causa.
Una regola che leggesse la causa finirebbe per allentarsi.

---

# 16. Autonomia e degradazione

| Soglia | Condizione | Azione |
|---|---|---|
| Termica | package > 75 °C | diagnostica critica + top-3 |
| Memoria | RAM > 90% | proposta chiusura processi |
| Quota LLM | rate limit da `api_retry` | sospende T2, **non fa fallire T1** |
| Contesto | budget token saturo | potatura (§5.5) |
| VRAM | headroom insufficiente | **rifiuta** il caricamento (§9) |
| Deepgram | chiave invalida, 429, rete | **ricade sul locale** e lo annuncia |
| **OAuth T1** | `authentication_failed` | **niente riavvio a ciclo**: `degraded_llm`, annuncio vocale, istruzione a schermo (§5.6). **Il core ESCE col codice 41** |
| **T1 cade e ricade** | 3 riavvii in 10 minuti, causa NON auth | **niente riavvio a ciclo**: `degraded_llm`, annuncio vocale. **Il core RESTA VIVO** |

Ogni soglia emette su `agent.advisory`. **Nessuna soglia agisce senza annunciarlo.**

### Le due righe si somigliano e finiscono in modo opposto, ed è una decisione

Deciso il **28 agosto 2026**. In tutti e due i casi si smette di riprovare — nel
primo il token non torna valido riprovandolo, nel secondo T1 è già caduto tre
volte in dieci minuti. Cambia che cosa resta acceso:

**Auth scaduta → il core esce (41).** Finché il Signore non rifà il login non
c'è niente che possa tornare a funzionare da solo, e `RestartPreventExitStatus`
impedisce a systemd di rilanciarlo contro un muro.

**Riavvii ripetuti → il core resta vivo.** Uno solo dei quattro sottosistemi è
rotto: §16.1b dichiara che in `degraded_llm` restano vivi frasi-comando, T0,
file e telemetria, e spegnere quei tre perché il quarto non parte è una perdita,
non una difesa.

⚠️ **E il freno del loop non era mai stato il codice d'uscita** — né è
`Supervisore.puo_riavviare`, che ha **un solo lettore in tutto `core/`**: la
funzione `su_riavvio`, che non ha chiamanti. È un freno su una strada che
nessuno percorre.

Il freno che gira è `ClaudeT1._degradato` — il segno che sopravvive a `stop()` —
più la guardia di `ask()`, che a sessione degradata passa da
`riavvia_dopo_guasto` e solleva invece di rispondere. Sta **dentro il processo**:
funziona anche quando il core gira a mano, fuori da systemd — cioè esattamente
quando si sta cercando di capire perché cade.

⚠️ Che i due freni siano in due posti diversi, e che quello dichiarato non sia
quello che gira, è **la domanda 2 ancora aperta**: chi possiede la degradazione
non-auth di T1. Vedi `docs/acceptance/DUE-ORFANI-VERI.md`.

## 16.1b `jarvis doctor` — diagnosi di tutti i sottosistemi

Con core, T1 persistente, Deepgram, Vosk, Electron e WebSocket in gioco,
rispondere a "cosa e' rotto" senza uno strumento e' penoso. Da implementare
in **Fase 1**, non alla fine.

```
$ jarvis doctor
CORE          ok      pid 4412, uptime 3d 14h
WS            ok      unix core.sock, dir 0700, 2 client
T1 claude     ok      sessione viva 3d, ultimo turno 12s fa
T1 auth       ok      claude.ai / max
STT           ok      deepgram flux-general-multi
TTS           ok      deepgram flux
WAKE          ok      vosk it, 4 frasi, 7 trigger oggi
QUOTA         WARN    13/15 spawn T2 nella finestra
VRAM          ok      2.1/8.0 GB
```

Stesso contenuto sul topic `agent.advisory` e nel pannello telemetria, e
raggiungibile a voce con la frase T0 `"come stiamo"` (§7.6).

| Stato | Cosa funziona | Segnale |
|---|---|---|
| `nominal` | tutto | — |
| `degraded_voice` | Deepgram giù → fallback locale attivo | ambra + annuncio |
| `degraded_llm` | frasi-comando, T0, file, telemetria | ambra + *"opero in modalità ridotta"* |
| `offline` | frasi-comando, T0, file locali | rosso |

**Proprietà preziosa**: grazie al wake a frasi, anche in `offline` JARVIS risponde a *"papà è a casa"* — quel percorso non tocca né rete né LLM.

---

# 17. Modelli e progetti 3D

| Formato | Libreria |
|---|---|
| glTF/GLB, OBJ, STL, PLY | **trimesh**, **pygltflib** |
| STEP / BREP / CAD parametrico | **build123d** (Apache 2.0) o CadQuery |
| Rendering headless, thumbnail | **Blender via `bpy`** (GPL-2.0+) o **pyrender** |

## 17.4 Matematica dei quattro generatori

**① Nuvola di punti sferica uniforme.** L'errore classico è campionare θ e φ uniformemente: addensa ai poli. Corretto: inversione `acos(2u − 1)`.

```javascript
export class PointCloud extends ParametricComponent {
  constructor(p = {}) {
    super({ count: p.count ?? 4000, radius: p.radius ?? 200,
            flattenY: p.flattenY ?? 0.45 },
           { name: "point-cloud", version: "v1" });
  }
  build() {
    const { count, radius, flattenY } = this.params;
    const a = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = 2 * Math.PI * Math.random();
      const phi = Math.acos(2 * Math.random() - 1);   // ◄ uniforme
      a[i*3]   = radius * Math.sin(phi) * Math.cos(theta);
      a[i*3+1] = radius * Math.cos(phi) * flattenY;
      a[i*3+2] = radius * Math.sin(phi) * Math.sin(theta);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(a, 3));
    return g;
  }
}
```

**② Spline Catmull-Rom** — `THREE.CatmullRomCurve3` chiusa, estrusa in tubo wireframe. Passa **esattamente** per i punti di controllo. Segmenti da `segmentsFor()` sulla lunghezza della curva.

**③ Estrusioni asimmetriche** — `THREE.ExtrudeGeometry` su sagome 2D ad angoli netti tagliati a 45°, con foro centrale. Stesso motivo del taglio dei pannelli: coerenza 2D/3D.

**④ `BufferGeometry` con `Float32Array`.** Sempre.

**Il globo** — usi **`d3.geoOrthographic()`** invece di implementarla. Se preferisce a mano:

```javascript
// x = R·cos φ·sin(λ − λ₀)   y = −R·sin φ
// visibile se cos φ · cos(λ − λ₀) > 0
function orthographic(latDeg, lonDeg, lon0Deg, R) {
  const phi = latDeg * Math.PI / 180, dl = (lonDeg - lon0Deg) * Math.PI / 180;
  return { x: R*Math.cos(phi)*Math.sin(dl), y: -R*Math.sin(phi),
           visible: Math.cos(phi)*Math.cos(dl) > 0 };
}
```

L'elevazione solare deriva dalla **declinazione stagionale e dall'angolo orario** — nessun valore inventato. Anche il sole è un dato vero.

## SketchUp via MCP

Integrabile come tool di FORGE, con questi limiti da progettare:
1. **Nessun `import`** (validazione AST). 2. **Nessun accesso al filesystem.** 3. **Unità in pollici** — conversione dal mm. 4. **Sandbox AST.** 5. **`build_model` non è transazionale**: dopo un fallimento ispezioni `model_snapshot.totals`, non assuma lo stato pulito. 6. **Materiali duplicati falliscono in silenzio** (`SU_ERROR_PARTIAL_SUCCESS`): verifichi il conteggio in `model_snapshot.materials` dopo ogni `add_materials`.

**L'I/O resta nel core Python; SketchUp è solo motore geometrico.**

---

# 18. Sicurezza

## 18.1 Prompt injection

OWASP lo colloca in cima ai rischi LLM. Nei test Gray Swan/Shade il tasso di successo sale dal 4,7% (1 tentativo) al **63% (100 tentativi)**.

**Vettore principale**: la `<webview>` e l'output di ARGUS.

1. **Isolamento dei tool** — contenuto non fidato solo in contesti con zero tool. *Questa è la difesa vera.*
2. **`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.**
3. **Allowlist + conferma umana** su ogni `side_effect=True`.
4. **Solo cestino, mai delete.**
5. Marcatura `<untrusted_source>`. Il minimo, non sufficiente.

## 18.2 Trasporto core ↔ Electron — socket UNIX

**Non TCP, nemmeno su loopback.** Il canale è un **socket UNIX** in
`$XDG_RUNTIME_DIR/jarvis-os/core.sock`, dentro una directory a `0700`.

**Perché.** Su questo canale viaggia la conferma umana dei tool
`side_effect=True` (§6.2), cioè l'invariante 3. Con TCP su `127.0.0.1`
l'autorizzazione a rispondere *«sì, cancella»* apparterrebbe a **qualunque
processo dell'utente capace di aprire una socket verso quella porta**, e la
sola difesa sarebbe un token applicativo che il codice deve ricordarsi di
verificare. Con un socket UNIX la verifica la fa il **kernel**, sui permessi
del filesystem, prima che una riga di codice applicativo giri.

È lo stesso principio dell'invariante 27 sulle gesture: *imposto dalla
macchina, non lasciato alla disciplina*. Un invariante che il sistema non
impone decade alla terza sessione che tocca quel file.

**Il varco vero sono i permessi della directory, non quelli del socket.** Il
modo con cui `bind()` crea il file dipende dalla `umask`, e fra `bind()` e
`chmod()` esiste una finestra. La difesa che regge è la **directory a `0700`**:
un socket permissivo dentro una directory non attraversabile resta
irraggiungibile. Il `chmod 0600` sul socket è ridondanza, non la difesa.

**Il protocollo non cambia**, cambia solo l'ascoltatore: WebSocket su stream,
stessi topic, stessi messaggi JSON. Lato Python `websockets.unix_serve()`;
lato Electron il processo **main** con uno URL `ws+unix://`.

⚠️ **Conseguenza architetturale, da non scoprire in Fase 1b**: l'API
`WebSocket` del browser **non può** aprire un socket UNIX. Il renderer non
parlerà mai direttamente col core: la connessione la apre il processo **main**
e la espone al renderer via `contextBridge`. §3.2 lo prevedeva già («main:
bridge WS ↔ renderer»), ma smette di essere una scelta e diventa un vincolo.

**Niente token per-sessione.** Sarebbe servito col TCP. Col socket UNIX
aggiunge un meccanismo da mantenere e nessuna garanzia in più.

**Non esiste una porta da esporre per sbaglio.** È la proprietà migliore di
questa scelta, ed è il motivo per cui supera l'invariante 7 invece di
violarlo: `0.0.0.0` non è più un errore possibile, è un'opzione che non c'è.

**Windows** (§23): l'equivalente è una **named pipe** (`\\.\pipe\jarvis-os`)
con una ACL che concede il solo utente corrente. Per questo `socket_path()`
sta dietro `platform.Paths` e non è una costante nel codice.

## 18.3 Privacy

**Il microfono è attivo solo dentro l'ambiente di JARVIS** (rev 5.31). Fino a
quella revisione questa riga diceva «sempre attivo per il wake», e lo era: il
core gira sotto systemd ventiquattro ore, quindi JARVIS sentiva la frase di
richiamo e rispondeva **anche a finestra chiusa** — che non è ciò che «un
ambiente cognitivo dentro il quale JARVIS vive» vuol dire. La riga è stata
emendata su richiesta esplicita dell'utente, e il perimetro che ne risulta è
più STRETTO di prima, mai più largo.

Il segnale è la **connessione della scrivania al socket**, non la visibilità
della finestra: una scrivania ridotta a icona resta collegata e JARVIS resta in
ascolto — è ciò che serve a un assistente a cui si parla senza guardarlo.

⚠️ **Conta solo chi si dichiara scrivania**, con un messaggio il cui `ruolo` è
un `Literal` e non una stringa: `ws_probe.py` si collega per diagnosi e non
accende niente. Se bastasse una connessione qualunque, qualunque cosa sapesse
aprire il socket potrebbe far ascoltare JARVIS — una denylist travestita.

⚠️ **E il flusso si CHIUDE davvero**, non si scartano i blocchi: `pw-record`
termina, e la spia del microfono del sistema operativo si spegne. Quella spia è
l'unica cosa che il Signore vede senza chiedere, e un microfono che non ascolta
ma tiene la spia accesa dice una bugia a chi la guarda.

**VAD e Vosk girano localmente**: l'audio senza frase nota **non lascia mai la macchina** e non viene salvato. Questo vale **anche con Deepgram primario** — solo dopo il match l'audio va in rete. Indicatore di ascolto sempre visibile, kill-switch a un clic, log dei trigger ispezionabile.

---

# 19. Legale — uso personale

**Marchi.** Il diritto dei marchi disciplina l'**uso nel commercio**: impedire confusione tra prodotti offerti al pubblico. Un progetto privato, non distribuito, non pubblicizzato **non è uso nel commercio**. Rischio pratico prossimo a zero.

**Voce.** Il right of publicity riguarda anch'esso lo sfruttamento commerciale. Per uso privato il quadro è molto più permissivo.

**L'unica condizione che conta:**

> Il momento in cui pubblica il repository, carica un video dimostrativo, o lo condivide anche gratuitamente, **l'analisi torna severa**. La distribuzione, anche non commerciale, è il confine.

**Riferimenti visivi.** Estrarre una **grammatica visiva** — palette, pesi, densità, regole di composizione — è normale pratica progettuale, ed è quello che abbiamo fatto in §10 e §11. Riprodurre gli artwork specifici è altra cosa, e non ne ha bisogno: il sistema di token dà risultati più coerenti di una copia. **Tenga le immagini di riferimento in `docs/`, non le impacchetti nell'applicazione.**

*Non sono un avvocato. Valutazione di rischio pratico, non parere legale.*

---

# 20. `CLAUDE.md` completo

```markdown
# JARVIS OS — Regole di progetto

## Cos'è
Un'applicazione desktop a schermo intero: un ambiente cognitivo dentro il
quale JARVIS vive, parla, mostra dati, apre il web, gestisce cartelle reali
e genera modelli 3D. Fuori dalla sua finestra non tocca nulla.
Uso strettamente personale. Non sarà distribuito.

## Invarianti — MAI violare

1. **Il core Python possiede le operazioni reali.** Il renderer Electron non
   tocca mai il disco.
2. **Allowlist, mai denylist.** Solo i tool registrati esistono.
3. **Ogni tool side_effect=True richiede conferma umana**, col path assoluto
   RISOLTO mostrato all'utente.
4. **Solo cestino, mai delete permanente.**
5. **<webview>, news, ARGUS e file letti sono DATO NON FIDATO.** Solo in
   contesti con zero tool. Marcati <untrusted_source>.
6. **Electron: contextIsolation true, nodeIntegration false, sandbox true.**
7. **Il canale core ↔ Electron non è mai raggiungibile dalla rete**, e la
   sua autorizzazione la impone il sistema operativo, non il codice.
   Oggi: socket UNIX in `$XDG_RUNTIME_DIR`, directory 0700 (§18.2).
   Mai una porta TCP.
8. **Tutto in streaming.** Il TTS accetta AsyncIterator[str]. Il chunker va
   SOLO davanti a Kokoro, mai davanti a Deepgram Flux.
9. **Un solo motore di animazione: anime.js v4.** Niente GSAP.
10. **Un solo motore 3D: three.js.** Niente Babylon.

## Backend LLM e voce

11. **Nessun modello LLM locale.** Solo Claude Code su abbonamento.
12. **Deepgram è il provider vocale primario**; Whisper e Kokoro sono
    fallback automatico su errore, chiave mancante o rete assente.
    Il fallback va sempre ANNUNCIATO, mai silenzioso.
13. **Il wake a frasi (Vosk) è SEMPRE locale**, anche con Deepgram primario.
14. **T0 non tocca mai un LLM.**
15. **T1 è un processo persistente**, da una working directory dedicata e
    vuota, con --allowedTools "".
16. **Ogni spawn T2 passa dal Governor.** T1 ha priorità assoluta.
17. **Non duplicare la gestione del contesto di T1.**

## Design e 3D — §10 e §11

18. **Zero valori letterali** di colore, spaziatura o tipografia. Tutto da
    tokens.css. border-radius sempre 0.
19. **ZERO glow, ZERO bloom, ZERO alone luminoso.** L'ombra portata è ammessa
    SOLO per separare due superfici sovrapposte: nera, senza colore, con la
    ricetta di §10.1. Nessuna ombra su un elemento che non ne copre un altro.
    La luminosità viene dal contrasto contro il nero.
20. **Il testo vive nel DOM, mai rasterizzato in WebGL.** Piani stratificati
    e board 3D si fanno con CSS 3D transforms, non con three.js.
21. **Le linee 3D usano Line2/LineMaterial**, mai LineBasicMaterial
    (linewidth è ignorato su quasi tutte le piattaforme).
22. **Nessuna geometria 3D scritta a mano.** Ogni componente estende
    ParametricComponent, deriva la densità dalla curvatura via
    segmentsFor(), e passa qualityGate() prima del render.
23. **Mai dati segnaposto.** Dati veri o stato vuoto esplicito.
24. **Ogni componente passa dal ciclo di verifica visiva §11.7**: rendi in
    gallery.html, screenshot con Playwright, GUARDA lo screenshot,
    verifica la checklist §11.8 punto per punto. Una violazione =
    riscrivere, non rattoppare.
25. **Nessuna animazione senza causa.** Zero animazione ambientale.
    Le tre classi di moto — e l'unica eccezione, dentro un pannello e con
    una sorgente viva che si puo' spegnere — stanno in §10.6.
26. **Budget di frame: three.js ≤8ms, Pixi ≤3ms, anime.js ≤4ms.**

## Gesture

27. **Nessuna gesture può innescare un tool con side_effect=True.**
    Imposto nel registry, non lasciato alla disciplina.
28. **MediaPipe su CPU** (delegate=CPU esplicito).

## Portabilità

29. **Linux è il target attuale, Windows è previsto.** Ogni chiamata
    specifica di piattaforma (sandbox, audio, path, temperature) sta
    dietro un'interfaccia in core/platform/. Mai `bwrap` o percorsi
    POSIX sparsi nel codice applicativo.

## Stile codice

- Python 3.12, asyncio, type hints ovunque, pydantic per gli schema.
- Nessuna eccezione propaga all'LLM: ToolResult(ok=False, error=...).
- structlog, mai print. Le chiavi API MAI nei log.
- Unità: millimetri nel 3D, pixel nella UI, pollici solo verso SketchUp.

## Non fare senza chiedere
- Aggiungere dipendenze non elencate.
- Introdurre React.
- Eseguire stringhe generate dall'LLM.
- Toccare file fuori dalle radici consentite.

## Copyright su codice di terzi

30. **Non copiare codice da repository di terzi** studiati come riferimento
    (vedi `docs/ANALISI-REPO-E-TECNOLOGIE.md`). Le idee architetturali si
    reimplementano da zero; il codice altrui, anche se pubblico su GitHub,
    resta coperto da copyright salvo licenza permissiva esplicita e
    verificata. Due dei tre repo analizzati hanno copyright pieno.

## Riferimenti

- La specifica completa e' in `docs/SPEC.md`. Consultala prima di ogni fase.
- I riferimenti visivi sono in `docs/design-reference/`.
  **famiglia-a/ = DA SEGUIRE. famiglia-b/ = NON SEGUIRE (contiene glow).**
  Leggi `docs/design-reference/README.md` prima di ogni componente visivo.
- `docs/ANALISI-REPO-E-TECNOLOGIE.md` contiene le idee adottate da progetti
  esterni e le tecnologie valutate e SCARTATE (Qt/QML, Unreal, Lottie, GSAP,
  React/Vue). Non riproporle.
- Il piano a fasi e' in `docs/SPEC.md` §22. Lavori UNA fase per volta.
  Non anticipi mai la fase successiva.

## Documentazione aggiornata

Prima di usare anime.js, uPlot, three-globe, augmented-ui, troika-three-text o
gli addon three.js, consulta la documentazione aggiornata via Context7.
NON scrivere a memoria: anime.js v4 ha API sostanzialmente diverse dalla v3 e
il modello tende alla v3. Lo stesso vale per PixiJS v8 e LangGraph 1.x.

## Definizione di "fatto"

Una fase e' chiusa solo quando TUTTI questi punti sono verdi:
1. i test della fase passano
2. il criterio di accettazione dichiarato in `docs/SPEC.md` §22 e' verificato
   e l'esito e' scritto in `docs/acceptance/FASE-NN.md`
3. per ogni componente visivo: il ciclo §11.7 e' stato eseguito e la
   checklist §11.8 riportata punto per punto
4. il commit e' fatto

Se non puoi verificare un criterio, lo DICHIARI. Non lo dai per buono.
```


---

# 21. Repo e codice

## 21.1 Struttura

```
jarvis-os/
├── CLAUDE.md
├── pyproject.toml
├── config/{default.toml, settings.schema.json}
├── core/
│   ├── engine.py  router.py  memory.py  settings.py  ws_server.py
│   ├── gpu_scheduler.py
│   ├── platform/                 # ◄ isolamento OS (§23)
│   │   ├── base.py               # Protocol: Sandbox, Audio, Paths, Sensors
│   │   ├── linux.py              # bwrap, PipeWire, XDG
│   │   └── windows.py            # (futuro) Job Objects, WASAPI, %APPDATA%
│   ├── llm/{grammar.py, claude_t1.py, claude_t2.py, governor.py}
│   ├── providers/
│   │   ├── base.py  registry.py  chunker.py  health.py
│   │   ├── stt_deepgram.py  stt_local.py
│   │   └── tts_deepgram.py  tts_local.py
│   ├── voice/{wake.py, pipeline.py, audio_io.py}
│   ├── tools/{registry.py, files.py, system.py, model3d.py, web.py}
│   ├── sandbox/{runner.py, policy.py}
│   ├── vision/{argus.py, ocr.py}
│   ├── gestures/{tracker.py, mapping.py}
│   └── news/{feeds.py, topics.py, gate.py}
├── app/{main.js, preload.js, package.json}
├── ui/
│   ├── gallery.html              # ◄ galleria componenti (§11.7)
│   └── src/
│       ├── style/tokens.css      # ◄ sorgente unica di verità
│       ├── bus.js
│       ├── anim/{boot.js, panels.js, rings.js, counters.js}
│       ├── windows/{winbox.js, browser.js, confirm.js}
│       ├── three/
│       │   ├── component.js      # ParametricComponent
│       │   ├── quality-gate.js
│       │   ├── math/{pointcloud.js, spline.js, extrude.js, globe.js}
│       │   └── components/{reactor-ring.js, node-graph.js, ...}
│       ├── css3d/{planes.js, board.js}    # ◄ piani stratificati, board
│       ├── pixi/
│       └── panels/{telemetry.js, files.js, console.js, agents.js,
│                   globe.js, browser.js, source.js, news.js, settings.js}
├── .claude/agents/{forge.md, argus.md, edith.md, veronica.md}
├── security/  packaging/
└── docs/
    ├── design-reference/{README.md, famiglia-a/, famiglia-b/}
    └── acceptance/
```

## 21.2 Allowlist tipizzata

```python
# core/tools/registry.py
from typing import Any, Callable, Awaitable
from pydantic import BaseModel

class ToolResult(BaseModel):
    ok: bool
    output: Any = None
    error: str | None = None

class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]
    side_effect: bool
    gesture_allowed: bool = False
    handler: Callable[[BaseModel], Awaitable[ToolResult]]
    model_config = {"arbitrary_types_allowed": True}

_REGISTRY: dict[str, Tool] = {}

def register(tool: Tool) -> None:
    # il vincolo gesture è IMPOSTO qui
    if tool.side_effect and tool.gesture_allowed:
        raise ValueError("un tool con side_effect non può essere gesture_allowed")
    _REGISTRY[tool.name] = tool

def get(name: str) -> Tool | None: return _REGISTRY.get(name)
```

## 21.3 Protocol dei provider

```python
# core/providers/base.py
from typing import Protocol, AsyncIterator
from dataclasses import dataclass

@dataclass
class Transcript:
    text: str; is_final: bool; confidence: float = 1.0; end_of_turn: bool = False

@dataclass
class AudioChunk:
    pcm: bytes; sample_rate: int

class STTProvider(Protocol):
    name: str
    async def stream(self, audio: AsyncIterator[bytes]) -> AsyncIterator[Transcript]: ...
    async def aclose(self) -> None: ...

class LLMProvider(Protocol):
    name: str
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]: ...
    async def aclose(self) -> None: ...

class TTSProvider(Protocol):
    name: str
    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]: ...
    async def flush(self) -> None: ...
    async def interrupt(self) -> None: ...
    async def aclose(self) -> None: ...
```

## 21.4 Telemetria — versione corretta

⚠️ Le revisioni precedenti avevano **due bug reali**: `process_iter` su tutti i processi 2,5 volte al secondo (1000 letture di `/proc`/s per tre righe), e `cpu_percent` inaffidabile perché `process_iter` ricrea gli oggetti `Process`, azzerando il contatore.

```python
# core/ws_server.py
import asyncio, json, time, psutil
from websockets.asyncio.server import unix_serve
from websockets.exceptions import ConnectionClosed

from core.platform import RUNTIME_DIR_MODE, paths as platform_paths

FAST_HZ, SLOW_HZ = 2.5, 1.0
_proc_cache: dict[int, psutil.Process] = {}

def _package_temp() -> float | None:
    temps = getattr(psutil, "sensors_temperatures", lambda: {})()
    for key in ("k10temp", "coretemp", "zenpower"):
        if temps.get(key): return max(t.current for t in temps[key])
    return None

def _top3_cpu() -> list[dict]:
    """Cache persistente: cpu_percent è affidabile solo su oggetti riusati."""
    alive = set()
    for p in psutil.process_iter(["pid"]):
        pid = p.info["pid"]; alive.add(pid)
        if pid not in _proc_cache:
            try:
                _proc_cache[pid] = psutil.Process(pid)
                _proc_cache[pid].cpu_percent(None)      # innesca il contatore
            except psutil.NoSuchProcess:
                continue
    for pid in set(_proc_cache) - alive: _proc_cache.pop(pid, None)
    rows = []
    for pid, proc in list(_proc_cache.items()):
        try:
            rows.append({"pid":pid, "name":proc.name(), "cpu":proc.cpu_percent(None)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            _proc_cache.pop(pid, None)
    rows.sort(key=lambda d: d["cpu"], reverse=True)
    return rows[:3]

def sample_fast() -> dict:
    vm = psutil.virtual_memory()
    return {"topic":"telemetry", "ts":time.time(),
            "cpu_percent":psutil.cpu_percent(None),
            "ram_percent":vm.percent, "package_temp_c":_package_temp()}

def make_advisory(t, top3):
    temp = t.get("package_temp_c")
    if temp is not None and temp > 75:
        return {"topic":"agent.advisory","level":"critical",
                "reason":"package_temp>75C","top3":top3}
    if t["ram_percent"] > 90:
        return {"topic":"agent.advisory","level":"warn","reason":"ram>90%"}
    return None

async def _handler(ws, state_provider):
    # la UI è stateless, il core è l'unica fonte di verità
    await ws.send(json.dumps({"topic":"state.snapshot", **state_provider()}))
    top3, last_slow = [], 0.0
    try:
        while True:
            t = sample_fast(); now = time.time()
            if now - last_slow >= 1.0 / SLOW_HZ:
                top3, last_slow = _top3_cpu(), now
                t["top3"] = top3
            await ws.send(json.dumps(t))
            if (adv := make_advisory(t, top3)): await ws.send(json.dumps(adv))
            await asyncio.sleep(1.0 / FAST_HZ)
    except ConnectionClosed:
        return

async def main(state_provider, paths=None):
    """Ascolta su un socket UNIX, non su TCP. Il perché è in §18.2."""
    paths = paths or platform_paths()
    sock = paths.socket_path()

    # mkdir(mode=...) NON applica il modo se la directory esiste già, e la
    # umask puo' comunque toglierne bit: il chmod esplicito non e' ridondante.
    # E' questa directory la difesa vera, non i permessi del socket (§18.2).
    sock.parent.mkdir(parents=True, exist_ok=True)
    sock.parent.chmod(RUNTIME_DIR_MODE)                    # 0700

    # Un socket orfano da un crash precedente fa fallire il bind con EADDRINUSE.
    sock.unlink(missing_ok=True)

    async with unix_serve(lambda ws: _handler(ws, state_provider), str(sock)):
        sock.chmod(0o600)                                  # ridondanza, non difesa
        await asyncio.Future()
```

## 21.5 Router e stream di Claude Code

```python
# core/router.py — LangGraph 1.x
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    text: str; tier: Literal["t0","t1","t2"] | None
    result: dict | None; steps: int

MAX_STEPS = 6

def normalize(s): return {"text": s["text"].strip().lower(), "steps": 0}

def classify(s):
    """T0: parser a grammatica, NON un LLM. Sotto i 10 ms."""
    t = s["text"]
    if any(k in t for k in ("apri","chiudi","pannello","cerca file",
                            "cartella","volume","cpu","memoria")): return {"tier":"t0"}
    if any(k in t for k in ("scrivi","codice","genera","modello",
                            "organizza","analizza")): return {"tier":"t2"}
    return {"tier":"t1"}

def route(s) -> Literal["t0","t1","t2"]: return s["tier"]

async def t0(s): return {"result":{"ok":True}, "steps":s["steps"]+1}
async def t1(s): return {"result":{"streamed":True}, "steps":s["steps"]+1}
async def t2(s): return {"result":{"spawned":True}, "steps":s["steps"]+1}

def build_router():
    g = StateGraph(AgentState)
    for n, f in (("normalize",normalize),("classify",classify),
                 ("t0",t0),("t1",t1),("t2",t2)): g.add_node(n, f)
    g.add_edge(START,"normalize"); g.add_edge("normalize","classify")
    g.add_conditional_edges("classify", route, {"t0":"t0","t1":"t1","t2":"t2"})
    for n in ("t0","t1","t2"): g.add_edge(n, END)
    return g.compile()
```

```python
# core/llm/claude_t1.py — parsing dello stream
async for line in proc.stdout:
    evt = json.loads(line)
    if evt.get("type") == "stream_event":
        delta = evt.get("event", {}).get("delta", {})
        if delta.get("type") == "text_delta":
            yield delta["text"]                    # → dritto al TTS
    elif evt.get("type") == "system" and evt.get("subtype") == "api_retry":
        bus.publish("agent.advisory", {"level":"warn","reason":evt["error"],
                                       "retry_ms":evt["retry_delay_ms"]})
    elif evt.get("type") == "result":
        session_id, cost = evt["session_id"], evt.get("total_cost_usd")
```

---

# 22. Piano a fasi e stime

### FASE 0 — Scaffold · 2 gg
> Repo secondo §21.1, `CLAUDE.md` con §20, Python 3.12 con uv, `core/settings.py`. **`ui/src/style/tokens.css` con §10.1, completo, prima di qualunque componente.** **`core/platform/base.py`** coi Protocol OS-specifici (§23).

**Criterio**: pytest verde; i token esistono prima di ogni CSS; nessuna chiamata OS fuori da `platform/`.

### FASE 0b — Galleria · 2 gg · **NUOVA**
> `ui/gallery.html` con routing `?component=`, `&grid=1`, `&tokens=audit`. Script Playwright `npm run shot`. Le immagini di riferimento in `docs/design-reference/` con README che distingue Famiglia A da Famiglia B.

**Criterio**: un componente di prova non conforme si illumina di magenta nell'audit. Lo screenshot si genera con un comando.

### FASE 1 — Core, allowlist, sandbox, telemetria · 1,5 sett.
> `engine.py`, `tools/registry.py` (§21.2), `sandbox/runner.py` (bwrap dietro `platform/linux.py`), `ws_server.py` (§21.4), `gpu_scheduler.py` (§9).

**Criterio**: `websocat` riceve snapshot e telemetria reale. Un tool non registrato solleva. La sandbox blocca scrittura fuori radice e rete.

### FASE 1b — Fetta verticale · 3 gg
> Finestra Electron massimizzata, un pannello WinBox con augmented-ui e token, collegato al WebSocket, con una striscia uPlot che mostra CPU/RAM reali.

**Criterio**: catena core → WS → Electron → pannello. Il pannello supera la checklist §11.8 col ciclo §11.7.

### FASE 2 — Filesystem reale · 2 sett.
> `tools/files.py` (§6.1), validazione post-`resolve()`, solo cestino, conferma §6.2 col path risolto, pannello file manager.

**Criterio**: i tre casi Stonic funzionano con una conferma per operazione. Nessun path fuori radice passa, nemmeno con `../`.

### FASE 3 — Voce · 3 sett.
> Wake Vosk (§7.2). **Deepgram Flux primario** STT e TTS, fallback locale automatico e annunciato. T1 persistente (§5.2). Chunker solo davanti a Kokoro. Barge-in con `text_spoken` in memoria.

**Criterio**: *"papà è a casa"* esegue in **~30 ms offline**; conversazione col **primo suono entro ~1 s**; staccando la rete il fallback si attiva e viene annunciato; barge-in entro 200 ms.

### FASE 4 — T2, Governor, subagent, memoria · 1,5 sett.
> `claude_t2.py`, `governor.py`, i quattro subagent, `router.py`, `memory.py` (senza duplicare il contesto di T1).

**Criterio**: operazione lunga in T2 mentre T1 risponde. Su rate limit T2 si sospende, T1 sopravvive.

### FASE 5 — Ambiente 3D e design · 5 sett.
> `ParametricComponent` e `qualityGate` **prima** di qualunque componente. Poi: anelli (SVG+anime.js), globo (three-globe+d3-geo), nuvole di punti, grafo a nodi (D3), tavola periodica (CSS Grid), glifi (PixiJS). Linee 3D **solo** con `Line2`/`LineMaterial`. Etichette 3D con troika.

**Criterio**: 60fps dentro il budget §10.4. Ogni componente ha parametri, versione, supera il gate **e il ciclo di verifica visiva**. Zero dati segnaposto.

### FASE 6 — Web, YouTube, CSS 3D, ARGUS · 2,5 sett.
> `<webview>` in pannello (§6.3). IFrame Player API. YouTube Data API. **Piani stratificati e board investigativa in CSS 3D** (§11.4). ARGUS `scope="app"` (§12).

**Criterio**: *"apri YouTube e metti synthwave"* funziona. La board 3D contiene testo selezionabile e una `<webview>` viva. Il renderer resta senza accesso al filesystem.

### FASE 7 — Gesture · 2 sett.
> MediaPipe CPU, isteresi 5 frame, solo `gesture_allowed`. Picking con three-mesh-bvh.

### FASE 8 — News · 1,5 sett.
> RSS + Guardian + YouTube, estrattore, gate, budget. Contenuto news solo in contesti con zero tool.

**Criterio**: budget 3/ora rispettato. Test di injection: un contenuto con istruzioni iniettate non produce alcuna azione.

### Suite di eval — trasversale, da Fase 1 in poi

Con Claude Code che scrive il codice, gli eval passano da buona pratica a
**necessità**: sono l'unico modo per accorgersi che una sessione ha rotto
qualcosa che funzionava tre fasi fa.

| File | Cosa misura | Da |
|---|---|---|
| `tests/t0_corpus.py` | 100 frasi etichettate: intento e latenza mediana | Fase 3 |
| `tests/eval_tools.py` | ogni tool dell'allowlist su input validi e invalidi | Fase 2 |
| `tests/eval_paths.py` | nessun path fuori radice passa, nemmeno con `..` | Fase 2 |
| `tests/eval_injection.py` | contenuto con istruzioni iniettate non produce azioni | Fase 6 |
| `tests/eval_visual.py` | ogni componente passa quality gate e checklist §11.8 | Fase 5 |

Gira all'**inizio** di ogni fase, non solo alla fine: è così che scopre le
regressioni della fase precedente.

### FASE 9 — Packaging · 3 gg
> Unit systemd utente. `jarvis-voice.service` con **`Restart=always`**.

## Stime

| Fase | Effort |
|---|---|
| 0 Scaffold + token + platform | 2 gg |
| 0b Galleria e ciclo visivo | 2 gg |
| 1 Core, allowlist, sandbox, telemetria | 1,5 sett. |
| 1b Fetta verticale | 3 gg |
| 2 Filesystem reale | 2 sett. |
| 3 Voce | 3 sett. |
| 4 T2, Governor, memoria | 1,5 sett. |
| 5 Ambiente 3D e design | 5 sett. |
| 6 Web, CSS 3D, ARGUS | 2,5 sett. |
| 7 Gesture | 2 sett. |
| 8 News | 1,5 sett. |
| 9 Packaging | 3 gg |
| **Totale** | **~5 mesi** |

I due giorni della Fase 0b si ripagano da soli nella Fase 5: senza il ciclo di verifica visiva, ogni componente 3D richiede tre o quattro giri di correzione manuale.

---

# 23. Portabilità verso Windows

Lei ha detto: Linux ora, Windows in futuro. **Non costruisca per Windows adesso** — sarebbe lavoro speculativo. Ma quattro cose vanno isolate oggi, perché isolarle dopo costa dieci volte tanto.

```python
# core/platform/base.py
from typing import Protocol
from pathlib import Path

class SandboxRunner(Protocol):
    async def run(self, argv: list[str], rw_paths: list[Path],
                  timeout: float) -> tuple[int, str, str]: ...

class AudioIO(Protocol):
    async def input_stream(self, sample_rate: int): ...
    async def play(self, pcm: bytes, sample_rate: int) -> None: ...

class Paths(Protocol):
    def config_dir(self) -> Path: ...
    def data_dir(self) -> Path: ...
    def workspace(self) -> Path: ...

class Sensors(Protocol):
    def package_temp(self) -> float | None: ...
```

| Area | Linux (oggi) | Windows (domani) | Rischio se non isolata |
|---|---|---|---|
| **Sandbox** | `bubblewrap` + seccomp | Job Objects, AppContainer, o WSL2 | **alto** — è la differenza più grande. `bwrap` non esiste su Windows e non ha un equivalente diretto |
| **Audio** | PipeWire | WASAPI (via `sounddevice`) | medio — `sounddevice` astrae quasi tutto |
| **Path** | XDG (`~/.config`, `~/.local/share`) | `%APPDATA%`, `%LOCALAPPDATA%` | basso se usa `Paths` da subito |
| **Temperature** | `psutil.sensors_temperatures()` | **non disponibile** su Windows in psutil; servirebbe LibreHardwareMonitor o WMI | basso — degradi a `None` |

**Cosa funziona già su entrambi**: Electron, three.js, tutto il renderer, Claude Code CLI, Deepgram, Vosk, Kokoro, faster-whisper, MediaPipe, il WebSocket, l'allowlist.

**In pratica**: il renderer è già portabile al 100%. Del core, il 90% lo è. Il 10% che non lo è vive in `core/platform/` — e se rispetta l'invariante 29 del `CLAUDE.md`, il giorno che vuole Windows scrive un solo file nuovo.

⚠️ **La sandbox resta il punto duro.** Se Windows diventasse prioritario, valuti se il profilo `exec` Le serve davvero o se può sostituirlo con un container Docker/Podman, che è portabile. Ma non lo faccia adesso: su Linux `bwrap` è più leggero e più sicuro.

---

# 24. Cosa resta incerto

1. **Se Haiku 4.5 supporti i cinque livelli di effort.** La documentazione li descrive per Opus 5 e Fable 5. Lo misuri.
2. ~~La latenza di avvio~~ — **misurata**: mediana 2,41 s a freddo (§5.2). Resta da misurare **il primo token sulla sessione persistente**, che è il numero che conta davvero. Atteso 300–900 ms; se superasse 1,5 s il vantaggio del design si assottiglia e va rivalutato.
3. **La precisione di Vosk sulle Sue frasi**, in italiano, col Suo microfono e la Sua stanza. **Almeno 20 ripetizioni per frase** prima di fidarsi.
4. **Il link Pinterest non è stato analizzato** — bloccato ai fetch automatici.
5. **Il costo VRAM della scena 3D a 60fps**: nessuna fonte primaria lo quantifica. La stima 1–2 GB è prudenziale.
6. **MediaPipe**: la preoccupazione sulla roadmap viene da un issue tracker, non da una dichiarazione ufficiale.
7. **Valutazione legale**: non sono un avvocato.
8. **Il costo mensile Deepgram con uso quotidiano.** Non l'ho stimato: dipende da quante ore di audio genera. Lo monitori dal primo mese — è la sola voce di costo ricorrente del progetto, dato che l'LLM è già nel Suo abbonamento.
