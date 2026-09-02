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
        campi = set(GeneraModelloArgs.model_fields)
        assert not campi & {"path", "destination", "file", "percorso"}, campi
        assert campi == {"forma"} | set(DEFAULT), campi

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
        assert "200x80x12" in r.verifica.osservato

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
