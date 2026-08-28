"""T1 — Claude Code come processo persistente. SPEC §5.2, invarianti 11, 15, 17.

Perche' persistente e non `claude -p` per turno: §5.2 misura 2,41 s mediani di
costo fisso a freddo — spawn di Node, portachiavi OAuth, discovery, handshake —
e `--bare` non e' una via d'uscita perche' rinuncia all'abbonamento (§5.1).
L'unico modo di eliminare quel costo e' non riavviare mai il processo.

⚠️ **MISURA CHE CONTRADDICE §24 PUNTO 2.** Quella sezione lasciava aperto il
primo token sulla sessione persistente, attendendo 300-900 ms e dichiarando che
oltre 1500 ms «il vantaggio del design si assottiglia e va rivalutato».

Misurato su questa macchina, abbonamento Max, Haiku 4.5:

    a freddo         ~5,6 s
    turni caldi      ~3,2-4,4 s   (mediana su piu' giri: 3,2 s e 4,35 s)
    con --effort low ~3,6 s       nessuna differenza significativa
    con --effort none ~3,4 s      nessuna differenza significativa

La persistenza **funziona** — toglie i 2,2 s di avvio — ma il resto e' il
viaggio verso il modello, e non e' sotto il nostro controllo. §5.2 sospettava
che Haiku 4.5 non esponesse i livelli di effort: le tre misure lo confermano.

Conseguenza sul budget di §7.5: il primo suono non puo' stare entro ~1 s con
questa configurazione. Il dettaglio e le opzioni sono in
`docs/acceptance/FASE-03.md`. Il banco di misura e' `scripts/bench_t1.py`,
perche' questo numero va rimisurato, non ricordato.

CLASSIFICAZIONE DELLE USCITE (ADR-003). §5.6 tratta la scadenza OAuth — il caso
piu' probabile — ma non gli altri. Un OOM o uno stream desincronizzato
farebbero ripartire T1 **senza contesto**, e JARVIS continuerebbe a parlare con
la stessa voce avendo dimenticato tutto, senza dirlo. E' il modo di fallire
peggiore che questo sistema possa avere.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from collections.abc import AsyncIterator, Callable
from enum import Enum
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


class Uscita(str, Enum):
    """Perche' T1 e' morto. Determina se e come si riparte (ADR-003)."""

    AUTH = "auth"            # §5.6: niente riavvio a ciclo, degraded_llm
    TRANSIENT = "transient"  # OOM, crash, stream rotto: si riparte e si annuncia
    REPEATED = "repeated"    # troppi riavvii nella finestra: si smette
    PULITA = "pulita"        # fermato da noi


#: Riavvii tollerati prima di dichiarare `REPEATED`, e finestra in secondi.
#: Quanto stderr di T1 si tiene. **Misurato su questa macchina**, con un figlio
#: che scrive N byte su stderr e poi risponde su stdout:
#:
#:     200 000 byte   il figlio arriva in fondo
#:     300 000 byte   ⚠️ BLOCCATO — non risponde piu'
#:
#: Il tubo di Linux tiene 64 KiB; asyncio ne pompa altrettanti nel proprio
#: `StreamReader` senza che nessuno legga, e **poi** il controllo di flusso
#: mette in pausa la lettura, il tubo si riempie e il figlio si ferma sulla
#: `write`. Fino a ieri `stderr=PIPE` era aperto e non lo leggeva NESSUNO:
#: bastava che `claude` scrivesse trecento kilobyte — un traceback in ciclo, un
#: avviso per token — perche' T1 restasse appeso per sempre, e in silenzio:
#: `ask()` sarebbe andato in timeout, avrebbe degradato, riavviato, e il
#: processo nuovo si sarebbe fermato allo stesso punto.
#:
#: Il numero e' **un tubo pieno**: oltre quello il sistema operativo stesso si
#: sarebbe rifiutato di accumulare senza un lettore, e cio' che serve — i
#: marcatori dell'autenticazione, la coda di un traceback — sta in fondo.
TETTO_STDERR = 65_536

#: Quanto si aspetta l'EOF dello stderr di un processo gia' morto prima di
#: classificarne la causa. E' l'attesa che un `read()` gia' avviato consegni
#: cio' che ha in mano: se scade, si classifica con quello che c'e'.
ATTESA_EOF_S = 2.0

#: ADR-003, classe `repeated`: **«≥ 3 riavvii in 10 minuti»**. I due numeri
#: stanno QUI perche' e' qui che vive la politica: `ClaudeT1` possiede il
#: processo, il `returncode`, lo `stderr` e il riavvio. `core/llm/supervisor.py`
#: li importa da qui per il proprio referto — una sorgente sola.
#:
#: ⚠️ **Erano `3, 300.0` e non erano conformi ad ADR-003, in due modi.** La
#: finestra era di cinque minuti invece di dieci, e il confronto
#: `len(recenti) >= 3` scattava al QUARTO guasto invece che al terzo, perche'
#: non contava quello in corso. Misurato, prima: T1 diceva `repeated` al quarto,
#: il Supervisore al terzo — due meta' della stessa politica in disaccordo su
#: quando smettere.
SOGLIA_RIPETUTI = 3
FINESTRA_RIAVVII_S = 600.0


#: Che cosa JARVIS dice quando la sessione si guasta. ⚠️ **Ogni frase dice una
#: cosa vera nel momento in cui viene pronunciata**, ed e' una correzione: la
#: frase della ripresa la diceva anche il ramo del timeout, che non aveva
#: riavviato niente, e prometteva preferenze conservate da un `_fatti_fissati`
#: che in esercizio tornava la lista vuota.
FRASI: dict[str, str] = {
    "auth": "Signore, la mia autenticazione e' scaduta. Opero in modalita' "
            "ridotta: comandi e file continuano a funzionare.",
    "ripetuti": "Signore, la sessione si e' interrotta piu' volte di seguito. "
                "Smetto di riprovare e opero in modalita' ridotta.",
    "non_risponde": "Signore, la sessione non ha risposto in tempo. La riprendo "
                    "al prossimo turno, senza la conversazione.",
    #: ⚠️ «Rimetto», non «ho conservato»: questa frase si pronuncia PRIMA della
    #: reiniezione, e una frase detta prima non puo' dichiarare compiuta
    #: un'azione che deve ancora riuscire. Vedi `riavvia_dopo_guasto`.
    "ripresa": "Signore, ho dovuto riavviare la sessione. Rimetto le Sue "
               "preferenze, non la conversazione.",
    "ripresa_nuda": "Signore, ho dovuto riavviare la sessione. Riparto senza la "
                    "conversazione.",
    #: E se la reiniezione non riesce, lo si dice: la frase di sopra e' gia'
    #: stata pronunciata, e lasciarla sola sarebbe una promessa non mantenuta.
    "preferenze_perdute": "Signore, non sono riuscito a rimettere le Sue "
                          "preferenze. Riparto da zero.",
}


class ClaudeT1:
    """La sessione vocale. Un processo, vivo fra i turni."""

    def __init__(
        self,
        modello: str,
        cwd: Path,
        persona: Path | None = None,
        su_annuncio: Callable[[str], None] | None = None,
        fatti_fissati: Callable[[], list[str]] | None = None,
        su_evento: Callable[[dict], Any] | None = None,
        #: Dove si RIFERISCE cio' che e' successo a T1 — di solito
        #: `Supervisore.riferisci`. Per funzione, come `su_evento`: T1 non deve
        #: sapere che cosa sia un `Supervisore`.
        #:
        #: ⚠️ **E' un canale DIVERSO da `su_evento`**, e non e' un dettaglio:
        #: `su_evento` osserva lo stream e decide, questo riferisce un fatto
        #: gia' deciso. Mescolarli rimetterebbe la classificazione dalla parte
        #: di chi non ha il processo — ed e' misurato che li' non funziona:
        #: `Supervisore.classifica` non legge nemmeno il proprio parametro.
        riferisci: Callable[[Any], Any] | None = None,
        #: ⚠️ **MONOTONO, non l'ora.** Qui si misura QUANTO TEMPO PASSA fra due
        #: riavvii, e l'ora di sistema puo' saltare all'indietro — un salto
        #: farebbe sembrare «vecchi» tre guasti appena avvenuti, e la classe
        #: `repeated` non scatterebbe. `core/llm/supervisor.py` lo vietava per
        #: iscritto da giorni; qui c'era `time.time()`, non iniettabile.
        orologio: Callable[[], float] = time.monotonic,
    ) -> None:
        self._modello = modello
        self._orologio = orologio
        self._cwd = Path(cwd).expanduser().resolve()
        # RISOLTO, non relativo. Il sottoprocesso gira da `voice-cwd`, non da
        # qui: un percorso relativo non esisterebbe la' dentro, Claude Code
        # uscirebbe subito e `ask()` restituirebbe il vuoto senza spiegare
        # perche'. Misurato: e' esattamente cosi' che si presenta il guasto.
        self._persona = Path(persona).expanduser().resolve() if persona else None
        self._su_annuncio = su_annuncio
        self._fatti_fissati = fatti_fissati or (lambda: [])
        #: Il `Supervisore` di §5.6, per funzione. **Era il proprietario della
        #: degradazione e non riceveva un solo evento**: `su_evento()` non
        #: aveva chiamanti, quindi `jarvis doctor` avrebbe detto `auth ok` con
        #: T1 gia' degradato. Due meta' di §5.6, e quella che riferisce lo
        #: stato era muta.
        self._su_evento = su_evento
        self._riferisci = riferisci
        self._proc: asyncio.subprocess.Process | None = None
        #: La CODA dello stderr del processo vivo. Bytearray e non lista di
        #: righe: `classifica` cerca sottostringhe, e le righe le
        #: ricomporrebbe solo per poi riunirle.
        self._stderr = bytearray()
        self._lettore: asyncio.Task | None = None
        #: Il segno che una degradazione c'e' stata, e che sopravvive a `stop()`.
        #: Vedi `_degrada`: senza, l'amnesia di ADR-003 rientrava dalla porta
        #: accanto al turno seguente. Si azzera SOLO dopo un riavvio riuscito.
        self._degradato: Uscita | None = None
        self._riavvii: list[float] = []
        # Un FLAG, non un lock.
        #
        # Con un `asyncio.Lock` preso dentro `ask()` — che e' un generatore
        # asincrono — il lock resta preso finche' il generatore non viene
        # chiuso. E il barge-in ABBANDONA lo stream a meta': dopo la prima
        # interruzione T1 sarebbe rimasto bloccato per sempre, in attesa di un
        # lock che nessuno avrebbe rilasciato.
        #
        # Con un flag rilasciato in `finally`, l'abbandono lo libera subito
        # (Python chiude il generatore) e una chiamata davvero concorrente
        # fallisce rumorosamente invece di incastrarsi in silenzio.
        self._occupato = False

    # ── argomenti ────────────────────────────────────────────────────────────

    def argv(self) -> list[str]:
        """L'invocazione di §5.2. Verificabile senza avviare nulla."""
        a = [
            "claude",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            # I token uno per uno: e' cio' che fa partire il TTS al primo,
            # invece che a frase finita (§7.4).
            "--include-partial-messages",
            "--replay-user-messages",
            "--model", self._modello,
            # Invariante 15: zero tool nel contesto. Il tier vocale PARLA; le
            # operazioni reali passano dall'allowlist del core (invariante 1).
            "--allowedTools", "",
        ]
        if self._persona:
            a += ["--append-system-prompt-file", str(self._persona)]
        return a

    # ── ciclo di vita ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Avvia il processo. La cwd deve essere dedicata e VUOTA.

        §5.2: senza `--bare`, Claude Code legge il `CLAUDE.md` corrente **e
        superiori**. Lanciarlo dalla radice del progetto gli farebbe caricare
        la costituzione a ogni frase detta a voce.
        """
        if self._proc is not None and self._proc.returncode is None:
            return
        self._cwd.mkdir(parents=True, exist_ok=True)
        residui = [p.name for p in self._cwd.iterdir()]
        if residui:
            log.warning("voice_cwd_non_vuota", cwd=str(self._cwd), contiene=residui,
                        conseguenza="verranno caricati a ogni turno (§5.2)")

        self._proc = await asyncio.create_subprocess_exec(
            *self.argv(), cwd=str(self._cwd),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # ⚠️ **Qualcuno deve leggere quel tubo.** Vedi `TETTO_STDERR`: senza,
        # trecento kilobyte su stderr fermano il figlio per sempre.
        self._stderr = bytearray()
        self._lettore = asyncio.create_task(self._leggi_stderr(self._proc))
        log.info("t1_avviato", pid=self._proc.pid, modello=self._modello)

    async def _leggi_stderr(self, proc) -> None:
        """Svuota lo stderr nel `self._stderr`, tenendone la coda.

        Non solleva verso nessuno: e' un compito di sfondo, e un lettore che
        cade deve al massimo far perdere una diagnosi — mai il turno.
        """
        try:
            while True:
                pezzo = await proc.stderr.read(4096)
                if not pezzo:
                    return                       # EOF: il processo e' finito
                self._stderr += pezzo
                if len(self._stderr) > TETTO_STDERR:
                    del self._stderr[:-TETTO_STDERR]
        except asyncio.CancelledError:
            raise
        except Exception as exc:                          # pragma: no cover
            log.warning("stderr_non_letto", errore=repr(exc),
                        conseguenza="la causa della morte non sara' leggibile")

    async def _ferma_lettore(self) -> None:
        """Chiude il lettore, ASPETTANDO l'EOF.

        ⚠️ Non si annulla e basta: alla morte del processo il lettore vede EOF e
        finisce da se', e **gli ultimi byte sono proprio quelli che spiegano la
        morte**. Annullarlo li butterebbe via nell'istante in cui servono.
        """
        t, self._lettore = self._lettore, None
        if t is None or t.done():
            return
        try:
            await asyncio.wait_for(t, timeout=ATTESA_EOF_S)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        except Exception as exc:                          # pragma: no cover
            log.warning("lettore_stderr_caduto", errore=repr(exc))

    async def stderr_del_morto(self) -> str:
        """Lo stderr del processo appena morto, atteso fino all'EOF.

        ⚠️ Senza l'attesa, `classifica` leggerebbe un buffer a meta' proprio
        nell'istante in cui i byte che mancano sono quelli che spiegano la
        morte — ed e' una corsa che si perde piu' spesso quando il processo
        muore in fretta, cioe' nel caso peggiore.
        """
        await self._ferma_lettore()
        return self._stderr.decode("utf-8", "replace")

    async def stop(self) -> None:
        # Prima il lettore, e anche se il processo non c'e' piu': un compito
        # che sopravvive al suo processo e' un compito che nessuno fermera'.
        await self._ferma_lettore()
        if self._proc is None:
            return
        proc, self._proc = self._proc, None
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        log.info("t1_fermato")

    @property
    def vivo(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    # ── conversazione ────────────────────────────────────────────────────────

    async def ask(self, testo: str, timeout: float = 90.0, *, nota: str | None = None) -> AsyncIterator[str]:
        """Manda un turno e restituisce i frammenti di testo **mentre arrivano**.

        E' un `AsyncIterator[str]`: entra direttamente nel TTS (§7.4). Aspettare
        la risposta completa costerebbe 500-1500 ms irrecuperabili.
        """
        if self._occupato:
            raise RuntimeError(
                "T1 e' gia' impegnato in un turno. La sessione vocale e' una "
                "sola: chiudere lo stream precedente prima di aprirne un altro."
            )
        # ⚠️ **UN PROCESSO MORTO NON SI RIAVVIA IN SILENZIO.**
        #
        # Qui c'era, dentro il `try`, `if not self.vivo: await self.start()`: T1
        # moriva, `ask()` ne apriva uno nuovo con la sessione VUOTA, e JARVIS
        # rispondeva con la stessa voce avendo perso la conversazione — **senza
        # dirlo**. E' testualmente cio' che ADR-003 chiama «il modo di fallire
        # peggiore che questo sistema possa avere», e la funzione che lo fa
        # bene — `riavvia_dopo_guasto` — non aveva un solo chiamante in
        # produzione: l'ha trovata `scripts/orfani.py`.
        #
        # La distinzione e' fra i due modi di NON essere vivo:
        #   `_proc is None`          mai avviato, o fermato di proposito da
        #                            `stop()`: si avvia e basta, non c'e' niente
        #                            da annunciare
        #   returncode non nullo     e' MORTO da solo: si passa da
        #                            `riavvia_dopo_guasto`, che reinietta i soli
        #                            fatti fissati (invariante 17) e ANNUNCIA
        #
        # ⚠️ E sta **prima** di `self._occupato = True`, non dopo:
        # `riavvia_dopo_guasto` usa `ask()` per reiniettare i fatti, e a
        # bandiera gia' alzata la rientranza solleverebbe «T1 e' gia' impegnato»
        # — cioe' la correzione dell'amnesia diventerebbe un turno perso.
        # ⚠️ `self._degradato` per PRIMO: `_degrada` chiama `stop()`, che azzera
        # `_proc`, quindi senza questo segno la condizione di destra e' falsa
        # proprio dopo una degradazione — e si cadeva su `if not self.vivo:
        # await self.start()`, cioe' una sessione vuota aperta in silenzio.
        if self._degradato is not None or (
                self._proc is not None and self._proc.returncode is not None):
            esito = await self.riavvia_dopo_guasto()
            if esito in (Uscita.AUTH, Uscita.REPEATED):
                # Degradato: `_degrada` l'ha gia' annunciato a voce. Qui si
                # solleva invece di rispondere, perche' rispondere sarebbe
                # esattamente la bugia che questo blocco esiste per impedire.
                raise RuntimeError(f"T1 degradato dopo un guasto: {esito.value}")

        self._occupato = True
        try:
            if not self.vivo:
                await self.start()
            proc = self._proc
            assert proc is not None

            # §7.4: la meta' mancante del barge-in. Se il turno precedente e'
            # stato interrotto, la sessione di T1 crede di aver detto tutto —
            # `_drena()` scarta il resto senza dirlo a nessuno. La cornice
            # gliene da' notizia, ed e' **una cornice** e non una frase perche'
            # deve essere impossibile scambiarla per parole del Signore.
            # Vedi `core/llm/sistema.py`.
            corpo = f"{nota}\n\n{testo}" if nota else testo
            if nota:
                # L'unico modo di sapere, da fuori, che la cornice e' partita.
                # Senza questa riga «la nota e' arrivata» sarebbe una lettura
                # del sorgente, non un'osservazione.
                log.info("nota_di_sistema", caratteri=len(nota))
            msg = {"type": "user", "message": {"role": "user",
                   "content": [{"type": "text", "text": corpo}]}}
            proc.stdin.write((json.dumps(msg) + "\n").encode())
            await proc.stdin.drain()

            t0 = time.perf_counter()
            primo = None
            visto_result = False
            try:
                while True:
                    riga = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
                    if not riga:
                        break
                    try:
                        e = json.loads(riga)
                    except json.JSONDecodeError:
                        continue          # una riga illeggibile non ferma il turno

                    tipo = e.get("type")
                    if tipo == "stream_event":
                        d = e.get("event", {}).get("delta", {})
                        if d.get("type") == "text_delta" and (t := d.get("text")):
                            if primo is None:
                                primo = time.perf_counter()
                                log.info("t1_primo_token",
                                         ms=round((primo - t0) * 1000))
                            yield t
                    elif tipo == "result":
                        visto_result = True
                        break
                    elif tipo == "system" and e.get("subtype") == "api_retry":
                        # §5.6 ha UN proprietario, ed e' il `Supervisore`: e'
                        # lui che annuncia, pubblica l'advisory e fa uscire il
                        # core col codice che `RestartPreventExitStatus`
                        # riconosce. Qui si smette e basta — annunciare due
                        # volte sarebbe due meta' in disaccordo.
                        if self._su_evento is not None and await self._su_evento(e):
                            log.warning("t1_fermo_per_auth", gestore="supervisore")
                            # ⚠️ **Il segno, anche qui.** `stop()` azzera `_proc`,
                            # e senza segno al turno dopo la guardia di `ask()`
                            # e' falsa: sessione nuova, vuota, in silenzio. E'
                            # lo stesso difetto chiuso in `_degrada`, nel ramo
                            # che allora non avevo toccato.
                            self._degradato = Uscita.AUTH
                            await self.stop()
                            return
                        # ⚠️ Ripiego per quando il supervisore non c'e' —
                        # i test lo costruiscono da solo, e un T1 senza
                        # supervisore che ignorasse un token scaduto
                        # riproverebbe a ciclo, che e' cio' che §5.6 vieta.
                        if "authentication" in json.dumps(e).lower():
                            await self._degrada(Uscita.AUTH)
                            return
            except asyncio.TimeoutError:
                log.error("t1_timeout", secondi=timeout)
                await self._degrada(Uscita.TRANSIENT)
                return

            if primo is not None:
                log.info("t1_turno_completo",
                         totale_ms=round((time.perf_counter() - t0) * 1000))
        finally:
            # ABBANDONARE UN TURNO DESINCRONIZZA LO STREAM.
            #
            # Il barge-in chiude questo generatore a meta'. Ma il modello sta
            # gia' generando, e i suoi eventi continuano ad arrivare su stdout:
            # il turno successivo li leggerebbe come propri e vedrebbe subito
            # un `result` che non gli appartiene, restituendo il vuoto.
            #
            # Misurato: dopo un abbandono, il turno seguente tornava una
            # stringa vuota. Si drena fino alla fine del turno abbandonato
            # PRIMA di liberare, e lo si fa in sottofondo perche' l'utente ha
            # gia' avuto il suo silenzio.
            if primo is not None and not visto_result:
                asyncio.create_task(self._drena(proc))
            else:
                self._occupato = False

    async def _drena(self, proc, timeout: float = 90.0) -> None:
        """Consuma cio' che resta del turno abbandonato, poi libera.

        Senza, il turno successivo erediterebbe gli eventi di questo.
        """
        try:
            while True:
                riga = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
                if not riga:
                    break
                try:
                    if json.loads(riga).get("type") == "result":
                        break
                except json.JSONDecodeError:
                    continue
        except (asyncio.TimeoutError, Exception):
            pass
        finally:
            self._occupato = False
            log.info("t1_stream_risincronizzato")

    # ── guasti ───────────────────────────────────────────────────────────────

    def classifica(self, returncode: int | None, stderr: str = "") -> Uscita:
        """Perche' e' morto (ADR-003)."""
        if returncode is None:
            return Uscita.PULITA
        testo = stderr.lower()
        if "authentication" in testo or "unauthorized" in testo or returncode == 41:
            return Uscita.AUTH
        ora = self._orologio()
        recenti = [t for t in self._riavvii if ora - t < FINESTRA_RIAVVII_S]
        # ⚠️ `+ 1` per il guasto IN CORSO: senza, «tre riavvii» diventava
        # «quattro guasti», e ADR-003 dice tre.
        return (Uscita.REPEATED if len(recenti) + 1 >= SOGLIA_RIPETUTI
                else Uscita.TRANSIENT)

    async def _riferisci_al_referto(self, nome: str) -> None:
        """Manda un fatto compiuto a chi tiene il referto. Non solleva mai.

        Un referto che cade non deve poter fermare un riavvio: il guasto e' gia'
        stato annunciato a voce, e perdere la riga sul bus e' meno grave che
        perdere la sessione.
        """
        if self._riferisci is None:
            return
        try:
            from core.llm.supervisor import EventoT1

            await self._riferisci(EventoT1[nome])
        except Exception as exc:                          # pragma: no cover
            log.error("referto_non_riuscito", evento=nome, errore=repr(exc))

    def _annuncia(self, chiave: str) -> None:
        """Una frase sola, e dice una cosa VERA nel momento in cui la dice.

        ⚠️ **`ripresa` la pronuncia solo chi ha davvero riavviato.** Prima era
        `_degrada(TRANSIENT)` a dirla, e `_degrada` **chiude**: il ramo del
        timeout la pronunciava dopo aver fermato T1 e senza aver riavviato
        niente. Due bugie in una frase — «ho dovuto riavviare» quando nessuno
        aveva riavviato, e «ho conservato le Sue preferenze» con
        `_fatti_fissati` che in esercizio tornava la lista vuota.
        """
        log.warning("t1_degradato", motivo=chiave)
        if self._su_annuncio:
            self._su_annuncio(FRASI[chiave])

    async def _degrada(self, motivo: Uscita) -> None:
        """CHIUDE e annuncia. Mai un'amnesia silenziosa (ADR-003).

        ⚠️ E lascia un segno: `self._degradato`. Senza, `stop()` azzerava
        `_proc` e al turno dopo la guardia di `ask()` — «e' morto da solo?» —
        era **falsa**, quindi si cadeva su `if not self.vivo: await self.start()`
        e si apriva una sessione VUOTA in silenzio. Cioe' esattamente l'amnesia
        che ADR-003 esiste per vietare, un turno dopo, e per la strada piu'
        frequente di tutte: il timeout.
        """
        await self.stop()
        self._degradato = motivo
        self._annuncia({Uscita.AUTH: "auth",
                        Uscita.REPEATED: "ripetuti"}.get(motivo, "non_risponde"))
        await self._riferisci_al_referto({
            Uscita.AUTH: "AUTH_SCADUTA",
            Uscita.REPEATED: "RIPETUTI",
        }.get(motivo, "NON_RISPONDE"))

    async def riavvia_dopo_guasto(self) -> Uscita:
        """Riparte da un guasto transitorio, reiniettando i SOLI fatti fissati.

        Mai i turni: l'invariante 17 vieta di duplicare la gestione del contesto
        di T1, e riprodurre la conversazione produrrebbe due gestori in
        disaccordo. I fatti fissati sono dell'utente, la conversazione e' di
        Claude Code.
        """
        # ⚠️ **Il motivo RICORDATO vince sulla riclassificazione.** Dopo un
        # `_degrada` il processo non c'e' piu', e `classifica(1)` direbbe
        # `TRANSIENT` a un token scaduto: si riproverebbe a ciclo proprio nel
        # caso in cui §5.6 vieta di riprovare.
        motivo = self._degradato
        if motivo is None:
            # ⚠️ **Con lo stderr, e prima non ci arrivava.** `classifica` ha tre
            # criteri per l'autenticazione — `returncode == 41`, «authentication»
            # e «unauthorized» nello stderr — e questa chiamata gliene passava
            # UNO. Due su tre erano irraggiungibili sulla strada viva.
            motivo = self.classifica(self._proc.returncode if self._proc else 1,
                                     await self.stderr_del_morto())
        if motivo in (Uscita.AUTH, Uscita.REPEATED):
            if self._degradato is None:
                await self._degrada(motivo)       # annunciato UNA volta sola
            return motivo

        self._riavvii.append(self._orologio())
        await self.stop()
        await self.start()
        # ⚠️ **Solo qui, e non prima.** Se `start()` solleva, lo stato resta
        # degradato e il turno dopo ripassa da questa porta invece di aprire una
        # sessione vuota in silenzio. E deve stare PRIMA della reiniezione, che
        # usa `ask()`: la guardia leggerebbe il segno e rientrerebbe.
        self._degradato = None
        fatti = self._fatti_fissati()

        # ⚠️ **L'ANNUNCIO PRIMA DEL REPLAY**, e la ragione sta scritta da giorni
        # nel docstring di `Supervisore.su_riavvio`: «se il replay fallisse,
        # l'utente ha comunque sentito che la conversazione non c'e' piu'».
        #
        # Qui l'ordine era capovolto. Misurato: con un replay che solleva,
        # **zero frasi**, `_degradato` gia' azzerato e una sessione viva e
        # VUOTA — quindi al turno dopo la guardia e' falsa e JARVIS risponde
        # senza conversazione e senza fatti, in silenzio. E' testualmente «il
        # modo di fallire peggiore che questo sistema possa avere» di ADR-003,
        # rientrato dentro la correzione che lo doveva chiudere.
        self._annuncia("ripresa" if fatti else "ripresa_nuda")
        if fatti:
            try:
                async for _ in self.ask("Contesto da ricordare: "
                                        + "; ".join(fatti)):
                    pass
            except Exception as exc:
                # Non si risolleva: la sessione E' viva, e far fallire il turno
                # sprecherebbe un riavvio riuscito. Si dice, e si continua.
                log.error("fatti_non_reiniettati", errore=repr(exc))
                self._annuncia("preferenze_perdute")
        # ⚠️ **`_annuncia` e non `_degrada`**: `_degrada` comincia con
        # `await self.stop()`, e chiamato dopo il riavvio uccideva il processo
        # appena avviato buttando via i fatti appena reiniettati. Misurato —
        # dopo un «riavvio riuscito» T1 restava morto.
        #
        # Il referto arriva DOPO, e dice `RIAVVIATO`: un fatto compiuto, non
        # un'intenzione. Prima di questa riga, dopo tre riavvii veri il doctor
        # mostrava `nominal, riavvii: 0`.
        await self._riferisci_al_referto("RIAVVIATO")
        return Uscita.TRANSIENT
