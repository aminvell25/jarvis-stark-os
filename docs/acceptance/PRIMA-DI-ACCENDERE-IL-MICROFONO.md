# Prima di accendere il microfono — nove difetti, otto corretti

**Rollback:** `03536ba`
**Richiesta:** «prima di iniziare con *accendi voice.enabled e provo io col
microfono* voglio che rilustri che non ci siano altri problemi e nel caso
risolvili».
**Esito: nove difetti trovati, otto corretti e provati, uno dichiarato. La
catena vocale vera è stata composta contro il microfono vero e ha retto sei
secondi. Il riconoscimento resta non provato: quello lo prova Lei parlando.**

---

## 0. Che cosa sarebbe successo accendendo l'interruttore ieri

`voice.enabled = true` avrebbe avviato un processo `claude` e **non avrebbe
aperto il microfono.** L'intestazione di `core/engine.py` dichiara il grado da
sempre — «*voice.enabled → wake Vosk, STT/TTS, T1 persistente, supervisore*» —
e `_gradi()` costruiva **solo T1**.

Chi avesse parlato avrebbe parlato nel vuoto: nessun errore da leggere, e
nessun modo di distinguere un microfono muto da un codice che non ascolta.

È il difetto che questo file aveva già avuto una volta, su un'altra riga:

> §13: la memoria di Fase 4 esisteva, era provata, e NON era registrata nella
> radice di composizione — quindi i suoi quattro tool non esistevano nel
> processo vero.

Due volte lo stesso guasto nello stesso file. Da adesso c'è un test.

## 1. I nove difetti

| | difetto | dove | come si sarebbe visto |
|---|---|---|---|
| **1** | `_gradi()` componeva solo T1 | `engine.py` | microfono mai aperto, nessun errore |
| **2** | `engine.py` chiama `self._voce.annuncia()`, e il metodo **non esisteva** | `pipeline.py` | `AttributeError` **mentre** §5.6 e ADR-003 annunciano un guasto |
| **3** | `PhraseWake` non esponeva il modello | `wake.py` | secondo caricamento: **284 ms e 87 MiB** per la stessa cosa |
| **4** | un compito morto è **muto** | `engine.py` | microfono chiuso senza una parola |
| **5** | un turno che fallisce chiudeva il microfono **per la sessione** | `pipeline.py` | sordo dopo il primo errore di rete |
| **6** | la trascrizione riceveva blocchi irregolari e chiamava `input_stream()` nudo | `pipeline.py` | campioni s16 spezzati; `TypeError` su Windows |
| **7** | lo spegnimento **rilanciava** l'eccezione di un compito già morto | `engine.py` | l'arresto del core inciampa su un guasto già noto |
| **8** | l'annuncio di ripiego finiva nei log **due volte** | `engine.py` | quattro righe per due ripieghi |
| **9** | `news.enabled = true`, `Watcher` costruito, `giro()` **mai chiamato**, e lo snapshot diceva `collegato: true` | `engine.py` | «le notizie sono collegate» e nessun giro sui feed |

I primi tre erano già stati trovati e corretti in questa stessa passata; i
difetti **4-8** sono nuovi, e il **9** è dichiarato più che corretto (§5).

## 2. Il difetto 4, misurato invece che supposto

L'ipotesi era: «un `asyncio.Task` che muore mentre qualcuno ne tiene il
riferimento non dice niente». La prima misura sembrava smentirla — il messaggio
compariva **prima** delle righe successive. Era un artefatto di buffering:
`stderr` non è bufferizzato, `stdout` sì. Rifatta su un canale solo, con marca
temporale:

```
[  300.6 ms] a 0,3 s: done=True — il core e' vivo e tiene il riferimento
[  601.3 ms] FINE del programma
[  605.9 ms] loop.call_exception_handler: 'Task exception was never retrieved'
```

**L'unico messaggio arriva dopo la fine del programma**, cioè alla distruzione
dell'oggetto. Un core che gira per ore tenendone il riferimento **non ci arriva
mai**.

E le sorgenti di eccezione non sono ipotetiche: su questa macchina non c'è
chiave Deepgram, quindi il TTS è **EdgeTTS, che è di rete**; T1 è un processo
esterno; `pw-play` può mancare.

La correzione è un `add_done_callback` che distingue tre esiti — annullato
(spegnimento voluto), eccezione (guasto, con la causa), ritorno pulito (il
flusso è finito da solo) — e un campo nuovo nello snapshot: `voce.microfono`,
che vale `spento`, `aperto`, `chiuso` o `caduto: <causa>`. Prima lo snapshot
diceva `t1_vivo`, cioè che `claude` gira, e di chi ascolta non diceva niente:
**T1 vivo e microfono chiuso** era uno stato possibile e invisibile.

## 3. Il difetto 5, e perché è il più grave dei cinque nuovi

`await self._su_trigger(trigger)` stava dentro l'`async for` **senza rete**. Una
sola eccezione — EdgeTTS irraggiungibile, T1 morto — risaliva fuori dal ciclo,
`run()` finiva, e la scrivania restava sorda per il resto della sessione.

Un turno perso è un turno perso. Non è la fine dell'ascolto.

⚠️ `CancelledError` viene rilanciato e non inghiottito: è lo spegnimento, e
mangiarlo renderebbe `_spegni_gradi()` un'attesa infinita. C'è un test apposta.

## 4. Il difetto 6, che era una correzione lasciata a metà

`AUDIO-IO-BLOCCHI-ESATTI.md` aveva misurato che `read(640)` restituisce 640
byte solo 19 volte su 40, e aveva messo `dal_microfono()` davanti al ciclo
principale. **Ma `_trascrivi()` era rimasto indietro**, e chiamava
`self._audio.input_stream()` diretto — cioè proprio il percorso che manda il
testo **fuori dalla macchina** riceveva i blocchi irregolari, con un blocco di
lunghezza dispari che spezza un campione s16 fra due chiamate al riconoscitore.

Due proprietari per una proprietà sola: è la stessa specie dei tre ritagli e
dei due orologi di questa settimana.

E la chiamata era **nuda**. `core/platform/base.py` dichiara
`input_stream(self, sample_rate: int)` **senza valore predefinito**: qui
funzionava soltanto per il default dell'implementazione Linux, e su Windows —
che l'invariante 29 promette — sarebbe stato un `TypeError` al primo turno.

## 5. Il difetto 9: dichiarato, non corretto, e perché

`Watcher.giro()` non ha **un solo chiamante nel core**: solo
`tests/test_news.py` e `scripts/fixture_fusi.py`. Con `news.enabled = true`
nelle Sue impostazioni di oggi, il `Watcher` si costruisce a ogni avvio, lo
snapshot diceva `collegato: true`, e **nessun giro sui feed è mai avvenuto**.

`FASE-08.md` dichiara quattro punti non verificati; **questo non è fra loro**.

Non l'ho corretto perché scrivere il ciclo periodico vuol dire decidere una
cadenza e una lista di argomenti che `NewsSettings` non contiene — cioè una
funzione nuova, non una riparazione. Ho fatto la cosa minima e onesta: il campo
adesso si chiama come ciò che misura davvero.

```
"news": { "abilitate": true, "watcher_costruito": true, "giri_fatti": 0 }
```

`giri_fatti: 0` è il numero che rende visibile la differenza fra «costruito» e
«funziona». Il test lo sorveglia e dice, nel proprio messaggio, che il giorno in
cui qualcuno aziona il `Watcher` quel test va **riscritto, non cancellato**.

## 6. La misura: la catena vera, contro il microfono vero

Impostazioni vere, modello vero, dispositivo vero. `voice.enabled` acceso **solo
in memoria**: `~/.config/jarvis-os/settings.toml` non è stato toccato. T1
sostituito, così non si spawna `claude`.

```
composizione: 292 ms
microfono   : aperto
stt         : vosk  primario=False        (chiave assente)
tts         : edge  primario=False        (chiave assente)
modello condiviso: True
  t+1s … t+6s  microfono = aperto
caduta      : None
dopo lo spegnimento: chiuso
```

E i due annunci di ripiego, invariante 12:

```
ripiego_annunciato  'Signore, non trovo la chiave del servizio vocale. Ascolto in locale con vosk.'
ripiego_annunciato  'Signore, non trovo la chiave del servizio vocale. Parlo con la voce di ripiego.'
ingresso_audio      byte=640 ms=20 rate=16000
```

**Due righe, non quattro** — è la correzione 8. E in sei secondi di rumore
ambientale **nessun falso trigger** del wake.

### Una cosa che ho verificato perché poteva rompere ogni turno

`_trascrivi()` apre un **secondo** `pw-record` mentre il ciclo principale tiene
il primo. Se due catture non convivessero, ogni turno «jarvis + frase libera»
fallirebbe. Misurato:

```
primo : 63454 byte in 2,0 s      secondo: 63454 byte in 2,0 s      OK
```

Convivono. Resta il fatto che durante un turno il microfono è aperto due volte:
lo dichiaro, non l'ho cambiato — unificarli è un cambio di struttura, non una
riparazione.

## 7. Le prove, e che bocciano

| file | |
|---|---|
| `tests/test_grado_voce.py` | **15** — composizione, wake dalle impostazioni, modello condiviso, ripiego annunciato, spegnimento, `annuncia`, turno al Governor, i quattro stati del microfono, le news |
| `tests/test_microfono_non_muore_in_silenzio.py` | **4** — il ciclo sopravvive a un turno caduto, l'annullamento passa, i blocchi dello STT sono esatti, il rate si passa |

**Ritirata una correzione per volta, ognuna diventa rossa:**

| correzione ritirata | esito |
|---|---|
| `add_done_callback` | 1 rosso |
| il `try` attorno a `_su_trigger` | 1 rosso |
| `dal_microfono` nella trascrizione | **2** rossi |
| lo snapshot delle news | 1 rosso |
| lo spegnimento che non rilancia | 1 rosso |
| il callback che duplicava l'annuncio | 1 rosso |

Nessuna delle sei è vera per assenza del fenomeno (§11.7 regola 4).

| | |
|---|---|
| `uv run pytest -q` | **710 passed** (erano 700) |
| composizione vera | 292 ms, microfono aperto 6 s |
| sorgenti UI toccate | **nessuna** — i cancelli visivi non possono essere cambiati |

## 8. Che cosa succede quando accende l'interruttore

Con `voice.enabled = true` e le impostazioni di oggi:

1. parte un processo `claude` (`claude-haiku-4-5-20251001`) da
   `voice-cwd`, vuota e dedicata;
2. si carica il modello Vosk italiano — 284 ms — e lo **stesso oggetto** serve
   sia il wake sia lo STT;
3. il microfono si apre a 16 kHz, blocchi da 20 ms;
4. due annunci di ripiego finiscono **nei log**: ascolto locale con Vosk, voce
   di ripiego EdgeTTS;
5. le quattro frasi attive sono `jarvis`, `papa e a casa`, `jarvis buonanotte`,
   `jarvis silenzio`.

⚠️ **La voce con cui JARVIS risponde è EdgeTTS, cioè un servizio di rete
Microsoft.** L'ascolto è locale e l'audio senza frase nota non lascia la
macchina (§18.3), ma **ciò che JARVIS dice viene sintetizzato fuori**. Con la
chiave Deepgram assente questo è lo stato normale, non l'eccezione.

## 9. Dichiarato aperto

1. **Il riconoscimento resta non provato.** Nessun sintetizzatore locale su
   questa macchina, e nessun parlato registrato. È esattamente ciò che la Sua
   prova col microfono verificherà, e per questo non lo do per verde.
2. **Invariante 12, una domanda vera.** «Il fallback va sempre ANNUNCIATO, mai
   silenzioso»: oggi l'annuncio è **una riga di log**. Se non sta guardando il
   terminale, non lo sente e non lo vede. Il metodo per dirlo a voce esiste
   (`VoicePipeline.annuncia`), ed è già quello che usano §5.6 e ADR-003.
   **Non l'ho collegato da solo**: farebbe parlare JARVIS a ogni avvio e
   manderebbe la frase a Microsoft ogni volta. La decisione è Sua.
3. **Durante un turno il microfono è aperto due volte** (§6). Misurato
   funzionante, non unificato.
4. **Le news non girano** (§5), e non gireranno finché qualcuno non aziona il
   `Watcher`.
5. **`core/tools/model3d.py` è vuoto** — zero byte. È territorio di una fase
   futura, fuori dal percorso vocale, e non l'ho toccato.
6. **`docs/acceptance/CATALOGO-SCORRIMENTO.json` viene riscritto da ogni
   esecuzione della suite**: i numeri d'inerzia dipendono dal carico. Dopo un
   giro di test l'albero non è mai pulito, e una regressione vera in quel file
   si nasconderebbe fra il rumore. L'ho **riportato allo stato committato** —
   la mia esecuzione non è più vera della precedente — e non l'ho corretto.
7. **`ruff` non è installato**: nessun lint è stato eseguito. Non è una
   dipendenza che aggiungo da solo.
8. **`settings.toml` ha permessi larghi** (`atteso=0600`). Il core lo dice a
   ogni avvio. È fuori dal repo ed è Sua configurazione: non l'ho cambiato.
9. **`shots/scrivania/` è ancora su disco** e dà ancora la misura vecchia. La
   rimozione è stata negata e non l'ho aggirata.
