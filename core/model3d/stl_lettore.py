"""STL riletto con `struct` e `numpy.frombuffer` (binario) o riga per riga (ASCII) — la fonte del verificatore.

Speculare a `glb_lettore.py`, e per la stessa ragione di ADR-012: chi scrive il
file nel laboratorio e' uno script eseguito in sandbox, con `trimesh` o con
quel che vuole; chi lo rilegge qui e' il formato. STL binario e' ottanta byte
di intestazione, un `uint32` col numero di triangoli, e cinquanta byte per
triangolo: normale, tre vertici, due byte di attributo. Non c'e' niente da
interpretare, e un file che non torna coi conti si rifiuta invece di essere
«riparato».

STL non ha unita': il laboratorio lavora in **millimetri** (`CLAUDE.md`,
stile codice), e lo dice a chi scrive lo script. Un file in metri qui
sembrerebbe un pezzo da un millesimo — che e' esattamente cio' che il confronto
col bbox atteso deve far vedere.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

#: Il formato, in tre numeri. Non sono configurabili: sono STL.
INTESTAZIONE = 80
BYTE_PER_TRIANGOLO = 50
#: Un record: normale (3 float), tre vertici (9 float), attributo (uint16).
_RECORD = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
assert _RECORD.itemsize == BYTE_PER_TRIANGOLO


class StlIllegibile(ValueError):
    """Il file non e' un STL binario che torna coi conti."""


@dataclass(frozen=True)
class LetturaStl:
    byte: int
    triangoli: int
    minimo: tuple[float, float, float]
    massimo: tuple[float, float, float]
    #: `binario` o `ascii`. FreeCAD (`Shape.exportStl`) scrive ASCII, trimesh
    #: binario: il laboratorio li rilegge tutti e due, e dice quale.
    formato: str = "binario"

    def dimensioni_mm(self) -> tuple[float, float, float]:
        return tuple(round(hi - lo, 3) for lo, hi in zip(self.minimo, self.massimo))


def _ascii(dati: bytes) -> np.ndarray:
    """I vertici di un STL ASCII: righe `vertex x y z`, tre per faccia. E'
    cio' che scrive `Shape.exportStl` di FreeCAD — trovato dal primo test
    dal vivo, che vedeva 235.812 byte per una piastra con un foro e un
    lettore che diceva «sembra un STL ASCII» e si fermava li'."""
    punti: list[tuple[float, float, float]] = []
    try:
        for riga in dati.decode("ascii", errors="strict").splitlines():
            parti = riga.split()
            if len(parti) == 4 and parti[0] == "vertex":
                punti.append((float(parti[1]), float(parti[2]), float(parti[3])))
    except (UnicodeDecodeError, ValueError) as exc:
        raise StlIllegibile(f"STL ASCII malformato: {exc}") from exc
    if not punti:
        raise StlIllegibile("zero triangoli: non e' un solido")
    if len(punti) % 3:
        raise StlIllegibile(f"STL ASCII con {len(punti)} vertici, non multipli di tre")
    v = np.asarray(punti, dtype="<f4").reshape(-1, 3, 3)
    if not np.isfinite(v).all():
        raise StlIllegibile("un vertice non e' finito")
    return v


def _grezzo(percorso: Path) -> tuple[bytes, np.ndarray, str]:
    dati = Path(percorso).read_bytes()
    corto = len(dati) < INTESTAZIONE + 4
    n = 0 if corto else struct.unpack_from("<I", dati, INTESTAZIONE)[0]
    attesi = INTESTAZIONE + 4 + n * BYTE_PER_TRIANGOLO
    if corto or len(dati) != attesi:
        # Un STL ASCII comincia con `solid` e non torna mai coi conti del
        # binario: si legge come testo. Un binario puo' cominciare con `solid`
        # anche lui — alcuni esportatori lo fanno — ma allora torna coi conti
        # e non passa di qui.
        if dati[:5] == b"solid":
            return dati, _ascii(dati), "ascii"
        if corto:
            raise StlIllegibile(f"{len(dati)} byte: meno di un'intestazione STL")
        raise StlIllegibile(
            f"dichiara {n} triangoli, cioe' {attesi} byte, e ne ha {len(dati)}")
    if n == 0:
        raise StlIllegibile("zero triangoli: non e' un solido")
    record = np.frombuffer(dati, dtype=_RECORD, count=n, offset=INTESTAZIONE + 4)
    v = record["v"]
    if not np.isfinite(v).all():
        raise StlIllegibile("un vertice non e' finito")
    return dati, v, "binario"


def leggi(percorso: Path) -> LetturaStl:
    """Conta e misura, senza costruire niente."""
    dati, v, formato = _grezzo(percorso)
    piatto = v.reshape(-1, 3)
    lo = piatto.min(axis=0)
    hi = piatto.max(axis=0)
    return LetturaStl(byte=len(dati), triangoli=len(v),
                      minimo=(float(lo[0]), float(lo[1]), float(lo[2])),
                      massimo=(float(hi[0]), float(hi[1]), float(hi[2])),
                      formato=formato)


def vertici(percorso: Path) -> tuple[np.ndarray, np.ndarray]:
    """`(posizioni (N,3) float32, triangoli (M,3) uint32)` per l'anteprima.

    STL ripete ogni vertice per ogni triangolo che lo tocca: un cubo sono 36
    vertici per 8 punti. Si **unificano** i punti identici, perche' e' il numero
    di punti che il `qualityGate()` del renderer conta (§17.2), e contare tre
    volte lo stesso non e' densita', e' formato.
    """
    _, v, _ = _grezzo(percorso)
    piatto = v.reshape(-1, 3)
    unici, inversa = np.unique(piatto, axis=0, return_inverse=True)
    return (unici.astype(np.float32),
            inversa.reshape(-1, 3).astype(np.uint32))
