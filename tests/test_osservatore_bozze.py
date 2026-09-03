"""ADR-015, la meta' «occhi»: `bozze/*/*.stl` cambia, il pannello lo mostra.

Si guida `giro()` a mano, senza aspettare: un giro e' un giro, e le regole
— fermo per due giri, stessi byte niente, all'avvio niente — si contano.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import trimesh

from core.osservatore_bozze import INTENTO, OsservatoreBozze
from core.tools.laboratorio import BOZZE


class _Presa:
    def __init__(self) -> None:
        self.messaggi: list[dict] = []
        self.righe: list[dict] = []

    async def pubblica(self, msg: dict) -> None:
        self.messaggi.append(msg)

    async def annota(self, flusso: str, traccia: str | None, **campi) -> None:
        self.righe.append({"flusso": flusso, "traccia": traccia, **campi})


@pytest.fixture
def mondo(tmp_path: Path):
    radice = tmp_path / "laboratorio"
    presa = _Presa()
    oss = OsservatoreBozze(lambda: radice / BOZZE, presa.pubblica, presa.annota, ogni_s=0.05)
    return radice, presa, oss


def _stl(cartella: Path, nome: str = "d.stl", raggio: float = 5.0) -> Path:
    cartella.mkdir(parents=True, exist_ok=True)
    p = cartella / nome
    trimesh.creation.cylinder(radius=raggio, height=6.0, sections=32).export(p)
    return p


def _giri(oss: OsservatoreBozze, n: int) -> list[list[Path]]:
    async def _run():
        return [await oss.giro() for _ in range(n)]
    return asyncio.run(_run())


class TestIlGiro:
    def test_senza_cartella_non_succede_niente(self, mondo) -> None:
        _, presa, oss = mondo
        assert _giri(oss, 3) == [[], [], []]
        assert presa.messaggi == [] and presa.righe == []

    def test_un_file_nuovo_si_pubblica_quando_e_FERMO_e_una_volta_sola(self, mondo) -> None:
        radice, presa, oss = mondo
        p = _stl(radice / BOZZE / "2026-09-03-staffa")
        primo, secondo, terzo = _giri(oss, 3)
        assert primo == [], "al primo giro e' appena comparso: si aspetta"
        assert secondo == [p], "al secondo e' fermo: si pubblica"
        assert terzo == [], "al terzo niente e' cambiato"
        [m] = presa.messaggi
        assert m["topic"] == "model3d.preview" and m["file"] == str(p)
        assert m["vertici"] == 66 and m["bbox"] == {"x": 10.0, "y": 10.0, "z": 6.0}
        assert m["versione"] == "bozza 2026-09-03-staffa"
        [r] = presa.righe
        assert r["flusso"] == "azione" and r["intento"] == INTENTO
        assert r["traccia"] and r["da"] == "protocollo"
        assert r["ok"] is True and r["mostrata"] is True
        assert r["bozza"] == "2026-09-03-staffa" and r["file"] == "d.stl"

    def test_gli_stessi_byte_riscritti_NON_si_ripubblicano(self, mondo) -> None:
        """Uno script deterministico rieseguito riscrive byte identici — misurato
        sulla staffa, stesso hash. Riproporre lo stesso pezzo sarebbe rumore."""
        radice, presa, oss = mondo
        p = _stl(radice / BOZZE / "b")
        _giri(oss, 2)
        dati = p.read_bytes()
        p.write_bytes(dati)                          # mtime nuovo, byte uguali
        import os
        os.utime(p, None)
        assert _giri(oss, 3) == [[], [], []]
        assert len(presa.messaggi) == 1

    def test_byte_diversi_si_ripubblicano(self, mondo) -> None:
        radice, presa, oss = mondo
        p = _stl(radice / BOZZE / "b")
        _giri(oss, 2)
        _stl(radice / BOZZE / "b", raggio=8.0)
        giri = _giri(oss, 3)
        assert [g for g in giri if g] == [[p]]
        assert presa.messaggi[-1]["bbox"] == {"x": 16.0, "y": 16.0, "z": 6.0}

    def test_solo_stl_e_solo_a_un_livello(self, mondo) -> None:
        radice, presa, oss = mondo
        b = radice / BOZZE / "b"
        b.mkdir(parents=True)
        (b / "genera.py").write_text("print(1)\n")
        (b / "bozza.json").write_text(json.dumps({"produce": ["d.stl"]}))
        (b / "note.STL.txt").write_text("no")
        _stl(b / "sotto", "profondo.stl")            # bozze/b/sotto/: troppo giu'
        _stl(radice / BOZZE, "libero.stl")           # bozze/libero.stl: non e' in una bozza
        assert _giri(oss, 3) == [[], [], []]
        assert presa.messaggi == []

    def test_un_file_illeggibile_lascia_una_riga_NON_un_guasto(self, mondo) -> None:
        radice, presa, oss = mondo
        b = radice / BOZZE / "b"
        b.mkdir(parents=True)
        (b / "rotto.stl").write_text("solid a\nendsolid a\n")
        _giri(oss, 3)
        assert presa.messaggi == []
        [r] = presa.righe
        assert r["ok"] is True and r["mostrata"] is False
        assert "ASCII" in r["esito"]

    def test_oltre_il_tetto_di_vertici_si_DICE_non_si_decima(self, mondo) -> None:
        radice, presa, oss = mondo
        b = radice / BOZZE / "grande"
        b.mkdir(parents=True)
        trimesh.creation.icosphere(subdivisions=6).export(b / "sfera.stl")   # 40.962 punti
        _giri(oss, 3)
        assert presa.messaggi == []
        [r] = presa.righe
        assert r["mostrata"] is False and "40962 > 20000" in r["esito"]

    def test_un_file_sparito_e_ricomparso_e_nuovo(self, mondo) -> None:
        radice, presa, oss = mondo
        p = _stl(radice / BOZZE / "b")
        _giri(oss, 2)
        p.unlink()
        _giri(oss, 1)
        _stl(radice / BOZZE / "b")
        giri = _giri(oss, 3)
        assert [g for g in giri if g] == [[p]]
        assert len(presa.messaggi) == 2


class TestIlCicloDiVita:
    def test_all_avvio_cio_che_c_e_gia_NON_si_pubblica(self, mondo) -> None:
        """Riaprendo JARVIS il pannello non si spalanca per ogni pezzo di ieri."""
        radice, presa, oss = mondo
        p = _stl(radice / BOZZE / "ieri")

        async def giro():
            oss.avvia()
            await asyncio.sleep(0.3)
            await oss.ferma()

        asyncio.run(giro())
        assert presa.messaggi == [] and oss.giri >= 3
        # Ma se cambia DOPO, si vede.
        _stl(radice / BOZZE / "ieri", raggio=7.0)
        _giri(oss, 2)
        assert [m["file"] for m in presa.messaggi] == [str(p)]

    def test_dal_vivo_con_l_orologio(self, mondo) -> None:
        radice, presa, oss = mondo

        async def giro():
            oss.avvia()
            await asyncio.sleep(0.12)
            _stl(radice / BOZZE / "viva")
            for _ in range(40):
                await asyncio.sleep(0.05)
                if presa.messaggi:
                    break
            await oss.ferma()

        asyncio.run(giro())
        assert len(presa.messaggi) == 1 and oss.pubblicazioni == 1

    def test_ferma_e_idempotente(self, mondo) -> None:
        _, _, oss = mondo

        async def giro():
            await oss.ferma()
            oss.avvia()
            oss.avvia()
            await oss.ferma()
            await oss.ferma()

        asyncio.run(giro())


class TestNellEngine:
    def test_e_un_grado_acceso_solo_col_laboratorio(self, short_paths) -> None:
        from core.engine import Engine
        from core.settings import LaboratorioSettings
        from core.tools.laboratorio import register_laboratorio_tools

        e = Engine(short_paths)
        assert e._laboratorio is None
        e._accendi_osservatore_bozze(e.settings)
        assert e._osservatore_bozze is None, "senza laboratorio, niente occhi"

        radice = short_paths.config_dir().parent / "lab" / "laboratorio"
        radice.mkdir(parents=True)

        class _Imp:
            laboratorio = LaboratorioSettings(enabled=True, radice=radice, osserva_ogni_s=0.05)

        e._laboratorio = register_laboratorio_tools(lambda: _Imp(), lambda: [radice.parent])
        assert e._laboratorio is not None
        spento = LaboratorioSettings(enabled=True, radice=radice, osserva_bozze=False)

        async def giro():
            e._accendi_osservatore_bozze(type("S", (), {"laboratorio": spento})())
            assert e._osservatore_bozze is None, "osserva_bozze = false spegne gli occhi"
            e._accendi_osservatore_bozze(_Imp())
            assert e._osservatore_bozze is not None
            _stl(radice / BOZZE / "2026-09-03-mia")
            for _ in range(40):
                await asyncio.sleep(0.05)
                if e._osservatore_bozze.pubblicazioni:
                    break
            await e._spegni_gradi()
            assert e._osservatore_bozze is None

        asyncio.run(giro())
        [r] = [r for r in e._diario.leggi(None, "azione", limite=10 ** 9)
               if r.get("intento") == INTENTO]
        assert r["traccia"] and r["mostrata"] is True and r["bozza"] == "2026-09-03-mia"
