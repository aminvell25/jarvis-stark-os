# Che cosa congela la fixture — i valori, e da dove vengono

**Rollback:** `03536ba`
**Risponde a:** «sono la mediana di ciò che la macchina mostra davvero, o un
punto scelto? Un numero congelato al valore comodo passa sempre, e questo
progetto ha già ritirato `L>25` per quel motivo.»

---

## 1. La risposta breve

**Nessuno ha scelto niente**: la registrazione è 75 secondi continui di una
sessione vera, presi dal socket del core, e lo scatto avviene dopo l'ultimo
frame. Non c'è un punto pescato.

**Ma «non scelto» non vuol dire «mediano»**, e per un campo su tre non lo è.

## 2. I valori congelati, e dove cadono nella sessione

172 campioni di telemetria in 74,6 s. Lo scatto mostra l'**ultimo**.

| campo | min | p25 | mediana | p75 | max | **congelato** | percentile |
|---|---|---|---|---|---|---|---|
| `ram_percent` | 31,4 | 31,4 | 31,4 | 31,5 | 31,7 | **31,4** | 59° |
| `package_temp_c` | 45,6 | 45,8 | 45,8 | 45,9 | 46,5 | **45,8** | 61° |
| `cpu_percent` | 2,3 | 3,3 | 3,8 | 4,1 | 12,1 | **4,3** | **90°** |

- **RAM e temperatura stanno alla mediana** (59° e 61°), e le loro
  distribuzioni sono strettissime: 0,3 punti di escursione su tutta la
  sessione.
- **La CPU no**: 4,3 % è il **90° percentile**. La mediana è 3,8.

Altri valori fissi dello scatto:

```
ram_available_bytes  16 647 798 784        core.uptime_s   37,9
top3                 claude-desktop 21,0 % · claude-desktop 15,5 % · gnome-shell 10,1 %
avvisi critici       0            (quindi la barra non resta su «degraded»)
fusi                 312 · 216 in luce · 96 in ombra
registrazione        4d5edf35cfdb64af · 214 frame · 9 topic
```

## 3. Quanto conta che la CPU sia al 90°

Meno di quanto sembri, e va detto perché.

La CPU entra nella misura per **due strade diverse**:

- **il numero in testa al pannello** — `CPU 4.3 %` — che è l'ultimo campione,
  cioè il 90° percentile. Sono poche decine di pixel di testo;
- **le due aree piene di uPlot**, che sono la parte che muove `L>60`: il
  grafico tiene gli **ultimi 120 campioni**, quindi la sua area è la
  distribuzione di **48 secondi** di sessione, non l'ultimo punto.

Quindi il criterio che potrebbe essere gonfiato da un campione alto — `L>60` —
non lo è: legge una finestra, non un istante. Il campione al 90° si vede solo
nel testo.

⚠️ **Non l'ho aggiustato**, e la ragione è §11.9: rifare la registrazione per
prendere un campione più comodo sarebbe scegliere il numero, cioè esattamente
la cosa che questa domanda esiste per escludere. E rifarla **azzera la
baseline**: tutto ciò che è stato misurato da `c15925d` in poi andrebbe
rimisurato.

## 4. La banda `25-120` è scesa, e non è rumore

Da **69,9 %** a **65,5 %** mentre l'entropia saliva da 2,20 a 2,44. Misurato:

```
  scarto della banda 25-120     −4,4 punti
  massa entrata nel bin 0       +4,34 punti
```

Coincidono a **0,06**. Il campo del globo è passato da `--bg-raised` (L 37,
dentro la banda) a `--bg-abyss` (L 7,6, **sotto** la banda): la massa non è
sparita, è uscita **verso il basso**.

Ed è la stessa mossa che ha alzato l'entropia — una banda meno affollata *è*
una distribuzione più articolata. Le due cose non sono in contraddizione: sono
lo stesso fatto letto da due metriche.

`25-120` non ha una soglia in `SOGLIE`: è stampata come contesto, come `lum` e
`L>120`.

## 5. Che cosa NON è congelato

| | |
|---|---|
| il renderer | Electron 43.4.0, Chrome 150.0.7871.224, dpr 1,25 — scritti in `occlusione.json`, non fissati |
| l'antialiasing e la GPU | dichiarati fuori controllo da `FIXTURE-DI-MISURA.md` |
| il fuso e il locale | `toLocaleTimeString("it-IT")` dipende dal TZ del processo |
| la contesa | due Electron insieme rompono tutto: ora lo impedisce `scripts/blocco.mjs` |

## 6. E adesso qualcuno la guarda

Fino a oggi i sei criteri erano misurati **a mano** e guardati da **nessuno**:
`verifica:scrivania` controlla dock, debordo, ombre e fuoco, non l'entropia.
Con un margine di **0,04** su 2,40, la prima superficie toccata lo rompeva in
silenzio.

```
npm run verifica:densita
```

scatta la fixture e giudica, scrivendo `docs/acceptance/DENSITA.json` con
l'impronta di **106 sorgenti** (`ui/src/**` più `ui/*.html`, `vendor/` escluso).
`tests/test_densita.py` verifica che l'esito sia fresco, che venga dalla
**fixture** e non da una scrivania viva, e che nessun margine sia negativo.

Provato che boccia: toccato `tokens.css` → rosso sull'impronta; messo
`provenienza: VIVA` → rosso sulla provenienza.

E ogni riga di `densita.mjs` porta adesso la provenienza — `VIVA` oppure
`fixture:4d5edf35cfdb64af` — che è ciò che §11.7 regola 5 chiedeva e che non era
mai stato fatto.

## 7. I margini, tutti e sei

| criterio | valore | soglia | margine |
|---|---|---|---|
| **entropia** | 2,44 | 2,40 | **+0,04** |
| dev.std | 34,8 | 32 | +2,8 |
| `L>60` | 28,0 % | 25 % | +3,0 |
| caldo | 3,7 % | 3–6 % | +0,7 / −2,3 |
| barra | 63,8 % | 25 % | +38,8 |
| dock | 24,2 % | 20 % | +4,2 *(in rapporto)* |

**È solo l'entropia a essere sul filo**, ed è il quarto atterraggio nei
centesimi di questo progetto: marchio 3,01/3,00, piano 2,428/2,40,
`--txt-primary` 4,536/4,50, e adesso 2,44/2,40. Il margine è scritto
nell'esito e un test lo legge: il giorno in cui si assottiglia ancora, il
numero è lì.

## 8. Dichiarato aperto

- **`shots/scrivania/` esiste ancora su disco** e non la produce più nessuno:
  `npm run scrivania` scrive in `shots/scrivania-viva/`. Non l'ho cancellata —
  `rm -rf` è negato dalle impostazioni del progetto, e non l'ho aggirato con un
  altro comando. Si può togliere a mano; `shots/` è in `.gitignore`.
- **Il campione di CPU al 90° percentile** resta quello. Vedi §3.
- **La misura vale per la registrazione `4d5edf35cfdb64af`.** Rifarla azzera la
  baseline (§11.9).
