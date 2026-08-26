# I tre orfani veri — e uno dei tre non era quello che sembrava

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §9, §14, §16 · **Rollback**: `ac75829`
**Test**: 1320 verdi (erano 1304) · **Orfani residui**: 11 → **7**

---

## ① `Governor.riprendi` — la ripresa era muta

**Il difetto non era quello che il nome suggerisce.** La sospensione **scadeva
da sola**: `sospeso` è un confronto sull'orologio, quindi T2 tornava a
funzionare comunque. Per questo l'orfano era invisibile: la funzione mancante
non rompeva niente di *funzionale*.

Rompeva §16, che dice «**nessuna soglia agisce senza annunciarlo**». La
degradazione si annunciava — «T2 sospeso, riprova fra 900 s» — e il seguito non
arrivava mai.

> Un'asimmetria fra il dire che qualcosa è rotto e il dire che è tornato a
> posto è **peggio del silenzio su entrambi**: la prima metà insegna a fidarsi
> degli advisory, la seconda tradisce quella fiducia.

Il controllo sta in `stato()` — che lo snapshot chiama a 2,5 Hz, quindi
l'annuncio arriva entro mezzo secondo — **e** in `puo_spawnare()`, perché un
core senza scrivania collegata non chiama `stato()` e la ripresa resterebbe
muta fino a un momento che non arriva mai.

È idempotente: `riprendi()` azzera `_sospeso_fino`, quindi venti chiamate
producono **un** advisory. Ha un test.

---

## ② `GpuScheduler.can_admit` — il verbo «rifiuta» non ha un oggetto

§16, riga VRAM: «headroom insufficiente → **rifiuta** il caricamento (§9)».

⚠️ **Nel core non si carica niente sulla GPU, e va detto invece di fingere.**
L'invariante 11 vieta i modelli LLM locali; §9 elenca Vosk (~50 MB, CPU),
Kokoro (CPU), MediaPipe (`delegate=CPU` obbligatorio) e Tesseract (CPU). Non
c'è `faster-whisper` nel codice. L'unico consumatore vero è la **scena
three.js + Pixi**, che §9 chiama «il consumatore principale» — e che vive nel
renderer, dove il core non può rifiutare niente.

Inventare un chiamante per far sembrare la regola applicata sarebbe stato
peggio dell'orfano. Ciò che il core **può** fare, e che §16 chiede a *ogni*
soglia, è annunciare: «ogni soglia emette su `agent.advisory`». Quindi la
regola si applica per intero — misura, confronto, advisory — e manca solo il
verbo.

**La soglia viene da §9, non da me**: la scena è stimata «~1–2 GB (stima
prudenziale)», e si prende il **limite inferiore**. Sopra 1 GiB la scena
potrebbe già essere stretta e non si dice niente; sotto, non ci sta di sicuro.
Un avviso che grida al lupo viene ignorato — è il guasto che §15 e §16 esistono
entrambe per evitare.

E **si emette sul cambio, in entrambi i versi**: è la lezione di ① applicata
nello stesso turno.

Misurato su questa macchina: headroom **7655 MiB** (unificata, RAM 18342 MiB),
`can_admit(1 GiB)` concesso. L'advisory non scatta, ed è corretto che non
scatti.

---

## ③ `gestures.emetti` — la catena non aveva un capo

Il suo docstring dice «**l'unica uscita delle gesture verso il resto del
sistema**», e nessuno la chiamava. Tracker MediaPipe, riconoscitore dei quattro
gesti di §14, isteresi a cinque fotogrammi: tutto scritto, tutto misurato sul
corpus, **mai congiunto**. Una mano davanti alla telecamera non poteva produrre
niente, perché la telecamera non si apriva mai.

Adesso c'è un grado, con la stessa forma della voce e delle news:

- si accende **solo** con `vision.enabled = true`, che parte **falso** —
  `settings.toml` lo dice bene: «il consenso migliore è non accenderla»;
- MediaPipe assente è uno **stato normale annunciato**, non un guasto: stessa
  forma di Tesseract in §12;
- una telecamera che si stacca emette un advisory e **non porta via il core**.

### Il fotogramma non esce dal thread

`fotogrammi()` è un iteratore **sincrono** che legge dalla telecamera: girarlo
sul loop bloccherebbe il core fra un fotogramma e l'altro. Sta in un thread, e
ciò che attraversa il confine è **solo il nome del gesto** — la stessa forma
del ricarico a caldo delle frasi di wake.

Non è solo prestazioni: §18.3 dice che l'audio senza frase nota non lascia mai
la macchina, e per le immagini vale a maggior ragione. Il modo più solido di
garantirlo è che il pixel non arrivi nemmeno al loop.

### E passa da `emetti`, non da `esegui_t0`

Non è una svista. `emetti()` usa `registry.invoke_da_gesture()`, fail-closed
sull'invariante 27: rifiuta tutto ciò che non è dichiarato `gesture_allowed`.
Farla passare dalla strada della voce vorrebbe dire che **una mano può fare ciò
che una frase può fare**, e §14 dice il contrario.

---

## Verifica

### ✅ Le tre bocciature

| perturbazione | esito |
|---|---|
| tolto il controllo della ripresa da `stato()` | 2 rossi |
| advisory VRAM a ogni giro invece che sul cambio | 2 rossi |
| gesture instradate su `esegui_t0` invece che su `emetti` | 2 rossi |

Ogni perturbazione con un `assert` sulla stringa prima di sostituire, e
annullata con copie in scratch.

### ✅ Il giro dal fotogramma all'intento

Provato con un tracker finto: cinque fotogrammi identici di palmo aperto
producono **un** `espandi_pannello`, non cinque — l'isteresi di §14.

⚠️ Il primo finto dava `sposta_pannello`: pollice e indice erano nello stesso
punto, quindi `pizzico()` era vero e vince sull'ordine. **Una mano finta va
costruita guardando le soglie, non a occhio** — ed è la stessa lezione delle
misure di questi giorni, applicata a un fixture.

### ✅ La suite

`1320 passed` (erano 1304). Orfani da 11 a **7**, e i sette restanti sono
callback di libreria (`on_any_event`), metodi chiamati per attributo
(`R.pianifica`), classi di protocollo (`TTSProvider`) o eccezioni dichiarate
(`ConfermaNonCollegata`).

### ❌ NON verificato

- **Una mano vera.** È il punto 1 dei NON VERIFICATI di Fase 7, e resta:
  `vision.enabled = false`, e la telecamera non è stata aperta in questo turno.
- **Un rate limit vero.** La sospensione è provata con `sospendi()` chiamata a
  mano; un `api_retry` reale da Claude Code no.
- **La VRAM sotto la soglia su questa macchina.** L'advisory è provato con una
  `GpuMemory` finta: qui l'headroom è 7,5 GiB e non scenderà sotto 1 GiB senza
  qualcuno che carichi qualcosa — che è precisamente il punto ②.
- **L'effetto delle gesture sulla scrivania.** `gesture.intent` finisce sul
  socket; che il renderer lo raccolga e sposti un pannello non è misurato qui.
