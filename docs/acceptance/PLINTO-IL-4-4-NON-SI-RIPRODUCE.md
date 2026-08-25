# Il 4,4 % non si riproduce — e i 32 px erano giusti

**Rollback:** `d77c7dd`
**Richiesta:** rimpicciolire le icone della barra delle applicazioni, e chiudere
lo 0,006 di entropia.
**Esito: icone fatte e misurate. L'entropia NON è chiusa — il divario è passato
da 0,006 a 0,023, e la causa è la correzione stessa.**

---

## 1. Le icone erano il doppio del riferimento

Misurato con un righello su entrambe le immagini, non a occhio. Fascia del
plinto, soglia sopra il fondo della lastra, gruppi contigui:

| | lato | % della larghezza | passo | % |
|---|---|---|---|---|
| `famiglia-a/01` | 20 px (5 piastre) | **2,22 %** | 47 px | 5,22 % |
| nostro, prima | 65 px (3 piastre) | **4,23 %** | 123 px | 8,01 % |
| nostro, dopo | 33 px (5 piastre) | **2,15 %** | 68 px | 4,43 % |

A soglia L>50 e L>60 il riferimento dà stabilmente **cinque** gruppi di
larghezze `[20, 15, 19, 20, 21]`, mediana 20 su 901.

### Da dove veniva il 64

`catalogo.js` fondava `--piastra: var(--s-5)` su questa frase:

> «40 px su 901» è il 4,4 % della larghezza, e il 4,4 % dei nostri 1536 fa 68.

**Quel 4,4 % non si riproduce.** Misuro 2,22 %, cioè la metà. Su quel numero il
plinto era stato portato **da 32 a 64**, e il file dichiarava i 32 px «sbagliati
da questo stesso file». Erano giusti: 2,22 % di 1536 fa 34 px, e `--s-4` è 32,
cioè il 2,08 % — **0,14 punti di scarto contro i 2,01** che il 64 lasciava
aperti.

### E le cinque sono tornate

Il file aveva scritto: «CINQUE PIASTRE DA 68 NON CI STANNO… delle due misure del
riferimento una doveva cedere. Cede *cinque*». Quel compromesso nasceva dal 64.
Col lato vero l'aritmetica cambia segno:

```
5 piastre a passo 68:  4x68 + 32 = 304 px sui 316 della lastra = 96 %
```

**Non è una scelta di composizione presa in questo turno: è un vincolo che
spariva.** Cinque è anche il conteggio del riferimento, quindi delle tre misure
— lato, conteggio, varco/lato — due combaciano e la terza sbaglia di 0,23. Con
quattro piastre ne combacerebbe una e la terza sbaglierebbe di 0,53.

## 2. Quanto è costato, misurato

| | prima | dopo il plinto | dopo la luce |
|---|---|---|---|
| **entropia** | 2,3940 | 2,3697 | **2,3772** |
| **`L>60`** | 25,1 % | 24,64 % | **24,64 %** |
| dev.std | 34,86 | 33,5 | 34,0 |
| caldo | 3,8 % | 3,8 % | 3,8 % |

**Due criteri erano puntellati dall'errore di misura.** `L>60 ≥ 25 %` passava
per 0,1 punti, e quei 0,1 punti erano tre piastre grandi il doppio del dovuto.
Tolto l'errore, il criterio è sotto: 24,64 %.

Dirlo è metà del lavoro. L'altra metà è non rimetterlo a posto ingrandendo di
nuovo le icone.

## 3. Quello che ho recuperato, e perché non è una toppa

`icone.js` dichiara che l'icona libera è «come le piastre del plinto». La
somiglianza si fermava alla polarità: la piastra del plinto porta un gradiente
verticale brevissimo — `--icona-viva` (L 219) sopra, `--icona` (L 171) sotto —
che `catalogo.js` giustifica così:

> Non è decorazione, è la stessa luce del pavimento letta su un oggetto che gli
> sta sopra.

L'icona libera è lo stesso genere di oggetto — sta sul pavimento, e ha
`--ombra-contatto` proprio perché lo **copre** — e non aveva quella luce. Due
oggetti della stessa classe illuminati da due sorgenti diverse: un'incoerenza,
non una scelta.

Corretta: **H 2,3697 → 2,3772**, `+0,0075`. Audit del montaggio `chrome`
pulito, 0 elementi fuori sistema, 0 letterali.

## 4. Lo 0,006 non è chiuso, ed è diventato 0,023

Lo dico senza girarci intorno: **la richiesta non è soddisfatta.** Il divario
era 0,0060 e adesso è **0,0228**, e la causa è la correzione delle icone, che
era l'altra metà della stessa richiesta.

Serve un elemento di **~4 700 px a L 176-223** — un quadrato di 67 px — e
chiuderebbe **entrambi** i criteri insieme:

```
    bin 11 (L 176-191): 0,400 % = 5173 px  ->  L>60 25,04 %
    bin 12 (L 192-207): 0,368 % = 4761 px  ->  L>60 25,01 %
    bin 13 (L 208-223): 0,355 % = 4596 px  ->  L>60 24,99 %
```

### La strada c'è, ed è già scritta nel repo

Non l'ho presa perché è una decisione sul linguaggio della scrivania, non una
mossa sulla metrica — ma le prove convergono da due direzioni indipendenti.

**Dalla misura.** Dove il riferimento tiene l'area chiara, griglia 6×8 di pixel
L≥176: righe 1 e 3, colonne 0-5, al **30-47 %**. Sono i due riproduttori video e
il calendario. Contenuto fotografico che non abbiamo e che l'invariante 23
vieta di inventare. Ma i bin intermedi raccontano un'altra cosa: bin 5 (L 80-95)
riferimento **6,3 %** contro il nostro 1,3 %, bin 7 (L 112-127) **5,9 %** contro
0,4 %.

**Dal documento.** `docs/design-reference/README.md`, la sezione che fissa
proprio questa soglia, nomina i colori uno per uno:

> `01`, riquadro `BUSINESS`: **blocco pieno** `#336276` (L 89). Non un pannello
> con bordo: una superficie.
> `05`, colonna `MARKET DATA`: righe alternate su fondo pieno, con il valore in
> monospace a destra. **È esattamente la forma che devono prendere le nostre
> tabelle.**

`#336276` **è** il nostro `--fill-2`, e sulla scrivania copre lo **0,26 %**:
un token dichiarato per «pannello acceso, selezione» che non riempie quasi
niente. `SORGENTI` e `FILE` sono le nostre tabelle, con dati veri, e il loro
fondo è il corpo del pannello.

Dare alle tabelle il fondo pieno del riferimento vale, sulla sola `SORGENTI`,
circa **39 000 px** — otto volte quello che serve. Muoverebbe `L>60`, entropia,
`25-120` e forse `caldo` in un colpo solo, e chiede il ciclo §11.7 su due
pannelli. **È un turno suo.**

## 5. §11.8, punto per punto

```
GEOMETRIA
✓ border-radius 0 — non toccato
✓ tagli a 45° — non toccati
✓ spaziature: --piastra e' --s-4, PASSO 68 e' multiplo di 4
✓ pesi di linea — non toccati
COLORE
✓ tutti da tokens.css — audit di `chrome` pulito
✓ caldo 3,8 % < 10 %
✓ tinte ≤ 3
✓ il gradiente e' quello gia' accettato del plinto, applicato all'oggetto
   che lo stesso file dichiara gemello
✓ ZERO alone, bloom, glow
✓ ombra-contatto: la piastra copre il pavimento — il solo caso concesso
TIPOGRAFIA
✓ non toccata
CONTENUTO
✓ dati veri — le cinque piastre sono moduli veri della giostra
✓ etichette e piedi tecnici intatti
✓ densita': dichiarata sotto, non aggiustata
MOVIMENTO
✓ la giostra risponde al gesto, come prima
TECNOLOGIA
✓ non toccata
```

Verificato **guardando**: le piastre misurano 34 px di altezza — glifo 32 più il
filo di 2 — cioè non sono tagliate dal ritaglio della scena. La prima lettura
dello scatto diceva il contrario, e sbagliava: la banda di misura includeva le
tessere della griglia sopra il plinto.

## 6. Verifica

| | |
|---|---|
| `npm run shot -- chrome` | audit 0 fuori sistema, 0 letterali · OK |
| `npm run scrivania:fixture` | EXIT=0, `scattiIdentici` true |
| `npm run verifica:catalogo` | §26.9 criterio 3, 6 condizioni su 6 |
| `uv run pytest -q` | **585 passed** |

## 7. Dichiarato aperto

- **Entropia 2,3772 su 2,40** — divario 0,0228. Era 0,0060 prima di questo
  turno, e l'ha allargato la correzione delle icone.
- **`L>60` 24,64 % su 25 %** — passava per 0,1 punti grazie a tre piastre
  grandi il doppio del dovuto.
- **Il `4,4 %` resta un numero senza fonte.** Non l'ho ritrovato in
  `famiglia-a/01` con nessuna soglia. Se venisse da un'altra immagine della
  famiglia, la misura di §1 va rifatta lì.
- Il riferimento sta a **42 %** di `L>60` e la soglia è 25: il README lo chiama
  «il divario più grande dell'intera revisione», e lo è ancora.
