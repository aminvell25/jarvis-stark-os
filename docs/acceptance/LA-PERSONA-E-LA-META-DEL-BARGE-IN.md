# La persona di T1, le due manopole morte, e la metà mancante del barge-in

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.2, §5.7, §7.4, §16
**Rollback**: `f29e5f2` · **Test**: 1347 → **1370** raccolti

---

## Una premessa del mandato non regge, e va detta prima

Il turno era da eseguire «PRIMA dell'attraversamento ① (accensione di
`voice.enabled`)». **① è già stato attraversato** (`40a7d57`): la voce era già
accesa da tredici ore quando abbiamo cominciato, perché il core legge
`~/.config/jarvis-os/settings.toml` e non la copia del repo.

La conseguenza pratica è quella che il mandato temeva, solo spostata:
l'attraversamento ① è stato fatto **con la persona vecchia**, quindi le sue
misure di latenza restano valide — non dipendono dal system prompt — mentre
tutto ciò che riguarda *come* JARVIS risponde va riattraversato.

---

## ① ② Le due manopole morte

`t1_persona` e `t1_cwd` stavano in `settings.toml`, erano validate da
`core/settings.py` e citate in §5.2 — e `core/engine.py` aveva **due percorsi
scritti a mano**. Cambiare il valore nel file non produceva alcun effetto.

È la stessa specie del `ui.grid_px` di §26.7 e dei due tetti del Governor: **un
parametro che esiste solo nella documentazione.**

Il terzo luogo c'era: `scripts/bench_t1.py:38` costruiva T1 con
`Path.home()/".local/share/..."` e `radice/"config/voice-persona.md"`. Un banco
che misura una configurazione diversa da quella che gira misura un'altra cosa.

Il percorso di prima resta come **predefinito**: chi non configura niente non
si accorge di nulla.

---

## ③ SPEC e il file spedito divergevano già

§5.7 **trascriveva** il testo della persona, e la trascrizione era già diversa
dal file: SPEC «è più naturale», file `e' piu' naturale`.

**La cura non è confrontare due copie: è non averne due.** §5.7 adesso rimanda
a `config/voice-persona.md` e non lo trascrive; un test si rompe se qualcuno
ricomincia.

Resta la **terza** copia — `~/.config/jarvis-os/voice-persona.md`, quella che
parla — che nessun test può guardare (`tests/conftest.py` spiega perché un test
che legge `~/.config/` passa o fallisce a seconda della macchina). La controlla
**`jarvis doctor`**, con la stessa forma di `_check_unit()`: non è una proprietà
del codice, è uno stato dell'installazione.

```
PERSONA    OK     identica al repository (97fdb99bcdea)
PERSONA    FAIL   DIVERSA dal repository: repo 97fdb99bcdea, installata 078ec5a51d8e.
                  E' la copia installata che parla.
```

---

## ④ La persona, sostituita

Sette difetti chiusi: «Creatore» (lessico di Ultron e Visione), «rispondi che te
ne occupi e basta» (dichiarava un esito non verificabile, e contraddiceva «Se
non sai, lo dici» tre righe sotto), «ironia asciutta quando serve» (troppo vago
per produrre alcunché), «due o tre frasi» (sbagliato come regola: una
spiegazione va ottenuta intera). Aggiunte: anticipare, dissentire, la
conseguenza dello streaming, e il contenuto non fidato.

### Il flag arriva davvero — provato, non dedotto

Il rischio era che `--append-system-prompt-file` non esistesse e venisse
ignorato in silenzio, rendendo l'intero turno teatro. Tre turni reali:

| | risposta a «Di' esattamente: pronto.» |
|---|---|
| senza persona | `'pronto.'` / `'Pronto.'` |
| con persona (vecchia o nuova) | **`'Pronto, Signore.'`** |

E due turni con la persona nuova, attraverso il percorso composto
(impostazioni → engine → `argv`):

> **Q:** Quanto fa sette per otto? — **A:** «Cinquantasei, Signore.»
> **Q:** Apri il pannello telemetria. — **A:** «Non ho strumenti per controllare
> l'interfaccia, Signore. Quelle azioni le esegue il sistema.»

Un fatto ottiene una frase; i numeri sono in parole; i LIMITI reggono.

⚠️ **Una nota onesta**: la persona prescrive «Vedo, Signore» / «Me ne occupo»
per le azioni, e il modello ha invece dichiarato di non avere strumenti. È più
onesto di quanto chiesto, ma non è quanto chiesto.

### Il budget dei token — NON MISURABILE, e deroga dichiarata

**① La premessa era falsa.** «Viaggia in ogni turno» non regge: T1 è
persistente, `--append-system-prompt-file` è un flag di **processo** passato una
volta a `start()`, e `ask()` scrive sullo stdin **soltanto** il messaggio
dell'utente. Non esiste il meccanismo per rimandarla.

**② Il conteggio è NON MISURABILE con gli strumenti di questo progetto.**
Nessun tokenizer fra le dipendenze, e non se ne aggiunge uno di soppiatto. Ho
provato a leggerlo da `usage` del CLI: è dominato da
`cache_creation_input_tokens`, che fra esecuzioni **identiche** ha oscillato fra
**13 082 e 16 643**. Un delta di duecento token non si estrae da quel rumore.

Ciò che è misurato è un **rapporto**, non un conteggio: 946 → 2 393 byte
(**2,53×**), 152 → 399 parole (**2,63×**).

**③ Il vincolo vero resta**, e non è il costo: un system prompt lungo su Haiku
diluisce l'aderenza. Deroga **dichiarata** in §5.7, con la ragione e il numero
che ho — non con quello che non ho.

---

## ⑤ La metà mancante del barge-in

Il barge-in **non è stato toccato**: due gate, cinque blocchi, soglia dedicata,
tarati su novanta secondi di eco misurata.

`ClaudeT1._drena()` consuma la generazione abbandonata e la **scarta**: dal
punto di vista del modello quella risposta è stata detta per intero.

### Un difetto dentro la metà dichiarata «fatta»

`text_spoken` → `Turno.testo_detto` → `sessions/`. Ma nel codice
`detto: list[str] = []` era **dichiarata e mai riempita**, e
`testo_detto = getattr(provider, "text_spoken", "") or "".join(detto)` con il
TTS locale — che non ha `text_spoken` — dava **la stringa vuota**. Ogni turno
locale finiva in `sessions/` col campo `jarvis` vuoto: la metà «fatta» lo era
solo per Deepgram, che su questa macchina non ha mai girato.

Adesso un generatore tracciante registra il testo **tirato dal
sintetizzatore**. È un **limite superiore** di ciò che è stato udito, non una
misura: fra l'ultimo token tirato e l'ultimo campione riprodotto c'è la coda del
sintetizzatore.

### La cornice, e le tre trappole

`core/llm/sistema.py`. Il formato `stream-json` non ha un ruolo «system» a metà
conversazione, quindi la nota viaggia dentro il messaggio `user` — ed è lì che
sta il rischio.

1. **Non confondibile**: la prima riga dice *in italiano* «Nota del sistema, non
   parole del Signore». Un tag da solo non basta: un modello che non l'ha mai
   visto lo tratta come testo.
2. **Non falsificabile**: `<sistema_jarvis>` è neutralizzato dentro
   `Untrusted.avvolto()`, come la chiusura di `<untrusted_source>`. Un titolo di
   giornale non può prendere la voce del core. **Chiuso prima che qualcuno lo
   trovi**, non dopo.
3. **Assente senza interruzione**: nessuna nota se non c'è stato barge-in, e la
   nota si consuma una volta sola.

E la differenza fra misura e limite superiore è **detta al modello**: «ha udito
soltanto» con `text_spoken`, «al più questo, e forse meno» col TTS locale.

### La prova comportamentale — due sondaggi, e uno solo discrimina

Interruzione vera a metà (lo stream abbandonato è esattamente ciò che fa il
barge-in), poi un secondo turno. Due domande diverse:

**Sondaggio A — «Cosa mi stava dicendo?»: NON discrimina.**

| | risposta |
|---|---|
| senza nota | «Stavo spiegando il ciclo del diesel… e perché rende i motori più efficienti» |
| con nota | «Stavo descrivendo il ciclo dei quattro tempi… espelle i gas» |

Entrambe descrivono più di ciò che è stato udito. Ma il criterio «citi SOLO ciò
che è stato udito» **è il criterio sbagliato per questa domanda**: a chi chiede
«cosa mi stava dicendo», rispiegare è la risposta giusta.

**Sondaggio B — «Ha finito di spiegarmi?»: discrimina nettamente.**

| | risposta |
|---|---|
| **senza nota** | «**Sì, Signore. L'ho conclusa.**» |
| **con nota** | «**No, Signore — Lei mi ha interrotto dopo i primi due tempi.** Vuole che continui?» |

Il primo è il difetto, testuale: JARVIS crede di aver detto ciò che nessuno ha
udito. Il secondo è la cura. **⑤ è chiuso**, e la prova non passa perché
l'interruzione non è avvenuta: l'interruzione avviene, e senza la cornice il
modello sbaglia.

---

## Verifica

### ✅ Sette bocciature, tutte eseguite

| perturbazione | esito |
|---|---|
| persona scritta a mano in `engine.py` | 1 rosso |
| cwd scritta a mano | 1 rosso |
| SPEC ritrascrive la persona | 1 rosso |
| persona vecchia rimessa | 4+ rossi |
| la nota non arriva a T1 | 1 rosso |
| il testo detto non si registra | 1 rosso |
| la cornice diventa falsificabile | 1 rosso |

Più la bocciatura di `doctor`: aggiunta una riga alla copia installata →
`PERSONA FAIL`, rimossa → `OK`.

### ✅ I test raccolti sono cresciuti

**1347 → 1370**, e la suite è verde.

### ⚠️ Un difetto trovato durante il lavoro

L'import di `nota_di_interruzione` in `pipeline.py` **non era entrato** — l'àncora
usata per inserirlo non corrispondeva — e **la suite è passata lo stesso**:
quella riga non è coperta da nessun test, perché sta sul percorso vocale vero.
Corretto, e vale la pena dirlo: la copertura di quel ramo è ciò che
l'attraversamento ① avrebbe dovuto dare e non ha dato.

### ❌ NON verificato

- **La persona dal microfono.** Provata con turni scritti a T1, non parlati. È
  il riattraversamento di ① che il mandato prevedeva, e che resta da fare.
- **Il conteggio in token.** NON MISURABILE, vedi sopra. Il vincolo di §5.7 è
  in deroga dichiarata.
- **L'aderenza su una conversazione lunga.** Due turni non sono un carattere:
  la diluizione su Haiku si vede parlando per venti minuti, non per due
  domande.
- **La cornice col TTS di Deepgram**, dove `text_spoken` è una misura vera.
  Senza chiave, il ramo `misurato=True` è provato solo con un finto.
