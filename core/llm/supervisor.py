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
from enum import Enum
import time
from typing import Any, ClassVar

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

# ⚠️ **Qui c'era `USCITA_RIPETUTI = 42`, e il ramo `repeated` ci usciva.**
#
# **Decisione del 28 agosto 2026, presa dall'utente**: per un guasto NON di
# autenticazione ripetuto il core **resta vivo in `degraded_llm`** e non esce
# dal processo. §5.6 e §16.1b lo dichiaravano gia' — in `degraded_llm` restano
# vivi T0, la telemetria, il file manager e l'interfaccia — e uscire li'
# contraddiceva la specifica: uno solo dei quattro sottosistemi e' rotto, e
# spegnere gli altri tre e' una perdita, non una difesa.
#
# ⚠️ **Il loop non e' lasciato libero, e il freno non era mai stato il 42** — ma
# non e' nemmeno `puo_riavviare`, e la prima stesura di questa nota lo diceva.
#
# Misurato: `puo_riavviare` ha **un solo lettore in tutto `core/`**, ed e'
# `su_riavvio` qui sotto, che non ha chiamanti. E' un freno su una strada che
# nessuno percorre.
#
# Il freno che GIRA sta in `ClaudeT1`: `self._degradato`, che sopravvive a
# `stop()`, piu' la guardia di `ask()`, che a sessione degradata passa da
# `riavvia_dopo_guasto` e solleva invece di rispondere. E' dentro il processo,
# quindi funziona anche col core avviato a mano fuori da systemd — cioe' quando
# si sta cercando di capire perche' cade, che e' il momento in cui serve.
#
# `USCITA_AUTH = 41` NON e' toccata: li' il core esce, perche' finche' il
# Signore non rifa' il login non c'e' niente che possa tornare a funzionare.

# ⚠️ **Qui c'erano `FINESTRA_RIAVVII_S` e `SOGLIA_RIPETUTI`.** Vivono in
# `core/llm/claude_t1.py`, che e' dove sta la politica di ADR-003: T1 possiede
# il processo, il `returncode`, il riavvio e la finestra. Questo modulo non ne
# ha piu' bisogno — non classifica e non conta il tempo: riceve fatti gia'
# decisi da `riferisci` e ne tiene il referto.

#: Quello che JARVIS dice a voce. Passa dal TTS LOCALE, che non dipende da
#: Claude: se dipendesse, l'annuncio della sessione scaduta sarebbe la prima
#: cosa a non funzionare.
FRASE = (
    "Signore, la mia sessione e' scaduta. Serve una nuova autenticazione."
)
ISTRUZIONE = "esegui `claude` e poi /login"

# ⚠️ **Qui c'erano `FRASE_TRANSIENT` e `FRASE_RIPETUTI`, e sono state TOLTE.**
#
# Le pronunciava `su_riavvio`, che non ha mai avuto un chiamante, e
# `FRASE_TRANSIENT` era identica carattere per carattere a `FRASI["ripresa"]` di
# `core/llm/claude_t1.py`: due frasi uguali in due file, e quella che gira e'
# l'altra. Il referto NON parla — la voce e' di chi ha il guasto fra le mani.
#
# Il loro contenuto — dire che cosa e' andato perso e che cosa e' rimasto — vive
# in `claude_t1.FRASI`, e i test che lo fissano sono migrati con lui.

#: ⚠️ Non dice piu' «riavvia il servizio a mano»: il servizio non si e' fermato.
#: Cio' che si e' fermato e' T1, e il resto di JARVIS continua a rispondere.
ISTRUZIONE_RIPETUTI = ("controlla i log del core; comandi, file e telemetria "
                       "continuano a funzionare")


#: Che cosa deve FARE il Signore, per ciascuna causa di degradazione.
#: ⚠️ Allowlist: un motivo che non e' qui non riceve un'istruzione a caso, ne
#: riceve NESSUNA. Dire la cosa sbagliata e' peggio che tacere — e prima qui
#: c'era un `if` sullo stato, che dava l'istruzione dell'autenticazione a
#: qualunque degradazione.
AZIONI: dict[str, str] = {
    "auth_expired": ISTRUZIONE,
    "riavvii_ripetuti": ISTRUZIONE_RIPETUTI,
}


class EventoT1(Enum):
    """Che cosa e' successo a T1, detto da chi lo possiede.

    ⚠️ **Un vocabolario suo, e non `Uscita` di `claude_t1`.** `Uscita.TRANSIENT`
    significa «degradato per timeout» in un punto e «riavviato con successo» in
    un altro: lo stesso simbolo con due significati opposti produrrebbe un
    advisory per il guasto e uno per il riavvio, cioe' due per un guasto solo.

    Qui ogni voce e' un FATTO COMPIUTO, e ce n'e' una per ciascuno.
    """

    #: Un guasto transitorio, ed e' DAVVERO ripartito.
    RIAVVIATO = "riavviato"
    #: Cade e ricade: si smette (ADR-003, classe `repeated`).
    RIPETUTI = "riavvii_ripetuti"
    #: Non ha risposto in tempo, e non e' stato riavviato.
    NON_RISPONDE = "non_risponde"
    #: ⚠️ L'autenticazione, vista dalla MORTE DEL PROCESSO e non dallo stream.
    #: Vedi `riferisci`: e' un buco misurato di §5.6, non un caso nuovo.
    AUTH_SCADUTA = "auth_expired"


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
    #: Il diario, per funzione come gli altri: `(ragione, azione)`, una riga
    #: per FATTO — dopo i cortocircuiti «gia' detto», non per ripetizione. Chi
    #: lo cabla e' `Engine._annota_guasto`; senza, il referto resta al bus e al
    #: doctor, come prima del 2 settembre 2026, quando domani mattina nessuno
    #: sapeva che T1 era caduto stanotte.
    annota: Callable[[str, str], Awaitable[None]] | None = None
    #: §5.6 — **posseduto da `su_evento`, e da nessun altro.**
    auth_scaduta: bool = False
    #: ADR-003 — la degradazione di T1 per una causa NON di autenticazione,
    #: **posseduta da chi riferisce il guasto di T1, e da nessun altro**.
    degrado_t1: str | None = None
    #: Quante volte T1 e' stato rilanciato per guasti NON di autenticazione.
    riavvii: int = 0
    _visti: list[str] = field(default_factory=list)

    @property
    def stato(self) -> str:
        """`nominal` o `degraded_llm` — **derivato, non scritto.**

        ⚠️ Qui c'erano due campi scrivibili, `stato` e `motivo`, e le DUE cause
        se li contendevano. La conseguenza misurata: dopo tre cadute non-auth,
        un token scaduto arrivava a `su_evento` con lo stato gia'
        `degraded_llm`, usciva dal cortocircuito «gia' detto» e produceva
        **zero frasi, zero advisory, zero uscite**. §5.6 spento da un guasto che
        con l'autenticazione non c'entra.

        Due guasti indipendenti vogliono due campi indipendenti. Lo stato e' la
        loro somma, e nessuno dei due puo' cancellare l'altro.
        """
        return "degraded_llm" if (self.auth_scaduta or self.degrado_t1) else "nominal"

    @property
    def motivo(self) -> str:
        """La causa PRINCIPALE. L'auth vince quando ci sono tutt'e due.

        Non perche' sia piu' grave, ma perche' e' l'unica delle due che chieda
        un'azione al Signore: le altre cause si guardano nei log, questa si
        risolve rifacendo il login. Le vede tutte `stato_doctor()["cause"]`.
        """
        if self.auth_scaduta:
            return "auth_expired"
        return self.degrado_t1 or ""

    @property
    def cause(self) -> list[str]:
        """Tutte le cause vive, nell'ordine in cui vanno lette."""
        fuori = ["auth_expired"] if self.auth_scaduta else []
        if self.degrado_t1:
            fuori.append(self.degrado_t1)
        return fuori

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

        # ⚠️ **Si guarda la CAUSA, non lo stato.** Con `self.stato ==
        # "degraded_llm"` bastava una degradazione di T1 per tutt'altra ragione
        # per rendere §5.6 muto: misurato, dopo tre cadute non-auth un token
        # scaduto produceva zero frasi, zero advisory, zero uscite. E la
        # decisione del 28 agosto — restare vivi — lo rendeva PERMANENTE,
        # perche' da `degraded_llm` non si torna indietro e il processo non
        # muore piu'.
        if self.auth_scaduta:
            return True                      # gia' detto, non lo si ripete

        self.auth_scaduta = True
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
        await self._annota("auth_expired", ISTRUZIONE)
        if self.esci is not None:
            self.esci(USCITA_AUTH)
        return True

    async def riferisci(self, evento: EventoT1) -> None:
        """T1 dice che cosa gli e' successo. Il referto e' di questa classe.

        ⚠️ **Fa tre cose e nient'altro**: conta, registra la causa, pubblica
        l'advisory. **Non parla** — T1 ha gia' parlato, e `FRASE_TRANSIENT` era
        identica carattere per carattere a `FRASI["ripresa"]` di `claude_t1`:
        due voci per un guasto solo. Non classifica, non riavvia, non reinietta,
        non frena. Chi possiede la degradazione non-auth di T1 e' `ClaudeT1`;
        qui si tiene il REFERTO, che e' l'unica meta' che T1 non puo' avere —
        il bus, `stato_doctor()` e il contatore di vita.

        Prima di questa funzione, dopo TRE riavvii veri di T1 `jarvis doctor`
        mostrava `stato: nominal, riavvii: 0` e sul bus non arrivava niente:
        JARVIS lo aveva detto a voce tre volte e la diagnostica che §16.1b crea
        per rispondere a «cosa e' rotto» non lo sapeva. E' §5.6 — «due meta', e
        quella che riferisce era muta» — a ruoli invertiti.

        ⚠️ **`AUTH_SCADUTA` esce col 41, e non e' un'estensione arbitraria.**
        §5.6 vede solo gli eventi dello STREAM, ma un token che scade fra due
        turni fa MORIRE il processo: `ClaudeT1.classifica` lo riconosce dal
        `returncode` 41 o dallo `stderr`, e quella strada non passava da qui.
        Misurato — T1 lo diceva a voce, e insieme: zero advisory, zero uscite,
        `stato_doctor()` a `nominal`. Cioe' testualmente il difetto che la rev
        5.29 dichiara chiuso per §5.6, vivo sull'altra strada di rilevamento.
        Qui NON si parla lo stesso: la voce l'ha gia' messa T1.
        """
        if evento is EventoT1.RIAVVIATO:
            # Un riavvio VERO. Il contatore conta le vite, e prima contava
            # anche quelle rifiutate: il ramo `repeated` incrementava prima di
            # decidere che non si riparte.
            self.riavvii += 1
            await self._pubblica("warn", evento.value, "")
            await self._annota(evento.value, "")
            return

        if evento is EventoT1.AUTH_SCADUTA:
            if self.auth_scaduta:
                return                       # gia' detto, non lo si ripete
            self.auth_scaduta = True
            log.critical("auth_scaduta", origine="morte_del_processo",
                         azione=ISTRUZIONE)
            await self._pubblica("critical", evento.value, ISTRUZIONE)
            await self._annota(evento.value, ISTRUZIONE)
            if self.esci is not None:
                self.esci(USCITA_AUTH)
            return

        if self.degrado_t1 == evento.value:
            return                           # gia' detto, non lo si ripete
        self.degrado_t1 = evento.value
        log.critical("t1_degradato", causa=evento.value)
        await self._pubblica("critical", evento.value,
                             AZIONI.get(evento.value, ""))
        await self._annota(evento.value, AZIONI.get(evento.value, ""))

    async def _annota(self, ragione: str, azione: str) -> None:
        """Una riga nel diario, se c'e' chi la scrive. Una per fatto."""
        if self.annota is not None:
            await self.annota(ragione, azione)

    async def _pubblica(self, livello: str, ragione: str, azione: str) -> None:
        """Solo il bus. La voce e' di chi ha il guasto fra le mani."""
        if self.pubblica is None:
            return
        await self.pubblica({
            "topic": "agent.advisory",
            "level": livello,
            "reason": ragione,
            "action": azione,
            "stato": self.stato,
        })

    def stato_doctor(self) -> dict[str, Any]:
        """Per `jarvis doctor` (§16.1b), riga «T1 auth».

        ⚠️ **L'azione dipende dal MOTIVO, e prima dipendeva solo dallo stato.**
        Qui c'era `ISTRUZIONE if self.stato == "degraded_llm" else ""`, cioe'
        «esegui `claude` e poi /login» per QUALUNQUE degradazione. Misurato:
        dopo tre cadute non-auth il doctor diceva

            motivo = 'riavvii_ripetuti'   azione = 'esegui `claude` e poi /login'

        — la causa giusta e l'istruzione sbagliata, sulla riga che §16.1b chiama
        la piu' importante dello strumento. Il Signore rifarebbe il login per un
        guasto che con l'autenticazione non c'entra.

        Era latente finche' `degraded_llm` non-auth era un preludio all'uscita
        del processo. **La decisione del 28 agosto — restare vivi — lo rende uno
        stato in cui si resta**, e quindi uno che si legge davvero.
        """
        return {
            "stato": self.stato,
            "motivo": self.motivo,
            #: ⚠️ TUTTE le cause vive, non solo la principale. Con un campo
            #: solo, un token scaduto dopo tre cadute cancellava la prima causa
            #: e il doctor dimenticava che T1 stava gia' cadendo.
            "cause": self.cause,
            "riavvii": self.riavvii,
            "azione": (AZIONI.get(self.motivo, "")
                       if self.stato == "degraded_llm" else ""),
        }
