"""Legge il diario — `dialogo` e `azione` — SPEC §3.2.

    uv run python scripts/diario.py                 # oggi, tutto
    uv run python scripts/diario.py --dialogo       # solo cio' che si e' detto
    uv run python scripts/diario.py --azioni        # solo cio' che si e' fatto
    uv run python scripts/diario.py --giorno 2026-08-26 --ultimi 50
    uv run python scripts/diario.py --segui         # e resta ad ascoltare

Esiste perche' il pannello della scrivania non c'e' ancora, e chi lo aspetta
non deve aspettare anche il registro. Legge lo stesso file che il pannello
mostrera'.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.diario import TOPIC, Diario  # noqa: E402
from core.platform import paths  # noqa: E402


def _riga(d: dict) -> str:
    t = time.strftime("%H:%M:%S", time.localtime(d.get("ts", 0)))
    if d.get("flusso") == "dialogo":
        chi = d.get("chi", "?")
        segni = []
        if d.get("interrotto"):
            segni.append("INTERROTTO")
        if chi == "jarvis" and d.get("misurato") is False:
            segni.append("detto≈stimato")
        coda = f"   [{' · '.join(segni)}]" if segni else ""
        freccia = "▸" if chi == "signore" else "◂"
        return f"{t} {freccia} {chi:8} {d.get('testo','')}{coda}"
    ok = "ok " if d.get("ok") else "NO "
    extra = f" — {d.get('errore')}" if d.get("errore") else ""
    return (f"{t}   {ok} {d.get('intento','?'):16} via {d.get('strada','?'):8}"
            f" {d.get('args') or ''}{extra}")


async def segui() -> int:
    import websockets

    sock = paths().socket_path()
    if not sock.exists():
        print(f"nessun socket in {sock}: il core non gira.")
        return 1
    print("in ascolto sul diario. Ctrl-C per smettere.\n")
    async with websockets.unix_connect(str(sock)) as ws:
        while True:
            try:
                msg = json.loads(await ws.recv())
            except json.JSONDecodeError:
                continue
            if msg.get("topic") == TOPIC:
                print(_riga(msg), flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dialogo", action="store_true")
    ap.add_argument("--azioni", action="store_true")
    ap.add_argument("--giorno")
    ap.add_argument("--ultimi", type=int, default=200)
    ap.add_argument("--segui", action="store_true")
    a = ap.parse_args()

    if a.segui:
        try:
            return asyncio.run(segui())
        except KeyboardInterrupt:
            return 0

    d = Diario(paths().data_dir() / "memory_data" / "diario")
    flusso = "dialogo" if a.dialogo else "azione" if a.azioni else None
    righe = d.leggi(giorno=a.giorno, flusso=flusso, limite=a.ultimi)
    if not righe:
        giorni = d.giorni()
        print(f"nessuna riga. Giorni disponibili: {', '.join(giorni) or 'nessuno'}")
        return 0
    for r in righe:
        print(_riga(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
