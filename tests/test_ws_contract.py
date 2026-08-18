"""Il contratto fra il core e il renderer.

Il pannello `ui/src/panels/telemetry.js` legge campi dai messaggi che il core
emette. Sono due basi di codice in due linguaggi, e **niente le tiene allineate
tranne questo test**: rinominare `cpu_percent` in `core/ws_server.py` non
romperebbe nulla in Python, e il pannello smetterebbe di mostrare la CPU senza
un errore, mostrando un trattino come se il dato non fosse disponibile.

Il test non ripete a mano l'elenco dei campi: lo **estrae dal sorgente del
pannello**. Se il pannello comincia a leggere un campo nuovo, il test se ne
accorge e chiede che il core lo mandi.
"""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

import pytest

from core.ws_server import make_advisory, sample_fast
from tests.conftest import FakeSensors

PANNELLO = Path(__file__).resolve().parent.parent / "ui/src/panels/telemetry.js"

#: Campi che il pannello legge da un oggetto diverso dal messaggio telemetria.
_NON_DAL_MESSAGGIO = {"toFixed", "length", "map", "join"}


def campi_letti_dal_pannello() -> set[str]:
    """I `t.<campo>` dentro il sorgente del pannello."""
    sorgente = PANNELLO.read_text(encoding="utf-8")
    return {
        m.group(1)
        for m in re.finditer(r"\bt\.([a-z_][a-z0-9_]*)\b", sorgente)
    } - _NON_DAL_MESSAGGIO


@pytest.fixture
def messaggio() -> dict:
    sensors = FakeSensors()
    m = sample_fast(sensors)
    m["top3"] = [asdict(p) for p in sensors.top_processes(3)]
    return m


class TestContratto:
    def test_il_pannello_legge_qualcosa(self) -> None:
        """Se l'estrazione trovasse zero campi, il test sotto passerebbe
        sempre senza verificare nulla."""
        assert len(campi_letti_dal_pannello()) >= 4

    def test_ogni_campo_letto_dal_pannello_esiste_nel_messaggio(self, messaggio) -> None:
        mancanti = campi_letti_dal_pannello() - set(messaggio)
        assert not mancanti, (
            f"il pannello legge campi che il core non manda: {sorted(mancanti)}. "
            f"O il core deve mandarli, o il pannello non deve leggerli."
        )

    def test_il_topic_e_quello_su_cui_il_renderer_si_iscrive(self, messaggio) -> None:
        assert messaggio["topic"] == "telemetry"

    def test_i_processi_hanno_i_campi_che_il_pannello_stampa(self, messaggio) -> None:
        assert messaggio["top3"]
        for p in messaggio["top3"]:
            assert {"name", "cpu"} <= set(p)

    def test_advisory_usa_il_topic_atteso(self) -> None:
        a = make_advisory({"package_temp_c": 99.0, "ram_percent": 10.0}, [])
        assert a["topic"] == "agent.advisory"


class TestSuperficieDelPreload:
    def test_il_preload_espone_esattamente_quattro_funzioni(self) -> None:
        """SPEC §6.3: il preload espone SOLO un bridge tipizzato.

        Era tre in Fase 1b, ed e' quattro dalla Fase 2: `confirm` e' la
        risposta a §6.2. Il test ha fatto il suo lavoro — e' fallito quando la
        quarta e' comparsa, e si aggiorna dichiarando perche', non allentando
        il confronto a un `>=`.
        """
        sorgente = (PANNELLO.parent.parent.parent.parent / "app/preload.js").read_text()
        esposte = set(re.findall(r"^\s{2}(\w+):", sorgente, re.MULTILINE))
        assert esposte == {"onMessage", "onStatus", "status", "confirm"}, esposte

    def test_il_renderer_non_puo_chiedere_operazioni(self) -> None:
        """La proprieta' che rende accettabile la quarta funzione: `confirm`
        risponde a una domanda gia' posta, citandone l'id. Non esiste una via
        per cui il renderer possa CHIEDERE un'operazione."""
        sorgente = (PANNELLO.parent.parent.parent.parent / "app/main.js").read_text()
        inviati = set(re.findall(r'topic:\s*"([^"]+)"', sorgente))
        assert inviati == {"fs.confirm_response"}, inviati

    def test_il_preload_richiede_solo_electron(self) -> None:
        """§6.3: «Mai `require`, `fs`, `child_process`».

        Cercare quelle parole nel sorgente non funziona: compaiono nel commento
        che cita la specifica. Conta cosa il file CHIEDE davvero, non cosa
        nomina — e la regola vera e' che l'unico modulo lecito e' `electron`,
        senza il quale non esisterebbe `contextBridge`.
        """
        sorgente = (PANNELLO.parent.parent.parent.parent / "app/preload.js").read_text()
        senza_commenti = re.sub(r"/\*.*?\*/|//[^\n]*", "", sorgente, flags=re.DOTALL)
        richiesti = set(re.findall(r"""require\(\s*["']([^"']+)["']""", senza_commenti))
        assert richiesti == {"electron"}, richiesti
