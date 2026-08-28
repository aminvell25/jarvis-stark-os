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
MAX_RIAVVII, FINESTRA_S = 3, 300.0


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
    ) -> None:
        self._modello = modello
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
        self._proc: asyncio.subprocess.Process | None = None
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
        log.info("t1_avviato", pid=self._proc.pid, modello=self._modello)

    async def stop(self) -> None:
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
        ora = time.time()
        recenti = [t for t in self._riavvii if ora - t < FINESTRA_S]
        return Uscita.REPEATED if len(recenti) >= MAX_RIAVVII else Uscita.TRANSIENT

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
        motivo = self._degradato or self.classifica(
            self._proc.returncode if self._proc else 1)
        if motivo in (Uscita.AUTH, Uscita.REPEATED):
            if self._degradato is None:
                await self._degrada(motivo)       # annunciato UNA volta sola
            return motivo

        self._riavvii.append(time.time())
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
        return Uscita.TRANSIENT
