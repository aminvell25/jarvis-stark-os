"""Il tipo che esce da un generatore, e le regole che lo rendono verificabile.

`Modello` e' l'equivalente Python di cio' che `ui/src/three/geometry.js`
chiama `Geometria`: posizioni, indici, linee di costruzione, piu' il `bbox`
**dichiarato** e i `params` che l'hanno prodotto.

⚠️ **Il bbox e' DICHIARATO, non misurato.** §11.10 regola 7: un componente lo
dichiara e il gate lo verifica. Qui vale due volte, perche' il verificatore di
ADR-012 confronta l'atteso — calcolato dagli argomenti — con cio' che sta nel
file: se il bbox venisse dai vertici appena generati, il confronto direbbe
solo che il codice e' coerente con se' stesso.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

#: Il tetto, ed e' lo stesso del quality gate del renderer
#: (`ui/src/three/quality-gate.js`, `LIMITS.maxVertices`). Sta qui perche' un
#: modello che il renderer rifiuterebbe non deve nemmeno essere scritto: si
#: dice `ok=False` con la ragione, e non si decima in silenzio (§17.2).
MAX_VERTICI = 20_000

#: Il minimo del gate, per la stessa ragione.
MIN_VERTICI = 24

#: glTF prescrive i **metri**; il progetto lavora in **millimetri** (`CLAUDE.md`,
#: stile codice). La conversione sta in un posto solo, all'export, e i parametri
#: in mm viaggiano in `asset.extras`: un visualizzatore esterno deve vedere il
#: pezzo grande quanto e'.
MM_PER_METRO = 1000.0


class ModelloNonValido(ValueError):
    """Parametri che non producono un solido. Mai un'eccezione verso l'LLM:
    `core/tools/model3d.py` la traduce in `ToolResult(ok=False, error=...)`."""


@dataclass(frozen=True)
class Quota:
    """Una misura da scrivere accanto al pezzo, e dove attaccarla.

    ⚠️ **La sceglie il GENERATORE, non il pannello**, ed è la correzione del
    3 settembre 2026. Prima il pannello annotava sempre i tre lati del bounding
    box: su una piastra funziona, perché il bbox è il pezzo, e su una forma il
    cui ingombro sia un RISULTATO no — i tre numeri finiscono appesi ad angoli
    che stanno nel vuoto. Un disegno scrive le misure di progetto, e quali
    siano dipende dal pezzo.

    Chi conosce il pezzo è chi lo genera, e il renderer non deve indovinarlo.
    """

    #: Già formattato, unità comprese: e' il generatore a sapere se scrivere
    #: «120 mm», «Ø12» o «R24».
    testo: str
    #: Dove ancorarla, in millimetri nello spazio del pezzo.
    punto: tuple[float, float, float]


@dataclass(frozen=True)
class Modello:
    """Un solido parametrico in millimetri, pronto per il disco e per lo schermo.

    `posizioni` (N,3) e `triangoli` (M,3) sono gli stessi array che finiscono
    nel GLB e nel messaggio `model3d.preview`: una sorgente sola.
    """

    nome: str
    versione: str
    #: I parametri, in millimetri. Sono l'ATTESO del verificatore.
    params: dict[str, float]
    posizioni: np.ndarray          # (N, 3) float32, mm
    triangoli: np.ndarray          # (M, 3) uint32
    #: Il bounding box **dichiarato**, in mm — non misurato dai vertici.
    bbox: tuple[float, float, float]
    #: Le linee di costruzione di §11.10 regola 3: assi, raggi, quote. Coppie
    #: di indici in `posizioni`, oppure vuoto quando il componente non ne ha.
    linee: np.ndarray = field(default_factory=lambda: np.zeros((0, 2), np.uint32))
    #: Quanto il bbox DICHIARATO puo' stare sopra quello misurato, in mm, e
    #: **perche'**. Zero — il caso di `estrusione_45` — vuol dire che il bbox
    #: e' esatto: gli smussi tagliano verso l'interno e non spostano gli
    #: estremi. Un valore positivo si accompagna sempre a una ragione in
    #: `motivo_tolleranza`, ed e' la stessa deroga che `pointcloud.js`
    #: dichiara al gate del renderer: un campione discreto di una superficie
    #: continua non tocca i propri estremi.
    tolleranza_mm: float = 0.0
    motivo_tolleranza: str = ""
    #: §11.10 regola 3 — le quote, scelte dal generatore. Vuoto e' ammesso e
    #: significa «questo pezzo non ha una misura da mostrare», non «me ne sono
    #: dimenticato»: un test conta che ogni generatore dell'allowlist ne
    #: dichiari almeno una.
    quote: tuple[Quota, ...] = ()

    def __post_init__(self) -> None:
        if self.posizioni.ndim != 2 or self.posizioni.shape[1] != 3:
            raise ModelloNonValido(f"posizioni {self.posizioni.shape}, attese (N, 3)")
        if self.triangoli.ndim != 2 or self.triangoli.shape[1] != 3:
            raise ModelloNonValido(f"triangoli {self.triangoli.shape}, attesi (M, 3)")
        n = len(self.posizioni)
        if n < MIN_VERTICI:
            raise ModelloNonValido(f"vertici {n} < {MIN_VERTICI}: il gate lo rifiuterebbe")
        if n > MAX_VERTICI:
            raise ModelloNonValido(
                f"vertici {n} > {MAX_VERTICI}: il gate del renderer lo rifiuterebbe. "
                "Si dice, non si decima (§17.2)")
        if not np.isfinite(self.posizioni).all():
            raise ModelloNonValido("una posizione non e' finita")
        if len(self.triangoli) and int(self.triangoli.max()) >= n:
            raise ModelloNonValido(
                f"un triangolo cita il vertice {int(self.triangoli.max())} di {n}")
        if len(self.linee) and int(self.linee.max()) >= n:
            raise ModelloNonValido("una linea di costruzione cita un vertice che non c'e'")
        # §11.10 regola 7, imposta alla COSTRUZIONE e non lasciata al gate.
        #
        # ⚠️ Trovato da `scripts/orfani.py` il 2 settembre 2026: `bbox_combacia`
        # era chiamata solo dai test — «provato, mai congiunto». Il posto in cui
        # serve e' questo: un modello che dichiara un bbox diverso dai propri
        # vertici mente su se' stesso, e il verificatore di ADR-012 userebbe
        # quel numero come ATTESO. Il gate del renderer lo direbbe dopo, a file
        # gia' scritto e a conferma gia' data.
        if self.tolleranza_mm < 0:
            raise ModelloNonValido("una tolleranza negativa non significa niente")
        if self.tolleranza_mm > 0 and not self.motivo_tolleranza.strip():
            raise ModelloNonValido(
                "una tolleranza sul bbox senza una ragione scritta non e' una "
                "deroga, e' un criterio allentato in silenzio (§11.10 regola 7)")
        if not self.bbox_combacia():
            raise ModelloNonValido(
                f"il bbox dichiarato {self.bbox} non e' quello dei vertici "
                f"{self.bbox_misurato()} entro {self.tolleranza_mm} mm: "
                "§11.10 regola 7")

    @property
    def vertici(self) -> int:
        return len(self.posizioni)

    def bbox_misurato(self) -> tuple[float, float, float]:
        """Il bbox dei vertici veri. Serve al CONFRONTO col dichiarato — che e'
        §11.10 regola 7 — non a sostituirlo."""
        d = self.posizioni.max(axis=0) - self.posizioni.min(axis=0)
        return (float(d[0]), float(d[1]), float(d[2]))

    #: Quanto puo' scostare un bbox che si dichiara ESATTO. Non e' una deroga:
    #: e' il rumore del `float32`, tre ordini di grandezza sotto.
    ESATTO_MM: ClassVar[float] = 0.01

    def bbox_combacia(self) -> bool:
        """Il dichiarato e il misurato coincidono, entro la tolleranza
        DICHIARATA. Chiamata da `__post_init__`: un modello che mente sul
        proprio ingombro non si costruisce.

        ⚠️ Il confronto e' **a senso unico oltre lo zero**: il dichiarato puo'
        stare SOPRA il misurato — e' cio' che succede a un poligono inscritto
        in un cerchio — e non sotto. Un bbox dichiarato piu' PICCOLO dei
        vertici non e' una discretizzazione, e' un errore.
        """
        for dichiarato, misurato in zip(self.bbox, self.bbox_misurato(), strict=True):
            scarto = dichiarato - misurato
            if scarto < -self.ESATTO_MM:
                return False
            if scarto > self.tolleranza_mm + self.ESATTO_MM:
                return False
        return True

    @property
    def tolleranza_relativa(self) -> float:
        """La tolleranza in frazione dell'ingombro, che e' la forma che il
        `qualityGate()` del renderer si aspetta (`meta.bboxTolleranza`)."""
        if self.tolleranza_mm <= 0:
            return 0.0
        return max(self.tolleranza_mm / d for d in self.bbox if d > 0)

    def per_il_renderer(self) -> dict[str, Any]:
        """Il corpo di `model3d.preview`, senza il topic.

        Base64 come `ArgusCaptureResponse.png`: e' l'unica forma binaria che il
        socket gia' porta. A 20.000 vertici sono ~320 KB, e li regge.
        """
        return {
            "nome": self.nome,
            "versione": self.versione,
            "unita": "mm",
            "params": dict(self.params),
            "bbox": {"x": self.bbox[0], "y": self.bbox[1], "z": self.bbox[2]},
            "vertici": self.vertici,
            "triangoli": len(self.triangoli),
            # La deroga viaggia col pezzo: il gate del renderer la legge in
            # `meta.bboxTolleranza`, e senza rifiuterebbe per una
            # discretizzazione che il core ha gia' dichiarato in forma chiusa.
            "bbox_tolleranza": self.tolleranza_relativa,
            "motivo_tolleranza": self.motivo_tolleranza,
            "quote": [{"testo": q.testo, "punto": list(q.punto)} for q in self.quote],
            "posizioni_b64": _b64(self.posizioni.astype(np.float32)),
            "indici_b64": _b64(self.triangoli.astype(np.uint32)),
            "linee_b64": _b64(self.linee.astype(np.uint32)),
        }


def _b64(a: np.ndarray) -> str:
    """Little-endian esplicito: il renderer legge con `DataView`/`TypedArray`,
    e una macchina big-endian scriverebbe byte che il browser interpreta al
    contrario. Oggi non ne abbiamo, e non e' una ragione per lasciarlo implicito.
    """
    return base64.b64encode(a.astype(a.dtype.newbyteorder("<")).tobytes()).decode("ascii")
