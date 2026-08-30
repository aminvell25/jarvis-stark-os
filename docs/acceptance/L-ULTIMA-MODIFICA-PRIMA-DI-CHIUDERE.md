# L'ultima modifica prima di chiudere la finestra si perdeva

**Data:** 30 agosto 2026 · **Riferimento:** `docs/SPEC.md` §26.10 punto 1, §26.5
**Rollback:** `29737f2` · **Test:** 1868 → **1870**

Corregge la diagnosi scritta poche ore prima in
`docs/acceptance/IL-FONDO-SENZA-CUSTODE.md`, che era falsa.

---

## Da dove si è partiti — e che cosa NON si è chiuso

⚠️ **Questo turno non chiude il sintomo che l'ha fatto cominciare.** Cercando la
causa di `agenti` che torna, ho trovato un difetto vero, diverso, e l'ho chiuso.
Della causa di `agenti` ho eliminato due ipotesi e non ne ho trovata una. Sta
scritto in fondo, con la misura che lo dice.

## Il sintomo da cui si è partiti

`prova-icone.mjs` toglie l'icona `agenti` trascinandola sul catalogo, riavvia, e
al riavvio l'icona **torna**: nove icone prima della chiusura, dieci dopo.
Misurato ieri, su HEAD: **3 corse rosse su 6**, sempre con la stessa firma, con
`rimozione.tolta: True` — cioè la rimozione era avvenuta davvero.

È parola per parola il guasto che un commento in `ui/src/app.js` dà per risolto:
*«prova-icone.mjs rimuove `agenti` trascinandola sul catalogo, e al riavvio
tornava, nove icone prima della chiusura e dieci dopo»*. Quel commento descrive
una cura vera per una causa diversa. La causa che restava era un'altra.

## La diagnosi sbagliata, e la misura che l'ha smentita

Avevo attribuito la perdita al renderer: la sezione 6 finisce con `dorme(400)`,
il debounce della persistenza è 500 ms, e la finestra si chiude prima che il
timer scatti. Il flush esiste — `window.addEventListener("pagehide", () =>
persistenza.adesso())` — ma passa per due salti asincroni (`ipcRenderer.send`,
poi `socket.send` nel processo principale), e sembrava plausibile che sotto
`app.close()` non arrivasse.

**Misurato, tre avvii, stesso marcatore** (`x = y = 137` sul primo pannello),
messo in coda e mai atteso:

| chiusura | marcatore sul disco |
|---|---|
| si aspetta oltre i 500 ms, poi si chiude | **arrivato** |
| `app.close()` di Playwright, subito | **arrivato** |
| `BrowserWindow.close()` vera, subito | **arrivato** |

Il flush funziona in tutt'e tre i casi. **La diagnosi era falsa**, e la prova che
l'ha smentita non aveva mai esercitato la strozzatura del core — perché azzerava
il contatore e mandava una scrittura sola, a scrivania ferma da un secondo e
mezzo.

## Il difetto vero: due metà scritte, provate, mai congiunte

`LayoutStore.salva()` frena a `MIN_INTERVALLO_S = 0.25` e **fonde invece di
scartare**: ciò che non scrive resta in `_in_attesa`, e `chiudi()` lo mette giù.
Tutt'e due le metà esistono da §26.10, e sono provate — `TestIlFreno::
test_cio_che_e_frenato_si_FONDE_e_non_si_perde` chiama `chiudi()` a mano.

**L'unico chiamante di `chiudi()` era lo spegnimento del CORE**, in
`Engine.run()`. Ma il core è un servizio che resta acceso; la scrivania è una
finestra che si apre e si chiude sopra di lui. Chi chiudeva la finestra entro un
quarto di secondo dall'ultima modifica la perdeva — e alla riapertura
`messaggio_iniziale()` rilegge il **disco**, che era rimasto indietro.

Sembrava anche la spiegazione dell'intermittenza — dipenderebbe da quanto tempo
passa fra la penultima scrittura e quella della rimozione. **Non lo è**, e la
misura sta in fondo.

## La cura, e dove va

Il punto di giunzione esisteva già ed era cablato: `WsServer` chiama
`su_scrivania(len(self._scrivanie))` a ogni connessione e a ogni distacco, e
`Engine._scrivanie_cambiate` lo riceve — è lo stesso segnale con cui il
microfono segue la scrivania.

```python
if quante == 0 and self._layout.chiudi():
    log.info("layout_messo_giu_alla_chiusura_della_scrivania")
```

**A zero, non a ogni distacco.** Con una finestra ancora aperta i messaggi
continuano ad arrivare e ciò che è in attesa parte col prossimo: scrivere a ogni
distacco sarebbe una scrittura in più per un evento che non ha cambiato niente.

## Le bocciature — eseguite

1. **Il test era rosso prima che la riga esistesse**, ed è il difetto stesso:
   `la scrivania si e' chiusa e cio' che il freno tratteneva non e' andato giu':
   e' perso`.
2. **La guardia `quante == 0` porta carico**: rilassata a `quante >= 0`, il
   secondo test cade — `Left contains one more item: GeometriaPannello(id=
   'telemetria', x=999, ...)`.

## ⚠️ Il sintomo `agenti` resta APERTO, e questa è la misura che lo dice

Sei corse della prova col core corretto: **0 rosse su 6**, e su disco nove icone
senza `agenti` tutte e sei. Sembra la cura. **Non lo è**, e basta contare nel log
del core:

```
scrivanie chiuse                                          18
volte in cui il freno aveva DAVVERO trattenuto qualcosa     0
```

In diciotto chiusure di scrivania `chiudi()` non ha mai avuto niente da mettere
giù. Il caso che questo turno ripara **non si è presentato nemmeno una volta**,
quindi non può essere lui a spiegare le sei corse verdi — né le tre rosse di
ieri.

Restano eliminate due ipotesi, ed è tutto ciò che si è guadagnato sul sintomo:

1. **non** è il flush di `pagehide` del renderer (misurato: arriva in tutt'e tre
   i modi di chiudere);
2. **non** è il layout trattenuto dal freno del core (misurato: in diciotto
   chiusure non c'era mai niente in attesa).

Il prossimo passo, quando si riprenderà: far tornare rossa la prova — ieri
capitava 3 volte su 6 — e guardare in quella corsa se il disco porti `agenti` o
no. Se lo porta, la rimozione non arriva al core; se non lo porta, a rimetterla
è il ripristino. Sono due difetti diversi e la risposta si legge in un campo
solo.

## Che cosa resta NON MISURABILE

Che il caso capiti **a una persona** e non solo alla prova. Richiede di chiudere
la finestra entro 250 ms da un trascinamento, cioè un gesto che nessuno ha
misurato quanto spesso faccia. Il difetto è dimostrato nel meccanismo e nella
prova; la sua frequenza nell'uso vero no.
