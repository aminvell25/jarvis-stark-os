# JARVIS OS — Regole di progetto

## Cos'è
Un'applicazione desktop a schermo intero: un ambiente cognitivo dentro il
quale JARVIS vive, parla, mostra dati, apre il web, gestisce cartelle reali
e genera modelli 3D. Fuori dalla sua finestra non tocca nulla.
Uso strettamente personale. Non sarà distribuito.

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

## Copyright su codice di terzi

30. **Non copiare codice da repository di terzi** studiati come riferimento
    (vedi `docs/ANALISI-REPO-E-TECNOLOGIE.md`). Le idee architetturali si
    reimplementano da zero; il codice altrui, anche se pubblico su GitHub,
    resta coperto da copyright salvo licenza permissiva esplicita e
    verificata. Due dei tre repo analizzati hanno copyright pieno.

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
4. il commit e' fatto

Se non puoi verificare un criterio, lo DICHIARI. Non lo dai per buono.
