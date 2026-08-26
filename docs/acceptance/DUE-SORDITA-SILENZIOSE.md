# Due sordità silenziose — il microfono che mentiva e la scrivania che non tornava

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §16, §3.2
**Rollback**: `590a104` · **Test**: 1401 → **1412**

---

## Che cosa è successo, in una sessione sola

**Il ciclo del microfono è rimasto fermo un'ora.** Il core girava — telemetria,
news, tutto vivo, 6 tick di CPU in 3 secondi — e `pw-record` era bloccato in
**`anon_pipe_write`**: la pipe piena perché **nessuno leggeva**. Per tutta
quell'ora lo snapshot ha detto:

```
microfono: aperto
```

Non era vero. Quel campo riportava che il **compito** era vivo, non che l'audio
arrivasse. L'unico modo in cui il guasto è emerso è stato qualcuno che ha detto
«non mi sente».

Il microfono era sano: un secondo lettore ha preso **148 blocchi in 3 secondi**.

**E la scrivania è rimasta scollegata dodici minuti** dopo un riavvio del core:
finestra viva, pannello vuoto, e il diario che intanto si riempiva su disco. Due
strade per lo stesso dato, e una interrotta in silenzio.

Sono la stessa famiglia: **uno stato riferito che non è lo stato vero.**

---

## Il battito del microfono

`VoicePipeline` timbra ogni blocco. `muto_da()` dice da quanti secondi non ne
arriva uno, e lo snapshot smette di chiamarlo «aperto»:

```
microfono: muto da 42 s
```

**La soglia si deriva.** I blocchi arrivano ogni **20 ms**: cinque secondi sono
**duecentocinquanta blocchi mancati**, cioè «rotto», non «la macchina è
occupata».

⚠️ **E il conto non scorre durante un turno.** Il ciclo non legge mentre serve
un turno — `_su_trigger` è atteso dentro il `async for` — e un turno può durare
fino al timeout di T1. Senza quella bandiera il battito griderebbe al lupo a
ogni conversazione, e un allarme che grida al lupo si spegne.

La bandiera si abbassa in un `finally`: una bandiera che resta alzata renderebbe
il battito cieco per sempre, cioè **lo stesso difetto con un nome nuovo**.

E la soglia **annuncia**, sul cambio e nei due versi, come la VRAM e la ripresa
del Governor. §16 lo chiede a ogni soglia, e questa non c'era: l'ora di sordità
è passata senza una riga.

## Il ponte che non riprovava

`riprova()` programma `collega()` con un timer. Se il socket non esiste
nell'istante del tentativo — **esattamente la finestra in cui il core si
riavvia** — `new WebSocket` solleva in modo sincrono, l'eccezione esce dal
callback del timer, e **nessuno programma il tentativo successivo**.

Un `try/catch` che richiama `riprova()`. Il ritardo non ha un tetto ai
tentativi, e un test lo impone: un tetto trasformerebbe un riavvio lungo in una
scrivania morta.

**Verificato nel comportamento**, non solo nel test: core riavviato con la
finestra aperta →

```
22:54:06  core_avviato
22:54:06  client_connesso  totale=1
```

---

## Un'ipotesi mia che non reggeva, e come l'ho scoperta

Ho scritto il `try/catch`, l'ho testato, e ho dichiarato che funzionava. **Non
avevo verificato niente**: `pgrep -f "electron..."` pescava la **mia stessa riga
di comando** — terza volta in questo progetto — e non c'era nessun Electron
acceso. La finestra che credevo viva non esisteva, e il mio `nohup` non era
sopravvissuto alla chiamata.

L'ho scoperto perché la scrivania *continuava* a non ricollegarsi dopo la
correzione. Il difetto era reale e la correzione giusta; la **prova** era falsa.

---

## Verifica

### ✅ Le quattro bocciature

| perturbazione | esito |
|---|---|
| «muto» torna a chiamarsi «aperto» | 1 rosso |
| la soglia non annuncia più | 1 rosso |
| il costruttore esce dal `try` | 1 rosso |
| la bandiera del turno non si abbassa | 1 rosso |

### ⚠️ Un togli-commenti, e perché è servito

**Quattro volte in questa sessione** un mio test ha letto un commento invece del
codice: `esegui_t0` nominato in un docstring che spiega perché non ci passa,
`self._vad` idem, `&#8862;` scambiato per un colore, e `new WebSocket` dentro la
spiegazione del difetto scritta sopra la riga vera.

Adesso c'è `senza_commenti()`, e i test che ispezionano un sorgente ci passano.
Un test che legge un sorgente deve leggere il **codice**.

### ✅ La suite

`1401 → 1412`, verde.

### ❌ NON verificato

- **La causa dell'ora di sordità.** `pw-record` bloccato in scrittura e il
  ciclo fermo sono *misurati*; **dove** fosse bloccato il ciclo no. `py-spy`
  non è installato e non aggiungo dipendenze senza chiedere. Il riavvio ha
  risolto, quindi la causa resta **ignota** — e il battito serve proprio a
  renderla osservabile la prossima volta invece di dedurla.
- **Il pannello che riceve `agent.diario` dal socket vivo.** Il diario si
  riempie su disco, verificato; che le righe compaiano nel pannello mentre si
  parla non è ancora stato guardato da nessuno.
