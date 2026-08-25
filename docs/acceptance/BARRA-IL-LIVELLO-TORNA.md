# Il `degraded` che non tornava indietro — T4

**Rollback:** `c15925d`
**Criterio:** il livello della barra torna a ciò che dice la sorgente stabile,
da solo, senza che nessuno lo rimetta a posto.

---

## 1. Il difetto

`ui/src/desk/barra.js` scriveva `degraded` su un `agent.advisory` critico e non
lo toglieva più nessuno. L'unico altro scrittore era `state.snapshot`, che
arriva **una volta** per sessione.

La sorgente dell'advisory è `package_temp_c > 75` valutata a 2,5 Hz: **un
campione** inchiodava la sessione. `DEBORDO-R99.md` riporta «barra passata a
DEGRADED (temp 55 °C)» — 55 è **sotto** la soglia, ed è la firma esatta del
latch: la barra diceva degraded mentre la temperatura era rientrata da un
pezzo.

Il nucleo aveva già la correzione, e il suo commento diceva perché:

> un parametro che poi torna indietro da solo mente per tutto il tempo in cui
> sta fuori posto

La barra no. Adesso ha la stessa forma: **offline > accento a tempo > stabile**,
un solo scrittore (`decidi()`), e l'advisory che alza un accento invece di
scrivere uno stato.

## 2. Perché la fixture non poteva vederlo

Due ragioni, entrambe misurate **prima** di scrivere il codice:

- la registrazione `4d5edf35cfdb64af` ha `avvisiCritici: 0` — riproducendola il
  ramo non si percorre mai;
- il Δ del latch è ~560 px su 1 294 848, lo **0,043 %**, sotto la precisione con
  cui `densita.mjs` stampa. Ambra e ciano stanno entrambi sopra L 60, quindi
  `L>60` non si muove affatto.

**Previsione fatta prima e verificata dopo:** dopo T4 il PNG della fixture deve
restare **byte-identico**. Lo è:

```
scrivania.png e g1.png: IDENTICI, 0 pixel di differenza
```

Un turno il cui Δ è zero, e si sa perché, è pulito. Impacchettato con la
fixture avrebbe lasciato un'ambiguità dello 0,04 % che nessuno poteva più
sciogliere — ed è la ragione per cui il piano lo teneva in un turno suo.

## 3. Come si misura, allora

`scripts/prova-barra.mjs`, nella **galleria**: il montaggio `chrome` ha già un
bus finto con `manda()`, e §11.7 assegna alla galleria la verifica dei
componenti. Nella scrivania viva il criterio dipenderebbe dal meteo dentro il
case, e un criterio così non è un criterio.

```
  ok  nessun errore di console                 nessuno
  ok  a riposo la barra dice nominal           nominal
  ok  l'accento e' MISURABILE                  nominal -> degraded
  ok  la scritta segue il dato                 degraded
  ok  l'accento SCADE dopo 2600 ms             degraded -> nominal
  ok  un advisory non critico non tocca niente nominal
  ok  state.snapshot puo' dire degraded        degraded
  ok  e l'accento non lo cancella scadendo     degraded

il livello torna indietro da solo — 8 condizioni su 8
```

### La prova che la prova boccia

Rimesso il latch e rilanciata, senza toccare altro:

```
  NO  l'accento SCADE dopo 2600 ms             degraded -> degraded — il latch e' ancora li'
  NO  un advisory non critico non tocca niente degraded
IL LIVELLO NON TORNA INDIETRO — 2 condizioni su 8
EXIT=1
```

Senza questo passaggio la prova sarebbe stata otto verdi di cui nessuno sa se
significano qualcosa — che è il difetto per cui `prova-catalogo.mjs` è stato
riscritto ieri.

### `MISURABILE` prima di tutto

Se l'advisory non accendesse niente, «l'accento scade» sarebbe vero **per
assenza del fenomeno** (§11.7 regola 4). È in un test suo, come l'inerzia del
catalogo, perché se cade quel criterio gli altri sono rumore.

### E la metà opposta

Un accento a tempo che scadendo riscrivesse `nominal` cancellerebbe ciò che
`state.snapshot` ha detto: lo stesso errore di categoria al contrario, facile
da introdurre proprio correggendo il primo. Il criterio 8 lo copre.

## 4. `AVVISO_MS` ha un proprietario solo

Era `const AVVISO_MS = 2600` dentro `sfondo.js`. Ricopiarlo in `barra.js`
avrebbe dato **due opinioni su quanto dura un avviso** — la regola che
`barra.js` stesso scrive sopra `SOGLIA_TEMP`.

Non lo esporta `sfondo.js` perché `barra.js` finirebbe per importarlo intero —
anime.js, `rings.js` — anche nella galleria, che monta la barra da sola in
`gallery/mounts/chrome.js`. Una costante non deve trascinare un motore di
animazione. Quindi `ui/src/desk/avviso.js`, sedici righe, e lo importano
entrambi.

## 5. Verifica

| | |
|---|---|
| `npm run verifica:barra` | **8/8**, EXIT=0 |
| la stessa prova col latch rimesso | 2 rossi, EXIT=1 |
| `uv run pytest -q` | **584 passed** |
| `npm run scrivania:fixture` | PNG byte-identico a prima di T4 |
| `npm run verifica:marchio` | §25.13.5 soddisfatto, contrasto 3,04:1 in tutti gli stati |

La guardia del marchio è caduta durante il turno — avevo toccato `sfondo.js` —
e ha detto quale comando lanciare. Ha fatto esattamente il suo mestiere.

## 6. Dichiarato aperto

- **L'impronta copre tre file**: `barra.js`, `avviso.js`, `chrome.js`. Se a
  rompere il ritorno fosse un quarto, la guardia non lo vedrebbe. Si allarga
  aggiungendolo a `FONTI`, non sperando che basti.
- **La prova gira nella galleria, non nella scrivania viva.** Prova che la
  macchina a stati torna indietro; non prova che il core mandi advisory con i
  livelli che ci aspettiamo. Quella è un'altra domanda e ha un'altra sede.
- **`fissa()` adesso ferma anche il timer dell'avviso.** Serve solo al modo di
  misura: un timer in sospeso scadrebbe fra i due scatti. Con la registrazione
  di oggi non si innescherebbe mai — ma una registrazione futura sì, e sarebbe
  una deriva scoperta due mesi dopo dentro una baseline.
