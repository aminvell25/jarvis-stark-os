"""EVAL — quanto JARVIS ritrova di cio' che ricorda.

## Perche' esiste

Ci sono quasi duemila test sul **codice** e zero sul **comportamento**. Il
giorno in cui il recupero della memoria scendera' sotto soglia — e scendera' —
nessun test diventera' rosso, perche' nessuno misura il recupero.

`MemoryStore.cerca()` e' una ricerca per **sottostringa**, in ordine
**alfabetico**, con un `break` al primo `limite` risultati:

    if ago in testo.lower() or ago in p.stem:   # sottostringa
    if len(out) >= limite: break                # e i primi che capitano

Su dieci file funziona. Il piano dice «non con duecento», e questo banco
esiste per dire **quando** smette, con un numero invece che con una previsione.

## Che cosa misura

Due assi, e il secondo e' quello che conta:

    per DIMENSIONE   10 topic contro 200. La differenza e' la degradazione
    per FORMA        domande LETTERALI (una sottostringa della nota) contro
                     PARAFRASATE (stessa cosa, parole diverse)

Una ricerca per sottostringa ha recall 1,0 sulle letterali per costruzione: e'
la stessa stringa. Il numero interessante e' l'altro, e la distanza fra i due
e' esattamente il debito che un indice vero pagherebbe.

E misura il **rifiuto corretto**: cinque domande la cui risposta NON e' in
memoria devono restituire zero risultati. Un recupero che risponde sempre
qualcosa e' peggio di uno che tace, perche' chi lo usa non puo' distinguere
«non lo so» da una ricostruzione plausibile.

## La meta' debole, dichiarata

⚠️ **Il corpus e le domande sono miei.** `eval_argomenti` puo' dire che le sue
frasi vengono da `t0_corpus`, scritto mesi prima per una proprieta' ortogonale;
qui non esiste un corpus del genere. I topic veri su questa macchina sono
**due**, sono privati, e non si committano.

Quindi: le venti domande le ho scritte io, e chi le scrive puo' scriverle
facili. Le due regole che ho seguito per renderle almeno controllabili:

1. **Le letterali contengono una sottostringa esatta della nota**, quindi il
   loro esito e' prevedibile a priori — servono da riferimento, non da misura.
2. **Le parafrasate non condividono nessuna parola di contenuto** con la nota
   che devono trovare. Non «quasi nessuna»: nessuna. E' una condizione che si
   verifica meccanicamente, e questo file la verifica (`test_le_parafrasi_sono
   _DAVVERO_parafrasi`) invece di fidarsi di chi le ha scritte.

La seconda regola e' cio' che impedisce di barare senza accorgersene.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.memory.attribuzione import parole
from core.memory.store import MemoryStore

RADICE = Path(__file__).resolve().parent.parent
ESITO = RADICE / "docs" / "acceptance" / "TERMOMETRO.json"

#: Le dieci note del corpus. Contenuto plausibile per un JARVIS domestico,
#: scritto nella forma che `Consolidatore` produce davvero.
NOTE: dict[str, str] = {
    "stampanti": "Il Signore ha due stampanti 3D in laboratorio, una a "
                 "filamento e una a resina. La resina la usa solo per i "
                 "pezzi piccoli.",
    "caffe": "Il Signore prende il caffe' amaro, e mai dopo le sedici.",
    "auto": "L'automobile e' una station wagon diesel del 2016. Il tagliando "
            "va fatto ogni ventimila chilometri.",
    "casa": "L'appartamento e' al terzo piano senza ascensore. Il "
            "riscaldamento e' a metano, autonomo.",
    "lavoro": "Il Signore lavora da casa il martedi' e il giovedi'. Le "
              "riunioni le preferisce di mattina.",
    "musica": "Ascolta soprattutto jazz modale e musica da camera. Non "
              "sopporta il rumore di fondo mentre legge.",
    "salute": "Corre tre volte a settimana. Ha avuto una distorsione alla "
              "caviglia destra a giugno.",
    "cucina": "Cucina spesso pesce azzurro. E' intollerante al lattosio.",
    "viaggi": "L'ultimo viaggio e' stato in Portogallo, in autunno. Odia "
              "volare di notte.",
    "libri": "Legge saggistica storica prima di dormire. I romanzi li "
             "abbandona a meta'.",
}

#: `(domanda, topic atteso, forma)`. `forma` e' `letterale` o `parafrasi`.
DOMANDE: list[tuple[str, str, str]] = [
    # ── letterali: contengono una sottostringa esatta della nota ────────────
    ("stampanti 3D", "stampanti", "letterale"),
    ("caffe' amaro", "caffe", "letterale"),
    ("station wagon", "auto", "letterale"),
    ("terzo piano", "casa", "letterale"),
    ("riunioni", "lavoro", "letterale"),
    ("jazz modale", "musica", "letterale"),
    ("caviglia", "salute", "letterale"),
    ("pesce azzurro", "cucina", "letterale"),
    ("Portogallo", "viaggi", "letterale"),
    ("saggistica", "libri", "letterale"),
    # ── parafrasi: NESSUNA parola di contenuto in comune con la nota ───────
    ("che macchinari tiene nell'officina", "stampanti", "parafrasi"),
    ("come lo beve la mattina", "caffe", "parafrasi"),
    ("quando serve la manutenzione al veicolo", "auto", "parafrasi"),
    ("come si scalda l'abitazione", "casa", "parafrasi"),
    ("in quali giorni non va in ufficio", "lavoro", "parafrasi"),
    ("che genere preferisce all'ascolto", "musica", "parafrasi"),
    ("che infortunio ha rimediato", "salute", "parafrasi"),
    ("quali alimenti deve evitare", "cucina", "parafrasi"),
    ("dov'e' andato in vacanza", "viaggi", "parafrasi"),
    ("che tipo di volumi tiene sul comodino", "libri", "parafrasi"),
]

#: Domande la cui risposta **non e' in memoria**. Devono restituire zero.
ASSENTI: list[str] = [
    "che cane ha",
    "quanto guadagna",
    "come si chiama sua sorella",
    "che gruppo sanguigno ha",
    "in che scuola andava",
]

#: Quanti topic di rumore nel corpus grande. Duecento e' il numero che il
#: piano nomina: «funziona con dieci file e non con duecento».
GRANDE = 200


def _riempi(store: MemoryStore, quanti_rumori: int) -> None:
    """Le dieci note vere, piu' `quanti_rumori` distrattori sintetici.

    ⚠️ I distrattori sono **rumore dichiarato**, non contenuto: il loro
    mestiere e' occupare posti nell'ordine alfabetico e far scattare il
    `break` di `cerca()` prima che arrivi la nota giusta. Sono nominati
    `nota-000`… apposta, per stare **prima** di `stampanti` in ordine
    alfabetico: e' il caso peggiore, ed e' quello che si vuole misurare.
    """
    for nome, testo in NOTE.items():
        store.scrivi_topic(nome, testo)
    for i in range(quanti_rumori):
        store.scrivi_topic(
            f"nota-{i:03d}",
            f"Appunto numero {i} di una sessione senza niente di notevole. "
            f"Argomenti generici, nessuna preferenza, nessuna decisione.")


def _rango(store: MemoryStore, domanda: str, atteso: str, k: int) -> bool:
    """Se il topic atteso compare fra i primi `k` risultati."""
    trovati = store.cerca(domanda, limite=k)
    return any(t.nome == atteso for t in trovati)


#: Una stringa che compare **in una nota vera e in tutti i distrattori**, e la
#: cui nota sta DOPO i distrattori in ordine alfabetico (`stampanti` > `nota-`).
#: E' li' che il `break` al primo `limite` di `cerca()` morde.
#:
#: ⚠️ **«una» e' una query degenere, e lo si dice.** Nessuno cerchera' mai
#: «una». E' scelta perche' isola il MECCANISMO in modo inequivocabile: la
#: stessa cosa capita a qualunque parola ordinaria man mano che le sessioni si
#: accumulano — i distrattori qui sono note di sessione, cioe' esattamente cio'
#: che `topics/` conterra' fra un anno. La query e' artificiale; l'affollamento
#: che dimostra non lo e'.
AFFOLLATA = ("una", "stampanti")


def _misura(store: MemoryStore) -> dict:
    fuori: dict = {"recall": {}, "rifiuto_corretto": None, "affollamento": None}
    for forma in ("letterale", "parafrasi"):
        gruppo = [d for d in DOMANDE if d[2] == forma]
        for k in (1, 3, 5):
            colpi = sum(1 for q, atteso, _ in gruppo if _rango(store, q, atteso, k))
            fuori["recall"].setdefault(forma, {})[f"@{k}"] = round(
                colpi / len(gruppo), 3)
    taciuti = sum(1 for q in ASSENTI if not store.cerca(q, limite=5))
    fuori["rifiuto_corretto"] = round(taciuti / len(ASSENTI), 3)
    domanda, atteso = AFFOLLATA
    fuori["affollamento"] = _rango(store, domanda, atteso, 5)
    return fuori


# ── il banco ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def misure(tmp_path_factory) -> dict:
    """Le due misure, a dieci topic e a duecentodieci."""
    fuori = {}
    for etichetta, rumore in (("dieci", 0), ("duecento", GRANDE)):
        d = tmp_path_factory.mktemp(f"memoria-{etichetta}")
        s = MemoryStore(d)
        _riempi(s, rumore)
        fuori[etichetta] = _misura(s)
        fuori[etichetta]["topic_totali"] = len(s.elenca_topic())
    return fuori


class TestIlBancoEOnesto:
    """Le regole che impediscono di barare senza accorgersene."""

    def test_le_parafrasi_sono_DAVVERO_parafrasi(self) -> None:
        """Nessuna parola di contenuto in comune con la nota da trovare.

        ⚠️ **E' la riga che tiene in piedi tutto il banco.** Le domande le ho
        scritte io, e chi scrive le domande puo' scriverle facili: basta
        lasciare una parola in comune e la ricerca per sottostringa la trova.
        Qui la condizione si verifica invece di dichiararla.
        """
        for domanda, atteso, forma in DOMANDE:
            if forma != "parafrasi":
                continue
            comuni = parole(domanda) & parole(NOTE[atteso])
            assert not comuni, (
                f"«{domanda}» condivide {comuni} con la nota «{atteso}»: non e' "
                "una parafrasi, e la ricerca per sottostringa la trova per il "
                "motivo sbagliato"
            )

    def test_le_letterali_sono_DAVVERO_letterali(self) -> None:
        """Il gruppo di riferimento: il loro esito e' prevedibile a priori, e
        serve a distinguere «la ricerca non funziona» da «il banco e' rotto»."""
        for domanda, atteso, forma in DOMANDE:
            if forma == "letterale":
                assert domanda.lower() in NOTE[atteso].lower(), domanda

    def test_le_assenti_non_sono_in_nessuna_nota(self) -> None:
        for q in ASSENTI:
            for nome, testo in NOTE.items():
                assert q.lower() not in testo.lower(), (nome, q)

    def test_venti_domande_e_dieci_note(self) -> None:
        """Il piano dice venti. Se qualcuno ne toglie una, il numero cambia
        senza che nessuno se ne accorga."""
        assert len(DOMANDE) == 20 and len(NOTE) == 10 and len(ASSENTI) == 5


class TestIlTermometro:
    """⚠️ **Questi test NON impongono una soglia**, e non e' una dimenticanza.

    Il criterio della fetta dice: «non serve che il numero sia buono, serve che
    esista, perche' oggi non c'e' niente da confrontare». Una soglia scelta
    oggi sarebbe un numero inventato che domani qualcuno prenderebbe per una
    misura — lo stesso difetto che `STATO-DEI-PIANI` documenta sull'entropia
    2,40, che «fa il cancello e l'obiettivo insieme, cioe' non misura».

    Qui si pinna che il banco **funzioni** e che il numero **esista**. La
    soglia si mette al secondo giro, quando ci sara' un valore precedente
    contro cui difenderla.
    """

    def test_il_banco_produce_i_numeri(self, misure: dict) -> None:
        for etichetta in ("dieci", "duecento"):
            m = misure[etichetta]
            assert set(m["recall"]) == {"letterale", "parafrasi"}
            assert all(0.0 <= v <= 1.0
                       for f in m["recall"].values() for v in f.values())
            assert 0.0 <= m["rifiuto_corretto"] <= 1.0
            assert isinstance(m["affollamento"], bool)

    def test_le_letterali_le_trova_a_dieci_topic(self, misure: dict) -> None:
        """Il riferimento: se anche queste cadono, e' rotto il banco, non la
        ricerca."""
        assert misure["dieci"]["recall"]["letterale"]["@5"] == 1.0

    def test_il_rumore_non_MIGLIORA_il_recupero(self, misure: dict) -> None:
        """⚠️ **Questo test si chiamava `test_la_DEGRADAZIONE_e_misurata`, e
        prometteva piu' di quanto guardasse.** Misurato: le letterali fanno
        **1,0 a dieci topic e 1,0 a duecentodieci**, quindi `duecento <= dieci`
        passava con `1.0 <= 1.0` — cioe' era verde per assenza di degradazione,
        non per averla misurata. Un test il cui nome dice «misura X» e il cui
        corpo controlla «X non peggiora» e' il tipo di verde che si crede.

        La degradazione da scala la misura `test_l_AFFOLLAMENTO`, qui sotto.
        Questa riga resta come guardia di sanita': se aggiungere duecento note
        di rumore MIGLIORASSE il recupero, sarebbe rotto il banco.
        """
        for forma in ("letterale", "parafrasi"):
            dieci = misure["dieci"]["recall"][forma]["@5"]
            duecento = misure["duecento"]["recall"][forma]["@5"]
            assert duecento <= dieci, forma

    def test_l_AFFOLLAMENTO_e_la_vera_soglia_di_scala(self, misure: dict) -> None:
        """**Dove `cerca()` smette davvero di funzionare quando cresce.**

        Non e' il numero di file: una ricerca per sottostringa o trova o non
        trova, e duecento note di rumore che non contengono la parola cercata
        non cambiano niente. E' il **`break` al primo `limite`**, in ordine
        alfabetico: appena piu' di cinque note contengono la stringa, vincono le
        prime cinque per nome, e la nota giusta puo' non esserci.

        Con dieci topic la parola «nessun» sta solo nella nota `cucina`. Con
        duecentodieci sta in tutti i distrattori `nota-NNN`, che in ordine
        alfabetico vengono prima — e `cucina` sparisce. **E' questo il momento
        in cui la memoria smette di rispondere**, e adesso ha un numero.
        """
        assert misure["dieci"]["affollamento"] is True, (
            "a dieci topic la nota giusta si trova: se no, e' rotto il banco"
        )
        assert misure["duecento"]["affollamento"] is False, (
            "a duecentodieci la nota giusta NON si trova piu': se la trovasse, "
            "`cerca()` sarebbe migliore di quanto credo e questo banco andrebbe "
            "rifatto — che sarebbe una buona notizia, ma va guardata"
        )

    def test_il_rifiuto_corretto_e_misurato(self, misure: dict) -> None:
        """Un recupero che risponde sempre qualcosa e' peggio di uno che tace:
        chi lo usa non puo' distinguere «non lo so» da una ricostruzione."""
        assert misure["dieci"]["rifiuto_corretto"] is not None

    def test_il_numero_finisce_nel_file_di_accettazione(self, misure: dict) -> None:
        """Il criterio della fetta: «il numero finisce in un file di
        accettazione **con la data**».

        ⚠️ Il file lo scrive `scripts/termometro.py`, non questo test: un test
        che riscrive la propria evidenza ogni volta che gira non e' evidenza.
        Qui si controlla che ci sia, e che dica di che giorno e'.
        """
        if not ESITO.exists():
            pytest.skip("TERMOMETRO.json non c'e': `uv run python "
                        "scripts/termometro.py`")
        d = json.loads(ESITO.read_text(encoding="utf-8"))
        assert d.get("data"), "una misura senza data non si confronta con niente"
        assert "memoria" in d
        assert set(d["memoria"]) >= {"dieci", "duecento"}
