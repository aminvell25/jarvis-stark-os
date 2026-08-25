"""core/engine — la radice di composizione."""

from __future__ import annotations

import asyncio

import pytest

from core.engine import Engine
from core.settings import SECRETS
from core.tools import registry
from tests.conftest import SECRETS_TOML


@pytest.fixture
def engine(short_paths) -> Engine:
    return Engine(short_paths)


class TestComposizione:
    def test_registra_i_tool_di_sistema_e_di_file(self, engine: Engine) -> None:
        nomi = set(registry.names())
        assert {"system_status", "top_processes"} <= nomi
        assert {"list_dir", "read_file", "trash_path", "organize_folder"} <= nomi

    def test_ogni_tool_distruttivo_ha_un_piano(self, engine: Engine) -> None:
        """Invariante 3, verificato sull'allowlist reale e non su un finto."""
        for nome in registry.names():
            t = registry.get(nome)
            if t.side_effect:
                assert t.planner is not None, f"{nome} distruttivo senza planner"
                assert t.gesture_allowed is False, f"{nome} distruttivo e gesture"

    def test_la_conferma_e_collegata(self, engine: Engine) -> None:
        """Senza, i tool distruttivi sarebbero inerti (fail-closed)."""
        from core.tools import registry as R

        assert R._CONFERMA is not None

    def test_costruire_due_volte_non_esplode(self, short_paths) -> None:
        """La radice di composizione POSSIEDE l'allowlist: ricostruirla la
        ridefinisce, non ci accumula sopra un doppione."""
        primo = Engine(short_paths)
        secondo = Engine(short_paths)
        assert registry.names() == sorted(set(registry.names()))

    def test_il_conteggio_dell_allowlist_DIPENDE_da_code_enabled(
        self, engine: Engine
    ) -> None:
        """Il conteggio esatto e' voluto: e' cosi' che si scopre un tool
        entrato nell'allowlist senza che nessuno l'abbia deciso, ed e' cosi'
        che si e' scoperto il contrario — i QUATTRO tool di memoria della Fase
        4 esistevano, erano provati, e non erano mai stati registrati.

          15 fino a Fase 6  timezones (Fase 5), open_web, youtube_search
          +2  §13           source_tree, archive_notes (introspect)
          +4  §13           recall, list_topics, pin_fact, write_topic
          +1  ADR-009       esegui_codice, ma SOLO se `code.enabled`

        ⚠️ L'ultimo addendo non e' una costante: e' una riga di configurazione.
        Un `== 22` fisso qui sarebbe verde anche il giorno in cui
        l'interruttore smettesse di funzionare — il caso peggiore, perche' quel
        tool esegue codice scritto da un LLM. Il conteggio si LEGGE dallo
        stesso posto da cui lo legge l'engine.
        """
        acceso = engine.settings.code.enabled
        # 22 e non 21 da §26.7: `imposta_valore` e' entrato nell'allowlist.
        assert len(registry.names()) == 22 + int(acceso)
        assert ("esegui_codice" in registry.names()) is acceso
        assert {"source_tree", "archive_notes", "recall", "list_topics",
                "pin_fact", "write_topic",
                # §26.7: senza questa riga la pagina impostazioni sarebbe una
                # vetrina, e il tool esisterebbe solo nei suoi test — che e'
                # esattamente il difetto di §13 e del Watcher delle news.
                "imposta_valore"} <= set(registry.names())

    def test_la_configurazione_spedita_lo_tiene_spento(self, engine: Engine) -> None:
        """E quindi il numero, con il file che si installa davvero, e' 21.
        `TestInterruttore` in `test_tool_codice.py` prova l'altro ramo."""
        assert engine.settings.code.enabled is False
        assert "esegui_codice" not in registry.names()

    def test_carica_le_impostazioni(self, engine: Engine) -> None:
        assert engine.settings.llm.backend == "claude_code"


class TestSnapshot:
    def test_ha_le_sezioni_attese(self, engine: Engine) -> None:
        snap = engine.state_snapshot()
        assert set(snap) >= {"fase", "core", "ws", "settings", "tools", "gpu"}
        # 9 da Fase 9: la fase e' il numero della composizione, e da qui in
        # avanti il core li compone tutti (§3.2).
        assert snap["fase"] == 9

    def test_espone_i_tool_senza_handler(self, engine: Engine) -> None:
        tools = engine.state_snapshot()["tools"]
        assert {"system_status", "trash_path"} <= {t["name"] for t in tools}
        for t in tools:
            assert set(t) == {"name", "description", "side_effect", "gesture_allowed"}

    def test_le_chiavi_compaiono_per_nome_non_per_valore(self, engine: Engine) -> None:
        chiave = SECRETS_TOML.split('"')[1]
        SECRETS.register(chiave)
        import json

        grezzo = json.dumps(engine.state_snapshot(), default=str)
        assert "deepgram_api_key" in grezzo, "il NOME deve esserci"
        assert chiave not in grezzo, "il VALORE non deve esserci"

    def test_dichiara_seccomp(self, engine: Engine) -> None:
        assert engine.state_snapshot()["core"]["seccomp"] is False


class TestCicloDiVita:
    async def test_avvio_e_chiusura_ordinata(self, engine: Engine) -> None:
        task = asyncio.create_task(engine.run())
        sock = engine.state_snapshot()["ws"]["socket"]
        from pathlib import Path

        for _ in range(200):
            if Path(sock).is_socket():
                break
            await asyncio.sleep(0.02)
        assert Path(sock).is_socket(), "il socket non e' stato creato"

        engine._stop.set()
        await asyncio.wait_for(task, timeout=10)
        assert not Path(sock).exists(), "il socket non e' stato rimosso"
