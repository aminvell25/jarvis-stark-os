"""Supervisore di T1 — SPEC §5.6.

> «Il processo T1 gira per settimane senza riavviarsi: e' tutto il punto del
> design. Prima o poi **il token OAuth scade**. […] E' il fallimento piu'
> probabile dell'intero sistema, e va gestito PRIMA che capiti, non dopo.»

Senza questo modulo succede questo:

    token scade → claude esce con errore di autenticazione
    → systemd Restart=always rilancia → fallisce di nuovo → loop infinito
    → JARVIS e' muto e non dice perche'

## Il codice di uscita, capovolto rispetto a §5.6

§5.6 suggerisce `RestartPreventExitStatus=41` e aggiunge: «Verifichi il codice
di uscita reale sul Suo sistema e lo sostituisca a 41: la documentazione non
pubblica una tabella completa dei codici di `-p`, quindi lo determini
empiricamente lasciando scadere una sessione di prova».

Quel consiglio ha due difetti. Il primo e' pratico: nessuno vuole aspettare la
scadenza di un token per configurare un servizio. Il secondo e' peggiore: il
numero dipenderebbe da una tabella che nessuno pubblica e che puo' cambiare a
una versione qualunque di `claude`, **in silenzio**.

Qui e' capovolto. Il supervisore riconosce `authentication_failed` nello
STREAM — che e' documentato ed e' gia' in §21.5 — e **esce lui** con
`USCITA_AUTH`. Il numero lo decidiamo noi, `RestartPreventExitStatus` funziona
per costruzione, e la unit systemd non ha bisogno di indovinare niente.

## Cosa NON fa

**Non tenta la riautenticazione.** §5.6 lo vieta, e ha ragione: richiede un
browser e un'interazione umana, e automatizzarla significa o fallire in
silenzio o conservare credenziali dove non devono stare. Dice all'utente cosa
fare — `claude`, poi `/login` — e si ferma.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger(__name__)

#: §5.6 verbatim. Sono i valori del campo `error` negli eventi
#: `system`/`api_retry` che significano «il token non vale piu'», non «riprova».
AUTH_ERRORS = frozenset({"authentication_failed", "oauth_org_not_allowed"})

#: Il codice con cui il core esce quando l'autenticazione e' scaduta.
#: `packaging/jarvis-core.service` lo ripete in `RestartPreventExitStatus`, e
#: `tests/test_supervisor.py` verifica che i due numeri coincidano — due
#: costanti uguali in due file diversi divergono al primo che le tocca.
USCITA_AUTH = 41

#: Quello che JARVIS dice a voce. Passa dal TTS LOCALE, che non dipende da
#: Claude: se dipendesse, l'annuncio della sessione scaduta sarebbe la prima
#: cosa a non funzionare.
FRASE = (
    "Signore, la mia sessione e' scaduta. Serve una nuova autenticazione."
)
ISTRUZIONE = "esegui `claude` e poi /login"


@dataclass
class Supervisore:
    """Guarda gli eventi di T1 e decide se e' il caso di smettere.

    Le tre azioni arrivano per funzione e non per import: il supervisore non
    deve sapere che cosa sia il TTS, ne' il bus, ne' systemd. Cosi' i test lo
    misurano senza far parlare nessuno e senza uscire dal processo.
    """

    parla: Callable[[str], Awaitable[None]] | None = None
    pubblica: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    esci: Callable[[int], None] | None = None

    stato: str = "nominal"
    motivo: str = ""
    #: Quante volte T1 e' stato rilanciato per guasti NON di autenticazione.
    riavvii: int = 0
    _visti: list[str] = field(default_factory=list)

    @property
    def puo_riavviare(self) -> bool:
        """Falso dopo un errore di autenticazione: niente loop.

        E' il cuore di §5.6. Un guasto qualunque si riprova; un token scaduto
        no, perche' riprovarlo non lo fa tornare valido e l'unica cosa che
        produce e' rumore nei log e un servizio che sbatte contro il muro
        cinque volte al secondo.
        """
        return self.stato != "degraded_llm"

    async def su_evento(self, evento: dict[str, Any]) -> bool:
        """Osserva un evento dello stream. Vero se ha riconosciuto l'auth.

        La firma e' quella di §5.6 (`on_stream_event`), il nome no: in questo
        repo i nomi sono in italiano, e un solo nome inglese in mezzo si nota
        piu' di quanto aiuti.
        """
        if evento.get("type") != "system" or evento.get("subtype") != "api_retry":
            return False

        errore = evento.get("error")
        if errore not in AUTH_ERRORS:
            # Un `api_retry` che non e' di autenticazione e' un ritardo, non
            # una scadenza: il Governor lo sta gia' guardando (Fase 4), e qui
            # non si fa niente.
            return False

        if self.stato == "degraded_llm":
            return True                      # gia' detto, non lo si ripete

        self.stato = "degraded_llm"
        self.motivo = "auth_expired"
        self._visti.append(str(errore))
        log.critical("auth_scaduta", errore=errore, azione=ISTRUZIONE)

        # L'ordine conta: prima si dice, poi si esce. Uscire per primi
        # significherebbe un servizio che muore senza aver spiegato perche',
        # cioe' esattamente il guasto silenzioso che §5.6 vuole evitare.
        if self.parla is not None:
            await self.parla(FRASE)
        if self.pubblica is not None:
            await self.pubblica({
                "topic": "agent.advisory",
                "level": "critical",
                "reason": "auth_expired",
                "action": ISTRUZIONE,
                "stato": self.stato,
            })
        if self.esci is not None:
            self.esci(USCITA_AUTH)
        return True

    def registra_riavvio(self, motivo: str) -> bool:
        """Un riavvio di T1 per un guasto qualunque. Falso se non si deve.

        Serve al caso opposto e piu' comune: T1 muore per un motivo che NON e'
        l'autenticazione — rete, OOM, un aggiornamento di `claude` — e li' il
        riavvio e' giusto.
        """
        if not self.puo_riavviare:
            log.warning("riavvio_rifiutato", motivo=motivo, stato=self.stato)
            return False
        self.riavvii += 1
        log.info("t1_riavviato", motivo=motivo, totale=self.riavvii)
        return True

    def stato_doctor(self) -> dict[str, Any]:
        """Per `jarvis doctor` (§16.1b), riga «T1 auth»."""
        return {
            "stato": self.stato,
            "motivo": self.motivo,
            "riavvii": self.riavvii,
            "azione": ISTRUZIONE if self.stato == "degraded_llm" else "",
        }
