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

> ### ⚠️ I numeri qui sotto sono di prima di §26.3, e nel mezzo il criterio è caduto
>
> Sono stati misurati con le tessere grandi (~100×70) e un catalogo largo il
> doppio. §26.3 ha portato le tessere a **20×20**, e a quel punto quarantuno
> stavano tutte dentro la vista: `contenuto 422` contro `vista 422`,
> `scorrevole false`, l'inerzia mai partita. **Il criterio è rimasto vuoto dal
> 22 al 24 agosto 2026**, e nessuno se n'è accorto perché la prova stampava un
> JSON e usciva 0 comunque.
>
> Rimisurato il 24 agosto con le tessere a **48×32**
> (`SUPERFICIE-CHIARA.md`), e adesso la prova **asserisce**:
>
> ```
> tessere            41          (40 di prova + 1 vera)
> vista / contenuto  422 / 1092  → scorrevole
> indicatore         38,64 %     = 422/1092, esatto a due decimali
> inerzia            -211 → -397 → -543 → -543
> budget             mediana 16,7 ms · max 17,3
> §26.9 criterio 3 soddisfatto — 6 condizioni su 6, exit 0
> ```
>
> `npm run verifica:catalogo`. Rimessa la regressione apposta, esce **1** e
> nomina le quattro condizioni cadute.

```
tessere            41          (40 di prova + 1 vera)
vista / contenuto  988 / 4227  → scorrevole          ← storico, pre-§26.3
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


---

# Il plinto diventa una giostra — 22 agosto 2026

## La decisione, e le due che sono state scartate

Il plinto aveva un tetto di cinque icone, preso dal riferimento. Con nove
moduli i quattro fuori dal taglio **non erano raggiungibili dal plinto in
nessun modo** — non nascosti dietro un gesto: assenti.

Il proprietario ha scelto fra tre uscite:

| | scartata perché |
|---|---|
| plinto fisso col massimo che ci sta | ruba alla griglia, che §26.3 ha già dovuto difendere due volte |
| giostra **più un registro** tabellare (il mockup di famiglia-d) | gli stessi nove nomi comparirebbero **tre volte** a schermo — griglia, registro, plinto |
| **giostra sola** ✅ | l'elenco completo c'è già, ed è la griglia |

E con essa cambia che cosa il plinto **promette**: non è l'indice, è il lancio
rapido. §26.3 è stata aggiornata, perché diceva il contrario.

## Che cosa è stato costruito

- `PLINTO_MAX` da 5 a `Infinity`: la giostra le porta tutte.
- Quattro piastre in vista, passo **80 px** (`--s-5 + --s-3`) fra i centri.
  Con piastre da `--s-4` fanno 272 px su un bordo lontano di 399: il **68 %**,
  contro il 66 % misurato sul riferimento.
- Le due esterne ruotano di **34°** e arretrano di **30 px**, con la caduta
  concentrata (esponente 1,6).
- **Tutte e quattro si premono dove sono**: nessuna piastra «a fuoco».
- **Aperto = piastra** (`--icona` con il simbolo a `--bg-void`), **chiuso =
  simbolo nudo**.
- Rotella: una piastra per scatto. Trascinamento: continuo, con aggancio alla
  più vicina al rilascio, soglia 4 px come per le icone libere.

## I due difetti trovati misurando, non guardando

**1. La prospettiva non arrivava alle piastre.** `perspective` sta su
`.cat__plinto` e vale solo per i **figli diretti**; le piastre sono nipoti,
perché in mezzo c'è `.cat__azioni`. Il difetto è silenzioso: la profondità
viene applicata, ma piatta. Misurato sul DOM vivo, i centri proiettati
cadevano a ±134 px invece dei ±120 calcolati — cioè esattamente la x **non**
proiettata — e i passi risultavano `94, 81, 94` invece di `80, 80, 80`.

Ingannava anche una cosa vera: le larghezze *cambiavano* fra piastre interne ed
esterne, 27 contro 32 px. Non era lo scorcio: era il coseno della rotazione.
`transform-style: preserve-3d` sul contenitore, e i passi sono tornati
`81, 80, 80`.

**2. Due padroni per la stessa proprietà.** L'animazione di cambio linguetta
girava su **tutte** le piastre nuove e le riportava a `opacity: 1`, dopo che
`disponi()` aveva spento le cinque fuori dalla finestra. Misurato: nove piastre
a opacity 1 e quattro sole con `pointer-events` — cinque visibili e non
premibili, cioè il contrario di ciò per cui la finestra esiste.

Corretto animando **solo** le piastre che la giostra ha lasciato in vista. È la
stessa regola che avevo scritto nel commento per la `y` e non avevo applicato
all'`opacity`: **una proprietà, un padrone.**

## I bersagli in pixel erano sbagliati, e restano da decidere

Le due misure che §26.3 chiama «la differenza singola più grande fra noi e il
riferimento» sono state trasferite in **pixel** da un'immagine larga 901 su una
finestra larga 1536:

| | trasferito | vale davvero | costruito |
|---|---|---|---|
| tessera della griglia | «28×14 px» | **8,2 % della larghezza** del pannello = 50×33 | 20×20 |
| icona del plinto | «40 px» | **4,4 % della larghezza** = 68 px | 32 px |

Meno della metà, in entrambi i casi. Non sono state corrette qui: la tessera è
una decisione sulla griglia e la piastra è l'unità di passo della giostra —
cambiarle cambia la geometria di §26.3, ed è una decisione, non una rifinitura.
La regola che impedisce il prossimo trasferimento sbagliato sta in
`docs/design-reference/README.md`, «un numero in pixel del riferimento non è un
bersaglio».

## Esito

```
node scripts/audit.mjs chrome        violazioniCalcolate 0 · violazioniSorgente 0
uv run pytest -q                     536 passed, 20 skipped
uv run pytest tests/eval_*.py …      236 passed
```

Ciclo §11.7 eseguito: reso, **scattato e guardato** — è così che si è vista la
quinta piastra visibile e non premibile, che nel DOM sembrava a posto.
