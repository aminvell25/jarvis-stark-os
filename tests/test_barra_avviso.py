"""Il livello della barra torna indietro da solo — e la misura e' FRESCA.

## Perche' questo test esiste

`barra.js` scriveva `degraded` su un `agent.advisory` critico e non lo toglieva
piu' nessuno: l'unico altro scrittore era `state.snapshot`, che arriva UNA
volta per sessione. La sorgente e' `package_temp_c > 75` valutata a 2,5 Hz —
**un campione** inchiodava la barra per tutta la sessione. `DEBORDO-R99.md`
riporta «barra passata a DEGRADED (temp 55 °C)»: 55 e' SOTTO la soglia, ed era
il latch, non la temperatura.

Un difetto cosi' non lo vede nessuno guardando: la barra dice una cosa
plausibile, solo che non e' vera. E non lo vede nemmeno una misura di densita',
perche' il Δ e' ~560 px su 1 294 848 — lo **0,043 %**, sotto la precisione con
cui `densita.mjs` stampa.

## Perche' questo test non apre niente

Come `tests/test_catalogo.py` e la guardia del marchio: la cattura resta
manuale — `npm run verifica:barra` — e qui si verifica che l'esito sia
**fresco**. Aprire un browser dentro la suite rimetterebbe il conflitto sul
socket del core vivo che il turno 1 ha documentato.

**Un esito vecchio e' peggio di nessun esito, perche' sembra una verifica.**
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ESITO = RADICE / "docs" / "acceptance" / "BARRA-AVVISO.json"


class TestIlLivelloTornaIndietroELaMisuraEFresca:
    def test_l_esito_esiste(self) -> None:
        assert ESITO.exists(), (
            "manca docs/acceptance/BARRA-AVVISO.json.\n"
            "Si produce con: npm run verifica:barra\n"
            "(non serve il core: la prova monta la barra nella galleria, "
            "perche' far salire il processore sopra i 75 °C al momento giusto "
            "non e' un criterio)"
        )

    def test_la_misura_descrive_i_sorgenti_di_ADESSO(self) -> None:
        """L'impronta, che e' la meta' che conta.

        Senza, questo file verificherebbe che il livello tornava indietro *un
        giorno*, e il latch potrebbe rientrare identico.
        """
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        h = hashlib.sha256()
        for f in d["fonti"]:
            h.update((RADICE / f).read_bytes())
        assert h.hexdigest()[:16] == d["impronta"], (
            "la barra e' cambiata dopo l'ultima misura.\n"
            f"impronta nell'esito {d['impronta']}, sorgenti adesso {h.hexdigest()[:16]}.\n"
            "Rimisura: npm run verifica:barra\n"
            f"(l'impronta copre {', '.join(d['fonti'])}: se a rompere il "
            "ritorno fosse un QUARTO file, aggiungilo a FONTI in "
            "scripts/prova-barra.mjs — la guardia non lo vede)"
        )

    def test_tutte_e_otto_le_condizioni(self) -> None:
        """Una per una, col nome: quale e' caduta si legge dal fallimento."""
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        assert len(d["criteri"]) == 8, (
            f"la prova misura otto condizioni, l'esito ne porta {len(d['criteri'])}"
        )
        caduti = [c for c in d["criteri"] if not c["ok"]]
        assert not caduti, "il livello non torna indietro:\n" + "\n".join(
            f"  {c['nome']}: {c['dettaglio']}" for c in caduti
        )

    def test_l_accento_e_stato_MISURABILE(self) -> None:
        """La condizione che tutte le altre presuppongono, isolata apposta.

        Se l'advisory non accendesse niente, «l'accento scade» sarebbe vero per
        **assenza del fenomeno** — §11.7 regola 4 — e il criterio continuerebbe
        a sembrare una verifica pur non bocciando piu' niente. E' la stessa
        forma dell'inerzia che non partiva in `tests/test_catalogo.py`.
        """
        m = json.loads(ESITO.read_text(encoding="utf-8"))["misure"]
        assert m["subitoDopo"] != m["aRiposo"], (
            f"l'advisory critico non ha cambiato il livello: resta "
            f"{m['aRiposo']}. Le altre condizioni sono vere per assenza."
        )

    def test_lo_stato_stabile_sopravvive_all_accento(self) -> None:
        """L'altra meta' del difetto, che e' facile introdurre correggendo la prima.

        Un accento a tempo che scadendo riscrivesse `nominal` cancellerebbe
        quello che `state.snapshot` ha detto: lo stesso errore di categoria al
        contrario. La precedenza e' offline > accento > stabile, e lo stabile
        deve restare sotto.
        """
        m = json.loads(ESITO.read_text(encoding="utf-8"))["misure"]
        assert m["dopoLAttesaConStabileDegradato"] == "degraded", (
            "scadendo, l'accento ha cancellato il livello stabile: la barra "
            f"dice {m['dopoLAttesaConStabileDegradato']} invece di degraded"
        )
