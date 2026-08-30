"""La traccia: che cosa ha cominciato, e come si ricongiunge — ADR-011.

## Perche' esiste

Il 30 agosto 2026, dato il diario di una giornata, **non esisteva il modo di
rispondere alla domanda «che cosa e' successo in quel turno»**. `annota(flusso,
**campi)` (`core/diario.py:89`) non portava nessun identificatore e
`registry.invoke` nemmeno: il wake, la trascrizione, la classificazione T0, la
chiamata al tool e la riga del diario erano righe che non si toccavano.

Il pezzo pero' c'era gia', e funzionava. `core/tools/confirm.py:71` mette un
`uuid4().hex` su `Piano` — dataclass frozen — e lo propaga fino a `fs.result` e
ai log; `core/engine.py:322` fa lo stesso con `_catture`, e il commento accanto
dice perche': *«senza correlazione due domande vicine si scambierebbero le
risposte»*. La correlazione nel progetto **c'era, confinata alle conferme
distruttive**. Qui si generalizza quella forma.

⚠️ **`Piano.id` non e' una traccia, ed e' la ragione per cui questo file esiste
invece di riusarlo.** Un `Piano` non porta un'origine, nasce DENTRO `invoke()`
— cioe' dopo che il turno e' gia' cominciato — e muore quando la conferma si
chiude (`confirm.py:152-153`). Serve un identificatore che nasca al principio e
sopravviva a tutto cio' che quel principio scatena.

## Che cosa NON e'

**Non e' un task e non e' un contesto.** Non porta stato, non porta storia, non
porta obiettivi: e' un identificatore e la sua origine, e l'invariante 17 —
«non duplicare la gestione del contesto di T1» — resta intatto perche' non c'e'
niente da duplicare. I campi sono **tre**, e un test lo pinna: il quarto campo
che qualcuno vorra' aggiungere sara' stato, e questa smettera' di essere una
traccia.

## Esplicita nel dominio, implicita solo nei log

ADR-011 sceglie l'opzione A — l'id passa **per parametro** — con una sola
concessione ai `contextvars`, che non e' un compromesso ma una divisione di
responsabilita':

    dominio  (diario, ToolResult, initiatives/)   esplicito, per parametro
    log                                           structlog.contextvars

La ragione e' misurabile e sta nel codice: `core/engine.py:2067` porta il gesto
riconosciuto dal thread di MediaPipe al loop con `call_soon_threadsafe`, che
**non copia il contesto**. Una traccia affidata ai soli `contextvars` sparirebbe
li' senza un errore, producendo righe senza id — e il diario e' proprio la cosa
che non funzionerebbe piu'. Un difetto silenzioso e' peggiore di uno rumoroso.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import StrEnum

#: Quanto e' lungo l'id. Dodici esadecimali: il diario si legge a occhio, e un
#: uuid intero sfonderebbe la riga senza aggiungere niente — 48 bit bastano
#: largamente per una giornata di turni.
LUNGHEZZA_ID = 12


class Origine(StrEnum):
    """I **cinque** modi in cui qualcosa comincia in questo sistema.

    E' un'allowlist, come i flussi del diario e come il registro dei tool: un
    elenco chiuso, non una convenzione. Un `StrEnum` e non una `str` libera
    perche' e' cosi' che l'elenco diventa un TIPO — e un tipo si pinna con un
    test, mentre una stringa libera si allunga in silenzio.

    ⚠️ **Non sono sei.** La prima stesura di ADR-011 elencava anche «testo dalla
    scrivania», e quel punto d'ingresso **non esiste**: `core/ws_server.py`
    accetta cinque tipi di messaggio provati uno per uno, e `app/preload.js`
    espone quattro verbi dichiarando che restano quattro *«finche' qualcuno non
    dice perche' ne serve una»*. L'assenza del testo e' una decisione presa, non
    una dimenticanza, e il documento e' stato corretto invece di inventare una
    superficie per far tornare il numero.

    Un valore nuovo qui dentro senza un produttore che lo emetta e' un test
    rosso, non una svista: vedi `tests/test_la_traccia_non_si_perde.py`.
    """

    #: Una frase di wake riconosciuta. `core/voice/pipeline.py`, `_turno()`.
    VOCE = "voce"
    #: Un gesto passato dall'isteresi. `core/engine.py`, `_gesture_intento()`.
    GESTURE = "gesture"
    #: Una ronda di protocollo. `core/engine.py`, `_ronda_di()`.
    PROTOCOLLO = "protocollo"
    #: Uno dei messaggi che la scrivania puo' mandare. Oggi: `ui.imposta`.
    UI = "ui"
    #: Una scrivania si e' collegata: stato iniziale e resoconto al risveglio.
    AVVIO = "avvio"


@dataclass(frozen=True, slots=True)
class Traccia:
    """Un identificatore, la sua origine, e il momento in cui e' cominciato.

    `frozen` per la stessa ragione di `Piano`: cio' che viaggia attraverso mezzo
    sistema non deve poter cambiare a meta' strada. `slots` perche' se ne crea
    una per turno e non costa niente farlo bene.
    """

    #: `uuid4().hex[:12]`. **Non derivato dal tempo**: due turni nello stesso
    #: millisecondo collidono, e l'ora di sistema puo' saltare all'indietro.
    id: str
    origine: Origine
    #: ⚠️ **`time.monotonic()`, non `time.time()`.** Serve per la DURATA, non per
    #: l'ora: l'ora della riga ce l'ha gia' il diario, in orologio di parete.
    #: Mescolare i due orologi nella stessa sottrazione e' un errore che questo
    #: progetto ha gia' fatto tre volte — l'ultima in `Trigger.aperto_a`, che
    #: stampo' «cinquantasei anni» di latenza di risveglio.
    t0: float

    @classmethod
    def nuova(cls, origine: Origine | str) -> "Traccia":
        """Una traccia nuova. **Solo in un punto d'ingresso.**

        `Origine(origine)` alza su un nome inventato invece di accettarlo: e' la
        stessa scelta del diario davanti a un flusso ignoto e del registry
        davanti a un tool non registrato. Un'origine sbagliata renderebbe
        illeggibile il registro senza che nessuno se ne accorga.
        """
        return cls(id=uuid.uuid4().hex[:LUNGHEZZA_ID],
                   origine=Origine(origine),
                   t0=time.monotonic())

    @property
    def durata_ms(self) -> float:
        """Da quanto e' cominciato cio' che questa traccia identifica.

        Sull'orologio monotono, quindi resta vera anche se `ntp` sposta l'ora
        di sistema in mezzo al turno.
        """
        return (time.monotonic() - self.t0) * 1000.0
