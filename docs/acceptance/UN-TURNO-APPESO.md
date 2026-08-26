# «Jarvis non mi sente» — un turno che non finisce, e il battito cieco

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.3, §7.5, §16
**Rollback**: `659a37c` · **Test**: 1457 → **1466**

---

## Colto sul fatto

```
00:55:19  wake_trigger      frase=jarvis  latenza_ms=3.61
00:55:20  cattura_avviata   pid=902471
00:55:27  cattura_fermata
          ...poi NIENTE, per quattro minuti

pw-record 888553   anon_pipe_write   0 byte in 3 s
snapshot           "microfono": "aperto"
```

È **lo stesso guasto dell'ora di sordità del 26 agosto**, che allora non ero
riuscito a spiegare e avevo dichiarato ignoto. Questa volta l'ho visto mentre
succedeva.

---

## Tre difetti incastrati, e il terzo nasconde il primo

**① Lo STT non aveva un tetto.** `async for grezzo in ws`: un socket che tace
senza chiudersi aspetta per sempre. `core/providers/stt_deepgram.py` non
conteneva **un solo** `wait_for` — mentre il TTS gemello ne ha uno dal 26
agosto, messo per lo stesso identico motivo sullo stesso identico tipo di
socket. Ho corretto un gemello e non ho guardato l'altro.

**② Il danno non resta nel provider.** `_su_trigger` è atteso **dentro**
l'`async for` del microfono: un turno appeso ferma il ciclo audio, `pw-record`
riempie la pipe e si blocca in `anon_pipe_write`. JARVIS diventa sordo.

**③ Il battito era cieco esattamente nel caso che lo produce.** La bandiera
`_in_turno` — scritta il giorno prima perché il battito non gridasse al lupo a
ogni conversazione — gli impediva anche di vedere una conversazione che non
finisce. **L'ho scritta io, e non le ho dato una fine.** Il documento di ieri
la difendeva con queste parole: *«un turno può durare fino al timeout di T1»*.
T1 il tetto ce l'ha; lo STT no, e nessuno aveva verificato quale.

---

## I due numeri, e perché nessuno dei due è scelto

**`stt_deepgram.TETTO_RECV_S = 20.0`** — lo stesso del TTS, e non per simmetria
estetica: stesso tipo di socket, stesso fornitore, stessa rete. La misura che
ha prodotto quel venti — *«il primo suono sta fra 3,6 e 14,0 s su questa
rete»* — descrive anche questo canale.

**`TETTO_TURNO_S = 8 + 20 + 90 = 118 s`** — la somma dei tetti **già
dichiarati** degli stadi che possono stallare: la cattura
(`_trascrivi(limite_s=8.0)`), la `recv` dello STT, una riga di T1
(`ClaudeT1.ask(timeout=90.0)`). Nessuno di quei numeri nasce qui, e un test
fallisce se uno dei tre cambia sotto.

⚠️ **Resta fuori il tempo di parlare**, e non è una svista: a 150 parole al
minuto — la costante di §15 — centodiciotto secondi sono **295 parole**, e
`config/voice-persona.md` chiede «una o due frasi». Una risposta che sfora quel
tetto ha già violato la persona, e il battito che se ne accorge dice una cosa
vera.

---

## Verifica

### ✅ Le cinque bocciature

| perturbazione | esito |
|---|---|
| il battito torna cieco durante il turno | 1 rosso |
| il tetto diventa un numero scelto (300) | 2 rossi |
| il turno non timbra più il proprio inizio | 1 rosso |
| lo STT si scosta dal TTS (45 s) | 2 rossi |
| il silenzio del fornitore non si annuncia | 1 rosso |

### ⚠️ Un test mio che diceva una cosa e non la imponeva

`test_durante_un_TURNO_non_e_muto` recitava *«un turno può durare fino al
timeout di T1»* e poi asseriva `muto_da() == 0.0` **senza alcun limite**. Il
commento descriveva un tetto che il test non verificava e che il codice non
aveva. Adesso il timbro del turno è obbligatorio.

### ✅ La suite

`1457 → 1466`, verde salvo il rosso dichiarato qui sotto.

### ⚠️ La diagnosi è per ELIMINAZIONE, non per osservazione diretta

Non ho visto lo stack del core appeso: `py-spy` non è installato e non aggiungo
dipendenze senza chiedere. Ciò che ho misurato è che **tutti gli altri stadi
hanno un tetto** (cattura 8 s, T1 90 s, TTS 20 s), che il tempo trascorso
(4 minuti) li supera tutti, e che **lo STT non ne aveva nessuno**. È una
deduzione forte, non un'osservazione. Lo dico come è.

### ❌ Difetto architetturale APERTO, non corretto

`_su_trigger` è atteso dentro l'`async for` del microfono: il ciclo audio si
ferma per **tutto** il turno, quindi anche una risposta lunga e legittima
riempie la pipe e produce audio stantio al ritorno. Il tetto rende la sordità
**temporanea**, non la elimina. La correzione vera — il turno come compito
separato, con il ciclo che continua a leggere — tocca il barge-in e merita un
turno suo.

### ❌ ROSSO ancora dichiarato

`test_densita.py::test_la_misura_descrive_i_sorgenti_di_ADESSO` resta rosso dal
commit precedente: rimisurare richiede che nessun altro Electron giri, cioè
chiudere la finestra del Signore.
