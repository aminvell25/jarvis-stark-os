# Le news girano — e la cadenza è dedotta, non inventata

**Rollback:** `8d4a1ec`
**Che cosa chiude:** il punto 3 dei NON VERIFICATI di Fase 9 («la menzione
vocale delle news»), e il difetto dichiarato in
`PRIMA-DI-ACCENDERE-IL-MICROFONO.md` §5 — «`Watcher.giro()` non ha un solo
chiamante nel core».
**Esito: il motore gira, un giro vero contro i feed veri è stato fatto, e il
numero che non era scritto da nessuna parte è derivato da due vincoli con la
derivazione scritta accanto.**

---

## 1. Il difetto, per la settima volta

`Watcher.giro()` non aveva **un solo chiamante nel core**: solo un test e uno
script di fixture. Con `news.enabled = true` il `Watcher` si costruiva a ogni
avvio, e lo snapshot diceva `giri_fatti: 0` — l'avevo messo io due giorni fa
proprio perché quel numero rendesse visibile la differenza fra «costruito» e
«funziona».

`EstrattoreLLM` era nello stesso stato, e il suo commento lo aveva previsto:

> il giorno in cui la pipeline sarà composta basterà passargliela.

## 2. La cadenza: che cosa è scritto e che cosa no

⚠️ **§15 non dichiara ogni quanto si guardino i feed.** Dichiara una sola
frequenza — **3 interruzioni all'ora** — che è il ritmo con cui JARVIS può
**parlare**, non quello con cui può **guardare**. Sono due cose diverse, e
prenderne una per l'altra sarebbe la scorciatoia.

**Il vincolo dal basso viene dal budget.** Tre interruzioni all'ora fanno una
finestra di 1200 s l'una. Un giro lungo quanto la finestra dà **un** candidato
per finestra: se il gate lo scarta — poco rilevante, già visto, Lei sta
parlando — quella finestra è persa fino al giro dopo. Dimezzandola ce ne sono
due.

**Il vincolo dall'alto viene dagli argomenti.** Un argomento vive 30 minuti.
Un giro più lento della vita di un argomento vorrebbe dire che un argomento può
nascere e scadere **senza essere mai stato guardato** — la funzione non
farebbe niente, in silenzio.

**E un pavimento che non viene dall'aritmetica.** Con `max_interruptions_per_hour
= 60` la formula darebbe 30 s su server che non sono nostri. Sotto il minuto
non si scende: è educazione, non calcolo, e lo scrivo perché è l'unico dei tre
numeri che non deriva da niente.

```
periodo = min( max( 3600 / (2 × tetto), 60 ), ttl_minuti × 60 / 2 )
```

| tetto/ora | periodo | da quale vincolo |
|---|---|---|
| 1 | 900 s | il TTL degli argomenti |
| 2 | 900 s | il TTL |
| **3** | **600 s** | **il budget — è il caso di §15** |
| 6 | 300 s | il budget |
| 30 | 60 s | il pavimento |

⚠️ **Il numero cambia con l'impostazione, ed è la proprietà che conta.** Una
costante travestita da deduzione passerebbe un test sul valore e fallirebbe
`test_CAMBIA_col_tetto`, che è lì apposta.

## 3. Senza argomenti non si guarda affatto

`giro()` calcola la rilevanza **contro gli argomenti**. Senza, niente può
essere rilevante e niente può passare: un giro a lista vuota è traffico su un
server di terzi in cambio di nulla. §15 vuole che le news seguano la
conversazione, e finché non si è parlato non c'è conversazione da seguire.

Misurato sul core vivo, appena riavviato:

```
"news_motore": { "periodo_s": 600.0, "giri_fatti": 0, "argomenti": [] }
```

Zero giri, e va bene così: nessuno ha ancora parlato.

## 4. Gli argomenti vengono dalla conversazione, e la card si dice

`_voce_su_turno` passa `turno.testo_utente` all'estrattore. Senza quella riga
il motore girerebbe **a vuoto per sempre** — un ciclo che non fa niente invece
di una funzione che non c'è, cioè peggio.

E `pubblica` non è più il broadcast nudo: è il broadcast **più** la menzione
vocale di §15 («card news + menzione vocale breve»).

⚠️ **Il titolo è dato non fidato, e dirlo ad alta voce non è eseguirlo**: il
TTS non ha tool, ed è precisamente il «contesto con zero tool» che §12 richiede.
Ciò che non si fa è passarlo a qualcosa che agisce.

⚠️ E la menzione **non aspetta**: parlare passa da EdgeTTS, che è di rete, e un
annuncio che non parte non deve far cadere il giro. Stessa forma degli annunci
di ripiego, per la stessa ragione.

## 5. Un giro vero, contro i feed veri

```
argomenti: ['preoccupa']
giro fatto: True · giri: 1
```

Il motore aziona i feed. **Nessuna card è passata**, e la ragione è misurata,
non supposta: l'argomento estratto è `preoccupa` — un verbo — invece di `clima`
e `governo`.

### La qualità dell'estrattore locale, misurata

| frase | argomenti |
|---|---|
| «mi preoccupa il clima, e cosa fa il governo in italia» | `['preoccupa']` |
| «stavo leggendo di intelligenza artificiale e semiconduttori» | `['artificiale', 'intelligenza', 'leggendo', 'semiconduttori']` |
| «che si dice del terremoto in giappone» | `['giappone', 'terremoto']` |

Due su tre sono buoni. Il primo perde i due sostantivi che contano e tiene un
verbo: con quell'argomento nessuna notizia può essere rilevante, e il giro non
può che tornare a mani vuote.

**È il ripiego, e §15 lo sa**: chiede un estrattore *haiku*. Vedi §7.

## 6. Verifica

| | |
|---|---|
| `uv run pytest -q` | **1103 passed** (erano 1080), zero rossi |
| `tests/test_news_motore.py` | **23** |
| dal vivo, sotto systemd | `grado_acceso grado=news_motore periodo_s=600.0` |
| un giro contro i feed veri | fatto, `giri: 1` |

**Ritirato un cardine per volta:**

| ritirato | esito |
|---|---|
| la cadenza diventa una costante | **5** rossi |
| si guarda anche senza argomenti | 1 rosso |
| il contesto si fissa alla costruzione | 1 rosso |
| nessuno avvia il motore | 1 rosso |
| gli argomenti non arrivano dal turno | 1 rosso |
| la menzione vocale sparisce | 1 rosso |

## 7. Dichiarato aperto

1. **L'estrattore haiku di §15 NON è collegato**, ed è la ragione per cui il
   giro vero è tornato a mani vuote. Non è una riga: il batch di §15 è **60 s**
   e il tetto di §5 è **15 spawn T2 all'ora**. Chi parla in continuazione
   chiederebbe 60 estrazioni all'ora contro un tetto di 15 — servono una
   decisione sul budget e probabilmente un batch più lungo, non un collegamento.
   E T1 non è la strada: usarlo sporcherebbe il suo contesto, che l'invariante
   17 vieta di duplicare.
2. **Nessuna card è mai passata dal gate in esercizio.** Il percorso è provato
   fino ai feed; che una notizia arrivi allo schermo e alla voce dipende dal
   punto 1 e da che cosa c'è oggi nei feed.
3. **La menzione vocale non è stata udita.** Il codice c'è ed è provato; perché
   suoni serve una card che passi.
4. **Il pavimento di 60 s è l'unico numero che non deriva da niente** (§2). Se
   un giorno un feed chiedesse di essere interrogato più di rado, quel numero va
   guardato di nuovo — non alzato di nascosto.
