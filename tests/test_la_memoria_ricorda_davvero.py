"""`topics/` e `initiatives/` erano a zero file, e non per caso.

Misurato il 27 agosto, su un sistema che gira da giorni:

    ~/.local/share/jarvis-os/memory_data/
      sessions/     2 file      ← la cronologia grezza, funziona
      conso/        2 file      ← i secondi di audio, funziona
      topics/       0 file      ← la memoria a lungo termine
      initiatives/  0 file      ← ciò che JARVIS ha fatto di sua iniziativa

`registra_iniziativa` ha **un solo chiamante** in produzione: il consolidamento
notturno. Cioè l'unica iniziativa che il sistema sappia prendere è mettere in
ordine i propri appunti — e non l'aveva **mai** fatto.

Nel journal di sette giorni c'è solo `grado_acceso grado=consolidamento ora=4`,
cioè il timer **armato**. Mai uno scatto. Il motivo è misurato: **il core si è
riavviato 27 volte in tre giorni**, e un `await asyncio.sleep()` fino alle 04:00
non sopravvive a un riavvio del processo — riparte da zero, ogni volta.

> La metà in uscita della memoria era vuota per un difetto di forma:
> **un'attesa invece di un recupero.**
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


def _conso(tmp_path: Path):
    from core.memory.consolidate import Consolidatore
    from core.memory.store import MemoryStore

    return Consolidatore(MemoryStore(tmp_path), None)


class TestUnaNotteSaltataSiVEDE:
    def test_mai_consolidato_conta_come_saltato(self, tmp_path: Path) -> None:
        """Il caso di oggi: nessun timbro, sessioni sul disco da due giorni."""
        assert _conso(tmp_path).saltato() is True

    def test_appena_fatto_NON_conta(self, tmp_path: Path) -> None:
        c = _conso(tmp_path)
        c._segna_run()
        assert c.saltato() is False

    def test_il_confine_e_UN_GIORNO_e_non_e_scelto(self, tmp_path: Path) -> None:
        """§5.5 dice «ogni notte», quindi il periodo è un giorno. Se qualcuno
        cambiasse `PERIODO_S`, questo test lo dice."""
        from core.memory.consolidate import PERIODO_S

        assert PERIODO_S == 24 * 3600.0
        c = _conso(tmp_path)
        c._segna_run()
        ora = time.time()
        assert c.saltato(adesso=ora + PERIODO_S - 60) is False
        assert c.saltato(adesso=ora + PERIODO_S + 60) is True

    def test_un_timbro_nel_FUTURO_non_e_saltato(self, tmp_path: Path) -> None:
        """Orologio spostato all'indietro, fuso cambiato: non si consolida due
        volte per un orologio storto.

        ⚠️ **E lo dice l'aritmetica, non una guardia.** Avevo scritto un
        `if ultimo <= ora else False`; la bocciatura ha mostrato che toglierlo
        non rompeva nulla — la differenza è negativa e non può superare
        `PERIODO_S`. Un controllo che non cambia nessun esito promette a chi
        legge una protezione che non c'è, e va tolto.
        """
        c = _conso(tmp_path)
        (tmp_path / "_ultimo-consolidamento.txt").write_text(str(time.time() + 9999))
        assert c.saltato() is False
        assert "if ultimo <= ora" not in _sorgente("core/memory/consolidate.py")

    def test_usa_l_orologio_di_PARETE_non_monotonic(self) -> None:
        """`monotonic` riparte a ogni riavvio del processo — cioè proprio nel
        caso che `saltato()` esiste per coprire."""
        s = _sorgente("core/memory/consolidate.py")
        dopo = s.split("def saltato", 1)[1].split("\n    def ", 1)[0]
        # ⚠️ Via anche la DOCSTRING, non solo i `#`: la spiegazione qui sopra
        # nomina `monotonic` per dire perché NON si usa, e un test che cercasse
        # la stringa nuda sarebbe rosso per il commento invece che per il
        # codice. È la sesta volta in questo progetto.
        codice = _senza_commenti(dopo.split('"""', 2)[-1])
        assert "time.time()" in codice and "monotonic" not in codice


class TestIlMotoreRECUPERAinveceDiAspettare:
    def test_il_recupero_c_e_ed_e_PRIMA_del_ciclo(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("Consolidatore(self._memoria, self._t2_conso,", 1)[1]
        prima_del_ciclo = dopo.split("while True:", 1)[0]
        assert "conso.saltato()" in prima_del_ciclo, (
            "il recupero sta dopo il `while True`, cioè dopo il primo sonno "
            "fino alle 04:00: non recupererebbe niente"
        )
        assert "await conso.esegui()" in prima_del_ciclo

    def test_e_NON_solleva(self) -> None:
        """Siamo in un compito di sfondo: un'eccezione qui finirebbe in un
        `Task` che nessuno guarda, e il ciclo notturno non partirebbe mai."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("if conso.saltato():", 1)[1].split("while True:", 1)[0]
        assert "try:" in dopo and "except Exception" in dopo

    def test_il_ciclo_notturno_RESTA(self) -> None:
        """Il recupero non lo sostituisce: chi lascia la macchina accesa deve
        avere il consolidamento alle 04:00, non al riavvio successivo."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("Consolidatore(self._memoria, self._t2_conso,", 1)[1]
        assert "self._secondi_fino_alle(ORA_DEFAULT)" in dopo

    def test_il_timbro_si_scrive_ANCHE_a_vuoto(self) -> None:
        """⚠️ È ciò che impedisce a un riavvio ogni dieci minuti di consolidare
        ogni dieci minuti. Il freno è su disco, non in memoria: un contatore in
        memoria si azzererebbe col processo, cioè con lo stesso difetto."""
        s = _senza_commenti(_sorgente("core/memory/consolidate.py"))
        dopo = s.split("if not da_fare:", 1)[1].split("return", 1)[0]
        assert "self._segna_run()" in dopo


class TestIDueT2ESISTONOdavvero:
    """⚠️ **La strada c'era e finiva su un null.**

    `Engine.__init__` costruiva `_t2_meta` e `_t2_conso` e poi li **azzerava
    centoquaranta righe dopo, nella stessa funzione**. Il commento diceva
    «costruito nella radice di composizione, non qui»: era vero prima che la
    composizione venisse spostata dentro `__init__`, e nessuno ha tolto
    l'azzeramento.

    Conseguenza: `_meta_comando` si arrendeva alla prima riga con «T2 non
    composto», quindi **`brief_me` e `needs_attention` non hanno mai potuto
    spawnare nulla — dal commit che li ha collegati** (`92c0ec4`, «nessun
    intento senza strada»).

    Trovato perché il recupero del consolidamento è caduto su `_t2_conso`, che
    era finito nella stessa trappola il giorno stesso.
    """

    def test_nessuno_dei_due_e_None_dopo_la_costruzione(self, short_paths) -> None:
        from core.engine import Engine

        e = Engine(short_paths)
        assert e._t2_meta is not None, (
            "`brief_me` risponderebbe «T2 non composto» per sempre"
        )
        assert e._t2_conso is not None, (
            "il consolidamento cadrebbe su AttributeError a ogni recupero"
        )

    def test_e_hanno_mani_DIVERSE(self, short_paths) -> None:
        """La distinzione del cancello 0 deve sopravvivere alla correzione."""
        from core.engine import Engine

        e = Engine(short_paths)
        assert e._t2_conso._tool == ""
        assert e._t2_meta._tool != ""

    def test_l_azzeramento_non_torna(self) -> None:
        import inspect

        from core.engine import Engine

        src = inspect.getsource(Engine.__init__)
        righe = [r.strip() for r in src.splitlines()]
        assert "self._t2_meta = None" not in righe
        assert "self._t2_conso = None" not in righe


class TestIlMotivoSOPRAVVIVE:
    def test_il_dettaglio_finisce_anche_nel_JOURNAL(self) -> None:
        """⚠️ Il `dettaglio` andava solo sull'advisory, che vive sul socket.
        Con la scrivania non collegata il motivo spariva — ed è sparito davvero
        il 27 agosto: «sessione 2026-08-27 non consolidata», e nessuno può più
        dire perché."""
        s = _senza_commenti(_sorgente("core/memory/consolidate.py"))
        assert 'log.warning("consolidamento_advisory", motivo=motivo, **extra)' in s

    def test_e_l_advisory_lo_porta_ancora_alla_UI(self) -> None:
        """Le due destinazioni sono due, non una al posto dell'altra."""
        s = _senza_commenti(_sorgente("core/memory/consolidate.py"))
        dopo = s.split("def _advisory", 1)[1].split("\n    async def ", 1)[0]
        assert "**extra}" in dopo and "self._su_advisory(msg)" in dopo
