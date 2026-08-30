"""`initiatives/` era una cartella in sola scrittura.

Esiste dalla Fase 4, e la docstring di `registra_iniziativa` dice — testuale —
*«Ciò che JARVIS ha fatto di propria iniziativa, **visibile al risveglio**»*.

Non lo era: nessuno leggeva quel file. Il file il cui unico scopo è essere letto
al risveglio non aveva un lettore, e la cartella è rimasta a zero righe fino al
27 agosto.

È la firma del JARVIS dei film: ha lavorato mentre Lei non c'era, e al ritorno
dice **una conclusione**.
"""

from __future__ import annotations

import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _sorgente(nome: str) -> str:
    return (RADICE / nome).read_text(encoding="utf-8")


def _senza_commenti(s: str) -> str:
    fuori = []
    for r in s.splitlines():
        t = "" if r.lstrip().startswith(("#", "#:")) else r.split("#", 1)[0]
        fuori.append(t)
    return "\n".join(fuori)


def _store(tmp_path: Path):
    from core.memory.store import MemoryStore

    return MemoryStore(tmp_path)


class TestInitiativesHaUnLettore:
    def test_rilegge_cio_che_ha_scritto(self, tmp_path: Path) -> None:
        s = _store(tmp_path)
        s.registra_iniziativa("consolidamento", {"sessione": "x", "turni": 3})
        fatte = s.iniziative_dal(0)
        assert len(fatte) == 1 and fatte[0]["tipo"] == "consolidamento"

    def test_il_taglio_e_STRETTO_sul_timbro(self, tmp_path: Path) -> None:
        """`> da` e non `>=`: rileggendo con il proprio timbro non si
        riferisce due volte la stessa iniziativa."""
        s = _store(tmp_path)
        s.registra_iniziativa("consolidamento", {})
        ts = s.iniziative_dal(0)[0]["ts"]
        assert s.iniziative_dal(ts) == []

    def test_una_riga_STORTA_non_fa_cadere_il_risveglio(self, tmp_path: Path) -> None:
        s = _store(tmp_path)
        s.registra_iniziativa("consolidamento", {})
        (s.initiatives / "rotto.jsonl").write_text("{non json\n")
        assert len(s.iniziative_dal(0)) == 1


class TestLaFraseVieneDaiDATI:
    def test_il_resoconto_NON_passa_da_un_modello(self) -> None:
        """⚠️ Non è un risparmio, è una proprietà. Ciò che JARVIS dice di aver
        FATTO non deve poter essere inventato: un modello che riassume un
        registro può sbagliare un numero o aggiungere una riga che non c'era."""
        s = _senza_commenti(_sorgente("core/memory/risveglio.py"))
        for vietato in ("ClaudeT2", "esegui(", "_t2", "governor", "Governor"):
            assert vietato not in s, f"{vietato} nel compositore del resoconto"

    def test_niente_da_riferire_si_DICE(self) -> None:
        from core.memory.risveglio import componi

        assert componi([]) == "Niente da riferire, Signore."

    def test_uno_e_due_concordano(self) -> None:
        from core.memory.risveglio import componi

        assert "1 sessione." in componi([{"tipo": "consolidamento"}])
        assert "2 sessioni." in componi([{"tipo": "consolidamento"}] * 2)

    def test_prosa_e_non_elenco(self) -> None:
        """§5.7: «Nessun elenco, nessun markdown, nessuna emoji: non si
        pronunciano»."""
        from core.memory.risveglio import componi

        t = componi([{"tipo": "consolidamento"}, {"tipo": "ronda"}])
        assert "\n" not in t and "- " not in t and "*" not in t
        assert " e " in t, "due cose si uniscono con «e», non con una virgola"

    def test_un_tipo_SENZA_frase_non_inventa(self) -> None:
        from core.memory.risveglio import componi

        t = componi([{"tipo": "cosa_nuova"}])
        assert "cosa_nuova" not in t, "pronuncerebbe un nome di codice (§5.7)"
        assert "1 cosa che non so ancora raccontare" in t

    def test_ogni_tipo_REGISTRATO_ha_la_sua_frase(self) -> None:
        """⚠️ La guardia che conta. Chi aggiunge un'iniziativa nuova e scorda
        la frase lascia a JARVIS qualcosa che non sa raccontare, e senza questo
        test se ne accorgerebbe soltanto sentendolo."""
        import re

        from core.memory.risveglio import FRASI

        registrati = set()
        for f in (RADICE / "core").rglob("*.py"):
            for m in re.finditer(r'registra_iniziativa\(\s*"([^"]+)"',
                                 _senza_commenti(f.read_text(encoding="utf-8"))):
                registrati.add(m.group(1))
        assert registrati, "nessun chiamante trovato: il grep è rotto"
        assert registrati <= set(FRASI), f"senza frase: {registrati - set(FRASI)}"


class TestQuandoSiDiceCheNonCeNiente:
    def test_appena_detto_NON_si_ripete(self, tmp_path: Path) -> None:
        """Dirlo a ogni riconnessione — ventisette riavvii in tre giorni — lo
        trasformerebbe in rumore, e il rumore si ignora."""
        from core.memory.risveglio import e_ora_di_dirlo

        assert e_ora_di_dirlo(time.time()) is False

    def test_dopo_un_giorno_SI(self, tmp_path: Path) -> None:
        from core.memory.consolidate import PERIODO_S
        from core.memory.risveglio import e_ora_di_dirlo

        ora = time.time()
        assert e_ora_di_dirlo(ora, adesso=ora + PERIODO_S - 60) is False
        assert e_ora_di_dirlo(ora, adesso=ora + PERIODO_S + 60) is True

    def test_il_confine_e_LO_STESSO_di_5_5(self) -> None:
        """Non un numero nuovo: l'unica cosa che JARVIS fa da solo ha periodo
        giornaliero, quindi un giorno è il più piccolo intervallo in cui
        «niente» sia un'informazione."""
        s = _senza_commenti(_sorgente("core/memory/risveglio.py"))
        assert "from core.memory.consolidate import PERIODO_S" in s
        corpo = s.split("def e_ora_di_dirlo", 1)[1].split("\n\ndef ", 1)[0]
        # Via la docstring: spiega il confine per esteso, e cercare la stringa
        # nuda sarebbe verde per il commento invece che per il codice.
        assert "PERIODO_S" in corpo.split('"""', 2)[-1]


class TestIlMotoreLoRACCONTA:
    def test_scatta_quando_la_scrivania_ARRIVA(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("def _scrivanie_cambiate", 1)[1].split("\n    async def ", 1)[0]
        assert "self._resoconto_al_risveglio(" in dopo

    def test_e_NON_dipende_dalla_voce(self) -> None:
        """⚠️ Legarlo a `self._voce is not None` avrebbe reso il risveglio muto
        con la voce spenta, che è la configurazione predefinita di §7.1."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("def _scrivanie_cambiate", 1)[1].split("\n    async def ", 1)[0]
        prima_del_return = dopo.split("if self._voce is None:", 1)[0]
        assert "self._resoconto_al_risveglio(" in prima_del_return

    def test_va_nel_flusso_AZIONE_non_dialogo(self) -> None:
        """⚠️ Trovato dal vivo: con `dialogo` la frase compariva DUE volte —
        una mia e una del turno che la pronuncia, perché `annuncia()` produce
        un `Turno` e `_annota_dialogo` lo scrive.

        Non sono un duplicato da sopprimere, sono due fatti: qui JARVIS ha
        deciso di RIFERIRE, e resta anche a voce spenta; in `dialogo` finisce
        ciò che ha DETTO, se l'ha detto.
        """
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]
        assert 'intento="resoconto_al_risveglio"' in corpo
        assert '"dialogo"' not in corpo

    def test_si_SCRIVE_prima_di_parlare(self) -> None:
        """Il diario è su disco e si legge a voce spenta; EdgeTTS è di rete. A
        ordine rovesciato, una rete assente cancellerebbe il resoconto invece
        di renderlo muto."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]
        assert corpo.index("self._diario.annota(") < corpo.index("self._dillo(")

    def test_una_voce_che_cade_non_perde_il_FATTO(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]
        dopo_dillo = corpo.split("self._dillo(", 1)[1]
        assert "except Exception" in dopo_dillo
