"""`initiatives/` era una cartella in sola scrittura.

Esiste dalla Fase 4, e la docstring di `registra_iniziativa` dice — testuale —
*«Ciò che JARVIS ha fatto di propria iniziativa, **visibile al risveglio**»*.

Non lo era: nessuno leggeva quel file. Il file il cui unico scopo è essere letto
al risveglio non aveva un lettore, e la cartella è rimasta a zero righe fino al
27 agosto.

È la firma del JARVIS dei film: ha lavorato mentre Lei non c'era, e al ritorno
dice **una conclusione**.
"""

from __future__ import annotations

import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _sorgente(nome: str) -> str:
    return (RADICE / nome).read_text(encoding="utf-8")


def _senza_commenti(s: str) -> str:
    fuori = []
    for r in s.splitlines():
        t = "" if r.lstrip().startswith(("#", "#:")) else r.split("#", 1)[0]
        fuori.append(t)
    return "\n".join(fuori)


def _store(tmp_path: Path):
    from core.memory.store import MemoryStore

    return MemoryStore(tmp_path)


class TestInitiativesHaUnLettore:
    def test_rilegge_cio_che_ha_scritto(self, tmp_path: Path) -> None:
        s = _store(tmp_path)
        s.registra_iniziativa("consolidamento", {"sessione": "x", "turni": 3})
        fatte = s.iniziative_dal(0)
        assert len(fatte) == 1 and fatte[0]["tipo"] == "consolidamento"

    def test_il_taglio_e_STRETTO_sul_timbro(self, tmp_path: Path) -> None:
        """`> da` e non `>=`: rileggendo con il proprio timbro non si
        riferisce due volte la stessa iniziativa."""
        s = _store(tmp_path)
        s.registra_iniziativa("consolidamento", {})
        ts = s.iniziative_dal(0)[0]["ts"]
        assert s.iniziative_dal(ts) == []

    def test_una_riga_STORTA_non_fa_cadere_il_risveglio(self, tmp_path: Path) -> None:
        s = _store(tmp_path)
        s.registra_iniziativa("consolidamento", {})
        (s.initiatives / "rotto.jsonl").write_text("{non json\n")
        assert len(s.iniziative_dal(0)) == 1


class TestLaFraseVieneDaiDATI:
    def test_il_resoconto_NON_passa_da_un_modello(self) -> None:
        """⚠️ Non è un risparmio, è una proprietà. Ciò che JARVIS dice di aver
        FATTO non deve poter essere inventato: un modello che riassume un
        registro può sbagliare un numero o aggiungere una riga che non c'era."""
        s = _senza_commenti(_sorgente("core/memory/risveglio.py"))
        for vietato in ("ClaudeT2", "esegui(", "_t2", "governor", "Governor"):
            assert vietato not in s, f"{vietato} nel compositore del resoconto"

    def test_niente_da_riferire_si_DICE(self) -> None:
        from core.memory.risveglio import componi

        assert componi([]) == "Niente da riferire, Signore."

    def test_uno_e_due_concordano(self) -> None:
        from core.memory.risveglio import componi

        assert "1 sessione." in componi([{"tipo": "consolidamento"}])
        assert "2 sessioni." in componi([{"tipo": "consolidamento"}] * 2)

    def test_prosa_e_non_elenco(self) -> None:
        """§5.7: «Nessun elenco, nessun markdown, nessuna emoji: non si
        pronunciano»."""
        from core.memory.risveglio import componi

        t = componi([{"tipo": "consolidamento"}, {"tipo": "ronda"}])
        assert "\n" not in t and "- " not in t and "*" not in t
        assert " e " in t, "due cose si uniscono con «e», non con una virgola"

    def test_un_tipo_SENZA_frase_non_inventa(self) -> None:
        from core.memory.risveglio import componi

        t = componi([{"tipo": "cosa_nuova"}])
        assert "cosa_nuova" not in t, "pronuncerebbe un nome di codice (§5.7)"
        assert "1 cosa che non so ancora raccontare" in t

    def test_ogni_tipo_REGISTRATO_ha_la_sua_frase(self) -> None:
        """⚠️ La guardia che conta. Chi aggiunge un'iniziativa nuova e scorda
        la frase lascia a JARVIS qualcosa che non sa raccontare, e senza questo
        test se ne accorgerebbe soltanto sentendolo."""
        import re

        from core.memory.risveglio import FRASI

        registrati = set()
        for f in (RADICE / "core").rglob("*.py"):
            for m in re.finditer(r'registra_iniziativa\(\s*"([^"]+)"',
                                 _senza_commenti(f.read_text(encoding="utf-8"))):
                registrati.add(m.group(1))
        assert registrati, "nessun chiamante trovato: il grep è rotto"
        assert registrati <= set(FRASI), f"senza frase: {registrati - set(FRASI)}"


class TestQuandoSiDiceCheNonCeNiente:
    def test_appena_detto_NON_si_ripete(self, tmp_path: Path) -> None:
        """Dirlo a ogni riconnessione — ventisette riavvii in tre giorni — lo
        trasformerebbe in rumore, e il rumore si ignora."""
        from core.memory.risveglio import e_ora_di_dirlo

        assert e_ora_di_dirlo(time.time()) is False

    def test_dopo_un_giorno_SI(self, tmp_path: Path) -> None:
        from core.memory.consolidate import PERIODO_S
        from core.memory.risveglio import e_ora_di_dirlo

        ora = time.time()
        assert e_ora_di_dirlo(ora, adesso=ora + PERIODO_S - 60) is False
        assert e_ora_di_dirlo(ora, adesso=ora + PERIODO_S + 60) is True

    def test_il_confine_e_LO_STESSO_di_5_5(self) -> None:
        """Non un numero nuovo: l'unica cosa che JARVIS fa da solo ha periodo
        giornaliero, quindi un giorno è il più piccolo intervallo in cui
        «niente» sia un'informazione."""
        s = _senza_commenti(_sorgente("core/memory/risveglio.py"))
        assert "from core.memory.consolidate import PERIODO_S" in s
        corpo = s.split("def e_ora_di_dirlo", 1)[1].split("\n\ndef ", 1)[0]
        # Via la docstring: spiega il confine per esteso, e cercare la stringa
        # nuda sarebbe verde per il commento invece che per il codice.
        assert "PERIODO_S" in corpo.split('"""', 2)[-1]


class TestIlMotoreLoRACCONTA:
    def test_scatta_quando_la_scrivania_ARRIVA(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("def _scrivanie_cambiate", 1)[1].split("\n    async def ", 1)[0]
        assert "self._resoconto_al_risveglio(" in dopo

    def test_e_NON_dipende_dalla_voce(self) -> None:
        """⚠️ Legarlo a `self._voce is not None` avrebbe reso il risveglio muto
        con la voce spenta, che è la configurazione predefinita di §7.1."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        dopo = s.split("def _scrivanie_cambiate", 1)[1].split("\n    async def ", 1)[0]
        prima_del_return = dopo.split("if self._voce is None:", 1)[0]
        assert "self._resoconto_al_risveglio(" in prima_del_return

    def test_va_nel_flusso_AZIONE_non_dialogo(self) -> None:
        """⚠️ Trovato dal vivo: con `dialogo` la frase compariva DUE volte —
        una mia e una del turno che la pronuncia, perché `annuncia()` produce
        un `Turno` e `_annota_dialogo` lo scrive.

        Non sono un duplicato da sopprimere, sono due fatti: qui JARVIS ha
        deciso di RIFERIRE, e resta anche a voce spenta; in `dialogo` finisce
        ciò che ha DETTO, se l'ha detto.
        """
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]
        assert 'intento="resoconto_al_risveglio"' in corpo
        assert '"dialogo"' not in corpo

    def test_si_SCRIVE_prima_di_parlare(self) -> None:
        """Il diario è su disco e si legge a voce spenta; EdgeTTS è di rete. A
        ordine rovesciato, una rete assente cancellerebbe il resoconto invece
        di renderlo muto."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]
        assert corpo.index("self._diario.annota(") < corpo.index("self._dillo(")

    def test_una_voce_che_cade_non_perde_il_FATTO(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]
        dopo_dillo = corpo.split("self._dillo(", 1)[1]
        assert "except Exception" in dopo_dillo


# ── dal 2 settembre 2026: il risveglio legge anche il DIARIO ─────────────────
#
# Fino ad allora sapeva dire che cosa JARVIS aveva FATTO, non che cosa si era
# ROTTO: i guasti andavano nel log, che senza systemd non viene scritto.
# Misurato sul disco vero: 91 righe di diario in otto giorni, zero `ok=False`.


def _diario(tmp_path: Path):
    from core.diario import Diario

    return Diario(tmp_path / "diario")


def _riga(d, ts: float, **campi) -> None:
    """Una riga con un `ts` scelto: `scrivi()` timbra con l'orologio, e qui
    serve raccontare ieri."""
    import json

    riga = {"ts": ts, "flusso": "azione", "traccia": None, **campi}
    with d._file(ts).open("a", encoding="utf-8") as f:
        f.write(json.dumps(riga, ensure_ascii=False) + "\n")


class TestOgniGuastoEmessoHaLaSuaFrase:
    def test_ogni_tipo_EMESSO_ha_la_sua_frase(self) -> None:
        """⚠️ La guardia che conta, come per le iniziative: chi emette un tipo
        di guasto nuovo e scorda la frase lascia a JARVIS qualcosa che non sa
        raccontare."""
        import re

        from core.memory.risveglio import DERIVATI, GUASTI

        emessi = set()
        for f in (RADICE / "core").rglob("*.py"):
            for m in re.finditer(r'_annota_guasto\(\s*[^,]+,\s*"([^"]+)"',
                                 _senza_commenti(f.read_text(encoding="utf-8"))):
                emessi.add(m.group(1))
        assert emessi, "nessun emettitore trovato: il grep è rotto"
        assert emessi <= set(GUASTI), f"senza frase: {emessi - set(GUASTI)}"
        # I derivati non li emette nessuno con quel nome: li deduce il lettore
        # dalla forma della riga, e devono avere la frase lo stesso.
        assert not (emessi & DERIVATI)
        assert DERIVATI <= set(GUASTI)

    def test_l_emettitore_e_UNO_e_scrive_ok_False(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _annota_guasto", 1)[1].split("\n    def ", 1)[0]
        # ⚠️ Via la docstring, o il test e' verde per il commento: sabotando
        # `ok=False` in `ok=True` la prima versione restava verde perche' la
        # docstring dice «`ok=False`». E' l'ottava volta in questo progetto.
        codice = corpo.split('"""', 2)[-1]
        assert '"azione"' in codice and "ok=False" in codice
        assert 'else "referto"' in codice, "senza traccia la riga dice da dove viene"

    async def test_la_riga_sul_DISCO_e_un_guasto(self, tmp_path: Path) -> None:
        """Il comportamento, non la forma: i metodi VERI di `Engine` su un
        diario vero, come fa `tests/test_la_traccia_non_si_perde.py`."""
        from core.engine import Engine
        from core.traccia import Origine, Traccia

        class _Finto:
            def __init__(self, diario) -> None:
                self._diario, self._compiti = diario, set()

        _Finto._annota_guasto = Engine._annota_guasto
        d = _diario(tmp_path)
        f = _Finto(d)
        t = Traccia.nuova(Origine.AVVIO)
        await f._annota_guasto(t, "protocollo", errore="caduto", strada="protocollo",
                               nome="ronda", dettaglio="RuntimeError('boom')")
        await f._annota_guasto(None, "t1_degradato", errore="non_risponde", strada="t1")
        righe = d.leggi(None, "azione", limite=10 ** 9)
        assert [r["intento"] for r in righe] == ["protocollo", "t1_degradato"]
        assert all(r["ok"] is False and r["flusso"] == "azione" for r in righe)
        assert righe[0]["traccia"] == t.id and righe[0]["da"] == "avvio"
        assert righe[1]["traccia"] is None and righe[1]["da"] == "referto"
        assert righe[0]["dettaglio"] == "RuntimeError('boom')"
        # E la riga e' un guasto per il lettore: la catena si chiude.
        from core.memory.risveglio import classifica_guasti

        assert [tp for tp, _ in classifica_guasti(righe, time.time())] == [
            "protocollo", "t1_degradato"]

    def test_le_cause_di_T1_sono_quelle_del_supervisore(self) -> None:
        from core.llm.supervisor import EventoT1
        from core.memory.risveglio import CAUSE

        assert set(CAUSE["t1_degradato"]) == {e.value for e in EventoT1}

    def test_le_cause_del_ripiego_sono_i_due_Motivi_di_guasto(self) -> None:
        from core.memory.risveglio import CAUSE
        from core.providers.health import Motivo

        assert set(CAUSE["ripiego_voce"]) == {Motivo.CHIAVE_ASSENTE, Motivo.ERRORE}
        assert Motivo.CONFIGURATO not in CAUSE["ripiego_voce"], \
            "un ripiego chiesto dalle impostazioni non è un guasto"

    def test_le_cause_del_protocollo_sono_CAUSE_ESITO(self) -> None:
        from core.memory.risveglio import CAUSE
        from core.protocolli import CAUSE_ESITO

        assert set(CAUSE["protocollo"]) == set(CAUSE_ESITO)

    def test_il_no_del_Signore_e_quello_di_confirm(self) -> None:
        from core.memory.risveglio import ESITI_DI_CONFERMA
        from core.tools.confirm import Esito

        assert set(ESITI_DI_CONFERMA) == {Esito.RIFIUTATO, Esito.SCADUTO}


class TestIlLettoreDelDiario:
    def test_il_taglio_e_STRETTO_e_il_limite_non_tronca(self, tmp_path: Path) -> None:
        """`Diario.leggi()` ha `limite=200` per il pannello: un giorno pieno
        perderebbe la mattina."""
        from core.memory.risveglio import righe_dal

        d = _diario(tmp_path)
        base = time.time() - 3600
        for i in range(250):
            _riga(d, base + i, intento="open_panel", ok=True)
        assert len(righe_dal(d, base)) == 249, "`> da`, e tutte le 249"
        assert righe_dal(d, base + 249) == []

    def test_legge_anche_IERI(self, tmp_path: Path) -> None:
        from core.memory.risveglio import righe_dal

        d = _diario(tmp_path)
        ieri = time.time() - 86400
        _riga(d, ieri + 10, intento="protocollo", ok=False, errore="caduto")
        _riga(d, time.time() - 5, intento="open_panel", ok=True)
        assert len(righe_dal(d, ieri)) == 2


class TestCheCosaEUnGuasto:
    def _guasti(self, righe, avviato_a=None):
        from core.memory.risveglio import classifica_guasti

        return classifica_guasti(righe, time.time() if avviato_a is None else avviato_a)

    def test_ok_False_e_un_guasto_e_ok_True_no(self) -> None:
        g = self._guasti([{"flusso": "azione", "intento": "open_panel", "ok": True},
                          {"flusso": "azione", "intento": "open_panel", "ok": False,
                           "errore": "boh", "strada": "ui"}])
        assert [(t, len(v)) for t, v in g] == [("comando_fallito", 1)]

    def test_un_verdetto_FALLITO_e_un_guasto_anche_con_ok_True(self) -> None:
        """ADR-012: «riuscito ma smentito» è la riga per cui il contratto
        esiste."""
        g = self._guasti([{"flusso": "azione", "intento": "create_file", "ok": True,
                           "verdetto": "fallito"}])
        assert [t for t, _ in g] == ["comando_smentito"]

    def test_non_verificato_e_onesto_non_rotto(self) -> None:
        assert self._guasti([{"flusso": "azione", "intento": "copy_path", "ok": True,
                              "verdetto": "non_verificato"}]) == []

    def test_il_NO_del_Signore_non_e_un_guasto(self) -> None:
        assert self._guasti([
            {"flusso": "azione", "intento": "trash_path", "ok": False,
             "errore": "operazione rifiutato"},
            {"flusso": "azione", "intento": "trash_path", "ok": False,
             "errore": "operazione scaduto"},
        ]) == []

    def test_il_resoconto_e_il_ciclo_di_vita_non_lo_sono(self) -> None:
        assert self._guasti([
            {"flusso": "azione", "intento": "resoconto_al_risveglio", "ok": False},
            {"flusso": "azione", "intento": "core_avviato", "ok": False},
            {"flusso": "azione", "intento": "core_fermato", "ok": False},
        ]) == []

    def test_il_dialogo_non_lo_e_mai(self) -> None:
        assert self._guasti([{"flusso": "dialogo", "ok": False}]) == []

    def test_una_frase_caduta_senza_T1_e_senza_risposta(self) -> None:
        g = self._guasti([{"flusso": "azione", "intento": None, "ok": False,
                           "strada": "caduto", "errore": "t1_assente"}] * 3)
        assert [(t, len(v)) for t, v in g] == [("senza_risposta", 3)]

    def test_il_ripiego_di_QUESTO_avvio_non_si_ripete(self) -> None:
        """L'invariante 12 l'ha appena fatto dire a voce; quello di un avvio
        precedente — un riavvio nella notte — invece si dice, perché nessuno
        l'ha sentito."""
        ora = time.time()
        righe = [{"flusso": "azione", "intento": "ripiego_voce", "ok": False,
                  "errore": "chiave assente", "ts": ora - 5},
                 {"flusso": "azione", "intento": "ripiego_voce", "ok": False,
                  "errore": "chiave assente", "ts": ora - 7200}]
        g = self._guasti(righe, avviato_a=ora - 60)
        assert [(t, len(v)) for t, v in g] == [("ripiego_voce", 1)]
        assert g[0][1][0]["ts"] == ora - 7200

    def test_si_raggruppa_per_tipo_E_causa(self) -> None:
        g = self._guasti([
            {"flusso": "azione", "intento": "protocollo", "ok": False, "errore": "caduto"},
            {"flusso": "azione", "intento": "protocollo", "ok": False, "errore": "caduto"},
            {"flusso": "azione", "intento": "protocollo", "ok": False, "errore": "non registrato"},
        ])
        assert [(t, len(v)) for t, v in g] == [("protocollo", 2), ("protocollo", 1)]


class TestDaQuandoAQuandoEraSpento:
    def _spento(self, righe, avviato_a, da):
        from core.memory.risveglio import intervallo_spento

        return intervallo_spento(righe, avviato_a, da)

    def test_acceso_all_ultimo_resoconto_niente_da_dire(self) -> None:
        ora = time.time()
        assert self._spento([], avviato_a=ora - 3600, da=ora - 60) is None

    def test_il_PRIMO_avvio_di_sempre_non_e_uno_spegnimento(self) -> None:
        """Trovato in laboratorio: al primo giro il resoconto diceva «non ho
        registrato lo spegnimento» di un processo mai esistito."""
        ora = time.time()
        righe = [{"intento": "core_avviato", "ts": ora - 30}]
        assert self._spento(righe, avviato_a=ora - 31, da=0.0) is None

    def test_uno_spegnimento_PULITO_ha_da_e_a(self) -> None:
        ora = time.time()
        righe = [{"intento": "core_fermato", "ts": ora - 9 * 3600},
                 {"intento": "core_avviato", "ts": ora - 60}]
        s = self._spento(righe, avviato_a=ora - 62, da=ora - 10 * 3600)
        assert s is not None and s.pulito and s.da == ora - 9 * 3600
        assert s.riavvii == 0, "l'avvio di adesso non è un riavvio"
        assert abs(s.durata_s - (9 * 3600 - 62)) < 1

    def test_senza_core_fermato_NON_si_inventa(self) -> None:
        """Invariante 23: un crash non lascia `core_fermato`, e allora si dice
        l'ultima cosa scritta e che lo spegnimento non è registrato."""
        ora = time.time()
        righe = [{"intento": "core_avviato", "ts": ora - 9 * 3600},
                 {"intento": "open_panel", "ts": ora - 8 * 3600}]
        s = self._spento(righe, avviato_a=ora - 62, da=ora - 10 * 3600)
        assert s is not None and not s.pulito and s.ultima == ora - 8 * 3600
        assert s.riavvii == 1

    def test_l_ULTIMO_evento_del_ciclo_di_vita_decide(self) -> None:
        """Fermato, riavviato, poi morto senza dirlo: non è uno spegnimento
        pulito, anche se un `core_fermato` c'è."""
        ora = time.time()
        righe = [{"intento": "core_fermato", "ts": ora - 9 * 3600},
                 {"intento": "core_avviato", "ts": ora - 8 * 3600},
                 {"intento": "open_panel", "ts": ora - 7 * 3600}]
        s = self._spento(righe, avviato_a=ora - 62, da=ora - 10 * 3600)
        assert s is not None and not s.pulito

    def test_non_dai_BUCHI_fra_le_righe(self) -> None:
        s = _senza_commenti(_sorgente("core/memory/risveglio.py"))
        corpo = s.split("def intervallo_spento", 1)[1].split("\ndef ", 1)[0]
        assert "core_fermato" in corpo and "core_avviato" in corpo


class TestLaFraseDeiGuasti:
    def _componi(self, guasti, spento=None, fatte=()):
        from core.memory.risveglio import componi

        return componi(list(fatte), guasti, spento, adesso=time.time())

    def test_la_causa_viene_dalla_tabella_e_non_dal_testo_libero(self) -> None:
        t = self._componi([("protocollo", [{"nome": "Scaricati", "errore": "non registrato",
                                            "dettaglio": "list_dir non registrato"}])])
        assert "il protocollo Scaricati non e' potuto girare perche' il suo strumento non era registrato" in t
        assert "list_dir" not in t, "il dettaglio si legge, non si pronuncia"

    def test_una_causa_IGNOTA_non_si_inventa(self) -> None:
        from core.memory.risveglio import IGNOTA

        t = self._componi([("consolidamento", [{"errore": "RuntimeError: boom"}])])
        assert IGNOTA in t and "RuntimeError" not in t

    def test_nessun_nome_di_codice_a_voce(self) -> None:
        """§5.7: si pronuncia italiano, non `ripiego_voce`."""
        from core.memory.risveglio import GUASTI

        for tipo, f in GUASTI.items():
            t = f([{"errore": "x", "ts": time.time(), "nome": "n", "server": "s",
                    "strada": "nessuna"}], time.time())
            # «protocollo» e «consolidamento» sono parole italiane; i nomi con
            # il trattino basso no, e il trattino basso non si pronuncia mai.
            assert "_" not in t, (tipo, t)
            assert "x" != t and "perche' per" not in t, (tipo, t)

    def test_uno_e_due_concordano_anche_qui(self) -> None:
        uno = self._componi([("comando_fallito", [{"strada": "nessuna"}])])
        due = self._componi([("comando_fallito", [{"strada": "nessuna"}] * 2)])
        assert "un comando non e' riuscito" in uno and "mandarlo" in uno
        assert "2 comandi non sono riusciti" in due and "mandarli" in due

    def test_spento_da_solo_si_DICE(self) -> None:
        from core.memory.risveglio import Spento

        ora = time.time()
        t = self._componi([], Spento(a=ora - 60, da=ora - 9 * 3600))
        assert t.startswith("Signore, sono stato spento da ")
        assert "Per il resto, niente da riferire." in t

    def test_un_crash_dice_che_non_lo_ha_registrato(self) -> None:
        from core.memory.risveglio import Spento

        ora = time.time()
        t = self._componi([], Spento(a=ora - 60, ultima=ora - 3 * 3600, riavvii=2))
        assert "non ho registrato lo spegnimento" in t.lower()
        assert "riavviato altre 2 volte" in t

    def test_le_tre_parti_stanno_insieme_in_PROSA(self) -> None:
        from core.memory.risveglio import Spento

        ora = time.time()
        t = self._componi([("t1_degradato", [{"errore": "riavviato"}] * 2)],
                          Spento(a=ora - 60, da=ora - 9 * 3600),
                          fatte=[{"tipo": "consolidamento"}])
        assert t.startswith("Mentre non c'era, Signore: ho messo in ordine gli appunti di 1 sessione.")
        assert "Sono stato spento da" in t
        assert "ho dovuto riavviare la sessione di Claude 2 volte" in t
        assert "\n" not in t and "- " not in t and "*" not in t

    def test_l_orario_si_pronuncia(self) -> None:
        from core.memory.risveglio import _quando

        adesso = time.mktime((2026, 9, 2, 8, 2, 0, 0, 0, -1))
        assert _quando(adesso - 3600, adesso) == "oggi alle 7:02"
        assert _quando(adesso - 9 * 3600, adesso) == "ieri alle 23:02"
        assert _quando(adesso - 3 * 86400, adesso) == "il 30 agosto alle 8:02"


class TestIlMotoreLeggeIlDiarioAlRisveglio:
    def _corpo(self) -> str:
        s = _senza_commenti(_sorgente("core/engine.py"))
        return s.split("async def _resoconto_al_risveglio", 1)[1].split("\n    async def ", 1)[0]

    def test_legge_il_diario_PRIMA_di_comporre(self) -> None:
        c = self._corpo()
        assert c.index("righe_dal(") < c.index("componi(")
        assert "classifica_guasti(" in c and "intervallo_spento(" in c

    def test_tace_solo_se_non_c_e_NIENTE(self) -> None:
        c = self._corpo()
        assert "not guasti" in c and "spento is None" in c

    def test_avviato_a_viene_dal_tempo_di_vita_non_da_una_riga(self) -> None:
        assert "time.time() - self.uptime_s" in self._corpo()

    def test_core_avviato_PRIMA_dei_gradi_e_core_fermato_DOPO_averli_spenti(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("    async def run(self) -> None:", 1)[1].split("\n    def ", 1)[0]
        assert corpo.index('intento="core_avviato"') < corpo.index("await self._gradi()")
        assert corpo.index("await self._spegni_gradi()") < corpo.index('intento="core_fermato"')

    def test_la_notte_conia_la_traccia_PRIMA_di_consolidare(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _consolida_di_notte", 1)[1].split("\n    async def ", 1)[0]
        assert corpo.count("Traccia.nuova(Origine.PROTOCOLLO)") == 2
        for ramo in corpo.split("conso.esegui()")[:-1]:
            assert "Traccia.nuova(Origine.PROTOCOLLO)" in ramo

    def test_il_protocollo_che_NON_gira_lascia_la_sua_riga(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _ronda_di", 1)[1].split("\n    def ", 1)[0]
        assert "if not esito.eseguito:" in corpo
        dopo = corpo.split("if not esito.eseguito:", 1)[1].split("if not esito.cambiato:", 1)[0]
        assert '_annota_guasto(' in dopo and '"protocollo"' in dopo

    async def test_il_resoconto_sul_DISCO_dice_i_guasti_e_lo_spento(self, tmp_path: Path) -> None:
        """Il giro intero sulla parte pura: un diario di ieri con un guasto e
        uno spegnimento, e la frase che ne esce."""
        from core.memory.risveglio import (classifica_guasti, componi,
                                           intervallo_spento, righe_dal)

        d = _diario(tmp_path)
        ora = time.time()
        da = ora - 10 * 3600
        _riga(d, da + 60, intento="ripiego_voce", ok=False, errore="chiave assente",
              da="avvio", strada="voce")
        _riga(d, da + 3600, intento="core_fermato", ok=True, da="avvio", strada="core")
        _riga(d, ora - 30, intento="core_avviato", ok=True, da="avvio", strada="core")
        righe = righe_dal(d, da)
        avviato_a = ora - 31
        g = classifica_guasti(righe, avviato_a)
        sp = intervallo_spento(righe, avviato_a, da)
        t = componi([], g, sp, adesso=ora)
        assert "sono stato spento da" in t.lower()
        assert "sono partito con la voce di ripiego perche' non ho trovato la chiave" in t


class TestUnaSessioneNonConsolidataEUnGuasto:
    """Trovato in laboratorio il 2 settembre 2026 con `claude` fuori dal PATH:
    due turni letti, zero topic, un advisory di un istante, e il mattino dopo
    il resoconto non sapeva che gli appunti non erano in ordine."""

    async def test_il_consolidatore_CONTA_le_sessioni_cadute(self, tmp_path: Path) -> None:
        from types import SimpleNamespace

        from core.memory.consolidate import Consolidatore

        s = _store(tmp_path)
        s.registra_turno("2026-09-01", {"utente": "ricordati Otto", "jarvis": "Certo.",
                                       "azione": None})

        class _T2Caduto:
            async def esegui(self, compito: str, etichetta: str):
                return SimpleNamespace(ok=False, testo="", errore="FileNotFoundError: claude",
                                       costo_usd=0.0, durata_s=0.0)

        avvisi: list[dict] = []
        conso = Consolidatore(s, _T2Caduto(), su_advisory=avvisi.append)
        esito = await conso.esegui()
        assert esito["eseguito"] is True and esito["topic"] == 0
        assert esito["fallite"] == 1, esito
        assert avvisi, "l'advisory di prima resta: e' l'istante, il diario e' il giorno dopo"

    def test_il_motore_la_riferisce_come_CADUTA(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        corpo = s.split("async def _riferisci_consolidamento", 1)[1].split("\n    async def ", 1)[0]
        codice = corpo.split('"""', 2)[-1]
        assert 'esito.get("fallite")' in codice and 'errore="caduto"' in codice
        assert 'errore="quota"' in codice
