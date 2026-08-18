"""core/sandbox/runner — il criterio di §22: la sandbox blocca davvero.

Questi test **eseguono** bubblewrap. Verificare l'argv non basta: un argv
giusto passato a un kernel che vieta gli user namespace produce comunque un
processo che non parte, e un argv giusto con un bind sbagliato produce un
processo che scrive dove non deve.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.sandbox.runner import SandboxTimeout, run_sandboxed


@pytest.fixture
def radice(tmp_path: Path) -> Path:
    d = tmp_path / "rw"
    d.mkdir()
    return d.resolve()


class TestScrittura:
    async def test_dentro_la_radice_riesce(self, radice: Path) -> None:
        rc, _, err = await run_sandboxed(
            ["/usr/bin/touch", str(radice / "file.txt")], [radice], [radice], 15
        )
        assert rc == 0, err
        assert (radice / "file.txt").exists(), "la scrittura non e' arrivata all'host"

    @pytest.mark.parametrize("bersaglio", ["/etc/intruso", "/usr/local/intruso"])
    async def test_fuori_dalla_radice_fallisce(self, radice: Path, bersaglio: str) -> None:
        rc, _, err = await run_sandboxed(
            ["/usr/bin/touch", bersaglio], [radice], [radice], 15
        )
        assert rc != 0
        assert "read-only" in err.lower()
        assert not Path(bersaglio).exists(), "l'host e' stato modificato"

    async def test_home_non_scrivibile(self, radice: Path) -> None:
        bersaglio = Path.home() / "intruso-di-prova"
        rc, _, _ = await run_sandboxed(
            ["/usr/bin/touch", str(bersaglio)], [radice], [radice], 15
        )
        assert rc != 0 and not bersaglio.exists()


class TestRete:
    async def test_risoluzione_dns_fallisce(self, radice: Path) -> None:
        rc, _, _ = await run_sandboxed(
            ["/usr/bin/getent", "hosts", "one.one.one.one"], [radice], [radice], 15
        )
        assert rc != 0

    async def test_connessione_tcp_irraggiungibile(self, radice: Path) -> None:
        """La prova che conta: non "il DNS non risolve" ma "il pacchetto non
        esce". Fallire il DNS sarebbe compatibile con una rete raggiungibile
        e un resolver rotto."""
        rc, out, _ = await run_sandboxed(
            ["/usr/bin/python3", "-c",
             "import socket\n"
             "try:\n"
             "    socket.create_connection(('1.1.1.1', 443), timeout=3)\n"
             "    print('RAGGIUNTA')\n"
             "except OSError as e:\n"
             "    print('irraggiungibile', e.errno)"],
            [radice], [radice], 20,
        )
        assert rc == 0
        assert "RAGGIUNTA" not in out, "la rete e' uscita dal namespace"
        assert "irraggiungibile" in out

    async def test_solo_loopback_via_netlink(self, radice: Path) -> None:
        """`--unshare-all` crea un namespace di rete vuoto: via netlink —
        che e' consapevole dei namespace — resta solo `lo`."""
        rc, out, _ = await run_sandboxed(
            ["/bin/sh", "-c", "ip -o link | wc -l"], [radice], [radice], 15
        )
        assert rc == 0 and out.strip() == "1"

    async def test_sys_e_quello_dellhost_in_sola_lettura(self, radice: Path) -> None:
        """PROPRIETA' REGISTRATA, non difetto corretto.

        `/sys` dentro la sandbox e' il sysfs dell'HOST, perche' §3.4 prescrive
        `--ro-bind / /` e bubblewrap non offre un rimontaggio di sysfs. Quindi
        `ls /sys/class/net` elenca le interfacce vere della macchina anche se
        il namespace di rete e' vuoto.

        Non e' un varco di ACCESSO — la rete resta irraggiungibile, lo provano
        i due test sopra — ma e' una divulgazione di INFORMAZIONE sull'hardware.
        Aggiungere `--tmpfs /sys` la chiuderebbe, ed e' uno scostamento da §3.4
        che non faccio in Fase 1 senza chiederlo: e' annotato fra i punti aperti
        di `docs/acceptance/FASE-01.md`.

        Questo test esiste perche' il giorno in cui qualcuno aggiunge
        `--tmpfs /sys` fallisca, e la decisione venga presa di proposito.
        """
        rc, out, _ = await run_sandboxed(
            ["/bin/sh", "-c", "ls /sys/class/net"], [radice], [radice], 15
        )
        assert rc == 0
        assert len(out.split()) >= 1
        rc2, _, err2 = await run_sandboxed(
            ["/usr/bin/touch", "/sys/intruso"], [radice], [radice], 15
        )
        assert rc2 != 0, "/sys deve restare in sola lettura"


class TestCicloDiVita:
    async def test_uscita_non_zero_non_solleva(self, radice: Path) -> None:
        """Un comando che fallisce e' un risultato, non un guasto."""
        rc, _, _ = await run_sandboxed(["/bin/false"], [radice], [radice], 15)
        assert rc != 0

    async def test_timeout_uccide(self, radice: Path) -> None:
        with pytest.raises(SandboxTimeout):
            await run_sandboxed(["/bin/sleep", "30"], [radice], [radice], 1.0)

    async def test_stdout_catturato(self, radice: Path) -> None:
        rc, out, _ = await run_sandboxed(
            ["/bin/echo", "ciao"], [radice], [radice], 15
        )
        assert rc == 0 and out.strip() == "ciao"
