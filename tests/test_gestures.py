"""Gesture — SPEC §14, invarianti 27 e 28. Fase 7."""

from __future__ import annotations

import pytest

from core.gestures.mapping import (
    FRAME_ISTERESI,
    INTENTI_UI,
    IntentoNonAmmesso,
    Isteresi,
    Riconoscitore,
    emetti,
    palmo_aperto,
    pizzico,
)
from core.tools import registry
from core.tools.system import register_system_tools
from core.tools.files import register_file_tools
from core.platform import paths, sensors
from tests.gesture_corpus import CORPUS, mano, pizzico_fermo


def riconosci_tutto(sequenza) -> list[str]:
    """Fa girare riconoscitore e isteresi, e restituisce cio' che e' USCITO."""
    r, i = Riconoscitore(), Isteresi()
    return [g for f in sequenza if (g := i.alimenta(r(f))) is not None]


class TestCorpus:
    @pytest.mark.parametrize("nome,seq,atteso", CORPUS, ids=[c[0] for c in CORPUS])
    def test_il_corpus(self, nome: str, seq, atteso: str | None) -> None:
        usciti = riconosci_tutto(seq)
        if atteso is None:
            assert usciti == [], f"{nome}: emesso {usciti} dove non doveva uscire nulla"
        else:
            assert usciti == [atteso], f"{nome}: atteso [{atteso}], uscito {usciti}"

    def test_meta_del_corpus_e_fatta_di_NON_gesti(self) -> None:
        """§14: «un falso positivo e' indistinguibile da un comando». Un corpus
        fatto solo di gesti veri misura la sensibilita' e non la specificita',
        ed e' la seconda che tiene su questa fase."""
        negativi = sum(1 for _, _, a in CORPUS if a is None)
        assert negativi >= len(CORPUS) / 2, f"solo {negativi} casi negativi su {len(CORPUS)}"


class TestGeometria:
    def test_le_soglie_sono_relative_alla_mano(self) -> None:
        """La stessa gesture a quaranta centimetri e a un metro dalla
        telecamera deve valere uguale: le distanze si misurano in
        dimensioni-mano, non in pixel."""
        for scala in (0.12, 0.25, 0.48):
            assert pizzico(mano(scala=scala, pollice_su_indice=True))
            assert palmo_aperto(mano(scala=scala, dita=1.0))
            assert not palmo_aperto(mano(scala=scala, dita=0.4))


class TestIsteresi:
    def test_conta_esattamente_cinque_fotogrammi(self) -> None:
        """§14: «gesto stabile per 5 frame (~166 ms)»."""
        i = Isteresi()
        for n in range(1, FRAME_ISTERESI):
            assert i.alimenta("sposta_pannello") is None, f"emesso al fotogramma {n}"
        assert i.alimenta("sposta_pannello") == "sposta_pannello"

    def test_non_riemette_finche_il_gesto_non_si_stacca(self) -> None:
        """La meta' che si dimentica sempre: una mano ferma in pizzico per due
        secondi produrrebbe sessanta intenti."""
        i = Isteresi()
        usciti = [g for _ in range(60) if (g := i.alimenta("sposta_pannello"))]
        assert usciti == ["sposta_pannello"]

    def test_dopo_lo_stacco_puo_riemettere(self) -> None:
        i = Isteresi()
        for _ in range(FRAME_ISTERESI):
            i.alimenta("sposta_pannello")
        for _ in range(3):
            i.alimenta(None)
        usciti = [g for _ in range(FRAME_ISTERESI) if (g := i.alimenta("sposta_pannello"))]
        assert usciti == ["sposta_pannello"]

    def test_un_gesto_lungo_emette_una_volta_sola(self) -> None:
        assert riconosci_tutto(pizzico_fermo(40)) == ["sposta_pannello"]


@pytest.fixture
def allowlist():
    registry.clear()
    register_system_tools(sensors())
    register_file_tools(lambda: None, lambda: paths())
    yield
    registry.clear()


class TestInvariante27:
    """«Nessuna gesture puo' innescare un tool con side_effect=True. Imposto
    nel registry, non lasciato alla disciplina.»"""

    @pytest.mark.parametrize(
        "vietato", ["trash_path", "create_file", "create_folder", "move_path",
                    "copy_path", "organize_folder"]
    )
    async def test_una_gesture_NON_PUO_invocare_un_tool_distruttivo(
        self, allowlist, vietato: str
    ) -> None:
        """Non «non lo fa»: non puo'. E solleva, invece di restituire un esito
        che finirebbe in un ramo di gestione errori."""
        with pytest.raises(registry.GestureVietata):
            await registry.invoke_da_gesture(vietato, {})

    async def test_e_nemmeno_passando_da_emetti(self, allowlist) -> None:
        """La via vera delle gesture e' `emetti()`: la barriera dev'essere li'
        sotto, non solo nella funzione che si spera venga usata."""
        with pytest.raises(registry.GestureVietata):
            await emetti("trash_path", {"path": "~/Documenti"})

    async def test_un_tool_ammesso_passa(self, allowlist) -> None:
        msg = await emetti("system_status")
        assert msg["tipo"] == "tool" and msg["ok"]

    async def test_i_quattro_intenti_di_interfaccia_passano(self, allowlist) -> None:
        for intento in sorted(INTENTI_UI):
            msg = await emetti(intento, {"pannello": "telemetria"})
            assert msg["tipo"] == "ui" and msg["intento"] == intento

    async def test_un_intento_sconosciuto_SOLLEVA(self, allowlist) -> None:
        """Non viene ignorato: un intento che non e' ne' tool ne' interfaccia
        significa che qualcuno ha scritto una mappatura che non doveva
        esistere, e va visto."""
        with pytest.raises(IntentoNonAmmesso):
            await emetti("formatta_il_disco")

    async def test_ogni_tool_dell_allowlist_e_deciso(self, allowlist) -> None:
        """Nessun tool deve stare in mezzo: o e' gesture_allowed, o una
        gesture che lo nomina solleva. Il test gira su TUTTI i tool
        registrati, quindi un tool nuovo ci finisce dentro da solo."""
        for t in registry.describe_all():
            if t["gesture_allowed"]:
                assert not t["side_effect"], f"{t['name']}: gesture su un distruttivo"
            else:
                with pytest.raises(registry.GestureVietata):
                    await registry.invoke_da_gesture(t["name"], {})
