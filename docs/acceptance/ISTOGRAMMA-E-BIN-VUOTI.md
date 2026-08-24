# Nove bin su sedici sono vuoti — e la diagnosi di §6 era sbagliata

**Data:** 23 agosto 2026
**Strumento:** `node scripts/densita.mjs --istogramma <png> [riferimento.png]`
**Misura su:** `shots/scrivania/scrivania.png` contro
`docs/design-reference/famiglia-a/01-desktop-mcu-completo.png`

## Perché

Due criteri su sei restano sotto soglia: **entropia 2,17 < 2,40** e **dev.std
31,3 < 32**. L'entropia riassume l'articolazione dell'istogramma in un numero,
e un numero non dice **dove** manca l'articolazione. La domanda era «quali
livelli non ci sono», e nessuna delle sei metriche sapeva rispondere.

## La misura

```
 bin   L          nostro   riferimento    scarto
   0    0- 15       0%      5.2%     +5.2
   1   16- 31    36.9%       26%    -10.9
   2   32- 47      36%     18.5%    -17.5
   3   48- 63     2.7%     10.2%     +7.5
   4   64- 79    13.8%      8.7%     -5.1
   5   80- 95     2.4%      6.3%     +3.9
   6   96-111     3.4%      5.6%     +2.2
   7  112-127     0.4%      5.9%     +5.5
   8  128-143     0.3%      3.6%     +3.3
   9  144-159     3.5%      2.3%     -1.2
  10  160-175     0.2%      1.4%     +1.2
  11  176-191     0.2%      1.1%     +0.9
  12  192-207     0.1%      1.5%     +1.4
  13  208-223     0.1%      1.1%       +1
  14  224-239       0%      0.7%     +0.7
  15  240-255       0%      1.9%     +1.9

  bin sotto lo 0.5 %: nostro 9 su 16, riferimento 0 su 16
```

**Nove dei sedici bin sono sotto lo 0,5 %. Nel riferimento non ce n'è nessuno.**
Il 72,9 % del fotogramma sta in due bin adiacenti (L 16–47). Il riferimento non
supera mai il 26 % in un bin solo.

## Il fotogramma ha cinque livelli, la palette ne dichiara sedici

Ogni token di `tokens.css` messo nel proprio bin, accanto all'area misurata:

| bin | L | area | token dichiarati |
|---|---|---|---|
| 0 | 0–15 | **0,0 %** | *nessuno* |
| 1 | 16–31 | 36,9 % | `--bg-void` 19, `--bg-deep` 30, `--bg-panel` 31 |
| 2 | 32–47 | 36,0 % | `--bg-raised` 37 |
| 3 | 48–63 | 2,7 % | `--cy-900` 48 |
| 4 | 64–79 | 13,8 % | `--fill-1` 66 |
| 5 | 80–95 | 2,4 % | `--fill-2` 89 |
| 6 | 96–111 | 3,4 % | `--cy-700` 100, `--fill-3` 103 |
| 7 | 112–127 | **0,4 %** | `--rust` 123, `--txt-ghost` 125 |
| 8 | 128–143 | **0,3 %** | *nessuno* |
| 9 | 144–159 | 3,5 % | `--manila` 146, `--txt-dim` 146 |
| 10 | 160–175 | **0,2 %** | `--icona` 171 |
| 11 | 176–191 | **0,2 %** | `--manila-viva` 179, `--cy-500` 181, `--amber` 185 |
| 12 | 192–207 | **0,1 %** | `--cy-300` 200 |
| 13 | 208–223 | **0,1 %** | `--icona-viva` 219 |
| 14 | 224–239 | **0,0 %** | `--cy-100` 231, `--txt-primary` 231 |
| 15 | 240–255 | **0,0 %** | *nessuno* |

**Solo tre dei nove bin vuoti non hanno un token: 0, 8 e 15.** Gli altri sei
hanno un colore dichiarato che copre fra lo 0,0 % e lo 0,2 % del fotogramma.

La ragione è una sola, e si legge nella colonna dei nomi: **i token chiari sono
tutti INCHIOSTRO, mai SUPERFICIE.** `--txt-primary` a L 231 copre lo 0,0 %
perché una lettera è sottile; `--cy-500` a L 181 copre lo 0,2 % perché è un
marcatore di 4 px e un tratto da uno. Il riferimento mette gli stessi livelli
su **aree piene**.

È esattamente la distinzione che §10.5 regola 2 fa già per la testata: «una
riga di testo su fondo uguale al corpo non è una testata — è testo». Qui vale
per tutta la metà chiara della palette.

## Quanto basta — calcolato, non stimato

> ### ⚠️ Corretta il 23 agosto 2026 — la riga «oggi» diceva il modello, non la misura
>
> La prima stesura di questa tabella aveva come prima riga `| oggi | 2,17 |
> **31,6** |`. La dev.std di oggi è **31,3**, misurata. Il 31,6 è ciò che
> predice il modello, e appartiene alla dichiarazione dell'errore, non a una
> riga che dice «oggi».
>
> **E la calibrazione cambia un verdetto.** Le righe erano scritte non
> calibrate: «+3 % a `--fill-2`» dava `32,3`, e da lì la frase «le due soglie
> cadono al secondo passo». Tolto il bias, dà **32,0** — *sulla* soglia, non
> oltre. Era lo stesso difetto del 3,01 su 3,00 del marchio, in un documento
> che nasceva per denunciarlo.

L'entropia si calcola dagli stessi sedici bin del criterio, quindi la previsione
su H è **esatta**. La dev.std collassa ogni bin sul proprio centro: sul
fotogramma di oggi predice **31,64** contro i **31,3** misurati, cioè un bias di
**+0,34**. Le colonne qui sotto portano il valore grezzo del modello e quello
**calibrato** — modello meno bias — e il giudizio si legge sul secondo.

Ipotesi del modello: l'area nuova viene dai bin 1 e 2 — cioè da pavimento e
corpo dei pannelli, che insieme fanno il 72,9 %.

| passo | H | dev.std modello | **dev.std calibrata** |
|---|---|---|---|
| **oggi (misurato)** | **2,17** | 31,64 | **31,3** |
| soglia | 2,40 | — | **32,0** |
| +6 % a `--cy-900` (L 48) | 2,33 | 31,6 | 31,3 |
| +3 % a `--fill-2` (L 89) | **2,42** | 32,3 | **32,0** — *sulla* soglia |
| +2 % a `--fill-3` (L 103) | 2,47 | 33,1 | 32,8 |
| +2 % a `--manila` (L 146) | 2,52 | 36,0 | 35,7 |
| +1,5 % a `--icona` (L 171) | 2,59 | 38,5 | 38,2 |

⚠️ **Il 9 % del secondo passo è la dose MINIMA, non quella giusta**, e la
tabella non lo diceva. Raddoppiarla non aiuta: con 8 % + 4 % la dev.std
calibrata arriva a **32,1**, e se l'area venisse dal pavimento invece che dai
corpi dei pannelli scenderebbe a **30,9** — sotto soglia. Il risultato dipende
da *dove si prende l'area*, e i due casi distano 1,2 punti, più dell'intero
margine.

### La ragione, e dice dove NON conviene mettere la superficie

La luminanza media del fotogramma è **L 47,7**. La dev.std si compra con la
**distanza dalla media**, e il bin 3 ne dista otto punti.

| bin | token | ΔH per 1 % | Δdev.std per 1 % |
|---|---|---|---|
| 3 | `--cy-900` 48 | +0,035 | **+0,00** |
| 5 | `--fill-2` 89 | +0,036 | +0,24 |
| 6 | `--fill-3` 103 | +0,032 | +0,48 |
| 9 | `--manila` 146 | +0,032 | +1,65 |
| 10 | `--icona` 171 | +0,058 | **+2,18** |
| 13 | `--icona-viva` 219 | +0,061 | **+4,15** |

**Il bin 3 non muove la dev.std di nulla**, e con l'area presa dal pavimento la
abbassa. Il margine non si compra con una dose più grande della stessa cosa: si
compra sul chiaro, dove la resa per unità di area è dieci-venti volte più alta.
E il bin 3 va escluso anche per una seconda ragione, indipendente: `--cy-900` è
il riempimento delle fasce del nucleo (§25.5, cancello `e4851ae`), e il nucleo
sta **sotto** i pannelli — lo stesso token sui due ridurrebbe il confine a un
gradino di alfa.

## Tre premesse che cadono

### ① «Serve un modulo Media» — non verificabile oggi: non c'è media

`DIVARIO-PREMIUM.md` §6 prescrive un modulo che mostri anteprime reali. Le
radici consentite sono `~/JARVIS`, `~/Documenti`, `~/Scaricati`
(`config/settings.toml`), e contengono **zero** file immagine — contati, non
supposti. Un modulo Media costruito oggi mostrerebbe uno stato vuoto: corretto
per l'invariante 23, e **inutile per la densità**.

Una sonda l'ha misurato prima di scrivere codice. Miniature vere in una
striscia libera di 1536×96 (l'11,4 % del fotogramma, il rettangolo libero più
grande che non copra né un pannello né il disco):

| contenuto della striscia | H | dev.std | L>60 |
|---|---|---|---|
| niente (oggi) | 2,17 | 31,3 | 25,0 % |
| miniature dei **nostri** scatti | 2,20 | **30,0** | **24,6 %** |
| miniature del **riferimento** | 2,33 | 31,9 | 27,1 % |

I nostri scatti **peggiorano** entrambe le metriche: sono la nostra palette, e
copiarla non articola niente. Conta il contenuto, non l'area.

### ② «Il rettangolo libero è al centro» — no, è una striscia in basso

Il rettangolo libero più grande del pavimento, esclusi i sei pannelli della
scena `avvio` e il disco del nucleo (centro 768,422 raggio 162,9), è
**1536×96 a (0,716)**: una striscia alta 96 px sopra il dock. Non c'è nessuno
spazio quadrato al centro — la prima sonda ne aveva usato uno che copriva il
nucleo, e i suoi numeri erano da buttare.

### ③ «Servono `--cy-800` e `--cy-600`» — il rimando porta al documento sbagliato, e solo uno dei due riempie un buco

`PIANO-CORE-E-DENSITA.md` §7 e §9 li danno «proposti in `DIVARIO-PREMIUM.md`».
Lì **non compaiono**: le due proposte stanno in
`docs/acceptance/MOCKUP-SCRIVANIA-VIVA.md`, con valori e motivazione.

> ⚠️ La prima stesura di questa sezione diceva che il rimando era «infondato» e
> che le proposte non esistevano. È falso: esistono, in un altro file. La
> correzione è qui invece che riscritta perché è lo stesso errore che questo
> documento contesta agli altri — una riga che rimanda a memoria.

Messe nell'istogramma, le due proposte non valgono lo stesso:

| | L | bin | c'è già un token lì? |
|---|---|---|---|
| P1 `--cy-800` `#1c5f6b` | 82 | 5 | **sì**, `--fill-2` a 89 — stesso bin |
| P2 `--cy-600` `#3f97a6` | 133 | 8 | **no**: è uno dei tre bin senza nessun token |

**P1 non aggiunge un livello all'istogramma**, aggiunge un secondo colore
dentro un livello che `--fill-2` occupa già. **P2 sì**: il bin 128–143 sta allo
0,3 % e non ha alcun token.

Va detto però che nessuna delle due nasce per la densità: entrambe nascono per
il **velo della nuvola additiva dell'insegna**, e quella insegna è stata
riscritta come componente unico (`NUCLEO-CORPO-CONTINUO.md`) senza quel velo.
Il «Contro» che le accompagna — «un token nuovo per un solo consumatore è un
token che nessuno manutiene» — resta quindi in piedi e senza il consumatore che
lo giustificava.

Per le due soglie non servono comunque: la tabella qui sopra le chiude al
secondo passo con `--cy-900` e `--fill-2`, che esistono da sempre.

## Che cosa questo turno NON fa

Non applica nessuna superficie. Il **dove** — quali pannelli, quali righe,
quali celle — è una decisione di §11.6 regola 2 (*un colore deve significare*),
e va presa componente per componente col ciclo §11.7. Questo documento dice
quanto serve e a quale livello; non dice a chi.

## Limite dichiarato

Il modello sposta area **fuori dai bin 1 e 2**. Se una superficie nuova
sostituisse invece del `--fill-1` (bin 4, 13,8 %), il guadagno sarebbe minore:
quel bin è già popolato, e toglierne area abbassa H. Chi applica le superfici
misuri con `--istogramma` invece di fidarsi della tabella.
