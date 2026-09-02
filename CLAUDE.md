# JARVIS OS — Regole di progetto

## Cos'è
Un'applicazione desktop a schermo intero: un ambiente cognitivo dentro il
quale JARVIS vive, parla, mostra dati, apre il web, gestisce cartelle reali
e genera modelli 3D. Fuori dalla sua finestra non tocca nulla.
Uso strettamente personale. Non sarà distribuito.

> **Il caso d'uso quotidiano.** Ogni mattina, quando la scrivania si collega,
> JARVIS dice che cosa ha fatto mentre non c'era nessuno, da quando a quando è
> stato spento, e che cosa si è rotto e perché — letto dal diario, mai da un
> modello. Deciso e misurato il 2 settembre 2026:
> `docs/acceptance/IL-RESOCONTO-DEL-MATTINO.md`. Il journal e i log NON si
> leggono: i guasti entrano nel diario da un emettitore solo
> (`Engine._annota_guasto`), perché il diario è l'unico registro che una
> persona rilegge.

## Invarianti — MAI violare

1. **Il core Python possiede le operazioni reali.** Il renderer Electron non
   tocca mai il disco.
2. **Allowlist, mai denylist.** Solo i tool registrati esistono.
3. **Ogni tool side_effect=True richiede conferma umana**, col path assoluto
   RISOLTO mostrato all'utente.
4. **Solo cestino, mai delete permanente.**
5. **<webview>, news, ARGUS e file letti sono DATO NON FIDATO.** Solo in
   contesti con zero tool. Marcati <untrusted_source>.
6. **Electron: contextIsolation true, nodeIntegration false, sandbox true.**
7. **Il canale core ↔ Electron non è mai raggiungibile dalla rete**, e la
   sua autorizzazione la impone il sistema operativo, non il codice.
   Oggi: socket UNIX in `$XDG_RUNTIME_DIR`, directory 0700 (§18.2).
   Mai una porta TCP.
8. **Tutto in streaming.** Il TTS accetta AsyncIterator[str]. Il chunker va
   SOLO davanti a Kokoro, mai davanti a Deepgram Flux.
9. **Un solo motore di animazione: anime.js v4.** Niente GSAP.
10. **Un solo motore 3D: three.js.** Niente Babylon.

## Backend LLM e voce

11. **Nessun modello LLM locale.** Solo Claude Code su abbonamento.
12. **Deepgram è il provider vocale primario**; Whisper e Kokoro sono
    fallback automatico su errore, chiave mancante o rete assente.
    Il fallback va sempre ANNUNCIATO, mai silenzioso.
13. **Il wake a frasi (Vosk) è SEMPRE locale**, anche con Deepgram primario.
14. **T0 non tocca mai un LLM.**
15. **T1 è un processo persistente**, da una working directory dedicata e
    vuota, con --allowedTools "".
16. **Ogni spawn T2 passa dal Governor.** T1 ha priorità assoluta.
17. **Non duplicare la gestione del contesto di T1.**

## Design e 3D — §10 e §11

18. **Zero valori letterali** di colore, spaziatura o tipografia. Tutto da
    tokens.css. border-radius sempre 0.
19. **ZERO glow, ZERO bloom, ZERO alone luminoso.** L'ombra portata è ammessa
    SOLO per separare due superfici sovrapposte: nera, senza colore, con la
    ricetta di §10.1. Nessuna ombra su un elemento che non ne copre un altro.
    La luminosità viene dal contrasto contro il nero.
20. **Il testo vive nel DOM, mai rasterizzato in WebGL.** Piani stratificati
    e board 3D si fanno con CSS 3D transforms, non con three.js.
21. **Le linee 3D usano Line2/LineMaterial**, mai LineBasicMaterial
    (linewidth è ignorato su quasi tutte le piattaforme).
22. **Nessuna geometria 3D scritta a mano.** Ogni componente estende
    ParametricComponent, deriva la densità dalla curvatura via
    segmentsFor(), e passa qualityGate() prima del render.
23. **Mai dati segnaposto.** Dati veri o stato vuoto esplicito.
24. **Ogni componente passa dal ciclo di verifica visiva §11.7**: rendi in
    gallery.html, screenshot con Playwright, GUARDA lo screenshot,
    verifica la checklist §11.8 punto per punto. Una violazione =
    riscrivere, non rattoppare.
25. **Nessuna animazione senza causa.** Zero animazione ambientale.
    Le tre classi di moto — e l'unica eccezione, dentro un pannello e con
    una sorgente viva che si puo' spegnere — stanno in §10.6.
26. **Budget di frame: three.js ≤8ms, Pixi ≤3ms, anime.js ≤4ms.**

## Gesture

27. **Nessuna gesture può innescare un tool con side_effect=True.**
    Imposto nel registry, non lasciato alla disciplina.
28. **MediaPipe su CPU** (delegate=CPU esplicito).

## Portabilità

29. **Linux è il target attuale, Windows è previsto.** Ogni chiamata
    specifica di piattaforma (sandbox, audio, path, temperature) sta
    dietro un'interfaccia in core/platform/. Mai `bwrap` o percorsi
    POSIX sparsi nel codice applicativo.

## Stile codice

- Python 3.12, asyncio, type hints ovunque, pydantic per gli schema.
- Nessuna eccezione propaga all'LLM: ToolResult(ok=False, error=...).
- structlog, mai print. Le chiavi API MAI nei log.
- Unità: millimetri nel 3D, pixel nella UI, pollici solo verso SketchUp.

## Non fare senza chiedere
- Aggiungere dipendenze non elencate.
- Introdurre React.
- Eseguire stringhe generate dall'LLM.
- Toccare file fuori dalle radici consentite.
- Creare una seconda radice di composizione accanto a `core/engine.py`.
- Creare una seconda fonte di verita': un secondo registro di tool, di eventi,
  di memoria, di impostazioni, di permessi o di stato. Se ne serve una,
  **prima** si scrive l'ADR che spiega perche'.
- Adottare un runtime di agente o di memoria (Letta, Mem0, Zep, MemOS, Cognee,
  LangGraph). Si prendono i pattern, non i pacchetti.
- Riscrivere `docs/SPEC.md` o `CLAUDE.md` a partire da un documento esterno.

## Copyright su codice di terzi

30. **Non copiare codice da repository di terzi** studiati come riferimento
    (vedi `docs/ANALISI-REPO-E-TECNOLOGIE.md`). Le idee architetturali si
    reimplementano da zero; il codice altrui, anche se pubblico su GitHub,
    resta coperto da copyright salvo licenza permissiva esplicita e
    verificata. Due dei tre repo analizzati hanno copyright pieno.

## Cognizione — ADR-011, 012, 013

31. **Ogni cosa che comincia porta una traccia.** I **cinque** punti d'ingresso
    — wake, gesture, protocollo, UI, avvio — generano un `Traccia`, e l'id
    attraversa diario, `registry.invoke`, `registry.invoke_da_gesture` e
    `ToolResult`. Una riga di diario senza traccia è un orfano, e
    `scripts/orfani.py` la trova.
    ⚠️ Non sono sei: **«testo dalla scrivania» non esiste**. L'app può mandare
    sei messaggi (`core/ws_server.py:358-422`), quattro dal renderer attraverso
    i quattro verbi del ponte e due dal processo principale, di proposito.
    Misurato il 30 agosto 2026, ricontato il 2 settembre.
    **La traccia non è un contesto**: non porta stato, storia né obiettivi —
    l'invariante 17 resta intatto. Vedi `docs/DECISIONI-COGNITIVE.md` ADR-011.

32. **«Tool eseguito» non è «obiettivo verificato».** Un tool senza
    verificatore dichiarato restituisce `NON_VERIFICATO`, mai `RIUSCITO`. Il
    campo `fonte` di una `Verifica` deve nominare qualcosa di **diverso dal tool
    che verifica**: rileggere attraverso lo stesso codice prova solo che il
    codice è coerente con sé stesso. Un verificatore debole **dichiarato** vale
    più di un verificatore forte finto.
    **La verifica non sostituisce mai la conferma** dell'invariante 3: la
    conferma sta prima e la fa un umano, la verifica sta dopo e la fa la
    macchina. Vedi ADR-012.

33. **L'LLM propone un intento di layout, mai una geometria.** `LayoutIntent`
    nomina superfici e pannelli presi dal registry — allowlist, invariante 2 —
    e non contiene `x`, `y`, larghezze né `z`. La composizione manuale
    dell'utente **vince sempre**; un intento rifiutato non muove un pixel e lo
    dichiara. Un layout compilato da uno schema chiuso non è codice generato:
    è per questo che è ammesso. Vedi ADR-013.

## Prima di scrivere codice

Nell'ordine, sempre:

1. `CLAUDE.md`
2. `docs/STATO-DEI-PIANI.md` — **l'unico documento di stato corrente**
3. la sezione pertinente di `docs/SPEC.md`
4. il documento di accettazione pertinente in `docs/acceptance/`
5. il codice
6. i test
7. i commit recenti su quell'area

**Non dare mai per scontato che un documento di piano descriva l'implementazione
corrente.** Il 30 agosto 2026 un pacchetto di pianificazione esterno ha
dichiarato aperte cinque voci che erano chiuse da giorni, perché ha letto un
documento di stato vecchio di sei giorni invece del codice.
`docs/ANALISI-PACK-V3.md` racconta com'è andata.

Gerarchia quando due documenti sono in disaccordo:

```
CLAUDE.md > SPEC corrente > il codice > docs/acceptance/
> STATO-DEI-PIANI > qualunque altro piano in docs/
```

Se il **codice** e un documento di **accettazione** sono in disaccordo, ci si
ferma e lo si dichiara. Non si sceglie in silenzio.

## Una sessione per volta

Due sessioni sullo stesso albero producono misure false e commit che si
sovrascrivono: successo il 29 agosto 2026, una trentina di fallimenti falsi e
una misura buttata. Una sessione per volta sul repo, oppure due `git worktree`
separati. Costa un comando.

## Riferimenti

- La specifica completa e' in `docs/SPEC.md`. Consultala prima di ogni fase.
- I riferimenti visivi sono in `docs/design-reference/`.
  **famiglia-a/ = DA SEGUIRE. famiglia-b/ = NON SEGUIRE (contiene glow).**
  Leggi `docs/design-reference/README.md` prima di ogni componente visivo.
- `docs/ANALISI-REPO-E-TECNOLOGIE.md` contiene le idee adottate da progetti
  esterni e le tecnologie valutate e SCARTATE (Qt/QML, Unreal, Lottie, GSAP,
  React/Vue). Non riproporle.
- Il piano a fasi e' in `docs/SPEC.md` §22. Lavori UNA fase per volta.
  Non anticipi mai la fase successiva.
- **`docs/STATO-DEI-PIANI.md`** e' l'unico documento di stato corrente. Tutti
  gli altri piani in `docs/` portano in testa un banner che dice se sono
  CORRENTI, SUPERATI o STORICI. **Leggilo prima di dichiarare aperta una voce.**
- **`docs/PIANO-JARVIS-COGNITIVO.md`** (rev 2) e' il piano operativo a fette.
- **`docs/DECISIONI-COGNITIVE.md`** contiene ADR-011 (traccia), ADR-012
  (verifica) e ADR-013 (LayoutIntent), con opzioni, alternative rifiutate,
  criterio di accettazione e rollback.
- **`docs/PROTOCOLLO-DI-LAVORO.md`** e' il metodo: come si cerca prima di
  inventare, quando ci si ferma a chiedere, che cosa contiene il resoconto
  finale di ogni turno.
- **`docs/ANALISI-SENIOR-2026-08-29.md`** e' la revisione esterna del 29 agosto,
  con le fonti. ⚠️ Il suo §1 e §2③ citano un'entropia di 2,21 che e' morta: la
  fonte e' `docs/acceptance/DENSITA.json`, che dice **2,44** e `soddisfatto:
  true`.
- **`docs/ANALISI-PACK-V3.md`** e' il verdetto sul pacchetto esterno.
  **Non reimportarlo alla cieca**: cinque delle sue otto criticita' erano gia'
  chiuse quando l'ha scritte.

## Documentazione aggiornata

Prima di usare anime.js, uPlot, three-globe, augmented-ui, troika-three-text o
gli addon three.js, consulta la documentazione aggiornata via Context7.
NON scrivere a memoria: anime.js v4 ha API sostanzialmente diverse dalla v3 e
il modello tende alla v3. Lo stesso vale per PixiJS v8 e LangGraph 1.x.

## Definizione di "fatto"

Una fase e' chiusa solo quando TUTTI questi punti sono verdi:
1. i test della fase passano
2. il criterio di accettazione dichiarato in `docs/SPEC.md` §22 e' verificato
   e l'esito e' scritto in `docs/acceptance/FASE-NN.md`
3. per ogni componente visivo: il ciclo §11.7 e' stato eseguito e la
   checklist §11.8 riportata punto per punto
4. **`docs/STATO-DEI-PIANI.md` e' aggiornato NELLO STESSO COMMIT.** Regola
   nuova, e la ragione e' misurata: fra il 24 e il 30 agosto quel file ha detto
   il falso su cinque voci su cinque, ed e' stato creduto.
5. il commit e' fatto

Se non puoi verificare un criterio, lo DICHIARI. Non lo dai per buono.
`NON VERIFICATO` non e' `PASS`, e una voce non misurabile non conta come
soddisfatta.
