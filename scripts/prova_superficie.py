"""Il core VERO che compone una superficie quando la scrivania si collega.

    XDG_CONFIG_HOME=<albero>/cfg XDG_DATA_HOME=<albero>/dati \
      uv run python scripts/prova_superficie.py [diagnostica]

Serve a `scripts/prova-superficie.mjs`, che avvia Electron contro questo core e
misura che cosa arriva davvero sullo schermo — §11.7 passo 0 regola 2: «cio' che
attraversa un confine si prova attraversando quel confine. Il layout tocca
renderer, preload, ponte, socket, core e disco».

## Perche' serve un lanciatore invece di `python -m core.engine`

La composizione la chiede una **frase**, e passa da `esegui_t0`. Dal di fuori
del processo non c'e' modo di mandarne una: `core/ws_server.py` accetta cinque
messaggi e nessuno di loro e' un testo — l'assenza e' una decisione presa
(ADR-011, correzione ①), non una dimenticanza.

Quindi il lanciatore fa dall'interno cio' che farebbe la voce: aspetta che una
scrivania si colleghi e chiama `esegui_t0(parse("componi la superficie ..."))`
con una traccia vera. **Non salta niente**: attraversa la grammatica, l'esecutore
T0, il compilatore, il disco e il socket. E' l'analogo esatto di cio' che
`prova-scena.mjs` fa dall'altra parte del confine chiamando
`window.__scrivania.scrivania.scena(nome)`.

⚠️ **Il core gira su una configurazione a parte.** `~/.config/jarvis-os/`
appartiene al Signore e non si tocca — e per di piu' non dichiara nessuna scena,
quindi l'allowlist della composizione sarebbe vuota. La prova vuole
`config/settings.toml`, versionata, che le scene le ha.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import log as core_log  # noqa: E402
from core.engine import Engine  # noqa: E402
from core.llm.grammar import parse  # noqa: E402
from core.traccia import Origine, Traccia  # noqa: E402

SUPERFICIE = sys.argv[1] if len(sys.argv) > 1 else "diagnostica"
FRASE = f"componi la superficie {SUPERFICIE}"


async def componi_quando_arriva(e: Engine) -> None:
    """Aspetta la scrivania, poi dice la frase. Una volta sola."""
    for _ in range(600):                       # sessanta secondi
        if e._ws.scrivanie > 0:
            break
        await asyncio.sleep(0.1)
    else:
        print("[prova] nessuna scrivania si e' collegata", flush=True)
        return
    # Il ripristino d'avvio deve essere finito, o si sovrappone alla
    # composizione e non si distingue quale dei due si sta guardando.
    await asyncio.sleep(3.0)

    # ⚠️ **Prima si sgombra, e non e' una scorciatoia della prova: e' il flusso.**
    # La scrivania apre sei pannelli all'avvio, e la regola 1 di ADR-013 dice
    # che i pannelli a schermo non si toccano — misurato il 30 agosto: senza
    # sgombrare, nessuna superficie si compone mai. «Nascondi tutto» libera la
    # griglia perche' `GeometriaPannello.nascosto` adesso attraversa il confine.
    # Sono due frasi che una persona dice davvero, una dopo l'altra.
    await e.esegui_t0(parse("nascondi tutto"), Traccia.nuova(Origine.VOCE))
    # Il renderer nasconde, poi RIFERISCE la nuova disposizione: senza questa
    # attesa il core comporrebbe sulla griglia di prima.
    await asyncio.sleep(2.5)

    intento = parse(FRASE)
    if intento is None:
        print(f"[prova] la grammatica non riconosce {FRASE!r}", flush=True)
        return
    esito = await e.esegui_t0(intento, Traccia.nuova(Origine.VOCE))
    print(f"[prova] {FRASE!r} -> {esito}", flush=True)


async def main() -> int:
    core_log.configura()
    e = Engine()
    asyncio.get_running_loop().create_task(componi_quando_arriva(e))
    await e.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
