# La fixture di misura — T3 del piano, e il pavimento di rumore

**Rollback:** `6017343`
**Criterio:** i tre gradini del piano, misurati su sedici esecuzioni.

---

## 1. Perché

Due sessioni di `npm run scrivania` davano `L>60` **26,1 %** e **25,3 %**, e la
differenza non era attribuibile. Il margine sulla soglia era passato da +1,1 a
+0,3 in un turno che non aveva toccato nessuna superficie. L'unica soglia
ancora aperta — entropia 2,21 su 2,40 — si chiude con mosse che valgono +0,07
l'una: sotto il rumore.

§11.9 rev 5.22 concede la seconda eccezione — il **modo di misura** — e questo
documento è la sua prima applicazione.

## 2. I tre gradini

| | che cosa | esito |
|---|---|---|
| **1** | `scattiIdentici === true` **dentro** l'esecuzione | **16/16** |
| **2** | `sha256(scrivania.png)` uguale fra esecuzioni | **15/16** |
| **3** | metriche identiche alla precisione stampata | **8/8** (misurate su otto delle sedici) |

Prima di questo turno il gradino 1 era `false` in **tutti e quattro** gli
`occlusione.json` esistenti.

### Il numero che conta

```
scrivania.png     1536x843   lum 46.5 · dev 34 · H 2.2 · 25-120 69.8 %
                             L>60 25.1 % · L>120 5.7 % · caldo 3.8 % · barra 63.8 %
  in 250 ms cambiano 0 pixel su 1.294.848 — 0.00 %, massimo scarto 0/255
  §5.4 soddisfatto: niente si muove senza causa
```

**Il pavimento di rumore è passato da ±1 punto di `L>60` a 0,00.** Un delta di
+0,07 di entropia adesso si legge.

⚠️ **Queste cifre non si sottraggono da nessuna misura viva** (§11.7 regola 5).
La baseline è la registrazione `4d5edf35cfdb64af` e nient'altro.

## 3. L'unica esecuzione deviante, e che cosa se ne sa

Su sedici, una ha dato un PNG diverso. È anche l'unica con **67 render
three.js invece di 5** — tutte le altre quindici: esattamente 5.

**Non è una causa dimostrata.** Il PNG deviante non era stato conservato,
quindi la differenza **non è attribuibile**: si sa che c'era e non si sa dove.
L'ipotesi è che il `ResizeObserver` di `ui/src/three/scena.js:115` alzi `sporco`
a ogni fotogramma dell'animazione di apertura, e che quanti ne cadano dipenda
dal carico — ma è un'ipotesi, e resta tale finché una deviazione non viene
catturata.

Due cose sono state fatte perché la prossima lo sia:

- `node scripts/densita.mjs --differenza <a.png> <b.png>` confronta due PNG di
  esecuzioni diverse, col riquadro e l'attribuzione ai pannelli;
- il conteggio dei render finisce in `occlusione.protocollo.budget`, cioè
  **viaggia col numero** invece di restare in un log che nessuno conserva.

### Che cosa NON è la causa, misurato

I `GPU process launch failed` comparivano in due esecuzioni. Sono alla riga 22
del log, gli scatti alla 13: **dopo**. Artefatto di chiusura, scartato.

## 4. Riproduzione a 10× — adottata perché misurata

Due esecuzioni a 1× e due a 10× danno lo **stesso PNG byte per byte**, e il
giro passa da ~100 s a **20 s**. Per questo `npm run scrivania:fixture` passa
`--velocita 10`.

A 10× la telemetria arriva a 25 Hz invece di 2,5 e il grafico resta identico
perché `telemetry.js` tiene gli **ultimi** 120 campioni comunque: cambia quando
arrivano, non quali restano.

⚠️ Vale per **questa** registrazione. Rifarla azzera la baseline (§11.9), e
l'equivalenza 1×/10× va rimisurata insieme al resto.

## 5. Il difetto che il turno ha trovato in sé stesso

`impronta()` scriveva `null` in `occlusione.json`: una misura **senza
provenienza**, che è precisamente ciò che §11.7 regola 5 vieta. La causa era un
`catch { return null; }` che ingoiava un `ReferenceError: fs is not defined` —
`fs` era dichiarato **tre volte dentro tre funzioni**, più due `require` in
linea, e un aiutante di modulo non ne vedeva nessuno.

È la stessa specie già contata cinque volte in due giorni: **un valore assente
che diventa un numero permissivo.** Tolto il `catch`, l'errore è diventato
rumoroso in un giro; `fs` adesso ha un proprietario solo, di modulo.

## 6. E il difetto che ho introdotto io

Ho scritto un confronto di pixel in `app/main.js` e un secondo in
`scripts/differenza.mjs`, e poi ho scoperto che `densita.mjs` **ce l'aveva già**
— con riquadro e attribuzione ai rettangoli:

```
  in 250 ms cambiano 0 pixel su 1.294.848 — 0.00 %, massimo scarto 0/255
```

Tre proprietari per la proprietà «dove cambiano i pixel», due dei quali miei,
nello stesso turno in cui il documento di ieri chiamava quel difetto per nome.
**Entrambi ritirati.** Di nuovo esiste solo `differenza()` in `densita.mjs`;
l'unica capacità che mancava davvero — confrontare due PNG di esecuzioni
diverse — è diventata un **modo** di quella funzione, non una seconda copia.

La regola che avrebbe evitato il giro a vuoto: **prima di scrivere una misura,
cercare se la misura c'è già.** `grep -n "cambiano" scripts/densita.mjs`
costava cinque secondi.

## 7. Verifica

| | |
|---|---|
| `uv run pytest -q` | **579 passed** in 59,84 s |
| `uv run pytest -q tests/test_fixture_scrivania.py` | 6 passed |
| `npm run verifica:scrivania` | **EXIT=0** |
| `npm run scrivania:fixture` | EXIT=0, 16 esecuzioni |
| impronta dichiarata in `occlusione.json` | `4d5edf35cfdb64af` |

## 8. Dichiarato aperto

- **La deviazione 1 su 16 non è attribuita.** Correlato misurato (67 render
  contro 5), meccanismo ipotizzato, prova assente.
- **Antialiasing, GPU e font non sono controllati.** `occlusione.protocollo.renderer`
  li dichiara — Electron 43.4.0, Chrome 150.0.7871.224, dpr 1,25 — perché una
  fixture fissa i **dati**, non il renderer.
- **Cinque orologi vivi latenti**: `news.js`, `meteo.js`, `console.js`,
  `lettura.js`, `calendario.js`. Zero pixel oggi perché fuori scena. Elencati
  per nome perché il giorno in cui qualcuno li compone non vanno riscoperti.
- **Fuso e locale**: `toLocaleTimeString("it-IT")` dipende dal TZ del processo.
- **La registrazione invecchia**: `source.tree` e `tools` fotografano il repo
  del 25 agosto 2026.
- **T4 resta fuori**, come da piano: il latch `degraded` di `barra.js:438-442`.
  Il suo Δ è ~560 px su 1 294 848 = **0,043 %**, sotto la precisione stampata:
  non sarà misurabile nemmeno con questa fixture, e va detto prima.
