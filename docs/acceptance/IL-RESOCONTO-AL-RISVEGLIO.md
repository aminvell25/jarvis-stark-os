# `initiatives/` era una cartella in sola scrittura

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.5, §3.2
**Rollback**: `b3aefc0` · **Test**: 1491 → **1508**

---

## Il difetto, nella docstring che lo dichiarava

`MemoryStore.registra_iniziativa`, dalla Fase 4:

> *«Ciò che JARVIS ha fatto di propria iniziativa, **visibile al risveglio**.»*

Non lo era. Nessuno leggeva quel file: **il file il cui unico scopo è essere
letto al risveglio non aveva un lettore.** Ed è la firma del JARVIS dei film —
ha lavorato mentre Lei non c'era, e al ritorno dice una conclusione.

---

## Le tre decisioni

### ① Il resoconto NON passa da un modello

È composto dai dati, con una tabella di frasi. Non è un risparmio: è una
proprietà.

> Ciò che JARVIS dice di **aver fatto** non deve poter essere inventato.

Un modello che riassume un registro può sbagliare un numero o aggiungere una
riga che non c'era, e sarebbe la peggiore bugia che questo sistema possa dire.
Il riassunto di una **conversazione** lo fa un modello (§5.5); il rendiconto
delle proprie **azioni** no.

E la tabella è un'allowlist, non un formattatore generico: un test confronta i
tipi che il core registra davvero — trovati grepando `registra_iniziativa("…")`
in `core/` — con le frasi disponibili. Chi aggiunge un'iniziativa e scorda la
frase lo scopre qui, non sentendolo.

### ② «Niente da riferire» si dice — ma non a ogni riconnessione

Il silenzio non è un resoconto: un JARVIS che tace e uno rotto si somigliano
troppo. Ma la scrivania si ricollega a ogni riavvio del core — **ventisette in
tre giorni** — e dirlo ogni volta lo trasformerebbe in rumore.

Il confine è `PERIODO_S`, **lo stesso di §5.5 e non un numero nuovo**: l'unica
cosa che JARVIS fa da solo ha periodo giornaliero, quindi un giorno senza
iniziative è il più piccolo intervallo in cui «niente» sia un'informazione.

### ③ Il taglio sul timbro è stretto

`> da`, non `>=`: rileggendo con il proprio timbro non si riferisce due volte la
stessa iniziativa.

---

## Due difetti trovati DAL VIVO, non dai test

**La riga finiva nel diario due volte.** L'avevo scritta nel flusso `dialogo`;
dal vivo ne sono comparse due — la mia e quella del turno che la pronuncia,
perché `annuncia()` produce un `Turno` e `_annota_dialogo` lo scrive.

Non erano un duplicato da sopprimere: sono **due fatti diversi**. Nel flusso
`azione` si registra che JARVIS **ha deciso di riferire**, e resta anche a voce
spenta; nel flusso `dialogo` finisce ciò che ha **detto**, se l'ha detto.

**E il resoconto non deve dipendere dalla voce.** Legarlo a `self._voce is not
None` — cioè metterlo dopo il `return` che c'era in `_scrivanie_cambiate` —
avrebbe reso il risveglio muto su un sistema con la voce spenta, che è la
configurazione predefinita di §7.1.

⚠️ **E si scrive prima di parlare.** Il diario è su disco e si legge a voce
spenta; il TTS di ripiego è EdgeTTS, che è di rete. A ordine rovesciato, una
rete assente cancellerebbe il resoconto invece di renderlo muto.

---

## Verifica

### ✅ Dal vivo, e con la finestra giusta

```
04:08:46  resoconto_al_risveglio  iniziative=1
          "Mentre non c'era, Signore: ho messo in ordine gli appunti di 1 sessione."
04:08:47  primo_suono_ms  ms=866        ← e l'ha detto ad alta voce
```

Riga nel diario, flusso `azione`:

```
{"flusso": "azione", "intento": "resoconto_al_risveglio", "ok": true,
 "da": "risveglio", "strada": "diario", "iniziative": 1, "testo": "…"}
```

Il freno, contando **solo dopo l'ultimo `core_avviato`** — la finestra larga mi
aveva già ingannato due volte stanotte:

```
primo avvio  (timbro rimosso)  → resoconti: 1
secondo avvio (timbro fresco)  → resoconti: 0
```

### ✅ Le cinque bocciature

| perturbazione | esito |
|---|---|
| il risveglio non racconta più | 2 rossi |
| il taglio diventa `>=`: si ripete | 1 rosso |
| un tipo registrato senza frase | 2 rossi |
| il resoconto diventa un elenco | 2 rossi |
| il resoconto scritto nel flusso `dialogo` | 2 rossi |

### ⚠️ E la settima volta

Un mio test ha letto una **docstring** invece del codice: `e_ora_di_dirlo` spiega
il confine per esteso e la stringa `PERIODO_S` compariva nella spiegazione. Il
togli-commenti adesso toglie anche le docstring.

### ❌ NON verificato

- **Il pannello del diario che mostra la riga.** È su disco e sul socket, e il
  pannello esiste — ma nessuno l'ha ancora guardato mentre arrivava.
- **Un risveglio con più tipi di iniziativa.** Oggi ne esiste uno solo, il
  consolidamento: la frase composta da due pezzi è provata nei test, mai nei
  dati.
- **Due scrivanie collegate insieme** (`scrivania_dichiarata totale=2`,
  osservato): il resoconto scatta a ogni salita sopra zero, quindi due app
  aperte lo sentirebbero una volta sola grazie al timbro — ma non l'ho provato.
