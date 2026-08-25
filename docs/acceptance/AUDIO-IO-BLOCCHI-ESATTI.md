# `read(n)` non dà `n` byte — e mezza catena vocale non lo sapeva

**Rollback:** `66543ef`
**Criterio:** `core/voice/audio_io.py` esiste e la catena vocale riceve blocchi
della dimensione che dichiara.
**Esito: SODDISFATTO. E PortAudio non serviva — quel blocco l'avevo riferito
male.**

---

## 1. Correzione a quel che avevo detto

`T0-E-IL-MICROFONO.md` elencava **PortAudio assente** fra le quattro cose
mancanti, e diceva che l'installazione toccava a Lei. **È sbagliato.**

`core/platform/linux_audio.py` esiste da prima, e in cima dichiara lo
scostamento:

> ⚠️ SCOSTAMENTO DICHIARATO da §23, che propone `sounddevice`. `sounddevice`
> richiede **PortAudio**, che non è installato e la cui installazione richiede
> privilegi di amministratore. `pw-record` e `pw-play` ci sono già.

Il progetto aveva già preso quella decisione, con la stessa ragione che avevo
appena riscoperto, e io ho letto `sounddevice: OSError` senza guardare se
qualcuno lo usasse. Nessuno lo usa. `pw-record` e `pw-play` sono **presenti** e
`core.platform.audio()` li compone già.

Il difetto della mia diagnosi è quello che questo progetto chiama per nome da
due giorni: **ho misurato una cosa vera e l'ho attribuita alla domanda
sbagliata.**

## 2. Il difetto vero, misurato sul microfono di questa macchina

`linux_audio.py` legge così:

```python
blocco = await proc.stdout.read(BLOCCO)
```

`asyncio.StreamReader.read(n)` restituisce **fino a** `n` byte. Quaranta letture
da 640 byte contro il microfono vero:

```
640 byte  19 volte      42 byte  13 volte
 44 byte   6 volte      24 byte   1 volta      626 byte  1 volta
```

**Ventuno su quaranta erano corti**, e un blocco da 42 byte è **1,3 ms di
audio**. Chi lo riceve non se ne accorge e non può accorgersene:

- `VAD.parla()` calcola l'energia **media** del blocco. Su 1,3 ms quel numero
  non significa niente: una consonante occlusiva ci sta dentro intera, la
  vocale che segue no.
- `PhraseWake.feed()` passa i byte a Vosk, e un blocco di lunghezza **dispari**
  spezza un campione s16 fra due chiamate.
- La latenza del wake per blocco diventa incomparabile: 0,022 ms su 42 byte e
  0,022 ms su 640 non sono la stessa misura.

Nessuno di questi guasti solleva. Sono tutti della specie che questo progetto ha
imparato a temere: **un numero plausibile che non significa niente.**

## 3. Che cosa fa `audio_io.py`

Riallinea un `AsyncIterator[bytes]` in blocchi di **esattamente** 20 ms, e
niente altro.

```
byte_per_blocco(rate, ms, canali)   l'aritmetica, in un posto solo
a_blocchi(sorgente, byte)           il riallineamento
da_pcm(dati, byte)                  una sorgente per le prove, senza microfono
dal_microfono(audio, rate)          compone core.platform.audio() col riallineamento
```

**Sta in `core/voice/` e non in `core/platform/`**, e non è un'eccezione
all'invariante 29: `pw-record` su Linux, WASAPI su Windows e un file su disco
hanno tutti e tre lo stesso comportamento — un flusso di byte senza promesse
sulla granularità — e la risposta è la stessa per tutti e tre. Qui non si apre
nessun dispositivo.

### La coda si riempie di silenzio, non si scarta

Alla fine di un flusso resta quasi sempre un avanzo più corto di un blocco.
Scartarlo perderebbe fino a 20 ms, e 20 ms in fondo a «papà è a casa» sono
l'ultima sillaba: il wake sentirebbe «papà è a ca». Zero non è un segnaposto —
è ciò che c'era davvero dopo l'ultimo campione, cioè niente.

Da un microfono il flusso non finisce mai, quindi la coda non esiste: è il caso
del file a farla comparire, ed è l'unico in cui la scelta si vede.

## 4. La misura

Catena vera — `VAD` e `PhraseWake` col modello Vosk scaricato — alimentata con
la granularità **misurata**, non con un flusso ordinato:

| | blocchi | dimensioni |
|---|---|---|
| senza riallineamento | 406 | 24, 32, 42, 44, 626, 640 |
| con riallineamento | **200** | **640** |

`250 blocchi su 406 non erano della misura.`

⚠️ **Sul mio segnale di prova il VAD decide uguale in entrambi i casi**, e non
lo nascondo: il rumore uniforme che ho generato ha la stessa energia media su
1,3 ms e su 20 ms, quindi non può mostrare quel guasto. Il parlato vero ha
struttura — occlusive, pause — e lì la differenza esiste. **È ragionata, non
misurata**, e resta così finché non c'è del parlato vero da dare in pasto.

Quello che è misurato è l'irregolarità, ed è quella che è stata corretta.

## 5. La pipeline adesso la usa

`VoicePipeline.run()` leggeva `self._audio.input_stream()` diretto. Adesso legge
`dal_microfono(self._audio, self._rate)`. Senza questa riga il modulo sarebbe
stato una libreria che nessuno chiama — cioè la stessa cosa del file vuoto di
prima, con più righe.

## 6. Le prove

`tests/test_audio_io.py`, 18 asserzioni, e `GRANULARITA_MISURATA` è la
distribuzione vera del microfono, non un caso inventato:

| | |
|---|---|
| la granularità vera diventa regolare | 640 su tutti |
| non si perde un campione | i byte che entrano escono, la coda è silenzio |
| un flusso già regolare passa **intatto** | la metà che conta di più: non rompere il caso buono |
| una lunghezza **dispari** non spezza un campione | s16, due byte |
| i pezzi vuoti non producono blocchi vuoti | `read()` torna `b""` a fine flusso |
| l'aritmetica rifiuta l'impossibile | un blocco da zero byte è un ciclo che non finisce |

Provato che bocciano: tolto il riallineamento, **6 rossi su 18**.

## 7. Verifica

| | |
|---|---|
| `tests/test_audio_io.py` | **18 passed** |
| `uv run pytest -q` | **691 passed** |
| `pw-record`, `pw-play` | presenti |
| `PhraseWake` sul modello vero | costruito, 200 blocchi, nessun falso trigger |

## 8. Dichiarato aperto

- **Il riconoscimento resta non provato.** Serve del parlato vero: il microfono
  (adesso raggiungibile — manca solo `voice.enabled` e qualcuno che parli)
  oppure `edge-tts`, che è di rete.
  ✅ **SUPERATO il 25 ago 2026** — vedi `IL-GIRO-SI-CHIUDE.md`: «papà è a casa»,
  detto da un umano, ha aperto la scena. 24 trigger veri, mediana 7,76 ms.
- **L'effetto dei blocchi corti sul VAD è ragionato, non misurato**, per la
  ragione in §4.
- **`faster_whisper` resta assente**, ed è l'unica strada STT senza chiave
  Deepgram. Non è nel percorso del wake: il wake è Vosk, ed è locale
  (invariante 13).
- **`BLOCCO = 1024` in `linux_audio.py` è 32 ms**, e i blocchi della catena sono
  20. I due numeri non devono coincidere — è proprio per questo che il
  riallineamento esiste — ma il commento di quella costante dice «abbastanza
  corto da non aggiungere latenza percepibile al gate VAD», e adesso il gate
  vede blocchi da 20 ms comunque. Non l'ho toccato.
