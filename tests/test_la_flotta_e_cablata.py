"""Le giunzioni che la radice di composizione ha fatto oggi — e solo quelle.

## Perche' questo file esiste

Questo progetto ha un difetto ricorrente con un nome preciso: **due meta'
scritte, provate, e mai congiunte**. §5.29, §5.33, §13, l'ottava giunzione
delle news, `set_frasi()` senza chiamanti, i quattro tool di memoria mai
registrati. Ogni volta il pezzo mancante era **una riga** nella radice di
composizione, e ogni volta i test delle due meta' erano verdi.

Un cablaggio senza un test che cade quando lo si toglie e' esattamente la
condizione che ha prodotto quei difetti. Qui sotto ce n'e' uno per giunzione, e
ognuno e' stato **bocciato**: la riga e' stata rimossa da `core/engine.py`, il
test e' diventato rosso, la riga e' stata rimessa.

## Che cosa NON e' cablato, e va letto come una dichiarazione

* **I subagent di T2.** Chi ha misurato il perimetro ha dichiarato un difetto
  invece di cablare: il tool di delega e' gia' invocabile sotto `dontAsk` pur
  non essendo in `--allowedTools`, quindi il default oggi e' «tutti i subagent»
  e non «nessuno». Il nome da spegnere (`Task` o `Agent`) non e' misurato.
  Cablare a indovinare sarebbe stato peggio di non cablare.
* **Lo scanner degli orfani** e le tre giunzioni del pannello diario: i loro
  autori hanno dichiarato «nessuna riga da cablare», e non ce n'e'.
"""

from __future__ import annotations

import io

import pytest
import structlog

import core.engine as mod_engine
from core.engine import Engine, main
from core.log import configura as configura_vera
from core.news.gate import Contesto
from core.settings import SECRETS, SecretRegistry


# ─────────────────────────────────────────────────────────────────────────────
# Attrezzatura
# ─────────────────────────────────────────────────────────────────────────────

#: Finta, e finta in modo evidente. Lunga sopra `SOGLIA_SOTTOSTRINGA` perche'
#: la redazione dei segreti corti e' un'altra proprieta', provata dal file di
#: chi ha scritto `core/log.py`: qui interessa solo che la catena sia INSTALLATA.
CHIAVE_FINTA = "finta_NON_REALE_c4f3e2d1b0a9"


class _EngineFinto:
    """Un `Engine` che non apre niente: nessun socket, nessuna impostazione.

    `main()` costruisce e fa girare il motore vero, e qui non interessa: la
    domanda e' che cosa succede **prima** di quella costruzione.
    """

    #: Chi e' stato costruito, in ordine. Di classe: `main()` costruisce da se'.
    ordine: list[str] = []

    def __init__(self) -> None:
        type(self).ordine.append("engine")
        self._codice_uscita = 0

    async def run(self) -> None:
        return


@pytest.fixture
def structlog_pulito():
    """structlog e' GLOBALE: senza questo, `configura()` di un test resterebbe
    installata per tutti quelli dopo, e un file di test cambierebbe l'esito di
    un altro a seconda dell'ordine."""
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


@pytest.fixture
def main_senza_engine(monkeypatch, structlog_pulito):
    """`main()` con l'unica cosa vera che ci interessa: la riga prima di tutto.

    Ritorna il buffer su cui i log finiscono davvero.

    ⚠️ **Si sostituisce il FLUSSO, non la funzione.** La catena installata e'
    quella vera di `core/log.py`, redazione compresa: cambia solo dove scrive.
    Sostituire `sys.stderr` non basterebbe — pytest lo rimpiazza da se' fra la
    preparazione del test e la sua esecuzione, e `configura()` lo lega al
    momento della chiamata. Il parametro `flusso` esiste per questo.

    Conseguenza voluta: se qualcuno togliesse `core_log.configura()` da
    `main()`, questo involucro non verrebbe mai chiamato, il buffer resterebbe
    vuoto, e i test qui sotto direbbero di no invece di passare per assenza.

    ⚠️ Si sostituisce `mod_engine.core_log.configura` e non un nome importato:
    e' `core/engine.py` a importare il MODULO, apposta, perche'
    `scripts/orfani.py` conta i richiami per nome e non risolve gli alias.
    Riscrivere quell'import come `from core.log import configura as ...`
    rimetterebbe `core.log.configura` fra gli orfani «provato, mai congiunto»,
    e qui fa cadere questi test con un `AttributeError` invece di lasciar
    tornare la misura sbagliata in silenzio.
    """
    _EngineFinto.ordine = []
    buffer = io.StringIO()

    def _configura_sul_buffer(*a, **k) -> None:
        _EngineFinto.ordine.append("log")
        configura_vera(*a, flusso=buffer, **k)

    monkeypatch.setattr(mod_engine.core_log, "configura", _configura_sul_buffer)
    monkeypatch.setattr(mod_engine, "Engine", _EngineFinto)
    return buffer


class _VoceFinta:
    """Una pipeline vocale ridotta alla SOLA cosa che il gate deve sapere.

    ⚠️ Definisce `sta_parlando` e **non** `_sta_parlando`, di proposito: la
    riga che questo cablaggio ha sostituito leggeva il campo privato di un
    altro modulo. Se qualcuno ce la rimettesse, qui esploderebbe con un
    `AttributeError` invece di continuare a funzionare per coincidenza.
    """

    def __init__(self, parla: bool | None, frase: bool = False) -> None:
        self.sta_parlando = parla
        # §15 «mai a meta' frase»: il terzo campo del `Contesto`, che dal
        # 28 agosto ha un produttore vero invece di un `False` scritto a mano.
        self.frase_in_corso = frase

    def stop(self) -> None:
        """`_spegni_gradi()` la ferma come fermerebbe quella vera."""


@pytest.fixture
async def motore_a_news_accese(short_paths):
    """Un `Engine` con `news.enabled = true` e la voce spenta.

    La voce resta spenta apposta: il lettore deve essere collegato **comunque**,
    perche' arriva per funzione e non per valore. Se il cablaggio dipendesse
    dall'ordine dei gradi, questo e' il caso in cui si vedrebbe.
    """
    e = Engine(short_paths)
    e._store.current.news.enabled = True
    e._store.current.voice.enabled = False
    await e._gradi()
    try:
        yield e
    finally:
        await e._spegni_gradi()


# ─────────────────────────────────────────────────────────────────────────────
# Giunzione 1 — la redazione dei segreti e' INSTALLATA, e prima di tutto
# ─────────────────────────────────────────────────────────────────────────────

    @property
    def frase_in_corso(self) -> bool:
        return False


class TestIlLogVieneCONFIGURATO:
    """`core/log.py` esisteva e nessuno lo chiamava.

    E' la forma esatta del difetto che questo progetto continua a trovare: il
    processore che maschera le chiavi era scritto in `core/settings.py` da
    fasi, ma `structlog.configure()` non veniva chiamato **da nessuna parte**
    in `core/`. La catena predefinita non filtra niente, quindi l'invariante
    «le chiavi API MAI nei log» era una frase in un documento.
    """

    async def test_main_CHIAMA_la_configurazione(self, main_senza_engine) -> None:
        assert await main() == 0
        assert "log" in _EngineFinto.ordine, (
            "`main()` non configura i log: la catena resta quella predefinita "
            "di structlog, che non maschera nessuna chiave"
        )

    async def test_i_log_si_configurano_PRIMA_di_costruire_Engine(
            self, main_senza_engine) -> None:
        """L'ordine non e' estetica.

        `Engine.__init__` costruisce `SettingsStore`, che chiama
        `load_settings()`, che scrive `settings_caricate` con l'elenco delle
        chiavi presenti. Configurare dopo vuol dire che la prima riga
        dell'avvio — proprio quella che parla di chiavi — esce senza redazione.
        """
        await main()
        assert _EngineFinto.ordine == ["log", "engine"], (
            f"ordine osservato: {_EngineFinto.ordine} — la configurazione dei "
            "log deve precedere la costruzione del motore"
        )

    async def test_dopo_main_una_CHIAVE_non_esce_in_chiaro(self, main_senza_engine) -> None:
        """La prova che conta: non «e' stata chiamata una funzione», ma «un
        segreto passato a un logger non compare nell'uscita».

        Qui `configura_log` e' quella VERA — nessuna sostituzione — e il
        segreto e' finto e registrato a mano: nessun `secrets.toml` viene letto.
        """
        buffer = main_senza_engine
        await main()
        SECRETS.register(CHIAVE_FINTA)

        structlog.get_logger("prova").info("chiave_di_prova", token=CHIAVE_FINTA)

        uscita = buffer.getvalue()
        assert CHIAVE_FINTA not in uscita, (
            "la chiave e' uscita IN CHIARO: la catena installata da `main()` "
            f"non contiene la redazione. Uscita: {uscita!r}"
        )
        assert SecretRegistry.MASK in uscita, (
            f"nessuna maschera nell'uscita, e nemmeno la chiave: il log non e' "
            f"arrivato nel buffer. Uscita: {uscita!r}"
        )

    async def test_la_redazione_scende_nei_DIZIONARI(self, main_senza_engine) -> None:
        """I log di questo progetto passano strutture, non stringhe: uno
        snapshot della mesh, un messaggio WebSocket, la risposta di un
        provider. `redact_secrets` — il processore che c'era gia' — guarda solo
        il primo livello, quindi installare *quello* non basterebbe."""
        buffer = main_senza_engine
        await main()
        SECRETS.register(CHIAVE_FINTA)

        structlog.get_logger("prova").info(
            "risposta", payload={"auth": {"token": CHIAVE_FINTA}})

        assert CHIAVE_FINTA not in buffer.getvalue(), (
            "la chiave annidata e' uscita in chiaro: e' stata installata una "
            "catena che guarda solo il primo livello dell'evento"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Giunzione 2 — il gate news sa se JARVIS sta parlando
# ─────────────────────────────────────────────────────────────────────────────


class TestIlGateSaSeLaVoceParla:
    """§15 regola 2: «mai mentre Lei parla».

    `Contesto.sta_parlando` e' un tri-stato, e `None` vale come divieto. Il
    campo non aveva un produttore vero: la radice leggeva `_sta_parlando`,
    campo PRIVATO di `VoicePipeline`, una volta per giro. Adesso il produttore
    e' uno solo ed e' una funzione, letta a ogni giro.
    """

    async def test_il_motore_news_HA_il_lettore(self, motore_a_news_accese) -> None:
        """Perche' si vede da fuori: senza questa riga «non e' passata nessuna
        news» e «nessuno ha collegato lo stato della voce, quindi non ne
        passera' mai nessuna» sono lo stesso snapshot."""
        from core.news.conoscibilita import NON_PRODOTTO

        conosc = motore_a_news_accese._news.stato()["conoscibilita"]
        assert conosc["sta_parlando"] != NON_PRODOTTO, (
            "`MotoreNews` non ha ricevuto il lettore: `sta_parlando` restera' "
            "ignoto a ogni giro, e ignoto vale come divieto — nessuna card "
            "passera' MAI, senza un errore da leggere"
        )

    async def test_il_lettore_riporta_la_voce_VIVA(self, motore_a_news_accese) -> None:
        """La catena intera, in due letture: pipeline -> engine -> motore.

        Il lettore si interroga a ogni giro, quindi la voce puo' nascere DOPO
        la composizione delle news — che e' il caso quando i gradi si
        accendono in ordine diverso — e il valore arriva lo stesso.
        """
        e = motore_a_news_accese
        e._voce = _VoceFinta(True)
        assert e._news._contesto_adesso().sta_parlando is True, (
            "la voce parla e il gate non lo sa: la card gli finirebbe sopra"
        )
        e._voce.sta_parlando = False
        assert e._news._contesto_adesso().sta_parlando is False, (
            "lo stato e' fissato al primo valore letto: il lettore e' stato "
            "chiamato una volta sola invece che a ogni giro"
        )

    async def test_a_voce_spenta_il_lettore_dice_NON_LO_SO(
            self, motore_a_news_accese) -> None:
        """`None` non e' `False`. A voce non composta nessuno puo' saperlo, e
        quello e' esattamente il caso in cui non si interrompe."""
        e = motore_a_news_accese
        assert e._voce is None
        assert e._voce_sta_parlando() is None
        assert e._news._contesto_adesso().sta_parlando is None
        assert Contesto(sta_parlando=None).motivo_del_no() == "non so se sta parlando"

    async def test_il_campo_ha_UN_SOLO_produttore(self, motore_a_news_accese) -> None:
        """La radice non dichiara piu' `sta_parlando` nel `Contesto`.

        Con due produttori, uno dei due vince per ordine di riga e l'altro
        resta li' a far credere di contare qualcosa. Qui il `Contesto` della
        radice porta solo cio' che la radice sa davvero.
        """
        e = motore_a_news_accese
        from core.news.conoscibilita import NON_COMPOSTO, NON_PRODOTTO

        e._voce = _VoceFinta(True)
        lettura = e._contesto_news()
        assert lettura.contesto().sta_parlando is None, (
            "la radice dichiara ancora `sta_parlando`: e' il secondo "
            "produttore, e legge un campo privato di un altro modulo"
        )
        assert lettura.conoscibilita()["sta_parlando"] == NON_PRODOTTO, (
            "il campo che la radice non dichiara dev'essere `non_prodotto` e "
            "non un ignoto muto: e' l'unico modo di vedere che manca un pezzo"
        )
        assert lettura.contesto().frase_in_corso is False
        assert lettura.conoscibilita()["pannello_a_schermo_intero"] == NON_COMPOSTO, (
            "un produttore c'e' — `LayoutStore.a_schermo_intero` — e a "
            "scrivania mai vista dice «non lo so»: e' configurazione, non un "
            "guasto, e le due non devono confondersi"
        )

    async def test_una_voce_che_SOLLEVA_non_ferma_il_motore(
            self, motore_a_news_accese) -> None:
        """Il lettore gira dentro il giro dei feed. Una pipeline in uno stato
        che non risponde deve togliere il permesso di parlare, non fermare le
        news."""
        class _VoceRotta:
            @property
            def sta_parlando(self):
                raise RuntimeError("pipeline in uno stato illegale")

            @property
            def frase_in_corso(self):
                raise RuntimeError("pipeline in uno stato illegale")

            def stop(self) -> None:
                """Rotta per il gate, non per l'arresto."""

        e = motore_a_news_accese
        e._voce = _VoceRotta()
        assert e._news._contesto_adesso().sta_parlando is None
