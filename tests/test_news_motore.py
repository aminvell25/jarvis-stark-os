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
from core.news.topics import EstrattoreLLM


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


class TestIlBatchACCUMULA:
    """§15 dice «batch», e adesso lo e'.

    ## I due difetti, che stavano nella stessa riga

        if ora - self._ultimo < self._batch_s and self._argomenti:

    **① Scartava invece di accumulare.** Dentro la finestra le battute dopo la
    prima non arrivavano mai al modello, e non venivano rimandate: sparivano. A
    60 s si perdeva poco; col batch portato a 600 s (rev 5.25) si perdevano
    fino a dieci minuti di conversazione per ogni frase estratta.

    **② `and self._argomenti` spegneva il limitatore** nel caso piu' comune. Se
    l'estrazione non trovava argomenti — 28 frasi su 43 del corpus — la
    condizione era falsa e **ogni battuta faceva uno spawn**. Non e' un caso di
    laboratorio: e' quello che succede parlando di cose senza argomenti, cioe'
    quasi sempre.

    I due si nascondevano a vicenda: chi guardava lo scarto vedeva «una sola
    battuta per finestra» e concludeva che il limitatore funzionava.
    """

    #: Il comportamento di PRIMA, ricostruito invece che citato: cosi' il
    #: «prima e dopo» non puo' invecchiare.
    @staticmethod
    async def _quante_arrivavano_PRIMA(battute, batch_s=600.0):
        ultimo, argomenti, arrivate = 0.0, [], 0
        for ora, _testo in battute:
            if ora - ultimo < batch_s and argomenti:
                continue
            ultimo = ora
            arrivate += 1
            argomenti = ["clima"]        # il modello trova qualcosa
        return arrivate

    @staticmethod
    def _una_finestra():
        """Dieci battute in dieci minuti, piu' una che chiude la finestra.

        L'ultima serve perche' senza di lei le nove accumulate sarebbero
        ancora **in coda** e non ancora al modello: la correzione trasforma
        «perse» in «in attesa», e la misura dev'essere presa dopo lo
        svuotamento o misurerebbe l'attesa invece della perdita.
        """
        return [(1_000.0 + i * 60, f"mi preoccupa il clima numero {i}")
                for i in range(10)] + [(1_700.0, "e adesso la finestra e' chiusa")]

    async def test_QUANTE_BATTUTE_raggiungono_il_modello(self) -> None:
        """La misura che dice se il difetto e' chiuso, e che prima non faceva
        nessuno: battute al modello su battute dette."""
        battute = self._una_finestra()
        prima = await self._quante_arrivavano_PRIMA(battute)

        async def modello(_: str) -> str:
            return "clima"

        e = EstrattoreLLM(modello, batch_s=600.0)
        for ora, testo in battute:
            await e.aggiorna(testo, adesso=ora)

        perse_prima = len(battute) - prima
        print(f"\n  battute al modello — prima: {prima}/{len(battute)} "
              f"({perse_prima} perse per sempre)  "
              f"dopo: {e.battute_al_modello}/{e.battute_dette} "
              f"({len(e._coda)} in coda, 0 perse)")
        assert prima == 2, "il comportamento di prima non e' quello che credevo"
        assert e.battute_dette == len(battute)
        assert e.battute_al_modello == len(battute), (
            f"{e.battute_dette - e.battute_al_modello - len(e._coda)} battute "
            "ancora scartate"
        )
        assert not e._coda, "la finestra chiusa ha lasciato roba in coda"

    async def test_la_PRIMA_battuta_parte_SUBITO(self) -> None:
        """Forma 2: dopo un silenzio, la prima cosa detta diventa argomento
        adesso e non fra dieci minuti. E' la proprieta' che c'era gia' e che
        accumulare tutto avrebbe tolto."""
        visti: list[str] = []

        async def spia(compito: str) -> str:
            visti.append(compito.split("TESTO:\n", 1)[1])
            return "clima"

        e = EstrattoreLLM(spia, batch_s=600.0)
        await e.aggiorna("mi preoccupa il clima", adesso=1_000.0)
        assert visti == ["mi preoccupa il clima"], "la prima ha aspettato"

        await e.aggiorna("e poi c'e' il governo", adesso=1_100.0)
        await e.aggiorna("di semiconduttori", adesso=1_200.0)
        assert len(visti) == 1, "spawn dentro la finestra"

        await e.aggiorna("che tempo fa domani", adesso=1_700.0)
        assert len(visti) == 2
        assert visti[1].split("\n") == ["e poi c'e' il governo",
                                         "di semiconduttori",
                                         "che tempo fa domani"], (
            "le battute in mezzo non sono state accumulate"
        )

    async def test_una_risposta_VUOTA_non_spegne_il_limitatore(self) -> None:
        """Il secondo difetto. `and self._argomenti` faceva uno spawn per
        battuta ogni volta che il modello non trovava niente — che e' il caso
        comune — e sfondava i 15/ora del Governor in un minuto."""
        n = 0

        async def muto(_: str) -> str:
            nonlocal n
            n += 1
            return ""

        e = EstrattoreLLM(muto, batch_s=600.0)
        for i in range(10):
            await e.aggiorna(f"battuta numero {i}", adesso=1_000.0 + i)
        assert n == 1, f"{n} spawn per 10 battute in 10 secondi"


class TestIlTETTOdellaCODA:
    """L'accumulatore senza fondo sarebbe una perdita travestita da correzione.

    Il tetto viene da fuori — 150 parole al minuto, 7 caratteri per parola —
    come il pavimento di 60 s viene dall'educazione. Cio' che e' nostro e' la
    moltiplicazione: **quanto si puo' dire in una finestra intera parlando
    senza fermarsi**, quindi il tetto SEGUE il batch.
    """

    def test_il_tetto_SEGUE_il_batch(self) -> None:
        assert EstrattoreLLM(batch_s=600.0).tetto_coda == 10_500
        assert EstrattoreLLM(batch_s=150.0).tetto_coda == 2_625
        # e non e' una costante travestita
        assert EstrattoreLLM(batch_s=60.0).tetto_coda == 1_050

    async def test_al_superamento_si_manda_in_ANTICIPO_e_non_si_scarta(self) -> None:
        """Scartare la piu' vecchia o la piu' nuova sarebbe lo stesso difetto in
        un posto nuovo, e silenzioso come quello appena corretto."""
        visti: list[str] = []

        async def spia(compito: str) -> str:
            visti.append(compito.split("TESTO:\n", 1)[1])
            return "clima"

        e = EstrattoreLLM(spia, batch_s=60.0)          # tetto 1 050 caratteri
        await e.aggiorna("prima battuta", adesso=1_000.0)
        lunga = "e poi ti dico una cosa lunga " * 20   # ~560 caratteri
        await e.aggiorna(lunga, adesso=1_001.0)
        assert len(visti) == 1, "invio anticipato troppo presto"
        await e.aggiorna(lunga, adesso=1_002.0)        # supera il tetto

        assert len(visti) == 2, "il tetto non ha fatto scattare l'invio"
        assert e.battute_al_modello == e.battute_dette == 3, "una battuta persa"
        assert visti[1].count("cosa lunga") == 40, "il contenuto e' stato tagliato"

    async def test_l_invio_anticipato_sta_DENTRO_la_quota(self) -> None:
        """Riempire il tetto richiede una finestra intera di parlato
        ininterrotto, quindi al peggio il ritmo raddoppia: 12 spawn l'ora
        contro i 15 di `MAX_PER_WINDOW`. Non e' fortuna — e' il tetto a essere
        definito come «una finestra di parlato»."""
        from core.llm.governor import MAX_PER_WINDOW

        e = EstrattoreLLM(batch_s=600.0)
        al_massimo_per_ora = 2 * 3600 / e._batch_s
        assert al_massimo_per_ora <= MAX_PER_WINDOW


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
