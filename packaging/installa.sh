#!/usr/bin/env bash
# Installa le unit systemd UTENTE di JARVIS OS — §22 Fase 9.
#
# Copia le unit e ricarica systemd. **Non abilita e non avvia niente**: un
# servizio che parte al login e' una modifica persistente della macchina, ed e'
# una decisione di chi la usa, non dell'installatore. Il comando per farlo lo
# stampa alla fine.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

echo "JARVIS OS — installazione delle unit utente"
echo "  repo:        $RADICE"
echo "  destinazione: $DEST"
echo

# La unit ha WorkingDirectory=%h/progetti/jarvis-stark-os. Se il repo sta
# altrove, la si adatta invece di far fallire l'avvio con un messaggio oscuro.
ATTESA="$HOME/progetti/jarvis-stark-os"
mkdir -p "$DEST"
if [[ "$RADICE" != "$ATTESA" ]]; then
  echo "! il repo non e' in $ATTESA: adatto WorkingDirectory"
  sed "s|%h/progetti/jarvis-stark-os|$RADICE|" \
      "$RADICE/packaging/jarvis-core.service" > "$DEST/jarvis-core.service"
else
  install -m 0644 "$RADICE/packaging/jarvis-core.service" "$DEST/jarvis-core.service"
fi

systemctl --user daemon-reload
echo "unit installata e systemd ricaricato."
echo

# Prerequisiti che si possono controllare senza avviare niente.
manca=0
command -v uv >/dev/null || { echo "! manca 'uv' — vedi INSTALLA.md §4"; manca=1; }
[[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/jarvis-os/settings.toml" ]] || {
  echo "! manca settings.toml — vedi INSTALLA.md §3"; manca=1; }

cat <<'FINE'

Non ho avviato niente: e' una Sua decisione.

  prova adesso, senza abilitare:   systemctl --user start jarvis-core
  guarda cosa dice:                journalctl --user -u jarvis-core -f
  diagnosi completa:               uv run python -m core.doctor
  al login, da qui in avanti:      systemctl --user enable --now jarvis-core

⚠️ Con `voice.enabled = true` in settings.toml il core apre il MICROFONO
   all'avvio, e con `vision.enabled = true` apre la TELECAMERA. Entrambe
   partono spente.
FINE
exit "$manca"
