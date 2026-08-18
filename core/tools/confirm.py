"""Conferma umana per i tool distruttivi — SPEC §6.2, invariante 3.

```
proposta -> validazione -> fs.confirm_request col PIANO RISOLTO
-> l'utente vede i path assoluti risolti -> conferma -> esegue -> fs.result
                                         -> rifiuto  -> ToolResult(ok=False)
```

Quattro proprieta', e la quarta e' quella che non si vede.

**`request_id` generato dal core.** Il renderer risponde a domande, non le
inventa: senza, una risposta qualunque autorizzerebbe qualunque cosa.

**Una risposta sola.** Senza, la stessa conferma riautorizza l'operazione a
ripetizione.

**Scadenza.** Senza, una conferma di stamattina autorizza un'operazione di
stasera.

**Il piano e' congelato e risolto.** Questa e' la meno ovvia. Se l'esecuzione
ricavasse di nuovo i percorsi dagli argomenti, un symlink sostituito FRA la
conferma e l'esecuzione cambierebbe cio' che accade: l'utente leggerebbe il
percorso giusto, confermerebbe, e verrebbe eseguita un'altra cosa. Si esegue il
piano congelato — `Piano` e `Operazione` sono `frozen` e portano `Path` gia'
risolti — mai gli argomenti.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import structlog

log = structlog.get_logger(__name__)

#: Quanto vive una richiesta senza risposta. Due minuti: abbastanza perche'
#: l'utente legga un piano di duecento righe, poco perche' una conferma
#: dimenticata non resti valida a lungo.
TTL_DEFAULT = 120.0


@dataclass(frozen=True)
class Operazione:
    """Una singola azione, coi percorsi GIA' RISOLTI."""

    tipo: str
    sorgente: Path | None = None
    destinazione: Path | None = None
    dettaglio: str = ""

    def descrivi(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "sorgente": str(self.sorgente) if self.sorgente else None,
            "destinazione": str(self.destinazione) if self.destinazione else None,
            "dettaglio": self.dettaglio,
        }


@dataclass(frozen=True)
class Piano:
    """Cio' che verra' eseguito, se l'utente approva. Immutabile."""

    tool: str
    riepilogo: str
    operazioni: tuple[Operazione, ...]
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def descrivi(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tool": self.tool,
            "riepilogo": self.riepilogo,
            "operazioni": [o.descrivi() for o in self.operazioni],
            "totale": len(self.operazioni),
        }


class Esito:
    APPROVATO = "approvato"
    RIFIUTATO = "rifiutato"
    SCADUTO = "scaduto"


class ConfirmBroker:
    """Pone la domanda, attende, e non la pone due volte."""

    def __init__(
        self,
        pubblica: Callable[[dict[str, Any]], Any],
        ttl: float = TTL_DEFAULT,
    ) -> None:
        self._pubblica = pubblica
        self._ttl = ttl
        self._pendenti: dict[str, asyncio.Future[bool]] = {}
        self._piani: dict[str, Piano] = {}

    @property
    def pendenti(self) -> list[Piano]:
        return list(self._piani.values())

    async def richiedi(self, piano: Piano) -> str:
        """Pubblica la richiesta e attende. Ritorna un valore di `Esito`."""
        loop = asyncio.get_running_loop()
        futuro: asyncio.Future[bool] = loop.create_future()
        self._pendenti[piano.id] = futuro
        self._piani[piano.id] = piano

        log.info(
            "conferma_richiesta",
            id=piano.id,
            tool=piano.tool,
            operazioni=len(piano.operazioni),
        )
        await self._pubblica({
            "topic": "fs.confirm_request",
            "scade_fra_s": self._ttl,
            **piano.descrivi(),
        })

        try:
            approvato = await asyncio.wait_for(futuro, timeout=self._ttl)
        except asyncio.TimeoutError:
            log.warning("conferma_scaduta", id=piano.id, tool=piano.tool)
            return Esito.SCADUTO
        finally:
            # Una domanda posta una volta si chiude una volta, qualunque sia
            # l'esito: scadenza compresa.
            self._pendenti.pop(piano.id, None)
            self._piani.pop(piano.id, None)

        log.info("conferma_risposta", id=piano.id, approvato=approvato)
        return Esito.APPROVATO if approvato else Esito.RIFIUTATO

    def rispondi(self, request_id: str, approvato: bool) -> bool:
        """Risponde a una richiesta pendente. `False` se non ce n'era una.

        Un id sconosciuto, gia' risposto o scaduto **non e' un errore**: e' il
        caso normale di un doppio clic o di una finestra rimasta aperta. Si
        ignora e si registra, non si solleva.
        """
        futuro = self._pendenti.get(request_id)
        if futuro is None or futuro.done():
            log.info("conferma_ignorata", id=request_id, motivo="sconosciuta o gia' chiusa")
            return False
        futuro.set_result(bool(approvato))
        return True
