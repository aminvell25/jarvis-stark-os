# Fase 1b — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 1b
**Test**: 135 verdi (erano 124) · **Precedente**: `FASE-01.md`

⚠️ **Ordine.** §22 mette Fase 1b fra la 1 e la 2. Era stata saltata: alla
richiesta «Fase 2» ho fermato il lavoro e segnalato che Fase 2 consegna un
pannello file manager e la conferma §6.2 «UI mostra il PATH ASSOLUTO RISOLTO»,
e che entrambi hanno bisogno della finestra che nasce qui.

---

## Il rischio che questa fase esisteva per ritirare

Nella rev 5.1 avevo scritto in §18.2, e nel docstring di
`Paths.socket_path()`, che l'API `WebSocket` del browser non può aprire un
socket UNIX e che quindi il renderer non parlerà mai direttamente col core.
**Non era mai stato provato, e l'avevo introdotto io.** Fase 2 avrebbe
progettato il flusso di conferma su quella premessa.

Provato su entrambi i lati, prima di scrivere qualunque altra cosa:

| Prova | Esito |
|---|---|
| Node con `ws` su `ws+unix://…` | **si collega**, riceve snapshot e telemetria |
| Chromium — lo stesso motore del renderer — su `ws+unix://…` | `DOMException: The URL's scheme must be either 'ws' or 'wss'` |
| Chromium su `unix://…` | stessa eccezione |

**L'affermazione regge.** L'architettura del ponte è confermata, e Fase 2 può
poggiarci sopra.

---

## I due criteri di §22

### 1. «catena core → WS → Electron → pannello» — ✅ VERIFICATO

```bash
uv run python -m core.engine &
npm run app -- --screenshot shots/app-collegato.png
```

`shots/app-collegato.png`, **guardato**: CPU 3,9 % · RAM 52,6 % · TEMP 44,9 °C ·
LIBERA 10,7 GiB, la striscia uPlot con la traccia reale della CPU su 12
campioni, e i tre processi veri (`claude-desktop 22 %`, `claude-desktop 17 %`,
`gnome-shell 8 %`).

**Che il dato sia misurato e non inventato** è verificato con la stessa
controprova di Fase 1: `ws_probe.py` legge psutil in un proprio processo e
stampa i valori accanto. RAM 52,7 % e temperatura 45,25 °C, presi un istante
prima. Coincidono.

### 2. «il pannello supera la checklist §11.8 col ciclo §11.7» — ✅ VERIFICATO

`npm run shot -- telemetry --pulito` → audit **0 e 0** su entrambi i livelli,
font tutti caricati, uscita 0. `shots/telemetry.png` **guardato**.

| §11.8 | Esito |
|---|---|
| **GEOMETRIA** — radius 0 · taglio 45° su 1–2 vertici · spaziature multiple di 4 · pesi hair/base/bold | ✅ un solo vertice, in basso a destra |
| **COLORE** — tutti da tokens · accento < 10 % · tinte ≤ 3 · zero gradienti · zero glow | ✅ `--rust` assente perché nessun valore supera le soglie di §16: l'accento è semantico |
| **TIPOGRAFIA** — cinque gradini · numeri in mono · caps ≥ .10em | ✅ **verificabile per la prima volta**, vedi sotto |
| **CONTENUTO** — dati veri · etichetta + id + piede · valore mono · densità | ✅ dopo una riscrittura, vedi «densità» |
| **MOVIMENTO** — animazione solo su evento · zero ambientale | ✅ nessuna animazione: uPlot non anima per scelta dell'autore, e WinBox è montato con `no-animation` |
| **TECNOLOGIA** — testo nel DOM · numeri in uPlot | ✅ |

### 3. Lo stato vuoto — non è in §22, ma l'invariante 23 lo impone

`shots/app-vuoto.png`, **guardato**: col core spento il pannello mostra
`NESSUNA SORGENTE COLLEGATA` in `--txt-ghost` e il piede dice «in attesa del
core». Nessuno zero finto, nessun ultimo valore congelato spacciato per
attuale. Sono i tre stati di §11.9, tutti e tre verificati.

---

## I font, dopo due fasi

Bloccavano la sezione TIPOGRAFIA di §11.8 da Fase 0b. Sbloccati con
`@fontsource/*` — **OFL-1.1**, la stessa licenza che il README già dichiarava —
copiati nel repo da `npm run fonts`.

Il guardiano scritto in Fase 0b ha fatto il suo lavoro fino all'ultimo giorno:
finché mancavano, `npm run shot` usciva con codice ≠ 0 e la galleria lo
dichiarava in rosso. Non è mai stato possibile scambiare uno scatto coi font di
ripiego per una verifica riuscita.

---

## Scoperte durante l'implementazione

**`"type": "module"` rendeva Electron inavviabile.** Aggiunto in Fase 0b per gli
script, faceva trattare `app/main.js` come modulo ES, dove `require` non
esiste. Peggio: **un preload con `sandbox: true` non può essere ESM**. Gli
script sono già `.mjs` — che è ESM a prescindere — quindi il campo non serviva
a nulla ed è stato tolto, con la ragione scritta accanto in `package.json`
perché nessuno lo rimetta.

**`noheader: true` non esiste in WinBox**, e veniva ignorato in silenzio: la
testata si toglie con la classe `no-header`. Se ne è accorto il ciclo §11.7
**guardando lo screenshot**, non leggendo il codice — nel primo scatto la barra
di titolo era lì, fuori palette. Ora le classi sono tre e ognuna ha una regola:
`no-header` (§10.2), `no-animation` (§10.3), `no-shadow` (invariante 19).

**Dei backtick in un commento hanno rotto il modulo.** Il commento CSS stava
dentro un template literal e i backtick lo chiudevano. Il pannello non caricava
affatto, e `npm run shot` — che esce ≠ 0 sugli errori di console — l'ha fatto
notare subito invece di produrre uno screenshot di una pagina vuota.

**uPlot infilava `system-ui` nel pannello.** Il livello 1 dell'audit l'ha visto
su sette elementi, più un `rgba(0,0,0,.07)`. È il caso per cui i due livelli
esistono separati: `ui/vendor/` è esente dall'audit del *sorgente* — quei
letterali non sono nostri da correggere — ma **non** da quello del *valore
calcolato* dentro i nostri componenti. §11.6 regola 1 dice che i due font sono
il 40 % dell'effetto: una libreria che ne introduce un terzo lo smonta.

**La densità è fallita al primo giro.** Le tre metriche occupavano un terzo
della larghezza e i due terzi restavano vuoti — §11.8 CONTENUTO, «la densità
regge il confronto?». §11.8 dice che un solo ✗ significa riscrivere: ho
riscritto la riga e aggiunto una quarta metrica **reale**,
`ram_available_bytes`, che il core mandava già a ogni messaggio e che nessuno
usava. Nessun dato inventato per riempire.

**Il controllo dell'invariante 29 scattava sulla propria spiegazione.** Il grep
di Fase 1 leggeva le righe grezze, quindi i commenti che *spiegano* la regola —
il docstring di `paths_cli` che dice perché `$XDG_RUNTIME_DIR` non va nel
codice dell'app — la violavano. Riscritto con `tokenize`, che scarta commenti e
stringhe, e **verificato che fallisca davvero** introducendo un `import psutil`
temporaneo fuori da `platform/`. Un controllo che si autoaccusa viene allentato
al primo falso positivo, e da lì non protegge più nulla.

---

## ❌ NON VERIFICATO — e perché

**La disposizione della finestra.** Né `x: "center"` né `.move("center","center")`
centrano il pannello con questa versione di WinBox: resta in alto a sinistra.
Non ho insistito e ho rimosso la chiamata inefficace invece di lasciarla come
codice morto. Agganci, affiancamento e workspace sono **§13**, una fase a sé;
Fase 1b doveva provare che i dati arrivano, non arredare la scrivania.

**Il comportamento sotto carico prolungato.** Lo scatto cattura 12 campioni —
soglia scelta perché con uno solo la striscia è una riga piatta e proverebbe
che i dati arrivano ma non che il grafico li disegna. Il ring buffer da 120
campioni e il ridimensionamento non sono stati osservati per ore.

**Wayland nativo.** L'app gira sotto **XWayland** (`XDG_SESSION_TYPE=wayland`,
`DISPLAY=:0`), senza `--ozone-platform=wayland`. Deliberato: §2.1 cita una
regressione X11 in Electron 43 — la versione installata — legata alle input
region degli overlay, che il cambio di scope ha eliminato. Aggiungere un flag
di piattaforma su una fase che deve isolare un rischio ne avrebbe aggiunto uno.

---

## Scostamenti dalla specifica, dichiarati

| # | Cosa | Decisione |
|---|---|---|
| **R12** | I woff2 andavano procurati a mano | `@fontsource/*` da npm, OFL-1.1. Non una libreria nuova: il modo di procurare i font che §11.3 già impone |
| **R13** | Electron 43 è la versione con la regressione X11 di §2.1 | Riguarda gli overlay click-through, eliminati dal cambio di scope. Nessun flag di piattaforma |
| **R16** | `ui/index.html` non è in §21.1 | Aggiunto: la finestra ha bisogno di un documento |
| **R17** | `core/paths_cli.py` non è in §21.1 | Aggiunto: il codice dell'app non deve conoscere `$XDG_RUNTIME_DIR` (invariante 29) |
| **R18** | `ui/vendor/` non è in §21.1 | Aggiunto: la galleria è servita via HTTP da `ui/` e l'app carica da `file://`; un percorso a `node_modules` funzionerebbe in uno solo dei due, e il ciclo §11.7 giudicherebbe un rendering diverso da quello che gira |

## Riepilogo

| | |
|---|---|
| Test | **135 verdi** (erano 124) |
| Criteri §22 Fase 1b | **2 su 2 verificati**, più lo stato vuoto di §11.9 |
| Rischio ritirato | l'assunto di ADR-002 sul ponte, provato su entrambi i lati |
| Non verificato | disposizione delle finestre (§13) · carico prolungato · Wayland nativo |
| Aperto per la Fase 2 | il ciclo `fs.confirm_request`/`fs.confirm_response` con `request_id` e scadenza. Il preload oggi espone **solo ricezione**: la quarta funzione andrà aggiunta di proposito, e un test fallisce se compare senza dichiararla |
