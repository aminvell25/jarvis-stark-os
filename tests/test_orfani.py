"""Lo scanner degli orfani non deve sparire una seconda volta.

`docs/SPEC.md` riga 15 cita 487 definizioni e 22 orfane. Quel numero non e'
piu' verificabile: lo script che l'ha prodotto e' stato eseguito e buttato,
e nessuno puo' piu' dire se la traiettoria 22 → 11 → 7 sia mai stata vera.

Questo file esiste perche' non succeda di nuovo. Confronta cio' che lo scanner
trova OGGI con la baseline in `docs/acceptance/ORFANI.json`, e diventa rosso
quando compare un orfano SOSPETTO che la baseline non conosce.

⚠️ **Il confronto e' sui sospetti, non su tutti gli orfani**, e non e' una
comodita': un orfano benigno che smette di esserlo — perde l'ultimo chiamante
nel proprio modulo e passa a `da_esaminare` — ha la stessa chiave di prima.
Confrontando le chiavi di TUTTI gli orfani quel peggioramento sarebbe verde.
Confrontando i sospetti diventa un sospetto nuovo, e rosso.

⚠️ **La riga non entra nel confronto.** Un commento aggiunto sopra una
definizione la sposta, e una baseline che diventa rossa per un commento e' una
baseline che si rigenera senza guardarla — cioe' nessuna baseline.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.orfani import (
    CATEGORIE,
    DICHIARATI,
    RADICE,
    Dichiarato,
    DichiarazioneScaduta,
    Rapporto,
    come_json,
    definizioni,
    scansiona,
)

BASELINE = RADICE / "docs" / "acceptance" / "ORFANI.json"

#: Il tetto dichiarato per la scansione. Se lo si supera si riduce il LAVORO,
#: mai il rigore: il rimedio e' leggere il disco una volta sola, non guardare
#: meno file.
TETTO_S = 5.0


@pytest.fixture(scope="module")
def rapporto() -> Rapporto:
    """Una scansione sola per tutto il file: e' pura, e costa lettura di disco."""
    return scansiona(RADICE)


@pytest.fixture(scope="module")
def baseline() -> dict:
    assert BASELINE.exists(), (
        f"{BASELINE} non c'e'. Si rigenera con lo scanner stesso:\n"
        f"    uv run python scripts/orfani.py --json > {BASELINE}"
    )
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def _chiavi_sospette(elenco: list[dict]) -> set[tuple[str, str | None, str]]:
    """Chi non e' spiegato ne' da una categoria ne' da una firma.

    ⚠️ `benigno` NON diventa vero per un dichiarato: resta la proprieta' del
    codice che era, e il filtro tiene le due cose separate. Chi legge la
    baseline deve poter vedere che `Governor.attivi` e' ancora `solo_test`.
    """
    return {(o["modulo"], o["classe"], o["nome"]) for o in elenco
            if not o["benigno"] and not o.get("dichiarato")}


def _scrivi(radice: Path, rel: str, testo: str) -> None:
    p = radice / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(testo, encoding="utf-8")


class TestLaScansione:
    """Che lo scanner misuri davvero cio' che dice di misurare."""

    def test_trova_le_definizioni_pubbliche(self, rapporto: Rapporto) -> None:
        """Il core ne ha centinaia: un conteggio a zero sarebbe uno scanner
        rotto che dichiara zero orfani, cioe' il guasto peggiore possibile."""
        assert rapporto.definizioni > 400, (
            f"solo {rapporto.definizioni} definizioni: lo scanner non sta "
            f"leggendo core/"
        )

    def test_le_private_non_si_contano(self) -> None:
        from scripts.orfani import _alberi, _sorgenti

        trovate = definizioni(_alberi(_sorgenti(RADICE, "core")), RADICE)
        privati = [d for d in trovate if d.nome.startswith("_")]
        assert not privati, f"nomi privati nel conteggio: {privati[:5]}"

    def test_ogni_orfano_ha_una_categoria_e_una_ragione(
        self, rapporto: Rapporto
    ) -> None:
        """«Ogni orfano finisce in una categoria, con la ragione»: senza
        ragione la categoria e' un'etichetta, e un'etichetta non si discute."""
        for o in rapporto.orfani:
            assert o.categoria in CATEGORIE, f"categoria ignota: {o.categoria}"
            assert o.benigno is CATEGORIE[o.categoria]
            assert len(o.ragione) > 10, f"{o.nome}: ragione muta"

    def test_la_scansione_sta_dentro_il_tetto(self) -> None:
        inizio = time.perf_counter()
        scansiona(RADICE)
        durata = time.perf_counter() - inizio
        assert durata < TETTO_S, f"scansione in {durata:.2f}s, tetto {TETTO_S}s"


class TestLaBaseline:
    """Il confronto con `docs/acceptance/ORFANI.json`."""

    def test_nessun_orfano_nuovo(self, rapporto: Rapporto, baseline: dict) -> None:
        """Il test che vale il file.

        Rosso quando compare un sospetto che la baseline non conosce: una
        funzione pubblica scritta in `core/` e mai chiamata, oppure un orfano
        benigno che ha perso l'ultimo chiamante.
        """
        noti = _chiavi_sospette(baseline["elenco"])
        oggi = _chiavi_sospette([
            {"modulo": o.modulo, "classe": o.classe, "nome": o.nome,
             "benigno": o.benigno, "dichiarato": o.dichiarato}
            for o in rapporto.orfani
        ])
        nuovi = oggi - noti
        dettaglio = "\n".join(
            f"  {o.modulo}:{o.riga}  "
            f"{o.classe + '.' if o.classe else ''}{o.nome}  "
            f"[{o.categoria}] {o.ragione}"
            for o in sorted(rapporto.orfani, key=lambda o: o.modulo)
            if (o.modulo, o.classe, o.nome) in nuovi
        )
        assert not nuovi, (
            f"{len(nuovi)} orfani NUOVI rispetto alla baseline:\n{dettaglio}\n\n"
            "Un pezzo scritto e mai congiunto, oppure un chiamante sparito. "
            "Se e' voluto, si collega; se e' un falso positivo noto, gli si "
            "da' una categoria in scripts/orfani.py. La baseline si rigenera "
            "solo dopo aver guardato le righe qui sopra:\n"
            f"    uv run python scripts/orfani.py --json > {BASELINE}"
        )

    def test_la_baseline_non_DERIVA_in_silenzio(
        self, rapporto: Rapporto, baseline: dict
    ) -> None:
        """⚠️ Il test qui sopra e' ASIMMETRICO, e la deriva l'ha sfruttata.

        `nuovi = oggi - noti` diventa rosso solo per un SOSPETTO nuovo. Un
        orfano BENIGNO che compare — una funzione pubblica nuova chiamata solo
        dentro il proprio modulo — non lo tocca, e i conteggi della baseline si
        allontanano da quelli veri senza che niente lo dica.

        E' successo: il 29 agosto la baseline diceva `529 definizioni, 169
        orfani` mentre la scansione viva ne contava `530 / 170`. La differenza
        era `ClaudeT1.stderr_del_morto`, nata nel commit dello stderr, e per un
        commit intero il file di riferimento ha detto un numero falso — mentre
        `docs/SPEC.md` cita quei conteggi come misura.

        Una baseline che non e' piu' la misura di oggi non e' una baseline:
        e' un file che qualcuno rigenerera' senza guardarlo.
        """
        oggi = come_json(rapporto)
        for campo in ("definizioni", "orfani_totali", "sospetti", "dichiarati"):
            assert baseline[campo] == oggi[campo], (
                f"la baseline dice {campo}={baseline[campo]}, la scansione viva "
                f"{oggi[campo]}.\n\n"
                "Non e' per forza un difetto — una funzione pubblica nuova usata "
                "solo in casa e' un orfano benigno legittimo. Ma il file di "
                "riferimento deve dire la misura di OGGI, e si rigenera dopo "
                "aver guardato che cosa e' cambiato:\n"
                "    uv run python scripts/orfani.py --tutti\n"
                f"    uv run python scripts/orfani.py --json > {BASELINE}"
            )

    def test_la_baseline_ha_la_forma_dello_scanner(
        self, rapporto: Rapporto, baseline: dict
    ) -> None:
        """La baseline la genera lo scanner stesso: se la forma diverge,
        qualcuno l'ha scritta a mano, e una baseline scritta a mano misura
        cio' che voleva chi l'ha scritta."""
        oggi = come_json(rapporto)
        assert set(baseline) == set(oggi)
        assert set(baseline["elenco"][0]) == set(oggi["elenco"][0])
        assert baseline["sospetti"] == len(_chiavi_sospette(baseline["elenco"]))

    def test_i_sospetti_noti_restano_dichiarati(self, baseline: dict) -> None:
        """La baseline non deve poter diventare vuota per distrazione: se
        qualcuno la rigenera su un albero rotto — `core/` non leggibile, zero
        definizioni — l'elenco a zero renderebbe verde qualunque cosa."""
        assert baseline["definizioni"] > 400
        assert baseline["orfani_totali"] >= baseline["sospetti"]


class TestLeBocciature:
    """Che ogni regola sia provata su un albero costruito apposta.

    Non si perturba `core/` per verificarle: `scansiona()` prende la radice per
    argomento, e un albero finto in `tmp_path` prova la stessa regola senza
    che altri test vedano un file comparire e sparire.
    """

    def test_una_pubblica_mai_chiamata_e_sospetta(self, tmp_path: Path) -> None:
        """Il requisito centrale: una funzione pubblica in `core/` che nessuno
        chiama deve far diventare rosso questo file."""
        _scrivi(tmp_path, "core/solo.py", "def mai_chiamata() -> int:\n    return 1\n")
        r = scansiona(tmp_path)
        sospetti = {o.nome: o.categoria for o in r.sospetti}
        assert sospetti == {"mai_chiamata": "da_esaminare"}

    def test_chiamata_da_un_altro_modulo_non_e_orfana(self, tmp_path: Path) -> None:
        _scrivi(tmp_path, "core/a.py", "def usata() -> int:\n    return 1\n")
        _scrivi(tmp_path, "core/b.py",
                "from core.a import usata\n\n\ndef altro() -> int:\n    return usata()\n")
        r = scansiona(tmp_path)
        assert "usata" not in {o.nome for o in r.orfani}

    def test_un_import_non_e_un_richiamo(self, tmp_path: Path) -> None:
        """La ri-esportazione non salva nessuno.

        Se `from .a import usata` contasse, ogni pacchetto potrebbe nascondere
        i propri orfani dietro il proprio `__init__.py` — che e' il posto dove
        si nascondono meglio, perche' nessuno lo legge.
        """
        _scrivi(tmp_path, "core/a.py", "def usata() -> int:\n    return 1\n")
        _scrivi(tmp_path, "core/__init__.py",
                'from core.a import usata\n\n__all__ = ["usata"]\n')
        r = scansiona(tmp_path)
        assert {o.nome: o.categoria for o in r.sospetti} == {"usata": "da_esaminare"}

    def test_chiamata_solo_dai_test_resta_sospetta(self, tmp_path: Path) -> None:
        """§5.29 e' nata da pezzi che avevano solo test. Un test non e' un
        chiamante: e' il motivo per cui l'orfano non si vedeva."""
        _scrivi(tmp_path, "core/a.py", "def provata() -> int:\n    return 1\n")
        _scrivi(tmp_path, "tests/test_a.py",
                "from core.a import provata\n\n\ndef test_x() -> None:\n"
                "    assert provata() == 1\n")
        r = scansiona(tmp_path)
        (o,) = r.sospetti
        assert (o.nome, o.categoria) == ("provata", "solo_test")
        assert "tests/test_a.py" in o.ragione

    def test_chiamata_per_attributo_di_modulo_conta(self, tmp_path: Path) -> None:
        """`R.pianifica(...)` e' un richiamo come un altro: lo scanner conta
        anche gli `Attribute`, o classificherebbe come orfano chiunque venga
        chiamato attraverso l'alias di un modulo."""
        _scrivi(tmp_path, "core/a.py", "def pianifica() -> int:\n    return 1\n")
        _scrivi(tmp_path, "core/b.py",
                "from core import a as R\n\n\ndef usa() -> int:\n"
                "    return R.pianifica()\n")
        r = scansiona(tmp_path)
        assert "pianifica" not in {o.nome for o in r.orfani}

    def test_usato_solo_nel_modulo_e_benigno(self, tmp_path: Path) -> None:
        _scrivi(tmp_path, "core/a.py",
                "def aiuto() -> int:\n    return 1\n\n\n"
                "def porta() -> int:\n    return aiuto()\n")
        r = scansiona(tmp_path)
        cat = {o.nome: o.categoria for o in r.orfani}
        assert cat["aiuto"] == "usato_solo_nel_modulo"
        assert [o.nome for o in r.sospetti] == ["porta"]

    def test_il_protocollo_non_e_sospetto(self, tmp_path: Path) -> None:
        _scrivi(tmp_path, "core/base.py",
                "from typing import Protocol\n\n\nclass Sorgente(Protocol):\n"
                "    def leggi(self) -> bytes: ...\n")
        r = scansiona(tmp_path)
        assert not r.sospetti
        assert {o.nome: o.categoria for o in r.orfani} == {
            "Sorgente": "protocollo", "leggi": "protocollo"}

    def test_l_implementazione_di_un_protocollo_non_e_sospetta(
        self, tmp_path: Path
    ) -> None:
        _scrivi(tmp_path, "core/base.py",
                "from typing import Protocol\n\n\nclass Sorgente(Protocol):\n"
                "    async def aclose(self) -> None: ...\n")
        _scrivi(tmp_path, "core/vera.py",
                "class SorgenteVera:\n    async def aclose(self) -> None:\n"
                "        return None\n")
        r = scansiona(tmp_path)
        cat = {(o.classe, o.nome): o.categoria for o in r.orfani}
        assert cat[("SorgenteVera", "aclose")] == "implementazione_di_protocollo"

    def test_l_eccezione_dichiarata_non_e_sospetta(self, tmp_path: Path) -> None:
        """E la catena si risale: una sottoclasse di una nostra eccezione e'
        un'eccezione, o basterebbe un livello di ereditarieta' per farla
        ricomparire fra i sospetti."""
        _scrivi(tmp_path, "core/errori.py",
                "class ToolIgnoto(LookupError):\n    pass\n\n\n"
                "class ToolIgnotoDavvero(ToolIgnoto):\n    pass\n")
        r = scansiona(tmp_path)
        assert not r.sospetti
        cat = {o.nome: o.categoria for o in r.orfani}
        assert cat["ToolIgnotoDavvero"] == "eccezione"
        # `ToolIgnoto` ha un chiamante vero — la sottoclasse, nello stesso
        # file — e la spiegazione piu' forte vince sulla piu' generica.
        assert cat["ToolIgnoto"] == "usato_solo_nel_modulo"

    def test_il_callback_di_libreria_vuole_la_base_esterna(
        self, tmp_path: Path
    ) -> None:
        """L'allowlist non basta da sola: `on_any_event` e' benigno perche' una
        base esterna lo chiama. Lo stesso nome in una classe nostra, che
        nessuna libreria conosce, resta un sospetto."""
        _scrivi(tmp_path, "core/veri.py",
                "from watchdog.events import FileSystemEventHandler\n\n\n"
                "class Osserva(FileSystemEventHandler):\n"
                "    def on_any_event(self, evento) -> None:\n        return None\n")
        _scrivi(tmp_path, "core/finti.py",
                "class Nostro:\n    def on_any_event(self, evento) -> None:\n"
                "        return None\n")
        r = scansiona(tmp_path)
        cat = {(o.classe, o.nome): o.categoria for o in r.orfani}
        assert cat[("Osserva", "on_any_event")] == "callback_libreria"
        assert cat[("Nostro", "on_any_event")] == "da_esaminare"

    def test_una_def_annidata_in_una_funzione_non_conta(self, tmp_path: Path) -> None:
        """Una funzione dentro una funzione non e' raggiungibile da fuori:
        contarla vorrebbe dire dichiarare orfano ogni chiusura del core."""
        _scrivi(tmp_path, "core/a.py",
                "def fuori() -> int:\n    def dentro() -> int:\n        return 1\n"
                "    return dentro()\n")
        r = scansiona(tmp_path)
        assert [o.nome for o in r.orfani] == ["fuori"]

    def test_una_def_sotto_if_o_try_conta(self, tmp_path: Path) -> None:
        """`if TYPE_CHECKING:` e `try: ... except ImportError:` di livello
        modulo definiscono nomi veri, visibili da fuori."""
        _scrivi(tmp_path, "core/a.py",
                "import sys\n\nif sys.platform == 'linux':\n"
                "    def solo_linux() -> int:\n        return 1\n")
        r = scansiona(tmp_path)
        assert [o.nome for o in r.orfani] == ["solo_linux"]


class TestIlCli:
    """Che il punto d'ingresso vero funzioni, non solo le funzioni interne."""

    def test_json_dice_quello_che_dice_la_scansione(self, rapporto: Rapporto) -> None:
        esito = subprocess.run(
            [sys.executable, str(RADICE / "scripts" / "orfani.py"), "--json"],
            capture_output=True, text=True, timeout=TETTO_S * 2, check=True,
        )
        d = json.loads(esito.stdout)
        assert d["definizioni"] == rapporto.definizioni
        assert d["sospetti"] == len(rapporto.sospetti)

    def test_il_riepilogo_e_leggibile(self) -> None:
        esito = subprocess.run(
            [sys.executable, str(RADICE / "scripts" / "orfani.py")],
            capture_output=True, text=True, timeout=TETTO_S * 2, check=True,
        )
        assert "definizioni pubbliche" in esito.stdout
        for categoria in CATEGORIE:
            if categoria in esito.stdout:
                break
        else:
            pytest.fail("il riepilogo non nomina nessuna categoria")


class TestIDichiarati:
    """La terza forma di allowlist: non una categoria, una firma.

    Le categorie sono proprietà del codice e si deducono guardandolo.
    `DICHIARATI` è un elenco di **decisioni**, e una decisione senza la sua
    ragione scritta è indistinguibile da una svista. Senza un elenco così,
    tre orfani buoni vengono rianalizzati a ogni scansione — e il rumore è il
    posto dove si nasconde l'orfano vero: `gestures.emetti` era «l'unica uscita
    delle gesture verso il resto del sistema» e stava in mezzo a diciannove
    falsi positivi.
    """

    def test_una_voce_SENZA_ragione_non_si_costruisce(self) -> None:
        """La struttura lo impedisce, non lo raccomanda: un elenco che si
        potesse allungare con una riga muta sarebbe il nascondiglio."""
        with pytest.raises(ValueError, match="non e' una ragione"):
            Dichiarato(modulo="core/a.py", classe=None, nome="x", perche="ok")

    def test_e_nemmeno_con_una_ragione_VUOTA(self) -> None:
        with pytest.raises(ValueError, match="non e' una ragione"):
            Dichiarato(modulo="core/a.py", classe=None, nome="x", perche="   ")

    def test_ogni_ragione_dichiarata_e_LEGGIBILE(self) -> None:
        for d in DICHIARATI:
            assert len(d.perche.strip()) >= Dichiarato.MINIMO
            assert d.perche.strip()[0].isupper(), (
                f"{d.nome}: una ragione comincia come una frase, perche' "
                "qualcuno dovra' leggerla fra tre mesi"
            )

    def test_un_dichiarato_NON_e_un_sospetto_ma_resta_nella_sua_categoria(
            self, rapporto: Rapporto) -> None:
        """⚠️ `benigno` non cambia. Chi legge deve poter vedere che
        `Governor.attivi` è ancora `solo_test`, e che a toglierlo dai sospetti
        è stata **una persona** — non lo strumento."""
        firmati = {(o.modulo, o.classe, o.nome) for o in rapporto.dichiarati}
        assert firmati == {d.chiave for d in DICHIARATI}
        for o in rapporto.dichiarati:
            assert o.benigno is False, (
                "un dichiarato marcato benigno confonde «lo strumento lo "
                "spiega» con «qualcuno ha deciso»"
            )
            assert (o.modulo, o.classe, o.nome) not in {
                (s.modulo, s.classe, s.nome) for s in rapporto.sospetti}

    def test_una_dichiarazione_SCADUTA_fa_cadere_la_scansione(
            self, tmp_path: Path) -> None:
        """⚠️ Il vincolo che tiene onesto l'elenco.

        Un'allowlist che sopravvive alla sparizione del proprio motivo diventa
        una lista di bugie in tre mesi. Qui il nome dichiarato **ha** un
        chiamante: la ragione scritta accanto non è più vera, e la scansione
        deve fermarsi invece di continuare a coprirlo.
        """
        _scrivi(tmp_path, "core/a.py", "def collegata() -> int:\n    return 1\n")
        _scrivi(tmp_path, "core/b.py",
                "from core.a import collegata\n\n\ndef usa() -> int:\n"
                "    return collegata()\n")
        firma = Dichiarato(
            modulo="core/a.py", classe=None, nome="collegata",
            perche="Nessuno la chiama, e va bene cosi': e' un'API per le prove "
                   "e forzarle un chiamante sarebbe inventare una funzione.")
        with pytest.raises(DichiarazioneScaduta, match="collegata"):
            scansiona(tmp_path, dichiarati=(firma,))

    def test_e_cade_anche_se_il_nome_e_SPARITO(
            self, tmp_path: Path) -> None:
        """L'altra metà: un nome cancellato lascerebbe una riga che spiega
        qualcosa che non c'è."""
        _scrivi(tmp_path, "core/a.py", "def altra() -> int:\n    return 1\n")
        firma = Dichiarato(
            modulo="core/a.py", classe=None, nome="cancellata",
            perche="Una ragione lunga abbastanza da passare la validazione e "
                   "da sembrare seria a chi la rilegge fra tre mesi.")
        with pytest.raises(DichiarazioneScaduta, match="cancellata"):
            scansiona(tmp_path, dichiarati=(firma,))

    def test_il_riepilogo_STAMPA_la_ragione(self, rapporto: Rapporto) -> None:
        """Un elenco di nomi nudi non fa risparmiare niente a chi indaga: la
        ragione va letta insieme al nome, o si torna a guardare il codice."""
        from scripts.orfani import _riepilogo

        testo = _riepilogo(rapporto, tutti=False)
        for d in DICHIARATI:
            assert d.nome in testo
            assert d.perche.split(".")[0] in testo
