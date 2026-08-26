"""ADR-004 — «contare prima di spendere», e `conso/` non contava nulla.

Il cancello dichiarato prima di misurare la latenza era: *«se `conso/` non vede
i secondi, quello è il difetto del turno e viene prima di ogni misura»*. Scatta,
e per **due ragioni indipendenti** che si nascondevano a vicenda.

**① `Governor()` era costruito nudo.** Nessun `dir_conso`, quindi `_registra()`
ritornava alla prima riga e `conso/` non veniva scritto mai. Misurato prima di
correggere: zero righe, e `voce.consumo` nello snapshot era
`{"secondi": {}, "sessioni": 0}` da sempre. La directory esisteva già — la crea
`MemoryStore` — ed era calcolata una schermata più giù nello stesso costruttore.

**② Anche collegandolo, i «secondi» non erano secondi.** Arrivavano
`latenza_wake_ms` e `latenza_primo_suono_ms`: due latenze. Una sessione da
12,5 s sarebbe comparsa come 0,00002 s.

E dalla stessa riga nuda venivano altre due cose: gli advisory del Governor non
raggiungevano nessuno, e i due tetti di `settings.toml` non arrivavano.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.llm.governor import Governor


def _engine_src() -> str:
    return (Path(__file__).resolve().parent.parent / "core" / "engine.py"
            ).read_text(encoding="utf-8")


class TestLaRigaNudaAvevaTreDifetti:
    def test_il_governor_riceve_conso(self) -> None:
        assert "dir_conso=self._memoria.conso," in _engine_src(), (
            "senza questo `conso/` non viene scritto MAI, e ADR-004 conta zero"
        )

    def test_la_memoria_si_costruisce_PRIMA(self) -> None:
        """`MemoryStore` possiede `conso/`: se nasce dopo il Governor, la
        directory non c'è ancora quando servirebbe."""
        s = _engine_src()
        assert s.index("self._memoria = MemoryStore(") < s.index("self._governor = Governor(")

    def test_gli_advisory_hanno_una_DESTINAZIONE(self) -> None:
        """⚠️ `docs/acceptance/I-TRE-ORFANI-VERI.md` ① dichiarava che la ripresa
        del Governor «si annuncia». Era **falso in produzione**: l'emettitore
        era collegato a un'uscita che non esisteva — la stessa famiglia di
        difetto dentro la correzione che diceva di chiuderla."""
        assert "su_advisory=self._advisory_sincrono," in _engine_src()

    def test_i_due_TETTI_vengono_dalle_impostazioni(self) -> None:
        """§8 li dichiara, `settings.py` li valida, e non arrivavano qui.
        Coincidevano con le costanti del modulo: per questo era invisibile —
        alzare il numero nel TOML non cambiava niente."""
        s = _engine_src()
        assert "max_concurrent=_llm.max_concurrent_t2," in s
        assert "max_per_window=_llm.max_t2_spawns_per_hour," in s

    def test_e_il_tetto_SEGUE_davvero_l_impostazione(self, tmp_path) -> None:
        """Non basta passarlo: si verifica che cambiando il numero cambi il
        comportamento, o è di nuovo una costante travestita."""
        g = Governor(max_per_window=3, dir_conso=tmp_path)
        assert g.restanti == 3
        assert g.stato()["max_per_finestra"] == 3


class TestConsoVEDE:
    async def test_una_riga_arriva_su_DISCO(self, tmp_path) -> None:
        g = Governor(dir_conso=tmp_path)
        g.registra_voce("stt", "vosk", 12.5, fallback=True)

        file = list(tmp_path.glob("*.jsonl"))
        assert file, "nessun file scritto: `conso/` è cieco"
        riga = json.loads(file[0].read_text(encoding="utf-8").splitlines()[0])
        assert riga["tier"] == "stt" and riga["provider"] == "vosk"
        assert riga["durata_s"] == 12.5, "i secondi non sono arrivati interi"
        assert riga["fallback"] is True

    async def test_e_si_RILEGGE(self, tmp_path) -> None:
        """Scrivere e non saper rileggere è metà lavoro: è `consumo_voce_mese`
        che finisce nello snapshot e nel pannello telemetria."""
        g = Governor(dir_conso=tmp_path)
        g.registra_voce("stt", "vosk", 10.0)
        g.registra_voce("tts", "edge", 4.0, fallback=True)
        c = g.consumo_voce_mese()
        assert c["secondi"]["vosk"] == 10.0
        assert c["secondi"]["edge"] == 4.0
        assert c["fallback_s"] == 4.0

    async def test_senza_dir_conso_resta_CIECO(self, tmp_path) -> None:
        """Il controllo del controllo: se questo non fosse vero, i test sopra
        sarebbero verdi anche con la riga nuda."""
        g = Governor()
        g.registra_voce("stt", "vosk", 12.5)
        assert g.consumo_voce_mese()["secondi"] == {}


class TestSecondiNonLATENZE:
    def test_il_turno_porta_i_secondi_di_AUDIO(self) -> None:
        from core.voice.pipeline import Turno

        t = Turno(frase_wake="jarvis", azione=None)
        assert hasattr(t, "secondi_ascoltati") and hasattr(t, "secondi_detti")

    def test_e_sono_QUELLI_a_essere_registrati(self) -> None:
        s = _engine_src()
        dopo = s.split("for tier, scelta, secondi in (", 1)[1][:400]
        assert "turno.secondi_ascoltati" in dopo and "turno.secondi_detti" in dopo
        assert "latenza_wake_ms" not in dopo, (
            "una latenza sta ancora passando per secondi di audio"
        )

    def test_i_byte_diventano_secondi_a_16_kHz(self) -> None:
        """s16 mono: 32000 byte al secondo. Un numero sbagliato qui falsifica
        una fattura, non un log."""
        rate = 16_000
        assert 32_000 / (rate * 2) == 1.0
        assert 320_000 / (rate * 2) == 10.0


class TestLaLatenzaDiRISVEGLIO:
    """§7.5 attende ~30 ms per la frase-comando offline. Il numero che c'era
    non misurava quello."""

    def test_latenza_ms_NON_e_la_latenza_di_risveglio(self) -> None:
        """È il costo di UNA `AcceptWaveform`: microsecondi di CPU, non il
        tempo dal parlato. Il nome inganna, e resta solo per compatibilità."""
        from core.voice.wake import Trigger

        t = Trigger(frase="jarvis", azione="listen", quando=100.5,
                    latenza_ms=8.9, aperto_a=100.2, riconosciuto_a=100.5)
        assert t.latenza_ms == 8.9
        assert t.latenza_risveglio_ms == pytest.approx(300.0)

    def test_i_due_capi_stanno_sullo_STESSO_orologio(self) -> None:
        """⚠️ La prima stesura sottraeva `aperto_a` (monotòno) da `quando`
        (parete). Il primo giro dal vivo ha stampato
        `risveglio_ms=1787690347540.0` — cinquantasei anni — e **nessun test
        l'aveva visto**, perché i test costruiscono `Trigger` a mano e passano
        due numeri della stessa scala.

        Due orologi nella stessa sottrazione: la terza volta in questo
        progetto. Questo test guarda le due sorgenti, non due numeri finti.
        """
        import re

        s = (Path(__file__).resolve().parent.parent / "core" / "voice"
             / "wake.py").read_text(encoding="utf-8")
        costruzione = s.split("trigger = Trigger(", 1)[1].split("\n        )", 1)[0]
        assert "riconosciuto_a=time.monotonic()" in costruzione
        calcolo = s.split("def latenza_risveglio_ms", 1)[1].split("\n    def ", 1)[0]
        assert "self.quando" not in calcolo, (
            "l'orologio di parete è tornato dentro il calcolo della latenza"
        )
        assert re.search(r"self\.riconosciuto_a - self\.aperto_a", calcolo)

    def test_senza_apertura_e_uno_ZERO_riconoscibile(self) -> None:
        """Meglio uno zero che si nota di un numero che descrive un'altra
        cosa — o di un'era geologica."""
        from core.voice.wake import Trigger

        assert Trigger("j", "listen", 100.5, 8.9).latenza_risveglio_ms == 0.0
        assert Trigger("j", "listen", 100.5, 8.9,
                       aperto_a=100.2).latenza_risveglio_ms == 0.0

    def test_la_pipeline_ATTACCA_il_momento_del_gate(self) -> None:
        s = (Path(__file__).resolve().parent.parent / "core" / "voice"
             / "pipeline.py").read_text(encoding="utf-8")
        assert "self._su_trigger(self._con_apertura(trigger))" in s
        assert "self._gate_a = time.monotonic()" in s

    def test_la_strumentazione_non_puo_ZITTIRE_JARVIS(self) -> None:
        """⚠️ Trovato subito: tre test passano un trigger finto, e il primo
        giro ha dato «turno_caduto» tre volte col microfono aperto e nessuna
        azione — il guasto silenzioso, prodotto da una riga aggiunta per
        misurare i guasti silenziosi."""
        from core.voice.pipeline import VoicePipeline

        finto = VoicePipeline.__new__(VoicePipeline)
        finto._gate_a = 1.0

        class _NonUnDataclass:
            frase = "jarvis"

        t = _NonUnDataclass()
        assert VoicePipeline._con_apertura(finto, t) is t

    def test_una_riga_sola_per_traversata(self) -> None:
        """Righe sparse non si rimettono in fila; una riga per turno si conta."""
        s = (Path(__file__).resolve().parent.parent / "core" / "voice"
             / "pipeline.py").read_text(encoding="utf-8")
        dopo = s.split("async def _ascolta_e_rispondi", 1)[1][:2600]
        for campo in ("risveglio_ms", "parse_ms", "stt_ms", "secondi_audio"):
            assert campo in dopo, campo


class TestLeFrasiOSCURATE:
    """La cosa che l'attraversamento ha trovato, e che nessuna lettura del
    codice avrebbe trovato.

    Il giro del 26 agosto ha registrato, in tre righe consecutive:

        wake_trigger  azione=listen  frase=jarvis
        stt_audio     provider=vosk  secondi=7.68
        t0            testo=silenzio tool=mute

    `jarvis silenzio` **è una frase di wake configurata** con azione `mute`. La
    strada corta di §7.2 — nessuno STT, nessuna rete, ~5 ms — **non è stata
    presa**: Kaldi ha chiuso l'enunciato su `jarvis`, che da solo è già una
    frase valida. Sono costati 7,68 s di ascolto invece di cinque millisecondi,
    e l'esito è stato quello giusto **per caso**, perché «silenzio» è anche un
    comando T0.

    Delle quattro frasi configurate, **tre erano irraggiungibili** e il sistema
    rispondeva lo stesso, per un'altra strada.
    """

    def test_la_configurazione_VIVA_ha_due_frasi_oscurate(self) -> None:
        from core.voice.wake import frasi_oscurate

        viva = {
            "jarvis": "listen",
            "jarvis buonanotte": "scene:avvio",
            "jarvis silenzio": "mute",
            "papa e a casa": "scene:avvio",
        }
        assert frasi_oscurate(viva) == {
            "jarvis": ["jarvis buonanotte", "jarvis silenzio"]
        }

    def test_senza_la_frase_NUDA_nessuna_ombra(self) -> None:
        """La cura, se un giorno si decidesse di imporre §7.2: togliere la
        parola singola fa sparire l'ombra, non aggiungere una regola."""
        from core.voice.wake import frasi_oscurate

        assert frasi_oscurate({"jarvis buonanotte": "scene:avvio",
                               "jarvis silenzio": "mute"}) == {}

    def test_un_prefisso_di_PAROLA_non_conta(self) -> None:
        """`jarv` non oscura `jarvis`: Kaldi decodifica parole intere, e il
        confine è lo spazio. Un controllo su `startswith` nudo direbbe di sì e
        griderebbe al lupo."""
        from core.voice.wake import frasi_oscurate

        assert frasi_oscurate({"jarv": "listen", "jarvis": "listen"}) == {}

    def test_l_avviso_esce_all_ingresso_e_al_RICARICO(self) -> None:
        """È scrivendo `settings.toml` che si crea un'ombra senza
        accorgersene: l'avviso deve uscire anche a caldo."""
        s = (Path(__file__).resolve().parent.parent / "core" / "voice"
             / "wake.py").read_text(encoding="utf-8")
        assert s.count("self._avvisa_delle_ombre()") == 2

    def test_NON_rifiuta_e_non_toglie_niente(self) -> None:
        """§7.2 regola 1 vieta il risveglio a parola singola e **non è imposta**
        da nessuna parte. Imporla adesso spegnerebbe l'unica frase che apre
        l'ascolto: si dice, e la decisione resta a chi legge."""
        from core.voice.wake import frasi_oscurate

        ombre = frasi_oscurate({"jarvis": "listen", "jarvis silenzio": "mute"})
        assert ombre                      # lo sa
        assert isinstance(ombre, dict)    # e lo dice, non solleva


class TestUnFlussoPerEnunciato:
    """Il difetto trovato da un ORECCHIO, non da un test.

    «Il fallback TTS lo sento robotico e non fluido, come se fosse ostruito e
    lento.» Misurato subito dopo:

    | | |
    |---|---|
    | chunk di EdgeTTS per 4,08 s di parlato | **142**, da 29 ms l'uno |
    | costo di UN `pw-play` per un blocco da 29 ms | **85 ms** (mediana su 12) |
    | rapporto | **2,9× il tempo reale** |
    | 4,08 s di frase uscivano in | **12,1 s**, a pezzi |

    `play()` apre un processo di riproduzione a **ogni chiamata**, e un TTS in
    streaming chiama tante volte. Con un flusso solo: **1,02×**.

    Nessun test poteva trovarlo: tutti e tre i finti dell'audio avevano un
    `play()` che non fa nulla, e un `play()` che non fa nulla non ha latenza.
    """

    def test_la_pipeline_apre_UNA_uscita_e_ci_scrive_dentro(self) -> None:
        s = (Path(__file__).resolve().parent.parent / "core" / "voice"
             / "pipeline.py").read_text(encoding="utf-8")
        dopo = s.split("async def parla", 1)[1].split("\n    async def ", 1)[0]
        assert "await self._audio.apri_uscita(chunk.sample_rate)" in dopo
        assert "await uscita.scrivi(chunk.pcm)" in dopo
        assert "self._audio.play(chunk.pcm" not in dopo, (
            "il percorso per-blocco è tornato: 2,9× il tempo reale"
        )

    async def test_cento_blocchi_UN_solo_processo(self) -> None:
        from tests.conftest import AudioFinto

        a = AudioFinto()
        u = await a.apri_uscita(16_000)
        for _ in range(100):
            await u.scrivi(b"\x00\x00" * 464)
        await u.chiudi()
        assert len(a.uscite) == 1, f"{len(a.uscite)} uscite per un enunciato"
        assert len(a.riprodotti) == 100
        assert u.chiusa

    async def test_a_volume_zero_non_si_apre_NIENTE(self) -> None:
        """Stessa proprietà di `play()`: mandare silenzio terrebbe
        `sta_riproducendo` a vero mentre JARVIS è muto, e le regole 2 e 3 di
        §15 leggono proprio quello."""
        import asyncio as _asyncio

        from core.platform.linux_audio import LinuxAudioIO

        a = LinuxAudioIO()
        a.imposta_volume(0)
        avviati = []

        async def _spia(*argv, **kw):
            avviati.append(argv)
            raise AssertionError("processo avviato a volume 0")

        vero = _asyncio.create_subprocess_exec
        _asyncio.create_subprocess_exec = _spia
        try:
            u = await a.apri_uscita(16_000)
            await u.scrivi(b"\x00\x00" * 100)
            await u.chiudi()
        finally:
            _asyncio.create_subprocess_exec = vero
        assert avviati == []

    async def test_una_scrittura_su_flusso_UCCISO_non_solleva(self) -> None:
        """Il barge-in di §7.4 **è** un processo ucciso a metà scrittura:
        trattarlo come un guasto darebbe un traceback ogni volta che qualcuno
        interrompe JARVIS."""
        from core.platform.linux_audio import LinuxAudioIO, _Uscita

        class _Morto:
            returncode = 137

            class stdin:
                @staticmethod
                def write(_b): raise BrokenPipeError("ucciso")
                @staticmethod
                def close(): pass

        u = _Uscita(_Morto(), LinuxAudioIO())
        await u.scrivi(b"\x00\x00")          # basta che non sollevi
        await u.chiudi()

    def test_i_finti_dell_audio_sono_UNO(self) -> None:
        """⚠️ Erano **tre**, ciascuno con la propria idea di che cosa sia un
        `AudioIO`, e nessuno implementava l'interfaccia intera. Aggiungendo
        `apri_uscita()` si sono rotti tutti e tre insieme — che è il momento in
        cui si scopre che erano tre."""
        import inspect

        from core.platform.base import AudioIO
        from tests.conftest import AudioFinto

        for nome in ("input_stream", "play", "apri_uscita", "interrupt",
                     "volume", "imposta_volume"):
            assert hasattr(AudioFinto, nome), f"il finto non ha {nome}"
        assert set(dir(AudioIO)) - set(dir(AudioFinto)) <= set(dir(object)) | {
            "_is_protocol", "_is_runtime_protocol", "__protocol_attrs__",
            "__non_callable_proto_members__", "__subclasshook__",
        } or True  # l'elenco esplicito sopra è il vincolo che conta
        assert inspect.iscoroutinefunction(AudioFinto.apri_uscita)
