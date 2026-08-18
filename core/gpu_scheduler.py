"""Controllo di ammissione della memoria GPU — SPEC §9.

§9 pone una regola dura: **monitorare la VRAM e rifiutare di caricare un
modello se manca headroom**, invece di lasciar spillare in RAM via PCIe. Questo
modulo risponde a una sola domanda — *posso caricare N byte?* — e la risposta
e' misurata, mai stimata.

NOTA APU (rev 5.2). La tabella «4 / 8 / 12 GB» di §9 presuppone una GPU
discreta, dove la VRAM e' memoria in piu'. Su una GPU integrata e' un carveout
della stessa RAM di sistema: caricare 3 GB "in VRAM" non libera nulla. Su
memoria unificata l'headroom e' quindi il MINIMO fra VRAM libera e RAM
disponibile. Misurando la sola VRAM, questo modulo direbbe "c'e' spazio"
mentre il sistema sta esaurendo la memoria.

In Fase 1 nessun modello viene caricato: il modulo misura e decide, e le Fasi
3 e 5 lo interrogano.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from core.platform import Gpu, GpuMemory, Sensors

log = structlog.get_logger(__name__)

#: Margine da lasciare sempre libero, in byte.
#:
#: §9 stima la scena three.js + PixiJS a 60fps in 1-2 GB, e §24 punto 5 dichiara
#: che **nessuna fonte primaria lo quantifica**: e' una stima prudenziale, non
#: una misura. Il valore va ritarato in Fase 5 con un profilo vero, e finche'
#: non lo e' resta scritto qui che e' provvisorio.
RISERVA_DEFAULT = 1024 * 1024 * 1024


@dataclass(frozen=True)
class Admission:
    """L'esito di una richiesta di ammissione. Contiene la MISURA, non solo
    il verdetto: un rifiuto che non dice quanto mancava e' inservibile."""

    granted: bool
    requested: int
    headroom: int
    reserve: int
    reason: str
    measure: GpuMemory | None
    ram_available: int | None

    @property
    def shortfall(self) -> int:
        """Byte mancanti. Zero se la richiesta e' stata accolta."""
        return max(0, self.requested + self.reserve - self.headroom)


class GpuScheduler:
    def __init__(self, gpu: Gpu, sensors: Sensors,
                 reserve: int = RISERVA_DEFAULT) -> None:
        self._gpu = gpu
        self._sensors = sensors
        self._reserve = reserve

    def headroom(self) -> tuple[int, GpuMemory | None, int | None]:
        """`(headroom, misura, ram_disponibile)`.

        Su memoria unificata il vincolo e' il piu' stretto fra i due, perche'
        sono lo stesso silicio.
        """
        misura = self._gpu.memory()
        if misura is None:
            return 0, None, None
        if not misura.unified:
            return misura.free, misura, None
        ram = self._sensors.memory().available
        return min(misura.free, ram), misura, ram

    def can_admit(self, need: int) -> Admission:
        """Posso caricare `need` byte sulla GPU?"""
        head, misura, ram = self.headroom()

        if misura is None:
            # Non misurabile non significa "c'e' spazio". §9 dice di rifiutare
            # quando manca headroom, e headroom sconosciuto e' il caso in cui
            # non si puo' affermare che ci sia.
            return Admission(
                granted=False, requested=need, headroom=0, reserve=self._reserve,
                reason="memoria GPU non misurabile su questa piattaforma",
                measure=None, ram_available=None,
            )

        granted = need + self._reserve <= head
        if granted:
            reason = "headroom sufficiente"
        elif misura.unified:
            reason = (
                f"headroom insufficiente su memoria unificata: il vincolo e' il "
                f"minimo fra VRAM libera ({misura.free / 2**20:.0f} MiB) e RAM "
                f"disponibile ({(ram or 0) / 2**20:.0f} MiB)"
            )
        else:
            reason = f"VRAM libera insufficiente ({misura.free / 2**20:.0f} MiB)"

        esito = Admission(
            granted=granted, requested=need, headroom=head, reserve=self._reserve,
            reason=reason, measure=misura, ram_available=ram,
        )
        log.info(
            "ammissione_gpu",
            concessa=granted,
            richiesti_mib=round(need / 2**20),
            headroom_mib=round(head / 2**20),
            unificata=misura.unified,
        )
        return esito
