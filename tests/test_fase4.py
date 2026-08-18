"""T2, Governor, memoria e router — SPEC §5.3, §5.4, §5.5, §21.5."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.llm.governor import Governor, QuotaEsaurita
from core.memory.pruner import ContextPruner
from core.memory.store import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path / "memory_data")


class TestGovernor:
    async def test_rispetta_il_massimo_concorrente(self) -> None:
        g = Governor(max_concurrent=2, max_per_window=10)
        picco = 0

        async def lavoro():
            nonlocal picco
            async with g.spawn("x"):
                picco = max(picco, g.attivi)
                await asyncio.sleep(0.15)

        await asyncio.gather(*(lavoro() for _ in range(4)))
        assert picco == 2, f"picco {picco}, il massimo e' 2"

    async def test_la_finestra_rifiuta_col_motivo(self) -> None:
        g = Governor(max_concurrent=5, max_per_window=2)
        for _ in range(2):
            async with g.spawn("x"):
                pass
        with pytest.raises(QuotaEsaurita, match="quota"):
            async with g.spawn("terzo"):
                pass

    async def test_due_richieste_simultanee_non_sfondano_la_finestra(self) -> None:
        """Il conteggio si incrementa PRIMA dell'attesa sul semaforo: con un
        solo slot residuo, due richieste insieme non devono passare entrambe."""
        g = Governor(max_concurrent=5, max_per_window=1)

        async def prova() -> bool:
            try:
                async with g.spawn("x"):
                    await asyncio.sleep(0.05)
                return True
            except QuotaEsaurita:
                return False

        esiti = await asyncio.gather(prova(), prova())
        assert sum(esiti) == 1, f"passati {sum(esiti)}, atteso 1"

    def test_il_rate_limit_sospende_e_annuncia(self) -> None:
        """§5.4: sospendi T2 -> degrada -> advisory -> **non far fallire T1**."""
        avvisi = []
        g = Governor(su_advisory=avvisi.append)
        g.osserva({"type": "system", "subtype": "api_retry",
                   "error": "rate_limit", "retry_delay_ms": 30_000})
        assert g.sospeso
        assert avvisi and avvisi[-1]["level"] == "warn"
        assert avvisi[-1]["t1_operativo"] is True, (
            "l'advisory non dice che T1 continua: chi lo legge non puo' saperlo"
        )

    def test_un_api_retry_qualunque_non_sospende(self) -> None:
        g = Governor()
        g.osserva({"type": "system", "subtype": "api_retry", "error": "overloaded"})
        assert not g.sospeso

    async def test_sospeso_rifiuta_i_nuovi_spawn(self) -> None:
        g = Governor()
        g.sospendi(60, "prova")
        with pytest.raises(QuotaEsaurita, match="sospeso"):
            async with g.spawn("x"):
                pass
        g.riprendi()
        async with g.spawn("x"):
            pass

    def test_lo_stato_dice_quanto_manca(self, tmp_path: Path) -> None:
        """§5.4: «sapere quando la finestra sta per chiudersi PRIMA che si
        chiuda»."""
        s = Governor(max_per_window=15).stato()
        assert s["restanti"] == 15 and "sospeso" in s

    async def test_il_log_conso_registra_la_finestra(self, tmp_path: Path) -> None:
        """R32: il numero operativo sono gli spawn, non il costo in dollari."""
        import json

        g = Governor(dir_conso=tmp_path / "conso")
        async with g.spawn("compito"):
            pass
        righe = list((tmp_path / "conso").glob("*.jsonl"))
        assert righe
        r = json.loads(righe[0].read_text().splitlines()[0])
        assert r["etichetta"] == "compito"
        assert "restanti" in r and "usati_nella_finestra" in r


class TestMemoriaCorreggibileAMano:
    def test_i_fatti_non_si_duplicano(self, store: MemoryStore) -> None:
        store.fissa("Le stampanti sono due.")
        store.fissa("Le stampanti sono due.")
        assert store.fatti_fissati() == ["Le stampanti sono due."]

    def test_una_correzione_a_mano_vale_subito(self, store: MemoryStore) -> None:
        """§5.5: «quando JARVIS ricorda una cosa sbagliata, Lei apre il file e
        la corregge con un editor». Non si tiene una copia in memoria."""
        store.fissa("Le stampanti sono due.")
        f = store.topics / "_fatti-fissati.md"
        f.write_text(f.read_text().replace("due", "tre"), encoding="utf-8")
        assert store.fatti_fissati() == ["Le stampanti sono tre."]

    def test_i_topic_sono_markdown_leggibili(self, store: MemoryStore) -> None:
        p = store.scrivi_topic("Stampa 3D", "PETG per i pezzi funzionali.")
        assert p.suffix == ".md"
        assert p.read_text().startswith("# Stampa 3D")

    def test_la_ricerca_non_pesca_i_fatti_fissati(self, store: MemoryStore) -> None:
        """Chi costruisce un contesto li mette gia' in testa: trovarli anche
        nella ricerca li duplicherebbe dentro il budget."""
        store.fissa("Le stampanti 3D sono due.")
        store.scrivi_topic("Stampa 3D", "PETG.")
        nomi = [t.nome for t in store.cerca("stampa")]
        assert "_fatti-fissati" not in nomi

    def test_le_iniziative_sono_ispezionabili(self, store: MemoryStore) -> None:
        store.registra_iniziativa("consolidamento", {"sessione": "s1"})
        assert list(store.initiatives.glob("*.jsonl"))


class TestPrunerNonDuplicaT1:
    def test_non_esiste_build_context(self) -> None:
        """Invariante 17 e §5.5: con T1 persistente Claude Code gestisce gia'
        il proprio contesto. Un `build_context()` qui sarebbe il secondo
        gestore di cui §5.5 avverte."""
        assert not hasattr(ContextPruner, "build_context")

    def test_serve_a_t1_solo_per_i_fatti_fissati(self, store: MemoryStore) -> None:
        store.fissa("Mi si chiama Signore.")
        assert ContextPruner(store).fatti_fissati() == ["Mi si chiama Signore."]

    def test_il_contesto_t2_mette_i_fatti_per_primi(self, store: MemoryStore) -> None:
        store.fissa("Mi si chiama Signore.")
        store.scrivi_topic("Backup", "Ogni domenica.")
        c = ContextPruner(store).contesto_per_t2("backup")
        assert c.index("Signore") < c.index("domenica")

    def test_il_troncamento_non_perde_i_fatti(self, store: MemoryStore) -> None:
        store.fissa("Fatto importante.")
        store.scrivi_topic("Lungo", "x " * 20_000)
        c = ContextPruner(store, budget_tokens=200).contesto_per_t2("lungo")
        assert "Fatto importante." in c


class TestConsolidamento:
    async def test_saltato_per_quota_lo_dice(self, store: MemoryStore) -> None:
        """R33: §16 vieta le degradazioni silenziose."""
        from core.memory.consolidate import Consolidatore

        avvisi = []
        store.registra_turno("s1", {"utente": "ciao", "jarvis": "salve"})

        class T2Saturo:
            async def esegui(self, *a, **k):
                raise QuotaEsaurita(type("P", (), {"motivo": "quota", "riprova_fra_s": 60})())

        r = await Consolidatore(store, T2Saturo(), avvisi.append).esegui()
        assert r["eseguito"] is False and r["motivo"] == "quota"
        assert avvisi and "quota" in avvisi[-1]["reason"]

    async def test_non_tocca_i_fatti_fissati(self, store: MemoryStore) -> None:
        from core.memory.consolidate import Consolidatore

        store.fissa("Questo e' mio.")
        store.registra_turno("s1", {"utente": "ciao", "jarvis": "salve"})

        class T2Finto:
            async def esegui(self, *a, **k):
                return type("R", (), {"ok": True, "testo": "nota", "errore": None,
                                      "costo_usd": 0.0, "durata_s": 1.0})()

        await Consolidatore(store, T2Finto()).esegui()
        assert store.fatti_fissati() == ["Questo e' mio."]

    async def test_ogni_scrittura_notturna_e_visibile(self, store: MemoryStore) -> None:
        """Scrive senza conferma: in cambio, la mattina dopo si sa cosa ha fatto."""
        from core.memory.consolidate import Consolidatore

        store.registra_turno("s1", {"utente": "ciao", "jarvis": "salve"})

        class T2Finto:
            async def esegui(self, *a, **k):
                return type("R", (), {"ok": True, "testo": "nota", "errore": None,
                                      "costo_usd": 0.0, "durata_s": 1.0})()

        await Consolidatore(store, T2Finto()).esegui()
        assert list(store.initiatives.glob("*.jsonl"))


class TestRouter:
    @pytest.mark.parametrize("frase,tier", [
        ("apri la telemetria", "t0"),
        ("come stiamo", "t0"),
        ("cerca fattura agosto", "t0"),
        ("scrivimi uno script per i backup", "t2"),
        ("organizza i download", "t2"),
        ("analizza questo file", "t2"),
        ("che ne pensi di questo progetto", "t1"),
        ("come stai oggi", "t1"),
    ])
    async def test_instrada(self, frase: str, tier: str) -> None:
        from core.router import build_router

        s = await build_router().ainvoke({"text": frase, "steps": 0})
        assert s["tier"] == tier, f"{frase!r} -> {s['tier']}, atteso {tier}"

    async def test_t0_passa_l_intent_non_il_testo(self) -> None:
        """R31: il classificatore E' il parser T0, e il suo risultato non si
        butta via per poi ricalcolarlo."""
        from core.router import build_router

        s = await build_router().ainvoke({"text": "apri la console", "steps": 0})
        assert s["intent"] is not None and s["intent"].tool == "open_panel"

    def test_langsmith_e_spento(self) -> None:
        """LangGraph porta `langsmith`. Non deve poter chiamare casa da un
        sistema il cui §18.3 e' attento a cosa lascia la macchina."""
        import os

        import core.router  # noqa: F401

        assert os.environ.get("LANGSMITH_TRACING") == "false"

    def test_il_classificatore_non_ha_una_seconda_lista(self) -> None:
        """§21.5 propone parole chiave che duplicherebbero la grammatica T0.
        Un secondo classificatore divergerebbe al primo comando aggiunto."""
        from pathlib import Path as P

        import io
        import tokenize

        sorgente = (P(__file__).resolve().parent.parent / "core/router.py").read_text()

        # Guarda il CODICE, non la prosa: il docstring CITA la lista di §21.5
        # per spiegare perche' non viene usata, e un controllo sul testo grezzo
        # scatterebbe sulla propria spiegazione. Stesso difetto gia' corretto
        # per l'invariante 29 in Fase 2.
        codice = " ".join(
            t.string for t in tokenize.generate_tokens(io.StringIO(sorgente).readline)
            if t.type not in (tokenize.COMMENT, tokenize.STRING)
        )
        assert "parse" in codice, "il router non chiede al parser T0"
        for rubata in ("apri", "chiudi", "pannello"):
            assert rubata not in codice, f"{rubata!r} riscritta nel codice del router"


class TestT2:
    def test_argv_secondo_la_specifica(self) -> None:
        from core.llm.claude_t2 import ClaudeT2

        a = ClaudeT2(Governor(), Path(".")).argv("compito")
        for atteso in ("-p", "--output-format", "--model", "--allowedTools",
                       "--permission-mode", "--max-turns", "--forward-subagent-text"):
            assert atteso in a, f"{atteso} assente: §5.3 lo richiede"

    def test_i_tool_di_scrittura_distruttiva_non_ci_sono(self) -> None:
        """T2 puo' leggere e modificare, ma cancellare passa dall'allowlist del
        core, che chiede conferma (§6.1)."""
        from core.llm.claude_t2 import ClaudeT2

        a = ClaudeT2(Governor(), Path(".")).argv("x")
        tool = a[a.index("--allowedTools") + 1]
        assert "rm" not in tool and "Write" not in tool

    async def test_ogni_spawn_passa_dal_governor(self) -> None:
        """Invariante 16. Con la finestra chiusa, non parte alcun processo."""
        from core.llm.claude_t2 import ClaudeT2

        g = Governor(max_per_window=0)
        r = await ClaudeT2(g, Path(".")).esegui("x", "prova")
        assert r.ok is False and "quota" in (r.errore or "")
