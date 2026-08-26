# §5.5 — il giro della memoria era rotto in tre punti insieme

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.5 · **Rollback**: `92c0ec4`
**Test**: 1274 verdi (erano 1253)

---

## Tre pezzi, e si nascondevano a vicenda

La scansione degli orfani ne aveva segnalati tre nella memoria. Presi uno per
uno sembravano tre dimenticanze indipendenti. Sono una catena rotta in tre
punti, e ogni rottura mascherava la successiva:

```
turno vocale  ──✗──>  sessions/  ──✗──>  Consolidatore  ──>  topics/  ──✗──>  T2
     ①                                        ②                              ③
```

**① `MemoryStore.registra_turno()` non aveva un chiamante.** `sessions/`
restava vuota: nessuna conversazione è mai stata scritta.

**② `Consolidatore.esegui()` non aveva un chiamante.** §5.5 dice «gira alle
04:00 via scheduler»; lo scheduler non c'era. La classe era scritta per intero
— advisory compresi, e con la tensione dell'invariante 3 già sciolta e
dichiarata in `FASE-04.md`.

**③ `ContextPruner.contesto_per_t2()` non aveva un chiamante.** Ogni spawn T2
ripartiva senza sapere niente.

Il punto che rende la catena istruttiva: **anche azionando il consolidatore non
avrebbe trovato niente da consolidare**, perché il registro delle sessioni non
lo scriveva nessuno. Due difetti che si coprono a vicenda non si trovano
guardandone uno.

---

## ① Il turno finisce nel registro

Nel `_voce_su_turno`, accanto al conteggio di ADR-004 e agli argomenti di §15.

**Un giorno è un file**, non un avvio del core: un core riavviato tre volte
spezzerebbe una conversazione in tre file che il consolidatore riassumerebbe
separatamente. Un turno in cui non ha parlato nessuno non si scrive. E un disco
pieno **non zittisce JARVIS**: siamo sul percorso della voce.

### ⚠️ Da oggi la trascrizione va su disco, e prima non ci andava

Non l'audio. §18.3 dice che l'audio senza frase nota non lascia mai la macchina
e non viene salvato, e **resta vero**. Il testo sì, ed è ciò che §5.5
prescrive: `sessions/` è nella sua pianta con la dicitura «cronologia grezza».
Sta in `memory_data/`, sotto il controllo dell'utente, e si cancella
cancellando il file.

È un cambiamento di cosa persiste, e va detto in chiaro invece di comparire.

---

## ② Il consolidatore gira alle 04:00

Un ciclo che dorme fino alla prossima ricorrenza dell'ora. L'aritmetica sta in
un metodo statico a parte — `_secondi_fino_alle` — perché è l'unica parte
misurabile senza aspettare una notte, e ha un test parametrizzato su quattro
ore.

A sessioni vuote **non spawna niente**: il consolidatore parla con un modello, e
un modello costa. E se la quota è finita **lo annuncia** (R33, §16): la mattina
dopo si deve sapere perché la memoria non è stata consolidata.

Non ha un interruttore nelle impostazioni perché non ne ha uno in §5.5: è parte
della memoria, come la potatura.

---

## ③ Il contesto arriva a T2 — e collegandolo è venuto fuori un difetto

I meta-comandi di §7.6, aggiunti nel commit precedente, sono il primo
consumatore naturale: un briefing senza memoria è un briefing su niente.

⚠️ **Non è duplicare il contesto di T1** (invariante 17): T1 tiene la *sua*
conversazione; questo è un processo effimero che nasce senza niente. Il divieto
è di gestire due volte lo stesso contesto, non di dare a un estraneo ciò che
serve per capire la domanda.

### Il difetto: `contesto_per_t2` non poteva funzionare

Passava il **compito intero** a `cerca()`, che fa una ricerca per sottostringa.
Un compito è un prompt di centinaia di caratteri e non è sottostringa di
niente: la funzione **non poteva restituire nemmeno un topic, mai**. Il contesto
era sempre e solo i fatti fissati.

Finché nessuno la chiamava, il difetto non aveva modo di manifestarsi. È
l'argomento più forte a favore del collegare gli orfani invece di lasciarli
lì: un pezzo che nessuno usa non è neutro, è **non misurato**.

Corretto cercando **parola per parola** e ordinando per quante parole distinte
del compito il topic tocca. `cerca()` resta com'è: il tool `recall` di §13 le
passa una parola sola, dove la sottostringa è il comportamento giusto, e
cambiarla avrebbe rotto quel caso per aggiustare questo. Entrambi i
comportamenti hanno un test.

---

## Verifica

### ✅ Le tre bocciature, una per giunzione

| perturbazione | esito |
|---|---|
| tolta la registrazione del turno | 1 rosso |
| tolto l'avvio del consolidatore | 1 rosso |
| rimessa la ricerca col compito intero | **3 rossi** |

Ogni perturbazione applicata con un `assert` sulla presenza della stringa prima
di sostituire, e annullata con copie in scratch.

### ✅ La suite

`1274 passed` (erano 1253).

Un test ha dovuto cambiare, e per una ragione vera:
`test_un_meta_comando_VUOTO_si_annuncia` leggeva i **primi 2000 caratteri** di
una funzione che è cresciuta col contesto di §5.5. Una finestra fissa su un
sorgente è una misura che invecchia da sola: adesso legge la funzione intera.

### ❌ NON verificato

- **Una notte vera.** Il ciclo è provato sull'aritmetica dell'attesa e sul
  consolidamento chiamato a mano; nessun core ha attraversato le 04:00.
- **Il consolidamento con un modello vero.** Provato con un T2 finto: quel che
  scrive nei topic dipende dal modello, e non l'ho letto.
- **Il turno dal microfono.** La registrazione è provata costruendo un `Turno`,
  non parlando.
- **Il costo di una giornata di sessioni.** Un file JSONL al giorno cresce, e
  non c'è nessuna rotazione: va guardato fra un mese.
