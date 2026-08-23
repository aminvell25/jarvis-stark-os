# Turno 4 — §25.13.5 in tutti gli stati, e la premessa che non reggeva

> `docs/PIANO-CORE-E-DENSITA.md` §8 dichiarava §25.13.5 **rotta nello stato T0**,
> per simulazione, e ne faceva il turno 4 bloccante. Misurata: **non è rotta in
> nessuno dei nove stati**, e il motivo non è fortuna — è geometria, e adesso è
> meccanizzata.

---

## Il risultato

Nove stati, stesso protocollo §5, pannelli aperti come §25.13.5 pretende:

| stato | contrasto | luminanza media | composito sotto il nome |
|---|---|---|---|
| riposo | **3,04:1** ✅ | 35,6 | `rgb(19, 33, 42)` L 30,7 |
| **t0** | **3,04:1** ✅ | 38,4 | `rgb(19, 33, 42)` L 30,7 |
| t1 | 3,04:1 ✅ | 35,6 | idem |
| ascolto | 3,04:1 ✅ | 35,6 | idem |
| t2 | 3,04:1 ✅ | 35,6 | idem |
| subagent | 3,04:1 ✅ | 35,6 | idem |
| offline | 3,04:1 ✅ | 35,6 | idem |
| warn | 3,04:1 ✅ | 35,6 | idem |
| onda *(inviluppo)* | 3,04:1 ✅ | 38,4 | idem |

**Identici a tre decimali, e il composito è `--bg-panel` esatto in tutti e
nove.** T0 dà 3,04, non 2,94.

Cambia solo la **luminanza media del ritaglio** — 35,6 → 38,4 in T0 e nell'onda
— ed è esattamente la prova del perché il criterio non si muove: il ritaglio
aggiunge 8 px di margine per lato e i suoi angoli pescano la ghiera accesa,
ma il contrasto si calcola **sui soli pixel di tratto**, e lì non arriva.

---

## ⚠️ Tre premesse di §8 che non reggevano

§8 è calibrato su `b2f7360`. Dopo di lui sono arrivati `4611cb6` e `fa31575`.

| §8 diceva | misurato |
|---|---|
| §25.13.5 chiusa a **3,01:1** | **3,04:1** |
| il marchio è largo **183 px**, ±91,5 | riquadro **137×20**, corpo 16,8 → ±68,5 |
| le lettere estreme stanno **sopra la ghiera** | **no**, 9,3 px di franco |

La causa è `4611cb6`: la larghezza del nome era una **citazione fissa** — 0,561
del raggio, la quota del riferimento — ed è diventata **derivata**: si misura la
diagonale del riquadro reso e la si tiene dentro `rCampo × 0,94`.

### La misura che chiude la questione

Distanza dal centro del disco di **ogni pixel di tratto** del marchio, cioè
esattamente i pixel su cui `--marchio` calcola `sotto`:

```
pixel di tratto                          451
raggio MASSIMO di un pixel di tratto    64,1 px
la ghiera (ANELLI[4]) comincia a        73,4 px
raggio massimo dell'angolo del RITAGLIO 79,1 px
```

Il `massimo del ritaglio 96,1 SENZA marchio` che §8 cita come prova **non è
sotto le lettere**: è nell'angolo del ritaglio, oltre 73,4 px. La simulazione
era giusta nel metodo e applicata a una geometria che non c'è più.

---

## Il deliverable vero: la separazione, meccanizzata

Il contrasto è un numero che può derivare; **la separazione è una proprietà che
vale in tutti gli stati insieme**. È anche la cosa che si è rotta due volte in
un giorno — a `b2f7360` e a `4611cb6` — sempre perché una geometria si muoveva
sotto un numero scritto altrove.

`window.__insegna.geometria()`, letta dal DOM vivo e verificata in
`npm run verifica:scrivania`:

```
raggioDisco              162,9 px
raggioMinimoFascia        73,4 px    min(outerR - thickness) x (2R / lato)
raggioMassimoInchiostro   69,2 px    semi-diagonale del riquadro reso
franco                     4,2 px    ASSERITO > 0
```

⚠️ Il raggio dell'inchiostro è la **semi-diagonale del riquadro**, cioè un
limite **superiore**: gli angoli del riquadro sono vuoti, e sui pixel veri il
franco è 9,3 px invece di 4,2. Un limite conservativo che sbaglia dalla parte
della prudenza è ciò che serve a una guardia.

**Perché regge in ogni stato.** Tutte le regole per-stato dell'insegna vivono su
`[data-anello]`: lo strato acceso, l'opacità di fase, la rotazione — gruppi ad
r ≥ 73,4 px — e `[data-livello="warn"|"critical"]` tocca **solo**
`[data-anello="0"]`, a r 144–160 px. Sotto 73,4 px c'è solo il cerchio del
campo, che nessuna regola di stato tocca.

---

## L'impulso non si insegue: si blocca

`impulso()` è `opacity: [0, 1, 0]` in 420 ms con `out(4)`: il picco sta nei
primi fotogrammi e `capturePage()` costa 50–150 ms. Rincorrerlo con un'attesa dà
**un fotogramma a caso**, e un criterio misurato su un fotogramma a caso non è
un criterio, è un sondaggio.

`window.__insegna.fissa(stato)` porta gli strati accesi al proprio estremo e
ferma tutto — rampe, rotazioni, animazioni in corso. Non falsifica niente:
**1 è il picco di `[0, 1, 0]`**, quindi si misura il **caso peggiore**.

⚠️ `fissa` pinza il **visivo**, non il contratto causale: `causeOra` e `inMoto`
restano di `forza`, perché *«se gira sta lavorando»* si verifica guardando il
moto, non un fotogramma. Due leve, due domande.

---

## L'uscita che §25.13 non poteva conoscere

`NUCLEO-SCALA-ALZATA.md` elenca tre uscite se il criterio cade. **Ce n'è una
quarta, nata dopo quel documento**: il nome ha una larghezza **derivata**, e
stringere il coefficiente `0,94` costa qualche pixel di scritta e nient'altro —
non tocca §25.13.2 regola 4, non tocca la forbice, non tocca il campo. È la più
economica delle quattro.

### E la terza uscita costa più di quanto quel documento dicesse

`--bg-void` sotto il nome: **misurato 3,43:1** (l'aritmetica di §8 diceva ≈3,4;
combacia). Ma da `2530889` il campo **copre tutto il disco**, non solo il mozzo:
portarlo a `--bg-void` non è «rinunciare a metà del campo», è **ridare al disco
i buchi** che quel commit ha chiuso.

**Quanto vale il campo**, misurato come §8 chiede — due render nella stessa
sessione, sugli **83 457 px del disco** e non sull'intera scrivania:

| | lum | dev.std | entropia | L>60 |
|---|---|---|---|---|
| col campo | 67,7 | 30,4 | **2,17** | 52,9 % |
| senza campo | 64,5 | 34,3 | **2,09** | 52,6 % |

**+0,08 di entropia sul disco**, +3,2 di luminanza media, e `L>60` invariato —
com'era prevedibile: `--bg-panel` vale L 31, sotto la soglia.

⚠️ **E una cosa sul metodo.** Sull'intera scrivania i due render danno 1,89 e
1,91: il campo sembrerebbe *togliere* entropia. Non è vero — sono due scatti a
dieci secondi di distanza con i pannelli vivi, e il rumore dei pannelli (±0,02)
è più grande dell'effetto. Il protocollo §5 garantisce due scatti a 250 ms per
la stessa misura; **non garantisce nulla fra due misure a dieci secondi**. Per
un effetto piccolo bisogna isolare la regione, ed è quello che è stato fatto.

---

## Verificato

```
npm run marchio:stati                    nove stati + la variante
node scripts/densita.mjs --marchio <ognuna>   tutte 3,04:1
npm run verifica:scrivania               franco 4,2 px > 0, asserito
node scripts/audit.mjs rings             0 / 0
uv run pytest -q                         561
```

**Densità invariata**: entropia 1,76, `L>60` 12,5 %, dev.std 22,6 — questo turno
è conformità e presidio, e non cambia un pixel della scrivania. È l'effetto
atteso che §4 gli assegna.

---

## Che cosa NON è stato verificato

- **`critical`** non è fra i nove stati: `fissa` lo accetta, ma `--marchio-stati`
  non lo cattura. Cambia lo stesso anello di `warn`, a r 144–160 px, quindi la
  separazione lo copre — ma non è stato fotografato.
- **Il franco è un limite superiore**, non l'inchiostro vero: la guardia in
  `verifica:scrivania` misura la semi-diagonale del riquadro. Il franco reale
  (9,3 px) è stato misurato **una volta**, a mano, sui pixel; non è meccanizzato.
  Sta al turno 5.
- **`densita.mjs --marchio` non è ancora in `package.json`** e la suite non lo
  tocca: è il turno 5 per intero.
- **I quattro centesimi di margine restano.** Questo turno dimostra che non
  derivano fra gli stati; non li allarga. La decisione di §25.13 resta aperta,
  con una quarta uscita in più e la terza rivalutata.
