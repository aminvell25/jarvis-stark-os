"""Avvia il core e chiede un'operazione distruttiva vera, per la verifica §6.2.

Serve a chiudere il tratto che `tests/test_confirm_e2e.py` non tocca: quel test
prova il giro attraverso il socket con un client di prova, questo lo prova con
la finestra vera di Electron.

    uv run python scripts/prova_conferma.py [--attendi-client]

Da usare insieme a `scripts/verifica-conferma.mjs`, che guida la finestra.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.engine import Engine  # noqa: E402
from core.tools import registry as R  # noqa: E402


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nome", default="prova-conferma.txt")
    ap.add_argument("--attesa-client", type=float, default=60.0)
    args = ap.parse_args()

    engine = Engine()
    bersaglio = engine.settings.fs.workspace / args.nome
    bersaglio.parent.mkdir(parents=True, exist_ok=True)
    bersaglio.write_text("contenuto da cestinare", encoding="utf-8")
    print(f"BERSAGLIO {bersaglio}", flush=True)

    task = asyncio.create_task(engine.run())

    scadenza = asyncio.get_running_loop().time() + args.attesa_client
    while asyncio.get_running_loop().time() < scadenza:
        if engine._ws.client_count > 0:
            break
        await asyncio.sleep(0.1)
    print(f"CLIENT {engine._ws.client_count}", flush=True)
    await asyncio.sleep(1.0)

    print("CHIEDO trash_path", flush=True)
    r = await R.invoke("trash_path", {"path": str(bersaglio)})
    print(f"ESITO ok={r.ok} error={r.error}", flush=True)
    print(f"OUTPUT {r.output}", flush=True)
    print(f"ESISTE_ANCORA {bersaglio.exists()}", flush=True)

    engine._stop.set()
    await asyncio.wait_for(task, timeout=10)
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
