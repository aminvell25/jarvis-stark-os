"""ContextPruner — SPEC §5.5, invariante 17.

⚠️ **Serve a DUE cose sole**, e §5.5 e' esplicito sul perche':

> «Con T1 persistente, Claude Code gestisce gia' il proprio contesto. Il
> `ContextPruner` serve solo per (a) i fatti fissati da reiniettare quando la
> sessione viene ricreata e (b) T2, dove ogni spawn parte da zero. **Non
> duplichi la gestione del contesto di T1**: otterrebbe due gestori in
> disaccordo.»

Per questo qui **non c'e' `build_context()` per T1**. §5.5 ne mostra uno, ma
usarlo per T1 sarebbe esattamente il secondo gestore di cui avverte. Il primo
uso esiste gia': `ClaudeT1.riavvia_dopo_guasto` (ADR-003) chiede i fatti
fissati, e fino a oggi riceveva una lista vuota.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from core.memory.store import MemoryStore

log = structlog.get_logger(__name__)

#: Caratteri per token, stima grossolana per l'italiano. Serve solo a decidere
#: quando potare, non a fatturare: una stima sbagliata del 20% non cambia nulla.
CHAR_PER_TOKEN = 3.6


@dataclass
class ContextPruner:
    store: MemoryStore
    budget_tokens: int = 12_000

    def fatti_fissati(self) -> list[str]:
        """Per T1, quando la sessione va ricreata (ADR-003)."""
        return self.store.fatti_fissati()

    def contesto_per_t2(self, compito: str, topic_rilevanti: int = 3) -> str:
        """Il contesto di uno spawn T2, che parte da zero.

        I fatti fissati per primi — sono dell'utente e valgono sempre — poi i
        topic che somigliano al compito, finche' il budget regge.
        """
        pezzi = []
        fatti = self.fatti_fissati()
        if fatti:
            pezzi.append("Fatti da tenere presenti:\n" + "\n".join(f"- {f}" for f in fatti))

        for t in self.store.cerca(compito, limite=topic_rilevanti):
            pezzi.append(t.contenuto.strip())

        testo = "\n\n".join(pezzi)
        massimo = int(self.budget_tokens * CHAR_PER_TOKEN)
        if len(testo) > massimo:
            # Si tronca dalla CODA: i fatti fissati stanno in testa e non si
            # perdono mai.
            testo = testo[:massimo].rsplit("\n", 1)[0]
            log.info("contesto_t2_potato", budget=self.budget_tokens)
        return testo
