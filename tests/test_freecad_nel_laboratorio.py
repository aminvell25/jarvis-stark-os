"""ADR-015, decisione 4: FreeCAD headless nel laboratorio, come binario nel
profilo — e sulla macchina del proprietario e' un snap.

`snap run` dentro bubblewrap muore su DBus (misurato). Si esegue il binario
del snap con il base snap come radice, il snap e i suoi content montati dove
il manifesto li vuole, e l'ambiente letto da `meta/snap.yaml`. Qui si prova:
il lettore del manifesto (sul snap vero, se c'e'), la forma dell'argv, e —
dal vivo — uno script FreeCAD che scrive STL e STEP nella bozza, verificati.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest

from core.platform.linux_snap import (RADICE_SNAP, SnapNonTrovato, _espandi,
                                      interprete_freecad, snap_di, trova_snap)
from core.sandbox.policy import SandboxPolicyError
from core.sandbox.runner import Profilo
from core.tools import registry
from core.tools.laboratorio import (BOZZE, MANIFESTO, InterpreteNonDisponibile,
                                    Laboratorio, Manifesto, StepIllegibile,
                                    compito_per_t2, leggi_step)
from core.verifica import Verdetto
from tests.test_laboratorio import _Impostazioni, _approva, _bozza, _invoca, _registra

FREECAD = interprete_freecad()
CON_FREECAD = pytest.mark.skipif(FREECAD is None, reason="il snap freecad non c'e'")
BWRAP = pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap non disponibile")

#: Una piastra 30x20x5 con un foro passante: STL e STEP con il solo `Part`.
PIASTRA = """\
import FreeCAD, Part
box = Part.makeBox(30, 20, 5)
foro = Part.makeCylinder(2.0, 10, FreeCAD.Vector(15, 10, -2))
pezzo = box.cut(foro)
assert pezzo.isValid()
print("volume", round(pezzo.Volume, 2))
pezzo.exportStl("piastra.stl")
pezzo.exportStep("piastra.step")
"""


@pytest.fixture(autouse=True)
def _pulisci():
    registry.clear()
    yield
    registry.set_confirm_hook(None)
    registry.clear()


@pytest.fixture
def radice(tmp_path: Path) -> Path:
    r = tmp_path / "laboratorio"
    r.mkdir()
    return r


class TestIlManifestoDelSnap:
    def test_espandi_non_tronca_le_variabili_lunghe(self) -> None:
        """`$SNAP` dentro `$SNAP_USER_COMMON`: la prima stesura dava
        `/snap/x/1_USER_COMMON`. Un passaggio per nome intero."""
        r = Path("/snap/x/1")
        assert _espandi("$SNAP_USER_COMMON/.local", r, {}) == "/tmp/.local"
        assert _espandi("$SNAP/usr/lib:$SNAP/kf6/usr/lib:$LD_LIBRARY_PATH", r, {}) == (
            "/snap/x/1/usr/lib:/snap/x/1/kf6/usr/lib")
        assert _espandi("$PYTHONUSERBASE/lib", r, {"PYTHONUSERBASE": "/tmp/.local"}) == "/tmp/.local/lib"

    def test_snap_di_riconosce_solo_cio_che_sta_sotto_snap(self) -> None:
        assert snap_di(Path("/usr/bin/python3")) is None
        assert snap_di(Path(sys.executable)) is None

    def test_un_comando_fuori_dai_snap_e_rifiutato(self) -> None:
        with pytest.raises(SnapNonTrovato):
            trova_snap(Path("/usr/bin/python3"))

    @CON_FREECAD
    def test_il_snap_vero_si_legge(self) -> None:
        s = trova_snap(FREECAD)
        assert s.nome == "freecad" and s.radice.parent == RADICE_SNAP / "freecad"
        assert s.base.is_dir() and (s.base / "usr" / "lib").is_dir()
        assert s.comando == (s.radice / "usr" / "bin" / "FreeCADCmd").resolve()
        # Le quattro che bastano — misurato — ci sono, e senza `$SNAP` residui.
        for chiave in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PATH", "SNAP"):
            assert chiave in s.ambiente and "$" not in s.ambiente[chiave]
        assert s.ambiente["SNAP"] == str(s.radice)
        # Le case nel manifesto puntano a `/tmp`, mai alla home vera.
        for valore in s.ambiente.values():
            assert not valore.startswith("/home/")
        # Il content snap di Qt (kf6) e' fra i montaggi, una volta sola.
        destinazioni = [d for _, d in s.contenuti]
        assert s.radice / "kf6" in destinazioni
        assert len(destinazioni) == len(set(destinazioni))


class TestIlProfiloPerUnSnap:
    @CON_FREECAD
    def test_l_argv_ha_il_base_come_radice_e_nessuna_libreria_dell_host(self, radice: Path) -> None:
        from core.platform.linux_sandbox import build_argv

        b = radice / "b"
        b.mkdir()
        a = build_argv([str(FREECAD), "genera.py"], [b], [radice], Profilo.LABORATORIO,
                       chdir=b, lavoro_mb=8)
        s = trova_snap(FREECAD)
        i = a.index("--ro-bind")
        assert a[i + 1:i + 3] == [str(s.base), "/"], "la radice e' il base snap"
        assert "/usr/lib" not in [a[j + 1] for j, x in enumerate(a) if x == "--ro-bind"]
        assert "--share-net" not in a and "--unshare-all" in a
        assert a.count("--bind") == 1 and a[a.index("--bind") + 1] == str(b.resolve())
        assert a[a.index("--size") + 2:a.index("--size") + 4] == ["--tmpfs", "/tmp"]
        assert str(RADICE_SNAP) in [a[j + 1] for j, x in enumerate(a) if x == "--tmpfs"]
        env = {a[j + 1]: a[j + 2] for j, x in enumerate(a) if x == "--setenv"}
        assert env["HOME"] == "/tmp" and env["SNAP"] == str(s.radice)
        assert "LD_LIBRARY_PATH" in env and "--clearenv" in a
        assert a[-2:] == [str(FREECAD), "genera.py"]

    def test_un_binario_sotto_snap_senza_manifesto_e_rifiutato(self, radice: Path, tmp_path: Path,
                                                              monkeypatch) -> None:
        from core.platform import linux_sandbox
        from core.platform import linux_snap

        finto = tmp_path / "snap" / "x" / "1" / "bin"
        finto.mkdir(parents=True)
        (finto / "cmd").write_text("")
        monkeypatch.setattr(linux_snap, "RADICE_SNAP", tmp_path / "snap")
        monkeypatch.setattr(linux_sandbox, "RADICE_SNAP", tmp_path / "snap")
        b = radice / "b"
        b.mkdir()
        with pytest.raises(SandboxPolicyError, match="snap.yaml"):
            linux_sandbox.build_argv([str(finto / "cmd"), "x.py"], [b], [radice], Profilo.LABORATORIO)


class TestIlManifestoDellaBozza:
    def test_l_interprete_e_un_allowlist(self) -> None:
        assert Manifesto(produce=["a.stl"]).interprete == "python"
        assert Manifesto(produce=["a.step"], interprete="freecad").interprete == "freecad"
        with pytest.raises(ValueError):
            Manifesto(produce=["a.stl"], interprete="blender")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            Manifesto(produce=["a.stl"], interprete="/snap/bin/freecad")  # type: ignore[arg-type]

    def test_senza_freecad_il_piano_lo_dice_prima_della_conferma(self, radice: Path, monkeypatch) -> None:
        import core.platform as piattaforma

        monkeypatch.setattr(piattaforma, "interprete_freecad", lambda: None)
        with pytest.raises(InterpreteNonDisponibile, match="non c'e'"):
            Laboratorio.interprete_per("freecad", "genera.py")
        _registra(radice)
        b = _bozza(radice, "cad", script="print(1)\n", produce=["a.stl"], manifesto=False)
        (b / MANIFESTO).write_text(json.dumps({"script": "genera.py", "produce": ["a.stl"],
                                               "interprete": "freecad"}))
        stato = _approva()
        r = _invoca("cad")
        assert not r.ok and "FreeCAD" in r.error and stato["piani"] == []

    def test_il_prompt_dice_se_freecad_c_e(self, monkeypatch) -> None:
        import core.platform as piattaforma

        monkeypatch.setattr(piattaforma, "interprete_freecad", lambda: Path("/snap/x"))
        assert "FreeCAD headless E' disponibile" in compito_per_t2("x", Path("/b"))
        monkeypatch.setattr(piattaforma, "interprete_freecad", lambda: None)
        assert "FreeCAD NON e' disponibile" in compito_per_t2("x", Path("/b"))


class TestIlLettoreStep:
    def test_intestazione_e_chiusura(self, tmp_path: Path) -> None:
        p = tmp_path / "a.step"
        p.write_bytes(b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
        assert leggi_step(p) == p.stat().st_size
        p.write_bytes(b"solid x\n")
        with pytest.raises(StepIllegibile, match="non comincia"):
            leggi_step(p)
        p.write_bytes(b"ISO-10303-21;\nHEADER;\n")
        with pytest.raises(StepIllegibile, match="non finisce"):
            leggi_step(p)


@CON_FREECAD
@BWRAP
class TestDalVivoConFreeCAD:
    def _bozza_freecad(self, radice: Path, nome: str = "piastra", script: str = PIASTRA,
                       produce: list[str] | None = None) -> Path:
        b = _bozza(radice, nome, script=script, produce=produce or ["piastra.stl", "piastra.step"],
                   manifesto=False)
        (b / MANIFESTO).write_text(json.dumps({
            "script": "genera.py", "produce": produce or ["piastra.stl", "piastra.step"],
            "richiesta": "una piastra forata", "interprete": "freecad"}))
        return b

    def test_freecad_scrive_stl_e_step_nella_bozza_e_il_verificatore_li_rilegge(
            self, radice: Path) -> None:
        ricevuti: list[dict] = []

        async def pubblica(msg: dict) -> None:
            ricevuti.append(msg)

        _registra(radice, pubblica=pubblica, max_timeout_s=120.0)
        b = self._bozza_freecad(radice)
        stato = _approva()
        r = _invoca("piastra", timeout_s=120.0)
        assert r.ok, r.error
        [piano] = stato["piani"]
        assert "(freecad)" in piano.riepilogo
        assert piano.operazioni[0].dettaglio.startswith(str(FREECAD))
        assert "runpy.run_path" in piano.operazioni[0].dettaglio
        assert "base snap di FreeCAD" in piano.operazioni[1].dettaglio
        assert sorted(r.output["prodotti"]) == ["piastra.step", "piastra.stl"]
        # FreeCAD scrive STL ASCII: il lettore lo rilegge lo stesso, e lo dice.
        assert r.output["misure"]["piastra.stl"]["bbox_mm"] == [30.0, 20.0, 5.0]
        from core.model3d import stl_lettore
        assert stl_lettore.leggi(b / "piastra.stl").formato == "ascii"
        assert r.output["misure"]["piastra.step"]["formato"] == "STEP"
        assert "volume 2937.17" in r.output["stdout"]
        assert r.verifica.verdetto == Verdetto.RIUSCITO
        assert "ISO 10303-21" in r.verifica.fonte
        # L'anteprima e' lo STL (unificato dai vertici ASCII); lo STEP non si mostra.
        assert r.output["anteprima"].startswith("piastra.stl:")
        [m] = ricevuti
        assert m["file"].endswith("piastra.stl") and m["bbox"] == {"x": 30.0, "y": 20.0, "z": 5.0}

    def test_uno_script_col_main_guard_gira_davvero(self, radice: Path) -> None:
        """FreeCADCmd da' a un file `__name__ == "<nome del file>"`: la staffa
        di opus, con `if __name__ == "__main__"`, era uscita con 0 senza
        scrivere niente. Con `runpy` il main guard scatta, e si vede."""
        _registra(radice, max_timeout_s=120.0)
        self._bozza_freecad(radice, "guardata", produce=["g.stl"], script="""\
import Part
def main():
    Part.makeBox(4, 3, 2).exportStl("g.stl")
    print("MAIN eseguito")
if __name__ == "__main__":
    main()
""")
        _approva()
        r = _invoca("guardata", timeout_s=120.0)
        assert r.ok and "MAIN eseguito" in r.output["stdout"]
        assert r.verifica.verdetto == Verdetto.RIUSCITO
        assert r.output["misure"]["g.stl"]["bbox_mm"] == [4.0, 3.0, 2.0]

    def test_BOCCIATURA_uno_step_finto_e_ILLEGGIBILE(self, radice: Path) -> None:
        _registra(radice, max_timeout_s=120.0)
        self._bozza_freecad(radice, "finta", script=(
            "open('piastra.stl', 'w').write('x')\nopen('piastra.step', 'w').write('non uno step')\n"))
        _approva()
        r = _invoca("finta", timeout_s=120.0)
        assert r.ok is True and r.verifica.verdetto == Verdetto.FALLITO
        assert "piastra.step (non comincia con ISO-10303-21;)" in r.verifica.osservato

    def test_dentro_freecad_la_rete_e_negata_e_la_casa_e_volatile(self, radice: Path) -> None:
        _registra(radice, max_timeout_s=120.0)
        fuori = radice / "proprietario.txt"
        fuori.write_text("mio")
        self._bozza_freecad(radice, "curiosa", produce=["c.stl"], script=f"""\
import os, socket, Part
Part.makeBox(1, 1, 1).exportStl("c.stl")
print("HOME", os.path.expanduser("~"))
try:
    open({str(fuori)!r}, "w").write("suo"); print("FUORI scritto")
except OSError as e:
    print("FUORI negato", type(e).__name__)
try:
    socket.create_connection(("1.1.1.1", 53), timeout=2); print("RETE aperta")
except OSError:
    print("RETE negata")
""")
        _approva()
        r = _invoca("curiosa", timeout_s=120.0)
        assert r.ok, r.error
        assert "HOME /tmp" in r.output["stdout"] and "RETE negata" in r.output["stdout"]
        assert fuori.read_text() == "mio"
