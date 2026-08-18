"""Costruzione dei provider dalle impostazioni — SPEC §8, §7.3.

Un posto solo in cui si decide chi esiste. La pipeline chiede una `Scelta` e
non sa se dietro c'e' Deepgram o il ripiego: e' cio' che rende il ripiego di
§7.3 una sostituzione e non un ramo `if` sparso.
"""

from __future__ import annotations

from typing import Any

import structlog

from core.providers.health import Scelta, scegli
from core.settings import Settings

log = structlog.get_logger(__name__)


def costruisci_stt(s: Settings, modello_vosk: Any = None,
                   errore_primario: bool = False) -> Scelta:
    from core.providers.stt_local import VoskSTT

    chiave = s.secrets.deepgram_api_key.get_secret_value()
    primario = None
    if chiave:
        from core.providers.stt_deepgram import DeepgramSTT

        primario = DeepgramSTT(chiave, eot_threshold=s.voice.eot_threshold,
                               eager_eot=s.voice.eager_eot,
                               modello=s.voice.deepgram_stt_model)
    return scegli(
        primario=primario,
        ripiego=VoskSTT(modello=modello_vosk),
        chiave_presente=bool(chiave),
        preferisci_primario=s.voice.stt_provider == "deepgram",
        tipo="stt",
        errore_primario=errore_primario,
    )


def costruisci_tts(s: Settings, errore_primario: bool = False) -> Scelta:
    from core.providers.tts_local import EdgeTTS

    chiave = s.secrets.deepgram_api_key.get_secret_value()
    primario = None
    if chiave:
        from core.providers.tts_deepgram import DeepgramTTS

        primario = DeepgramTTS(chiave)
    return scegli(
        primario=primario,
        ripiego=EdgeTTS(),
        chiave_presente=bool(chiave),
        preferisci_primario=s.voice.tts_provider == "deepgram",
        tipo="tts",
        errore_primario=errore_primario,
    )
