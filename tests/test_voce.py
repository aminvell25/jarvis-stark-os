"""Voce: chunker, wake, audio, T1 — SPEC §7."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.llm.claude_t1 import (
    FINESTRA_RIAVVII_S,
    SOGLIA_RIPETUTI,
    ClaudeT1,
    Uscita,
)
from core.platform.linux_audio import argv_play, argv_record, tono
from core.providers.chunker import MAX_CHARS, MIN_CHARS, clause_chunks


async def _da(testo: str, pezzo: int = 3):
    for i in range(0, len(testo), pezzo):
        yield testo[i:i + pezzo]


class TestChunker:
    async def test_il_primo_frammento_esce_prima(self) -> None:
        """§7.4: soglia dimezzata sul primo. Cio' che l'orecchio percepisce
        come reattivita' e' QUANDO JARVIS comincia a parlare."""
        testo = "Sono operativo. " + "Poi continuo con una frase molto piu' lunga della prima. "
        pezzi = [c async for c in clause_chunks(_da(testo))]
        assert pezzi[0] == "Sono operativo."
        assert len(pezzi[0]) < MIN_CHARS, "il primo non ha usato la soglia dimezzata"

    async def test_spezza_sui_confini_di_frase(self) -> None:
        pezzi = [c async for c in clause_chunks(_da(
            "Prima frase abbastanza lunga da superare la soglia. Seconda frase altrettanto lunga."))]
        assert len(pezzi) >= 2
        assert all(p.strip() for p in pezzi)

    async def test_taglia_comunque_a_max_chars(self) -> None:
        """Un testo senza punteggiatura non deve restare muto per sempre."""
        pezzi = [c async for c in clause_chunks(_da("parola " * 120))]
        assert pezzi and max(len(p) for p in pezzi) <= MAX_CHARS + 10

    async def test_non_perde_la_coda(self) -> None:
        pezzi = [c async for c in clause_chunks(_da("Frase senza punto finale"))]
        assert "".join(pezzi).replace(" ", "") == "Frasesenzapuntofinale"

    async def test_flusso_vuoto(self) -> None:
        assert [c async for c in clause_chunks(_da(""))] == []


class TestAudioArgv:
    """L'argv si verifica confrontando stringhe, senza catturare audio."""

    def test_cattura_a_16k_mono_s16(self) -> None:
        a = argv_record()
        assert a[0] == "pw-record"
        assert "--rate" in a and "16000" in a
        assert "--channels" in a and "1" in a
        assert "--format" in a and "s16" in a
        assert "--raw" in a

    def test_riproduzione_stessi_parametri(self) -> None:
        """Se cattura e riproduzione divergessero, il tono di conferma
        uscirebbe accelerato o rallentato."""
        r, p = argv_record(), argv_play()
        assert r[1:] == p[1:] and p[0] == "pw-play"

    def test_il_tono_dura_ottanta_millisecondi(self) -> None:
        """§7.2 regola 2: un tono, non una voce."""
        t = tono()
        assert len(t) / 2 / 16000 == pytest.approx(0.080, abs=0.001)

    def test_il_tono_non_comincia_di_netto(self) -> None:
        """Un'onda troncata produce un clic, e questo suono si sentira'
        decine di volte al giorno."""
        import array

        c = array.array("h")
        c.frombytes(tono())
        assert abs(c[0]) < 200, "attacco netto: si sentira' come un clic"
        assert abs(c[-1]) < 200, "rilascio netto"


class TestT1:
    @pytest.fixture
    def t1(self, tmp_path: Path) -> ClaudeT1:
        return ClaudeT1("claude-haiku-4-5-20251001", tmp_path / "voice-cwd",
                        Path("config/voice-persona.md"))

    def test_argv_secondo_la_specifica(self, t1: ClaudeT1) -> None:
        a = t1.argv()
        for atteso in ("--input-format", "stream-json", "--include-partial-messages",
                       "--replay-user-messages", "--allowedTools"):
            assert atteso in a, f"{atteso} assente: §5.2 lo richiede"

    def test_zero_tool_nel_contesto(self, t1: ClaudeT1) -> None:
        """Invariante 15: il tier vocale PARLA. Le operazioni reali passano
        dall'allowlist del core, non da qui."""
        a = t1.argv()
        assert a[a.index("--allowedTools") + 1] == ""

    def test_la_persona_e_in_append(self, t1: ClaudeT1) -> None:
        a = t1.argv()
        assert "--append-system-prompt-file" in a

    @pytest.mark.parametrize("rc,err,atteso", [
        (41, "", Uscita.AUTH),
        (1, "authentication failed", Uscita.AUTH),
        (1, "Unauthorized", Uscita.AUTH),
        (1, "killed", Uscita.TRANSIENT),
        (None, "", Uscita.PULITA),
    ])
    def test_classificazione_delle_uscite(self, t1, rc, err, atteso) -> None:
        """ADR-003. §5.6 copre solo il caso auth; gli altri farebbero ripartire
        T1 senza contesto, e JARVIS continuerebbe a parlare avendo dimenticato
        tutto senza dirlo."""
        assert t1.classifica(rc, err) is atteso

    def test_troppi_riavvii_smettono(self, t1: ClaudeT1) -> None:
        """⚠️ Il test di prima riempiva `_riavvii` con `time.time()` e passava
        **per caso**: con un orologio monotono quei valori sono enormi, la
        differenza è negativa, e cadono dentro la finestra qualunque cosa dica
        la soglia. Adesso l'orologio si muove, e si misura la soglia."""
        assert t1.classifica(1, "crash") is Uscita.TRANSIENT
        for _ in range(SOGLIA_RIPETUTI - 1):
            t1._riavvii.append(t1._orologio())
        assert t1.classifica(1, "crash") is Uscita.REPEATED

    def test_e_la_FINESTRA_dimentica(self, t1: ClaudeT1) -> None:
        """Tre riavvii in dieci minuti sono un guasto; tre in tre giorni sono
        la vita normale di un processo."""
        t1._riavvii = [t1._orologio() - FINESTRA_RIAVVII_S - 1] * 10
        assert t1.classifica(1, "crash") is Uscita.TRANSIENT

    def test_i_NUMERI_sono_quelli_che_ADR_003_dichiara(self) -> None:
        """«≥ 3 riavvii in 10 minuti». Erano `3, 300.0` con `len(...) >= 3`:
        cinque minuti invece di dieci, e la soglia al QUARTO guasto perché non
        contava quello in corso."""
        assert (SOGLIA_RIPETUTI, FINESTRA_RIAVVII_S) == (3, 600.0)

    def test_e_il_supervisore_NON_ne_ha_di_suoi(self) -> None:
        """Due coppie di numeri in due file sono due metà della stessa politica
        in disaccordo su quando smettere. Misurato prima: T1 diceva `repeated`
        al quarto guasto, il Supervisore al terzo."""
        from core.llm import supervisor

        # ⚠️ `is` e non `==`: due letterali uguali in due moduli diversi danno
        # due oggetti diversi (i float non si internano), quindi `is` vede la
        # RIDICHIARAZIONE mentre `==` la lascerebbe passare — ed è la
        # ridichiarazione il difetto, non il valore di oggi.
        assert supervisor.SOGLIA_RIPETUTI is SOGLIA_RIPETUTI
        assert supervisor.FINESTRA_RIAVVII_S is FINESTRA_RIAVVII_S

    def test_l_orologio_e_MONOTONO_e_iniettabile(self) -> None:
        """`core/llm/supervisor.py` lo vietava per iscritto da giorni: «l'ora di
        sistema può saltare all'indietro». Un salto farebbe sembrare vecchi tre
        guasti appena avvenuti, e `repeated` non scatterebbe."""
        import inspect
        import time as _t

        p = inspect.signature(ClaudeT1.__init__).parameters["orologio"]
        assert p.default is _t.monotonic


class TestRipiegoAnnunciato:
    """Invariante 12: «il fallback va sempre ANNUNCIATO, mai silenzioso»."""

    class _Finto:
        def __init__(self, nome): self.name = nome
        per_enunciato = True

    def test_il_primario_non_annuncia_nulla(self) -> None:
        from core.providers.health import scegli

        s = scegli(self._Finto("deepgram"), self._Finto("edge"), True, True, "tts")
        assert s.primario and s.annuncio is None

    @pytest.mark.parametrize("chiave,errore,atteso", [
        (False, False, "chiave"),
        (True, True, "non risponde"),
    ])
    def test_ogni_ripiego_porta_il_suo_annuncio(self, chiave, errore, atteso) -> None:
        from core.providers.health import scegli

        s = scegli(self._Finto("deepgram") if chiave else None, self._Finto("edge"),
                   chiave, True, "tts", errore_primario=errore)
        assert not s.primario
        assert s.annuncio and atteso in s.annuncio

    def test_un_ripiego_senza_annuncio_non_si_costruisce(self) -> None:
        """Reso STRUTTURALE: non e' una convenzione che il prossimo provider
        possa dimenticare."""
        from core.providers.health import Scelta

        with pytest.raises(ValueError, match="invariante 12"):
            Scelta(provider=self._Finto("x"), primario=False, motivo="y", annuncio=None)

    def test_la_pipeline_annuncia_all_avvio(self) -> None:
        from core.providers.health import scegli
        from core.voice.pipeline import VoicePipeline

        detti = []
        p = VoicePipeline(
            audio=None, wake=None,
            stt=scegli(None, self._Finto("vosk"), False, True, "stt"),
            tts=scegli(None, self._Finto("edge"), False, True, "tts"),
            su_annuncio=detti.append,
        )
        assert len(p.annuncia_ripieghi()) == 2 and len(detti) == 2


class TestChunkerSoloDoveServe:
    """§7.4: davanti a Flux il chunker aggiunge SOLO latenza."""

    def test_flux_non_vuole_il_chunker(self) -> None:
        from core.providers.tts_deepgram import DeepgramTTS

        assert DeepgramTTS("chiave-finta").per_enunciato is False

    def test_il_ripiego_lo_vuole(self) -> None:
        from core.providers.tts_local import EdgeTTS

        assert EdgeTTS().per_enunciato is True

    async def test_la_pipeline_lo_mette_solo_dove_serve(self) -> None:
        """La decisione la porta il provider, non un `if` ricordato a memoria."""
        from core.providers.base import AudioChunk
        from core.voice.pipeline import VoicePipeline
        from core.providers.health import Scelta

        visti: dict[str, list[str]] = {}

        class Tts:
            def __init__(self, per_enunciato): self.per_enunciato = per_enunciato
            name = "prova"
            async def stream(self, text):
                visti[str(self.per_enunciato)] = [t async for t in text]
                yield AudioChunk(pcm=b"\x00\x00", sample_rate=16000)
            async def interrupt(self): pass

        from tests.conftest import AudioFinto as Audio

        async def token():
            for t in ["Sono ", "operativo. ", "Tutto ", "regolare."]:
                yield t

        for per_enunciato in (True, False):
            p = VoicePipeline(audio=Audio(), wake=None,
                              stt=Scelta(Tts(True), True, "ok", None),
                              tts=Scelta(Tts(per_enunciato), True, "ok", None))
            await p.parla(token())

        assert len(visti["True"]) < len(visti["False"]), (
            "il chunker non ha aggregato davanti al TTS a enunciato, "
            "oppure ha aggregato davanti a Flux"
        )


class TestVAD:
    def test_il_silenzio_non_sveglia(self) -> None:
        from core.voice.pipeline import VAD

        assert VAD().parla(b"\x00\x00" * 512) is False

    def test_il_parlato_apre_il_gate(self) -> None:
        from core.platform.linux_audio import tono
        from core.voice.pipeline import VAD

        assert VAD().parla(tono()[:2048]) is True

    def test_isteresi_non_chiude_al_primo_respiro(self) -> None:
        """Una soglia secca taglierebbe le parole a meta'."""
        from core.platform.linux_audio import tono
        from core.voice.pipeline import VAD

        v = VAD()
        v.parla(tono()[:2048])
        for _ in range(3):
            assert v.parla(b"\x00\x00" * 512) is True, "chiuso troppo presto"
