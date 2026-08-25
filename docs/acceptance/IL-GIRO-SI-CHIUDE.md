# «Papà è a casa» — detto da un umano, la scena si è aperta

**Rollback:** `752b830`
**Criterio ⑤ del piano:** «*papà è a casa* eseguito **offline** con la latenza
mediana misurata su cento frasi, non stimata».
**Esito: SODDISFATTO.** Per la prima volta in questo progetto una frase detta
da una persona ha attraversato tutta la catena e ha mosso lo schermo.

---

## 1. La traccia

```
18:18:28  wake_trigger    azione=scene:avvio  frase='papa e a casa'  latenza_ms=8.19
18:18:28  azione_diretta  azione=scene:avvio  frase='papa e a casa'
18:18:28  t0_ui           intento=scene  args={'nome': 'avvio'}
```

e la conferma che nessun log poteva darmi, perché il pixel non è un log:

> «Ho detto *papà è a casa* e la scena si è aperta».

La riga `t0_ui` è quella che ieri non esisteva: è `esegui_t0()` che emette
`ui.intent` con `args.nome`. Prima al suo posto c'era un `ui.action` che
nessuno ascoltava.

## 2. Il percorso, per intero

```
pw-record  ->  a_blocchi(640 byte, 20 ms)  ->  VAD (media tolta)  ->  Vosk locale
           ->  chiudi() alla chiusura del gate  ->  Trigger
           ->  esegui_t0()  ->  ui.intent  ->  socket UNIX  ->  Electron
           ->  applicaScena("avvio")
```

**Nove pezzi**, e in due giorni sette di loro erano rotti o scollegati. Nessuno
dei sette sollevava un'eccezione.

| | il difetto | come si sarebbe visto |
|---|---|---|
| `_gradi()` | componeva solo T1 | il microfono non si apriva |
| `audio_io` | `read(n)` non dà `n` byte | energia media senza significato |
| `VAD.energia` | RMS senza togliere la media | 250 blocchi su 250 «parlato» |
| barge-in | un blocco solo da 20 ms | JARVIS si interrompeva da solo |
| `EdgeTTS.interrupt` | una bandiera invece di un `kill` | muto per il resto della sessione |
| `pipeline.run` | `continue` sul silenzio | Vosk non chiudeva mai un enunciato |
| `_voce_su_azione` | topic `ui.action` | l'azione andava a nessuno |

## 3. Le due latenze, e restano due

⚠️ §11.7 regola 5: *la provenienza di una misura fa parte della misura*.

| | che cosa | valore | vincolo |
|---|---|---|---|
| **wake** | da `feed()` al `Trigger`, **24 trigger veri** di questa voce | mediana **7,76 ms**, max 13,95 | tempo reale: un blocco dura 20 ms |
| **T0** | `parse()` su testo, 133 frasi del corpus | mediana **0,0032 ms** | §7.6: 10 ms |

Sono due cose diverse e non si sommano né si sostituiscono. Il criterio ⑤ dice
«latenza mediana misurata su cento frasi»: quella è la seconda, ed era già
registrata in `T0-CORPUS.json`. La prima è nuova, ed è la prima misura di
questo progetto presa su una **voce umana**.

Per frase:

```
'jarvis'          n=17   mediana 7,79 ms   min 4,13   max 13,32
'papa e a casa'   n= 7   mediana 7,72 ms   min 4,53   max 13,95
```

## 4. «Offline» — verificato, non assunto

Il percorso di una frase-wake con azione diretta non tocca la rete:

* la cattura è `pw-record`, locale;
* il riconoscimento è Vosk col modello su disco (invariante 13);
* l'azione **salta lo STT e salta T1** — è il guadagno non ovvio di §7.2, ed è
  la ragione per cui esiste il percorso corto;
* la conferma acustica è un tono generato in locale;
* `ui.intent` viaggia su un socket UNIX in `$XDG_RUNTIME_DIR` (invariante 7).

⚠️ **Non è offline tutto il resto.** All'avvio, senza chiave Deepgram, i due
annunci di ripiego passano da EdgeTTS, che è rete Microsoft. E `jarvis` da solo
apre lo STT e può arrivare a T1. Offline è **questo percorso**, non il sistema.

## 5. Che cosa questo chiude

| documento | dichiarava |
|---|---|
| `T0-E-IL-MICROFONO.md` | «il criterio ⑤ non è soddisfatto» |
| `AUDIO-IO-BLOCCHI-ESATTI.md` | «il riconoscimento resta non provato» |
| `PRIMA-DI-ACCENDERE-IL-MICROFONO.md` | idem |
| `LA-VOCE-SI-SENTE.md` | idem |
| `JARVIS-NON-SI-SVEGLIAVA.md` | «non so se la SUA voce apre il gate» |
| `LA-VOCE-PARLAVA-A-NESSUNO.md` | «non ho verificato che l'intento arrivi allo schermo» |

Tutti annotati con la data e il rimando, non riscritti: restano la fotografia
di com'era, che è il loro valore.

Il gate: la voce **apre** a distanza normale dal portatile, e il numero non l'ho
dovuto toccare. Il fondo della stanza è 0,001 e la soglia 0,012 — il fattore
dodici che avevo *ragionato* c'era davvero.

## 6. Che cosa NON prova

1. **La polarizzazione continua di -8470 arriva ancora a Vosk**, e adesso so
   che **non gli impedisce di riconoscere**. Non so se gli costi accuratezza:
   per quello servirebbe un confronto A/B su parlato vero, e non l'ho fatto.
2. **Nessun falso positivo misurato.** Sette «papà è a casa» sono andati a
   buon fine; quante volte si svegli **quando non deve** non è misurato, e si
   misura solo lasciandolo acceso per ore.
3. **Due dei sette trigger di quella frase sono a tre secondi l'uno
   dall'altro** (18:18:28 e 18:18:31): o l'ha detta due volte, o si è
   svegliato due volte su una frase sola. Non so distinguere i due casi dal
   log, e per saperlo servirebbe registrare l'audio del trigger — che è una
   decisione sulla privacy, non un dettaglio tecnico.
4. **`jarvis silenzio` non fa ancora niente** (`mute` senza destinazione), e le
   scene `welcome_home` e `goodnight` restano da progettare.

## 7. Verifica

| | |
|---|---|
| trigger veri da voce umana | **24** |
| «papà è a casa» → scena aperta | **confermato dall'utente** |
| `uv run pytest -q` | **741 passed** |
| core / scrivania | pid 212984 / 212601, entrambi vivi |
| sorgenti toccate in questo turno | **nessuna** — solo documenti |
