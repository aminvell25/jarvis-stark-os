# `sta_riproducendo` e `su_riavvio` — nessuno dei due era ciò che sembrava

**Base:** `3974e14`, 1770 test verdi · **Commit:** `085a13e`, `303fd6c`,
`e5ac63d` · **Rollback:** `3974e14`

Due orfani rimasti dalla fase 1, etichettati «sospetti veri». Guardandoli
davvero, **nessuno dei due era il difetto che sembrava** — e cercandone il
chiamante mancante ne sono venuti fuori quattro che sembravano niente.

Metodo: dieci agenti in sola lettura (quattro letture indipendenti, sei
confutazioni con lenti diverse, due sintesi), poi **ogni fatto decisivo
rimisurato da me** prima di scrivere una riga. Tutte e sei le confutazioni
hanno respinto la proposta che stavano esaminando; è il motivo per cui questo
turno non contiene nessuna delle cure che sembravano ovvie all'inizio.

---

## ① `LinuxAudioIO.sta_riproducendo` — non andava collegata, andava tolta

Quattro punti scritti — il commento in `linux_audio.py`, la riga di changelog
della rev 5.29, un atto di accettazione e due docstring di test — dicevano la
stessa frase: *«le regole 2 e 3 di §15 leggono proprio quello»*.

**È falsa.** La catena di §15 è

    VoicePipeline.sta_parlando → Engine._voce_sta_parlando
    → MotoreNews._parla_adesso → Contesto → Gate.valuta

e `LinuxAudioIO` non compare in nessun punto. Il codice non era rotto: era rotta
la frase che lo giustificava.

E non deve comparirci, per tre ragioni indipendenti (una per lente):

| lente | perché no |
|---|---|
| invariante 29 | un processo `pw-play` aperto non vuol dire «si sente»: `imposta_volume(0)` a metà frase lo lascia aperto con dentro campioni a zero. Un `WindowsAudioIO` che applica il guadagno sul PCM darebbe a §15 una risposta diversa a parità di comportamento udibile |
| due produttori | riallinearsi al processo a ogni blocco **disfa** il barge-in, che quel processo lo uccide apposta |
| i test | il finto condiviso `AudioFinto` non chiude le sue uscite su `interrupt()`: il codice nuovo leggerebbe un campo che il finto tiene bugiardo, e la suite non se ne accorgerebbe |

**Tolta.** La regola del volume 0 resta e cambia la giustificazione: non si paga
un processo per scrivere silenzio — 85 ms di processo per 29 ms di audio,
misurati e già scritti in `AudioIO.apri_uscita`.

### Ma cercandone il lettore è venuto fuori il difetto vero

`VoicePipeline._sta_parlando` si abbassa in due posti, e in entrambi
l'abbassamento stava **dopo** un `await`, in sequenza:

    parla()       await uscita.chiudi()   →  self._sta_parlando = False
    interrompi()  await ...interrupt()    →  self._sta_parlando = False

`chiudi()` attende che la coda del dispositivo si svuoti. Misurato:

| scenario | prima | dopo |
|---|---|---|
| annullato dentro `chiudi()` | `sta_parlando=True` | `False` |
| `chiudi()` solleva `OSError` | `sta_parlando=True` | `False` |
| `interrompi()` con un TTS che solleva | `sta_parlando=True` | `False` |

Col lucchetto della voce **già libero**: il turno è morto e la bandiera è
rimasta alzata. Da lì §15 regola 2 risponde «sta parlando» a ogni giro dei
feed — **nessuna card passa più, mai**.

### ⚠️ E lo strumento scritto il giorno prima non lo vede

`MotoreNews.conoscibilita()` dichiara i tre campi `noto`. E ha ragione: il
produttore c'è, non ha sollevato, ha risposto un `bool`. **Il campo dice un
fatto, e il fatto è falso.**

Quello strumento distingue un produttore che *manca* da uno che è *rotto*. Un
produttore che **mente** è `noto` come qualunque altro, e deve esserlo: dire il
contrario vorrebbe dire un secondo produttore che controlla il primo. È il
limite dichiarato di `conoscibilita()`, ed è la ragione per cui la garanzia sta
in un `finally` annidato e non nell'osservabilità. Fissato da un test suo.

---

## ② `Supervisore.su_riavvio` — la strada che GIRA era rotta in tre punti

L'ipotesi di partenza («è la più vecchia di due implementazioni») era falsa: il
Supervisore è di **sette giorni più recente**. Ma la domanda che apriva era
giusta, e la risposta sta altrove — in `ClaudeT1.riavvia_dopo_guasto`, la strada
che gira davvero.

| difetto | prima | dopo |
|---|---|---|
| il riavvio riuscito lasciava T1 morto (`_degrada` comincia con `stop()`) | `vivo=False` | `vivo=True` |
| la guardia di `ask()` al turno dopo una degradazione | `False` → sessione vuota in silenzio | `True` → ripassa dal riavvio |
| «ho conservato le Sue preferenze» | `_fatti_fissati()` → `[]` | cablato dalla radice |

Il primo è il peggiore: il recupero di ADR-003 riavviava T1, gli rimetteva i
fatti fissati, **poi lo uccideva**, e annunciava successo. Il secondo è
l'amnesia che ADR-003 esiste per vietare, un turno dopo, per la strada più
frequente di tutte — il timeout.

### ⚠️ E `su_riavvio` resta un orfano. La decisione non è mia

Cablarla **contraddice la specifica**, e in questo progetto nessun invariante e
nessuna dichiarazione si emendano dentro un turno di implementazione. Perciò il
turno si ferma qui e lo dice.

Che cosa succederebbe cablandola, misurato:

- `Supervisore.su_riavvio` chiama `self.esci(USCITA_RIPETUTI)` — **codice 42**,
  cioè il core esce. Ma §5.6 e §16.1b dichiarano che in `degraded_llm` restano
  vivi T0, telemetria, file manager e interfaccia. **O parte il 42 contro la
  SPEC, o si sdoppia il campo `esci` e un test verde diventa rosso**: non esiste
  la variante indolore;
- `Supervisore.classifica(motivo)` **non legge il parametro `motivo`**.
  Misurato: `classifica("authentication_failed")` → `'transient'`, mentre
  `ClaudeT1.classifica(41, "")` → `AUTH`. Delegare la classificazione spegne il
  rilevamento auth *dalla morte del processo*, che è il caso di §5.6;
- l'ordine `repeated` → `auth` acceca il ramo auth: dopo tre cadute,
  `su_evento` con un evento di autenticazione vero produce **zero frasi, zero
  advisory, zero uscite**. Oggi è irraggiungibile solo perché `su_riavvio` non
  gira; sarebbe il cablaggio ad aprirlo.

> ## ✅ LA DOMANDA 1 È DECISA — 28 agosto 2026
>
> > «resta vivo in `degraded_llm`, non uscire col 42»
>
> Implementata in `e139278`: `USCITA_RIPETUTI` tolto, la unit dice
> `RestartPreventExitStatus=41`, §16 ha una riga in più. **Il primo dei tre
> punti qui sotto non descrive più nessuna alternativa.**
>
> E implementandola sono venuti fuori due residui che la decisione rende
> visibili, perché `degraded_llm` non-auth diventa uno stato in cui si RESTA:
> `stato_doctor()["azione"]` diceva «esegui `claude` e poi /login» per qualunque
> degradazione, e `jarvis doctor` stampava «T1 auth: sessione scaduta» per una
> sessione che non era scaduta. Corretti tutti e due.
>
> **La domanda 2 resta aperta**, ed è quella qui sotto.

**Le due domande poste allora, e sono due:**

1. per un guasto non-auth ripetuto, il core **esce col 42** o **resta vivo** in
   `degraded_llm`? La decisione formale (ADR-003, opzione A) non nomina nessun
   codice d'uscita; `USCITA_RIPETUTI` esiste nel codice e non è nominato da
   nessuna unit systemd nel repo;
2. chi possiede la degradazione **non-auth** — il `Supervisore`, che ha la bocca
   (`agent.advisory`, `stato_doctor()`, il codice d'uscita), o `ClaudeT1`, che
   ha le mani (il processo, la classificazione dal `returncode`, i fatti)?

Finché non è deciso, `su_riavvio` **non entra in `DICHIARATI`**: quell'elenco
dice «guardato, e va bene così», e questo è «guardato, e serve una decisione».
Metterlo lì sarebbe la bugia che il meccanismo esiste per impedire.

---

## Misura

| | prima | dopo |
|---|---|---|
| test | 1770 | 1782 |
| sospetti dello scanner | 10 | 9 |
| bocciature eseguite | — | 11 rosse, 2 non discriminavano e sono state corrette |

Le due bocciature che non discriminavano hanno trovato altrettanti buchi veri:
un test che partiva da uno stato non degradato, e un test che non esisteva.

## Che cosa NON è verificato

- ⚠️ **Nessun processo `claude` vero è stato avviato**, e nessun `pw-play`.
  Tutte le misure usano processi finti e la logica vera dei moduli.
- ⚠️ **La larghezza reale della finestra** in cui la bandiera può incastrarsi:
  quanto duri lo svuotamento della coda su una risposta vera non è misurato.
  Per la conseguenza *permanente* la domanda non si pone: dopo, ogni giro è
  dentro.
- ⚠️ **La frequenza reale dei timeout di T1**, che è il ramo che rende grave il
  rientro silenzioso.
- ⚠️ **Una divergenza dichiarata e non corretta**: a volume 0 la pipeline alza
  `_sta_parlando` mentre l'altoparlante è muto. Non si corregge, e la ragione è
  che a volume 0 il comportamento conservativo è quello giusto — il Signore ha
  zittito JARVIS, e una card in meno è ciò che ha chiesto.
- ⚠️ **`stderr` di T1 è aperto (`PIPE`) e non viene letto in nessun punto.**
  Due dei tre criteri di rilevamento auth di `ClaudeT1.classifica` leggono lo
  stderr, quindi sulla strada viva sono irraggiungibili — e un tubo mai letto
  può riempirsi e bloccare il figlio. Non misurato qui: è un turno suo.
