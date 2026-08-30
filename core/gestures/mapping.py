"""Dai landmark all'intento — SPEC §14, invariante 27.

## Due allowlist, e nessuna via di mezzo

§14 punto 2: «Stessa allowlist dei comandi vocali. Una gesture emette un
intento sul bus, come T0».

Ma gli intenti di T0 non sono tutti tool: `open_panel` non e' nell'allowlist
del registry — e' un'azione del renderer. Quindi le strade sono due, ed
entrambe sono **allowlist**, mai un ramo che lascia passare il resto:

    intento che nomina un TOOL   -> registry.invoke_da_gesture(), che rifiuta
                                    tutto cio' che non e' gesture_allowed
    intento di INTERFACCIA       -> deve stare in INTENTI_UI, che sono i
                                    quattro della tabella di §14 e nessun altro

Un intento che non e' ne' l'uno ne' l'altro **solleva**. Non «viene ignorato»:
un intento sconosciuto sul percorso delle gesture significa che qualcuno ha
scritto una mappatura che non doveva esistere, e va visto.

## L'isteresi, e perche' conta piu' del riconoscitore

§14: «gesto stabile per 5 frame (~166 ms)». Il motivo sta una riga sopra, nel
punto 3: «un falso positivo e' indistinguibile da un comando».

`Isteresi` fa due cose, e la seconda si dimentica sempre:

  1. non emette finche' il gesto non si ripete per N fotogrammi;
  2. non riemette finche' il gesto non si INTERROMPE. Senza questa, una mano
     ferma in pizzico per due secondi produrrebbe sessanta intenti.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.gestures.tracker import Fotogramma, Mano
from core.tools import registry

log = structlog.get_logger(__name__)

#: Indici dei landmark MediaPipe che servono qui. Scritti per nome perche'
#: `punti[8]` fra sei mesi non dice niente a nessuno.
POLSO = 0
POLLICE = 4
INDICE = 8
MEDIO = 12
ANULARE = 16
MIGNOLO = 20
MEDIO_BASE = 9
NOCCHE = (5, 9, 13, 17)
PUNTE = (INDICE, MEDIO, ANULARE, MIGNOLO)

FRAME_ISTERESI = 5      # §14
#: Storia per i gesti di MOVIMENTO. Dodici fotogrammi = 400 ms a 30fps.
#:
#: I due gesti di movimento non hanno lo stesso tempo, e trattarli uguale li
#: rompe entrambi. Una spinta laterale e' uno scatto: si esaurisce in un
#: quarto di secondo, e guardare piu' indietro vuol dire scambiare per spinta
#: una mano che si e' spostata piano. Una rotazione a due mani e' un gesto
#: lento: in otto fotogrammi non accumula abbastanza angolo, e infatti il
#: corpus non la vedeva. Storia lunga, e la spinta ne guarda solo la coda.
FINESTRA = 12
FINESTRA_SPINTA = 8

#: Soglie, tutte RELATIVE alla dimensione della mano: la stessa gesture a
#: quaranta centimetri e a un metro dalla telecamera deve valere uguale.
PIZZICO = 0.45
DITO_ESTESO = 1.25
SPINTA = 0.9            # spostamento del polso, in dimensioni-mano
ROTAZIONE_GRADI = 22.0

#: I quattro intenti di interfaccia della tabella di §14. Allowlist.
INTENTI_UI = frozenset({
    "sposta_pannello",       # pizzico + trascina
    "ruota_mesh",            # rotazione a due mani
    "espandi_pannello",      # palmo aperto
    "cambia_workspace",      # spinta laterale
})


class IntentoNonAmmesso(Exception):
    """Una mappatura punta a qualcosa che le gesture non possono fare."""


# ── geometria ────────────────────────────────────────────────────────────────

def _dist(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.dist(a[:2], b[:2])


def dimensione(m: Mano) -> float:
    """Polso -> base del medio. E' l'unita' di misura di tutto il resto."""
    d = _dist(m.punti[POLSO], m.punti[MEDIO_BASE])
    return d if d > 1e-6 else 1e-6


def pizzico(m: Mano) -> bool:
    """Pollice e indice che si toccano, in proporzione alla mano."""
    return _dist(m.punti[POLLICE], m.punti[INDICE]) / dimensione(m) < PIZZICO


def palmo_aperto(m: Mano) -> bool:
    """Quattro dita estese: la punta piu' lontana dal polso della nocca.

    Non si misura l'angolo delle falangi: con la mano di taglio quel conto
    diventa instabile, mentre il rapporto delle distanze regge.
    """
    d = dimensione(m)
    return all(
        _dist(m.punti[POLSO], m.punti[punta]) / d
        > _dist(m.punti[POLSO], m.punti[nocca]) / d * DITO_ESTESO
        for punta, nocca in zip(PUNTE, NOCCHE, strict=True)
    )


def _angolo(a: Mano, b: Mano) -> float:
    """L'inclinazione della retta fra i due polsi, in gradi."""
    (ax, ay, *_), (bx, by, *_) = a.punti[POLSO], b.punti[POLSO]
    return math.degrees(math.atan2(by - ay, bx - ax))


# ── riconoscimento ───────────────────────────────────────────────────────────

@dataclass
class Riconoscitore:
    """Da un fotogramma al nome del gesto, con la storia che serve.

    Due gesti sono statici — si vedono in un fotogramma solo — e due sono di
    movimento, e hanno bisogno di ricordare dov'era la mano.
    """

    storia: deque[Fotogramma] = field(default_factory=lambda: deque(maxlen=FINESTRA))

    def __call__(self, f: Fotogramma) -> str | None:
        self.storia.append(f)
        if not f.mani:
            return None

        # Due mani: la rotazione ha la precedenza, perche' con due mani in
        # scena un pizzico casuale dell'una non deve rubare il gesto.
        if len(f.mani) >= 2 and self._rotazione():
            return "ruota_mesh"

        m = f.mani[0]
        if pizzico(m):
            return "sposta_pannello"
        if self._spinta():
            return "cambia_workspace"
        if palmo_aperto(m):
            return "espandi_pannello"
        return None

    def _spinta(self) -> bool:
        """Il polso che attraversa lateralmente, in dimensioni-mano."""
        con_mano = [f for f in self.storia if f.mani][-FINESTRA_SPINTA:]
        if len(con_mano) < 3:
            return False
        primo, ultimo = con_mano[0].mani[0], con_mano[-1].mani[0]
        dx = abs(ultimo.punti[POLSO][0] - primo.punti[POLSO][0])
        dy = abs(ultimo.punti[POLSO][1] - primo.punti[POLSO][1])
        # LATERALE: se sale piu' di quanto scorre, non e' una spinta.
        return dx / dimensione(ultimo) > SPINTA and dx > dy

    def _rotazione(self) -> bool:
        """L'inclinazione fra i due polsi che cambia dentro la finestra."""
        due = [f for f in self.storia if len(f.mani) >= 2]
        if len(due) < 3:
            return False
        a = _angolo(due[0].mani[0], due[0].mani[1])
        b = _angolo(due[-1].mani[0], due[-1].mani[1])
        scarto = abs((b - a + 180) % 360 - 180)
        return scarto > ROTAZIONE_GRADI


# ── isteresi ─────────────────────────────────────────────────────────────────

@dataclass
class Isteresi:
    """Stabile per N fotogrammi, e **una volta sola** finche' non si stacca."""

    frame: int = FRAME_ISTERESI
    _corrente: str | None = None
    _conteggio: int = 0
    _gia_emesso: bool = False

    @property
    def conteggio(self) -> int:
        return self._conteggio

    @property
    def gesto(self) -> str | None:
        return self._corrente

    def alimenta(self, gesto: str | None) -> str | None:
        """Il gesto da emettere adesso, oppure `None`."""
        if gesto != self._corrente:
            self._corrente = gesto
            self._conteggio = 1 if gesto else 0
            self._gia_emesso = False
            return None

        if gesto is None:
            return None

        self._conteggio += 1
        if self._conteggio >= self.frame and not self._gia_emesso:
            self._gia_emesso = True
            return gesto
        return None


# ── emissione ────────────────────────────────────────────────────────────────

async def emetti(intento: str, args: dict[str, Any] | None = None,
                 pubblica: Callable[[dict], Awaitable[None]] | None = None,
                 *, traccia=None) -> dict:
    """L'unica uscita delle gesture verso il resto del sistema.

    Le due allowlist dell'intestazione, in quest'ordine: prima si guarda se
    l'intento e' un tool — perche' un tool ha conseguenze — poi se e' una delle
    quattro azioni di interfaccia. Se non e' nessuno dei due, si solleva.

    ⚠️ **La traccia si inoltra e basta: qui NON si annota** (ADR-011). La riga
    di diario del gesto la scrive `core/engine.py`, che possiede il diario,
    per la stessa ragione per cui `pubblica` arriva per funzione — questo
    modulo non deve sapere che cosa sia un socket, e non deve sapere che cosa
    sia un registro.

    Non annotata nel tipo: `core.gestures` non importa `core.traccia` per la
    stessa ragione di `core/protocolli.py`. Riceve, non va a prendere.
    """
    if intento in registry.names():
        # Fail-closed: `invoke_da_gesture` rifiuta tutto cio' che non e'
        # dichiarato `gesture_allowed` (invariante 27).
        esito = await registry.invoke_da_gesture(intento, args or {},
                                                 traccia=traccia)
        msg = {"topic": "gesture.intent", "intento": intento, "tipo": "tool",
               "ok": esito.ok}
    elif intento in INTENTI_UI:
        msg = {"topic": "gesture.intent", "intento": intento, "tipo": "ui",
               "args": args or {}}
    else:
        raise IntentoNonAmmesso(
            f"l'intento {intento!r} non e' ne' un tool dell'allowlist ne' uno "
            f"dei quattro intenti di interfaccia di §14 ({sorted(INTENTI_UI)}). "
            "Una mappatura che ci punta e' un errore di cablaggio."
        )

    log.info("gesture_intento", intento=intento, tipo=msg["tipo"])
    if pubblica is not None:
        await pubblica(msg)
    return msg
