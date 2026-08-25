# L'annuncio si sente — e per sentirlo servivano cinque correzioni

**Rollback:** `c382d13`
**Richiesta:** «Accendi `voice.enabled` e collega l'annuncio a voce».
**Esito: `voice.enabled = true`, e l'annuncio si SENTE. Collegarlo ha scoperto
cinque difetti veri, uno dei quali rendeva JARVIS incapace di finire una
frase. Tutti misurati, tutti corretti, tutti con una prova che boccia.**

---

## 1. L'interruttore

Una riga sola in `~/.config/jarvis-os/settings.toml`, e il file lo dice da sé:

```diff
 # ⚠️ Con `true` il core apre il MICROFONO all'avvio e spawna un processo
 # `claude` persistente (§5.2). Parte spento di proposito: si accende qui.
-enabled = false
+enabled = true
```

Copia dello stato precedente in `/tmp/settings.toml.prima`.

## 2. Il collegamento, e le tre reti che gli servono

L'invariante 12 dice «il fallback va sempre **ANNUNCIATO**, mai silenzioso», e
fino a ieri l'annuncio era una riga di log: se nessuno guarda il terminale, non
è un annuncio, è un annuncio archiviato. Adesso la frase passa da
`VoicePipeline.annuncia()` — la stessa via di §5.6 e ADR-003 — che non tocca
nessun modello: se dipendesse da Claude, l'annuncio che Claude non risponde
sarebbe la prima cosa a non funzionare.

Tre precauzioni, e nessuna è ornamentale:

| | perché |
|---|---|
| **non si aspetta** | `annuncia_ripieghi()` gira all'inizio di `run()`, **fuori** dalla rete che protegge i turni. Se parlare sollevasse lì, `run()` finirebbe e il microfono non si aprirebbe mai: collegare l'annuncio del ripiego chiuderebbe l'ascolto |
| **un tetto di 30 s** | EdgeTTS è di rete. Una rete che accetta e non risponde terrebbe la voce occupata per sempre, e ogni annuncio dopo si accoderebbe dietro a un morto |
| **riferimenti forti** | `asyncio` tiene i task per **riferimento debole**: uno non referenziato può essere raccolto a metà frase, e l'annuncio sparirebbe senza errore — il guasto muto, proprio nel punto che esiste per non essere muto |

E i due chiamanti non sono simmetrici: `annuncia_ripieghi()` scrive già la
propria riga di log, `ClaudeT1` non ne scrive nessuna. Un parametro `registra`
lo dice, invece di lasciare che uno dei due sia sbagliato.

## 3. I cinque difetti che il collegamento ha scoperto

### 3.1 JARVIS non poteva finire una frase — e la causa era il convertitore

Le due frasi di ripiego morivano **prima del primo campione**: `barge_in` due
volte, `primo_suono_ms = 0,0` due volte.

Cercando perché, la misura sul microfono vero, stanza in quiete:

```
energia mediana 0,25772   p95 0,26899
soglia di apertura del gate 0,01200
blocchi giudicati PARLATO: 250/250 = 100,0 %
```

Ventuno volte sopra la soglia. Separando la componente continua:

```
media dei campioni (polarizzazione continua)  -8470,5  su 32768
RMS come lo calcolava VAD.energia              0,25856
RMS senza la continua                          0,00242
```

**`VAD.energia()` calcolava l'RMS senza togliere la media**, quindi misurava la
polarizzazione del convertitore invece del suono. Il suono vero di questa
stanza è 0,0024 — **sotto la soglia di chiusura**, esattamente come progettato.

Una causa sola, due guasti:

1. il gate non si chiudeva mai, quindi il barge-in scattava all'istante ogni
   volta che JARVIS apriva bocca;
2. Vosk veniva alimentato in continuazione, che è precisamente ciò che §7.1
   chiede a questo gate di **non** fare. Invisibile, perché Vosk scarta da sé
   l'audio che non contiene una frase nota.

Nessuno dei due sollevava. Togliere la media costa **+0,0126 ms** misurati
(0,0078 → 0,0203) su un blocco che dura 20 ms.

Dopo: `46/250 = 18,4 %`, mediana **0,00101**.

### 3.2 Il barge-in scattava contro il silenzio

Fra la richiesta al TTS e il primo campione passa il tempo della sintesi:
misurato con EdgeTTS su questa rete, **1161 ms**. In quella finestra
`_sta_parlando` era già vero e JARVIS non era ancora udibile, quindi il
barge-in poteva scattare contro il silenzio — e scattava.

Non c'è niente da interrompere finché non si sente niente: chi parla in quella
finestra non sta parlando *sopra* a JARVIS, sta solo parlando.

### 3.3 Dopo il primo barge-in, JARVIS restava muto per sempre

`EdgeTTS.interrupt()` alzava **solo una bandiera**, e la bandiera si legge fra
una lettura e l'altra del decodificatore. Quella lettura non torna.

Misurato su dispositivo vero: dopo il barge-in, `parla()` **non tornava più** —
appesa oltre i dieci secondi della prova, **col lucchetto della voce in mano**.
Da lì in poi ogni altra frase si accodava dietro a una che non finiva mai.

La regola giusta era già scritta venti file più in là, in
`LinuxAudio.interrupt()`:

> Uccidere il processo è più rapido e più affidabile di qualunque flag: non
> richiede che il ciclo di riproduzione collabori.

Valeva per l'altoparlante e non era stata applicata al decodificatore.

⚠️ **E si uccide senza aspettare.** Il primo tentativo faceva
`proc.kill(); await proc.wait()`, e andava in stallo: `stream()` gira in
un'altra corutina con una lettura pendente sullo stesso trasporto, e le due
attese si bloccano a vicenda. Misurato: `interrompi()` non tornava più.
La mietitura la fa il `finally` di `stream()`, che è il proprietario del
processo.

| | prima | dopo |
|---|---|---|
| `interrompi()` | non tornava | **2,6 ms** |
| `parla()` dopo il barge-in | appesa oltre 10 s | **169 ms** |

### 3.4 Due annunci parlavano insieme

`parla()` non aveva lucchetto. Misurato con due frasi concorrenti:

```
ordine all'altoparlante: A0 B0 A1 B1 A2 B2
```

I frammenti di due frasi alternati. E non è un caso limite: su questa macchina
i ripieghi annunciati all'avvio sono **due**, quindi è il caso normale. Sotto
c'era un secondo guasto più silenzioso: il `finally` della prima frase che
finisce spegne `_sta_parlando` mentre la seconda sta ancora parlando, e da lì
il barge-in non risponde più.

Il lucchetto sta in `parla()` e non nei chiamanti: «chi sta parlando» è una
proprietà della pipeline, e lasciarla ai chiamanti darebbe tante opinioni
quanti sono — il difetto dei tre ritagli e dei due orologi. Dopo:
`A0 A1 A2 B0 B1 B2`.

### 3.5 I test aprivano il microfono vero e chiamavano la rete

Collegando l'annuncio, `tests/test_grado_voce.py` è passato da **2 s a 62** —
due volte il tetto di 30 s — perché ogni caso chiamava EdgeTTS. E già prima
apriva `pw-record` a ogni test, cosa che si vedeva solo come un
`PytestUnraisableExceptionWarning` su un FileIO.

Una suite che tocca la rete non è una suite: è un'altra cosa che può fallire
per ragioni che non riguardano il codice.

Il fixture adesso sostituisce i **tre trasporti** — il processo `claude`, il
dispositivo audio, la rete di EdgeTTS — e **non** la logica che li sceglie:
`costruisci_stt` e `costruisci_tts` restano quelli veri, quindi i test sul
ripiego provano la decisione vera. Da 62 s a **2,7 s**.

## 4. La misura: JARVIS parla

Catena vera, modello vero, microfono e altoparlanti veri. T1 sostituito.

```
composizione 289 ms · microfono aperto
stt vosk (primario=False, chiave assente) · tts edge (primario=False)
ripiego_annunciato  'Signore, non trovo la chiave del servizio vocale. Ascolto in locale con vosk.'
ripiego_annunciato  'Signore, non trovo la chiave del servizio vocale. Parlo con la voce di ripiego.'
primo_suono_ms  ms=627          <- la PRIMA frase esce dall'altoparlante
riproduzione_interrotta · decodifica_interrotta · barge_in
turno_vocale  primo_suono_ms=626.6
primo_suono_ms  ms=4187         <- la SECONDA, in coda alla prima
turno_vocale  primo_suono_ms=4187.1
caduta: None · dopo lo spegnimento: chiuso
```

Prima di queste correzioni la stessa sequenza dava `primo_suono_ms = 0,0` due
volte: **nessun suono**.

## 5. Che cosa ho misurato e non ho cambiato

Le due frasi vengono troncate dal barge-in dopo circa tre secondi. Ho separato
le due cause possibili invece di attribuirle, sei secondi per lato:

| | mediana | p95 | **max** | blocchi sopra soglia |
|---|---|---|---|---|
| JARVIS zitto | 0,00058 | 0,00378 | **0,76418** | 1,7 % |
| JARVIS parla | 0,00116 | 0,00716 | **0,01249** | 1,0 % |

Soglia di apertura: **0,01200**.

Quindi, in ordine di importanza:

1. **A tagliare le frasi sono i transitori della stanza**, non l'eco: con
   JARVIS zitto il massimo è 0,764, sessanta volte la soglia. Il barge-in sta
   facendo il suo mestiere — §7.4 vuole che si possa interrompere JARVIS — ma
   **un blocco solo da 20 ms basta** ad aprirlo, quindi un colpo di tosse o un
   tasto tronca un annuncio.
2. **L'eco sfiora la soglia**: 0,01249 contro 0,01200, un margine del **4 %**.
   JARVIS può interrompere se stesso. È il quinto atterraggio nei centesimi di
   questo progetto, e stavolta in una grandezza fisica.

La correzione naturale — chiedere **N blocchi consecutivi** sopra soglia prima
di dichiarare il barge-in — respingerebbe sia il transitorio singolo sia
l'eco. Ma è un cambio a §7.4, non una riparazione, e il numero giusto si sceglie
ascoltando. **Non l'ho fatto da solo.**

## 6. Le prove

| file | |
|---|---|
| `tests/test_voce_barge_in.py` | **8** — la continua non è parlato, il parlato sopra la continua sì, la stanza misurata non apre il gate, `_sta_parlando` solo dopo il primo suono, `interrupt()` uccide, `interrupt()` non aspetta |
| `tests/test_grado_voce.py` | **18** — le tre nuove: la frase arriva all'altoparlante, una voce che non parte non chiude il microfono, T1 annuncia prima che la voce esista |
| `tests/test_microfono_non_muore_in_silenzio.py` | **5** — la nuova: due frasi non si intrecciano |

**Ritirata una correzione per volta:**

| correzione ritirata | esito |
|---|---|
| la media nell'energia del VAD | **2** rossi |
| `_sta_parlando` al primo suono | 1 rosso |
| `interrupt()` che uccide | 1 rosso |
| `interrupt()` che non aspetta | 1 rosso |
| il lucchetto della voce | 1 rosso |
| l'annuncio parlato | 1 rosso |
| il tetto e la rete attorno all'annuncio | 4 rossi |
| il log di T1 | 1 rosso |
| il `try` attorno a `_su_trigger` | 1 rosso |

⚠️ **Due miei test si reggevano sul difetto del VAD.** Il loro audio finto era
un valore costante — continua pura — e prima passava per parlato. Corretto il
dato, non la correzione: un dato di prova che si regge su un difetto sparisce
insieme al difetto.

| | |
|---|---|
| `uv run pytest -q` | **722 passed** (erano 710) |
| `tests/test_grado_voce.py` | da 62 s a **2,7 s**, senza rete e senza microfono |
| sorgenti UI toccate | **nessuna** |

## 7. Dichiarato aperto

1. **Il barge-in su un blocco solo** (§5). Misure allegate, decisione Sua.
2. **La voce di JARVIS è EdgeTTS, cioè rete Microsoft.** Adesso che l'annuncio
   è collegato, **ogni avvio senza chiave Deepgram manda due frasi fuori dalla
   macchina.** L'ascolto resta locale (§18.3): esce ciò che JARVIS dice, non
   ciò che sente.
3. **Il riconoscimento resta non provato.** È la Sua prova col microfono.
   ✅ **SUPERATO il 25 ago 2026** — vedi `IL-GIRO-SI-CHIUDE.md`: «papà è a
   casa», detto da un umano, ha aperto la scena. 24 trigger veri, mediana
   7,76 ms.
4. **`play()` genera un processo `pw-play` per ogni chunk** del TTS. Funziona e
   non l'ho toccato, ma fra un chunk e l'altro c'è il costo di uno spawn: se
   la voce suonerà a scatti, la causa è lì e non nella sintesi.
5. **La polarizzazione continua di -8470 resta nel segnale** che arriva a Vosk:
   il VAD adesso la ignora, il riconoscitore no. Non so se lo disturbi, e non
   l'ho misurato — servirebbe del parlato vero.
6. **Restano aperti i nove punti** di `PRIMA-DI-ACCENDERE-IL-MICROFONO.md`, fra
   cui le news che non girano e `settings.toml` con permessi larghi.
