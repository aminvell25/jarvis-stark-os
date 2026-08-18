# Fase 3 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 3
**Test**: 184 verdi (erano 156) · **Precedente**: `FASE-02.md`

JARVIS parla e ascolta. Due dei quattro criteri sono rispettati con ampio
margine, **uno non è raggiungibile** e il quarto lo è solo in parte — e la
ragione del primo è una misura che contraddice la specifica.

---

## I quattro criteri di §22

### 1. «*papà è a casa* esegue in ~30 ms **offline**» — ✅ VERIFICATO

Frase sintetizzata con `edge-tts`, PCM a 16 kHz dato in pasto a `PhraseWake`
come lo darebbe `pw-record`:

| | |
|---|---|
| riconoscimento | **3,55 ms** |
| calcolo su tutto il flusso (2,18 s di audio) | 26,8 ms |
| **costo dell'ascolto continuo** | **12,3 ms di CPU per secondo di audio** — l'1,2 % di un core |
| caricamento del modello | 262 ms, una volta sola all'avvio |

§7.2 diceva «CPU trascurabile»: ora è misurato. E il percorso è davvero
**offline** — Vosk gira in locale e la frase porta la propria azione, senza STT,
senza LLM, senza rete.

⚠️ **Quello che questa prova NON dimostra**: la precisione sulla Sua voce, nella
Sua stanza, col Suo microfono. §24 punto 3 lo dichiara già e chiede almeno 20
ripetizioni Sue. Io ho provato il *percorso*, non la Sua pronuncia.

### 2. «conversazione col primo suono entro ~1 s» — ❌ **NON RAGGIUNGIBILE**

Misurato, e i due addendi sono entrambi sopra il previsto:

| | misurato | atteso |
|---|---|---|
| primo token di T1, sessione **calda** | **3,2 – 4,4 s** | 300–900 ms (§24 p. 2) |
| primo PCM da `edge-tts` | 503 – 655 ms | — |
| **primo suono** | **~4,4 s** | **~1 s** |

§24 punto 2 lasciava aperto proprio questo numero — «*quello che conta
davvero*» — e dichiarava che **oltre 1500 ms il vantaggio del design va
rivalutato**. La misura è tre volte quella soglia.

**La persistenza funziona**: a freddo ~5,6 s, a caldo ~3,7 s, cioè **1,1 s
risparmiati** e misurati. Ma il resto non è avvio di processo: è il viaggio
verso il modello, e non è sotto il nostro controllo.

§5.2 sospettava che Haiku 4.5 non esponesse i livelli di effort. **Confermato**:

| configurazione | mediana |
|---|---|
| come da §5.2 | 3206 ms |
| `--effort low` | 3608 ms |
| `--effort none` | 3370 ms |

Nessuna differenza fuori dal rumore. `scripts/bench_t1.py` rimisura e segnala
da sé lo sforamento, perché **questo numero va rimisurato, non ricordato**.

### 3. «staccando la rete il fallback si attiva e viene annunciato» — ⚠️ PARZIALE

**Verificato**: senza chiave il sistema parte in ripiego e **lo annuncia**,
a voce, dagli altoparlanti — *«Signore, non trovo la chiave del servizio
vocale. Parlo con la voce di ripiego.»* Verificata anche la scelta su errore
del primario, con provider che falliscono a comando.

**Non verificato**: il ramo Deepgram. La chiave non c'è
(`~/.config/jarvis-os/secrets.toml` non esiste), quindi `stt_deepgram.py` e
`tts_deepgram.py` **non sono mai stati eseguiti contro il servizio vero**. Sono
scritti secondo §7.3 e verificati solo nella forma — URL, intestazioni, parsing
degli eventi — e lo dichiarano nel proprio docstring.

⚠️ **E c'è di più, per lo scostamento R26**: con `edge-tts` come ripiego, a rete
staccata **cadono entrambi i provider**. Vedi sotto.

### 4. «barge-in entro 200 ms» — ✅ VERIFICATO CON AMPIO MARGINE

Cinque giri, riproduzione in corso interrotta a metà:

| | |
|---|---|
| mediana | **1,4 ms** |
| massimo | **1,9 ms** |
| criterio | 200 ms |

**Cento volte sotto**, e la ragione è la scelta di R25: il barge-in è una
`kill()` del processo di riproduzione, non un flag controllato in un ciclo. Il
kernel lo fa in microsecondi e senza che il nostro codice collabori.

---

## Scostamenti dalla specifica, dichiarati

| # | Cosa | Decisione |
|---|---|---|
| **R25** | §23 propone `sounddevice`, che richiede PortAudio (non installato, servirebbe `sudo`) | **PipeWire** via `pw-record`/`pw-play`. Zero dipendenze nuove, e il barge-in diventa una `kill()` |
| **R26** | §4 e l'invariante 12 prevedono **Kokoro** offline; su Sua indicazione il ripiego TTS è **Edge streaming** | Fatto, e **`edge-stt` non esiste**: lo STT di ripiego è **Vosk**, già caricato per il wake — zero download in più e resta offline |
| **R27** | §7.4 dice «chunker solo davanti a Kokoro» | La regola diventa *«davanti al TTS a enunciato, mai davanti a Flux»*. Il provider lo dichiara in `per_enunciato`, e un test verifica che la pipeline lo rispetti |
| **R28** | §7.1 indica **Silero VAD** | Gate a energia con isteresi: stesso mestiere, nessun modello da scaricare. Sta dietro la stessa interfaccia |
| **R30** | §7.3 indica `faster-whisper base` come STT di ripiego | **Vosk**, per la ragione di R26 |

### ⚠️ Lo scostamento che cambia il significato di un invariante

L'invariante 12 dice che il ripiego scatta anche su *«rete assente»*, e §16
elenca `offline` fra gli stati funzionanti. **Con `edge-tts`, senza rete JARVIS
resta muto.**

Cosa continua a funzionare senza rete: wake a frasi, T0, file, telemetria — e
*«papà è a casa»* esegue lo stesso, perché quel percorso non tocca né rete né
modelli remoti. **Si perde la voce.**

L'annuncio di degradazione che §12 impone diventa allora **visivo**: §16 prevede
già «ambra + indicatore a schermo», e la finestra esiste dalla Fase 1b. Il
cablaggio di quell'indicatore è **da fare**.

---

## Le garanzie strutturali di questa fase

| Garanzia | Dove è imposta |
|---|---|
| un ripiego **non si costruisce** senza la frase che lo annuncia (inv. 12) | `providers/health.py::Scelta.__post_init__` |
| il chunker va solo davanti al TTS a enunciato | il provider dichiara `per_enunciato`; un test confronta i due percorsi |
| `search_files` resta l'ultima regola T0 | `t0_corpus.py`, con il messaggio che spiega perché |
| T1 non ha tool nel contesto (inv. 15) | `--allowedTools ""`, verificato in `test_voce.py` |

---

## Scoperte durante l'implementazione

**Il modello Vosk si scarica da sé.** `Model(lang="it")` → `~/.cache/vosk/`:
47 MB in tre secondi, **nessun `curl`**. Era il blocco che sembrava richiedere
un intervento Suo, e non c'era. L'ho scoperto consultando la documentazione via
Context7 invece di assumere.

**Il corpus T0 ha trovato sette buchi al primo giro.** Le regex di §7.6 sono
schizzi che non coprono gli articoli italiani: *«apri le news»*, *«mostra gli
agenti»*, *«stato del sistema»* non venivano riconosciute. Non è pignoleria
linguistica — sono le forme in cui una persona parla davvero.

**E ho verificato che il corpus colga una regola avida**, inserendone una di
prova: *«raccontami una cosa interessante»* veniva rubata a T1. È il guasto
silenzioso che quelle 20 frasi conversazionali esistono per sorvegliare —
JARVIS risponderebbe con un'azione invece che con una frase.

**Ho committato una volta con la suite rotta.** `test_platform.py` importava
ancora `LinuxAudioIO` dalla vecchia posizione dopo lo spostamento in
`linux_audio.py`. Il punto 1 della «definizione di fatto» lo vieta: corretto e
commit emendato prima di riferire.

---

## ❌ NON VERIFICATO — l'elenco completo

1. **Il ramo Deepgram**, per assenza della chiave. Codice scritto secondo §7.3,
   mai eseguito contro il servizio.
2. **La precisione del wake sulla Sua voce** — §24 punto 3, richiede 20
   ripetizioni Sue.
3. **La cattura dal microfono vero.** Su Sua indicazione la verifica è avvenuta
   per sintesi. `pw-record` è implementato e il suo argv è testato, ma non è
   mai stato eseguito.
4. **L'indicatore visivo di degradazione** quando manca la rete (conseguenza di
   R26): la finestra esiste, il cablaggio no.
5. **Il turno completo end-to-end** microfono → wake → STT → T1 → voce, che
   richiede i punti 2 e 3.

## Riepilogo

| | |
|---|---|
| Test | **184 verdi** (erano 156) |
| Criteri §22 Fase 3 | **2 su 4 pieni** · 1 parziale · **1 non raggiungibile** |
| Misura che contraddice la specifica | primo token T1: **3,7 s** contro i 900 ms attesi, oltre la soglia di riesame di §24 |
| Decisione che spetta a Lei | §24 punto 2 chiede di rivalutare il design a questa soglia |
