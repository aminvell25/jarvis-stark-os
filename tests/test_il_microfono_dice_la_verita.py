"""Due sordità silenziose, misurate — §16, §3.2.

Il 26 agosto 2026, in una sessione sola:

- il ciclo del microfono è rimasto **fermo un'ora** con `pw-record` bloccato in
  `anon_pipe_write` — pipe piena, nessuno legge — mentre lo snapshot diceva
  `microfono: aperto`. Chi parlava parlava nel vuoto, e l'unico modo di
  accorgersene è stato dirlo a voce;
- la scrivania è rimasta **scollegata dodici minuti** dopo un riavvio del core,
  con la finestra viva e vuota, mentre il diario si riempiva su disco.

Nessuno dei due si è annunciato. Sono la stessa famiglia: uno stato riferito che
non è lo stato vero.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent


def _engine() -> str:
    return (RADICE / "core" / "engine.py").read_text(encoding="utf-8")


def senza_commenti(sorgente: str) -> str:
    """Il codice, senza commenti — e serve piu' di quanto sembri.

    ⚠️ **Quattro volte in questa sessione** un mio test ha pescato un commento
    invece del codice: `esegui_t0` nominato in un docstring che spiega perche'
    non ci passa, `self._vad` idem, `&#8862;` scambiato per un colore, e
    `new WebSocket` dentro la spiegazione del difetto che stava sopra la riga
    vera. Un test che legge un sorgente deve leggere il **codice**, e questa e'
    la riga che lo garantisce una volta per tutte.
    """
    import re

    s = re.sub(r"/\*.*?\*/", "", sorgente, flags=re.S)     # blocchi C
    s = re.sub(r'^\s*#.*$', "", s, flags=re.M)              # righe Python
    return re.sub(r"^\s*//.*$", "", s, flags=re.M)          # righe JS


class TestIlBattitoDelMicrofono:
    def _pipeline(self):
        from core.voice.pipeline import VoicePipeline

        p = VoicePipeline.__new__(VoicePipeline)
        p._ultimo_blocco = 0.0
        p._in_turno = False
        return p

    def test_prima_di_partire_e_None_non_zero(self) -> None:
        """`None` è «non è mai partito», `0.0` è «arrivato adesso»: sono due
        cose diverse e confonderle produrrebbe un allarme all'avvio."""
        assert self._pipeline().muto_da() is None

    def test_conta_i_secondi_dall_ultimo_blocco(self) -> None:
        p = self._pipeline()
        p._ultimo_blocco = 100.0
        assert p.muto_da(adesso=107.5) == pytest.approx(7.5)

    def test_durante_un_TURNO_non_e_muto(self) -> None:
        """Il ciclo non legge mentre serve un turno — `_su_trigger` è atteso
        dentro il `async for` — e un turno può durare fino al timeout di T1.
        Chiamarlo «muto» sarebbe una diagnosi sbagliata di un funzionamento
        corretto."""
        p = self._pipeline()
        p._ultimo_blocco = 100.0
        p._in_turno = True
        assert p.muto_da(adesso=180.0) == 0.0

    def test_il_ciclo_TIMBRA_ogni_blocco(self) -> None:
        s = (RADICE / "core" / "voice" / "pipeline.py").read_text(encoding="utf-8")
        dopo = s.split("async for blocco in dal_microfono", 1)[1][:600]
        assert "self._ultimo_blocco = time.monotonic()" in dopo

    def test_e_la_bandiera_del_turno_si_abbassa_SEMPRE(self) -> None:
        """Anche se il turno cade: una bandiera che resta alzata renderebbe il
        battito cieco per sempre — cioè il difetto di prima, con un nome
        nuovo."""
        s = (RADICE / "core" / "voice" / "pipeline.py").read_text(encoding="utf-8")
        dopo = s.split("self._in_turno = True", 1)[1][:1400]
        assert "finally:" in dopo and "self._in_turno = False" in dopo


class TestLoSnapshotDiceLaVERITA:
    def test_la_soglia_viene_dal_periodo_dei_BLOCCHI(self) -> None:
        """20 ms l'uno: cinque secondi sono duecentocinquanta blocchi mancati,
        cioè «rotto», non «la macchina è occupata»."""
        from core.engine import SILENZIO_SOSPETTO_S

        assert SILENZIO_SOSPETTO_S == 5.0
        assert SILENZIO_SOSPETTO_S / 0.020 == 250

    def test_muto_non_si_chiama_piu_APERTO(self) -> None:
        s = _engine()
        dopo = s.split("def _stato_microfono", 1)[1].split("\n    def ", 1)[0]
        assert "muto da" in dopo
        assert "self._voce.muto_da()" in dopo

    def test_e_la_soglia_ANNUNCIA(self) -> None:
        """§16: nessuna soglia agisce senza annunciarlo. Questa non c'era, e
        l'ora di sordità è passata senza una riga."""
        s = _engine()
        assert "self._controlla_microfono()" in s
        dopo = s.split("def _controlla_microfono", 1)[1].split("\n    def ", 1)[0]
        assert '"microfono_muto"' in dopo and '"microfono_tornato"' in dopo

    def test_sul_CAMBIO_e_non_a_2_5_Hz(self) -> None:
        """Lo snapshot gira a 2,5 Hz: un advisory ogni 400 ms sarebbe rumore."""
        s = _engine()
        dopo = s.split("def _controlla_microfono", 1)[1].split("\n    def ", 1)[0]
        assert "if sospetto == self._microfono_sospetto:" in dopo
        assert "return" in dopo


class TestIlPonteRIPROVA:
    """La scrivania non tornava dopo un riavvio del core."""

    def test_il_costruttore_e_dentro_un_try(self) -> None:
        """`riprova()` programma `collega()` con un timer. Se il socket non
        esiste nell'istante del tentativo — cioè ESATTAMENTE la finestra in cui
        il core si riavvia — `new WebSocket` solleva in modo sincrono,
        l'eccezione esce dal callback, e **nessuno programma il tentativo
        successivo**."""
        s = senza_commenti((RADICE / "app" / "main.js").read_text(encoding="utf-8"))
        dopo = s.split("function collega()", 1)[1].split("function riprova", 1)[0]
        assert "try {" in dopo
        i = dopo.index("try {")
        assert dopo.index("new WebSocket") > i, "il costruttore è fuori dal try"
        assert "riprova(" in dopo[i:], "il catch non riprogramma il tentativo"

    def test_e_il_ritardo_non_si_arrende_MAI(self) -> None:
        """Un tetto al numero di tentativi trasformerebbe un riavvio lungo in
        una scrivania morta."""
        s = (RADICE / "app" / "main.js").read_text(encoding="utf-8")
        assert "Math.min(250 * 2 ** Math.min(tentativi, 5), 5000)" in s
        assert "tentativi >" not in s, "esiste un tetto ai tentativi"
