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

    async def ask(self, testo: str, timeout: float = 90.0) -> AsyncIterator[str]:
        """Manda un turno e restituisce i frammenti di testo **mentre arrivano**.

        E' un `AsyncIterator[str]`: entra direttamente nel TTS (§7.4). Aspettare
        la risposta completa costerebbe 500-1500 ms irrecuperabili.
        """
        if self._occupato:
            raise RuntimeError(
                "T1 e' gia' impegnato in un turno. La sessione vocale e' una "
                "sola: chiudere lo stream precedente prima di aprirne un altro."
            )
        self._occupato = True
        try:
            if not self.vivo:
                await self.start()
            proc = self._proc
            assert proc is not None

            msg = {"type": "user", "message": {"role": "user",
                   "content": [{"type": "text", "text": testo}]}}
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

    async def _degrada(self, motivo: Uscita) -> None:
        """Chiude e ANNUNCIA. Mai un'amnesia silenziosa (ADR-003)."""
        await self.stop()
        if motivo is Uscita.AUTH:
            testo = ("Signore, la mia autenticazione e' scaduta. Opero in modalita' "
                     "ridotta: comandi e file continuano a funzionare.")
        elif motivo is Uscita.REPEATED:
            testo = ("Signore, la sessione si e' interrotta piu' volte di seguito. "
                     "Smetto di riprovare e opero in modalita' ridotta.")
        else:
            testo = ("Signore, ho dovuto riavviare la sessione. Ho conservato le Sue "
                     "preferenze, non la conversazione.")
        log.warning("t1_degradato", motivo=motivo.value)
        if self._su_annuncio:
            self._su_annuncio(testo)

    async def riavvia_dopo_guasto(self) -> Uscita:
        """Riparte da un guasto transitorio, reiniettando i SOLI fatti fissati.

        Mai i turni: l'invariante 17 vieta di duplicare la gestione del contesto
        di T1, e riprodurre la conversazione produrrebbe due gestori in
        disaccordo. I fatti fissati sono dell'utente, la conversazione e' di
        Claude Code.
        """
        motivo = self.classifica(self._proc.returncode if self._proc else 1)
        if motivo in (Uscita.AUTH, Uscita.REPEATED):
            await self._degrada(motivo)
            return motivo

        self._riavvii.append(time.time())
        await self.stop()
        await self.start()
        fatti = self._fatti_fissati()
        if fatti:
            async for _ in self.ask("Contesto da ricordare: " + "; ".join(fatti)):
                pass
        await self._degrada(Uscita.TRANSIENT)     # l'annuncio non e' facoltativo
        return Uscita.TRANSIENT
