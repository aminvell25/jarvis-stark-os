"""ADR-009 — il tetto di RAM e di CPU del codice generato.

Chiude il punto 3 dei «non verificato» di `TOOLS-CODE.md`, che era il piu'
grave, e non per la ragione che c'era scritta: **il timeout limita il TEMPO.**
Misurato qui sotto, mezzo giga si alloca in una frazione di secondo — nessun
timeout utile scatterebbe mai, e su una APU a memoria unificata l'OOM killer
del kernel puo' prendersi il core di JARVIS o la sessione desktop invece del
processo isolato.

## Perche' un cgroup e non `resource.setrlimit()`

Sono state misurate tutte e due prima di scegliere, e la differenza non e'
un'opinione: **un rlimit e' per PROCESSO.** Otto `os.fork()` da 400 MiB stanno
tutti sotto un limite di 512 e insieme ne allocano 3200.

    prova                              RLIMIT_AS   RLIMIT_DATA   cgroup
    2 GiB in un processo               ferma       ferma         ferma
    otto figli da 400 MiB              PASSA       PASSA         ferma
    2 GiB condivisi (MAP_SHARED)       ferma       PASSA         ferma
    4 GiB riservati, 1 pagina toccata  UCCIDE      passa         passa
    tetto alla CPU                     no          no            si'

Le due righe in mezzo sono i test `TestLeEvasioni` di questo file, e sono la
ragione della scelta. L'ultima e' il punto 2, che arriva gratis.

## Ogni test tenta

Nessuno guarda solo l'argv: si alloca davvero, e si guarda chi viene fermato.
Un argv giusto su un gestore di cgroup che non delega il controllore `memory`
produce un processo che gira senza tetto.
"""

from __future__ import annotations

import shutil
import sys
import time

import pytest

from core.platform.linux_sandbox import (
    BWRAP,
    LIMITE,
    argv_limite,
    limite_mancante,
)
from core.sandbox.policy import SandboxPolicyError
from core.sandbox.runner import Profilo, SandboxMemoriaEsaurita, run_sandboxed

pytestmark = [
    pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap non disponibile"),
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="solo Linux"),
    pytest.mark.skipif(limite_mancante() is not None,
                       reason=f"tetti non applicabili: {limite_mancante()}"),
]

#: L'interprete di sistema: ADR-008 rifiuta quello di un venv.
PY = "/usr/bin/python3"

#: Cresce di 32 MiB per volta e TOCCA le pagine. Toccarle e' obbligatorio:
#: `bytearray(n)` grande arriva da una mmap anonima, che il kernel non popola
#: finche' nessuno ci scrive. Senza toccarle il cgroup non addebita niente e il
#: test direbbe che il tetto non funziona.
def _cresce(mb: int) -> str:
    return (f"b=[]\n"
            f"for _ in range({mb // 32}):\n"
            f"    x=bytearray(32*1024*1024)\n"
            f"    [x.__setitem__(i,1) for i in range(0,len(x),4096)]\n"
            f"    b.append(x)\n"
            f"print('ARRIVATO A {mb} MiB')")


async def _corri(sorgente: str, memoria_mb: int | None = 256,
                 cpu_percento: int | None = None, lavoro_mb: int = 16,
                 timeout: float = 30.0) -> tuple[int, str, str]:
    return await run_sandboxed(
        [PY, "-I", "-S", "-c", sorgente], [], [], timeout=timeout,
        profilo=Profilo.CODICE, lavoro_mb=lavoro_mb,
        memoria_mb=memoria_mb, cpu_percento=cpu_percento,
    )


# ── il controllo: senza tetto, la minaccia e' vera ───────────────────────────


class TestLaMinaccia:
    """Senza questi due test, «il tetto ferma» non si distingue da «questa
    macchina non ce la faceva comunque»."""

    async def test_senza_tetto_mezzo_giga_passa(self) -> None:
        rc, out, err = await _corri(_cresce(512), memoria_mb=None)
        assert rc == 0 and "ARRIVATO A 512 MiB" in out, err

    async def test_e_il_timeout_non_lo_avrebbe_mai_fermato(self) -> None:
        """Il punto 3 diceva «la RAM non ha un tetto» e lasciava intendere che
        il timeout facesse da rete. Non ne fa: misura il tempo, e allocare non
        ne richiede."""
        t0 = time.monotonic()
        rc, _, _ = await _corri(_cresce(512), memoria_mb=None)
        durata = time.monotonic() - t0
        assert rc == 0
        assert durata < 5.0, (
            f"512 MiB in {durata:.2f}s: il timeout predefinito del tool e' 5s, "
            f"quindi non e' mai intervenuto"
        )


# ── il tetto ─────────────────────────────────────────────────────────────────


class TestIlTetto:
    async def test_col_tetto_viene_fermato(self) -> None:
        with pytest.raises(SandboxMemoriaEsaurita):
            await _corri(_cresce(1024), memoria_mb=256)

    async def test_il_messaggio_dice_MEMORIA_e_dice_quanta(self) -> None:
        """«Il messaggio che torna all'LLM deve dire *limite di memoria
        superato*, non un traceback di `MemoryError` che sembra un bug del suo
        codice.»"""
        with pytest.raises(SandboxMemoriaEsaurita) as exc:
            await _corri(_cresce(1024), memoria_mb=256)
        testo = str(exc.value)
        assert "memoria" in testo.lower()
        assert "256" in testo, "il messaggio deve dire QUALE tetto"
        assert "MemoryError" not in testo and "Traceback" not in testo

    async def test_il_messaggio_e_certo_non_congetturato(self) -> None:
        """Con `OOMPolicy=continue` il cgroup sopravvive al processo e
        `memory.events` si legge: il messaggio riporta `oom_kill`, che e' la
        verita' del kernel. Senza, systemd smonta lo scope mentre stiamo per
        leggerlo e resta solo «probabilmente la memoria» — misurato, 6 su 6."""
        with pytest.raises(SandboxMemoriaEsaurita) as exc:
            await _corri(_cresce(1024), memoria_mb=256)
        assert "oom_kill=" in str(exc.value), (
            "letto da memory.events, non dedotto dal codice d'uscita"
        )

    async def test_un_programma_onesto_non_viene_toccato(self) -> None:
        """Un tetto che uccide il lavoro legittimo verrebbe alzato al primo
        fastidio, e da li' non proteggerebbe piu' niente. Misurato: CPython
        nudo in questo profilo occupa 7 MiB, questo programma 31 al picco."""
        rc, out, err = await _corri(
            "import json, statistics, hashlib\n"
            "d=[{'i':i,'q':i*i} for i in range(50_000)]\n"
            "s=json.dumps(d)\n"
            "print(len(s), statistics.mean(x['i'] for x in d))",
            memoria_mb=256,
        )
        assert rc == 0 and "24999.5" in out, err


# ── le due evasioni che hanno deciso la scelta ───────────────────────────────


class TestLeEvasioni:
    async def test_otto_figli_non_scavalcano_il_tetto(self) -> None:
        """**Il test che esclude `resource.setrlimit()`.**

        Un rlimit vale per un processo: misurato, con `RLIMIT_AS` e
        `RLIMIT_DATA` a 512 MiB, otto figli da 400 MiB restano vivi tutti e
        otto e ne allocano 3200 insieme. Il cgroup addebita l'albero intero.
        """
        rc, out, err = await _corri(
            "import os, time\n"
            "f=[]\n"
            "for k in range(8):\n"
            "    pid=os.fork()\n"
            "    if pid==0:\n"
            "        b=bytearray(200*1024*1024)\n"
            "        [b.__setitem__(i,1) for i in range(0,len(b),4096)]\n"
            "        time.sleep(2); os._exit(0)\n"
            "    f.append(pid)\n"
            "time.sleep(1.5)\n"
            "vivi=sum(1 for p in f if os.waitpid(p, os.WNOHANG)==(0,0))\n"
            "print(f'VIVI {vivi}')",
            memoria_mb=256, timeout=40,
        )
        assert rc == 0, err
        vivi = int(out.split("VIVI")[1])
        # ⚠️ L'invariante NON e' «nessun figlio sopravvive»: e' «insieme non
        # superano il tetto». Un figlio da 200 MiB dentro un tetto da 256 ci
        # sta, ed e' giusto che ci stia — il cgroup limita il totale, non
        # vieta di allocare. La prima stesura pretendeva zero superstiti e
        # falliva con uno, cioe' misurava la cosa sbagliata.
        assert vivi * 200 <= 256, (
            f"{vivi} figli vivi = {vivi * 200} MiB insieme, oltre il tetto di "
            f"256: con RLIMIT_AS o RLIMIT_DATA restano vivi tutti e otto e ne "
            f"tengono 3200"
        )
        assert vivi < 8, "sopravvivono tutti: il tetto non vale per l'albero"

    async def test_la_memoria_condivisa_non_scavalca_il_tetto(self) -> None:
        """**Il test che esclude `RLIMIT_DATA` in particolare.**

        `RLIMIT_DATA` copre il break e le mappature anonime PRIVATE. Una mmap
        anonima condivisa — il predefinito di `mmap.mmap(-1, n)` in Python —
        non la vede: misurato, 2 GiB scritti sotto un limite di 512 MiB.
        """
        with pytest.raises(SandboxMemoriaEsaurita):
            await _corri(
                "import mmap\n"
                "T=1024**3\n"
                "m=mmap.mmap(-1, T)\n"
                "for i in range(0, T, 4096): m[i]=1\n"
                "print('SCRITTO')",
                memoria_mb=256,
            )


# ── e cio' che NON deve diventare un errore di memoria ───────────────────────


class TestNonSiScambiaPerMemoria:
    """Il codice d'uscita non basta a riconoscere l'OOM, in nessuna delle due
    direzioni: 137 arriva anche da chi si uccide da solo. Attribuire la
    memoria a chi non l'ha esaurita manderebbe l'LLM a cercare un problema
    che non c'e'."""

    async def test_chi_si_uccide_da_solo_non_diventa_un_errore_di_memoria(self) -> None:
        rc, _, _ = await _corri(
            "import os, signal; os.kill(os.getpid(), signal.SIGKILL)",
            memoria_mb=256,
        )
        assert rc in (137, -9), f"atteso un 137, ricevuto {rc}"

    async def test_uscire_con_137_non_diventa_un_errore_di_memoria(self) -> None:
        rc, _, _ = await _corri("import sys; sys.exit(137)", memoria_mb=256)
        assert rc == 137


# ── il punto 2: la CPU, che arriva con lo stesso cgroup ──────────────────────


class TestLaCpu:
    async def test_la_quota_taglia_i_giri(self) -> None:
        """`while True: pass` lo uccide il timeout, ma per quei secondi occupa
        un core. `CPUQuota` lo rallenta, e in modo proporzionale: misurato al
        25% fa un quarto dei giri, al 10% un decimo."""
        ciclo = ("import time\n"
                 "t0=time.monotonic(); n=0\n"
                 "while time.monotonic()-t0 < 2.0: n+=1\n"
                 "print(n)")
        _, pieno, _ = await _corri(ciclo, memoria_mb=256, cpu_percento=100)
        _, quarto, _ = await _corri(ciclo, memoria_mb=256, cpu_percento=25)
        assert int(quarto) < int(pieno) / 2, (
            f"con un quarto di core ha fatto {quarto.strip()} giri contro "
            f"{pieno.strip()}: la quota non morde"
        )


class TestIlTimeoutContinuaAFunzionare:
    async def test_col_cgroup_di_mezzo_il_timeout_uccide_ancora(self) -> None:
        """Il cgroup si infila FRA noi e bubblewrap, e il timeout uccide «il
        processo che abbiamo lanciato». Con `--scope` quel processo e' ancora
        bubblewrap — `systemd-run` fa `exec`, non `fork` — quindi ucciderlo
        smonta il PID namespace come prima. Se un giorno diventasse un `fork`,
        questo test lo direbbe invece di lasciare processi orfani."""
        from core.sandbox.runner import SandboxTimeout

        with pytest.raises(SandboxTimeout):
            await _corri("while True: pass", memoria_mb=256, cpu_percento=25,
                         timeout=2.0)

    async def test_e_un_timeout_non_diventa_un_errore_di_memoria(self) -> None:
        from core.sandbox.runner import SandboxTimeout

        with pytest.raises(SandboxTimeout) as exc:
            await _corri("while True: pass", memoria_mb=256, timeout=2.0)
        assert "memoria" not in str(exc.value).lower()


# ── la forma dell'argv: cio' che non si vede eseguendo ───────────────────────


class TestArgv:
    def test_il_cgroup_sta_FUORI_da_bubblewrap(self) -> None:
        """Dentro sarebbe inutile — il processo isolato non ha
        `/sys/fs/cgroup` — e comunque un limite che si applica da se' e' un
        limite che si puo' togliere da se'."""
        fuori = argv_limite("u", 256, 50)
        assert fuori[0] == LIMITE and fuori[-1] == "--"
        assert BWRAP not in fuori

    def test_lo_swap_e_chiuso(self) -> None:
        """Senza `MemorySwapMax=0` il tetto non ferma niente: misurato, con
        512 MB e lo swap concesso 2 GiB si allocano lo stesso, solo piu'
        lentamente. E' l'unica riga senza la quale tutto il resto e' teatro."""
        assert "MemorySwapMax=0" in argv_limite("u", 256, None)

    def test_oompolicy_continue_c_e(self) -> None:
        """Non allenta il tetto: impedisce a systemd di smontare il cgroup
        prima che si possa leggere `memory.events`, cioe' e' la differenza fra
        un messaggio certo e uno probabile."""
        assert "OOMPolicy=continue" in argv_limite("u", 256, None)

    def test_gli_scope_stanno_in_una_FETTA_nostra(self) -> None:
        """Non e' ordine: il contatore degli OOM su cui si basa la diagnosi e'
        gerarchico, e sotto `app.slice` comprenderebbe l'OOM di qualunque
        altra applicazione della sessione."""
        from core.platform.linux_sandbox import FETTA

        assert f"--slice={FETTA}" in argv_limite("u", 256, None)

    def test_il_nome_dello_scope_lo_scegliamo_noi(self) -> None:
        """Senza `--unit=` il percorso del cgroup e' casuale, e senza il
        percorso non si legge `memory.events`."""
        assert "--unit=jarvis-1" in argv_limite("jarvis-1", 256, None)

    def test_la_cpu_si_puo_chiedere_da_sola(self) -> None:
        solo_cpu = argv_limite("u", None, 25)
        assert "CPUQuota=25%" in solo_cpu
        assert not any("MemoryMax" in a for a in solo_cpu)

    @pytest.mark.parametrize("memoria,cpu", [(0, None), (-1, None), (None, 0)])
    def test_i_valori_non_positivi_sono_rifiutati(self, memoria, cpu) -> None:
        with pytest.raises(SandboxPolicyError):
            argv_limite("u", memoria, cpu)


class TestFailClosed:
    async def test_senza_systemd_run_solleva_invece_di_girare_SENZA_tetto(
        self, monkeypatch
    ) -> None:
        """«Un limite che non si applica perche' manca un binario e' peggio di
        nessun limite.» Peggio perche' chi ha scritto `memory_mb = 512` crede
        di averlo: la terza possibilita' — eseguire lo stesso, in silenzio — e'
        l'unica inaccettabile."""
        import core.platform.linux_sandbox as LS

        monkeypatch.setattr(LS, "LIMITE", "systemd-run-che-non-esiste")
        with pytest.raises(SandboxPolicyError, match="non applicabile"):
            await _corri("print('non deve arrivarci')", memoria_mb=256)

    def test_il_doctor_puo_dire_PERCHE_non_e_applicabile(self, monkeypatch) -> None:
        """Una diagnosi che dice solo «no» manda a indovinare."""
        import core.platform.linux_sandbox as LS

        monkeypatch.setattr(LS, "LIMITE", "systemd-run-che-non-esiste")
        assert "non e' nel PATH" in (limite_mancante() or "")


# ── l'interazione che nessuno aveva previsto ─────────────────────────────────


class TestLaTmpfsPesaSulloStessoTetto:
    """Le pagine della tmpfs di lavoro sono addebitate allo stesso cgroup.

    Non e' dedotto: e' il motivo per cui `CodeSettings` rifiuta una
    configurazione con `memory_mb` troppo vicino a `tmpfs_mb`. Qui si prova
    l'interazione al livello del runner, dove quel controllo non c'e'.
    """

    async def test_riempire_lo_spazio_di_lavoro_consuma_il_tetto(self) -> None:
        with pytest.raises(SandboxMemoriaEsaurita):
            await _corri(
                "open('/lavoro/x','wb').write(b'\\0' * (200*1024*1024))\n"
                "print('SCRITTO')",
                memoria_mb=64, lavoro_mb=256,
            )

    async def test_con_il_margine_giusto_invece_riesce(self) -> None:
        rc, out, err = await _corri(
            "open('/lavoro/x','wb').write(b'\\0' * (48*1024*1024))\n"
            "print('SCRITTO')",
            memoria_mb=256, lavoro_mb=64,
        )
        assert rc == 0 and "SCRITTO" in out, err

    def test_le_impostazioni_rifiutano_un_tetto_sotto_la_tmpfs(self) -> None:
        from pydantic import ValidationError

        from core.settings import CodeSettings

        with pytest.raises(ValidationError, match="non basta"):
            CodeSettings(tmpfs_mb=64, memory_mb=100)
        # tmpfs + margine misurato = il minimo che parte
        assert CodeSettings(tmpfs_mb=64, memory_mb=128).memory_mb == 128
