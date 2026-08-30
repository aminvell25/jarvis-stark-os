"""La persistenza del layout — §26.10 punto 1.

«Un'icona trascinata sul fondo che al riavvio torna al suo posto e' peggio di
un'icona che non si puo' trascinare.» Quindi il criterio non e' «il file viene
scritto»: e' **che al riavvio la disposizione ci sia ancora**, e il test lo
verifica riavviando davvero il core, non simulando un riavvio.

## Cosa NON e' questo modulo

Non e' un tool. `tools/registry.py` e' l'allowlist di cio' che l'LLM invoca;
questo e' l'ambiente che ricorda se stesso. Un test qui sotto lo impone,
perche' e' la decisione che un domani distratto rifarebbe al contrario.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest
from websockets.asyncio.client import unix_connect

from core.engine import Engine
from core.layout import (
    MINIMO_ICONA,
    NOME_FILE,
    CartellaLibera,
    GeometriaPannello,
    IconaLibera,
    Layout,
    LayoutMessage,
    LayoutStore,
    adatta,
)
from core.tools import registry


async def _attendi(condizione, timeout: float = 10.0) -> bool:
    fine = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < fine:
        if condizione():
            return True
        await asyncio.sleep(0.02)
    return condizione()


def _pannello(**campi) -> dict:
    base = {"id": "telemetria", "x": 100, "y": 60, "larghezza": 800,
            "altezza": 400, "z": 3, "massimizzato": False}
    return {**base, **campi}


# ── lo schema e il negozio ───────────────────────────────────────────────────


class TestIlNegozio:
    def test_file_assente_non_e_un_errore(self, tmp_path: Path) -> None:
        """«File assente: si parte dalla disposizione di moduli.js, come oggi.»"""
        s = LayoutStore(tmp_path / NOME_FILE)
        assert s.carica() == Layout()
        assert s.corrotto_in is None

    def test_giro_completo_su_disco(self, tmp_path: Path) -> None:
        s = LayoutStore(tmp_path / NOME_FILE)
        assert s.salva(Layout(pannelli=[GeometriaPannello(**_pannello())]))
        riletto = s.carica()
        assert [p.id for p in riletto.pannelli] == ["telemetria"]
        assert riletto.pannelli[0].z == 3

    def test_il_file_e_privato(self, tmp_path: Path) -> None:
        """0600 come `settings.toml`. Non contiene segreti, ma e' stato
        dell'utente e non c'e' ragione perche' lo legga qualcun altro."""
        s = LayoutStore(tmp_path / NOME_FILE)
        s.salva(Layout())
        assert (os.stat(s.percorso).st_mode & 0o077) == 0

    def test_json_corrotto_viene_messo_da_parte_e_si_riparte(self, tmp_path: Path) -> None:
        """«Un core che non parte per una virgola di troppo e' inaccettabile.»"""
        f = tmp_path / NOME_FILE
        f.write_text('{"pannelli": [ {"id": "telemetria",, ] ', encoding="utf-8")
        s = LayoutStore(f)

        layout = s.carica()

        assert layout == Layout(), (
            "un file rotto deve dare un layout vuoto, non un'eccezione"
        )
        assert s.corrotto_in is not None and s.corrotto_in.exists()
        assert not f.exists(), "l'originale dev'essere stato spostato, non lasciato li'"
        # il contenuto rotto resta leggibile: se domani si vuole capire come
        # si e' rotto, il file deve esistere ancora
        assert ",," in s.corrotto_in.read_text(encoding="utf-8")

    def test_un_json_valido_che_non_e_un_layout_e_corrotto_lo_stesso(
        self, tmp_path: Path
    ) -> None:
        """`{"pannelli": "ciao"}` e' JSON perfetto e non e' un layout. Il
        confine e' lo SCHEMA, non il parser."""
        f = tmp_path / NOME_FILE
        f.write_text('{"pannelli": "ciao"}', encoding="utf-8")
        assert LayoutStore(f).carica() == Layout()
        assert f.with_suffix(f.suffix + ".corrotto").exists()

    def test_la_scrittura_e_atomica(self, tmp_path: Path) -> None:
        """Nessun `.tmp` sopravvive: se ne restasse uno, prima o poi qualcuno
        troverebbe un JSON troncato al posto del layout."""
        s = LayoutStore(tmp_path / NOME_FILE)
        s.salva(Layout(pannelli=[GeometriaPannello(**_pannello())]))
        assert [f.name for f in tmp_path.iterdir()] == [NOME_FILE]


class TestIlFreno:
    """Il debounce del renderer non e' una difesa: il renderer puo' scegliere
    di non farlo. Questo e' il freno che non dipende da chi parla."""

    def test_due_salvataggi_ravvicinati_toccano_il_disco_una_volta(
        self, tmp_path: Path
    ) -> None:
        s = LayoutStore(tmp_path / NOME_FILE)
        assert s.salva(Layout(), ora=100.0) is True
        assert s.salva(Layout(), ora=100.05) is False
        assert s.salva(Layout(), ora=100.10) is False

    def test_cio_che_e_frenato_si_FONDE_e_non_si_perde(self, tmp_path: Path) -> None:
        """Scartare vorrebbe dire perdere l'ultima posizione di un
        trascinamento veloce — cioe' proprio quella che l'utente guarda."""
        s = LayoutStore(tmp_path / NOME_FILE)
        s.salva(Layout(), ora=100.0)
        s.salva(Layout(pannelli=[GeometriaPannello(**_pannello(x=999))]), ora=100.05)

        assert s.chiudi() is True
        assert s.carica().pannelli[0].x == 999

    def test_passato_l_intervallo_si_scrive_di_nuovo(self, tmp_path: Path) -> None:
        s = LayoutStore(tmp_path / NOME_FILE)
        s.salva(Layout(), ora=100.0)
        assert s.salva(Layout(), ora=100.0 + LayoutStore.MIN_INTERVALLO_S) is True


class TestFuoriArea:
    """«Posizione fuori dall'area: si riporta dentro, non si scarta.»"""

    def test_un_pannello_oltre_il_bordo_rientra(self) -> None:
        dentro = adatta(
            Layout(pannelli=[GeometriaPannello(**_pannello(x=3000, y=-40))]),
            1536, 827,
        ).pannelli[0]
        assert 0 <= dentro.x <= 1536 and 0 <= dentro.y <= 827

    def test_ne_resta_abbastanza_per_riprenderlo(self) -> None:
        """Non basta «dentro»: la testa e' la maniglia, e un pannello con un
        pixel a schermo e' irraggiungibile quanto uno fuori."""
        # 30000 e non 99999: oltre 32768 lo rifiuta gia' lo schema, ed e'
        # giusto cosi' — ma allora il caso da provare qui e' quello che lo
        # schema LASCIA passare e che l'area non contiene.
        dentro = adatta(
            Layout(pannelli=[GeometriaPannello(**_pannello(x=30000, y=30000))]),
            1536, 827,
        ).pannelli[0]
        assert dentro.x <= 1536 - 80 and dentro.y <= 827 - 80

    def test_un_pannello_piu_grande_dello_schermo_viene_rimpicciolito(self) -> None:
        dentro = adatta(
            Layout(pannelli=[GeometriaPannello(**_pannello(larghezza=5000, altezza=3000))]),
            1536, 827,
        ).pannelli[0]
        assert dentro.larghezza == 1536 and dentro.altezza == 827

    def test_NON_si_scarta(self) -> None:
        prima = Layout(pannelli=[GeometriaPannello(**_pannello(x=9000)),
                                 GeometriaPannello(**_pannello(id="console", x=-9000))])
        assert len(adatta(prima, 1536, 827).pannelli) == 2

    def test_l_area_viene_ricordata(self) -> None:
        """Senza, al prossimo avvio non si distingue «fuori schermo» da
        «schermo cambiato»."""
        d = adatta(Layout(), 1536, 827)
        assert (d.area_larghezza, d.area_altezza) == (1536, 827)


# ── il canale ────────────────────────────────────────────────────────────────


class TestIlCanale:
    """Il terzo tipo in ingresso, e il primo che il renderer INIZIA."""

    def _msg(self, **extra) -> str:
        return json.dumps({
            "topic": "ui.layout", "area_larghezza": 1536, "area_altezza": 827,
            "pannelli": [_pannello()], **extra,
        })

    def test_un_messaggio_buono_passa(self) -> None:
        m = LayoutMessage.model_validate_json(self._msg())
        assert m.da_mettere_giu().pannelli[0].id == "telemetria"

    @pytest.mark.parametrize("grezzo,perche", [
        ('{"topic":"ui.layout","area_larghezza":1536,"area_altezza":827,'
         '"pannelli":[],"comando":"rm -rf"}', "un campo in piu'"),
        ('{"topic":"ui.qualcosaltro","area_larghezza":1,"area_altezza":1,"pannelli":[]}',
         "un topic diverso"),
        ('{"area_larghezza":1536,"area_altezza":827,"pannelli":[]}', "senza topic"),
        ('{"topic":"ui.layout","pannelli":[]}', "senza area"),
        ('{"topic":"ui.layout","area_larghezza":1536,"area_altezza":827,'
         '"pannelli":[{"id":"../../etc/passwd","x":0,"y":0,'
         '"larghezza":1,"altezza":1}]}', "un id che e' un percorso"),
        ('{"topic":"ui.layout","area_larghezza":1536,"area_altezza":827,'
         '"pannelli":[{"id":"a","x":99999999,"y":0,"larghezza":1,"altezza":1}]}',
         "una coordinata assurda"),
    ])
    def test_cio_che_non_passa_lo_schema_viene_rifiutato(self, grezzo, perche) -> None:
        """`extra="forbid"` e i limiti non sono pedanteria: sono cio' che
        rende questo canale una DICHIARAZIONE DI STATO e non un canale di
        comandi. Il giorno in cui uno di questi passasse, il canale sarebbe
        diventato un'altra cosa."""
        with pytest.raises(Exception):
            LayoutMessage.model_validate_json(grezzo)

    def test_il_taglio_avviene_PRIMA_del_disco(self) -> None:
        """Un renderer che sbaglia non lascia dietro un file che il prossimo
        avvio dovra' correggere."""
        m = LayoutMessage.model_validate_json(self._msg(pannelli=[_pannello(x=30000)]))
        assert m.da_mettere_giu().pannelli[0].x <= 1536


# ── §26.5 — il fondo della scrivania ─────────────────────────────────────────


class TestLIdentitaDiUnIcona:
    """R92 — il segnaposto del punto 1 aveva la forma sbagliata.

    Diceva `id: str = ID`, e `ID` accetta `^[a-z0-9][a-z0-9_.-]*$`. Non era un
    dettaglio: la PRIMA icona di un file con una maiuscola avrebbe fatto
    rifiutare l'intero messaggio, e la scrivania avrebbe smesso di ricordare
    anche i pannelli. La difesa si sarebbe trasformata in un guasto.
    """

    @pytest.mark.parametrize("nome", [
        "Relazione Q3 (bozza).pdf",   # maiuscole, spazi, parentesi
        "sezione-longitudinale.dxf",
        "città.md",                   # accento
        "IMG_0042.JPEG",
        "a" * 255,                    # il tetto dichiarato
    ])
    def test_un_nome_di_file_vero_passa(self, nome: str) -> None:
        ic = IconaLibera(tipo="file", nome=nome, x=10, y=20)
        assert ic.nome == nome

    @pytest.mark.parametrize("nome, perche", [
        ("../etc/passwd", "risale"),
        ("sotto/nota.txt", "separatore"),
        ("c:\\windows\\note.txt", "separatore di Windows"),
        (".", "voce di directory"),
        ("..", "voce di directory"),
        ("nota\x00.txt", "carattere di controllo"),
        ("nota\n.txt", "a capo, e finirebbe in un log"),
        ("a" * 256, "oltre il tetto"),
        ("", "vuoto"),
    ])
    def test_cio_che_somiglia_a_un_percorso_e_rifiutato(self, nome, perche) -> None:
        """Il campo e' un'ETICHETTA e il core non ci apre niente. Il validatore
        c'e' lo stesso: un campo che oggi nessuno tratta come un percorso e' un
        campo che fra un anno qualcuno trattera' come un percorso."""
        with pytest.raises(Exception):
            IconaLibera(tipo="file", nome=nome, x=0, y=0)

    def test_il_nome_di_un_MODULO_resta_stretto(self) -> None:
        """La larghezza serve ai nomi che arrivano dal disco. Un id di modulo
        e' scritto da noi, e uno storto e' un errore nostro da vedere subito."""
        assert IconaLibera(tipo="modulo", nome="telemetria", x=0, y=0)
        with pytest.raises(Exception):
            IconaLibera(tipo="modulo", nome="Telemetria", x=0, y=0)
        with pytest.raises(Exception):
            IconaLibera(tipo="modulo", nome="globo tattico", x=0, y=0)

    def test_il_tipo_e_un_elenco_chiuso(self) -> None:
        with pytest.raises(Exception):
            IconaLibera(tipo="scorciatoia", nome="x", x=0, y=0)

    def test_un_percorso_non_entra_nemmeno_di_traverso(self) -> None:
        """Nessun campo del fondo puo' portare un percorso: non c'e' proprio.

        E' la stessa sicurezza strutturale di `timezones`, che non ha un
        parametro path perche' non deve poterlo avere.
        """
        campi = set(IconaLibera.model_fields) | set(CartellaLibera.model_fields)
        assert not {c for c in campi if "path" in c or "percorso" in c}
        with pytest.raises(Exception):
            IconaLibera(tipo="file", nome="x", x=0, y=0,
                        percorso="/home/aminvell/JARVIS")


class TestCioCheNonVieneRIFIUTATO:
    """Il rovescio: rifiutare troppo e' l'altro modo di perdere il layout.

    Sono situazioni che il renderer non produce. Se arrivassero, far fallire
    l'INTERO messaggio significherebbe buttare via anche la disposizione dei
    pannelli — di nuovo la difesa che diventa guasto. Le raddrizza il renderer,
    che disegna sul fondo cio' che non trova casa.
    """

    def test_due_icone_uguali_passano(self) -> None:
        i = {"tipo": "modulo", "nome": "globo", "x": 1, "y": 2}
        assert len(Layout(icone=[IconaLibera(**i), IconaLibera(**i)]).icone) == 2

    def test_un_dentro_orfano_passa(self) -> None:
        l = Layout(icone=[IconaLibera(tipo="modulo", nome="globo", x=0, y=0,
                                      dentro="cartella.9")])
        assert l.icone[0].dentro == "cartella.9"


class TestLeCartelleNonSonoDelFilesystem:
    def test_l_id_resta_stretto(self) -> None:
        """L'id lo genera il renderer: e' nostro, non arriva dal disco."""
        assert CartellaLibera(id="cartella.1", x=0, y=0)
        with pytest.raises(Exception):
            CartellaLibera(id="../renders", x=0, y=0)

    def test_l_etichetta_e_un_nome_e_non_un_id(self) -> None:
        c = CartellaLibera(id="cartella.1", x=0, y=0, etichetta="Rendering 2026")
        assert c.etichetta == "Rendering 2026"

    def test_l_etichetta_non_porta_caratteri_di_controllo(self) -> None:
        """Finisce in un log."""
        with pytest.raises(Exception):
            CartellaLibera(id="cartella.1", x=0, y=0, etichetta="a\nb")

    def test_il_contenuto_sta_nelle_icone_e_non_qui(self) -> None:
        """Due contabilita' della stessa appartenenza divergerebbero al primo
        ramo dimenticato — e' gia' successo con la geometria di WinBox (R85)."""
        assert "icone" not in CartellaLibera.model_fields
        assert "contenuto" not in CartellaLibera.model_fields


class TestLAreaCominciaDaQualcheParte:
    """Il ritaglio del core e quello del renderer devono essere LA STESSA banda.

    `area_larghezza` e `area_altezza` sono il **pavimento** — lo spazio fra
    barra e dock — ma pannelli e icone sono salvati in coordinate di
    **finestra**. Fino al 25 agosto 2026 `adatta()` tagliava contro
    `[0, altezza - 80]` mentre `ui/src/desk/geometria-area.js::dentroArea`
    tagliava contro `[alto, alto + altezza - 80]`: due ritagli, due spazi di
    coordinate, una proprieta' sola.

    Con una barra alta 32 px la banda del core era traslata di 32 px in su.

    Il difetto era latente e nessuno lo vedeva finche' i numeri non si
    muovevano. Si e' visto quando il dock e' cresciuto di otto pixel per fare
    posto ai campi di stato: `TestIconeVere::test_10` e' caduto, e un'icona
    posata in fondo al pavimento tornava piu' su a ogni riavvio.
    """

    BARRA, PAVIMENTO = 32, 783          # dock 28 px su una finestra alta 843

    def test_un_icona_in_fondo_al_pavimento_NON_si_muove(self) -> None:
        """Il caso che cadeva: y 720 e' dentro il pavimento (32..815) e il
        renderer la accetta, ma la vecchia banda del core finiva a 703."""
        dopo = adatta(
            Layout(icone=[IconaLibera(tipo="file", nome="x.txt", x=100, y=720)]),
            1536, self.PAVIMENTO, sinistra=0, alto=self.BARRA,
        )
        assert (dopo.icone[0].x, dopo.icone[0].y) == (100, 720)

    def test_un_icona_NON_puo_finire_dentro_la_barra(self) -> None:
        """L'altro lato dello stesso difetto: `max(0, ...)` ammetteva y 10,
        cioe' sotto la barra, dove l'icona e' coperta e non si riprende."""
        dopo = adatta(
            Layout(icone=[IconaLibera(tipo="file", nome="x.txt", x=100, y=10)]),
            1536, self.PAVIMENTO, alto=self.BARRA,
        )
        assert dopo.icone[0].y == self.BARRA

    def test_la_banda_e_quella_di_dentroArea(self) -> None:
        """I due estremi, uno per uno, con la soglia delle ICONE.

        Che i numeri delle due sponde coincidano non si afferma qui: lo misura
        `tests/test_geometria_area.py::TestITreRitagliSonoUNO`, facendo girare
        la stessa tabella nei due linguaggi."""
        basso = self.BARRA + self.PAVIMENTO - MINIMO_ICONA
        for y, atteso in ((self.BARRA - 1, self.BARRA), (basso, basso),
                          (basso + 1, basso), (9999, basso)):
            dopo = adatta(
                Layout(icone=[IconaLibera(tipo="file", nome="x.txt", x=0, y=y)]),
                1536, self.PAVIMENTO, alto=self.BARRA,
            )
            assert dopo.icone[0].y == atteso, f"y {y} -> {dopo.icone[0].y}, atteso {atteso}"

    def test_il_dock_che_cresce_NON_sposta_un_icona(self) -> None:
        """La regressione, alla lettera. Otto pixel di dock in piu' accorciano
        il pavimento da 783 a 775, e un'icona a 700 restava a 700 col dock
        vecchio e finiva a 695 con quello nuovo."""
        prima = Layout(icone=[IconaLibera(tipo="file", nome="x.txt", x=100, y=700)])
        dopo = adatta(prima, 1536, 783, alto=self.BARRA)
        ancora = adatta(dopo, 1536, 775, alto=self.BARRA)
        assert dopo.icone[0].y == 700
        assert ancora.icone[0].y == 700

    def test_vale_anche_per_i_pannelli(self) -> None:
        """Non e' un difetto delle sole icone: `dentroArea` e' la funzione dei
        PANNELLI, ed e' quella con cui il core era disallineato."""
        p = GeometriaPannello(**_pannello(x=100, y=720))
        dopo = adatta(Layout(pannelli=[p]), 1536, self.PAVIMENTO, alto=self.BARRA)
        assert dopo.pannelli[0].y == 720

    def test_l_origine_viene_ricordata(self) -> None:
        d = adatta(Layout(), 1536, 783, sinistra=0, alto=32)
        assert (d.area_sinistra, d.area_alto) == (0, 32)

    def test_un_messaggio_SENZA_origine_si_comporta_come_prima(self) -> None:
        """La scelta di compatibilita', pinnata: un renderer che non manda i due
        campi nuovi continua a funzionare, con la banda di prima. E' sbagliata
        di quanto e' alta la barra, ma non e' una rottura."""
        msg = LayoutMessage(
            topic="ui.layout", versione=1, area_larghezza=1536, area_altezza=783,
            pannelli=[], icone=[IconaLibera(tipo="file", nome="x.txt", x=0, y=10)],
            cartelle=[], scena=None,
        )
        assert (msg.area_sinistra, msg.area_alto) == (0, 0)
        assert msg.da_mettere_giu().icone[0].y == 10


class TestIlFondoFuoriArea:
    def test_un_icona_oltre_il_bordo_rientra(self) -> None:
        """⚠️ 960 e 760, non 920 e 720: un'icona usa `MINIMO_ICONA` (40), non
        il minimo dei pannelli. Fino al 25 agosto 2026 il core applicava 80 anche
        alle icone mentre `ui/src/desk/icone.js` ne teneva 40, e restava una
        fascia di 40 px in cui il renderer accettava e il core spostava."""
        dopo = adatta(Layout(icone=[IconaLibera(tipo="file", nome="x.txt",
                                               x=5000, y=9000)]), 1000, 800)
        assert (dopo.icone[0].x, dopo.icone[0].y) == (960, 760)

    def test_una_cartella_oltre_il_bordo_rientra(self) -> None:
        """Una cartella e' un oggetto del fondo come un'icona: stessa soglia."""
        dopo = adatta(Layout(cartelle=[CartellaLibera(id="cartella.1",
                                                      x=-400, y=3)]), 1000, 800)
        assert (dopo.cartelle[0].x, dopo.cartelle[0].y) == (0, 3)

    def test_il_taglio_avviene_PRIMA_del_disco(self) -> None:
        """Come per i pannelli: un renderer che sbaglia non lascia dietro di se'
        un file che il prossimo avvio dovra' correggere."""
        msg = LayoutMessage(
            topic="ui.layout", area_larghezza=1000, area_altezza=800,
            icone=[IconaLibera(tipo="modulo", nome="globo", x=9000, y=1)],
            cartelle=[CartellaLibera(id="cartella.1", x=9000, y=1)],
        )
        giu = msg.da_mettere_giu()
        # 1000 - MINIMO_ICONA. ⚠️ Era `1000 - 80`, «lo stesso minimo_visibile
        # dei pannelli», e il commento diceva che andava bene perche' un'icona
        # e' piu' piccola di una finestra. Il ragionamento e' giusto e portava
        # alla conclusione opposta: piu' piccola vuol dire che ne basta MENO a
        # schermo, ed e' il 40 che `ui/src/desk/icone.js` usava gia'.
        assert giu.icone[0].x == 1000 - MINIMO_ICONA
        assert giu.cartelle[0].x == 1000 - MINIMO_ICONA


class TestIlFondoSopravviveAlDisco:
    def test_giro_completo(self, tmp_path: Path) -> None:
        negozio = LayoutStore(tmp_path / NOME_FILE)
        dentro = Layout(
            pannelli=[GeometriaPannello(**_pannello())],
            icone=[
                IconaLibera(tipo="modulo", nome="globo", x=10, y=20),
                IconaLibera(tipo="file", nome="Relazione Q3.pdf", x=0, y=0,
                            dentro="cartella.1"),
            ],
            cartelle=[CartellaLibera(id="cartella.1", x=40, y=50,
                                     etichetta="renders", aperta=True)],
        )
        assert negozio.salva(dentro, ora=1000.0)
        fuori = LayoutStore(tmp_path / NOME_FILE).carica()
        assert fuori == dentro
        assert fuori.icone[1].nome == "Relazione Q3.pdf"
        assert fuori.cartelle[0].aperta is True

    def test_un_layout_di_sole_icone_ha_qualcosa_da_ripristinare(self) -> None:
        """§26.5: il ripristino non deve saltare una scrivania senza pannelli
        spostati e con tre icone sul fondo.

        ⚠️ **Questo test asseriva su `Layout.vuoto()`, un predicato che il
        renderer non chiama MAI.** La guardia vera è `ui/src/app.js:303`, e
        conta il fondo e i pannelli separatamente. Un test che misura un
        predicato Python al posto della guardia che gira è una ricevuta, non un
        custode: qui si asserisce sui campi, che è ciò che la guardia legge.

        ⚠️ **E la proprietà END-TO-END resta senza custode**, dichiarato in
        `docs/acceptance/IL-FONDO-SENZA-CUSTODE.md`: né `test_10` né `test_11`
        esercitano `pannelli == 0` — `test_11` pretende `ripristino["messi"]`,
        che si scrive solo dopo `if (!roba) return`, e una cartella aperta è un
        pannello. Scrivere in `test_10` che copre §26.5 sarebbe stata una
        ricevuta falsa.
        """
        vuoto = Layout()
        assert not (vuoto.pannelli or vuoto.icone or vuoto.cartelle)

        sole_icone = Layout(icone=[IconaLibera(tipo="modulo", nome="globo",
                                               x=0, y=0)])
        assert not sole_icone.pannelli
        assert sole_icone.icone or sole_icone.cartelle, (
            "un fondo non vuoto è ciò che `ui/src/app.js:303` conta per non "
            "saltare il ripristino"
        )

        sole_cartelle = Layout(cartelle=[CartellaLibera(id="cartella.1",
                                                        x=0, y=0)])
        assert not sole_cartelle.pannelli
        assert sole_cartelle.cartelle


# ── §26.5 — icone libere e cartelle, nell'app vera ───────────────────────────


@pytest.fixture(scope="module")
def esiti_icone() -> dict:
    """`scripts/prova-icone.mjs`: Electron vero, core vero, puntatore vero.

    Un solo avvio per tutte le prove — anzi due, perche' §26.9 punto 4 vuole un
    riavvio VERO — e ogni sezione va a fondo per conto suo, cosi' una sola
    esecuzione da' il quadro intero.
    """
    import shutil
    import subprocess

    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    radice = Path(__file__).resolve().parent.parent
    if not (radice / "node_modules/playwright").exists():
        pytest.skip("playwright non installato")
    from core.platform import paths as platform_paths
    if not platform_paths().socket_path().exists():
        pytest.skip("il core non e' in esecuzione: `python -m core.engine`")

    r = subprocess.run(
        ["node", "scripts/prova-icone.mjs", "--scatti", "shots/icone"],
        cwd=radice, capture_output=True, text=True, timeout=900,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.mark.slow
class TestIconeVere:
    """§26.9 criteri 4 e 5, col puntatore e col riavvio veri.

    ## Perche' non bastano i test dello schema

    Meta' di §26.5 e' fatta di cose che un test senza puntatore non puo'
    nemmeno esprimere: che tirare fuori un'icona non scorra il nastro, che
    l'icona in mano stia SOPRA i pannelli mentre li attraversa, che la cartella
    si accenda quando ci si passa sopra con qualcosa in mano.

    Ed e' cosi' che si e' trovato R98: la regola che distingueva estrazione e
    scorrimento — «piu' verticale che orizzontale» — era sbagliata, e nessun
    test senza un puntatore vero avrebbe potuto dirlo.
    """

    def test_1_l_icona_esce_dal_catalogo_e_l_indice_non_perde_la_voce(
            self, esiti_icone) -> None:
        """§26.5: «L'icona nel catalogo non sparisce: il catalogo e' l'indice,
        la scrivania e' il piano di lavoro.»"""
        e = esiti_icone["estrazione"]
        assert e.get("icona"), f"nessuna icona sul fondo: {e}"
        assert e["indice_intatto"], "il catalogo ha perso la voce che ha ceduto"
        assert e["dove_lho_lasciata"], e
        # R95/R98: il gesto verticale non deve aver scorso il nastro.
        assert e["nastro_fermo"], "l'estrazione ha scorso il catalogo"

    def test_2_cio_che_si_ha_in_mano_si_vede_sempre(self, esiti_icone) -> None:
        """Al proprio piano l'icona sparirebbe dietro il primo pannello
        attraversato, e si trascinerebbe alla cieca."""
        e = esiti_icone["estrazione"]
        assert e["sopra_i_pannelli"], e["in_mano"]

    def test_3_le_icone_libere_stanno_SOTTO_i_pannelli(self, esiti_icone) -> None:
        """§26.5, e misurato nella finestra vera invece che nel CSS."""
        e = esiti_icone["sottoIPannelli"]
        assert e["sotto"], e
        assert e["dentro_un_pannello_risponde"] == "pannello", (
            "lo strato delle icone intercetta i clic dei pannelti sotto"
        )
        assert e["strato_trasparente"]

    def test_4_il_fondo_esiste_davvero_sulla_scrivania_composta(
            self, esiti_icone) -> None:
        """R97, e la sua chiusura da parte di §26.6.

        Con la CASCATA di ADR-010 — tredici pannelli aperti insieme, ognuno
        sulla propria piastrellatura completa — non esisteva un solo punto di
        fondo scoperto: le icone libere si potevano posare, ma solo sotto ai
        pannelli, e per vederle serviva `Alt+H`.

        Con la scena di avvio il fondo torna, ed e' dove il riferimento lo
        usa: il quadrante in basso a sinistra e le fasce ai lati del catalogo,
        larghe due colonne — troppo strette per qualunque pannello (R99) e
        giuste per una cartella manila.

        ⚠️ Il numero si misura invece di darlo per buono: se una composizione
        futura tornasse a coprire tutto, §26.5 diventerebbe raggiungibile solo
        di nascosto, e sarebbe questo test a dirlo.
        """
        e = esiti_icone["scoprireIlFondo"]
        assert e["fondo_scoperto_a_scrivania_piena"] is True, (
            "la scrivania composta non lascia scoperto un solo punto di fondo: "
            "le cartelle di §26.5 non avrebbero dove stare"
        )
        assert e["con_alt_h"], "nemmeno Alt+H scopre il fondo"
        assert e["catalogo_ancora_li"], "Alt+H ha nascosto anche l'indice"

    def test_5_l_icona_lasciata_su_una_cartella_ENTRA(self, esiti_icone) -> None:
        """§26.9 criterio 5, prima meta'."""
        e = esiti_icone["cartella"]
        assert e["cartella_nata"], e
        assert e["dentro"], "l'icona non e' entrata nella cartella"
        assert e["sparita_dal_fondo"] == 0, "e' entrata E rimasta fuori"

    def test_6_la_cartella_dichiara_quante_cose_contiene(self, esiti_icone) -> None:
        """§26.9 criterio 5, seconda meta'. Zero e' uno stato esplicito."""
        e = esiti_icone["cartella"]
        assert e["conteggio_dichiarato"], "la cartella non dichiara niente"
        assert any(c.isdigit() for c in e["conteggio_dichiarato"])

    def test_7_la_cartella_si_illumina_quando_ci_passo_sopra(
            self, esiti_icone) -> None:
        """§26.5: «si illumina a --manila piu' chiaro mentre il puntatore e'
        sopra». Si guarda il colore CALCOLATO, non la classe."""
        e = esiti_icone["cartella"]
        assert e["si_illumina"], (e["acceso_mentre_ci_passo"], e["fondo_a_riposo"])
        assert e["acceso_mentre_ci_passo"]["esito"] == "cartella", (
            "cio' che si ha in mano non annuncia dove sta per finire"
        )

    def test_8_la_cartella_si_apre_come_un_pannello_di_10_2(
            self, esiti_icone) -> None:
        """§26.5: «un pannello del sistema, con l'anatomia a cinque parti».

        R94: passa dal registro della scrivania, quindi ha i tre controlli veri
        della cornice ed entra nella disposizione salvata come ogni altro.
        """
        e = esiti_icone["aperturaCartella"]
        assert e["aperto"] and e["dentro_winbox"], e
        assert e["controlli"] == ["riduci", "ingrandisci", "chiudi"], e["controlli"]
        assert e["maniglia"], "la testa non e' una maniglia: non si trascina"
        for parte in ("etichetta", "conteggio", "id", "piede"):
            assert e[parte], f"manca la parte «{parte}» di §10.2"
        assert e["righe"], "il pannello non elenca cio' che la cartella contiene"
        assert e["nella_disposizione"]

    def test_9_trascinarla_sul_catalogo_la_toglie(self, esiti_icone) -> None:
        """§26.5: «si rimuove trascinandola sul catalogo o dal menu
        contestuale». E lo ANNUNCIA prima, col catalogo che passa all'accento
        caldo: una rimozione che non si vede arrivare e' una rimozione per
        sbaglio."""
        e = esiti_icone["rimozione"]
        assert e["tolta"], e
        assert e["avvisa"]["esito"] == "rimuovi", e["avvisa"]

    def test_10_riavviato_il_core_e_ANCORA_LI(self, esiti_icone) -> None:
        """§26.9 criterio 4, alla lettera: «Verificato riavviando davvero, non
        simulando.» Fra i due avvii non resta niente in memoria: l'unica cosa
        che attraversa e' `layout.json`.

        ⚠️ Si confrontano `id` ed `etichetta` delle cartelle, non le
        coordinate: il core le fa passare da `adatta()` contro l'area
        dichiarata, e uno scarto di qualche pixel e' il taglio che funziona,
        non un errore.
        """
        e = esiti_icone["riavvio"]
        assert e["su_disco"], "il core non ha scritto niente"
        assert e["su_disco"]["cartelle"], "le cartelle non sono finite su disco"
        assert e["icone_uguali"], (e["prima_della_chiusura"], e["dopo_la_riapertura"])
        assert e["cartelle_uguali"], e
        assert e["e_ancora_li"], e

    def test_11_una_cartella_aperta_si_riapre(self, esiti_icone) -> None:
        """`aperta` non e' un campo decorativo dello schema: al riavvio il
        pannello della cartella deve tornare, col suo contenuto."""
        e = esiti_icone["riavvio"]
        assert any(str(m).startswith("cartella.")
                   for m in e["ripristino"]["messi"]), e["ripristino"]
        assert e["a_schermo"]["conteggio"], "la cartella riaperta non conta piu'"

    def test_12_un_layout_di_SOLE_icone_si_rimette(self, esiti_icone) -> None:
        """§26.5 — il ramo che `test_10` e `test_11` NON possono prendere.

        `ui/src/app.js` decide il ripristino con
        `(layout?.pannelli?.length ?? 0) + suoFondo`, e il secondo termine
        esiste perche' una scrivania di sole icone non riparta vuota. Fino a
        questa sezione **nessuna prova lo esercitava**: `test_11` pretende una
        cartella aperta, e una cartella aperta *e'* un pannello, quindi
        `layout.pannelli` era sempre non vuoto e la guardia si attraversava
        dai pannelli. Misurato a HEAD: `riavvio.ripristino.ricevuti == 7`.
        Togliere `+ suoFondo` lasciava verde tutta la classe.

        Le tre asserzioni dicono tre cose diverse, e servono tutt'e tre:

        * `su_disco["pannelli"] == []` col fondo pieno — il caso e' stato
          **prodotto davvero**, non descritto;
        * `ripristino["ricevuti"] == 0` — quel layout e' arrivato al renderer,
          che ha attraversato la guardia **dal fondo**;
        * `icone_uguali` — la proprieta' di §26.5 vale.

        ⚠️ **Una quarta asserzione dice CHI scrive**, e sta qui per via di una
        bocciatura andata storta. Leggendo il codice, chiudere un pannello non
        scrive niente: `onclose` chiama `annuncia()`, che avvisa gli
        osservatori e non la persistenza. La prima stesura della sezione
        aggiungeva percio' un gesto sul fondo per far scattare la scrittura —
        e la bocciatura che doveva dimostrarlo necessario **ha dimostrato il
        contrario**: tolto il gesto, su disco arriva `pannelli: []` lo stesso.
        Il gesto e' stato tolto, e al suo posto la sezione misura le scritture
        dopo la chiusura dei moduli e dopo quella della cartella.
        """
        e = esiti_icone["soloIlFondo"]
        assert not e["chiusura"]["restano"], e["chiusura"]
        assert e["su_disco"], "il core non ha scritto niente"
        assert e["su_disco"]["pannelli"] == [], e["su_disco"]["pannelli"]
        assert e["su_disco"]["icone"], "il fondo non e' finito su disco"
        # Chi scrive: l'ultima scrittura dopo la chiusura porta ZERO pannelli.
        # Se un domani la chiusura smettesse di scrivere, il caso non nascerebbe
        # piu' e questa riga lo direbbe prima delle altre.
        assert e["chiusura"]["scritture"], "la chiusura non ha scritto niente"
        assert e["chiusura"]["scritture"][-1]["pannelli"] == 0, e["chiusura"]
        rip = e.get("ripristino")
        assert rip is not None, (
            "il renderer non ha ripristinato NIENTE: con `pannelli: []` la "
            "guardia di §26.5 e' tornata indietro, e il fondo e' andato perso")
        assert rip["ricevuti"] == 0, rip
        assert e["icone_uguali"], (e["prima_della_chiusura"], e["dopo_la_riapertura"])
        assert e["a_schermo"]["icone"], "sul fondo non e' tornata nessuna icona"


class TestNonEUnTool:
    def test_non_e_nell_allowlist(self, short_paths) -> None:
        """Con `side_effect=True` uscirebbe una conferma a ogni pannello
        spostato; con `side_effect=False` starebbe nell'elenco che l'LLM riceve
        senza che nessuno debba invocarlo. Non passa dal registry affatto."""
        Engine(short_paths)
        assert not [n for n in registry.names() if "layout" in n]


class TestR82:
    """Il ridimensionamento ADATTA, non ricompone.

    Trovato dal vivo e non dai test: col ripristino funzionante, un pannello
    rimesso a 500,300 tornava a 4,42 entro un secondo dall'avvio. La causa era
    `window.addEventListener("resize", affianca)`, che §13 poteva permettersi
    perche' non c'era niente da conservare.

    L'esperimento che l'ha isolata: tolta quella riga, il ripristino ha tenuto.
    Rimessa, no. Questo test e' la riga che impedisce che torni — ed e' un
    controllo sul SORGENTE perche' la prova vera vuole una finestra vera, e una
    prova che costa venti secondi non gira a ogni commit.
    """

    def _scrivania(self) -> str:
        """Il CODICE, senza i commenti.

        Il commento che spiega R82 contiene per forza la riga che vieta — non
        si spiega un divieto senza nominarlo. Un controllo che scatta sulla
        propria spiegazione viene allentato al primo falso positivo, e da li'
        non protegge piu' niente: e' la stessa lezione del test
        dell'invariante 29 in `test_platform.py`.
        """
        import re as _re

        radice = Path(__file__).resolve().parent.parent
        testo = (radice / "ui/src/desk/scrivania.js").read_text(encoding="utf-8")
        senza_blocchi = _re.sub(r"/\*.*?\*/", " ", testo, flags=_re.S)
        return _re.sub(r"^\s*//.*$", " ", senza_blocchi, flags=_re.M)

    def test_il_resize_non_chiama_affianca(self) -> None:
        s = self._scrivania()
        assert 'addEventListener("resize", affianca)' not in s, (
            "il ridimensionamento rimette i pannelli nelle celle dichiarate e "
            "cancella la disposizione dell'utente: e' il difetto R82"
        )
        assert 'addEventListener("resize", riadatta)' in s

    def test_affianca_resta_un_gesto_esplicito(self) -> None:
        """Ricomporre non sparisce: diventa `Alt+T`. §26.2 — «nessun riordino
        automatico: una pila che si riorganizza da sola e' la cosa che rende un
        ambiente inabitabile»."""
        radice = Path(__file__).resolve().parent.parent
        tastiera = (radice / "ui/src/desk/tastiera.js").read_text(encoding="utf-8")
        assert "affianca" in tastiera, "Alt+T deve ancora ricomporre"


# ── il ritardo, nel renderer ─────────────────────────────────────────────────


BANCO_DEBOUNCE = """
import { creaPersistenza, RITARDO_MS } from "./ui/src/desk/layout.js";

const inviati = [];
const p = creaPersistenza({ invia: (d) => inviati.push(d) });

// Dieci movimenti in 200 ms, uno ogni 20.
let n = 0;
const t = setInterval(() => {
  p.suDisposizione({ area: { larghezza: 1536, altezza: 827 },
                     pannelli: [{ id: "console", x: n, y: 0, larghezza: 10,
                                  altezza: 10, z: 1, massimizzato: false }],
                     scena: null });
  if (++n === 10) clearInterval(t);
}, 20);

// Un margine oltre il ritardo, e poi si guarda.
setTimeout(() => {
  console.log(JSON.stringify({
    ritardo: RITARDO_MS,
    scritture: inviati.length,
    ultimoX: inviati.at(-1)?.pannelli?.[0]?.x ?? null,
  }));
}, 200 + RITARDO_MS + 250);
"""


@pytest.mark.slow
def test_dieci_movimenti_in_200ms_producono_UNA_scrittura(tmp_path: Path) -> None:
    """«Un debounce, non un throttle — durante il trascinamento non si scrive
    niente.»

    Con un throttle si scriverebbe DURANTE, e sul disco finirebbero posizioni
    intermedie che nessuno ha scelto. Qui si misura che ne esca **una sola**, e
    che sia **l'ultima**: e' dove l'utente ha lasciato la finestra, l'unica
    posizione che significhi qualcosa.
    """
    import shutil
    import subprocess

    if shutil.which("node") is None:
        pytest.skip("node non disponibile")

    radice = Path(__file__).resolve().parent.parent
    banco = tmp_path / "banco.mjs"
    banco.write_text(BANCO_DEBOUNCE.replace("./ui/src/desk/layout.js",
                                            str(radice / "ui/src/desk/layout.js")),
                     encoding="utf-8")
    r = subprocess.run(["node", str(banco)], cwd=radice,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-800:]
    esito = json.loads(r.stdout.strip().splitlines()[-1])

    assert esito["ritardo"] == 500, "§26.5 dice 500 ms"
    assert esito["scritture"] == 1, (
        f"{esito['scritture']} scritture invece di una: durante il "
        f"trascinamento non si deve scrivere niente"
    )
    assert esito["ultimoX"] == 9, "l'ultima posizione, non una di mezzo"


# ── il giro vero: salva, riavvia, ritrova ────────────────────────────────────


@pytest.mark.slow
class TestQuandoLaScrivaniaSiChiude:
    """L'ultima modifica prima di chiudere la finestra non si perde.

    ## Il difetto, e la sua forma

    `LayoutStore` frena a `MIN_INTERVALLO_S` (0,25 s) e **fonde invece di
    scartare**: cio' che non scrive resta in `_in_attesa`, e `chiudi()` lo mette
    giu'. Tutt'e due le meta' esistono da §26.10 e sono provate
    (`TestIlFreno::test_cio_che_e_frenato_si_FONDE_e_non_si_perde`).

    **Non erano congiunte.** L'unico chiamante di `chiudi()` era lo spegnimento
    del CORE, e il core e' un servizio che resta acceso: la scrivania e' una
    finestra che si apre e si chiude sopra di lui. Chi chiudeva la finestra
    entro un quarto di secondo dall'ultima modifica la perdeva — e al riavvio
    della scrivania `messaggio_iniziale()` rilegge il DISCO, che era rimasto
    indietro.

    ⚠️ **La diagnosi precedente era sbagliata, ed e' stata misurata.** Il 30
    agosto avevo attribuito la perdita al debounce di 500 ms del renderer
    (`docs/acceptance/IL-FONDO-SENZA-CUSTODE.md`). Tre chiusure a confronto —
    con l'attesa, con `app.close()` di Playwright, con `BrowserWindow.close()`
    vera — hanno recapitato il marcatore **tutt'e tre**: il flush di `pagehide`
    funziona. Il pezzo che mancava stava un piano sotto, nel core.
    """

    async def test_cio_che_il_freno_TRATTIENE_va_giu_alla_chiusura_della_scrivania(
        self, short_paths
    ) -> None:
        """L'ultima scrivania si stacca: quel che era trattenuto va sul disco.

        Le due `salva()` hanno l'ora esplicita perche' il caso e' proprio
        «entro `MIN_INTERVALLO_S`», e un test che lo lasciasse decidere
        all'orologio proverebbe qualcosa di diverso a ogni esecuzione.
        """
        engine = Engine(short_paths)
        file_layout = short_paths.data_dir() / NOME_FILE

        assert engine._layout.salva(Layout(), ora=100.0) is True
        trattenuto = Layout(pannelli=[GeometriaPannello(**_pannello(x=999))])
        assert engine._layout.salva(trattenuto, ora=100.05) is False
        # Il freno ha morso davvero: senza questa riga il resto non proverebbe
        # niente, perche' un valore gia' sul disco tornerebbe verde da solo.
        assert LayoutStore(file_layout).carica().pannelli == []

        engine._scrivanie_cambiate(0)

        rimesso = LayoutStore(file_layout).carica().pannelli
        assert rimesso, ("la scrivania si e' chiusa e cio' che il freno "
                         "tratteneva non e' andato giu': e' perso")
        assert rimesso[0].x == 999

    async def test_una_scrivania_su_due_che_si_chiude_NON_mette_giu_niente(
        self, short_paths
    ) -> None:
        """Il momento e' «non c'e' piu' nessuno», non «qualcuno se n'e'
        andato». Con una finestra ancora aperta i messaggi continuano ad
        arrivare, e mettere giu' a ogni distacco vorrebbe dire scrivere sul
        disco per un evento che non ha cambiato niente."""
        engine = Engine(short_paths)
        file_layout = short_paths.data_dir() / NOME_FILE

        engine._layout.salva(Layout(), ora=100.0)
        engine._layout.salva(Layout(pannelli=[GeometriaPannello(**_pannello(x=999))]),
                             ora=100.05)

        engine._scrivanie_cambiate(1)

        assert LayoutStore(file_layout).carica().pannelli == []


class TestRiavvioVero:
    async def test_il_layout_sopravvive_al_RIAVVIO_del_core(self, short_paths) -> None:
        """Il criterio di §26.9 punto 4, alla lettera: «riavviato il core, e'
        ancora li'. Verificato riavviando davvero, non simulando.»

        Due `Engine` distinti, due `run()`, due connessioni. Fra i due non
        resta niente in memoria: l'unica cosa che attraversa e' il file.
        """
        sock = short_paths.socket_path()

        # ── primo avvio: il renderer manda la propria disposizione ──────────
        primo = Engine(short_paths)
        t1 = asyncio.create_task(primo.run())
        assert await _attendi(lambda: sock.is_socket()), "socket non comparso"
        async with unix_connect(str(sock)) as ws:
            await ws.send(json.dumps({
                "topic": "ui.layout", "area_larghezza": 1536, "area_altezza": 827,
                "pannelli": [_pannello(id="console", x=222, y=111, z=7)],
            }))
            # il messaggio viaggia e il core scrive
            file_layout = short_paths.data_dir() / NOME_FILE
            assert await _attendi(file_layout.exists), "il core non ha scritto"
        primo._stop.set()
        await asyncio.wait_for(t1, timeout=10)

        # ── secondo avvio: il core SPINGE il layout a chi si collega ────────
        secondo = Engine(short_paths)
        t2 = asyncio.create_task(secondo.run())
        assert await _attendi(lambda: sock.is_socket()), "socket non ricomparso"
        ricevuto: list[dict] = []
        async with unix_connect(str(sock)) as ws:
            async def leggi() -> None:
                async for grezzo in ws:
                    m = json.loads(grezzo)
                    if m.get("topic") == "ui.layout":
                        ricevuto.append(m)
                        return
            await asyncio.wait_for(leggi(), timeout=10)
        secondo._stop.set()
        await asyncio.wait_for(t2, timeout=10)

        assert ricevuto, "lo snapshot iniziale non porta ui.layout"
        p = ricevuto[0]["pannelli"][0]
        assert (p["id"], p["x"], p["y"], p["z"]) == ("console", 222, 111, 7)

    async def test_un_layout_corrotto_non_impedisce_l_avvio(self, short_paths) -> None:
        """Il caso peggiore: il file c'e' ed e' spazzatura. Il core parte
        lo stesso, mette da parte, e lo DICHIARA nello snapshot."""
        f = short_paths.data_dir() / NOME_FILE
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("{{{ non e' json", encoding="utf-8")

        engine = Engine(short_paths)
        task = asyncio.create_task(engine.run())
        sock = short_paths.socket_path()
        assert await _attendi(lambda: sock.is_socket()), "il core non e' partito"

        pannelli = await engine.stato_pannelli()
        engine._stop.set()
        await asyncio.wait_for(task, timeout=10)

        layout = next(m for m in pannelli if m["topic"] == "ui.layout")
        assert layout["pannelli"] == []
        assert engine.state_snapshot()["layout"]["corrotto_in"] is not None
        assert f.with_suffix(f.suffix + ".corrotto").exists()

    async def test_un_pannello_che_non_esiste_piu_non_fa_cadere_l_avvio(
        self, short_paths
    ) -> None:
        """Il core non conosce `moduli.js` e non deve: accetta l'id, lo
        ricorda, e a ignorarlo e' il renderer. Qui si verifica la meta' del
        core — che un id sconosciuto non sia un errore che ferma qualcosa."""
        store = LayoutStore(short_paths.data_dir() / NOME_FILE)
        store.salva(Layout(pannelli=[
            GeometriaPannello(**_pannello(id="pannello.sparito")),
            GeometriaPannello(**_pannello(id="console")),
        ]))

        engine = Engine(short_paths)
        task = asyncio.create_task(engine.run())
        assert await _attendi(lambda: short_paths.socket_path().is_socket())
        pannelli = await engine.stato_pannelli()
        engine._stop.set()
        await asyncio.wait_for(task, timeout=10)

        ids = [p["id"] for p in
               next(m for m in pannelli if m["topic"] == "ui.layout")["pannelli"]]
        assert ids == ["pannello.sparito", "console"]


# ── il gesto vero, nell'applicazione vera ────────────────────────────────────


#: Una sola esecuzione di Electron per tutte le prove del gesto: avviarne una
#: per controllo costerebbe dieci minuti e nessuno li aspetterebbe. `module` e
#: non `class` perche' una fixture di classe definita come metodo d'istanza e'
#: deprecata da pytest, e qui i warning sono errori.
@pytest.fixture(scope="module")
def esiti() -> dict:
    import shutil
    import subprocess

    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    radice = Path(__file__).resolve().parent.parent
    if not (radice / "node_modules/playwright").exists():
        pytest.skip("playwright non installato")
    # Il core dev'essere in ascolto: l'app vera parla col core vero.
    from core.platform import paths as platform_paths
    if not platform_paths().socket_path().exists():
        pytest.skip("il core non e' in esecuzione: `python -m core.engine`")

    r = subprocess.run(
        ["node", "scripts/prova-gesti.mjs", "--scatti", "shots/gesti"],
        cwd=radice, capture_output=True, text=True, timeout=600,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.mark.slow
class TestGestiVeri:
    """§26.9 criterio 4, e i «non verificato» 1, 6 e 7 di LAYOUT-PERSISTENTE.

    `scripts/prova-gesti.mjs` avvia **`app/main.js` con Electron**, non la
    galleria, e muove il puntatore con `page.mouse.down/move/up` di Playwright
    — che entra nella pipeline di input del browser, non e' un
    `dispatchEvent()` a livello JS.

    ## Perche' l'app e non la galleria

    R82 ha mostrato che i sei test possono essere verdi mentre il giro completo
    e' rotto. E' la SECONDA volta: prima c'era stato il CSP di PixiJS — la
    galleria non ne aveva uno, i glifi ci giravano, e nell'app non partivano da
    quattro fasi. La regola che se ne ricava, e che §11.7 adesso porta scritta:

        **un ambiente di prova piu' permissivo di quello reale approva codice
        che nel reale e' rotto.**

    Un solo processo Electron per tutte le prove: avviarne uno per controllo
    costerebbe dieci minuti e nessuno lo aspetterebbe.
    """

    def test_1_il_pannello_e_dove_l_ho_lasciato(self, esiti) -> None:
        """Premere sulla testa, muovere in venti passi, rilasciare."""
        g = esiti["gesto"]
        assert "errore" not in g, g
        assert g["dove_lo_lascio"], f"lasciato in {g['dopo']}, atteso {g['atteso']}"

    def test_2_venti_pointermove_producono_UNA_scrittura(self, esiti) -> None:
        """Il caso che il banco sintetico non copriva: una sequenza VERA di
        `pointermove`, con `setPointerCapture` e il ritmo di un mouse."""
        g = esiti["gesto"]
        assert g["scritture"] == 1, (
            f"{g['scritture']} scritture in {g['durata_ms']} ms di gesto"
        )
        assert g["inviata_e_l_ultima"], (
            f"al core e' andata {g['ultima_posizione_inviata']}, il pannello e' "
            f"in {g['dopo']}: e' stata mandata una posizione di mezzo"
        )

    def test_3_il_doppio_clic_massimizza_e_poi_torna_DOVE_ERA(self, esiti) -> None:
        d = esiti["doppioClic"]
        assert "errore" not in d, d
        assert d["ha_massimizzato"], d["reso_massimizzato"]
        assert d["torna_dove_era"], (
            f"era in {d['prima']}, e' tornato in {d['tornato']}"
        )

    @pytest.mark.parametrize("bordo", ["sinistra", "destra", "alto", "basso"])
    def test_4_l_aggancio_al_bordo_e_un_GESTO(self, esiti, bordo) -> None:
        """`zonaAggancio()` era provata come funzione su cinque punti. Qui si
        trascina fin dentro la soglia e si rilascia, come farebbe una mano."""
        a = esiti["aggancio"][bordo]
        assert a["agganciato"], a

    def test_5_riaperta_l_app_il_pannello_e_dove_l_avevo_lasciato(self, esiti) -> None:
        """Criterio 4 di §26.9. L'app si chiude davvero e si riapre davvero."""
        g = esiti["giroCompleto"]
        assert "errore" not in g, g
        assert g["e_dove_l_ho_lasciato"], (
            f"lasciato in {g['prima_della_chiusura']}, su disco {g['su_disco']}, "
            f"riaperto in {g['dopo_la_riapertura']}"
        )
        assert g["ripristino"]["ignorati"] == []

    def test_6_riadatta_muove_SOLO_chi_era_fuori(self, esiti) -> None:
        """Il «non verificato» 7. Chi era dentro non si muove di un pixel."""
        r = esiti["riadatta"]
        assert "errore" not in r, r
        assert r["solo_chi_era_fuori"], (
            f"mossi {r['mossi']}, ma fuori c'erano solo {r['erano_fuori']}"
        )
        assert r["tutti_dentro"], "qualcuno e' rimasto irraggiungibile"


class TestLaStrisciaDiceLaVERITA:
    """⚠️ La striscia LAYOUT del dock diceva `ok` su un file appena buttato via.

    La formula è `corrotto_in ? "corrotto" : esiste ? "ok" : "assente"`
    (`ui/src/desk/dock.js`), e `corrotto_in` si valorizza **dentro** `carica()`.
    Ma `carica()` aveva un solo chiamante — `messaggio_iniziale`, alla
    connessione della scrivania — mentre `state.snapshot` parte prima
    (`core/ws_server.py`, e la riga sopra dichiara perché). Quindi nella
    sessione in cui il guasto accade lo snapshot non poteva saperlo.

    Misurato, prima:

        file corrotto, prima di carica():  esiste=True,  corrotto_in=None  -> «ok»
        file corrotto, dopo  carica():     esiste=False, corrotto_in=<...>  -> «corrotto»
    """

    def _striscia(self, st: dict) -> str:
        """La formula di `ui/src/desk/dock.js`, qui perché il confine non si
        importa: l'accordo si misura, come `MINIMO_PANNELLO`."""
        return "corrotto" if st["corrotto_in"] else ("ok" if st["esiste"] else "assente")

    def test_un_layout_corrotto_lo_dice_dal_PRIMO_snapshot(self, short_paths) -> None:
        from core.engine import Engine
        f = short_paths.data_dir() / NOME_FILE
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('{"pannelli": "ciao"}', encoding="utf-8")

        e = Engine(short_paths)
        st = e.state_snapshot()["layout"]
        assert self._striscia(st) == "corrotto", (
            f"la striscia dice «{self._striscia(st)}» su un file che il core ha "
            "appena messo da parte: il Signore legge `ok` e non sa di aver perso "
            "la disposizione"
        )
        assert st["corrotto_in"] is not None

    def test_e_un_primo_avvio_resta_ASSENTE(self, short_paths) -> None:
        """Un file che non c'è mai stato non è un guasto: le due cose non
        devono confondersi, o la striscia griderebbe a ogni installazione."""
        from core.engine import Engine

        st = Engine(short_paths).state_snapshot()["layout"]
        assert self._striscia(st) == "assente"
        assert st["corrotto_in"] is None

    def test_e_un_layout_SANO_dice_ok(self, short_paths) -> None:
        from core.engine import Engine
        f = short_paths.data_dir() / NOME_FILE
        f.parent.mkdir(parents=True, exist_ok=True)
        LayoutStore(f).salva(Layout(pannelli=[_pannello()]))

        st = Engine(short_paths).state_snapshot()["layout"]
        assert self._striscia(st) == "ok"
        assert st["corrotto_in"] is None
