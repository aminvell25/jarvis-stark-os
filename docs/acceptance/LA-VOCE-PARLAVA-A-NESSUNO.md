# «Papà è a casa» non faceva niente — e JARVIS l'aveva sentita

**Rollback:** `2cfa045`
**Sintomo riferito:** «Ho detto *papà è a casa* e non è successo niente».
**Esito: il microfono, il wake e il riconoscimento funzionavano. Il log lo
dimostra. L'azione veniva trasmessa su un topic che NESSUNO ascolta — e l'avevo
scritto io in questa stessa sessione. Corretto. Resta una seconda causa, di
progetto, che dichiaro senza deciderla.**

---

## 1. Quello che il log diceva, e che contraddice il sintomo

```
17:38:13  wake_trigger    azione=scene:welcome_home  frase='papa e a casa'  latenza_ms=7.72
17:38:13  azione_diretta  azione=scene:welcome_home  latenza_ms=7.72
17:38:15  wake_trigger    azione=scene:welcome_home  frase='papa e a casa'  latenza_ms=13.04
```

Tredici trigger in tutto: `jarvis` sette volte (5,9–13,3 ms) e `papà è a casa`
tre. E uno di questi è arrivato fino in fondo:

```
17:38:31  wake_trigger  azione=listen frase=jarvis
17:38:36  t1_primo_token  ms=1674
17:38:37  primo_suono_ms  ms=2250
17:38:50  t1_turno_completo  totale_ms=16097
```

**Wake, STT, T1 e voce hanno funzionato tutti**, per la prima volta, con la Sua
voce vera. La correzione del turno precedente era giusta.

## 2. La prima causa: un topic che non esiste

`_voce_su_azione` trasmetteva

```python
{"topic": "ui.action", "azione": "scene:welcome_home", "args": {}}
```

e **nessuno ascolta `ui.action`.** Il renderer si iscrive a **`ui.intent`** con
`{intento, args}` (`ui/src/desk/scrivania.js:800`), e `applicaScena` legge
`args.nome`: la stringa `scene:welcome_home` va **spezzata**, non passata
intera.

**L'ho scritto io in questa sessione**, componendo il grado voce. E il difetto
è peggiore di uno sbaglio di nome: `esegui_t0()`, venti righe più in su,
**produceva già** il messaggio giusto, con due destinazioni — `INTENTI_UI`
verso il socket, e `registry.invoke()` per gli intenti che nominano un tool,
cioè con la conferma umana dove serve (invariante 3). Trasmettendo a mano ho
saltato entrambe: **un intento vocale che nominava un tool non lo invocava
affatto.**

È la stessa specie di §13, del `Watcher` delle news e di `_gradi()` che
componeva solo T1: due pezzi scritti, provati, e mai congiunti. Con
l'aggravante che qui il proprietario della strada esisteva già e io ne ho
costruita una seconda.

Adesso `_voce_su_azione` traduce e instrada:

```
scene:welcome_home  ->  Intent(tool="scene", args={"nome": "welcome_home"})  ->  esegui_t0()
open_panel + args   ->  Intent(tool="open_panel", args={...})               ->  esegui_t0()
```

Nessun elenco di prefissi ammessi: l'allowlist resta **una sola**, quella di
`esegui_t0()`, che rifiuta e logga ciò che non è né in `INTENTI_UI` né nel
registry. E ciò che non arriva da nessuna parte adesso **lo dice**:
`voce_senza_destinazione`.

## 3. La seconda causa, e questa non la decido io

Le frasi in `settings.toml` nominano `scene:welcome_home` e `scene:goodnight`.
Nel renderer, `moduli.js`, le scene dichiarate sono **una sola**:

```
export const SCENE = [ { nome: "avvio", … } ]
```

`applicaScena` con un nome che non esiste ritorna `null` e non fa niente, **per
progetto** — il commento lo dice: «JARVIS richiama scene **dichiarate**, non ne
inventa». Quindi anche con l'instradamento corretto e la scrivania aperta,
`welcome_home` non applica niente.

Tre strade, e sono Sue:

1. **Puntare le frasi su `avvio`**, l'unica che esiste. Una riga in
   `settings.toml`, zero codice, e da subito si vede qualcosa.
2. **Dichiarare le due scene** in `moduli.js`. È progettarle — quali pannelli,
   in quali celle — e passa dal ciclo §11.7 con la checklist §11.8.
3. **Lasciarle così** e usarle come promemoria di ciò che manca.

Non ho scelto da solo: inventare la composizione di «bentornato a casa» e
«buonanotte» è una decisione di design, non una riparazione.

## 4. Una terza cosa, minore ma dello stesso genere

`mute` — la frase `jarvis silenzio` — non è né in `INTENTI_UI` né nel registry.
Prima non arrivava da nessuna parte **in silenzio**; adesso c'è
`voce_senza_destinazione` a dirlo. Non l'ho implementato: che cosa debba fare
esattamente («zittisci la frase in corso» oppure «non parlare più finché non
te lo dico») è una decisione, non un dettaglio.

## 5. E la scrivania non era aperta

Nessun processo Electron in esecuzione, e nessun `client_connesso` nel log al
momento delle azioni. Anche col topic giusto, il messaggio sarebbe andato a
zero destinatari. Il comando è `npm run app`.

## 6. Le prove

`tests/test_voce_arriva_alla_scrivania.py`, **6** asserzioni:

| | |
|---|---|
| una scena diventa un **intento**, col nome negli argomenti | il difetto alla lettera |
| il topic morto `ui.action` non si usa più | |
| gli **argomenti** di T0 arrivano interi | `open_panel` senza `panel` è una categoria, non un comando |
| un'azione senza destinazione **si dice** | `mute` |
| un intento che nomina un **tool** lo invoca | la metà che il socket a mano saltava del tutto |
| il compito è **referenziato** | `asyncio` tiene i task per riferimento debole |

**Ritirate:**

| correzione ritirata | esito |
|---|---|
| il topic morto `ui.action` | **6** rossi |
| la stringa `scene:…` non più spezzata | 2 rossi |
| il riferimento al compito | 1 rosso |
| la riga che dice l'azione senza destinazione | 1 rosso |

| | |
|---|---|
| `uv run pytest -q` | **740 passed** (erano 734) |
| sorgenti UI toccate | **nessuna** |

## 7. Dichiarato aperto

1. **Le due scene non esistono** (§3). Decisione Sua.
2. **`mute` non ha destinazione** (§4). Decisione Sua.
3. **Non ho potuto verificare dal vivo che l'intento arrivi allo schermo**,
   perché servono insieme la scrivania aperta e una frase detta da Lei. Le
   prove coprono la forma del messaggio; il tragitto fino al pixel no.
4. **Il riconoscimento della Sua voce è invece PROVATO**, e non da me: dai
   tredici trigger nel log di questa sessione. È il punto che tre documenti
   dichiaravano aperto, e si può chiudere.
