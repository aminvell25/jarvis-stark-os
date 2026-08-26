# ① La voce, attraversata da un ingresso vero — e tre cose che nessuna lettura avrebbe trovato

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.2, §7.5, §7.6, ADR-004
**Rollback**: `dddb98e` · **Test**: 1337 verdi (erano 1320)

---

## Due premesse del mandato non reggevano

**ⓐ La voce era già accesa da tredici ore.** Il core legge
`~/.config/jarvis-os/settings.toml`, non `config/settings.toml`: il file del
repo dice `enabled = false`, quello vivo dice `true`. E il core in esecuzione
era di **tredici commit fa** — precedente a tutto il lavoro di oggi, il che
spiega perché `sessions/` fosse vuota: quel binario non aveva ancora
`registra_turno`.

**ⓑ La catena wake è quella giusta.** Verificata prima di accendere, come
richiesto: senza chiave l'oggetto Deepgram **non viene nemmeno costruito**
(`registry.py:25-31`), e `connect()` è raggiungibile solo oltre
`if trigger is None: continue` (`pipeline.py:293`). Nessun audio lascia la
macchina prima di un wake. Chiave assente → **Vosk + edge-tts**.

---

## Il difetto del turno, e il cancello che avevate dichiarato

> *«Se `conso/` non li vede, quello è il difetto del turno e viene prima di
> ogni misura di latenza.»*

**Scatta**, per due ragioni indipendenti che si nascondevano a vicenda.

### ① `Governor()` era costruito nudo — e mancavano tre cose

| | conseguenza |
|---|---|
| `dir_conso=None` | `conso/` **non veniva scritto mai**. La directory esisteva già — la crea `MemoryStore` — ed era calcolata una schermata più giù nello stesso costruttore |
| `su_advisory=None` | `t2_sospeso` e `t2_ripreso` **non raggiungevano nessuno** |
| i due tetti di §8 | `max_concurrent_t2` e `max_t2_spawns_per_hour` validati e **mai passati**. Coincidevano con le costanti del modulo: per questo era invisibile |

⚠️ **Devo correggere una mia affermazione.**
`docs/acceptance/I-TRE-ORFANI-VERI.md` ① dichiarava che la ripresa del Governor
«si annuncia». Era **falsa in produzione**: avevo collegato l'emettitore a
un'uscita che non esisteva — *la stessa famiglia di difetto dentro la
correzione che diceva di chiuderla*. I test passavano perché sono loro a
passare il callback. La correzione è in testa a quella sezione.

### ② Anche collegandolo, i «secondi» non erano secondi

Arrivavano `latenza_wake_ms` e `latenza_primo_suono_ms`: **due latenze**. Una
sessione da 12,5 s sarebbe comparsa come 0,00002 s. Adesso `Turno` porta
`secondi_ascoltati` e `secondi_detti`, contati sui **byte** del flusso ÷
`rate × 2` — ciò che un fornitore fattura.

### La misura, prima e dopo

| | prima | dopo |
|---|---|---|
| righe in `conso/` | **0** | 26 |
| `voce.consumo` | `{"secondi": {}, "sessioni": 0}` | `{"secondi": {"edge": 130.3, "vosk": 34.1}, "fallback_s": 164.4, "sessioni": 22}` |

---

## Le due latenze, separate — e sono due cose diverse

**§7.5 chiede ~30 ms per la frase-comando offline**, ed è un budget di
*elaborazione*. Va tenuto distinto dal tempo che passa dalla voce.

| | mediana | max | budget | esito |
|---|---|---|---|---|
| **elaborazione Vosk** (`latenza_ms`, 13 trigger) | **4,02 ms** | 8,61 ms | 20 ms (§7.5) | ✅ |
| **`parse()`** (6 turni) | **0,025 ms** | 0,049 ms | 10 ms (§7.6) | ✅ 200× margine |
| **risveglio a orologio** (`audio_in → wake`, 12 turni) | **584 ms** | 5,6 s | — | vedi sotto |

Il terzo numero è nuovo e non ha un budget in §7.5, perché §7.5 non lo misura.
È **bimodale**: 5 turni su 12 sotto i 50 ms, 7 sopra i 500 ms. La ragione è
strutturale — il riconoscimento avviene quando il gate VAD si **chiude**, cioè
240 ms dopo che si è smesso di parlare: quel numero contiene **la durata della
frase detta**. Non è latenza di sistema, è quanto si è parlato prima che la
frase-wake fosse decidibile.

⚠️ **`latenza_ms` non è mai stata la latenza di risveglio**, malgrado il nome:
è il costo di *una* `AcceptWaveform`. Il nome resta per compatibilità, con un
commento che lo dice.

---

## LA COSA CHE L'ATTRAVERSAMENTO HA TROVATO: tre frasi su quattro erano irraggiungibili

Tre righe consecutive del giro:

```
14:21:47  wake_trigger  azione=listen  frase=jarvis  latenza_ms=4.02
14:21:55  stt_audio     provider=vosk  secondi=7.68
14:21:55  t0            testo=silenzio tool=mute
```

`jarvis silenzio` **è una frase di wake configurata**, con azione `mute`. La
strada corta di §7.2 — nessuno STT, nessuna rete, ~5 ms — **non è stata
presa**: Kaldi ha chiuso l'enunciato su `jarvis`, che da solo è già una frase
valida, e il resto è finito nella trascrizione.

**7,68 secondi di ascolto invece di cinque millisecondi**, e l'esito giusto
**per caso**, perché «silenzio» è anche un comando T0. Se la frase fosse stata
`jarvis buonanotte` — e lo era, due volte — l'esito è stato *niente*.

Delle **quattro** frasi configurate, `jarvis` ne oscura **due**; e delle quattro
frasi dirette pronunciate (blocco C) **una sola** ha preso la strada corta
(`azione_diretta` = 1).

> **Una parola singola che è prefisso di altre frasi non produce falsi
> risvegli: rende irraggiungibili le frasi lunghe.** È l'argomento contro §7.2
> regola 1 al contrario di come me l'aspettavo, e viene da una misura.

`frasi_oscurate()` adesso lo dice all'ingresso **e a ogni ricarica a caldo** —
è scrivendo `settings.toml` che si crea un'ombra senza accorgersene. **Non
rifiuta**: §7.2 regola 1 non è imposta da nessuna parte, e imporla adesso
spegnerebbe l'unica frase che apre l'ascolto. La decisione resta a chi legge.

---

## I negativi

| | atteso | osservato |
|---|---|---|
| utterance con wake word | 14 | **13 risvegli** |
| frasi diritte (blocco C) sulla strada corta | 4 | **1** |
| turni senza testo dopo il risveglio | — | **6**, 47,6 s di ascolto per nulla |
| risvegli durante i 14 negativi + 60 s di silenzio | 0 | **0 righe di journal dopo l'ultimo turno** |
| `barge_in` | — | **0** |

**Zero falsi risvegli.** L'ipotesi coerente coi numeri — 12 `jarvis` osservati
contro 10 attesi, più 6 turni senza testo — è che i due `jarvis buonanotte`
siano stati decodificati come `jarvis` nudo, cioè **l'ombra**, non un falso
positivo. Non posso attribuirli uno per uno senza la Sua segmentazione, e lo
dichiaro invece di scegliere il conteggio che mi conviene.

⚠️ **`jarvis silenzio` era nel blocco A, e ha zittito JARVIS per le 24
utterance successive.** È un difetto del protocollo che ho scritto io. Ha però
ripulito la misura dei falsi risvegli: senza voce di JARVIS non c'è eco, e i
`barge_in` sono zero.

---

## Un difetto trovato dal primo giro, ed è mio

Il primo turno dal vivo ha stampato **`risveglio_ms=1787690347540.0`** —
cinquantasei anni. Sottraevo un `time.monotonic()` da `Trigger.quando`, che è
l'**orologio di parete**.

**Nessun test l'aveva visto**, perché i test costruiscono `Trigger` a mano e
passano due numeri della stessa scala. Terza volta in questo progetto che due
orologi finiscono nella stessa sottrazione, dopo `argomenti_a()` e
`estrai_locale()`.

Corretto con un campo `riconosciuto_a` monotòno, e con un test che guarda le
**due sorgenti nel sorgente** invece di due numeri finti.

E un secondo, nello stesso giro: `_con_apertura` sollevava su un trigger che
non fosse un dataclass, e tre test passano un finto — «turno_caduto» tre volte,
microfono aperto, nessuna azione. **Il guasto silenzioso, prodotto da una riga
aggiunta per misurare i guasti silenziosi.** Adesso non solleva mai.

---

## Una cosa che si vede solo adesso che il contatore esiste

Dopo `mute`, `conso/` ha continuato a registrare TTS: 18,07 s alle 14:23:16,
9,07 s alle 14:24:33. **Zittire JARVIS non ferma la spesa** — edge-tts sintetizza
comunque, e `play()` scarta il PCM a valle. Per un contatore di costi è il
comportamento giusto (il fornitore ha lavorato), ma è una cosa che nessuno
sapeva e che nessuna lettura del codice avrebbe reso evidente.

---

## Verifica

### ✅ Le bocciature

| perturbazione | esito |
|---|---|
| `Governor()` rimesso nudo | 3 rossi |
| latenze rimesse al posto dei secondi | 1 rosso |
| orologio di parete rimesso nel calcolo del risveglio | 1 rosso |
| confine di parola tolto da `frasi_oscurate` | 1 rosso |

### ✅ La suite

`1337 passed` (erano 1320).

⚠️ Un giro intermedio ha dato tre rossi in `eval_visual.py` con
`EADDRINUSE 127.0.0.1:5173`: un server di sviluppo lasciato acceso da un mio
giro precedente, non una regressione. Ucciso, e la suite è tornata verde —
diagnosticato prima di chiamarlo difetto, come il caso `TMPDIR=/tmp/jt`.

### ❌ NON verificato

- **L'attribuzione una-per-una delle 28 utterance.** Senza la Sua
  segmentazione non posso dire quale risveglio corrisponde a quale frase: i
  conteggi aggregati sono solidi, la mappa no.
- **Deepgram.** Chiave assente: apertura, primo parziale e secondi consumati
  restano **NON MISURABILI**. Ciò che è misurato è Vosk + edge-tts.
- **Il primo suono entro ~1 s** (§7.5). `FASE-03.md` lo dichiara già NON
  RAGGIUNGIBILE a ~4,4 s, e questo giro non lo rimisura.
- **La Sua pronuncia, nella Sua stanza.** §24 punto 3 chiede almeno 20
  ripetizioni; qui ce ne sono 28 di una sessione sola.
- **Il tasso di falsi risvegli su una giornata.** 60 s di silenzio non sono un
  campione: sono l'assenza di un allarme in un minuto.
