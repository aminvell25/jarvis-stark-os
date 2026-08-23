# Fase 2 — i riempimenti di stato, e dove finisce la leva

> Leva ① del piano generale: *«i riempimenti di stato dentro i pannelli — fino a
> +16,5 punti»*. Fatta sui pannelli della scena, misurata, e **conclusa prima
> del +16,5**: questo documento dice perché.

---

## Che cosa è stato fatto

| pannello | prima | dopo | resa |
|---|---|---|---|
| `telemetry` | tre righe di testo | la quota di CPU è una **barra** larga quanto il dato, `--fill-2`, più zebra | +0,03 ent · +0,4 L>60 |
| `agents` | nodi `--bg-raised` con filo su quattro lati | **superfici**: `--fill-1` collegato, `--fill-2` attivo, niente per lo scollegato | +0,05 ent · **+2,1** L>60 |
| `news` | carte `--bg-raised` = il fondo del pannello | carte `--fill-1` | **zero** — vedi sotto |
| `cartella` | pannello freddo con accento manila | **superficie manila**, polarità rovesciata | caldo 0,2 → 3,2 % |

E un difetto di sicurezza trovato strada facendo: `telemetry` scriveva i nomi
dei processi con **`innerHTML`**. Un nome di processo arriva dal sistema
operativo ed è dato non fidato (invariante 5); `panels/cartella.js` evitava già
lo stesso difetto sui nomi dei file, con la motivazione scritta accanto.

---

## ⚠️ Le carte news pagano zero, e il perché vale più del cambiamento

Misurato isolando i due cambiamenti — uno scatto con le carte a `--fill-1`, uno
con le carte rimesse a `--bg-raised`: **numeri identici a tre decimali**.

Il fondo delle carte non porta niente perché **non ci sono carte**. Il `Watcher`
è costruito e non gira, `news.card` non esce mai, e il pannello mostra il
proprio stato vuoto. Il cambiamento resta perché è giusto, ma oggi è
**latente**: pagherà il giorno che le notizie arrivano.

Vale come metodo: un cambiamento che *dovrebbe* pagare e non paga va isolato,
non sommato al vicino che paga davvero.

---

## Dove è finita la leva, misurato

Le quattro bande di luminanza, che sono la scomposizione vera del divario:

| banda | noi, stamattina | **noi, ora** | riferimento | scarto |
|---|---|---|---|---|
| L < 25 — pavimento | 37,8 % | **27,9 %** | 21,9 % | +6,0 |
| L 25–60 — superficie spenta | 53,0 % | **53,1 %** | 36,0 % | **+17,1** |
| L 60–120 — i riempimenti | 8,2 % | **15,0 %** | 24,7 % | −9,7 |
| L > 120 — media e testo chiaro | 1,0 % | **4,0 %** | 17,4 % | −13,4 |

**Il pavimento nudo si è quasi chiuso** — da +15,9 a +6,0 — e la banda dei
riempimenti è quasi raddoppiata. Ma **la banda 25–60 non si è mossa di un
decimo**, ed è adesso il divario più grande.

### Perché la leva ① non arriva ai +16,5 promessi

La banda 25–60 è il **corpo nudo dei pannelli**: `--bg-panel` (31),
`--bg-raised` (37), `--cy-900` (48). E quei valori sono **giusti**: §10.5 li ha
misurati sul riferimento stesso — `#1e2631` letto identico a quattro quote sul
calendario.

Il riferimento tiene quella banda al 36 % non perché i suoi corpi siano più
chiari, ma perché **ne resta scoperto di meno**: i suoi pannelli sono più
pieni di roba. Non è un problema di riempimenti di stato, è un problema di
**quantità di dato**.

Provare a chiuderla alzando la zebra da `--bg-panel` a `--fill-1` sarebbe la
strada sbagliata: `panels/tabella.js` la fissa a *«sei punti di L, non un
colore — si vede che sono righe, non si vede la riga»*, e a +29 punti si
vedrebbe la riga. Sarebbe decorazione che riempie, che è esattamente ciò che
§11.6 regola 2 vieta.

### E i 13,4 punti sopra L 120 non arrivano da nessun riempimento

Sono contenuto fotografico. `DIVARIO-PREMIUM.md` §6 lo dichiara già: senza un
modulo Media quei punti non si recuperano, e va detto invece di sperare che
arrivino dagli altri.

---

## Il totale della giornata

| | 22 ago | **23 ago, fine** | soglia | riferimento |
|---|---|---|---|---|
| entropia | 1,58 | **2,01** | 2,40 | 3,32 |
| dev.std | 20,1 | **29,6** | 32 | 55,7 |
| `L>60` | 9,2 % | **19,0 %** | 25 % | 42,1 % |
| caldo | 0,18 % | **3,2 %** ✅ | 3–6 % | 5,70 % |
| fondo nudo | 37,8 % | **27,9 %** | — | 21,9 % |

**+0,43 di entropia in un giorno**, contro i +0,27 dei cinque giorni
precedenti. Il caldo è dentro la forbice. Restano tre criteri sotto soglia:
entropia, dev.std e riempito — e per tutti e tre la distanza residua **non sta
nei riempimenti**.

---

## Che cosa NON è stato fatto

- **`source.js` e `files.js`** non sono stati toccati: `files` ha già la zebra e
  nessuno dei due è nella scena `avvio`, quindi qualunque cambiamento sarebbe
  latente come quello delle news — e senza il vantaggio di essere già giusto.
- **`rings.js`**, ultima voce della leva ①, non è nella scena.
- **Il globo** è il più grande riquadro scuro rimasto (472×337, il 12,3 % dello
  schermo) e resta un reticolo su fondo. Riempirlo vuol dire dati di costa, che
  in questo ambiente non si possono scaricare.
- **Nessuna misura sotto carico**: tutti i numeri sono a riposo.
