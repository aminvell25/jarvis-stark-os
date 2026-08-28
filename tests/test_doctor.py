"""core/doctor — SPEC §16.1b."""

from __future__ import annotations

import pytest

from core.doctor import Check, exit_code, render, run_checks
from core.settings import SECRETS
from tests.conftest import SECRETS_TOML

STATI_VALIDI = {"ok", "warn", "fail", "n/d"}


@pytest.fixture
async def checks(short_paths):
    return await run_checks(short_paths)


class TestRegistroDeiControlli:
    async def test_ogni_controllo_ha_uno_stato_valido(self, checks) -> None:
        assert checks and all(c.stato in STATI_VALIDI for c in checks)

    async def test_ogni_controllo_ha_un_dettaglio(self, checks) -> None:
        """Uno stato senza dettaglio non aiuta a capire cosa fare."""
        assert all(c.dettaglio.strip() for c in checks)

    async def test_ci_sono_tutte_le_righe_di_16_1b(self, checks) -> None:
        """§16.1b elenca i sottosistemi che lo strumento deve coprire.

        Fino alla Fase 8 sei di queste righe dicevano «non ancora
        implementato»: era la verita', ed era giusto dirla. Da Fase 9 esistono
        tutte, e il test verifica che nessuna sia sparita nel passaggio —
        sparire e' il modo in cui un doctor comincia a mentire per omissione.
        """
        nomi = {c.nome for c in checks}
        assert {"CORE", "WS", "SETTINGS", "SANDBOX", "VRAM",
                "T1 claude", "T1 auth", "STT", "TTS", "WAKE", "QUOTA"} <= nomi

    async def test_spento_e_rotto_non_sono_la_stessa_cosa(self, checks) -> None:
        """Con `voice.enabled = false` T1 non c'e' perche' e' stato deciso, non
        perche' e' guasto. Un doctor che dicesse «fail» manderebbe qualcuno a
        cercare un problema che non esiste."""
        t1 = next(c for c in checks if c.nome == "T1 claude")
        assert t1.stato == "n/d" and "spenta" in t1.dettaglio

    async def test_core_spento_e_un_guasto(self, checks) -> None:
        """Nessun engine gira in questo test: il doctor deve dirlo."""
        core = next(c for c in checks if c.nome == "CORE")
        assert core.stato == "fail" and "non in esecuzione" in core.dettaglio

    async def test_settings_letto_dalla_config_dir(self, checks) -> None:
        s = next(c for c in checks if c.nome == "SETTINGS")
        assert s.stato == "ok" and "deepgram_api_key" in s.dettaglio


class TestSandboxProvataDavvero:
    async def test_esegue_un_processo_isolato(self, checks) -> None:
        """`which bwrap` direbbe ok su un kernel che vieta gli userns: il
        controllo deve provarci."""
        sb = next(c for c in checks if c.nome == "SANDBOX")
        assert sb.stato in {"ok", "warn"}
        assert "ok," in sb.dettaglio

    async def test_dichiara_seccomp_assente(self, checks) -> None:
        sb = next(c for c in checks if c.nome == "SANDBOX")
        assert "seccomp NON applicato" in sb.dettaglio


class TestUscita:
    async def test_nd_non_e_un_guasto(self) -> None:
        assert exit_code([Check("X", "n/d", "d"), Check("Y", "ok", "d")]) == 0

    async def test_fail_lo_e(self) -> None:
        assert exit_code([Check("X", "fail", "d")]) == 1

    async def test_warn_non_lo_e(self) -> None:
        assert exit_code([Check("X", "warn", "d")]) == 0

    async def test_le_colonne_sono_allineate(self, checks) -> None:
        """§16.1b mostra un'uscita in colonne: lo stato deve cominciare alla
        stessa posizione in ogni riga, o l'occhio non puo' scorrerla."""
        righe = render(checks).splitlines()
        offset = max(len(c.nome) for c in checks) + 2
        for riga, c in zip(righe, checks):
            assert riga[offset:].startswith(c.stato.upper()), (
                f"colonna disallineata: {riga!r}"
            )

    async def test_nessuna_chiave_nelluscita(self, checks) -> None:
        chiave = SECRETS_TOML.split('"')[1]
        SECRETS.register(chiave)
        assert chiave not in render(checks)


class TestLaRigaPiuImportanteDiceLaCOSAGIUSTA:
    """⚠️ `_check_auth` è, per stessa ammissione del suo docstring, «la riga più
    importante dello strumento». Etichetta e nome del guasto erano **cablati**:
    dopo tre cadute non-auth stampava

        [fail] T1 auth: sessione scaduta (riavvii_ripetuti) — ...

    cioè la causa giusta, l'etichetta sbagliata e il nome sbagliato. Era latente
    finché un `degraded_llm` non-auth era un preludio all'uscita del processo.
    **La decisione del 28 agosto 2026 — restare vivi — lo rende uno stato in cui
    si RESTA**, e quindi uno che si legge davvero.
    """

    def _snap(self, motivo: str, azione: str = "fai questo"):
        return {"voce": {"auth": {"stato": "degraded_llm", "motivo": motivo,
                                  "riavvii": 3, "azione": azione}}}

    def test_per_l_auth_dice_sessione_scaduta(self) -> None:
        from core.doctor import _check_auth

        c = _check_auth(self._snap("auth_expired"))
        assert c.nome == "T1 auth"
        assert "sessione scaduta" in c.dettaglio

    def test_per_i_riavvii_ripetuti_NON_dice_sessione_scaduta(self) -> None:
        from core.doctor import _check_auth

        c = _check_auth(self._snap("riavvii_ripetuti"))
        assert c.stato == "fail"
        assert "scaduta" not in c.dettaglio, (
            "dice al Signore che la sessione è scaduta quando non lo è"
        )
        assert c.nome != "T1 auth", (
            "l'etichetta dice «auth» per un guasto che con l'autenticazione "
            "non c'entra"
        )
        assert "riavvii_ripetuti" in c.dettaglio

    def test_una_causa_SCONOSCIUTA_non_prende_il_nome_di_un_altra(self) -> None:
        """Allowlist: dire la cosa sbagliata è peggio che essere generici."""
        from core.doctor import _check_auth

        c = _check_auth(self._snap("una_causa_nuova", azione=""))
        assert c.stato == "fail"
        assert "scaduta" not in c.dettaglio
        assert c.dettaglio.endswith("(una_causa_nuova)"), c.dettaglio

    def test_a_stato_NOMINALE_resta_la_riga_di_sempre(self) -> None:
        from core.doctor import _check_auth

        c = _check_auth({"voce": {"auth": {"stato": "nominal", "motivo": "",
                                           "riavvii": 0, "azione": ""}}})
        assert (c.nome, c.stato) == ("T1 auth", "ok")


class TestLaUnitInstallataEQuellaDelRepo:
    """Il repository non è la macchina.

    ⚠️ **Trovato dal vivo, non ipotizzato.** La copia in
    `~/.config/systemd/user/` era del 19 agosto e diceva una riga
    `RestartPreventExitStatus` diversa da quella del repository. Con la copia
    vecchia systemd si sarebbe comportato in modo diverso da come il repository
    crede, e nessun test poteva accorgersene.

    `tests/test_supervisor.py` verifica quella riga e resta verde: legge il
    file del REPOSITORY. Questa differenza non è una proprietà del codice, è
    uno stato dell'installazione, e per questo vive nel doctor.

    ⚠️ **E si è ripresentata il 28 agosto, a parti invertite.** La decisione di
    restare vivi in `degraded_llm` ha tolto il codice 42 dalla unit del
    repository, mentre la copia installata lo aveva ancora: `_check_unit`
    confronta l'impronta dell'intero file, quindi dice `fail` finché non si
    reinstalla con `packaging/installa.sh`. È il comportamento voluto — una
    difesa che il repository crede attiva e che sulla macchina non lo è vale
    un `fail`, in tutte e due le direzioni.
    """

    def _installa(self, casa, testo: str) -> None:
        d = casa / ".config" / "systemd" / "user"
        d.mkdir(parents=True, exist_ok=True)
        (d / "jarvis-core.service").write_text(testo, encoding="utf-8")

    def test_allineata_e_OK(self, tmp_path, monkeypatch) -> None:
        from pathlib import Path as P

        from core.doctor import _check_unit

        repo = P(__file__).resolve().parent.parent / "packaging" / "jarvis-core.service"
        self._installa(tmp_path, repo.read_text(encoding="utf-8"))
        monkeypatch.setattr(P, "home", staticmethod(lambda: tmp_path))
        c = _check_unit()
        assert c.stato == "ok" and "allineata" in c.dettaglio

    def test_VECCHIA_e_un_FAIL_non_un_avviso(self, tmp_path, monkeypatch) -> None:
        """Non `warn`: una unit vecchia può disattivare in silenzio una difesa
        che il repository crede attiva."""
        from pathlib import Path as P

        from core.doctor import _check_unit

        repo = P(__file__).resolve().parent.parent / "packaging" / "jarvis-core.service"
        vecchia = repo.read_text(encoding="utf-8").replace(
            "RestartPreventExitStatus=41", "RestartPreventExitStatus=41 42")
        assert vecchia != repo.read_text(encoding="utf-8"), (
            "la riga che questo test manomette non esiste più: il controllo "
            "va riscritto, non cancellato"
        )
        self._installa(tmp_path, vecchia)
        monkeypatch.setattr(P, "home", staticmethod(lambda: tmp_path))
        c = _check_unit()
        assert c.stato == "fail"
        assert "installa.sh" in c.dettaglio, "dice che è rotta e non come si aggiusta"

    def test_NON_installata_e_un_avviso(self, tmp_path, monkeypatch) -> None:
        """Chi non l'ha installata non ha un guasto: ha una scelta che non ha
        fatto. Il core gira benissimo lanciato a mano."""
        from pathlib import Path as P

        from core.doctor import _check_unit

        monkeypatch.setattr(P, "home", staticmethod(lambda: tmp_path))
        c = _check_unit()
        assert c.stato == "warn" and "installa.sh" in c.dettaglio

    async def test_e_nell_elenco_dei_controlli(self) -> None:
        """Un controllo che nessuno esegue non controlla niente — ed è il
        difetto che questa sessione ha incontrato sei volte."""
        from core.doctor import run_checks

        nomi = [c.nome for c in await run_checks()]
        assert "UNIT" in nomi, f"controlli eseguiti: {nomi}"
