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
   quattro nella sintetica, `max 13,95` il 25 agosto. Non è stato indagato che
   cosa distingua i due casi — dichiarato, non spiegato.

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
5. **La prova non gira in `pytest`.** Vuole un altoparlante, un microfono e
   una stanza; e tocca il muto del sistema, che rimette com'era in un
   `finally`. Il pezzo che *si può* provare senza aria — tool, disco, inotify,
   iscritto — è entrato nella suite:
   `test_il_TOOL_scrive_e_l_iscritto_lo_viene_a_sapere`.
