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
    NOME_FILE,
    GeometriaPannello,
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
        assert s.carica().vuoto()
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

        assert layout.vuoto(), "un file rotto deve dare un layout vuoto, non un'eccezione"
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
        assert LayoutStore(f).carica().vuoto()
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
