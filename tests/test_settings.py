"""core/settings — SPEC §8."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from watchdog.events import (FileClosedNoWriteEvent, FileModifiedEvent,
                             FileMovedEvent, FileOpenedEvent)

from core.settings import (
    _ChangeHandler,
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
        """⚠️ Si fissa la FORMA, non il valore.

        Prima qui c'era `== "scene:welcome_home"`, e ha bocciato il giorno in
        cui quella frase e' stata puntata su una scena che esiste davvero —
        una modifica legittima della configurazione, non una regressione. Un
        test che fissa il contenuto di `settings.toml` e' un test che rende
        rosso il cambiare idea; il precedente e' la riga 113 di `lettura.js`,
        fissata per numero e rotta da un import.

        Cio' che deve restare vero e' che le frasi si leggano e che a ognuna
        arrivi la sua azione. Che le scene nominate ESISTANO lo sorveglia
        `tests/test_voce_arriva_alla_scrivania.py`, che e' il posto giusto:
        li' c'e' l'altro lato del contratto.
        """
        frasi = {p.say: p.action for p in load_settings(paths).voice.wake.phrases}
        assert set(frasi) == {"jarvis", "papa e a casa", "jarvis buonanotte",
                              "jarvis silenzio"}
        assert frasi["jarvis"] == "listen"
        assert frasi["papa e a casa"].startswith("scene:")
        assert all(a for a in frasi.values()), f"un'azione vuota: {frasi}"

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
            # `observer.start()` ritorna prima che il watch inotify sia
            # attivo: sotto carico la prima scrittura puo' cadere in quella
            # finestra e non generare alcun evento. Si riscrive finche'
            # l'evento arriva, invece di sperare in un `sleep` tarato bene.
            _edit(paths, "target_fps = 60", "target_fps = 30")
            for _ in range(50):
                if visto.wait(timeout=0.2):
                    break
                _edit(paths, "target_fps = 30", "target_fps = 30")
            assert visto.is_set(), "nessun evento entro 10 s"

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


class TestUnaLetturaNonEUnCambio:
    """⚠️ Il difetto del 31 agosto 2026, e perche' nessun test lo vedeva.

    inotify manda `IN_OPEN` anche a chi apre il file per **leggerlo**, e
    l'antirimbalzo era sul fronte di salita: la lettura consumava la finestra e
    la scrittura che arrivava un millisecondo dopo veniva scartata.

    Colpiva esattamente la strada per cui il ricarico a caldo esiste, perche'
    `imposta_valore` **legge** il TOML (`_documento`) prima di riscriverlo:
    cambiare una frase di wake dalla pagina non la faceva mai arrivare al
    riconoscitore. Trovato provando il microfono vero, non da un test.

    `TestRicaricaACaldo::test_emette_evento_sul_cambio` non lo vedeva perche'
    riscrive lo stesso valore fino a cinquanta volte con `debounce_s=0.01`:
    prima o poi una scrittura cade fuori dalla finestra e l'evento passa. La
    ripetizione, che serviva a coprire la finestra fra `Observer.start()` e il
    watch attivo, copriva anche il difetto. Qui si scrive **una volta sola**.
    """

    def _attendi_sorveglianza(self, paths: FakePaths, store: SettingsStore,
                              visto: threading.Event, attesa: float = 0.8) -> None:
        """Il watch inotify e' attivo? Si prova finche' non risponde.

        `Observer.start()` ritorna prima che il watch lo sia: senza questa
        attesa la prova misurerebbe quella finestra invece del difetto.
        """
        for i in range(50):
            _edit(paths, f"target_fps = {60 if i % 2 == 0 else 30}",
                  f"target_fps = {30 if i % 2 == 0 else 60}")
            if visto.wait(timeout=attesa):
                visto.clear()
                time.sleep(attesa)       # nessuna coda del riscaldamento
                visto.clear()
                return
        raise AssertionError("la sorveglianza non si e' mai svegliata")

    def test_il_cambio_arriva_anche_se_qualcuno_ha_appena_LETTO_il_file(
            self, paths: FakePaths) -> None:
        """La prova decisiva: due giri identici tranne una `read_text()`."""
        visto = threading.Event()
        # Il valore di esercizio, non 0,01: con dieci millisecondi la lettura e
        # la scrittura possono cadere in finestre diverse e il difetto
        # sparirebbe a caso.
        store = SettingsStore(paths, debounce_s=0.2)
        store.subscribe(lambda _s: visto.set())
        f = paths.config_dir() / "settings.toml"
        with store:
            self._attendi_sorveglianza(paths, store, visto)
            atteso = 30 if store.current.ui.target_fps == 60 else 60
            f.read_text(encoding="utf-8")             # ← LA LETTURA
            _edit(paths, f"target_fps = {store.current.ui.target_fps}",
                  f"target_fps = {atteso}")
            assert visto.wait(timeout=5), "la lettura si e' mangiata il cambio"
        assert store.current.ui.target_fps == atteso

    def test_una_lettura_da_SOLA_non_fa_ricaricare(self, paths: FakePaths) -> None:
        """E non e' solo efficienza: `reload()` rilegge e confronta l'intero
        `Settings` a ogni apertura del file, cioe' a ogni `_documento()` di
        `imposta_valore` e a ogni `jarvis doctor`."""
        store = SettingsStore(paths, debounce_s=0.05)
        ricariche: list[int] = []
        store._current = store.current           # nessun cambio possibile
        vero_reload = store.reload
        store.reload = lambda: (ricariche.append(1), vero_reload())[1]  # type: ignore[method-assign]
        with store:
            for _ in range(20):
                (paths.config_dir() / "settings.toml").read_text(encoding="utf-8")
            time.sleep(0.4)
        assert ricariche == [], f"{len(ricariche)} ricariche per sole letture"

    def test_l_antirimbalzo_e_sul_fronte_di_DISCESA(self, tmp_path: Path) -> None:
        """Una raffica chiama il gancio **una volta, dopo l'ultimo evento**.

        ⚠️ **La prima stesura di questo test passava lo stesso col fronte di
        salita**, e va detto perche' e' il motivo per cui adesso e' scritto
        cosi'. Guidava il difetto attraverso inotify — due `_edit` di fila — e
        l'esito dipendeva da chi vinceva la corsa fra il thread di watchdog e
        la seconda scrittura: quasi sempre il dispatch arrivava a cose fatte e
        leggeva gia' il contenuto finale. Un sabotaggio senza rosso non e' un
        test che perdona: e' un test che non guarda.

        Qui gli eventi si danno al gestore **a mano**. Nessuna corsa, e la
        differenza fra i due fronti diventa un'asserzione sola: col fronte di
        salita il gancio e' gia' stato chiamato al primo evento — cioe' si
        rilegge il file mentre lo si sta ancora scrivendo.
        """
        chiamate: list[int] = []
        h = _ChangeHandler({"settings.toml"}, lambda: chiamate.append(1), 0.25)
        f = str(tmp_path / "settings.toml")

        for _ in range(5):
            h.on_any_event(FileModifiedEvent(f))
            time.sleep(0.02)
        assert chiamate == [], "chiamato PRIMA della fine della raffica"

        time.sleep(0.5)
        assert chiamate == [1], f"una raffica, {len(chiamate)} ricariche"
        h.annulla()

    def test_le_letture_non_arrivano_MAI_al_gancio(self, tmp_path: Path) -> None:
        """`IN_OPEN` e `IN_CLOSE_NOWRITE` dicono che qualcuno ha **letto**."""
        chiamate: list[int] = []
        h = _ChangeHandler({"settings.toml"}, lambda: chiamate.append(1), 0.05)
        f = str(tmp_path / "settings.toml")

        for _ in range(10):
            h.on_any_event(FileOpenedEvent(f))
            h.on_any_event(FileClosedNoWriteEvent(f))
        time.sleep(0.3)
        assert chiamate == [], f"{len(chiamate)} ricariche per sole letture"

        # E il file che cambia davvero passa: la guardia non e' una tapparella.
        h.on_any_event(FileMovedEvent(str(tmp_path / ".tmp"), f))
        time.sleep(0.3)
        assert chiamate == [1]
        h.annulla()

    def test_stop_butta_via_un_ricarico_in_ATTESA(self, paths: FakePaths) -> None:
        """Col fronte di discesa un `Timer` puo' essere gia' partito quando la
        sorveglianza si ferma: senza `annulla()` la ricarica arriverebbe dopo
        lo `stop()`, cioe' a padrone spento."""
        store = SettingsStore(paths, debounce_s=0.4)
        ricevute: list[Settings] = []
        store.subscribe(ricevute.append)
        store.start()
        time.sleep(0.3)
        _edit(paths, "target_fps = 60", "target_fps = 30")
        store.stop()                       # prima che il timer scatti
        time.sleep(0.8)
        assert ricevute == []
