"""Il tool web e YouTube — SPEC §6.3, Fase 6."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from core.tools import registry
from core.tools.web import register_web_tools, valida_url


class TestValidazione:
    @pytest.mark.parametrize(
        "grezzo,atteso",
        [
            ("https://esempio.it", "https://esempio.it"),
            ("HTTPS://ESEMPIO.IT/Pagina", "https://esempio.it/Pagina"),
            ("  https://esempio.it/a?b=c#d  ", "https://esempio.it/a?b=c#d"),
        ],
    )
    def test_url_validi_normalizzati(self, grezzo: str, atteso: str) -> None:
        """Schema e host in minuscolo, percorso no: `/Pagina` e `/pagina` sono
        due risorse diverse su quasi ogni server."""
        assert valida_url(grezzo) == atteso

    @pytest.mark.parametrize(
        "grezzo",
        [
            "javascript:alert(1)",
            "data:text/html,<script>fetch('//x')</script>",
            "file:///etc/passwd",
            "http://esempio.it",           # non https
            "https://",                    # senza host
            "https://utente:segreto@esempio.it",
            "chrome://settings",
        ],
    )
    def test_url_rifiutati(self, grezzo: str) -> None:
        """Allowlist, non denylist: non serve elencare `javascript:` fra i
        vietati, basta che non sia fra i previsti."""
        with pytest.raises(ValueError):
            valida_url(grezzo)


class _FinteImpostazioni:
    """Il minimo che serve al tool: la chiave, e la possibilita' di cambiarla."""

    def __init__(self, chiave: str = "") -> None:
        self.secrets = type("S", (), {"youtube_api_key": SecretStr(chiave)})()


@pytest.fixture
def allowlist_pulita():
    registry.clear()
    yield
    registry.clear()


class TestYouTube:
    async def test_senza_chiave_apre_la_ricerca_e_lo_ANNUNCIA(self, allowlist_pulita) -> None:
        """Il ripiego silenzioso e' il difetto che §7.4 vieta per la voce, e
        vale qui allo stesso modo: aprire la ricerca invece di far partire il
        video e' un esito diverso da quello chiesto, e va detto."""
        register_web_tools(lambda: _FinteImpostazioni(""))
        r = await registry.invoke("youtube_search", {"query": "synthwave"})
        assert r.ok
        assert r.output["modo"] == "ricerca_aperta"
        assert "synthwave" in r.output["url"]
        assert r.output["annuncio"], "ripiego senza annuncio"

    async def test_con_chiave_ma_rete_muta_ripiega_e_lo_annuncia(
        self, allowlist_pulita, monkeypatch
    ) -> None:
        """Una chiave che c'e' ma non risponde non deve diventare un errore
        per l'utente: diventa la ricerca aperta, e si dice perche'."""
        def esplode(*_a, **_k):
            raise TimeoutError("rete assente")

        monkeypatch.setattr("core.tools.web._cerca_su_youtube", esplode)
        register_web_tools(lambda: _FinteImpostazioni("chiave-finta"))
        r = await registry.invoke("youtube_search", {"query": "synthwave"})
        assert r.ok and r.output["modo"] == "ricerca_aperta"
        assert "TimeoutError" in r.output["annuncio"]

    async def test_con_chiave_e_risposta_riproduce(self, allowlist_pulita, monkeypatch) -> None:
        """La strada completa, contro un finto della Data API: la chiamata
        vera non e' provata (nessuna chiave su questa macchina) ed e'
        dichiarato in FASE-06.md, ma il percorso del codice si'."""
        monkeypatch.setattr(
            "core.tools.web._cerca_su_youtube",
            lambda q, k: {"video_id": "dQw4w9WgXcQ", "titolo": "T", "canale": "C"},
        )
        register_web_tools(lambda: _FinteImpostazioni("chiave-finta"))
        r = await registry.invoke("youtube_search", {"query": "synthwave"})
        assert r.ok and r.output["modo"] == "riproduzione"
        assert r.output["video_id"] == "dQw4w9WgXcQ"

    async def test_la_chiave_non_esce_mai(self, allowlist_pulita, monkeypatch) -> None:
        """La chiave viaggia nella query string della richiesta: non deve
        comparire in nessun `ToolResult`, per nessuna delle strade."""
        monkeypatch.setattr(
            "core.tools.web._cerca_su_youtube",
            lambda q, k: {"video_id": "x", "titolo": "T", "canale": "C"},
        )
        register_web_tools(lambda: _FinteImpostazioni("CHIAVE-SEGRETA-123"))
        for query in ["synthwave", ""]:
            r = await registry.invoke("youtube_search", {"query": query})
            assert "CHIAVE-SEGRETA-123" not in str(r.output)


class TestOpenWeb:
    async def test_restituisce_l_url_risolto(self, allowlist_pulita) -> None:
        register_web_tools(lambda: _FinteImpostazioni(""))
        r = await registry.invoke("open_web", {"url": "HTTPS://Esempio.it/x"})
        assert r.ok and r.output["url"] == "https://esempio.it/x"

    async def test_uno_schema_non_previsto_e_un_esito_non_un_crash(
        self, allowlist_pulita
    ) -> None:
        """Nessuna eccezione propaga all'LLM — stile codice di CLAUDE.md."""
        register_web_tools(lambda: _FinteImpostazioni(""))
        r = await registry.invoke("open_web", {"url": "javascript:alert(1)"})
        assert not r.ok and "non ammesso" in r.error

    async def test_nessuno_dei_due_ha_side_effect(self, allowlist_pulita) -> None:
        """Aprire una pagina non tocca il disco: nessuna conferma di §6.2. Ma
        il test esiste perche' se un domani uno dei due la acquisisse, il
        registry pretenderebbe un planner e la cosa dev'essere una decisione,
        non una sorpresa."""
        register_web_tools(lambda: _FinteImpostazioni(""))
        per_nome = {t["name"]: t for t in registry.describe_all()}
        for nome in ("open_web", "youtube_search"):
            assert per_nome[nome]["side_effect"] is False
