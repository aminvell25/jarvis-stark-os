"""Il volume DI JARVIS — §7.6, invariante 29.

`set_volume` e `mute` sono nella grammatica T0 dalla Fase 3 e nel corpus delle
frasi etichettate, e **non avevano un esecutore**: `esegui_t0` li rifiutava con
«non e' ne' un'azione della scrivania ne' un tool dell'allowlist». JARVIS
riconosceva la frase e non faceva niente — il guasto piu' visibile all'uso, e
indistinguibile da «non mi ha sentito».

## ⚠️ Il volume e' DI JARVIS, non del sistema

`CLAUDE.md` apre dicendo che fuori dalla sua finestra non tocca nulla, e il
mixer di PipeWire e' fuori dalla sua finestra. «Volume 40» vuol dire che JARVIS
parla piu' piano, **non** che abbassa la musica che sta ascoltando — che e'
anche cio' che si intende dicendolo.

Implementato come guadagno sul PCM che JARVIS riproduce: non chiede permessi,
non tocca il mixer, e sparisce quando il processo finisce.

## Perche' `side_effect=False`

L'invariante 3 e la conferma di §6.2 esistono per le operazioni irreversibili
sui file di chi usa il sistema: mostrano il path risolto perche' una
cancellazione non si annulla. Il volume si annulla dicendo un altro numero, non
tocca il disco, e non esce dal processo. Chiedere una conferma a chi ha appena
detto «volume 40» sarebbe attrito senza protezione.

`gesture_allowed=False` invece **si', per ora**: l'invariante 27 vieta le
gesture solo sui `side_effect=True`, quindi qui sarebbe permesso — ma una mano
che passa davanti alla telecamera e zittisce JARVIS senza che nessuno l'abbia
chiesto e' esattamente il genere di sorpresa che §14 evita. Se un giorno servira'
sara' una decisione, non una svista.
"""

from __future__ import annotations

from collections.abc import Callable

import structlog
from pydantic import BaseModel, Field

from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

#: Sotto questo livello «alza» non ha un valore ovvio da cui ripartire.
LIVELLO_PREDEFINITO = 70


class SetVolumeArgs(BaseModel):
    #: Non `ge=0, le=100`: il corpus T0 contiene `("volume 250", ..., 100)` e
    #: la grammatica satura gia'. Un'iperbole non e' un errore di validazione.
    level: int


class VuotoArgs(BaseModel):
    """Nessun argomento."""


def register_audio_tools(audio: Callable[[], object]) -> None:
    """Registra i tool del volume legandoli a un `AudioIO`.

    ⚠️ **Per funzione e non per valore**, come le chiavi dei collector. Non e'
    simmetria: l'`AudioIO` si costruisce quando serve, e chiamarlo qui
    forzerebbe la costruzione alla registrazione dei tool — cioe' prima che la
    radice di composizione decida se la voce si accende. L'ha trovato un test
    che sostituiva la fabbrica: la sostituzione arrivava dopo, e l'oggetto era
    gia' quello vero.

    Quel che conta e' che sia lo **stesso** oggetto della pipeline vocale, o il
    guadagno vivrebbe su un'istanza che non riproduce niente — due meta'
    scollegate, il difetto ricorrente di questo progetto.
    """
    #: Il livello prima del muto, per poterci tornare. Vive qui e non
    #: nell'`AudioIO`: e' una comodita' dell'interfaccia vocale, non una
    #: proprieta' della scheda audio.
    stato = {"prima_del_muto": None}

    async def _set_volume(args: SetVolumeArgs) -> ToolResult:
        applicato = audio().imposta_volume(args.level)
        if applicato > 0:
            stato["prima_del_muto"] = None
        return ToolResult(ok=True, output={"volume": applicato})

    async def _mute(_args: VuotoArgs) -> ToolResult:
        if audio().volume == 0:
            return ToolResult(ok=True, output={"volume": 0, "gia_muto": True})
        stato["prima_del_muto"] = audio().volume
        return ToolResult(ok=True, output={"volume": audio().imposta_volume(0)})

    async def _unmute(_args: VuotoArgs) -> ToolResult:
        """Torna al livello di prima. Senza un «prima», a un valore udibile:
        riattivare l'audio e restare muti sarebbe la risposta sbagliata."""
        precedente = stato["prima_del_muto"] or LIVELLO_PREDEFINITO
        stato["prima_del_muto"] = None
        return ToolResult(ok=True, output={"volume": audio().imposta_volume(precedente)})

    register(Tool(
        name="set_volume",
        description="Il volume della voce di JARVIS, 0-100. Non tocca il mixer del sistema.",
        args_schema=SetVolumeArgs,
        side_effect=False,
        gesture_allowed=False,
        handler=_set_volume,
    ))
    register(Tool(
        name="mute",
        description="Zittisce JARVIS, ricordando il livello per poterci tornare.",
        args_schema=VuotoArgs,
        side_effect=False,
        gesture_allowed=False,
        handler=_mute,
    ))
    register(Tool(
        name="unmute",
        description="Riattiva la voce di JARVIS al livello di prima del muto.",
        args_schema=VuotoArgs,
        side_effect=False,
        gesture_allowed=False,
        handler=_unmute,
    ))
