"""La cadenza dedotta, e chi aziona il `Watcher` — §15.

## Il difetto

`Watcher.giro()` non aveva **un solo chiamante nel core**. Con
`news.enabled = true` il `Watcher` si costruiva a ogni avvio, lo snapshot
diceva `giri_fatti: 0`, e nessun giro sui feed è mai avvenuto. `EstrattoreLLM`
era nello stesso stato, e il suo commento lo diceva: «il giorno in cui la
pipeline sarà composta basterà passargliela».

## La cadenza non è in §15, e non si inventa

§15 dichiara **una** frequenza: 3 interruzioni all'ora, che è il ritmo con cui
JARVIS può *parlare*, non quello con cui può *guardare*. Il periodo dei giri si
deriva, e questi test fissano la derivazione — non il numero.

Ciò che si verifica è che il periodo **cambi con l'impostazione**: una costante
travestita da deduzione passerebbe un test sul valore e fallirebbe questo.
"""

from __future__ import annotations

import asyncio

import pytest

from core.news.gate import Contesto
from core.news.motore import PERIODO_MINIMO_S, MotoreNews, periodo_dei_giri


class _Impostazioni:
    def __init__(self, tetto: int = 3, ttl: int = 30) -> None:
        self.max_interruptions_per_hour = tetto
        self.topic_ttl_minutes = ttl


class _WatcherFinto:
    def __init__(self, passati: int = 0) -> None:
        self.chiamate: list[tuple[list[str], Contesto]] = []
        self._passati = passati

    async def giro(self, argomenti, contesto, adesso=None):
        self.chiamate.append((list(argomenti), contesto))

        class _G:
            letti = 3
            passati = self._passati
            scartati: dict = {}
        return _G()


class TestLaCadenzaSiDEDUCE:
    def test_col_tetto_di_TRE_fa_dieci_minuti(self) -> None:
        """3/ora → finestra di 1200 s → dimezzata → 600 s.

        ⚠️ Si chiamava `test_col_tetto_di_15_...` e il tetto è 3. Il 15 era
        `§15` — la sezione — e l'ho perso io con un `sed` che toglieva il `§`,
        che Python non accetta in un identificatore. Un numero di troppo dentro
        il nome di un test che parla di numeri dedotti: sembrava il tetto dei
        15 spawn T2/ora del Governor, che con la cadenza non c'entra nulla.

        Il numero non è scelto: è la finestra del budget divisa per due, così
        che ogni finestra abbia **due** occasioni invece di una. Con una sola,
        un candidato scartato dal gate perde la finestra fino al giro dopo.
        """
        assert periodo_dei_giri(3, 30) == 600.0

    @pytest.mark.parametrize("tetto,atteso", [(3, 600.0), (4, 450.0), (6, 300.0),
                                              (12, 150.0)])
    def test_CAMBIA_col_tetto(self, tetto: int, atteso: float) -> None:
        """La proprietà che conta. Una costante travestita da deduzione
        passerebbe il test qui sopra e fallirebbe questo."""
        assert periodo_dei_giri(tetto, 30) == atteso

    def test_il_TTL_degli_argomenti_e_il_tetto_superiore(self) -> None:
        """Un giro più lento della vita di un argomento vorrebbe dire che un
        argomento può nascere e scadere senza essere mai stato guardato — la
        funzione non farebbe niente, in silenzio. Con 1/ora il budget direbbe
        1800 s, e il TTL lo riporta a 900."""
        assert periodo_dei_giri(1, 30) == 900.0
        assert periodo_dei_giri(2, 30) == 900.0
        # E segue il TTL, non un numero fisso.
        assert periodo_dei_giri(1, 10) == 300.0

    def test_il_PAVIMENTO_non_viene_dall_aritmetica(self) -> None:
        """Con 60/ora la formula darebbe 30 s su server che non sono nostri.
        Sotto il minuto non si scende, ed è educazione, non calcolo."""
        assert periodo_dei_giri(60, 30) == PERIODO_MINIMO_S
        assert periodo_dei_giri(30, 30) == PERIODO_MINIMO_S

    @pytest.mark.parametrize("tetto,ttl", [(0, 30), (-1, 30), (3, 0)])
    def test_i_numeri_impossibili_si_RIFIUTANO(self, tetto: int, ttl: int) -> None:
        """Un tetto a zero vuol dire che JARVIS non può mai parlare: guardare i
        feed sarebbe traffico per niente, ed è meglio dirlo che dividere per
        zero."""
        with pytest.raises(ValueError):
            periodo_dei_giri(tetto, ttl)


class TestSenzaArgomentiNON_SI_GUARDA:
    async def test_nessun_giro_a_lista_vuota(self) -> None:
        """`giro()` calcola la rilevanza **contro gli argomenti**: senza,
        niente può essere rilevante e niente può passare. Un giro sarebbe
        traffico su un server di terzi in cambio di nulla."""
        w = _WatcherFinto()
        m = MotoreNews(w, _Impostazioni())
        assert await m.un_giro() is False
        assert w.chiamate == []
        assert m.giri == 0

    async def test_dopo_una_frase_il_giro_si_fa(self) -> None:
        w = _WatcherFinto()
        m = MotoreNews(w, _Impostazioni())
        parole = await m.ascolta("mi preoccupa il clima e il governo")
        assert parole, "nessun argomento estratto dalla frase"
        assert await m.un_giro() is True
        assert w.chiamate and w.chiamate[0][0] == parole
        assert m.giri == 1


class TestIlBATCHeIlPERIODO:
    """§15 dice «batch 60s», ma 60 s vorrebbero dire fino a 60 spawn all'ora
    contro il tetto di 15 del Governor: tre estrazioni su quattro rifiutate e
    cadute sul ripiego locale. Il batch e' il periodo dei giri — nessun numero
    nuovo, e la proprieta' si verifica misurando, non leggendo il sorgente."""

    def test_il_batch_dell_estrattore_E_il_periodo(self) -> None:
        m = MotoreNews(_WatcherFinto(), _Impostazioni())
        assert m.argomenti._batch_s == periodo_dei_giri(3, 30) == 600.0

    def test_e_SEGUE_l_impostazione(self) -> None:
        """Una costante travestita passerebbe il test qui sopra."""
        m = MotoreNews(_WatcherFinto(), _Impostazioni(tetto=12))
        assert m.argomenti._batch_s == 150.0

    def test_sta_DENTRO_il_tetto_degli_spawn(self) -> None:
        """La ragione per cui il numero e' quello: 3600/600 = 6 estrazioni
        l'ora contro `MAX_PER_WINDOW = 15`. Col tetto di §15 al massimo — 60
        interruzioni l'ora — il pavimento di 60 s riporterebbe il batch a 60,
        cioe' proprio i 60 spawn/ora che non stanno nella quota: la' l'unico
        esito possibile e' il ripiego, e va saputo."""
        from core.llm.governor import MAX_PER_WINDOW

        m = MotoreNews(_WatcherFinto(), _Impostazioni())
        assert 3600 / m.argomenti._batch_s <= MAX_PER_WINDOW


class TestIlBatchSCARTAinveceDiACCUMULARE:
    """⚠️ **DIFETTO NOTO, dichiarato e non ancora corretto.**

    §15 dice «batch 60s», e «batch» vuol dire raggruppare. `EstrattoreLLM`
    invece **limita la frequenza**: dentro la finestra restituisce gli argomenti
    di prima e **scarta** le battute successive, che non arrivano mai al
    modello.

    A 60 s si perdeva poco. Portando il batch a 600 s — la cadenza dedotta —
    l'ho reso **dieci volte peggiore senza accorgermene**: adesso haiku vede una
    frase ogni dieci minuti e le altre nove minuti e mezzo di conversazione
    spariscono.

    Il test fissa il comportamento di OGGI perche' non si perda di vista. La
    correzione e' un turno suo: accumulare cambia cio' che il modello riceve, e
    quindi rifa' la misura di `HAIKU-RISPOSTE.json`, che e' costata 11,3 USD
    nozionali su un percorso a frase singola.
    """

    async def test_solo_la_PRIMA_battuta_arriva_al_modello(self) -> None:
        """Le battute dentro la finestra sono perse per SEMPRE, non rimandate.

        ⚠️ **La prima stesura di questo test non discriminava.** Chiamava tre
        volte con l'orologio fermo e verificava che una sola battuta arrivasse
        al modello — ma quello lo garantisce il limitatore di frequenza, che
        c'e' in entrambi i casi. Facendo accumulare `aggiorna` per prova, il
        test restava **verde**. Un criterio vero per il motivo sbagliato.

        Adesso l'orologio **supera** la finestra: al giro dopo si guarda che
        cosa arriva. Se arrivasse anche cio' che e' stato detto in mezzo, il
        difetto sarebbe corretto.
        """
        visti: list[str] = []

        async def spia(compito: str) -> str:
            visti.append(compito.split("TESTO:\n", 1)[1])
            return "clima"

        m = MotoreNews(_WatcherFinto(), _Impostazioni(), chiedi=spia)
        await m.argomenti.aggiorna("mi preoccupa il clima", adesso=1_000.0)
        await m.argomenti.aggiorna("e poi c'e' il governo", adesso=1_100.0)
        await m.argomenti.aggiorna("sto leggendo di semiconduttori", adesso=1_200.0)
        # la finestra (600 s) e' scaduta: il modello viene interrogato di nuovo
        await m.argomenti.aggiorna("che tempo fa domani", adesso=1_700.0)

        assert len(visti) == 2, f"spawn attesi 2, fatti {len(visti)}"
        assert "governo" not in visti[1] and "semiconduttori" not in visti[1], (
            "comportamento cambiato: il batch ACCUMULA, il difetto e' corretto — "
            "togli questo test e RIFAI la misura di HAIKU-RISPOSTE.json, che era "
            "stata presa su un percorso a frase singola"
        )
        assert visti[1] == "che tempo fa domani"


    def test_e_la_finestra_scartata_e_lunga_quanto_il_PERIODO(self) -> None:
        """La misura del danno: quanto dura il silenzio in cui si scarta."""
        m = MotoreNews(_WatcherFinto(), _Impostazioni())
        assert m.argomenti._batch_s == 600.0


class TestIlMODELLOeCOLLEGATO:
    """La giunzione. `EstrattoreLLM(chiedi=...)` esisteva dalla Fase 8 e
    nessuno gli passava un modello: girava sempre il ripiego locale."""

    async def test_chi_ascolta_CHIAMA_il_modello(self) -> None:
        chiamate = []

        async def finto(compito: str) -> str:
            chiamate.append(compito)
            return "clima, governo"

        m = MotoreNews(_WatcherFinto(), _Impostazioni(), chiedi=finto)
        parole = await m.ascolta("mi preoccupa il clima e il governo")
        assert chiamate, "il motore non ha mai chiamato il modello"
        assert "TESTO:" in chiamate[0], "e' arrivato il testo nudo, senza il compito"
        assert sorted(parole) == ["clima", "governo"]

    async def test_un_modello_che_cade_RIPIEGA_sul_locale(self) -> None:
        """Invariante 12: il ripiego esiste e non zittisce la catena."""
        async def cade(_: str) -> str:
            raise RuntimeError("quota della finestra esaurita")

        m = MotoreNews(_WatcherFinto(), _Impostazioni(), chiedi=cade)
        assert sorted(await m.ascolta("mi preoccupa il clima e il governo")) == \
            ["clima", "governo"]

    def test_la_radice_di_composizione_PASSA_lo_spawn(self) -> None:
        from pathlib import Path

        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        assert "chiedi=self._argomenti_col_modello" in s, (
            "il motore si costruisce senza modello: girerebbe il ripiego locale "
            "per sempre, che e' la nona giunzione mancante in tre giorni"
        )
        assert "modello=MODELLO_ARGOMENTI" in s, "lo spawn non usa il modello di §15"
        assert 'tool="", max_turns=1' in s, (
            "lo spawn dell'estrattore ha dei tool: non c'e' niente da azionare, "
            "e zero tool e' anche la condizione dell'invariante 5"
        )


class TestIlContestoARRIVA:
    async def test_il_contesto_e_quello_di_ADESSO(self) -> None:
        """Le regole 2 e 3 di §15 dipendono da che cosa sta succedendo: il
        contesto si chiede a ogni giro, non si fissa alla costruzione."""
        stato = {"parla": False}
        w = _WatcherFinto()
        m = MotoreNews(w, _Impostazioni(),
                       contesto=lambda: Contesto(sta_parlando=stato["parla"]))
        await m.ascolta("mi preoccupa il clima")
        await m.un_giro()
        stato["parla"] = True
        await m.un_giro()
        assert [c.sta_parlando for _, c in w.chiamate] == [False, True]

    async def test_senza_contesto_e_TRI_STATO_non_falso(self) -> None:
        """`None` non è `False`: «non lo so» non interrompe."""
        w = _WatcherFinto()
        m = MotoreNews(w, _Impostazioni())
        await m.ascolta("mi preoccupa il clima")
        await m.un_giro()
        assert w.chiamate[0][1].sta_parlando is None


class TestUnFeedCheSiComportaMALE:
    async def test_un_giro_che_solleva_NON_ferma_il_motore(self) -> None:
        class _Rotto:
            async def giro(self, *_a, **_k):
                raise RuntimeError("il feed ha chiuso la connessione")

        m = MotoreNews(_Rotto(), _Impostazioni())
        await m.ascolta("mi preoccupa il clima")
        assert await m.un_giro() is False
        assert m.giri == 0                     # non conta un giro che non c'è stato

    async def test_una_frase_che_rompe_l_estrattore_non_zittisce_JARVIS(self) -> None:
        """Siamo sul percorso della voce: un'eccezione qui zittirebbe JARVIS."""
        m = MotoreNews(_WatcherFinto(), _Impostazioni())

        async def esplode(*_a, **_k):
            raise RuntimeError("estrattore rotto")

        m.argomenti.aggiorna = esplode
        assert await m.ascolta("qualcosa") == []


class TestIlCicloSiFERMA:
    async def test_avvia_e_ferma(self) -> None:
        m = MotoreNews(_WatcherFinto(), _Impostazioni())
        compito = m.avvia()
        await asyncio.sleep(0)
        assert not compito.done()
        await m.ferma()
        assert compito.cancelled() or compito.done()

    async def test_fermare_due_volte_non_esplode(self) -> None:
        m = MotoreNews(_WatcherFinto(), _Impostazioni())
        m.avvia()
        await m.ferma()
        await m.ferma()


class TestLaCatenaEATTACCATA:
    """Le giunzioni. Il difetto che questo file corregge è precisamente una
    giunzione mancante, ed è la settima in due giorni."""

    def _engine(self) -> str:
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent / "core" / "engine.py"
                ).read_text(encoding="utf-8")

    def test_la_radice_di_composizione_lo_AVVIA(self) -> None:
        s = self._engine()
        assert "MotoreNews(self._watcher, s.news" in s
        assert "self._compito_news = self._news.avvia()" in s, (
            "il motore si costruisce e nessuno lo fa girare: sarebbe la stessa "
            "cosa di prima, con più righe"
        )

    def test_gli_argomenti_vengono_dal_TURNO_VOCALE(self) -> None:
        """§15: dalla conversazione. Senza questa riga il motore girerebbe a
        vuoto per sempre — un ciclo che non fa niente invece di una funzione
        che non c'è, cioè peggio."""
        s = self._engine()
        dopo = s.split("def _voce_su_turno", 1)[1].split("\n    def ", 1)[0]
        assert "self._news.ascolta(detto)" in dopo

    def test_la_card_si_dice_anche_a_VOCE(self) -> None:
        """§15: «card news + menzione vocale breve». È il punto 3 dei NON
        VERIFICATI di Fase 9."""
        s = self._engine()
        dopo = s.split("async def _pubblica_news", 1)[1].split("\n    def ", 1)[0]
        assert 'msg.get("topic") != "news.card"' in dopo
        assert "_annuncia_a_voce" in dopo
        assert "self._ws.broadcast(msg)" in dopo, (
            "la card non arriva più alla scrivania: la menzione vocale si "
            "AGGIUNGE al broadcast, non lo sostituisce"
        )

    def test_lo_spegnimento_FERMA_il_motore(self) -> None:
        s = self._engine()
        dopo = s.split("async def _spegni_gradi", 1)[1].split("\n    async def", 1)[0]
        assert "self._news.ferma()" in dopo

    def test_lo_snapshot_porta_la_CADENZA_e_i_giri(self) -> None:
        s = self._engine()
        assert '"news_motore": (self._news.stato()' in s
        assert "self._news.giri if self._news is not None else 0" in s, (
            "`giri_fatti` è ancora il contatore fermo a zero"
        )
