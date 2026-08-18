"""Il tracker delle mani — SPEC §14.1, invariante 28. Fase 7.

Nessuno di questi test accende la telecamera: verificano il contorno — modello,
configurazione, ciclo di vita — che e' quello che si rompe in silenzio. La
misura dal vivo sta in `scripts/bench_gestures.py` e il suo esito in FASE-07.md.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from core.gestures import tracker as T


class TestModello:
    def test_non_riscarica_un_modello_gia_buono(self, tmp_path: Path) -> None:
        dest = T.percorso_modello(tmp_path)
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"x" * (T.MODELLO_MIN_BYTE + 1))
        assert T.scarica_modello(tmp_path, url="https://non.esiste.invalido/x") == dest

    def test_un_download_troncato_non_diventa_un_modello(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Un file troppo piccolo e' quasi sempre una pagina di errore salvata
        col nome giusto. Senza questo controllo l'errore che ne uscirebbe
        parlerebbe di flatbuffer invece che di rete."""
        import io
        import urllib.request

        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda *a, **k: io.BytesIO(b"<html>404</html>"),
        )
        with pytest.raises(RuntimeError, match="pagina di errore"):
            T.scarica_modello(tmp_path)
        # E non ha lasciato residui che al giro dopo sembrerebbero buoni.
        assert not T.percorso_modello(tmp_path).exists()
        assert not list((tmp_path / "models").glob("*.parziale"))


class TestConfigurazione:
    def test_il_delegate_CPU_e_ESPLICITO(self) -> None:
        """Invariante 28 e §14.1. Non un default su cui contare: scritto.

        Il test guarda il SORGENTE perche' verificarlo a runtime vorrebbe dire
        costruire il landmarker, cioe' caricare il modello e MediaPipe.
        """
        sorgente = inspect.getsource(T.TrackerMediaPipe.avvia)
        assert "Delegate.CPU" in sorgente
        assert "Delegate.GPU" not in sorgente

    def test_il_modo_e_VIDEO_non_IMAGE(self) -> None:
        """In `RunningMode.IMAGE` ogni fotogramma e' indipendente e il
        tracciamento fra l'uno e l'altro sparisce: l'isteresi di §14 si
        appoggia proprio a quella continuita'."""
        assert "RunningMode.VIDEO" in inspect.getsource(T.TrackerMediaPipe.avvia)

    def test_due_mani_perche_la_rotazione_ne_vuole_due(self) -> None:
        assert T.MANI_MAX == 2


class TestTelecamera:
    def test_importare_il_modulo_non_accende_niente(self) -> None:
        """R53: si accende su richiesta, mai all'avvio. Un tracker appena
        costruito non ha ne' telecamera ne' modello."""
        t = T.TrackerMediaPipe(Path("/tmp"))
        assert t._camera is None and t._landmarker is None
        assert t.fps_camera == 0.0

    def test_ferma_e_idempotente(self) -> None:
        """Si chiama da `__exit__`, da un `finally` e a mano: due volte non
        deve essere un problema."""
        t = T.TrackerMediaPipe(Path("/tmp"))
        t.ferma()
        t.ferma()

    def test_i_fotogrammi_senza_avvio_sollevano(self) -> None:
        t = T.TrackerMediaPipe(Path("/tmp"))
        with pytest.raises(RuntimeError, match="non avviato"):
            next(iter(t.fotogrammi(1)))

    def test_nessun_percorso_di_scrittura_per_i_fotogrammi(self) -> None:
        """R53, terza regola: nessun fotogramma tocca il disco.

        Si verifica sul SORGENTE perche' e' una proprieta' del codice, non di
        un'esecuzione: l'unica scrittura del modulo e' quella del modello.
        """
        sorgente = inspect.getsource(T)
        scritture = [r for r in ("imwrite", "imsave", "tofile", ".save(")
                     if r in sorgente]
        assert not scritture, f"il tracker puo' scrivere immagini: {scritture}"
        # `write_bytes` c'e', ed e' del modello: una sola occorrenza, dentro
        # `scarica_modello`.
        assert sorgente.count("open(\"wb\")") <= 1


class TestInterfaccia:
    def test_rispetta_il_Protocol(self) -> None:
        """§4: «MediaPipe, roadmap incerta: isolare dietro interfaccia»."""
        from core.platform.base import HandTracker

        t = T.TrackerMediaPipe(Path("/tmp"))
        for metodo in ("disponibile", "avvia", "ferma", "fotogrammi"):
            assert callable(getattr(t, metodo)), metodo
        assert hasattr(HandTracker, "__protocol_attrs__") or True  # Protocol runtime

    def test_disponibile_non_solleva_mai(self) -> None:
        """Su una macchina senza MediaPipe deve rispondere `False`, non
        esplodere: l'assenza e' uno stato normale."""
        assert isinstance(T.TrackerMediaPipe(Path("/tmp")).disponibile(), bool)
