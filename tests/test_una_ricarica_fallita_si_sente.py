"""Il Signore corregge `settings.toml`, salva, e non succede niente.

`SettingsStore.reload()` tiene le impostazioni precedenti quando il file nuovo
non si carica, e scrive `ricarica_fallita` nel journal. `subscribe_errors` esiste
per dirlo a qualcuno, e **non aveva un chiamante**: l'ha trovato
`scripts/orfani.py`.

Il caso non è raro, ed è il peggiore per chi lo vive: da fuori è indistinguibile
da «la modifica non ha avuto effetto» o da «JARVIS l'ha ignorata», e l'unica
traccia sta in un journal che nessuno guarda mentre edita un file.

§16 dice «nessuna soglia agisce senza annunciarlo». Tenere le impostazioni
vecchie è un'azione.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _sorgente() -> str:
    return (RADICE / "core" / "engine.py").read_text(encoding="utf-8")


def _senza_commenti(s: str) -> str:
    return "\n".join(
        "" if r.lstrip().startswith(("#", "#:")) else r.split("#", 1)[0]
        for r in s.splitlines())


class TestLErroreArrivaSullaSCRIVANIA:
    async def test_un_advisory_esce_sul_socket(self, short_paths) -> None:
        from core.engine import Engine

        e = Engine(short_paths)
        inviati: list[dict] = []

        async def finto(msg):
            inviati.append(msg)

        e._ws.broadcast = finto
        e._impostazioni_non_ricaricate(ValueError("riga 12: virgola di troppo"))
        await asyncio.sleep(0)
        assert len(inviati) == 1
        assert inviati[0]["topic"] == "agent.advisory"
        assert inviati[0]["level"] == "warn"
        assert "virgola di troppo" in inviati[0]["reason"], (
            "senza il motivo, l'avviso dice che qualcosa non va e non che cosa"
        )

    async def test_dice_che_TIENE_le_precedenti(self, short_paths) -> None:
        """La cosa che il Signore deve sapere non è che il file è storto — quello
        lo sa — ma che JARVIS sta girando con le impostazioni di prima."""
        from core.engine import Engine

        e = Engine(short_paths)
        inviati: list[dict] = []

        async def finto(msg):
            inviati.append(msg)

        e._ws.broadcast = finto
        e._impostazioni_non_ricaricate(ValueError("x"))
        await asyncio.sleep(0)
        assert "precedenti" in inviati[0]["reason"]


class TestLIscrizioneESISTE:
    def test_il_core_si_ISCRIVE(self) -> None:
        assert "self._store.subscribe_errors(" in _senza_commenti(_sorgente())

    def test_PRIMA_di_far_partire_la_sorveglianza(self) -> None:
        """⚠️ `start()` accende il watchdog: iscrivendosi dopo, un file già
        storto al primo salvataggio passerebbe senza avviso."""
        c = _senza_commenti(_sorgente())
        assert c.index("subscribe_errors(") < c.index("self._store.start()")

    def test_RIMBALZA_sul_loop(self) -> None:
        """⚠️ Il richiamo arriva dal thread di watchdog, e `_advisory_sincrono`
        fa `create_task`, che di là non ha un loop. È lo stesso rimbalzo che già
        fa `_ricarica_frasi`."""
        c = _senza_commenti(_sorgente())
        dopo = c.split("subscribe_errors(", 1)[1][:300]
        assert "call_soon_threadsafe" in dopo

    def test_e_si_DISISCRIVE_allo_stop(self) -> None:
        """Un ascoltatore che sopravvive al core tiene vivo un riferimento a un
        oggetto morto, e il prossimo `Engine` ne troverebbe due."""
        c = _senza_commenti(_sorgente())
        assert "self._disiscrivi_errori()" in c


class TestNonSiDiceAVOCE:
    def test_l_annuncio_vocale_NON_c_e(self) -> None:
        """Chi ha appena salvato `settings.toml` è davanti alla tastiera:
        l'avviso sulla scrivania arriva dove sta guardando, e a voce sarebbe un
        annuncio per una cosa che ha già sotto gli occhi."""
        c = _senza_commenti(_sorgente())
        corpo = c.split("def _impostazioni_non_ricaricate", 1)[1].split(
            "\n    def ", 1)[0]
        assert "_annuncia_a_voce" not in corpo and "_dillo" not in corpo
