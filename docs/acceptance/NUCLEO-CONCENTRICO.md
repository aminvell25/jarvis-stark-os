> ## 🔴 STORICO — il nucleo che questo documento misura NON ESISTE PIÙ
>
> Il 2 settembre 2026 il nucleo è stato rifatto sul riferimento «Aurora»: otto
> stati, tre gusci deformati da rumore FBM, catena di post-processing. Tutto
> quello che sta qui sotto — geometria, strati, criteri, numeri — misura un
> oggetto **cancellato**. Il codice sta in git e si recupera con un checkout.
>
> **Lo stato corrente è in `docs/acceptance/NUCLEO-AURORA.md`.**
>
> ⚠️ Questo documento **non si cancella** e non è un rifiuto: è il registro di
> ciò che è stato misurato e perché, ed è citato da 0 altri file. La
> «definizione di fatto» di CLAUDE.md poggia su questi referti. Serve però il
> cartello: fra il 24 e il 30 agosto un documento di stato ha detto il falso su
> cinque voci su cinque, **ed è stato creduto** — e la cura non è cancellare, è
> dire da quando una cosa non vale più.

# I cerchi erano storti — e la descrizione del riferimento era sbagliata

> Il proprietario ha guardato il nucleo e ha detto che i cerchi non sono
> simmetrici ma storti. Aveva ragione, e la causa non era un errore di
> disegno: era **una descrizione sbagliata del riferimento**, scritta in due
> documenti e propagata nella geometria.

---

## La misura che lo dimostra

Adattando un cerchio ai bordi di ciascuna banda coi minimi quadrati (Kasa),
720 raggi per banda, saltando i varchi:

**`famiglia-a/12`, il riferimento** (raggio del disco 120 px):

| banda | centro | R | errore medio |
|---|---|---|---|
| r 108–122 | (−0,15 · +0,56) | 120,1 | 2,65 |
| r 94–107 | (+0,73 · +1,22) | 105,4 | 1,88 |
| r 74–92 | (+2,08 · −0,50) | 88,4 | 2,78 |
| r 58–73 | (+0,36 · −2,22) | 71,7 | 1,27 |

Gli scarti stanno fra **0,15 e 2,08 px su 120** — sotto l'1,7 %, e dello stesso
ordine dell'errore della misura. **Il riferimento è concentrico.**

**Il nostro**, prima della correzione: la tabella `ANELLI` dichiarava
`(+4, −3)`, `(−3, +5)`, `(+2, +4)` su un raggio di 120 — fino al **4,2 %**, e
ognuno in una direzione diversa. È quello che si vedeva.

## E due documenti lo dicevano già, in disaccordo fra loro

- **§25.1** e `docs/design-reference/README.md`: *«anelli disallineati, centri
  sfalsati»* — sbagliato;
- **§10.3**: *«Anelli **concentrici**»* — giusto;
- il file si chiama `12-logo-anelli-**concentrici**.png`.

Nessuno aveva mai confrontato le due righe. Le prime due sono corrette in
questo commit, con la misura accanto.

---

## Le fasce: il commento diceva già la cosa giusta, i numeri no

Il commento sopra `ANELLI` diceva: *«Le fasce sono ADIACENTI, con corridoi di
pochi millimetri fra l'una e l'altra. La prima versione le aveva distanti, e lo
screenshot mostrava quattro archi sottili che galleggiavano nel vuoto.»*

I numeri non lo seguivano:

| | fasce | corridoi |
|---|---|---|
| prima | 8, 5, 12, 4, 3 | **6, 7, 8, 12** |
| riferimento, coperto | **0,484 del raggio** | — |
| nostro, coperto | **0,267** | — |

Il vuoto era largo quanto il pieno, e coprivamo il **55 %** di quanto il
riferimento copre.

**Dopo**: corridoi fissi a 3 unità, fasce 11, 9, 17, 13, 3 → coperto **0,442**,
contro lo 0,484 del riferimento. Le tacche sono cresciute in proporzione
(circa un terzo e due terzi dello spessore della propria fascia), o dentro una
fascia larga sarebbero sparite.

**E non è solo aspetto.** Un varco che ruota dentro una fascia larga si legge;
dentro un filo no — e il varco che ruota **è** il movimento di §25.6. Fasce più
larghe sono più dinamiche prima ancora che si muova qualcosa.

---

## ⚠️ Un difetto mio del turno 3, trovato guardando

Il primo scatto della composizione nuova aveva **l'anello esterno ambra**,
mentre la barra della scrivania diceva `NOMINAL`. Non era il tema: era un
difetto.

```js
if (topic === "agent.advisory") { livello = msg.livello ?? "warn"; }
```

**Un avviso succede, non dura.** Quella riga lo trattava come uno stato: al
primo `agent.advisory` senza livello il nucleo passava a `warn` e non lo
toglieva più nessuno. È lo stesso errore di categoria che il commento sull'onda
descrive due schermate più sopra — *«un parametro che poi torna indietro da
solo mente per tutto il tempo in cui sta fuori posto»* — commesso sul campo
accanto, nello stesso file.

Adesso l'avviso alza un accento **a tempo** (2600 ms, la stessa durata che la
stesura a nuvola dava allo stato «pensa») e poi restituisce il comando a
`state.snapshot` e `agent.mesh`, che sono le sorgenti che sanno anche quando
una cosa rientra. Verificato: `data-livello` torna a `nominal`.

---

## ⚠️ Il marchio si è rotto di nuovo, e stavolta la riparazione è strutturale

Allargando le fasce, la fascia dei 233 s è scesa da r 70 a r **61**, cioè sotto
le estremità del nome. Misurato: §25.13.5 da **3,01:1 a 2,94:1** — sotto il
minimo. Il margine zero dichiarato nel commit precedente è saltato **alla prima
modifica**, che è esattamente ciò che «margine zero» significava.

La causa non era il colore: era che **la larghezza del nome era una citazione
fissa** — 0,561 del raggio, la quota misurata sul riferimento — mentre il campo
su cui deve posare è **derivato dalla geometria**. Due numeri che devono stare
insieme, di cui uno solo si aggiorna.

**Adesso il nome si stringe dentro il campo.** La quota resta l'intento; il
campo è il vincolo: si misura la diagonale del riquadro reso — l'angolo, che è
il punto più lontano dal centro — e la si tiene dentro il raggio che
`costruisciDisco` dichiara. Se la composizione cambia, il nome si adatta da
solo.

| | contrasto | composito sotto il nome |
|---|---|---|
| fasce allargate, nome fisso | 2,94:1 ❌ | misto campo + fascia accesa |
| nome legato al campo | **3,04:1** ✅ | `rgb(19, 33, 42)` = **`--bg-panel` esatto** |

Il numero è quasi lo stesso, ma è **un altro tipo di numero**: prima era una
media fra due fondi diversi, adesso è il rapporto fra due token dichiarati —
`--cy-700` su `--bg-panel`, che vale 3,07:1 in teoria e 3,04 misurato con
l'antialiasing. Deterministico, e stabile a qualunque composizione.

Resta sottile, e resta la stessa decisione di prima: guadagnare margine
richiede §25.13, non §25.5.

---

## Le misure

| | prima | dopo |
|---|---|---|
| entropia | 1,69 | **1,73** |
| `L>60` | 10,0 % | **10,0 %** |
| banda 25–120 | 64,5 % | **66,1 %** |
| luminanza media | 35,55 | **35,9** |
| §25.13.5 | 3,01:1 | **3,04:1** |

Verifica in finestra vera, blocco `nucleo`: `aRiposo []`, una causa per anello,
`t0` impulso senza moto, opacità di fase esatte, **zero fotogrammi in un
secondo di riposo**. Suite **561 passed**. Audit `rings` 0/0 — il pannello di
§10.3 usa la stessa geometria e migliora con lei: anche lì le fasce erano
sottili e i centri sfalsati.

---

## Che cosa NON è stato verificato

- **Il ciclo §11.8 punto per punto** sul pannello `rings` dopo il cambio di
  composizione: è stato guardato e l'audit è pulito, ma la checklist non è
  stata ripercorsa riga per riga.
- **`--rust` su `critical`**: la strada dell'avviso adesso lo porta
  (`avvisoLivello`), ma nessuna esecuzione ha pubblicato un advisory critico.
- **La durata di 2600 ms dell'accento** è ereditata dalla stesura a nuvola, non
  ritarata su questa.
- **La copertura 0,442 contro 0,484** del riferimento non è stata chiusa: i
  corridoi a 3 unità sono una scelta, non una misura del riferimento — che i
  propri corridoi li ha di 8 e 13 millesimi di raggio, cioè circa 1 e 1,5
  unità. Portarli lì stringerebbe ancora il vuoto.
