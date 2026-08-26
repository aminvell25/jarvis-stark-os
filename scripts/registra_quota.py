"""Registra il contatore del Governor mentre qualcuno parla — §5.4, §16.

    PYTHONPATH=. uv run python scripts/registra_quota.py [--secondi 600]

## Perche' esiste

Il tetto di 15 spawn/ora non e' mai stato toccato da traffico vero. Lo
snapshot pubblica `quota.usati_nella_finestra` a 2,5 Hz e nessuno lo
**conserva**: dopo il fatto si puo' leggere solo l'ultimo valore, che a
finestra scaduta e' tornato a zero. Un contatore che si puo' guardare ma non
rileggere non e' una misura.

Scrive una riga per campione con **due orologi** — quello di parete per
rimettersi in fila col journal, quello monotono per le differenze — sul
modello di `scripts/registra.py`.

⚠️ **`quota` non e' un messaggio periodico.** Va in `state.snapshot`, che il
server manda **una volta sola alla connessione** (`ws_server.py:241`): in
cinque secondi arrivano 13 `telemetry`, 3 `agent.mesh` e **un** solo snapshot.
Per campionarlo bisogna riconnettersi, e questo script lo fa.

⚠️ Non tocca il core: legge il socket e basta.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.platform import paths  # noqa: E402

#: Nessuna attesa fra un campione e l'altro: si registra OGNI snapshot. Un
#:  fra le letture lascia accodare i messaggi e perde proprio i
#: passaggi rapidi — misurato, un campione in cinque secondi.


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secondi", type=float, default=600.0)
    ap.add_argument("--fuori", default="docs/acceptance/QUOTA-VIVA.jsonl")
    a = ap.parse_args()

    import websockets

    sock = paths().socket_path()
    if not sock.exists():
        print(f"nessun socket in {sock}: il core non gira.")
        return 1

    fuori = Path(a.fuori)
    fine = time.monotonic() + a.secondi
    n = 0
    with fuori.open("w", encoding="utf-8") as f:
        while time.monotonic() < fine:
            # ⚠️ **Si RICONNETTE a ogni campione, e non e' spreco.**
            #
            # `state.snapshot` — l'unico messaggio che porta `quota` — viene
            # inviato **una volta sola, alla connessione** (`ws_server.py:241`),
            # non a 2,5 Hz come `telemetry`. Misurato: in cinque secondi
            # arrivano 13 `telemetry`, 3 `agent.mesh` e **un** `state.snapshot`.
            #
            # Il contatore vivo esiste altrove — `agent.mesh` lo rende come
            # testo, «2/2 · 14 nella finestra» — ma parsare una stringa
            # formattata per la UI e' un accoppiamento che si rompe al primo
            # ritocco. Riconnettersi costa un socket UNIX locale e restituisce
            # il numero nella sua forma.
            try:
                async with websockets.unix_connect(str(sock)) as ws:
                    grezzo = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    msg = json.loads(grezzo)
            except Exception as exc:
                f.write(json.dumps({"wall": time.time(), "mono": time.monotonic(),
                                    "errore": repr(exc)}) + "\n")
                f.flush()
                await asyncio.sleep(PERIODO_S)
                continue

            q = msg.get("quota") or {}
            f.write(json.dumps({
                "wall": time.time(),
                "mono": time.monotonic(),
                "usati": q.get("usati_nella_finestra"),
                "restanti": q.get("restanti"),
                "attivi": q.get("attivi"),
                "sospeso": q.get("sospeso"),
            }, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            await asyncio.sleep(PERIODO_S)
    print(f"{n} campioni in {fuori}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
