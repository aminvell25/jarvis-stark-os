"""Supervisore di T1 — SPEC §5.6, e l'avvio a gradi di Fase 9."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.llm.supervisor import AUTH_ERRORS, USCITA_AUTH, Supervisore

RADICE = Path(__file__).resolve().parent.parent
UNIT = RADICE / "packaging/jarvis-core.service"


def evento_auth(errore: str = "authentication_failed") -> dict:
    """La forma esatta di §21.5: `system` / `api_retry` col campo `error`."""
    return {"type": "system", "subtype": "api_retry", "error": errore}


class _Raccolta:
    def __init__(self) -> None:
        self.dette: list[str] = []
        self.pubblicate: list[dict] = []
        self.uscite: list[int] = []

    def supervisore(self) -> Supervisore:
        return Supervisore(
            parla=self._parla, pubblica=self._pubblica, esci=self.uscite.append
        )

    async def _parla(self, frase: str) -> None:
        self.dette.append(frase)

    async def _pubblica(self, msg: dict) -> None:
        self.pubblicate.append(msg)


class TestScadenzaAuth:
    @pytest.mark.parametrize("errore", sorted(AUTH_ERRORS))
    async def test_riconosce_e_si_ferma(self, errore: str) -> None:
        r = _Raccolta()
        s = r.supervisore()
        assert await s.su_evento(evento_auth(errore))
        assert s.stato == "degraded_llm"
        assert s.uscite_previste() if hasattr(s, "uscite_previste") else True
        assert r.uscite == [USCITA_AUTH]

    async def test_dice_PRIMA_di_uscire(self) -> None:
        """Uscire per primi significherebbe un servizio che muore senza aver
        spiegato perche': il guasto silenzioso che §5.6 esiste per evitare."""
        ordine: list[str] = []
        s = Supervisore(
            parla=lambda f: _segna(ordine, "parla"),
            pubblica=lambda m: _segna(ordine, "pubblica"),
            esci=lambda c: ordine.append("esci"),
        )
        await s.su_evento(evento_auth())
        assert ordine == ["parla", "pubblica", "esci"]

    async def test_l_annuncio_dice_cosa_fare(self) -> None:
        """Un avviso che non dice l'azione e' un avviso che si subisce."""
        r = _Raccolta()
        await r.supervisore().su_evento(evento_auth())
        assert r.dette and "scaduta" in r.dette[0]
        adv = r.pubblicate[0]
        assert adv["level"] == "critical" and adv["reason"] == "auth_expired"
        assert "/login" in adv["action"]

    async def test_NIENTE_riavvio_a_ciclo(self) -> None:
        """Il cuore di §5.6: riprovare non fa tornare valido un token, e
        produce solo un servizio che sbatte contro il muro."""
        r = _Raccolta()
        s = r.supervisore()
        await s.su_evento(evento_auth())
        assert not s.puo_riavviare
        assert not s.registra_riavvio("crash qualunque")
        assert s.riavvii == 0

    async def test_non_lo_ripete_a_ogni_evento(self) -> None:
        r = _Raccolta()
        s = r.supervisore()
        for _ in range(5):
            await s.su_evento(evento_auth())
        assert len(r.uscite) == 1 and len(r.dette) == 1


class TestAltriEventi:
    @pytest.mark.parametrize("evento", [
        {"type": "system", "subtype": "api_retry", "error": "rate_limit"},
        {"type": "system", "subtype": "api_retry", "error": "overloaded"},
        {"type": "assistant", "message": {}},
        {"type": "result", "is_error": True},
        {},
    ])
    async def test_non_si_fermano_per_niente(self, evento: dict) -> None:
        """Un `api_retry` che non e' di autenticazione e' un ritardo, e il
        Governor lo sta gia' guardando (Fase 4). Qui non si fa niente."""
        r = _Raccolta()
        s = r.supervisore()
        assert not await s.su_evento(evento)
        assert s.puo_riavviare and not r.uscite

    async def test_un_guasto_qualunque_si_riavvia(self) -> None:
        s = Supervisore()
        assert s.registra_riavvio("rete assente")
        assert s.registra_riavvio("processo ucciso")
        assert s.riavvii == 2


class TestLaUnitEIlCodice:
    """Due costanti uguali in due file diversi divergono al primo che le tocca."""

    def test_la_unit_impedisce_il_riavvio_su_QUEL_codice(self) -> None:
        testo = UNIT.read_text()
        m = re.search(r"^RestartPreventExitStatus=(\d+)", testo, re.M)
        assert m, "la unit non impedisce il riavvio su nessun codice"
        assert int(m.group(1)) == USCITA_AUTH, (
            f"la unit dice {m.group(1)}, il supervisore esce con {USCITA_AUTH}: "
            "con due numeri diversi il loop infinito di §5.6 torna"
        )

    def test_la_unit_riavvia_sempre_TRANNE_quello(self) -> None:
        testo = UNIT.read_text()
        assert re.search(r"^Restart=always", testo, re.M)

    def test_niente_direttive_che_un_servizio_utente_non_puo_applicare(self) -> None:
        """Trovato avviando la unit VERA, non validandola.

        `ProtectKernelModules=true` e' sintatticamente corretta —
        `systemd-analyze verify` la approva — e fa fallire l'avvio con
        `218/CAPABILITIES`: toglie CAP_SYS_MODULE dal bounding set, e per
        farlo serve CAP_SETPCAP, che un gestore utente non ha.

        L'elenco viene da una prova diretta, una direttiva per volta, su
        questa macchina: le altre passano tutte. Chi domani ne aggiungera'
        un'altra pescando da una guida all'irrobustimento — quasi tutte
        scritte per servizi di SISTEMA — trovera' questo test.
        """
        vietate = {
            "ProtectKernelModules",   # 218/CAPABILITIES, misurato
            "CapabilityBoundingSet",  # stessa ragione: serve CAP_SETPCAP
            "AmbientCapabilities",
            "PrivateDevices",         # implica CapabilityBoundingSet
            "PrivateUsers",           # confligge con il socket in XDG_RUNTIME_DIR
            "DynamicUser",            # un servizio utente ha gia' il suo utente
        }
        testo = UNIT.read_text()
        attive = {
            r.split("=")[0].strip()
            for r in testo.splitlines()
            if r and not r.startswith("#") and "=" in r
        }
        trovate = vietate & attive
        assert not trovate, (
            f"direttive non applicabili in un servizio utente: {sorted(trovate)}. "
            "systemd-analyze verify le approva e l'avvio fallisce con 218."
        )

    def test_startlimit_sta_in_Unit_non_in_Service(self) -> None:
        """Lo snippet di §5.6 le mette in [Service], dove systemd le IGNORA in
        silenzio: il limite di partenze non sarebbe mai stato applicato."""
        # Si taglia sulla RIGA di sezione, non sulla stringa: nel commento
        # qui sopra la parola «[Service]» compare per spiegare l'errore, e un
        # `split` ingenuo tagliava li' — facendo fallire il test su una unit
        # corretta.
        testo = UNIT.read_text()
        unit, servizio = testo.split("\n[Service]\n", 1)
        assert "StartLimitBurst" in unit and "StartLimitIntervalSec" in unit
        assert "StartLimitBurst" not in servizio


async def _segna(dove: list[str], cosa: str) -> None:
    dove.append(cosa)
