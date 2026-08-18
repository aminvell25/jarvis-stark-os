#!/usr/bin/env bash
# Toglie le unit di JARVIS OS. Una cosa che si installa si deve poter togliere,
# e senza dover ricordare dove era finita.
set -euo pipefail

DEST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

systemctl --user disable --now jarvis-core.service 2>/dev/null || true
rm -f "$DEST/jarvis-core.service"
systemctl --user daemon-reload
systemctl --user reset-failed jarvis-core.service 2>/dev/null || true

echo "unit rimossa. Restano intatti:"
echo "  le impostazioni  ${XDG_CONFIG_HOME:-$HOME/.config}/jarvis-os/"
echo "  la memoria       i file markdown di §5.5"
echo "Si cancellano a mano, di proposito: nessun disinstallatore deve poter"
echo "buttare via la memoria di qualcuno."
