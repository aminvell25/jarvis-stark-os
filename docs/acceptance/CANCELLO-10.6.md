# Cancello §10.6 — le tre classi di moto

**Data:** 24 agosto 2026 · **Rollback:** `2493454`
**Precedente di forma:** `e4851ae` / `CANCELLO-25.5.md` — governance, **zero codice**

Le regole di uscita del piano vietano di emendare la specifica dentro un turno
di implementazione. L'emendamento arriva quindi prima e da solo, e questo
documento porta la misura e il costo.

## Che cosa lo motiva

L'invariante 25 ha **due parole**: «con causa» e «ambientale». Ne servono
**tre**, e non per comodità — per due contenuti che la specifica **prescrive già**
e che oggi il loro stesso banco boccerebbe:

| | dove è prescritto | perché cade |
|---|---|---|
| **Equalizzatore vocale** | §11.5, Fase 3: «uPlot o canvas su **dati veri del microfono**». Il README lo misura su `famiglia-a/10`, riquadro `VOICE EQUALIZER` | un istogramma alimentato da un microfono aperto si muove finché il microfono è aperto. Non ha un evento di inizio e uno di fine: ha una **sorgente** |
| **`<webview>` con una pagina viva** | §6.3 la consente, `app/main.js` la mette già in sicurezza, `core/tools/web.py` la alimenta | una pagina reale contiene video, GIF, caroselli. Nessuno ha una «causa» nel senso dell'invariante 25, e tutti finiscono nella differenza a 250 ms di `densita.mjs` |

Nessuna delle due è decorazione. Cadono perché **non c'è una parola per dirle**.

## Che cosa cambia

```
classe 1  transitorio con causa            gia' legale, invariata
classe 2  continuo governato da una        NUOVA — solo nel contenuto
          sorgente viva                    di un pannello
classe 3  ambientale                       vietata, invariata
```

⚠️ **Che cosa NON cambia, ed è la metà che tiene il vincolo.** §10.3 «Fondo:
immobile» resta assoluta. Barra, dock, catalogo, cornice e strato di presenza
oltre ciò che §25.6 già assegna restano fermi. È l'unica riga del progetto mai
violata, e il cancello non la sfiora. Resta ferma anche la dottrina degli
anelli — una causa per anello, *«se gira, sta lavorando»* — che è il modello da
cui la classe 2 è ricavata, non un'eccezione a cui si aggiunge.

## Le tre condizioni, e perché sono già misurabili

Il cancello non introduce un criterio nuovo: **riusa tre strumenti che
esistono**. È la ragione per cui costa mezza giornata invece di due.

**(a) Falsificabilità** — `app/main.js` esegue già esattamente questo test sul
nucleo: `ins.forza(null)`, **due finestre da un secondo, si tiene la minore**.
Il commento in quel punto spiega già il perché di due e non una: *«un'animazione
ambientale gira in ENTRAMBE le finestre; un evento cade in una sola»*. Serve
generalizzare la leva da `window.__insegna` a un registro `window.__moto`.

**(b) Leggibilità da fermo** — è una riga nuova di §11.8, sezione CONTENUTO, e
non ha bisogno di strumenti: si guarda lo scatto, che è già il passo 4 di §11.7.

**(c) Attribuzione** — `scripts/densita.mjs` attribuisce già i pixel mossi per
zona, e `scripts/occlusione-dom.js` emette già i rettangoli. Oggi il calcolo
dell'ambiente tratta il nucleo come **caso particolare**; la generalizzazione è
una riga:

```
ambiente = diversi − Σ per[zone con sorgente viva dichiarata]      soglia: 0
```

Ed è un miglioramento indipendente dal cancello: oggi quella riga dice «§5.4 non
soddisfatto» ogni volta che il nucleo si muove **con** causa, cioè dice il falso
in un caso su uno.

## Il tetto — due sorgenti, 15 % del fotogramma

Una sorgente va bene, dodici sono uno screensaver.

⚠️ **Il 15 % non viene da nessun riferimento: è una scelta, non una misura.** Va
letta come la polarità della testata in §10.5 regola 2, che sceglie una delle tre
del riferimento e lo dichiara. Chi la cambia cambi anche questa riga, e scriva
perché.

## Quanto vale, onestamente

**Poco, in metrica.** Il moto non compra entropia: `famiglia-a/01` è un PNG
fermo, e il suo 42,1 % di `L>60` lo produce con superfici piene, non con
l'animazione, che in un fotogramma non c'è.

Vale perché **sblocca due contenuti** — microfono e web vivo — che sono le uniche
fonti disponibili per i bin sopra L 190, dove stiamo allo 0,1 % contro l'1,1–1,9 %
del riferimento.

⚠️ E per questo il cancello si apre **adesso ma si usa tardi**: le fasi che lo
consumano sono la sesta e la settima del piano, non la prima. Aprirlo e correre
a metterci dentro del movimento sarebbe l'errore classico — **mettere moto per
nascondere una composizione ferma e vuota**.

## Il costo del ritorno

Chiudere il cancello dopo l'uso significa togliere l'equalizzatore vocale e la
pagina viva, cioè due componenti e un topic del core. Prima dell'uso non costa
niente: oggi nessun componente è di classe 2, e la riga di §10.6 è inerte.

## In coda: §11.7 prende una regola 4

Stesso turno perché è lo stesso tipo di emendamento.

> **Un criterio su un fenomeno dichiara prima che il fenomeno è avvenuto.** Gli
> esiti sono **tre**: `soddisfatto`, `non soddisfatto`, **`non misurabile`** — e
> il terzo **non conta come verde**.

Cinque occorrenze finora, tutte con lo stesso meccanismo — un criterio vero **per
assenza del fenomeno**:

| | il criterio | perché era vero |
|---|---|---|
| 1 | «il nucleo copre ≥ 5 % del pavimento» | 5 % era il **massimo teorico**: non poteva essere mancato |
| 2 | «0/0 elementi caldi coperti» | zero su zero non si distingue da un predicato rotto |
| 3 | il banco di §11.4 | dava un verdetto dove il fotogramma **non è misurabile** |
| 4 | il CSP di PixiJS | la galleria non aveva CSP: la prova non attraversava il confine che rompeva |
| 5 | `si_e_fermata` di `prova-catalogo.mjs` | quattro letture a zero, quindi `fermo == ancoraFermo` |

La regola era stata proposta in `ENTROPIA-AREA-CHE-NON-CE.md` e **non scritta**,
perché un emendamento dentro un turno di implementazione è ciò che le regole di
uscita vietano. Questo è il turno giusto.

## Nota sul commit

`docs/SPEC.md` portava **modifiche non committate del proprietario**: il salto di
revisione da 5.16 a 5.20 e le quattro righe di changelog 5.17–5.20, che
documentano lavoro già committato. Non era possibile aggiungere §10.6 senza
portarle dentro, e lasciarle fuori per sempre sarebbe stato peggio. Entrano in
questo commit, ed è detto qui perché non sia una sorpresa in un `git log`.
