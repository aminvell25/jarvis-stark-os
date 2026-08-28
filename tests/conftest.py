"""Attrezzatura comune.

Principio: **nessun test tocca la configurazione reale dell'utente.** Ogni
prova costruisce la propria `config_dir` in una directory temporanea e la
consegna al codice attraverso un `Paths` finto. Se una suite dipende da
`~/.config/jarvis-os/`, passa o fallisce a seconda della macchina, e allora
non sta misurando il codice.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from core.platform.base import MemoryInfo, ProcessInfo

REPO = Path(__file__).resolve().parent.parent

SECRETS_TOML = """\
deepgram_api_key = "dg_chiave_di_prova_NON_REALE_9f3a"
guardian_api_key = ""
youtube_api_key  = ""
"""


class FakePaths:
    """`Paths` radicato in una directory temporanea."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def config_dir(self) -> Path:
        return self._root / "config"

    def data_dir(self) -> Path:
        return self._root / "data"

    def workspace(self) -> Path:
        return self._root / "JARVIS"

    def runtime_dir(self) -> Path:
        return self._root / "run"

    def socket_path(self) -> Path:
        return self.runtime_dir() / "core.sock"

    def is_private(self, path: Path) -> bool:
        return not (path.stat().st_mode & 0o077)

    def trash_dir_for(self, path: Path) -> Path | None:
        # Delega alla regola vera: i test cestinano file veri, e un cestino
        # finto direbbe che sono recuperabili senza che lo siano.
        from core.platform.linux import LinuxPaths

        return LinuxPaths().trash_dir_for(path)

    def find_trashed(self, original: Path) -> Path | None:
        from core.platform.linux import LinuxPaths

        return LinuxPaths().find_trashed(original)


@pytest.fixture
def paths(tmp_path: Path) -> FakePaths:
    """Config dir popolata col `config/settings.toml` REALE del repository.

    Usare il file spedito e non una copia ridotta significa che se qualcuno
    aggiunge una chiave al file di configurazione senza aggiungerla allo
    schema, i test lo scoprono subito: `extra="forbid"` la respinge.
    """
    p = FakePaths(tmp_path)
    p.config_dir().mkdir(parents=True)
    shutil.copy(REPO / "config" / "settings.toml", p.config_dir() / "settings.toml")
    (p.config_dir() / "secrets.toml").write_text(SECRETS_TOML, encoding="utf-8")
    for name in ("settings.toml", "secrets.toml"):
        (p.config_dir() / name).chmod(0o600)
    return p


@pytest.fixture(autouse=True)
def _clean_secret_registry():
    """Il registro dei segreti e' globale: va svuotato fra un test e l'altro,
    altrimenti una chiave registrata da un test oscura l'output di un altro e
    produce fallimenti che sembrano stregoneria."""
    from core.settings import SECRETS

    SECRETS.clear()
    yield
    SECRETS.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Attrezzatura per il socket e per la misura
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def short_paths():
    """`Paths` con radice CORTA, per i test che legano un socket UNIX.

    `tmp_path` di pytest produce percorsi come
    `/tmp/pytest-of-utente/pytest-42/test_un_nome_lungo0/`, e sommato a
    `run/core.sock` supera facilmente i 108 byte di `sun_path`. Il fallimento
    che ne segue — "AF_UNIX path too long" — non dice a nessuno cosa fare, e
    dipenderebbe dalla lunghezza del NOME del test: la specie peggiore di test
    fragile.
    """
    with tempfile.TemporaryDirectory(prefix="jt-") as d:
        root = Path(d)
        p = FakePaths(root)
        p.config_dir().mkdir(parents=True)
        shutil.copy(REPO / "config" / "settings.toml", p.config_dir() / "settings.toml")
        (p.config_dir() / "secrets.toml").write_text(SECRETS_TOML, encoding="utf-8")
        for name in ("settings.toml", "secrets.toml"):
            (p.config_dir() / name).chmod(0o600)
        yield p


class FakeSensors:
    """`Sensors` deterministico: i test misurano numeri scelti, non la macchina."""

    def __init__(self, cpu: float = 12.5, ram_percent: float = 40.0,
                 temp: float | None = 55.0, available: int = 8 * 2**30) -> None:
        self._cpu, self._ram, self._temp, self._avail = cpu, ram_percent, temp, available

    def cpu_percent(self) -> float:
        return self._cpu

    def memory(self) -> MemoryInfo:
        return MemoryInfo(total=16 * 2**30, available=self._avail, percent=self._ram)

    def top_processes(self, n: int = 3) -> list[ProcessInfo]:
        return [ProcessInfo(pid=1000 + i, name=f"proc{i}", cpu=90.0 - i)
                for i in range(n)]

    def package_temp(self) -> float | None:
        return self._temp


@pytest.fixture(autouse=True)
def _clean_registry():
    """Il registro dei tool e' globale: va svuotato fra un test e l'altro."""
    from core.tools import registry

    registry.clear()
    yield
    registry.clear()


class UscitaFinta:
    """Il flusso di riproduzione, per i finti. Registra ciò che gli arriva."""

    def __init__(self, scritti: list, rate: int) -> None:
        self.scritti = scritti
        self.rate = rate
        self.chiusa = False

    async def scrivi(self, pcm: bytes) -> None:
        self.scritti.append(pcm)

    async def chiudi(self) -> None:
        self.chiusa = True


class AudioFinto:
    """Un `AudioIO` finto **completo**.

    ⚠️ Esiste perché i finti dell'audio erano **tre**, ciascuno con la propria
    idea di che cosa sia un `AudioIO`, e nessuno implementava l'interfaccia
    intera. Aggiungendo `apri_uscita()` al Protocol si sono rotti tutti e tre
    insieme — che è il momento in cui si scopre che erano tre.

    Chi ne ha bisogno di uno diverso lo eredita e sovrascrive un metodo, invece
    di ricominciare da zero e dimenticarne uno.
    """

    def __init__(self, blocchi: list[bytes] | None = None) -> None:
        #: Ciò che è stato riprodotto, in ordine, comunque sia arrivato.
        self.riprodotti: list[bytes] = []
        self.aperture: list[int | None] = []
        self.uscite: list[UscitaFinta] = []
        self.interruzioni = 0
        self._blocchi = blocchi or []
        self._volume = 100

    def input_stream(self, sample_rate=None):
        self.aperture.append(sample_rate)

        async def gen():
            for b in self._blocchi:
                yield b

        return gen()

    async def play(self, pcm: bytes, sample_rate: int | None = None) -> None:
        self.riprodotti.append(pcm)

    async def apri_uscita(self, sample_rate: int = 16_000) -> UscitaFinta:
        u = UscitaFinta(self.riprodotti, sample_rate)
        self.uscite.append(u)
        return u

    async def interrupt(self) -> None:
        self.interruzioni += 1

    @property
    def volume(self) -> int:
        return self._volume

    def imposta_volume(self, livello: int) -> int:
        self._volume = max(0, min(100, int(livello)))
        return self._volume


def lettura_nota(**valori: bool):
    """Una `Lettura` in cui ogni campo dato è `noto`.

    ⚠️ Sta qui e non in `core/news/conoscibilita.py`: è una comodità per i
    test, e la scansione degli orfani l'ha trovata senza un solo chiamante in
    `core/` un minuto dopo che l'avevo scritta lì. Una comodità per i test
    scritta nel codice applicativo è un pezzo che sembra congiunto e non lo è.
    """
    from core.news.conoscibilita import NOTO, Lettura, Sguardo

    return Lettura({n: Sguardo(v, NOTO) for n, v in valori.items()})


async def da_pcm(dati, byte: int):
    """Sorgente da byte già in memoria: per le prove, senza un microfono.

    Serve a rendere provabile la catena `VAD → wake → T0` su audio registrato o
    sintetizzato, che è l'unico modo di verificarla finché §5 di
    `docs/acceptance/T0-E-IL-MICROFONO.md` resta aperto.

    Accetta anche un iterabile di pezzi, così un test può **riprodurre la
    granularità irregolare misurata**: `da_pcm([b"x"*42, b"x"*640, ...])`.

    ⚠️ Sta qui e non in `core/voice/audio_io.py`, dove è nata: i suoi unici
    chiamanti sono cinque righe di `tests/test_audio_io.py`, e una comodità per
    le prove scritta nel codice applicativo è un pezzo che sembra congiunto e
    non lo è. Stessa specie di `lettura_nota` qui sopra.
    """
    from core.voice.audio_io import a_blocchi

    async def uno():
        if isinstance(dati, (bytes, bytearray)):
            yield bytes(dati)
        else:
            for p in dati:
                yield bytes(p)

    async for b in a_blocchi(uno(), byte):
        yield b
