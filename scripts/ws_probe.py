"""Client di diagnosi per il socket del core.

SPEC §22 Fase 1 nomina `websocat` come strumento del criterio di accettazione.
**Scostamento dichiarato**: `websocat` non e' installato, e con il socket UNIX
di §18.2 servirebbe comunque il supporto `ws+unix://`. Questo script usa la
libreria `websockets` gia' fra le dipendenze: zero dipendenze nuove, e resta
nel repo come strumento riusabile.

    uv run python scripts/ws_probe.py [--messaggi N]

Stampa lo `state.snapshot` e i messaggi di telemetria che seguono, e confronta
la telemetria ricevuta con una lettura indipendente di psutil: e' cosi' che si
verifica che il dato e' REALE e non un valore inventato dal server.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Eseguito come `python scripts/ws_probe.py`, l'interprete mette `scripts/` in
# sys.path, non la radice del repository: senza questa riga `core` non si
# importa. E' uno strumento di diagnosi, deve funzionare da qualunque cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from websockets.asyncio.client import unix_connect  # noqa: E402

from core.platform import (  # noqa: E402
    paths as platform_paths,
    sensors as platform_sensors,
)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--messaggi", type=int, default=4)
    args = ap.parse_args()

    sock = platform_paths().socket_path()
    if not sock.exists():
        print(f"nessun socket in {sock} — il core non e' in esecuzione.")
        print("avvialo con:  uv run python -m core.engine")
        return 1

    sensors = platform_sensors()
    sensors.cpu_percent()                      # innesca il contatore locale

    async with unix_connect(str(sock)) as ws:
        snap = json.loads(await ws.recv())
        print("=== state.snapshot ===")
        print(json.dumps(snap, indent=2, ensure_ascii=False))

        print(f"\n=== telemetria ({args.messaggi} messaggi) ===")
        for _ in range(args.messaggi):
            m = json.loads(await ws.recv())
            if m.get("topic") != "telemetry":
                print(f"  [{m.get('topic')}] {m}")
                continue
            top = ", ".join(f"{p['name']}:{p['cpu']:.0f}%" for p in m.get("top3", [])[:3])
            print(f"  cpu {m['cpu_percent']:5.1f}%  ram {m['ram_percent']:5.1f}%  "
                  f"temp {m['package_temp_c']}  {top}")

    mem = sensors.memory()
    print("\n=== controprova indipendente (psutil letto da questo processo) ===")
    print(f"  ram {mem.percent:.1f}%   temp {sensors.package_temp()}")
    print("  se i due blocchi concordano, il dato sul socket e' misurato, non inventato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
