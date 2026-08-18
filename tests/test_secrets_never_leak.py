"""Le chiavi API non compaiono da nessuna parte — CLAUDE.md, stile codice.

Ci sono due varchi distinti e servono due difese distinte.

`SecretStr` chiude il primo: `repr()`, `str()` e la serializzazione JSON
mostrano asterischi. Ma non chiude il secondo: dopo `get_secret_value()` il
segreto e' una stringa qualunque, e una stringa qualunque finisce in un log
per distrazione. Quello lo chiude il processore `redact_secrets`.

Questi test coprono entrambi, perche' passare il primo e fallire il secondo
darebbe l'illusione della protezione.
"""

from __future__ import annotations

import io

import pytest
import structlog

from core.settings import SECRETS, Secrets, SecretRegistry, load_settings, redact_secrets
from tests.conftest import FakePaths

CHIAVE = "dg_chiave_di_prova_NON_REALE_9f3a"      # la stessa di conftest.SECRETS_TOML


@pytest.fixture
def log_buffer():
    """structlog reale con la catena di produzione, che scrive in memoria.

    Non `structlog.testing.capture_logs`: quella scorciatoia intercetta gli
    eventi PRIMA dei processori, quindi non verificherebbe mai la redazione —
    proverebbe solo che il test sa scrivere un dizionario.
    """
    buf = io.StringIO()
    structlog.configure(
        processors=[redact_secrets, structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(file=buf),
        cache_logger_on_first_use=False,
    )
    yield buf
    structlog.reset_defaults()


class TestSecretStrChiudeIlPrimoVarco:
    def test_non_compare_in_repr(self, paths: FakePaths) -> None:
        s = load_settings(paths)
        assert CHIAVE not in repr(s)
        assert CHIAVE not in repr(s.secrets)
        assert CHIAVE not in repr(s.secrets.deepgram_api_key)

    def test_non_compare_in_str(self, paths: FakePaths) -> None:
        s = load_settings(paths)
        assert CHIAVE not in str(s)
        assert CHIAVE not in str(s.secrets.deepgram_api_key)

    def test_non_compare_nel_dump(self, paths: FakePaths) -> None:
        s = load_settings(paths)
        assert CHIAVE not in str(s.secrets.model_dump(mode="json"))
        assert CHIAVE not in str(s.secrets.model_dump())
        assert CHIAVE not in str(s.model_dump())

    def test_ma_il_valore_resta_recuperabile(self, paths: FakePaths) -> None:
        """La protezione non deve rendere la chiave inutilizzabile: il
        provider Deepgram dovra' pur leggerla."""
        s = load_settings(paths)
        assert s.secrets.deepgram_api_key.get_secret_value() == CHIAVE

    def test_present_riporta_i_nomi_non_i_valori(self, paths: FakePaths) -> None:
        s = load_settings(paths)
        assert s.secrets.present() == {"deepgram_api_key"}


class TestRedazioneChiudeIlSecondoVarco:
    def test_valore_esplicito_nei_log_viene_oscurato(self, paths, log_buffer) -> None:
        """Il caso reale: qualcuno scrive `key=chiave.get_secret_value()`."""
        s = load_settings(paths)
        structlog.get_logger().info(
            "prova", key=s.secrets.deepgram_api_key.get_secret_value()
        )
        uscita = log_buffer.getvalue()
        assert CHIAVE not in uscita
        assert SecretRegistry.MASK in uscita

    def test_valore_annegato_in_una_frase(self, paths, log_buffer) -> None:
        load_settings(paths)
        structlog.get_logger().warning(
            "richiesta_fallita", url=f"https://api.deepgram.com/?token={CHIAVE}&x=1"
        )
        assert CHIAVE not in log_buffer.getvalue()

    def test_oggetto_secretstr_nei_log(self, paths, log_buffer) -> None:
        s = load_settings(paths)
        structlog.get_logger().info("prova", key=s.secrets.deepgram_api_key)
        assert CHIAVE not in log_buffer.getvalue()

    def test_la_riga_di_caricamento_non_perde_nulla(self, log_buffer, paths) -> None:
        """`load_settings` logga da se': verifichiamo il suo output vero."""
        load_settings(paths)
        uscita = log_buffer.getvalue()
        assert "settings_caricate" in uscita
        assert CHIAVE not in uscita
        assert "deepgram_api_key" in uscita          # il NOME si', il valore no


class TestIlRegistroNonSiAutodistrugge:
    def test_la_stringa_vuota_non_viene_registrata(self) -> None:
        """Se `""` finisse nel registro, `scrub` inserirebbe il marcatore fra
        ogni coppia di caratteri di ogni messaggio. E' il modo piu' rapido di
        rendere illeggibili tutti i log del sistema, e due delle tre chiavi
        del template SONO vuote."""
        SECRETS.register_secrets(Secrets())          # tutte e tre vuote
        assert SECRETS.scrub("ciao mondo") == "ciao mondo"

    def test_oscura_piu_chiavi(self) -> None:
        SECRETS.register("aaa", "bbb")
        assert SECRETS.scrub("x aaa y bbb z") == (
            f"x {SecretRegistry.MASK} y {SecretRegistry.MASK} z"
        )

    def test_clear_svuota(self) -> None:
        SECRETS.register("segreto")
        SECRETS.clear()
        assert SECRETS.scrub("segreto") == "segreto"
