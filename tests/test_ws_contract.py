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

#: ⚠️ IL PANNELLO RICEVE DUE TOPIC, e fino al 25 agosto 2026 ne riceveva uno.
#:
#: `moduli.js` gli manda anche `state.snapshot`, che porta il consumo vocale del
#: mese (ADR-004): un dato che non ha senso rimandare 2,5 volte al secondo. Il
#: pannello smista sul campo `topic` e torna subito.
#:
#: Questi due campi vengono da li', e questo test — che verifica il contratto
#: con `telemetry` — non li deve cercare in un messaggio di telemetria. Non e'
#: una deroga: e' che la domanda «questo campo esiste?» ha due destinatari
#: diversi, e il secondo lo verifica `test_i_campi_dello_snapshot_esistono`.
_DALLO_SNAPSHOT = {"topic", "voce"}


def campi_letti_dal_pannello() -> set[str]:
    """I `t.<campo>` dentro il sorgente del pannello."""
    sorgente = PANNELLO.read_text(encoding="utf-8")
    return {
        m.group(1)
        for m in re.finditer(r"\bt\.([a-z_][a-z0-9_]*)\b", sorgente)
    } - _NON_DAL_MESSAGGIO - _DALLO_SNAPSHOT


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

    def test_i_campi_dello_snapshot_esistono(self) -> None:
        """L'altra meta': `voce.consumo` deve esistere in `state.snapshot`, o il
        pannello mostrerebbe per sempre lo stato vuoto credendo che il consumo
        sia zero — che e' §11.7 regola 4, un criterio vero per assenza."""
        import inspect

        from core.engine import Engine
        sorgente = inspect.getsource(Engine)
        assert '"consumo": self._governor.consumo_voce_mese()' in sorgente, (
            "il pannello legge `voce.consumo` e il core non lo mette nello "
            "snapshot: mostrerebbe «nessun consumo» per sempre"
        )

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
    def test_il_preload_espone_esattamente_cinque_funzioni(self) -> None:
        """SPEC §6.3: il preload espone SOLO un bridge tipizzato.

        Tre in Fase 1b, quattro dalla Fase 2 (`confirm`, la risposta a §6.2),
        **cinque da §26.10 punto 1** (`salvaLayout`). Il test ha fatto il suo
        lavoro tutte e due le volte: e' fallito quando la funzione e'
        comparsa, e si aggiorna dichiarando perche', non allentando il
        confronto a un `>=`.

        La dichiarazione della quinta sta nell'intestazione di `preload.js` e
        in `core/layout.py`. In una riga: senza persistenza, un'icona
        trascinata che al riavvio torna al suo posto e' peggio di un'icona che
        non si puo' trascinare.
        """
        sorgente = (PANNELLO.parent.parent.parent.parent / "app/preload.js").read_text()
        esposte = set(re.findall(r"^\s{2}(\w+):", sorgente, re.MULTILINE))
        assert esposte == {"onMessage", "onStatus", "status", "confirm",
                           "salvaLayout"}, esposte

    def test_cio_che_sale_e_una_risposta_oppure_uno_STATO(self) -> None:
        """La proprieta' che tiene, riformulata il giorno in cui e' cambiata.

        Fino a §26 i messaggi in salita erano due e **entrambi risposte**:
        ognuno cita l'`id` di una domanda che il core ha gia' posto. Il test
        diceva: «il giorno in cui questo elenco conterra' un messaggio senza
        `id`, sara' una RICHIESTA, e allora il ponte avra' smesso di essere un
        ponte».

        Quel giorno e' arrivato, e la previsione era **quasi** giusta: manca
        un terzo caso. `ui.layout` non ha un `id` e non e' una richiesta —

            **non chiede un'operazione: dichiara uno stato dell'ambiente.**
            Il core non lo ESEGUE, lo RICORDA.

        La proprieta' diventa quindi: ogni messaggio in salita e' **o** una
        risposta con l'`id` di una domanda gia' posta, **o** una dichiarazione
        di stato che non nomina nessuna operazione. Il secondo ramo non e' una
        scappatoia: e' verificabile, e i due test qui sotto lo verificano.
        """
        sorgente = (PANNELLO.parent.parent.parent.parent / "app/main.js").read_text()
        inviati = set(re.findall(r'topic:\s*"([^"]+)"', sorgente))
        assert inviati == {"fs.confirm_response", "argus.capture_response",
                           "ui.layout"}, inviati

        for blocco in re.findall(r"socket\.send\(JSON\.stringify\(\{(.*?)\}\)\);",
                                 sorgente, re.S):
            if '"ui.layout"' in blocco:
                continue                      # e' una dichiarazione, non una risposta
            assert "id:" in blocco, f"messaggio in salita senza id:\n{blocco[:200]}"

    def test_la_dichiarazione_di_stato_non_nomina_nessuna_operazione(self) -> None:
        """Il secondo ramo, verificato invece che concesso.

        `ui.layout` e' innocuo per **cio' che non contiene**: nessun percorso,
        nessun nome di tool, nessun campo libero. Il ponte lo costruisce campo
        per campo da un elenco fisso, e questo test e' quell'elenco.

        Il giorno in cui qualcuno aggiungesse qui un campo `comando`, o `path`,
        o un `...dato` che copia tutto, il canale smetterebbe di essere una
        dichiarazione e tornerebbe a essere il canale generico che §6.3 vieta.
        """
        sorgente = (PANNELLO.parent.parent.parent.parent / "app/main.js").read_text()
        blocco = next(b for b in
                      re.findall(r"socket\.send\(JSON\.stringify\(\{(.*?)\}\)\);",
                                 sorgente, re.S) if '"ui.layout"' in b)

        assert "..." not in blocco, (
            "il ponte copia l'oggetto invece di ricostruirlo: cosi' passa "
            "qualunque chiave, e il canale torna generico"
        )
        primo_livello = set(re.findall(r"^\s{6}(\w+):", blocco, re.MULTILINE))
        # §26.5 ha aggiunto `icone` e `cartelle`: sono posizioni sul fondo
        # della scrivania, della stessa natura dei pannelli. L'elenco cresce
        # quando cresce l'ambiente; cio' che NON deve entrare e' qui sotto.
        #
        # `area_sinistra` e `area_alto` sono entrati il 25 agosto 2026, e sono
        # della stessa natura dei due che c'erano gia': due interi che dicono
        # DOVE comincia il pavimento, come larghezza e altezza dicono quanto e'
        # grande. Non nominano un'operazione ne' un posto sul disco. Servivano
        # perche' senza, `core/layout.py::adatta` tagliava contro una banda
        # traslata di quanto e' alta la barra — vedi
        # docs/acceptance/AREA-DUE-RITAGLI-DUE-COORDINATE.md.
        assert primo_livello == {"topic", "area_larghezza", "area_altezza",
                                 "area_sinistra", "area_alto",
                                 "pannelli", "icone", "cartelle",
                                 "scena"}, primo_livello

        # La proprieta' vera, che l'elenco da solo non esprime: **niente che
        # nomini un'operazione o un posto sul disco.** Un elenco puo' crescere
        # per ragioni buone; questa riga non deve mai cedere, e vale anche sui
        # campi annidati che il conteggio a sei spazi non vede.
        #
        # ⚠️ `icone[].nome` porta un nome di FILE, ed e' il caso limite: e'
        # un'ETICHETTA, non un percorso. Lo schema del core rifiuta i
        # separatori proprio perche' la distinzione resti visibile fra un anno.
        for vietata in ("path", "percorso", "comando", "tool", "argv", "cmd",
                        "eseg", "file:"):
            assert vietata not in blocco.lower(), (
                f"il canale ui.layout nomina «{vietata}»: era una dichiarazione "
                "di stato, sta diventando una richiesta"
            )

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


class TestCablaggioDellaConferma:
    """Il tratto fra `fs.confirm_request` e la finestra, in `ui/src/app.js`.

    E' JavaScript e non c'e' un test runner JS in questo progetto: qui si
    verifica che il cablaggio ESISTA e passi dalle vie giuste. Che funzioni
    lo prova `scripts/verifica-conferma.mjs` guidando Electron via CDP, e il
    giro attraverso il socket lo prova `test_confirm_e2e.py`.

    Questi test non sostituiscono quelle verifiche: impediscono che un
    riordino futuro stacchi il filo senza che nessuno se ne accorga.
    """

    @property
    def _app(self) -> str:
        return (PANNELLO.parent.parent / "app.js").read_text()

    def test_si_iscrive_alla_richiesta_di_conferma(self) -> None:
        assert 'bus.su("fs.confirm_request"' in self._app

    def test_risponde_solo_tramite_il_preload(self) -> None:
        """La risposta esce per l'unica via esposta, non per un'altra."""
        assert "window.jarvis?.confirm?.(" in self._app

    def test_le_conferme_si_accodano(self) -> None:
        """Due finestre sovrapposte significano approvare senza sapere quale
        delle due si sta approvando."""
        assert "coda" in self._app and "mostraProssima" in self._app

    def test_la_finestra_non_ha_via_di_uscita_accidentale(self) -> None:
        """Si esce scegliendo. Un clic fuori non deve poter decidere."""
        assert '"no-close"' in self._app
        assert "modal: true" in self._app

    def test_la_caduta_del_core_chiude_le_conferme(self) -> None:
        """Approvare qualcosa che nessuno eseguira' e' peggio che non chiedere."""
        app = self._app
        assert "coda.length = 0" in app
