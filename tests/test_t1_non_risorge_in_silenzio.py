"""T1 moriva e rinasceva vuoto, e JARVIS rispondeva come se niente fosse.

`ClaudeT1.ask()` conteneva, dentro il `try`:

    if not self.vivo:
        await self.start()

Il processo di T1 muore — OOM, crash, stream desincronizzato — e la chiamata
successiva ne apre uno **nuovo con la sessione vuota**. JARVIS risponde con la
stessa voce avendo perso la conversazione, **senza dirlo**.

`docs/acceptance/ADR-003-LAMNESIA-SI-ANNUNCIA.md` lo chiama testualmente *«il
modo di fallire peggiore che questo sistema possa avere»*, e la funzione che lo
fa bene — `riavvia_dopo_guasto`, che reinietta i soli fatti fissati e **annuncia**
— non aveva un solo chiamante in produzione.

L'ha trovata `scripts/orfani.py`, rimesso nel repo lo stesso giorno.

## Le due maniere di non essere vivo

    `_proc is None`         mai avviato, o fermato di proposito da `stop()`:
                            si avvia e basta, non c'è niente da annunciare
    returncode non nullo    è MORTO da solo: si passa da `riavvia_dopo_guasto`

Confonderle vorrebbe dire annunciare un'amnesia a ogni avvio del core.
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


class _ProcMorto:
    """Un processo che è morto: `returncode` c'è, e non è zero."""

    def __init__(self, returncode: int = 137) -> None:
        self.returncode = returncode
        self.pid = 4242


def _t1(**kw):
    from core.llm.claude_t1 import ClaudeT1

    return ClaudeT1("haiku", Path("/tmp"), **kw)


class TestUnProcessoMORTOnonSiRiavviaInSilenzio:
    async def test_ask_passa_da_riavvia_dopo_guasto(self) -> None:
        t1 = _t1()
        t1._proc = _ProcMorto()
        passato: list[str] = []

        async def finto():
            passato.append("riavvio")
            from core.llm.claude_t1 import Uscita

            return Uscita.TRANSIENT

        t1.riavvia_dopo_guasto = finto

        async def start_finto():
            passato.append("start")

        t1.start = start_finto
        try:
            async for _ in t1.ask("ciao"):
                pass
        except Exception:
            pass
        assert "riavvio" in passato, (
            "il processo morto e' stato rimpiazzato senza passare da ADR-003"
        )

    async def test_e_un_processo_MAI_AVVIATO_no(self) -> None:
        """Confondere le due vorrebbe dire annunciare un'amnesia a ogni avvio
        del core."""
        t1 = _t1()
        assert t1._proc is None
        passato: list[str] = []

        async def finto():                     # pragma: no cover
            passato.append("riavvio")
            raise AssertionError("non c'era niente da riavviare")

        t1.riavvia_dopo_guasto = finto

        async def start_finto():
            passato.append("start")

        t1.start = start_finto
        try:
            async for _ in t1.ask("ciao"):
                pass
        except Exception:
            pass
        assert passato == ["start"]

    async def test_degradato_SOLLEVA_invece_di_rispondere(self) -> None:
        """⚠️ Rispondere dopo una degradazione sarebbe esattamente la bugia che
        questo blocco esiste per impedire: `_degrada` ha già annunciato, e una
        risposta dopo l'annuncio direbbe che va tutto bene."""
        import pytest

        from core.llm.claude_t1 import Uscita

        t1 = _t1()
        t1._proc = _ProcMorto()

        async def degradato():
            return Uscita.AUTH

        t1.riavvia_dopo_guasto = degradato
        with pytest.raises(RuntimeError, match="degradato"):
            async for _ in t1.ask("ciao"):
                pass

    async def test_sta_PRIMA_della_bandiera_di_occupato(self) -> None:
        """⚠️ `riavvia_dopo_guasto` usa `ask()` per reiniettare i fatti: a
        bandiera già alzata la rientranza solleverebbe «T1 è già impegnato»,
        cioè la correzione dell'amnesia diventerebbe un turno perso."""
        t1 = _t1()
        t1._proc = _ProcMorto()
        visto: list[bool] = []

        async def guarda():
            visto.append(t1._occupato)
            from core.llm.claude_t1 import Uscita

            return Uscita.TRANSIENT

        t1.riavvia_dopo_guasto = guarda

        async def start_finto():
            return

        t1.start = start_finto
        try:
            async for _ in t1.ask("ciao"):
                pass
        except Exception:
            pass
        assert visto == [False], "la bandiera era gia' alzata: rientranza"


class TestIlRiavvioFaCioCheADR003CHIEDE:
    def test_reinietta_i_SOLI_fatti_fissati(self) -> None:
        """Mai i turni: l'invariante 17 vieta di duplicare la gestione del
        contesto di T1, e riprodurre la conversazione darebbe due gestori in
        disaccordo."""
        s = (RADICE / "core" / "llm" / "claude_t1.py").read_text(encoding="utf-8")
        corpo = s.split("async def riavvia_dopo_guasto", 1)[1].split(
            "\n    async def ", 1)[0]
        assert "self._fatti_fissati()" in corpo
        assert "turni" not in corpo.split('"""', 2)[-1]

    def test_e_ANNUNCIA_sempre(self) -> None:
        """L'annuncio non è facoltativo: §16 dice «nessuna soglia agisce senza
        annunciarlo», e un'amnesia taciuta è la soglia peggiore."""
        s = (RADICE / "core" / "llm" / "claude_t1.py").read_text(encoding="utf-8")
        corpo = s.split("async def riavvia_dopo_guasto", 1)[1].split(
            "\n    async def ", 1)[0]
        assert "_degrada(Uscita.TRANSIENT)" in corpo

    def test_non_e_piu_un_ORFANO(self) -> None:
        """La prova che la giunzione esiste: prima compariva solo nei test e in
        due commenti."""
        s = (RADICE / "core" / "llm" / "claude_t1.py").read_text(encoding="utf-8")
        codice = "\n".join(r.split("#", 1)[0] for r in s.splitlines())
        assert codice.count("riavvia_dopo_guasto") >= 2, (
            "definita e mai chiamata: e' di nuovo un orfano"
        )
