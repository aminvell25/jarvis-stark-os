# Il globo prende un corpo — e il modello di geometria impara le superfici

> Il globo era il riquadro più scuro rimasto sulla scrivania. Misurato prima di
> toccarlo: **78,3 % nella banda L 25-60** — cioè quasi tutto corpo nudo di
> pannello — con entropia **1,36** contro i **3,05** del proprio riferimento.

---

## Il riferimento non si può copiare, e va detto

`famiglia-a/10-globo-gps-locator.png` mette al centro una **Terra fotografica**:
continenti, nuvole, un lembo atmosferico. È il contenuto che
`DIVARIO-PREMIUM.md` §6 dichiara irraggiungibile senza un modulo Media, e i
suoi 11,4 punti sopra L 120 vengono da lì.

Ma il confronto diceva anche un'altra cosa, che si può fare: la nostra sfera
non aveva **corpo**. Una sfera fatta di sole linee non è un pianeta visto da
lontano, è un mappamondo di fil di ferro — e il terminatore ambra galleggiava
nel vuoto invece di separare due cose.

---

## Che cosa è stato costruito

### ① Il modello di geometria impara le superfici

`Geometria` portava solo vertici in sequenza, e i tre ruoli — `linea`,
`costruzione`, `punti` — descrivono tutti una sequenza. Una superficie no: ha
bisogno di sapere **quali terne di vertici formano un triangolo**, e
quell'informazione non sta nell'ordine dei punti.

- `Gruppo` prende il quarto ruolo, **`superficie`**;
- `Geometria` prende gli **indici**, un `Uint32Array` — per la stessa ragione
  per cui le posizioni sono un `Float32Array`: un Array normale è una copia in
  più e un cast a ogni upload;
- un gruppo `superficie` **senza** indici solleva: non è una superficie;
- `versoSuperficie()` in `buffer.js`, accanto a `versoLinee` e non dentro —
  una superficie e una linea non si disegnano con la stessa primitiva, e
  mescolarle vorrebbe dire un ramo che sceglie, cioè due funzioni scritte in
  una.

### ② `Sfera`, un componente parametrico come gli altri

§11.10 regola 5 vieta le geometrie standard: niente `SphereGeometry`. La
tassellatura viene da `segmentsFor()`, quindi la densità la decide la curvatura.

⚠️ **La corda è 12 mm e non 1,2**, ed è dichiarata, non allentata. Il valore
predefinito è tarato su una **linea**, dove lo scarto dalla curva si vede come
una spezzata; su una superficie piena l'errore è invisibile ovunque tranne che
sulla silhouette — e la silhouette la disegna già l'equatore della graticola,
che resta a 1,2.

Il conto:

| corda | nLon | nLat | vertici |
|---|---|---|---|
| 1,2 mm | 256 | 128 | **33 153** — il gate boccia sopra 20 000 |
| 12 mm | 105 | 52 | **5 618** |

Alzare il tetto del gate per far passare una sfera sarebbe cambiare la regola
per il caso. Una corda dichiarata **per tipo di primitiva** è un'altra cosa.

### ③ Il colore è un dato, non una scelta grafica

Ogni vertice è colorato da `illuminato()` — lo stesso prodotto scalare col punto
subsolare che già colorava i fusi. **Giorno `--fill-1` (L 66), notte
`--bg-panel` (L 31).**

Non è decorazione che riempie: è l'astronomia già calcolata, resa superficie. E
il terminatore ambra adesso separa due superfici invece di essere una linea
sospesa.

---

## Le misure

**Il pannello del globo:**

| | prima | **dopo** | riferimento |
|---|---|---|---|
| entropia | 1,36 | **1,95** | 3,05 |
| luminanza | 43,8 | **48,3** | 58,9 |
| L 25–60 | 78,3 % | **58,3 %** | 47,7 % |
| L 60–120 | 13,6 % | **34,0 %** | 23,4 % |

La banda dei riempimenti **supera il riferimento** (34,0 contro 23,4), e il
divario sulla banda spenta si chiude da +30,6 a +10,6. Quello che resta è
l'11,4 % sopra L 120, che è la fotografia.

**La scrivania intera:**

| | prima | **dopo** | soglia |
|---|---|---|---|
| entropia | 2,01 | **2,09** | 2,40 |
| dev.std | 29,6 | **29,8** | 32 |
| `L>60` | 19,0 % | **21,9 %** | 25 % |
| caldo | 3,2 % | 3,1 % | 3–6 % |

Audit `globe` **0/0**, suite **564 passed**.

---

## Che cosa NON è stato fatto

- **Nessuna texture**: il corpo è a due colori piatti, e i continenti non ci
  sono. Servono dati di costa, che in questo ambiente non si scaricano.
- **Il lembo atmosferico** del riferimento è un alone, e l'invariante 19 lo
  vieta a prescindere.
- **`versoSuperficie` non ha un test**: è coperta di fatto dal gate del globo,
  che gira nell'audit, ma nessuna prova la chiama da sola.
- **Il ciclo §11.8 punto per punto** sul globo non è stato ripercorso: audit
  pulito e sguardo, non checklist.
- **Il catalogo copre l'angolo in basso a destra del pannello**, come già
  segnalato altrove: non è di questo lavoro.
