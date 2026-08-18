"""Chi parla, e perche' — SPEC §7.3, §8, invariante 12.

> «Deepgram e' il provider vocale primario; Whisper e Kokoro sono fallback
> automatico su errore, chiave mancante o rete assente. **Il fallback va sempre
> ANNUNCIATO, mai silenzioso.**»

L'annuncio non e' una cortesia: senza, l'utente sente una voce diversa o una
trascrizione peggiore e non sa perche'. E' lo stesso principio di §16 —
*nessuna soglia agisce senza annunciarlo*.

**Reso strutturale.** `Scelta` porta il provider E l'annuncio insieme: non
esiste un modo di ottenere un provider di ripiego senza ricevere anche la frase
da dire. Un test lo impone, perche' e' esattamente il tipo di regola che si
perde quando qualcuno aggiunge un terzo provider di fretta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

log = structlog.get_logger(__name__)


class Motivo:
    OK = "primario disponibile"
    CHIAVE_ASSENTE = "chiave assente"
    ERRORE = "il primario ha fallito"
    CONFIGURATO = "ripiego richiesto dalle impostazioni"


@dataclass(frozen=True)
class Scelta:
    """Un provider e, se non e' il primario, la frase che lo annuncia."""

    provider: Any
    primario: bool
    motivo: str
    annuncio: str | None

    def __post_init__(self) -> None:
        # Invariante 12, imposto qui: un ripiego senza annuncio non si
        # costruisce nemmeno.
        if not self.primario and not self.annuncio:
            raise ValueError(
                "un provider di ripiego senza annuncio viola l'invariante 12: "
                "il fallback va sempre annunciato, mai silenzioso"
            )


def _annuncio_stt(motivo: str, nome: str) -> str:
    if motivo == Motivo.CHIAVE_ASSENTE:
        return (f"Signore, non trovo la chiave del servizio vocale. "
                f"Ascolto in locale con {nome}.")
    if motivo == Motivo.ERRORE:
        return f"Signore, il servizio vocale non risponde. Passo a {nome} in locale."
    return f"Signore, ascolto in locale con {nome}."


def _annuncio_tts(motivo: str, nome: str) -> str:
    if motivo == Motivo.CHIAVE_ASSENTE:
        return f"Signore, non trovo la chiave del servizio vocale. Parlo con la voce di ripiego."
    if motivo == Motivo.ERRORE:
        return "Signore, il servizio vocale non risponde. Passo alla voce di ripiego."
    return "Signore, uso la voce di ripiego."


def scegli(
    primario: Any | None,
    ripiego: Any,
    chiave_presente: bool,
    preferisci_primario: bool,
    tipo: str,
    errore_primario: bool = False,
) -> Scelta:
    """Decide, e produce l'annuncio quando serve.

    `primario` puo' essere `None` — non costruito perche' la chiave manca — e
    in quel caso non c'e' scelta da fare, solo una da dichiarare.
    """
    annuncia = _annuncio_stt if tipo == "stt" else _annuncio_tts

    if errore_primario:
        motivo = Motivo.ERRORE
    elif not chiave_presente:
        motivo = Motivo.CHIAVE_ASSENTE
    elif not preferisci_primario:
        motivo = Motivo.CONFIGURATO
    else:
        motivo = Motivo.OK

    if motivo == Motivo.OK and primario is not None:
        log.info("provider_scelto", tipo=tipo, provider=primario.name, primario=True)
        return Scelta(provider=primario, primario=True, motivo=motivo, annuncio=None)

    log.warning("provider_di_ripiego", tipo=tipo, provider=ripiego.name, motivo=motivo)
    return Scelta(provider=ripiego, primario=False, motivo=motivo,
                  annuncio=annuncia(motivo, ripiego.name))
