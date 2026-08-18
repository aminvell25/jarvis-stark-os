"""L'interprete e' 3.12 e non 3.13 — SPEC §4, ADR-001.

MediaPipe (Fase 7) non ha wheel oltre 3.12. Il vincolo va scoperto qui, dove
costa una riga, non alla Fase 7 con dieci settimane di core gia' scritte.
"""

import sys


def test_interprete_e_312() -> None:
    assert sys.version_info[:2] == (3, 12), (
        f"atteso Python 3.12, trovato {sys.version_info.major}."
        f"{sys.version_info.minor}. `uv python pin 3.12` e poi `uv sync`."
    )
