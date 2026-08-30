"""§26.9 criterio 6 — `scene:briefing` sullo schermo.

La scena esiste in `config/settings.toml` dal giorno di §26.6 e non era mai
stata applicata dal vivo: `LE-FRASI-PUNTANO-A-UNA-SCENA-CHE-ESISTE.md`
dichiarava «non ho verificato dal vivo che la scena si applichi sullo schermo».
Qui si applica davvero, e la sovrapposizione si misura in pixel invece di
guardarla.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def esito_scena() -> dict:
    """`scripts/prova-scena.mjs`: Electron vero, core vero, scena vera.

    ⚠️ **Salta invece di essere rosso quando il core non dichiara le scene.**
    Le scene stanno in `settings.toml` (§26.6), e il core in esecuzione legge
    quella di chi usa la macchina — che puo' essere piu' vecchia di
    `config/settings.toml`. Un rosso direbbe «la scena non funziona»; la verita'
    e' «questo core non l'ha mai sentita nominare», e sono due cose diverse.
    """
    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    if not (RADICE / "node_modules/playwright").exists():
        pytest.skip("playwright non installato")
    from core.platform import paths as platform_paths
    if not platform_paths().socket_path().exists():
        pytest.skip("il core non e' in esecuzione: `python -m core.engine`")

    r = subprocess.run(
        ["node", "scripts/prova-scena.mjs", "--scatti", "shots/scena-briefing"],
        cwd=RADICE, capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    d = json.loads(r.stdout.strip().splitlines()[-1])
    if not any(s["nome"] == "briefing" for s in d["dichiarate"]):
        pytest.skip(
            "il core in esecuzione non dichiara `briefing`: le scene stanno in "
            "`settings.toml` e quella caricata non le ha. Per provarla: "
            "XDG_CONFIG_HOME=<albero con config/settings.toml> python -m core.engine")
    return d


@pytest.mark.slow
class TestLaScenaSiApplica:
    """§26.9 criterio 6, prima meta': «`scene:briefing` dispone tre pannelli»."""

    def test_la_scena_arriva_dalle_impostazioni_e_si_applica(self, esito_scena) -> None:
        """Il giro intero: `settings.toml` -> core -> `ui.scene` -> scrivania.

        Il nome non basta: la scena si dichiara con i suoi pannelli, e
        `applicaScena` ritorna `null` per un nome che non conosce — cioe'
        fallirebbe in silenzio. Si guarda `scenaCorrente` DOPO.
        """
        assert esito_scena["scena_prima"] == "avvio", esito_scena["scena_prima"]
        assert esito_scena["scena_dopo"] == "briefing", (
            "la scena non si e' applicata: `applicaScena` ritorna null per un "
            "nome che il core non ha dichiarato", esito_scena["dichiarate"])

    def test_i_tre_pannelli_dichiarati_sono_quelli_a_schermo(self, esito_scena) -> None:
        """E gli altri sono NASCOSTI, non chiusi — `scrivania.js`: chiudere
        costerebbe i dati che il core manda una volta sola, e far sparire il
        pannello su cui si stava lavorando e' la cosa che rende un ambiente
        inabitabile."""
        visibili = {p["id"] for p in esito_scena["disposti"]["pannelli"]}
        assert visibili == {"news", "telemetria", "agenti"}, visibili
        assert esito_scena["disposti"]["nascosti"], (
            "l'avvio apre sei pannelli: dopo la scena i tre fuori devono essere "
            "nascosti, e se non ce n'e' nessuno qualcuno li ha chiusi")

    def test_la_pila_rispetta_lo_z_dichiarato(self, esito_scena) -> None:
        """§26.6: «le celle si sovrappongono di proposito, quindi chi sta sopra
        va detto». La scena dichiara news 3, telemetria 2, agenti 1."""
        z = {p["id"]: p["z"] for p in esito_scena["disposti"]["pannelli"]}
        assert z["news"] > z["telemetria"] > z["agenti"], z

    def test_almeno_una_coppia_si_SOVRAPPONE_davvero(self, esito_scena) -> None:
        """⚠️ **Una coppia, non tre.** §26.6 dice «le celle si sovrappongono di
        proposito», ma i suoi stessi numeri danno una sola sovrapposizione:
        `news` occupa le colonne 0-4 e `telemetria` comincia dalla 5 — a schermo
        sono affiancate, misurati 8 px di distacco. Si sovrappongono
        `telemetria` (5-8) e `agenti` (8-11), 190x162 px.

        La prova custodisce cio' che i numeri dicono, non cio' che la frase
        promette: pretendere tre sovrapposizioni vorrebbe dire cambiare le celle
        di §26.6 dentro un turno di implementazione.
        """
        coppie = esito_scena["sovrapposte"]
        assert coppie, (
            "nessun pannello ne copre un altro: la scena e' diventata una "
            "piastrellatura, e §26.2 esiste per la sovrapposizione")
        telemetria_agenti = [c for c in coppie
                             if {c["a"], c["b"]} == {"telemetria", "agenti"}]
        assert telemetria_agenti, coppie
        c = telemetria_agenti[0]
        assert c["larghezza"] > 0 and c["altezza"] > 0, c
        assert c["sopra"] == "telemetria", (
            "la scena dichiara telemetria z=2 e agenti z=1", c)
