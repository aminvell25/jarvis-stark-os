"""Il catalogo scorre — e la misura e' FRESCA.

## Perche' questo test esiste

`scripts/prova-catalogo.mjs` verifica §26.9 criterio 3 nell'app vera. Fino al
24 agosto 2026 stampava un JSON e usciva **0 comunque**: fra il 22 e il 24 la
griglia ha smesso di scorrere del tutto — le tessere erano scese a 20x20 e
quarantuno ci stavano tutte nei 422 px della vista — e nessuno se n'e' accorto.

Poi la prova ha avuto un verdetto. Non e' bastato: **il comando esisteva e non
lo lanciava nessuno**, che e' la stessa ragione per cui il difetto era passato.
Un criterio che qualcuno deve ricordarsi di eseguire non e' una guardia.

## Perche' questo test non apre Electron

Perche' aprire Electron dentro la suite rimette il conflitto che il turno 1 ha
documentato: cinque file di test usano il socket del core VIVO, e uno scatto in
parallelo gli sposta il layout sotto. Misurato: la suite intera fallisce
`TestIconeVere` circa una volta su due quando qualcosa tocca quel socket.

Quindi la cattura resta manuale — `npm run verifica:catalogo` — e qui si
verifica che l'esito sia **fresco**: un'impronta dei sorgenti del catalogo
viaggia dentro il file, e se non combacia vuol dire che qualcuno l'ha cambiato
senza rimisurare. **Un esito vecchio e' peggio di nessun esito, perche' sembra
una verifica** — ed e' la stessa forma del difetto che questo file esiste per
impedire.

E' lo stesso impianto della guardia del marchio (`tests/test_nucleo.py`,
`test_il_marchio_regge_in_TUTTI_gli_stati_e_la_misura_e_FRESCA`).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ESITO = RADICE / "docs" / "acceptance" / "CATALOGO-SCORRIMENTO.json"


class TestIlCatalogoScorreELaMisuraEFresca:
    def test_l_esito_esiste(self) -> None:
        assert ESITO.exists(), (
            "manca docs/acceptance/CATALOGO-SCORRIMENTO.json.\n"
            "Si produce con: npm run verifica:catalogo\n"
            "(serve il core acceso: la linguetta FILE legge fs.list dal core, "
            "e col core spento la prova riporta zero tessere)"
        )

    def test_la_misura_descrive_i_sorgenti_di_ADESSO(self) -> None:
        """L'impronta, che e' la meta' che conta.

        Senza, questo file verificherebbe che il catalogo scorreva *un giorno*,
        e la regressione del 22 agosto passerebbe di nuovo identica.
        """
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        h = hashlib.sha256()
        for f in d["fonti"]:
            h.update((RADICE / f).read_bytes())
        assert h.hexdigest()[:16] == d["impronta"], (
            "il catalogo e' cambiato dopo l'ultima misura di §26.9 criterio 3.\n"
            f"impronta nell'esito {d['impronta']}, sorgenti adesso {h.hexdigest()[:16]}.\n"
            "Rimisura: npm run verifica:catalogo\n"
            f"(l'impronta copre {', '.join(d['fonti'])}: se a far smettere di "
            "scorrere la griglia fosse un TERZO file — per esempio app.css che "
            "ridimensiona .cat — aggiungilo a FONTI in scripts/prova-catalogo.mjs, "
            "perche' la guardia non lo vede)"
        )

    def test_tutte_e_sei_le_condizioni(self) -> None:
        """Una per una, col nome: quale e' caduta si legge dal fallimento.

        Un `assert d["soddisfatto"]` direbbe soltanto «no».
        """
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        assert len(d["criteri"]) == 6, (
            f"§26.9 criterio 3 si misura in sei condizioni, l'esito ne porta "
            f"{len(d['criteri'])}"
        )
        caduti = [c for c in d["criteri"] if not c["ok"]]
        assert not caduti, "§26.9 criterio 3 non soddisfatto:\n" + "\n".join(
            f"  {c['nome']}: {c['dettaglio']}" for c in caduti
        )

    def test_l_inerzia_e_stata_MISURABILE(self) -> None:
        """La condizione che le altre presuppongono, isolata apposta.

        `si_e_fermata` e' stata vera per due giorni perche' il nastro non si era
        mai mosso: quattro letture a zero, quindi `fermo == ancoraFermo`. Un
        fermo che non e' mai stato in moto e' l'assenza del fenomeno, non una
        decelerazione riuscita — e un criterio vero per assenza non boccia piu'
        niente pur continuando a sembrare una verifica.

        Sta in un test suo perche' se cade, gli altri due sull'inerzia sono
        rumore: non c'e' nessuna inerzia di cui dire qualcosa.
        """
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        i = d["misure"]["inerzia"]
        assert i["misurabile"], (
            f"il nastro non si e' mosso dopo il rilascio (x = {i['subito']}): "
            "l'inerzia non e' stata misurata, e le condizioni che la riguardano "
            "sarebbero vere per assenza del fenomeno.\n"
            "Di solito vuol dire che la griglia non scorre: "
            f"contenuto {d['misure']['contenuto']['contenuto']} px contro vista "
            f"{d['misure']['contenuto']['vista']} px."
        )
