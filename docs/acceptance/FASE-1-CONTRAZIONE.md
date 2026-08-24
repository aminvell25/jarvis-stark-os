# Fase 1 — i pannelli vuoti si contraggono

**Data:** 24 agosto 2026 · **Rollback:** `0a07541`
**Piano:** la FUI avanzata, fase 1

`DIVARIO-PREMIUM.md` §5, impatto ALTO, aperto. Il documento lo chiama *«la cosa
che più fa sembrare finto l'insieme, più di qualunque scelta cromatica»*, e
§11.6 regola 3 lo dice come regola: *«Se un pannello ha poco da dire, lo
rimpicciolisca — non lo riempia di spazio.»*

## Il contratto: il pannello dichiara di essere VUOTO, non quanto è grande

⚠️ **Nessun contratto nuovo.** Ciambella, tabella, news e source scrivono già
`data-stato="vuoto"` da sempre. La scrivania legge **quello**, e la dimensione
la dichiara `moduli.js` con `cellaRidotta`.

Aggiungere un `superficie()` accanto a `data-stato` sarebbe stata **una seconda
dichiarazione della stessa cosa**, cioè il modo esatto in cui le due si slegano.
Il pannello dice *sono vuoto*; l'ambiente decide che cosa farne; il modulo dice
*quanto piccolo*. Tre verità, tre proprietari.

## E si contrae solo un pannello INTATTO

Un pannello che l'utente ha spostato o ridimensionato **è suo**. Rimpicciolirlo
perché si è svuotato sarebbe R82 daccapo: una regola dell'ambiente che cancella
una decisione della persona un secondo dopo che l'ha presa.

## Provato nell'app vera — `npm run verifica:contrazione`

```
ok  il pannello VUOTO nasce alla cella ridotta      472 px, attesi ~472
ok  arrivato il contenuto torna alla cella piena    952 px, attesi ~952
ok  la mano dell'utente cambia la dimensione        700x400
ok  e svuotandosi NON si contrae: la mano vince     700x400
§11.6 regola 3 soddisfatta — 4 condizioni su 4
```

**Controllo**: tolta `cellaRidotta` al browser, la prova esce **1** e nomina la
condizione caduta. La quarta riga è quella che conta: è la sola che protegge
l'utente dall'ambiente.

## La contrazione nella scena `avvio` è stata PROVATA E RITIRATA

Il piano la dava per acquisita. Misurata su `news`, cella `[8,2,4,1]` → `[10,2,2,1]`:

| | prima | con la contrazione |
|---|---|---|
| pavimento nudo | 29,0 % | **32,4 %** |
| `L>60` | 26,1 % | **24,4 %** — **sotto la soglia di 25** |
| entropia | 2,23 | 2,18 |
| dev.std | 34,1 | 33,2 |

`news` scende davvero da 472 a 232 px — il meccanismo funziona. Ma **in una
scena curata la contrazione non restituisce spazio a nessuno: lascia un buco, e
il buco costa più di quanto il pannello vuoto valesse.** Un criterio che passava
cade.

**La regola vale dove la dimensione la decide il modulo** — cioè quando lo si
apre dal catalogo — **non dove l'ha decisa chi ha composto.** Chi vorrà
contrarre anche nella scena dia prima la cella liberata a qualcuno.

## Tre difetti miei, tutti trovati misurando

**① La cella ridotta veniva da una fonte diversa da quella piena.** Il ripiego
era `composizione.get(id)?.cellaRidotta ?? def.cellaRidotta`: se una scena
dichiarava la cella piena e non quella ridotta, si prendeva quella del
**modulo** — che appartiene a un'altra composizione. `news` finiva a
`[964, 36, 232, 679]`, una colonna alta tutta la scrivania in un punto che
nessuno aveva chiesto, e `L>60` crollava a **22,75 %**. Una cella piena e una
ridotta prese da due posti diversi non sono due dimensioni della stessa cosa:
sono due layout mescolati.

**② Alla nascita si chiedeva «l'ha toccato l'utente?».** Un pannello appena
creato non può essere stato toccato da nessuno, e la domanda faceva danno:
`areaComposizione` e `area()` differiscono per un arrotondamento e la
contrazione non partiva mai. `browser` nasceva a 952 px con
`data-stato="vuoto"` già scritto.

**③ `intatto()` e `intatta()` rispondevano a due domande diverse col metro di
una sola.** `intatta()` chiede *«la composizione è ancora come è stata
composta»*, e il metro è l'area di allora. `intatto(v)` chiede *«questo pannello
l'ha toccato l'utente»*, e il metro è l'area di **adesso**: dopo un
ridimensionamento della finestra i pannelli sono stati riadattati, e
confrontarli con l'area di prima risponde «toccati» su tutti. Col metro
sbagliato un pannello contratto **non tornava mai pieno**.

## L'etichetta del budget news — `DIVARIO §11`, chiusa

Diceva `3/3 nell'ora` accanto a un pannello vuoto, che chiunque legge come «tre
**usate** su tre», cioè il contrario: il numeratore era il **residuo**. Adesso
dice **`3 rimaste su 3 nell'ora`**. *Un'etichetta che dice il rovescio di quello
che significa è peggio di un'etichetta assente.*

## Le misure — e una contaminazione da dichiarare

⚠️ **Le prime misure di questa fase erano sporche, e la causa è la Fase 0.** I
giri a 1280 e 1920 hanno salvato le posizioni delle icone a larghezze diverse, e
al ritorno a 1536 **nove icone su dieci erano coperte dai pannelli** — bin 10
da 1,0 % a 0,3 %, dev.std da 34,2 a 33,0. Sembrava un peggioramento della Fase 1
e non lo era: è **il difetto che la Fase 0 ha appena misurato**, che colpisce le
misure di chi lo misura. Pulito il fondo (copia in
`layout.json.prima-dei-giri-di-risoluzione`), tutto torna.

Tre giri con layout pulito:

| | dev.std | entropia | L>60 | caldo |
|---|---|---|---|---|
| giro 1 | 34,1 | 2,23 | 25,65 % | 3,8 % |
| giro 2 | 34,1 | 2,23 | 25,65 % | 3,8 % |
| giro 3 | 34,15 | 2,23 | 25,75 % | 3,8 % |
| soglia | 32 | **2,40** | 25 | 3–6 |

**Effetto sulla scrivania: nessuno di misurabile**, ed è atteso — la scena non
contrae. Tutte le soglie che passavano passano ancora; l'entropia resta aperta.

⚠️ `L>60` sta a **25,7 %** contro il 26,1–26,2 % della sessione di
`FONDO-26-5.md`. Sono 0,45 punti, il margine sulla soglia resta +0,7, e **non ne
conosco la causa**: la scrivania riceve dati vivi e l'area sotto la curva della
CPU si muove con essi. Lo scrivo invece di attribuirlo a qualcosa.

## Che cosa NON è stato fatto

- **Nessun ciclo §11.7**: nella scena non cambia un pixel. Il pannello che si
  contrae si vede solo aprendo `browser` dal catalogo, e lì la prova è
  `verifica:contrazione`, non uno scatto.
- **La contrazione nella scena resta fuori**, con la misura che lo motiva.
- **`prova-contrazione.mjs` non è nella suite**: apre Electron, e la suite
  condivide il socket del core vivo. Vale la stessa regola della guardia del
  marchio — cattura manuale, e se un giorno servirà la freschezza si aggiunge
  un'impronta come per il catalogo.
