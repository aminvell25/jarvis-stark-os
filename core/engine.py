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
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog

from core.gestures.mapping import FRAME_ISTERESI
from core.diario import Diario
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
#: Il MODULO, non la funzione rinominata.
#:
#: ⚠️ **La ragione originale non vale piu'.** Qui c'era scritto che un
#: `from core.log import configura as configura_log` sarebbe stato invisibile a
#: `scripts/orfani.py`, che non risolveva gli alias — vero quel giorno, e la
#: revisione del 27 agosto ha fatto notare che un aggiramento scritto nel codice
#: applicativo per un limite dello strumento di misura e' il limite che va
#: tolto. Lo scanner adesso risolve gli alias.
#:
#: La forma resta perche' `core_log.configura()` dice da dove viene la
#: configurazione, e un nome rinominato lo nasconderebbe.
from core import log as core_log
from core.settings import Settings, SettingsStore
from core.agents_mesh import snapshot as mesh_snapshot
from core.llm import grammar
from core.llm.claude_t2 import ClaudeT2
from core.llm.governor import Governor
from core.llm.supervisor import USCITA_AUTH, Supervisore

from core.protocolli import Ronda, carica
from core.tools import registry
from core.tools.confirm import ConfirmBroker
from core.tools.audio import register_audio_tools
from core.tools.code import register_code_tool
from core.tools.files import register_file_tools
from core.tools.geo import leggi_fusi, register_geo_tools
from core.tools.impostazioni import (
    chiavi_bloccate,
    chiavi_modificabili,
    register_settings_tool,
)
from core.tools.introspect import leggi_albero, leggi_note, register_introspect_tools
from core.tools.memory import register_memory_tools
from core.tools.meteo import TIMEOUT_S as TIMEOUT_METEO_S
from core.tools.meteo import previsione, register_meteo_tools
from core.tools.web import register_web_tools
from core.tools.system import register_system_tools
from core.ws_server import WsServer

log = structlog.get_logger(__name__)

#: La radice del progetto. Serve a T2, che gira da qui **di proposito**: e' la
#: directory in cui vede `CLAUDE.md` e i subagent (§5.3). T1 fa il contrario.
RADICE = Path(__file__).resolve().parent.parent

#: Quanto si aspetta il ponte per una cattura. §12 non lo dichiara; viene dal
#: budget di §10.4: un fotogramma e' 16,7 ms, e `capturePage()` su una finestra
#: 4K ne costa qualche decina. Cinque secondi sono due ordini di grandezza piu'
#: del previsto — cioe' «il ponte non c'e'», non «il ponte e' lento».
TIMEOUT_CATTURA_S = 5.0

#: Dopo quanti secondi senza un blocco audio il microfono e' sospetto.
#:
#: I blocchi arrivano ogni **20 ms**: cinque secondi sono duecentocinquanta
#: blocchi mancati, cioe' «rotto», non «la macchina e' occupata». E il conto
#: NON scorre durante un turno — la' il ciclo non legge per costruzione, e un
#: turno puo' durare fino al timeout di T1: vedi `VoicePipeline.muto_da`.
SILENZIO_SOSPETTO_S = 5.0

#: Quanta VRAM serve alla scena, e da dove viene il numero.
#:
#: §9: «Scena three.js + PixiJS 60fps | ~1-2 GB (stima prudenziale) | **il
#: consumatore principale**». Si prende il **limite inferiore**: sotto, la
#: scena non ci sta di sicuro, e l'avviso non e' mai un falso allarme.
VRAM_SCENA = 1024 * 2**20

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
        # §13: la memoria di Fase 4 esisteva, era provata, e NON era registrata
        # nella radice di composizione. Sta **prima** del Governor perche' e'
        # lei che possiede `conso/`, e il Governor senza quella directory non
        # scrive niente.
        # ⚠️ **La workspace si CREA**, come ogni altra radice che questo core
        # possiede: `MemoryStore`, `Diario` e `Ronda` fanno lo stesso.
        #
        # `fs.workspace` non e' una cartella qualunque: §3.4 la dichiara
        # l'**unico percorso scrivibile della sandbox** (`ro-bind /` piu'
        # `rw-bind ~/JARVIS/`). Una cosa cosi' non puo' dipendere da una
        # cartella fatta a mano.
        #
        # Misurato: non esisteva, e a **ogni** collegamento della scrivania il
        # core scriveva `workspace_non_elencabile` e il pannello file restava
        # senza la workspace. Sette volte nel journal di oggi, a livello `info`
        # — cioe' un difetto che si vede solo se qualcuno va a cercarlo.
        #
        # Non solleva: una home in sola lettura e' un guaio dell'utente, non un
        # motivo per non accendere JARVIS. Chi ci scrive dentro trova comunque
        # l'errore vero al momento di scrivere.
        try:
            self._store.current.fs.workspace.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("workspace_non_creata",
                        percorso=str(self._store.current.fs.workspace),
                        errore=repr(exc))

        self._memoria = MemoryStore(self._paths.data_dir() / "memory_data")
        # Il diario: due flussi, su disco e sul socket. Non e' la memoria —
        # `sessions/` alimenta il consolidamento di §5.5 e vive quanto lei;
        # questo e' uno strumento di osservazione e si cancella senza perdere
        # nulla di cio' che JARVIS sa. Vedi `core/diario.py`.
        self._diario = Diario(self._paths.data_dir() / "memory_data" / "diario",
                              pubblica=lambda m: self._ws.broadcast(m))

        # ⚠️ **Tre argomenti che mancavano tutti e tre, e la riga era una sola.**
        #
        # `Governor()` nudo significava:
        #
        # 1. **`dir_conso=None`** -> `_registra()` ritorna alla prima riga, e
        #    `conso/` non veniva scritto MAI. Misurato prima di correggere:
        #    zero righe, e `voce.consumo` nello snapshot era
        #    `{"secondi": {}, "sessioni": 0}` da sempre. La directory esisteva
        #    gia' — la crea `MemoryStore` — ed era calcolata una schermata piu'
        #    giu' nello stesso costruttore. ADR-004 esiste per contare prima di
        #    spendere, e non contava.
        #
        # 2. **`su_advisory=None`** -> `t2_sospeso` e `t2_ripreso` non
        #    raggiungevano `agent.advisory`. `docs/acceptance/I-TRE-ORFANI-VERI.md`
        #    dichiarava che la ripresa «si annuncia»: era **falso in
        #    produzione**. Avevo collegato l'emettitore a un'uscita che non
        #    esisteva — la stessa famiglia di difetto dentro la correzione che
        #    diceva di chiuderla.
        #
        # 3. **i due tetti dalle impostazioni** -> `max_concurrent_t2` e
        #    `max_t2_spawns_per_hour` di §8 erano validati da `settings.py` e
        #    non arrivavano qui. Coincidevano con le costanti del modulo, ed e'
        #    esattamente per questo che la disconnessione era invisibile:
        #    alzare il numero nel TOML non cambiava niente.
        _llm = self._store.current.llm
        self._governor = Governor(
            max_concurrent=_llm.max_concurrent_t2,
            max_per_window=_llm.max_t2_spawns_per_hour,
            su_advisory=self._advisory_sincrono,
            dir_conso=self._memoria.conso,
        )
        self._supervisore = Supervisore(
            parla=self._parla_locale,
            pubblica=lambda msg: self._ws.broadcast(msg),
            esci=self._esci_per_auth,
            # ⚠️ Qui c'erano `fatti_fissati` e `reinietta`, per ADR-003 azione 2.
            # Il supervisore non reinietta piu' niente: la reiniezione la fa chi
            # possiede la sessione, cioe' `ClaudeT1.riavvia_dopo_guasto`, che
            # riceve `fatti_fissati` qualche riga piu' sotto. Qui era per meta'
            # un no-op dichiarato — `reinietta` restava None — e per meta' un
            # secondo produttore in attesa di essere cablato.
        )

        # §7.6: «briefing», «fammi il punto», «cosa richiede la mia attenzione».
        # Tre frasi nella grammatica dalla Fase 3, senza esecutore fino a oggi.
        #
        # ⚠️ **Dopo il supervisore, e l'ordine non e' estetico**: gli passa
        # `su_evento`, e costruirlo prima dava `AttributeError` al primo avvio.
        # L'ha trovato `test_costruire_due_volte_non_esplode`, che e' li' per
        # questo.
        self._t2_meta = ClaudeT2(self._governor, RADICE,
                                 su_evento=self._supervisore.su_evento)
        #: ⚠️ **Il consolidamento notturno ha un T2 SUO, con zero tool.**
        #:
        #: §5.5 lo prescrive alla lettera — *«un processo T2 dedicato con
        #: `--allowedTools ""`: legge e scrive solo tramite i tool memoria
        #: dell'allowlist, mai direttamente»* — e riceveva invece `_t2_meta`,
        #: cioe' `Read,Edit,Bash(git *),Glob,Grep`.
        #:
        #: **Misurato** il 27 agosto con quella stessa riga di comando, in una
        #: copia scratch: `Write` e `Bash` generico sono negati, ma `Edit` e
        #: `Bash(git add && git commit)` **riescono, senza nessuna conferma**.
        #: Quindi il consolidamento poteva modificare un file qualunque del
        #: repository e committarlo, alle 04:00, con nessuno davanti — e a
        #: tenerlo dentro `topics/` era **il testo del prompt**, non un
        #: meccanismo.
        #:
        #: Non gli servono: `esegui()` gli passa gli scambi NEL COMPITO e
        #: scrive con `MemoryStore.scrivi_topic`. Con zero tool non c'e' niente
        #: su cui iterare, quindi anche `max_turns=1` non e' un numero scelto.
        self._t2_conso = ClaudeT2(self._governor, RADICE, tool="", max_turns=1,
                                  su_evento=self._supervisore.su_evento)
        #: I protocolli dichiarati — il primitivo di Iron Man 3: JARVIS non
        #: improvvisa mai un'azione, esegue un comando scritto prima e
        #: richiamato per nome. La validazione e' fail-closed e RUMOROSA: una
        #: dichiarazione storta non deve poter restare inerte in silenzio, o il
        #: Signore crederebbe che JARVIS sorvegli qualcosa che nessuno guarda.
        self._ronda = Ronda(self._memoria.radice / "protocolli")
        self._protocolli = carica(self._store.current.protocolli)
        if self._protocolli:
            log.info("protocolli_caricati",
                     quanti=len(self._protocolli),
                     nomi=[p.nome for p in self._protocolli])
        #: Composti solo se le impostazioni lo dicono — vedi `_gradi()`.
        self._t1 = None
        self._voce = None
        #: Il riconoscitore di richiamo vivo. Serve allo snapshot per
        #: dire con quale modello si stia ascoltando DAVVERO — vedi
        #: `PhraseWake.modello_caricato_da`.
        self._wake = None
        self._compito_voce = None
        #: Popolato da `_voce_e_finita()`. `None` = il microfono non e'
        #: caduto, che NON e' la stessa cosa di «e' aperto»: a voce spenta
        #: non c'e' nessun microfono da far cadere.
        self._voce_caduta: str | None = None
        #: Come smettere di ascoltare i cambi di impostazioni. `None` a voce
        #: spenta: non c'e' nessun wake a cui riportarli.
        self._disiscrivi_frasi = None
        #: ⚠️ Riferimenti FORTI ai compiti di sfondo. `asyncio` tiene solo
        #: riferimenti deboli ai task: uno non referenziato puo' essere
        #: raccolto dal GC **a meta' del lavoro**, e cio' che stava facendo
        #: sparirebbe senza un errore — il guasto muto, nei punti che esistono
        #: apposta per non essere muti: un annuncio, un'azione vocale, il
        #: salvataggio di un'impostazione.
        self._compiti: set[asyncio.Task] = set()
        self._watcher = None
        #: ADR-007. `None` finche' `_gradi()` non ha girato.
        self._mcp = None
        #: Quanti giri sui feed sono stati fatti davvero. Resta 0 finche'
        #: qualcuno non aziona il `Watcher`: e' il numero che rende visibile
        #: la differenza fra «costruito» e «funziona».
        #: §15. `None` finche' `news.enabled` non lo accende.
        self._news = None
        self._compito_news = None
        #: Le parole che hanno fatto passare l'ultima card. Sono cio' che
        #: «non parlarmene piu'» chiude quando non nomina un argomento.
        self._ultima_news_colpita: list[str] = []
        #: ⚠️ UNO SOLO, e condiviso. I tool del volume e la pipeline vocale
        #: devono agire sullo stesso oggetto: due istanze vorrebbero dire un
        #: guadagno impostato su una che non riproduce niente — due meta'
        #: scollegate, il difetto ricorrente di questo progetto.
        #: Costruirlo non avvia nulla: `LinuxAudioIO.__init__` e' inerte.
        self._audio = None
        #: ⚠️ **Qui c'erano due righe che azzeravano i due T2 appena
        #: costruiti**, centoquaranta righe piu' su, nella stessa funzione.
        #:
        #: Il commento diceva «costruito nella radice di composizione, non
        #: qui»: era vero prima che la composizione venisse spostata dentro
        #: `__init__`, e nessuno ha tolto l'azzeramento.
        #:
        #: Conseguenza: `self._t2_meta` era **sempre `None`**, e
        #: `_meta_comando` si arrendeva alla prima riga con «T2 non composto».
        #: `brief_me` e `needs_attention` non hanno mai potuto spawnare nulla
        #: **dal commit che li ha collegati** (`92c0ec4`, «nessun intento senza
        #: strada»): la strada c'era e finiva su un null.
        #:
        #: Trovato perche' il recupero del consolidamento e' cascato su
        #: `_t2_conso`, che era finito nella stessa trappola il giorno stesso.
        self._compito_conso = None
        #: Le catture in volo, per id. §12: la richiesta e la risposta viaggiano
        #: su un socket asincrono, e senza correlazione due domande vicine si
        #: scambierebbero le risposte.
        self._catture: dict[str, asyncio.Future] = {}
        #: L'ultimo verdetto sulla VRAM. Serve a emettere l'advisory **sul
        #: cambio** e non a 2,5 Hz. Parte da `False` — «finora non e' scarsa» —
        #: cosi' il primo snapshot con memoria insufficiente lo dice.
        self._vram_scarsa = False
        #: Lo stesso, per il microfono: si annuncia sul CAMBIO, non a 2,5 Hz.
        self._microfono_sospetto = False
        self._compito_gesture = None
        self._argus = None
        self._codice_uscita = 0

        # La radice di composizione POSSIEDE l'allowlist: e' lei a decidere
        # che cosa esiste. Svuotare prima di registrare rende l'avvio
        # idempotente senza nascondere i doppioni dentro una fase.
        registry.clear()
        register_system_tools(self._sensors)
        # §7.6: `volume 40` e `silenzio` erano nella grammatica dalla Fase 3
        # e non avevano un esecutore. Vedi `core/tools/audio.py`.
        register_audio_tools(lambda: self.audio)
        register_geo_tools()
        # I sorgenti e i documenti del progetto, per i moduli «Core sorgente» e
        # «Piani d'archivio» di §13. Nessun parametro path: vedi l'intestazione
        # di `core/tools/introspect.py`.
        register_introspect_tools()
        # §13: la memoria di Fase 4 esisteva, era provata, e NON era registrata
        # nella radice di composizione — quindi i suoi quattro tool non
        # esistevano nel processo vero. Una riga mancante, trovata cercando chi
        # potesse produrre l'archivio. Dichiarata in `SEZIONE-13.md`.
        # ⚠️ `MemoryStore` si costruisce PIU' SU, prima del Governor: e' lui il
        # proprietario di `conso/`, e il Governor deve riceverlo. Qui resta
        # solo la registrazione dei tool.
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
        # ⚠️ **Una radice consentita non puo' contenere lo stato di JARVIS.**
        #
        # Il 27 agosto la workspace e' passata da `~/JARVIS` a
        # `~/.local/share/jarvis-os/workspace`, cioe' **dentro** la cartella in
        # cui vivono `memory_data/`, `layout.json` e i modelli. Oggi e' una
        # sorella e non c'e' guaio; ma basta scrivere
        # `workspace = "~/.local/share/jarvis-os"` — una riga plausibile, e
        # persino comoda — perche' `trash_path` possa cestinare la memoria di
        # JARVIS con una conferma sola, e `organize_folder` riordinargli i
        # ricordi per tipo di file.
        #
        # La radice si **toglie**, e si dice. Togliere e' fail-closed: JARVIS
        # perde una cartella su cui lavorare, non la propria memoria. Rifiutare
        # l'avvio sarebbe peggio — un core che non parte per una riga di
        # configurazione e' inaccettabile, e lo dice gia' `LayoutStore`.
        register_file_tools(self._radici_sicure, lambda: self._paths)
        # §26.7 — l'unico posto da cui `settings.toml` viene RISCRITTO. Un tool
        # solo, `side_effect=True`, quindi con la conferma di §6.2: sta
        # scrivendo la configurazione di un sistema che apre un microfono e
        # puo' eseguire codice.
        register_settings_tool(lambda: self._store.current, self._paths.config_dir)

        # §26.10 punto 1. NON e' un tool: nessuno lo invoca, e' l'ambiente che
        # ricorda se stesso. Vedi l'intestazione di `core/layout.py`.
        self._layout = LayoutStore(self._paths.data_dir() / NOME_LAYOUT)

        # ⚠️ **Si legge il layout ADESSO, e non alla prima connessione.**
        #
        # `carica()` aveva un solo chiamante — `messaggio_iniziale`, che gira
        # quando la scrivania si collega — mentre `state.snapshot` parte PRIMA
        # (`core/ws_server.py:275`, e la riga sopra dichiara perche': «ogni
        # client riceve lo stato completo prima di qualunque delta»). Ma
        # `corrotto_in` si valorizza dentro `carica()`. Quindi nella sessione in
        # cui il guasto accade lo snapshot non poteva saperlo, e la striscia
        # LAYOUT del dock — `corrotto_in ? "corrotto" : esiste ? "ok"` — diceva
        # **`ok` su un file appena buttato via**. Misurato:
        #
        #     file corrotto, prima di carica():  esiste=True,  corrotto_in=None
        #     file corrotto, dopo  carica():     esiste=False, corrotto_in=<path>
        #
        # Leggerlo qui non cambia il significato di `corrotto_in` — resta «e'
        # successo in questa sessione» — e non tocca l'ordine dei messaggi, che
        # `core/doctor.py:56` legge prendendo il PRIMO frame per lo snapshot:
        # spostarlo avrebbe rotto `jarvis doctor` per riparare una striscia.
        #
        # ⚠️ Resta scoperta una finestra stretta: un file che si corrompe FRA
        # questo istante e la connessione della scrivania. Lo rileva
        # `messaggio_iniziale`, ma lo snapshot di quel client e' gia' partito.
        # Dichiarata, non chiusa: chiuderla vuol dire rileggere il disco a ogni
        # snapshot, cioe' a 2,5 Hz.
        self._layout.carica()

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
            # §26.7. Il renderer CHIEDE, e chi decide e' `imposta_valore`, che
            # ha `side_effect=True` e apre la conferma di §6.2: la pagina non
            # ha modo di scrivere, solo di far nascere una domanda.
            on_impostazione=self._imposta_da_ui,
            # Il microfono si apre solo dentro l'ambiente di JARVIS: il core
            # gira sotto systemd ventiquattro ore, l'app no.
            su_scrivania=self._scrivanie_cambiate,
            # §12. Il ponte cattura la finestra e rimanda il PNG: senza questa
            # riga la risposta si scartava come qualunque messaggio non
            # atteso, e ARGUS non aveva un solo chiamante nel core. Le due
            # meta' — `ArgusCaptureResponse` nel contratto e `catturaEInvia`
            # in `app/main.js` — erano scritte da Fase 6 e non si parlavano.
            on_capture=self._cattura_arrivata,
        )

        # Il broker pubblica sul socket, e il registry gli chiede il permesso
        # prima di ogni tool distruttivo. Senza questo collegamento i tool con
        # side_effect NON funzionano (fail-closed): e' il verso giusto.
        self._broker = ConfirmBroker(self._ws.broadcast)
        registry.set_confirm_hook(self._broker.richiedi)
        # §6.2, la seconda meta': com'e' andata. Il broker possiede la DOMANDA
        # — l'ha pubblicata lui, con quell'id — e la radice possiede la
        # RISPOSTA, perche' e' l'unica che abbia insieme il socket e il diario.
        registry.set_result_hook(self._esito_confermato)
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
        self._controlla_vram()
        self._controlla_microfono()
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
            # §26.7 — quel che serve alla PAGINA impostazioni per esistere.
            # Non e' un doppione di `settings` qui sotto: quello e' un estratto
            # scelto a mano per il doctor, questo e' l'elenco DERIVATO dallo
            # schema, cioe' l'unica lista che non diverge dal modello quando
            # qualcuno aggiunge una chiave.
            "impostazioni": {
                "modificabili": chiavi_modificabili(s),
                # Le cinque che si guardano e non si toccano, col loro valore.
                "bloccate": chiavi_bloccate(s),
                "file": str(self._paths.config_dir() / "settings.toml"),
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
                # ⚠️ `gap_px` MANCAVA, e il renderer lo applica dalla stessa
                # riga di `grid_px` (§26.9 criterio 7): senza, `applicaScala`
                # lo avrebbe saltato per sempre — una meta' collegata e
                # l'altra no, che e' il difetto che quella riga corregge.
                # Trovato da `test_il_valore_arriva_NELLO_SNAPSHOT`.
                "ui": {"target_fps": s.ui.target_fps, "grid_px": s.ui.grid_px,
                       "gap_px": s.ui.gap_px},
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
                # ⚠️ **Il modello VIVO, non quello chiesto.** Qui c'era
                # `str(s.voice.wake.model)`: cambiando il modello in
                # `settings.toml` lo snapshot rispondeva col percorso nuovo
                # all'istante, mentre il riconoscitore continuava con quello di
                # prima — per sempre, perche' `set_frasi()` non ricarica il
                # modello e nessun'altra strada lo fa. E `jarvis doctor`
                # validava l'esistenza di un file che il riconoscitore vivo non
                # aveva mai aperto, e rispondeva `ok`.
                "wake_model": self._modello_wake_vivo(),
                "wake_model_chiesto": str(s.voice.wake.model),
                # Stessa regola: quante frasi ha il riconoscitore, non quante ne
                # chiede il file. Le due divergono se `set_frasi()` e' caduta —
                # `frasi_non_applicate`, «restano quelle di prima».
                "wake_frasi": (len(self._wake.frasi) if self._wake is not None
                               else len(s.voice.wake.phrases)),
                # ADR-004: i secondi di audio del MESE per provider, e quanti
                # in ripiego. §24.8 chiama Deepgram «la sola voce di costo
                # ricorrente», e il sistema misurava con precisione i token
                # dell'abbonamento — cioe' cio' che non gli costa.
                "consumo": self._governor.consumo_voce_mese(),
            },
            "quota": self._governor.stato(),
            # ADR-007: quali server sono montati, quali tool sono stati
            # NOMINATI, e che cosa non e' riuscito. Un montaggio fallito che
            # non lascia traccia e' un tool che non c'e' senza che nessuno
            # sappia perche'.
            # §15: la cadenza dedotta, i giri fatti davvero e gli argomenti
            # vivi. `giri_fatti` restava a zero perche' nessuno azionava il
            # `Watcher`; adesso e' un numero che cresce.
            "news_motore": (self._news.stato() if self._news is not None
                            else {"periodo_s": None, "giri_fatti": 0,
                                  "argomenti": [], "ultimo_giro": None}),
            "mcp": (self._mcp.stato() if self._mcp is not None
                    else {"server": [], "promossi": [], "guasti": []}),
            "news": {
                "abilitate": s.news.enabled,
                # ⚠️ `collegato` diceva «l'oggetto esiste», e chi legge lo
                # capisce come «le notizie arrivano». NON arrivano:
                # `Watcher.giro()` non ha un solo chiamante nel core — solo
                # `tests/test_news.py` e `scripts/fixture_fusi.py`. Costruito
                # e mai azionato, come i quattro tool di memoria di §13.
                # Il nome adesso dice cio' che il campo misura davvero.
                "watcher_costruito": self._watcher is not None,
                "giri_fatti": self._news.giri if self._news is not None else 0,
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

    async def esegui_t0(self, intent: grammar.Intent) -> dict[str, Any]:  # noqa: D401
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

        # ⚠️ **Ogni esito, non solo quelli riusciti.** Il registro serve a
        # spiegare perche' qualcosa NON e' successo: un intento rifiutato e'
        # la riga piu' utile che ci sia, ed e' proprio quella che il journal
        # scriveva come `warning` in mezzo a tutto il resto.
        esito = await self._esegui_t0(intent)
        self._compito_di_sfondo(self._diario.annota(
            "azione", intento=intent.tool, args=intent.args or None,
            ok=bool(esito.get("ok")), da="voce",
            strada=("ui" if intent.tool in grammar.INTENTI_UI else
                    "core" if intent.tool in grammar.INTENTI_CORE else
                    "tool" if intent.tool in registry.names() else "nessuna"),
            errore=esito.get("error"),
        ))
        return esito

    async def _esegui_t0(self, intent: grammar.Intent) -> dict[str, Any]:
        """La decisione vera. `esegui_t0` la avvolge per annotarne l'esito."""

        if intent.tool in grammar.INTENTI_UI:
            # Gli ARGOMENTI viaggiano con l'intento. `open_panel` senza
            # `{"panel": "globo"}` non e' un comando, e' una categoria — ed e'
            # esattamente cio' che `VoicePipeline._su_azione` lasciava cadere.
            await self._ws.broadcast({
                "topic": "ui.intent", "intento": intent.tool, "args": intent.args,
            })
            log.info("t0_ui", intento=intent.tool, args=intent.args)
            return {"ok": True, "tier": "t0", "intento": intent.tool}

        if intent.tool in grammar.INTENTI_CORE:
            # La terza allowlist: intenti che toccano stato del core e non
            # passano ne' dalla scrivania ne' dal registro dei tool.
            return await self._intento_del_core(intent)

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

    async def _esito_confermato(self, piano, r) -> None:
        """Com'e' andata l'operazione che il Signore ha approvato — §6.2.

        ⚠️ **`fs.result` era promesso in due punti e non lo pubblicava nessuno.**
        Il diagramma di §6.2 e quello in cima a `core/tools/confirm.py` dicono
        `conferma -> esegue -> fs.result`, e in tutto il repository quella
        stringa compariva **solo in quelle due righe di prosa**. Il Signore
        approvava di spostare duecento file, la finestra si chiudeva al clic, e
        cio' che accadeva dopo non tornava indietro: se il ventesimo file non si
        muoveva, per la scrivania l'operazione era andata bene.

        Due destinazioni, e sono due cose diverse:

          `fs.result`    la RISPOSTA alla domanda, con lo stesso `id` con cui e'
                         stata posta. Chiude la conversazione di §6.2.
          il diario      il RECORD, che sopravvive alla sessione ed e' cio' che
                         il Signore rilegge. Forma `azione`, come ogni altro
                         atto: nessuna forma nuova da rendere.

        Non solleva verso il registro: l'operazione E' GIA' AVVENUTA, e un
        referto che cade non deve poter trasformarla in un errore. Chi chiama
        cattura, ma qui si e' espliciti lo stesso.
        """
        try:
            await self._ws.broadcast({
                "topic": "fs.result",
                "id": piano.id,
                "ok": bool(r.ok),
                "error": r.error,
            })
        except Exception as exc:
            log.error("fs_result_non_pubblicato", id=piano.id, errore=repr(exc))
        try:
            await self._diario.annota(
                "azione", intento=piano.tool, args=None, ok=bool(r.ok),
                da="conferma", strada="tool",
                operazioni=len(piano.operazioni), errore=r.error)
        except Exception as exc:
            log.error("esito_non_annotato", id=piano.id, errore=repr(exc))

    def _esci_per_auth(self, codice: int) -> None:
        """§5.6: si ferma, e con un codice che la unit systemd riconosce.

        Non si chiama `sys.exit()` da un callback dentro il loop: si registra
        il codice e si chiede l'arresto pulito, cosi' il socket viene chiuso e
        non resta un file orfano in $XDG_RUNTIME_DIR.
        """
        self._codice_uscita = codice
        log.critical("uscita_per_auth", codice=codice)
        self._stop.set()

    @property
    def audio(self):
        """L'`AudioIO`, costruito alla prima richiesta e **uno solo**.

        Pigro e non nel costruttore: i tool del volume si registrano prima che
        la radice di composizione decida se la voce si accende, e costruirlo
        li' impedirebbe di sostituire la fabbrica — che e' come si prova un
        microfono che muore.
        """
        if self._audio is None:
            self._audio = platform_audio()
        return self._audio

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
            # ⚠️ **Due manopole che non giravano.** `t1_cwd` e `t1_persona`
            # stanno in `settings.toml`, sono validate da `core/settings.py`, e
            # §5.2 le cita — e qui c'erano due percorsi scritti a mano.
            # Cambiare il valore nel file non produceva nessun effetto: la
            # stessa specie del `ui.grid_px` di §26.7 e dei due tetti del
            # Governor, cioe' un'impostazione che esiste solo nella
            # documentazione.
            #
            # Il percorso di prima resta come PREDEFINITO: chi non configura
            # niente non deve accorgersi di nulla.
            cwd = s.llm.t1_cwd or (self._paths.data_dir() / "voice-cwd")
            cwd.mkdir(parents=True, exist_ok=True)
            self._t1 = ClaudeT1(
                modello=s.llm.t1_model,
                cwd=cwd,
                persona=s.llm.t1_persona or (self._paths.config_dir()
                                             / "voice-persona.md"),
                su_annuncio=lambda f: self._annuncia_a_voce(f, registra=True),
                # §5.6: il proprietario della degradazione e' UNO.
                su_evento=self._supervisore.su_evento,
                # ⚠️ Il canale del REFERTO, e non e' `su_evento`. T1 possiede
                # la degradazione non-auth — processo, `returncode`, `stderr`,
                # riavvio — e il supervisore ne tiene il referto: bus,
                # `stato_doctor()` e il contatore di vita. Senza questa riga,
                # dopo tre riavvii veri `jarvis doctor` diceva ancora
                # `nominal, riavvii: 0`.
                riferisci=self._supervisore.riferisci,
                # ⚠️ **ADR-003 azione 2, e non era cablata.** `riavvia_dopo_guasto`
                # reinietta `self._fatti_fissati()` e poi ANNUNCIA «ho conservato
                # le Sue preferenze»: senza questa riga il default di
                # `ClaudeT1.__init__` e' `lambda: []`, quindi non si conservava
                # niente e lo si diceva lo stesso. Misurato in esercizio.
                #
                # Stessa espressione che riceve il `Supervisore` (vedi sopra):
                # e' la sorgente, non un secondo produttore — e in esercizio il
                # solo a reiniettare davvero e' T1, perche' `Supervisore.reinietta`
                # resta None per la ragione dichiarata li'.
                fatti_fissati=lambda: ContextPruner(self._memoria).fatti_fissati(),
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
            # ⚠️ Lo stato INIZIALE, non un valore comodo. Se il core parte
            # prima dell'app — che e' il caso normale sotto systemd — il
            # microfono deve nascere chiuso, non aprirsi per un istante.
            self._wake = wake
            self._voce = VoicePipeline(
                ascolto_consentito=self._ws.scrivanie > 0,
                # Il dispositivo si apre QUI e non nel costruttore: a voce
                # spenta non c'e' ragione di toccarlo.
                audio=self.audio, wake=wake, stt=stt, tts=tts, t1=self._t1,
                # §16, riga Deepgram: «chiave invalida, 429, rete → ricade sul
                # locale e lo annuncia». Era imposta solo all'avvio; un
                # provider che cade MENTRE parla non era previsto.
                ricostruisci_tts=lambda: costruisci_tts(self._store.current,
                                                        errore_primario=True),
                su_azione=self._voce_su_azione,
                # `registra=False`: `annuncia_ripieghi()` scrive gia' la
                # sua riga, e loggare di nuovo darebbe due righe per un
                # annuncio solo. Qui il callback serve a DIRLA, non a
                # scriverla. T1 (venti righe sopra) e' il caso opposto.
                su_annuncio=lambda f: self._annuncia_a_voce(f, registra=False),
                su_turno=self._voce_su_turno,
            )
            # ⚠️ **Le frasi cambiano SCRIVENDOLE, senza riavviare il core.**
            #
            # `PhraseWake.set_frasi()` esisteva dalla Fase 3 e non aveva un
            # solo chiamante: la ricarica a caldo di `settings.toml` funziona,
            # e al wake non arrivava. Cambiare una frase voleva dire riavviare
            # — la sesta volta, in due giorni, di due pezzi scritti e mai
            # congiunti.
            #
            # ⚠️ E si RIMBALZA SUL LOOP. `SettingsStore.reload()` gira sul
            # thread di watchdog, e `call_soon_threadsafe` fa eseguire il
            # riporto fra due giri del loop, mai dentro uno.
            #
            # ⚠️ **La ragione qui scritta NON e' piu' quella che regge.** Fino
            # al 27 agosto diceva: «`set_frasi()` ricostruisce il
            # `KaldiRecognizer` che `feed()` sta usando», e il rimbalzo era
            # l'unica cosa a impedire quella corsa. Oggi `set_frasi()` non
            # ricostruisce piu' niente: **deposita** il cambio, e lo applica
            # `feed()` fra un blocco audio e l'altro. La corsa la chiude
            # `core/voice/wake.py`, non questa riga.
            #
            # Il rimbalzo RESTA. `_ricarica_frasi` legge `wake._frasi` per
            # decidere se c'e' qualcosa da fare e poi scrive nei log: due
            # letture del wake dal thread sbagliato, che oggi non fanno danno
            # ma non hanno nessuna ragione di stare fuori dal loop del core.
            # Lo pretende dal sorgente
            # `tests/test_grado_voce.py::test_si_RIMBALZA_sul_loop_e_non_si_chiama_dal_thread`.
            ciclo = asyncio.get_running_loop()
            self._disiscrivi_frasi = self._store.subscribe(
                lambda nuove: ciclo.call_soon_threadsafe(self._ricarica_frasi,
                                                         wake, nuove))
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

            # §15: le news seguono la CONVERSAZIONE, e la card che passa si
            # dice anche a voce — «card news + menzione vocale breve».
            # `pubblica` non e' piu' il broadcast nudo: e' il broadcast piu'
            # la menzione, e la menzione la fa solo chi ha una voce.
            # §15 elenca TRE sorgenti e ne era composta una. Gli altri due
            # collector erano scritti, provati e senza chiamanti — l'ottava
            # giunzione mancante. Comporli non costa nulla anche senza chiavi:
            # `disponibile()` risponde di no, il `Watcher` lo mette fra gli
            # errori del giro e lo ANNUNCIA una volta su `agent.advisory`,
            # invece di fingere che la sorgente non esista.
            from core.news.collectors.guardian import GuardianCollector
            from core.news.collectors.youtube import YouTubeCollector

            self._watcher = Watcher(
                # La chiave arriva **per funzione**: `SettingsStore` ricarica a
                # caldo, e un collector che l'avesse letta una volta sola
                # resterebbe convinto di non averla per sempre.
                [RssCollector(),
                 GuardianCollector(
                     lambda: self._store.current.secrets.guardian_api_key
                     .get_secret_value()),
                 YouTubeCollector(
                     lambda: self._store.current.secrets.youtube_api_key
                     .get_secret_value())],
                # Il `MemoryStore` non era passato, e senza di lui
                # «non parlarmene piu'» (§15 regola 5) non sopravviveva al
                # riavvio: il file markdown c'era, nessuno lo leggeva.
                Gate(self._memoria, max_per_ora=s.news.max_interruptions_per_hour),
                self._pubblica_news,
            )
            # ⚠️ **Qui mancava il motore.** `Watcher.giro()` non aveva un solo
            # chiamante nel core: il `Watcher` si costruiva a ogni avvio e
            # nessun giro sui feed e' mai avvenuto — `giri_fatti: 0` nello
            # snapshot lo diceva. La cadenza NON e' in §15 e non la invento:
            # e' dedotta dal tetto di 3/ora, e la deduzione sta per esteso in
            # `core/news/motore.py`.
            from core.news.motore import MotoreNews
            from core.news.topics import MODELLO_ARGOMENTI

            # §15 vuole haiku sull'estrattore, e finora non c'era: girava il
            # ripiego locale, che il banco `tests/eval_argomenti.py` misura a
            # **0,410 di precisione** contro una barra di 0,667 dedotta dal
            # tetto di 3 interruzioni/ora. I suoi errori residui sono sintagmi
            # regolari — «la luce», «la fantasia» — che nessuna regola di forma
            # separa da «il bagno»: la differenza e' semantica, e per quella
            # serve un modello. La decisione viene dalla misura, non da §15.
            #
            # `tool=""`: non c'e' niente da azionare in un compito che
            # trasforma testo in parole, e zero tool e' anche la condizione
            # dell'invariante 5 se un domani qualcuno gli passasse una news.
            self._t2_argomenti = ClaudeT2(self._governor, RADICE,
                                          modello=MODELLO_ARGOMENTI,
                                          tool="", max_turns=1,
                                          su_evento=self._supervisore.su_evento)
            # ⚠️ `sta_parlando` arriva PER FUNZIONE, e si legge a ogni giro.
            # §15 regola 2 — «mai mentre Lei parla» — dipende da uno stato che
            # cambia mentre il motore gira: passarne il valore lo fisserebbe
            # all'avvio, cioe' a «zitto», e il gate aprirebbe la bocca sopra la
            # voce. Le news non devono sapere che cosa sia una `VoicePipeline`:
            # ricevono un lettore, e `MotoreNews._parla_adesso` lo interroga.
            self._news = MotoreNews(self._watcher, s.news,
                                    contesto=self._contesto_news,
                                    sta_parlando=self._voce_sta_parlando,
                                    chiedi=self._argomenti_col_modello)
            self._compito_news = self._news.avvia()
            log.info("grado_acceso", grado="news",
                     tetto=s.news.max_interruptions_per_hour,
                     estrattore=MODELLO_ARGOMENTI)
        else:
            log.info("grado_spento", grado="news")

        # §12. ARGUS era scritto per intero — le due strade, la busta non
        # fidata, il rettangolo che viaggia col risultato — e **non aveva un
        # chiamante nel core**. Lo stato arriva dallo STESSO snapshot che
        # alimenta la scrivania: una copia divergerebbe.
        from core.tools.argus import register_argus_tools
        from core.vision.argus import Argus
        from core.vision.ocr import TesseractOcr

        ocr = TesseractOcr()
        self._argus = Argus(ocr, stato=self.state_snapshot)
        register_argus_tools(self._argus, self.chiedi_cattura)
        log.info("grado_acceso" if ocr.disponibile() else "grado_parziale",
                 grado="argus", ocr=ocr.disponibile(),
                 perche="" if ocr.disponibile()
                        else "tesseract assente: resta la strada dello stato, "
                             "che e' quella di §12 per i pannelli di JARVIS")

        # §5.5: il consolidamento notturno. Non ha un interruttore nelle
        # impostazioni perche' non ne ha uno in §5.5: e' parte della memoria,
        # come la potatura. Se la quota e' finita, LO DICE (R33).
        self._compito_conso = asyncio.create_task(self._consolida_di_notte())
        self._compiti.add(self._compito_conso)

        # ADR-007. Dopo la voce e le news, e con la stessa forma: cio' che
        # non si accende viene ANNUNCIATO. Un server MCP e' un programma di
        # terzi, quindi parte spento come voce, codice e vision.
        from core.mcp.montaggio import monta as monta_mcp

        self._mcp = await monta_mcp(s.mcp)

        if s.vision.enabled:
            self._accendi_gesture()
        elif not s.vision.enabled:
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
        self._compiti.add(compito)
        compito.add_done_callback(self._annuncio_finito)

    async def _dillo(self, frase: str) -> None:
        """La frase, con un tetto. Vedi `TETTO_ANNUNCIO_S`."""
        await asyncio.wait_for(self._voce.annuncia(frase), TETTO_ANNUNCIO_S)

    def _annuncio_finito(self, compito: asyncio.Task) -> None:
        """Un annuncio che non e' stato detto si dice — nei log, almeno."""
        self._compiti.discard(compito)
        if compito.cancelled():
            return
        exc = compito.exception()
        if exc is not None:
            log.error("annuncio_non_detto", errore=repr(exc),
                      conseguenza="il ripiego resta nei log e non nell'aria")

    def _modello_wake_vivo(self) -> str | None:
        """Il modello con cui si sta ascoltando, o `None` se non si sa.

        `None` a voce spenta: non e' una bugia, e' l'assenza di un fatto. Chi
        legge lo snapshot ha `wake_model_chiesto` accanto e sa distinguere «non
        sto ascoltando» da «sto ascoltando con un altro modello».
        """
        if self._wake is None:
            return None
        try:
            return self._wake.modello_caricato_da
        except Exception as exc:                          # pragma: no cover
            log.warning("modello_wake_non_leggibile", errore=repr(exc))
            return None

    def _ricarica_frasi(self, wake, nuove) -> None:
        """Le frasi di wake dalle impostazioni appena rilette.

        Gira **sul loop**, non sul thread che ha letto il file: vedi il
        commento in `_gradi()`. Non solleva: un `settings.toml` con una frase
        storta non deve spegnere il microfono, e cio' che c'era continua a
        valere.
        """
        try:
            frasi = {f.say: f.action for f in nuove.voice.wake.phrases}
        except Exception as exc:                         # pragma: no cover
            log.error("frasi_non_lette", errore=repr(exc))
            return
        # ⚠️ **Prima del cancello sulle frasi.** Chi cambia solo il modello non
        # tocca le frasi, quindi la riga qui sotto tornerebbe e la divergenza
        # resterebbe muta — che e' esattamente il caso da cui viene questo
        # difetto.
        self._modello_wake_cambiato(wake, nuove)
        if frasi == dict(getattr(wake, "_frasi", {})):
            return                       # il file e' cambiato altrove
        try:
            wake.set_frasi(frasi)
        except Exception as exc:
            log.error("frasi_non_applicate", errore=repr(exc),
                      conseguenza="restano quelle di prima")
            return
        log.info("frasi_ricaricate_a_caldo", frasi=sorted(frasi))

    def _modello_wake_cambiato(self, wake, nuove) -> None:
        """⚠️ **Il modello non si ricarica a caldo, e prima non lo diceva nessuno.**

        `set_frasi()` cambia la grammatica e lascia il modello dov'e', per una
        ragione misurata: ricaricarlo costa 206 ms sul thread di chi ha salvato
        il file. La scelta e' giusta; il silenzio no.

        Chi cambiava `voice.wake.model` in `settings.toml` vedeva lo snapshot
        rispondere col percorso nuovo, `jarvis doctor` dire `ok` dopo aver
        verificato che quel file esiste, e il riconoscitore continuare col
        modello di prima **fino al riavvio**. §16 dice che nessuna soglia agisce
        senza annunciarlo: questa non agisce, e non annunciava nemmeno quello.
        """
        vivo = getattr(wake, "modello_caricato_da", None)
        chiesto = str(nuove.voice.wake.model)
        if not vivo or vivo == chiesto:
            return
        log.warning("wake_modello_non_ricaricato", vivo=vivo, chiesto=chiesto,
                    conseguenza="si continua ad ascoltare col modello di prima "
                                "fino al riavvio del core")
        self._advisory_sincrono({
            "topic": "agent.advisory",
            "level": "warn",
            "reason": "wake_modello_non_ricaricato",
            "action": "riavvia il core per ascoltare col modello nuovo",
        })

    def _radici_sicure(self) -> Settings:
        """Le impostazioni, con le radici che contengono lo stato di JARVIS
        tolte dall'elenco.

        Ritorna un `Settings`, non una lista, perche' e' cio' che
        `register_file_tools` legge — e lo rilegge a ogni uso, che e' come le
        radici si ricaricano a caldo.
        """
        s = self._store.current
        stato = self._paths.data_dir().resolve()
        buone, tolte = [], []
        for r in s.fs.allowed_roots:
            try:
                risolta = r.expanduser().resolve()
            except OSError:                               # pragma: no cover
                tolte.append(r)
                continue
            # Contiene lo stato — o E' lo stato. Una sorella (`.../workspace`)
            # non lo contiene, e resta.
            if risolta == stato or risolta in stato.parents:
                tolte.append(r)
            else:
                buone.append(r)
        if not tolte:
            return s
        log.error("radice_tolta", radici=[str(r) for r in tolte],
                  perche="contiene lo stato di JARVIS: i tool di file "
                         "potrebbero cestinargli la memoria")
        return s.model_copy(update={"fs": s.fs.model_copy(
            update={"allowed_roots": buone})})

    def _scrivanie_cambiate(self, quante: int) -> None:
        """L'app si e' aperta o chiusa: il microfono la segue.

        **Nascosta va bene.** Il segnale e' la connessione al socket, non la
        visibilita' della finestra: una scrivania ridotta a icona resta
        collegata, e JARVIS resta in ascolto — che e' cio' che serve a un
        assistente a cui si parla senza guardarlo.

        ⚠️ **Conta solo chi si e' DICHIARATO scrivania.** `ws_probe.py` si
        collega per diagnosi e non accende niente: se bastasse una
        connessione qualunque, qualunque cosa sapesse aprire il socket
        potrebbe far ascoltare JARVIS.
        """
        # ⚠️ **Il resoconto viene PRIMA, e fuori dal `return` della voce.**
        # Raccontare cosa si e' fatto mentre non c'era nessuno non ha niente a
        # che vedere con il microfono: legarlo a `self._voce is not None`
        # avrebbe reso il risveglio muto su un sistema con la voce spenta, che
        # e' la configurazione predefinita di §7.1.
        if quante > 0:
            self._compito_di_sfondo(self._resoconto_al_risveglio())

        if self._voce is None:
            return
        self._voce.consenti(quante > 0)
        log.info("microfono_segue_la_scrivania", scrivanie=quante,
                 ascolta=quante > 0)

    async def _resoconto_al_risveglio(self) -> None:
        """Che cosa JARVIS ha fatto mentre non c'era nessuno.

        La firma del JARVIS dei film: ha lavorato, e al ritorno dice **una
        conclusione**. `initiatives/` esisteva dalla Fase 4 con la docstring
        «visibile al risveglio», e non aveva un lettore.

        ⚠️ **Si scrive PRIMA di parlare.** Il diario e' su disco e si legge
        anche a voce spenta; il TTS di ripiego e' EdgeTTS, che e' di rete. Se
        l'ordine fosse rovesciato, una rete assente cancellerebbe il resoconto
        invece di renderlo muto.
        """
        from core.memory import risveglio

        try:
            # ⚠️ **La ronda gira PRIMA di leggere le iniziative**, o cio' che
            # trova adesso finirebbe nel resoconto del risveglio successivo —
            # cioe' domani, per una cosa vista stamattina.
            await self._ronda_di("risveglio")
            da = risveglio.ultimo(self._memoria)
            fatte = self._memoria.iniziative_dal(da)
            if not fatte and not risveglio.e_ora_di_dirlo(da):
                return
            testo = risveglio.componi(fatte)
            risveglio.segna(self._memoria)
            log.info("resoconto_al_risveglio", iniziative=len(fatte), testo=testo)
            # ⚠️ **Flusso `azione`, non `dialogo`.** Ci ero andato con
            # `dialogo`, e dal vivo la frase e' comparsa nel diario DUE volte:
            # una mia, e una del turno che la pronuncia — `annuncia()` produce
            # un `Turno`, e `_annota_dialogo` lo scrive.
            #
            # Le due righe non sono un duplicato da sopprimere: sono due fatti
            # diversi. Qui si registra che JARVIS **ha deciso di riferire**, e
            # resta anche a voce spenta; nel flusso `dialogo` finisce cio' che
            # ha **detto**, se l'ha detto.
            await self._diario.annota(
                "azione", intento="resoconto_al_risveglio", args=None,
                ok=True, da="risveglio", strada="diario",
                testo=testo, iniziative=len(fatte), errore=None)
        except Exception as exc:
            log.error("resoconto_caduto", errore=repr(exc))
            return

        if self._voce is not None:
            try:
                await self._dillo(testo)
            except Exception as exc:
                # Gia' scritto nel diario: qui si perde la voce, non il fatto.
                log.warning("resoconto_non_detto", errore=repr(exc))

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
        if self._compito_voce.done():
            return "chiuso"
        # Prima del battito: un microfono chiuso APPOSTA non e' un microfono
        # muto, e chiamarlo «muto da 40 s» sarebbe un allarme per una cosa
        # voluta — cioe' il modo piu' rapido di far ignorare gli allarmi.
        if self._voce is not None and not self._voce.ascolta:
            return "sospeso: nessuna scrivania"
        # ⚠️ **«aperto» diceva che il COMPITO gira, non che l'audio arriva.**
        #
        # Il 26 agosto il compito era vivo, il ciclo fermo, e `pw-record`
        # bloccato in `anon_pipe_write` — pipe piena, nessuno legge — per
        # **un'ora**. Lo snapshot ha detto «aperto» per tutta l'ora, e
        # l'unico modo di accorgersene e' stato che qualcuno dicesse «non mi
        # sente». Un compito vivo che non consuma il suo flusso e' un
        # microfono chiuso con un'etichetta sbagliata.
        muto = self._voce.muto_da() if self._voce is not None else None
        if muto is not None and muto > SILENZIO_SOSPETTO_S:
            return f"muto da {muto:.0f} s"
        return "aperto"

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

    def _imposta_da_ui(self, msg) -> None:
        """Una modifica chiesta dalla pagina impostazioni (§26.7).

        Sincrono come gli altri handler in ingresso, quindi il lavoro vero va
        in un compito — **tenuto**, perche' `asyncio` referenzia i task solo
        debolmente e uno raccolto a meta' scrittura sparirebbe in silenzio.
        """
        compito = asyncio.create_task(self._imposta(msg.chiave, msg.valore))
        self._compiti.add(compito)
        compito.add_done_callback(self._compiti.discard)

    async def _imposta(self, chiave: str, valore) -> None:
        """Invoca il tool e **rimanda l'esito**.

        L'esito torna indietro perche' un salvataggio che fallisce in silenzio
        e' il guasto che questa sessione ha inseguito tutto il giorno: la
        pagina deve poter dire «rifiutato, e perche'» invece di mostrare un
        valore che sul disco non c'e'.
        """
        esito = await registry.invoke("imposta_valore",
                                      {"chiave": chiave, "valore": valore})
        await self._ws.broadcast({
            "topic": "ui.impostazione",
            "chiave": chiave,
            "ok": bool(esito.ok),
            "valore": (esito.output or {}).get("valore") if esito.ok else None,
            "errore": esito.error,
        })
        log.info("impostazione_dalla_pagina", chiave=chiave, ok=esito.ok,
                 errore=esito.error)

    async def _argomenti_col_modello(self, compito: str) -> str:
        """Lo spawn di §15 per l'estrattore di argomenti.

        **Solleva** se non riesce, ed e' voluto: `EstrattoreLLM` prende
        l'eccezione, ricade su `estrai_locale` e lo ANNUNCIA nei log
        (invariante 12). Restituire una stringa vuota invece farebbe sparire
        gli argomenti in silenzio, che e' il guasto peggiore — sembrerebbe che
        non si sia parlato di niente.

        Il Governor e' fail-closed: a quota finita `esegui()` torna con
        `ok=False`, e da qui esce come ripiego annunciato invece che come
        crollo. Con batch di 600 s sono 6 spawn l'ora contro un tetto di 15.
        """
        r = await self._t2_argomenti.esegui(compito, "argomenti")
        if not r.ok:
            raise RuntimeError(r.errore or "estrazione argomenti non riuscita")
        return r.testo

    def _sguardo_voce(self, leggi, campo: str):
        """Uno stato della voce, col perche' se non si sa.

        ⚠️ **Ogni campo del `Contesto` cade per conto suo.** `MotoreNews`
        costruisce la lettura con `self._contesto()`: se questa radice solleva,
        non e' un campo a diventare ignoto — e' il giro delle news a morire.
        Tre campi che dipendono dallo stato vivo della voce e una sola eccezione
        che li porta via tutti insieme non e' fail-closed, e' un guasto.

        ⚠️ **A voce spenta la causa e' `non_composto`, e non `ha_sollevato`.**
        Senza questa riga `lambda: self._voce.frase_in_corso` alzerebbe un
        `AttributeError` su `None`, e un interruttore da accendere arriverebbe
        a chi guarda travestito da difetto da inseguire. Sono le due cause che
        questo turno esiste per distinguere: per il gate valgono lo stesso —
        sull'ignoto §15 tace — per chi legge no.
        """
        from core.news.conoscibilita import NON_COMPOSTO, Sguardo, guarda

        if self._voce is None:
            return Sguardo(None, NON_COMPOSTO)
        return guarda(leggi, campo=campo)

    def _voce_frase_in_corso(self):
        """Se il Signore ha una frase a meta' — §15, «mai a meta' frase».

        ⚠️ **Qui c'era `False` fisso**, con la giustificazione «il turno
        dell'utente e' chiuso quando il giro dei feed gira». Non e' vero: il
        giro delle news sta su un timer suo, indipendente dai turni, e puo'
        scattare mentre il Signore parla. Un valore scritto a mano presentato
        come un fatto, che teneva spenta una delle cinque regole di §15.
        """
        return self._sguardo_voce(lambda: self._voce.frase_in_corso,
                                  "frase_in_corso")

    def _voce_sta_parlando(self) -> bool | None:
        """Se JARVIS ha voce in uscita **adesso** — §15, regola 2.

        `None` a voce non composta: non e' `False`. `Contesto` e' un tri-stato
        apposta, e «non lo so» non interrompe. A voce spenta non c'e' nessuno
        che possa saperlo, e quello e' esattamente il caso in cui si tace.

        Il lettore e' una FUNZIONE e non un valore: `MotoreNews` lo chiama a
        ogni giro, quindi `self._voce` puo' nascere dopo, cambiare stato o non
        esserci affatto senza che la giunzione vada rifatta.

        ⚠️ **Non ingoia l'eccezione, e questa e' una riga tolta.** Qui c'era un
        `try/except` che rendeva `None` una pipeline rotta, e `MotoreNews` ne ha
        gia' uno che fa la stessa cosa e in piu' sa CLASSIFICARLA. Ingoiando qui,
        un guasto arrivava a chi guarda travestito da voce spenta — e la
        distinzione fra un interruttore e un difetto e' esattamente cio' che
        questo campo doveva smettere di perdere. Chi produce il campo e' uno
        solo: `MotoreNews._parla_adesso`, che lo legge a ogni giro.
        """
        if self._voce is None:
            return None
        return self._voce.sta_parlando

    def _contesto_news(self):
        """Che cosa sta succedendo adesso, e che cosa non si sa — §15, 2 e 3.

        Torna una `Lettura`: gli stessi tre tri-stati che il gate ha sempre
        ricevuto, **piu'** il perche' di ciascun ignoto. Il gate riceve
        `Contesto` e non un byte di piu': la conoscibilita' e' per chi guarda,
        e una regola non deve poterla leggere.

        ⚠️ **`sta_parlando` NON si dichiara qui.** Qui c'era
        `bool(self._voce._sta_parlando)`: un campo privato di un altro modulo,
        letto una volta per giro dalla radice di composizione. Adesso quel campo
        ha **un** produttore — `MotoreNews._parla_adesso`, che interroga
        `_voce_sta_parlando` a ogni giro — e questo metodo dichiara solo cio'
        che sa la radice. Il campo che manca qui non e' un buco: la `Lettura`
        lo chiama `non_prodotto` finche' nessuno lo riempie, che e' la cosa piu'
        importante da vedere in uno snapshot.

        ⚠️ **`frase_in_corso` non e' piu' `False` scritto a mano**, e
        `pannello_a_schermo_intero` un produttore ce l'ha e non e' stato
        scritto: c'era gia'. `GeometriaPannello.massimizzato` esiste da §26.2,
        la scrivania lo riempie da WinBox, `ui.layout` lo porta e pydantic lo
        valida — e nessuno lo leggeva. Finche' quel campo restava `None`, il
        gate trattava l'ignoto come divieto e **nessuna card poteva passare in
        esercizio, mai, per costruzione**.
        """
        from core.news.conoscibilita import Lettura, guarda

        return Lettura({
            "frase_in_corso": self._voce_frase_in_corso(),
            "pannello_a_schermo_intero": guarda(
                self._layout.a_schermo_intero, campo="pannello_a_schermo_intero"),
        })

    # ── ARGUS: §12, e le due strade ─────────────────────────────────────────

    def _cattura_arrivata(self, msg) -> None:
        """La risposta del ponte. Sincrono: lo chiama il lettore del socket."""
        futuro = self._catture.pop(msg.id, None)
        if futuro is None or futuro.done():
            # Una cattura scaduta che arriva dopo non e' un errore: e' tardi.
            log.info("cattura_tardiva", id=msg.id)
            return
        futuro.set_result(msg)

    async def chiedi_cattura(self, timeout: float = TIMEOUT_CATTURA_S):
        """Chiede al ponte uno scatto della finestra e aspetta il PNG.

        ⚠️ **Con un timeout, e non e' prudenza generica.** Il ponte e' un altro
        processo: se Electron non e' avviato, o la finestra e' distrutta, o la
        cattura fallisce, `catturaEInvia` **non risponde affatto** — lo dice il
        suo stesso commento («il core scade da solo»). Senza timeout questa
        coroutine resterebbe appesa per sempre, e con lei il tool che l'ha
        chiamata.
        """
        if self._ws.client_count == 0:
            raise RuntimeError("nessun ponte collegato: la finestra non c'e'")
        ident = uuid.uuid4().hex[:16]
        futuro: asyncio.Future = asyncio.get_running_loop().create_future()
        self._catture[ident] = futuro
        await self._ws.broadcast({"topic": "argus.capture_request", "id": ident})
        try:
            return await asyncio.wait_for(futuro, timeout)
        except TimeoutError:
            self._catture.pop(ident, None)
            raise RuntimeError(
                f"il ponte non ha risposto in {timeout:.0f} s: nessuna cattura"
            ) from None

    async def _intento_del_core(self, intent: grammar.Intent) -> dict[str, Any]:
        """Gli intenti che esegue la radice di composizione.

        Uno solo, per ora: «non parlarmene piu'» di §15, che era l'unica delle
        cinque regole senza una strada — `Gate.silenzia()` scriveva il file ed
        era chiamata soltanto dai suoi test.
        """
        if intent.tool == "silence_topic":
            return await self._silenzia_argomento(str(intent.args.get("topic") or ""))
        if intent.tool == "doctor":
            return await self._diagnostica()
        if intent.tool in ("brief_me", "needs_attention"):
            return await self._meta_comando(intent.tool)
        return {"ok": False, "tier": "t0", "intento": intent.tool,
                "error": "intento del core senza esecutore"}

    async def _diagnostica(self) -> dict[str, Any]:
        """«Come stiamo» — §16.1b, che lo chiede esplicitamente a voce.

        `jarvis doctor` esisteva come comando di terminale dalla Fase 1, e la
        frase T0 che §7.6 gli assegna non aveva un esecutore: si poteva
        chiedere «come stiamo» e non succedeva niente.

        Va sul bus **e** a voce, come §16.1b prescrive («stesso contenuto sul
        topic `agent.advisory` e nel pannello telemetria, e raggiungibile a
        voce»). A voce si dice solo cio' che non e' `ok`: leggere quindici
        righe verdi ad alta voce sarebbe inutilizzabile.
        """
        from core import doctor

        try:
            controlli = await doctor.run_checks()
        except Exception as exc:                          # pragma: no cover
            log.error("doctor_fallito", errore=repr(exc))
            return {"ok": False, "tier": "t0", "intento": "doctor",
                    "error": f"diagnostica non riuscita: {type(exc).__name__}"}

        righe = [{"nome": c.nome, "stato": c.stato, "dettaglio": c.dettaglio}
                 for c in controlli]
        malati = [c for c in controlli if c.stato != "ok"]
        await self._ws.broadcast({
            "topic": "agent.advisory",
            "level": "warn" if malati else "info",
            "reason": "diagnostica",
            "dettaglio": righe,
        })

        if not malati:
            frase = f"Tutti i sistemi nominali, Signore. {len(controlli)} controlli."
        else:
            elenco = "; ".join(f"{c.nome} {c.stato}" for c in malati[:3])
            frase = (f"Signore, {len(malati)} sistemi su {len(controlli)} "
                     f"chiedono attenzione: {elenco}.")
        self._annuncia_a_voce(frase, registra=False)
        log.info("doctor_a_voce", controlli=len(controlli), malati=len(malati))
        return {"ok": not malati, "tier": "t0", "intento": "doctor",
                "output": {"controlli": righe, "malati": len(malati)}}

    #: I due meta-comandi di §7.6, e che cosa si chiede al modello.
    #: Frasi diverse perche' sono domande diverse: una guarda indietro, l'altra
    #: guarda cio' che aspetta.
    META_COMANDI = {
        "brief_me": "Fammi un briefing di due frasi su come e' andata la "
                    "giornata di lavoro su questo progetto: guarda il log di "
                    "git di oggi e i documenti in docs/acceptance/ piu' "
                    "recenti. Rispondi in italiano, parlato, senza elenchi.",
        "needs_attention": "In due frasi: che cosa in questo progetto richiede "
                           "attenzione adesso? Guarda i punti dichiarati NON "
                           "VERIFICATI nei docs/acceptance/ piu' recenti e lo "
                           "stato di git. Rispondi in italiano, parlato, senza "
                           "elenchi.",
    }

    async def _meta_comando(self, quale: str) -> dict[str, Any]:
        """§7.6: «non chiedono UNA COSA, chiedono lo STATO».

        La frase e' deterministica (T0), la risposta no: e' un compito lungo, e
        va in T2 — che passa dal Governor come ogni spawn (invariante 16).

        ⚠️ **Non si attende.** Un briefing puo' costare decine di secondi, e
        `esegui_t0` sta sul percorso della voce: restituisce subito «ci sto
        pensando», e la risposta arriva quando arriva. Bloccare qui vorrebbe
        dire un JARVIS muto per mezzo minuto dopo una domanda.
        """
        if self._t2_meta is None:
            return {"ok": False, "tier": "t0", "intento": quale,
                    "error": "T2 non composto: nessun modello per i meta-comandi"}

        compito = asyncio.create_task(self._rispondi_al_meta(quale))
        self._compiti.add(compito)
        compito.add_done_callback(self._compiti.discard)
        self._annuncia_a_voce("Un momento, Signore.", registra=False)
        return {"ok": True, "tier": "t0", "intento": quale, "output": {"avviato": True}}

    async def _rispondi_al_meta(self, quale: str) -> None:
        """Lo spawn, e la risposta detta. Non solleva: e' un task di sfondo."""
        # §5.5: **uno spawn T2 parte da zero, e non deve.**
        # `ContextPruner.contesto_per_t2()` esisteva dalla Fase 4 e non aveva
        # un chiamante: ogni T2 ripartiva senza sapere niente di cio' che era
        # gia' stato detto o deciso. I fatti fissati per primi — sono
        # dell'utente e valgono sempre — poi i topic che somigliano al compito.
        #
        # ⚠️ Non e' duplicare il contesto di T1 (invariante 17): T1 tiene la
        # SUA conversazione, questo e' un processo effimero che nasce senza
        # niente. Il divieto e' di gestire due volte lo stesso contesto, non di
        # dare a un estraneo cio' che serve per capire la domanda.
        contesto = ContextPruner(self._memoria).contesto_per_t2(self.META_COMANDI[quale])
        compito = (f"{contesto}\n\n---\n\n{self.META_COMANDI[quale]}"
                   if contesto.strip() else self.META_COMANDI[quale])
        log.info("meta_comando_avviato", quale=quale, contesto_caratteri=len(contesto))
        try:
            r = await self._t2_meta.esegui(compito, quale)
        except Exception as exc:
            log.error("meta_comando_fallito", quale=quale, errore=repr(exc))
            self._annuncia_a_voce("Signore, non sono riuscito a farmi un'idea.",
                                  registra=False)
            return
        if not r.ok or not r.testo.strip():
            # ANNUNCIATO: un meta-comando che tace e' indistinguibile da uno
            # che non e' mai partito.
            log.warning("meta_comando_vuoto", quale=quale, errore=r.errore)
            self._annuncia_a_voce("Signore, non sono riuscito a farmi un'idea.",
                                  registra=False)
            return
        log.info("meta_comando", quale=quale, durata_s=r.durata_s, caratteri=len(r.testo))
        await self._ws.broadcast({"topic": "agent.advisory", "level": "info",
                                  "reason": quale, "dettaglio": r.testo})
        self._annuncia_a_voce(r.testo.strip(), registra=True)

    async def _silenzia_argomento(self, argomento: str) -> dict[str, Any]:
        """§15 regola 5. Persistente, annunciato, e **senza conferma**.

        ⚠️ **Perche' non passa dal registro dei tool e dalla conferma di §6.2.**
        L'invariante 3 esiste per le operazioni irreversibili sui file DI CHI
        USA il sistema: mostra il path risolto perche' una cancellazione non si
        annulla. Qui non si tocca niente di Suo — si scrive una preferenza che
        Lei ha appena pronunciato, dentro la memoria di JARVIS, e si annulla
        cancellando una riga da un file markdown. Chiedere «confermi di voler
        chiudere l'argomento?» a chi ha appena detto «non parlarmene piu'»
        sarebbe attrito nel punto in cui §15 esiste per toglierlo.
        **La conferma e' la frase.** Cio' che resta e' la responsabilita': si
        ANNUNCIA a voce e si scrive nel log, come i ripieghi dell'invariante 12.

        Senza argomento e' **anaforica**: chiude cio' di cui si parlava, cioe'
        le parole che hanno fatto passare l'ultima card. Se non c'e' stata
        nessuna card, lo dice invece di tacere: «non ho niente da chiudere» e'
        un esito, e il silenzio no.
        """
        if self._news is None:
            return {"ok": False, "tier": "t0", "intento": "silence_topic",
                    "error": "le news sono spente: non c'e' niente da chiudere"}

        parole = [argomento.strip().lower()] if argomento.strip() else list(
            self._ultima_news_colpita)
        if not parole:
            frase = "Signore, non ho niente da chiudere: non Le ho ancora detto nulla."
            self._annuncia_a_voce(frase, registra=False)
            return {"ok": False, "tier": "t0", "intento": "silence_topic",
                    "error": "nessun argomento in corso"}

        for p in parole:
            self._watcher._gate.silenzia(p)
        elenco = ", ".join(parole)
        self._annuncia_a_voce(f"Va bene, Signore. Non Le parlero' piu' di {elenco}.",
                              registra=False)
        log.info("argomento_chiuso", parole=parole, da="voce")
        return {"ok": True, "tier": "t0", "intento": "silence_topic",
                "output": {"silenziati": parole}}

    async def _pubblica_news(self, msg: dict) -> None:
        """Il broadcast, piu' la menzione vocale di §15.

        ⚠️ La menzione **non aspetta** e non puo' far cadere il giro: parlare
        passa da EdgeTTS, che e' di rete. Stessa forma degli annunci di
        ripiego, e per la stessa ragione.

        ⚠️ E il titolo e' **dato non fidato** (invariante 5). Dirlo ad alta
        voce non e' eseguirlo: il TTS non ha tool, ed e' precisamente il
        «contesto con zero tool» che §12 richiede. Quel che NON si fa e'
        passarlo a qualcosa che agisce.
        """
        await self._ws.broadcast(msg)
        if msg.get("topic") != "news.card" or self._voce is None:
            return
        titolo = str(msg.get("titolo") or "").strip()
        if not titolo:
            return
        # Che cosa ha fatto passare QUESTA card: sono le parole che «non
        # parlarmene piu'» deve chiudere quando non ne nomina nessuna. Si
        # calcola qui e non nel gate perche' e' una proprieta' della card
        # mostrata, non della decisione.
        minuscolo = titolo.lower()
        self._ultima_news_colpita = [
            p for p in self._news.argomenti.parole() if p in minuscolo
        ] if self._news is not None else []

        fonte = str(msg.get("fonte") or "").strip()
        breve = f"Signore, da {fonte}: {titolo}." if fonte else f"Signore: {titolo}."
        self._annuncia_a_voce(breve, registra=True)

    async def _ronda_di(self, innesco: str) -> None:
        """Esegue i protocolli di quell'innesco e registra cio' che e' cambiato.

        ⚠️ **Un'iniziativa solo quando c'e' qualcosa da dire.** Una ronda che non
        trova niente non e' un evento: registrarla riempirebbe `initiatives/` di
        righe che nessuno legge, e il resoconto direbbe ogni giorno che JARVIS ha
        guardato senza dire mai che cosa. Il silenzio di un protocollo lo copre
        gia' «niente da riferire», una volta al giorno.

        Non solleva: e' un compito di sfondo, e un protocollo storto non deve
        poter portare via il risveglio o il consolidamento.
        """
        from core.protocolli import TIPO_INIZIATIVA

        for p in [x for x in self._protocolli if x.innesco == innesco]:
            try:
                esito = await self._ronda.esegui(
                    p, registry.invoke, nomi_tool=set(registry.names()))
            except Exception as exc:                      # pragma: no cover
                log.error("ronda_caduta", nome=p.nome, errore=repr(exc))
                continue
            if not esito.cambiato:
                continue
            try:
                self._memoria.registra_iniziativa(
                    TIPO_INIZIATIVA,
                    {"nome": p.nome, "innesco": innesco, "frase": esito.frase})
            except Exception as exc:                      # pragma: no cover
                log.error("iniziativa_non_registrata", errore=repr(exc))

    def _annota_dialogo(self, turno) -> None:
        """Le due battute del turno, nel flusso `dialogo`.

        ⚠️ **Porta anche cio' che il turno NON diceva a nessuno**: se e' stato
        interrotto, e se il testo detto e' una misura o un limite superiore.
        Senza, rileggendo il registro non si distingue una risposta finita da
        una troncata — che e' esattamente la differenza che §7.4 esiste per
        tenere.
        """
        utente = (getattr(turno, "testo_utente", "") or "").strip()
        detto = (getattr(turno, "testo_detto", "") or "").strip()
        if not utente and not detto:
            return
        for chi, testo in (("signore", utente), ("jarvis", detto)):
            if not testo:
                continue
            self._compito_di_sfondo(self._diario.annota(
                "dialogo", chi=chi, testo=testo,
                frase_wake=getattr(turno, "frase_wake", "") or None,
                interrotto=bool(getattr(turno, "interrotto", False)),
                misurato=bool(getattr(turno, "detto_misurato", False))
                if chi == "jarvis" else None,
                secondi=round(getattr(turno, "secondi_detti", 0.0), 2)
                if chi == "jarvis" else round(getattr(turno, "secondi_ascoltati", 0.0), 2),
            ))

    def _annota_instradamento(self, turno) -> None:
        """La riga di `azione` per gli enunciati che NON sono diventati un tool.

        ⚠️ **Il registro non sapeva dire perche' non era successo niente.**
        Il primo comando detto davvero al microfono — «apriti i pannelli
        telemetria» — e' finito a T1, che ha risposto «Vedo, Signore. Mi occupo
        del caricamento della telemetria». Nel diario restavano due righe di
        `dialogo` e **zero** righe di `azione`, e per sapere se T0 avesse anche
        solo visto quella frase ho dovuto eseguire il parser a mano.

        `esegui_t0` annota gia' cio' che la grammatica riconosce. Qui si
        annota l'altra meta': la delega a T1 e la caduta. Sono le due strade
        che non producono un tool, ed erano le due che il registro taceva.
        """
        strada = getattr(turno, "strada", "t1")
        if strada == "t0":
            return                          # gia' annotata da `esegui_t0`
        testo = (getattr(turno, "testo_utente", "") or "").strip()
        if not testo:
            return
        self._compito_di_sfondo(self._diario.annota(
            "azione", intento=None, args=None,
            # Delegare a T1 e' un esito riuscito; cadere no. La distinzione la
            # porta la strada, non un'euristica su cosa T1 abbia risposto.
            ok=(strada == "t1"), da="voce", strada=strada,
            # Il testo che non ha trovato un comando. Sta QUI e non solo nel
            # flusso `dialogo` perche' e' l'ingresso da cui si ripara la
            # grammatica: un registro che costringe a incrociare due flussi
            # per la domanda piu' frequente non e' un registro.
            testo=testo,
            quasi_comando=getattr(turno, "quasi_comando", None),
            errore=None if strada == "t1" else "t1_assente",
        ))

    def _compito_di_sfondo(self, coro) -> None:
        """Un compito che nessuno attende, ma di cui si tiene il riferimento:
        senza, Python puo' raccoglierlo a meta'."""
        c = asyncio.create_task(coro)
        self._compiti.add(c)
        c.add_done_callback(self._compiti.discard)

    def _registra_turno_in_memoria(self, turno) -> None:
        """Una riga in `sessions/<oggi>.jsonl`. Non solleva.

        Il nome della sessione e' il **giorno**: un file per giornata invece di
        uno per avvio del core, o un core riavviato tre volte spezzerebbe una
        conversazione in tre file che il consolidatore riassumerebbe
        separatamente.

        Si scrive solo se c'e' qualcosa da scrivere: un turno in cui non ha
        parlato nessuno e' rumore nella cronologia.
        """
        utente = (getattr(turno, "testo_utente", "") or "").strip()
        detto = (getattr(turno, "testo_detto", "") or "").strip()
        if not utente and not detto:
            return
        try:
            self._memoria.registra_turno(
                time.strftime("%Y-%m-%d"),
                {"utente": utente, "jarvis": detto,
                 "azione": getattr(turno, "azione", None)},
            )
        except Exception as exc:
            # Siamo sul percorso della voce: un disco pieno non zittisce JARVIS.
            log.error("turno_non_registrato", errore=repr(exc))

    async def _consolida_di_notte(self) -> None:
        """§5.5: «gira alle 04:00 via scheduler». Lo scheduler non c'era.

        `Consolidatore` era scritto per intero — advisory compresi, e con la
        tensione dell'invariante 3 gia' sciolta e dichiarata — e **non aveva un
        chiamante**. La memoria a lungo termine non e' mai stata consolidata.

        Il ciclo dorme fino alla prossima ricorrenza dell'ora e riprova ogni
        giorno. Non solleva mai: e' un compito di sfondo, e un'eccezione qui
        finirebbe in un `Task` che nessuno guarda.
        """
        from core.memory.consolidate import ORA_DEFAULT, Consolidatore

        conso = Consolidatore(self._memoria, self._t2_conso,
                              su_advisory=self._advisory_sincrono)
        log.info("grado_acceso", grado="consolidamento", ora=ORA_DEFAULT)

        # ⚠️ **RECUPERO, non attesa.** Prima di rimettersi a dormire.
        #
        # Il ciclo qui sotto e' corretto e non era sufficiente: un
        # `asyncio.sleep()` fino alle 04:00 non sopravvive a un riavvio del
        # processo. Misurato sul journal: **27 riavvii in tre giorni**, e in
        # sette giorni nemmeno un consolidamento — solo `grado_acceso` che
        # arma il timer, mai uno scatto. `topics/` e `initiatives/` erano a
        # **zero file**: la memoria di JARVIS aveva soltanto la cronologia
        # grezza.
        #
        # Non si consolida a ogni avvio: `_segna_run()` timbra su disco anche
        # quando non c'era niente da fare, quindi il secondo avvio dello stesso
        # giorno trova il timbro fresco e non fa niente. E' il timbro a limitare
        # la frequenza, non un contatore in memoria — che si azzererebbe con il
        # processo, cioe' con lo stesso difetto.
        if conso.saltato():
            log.info("consolidamento_recupero",
                     perche="una notte e' passata senza consolidamento")
            try:
                log.info("consolidamento", **await conso.esegui())
            except Exception as exc:
                log.error("consolidamento_caduto", errore=repr(exc),
                          quando="recupero")
            await self._ronda_di("notte")

        while True:
            await asyncio.sleep(self._secondi_fino_alle(ORA_DEFAULT))
            try:
                esito = await conso.esegui()
                log.info("consolidamento", **esito)
                await self._ronda_di("notte")
            except Exception as exc:                      # pragma: no cover
                log.error("consolidamento_caduto", errore=repr(exc))

    @staticmethod
    def _secondi_fino_alle(ora: int) -> float:
        """Quanto manca alla prossima ricorrenza di quell'ora locale.

        Separato e statico perche' e' l'unica parte aritmetica del ciclo, ed e'
        l'unica che si possa misurare senza aspettare una notte.
        """
        adesso = datetime.now()
        bersaglio = adesso.replace(hour=ora, minute=0, second=0, microsecond=0)
        if bersaglio <= adesso:
            bersaglio = bersaglio.replace(day=adesso.day) + timedelta(days=1)
        return (bersaglio - adesso).total_seconds()

    # ── gesture: §14, e la catena che non aveva un capo ─────────────────────

    def _accendi_gesture(self) -> None:
        """Compone tracker, riconoscitore, isteresi ed emissione.

        ⚠️ `gestures.emetti()` — «l'unica uscita delle gesture verso il resto
        del sistema», dice il suo docstring — **non aveva un chiamante**. Il
        tracker MediaPipe, il riconoscitore dei quattro gesti di §14 e
        l'isteresi a cinque fotogrammi erano scritti e misurati sul corpus, e
        nessuno li congiungeva: una mano davanti alla telecamera non poteva
        produrre niente, perche' la telecamera non si apriva mai.

        Il grado si accende solo con `vision.enabled = true`, che parte
        **falso**: il commento in `settings.toml` lo dice bene — «il consenso
        migliore e' non accenderla».

        E l'assenza di MediaPipe e' uno **stato normale annunciato**, non un
        guasto: stessa forma di Tesseract in §12.
        """
        from core.gestures.tracker import TrackerMediaPipe

        tracker = TrackerMediaPipe(self._paths.data_dir())
        if not tracker.disponibile():
            log.info("grado_parziale", grado="gesture", mediapipe=False,
                     perche="mediapipe non installato: la telecamera resta chiusa")
            return
        self._compito_gesture = asyncio.create_task(self._gira_gesture(tracker))
        self._compiti.add(self._compito_gesture)
        log.info("grado_acceso", grado="gesture", isteresi=FRAME_ISTERESI)

    async def _gira_gesture(self, tracker) -> None:
        """Il ciclo, in un THREAD, e gli intenti riportati sul loop.

        `fotogrammi()` e' un iteratore **sincrono** che legge dalla telecamera:
        girarlo sul loop bloccherebbe tutto il core fra un fotogramma e
        l'altro. Sta in un thread, e cio' che ne esce torna con
        `call_soon_threadsafe` — la stessa forma del ricarico a caldo delle
        frasi di wake, e per la stessa ragione.

        ⚠️ **Il fotogramma non esce dal thread**: attraversa il confine solo il
        NOME del gesto. §18.3 dice che l'audio senza frase nota non lascia mai
        la macchina; per le immagini vale a maggior ragione, e il modo piu'
        solido di garantirlo e' che il pixel non arrivi nemmeno al loop.
        """
        from core.gestures.mapping import Isteresi, Riconoscitore

        ciclo = asyncio.get_running_loop()
        riconosci, isteresi = Riconoscitore(), Isteresi()

        def _nel_thread() -> None:
            with tracker:
                for fotogramma in tracker.fotogrammi():
                    intento = isteresi.alimenta(riconosci(fotogramma))
                    if intento is not None:
                        ciclo.call_soon_threadsafe(self._gesture_intento, intento)

        try:
            await asyncio.to_thread(_nel_thread)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # La telecamera che si stacca non deve portarsi via il core.
            log.error("gesture_cadute", errore=repr(exc))
            await self._ws.broadcast({
                "topic": "agent.advisory", "level": "warn",
                "reason": "gesture_cadute", "dettaglio": repr(exc),
            })

    def _gesture_intento(self, intento: str) -> None:
        """Un gesto riconosciuto diventa un intento — **passando da `emetti`**.

        Non da `esegui_t0`, e non e' una svista: `emetti()` usa
        `registry.invoke_da_gesture()`, che e' fail-closed sull'invariante 27 e
        rifiuta tutto cio' che non e' dichiarato `gesture_allowed`. Farla
        passare dalla strada della voce vorrebbe dire che una mano puo' fare
        ciò che una frase puo' fare, e §14 dice il contrario.
        """
        async def _fai() -> None:
            from core.gestures.mapping import IntentoNonAmmesso, emetti

            try:
                await emetti(intento, {}, self._ws.broadcast)
            except IntentoNonAmmesso as exc:
                # Un errore di cablaggio, non un gesto sbagliato: si dice.
                log.error("gesture_intento_non_ammesso", intento=intento,
                          errore=str(exc))

        compito = asyncio.create_task(_fai())
        self._compiti.add(compito)
        compito.add_done_callback(self._compiti.discard)

    def _controlla_microfono(self) -> None:
        """§16: nessuna soglia agisce senza annunciarlo — e questa non c'era.

        Emette **sul cambio**, nei due versi, come la VRAM e la ripresa del
        Governor. Un'ora di sordita' silenziosa e' costata una sessione intera:
        il difetto non era il silenzio, era che nessuno se ne accorgesse.
        """
        muto = self._voce.muto_da() if self._voce is not None else None
        sospetto = muto is not None and muto > SILENZIO_SOSPETTO_S
        if sospetto == self._microfono_sospetto:
            return
        self._microfono_sospetto = sospetto
        self._advisory_sincrono({
            "topic": "agent.advisory",
            "level": "warn" if sospetto else "info",
            "reason": "microfono_muto" if sospetto else "microfono_tornato",
            "dettaglio": (f"nessun blocco audio da {muto:.0f} s" if sospetto
                          else "i blocchi audio sono tornati"),
            "secondi": round(muto or 0.0, 1),
        })
        log.warning("microfono", sospetto=sospetto, muto_da=round(muto or 0.0, 1))

    def _controlla_vram(self) -> None:
        """§16, riga VRAM: «headroom insufficiente -> **rifiuta** il caricamento».

        ⚠️ **Il rifiuto oggi non ha un soggetto, e va detto.** `can_admit()` non
        aveva un chiamante perche' nel core **niente si carica sulla GPU**:
        l'invariante 11 vieta i modelli LLM locali, e §9 elenca Vosk, Kokoro,
        MediaPipe e Tesseract tutti su CPU. L'unico consumatore vero e' la
        scena three.js piu' Pixi, che §9 chiama «il consumatore principale» e
        che vive nel renderer — dove il core non puo' rifiutare niente.

        Cio' che il core puo' fare, e che §16 chiede a ogni soglia, e'
        **annunciare**: «ogni soglia emette su `agent.advisory`». Quindi la
        regola si applica per intero — la misura, il confronto, l'advisory — e
        manca solo il verbo «rifiuta», che non ha un oggetto.

        La soglia viene da §9, non da me: la scena e' stimata «~1-2 GB
        (stima prudenziale)». Si prende il **limite inferiore**. Sopra 1 GiB la
        scena potrebbe gia' essere stretta e non diciamo niente; sotto, non ci
        sta di sicuro. Un avviso che grida al lupo viene ignorato, ed e' il
        guasto che §15 e §16 esistono entrambe per evitare.

        **Emette solo sul CAMBIO**, in entrambi i versi. E' la stessa lezione
        di `Governor.riprendi`, applicata subito: annunciare il guasto e tacere
        sul ritorno insegna a fidarsi degli advisory e poi tradisce quella
        fiducia.
        """
        esito = self._gpu_scheduler.can_admit(VRAM_SCENA)
        if esito.granted == (not self._vram_scarsa):
            return                                    # niente e' cambiato
        self._vram_scarsa = not esito.granted
        self._advisory_sincrono({
            "topic": "agent.advisory",
            "level": "warn" if self._vram_scarsa else "info",
            "reason": "vram_insufficiente" if self._vram_scarsa else "vram_tornata",
            "dettaglio": esito.reason,
            # Un rifiuto che non dice quanto mancava e' inservibile: e' scritto
            # in `Admission`, e qui si usa.
            "mancano_byte": esito.shortfall,
            "servono_byte": VRAM_SCENA,
        })
        log.warning("vram", scarsa=self._vram_scarsa, mancano=esito.shortfall,
                    motivo=esito.reason)

    def _impostazioni_non_ricaricate(self, exc: Exception) -> None:
        """§16: nessuna soglia agisce senza annunciarlo — e tenere le
        impostazioni vecchie e' un'azione.

        Non si dice a voce: chi ha appena salvato `settings.toml` e' davanti
        alla tastiera, e l'avviso sulla scrivania arriva dove sta guardando.
        A voce sarebbe un annuncio per una cosa che ha gia' sotto gli occhi.
        """
        motivo = str(exc)
        log.warning("impostazioni_non_ricaricate", errore=motivo)
        self._advisory_sincrono({
            "topic": "agent.advisory", "level": "warn",
            "reason": f"settings.toml non ricaricato, tengo le precedenti: {motivo}",
        })

    def _advisory_sincrono(self, msg: dict) -> None:
        """Il `Consolidatore` chiama un callback SINCRONO, e il socket e'
        asincrono: senza questo ponte la coroutine cadrebbe non attesa."""
        compito = asyncio.create_task(self._ws.broadcast(msg))
        self._compiti.add(compito)
        compito.add_done_callback(self._compiti.discard)

    def _voce_su_azione(self, azione: str, args: dict) -> None:
        """Un'azione decisa dalla voce arriva alla scrivania **come le altre**.

        ⚠️ **Come le altre, e non per una via tutta sua.** Questa funzione
        trasmetteva `{"topic": "ui.action", "azione": ...}`, e *nessuno*
        ascolta `ui.action`: il renderer si iscrive a **`ui.intent`** con
        `{intento, args}` (`ui/src/desk/scrivania.js:800`). Il risultato e' che
        JARVIS riconosceva la frase, scriveva `azione_diretta` nel log, e la
        scrivania non riceveva niente — un guasto perfettamente silenzioso, e
        indistinguibile da «non mi ha sentito».

        Peggio: `esegui_t0()` **produceva gia'** il messaggio giusto, con
        l'allowlist di `INTENTI_UI` e con `registry.invoke()` per gli intenti
        che nominano un tool — cioe' con la conferma umana dove serve
        (invariante 3). Passando dal socket a mano, un intento vocale che
        nominava un tool non lo invocava affatto: **le due meta' erano
        entrambe rotte.**

        E' la stessa specie di difetto di §13, del `Watcher` delle news e di
        `_gradi()`: due pezzi scritti, provati, e mai congiunti. Qui il
        proprietario della strada esisteva gia' e ne ho costruita una seconda.
        """
        # `create_task` e non `await`: `su_azione` e' un callback SINCRONO —
        # la pipeline lo chiama da dentro il proprio ciclo, e restituirle una
        # coroutine non attesa la lascerebbe cadere in silenzio.
        compito = asyncio.create_task(self._instrada_voce(azione, args))
        self._compiti.add(compito)
        compito.add_done_callback(self._compiti.discard)

    async def _instrada_voce(self, azione: str, args: dict) -> None:
        """Traduce l'azione di una frase-wake in un intento, e la instrada.

        Le azioni di `settings.toml` hanno la forma `scene:welcome_home`
        (§26.6, e `docs/SPEC.md` riga 656). Il renderer si aspetta invece
        `intento: "scene"` con `args.nome`, perche' `applicaScena` legge
        `args.nome ?? args.scena`: la stringa col due punti va **spezzata**,
        non passata intera.

        Non serve un elenco di prefissi ammessi: `esegui_t0()` rifiuta e logga
        cio' che non e' ne' in `INTENTI_UI` ne' nel registry, e l'allowlist
        resta una sola — la sua.
        """
        if ":" in azione:
            testa, coda = azione.split(":", 1)
            intento, argomenti = testa, {"nome": coda, **args}
        else:
            intento, argomenti = azione, dict(args)
        esito = await self.esegui_t0(grammar.Intent(tool=intento, args=argomenti))
        if not esito.get("ok"):
            # Una frase riconosciuta che non arriva da nessuna parte si DICE.
            # E' il difetto appena corretto: senza questa riga, l'unica traccia
            # sarebbe `azione_diretta`, che dice che e' partita e non che e'
            # arrivata.
            log.warning("voce_senza_destinazione", azione=azione,
                        intento=intento, errore=esito.get("error"))

    def _voce_su_turno(self, turno) -> None:
        """ADR-004: **il turno si conta**, e senza questa riga il contatore
        costruito ieri non avrebbe mai visto un secondo di audio.

        `tier` distingue chi ha parlato: `stt` per cio' che abbiamo ascoltato,
        `tts` per cio' che abbiamo detto. `fallback` e' vero quando il provider
        non e' il primario — ed e' la misura di quanto Deepgram sia davvero
        affidabile su questa rete (invariante 12).
        """
        # ⚠️ **SECONDI DI AUDIO, non latenze.**
        #
        # Questa riga passava `latenza_wake_ms` come «secondi STT» e
        # `latenza_primo_suono_ms` come «secondi TTS». Sono due latenze: una
        # sessione da 12,5 s compariva in `conso/` come 0,00002 s, e
        # `latenza_wake_ms` non e' nemmeno la latenza di risveglio — e' il
        # costo di UNA `AcceptWaveform`.
        #
        # ADR-004 si chiama «contare prima di spendere»: cio' che un fornitore
        # fattura sono i secondi di audio, e adesso sono quelli che arrivano.
        for tier, scelta, secondi in (
            ("stt", self._voce._stt, turno.secondi_ascoltati),
            ("tts", self._voce._tts, turno.secondi_detti),
        ):
            if secondi <= 0:
                continue
            self._governor.registra_voce(
                tier, scelta.provider.name, secondi,
                fallback=not scelta.primario)
        log.info("turno_vocale", frase=turno.frase_wake, azione=turno.azione,
                 wake_ms=round(turno.latenza_wake_ms, 1),
                 primo_suono_ms=round(turno.latenza_primo_suono_ms, 1))

        # §5.5: **il turno finisce nel registro della sessione.**
        # `MemoryStore.registra_turno()` esisteva dalla Fase 4 e non aveva un
        # chiamante: `sessions/` restava vuota, e il consolidatore notturno —
        # che legge esattamente da li' — non avrebbe avuto niente da leggere
        # nemmeno il giorno in cui qualcuno lo avesse azionato. Due pezzi
        # scollegati che si nascondevano a vicenda.
        #
        # ⚠️ **Qui la TRASCRIZIONE va su disco**, e prima non ci andava. Non
        # l'audio: §18.3 dice che l'audio senza frase nota non lascia la
        # macchina e non viene salvato, e resta vero. Il testo si', ed e' cio'
        # che §5.5 prescrive — `sessions/` e' nella pianta di §5.5 con la
        # dicitura «cronologia grezza». Sta in `memory_data/`, sotto il
        # controllo dell'utente, e si cancella cancellando il file.
        self._registra_turno_in_memoria(turno)
        self._annota_dialogo(turno)
        self._annota_instradamento(turno)

        # §15: **gli argomenti vengono dalla conversazione.** `EstrattoreLLM`
        # esisteva dalla Fase 8 e non aveva un chiamante, e il suo commento
        # diceva gia' «il giorno in cui la pipeline sara' composta bastera'
        # passargliela». E' oggi.
        #
        # Senza questa riga il motore girerebbe a vuoto per sempre: nessun
        # argomento, nessun giro — e sarebbe un ciclo che non fa niente invece
        # di una funzione che non c'e', cioe' peggio.
        detto = getattr(turno, "testo_utente", "") or ""
        if self._news is not None and detto.strip():
            compito = asyncio.create_task(self._news.ascolta(detto))
            self._compiti.add(compito)
            compito.add_done_callback(self._compiti.discard)

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
        if self._disiscrivi_frasi is not None:
            # Prima di fermare il wake: un cambio che arrivasse dopo
            # troverebbe un riconoscitore che non c'e' piu'.
            self._disiscrivi_frasi()
            self._disiscrivi_frasi = None
        if self._t1 is not None:
            await self._t1.stop()
            log.info("grado_spento", grado="voce", perche="arresto")
        if self._compito_gesture is not None:
            self._compito_gesture.cancel()
            self._compito_gesture = None

        if getattr(self, "_disiscrivi_errori", None) is not None:
            self._disiscrivi_errori()
            self._disiscrivi_errori = None
        if self._compito_conso is not None:
            self._compito_conso.cancel()
            self._compito_conso = None

        if self._news is not None:
            await self._news.ferma()
            self._news = None
            log.info("grado_spento", grado="news", perche="arresto")
        if self._mcp is not None:
            # I server MCP sono processi figli: senza questa riga
            # sopravviverebbero al core che li ha avviati.
            await self._mcp.ferma()
            log.info("grado_spento", grado="mcp", perche="arresto")

    # ── ciclo di vita ────────────────────────────────────────────────────────

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._chiedi_stop, sig)

        # ⚠️ **Una ricarica fallita non la sentiva nessuno.**
        #
        # `SettingsStore.reload()` tiene le impostazioni precedenti e scrive
        # `ricarica_fallita` nel journal. `subscribe_errors` esiste per dirlo a
        # qualcuno, e **non aveva un chiamante**: l'ha trovato
        # `scripts/orfani.py`.
        #
        # Il caso non e' raro ed e' il peggiore per chi lo vive: il Signore
        # corregge `settings.toml`, salva, e non succede niente. Da fuori e'
        # indistinguibile da «la modifica non ha avuto effetto» o da «JARVIS
        # l'ha ignorata», e l'unica traccia sta in un journal che nessuno
        # guarda mentre edita un file.
        #
        # `call_soon_threadsafe` perche' il richiamo arriva dal thread di
        # watchdog: `_advisory_sincrono` fa `create_task`, che di la' non ha un
        # loop. E' lo stesso rimbalzo che gia' fa `_ricarica_frasi`.
        self._disiscrivi_errori = self._store.subscribe_errors(
            lambda exc: loop.call_soon_threadsafe(
                self._impostazioni_non_ricaricate, exc))
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
    # ⚠️ **PRIMA di `Engine()`, e non e' una preferenza di stile.**
    #
    # «Le chiavi API MAI nei log» e' un invariante di CLAUDE.md, e fino a oggi
    # non aveva un installatore: `core/settings.py` costruiva il registro dei
    # segreti e il processore che li maschera, ma in tutto `core/` non esisteva
    # una sola chiamata a `structlog.configure()`. La catena predefinita non
    # filtra niente — una protezione scritta e mai installata e' come nessuna
    # protezione, con l'aggravante che chi legge il codice la crede attiva.
    #
    # L'ordine: `Engine.__init__` costruisce `SettingsStore`, che chiama
    # `load_settings()`, che scrive `settings_caricate` con l'elenco delle
    # chiavi presenti E popola `SECRETS`. Configurare dopo vorrebbe dire che la
    # PRIMA riga dell'avvio esce senza redazione, ed e' proprio quella che
    # parla di chiavi.
    core_log.configura()
    e = Engine()
    await e.run()
    return e._codice_uscita


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
