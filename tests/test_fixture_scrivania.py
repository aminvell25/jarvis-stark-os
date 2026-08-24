"""La registrazione della scrivania e' VERA, e non e' stata ritoccata.

## Perche' questo file esiste

§11.9 concede una seconda eccezione al divieto di dati finti — il **modo di
misura** — e la prima delle cinque condizioni e' che i dati siano «registrati da
una sessione vera, mai generati». Una concessione senza una guardia e' un
invito: chi ha bisogno che una metrica torni puo' alzare `ram_percent` di due
punti e nessuno se ne accorge, perche' l'area sotto la curva della telemetria
**e'** quel numero, su un pannello che e' il 16,5 % dello schermo.

Le quattro asserzioni qui sotto non impediscono la modifica: la rendono
**visibile e deliberata**. La difesa vera sta nel cancello — *un numero di
fixture non si confronta mai con uno vivo* — e questa e' la seconda linea.

## Perche' non apre niente

Come `tests/test_catalogo.py` e la guardia del marchio: la cattura resta manuale
(`uv run python scripts/registra.py`, col core acceso) e la suite verifica
l'artefatto. Aprire un socket dentro la suite rimetterebbe il conflitto che il
turno 1 ha documentato.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FILO = RADICE / "docs" / "acceptance" / "SESSIONE-SCRIVANIA.jsonl"
PROVENIENZA = RADICE / "docs" / "acceptance" / "SESSIONE-SCRIVANIA.json"

#: `core/ws_server.py`: FAST_HZ = 2.5, cioe' un campione ogni 400 ms.
PERIODO_MS = 400
#: `ui/src/panels/telemetry.js`: CAMPIONI = 120. Sotto, il grafico resta
#: parziale — deterministico ma non rappresentativo.
CAMPIONI_MINIMI = 120


def _frame() -> list[dict]:
    return [json.loads(r) for r in FILO.read_text(encoding="utf-8").splitlines() if r.strip()]


class TestLaRegistrazioneEVeraENonRitoccata:
    def test_i_due_file_esistono(self) -> None:
        for f in (FILO, PROVENIENZA):
            assert f.exists(), (
                f"manca {f.relative_to(RADICE)}.\n"
                "Si produce col core acceso: uv run python scripts/registra.py"
            )

    def test_l_impronta_combacia(self) -> None:
        """La meta' che conta: il `.jsonl` descrive QUESTA provenienza.

        Senza, si potrebbe cambiare un valore nel filo e lasciare intatto il
        resoconto, e nessun diff lo direbbe.
        """
        d = json.loads(PROVENIENZA.read_text(encoding="utf-8"))
        vera = hashlib.sha256(FILO.read_bytes()).hexdigest()[:16]
        assert vera == d["impronta"], (
            "la registrazione e' stata modificata dopo essere stata scritta.\n"
            f"impronta nel resoconto {d['impronta']}, filo adesso {vera}.\n"
            "Se la modifica e' voluta, rifai la registrazione: "
            "uv run python scripts/registra.py"
        )

    def test_il_tempo_non_torna_indietro(self) -> None:
        f = _frame()
        assert len(f) > 50, f"registrazione troppo corta: {len(f)} frame"
        ms = [x["ms"] for x in f]
        assert ms == sorted(ms), "i frame non sono in ordine di tempo"

    def test_la_cadenza_e_quella_del_core(self) -> None:
        """Impedisce di INSERIRE o TOGLIERE campioni.

        Alzare la curva della CPU si puo' fare anche senza toccare un valore:
        basta togliere i campioni bassi. La mediana degli intervalli lo vede,
        perche' `FAST_HZ` e' una costante del server e non una media.
        """
        t = [x["ms"] for x in _frame() if x["msg"].get("topic") == "telemetry"]
        assert len(t) >= CAMPIONI_MINIMI, (
            f"{len(t)} campioni di telemetria: sotto i {CAMPIONI_MINIMI} che "
            "`telemetry.js` tiene, il grafico resta parziale"
        )
        intervalli = [b - a for a, b in zip(t, t[1:])]
        mediana = statistics.median(intervalli)
        assert PERIODO_MS * 0.875 <= mediana <= PERIODO_MS * 1.125, (
            f"cadenza {mediana:.0f} ms invece di ~{PERIODO_MS}: qualcuno ha "
            "inserito o tolto campioni di telemetria"
        )

    def test_la_ram_e_fisicamente_coerente(self) -> None:
        """La guardia contro il ritocco dei VALORI, ed e' la piu' difficile da aggirare.

        `ram_available_bytes` e `ram_percent` descrivono la stessa macchina:
        `disponibili / (1 - percentuale/100)` deve dare lo stesso totale in ogni
        frame. Chi alza `ram_percent` per gonfiare l'area sotto la curva rompe
        il totale alla prima riga che tocca, e per non romperlo dovrebbe
        ricalcolare anche i byte — cioe' fare una cosa deliberata invece di una
        distratta.
        """
        totali = []
        for x in _frame():
            m = x["msg"]
            if m.get("topic") != "telemetry":
                continue
            p = m.get("ram_percent")
            b = m.get("ram_available_bytes")
            assert p is not None and b is not None, "un frame di telemetria e' monco"
            assert 0 < p < 100, f"ram_percent fuori scala: {p}"
            totali.append(b / (1 - p / 100))
        assert totali, "nessun frame di telemetria"
        scarto = (max(totali) - min(totali)) / statistics.mean(totali)
        assert scarto < 0.01, (
            f"la RAM totale ricostruita varia dell'{scarto * 100:.1f} % fra i frame: "
            "i valori non vengono tutti dalla stessa macchina"
        )

    def test_il_resoconto_dice_se_la_barra_restera_degradata(self) -> None:
        """Non e' un divieto: e' una cosa che chi legge deve poter sapere.

        Un `agent.advisory` critico dentro la registrazione inchioda la barra su
        `degraded` in ogni riproduzione — `barra.js` scrive quello stato e non lo
        toglie piu'. Il campo dev'esserci; se e' diverso da zero, e' una
        decisione, non una sorpresa.
        """
        d = json.loads(PROVENIENZA.read_text(encoding="utf-8"))
        assert "avvisiCritici" in d, "il resoconto non dice se ci sono advisory critici"
