# Fase 0 e 0b — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 · **Commit**: vedi in fondo

Ogni criterio e' riportato con l'esito e con **come** e' stato verificato.
Quelli che non ho potuto verificare sono dichiarati tali, col motivo.

---

## FASE 0 — criteri di §22

### 1. «pytest verde» — ✅ VERIFICATO

```
uv run pytest -q   →   49 passed
```

| File | Test | Copre |
|---|---|---|
| `test_settings.py` | 18 | caricamento, validazione, permessi, ricarica a caldo |
| `test_secrets_never_leak.py` | 12 | i due varchi delle chiavi API |
| `test_platform.py` | 18 | Paths, Sensors, stub, conformita' ai Protocol |
| `test_python_version.py` | 1 | l'interprete e' 3.12 |

I test costruiscono la propria `config_dir` in `tmp_path` e la passano tramite
un `Paths` finto: **nessun test dipende da `~/.config/jarvis-os/`**. Una suite
che passa o fallisce a seconda della macchina non misura il codice.

### 2. «i token esistono prima di ogni CSS» — ✅ VERIFICATO

Due letture, entrambe soddisfatte.

*Nel tempo*: `tokens.css` e' nel commit della Fase 0 (`37e89b3`); ogni altro CSS
e' nel commit successivo.

*Nell'ordine di caricamento*: in `gallery.html` l'ordine e'
`fonts.css` → `tokens.css` → `chrome.css`.

`fonts.css` precede i token ed e' voluto: contiene **solo** `@font-face`, zero
valori di design, e una `@font-face` va dichiarata prima che il font venga
usato. E' separato da `tokens.css` proprio per non intaccarne il verbatim.

### 3. «nessuna chiamata OS fuori da `platform/`» — ✅ VERIFICATO

Per grep, non a occhio:

```
grep -rnE 'psutil|os\.environ|os\.getuid|os\.getenv|subprocess|sys\.platform|
           Path\.home|tempfile|bwrap|/proc/|st_mode|XDG_' core/ --include='*.py'
  | grep -v '^core/platform/'
→ nessun risultato
```

Controprova eseguita: le stesse chiamate **esistono** dentro `core/platform/linux.py`
(10 occorrenze), quindi il grep cerca davvero qualcosa.

### Consegne richieste

| Consegna | Esito |
|---|---|
| `pyproject.toml` con uv, Python 3.12, dipendenze del solo core | ✅ `requires-python = ">=3.12,<3.13"`; interprete effettivo 3.12.14 |
| Albero secondo §21.1 | ✅ con due scostamenti dichiarati (R3, R4) |
| `platform/base.py` coi quattro Protocol | ✅ + `is_private` (vedi sotto) |
| `platform/linux.py`: solo Paths e Sensors | ✅ sandbox e audio sollevano `NotImplementedError` |
| `Paths` prevede il socket UNIX | ✅ `runtime_dir()` e `socket_path()` |
| `settings.py`: 0600, pydantic §8, watchdog, SecretStr | ✅ |
| `tokens.css` = §10.1 verbatim | ✅ 32 righe, verificato con `diff` contro la specifica |
| Test: caricamento, validazione, hot reload, chiave assente dai log | ✅ |

---

## FASE 0b — criteri di §22

### 1. «un componente non conforme si illumina di magenta» — ✅ VERIFICATO

`npm run shot -- non-conforme` → `shots/non-conforme.png`, **guardato**.

L'audit riporta **3 elementi fuori sistema** (livello 1) e **22 regole con
valori letterali** (livello 2). Nello screenshot il componente e' cerchiato di
magenta con tre marcatori indicizzati, e sono visibili a occhio le violazioni
deliberate: angoli a 6px, alone ciano dell'ombra esterna, Comic Sans, Georgia.

### 2. «un componente conforme e' invisibile all'audit» — ✅ VERIFICATO

Non e' un criterio di §22: l'ho aggiunto perche' senza di esso il primo non
significa niente. Un audit che boccia tutto e' inutile quanto uno che non
boccia niente.

`npm run shot -- conforme --pulito` → **0 violazioni su entrambi i livelli**.
Screenshot guardato: pannello conforme all'anatomia §10.2, taglio a 45° sul
solo vertice in basso a destra, zero magenta.

### 3. «lo screenshot si genera con un comando» — ✅ VERIFICATO

```
npm run shot -- <componente> [--pulito] [--grid]
```

Avvia il server, scatta a 1920×1080 con `deviceScaleFactor: 2`, spegne, ed
**esce con codice ≠ 0** quando lo scatto non e' una verifica valida.

### 4. Verifica di `docs/design-reference/README.md` — ✅ VERIFICATO

`npm run check:refs` → famiglia-a 12 immagini, famiglia-b 4, README coerente.

---

## ❌ NON VERIFICATO — e perche'

### Il criterio visivo di §11.8, sezione TIPOGRAFIA

**I cinque woff2 non sono nel repository.** Barlow Semi Condensed e IBM Plex
Mono non sono installati nel sistema e non sono stati vendorizzati: `curl` e
`wget` sono in deny nei permessi, e non ho aggirato il divieto per altre vie.

Conseguenza: gli screenshot sono resi con i font di ripiego del sistema.
Reggono i punti GEOMETRIA, COLORE, CONTENUTO, MOVIMENTO e TECNOLOGIA di §11.8.
**Non regge TIPOGRAFIA**: «solo i cinque gradini», «tutti i numeri in
`--font-mono`», «etichette caps con letter-spacing ≥ .10em» sono stati
verificati sui *valori CSS* dall'audit, non sul *rendering*.

Il guardiano dei font rende impossibile scambiare questo per un successo:
`npm run shot` esce con codice 1 e la galleria lo dichiara in rosso in testa
alla pagina, visibile in entrambi gli screenshot.

**Per chiudere il punto**: mettere i cinque file in `ui/src/style/fonts/`
(istruzioni in `ui/src/style/fonts/README.md`) e rieseguire i due comandi.

### Il socket UNIX

`Paths.socket_path()` restituisce un percorso; **non esiste alcun trasporto**.
La verifica che l'autorizzazione via permessi del file funzioni appartiene alla
Fase 1. `RUNTIME_DIR_MODE = 0o700` vive in `core/platform/base.py` perche' il
valore stia nel codice e non nella memoria di chi scrivera' il server.

---

## Scostamenti dalla specifica, dichiarati

| # | Cosa | Decisione |
|---|---|---|
| **R1** | §21.4 e §18.2 descrivono TCP `127.0.0.1:8765` con token; `Paths` prevede un socket UNIX | Divergenza voluta (ADR-002 opzione B). L'autorizzazione la fa il kernel sui permessi del file. **Recepito in SPEC rev 5.1** (§3.2, §16.1b, §18.2, §21.4) e nell'invariante 7. Conseguenza gia' scritta nel docstring: l'API WebSocket del browser non puo' aprire un socket UNIX, quindi il renderer non parlera' mai direttamente col core |
| **R2** | §10.1 contiene un'ombra **esterna** in `.jarvis-panel`, l'invariante 19 dice «solo inset» | Deciso: l'invariante vieta l'**emissione di luce**, non la profondita'. L'audit ammette un'ombra esterna solo se la sua luminanza e' inferiore al fondo. `filter: drop-shadow` resta vietato senza eccezioni |
| **R3** | §21.1 dice `core/memory.py`, §5.5 dice `core/memory/consolidate.py` | Scelto **package** |
| **R4** | §21.1 elenca `config/{default.toml, settings.schema.json}` | **Non creati**: i modelli pydantic *sono* lo schema. Un JSON separato sarebbe una seconda sorgente di verita' |
| — | `app/package.json` di §21.1 | **Non creato**: un `package.json` vuoto e' JSON invalido e fa fallire qualunque strumento lo trovi. Nascera' in Fase 1b con contenuto vero |

## Scoperte durante l'implementazione

**`Paths.is_private()` non era nel piano.** SPEC §8 chiede permessi 0600 senza
dire chi li verifica. Scriverlo in `settings.py` avrebbe messo `st_mode & 0o077`
— semantica POSIX pura — nel codice applicativo, che e' il primo passo verso
la violazione dell'invariante 29. E' andato dietro l'interfaccia.

**Tre invarianti sono ora imposti dallo schema**, non dalla disciplina:
`fs.trash_only` accetta solo `True` (inv. 4), `llm.backend` solo `"claude_code"`
(inv. 11), `vision.scope` solo `"app"` (§12). Stesso principio dell'invariante 27.

**Il ciclo §11.7 ha trovato due difetti dell'audit al primo giro**, e li ha
trovati perche' ho guardato gli screenshot invece di limitarmi a generarli:

1. `row-gap: normal` su elementi non-flex dava `NaN`, e `NaN % 4 !== 0` e' vero:
   **ogni** elemento risultava violare. Lo ha scoperto la fixture conforme, che
   e' esattamente il motivo per cui esiste.
2. I riquadri con l'elenco delle violazioni **coprivano il componente**, cioe'
   la cosa che il ciclo esiste per far guardare. Sostituiti da un indice; il
   dettaglio e' andato nella barra e nell'uscita di `npm run shot`.

## Riepilogo

| | |
|---|---|
| Test Python | **49 verdi** |
| Criteri Fase 0 | **3 su 3 verificati** |
| Criteri Fase 0b | **4 su 4 verificati** (3 di §22 + 1 aggiunto) |
| Non verificato | **1** — tipografia resa, per assenza dei woff2 |
