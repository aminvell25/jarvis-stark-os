"""JARVIS non improvvisa: esegue un protocollo che qualcuno ha scritto prima.

Nei due film le uniche due volte in cui JARVIS tocca il mondo — «House Party
Protocol», «Clean Slate Protocol» — esegue un comando che Tony aveva scritto
**mesi prima** e che richiama per nome. Fuori da un protocollo, riferisce e
chiede.

È la stessa forma dell'allowlist che questo progetto usa dappertutto: un
protocollo non è una libertà, è una dichiarazione. Chi la scrive è l'utente, in
`settings.toml`; JARVIS la esegue e basta.

## ⚠️ Il difetto che questo file esiste per impedire

Il primo disegno filtrava i tool su `side_effect`. È **sbagliato**, ed è
misurato: `open_web` ha `side_effect=False` e la sua stessa descrizione dice
«Apre una pagina https in un pannello browser»; `youtube_search` ha
`side_effect=False` e «lo fa partire».

In questo progetto `side_effect=True` significa «c'è un percorso risolto da
mostrare a chi conferma» — cioè «tocca il disco» — non «cambia qualcosa».
Un'allowlist costruita su quel campo avrebbe lasciato JARVIS aprire pagine e far
partire video di propria iniziativa, al risveglio, senza che nessuno chiedesse.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.protocolli import (
    INNESCHI,
    TOOL_OSSERVATIVI,
    Protocollo,
    ProtocolloRifiutato,
    Ronda,
    carica,
    firma,
    valida,
)

RADICE = Path(__file__).resolve().parent.parent
TUTTI = frozenset(TOOL_OSSERVATIVI | {"open_web", "youtube_search", "trash_path"})


class _Grezzo:
    def __init__(self, **kw) -> None:
        self.__dict__.update(
            {"nome": "ronda", "innesco": "risveglio", "tool": "list_dir",
             "args": {}, "frase": "e' cambiato qualcosa", **kw})


class _Esito:
    def __init__(self, ok=True, output=None, error=None) -> None:
        self.ok, self.output, self.error = ok, output, error


class TestLAllowlistNonEsideEffect:
    """La decisione che regge tutto il modulo."""

    def test_open_web_e_FUORI_pur_non_toccando_il_disco(self) -> None:
        """⚠️ La descrizione del tool dice «Apre una pagina https in un pannello
        browser». Un JARVIS che apre pagine di sua iniziativa al risveglio non è
        un sorvegliante, è un intruso."""
        assert "open_web" not in TOOL_OSSERVATIVI
        assert "youtube_search" not in TOOL_OSSERVATIVI
        with pytest.raises(ProtocolloRifiutato, match="osservativo"):
            valida(_Grezzo(tool="open_web"), nomi_tool=TUTTI)

    def test_e_i_tool_che_cambiano_la_VOCE_pure(self) -> None:
        for t in ("mute", "unmute", "set_volume"):
            assert t not in TOOL_OSSERVATIVI, f"{t} cambia la voce di JARVIS"

    def test_ogni_nome_ESISTE_e_non_tocca_il_disco(self) -> None:
        """⚠️ Un'allowlist esplicita invecchia: un tool rinominato resterebbe
        qui dentro senza che nessuno se ne accorga, e il protocollo che lo
        nomina verrebbe rifiutato a ogni avvio con una ragione che sembra un
        errore dell'utente.

        Si compone il registro come fa la radice, non si legge il sorgente:
        `core/tools/files.py` registra con un aiutante locale e un grep del
        nome non lo troverebbe.
        """
        import tempfile

        import core.tools.audio  # noqa: F401
        import core.tools.files
        import core.tools.geo  # noqa: F401
        import core.tools.introspect  # noqa: F401
        import core.tools.memory  # noqa: F401
        import core.tools.system
        import core.tools.web  # noqa: F401
        from tests.conftest import FakeSensors
        from core.tools import registry

        import core.tools.geo
        import core.tools.introspect
        import core.tools.memory
        from core.memory.store import MemoryStore

        store = MemoryStore(Path(tempfile.mkdtemp()))
        for registra in (
            lambda: core.tools.files.register_file_tools([Path(tempfile.mkdtemp())]),
            lambda: core.tools.system.register_system_tools(FakeSensors()),
            core.tools.geo.register_geo_tools,
            core.tools.introspect.register_introspect_tools,
            lambda: core.tools.memory.register_memory_tools(lambda: store),
        ):
            try:
                registra()
            except Exception:                  # gia' registrati da un altro test
                pass

        assenti = {n for n in TOOL_OSSERVATIVI if registry.get(n) is None}
        assert assenti <= {"ask_state"}, (
            f"nomi che non esistono piu': {sorted(assenti - {'ask_state'})}"
        )
        for nome in TOOL_OSSERVATIVI - assenti:
            assert registry.get(nome).side_effect is False, (
                f"{nome} tocca il disco: un protocollo non puo' invocarlo"
            )

    def test_un_tool_non_registrato_in_questo_avvio_si_RIFIUTA(self) -> None:
        """`ask_state` esiste solo col grado ARGUS acceso: dichiararlo a grado
        spento non deve produrre una ronda che fallisce a ogni giro."""
        with pytest.raises(ProtocolloRifiutato, match="registrato"):
            valida(_Grezzo(tool="ask_state"), nomi_tool=frozenset({"list_dir"}))


class TestLaDichiarazioneEFailClosed:
    def test_innesco_sconosciuto(self) -> None:
        with pytest.raises(ProtocolloRifiutato, match="innesco"):
            valida(_Grezzo(innesco="quando_mi_va"), nomi_tool=TUTTI)
        assert set(INNESCHI) == {"risveglio", "notte"}

    def test_senza_nome(self) -> None:
        with pytest.raises(ProtocolloRifiutato, match="nome"):
            valida(_Grezzo(nome="  "), nomi_tool=TUTTI)

    def test_senza_FRASE(self) -> None:
        """Senza, un cambiamento trovato non si può dire — e un sorvegliante
        muto è indistinguibile da uno spento."""
        with pytest.raises(ProtocolloRifiutato, match="frase"):
            valida(_Grezzo(frase=""), nomi_tool=TUTTI)

    def test_uno_rifiutato_non_porta_via_gli_ALTRI(self) -> None:
        buoni = carica([_Grezzo(nome="a"), _Grezzo(nome="b", tool="open_web"),
                        _Grezzo(nome="c")], nomi_tool=TUTTI)
        assert [p.nome for p in buoni] == ["a", "c"]

    def test_il_rifiuto_e_RUMOROSO(self) -> None:
        """⚠️ Una dichiarazione storta che sparisse in silenzio è la peggiore
        delle uscite: JARVIS non sorveglia, e nessuno lo sa."""
        from structlog.testing import capture_logs

        with capture_logs() as righe:
            carica([_Grezzo(tool="open_web")], nomi_tool=TUTTI)
        detti = [r for r in righe if r["event"] == "protocollo_rifiutato"]
        assert len(detti) == 1 and detti[0]["log_level"] == "error"


class TestParlaSoloQuandoQUALCOSAcambia:
    def _ronda(self, tmp_path: Path) -> Ronda:
        return Ronda(tmp_path / "protocolli")

    async def _giro(self, r: Ronda, uscita) -> object:
        p = Protocollo(nome="ronda", innesco="risveglio", tool="list_dir",
                       args={}, frase="e' cambiato qualcosa")

        async def invoca(_t, _a):
            return _Esito(output=uscita)

        return await r.esegui(p, invoca)

    async def test_il_PRIMO_giro_non_e_un_cambiamento(self, tmp_path: Path) -> None:
        """È un primo valore. Dirlo vorrebbe dire che ogni protocollo nuovo
        parla una volta per niente, e la prima cosa che JARVIS dice di sua
        iniziativa sarebbe rumore."""
        e = await self._giro(self._ronda(tmp_path), {"file": ["a"]})
        assert e.eseguito and not e.cambiato and e.frase == ""

    async def test_uguale_a_prima_TACE(self, tmp_path: Path) -> None:
        r = self._ronda(tmp_path)
        await self._giro(r, {"file": ["a"]})
        e = await self._giro(r, {"file": ["a"]})
        assert not e.cambiato

    async def test_diverso_PARLA_con_la_frase_dichiarata(self, tmp_path: Path) -> None:
        r = self._ronda(tmp_path)
        await self._giro(r, {"file": ["a"]})
        e = await self._giro(r, {"file": ["a", "b"]})
        assert e.cambiato and e.frase == "e' cambiato qualcosa"

    async def test_un_tool_che_FALLISCE_non_e_un_cambiamento(self, tmp_path: Path) -> None:
        """Altrimenti una radice tolta farebbe parlare JARVIS ogni giorno."""
        r = self._ronda(tmp_path)
        p = Protocollo(nome="ronda", innesco="risveglio", tool="list_dir",
                       args={}, frase="x")

        async def rotto(_t, _a):
            return _Esito(ok=False, error="radice non consentita")

        e = await r.esegui(p, rotto)
        assert not e.eseguito and not e.cambiato and e.errore

    async def test_e_non_SOLLEVA_mai(self, tmp_path: Path) -> None:
        r = self._ronda(tmp_path)
        p = Protocollo(nome="ronda", innesco="risveglio", tool="list_dir",
                       args={}, frase="x")

        async def esplode(_t, _a):
            raise RuntimeError("il disco non c'e' piu'")

        e = await r.esegui(p, esplode)
        assert not e.eseguito and "disco" in (e.errore or "")


class TestLImprontaEcanonica:
    def test_lo_stesso_dizionario_in_ordine_diverso_e_UGUALE(self) -> None:
        """⚠️ Senza `sort_keys` due giri identici darebbero impronte diverse e
        ogni giro sembrerebbe un cambiamento. Un sorvegliante che grida sempre è
        un sorvegliante che si spegne."""
        assert firma({"a": 1, "b": 2}) == firma({"b": 2, "a": 1})

    def test_un_contenuto_diverso_da_impronta_diversa(self) -> None:
        assert firma({"a": 1}) != firma({"a": 2})


class TestIlMotoreLaFaGIRARE:
    def _engine_src(self) -> str:
        return (RADICE / "core" / "engine.py").read_text(encoding="utf-8")

    def test_al_risveglio_PRIMA_di_leggere_le_iniziative(self) -> None:
        """Altrimenti ciò che la ronda trova adesso finirebbe nel resoconto di
        domani, per una cosa vista stamattina."""
        s = self._engine_src()
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split(
            "\n    async def ", 1)[0]
        assert 'self._ronda_di("risveglio")' in corpo
        assert corpo.index('_ronda_di("risveglio")') < corpo.index("iniziative_dal(")

    def test_e_di_NOTTE(self) -> None:
        s = self._engine_src()
        corpo = s.split("async def _consolida_di_notte", 1)[1].split(
            "\n    async def ", 1)[0]
        assert corpo.count('self._ronda_di("notte")') == 2, (
            "il recupero all'avvio e il ciclo delle 04:00 sono due strade, e "
            "una ronda che gira solo su una delle due e' meta' sorveglianza"
        )

    def test_solo_un_CAMBIAMENTO_diventa_un_iniziativa(self) -> None:
        """Una ronda che non trova niente non è un evento: registrarla
        riempirebbe `initiatives/` di righe che nessuno legge."""
        s = self._engine_src()
        corpo = s.split("async def _ronda_di", 1)[1].split("\n    def ", 1)[0]
        assert "if not esito.cambiato:" in corpo
        assert corpo.index("if not esito.cambiato:") < corpo.index(
            "registra_iniziativa")


class TestLaFraseDelProtocolloEDELLUTENTE:
    def test_il_resoconto_dice_la_frase_DICHIARATA(self) -> None:
        """JARVIS non compone una spiegazione di una cosa che non ha deciso lui
        di sorvegliare."""
        from core.memory.risveglio import componi

        t = componi([{"tipo": "protocollo", "nome": "ronda",
                      "frase": "e' cambiato qualcosa in Scaricati"}])
        assert "e' cambiato qualcosa in Scaricati" in t
        assert "?" not in t

    def test_due_protocolli_si_uniscono_in_PROSA(self) -> None:
        from core.memory.risveglio import componi

        t = componi([{"tipo": "protocollo", "frase": "prima cosa"},
                     {"tipo": "protocollo", "frase": "seconda cosa"}])
        assert " e " in t and "\n" not in t and "- " not in t

    def test_la_STESSA_frase_due_volte_si_dice_una(self) -> None:
        from core.memory.risveglio import componi

        t = componi([{"tipo": "protocollo", "frase": "x"},
                     {"tipo": "protocollo", "frase": "x"}])
        assert t.count("x") == 1


class TestIDueProtocolliSPEDITI:
    """Invariante 23 applicato a una configurazione: non un motore vuoto."""

    def test_config_ne_dichiara_due_VALIDI(self) -> None:
        import tomllib

        from core.settings import ProtocolloSettings

        d = tomllib.loads((RADICE / "config" / "settings.toml").read_text())
        grezzi = [ProtocolloSettings(**x) for x in d.get("protocolli", [])]
        assert len(grezzi) == 2
        buoni = carica(grezzi, nomi_tool=TUTTI)
        assert len(buoni) == 2, "un protocollo spedito e' rifiutato al caricamento"

    def test_e_coprono_ENTRAMBI_gli_inneschi(self) -> None:
        """Un motore provato su un solo innesco è un motore provato a metà."""
        import tomllib

        d = tomllib.loads((RADICE / "config" / "settings.toml").read_text())
        assert {x["innesco"] for x in d["protocolli"]} == set(INNESCHI)

    def test_e_il_predefinito_del_modello_resta_VUOTO(self) -> None:
        """⚠️ Quali cose JARVIS sorvegli è una decisione dell'utente. Un valore
        predefinito qui sarebbe JARVIS che decide per lui, cioè l'opposto del
        modello che questa sezione imita."""
        from core.settings import Settings

        campo = Settings.model_fields["protocolli"]
        assert campo.default_factory() == []


class TestLaMemoriaDellaRonda:
    def test_ricorda_su_DISCO(self, tmp_path: Path) -> None:
        """In memoria non basta: il core si è riavviato 27 volte in tre giorni,
        e una ronda che dimentica a ogni riavvio grida al primo giro dopo."""
        r = Ronda(tmp_path / "p")
        assert r.vista("ronda") is None
        r._ricorda("ronda", "abc123")
        assert Ronda(tmp_path / "p").vista("ronda") == "abc123"

    def test_un_file_STORTO_vale_come_mai_visto(self, tmp_path: Path) -> None:
        r = Ronda(tmp_path / "p")
        (tmp_path / "p" / "ronda.json").write_text("{non json")
        assert r.vista("ronda") is None

    def test_il_nome_diventa_un_percorso_SICURO(self, tmp_path: Path) -> None:
        """Il nome lo scrive l'utente: non deve poter uscire dalla cartella."""
        r = Ronda(tmp_path / "p")
        r._ricorda("../../fuori", "x")
        assert not (tmp_path.parent / "fuori.json").exists()
        assert list((tmp_path / "p").glob("*.json"))
