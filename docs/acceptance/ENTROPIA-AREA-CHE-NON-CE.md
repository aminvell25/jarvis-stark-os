# L'aritmetica del bin 13 regge. L'area no.

**Data:** 24 agosto 2026 · **Rollback:** `5e49783`
**Precedente:** `ISTOGRAMMA-E-BIN-VUOTI.md`, `SUPERFICIE-CHIARA.md`

## Il calcolo del proprietario, verificato

Ricalcolato per conto mio dall'istogramma di `shots/scrivania/scrivania.png`:

| passo | mio | del proprietario |
|---|---|---|
| oggi | 2,182 | 2,187 |
| +4,0 % bin 5 `--fill-2` L 89,5 | 2,321 | 2,325 |
| +2,0 % bin 11 `--amber` 185 | 2,420 | 2,425 |
| +1,5 % bin 13 `--icona-viva` L 218,5 | **2,494** | **2,502** |
| +1,2 % bin 7 `--rust` | 2,553 | 2,563 |
| *(bin 3 da solo, +6 % a `--cy-900`)* | 2,337 | 2,345 |

Scarto **costante ~0,006**: io parto dall'istogramma stampato e arrotondato,
lui dai float esatti. Verso, ordine e conclusioni identici.

**Il margine regge anche al caso peggiore**: prendendo l'area dal solo
pavimento invece che dai corpi dei pannelli, il terzo passo dà **2,492** invece
di 2,494. Il margine su 2,40 è **+0,09**, non i centesimi degli ultimi tre
atterraggi. E il bin 3 non arriva, confermato: 2,337 contro una soglia di 2,40.

**Il piano è aritmeticamente giusto.** Quello che non regge è la premessa che
quell'area esista.

## Le aree, misurate nell'app vera

Non stimate. Sondа Playwright su Electron vero, finestra massimizzata, scena
`avvio`, core acceso, `getBoundingClientRect()` su ogni candidato:

| candidato | n | % del fotogramma | |
|---|---|---|---|
| tessere del catalogo, **premute** | 10 | **1,186 %** | sempre vero |
| piastre del plinto | 10 | 3,187 % lorde | **solo 3 in vista** (`FINESTRA` 3) |
| **card di news** | **0** | **0 %** | il Watcher non gira |
| **nodi agenti attivi** | **0** | **0 %** | a riposo `attivo` è falso su tutti e otto |
| testate dei pannelli | 21 | 14,605 % | **= il bin 4**, e §10.5 le fissa a `--fill-1` |
| righe di file e cartelle | 21 | 12,135 % lorde | il conteggio include ciò che è ritagliato |

### ① Il secondo componente proposto non esiste

`forge` aveva proposto la card di news più recente, stimandola **1,63 %** con
una geometria di pannello dichiarata «stima, non misura». Le card sono
**zero**: il Watcher non gira e il pannello mostra il proprio stato vuoto.
L'invariante 23 vieta di inventarne.

### ② Da dove viene l'area conta più di quanta ne sia

Il +0,38 del piano prende l'area dai bin **1 e 2** — pavimento e corpi dei
pannelli, il 71,6 % insieme. È il serbatoio giusto, ed è anche quello che non
si può spendere: riempirlo vuol dire accendere superfici dentro i pannelli, e
§10.1 le concede **solo dove c'è uno stato da dire**. Gli stati che le
giustificherebbero — una selezione, un nodo che lavora, una notizia arrivata —
a scrivania ferma **non stanno accadendo**.

L'unico altro serbatoio grande è il **bin 4**, che misurato è per il 94 % le
**testate dei pannelli**, e §10.5 regola 2 le fissa a `--fill-1`. Presa da lì,
la stessa distribuzione **satura**:

```
tutta a bin 13, presa dal bin 4:  2 % → 2,256   5 % → 2,307   8 % → 2,319 (fermo)
sparsa 5+11+13, presa dal bin 4:  4 % → 2,320   8 % → 2,392   10 % → 2,408
```

Servirebbe il **10 %** invece dell'8,7 %, e sarebbero due terzi delle testate:
un emendamento a §10.5 dentro un turno di implementazione, che le regole di
uscita vietano.

### ③ E la tessera premuta non significa più niente

1,186 % è area vera e sempre presente. Ma con ADR-010 **tutti e dieci** i
moduli sono aperti, quindi tutte e dieci le tessere sono `aria-pressed="true"`:
non esiste una tessera non premuta da cui distinguerle. Accenderle tutte non
direbbe «questi sono aperti» — direbbe soltanto che il catalogo è chiaro.

§11.6 regola 2 chiede che un colore **significhi**. Uno stato che vale per
tutti gli elementi insieme non è un significato: è un fondo.

## Che cosa questo turno NON fa, e perché lo dice invece di farlo

**Non applica nessuna superficie nuova.** Con due componenti e stati
genuinamente veri non c'è l'area, e le tre strade per procurarsela sono tutte
sbarrate da una regola: inventare uno stato (invariante 23), spostare le
testate (§10.5), o riempire il bin 3 col token del nucleo (§25.5).

L'entropia resta **2,19 su 2,40, aperta**, col numero e la ragione. Non è stata
aggiustata.

## Il divario, riformulato

Non è più «mancano dei livelli nella palette» — quella diagnosi è di
`ISTOGRAMMA-E-BIN-VUOTI.md` ed è corretta. È più stretta:

> **Le superfici chiare vogliono stati, e a scrivania ferma gli stati non
> accadono.** Il riferimento è una schermata *in attività*: quattro riproduttori
> che riproducono, una mesh che lavora, un feed che scorre. La nostra è una
> schermata *pronta*, e una schermata pronta è per costruzione più scura.

È la stessa forma della conclusione sul modulo Media: la metrica chiede
contenuto che il sistema, oggi, non ha. Chiuderla non è un lavoro di colore.

---

# La regola per §11.7, e le cinque volte che l'hanno chiesta

`si_e_fermata` era vera perché il nastro non si era mai mosso. È la **quinta**
volta che lo stesso meccanismo passa una verifica:

| | il criterio | perché era vero |
|---|---|---|
| 1 | «il nucleo copre ≥ 5 % del pavimento» | 5 % era il **massimo teorico**: la soglia non poteva essere mancata |
| 2 | «0/0 elementi caldi coperti» | zero su zero non si distingue da un predicato rotto |
| 3 | il banco di §11.4 | dava un verdetto dove il frame **non è misurabile** |
| 4 | il CSP di PixiJS | la galleria non aveva CSP: la prova non attraversava il confine che rompeva |
| 5 | `si_e_fermata` | quattro letture a zero, quindi `fermo == ancoraFermo` |

Il meccanismo è sempre lo stesso: **un criterio vero per assenza del fenomeno**.
Non boccia più niente, e continua a sembrare una verifica — che è peggio del non
averlo, perché occupa il posto di quella vera.

## La formulazione proposta — §11.7, regola 4

> **4. Un criterio su un fenomeno dichiara prima che il fenomeno è avvenuto.**
>
> Prima di giudicare *come* qualcosa è andato, si verifica *che sia successo*.
> Un nastro che non si è mai mosso si è anche fermato; una superficie che non
> esiste non è mai fuori scala; zero elementi su zero sono tutti coperti. In
> tutti e tre i casi il criterio passa **per assenza del fenomeno**, e da quel
> momento non può più bocciare niente.
>
> Gli esiti sono quindi **tre e non due**: `soddisfatto`, `non soddisfatto`,
> **`non misurabile`**. Il terzo non è una via di mezzo ed è il più importante:
> dice che la prova non ha visto ciò di cui doveva parlare, e **non conta come
> verde**. Chi lo incontra guarda il fenomeno, non il verdetto.
>
> In pratica, ogni criterio su un fenomeno porta accanto la propria condizione
> di misurabilità, e la condizione si asserisce **per prima**:
>
> ```
> l'inerzia e' MISURABILE      x != 0 dopo il rilascio
> l'inerzia CONTINUA           subito != dopoUnPo
> l'inerzia DECELERA e si ferma  fermo == ancoraFermo
> ```
>
> Vale in particolare per **soglie di copertura, conteggi su insiemi vuoti, e
> misure di tempo sotto un tetto**: sono i tre posti in cui l'assenza somiglia
> di più al successo.

⚠️ **Non l'ho scritta in `docs/SPEC.md`**, e per due ragioni che vanno dette
invece di essere aggirate: quel file porta modifiche **non ancora committate**
del proprietario, e un emendamento alla specifica dentro un turno di
implementazione è ciò che le regole di uscita del piano vietano. Il testo qui
sopra è pronto da incollare sotto le tre regole esistenti di §11.7.
