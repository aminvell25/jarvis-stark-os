# Il catalogo — esito · §26.10 punto 4

**Data**: 19 agosto 2026 · **Riferimento**: `SPEC-26-AMBIENTE-UNICO.md` §26.3 e
§26.4, `famiglia-a/01` · **Precedente**: `ADR-010.md`
**Test**: **517 + 220** verdi · **SPEC**: rev **5.14**

---

## Che cos'è, e che cosa ha sostituito

§26.3 in una riga: **unifica la barra delle applicazioni e il file manager**,
che erano due richieste separate. Sono lo stesso contenitore con due linguette.

Quindi il dock ha **ceduto l'indice**: gli otto moduli sono la linguetta
`MODULI`, le azioni stanno sul plinto, e il dock è diventato una striscia di
stato — `TUTTO · 14 pannelli | T2 inerte`. Due elenchi degli stessi otto
moduli a schermo sarebbero stati due posti in cui la stessa verità può
divergere.

⚠️ Il criterio A di §13 — «le otto voci aprono e chiudono il proprio modulo» —
**non è stato cancellato: si è spostato**. `--verifica-scrivania` lo prova
sulle tessere del catalogo. Cancellarlo sarebbe stato il modo più comodo di
far tornare i conti.

## Sta nella cornice, non fra i pannelli

Il catalogo è l'**indice** dell'ambiente, e un indice che si può seppellire
smette di essere un indice — la stessa ragione per cui §26.5 dice che un'icona
tirata fuori non sparisce dal catalogo. Vive in `#scrivania`, sopra i pannelli.

Il suo contenitore ha `pointer-events: none` e solo il catalogo lo riprende:
senza, metà schermo sarebbe una lastra invisibile che intercetta i clic
destinati ai pannelli sotto.

## L'anatomia, dal riferimento

| | | fatto |
|---|---|---|
| ① | frecce di navigazione | ✅ (scorrono il nastro — la cronologia è del file manager, punto 9) |
| ② | due campi percorso **riempiti** | ✅ `--fill-3`, testo scuro: la cosa più chiara della testa |
| ③ | linguette a **separatore diagonale** | ✅ bordo ruotato di uno pseudo-elemento, non un glifo |
| ④ | griglia di tessere, scorrevole | ✅ |
| ⑤ | **plinto in prospettiva** | ✅ `rotateX(52deg)`, CSS 3D come §11.4 |
| ⑥ | cartelle manila 2×2 fuori dal pannello | ❌ è il punto 5 |

Il separatore diagonale è un **bordo ruotato**, non il carattere `╱`: un glifo
dipenderebbe dal font e si disallineerebbe al primo cambio di corpo.

---

## §26.9 criterio 3, misurato con quaranta file VERI

> «Con 40 icone la griglia scorre, l'inerzia decelera e si ferma, nessuna
> scrollbar di sistema è visibile nello screenshot.»

`scripts/prova-catalogo.mjs` crea quaranta file nella workspace, misura, e li
toglie. Inventare quaranta voci finte avrebbe provato lo scorrimento senza
provare che il catalogo sappia mostrare **quello che c'è davvero** — che è la
metà interessante, visto che la linguetta `FILE` legge `fs.list` dal core.

```
tessere            41          (40 di prova + 1 vera)
vista / contenuto  988 / 4227  → scorrevole
indicatore         23,37 %     = 988/4227, proporzionale al visibile
```

**L'inerzia**, misurata in quattro istanti dopo il rilascio:

```
subito     −494
+200 ms    −709     ha continuato
+1,4 s     −887     si è fermata
+1,8 s     −887     e resta ferma
```

**Nessuna barra di sistema**: `overflow: hidden` sulla vista, e zero elementi
dentro il catalogo che scorrerebbero da soli.

**Budget**: durante un trascinamento vero di 40 passi, mediana **16,7 ms** —
il vsync — e massimo 29,1. Il nastro si muove con `transform: translateX()` su
un contenitore solo: cambia la composizione, non il layout.

---

## ⚠️ Due difetti, e nessuno dei due l'hanno trovato i test

### R90 — la griglia si ricostruiva a ogni cambio di stato

`--verifica-scrivania` diceva che **otto voci su otto non commutavano mai**.
Non era il criterio: era il catalogo.

`disegna()` rifaceva l'intera griglia a ogni `osserva()` — cioè a ogni
pannello che si apre, si chiude o **prende il fuoco**. Con quarantuno tessere
significava distruggere e ricreare quarantuno nodi decine di volte al minuto:
si perdevano il fuoco della tastiera e lo stato di hover, e il pulsante che si
stava premendo veniva staccato dal documento **a metà del clic**.

Adesso il contenuto si ridisegna solo quando cambia — linguetta nuova, elenco
di file nuovo — e lo stato si aggiorna sul posto.

È il tipo di difetto che un test sul registro non vede mai: il registro era
giusto, era il DOM a sfaldarsi sotto le dita.

### R91 — il catalogo era dietro i pannelli, e non si vedeva affatto

Il primo scatto della scrivania col catalogo mostrava… nessun catalogo. Il suo
contenitore aveva `display: contents`, che gli toglie il box — e con esso lo
z-index che `app.css` dà a `#scrivania > *`. Veniva disegnato **dietro** i
quattordici pannelli.

Un errore da una riga che a occhio sembra «il componente non funziona», e che
si risolve guardando: c'era, con le sue otto tessere, in fondo alla pila.

---

## E due difetti nelle prove appena scritte

**Il backtick, l'ottava volta.** `display: contents` scritto fra apici inversi
dentro il commento CSS del catalogo: chiude il template literal, e il renderer
muore con `SyntaxError: Unexpected identifier 'display'`. Il test lo trova in
un decimo di secondo — ma io l'avevo eseguito **prima** di introdurre
l'errore, e dopo ho controllato solo `app.js` con `node --check`, che non
guarda i file importati.

**Il percorso della workspace, preso male.** `prova-catalogo.mjs` chiedeva la
workspace a `load_settings()` e prendeva `out.trim()` intero — ma structlog
scrive `settings_caricate` su **stdout**, e il percorso diventava
«2026-08-19 17:13 [info] settings_caricate … /home/…/JARVIS». `mkdirSync` ha
creato una directory con quel nome dentro il progetto, i quaranta file sono
finiti lì, e la prova ha misurato **un** file concludendo che la griglia non
scorre.

Il difetto era nella prova, non nel catalogo. Ma per un quarto d'ora ha detto
il contrario, ed è esattamente il modo in cui una misura sbagliata fa
riscrivere codice che andava bene.

---

## L'audit, e i due token nuovi

`--icona` (L 171) e `--icona-viva` (L 219) — misurati sul plinto del
riferimento. Servono perché **nessuno dei token esistenti arriva lassù senza
essere il colore del dato**, e la differenza è misurata: la fascia del
catalogo nel riferimento ha il **26,2 %** di superficie accesa, il nostro dock
di ieri il **2,8 %**, perché le nostre «icone» erano testo a L 96.

Come per i riempimenti, `categorizza()` va esteso o il primo pulsante che usa
il token che §26.3 gli assegna risulta fuori sistema. E come allora, la
fixture `conforme` li usa bene e `non-conforme-banda` continua a cadere: il
grigio inventato resta magenta.

Audit: `chrome` (barra + catalogo + dock) **0 violazioni**, ai due livelli.

---

## ❌ NON VERIFICATO

1. **Le linguette `SCENE` e `SISTEMA` sono stati vuoti dichiarati.** Dicono
   che cosa manca e dove arriverà (§26.6, §26.7). Sono l'invariante 23
   applicata, non contenuti: il catalogo con quelle due linguette piene non
   l'ha visto nessuno.
2. **La linguetta `FILE` elenca e non apre.** Cliccare una voce porta al
   pannello file manager, che è ciò che oggi sa aprire un file. Aprire dal
   catalogo è §26.8, punto 9.
3. **Le tessere hanno tutte lo stesso segno.** Un quadrato pieno, uguale per
   tutti. È deliberato — non invento quattordici pittogrammi — ma il
   riferimento distingue le sue icone, e a distinguere le nostre resta solo
   l'etichetta.
4. **Il plinto è un trapezio, non una lastra illuminata.** `rotateX(52deg)` su
   `--fill-1`: la prospettiva c'è e si legge, ma nel riferimento la lastra ha
   un bordo anteriore acceso e un riflesso. Non li ho aggiunti: sarebbero
   stati un gradiente, e §11.8 ne ammette solo quello della ricetta del vetro.
5. **Le etichette delle azioni sul plinto sono al limite.** `--txt-ghost` su
   `--fill-1` è 3,03:1 — sopra la soglia UI, sotto quella del testo normale.
   Si leggono; a corpo 8,5 px non è molto.
6. **Lo scorrimento è stato provato con un solo gesto.** Un trascinamento
   veloce da destra a sinistra. Non ho provato il lancio corto, quello
   contrario, o il caso in cui il rilascio avviene già oltre il fondo corsa.
7. **La rotellina non è stata provata con un dispositivo vero.** Il codice c'è
   e legge `deltaX`/`deltaY`; a mandare l'evento sarebbe stato un
   `dispatchEvent`, che è la simulazione che il passo 0 di §11.7 dice di non
   contare come prova.

---

## Riepilogo

| | |
|---|---|
| Test | **517 + 220** verdi |
| Criterio 3 di §26.9 | **chiuso**, con 40 file veri |
| Icone nella griglia, misurate | **41**, contenuto 4227 px in 988 di vista |
| Inerzia | continua dopo il rilascio, decelera, **si ferma** |
| Barre di scorrimento di sistema | **zero** |
| Budget durante il trascinamento | **16,7 ms** — il vsync |
| Difetti trovati dalla verifica dal vivo | **2** — R90, R91 |
| Difetti nelle prove appena scritte | **2** — il backtick, e il percorso preso da stdout |
| Token aggiunti | **2** — `--icona`, `--icona-viva` |
| Elenchi degli otto moduli a schermo | 2 → **1** |
