# Il fondo della scrivania — §26.5 costruita, e le due soglie chiuse col margine

**Data:** 24 agosto 2026 · **Rollback:** `5969055`
**Precedente:** `ENTROPIA-AREA-CHE-NON-CE.md`

## La premessa che avevo sbagliato

Avevo scritto: «l'unico altro serbatoio grande è il bin 4, che è le testate».
**È falso.** Il pavimento libero è il **29,6 %** del fotogramma — è nella mia
stessa misura di occlusione — ed è tutto bin 1–2. Avevo cercato dove mettere
superficie **dentro i pannelli**, dove §10.1 pretende uno stato, e non avevo
guardato il piano di lavoro, dove §26.5 mette **oggetti posati** — che uno
stato non ce l'hanno e non devono averlo.

Verificato che il pavimento non satura, al contrario del bin 4:

```
presa dal PAVIMENTO   3,0 % → 2,320   5,5 % → 2,389   7,0 % → 2,466   9,0 % → 2,558
presa dal bin 4       2,0 % → 2,256   5,0 % → 2,307   8,0 % → 2,319 (fermo)
```

## Le due correzioni al quadro proposto

**① `--manila` e `--manila-viva` sono CALDI**, e il caldo ha un tetto.
Misurato su `tokens.css` col criterio di `densita.mjs` (r > b+15 e L > 30):

```
--icona       #a2adb1  L 171,0  r 162 b 177   freddo
--icona-viva  #d4dcdf  L 218,5  r 212 b 223   freddo
--manila      #b48d64  L 146,3  r 180 b 100   CALDO
--manila-viva #dcac7a  L 178,6  r 220 b 122   CALDO
```

Il caldo sta a 3,8 % col tetto a 6,0: restano **+2,2 %**, non i +4,0 % che il
quadro chiedeva fra bin 9 e bin 11. Il bin 10 (`--icona`) invece è **freddo** e
non consuma quel budget: è la leva che si può spingere.

**② Un'icona era un TRATTO, non una superficie.** `.ico__segno` disegnava il
glifo a `--icona` su fondo trasparente. Un glifo copre circa il 30 % del
proprio riquadro: nessun numero di icone avrebbe mai prodotto area. È lo stesso
difetto che la piastra del plinto aveva mostrato ieri, e la stessa correzione —
**«icone come piastre»**: polarità rovesciata, piastra chiara col simbolo scuro.

## L'esito — A/B nella stessa sessione, tre scatti per lato

I sorgenti sono stati messi via con `git stash` fra i due blocchi, così le due
misure vedono la stessa macchina e lo stesso carico.

| | dev.std | entropia | L>60 | L>120 | caldo |
|---|---|---|---|---|---|
| PRIMA 1 | 33,00 | 2,19 | 25,4 % | 5,3 % | 3,8 % |
| PRIMA 2 | 32,90 | 2,18 | 25,3 % | 5,3 % | 3,8 % |
| PRIMA 3 | 32,90 | 2,18 | 25,3 % | 5,3 % | 3,8 % |
| **DOPO 1** | **34,30** | **2,22** | **26,1 %** | 5,9 % | 3,8 % |
| **DOPO 2** | **33,95** | **2,22** | **26,0 %** | 5,7 % | 3,85 % |
| **DOPO 3** | **34,35** | **2,23** | **26,1 %** | 5,9 % | 3,8 % |
| soglia | 32 | **2,40** | 25 | — | 3–6 |

**Δ dev.std +1,2 · Δ entropia +0,04 · Δ L>60 +0,75 · caldo invariato.**

**Le due soglie che passavano adesso passano col margine**, che è ciò che il
proprietario ha chiesto: dev.std da **+0,9 a +2,2**, `L>60` da **+0,4 a +1,1**.
Erano due atterraggi nei centesimi; adesso non lo sono.

⚠️ **Un settimo scatto, scartato.** Prima dell'A/B una singola esecuzione aveva
dato dev 32,05 · H 2,16 · L>60 24,7 %, cioè un peggioramento. Era un fotogramma
sfortunato: la telemetria disegna l'area sotto la curva della CPU, che a quel
momento era all'1,7 % invece del 3,6 %, e l'area riempita si restringe con lei.
**Un campione non è una misura** — è la terza volta oggi, e l'A/B a sei scatti
esiste per questo.

## L'entropia — 2,22 su 2,40, ancora aperta

Il modello prevedeva +0,14 per il 3 % al bin 10. Misurato: **+0,04**, perché le
dieci piastre valgono **0,8 %** e non 3 %.

```
bin 10   0,2 % → 1,0 %     le dieci piastre
```

Dieci piastre da ~40×40 px sono l'1,24 % di area geometrica; il glifo scuro
dentro ne toglie un terzo. Per arrivare a 2,40 servirebbe **quattro volte**
quell'area, cioè quaranta oggetti — e nelle radici consentite ce ne sono
**quattro** (`~/JARVIS` una cartella, `~/Scaricati` tre voci, `~/Documenti`
vuota), più i dieci moduli registrati.

L'entropia resta **aperta e non aggiustata**. Ma il divario non è più solo
diagnosticato: adesso il pavimento **sa portare superficie**, e ogni oggetto
che ci finisce ne aggiunge.

## Che cosa è stato costruito

**① `desk/icone.js` — le icone diventano piastre.** `.ico__segno` passa da
glifo colorato a piastra piena: `background: var(--icona)`, simbolo a
`--bg-void`, ombra di contatto (ammessa da §10.1: la piastra copre il
pavimento). I file tengono il manila di §26.5. È la stessa polarità rovesciata
delle piastre del plinto, e per la stessa ragione: un oggetto **posato** si
distingue da un pannello proprio perché il suo fondo è più chiaro del segno.

**② `desk/moduli.js` — la scena `avvio` dichiara un fondo.** Dieci icone, una
per modulo registrato, in fila sul bordo basso a destra del catalogo. Una scena
è una disposizione **dichiarata**: dichiarava quali pannelli si aprono, adesso
anche che cosa è posato sul piano. `scrivania.js` la applica dopo i pannelli
(le icone stanno sotto, `--z-icone` 5); `app.js` collega `posaFondo` a
`icone.ripristina`, che accetta già quella forma.

Non sono segnaposto: ogni voce rimanda a un modulo **registrato in `MODULI`**.
E la duplicazione col catalogo è voluta — §26.5 la mette per prima: «l'icona
nel catalogo NON sparisce, il catalogo è l'indice e la scrivania è il piano».

## Il difetto peggiore: la scena resuscitava un'icona rimossa

La prima stesura faceva posare il fondo a `applicaScena`, chiamando
`ripristina()`. Due difetti dentro, e li ha trovati
`TestIconeVere::test_10_riavviato_il_core_e_ANCORA_LI` — l'unico test che
riavvia il core davvero.

**① Riscriveva le coordinate.** Un'icona trascinata dall'utente tornava al
posto dichiarato dalla scena a ogni riavvio. §26.5 lo liquida in una riga:
«un'icona trascinata che al riavvio torna dov'era è **peggio** di non poterla
trascinare».

**② Riportava indietro ciò che era stato tolto.** Corretto il primo difetto
— posare solo ciò che manca — restava il secondo, più insidioso: la prova
rimuove `agenti` trascinandola sul catalogo (§26.5), e al riavvio la scena la
rimetteva. **Nove icone prima della chiusura, dieci dopo.** Rimuovere qualcosa
e ritrovarsela è peggio del non poterlo rimuovere.

E il guardare *quando* si posa non bastava: `apriIniziale()` compone **prima**
che `ui.layout` arrivi, quindi al momento della scena il pavimento è vuoto per
costruzione, sempre. Guardare se è vuoto lì non significa niente.

**La regola che regge**, e sta in `app.js` dove il layout arriva, non nella
scena: *il fondo dichiarato è un **default**, e vale solo se il layout non ne
porta uno.* Un piano **mai apparecchiato**, non un piano **sgombrato**.

⚠️ Il caso che non copre, dichiarato: chi togliesse a mano **tutte** le icone
se le ritroverebbe. Distinguere «mai apparecchiato» da «svuotato apposta» vuole
un dato che il core non tiene — `layout.json` assente e `layout.json` vuoto
sono oggi la stessa cosa.

## Due difetti trovati dal ciclo §11.7, non dal codice

**① La fila era sotto il pannello `file`.** Al primo scatto le icone stavano a
y 668 e il pannello `file` — 844..1436 in x, fino a y 715 — ne copriva **otto su
dieci**: si vedevano le etichette e non le piastre. L'occlusione contava 19
icone coperte su 21. *Un'icona che non si vede non è un oggetto posato, è un
oggetto perso.*

Portata a 716, e poi a **700**: a 716 il core le riportava a 703 — `adatta()`
taglia contro l'area dichiarata, e 716 più l'altezza dell'icona la sfonda. *Una
coordinata che il core corregge non è una coordinata: è una richiesta.*

**② `ripristina()` lasciava elementi orfani nel DOM.** Ogni voce ricreata nasce
con `el: null`, quindi `disegna()` gliene fa uno nuovo — e quello di prima resta
attaccato al documento, invisibile al modello e visibilissimo a schermo. Finché
quella funzione serviva solo al ripristino all'avvio non poteva succedere: la si
chiamava una volta. Da §26.5 la chiama **ogni applicazione di scena**, e due
scene di fila hanno portato le icone da 21 a 31 — contate dall'occlusione, non
dedotte. Adesso l'elemento vecchio si toglie prima.

## Limiti dichiarati

- **Le etichette si troncano a sei caratteri**: «Teleme…», «Core s…», «Globo …».
  `.ico` è largo 49,5 px — il 9 % della larghezza del catalogo, misurato sul
  riferimento — e `--t-micro` non ci fa stare di più. Il nome intero resta nel
  `title`, come per le tessere del catalogo (§26.3). Allargare l'icona sarebbe
  una terza decisione di design, fuori dal budget di due componenti di questo
  turno.
- **Il ciclo di vita è: il default posa una volta, poi comanda la
  persistenza.** Provato con un riavvio vero (`prova-icone.mjs`, undici test su
  undici verdi), non simulato.
- ~~Lo scatto misurato non mostra la disposizione dichiarata~~ ✅ **risolto
  pulendo il layout**, vedi sotto.

---

# La pulizia del layout, e lo scatto rifatto

Lo scatto misurato portava l'arrangiamento lasciato da `prova-icone.mjs`, che
le icone le trascina apposta. Ispezionato
`~/.local/share/jarvis-os/layout.json`, i residui erano **due** e non di più:

| | |
|---|---|
| `avvio` a (396, 331) | un **nome di scena usato come nome di icona**. Non è un modulo registrato: `etichettaDi()` non lo trova in `MODULI` e ripiega sul nome grezzo. È il residuo che il turno 1 aveva contato |
| `console` a x **773** invece di 892 | trascinata dalla prova. È la sovrapposizione con `telemetria` che si vedeva nel ritaglio |

Le altre nove erano già alle coordinate dichiarate.

**Tolto l'intero fondo** — `icone` e `cartelle` a zero, i dieci pannelli
intatti — con copia in `layout.json.prima-della-pulizia-fondo`, che è la
convenzione già in uso in quella cartella (`.prima-del-nucleo`,
`.prima-della-scena`, `.scena-a-800`).

Al primo avvio successivo il default ha riposato la fila, e il core l'ha
riscritta su disco:

```
telemetria 756 700   agenti 824 700   console 892 700   file 960 700
sorgente 1028 700    cartella 1096 700   browser 1164 700   news 1232 700
meteo 1300 700       globo 1368 700
```

Passo 68 esatto, y identica per tutte, **0 su 10 coperte** dall'occlusione.
È anche la prova del ciclo di vita: **il default posa una volta, poi comanda la
persistenza** — le coordinate su disco vengono dal default, non dalla scena
riapplicata.

Densità invariata: **dev.std 34,1 · entropia 2,23 · L>60 26,1 % · caldo 3,8 %**.
I residui sporcavano la fotografia, non la misura.
