"""Distinguere «non è passato niente» da «non poteva passare» — §15.

## L'ambiguità in cui §15 si è nascosta per sei turni

Il gate legge tre tri-stati e su `None` tace. È fail-closed, ed è giusto. Ma
uno snapshot con zero card ha due letture, e il sistema non sapeva dire quale:

    zero card    perché non c'era niente di rilevante
    zero card    perché un campo era ignoto, e lo resterà finché qualcuno non
                 collega un pezzo che manca

`MotoreNews.stato()` aveva già la cura, applicata a **un campo su tre**:
`voce_collegata`. Una riga gemella per il secondo e nessuna per il terzo
sarebbe lo stesso difetto in scala ridotta. Qui si misura il meccanismo
generale: `conoscibilita()` risponde per **ogni** campo che `Contesto`
dichiara, e distingue le due specie di ignoto.

    configurazione   `non_prodotto`, `non_composto` — un interruttore da
                     accendere, permanente finché non lo si accende
    guasto           `ha_sollevato`, `risposta_storta` — il produttore c'è e
                     ha fallito adesso: si insegue

⚠️ Ciò che rende questi test capaci di **bocciare**: ognuno contiene il caso
SCOLLEGATO accanto a quello collegato. Un test che dicesse solo «lo stato dice
`noto`» mentre il finto è sempre collegato è vero per assenza del fenomeno —
l'undicesima volta che questa famiglia si presenta in questo repository.
"""

from __future__ import annotations

import pytest

from core.layout import GeometriaPannello, Layout
from core.news.conoscibilita import (
    CAMPI, CAUSE, CONFIGURAZIONI, GUASTI, HA_SOLLEVATO, MAI_LETTO,
    NON_COMPOSTO, NON_PRODOTTO, NOTO, RISPOSTA_STORTA, Lettura, Sguardo, guarda,
)
from core.news.gate import Contesto, Gate
from core.news.motore import MotoreNews

from tests.conftest import lettura_nota

from tests.test_il_gate_sa_se_parli import (
    _chiedi_clima, _CollettoreFinto, _Impostazioni, _uscite,
)


class _Watcher:
    """Un watcher che non guarda niente: qui si misura la lettura, non i feed."""

    def __init__(self) -> None:
        self.visti: list[Contesto] = []

    async def giro(self, parole, contesto):
        self.visti.append(contesto)
        return type("G", (), {"letti": 0, "passati": 0, "scartati": {},
                              "errori": []})()


async def _motore_con(contesto=None, sta_parlando=None):
    w = _Watcher()
    m = MotoreNews(w, _Impostazioni(), contesto=contesto,
                   sta_parlando=sta_parlando, chiedi=_chiedi_clima)
    assert await m.ascolta("mi dici come va il clima") == ["clima"]
    return m, w


# ─────────────────────────────────────────────────────────────────────────────
# Il vocabolario: un valore e una causa che si contraddicono non si costruiscono
# ─────────────────────────────────────────────────────────────────────────────


class TestUnoSguardoNonPuoContraddirsi:
    """La struttura lo impedisce, invece di raccomandarlo a chi scrive."""

    def test_noto_senza_valore_NON_si_costruisce(self) -> None:
        with pytest.raises(ValueError, match="contraddice"):
            Sguardo(None, NOTO)

    @pytest.mark.parametrize("causa", sorted(set(CAUSE) - {NOTO}))
    def test_un_valore_con_una_causa_di_ignoto_NON_si_costruisce(
            self, causa: str) -> None:
        with pytest.raises(ValueError, match="contraddice"):
            Sguardo(True, causa)

    def test_una_causa_inventata_e_un_REFUSO_non_un_caso_nuovo(self) -> None:
        """Allowlist, mai denylist: una causa che non è dichiarata non è un
        caso da accogliere, è un errore di chi scrive."""
        with pytest.raises(ValueError, match="causa sconosciuta"):
            Sguardo(None, "boh")

    def test_le_due_specie_non_si_sovrappongono(self) -> None:
        assert not (CONFIGURAZIONI & GUASTI)
        assert (CONFIGURAZIONI | GUASTI | {NOTO, MAI_LETTO}) == set(CAUSE)


class TestGuardaDistingueIQuattroEsiti:
    def test_un_bool_e_NOTO(self) -> None:
        assert guarda(lambda: True) == Sguardo(True, NOTO)
        assert guarda(lambda: False) == Sguardo(False, NOTO)

    def test_None_e_CONFIGURAZIONE(self) -> None:
        """Il produttore c'è e dice «non lo so»: voce spenta, nessuna
        scrivania ha mai riferito. Si risolve accendendo qualcosa."""
        assert guarda(lambda: None).causa == NON_COMPOSTO

    def test_sollevare_e_un_GUASTO_e_non_esce(self) -> None:
        def rotto():
            raise RuntimeError("la pipeline non risponde")

        assert guarda(rotto).causa == HA_SOLLEVATO

    @pytest.mark.parametrize("valore", [0, "", [], 0.0, 1])
    def test_un_valore_che_non_e_un_bool_e_un_GUASTO(self, valore) -> None:
        """⚠️ `isinstance` e non `bool()`: un campo non inizializzato che torna
        `0` diventerebbe `False`, cioè «interrompi pure»."""
        s = guarda(lambda: valore)
        assert s.valore is None and s.causa == RISPOSTA_STORTA


class TestIlQuartoCampoEntraDaSOLO:
    """⚠️ La ragione per cui questo è un meccanismo e non tre righe scritte a
    mano: fra un mese qualcuno aggiunge un campo al `Contesto`, guarda lo
    stato, non lo vede, e ricomincia da capo."""

    def test_i_campi_sono_DERIVATI_dal_Contesto(self) -> None:
        from dataclasses import fields

        assert CAMPI == tuple(f.name for f in fields(Contesto))

    def test_un_campo_senza_sguardo_e_NON_PRODOTTO(self) -> None:
        c = lettura_nota(sta_parlando=False).conoscibilita()
        assert c["sta_parlando"] == NOTO
        assert set(c) == set(CAMPI)
        assert c["frase_in_corso"] == NON_PRODOTTO

    def test_uno_sguardo_su_un_campo_che_non_esiste_e_un_REFUSO(self) -> None:
        with pytest.raises(ValueError, match="non sono campi di Contesto"):
            Lettura({"sta_zitto": Sguardo(True, NOTO)})


class TestIlGateRiceveESATTAMENTEQuelloDiPrima:
    """La conoscibilità è per chi guarda. Una regola non deve poterla leggere,
    o la distinzione fra «non lo so» e «perché non lo so» finirebbe per
    allentare il gate — ed è il rischio che questo turno rifiuta di correre."""

    def test_il_Contesto_ha_i_tre_campi_e_basta(self) -> None:
        c = lettura_nota(sta_parlando=False, frase_in_corso=False,
                         pannello_a_schermo_intero=False).contesto()
        assert isinstance(c, Contesto)
        assert set(vars(c)) == set(CAMPI)

    def test_una_causa_di_GUASTO_vale_come_ignoto_e_quindi_come_divieto(self) -> None:
        c = Lettura({"sta_parlando": Sguardo(None, HA_SOLLEVATO),
                     "frase_in_corso": Sguardo(False, NOTO),
                     "pannello_a_schermo_intero": Sguardo(False, NOTO)}).contesto()
        assert c.motivo_del_no() == "non so se sta parlando"


# ─────────────────────────────────────────────────────────────────────────────
# I tre casi obbligatori, ciascuno col suo scollegato accanto
# ─────────────────────────────────────────────────────────────────────────────


class TestLoStatoDiceQualeDeiTreManca:
    async def test_nessuna_scrivania_ha_mai_riferito(self, short_paths) -> None:
        """Caso 1. E lo dice **in modo diverso** da «ha riferito e nessun
        pannello è massimizzato»: il primo è un pezzo che manca, il secondo è
        una risposta."""
        from core.engine import Engine

        class _Voce:
            frase_in_corso = False
            sta_parlando = False

        e = Engine(short_paths)
        e._voce = _Voce()

        m, _ = await _motore_con(contesto=e._contesto_news,
                                 sta_parlando=e._voce_sta_parlando)
        await m.un_giro()
        muta = m.conoscibilita()
        assert muta["pannello_a_schermo_intero"] == NON_COMPOSTO

        e._layout._ultimo = Layout(pannelli=[GeometriaPannello(
            id="meteo", x=0, y=0, larghezza=10, altezza=10, massimizzato=False)])
        await m.un_giro()
        viva = m.conoscibilita()
        assert viva["pannello_a_schermo_intero"] == NOTO
        assert muta != viva, (
            "una scrivania che non ha mai riferito e una che risponde «nessun "
            "pannello è massimizzato» danno lo stesso snapshot"
        )

    async def test_la_voce_e_spenta(self, short_paths) -> None:
        """Caso 2, e **distinto dal caso 1**: due campi ignoti per due ragioni
        che stanno in due posti diversi dello stesso snapshot."""
        from core.engine import Engine

        e = Engine(short_paths)
        assert e._voce is None
        e._layout._ultimo = Layout(pannelli=[GeometriaPannello(
            id="meteo", x=0, y=0, larghezza=10, altezza=10, massimizzato=False)])

        m, _ = await _motore_con(contesto=e._contesto_news,
                                 sta_parlando=e._voce_sta_parlando)
        await m.un_giro()
        c = m.conoscibilita()
        assert c["frase_in_corso"] == NON_COMPOSTO
        assert c["sta_parlando"] == NON_COMPOSTO
        assert c["pannello_a_schermo_intero"] == NOTO, (
            "la scrivania ha riferito: se anche questo è ignoto, lo snapshot "
            "non distingue una voce spenta da una scrivania mai vista"
        )

    async def test_un_produttore_che_solleva_e_un_GUASTO_e_il_giro_CONTINUA(
            self, short_paths) -> None:
        """Caso 3, e le due metà contano entrambe: se l'eccezione fermasse il
        giro, il silenzio sarebbe lo stesso ma per un guasto diverso, e i feed
        smetterebbero di essere guardati senza che si veda."""
        from core.engine import Engine

        class _Rotta:
            @property
            def frase_in_corso(self):
                raise RuntimeError("pipeline in uno stato illegale")

            @property
            def sta_parlando(self):
                return False

        e = Engine(short_paths)
        e._voce = _Rotta()
        e._layout._ultimo = Layout(pannelli=[GeometriaPannello(
            id="meteo", x=0, y=0, larghezza=10, altezza=10, massimizzato=False)])

        m, w = await _motore_con(contesto=e._contesto_news,
                                 sta_parlando=e._voce_sta_parlando)
        assert await m.un_giro() is True, "un produttore rotto ha fermato il giro"
        assert len(w.visti) == 1
        c = m.conoscibilita()
        assert c["frase_in_corso"] == HA_SOLLEVATO
        assert c["frase_in_corso"] in GUASTI
        assert c["sta_parlando"] == NOTO and c["pannello_a_schermo_intero"] == NOTO, (
            "un campo che cade ha portato via gli altri: è la proprietà "
            "chiusa in 7a4b39f, e vale anche per le cause"
        )


class TestPrimaDelPrimoGiro:
    """⚠️ `conoscibilita()` **non legge i produttori**: una seconda lettura
    darebbe un valore diverso da quello che il giro ha usato, e sarebbe il
    secondo produttore che questa giunzione ha appena finito di togliere."""

    async def test_a_giri_zero_e_MAI_LETTO_e_non_un_valore_riletto(self) -> None:
        letture: list[int] = []

        def contesto():
            letture.append(1)
            return lettura_nota(frase_in_corso=False)

        m, _ = await _motore_con(contesto=contesto, sta_parlando=lambda: False)
        assert m.conoscibilita()["frase_in_corso"] == MAI_LETTO
        assert letture == [], "conoscibilita() ha letto un produttore"

    async def test_senza_lettore_parla_adesso_dice_NON_PRODOTTO(self) -> None:
        """⚠️ Questa guardia è irraggiungibile da `_contesto_adesso`, che senza
        lettore non tocca il campo — e la bocciatura l'ha detto: perturbandola,
        nessun test cadeva. Non è morta, è una **precondizione** di un metodo
        privato che si può chiamare da solo, e allora la si prova da sola
        invece di lasciarla senza nessuno che la guardi.

        Toglierla non è un'opzione: `_parla_adesso` chiamerebbe `None()`.
        """
        m, _ = await _motore_con(sta_parlando=None)
        s = m._parla_adesso()
        assert s.valore is None and s.causa == NON_PRODOTTO, (
            "«nessuno l'ha collegato» e «il lettore dice non lo so» sono due "
            "lavori diversi: collegare un pezzo, o accendere un interruttore"
        )

    async def test_ma_il_CABLAGGIO_si_sa_senza_leggere(self) -> None:
        """È ciò che `voce_collegata` diceva, generalizzato: se nessuno produce
        un campo, il gate resterà chiuso per sempre e va detto subito, non al
        primo giro — che con la lista di argomenti vuota potrebbe non arrivare
        mai."""
        muto, _ = await _motore_con(sta_parlando=None)
        collegato, _ = await _motore_con(sta_parlando=lambda: False)
        assert muto.conoscibilita()["sta_parlando"] == NON_PRODOTTO
        assert collegato.conoscibilita()["sta_parlando"] == MAI_LETTO


# ─────────────────────────────────────────────────────────────────────────────
# §15: la dipendenza dichiarata
# ─────────────────────────────────────────────────────────────────────────────


class TestLeNotizieRichiedonoLaVoceACCESA:
    """La conseguenza dichiarata del disegno, non scoperta.

    A `voice.enabled = false` la pipeline non si compone, due dei tre campi
    diventano ignoti e l'ignoto vale come divieto: **nessuna card può passare**.
    È fail-closed corretto, e fino a oggi non era scritto da nessuna parte.

    Se un giorno una card passasse a voce spenta, quella è una decisione nuova
    — e deve far cadere qualcosa, non passare inosservata.
    """

    async def test_a_voce_spenta_NESSUNA_card_esce(self, short_paths) -> None:
        from core.engine import Engine
        from core.news.feeds import Watcher

        cards: list[dict] = []

        async def pubblica(msg: dict) -> None:
            cards.append(msg)

        e = Engine(short_paths)
        assert e._voce is None
        e._layout._ultimo = Layout(pannelli=[GeometriaPannello(
            id="meteo", x=0, y=0, larghezza=10, altezza=10, massimizzato=False)])

        w = Watcher([_CollettoreFinto()], Gate(None), pubblica)
        m = MotoreNews(w, _Impostazioni(), contesto=e._contesto_news,
                       sta_parlando=e._voce_sta_parlando, chiedi=_chiedi_clima)
        assert await m.ascolta("mi dici come va il clima") == ["clima"]
        assert await m.un_giro() is True
        assert _uscite(cards) == [], (
            "una card è uscita a voce spenta: §15 dice che le notizie "
            "richiedono la voce accesa, e questa è una decisione nuova"
        )
        assert m.conoscibilita()["frase_in_corso"] in CONFIGURAZIONI, (
            "e la ragione dev'essere leggibile: un pezzo da collegare, non un "
            "silenzio"
        )

    def test_la_dipendenza_e_SCRITTA_in_SPEC(self) -> None:
        """Una proprietà che regge per costruzione e non è dichiarata è una
        proprietà che qualcuno toglierà senza sapere di toglierla."""
        from pathlib import Path

        spec = (Path(__file__).resolve().parent.parent / "docs" / "SPEC.md"
                ).read_text(encoding="utf-8")
        i = spec.index("# 15. News proattive")
        sezione = spec[i:spec.index("\n# 16.", i)]
        assert "le notizie richiedono la voce accesa" in sezione.lower(), (
            "§15 non dichiara la dipendenza: resterebbe da scoprire leggendo "
            "tre moduli e un tri-stato"
        )
