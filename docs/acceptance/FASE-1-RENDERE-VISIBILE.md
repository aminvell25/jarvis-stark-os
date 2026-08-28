# Fase 1 — Rendere visibile

**Base:** `7a4b39f`, 1733 test verdi · **Commit:** `1e109a4` (turno 1) e questo
(turno 2) · **Rollback:** `7a4b39f`

Non è una fase di funzionalità. Serve perché la sera dell'attraversamento
(fase 2) si possa distinguere **«non è passato niente»** da **«non poteva
passare»** — l'ambiguità in cui §15 si è nascosta per sei turni consecutivi.

---

## Il vero prodotto: che cosa GUARDARE quando non passa nessuna card

Lo snapshot del core porta un campo nuovo:

```
stato["news_motore"]["conoscibilita"]
```

È un dizionario con **una parola per ogni campo del `Contesto`** che il gate di
§15 legge. Si legge così, e ogni riga dice che cosa fare:

| che cosa legge | vuol dire | che cosa fare |
|---|---|---|
| `noto` | il campo si sa, e il gate ha deciso su un fatto | niente: se la card non è uscita, il motivo è un altro (rilevanza, budget, argomento silenziato) |
| `mai_letto` | nessun giro ha ancora guardato | guardare `giri_fatti` e `argomenti` nello stesso snapshot: a lista di argomenti vuota un giro non parte affatto |
| `non_prodotto` | **nessuno riempie quel campo** | è un pezzo che manca: il gate resterà chiuso per sempre finché non lo si collega |
| `non_composto` | il produttore c'è e dice «non lo so» | un interruttore spento: voce spenta, o nessuna scrivania ha mai riferito |
| `ha_sollevato` | il produttore ha fallito adesso | **guasto**: nei log c'è `stato_non_leggibile` col campo e l'eccezione |
| `risposta_storta` | il produttore ha risposto qualcosa che non è un `bool` | **guasto**: nei log c'è `stato_non_bool` col campo e il tipo |

Le prime tre righe sono **configurazione** — si risolvono accendendo qualcosa.
Le ultime due sono **difetti da inseguire**. Prima di oggi erano tutte lo stesso
`None`, e lo snapshot non le distingueva.

### Le tre letture più probabili, quella sera

**a) `frase_in_corso: non_composto` e `sta_parlando: non_composto`**
La voce è spenta. **Le notizie richiedono la voce accesa** — è dichiarato in
§15.1, è fail-closed corretto, e finché resta così nessuna card può passare.
Si accende `voice.enabled`.

**b) `pannello_a_schermo_intero: non_composto`**
Nessuna scrivania ha ancora riferito il proprio layout. Diverso da `noto` con
valore falso, che vuol dire «ha riferito, e nessun pannello è massimizzato».
Si sposta o si ridimensiona una finestra e il campo si accende.

**c) tutti e tre `noto`, e ancora zero card**
Allora il gate ha deciso su fatti, e il motivo è a valle: `giri_fatti` che non
cresce, `argomenti` vuoto, o rilevanza sotto `RILEVANZA_MINIMA`.

⚠️ **Un caso che questo campo NON copre**: il Signore che parla senza che il
VAD apra — voce bassa, microfono lontano. Lì `frase_in_corso` dice `noto: false`
mentre in realtà una frase c'è. Il gate non lo saprà, ed è un limite dichiarato,
non un difetto nascosto.

---

## Turno 1 — la conoscibilità del contesto

### Che cosa è cambiato

- Nasce `core/news/conoscibilita.py`: `Sguardo` (valore **e** causa, dalla
  stessa lettura), `guarda()`, `Lettura` (il `Contesto` di un giro e il perché
  di ogni suo ignoto), sei cause in due specie.
- `MotoreNews.stato()` espone `conoscibilita`. **`voce_collegata` è tolto**: era
  il ragionamento giusto applicato a un campo su tre, e due modi di dire una
  cosa sola sono la famiglia di difetto che questa fase insegue.
- I campi sono **derivati** da `dataclasses.fields(Contesto)`: il quarto che
  qualcuno aggiungesse domani entra da solo.
- §15.1 e §15.2 in `docs/SPEC.md`: la dipendenza dalla voce accesa e le due
  specie di ignoto.

### Il vincolo rispettato

**Nessun secondo produttore.** Ogni campo ha ancora un solo produttore, e la
causa esce dalla stessa chiamata che produce il valore. `conoscibilita()` **non
legge**: riferisce l'ultima lettura, o dice `mai_letto`. Rileggere darebbe un
valore diverso da quello che il giro ha usato.

**Il gate riceve esattamente quello di prima.** `Lettura.contesto()` porta i tre
tri-stati e nient'altro. Una regola che potesse leggere la causa finirebbe per
allentarsi.

### Una riga tolta, non aggiunta

`Engine._voce_sta_parlando` aveva un `try/except` che rendeva `None` una
pipeline rotta. `MotoreNews._parla_adesso` ne ha già uno che fa la stessa cosa e
in più sa **classificarla**: ingoiando a monte, un guasto arrivava a chi guarda
travestito da voce spenta.

### Misura

| | prima | dopo |
|---|---|---|
| test | 1733 | 1763 (1770 a fine fase) |
| campi del `Contesto` con una causa leggibile | 0 | 3 su 3 |
| bocciature eseguite | — | 7 rosse, 1 non discriminava |

⚠️ **L'ottava bocciatura NON discriminava.** La guardia «nessun lettore» in
`_parla_adesso` è irraggiungibile da `_contesto_adesso`, che senza lettore non
tocca il campo. Non è morta — toglierla farebbe chiamare `None()` — è una
precondizione di un metodo privato, e adesso ha un test che la chiama da sola.

⚠️ **Due orfani miei, trovati un minuto dopo averli scritti.** `Sguardo.guasto`
e `Lettura.noti`: nessun chiamante in `core/`. Tolti; la scorciatoia per i test
vive in `tests/conftest.py`.

⚠️ **Tre test di GREP sul sorgente** sono caduti alla prima riscrittura che non
cambiava il comportamento, e sono stati riscritti come comportamento. Nona,
decima e undicesima volta in questa sessione.

---

## Turno 2 — gli orfani dichiarati

`DICHIARATI` in `scripts/orfani.py`: **nomi specifici, ciascuno firmato dalla
sua ragione**. Non una categoria — le categorie sono proprietà del codice, e
«dichiarato» è la decisione di una persona.

I tre firmati: `registry.pianifica`, `Governor.attivi`, `Gate.silenziati`.

### I vincoli, e come sono imposti

- **Una voce senza motivazione non entra**: `Dichiarato.__post_init__` alza se
  la ragione è sotto 30 caratteri. È la struttura a impedirlo, non una nota.
- **Un dichiarato che non è più orfano fa cadere la scansione**:
  `DichiarazioneScaduta`. Un'allowlist che sopravvive alla sparizione del
  proprio motivo diventa una lista di bugie in tre mesi.
- **`benigno` non cambia** per un dichiarato: resta la proprietà del codice che
  era. Chi legge deve poter vedere che `Governor.attivi` è ancora `solo_test` e
  che a toglierlo dai sospetti è stata **una persona**.

Cinque bocciature, cinque rosse.

### ⚠️ NON si arriva a zero: restano DIECI voci non spiegate

Il vincolo diceva di dirlo invece di chiudere il turno. Nessuna di queste è
stata firmata, perché firmarle vorrebbe dire dichiarare buono ciò che non ho
guardato abbastanza:

| nome | categoria | che cos'è |
|---|---|---|
| `Isteresi.conteggio` | `da_esaminare` | gestures, §14 — nessun riferimento, in nessun posto |
| `Mano.polso` | `da_esaminare` | gestures, §14 — idem |
| ~~`LinuxAudioIO.sta_riproducendo`~~ | — | ✅ **CHIUSO il 28 agosto**: la frase di §5.29 era falsa, §15 legge una bandiera della pipeline. Proprietà tolta; il difetto vero era altrove. Vedi `DUE-ORFANI-VERI.md` |
| `ConfirmBroker.pendenti` | `da_esaminare` | le conferme in attesa (invariante 3): JARVIS le sa e non le mostra |
| `TrackerMediaPipe.fps_camera` | `solo_test` | «la cadenza misurata all'avvio», usata da `scripts/bench_gestures.py` |
| `Supervisore.su_riavvio` | `solo_test` | ⚠️ **sospetto vero**: «T1 è morto per un guasto NON di autenticazione» — §5.6 |
| `build_router` | `solo_test` | il grafo LangGraph di §21.5. **È il turno 7 del piano**: usarlo dove pesa, o toglierlo |
| `da_pcm` | `solo_test` | «sorgente da byte già in memoria: per le prove» — probabile dichiarato, da guardare |
| `PhraseWake.frasi_vive` | `solo_test` | introspezione del riconoscitore vivo |
| `PhraseWake.registro` | `solo_test` | i trigger di questa sessione, in ordine |

Tre sembravano difetti veri (`sta_riproducendo`, `su_riavvio`, `build_router`) e
uno è già una fase del piano.

> ⚠️ **Aggiornato il 28 agosto.** Due dei tre sono stati guardati davvero, e
> **nessuno dei due era il difetto che sembrava**. `sta_riproducendo` non andava
> collegata ma tolta, e cercandone il lettore mancante è venuto fuori il difetto
> vero: la bandiera che §15 legge poteva restare alzata per sempre.
> `su_riavvio` non è un pezzo scollegato ma una **domanda di proprietà aperta**,
> e cablarla contraddirebbe la SPEC. Vedi `DUE-ORFANI-VERI.md`. **Non sono un lavoro di questo turno**, e metterli
in un'allowlist per far tornare il conto sarebbe esattamente ciò che l'elenco
firmato deve impedire.

Da 13 a 10 sospetti: le tre voci tolte sono le tre firmate, e nessun'altra.

---

## Che cosa NON è verificato

- ⚠️ **Nessuno di questi campi è mai stato letto in esercizio.** Tutta la
  misura di questa fase è sui test. La fase 2 è una sera davanti allo schermo,
  ed è lì che si saprà se questo foglio serve a qualcosa — è precisamente il
  motivo per cui è stato scritto.
- ⚠️ **Nessuna card è mai passata dal gate in esercizio**, e resta vero. Questa
  fase non lo cambia: rende leggibile il perché.
- ⚠️ Il caso «parla senza che il VAD apra» resta non coperto e non misurabile
  senza un microfono e una voce vera.
