# Fase 6 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 6
**Test**: 248 verdi (erano 223) + 185 negli eval · **Precedente**: `FASE-05.md`

È la fase in cui entra in casa **contenuto di qualcun altro**. Fino a ieri il
renderer disegnava solo dati che venivano dal core; da oggi ospita una
`<webview>` che può contenere testo scritto apposta per l'agente.

---

## I criteri di §22

### 1. «*apri YouTube e metti synthwave* funziona» — ⚠️ VERIFICATO A METÀ, E LA METÀ È DICHIARATA

La catena intera, con la frase del criterio parola per parola:

```
1. T0      youtube_search {'query': 'synthwave'}          ← nessun LLM
2. tool    ok=True  modo=ricerca_aperta
3. url     https://www.youtube.com/results?search_query=synthwave
4. annuncio «Senza chiave YouTube Data API non posso far partire il video: apro la ricerca.»
5. sul bus web.open → il pannello browser carica l'URL
```

**Cosa funziona**: la frase diventa un intento in meno di un millisecondo, il
tool decide, il messaggio arriva al pannello, la pagina si apre.

**Cosa non ho potuto provare**: la riproduzione vera. Richiede la YouTube Data
API v3, e su questa macchina non esiste nemmeno `settings.toml` — nessuna
chiave. Il ripiego è **annunciato**, come il ripiego vocale di §7.4: mai un
silenzio, mai fingere che sia andata come chiesto.

La strada con chiave è scritta e verificata contro un finto della Data API
(`tests/test_web.py`), compreso il caso «chiave presente ma rete muta». La
chiamata di rete vera resta **non provata**.

### 2. «La board 3D contiene testo selezionabile e una `<webview>` viva» — ✅ VERIFICATO nella finestra vera

```bash
npm run verifica
```

```json
{
 "webviewViva": true,
 "webviewSrc": "https://www.youtube-nocookie.com/embed/videoseries?list=PL",
 "caratteriSelezionati": 140,
 "campione": "Ogni criterio e' riportato con l'esito e con come e' stato v"
}
```

Sono due cose e le ho verificate separatamente. La webview ha un
`webContentsId` reale e ha caricato un URL remoto **mentre la carta è ruotata
nello spazio**. Il testo si seleziona davvero — non «è nel DOM», si seleziona,
che è precisamente ciò che rasterizzarlo in WebGL avrebbe tolto.

È la prova che la scelta di §11.4 era quella giusta: in three.js nessuna delle
due cose sarebbe stata possibile.

### 3. «Il renderer resta senza accesso al filesystem» — ✅ VERIFICATO

Nella stessa finestra, dal renderer:

| | |
|---|---|
| `typeof require` | `undefined` |
| `typeof process` | `undefined` |
| `typeof module` | `undefined` |
| `Object.keys(window.jarvis)` | `["confirm", "onMessage", "onStatus", "status"]` |

**Il preload è rimasto a quattro funzioni**, ed è un risultato, non un caso:
ho guardato cosa serviva davvero e nulla di questa fase passa di lì. La
cattura di ARGUS la fa il processo principale; il controllo di YouTube sono
parametri di URL; e ciò che c'è nei pannelli il core lo sa già.

### 4. Injection (§22, tabella eval) — ✅ VERIFICATO, con un limite dichiarato

`tests/eval_injection.py`, 39 casi su sei famiglie di attacco.

**Cosa NON prova**: che un LLM ignori un'istruzione iniettata. Non è
dimostrabile con un test, e progettare come se lo fosse è l'errore di fondo.

**Cosa prova**: che l'istruzione non abbia **niente da azionare**.

---

## Le tre barriere, e perché sono strutturali

### `Untrusted` non è una stringa

Ricordarsi di marcare il contenuto a ogni chiamata è il modo in cui queste
regole muoiono. Qui la regola è un **tipo**, con tre proprietà:

1. **`__str__` solleva.** Una f-string scritta di fretta fra sei mesi non
   compila un prompt: fallisce. L'unica via è `avvolto()`, che marca.
2. **`__repr__` non mostra il contenuto.** Log, traceback e `print()` di debug
   vedono origine e lunghezza. Il testo di una pagina ostile non finisce nei
   registri, dove qualcuno potrebbe rileggerlo fuori dalla busta.
3. **La busta non si chiude dall'interno.** Un contenuto che contenesse
   `</untrusted_source>` uscirebbe dalla marcatura e il resto sembrerebbe
   fidato: è l'attacco più ovvio contro questo schema, ed è neutralizzato.

### Lo spawn con tool RIFIUTA

`ClaudeT2.componi()` solleva se riceve un `Untrusted` e `--allowedTools` non è
vuota. Fail-closed come il registry di Fase 1: chi domani aggiungerà un
percorso nuovo troverà un'eccezione al primo giro, non un varco al centesimo.
Basta **un** tool a chiudere la porta.

### Il parser T0 rifiuta ciò che non è una stringa

L'anello che quasi mi sfuggiva. Il parser trasforma testo in **azioni**: una
pagina che contenesse *«apri il pannello file»* — un comando T0 perfettamente
valido — ne uscirebbe come un intento vero, **senza passare da nessun LLM**.
È l'ultimo dei sei carichi del corpus, ed è il più insidioso perché non
assomiglia a un attacco.

Come stringa produce un intento; come `Untrusted`, `None`.

---

## Scostamenti dalla specifica, dichiarati

### ⚠️ `webviewTag: true`, e perché non `WebContentsView`

`WebContentsView` è l'alternativa moderna e sarebbe la scelta ovvia. **Non è
utilizzabile qui**: è una vista nativa sovrapposta alla finestra, non un
elemento del DOM, e non può stare dentro un piano ruotato da una
`transform: rotateY()`. Il criterio 2 chiede esattamente quello.

La difesa vera non è l'attributo: è `will-attach-webview`, che cancella
`preload` e `nodeIntegration` **prima** che la webview nasca. Un renderer
compromesso che scrivesse `<webview nodeintegration>` otterrebbe una webview
normale. Più `setWindowOpenHandler` che nega ogni finestra nuova, e
`will-navigate` che impedisce al renderer di sostituirsi con una pagina remota
— che erediterebbe il preload.

### ⚠️ YouTube senza lo script di terzi

§6.3 dice di usare l'IFrame Player API e non il DOM di youtube.com. Il
contratto di quell'API sono i **parametri dell'URL di embed**, e li uso.
Caricare invece il loader `youtube.com/iframe_api` avrebbe richiesto
`script-src https://www.youtube.com` nel CSP: script di terzi nel documento
che ospita il preload. Non vale il prezzo, e non serve.

Non uso `listType: "search"`, che YouTube ha deprecato nel 2020.

### ⚠️ `core/tools/web.py` e `core/vision/` non sono in §21.1 con questo contenuto

Due tool nuovi — `open_web` e `youtube_search` — entrambi `side_effect=False`:
aprire una pagina non tocca il disco. Lo schema è validato con
un'**allowlist** (solo `https`), non con un elenco di schemi vietati che
sarebbe destinato a essere incompleto.

### ⚠️ I piani stratificati mostrano documenti, non immagini

§11.4 dice «documenti e immagini». Le immagini di riferimento stanno in
`docs/`, fuori dalla radice che il server della galleria serve — e copiarle
dentro `ui/` vorrebbe dire duplicare 13 MB nel renderer. I piani mostrano i
sette documenti di accettazione veri, col testo selezionabile. Le immagini
arriveranno quando ci sarà una sorgente di immagini dentro il perimetro del
renderer.

### ⚠️ Il contratto in ingresso passa da uno a due messaggi

`fs.confirm_response` (§6.2) e `argus.capture_response` (§12), entrambi
pydantic con `extra="forbid"`. È l'unica superficie che si allarga in questa
fase, e `tests/test_ws_contract.py` ora sorveglia la proprietà giusta: **sono
entrambi RISPOSTE**, ognuna cita l'`id` di una domanda che il core ha già
posto. Il giorno in cui quell'elenco conterrà un messaggio senza `id`, sarà una
richiesta, e il ponte avrà smesso di essere un ponte.

---

## Quello che ha trovato il ciclo §11.7

**I piani erano una pila illeggibile.** Sette piani scartati di 26 px, col
testo di quelli dietro che attraversava quelli davanti. Riscritti a giostra: il
documento a fuoco è sempre il primo, gli altri arretrano in diagonale, e oltre
il quinto spariscono.

**La ricetta del vetro copiata a mano.** Avevo scritto
`rgba(14, 19, 21, 0.72)` nei piani: quel letterale è lecito **solo** dentro
`tokens.css`, che è la sorgente. L'ha visto l'audit al primo scatto.

**Un'emoji nel testo delle carte.** Viene dai documenti veri, ed è legittima
lì; ma è un glifo a colori, e in un'interfaccia monocroma rompe la palette
**senza che l'audit la veda** — non è un colore CSS, è un font.

**La carta viva usciva dal palco.** Contiene un riquadro e non tre righe: è più
alta delle altre e andava collocata più in su.

---

## ❌ NON VERIFICATO

1. **La riproduzione YouTube vera.** Serve una chiave Data API v3. Il percorso
   del codice è provato contro un finto; la chiamata di rete no.
2. **L'OCR di ARGUS.** Tesseract non è installato su questa macchina e non
   posso installarlo — `sudo` è negato dalle regole del progetto. La strada
   dello stato (§12, «zero OCR, zero latenza») è verificata; quella dell'OCR
   degrada **annunciata** e i suoi test girano contro un OCR finto.
   ```bash
   sudo apt install tesseract-ocr tesseract-ocr-ita
   ```
3. **La cattura `capturePage()` di ARGUS end-to-end.** Il giro completo —
   core chiede, ponte cattura, core riceve — è scritto e i due capi sono
   provati separatamente, ma non l'ho fatto girare per intero: senza OCR non
   avrebbe prodotto nulla di leggibile.
4. **Il comportamento con più webview aperte insieme.** Ne ho provata una per
   pannello. Il budget di frame regge (16,7 ms, invariato), ma con quattro
   pagine vive il numero è un altro.
5. **La persistenza della sessione `persist:jarvis`** fra un avvio e l'altro.

---

## Riepilogo

| | |
|---|---|
| Test | **248 verdi** (erano 223) + **185** negli eval |
| Casi di injection | 39, su sei famiglie di attacco |
| Superficie del preload | **invariata**: quattro funzioni |
| Contratto in ingresso | 1 → 2 messaggi, entrambi risposte con `id` |
| Componenti visivi nuovi | 3, tutti col ciclo §11.7 |
| Budget di frame | **16,7 ms**, invariato con la webview viva |
| Criteri di §22 | 3 verificati, 1 a metà e dichiarato |
