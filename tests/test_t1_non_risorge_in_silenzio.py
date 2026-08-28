"""T1 moriva e rinasceva vuoto, e JARVIS rispondeva come se niente fosse.

`ClaudeT1.ask()` conteneva, dentro il `try`:

    if not self.vivo:
        await self.start()

Il processo di T1 muore — OOM, crash, stream desincronizzato — e la chiamata
successiva ne apre uno **nuovo con la sessione vuota**. JARVIS risponde con la
stessa voce avendo perso la conversazione, **senza dirlo**.

`docs/acceptance/ADR-003-LAMNESIA-SI-ANNUNCIA.md` lo chiama testualmente *«il
modo di fallire peggiore che questo sistema possa avere»*, e la funzione che lo
fa bene — `riavvia_dopo_guasto`, che reinietta i soli fatti fissati e **annuncia**
— non aveva un solo chiamante in produzione.

L'ha trovata `scripts/orfani.py`, rimesso nel repo lo stesso giorno.

## Le due maniere di non essere vivo

    `_proc is None`         mai avviato, o fermato di proposito da `stop()`:
                            si avvia e basta, non c'è niente da annunciare
    returncode non nullo    è MORTO da solo: si passa da `riavvia_dopo_guasto`

Confonderle vorrebbe dire annunciare un'amnesia a ogni avvio del core.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent


class _ProcMorto:
    """Un processo che è morto: `returncode` c'è, e non è zero."""

    def __init__(self, returncode: int = 137) -> None:
        self.returncode = returncode
        self.pid = 4242


def _t1(**kw):
    from core.llm.claude_t1 import ClaudeT1

    return ClaudeT1("haiku", Path("/tmp"), **kw)


class TestUnProcessoMORTOnonSiRiavviaInSilenzio:
    async def test_ask_passa_da_riavvia_dopo_guasto(self) -> None:
        t1 = _t1()
        t1._proc = _ProcMorto()
        passato: list[str] = []

        async def finto():
            passato.append("riavvio")
            from core.llm.claude_t1 import Uscita

            return Uscita.TRANSIENT

        t1.riavvia_dopo_guasto = finto

        async def start_finto():
            passato.append("start")

        t1.start = start_finto
        try:
            async for _ in t1.ask("ciao"):
                pass
        except Exception:
            pass
        assert "riavvio" in passato, (
            "il processo morto e' stato rimpiazzato senza passare da ADR-003"
        )

    async def test_e_un_processo_MAI_AVVIATO_no(self) -> None:
        """Confondere le due vorrebbe dire annunciare un'amnesia a ogni avvio
        del core."""
        t1 = _t1()
        assert t1._proc is None
        passato: list[str] = []

        async def finto():                     # pragma: no cover
            passato.append("riavvio")
            raise AssertionError("non c'era niente da riavviare")

        t1.riavvia_dopo_guasto = finto

        async def start_finto():
            passato.append("start")

        t1.start = start_finto
        try:
            async for _ in t1.ask("ciao"):
                pass
        except Exception:
            pass
        assert passato == ["start"]

    async def test_degradato_SOLLEVA_invece_di_rispondere(self) -> None:
        """⚠️ Rispondere dopo una degradazione sarebbe esattamente la bugia che
        questo blocco esiste per impedire: `_degrada` ha già annunciato, e una
        risposta dopo l'annuncio direbbe che va tutto bene."""
        import pytest

        from core.llm.claude_t1 import Uscita

        t1 = _t1()
        t1._proc = _ProcMorto()

        async def degradato():
            return Uscita.AUTH

        t1.riavvia_dopo_guasto = degradato
        with pytest.raises(RuntimeError, match="degradato"):
            async for _ in t1.ask("ciao"):
                pass

    async def test_sta_PRIMA_della_bandiera_di_occupato(self) -> None:
        """⚠️ `riavvia_dopo_guasto` usa `ask()` per reiniettare i fatti: a
        bandiera già alzata la rientranza solleverebbe «T1 è già impegnato»,
        cioè la correzione dell'amnesia diventerebbe un turno perso."""
        t1 = _t1()
        t1._proc = _ProcMorto()
        visto: list[bool] = []

        async def guarda():
            visto.append(t1._occupato)
            from core.llm.claude_t1 import Uscita

            return Uscita.TRANSIENT

        t1.riavvia_dopo_guasto = guarda

        async def start_finto():
            return

        t1.start = start_finto
        try:
            async for _ in t1.ask("ciao"):
                pass
        except Exception:
            pass
        assert visto == [False], "la bandiera era gia' alzata: rientranza"


class _ProcFinto:
    """Un processo che si può uccidere e che non esiste."""

    def __init__(self, rc: int | None = None) -> None:
        self.returncode = rc
        self.stdin = self

    def write(self, b: bytes) -> None: ...
    async def drain(self) -> None: ...
    def close(self) -> None: ...
    def kill(self) -> None: self.returncode = -9
    async def wait(self) -> int | None: return self.returncode


def _t1_con_spie(fatti=(), rc=1, spia_ask: bool = True):
    """Un `ClaudeT1` vero, con `start` — e su richiesta `ask` — sostituiti.

    ⚠️ `spia_ask=False` per i test della GUARDIA di `ask()`: lì il metodo vero
    serve, o si misurerebbe la spia.
    """
    from core.llm.claude_t1 import ClaudeT1

    detti: list[str] = []
    avvii: list[int] = []
    reiniettati: list[str] = []

    t1 = ClaudeT1(modello="x", cwd="/tmp", su_annuncio=detti.append,
                  fatti_fissati=lambda: list(fatti))
    t1._proc = _ProcFinto(rc=rc)

    async def start():
        avvii.append(1)
        t1._proc = _ProcFinto()

    async def ask(testo, **kw):
        reiniettati.append(testo)
        if False:                                        # pragma: no cover
            yield

    t1.start = start
    if spia_ask:
        t1.ask = ask
    return t1, detti, avvii, reiniettati


class TestIlRiavvioFaCioCheADR003CHIEDE:
    """⚠️ Erano tre assertion sul SORGENTE, e la prima riscrittura che non
    cambiava il comportamento le ha fatte cadere. Dodicesima volta in questa
    sessione. Riscritte come comportamento — e così facendo hanno trovato che
    il comportamento era rotto."""

    async def test_reinietta_i_SOLI_fatti_fissati(self) -> None:
        """Mai i turni: l'invariante 17 vieta di duplicare la gestione del
        contesto di T1, e riprodurre la conversazione darebbe due gestori in
        disaccordo."""
        from core.llm.claude_t1 import Uscita

        t1, _, _, reiniettati = _t1_con_spie(fatti=["preferisce il caffè amaro"])
        assert await t1.riavvia_dopo_guasto() is Uscita.TRANSIENT
        assert len(reiniettati) == 1
        assert "caffè amaro" in reiniettati[0]

    async def test_e_ANNUNCIA_sempre(self) -> None:
        """L'annuncio non è facoltativo: §16 dice «nessuna soglia agisce senza
        annunciarlo», e un'amnesia taciuta è la soglia peggiore."""
        t1, detti, _, _ = _t1_con_spie(fatti=["una preferenza"])
        await t1.riavvia_dopo_guasto()
        assert len(detti) == 1 and "riavviare la sessione" in detti[0]

    async def test_dopo_il_riavvio_T1_E_VIVO(self) -> None:
        """⚠️ **Il difetto che le assertion sul sorgente non potevano vedere.**

        `riavvia_dopo_guasto` chiudeva con `await self._degrada(TRANSIENT)` per
        annunciare — e `_degrada` comincia con `await self.stop()`. Riavviava
        T1, gli rimetteva i fatti fissati, **poi lo uccideva**, e annunciava
        «ho riavviato la sessione, ho conservato le Sue preferenze».

        Misurato: `T1 è VIVO dopo il riavvio? False`. Il recupero di ADR-003
        era un no-op che annunciava successo.
        """
        t1, _, avvii, _ = _t1_con_spie(fatti=["una preferenza"])
        await t1.riavvia_dopo_guasto()
        assert avvii == [1], "non ha riavviato"
        assert t1.vivo is True, (
            "T1 è morto subito dopo essere stato riavviato: i fatti reiniettati "
            "sono finiti in una sessione uccisa un istante dopo"
        )

    async def test_e_la_frase_dice_le_preferenze_SOLO_se_ce_ne_sono(self) -> None:
        """«Ho conservato le Sue preferenze» con zero fatti fissati è una
        promessa che nessuno ha mantenuto — ed è ciò che diceva in esercizio,
        perché `fatti_fissati` non era cablato dalla radice di composizione."""
        t1, detti, _, reiniettati = _t1_con_spie(fatti=[])
        await t1.riavvia_dopo_guasto()
        assert reiniettati == [], "non c'era niente da rimettere"
        assert len(detti) == 1
        assert "conservato le Sue preferenze" not in detti[0], detti[0]
        assert "senza la conversazione" in detti[0]


class TestLAnnuncioVIENEPRIMADelReplay:
    """⚠️ La ragione sta scritta da giorni nel docstring di
    `Supervisore.su_riavvio`: «l'annuncio prima del replay: se il replay
    fallisse, l'utente ha comunque sentito che la conversazione non c'è più».

    In `ClaudeT1` l'ordine era capovolto — dentro la correzione che doveva
    chiudere ADR-003. Misurato: con un replay che solleva, **zero frasi**,
    `_degradato` già azzerato e una sessione viva e VUOTA, quindi al turno dopo
    la guardia è falsa e JARVIS risponde senza conversazione e senza fatti, in
    silenzio.
    """

    async def test_se_il_replay_SOLLEVA_il_Signore_lo_sente_lo_stesso(self) -> None:
        t1, detti, _, _ = _t1_con_spie(fatti=["una preferenza"])

        async def ask_rotta(testo, **kw):
            raise RuntimeError("la sessione nuova non accetta il contesto")
            if False:                                    # pragma: no cover
                yield

        t1.ask = ask_rotta
        await t1.riavvia_dopo_guasto()
        assert detti, (
            "nessuna frase: l'amnesia è tornata silenziosa, ed è testualmente "
            "«il modo di fallire peggiore che questo sistema possa avere»"
        )
        assert "riavviare la sessione" in detti[0]

    async def test_e_gli_si_dice_che_le_preferenze_NON_ci_sono_piu(self) -> None:
        """La prima frase promette di rimetterle. Lasciarla sola sarebbe una
        promessa non mantenuta."""
        t1, detti, _, _ = _t1_con_spie(fatti=["una preferenza"])

        async def ask_rotta(testo, **kw):
            raise RuntimeError("no")
            if False:                                    # pragma: no cover
                yield

        t1.ask = ask_rotta
        await t1.riavvia_dopo_guasto()
        assert len(detti) == 2, detti
        assert "non sono riuscito a rimettere" in detti[1]

    async def test_un_replay_fallito_NON_spreca_il_riavvio_riuscito(self) -> None:
        """La sessione è viva: far fallire il turno butterebbe via un riavvio
        che è andato a buon fine."""
        t1, _, avvii, _ = _t1_con_spie(fatti=["una preferenza"])

        async def ask_rotta(testo, **kw):
            raise RuntimeError("no")
            if False:                                    # pragma: no cover
                yield

        t1.ask = ask_rotta
        esito = await t1.riavvia_dopo_guasto()           # non solleva
        assert avvii == [1] and t1.vivo is True
        assert esito is not None

    async def test_la_frase_non_dichiara_COMPIUTO_cio_che_deve_ancora_riuscire(
            self) -> None:
        """Detta prima del replay, «ho conservato» sarebbe falsa nell'istante
        in cui viene pronunciata."""
        t1, detti, _, _ = _t1_con_spie(fatti=["una preferenza"])
        await t1.riavvia_dopo_guasto()
        assert "ho conservato" not in detti[0].lower(), detti[0]


class TestUnaDEGRADAZIONELasciaIlSegno:
    """⚠️ `_degrada` chiama `stop()`, che azzera `_proc`. Senza un segno che
    sopravviva, al turno dopo la guardia «è morto da solo?» era **falsa** e si
    cadeva su `if not self.vivo: await self.start()`: sessione nuova, vuota,
    in silenzio. L'amnesia che ADR-003 esiste per vietare, un turno dopo."""

    async def test_dopo_un_AUTH_il_turno_dopo_NON_apre_una_sessione_vuota(
            self) -> None:
        from core.llm.claude_t1 import Uscita

        t1, detti, avvii, _ = _t1_con_spie(spia_ask=False)
        await t1._degrada(Uscita.AUTH)
        assert t1._proc is None, "questo test presuppone che `stop()` azzeri `_proc`"

        with pytest.raises(RuntimeError, match="degradato"):
            async for _ in t1.ask("ciao"):
                pass                                     # pragma: no cover
        assert avvii == [], "ha aperto una sessione nuova con l'auth scaduta"
        assert len(detti) == 1, "l'annuncio si ripete a ogni turno"

    async def test_il_TIMEOUT_passa_dalla_STESSA_porta(self) -> None:
        """Il ramo più frequente di tutti. Prima chiamava `_degrada` e usciva,
        e il turno dopo apriva una sessione vuota senza dire niente."""
        from core.llm.claude_t1 import Uscita

        t1, detti, _, _ = _t1_con_spie(spia_ask=False)
        await t1._degrada(Uscita.TRANSIENT)              # ciò che fa il timeout
        assert "non ha risposto in tempo" in detti[0], (
            "annuncia un riavvio che non è avvenuto"
        )

        class _Sentinella(Exception):
            """Perché il turno dopo si fermi qui, e si veda che ci è passato."""

        passato: list[int] = []

        async def spia():
            passato.append(1)
            raise _Sentinella

        t1.riavvia_dopo_guasto = spia
        with pytest.raises(_Sentinella):
            async for _ in t1.ask("ciao"):
                pass                                     # pragma: no cover
        assert passato == [1], "il turno dopo non è passato dal riavvio annunciato"

    async def test_dopo_un_riavvio_RIUSCITO_il_segno_e_tolto(self) -> None:
        """⚠️ L'ha trovato la bocciatura: togliendo l'azzeramento non cadeva
        nessun test. L'altra metà c'era e questa no.

        Senza, il segno resta per sempre: ogni turno successivo ripasserebbe da
        `riavvia_dopo_guasto`, cioè T1 riavviato a ogni frase — e l'annuncio a
        ogni frase con lui.
        """
        import contextlib

        from core.llm.claude_t1 import ClaudeT1, Uscita

        t1, _, _, _ = _t1_con_spie(fatti=["una preferenza"])
        # ⚠️ Si parte da uno stato DAVVERO degradato, o il segno sarebbe già
        # `None` in partenza e il test passerebbe togliendo la cura — è la
        # prima stesura, e la bocciatura l'ha respinta.
        await t1._degrada(Uscita.TRANSIENT)
        assert t1._degradato is Uscita.TRANSIENT
        await t1.riavvia_dopo_guasto()

        chiamate: list[int] = []

        async def spia():
            chiamate.append(1)
            return None

        t1.riavvia_dopo_guasto = spia
        t1.ask = ClaudeT1.ask.__get__(t1)            # il metodo VERO, con la guardia
        with contextlib.suppress(Exception):
            async for _ in t1.ask("ciao"):
                pass                                 # pragma: no cover
        assert chiamate == [], (
            "il segno non è stato tolto: T1 si riavvia a ogni turno, per sempre"
        )

    async def test_il_segno_si_toglie_SOLO_dopo_un_avvio_riuscito(self) -> None:
        """Se `start()` solleva, lo stato resta degradato: altrimenti la cura
        si disarmerebbe da sola proprio quando serve."""
        from core.llm.claude_t1 import Uscita

        t1, _, _, _ = _t1_con_spie()

        async def start_rotta():
            raise OSError("claude non parte")

        t1.start = start_rotta
        await t1._degrada(Uscita.TRANSIENT)
        with pytest.raises(OSError):
            await t1.riavvia_dopo_guasto()
        assert t1._degradato is Uscita.TRANSIENT

    async def test_un_AUTH_ricordato_NON_torna_transitorio(self) -> None:
        """⚠️ Dopo `stop()` il processo non c'è più, e `classifica(1)` direbbe
        `TRANSIENT` a un token scaduto: si riproverebbe a ciclo proprio nel
        caso in cui §5.6 vieta di riprovare."""
        from core.llm.claude_t1 import Uscita

        t1, _, avvii, _ = _t1_con_spie()
        await t1._degrada(Uscita.AUTH)
        assert await t1.riavvia_dopo_guasto() is Uscita.AUTH
        assert avvii == []


class TestLaRADICECablaIFattiFissati:
    """«Ho conservato le Sue preferenze» era falsa in esercizio: il default di
    `ClaudeT1.__init__` è `lambda: []`, e la radice di composizione passava
    `fatti_fissati` al `Supervisore` e non a T1."""

    def test_l_engine_lo_passa_a_T1(self) -> None:
        import inspect

        from core.engine import Engine

        src = inspect.getsource(Engine)
        corpo = src.split("self._t1 = ClaudeT1(", 1)[1].split("await self._t1.start", 1)[0]
        codice = [r.split("#", 1)[0] for r in corpo.splitlines()]
        assert any("fatti_fissati=" in r for r in codice), (
            "T1 non riceve i fatti fissati: `riavvia_dopo_guasto` reinietta la "
            "lista vuota e annuncia di aver conservato le preferenze"
        )


class TestT1RIFERISCEaChiTieneIlReferto:
    """L'altra metà della giunzione: che T1 lo dica davvero.

    Misurato prima: dopo tre riavvii veri, `jarvis doctor` mostrava
    `nominal, riavvii: 0` e sul bus non c'era niente.
    """

    def _t1(self, fatti=("una preferenza",), rc=1):
        from core.llm.supervisor import Supervisore

        bus, uscite = [], []

        async def pubblica(m):
            bus.append(m)

        sup = Supervisore(pubblica=pubblica, esci=uscite.append)
        t1, detti, avvii, _ = _t1_con_spie(fatti=fatti, rc=rc)
        t1._riferisci = sup.riferisci
        return t1, sup, bus, uscite, detti, avvii

    async def test_un_riavvio_riuscito_arriva_al_DOCTOR(self) -> None:
        t1, sup, bus, _, _, _ = self._t1()
        await t1.riavvia_dopo_guasto()
        assert sup.riavvii == 1, "il doctor direbbe ancora `riavvii: 0`"
        assert bus and bus[-1]["reason"] == "riavviato"

    async def test_una_degradazione_arriva_al_DOCTOR(self) -> None:
        from core.llm.claude_t1 import Uscita

        t1, sup, bus, _, _, _ = self._t1()
        await t1._degrada(Uscita.REPEATED)
        assert sup.stato_doctor()["motivo"] == "riavvii_ripetuti"
        assert bus[-1]["level"] == "critical"

    async def test_l_AUTH_dalla_MORTE_del_processo_fa_uscire_il_core(self) -> None:
        """§5.6 vede solo lo stream. Un token che scade fra due turni fa morire
        il processo, e prima quella strada non arrivava a nessuno: zero
        advisory, zero uscite, `stato_doctor()` a `nominal`."""
        from core.llm.claude_t1 import Uscita

        t1, sup, bus, uscite, detti, _ = self._t1(rc=41)
        await t1.riavvia_dopo_guasto()
        assert uscite == [41], "il core non è uscito con il token scaduto"
        assert sup.stato_doctor()["motivo"] == "auth_expired"
        assert len(detti) == 1, "una voce sola: T1 parla, il referto no"

    async def test_un_referto_che_CADE_non_ferma_il_riavvio(self) -> None:
        """Perdere una riga sul bus è meno grave che perdere la sessione."""
        t1, _, _, _, _, avvii = self._t1()

        async def rotto(_e):
            raise RuntimeError("il bus non risponde")

        t1._riferisci = rotto
        await t1.riavvia_dopo_guasto()
        assert avvii == [1] and t1.vivo is True

    async def test_e_senza_referto_T1_funziona_lo_stesso(self) -> None:
        """Il canale arriva per funzione: i test lo costruiscono senza."""
        t1, _, avvii, _ = _t1_con_spie(fatti=["x"])
        assert t1._riferisci is None
        await t1.riavvia_dopo_guasto()
        assert avvii == [1]


class TestIlRamoGESTITODalSupervisoreLasciaIlSegno:
    """⚠️ Lo stesso difetto di `_degrada`, nel ramo che allora non avevo
    toccato.

    Quando il supervisore gestisce l'auth, `ask()` fa `stop()` — che azzera
    `_proc` — ed esce. Senza segno, al turno dopo la guardia è falsa e si cade
    su `if not self.vivo: await self.start()`: sessione nuova, vuota, in
    silenzio, con il token ancora scaduto.
    """

    def _t1_che_riceve_un_auth(self):
        import json

        from core.llm.claude_t1 import ClaudeT1

        evento = json.dumps({"type": "system", "subtype": "api_retry",
                             "error": "authentication_failed"}).encode() + b"\n"

        class _Stdout:
            def __init__(self): self.righe = [evento, b""]
            async def readline(self): return self.righe.pop(0)

        class _Proc:
            returncode = None
            def __init__(self): self.stdout = _Stdout(); self.stdin = self
            def write(self, b): pass
            async def drain(self): pass
            def close(self): pass
            def kill(self): self.returncode = -9
            async def wait(self): return self.returncode

        gestiti: list[dict] = []

        async def su_evento(e):
            gestiti.append(e)
            return True                      # il supervisore ha gestito

        t1 = ClaudeT1("x", Path("/tmp"), su_evento=su_evento)
        t1._proc = _Proc()
        return t1, gestiti

    async def test_dopo_che_il_supervisore_ha_gestito_resta_il_segno(self) -> None:
        from core.llm.claude_t1 import Uscita

        t1, gestiti = self._t1_che_riceve_un_auth()
        async for _ in t1.ask("ciao"):
            pass
        assert gestiti, "il ramo non è stato attraversato: il test non prova nulla"
        assert t1._proc is None, "`stop()` non ha azzerato `_proc`"
        assert t1._degradato is Uscita.AUTH, (
            "nessun segno: al turno dopo JARVIS apre una sessione vuota in "
            "silenzio, col token ancora scaduto"
        )

    async def test_e_il_turno_dopo_NON_risponde(self) -> None:
        t1, _ = self._t1_che_riceve_un_auth()
        async for _ in t1.ask("ciao"):
            pass

        avviata = []

        async def start():
            avviata.append(1)

        t1.start = start
        with pytest.raises(RuntimeError, match="degradato"):
            async for _ in t1.ask("e adesso?"):
                pass                                     # pragma: no cover
        assert avviata == [], "ha aperto una sessione nuova con il token scaduto"


class TestLaRADICECablaIlREFERTO:
    def test_l_engine_lo_passa_a_T1(self) -> None:
        import inspect

        from core.engine import Engine

        src = inspect.getsource(Engine)
        corpo = src.split("self._t1 = ClaudeT1(", 1)[1].split("await self._t1.start", 1)[0]
        codice = [r.split("#", 1)[0] for r in corpo.splitlines()]
        assert any("riferisci=" in r for r in codice), (
            "T1 non ha il canale del referto: dopo tre riavvii veri "
            "`jarvis doctor` direbbe ancora `nominal, riavvii: 0`"
        )
