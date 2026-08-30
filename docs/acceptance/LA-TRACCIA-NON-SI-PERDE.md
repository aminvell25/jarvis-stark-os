# La traccia non si perde per strada — ADR-011, fetta 1

**Data**: 30 agosto 2026 · **Riferimento**: `docs/DECISIONI-COGNITIVE.md` ADR-011,
`CLAUDE.md` invariante 31 · **Rollback**: `e587a82`
**Test**: 1851 → **1877**, 25 saltati, **0 rossi**

---

## Il criterio, punto per punto

ADR-011 ne dichiara otto. Sei sono **verificati**, uno è **parziale e si dice
perché**, uno è verde con una nota.

| # | criterio | esito |
|---|---|---|
| 1 | N righe di diario con lo stesso id, dal `wake_trigger` alla riga del tool | ⚠️ **PARZIALE** — vedi sotto |
| 2 | uno script ricostruisce il turno dai due archivi | ✅ `scripts/diario.py --traccia` |
| 3 | un gesto lascia una riga di diario | ✅ e prima non ne lasciava nessuna |
| 4 | una ronda che cambia porta la traccia in `initiatives/`; una vuota non scrive | ✅ |
| 5 | un punto d'ingresso nuovo senza traccia fa fallire un test | ✅ sabotaggio 4 |
| 6 | la guardia boccia `invoke` passato per riferimento | ✅ sabotaggio 1 |
| 7 | le righe scritte prima si leggono ancora | ✅ su **61 righe vere** |
| 8 | `uv run pytest -q` verde | ✅ 1877 passati, 0 rossi |

---

## ① Il criterio 1 è parziale, e la parte che manca ha un nome

Il criterio chiede «dal `wake_trigger` alla riga del tool». **`wake_trigger` non
è una riga di diario: è una riga di log.** La scrive `PhraseWake`, e nel diario
non entra. Quindi la catena verificabile *dentro il diario* va dalla prima riga
del turno a quella del tool — quattro righe, misurate:

```
$ scripts/diario.py --traccia 3ccfe674048c
traccia 3ccfe674048c — 4 righe

16:40:45   ok  open_panel       via ui       {'panel': 'telemetria'}
16:40:45 ▸ signore  apri la telemetria
16:40:45 ◂ jarvis   Vedo, Signore.
16:40:45   ok  —                via t1       apri la telemetria
```

`wake_trigger` si ricongiunge nel **journal**, non nel diario:
`VoicePipeline._turno()` apre `bound_contextvars(traccia=…, origine=…)` e
`core/log.py:394` ha già `merge_contextvars` in testa alla catena, quindi ogni
riga di log del turno porta l'id senza che nessuna delle ottocento chiamate
cambi. Misurato dal vivo:

```
[info] azione_diretta  azione=scene:welcome_home frase=jarvis
                       origine=voce traccia=66b8bc59b229
```

Cioè: **una join fra due registri, non N righe in uno.** Va detto così.

**E il giro col microfono vero non è stato fatto.** `NON VERIFICATO`, non `PASS`.

---

## ② Il difetto peggiore di questa fetta era nello strumento, non nel codice

ADR-011 lo aveva previsto e il criterio 6 chiede di provarlo. Provato:

```
### 1-ronda-non-inoltra  →  core/protocolli.py
    ROSSI: test_regola_3_un_inoltratore_dichiarato_inoltra_DAVVERO
    1 failed, 24 passed
```

**Le regole 1 e 2 restano verdi.** È la misura di quanto valgono da sole: una
guardia che cerca nodi `Call` con `func.attr == "invoke"` trova le tre chiamate
di `core/engine.py`, le dichiara tutte in regola, e il percorso del protocollo
resta senza traccia **con la guardia verde** — perché `registry.invoke` lì si
passa per riferimento (`engine.py`) e si chiama altrove (`protocolli.py`).

Le tre regole, e la terza esiste solo per questo:

```
1. CHIAMATE      ogni `Call` a una porta passa `traccia=`
2. RIFERIMENTI   una porta nominata fuori da `Call` è VIETATA, salvo verso un
                 inoltratore DICHIARATO che passa `traccia=`
3. INOLTRATORI   di ogni inoltratore dichiarato si apre la definizione e si
                 verifica che inoltri davvero
```

---

## ③ Gli otto sabotaggi, con l'esito

Ogni riga: modifica applicata, `pytest` eseguito, file ripristinato.

| sabotaggio | rosso |
|---|---|
| `Ronda.esegui` non inoltra più la traccia | `test_regola_3_…_inoltra_DAVVERO` (1 e 2 verdi) |
| `emetti` non passa `traccia=` a `invoke_da_gesture` | `test_regola_1_ogni_chiamata_…` |
| `registry.invoke` passato nudo a un'altra funzione | `test_regola_2_…_per_RIFERIMENTO_e_vietata` |
| `TESTO = "testo"` aggiunto a `Origine` | `test_le_origini_sono_CINQUE`, `test_un_origine_inventata_non_entra` |
| `_turno()` conia una seconda traccia per `su_turno` | `test_le_DUE_uscite_del_wake_portano_LA_STESSA_traccia` |
| `invoke()` timbra solo il ramo `ok=True` | `test_e_ANCHE_i_rami_falliti`, `test_e_il_fail_closed_della_conferma` |
| `Diario.scrivi` omette la chiave quando è nulla | `test_un_ANNUNCIO_dichiara_di_non_avere_un_origine` |
| un quarto campo su `Traccia` | `test_la_traccia_ha_TRE_campi_e_non_e_un_contesto` |

---

## ④ I punti d'ingresso sono **cinque**, e sono una misura

La prima stesura di ADR-011 ne elencava sei. Il sesto — «testo dalla
scrivania» — **non esiste**, e l'assenza è una decisione presa:
`core/ws_server.py` prova cinque tipi di messaggio uno per uno, `app/preload.js`
espone quattro verbi dichiarando che restano quattro *«finché qualcuno non dice
perché ne serve una»*, ed `esegui_t0()` ha un solo chiamante di produzione, che
viene dalla voce. **Il documento è stato corretto; la superficie non è stata
inventata per far tornare il numero.**

| origine | nasce in | il record |
|---|---|---|
| `voce` | `pipeline.py` `_turno()` | diario, 3 punti |
| `gesture` | `engine.py` `_gesture_intento()` | diario, **riga nuova** |
| `protocollo` | `engine.py` `_consolida_di_notte()` | `initiatives/` |
| `ui` | `engine.py` `_imposta_da_ui()` | diario, via `_esito_confermato` |
| `avvio` | `engine.py` `_scrivanie_cambiate()` | diario, resoconto |

Due letture, dichiarate perché sono letture: `ui` **nasce** in `_imposta_da_ui`
e la conferma la **eredita** da `ToolResult.traccia_id` — coniarla in
`_esito_confermato` darebbe alla riga della conferma un id diverso da quello del
turno che l'ha causata; e `avvio` è **una per collegamento di scrivania**, non
una per boot, o tre mattine diverse porterebbero lo stesso id.

---

## ⑤ Due difetti trovati misurando, e nessuno dei due era ADR-011

### `scripts/diario.py` cadeva sulle righe che spiegano il silenzio

Trovato **provando la ricostruzione su un turno vero**, non da un test.
`_annota_instradamento` scrive `intento=None` — la chiave c'è e vale `null` —
quindi `d.get("intento", "?")` restituisce `None` e `f"{None:16}"` alza
`TypeError`.

Misurato sul diario vero: **8 righe su 61**, e il comando moriva con uno stack
trace. Il difetto è anteriore ad ADR-011 (riprodotto sul codice a `e587a82`) ed
è crudele nel modo peggiore: quelle righe esistono per spiegare **perché non è
successo niente**, e l'unico modo di rileggere un giorno passato si rompeva
proprio su quelle. Dopo la correzione, il 27 agosto si legge:

```
00:43:32   ok  —                via t1       il panetto della geometria.
01:21:46   ok  —                via t1       Aprite elemetria.
03:55:26   ok  —                via t1       Chi ore sono?
```

Tre trascrizioni che T0 non ha riconosciuto, illeggibili da tre giorni.

### La guardia degli invarianti era cieca sulla seconda metà

`TestGliInvariantiNonDivergono.blocco()` estrae §20 di `SPEC.md` fermandosi al
primo `` \n``` ``. Quando `CLAUDE.md` ha guadagnato un blocco di codice suo — la
gerarchia delle fonti, il 30 agosto — l'estrattore ha cominciato a fermarsi sul
fence **annidato**: confrontava **7.827 caratteri su 11.388**, e una divergenza
dopo quel punto sarebbe passata inosservata.

Il 30 agosto ce n'era davvero una: l'invariante 31 diceva «sei punti d'ingresso»
in §20 e «cinque» in `CLAUDE.md`. Il test l'ha segnalata **per il motivo
sbagliato** — la troncatura rendeva diversi anche i primi 7.827 caratteri.
Corretto: fence a quattro apici, che un ``` annidato non può chiudere.

---

## ⑥ Che cosa NON è verificato — per nome

1. **Il giro col microfono vero.** Il criterio 1 alla lettera vuole una frase
   detta da una persona. Non fatto. `NON VERIFICATO`.
2. **`Origine.GESTURE` dal vivo.** `engine.py` chiude la telecamera se MediaPipe
   manca, e **su questa macchina manca** (verificato: l'import fallisce). Il
   percorso è provato solo in test.
3. **`Origine.PROTOCOLLO` al suo innesco vero.** La ronda notturna parte da
   `_secondi_fino_alle(ORA_DEFAULT)`; è stata guidata direttamente, l'innesco
   orario no.
4. **Che l'id arrivi a *tutte* le righe di log.** `merge_contextvars` è in
   catena e l'effetto è misurato su `azione_diretta`; la copertura è quella dei
   test, non è totale.
5. **Il consolidamento notturno resta senza traccia.** `consolidate.py` scrive
   in `initiatives/` con `"traccia": null`, **dichiarato** in `SENZA_TRACCIA` e
   visibile a `scripts/orfani.py --diario`. Dargliela vuol dire un parametro su
   `Consolidatore.esegui()`, che ADR-011 non nomina: è il passo più piccolo dopo
   questa fetta.
6. **Una previsione del piano che era falsa, e va detto.** Il piano dichiarava
   «nove test falliscono per il limite `inotify` di questa macchina» e prendeva
   quel numero da una memoria, non da una misura. **Non si è riprodotto**: la
   suite gira verde per intero, prima e dopo. Il criterio 8 è soddisfatto senza
   la clausola.

---

## ⑦ Le due misure sul disco vero

```
$ scripts/orfani.py --diario        # sul diario dell'utente
61 righe in diario/ e initiatives/
 · vecchia                      61
Nessuna riga orfana: ogni riga senza traccia e' o d'archivio o dichiarata.

$ scripts/orfani.py --diario        # su una radice dati usa-e-getta, dopo un turno
8 righe in diario/ e initiatives/
 · dichiarata                    1     ← l'annuncio, che dichiara di non averne
 · tracciata                     7
```

Tre stati, e restano distinti: chiave **assente** = riga d'archivio; `null` =
il produttore dichiara di non avere un'origine; un id = si ricongiunge.
`Diario.scrivi` normalizza `""` a `None`, così non nasce un quarto stato che non
significa niente.

---

## ⑧ Costo

`core/traccia.py` è 130 righe, di cui ~70 di commento. Nessuna dipendenza nuova:
`uuid`, `time`, `dataclasses`, `enum` dalla libreria standard, e
`structlog.contextvars`, che era già in catena.

Definizioni pubbliche in `core/`: 531 → **535**. Orfani sospetti: **5, invariati** —
nessuna delle quattro definizioni nuove nasce senza chiamante.

Costo in contesto per T1: **zero**. La traccia non entra mai nel prompt.
