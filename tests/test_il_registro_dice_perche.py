"""Il primo comando detto davvero al microfono, e il registro che taceva.

Il Signore ha aperto l'app e ha detto **«apriti i pannelli telemetria»**.
JARVIS ha risposto *«Vedo, Signore. Mi occupo del caricamento della
telemetria»*, e non è successo niente.

Nel diario restavano **otto righe di `dialogo` e zero di `azione`**. Per sapere
se T0 avesse anche solo visto quella frase ho dovuto eseguire il parser a mano.
Sono due difetti distinti, e il secondo è quello che li nasconde tutti.

**① La grammatica non conosce l'imperativo con il pronome attaccato.**
In italiano l'imperativo prende l'enclitico — apri/aprimi/aprila/apriti,
mostra/mostrami, chiudi/chiudilo — ed è la forma normale del parlato. `parse()`
conosceva solo la nuda, e il plurale «pannelli» mancava dov'era ammesso
«pannello»: un'asimmetria della stessa famiglia di quella già corretta fra
`open_panel` e `close_panel`.

**② Il registro non sapeva dire perché non era successo niente.**
`esegui_t0` annota ciò che la grammatica riconosce. L'altra metà — la delega a
T1, e la caduta quando T1 non c'è — non lasciava riga.

E una cosa che T1 **non** ha fatto: non ha mentito. «Vedo, Signore» e «Me ne
occupo» sono le due frasi che `config/voice-persona.md` gli PRESCRIVE alla
riga 41. Ha obbedito alla lettera. La riga falsa è quella sopra — *«Quelle
azioni le fa il sistema prima di arrivare a te»* — vera nel caso che non
capita mai, perché T1 è raggiunto **soltanto** quando T0 ha mancato.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from core.llm.grammar import (
    VERBI_DI_COMANDO,
    parse,
    quasi_comando,
    regole,
)
from core.traccia import Origine, Traccia
from tests.t0_corpus import CONVERSAZIONALI, CONVERSAZIONALI_NEWS


def _sorgente(nome: str) -> str:
    return (Path(__file__).resolve().parent.parent / nome).read_text(encoding="utf-8")


class TestLImperativoColPronomeAttaccato:
    """§7.6 — la forma in cui una persona parla davvero."""

    def test_la_frase_VERA_che_e_finita_a_T1(self) -> None:
        """Questa non è una frase scritta per il test: è la prima che il
        Signore abbia detto al microfono con l'intento di comandare."""
        assert parse("apriti i pannelli telemetria") == parse("apri la telemetria")

    @pytest.mark.parametrize("frase", [
        "aprimi la telemetria", "aprila la console", "mostrami il globo",
        "mostrameli i file", "chiudilo il globo", "chiudimi la console",
    ])
    def test_la_FAMIGLIA_degli_enclitici(self, frase: str) -> None:
        assert parse(frase) is not None, f"{frase!r} è italiano corrente"

    def test_il_PLURALE_era_un_asimmetria(self) -> None:
        """`(?:pannello\\s+)?` accettava il singolare e non il plurale, mentre
        gli articoli plurali erano ammessi ovunque nel corpus."""
        assert parse("apri i pannelli telemetria") == parse("apri il pannello telemetria")

    @pytest.mark.parametrize("frase", [
        "apriti cielo", "mostrati un po' piu' paziente", "nascondi la delusione",
        "chiudi un occhio stavolta", "apri bene le orecchie",
    ])
    def test_e_NON_ruba_le_frasi_che_il_corpus_sorveglia(self, frase: str) -> None:
        """⚠️ La sicurezza non viene dalla prudenza: viene dall'**allowlist**.
        `cielo` e `delusione` non sono pannelli, ed è la stessa allowlist che
        chiuse il furto di «chiudi un occhio stavolta»."""
        assert parse(frase) is None

    def test_NON_si_allarga_dove_l_oggetto_e_testo_LIBERO(self) -> None:
        """Un limite dichiarato, non una dimenticanza. Davanti alla coda di
        `search_files` un pronome in più diventa una query, ed è il difetto che
        quella regola ha già avuto una volta («cerca di capirmi»)."""
        assert parse("cercami il file dei conti") is None

    def test_nessuna_conversazionale_viene_rubata(self) -> None:
        """La misura PRIMA dell'allargamento era zero. Deve restare zero."""
        rubate = [f for f in CONVERSAZIONALI + CONVERSAZIONALI_NEWS if parse(f)]
        assert rubate == []


class TestIlQuasiComandoSiRegistraENONsiDice:
    """La decisione dichiarata **prima** di scrivere il codice, e il numero che
    l'ha decisa."""

    def test_etichetta_un_comando_MANCATO(self) -> None:
        assert parse("apri il coso strano") is None
        assert quasi_comando("apri il coso strano") == "apri"

    def test_e_NON_etichetta_una_conversazione(self) -> None:
        assert quasi_comando("raccontami com'e' andata la giornata") is None
        assert quasi_comando("la gara di sci e' stata rinviata") is None

    def test_il_15_1_PER_CENTO_e_una_misura_non_una_stima(self) -> None:
        """⚠️ Il numero che ha deciso di NON metterlo in bocca a JARVIS.
        Se qualcuno allarga `VERBI_DI_COMANDO`, questo test lo dice invece di
        lasciare il commento a mentire."""
        conv = CONVERSAZIONALI + CONVERSAZIONALI_NEWS
        falsi = [f for f in conv if quasi_comando(f)]
        assert len(conv) == 53 and len(falsi) == 8, (
            f"il commento in grammar.py dichiara 8 su 53 = 15,1%; "
            f"misurato adesso {len(falsi)} su {len(conv)}"
        )

    def test_i_verbi_ESISTONO_davvero_in_una_regola(self) -> None:
        """Nessun verbo inventato: ognuno deve comparire in un pattern vero.

        ⚠️ **Il verso opposto non è sorvegliato**: chi aggiunge una regola con
        un verbo nuovo e scorda la tupla perde una riga di registro, non un
        comando. Lo dichiaro invece di far finta che la guardia sia doppia.
        """
        patterns = " ".join(p for p, _ in regole())
        for v in VERBI_DI_COMANDO:
            assert v in patterns, f"{v!r} non compare in nessuna regola"

    def test_NON_entra_nel_contesto_di_T1(self) -> None:
        """La prova negativa: il quasi-comando è diagnosi, non un fatto da
        raccontare al modello. Una frase su sette porterebbe a JARVIS un
        «nessun comando riconosciuto» in mezzo a un discorso."""
        dopo = _sorgente("core/voice/pipeline.py").split("quasi = quasi_comando(", 1)[1]
        dopo = dopo.split("await self.parla(", 1)[0]
        assert "nota = nota_di_interruzione(" in dopo, "il ramo della nota è qui"
        assert "quasi" not in dopo.split("nota = nota_di_interruzione(", 1)[1], (
            "il quasi-comando NON deve finire nella nota di sistema"
        )


# ── la strumentazione, guidata da un turno vero ──────────────────────────────

class _Provider:
    name = "finto"
    per_enunciato = False
    text_spoken = ""

    async def stream(self, testo):
        from core.providers.base import AudioChunk

        yield AudioChunk(pcm=b"\x00\x00" * 160, sample_rate=24000)

    async def interrupt(self) -> None:
        return


class _T1:
    """Registra la `nota` ricevuta: è la prova negativa, in comportamento."""

    def __init__(self) -> None:
        self.note: list[str | None] = []

    def ask(self, testo: str, nota=None):
        self.note.append(nota)

        async def gen():
            yield "Vedo, Signore."

        return gen()


def _pipeline(t1=None, su_turno=None):
    from core.providers.health import Scelta
    from core.voice.pipeline import VoicePipeline
    from tests.conftest import AudioFinto

    scelta = Scelta(provider=_Provider(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=AudioFinto(), wake=None, stt=scelta, tts=scelta,
                         t1=t1, su_turno=su_turno)


async def _turno(testo: str, *, t1=None):
    from core.voice.wake import Trigger

    visti: list = []
    p = _pipeline(t1=t1, su_turno=visti.append)

    async def _finta(*_a, **_k):
        return testo

    p._trascrivi = _finta
    await p._ascolta_e_rispondi(Trigger("jarvis", "listen", 100.0, 0.1),
                                Traccia.nuova(Origine.VOCE))
    return visti


class TestIlRegistroDicePerDoveEPassato:
    async def test_T0_dichiara_la_sua_strada(self) -> None:
        visti = await _turno("apri la telemetria")
        assert visti and visti[0].strada == "t0"
        assert visti[0].azione == "open_panel"

    async def test_la_DELEGA_a_T1_lascia_una_riga(self) -> None:
        """Prima: `azione is None`, indistinguibile da un turno caduto."""
        visti = await _turno("apri il coso strano", t1=_T1())
        assert visti and visti[0].strada == "t1"
        assert visti[0].quasi_comando == "apri"
        assert visti[0].testo_utente == "apri il coso strano"

    async def test_una_conversazione_NON_porta_un_quasi_comando(self) -> None:
        visti = await _turno("la gara di sci e' stata rinviata", t1=_T1())
        assert visti and visti[0].strada == "t1"
        assert visti[0].quasi_comando is None

    async def test_la_nota_a_T1_resta_VUOTA(self) -> None:
        """La stessa decisione del test statico, ma vista dal modello."""
        t1 = _T1()
        await _turno("apri il coso strano", t1=t1)
        assert t1.note == [None]

    async def test_l_enunciato_CADUTO_non_sparisce_piu(self) -> None:
        """⚠️ Voce accesa, T0 che non riconosce, T1 che non è partito: JARVIS
        taceva e **il diario non aveva la riga per dirlo**."""
        visti = await _turno("apri il coso strano", t1=None)
        assert visti and visti[0].strada == "nessuna"
        assert visti[0].testo_utente == "apri il coso strano"


class TestLaRigaFinisceNelDiario:
    async def test_la_delega_diventa_una_riga_di_AZIONE(self, tmp_path: Path) -> None:
        from core.diario import Diario
        from core.engine import Engine
        from core.voice.pipeline import Turno

        class _Finto:
            _compito_di_sfondo = Engine._compito_di_sfondo
            _annota_instradamento = Engine._annota_instradamento

            def __init__(self, d):
                self._diario, self._compiti = d, set()

        d = Diario(tmp_path)
        f = _Finto(d)
        f._annota_instradamento(Turno(frase_wake="jarvis", azione=None, strada="t1",
                                      quasi_comando="apri",
                                      testo_utente="apri il coso strano"))
        await asyncio.sleep(0)
        righe = d.leggi(flusso="azione")
        assert len(righe) == 1
        assert righe[0]["strada"] == "t1" and righe[0]["ok"] is True
        assert righe[0]["quasi_comando"] == "apri"
        assert righe[0]["testo"] == "apri il coso strano", (
            "il testo sta QUI e non solo nel flusso `dialogo`: è l'ingresso da "
            "cui si ripara la grammatica"
        )

    async def test_T0_non_viene_annotato_DUE_volte(self, tmp_path: Path) -> None:
        from core.diario import Diario
        from core.engine import Engine
        from core.voice.pipeline import Turno

        class _Finto:
            _compito_di_sfondo = Engine._compito_di_sfondo
            _annota_instradamento = Engine._annota_instradamento

            def __init__(self, d):
                self._diario, self._compiti = d, set()

        d = Diario(tmp_path)
        _Finto(d)._annota_instradamento(
            Turno(frase_wake="jarvis", azione="open_panel", strada="t0",
                  testo_utente="apri la telemetria"))
        await asyncio.sleep(0)
        assert d.leggi(flusso="azione") == [], "`esegui_t0` l'ha già scritta"

    async def test_la_CADUTA_si_distingue_dalla_delega(self, tmp_path: Path) -> None:
        from core.diario import Diario
        from core.engine import Engine
        from core.voice.pipeline import Turno

        class _Finto:
            _compito_di_sfondo = Engine._compito_di_sfondo
            _annota_instradamento = Engine._annota_instradamento

            def __init__(self, d):
                self._diario, self._compiti = d, set()

        d = Diario(tmp_path)
        _Finto(d)._annota_instradamento(
            Turno(frase_wake="jarvis", azione=None, strada="nessuna",
                  testo_utente="apri il coso strano"))
        await asyncio.sleep(0)
        r = d.leggi(flusso="azione")[0]
        assert r["ok"] is False and r["errore"] == "t1_assente"

    def test_il_motore_lo_CHIAMA(self) -> None:
        assert "self._annota_instradamento(turno)" in _sorgente("core/engine.py")
