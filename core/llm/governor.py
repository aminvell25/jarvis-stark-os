"""Governor — chi puo' girare, e quando. SPEC §5.4, invariante 16.

> «L'uso programmatico **attinge ai limiti dell'abbonamento**. Il pool crediti
> separato per l'Agent SDK e' sospeso dal 15 giugno 2026.»

Tre regole, e la terza e' quella che conta:

1. al massimo `max_concurrent` spawn T2 insieme
2. al massimo `max_per_window` spawn nella finestra
3. **T1 non va MAI in coda.** Il Governor gestisce solo T2. Se la quota si
   esaurisce, T2 si sospende e T1 sopravvive: e' la differenza fra un sistema
   che rallenta e uno che ammutolisce

FAIL-CLOSED, come il registry dei tool: senza Governor collegato, nessuno spawn
T2 gira. Dimenticare di cablarlo rende il sistema inerte, non illimitato.

NOTA SU `conso/` (rilievo R32). ADR-004 osservava che il Governor accumulava
`total_cost_usd` — l'LLM, gia' pagato dall'abbonamento — mentre Deepgram, la
sola voce di costo ricorrente di §24.8, non era misurato. Da allora il quadro
e' cambiato: **nessuna chiave Deepgram, `edge-tts` gratuito, nessun costo
ricorrente**. Il numero operativo sono quindi **gli spawn nella finestra**, che
e' cio' che vincola davvero. `total_cost_usd` si registra lo stesso perche' lo
stream lo riporta, ma non e' su quello che si decide.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

MAX_CONCURRENT = 2
MAX_PER_WINDOW = 15
WINDOW_S = 3600.0


class Rifiuto:
    QUOTA = "quota della finestra esaurita"
    SOSPESO = "T2 sospeso dal rate limit"
    OK = "concesso"


@dataclass(frozen=True)
class Permesso:
    concesso: bool
    motivo: str
    #: Quanti spawn restano nella finestra. Serve al pannello telemetria: §5.4
    #: vuole «sapere quando la finestra sta per chiudersi PRIMA che si chiuda».
    restanti: int = 0
    riprova_fra_s: float = 0.0


@dataclass
class Consumo:
    """Una riga del log giornaliero."""

    quando: float
    tier: str
    etichetta: str
    esito: str
    durata_s: float = 0.0
    costo_usd: float | None = None
    token: dict[str, Any] = field(default_factory=dict)


class Governor:
    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT,
        max_per_window: int = MAX_PER_WINDOW,
        window_s: float = WINDOW_S,
        su_advisory: Callable[[dict], Any] | None = None,
        dir_conso: Path | None = None,
    ) -> None:
        self._max_concurrent = max_concurrent
        self._max_per_window = max_per_window
        self._window_s = window_s
        self._su_advisory = su_advisory
        self._dir_conso = dir_conso
        self._sem = asyncio.Semaphore(max_concurrent)
        self._spawn: list[float] = []
        self._sospeso_fino: float = 0.0
        self._attivi = 0

    # ── stato ────────────────────────────────────────────────────────────────

    @property
    def sospeso(self) -> bool:
        return time.monotonic() < self._sospeso_fino

    @property
    def attivi(self) -> int:
        return self._attivi

    def _nella_finestra(self) -> list[float]:
        ora = time.monotonic()
        self._spawn = [t for t in self._spawn if ora - t < self._window_s]
        return self._spawn

    @property
    def restanti(self) -> int:
        return max(0, self._max_per_window - len(self._nella_finestra()))

    def stato(self) -> dict[str, Any]:
        """Per `state.snapshot` e per `jarvis doctor`."""
        return {
            "attivi": self._attivi,
            "max_concurrent": self._max_concurrent,
            "usati_nella_finestra": len(self._nella_finestra()),
            "max_per_finestra": self._max_per_window,
            "restanti": self.restanti,
            "sospeso": self.sospeso,
            "riprova_fra_s": max(0.0, self._sospeso_fino - time.monotonic()),
        }

    # ── ammissione ───────────────────────────────────────────────────────────

    def puo_spawnare(self) -> Permesso:
        """Decide **senza** attendere. `acquisisci()` attende sul concorrente."""
        if self.sospeso:
            return Permesso(False, Rifiuto.SOSPESO, self.restanti,
                            max(0.0, self._sospeso_fino - time.monotonic()))
        if self.restanti <= 0:
            # `min()` su lista vuota solleva, e la lista E' vuota quando la
            # finestra e' configurata a zero — il modo piu' diretto di
            # disattivare T2. Un guasto interno invece di un rifiuto pulito.
            finestra = self._nella_finestra()
            attesa = (self._window_s - (time.monotonic() - min(finestra))
                      if finestra else self._window_s)
            return Permesso(False, Rifiuto.QUOTA, 0, attesa)
        return Permesso(True, Rifiuto.OK, self.restanti)

    @asynccontextmanager
    async def spawn(self, etichetta: str):
        """Concede uno slot T2, o solleva `QuotaEsaurita`.

        **T1 non passa di qui**: e' riservato e non va mai in coda (§5.4).
        """
        p = self.puo_spawnare()
        if not p.concesso:
            log.warning("t2_rifiutato", etichetta=etichetta, motivo=p.motivo,
                        riprova_fra_s=round(p.riprova_fra_s))
            self._registra(Consumo(time.time(), "t2", etichetta, f"rifiutato: {p.motivo}"))
            raise QuotaEsaurita(p)

        # Il conteggio della finestra si incrementa PRIMA dell'attesa sul
        # semaforo: due richieste simultanee con un solo slot residuo non
        # devono passare entrambe.
        self._spawn.append(time.monotonic())
        await self._sem.acquire()
        self._attivi += 1
        t0 = time.monotonic()
        log.info("t2_avviato", etichetta=etichetta, attivi=self._attivi,
                 restanti=self.restanti)
        esito = "ok"
        try:
            yield self
        except Exception as exc:
            esito = f"errore: {type(exc).__name__}"
            raise
        finally:
            self._attivi -= 1
            self._sem.release()
            self._registra(Consumo(time.time(), "t2", etichetta, esito,
                                   durata_s=round(time.monotonic() - t0, 2)))

    # ── degradazione ─────────────────────────────────────────────────────────

    def osserva(self, evento: dict) -> None:
        """Guarda gli eventi dello stream di Claude Code (§21.5).

        Su `api_retry` con `error=rate_limit`: **sospende T2, degrada, annuncia,
        e non tocca T1**.
        """
        if evento.get("type") != "system" or evento.get("subtype") != "api_retry":
            return
        testo = json.dumps(evento).lower()
        if "rate_limit" not in testo and "rate limit" not in testo:
            return
        attesa = float(evento.get("retry_delay_ms", 60_000)) / 1000.0
        self.sospendi(attesa, "rate_limit")

    def sospendi(self, secondi: float, motivo: str) -> None:
        self._sospeso_fino = time.monotonic() + secondi
        log.warning("t2_sospeso", motivo=motivo, secondi=round(secondi))
        self._advisory({
            "topic": "agent.advisory",
            "level": "warn",
            "reason": f"t2_sospeso: {motivo}",
            "riprova_fra_s": round(secondi),
            # §5.4: «sospendi T2 -> degrada -> agent.advisory -> NON far
            # fallire T1». Lo stato lo dice esplicitamente, cosi' che chi
            # legge l'advisory sappia che la conversazione continua.
            "t1_operativo": True,
        })

    def riprendi(self) -> None:
        self._sospeso_fino = 0.0
        log.info("t2_ripreso")
        self._advisory({"topic": "agent.advisory", "level": "info",
                        "reason": "t2_ripreso"})

    def _advisory(self, msg: dict) -> None:
        if self._su_advisory:
            self._su_advisory(msg)

    # ── log giornaliero ──────────────────────────────────────────────────────

    def _registra(self, c: Consumo) -> None:
        if self._dir_conso is None:
            return
        try:
            self._dir_conso.mkdir(parents=True, exist_ok=True)
            giorno = time.strftime("%Y-%m-%d", time.localtime(c.quando))
            riga = {
                "ts": c.quando, "tier": c.tier, "etichetta": c.etichetta,
                "esito": c.esito, "durata_s": c.durata_s,
                "costo_usd": c.costo_usd, "token": c.token,
                # R32: e' questo il numero su cui si decide.
                "usati_nella_finestra": len(self._nella_finestra()),
                "restanti": self.restanti,
            }
            with (self._dir_conso / f"{giorno}.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(riga, ensure_ascii=False) + "\n")
        except OSError as exc:
            # Il log non deve poter fermare un'operazione.
            log.warning("conso_non_scritto", errore=str(exc))

    def registra_risultato(self, etichetta: str, evento: dict) -> None:
        """Registra l'evento `result` di uno spawn: costo e token riportati."""
        self._registra(Consumo(
            time.time(), "t2", etichetta, "result",
            costo_usd=evento.get("total_cost_usd"),
            token=evento.get("usage", {}) or {},
        ))


class QuotaEsaurita(RuntimeError):
    def __init__(self, permesso: Permesso) -> None:
        super().__init__(f"{permesso.motivo}; riprova fra {permesso.riprova_fra_s:.0f} s")
        self.permesso = permesso
