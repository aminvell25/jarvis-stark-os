# «Jarvis» non faceva niente — il gate affamava Vosk del silenzio

**Rollback:** `03c89b9`
**Sintomo riferito:** «Ho detto *jarvis* ma non è successo niente».
**Esito: trovato, e non era il microfono. Il ciclo toglieva a Kaldi
esattamente ciò che gli serve per chiudere una frase. Corretto e provato col
riconoscitore vero: quattro frasi su quattro, latenze 4,6–8,3 ms.**

---

## 1. Che cosa il core aveva visto: niente

Nessun trigger, nessun errore, nessuna riga. Il core era vivo, il microfono
aperto, T1 vivo. Un guasto perfettamente silenzioso.

## 2. La misura che ha separato le due ipotesi

Le possibilità erano due — il microfono non arriva a Vosk, oppure Vosk non
riconosce — e si separano senza scomodare nessuno: si sintetizza la parola e
la si dà in pasto al riconoscitore, senza passare dal microfono.

| | |
|---|---|
| audio intero, silenzio compreso | trigger **`jarvis`** |
| **solo i blocchi che il VAD lascia passare** — cioè quel che fa `run()` | **NESSUN trigger** |

Il riconoscitore, il modello e la grammatica funzionavano. Era il **ciclo**.

## 3. La causa

```python
if not parlato:
    continue                      # silenzio: Vosk non si sveglia
```

Il commento dice la verità e descrive il difetto senza saperlo. Il gate
d'ascolto esiste per non far girare Vosk sul silenzio (§7.1), e a Vosk
arrivavano **solo** i blocchi giudicati parlato.

Ma **Kaldi chiude un enunciato quando sente il silenzio.** Togliendoglielo, il
riconoscitore restava per sempre a metà di una frase che non finiva mai.

Una riga scritta per risparmiare CPU impediva il riconoscimento, e nessuna
delle misure fatte finora poteva accorgersene: blocchi della misura giusta,
latenza di `feed()`, assenza di falsi trigger sul silenzio — tutte vere, tutte
cieche a questo. **Serviva una frase**, e nessuno gliene aveva mai detta una.

## 4. Le due strade, e perché la seconda

**Continuare a nutrirlo di silenzio dopo la chiusura del gate.** Funziona, ma
serve tanto silenzio. Misurato su quattro frasi:

| K blocchi dopo la chiusura | `Jarvis.` | `Papà è a casa.` | `Jarvis buonanotte.` |
|---|---|---|---|
| 0 … 25 | nessuno | nessuno | nessuno |
| **40** | ✅ | ✅ | ✅ |

Ottocento millisecondi, e appesi a un dettaglio interno di Kaldi che cambia col
modello. Un numero così è la specie che questo progetto ha già ritirato due
volte.

**Chiedere il finale quando il gate si chiude.** Deterministico: non dipende da
quanto silenzio il riconoscitore voglia, e la frase si riconosce **240 ms** dopo
che si è smesso di parlare — la coda dell'isteresi — invece che dopo 800.

`PhraseWake.chiudi()`, e `feed()` e `chiudi()` condividono `_riconosci()`: una
sola opinione su che cosa sia una frase nota.

## 5. La verifica, col riconoscitore vero

Quattro frasi **di seguito**, un solo riconoscitore, dentro `run()` vero:

```
TRIGGER: [('jarvis', 7.62 ms), ('papa e a casa', 8.27 ms),
          ('jarvis silenzio', 4.69 ms), ('jarvis buonanotte', 4.61 ms)]
```

Tutte e quattro, e il riconoscitore si rimette a zero fra un enunciato e
l'altro — che è la seconda cosa che `FinalResult()` doveva fare e che andava
verificata, non data per buona.

⚠️ **`jarvis` non produce un'azione, ed è giusto così**: mappa su `listen`,
quindi prende il ramo STT invece di quello dell'azione diretta. La prima
lettura di questa misura contava le azioni e ne trovava tre su quattro: era la
mia aspettativa a essere sbagliata, non il codice.

## 6. Le prove

`tests/test_wake_si_sveglia.py`, **6** asserzioni:

| | |
|---|---|
| alla chiusura del gate si chiede il finale | il difetto, alla lettera |
| il silenzio **puro** non chiude niente | senza un enunciato aperto non c'è niente da chiudere |
| si chiude **una volta sola** per enunciato | trenta blocchi di silenzio sono una pausa, non trenta |
| due frasi fanno **due** chiusure | |
| il parlato arriva **ancora** a Vosk | la metà che conta di più: non rompere il caso buono |
| **una frase vera sveglia JARVIS** | col modello Vosk vero |

**Ritirate:**

| correzione ritirata | esito |
|---|---|
| il `continue` sul silenzio (il difetto) | **4** rossi |
| `chiudi()` che non riconosce | 1 rosso |

### La fixture, e la sua provenienza

`tests/fixtures/wake-jarvis.pcm.gz` — 59 136 byte di PCM, s16le mono 16 kHz,
compressi in 25 869 — con `wake-jarvis.json` accanto: voce, formato, durata e
`sha256`, che il test verifica prima di usarlo.

⚠️ **È la parola «Jarvis» sintetizzata da edge-tts, NON una voce umana.** Prova
che la catena gate → Vosk → trigger funziona da capo a fondo; **non** prova che
riconosca Lei. Esiste perché edge-tts è di rete e il modello Vosk non sta nel
repo: senza il file, la prova col riconoscitore vero non potrebbe girare
offline.

⚠️ **Senza il modello Vosk il test si SALTA**, e un test saltato non è verde
(§11.7 regola 4). Su questa macchina gira.

| | |
|---|---|
| `uv run pytest -q` | **734 passed** (erano 728) |
| sorgenti UI toccate | **nessuna** |

## 7. Dichiarato aperto

1. **Non so ancora se la SUA voce apre il gate.** Tutto quel che è provato usa
   audio sintetico riprodotto dagli altoparlanti o iniettato. Il fondo della
   stanza è 0,001 e la soglia d'apertura è 0,012: c'è un fattore dodici, e una
   voce vicina al portatile dovrebbe passarlo largamente — **ma è ragionato,
   non misurato.** Se dicendo «papà è a casa» non succede niente, è questo il
   prossimo numero da guardare.
2. **La polarizzazione continua di -8470 arriva ancora a Vosk.** Il VAD adesso
   la ignora, il riconoscitore no. Sull'audio sintetico non dà fastidio —
   quello non ce l'ha — quindi **questa prova non dice niente su un audio che
   la contiene**, cioè proprio quello del microfono. È il sospetto numero due
   se il riconoscimento fallisse dal vivo.
3. **La stessa domanda vale per `_trascrivi()`**, che alimenta lo STT con lo
   stesso schema e potrebbe avere lo stesso guasto di endpointing. Non l'ho
   toccato: si vedrà quando una frase supererà il wake.
4. **Restano aperti** i punti di `BARGE-IN-DUE-GATE.md`,
   `LA-VOCE-SI-SENTE.md` e `PRIMA-DI-ACCENDERE-IL-MICROFONO.md`.
