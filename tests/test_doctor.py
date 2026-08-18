"""core/doctor — SPEC §16.1b."""

from __future__ import annotations

import pytest

from core.doctor import NON_ANCORA, Check, exit_code, render, run_checks
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

    async def test_i_sottosistemi_futuri_sono_nd_non_ok(self, checks) -> None:
        """Un doctor che dichiara sano cio' che non esiste e' peggio di uno
        che tace: mente con l'autorevolezza di uno strumento."""
        attesi = {n for n, _ in NON_ANCORA}
        for c in checks:
            if c.nome in attesi:
                assert c.stato == "n/d", f"{c.nome} dice {c.stato}, non esiste ancora"
                assert "Fase" in c.dettaglio

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
