"""OCR — SPEC §12, §4 (Tesseract v5). Dietro un'interfaccia, per §23.

Su Windows il binario si chiamera' diversamente e stara' altrove: l'invariante
29 vuole che la scelta viva qui e non sparsa nel codice applicativo.

⚠️ **Su questa macchina Tesseract NON e' installato.** Il modulo lo verifica
all'avvio e degrada ANNUNCIANDOLO — la stessa regola del ripiego vocale di
§7.4: mai un silenzio, mai fingere che sia andata come chiesto. La strada
principale di §12 non ne ha bisogno:

> «JARVIS conosce gia' il contenuto dei propri pannelli — e' lui a
> renderizzarli. Per la maggior parte delle domande non serve OCR, serve
> interrogare lo stato.»

    sudo apt install tesseract-ocr tesseract-ocr-ita
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

BINARIO = "tesseract"
LINGUA = "ita+eng"
TIMEOUT_S = 8.0


@dataclass(frozen=True)
class EsitoOcr:
    """Il testo, oppure il motivo per cui non c'e'.

    Non solleva: ARGUS sta su un percorso interattivo, e un'eccezione qui
    diventerebbe silenzio proprio mentre qualcuno sta chiedendo qualcosa.
    """

    ok: bool
    testo: str = ""
    annuncio: str = ""
    durata_ms: int = 0


class TesseractOcr:
    """L'implementazione Linux del Protocol `Ocr` di `core/platform/base.py`."""

    nome = "tesseract"

    def disponibile(self) -> bool:
        return shutil.which(BINARIO) is not None

    async def leggi(self, png: bytes, lingua: str = LINGUA) -> EsitoOcr:
        if not self.disponibile():
            # ANNUNCIATO, non silenzioso.
            return EsitoOcr(
                ok=False,
                annuncio=(
                    "Tesseract non e' installato: non posso leggere il testo dallo "
                    "schermo. Le domande sui pannelli di JARVIS funzionano lo stesso, "
                    "perche' non passano dall'OCR."
                ),
            )
        t0 = asyncio.get_running_loop().time()
        try:
            testo = await asyncio.to_thread(self._esegui, png, lingua)
        except Exception as exc:
            log.warning("ocr_fallito", errore=type(exc).__name__)
            return EsitoOcr(ok=False, annuncio=f"OCR fallito: {type(exc).__name__}")
        ms = int((asyncio.get_running_loop().time() - t0) * 1000)
        return EsitoOcr(ok=True, testo=testo, durata_ms=ms)

    def _esegui(self, png: bytes, lingua: str) -> str:
        """`tesseract IN out` con file temporanei.

        Passare l'immagine su stdin (`tesseract - -`) sarebbe piu' elegante ma
        non funziona con tutte le build; il file temporaneo funziona ovunque e
        vive qualche millisecondo.
        """
        with tempfile.TemporaryDirectory() as tmp:
            ingresso = Path(tmp) / "cattura.png"
            ingresso.write_bytes(png)
            r = subprocess.run(
                [BINARIO, str(ingresso), "stdout", "-l", lingua],
                capture_output=True, timeout=TIMEOUT_S,
            )
            if r.returncode != 0:
                raise RuntimeError(r.stderr.decode("utf-8", "replace")[:200])
            return r.stdout.decode("utf-8", "replace").strip()
