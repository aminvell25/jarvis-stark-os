"""Il banco degli argomenti, ma con haiku VERO — §15, §11.7.

`tests/eval_argomenti.py` misura la regola locale a costo zero e in 60 ms. Non
puo' misurare haiku: servono una rete, una quota e ~2,2 USD nozionali a giro, e
un test che spende non e' un test. Questo script lo fa a mano, e scrive l'esito
in `docs/acceptance/HAIKU-BARRA.json`, che il banco poi controlla senza
spendere.

## Che cosa misura, e che cosa NON misura

⚠️ **Misura il percorso di produzione di OGGI, che e' una frase per volta.**
`MotoreNews.ascolta(detto)` passa una singola battuta a `EstrattoreLLM.aggiorna`,
e il «batch» di §15 e' un limitatore di frequenza, non un accumulatore: dentro
la finestra le altre battute vengono SCARTATE, non sommate. Percio' misurare
frase per frase non e' un percorso inventato — e' quello che gira. Il giorno in
cui il batch accumulera' davvero, questo numero andra' rifatto, perche' haiku
avra' piu' contesto di adesso.

⚠️ **Misura haiku PIU' il filtro estrattivo**, che e' cio' che va in produzione.
Salva pero' le risposte grezze, cosi' l'analisi puo' dire quanto dei due sta
reggendo il numero — e la risposta e' che il filtro ne regge la maggior parte.

⚠️ **Il Governor qui non e' quello di produzione**: 8 spawn in parallelo e
nessun tetto orario, contro 2 e 15/ora. Con quelli veri 43 frasi non
starebbero in una finestra sola. E' una scelta del banco, non una misura.

    uv run python scripts/banco_haiku.py 5          # cinque giri, una frase per spawn
    uv run python scripts/banco_haiku.py 5 --gruppi 5   # cinque battute per spawn
    uv run python scripts/banco_haiku.py 1 --frasi 5    # pilota

## Il percorso a GRUPPI

Dopo la correzione dello scarto, la produzione ha **due** ingressi: la prima
battuta dopo un silenzio va da sola, e le successive vanno insieme a fine
finestra. `--gruppi N` misura il secondo, componendo le 43 frasi in gruppi
contigui di N — l'ordine e' quello del corpus, ed e' una scelta dichiarata.
L'atteso di un gruppo e' l'**unione** degli attesi delle sue frasi: nessuna
etichetta nuova, solo le stesse composte come le comporra' il giro vero.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from core.llm.claude_t2 import ClaudeT2
from core.llm.governor import Governor
from core.news.topics import PROMPT

RADICE = Path(__file__).resolve().parent.parent
GREZZE = RADICE / "docs" / "acceptance" / "HAIKU-RISPOSTE.json"
GRUPPI = RADICE / "docs" / "acceptance" / "HAIKU-RISPOSTE-GRUPPI.json"

#: 8 e non 2: vedi l'intestazione. Il tetto orario sparisce perche' 43 frasi per
#: giro sfonderebbero i 15 di `MAX_PER_WINDOW` alla terza frase.
PARALLELE = 8


async def un_giro(t2: ClaudeT2, frasi: list[str], giro: int) -> list[dict]:
    async def una(frase: str) -> dict:
        r = await t2.esegui(PROMPT.format(testo=frase), f"banco{giro}")
        return {"frase": frase, "ok": r.ok, "testo": r.testo,
                "durata_s": r.durata_s, "costo": r.costo_usd, "errore": r.errore}

    return list(await asyncio.gather(*(una(f) for f in frasi)))


async def main() -> None:
    from tests.t0_corpus import CONVERSAZIONALI

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    argomenti = sys.argv[2:]
    quante = (int(argomenti[argomenti.index("--frasi") + 1])
              if "--frasi" in argomenti else len(CONVERSAZIONALI))
    gruppo = (int(argomenti[argomenti.index("--gruppi") + 1])
              if "--gruppi" in argomenti else 1)
    scelte = CONVERSAZIONALI[:quante]
    frasi = ["\n".join(scelte[i:i + gruppo]) for i in range(0, len(scelte), gruppo)]
    print(f"{len(scelte)} frasi in {len(frasi)} spawn per giro "
          f"(gruppi da {gruppo})", flush=True)
    t2 = ClaudeT2(Governor(max_concurrent=PARALLELE, max_per_window=10_000),
                  RADICE, modello="haiku", tool="", max_turns=1)

    giri, costo = [], 0.0
    for g in range(n):
        t0 = time.monotonic()
        esiti = await un_giro(t2, frasi, g)
        giri.append(esiti)
        speso = sum(e["costo"] or 0 for e in esiti)
        costo += speso
        falliti = [e for e in esiti if not e["ok"]]
        print(f"giro {g}: {len(esiti)} frasi · {time.monotonic() - t0:.0f} s · "
              f"{speso:.4f} USD · falliti {len(falliti)}", flush=True)

    fuori = GREZZE if gruppo == 1 else GRUPPI
    fuori.write_text(json.dumps(giri, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(f"totale {costo:.4f} USD nozionali · risposte grezze in {fuori.name}")


if __name__ == "__main__":
    asyncio.run(main())
