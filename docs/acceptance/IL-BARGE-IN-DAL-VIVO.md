# ① riattraversato: la persona al microfono, e il barge-in che non era raggiungibile

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.4, §7.5, §16, invariante 12
**Rollback**: `6a7df60` · **Test**: 1370 → **1385**

---

## Sei difetti, e nessuno era visibile prima di parlare

È comparsa una chiave Deepgram, e con lei sono entrati in funzione due file che
portavano da mesi l'intestazione «⚠️ NON VERIFICATO». Quattro difetti stavano
lì dentro, invisibili **per la stessa ragione**: senza chiave quel codice non
girava, e ogni test girava contro il ripiego locale.

| | difetto | sintomo udito |
|---|---|---|
| 1 | endpoint `/v2/speak` | HTTP 400, **silenzio** |
| 2 | voce predefinita `aura-2-thalia-en` | italiano con accento inglese |
| 3 | nessuna uscita del ciclo su `Flushed` | il turno non finiva |
| 4 | nessuna uscita del ciclo su `Cleared` | **la sessione** non finiva |
| 5 | nessun ripiego a caldo del TTS | silenzio, senza annuncio |
| 6 | il barge-in non era raggiungibile | non si riusciva a interromperlo |

### 1 — «Flux» non è un TTS

L'API lo ha detto alla lettera:

> `Only flux models are supported on the /v2/speak endpoint. Please use the
> /v1/speak endpoint for Aura text-to-speech requests.`

E il catalogo lo conferma: `GET /v1/models` restituisce **solo** voci `aura-*`
fra i TTS, **nessuna** `flux`. Flux è il modello di *riconoscimento*. §7.4
chiamava «Flux» il TTS, e il nome era finito nel posto sbagliato dentro un file
che non aveva mai girato.

### 2 — La voce era inglese

`aura-2-thalia-en`, e `costruisci_tts` non la sovrascriveva. Corretta **prima**
di far parlare, o la misura sarebbe stata di una voce sbagliata per
costruzione. `aura-2-elio-it` scelta fra le nove italiane per i tratti che
Deepgram le attribuisce — *calm, professional, smooth, trustworthy* — che sono
le parole con cui §5.7 descrive JARVIS. Configurabile da `voice.tts_voce`:
quarta manopola resa viva in due turni.

### 3 e 4 — Il ciclo che non usciva

Aura manda l'audio e poi `Flushed`, **ma non chiude il socket**:
`async for msg in ws` restava appeso per sempre. Corretto con un `break`.

Poi la stessa cosa, un gradino più in basso e molto peggio: `interrupt()` manda
`Clear`, il server risponde `Cleared` — e quel ramo registrava `text_spoken` e
**continuava ad aspettare**. Misurato dal vivo:

```
21:02:19  barge_in_sostenuto  blocchi=5  da=sorvegliante
21:02:19  riproduzione_interrotta
21:02:19  barge_in
                                          ← e poi il journal tace
```

`parla()` non tornava, e il ciclo principale — che attende il turno dentro
`async for blocco in dal_microfono(...)` — restava sospeso: **microfono aperto e
sordo per il resto della sessione**. Chi parlava ha detto la frase successiva e
non è successo niente.

Aggiunto anche un **tetto di 20 s** sulla ricezione: il primo suono misurato su
questa rete sta fra 3,6 e 14,0 s, quindi venti secondi sono «il server tace»,
non «il server è lento». *Un turno perso è un turno perso; una sessione muta è
un'altra cosa.*

### 5 — Il ripiego di §16 valeva solo all'avvio

§16 dice «Deepgram: chiave invalida, 429, rete → **ricade sul locale e lo
annuncia**». Era imposto **una volta sola**, da `costruisci_tts()`, guardando se
la chiave c'era. **Un provider che fallisce mentre parla non era previsto da
nessuno.**

Tre turni di fila: wake riconosciuto, STT riuscito, T1 che risponde — e poi
`turno_caduto` con un HTTP 400. Chi parlava ha sentito il tono di conferma e
**nient'altro, tre volte, senza un annuncio**. Il guasto silenzioso nella sua
forma più pura, dentro il meccanismo che esiste per impedirlo.

`_con_ripiego()` ora costruisce il ripiego, **lo annuncia** e riprova — ma solo
se non è ancora uscito un suono: a metà frase i token sono già stati consumati e
rigenerarli è impossibile. Lì il turno si perde, **detto**.

---

## 6 — Il barge-in esisteva, era tarato, e non era raggiungibile

I due gate di §7.4 sono giusti: `BLOCCHI_BARGE_IN = 5` e
`SOGLIA_BARGE_IN = 0,030`, tarati su novanta secondi di eco misurata. **Non ne
ho cambiato un numero.**

Il difetto era strutturale. Il controllo

```python
if self._sta_parlando and self._vad.sostenuto:
```

sta in cima al ciclo principale, e il ciclo principale è **sospeso** mentre
JARVIS parla: `await self._su_trigger(...)` è dentro
`async for blocco in dal_microfono(...)`. Finché il turno non finisce **nessun
blocco viene letto**, e la condizione non poteva essere valutata proprio
nell'unico momento in cui conta.

> ⚠️ **Zero eventi `barge_in` in tutta la storia del progetto.** In
> `LA-VOCE-ATTRAVERSATA.md` avevo attribuito quello zero al fatto che JARVIS
> fosse muto. **Era una spiegazione sbagliata di un dato giusto**, e l'avevo
> scritta io.

La cura è un **sorvegliante**: un compito che parte col primo suono — da lì c'è
qualcosa da interrompere — legge il microfono in parallelo e chiama lo stesso
`interrompi()`. Ha un VAD **proprio** con le **stesse** soglie: far avanzare
l'isteresi del gate d'ascolto da due posti la corromperebbe. Un secondo
lettore, non una seconda taratura.

---

## Il giro chiuso, dal microfono

```
21:09:23  primo_suono_ms  ms=5591
21:09:37  barge_in_sostenuto  blocchi=5  da=sorvegliante  soglia=0.03
21:09:37  barge_in
21:09:37  interruzione_da_riferire  misurato=False  udito=394
21:09:37  turno_vocale                              ← il turno FINISCE
21:09:39  wake_trigger  frase=jarvis
21:09:43  nota_di_sistema  caratteri=727
```

E la risposta, alla lettera:

> **«No, Signore — mi ha interrotto dopo la prima frase.»**

Ieri lo stesso esito era stato ottenuto con turni **scritti**. Adesso viene da
una voce, con un'interruzione vera.

### ⚠️ Il ramo «misurato» resta NON VERIFICATO

`misurato=False` **anche con Deepgram**: il `Cleared` di Aura **non porta
`text_spoken`**, e la cornice è ricaduta sul limite superiore — «al più questo,
e forse meno» — invece che sulla misura. È il comportamento giusto: il sistema
ha scelto l'affermazione più debole e vera. Ma significa che il ramo
`misurato=True` **non è mai stato esercitato**, nemmeno adesso.

Aggiunta una riga che, alla prossima interruzione, stampa i campi veri di
`Cleared`: un'incognita trasformata in una misura da fare.

---

## Le misure

| | mediana | max | budget | esito |
|---|---|---|---|---|
| elaborazione Vosk | **6,40 ms** | 8,03 | 20 ms (§7.5) | ✅ |
| `parse()` | **0,041 ms** | 0,069 | 10 ms (§7.6) | ✅ |
| primo suono | **4,43 s** | 13,99 | ~1 s (§7.5) | ❌ |

Il primo suono resta fuori budget, come `FASE-03.md` dichiarava già a ~4,4 s
col ripiego locale. **Con Deepgram non è migliorato**, e il massimo di 14 s è
peggio di quanto fosse mai stato misurato.

**`conso/` conta i secondi veri**, che è ciò per cui ADR-004 esiste:

```
stt  deepgram   23,24 s      tts  deepgram  106,00 s
stt  vosk       46,72 s      tts  edge      221,16 s
```

**4 barge-in**, **3 note di sistema** consegnate.

---

## Verifica

### ✅ Le bocciature

endpoint `/v2` · nessun `break` su `Flushed` · nessun `break` su `Cleared` ·
nessun sorvegliante · nessun ripiego a caldo · voce inglese — **sei
perturbazioni, sei rossi**, ciascuna annullata con copie in scratch.

### ⚠️ Un inciampo mio, il secondo identico

Un test asseriva `"self._vad" not in dopo`, e il docstring **nomina**
`self._vad` per spiegare perché non lo usa: rosso per il commento invece che
per il codice. Stessa trappola di `esegui_t0` in `test_tre_orfani_veri.py`.
Corretto tagliando il docstring prima di cercare.

### ❌ NON verificato

- **Il ramo `misurato=True`** della cornice, vedi sopra.
- **I falsi risvegli con STT remoto.** Il blocco dei negativi non è stato
  detto: la sessione è finita sulla catena di difetti. Adesso un falso risveglio
  costa secondi di Deepgram, non solo attenzione.
- **Il primo suono sotto 1 s.** Fuori budget di 4,4×, e non è un difetto di
  questo turno: è il viaggio verso il modello.
- **La persona su una conversazione lunga.** Cinque frasi non sono un
  carattere.
