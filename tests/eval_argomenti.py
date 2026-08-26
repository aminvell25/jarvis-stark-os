"""EVAL — il banco degli argomenti (§15).

## Perche' esiste

La diagnosi che questo file sostituisce era un aneddoto su tre frasi contate a
mano: «una frase su tre da' un verbo e perde i sostantivi». Era falsa. Il
meccanismo vero e' che la vecchia regola

    n >= MIN_OCCORRENZE or len(p) >= MIN_LUNGHEZZA_SINGOLA

su **una frase sola** ha tutti i conteggi a 1, quindi l'`or` collassa a «e'
lunga» — e la lunghezza in italiano non dice niente sull'essere un argomento.
`clima` (5) e `governo` (7) cadevano, `pensando` (8) passava.

Il difetto di quella diagnosi non era il meccanismo sbagliato: era il metodo.
Contava i successi, e i falsi positivi erano invisibili. Da qui il banco, e da
qui **precisione e richiamo** invece di «due su tre».

## Da dove vengono le frasi

**Non le ho scritte per questo banco.** Sono le 43 frasi conversazionali di
`tests/t0_corpus.py`, importate e non copiate, scritte mesi fa per una
proprieta' ORTOGONALE — che il parser T0 le lasci andare a T1 — e quindi
impossibili da avere scelto perche' questa regola le passasse. E' la garanzia
piu' forte contro il sovradattamento che si possa avere senza chiedere a
qualcun altro di dettarle.

Il prezzo: **28 frasi su 43 non hanno nessun argomento**, perche' venti di loro
sono modi di dire scelti per somigliare a comandi. E' una fetta avversaria
della lingua, non un campione: la precisione misurata qui e' un **limite
inferiore**, non la precisione che si vedrebbe parlando del mondo. Va detto
prima di leggere i numeri.

## Le etichette

Le etichette sono **mie**, e questa e' la meta' debole del banco: chi ripara la
regola ha scritto la verita' di riferimento. Le due regole che ho seguito, per
renderle almeno controllabili:

1. **Un argomento e' una cosa di cui si potrebbero leggere notizie.** «bagno»
   si', «pazienza» no, anche se sono tutti e due sostantivi introdotti da un
   articolo.
2. **Solo parole che compaiono nella frase**, perche' l'estrattore e'
   estrattivo: «meteo» non e' un'etichetta ammessa per «che tempo fa domani».

E una scelta dichiarata: la verita' e' a **token singoli**, non a locuzioni.
«divulgazione scientifica» sono due argomenti, non uno, perche' il gate
confronta parole con parole.

## La metrica

Precisione e richiamo **micro-mediati**: si sommano i veri positivi di tutte le
frasi e si divide una volta sola. Le frasi con attesa vuota contribuiscono
quindi solo alla precisione — ed e' li' che un falso positivo diventa visibile
invece di nascondersi dietro i successi.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from core.news.topics import (
    FERME,
    MAX_ARGOMENTI,
    MIN_LUNGHEZZA,
    EstrattoreLLM,
    estrai_locale,
)
from tests.t0_corpus import CONVERSAZIONALI

#: frase → argomenti attesi. Le chiavi DEVONO coincidere con `CONVERSAZIONALI`,
#: e un test lo verifica: cosi' una frase aggiunta la' non puo' entrare qui
#: senza etichetta, ne' un'etichetta sopravvivere a una frase cancellata.
ATTESI: dict[str, set[str]] = {
    # ── frasi che parlano di qualcosa (15) ───────────────────────────────────
    "mi metti un po' di musica mentre lavoro": {"musica", "lavoro"},
    "cosa ne pensi dei video di divulgazione scientifica":
        {"video", "divulgazione", "scientifica"},
    "ieri ho visto un documentario interessante": {"documentario"},
    "che ne pensi di questo progetto": {"progetto"},
    "spiegami come funziona un motore diesel": {"motore", "diesel"},
    "quanto manca a natale": {"natale"},
    # `tempo` qui e' il meteo. Nella frase «non trovo mai il tempo di leggere»
    # e' la stessa parola e non e' un argomento: un estrattore a sacchetto di
    # parole non puo' distinguerle, e il falso positivo di la' e' il prezzo del
    # vero positivo di qua. E' un limite della classe di soluzioni, non un bug.
    "che tempo fa domani": {"tempo"},
    "scrivimi due righe per un'email di scuse": {"email"},
    "non ricordo dove ho messo le chiavi": {"chiavi"},
    "qual e' la capitale del portogallo": {"capitale", "portogallo"},
    "traduci questa frase in inglese": {"inglese"},
    "perche' il cielo e' blu": {"cielo"},
    "sto pensando di rifare il bagno": {"bagno"},
    "il file e' importante": {"file"},
    "volume alto di poesie": {"poesie"},

    # ── frasi che non parlano di niente (28) ─────────────────────────────────
    # Sono la meta' che conta: un estrattore che risponde sempre qualcosa qui
    # accumula falsi positivi, e nessun conteggio di successi lo mostrerebbe.
    "come stai oggi": set(),
    "raccontami una cosa interessante": set(),
    "ho avuto una giornata pesante": set(),
    "secondo te conviene comprarlo": set(),
    "mi sento stanco": set(),
    "aiutami a decidere": set(),
    "fammi ridere": set(),
    "cosa ne dici se andiamo avanti cosi'": set(),
    "ricordami perche' l'avevamo deciso": set(),
    "buonanotte jarvis": set(),
    "cerco sempre di arrivare puntuale": set(),
    "non trovo mai il tempo di leggere": set(),
    "apriti cielo": set(),
    "chiudiamo qui il discorso": set(),
    "mostrati un po' piu' paziente": set(),
    "vai tranquillo": set(),
    "alza pure la voce se non mi senti": set(),
    "abbassa i toni per favore": set(),
    "cerca di capirmi": set(),
    "trova il modo di dirglielo": set(),
    "apri bene le orecchie": set(),
    "chiudi un occhio stavolta": set(),
    "mostra un po' di pazienza": set(),
    "vado a fare due passi": set(),
    "spegni la luce quando esci": set(),
    "accendi la fantasia": set(),
    "workspace non e' una parola italiana": set(),
    "nascondi la delusione": set(),
}

#: La barra per la decisione su haiku, **dichiarata prima di misurare** — se no
#: e' una razionalizzazione a posteriori.
#:
#: Si deriva dal budget di §15 e non si sceglie: un argomento falso fa
#: interrompere JARVIS sulla cosa sbagliata, e con 3 interruzioni all'ora una
#: precisione `P` ne lascia `3(1-P)` fuori tema. Perche' ne resti meno di una:
#:
#:     3 (1 - P) < 1   →   P > 2/3
BARRA_PRECISIONE = 2 / 3


# ── la regola di PRIMA, tenuta viva per il confronto ─────────────────────────
#
# Non un numero copiato in una `assert`: la regola vecchia gira davvero, sullo
# stesso corpus, dentro lo stesso giro di test. Cosi' il «prima e dopo» non puo'
# invecchiare, e un giorno in cui qualcuno rimettesse la vecchia regola in
# `topics.py` i due risultati coinciderebbero e il confronto diventerebbe rosso.
_VECCHIO_TOKEN = re.compile(r"[a-zàèéìòóù']{%d,}" % MIN_LUNGHEZZA)


def regola_vecchia(testo: str) -> set[str]:
    """`n >= 2 or len(p) >= 8`, con l'apostrofo dentro il token."""
    conteggi: dict[str, int] = {}
    for p in _VECCHIO_TOKEN.findall(testo.lower()):
        if p in FERME:
            continue
        conteggi[p] = conteggi.get(p, 0) + 1
    notevoli = {p: n for p, n in conteggi.items() if n >= 2 or len(p) >= 8} or conteggi
    return {p for p, _ in sorted(notevoli.items(),
                                 key=lambda kv: (-kv[1], kv[0]))[:MAX_ARGOMENTI]}


def regola_oggi(testo: str) -> set[str]:
    return {a.parola for a in estrai_locale(testo)}


def catena_larga(testo: str) -> set[str]:
    """L'alternativa MISURATA E SCARTATA: dopo il primo articolo, tieni tutto.

    E' l'unica regola che recupera «di intelligenza artificiale e
    semiconduttori». Ereditare l'introduttore solo attraverso la congiunzione
    non basta — la catena si e' gia' rotta su `artificiale`, che segue un
    sostantivo — e infatti sul banco non cambia nemmeno un esito.

    Sta qui e non in `topics.py` perche' non e' adottata: serve a tenere
    misurato il suo prezzo, cosi' la decisione resta rivedibile con un numero
    invece che con un ricordo.
    """
    from core.news.topics import INTRODUCONO, TOKEN

    parole, conteggi, aperta = TOKEN.findall(testo.lower()), {}, False
    for prima, p in zip([""] + parole, parole):
        if prima in INTRODUCONO:
            aperta = True
        if aperta and len(p) >= MIN_LUNGHEZZA and p not in FERME:
            conteggi[p] = conteggi.get(p, 0) + 1
    return set(sorted(conteggi, key=lambda k: (-conteggi[k], k))[:MAX_ARGOMENTI])


def con_ripiego_a_tutti(testo: str) -> set[str]:
    """La vecchia clausola `or conteggi`: se il filtro non tiene nessuno,
    tienili tutti. Tenuta viva per misurarne il prezzo."""
    from core.news.topics import TOKEN

    r = regola_oggi(testo)
    if r:
        return r
    return {p for p in TOKEN.findall(testo.lower())
            if len(p) >= MIN_LUNGHEZZA and p not in FERME}


class Misura:
    """Veri positivi, falsi positivi, mancati — e le due frazioni."""

    def __init__(self, regola) -> None:
        self.tp = self.fp = self.fn = 0
        self.errori: list[tuple[str, set[str], set[str]]] = []
        for frase in CONVERSAZIONALI:
            atteso, ottenuto = ATTESI[frase], regola(frase)
            self.tp += len(ottenuto & atteso)
            self.fp += len(ottenuto - atteso)
            self.fn += len(atteso - ottenuto)
            if ottenuto != atteso:
                self.errori.append((frase, atteso, ottenuto))

    @property
    def precisione(self) -> float:
        # Una regola che non propone mai niente non ha precisione 1: non ha
        # precisione. Il richiamo, misurato accanto, e' cio' che la smaschera.
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def richiamo(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    def __str__(self) -> str:
        return (f"P={self.precisione:.3f} R={self.richiamo:.3f} "
                f"(tp={self.tp} fp={self.fp} fn={self.fn})")


#: Una congiunzione coordinante isolata, oppure una virgola.
#:
#: ⚠️ `e'` NON conta: nel corpus e' la copula «è» scritta in ASCII, e `TOKEN` —
#: che l'apostrofo lo taglia — non le distingue piu'. Qui il criterio gira sulla
#: frase GREZZA, dove la distinzione c'e' ancora.
#:
#: Il criterio e' scelto per essere **indipendente dal rimedio**: conta una
#: proprieta' di superficie del corpus, non cio' che una regola nuova
#: riuscirebbe a recuperare.
COORDINA = re.compile(r"(?<![a-z\u00e0\u00e8\u00e9\u00ec\u00f2\u00f3\u00f9'])(?:e|ed|o|od)(?![a-z\u00e0\u00e8\u00e9\u00ec\u00f2\u00f3\u00f9'])")


def coordina(frase: str) -> bool:
    return bool(COORDINA.search(frase)) or "," in frase


class TestIlRilevatoreDiCOORDINAZIONE:
    """Il controllo del controllo. Il conteggio piu' sotto vale **zero**, e uno
    zero puo' venire da una regex rotta invece che da un corpus senza
    coordinazioni: senza queste nove prove non si saprebbe quale dei due."""

    @pytest.mark.parametrize("frase,atteso", [
        ("sto leggendo di intelligenza artificiale e semiconduttori", True),
        ("mi preoccupa il clima, e cosa fa il governo", True),
        ("parliamo di clima ed energia", True),
        ("il caffe o il te", True),
        ("mele pere e banane", True),
        # la copula, che con l'apostrofo si scrive come la congiunzione
        ("qual e' la capitale del portogallo", False),
        ("il file e' importante", False),
        ("perche' il cielo e' blu", False),
        ("come stai oggi", False),
    ])
    def test_si_accende_dove_deve(self, frase: str, atteso: bool) -> None:
        assert coordina(frase) is atteso


class TestIlBanco:
    def test_ogni_frase_e_ETICHETTATA(self) -> None:
        """Il corpus e' importato: se qualcuno ne aggiunge una la', qui manca
        l'attesa, e una frase senza attesa non misura niente."""
        senza = [f for f in CONVERSAZIONALI if f not in ATTESI]
        assert not senza, f"frasi senza etichetta: {senza}"

    def test_nessuna_etichetta_ORFANA(self) -> None:
        """E il contrario: un'etichetta rimasta dietro a una frase cancellata
        gonfierebbe il banco con una frase che nessuno misura."""
        orfane = [f for f in ATTESI if f not in CONVERSAZIONALI]
        assert not orfane, f"etichette senza frase: {orfane}"

    def test_il_banco_e_abbastanza_grande(self) -> None:
        assert len(CONVERSAZIONALI) >= 40

    def test_la_META_del_banco_non_ha_argomenti(self) -> None:
        """Il pavimento che rende il banco capace di vedere i falsi positivi.
        Senza frasi ad attesa vuota, una regola che risponde sempre qualcosa
        sembrerebbe brava."""
        vuote = sum(1 for f in CONVERSAZIONALI if not ATTESI[f])
        assert vuote >= len(CONVERSAZIONALI) / 3, (
            f"solo {vuote} frasi su {len(CONVERSAZIONALI)} hanno attesa vuota"
        )

    def test_la_metrica_smaschera_la_regola_MUTA(self) -> None:
        """Il baro piu' semplice: non rispondere mai. Precisione perfetta per
        vacuita', funzione spenta. Qui vale **zero**, non uno — non avere
        occasioni di sbagliare non e' precisione — e il richiamo lo conferma."""
        muta = Misura(lambda _frase: set())
        assert muta.precisione == 0.0
        assert muta.richiamo == 0.0

    def test_le_etichette_sono_ESTRATTIVE(self) -> None:
        """Un'etichetta che non compare nella frase sarebbe irraggiungibile per
        costruzione, e abbasserebbe il richiamo per un difetto del banco invece
        che della regola."""
        from core.news.topics import TOKEN

        for frase, atteso in ATTESI.items():
            dette = set(TOKEN.findall(frase.lower()))
            assert atteso <= dette, f"{frase!r}: etichette assenti {atteso - dette}"


class TestLaRegolaRIPARATA:
    def test_la_precisione_e_MIGLIORE_di_prima(self) -> None:
        """Il «prima e dopo», con il prima calcolato adesso e non citato."""
        prima, dopo = Misura(regola_vecchia), Misura(regola_oggi)
        print(f"\n  argomenti — prima: {prima}\n              dopo:  {dopo}")
        assert dopo.precisione > prima.precisione * 2, (
            f"la regola nuova non paga: {dopo} contro {prima}"
        )

    def test_e_NON_l_ha_comprata_col_silenzio(self) -> None:
        """Il modo piu' facile di alzare la precisione e' proporre di meno, fino
        a non proporre niente: precisione perfetta e funzione spenta. Il
        richiamo e' il guardiano di quel baro, ed e' per questo che non basta
        misurare la precisione anche se la barra e' solo su di lei."""
        prima, dopo = Misura(regola_vecchia), Misura(regola_oggi)
        assert dopo.richiamo >= prima.richiamo, (
            f"richiamo sceso da {prima.richiamo:.3f} a {dopo.richiamo:.3f}: "
            "la precisione e' stata comprata smettendo di rispondere"
        )

    def test_l_apostrofo_non_incolla_piu_l_articolo(self) -> None:
        """`un'email` era UNA parola di otto lettere — lunga abbastanza da
        passare la vecchia soglia — e l'argomento vero non esisteva."""
        assert "email" in regola_oggi("scrivimi due righe per un'email di scuse")
        assert "un'email" in regola_vecchia("scrivimi due righe per un'email di scuse")

    def test_perche_con_l_apostrofo_sfuggiva_a_FERME(self) -> None:
        """`FERME` contiene `perche` e `perché`, non `perche'`.

        ⚠️ La prima versione di questo test asseriva `"perche" not in ...`, e
        restava verde anche ritirando la correzione — perche' con la vecchia
        regola il token era `perche'`, con l'apostrofo, e la parola senza non
        c'era comunque. Un criterio vero per assenza del fenomeno (§11.7
        regola 4). Adesso guarda l'insieme intero, che non puo' essere verde
        per distrazione.
        """
        assert "perche'" in regola_vecchia("perche' il cielo e' blu")
        assert regola_oggi("perche' il cielo e' blu") == {"cielo"}

    def test_la_frase_del_difetto(self) -> None:
        """La frase da cui e' partita la revisione. `preoccupa` ha 9 lettere e
        vinceva; `clima` e `governo` cadevano per la lunghezza."""
        assert regola_vecchia("mi preoccupa il clima e il governo") == {"preoccupa"}
        assert regola_oggi("mi preoccupa il clima e il governo") == {"clima", "governo"}


class TestINumeriCITATI:
    """Un numero copiato in un commento invecchia in silenzio.

    ⚠️ E' successo due volte nello stesso file: `topics.py` ha portato **0,421**
    per un giorno mentre il valore vero era **0,410**, e **0,155** come prezzo
    del ripiego mentre era **0,136**. Nessuno dei due era sbagliato quando fu
    scritto — sono rimasti indietro quando `INTRODUCONO` ha preso le forme
    elise. Il secondo l'ha trovato questo test, non una rilettura.
    """

    #: Le due forme in cui una precisione compare nei commenti.
    CITAZIONE = re.compile(
        r"precisione \*{0,2}(0,\d{3})|\*{0,2}(0,\d{3})\*{0,2} di precisione")
    SORGENTI = ("core/news/topics.py", "core/engine.py")

    def test_la_precisione_citata_e_quella_MISURATA(self) -> None:
        """Ogni cifra citata dev'essere una delle quantita' che il banco
        calcola — non solo la precisione di adesso: anche quella di prima, il
        prezzo del ripiego e la precisione dell'alternativa scartata sono
        numeri altrettanto capaci di invecchiare."""
        oggi, prima = Misura(regola_oggi), Misura(regola_vecchia)
        ripiego, larga = Misura(con_ripiego_a_tutti), Misura(catena_larga)
        leciti = {
            f"{v:.3f}".replace(".", ","): nome for nome, v in [
                ("precisione di adesso", oggi.precisione),
                ("precisione di prima", prima.precisione),
                ("precisione col ripiego", ripiego.precisione),
                ("precisione della catena larga", larga.precisione),
                ("prezzo del ripiego", oggi.precisione - ripiego.precisione),
            ]
        }
        radice = Path(__file__).resolve().parent.parent
        trovati = []
        for f in self.SORGENTI:
            testo = (radice / f).read_text(encoding="utf-8")
            for a, b in self.CITAZIONE.findall(testo):
                trovati.append((f, a or b))
        assert trovati, "nessuna citazione trovata: la regex non guarda piu' niente"
        sbagliate = [(f, n) for f, n in trovati if n not in leciti]
        assert not sbagliate, (
            f"numeri invecchiati: {sbagliate}. Le quantita' vere sono {leciti}"
        )


class TestLaBarraDIhaiku:
    def test_il_locale_NON_arriva_alla_barra(self) -> None:
        """La ragione per cui haiku e' collegato, scritta come test.

        ⚠️ Se questo test diventa rosso vuol dire che la regola locale ha
        superato la barra da sola: allora lo spawn di haiku non e' piu'
        giustificato e va tolto, non aggiornata la soglia.
        """
        m = Misura(regola_oggi)
        assert m.precisione < BARRA_PRECISIONE, (
            f"precisione locale {m.precisione:.3f} sopra la barra "
            f"{BARRA_PRECISIONE:.3f}: haiku non serve piu'"
        )

    def test_gli_errori_residui_sono_SINTAGMI_REGOLARI(self) -> None:
        """Perche' nessuna regola di forma puo' fare meglio: cio' che resta
        sbagliato e' «la luce», «la fantasia», «le orecchie» — articolo piu'
        sostantivo, identici a «il bagno». La differenza e' semantica, e questo
        e' il confine della classe di soluzioni, non un difetto da limare."""
        m = Misura(regola_oggi)
        falsi = {p for _, att, got in m.errori for p in got - att}
        for parola in ("luce", "fantasia", "orecchie", "pazienza"):
            assert parola in falsi, (
                f"{parola!r} non e' piu' un falso positivo: la regola e' "
                "cambiata e questa spiegazione va rimisurata"
            )


class TestIlPREZZO:
    """Che cosa la regola nuova ha smesso di fare. Va scritto qui, non
    scoperto fra sei mesi.

    ⚠️ La prima stesura diceva che il caso perso e' «il sostantivo nudo o
    l'elenco». **Era il caso sbagliato**: quelli sono rari nel parlato. Il caso
    perso e' la **coordinazione dentro una frase normale**, che e' come si
    parla — e questo banco non ne contiene nemmeno una.
    """

    def test_la_COORDINAZIONE_e_il_caso_perso(self) -> None:
        """«di intelligenza artificiale e semiconduttori» → solo `intelligenza`.

        `artificiale` segue un sostantivo, `semiconduttori` segue una
        congiunzione: nessuno dei due segue una parola di `INTRODUCONO`, e
        cadono proprio i termini piu' specifici della frase.
        """
        assert regola_oggi("sto leggendo di intelligenza artificiale "
                           "e semiconduttori") == {"intelligenza"}

    def test_il_banco_NON_misura_la_coordinazione(self) -> None:
        """Il limite del banco, fissato come tripwire invece che come nota.

        **Zero** frasi su 43 contengono una coordinazione: qualunque numero
        sulla coordinazione calcolato su questo corpus sarebbe calcolato su un
        insieme vuoto. Il richiamo aggregato non la vede perche' non c'e'.

        ⚠️ Se questo test diventa rosso vuol dire che il corpus **adesso** ne
        contiene: allora il sottoinsieme si puo' misurare davvero, e la
        decisione sul rimedio va ripresa con quel numero in mano.
        """
        quante = sum(1 for f in CONVERSAZIONALI if coordina(f))
        assert quante == 0, (
            f"{quante} frasi con coordinazione: il sottoinsieme esiste, "
            "misuralo invece di dichiararlo non misurabile"
        )

    def test_la_catena_LARGA_costa_precisione(self) -> None:
        """L'unico rimedio che recupererebbe quella frase — e il suo prezzo.

        «Ereditare l'introduttore attraverso la congiunzione» da solo e' un
        **non-fatto**: non cambia niente sul banco e non recupera nemmeno la
        frase, perche' la catena si e' gia' rotta su `artificiale`. Serve
        tenere la catena aperta anche attraverso le parole piene, e allora la
        frase si recupera.

        Il banco non ha coordinazioni, quindi non puo' mostrarne il beneficio;
        puo' pero' mostrarne il **costo**, perche' quella regola si accende su
        13 frasi su 43. Per la politica dichiarata prima di misurare — la
        precisione e' il cancello, il richiamo si riporta — non si adotta.
        """
        assert catena_larga("sto leggendo di intelligenza artificiale e "
                            "semiconduttori") == {"intelligenza", "artificiale",
                                                  "semiconduttori"}
        stretta, larga = Misura(regola_oggi), Misura(catena_larga)
        print(f"\n  catena stretta (adottata): {stretta}"
              f"\n  catena larga  (scartata):  {larga}")
        assert larga.precisione < stretta.precisione
        assert larga.richiamo > stretta.richiamo

    def test_un_sostantivo_NUDO_non_produce_niente(self) -> None:
        """Senza articolo davanti, la regola non ha la posizione su cui decide.

        Non e' un caso di laboratorio: era l'input di tre test del motore, che
        scrivevano `ascolta("clima")` come scorciatoia. Nel parlato vero un
        sostantivo nudo e' raro — si dice «il clima», «di clima» — ma quando
        capita l'esito e' silenzio, e il silenzio §15 lo tollera.
        """
        assert regola_oggi("clima") == set()
        assert regola_oggi("il clima") == {"clima"}

    def test_un_ELENCO_senza_articoli_si_perde(self) -> None:
        """Il caso peggiore della classe: parlando per elenchi — «clima,
        governo, inflazione» — non si aggancia niente."""
        assert regola_oggi("clima, governo, inflazione") == set()


class TestIlRipiegoAtuttiITOKEN:
    def test_tenerli_tutti_quando_non_si_trova_niente_COSTA(self) -> None:
        """La misura che giustifica la lista vuota.

        La vecchia regola aveva `... or conteggi`: se il filtro non teneva
        nessuno, li teneva tutti. Sembra prudenza — meglio qualcosa che niente —
        e invece e' il caso in cui la regola sa di non sapere, e risponde
        comunque.
        """
        secco, ripiegato = Misura(regola_oggi), Misura(con_ripiego_a_tutti)
        print(f"\n  senza ripiego: {secco}\n  con ripiego:   {ripiegato}")
        assert ripiegato.precisione < secco.precisione


class TestLaRispostaDelModelloEESTRATTIVA:
    """L'allowlist che si costruisce da sola: il vocabolario ammesso e' cio' che
    e' stato pronunciato. Vale per la risposta del modello, non per il locale.
    """

    async def test_una_parola_inventata_non_diventa_un_argomento(self) -> None:
        async def inventa(_: str) -> str:
            return "clima, geopolitica, borsa"

        e = EstrattoreLLM(inventa, batch_s=0)
        await e.aggiorna("mi preoccupa il clima")
        assert e.parole() == ["clima"], (
            "il modello ha aggiunto argomenti che non sono stati detti, e quegli "
            "argomenti sceglierebbero quali notizie La raggiungono"
        )

    async def test_una_risposta_in_PROSA_non_produce_argomenti(self) -> None:
        async def prosa(_: str) -> str:
            return "Mi dispiace, non riesco a individuare argomenti precisi."

        e = EstrattoreLLM(prosa, batch_s=0)
        await e.aggiorna("mi preoccupa il clima")
        assert e.parole() == []

    async def test_il_ripiego_al_locale_e_ANNUNCIATO(self) -> None:
        """Invariante 12, nella forma che vale anche fuori dalla voce: un
        ripiego silenzioso e' peggio di un errore."""
        async def esplode(_: str) -> str:
            raise RuntimeError("quota finita")

        e = EstrattoreLLM(esplode, batch_s=0)
        await e.aggiorna("mi preoccupa il clima e il governo")
        assert sorted(e.parole()) == ["clima", "governo"]


# ── la registrazione ─────────────────────────────────────────────────────────

ESITO = Path(__file__).resolve().parent.parent / "docs" / "acceptance" / "ARGOMENTI-CORPUS.json"
#: Le due cose che, cambiando, rendono vecchio il numero.
FONTI = ("core/news/topics.py", "tests/eval_argomenti.py")


def _registra(prima: Misura, dopo: Misura) -> None:
    """Scrive la misura — **solo se e' cambiato cio' che misura**.

    Stessa forma di `T0-CORPUS.json`: l'impronta dice CHE COSA e' stato
    misurato, cosi' un numero vecchio si riconosce, e un giro di test su
    sorgenti immutati non sporca `git status`.
    """
    radice = ESITO.parent.parent.parent
    h = hashlib.sha256()
    for f in FONTI:
        h.update((radice / f).read_bytes())
    impronta = h.hexdigest()[:16]
    if ESITO.exists():
        try:
            if json.loads(ESITO.read_text(encoding="utf-8")).get("impronta") == impronta:
                return
        except json.JSONDecodeError:
            pass
    ESITO.write_text(json.dumps({
        "_": "GENERATO da tests/eval_argomenti.py — non modificare a mano",
        "fonti": list(FONTI),
        "impronta": impronta,
        "frasi": len(CONVERSAZIONALI),
        "frasi_senza_argomenti": sum(1 for f in CONVERSAZIONALI if not ATTESI[f]),
        # ⚠️ Zero. Il banco non puo' dire NIENTE sulla coordinazione, che e' il
        # caso che la regola perde. Rilevatore controllato su nove prove.
        "frasi_con_coordinazione": sum(1 for f in CONVERSAZIONALI if coordina(f)),
        "argomenti_attesi": sum(len(a) for a in ATTESI.values()),
        "provenienza": "tests/t0_corpus.py CONVERSAZIONALI — scritte per T0, "
                       "non per questo banco; etichette mie",
        "barra_precisione": round(BARRA_PRECISIONE, 4),
        "barra_da": "3 interruzioni/ora (§15): 3(1-P) < 1",
        "prima": {"precisione": round(prima.precisione, 4),
                  "richiamo": round(prima.richiamo, 4),
                  "tp": prima.tp, "fp": prima.fp, "fn": prima.fn,
                  "regola": "n >= 2 or len(p) >= 8"},
        "dopo": {"precisione": round(dopo.precisione, 4),
                 "richiamo": round(dopo.richiamo, 4),
                 "tp": dopo.tp, "fp": dopo.fp, "fn": dopo.fn,
                 "regola": "introdotta da articolo o preposizione"},
        "haiku_collegato": dopo.precisione < BARRA_PRECISIONE,
        "limite": "28 frasi su 43 sono modi di dire scelti per somigliare a "
                  "comandi: la precisione qui e' un limite inferiore",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class TestLaMisuraSIREGISTRA:
    def test_scrive_l_esito(self) -> None:
        """Un numero che vive solo nell'output di pytest non si puo' confrontare
        col mese prossimo."""
        _registra(Misura(regola_vecchia), Misura(regola_oggi))
        assert ESITO.exists()
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        assert d["frasi"] == len(CONVERSAZIONALI)


@pytest.mark.parametrize("frase", CONVERSAZIONALI)
def test_nessuna_frase_fa_SOLLEVARE_l_estrattore(frase: str) -> None:
    """Siamo sul percorso della voce: un'eccezione qui zittirebbe JARVIS."""
    estrai_locale(frase)
