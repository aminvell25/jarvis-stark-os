"""Legge il diario — `dialogo` e `azione` — SPEC §3.2.

    uv run python scripts/diario.py                 # oggi, tutto
    uv run python scripts/diario.py --dialogo       # solo cio' che si e' detto
    uv run python scripts/diario.py --azioni        # solo cio' che si e' fatto
    uv run python scripts/diario.py --giorno 2026-08-26 --ultimi 50
    uv run python scripts/diario.py --segui         # e resta ad ascoltare
    uv run python scripts/diario.py --traccia 4f1a9c2b7e03   # UN turno intero

⚠️ **La ragione scritta qui era falsa, e falsa nella direzione che fa cancellare
questo file.** Diceva «esiste perche' il pannello della scrivania non c'e'
ancora». Il pannello c'e' dal 26 agosto — `ui/src/panels/diario.js`, stesso
giorno di questo script — ma e' una **coda viva**: riceve `agent.diario` mentre
le righe si scrivono, non apre nessun file e non sa chiedere un giorno.

Quindi questo comando non aspetta niente: **e' l'unico modo di rileggere un
giorno passato**, e resta l'unico finche' il pannello non imparera' a chiederlo.
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
from core.memory.store import MemoryStore  # noqa: E402
from core.platform import paths  # noqa: E402


def _traccia(d: dict) -> str:
    """La colonna dell'origine. Tre stati, e si distinguono a occhio:

        4f1a9c2b7e03   l'id del turno
        ————           il produttore ha dichiarato di non averne una
        (spazio)       riga scritta PRIMA di ADR-011
    """
    if "traccia" not in d:
        return " " * 12
    return str(d["traccia"]) if d["traccia"] else "—" * 12


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
    # ⚠️ **`or` e non il default di `get`, e non e' pedanteria: il comando
    # CADEVA.** `_annota_instradamento` scrive `intento=None` — la chiave c'e'
    # e vale `null` — quindi `get("intento", "?")` restituisce `None`, e
    # `f"{None:16}"` alza `TypeError`.
    #
    # Misurato il 30 agosto sul diario vero: **8 righe su 61**, e
    # `scripts/diario.py --azioni --giorno 2026-08-27` moriva con uno stack
    # trace. Il difetto e' arrivato con le righe di `_annota_instradamento`, ed
    # e' particolarmente crudele: quelle righe esistono per spiegare **perche'
    # non e' successo niente**, e l'unico modo di rileggere un giorno passato
    # si rompeva proprio su quelle. Trovato provando la ricostruzione di
    # ADR-011 su un turno vero, non da un test.
    return (f"{t}   {ok} {(d.get('intento') or '—'):16} "
            f"via {(d.get('strada') or '?'):8}"
            f" {d.get('args') or d.get('testo') or ''}{extra}")


def _riga_iniziativa(d: dict) -> str:
    t = time.strftime("%H:%M:%S", time.localtime(d.get("ts", 0)))
    return (f"{t}   ·   {d.get('tipo','?'):16} "
            f"{d.get('nome') or d.get('sessione') or ''}  "
            f"{d.get('frase') or ''}".rstrip())


def un_turno(ident: str) -> int:
    """Che cosa e' successo in quel turno — **ADR-011, criterio 2**.

    ⚠️ **E' una join su DUE archivi che esistono gia', e non ne nasce un
    terzo.** Il diario tiene cio' che il sistema ha detto e deciso; le ronde di
    protocollo hanno invece il loro record in `initiatives/`, e il commento
    sopra `Engine._ronda_di` vieta di duplicarlo — sarebbe una seconda fonte di
    verita' — cosi' come vieta di registrare le ronde vuote. Quindi la traccia
    entra in entrambi gli archivi e la ricostruzione li rilegge tutti e due,
    in ordine di orologio.

    Prima di ADR-011 questa domanda non aveva risposta: wake, STT, T0, tool e
    riga di diario erano righe che non si toccavano.
    """
    dati = paths().data_dir() / "memory_data"
    d = Diario(dati / "diario")
    store = MemoryStore(dati)

    trovate: list[tuple[float, str]] = []
    for giorno in d.giorni():
        for r in d.leggi(giorno=giorno, limite=10**9):
            if r.get("traccia") == ident:
                trovate.append((r.get("ts", 0.0), _riga(r)))
    for p in sorted(store.initiatives.glob("*.jsonl")):
        for riga in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(riga)
            except json.JSONDecodeError:
                continue
            if r.get("traccia") == ident:
                trovate.append((r.get("ts", 0.0), _riga_iniziativa(r)))

    if not trovate:
        print(f"nessuna riga con traccia {ident!r}.")
        print("Le righe scritte prima di ADR-011 non ne hanno: "
              "`scripts/orfani.py --diario` dice quante sono.")
        return 1
    # ⚠️ Ordine di OROLOGIO DI PARETE, che e' cio' che i due archivi scrivono.
    # `Traccia.t0` e' monotono e serve alla durata, non a mettere in fila righe
    # che vengono da file diversi.
    print(f"traccia {ident} — {len(trovate)} righe\n")
    for _, riga in sorted(trovate, key=lambda x: x[0]):
        print(riga)
    return 0


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
    ap.add_argument("--traccia", metavar="ID",
                    help="ricostruisce UN turno da diario/ e initiatives/")
    a = ap.parse_args()

    if a.traccia:
        return un_turno(a.traccia)

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
