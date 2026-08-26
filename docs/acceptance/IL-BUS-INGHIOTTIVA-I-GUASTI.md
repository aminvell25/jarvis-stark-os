# «Non mi apre il pannello telemetria» — e non c'era una riga da leggere

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §13, §3.2
**Rollback**: `cd5606a`

---

## Il registro ha bisezionato il guasto in un colpo

Il core ha fatto **tutto giusto**, e lo dice da solo:

```
00:42:51  wake_trigger  frase=jarvis  latenza_ms=3.03
00:42:55  traversata    esito=t0  tool=open_panel  stt_provider=deepgram
00:42:55  t0            testo='Apri pannello telemetria.'  args={'panel': 'telemetria'}
00:42:55  t0_ui         intento=open_panel
diario    {"flusso": "azione", "intento": "open_panel", "strada": "ui", "ok": true}
```

Il registro dell'instradamento, scritto ieri per un'altra ragione, ha
risparmiato l'intera diagnosi del core: risveglio, trascrizione, grammatica,
istradamento — tutto verde, in cinque righe. Il difetto è a valle del socket.

E la disposizione salvata dice che il pannello non si è aperto:

```
layout.json → ['globo', 'agenti', 'news', 'file', 'meteo']
```

---

## Che cosa ho misurato, e che cosa NON ho ancora trovato

`apri("telemetria")` **funziona**. Provato nel browser, sulla scrivania vera:
chiuso il pannello, richiamato `apri`, riaperto. Il componente è importato
staticamente, quindi non c'è un caricamento pigro che possa fallire.

Quindi il guasto sta fra il socket e `apri`. **E lì non c'era niente da
leggere**: né nel renderer, né nel ponte, né nel journal del core, che vedeva
`t0_ui` e considerava il lavoro fatto.

⚠️ **La causa vera resta IGNOTA.** Ciò che segue non è la correzione del
difetto: è la costruzione di ciò che serve a vederlo. Come il battito del
microfono, che non ha spiegato l'ora di sordità — l'ha resa osservabile.

---

## Due difetti nel bus, e il secondo è peggiore del primo

```js
for (const cb of iscritti.get(msg?.topic) ?? []) cb(msg);
```

**① Il promesso si buttava via.** `suIntento` della scrivania è `async`: se
`apri()` solleva, nasce un rifiuto non gestito che **nessuno guardava**. Un
pannello che non si apre non lasciava traccia da nessuna parte.

**② Un'eccezione SINCRONA fermava la consegna a tutti quelli dopo.** Usciva
dal `for`, e gli iscritti successivi non ricevevano niente — in ordine di
iscrizione, cioè per caso. Un pannello rotto zittiva gli altri.

Misurato nella pagina, prima e dopo, con tre iscritti (sincrono rotto, async
rotto, sano):

| consegna | il terzo riceve? | i guasti si vedono? |
|---|---|---|
| **prima** | **no** | no |
| **dopo** | sì | sì, due righe `[bus] iscritto in errore` |

## E la seconda metà: adesso il renderer si può leggere

- `app/main.js` inoltra **avvisi ed errori** della console del renderer al
  registro dell'app. Solo quelli: inoltrare tutto renderebbe il registro
  illeggibile, e un registro illeggibile non si legge.
- `ui/src/app.js` cattura i rifiuti non gestiti. Un rifiuto può nascere dentro
  un `alimenta` o un'animazione, fuori dal bus, e moriva dentro una finestra
  che nessuno apre.

---

## E una prova arrivata per caso: la terza gamba del cancello

Il documento precedente dichiarava non osservato che **chiudendo la finestra
`pw-record` termini**. L'app si è chiusa da sola alle 00:43:45, e il core l'ha
scritto:

```
00:43:45  client_disconnesso  totale=0
00:43:45  scrivania_chiusa    totale=0
00:43:45  ascolto_revocato
00:43:45  cattura_fermata      →  pgrep pw-record: NESSUNO
```

**Tutte e tre le gambe di §18.3 sono ora provate in produzione.**

⚠️ E dice un'altra cosa: **l'app è morta ventitré secondi dopo il comando
fallito**, senza lasciare una riga. Se è caduto il renderer, l'inoltro appena
aggiunto lo dirà la prossima volta — ed è la stessa cecità di cui sopra.

---

## Verifica

### ✅ La bocciatura, eseguita nella pagina

La consegna vecchia riprodotta a mano: con un iscritto sincrono rotto davanti,
il secondo riceve **`[]`**. Con quella nuova riceve il messaggio e i due guasti
compaiono in console.

### ❌ ROSSO DICHIARATO — `test_densita.py::test_la_misura_descrive_i_sorgenti_di_ADESSO`

```
impronta nell'esito 4eb4d262a83e6696, sorgenti adesso 57a620826b654621
```

Ho toccato due sorgenti della UI (`bus.js`, `app.js`), e la misura di densità
registrata non li descrive più. La guardia fa il suo lavoro.

**Non l'ho rimisurata**, e il motivo non è pigrizia: `npm run verifica:densita`
rifiuta di partire con un altro Electron vivo —

> *«due insieme si contendono la GPU e la misura non vale: sette PNG diversi su
> otto giri»*

— quindi rimisurare vuol dire **chiudere la finestra del Signore** mentre sta
per provare la voce. Le due modifiche sono di solo registro e non possono
cambiare un pixel, ma «non può cambiare» è esattamente l'assunzione che questa
guardia esiste per non far fare.

**Da rimisurare alla prima finestra libera.** Fino ad allora il rosso resta, ed
è dichiarato qui.

### ❌ NON verificato

- **Perché il pannello non si apra.** È il difetto vero, ed è ancora ignoto.
  Adesso ha un posto dove comparire.
