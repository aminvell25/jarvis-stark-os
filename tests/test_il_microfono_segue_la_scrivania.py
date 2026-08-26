"""Fuori dall'ambiente di JARVIS non si ascolta.

Il core gira sotto systemd ventiquattro ore su ventiquattro; l'app no. Fino a
oggi il microfono si apriva con il core e restava aperto: JARVIS sentiva la
frase di richiamo e rispondeva anche a finestra chiusa, che non è ciò che
«un ambiente cognitivo dentro il quale JARVIS vive» vuol dire.

**Il segnale è la connessione, non la visibilità.** Una scrivania ridotta a
icona resta collegata e JARVIS resta in ascolto — è ciò che serve a un
assistente a cui si parla senza guardarlo.

⚠️ **E conta solo chi si è DICHIARATO scrivania.** `ruolo` è un `Literal`, non
una stringa: `ws_probe.py` si collega per diagnosi e non accende niente. Se
bastasse una connessione qualunque, qualunque cosa sapesse aprire il socket
potrebbe far ascoltare JARVIS — e sarebbe una denylist travestita.

⚠️ **Il flusso si chiude davvero.** Scartare i blocchi lasciando `pw-record`
aperto terrebbe accesa la spia del microfono del sistema operativo, e quella
spia è l'unica cosa che il Signore vede senza chiedere.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from pydantic import ValidationError
from websockets.asyncio.client import unix_connect

from core.ws_server import RuoloMessage, WsServer
from tests.conftest import AudioFinto, FakeSensors


def _main_js() -> str:
    return (Path(__file__).resolve().parent.parent / "app" / "main.js"
            ).read_text(encoding="utf-8")


# ── la pipeline ──────────────────────────────────────────────────────────────

class _AudioSenzaFine(AudioFinto):
    """Un microfono che non finisce: così la chiusura del flusso è una
    DECISIONE del cancello e non l'esaurirsi di una lista."""

    def __init__(self, *a, **k) -> None:
        super().__init__(*a, **k)
        #: Quante volte il flusso è stato CHIUSO. `aperture` dice che non si è
        #: riaperto; solo questo dice che si è chiuso — ed è la differenza fra
        #: «non ascolta» e «`pw-record` è terminato», cioè fra una promessa del
        #: codice e la spia del microfono che si spegne.
        self.chiusure = 0

    def input_stream(self, sample_rate=None):
        self.aperture.append(sample_rate)

        async def gen():
            try:
                while True:
                    yield b"\x00\x30\x00\xd0" * 160
                    await asyncio.sleep(0)
            finally:
                self.chiusure += 1

        return gen()


def _pipeline(audio, consentito: bool):
    from core.providers.health import Scelta
    from core.voice.pipeline import VoicePipeline

    class _P:
        name = "finto"
        per_enunciato = False

        async def stream(self, testo):
            return
            yield                                        # pragma: no cover

        async def interrupt(self): return

    class _WakeMuto:
        """Sente i blocchi e non riconosce mai: qui si misura l'APERTURA del
        flusso, non il risveglio."""

        frasi = ("jarvis",)

        def feed(self, _pcm):
            return None

    s = Scelta(provider=_P(), primario=True, motivo="", annuncio=None)
    return VoicePipeline(audio=audio, wake=_WakeMuto(), stt=s, tts=s,
                         ascolto_consentito=consentito)


async def _gira(p, quanto: int = 30):
    for _ in range(quanto):
        await asyncio.sleep(0)


@asynccontextmanager
async def _viva(p):
    """Fa girare `run()` e la spegne SEMPRE.

    ⚠️ Senza questo, un'asserzione che fallisce lascia dietro un compito con
    un generatore infinito: la suite non fallisce, si **appende**. Trovato
    eseguendo la bocciatura — cioè il test rotto l'ha scoperto la prova che
    doveva romperlo."""
    t = asyncio.create_task(p.run())
    try:
        yield t
    finally:
        p.stop()
        try:
            await asyncio.wait_for(t, 2)
        except (TimeoutError, asyncio.TimeoutError):
            t.cancel()
            raise AssertionError("`run()` non è uscita dopo `stop()`")


class TestIlMicrofonoNonSiApreDaSolo:
    async def test_senza_scrivania_pw_record_NON_parte(self) -> None:
        """La proprietà vera: non «i blocchi si scartano», ma **il flusso non
        viene nemmeno aperto**."""
        a = _AudioSenzaFine()
        p = _pipeline(a, consentito=False)
        async with _viva(p):
            await _gira(p)
            assert a.aperture == [], "il microfono si è aperto senza una scrivania"

    async def test_quando_la_scrivania_arriva_si_apre(self) -> None:
        a = _AudioSenzaFine()
        p = _pipeline(a, consentito=False)
        async with _viva(p):
            await _gira(p)
            p.consenti(True)
            await _gira(p)
            assert len(a.aperture) == 1

    async def test_quando_se_ne_va_il_flusso_si_CHIUDE(self) -> None:
        """E non si riapre da solo: una seconda apertura vorrebbe dire che la
        spia del microfono resta accesa a finestra chiusa."""
        a = _AudioSenzaFine()
        p = _pipeline(a, consentito=True)
        async with _viva(p) as t:
            await _gira(p)
            assert len(a.aperture) == 1
            p.consenti(False)
            await _gira(p, 60)
            assert a.chiusure == 1, (
                "il flusso non si è CHIUSO: scartare i blocchi lascerebbe "
                "`pw-record` vivo e la spia del microfono accesa"
            )
            assert len(a.aperture) == 1, "l'ha riaperto"
            assert not t.done(), "revocare l'ascolto ha ucciso la pipeline"

    async def test_fermare_una_pipeline_SOSPESA_non_si_appende(self) -> None:
        """⚠️ Senza `_consentito.set()` dentro `stop()`, `run()` resterebbe su
        `wait()` per sempre e la chiusura del core andrebbe in timeout."""
        p = _pipeline(_AudioSenzaFine(), consentito=False)
        async with _viva(p):                  # basta che l'uscita non scada
            await _gira(p)

    async def test_un_microfono_MORTO_non_diventa_un_ciclo_infinito(self) -> None:
        """Un flusso che finisce da solo mentre l'ascolto è consentito è un
        guasto, non una sospensione: si esce, come faceva prima."""
        a = AudioFinto(blocchi=[b"\x00\x30\x00\xd0" * 160] * 3)
        p = _pipeline(a, consentito=True)
        await asyncio.wait_for(p.run(), 2)
        assert len(a.aperture) == 1, "ha riaperto il microfono in un ciclo"

    def test_consenti_e_IDEMPOTENTE(self) -> None:
        p = _pipeline(_AudioSenzaFine(), consentito=True)
        p.consenti(True)
        assert p.ascolta
        p.consenti(False)
        p.consenti(False)
        assert not p.ascolta


# ── il ruolo, sul socket vero ────────────────────────────────────────────────

class TestSoloChiSiDichiaraScrivania:
    def test_il_ruolo_e_una_ALLOWLIST(self) -> None:
        RuoloMessage.model_validate_json(
            '{"topic":"client.ruolo","ruolo":"scrivania"}')
        for cattivo in ('{"topic":"client.ruolo","ruolo":"amministratore"}',
                        '{"topic":"client.ruolo","ruolo":"scrivania","x":1}',
                        '{"topic":"altro","ruolo":"scrivania"}'):
            with pytest.raises(ValidationError):
                RuoloMessage.model_validate_json(cattivo)

    async def test_una_SONDA_che_si_collega_non_accende_niente(
            self, short_paths) -> None:
        """`ws_probe.py` si collega per diagnosi. Se bastasse una connessione,
        la diagnosi accenderebbe il microfono."""
        visti: list[int] = []
        srv = WsServer(dict, FakeSensors(), short_paths,
                       su_scrivania=visti.append)
        async with srv:
            async with unix_connect(str(srv.socket_path)) as ws:
                await asyncio.wait_for(ws.recv(), 5)      # lo snapshot
                await asyncio.sleep(0.05)
                assert srv.scrivanie == 0
        assert visti == [], "una connessione muta ha contato come scrivania"

    async def test_chi_si_DICHIARA_conta_e_alla_chiusura_scala(
            self, short_paths) -> None:
        visti: list[int] = []
        srv = WsServer(dict, FakeSensors(), short_paths,
                       su_scrivania=visti.append)
        async with srv:
            async with unix_connect(str(srv.socket_path)) as ws:
                await asyncio.wait_for(ws.recv(), 5)
                await ws.send(json.dumps({"topic": "client.ruolo",
                                          "ruolo": "scrivania"}))
                for _ in range(200):
                    if srv.scrivanie == 1:
                        break
                    await asyncio.sleep(0.01)
                assert srv.scrivanie == 1
            for _ in range(200):
                if srv.scrivanie == 0:
                    break
                await asyncio.sleep(0.01)
            assert srv.scrivanie == 0
        assert visti == [1, 0]

    async def test_un_ruolo_INVENTATO_non_conta(self, short_paths) -> None:
        srv = WsServer(dict, FakeSensors(), short_paths)
        async with srv:
            async with unix_connect(str(srv.socket_path)) as ws:
                await asyncio.wait_for(ws.recv(), 5)
                await ws.send(json.dumps({"topic": "client.ruolo",
                                          "ruolo": "amministratore"}))
                await asyncio.sleep(0.05)
                assert srv.scrivanie == 0


# ── la scrivania si dichiara, e lo rifà a ogni riconnessione ────────────────

class TestLaScrivaniaSiDichiara:
    def test_il_ponte_manda_il_ruolo(self) -> None:
        assert '"client.ruolo"' in _main_js()

    def test_e_lo_manda_dentro_open_cioe_a_OGNI_riconnessione(self) -> None:
        """Il core dimentica il ruolo quando la connessione cade: una
        scrivania che si ricollega senza ridichiararsi resterebbe muta —
        e sarebbe muta proprio dopo un riavvio del core, cioè quando serve."""
        s = _main_js()
        dentro = s.split('socket.on("open"', 1)[1].split("});", 1)[0]
        assert '"client.ruolo"' in dentro


class TestIlMotoreCollegaLeDueCose:
    def test_il_server_avvisa_il_motore(self) -> None:
        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        assert "su_scrivania=self._scrivanie_cambiate," in s

    def test_la_pipeline_NASCE_nello_stato_giusto(self) -> None:
        """Il core parte prima dell'app: se il valore iniziale fosse `True` il
        microfono si aprirebbe per un istante a ogni avvio."""
        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        assert "ascolto_consentito=self._ws.scrivanie > 0," in s
