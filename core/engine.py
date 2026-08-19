"""Radice di composizione del core — SPEC §3.2. **L'unica**, da Fase 9.

§3.2 disegna il CORE come un processo solo: engine, router, memoria, Governor,
scheduler GPU, tool layer, T0/T1/T2, voce, sandbox. Fino alla Fase 8 questo
file ne componeva meta', e `VoicePipeline` era costruita soltanto dai test —
due radici, e ogni fase dalla 5 alla 8 ha dichiarato «non verificato» qualcosa
che dipendeva da quella separazione: la mesh agenti con T1 vivo, ARGUS su stati
reali, le regole 2 e 3 del gate news, la menzione vocale.

Fase 9 le unisce. Ma unirle vuol dire che il core, appena parte, aprirebbe il
microfono e spawnerebbe un processo `claude` — e questo NON deve accadere per
il fatto di aver avviato un servizio.

## L'avvio e' a gradi

    sempre              impostazioni, piattaforma, allowlist, GPU, socket, tool
    voice.enabled       wake Vosk, STT/TTS, T1 persistente, supervisore
    news.enabled        collector, gate, budget
    vision.enabled      ARGUS e telecamera (Fase 7 ha spia e consenso)

Fail-closed come tutto il resto: senza gli interruttori il core parte come
partiva in Fase 8. Gli interruttori sono predefiniti a `false` nello schema, e
non nel file di esempio: una configurazione scritta prima che il campo
esistesse non deve poter accendere un microfono.
"""

from __future__ import annotations

import asyncio
import os
import signal
import time
from collections.abc import Callable
from typing import Any

import structlog

from core.gpu_scheduler import GpuScheduler
from core.memory.store import MemoryStore
from core.platform import Paths, gpu as platform_gpu, paths as platform_paths, sensors as platform_sensors
from core.platform.linux_sandbox import SECCOMP_APPLICATO
from core.settings import Settings, SettingsStore
from core.agents_mesh import snapshot as mesh_snapshot
from core.llm import grammar
from core.llm.governor import Governor
from core.llm.supervisor import USCITA_AUTH, Supervisore
from core.tools import registry
from core.tools.confirm import ConfirmBroker
from core.tools.code import register_code_tool
from core.tools.files import register_file_tools
from core.tools.geo import leggi_fusi, register_geo_tools
from core.tools.introspect import leggi_albero, leggi_note, register_introspect_tools
from core.tools.memory import register_memory_tools
from core.tools.web import register_web_tools
from core.tools.system import register_system_tools
from core.ws_server import WsServer

log = structlog.get_logger(__name__)

FASE = 9


class Engine:
    """Il core in esecuzione."""

    def __init__(self, paths: Paths | None = None) -> None:
        self._paths = paths or platform_paths()
        self._avvio = time.monotonic()

        self._store = SettingsStore(self._paths)
        self._sensors = platform_sensors()
        self._gpu_scheduler = GpuScheduler(platform_gpu(), self._sensors)

        # Il Governor e il supervisore si costruiscono SEMPRE: sono contatori e
        # regole, non processi. Averli anche a voce spenta vuol dire che
        # `jarvis doctor` e la mesh agenti dicono qualcosa di vero invece di
        # «non collegato», e che il giorno in cui la voce si accende non cambia
        # nient'altro.
        self._governor = Governor()
        self._supervisore = Supervisore(
            parla=self._parla_locale,
            pubblica=lambda msg: self._ws.broadcast(msg),
            esci=self._esci_per_auth,
        )
        #: Composti solo se le impostazioni lo dicono — vedi `_gradi()`.
        self._t1 = None
        self._voce = None
        self._watcher = None
        self._codice_uscita = 0

        # La radice di composizione POSSIEDE l'allowlist: e' lei a decidere
        # che cosa esiste. Svuotare prima di registrare rende l'avvio
        # idempotente senza nascondere i doppioni dentro una fase.
        registry.clear()
        register_system_tools(self._sensors)
        register_geo_tools()
        # I sorgenti e i documenti del progetto, per i moduli «Core sorgente» e
        # «Piani d'archivio» di §13. Nessun parametro path: vedi l'intestazione
        # di `core/tools/introspect.py`.
        register_introspect_tools()
        # §13: la memoria di Fase 4 esisteva, era provata, e NON era registrata
        # nella radice di composizione — quindi i suoi quattro tool non
        # esistevano nel processo vero. Una riga mancante, trovata cercando chi
        # potesse produrre l'archivio. Dichiarata in `SEZIONE-13.md`.
        self._memoria = MemoryStore(self._paths.data_dir() / "memory_data")
        register_memory_tools(lambda: self._memoria)
        # ADR-006 + ADR-008: l'unico punto in cui gira codice generato, e gira
        # nel profilo che parte da una radice vuota. Registrato QUI perche' §13
        # ha trovato i quattro tool di memoria scritti, provati e mai
        # registrati: nel processo vero non esistevano.
        register_code_tool(lambda: self._store.current)
        # `pubblica` chiude la catena tool -> socket -> pannello. Il WS
        # nasce dopo, quindi si passa una lambda e non il metodo.
        register_web_tools(lambda: self._store.current,
                           lambda msg: self._ws.broadcast(msg))
        register_file_tools(lambda: self._store.current, lambda: self._paths)

        self._ws = WsServer(
            self.state_snapshot, self._sensors, self._paths,
            on_confirm=lambda rid, ok: self._broker.rispondi(rid, ok),
            mesh_provider=self.agents_mesh,
            iniziale_provider=self.stato_pannelli,
        )

        # Il broker pubblica sul socket, e il registry gli chiede il permesso
        # prima di ogni tool distruttivo. Senza questo collegamento i tool con
        # side_effect NON funzionano (fail-closed): e' il verso giusto.
        self._broker = ConfirmBroker(self._ws.broadcast)
        registry.set_confirm_hook(self._broker.richiedi)
        self._stop = asyncio.Event()

    # ── stato ────────────────────────────────────────────────────────────────

    @property
    def settings(self) -> Settings:
        return self._store.current

    @property
    def uptime_s(self) -> float:
        return time.monotonic() - self._avvio

    def agents_mesh(self) -> dict[str, Any]:
        """Il grafo degli agenti per il pannello di §13.

        T1 e T2 non sono composti qui — vivono nella pipeline vocale — e la
        mesh lo dice: `non collegato`, non `inerte`. La differenza e' quella
        fra «non c'e'» e «c'e' e non sta facendo niente», e su un pannello di
        stato e' l'informazione principale.
        """
        return mesh_snapshot(
            regole_t0=len(grammar.regole()),
            tool_registrati=len(registry.describe_all()),
            # Da Fase 9 arrivano gli OGGETTI VERI. Il pannello di §13 smette di
            # dire «non collegato» quando davvero collegato lo e'.
            governor=self._governor,
            t1=self._t1,
        )

    def state_snapshot(self) -> dict[str, Any]:
        """Lo stato completo per un client che si collega.

        ⚠️ **Nessun segreto.** Le chiavi compaiono per NOME, mai per valore:
        `Secrets.present()` restituisce i nomi valorizzati. Il rimando a
        `settings.model_dump()` porterebbe con se' i `SecretStr`, ed e' il
        modo esatto in cui una chiave finirebbe sul filo.
        """
        s = self.settings
        misura = self._gpu_scheduler.headroom()
        gpu_mem = misura[1]
        return {
            "fase": FASE,
            "core": {
                "pid": os.getpid(),
                "uptime_s": round(self.uptime_s, 1),
                "seccomp": SECCOMP_APPLICATO,
            },
            "ws": {
                "socket": str(self._ws.socket_path),
                "clients": self._ws.client_count,
            },
            "settings": {
                "voice": {
                    "stt_provider": s.voice.stt_provider,
                    "tts_provider": s.voice.tts_provider,
                    "fallback_on_error": s.voice.fallback_on_error,
                },
                "llm": {"backend": s.llm.backend, "t1_model": s.llm.t1_model},
                "fs": {
                    "workspace": str(s.fs.workspace),
                    "allowed_roots": [str(p) for p in s.fs.allowed_roots],
                    "trash_only": s.fs.trash_only,
                },
                "ui": {"target_fps": s.ui.target_fps, "grid_px": s.ui.grid_px},
                "chiavi_presenti": sorted(s.secrets.present()),   # NOMI, non valori
            },
            # Da Fase 9: i sottosistemi che §16.1b elenca e che fino a ieri
            # `jarvis doctor` doveva dichiarare «non ancora implementato».
            "voce": {
                "abilitata": s.voice.enabled,
                "t1_vivo": bool(self._t1 is not None and self._t1.vivo),
                "auth": self._supervisore.stato_doctor(),
                "wake_model": str(s.voice.wake.model),
                "wake_frasi": len(s.voice.wake.phrases),
            },
            "quota": self._governor.stato(),
            "news": {"abilitate": s.news.enabled, "collegato": self._watcher is not None},
            "tools": registry.describe_all(),
            "gpu": (
                {
                    "driver": gpu_mem.driver,
                    "total_bytes": gpu_mem.total,
                    "used_bytes": gpu_mem.used,
                    "unified": gpu_mem.unified,
                    "headroom_bytes": misura[0],
                }
                if gpu_mem is not None
                else None
            ),
        }

    # ── lo stato iniziale della scrivania (§13) ──────────────────────────────

    async def stato_pannelli(self) -> list[dict[str, Any]]:
        """I dati che i pannelli di §13 non possono chiedere da soli.

        Quattro topic — `source.tree`, `geo.timezones`, `archive.notes`,
        `fs.list` — erano consumati da sei pannelli e prodotti da nessuno: i
        pannelli mostravano il proprio stato vuoto perche' quello era il vero,
        e meta' scrivania restava spenta.

        Non li chiede il renderer, e non e' una svista: **il renderer non puo'
        chiedere niente** (invariante 1, §6.3). Li manda il core a chi si
        collega, una volta, come gia' fa con `state.snapshot` e `agent.mesh`.

        Ogni sorgente e' avvolta a se'. Un disco lento su una cartella non deve
        togliere il globo, e un guasto vale il pannello che riguarda: chi
        fallisce lascia il proprio pannello allo stato vuoto, che e' l'unica
        cosa onesta da mostrare quando un dato non c'e' (invariante 23).
        """
        fuori: list[dict[str, Any]] = []

        def prova(nome: str, f: Callable[[], dict[str, Any]]) -> None:
            try:
                fuori.append(f())
            except Exception as exc:                          # noqa: BLE001
                log.warning("stato_iniziale_parziale", sorgente=nome,
                            errore=str(exc)[:120])

        prova("source.tree", lambda: {
            "topic": "source.tree", "files": leggi_albero(),
        })
        prova("archive.notes", lambda: {
            # In chiaro: qui l'unico consumatore e' il DOM. La versione
            # avvolta in `<untrusted_source>` la produce il TOOL, per chi
            # invece potrebbe metterla nel contesto di un LLM. Due lettori
            # della stessa sorgente, non una catena che apre una busta.
            "topic": "archive.notes", "note": leggi_note(),
        })
        prova("geo.timezones", lambda: {
            "topic": "geo.timezones",
            "zone": [{"nome": z["nome"], "lat": z["lat"], "lon": z["lon"]}
                     for z in leggi_fusi()],
        })

        # La workspace passa dal TOOL, non da un secondo `iterdir()`: e' sotto
        # le radici consentite, e leggerla scavalcando l'allowlist sarebbe una
        # seconda strada verso il disco (invariante 2).
        esito = await registry.invoke("list_dir",
                                      {"path": str(self.settings.fs.workspace)})
        if esito.ok:
            fuori.append({"topic": "fs.list", **esito.output})
        else:
            log.info("workspace_non_elencabile", motivo=esito.error)

        return fuori

    # ── T0 verso la scrivania (§7.6, §13) ────────────────────────────────────

    async def esegui_t0(self, intent: grammar.Intent) -> dict[str, Any]:
        """L'esecutore T0 del router di §21.5. **Non esisteva.**

        `build_router` compariva soltanto nei test: gli intenti `open_panel`,
        `hide_all`, `switch_workspace` — nella grammatica e nel corpus di cento
        frasi dalla Fase 3 — non avevano nessuna strada verso la scrivania.

        Due strade, ed entrambe sono **allowlist**, mai un ramo che lascia
        passare il resto. E' la stessa forma di `core/gestures/mapping.py`,
        deliberatamente: se le gesture e la voce arrivassero al sistema per due
        vie diverse, una delle due sarebbe la piu' debole.

            intento di INTERFACCIA  -> grammar.INTENTI_UI, e finisce sul socket
            intento che nomina un TOOL -> registry.invoke(), con la conferma
                                          umana dove serve (invariante 3)

        Un intento che non e' ne' l'uno ne' l'altro si RIFIUTA. Non solleva:
        siamo sul percorso della voce, e un'eccezione qui zittirebbe JARVIS.
        """
        if intent is None:
            return {"ok": False, "tier": "t0", "error": "nessun intento"}

        if intent.tool in grammar.INTENTI_UI:
            # Gli ARGOMENTI viaggiano con l'intento. `open_panel` senza
            # `{"panel": "globo"}` non e' un comando, e' una categoria — ed e'
            # esattamente cio' che `VoicePipeline._su_azione` lasciava cadere.
            await self._ws.broadcast({
                "topic": "ui.intent", "intento": intent.tool, "args": intent.args,
            })
            log.info("t0_ui", intento=intent.tool, args=intent.args)
            return {"ok": True, "tier": "t0", "intento": intent.tool}

        if intent.tool in registry.names():
            esito = await registry.invoke(intent.tool, intent.args)
            log.info("t0_tool", tool=intent.tool, ok=esito.ok)
            return {"ok": esito.ok, "tier": "t0", "tool": intent.tool,
                    "output": esito.output, "error": esito.error}

        log.warning("t0_intento_senza_destinazione", intento=intent.tool)
        return {"ok": False, "tier": "t0", "intento": intent.tool,
                "error": f"l'intento {intent.tool!r} non e' ne' un'azione "
                         f"della scrivania ne' un tool dell'allowlist"}

    # ── i gradi dell'avvio (§3.2, Fase 9) ────────────────────────────────────

    async def _parla_locale(self, frase: str) -> None:
        """L'annuncio del supervisore, con la voce che NON dipende da Claude.

        §5.6 lo dice esplicitamente: se l'annuncio della sessione scaduta
        passasse dal modello, sarebbe la prima cosa a non funzionare proprio
        quando serve. A voce spenta resta comunque nel log e sul bus.
        """
        log.critical("annuncio_vocale", frase=frase)
        if self._voce is not None:
            await self._voce.annuncia(frase)

    def _esci_per_auth(self, codice: int) -> None:
        """§5.6: si ferma, e con un codice che la unit systemd riconosce.

        Non si chiama `sys.exit()` da un callback dentro il loop: si registra
        il codice e si chiede l'arresto pulito, cosi' il socket viene chiuso e
        non resta un file orfano in $XDG_RUNTIME_DIR.
        """
        self._codice_uscita = codice
        log.critical("uscita_per_auth", codice=codice)
        self._stop.set()

    async def _gradi(self) -> None:
        """Compone cio' che le impostazioni accendono, e niente altro."""
        s = self._store.current

        if s.voice.enabled:
            # Import PIGRO, come il tracker di Fase 7: `vosk` e i provider
            # audio pesano, e a voce spenta non devono nemmeno essere caricati.
            from core.llm.claude_t1 import ClaudeT1

            # La cwd di T1 e' VUOTA e dedicata (invariante 15): da li' Claude
            # Code non carica ne' `CLAUDE.md` ne' i subagent, che a ogni frase
            # detta a voce sarebbero contesto pagato e mai usato (§5.2).
            cwd = self._paths.data_dir() / "voice-cwd"
            cwd.mkdir(parents=True, exist_ok=True)
            self._t1 = ClaudeT1(
                modello=s.llm.t1_model,
                cwd=cwd,
                persona=self._paths.config_dir() / "voice-persona.md",
                su_annuncio=lambda f: log.warning("ripiego_annunciato", testo=f),
            )
            await self._t1.start()
            log.info("grado_acceso", grado="voce", t1=s.llm.t1_model)
        else:
            log.info("grado_spento", grado="voce",
                     perche="voice.enabled = false: nessun microfono, nessun processo claude")

        if s.news.enabled:
            from core.news.collectors.rss import RssCollector
            from core.news.feeds import Watcher
            from core.news.gate import Gate

            self._watcher = Watcher(
                [RssCollector()],
                # Il `MemoryStore` non era passato, e senza di lui
                # «non parlarmene piu'» (§15 regola 5) non sopravviveva al
                # riavvio: il file markdown c'era, nessuno lo leggeva.
                Gate(self._memoria, max_per_ora=s.news.max_interruptions_per_hour),
                lambda msg: self._ws.broadcast(msg),
            )
            log.info("grado_acceso", grado="news",
                     tetto=s.news.max_interruptions_per_hour)
        else:
            log.info("grado_spento", grado="news")

        if not s.vision.enabled:
            log.info("grado_spento", grado="vision",
                     perche="vision.enabled = false: nessuna telecamera")

    async def _spegni_gradi(self) -> None:
        if self._t1 is not None:
            await self._t1.stop()
            log.info("grado_spento", grado="voce", perche="arresto")

    # ── ciclo di vita ────────────────────────────────────────────────────────

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._chiedi_stop, sig)

        self._store.start()
        try:
            async with self._ws:
                await self._gradi()
                log.info(
                    "core_avviato",
                    fase=FASE,
                    pid=os.getpid(),
                    socket=str(self._ws.socket_path),
                    tool=registry.names(),
                    seccomp=SECCOMP_APPLICATO,
                )
                await self._stop.wait()
        finally:
            await self._spegni_gradi()
            self._store.stop()
            log.info("core_fermato", uptime_s=round(self.uptime_s, 1),
                     codice=self._codice_uscita)

    def _chiedi_stop(self, sig: signal.Signals) -> None:
        log.info("segnale_ricevuto", segnale=sig.name)
        self._stop.set()


async def main() -> int:
    """Il codice di uscita e' il contratto con systemd (§5.6).

    Zero: arresto normale, e `Restart=always` rilancia. `USCITA_AUTH`: token
    scaduto, e `RestartPreventExitStatus=41` tiene il servizio fermo invece di
    farlo sbattere contro il muro cinque volte al secondo.
    """
    e = Engine()
    await e.run()
    return e._codice_uscita


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
