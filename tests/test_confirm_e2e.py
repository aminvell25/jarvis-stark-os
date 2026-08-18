"""Il giro completo della conferma, attraverso il socket vero — §6.2.

Gli altri test verificano i pezzi. Questo verifica che si tengano: il core
propone, il messaggio attraversa il socket UNIX, un client esterno risponde, e
solo allora il file si muove.

E' la prova che il criterio di §22 descrive — *«una conferma per operazione»* —
misurata invece che raccontata.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from websockets.asyncio.client import unix_connect

from core.engine import Engine
from core.tools import registry as R


async def _attendi(condizione, timeout: float = 10.0) -> bool:
    fine = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < fine:
        if condizione():
            return True
        await asyncio.sleep(0.02)
    return condizione()


class ClientDiProva:
    """Un client sul socket, come sara' il processo main di Electron."""

    def __init__(self, ws) -> None:
        self._ws = ws
        self.richieste: list[dict] = []
        self._task = asyncio.create_task(self._ascolta())

    async def _ascolta(self) -> None:
        async for grezzo in self._ws:
            msg = json.loads(grezzo)
            if msg.get("topic") == "fs.confirm_request":
                self.richieste.append(msg)

    async def rispondi(self, request_id: str, approvato: bool) -> None:
        await self._ws.send(json.dumps({
            "topic": "fs.confirm_response", "id": request_id, "approvato": approvato,
        }))

    async def chiudi(self) -> None:
        self._task.cancel()


@pytest.fixture
async def sistema(short_paths, tmp_path: Path):
    """Engine vero, socket vero, radice temporanea."""
    radice = (tmp_path / "radice").resolve()
    radice.mkdir()

    engine = Engine(short_paths)
    # Le radici consentite del settings di prova puntano alla home; qui si
    # lavora in una directory temporanea, e l'unico modo onesto e' dirlo al
    # sistema come farebbe un settings.toml diverso.
    engine.settings.fs.allowed_roots.clear()
    engine.settings.fs.allowed_roots.append(radice)

    task = asyncio.create_task(engine.run())
    sock = short_paths.socket_path()
    assert await _attendi(lambda: sock.is_socket()), "il socket non e' comparso"

    async with unix_connect(str(sock)) as ws:
        client = ClientDiProva(ws)
        yield {"engine": engine, "client": client, "radice": radice}
        await client.chiudi()

    engine._stop.set()
    await asyncio.wait_for(task, timeout=10)

    # I test cestinano file veri, e il cestino e' quello dell'utente: senza
    # questo, ogni esecuzione della suite ci lascia dentro qualcosa. Si
    # rimuove solo cio' che questo test ha messo, ritrovandolo dal registro.
    from core.platform.linux import LinuxPaths

    piattaforma = LinuxPaths()
    for lasciato in radice.rglob("*"):
        pass
    for nome in ("da-cestinare.txt", "da-tenere.txt", "vero.txt",
                 "protetto.txt", "dopo-spazzatura.txt"):
        ritrovato = piattaforma.find_trashed(radice / nome)
        if ritrovato and ritrovato.exists():
            info = ritrovato.parent.parent / "info" / (ritrovato.name + ".trashinfo")
            ritrovato.unlink(missing_ok=True)
            info.unlink(missing_ok=True)


class TestGiroCompleto:
    async def test_approvazione_esegue(self, sistema) -> None:
        radice, client = sistema["radice"], sistema["client"]
        bersaglio = radice / "da-cestinare.txt"
        bersaglio.write_text("contenuto")

        esito = asyncio.create_task(R.invoke("trash_path", {"path": str(bersaglio)}))
        assert await _attendi(lambda: client.richieste), "nessuna richiesta di conferma"

        richiesta = client.richieste[0]
        assert richiesta["tool"] == "trash_path"
        assert richiesta["operazioni"][0]["sorgente"] == str(bersaglio)
        assert bersaglio.exists(), "ha eseguito PRIMA della conferma"

        await client.rispondi(richiesta["id"], True)
        r = await asyncio.wait_for(esito, timeout=10)
        assert r.ok, r.error
        assert not bersaglio.exists()
        assert r.output["verificato"] is True, "non ha verificato dove e' finito"

        Path(r.output["recuperabile_da"]).unlink(missing_ok=True)

    async def test_rifiuto_non_esegue(self, sistema) -> None:
        radice, client = sistema["radice"], sistema["client"]
        bersaglio = radice / "da-tenere.txt"
        bersaglio.write_text("contenuto")

        esito = asyncio.create_task(R.invoke("trash_path", {"path": str(bersaglio)}))
        assert await _attendi(lambda: client.richieste)

        await client.rispondi(client.richieste[0]["id"], False)
        r = await asyncio.wait_for(esito, timeout=10)
        assert r.ok is False and "rifiutat" in r.error
        assert bersaglio.exists(), "ha eseguito nonostante il rifiuto"

    async def test_il_percorso_mostrato_e_risolto(self, sistema) -> None:
        """§6.2: «UI mostra il PATH ASSOLUTO RISOLTO, non quello richiesto»."""
        radice, client = sistema["radice"], sistema["client"]
        (radice / "sotto").mkdir()
        bersaglio = radice / "vero.txt"
        bersaglio.write_text("x")
        contorto = radice / "sotto" / ".." / "vero.txt"

        esito = asyncio.create_task(R.invoke("trash_path", {"path": str(contorto)}))
        assert await _attendi(lambda: client.richieste)
        mostrato = client.richieste[0]["operazioni"][0]["sorgente"]
        assert ".." not in mostrato
        assert mostrato == str(bersaglio)

        await client.rispondi(client.richieste[0]["id"], False)
        await asyncio.wait_for(esito, timeout=10)

    async def test_una_conferma_per_molte_operazioni(self, sistema) -> None:
        """§6.2: per 200 file una sola conferma, col piano completo."""
        radice, client = sistema["radice"], sistema["client"]
        for n in ("a.pdf", "b.jpg", "c.mp3", "d.zip", "e.py"):
            (radice / n).write_text("x")

        esito = asyncio.create_task(R.invoke("organize_folder", {"path": str(radice)}))
        assert await _attendi(lambda: client.richieste)
        assert len(client.richieste) == 1, "piu' di una conferma per un'operazione sola"
        assert client.richieste[0]["totale"] == 5

        await client.rispondi(client.richieste[0]["id"], True)
        r = await asyncio.wait_for(esito, timeout=10)
        assert r.ok and r.output["spostati"] == 5
        assert (radice / "Documenti" / "a.pdf").exists()

    async def test_una_risposta_a_un_id_inventato_non_fa_nulla(self, sistema) -> None:
        """Il renderer risponde a domande, non le inventa."""
        radice, client = sistema["radice"], sistema["client"]
        bersaglio = radice / "protetto.txt"
        bersaglio.write_text("x")

        esito = asyncio.create_task(R.invoke("trash_path", {"path": str(bersaglio)}))
        assert await _attendi(lambda: client.richieste)

        await client.rispondi("id-inventato-di-sana-pianta", True)
        await asyncio.sleep(0.3)
        assert not esito.done(), "un id inventato ha sbloccato l'operazione"
        assert bersaglio.exists()

        await client.rispondi(client.richieste[0]["id"], False)
        await asyncio.wait_for(esito, timeout=10)

    async def test_messaggio_malformato_non_rompe_il_canale(self, sistema) -> None:
        """Un client che sbaglia a parlare non deve fermare il core."""
        radice, client = sistema["radice"], sistema["client"]
        for spazzatura in ('{"topic":"fs.confirm_response"}', "non e' json",
                           '{"topic":"altro","id":"x","approvato":true}',
                           '{"topic":"fs.confirm_response","id":"x","approvato":true,"extra":1}'):
            await client._ws.send(spazzatura)

        bersaglio = radice / "dopo-spazzatura.txt"
        bersaglio.write_text("x")
        esito = asyncio.create_task(R.invoke("trash_path", {"path": str(bersaglio)}))
        assert await _attendi(lambda: client.richieste), "il canale si e' fermato"
        await client.rispondi(client.richieste[0]["id"], False)
        await asyncio.wait_for(esito, timeout=10)
