"""Il grafo degli agenti e i fusi orari — SPEC §13, Fase 5."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.agents_mesh import SUBAGENTI, snapshot
from core.tools.geo import TABELLA, _gradi, leggi_fusi

RADICE = Path(__file__).resolve().parent.parent


class TestMesh:
    def test_i_subagent_dichiarati_sono_quelli_veri(self) -> None:
        """La costante deve corrispondere ai file in `.claude/agents/`.

        Una tupla scritta a mano che si scollega dalla realta' senza che
        nessuno se ne accorga e' peggio di nessuna tupla: il pannello
        mostrerebbe agenti che non esistono, con l'aria di essere un dato.
        """
        veri = sorted(p.stem for p in (RADICE / ".claude/agents").glob("*.md"))
        assert list(SUBAGENTI) == veri

    def test_senza_governor_i_tier_dicono_non_collegato(self) -> None:
        """«non collegato» e «inerte» non sono la stessa cosa.

        Il primo vuol dire che il tier non e' composto in questo processo; il
        secondo che c'e' e non sta facendo niente. Su un pannello di stato e'
        l'informazione principale, e confonderli sarebbe un dato falso.
        """
        m = snapshot(regole_t0=13, tool_registrati=14)
        per_id = {n["id"]: n for n in m["nodi"]}
        assert per_id["t1"]["stato"] == "non collegato"
        assert per_id["t2"]["stato"] == "non collegato"
        assert per_id["t0"]["stato"] == "pronto"
        assert "13 regole" in per_id["t0"]["dettaglio"]

    def test_ogni_arco_collega_nodi_che_esistono(self) -> None:
        m = snapshot(regole_t0=13, tool_registrati=14)
        noti = {n["id"] for n in m["nodi"]}
        for da, a in m["archi"]:
            assert da in noti and a in noti, (da, a)


class TestFusi:
    def test_coordinate_iso6709_in_gradi_decimali(self) -> None:
        # +DDMM+DDDMM e +DDMMSS+DDDMMSS: le due lunghezze del formato.
        assert _gradi("+4722+00832") == pytest.approx((47.3667, 8.5333), abs=1e-3)
        assert _gradi("-3352+15113") == pytest.approx((-33.8667, 151.2167), abs=1e-3)
        assert _gradi("+404251-0740023") == pytest.approx((40.7142, -74.0064), abs=1e-3)

    @pytest.mark.skipif(not TABELLA.exists(), reason="tzdata non installata")
    def test_la_tabella_vera_si_legge_tutta(self) -> None:
        zone = leggi_fusi()
        assert len(zone) > 200, "tzdata ha molte piu' zone di cosi'"
        for z in zone:
            assert -90 <= z["lat"] <= 90, z
            assert -180 <= z["lon"] <= 180, z
        assert any(z["nome"] == "Europe/Rome" for z in zone)
