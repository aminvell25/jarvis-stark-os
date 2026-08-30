"""§5.5 — il giro della memoria, che era rotto in tre punti insieme.

Tre pezzi scritti dalla Fase 4, ciascuno provato dai propri test, e nessuno dei
tre collegato:

1. `MemoryStore.registra_turno()` — `sessions/` restava **vuota**;
2. `Consolidatore.esegui()` — nessuno lo azionava alle 04:00;
3. `ContextPruner.contesto_per_t2()` — ogni T2 ripartiva da zero.

Si nascondevano a vicenda: anche azionando il consolidatore non avrebbe trovato
niente da consolidare, perché il registro delle sessioni non lo scriveva
nessuno. È il difetto ricorrente di questo progetto, moltiplicato per tre.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from core.memory.store import MemoryStore
from core.memory.attribuzione import Attribuzione


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    return MemoryStore(tmp_path)


def _engine_src() -> str:
    return (Path(__file__).resolve().parent.parent / "core" / "engine.py"
            ).read_text(encoding="utf-8")


class _Turno:
    def __init__(self, utente: str = "", detto: str = "", azione=None) -> None:
        self.testo_utente = utente
        self.testo_detto = detto
        self.azione = azione


class TestIlTurnoFINISCE_in_sessions:
    def test_la_riga_c_e_nella_radice_di_composizione(self) -> None:
        s = _engine_src()
        dopo = s.split("def _voce_su_turno", 1)[1].split("\n    def _registra_turno", 1)[0]
        assert "self._registra_turno_in_memoria(turno)" in dopo

    def test_scrive_utente_e_jarvis(self, store, monkeypatch) -> None:
        from core.engine import Engine

        finto = Engine.__new__(Engine)
        finto._memoria = store
        Engine._registra_turno_in_memoria(finto, _Turno("che tempo fa", "Sereno, Signore."))

        righe = list(store.sessions.glob("*.jsonl"))
        assert len(righe) == 1, "nessun file di sessione"
        d = json.loads(righe[0].read_text(encoding="utf-8").splitlines()[0])
        assert d["utente"] == "che tempo fa" and d["jarvis"] == "Sereno, Signore."

    def test_un_turno_MUTO_non_sporca_la_cronologia(self, store) -> None:
        from core.engine import Engine

        finto = Engine.__new__(Engine)
        finto._memoria = store
        Engine._registra_turno_in_memoria(finto, _Turno("", ""))
        assert list(store.sessions.glob("*.jsonl")) == []

    def test_un_disco_pieno_NON_zittisce_JARVIS(self, store) -> None:
        """Siamo sul percorso della voce: un'eccezione qui chiuderebbe il
        microfono per un errore di scrittura."""
        from core.engine import Engine

        class _Rotto:
            def registra_turno(self, *_a, **_k):
                raise OSError("No space left on device")

        finto = Engine.__new__(Engine)
        finto._memoria = _Rotto()
        Engine._registra_turno_in_memoria(finto, _Turno("qualcosa", "risposta"))

    def test_un_giorno_e_un_FILE(self, store) -> None:
        """Un core riavviato tre volte spezzerebbe una conversazione in tre
        file che il consolidatore riassumerebbe separatamente."""
        from core.engine import Engine

        finto = Engine.__new__(Engine)
        finto._memoria = store
        for i in range(3):
            Engine._registra_turno_in_memoria(finto, _Turno(f"frase {i}", "ok"))
        file = list(store.sessions.glob("*.jsonl"))
        assert len(file) == 1
        assert len(file[0].read_text(encoding="utf-8").strip().splitlines()) == 3


class TestIlCONSOLIDATORE_gira:
    def test_la_radice_lo_AVVIA_e_lo_ferma(self) -> None:
        s = _engine_src()
        assert "asyncio.create_task(self._consolida_di_notte())" in s
        dopo = s.split("async def _spegni_gradi", 1)[1].split("\n    async def", 1)[0]
        assert "self._compito_conso.cancel()" in dopo

    def test_l_ora_e_quella_di_5_5(self) -> None:
        from core.memory.consolidate import ORA_DEFAULT

        assert ORA_DEFAULT == 4

    @pytest.mark.parametrize("ora", [0, 4, 12, 23])
    def test_l_attesa_e_SEMPRE_futura_e_sotto_un_giorno(self, ora: int) -> None:
        """L'unica parte aritmetica del ciclo, e l'unica misurabile senza
        aspettare una notte."""
        from core.engine import Engine

        s = Engine._secondi_fino_alle(ora)
        assert 0 < s <= 24 * 3600

    async def test_senza_turni_non_spende_una_QUOTA(self, store) -> None:
        """Il consolidatore parla con un modello, e un modello costa. A
        sessioni vuote non deve spawnare niente."""
        from core.memory.consolidate import Consolidatore

        class _T2:
            chiamate = 0

            async def esegui(self, *_a, **_k):
                _T2.chiamate += 1
                raise AssertionError("spawn a sessioni vuote")

        esito = await Consolidatore(store, _T2()).esegui()
        assert esito["eseguito"] is False and _T2.chiamate == 0

    async def test_con_turni_scrive_un_TOPIC_e_lo_registra(self, store) -> None:
        """Il giro intero, dal turno alla nota durevole."""
        from core.engine import Engine
        from core.memory.consolidate import Consolidatore

        finto = Engine.__new__(Engine)
        finto._memoria = store
        Engine._registra_turno_in_memoria(
            finto, _Turno("mi preoccupa il clima", "Capisco, Signore."))

        class _Risultato:
            ok = True
            testo = "L'utente segue il tema del clima."
            errore = None
            costo_usd = 0.01
            durata_s = 1.0

        class _T2:
            """⚠️ Dalla fetta 3 le chiamate sono **due**, una per corpus, e
            ognuna vede SOLO le sue frasi: e' cosi' che la classe viene dalla
            costruzione invece che da cio' che il modello risponde. Quindi la
            frase del Signore deve arrivare al compito `-utente` e **non** a
            quello `-jarvis`, e viceversa."""

            def __init__(self):
                self.visti = {}

            async def esegui(self, compito, etichetta):
                self.visti[etichetta.rsplit("-", 1)[-1]] = compito
                return _Risultato()

        # ⚠️ `oggi=` perche' il turno e' stato scritto nella sessione di OGGI, e
        # dal 29 agosto la sessione aperta si lascia stare: riassumerla adesso
        # vorrebbe dire riassumerne meta'. Fingendo un altro giorno la si tratta
        # come chiusa, che e' cio' che questo test vuole misurare.
        t2 = _T2()
        esito = await Consolidatore(store, t2).esegui(oggi="9999-12-31")
        assert esito["topic"] == 1, esito
        assert "mi preoccupa il clima" in t2.visti["utente"], (
            "il turno non arriva al modello"
        )
        assert "mi preoccupa il clima" not in t2.visti["jarvis"], (
            "una frase del Signore nel corpus di JARVIS renderebbe la classe "
            "una bugia: la sezione `proposto-e-accettato` conterrebbe una cosa "
            "che il Signore ha dichiarato"
        )
        assert "Capisco, Signore." in t2.visti["jarvis"]
        assert any("clima" in (store.leggi_topic(n).contenuto or "")
                   for n in store.elenca_topic()), (
            "il consolidamento non ha lasciato traccia nei topic"
        )
        # §5.5: ogni scrittura notturna è visibile al risveglio.
        assert list(store.initiatives.glob("*.jsonl")), "nessuna iniziativa registrata"

    async def test_una_quota_esaurita_si_ANNUNCIA(self, store) -> None:
        """R33 e §16: nessuna degradazione silenziosa. La mattina dopo si deve
        sapere perché la memoria non è stata consolidata."""
        from core.engine import Engine
        from core.llm.governor import QuotaEsaurita
        from core.memory.consolidate import Consolidatore

        finto = Engine.__new__(Engine)
        finto._memoria = store
        Engine._registra_turno_in_memoria(finto, _Turno("qualcosa", "risposta"))

        from core.llm.governor import Permesso, Rifiuto

        class _T2:
            async def esegui(self, *_a, **_k):
                raise QuotaEsaurita(Permesso(False, Rifiuto.QUOTA, riprova_fra_s=60))

        avvisi: list[dict] = []
        esito = await Consolidatore(store, _T2(),
                                    su_advisory=avvisi.append).esegui(oggi="9999-12-31")
        assert esito["motivo"] == "quota"
        assert avvisi and avvisi[0]["topic"] == "agent.advisory"


class TestIlContestoARRIVA_a_T2:
    def test_i_meta_comandi_lo_COSTRUISCONO(self) -> None:
        s = _engine_src()
        dopo = s.split("async def _rispondi_al_meta", 1)[1][:2500]
        assert "contesto_per_t2" in dopo
        assert "ContextPruner(self._memoria)" in dopo

    def test_i_fatti_fissati_stanno_in_TESTA(self, store) -> None:
        """Sono dell'utente e valgono sempre: se il budget tronca, si tronca
        dalla coda."""
        from core.memory.pruner import ContextPruner

        store.fissa("Il proprietario si chiama Amin", Attribuzione.DICHIARATO)
        store.scrivi_topic("clima", "Discussione sul clima e sull'energia.")
        testo = ContextPruner(store).contesto_per_t2("che cosa sappiamo del clima")
        assert testo.index("Amin") < testo.index("clima")

    def test_senza_memoria_il_compito_resta_QUELLO(self) -> None:
        """Un contesto vuoto non deve aggiungere separatori a un prompt."""
        s = _engine_src()
        dopo = s.split("async def _rispondi_al_meta", 1)[1][:2500]
        assert "if contesto.strip() else" in dopo


class TestUnDifettoTROVATO_collegando:
    """`contesto_per_t2` passava il compito INTERO a `cerca()`, che fa una
    ricerca per sottostringa. Un compito è un prompt di centinaia di caratteri
    e non è sottostringa di niente: la funzione non poteva restituire nemmeno
    un topic, mai.

    Finché nessuno la chiamava, il difetto non aveva modo di manifestarsi. È
    l'argomento contro il collegare senza misurare — e a favore del collegare.
    """

    def test_il_compito_INTERO_non_trova_niente(self, store) -> None:
        store.scrivi_topic("clima", "Discussione sul clima e sull'energia.")
        assert store.cerca("che cosa sappiamo del clima") == [], (
            "`cerca` ha smesso di essere per sottostringa: allora questa "
            "spiegazione va rimisurata, e il tool `recall` con lei"
        )

    def test_ma_parola_per_parola_lo_TROVA(self, store) -> None:
        from core.memory.pruner import ContextPruner

        store.scrivi_topic("clima", "Discussione sul clima e sull'energia.")
        testo = ContextPruner(store).contesto_per_t2("che cosa sappiamo del clima")
        assert "clima" in testo

    def test_e_ordina_per_QUANTE_parole_tocca(self, store) -> None:
        """Un topic che ne tocca tre è più pertinente di uno che ne tocca una."""
        from core.memory.pruner import ContextPruner

        store.scrivi_topic("molto", "Parliamo di clima, energia e governo.")
        store.scrivi_topic("poco", "Una nota sul governo soltanto.")
        testo = ContextPruner(store).contesto_per_t2(
            "clima energia governo", topic_rilevanti=2)
        assert testo.index("clima, energia") < testo.index("governo soltanto")

    def test_cerca_resta_com_era_per_il_tool_recall(self, store) -> None:
        """§13: `recall` le passa una parola sola, dove la sottostringa è il
        comportamento giusto. Cambiarla avrebbe rotto quel caso per aggiustare
        questo."""
        store.scrivi_topic("clima", "Discussione sul clima.")
        assert [t.nome for t in store.cerca("clima")] == ["clima"]
