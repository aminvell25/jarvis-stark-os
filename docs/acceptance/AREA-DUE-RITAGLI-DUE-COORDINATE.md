# Due ritagli, due spazi di coordinate, una proprietà sola

**Rollback:** `7c9fbcc`
**Criterio:** §26.9 criterio 4 — «riaperta l'app, il pannello è dove l'ho
lasciato», verificato riavviando davvero.
**Esito: SODDISFATTO. E la fascia del dock può tornare alla sua altezza.**

---

## 1. Il difetto

`area_larghezza` e `area_altezza` descrivono il **pavimento** — lo spazio fra
barra e dock. Ma pannelli e icone sono salvati in coordinate di **finestra**:
lo strato delle icone è `position: fixed; inset: 0`, e un pannello a `y = 36`
sta 36 px sotto il bordo della finestra, non del pavimento.

Il ritaglio esisteva in **tre posti**:

| chi | banda ammessa per `y` |
|---|---|
| `ui/src/desk/geometria-area.js::dentroArea` (pannelli) | `[alto, alto + altezza − 80]` |
| `ui/src/desk/icone.js::dentroArea` (icone) | `[alto, alto + altezza − 80]` |
| `core/layout.py::adatta` | `[0, altezza − 80]` |

I due del renderer concordavano. Il core no: **la sua banda era traslata in su
di quanto è alta la barra**, 32 px. Misurato, con pavimento 32..815:

```
  renderer  dentroArea: y ammessa [32, 735]
  core      adatta:     y ammessa [0, 703]
```

Due conseguenze, in direzioni opposte:

- il core **ammetteva** una posizione fra 0 e 31, cioè **dentro la barra**,
  dove un'icona è coperta e non si riprende più;
- il core **spostava** una posizione fra 704 e 735, cioè buona, in fondo al
  pavimento.

## 2. Perché nessuno l'aveva visto

Perché era latente finché i numeri non si muovevano. `7c9fbcc` ha alzato il
dock di otto pixel per fare posto ai campi di stato, il pavimento è passato da
783 a 775, e la banda del core da `[0, 703]` a `[0, 695]`. Un'icona a y 700
sopravviveva al primo e non al secondo:

```
FAILED tests/test_layout.py::TestIconeVere::test_10_riavviato_il_core_e_ANCORA_LI
```

Quel turno ha aggirato il sintomo — padding verticale a `--s-1`, la fascia
resta 28 px — e ha dichiarato il fatto sottostante aperto. Questo lo chiude.

## 3. La correzione

`adatta()` impara **dove comincia** l'area:

```python
def dentro(v: int, comincia: int, quanto: int) -> int:
    return max(comincia, min(v, comincia + quanto - minimo_visibile))
```

E il segnale viaggia lungo tutta la catena, che prima ne portava metà:

```
ui/src/desk/scrivania.js  area: { sinistra, alto, larghezza, altezza }
app/preload.js            → forward
app/main.js               → area_sinistra, area_alto
core/layout.py            LayoutMessage → adatta(…, sinistra=, alto=)
```

`Layout` guadagna `area_sinistra` e `area_alto` opzionali, così la prossima
apertura sa contro che cosa era stato tagliato.

**I valori predefiniti sono zero**, cioè il comportamento di prima: un renderer
che non manda i due campi continua a funzionare, con la banda vecchia. È
sbagliata di quanto è alta la barra, ma non è una rottura — e un test lo pinna.

## 4. Che cosa prova, e che cosa proverebbe se cadesse

`TestLAreaCominciaDaQualcheParte`, sette asserzioni:

| | |
|---|---|
| un'icona in fondo al pavimento **non si muove** | y 720 resta 720 (prima: 703) |
| un'icona **non può finire dentro la barra** | y 10 diventa 32 (prima: 10) |
| la banda è quella di `dentroArea` | i quattro estremi, uno per uno |
| **il dock che cresce non sposta un'icona** | la regressione alla lettera: 783 → 775, y 700 resta 700 |
| vale anche per i pannelli | non è un difetto delle sole icone |
| l'origine viene ricordata | `area_sinistra`, `area_alto` |
| un messaggio senza origine si comporta come prima | la scelta di compatibilità, pinnata |

E la prova che discriminano, misurata:

```
  alto= 0: y 720 -> 703
  alto=32: y 720 -> 720
```

## 5. Il fantasma che ho quasi diagnosticato

Rimesso il dock a 36 px per la prova end-to-end, cadevano **due** test invece
di uno, e `su_disco` era `null`: il core non scriveva più niente.

Non era un secondo difetto. **Il core in esecuzione precedeva la mia
modifica**: `LayoutMessage` ha `extra="forbid"`, quindi il processo vecchio
rifiutava `area_sinistra` e `area_alto` e scartava il messaggio intero. Girava
da tre ore — è lo stesso pid che ha prodotto la registrazione della fixture.

Riavviato il core, **11 passed** col dock a 36 px.

⚠️ È la seconda volta in due giorni che un core vecchio produce un esito che
sembra un difetto del codice nuovo: la prima fu `quando = None` in
`geo.timezones`. La regola vale la pena scriverla: **dopo aver toccato uno
schema del core, il core si riavvia prima di credere a un test end-to-end.**

## 6. E la fascia del dock torna alla sua altezza

`DOCK-LA-FASCIA-ERA-VUOTA.md` §6 diceva:

> La strada per rientrare nella forbice non è togliere campi: è alzare la
> fascia al 5,9 %. Ma alzarla sposta il pavimento — cioè esattamente ciò che ha
> fatto cadere `TestIconeVere`.

L'ostacolo non c'è più, quindi il padding verticale torna a `--s-2`:

| | 28 px | 36 px |
|---|---|---|
| **dock** | 31,2 % | **24,2 %** ✅ dentro 22,8–26,2 |
| altezza della fascia | 3,3 % | **4,3 %** (riferimento 5,9 %) |
| entropia | 2,43 | **2,44** |
| `L>60` | 27,9 % | **28,0 %** |
| caldo | 3,8 % | 3,7 % |

Non è ampliamento di quello che era stato chiesto: è il compromesso che
`7c9fbcc` aveva preso **solo** per aggirare questo difetto, e che senza il
difetto non ha più una ragione.

## 7. Verifica

| | |
|---|---|
| `TestLAreaCominciaDaQualcheParte` | 7 passed |
| `TestIconeVere` col dock a **36 px** | **11 passed** (prima: 1 rosso) |
| `TestIconeVere` col dock a 28 px | 11 passed |
| `npm run scrivania:fixture` | EXIT=0, `scattiIdentici` true |
| `uv run pytest -q` | **592 passed** |
| `tests/test_ws_contract.py` | 14 passed dopo l'aggiornamento deliberato dell'elenco |

## 8. La guardia del ponte ha fatto il suo mestiere

`TestSuperficieDelPreload::test_la_dichiarazione_di_stato_non_nomina_nessuna_operazione`
inchioda l'elenco esatto dei campi che il ponte può mandare, ed è caduto appena
ne ho aggiunti due. È il comportamento voluto: il suo commento dice «l'elenco
cresce quando cresce l'ambiente; ciò che NON deve entrare è qui sotto».

`area_sinistra` e `area_alto` sono due interi che dicono **dove** comincia il
pavimento, come larghezza e altezza dicono quanto è grande. Non nominano
un'operazione né un posto sul disco, e la seconda asserzione del test — quella
che non deve mai cedere — è rimasta intatta. L'elenco è stato aggiornato con la
ragione scritta accanto, non allargato.

## 9. Dichiarato aperto

- **Tre implementazioni dello stesso ritaglio restano tre**: `geometria-area.js`
  per i pannelli, `icone.js` per le icone, `adatta()` nel core. Adesso
  concordano, e niente lo impone: concordano perché tre commenti lo dicono.
  Unificarle vuol dire un confine fra Python e JS, ed è un turno suo.
- **`MIN_VISIBILE = 80` in JS e `minimo_visibile = 80` in Python** sono due
  numeri per la stessa soglia. Stessa specie, stesso rimedio mancante.
- **`TestIconeVere` è instabile quando gira insieme al resto del file**: una
  volta su alcune, `test_1` cade e da lì cade il resto. È il conflitto sul
  socket del core vivo che `tests/test_catalogo.py` documenta. Non l'ho
  toccato.
- Le misure di densità valgono per la registrazione `4d5edf35cfdb64af` (§11.9).
