"""Tracker delle mani — SPEC §14, invariante 28.

MediaPipe HandLandmarker con **`delegate=CPU` esplicito**. Non e' un default su
cui contare: §14 punto 1 lo chiede scritto, e su una macchina con la GPU
occupata da altro (§9) un delegate implicito potrebbe finire in coda dietro a
un modello 3D.

## Tre regole sulla telecamera, imposte dal codice

`R53` del piano di fase, e ognuna e' una riga di codice, non una buona
intenzione:

1. **Si accende su richiesta.** `avvia()` apre il dispositivo; l'import di
   questo modulo no. Il core parte senza toccare la webcam.
2. **Si rilascia sempre**, anche su eccezione: `ferma()` sta in un `finally`,
   e `Tracker` e' un context manager perche' dimenticarsene sia difficile.
3. **Nessun fotogramma tocca il disco.** In questo file non esiste un percorso
   di scrittura: i frame vivono in memoria per il tempo di una inferenza e
   vengono sovrascritti dal successivo. Cio' che esce di qui sono **landmark
   normalizzati**, cioe' 21 terne di numeri fra 0 e 1 — non un'immagine.

## Import pigro

§4 avverte: «MediaPipe — roadmap incerta, Python <= 3.12, isolare dietro
interfaccia». `import mediapipe` costa centinaia di millisecondi e trascina
numpy, OpenCV e matplotlib. Qui si importa **dentro `avvia()`**: il core si
avvia, i test girano e `jarvis doctor` risponde anche su una macchina dove
MediaPipe non c'e'.
"""

from __future__ import annotations

import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

#: Il modello ufficiale di Google. Come per Vosk in Fase 3, si scarica al primo
#: uso: nessun binario di terzi nel repository.
MODELLO_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODELLO_NOME = "hand_landmarker.task"
#: Il float16 ufficiale pesa ~7,8 MB. Un file molto piu' piccolo e' quasi
#: sempre una pagina di errore salvata col nome giusto.
MODELLO_MIN_BYTE = 5_000_000

MANI_MAX = 2          # §14: la rotazione a due mani
FIDUCIA = 0.5
LARGHEZZA, ALTEZZA = 640, 480
FPS_RICHIESTI = 30    # §14.1

#: Sotto questa frazione degli fps richiesti, il ripiego si ANNUNCIA.
SOGLIA_ANNUNCIO = 0.7


@dataclass(frozen=True)
class Mano:
    """Una mano vista in un fotogramma.

    `punti` sono i 21 landmark di MediaPipe, gia' normalizzati fra 0 e 1 sul
    fotogramma. Restano normalizzati per tutta la catena: il core non sa quanto
    e' grande la finestra, e il renderer non sa quanto e' grande il fotogramma
    (R55 del piano di fase).
    """

    lato: str                       # "Left" | "Right", come lo dice MediaPipe
    punti: tuple[tuple[float, float, float], ...] = ()
    fiducia: float = 0.0

    # ⚠️ **Qui c'era `polso`, una proprieta' per `self.punti[0]`, ed e' TOLTA.**
    # Zero occorrenze di `.polso` in tutto il repository — misurato — mentre il
    # polso si legge otto volte come `m.punti[POLSO]` in `mapping.py`, che e' la
    # forma leggibile perche' sta accanto a `MEDIO_BASE`, `punta` e `nocca`.
    # Una scorciatoia per UN punto su ventuno non e' una scorciatoia: e' un
    # secondo modo di scrivere la stessa cosa, e chi legge deve chiedersi
    # perche' il polso ce l'abbia e le nocche no.


@dataclass
class Fotogramma:
    """Cosa il tracker ha visto, e quanto ci ha messo."""

    mani: list[Mano] = field(default_factory=list)
    ts: float = 0.0
    ms_inferenza: float = 0.0
    indice: int = 0


def percorso_modello(data_dir: Path) -> Path:
    return Path(data_dir) / "models" / MODELLO_NOME


def scarica_modello(data_dir: Path, url: str = MODELLO_URL) -> Path:
    """Scarica il modello se manca. Come Vosk in Fase 3.

    Verifica la DIMENSIONE e non solo l'esistenza: un download interrotto
    lascia un file valido come percorso e invalido come modello, e l'errore
    che ne uscirebbe parlerebbe di flatbuffer invece che di rete.
    """
    dest = percorso_modello(data_dir)
    if dest.exists() and dest.stat().st_size >= MODELLO_MIN_BYTE:
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("modello_gesture_scarico", url=url, dove=str(dest))
    parziale = dest.with_suffix(".parziale")
    with urllib.request.urlopen(url, timeout=60) as r, parziale.open("wb") as f:
        while blocco := r.read(1 << 16):
            f.write(blocco)

    # La dimensione PRIMA di cancellare: la prima versione la rileggeva dopo
    # l'unlink, e l'errore che doveva spiegare il problema ne diventava un
    # altro. L'ha trovato il test, non io.
    byte = parziale.stat().st_size
    if byte < MODELLO_MIN_BYTE:
        parziale.unlink(missing_ok=True)
        raise RuntimeError(
            f"il modello scaricato pesa {byte} byte: "
            "e' quasi certamente una pagina di errore, non un modello"
        )
    # Rinomina atomica: o c'e' il modello intero, o non c'e' niente.
    parziale.replace(dest)
    log.info("modello_gesture_pronto", byte=dest.stat().st_size)
    return dest


class TrackerMediaPipe:
    """L'implementazione del Protocol `HandTracker` di `platform/base.py`.

    Non e' un `Protocol` a caso: §4 mette MediaPipe fra le dipendenze con
    roadmap incerta, e il giorno in cui andra' sostituito il resto del sistema
    non deve accorgersene.
    """

    nome = "mediapipe"

    def __init__(self, data_dir: Path, dispositivo: int = 0,
                 mani_max: int = MANI_MAX, esposizione: float | None = None) -> None:
        """`esposizione` in unita' V4L2; `None` lascia l'automatico.

        Non e' un dettaglio di configurazione, e' il collo di bottiglia della
        fase. Vedi `_misura_cadenza()`.
        """
        self._data_dir = Path(data_dir)
        self._dispositivo = dispositivo
        self._mani_max = mani_max
        self._esposizione = esposizione
        self._camera: Any = None
        self._landmarker: Any = None
        self._indice = 0
        self._fps_camera = 0.0

    # ── disponibilita' ───────────────────────────────────────────────────────

    def disponibile(self) -> bool:
        """MediaPipe e' installato? Import pigro anche qui.

        Come `TesseractOcr.disponibile()` di Fase 6: l'assenza e' uno stato
        normale da annunciare, non un guasto da scoprire al primo uso.
        """
        try:
            import mediapipe  # noqa: F401
        except Exception:
            return False
        return True

    # ── ciclo di vita ────────────────────────────────────────────────────────

    def avvia(self) -> None:
        """Apre modello e telecamera. **Qui** si importa MediaPipe."""
        from mediapipe.tasks.python import BaseOptions            # noqa: PLC0415
        from mediapipe.tasks.python import vision                 # noqa: PLC0415
        import cv2                                                # noqa: PLC0415

        modello = scarica_modello(self._data_dir)
        opzioni = vision.HandLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=str(modello),
                # ⚠️ ESPLICITO — invariante 28 e §14.1. Non il default.
                delegate=BaseOptions.Delegate.CPU,
            ),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=self._mani_max,
            min_hand_detection_confidence=FIDUCIA,
            min_tracking_confidence=FIDUCIA,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(opzioni)

        self._camera = cv2.VideoCapture(self._dispositivo, cv2.CAP_V4L2)
        if not self._camera.isOpened():
            self.ferma()
            raise RuntimeError(f"telecamera {self._dispositivo} non apribile")
        self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, LARGHEZZA)
        self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTEZZA)
        self._camera.set(cv2.CAP_PROP_FPS, FPS_RICHIESTI)
        # Un fotogramma di buffer: con la coda piena si tracciano mani di
        # mezzo secondo fa, e l'isteresi di §14 diventa ritardo invece che
        # stabilita'.
        self._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if self._esposizione is not None:
            self._camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)   # 1 = manuale, V4L2
            self._camera.set(cv2.CAP_PROP_EXPOSURE, self._esposizione)

        self._fps_camera = self._misura_cadenza()
        log.info("gesture_camera_accesa", dispositivo=self._dispositivo,
                 delegate="CPU", mani_max=self._mani_max,
                 fps_camera=round(self._fps_camera, 1),
                 esposizione="manuale" if self._esposizione is not None else "automatica")

        if self._fps_camera < FPS_RICHIESTI * SOGLIA_ANNUNCIO:
            # ANNUNCIATO, mai subito in silenzio — la stessa regola del ripiego
            # vocale di §7.4 e di quello YouTube di Fase 6.
            log.warning(
                "gesture_cadenza_ridotta",
                fps=round(self._fps_camera, 1), richiesti=FPS_RICHIESTI,
                causa="probabile auto-esposizione: con poca luce la telecamera "
                      "allunga il tempo di posa e dimezza la cadenza",
                rimedio="TrackerMediaPipe(..., esposizione=100) per forzarla corta, "
                        "a costo di un'immagine piu' scura",
            )

    def _misura_cadenza(self) -> float:
        """Quanti fotogrammi al secondo da' DAVVERO questa telecamera.

        Non `CAP_PROP_FPS`: quello e' cio' che la telecamera dichiara, e sulla
        macchina di sviluppo dichiarava 30 mentre ne consegnava 12,5. La
        differenza non era MediaPipe — l'inferenza sta in 8,3 ms — ma
        l'auto-esposizione, che con poca luce allunga il tempo di posa.
        Misurato e' l'unico modo di saperlo.
        """
        for _ in range(8):        # scarto l'avvio
            self._camera.read()
        t0 = time.perf_counter()
        letti = 0
        for _ in range(20):
            ok, _f = self._camera.read()
            letti += int(ok)
        durata = time.perf_counter() - t0
        return letti / durata if durata > 0 else 0.0

    @property
    def fps_camera(self) -> float:
        """La cadenza misurata all'avvio. Zero se il tracker non e' avviato."""
        return self._fps_camera

    def ferma(self) -> None:
        """Rilascia tutto. Idempotente: si puo' chiamare due volte."""
        if self._camera is not None:
            self._camera.release()
            self._camera = None
            log.info("gesture_camera_spenta")
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def __enter__(self) -> TrackerMediaPipe:
        self.avvia()
        return self

    def __exit__(self, *_e: object) -> None:
        self.ferma()

    # ── il flusso ────────────────────────────────────────────────────────────

    def fotogrammi(self, quanti: int | None = None) -> Iterator[Fotogramma]:
        """Legge dalla telecamera e restituisce landmark, un fotogramma per volta.

        `quanti` esiste per la misura e per i test: senza, va finche' non lo si
        interrompe. Il frame non esce mai da questa funzione.
        """
        import cv2                                                # noqa: PLC0415
        import mediapipe as mp                                    # noqa: PLC0415

        if self._camera is None or self._landmarker is None:
            raise RuntimeError("tracker non avviato: chiamare avvia() o usare `with`")

        letti = 0
        while quanti is None or letti < quanti:
            ok, bgr = self._camera.read()
            if not ok:
                log.warning("fotogramma_non_letto")
                break
            letti += 1
            self._indice += 1

            # MediaPipe vuole RGB; OpenCV da' BGR. Una conversione, in memoria.
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            immagine = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            t0 = time.perf_counter()
            # In RunningMode.VIDEO il timestamp deve crescere in modo
            # monotono, in millisecondi: MediaPipe lo usa per il tracking fra
            # fotogrammi, ed e' cio' che rende stabile il riconoscimento.
            esito = self._landmarker.detect_for_video(immagine, self._indice * 33)
            ms = (time.perf_counter() - t0) * 1000

            mani = []
            for i, punti in enumerate(esito.hand_landmarks):
                lato = "Right"
                fiducia = 0.0
                if i < len(esito.handedness) and esito.handedness[i]:
                    lato = esito.handedness[i][0].category_name
                    fiducia = float(esito.handedness[i][0].score)
                mani.append(Mano(
                    lato=lato,
                    punti=tuple((float(p.x), float(p.y), float(p.z)) for p in punti),
                    fiducia=fiducia,
                ))

            yield Fotogramma(mani=mani, ts=time.time(), ms_inferenza=ms,
                             indice=self._indice)
            # `bgr` e `rgb` vengono sovrascritti al giro successivo: nessun
            # fotogramma sopravvive all'iterazione, e nessuno tocca il disco.
