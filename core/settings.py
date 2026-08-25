"""Impostazioni e chiavi — SPEC §8.

Due file separati, con due politiche diverse:

* `settings.toml` — configurazione. Permessi larghi: **avviso**.
* `secrets.toml`  — chiavi API. Permessi larghi: **rifiuto**.

L'asimmetria e' voluta. Un `settings.toml` leggibile dal gruppo e' sciatteria;
un `secrets.toml` leggibile dal gruppo e' una chiave compromessa, e continuare
come se nulla fosse significherebbe usarla sapendo che e' esposta.

Alcuni vincoli del `CLAUDE.md` sono imposti QUI, dallo schema, invece di essere
affidati alla disciplina di chi scrive il file di configurazione:

* invariante 4  — `fs.trash_only` accetta solo `True`
* invariante 11 — `llm.backend` accetta solo `"claude_code"`
* SPEC §12      — `vision.scope` accetta solo `"app"`

E' lo stesso principio dell'invariante 27 («imposto nel registry, non lasciato
alla disciplina»): un invariante che la macchina non verifica decade.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, Literal

import structlog
import tomlkit
from pydantic import (BaseModel, ConfigDict, Field, SecretStr, field_validator,
                      model_validator)
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from core.platform import Paths, paths as platform_paths

log = structlog.get_logger(__name__)

SETTINGS_FILENAME = "settings.toml"
SECRETS_FILENAME = "secrets.toml"


# ─────────────────────────────────────────────────────────────────────────────
# Errori
# ─────────────────────────────────────────────────────────────────────────────


class SettingsError(Exception):
    """Base delle anomalie di configurazione."""


class MissingSettingsFile(SettingsError):
    """Un file di configurazione atteso non esiste."""


class InsecurePermissions(SettingsError):
    """Un file di segreti e' leggibile oltre il proprietario."""


class InvalidSettings(SettingsError):
    """Il contenuto non supera la validazione dello schema."""


# ─────────────────────────────────────────────────────────────────────────────
# Schema — SPEC §8, esteso con le chiavi presenti in config/settings.toml
# ─────────────────────────────────────────────────────────────────────────────


class _Strict(BaseModel):
    """`extra="forbid"` ovunque.

    Una chiave sconosciuta in `settings.toml` e' quasi sempre un refuso, e un
    refuso accettato in silenzio produce un'impostazione che l'utente crede
    attiva e non lo e'. Meglio un errore all'avvio.
    """

    model_config = ConfigDict(extra="forbid")


class WakePhrase(_Strict):
    """Una frase-comando riconosciuta in locale da Vosk (SPEC §7.2)."""

    say: str = Field(min_length=1)
    action: str = Field(min_length=1)


class WakeSettings(_Strict):
    model: Path
    confirm_tone_ms: int = Field(ge=0, le=1000)
    log_triggers: bool = True
    phrases: list[WakePhrase] = Field(default_factory=list)

    _expand = field_validator("model")(lambda v: Path(v).expanduser())


class VoiceSettings(_Strict):
    #: Fase 9. **Predefinito FALSE, ed e' deliberato**: con la composizione
    #: unica di §3.2 il core, appena parte, aprirebbe il microfono e spawnerebbe
    #: un processo `claude`. Un servizio che accende il microfono perche' e'
    #: stato installato sarebbe la peggiore sorpresa dell'intero progetto.
    #: Si accende scrivendolo, e allora e' una decisione scritta.
    enabled: bool = False

    stt_provider: Literal["deepgram", "local"]
    tts_provider: Literal["deepgram", "local"]
    fallback_on_error: bool
    fallback_stt: Literal["local"]
    fallback_tts: Literal["local"]
    deepgram_stt_model: str
    eot_threshold: float = Field(ge=0.0, le=1.0)

    #: SPEC §8: `true` costa il 50-70% di chiamate LLM in piu'. Resta
    #: configurabile, ma il costo e' scritto accanto al campo.
    eager_eot: bool = False

    whisper_model: str = "base"
    kokoro_voice: str = "bm_george"
    wake: WakeSettings


class LLMSettings(_Strict):
    #: Invariante 11: nessun modello LLM locale. Lo schema lo impone.
    backend: Literal["claude_code"]

    t1_model: str
    t1_cwd: Path
    t2_model: str
    max_concurrent_t2: int = Field(ge=1)

    #: Presenti in config/settings.toml, assenti in SPEC §8. Dove i due
    #: divergono vince il file spedito, che e' quello che gira.
    t1_persona: Path | None = None
    max_t2_spawns_per_hour: int = Field(default=15, ge=1)

    @field_validator("t1_cwd", "t1_persona")
    @classmethod
    def _expand(cls, v: Path | None) -> Path | None:
        return Path(v).expanduser() if v is not None else None


class FSSettings(_Strict):
    workspace: Path
    allowed_roots: list[Path] = Field(min_length=1)

    #: Invariante 4: solo cestino, mai delete permanente. `false` non e' una
    #: configurazione valida, e' la disattivazione di un invariante.
    trash_only: Literal[True]

    @field_validator("workspace")
    @classmethod
    def _expand_one(cls, v: Path) -> Path:
        return Path(v).expanduser()

    @field_validator("allowed_roots")
    @classmethod
    def _expand_many(cls, v: list[Path]) -> list[Path]:
        return [Path(p).expanduser() for p in v]


class VisionSettings(_Strict):
    enabled: bool
    #: SPEC §12: deciso, ARGUS vede solo la finestra di JARVIS.
    scope: Literal["app"]
    engine: Literal["tesseract"]


class NewsSettings(_Strict):
    enabled: bool
    max_interruptions_per_hour: int = Field(ge=0)
    topic_ttl_minutes: int = Field(ge=1)


class CodeSettings(_Strict):
    """I tetti del tool che esegue codice generato (ADR-008, `tools/code.py`).

    Sono **politica**, non parametri: l'LLM chiede un timeout, questi decidono
    quanto puo' ottenere. Un tetto che il chiamante puo' alzare non e' un
    tetto.
    """

    #: **Predefinito FALSE**, come `voice`, `vision` e la Fase 9.
    #:
    #: Non e' prudenza generica: e' l'unico posto del sistema in cui gira
    #: qualcosa che ha scritto un LLM. Con `false` il tool non viene REGISTRATO
    #: — non esiste nell'allowlist, quindi non e' un tool che fallisce ma un
    #: tool che non c'e', e non compare nemmeno nell'elenco che l'LLM riceve.
    #:
    #: ⚠️ Le impostazioni si ricaricano a caldo, la composizione no: cambiare
    #: questo campo ha effetto al riavvio del core. E' la stessa asimmetria
    #: trovata in §13 con le categorie del file manager.
    enabled: bool = False

    #: La directory di lavoro dentro la sandbox. E' RAM: piccola di proposito.
    tmpfs_mb: int = Field(default=64, ge=1, le=1024)

    #: Il tetto di memoria del cgroup, `MemoryMax` (ADR-009).
    #:
    #: Il timeout limita il TEMPO, e non serve a niente qui: misurato, 2 GiB
    #: si allocano in **0,49 s**, molto prima che qualunque timeout scatti.
    #: Su una APU a memoria unificata l'OOM killer del kernel puo' prendersi il
    #: core di JARVIS o la sessione desktop invece del processo isolato.
    memory_mb: int = Field(default=512, ge=32, le=8192)

    #: `CPUQuota`, in percentuale di UN core. 50 = mezzo core.
    #:
    #: `while True: pass` viene ucciso dal timeout, ma per quei secondi occupa
    #: un core intero. Misurato: con 25% il ciclo fa esattamente un quarto dei
    #: giri. Arriva gratis col cgroup che serviva per la memoria.
    cpu_percent: int = Field(default=50, ge=1, le=400)

    #: Quanto stdout torna nel contesto dell'LLM. Un programma che stampa in un
    #: ciclo produce centinaia di MB, e li produrrebbe dentro un prompt.
    max_output_kb: int = Field(default=64, ge=1, le=4096)
    #: Il tetto al timeout richiesto. Il parametro del tool e' un desiderio.
    max_timeout_s: float = Field(default=10.0, gt=0.0, le=120.0)
    #: Quante esecuzioni insieme. ADR-008 ha provato UN processo per volta.
    max_concurrent: int = Field(default=2, ge=1, le=16)

    #: Quanto deve avanzare a interprete e stack sopra la tmpfs di lavoro.
    #: Misurato: CPython nudo in quel profilo occupa 7 MiB, un programma
    #: onesto che serializza 50.000 record ne tocca 31 al picco.
    MARGINE_MB: ClassVar[int] = 64

    @model_validator(mode="after")
    def _la_memoria_deve_stare_sopra_la_tmpfs(self) -> "CodeSettings":
        """⚠️ **Le pagine della tmpfs pesano sullo stesso `MemoryMax`.**

        Non e' dedotto: misurato. Con `memory_mb = 32` e `tmpfs_mb = 64`,
        scrivere 48 MiB in `/lavoro` fa uccidere il processo dal kernel — e il
        codice riceverebbe «limite di memoria superato» per aver usato lo
        spazio di lavoro che gli abbiamo dato.

        Una configurazione cosi' non e' stretta, e' rotta: meglio non partire.
        """
        minimo = self.tmpfs_mb + self.MARGINE_MB
        if self.memory_mb < minimo:
            raise ValueError(
                f"code.memory_mb = {self.memory_mb} non basta: la tmpfs di "
                f"lavoro ({self.tmpfs_mb} MB) pesa sullo STESSO tetto del "
                f"cgroup, e all'interprete serve margine. Minimo {minimo}"
            )
        return self


#: La griglia su cui sono dichiarate le celle delle scene.
#:
#: ⚠️ **E' una copia**: l'originale sta in `ui/src/desk/moduli.js`, che e' il
#: posto giusto perche' e' il renderer a trasformare celle in pixel. Il core
#: la ripete per poter RIFIUTARE una cella impossibile invece di lasciarla
#: arrivare a schermo — una scena che dichiara la colonna 40 e' un errore di
#: chi l'ha scritta, e va visto quando si salva, non quando si guarda.
#:
#: Un test lega i due numeri: due griglie che divergono comporrebbero due
#: scrivanie diverse dalla stessa dichiarazione.
COLONNE = 12
RIGHE = 4


class ScenaPannello(_Strict):
    """Un pannello dentro una scena: quale, dove, e sopra a chi.

    `cella` e' `[colonna, riga, colonne, righe]`, come in `moduli.js`. Non
    pixel: cosi' la stessa scena compone uno schermo qualunque, ed e' la
    ragione per cui §26.6 le scrive in celle.

    ⚠️ **`id` non viene validato contro i moduli esistenti.** Il core non
    conosce `moduli.js` e non deve: e' interfaccia. Un id sconosciuto lo
    IGNORA il renderer, con la stessa regola con cui ignora un pannello tolto
    dal codice — un ambiente che non parte perche' una scena nomina una
    finestra che non c'e' piu' sarebbe rotto dal proprio passato.
    """

    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    cella: tuple[int, int, int, int]
    #: L'ordine di sovrapposizione DENTRO la scena. §26.6: le celle si
    #: sovrappongono di proposito, quindi chi sta sopra va detto.
    z: int = Field(default=0, ge=0, le=999)

    @model_validator(mode="after")
    def _la_cella_sta_nella_griglia(self) -> "ScenaPannello":
        c, r, dc, dr = self.cella
        if dc < 1 or dr < 1:
            raise ValueError(f"cella {list(self.cella)}: larghezza e altezza >= 1")
        if c < 0 or r < 0 or c + dc > COLONNE or r + dr > RIGHE:
            raise ValueError(
                f"cella {list(self.cella)} fuori dalla griglia {COLONNE}x{RIGHE}"
            )
        return self


class Scena(_Strict):
    """§26.6 — un nome, un insieme di pannelli, e per ognuno una geometria.

    ## Perche' sta in `settings.toml` e il layout no

    Sono due cose opposte, ed e' la stessa distinzione di `core/layout.py`.
    Una scena e' **intenzione umana**: qualcuno ha deciso che «briefing»
    significa news, telemetria e mesh disposti cosi', e accanto ci scrive
    perche'. Il layout e' **stato della macchina**, cambia a ogni finestra
    spostata, e nessuno lo legge per capire una decisione.

    ## Il limite, dichiarato qui perche' e' dove si scivola

    §26.6: **JARVIS richiama scene DICHIARATE, non ne inventa.** Non calcola
    una disposizione e non decide che cosa sia importante. La liberta' di
    comporre a piacere vorrebbe dire che il renderer esegue una geometria
    prodotta da un LLM, e ADR-006 dice che il codice generato non tocca
    l'ambiente.
    """

    nome: str = Field(min_length=1, max_length=64,
                      pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    descrizione: str = Field(default="", max_length=200)
    pannelli: list[ScenaPannello] = Field(min_length=1, max_length=32)


class MeteoSettings(_Strict):
    """§26 — la sorgente del pannello meteo.

    ## Perche' le coordinate stanno QUI e non fra gli argomenti del tool

    Stessa ragione di `timezones`, che non ha un parametro `path`: un LLM che
    potesse scegliere la latitudine userebbe il tool per interrogare un
    servizio esterno con dati suoi. Cosi' l'unica cosa che puo' chiedere e' il
    tempo **del posto in cui sta l'utente**.

    ## Perche' non c'e' una posizione predefinita

    Nessun default: senza `latitude` e `longitude` il tool **non si registra**,
    quindi la prima chiamata di rete di questo sottosistema avviene solo dopo
    che un umano ha scritto due numeri qui dentro. Un valore predefinito —
    Roma, Greenwich, qualunque — sarebbe un dato inventato che sembra vero, e
    l'invariante 23 lo vieta: il pannello mostrerebbe il tempo di un posto in
    cui non sei.
    """

    enabled: bool = True
    #: Gradi decimali. `None` = nessuna posizione, quindi nessuna rete.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    #: L'etichetta che il pannello mostra. Viene da QUI e non dall'API: e'
    #: l'unico modo perche' nel DOM non finisca testo di terzi (invariante 5).
    nome: str = Field(default="", max_length=64)
    units: Literal["celsius", "fahrenheit"] = "celsius"

    @model_validator(mode="after")
    def _le_coordinate_vanno_in_coppia(self) -> "MeteoSettings":
        """Una sola delle due e' quasi sempre un errore di battitura, e in
        silenzio darebbe un pannello vuoto senza dire perche'."""
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "meteo.latitude e meteo.longitude vanno impostate insieme: "
                "una sola delle due non individua nessun posto"
            )
        return self


class UISettings(_Strict):
    target_fps: int = Field(ge=1)
    grid_px: int = Field(ge=1)
    gap_px: int = Field(ge=0)
    #: §26.6. Predefinito vuoto: una configurazione scritta prima che questa
    #: sezione esistesse non deve impedire l'avvio.
    scene: list[Scena] = Field(default_factory=list, max_length=32)
    #: Quale scena compone la scrivania al primo avvio, quando non c'e' un
    #: layout salvato da rimettere.
    #:
    #: ⚠️ Senza, la scrivania si compone da sola aprendo TUTTO — ed e' come si
    #: e' scoperto che «aprire tutto» non e' una composizione: quattordici
    #: pannelli disposti su quattro piastrellature complete della stessa
    #: griglia diventano una CASCATA, e di quattordici se ne leggono due.
    #: Il problema non erano le quattro pagine di ADR-010: era che niente
    #: componeva.
    scena_iniziale: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _la_scena_iniziale_esiste(self) -> "UISettings":
        """Un nome che non trova una scena e' un errore di configurazione, e va
        visto adesso: al primo avvio si vedrebbe soltanto una scrivania vuota,
        e nessuno collegherebbe le due cose."""
        if self.scena_iniziale is None:
            return self
        nomi = {s.nome for s in self.scene}
        if self.scena_iniziale not in nomi:
            raise ValueError(
                f"ui.scena_iniziale = {self.scena_iniziale!r} non e' fra le "
                f"scene dichiarate: {sorted(nomi) or 'nessuna'}"
            )
        return self

    def scena(self, nome: str) -> Scena | None:
        for s in self.scene:
            if s.nome == nome:
                return s
        return None


class Secrets(_Strict):
    """Chiavi API. Ogni campo e' `SecretStr`: non compare in `repr()`.

    Una chiave vuota e' legittima e non e' un errore: SPEC §8 prevede che
    senza `deepgram_api_key` JARVIS parta in locale e lo annunci.
    """

    deepgram_api_key: SecretStr = SecretStr("")
    guardian_api_key: SecretStr = SecretStr("")
    youtube_api_key: SecretStr = SecretStr("")

    def present(self) -> set[str]:
        """Nomi delle chiavi effettivamente valorizzate. Non i valori."""
        return {
            name
            for name in type(self).model_fields
            if getattr(self, name).get_secret_value()
        }


class McpToolPromosso(_Strict):
    """Un tool che un umano ha NOMINATO. ADR-007 decisione 1.

    `side_effect` sta qui e non nell'annuncio del server: un terzo non ha
    titolo per dichiarare innocua la propria operazione, e se lo avesse
    basterebbe mentire una volta per saltare la conferma di §6.2.
    """

    tool: str = Field(min_length=1, max_length=64)
    side_effect: bool = False


class McpServer(_Strict):
    """Un server MCP da montare. ADR-007."""

    nome: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    #: Il comando, gia' spezzato. Una stringa sola andrebbe passata a una
    #: shell, e una shell in mezzo e' un modo di eseguire cio' che non si e'
    #: scritto — «Non fare senza chiedere: eseguire stringhe generate».
    comando: list[str] = Field(min_length=1, max_length=16)
    #: SOLO questi diventano invocabili. Vuoto vuol dire: il server si monta,
    #: si guarda cosa propone, e non se ne usa niente. E' uno stato utile.
    promossi: list[McpToolPromosso] = Field(default_factory=list, max_length=32)


class McpSettings(_Strict):
    """§ADR-007. Parte SPENTO, come voce, codice e vision.

    Montare un server MCP vuol dire avviare **un programma di terzi** e mettere
    dei suoi tool a portata dell'LLM. E' la stessa specie di decisione di
    `voice.enabled` e `code.enabled`, e si prende nello stesso modo: scrivendo
    nel file, non cliccando una casella.
    """

    enabled: bool = False
    servers: list[McpServer] = Field(default_factory=list, max_length=8)


class Settings(_Strict):
    voice: VoiceSettings
    llm: LLMSettings
    fs: FSSettings
    vision: VisionSettings
    news: NewsSettings
    ui: UISettings
    #: Con valori predefiniti, come `code`: una configurazione scritta prima
    #: che questa sezione esistesse non deve impedire l'avvio. Senza
    #: coordinate resta inerte e non tocca la rete.
    meteo: MeteoSettings = Field(default_factory=MeteoSettings)
    #: Con valori predefiniti: una configurazione scritta prima che questa
    #: sezione esistesse non deve impedire l'avvio, e i predefiniti sono i
    #: piu' stretti fra quelli utili.
    code: CodeSettings = Field(default_factory=CodeSettings)
    #: Con valori predefiniti, come `code` e `meteo`: una configurazione
    #: scritta prima che questa sezione esistesse non deve impedire l'avvio.
    mcp: McpSettings = Field(default_factory=McpSettings)
    secrets: Secrets = Field(default_factory=Secrets)


# ─────────────────────────────────────────────────────────────────────────────
# Redazione nei log — invariante «le chiavi API MAI nei log»
# ─────────────────────────────────────────────────────────────────────────────


class SecretRegistry:
    """Valori da oscurare in qualunque log.

    `SecretStr` protegge `repr()` e `str()`, ma non protegge nulla dopo una
    chiamata a `get_secret_value()`: da li' in poi e' una stringa qualunque e
    puo' finire in un log per distrazione. Questo registro chiude quel varco.

    Le stringhe vuote non si registrano mai: oscurare `""` significherebbe
    inserire il marcatore fra ogni coppia di caratteri di ogni messaggio.
    """

    MASK = "***REDACTED***"

    def __init__(self) -> None:
        self._values: set[str] = set()
        self._lock = threading.Lock()

    def register(self, *values: str) -> None:
        with self._lock:
            self._values.update(v for v in values if v)

    def register_secrets(self, secrets: Secrets) -> None:
        self.register(
            *(
                getattr(secrets, name).get_secret_value()
                for name in type(secrets).model_fields
            )
        )

    def clear(self) -> None:
        with self._lock:
            self._values.clear()

    def scrub(self, text: str) -> str:
        with self._lock:
            values = tuple(self._values)
        for secret in values:
            text = text.replace(secret, self.MASK)
        return text


SECRETS = SecretRegistry()


def redact_secrets(_logger: Any, _name: str, event_dict: dict) -> dict:
    """Processore structlog: oscura ogni valore di segreto noto.

    Va inserito **prima** del renderer, altrimenti agisce su una riga gia'
    formattata e perde le chiavi annidate nei valori strutturati.
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = SECRETS.scrub(value)
        elif isinstance(value, SecretStr):
            event_dict[key] = SecretRegistry.MASK
    return event_dict


# ─────────────────────────────────────────────────────────────────────────────
# Caricamento
# ─────────────────────────────────────────────────────────────────────────────


def _read_toml(path: Path) -> dict:
    try:
        return tomlkit.parse(path.read_text(encoding="utf-8")).unwrap()
    except OSError as exc:
        raise MissingSettingsFile(f"{path} non leggibile: {exc}") from exc
    except Exception as exc:                      # errore di sintassi TOML
        raise InvalidSettings(f"{path} non e' TOML valido: {exc}") from exc


def load_settings(paths: Paths | None = None) -> Settings:
    """Carica e valida `settings.toml` + `secrets.toml` da `Paths.config_dir()`.

    Il `config/` del repository e' un **template**, non la sorgente: il file
    che gira e' quello in `~/.config/jarvis-os/` (SPEC §8, INSTALLA.md §3).
    """
    p = paths or platform_paths()
    config_dir = p.config_dir()
    settings_file = config_dir / SETTINGS_FILENAME
    secrets_file = config_dir / SECRETS_FILENAME

    if not settings_file.exists():
        raise MissingSettingsFile(
            f"{settings_file} non esiste. INSTALLA.md §3: copiare "
            f"config/{SETTINGS_FILENAME} in {config_dir} e dargli permessi 0600."
        )

    if not p.is_private(settings_file):
        log.warning(
            "permessi_larghi",
            file=str(settings_file),
            atteso="0600",
            azione="proseguo",
        )

    raw: dict = _read_toml(settings_file)

    if secrets_file.exists():
        if not p.is_private(secrets_file):
            raise InsecurePermissions(
                f"{secrets_file} e' leggibile oltre il proprietario. Una chiave "
                f"esposta va considerata compromessa: `chmod 600 {secrets_file}` "
                f"e, se il sistema e' condiviso, ruotare le chiavi."
            )
        raw["secrets"] = _read_toml(secrets_file)
    else:
        log.warning(
            "secrets_assenti",
            file=str(secrets_file),
            conseguenza="JARVIS partira' con i provider locali (SPEC §8)",
        )

    try:
        settings = Settings.model_validate(raw)
    except Exception as exc:
        raise InvalidSettings(str(exc)) from exc

    SECRETS.register_secrets(settings.secrets)
    log.info(
        "settings_caricate",
        config_dir=str(config_dir),
        chiavi_presenti=sorted(settings.secrets.present()),   # i NOMI, non i valori
    )
    return settings


# ─────────────────────────────────────────────────────────────────────────────
# Ricarica a caldo
# ─────────────────────────────────────────────────────────────────────────────

Listener = Callable[[Settings], None]
ErrorListener = Callable[[SettingsError], None]


class _ChangeHandler(FileSystemEventHandler):
    """Traduce gli eventi del filesystem in un solo segnale, con antirimbalzo.

    Serve intercettare `modified`, `created` **e** `moved`: molti editor
    salvano scrivendo un temporaneo e rinominandolo sopra l'originale, e in
    quel caso `modified` non arriva mai. Un watcher che ascolta solo
    `modified` funziona con `echo >>` e non funziona con un editor vero.
    """

    def __init__(self, filenames: set[str], on_change: Callable[[], None],
                 debounce_s: float) -> None:
        self._filenames = filenames
        self._on_change = on_change
        self._debounce_s = debounce_s
        self._last = 0.0

    def _touches_us(self, event: FileSystemEvent) -> bool:
        candidates = [event.src_path, getattr(event, "dest_path", "")]
        return any(Path(str(c)).name in self._filenames for c in candidates if c)

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory or not self._touches_us(event):
            return
        now = time.monotonic()
        if now - self._last < self._debounce_s:
            return
        self._last = now
        self._on_change()


class SettingsStore:
    """Le impostazioni correnti, e chi vuole sapere quando cambiano.

    **Su ricarica non valida le impostazioni precedenti restano attive.** Un
    refuso in `settings.toml` non deve azzittire JARVIS mentre e' in esercizio:
    l'errore va annunciato (SPEC §16) e la configurazione buona va tenuta.
    Questo vale solo per la RIcarica — al primo caricamento un file invalido
    e' un errore fatale, perche' non c'e' nulla di buono da conservare.
    """

    def __init__(self, paths: Paths | None = None, debounce_s: float = 0.2) -> None:
        self._paths = paths or platform_paths()
        self._debounce_s = debounce_s
        self._listeners: list[Listener] = []
        self._error_listeners: list[ErrorListener] = []
        self._observer: Observer | None = None
        self._current: Settings = load_settings(self._paths)

    @property
    def current(self) -> Settings:
        return self._current

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        """Registra un ascoltatore. Ritorna la funzione per disiscriverlo."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def subscribe_errors(self, listener: ErrorListener) -> Callable[[], None]:
        self._error_listeners.append(listener)
        return lambda: self._error_listeners.remove(listener)

    def reload(self) -> bool:
        """Ricarica da disco. `True` se le impostazioni sono cambiate."""
        try:
            fresh = load_settings(self._paths)
        except SettingsError as exc:
            log.error("ricarica_fallita", errore=str(exc), azione="mantengo le precedenti")
            for listener in list(self._error_listeners):
                listener(exc)
            return False

        if fresh == self._current:
            return False

        self._current = fresh
        log.info("settings_ricaricate")
        for listener in list(self._listeners):
            listener(fresh)
        return True

    def start(self) -> None:
        """Avvia la sorveglianza di `config_dir()`.

        ⚠️ `Observer.start()` ritorna prima che il watch inotify sia
        effettivamente attivo: c'e' una finestra di pochi millisecondi in cui
        una modifica non genera evento. In esercizio e' benigna — il file e'
        appena stato letto dal costruttore — ma va saputa da chi scrive test
        su questo percorso.
        """
        if self._observer is not None:
            return
        handler = _ChangeHandler(
            {SETTINGS_FILENAME, SECRETS_FILENAME}, self.reload, self._debounce_s
        )
        observer = Observer()
        observer.schedule(handler, str(self._paths.config_dir()), recursive=False)
        observer.start()
        self._observer = observer
        log.info("sorveglianza_avviata", dir=str(self._paths.config_dir()))

    def stop(self) -> None:
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None
        log.info("sorveglianza_fermata")

    def __enter__(self) -> SettingsStore:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()
