"""Registra una sessione vera del core, per il modo di misura di §11.9.

    uv run python scripts/registra.py [--secondi 75]

## Perche' esiste

Due sessioni di `npm run scrivania` davano `L>60` 26,1 % e 25,3 %, e la
differenza non era attribuibile: `telemetry` arriva a 2,5 Hz e le due serie
uPlot sono aree piene sopra la soglia L>60, alte quanto `cpu_percent`, su un
pannello che e' il 16,5 % dello schermo. Quattro misure sono gia' state
contaminate cosi'.

§11.9 concede una seconda eccezione al divieto di dati finti — il **modo di
misura** — a cinque condizioni, e la prima e' che i dati siano **registrati da
una sessione vera, mai generati**. Questo script fa la registrazione.

## Perche' NON e' `ws_probe.py` esteso

Quel file dichiara di esistere per provare che il dato e' **vero**: «e' cosi'
che si verifica che il dato e' REALE e non un valore inventato dal server».
Farne anche la cosa che lo rende **vecchio** e' un conflitto dentro un file
solo. Ne eredita pero' due idee buone: controllare il socket prima di provarci,
e la **controprova psutil indipendente** — che qui non si stampa e si perde, si
scrive **dentro l'artefatto**.

## Che cosa produce

Due file in `docs/acceptance/`, la coppia esatta di `CATALOGO-SCORRIMENTO.json`
piu' `tests/test_catalogo.py`:

    SESSIONE-SCRIVANIA.jsonl   una riga per frame: {"ms": …, "msg": {…}}
    SESSIONE-SCRIVANIA.json    la provenienza, con l'impronta sha256 del .jsonl

JSONL e non un `.json` unico perche' il filo **e'** una sequenza di frame: una
modifica a mano compare come una riga sola in un diff invece di sparire dentro
un array indentato.

Il messaggio si salva **decodificato** e non come stringa grezza: `barra.js`
conta `JSON.stringify(m)` sull'oggetto gia' passato da `JSON.parse`, quindi i
byte sul filo non entrano in nessuna metrica, e un file leggibile si puo'
rivedere prima di committarlo — cosa necessaria, perche' contiene percorsi
della home e l'elenco dei file della workspace. Le chiavi no: `_encode` del
server le ha gia' oscurate all'origine.

⚠️ **La macchina dev'essere quieta.** Se durante la registrazione scatta un
`agent.advisory` di livello `critical` — `package_temp_c > 75`, valutato a
2,5 Hz — la barra resta inchiodata su `degraded` in ogni riproduzione futura.
Lo script lo **dichiara** invece di filtrarlo: filtrare un frame sarebbe
inventare una sessione che non c'e' stata.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Come `ws_probe.py`: eseguito da `scripts/`, l'interprete non mette la radice
# in sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from websockets.asyncio.client import unix_connect  # noqa: E402

from core.platform import (  # noqa: E402
    paths as platform_paths,
    sensors as platform_sensors,
)

RADICE = Path(__file__).resolve().parent.parent
FILO = RADICE / "docs" / "acceptance" / "SESSIONE-SCRIVANIA.jsonl"
PROVENIENZA = RADICE / "docs" / "acceptance" / "SESSIONE-SCRIVANIA.json"

#: Sotto i 48 s il grafico della telemetria resta parziale: `telemetry.js`
#: tiene 120 campioni a 2,5 Hz. Con 75 s ce ne sono ~187 e c'e' margine.
SECONDI = 75


def impronta(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()[:16]


def commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=RADICE, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:                                          # noqa: BLE001
        return "sconosciuto"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secondi", type=float, default=SECONDI)
    args = ap.parse_args()

    sock = platform_paths().socket_path()
    if not sock.exists():
        print(f"nessun socket in {sock} — il core non e' in esecuzione.")
        print("avvialo con:  uv run python -m core.engine")
        return 1

    sensors = platform_sensors()
    sensors.cpu_percent()                      # innesca il contatore locale

    frame: list[dict] = []
    critici = 0
    t0 = time.monotonic()

    async with unix_connect(str(sock)) as ws:
        scadenza = t0 + args.secondi
        while time.monotonic() < scadenza:
            resto = scadenza - time.monotonic()
            try:
                grezzo = await asyncio.wait_for(ws.recv(), timeout=resto)
            except asyncio.TimeoutError:
                break
            msg = json.loads(grezzo)
            if msg.get("topic") == "agent.advisory" and msg.get("level") == "critical":
                critici += 1
            frame.append({"ms": round((time.monotonic() - t0) * 1000), "msg": msg})

    if not frame:
        print("nessun frame ricevuto: il core e' collegato ma non parla.")
        return 1

    FILO.write_text(
        "".join(json.dumps(f, ensure_ascii=False, sort_keys=True) + "\n" for f in frame),
        encoding="utf-8")

    per_topic = Counter(f["msg"].get("topic", "?") for f in frame)
    # La controprova di `ws_probe.py`, ma SCRITTA invece che stampata: dice che
    # i valori registrati venivano da una macchina vera, e lo dice dentro
    # l'artefatto, dove chi rivede il file la trova.
    mem = sensors.memory()
    controprova = {
        "cpu_percent": round(sensors.cpu_percent(), 1),
        "ram_percent": round(mem.percent, 1),
        "package_temp_c": sensors.package_temp(),
        "letta_con": "psutil, in questo processo, indipendentemente dal socket",
    }
    PROVENIENZA.write_text(json.dumps({
        "_": "GENERATO da scripts/registra.py — non modificare a mano",
        "quando": datetime.now(timezone.utc).isoformat(),
        "durata_ms": frame[-1]["ms"],
        "frame": len(frame),
        "perTopic": dict(sorted(per_topic.items())),
        "impronta": impronta(FILO),
        "controprova": controprova,
        "commit": commit(),
        "avvisiCritici": critici,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"  filo        {FILO.relative_to(RADICE)} · {len(frame)} frame · "
          f"{frame[-1]['ms'] / 1000:.1f} s")
    for t, n in sorted(per_topic.items()):
        print(f"              {t:22} {n:5}")
    print(f"  provenienza {PROVENIENZA.relative_to(RADICE)} · impronta {impronta(FILO)}")
    if critici:
        print(f"\n  ⚠️ {critici} advisory CRITICAL nella registrazione: la barra restera'")
        print("     su «degraded» in ogni riproduzione. Se non e' voluto, rifai la")
        print("     registrazione a macchina fredda — non togliere i frame a mano.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
