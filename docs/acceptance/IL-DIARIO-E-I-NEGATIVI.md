# I negativi, il blocco A, e il registro che mancava per spiegarli

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §3.2, §5.5, §7.2, §7.4
**Rollback**: `0bca84b` · **Test**: 1385 → **1392**

---

## Le misure che mancavano a ①

Quattro frasi **senza** wake word, poi cinque comandi con `jarvis`.

### I negativi: 2 falsi risvegli su 4

| detto | trascritto | esito |
|---|---|---|
| «domani mattina devo passare in ufficio presto» | `Domani mattino devo passare in ufficio presto.` | ❌ **falso risveglio** |
| «ha ricevuto la lettera…» | — | ✅ nessun risveglio |
| «per varie ragioni…» | — | ✅ nessun risveglio |
| «la gara di sci è stata rinviata a domenica» | `La gara di sci è stata rinviata a domenica.` | ❌ **falso risveglio** |

**50 % di falsi risvegli**, e nessuna delle due frasi contiene qualcosa che
somigli a «jarvis» a orecchio umano. È la misura che §7.2 regola 1 aspettava: la
frase di wake è **una parola sola**, con una grammatica Kaldi chiusa che deve
pur scegliere qualcosa, e la regola che vieta il risveglio a parola singola
**non è imposta** da nessuna parte.

⚠️ E ognuno di quei falsi risvegli è costato un turno intero: STT remoto, T1,
TTS. Adesso costa **secondi di Deepgram**, non solo attenzione.

### Il blocco A: 4 comandi su 5, e uno sparito

| # | detto | trascritto da Deepgram | esito |
|---|---|---|---|
| 1 | quanto fa dodici per sette | `Quando fa duedici per sette?` | T1 → «Ottantaquattro, Signore.» ✅ |
| 2 | **apri il pannello telemetria** | — | ❌ **nessun turno** |
| 3 | spiegami perché il cielo è blu | `Spiegami perché il cero è blu.` | T1, e ha chiesto «Intende il cielo, Signore?» ✅ |
| 4 | secondo me il sole gira intorno alla terra | *(esatto)* | «È il contrario, Signore.» ✅ **dissente** |
| 5 | che ore sono | `Chiori sono?` | «Non ho l'ora precisa… Signore.» ✅ |

**Nessuno dei cinque ha attraversato T0.** Tutti `esito=t1`, `tool=None` — e il
secondo, che è un comando `open_panel` di manuale, non ha prodotto **niente**.

### La qualità dello STT italiano è il fatto dominante

`flux-general-multi` con `language_hint=it` — la configurazione è corretta.
Eppure: «duedici», «il cero è blu», «Chiori sono», e in un giro precedente
«Giardi, mi sei finito di spiegarmi?» per *«jarvis, hai finito di spiegarmi»*.

Le tre righe che contano non sono nel journal ma nella conversazione: JARVIS ha
**risposto giusto lo stesso** tre volte su tre — 84 per «duedici per sette», e
ha chiesto conferma su «cero». La persona regge una trascrizione sporca; T0 no,
perché T0 è una grammatica esatta.

**Ipotesi, non conclusione**: il comando 2 potrebbe non essere arrivato affatto
(mancato risveglio) oppure essere stato trascritto male e non aver morso su
nessuna regola. **Non posso distinguerle**, ed è esattamente per questo che
esiste il resto di questo documento.

---

## Ciò che ho imparato non potendo spiegare

Il journal registrava `traversata esito=t1` e **non registrava che cosa lo STT
avesse capito**. Il testo c'era, in `sessions/<giorno>.jsonl`, e ci sono
arrivato per caso.

Ma `sessions/` ha **un solo scopo**: è la cronologia grezza che alimenta il
consolidamento notturno di §5.5. Chiedergli di essere anche lo strumento di
diagnosi sarebbe due letture della stessa domanda — il difetto che questo
progetto ha già pagato coi tre ritagli e i due orologi.

## Il diario: due flussi, e perché due

```
dialogo   ciò che è stato DETTO — da chi, con che parole
azione    ciò che il sistema ha DECISO e FATTO — e con che esito
```

Sono domande diverse. *«Che cosa mi ha risposto»* si guarda in ordine di
conversazione; *«perché ha aperto quel pannello»* si guarda in ordine di causa.
Mescolarli produce un registro in cui non si legge nessuna delle due.

**Ogni evento va su disco e sul socket**: su disco perché un numero che vive
solo in un terminale non si confronta col mese prossimo; sul socket perché §3.2
dice che il core è la sorgente di verità della UI.

Due proprietà volute:

- **`FLUSSI` è una allowlist**, non una convenzione: un flusso scritto male
  renderebbe illeggibile il registro senza che nessuno se ne accorga;
- **ogni esito di `esegui_t0`, non solo quelli riusciti.** Un intento rifiutato
  è la riga più utile che ci sia, ed è proprio quella che finiva in un
  `warning` in mezzo a tutto il resto.

E il dialogo porta ciò che il turno non diceva a nessuno: **se è stato
interrotto**, e se il testo detto è una misura o un limite superiore. Senza,
rileggendo non si distingue una risposta finita da una troncata.

⚠️ **Il diario NON è la memoria.** Si cancella senza perdere nulla di ciò che
JARVIS sa.

## Come si guarda, oggi

```bash
uv run python scripts/diario.py            # oggi, tutto
uv run python scripts/diario.py --dialogo  # solo ciò che si è detto
uv run python scripts/diario.py --azioni   # solo ciò che si è fatto
uv run python scripts/diario.py --segui    # e resta ad ascoltare
```

Il pannello nella scrivania **non c'è ancora**, ed è il turno successivo: legge
lo stesso file, e §11.7 vuole il ciclo di verifica visiva che non entra in
questo turno insieme al resto.

> ⚠️ **CORRETTO il 29 agosto 2026.** Il pannello è arrivato lo stesso giorno di
> questa riga (`ui/src/panels/diario.js`), e **non legge lo stesso file**: è una
> coda viva che riceve `agent.diario` mentre le righe si scrivono. Riaprendo
> l'app, il diario di ieri non si vede, e `scripts/diario.py` resta l'unico modo
> di rileggere un giorno passato. La previsione era sbagliata su tutt'e due i
> punti: sul quando, e su come.

---

## Verifica

`1385 → 1392` test, suite verde. Un flusso inventato non entra nel registro; un
disco pieno non zittisce JARVIS; `annota()` manda anche al socket.

## ❌ NON verificato

- **Il diario dal vivo.** Scritto, provato e collegato, ma dal riavvio nessun
  turno vocale ci è passato: la prima riga vera arriverà alla prossima frase.
- **Perché il comando 2 sia sparito.** Resta un'ipotesi a due rami, e il diario
  serve proprio a chiuderla: alla prossima ripetizione si vedrà se il risveglio
  manca o se la trascrizione non morde.
- **La persona che «taglia corto».** Osservato da Lei sulla domanda 3, non
  ancora misurato: senza il registro non avevo di che contare le parole. Adesso
  ce l'ho, e va misurato prima di riscrivere la regola.
