# §7.6 — i cinque intenti che JARVIS riconosceva e non eseguiva

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.6, §16.1b · **Rollback**: `bedb995`
**Test**: 1253 verdi (erano 1223)

---

## Il difetto

`set_volume`, `mute`, `brief_me`, `needs_attention` e `doctor` erano nella
grammatica T0 **dalla Fase 3** e nel corpus delle frasi etichettate.
`esegui_t0` li rifiutava con «non è né un'azione della scrivania né un tool
dell'allowlist»: JARVIS riconosceva la frase, scriveva una riga nel log, e non
succedeva niente.

È il guasto più visibile all'uso, perché dall'esterno è **indistinguibile da
«non mi ha sentito»** — e la reazione naturale è ripetere la frase più forte.

Un test lo sapeva e lo diceva da tempo: `test_le_due_strade_sono_due_allowlist`
li elencava come «noti e senza destinazione». Elencare non è chiudere.

**Oggi quell'insieme è vuoto**, e il test resta perché il suo mestiere non è
elencarli: è accorgersi del prossimo.

---

## ① Il volume è DI JARVIS, non del sistema

`CLAUDE.md` apre dicendo che fuori dalla sua finestra non tocca nulla, e il
mixer di PipeWire è fuori dalla sua finestra. **«Volume 40» vuol dire che
JARVIS parla più piano**, non che abbassa la musica che sta ascoltando — che è
anche ciò che si intende dicendolo.

Implementato come **guadagno sul PCM** che JARVIS riproduce: non chiede
permessi, non tocca il mixer, sparisce quando il processo finisce. Sta in
`core/platform/base.py` come parte del Protocol `AudioIO` (invariante 29), con
l'implementazione in `linux_audio.py`.

Tre proprietà misurate:

- **A volume pieno il PCM non si tocca** — `_con_guadagno` restituisce lo
  stesso oggetto. Il caso normale non paga niente, e il barge-in di §7.4 ha
  200 ms di budget che non vanno spesi a moltiplicare campioni per uno.
- **A volume zero non si riproduce affatto.** Mandare zeri a PipeWire terrebbe
  `sta_riproducendo` a vero per tutta la frase, e le regole 2 e 3 di §15
  leggono proprio quello: JARVIS resterebbe «occupato a parlare» mentre è muto.

  > ⚠️ **CORRETTO il 28 agosto 2026.** La regola è giusta, questa
  > giustificazione era falsa. §15 legge `VoicePipeline.sta_parlando`, una
  > bandiera della pipeline: `LinuxAudioIO` non è mai stato nella catena, e
  > `sta_riproducendo` non aveva un solo lettore in tutto il repository — è
  > stata tolta. La ragione vera del ritorno anticipato è che non si paga un
  > processo per scrivere silenzio (85 ms di processo per 29 ms di audio,
  > `core/platform/base.py`). Vedi `docs/acceptance/DUE-ORFANI-VERI.md`.
- **Un'iperbole satura**, non fallisce. Il corpus T0 contiene già
  `("volume 250", ..., 100)`.

E il contrario del muto, che **non esisteva**: si poteva zittire JARVIS e non
riaccenderlo a voce. `unmute` torna al livello di prima; senza un «prima», a un
livello udibile — riattivare l'audio e restare muti sarebbe la risposta
sbagliata.

### `side_effect=False`, e perché

§6.2 esiste per le operazioni irreversibili sui file di chi usa il sistema. Il
volume si annulla dicendo un altro numero, non tocca il disco, non esce dal
processo. Una conferma qui sarebbe attrito senza protezione.

`gesture_allowed=False` **è invece una decisione, non un obbligo**: l'invariante
27 vieta le gesture solo sui `side_effect=True`. Una mano che passa davanti alla
telecamera e zittisce JARVIS è il genere di sorpresa che §14 evita.

---

## ② `doctor` — §16.1b lo chiedeva a voce, e non rispondeva

`jarvis doctor` esisteva come comando di terminale dalla Fase 1. §16.1b dice
«stesso contenuto sul topic `agent.advisory` e nel pannello telemetria, e
raggiungibile a voce con la frase T0 *come stiamo*». La frase c'era,
l'esecutore no.

Adesso va **sul bus e a voce**. A voce si dice solo ciò che non è `ok`: leggere
quindici righe verdi ad alta voce sarebbe inutilizzabile.

---

## ③ I meta-comandi passano da T2 e non aspettano

§7.6: «non chiedono UNA COSA, chiedono lo STATO. Frase deterministica (T0) che
innesca un fan-out di subagent (T2)».

La frase è deterministica, la risposta no: è un compito lungo e va in T2, che
passa dal Governor come ogni spawn (invariante 16).

⚠️ **Non si attende.** Un briefing costa decine di secondi ed `esegui_t0` sta
sul percorso della voce: risponde subito «un momento, Signore», e la risposta
arriva quando arriva. Bloccare lì vorrebbe dire un JARVIS muto per mezzo minuto
dopo una domanda.

E un meta-comando che tace è indistinguibile da uno mai partito: se lo spawn
fallisce o torna vuoto, **lo dice**.

---

## Un difetto trovato dai test durante il lavoro

Costruire l'`AudioIO` nel costruttore ha rotto
`test_la_caduta_finisce_nello_SNAPSHOT`, che sostituisce la fabbrica
`platform_audio` per simulare un microfono che muore: la sostituzione arrivava
**dopo** la costruzione, e l'oggetto era già quello vero.

Corretto con una **proprietà pigra**: i tool ricevono un getter, non l'istanza,
e l'oggetto nasce alla prima richiesta. Un solo `platform_audio()` in tutto il
file, e due consumatori che passano da lì — perché due istanze vorrebbero dire
un guadagno impostato su una che non riproduce niente.

---

## Verifica

### ✅ Le bocciature

- **Due istanze di `AudioIO` invece di una**: `test_l_AudioIO_e_UNO_SOLO` rosso.
- **Tolta la guardia del volume zero**: rosso — **ma solo dopo aver riscritto
  il test.**

⚠️ **La prima stesura non discriminava.** Asseriva `sta_riproducendo is False`
*dopo* `await play(...)` — ma `play` attende la fine del processo, quindi a quel
punto è falso in ogni caso. Neutralizzando la guardia il test restava verde.
Riscritto per guardare ciò che conta: che il processo **non venga avviato**, con
il controllo del controllo (a volume udibile il processo parte).

> **Quarta occorrenza in questo arco** di «criterio vero per il motivo
> sbagliato» (§11.7 regola 4), e tutte e quattro trovate eseguendo la
> bocciatura.

### ✅ La suite

`1253 passed` (erano 1223). Tre test hanno dovuto cambiare, e ognuno per una
ragione vera: due conteggi dell'allowlist (22 → 25 tool) e l'esempio di
«intento senza destinazione», che usava `mute` — adesso ne ha una, e lasciarlo
lì avrebbe reso quel test verde per il motivo sbagliato. Sostituito con un
intento che non esiste, più il controllo del controllo su `mute`.

### ❌ NON verificato

- **Il volume dal microfono.** Provato come tool e come intento, non
  pronunciato.
- **L'attenuazione all'orecchio.** Il PCM è misurato campione per campione; che
  40 suoni «più piano quanto ci si aspetta» non è una misura che ho fatto.
- **`brief_me` e `needs_attention` con uno spawn vero.** Il percorso è provato
  fino allo spawn; il contenuto della risposta dipende dal modello e non l'ho
  ascoltato.
- **`doctor` a voce con un sistema davvero malato.** Provato con i controlli
  reali di questa macchina, che oggi sono quasi tutti verdi.
