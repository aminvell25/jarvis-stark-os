"""I tre orfani che restavano dopo la scansione, e che erano difetti veri.

La scansione di `core/` ne aveva trovati 22; diciannove erano callback di
libreria, metodi chiamati per attributo o classi di protocollo. Tre no:

1. `Governor.riprendi` — la sospensione scadeva da sola, ma **la ripresa era
   muta**: §16 dice che nessuna soglia agisce senza annunciarlo, e qui la metà
   che annuncia il guasto c'era mentre quella che annuncia il ritorno no;
2. `GpuScheduler.can_admit` — §16 riga VRAM, «headroom insufficiente → rifiuta
   il caricamento», non era imposta da nessuno;
3. `gestures.emetti` — «l'unica uscita delle gesture verso il resto del
   sistema», dice il suo docstring, e nessuno la chiamava: la catena c'era
   tutta e non aveva un capo.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from core.llm.governor import Governor


def _engine_src() -> str:
    return (Path(__file__).resolve().parent.parent / "core" / "engine.py"
            ).read_text(encoding="utf-8")


class TestLaRipresaSIANNUNCIA:
    """Un'asimmetria fra il dire che qualcosa è rotto e il dire che è tornato a
    posto è peggio del silenzio su entrambi: la prima metà insegna a fidarsi
    degli advisory, la seconda tradisce quella fiducia."""

    def test_prima_il_guasto_poi_il_RITORNO(self) -> None:
        avvisi: list[dict] = []
        g = Governor(su_advisory=avvisi.append)

        g.sospendi(0.02, "rate_limit")
        assert [a["reason"] for a in avvisi] == ["t2_sospeso: rate_limit"]
        assert g.sospeso is True

        time.sleep(0.03)
        g.stato()
        assert g.sospeso is False
        assert [a["reason"] for a in avvisi][-1] == "t2_ripreso"

    def test_lo_dice_UNA_volta_sola(self) -> None:
        """Lo snapshot chiama `stato()` a 2,5 Hz: un advisory ogni 400 ms
        sarebbe rumore, non informazione."""
        avvisi: list[dict] = []
        g = Governor(su_advisory=avvisi.append)
        g.sospendi(0.02, "rate_limit")
        time.sleep(0.03)
        for _ in range(20):
            g.stato()
        assert sum(1 for a in avvisi if a["reason"] == "t2_ripreso") == 1

    def test_lo_dice_anche_SENZA_scrivania(self) -> None:
        """Un core senza renderer collegato non chiama `stato()`: la ripresa
        resterebbe muta fino a un `stato()` che non arriva mai."""
        avvisi: list[dict] = []
        g = Governor(su_advisory=avvisi.append)
        g.sospendi(0.02, "rate_limit")
        time.sleep(0.03)
        g.puo_spawnare()
        assert any(a["reason"] == "t2_ripreso" for a in avvisi)

    def test_finche_e_sospeso_NON_annuncia_il_ritorno(self) -> None:
        avvisi: list[dict] = []
        g = Governor(su_advisory=avvisi.append)
        g.sospendi(60.0, "rate_limit")
        for _ in range(5):
            g.stato()
        assert not any(a["reason"] == "t2_ripreso" for a in avvisi)


class TestLaVRAM:
    """§16 riga VRAM. ⚠️ Il verbo «rifiuta» oggi non ha un oggetto: nel core
    niente si carica sulla GPU — l'invariante 11 vieta i modelli LLM locali e
    §9 elenca Vosk, Kokoro, MediaPipe e Tesseract tutti su CPU. L'unico
    consumatore è la scena, che vive nel renderer. Ciò che il core può fare, e
    che §16 chiede a **ogni** soglia, è annunciare."""

    def test_la_soglia_viene_da_9_e_non_da_me(self) -> None:
        from core.engine import VRAM_SCENA

        assert VRAM_SCENA == 1024 * 2**20, (
            "§9 stima la scena «~1-2 GB (stima prudenziale)»: si prende il "
            "limite inferiore, perché sotto non ci sta di sicuro e l'avviso "
            "non è mai un falso allarme"
        )

    def test_lo_snapshot_la_CONTROLLA(self) -> None:
        s = _engine_src()
        assert "self._controlla_vram()" in s
        assert "self._gpu_scheduler.can_admit(VRAM_SCENA)" in s

    def _engine_finto(self, libera: int):
        from core.engine import Engine
        from core.gpu_scheduler import GpuScheduler
        from core.platform.base import GpuMemory

        class _Gpu:
            def memory(self):
                # `free` e' derivata: total - used. Un finto che la passasse
                # per argomento misurerebbe una GpuMemory che non esiste.
                return GpuMemory(total=8 * 2**30, used=8 * 2**30 - libera,
                                 driver="finto", unified=False)

        e = Engine.__new__(Engine)
        e._gpu_scheduler = GpuScheduler(_Gpu(), None)
        e._vram_scarsa = False
        e.avvisi = []
        e._advisory_sincrono = e.avvisi.append
        return e

    def test_sotto_la_soglia_ANNUNCIA(self) -> None:
        e = self._engine_finto(200 * 2**20)
        e._controlla_vram()
        assert e.avvisi and e.avvisi[0]["reason"] == "vram_insufficiente"
        assert e.avvisi[0]["mancano_byte"] > 0, (
            "un rifiuto che non dice quanto mancava è inservibile"
        )

    def test_sopra_la_soglia_TACE(self) -> None:
        e = self._engine_finto(6 * 2**30)
        e._controlla_vram()
        assert e.avvisi == []

    def test_annuncia_sul_CAMBIO_e_non_a_2_5_Hz(self) -> None:
        e = self._engine_finto(200 * 2**20)
        for _ in range(10):
            e._controlla_vram()
        assert len(e.avvisi) == 1

    def test_e_annuncia_anche_il_RITORNO(self) -> None:
        """La stessa lezione di `Governor.riprendi`, applicata subito."""
        e = self._engine_finto(200 * 2**20)
        e._controlla_vram()
        e._gpu_scheduler = self._engine_finto(6 * 2**30)._gpu_scheduler
        e._controlla_vram()
        assert [a["reason"] for a in e.avvisi] == ["vram_insufficiente", "vram_tornata"]


class TestLeGESTURE_hanno_un_capo:
    def test_la_radice_le_ACCENDE_e_le_ferma(self) -> None:
        s = _engine_src()
        assert "self._accendi_gesture()" in s
        dopo = s.split("async def _spegni_gradi", 1)[1].split("\n    async def", 1)[0]
        assert "self._compito_gesture.cancel()" in dopo

    def test_solo_con_vision_ENABLED(self) -> None:
        """`settings.toml` lo dice: «il consenso migliore è non accenderla»."""
        s = _engine_src()
        assert "if s.vision.enabled:\n            self._accendi_gesture()" in s

    def test_mediapipe_assente_e_uno_STATO_annunciato(self) -> None:
        s = _engine_src()
        dopo = s.split("def _accendi_gesture", 1)[1].split("\n    async def _gira", 1)[0]
        assert 'grado="gesture", mediapipe=False' in dopo
        assert "return" in dopo

    def test_l_intento_passa_da_EMETTI_e_non_da_esegui_t0(self) -> None:
        """`emetti()` usa `invoke_da_gesture()`, fail-closed sull'invariante
        27. Passare da `esegui_t0` vorrebbe dire che una mano può fare ciò che
        una frase può fare, e §14 dice il contrario."""
        s = _engine_src()
        dopo = s.split("def _gesture_intento", 1)[1].split("\n    def _controlla_vram", 1)[0]
        assert "await emetti(intento" in dopo
        # (0) Non `"esegui_t0" not in dopo`: il docstring la NOMINA per dire
        # che non ci passa, e un test che cercasse la stringa nuda sarebbe
        # rosso per il commento invece che per il codice.
        codice = [r for r in dopo.splitlines()
                  if "esegui_t0" in r and "`esegui_t0`" not in r
                  and not r.strip().startswith("#")]
        assert codice == [], codice

    async def test_il_giro_dal_FOTOGRAMMA_all_intento(self) -> None:
        """La catena intera con un tracker finto: è ciò che nessuno aveva mai
        fatto girare."""
        from core.engine import Engine
        from core.gestures.mapping import FRAME_ISTERESI
        from core.gestures.tracker import Fotogramma, Mano

        # Una mano col palmo aperto, ferma: §14 la mappa su `espandi_pannello`.
        #
        # ⚠️ Il primo finto dava `sposta_pannello`: pollice e indice erano
        # nello stesso punto, quindi `pizzico()` era vero e vince sull'ordine.
        # Una mano finta va costruita guardando le soglie, non a occhio.
        punti = [(0.5, 0.9, 0.0)] * 21
        punti[0] = (0.5, 0.9, 0.0)                       # POLSO
        for idx in (2, 5, 9, 13, 17):                    # NOCCHE, sopra il polso
            punti[idx] = (0.5, 0.7, 0.0)
        for idx in (8, 12, 16, 20):                      # PUNTE, molto più su
            punti[idx] = (0.5, 0.1, 0.0)
        punti[4] = (0.3, 0.1, 0.0)                       # POLLICE, di lato

        emessi: list[dict] = []

        class _Ws:
            async def broadcast(self, msg):
                emessi.append(msg)

        e = Engine.__new__(Engine)
        e._ws = _Ws()
        e._compiti = set()

        class _Tracker:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def fotogrammi(self, quanti=None):
                for i in range(FRAME_ISTERESI + 2):
                    yield Fotogramma(indice=i,
                                     mani=[Mano(lato="Right",
                                                punti=tuple(punti),
                                                fiducia=0.9)])

        await e._gira_gesture(_Tracker())
        await asyncio.sleep(0)
        await asyncio.gather(*e._compiti, return_exceptions=True)
        intenti = [m["intento"] for m in emessi if m.get("topic") == "gesture.intent"]
        assert intenti == ["espandi_pannello"], (
            f"la catena non produce un intento: {emessi}"
        )

    async def test_una_telecamera_che_si_STACCA_non_porta_via_il_core(self) -> None:
        from core.engine import Engine

        avvisi: list[dict] = []

        class _Ws:
            async def broadcast(self, msg):
                avvisi.append(msg)

        class _Rotto:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def fotogrammi(self, quanti=None):
                raise OSError("VIDIOC_DQBUF: No such device")

        e = Engine.__new__(Engine)
        e._ws = _Ws()
        e._compiti = set()
        await e._gira_gesture(_Rotto())
        assert avvisi and avvisi[0]["reason"] == "gesture_cadute"
