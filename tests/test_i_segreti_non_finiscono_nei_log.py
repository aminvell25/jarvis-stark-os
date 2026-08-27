"""Le chiavi API non finiscono nei log — CLAUDE.md, «Stile codice».

`tests/test_secrets_never_leak.py` prova che il processore di `settings.py`
funziona **se qualcuno lo installa**. Qui si prova l'altra meta': che
`core.log.configura()` lo installa davvero, e che la redazione regge sui casi
in cui quella vecchia cedeva — il segreto annidato in un dizionario, dentro
una lista, dentro un traceback.

⚠️ Nessun valore di questi test e' una chiave vera: sono stringhe inventate,
registrate a mano nel registro dei segreti che la fixture di `conftest.py`
svuota dopo ogni prova.
"""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
import structlog
from pydantic import SecretStr

import core.log as core_log
from core.log import (MASCHERA, PROFONDITA_MASSIMA, SOGLIA_SOTTOSTRINGA,
                      _soglia_sottostringa, _valori_registrati, configura,
                      redazione)
from core.settings import SECRETS

#: Una chiave finta, lunga come una vera. Non esiste da nessuna parte.
CHIAVE = "finta_NON_REALE_a1b2c3d4e5f6a7b8"

#: Un segreto piu' corto della soglia. Serve a provare il fail-closed sulla
#: forma, non a proteggere qualcosa.
CORTO = "abc"


# ─────────────────────────────────────────────────────────────────────────────
# Attrezzatura
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def uscita() -> Any:
    """structlog configurato dalla catena VERA, che scrive in memoria.

    Non `structlog.testing.capture_logs`: quella intercetta gli eventi prima
    dei processori, quindi passerebbe anche se `configura()` non installasse
    nessuna redazione — proverebbe solo che il test sa scrivere un dizionario.
    """
    buf = io.StringIO()
    configura(livello="debug", formato="json", flusso=buf)
    yield buf
    structlog.reset_defaults()


def righe(buf: io.StringIO) -> list[dict]:
    return [json.loads(r) for r in buf.getvalue().splitlines() if r.strip()]


def applica(evento: dict) -> dict:
    """Il solo processore, senza catena: per guardare la struttura."""
    return dict(redazione(None, "info", evento))


# ─────────────────────────────────────────────────────────────────────────────
# 1. La catena installata da `configura()`
# ─────────────────────────────────────────────────────────────────────────────


class TestConfiguraInstallaLaRedazione:
    def test_una_chiave_registrata_non_esce(self, uscita: io.StringIO) -> None:
        SECRETS.register(CHIAVE)
        structlog.get_logger().info("prova", key=CHIAVE)
        testo = uscita.getvalue()
        assert CHIAVE not in testo
        assert MASCHERA in testo

    def test_la_chiave_annegata_in_una_frase_sparisce(self, uscita) -> None:
        SECRETS.register(CHIAVE)
        structlog.get_logger().warning(
            "richiesta_fallita", url=f"https://api.deepgram.com/?token={CHIAVE}&x=1"
        )
        testo = uscita.getvalue()
        assert CHIAVE not in testo
        # Il resto della riga resta leggibile: mascherare non vuol dire
        # cancellare il contesto che serve a capire l'errore.
        assert "api.deepgram.com" in testo and "x=1" in testo

    def test_un_log_senza_chiavi_resta_identico(self, uscita) -> None:
        """Con un segreto registrato ma assente dal messaggio, la riga deve
        uscire uguale a com'e' stata scritta: campo per campo, tipo per tipo."""
        SECRETS.register(CHIAVE)
        structlog.get_logger().info(
            "settings_caricate", config_dir="/home/x/.config/jarvis-os",
            chiavi=["deepgram_api_key"], quante=1, attivo=True,
        )
        [riga] = righe(uscita)
        assert riga["event"] == "settings_caricate"
        assert riga["config_dir"] == "/home/x/.config/jarvis-os"
        assert riga["chiavi"] == ["deepgram_api_key"]
        assert riga["quante"] == 1 and riga["attivo"] is True
        assert MASCHERA not in uscita.getvalue()

    def test_senza_nessun_segreto_registrato_esce_tutto(self, uscita) -> None:
        structlog.get_logger().info("nudo", testo="niente da nascondere")
        [riga] = righe(uscita)
        assert riga["testo"] == "niente da nascondere"

    def test_la_riga_di_avvio_vera_non_perde_niente(self, uscita, paths) -> None:
        """Il percorso di avvio, per intero: `configura()` e poi
        `load_settings()`, che registra le chiavi e logga da se'.

        La chiave e' quella FINTA di `conftest.SECRETS_TOML` — l'unico
        `secrets.toml` che i test vedono e' quello scritto in una directory
        temporanea dalla fixture.
        """
        from core.settings import load_settings

        impostazioni = load_settings(paths)
        finta = impostazioni.secrets.deepgram_api_key.get_secret_value()
        testo = uscita.getvalue()
        assert "settings_caricate" in testo
        assert "deepgram_api_key" in testo       # il NOME della chiave si'
        assert finta not in testo                # il VALORE no

    def test_il_traceback_viene_ripulito(self, uscita) -> None:
        """⚠️ Il caso che decide l'ORDINE della catena: `format_exc_info`
        trasforma l'eccezione in stringa, e se la redazione girasse prima
        troverebbe un oggetto e lascerebbe uscire il testo."""
        SECRETS.register(CHIAVE)
        try:
            raise RuntimeError(f"401 con la chiave {CHIAVE}")
        except RuntimeError:
            structlog.get_logger().exception("provider_ko")
        testo = uscita.getvalue()
        assert "RuntimeError" in testo          # il traceback c'e'
        assert CHIAVE not in testo              # la chiave no

    def test_anche_il_renderer_leggibile_maschera(self) -> None:
        """La redazione sta nella catena, non nel renderer: cambiando il
        formato non deve cambiare cio' che esce."""
        buf = io.StringIO()
        configura(livello="info", formato="console", flusso=buf)
        try:
            SECRETS.register(CHIAVE)
            structlog.get_logger().info("prova", key=CHIAVE)
            try:
                raise RuntimeError(f"401 con la chiave {CHIAVE}")
            except RuntimeError:
                structlog.get_logger().exception("provider_ko")
            testo = buf.getvalue()
            assert CHIAVE not in testo
            assert MASCHERA in testo and "prova" in testo
            assert "RuntimeError" in testo
        finally:
            structlog.reset_defaults()

    def test_auto_scrive_json_quando_l_uscita_non_e_un_terminale(self) -> None:
        """Sotto systemd l'uscita e' una pipe: li' serve JSON per il journal,
        e il renderer leggibile andrebbe nel giornale con i colori dentro."""
        buf = io.StringIO()                     # `isatty()` -> False
        configura(livello="info", formato="auto", flusso=buf)
        try:
            structlog.get_logger().info("prova", n=1)
            assert json.loads(buf.getvalue().strip())["n"] == 1
        finally:
            structlog.reset_defaults()

    def test_un_livello_sconosciuto_non_ferma_il_core(self) -> None:
        buf = io.StringIO()
        configura(livello="verbosissimo", formato="json", flusso=buf)
        try:
            structlog.get_logger().info("dopo")
            eventi = [r["event"] for r in righe(buf)]
            assert "livello_di_log_sconosciuto" in eventi
            assert "dopo" in eventi             # e si e' ripiegato su info
        finally:
            structlog.reset_defaults()


# ─────────────────────────────────────────────────────────────────────────────
# 2. La struttura: dove la redazione vecchia non arrivava
# ─────────────────────────────────────────────────────────────────────────────


class TestScendeNellaStruttura:
    def test_dentro_un_dizionario_annidato(self, uscita) -> None:
        SECRETS.register(CHIAVE)
        structlog.get_logger().info(
            "ws_out", msg={"tipo": "auth", "payload": {"token": CHIAVE}}
        )
        [riga] = righe(uscita)
        assert riga["msg"]["payload"]["token"] == MASCHERA
        assert riga["msg"]["tipo"] == "auth"     # il resto non si tocca

    def test_dentro_una_lista(self, uscita) -> None:
        SECRETS.register(CHIAVE)
        structlog.get_logger().info("cmd", argv=["curl", "-H", f"Bearer {CHIAVE}"])
        [riga] = righe(uscita)
        assert CHIAVE not in uscita.getvalue()
        assert riga["argv"][0] == "curl"
        assert riga["argv"][2] == f"Bearer {MASCHERA}"

    def test_lista_dentro_dizionario_dentro_lista(self, uscita) -> None:
        SECRETS.register(CHIAVE)
        structlog.get_logger().info("misto", x=[{"y": [{"z": CHIAVE}]}])
        assert CHIAVE not in uscita.getvalue()

    def test_anche_le_chiavi_del_dizionario(self) -> None:
        """Un dizionario indicizzato per token esiste (una cache di sessioni),
        e ripulirne i soli valori lascerebbe il segreto in bella vista."""
        SECRETS.register(CHIAVE)
        fuori = applica({"event": "sessioni", "per_token": {CHIAVE: 3}})
        assert CHIAVE not in json.dumps(fuori, default=str)
        assert fuori["per_token"][MASCHERA] == 3

    def test_tuple_e_insiemi_restano_del_loro_tipo(self) -> None:
        SECRETS.register(CHIAVE)
        fuori = applica({"event": "x", "t": (CHIAVE, "ok"), "s": {CHIAVE}})
        assert isinstance(fuori["t"], tuple) and fuori["t"] == (MASCHERA, "ok")
        assert isinstance(fuori["s"], set) and fuori["s"] == {MASCHERA}

    def test_i_byte_di_un_sottoprocesso(self) -> None:
        """L'uscita di `claude` arriva in byte, e i byte finiscono nei log."""
        SECRETS.register(CHIAVE)
        fuori = applica({"event": "stdout", "dati": f"x {CHIAVE}\n".encode()})
        assert isinstance(fuori["dati"], bytes)
        assert CHIAVE.encode() not in fuori["dati"]

    def test_un_oggetto_qualunque_che_stampa_la_chiave(self) -> None:
        """Il renderer stampa gli oggetti con `str()`: e' li' che si guarda."""

        class Richiesta:
            def __str__(self) -> str:
                return f"GET /v1?key={CHIAVE}"

        SECRETS.register(CHIAVE)
        fuori = applica({"event": "http", "req": Richiesta()})
        assert CHIAVE not in str(fuori["req"])

    def test_un_secretstr_non_ancora_registrato(self) -> None:
        """`SecretStr` si maschera per il TIPO, non perche' e' nel registro:
        e' l'unico caso in cui si sa che e' un segreto anche a registro vuoto."""
        fuori = applica({"event": "x", "k": SecretStr("mai_registrata_12345")})
        assert fuori["k"] == MASCHERA

    def test_oltre_la_profondita_massima_non_passa(self) -> None:
        """Fail-closed: sotto la soglia di ricorsione si perde la struttura,
        mai il segreto."""
        dentro: Any = CHIAVE
        for _ in range(PROFONDITA_MASSIMA + 3):
            dentro = {"g": dentro}
        SECRETS.register(CHIAVE)
        fuori = applica({"event": "profondo", "x": dentro})
        assert CHIAVE not in json.dumps(fuori, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# 3. La soglia — fail-closed sulla forma
# ─────────────────────────────────────────────────────────────────────────────


class TestSogliaSottostringa:
    def test_la_soglia_e_derivata_non_scelta(self) -> None:
        """Il numero viene dai tre parametri dichiarati nel modulo. Se cambia
        uno dei tre, cambia il numero: non e' una costante messa a occhio."""
        assert SOGLIA_SOTTOSTRINGA == _soglia_sottostringa(16, 1_000_000, 1e-3)
        assert SOGLIA_SOTTOSTRINGA == 8
        # Un alfabeto piu' povero (binario) richiede piu' caratteri...
        assert _soglia_sottostringa(2, 1_000_000, 1e-3) > SOGLIA_SOTTOSTRINGA
        # ...e una tolleranza piu' larga ne richiede meno.
        assert _soglia_sottostringa(16, 1_000_000, 1.0) < SOGLIA_SOTTOSTRINGA

    def test_i_parametri_impossibili_si_rifiutano(self) -> None:
        with pytest.raises(ValueError):
            _soglia_sottostringa(1, 1_000, 1e-3)
        with pytest.raises(ValueError):
            _soglia_sottostringa(16, 1_000, 0.0)

    def test_un_segreto_corto_non_mangia_il_log(self, uscita) -> None:
        """Se «abc» si mascherasse per sottostringa, ogni riga che lo contiene
        uscirebbe monca — ed e' cosi' che si rendono illeggibili tutti i log."""
        assert len(CORTO) < SOGLIA_SOTTOSTRINGA
        SECRETS.register(CORTO)
        structlog.get_logger().info("apri", path="/home/x/abcdef/nota.md")
        [riga] = righe(uscita)
        assert riga["path"] == "/home/x/abcdef/nota.md"

    def test_ma_il_segreto_corto_da_solo_si_maschera(self, uscita) -> None:
        """Fail-closed: la sottostringa no, il valore intero del campo si'."""
        SECRETS.register(CORTO)
        structlog.get_logger().info("token", valore=CORTO)
        [riga] = righe(uscita)
        assert riga["valore"] == MASCHERA

    def test_un_segreto_lungo_si_maschera_per_sottostringa(self, uscita) -> None:
        assert len(CHIAVE) >= SOGLIA_SOTTOSTRINGA
        SECRETS.register(CHIAVE)
        structlog.get_logger().info("apri", path=f"/tmp/{CHIAVE}/x")
        [riga] = righe(uscita)
        assert riga["path"] == f"/tmp/{MASCHERA}/x"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Il registro e' UNO
# ─────────────────────────────────────────────────────────────────────────────


class TestRiusaIlRegistroEsistente:
    def test_legge_il_registro_di_settings(self) -> None:
        """⚠️ Il patto con `core/settings.py`. Se `SecretRegistry` cambiasse
        la forma dei propri valori interni questo test cade, e cade QUI —
        invece di far degradare la redazione in silenzio altrove."""
        SECRETS.register(CHIAVE)
        assert _valori_registrati() == (CHIAVE,)

    def test_una_chiave_registrata_dopo_configura_e_coperta(self, uscita) -> None:
        """La catena si installa all'avvio, le chiavi arrivano dopo, col
        primo `load_settings()`. Il processore rilegge il registro a ogni
        evento: se ne tenesse una copia, questa riga uscirebbe in chiaro."""
        structlog.get_logger().info("prima")
        SECRETS.register(CHIAVE)
        structlog.get_logger().info("dopo", key=CHIAVE)
        assert CHIAVE not in uscita.getvalue()

    def test_svuotare_il_registro_smette_di_mascherare(self, uscita) -> None:
        """Il contrario del test precedente, e prova la stessa cosa: la
        sorgente e' il registro vivo, non una fotografia."""
        SECRETS.register(CHIAVE)
        SECRETS.clear()
        structlog.get_logger().info("x", key=CHIAVE)
        assert CHIAVE in uscita.getvalue()

    def test_se_il_registro_non_e_leggibile_maschera_di_piu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Il giorno in cui `SecretRegistry` rinomina i propri interni.

        Degradazione verso il piu' stretto: non potendo piu' distinguere
        lunghi e corti si passa tutto da `SECRETS.scrub()` — API pubblica, che
        maschera anche i corti. Rumore nei log, zero chiavi fuori.
        """

        class RegistroRinominato:
            """Stesso comportamento pubblico, interni con un altro nome."""

            def __init__(self) -> None:
                self._valori = {CHIAVE, CORTO}     # non piu' `_values`

            def scrub(self, testo: str) -> str:
                for s in self._valori:
                    testo = testo.replace(s, MASCHERA)
                return testo

        SECRETS.register(CHIAVE, CORTO)
        monkeypatch.setattr(core_log, "SECRETS", RegistroRinominato())
        assert _valori_registrati() is None
        fuori = applica({"event": "x", "a": CHIAVE, "b": "/home/x/abcdef"})
        assert fuori["a"] == MASCHERA
        assert MASCHERA in fuori["b"]           # anche il corto, qui


# ─────────────────────────────────────────────────────────────────────────────
# 5. Il processore non puo' rompere il log
# ─────────────────────────────────────────────────────────────────────────────


class TestNonSollevaMai:
    def test_un_oggetto_che_esplode_a_stamparsi(self) -> None:
        class Esplosivo:
            def __str__(self) -> str:
                raise RuntimeError("non mi stampo")

        SECRETS.register(CHIAVE)
        fuori = applica({"event": "x", "b": Esplosivo()})
        # Non si sa che cosa contenesse: esce la maschera, non l'oggetto.
        assert fuori["b"] == MASCHERA

    def test_un_ciclo_non_costa_la_riga_di_log(self) -> None:
        """Un dizionario che contiene se stesso non deve ne' bloccare la
        ricorsione ne' far scattare l'ultimo argine: e' il tetto di
        `PROFONDITA_MASSIMA` che lo tronca, e la riga esce comunque."""
        d: dict[str, Any] = {"k": CHIAVE}
        d["se_stesso"] = d
        SECRETS.register(CHIAVE)
        fuori = applica({"event": "x", "d": d})
        assert fuori["event"] == "x"            # non "redazione_fallita"
        assert CHIAVE not in json.dumps(fuori, default=str)

    def test_l_ultimo_argine_non_lascia_uscire_l_evento(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Se la redazione stessa si rompe, l'evento NON esce com'e': non si
        sa se conteneva una chiave."""

        def esplode(*_a: Any, **_k: Any) -> None:
            raise RuntimeError("rotto")

        SECRETS.register(CHIAVE)
        monkeypatch.setattr(core_log, "_oscura", esplode)
        fuori = applica({"event": "x", "key": CHIAVE})
        assert fuori["event"] == "redazione_fallita"
        assert CHIAVE not in json.dumps(fuori, default=str)


class TestSiGuardaAncheIlREPR:
    """⚠️ Il commento diceva «il renderer lo stamperà con `str()`». È falso.

    `JSONRenderer` serializza gli oggetti sconosciuti con `repr`, e
    `ConsoleRenderer` rende con `repr` ogni valore che non sia già una stringa.
    Una classe con `__str__` discreto e `__repr__` che mostra i campi — cioè la
    forma predefinita di ogni dataclass — usciva pulita al giudizio e con la
    chiave in chiaro sulla riga.

    E il test che avrebbe dovuto accorgersene verificava con `str(...)`, cioè
    con la stessa funzione che il codice aveva usato per decidere.
    """

    def test_un_oggetto_discreto_a_str_e_loquace_a_repr_NON_passa(self) -> None:
        from core.settings import SECRETS

        finta = "finta_NON_REALE_a1b2c3d4e5f6a7b8"
        SECRETS.register(finta)

        class Furbo:
            def __str__(self) -> str:
                return "Furbo()"

            def __repr__(self) -> str:
                return f"Furbo(key={finta!r})"

        fuori = applica({"o": Furbo()})["o"]
        assert finta not in str(fuori), "sporco con str()"
        assert finta not in repr(fuori), (
            "sporco con repr(): e' la forma che entrambi i renderer usano"
        )

    def test_un_oggetto_PULITO_in_entrambe_le_forme_esce_intatto(self) -> None:
        """La redazione non deve mascherare ciò che non ha niente da nascondere:
        `Untrusted` ha `__repr__` che dice l'origine e i caratteri, ed è
        esattamente quello che serve leggere in un log."""
        class Pulito:
            def __repr__(self) -> str:
                return "<Pulito origine='guardian' caratteri=15>"

        o = Pulito()
        assert applica({"o": o})["o"] is o, (
            "un oggetto pulito ha perso il proprio tipo"
        )
