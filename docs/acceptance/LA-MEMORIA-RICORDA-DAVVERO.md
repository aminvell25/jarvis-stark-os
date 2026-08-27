# La memoria aveva la metà in uscita vuota — e tre difetti la tenevano così

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.5, §7.6
**Rollback**: `fa75ebd` · **Test**: 1477 → **1491**

---

## La misura che ha aperto il turno

```
~/.local/share/jarvis-os/memory_data/
  sessions/     2 file      ← la cronologia grezza, funziona
  conso/        2 file      ← i secondi di audio, funziona
  topics/       0 file
  initiatives/  0 file
```

Su un sistema in esercizio da giorni. `registra_iniziativa` ha **un solo
chiamante**: il consolidamento notturno — cioè l'unica iniziativa che JARVIS
sappia prendere è mettere in ordine i propri appunti, e non l'aveva mai fatto.

Nel journal di sette giorni: solo `grado_acceso grado=consolidamento ora=4`, il
timer **armato**. Mai uno scatto.

---

## ① Un'attesa invece di un recupero

`await asyncio.sleep(secondi_fino_alle(4))` non sopravvive a un riavvio del
processo: riparte da zero. Misurato sul journal: **27 riavvii in tre giorni**.

Adesso il consolidamento **recupera** all'avvio: `Consolidatore.saltato()` legge
il timbro su disco, e se una notte è passata si consolida subito.

**`PERIODO_S = 24 h` non è scelto**: §5.5 dice «ogni notte», quindi il periodo è
un giorno. Un test lo impone.

**Orologio di parete, non `monotonic`**: il timbro si legge fra un avvio e
l'altro, e `monotonic` riparte a ogni riavvio — cioè proprio nel caso che questa
funzione esiste per coprire.

**E il freno è su disco.** `_segna_run()` timbra anche quando non c'era niente da
fare, quindi un riavvio ogni dieci minuti non consolida ogni dieci minuti. Un
contatore in memoria si azzererebbe col processo: lo stesso difetto con un nome
nuovo.

⚠️ **Una guardia mia, scritta e tolta.** Avevo aggiunto `if ultimo <= ora else
False` contro un orologio spostato all'indietro. La bocciatura ha mostrato che
toglierla **non rompeva niente**: la differenza diventa negativa e non può
superare `PERIODO_S`. Un controllo che non cambia nessun esito promette a chi
legge una protezione che non c'è.

## ② Due T2 costruiti e azzerati nella stessa funzione

Il recupero è caduto subito: `'NoneType' object has no attribute 'esegui'`.

`Engine.__init__` costruisce `_t2_meta` e `_t2_conso`… e **centoquaranta righe
dopo, nella stessa funzione**, li rimette a `None`. Il commento diceva
*«costruito nella radice di composizione, non qui»*: era vero prima che la
composizione venisse spostata dentro `__init__`, e nessuno ha tolto
l'azzeramento.

> **`brief_me` e `needs_attention` non hanno mai potuto spawnare nulla.**

`_meta_comando` si arrende alla prima riga con «T2 non composto», e lo fa **dal
commit che li ha collegati** — `92c0ec4`, *«nessun intento senza strada»*. La
strada c'era, e finiva su un null.

`docs/acceptance/NESSUN-INTENTO-SENZA-STRADA.md` dichiarava quei due «mai
eseguiti con uno spawn vero» attribuendolo al non aver ascoltato. Il motivo
vero era un altro: **non potevano**.

L'ho trovato solo perché il mio `_t2_conso` era finito nella stessa trappola il
giorno stesso.

## ③ Il motivo di un fallimento non arrivava nel journal

`log.warning("consolidamento_advisory", motivo=motivo)` — senza `**extra`. Il
`dettaglio` andava **solo** sull'advisory, che vive sul socket. Con la scrivania
scollegata spariva.

Ed è sparito davvero: *«sessione 2026-08-27 non consolidata»*, e **nessuno può
più dire perché**. Il journal è la cosa che sopravvive.

---

## Verifica

### ✅ La prima notte attraversata — dal vivo

```
03:51:17  consolidamento_recupero   perche="una notte e' passata senza consolidamento"
03:51:17  t2_avviato                etichetta=consolidamento-2026-08-26
03:52:02  topic_scritto             .../topics/sessione-2026-08-26.md
03:52:27  consolidamento_fatto      topic=1 turni=41
```

```
topics:      1 file   (era 0)
initiatives: 1 file   (era 0)
```

L'iniziativa registrata: **38 turni, 0,153 USD, 44,4 s**.

E il riassunto non è generico — ha isolato **da solo** il difetto STT della sera
prima:

> *«Riconoscimento vocale (STT) mostra errori ricorrenti sulla frase "apri
> pannelli telemetria"… bug di riconoscimento da indagare, non un problema di
> logica applicativa.»*

### ✅ Le cinque bocciature

| perturbazione | esito |
|---|---|
| via il recupero all'avvio | 2 rossi |
| `PERIODO_S` diventa un numero scelto | 1 rosso |
| il timbro non si scrive a vuoto | 1 rosso |
| torna l'azzeramento di `_t2_conso` | 3 rossi |
| il motivo non arriva nel journal | 1 rosso |

### ⚠️ Il togli-commenti ora toglie anche le docstring

Sesta volta che un mio test legge una spiegazione invece del codice: la
docstring di `saltato()` nomina `monotonic` per dire perché **non** si usa.

### ❌ NON verificato

- **Perché la sessione `2026-08-27` non si sia consolidata.** L'advisory è
  scattato e il motivo è perso — è esattamente il difetto ③, e la prossima
  volta sarà leggibile. Non ho rieseguito apposta: costerebbe due spawn dal
  budget del Signore per una risposta che il prossimo giro darà gratis.
- **Il ciclo delle 04:00 vero.** Il recupero non lo sostituisce: chi lascia la
  macchina accesa deve avere il consolidamento all'ora giusta. Nessun core ha
  ancora attraversato le 04:00 restando vivo.
- **`brief_me` con lo spawner ora funzionante.** Il null è tolto e i test lo
  impongono, ma nessuno ha ancora chiesto un briefing a voce.
