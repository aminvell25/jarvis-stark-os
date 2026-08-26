"""§7.6 — i cinque intenti che JARVIS riconosceva e non eseguiva.

`set_volume`, `mute`, `brief_me`, `needs_attention` e `doctor` erano nella
grammatica dalla Fase 3 e nel corpus delle frasi etichettate. `esegui_t0` li
rifiutava con «non è né un'azione della scrivania né un tool dell'allowlist»:
JARVIS riconosceva la frase, scriveva una riga nel log, e non succedeva niente.

È il guasto più visibile all'uso, perché dall'esterno è indistinguibile da «non
mi ha sentito» — e la reazione naturale è ripetere la frase più forte.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from core.llm.grammar import INTENTI_CORE, INTENTI_UI, parse, regole
from core.platform.linux_audio import LinuxAudioIO
from core.tools import registry
from core.tools.audio import LIVELLO_PREDEFINITO, register_audio_tools


@pytest.fixture
def audio() -> LinuxAudioIO:
    registry.clear()
    a = LinuxAudioIO()
    register_audio_tools(lambda: a)
    return a


class TestNessunIntentoSenzaStrada:
    def test_ogni_regola_della_grammatica_HA_una_destinazione(self, audio) -> None:
        """La proprietà, non l'elenco: un intento nuovo senza esecutore fa
        fallire qui, non in esercizio."""
        from core.settings import Settings
        from core.tools.files import register_file_tools
        from core.tools.system import register_system_tools
        from core.tools.web import register_web_tools
        from tests.conftest import FakeSensors

        # Tutti i registratori che l'engine chiama a impostazioni predefinite.
        # ⚠️ Dimenticarne uno farebbe fallire questo test per il motivo
        # sbagliato: `open_web` e `youtube_search` sono comparsi come orfani
        # alla prima stesura, e l'orfano era il registratore mancante.
        register_system_tools(FakeSensors())
        register_file_tools(lambda: _FinteImpostazioni())
        register_web_tools(lambda: Settings.model_construct())

        orfani = {
            tool for _, tool in regole()
            if tool not in INTENTI_UI
            and tool not in INTENTI_CORE
            and tool not in set(registry.names())
        }
        assert orfani == set(), f"intenti senza esecutore: {sorted(orfani)}"


class _FinteImpostazioni:
    class fs:
        allowed_roots = [Path("/tmp")]
        trash_only = True


class TestIlVolumeEdiJARVIS:
    """`CLAUDE.md`: «fuori dalla sua finestra non tocca nulla». Il mixer di
    PipeWire è fuori dalla sua finestra."""

    async def test_volume_40_attenua_il_PCM(self, audio) -> None:
        r = await registry.invoke("set_volume", {"level": 40})
        assert r.ok and r.output["volume"] == 40
        pcm = struct.pack("<4h", 1000, -1000, 32767, -32768)
        assert struct.unpack("<4h", audio._con_guadagno(pcm)) == (400, -400, 13106, -13107)

    async def test_a_volume_pieno_il_PCM_non_si_TOCCA(self, audio) -> None:
        """Il caso normale non paga niente: il barge-in di §7.4 ha 200 ms di
        budget e non vanno spesi a moltiplicare campioni per uno."""
        await registry.invoke("set_volume", {"level": 100})
        pcm = b"\x00\x01" * 100
        assert audio._con_guadagno(pcm) is pcm

    async def test_un_iperbole_SATURA_e_non_fallisce(self, audio) -> None:
        """Il corpus T0 contiene già `("volume 250", ..., 100)`: «volume
        mille» è un modo di dire, non un errore di validazione."""
        r = await registry.invoke("set_volume", {"level": 250})
        assert r.ok and r.output["volume"] == 100
        r = await registry.invoke("set_volume", {"level": -5})
        assert r.ok and r.output["volume"] == 0

    async def test_il_muto_RICORDA_il_livello(self, audio) -> None:
        await registry.invoke("set_volume", {"level": 35})
        await registry.invoke("mute", {})
        assert audio.volume == 0
        r = await registry.invoke("unmute", {})
        assert r.output["volume"] == 35, "riattivare l'audio ha perso il livello"

    async def test_unmute_senza_un_prima_torna_UDIBILE(self, audio) -> None:
        """Riattivare l'audio e restare muti sarebbe la risposta sbagliata."""
        audio.imposta_volume(0)
        r = await registry.invoke("unmute", {})
        assert r.output["volume"] == LIVELLO_PREDEFINITO

    async def test_a_volume_zero_non_si_riproduce_AFFATTO(self, audio,
                                                          monkeypatch) -> None:
        """Mandare zeri a PipeWire terrebbe `sta_riproducendo` a vero per tutta
        la frase, e le regole 2 e 3 di §15 leggono proprio quello: JARVIS
        resterebbe «occupato a parlare» mentre è muto.

        ⚠️ **La prima stesura di questo test non discriminava.** Asseriva
        `sta_riproducendo is False` DOPO `await play(...)` — ma `play` attende
        la fine del processo, quindi a quel punto è falso in ogni caso.
        Neutralizzando la guardia il test restava verde. Adesso guarda ciò che
        conta davvero: che il processo **non venga avviato**.
        """
        import asyncio as _asyncio

        avviati: list[tuple] = []

        async def _spia(*argv, **kw):
            avviati.append(argv)
            raise AssertionError("processo avviato a volume 0")

        monkeypatch.setattr(_asyncio, "create_subprocess_exec", _spia)
        audio.imposta_volume(0)
        await audio.play(b"\x00\x01" * 1000)
        assert avviati == [], "pw-play avviato per riprodurre silenzio"

        # E il controllo del controllo: a volume udibile il processo parte.
        audio.imposta_volume(50)
        with pytest.raises(AssertionError, match="processo avviato"):
            await audio.play(b"\x00\x01" * 1000)

    async def test_nessuno_di_questi_chiede_CONFERMA(self, audio) -> None:
        """§6.2 esiste per le operazioni irreversibili sui file dell'utente. Il
        volume si annulla dicendo un altro numero."""
        for nome in ("set_volume", "mute", "unmute"):
            assert registry.get(nome).side_effect is False

    async def test_e_nessuno_e_raggiungibile_da_una_GESTURE(self, audio) -> None:
        """Non è l'invariante 27 a vietarlo — quello riguarda i side_effect.
        È una decisione: una mano che passa davanti alla telecamera e zittisce
        JARVIS è il genere di sorpresa che §14 evita."""
        for nome in ("set_volume", "mute", "unmute"):
            assert registry.get(nome).gesture_allowed is False


class TestLeFrasi:
    @pytest.mark.parametrize("frase,atteso", [
        ("volume 40", "set_volume"),
        ("silenzio", "mute"),
        ("riattiva l'audio", "unmute"),
        ("torna a parlare", "unmute"),
        ("come stiamo", "doctor"),
        ("briefing", "brief_me"),
        ("cosa richiede la mia attenzione", "needs_attention"),
    ])
    def test_riconosciute(self, frase: str, atteso: str) -> None:
        assert parse(frase).tool == atteso

    @pytest.mark.parametrize("frase", ["torna a casa presto",
                                       "riaccendi la luce in cucina"])
    def test_le_vicine_restano_CONVERSAZIONE(self, frase: str) -> None:
        assert parse(frase) is None


class TestGliIntentiDelCORE:
    """Le tre strade sono tre allowlist, e la terza esegue davvero."""

    def _engine(self) -> str:
        return (Path(__file__).resolve().parent.parent / "core" / "engine.py"
                ).read_text(encoding="utf-8")

    def test_doctor_chiama_i_CONTROLLI(self) -> None:
        s = self._engine()
        dopo = s.split("async def _diagnostica", 1)[1].split("\n    #: I due meta", 1)[0]
        assert "doctor.run_checks()" in dopo
        assert '"topic": "agent.advisory"' in dopo, "§16.1b vuole lo stesso contenuto sul bus"
        assert "_annuncia_a_voce" in dopo, "§16.1b lo vuole raggiungibile a voce"

    def test_doctor_a_voce_dice_solo_cio_che_NON_va(self) -> None:
        """Leggere quindici righe verdi ad alta voce sarebbe inutilizzabile."""
        s = self._engine()
        dopo = s.split("async def _diagnostica", 1)[1].split("\n    #: I due meta", 1)[0]
        assert 'c.stato != "ok"' in dopo

    def test_i_meta_comandi_passano_da_T2_e_NON_aspettano(self) -> None:
        """Un briefing costa decine di secondi ed `esegui_t0` sta sul percorso
        della voce: bloccare lì vorrebbe dire un JARVIS muto per mezzo minuto
        dopo una domanda."""
        s = self._engine()
        dopo = s.split("async def _meta_comando", 1)[1].split("\n    async def _rispondi", 1)[0]
        assert "asyncio.create_task(self._rispondi_al_meta" in dopo
        assert "Un momento, Signore." in dopo

    def test_un_meta_comando_VUOTO_si_annuncia(self) -> None:
        """Un meta-comando che tace è indistinguibile da uno mai partito."""
        s = self._engine()
        dopo = s.split("async def _rispondi_al_meta", 1)[1].split("\n    def ", 1)[0]
        assert "meta_comando_vuoto" in dopo
        assert dopo.count("_annuncia_a_voce") >= 3

    def test_lo_spawn_passa_dal_GOVERNOR(self) -> None:
        """Invariante 16: ogni spawn T2 ci passa."""
        s = self._engine()
        assert "self._t2_meta = ClaudeT2(self._governor, RADICE)" in s

    def test_l_AudioIO_e_UNO_SOLO(self) -> None:
        """Due istanze vorrebbero dire un guadagno impostato su una che non
        riproduce niente — due metà scollegate."""
        s = self._engine()
        # Una sola costruzione, dentro la proprietà pigra, e due consumatori
        # che passano da lì. ⚠️ Pigra e non nel costruttore: i tool si
        # registrano prima che la radice decida se la voce si accende, e
        # costruirlo lì impedisce di sostituire la fabbrica — che è come si
        # prova un microfono che muore. L'ha trovato quel test.
        assert s.count("platform_audio()") == 1
        assert "if self._audio is None:" in s
        assert "register_audio_tools(lambda: self.audio)" in s
        assert "audio=self.audio" in s
