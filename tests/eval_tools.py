"""EVAL — ogni tool dell'allowlist, su input validi e invalidi (§22).

Due proprieta' che valgono per TUTTI i tool, presenti e futuri, e che i test
scritti a mano tool per tool smettono di coprire appena qualcuno ne aggiunge
uno: l'eval li scopre dal registro.

1. **Nessuno solleva mai.** Il `CLAUDE.md` lo impone: le anomalie tornano come
   `ToolResult(ok=False, error=...)`, perche' un'eccezione che risale
   arriverebbe all'LLM come un guasto invece che come un esito.
2. **Nessun tool distruttivo esegue senza conferma.**
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from core.tools import registry as R
from core.tools.files import register_file_tools
from core.tools.system import register_system_tools
from tests.conftest import FakeSensors


class FakeFS:
    def __init__(self, roots): self.allowed_roots = roots
    trash_only = True


class FakeSettings:
    def __init__(self, roots): self.fs = FakeFS(roots)


@pytest.fixture
def mondo(tmp_path: Path):
    """Allowlist completa su una radice temporanea, con conferma controllabile."""
    radice = (tmp_path / "radice").resolve()
    (radice / "sotto").mkdir(parents=True)
    (radice / "documento.txt").write_text("contenuto di prova")
    (radice / "immagine.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)

    R.clear()
    register_system_tools(FakeSensors())
    register_file_tools(lambda: FakeSettings([radice]))

    stato = {"esito": "approvato", "richieste": []}

    async def hook(piano):
        stato["richieste"].append(piano)
        return stato["esito"]

    R.set_confirm_hook(hook)
    return {"radice": radice, "stato": stato, "fuori": tmp_path / "fuori"}


#: Argomenti INVALIDI per ogni tool: tipo sbagliato, campo mancante, percorso
#: fuori radice, valore fuori intervallo. Nessuno deve sollevare.
def _argomenti_invalidi(radice: Path, fuori: Path) -> list[tuple[str, dict]]:
    return [
        ("list_dir", {}),                                  # campo mancante
        ("list_dir", {"path": 12345}),                     # tipo sbagliato
        ("list_dir", {"path": str(fuori)}),                # fuori radice
        ("list_dir", {"path": str(radice / "..")}),        # traversal
        ("list_dir", {"path": "x\x00y"}),                  # byte NUL
        ("read_file", {"path": str(radice)}),              # e' una directory
        ("read_file", {"path": str(radice / "documento.txt"), "max_bytes": 0}),
        ("read_file", {"path": str(radice / "documento.txt"), "max_bytes": 10**12}),
        ("search_files", {"query": ""}),                   # vuota
        ("search_files", {"query": "x", "limit": 99999}),
        ("stat_path", {"path": str(radice / "nonesiste")}),
        ("create_file", {"path": str(fuori / "x.txt")}),
        ("create_file", {"path": str(radice / "documento.txt")}),   # esiste gia'
        ("create_folder", {"path": str(radice / "sotto")}),         # esiste gia'
        ("move_path", {"source": str(radice / "nonesiste"), "destination": str(radice / "b")}),
        ("move_path", {"source": str(radice / "documento.txt"), "destination": str(fuori / "b")}),
        ("copy_path", {"source": str(fuori / "a"), "destination": str(radice / "b")}),
        ("trash_path", {"path": str(radice)}),             # e' una radice
        ("trash_path", {"path": str(radice / "nonesiste")}),
        ("organize_folder", {"path": str(radice / "documento.txt")}),  # non e' una dir
        ("organize_folder", {"path": str(fuori)}),
    ]


class TestNessunoSolleva:
    async def test_input_invalidi(self, mondo) -> None:
        """La proprieta' che conta: qualunque input, nessuna eccezione."""
        for nome, args in _argomenti_invalidi(mondo["radice"], mondo["fuori"]):
            try:
                r = await R.invoke(nome, args)
            except Exception as exc:                      # noqa: BLE001
                pytest.fail(f"{nome}({args}) ha sollevato {type(exc).__name__}: {exc}")
            assert r.ok is False, f"{nome}({args}) doveva fallire e invece e' riuscito"
            assert r.error, f"{nome} ha fallito senza dire perche'"

    async def test_ogni_tool_e_coperto(self, mondo) -> None:
        """Un eval che dimentica un tool non protegge quel tool."""
        coperti = {n for n, _ in _argomenti_invalidi(mondo["radice"], mondo["fuori"])}
        di_file = {n for n in R.names() if n not in {"system_status", "top_processes"}}
        assert di_file <= coperti, f"tool senza casi invalidi: {sorted(di_file - coperti)}"


class TestInputValidi:
    async def test_lettura(self, mondo) -> None:
        r = await R.invoke("list_dir", {"path": str(mondo["radice"])})
        assert r.ok and r.output["totale"] == 3

        r = await R.invoke("read_file", {"path": str(mondo["radice"] / "documento.txt")})
        assert r.ok and "contenuto di prova" in r.output["content"]

        r = await R.invoke("search_files", {"query": "documento"})
        assert r.ok and r.output["totale"] == 1

        r = await R.invoke("stat_path", {"path": str(mondo["radice"] / "immagine.png")})
        assert r.ok and r.output["categoria"] == "Immagini"

    async def test_una_pagina_web_e_codice(self, mondo) -> None:
        """`.html` stava in «Altro» accanto a `.js` in «Codice», e sono la
        stessa cosa: sorgenti che qualcuno ha scritto.

        Visto sul pannello file di §13 con una cartella vera — quattro `.html`
        etichettati «Altro» sotto gli occhi — non ragionando sull'elenco.
        """
        from pathlib import Path as _P

        from core.tools.files import categoria

        for nome in ("pagina.html", "pagina.htm", "stile.css",
                     "geo-map.js", "core.py", "settings.toml"):
            assert categoria(_P(nome)) == "Codice", nome
        # E cio' che codice non e' non ci finisce dentro per errore.
        assert categoria(_P("appunti.md")) == "Documenti"
        assert categoria(_P("logo.svg")) == "Immagini"
        assert categoria(_P("ignoto.xyz")) == "Altro"

    async def test_scrittura_con_conferma(self, mondo) -> None:
        nuovo = mondo["radice"] / "nuovo.txt"
        r = await R.invoke("create_file", {"path": str(nuovo), "content": "ciao"})
        assert r.ok and nuovo.read_text() == "ciao"
        assert len(mondo["stato"]["richieste"]) == 1


class TestContenutoNonFidato:
    async def test_read_file_marca_la_sorgente(self, mondo) -> None:
        """Invariante 5. La marcatura nasce qui: aggiungerla dopo vorrebbe dire
        rintracciare tutti i consumatori."""
        r = await R.invoke("read_file", {"path": str(mondo["radice"] / "documento.txt")})
        assert r.output["untrusted"] is True
        assert r.output["content"].startswith("<untrusted_source")
        assert r.output["content"].rstrip().endswith("</untrusted_source>")


class TestConfermaSuOgniDistruttivo:
    async def test_nessun_distruttivo_esegue_su_rifiuto(self, mondo) -> None:
        """La proprieta' generale, su tutta l'allowlist reale."""
        mondo["stato"]["esito"] = "rifiutato"
        radice = mondo["radice"]
        casi = {
            "create_file": {"path": str(radice / "mai.txt"), "content": "x"},
            "create_folder": {"path": str(radice / "mai")},
            "move_path": {"source": str(radice / "documento.txt"),
                          "destination": str(radice / "spostato.txt")},
            "copy_path": {"source": str(radice / "documento.txt"),
                          "destination": str(radice / "copia.txt")},
            "trash_path": {"path": str(radice / "documento.txt")},
            "organize_folder": {"path": str(radice)},
        }
        for nome in (n for n in R.names() if R.get(n).side_effect):
            assert nome in casi, f"{nome} non e' coperto da questo eval"
            r = await R.invoke(nome, casi[nome])
            assert r.ok is False and "rifiutat" in r.error

        # e nulla e' cambiato sul disco
        assert (radice / "documento.txt").exists()
        assert not (radice / "mai.txt").exists()
        assert not (radice / "spostato.txt").exists()
        assert not (radice / "copia.txt").exists()

    async def test_il_piano_mostra_percorsi_risolti(self, mondo) -> None:
        """§6.2: all'utente si mostra il path RISOLTO, non quello richiesto."""
        piano = await R.pianifica(
            "trash_path", {"path": str(mondo["radice"] / "sotto" / ".." / "documento.txt")}
        )
        mostrato = piano.operazioni[0].sorgente
        assert ".." not in str(mostrato)
        assert mostrato == mondo["radice"] / "documento.txt"


class TestRevisioneDiSicurezza:
    """Le tre falle trovate rivedendo la Fase 2, e i test che le bloccano.

    Non sono ipotesi: ognuna e' stata riprodotta prima di essere corretta.
    """

    async def test_copiare_una_cartella_non_materializza_i_symlink(self, mondo) -> None:
        """FALLA. `shutil.copytree` col default `symlinks=False` DEREFERENZIA i
        symlink dentro l'albero: un link a `/etc/hostname` diventava un file
        vero, col contenuto materializzato dentro una radice consentita.

        La validazione dei percorsi non la intercetta, perche' il percorso
        copiato e' legittimo: e' il CONTENUTO ad arrivare da fuori.
        """
        radice = mondo["radice"]
        (radice / "cartella").mkdir()
        (radice / "cartella" / "esca").symlink_to("/etc/hostname")

        r = await R.invoke("copy_path", {
            "source": str(radice / "cartella"),
            "destination": str(radice / "copiata"),
        })
        assert r.ok, r.error
        copiato = radice / "copiata" / "esca"
        assert copiato.is_symlink(), "il link e' stato materializzato in un file vero"
        assert not copiato.resolve().is_relative_to(radice), "contenuto esterno importato"

    async def test_read_file_non_carica_tutto_il_file(self, mondo) -> None:
        """FALLA. `read_bytes()[:n]` legge il file INTERO e poi taglia: il
        tetto non proteggeva da nulla. Su un file grande il core si ferma
        mentre lo ingoia."""
        grande = mondo["radice"] / "grande.bin"
        grande.write_bytes(b"A" * (4 * 1024 * 1024))

        r = await R.invoke("read_file", {"path": str(grande), "max_bytes": 1024})
        assert r.ok
        assert r.output["bytes"] == 1024
        assert r.output["troncato"] is True

    async def test_un_percorso_sostituito_dopo_la_conferma_ferma_l_operazione(
        self, mondo
    ) -> None:
        """FALLA parziale. Fra la conferma e l'esecuzione possono passare due
        minuti. Se il percorso approvato diventa un symlink verso l'esterno,
        l'utente ha letto e approvato una cosa e ne accadrebbe un'altra.

        Il controllo non chiude del tutto la finestra — resta un istante fra
        verifica e chiamata di sistema — ma la riduce da minuti a microsecondi.
        """
        radice = mondo["radice"]
        bersaglio = radice / "innocuo.txt"
        bersaglio.write_text("x")

        piano = await R.pianifica("trash_path", {"path": str(bersaglio)})

        # Il mondo cambia sotto: il file approvato diventa un link all'esterno.
        bersaglio.unlink()
        bersaglio.symlink_to("/etc/hostname")

        tool = R.get("trash_path")
        r = await tool.handler(None, piano)
        assert r.ok is False and "non e' piu' valido" in r.error
        assert Path("/etc/hostname").exists(), "ha toccato il bersaglio del link"
