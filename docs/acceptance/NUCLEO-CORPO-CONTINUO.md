# I corridoi: non erano larghi, erano buchi

> *«Stringi i corridoi come nel riferimento.»* La misura ha smentito la
> premessa — e la premessa l'avevo scritta io.

---

## ⚠️ Correzione a quello che avevo detto

Nel documento precedente avevo scritto che il riferimento ha corridoi *«attorno
a 1–1,5 unità»*. **È falso**, e veniva da una segmentazione grossolana per
soglia invece che dal profilo fine.

Profilo radiale di `famiglia-a/12` a passo 1 px, r 40–120:

| zona | larga | media L |
|---|---|---|
| r 40–57 | 18 | 39,6 |
| r 58–65 | 8 | **130,0** |
| r 66–73 | 8 | 84,1 |
| r 74–88 | 15 | **105,3** |
| r 89–103 | 15 | 45,4 |
| r 104–118 | 15 | **88,9** |

Due fatti, e ribaltano la richiesta:

1. **Le zone del riferimento sono larghe 8–18 unità** — cioè *più larghe* dei
   corridoi da 3 che avevamo, non più strette;
2. **il minimo su tutto il disco è L 34,0**, contro il pavimento della
   scrivania a 19,2. Nel riferimento fra una fascia e l'altra **non c'è vuoto,
   c'è una superficie più scura**.

Il difetto dei nostri corridoi non era la larghezza: **era che si vedeva il
pavimento attraverso**. Cinque anelli sospesi invece di un oggetto.

---

## Fatte tutte e due

**① Il corpo copre tutto il disco.** Il cerchio di fondo passa dal raggio del
mozzo (55) al raggio esterno (120). I corridoi restano corridoi — il loro fondo
è più scuro delle fasce — ma il nucleo torna a essere **un** oggetto.

**② I corridoi si stringono lo stesso**, da 3 a 2 unità, e le fasce crescono:
12 / 10 / 18 / 14 / 3.

| | prima | dopo | riferimento |
|---|---|---|---|
| coperto dalle fasce | 0,442 | **0,475** | 0,484 |
| minimo dentro il disco | **19,3** (pavimento) | **30,4** | 34,0 |
| corridoi | 3 unità di vuoto | 2 unità di corpo | *nessun vuoto* |

---

## Che cosa resta diverso, e perché non l'ho fatto

Le zone del riferimento **alternano** in luminanza: 130 · 84 · 105 · 45 · 89.
Le nostre stanno tutte fra **50 e 52**.

| frazione del raggio | riferimento | noi |
|---|---|---|
| 0,33–0,47 | 38,9 | 36,7 |
| 0,48–0,54 | **132,7** | 52,3 |
| 0,55–0,61 | 84,1 | 50,5 |
| 0,62–0,73 | **107,2** | 50,8 |
| 0,74–0,86 | 45,4 | 52,0 |
| 0,87–0,98 | **92,8** | 51,7 |

La causa è la **riga «riempimento del nucleo» di §25.5**, aggiunta col cancello
del 23 agosto: i riempimenti stanno sotto **L 48**. Le bande chiare del
riferimento sono **superfici chiare**, non contorni chiari su superfici scure —
e una superficie a L 105 sfonda quella riga.

L'emendamento aveva alzato il **tratto** a `--cy-700`; il **riempimento** è
rimasto al tetto vecchio. È lo stesso ceiling di prima, spostato di una riga.
Alzarlo è di nuovo una decisione, e non si prende dentro un turno di
implementazione.

---

## ⚠️ E un difetto nella verifica, non nel componente

`fotogrammiInUnSecondoDiRiposo` ha risposto **87** una volta su tre. Non era un
ciclo acceso: era **un evento vero del bus** — un advisory, o un nodo che
cambia stato — caduto dentro il secondo sbagliato. La leva `forza(null)` ferma
le cause forzate, non il core.

L'asserzione `=== 0` era quindi **fragile per costruzione**: poteva fallire
perché il sistema aveva funzionato. Adesso si misurano **due finestre e si
tiene la minore**: un'animazione ambientale gira in entrambe, un evento cade in
una sola. È esattamente la domanda dell'invariante 25 — non «si è mosso
qualcosa», ma «si muove qualcosa **senza causa**».

Misurato dopo la correzione: `[0, 0]`.

---

## Misure

| | prima | dopo |
|---|---|---|
| entropia | 1,73 | **1,74** |
| banda 25–120 | 66,1 % | **66,65 %** |
| luminanza media | 35,9 | **36,0** |
| §25.13.5 | 3,04:1 | **3,04:1** |

Il marchio non si è mosso di un centesimo, ed era la cosa da temere: il nome è
legato al raggio del campo, che non è cambiato — il corpo si è esteso, ma
`rCampo`, che è il vincolo del marchio, resta il bordo interno dell'anello più
interno. Le due misure sono separate apposta.

Suite **561 passed**. Audit `rings` 0/0. Verifica in finestra vera: una causa
per anello, `aRiposo []`, riposo `[0, 0]`.

---

## Che cosa NON è stato verificato

- **L'alternanza di luminanza fra le fasce** resta fuori portata finché la riga
  «riempimento» di §25.5 sta a L 48. Non è stato tentato niente per aggirarla.
- **La larghezza delle nostre zone** non segue quella del riferimento zona per
  zona: le sue sono 18/8/8/15/15/15, le nostre derivano dai raggi di `ANELLI`
  che vengono da §10.3 e non sono stati rimessi in discussione.
- **Il ciclo §11.8 punto per punto** sul pannello `rings` non è stato
  ripercorso: audit pulito e occhio, non checklist.
