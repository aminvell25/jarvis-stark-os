# Il barge-in tagliava tutto — e la colpa era di JARVIS, non della stanza

**Rollback:** `70f2b9b`
**Richiesta:** «Il barge-in taglia tutto, mettici N blocchi consecutivi».
**Esito: fatto, e N da solo NON bastava. Servivano due gate. Su 90 s di eco
vera: da 787 blocchi che avrebbero interrotto a ZERO. Gli annunci d'avvio
adesso arrivano in fondo — nove secondi ciascuno, nessuna interruzione.**

---

## 1. Correzione a quel che avevo detto

Nel turno precedente ho scritto:

> A tagliare le frasi sono i **transitori della stanza**, non l'eco: con JARVIS
> zitto il massimo è 0,764, sessanta volte la soglia.

**È sbagliato**, e l'errore è di campionamento: quella misura durava sei
secondi e io stavo digitando. Il controllo giusto, novanta secondi con JARVIS
zitto e le mani ferme:

```
STANZA 90 s (JARVIS zitto): 4500 blocchi, 0 sopra soglia (0,0 %), 0 raffiche
```

**Zero.** Quindi le 43 raffiche misurate mentre JARVIS parla sono **tutte
eco della sua stessa voce**. Non era la stanza: era JARVIS che interrompeva se
stesso, sistematicamente.

Il difetto della mia diagnosi è quello che questo progetto nomina da giorni: ho
misurato una cosa vera e l'ho attribuita alla domanda sbagliata. La differenza
qui è che il controllo costava novanta secondi e non l'avevo fatto.

## 2. Perché N da solo non bastava

La distribuzione delle raffiche — blocchi consecutivi sopra la soglia
d'ascolto — su 90 s di eco:

```
1x18   2x9   3x8   4x5   8x1   19x1   23x1              43 raffiche
```

| N | raffiche che sfondano |
|---|---|
| 3 | 16 |
| 4 | 8 |
| **5** | **3** |
| 6 | 3 |
| 8 | 3 |

Cinque blocchi respingono quaranta raffiche su quarantatré. Le tre che restano
sono lunghe **8, 19 e 23 blocchi** — 160, 380 e 460 ms — e nessun N ragionevole
le ferma. Portare N a 24 le fermerebbe, ma vorrebbe dire **480 ms** di ritardo
prima che JARVIS si zittisca, e una parola breve come «basta» dura meno: il
barge-in smetterebbe di funzionare proprio nel caso per cui esiste.

⚠️ **E un campione corto avrebbe dato la risposta comoda.** I primi 30 s
davano raffiche lunghe al massimo 4, cioè «N=5 basta e avanza». Le tre lunghe
compaiono solo allungando la misura. Un numero calibrato su quel campione
sarebbe passato tutte le prove e avrebbe continuato a tagliare.

## 3. Il secondo gate, e perché è un problema più facile

Il gate d'ascolto e il gate del barge-in rispondono a due domande diverse:

* l'ascolto deve **sentire una voce da lontano**, quindi apre basso: 0,012;
* il barge-in deve **distinguere una voce dall'eco della propria**, e l'eco è
  attenuato dal percorso altoparlante-stanza-microfono.

Un solo numero per due domande è la stessa specie di difetto dei tre ritagli e
dei due orologi: una proprietà, due proprietari.

Le energie dell'eco, 4500 blocchi su 90 s:

```
p50 0,00214   p90 0,00655   p99 0,01281   p99,9 0,01630   MAX 0,02444

sopra 0,012 -> 72 blocchi        sopra 0,020 -> 3        sopra 0,030 -> 0
```

**0,030** lascia passare zero blocchi d'eco, con un margine di 1,23× sul
massimo misurato.

## 4. La misura, sullo stesso audio

Novanta secondi di eco vera, dati in pasto a due VAD in parallelo — la regola
di prima e quella di adesso, stesso segnale, stesso istante:

| | |
|---|---|
| PRIMA — un blocco sopra 0,012 | **787 blocchi** avrebbero interrotto |
| DOPO — cinque blocchi sopra 0,030 | **0 interruzioni** |

787 e non 72 perché conta l'isteresi: una volta aperto, il gate resta aperto
per dodici blocchi di silenzio. Un colpo d'eco isolato valeva 260 ms di
«qualcuno sta parlando».

### E sul sistema vero, dopo il riavvio

```
16:58:28  primo_suono_ms  ms=573
16:58:37  turno_vocale    primo_suono_ms=573.0        <- nove secondi interi
16:58:38  primo_suono_ms  ms=10253
16:58:47  turno_vocale    primo_suono_ms=10253.0      <- e altri nove
barge_in: 0
```

Prima le stesse due frasi morivano dopo circa tre secondi, e prima ancora
prima del primo campione.

## 5. Un terzo difetto, trovato per strada

Sul ramo in cui JARVIS parla, `parla()` veniva chiamato **due volte sullo
stesso blocco** — una per il barge-in e una per il gate. Ogni chiamata fa
avanzare l'isteresi, quindi il contatore del silenzio correva al doppio della
velocità **esattamente mentre JARVIS parlava**, cioè nel momento in cui la
misura conta di più. Adesso il blocco si consuma una volta sola, e c'è una
prova che conta le chiamate.

## 6. Dove vivono i numeri

In `core/voice/pipeline.py`, come costanti con la misura scritta accanto:
`BLOCCHI_BARGE_IN = 5` e `SOGLIA_BARGE_IN = 0.030`. Il conteggio sta dentro il
`VAD` — «da quanto qualcuno parla» è una proprietà del VAD, non del ciclo — e
si azzera a ogni pausa e dopo ogni barge-in, perché la coda del suono che ha
appena interrotto non deve interrompere anche la frase successiva.

Il log dice perché è scattato: `barge_in_sostenuto blocchi=… soglia=…`. Un
barge-in che non dice quanto è durato non si può tarare.

## 7. Le prove

`tests/test_voce_barge_in.py`, **14** asserzioni (erano 8). Le sei nuove:

| | |
|---|---|
| un blocco forte da solo **non** interrompe | il difetto, alla lettera |
| cinque di fila interrompono | l'altra metà: il barge-in deve ancora funzionare |
| una pausa **azzera** il conto | quattro colpi, pausa, quattro colpi non fanno otto |
| i due gate sono **diversi** | un suono fra 0,012 e 0,030 apre l'ascolto e non interrompe: è la fascia dove vive l'eco (p99 = 0,01281) |
| dopo un barge-in il conto riparte | la coda non interrompe la frase dopo |
| il VAD consuma un blocco **una volta sola** | §5 |

**Ritirata una correzione per volta:**

| correzione ritirata | esito |
|---|---|
| `BLOCCHI_BARGE_IN` torna a 1 | 1 rosso |
| `SOGLIA_BARGE_IN` torna a 0,012 | 1 rosso |
| l'azzeramento sulla pausa | 1 rosso |
| la doppia chiamata al VAD | 1 rosso |

| | |
|---|---|
| `uv run pytest -q` | **728 passed** (erano 722) |
| eco vera, 90 s | 787 → **0** |
| annunci d'avvio | interi, **9 s ciascuno**, zero barge-in |
| sorgenti UI toccate | **nessuna** |

## 8. Dichiarato aperto

1. **Quanto forte arrivi la SUA voce a questo microfono non è misurato.**
   0,030 è calibrato sull'eco, che è misurato; l'altro lato della soglia no.
   Se dicendo qualcosa mentre JARVIS parla non si zittisse, è questo il numero
   da abbassare — e il log `barge_in_sostenuto` dirà quanto ci è andato vicino.
2. **Alzare il volume degli altoparlanti alza l'eco.** 0,030 vale per il
   volume di oggi. Il comando che rifà la misura è nel documento e nel
   commento della costante.
3. **Nessuna cancellazione d'eco.** Due gate separati sono il rimedio
   pragmatico; l'AEC vero è un'altra cosa e non è in §7.
4. **La coda di 12 blocchi dell'isteresi non l'ho toccata.** È lei a
   trasformare 72 blocchi d'eco in 787 decisioni di «sta parlando», e adesso
   non fa più danno al barge-in — ma continua a tenere aperto il gate
   dell'ascolto per 240 ms dopo ogni suono.
5. **Restano aperti i punti** di `LA-VOCE-SI-SENTE.md` e
   `PRIMA-DI-ACCENDERE-IL-MICROFONO.md`: il riconoscimento non provato,
   EdgeTTS di rete, le news che non girano.
