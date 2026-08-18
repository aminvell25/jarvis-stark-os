"""core/platform — SPEC §23, invariante 29."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.platform import (
    gpu as platform_gpu,
    paths as platform_paths,
    sandbox_runner as platform_sandbox,
    sensors as platform_sensors,
)
from core.platform.base import (
    RUNTIME_DIR_MODE,
    AudioIO,
    Gpu,
    Paths,
    SandboxRunner,
    Sensors,
)
from core.platform.linux import LinuxAudioIO, LinuxGpu, LinuxPaths, LinuxSensors
from core.platform.linux_sandbox import LinuxSandboxRunner


class TestLinuxPaths:
    def test_rispetta_le_variabili_xdg(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "dat"))
        p = LinuxPaths()
        assert p.config_dir() == tmp_path / "cfg" / "jarvis-os"
        assert p.data_dir() == tmp_path / "dat" / "jarvis-os"

    def test_ricade_su_xdg_di_default(self, monkeypatch) -> None:
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        p = LinuxPaths()
        assert p.config_dir() == Path.home() / ".config" / "jarvis-os"
        assert p.data_dir() == Path.home() / ".local" / "share" / "jarvis-os"

    def test_ignora_le_variabili_xdg_relative(self, monkeypatch) -> None:
        """La specifica XDG impone di trattare un path relativo come assente.

        Senza questo controllo un `XDG_CONFIG_HOME=.config` malposto verrebbe
        risolto rispetto alla working directory: per T1 e' `voice-cwd`, che
        SPEC §5.2 vuole vuota.
        """
        monkeypatch.setenv("XDG_CONFIG_HOME", ".config")
        assert LinuxPaths().config_dir() == Path.home() / ".config" / "jarvis-os"

    def test_socket_dentro_runtime_dir(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        p = LinuxPaths()
        assert p.runtime_dir() == tmp_path / "jarvis-os"
        assert p.socket_path().parent == p.runtime_dir()
        assert p.socket_path().name == "core.sock"

    def test_runtime_dir_ricade_e_resta_assoluta(self, monkeypatch) -> None:
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        fallback = LinuxPaths().runtime_dir()
        assert fallback.is_absolute()
        assert "jarvis-os" in fallback.name

    def test_modo_della_runtime_dir_e_privato(self) -> None:
        """La sede del socket e' il confine di sicurezza fra core ed Electron
        (vedi `base.Paths.socket_path`): 0700 non e' negoziabile."""
        assert RUNTIME_DIR_MODE == 0o700

    @pytest.mark.parametrize(
        "mode, atteso",
        [(0o600, True), (0o400, True), (0o640, False), (0o604, False), (0o666, False)],
    )
    def test_is_private(self, tmp_path: Path, mode: int, atteso: bool) -> None:
        f = tmp_path / "x.toml"
        f.write_text("a = 1", encoding="utf-8")
        f.chmod(mode)
        assert LinuxPaths().is_private(f) is atteso


class TestLinuxSensors:
    def test_temperatura_e_float_o_none(self) -> None:
        t = LinuxSensors().package_temp()
        assert t is None or isinstance(t, float)

    def test_none_non_e_un_errore(self, monkeypatch) -> None:
        """Su Windows psutil non espone le temperature: `None` e' l'esito
        previsto e la soglia termica di SPEC §16 semplicemente non scatta."""
        monkeypatch.setattr("psutil.sensors_temperatures", lambda: {})
        assert LinuxSensors().package_temp() is None


class TestStubNonImplementati:
    """L'audio appartiene alla Fase 3.

    Il punto del test non e' che sollevi: e' che NON restituisca un valore
    plausibile. Uno stub che ritorna silenzio farebbe credere alla Fase 3 che
    il microfono funzioni.

    La sandbox non e' piu' qui: implementata in Fase 1, vive in
    `core/platform/linux_sandbox.py` (invariante 29) e ha i suoi test in
    `test_sandbox_policy.py` e `test_sandbox_runner.py`.
    """

    async def test_audio_in_solleva(self) -> None:
        with pytest.raises(NotImplementedError, match="Fase 3"):
            await LinuxAudioIO().input_stream(16000)

    async def test_audio_out_solleva(self) -> None:
        with pytest.raises(NotImplementedError, match="Fase 3"):
            await LinuxAudioIO().play(b"", 16000)


class TestConformitaAiProtocol:
    def test_le_implementazioni_soddisfano_i_protocol(self) -> None:
        assert isinstance(LinuxPaths(), Paths)
        assert isinstance(LinuxSensors(), Sensors)
        assert isinstance(LinuxGpu(), Gpu)
        assert isinstance(LinuxSandboxRunner([]), SandboxRunner)
        assert isinstance(LinuxAudioIO(), AudioIO)

    def test_il_doppio_dei_test_soddisfa_il_protocol(self) -> None:
        """Il `Paths` e' cresciuto in Fase 2 con `trash_dir_for`, e il doppio
        dei test non l'ha seguito: il fallimento e' comparso a valle, dentro un
        tool, come `AttributeError`. Questo test lo fa comparire QUI, dove si
        capisce cos'e' successo."""
        from pathlib import Path as P
        from tests.conftest import FakePaths

        assert isinstance(FakePaths(P("/tmp")), Paths)

    def test_le_factory_scelgono_linux(self) -> None:
        assert isinstance(platform_paths(), LinuxPaths)
        assert isinstance(platform_sensors(), LinuxSensors)
        assert isinstance(platform_gpu(), LinuxGpu)
        assert isinstance(platform_sandbox([]), LinuxSandboxRunner)

    def test_nessuna_chiamata_di_piattaforma_fuori_da_platform(self) -> None:
        """L'invariante 29 alla lettera: «Mai `bwrap` o percorsi POSIX sparsi
        nel codice applicativo».

        E' il controllo che ha scoperto, in Fase 1, che `core/sandbox/policy.py`
        nominava bwrap: §21.1 mette `core/sandbox/` fuori da `platform/`, ma
        §23 dice che su Windows la sandbox e' un'implementazione diversa. Le
        due sezioni confliggono e l'invariante vince.

        Guarda il CODICE, non il testo. Commenti e docstring che *spiegano* la
        regola nominano per forza cio' che vieta — `$XDG_RUNTIME_DIR` compare
        nel docstring di `paths_cli` proprio per dire perche' quel modulo
        esiste. Un controllo che scatta sulla propria spiegazione viene
        allentato al primo falso positivo, e da li' non protegge piu' nulla.
        """
        import io
        import re
        import tokenize
        from pathlib import Path as P

        VIETATI = re.compile(
            r"\b(bwrap|psutil|XDG_[A-Z_]+|sensors_temperatures|st_mode)\b|/proc/",
            re.IGNORECASE,
        )

        def codice_senza_prosa(testo: str) -> str:
            fuori = []
            for tok in tokenize.generate_tokens(io.StringIO(testo).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                fuori.append(tok.string)
            return " ".join(fuori)

        radice = P(__file__).resolve().parent.parent / "core"
        colpevoli = [
            str(f.relative_to(radice.parent))
            for f in radice.rglob("*.py")
            if not f.is_relative_to(radice / "platform")
            and VIETATI.search(codice_senza_prosa(f.read_text()))
        ]
        assert not colpevoli, (
            "chiamate di piattaforma fuori da core/platform/: " + ", ".join(colpevoli)
        )
