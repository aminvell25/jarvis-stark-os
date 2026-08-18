"""News proattive — SPEC §15, criterio di §22. Fase 8."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import pytest

from core.llm.untrusted import ContenutoNonFidato, Untrusted
from core.news.collectors.base import Item, rilevanza_per_parole
from core.news.collectors.guardian import GuardianCollector
from core.news.collectors.rss import DocumentoSospetto, RssCollector, analizza
from core.news.collectors.youtube import YouTubeCollector
from core.news.feeds import Watcher
from core.news.gate import FINESTRA_S, MAX_PER_ORA, Contesto, Gate
from core.news.topics import estrai_locale, EstrattoreLLM
from tests.news_corpus import CORPUS, OSTILI, RSS_VERO


def item(titolo: str, url: str = "https://esempio.invalido/a", ril: float = 1.0) -> Item:
    return Item(fonte="prova", url=url,
                testo=Untrusted.da("news:prova", titolo), rilevanza=ril)


LIBERO = Contesto(sta_parlando=False, pannello_a_schermo_intero=False, frase_in_corso=False)


class TestParser:
    @pytest.mark.parametrize("nome,xml,quanti,solleva", CORPUS, ids=[c[0] for c in CORPUS])
    def test_il_corpus(self, nome: str, xml: str, quanti: int, solleva: bool) -> None:
        if solleva:
            with pytest.raises((DocumentoSospetto, ET.ParseError)):
                analizza(xml, "prova")
            return
        assert len(analizza(xml, "prova")) == quanti

    def test_ogni_testo_esce_come_NON_FIDATO(self) -> None:
        """§15: «un titolo e' testo controllato da terzi. Stesse regole di §12»."""
        for i in analizza(RSS_VERO, "prova"):
            assert isinstance(i.testo, Untrusted)
            assert i.testo.origine == "news:prova"

    def test_l_id_sta_sull_url_non_sul_titolo(self) -> None:
        """Le testate riscrivono i titoli nel corso della giornata: un id che
        cambia con essi farebbe ricomparire la stessa storia ogni ora."""
        a = item("Titolo del mattino", "https://esempio.invalido/x")
        b = item("Titolo rivisto nel pomeriggio", "https://esempio.invalido/x")
        assert a.id == b.id

    def test_una_data_incomprensibile_vale_zero_non_adesso(self) -> None:
        """Una data inventata farebbe sembrare freschissima una notizia di tre
        giorni fa: §11.9, dati veri o niente."""
        xml = RSS_VERO.replace("Tue, 18 Aug 2026 12:36:11 GMT", "boh")
        assert analizza(xml, "prova")[0].pubblicato == 0.0


class TestRilevanza:
    def test_non_si_diluisce_col_numero_di_argomenti(self) -> None:
        """Una notizia che tocca UNA cosa che mi interessa e' rilevante, non e'
        un ottavo di rilevante. La prima versione divideva per il numero di
        argomenti e con otto interessi non passava piu' niente."""
        i = item("Alluvione in valle")
        pochi = rilevanza_per_parole(i, ["alluvione"])
        molti = rilevanza_per_parole(i, ["alluvione", "borsa", "cinema", "calcio",
                                         "musica", "scuola", "traffico", "meteo"])
        assert pochi == molti > 0


class TestBudget:
    """Il criterio di §22: «budget 3/ora rispettato»."""

    def test_su_venti_notizie_ne_passano_TRE(self) -> None:
        g = Gate()
        t = 1_000_000.0
        passate = [
            g.valuta(item(f"Alluvione numero {n}", f"https://esempio.invalido/{n}"),
                     ["alluvione"], LIBERO, t + n).passa
            for n in range(20)
        ]
        assert sum(passate) == MAX_PER_ORA == 3
        assert g.restanti(t + 20) == 0

    def test_la_finestra_SCORRE(self) -> None:
        """Tre all'ora contate sull'ora solare darebbero tre annunci alle 10:58
        e altri tre alle 11:02: sei in quattro minuti, formalmente dentro il
        budget."""
        g = Gate()
        t = 1_000_000.0
        for n in range(3):
            assert g.valuta(item(f"A{n}", f"https://esempio.invalido/a{n}"),
                            ["a"], LIBERO, t + n).passa
        assert not g.valuta(item("A4", "https://esempio.invalido/a4"),
                            ["a"], LIBERO, t + 60).passa
        # Passata l'ora, il primo slot torna libero.
        assert g.valuta(item("A5", "https://esempio.invalido/a5"),
                        ["a"], LIBERO, t + FINESTRA_S + 1).passa

    def test_il_budget_si_consuma_solo_su_cio_che_ESCE(self) -> None:
        """Contarlo prima vorrebbe dire bruciare le interruzioni con notizie
        che non sono mai uscite."""
        g = Gate()
        for n in range(10):
            g.valuta(item(f"Irrilevante {n}", f"https://esempio.invalido/i{n}", ril=0.0),
                     ["altro"], LIBERO, 1_000_000.0)
        assert g.restanti(1_000_000.0) == MAX_PER_ORA


class TestLeCinqueRegole:
    """§15: «le regole senza cui abbandonera' la funzione in tre giorni»."""

    @pytest.mark.parametrize(
        "contesto,atteso",
        [
            (Contesto(sta_parlando=True, pannello_a_schermo_intero=False, frase_in_corso=False),
             "sta parlando"),
            (Contesto(sta_parlando=False, pannello_a_schermo_intero=True, frase_in_corso=False),
             "pannello a schermo intero"),
            (Contesto(sta_parlando=False, pannello_a_schermo_intero=False, frase_in_corso=True),
             "frase a meta'"),
        ],
    )
    def test_non_interrompe_quando_non_deve(self, contesto: Contesto, atteso: str) -> None:
        d = Gate().valuta(item("Alluvione"), ["alluvione"], contesto)
        assert not d.passa and atteso in d.motivo

    @pytest.mark.parametrize("ignoto", ["sta_parlando", "pannello_a_schermo_intero",
                                        "frase_in_corso"])
    def test_cio_che_NON_SO_vale_come_un_NO(self, ignoto: str) -> None:
        """La tentazione sarebbe trattare «non lo so» come via libera, perche'
        altrimenti in questa configurazione non passa mai niente. E' la
        tentazione sbagliata: in un sistema che parla da solo, la modalita'
        silenziosa e' quella sicura."""
        campi = {"sta_parlando": False, "pannello_a_schermo_intero": False,
                 "frase_in_corso": False, ignoto: None}
        d = Gate().valuta(item("Alluvione"), ["alluvione"], Contesto(**campi))
        assert not d.passa and "non so" in d.motivo

    def test_una_notizia_non_si_ripropone(self) -> None:
        g = Gate()
        i = item("Alluvione", "https://esempio.invalido/uguale")
        assert g.valuta(i, ["alluvione"], LIBERO).passa
        d = g.valuta(i, ["alluvione"], LIBERO)
        assert not d.passa and "gia' proposto" in d.motivo

    async def test_gli_argomenti_scadono_dopo_trenta_minuti(self) -> None:
        """§15, quarta regola.

        Si misura sull'orologio INIETTATO e non su `parole()`, che legge quello
        vero: argomenti timbrati al secondo 1000 dell'epoca sono scaduti da
        cinquant'anni, e il test misurerebbe la data di oggi.
        """
        e = EstrattoreLLM()
        estratti = await e.aggiorna("alluvione alluvione maltempo maltempo", adesso=1_000.0)
        assert [a.parola for a in estratti] == ["alluvione", "maltempo"]
        for a in estratti:
            assert not a.scaduto(1_000.0 + 29 * 60), "scaduto troppo presto"
            assert a.scaduto(1_000.0 + 31 * 60), "non e' mai scaduto"

    def test_non_parlarmene_piu_e_PERSISTENTE(self, tmp_path) -> None:
        """§15, quinta regola. Un file markdown che sopravvive al riavvio e che
        si corregge con un editor — la proprieta' che §5.5 chiede alla memoria."""
        from core.memory.store import MemoryStore

        store = MemoryStore(tmp_path)
        g = Gate(store)
        g.silenzia("calcio")
        assert not g.valuta(item("Il calcio in tv"), ["calcio"], LIBERO).passa

        # Un gate NUOVO, come dopo un riavvio, deve saperlo ancora.
        g2 = Gate(MemoryStore(tmp_path))
        assert "calcio" in g2.silenziati
        d = g2.valuta(item("Il calcio in tv"), ["calcio"], LIBERO)
        assert not d.passa and "chiuso" in d.motivo


class TestSorgentiSenzaChiave:
    """§15: due delle tre sorgenti vogliono una chiave, e l'assenza si ANNUNCIA."""

    @pytest.mark.parametrize("classe", [GuardianCollector, YouTubeCollector])
    async def test_senza_chiave_lo_dice(self, classe) -> None:
        c = classe(lambda: "")
        ok, motivo = c.disponibile()
        assert not ok and motivo
        esito = await c.poll(["clima"])
        assert esito.errore and not esito.item

    async def test_una_fonte_rotta_non_e_una_giornata_tranquilla(self) -> None:
        """Un collector che restituisse zero item quando la sorgente lo
        respinge direbbe «non ci sono notizie» invece di «questa fonte non
        risponde». La prima e' normale, la seconda va riparata."""
        c = RssCollector({"Rotta": "https://non.esiste.invalido/feed.xml"})
        esito = await c.poll(["clima"])
        assert not esito.item
        assert esito.errore and esito.fonti_in_errore


class TestWatcher:
    async def test_annuncia_le_fonti_spente(self) -> None:
        """§16: «nessuna soglia agisce senza annunciarlo». Una funzione che
        tace puo' tacere per due motivi opposti."""
        msg = []
        w = Watcher([GuardianCollector(lambda: "")], Gate(), lambda m: _raccogli(msg, m))
        g = await w.giro(["clima"], LIBERO)
        assert g.passati == 0
        advisory = [m for m in msg if m["topic"] == "agent.advisory"]
        assert advisory and "guardian" in str(advisory[0]["dettaglio"])


async def _raccogli(dove: list, msg: dict) -> None:
    dove.append(msg)


class TestEstrattore:
    def test_RIFIUTA_il_contenuto_non_fidato(self) -> None:
        """R60: se l'estrattore leggesse le news, un articolo ostile potrebbe
        iniettare i propri argomenti e da li' in poi decidere quali altre
        notizie La raggiungono. E' l'avvelenamento del ciclo di retroazione."""
        for i in analizza(OSTILI[0][1], "ostile"):
            with pytest.raises(ContenutoNonFidato):
                estrai_locale(i.testo)

    def test_sulla_conversazione_invece_funziona(self) -> None:
        a = [x.parola for x in estrai_locale(
            "Parliamo di alluvione e maltempo. L'alluvione mi preoccupa, "
            "il maltempo pure."
        )]
        assert "alluvione" in a and "maltempo" in a

    def test_scarta_le_parole_che_non_distinguono_niente(self) -> None:
        """Un argomento «cosa» farebbe passare qualunque notizia."""
        a = [x.parola for x in estrai_locale(
            "Cosa ne pensi di quello che e' successo? Molto interessante, "
            "sempre quello."
        )]
        for vuota in ("cosa", "quello", "sempre", "molto", "interessante"):
            assert vuota not in a
