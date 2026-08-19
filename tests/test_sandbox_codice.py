"""ADR-008 — il profilo che isola il codice generato.

Questi test **eseguono** bubblewrap e **tentano davvero**, come quelli di
Fase 1. Verificare l'argv non basta: un argv giusto passato a un kernel che
vieta gli user namespace produce un processo che non parte, e un argv con un
bind sbagliato produce un processo che legge quello che non deve.

## Il controllo e' meta' del valore

Ogni prova di segregazione gira DUE VOLTE: col profilo nuovo, dove deve
fallire, e col profilo vecchio, dove deve **riuscire**. Senza il secondo giro
un test verde non distingue «la sandbox blocca» da «il file non c'e' su questa
macchina», e sarebbe verde anche il giorno in cui qualcuno rimuovesse tutte le
difese.

⚠️ **Il contenuto dei segreti non viene mai stampato ne' asserito.** Si
verifica che l'apertura sollevi, e nel giro di controllo si verifica soltanto
la LEGGIBILITA' con `os.access`. Un test che stampasse `secrets.toml` in un
report di CI sarebbe il difetto che sta cercando di prevenire.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from core.platform.linux_sandbox import (
    LAVORO,
    LIBRERIE,
    albero_interprete,
    build_argv,
)
from core.sandbox.policy import SandboxPolicyError
from core.sandbox.runner import Profilo, run_sandboxed

pytestmark = [
    pytest.mark.skipif(shutil.which("bwrap") is None, reason="bwrap non disponibile"),
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="solo Linux"),
]

TIMEOUT = 30.0

#: L'interprete che il profilo monta. **Quello di sistema**, non quello del
#: venv: un venv non e' autonomo (vedi `albero_interprete`), e per il codice
#: generato l'interprete di sistema e' anche la scelta piu' stretta — non
#: porta dentro i site-packages del progetto.
INTERPRETE = "/usr/bin/python3"

#: I percorsi che il codice generato NON deve poter leggere. Sono quelli veri
#: di questa macchina, non dei finti: la minaccia di ADR-008 e' esattamente
#: `open(secrets.toml).read()` seguito da `print()`.
SEGRETI = {
    "secrets.toml": Path.home() / ".config" / "jarvis-os" / "secrets.toml",
    "~/.ssh": Path.home() / ".ssh",
    "~": Path.home(),
}


async def _esegui(codice: str, profilo: Profilo) -> tuple[int, str, str]:
    """Esegue un frammento nel profilo dato. `rw_paths` vuoto per entrambi."""
    return await run_sandboxed(
        [INTERPRETE, "-c", codice], [], [Path("/tmp")], TIMEOUT, profilo
    )


def _riuscito(out: str) -> bool:
    """Il frammento stampa RIUSCITO o FALLITO: nessun contenuto, mai."""
    return out.strip().startswith("RIUSCITO")


#: Il frammento e' lo stesso per i due profili — cambia solo l'isolamento
#: attorno. Stampa l'ESITO, non il dato: se leggesse davvero un segreto,
#: quel segreto non deve finire nell'output di pytest.
def _tenta(espressione: str) -> str:
    return (
        "try:\n"
        "    import os\n"
        f"    r = {espressione}\n"
        "    print('RIUSCITO', type(r).__name__)\n"
        "except Exception as e:\n"
        "    print('FALLITO', type(e).__name__)\n"
    )


# ── le cinque prove di ADR-008 ───────────────────────────────────────────────


class TestNonLegge:
    """Il cuore di ADR-008: con `--tmpfs /` non c'e' niente da leggere."""

    async def test_secrets_toml_non_si_apre(self) -> None:
        p = SEGRETI["secrets.toml"]
        if not p.exists():
            pytest.skip(f"{p} non esiste su questa macchina: la prova sarebbe vuota")
        rc, out, err = await _esegui(_tenta(f"open({str(p)!r}).read()"), Profilo.CODICE)
        assert rc == 0, err
        assert not _riuscito(out), f"il codice generato ha letto {p}"
        assert "FileNotFoundError" in out, out

    async def test_ssh_non_si_elenca(self) -> None:
        p = SEGRETI["~/.ssh"]
        if not p.exists():
            pytest.skip(f"{p} non esiste su questa macchina")
        rc, out, err = await _esegui(_tenta(f"os.listdir({str(p)!r})"), Profilo.CODICE)
        assert rc == 0, err
        assert not _riuscito(out), f"il codice generato ha elencato {p}"

    async def test_la_home_non_si_elenca(self) -> None:
        """`os.listdir(os.path.expanduser("~"))`, la forma di ADR-008.

        Con `--clearenv` HOME non esiste e `/etc/passwd` nemmeno, quindi
        `expanduser` restituisce `~` alla lettera e l'elenco fallisce. Non e'
        un caso fortunato: e' il motivo per cui HOME resta assente.
        """
        rc, out, err = await _esegui(
            _tenta("os.listdir(os.path.expanduser('~'))"), Profilo.CODICE
        )
        assert rc == 0, err
        assert not _riuscito(out), "il codice generato ha elencato la home"

    async def test_home_reale_e_slash_home_non_esistono(self) -> None:
        """Anche nominandola per percorso assoluto, senza passare da HOME."""
        for bersaglio in (str(Path.home()), "/home", "/etc/passwd", "/root"):
            rc, out, err = await _esegui(
                _tenta(f"os.listdir({bersaglio!r})"), Profilo.CODICE
            )
            assert rc == 0, err
            assert not _riuscito(out), f"{bersaglio} e' visibile dalla sandbox"


class TestFunzionaAncora:
    """Una sandbox che non fa girare niente non e' una sandbox, e' un muro."""

    async def test_la_stdlib_si_importa(self) -> None:
        rc, out, err = await _esegui(
            "import json, math, hashlib, re, datetime, itertools, statistics\n"
            "print('RIUSCITO', json.dumps({'radice': math.isqrt(144)}))\n",
            Profilo.CODICE,
        )
        assert rc == 0, err
        assert _riuscito(out) and '"radice": 12' in out, out

    async def test_la_tmpfs_di_lavoro_si_scrive(self) -> None:
        rc, out, err = await _esegui(
            "import os\n"
            f"open({LAVORO!r} + '/uscita.txt', 'w').write('x' * 10)\n"
            f"print('RIUSCITO', os.path.getsize({LAVORO!r} + '/uscita.txt'), os.getcwd())\n",
            Profilo.CODICE,
        )
        assert rc == 0, err
        assert _riuscito(out) and "10" in out and LAVORO in out, out

    async def test_la_tmpfs_e_volatile(self) -> None:
        """Cio' che il codice scrive non arriva all'host: torna per stdout.

        Due esecuzioni consecutive non si vedono a vicenda, e sull'host non
        compare niente — `LAVORO` non esiste proprio, fuori.
        """
        await _esegui(f"open({LAVORO!r} + '/lasciato.txt', 'w').write('io')", Profilo.CODICE)
        rc, out, _ = await _esegui(
            _tenta(f"open({LAVORO!r} + '/lasciato.txt').read()"), Profilo.CODICE
        )
        assert rc == 0 and not _riuscito(out), "la tmpfs sopravvive fra due esecuzioni"
        assert not Path(LAVORO).exists(), f"{LAVORO} e' comparso sull'host"


class TestControllo:
    """⚠️ Il giro che rende veri gli altri.

    Se queste asserzioni cadono, ogni test qui sopra e' verde per il motivo
    sbagliato: non perche' la sandbox blocca, ma perche' non c'e' niente da
    leggere su questa macchina.
    """

    @pytest.mark.parametrize("nome", list(SEGRETI))
    async def test_il_profilo_vecchio_li_vede_tutti(self, nome: str) -> None:
        p = SEGRETI[nome]
        if not p.exists():
            pytest.skip(f"{p} non esiste su questa macchina")
        # `os.access` e non `open().read()`: si accerta la LEGGIBILITA', non
        # si tira dentro il contenuto. Il segreto non deve passare da qui.
        rc, out, err = await _esegui(
            f"import os; print('RIUSCITO' if os.access({str(p)!r}, os.R_OK) else 'FALLITO')",
            Profilo.STRUMENTO,
        )
        assert rc == 0, err
        assert _riuscito(out), (
            f"{p} non e' leggibile nemmeno col profilo vecchio: i test di "
            f"segregazione qui sopra non stanno provando niente"
        )

    async def test_il_profilo_vecchio_elenca_la_home(self) -> None:
        rc, out, err = await _esegui(
            "import os; v = os.listdir(os.path.expanduser('~')); print('RIUSCITO', len(v))",
            Profilo.STRUMENTO,
        )
        assert rc == 0, err
        assert _riuscito(out), "il profilo vecchio non elenca la home"
        assert int(out.split()[1]) > 0


# ── la politica, prima di eseguire ───────────────────────────────────────────


class TestPolitica:
    def test_il_profilo_non_ha_un_valore_predefinito(self) -> None:
        """Un chiamante che se lo dimentica non parte, invece di ricevere il
        piu' permissivo. E' la stessa forma del gancio di conferma."""
        import inspect

        for f in (run_sandboxed, build_argv):
            par = inspect.signature(f).parameters["profilo"]
            assert par.default is inspect.Parameter.empty, (
                f"{f.__name__} ha un profilo predefinito: un chiamante "
                f"distratto otterrebbe {par.default}"
            )

    def test_codice_rifiuta_i_percorsi_scrivibili(self, tmp_path: Path) -> None:
        """Il risultato torna per stdout, non per un file sull'host."""
        with pytest.raises(SandboxPolicyError, match="stdout"):
            build_argv([INTERPRETE], [tmp_path], [tmp_path], Profilo.CODICE)

    def test_codice_rifiuta_una_cwd_dellhost(self, tmp_path: Path) -> None:
        with pytest.raises(SandboxPolicyError, match="tmpfs"):
            build_argv([INTERPRETE], [], [tmp_path], Profilo.CODICE, chdir=tmp_path)

    def test_codice_rifiuta_l_interprete_di_un_venv(self) -> None:
        """Un venv e' un albero di puntatori, non un interprete autonomo.

        Montarne il solo binario da' «Could not find platform independent
        libraries»; montarne l'albero porterebbe dentro i site-packages del
        progetto, che e' piu' superficie, non meno.
        """
        venv = Path(sys.prefix) / "bin" / "python3"
        if not (Path(sys.prefix) / "pyvenv.cfg").is_file():
            pytest.skip("i test non girano in un venv")
        with pytest.raises(SandboxPolicyError, match="venv"):
            build_argv([str(venv)], [], [], Profilo.CODICE)

    def test_codice_rifiuta_un_percorso_relativo(self) -> None:
        with pytest.raises(SandboxPolicyError, match="assoluto"):
            build_argv(["bin/python3"], [], [], Profilo.CODICE)

    def test_argv_vuoto_rifiutato_in_entrambi(self) -> None:
        for profilo in Profilo:
            with pytest.raises(SandboxPolicyError, match="argv vuoto"):
                build_argv([], [], [], profilo)


class TestArgv:
    """Cio' che l'argv dice di montare, letto come lo legge bubblewrap."""

    def test_codice_non_monta_la_radice_dellhost(self) -> None:
        a = build_argv([INTERPRETE], [], [], Profilo.CODICE)
        assert "--tmpfs" in a and a[a.index("--tmpfs") + 1] == "/"
        coppie = list(zip(a, a[1:]))
        assert ("--ro-bind", "/") not in coppie, (
            "il profilo CODICE monta la radice dell'host: e' il difetto che "
            "ADR-008 esiste per chiudere"
        )

    def test_codice_monta_SOLO_librerie_e_interprete(self) -> None:
        """L'elenco completo di cio' che entra, non l'assenza di un sospetto.

        ⚠️ La prima versione asseriva soltanto «`/etc` non e' fra i bind». Era
        verde anche col profilo vecchio — che monta `/` e quindi non nomina
        `/etc` — cioe' verde per il motivo sbagliato. Il controllo di ADR-008
        l'ha scoperto: era l'unico test di questa classe a sopravvivere alla
        reintroduzione del profilo largo.

        Un'allowlist si verifica elencandola. Misurato: CPython parte cosi',
        senza `/etc`; se un giorno servisse, sara' UN file aggiunto di
        proposito e questo test lo fara' notare.
        """
        a = build_argv([INTERPRETE], [], [], Profilo.CODICE)
        montati = {a[i + 1] for i, v in enumerate(a) if v in ("--ro-bind", "--bind")}
        atteso = {d for d in LIBRERIE if Path(d).exists()}
        atteso |= {str(s) for s, _ in albero_interprete(Path(INTERPRETE))}
        assert montati == atteso, (
            f"il profilo CODICE monta qualcosa che non e' in elenco.\n"
            f"  in piu': {sorted(montati - atteso)}\n"
            f"  in meno: {sorted(atteso - montati)}"
        )
        assert not [m for m in montati if m == "/etc" or m.startswith("/etc/")]

    def test_codice_pulisce_l_ambiente(self) -> None:
        a = build_argv([INTERPRETE], [], [], Profilo.CODICE)
        assert "--clearenv" in a
        assert "HOME" not in a, (
            "HOME impostata renderebbe `expanduser('~')` una directory vera e "
            "scrivibile: resta assente di proposito"
        )

    def test_strumento_e_rimasto_quello_della_fase_1(self) -> None:
        """ADR-008 aggiunge un profilo, non ne cambia uno gia' verificato."""
        a = build_argv(["/bin/true"], [], [], Profilo.STRUMENTO)
        coppie = list(zip(a, a[1:]))
        assert ("--ro-bind", "/") in coppie
        assert "--unshare-all" in a and "--die-with-parent" in a
        assert "--clearenv" not in a

    def test_l_interprete_di_sistema_non_tira_dentro_home(self) -> None:
        coppie = albero_interprete(Path(INTERPRETE))
        casa = str(Path.home())
        assert not [d for _, d in coppie if str(d).startswith(casa)], coppie

    def test_un_interprete_fuori_da_usr_porta_il_suo_albero(self) -> None:
        """Il caso di uv, che tiene i Python in `~/.local/share/uv/python/...`.

        E' l'unica eccezione al «nessun pezzo di $HOME», ed e' dichiarata in
        ADR-008: quell'albero contiene un interprete e la sua stdlib.
        """
        reale = Path(sys.executable).resolve()
        if str(reale).startswith("/usr/"):
            pytest.skip("l'interprete dei test e' gia' sotto /usr")
        coppie = albero_interprete(reale)
        prefissi = [s for s, _ in coppie]
        assert reale.parent.parent in prefissi, coppie
