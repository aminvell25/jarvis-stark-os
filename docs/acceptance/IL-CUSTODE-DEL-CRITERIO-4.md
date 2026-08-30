# §26.9 criterio 4 — il verdetto era deciso da chi arrivava primo

**Data:** 30 agosto 2026 · **Riferimento:** `docs/SPEC-26-AMBIENTE-UNICO.md`
§26.9 punto 4, §26.5 · **Rollback:** `879ff4a` · **Test:** 1870 → **1872**

---

## Il difetto era della prova, non del prodotto

Il criterio dice: *«Un'icona portata sul fondo ci resta; riavviato il core, è
ancora lì. Verificato riavviando davvero, non simulando.»* Parla di
**persistenza attraverso un riavvio**. Non dice niente sul chiudere la finestra
entro mezzo secondo da un gesto.

`prova-icone.mjs` però faceva proprio quello: la sezione 6 finiva con
`dorme(400)`, il debounce della persistenza è **500 ms**, e la sezione 7
chiudeva l'app subito dopo. La chiusura cadeva **sul filo**, dove l'esito
dipende da chi arriva primo — il timer del debounce, il flush di `pagehide`, o
la morte del processo.

Misurato: **1 rosso su 9**. Poi, aggiungendo un solo `evaluate` per strumentare,
**1 su 2**. Un verdetto che si sposta perché si è guardato non è un verdetto.

Sono due proprietà, e stavano in una:

| proprietà | dove vive adesso |
|---|---|
| la rimozione sopravvive al riavvio | `test_10`, con l'attesa oltre il debounce |
| una modifica fatta negli ultimi 500 ms prima di uscire sopravvive | `scripts/prova-flush.mjs` — **non garantita**, vedi sotto |

## La cura

Una riga in cima alla sezione 7, `await dorme(RITARDO_MS + 400)`, con scritto
perché. 900 ms contro un debounce di 500: il timer è già scattato quando la
finestra si chiude, quale che sia il carico.

**Otto corse, criterio 4 verde otto volte su otto.**

## ⚠️ La bocciatura che non discrimina, e il custode che è cambiato per questo

La prima stesura custodiva l'**esito**: la prova registrava
`inviato_prima_di_chiudere.ultimo_icone` — quante icone portasse l'ultima
disposizione partita davvero — e `test_10` pretendeva che valesse quanto il
fondo a schermo. Con l'attesa piena vale 9; accorciandola a 400 ms doveva
valere 10, perché la rimozione non sarebbe ancora partita.

**Bocciatura eseguita, e non discrimina**: con `dorme(400)` quel campo diceva
**9 lo stesso**. Poche ore prima, sulla stessa riga di codice ma con la macchina
più carica, diceva 10. Il campo sta sullo stesso filo che dovrebbe sorvegliare.

> **Una corsa non si può far cadere a comando.** Ciò che si può custodire è la
> riga che la toglie.

Il custode è quindi statico, e cade netto: `TestIlFiloDeiCinquecentoMillisecondi`
legge `scripts/prova-icone.mjs` — il codice, non i commenti — e pretende
l'attesa **prima della prima chiusura**. Cercarla nel file intero non basterebbe:
la sezione 8 ne ha una uguale, e direbbe di sì anche con la sezione 7 tornata sul
filo.

Il campo strumentato è stato **tolto** insieme al suo `evaluate`: non porta
carico, e perturba ciò che misura.

## L'altra proprietà: c'è la rete, non c'è la garanzia

`ui/src/app.js` registra `pagehide` → `persistenza.adesso()`: chi chiude prima
del timer ha quella sola rete. Misurata con `scripts/prova-flush.mjs`, che mette
in coda una scrittura marcata e chiude senza aspettare:

```
app.close() di Playwright   8/8 recapitati
BrowserWindow.close() vera  8/8 recapitati
```

Su un'app ferma arriva sempre. **Dentro `prova-icone.mjs` — sette pannelli
aperti, scrivania viva — si perdeva 1 volta su 9.** Quindi la proprietà **non è
garantita sotto carico**, e nessuna prova la asserisce: un test che dicesse
«arriva sempre» sarebbe rosso a caso, cioè una ricevuta falsa.

Si custodisce ciò che è vero e non dipende dal carico: **che la rete ci sia**.
Toglierla trasformerebbe una perdita occasionale in una perdita certa — ed è la
seconda bocciatura, eseguita: senza quella riga il test cade.

`scripts/prova-flush.mjs` resta come **strumento di misura a mano**, non
consumato da nessun test, come i `bench_*` del progetto. È l'unico modo di
rimisurare quel numero.

## Che cosa resta aperto, con il suo numero

**`test_1` e `test_2` restano intermittenti**: 1 corsa su 8 oggi, con
`estrazione.sopra_i_pannelli: None`. È un'altra sezione e un'altra causa — non
tocca il criterio 4, e non è stata diagnosticata. Va guardata per conto suo.

## Che cosa resta NON MISURABILE

**Quanto spesso una persona chiuda la finestra entro 500 ms da un gesto.** È il
caso in cui la rete di `pagehide` è l'unica cosa fra la modifica e la perdita, e
non è misurato quanto capiti nell'uso vero.
