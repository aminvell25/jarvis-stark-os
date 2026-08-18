"""Voce: chunker, wake, audio, T1 — SPEC §7."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.llm.claude_t1 import ClaudeT1, Uscita
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
        import time

        t1._riavvii = [time.time()] * 3
        assert t1.classifica(1, "crash") is Uscita.REPEATED
