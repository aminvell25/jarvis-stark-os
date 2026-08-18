"""Banco di misura del primo token di T1 — la domanda aperta di §24 punto 2.

§24 lasciava aperto «il primo token sulla sessione persistente, che e' il numero
che conta davvero», attendendo 300-900 ms e dichiarando che oltre 1500 ms il
design va rivalutato.

Questo script lo misura. Esiste perche' quel numero va **rimisurato**, non
ricordato: dipende dal modello, dalla rete e dal servizio, e cambiera'.

    uv run python scripts/bench_t1.py [--giri 5]
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.llm.claude_t1 import ClaudeT1  # noqa: E402

SOGLIA_ATTESA_MS = 900     # §24: atteso 300-900
SOGLIA_ALLARME_MS = 1500   # §24: oltre questo il design va rivalutato


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--giri", type=int, default=5)
    ap.add_argument("--modello", default="claude-haiku-4-5-20251001")
    args = ap.parse_args()

    radice = Path(__file__).resolve().parent.parent
    t1 = ClaudeT1(args.modello,
                  Path.home() / ".local/share/jarvis-os/voice-cwd",
                  radice / "config/voice-persona.md")

    async def turno(testo: str) -> float | None:
        t0 = time.perf_counter()
        primo = None
        async for _ in t1.ask(testo):
            if primo is None:
                primo = time.perf_counter()
        return (primo - t0) * 1000 if primo else None

    await t1.start()
    freddo = await turno("Di' soltanto: pronto.")
    print(f"  a freddo          {freddo:7.0f} ms")

    tempi = []
    for i in range(args.giri):
        ms = await turno(f"Rispondi con una frase brevissima, prova {i + 1}.")
        if ms:
            tempi.append(ms)
            print(f"  turno caldo {i + 1:<2}    {ms:7.0f} ms")
    await t1.stop()

    if not tempi:
        print("  nessuna misura")
        return 1

    mediana = statistics.median(tempi)
    print(f"\n  MEDIANA CALDA     {mediana:7.0f} ms")
    print(f"  risparmio della persistenza: {freddo - mediana:.0f} ms")
    if mediana <= SOGLIA_ATTESA_MS:
        print("  ✅ dentro le attese di §24")
    elif mediana <= SOGLIA_ALLARME_MS:
        print("  ⚠️  sopra le attese, sotto la soglia di riesame")
    else:
        print(f"  ❌ OLTRE {SOGLIA_ALLARME_MS} ms: §24 punto 2 chiede di rivalutare il design")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
