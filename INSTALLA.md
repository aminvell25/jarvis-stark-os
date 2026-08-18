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
