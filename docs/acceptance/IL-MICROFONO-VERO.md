# Il microfono vero — §7.2, §26.7 residui ② e ③

**Data**: 31 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.1-§7.2,
`CLAUDE.md` invariante 13 · **Rollback**: `fa43981`
**Test**: 2033 → **2039**, 25 saltati, **0 rossi**

> Era l'ultimo `NON VERIFICATO` della fetta 6: *«che una frase aggiunta dalla
> pagina svegli JARVIS detta a un microfono»*. La scrittura e il ricarico erano
> provati dal vivo; l'ultimo metro, quello dall'aria al riconoscitore, no.

**Adesso lo è**, due volte: prima con una voce sintetica che esce
dall'altoparlante e rientra dal microfono del portatile, poi **con la voce del
Signore**. E attraversando quell'ultimo metro si è scoperto che **il metro
prima era rotto**: il ricarico a caldo, attraverso l'inotify vero, non
funzionava affatto.

---

## Il criterio, punto per punto

| # | criterio | esito |
|---|---|---|
| 1 | una frase nuova entra col tool che invoca la pagina | ✅ `ok=True`, `verdetto=riuscito` |
| 2 | arriva al riconoscitore **per inotify**, senza `reload()` a mano | ✅ **e prima non ci arrivava**: vedi §② |
| 3 | detta **in aria**, sveglia JARVIS | ✅ `wake_trigger`, 6 giri su 6 |
| 4 | il trigger porta l'azione giusta | ✅ `azione='scene:avvio'` |
| 5 | detta da una **voce umana** | ✅ **10 su 10**, mediana 8,54 ms — vedi §⑤ |
| 6 | `uv run pytest -q` verde | ✅ 2039 passati, 0 rossi |

---

## ① Il microfono di questa macchina, misurato

Due sorgenti. Si è suonato un tono di 1 kHz dall'altoparlante e si è guardata
l'energia a quella frequenza, prima in silenzio e poi col tono:

| sorgente | silenzio | col tono | |
|---|---|---|---|
| `61` ALC257 analogico (presa jack) | 0,01 | 0,02 | **sorda**: non c'è niente attaccato |
| `62` DMIC digitale (**predefinita**) | 0,22 | **633** | è quella che JARVIS apre |

⚠️ **E il DMIC apre il gate per 200 ms appena lo si accende.** L'energia del
VAD, a finestre di 100 ms, con la stanza in quiete:

```
    0 ms   0,72766   ← sessanta volte la soglia di apertura (0,012)
  100 ms   0,02041   ← ancora aperta
  200 ms   0,00325   ← stanza in quiete, gate chiuso
```

Cioè **ogni apertura del microfono comincia con due blocchi di rumore dentro
Vosk**, a gate aperto, seguiti da una chiusura e da un `FinalResult` su una
raffica. Non fa danno — la grammatica vincolata e `[unk]` scartano tutto — ma
c'è, e in esercizio non lo salta nessuno. **Dichiarato, non risolto qui**:
saltarlo è una decisione di piattaforma, e prenderla dentro un banco vorrebbe
dire nasconderla.

La **polarizzazione continua** dello stesso convertitore — circa −8600 — è
invece cosa già nota e già risolta: `VAD.energia` toglie la media, e la sua
docstring porta la misura del 28 agosto.

---

## ② Il difetto che solo il microfono ha trovato

Il residuo ② di §26.7 diceva:

> *«Il ricarico a caldo è provato con `store.reload()` a mano, non con
> l'inotify vero.»*

Sembrava una pignoleria. Non lo era: **attraverso l'inotify il ricarico non
funzionava**, e chiamare `reload()` a mano saltava esattamente il pezzo rotto.

### La misura

Due giri identici tranne **una `read_text()`**:

```
A  nessuna lettura dopo l'avvio            avvisati=[5]   ← ricarica
B  UNA lettura prima di scrivere           avvisati=[]    ← NON ricarica
```

### Perché

inotify manda `IN_OPEN` anche a chi apre il file per **leggerlo**, e
l'antirimbalzo di `_ChangeHandler` era sul **fronte di salita**: la lettura
consumava la finestra di 200 ms, e la scrittura che arrivava un millisecondo
dopo veniva scartata.

E `imposta_valore` **legge** il TOML — `_documento(percorso)` — prima di
riscriverlo. Cioè il difetto colpiva precisamente la strada per cui il ricarico
a caldo esiste: **ogni** impostazione cambiata dalla pagina restava sul disco
senza mai arrivare al processo. Le frasi di wake non raggiungevano il
riconoscitore, mai.

### Perché nessun test lo vedeva

`TestRicaricaACaldo::test_emette_evento_sul_cambio` riscrive lo stesso valore
**fino a cinquanta volte** con `debounce_s=0.01`: prima o poi una scrittura
cade fuori dalla finestra e l'evento passa. La ripetizione serviva a coprire
l'intervallo fra `Observer.start()` e il watch attivo — una ragione buona — e
copriva anche il difetto.

### La correzione, in due pezzi

1. **Una lettura non è un cambio.** `opened` e `closed_no_write` non arrivano
   più al gancio. Un `jarvis doctor` o un `_documento()` non fanno più
   rileggere e riconfrontare l'intero `Settings`.
2. **L'antirimbalzo passa sul fronte di DISCESA.** Si ricarica una volta sola,
   `debounce_s` dopo l'**ultimo** evento, quando il file è fermo. Sul fronte di
   salita si ricaricava al primo evento della raffica — cioè si leggeva il file
   *mentre* lo si stava scrivendo — e si scartava il resto, l'ultimo compreso:
   un editor che salva sul posto lasciava le impostazioni al valore di mezzo
   fino al cambio successivo.

`SettingsStore.stop()` butta via un ricarico in attesa: col fronte di discesa
un `Timer` può essere già partito quando la sorveglianza si ferma.

### I sabotaggi

| sabotaggio | rosso |
|---|---|
| il filtro sulle letture non c'è più | `test_una_lettura_da_SOLA_non_fa_ricaricare`, `test_le_letture_non_arrivano_MAI_al_gancio`, `test_stop_butta_via_un_ricarico_in_ATTESA` |
| l'antirimbalzo torna sul fronte di salita | `test_l_antirimbalzo_e_sul_fronte_di_DISCESA`, `test_stop_butta_via_…` |
| `stop()` non annulla il timer | `test_stop_butta_via_un_ricarico_in_ATTESA` |
| **il codice com'era il 30 agosto** (entrambi) | tutti e tre, `test_il_cambio_arriva_anche_se_qualcuno_ha_appena_LETTO_il_file` compreso |
| il codice del 30 agosto, contro il **tool vero** | `test_il_TOOL_scrive_e_l_iscritto_lo_viene_a_sapere` |

⚠️ **Un sabotaggio non produceva rosso, e ha riscritto un test.** La prima
stesura di `test_l_antirimbalzo_e_sul_fronte_di_DISCESA` guidava il difetto
attraverso inotify, con due scritture di fila: l'esito dipendeva da chi vinceva
la corsa fra il thread di watchdog e la seconda scrittura, e quasi sempre il
dispatch arrivava a cose fatte leggendo già il contenuto finale. Adesso gli
eventi si danno al gestore **a mano**: nessuna corsa, e la differenza fra i due
fronti è un'asserzione sola.

---

## ③ La catena intera, dal vivo

```
[frasi nel file] ['jarvis', 'jarvis buonanotte', 'jarvis silenzio', 'papa e a casa']
[scritta] ok=True errore=None verdetto=riuscito
   wake_frasi_chieste      quando="al primo blocco di parlato che arriva"
   frasi_ricaricate_a_caldo
[inotify] la frase e' arrivata al wake: True
[wake] la frase e' VIVA nel riconoscitore: True
[dico] 'accendi la scrivania' dall'altoparlante
   wake_frasi_applicate
   wake_trigger  frase='accendi la scrivania' azione='scene:avvio' latenza_ms=15.5
[SVEGLIATO]
```

```
imposta_valore → conferma §6.2 → tomlkit → settings.toml
  → inotify VERO → SettingsStore.reload() → Engine._ricarica_frasi
  → PhraseWake.set_frasi() → pw-record → ALTOPARLANTE → ARIA → MICROFONO
  → VAD → Vosk → Trigger
```

**Sei giri su sei** con la voce sintetica, **dieci su dieci** con quella del
Signore. `scripts/prova_microfono.py`.

⚠️ Il registro mostra che **il tono apre il gate** prima di quasi ogni frase —
`gate APRE` seguito da `gate CHIUDE nessuna frase nota`. È il bip di §7.2 che
rientra dal microfono, ed è la conferma che il segnale di via arriva davvero
dove deve.

---

## ④ Il banco, e le tre decisioni che porta

**Non si accende il grado voce.** `voice.enabled = true` costruisce il grado
intero e **spawna T1**, un processo `claude` persistente (§5.2). Il wake non
tocca nessun LLM — sta prima di T0, che già non ne tocca (invariante 14) —
quindi accenderlo farebbe spendere l'abbonamento per provare un percorso che
non lo attraversa. È la ragione per cui `scripts/banco_haiku.py` sta fuori da
`pytest`: **un test che spende non è un test**.

**Il ricarico è quello dell'`Engine`, non una copia.** Ci si iscrive con
`engine._ricarica_frasi`, che prende il wake per parametro: il cancello «il
file è cambiato altrove», l'avviso sul modello che non si ricarica e il
rimbalzo sul loop sono quelli veri. Riscriverli nel banco vorrebbe dire provare
la copia invece dell'originale — il difetto che questo progetto ha già misurato
tre volte, l'ultima con `nascosto` che cadeva nella terza copia campo-per-campo
(fetta 5).

**Il gate è quello di `pipeline.py`.** ⚠️ La prima stesura del banco lo
saltava, e non funzionava: senza gate `feed()` non ha mai un enunciato chiuso —
`chiudi()` è l'unico a riabbassare `_enunciato_aperto` — e un cambio di frasi
depositato da `set_frasi()` **non entra mai in vigore**. Misurato: la frase
arrivava al wake, `frasi_ricaricate_a_caldo` nei log, e `frasi_vive` restava
l'elenco di prima.

### E un'ipotesi sbagliata, misurata invece che creduta

Il banco riusciva **3 volte su 4**. La prima ipotesi era che la voce sintetica
facesse pause abbastanza lunghe da chiudere il gate a metà frase; si è
rallentata e poi accelerata la voce, e non è cambiato niente — 3 su 4 da
lente, 4 su 6 da normali. Registrando l'audio e ripassandolo enunciato per
enunciato si è visto che **Vosk sente la frase intera e la riconosce**:

```
[  120 ms] gate APRE    energia=0.0149
[ 1700 ms] gate CHIUDE  vosk dice: 'accendi la scrivania'
```

La causa vera era il **momento** in cui il cambio entra in vigore: se il gate
è già aperto quando la frase comincia, l'enunciato va al riconoscitore di
prima. Il banco adesso aspetta che la frase sia **viva** (`frasi_vive`), non
solo dichiarata (`frasi`) — che è esattamente la distinzione per cui quella
proprietà esiste. **6 su 6.**

Non è un difetto del prodotto: la garanzia di `PhraseWake.chiudi()` — un
enunciato già cominciato non si butta via — è deliberata e resta.

---

## ⑥ I due modi della latenza — indagati

Le tre misure mostravano una latenza **bimodale**: uno stretto intorno a
8,5 ms e uno intorno a 15. Dichiarato non spiegato il 31 agosto; spiegato qui.

### Che cosa misura quel numero

La docstring di `Trigger.latenza_ms` lo dice già, ed è il punto di partenza:

> *«Non è la latenza di risveglio. È il costo di UNA `AcceptWaveform` o di un
> `FinalResult()` — microsecondi di CPU, non il tempo dal parlato.»*

Due operazioni Kaldi diverse in un campo solo: la prima ipotesi era che i due
modi fossero **le due porte**.

### Tre ipotesi, tutte e tre refutate

**① La porta.** Rigiocando a freddo otto frasi catturate, cinque volte:
**40 trigger su 40** escono da `chiudi/FinalResult`, e da sola quella porta è
strettissima — mediana 7,91 ms, min 7,22, max 8,22. **Zero** modi lenti. E dal
vivo entrambe le porte mostrano entrambi i modi (`feed` a 10,48 ms, `chiudi` a
7,54). Non è la porta.

**② La CPU addormentata.** Il governor è `powersave` con un intervallo di 8×
(623 MHz – 5,09 GHz), e nel vivo il processo dorme fra un blocco e l'altro:
sembrava spiegare un rapporto di 2. Due misure la smontano.

*Tempo di parete contro tempo di CPU*, dieci trigger dal vivo: coincidono in
ogni riga — `15,72` contro `15,69`, `8,87` contro `8,86`. Non è preemption: il
processo brucia davvero quel tempo.

*Un metro di taratura* — lavoro Python fisso, cronometrato subito prima della
chiamata Kaldi, che non chiede niente al kernel. Serve perché su `amd-pstate`
`scaling_cur_freq` riporta un valore nominale: nelle prime dieci righe le
letture **dopo** la chiamata stavano tutte a ~1979 MHz, che per dieci momenti
diversi è una firma, non un dato. Il metro dice:

```
chiamata lenta (15,24 ms)   metro 0,86 ms
chiamate veloci (8,6-8,9)   metro 1,05 – 1,21 ms
```

Sulla chiamata lenta la CPU era **più veloce**, non più lenta. Non è il clock.

**③ Il rumore che gonfia il reticolo.** Si mette davanti alla stessa frase
k blocchi di riempimento, una volta di **rumore di stanza vero** e una volta di
**silenzio digitale**:

```
k=25    rumore 14,60 ms     silenzio 13,95 ms
k=50    rumore 14,12 ms     silenzio 13,72 ms
k=100   rumore 14,48 ms     silenzio 14,52 ms
```

Identici. Il contenuto dell'audio non c'entra.

### La risposta: è periodico nella DURATA dell'enunciato

Stessa frase, riempimento di puro silenzio, un blocco per volta:

```
  blocchi  durata    costo
     73    1,46 s     8,30 ms   ████████
     74    1,48 s    13,88 ms   ██████████████
     …                          (sei blocchi lenti)
     79    1,58 s    14,43 ms   ██████████████
     80    1,60 s     8,28 ms   ████████
     …                          (sei blocchi veloci)
     85    1,70 s     8,39 ms   ████████
     86    1,72 s    14,44 ms   ██████████████
     …
     91    1,82 s    15,83 ms   ███████████████
     92    1,84 s     8,31 ms   ████████
     …
     97    1,94 s     8,47 ms   ████████
     98    1,96 s    14,36 ms   ██████████████
     …
    103    2,06 s    14,77 ms   ██████████████
    104    2,08 s     7,32 ms   ███████
```

**Sei blocchi lenti, sei veloci, a ripetizione.** Periodo **12 blocchi = 240 ms**
di enunciato, con le transizioni a 1,48 / 1,60 / 1,72 / 1,84 / 1,96 / 2,08 s —
cioè a intervalli esatti di 120 ms. Non dipende da che cosa contenga l'audio,
solo da **quanto dura**.

### E questo spiega perché a freddo non si vedeva mai

Nel rigioco le otto frasi erano lunghe **73 blocchi tutte** — la voce sintetica
dice sempre la stessa cosa nello stesso tempo. Stessa lunghezza, stessa fase
del ciclo, stesso costo: 40 su 40 veloci, 7,22–8,22 ms. Dal vivo la lunghezza
dipende da quando il gate si chiude, quindi la fase è di fatto casuale, e i due
modi compaiono.

### Il meccanismo — verificato, e non è la potatura

L'ipotesi era una **potatura periodica del reticolo**. È **sbagliata**, e si
smonta con l'aritmetica prima ancora che con una prova: `--prune-interval` vale
25 frame **del decodificatore**, e con `--frame-subsampling-factor=3` un frame
del decodificatore sono 30 ms — cioè 750 ms, non 240.

La causa vera è **la dimensione del pezzo con cui si valuta la rete neurale**.
L'elenco delle opzioni registrate, estratto dalla `libvosk.so` spedita col
pacchetto, la dichiara:

```
--frames-per-chunk : Number of frames in each chunk that is separately
                     evaluated by the neural net. Measured before any
                     subsampling […] (i.e. counts input frames.
                     (int, default = 24)
```

**24 frame d'ingresso × 10 ms = 240 ms**, che è esattamente il periodo misurato.

**Provato cambiandolo**, non dedotto. `conf/model.conf` del modello passa da un
`ParseOptions` severo — un'opzione inventata fa fallire il caricamento, quindi
un «non è cambiato niente» qui significa davvero qualcosa. Modello sostituito
con una copia a collegamenti simbolici, il vero non si tocca:

```
predefinito     .LLLLLL......LLLLLL......L   bande [6,6,6,6]    periodo 12  ✓
chunk 36        .LLLLLL............LLLLLL.   bande [6,12,6]     periodo 18  ✓
potatura 5      .LLLLLL......LLLLLL......L   bande [6,6,6,6]    periodo 12  ✓
potatura 100    ......L.......L..LL.LLLLLL   irregolare, max 21,58 ms
```

* **il periodo segue `frames-per-chunk`**: 24 → 12 blocchi, 36 → 18. Causale.
* **potare cinque volte più spesso non sposta niente**: il disegno è
  identico al predefinito, banda per banda. La potatura non è il metronomo.
* potare **molto** meno (100) alza il costo massimo a 21,58 ms e rompe la
  regolarità: la potatura governa **quanti gettoni si accumulano**, cioè
  l'ampiezza, non il ritmo.

E il sorgente di Vosk — letto, non copiato (invariante 30) — dice perché.
`recognizer.cc` costruisce un **`SingleUtteranceNnet3IncrementalDecoder`**, lo
stesso nome che compare nei typeinfo della libreria spedita. Il finale chiama,
in quest'ordine, `InputFinished()` sulla catena delle feature, poi
`UpdateSilenceWeights()`, poi **`AdvanceDecoding()`**, e solo allora
`FinalizeDecoding()`. `model.cc` legge `conf/model.conf` e **non** imposta
`frames_per_chunk`, che quindi resta a 24.

Il conto torna: durante il flusso la rete produce uscite solo a pezzi interi da
240 ms, quindi il decodificatore è sempre indietro di una frazione di pezzo che
dipende da dove è finito l'enunciato. `InputFinished()` costringe a svuotare il
pezzo parziale, e l'`AdvanceDecoding()` che segue deve smaltire quel residuo:
tanto più grande quanto più lontani si è dal confine.

⚠️ **Due cose che restano senza spiegazione**, e le dichiaro invece di
arrotondarle: la banda cara è larga **120 ms in entrambi i casi** — 6 blocchi
sia a chunk 24 sia a chunk 36 — e non so perché non scali col pezzo. E il
sovrapprezzo cresce meno del pezzo: +7,9 ms a 24, +10,4 ms a 36, cioè 1,32×
contro 1,5× di rapporto. Compatibile con «un pezzo di rete in più», non una
prova che lo sia.

### Perché non si tocca comunque

I due modi distano **6,3 ms**. La latenza di §7.5 — dal primo blocco con voce
al riconoscimento — misurata adesso dal banco è **~1.500 ms**, di cui 240 fissi
sono la coda del VAD (`coda_blocchi=12`). Sei millisecondi su millecinquecento
sono lo **0,4 %**, e stanno dentro un termine che non dipende da noi.

E non se ne fa un test: sarebbe fissare un dettaglio interno di una libreria di
terzi, che il giorno di un aggiornamento di Vosk diventerebbe rosso senza che
niente sia peggiorato.

⚠️ **Una correzione che viene da qui.** Il banco riferiva `latenza_ms`
chiamandola «latenza», ed è il numero che la sua stessa docstring dichiara non
essere quello. `aperto_a` lo riempie solo `pipeline.py:625`, e il banco la
pipeline non la usa: `latenza_risveglio_ms` tornava **zero** e non lo guardava
nessuno. Adesso il banco riempie `aperto_a` come fa la pipeline e stampa
entrambi, col nome giusto: `kaldi` e `risveglio`.

---

## ⑤ Che cosa NON è verificato — per nome

1. ~~La voce è sintetica.~~ ✅ **Chiuso lo stesso giorno, col Signore che
   parla.** Era il limite che contava, e la congiunzione che nessuno aveva mai
   provato — una frase *aggiunta col tool*, detta da *una persona* — adesso è
   provata:

   ```
   ▶ DILLO ADESSO: «accendi la scrivania»
   [SVEGLIATO] frase='accendi la scrivania' azione='scene:avvio' latenza=8,9 ms
   picco di energia: 0,0412        (soglia di apertura 0,0120)
   ```

   Le due metà erano provate separatamente: il **25 agosto**
   (`IL-GIRO-SI-CHIUDE.md`) una persona aveva svegliato JARVIS con **24
   trigger veri**, mediana 7,76 ms — ma su frasi **già nel file**. Oggi la
   frase è nuova, ci è arrivata dal tool, e la voce è quella di una persona.
   Gli 8,9 ms stanno accanto ai 7,76 di allora, e sotto i 15,2 della voce
   sintetica.

   ⚠️ Il primo giro era **un trigger solo** — un fatto, non una statistica — e
   così è stato dichiarato. Misurata subito dopo, **dieci ripetizioni guidate
   dal tono, dieci successi**:

   ```
   ESITO — umana, 10 su 10
      #   latenza    dal tono            #   latenza    dal tono
      1     8,29 ms    2,78 s            6     8,50 ms    2,33 s
      2     8,72 ms    2,58 s            7     8,59 ms    2,06 s
      3     7,19 ms    2,33 s            8     8,35 ms    1,94 s
      4    15,71 ms    2,33 s            9     9,03 ms    2,74 s
      5    14,63 ms    2,33 s           10     8,47 ms    3,10 s

   latenza  mediana 8,54 ms   min 7,19   max 15,71
   ```

   Contro la voce sintetica sulle stesse righe di codice: mediana 8,97 ms, min
   8,79, max 9,07 su 4 ripetizioni. E contro il 25 agosto: mediana 7,76 ms su
   24 trigger, max 13,95.

   **La latenza ha due modi**, e si vedono in tutte e tre le misure: uno
   intorno a 8,5 ms e uno intorno a 15. Due ripetizioni su dieci qui, una su
   quattro nella sintetica, `max 13,95` il 25 agosto. ✅ **Indagato: §⑥.** È
   periodico nella durata dell'enunciato — sei blocchi lenti, sei veloci — e
   vale lo 0,4 % della latenza che una persona percepisce.

   ⚠️ **Una colonna di quel giro era falsa, ed è un difetto del banco.** Il
   picco di energia riferiva il massimo di **tutta la sessione** invece che
   della singola ripetizione: sette righe su dieci dicevano `0,0366` identico
   alla quarta cifra, che per dieci frasi dette da una persona non è un dato,
   è una firma. `misura["picco"]` era azzerato fra una ripetizione e l'altra,
   ma `ascolta()` teneva anche una **variabile locale** che nessuno azzerava e
   che ci riscriveva dentro il massimo corrente. Corretto — una sola sede del
   massimo — e verificato: i picchi adesso variano fra ripetizioni.

   Non tocca il risultato: la latenza viene dai `Trigger`, e di fallimenti da
   diagnosticare non ce n'è stato nessuno. Di quel giro resta vero che il
   massimo di sessione ha toccato **0,0468**, quasi quattro volte la soglia.

2. **Una stanza in quiete, un microfono a mezzo metro.** ⚠️ E la quiete non è
   tanta quanta sembra: nella prova con la voce umana il gate si è aperto
   **due volte da solo** prima che il Signore parlasse, a `0,0121` e `0,0127`
   — cioè il rumore di fondo di questa stanza tocca la soglia di apertura
   (0,012). Non ha fatto danno; vuol dire che il margine è sottile. Nessuna prova con
   rumore di fondo, musica, o da tre metri di distanza. Le soglie del VAD
   (0,012 / 0,006) non sono state ritarate contro niente di tutto questo.
3. **Il grado voce intero non è mai partito.** T1, STT e TTS restano fuori:
   quello che si prova qui è il wake, che è il pezzo che l'invariante 13
   dichiara **sempre locale**. Che cosa succeda dopo il trigger — Deepgram, il
   ripiego annunciato, il barge-in — è provato altrove e non da qui.
4. **Il transitorio di 200 ms del DMIC resta in esercizio.** Misurato e
   dichiarato in §①, non tolto.
5. **La voce sintetica non è infallibile nemmeno lei**: in un giro da cinque
   ripetizioni una è mancata, con picco `0,0431` — cioè il suono era arrivato.
   Non indagata: non è il soggetto di questa prova, e le ripetizioni che
   contano sono quelle umane.
6. **La prova non gira in `pytest`.** Vuole un altoparlante, un microfono e
   una stanza; e tocca il muto del sistema, che rimette com'era in un
   `finally`. Il pezzo che *si può* provare senza aria — tool, disco, inotify,
   iscritto — è entrato nella suite:
   `test_il_TOOL_scrive_e_l_iscritto_lo_viene_a_sapere`.
