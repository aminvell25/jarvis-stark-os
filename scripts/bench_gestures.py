"""Misura la catena gesture dal vivo — §14.1, criterio 2 di Fase 7.

    PYTHONPATH=. uv run python scripts/bench_gestures.py [fotogrammi]

⚠️ **Accende la telecamera.** Nessun fotogramma viene salvato o trasmesso: da
`fotogrammi()` escono solo landmark normalizzati, e questo script stampa
numeri. La telecamera si spegne appena il conteggio finisce, anche se qualcosa
va storto — `with` lo garantisce.
"""

from __future__ import annotations

import statistics
import sys
import time

from core.gestures.mapping import Isteresi, Riconoscitore
from core.gestures.tracker import TrackerMediaPipe
from core.platform import paths

QUANTI = int(sys.argv[1]) if len(sys.argv) > 1 else 150
ESPOSIZIONE = float(sys.argv[2]) if len(sys.argv) > 2 else None


def main() -> int:
    t = TrackerMediaPipe(paths().data_dir(), esposizione=ESPOSIZIONE)
    if not t.disponibile():
        print("MediaPipe non installato: niente da misurare.")
        return 1

    riconosci, isteresi = Riconoscitore(), Isteresi()
    inferenze: list[float] = []
    visti: list[str] = []
    con_mano = 0

    print(f"accendo la telecamera per {QUANTI} fotogrammi.")
    print("METTA UNA MANO davanti alla webcam: palmo aperto, poi un pizzico.\n", flush=True)
    t0 = time.perf_counter()
    with t:
        for f in t.fotogrammi(QUANTI):
            inferenze.append(f.ms_inferenza)
            if f.mani:
                con_mano += 1
            if (g := isteresi.alimenta(riconosci(f))) is not None:
                visti.append(g)
                print(f"  [{f.indice:3d}] gesto: {g}", flush=True)
    durata = time.perf_counter() - t0

    print(f"\nfotogrammi     {len(inferenze)} in {durata:.2f} s")
    print(f"fps catena     {len(inferenze) / durata:.1f}")
    print(f"fps telecamera {t.fps_camera:.1f} "
          f"({'esposizione forzata' if ESPOSIZIONE else 'esposizione automatica'})")
    print(f"inferenza      mediana {statistics.median(inferenze):.1f} ms · "
          f"max {max(inferenze):.1f} ms")
    print(f"con una mano   {con_mano}/{len(inferenze)} fotogrammi")
    print(f"gesti emessi   {visti or 'nessuno'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
