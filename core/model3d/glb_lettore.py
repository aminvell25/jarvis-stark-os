"""Rilettura di un file GLB con la SOLA libreria standard — ADR-012, ADR-014.

⚠️ **Questo modulo non importa `trimesh`, e un test lo impone.** E' l'intera
ragione per cui esiste: chi scrive il file e' `trimesh`, e un verificatore che
rileggesse col medesimo codice proverebbe che il codice e' coerente con se'
stesso — «il verde e' una bugia con due firme», `core/tools/files.py`. Il campo
`fonte` di ADR-012 deve nominare qualcosa di diverso dal tool che verifica, e
qui la fonte e' il **formato**: `struct` per l'intestazione binaria e `json`
per il chunk, letti dal disco.

E' anche la ragione per cui `pygltflib` non e' entrato fra le dipendenze
(§17.3): sarebbe una seconda libreria che sa di glTF, e la sua indipendenza
dallo scrittore sarebbe una supposizione invece di un fatto.

Il formato, dalla specifica glTF 2.0, e' venti righe:

    intestazione   magic "glTF" | versione uint32 | lunghezza totale uint32
    chunk JSON     lunghezza uint32 | tipo 0x4E4F534A | testo
    chunk BIN      lunghezza uint32 | tipo 0x004E4942 | byte
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"glTF"
TIPO_JSON = 0x4E4F534A
TIPO_BIN = 0x004E4942

#: Un GLB piu' grande di cosi' non lo produce nessun generatore
#: dell'allowlist: 20.000 vertici sono ~1 MB. Il tetto esiste perche' il
#: verificatore legge il chunk JSON in memoria, e un file ostile non deve
#: poterlo riempire.
MAX_BYTE = 64 * 1024 * 1024


class GlbIllegibile(ValueError):
    """Il file non e' un GLB valido. Non si solleva verso l'LLM: il
    verificatore la trasforma in un `osservato` che non combacia."""


@dataclass(frozen=True)
class LetturaGlb:
    """Cio' che il disco dice del file, senza chiedere niente a chi l'ha scritto."""

    byte: int
    versione: int
    lunghezza_dichiarata: int
    #: Vertici, dall'accessor `POSITION` della prima primitiva.
    vertici: int
    #: `min` e `max` dell'accessor, **nelle unita' del file** (metri).
    minimo: tuple[float, float, float]
    massimo: tuple[float, float, float]
    #: Quello che il file dice di se': `asset.extras`, dove il tool scrive i
    #: parametri in millimetri. Si LEGGE e non si crede: e' l'unica parte che
    #: viene dallo scrittore, e il verificatore non la usa come prova.
    extras: dict

    @property
    def coerente(self) -> bool:
        """La lunghezza dichiarata nell'intestazione e' quella del file."""
        return self.lunghezza_dichiarata == self.byte

    def dimensioni_mm(self) -> tuple[float, float, float]:
        """Il bbox dai `min`/`max` dell'accessor, riportato in millimetri.

        La conversione e' l'inversa di quella dell'export (§17.3): glTF e' in
        metri, il progetto in millimetri.
        """
        return tuple(round((a - b) * 1000.0, 6)
                     for a, b in zip(self.massimo, self.minimo, strict=True))


def leggi(percorso: str | Path) -> LetturaGlb:
    """Apre il GLB e ne estrae cio' che serve a verificarlo. Solleva
    `GlbIllegibile` su qualunque cosa non torni."""
    p = Path(percorso)
    dati = p.read_bytes()
    if len(dati) > MAX_BYTE:
        raise GlbIllegibile(f"{len(dati)} byte: oltre il tetto di {MAX_BYTE}")
    if len(dati) < 20:
        raise GlbIllegibile(f"{len(dati)} byte: troppo corto per un GLB")
    magic, versione, lunghezza = struct.unpack_from("<4sII", dati, 0)
    if magic != MAGIC:
        raise GlbIllegibile(f"magic {magic!r}, atteso {MAGIC!r}")
    if versione != 2:
        raise GlbIllegibile(f"versione glTF {versione}, attesa 2")

    testo = None
    off = 12
    while off + 8 <= len(dati):
        lung, tipo = struct.unpack_from("<II", dati, off)
        corpo = dati[off + 8: off + 8 + lung]
        if len(corpo) < lung:
            raise GlbIllegibile(f"chunk troncato a {off}: {len(corpo)} byte su {lung}")
        if tipo == TIPO_JSON and testo is None:
            testo = corpo
        off += 8 + lung
    if testo is None:
        raise GlbIllegibile("nessun chunk JSON")
    try:
        doc = json.loads(testo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GlbIllegibile(f"chunk JSON illeggibile: {exc}") from exc

    try:
        primitiva = doc["meshes"][0]["primitives"][0]
        acc = doc["accessors"][primitiva["attributes"]["POSITION"]]
        vertici = int(acc["count"])
        minimo = tuple(float(v) for v in acc["min"])
        massimo = tuple(float(v) for v in acc["max"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        # `min`/`max` sono OBBLIGATORI sull'accessor POSITION per la specifica
        # glTF 2.0, ed e' per questo che GLB e' il formato della prima fetta
        # (§17.3): sono la misura del pezzo scritta nel file, indipendente dai
        # byte del buffer.
        raise GlbIllegibile(f"accessor POSITION assente o incompleto: {exc}") from exc
    if len(minimo) != 3 or len(massimo) != 3:
        raise GlbIllegibile(f"accessor POSITION non e' 3D: min {minimo}, max {massimo}")

    return LetturaGlb(
        byte=len(dati), versione=versione, lunghezza_dichiarata=lunghezza,
        vertici=vertici, minimo=minimo, massimo=massimo,
        extras=dict((doc.get("asset") or {}).get("extras") or {}),
    )
