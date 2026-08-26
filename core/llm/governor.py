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
    #: ⚠️ ADR-004. `tier` vale «t1»/«t2» per l'LLM e «stt»/«tts» per la voce, e
    #: questi due campi hanno senso solo per la seconda: chi ha parlato e se era
    #: il ripiego. Restano `None`/`False` per l'LLM invece di stare in una
    #: seconda dataclass, perche' `conso/` e' UN registro e leggerlo in due
    #: forme diverse sarebbe due letture della stessa domanda.
    provider: str | None = None
    fallback: bool = False


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

    def _controlla_ripresa(self) -> None:
        """La sospensione e' scaduta? Allora **dillo**.

        ⚠️ `riprendi()` non aveva un solo chiamante. La sospensione scadeva da
        sola — `sospeso` e' un confronto sull'orologio — quindi T2 tornava a
        funzionare comunque, e per questo il difetto era invisibile. Ma §16
        dice «**nessuna soglia agisce senza annunciarlo**», e qui la
        degradazione si annunciava mentre la ripresa era muta: chi leggeva
        l'advisory «T2 sospeso, riprova fra 900 s» non riceveva mai il seguito.

        Un'asimmetria fra il dire che qualcosa e' rotto e il dire che e'
        tornato a posto e' peggio del silenzio su entrambi: la prima meta'
        insegna a fidarsi degli advisory, la seconda tradisce quella fiducia.

        Idempotente: `riprendi()` azzera `_sospeso_fino`, quindi chiamarlo a
        2,5 Hz dallo snapshot emette **un** advisory e non uno ogni 400 ms.
        """
        if 0.0 < self._sospeso_fino <= time.monotonic():
            self.riprendi()

    def stato(self) -> dict[str, Any]:
        """Per `state.snapshot` e per `jarvis doctor`.

        Lo chiama lo snapshot a 2,5 Hz, ed e' per questo che il controllo della
        ripresa sta qui: e' il posto che guarda piu' spesso, quindi l'annuncio
        arriva entro mezzo secondo dalla scadenza invece che al prossimo spawn
        — che potrebbe non arrivare mai.
        """
        self._controlla_ripresa()
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
        # Anche qui, e non solo nello snapshot: un core senza scrivania
        # collegata non chiama `stato()`, e la ripresa resterebbe muta.
        self._controlla_ripresa()
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
                "provider": c.provider, "fallback": c.fallback,
                # R32: e' questo il numero su cui si decide.
                "usati_nella_finestra": len(self._nella_finestra()),
                "restanti": self.restanti,
            }
            with (self._dir_conso / f"{giorno}.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(riga, ensure_ascii=False) + "\n")
        except OSError as exc:
            # Il log non deve poter fermare un'operazione.
            log.warning("conso_non_scritto", errore=str(exc))

    def registra_voce(self, tier: str, provider: str, secondi: float, *,
                      fallback: bool = False, esito: str = "ok") -> None:
        """ADR-004: i SECONDI di audio, per provider, e se era il ripiego.

        ## Perche' esiste

        §24.8 chiama Deepgram «la sola voce di costo ricorrente del progetto», e
        il sistema misurava con precisione `total_cost_usd` — cioe' l'LLM, che
        l'abbonamento copre gia' — e **non misurava l'unica cosa che gli costa**.

        ⚠️ Su questa macchina oggi non costa niente: nessuna chiave Deepgram,
        `edge-tts` gratuito. Il contatore serve **prima**: accendere il
        microfono e cominciare a spendere senza saper contare e' il difetto per
        cui ADR-004 esiste, e un mese di consumo non attribuito non si recupera.

        `fallback` non e' contabilita': e' la misura di **quanto Deepgram sia
        davvero affidabile** su questa rete. Se i minuti in ripiego locale sono
        molti, l'invariante 12 sta lavorando parecchio e nessuno lo saprebbe.
        """
        self._registra(Consumo(
            time.time(), tier, provider, esito,
            durata_s=float(secondi), provider=provider, fallback=bool(fallback),
        ))

    def consumo_voce_mese(self, adesso: float | None = None) -> dict[str, Any]:
        """I secondi del MESE per provider, letti da `conso/`.

        Il mese e non il giorno: e' l'unita' con cui Deepgram fattura, e un
        totale giornaliero non risponde alla domanda che §24.8 pone.

        ⚠️ Legge il disco a ogni chiamata e non tiene un totale in memoria: un
        contatore in RAM si azzera a ogni riavvio del core, cioe' proprio quando
        serve — e i file ci sono gia'.
        """
        vuoto: dict[str, Any] = {"secondi": {}, "fallback_s": 0.0, "sessioni": 0}
        if self._dir_conso is None or not self._dir_conso.is_dir():
            return vuoto
        prefisso = time.strftime("%Y-%m", time.localtime(adesso or time.time()))
        for f in sorted(self._dir_conso.glob(f"{prefisso}-*.jsonl")):
            try:
                righe = f.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for r in righe:
                try:
                    d = json.loads(r)
                except json.JSONDecodeError:
                    continue
                if d.get("tier") not in ("stt", "tts"):
                    continue
                p = d.get("provider") or "?"
                vuoto["secondi"][p] = round(
                    vuoto["secondi"].get(p, 0.0) + float(d.get("durata_s") or 0.0), 1)
                if d.get("fallback"):
                    vuoto["fallback_s"] = round(
                        vuoto["fallback_s"] + float(d.get("durata_s") or 0.0), 1)
                vuoto["sessioni"] += 1
        return vuoto

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
