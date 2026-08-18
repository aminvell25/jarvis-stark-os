"""core/settings — SPEC §8."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from core.settings import (
    InsecurePermissions,
    InvalidSettings,
    MissingSettingsFile,
    Settings,
    SettingsStore,
    load_settings,
)
from tests.conftest import FakePaths


def _edit(paths: FakePaths, cerca: str, sostituisci: str) -> None:
    f = paths.config_dir() / "settings.toml"
    testo = f.read_text(encoding="utf-8")
    assert cerca in testo, f"ancora {cerca!r} assente da settings.toml"
    f.write_text(testo.replace(cerca, sostituisci), encoding="utf-8")


class TestCaricamento:
    def test_carica_il_settings_toml_spedito(self, paths: FakePaths) -> None:
        s = load_settings(paths)
        assert isinstance(s, Settings)
        assert s.voice.stt_provider == "deepgram"
        assert s.llm.backend == "claude_code"
        assert s.ui.grid_px == 110

    def test_espande_la_tilde(self, paths: FakePaths) -> None:
        s = load_settings(paths)
        for p in [s.fs.workspace, s.llm.t1_cwd, s.voice.wake.model, *s.fs.allowed_roots]:
            assert "~" not in str(p), f"tilde non espansa in {p}"
            assert p.is_absolute()

    def test_legge_le_frasi_wake(self, paths: FakePaths) -> None:
        frasi = {p.say: p.action for p in load_settings(paths).voice.wake.phrases}
        assert frasi["papa e a casa"] == "scene:welcome_home"

    def test_settings_mancante_e_fatale(self, paths: FakePaths) -> None:
        (paths.config_dir() / "settings.toml").unlink()
        with pytest.raises(MissingSettingsFile, match="INSTALLA.md"):
            load_settings(paths)

    def test_secrets_mancante_non_e_fatale(self, paths: FakePaths) -> None:
        """SPEC §8: senza chiave Deepgram JARVIS parte in locale e lo annuncia.
        Non e' un errore, e' una degradazione prevista."""
        (paths.config_dir() / "secrets.toml").unlink()
        s = load_settings(paths)
        assert s.secrets.present() == set()

    def test_toml_malformato(self, paths: FakePaths) -> None:
        (paths.config_dir() / "settings.toml").write_text("[voice\n", encoding="utf-8")
        with pytest.raises(InvalidSettings):
            load_settings(paths)


class TestValidazione:
    def test_chiave_sconosciuta_e_errore(self, paths: FakePaths) -> None:
        """Un refuso accettato in silenzio produce un'impostazione che l'utente
        crede attiva e non lo e'."""
        _edit(paths, "[llm]", "[llm]\nt1_modle = \"typo\"")
        with pytest.raises(InvalidSettings, match="t1_modle"):
            load_settings(paths)

    def test_tipo_errato(self, paths: FakePaths) -> None:
        _edit(paths, "eot_threshold = 0.7", 'eot_threshold = "molto"')
        with pytest.raises(InvalidSettings, match="eot_threshold"):
            load_settings(paths)

    def test_valore_fuori_intervallo(self, paths: FakePaths) -> None:
        _edit(paths, "eot_threshold = 0.7", "eot_threshold = 1.4")
        with pytest.raises(InvalidSettings, match="eot_threshold"):
            load_settings(paths)

    def test_trash_only_false_e_respinto(self, paths: FakePaths) -> None:
        """Invariante 4: solo cestino, mai delete permanente. `false` non e' una
        configurazione, e' la disattivazione di un invariante — e va impedita
        dallo schema, non dalla buona volonta'."""
        _edit(paths, "trash_only = true", "trash_only = false")
        with pytest.raises(InvalidSettings, match="trash_only"):
            load_settings(paths)

    def test_backend_locale_e_respinto(self, paths: FakePaths) -> None:
        """Invariante 11: nessun modello LLM locale."""
        _edit(paths, 'backend = "claude_code"', 'backend = "ollama"')
        with pytest.raises(InvalidSettings, match="backend"):
            load_settings(paths)

    def test_scope_oltre_la_finestra_e_respinto(self, paths: FakePaths) -> None:
        """SPEC §12: ARGUS vede solo la finestra di JARVIS."""
        _edit(paths, 'scope = "app"', 'scope = "screen"')
        with pytest.raises(InvalidSettings, match="scope"):
            load_settings(paths)


class TestPermessi:
    def test_secrets_leggibile_da_altri_e_rifiutato(self, paths: FakePaths) -> None:
        """Una chiave esposta va considerata compromessa: proseguire
        significherebbe usarla sapendolo."""
        (paths.config_dir() / "secrets.toml").chmod(0o644)
        with pytest.raises(InsecurePermissions, match="compromessa"):
            load_settings(paths)

    def test_settings_leggibile_da_altri_avvisa_ma_prosegue(
        self, paths: FakePaths
    ) -> None:
        """Asimmetria voluta: un settings.toml leggibile e' sciatteria, non una
        compromissione."""
        (paths.config_dir() / "settings.toml").chmod(0o644)
        assert load_settings(paths).ui.target_fps == 60


class TestRicaricaACaldo:
    def test_emette_evento_sul_cambio(self, paths: FakePaths) -> None:
        visto = threading.Event()
        ricevute: list[Settings] = []

        store = SettingsStore(paths, debounce_s=0.01)
        store.subscribe(lambda s: (ricevute.append(s), visto.set()))
        assert store.current.ui.target_fps == 60

        with store:
            _edit(paths, "target_fps = 60", "target_fps = 30")
            assert visto.wait(timeout=10), "nessun evento entro 10 s"

        assert ricevute[-1].ui.target_fps == 30
        assert store.current.ui.target_fps == 30

    def test_ricarica_invalida_conserva_le_precedenti(self, paths: FakePaths) -> None:
        """Un refuso in settings.toml non deve azzittire JARVIS in esercizio:
        l'errore si annuncia (SPEC §16) e la configurazione buona si tiene."""
        store = SettingsStore(paths, debounce_s=0.01)
        errori: list[Exception] = []
        store.subscribe_errors(errori.append)

        (paths.config_dir() / "settings.toml").write_text("[voice\n", encoding="utf-8")
        assert store.reload() is False
        assert store.current.ui.target_fps == 60      # la buona e' ancora attiva
        assert len(errori) == 1

    def test_ricarica_identica_non_emette(self, paths: FakePaths) -> None:
        store = SettingsStore(paths, debounce_s=0.01)
        chiamate: list[Settings] = []
        store.subscribe(chiamate.append)
        assert store.reload() is False
        assert chiamate == []

    def test_stop_e_idempotente(self, paths: FakePaths) -> None:
        store = SettingsStore(paths, debounce_s=0.01)
        store.start()
        store.stop()
        store.stop()
