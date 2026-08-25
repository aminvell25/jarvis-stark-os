# T0 misurato, e il microfono che non si può ancora accendere

**Rollback:** `711e5bc`
**Criterio ⑤:** «*papà è a casa* eseguito offline con la latenza mediana
misurata su cento frasi, non stimata».
**Esito: il corpus è misurato e registrato — e ha trovato due difetti veri. Il
microfono NON si accende: mancano quattro cose, tre delle quali sono
installazioni che non faccio senza chiederle.**

---

## 1. Le due frasi rubate

L'indicazione era precisa:

> le venti frasi conversazionali che devono dare `None` servono più delle cento
> che devono dare un comando.

Aveva ragione, e le venti che c'erano non bastavano: **nessuna di loro comincia
con un verbo di comando**. «mi sento stanco», «perché il cielo è blu» — parlano
d'altro, nessuna regola le sfiora, passavano tutte.

Il guasto che il corpus dichiara di sorvegliare è un altro:

> Il rischio non è che il parser manchi un comando — quello si nota subito. È
> che **ne rubi uno a T1** […] Quel guasto è silenzioso: JARVIS risponderebbe
> con un'azione invece che con una frase.

Venti frasi nuove che **cominciano come un comando e non lo sono**. Due
venivano rubate:

| frase | diventava | che cosa faceva |
|---|---|---|
| `cerca di capirmi` | `search_files {"query": "di capirmi"}` | frugava nel filesystem invece di rispondere |
| `chiudi un occhio stavolta` | `close_panel {"panel": "occhio"}` | chiudeva un pannello che non esiste |

### Le cause, e sono due difetti diversi

**`close_panel` accettava `\w+`, cioè qualunque parola**, mentre `open_panel`
accetta solo i nomi in `_PANNELLI`. Un'asimmetria: si poteva «chiudere»
qualsiasi cosa e «aprire» solo ciò che esiste. Adesso usano lo stesso elenco.

**`cerca di ...` in italiano vuol dire «prova a»**, non è una ricerca. Nessuno
chiede di cercare un file dicendo «cerca di X»: si dice «cerca X» o «cerca il
file X», e le due forme restano intatte — verificate.

Le altre diciotto passavano già: il parser è per il resto ben educato, e questi
due sono veri.

## 2. Il numero, adesso registrato

```
133 frasi — 90 comandi, 43 conversazionali
mediana  0,0032 ms   ·   p95  0,0070 ms   ·   max  0,0099 ms
budget §7.6: 10 ms
```

Tremila volte sotto il budget. Prima questo numero si **stampava e si perdeva**:
§22 lo elenca fra le misure della Fase 3, e una misura che vive solo
nell'output di pytest non si confronta col mese prossimo. Adesso sta in
`docs/acceptance/T0-CORPUS.json`, con l'impronta di `grammar.py` e del corpus —
le due cose che, cambiando, rendono vecchio il numero.

⚠️ **È la latenza di `parse()` su testo, e il file lo dice nel campo `misura`.**
Non è la latenza dal microfono. Confonderle sarebbe il difetto di provenienza
che §11.7 regola 5 vieta.

## 3. Il microfono: che cosa manca, misurato

| | stato |
|---|---|
| dispositivi di cattura | **ok** — due schede: `ALC257 Analog`, `acp-pdm-mach` DMIC |
| `vosk` | **ok** |
| `numpy` | ok |
| **PortAudio** | **ASSENTE** — `sounddevice` è installato e solleva `OSError: PortAudio library not found` |
| **modello Vosk it** | **ASSENTE** — `~/.local/share/jarvis-os/vosk-model-small-it-0.22` non esiste |
| `faster_whisper` | assente — è il ripiego STT locale, e senza chiave Deepgram è **l'unica** strada |
| `webrtcvad` | assente — `core/voice/pipeline.py` ha un VAD a energia proprio, quindi forse non serve |
| **`core/voice/audio_io.py`** | **0 byte** — lo strato di ingresso audio non esiste |
| `voice.enabled` | `false` |

Quindi ⑤ non è «accendere un interruttore»: sono **un modulo da scrivere e tre
installazioni**.

### Che cosa invece è già pronto

`core/voice/wake.py` e `core/voice/pipeline.py` esistono (139 e 281 righe), e le
loro interfacce prendono **byte PCM**: `PhraseWake.feed(pcm)`, `VAD.parla(pcm)`.
Il che vuol dire che la catena si può provare **senza un microfono**, appena il
modello c'è — è `audio_io.py` a mancare, non l'architettura.

## 4. Che cosa non ho fatto, e perché

**Non ho installato niente.** `CLAUDE.md`, *Non fare senza chiedere*:
«Aggiungere dipendenze non elencate.» E scaricare un modello Vosk è una
richiesta di rete verso l'esterno.

Le tre cose da decidere, con il loro peso:

1. **PortAudio** (`libportaudio2`) — pacchetto di sistema, serve `sudo`, che le
   impostazioni del progetto negano. **Deve farlo Lei.**
2. **Il modello Vosk `small-it-0.22`** — ~50 MB da `alphacephei.com`. Posso
   scaricarlo se me lo dice.
3. **`faster_whisper`** — dipendenza Python, trascina `ctranslate2` e un modello
   suo. È il ripiego STT locale, e senza chiave Deepgram diventa la strada
   principale, non il ripiego.

## 5. Una cosa che ho visto e non ho toccato

```
[warning] permessi_larghi  atteso=0600  file=~/.config/jarvis-os/settings.toml
```

Il core lo dice a ogni avvio. `settings.toml` non contiene chiavi — quelle
stanno in `secrets.toml` — ma il file dichiara le radici consentite del
filesystem, e permessi larghi su quel file sono permessi larghi su quella
decisione. Non l'ho cambiato: sono i Suoi file di configurazione fuori dal
repo, e `chmod` su di essi non è una modifica che prendo da solo.

## 6. Verifica

| | |
|---|---|
| `tests/t0_corpus.py` | **139 passed** (erano 119) |
| frasi conversazionali | 43, erano 23 |
| le due rubate | adesso danno `None`; i comandi veri reggono |
| `uv run pytest -q` | **673 passed** |

## 7. Dichiarato aperto

- **Il criterio ⑤ non è soddisfatto**: «*papà è a casa* eseguito offline» ha
  bisogno del microfono, e il microfono ha bisogno di §4. Il documento lo dice
  invece di dare per verde una latenza misurata su testo.
- **`core/voice/audio_io.py` è vuoto.** È il pezzo da scrivere, e si scrive
  bene solo contro un PortAudio che esiste: scriverlo prima vorrebbe dire
  provarlo mai.
- **Le venti frasi nuove sono le mie**, non una lista di riferimento. Coprono i
  verbi delle regole esistenti — cerca, trova, apri, chiudi, mostra, vai, alza,
  abbassa, spegni, accendi, nascondi — e i tre sostantivi che compaiono nei
  pattern: file, workspace, volume. Un verbo nuovo in `grammar.py` vuole una
  frase nuova qui.
