# Come usare questo pacchetto

## 1. Crea il repo

```bash
mkdir ~/jarvis-os && cd ~/jarvis-os
git init
```

## 2. Copia tutto il contenuto di questa cartella nella root del repo

```bash
cp -r /percorso/jarvis-os-bootstrap/. ~/jarvis-os/
```

Ottieni:

```
jarvis-os/
├── CLAUDE.md                       ← la costituzione, letta a ogni sessione
├── .gitignore
├── .claude/
│   ├── settings.json               ← permessi
│   └── agents/{forge,argus,edith,veronica}.md
├── config/
│   ├── settings.toml               ← da copiare in ~/.config/jarvis-os/
│   ├── secrets.toml.example        ← da copiare e riempire
│   └── voice-persona.md            ← da copiare in ~/.config/jarvis-os/
├── docs/
│   ├── SPEC.md                     ← la specifica rev 5.0
│   └── design-reference/
│       ├── README.md               ← mappa delle immagini
│       ├── famiglia-a/  (12 img)   ← DA SEGUIRE
│       └── famiglia-b/  (4 img)    ← NON SEGUIRE
├── PRIMO-PROMPT.md                 ← il prompt da incollare
└── INSTALLA.md                     ← questo file
```

## 3. Configurazione utente

```bash
mkdir -p ~/.config/jarvis-os ~/.local/share/jarvis-os/voice-cwd ~/JARVIS

cp config/settings.toml     ~/.config/jarvis-os/
cp config/voice-persona.md  ~/.config/jarvis-os/
cp config/secrets.toml.example ~/.config/jarvis-os/secrets.toml

chmod 600 ~/.config/jarvis-os/settings.toml ~/.config/jarvis-os/secrets.toml
$EDITOR ~/.config/jarvis-os/secrets.toml      # inserire la chiave Deepgram
```

La directory `~/.local/share/jarvis-os/voice-cwd` deve restare **vuota**:
e' da li' che parte il processo T1, e qualunque `CLAUDE.md` o `.claude/`
al suo interno verrebbe caricato a ogni frase (SPEC §5.2).

## 4. Prerequisiti

```bash
claude --version      # >= 2.1.205
node --version        # >= 20
python3 --version     # 3.12
uv --version
claude auth status    # deve dire loggedIn: true
fc-list | grep -i "Barlow Semi Condensed"
fc-list | grep -i "IBM Plex Mono"
```

Modello Vosk italiano piccolo da alphacephei.com/vosk/models in
`~/.local/share/jarvis-os/` (serve dalla Fase 3, non subito).

## 5. Primo commit, poi si parte

```bash
git add -A && git commit -m "chore: costituzione di progetto"
claude
```

Poi segua `PRIMO-PROMPT.md`.

## 6. Avvio come servizio (Fase 9)

Il core e' un **servizio utente** di systemd: `systemctl --user`, mai di
sistema. Tocca i Suoi file, apre il Suo microfono e parla col Suo abbonamento —
un servizio di sistema girerebbe con privilegi che non gli servono e senza
`$XDG_RUNTIME_DIR`, che e' dove vive il socket (invariante 7).

```bash
packaging/installa.sh              # copia la unit, ricarica systemd, NON avvia
systemctl --user start jarvis-core # prova adesso
journalctl --user -u jarvis-core -f
uv run python -m core.doctor       # la diagnosi di §16.1b
```

L'installatore **non abilita e non avvia niente**: un servizio che parte al
login e' una modifica persistente della macchina, ed e' una decisione Sua.
Quando lo vuole:

```bash
systemctl --user enable --now jarvis-core
```

Per togliere tutto: `packaging/disinstalla.sh` — che lascia intatte le
impostazioni e la memoria, di proposito.

### Cosa parte, e cosa no

L'avvio e' **a gradi**, e ogni grado e' un interruttore in `settings.toml`:

| Grado | Interruttore | Cosa accende |
|---|---|---|
| sempre | — | impostazioni, allowlist, GPU, socket, tool su file |
| voce | `voice.enabled` | **microfono**, wake Vosk, STT/TTS, T1 persistente |
| news | `news.enabled` | collector RSS, gate, budget |
| ARGUS | `vision.enabled` | **telecamera**, su richiesta di una gesture |

**Voce e ARGUS partono spente**, e non e' timidezza: un servizio che accende il
microfono perche' e' stato installato sarebbe la peggiore sorpresa di tutto il
progetto. Si accendono scrivendolo nel file, e allora e' una decisione scritta.

### Quando la sessione di Claude scade

Succedera' (§5.6). Il core lo riconosce, lo dice a voce, lo scrive su
`agent.advisory` e **si ferma con il codice 41** — che la unit conosce e sul
quale non riavvia. Senza quello, `Restart=always` lo rilancerebbe all'infinito
contro un token che non torna valido.

```bash
claude          # e poi /login
systemctl --user restart jarvis-core
```
