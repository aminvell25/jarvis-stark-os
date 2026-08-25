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
import time
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

#: Lo stesso, per la classe `repeated`: T1 cade e ricade, e riavviarlo ancora
#: non lo aggiusta. Un codice DIVERSO da quello dell'auth perche' la causa e'
#: diversa e chi legge i log deve poterle distinguere; entrambi stanno in
#: `RestartPreventExitStatus`.
USCITA_RIPETUTI = 42

#: ADR-003, classe `repeated`: «N riavvii nella finestra». I due numeri.
#: ⚠️ La finestra si misura con un orologio MONOTONO, non con l'ora: qui la
#: domanda e' «quanto tempo e' passato», e l'ora di sistema puo' saltare.
FINESTRA_RIAVVII_S = 600.0
SOGLIA_RIPETUTI = 3

#: Quello che JARVIS dice a voce. Passa dal TTS LOCALE, che non dipende da
#: Claude: se dipendesse, l'annuncio della sessione scaduta sarebbe la prima
#: cosa a non funzionare.
FRASE = (
    "Signore, la mia sessione e' scaduta. Serve una nuova autenticazione."
)
ISTRUZIONE = "esegui `claude` e poi /login"

#: ⚠️ LA FRASE CHE RENDE ONESTO IL RIAVVIO, ed e' il cuore di ADR-003.
#:
#: «Il modo di fallire e' il peggiore che questo sistema possa avere: JARVIS
#: continua a rispondere, con la stessa voce e la stessa persona, avendo perso
#: la conversazione, e non lo dice.» §16 vieta che una soglia agisca senza
#: annunciarlo, e perdere la memoria di una conversazione e' la soglia piu'
#: grossa di tutte.
#:
#: Dice due cose e non una: che cosa e' andato perso — la conversazione — e che
#: cosa e' rimasto — i fatti fissati. Dire solo «ho riavviato» lascerebbe
#: all'utente il compito di indovinare che cosa ricordo ancora.
FRASE_TRANSIENT = (
    "Signore, ho dovuto riavviare la sessione. "
    "Ho conservato le Sue preferenze, non la conversazione."
)
FRASE_RIPETUTI = (
    "Signore, la sessione continua a cadere. Smetto di riprovare."
)
ISTRUZIONE_RIPETUTI = "controlla i log del core e riavvia il servizio a mano"


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
    #: ADR-003 azione 2: i FATTI FISSATI, mai i turni. Arriva per funzione — di
    #: solito `ContextPruner.fatti_fissati` — perche' l'invariante 17 vieta di
    #: duplicare la gestione del contesto di T1: il contesto conversazionale
    #: resta di Claude Code, i fatti fissati restano dell'utente, e il
    #: supervisore non possiede ne' l'uno ne' gli altri.
    fatti_fissati: Callable[[], list[str]] | None = None
    #: Dove rimettere quei fatti nella sessione nuova.
    reinietta: Callable[[list[str]], Awaitable[None]] | None = None
    #: ⚠️ MONOTONO, non l'ora: qui si misura QUANTO TEMPO PASSA fra due
    #: riavvii, e l'ora di sistema puo' saltare all'indietro. E' la stessa
    #: distinzione di `ui/src/desk/orologio.js`, dall'altra parte del sistema.
    orologio: Callable[[], float] = time.monotonic

    stato: str = "nominal"
    motivo: str = ""
    #: Quante volte T1 e' stato rilanciato per guasti NON di autenticazione.
    riavvii: int = 0
    _visti: list[str] = field(default_factory=list)
    #: Gli istanti dei riavvii dentro la finestra. Non un contatore: un
    #: contatore non sa dimenticare, e «tre riavvii in dieci minuti» e' un
    #: guasto mentre «tre in tre giorni» e' la vita normale di un processo.
    _quando: list[float] = field(default_factory=list)

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

    def classifica(self, motivo: str) -> str:
        """`auth`, `repeated` o `transient` — le tre classi di ADR-003.

        Pura: non parla, non esce, non tocca lo stato. Cosi' la si puo'
        interrogare in un test senza far succedere niente, ed e' anche il modo
        in cui `su_riavvio` resta leggibile.
        """
        if self.stato == "degraded_llm":
            return "auth" if self.motivo == "auth_expired" else "repeated"
        adesso = self.orologio()
        dentro = [t for t in self._quando if adesso - t < FINESTRA_RIAVVII_S]
        return "repeated" if len(dentro) + 1 >= SOGLIA_RIPETUTI else "transient"

    async def su_riavvio(self, motivo: str) -> bool:
        """T1 e' morto per un guasto NON di autenticazione. Vero se si riparte.

        E' il ramo che ADR-003 chiamava «il difetto peggiore ancora aperto»:
        prima di oggi qui si contava e basta, T1 ripartiva **vuoto** e JARVIS
        continuava a rispondere con la stessa voce avendo perso la
        conversazione, **senza dirlo**.

        Tre cose, in quest'ordine, e l'ordine e' la sostanza:

        1. si classifica;
        2. se e' `repeated` si smette — e lo si dice — perche' riavviare
           ancora non aggiusta niente e produce solo un servizio che sbatte
           contro il muro;
        3. se e' `transient` si riparte, si **rimettono i fatti fissati** e si
           **annuncia**. L'annuncio prima del replay: se il replay fallisse,
           l'utente ha comunque sentito che la conversazione non c'e' piu'.
        """
        if not self.puo_riavviare:
            log.warning("riavvio_rifiutato", motivo=motivo, stato=self.stato)
            return False

        classe = self.classifica(motivo)
        adesso = self.orologio()
        self._quando = [t for t in self._quando if adesso - t < FINESTRA_RIAVVII_S]
        self._quando.append(adesso)
        self.riavvii += 1

        if classe == "repeated":
            self.stato = "degraded_llm"
            self.motivo = "riavvii_ripetuti"
            log.critical("t1_riavvii_ripetuti", motivo=motivo,
                         nella_finestra=len(self._quando), soglia=SOGLIA_RIPETUTI)
            await self._annuncia(FRASE_RIPETUTI, "critical", "riavvii_ripetuti",
                                 ISTRUZIONE_RIPETUTI)
            if self.esci is not None:
                self.esci(USCITA_RIPETUTI)
            return False

        log.info("t1_riavviato", motivo=motivo, totale=self.riavvii, classe=classe)
        await self._annuncia(FRASE_TRANSIENT, "warn", "sessione_riavviata", "")
        await self._rimetti_i_fatti()
        return True

    async def _rimetti_i_fatti(self) -> None:
        """ADR-003 azione 2: **solo** i fatti fissati, mai i turni.

        Se non c'e' niente da rimettere non si chiama nessuno: reiniettare una
        lista vuota scriverebbe nel contesto nuovo una riga che non dice
        niente, e il budget di §5.5 e' di qualcuno.
        """
        if self.fatti_fissati is None or self.reinietta is None:
            return
        fatti = list(self.fatti_fissati())
        if not fatti:
            return
        await self.reinietta(fatti)
        log.info("fatti_reiniettati", quanti=len(fatti))

    async def _annuncia(self, frase: str, livello: str, ragione: str,
                        azione: str) -> None:
        """Voce PRIMA del bus, come nel ramo dell'auth: la voce e' l'unica cosa
        che l'utente sente se non sta guardando lo schermo."""
        if self.parla is not None:
            await self.parla(frase)
        if self.pubblica is not None:
            await self.pubblica({
                "topic": "agent.advisory",
                "level": livello,
                "reason": ragione,
                "action": azione,
                "stato": self.stato,
            })

    def stato_doctor(self) -> dict[str, Any]:
        """Per `jarvis doctor` (§16.1b), riga «T1 auth»."""
        return {
            "stato": self.stato,
            "motivo": self.motivo,
            "riavvii": self.riavvii,
            "azione": ISTRUZIONE if self.stato == "degraded_llm" else "",
        }
