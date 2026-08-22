"""Il meteo — la sorgente del pannello di §26.

## Perche' esiste un tool e non una chiamata dal renderer

Invariante 1: il renderer non tocca il disco e non apre socket. Il meteo e'
rete, quindi sta nel core, e ci sta come **tool nell'allowlist** — cosi' e'
anche una cosa che JARVIS puo' chiedersi da solo («che tempo fa domani») e non
solo un riquadro che si riempie.

`side_effect=False`: leggere il tempo non cambia niente. Niente `planner`, e il
registry lo impone.

## ⚠️ Nessun parametro di posizione, e non e' pigrizia

Come `timezones`, che non ha un parametro `path` perche' non deve poterlo
avere: le coordinate arrivano dalle **impostazioni**, non dagli argomenti. Un
LLM che potesse scegliere la latitudine potrebbe usare questo tool per sondare
un servizio esterno con dati che decide lui. Cosi' invece l'unica cosa che
puo' fare e' chiedere il tempo **del posto in cui sta l'utente**, che e' l'unico
posto che gli serve.

## Invariante 5 — quello che torna dalla rete e' dato NON FIDATO

Open-Meteo risponde JSON. Non lo si passa avanti com'e':

  - lo schema pydantic accetta **solo numeri e interi**, mai una stringa
    libera. Nessun campo di testo dell'API entra nel sistema.
  - il nome della citta' NON viene dall'API: viene dalle impostazioni, cioe'
    l'ha scritto l'utente.
  - il codice WMO e' un intero, e viene mappato su un elenco chiuso di
    condizioni NOSTRE. Un codice sconosciuto diventa `ignoto`, che e' uno
    stato dichiarato — non un'icona a caso.

Quindi nel DOM non arriva nessun testo di terzi, e non serve `Untrusted`: non
c'e' prosa da avvolgere. La barriera qui e' lo SCHEMA.

## Invariante 23 — se non si sa, si dice

Rete assente, servizio giu', coordinate non impostate: tre cause diverse, e
tutte e tre danno `ok=False` con un motivo. Il pannello mostra il proprio stato
vuoto. **Non esiste un ripiego a dati finti**, e non deve esistere: un meteo
inventato e' peggio di nessun meteo, perche' qualcuno esce senza ombrello.

## Perche' Open-Meteo

Nessuna chiave API — quindi nessun segreto da custodire e nessun account. E
nessuna dipendenza nuova: `urllib.request` della libreria standard, la stessa
che usano i collector RSS della Fase 8.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import structlog
from pydantic import BaseModel, Field, ValidationError

from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

ENDPOINT = "https://api.open-meteo.com/v1/forecast"

#: Sette giorni: e' la fascia del riferimento, che ne mostra sette.
GIORNI = 7

#: Oltre questo la richiesta si abbandona. Il meteo e' un ornamento
#: informativo: nessun avvio, nessuna connessione e nessun pannello devono
#: aspettarlo piu' di cosi'.
TIMEOUT_S = 6.0

#: Lo stesso di `core/news/collectors/rss.py`: meta' dei servizi rifiuta il
#: `Python-urllib` predefinito, e non e' un travestimento — e' dire chi siamo.
AGENTE = "JARVIS-OS/1.0 (uso personale)"


class MeteoArgs(BaseModel):
    """Nessun argomento. La posizione sta nelle impostazioni (vedi sopra)."""


# ── la mappa dei codici WMO ──────────────────────────────────────────────────
#
# ⚠️ **Otto condizioni, non due.** Il riferimento visivo ne disegna DUE — un
# sole e un sole con nuvola — e ricondurre tutto il tempo a due icone e' un
# segnaposto travestito da icona: con la sola coppia, «nebbia» e «temporale»
# diventerebbero entrambi «sereno».
#
# I codici sono quelli WMO 4677 che Open-Meteo restituisce. La mappa e' chiusa:
# cio' che non e' elencato vale `ignoto`, e `ignoto` ha un segno suo.
CONDIZIONI: dict[int, str] = {
    0: "sereno",
    1: "poco-nuvoloso", 2: "poco-nuvoloso", 3: "nuvoloso",
    45: "nebbia", 48: "nebbia",
    51: "pioviggine", 53: "pioviggine", 55: "pioviggine",
    56: "pioviggine", 57: "pioviggine",
    61: "pioggia", 63: "pioggia", 65: "pioggia",
    66: "pioggia", 67: "pioggia",
    80: "pioggia", 81: "pioggia", 82: "pioggia",
    71: "neve", 73: "neve", 75: "neve", 77: "neve",
    85: "neve", 86: "neve",
    95: "temporale", 96: "temporale", 99: "temporale",
}

#: Le condizioni che il pannello sa disegnare. Serve al renderer per sapere
#: quanti segni gli servono, e a un test per impedire che le due cose divergano.
SEGNI = ("sereno", "poco-nuvoloso", "nuvoloso", "nebbia", "pioviggine",
         "pioggia", "neve", "temporale", "ignoto")


def condizione(codice: int | None) -> str:
    """Da codice WMO a una delle nostre condizioni. Mai un'eccezione."""
    if codice is None:
        return "ignoto"
    return CONDIZIONI.get(int(codice), "ignoto")


# ── lo schema della risposta ─────────────────────────────────────────────────
#
# Accetta SOLO numeri. Non c'e' un campo di testo in tutta la struttura, ed e'
# la ragione per cui il JSON di un servizio esterno puo' finire in un pannello
# senza passare da `Untrusted`: non c'e' prosa da avvolgere.


class _Adesso(BaseModel):
    temperature_2m: float
    weather_code: int
    is_day: int = 1


class _Giorni(BaseModel):
    weather_code: list[int]
    temperature_2m_max: list[float]
    temperature_2m_min: list[float]


class Risposta(BaseModel):
    latitude: float
    longitude: float
    current: _Adesso
    daily: _Giorni
    #: ⚠️ Le date NON entrano: sarebbero l'unico campo di testo, e il pannello
    #: non ne ha bisogno — i giorni li conta a partire da oggi.


def _scarica(lat: float, lon: float, unita: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "forecast_days": GIORNI,
        "timezone": "auto",
        "temperature_unit": unita,
    })
    richiesta = urllib.request.Request(
        f"{ENDPOINT}?{query}", headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(richiesta, timeout=TIMEOUT_S) as r:
        return json.loads(r.read().decode("utf-8"))


def previsione(lat: float, lon: float, nome: str, unita: str) -> dict[str, Any]:
    """La forma che il pannello consuma. Solleva su guasto: avvolge il tool."""
    grezzo = _scarica(lat, lon, unita)
    r = Risposta.model_validate(grezzo)
    giorni = []
    for i in range(min(GIORNI, len(r.daily.weather_code))):
        giorni.append({
            # L'INDICE, non una data: 0 e' oggi. Il renderer sa che giorno e'
            # oggi — ha un orologio — e la data dell'API non entra.
            "fra": i,
            "condizione": condizione(r.daily.weather_code[i]),
            "max": round(r.daily.temperature_2m_max[i]),
            "min": round(r.daily.temperature_2m_min[i]),
        })
    return {
        "luogo": nome,
        "unita": "°C" if unita == "celsius" else "°F",
        "adesso": {
            "temperatura": round(r.current.temperature_2m),
            "condizione": condizione(r.current.weather_code),
            "giorno": bool(r.current.is_day),
        },
        "giorni": giorni,
        # ⚠️ Quando e' stato preso. Un meteo senza «aggiornato alle» mostra
        # numeri senza data, e i numeri vecchi sono peggio dello stato vuoto.
        "aggiornato": int(time.time()),
        "sorgente": "open-meteo.com",
    }


def register_meteo_tools(impostazioni: Any) -> bool:
    """Registra `weather` se le impostazioni dicono dove siamo.

    ⚠️ **Senza coordinate il tool non esiste**, e non e' un ripiego: e' la
    stessa forma di `code.enabled` (ADR-009). Un tool che c'e' ma fallisce
    sempre riempie l'elenco che l'LLM riceve di cose che non funzionano; un
    tool che non c'e' non si puo' invocare per sbaglio.

    E' anche il motivo per cui **la prima chiamata di rete di questo modulo
    avviene solo dopo che un umano ha scritto due numeri in `settings.toml`**.
    """
    m = getattr(impostazioni, "meteo", None)
    if m is None or not m.enabled:
        log.info("meteo_spento", perche="meteo.enabled = false")
        return False
    if m.latitude is None or m.longitude is None:
        log.info("meteo_senza_posizione",
                 perche="meteo.latitude / meteo.longitude non impostate",
                 conseguenza="il tool non si registra e il pannello resta vuoto")
        return False

    async def _meteo(_args: MeteoArgs) -> ToolResult:
        try:
            return ToolResult(ok=True, output=previsione(
                m.latitude, m.longitude, m.nome or "posizione impostata", m.units))
        except urllib.error.URLError as exc:
            # Rete assente o servizio giu'. Nessuna eccezione verso l'LLM.
            return ToolResult(ok=False, error=f"meteo non raggiungibile: {exc}")
        except (ValidationError, ValueError, KeyError) as exc:
            # La risposta non e' quella che ci aspettiamo: e' un guasto della
            # SORGENTE, e va detto cosi' invece di mostrare mezzi dati.
            return ToolResult(ok=False,
                              error=f"risposta meteo non valida: {str(exc)[:120]}")
        except OSError as exc:
            return ToolResult(ok=False, error=f"meteo non leggibile: {exc}")

    register(Tool(
        name="weather",
        description=(
            "Tempo attuale e previsione a sette giorni per la posizione "
            "configurata. Sola lettura, nessun argomento: la posizione sta "
            "nelle impostazioni e non si puo' scegliere."
        ),
        args_schema=MeteoArgs,
        side_effect=False,
        gesture_allowed=True,
        handler=_meteo,
    ))
    log.info("meteo_acceso", luogo=m.nome, unita=m.units)
    return True
