"""Riproduce una sessione registrata, per il modo di misura di §11.9.

    uv run python scripts/riproduttore.py --da docs/acceptance/SESSIONE-SCRIVANIA.jsonl \\
                                          --socket /run/user/1000/jarvis-os/riproduzione.sock

Stampa `pronto <percorso>` su stdout quando il socket accetta connessioni, e
poi resta in ascolto. Chi lo avvia aspetta **quella riga**, non l'esistenza del
file: fra `bind()` e `chmod 0600` c'e' una finestra, e collegarsi dentro quella
finestra e' precisamente cio' che la disciplina del socket esiste per impedire.

## Perche' non riusa `WsServer`

Quattro ragioni, in ordine di peso:

1. **`_invia` E' il ciclo di campionamento vivo.** Per riprodurre lo si
   scavalca per intero, e cio' che resta di `WsServer` e' il ciclo di vita del
   socket — che infatti e' stato estratto come `prepara_socket()` ed e' l'unica
   cosa che si riusa.
2. **`__init__` pretende `state_provider`, `sensors`, `paths`.** Passargli dei
   finti per soddisfare una firma e' la forma con cui una classe critica per la
   sicurezza acquista una «modalita' di prova». `core/ws_server.py` e' puntato
   da tre file di test sulla sicurezza: chi legge quel confine domani non deve
   dover ragionare su un ramo che in produzione non si raggiunge mai.
3. **`_riceve` accetta tre tipi di messaggio e li smista.** Il riproduttore ne
   deve accettare **zero**. E' la politica opposta, non un parametro della
   stessa politica.
4. **`_encode` rioscura i segreti e riserializza.** La registrazione e' gia'
   oscurata all'origine — e' stata catturata *dopo* `_encode` — e riserializzare
   e' un secondo posto in cui l'ordine delle chiavi puo' cambiare.

## Le due scelte che sembrano dettagli e non lo sono

**A fine registrazione la connessione resta APERTA e muta.** Se chiudesse,
`app/main.js` riproverebbe col backoff e **rigiocherebbe lo stream dall'inizio**:
un ciclo infinito di scrivanie, col PNG catturato in un punto qualunque del
secondo giro.

**Cio' che sale si legge e si scarta.** Non conferme, non layout, niente. E'
anche la ragione per cui il modo di misura **smette di corrompere
`layout.json`**: `scena("avvio")` risale come `ui.layout` e il core la scrive su
disco, ed e' la contaminazione che `FASE-1-CONTRAZIONE.md` ha gia' dovuto
ripulire a mano.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from websockets.asyncio.server import unix_serve  # noqa: E402

from core.ws_server import prepara_socket  # noqa: E402


def leggi(filo: Path) -> list[dict]:
    return [json.loads(r) for r in filo.read_text(encoding="utf-8").splitlines() if r.strip()]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--da", required=True, type=Path)
    ap.add_argument("--socket", required=True, type=Path)
    #: 1.0 = il tempo della registrazione. 0 = il piu' in fretta possibile.
    #: Quale usare l'ha deciso una misura, non un'opinione: due giri a 1x e due
    #: a 10x, sull'impronta 4d5edf35cfdb64af, danno lo STESSO PNG byte per byte
    #: (`scripts/differenza.mjs`: «uguali»), e il giro passa da ~100 s a 20 s.
    #: Per questo `npm run scrivania:fixture` passa `--velocita 10`.
    #:
    #: A 10x la telemetria arriva a 25 Hz invece di 2,5, e il grafico resta
    #: identico perche' `telemetry.js` tiene gli ULTIMI 120 campioni comunque:
    #: cambia quando arrivano, non quali restano.
    #:
    #: ⚠️ La misura vale per QUESTA registrazione. Rifarla azzera la baseline
    #: (§11.9), e l'equivalenza 1x/10x va rimisurata insieme al resto.
    ap.add_argument("--velocita", type=float, default=1.0)
    args = ap.parse_args()

    if not args.da.exists():
        print(f"manca {args.da}", file=sys.stderr)
        return 2
    frame = leggi(args.da)
    if not frame:
        print(f"{args.da} e' vuoto", file=sys.stderr)
        return 2

    servite = 0

    async def servi(ws) -> None:
        nonlocal servite
        servite += 1
        if servite > 1:
            # Un secondo client vedrebbe lo stream da capo mentre il primo e'
            # a meta': due scrivanie diverse dalla stessa registrazione.
            print("  rifiutato un secondo client", file=sys.stderr)
            await ws.close()
            return

        async def scarta() -> None:
            try:
                async for _ in ws:
                    pass
            except Exception:                                  # noqa: BLE001
                pass

        muto = asyncio.create_task(scarta())
        precedente = 0
        for f in frame:
            if args.velocita > 0:
                attesa = (f["ms"] - precedente) / 1000 / args.velocita
                if attesa > 0:
                    await asyncio.sleep(attesa)
            precedente = f["ms"]
            await ws.send(json.dumps(f["msg"], ensure_ascii=False))
        print(f"  trasmessi {len(frame)} frame, la connessione resta aperta",
              file=sys.stderr)
        await muto            # si resta muti finche' il client se ne va

    sock = prepara_socket(args.socket)
    async with unix_serve(servi, str(sock)):
        sock.chmod(0o600)
        # La riga che chi ci avvia sta aspettando. `flush` perche' stdout verso
        # una pipe e' bufferizzato, e chi aspetta resterebbe fermo per sempre.
        print(f"pronto {sock}", flush=True)
        await asyncio.Future()                                 # per sempre
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(0) from None
