"""Una radice consentita non può contenere lo stato di JARVIS.

Il 27 agosto la workspace è passata da `~/JARVIS` a
`~/.local/share/jarvis-os/workspace` — cioè **dentro** la cartella in cui vivono
`memory_data/`, `layout.json`, i modelli Vosk e la sessione di T1.

Oggi è una **sorella** di `memory_data/` e non c'è guaio. Ma basta scrivere

    workspace = "~/.local/share/jarvis-os"

— una riga plausibile, e persino comoda — perché `trash_path` possa cestinare la
memoria di JARVIS con una conferma sola, e `organize_folder` riordinargli i
ricordi per tipo di file.

La radice si **toglie**, e si dice. Togliere è fail-closed: JARVIS perde una
cartella su cui lavorare, non la propria memoria.
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _engine(short_paths):
    from core.engine import Engine

    return Engine(short_paths)


class TestLaRadiceCheContieneLoStatoSiTOGLIE:
    def test_una_SORELLA_dello_stato_resta(self, short_paths) -> None:
        """`.../jarvis-os/workspace` non contiene `.../jarvis-os/memory_data`:
        è accanto. Toglierla sarebbe togliere la workspace a JARVIS."""
        e = _engine(short_paths)
        dentro = e._paths.data_dir() / "workspace"
        s = e._store.current
        e._store._current = s.model_copy(update={"fs": s.fs.model_copy(
            update={"allowed_roots": [dentro]})})
        assert dentro in e._radici_sicure().fs.allowed_roots

    def test_la_cartella_dello_STATO_si_toglie(self, short_paths) -> None:
        e = _engine(short_paths)
        stato = e._paths.data_dir()
        s = e._store.current
        e._store._current = s.model_copy(update={"fs": s.fs.model_copy(
            update={"allowed_roots": [stato, Path("/usr/share")]})})
        rimaste = e._radici_sicure().fs.allowed_roots
        assert stato not in rimaste
        # ⚠️ Non `/tmp`: nella fixture lo stato vive SOTTO `/tmp`, quindi `/tmp`
        # lo contiene davvero e la regola lo toglie — giustamente. Ci sono
        # cascato scrivendo questo test, ed e' la prova che la regola guarda i
        # percorsi veri e non i nomi.
        assert Path("/usr/share") in rimaste, "ha tolto anche le radici innocenti"

    def test_e_un_ANTENATO_pure(self, short_paths) -> None:
        """La home intera come radice consentita è la stessa cosa, in grande."""
        e = _engine(short_paths)
        s = e._store.current
        e._store._current = s.model_copy(update={"fs": s.fs.model_copy(
            update={"allowed_roots": [e._paths.data_dir().parent.parent]})})
        assert e._radici_sicure().fs.allowed_roots == []

    def test_e_lo_DICE(self, short_paths) -> None:
        """⚠️ Una radice tolta in silenzio è un tool che non funziona senza una
        ragione da leggere: chi ha scritto quella riga deve sapere perché."""
        from structlog.testing import capture_logs

        e = _engine(short_paths)
        s = e._store.current
        e._store._current = s.model_copy(update={"fs": s.fs.model_copy(
            update={"allowed_roots": [e._paths.data_dir()]})})
        with capture_logs() as righe:
            e._radici_sicure()
        detti = [r for r in righe if r["event"] == "radice_tolta"]
        assert len(detti) == 1 and detti[0]["log_level"] == "error"

    def test_senza_niente_da_togliere_NON_dice_niente(self, short_paths) -> None:
        """Un allarme che suona sempre si spegne."""
        from structlog.testing import capture_logs

        e = _engine(short_paths)
        with capture_logs() as righe:
            e._radici_sicure()
        assert not [r for r in righe if r["event"] == "radice_tolta"]


class TestIToolLoRICEVONO:
    def test_register_file_tools_prende_il_FILTRO(self) -> None:
        """Non `self._store.current`: altrimenti il filtro esiste e non filtra."""
        s = (RADICE / "core" / "engine.py").read_text(encoding="utf-8")
        assert "register_file_tools(self._radici_sicure," in s
        assert "register_file_tools(lambda: self._store.current," not in s

    def test_e_si_rilegge_a_ogni_uso(self) -> None:
        """`register_file_tools` prende una FUNZIONE apposta: le radici si
        ricaricano a caldo, e un elenco fissato all'avvio non seguirebbe una
        correzione del file."""
        s = (RADICE / "core" / "tools" / "files.py").read_text(encoding="utf-8")
        assert "def radici()" in s or "leggi_settings()" in s
