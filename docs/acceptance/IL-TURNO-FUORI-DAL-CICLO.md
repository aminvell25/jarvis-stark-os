# Il turno esce dal ciclo — e il sorvegliante sparisce con lui

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §7.1, §7.4
**Rollback**: `c2c9f8a` · **Test**: 1466 → **1469**

---

## Il difetto che il commit precedente aveva dichiarato aperto

> *«`_su_trigger` è atteso dentro l'`async for` del microfono: il ciclo audio
> si ferma per tutto il turno. Il tetto rende la sordità temporanea, non la
> elimina.»*

Una riga:

```python
self._compito_turno = asyncio.create_task(self._turno(self._con_apertura(trigger)))
```

Il ciclo non si ferma più. Finché i blocchi vengono consumati, `pw-record` non
riempie la pipe — ed è **tutta** la famiglia delle sordità del 26 e 27 agosto.

---

## E il sorvegliante del barge-in sparisce

`_sorveglia_barge_in` esisteva **per una ragione sola**: il ciclo era bloccato,
quindi il controllo del barge-in in cima al ciclo non poteva scattare mentre
JARVIS parlava. La toppa era un **secondo lettore del microfono**, con un
secondo `pw-record` e un secondo VAD.

Con il ciclo libero, il barge-in torna dov'era stato progettato. E non si perde
nessuna taratura: i due VAD erano **identici** — `SOGLIA_BARGE_IN` e
`BLOCCHI_BARGE_IN` sono già i default di `VAD()`, e il sorvegliante li passava
esplicitamente senza cambiarli.

**Un microfono, un lettore.** Un test conta le aperture di `dal_microfono` e
dichiara la seconda: `_trascrivi`, che apre il proprio flusso dopo il risveglio
per mandarlo allo STT — è un'altra cosa, e sta scritto perché il conto non
menta.

---

## Tre cose che il ciclo libero rende necessarie

**① Un turno alla volta.** Il ciclo ora legge anche mentre JARVIS parla, ed è
il suo stesso eco che rientra dal microfono. Senza freno, ogni blocco di eco
diventerebbe un turno nuovo. Il `continue` tiene anche la voce di JARVIS fuori
da Vosk.

**② Le due uscite non sono la stessa.** Se la pipeline viene **annullata**, il
turno se ne va con lei — senza, resterebbe un compito vivo che parla con il
microfono già chiuso. Se il ciclo finisce **da solo** (microfono morto, ascolto
revocato), il turno si **aspetta**: tagliare a metà una risposta già cominciata
perché il flusso in ingresso è finito sarebbe peggio del guasto.

**③ `stop()` lo ferma.** Il turno non è più figlio del ciclo: uscire dal ciclo
non lo ferma più da solo.

---

## Verifica

### ✅ Le quattro bocciature

| perturbazione | esito |
|---|---|
| il turno torna dentro il ciclo | 2 rossi |
| l'annullamento non porta via il turno | 1 rosso |
| due turni insieme | 1 rosso |
| l'uscita normale non aspetta il turno | 1 rosso |

⚠️ **Le ultime due non discriminavano** al primo giro: erano proprietà che i
miei commenti dichiaravano e che nessun test imponeva. Trovate eseguendo le
bocciature, e ora hanno un test ciascuna.

### ⚠️ Sei test riscritti, nessuno indebolito

- **due del sorvegliante** → sostituiti da una prova **comportamentale**: con
  un turno in volo, il ciclo continua a leggere. È più forte di quelle che
  cercavano `_sorveglia_barge_in` nel sorgente.
- **`test_l_annullamento_passa_ancora`**: la proprietà è la stessa — chi spegne
  non aspetta per sempre — ma passa da un'altra strada e va imposta lì.
- **`test_il_ciclo_SOPRAVVIVE_a_un_turno_che_solleva`**: il finto consegnava
  tutti i blocchi **senza mai cedere il controllo**, e nessun microfono vero lo
  fa. Con il turno che gira per conto suo, quella finzione si vedeva.
- **due grep di sorgente** allineati alla riga nuova.

### ✅ La suite

`1466 → 1469`, verde salvo il rosso dichiarato.

### ⚠️ L'app muore, e potrei essere io

L'app Electron si è chiusa **tre volte** stasera senza lasciare una riga.
Ho aggiunto `render-process-gone`, `unresponsive` e `closed` al registro — un
renderer che muore non lasciava traccia, e `console-message` non copre il caso
in cui a morire è il processo che scriverebbe.

Ma **non attribuisco il guasto a JARVIS**: quelle istanze le ho avviate io da
una sessione di lavoro, e ogni morte coincide con un mio comando lungo. Che sia
il renderer o il mio stesso ambiente che raccoglie un processo figlio, non l'ho
distinto. **Non misurabile finché non muore una finestra aperta da Lei.**

### ❌ ROSSO ancora dichiarato

`test_densita.py::test_la_misura_descrive_i_sorgenti_di_ADESSO`. Rimisurare
richiede che nessun altro Electron giri:

> *«due insieme si contendono la GPU e la misura non vale: sette PNG diversi su
> otto giri»*

Servono due minuti con la finestra chiusa.
