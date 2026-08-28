"""Supervisore di T1 — SPEC §5.6, e l'avvio a gradi di Fase 9."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core.llm.supervisor import (
    AUTH_ERRORS,
    ISTRUZIONE,
    ISTRUZIONE_RIPETUTI,
    USCITA_AUTH,
    EventoT1,
    Supervisore,
)

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
        assert s.auth_scaduta is True
        assert s.riavvii == 0
        # ⚠️ Che NON si riprovi lo impone chi ha il processo, ed è misurato in
        # `tests/test_t1_non_risorge_in_silenzio.py`: dopo un'auth `ask()`
        # solleva e non apre nessuna sessione nuova. Qui si fissa la metà del
        # referto: la causa è registrata, e il core è uscito una volta sola.

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
        assert s.stato == "nominal" and not r.uscite

    async def test_un_guasto_qualunque_si_riavvia(self) -> None:
        """Il contatore di vita conta i riavvii VERI, e li conta qui perché è
        l'unica metà che T1 non può avere: `jarvis doctor` la legge."""
        s = Supervisore()
        await s.riferisci(EventoT1.RIAVVIATO)
        await s.riferisci(EventoT1.RIAVVIATO)
        assert s.riavvii == 2
        assert s.stato == "nominal", "due riavvii riusciti non sono una degradazione"


class TestLaUnitEIlCodice:
    """Due costanti uguali in due file diversi divergono al primo che le tocca."""

    def test_la_unit_impedisce_il_riavvio_su_QUEL_codice(self) -> None:
        testo = UNIT.read_text()
        m = re.search(r"^RestartPreventExitStatus=([\d ]+)", testo, re.M)
        assert m, "la unit non impedisce il riavvio su nessun codice"
        codici = [int(x) for x in m.group(1).split()]
        assert codici == [USCITA_AUTH], (
            f"la unit dice {m.group(1)}, il supervisore esce con {USCITA_AUTH} "
            "e con nient'altro: un numero in piu' qui e' un caso in cui systemd "
            "non riavvia e nessuno nel core sa perche'"
        )

    def test_il_supervisore_NON_esce_per_i_riavvii_ripetuti(self) -> None:
        """⚠️ **Decisione dell'utente, 28 agosto 2026**: per un guasto non-auth
        ripetuto il core RESTA VIVO in `degraded_llm`.

        §5.6 e §16.1b dichiarano che lì T0, la telemetria, il file manager e
        l'interfaccia continuano a funzionare: uno solo dei quattro sottosistemi
        è rotto, e uscire spegnerebbe gli altri tre.

        Il freno del loop non era mai stato il codice d'uscita: è
        `ClaudeT1._degradato` più la guardia di `ask()`, e vive dentro il
        processo — quindi funziona anche
        quando il core gira a mano, fuori da systemd, che è esattamente il
        momento in cui si sta cercando di capire perché cade.
        """
        s = (RADICE / "core" / "llm" / "supervisor.py").read_text(encoding="utf-8")
        codice = "\n".join(r.split("#", 1)[0] for r in s.splitlines())
        assert "USCITA_RIPETUTI" not in codice, (
            "il codice 42 è tornato: la decisione dice di restare vivi"
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


# ── ADR-003: le due classi che mancavano ─────────────────────────────────────


def _spia(fatti=None):
    """Un supervisore che raccoglie invece di parlare, e cosa ha raccolto."""
    detto: list[str] = []
    bus: list[dict] = []
    uscite: list[int] = []
    rimessi: list[list[str]] = []

    async def parla(f):
        detto.append(f)

    async def pubblica(m):
        bus.append(m)

    s = Supervisore(parla=parla, pubblica=pubblica, esci=uscite.append)
    return s, {"detto": detto, "bus": bus, "uscite": uscite, "rimessi": rimessi}


class TestIlREFERTO:
    """⚠️ §5.6 di nuovo, a ruoli invertiti: «due metà, e quella che riferisce
    era muta».

    Misurato prima: dopo TRE riavvii veri di T1, `stato_doctor()` mostrava
    `stato: nominal, riavvii: 0` e sul bus non arrivava niente. JARVIS lo aveva
    detto a voce tre volte, e la diagnostica che §16.1b crea per rispondere a
    «cosa è rotto» non lo sapeva.

    `ClaudeT1` possiede la degradazione non-auth — processo, `returncode`,
    `stderr`, riavvio, voce. Il `Supervisore` ne tiene il **referto**: bus,
    `stato_doctor()`, contatore di vita. È l'unica metà che T1 non può avere.
    """

    async def test_un_riavvio_VERO_conta_e_finisce_sul_bus(self) -> None:
        s, r = _spia()
        await s.riferisci(EventoT1.RIAVVIATO)
        assert s.riavvii == 1
        assert r["bus"][-1]["reason"] == "riavviato"
        assert r["bus"][-1]["level"] == "warn"

    async def test_il_referto_NON_parla(self) -> None:
        """T1 ha già parlato: `FRASE_TRANSIENT` era identica carattere per
        carattere alla frase della ripresa di `claude_t1`. Due voci per un
        guasto solo."""
        s, r = _spia()
        for e in EventoT1:
            await s.riferisci(e)
        assert r["detto"] == [], r["detto"]

    async def test_una_degradazione_arriva_al_DOCTOR(self) -> None:
        s, r = _spia()
        await s.riferisci(EventoT1.RIPETUTI)
        d = s.stato_doctor()
        assert d["stato"] == "degraded_llm"
        assert d["motivo"] == "riavvii_ripetuti"
        assert d["azione"] == ISTRUZIONE_RIPETUTI
        assert r["bus"][-1]["level"] == "critical"

    async def test_la_stessa_causa_non_si_ripete(self) -> None:
        s, r = _spia()
        for _ in range(4):
            await s.riferisci(EventoT1.RIPETUTI)
        assert len(r["bus"]) == 1

    async def test_il_contatore_conta_le_VITE_non_i_rifiuti(self) -> None:
        """⚠️ Il ramo `repeated` incrementava PRIMA di decidere che non si
        riparte: il contatore diceva tre riavvii dove ce n'erano due."""
        s, _ = _spia()
        await s.riferisci(EventoT1.RIAVVIATO)
        await s.riferisci(EventoT1.RIPETUTI)
        assert s.riavvii == 1, "ha contato un riavvio che non è avvenuto"

    async def test_l_AUTH_dalla_MORTE_del_processo_esce_col_41(self) -> None:
        """⚠️ Un buco misurato di §5.6, non un caso nuovo.

        §5.6 vede solo gli eventi dello STREAM, ma un token che scade fra due
        turni fa **morire il processo**: `ClaudeT1.classifica` lo riconosce dal
        `returncode` 41 o dallo `stderr`, e quella strada non passava di qui.
        Misurato prima: T1 lo diceva a voce, e insieme zero advisory, zero
        uscite, `stato_doctor()` a `nominal` — cioè `jarvis doctor` avrebbe
        detto «auth ok» con il token scaduto, che è testualmente il difetto che
        la rev 5.29 dichiara chiuso.
        """
        s, r = _spia()
        await s.riferisci(EventoT1.AUTH_SCADUTA)
        assert r["uscite"] == [USCITA_AUTH]
        assert s.stato_doctor()["motivo"] == "auth_expired"
        assert r["bus"][-1]["reason"] == "auth_expired"
        assert r["detto"] == [], "la voce l'ha già messa T1: due voci sarebbero due"

    async def test_e_non_esce_DUE_volte_per_lo_stesso_token(self) -> None:
        s, r = _spia()
        await s.riferisci(EventoT1.AUTH_SCADUTA)
        await s.su_evento(evento_auth())
        await s.riferisci(EventoT1.AUTH_SCADUTA)
        assert len(r["uscite"]) == 1

    async def test_le_due_strade_dell_auth_si_INCONTRANO(self) -> None:
        """Stream e morte del processo scrivono lo stesso campo: chi arriva
        secondo trova già detto."""
        s, r = _spia()
        await s.su_evento(evento_auth())
        assert s.auth_scaduta is True
        await s.riferisci(EventoT1.AUTH_SCADUTA)
        assert len(r["uscite"]) == 1 and len(r["detto"]) == 1


class TestLeDueCAUSEsonoINDIPENDENTI:
    """⚠️ §5.6 poteva essere spento da un guasto che con l'autenticazione non
    c'entra.

    `su_evento` si cortocircuitava su `if self.stato == "degraded_llm"`, e
    `su_riavvio` scriveva quello stesso stato per una causa tutta diversa.
    Misurato, prima:

        supervisore PULITO           su_evento -> True   uscite=[41]
        dopo 3 cadute non-auth       su_evento -> True   uscite=[]

    Zero frasi, zero advisory, zero uscite: il token è scaduto e nessuno lo
    dice. Era latente solo perché `su_riavvio` non ha chiamanti — e la
    decisione del 28 agosto di **restare vivi** lo rendeva permanente, perché
    da `degraded_llm` non si torna indietro e il processo non muore più.

    Due guasti indipendenti vogliono due campi indipendenti.
    """

    async def test_un_AUTH_dopo_tre_cadute_fa_partire_il_41(self) -> None:
        s, r = _spia()
        await s.riferisci(EventoT1.RIPETUTI)
        assert s.degrado_t1 == "riavvii_ripetuti"

        prima = len(r["uscite"]), len(r["detto"]), len(r["bus"])
        assert await s.su_evento(evento_auth()) is True
        dopo = len(r["uscite"]), len(r["detto"]), len(r["bus"])

        assert dopo[0] == prima[0] + 1 and r["uscite"][-1] == USCITA_AUTH, (
            "il token è scaduto e il core non è uscito: §5.6 spento da un "
            "guasto che con l'autenticazione non c'entra"
        )
        assert dopo[1] == prima[1] + 1, "non l'ha detto a voce"
        assert r["bus"][-1]["reason"] == "auth_expired"

    async def test_e_il_doctor_riferisce_TUTTE_E_DUE_le_cause(self) -> None:
        """Con un campo solo, l'ultimo scrittore cancellava il primo e il
        doctor dimenticava che T1 stava già cadendo."""
        s, _ = _spia()
        await s.riferisci(EventoT1.RIPETUTI)
        await s.su_evento(evento_auth())

        d = s.stato_doctor()
        assert d["cause"] == ["auth_expired", "riavvii_ripetuti"], d["cause"]
        assert d["motivo"] == "auth_expired", (
            "fra le due, quella che chiede un'azione al Signore viene prima"
        )
        assert d["azione"] == ISTRUZIONE

    async def test_l_auth_NON_si_ripete_a_ogni_evento(self) -> None:
        """La proprietà che il cortocircuito difendeva, e che resta: stessa
        causa, una volta sola."""
        s, r = _spia()
        for _ in range(4):
            await s.su_evento(evento_auth())
        assert len(r["uscite"]) == 1 and len(r["detto"]) == 1

    async def test_una_caduta_non_auth_NON_finge_un_auth(self) -> None:
        s, _ = _spia()
        await s.riferisci(EventoT1.RIPETUTI)
        assert s.auth_scaduta is False
        assert s.stato_doctor()["motivo"] == "riavvii_ripetuti"


class TestLIstruzioneDelDOCTOR:
    """⚠️ La riga che §16.1b chiama la più importante dello strumento.

    `stato_doctor()["azione"]` era `ISTRUZIONE if stato == "degraded_llm"`,
    cioè «esegui `claude` e poi /login» per **qualunque** degradazione. Dopo
    tre cadute non-auth il doctor mostrava la causa giusta e l'istruzione
    sbagliata, e il Signore avrebbe rifatto il login per un guasto che con
    l'autenticazione non c'entra.

    Era latente finché `degraded_llm` non-auth era un preludio all'uscita del
    processo. **La decisione del 28 agosto — restare vivi — lo rende uno stato
    in cui si resta**, e quindi uno che si legge davvero.
    """

    async def test_per_l_auth_dice_di_rifare_il_LOGIN(self) -> None:
        s, _ = _spia()
        await s.su_evento(evento_auth())
        d = s.stato_doctor()
        assert d["motivo"] == "auth_expired"
        assert d["azione"] == ISTRUZIONE

    async def test_per_i_riavvii_ripetuti_dice_ALTRO(self) -> None:
        s, _ = _spia()
        await s.riferisci(EventoT1.RIPETUTI)
        d = s.stato_doctor()
        assert d["motivo"] == "riavvii_ripetuti"
        assert d["azione"] == ISTRUZIONE_RIPETUTI
        assert d["azione"] != ISTRUZIONE, (
            "il doctor dice di rifare il login per un guasto che non c'entra "
            "con l'autenticazione"
        )

    async def test_e_un_motivo_SCONOSCIUTO_non_riceve_un_istruzione_a_caso(
            self) -> None:
        """Allowlist: dire la cosa sbagliata è peggio che tacere."""
        s, _ = _spia()
        s.degrado_t1 = "una_causa_nuova"
        assert s.stato_doctor()["azione"] == ""

    def test_a_stato_NOMINALE_non_c_e_niente_da_fare(self) -> None:
        s, _ = _spia()
        assert s.stato_doctor()["azione"] == ""


