"""Il pilastro 3D — SPEC §17.1-17.3, ADR-014, invarianti 1, 3, 22, 23, 34.

`core/tools/model3d.py` e' stato **0 byte dal 18 agosto al 2 settembre 2026**,
mentre `CLAUDE.md` prometteva «genera modelli 3D» in prima pagina. Questi test
misurano le tre cose che ADR-014 promette in cambio:

* la geometria e' **parametrica e verificabile** — conteggi chiusi, bbox
  analitico, topologia che `trimesh` conferma senza passare dal nostro codice;
* il file lo decide il **core**, non chi chiede — nessun argomento `path`, la
  conferma di §6.2 col percorso risolto, e un rifiuto che non lascia niente;
* il verificatore di ADR-012 ha una **fonte indipendente**: rilegge il GLB con
  la sola libreria standard, e boccia davvero.
"""

from __future__ import annotations

import ast
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from core.model3d import glb_lettore
from core.model3d.estrusione import DEFAULT, TRIANGOLI, VERTICI, estrusione_45
from core.model3d.parametrico import MAX_VERTICI, Modello, ModelloNonValido
from core.tools import registry as R
from core.tools.model3d import GENERATORI, GeneraModelloArgs, register_model3d_tools
from core.verifica import Verdetto

RADICE = Path(__file__).resolve().parent.parent


class _FakeFS:
    trash_only = True

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.allowed_roots = [workspace]


class _FakeSettings:
    def __init__(self, workspace: Path) -> None:
        self.fs = _FakeFS(workspace)


@pytest.fixture
def mondo(tmp_path: Path):
    """Il tool solo, su una workspace temporanea, con la conferma in mano."""
    ws = (tmp_path / "workspace").resolve()
    ws.mkdir(parents=True)
    R.clear()
    pubblicati: list[dict] = []

    async def pubblica(msg: dict) -> None:
        pubblicati.append(msg)

    register_model3d_tools(lambda: _FakeSettings(ws), pubblica)
    stato = {"esito": "approvato", "richieste": []}

    async def hook(piano):
        stato["richieste"].append(piano)
        return stato["esito"]

    R.set_confirm_hook(hook)
    yield {"ws": ws, "stato": stato, "pubblicati": pubblicati}
    R.set_confirm_hook(None)
    R.clear()


# ── ① la geometria ───────────────────────────────────────────────────────────


class TestLEstrusioneEUnSolido:
    def test_i_conteggi_sono_chiusi(self) -> None:
        """32 vertici e 64 triangoli, sempre: e' cio' che il verificatore usa
        come atteso, e un atteso che cambia con i parametri non e' un atteso."""
        m = estrusione_45()
        assert (m.vertici, len(m.triangoli)) == (VERTICI, TRIANGOLI)
        piccola = estrusione_45(larghezza=40, altezza=30, profondita=3,
                                foro_larghezza=10, foro_altezza=8, smusso_foro=1)
        assert (piccola.vertici, len(piccola.triangoli)) == (VERTICI, TRIANGOLI)

    def test_il_bbox_e_ANALITICO_e_combacia_coi_vertici(self) -> None:
        """§11.10 regola 7. Gli smussi tagliano verso l'interno e non spostano
        gli estremi: qui la regola e' un'uguaglianza, non un «entro il 2 %»."""
        m = estrusione_45(larghezza=120, altezza=80, profondita=12)
        assert m.bbox == (120.0, 80.0, 12.0)
        assert m.bbox_combacia(), (m.bbox, m.bbox_misurato())

    def test_e_un_solido_CHIUSO_con_un_foro_passante(self) -> None:
        """La topologia la conferma `trimesh`, che non e' questo codice.

        `euler_number == 0` e' la firma del genere 1: 32 vertici, 96 spigoli,
        64 triangoli. Un foro cieco darebbe 2, un guscio aperto non sarebbe
        `watertight`.
        """
        import trimesh

        m = estrusione_45()
        t = trimesh.Trimesh(vertices=m.posizioni.astype(np.float64),
                            faces=m.triangoli, process=False)
        assert t.is_watertight, "il solido ha dei buchi nella superficie"
        assert t.euler_number == 0, f"euler {t.euler_number}: il foro non passa"
        assert t.is_winding_consistent, "le normali non sono coerenti"
        assert t.volume > 0, "il solido e' rovesciato: volume negativo"

    def test_il_volume_e_quello_giusto(self) -> None:
        """Controprova indipendente dai vertici: area della sagoma per la
        profondita', calcolata a mano dai parametri.

        Rettangolo meno i quattro triangoli degli smussi, meno il foro (che e'
        la stessa formula con un solo smusso, quattro volte)."""
        import trimesh

        p = dict(DEFAULT)
        area = (p["larghezza"] * p["altezza"]
                - sum(s * s / 2 for s in (p["smusso_bl"], p["smusso_br"],
                                          p["smusso_tr"], p["smusso_tl"]))
                - (p["foro_larghezza"] * p["foro_altezza"]
                   - 4 * p["smusso_foro"] ** 2 / 2))
        m = estrusione_45()
        t = trimesh.Trimesh(vertices=m.posizioni.astype(np.float64),
                            faces=m.triangoli, process=False)
        assert t.volume == pytest.approx(area * p["profondita"], rel=1e-4)

    def test_le_linee_di_costruzione_sono_gli_SPIGOLI_veri(self) -> None:
        """§11.10 regola 3: i profili e le generatrici, non le diagonali della
        triangolazione — che disegnate sopra la faccia sarebbero rumore."""
        m = estrusione_45()
        assert len(m.linee) == 48, "4 profili da 8 piu' 16 generatrici"
        lati = {tuple(sorted(map(int, l))) for l in m.linee}
        assert len(lati) == 48, "una linea e' ripetuta"

    def test_gli_smussi_TUTTI_uguali_si_rifiutano(self) -> None:
        """§11.10 regola 4: l'asimmetria e' progettata. Un pezzo simmetrico non
        e' vietato dalla geometria, e' vietato dal disegno."""
        with pytest.raises(ModelloNonValido, match="asimmetria"):
            estrusione_45(smusso_bl=5, smusso_br=5, smusso_tr=5, smusso_tl=5)

    @pytest.mark.parametrize("parametri,perche", [
        ({"larghezza": -10}, "positiva"),
        ({"profondita": 0}, "positiva"),
        ({"smusso_bl": 100, "smusso_br": 100}, "lato"),
        ({"foro_larghezza": 118}, "parete"),
        ({"foro_larghezza": 10, "foro_altezza": 10, "smusso_foro": 9}, "foro"),
        ({"smusso_bl": -1}, "negativo"),
    ])
    def test_i_parametri_impossibili_si_rifiutano_con_la_RAGIONE(
            self, parametri: dict, perche: str) -> None:
        with pytest.raises(ModelloNonValido, match=perche):
            estrusione_45(**parametri)

    def test_un_parametro_sconosciuto_non_passa(self) -> None:
        """Allowlist anche qui: un nome inventato non diventa un attributo."""
        with pytest.raises(ModelloNonValido, match="sconosciuti"):
            estrusione_45(raggio=10)

    def test_il_tetto_dei_vertici_e_quello_del_GATE(self) -> None:
        """§17.2: oltre il tetto si dice `ok=False`, non si decima in silenzio.
        Il numero e' `LIMITS.maxVertices` del gate del renderer, e questo test
        tiene uguali i due file."""
        sorgente = (RADICE / "ui/src/three/quality-gate.js").read_text(encoding="utf-8")
        n = int(__import__("re").search(r"maxVertices:\s*(\d+)", sorgente).group(1))
        assert MAX_VERTICI == n, f"core {MAX_VERTICI}, gate del renderer {n}"

    def test_un_modello_troppo_grande_si_rifiuta(self) -> None:
        with pytest.raises(ModelloNonValido, match="gate"):
            Modello(nome="x", versione="v1", params={},
                    posizioni=np.zeros((MAX_VERTICI + 1, 3), np.float32),
                    triangoli=np.zeros((1, 3), np.uint32), bbox=(0, 0, 0))

    def test_un_triangolo_che_cita_un_vertice_assente_si_rifiuta(self) -> None:
        with pytest.raises(ModelloNonValido, match="cita il vertice"):
            Modello(nome="x", versione="v1", params={},
                    posizioni=np.zeros((30, 3), np.float32),
                    triangoli=np.array([[0, 1, 99]], np.uint32), bbox=(0, 0, 0))

    def test_un_bbox_che_MENTE_non_si_costruisce(self) -> None:
        """§11.10 regola 7, imposta alla costruzione. Trovato da
        `scripts/orfani.py`: `bbox_combacia` era provata e mai congiunta, e il
        posto in cui serve è questo — il verificatore di ADR-012 userebbe quel
        numero come atteso, e il gate del renderer lo direbbe a file già
        scritto e a conferma già data."""
        with pytest.raises(ModelloNonValido, match="regola 7"):
            Modello(nome="x", versione="v1", params={},
                    posizioni=np.zeros((30, 3), np.float32),
                    triangoli=np.zeros((1, 3), np.uint32), bbox=(99, 0, 0))


# ── ② il lettore GLB, e la sua indipendenza ──────────────────────────────────


class TestIlLettoreEIndipendente:
    def test_NON_importa_trimesh(self) -> None:
        """⚠️ È l'intera ragione per cui questo modulo esiste. Un verificatore
        che rilegge col codice che ha scritto prova che il codice è coerente
        con sé stesso — «il verde è una bugia con due firme»."""
        albero = ast.parse((RADICE / "core/model3d/glb_lettore.py").read_text(encoding="utf-8"))
        importati = set()
        for n in ast.walk(albero):
            if isinstance(n, ast.Import):
                importati |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                importati.add(n.module.split(".")[0])
        assert "trimesh" not in importati, f"importa {sorted(importati)}"
        assert "numpy" not in importati, "nemmeno numpy: bastano struct e json"

    def _glb(self, tmp_path: Path) -> Path:
        from core.tools.model3d import _scrivi_glb

        p = tmp_path / "pezzo.glb"
        _scrivi_glb(estrusione_45(), p)
        return p

    def test_rilegge_quello_che_e_stato_scritto(self, tmp_path: Path) -> None:
        letto = glb_lettore.leggi(self._glb(tmp_path))
        assert letto.versione == 2 and letto.coerente
        assert letto.vertici == VERTICI
        assert letto.dimensioni_mm() == pytest.approx((120.0, 80.0, 12.0), abs=0.01)

    def test_i_parametri_viaggiano_col_pezzo(self, tmp_path: Path) -> None:
        """Chi apre il file fra sei mesi vede da che numeri è nato. Si leggono
        e non si credono: il verificatore usa i `min`/`max` dell'accessor."""
        letto = glb_lettore.leggi(self._glb(tmp_path))
        assert letto.extras["unita_parametri"] == "mm"
        assert letto.extras["params"]["larghezza"] == 120.0

    def test_il_file_e_in_METRI(self, tmp_path: Path) -> None:
        """glTF 2.0 lo prescrive, e un visualizzatore esterno deve vedere il
        pezzo grande quanto è. La conversione sta in un posto solo."""
        letto = glb_lettore.leggi(self._glb(tmp_path))
        assert letto.massimo[0] - letto.minimo[0] == pytest.approx(0.120, abs=1e-5)

    def test_un_file_TRONCATO_non_passa(self, tmp_path: Path) -> None:
        p = self._glb(tmp_path)
        dati = p.read_bytes()
        p.write_bytes(dati[: len(dati) // 2])
        with pytest.raises(glb_lettore.GlbIllegibile):
            glb_lettore.leggi(p)

    def test_una_lunghezza_che_MENTE_si_vede(self, tmp_path: Path) -> None:
        p = self._glb(tmp_path)
        dati = bytearray(p.read_bytes())
        struct.pack_into("<I", dati, 8, len(dati) + 1000)
        p.write_bytes(dati)
        assert glb_lettore.leggi(p).coerente is False

    @pytest.mark.parametrize("contenuto", [b"", b"non un glb", b"glTF" + b"\x00" * 16])
    def test_cio_che_non_e_un_GLB_si_rifiuta(self, tmp_path: Path, contenuto: bytes) -> None:
        p = tmp_path / "finto.glb"
        p.write_bytes(contenuto)
        with pytest.raises(glb_lettore.GlbIllegibile):
            glb_lettore.leggi(p)

    def test_senza_min_e_max_non_si_verifica_niente(self, tmp_path: Path) -> None:
        """Sono obbligatori sull'accessor POSITION per la specifica, ed è la
        ragione per cui GLB è il formato della prima fetta (§17.3)."""
        p = self._glb(tmp_path)
        dati = p.read_bytes()
        lung, _tipo = struct.unpack_from("<II", dati, 12)
        doc = json.loads(dati[20: 20 + lung].decode("utf-8"))
        del doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]["min"]
        testo = json.dumps(doc).encode("utf-8")
        testo += b" " * (-len(testo) % 4)
        nuovo = bytearray(dati[:12])
        nuovo += struct.pack("<II", len(testo), glb_lettore.TIPO_JSON) + testo
        nuovo += dati[20 + lung:]
        struct.pack_into("<I", nuovo, 8, len(nuovo))
        p.write_bytes(nuovo)
        with pytest.raises(glb_lettore.GlbIllegibile, match="POSITION"):
            glb_lettore.leggi(p)


# ── ③ il tool: conferma, file, verdetto ──────────────────────────────────────


class TestIlToolChiedePrimaDiScrivere:
    def test_non_esiste_un_argomento_PATH(self) -> None:
        """Sicurezza strutturale, come `core/tools/introspect.py`: non esiste
        una richiesta che possa nominare un percorso."""
        from core.model3d.tubo import DEFAULT as TUBO

        campi = set(GeneraModelloArgs.model_fields)
        assert not campi & {"path", "destination", "file", "percorso"}, campi
        # I parametri delle due forme, e nient'altro: uno schema che
        # guadagnasse un campo senza un generatore dietro sarebbe una manopola
        # morta, e uno che ne perdesse uno lo renderebbe inarrivabile.
        assert campi == {"forma"} | set(DEFAULT) | set(TUBO), campi

    def test_e_distruttivo_e_NON_e_ammesso_alle_gesture(self, mondo) -> None:
        """Invariante 27, imposto dal registro: una mano non scrive sul disco."""
        d = [t for t in R.describe_all() if t["name"] == "genera_modello"][0]
        assert d["side_effect"] is True and d["gesture_allowed"] is False

    async def test_il_piano_mostra_il_percorso_RISOLTO_e_la_misura(self, mondo) -> None:
        """Invariante 3: l'utente vede dove finisce il file, e quanto è grande
        il pezzo, PRIMA di dire di sì."""
        r = await R.invoke("genera_modello", {"forma": "estrusione_45"})
        assert r.ok, r.error
        piano = mondo["stato"]["richieste"][0]
        op = piano.operazioni[0]
        assert op.destinazione.is_absolute()
        assert op.destinazione.parent == mondo["ws"] / "modelli"
        assert op.destinazione.suffix == ".glb"
        assert "120x80x12 mm" in op.dettaglio and "32 vertici" in op.dettaglio

    async def test_un_RIFIUTO_non_lascia_niente(self, mondo) -> None:
        mondo["stato"]["esito"] = "rifiutato"
        r = await R.invoke("genera_modello", {})
        assert r.ok is False and "rifiutato" in r.error
        assert not list((mondo["ws"] / "modelli").glob("*")) \
            if (mondo["ws"] / "modelli").exists() else True
        assert r.verifica.verdetto is Verdetto.BLOCCATO

    async def test_i_parametri_impossibili_NON_arrivano_alla_conferma(self, mondo) -> None:
        """Il planner genera per davvero, quindi un pezzo che non esiste viene
        rifiutato prima di disturbare una persona."""
        r = await R.invoke("genera_modello", {"foro_larghezza": 119})
        assert r.ok is False and r.error
        assert mondo["stato"]["richieste"] == [], "ha chiesto conferma per un pezzo impossibile"

    async def test_scrive_il_file_e_lo_ANNUNCIA(self, mondo) -> None:
        r = await R.invoke("genera_modello", {"larghezza": 60, "altezza": 40,
                                              "profondita": 6, "foro_larghezza": 20,
                                              "foro_altezza": 12, "smusso_foro": 2})
        assert r.ok, r.error
        p = Path(r.output["path"])
        assert p.is_file() and p.stat().st_size == r.output["bytes"] > 0
        assert r.output["vertici"] == VERTICI and r.output["bbox_mm"] == [60.0, 40.0, 6.0]
        # La catena tool -> socket -> pannello: senza, il file si scrive e non
        # si vede. Stessa forma di `core/tools/web.py`.
        [msg] = mondo["pubblicati"]
        assert msg["topic"] == "model3d.preview" and msg["file"] == str(p)
        assert msg["unita"] == "mm" and msg["vertici"] == VERTICI
        assert msg["bbox"] == {"x": 60.0, "y": 40.0, "z": 6.0}
        assert msg["posizioni_b64"] and msg["indici_b64"] and msg["linee_b64"]

    async def test_la_preview_porta_gli_STESSI_vertici_del_file(self, mondo) -> None:
        """Una sorgente sola: il file è la verità, la preview è una vista dello
        stesso buffer (§17.2)."""
        import base64

        r = await R.invoke("genera_modello", {})
        msg = mondo["pubblicati"][0]
        dal_socket = np.frombuffer(base64.b64decode(msg["posizioni_b64"]),
                                   dtype="<f4").reshape(-1, 3)
        letto = glb_lettore.leggi(Path(r.output["path"]))
        assert len(dal_socket) == letto.vertici
        assert dal_socket.max(axis=0)[0] == pytest.approx(letto.massimo[0] * 1000, abs=0.01)


class TestIlVerificatoreBOCCIA:
    async def test_un_file_giusto_e_RIUSCITO(self, mondo) -> None:
        r = await R.invoke("genera_modello", {})
        assert r.verifica.verdetto is Verdetto.RIUSCITO, r.verifica

    async def test_la_fonte_non_nomina_il_TOOL(self, mondo) -> None:
        """ADR-012, imposto dal registro: un verificatore che nomina il proprio
        tool viene declassato. Qui la fonte è il FORMATO, letto dal disco."""
        r = await R.invoke("genera_modello", {})
        assert "genera_modello" not in r.verifica.fonte
        assert "struct" in r.verifica.fonte and "POSITION" in r.verifica.fonte

    async def test_un_file_TRONCATO_dopo_la_scrittura_e_FALLITO(self, mondo) -> None:
        """⚠️ Il sabotaggio che conta: un verificatore che non ha mai bocciato
        non è un verificatore. Si scrive il file, lo si rompe alle spalle del
        tool, e il verdetto deve smentire l'`ok`."""
        vero = None

        async def scrivi_e_rompi(a, piano):
            nonlocal vero
            vero = await originale(a, piano)
            Path(vero.output["path"]).write_bytes(b"glTF rotto")
            return vero

        strumento = R.get("genera_modello")
        originale = strumento.handler
        object.__setattr__(strumento, "handler", scrivi_e_rompi)
        try:
            r = await R.invoke("genera_modello", {})
        finally:
            object.__setattr__(strumento, "handler", originale)
        assert r.ok is True, "il tool ha creduto di aver scritto"
        assert r.verifica.verdetto is Verdetto.FALLITO, r.verifica
        assert "non si puo' rileggere" in r.verifica.osservato

    async def test_un_pezzo_di_MISURA_diversa_e_FALLITO(self, mondo) -> None:
        """Il caso più insidioso: il file è un GLB valido, ma non è il pezzo
        che era stato chiesto."""
        from core.tools.model3d import _scrivi_glb

        async def scrivi_un_altro(a, piano):
            r = await originale(a, piano)
            _scrivi_glb(estrusione_45(larghezza=200), Path(r.output["path"]))
            return r

        strumento = R.get("genera_modello")
        originale = strumento.handler
        object.__setattr__(strumento, "handler", scrivi_un_altro)
        try:
            r = await R.invoke("genera_modello", {})
        finally:
            object.__setattr__(strumento, "handler", originale)
        assert r.verifica.verdetto is Verdetto.FALLITO
        assert "200.0x80.0x12.0" in r.verifica.osservato

    async def test_un_tool_che_NON_esegue_e_NON_VERIFICATO(self, mondo) -> None:
        """Non `FALLITO`: senza uno stato di partenza non si distingue «non
        fatto» da «fatto e disfatto»."""
        mondo["ws"].joinpath("modelli").mkdir()
        r1 = await R.invoke("genera_modello", {})
        # Lo stesso secondo, lo stesso nome: il tool si rifiuta di sovrascrivere.
        Path(r1.output["path"]).touch()
        strumento = R.get("genera_modello")
        originale = strumento.planner

        async def stesso_nome(a):
            piano = await originale(a)
            from core.tools.confirm import Operazione, Piano

            return Piano(tool=piano.tool, riepilogo=piano.riepilogo,
                         operazioni=(Operazione(tipo="create",
                                                destinazione=Path(r1.output["path"]),
                                                dettaglio="doppione"),))

        object.__setattr__(strumento, "planner", stesso_nome)
        try:
            r = await R.invoke("genera_modello", {})
        finally:
            object.__setattr__(strumento, "planner", originale)
        assert r.ok is False and "esiste gia'" in r.error
        assert r.verifica.verdetto is Verdetto.NON_VERIFICATO


class TestLAllowlistDelleForme:
    def test_ogni_forma_dichiarata_ha_un_generatore_E_dei_conteggi(self) -> None:
        """Invariante 34: l'LLM sceglie un nome, non scrive una geometria. Un
        nome senza conteggi non avrebbe un atteso, cioè non sarebbe
        verificabile."""
        from core.tools.model3d import CONTEGGI

        forme = set(GeneraModelloArgs.model_fields["forma"].annotation.__args__)
        assert forme == set(GENERATORI) == set(CONTEGGI), (forme, set(GENERATORI))

    async def test_una_forma_inventata_non_entra(self, mondo) -> None:
        r = await R.invoke("genera_modello", {"forma": "cubo"})
        assert r.ok is False and "forma" in r.error.lower()
        assert mondo["stato"]["richieste"] == []


# ── ④ il tubo su spline — fetta 2, §17.4 ② ───────────────────────────────────


class TestIlGemello:
    """`segmenti_per` in Python e `segmentsFor()` in JavaScript sono la stessa
    formula in due linguaggi, e §17.2 obbliga ad averle entrambe: il generatore
    vive nel core, il componente che lo incassa nel renderer, e la regola della
    densità è dell'uno e dell'altro.

    Due copie sono due occasioni di sbagliare — «il caso peggiore non è
    scrivere due volte la stessa cosa: è scrivere la seconda **leggermente
    diversa**», `PROTOCOLLO-DI-LAVORO` §3. La cura non è cancellarne una:
    è eseguirle entrambe sugli stessi ingressi.
    """

    #: Gli ingressi, scelti sui punti in cui due implementazioni divergono:
    #: i due estremi del clamp, il raggio che ci cade sopra esatto, l'arco
    #: parziale, la corda diversa dalla predefinita, e un valore che manda
    #: `ceil` a cavallo di un intero.
    CASI = [
        (1.0, None, None), (8.0, None, None), (90.0, None, None),
        (1000.0, None, None), (0.001, None, None),
        (100.0, 1.5707963267948966, None), (100.0, 0.1, None),
        (50.0, 6.283185307179586, 3.0), (50.0, 6.283185307179586, 0.5),
        (12.5, 2.0943951023931953, 1.2),
        # (r*arco)/corda esattamente intero: `ceil` non deve aggiungere uno.
        (12.0 / (2 * 3.141592653589793), 6.283185307179586, 1.0),
        (48.9, 4.71238898038469, 2.7),
    ]

    def test_le_due_implementazioni_DANNO_lo_stesso_numero(self) -> None:
        import json
        import subprocess

        from core.model3d.parametrico import segmenti_per

        casi = [[r, a, c] for r, a, c in self.CASI]
        nostri = [segmenti_per(*[v for v in c if v is not None]) for c in casi]
        codice = """
          import { ParametricComponent } from './ui/src/three/component.js';
          class Prova extends ParametricComponent { build() { return null; } }
          const c = new Prova({ raggio: 1 },
            { name: 'prova', version: 'v1', bbox: { x: 1, y: 1, z: 1 } });
          const casi = JSON.parse(process.argv[1]);
          console.log(JSON.stringify(casi.map(
            ([r, a, ch]) => c.segmentsFor(...[r, a, ch].filter((v) => v !== null)))));
        """
        r = subprocess.run(
            ["node", "--no-warnings", "--input-type=module", "-e", codice,
             "--", json.dumps(casi)],
            cwd=RADICE, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr
        loro = json.loads(r.stdout)
        assert loro == nostri, (
            "le due implementazioni della densità sono divergute:\n"
            + "\n".join(f"  {c} → python {p}, javascript {j}"
                        for c, p, j in zip(casi, nostri, loro, strict=True) if p != j))

    def test_i_due_ESTREMI_sono_gli_stessi(self) -> None:
        """Il clamp è metà della formula: senza, un raggio piccolo darebbe un
        triangolo e uno grande centomila segmenti."""
        import re

        from core.model3d.parametrico import CORDA_MM, SEGMENTI_MAX, SEGMENTI_MIN

        js = (RADICE / "ui/src/three/component.js").read_text(encoding="utf-8")
        riga = re.search(r"Math\.max\((\d+),\s*Math\.min\((\d+),", js)
        assert riga, "la formula in JavaScript è cambiata forma"
        assert (int(riga.group(1)), int(riga.group(2))) == (SEGMENTI_MIN, SEGMENTI_MAX)
        assert f"targetChordMm = {CORDA_MM}" in js, "la corda predefinita è divergente"

    def test_e_il_gemello_e_DICHIARATO_in_tutti_e_due(self) -> None:
        """Una copia che non dice di essere una copia è quella che diverge."""
        py = (RADICE / "core/model3d/parametrico.py").read_text(encoding="utf-8")
        assert "segmentsFor" in py, "il gemello Python non nomina quello JavaScript"


class TestIlTuboEPiegato:
    """⚠️ Qui c'era `TestIlTuboEUnAnello`, e con lui un guscio che e' stato
    BUTTATO. La prima stesura faceva cio' che §17.4 ② dice alla lettera — una
    spline Catmull-Rom chiusa su due armoniche — e la matematica era giusta:
    passava per i punti di controllo a 1,5e-14 mm, il telaio si chiudeva senza
    cucitura, la topologia era un toro. **L'oggetto non era un pezzo**: un
    anello ondulato con misure risultanti invece che di progetto, e
    un'asimmetria che si leggeva come un errore. Il proprietario l'ha respinto
    guardandolo, ed e' §11.7: una violazione si riscrive, non si rattoppa.
    Sta al commit `cd5dbbd`.
    """

    def test_i_conteggi_vengono_dalla_FORMULA_non_dalla_mesh(self) -> None:
        """L'atteso del verificatore: `conteggi_di` applica la regola dei
        segmenti senza spazzare niente, ed è la seconda affermazione
        indipendente sullo stesso numero."""
        from core.model3d.tubo import DEFAULT, conteggi_di, tubo_piegato

        m = tubo_piegato()
        assert (m.vertici, len(m.triangoli)) == conteggi_di(DEFAULT)

    def test_la_densita_viene_dalla_CURVATURA(self) -> None:
        """§11.10 regola 2, e qui la formula ci sta meglio che mai: i raccordi
        sono archi di cerchio veri, cioè esattamente la cosa per cui
        `segmentsFor(raggio, arco)` è nata."""
        from core.model3d.tubo import DEFAULT, lati_di, sezioni_di

        assert lati_di({**DEFAULT, "diametro": 40.0}) > lati_di(DEFAULT)
        assert sezioni_di({**DEFAULT, "corda_mm": 0.5}) > sezioni_di(DEFAULT)
        assert sezioni_di({**DEFAULT, "angolo_1": 170.0}) > sezioni_di(DEFAULT)

    def test_e_un_tubo_CHIUSO_dai_tappi(self) -> None:
        """Il percorso è aperto e i due estremi sono tappati: la superficie è
        di genere zero, `euler_number == 2`. Un anello darebbe 0, e un tubo
        senza tappi non sarebbe `watertight`."""
        import trimesh

        from core.model3d.tubo import tubo_piegato

        m = tubo_piegato()
        t = trimesh.Trimesh(vertices=m.posizioni.astype(np.float64),
                            faces=m.triangoli, process=False)
        assert t.is_watertight and t.euler_number == 2
        assert t.is_winding_consistent and t.volume > 0

    def test_le_corse_sono_DRITTE_e_le_pieghe_a_raggio_costante(self) -> None:
        """La proprietà che distingue un tubo piegato da una curva qualunque:
        fra due raccordi la linea d'asse non curva affatto, e dentro un
        raccordo il raggio non cambia."""
        from core.model3d.tubo import DEFAULT, _percorso

        centri, tangenze = _percorso(DEFAULT)
        # Il primo tratto, dall'origine al primo punto di tangenza.
        dritto = centri[: tangenze[0] + 1]
        d = np.diff(dritto, axis=0)
        versori = d / np.linalg.norm(d, axis=1, keepdims=True)
        assert np.abs(versori - versori[0]).max() < 1e-9, "la corsa non è dritta"

        # Il primo raccordo: tutti i punti a distanza `raggio_piega` dal centro
        # del cerchio, che si ricava da tre punti dell'arco.
        arco = centri[tangenze[0]: tangenze[1] + 1]
        assert len(arco) > 3
        centro = _centro_di_arco(arco[0], arco[len(arco) // 2], arco[-1])
        raggi = np.linalg.norm(arco - centro, axis=1)
        assert np.abs(raggi - DEFAULT["raggio_piega"]).max() < 1e-6, (
            f"il raggio varia fra {raggi.min():.4f} e {raggi.max():.4f}")

    def test_gli_anelli_disegnati_cadono_sulle_TANGENZE(self) -> None:
        """§11.10 regola 3: le uniche circonferenze che un disegno traccia sono
        quelle dove il pezzo smette di essere dritto."""
        from core.model3d.tubo import DEFAULT, _percorso, lati_di, tubo_piegato

        m = tubo_piegato()
        _, tangenze = _percorso(DEFAULT)
        lati = lati_di(DEFAULT)
        sezioni_con_anello = {int(a) // lati for a in m.linee[:, 0]
                              if int(a) < m.vertici - 2}
        assert set(tangenze) <= sezioni_con_anello, sorted(tangenze)

    def test_il_bbox_viene_dalla_TANGENTE_non_dal_raggio_pieno(self) -> None:
        """⚠️ Il presidio di §11.10 regola 7 ha preso la prima stesura con 7,8
        mm di scarto su X. Il disco della sezione sta nel piano perpendicolare
        alla tangente: dove il tubo corre lungo un asse, su quell'asse non
        sporge affatto."""
        from core.model3d.tubo import DEFAULT, _percorso, tubo_piegato

        m = tubo_piegato()
        centri, _ = _percorso(DEFAULT)
        raggio = DEFAULT["diametro"] / 2
        ingenuo = (centri.max(axis=0) + raggio) - (centri.min(axis=0) - raggio)
        assert m.bbox[0] < ingenuo[0] - 1.0, (
            "il bbox coincide con «linea d'asse più raggio», che è troppo largo")
        for dichiarato, misurato in zip(m.bbox, m.bbox_misurato(), strict=True):
            assert misurato <= dichiarato + 0.01
            assert dichiarato - misurato <= m.tolleranza_mm + 0.01

    def test_il_raggio_di_piega_SEGUE_il_diametro(self) -> None:
        """Su una piegatrice la matrice si sceglie per il tubo. Trovato
        provando la frase vera: «fammi un tubo da 20 millimetri» falliva con
        «sotto 1,5 diametri il tubo si schiaccia», perché il diametro cambiava
        e il raggio restava quello del tubo predefinito."""
        from core.model3d.tubo import PIEGA_SU_DIAMETRO, tubo_piegato

        m = tubo_piegato(diametro=20.0)
        assert m.params["raggio_piega"] == 20.0 * PIEGA_SU_DIAMETRO
        # E chi lo chiede esplicitamente lo ottiene: 35 non è due diametri, e
        # lascia posto alle tangenti su tutte e tre le pieghe.
        assert tubo_piegato(diametro=20.0, raggio_piega=35.0).params["raggio_piega"] == 35.0

    def test_una_tolleranza_SENZA_ragione_non_si_costruisce(self) -> None:
        with pytest.raises(ModelloNonValido, match="allentato in silenzio"):
            Modello(nome="x", versione="v1", params={"a": 1.0},
                    posizioni=np.zeros((30, 3), np.float32),
                    triangoli=np.zeros((1, 3), np.uint32), bbox=(0, 0, 0),
                    tolleranza_mm=5.0)

    def test_un_bbox_piu_PICCOLO_dei_vertici_resta_un_errore(self) -> None:
        """La tolleranza vale in un verso solo: un poligono inscritto sta
        DENTRO il cerchio, mai fuori."""
        from core.model3d.tubo import tubo_piegato

        m = tubo_piegato()
        with pytest.raises(ModelloNonValido, match="regola 7"):
            Modello(nome="x", versione="v1", params=m.params,
                    posizioni=m.posizioni, triangoli=m.triangoli,
                    bbox=(m.bbox[0] - 5.0, m.bbox[1], m.bbox[2]),
                    tolleranza_mm=m.tolleranza_mm, motivo_tolleranza="prova")

    @pytest.mark.parametrize("parametri,perche", [
        ({"diametro": 0}, "positivo"),
        ({"corsa_2": 0}, "positiva"),
        ({"angolo_1": 180}, "fra 0 e 180"),
        ({"rotazione_2": 400}, "fra -180 e 180"),
        ({"raggio_piega": 10}, "si schiaccia"),
        ({"corsa_3": 20}, "tratto dritto sparirebbe"),
    ])
    def test_i_parametri_impossibili_si_rifiutano_con_la_RAGIONE(
            self, parametri: dict, perche: str) -> None:
        from core.model3d.tubo import tubo_piegato

        with pytest.raises(ModelloNonValido, match=perche):
            tubo_piegato(**parametri)

    def test_corse_e_angoli_tutti_uguali_si_rifiutano(self) -> None:
        """§11.10 regola 4, come i quattro smussi della piastra: una spirale
        regolare non è un'asimmetria progettata."""
        from core.model3d.tubo import tubo_piegato

        with pytest.raises(ModelloNonValido, match="asimmetria"):
            tubo_piegato(corsa_1=80, corsa_2=80, corsa_3=80, corsa_4=80,
                         angolo_1=90, angolo_2=90, angolo_3=90)


def _centro_di_arco(a, b, c):
    """Il centro del cerchio per tre punti nello spazio. Serve a misurare che
    un raccordo abbia raggio COSTANTE senza chiederlo al generatore."""
    ab, ac = b - a, c - a
    n = np.cross(ab, ac)
    return a + np.cross(float(ab @ ab) * ac - float(ac @ ac) * ab, n) / (2 * float(n @ n))


class TestLeQuoteLeSceglieIlGENERATORE:
    """⚠️ Questa classe nasce da una bocciatura che non ha trovato NIENTE da
    fare: sabotando le quote nel messaggio, `pytest -k quote` ha deselezionato
    tutti e 63 i test. Il meccanismo era costruito e non sorvegliato.

    E nasce da un difetto visto guardando lo scatto: il pannello annotava
    sempre i tre lati del bounding box, e su un tubo piegato quei tre numeri
    sono un RISULTATO — 177,6 x 113,1 x 153,6 — appesi ad angoli che stanno
    nel vuoto. Un disegno di un tubo scrive Ø12 e R24.
    """

    def test_ogni_forma_dell_allowlist_DICHIARA_le_sue_quote(self) -> None:
        """La stessa forma di `FRASI` nel risveglio: chi aggiunge un
        generatore e scorda le quote lascia un pezzo senza una misura, e senza
        questo test se ne accorgerebbe soltanto guardandolo."""
        for nome, genera in GENERATORI.items():
            m = genera()
            assert m.quote, f"{nome} non dichiara nessuna quota (§11.10 regola 3)"
            for q in m.quote:
                assert q.testo.strip(), nome
                assert len(q.punto) == 3, nome

    def test_le_quote_del_TUBO_sono_di_progetto_non_di_risultato(self) -> None:
        """Ø e R sono i numeri che si ordinano; l'ingombro è ciò che ne esce."""
        from core.model3d.tubo import DEFAULT, tubo_piegato

        m = tubo_piegato()
        testi = [q.testo for q in m.quote]
        assert any(t.startswith("\u00d8") for t in testi), testi
        assert any(t.startswith("R") for t in testi), testi
        # Nessuna quota ripete un lato dell'ingombro, che è un risultato.
        for lato in m.bbox:
            assert not any(f"{lato:.1f}" in t for t in testi), (lato, testi)
        # E i due numeri detti sono quelli chiesti.
        assert f"\u00d8{DEFAULT['diametro']:g}" in testi
        assert f"R{m.params['raggio_piega']:g}" in testi

    def test_le_quote_della_PIASTRA_sono_i_suoi_tre_lati(self) -> None:
        """Sulla piastra il bbox È il pezzo, e i tre lati sono di progetto: gli
        smussi tagliano verso l'interno e non spostano gli estremi."""
        m = estrusione_45()
        testi = [q.testo for q in m.quote]
        for lato in m.bbox:
            assert f"{lato:g} mm" in testi, (lato, testi)
        assert any("foro" in t for t in testi), testi

    def test_le_quote_ARRIVANO_al_renderer(self) -> None:
        m = estrusione_45()
        msg = m.per_il_renderer()
        assert len(msg["quote"]) == len(m.quote)
        assert msg["quote"][0]["testo"] == m.quote[0].testo
        assert len(msg["quote"][0]["punto"]) == 3

    def test_il_PANNELLO_non_le_sceglie_piu(self) -> None:
        """Il renderer non può sapere quali misure contano su un pezzo che non
        ha generato: le proietta e basta."""
        js = (RADICE / "ui/src/panels/modello.js").read_text(encoding="utf-8")
        assert "corrente.quote" in js
        codice = "\n".join(r for r in js.splitlines()
                            if not r.lstrip().startswith(("*", "/*", "//")))
        assert "meta.bbox" not in codice.split("function piede", 1)[0].split(
            "for (const q of", 1)[-1], (
            "il pannello legge ancora il bounding box per le quote")


class TestLeDueFormeConvivono:
    async def test_entrambe_arrivano_al_DISCO_e_al_verdetto(self, mondo) -> None:
        from core.model3d.tubo import DEFAULT as TUBO
        from core.tools.model3d import CONTEGGI

        for forma in ("estrusione_45", "tubo_piegato"):
            r = await R.invoke("genera_modello", {"forma": forma})
            assert r.ok, (forma, r.error)
            assert r.verifica.verdetto is Verdetto.RIUSCITO, (forma, r.verifica)
            letto = glb_lettore.leggi(Path(r.output["path"]))
            assert letto.vertici == r.output["vertici"]
        assert CONTEGGI["tubo_piegato"](TUBO)[0] > 1000, "il tubo è denso, e va provato denso"

    async def test_un_parametro_dell_ALTRA_forma_si_rifiuta(self, mondo) -> None:
        """Non si filtra per forma: ignorare in silenzio ciò che qualcuno ha
        chiesto è lo stesso difetto che `extra="forbid"` chiude più su."""
        r = await R.invoke("genera_modello", {"forma": "tubo_piegato", "larghezza": 50})
        assert r.ok is False and "larghezza" in r.error
        assert mondo["stato"]["richieste"] == []

    async def test_la_TOLLERANZA_del_tubo_arriva_al_renderer(self, mondo) -> None:
        """Senza, il gate del renderer boccerebbe il tubo per una
        discretizzazione che il core ha già calcolato in forma chiusa."""
        await R.invoke("genera_modello", {"forma": "tubo_piegato"})
        msg = mondo["pubblicati"][0]
        assert msg["bbox_tolleranza"] > 0 and msg["motivo_tolleranza"]
        await R.invoke("genera_modello", {"forma": "estrusione_45"})
        assert mondo["pubblicati"][1]["bbox_tolleranza"] == 0, (
            "una piastra non ha niente da derogare: il suo bbox è esatto")
