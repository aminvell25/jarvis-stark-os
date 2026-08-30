# §26.9 criterio 6 — la scena esisteva, e non era mai stata applicata

**Data:** 30 agosto 2026 · **Riferimento:** `docs/SPEC-26-AMBIENTE-UNICO.md`
§26.9 punto 6, §26.6 · **Rollback:** `8799b78` · **Test:** 1872 → **1876**

---

## ⚠️ Una correzione, prima di tutto

Ieri ho scritto che il criterio 6 mancava perché *«la scena non è mai stata
scritta»*. **Era falso.** `briefing` esiste in `config/settings.toml` — la
`settings.toml` versionata del repo — dal giorno di §26.6, con le celle di §26.6
alla lettera. Avevo guardato `~/.config/jarvis-os/settings.toml`, che di scene
non ne ha, e `ui/src/desk/moduli.js`, che dichiara solo `avvio`.

Quello che mancava è l'altra metà, ed era già dichiarata altrove:
`LE-FRASI-PUNTANO-A-UNA-SCENA-CHE-ESISTE.md` diceva *«non ho verificato dal vivo
che la scena si applichi sullo schermo»*.

## La prima metà: applicata, e misurata

`scripts/prova-scena.mjs` fa il giro intero — `settings.toml` → core →
`ui.scene` → `dichiaraScene` → `applicaScena` — su Electron vero e core vero.

```
scene dichiarate dal core   avvio · briefing · officina
scena                       avvio  ->  briefing

VISIBILI   news        x   4  y  36   592×501   z 25
           telemetria  x 604  y  36   550×332   z 24
           agenti      x 964  y 206   472×332   z 23
nascosti   globo · file · cartella
```

Tre cose che il criterio chiede e che ora sono numeri:

- **la scena si applica**: `scenaCorrente` passa a `briefing`. Non è ovvio —
  `applicaScena` ritorna `null` per un nome non dichiarato, cioè fallirebbe in
  silenzio;
- **restano i tre dichiarati**, e gli altri sono **nascosti, non chiusi**:
  chiudere costerebbe i dati che il core manda una volta sola, e far sparire il
  pannello su cui si stava lavorando è ciò che rende un ambiente inabitabile;
- **la pila rispetta lo `z` dichiarato**: news 3 > telemetria 2 > agenti 1.

### ⚠️ Una coppia si sovrappone, non tre

```
telemetria / agenti   190 × 162 px   sopra: telemetria
```

§26.6 scrive *«le celle si sovrappongono di proposito»*, **ma i suoi stessi
numeri danno una sola sovrapposizione**: `news` occupa le colonne 0–4 e
`telemetria` comincia dalla 5, quindi a schermo sono affiancate — misurati **8 px
di distacco**. Si sovrappongono `telemetria` (5–8) e `agenti` (8–11).

La prova custodisce ciò che i numeri dicono, non ciò che la frase promette.
Pretendere tre sovrapposizioni vorrebbe dire cambiare le celle di §26.6 dentro un
turno di implementazione, e quello non si fa.

## La seconda metà: lo screenshot c'è, il confronto **non è alla pari**

`npm run scena:briefing` lo riproduce. `SCENA` era un letterale in
`app/main.js` — il modo di scatto sapeva comporre una scena sola — ed è
diventato `opzione("--scena") ?? "avvio"`, così ogni scatto già preso continua a
valere.

Misurato con lo strumento del progetto, `scripts/densita.mjs`:

```
scrivania.png  1920x1062  lum 36.5 · dev 24.6 · H 1.77 · L>60 13.6% · caldo 0.1% · barra 40.2%
SOTTO SOGLIA — entropia 1.77 < 2.4 · dev.std 24.6 < 32 · riempito 13.6% < 25% · caldo 0.1% < 3%
dock 19.4% · soglia 20% · riferimento 22,8-26,2% · SOTTO, in rapporto non boccia
§5.4 soddisfatto: niente si muove senza causa — quel che cambia è telemetry all'89%
pavimento coperto dai pannelli 52.7%
```

**Sotto soglia su tutto tranne la barra. E il confronto non dice quello che
sembra dire**, per due ragioni che vanno dette invece di essere aggirate:

1. **Il core di questa prova non ha dati.** Gira su una configurazione a parte
   (`XDG_CONFIG_HOME`), senza chiavi: niente news, nessuna storia di telemetria,
   nessun archivio. Tre pannelli vuoti non possono raggiungere una densità
   tarata su una scrivania piena.
2. **Le soglie sono del criterio 8, e sono state tarate sul banco fixture** con
   la scena `avvio`: cinque pannelli, il fondo con le icone e le cartelle
   manila. `DENSITA.json` le soddisfa lì, con entropia 2,44.

### Perché non si è fatto lo scatto sul banco fixture, che sarebbe alla pari

Perché **il banco non conosce le scene**: `docs/acceptance/SESSIONE-SCRIVANIA.jsonl`
porta un frame `ui.scene` con `scene: []`, registrato da un core la cui
`settings.toml` non ne dichiarava nessuna. Per avere `briefing` sul banco
bisognerebbe **ri-registrare la sessione**, che è un artefatto congelato
(`FIXTURE-CHE-COSA-CONGELA.md`) e la provenienza della baseline del criterio 8
(`provenienza: fixture:4d5edf35cfdb64af`). Cambiarla vuol dire rimisurare il
criterio 8.

**Prezzo dichiarato, decisione non presa.** È del Signore.

## Esito del criterio 6

| metà | esito |
|---|---|
| «`scene:briefing` dispone tre pannelli sovrapposti» | ✅ soddisfatta, con la precisazione sulla coppia |
| «Screenshot allegato, confrontato con `famiglia-a/01`» | ⚠️ **NON MISURABILE alla pari** — lo scatto c'è ed è misurato, il confronto è contro una scrivania piena di dati che questa non ha |

## Le bocciature — eseguite

1. **Tolto il ciclo che nasconde** in `applicaScena`: la prova cade elencando i
   pannelli di troppo — `{agenti, cartella, file, globo, news, telemetria}`
   contro i tre attesi.
2. **Spostata `agenti` fuori da `telemetria`** nella `settings.toml` della prova
   (celle `[9, 2, 3, 2]`): *«nessun pannello ne copre un altro: la scena è
   diventata una piastrellatura, e §26.2 esiste per la sovrapposizione»*.

## Che cosa resta da dire

**Sulla macchina del Signore `briefing` non esiste.**
`~/.config/jarvis-os/settings.toml` non ha nessun blocco `[[ui.scene]]`: è più
vecchia di §26.6. La scena vive in `config/settings.toml`, versionata. Copiare i
tre blocchi nella configurazione viva è una modifica al Suo ambiente e non
l'ho fatta — `tests/test_scena.py` **salta** invece di essere rosso, e dice come
si prova.
