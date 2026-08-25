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
import contextlib
import os
import signal
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import structlog

from core.gpu_scheduler import GpuScheduler
from core.memory.pruner import ContextPruner
from core.memory.store import MemoryStore
from core.platform import (
    Paths,
    audio as platform_audio,
    gpu as platform_gpu,
    paths as platform_paths,
    sensors as platform_sensors,
)
from core.platform.linux_sandbox import SECCOMP_APPLICATO
from core.layout import NOME_FILE as NOME_LAYOUT, LayoutStore, messaggio_iniziale
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
from core.tools.meteo import TIMEOUT_S as TIMEOUT_METEO_S
from core.tools.meteo import previsione, register_meteo_tools
from core.tools.web import register_web_tools
from core.tools.system import register_system_tools
from core.ws_server import WsServer

log = structlog.get_logger(__name__)

FASE = 9

#: Quanto si aspetta un annuncio prima di rinunciarci. Il TTS di ripiego e'
#: EdgeTTS, che e' di RETE: senza tetto, una rete che accetta la connessione e
#: non risponde piu' terrebbe la voce occupata per sempre, e ogni annuncio
#: successivo si accoderebbe dietro a un morto.
TETTO_ANNUNCIO_S = 30.0


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
            # ADR-003 azione 2. `fatti_fissati` arriva per funzione e non come
            # oggetto: il supervisore non deve sapere che cosa sia un
            # `ContextPruner`, e cosi' i test lo misurano senza una memoria
            # vera. `reinietta` resta None finche' T1 non c'e' — e un replay
            # senza nessuno a cui parlare sarebbe una riga che finge.
            fatti_fissati=lambda: ContextPruner(self._memoria).fatti_fissati(),
        )
        #: Composti solo se le impostazioni lo dicono — vedi `_gradi()`.
        self._t1 = None
        self._voce = None
        self._compito_voce = None
        #: Popolato da `_voce_e_finita()`. `None` = il microfono non e'
        #: caduto, che NON e' la stessa cosa di «e' aperto»: a voce spenta
        #: non c'e' nessun microfono da far cadere.
        self._voce_caduta: str | None = None
        #: ⚠️ Riferimenti FORTI ai compiti di annuncio. `asyncio` tiene solo
        #: riferimenti deboli ai task: uno non referenziato puo' essere
        #: raccolto dal GC **a meta' della frase**, e l'annuncio sparirebbe
        #: senza un errore — di nuovo il guasto muto, nel punto che esiste
        #: apposta per non essere muto.
        self._annunci: set[asyncio.Task] = set()
        self._watcher = None
        #: Quanti giri sui feed sono stati fatti davvero. Resta 0 finche'
        #: qualcuno non aziona il `Watcher`: e' il numero che rende visibile
        #: la differenza fra «costruito» e «funziona».
        self._giri_news = 0
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
        # ADR-006 + ADR-008 + ADR-009: l'unico punto in cui gira codice
        # generato, e gira nel profilo che parte da una radice vuota, dentro un
        # cgroup con un tetto di RAM e di CPU. Registrato QUI perche' §13 ha
        # trovato i quattro tool di memoria scritti, provati e mai registrati:
        # nel processo vero non esistevano.
        #
        # Ritorna False se `code.enabled` e' false, e allora `esegui_codice`
        # NON e' nell'allowlist — come la voce e la vision, questo sottosistema
        # parte spento e si accende scrivendolo (Fase 9).
        self._codice_acceso = register_code_tool(lambda: self._store.current)
        # §26 — il meteo. Senza coordinate in `settings.toml` NON si registra,
        # quindi questa riga non tocca la rete finche' un umano non ha scritto
        # due numeri. Stessa forma di `code.enabled` (ADR-009): un tool che c'e'
        # ma fallisce sempre e' peggio di un tool che non c'e'.
        self._meteo_acceso = register_meteo_tools(self._store.current)
        # `pubblica` chiude la catena tool -> socket -> pannello. Il WS
        # nasce dopo, quindi si passa una lambda e non il metodo.
        register_web_tools(lambda: self._store.current,
                           lambda msg: self._ws.broadcast(msg))
        register_file_tools(lambda: self._store.current, lambda: self._paths)

        # §26.10 punto 1. NON e' un tool: nessuno lo invoca, e' l'ambiente che
        # ricorda se stesso. Vedi l'intestazione di `core/layout.py`.
        self._layout = LayoutStore(self._paths.data_dir() / NOME_LAYOUT)

        self._ws = WsServer(
            self.state_snapshot, self._sensors, self._paths,
            on_confirm=lambda rid, ok: self._broker.rispondi(rid, ok),
            mesh_provider=self.agents_mesh,
            iniziale_provider=self.stato_pannelli,
            # Il renderer manda la propria geometria; il core decide se e come
            # metterla giu'. `da_mettere_giu()` la riporta dentro l'area PRIMA
            # del disco: un renderer che sbaglia non lascia dietro un file che
            # il prossimo avvio dovra' correggere.
            on_layout=lambda msg: self._layout.salva(msg.da_mettere_giu()),
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
                # T1 vivo e microfono chiuso e' uno stato possibile e finora
                # invisibile: `claude` gira, e nessuno ascolta.
                "microfono": self._stato_microfono(),
                "auth": self._supervisore.stato_doctor(),
                "wake_model": str(s.voice.wake.model),
                "wake_frasi": len(s.voice.wake.phrases),
                # ADR-004: i secondi di audio del MESE per provider, e quanti
                # in ripiego. §24.8 chiama Deepgram «la sola voce di costo
                # ricorrente», e il sistema misurava con precisione i token
                # dell'abbonamento — cioe' cio' che non gli costa.
                "consumo": self._governor.consumo_voce_mese(),
            },
            "quota": self._governor.stato(),
            "news": {
                "abilitate": s.news.enabled,
                # ⚠️ `collegato` diceva «l'oggetto esiste», e chi legge lo
                # capisce come «le notizie arrivano». NON arrivano:
                # `Watcher.giro()` non ha un solo chiamante nel core — solo
                # `tests/test_news.py` e `scripts/fixture_fusi.py`. Costruito
                # e mai azionato, come i quattro tool di memoria di §13.
                # Il nome adesso dice cio' che il campo misura davvero.
                "watcher_costruito": self._watcher is not None,
                "giri_fatti": self._giri_news,
            },
            # ADR-009. `acceso` e' se il tool E' NELL'ALLOWLIST, non se
            # l'impostazione dice di si': le due cose divergono appena qualcuno
            # cambia `enabled` senza riavviare, ed e' la divergenza che il
            # doctor deve poter vedere.
            # §26.10 punto 1: dove sta il layout e se c'e' stato un guasto.
            # Un file corrotto messo da parte in silenzio sarebbe la stessa
            # cosa di un file corrotto ignorato.
            "layout": self._layout.stato(),
            # §26: acceso vuol dire NELL'ALLOWLIST, non «l'impostazione dice
            # di si'» — le due cose divergono se mancano le coordinate.
            "meteo": {
                "acceso": self._meteo_acceso,
                "impostazione": s.meteo.enabled,
                "posizione": bool(s.meteo.latitude is not None),
                "luogo": s.meteo.nome,
            },
            "codice": {
                "acceso": self._codice_acceso,
                "impostazione": s.code.enabled,
                "memoria_mb": s.code.memory_mb,
                "cpu_percento": s.code.cpu_percent,
                "lavoro_mb": s.code.tmpfs_mb,
            },
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
        # §26 — il meteo, se c'e' una posizione. E' l'unica sorgente di questo
        # elenco che esce sulla RETE, quindi non va nel `prova()` sincrono: sei
        # secondi di timeout dentro il ciclo degli eventi fermerebbero il core
        # e tutti gli altri pannelli. Va in un thread, e se non risponde il
        # pannello resta al proprio stato vuoto come gli altri.
        if self._meteo_acceso:
            try:
                dati = await asyncio.wait_for(
                    asyncio.to_thread(
                        previsione,
                        self.settings.meteo.latitude, self.settings.meteo.longitude,
                        self.settings.meteo.nome or "posizione impostata",
                        self.settings.meteo.units),
                    timeout=TIMEOUT_METEO_S)
                fuori.append({"topic": "weather.forecast", **dati})
            except Exception as exc:                          # noqa: BLE001
                log.warning("meteo_non_disponibile", errore=str(exc)[:120],
                            conseguenza="il pannello mostra il proprio stato vuoto")

        # ⚠️ `quando` — l'ISTANTE DEL CAMPIONE, e finora lo metteva il renderer.
        #
        # `panels/globe.js` calcola punto subsolare, terminatore e conteggio
        # luce/ombra da `msg.quando ? new Date(msg.quando) : new Date()`. Il
        # campo lo accetta da sempre e nessuno glielo mandava: le zone
        # venivano dal core e l'istante dall'orologio del renderer al momento
        # della connessione. Due orologi per una sola immagine, e il piede
        # stampa `HH:MM:SS UTC` come se appartenesse al dato.
        #
        # Per l'invariante 1 i fatti li possiede il core, e l'istante di un
        # campione appartiene al campione. Il montaggio di galleria lo dice
        # gia': «L'istante e' fissato — non `new Date()`». Era l'app a essere
        # l'eccezione.
        #
        # ⚠️ ISO-8601, NON `time.time()`. `new Date(float_di_secondi)` viene
        # letto come MILLISECONDI: il globo disegnerebbe il terminatore del
        # 1970 — un'immagine sbagliata e STABILE, che e' peggio di una giusta e
        # instabile, perche' passerebbe la fixture invece di essere bocciata.
        prova("geo.timezones", lambda: {
            "topic": "geo.timezones",
            "quando": datetime.now(timezone.utc).isoformat(),
            "zone": [{"nome": z["nome"], "lat": z["lat"], "lon": z["lon"]}
                     for z in leggi_fusi()],
        })

        # §26.6 — le scene DICHIARATE. Il catalogo le elenca nella propria
        # linguetta e la voce le richiama per nome; il renderer ne porta con
        # se' una predefinita, perche' la composizione di partenza non puo'
        # dipendere da un file di configurazione aggiornato. A parita' di nome
        # vince questa: e' quella che un umano ha scritto a mano.
        prova("ui.scene", lambda: {
            "topic": "ui.scene",
            "iniziale": self.settings.ui.scena_iniziale,
            "scene": [
                {"nome": s.nome, "descrizione": s.descrizione,
                 "pannelli": [{"id": p.id, "cella": list(p.cella), "z": p.z}
                              for p in s.pannelli]}
                for s in self.settings.ui.scene
            ],
        })

        # §26.10 punto 1. Il renderer non chiede il proprio layout: glielo
        # manda il core, come gia' fa con lo snapshot e coi quattro topic qui
        # sopra. Se il file non c'e' o era corrotto arriva un layout VUOTO, e
        # il renderer parte dalla disposizione di `moduli.js` come oggi.
        prova("ui.layout", lambda: messaggio_iniziale(self._layout))

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
                su_annuncio=lambda f: self._annuncia_a_voce(f, registra=True),
            )
            await self._t1.start()

            # ⚠️ QUI MANCAVA META' DEL GRADO, e l'intestazione di questo file lo
            # dichiarava da sempre: «voice.enabled -> wake Vosk, STT/TTS, T1
            # persistente, supervisore». Si costruiva solo T1.
            #
            # Accendere `voice.enabled` avviava quindi un processo `claude` e
            # NON apriva il microfono: chi avesse parlato avrebbe parlato nel
            # vuoto, senza un errore da leggere e senza modo di distinguere un
            # microfono muto da un codice che non ascolta.
            from core.providers.registry import costruisci_stt, costruisci_tts
            from core.voice.pipeline import VoicePipeline
            from core.voice.wake import PhraseWake

            wake = PhraseWake(
                {f.say: f.action for f in s.voice.wake.phrases},
                model_path=str(s.voice.wake.model),
            )
            # ⚠️ Il modello si PASSA, non si ricarica: `stt_local.py` dice «il
            # modello e' lo stesso oggetto». Ricaricarlo costa 284 ms misurati
            # e 87 MiB per la stessa cosa.
            stt = costruisci_stt(s, modello_vosk=wake.modello)
            tts = costruisci_tts(s)
            self._voce = VoicePipeline(
                # Il dispositivo si apre QUI e non nel costruttore: a voce
                # spenta non c'e' ragione di toccarlo.
                audio=platform_audio(), wake=wake, stt=stt, tts=tts, t1=self._t1,
                su_azione=self._voce_su_azione,
                # `registra=False`: `annuncia_ripieghi()` scrive gia' la
                # sua riga, e loggare di nuovo darebbe due righe per un
                # annuncio solo. Qui il callback serve a DIRLA, non a
                # scriverla. T1 (venti righe sopra) e' il caso opposto.
                su_annuncio=lambda f: self._annuncia_a_voce(f, registra=False),
                su_turno=self._voce_su_turno,
            )
            self._compito_voce = asyncio.create_task(self._voce.run())
            # ⚠️ UN COMPITO CHE MUORE E' MUTO, ed e' misurato: l'unico
            # messaggio che asyncio produce — «Task exception was never
            # retrieved» — arriva alla DISTRUZIONE dell'oggetto. In una prova
            # che finisce sono 605,9 ms; in un core che resta vivo tenendone
            # il riferimento quel momento NON ARRIVA MAI.
            #
            # Senza questa riga, un `pw-record` assente o un dispositivo
            # occupato chiuderebbero il microfono senza una parola, e chi
            # parla parlerebbe nel vuoto: esattamente il guasto che le venti
            # righe qui sopra hanno appena finito di correggere.
            self._compito_voce.add_done_callback(self._voce_e_finita)
            log.info("grado_acceso", grado="voce", t1=s.llm.t1_model,
                     wake=sorted(wake.frasi), stt=stt.provider.name,
                     tts=tts.provider.name)
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

    def _annuncia_a_voce(self, frase: str, *, registra: bool) -> None:
        """Invariante 12: «il fallback va sempre ANNUNCIATO, mai silenzioso».

        Una riga di log in un terminale che nessuno sta guardando non e' un
        annuncio: e' un annuncio archiviato. Qui la frase viene **detta**, per
        la stessa via con cui §5.6 annuncia la sessione scaduta e ADR-003
        l'amnesia — `VoicePipeline.annuncia()`, che non passa da nessun
        modello. Se dipendesse da Claude, l'annuncio che Claude non risponde
        sarebbe la prima cosa a non funzionare.

        ⚠️ **Non aspetta, e non puo' far cadere niente.** `annuncia_ripieghi()`
        gira all'INIZIO di `run()`, fuori dalla rete che protegge i turni: se
        parlare sollevasse qui — e il TTS di ripiego e' EdgeTTS, che e' di rete
        — `run()` finirebbe e **il microfono non si aprirebbe mai**. Sarebbe la
        beffa esatta: collegare l'annuncio del ripiego chiude l'ascolto.

        `registra` distingue i due chiamanti, e non sono simmetrici:
        `VoicePipeline.annuncia_ripieghi()` scrive gia' la propria riga —
        loggare di nuovo darebbe due righe per un annuncio solo — mentre
        `ClaudeT1` non logga affatto, e senza questa riga il suo ripiego
        sarebbe muto due volte.
        """
        if registra or self._voce is None:
            # `detto` dice se la frase e' stata anche pronunciata: a voce non
            # ancora composta (T1 annuncia durante `start()`) resta il log, ed
            # e' meglio di niente.
            log.warning("ripiego_annunciato", testo=frase,
                        detto=self._voce is not None)
        if self._voce is None:
            return
        compito = asyncio.create_task(self._dillo(frase))
        self._annunci.add(compito)
        compito.add_done_callback(self._annuncio_finito)

    async def _dillo(self, frase: str) -> None:
        """La frase, con un tetto. Vedi `TETTO_ANNUNCIO_S`."""
        await asyncio.wait_for(self._voce.annuncia(frase), TETTO_ANNUNCIO_S)

    def _annuncio_finito(self, compito: asyncio.Task) -> None:
        """Un annuncio che non e' stato detto si dice — nei log, almeno."""
        self._annunci.discard(compito)
        if compito.cancelled():
            return
        exc = compito.exception()
        if exc is not None:
            log.error("annuncio_non_detto", errore=repr(exc),
                      conseguenza="il ripiego resta nei log e non nell'aria")

    def _stato_microfono(self) -> str:
        """Una parola per lo stato del microfono, e nessuna e' ambigua.

        `spento` (voce non accesa), `aperto` (il ciclo gira), `caduto: ...`
        con la causa. Prima non c'era: `t1_vivo` diceva che `claude` gira, e
        di chi ascolta non diceva niente.
        """
        if self._voce_caduta is not None:
            return f"caduto: {self._voce_caduta}"
        if self._compito_voce is None:
            return "spento"
        return "chiuso" if self._compito_voce.done() else "aperto"

    def _voce_e_finita(self, compito: asyncio.Task) -> None:
        """Il microfono si e' chiuso: si dice, sempre, e con la causa.

        Tre esiti, e sono tre cose diverse: annullato e' lo spegnimento
        voluto; un'eccezione e' un guasto; un ritorno pulito vuol dire che il
        flusso del microfono e' finito da solo, che da un dispositivo vivo non
        dovrebbe succedere.
        """
        if compito.cancelled():
            return                          # `_spegni_gradi()`, ed e' voluto
        exc = compito.exception()
        if exc is None:
            self._voce_caduta = "il flusso del microfono e' finito"
            log.warning("voce_finita", perche=self._voce_caduta,
                        conseguenza="nessun altro blocco audio arrivera'")
            return
        self._voce_caduta = repr(exc)
        log.error("voce_caduta", errore=self._voce_caduta,
                  conseguenza="il microfono e' CHIUSO: JARVIS non ascolta piu'",
                  exc_info=exc)

    def _voce_su_azione(self, azione: str, args: dict) -> None:
        """Un'azione decisa dalla voce arriva alla scrivania come le altre."""
        # `create_task` e non `await`: `su_azione` e' un callback SINCRONO —
        # la pipeline lo chiama da dentro il proprio ciclo, e restituirle una
        # coroutine non attesa la lascerebbe cadere in silenzio.
        asyncio.create_task(self._ws.broadcast(
            {"topic": "ui.action", "azione": azione, "args": args}))

    def _voce_su_turno(self, turno) -> None:
        """ADR-004: **il turno si conta**, e senza questa riga il contatore
        costruito ieri non avrebbe mai visto un secondo di audio.

        `tier` distingue chi ha parlato: `stt` per cio' che abbiamo ascoltato,
        `tts` per cio' che abbiamo detto. `fallback` e' vero quando il provider
        non e' il primario — ed e' la misura di quanto Deepgram sia davvero
        affidabile su questa rete (invariante 12).
        """
        for tier, scelta, ms in (
            ("stt", self._voce._stt, turno.latenza_wake_ms),
            ("tts", self._voce._tts, turno.latenza_primo_suono_ms),
        ):
            if ms <= 0:
                continue
            self._governor.registra_voce(
                tier, scelta.provider.name, ms / 1000.0,
                fallback=not scelta.primario)
        log.info("turno_vocale", frase=turno.frase_wake, azione=turno.azione,
                 wake_ms=round(turno.latenza_wake_ms, 1),
                 primo_suono_ms=round(turno.latenza_primo_suono_ms, 1))

    async def _spegni_gradi(self) -> None:
        if self._voce is not None:
            self._voce.stop()
            if self._compito_voce is not None:
                self._compito_voce.cancel()
                try:
                    await self._compito_voce
                except asyncio.CancelledError:
                    pass
                except Exception:
                    # ⚠️ Un compito GIA' MORTO ripropone la sua eccezione a chi
                    # lo attende. Qui vorrebbe dire che l'arresto del core
                    # inciampa su un guasto della voce **gia' registrato** da
                    # `_voce_e_finita()` con la sua causa: risalirebbe dal
                    # `finally` di `run()`, saltando la chiusura del layout e
                    # l'ultima riga di log. Trovato da un test, non a mano.
                    pass
            log.info("grado_spento", grado="voce", perche="arresto")
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
            # Cio' che il freno del layout aveva trattenuto va giu' adesso.
            # Senza, l'ultima posizione di un trascinamento veloce resterebbe
            # in memoria fino al messaggio successivo — che, se si sta
            # spegnendo, non arriva.
            if self._layout.chiudi():
                log.info("layout_messo_giu_alla_chiusura")
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
