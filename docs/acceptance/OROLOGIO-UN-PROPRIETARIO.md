# I cinque orologi vivi — e il core ne trasmetteva uno da sempre

**Rollback:** `a44d85a`
**Criterio:** nessun pannello chiede l'ora alla macchina che disegna.
**Esito: SODDISFATTO. Nove punti chiusi, un proprietario, due guardie.**

---

## 1. Il dato c'era già

`telemetry` porta `ts` e arriva **2,5 volte al secondo**; `agent.mesh` ne porta
un altro. **Nessuno li leggeva.** Nove punti del renderer chiamavano
`new Date()` o `Date.now()` per sapere l'ora — cioè chiedevano all'orologio
della macchina che **disegna** mentre il dato accanto veniva da quella che
**misura**.

È lo stesso difetto già corretto per il globo in `cb4a52b`: «le zone venivano
dal core e l'istante dal renderer, due orologi per un'immagine sola». Corretto
lì, lasciato in piedi in cinque pannelli — e **dichiarato aperto in cinque
documenti di accettazione di fila**:

> Cinque derive latenti: `news.js`, `meteo.js`, `console.js`, `lettura.js`,
> `calendario.js`. Zero pixel oggi perché sono fuori scena — vanno elencati per
> nome, non riscoperti il giorno in cui qualcuno li compone.

Elencarli non li ha fermati. Sarebbe bastata una scena futura che aprisse uno
di quei pannelli e la fixture di §11.9 avrebbe smesso di essere riproducibile,
**senza che nessun test se ne accorgesse**.

## 2. Il proprietario

`ui/src/desk/orologio.js`, alimentato da `app.js` con `bus.suOgni((m) =>
alimenta(m?.ts))`:

| | |
|---|---|
| `adesso()` | l'istante in ms — del core se lo si sa |
| `data()` · `ora()` | lo stesso come `Date` e come `HH:MM:SS` |
| `fonte()` | «core» o «locale» |

Tre scelte che non sono dettagli:

- **Il ripiego è dichiarato, non silenzioso.** Finché il primo campione non
  arriva, `adesso()` torna all'orologio locale e `fonte()` lo dice. §11.7 regola
  5 — la provenienza di una misura fa parte della misura — vale anche per un'ora.
- **Non torna mai indietro.** Un `ts` più vecchio si scarta: i messaggi possono
  arrivare fuori ordine, e un orologio che indietreggia farebbe apparire
  «3 min fa» dopo «adesso».
- **Non serve nessuna leva `fissa()`.** Sotto la fixture il `ts` è quello della
  registrazione, quindi ogni orologio che legge di qui è fermo **perché la sua
  sorgente è ferma**. I due intervalli che restano — l'uptime di `lettura` e la
  freschezza del meteo — continuano a scattare e il valore non si muove.

## 3. I nove punti

| file | era | perché era sbagliato |
|---|---|---|
| `news.js` | `new Date()` | l'ora dell'ultima card, su un dato del core |
| `meteo.js` | `Date.now()/1000 − secondi` | `secondi` è un istante del core: due orologi per fare una durata |
| `meteo.js` | `new Date().getDay()` | quale colonna è oggi |
| `console.js` | `new Date()` | il ripiego di una riga che viene dal core |
| `lettura.js` | `Date.now()` ×2 | l'uptime avanzava con un orologio diverso da quello che ha prodotto `uptime_s` |
| `lettura.js` | `new Date()` | l'ora nel piede |
| `calendario.js` | `new Date()` ×3 | un calendario è fatto di date, e la data è un dato |
| `globe.js` | `new Date()` | il **ripiego** che `cb4a52b` aveva lasciato |
| `telemetry.js` | `Date.now()` | idem |

## 4. Che cosa NON è stato toccato, e perché

`Date.now()` resta in tre posti, elencati in `DUREVOLI`:

```
ui/src/desk/barra.js      l'uptime che avanza fra due snapshot
ui/src/desk/layout.js     il freno delle scritture
ui/src/desk/orologio.js   il ripiego, dichiarato
```

Misurano **quanto tempo passa**, non che ora è. L'orologio del core arriva a
2,5 Hz, cioè può essere vecchio di 400 ms: per una durata non va bene. Non sono
deroghe, sono l'altro mestiere — e un test verifica che i tre usino ancora
`Date.now()`, perché un'eccezione che sopravvive alla ragione che la
giustificava diventa un buco.

## 5. Le due guardie

`TestLOrologio` — il comportamento, eseguendo il modulo **vero** con
`node --input-type=module`, lo stesso ponte di `test_geometria_area.py`: il
ripiego lo dichiara, l'ora del core è quella del core, non torna indietro,
ignora tutto ciò che non è un istante.

`TestNessunPannelloHaUnOrologioSuO` — il **sorgente**, un file per volta:
nessun `new Date()` né `Date.now()` in `ui/src/panels/`. Un confronto di
comportamento non distingue «la copia non c'è» da «la copia c'è e per ora dice
lo stesso».

Provato che bocciano: rimesso un `new Date()` in `news.js` → rosso su
`news.js`; tolta l'alimentazione da `app.js` → rosso su
`test_l_orologio_e_alimentato`.

## 6. Tre difetti trovati per strada

**① La mia guardia passava su un commento.** La prima stesura di
`test_l_orologio_e_alimentato` cercava «orologio.js» nel file intero, e passava
per via della riga di spiegazione che avevo scritto accanto al codice. Un
criterio soddisfatto da qualcosa che non è il fenomeno — §11.7 regola 4,
commessa **dentro il test che la applica**. Adesso guarda il codice senza
commenti e chiede sia l'import sia la chiamata.

**② Due collisioni di nome.** `news.js` aveva già un `ora(ts)` che *formatta*
un istante, e `meteo.js` un `adesso` che è un nodo DOM. Il primo ha rotto la
galleria con `SyntaxError: Identifier 'ora' has already been declared`, e le
sette esecuzioni sono fallite in blocco. Risolte con un alias e la ragione
accanto. **`node --check` non l'aveva vista**: ho verificato i sette moduli con
un `import()` vero, che è la lezione già scritta e che avevo di nuovo saltato.

**③ Un test inchiodato a un numero di riga.**
`test_il_sesto_gradino_ha_UN_SOLO_consumatore` fissava
`ui/src/panels/lettura.js:113`, e un import in cima al file l'ha spostato a
114. Il consumatore era sempre uno: il test segnalava una cosa che non era
successa. Adesso fissa il **file**. Un allarme che scatta per una coordinata
invece che per il fenomeno viene disattivato al secondo falso positivo, e da lì
non protegge più niente.

## 7. Sulla scrivania non cambia niente

```
scrivania.png e prima.png: IDENTICI, 0 pixel di differenza
```

Ed è giusto: i cinque pannelli sono fuori scena, che è esattamente il motivo
per cui la deriva era latente. Le metriche restano dock 24,2 %, entropia 2,44,
`L>60` 28,0 %, caldo 3,7 %, barra 63,8 %.

## 8. Verifica

| | |
|---|---|
| `tests/test_orologio.py` | 25 passed |
| `npm run shot` su 8 componenti | tutti EXIT=0, audit 0 letterali |
| `import()` vero sui 7 moduli toccati | tutti caricano |
| `npm run scrivania:fixture` | EXIT=0, PNG identico |
| `uv run pytest -q` | **621 passed** |

## 9. Dichiarato aperto

- **`agent.mesh.ts` alimenta anche lui.** Arriva a 1 Hz e non è un problema —
  `alimenta` tiene il più recente — ma se un giorno i due orologi del core
  divergessero, qui vincerebbe il più avanti senza dirlo.
- **`ui/src/desk/` non è coperto dalla guardia sul sorgente**, solo
  `ui/src/panels/`. I tre `Date.now()` che restano lì sono legittimi, e allargare
  il controllo vorrebbe dire elencare le eccezioni due volte.
- **La risoluzione è 400 ms.** Nessun uso attuale ne soffre; un uso futuro che
  ne soffrisse deve usare `Date.now()` e dirlo.
