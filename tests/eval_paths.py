"""EVAL — nessun percorso fuori radice passa, nemmeno con `..`.

E' il criterio duro di §22 Fase 2 e la difesa piu' importante del progetto:
tutto cio' che sta a valle — cestino, conferma umana, isolamento — presuppone
che un percorso non consentito non arrivi mai fin li'.

**Un corpus, non tre casi.** §22 prescrive che gli eval girino all'INIZIO di
ogni fase: sono l'unico modo per accorgersi che una sessione ha rotto qualcosa
che funzionava tre fasi fa. Un corpus di tre esempi non se ne accorge.

Ogni voce dichiara l'esito atteso e **il perche'**, cosi' che chi un giorno
vedra' fallire una riga sappia se sta guardando una regressione o una regola
che e' cambiata di proposito.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from core.paths_policy import PathFuoriRadice, e_una_radice, risolvi_sotto_radici

AMMESSO, RIFIUTATO = "ammesso", "rifiutato"


@pytest.fixture
def terreno(tmp_path: Path):
    """Una radice consentita, con dentro le trappole abituali."""
    radice = (tmp_path / "consentita").resolve()
    (radice / "sotto" / "ancora").mkdir(parents=True)
    (radice / "file.txt").write_text("x")

    esterna = (tmp_path / "esterna").resolve()
    esterna.mkdir()
    (esterna / "segreto.txt").write_text("non deve essere raggiungibile")

    # Le tre trappole che contano.
    (radice / "link_fuori").symlink_to(esterna)              # link diretto fuori
    (radice / "sotto" / "link_su").symlink_to(radice.parent)  # link al genitore
    (radice / "link_dentro").symlink_to(radice / "sotto")     # link innocuo

    return {"radice": radice, "esterna": esterna, "radici": [radice]}


def _casi(t) -> list[tuple[str, object, str, str]]:
    r, esterna = t["radice"], t["esterna"]
    return [
        # (descrizione, percorso, atteso, perche')
        ("percorso normale",            r / "file.txt", AMMESSO,
         "sta dentro la radice"),
        ("sottodirectory profonda",     r / "sotto" / "ancora", AMMESSO,
         "sta dentro la radice"),
        ("la radice stessa",            r, AMMESSO,
         "una radice sta dentro se stessa; il divieto di distruggerla e' del tool"),
        ("file non ancora esistente",   r / "nuovo.txt", AMMESSO,
         "create_file deve poter nominare cio' che non c'e' ancora"),
        ("link che resta dentro",       r / "link_dentro" / "ancora", AMMESSO,
         "risolve dentro la radice: e' lecito"),

        (".. singolo",                  r / ".." / "esterna", RIFIUTATO,
         "resolve() lo appiattisce e cade fuori"),
        (".. ripetuti",                 r / ".." / ".." / ".." / "etc", RIFIUTATO,
         "risalire fino alla radice del filesystem"),
        (".. dopo un segmento inesistente", r / "nonesiste" / ".." / ".." / "esterna",
         RIFIUTATO,
         "resolve() risolve lessicalmente cio' che non esiste: verificato sul campo"),
        (".. in mezzo al percorso",     r / "sotto" / ".." / ".." / "esterna", RIFIUTATO,
         "stesso appiattimento, nascosto meglio"),

        ("symlink verso l'esterno",     r / "link_fuori" / "segreto.txt", RIFIUTATO,
         "il link e' dentro, il bersaglio no: conta il bersaglio"),
        ("symlink al genitore",         r / "sotto" / "link_su" / "esterna", RIFIUTATO,
         "un link a meta' percorso e' il caso che un controllo lessicale manca"),

        ("percorso assoluto esterno",   Path("/etc/passwd"), RIFIUTATO,
         "nessuna relazione con le radici"),
        ("percorso assoluto di sistema", Path("/"), RIFIUTATO,
         "la radice del filesystem non e' una radice consentita"),
        ("tilde di un altro utente",    "~root/.ssh/id_rsa", RIFIUTATO,
         "expanduser risolve a /root: verificato sul campo"),
        ("stringa vuota",               "", RIFIUTATO,
         "risolve alla working directory, che non e' una radice"),
        ("solo punto",                  ".", RIFIUTATO,
         "come sopra"),
        ("byte NUL",                    "dentro\x00/etc/passwd", RIFIUTATO,
         "resolve() alza ValueError: cio' che non si puo' verificare si rifiuta"),

        ("prefisso che somiglia alla radice", Path(str(r) + "-altro" ) / "x", RIFIUTATO,
         "«/tmp/x/consentita-altro» NON e' sotto «/tmp/x/consentita»: "
         "il confronto e' per componenti, non per stringa"),
        ("esterna con lo stesso nome",  esterna / "segreto.txt", RIFIUTATO,
         "fuori e' fuori"),
    ]


class TestCorpus:
    def test_ogni_caso_si_comporta_come_dichiarato(self, terreno) -> None:
        fallimenti = []
        for descrizione, percorso, atteso, perche in _casi(terreno):
            try:
                risolvi_sotto_radici(percorso, terreno["radici"])
                ottenuto = AMMESSO
            except PathFuoriRadice:
                ottenuto = RIFIUTATO
            if ottenuto != atteso:
                fallimenti.append(
                    f"  {descrizione}: atteso {atteso}, ottenuto {ottenuto}\n"
                    f"      percorso: {percorso}\n"
                    f"      perche':  {perche}"
                )
        assert not fallimenti, "casi non conformi:\n" + "\n".join(fallimenti)

    def test_il_corpus_copre_entrambi_gli_esiti(self, terreno) -> None:
        """Un corpus di soli rifiuti passerebbe anche con una regola che
        rifiuta tutto, e non misurerebbe nulla."""
        attesi = [a for _, _, a, _ in _casi(terreno)]
        assert attesi.count(AMMESSO) >= 4 and attesi.count(RIFIUTATO) >= 10


class TestProprietaDellaRegola:
    def test_le_radici_vengono_risolte(self, tmp_path: Path) -> None:
        """Il difetto di §6.1. Con una radice che e' un symlink, un controllo
        che non risolve le radici rifiuterebbe TUTTO — e su una macchina con
        radici reali il difetto resterebbe invisibile."""
        vera = (tmp_path / "vera").resolve()
        vera.mkdir()
        (vera / "f.txt").write_text("x")
        link_radice = tmp_path / "radice_link"
        link_radice.symlink_to(vera)

        assert risolvi_sotto_radici(link_radice / "f.txt", [link_radice]) == vera / "f.txt"

    def test_nessuna_radice_configurata_rifiuta_tutto(self, tmp_path: Path) -> None:
        """Una configurazione vuota non deve significare "tutto permesso"."""
        with pytest.raises(PathFuoriRadice, match="nessuna radice"):
            risolvi_sotto_radici(tmp_path / "x", [])

    def test_il_messaggio_nomina_il_percorso_risolto(self, terreno) -> None:
        """§6.2 vuole che l'utente veda il path RISOLTO. Vale anche per gli
        errori: dire «.. rifiutato» senza dire dove portava non aiuta."""
        with pytest.raises(PathFuoriRadice) as e:
            risolvi_sotto_radici(terreno["radice"] / ".." / "esterna", terreno["radici"])
        assert str(terreno["esterna"]) in str(e.value)


class TestNormalizzazioneUnicode:
    def test_nfc_e_nfd_sono_percorsi_diversi(self, terreno) -> None:
        """Su Linux i nomi di file sono byte: «café» in NFC e in NFD sono due
        file distinti. Non e' un varco — entrambi restano dentro la radice —
        ma e' registrato perche' un giorno qualcuno confrontera' due nomi che
        sullo schermo sembrano identici e non capira' perche' differiscono.
        """
        r = terreno["radice"]
        nfc = unicodedata.normalize("NFC", "café.txt")
        nfd = unicodedata.normalize("NFD", "café.txt")
        assert nfc != nfd
        a = risolvi_sotto_radici(r / nfc, terreno["radici"])
        b = risolvi_sotto_radici(r / nfd, terreno["radici"])
        assert a != b, "il sistema li tratterebbe come lo stesso file"


class TestRadiciComeBersaglio:
    def test_riconosce_una_radice(self, terreno) -> None:
        assert e_una_radice(terreno["radice"], terreno["radici"])

    def test_una_sottodirectory_non_e_una_radice(self, terreno) -> None:
        assert not e_una_radice(terreno["radice"] / "sotto", terreno["radici"])

    def test_percorso_illeggibile_non_e_una_radice(self, terreno) -> None:
        assert not e_una_radice("x\x00y", terreno["radici"])
