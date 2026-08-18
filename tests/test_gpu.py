"""GPU e controllo di ammissione — SPEC §9 e nota APU della rev 5.2."""

from __future__ import annotations

from core.gpu_scheduler import GpuScheduler
from core.platform import gpu as platform_gpu
from core.platform.base import GpuMemory
from core.platform.linux import LinuxGpu
from tests.conftest import FakeSensors

GIB = 2**30


class FakeGpu:
    def __init__(self, memoria: GpuMemory | None) -> None:
        self._m = memoria

    def memory(self) -> GpuMemory | None:
        return self._m


def _sched(gpu_mem: GpuMemory | None, ram_disponibile: int, riserva: int = 0):
    return GpuScheduler(FakeGpu(gpu_mem), FakeSensors(available=ram_disponibile),
                        reserve=riserva)


class TestHeadroomUnificato:
    def test_su_memoria_unificata_vince_il_vincolo_piu_stretto(self) -> None:
        """Il caso di questa macchina: 8 GiB di "VRAM" sono un carveout della
        RAM. Contarli come capacita' in piu' e' l'errore che §9 letta alla
        lettera farebbe commettere."""
        m = GpuMemory(total=8 * GIB, used=2 * GIB, unified=True, driver="amdgpu")
        head, _, ram = _sched(m, ram_disponibile=3 * GIB).headroom()
        assert head == 3 * GIB, "ha usato la VRAM libera invece del minimo"
        assert ram == 3 * GIB

    def test_su_gpu_discreta_conta_solo_la_vram(self) -> None:
        m = GpuMemory(total=8 * GIB, used=2 * GIB, unified=False, driver="nvidia")
        head, _, ram = _sched(m, ram_disponibile=1 * GIB).headroom()
        assert head == 6 * GIB, "su memoria dedicata la RAM non e' un vincolo"
        assert ram is None

    def test_gpu_non_leggibile(self) -> None:
        head, misura, _ = _sched(None, ram_disponibile=8 * GIB).headroom()
        assert head == 0 and misura is None


class TestAmmissione:
    def test_concede_se_entra(self) -> None:
        m = GpuMemory(total=8 * GIB, used=0, unified=False, driver="x")
        a = _sched(m, 8 * GIB).can_admit(4 * GIB)
        assert a.granted and a.shortfall == 0

    def test_rifiuta_se_non_entra_e_dice_quanto_manca(self) -> None:
        """Un rifiuto che non dice quanto mancava e' inservibile."""
        m = GpuMemory(total=8 * GIB, used=6 * GIB, unified=False, driver="x")
        a = _sched(m, 8 * GIB).can_admit(4 * GIB)
        assert not a.granted and a.shortfall == 2 * GIB

    def test_la_riserva_e_inclusa_nel_conto(self) -> None:
        m = GpuMemory(total=8 * GIB, used=0, unified=False, driver="x")
        assert _sched(m, 8 * GIB, riserva=GIB).can_admit(8 * GIB).granted is False
        assert _sched(m, 8 * GIB, riserva=GIB).can_admit(7 * GIB).granted is True

    def test_non_misurabile_significa_rifiuto(self) -> None:
        """§9 dice di rifiutare quando manca headroom, e headroom sconosciuto
        e' il caso in cui non si puo' affermare che ci sia."""
        a = _sched(None, 16 * GIB).can_admit(1024)
        assert not a.granted and "non misurabile" in a.reason

    def test_il_motivo_del_rifiuto_nomina_la_memoria_unificata(self) -> None:
        m = GpuMemory(total=8 * GIB, used=0, unified=True, driver="amdgpu")
        a = _sched(m, GIB).can_admit(4 * GIB)
        assert not a.granted and "unificata" in a.reason


class TestLetturaReale:
    def test_legge_o_dichiara_assente(self) -> None:
        """Su questa macchina deve leggere; su una senza GPU deve dire `None`
        senza sollevare. Non deve mai inventare un numero."""
        m = platform_gpu().memory()
        if m is None:
            return
        assert m.total > 0 and 0 <= m.used <= m.total
        assert m.free == m.total - m.used
        assert isinstance(m.unified, bool) and m.driver

    def test_nessuna_scheda_leggibile_da_None(self, tmp_path) -> None:
        g = LinuxGpu()
        g._RADICE = tmp_path                      # nessuna card* qui dentro
        assert g.memory() is None
