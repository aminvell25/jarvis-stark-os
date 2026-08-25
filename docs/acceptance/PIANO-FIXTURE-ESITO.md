# Il piano della fixture — esito

Cinque turni, cinque commit, dal 25 agosto 2026.

| | turno | commit | che cosa ha comprato |
|---|---|---|---|
| T0 | il cancello §11.9 | `4c8c35b` | la seconda eccezione — il **modo** di misura — e §11.7 regola 5 |
| T1 | `quando` in `geo.timezones` | `cb4a52b` | un orologio solo per un'immagine sola |
| T2 | il registratore | `6017343` | una sessione vera su disco, con due guardie contro il ritocco |
| T3 | il riproduttore e il modo | `c15925d` | **il pavimento di rumore a 0,00** |
| T4 | il `degraded` che non tornava | `6aa7db0` | un difetto che nessuna misura di densità poteva vedere |

## Il problema che c'era

Due sessioni di `npm run scrivania` davano `L>60` **26,1 %** e **25,3 %**, e la
differenza non era attribuibile a niente. Quattro misure erano già state
contaminate dallo stesso meccanismo. Il margine sulla soglia era passato da
+1,1 a +0,3 in un turno che non aveva toccato nessuna superficie.

## Il problema adesso

```
dev 34 · H 2.2 · L>60 25.1 % · caldo 3.8 % · barra 63.8 %
in 250 ms cambiano 0 pixel su 1.294.848 — 0.00 %, massimo scarto 0/255
```

Sedici esecuzioni: `scattiIdentici` **16/16**, PNG identico **15/16**, metriche
identiche a ogni cifra stampata su tutte quelle misurate.

**L'entropia a 2,21 contro 2,40 resta l'unica soglia aperta, e adesso è
attaccabile**: le mosse che valgono +0,07 l'una prima sparivano nel rumore, e
adesso si leggono.

## Le tre regole nuove, in ordine di quanto sono costate

**La provenienza di una misura fa parte della misura** (§11.7 regola 5). Un
numero senza la sua sorgente non è un numero: non si sa con che cosa si può
confrontare. Due numeri di provenienza diversa **non si sottraggono**.

**La fixture compra delta attribuibili dentro una baseline, non comparabilità
fra baseline diverse.** Rifare la registrazione **azzera** la baseline.

**Una fixture fissa i dati, non il renderer.** Electron, Chrome e dpr sono
scritti dentro `occlusione.json` perché un aggiornamento di driver o di font
sposta il numero senza che nel repo cambi niente.

## Quello che il piano aveva previsto giusto

- che il gradino 1 fosse il vero collaudo dell'impianto: è arrivato al primo
  colpo, ed era `false` in tutti e quattro gli scatti precedenti;
- che T4 andasse tenuto in un turno suo, perché il suo Δ è lo 0,043 % e
  impacchettato con la fixture avrebbe lasciato un'ambiguità insolubile;
- che T1 dovesse precedere T2, o il globo sarebbe ricaduto su `new Date()`
  **dentro** la fixture;
- che `--velocita` andasse **misurata** e non scelta: 1× e 10× danno lo stesso
  PNG, e il giro passa da ~100 s a 20 s.

## Quello che ha sbagliato

Il piano dava il gradino 1 come **obbligatorio**, cioè come precondizione dei
gradini 2 e 3. Misurato: in una tornata i gradini 2 e 3 erano già verdi mentre
il gradino 1 era `1, 0, 0`. Sono tre proprietà indipendenti — «la scrivania sta
ferma» e «la misura si ripete» non sono la stessa domanda.

## Aperto, dichiarato

- **Entropia 2,21 contro 2,40.** L'unica soglia sotto, e adesso misurabile.
- **Una deviazione su sedici non è attribuita.** Correlato misurato — 67 render
  three.js contro 5 — meccanismo ipotizzato, prova assente. `densita.mjs
  --differenza` esiste perché la prossima lo sia.
- **Dock al 2,0 % contro 20.** In rapporto, non blocca.
- **Cinque orologi vivi latenti**: `news.js`, `meteo.js`, `console.js`,
  `lettura.js`, `calendario.js`. Zero pixel oggi perché fuori scena.
- **L'uscita di `--scrivania` non propaga.**
- **La registrazione invecchia**: `source.tree` e `tools` fotografano il repo
  del 25 agosto 2026.
