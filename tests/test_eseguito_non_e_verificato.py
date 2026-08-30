"""«Eseguito» non e' «verificato» — ADR-012.

`ToolResult(ok=True)` significa **una cosa sola**: la chiamata non ha sollevato
un'eccezione. Non significa che il file sia sul disco, che l'impostazione abbia
avuto effetto, che il cestino contenga cio' che doveva contenere.

Questo file tiene la regola che rende l'ADR non decorativo — **un tool senza
verificatore torna `NON_VERIFICATO`, non `RIUSCITO`** — e le due che la
proteggono dal diventare un timbro:

    fonte indipendente   un verificatore che rilegge attraverso lo stesso
                         codice del tool prova solo che il codice e' coerente
                         con se' stesso. Il campo `fonte` deve nominare
                         qualcosa di DIVERSO dal tool, e `registry.invoke`
                         declassa chi non lo fa.
    percorsi dal PIANO   i tre verificatori guardano i percorsi RISOLTI del
                         piano congelato, mai gli argomenti: risolverli di
                         nuovo rifarebbe cio' che §6.2 esiste per impedire.

⚠️ ADR-012 affidava la prima alla revisione umana — «viene rifiutato in
revisione». Una regola affidata alla disciplina regge finche' qualcuno ha
fretta: qui e' il registro a non poterla saltare, come per la conferma.
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel

from core.tools import registry as R
from core.tools.confirm import Operazione, Piano
from core.traccia import Origine, Traccia
from core.verifica import NESSUNA_FONTE, Verdetto, Verifica


class Args(BaseModel):
    x: int = 1


async def _ok(a):
    return R.ToolResult(ok=True, output=a.x)


def _registra(nome="prova", verifica=None, **extra):
    R.register(R.Tool(name=nome, description="d", args_schema=Args,
                      side_effect=False, handler=_ok, verifica=verifica, **extra))


# ── ① il tipo ────────────────────────────────────────────────────────────────


class TestIlVerdetto:
    def test_i_valori_sono_QUATTRO_e_ognuno_ha_un_produttore(self) -> None:
        """L'elenco e' chiuso, ed e' una misura — non un disegno.

        ADR-012 ne elencava sei. `ANNULLATO` e `DEGRADATO` non li emetteva
        nessuno: niente annulla un tool — la conferma e' rifiutata o scaduta, e
        sono entrambe un blocco — e il ripiego annunciato dell'invariante 12
        riguarda la VOCE, che non e' un tool. E' la stessa regola applicata a
        `Origine` nella fetta 1, e questa riga e' il test che la impone.

        I quattro produttori, uno per valore:
          RIUSCITO / FALLITO   `Verifica.confronta`, dal verificatore
          BLOCCATO             `registry._bloccata`, dal registro
          NON_VERIFICATO       `registry._verifica` quando non c'e' verificatore
        """
        assert {v.value for v in Verdetto} == {
            "riuscito", "fallito", "bloccato", "non_verificato"
        }

    def test_una_verifica_senza_fonte_non_e_una_verifica(self) -> None:
        """Il campo che porta tutto il peso di ADR-012: senza, «ho guardato» e
        «non ho guardato» diventano la stessa riga."""
        with pytest.raises(ValueError, match="fonte"):
            Verifica(atteso="a", osservato="b", verdetto=Verdetto.RIUSCITO,
                     fonte="   ", quando=0.0)

    def test_confronta_decide_il_verdetto_e_non_chi_chiama(self) -> None:
        assert Verifica.confronta("62 byte", "62 byte",
                                  fonte="os.stat").verdetto is Verdetto.RIUSCITO
        assert Verifica.confronta("62 byte", "52 byte",
                                  fonte="os.stat").verdetto is Verdetto.FALLITO

    def test_la_verifica_e_congelata(self) -> None:
        v = Verifica.confronta("a", "a", fonte="os.stat")
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.verdetto = Verdetto.FALLITO


# ── ② la regola che rende l'ADR non decorativo ───────────────────────────────


class TestSenzaVerificatoreNonSiSa:
    async def test_un_tool_senza_verificatore_torna_NON_VERIFICATO(self) -> None:
        """**Il criterio 1 di ADR-012.** `ok=True` e `non_verificato` insieme:
        non e' una contraddizione, sono due assi. Senza questo valore «non lo
        so» collassa su «si'», e il registro comincia a raccontare."""
        _registra()
        r = await R.invoke("prova", {"x": 3})
        assert r.ok is True
        assert r.verifica.verdetto is Verdetto.NON_VERIFICATO
        assert r.verifica.fonte == NESSUNA_FONTE
        assert "non ha un verificatore" in r.verifica.osservato

    async def test_e_NON_torna_riuscito(self) -> None:
        _registra()
        assert (await R.invoke("prova")).verifica.verdetto is not Verdetto.RIUSCITO

    async def test_la_verifica_porta_la_traccia(self) -> None:
        """ADR-011 → ADR-012: una verifica che non si ritrova non serve a
        niente, ed e' la ragione dell'ordine fra le due fette."""
        _registra()
        t = Traccia.nuova(Origine.VOCE)
        r = await R.invoke("prova", traccia=t)
        assert r.verifica.traccia_id == t.id and r.traccia_id == t.id

    async def test_un_verificatore_vero_dice_RIUSCITO(self) -> None:
        _registra(verifica=lambda a, p, r: Verifica.confronta(
            "3", str(r.output), fonte="il chiamante"))
        assert (await R.invoke("prova", {"x": 3})).verifica.verdetto is Verdetto.RIUSCITO

    async def test_un_verificatore_asincrono_va_bene_uguale(self) -> None:
        async def tardi(a, p, r):
            await asyncio.sleep(0)
            return Verifica.confronta("3", str(r.output), fonte="il chiamante")

        _registra(verifica=tardi)
        assert (await R.invoke("prova", {"x": 3})).verifica.verdetto is Verdetto.RIUSCITO


class TestUnVerificatoreNonSiAutocertifica:
    """Criterio 3 di ADR-012, **imposto invece che raccomandato**."""

    async def test_chi_nomina_se_stesso_viene_declassato(self) -> None:
        """Rileggere attraverso lo stesso codice non prova che l'azione sia
        riuscita: prova che il codice e' coerente con se' stesso. Il verde
        sarebbe una bugia con due firme."""
        _registra(verifica=lambda a, p, r: Verifica.confronta(
            "x", "x", fonte="rileggo con prova stesso"))
        r = await R.invoke("prova")
        assert r.verifica.verdetto is Verdetto.NON_VERIFICATO
        assert "se' stesso" in r.verifica.osservato

    async def test_un_verificatore_che_CADE_non_annulla_l_azione(self) -> None:
        """L'azione **e' gia' successa**: un verificatore rotto non deve poterla
        trasformare in un errore. Vale `NON_VERIFICATO`, che e' cio' che si sa."""
        def esplode(a, p, r):
            raise RuntimeError("il disco non risponde")

        _registra(verifica=esplode)
        r = await R.invoke("prova")
        assert r.ok is True
        assert r.verifica.verdetto is Verdetto.NON_VERIFICATO
        assert "il disco non risponde" in r.verifica.osservato


class TestBloccatoLoDiceIlRegistro:
    """Il verdetto che non ha bisogno di un verificatore per essere vero."""

    async def test_argomenti_invalidi(self) -> None:
        """Il tool non e' partito, e il registro lo sa con CERTEZZA. Non e'
        «non si sa»: `NON_VERIFICATO` vorrebbe dire «potrebbe essere successo e
        non ho guardato», e qui non e' successo."""
        _registra()
        r = await R.invoke("prova", {"x": "non un numero"})
        assert r.ok is False and r.verifica.verdetto is Verdetto.BLOCCATO

    async def test_nessuna_conferma_collegata(self) -> None:
        """Fail-closed dell'invariante 3: i tool distruttivi non girano."""
        async def planner(a):
            return Piano(tool="d", riepilogo="", operazioni=(
                Operazione(tipo="write", destinazione=Path("/tmp/x")),))

        async def h(a, piano=None):
            return R.ToolResult(ok=True)

        R.register(R.Tool(name="distruttivo", description="d", args_schema=Args,
                          side_effect=True, planner=planner, handler=h))
        r = await R.invoke("distruttivo")
        assert r.verifica.verdetto is Verdetto.BLOCCATO
        assert "fail-closed" in r.verifica.osservato

    async def test_il_Signore_dice_no(self) -> None:
        async def planner(a):
            return Piano(tool="d", riepilogo="", operazioni=(
                Operazione(tipo="write", destinazione=Path("/tmp/x")),))

        async def h(a, piano=None):
            raise AssertionError("non doveva eseguire")

        async def rifiuta(_p):
            return "rifiutato"

        R.register(R.Tool(name="distruttivo", description="d", args_schema=Args,
                          side_effect=True, planner=planner, handler=h))
        R.set_confirm_hook(rifiuta)
        r = await R.invoke("distruttivo")
        assert r.verifica.verdetto is Verdetto.BLOCCATO
        assert r.verifica.fonte == "registry.invoke", (
            "la fonte e' il REGISTRO: la domanda l'ha posta lui e il no l'ha "
            "ricevuto lui. Non e' il tool a raccontarlo"
        )


# ── ③ i tre verificatori veri, su file veri ──────────────────────────────────


@pytest.fixture
def mondo():
    """L'allowlist dei file su una radice temporanea, con la conferma aperta."""
    from tests.eval_tools import FakeSettings

    from core.platform import paths
    from core.tools.files import register_file_tools

    d = Path(tempfile.mkdtemp()).resolve()
    register_file_tools(lambda: FakeSettings([d]), leggi_paths=paths)

    async def si(_p):
        return "approvato"

    R.set_confirm_hook(si)
    return d


class TestITreVerificatori:
    async def test_create_file_misura_i_BYTE_non_i_caratteri(self, mondo) -> None:
        """⚠️ **Il difetto che scrivere questo verificatore ha trovato.**

        `_create_file` riferiva `bytes: len(a.content)` — un conto di CARATTERI
        sotto un nome che dice byte. Misurato il 30 agosto: «pero' e' cosi', con
        aeiou accentate» sono 52 caratteri e **62 byte** sul disco. Nessuno
        leggeva quel campo, quindi il difetto era invisibile.

        L'atteso viene dagli ARGOMENTI e l'osservato dal FILESYSTEM: se il
        verificatore si fidasse del referto del tool, il tool si
        autocertificherebbe — ed e' precisamente cio' che ADR-012 vieta.
        """
        testo = "però è così, con àèìòù — accenti e un trattino lungo"
        assert len(testo) != len(testo.encode("utf-8")), "il caso non e' quello"
        r = await R.invoke("create_file",
                           {"path": str(mondo / "x.txt"), "content": testo})
        assert r.verifica.verdetto is Verdetto.RIUSCITO
        assert str(len(testo.encode("utf-8"))) in r.verifica.atteso
        assert (mondo / "x.txt").stat().st_size == len(testo.encode("utf-8"))
        assert r.output["bytes"] == len(testo.encode("utf-8")), (
            "il campo si chiama `bytes` e adesso contiene byte"
        )

    async def test_create_file_guarda_il_PIANO_e_non_gli_argomenti(
        self, mondo
    ) -> None:
        """§6.2: fra la conferma e l'esecuzione un symlink puo' essere cambiato.

        Un verificatore che risolvesse di nuovo `a.path` guarderebbe un percorso
        DIVERSO da quello toccato, con l'aria di aver verificato — cioe' il
        difetto peggiore possibile in un verificatore. Qui i due percorsi si
        fanno divergere apposta e si guarda quale dei due finisce nel verdetto.
        """
        from core.tools.files import CreateFileArgs

        vero = mondo / "vero.txt"
        vero.write_text("dodici byte")
        tool = R.get("create_file")
        args = CreateFileArgs(path=str(mondo / "MENZOGNA.txt"), content="dodici byte")
        piano = Piano(tool="create_file", riepilogo="",
                      operazioni=(Operazione(tipo="create", destinazione=vero),))
        v = tool.verifica(args, piano, R.ToolResult(ok=True))
        assert "vero.txt" in v.osservato and "MENZOGNA" not in v.osservato

    async def test_trash_guarda_i_due_estremi(self, mondo) -> None:
        """L'origine non c'e' piu' **e** la copia nel cestino c'e'. Entrambe."""
        bersaglio = mondo / "da-cestinare.txt"
        bersaglio.write_text("ciao")
        r = await R.invoke("trash_path", {"path": str(bersaglio)})
        assert r.verifica.verdetto is Verdetto.RIUSCITO
        assert "os.path.exists" in r.verifica.fonte
        assert not bersaglio.exists()
        assert os.path.exists(r.output["recuperabile_da"])

    async def test_trash_DICHIARA_quando_non_sa_dove_e_finito(self, mondo) -> None:
        """La meta' non osservabile si dichiara, non si finge.

        ⚠️ `_trash` faceva gia' questa ricerca e riferiva `verificato: bool` —
        poi restituiva `ok=True` comunque. Un'osservazione che non ha effetto
        non e' una verifica: e' il quarto esempio del pattern che ADR-012
        elenca, e il piu' istruttivo, perche' il campo c'era ed era corretto.
        """
        from core.tools.files import PathArgs

        tool = R.get("trash_path")
        sparito = mondo / "mai-esistito.txt"
        piano = Piano(tool="trash_path", riepilogo="",
                      operazioni=(Operazione(tipo="trash", sorgente=sparito),))
        v = tool.verifica(PathArgs(path=str(sparito)), piano,
                          R.ToolResult(ok=True, output={"recuperabile_da": None}))
        assert v.verdetto is Verdetto.NON_VERIFICATO
        assert "non e' stata riferita" in v.fonte

    async def test_imposta_valore_rilegge_il_TOML_dal_disco(self, paths) -> None:
        from core.settings import SettingsStore
        from core.tools.impostazioni import register_settings_tool

        store = SettingsStore(paths)
        register_settings_tool(lambda: store.current, paths.config_dir)

        async def si(_p):
            return "approvato"

        R.set_confirm_hook(si)
        r = await R.invoke("imposta_valore",
                           {"chiave": "ui.target_fps", "valore": 45})
        assert r.ok and r.verifica.verdetto is Verdetto.RIUSCITO
        assert "tomlkit" in r.verifica.fonte
        assert "45" in r.verifica.osservato
        # La fonte e' il file, non il referto del tool: si legge col disco.
        testo = (paths.config_dir() / "settings.toml").read_text(encoding="utf-8")
        assert "45" in testo and "#" in testo, "i commenti sono sopravvissuti"

    async def test_nessuno_dei_tre_nomina_se_stesso_nella_fonte(
        self, mondo
    ) -> None:
        """Criterio 3, applicato ai verificatori VERI invece che a un finto.

        ⚠️ Il controllo di `registry.invoke` declassa chi si autocertifica, ma
        lo fa **dopo** che l'azione e' avvenuta: il verdetto e' onesto e il file
        e' gia' scritto. Questa riga lo scopre prima — si eseguono i tre
        verificatori e si guarda che cosa dichiarano come fonte.
        """
        from core.tools.files import CreateFileArgs, PathArgs

        f = mondo / "a.txt"
        f.write_text("x")
        casi = [
            ("create_file", CreateFileArgs(path=str(f), content="x"),
             Piano(tool="create_file", riepilogo="",
                   operazioni=(Operazione(tipo="create", destinazione=f),)),
             R.ToolResult(ok=True)),
            ("trash_path", PathArgs(path=str(f)),
             Piano(tool="trash_path", riepilogo="",
                   operazioni=(Operazione(tipo="trash", sorgente=f),)),
             R.ToolResult(ok=True, output={"recuperabile_da": str(f)})),
        ]
        for nome, args, piano, r in casi:
            tool = R.get(nome)
            assert tool.verifica is not None, f"{nome} non ha un verificatore"
            v = tool.verifica(args, piano, r)
            assert nome not in v.fonte, (
                f"{nome} dichiara come fonte se' stesso ({v.fonte!r}): "
                "rileggere attraverso lo stesso codice non e' una verifica"
            )
            assert v.fonte.strip(), f"{nome}: fonte vuota"


# ── ④ il verdetto si vede nel diario, con la sua traccia ─────────────────────


class TestSiVedeNelDiario:
    """Criterio 1: «e si vede nel diario, con la sua traccia»."""

    async def test_la_riga_porta_ok_E_verdetto(self, tmp_path) -> None:
        from core.diario import Diario
        from core.engine import Engine

        class _Motore:
            _compito_di_sfondo = Engine._compito_di_sfondo
            _esito_confermato = Engine._esito_confermato

            def __init__(self, d):
                self._diario, self._compiti = d, set()
                self._ws = _WsMuto()

        d = Diario(tmp_path)
        t = Traccia.nuova(Origine.UI)
        piano = Piano(tool="imposta_valore", riepilogo="",
                      operazioni=(Operazione(tipo="write",
                                             destinazione=tmp_path / "s.toml"),))
        r = R.ToolResult(ok=True, traccia_id=t.id,
                         verifica=Verifica.non_verificata("nessuno ha guardato",
                                                          traccia_id=t.id))
        await _Motore(d)._esito_confermato(piano, r)
        riga = d.leggi(flusso="azione")[0]
        assert riga["ok"] is True, "il tool non ha sollevato"
        assert riga["verdetto"] == "non_verificato", (
            "e nessuno e' andato a guardare. Le due cose stanno ACCANTO: "
            "sostituirne una con l'altra perderebbe la differenza che ADR-012 "
            "introduce"
        )
        assert riga["traccia"] == t.id
        assert riga["osservato"] == "nessuno ha guardato"


class _WsMuto:
    async def broadcast(self, _msg):
        return None


# ── ⑤ jarvis doctor conta i verificatori ─────────────────────────────────────


class TestIlDottoreLoConta:
    """Criterio 4 di ADR-012."""

    def test_warn_quando_un_tool_DISTRUTTIVO_e_scoperto(self) -> None:
        from core.doctor import _check_verifica

        c = _check_verifica({"tools": [
            {"name": "create_file", "side_effect": True, "verificabile": True},
            {"name": "move_path", "side_effect": True, "verificabile": False},
            {"name": "list_dir", "side_effect": False, "verificabile": False},
        ]})
        assert c.stato == "warn" and "move_path" in c.dettaglio
        assert "1/3" in c.dettaglio, "il conto dei verificatori"

    def test_ok_quando_i_distruttivi_sono_coperti(self) -> None:
        from core.doctor import _check_verifica

        c = _check_verifica({"tools": [
            {"name": "create_file", "side_effect": True, "verificabile": True},
            {"name": "list_dir", "side_effect": False, "verificabile": False},
        ]})
        assert c.stato == "ok"

    def test_a_core_spento_dice_che_non_lo_sa(self) -> None:
        """⚠️ Il registro dei tool vive nel processo del CORE, e il dottore e'
        un altro processo: chiederlo al registro locale darebbe **zero** — un
        numero falso e tranquillizzante al contrario."""
        from core.doctor import _check_verifica

        assert _check_verifica(None).stato == "n/d"


class TestAncheIlNoLasciaUnaRIGA:
    """⚠️ **Trovato provando il rifiuto dal vivo con Electron, il 31 agosto.**

    `_ESITO` — il gancio di §6.2 — girava solo sul ramo approvato. Una domanda
    **rifiutata** non lasciava nessuna riga di diario: il log l'aveva, il
    registro che una persona rilegge no. E `Verdetto.BLOCCATO`, che ADR-012 ha
    introdotto proprio per questo, non poteva arrivarci per la via della pagina
    — dove non c'e' un `esegui_t0` a scrivere la riga.

    `esegui_t0` lo dice gia' della voce: «ogni esito, non solo quelli riusciti.
    Il registro serve a spiegare perche' qualcosa NON e' successo: un intento
    rifiutato e' la riga piu' utile che ci sia». Adesso vale anche per §6.2, da
    qualunque origine la domanda arrivi: **un piano, una risposta.**
    """

    @staticmethod
    def _distruttivo():
        from pydantic import BaseModel

        from core.tools import registry as R
        from core.tools.confirm import Operazione, Piano

        class A(BaseModel):
            x: int = 1

        async def planner(a):
            return Piano(tool="d", riepilogo="",
                         operazioni=(Operazione(tipo="write",
                                                destinazione=Path("/tmp/x")),))

        async def h(a, piano=None):
            raise AssertionError("non doveva eseguire")

        R.register(R.Tool(name="distruttivo", description="d", args_schema=A,
                          side_effect=True, planner=planner, handler=h))
        return R

    @pytest.mark.parametrize("risposta", ["rifiutato", "scaduto"])
    async def test_il_gancio_gira_anche_sul_NO(self, risposta) -> None:
        R = self._distruttivo()
        riferiti: list = []

        async def no(_p):
            return risposta

        async def esito(piano, r):
            riferiti.append((piano, r))

        R.set_confirm_hook(no)
        R.set_result_hook(esito)
        r = await R.invoke("distruttivo", traccia=Traccia.nuova(Origine.UI))

        assert r.ok is False
        assert riferiti, "una domanda rifiutata non ha lasciato nessuna risposta"
        _, riferito = riferiti[0]
        assert riferito.verifica.verdetto is Verdetto.BLOCCATO

    async def test_e_la_riga_di_diario_porta_BLOCCATO(self, tmp_path) -> None:
        """Il giro fino al registro, con `_esito_confermato` vero."""
        import asyncio

        from core.diario import Diario
        from core.engine import Engine
        from core.tools.confirm import Operazione, Piano

        class _Motore:
            _compito_di_sfondo = Engine._compito_di_sfondo
            _esito_confermato = Engine._esito_confermato

            def __init__(self, d):
                self._diario, self._compiti = d, set()
                self._ws = _WsMuto()

        R = self._distruttivo()
        d = Diario(tmp_path)
        motore = _Motore(d)

        async def no(_p):
            return "rifiutato"

        R.set_confirm_hook(no)
        R.set_result_hook(motore._esito_confermato)
        t = Traccia.nuova(Origine.UI)
        await R.invoke("distruttivo", traccia=t)
        await asyncio.sleep(0)

        righe = d.leggi(flusso="azione")
        assert len(righe) == 1, "il no non ha lasciato una riga"
        assert righe[0]["ok"] is False
        assert righe[0]["verdetto"] == "bloccato"
        assert righe[0]["traccia"] == t.id
        assert "rifiutato" in righe[0]["osservato"]

    async def test_un_referto_che_CADE_non_rompe_il_rifiuto(self) -> None:
        """Stessa regola del ramo approvato: un registro che cade non e' una
        ragione per fingere che la domanda non sia stata posta."""
        R = self._distruttivo()

        async def no(_p):
            return "rifiutato"

        async def rotto(_piano, _r):
            raise OSError("disco pieno")

        R.set_confirm_hook(no)
        R.set_result_hook(rotto)
        r = await R.invoke("distruttivo", traccia=Traccia.nuova(Origine.UI))
        assert r.ok is False and r.verifica.verdetto is Verdetto.BLOCCATO
