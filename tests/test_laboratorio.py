"""ADR-015 — il laboratorio: due zone, un profilo in piu', un tool con conferma.

Che cosa si prova, e con che cosa:

  - `Profilo.LABORATORIO` e `Profilo.AGENTE` per ARGV, senza eseguire: una
    sola directory scrivibile, la bozza; `--size` prima della tmpfs che
    limita; il venv montato in sola lettura; la rete solo per l'agente.
  - dal vivo, con bubblewrap: uno script che importa `numpy` e `trimesh`
    scrive un STL nella bozza; un file scritto FUORI non arriva sull'host; la
    rete e' negata.
  - `esegui_bozza` dalla strada vera, `registry.invoke`: piano con lo script
    risolto, conferma, esecuzione, verifica. E le bocciature: chi dichiara
    `staffa.stl` e scrive `staffa.txt` e' FALLITO; un rifiuto non lascia file;
    un manifesto assente non esegue; un `path` negli argomenti e' rifiutato.
  - la regola delle due zone misurata: il file del proprietario, byte per
    byte, prima e dopo.
"""

from __future__ import annotations

import asyncio
import json
import shlex
import shutil
import sys
from pathlib import Path

import pytest

from core.llm import grammar
from core.model3d import stl_lettore
from core.platform.linux_sandbox import STATO_AGENTE, albero_venv, build_argv
from core.sandbox.policy import SandboxPolicyError
from core.sandbox.runner import Profilo, argv_isolato, run_sandboxed
from core.settings import LaboratorioSettings, LLMSettings
from core.tools import registry
from core.tools.laboratorio import (BOZZE, ESEGUITE, MANIFESTO, Confronto,
                                    Laboratorio, Manifesto, compito_per_t2,
                                    differenze, etichetta, fotografia,
                                    librerie_disponibili, parlato,
                                    register_laboratorio_tools, righe_del_cervello)
from core.verifica import Verdetto

BWRAP = [
    pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap non disponibile"),
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="solo Linux"),
]

#: Uno script che scrive un cubo 40x30x12 in STL binario: e' il caso buono.
CUBO = """\
import trimesh
m = trimesh.creation.box(extents=(40.0, 30.0, 12.0))
assert m.is_watertight
m.export("cubo.stl")
print("cubo.stl", len(m.faces))
"""


class _Impostazioni:
    def __init__(self, radice: Path, **campi: object) -> None:
        self.laboratorio = LaboratorioSettings(
            **{"enabled": True, "radice": radice, **campi})  # type: ignore[arg-type]


@pytest.fixture
def radice(tmp_path: Path) -> Path:
    r = tmp_path / "laboratorio"
    r.mkdir()
    return r


@pytest.fixture(autouse=True)
def _pulisci():
    registry.clear()
    yield
    registry.set_confirm_hook(None)
    registry.clear()


def _registra(radice: Path, radici: list[Path] | None = None, pubblica=None,
              stato: Path | None = "auto", **campi: object) -> Laboratorio | None:
    registry.clear()
    if stato == "auto":
        stato = radice.parent / "stato-jarvis"
    return register_laboratorio_tools(
        lambda: _Impostazioni(radice, **campi),
        lambda: radici if radici is not None else [radice], pubblica, stato=stato)


def _bozza(radice: Path, nome: str, script: str = CUBO,
           produce: list[str] | None = None, manifesto: bool = True) -> Path:
    b = radice / BOZZE / nome
    b.mkdir(parents=True)
    (b / "genera.py").write_text(script, encoding="utf-8")
    if manifesto:
        (b / MANIFESTO).write_text(json.dumps({
            "script": "genera.py", "produce": produce or ["cubo.stl"],
            "richiesta": "un cubo"}), encoding="utf-8")
    return b


def _approva(esito: str = "approvato") -> dict:
    stato = {"piani": []}

    async def hook(piano):
        stato["piani"].append(piano)
        return esito

    registry.set_confirm_hook(hook)
    return stato


def _invoca(nome: str, **args: object):
    return asyncio.run(registry.invoke("esegui_bozza", {"bozza": nome, **args}))


# ── le impostazioni ─────────────────────────────────────────────────────────

class TestLeImpostazioni:
    def test_il_laboratorio_parte_SPENTO(self) -> None:
        assert LaboratorioSettings().enabled is False
        assert LaboratorioSettings().radice == Path("~/JARVIS/laboratorio").expanduser()

    def test_laboratorio_model_e_opus_e_MAI_haiku(self, tmp_path: Path) -> None:
        base = dict(backend="claude_code", t1_model="claude-haiku-4-5-20251001",
                    t1_cwd=tmp_path, t2_model="sonnet", max_concurrent_t2=1)
        assert LLMSettings(**base).laboratorio_model == "opus"
        assert LLMSettings(**base, laboratorio_model="sonnet").laboratorio_model == "sonnet"
        with pytest.raises(ValueError, match="haiku e' per la voce"):
            LLMSettings(**base, laboratorio_model="claude-haiku-4-5-20251001")

    def test_spento_il_tool_NON_ESISTE(self, radice: Path) -> None:
        assert _registra(radice, enabled=False) is None
        assert "esegui_bozza" not in registry.names()

    def test_radice_fuori_dalle_radici_consentite_NON_si_registra(
            self, radice: Path, tmp_path: Path) -> None:
        """Una radice la decide il proprietario: il tool la chiede, non la prende."""
        assert _registra(radice, radici=[tmp_path / "altrove"]) is None
        assert "esegui_bozza" not in registry.names()

    def test_acceso_e_sotto_le_radici_il_tool_c_e(self, radice: Path) -> None:
        assert _registra(radice) is not None
        t = registry.get("esegui_bozza")
        assert t.side_effect is True and t.planner is not None
        assert t.gesture_allowed is False and t.verifica is not None


# ── i profili, per argv ─────────────────────────────────────────────────────

class TestIlProfiloLaboratorio:
    def test_UNA_sola_directory_scrivibile(self, radice: Path) -> None:
        b = radice / "b"
        b.mkdir()
        with pytest.raises(SandboxPolicyError, match="ESATTAMENTE una"):
            build_argv([sys.executable, "x.py"], [], [radice], Profilo.LABORATORIO)
        with pytest.raises(SandboxPolicyError, match="ESATTAMENTE una"):
            build_argv([sys.executable, "x.py"], [b, radice], [radice],
                       Profilo.LABORATORIO)

    def test_la_bozza_deve_stare_sotto_le_radici(self, radice: Path,
                                                 tmp_path: Path) -> None:
        fuori = tmp_path / "fuori"
        fuori.mkdir()
        with pytest.raises(SandboxPolicyError):
            build_argv([sys.executable, "x.py"], [fuori], [radice], Profilo.LABORATORIO)

    def test_la_cwd_E_la_bozza(self, radice: Path) -> None:
        b = radice / "b"
        b.mkdir()
        with pytest.raises(SandboxPolicyError, match="E' la bozza"):
            build_argv([sys.executable, "x.py"], [b], [radice], Profilo.LABORATORIO,
                       chdir=radice)
        a = build_argv([sys.executable, "x.py"], [b], [radice], Profilo.LABORATORIO,
                       chdir=b, lavoro_mb=8)
        assert a[a.index("--chdir") + 1] == str(b.resolve())

    def test_l_argv_dice_cio_che_promette(self, radice: Path) -> None:
        b = radice / "b"
        b.mkdir()
        a = build_argv([sys.executable, "-I", "x.py"], [b], [radice],
                       Profilo.LABORATORIO, lavoro_mb=8)
        assert "--unshare-all" in a and "--share-net" not in a
        assert a[a.index("--tmpfs") + 1] == "/", "la radice e' VUOTA"
        assert a.count("--bind") == 1, "un solo bind scrivibile: la bozza"
        assert a[a.index("--bind") + 1] == str(b.resolve())
        # `--size` vale per la tmpfs CHE SEGUE, e bubblewrap rifiuta altrimenti.
        i = a.index("--size")
        assert a[i + 1] == str(8 * 1024 * 1024) and a[i + 2:i + 4] == ["--tmpfs", "/tmp"]
        assert "--clearenv" in a
        assert "HOME" not in a

    def test_il_venv_e_montato_in_sola_lettura(self) -> None:
        """`CODICE` rifiuta un venv; `LABORATORIO` lo vuole, ed e' il punto."""
        py = Path(sys.executable)
        if not (py.parent.parent / "pyvenv.cfg").is_file():
            pytest.skip("i test non girano da un venv")
        coppie = albero_venv(py)
        venv = py.parent.parent
        assert (venv.resolve(), venv) in coppie
        # E l'interprete VERO dietro il collegamento, con la sua stdlib.
        reale = py.resolve()
        assert (reale, reale) in coppie


class TestIlProfiloAgente:
    def test_rete_condivisa_DOPO_unshare_all(self, radice: Path) -> None:
        b = radice / "b"
        b.mkdir()
        a = build_argv(["claude", "-p", "x"], [b], [radice], Profilo.AGENTE, chdir=b)
        assert a.index("--unshare-all") < a.index("--share-net")
        assert a[a.index("--ro-bind"):a.index("--ro-bind") + 3] == ["--ro-bind", "/", "/"]
        scrivibili = [a[i + 1] for i, x in enumerate(a) if x == "--bind"]
        assert scrivibili[0] == str(b.resolve())
        attesi = {str(p.expanduser()) for p in STATO_AGENTE if p.expanduser().exists()}
        assert set(scrivibili[1:]) == attesi, "lo stato dell'agente, e nient'altro"

    def test_una_sola_bozza_e_niente_lavoro_mb(self, radice: Path) -> None:
        b = radice / "b"
        b.mkdir()
        c = radice / "c"
        c.mkdir()
        with pytest.raises(SandboxPolicyError, match="ESATTAMENTE una"):
            build_argv(["claude"], [b, c], [radice], Profilo.AGENTE)
        with pytest.raises(SandboxPolicyError, match="lavoro_mb"):
            build_argv(["claude"], [b], [radice], Profilo.AGENTE, lavoro_mb=8)

    def test_argv_isolato_passa_dalla_piattaforma(self, radice: Path) -> None:
        b = radice / "b"
        b.mkdir()
        a = argv_isolato(["claude", "-p", "x"], [b], [radice], Profilo.AGENTE, chdir=b)
        assert a[0] == "bwrap" and a[-3:] == ["claude", "-p", "x"]


# ── dal vivo ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("_", [0], ids=["bwrap"])
class TestDalVivo:
    pytestmark = BWRAP

    def test_numpy_e_trimesh_ci_sono_e_lo_stl_finisce_nella_bozza(
            self, radice: Path, _) -> None:
        b = _bozza(radice, "cubo")
        rc, out, err = asyncio.run(run_sandboxed(
            [sys.executable, "-I", "genera.py"], rw_paths=[b], allowed_roots=[radice],
            timeout=60, profilo=Profilo.LABORATORIO, chdir=b, lavoro_mb=32))
        assert rc == 0, err
        letto = stl_lettore.leggi(b / "cubo.stl")
        assert letto.triangoli == 12 and letto.dimensioni_mm() == (40.0, 30.0, 12.0)

    def test_fuori_dalla_bozza_NON_arriva_sull_host_e_la_rete_e_negata(
            self, radice: Path, tmp_path: Path, _) -> None:
        """Dentro, una scrittura su un percorso non montato RIESCE — finisce
        nella tmpfs della radice vuota — e sull'host non c'e'. E' la misura
        che conta: il disco del proprietario, non lo stdout dello script."""
        bersaglio = tmp_path / "proprietario.txt"
        bersaglio.write_text("mio", encoding="utf-8")
        b = _bozza(radice, "cattivo", script=f"""\
import os, socket
try:
    open({str(bersaglio)!r}, "w").write("suo")
    print("FUORI scritto")
except OSError as e:
    print("FUORI negato", type(e).__name__)
try:
    socket.create_connection(("1.1.1.1", 53), timeout=2); print("RETE aperta")
except OSError:
    print("RETE negata")
print("HOME" in os.environ)
""")
        rc, out, err = asyncio.run(run_sandboxed(
            [sys.executable, "-I", "genera.py"], rw_paths=[b], allowed_roots=[radice],
            timeout=30, profilo=Profilo.LABORATORIO, chdir=b))
        assert rc == 0, err
        assert bersaglio.read_text(encoding="utf-8") == "mio"
        assert "RETE negata" in out and "False" in out


class TestLeLibrerieDelLaboratorio:
    """Le due dipendenze di ADR-015, approvate dal proprietario: senza, il
    primo script dal vivo e' caduto su `ModuleNotFoundError: manifold3d`."""

    def test_manifold3d_e_shapely_sono_dichiarate_e_ci_sono(self) -> None:
        presenti, _ = librerie_disponibili()
        nomi = {p.split(":")[0] for p in presenti}
        assert {"manifold3d", "shapely"} <= nomi, presenti
        testo = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()
        assert '"manifold3d>=' in testo and '"shapely>=' in testo

    def test_il_prompt_dice_cio_che_c_e_e_non_cio_che_ricorda(self, monkeypatch) -> None:
        import importlib.util

        con = compito_per_t2("x", Path("/b"))
        assert "Con booleane e poligoni" in con and "engine='manifold'" in con
        assert "Senza booleane" not in con

        vero = importlib.util.find_spec
        monkeypatch.setattr(importlib.util, "find_spec",
                            lambda nome: None if nome == "manifold3d" else vero(nome))
        senza = compito_per_t2("x", Path("/b"))
        assert "ASSENTI" in senza and "manifold3d" in senza
        assert "Senza booleane" in senza and "Con booleane e poligoni" not in senza

    @pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap non disponibile")
    def test_le_booleane_girano_DENTRO_la_sandbox(self, radice: Path) -> None:
        """Wheel compilate, venv in sola lettura, radice vuota: si prova
        eseguendo, non deducendo. Un foro con `difference`, un profilo con un
        foro con `extrude_polygon`, tutti e due watertight e nella bozza."""
        b = _bozza(radice, "forata", produce=["forato.stl"], script="""\
import trimesh
from shapely.geometry import Polygon
a = trimesh.creation.box(extents=(20, 20, 5))
c = trimesh.creation.cylinder(radius=2, height=10, sections=32)
d = trimesh.boolean.difference([a, c], engine="manifold")
assert d.is_watertight and len(d.faces) > 12
d.export("forato.stl")
p = Polygon([(0, 0), (30, 0), (30, 10), (0, 10)], holes=[[(5, 5), (7, 5), (7, 7), (5, 7)]])
e = trimesh.creation.extrude_polygon(p, 3.0)
assert e.is_watertight
e.export("profilo.stl")
""")
        rc, out, err = asyncio.run(run_sandboxed(
            [sys.executable, "-I", "genera.py"], rw_paths=[b], allowed_roots=[radice],
            timeout=60, profilo=Profilo.LABORATORIO, chdir=b, lavoro_mb=32))
        assert rc == 0, err
        forato = stl_lettore.leggi(b / "forato.stl")
        assert forato.dimensioni_mm() == (20.0, 20.0, 5.0) and forato.triangoli > 12
        assert stl_lettore.leggi(b / "profilo.stl").dimensioni_mm() == (30.0, 10.0, 3.0)


# ── il tool, dalla strada vera ──────────────────────────────────────────────

class TestEseguiBozza:
    pytestmark = BWRAP

    def test_il_piano_mostra_script_interprete_e_cartella_RISOLTI(
            self, radice: Path) -> None:
        _registra(radice)
        b = _bozza(radice, "cubo")
        stato = _approva()
        r = _invoca("cubo")
        assert r.ok, r.error
        [piano] = stato["piani"]
        assert [o.tipo for o in piano.operazioni] == ["esegui", "sandbox", "diff", "create"]
        assert piano.operazioni[0].sorgente == b / "genera.py"
        assert piano.operazioni[0].destinazione == b
        assert sys.executable in piano.operazioni[0].dettaglio
        # La sandbox e il diff NON hanno percorsi: e' cosi' che la finestra di
        # conferma ne mostra il dettaglio invece del percorso.
        assert piano.operazioni[1].sorgente is None and piano.operazioni[1].destinazione is None
        assert "scrivibile SOLO" in piano.operazioni[1].dettaglio
        assert piano.operazioni[2].dettaglio == "prima esecuzione di questa bozza"
        assert [o.destinazione for o in piano.operazioni if o.tipo == "create"] == [b / "cubo.stl"]

    def test_esegue_verifica_e_misura(self, radice: Path) -> None:
        _registra(radice)
        b = _bozza(radice, "cubo")
        _approva()
        r = _invoca("cubo")
        assert r.ok and r.output["returncode"] == 0
        assert "cubo.stl" in r.output["prodotti"]
        assert r.output["misure"]["cubo.stl"]["bbox_mm"] == [40.0, 30.0, 12.0]
        assert r.output["untrusted"] is True
        assert r.verifica is not None and r.verifica.verdetto == Verdetto.RIUSCITO
        assert "stl_lettore" in r.verifica.fonte and "non dallo script" in r.verifica.fonte

    def test_un_rifiuto_non_lascia_NESSUN_file(self, radice: Path) -> None:
        _registra(radice)
        b = _bozza(radice, "cubo")
        prima = fotografia(radice)
        _approva("rifiutato")
        r = _invoca("cubo")
        assert not r.ok and r.verifica.verdetto == Verdetto.BLOCCATO
        assert not (b / "cubo.stl").exists()
        assert differenze(prima, fotografia(radice)) == []

    def test_BOCCIATURA_dichiara_staffa_stl_e_scrive_staffa_txt(
            self, radice: Path) -> None:
        """«Eseguito» non e' «verificato» (invariante 32): rc=0, ok=True, e il
        verificatore dice FALLITO perche' e' andato a guardare."""
        _registra(radice)
        _bozza(radice, "bugiarda", produce=["staffa.stl"],
               script='open("staffa.txt", "w").write("x")\nprint("fatto")\n')
        _approva()
        r = _invoca("bugiarda")
        assert r.ok is True
        assert r.verifica.verdetto == Verdetto.FALLITO
        assert "ASSENTI: staffa.stl" in r.verifica.osservato

    def test_BOCCIATURA_un_stl_vuoto_e_ILLEGGIBILE(self, radice: Path) -> None:
        _registra(radice)
        _bozza(radice, "ascii", produce=["a.stl"],
               script='open("a.stl", "w").write("solid a\\nendsolid a\\n")\n')
        _approva()
        r = _invoca("ascii")
        assert r.ok is True and r.verifica.verdetto == Verdetto.FALLITO
        assert "ILLEGGIBILI: a.stl" in r.verifica.osservato

    def test_senza_manifesto_non_si_esegue(self, radice: Path) -> None:
        _registra(radice)
        b = _bozza(radice, "muta", manifesto=False)
        stato = _approva()
        r = _invoca("muta")
        assert not r.ok and "manca" in r.error and MANIFESTO in r.error
        assert stato["piani"] == [], "nessuna domanda: il piano non si e' costruito"
        assert not (b / "cubo.stl").exists()

    def test_uno_script_che_fallisce_e_ok_False_e_NON_VERIFICATO(
            self, radice: Path) -> None:
        _registra(radice)
        _bozza(radice, "rotta", script='import sys\nprint("errore", file=sys.stderr)\nsys.exit(3)\n')
        _approva()
        r = _invoca("rotta")
        assert not r.ok and "uscito con 3" in r.error
        assert r.verifica.verdetto == Verdetto.NON_VERIFICATO

    def test_gli_argomenti_sono_un_NOME_mai_un_percorso(self, radice: Path) -> None:
        _registra(radice)
        _approva()
        for cattivo in ("../fuori", "a/b", "/tmp/x", "..", "A B"):
            r = _invoca(cattivo)
            assert not r.ok, cattivo
        r = asyncio.run(registry.invoke("esegui_bozza",
                                        {"bozza": "cubo", "path": "/tmp/x.py"}))
        assert not r.ok and "path" in (r.error or "")

    def test_una_bozza_inesistente_non_esegue_niente(self, radice: Path) -> None:
        _registra(radice)
        stato = _approva()
        r = _invoca("non-c-e")
        assert not r.ok and "non esiste" in r.error and stato["piani"] == []

    def test_LE_DUE_ZONE_il_file_del_proprietario_resta_byte_per_byte(
            self, radice: Path) -> None:
        """La misura di ADR-015, criterio 6: uno script che PROVA a scrivere
        fuori dalla bozza — nella radice del proprietario — non ci riesce, e
        il tool lo sa perche' ha fotografato prima e dopo."""
        _registra(radice)
        mio = radice / "definitivo.stl"
        mio.write_bytes(b"\x00" * 84)
        _bozza(radice, "invadente", produce=["cubo.stl"], script=CUBO + f"""
try:
    open({str(mio)!r}, "wb").write(b"suo")
    open({str(radice / 'nuovo.txt')!r}, "w").write("suo")
except OSError:
    pass
""")
        _approva()
        r = _invoca("invadente")
        assert r.ok, r.error
        assert mio.read_bytes() == b"\x00" * 84
        assert not (radice / "nuovo.txt").exists()
        assert r.output["prodotti"] == ["cubo.stl"]

    def test_l_anteprima_va_al_pannello(self, radice: Path) -> None:
        ricevuti: list[dict] = []

        async def pubblica(msg: dict) -> None:
            ricevuti.append(msg)

        _registra(radice, pubblica=pubblica)
        _bozza(radice, "cubo")
        _approva()
        r = _invoca("cubo")
        assert r.ok
        # Un cubo ha 8 vertici: sotto `MIN_VERTICI`, il gate lo rifiuterebbe,
        # e si DICE invece di gonfiarlo.
        assert r.output["anteprima"].startswith("cubo.stl non mostrata")
        assert ricevuti == []

    def test_l_anteprima_di_un_pezzo_vero_arriva_col_bbox_misurato(
            self, radice: Path) -> None:
        """Un cilindro a 32 lati sono 66 punti unificati: sopra `MIN_VERTICI`,
        e il pannello riceve lo stesso messaggio di `genera_modello`."""
        ricevuti: list[dict] = []

        async def pubblica(msg: dict) -> None:
            ricevuti.append(msg)

        _registra(radice, pubblica=pubblica)
        _bozza(radice, "cilindro", produce=["d.stl"], script=(
            "import trimesh\n"
            "m = trimesh.creation.cylinder(radius=5.0, height=6.0, sections=32)\n"
            "assert m.is_watertight\nm.export('d.stl')\n"))
        _approva()
        r = _invoca("cilindro")
        assert r.ok and r.verifica.verdetto == Verdetto.RIUSCITO
        assert r.output["anteprima"].startswith("d.stl: 66 vertici")
        [m] = ricevuti
        assert m["topic"] == "model3d.preview" and m["file"] == str(radice / BOZZE / "cilindro" / "d.stl")
        assert m["vertici"] == 66 and m["unita"] == "mm"
        assert m["bbox"] == {"x": 10.0, "y": 10.0, "z": 6.0}
        assert m["bbox_tolleranza"] == 0.0 and m["quote"] == []

    def test_il_timeout_richiesto_passa_dal_tetto(self, radice: Path) -> None:
        _registra(radice, max_timeout_s=2.0)
        _bozza(radice, "lenta", script="import time\ntime.sleep(30)\n")
        _approva()
        r = _invoca("lenta", timeout_s=100.0)
        assert not r.ok and "entro 2s" in r.error
        assert r.output["timeout_limitato"] is True


# ── la conferma col diff ────────────────────────────────────────────────────

class TestLaConfermaColDiff:
    """Fetta 4 di ADR-015. Rieseguire uno script identico da' byte identici
    (misurato); l'unico motivo per rieseguire e' un cambiamento, ed e' quello
    che la conferma mette sotto gli occhi."""

    pytestmark = BWRAP

    def _piani(self, radice: Path) -> list:
        return _approva()["piani"]

    def test_prima_identico_cambiato_con_il_diff(self, radice: Path) -> None:
        lab = _registra(radice)
        b = _bozza(radice, "cubo")
        piani = self._piani(radice)
        assert _invoca("cubo").ok
        assert piani[-1].operazioni[2].dettaglio == "prima esecuzione di questa bozza"
        assert "prima esecuzione" in piani[-1].riepilogo

        # Lo storico sta fra i dati di JARVIS, NON nella bozza.
        copia = lab.stato / ESEGUITE / "cubo" / "genera.py"
        assert copia.read_text() == CUBO
        assert sorted(p.name for p in b.iterdir()) == ["bozza.json", "cubo.stl", "genera.py"]

        assert _invoca("cubo").ok
        d = piani[-1].operazioni[2].dettaglio
        assert d.startswith("script identico all'ultima esecuzione (oggi alle ")
        assert d.endswith(", che era riuscita: il risultato sara' identico")

        (b / "genera.py").write_text(CUBO.replace("40.0, 30.0, 12.0", "50.0, 30.0, 12.0")
                                     + "print('fine')\n", encoding="utf-8")
        assert _invoca("cubo").ok
        d = piani[-1].operazioni[2].dettaglio
        assert d.startswith("script CAMBIATO dall'ultima esecuzione (oggi alle ")
        assert "+2/-1 righe" in d.splitlines()[0]
        assert "-m = trimesh.creation.box(extents=(40.0, 30.0, 12.0))" in d
        assert "+m = trimesh.creation.box(extents=(50.0, 30.0, 12.0))" in d
        assert "+print('fine')" in d
        assert "CAMBIATO" in piani[-1].riepilogo

    def test_dopo_un_fallimento_identico_dice_che_fallira(self, radice: Path) -> None:
        _registra(radice)
        _bozza(radice, "rotta", script="import sys\nsys.exit(3)\n")
        piani = self._piani(radice)
        assert not _invoca("rotta").ok
        assert not _invoca("rotta").ok
        d = piani[-1].operazioni[2].dettaglio
        assert ", che era FALLITA (rc 3): fallira' allo stesso modo" in d

    def test_senza_storico_lo_dice(self, radice: Path) -> None:
        _registra(radice, stato=None)
        _bozza(radice, "cubo")
        piani = self._piani(radice)
        assert _invoca("cubo").ok
        assert piani[-1].operazioni[2].dettaglio == "senza storico delle esecuzioni"

    def test_un_diff_lungo_si_tronca_e_lo_dice(self, radice: Path) -> None:
        lab = _registra(radice)
        b = _bozza(radice, "lunga")
        _approva()
        assert _invoca("lunga").ok
        (b / "genera.py").write_text(CUBO + "".join(f"x{i} = {i}\n" for i in range(200)))
        c = lab.confronta_script(b, "genera.py")
        assert c.stato == "cambiato" and c.aggiunte == 200 and c.tolte == 0
        assert c.righe_oltre > 0 and len(c.diff.splitlines()) == 60
        piani = self._piani(radice)
        assert _invoca("lunga").ok
        assert f"… altre {c.righe_oltre} righe di diff non mostrate" in piani[-1].operazioni[2].dettaglio

    def test_lo_stesso_script_con_un_comando_diverso_NON_e_identico(self, radice: Path) -> None:
        """FreeCAD e' passato da `FreeCADCmd genera.py` a runpy: la conferma
        avrebbe detto «non produrra' niente neanche stavolta»."""
        lab = _registra(radice)
        b = _bozza(radice, "cubo")
        _approva()
        assert _invoca("cubo").ok
        c = lab.confronta_script(b, "genera.py", "altro-comando genera.py")
        assert c.stato == "comando_cambiato"
        assert "COMANDO diverso" in c.frase() and "ora: altro-comando" in c.frase()
        assert c.a_voce().startswith("lo script e' lo stesso, ma")
        # E col comando giusto resta «identico».
        stesso = lab.confronta_script(b, "genera.py", shlex.join(
            Laboratorio.interprete_per("python", "genera.py")))
        assert stesso.stato == "identico"

    def test_un_esecuzione_vuota_non_e_riuscita(self, radice: Path) -> None:
        """rc 0 e zero prodotti: il caso che il solo rc nascondeva."""
        lab = _registra(radice)
        b = _bozza(radice, "muta", produce=["m.stl"], script="print('niente')\n")
        _approva()
        r = _invoca("muta")
        assert r.ok and r.verifica.verdetto == Verdetto.FALLITO
        c = lab.confronta_script(b, "genera.py")
        assert c.prodotti_precedenti == 0
        assert "NON ha prodotto niente" in c.frase() and "neanche stavolta" in c.frase()
        assert c.a_voce().endswith("che non aveva prodotto niente")

    def test_uno_storico_vecchio_non_promette_niente(self) -> None:
        c = Confronto("identico", rc_precedente=0, prodotti_precedenti=None)
        assert c.frase().endswith("uscita con rc 0 (prodotti non registrati)")
        assert "risultato sara'" not in c.frase(), "con uno storico cieco non si promette"
        assert c.a_voce() == "lo script e' identico all'ultima volta"

    def test_le_frasi_a_voce(self) -> None:
        assert Confronto("prima").a_voce() == "e' la prima esecuzione"
        assert Confronto("identico", rc_precedente=0, prodotti_precedenti=1).a_voce().endswith(
            "il risultato sara' lo stesso")
        assert Confronto("identico", rc_precedente=1).a_voce().endswith("che era fallita")
        assert Confronto("cambiato", aggiunte=12, tolte=3).a_voce() == (
            "lo script e' cambiato: 12 righe in piu' e 3 in meno")
        assert Confronto("senza_storico").a_voce() == "non ho lo storico delle esecuzioni"


# ── la cartella e i nomi ────────────────────────────────────────────────────

class TestLaCartella:
    def test_nuova_bozza_non_sovrascrive_MAI(self, radice: Path) -> None:
        lab = Laboratorio(lambda: _Impostazioni(radice), lambda: [radice])
        a = lab.nuova_bozza("una staffa per un servo SG90", quando=0)
        b = lab.nuova_bozza("una staffa per un servo SG90", quando=0)
        assert a.name.endswith("-staffa-per-un-servo-sg90") and b.name == a.name + "-2"
        assert a.parent == radice / BOZZE

    def test_trova_bozza_l_ultima_toccata_o_quella_che_somiglia(self, radice: Path) -> None:
        import os
        import time

        lab = Laboratorio(lambda: _Impostazioni(radice), lambda: [radice])
        assert lab.trova_bozza() is None, "senza bozze/ non c'e' niente da trovare"
        a = _bozza(radice, "2026-09-01-staffa-per-un-servo-sg90")
        b = _bozza(radice, "2026-09-02-distanziale-m3")
        c = _bozza(radice, "2026-09-03-staffa-lunga")
        t = time.time()
        for i, d in enumerate((c, a, b)):          # b e' l'ultima TOCCATA
            os.utime(d, (t + i, t + i))
        assert lab.trova_bozza() == b
        assert lab.trova_bozza("staffa") == a, "fra le due staffe, la piu' recente"
        assert lab.trova_bozza("della staffa lunga") == c
        assert lab.trova_bozza("il distanziale") == b
        assert lab.trova_bozza("elmo") is None
        (radice / BOZZE / "non un nome!").mkdir()
        assert lab.trova_bozza("non") is None, "un nome fuori regola non si trova"

    def test_a_voce_si_dice_l_etichetta(self) -> None:
        assert parlato("2026-09-03-staffa-per-un-servo-sg90") == "staffa per un servo sg90"
        assert parlato("mia-bozza") == "mia bozza"

    def test_l_etichetta_e_un_nome_pulito(self) -> None:
        assert etichetta("Un'asta filettata M8, 120 mm!") == "asta-filettata-m8-120-mm"
        assert etichetta("   ") == "bozza"

    def test_il_manifesto_rifiuta_percorsi_e_formati_ignoti(self) -> None:
        with pytest.raises(ValueError):
            Manifesto(script="../x.py", produce=["a.stl"])
        with pytest.raises(ValueError):
            Manifesto(produce=["a.obj"])
        with pytest.raises(ValueError):
            Manifesto(produce=["sub/a.stl"])
        with pytest.raises(ValueError):
            Manifesto(produce=["a.stl"], path="/x")  # type: ignore[call-arg]


# ── il lettore STL ──────────────────────────────────────────────────────────

class TestIlLettoreStl:
    def test_un_cubo_di_trimesh_sono_12_triangoli_e_8_punti(self, tmp_path: Path) -> None:
        import trimesh
        p = tmp_path / "c.stl"
        trimesh.creation.box(extents=(40.0, 30.0, 12.0)).export(p)
        letto = stl_lettore.leggi(p)
        assert letto.triangoli == 12 and letto.dimensioni_mm() == (40.0, 30.0, 12.0)
        pos, tri = stl_lettore.vertici(p)
        assert pos.shape == (8, 3) and tri.shape == (12, 3)

    def test_ascii_troncato_e_vuoto_sono_ILLEGGIBILI(self, tmp_path: Path) -> None:
        p = tmp_path / "a.stl"
        p.write_text("solid a\nendsolid a\n")
        with pytest.raises(stl_lettore.StlIllegibile, match="zero triangoli"):
            stl_lettore.leggi(p)
        # Un ASCII VERO si legge: e' cio' che FreeCAD scrive con exportStl.
        p.write_text("solid a\n" + "".join(
            f"facet normal 0 0 1\nouter loop\nvertex {x} {y} 0\nvertex {x+1} {y} 0\n"
            f"vertex {x} {y+1} 0\nendloop\nendfacet\n" for x in range(3) for y in range(3)
        ) + "endsolid a\n")
        letto = stl_lettore.leggi(p)
        assert letto.formato == "ascii" and letto.triangoli == 9
        assert letto.dimensioni_mm() == (3.0, 3.0, 0.0)
        p.write_text("solid a\nfacet\nvertex 1 2\nendsolid\n")
        with pytest.raises(stl_lettore.StlIllegibile, match="zero triangoli"):
            stl_lettore.leggi(p)
        p.write_text("solid a\nvertex 1 2 x\nvertex 1 2 3\nvertex 1 2 3\nendsolid\n")
        with pytest.raises(stl_lettore.StlIllegibile, match="malformato"):
            stl_lettore.leggi(p)
        import trimesh
        trimesh.creation.box().export(p)
        p.write_bytes(p.read_bytes()[:-10])
        with pytest.raises(stl_lettore.StlIllegibile, match="dichiara 12 triangoli"):
            stl_lettore.leggi(p)
        p.write_bytes(b"\x00" * 84)
        with pytest.raises(stl_lettore.StlIllegibile, match="zero triangoli"):
            stl_lettore.leggi(p)


# ── la grammatica ───────────────────────────────────────────────────────────

class TestLaFrase:
    @pytest.mark.parametrize("frase, richiesta", [
        ("costruisci nel laboratorio una staffa per un servo SG90",
         "una staffa per un servo sg90"),
        ("nel laboratorio, fammi un tappo da 40 millimetri", "un tappo da 40 millimetri"),
        ("progetta in laboratorio un supporto per il telefono", "un supporto per il telefono"),
    ])
    def test_la_richiesta_e_testo_libero(self, frase: str, richiesta: str) -> None:
        i = grammar.parse(frase)
        assert i is not None and i.tool == "laboratorio"
        assert i.args == {"richiesta": richiesta}
        assert "laboratorio" in grammar.INTENTI_CORE

    @pytest.mark.parametrize("frase", [
        "apri il laboratorio", "costruisci una staffa", "genera un'estrusione di 80 millimetri",
    ])
    def test_senza_la_parola_o_senza_il_verbo_NON_e_il_laboratorio(self, frase: str) -> None:
        i = grammar.parse(frase)
        assert i is None or i.tool != "laboratorio"

    @pytest.mark.parametrize("frase, quale", [
        ("esegui la bozza", ""),
        ("riesegui la bozza della staffa", "staffa"),
        ("rilancia l'ultima bozza", ""),
        ("esegui di nuovo la bozza del distanziale", "distanziale"),
        ("rifai la bozza", ""),
    ])
    def test_rieseguire_una_bozza_e_un_intento_del_core(self, frase: str, quale: str) -> None:
        i = grammar.parse(frase)
        assert i is not None and i.tool == "riesegui_bozza"
        assert i.args == {"quale": quale}
        assert "riesegui_bozza" in grammar.INTENTI_CORE

    @pytest.mark.parametrize("frase", ["la bozza e' pronta?", "esegui il codice",
                                       "apri la bozza della staffa"])
    def test_senza_la_forma_giusta_NON_e_una_bozza(self, frase: str) -> None:
        i = grammar.parse(frase)
        assert i is None or i.tool != "riesegui_bozza"


# ── le righe del cervello ────────────────────────────────────────────────────

class TestLeRigheDelCervello:
    def test_dal_flusso_di_claude_code_escono_righe_vere(self) -> None:
        from core.llm.claude_t2 import Evento

        ev = Evento("assistant", {"message": {"content": [
            {"type": "text", "text": "Genero  i tre\nfile."},
            {"type": "tool_use", "name": "Write",
             "input": {"file_path": "/x/bozza/genera.py", "content": "..."}},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/x/bozza/BOZZA.md"}},
            {"type": "tool_use", "name": "Grep", "input": {"pattern": "sg90"}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
            {"type": "tool_use", "name": "Ignoto", "input": {}},
        ]}})
        assert righe_del_cervello(ev) == [
            "Genero i tre file.", "scrive genera.py", "legge BOZZA.md",
            "cerca sg90", "ESEGUE ls", "usa Ignoto"]
        assert righe_del_cervello(Evento("result", {"is_error": False})) == []
        assert righe_del_cervello(Evento("system", {})) == []

    def test_un_paragrafo_lungo_diventa_una_riga(self) -> None:
        from core.llm.claude_t2 import Evento

        ev = Evento("assistant", {"message": {"content": [{"type": "text", "text": "a" * 2000}]}})
        [riga] = righe_del_cervello(ev)
        assert len(riga) == 600 and riga.endswith("…")

    def test_esegui_passa_ogni_evento_all_osservatore_e_un_osservatore_rotto_non_ferma(
            self, monkeypatch) -> None:
        from core.llm.claude_t2 import ClaudeT2, Evento
        from core.llm.governor import Governor

        t2 = ClaudeT2(Governor(), Path("/tmp"), modello="opus", tool="")
        eventi = [Evento("assistant", {"message": {"content": [{"type": "text", "text": "ciao"}]}}),
                  Evento("result", {"is_error": False, "session_id": "s1", "total_cost_usd": 0.1})]

        async def stream(task, etichetta, resume=None, contenuto=None):
            for ev in eventi:
                yield ev

        monkeypatch.setattr(t2, "stream", stream)
        visti: list[str] = []

        async def osserva(ev) -> None:
            visti.append(ev.tipo)
            if ev.tipo == "result":
                raise RuntimeError("l'osservatore cade")

        r = asyncio.run(t2.esegui("x", "prova", osserva=osserva))
        assert visti == ["assistant", "result"]
        assert r.ok and r.testo == "ciao" and r.costo_usd == 0.1


# ── la radice di composizione: dalla richiesta al diario ────────────────────

class TestLaRadiceDiComposizione:
    """Criterio 7 di ADR-015: la riga di diario porta la traccia del turno e
    il verdetto. T2 e' finto — scrive i tre file e torna — perche' qui si
    giudica il cablaggio, non Claude Code, che ha il suo giro dal vivo."""

    pytestmark = BWRAP

    def test_spento_l_intento_lo_dice(self, short_paths) -> None:
        from core.engine import Engine
        from core.traccia import Origine, Traccia

        e = Engine(short_paths)
        assert e._laboratorio is None, "il laboratorio parte SPENTO"
        esito = asyncio.run(e._costruisci_nel_laboratorio("un cubo", Traccia.nuova(Origine.VOCE)))
        assert esito["ok"] is False and "laboratorio spento" in esito["error"]

    @staticmethod
    def _engine_col_laboratorio(short_paths):
        """Un engine con il laboratorio acceso su una radice DENTRO la tmp.

        ⚠️ Le radici consentite del file spedito sono cartelle VERE del
        proprietario, e `short_paths` le copia tali e quali: la prima stesura
        di questo test ha scritto una bozza in
        `~/.local/share/jarvis-os/workspace/laboratorio`, sul disco vero. Si
        riscrivono PRIMA di comporre l'engine, e puntano dentro la tmp.
        """
        import re

        from core.engine import Engine

        radice_consentita = short_paths.config_dir().parent / "lab"
        radice_consentita.mkdir()
        toml = short_paths.config_dir() / "settings.toml"
        toml.write_text(re.sub(r"allowed_roots = \[[^\]]*\]",
                               f'allowed_roots = ["{radice_consentita}"]',
                               toml.read_text(encoding="utf-8")), encoding="utf-8")
        e = Engine(short_paths)
        assert list(e.settings.fs.allowed_roots) == [radice_consentita]
        radice = radice_consentita / "laboratorio"
        radice.mkdir()
        e._laboratorio = register_laboratorio_tools(
            lambda: _Impostazioni(radice),
            lambda: list(e._radici_sicure().fs.allowed_roots),
            stato=short_paths.data_dir() / "laboratorio")
        assert e._laboratorio is not None
        return e, radice

    def test_esegui_la_bozza_trova_esegue_e_riferisce(self, short_paths, monkeypatch) -> None:
        """L'altra meta' del laboratorio: una bozza scritta A MANO dal
        proprietario, «esegui la bozza», la conferma, il verdetto, la frase."""
        from core.traccia import Origine, Traccia

        e, radice = self._engine_col_laboratorio(short_paths)
        dette: list[str] = []
        monkeypatch.setattr(e, "_annuncia_a_voce",
                            lambda frase, *, registra: dette.append(frase))
        traccia = Traccia.nuova(Origine.VOCE)

        vuoto = asyncio.run(e._riesegui_bozza("", traccia))
        assert vuoto["ok"] is False and "nessuna bozza in" in vuoto["error"]

        _bozza(radice, "2026-09-03-mia-staffa", produce=["d.stl"], script=(
            "import trimesh\n"
            "trimesh.creation.cylinder(radius=5.0, height=6.0, sections=32).export('d.stl')\n"))
        _approva()

        ignota = asyncio.run(e._riesegui_bozza("elmo", traccia))
        assert ignota["ok"] is False and "somigli a «elmo»" in ignota["error"]

        async def giro() -> dict:
            esito = await e._riesegui_bozza("della staffa", traccia)
            await asyncio.gather(*e._compiti)
            return esito

        esito = asyncio.run(giro())
        assert esito["ok"] is True and esito["output"]["bozza"] == "2026-09-03-mia-staffa"
        assert dette[0] == ("Eseguo la bozza «mia staffa», Signore: e' la prima "
                            "esecuzione. Confermi sulla scrivania.")
        assert dette[-1].startswith("Signore, la bozza «mia staffa» e' pronta: d.stl")
        [r] = [r for r in e._diario.leggi(None, "azione", limite=10 ** 9)
               if r.get("intento") == "esegui_bozza"]
        assert r["traccia"] == traccia.id and r["verdetto"] == "riuscito"
        assert (radice / BOZZE / "2026-09-03-mia-staffa" / "d.stl").is_file()

    def test_la_riga_di_diario_porta_la_traccia_e_il_verdetto(
            self, short_paths, monkeypatch) -> None:
        import core.engine as motore
        from core.llm.claude_t2 import Risultato
        from core.traccia import Origine, Traccia

        e, radice = self._engine_col_laboratorio(short_paths)

        visto: dict = {}

        class T2Finto:
            def __init__(self, governor, radice, modello, tool, max_turns,
                         su_evento=None, avvolgi=None):
                visto.update(modello=modello, tool=tool, max_turns=max_turns,
                             bozza=Path(radice), avvolto=avvolgi(["claude", "-p", "x"]))

            async def esegui(self, task, etichetta, osserva=None):
                from core.llm.claude_t2 import Evento

                b = visto["bozza"]
                assert "l'UNICA in cui puoi scrivere" in task
                # Le righe del cervello: eventi nella forma di stream-json.
                if osserva is not None:
                    await osserva(Evento("assistant", {"message": {"content": [
                        {"type": "text", "text": "Genero il cilindro con trimesh."},
                        {"type": "tool_use", "name": "Write",
                         "input": {"file_path": str(b / "genera.py"), "content": "x"}},
                    ]}}))
                    await osserva(Evento("result", {"is_error": False}))
                (b / "genera.py").write_text(
                    "import trimesh\n"
                    "m = trimesh.creation.cylinder(radius=5.0, height=6.0, sections=32)\n"
                    "m.export('d.stl')\n", encoding="utf-8")
                (b / MANIFESTO).write_text(json.dumps(
                    {"script": "genera.py", "produce": ["d.stl"], "richiesta": "un cubo"}))
                (b / "BOZZA.md").write_text("# bozza\n", encoding="utf-8")
                return Risultato(ok=True, testo="Ho progettato un distanziale.")

        monkeypatch.setattr(motore, "ClaudeT2", T2Finto)
        dette: list[str] = []
        monkeypatch.setattr(e, "_annuncia_a_voce",
                            lambda frase, *, registra: dette.append(frase))
        _approva()
        traccia = Traccia.nuova(Origine.VOCE)

        async def giro() -> None:
            await e._bozza_scritta_ed_eseguita("un cubo", traccia)
            await asyncio.gather(*e._compiti)

        asyncio.run(giro())

        # Chi scrive: opus (mai haiku), i tool senza Bash, e l'argv AVVOLTO
        # da bubblewrap — il confine e' il kernel, non l'elenco dei tool.
        assert visto["modello"] == e.settings.llm.laboratorio_model == "opus"
        assert "Bash" not in visto["tool"]
        assert visto["avvolto"][0] == "bwrap" and "--share-net" in visto["avvolto"]
        assert visto["bozza"].parent == radice / BOZZE

        # UNA riga per il piano, scritta da `_esito_confermato` — «un piano,
        # una risposta» — e porta la traccia del turno vocale perche'
        # `registry.invoke` l'ha messa nel `ToolResult`. La prima stesura ne
        # scriveva una seconda a mano, e questo `== 1` l'ha trovata.
        righe = [r for r in e._diario.leggi(None, "azione", limite=10 ** 9)
                 if r.get("intento") == "esegui_bozza"]
        assert len(righe) == 1, righe
        [r] = righe
        assert r["traccia"] == traccia.id
        assert r["ok"] is True and r["verdetto"] == "riuscito"
        assert r["da"] == "conferma" and r["operazioni"] == 4
        assert "presenti e leggibili" in r["osservato"]
        assert dette[-1].startswith("Signore, la bozza «cubo» e' pronta: d.stl")
        assert "66 triangoli" not in dette[-1] and "10 per 10 per 6 millimetri" in dette[-1]

        # Le righe del cervello: nel diario come DIALOGO del laboratorio, con
        # la traccia del turno — e mai dette a voce.
        cervello = [r for r in e._diario.leggi(None, "dialogo", limite=10 ** 9)
                    if r.get("chi") == "laboratorio"]
        testi = [r["testo"] for r in cervello]
        assert testi[0] == "opus scrive la bozza «cubo»"
        assert "Genero il cilindro con trimesh." in testi
        assert "scrive genera.py" in testi
        assert testi[-1].startswith("bozza scritta in ")
        assert all(r["traccia"] == traccia.id and r["bozza"] == "2026-09-03-cubo"
                   for r in cervello)
        assert not any("Genero il cilindro" in d or "scrive genera.py" in d for d in dette)
