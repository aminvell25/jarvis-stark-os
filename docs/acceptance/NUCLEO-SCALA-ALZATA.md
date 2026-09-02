> ## 🔴 STORICO — il nucleo che questo documento misura NON ESISTE PIÙ
>
> Il 2 settembre 2026 il nucleo è stato rifatto sul riferimento «Aurora»: otto
> stati, tre gusci deformati da rumore FBM, catena di post-processing. Tutto
> quello che sta qui sotto — geometria, strati, criteri, numeri — misura un
> oggetto **cancellato**. Il codice sta in git e si recupera con un checkout.
>
> **Lo stato corrente è in `docs/acceptance/NUCLEO-AURORA.md`.**
>
> ⚠️ Questo documento **non si cancella** e non è un rifiuto: è il registro di
> ciò che è stato misurato e perché, ed è citato da 3 altri file. La
> «definizione di fatto» di CLAUDE.md poggia su questi referti. Serve però il
> cartello: fra il 24 e il 30 agosto un documento di stato ha detto il falso su
> cinque voci su cinque, **ed è stato creduto** — e la cura non è cancellare, è
> dire da quando una cosa non vale più.

# Il nucleo con §25.5 alzata, e il campo interno pieno

> Implementazione del cancello `docs/acceptance/CANCELLO-25.5.md`. Il turno di
> governance è arrivato prima e da solo, come le regole di uscita del piano
> pretendono; questo applica ciò che quello ha deciso, e misura i tre costi che
> aveva previsto.

---

## Applicato

| | prima | dopo |
|---|---|---|
| tratto del nucleo a riposo | `--cy-900` (L 48,5) | **`--cy-700`** (L 100) |
| anello attivo | `--cy-700` | **`--cy-500`** (L 181) |
| riempimento delle fasce | `--bg-panel` (L 31) | **`--cy-900`** (L 48,5) |
| campo interno | *vuoto* | **`--bg-panel`** (L 30,7) |

Il campo interno è un cerchio il cui raggio **non è un numero**: è il bordo
interno dell'anello più interno, derivato da `ANELLI`. Scritto a mano
smetterebbe di combaciare al primo cambio di composizione, lasciando una
fessura o una sovrapposizione senza che nulla lo segnali.

## Il profilo, contro il riferimento

| | riferimento | prima | **dopo** |
|---|---|---|---|
| campo interno | 43,3 | 22,6 (vuoto) | **~31** |
| fasce, media | 43–125 | 25,6–35,5 | **36,2–61,0** |
| picchi a riposo | (bloom) | 47,7–48,5 | **97,0–99,6** |
| anello attivo, picco | — | 96,2 | **176,2** |

## E la densità si muove

Il cancello prevedeva che il nucleo, passando da L 48 a L 100, cominciasse a
contare sopra la soglia `L>60` di §11.8. **È successo, ed è misurato:**

| | prima | dopo |
|---|---|---|
| entropia | 1,57 | **1,69** |
| `L>60` | 9,2 % | **10,0 %** |
| luminanza media | 34,5 | **35,55** |
| banda 25–120 | 61,8 % | **64,5 %** |

+0,12 di entropia da un solo cambiamento. Per contesto,
`docs/PIANO-CORE-E-DENSITA.md` conta **+0,27 in cinque giorni**. La tensione 1
di Parte 3 del piano — *«il nucleo resta un costo senza resa metrica»* — si è
sciolta.

---

## ⚠️ Il marchio: rotto, e rimesso in piedi dal fondo

Il cancello lo aveva previsto per primo, e aveva ragione.

| passo | composito sotto il nome | contrasto | §25.13.5 |
|---|---|---|---|
| scala alzata, campo a `--cy-900` | L 65,7 | **1,77:1** | ❌ |
| scudo rinforzato a tre veli | L 46,8 | **2,40:1** | ❌ |
| campo a `--bg-panel` | L 31,5 | **3,01:1** | ✅ |

**Non si poteva rispondere alzando il marchio**, ed è il punto: `--cy-700` è il
tetto di §25.13.2 regola 4, e il gradino sopra — `--cy-500` — dà **7,04:1**
contro quel fondo, che sfonda il **tetto** di 5,0:1. Fra i due non c'è nessun
token. La forbice di §25.13.5 si raggiunge **dal fondo, non dalla scritta**.

Da qui le due mosse, in ordine:

1. **Lo scudo è tarato sul fondo, e il fondo era cambiato.** §25.13.4 lo
   dichiara ammesso proprio per questo — è il colore del *pavimento*, toglie
   contrasto a ciò che passa sotto invece di aggiungerne alla scritta. Tre veli
   invece di due, e più larghi. Ha portato 1,77 → 2,40, e non bastava.
2. **Il campo è sceso di un gradino**, da `--cy-900` a `--bg-panel`. §25.5
   ammetterebbe il primo; il marchio no.

Il campo resta così **più scuro delle fasce**, dove nel riferimento campo
(43,3) e fasce scure (45,2) sono quasi pari. Non è un ripiego: un centro più
scuro sotto un nome è esattamente ciò che un nome chiede.

### ⚠️ E passa con margine ZERO

**3,01:1 su un minimo di 3,00.** Misurato tre volte, sempre 3,01 — è
deterministico, non fortunato. Ma un centesimo non è margine: **qualunque cosa
schiarisca il composito sotto il nome rompe §25.13.5**, e non c'è un altro
token più scuro con cui rispondere. `--bg-deep` vale L 30,2 contro i 30,7 di
`--bg-panel`: mezzo punto, che non sposta il rapporto.

Le uscite, quando servirà, sono tutte in §25.13 e nessuna in §25.5:

- **alzare il tetto del marchio** oltre `--cy-700` (regola 4), e allora anche
  il tetto di 5,0:1 di §25.13.5 va riletto, perché `--cy-500` lo sfonda;
- **alzare il pavimento della forbice**, cioè accettare che un marchio si legga
  sotto 3:1 — che è quello che AA vieta per un corpo grande;
- **togliere il campo sotto il nome**, cioè rinunciare a metà di ciò che questo
  turno ha aggiunto.

Nessuna delle tre è stata fatta. **La prossima persona che tocca il fondo del
nucleo deve sapere che sta lavorando su un centesimo.**

---

## Verificato

`npm run verifica:scrivania`, blocco `nucleo`, in finestra vera:

```
aRiposo []                    nessun anello in moto senza causa
t1 ["t1"]  ascolto ["ascolto"]  t2 ["t2"]  subagent ["subagent"]
t0 [] · impulso 144 fotogrammi · dopo l'impulso 0
opacita' a fase 3 [0.06, 0.06, 0.06, 1, 1] · a fase 9 tutti a 1
fotogrammi in un secondo di riposo: 0
```

**Un solo anello acceso per volta** — la condizione a cui §25.5 ammette
`--cy-500` — non è una promessa: è quella riga, e la verifica gira in finestra
vera. Invariante 25 regge dopo il passaggio ad anime.js: zero fotogrammi a
riposo.

`tests/test_nucleo.py` conta adesso la scala nuova: tratto a `--cy-700`,
riempimenti fra i soli token sotto L 48, acceso a `--cy-500`, `--cy-100` ancora
vietato. Suite: **561 passed**. Budget di frame: mediana **16,7 ms**, sul
vsync, invariato.

Guardati, `npm run nucleo`: a riposo il disco ha un corpo e le tacche si
leggono; con `t1` l'anello esterno **stacca** invece di accennare.

---

## Che cosa NON è stato verificato

- **Il tetto di 5,0:1 di §25.13.5 non è mai stato esercitato**: il marchio sta
  al pavimento della forbice, non al soffitto.
- **`--amber` su `warn` e `--rust` su `critical`** restano regole CSS che
  nessuna esecuzione ha acceso.
- **La densità è misurata sulla scrivania intera**, non sul solo nucleo:
  +0,12 di entropia è attribuito a questo cambiamento perché è l'unico
  intervenuto fra le due misure, non perché sia stato isolato.
- **Il campo interno non ha un ciclo §11.8 punto per punto**: è stato guardato,
  non passato in rassegna riga per riga.
- I due difetti **preesistenti** di `verifica:scrivania` — dock a 9, cornice col
  fuoco identica a quella senza — restano aperti.
