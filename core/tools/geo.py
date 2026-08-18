"""Fusi orari — SOLA LETTURA, per il globo tattico di §13.

⚠️ **Non e' in §21.1.** Lo aggiungo qui e lo dichiaro in `FASE-05.md`.

Perche' serve un tool: §13 vuole che il globo mostri «fusi orari, coordinate,
elevazione solare calcolata». I fusi stanno in `/usr/share/zoneinfo/zone1970.tab`,
cioe' su disco, e il renderer il disco non lo tocca (invariante 1). Passa
dall'allowlist come tutto il resto (invariante 2).

Perche' e' sicuro nonostante legga fuori dalle radici consentite: **non ha
parametri**. Il percorso e' una costante del modulo, non un argomento, quindi
non esiste input che possa spostarlo altrove — la difesa e' strutturale, non
una validazione da ricordarsi. `side_effect=False`, quindi nessuna conferma
(§6.2) e nessuna deroga all'invariante 3.

`zone1970.tab` e' di **pubblico dominio** (lo dichiara il file stesso, prima
riga dei commenti): nessun vincolo di licenza, e nessun bisogno di rete.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from pydantic import BaseModel

from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

# Costante, non argomento: vedi l'intestazione.
TABELLA = Path("/usr/share/zoneinfo/zone1970.tab")


class FusiArgs(BaseModel):
    """Nessun argomento: la tabella e' una sola."""


def _gradi(campo: str) -> tuple[float, float]:
    """Le coordinate ISO 6709 di zone1970.tab in gradi decimali.

    Il formato ha due lunghezze: `+DDMM+DDDMM` e `+DDMMSS+DDDMMSS`. Distinguere
    a naso sui caratteri sarebbe fragile; si distingue sulla lunghezza del
    segmento, che e' un dato del formato.
    """
    taglio = campo.find("+", 1)
    if taglio == -1:
        taglio = campo.find("-", 1)
    lat, lon = campo[:taglio], campo[taglio:]

    def uno(s: str, gradi_cifre: int) -> float:
        segno = -1.0 if s[0] == "-" else 1.0
        corpo = s[1:]
        g = int(corpo[:gradi_cifre])
        m = int(corpo[gradi_cifre:gradi_cifre + 2])
        sec = int(corpo[gradi_cifre + 2:gradi_cifre + 4]) if len(corpo) > gradi_cifre + 2 else 0
        return segno * (g + m / 60 + sec / 3600)

    return uno(lat, 2), uno(lon, 3)


def leggi_fusi(tabella: Path = TABELLA) -> list[dict]:
    """Nome, latitudine, longitudine e paesi di ogni fuso.

    Solleva se il file non c'e': un globo senza fusi mostrerebbe uno stato
    vuoto, ed e' meglio saperlo dal `ToolResult` che dedurlo da un pannello
    spoglio.
    """
    fuori: list[dict] = []
    for riga in tabella.read_text(encoding="utf-8").splitlines():
        if not riga or riga.startswith("#"):
            continue
        campi = riga.split("\t")
        if len(campi) < 3:
            continue
        paesi, coord, nome = campi[0], campi[1], campi[2]
        try:
            lat, lon = _gradi(coord)
        except (ValueError, IndexError):
            log.warning("fuso_non_interpretabile", riga=riga[:60])
            continue
        fuori.append({"nome": nome, "lat": round(lat, 4), "lon": round(lon, 4),
                      "paesi": paesi.split(",")})
    return fuori


def register_geo_tools() -> None:
    async def _fusi(_args: FusiArgs) -> ToolResult:
        try:
            zone = leggi_fusi()
        except OSError as exc:
            # Nessuna eccezione arriva all'LLM — stile codice di CLAUDE.md.
            return ToolResult(ok=False, error=f"tabella dei fusi non leggibile: {exc}")
        return ToolResult(ok=True, output={"sorgente": str(TABELLA), "zone": zone})

    register(Tool(
        name="timezones",
        description=(
            "Nome, latitudine e longitudine di ogni fuso orario, dalla tabella "
            "tzdata di sistema. Sola lettura, nessun argomento."
        ),
        args_schema=FusiArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_fusi,
    ))
