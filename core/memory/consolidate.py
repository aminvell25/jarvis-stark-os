"""Consolidamento notturno — SPEC §5.5.

Il `ContextPruner` e' **reattivo**: pota quando il budget e' saturo, e cio' che
scarta e' perso. Questo passaggio e' **programmato**: gira quando nessuno usa il
sistema e ha tempo di ragionare su cosa vale la pena conservare.

> «Potatura sotto pressione e consolidamento a mente fredda non sono lo stesso
> lavoro. Servono entrambi.»

Idea adottata da `Grominet95/jarvis-OS` (`docs/ANALISI-REPO-E-TECNOLOGIE.md`
§1.1①), **reimplementata da zero** come impone l'invariante 30.

⚠️ **NON TOCCA I FATTI FISSATI**: sono dell'utente (§5.5).

⚠️ **SE NON GIRA, LO DICE** (rilievo R33). Passa dal Governor come ogni T2
(invariante 16), e se la finestra e' esaurita o il token e' scaduto nella notte
non gira. §16 vieta le degradazioni silenziose: emette un `agent.advisory`, e
la mattina dopo si sa perche' la memoria non e' stata consolidata.

⚠️ **SCRIVE SENZA CONFERMA UMANA, ed e' una tensione dichiarata.** L'invariante
3 vuole conferma per ogni `side_effect=True`, ma alle 04:00 non c'e' nessuno che
confermi. La si scioglie restringendo il raggio: scrive **solo** dentro
`topics/`, non tocca i fatti fissati, e ogni scrittura finisce in
`initiatives/`, visibile al risveglio. E' un compromesso, non una scappatoia, e
sta scritto in `docs/acceptance/FASE-04.md`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from core.llm.governor import QuotaEsaurita
from core.memory.store import MemoryStore

log = structlog.get_logger(__name__)

ORA_DEFAULT = 4          # le 04:00 di §5.5
SEGNAPOSTO = "_ultimo-consolidamento"


class Consolidatore:
    def __init__(
        self,
        store: MemoryStore,
        t2,
        su_advisory: Callable[[dict], Any] | None = None,
    ) -> None:
        self._store = store
        self._t2 = t2
        self._su_advisory = su_advisory

    def ultimo_run(self) -> float:
        p = self._store.radice / f"{SEGNAPOSTO}.txt"
        try:
            return float(p.read_text().strip())
        except (OSError, ValueError):
            return 0.0

    def _segna_run(self) -> None:
        (self._store.radice / f"{SEGNAPOSTO}.txt").write_text(str(time.time()))

    def _advisory(self, livello: str, motivo: str, **extra) -> None:
        msg = {"topic": "agent.advisory", "level": livello,
               "reason": f"consolidamento: {motivo}", **extra}
        log.warning("consolidamento_advisory", motivo=motivo)
        if self._su_advisory:
            self._su_advisory(msg)

    async def esegui(self) -> dict[str, Any]:
        """Rilegge le sessioni dall'ultimo giro e fonde nei topic."""
        da = self.ultimo_run()
        turni = self._store.sessioni_dal(da)
        if not turni:
            log.info("consolidamento_niente_da_fare")
            self._segna_run()
            return {"eseguito": False, "motivo": "niente di nuovo", "topic": 0}

        per_sessione: dict[str, list[dict]] = {}
        for t in turni:
            per_sessione.setdefault(t["sessione"], []).append(t)

        scritti = 0
        for sessione, frammenti in per_sessione.items():
            testo = "\n".join(
                f"- {f.get('utente','')} -> {f.get('jarvis','')}".strip()
                for f in frammenti if f.get("utente") or f.get("jarvis")
            )
            if not testo.strip():
                continue

            compito = (
                "Riassumi questi scambi in note durevoli, in italiano, in non piu' di "
                "dieci righe. Solo cio' che vale la pena ricordare fra un mese: "
                "preferenze, decisioni, fatti stabili. Ometti le chiacchiere.\n\n"
                + testo
            )
            try:
                r = await self._t2.esegui(compito, f"consolidamento-{sessione}")
            except QuotaEsaurita as exc:
                # R33: la quota e' finita. NON si finge che sia andato bene.
                self._advisory("warn", "quota esaurita, riprovo la prossima notte",
                               dettaglio=str(exc))
                return {"eseguito": False, "motivo": "quota", "topic": scritti}

            if not r.ok or not r.testo:
                self._advisory("warn", f"sessione {sessione} non consolidata",
                               dettaglio=r.errore or "risposta vuota")
                continue

            self._store.scrivi_topic(f"sessione {sessione}", r.testo)
            # Ogni scrittura notturna e' visibile al risveglio: e' cio' che
            # rende accettabile scrivere senza conferma.
            self._store.registra_iniziativa("consolidamento", {
                "sessione": sessione, "turni": len(frammenti),
                "costo_usd": r.costo_usd, "durata_s": r.durata_s,
            })
            scritti += 1

        self._segna_run()
        log.info("consolidamento_fatto", topic=scritti, turni=len(turni))
        return {"eseguito": True, "topic": scritti, "turni": len(turni)}
