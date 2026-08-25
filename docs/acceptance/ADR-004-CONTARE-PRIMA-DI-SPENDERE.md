# Contare prima di spendere — ADR-004

**Rollback:** `9812d29`
**Criterio:** ADR-004 opzione A — «ogni sessione STT e ogni sintesi TTS registra
durata, provider e se era il fallback; il pannello telemetria mostra i minuti
del mese».
**Esito: SODDISFATTO per la registrazione e la riga. Il primo minuto vero si
conterà quando il microfono si accende — ed è per questo che viene prima.**

---

## 1. Perché prima del microfono, e non dopo

L'ordine era ⑤ microfono → ③ ADR-004. È stato invertito, e la ragione regge:

> Per tutta la durata di ② e ③ il sistema spenderebbe senza contare, che è
> esattamente il difetto per cui ADR-004 esiste.

Un mese di consumo non attribuito non si recupera. E ADR-004 costa poco — il
suo stesso testo dice «il dato lo produce già la pipeline, va solo contato».

## 2. Il difetto, con le parole dell'ADR

> Il sistema misura con precisione ciò che non gli costa, e non misura ciò che
> gli costa.

`core/llm/governor.py` accumulava `total_cost_usd` dagli eventi `result`: i
token dell'abbonamento, già pagati. §24.8 chiama Deepgram «la sola voce di
costo ricorrente del progetto» e **non c'era né `seconds`, né `fallback`, né la
riga nel pannello**.

⚠️ **Su questa macchina oggi non costa niente** — nessuna chiave Deepgram,
`edge-tts` gratuito, e la registrazione della fixture lo conferma
(`chiavi_presenti: []`). Il docstring del Governor lo diceva già. Il contatore
non serve a ridurre una bolletta che non esiste: serve a **esserci prima** che
esista.

## 3. Che cosa registra

`Governor.registra_voce(tier, provider, secondi, fallback=, esito=)` scrive in
`conso/YYYY-MM-DD.jsonl` la riga che ADR-004 chiede:

```json
{"tier": "stt", "provider": "deepgram", "durata_s": 12.5, "fallback": false, …}
```

`tier` vale `stt`/`tts` per la voce e `t1`/`t2` per l'LLM: **`conso/` resta un
registro solo**, e leggerlo in due forme diverse sarebbe due letture della
stessa domanda. `provider` e `fallback` restano `null`/`false` sulle righe
dell'LLM, e un test verifica che quelle righe **non entrino** nel conto della
voce — sommarle darebbe secondi di audio che nessuno ha pronunciato.

### `fallback` non è contabilità

È la misura di **quanto Deepgram sia davvero affidabile su questa rete**. Se i
minuti in ripiego locale sono molti, l'invariante 12 sta lavorando parecchio e
nessuno lo saprebbe. L'ADR lo dice: «il conteggio dei minuti in fallback locale
dice quanto Deepgram è realmente affidabile».

## 4. Il mese, e perché si legge dal disco

`consumo_voce_mese()` somma i secondi del **mese** per provider — è l'unità con
cui Deepgram fattura, e un totale giornaliero non risponde alla domanda di
§24.8.

Legge i file a ogni chiamata invece di tenere un totale in RAM: un contatore in
memoria si azzera a ogni riavvio del core, cioè **proprio quando serve**, e i
file ci sono già.

Due casi che un lettore ingenuo sbaglia, entrambi pinnati:

- **un file di un altro mese** non entra nel totale di questo;
- **una riga tronca** — il log si scrive in append da un processo che può
  morire a metà riga — non azzera un mese di misura.

## 5. La riga nel pannello

`state.snapshot` porta `voce.consumo`, e `panels/telemetry.js` lo mostra:

```
voce, questo mese · deepgram 0,3 min · whisper 0,1 min · 3 sessioni · 0,1 min in ripiego
```

Con zero consumo resta lo **stato vuoto**: `voce · nessun consumo registrato
questo mese`, in `--txt-ghost`. Non un «0 min» su un riquadro acceso — acceso
vuol dire «questo dato c'è», ed è l'idioma che barra e dock già usano.

Il pannello riceve adesso **due topic**: `telemetry` a 2,5 Hz e `state.snapshot`
una volta. Il consumo del mese non ha senso rimandarlo due volte e mezzo al
secondo.

## 6. La guardia del contratto ha fatto il suo mestiere

`test_ogni_campo_letto_dal_pannello_esiste_nel_messaggio` scandisce il sorgente
del pannello per i `t.<campo>` e li cerca in un messaggio `telemetry`. Ha
segnalato `voce` appena l'ho aggiunto.

**Non l'ho aggirata rinominando la variabile**, che sarebbe stato facile e
disonesto: il suo modello — «il pannello legge un topic» — non vale più, e il
modello è stato esteso. `_DALLO_SNAPSHOT` elenca i due campi che vengono
dall'altro topic, e un test nuovo verifica **l'altra metà**: che il core metta
davvero `voce.consumo` nello snapshot. Senza, il pannello mostrerebbe «nessun
consumo» per sempre credendo che sia zero — §11.7 regola 4, un criterio vero
per assenza.

Provato che boccia: tolto `"consumo"` da `engine.py` → rosso.

## 7. Il costo in densità, dichiarato

La riga nuova ha fatto scendere l'entropia da **2,44 a 2,43**: il margine
sulla soglia passa da +0,04 a **+0,03**.

È il quinto assottigliamento nei centesimi di questo progetto, e va detto
invece di lasciarlo scoprire: `docs/acceptance/DENSITA.json` lo registra e
`tests/test_densita.py` lo legge. Gli altri criteri non si muovono —
dev +2,9, `L>60` +3,1, barra +38,8.

Il costo è reale e la causa è nota: una riga di testo `--txt-dim` su
`--bg-raised` aggiunge massa a una banda già affollata. Non l'ho compensata con
una mossa cosmetica altrove: sarebbe stato inseguire il numero.

## 8. Verifica

| | |
|---|---|
| `tests/test_governor.py` | **6 passed** (file nuovo) |
| `tests/test_ws_contract.py` | 15 passed, e la nuova guardia boccia |
| `npm run shot -- telemetry` | audit 0 letterali · OK |
| `npm run verifica:densita` | EXIT=0, `DENSITA' CONFORME` |
| `uv run pytest -q` | **673 passed** |

## 9. Dichiarato aperto

- **Nessuno chiama ancora `registra_voce`**: la pipeline vocale non gira. È il
  cablaggio che si chiude con ⑤, e il contatore esiste apposta per essere lì
  quando arriva. Il documento lo dice invece di far credere che il criterio sia
  esercitato.
- **L'opzione C di ADR-004** — tetto mensile che degrada al locale — resta
  «rivalutata dopo il primo mese di misura». Nessun mese, nessuna
  rivalutazione.
- **Il margine dell'entropia è +0,03.**
