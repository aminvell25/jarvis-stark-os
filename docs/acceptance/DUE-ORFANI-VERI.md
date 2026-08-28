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

### ✅ E `su_riavvio` NON è più un orfano: è stata tolta — 28 agosto 2026

Decisa la domanda 1 dal Signore («resta vivo in `degraded_llm`, non uscire col
42»), è caduto il blocco che impediva di decidere la 2. La risposta, dopo tre
confutazioni indipendenti e con le misure rifatte da me:

> **La degradazione non-auth la possiede `ClaudeT1`, per intero** — processo,
> `returncode`, `stderr`, classificazione, freno, riavvio, reiniezione e voce.
> Il `Supervisore` ne tiene il **referto**: il bus, `stato_doctor()` e il
> contatore di vita. È l'unica metà che T1 non può avere.

`su_riavvio` non è stata riciclata come canale del referto: **decideva e
agiva**, cioè faceva due volte ciò che T1 fa già, e con gli strumenti
sbagliati — `Supervisore.classifica` non legge nemmeno il proprio parametro
(misurato: `classifica("authentication_failed")` → `transient`). Al suo posto
c'è `riferisci(EventoT1)`, che conta, registra e pubblica, e **non parla**.

Sono cadute con lei, senza lettori: `classifica`, `puo_riavviare`,
`_rimetti_i_fatti`, `_annuncia`, `_quando`, `FRASE_TRANSIENT`, `FRASE_RIPETUTI`,
i campi `fatti_fissati` / `reinietta` / `orologio`, e le due costanti della
finestra. ⚠️ **Le loro proprietà sono migrate prima della cancellazione**, in
`tests/test_t1_non_risorge_in_silenzio.py`: erano l'unica specifica eseguibile
della classe `repeated`, e cancellarle sarebbe stata la perdita, non la
potatura. La migrazione è verificata perturbando `ClaudeT1` — se le prove
fossero decorative, resterebbero verdi.

### Che cosa ha trovato la strada, facendola

- **Il doctor non sapeva niente**: dopo tre riavvii veri, `nominal, riavvii: 0`,
  zero advisory. §5.6 a ruoli invertiti.
- **Un buco di §5.6 sull'altra strada di rilevamento**: §5.6 vede solo lo
  stream, ma un token che scade fra due turni fa **morire il processo**.
  Misurato: T1 lo diceva a voce, e insieme zero advisory, zero uscite,
  `stato_doctor()` a `nominal` — cioè `jarvis doctor` avrebbe detto «auth ok»
  col token scaduto, il difetto che la rev 5.29 dichiara chiuso.
- **`ClaudeT1` non era conforme ad ADR-003**: finestra di 5 minuti invece di 10,
  soglia al quarto guasto invece che al terzo, orologio non monotono. E il test
  che la fissava passava per caso.
- **Il cancello dell'auth si chiudeva sullo stato**, quindi una degradazione
  non-auth spegneva §5.6 — e la decisione di restare vivi lo rendeva permanente.

### ✅ E il punto che restava aperto è chiuso — 29 agosto 2026

⚠️ Era: «`classifica` riceve un solo argomento, e `stderr` è un `PIPE` che
nessuno legge». Guardato, e **la diagnosi era giusta a metà**: non serviva un
processo `claude` vero, bastava un figlio qualunque.

**Il tubo non si riempie come temevo** — asyncio lo pompa da solo nel proprio
`StreamReader` anche senza lettori. Ma il blocco arriva lo stesso, più in là:
esaurito quel buffer il controllo di flusso mette in pausa la lettura, il tubo
si riempie e il figlio si ferma sulla `write`. **Misurato**:

    200 000 byte su stderr   il figlio arriva in fondo
    300 000 byte su stderr   ⚠️ BLOCCATO

e con un `ClaudeT1` vero, A/B sul solo lettore:

    senza lettore   ⚠️ BLOCCATO   (8 s, il timeout della prova)
    con lettore     risponde      11 ms

**E il secondo difetto era il più caro.** `classifica` ha tre criteri per
l'autenticazione e ne riceveva uno. Misurato su un figlio che muore dicendo
`Error: Unauthorized - token expired` con `returncode 1`:

    classifica(rc, stderr) -> auth        con la cura
    classifica(rc, "")     -> transient   com'era

Un token scaduto preso per un guasto passeggero, e **riprovato in ciclo** —
esattamente ciò che §5.6 esiste per vietare.

