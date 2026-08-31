"""La traccia non si perde per strada — ADR-011.

Il 30 agosto 2026, dato il diario di una giornata, **non si poteva rispondere a
«che cosa e' successo in quel turno»**: `annota(flusso, **campi)` non portava
nessun id e `registry.invoke` nemmeno. Questo file tiene le due meta' del
rimedio.

## Una guardia, e il punto cieco che l'avrebbe resa inutile

Il parametro su `registry.invoke()` e' **opzionale** — obbligatorio romperebbe
una sessantina di chiamate nei test senza aggiungere una sola prova — quindi
l'imposizione la fa una scansione AST di `core/`.

⚠️ **Una guardia che cerca soltanto nodi `Call` e' cieca proprio sul percorso
che deve proteggere**, ed e' il difetto piu' pericoloso di questa fetta:

    core/engine.py       await self._ronda.esegui(p, registry.invoke, ...)
    core/protocolli.py   r = await invoca(p.tool, p.args)

`registry.invoke` e' passato **per riferimento**, non chiamato. Una guardia
ingenua trova le tre chiamate di `core/engine.py`, le dichiara tutte in regola,
e il percorso del protocollo resta senza traccia **con la guardia verde**.

E' la stessa forma del difetto che `scripts/orfani.py` ha trovato in
`riavvia_dopo_guasto`, ed e' la stessa che questo repository ha appena trovato
in `TestGliInvariantiNonDivergono.blocco()`: **lo strumento diceva ok perche'
guardava dalla parte sbagliata.** Quindi tre regole, non una:

    1. CHIAMATE      ogni `Call` a una porta passa `traccia=`
    2. RIFERIMENTI   una porta nominata fuori da `Call` e' VIETATA, salvo che
                     sia argomento di un inoltratore DICHIARATO che passa
                     `traccia=`
    3. INOLTRATORI   di ogni inoltratore dichiarato si apre la definizione e si
                     verifica che inoltri davvero

⚠️ **Cio' che la guardia NON sa fare, dichiarato.** Gli inoltratori si
riconoscono per NOME dell'attributo — `x.esegui(...)` conta per `Ronda.esegui`
di chiunque sia `x` — perche' saperlo davvero vorrebbe dire un'inferenza di
tipi. E' lo stesso prezzo che `scripts/orfani.py` dichiara nella propria
intestazione, ed e' accettabile qui perche' l'elenco degli inoltratori e' una
**allowlist corta e firmata**: la guardia puo' perdere un caso, non inventarne
uno. E resta una guardia di FORMA: che una traccia vera scorra davvero lo
provano i test di comportamento in fondo al file, non l'AST.
"""

from __future__ import annotations

import ast
import dataclasses
from dataclasses import dataclass
from typing import ClassVar

import pytest

from core.traccia import LUNGHEZZA_ID, Origine, Traccia
from scripts.orfani import RADICE, _alberi, _sorgenti

#: Le due porte del registry. **Entrambe**: una porta sola coperta e' una porta
#: sola coperta, e `invoke_da_gesture` e' quella da cui passano le gesture.
PORTE = ("invoke", "invoke_da_gesture")

#: Il nome del parametro, ovunque. Un secondo nome sarebbe un secondo vocabolario.
PAROLA = "traccia"


@dataclass(frozen=True)
class Inoltratore:
    """Una funzione a cui una porta del registry si passa **per riferimento**.

    Stessa forma e stessa disciplina di `Dichiarato` in `scripts/orfani.py`: la
    ragione e' un campo obbligato e validato, non una raccomandazione. Un elenco
    che si potesse allungare con una riga muta sarebbe esattamente il posto in
    cui si nasconde il percorso senza traccia.
    """

    modulo: str
    classe: str | None
    nome: str
    #: Il parametro che riceve il callable: e' quello che la regola 3 insegue.
    parametro: str
    perche: str

    MINIMO: ClassVar[int] = 30

    def __post_init__(self) -> None:
        if len(self.perche.strip()) < self.MINIMO:
            raise ValueError(
                f"{self.modulo}:{self.nome} — la ragione e' lunga "
                f"{len(self.perche.strip())} caratteri, e sotto {self.MINIMO} "
                "non e' una ragione ma un timbro."
            )


#: Chi puo' ricevere una porta per riferimento. Oggi uno solo.
INOLTRATORI: tuple[Inoltratore, ...] = (
    Inoltratore(
        modulo="core/protocolli.py", classe="Ronda", nome="esegui",
        parametro="invoca",
        perche="La ronda dei protocolli riceve `registry.invoke` per riferimento "
               "perche' `core/protocolli.py` non deve importare il registro: e' "
               "la stessa inversione con cui il diario riceve `pubblica` e non "
               "sa che cosa sia un socket. La traccia le arriva per parametro e "
               "lei la inoltra, e la regola 3 lo verifica aprendo il corpo.",
    ),
)

# ── la macchina della guardia ────────────────────────────────────────────────


def _nome_chiamato(f: ast.expr) -> str | None:
    """Il nome dell'attributo o della variabile in posizione `func`."""
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _ha_kw(chiamata: ast.Call, parola: str = PAROLA) -> bool:
    return any(k.arg == parola for k in chiamata.keywords)


@dataclass
class _Scansione:
    """Cio' che una passata su un modulo trova."""

    chiamate: list[tuple[int, str, bool]]          # riga, porta, ha traccia
    riferimenti: list[tuple[int, str, bool]]       # riga, porta, e' coperto
    annotazioni: list[tuple[int, bool, bool]]      # riga, ha traccia, e' None


def _scansiona(albero: ast.Module) -> _Scansione:
    nomi_inoltratori = {i.nome for i in INOLTRATORI}
    in_posizione_func: set[int] = set()
    coperti: dict[int, bool] = {}                  # id(nodo) -> il call ha traccia
    chiamate: list[tuple[int, str, bool]] = []
    annotazioni: list[tuple[int, bool, bool]] = []

    for n in ast.walk(albero):
        if not isinstance(n, ast.Call):
            continue
        nome = _nome_chiamato(n.func)
        if nome in PORTE:
            in_posizione_func.add(id(n.func))
            chiamate.append((n.lineno, nome, _ha_kw(n)))
        elif nome == "annota":
            # `annota(flusso, traccia, **campi)`: la traccia e' il SECONDO
            # posizionale, e `None` li' e' una dichiarazione da firmare.
            secondo = n.args[1] if len(n.args) > 1 else None
            per_kw = _ha_kw(n)
            e_none = isinstance(secondo, ast.Constant) and secondo.value is None
            annotazioni.append((n.lineno, secondo is not None or per_kw, e_none))
        elif nome in nomi_inoltratori:
            for a in (*n.args, *(k.value for k in n.keywords)):
                coperti[id(a)] = _ha_kw(n)

    riferimenti: list[tuple[int, str, bool]] = []
    for n in ast.walk(albero):
        if isinstance(n, ast.Attribute):
            nome = n.attr
        elif isinstance(n, ast.Name):
            nome = n.id
        else:
            continue
        if nome in PORTE and id(n) not in in_posizione_func:
            riferimenti.append((n.lineno, nome, coperti.get(id(n), False)))
    return _Scansione(chiamate, riferimenti, annotazioni)


@pytest.fixture(scope="module")
def scansioni() -> dict[str, _Scansione]:
    """Una passata sola su tutto `core/`, riusando il lettore di `orfani.py`.

    ⚠️ Si riusa `_sorgenti`/`_alberi` invece di riscriverli: un secondo lettore
    di AST sarebbe una seconda fonte di verita' su che cosa sia «il codice di
    `core/`», e i due divergerebbero al primo file escluso da uno solo dei due.
    """
    alberi = _alberi(_sorgenti(RADICE, "core"))
    return {p.relative_to(RADICE).as_posix(): _scansiona(a) for p, a in alberi.items()}


# ── ① il tipo, e l'elenco chiuso ─────────────────────────────────────────────


class TestIlTipo:
    def test_le_origini_sono_CINQUE(self) -> None:
        """L'elenco e' chiuso, ed e' una misura — non un disegno.

        La prima stesura di ADR-011 ne elencava **sei**, e il sesto — «testo
        dalla scrivania» — non esiste: `core/ws_server.py` accetta cinque tipi
        di messaggio provati uno per uno, `app/preload.js` espone quattro verbi
        dichiarando che restano quattro, e `esegui_t0()` ha un solo chiamante di
        produzione, che viene dalla voce.

        Un valore nuovo qui dentro senza un produttore che lo emetta e' un test
        rosso: **e' questa riga**. Chi lo aggiunge aggiunge anche il produttore,
        oppure non lo aggiunge.
        """
        assert {o.value for o in Origine} == {
            "voce", "gesture", "protocollo", "ui", "avvio"
        }

    def test_la_traccia_ha_TRE_campi_e_non_e_un_contesto(self) -> None:
        """Invariante 17. Un quarto campo sarebbe **stato**, e questa smetterebbe
        di essere una traccia per diventare il contesto che T1 gia' tiene."""
        assert [f.name for f in dataclasses.fields(Traccia)] == ["id", "origine", "t0"]

    def test_l_id_e_corto_e_non_viene_dal_tempo(self) -> None:
        """Dodici esadecimali, e da `uuid4`: due turni nello stesso millisecondo
        collidono, e l'ora di sistema puo' saltare all'indietro."""
        ids = {Traccia.nuova(Origine.VOCE).id for _ in range(500)}
        assert len(ids) == 500
        assert all(len(i) == LUNGHEZZA_ID and int(i, 16) >= 0 for i in ids)

    def test_un_origine_inventata_non_entra(self) -> None:
        """Fail-closed sul NOME, come il diario davanti a un flusso ignoto."""
        with pytest.raises(ValueError):
            Traccia.nuova("testo")

    def test_la_durata_sta_sull_orologio_monotono(self) -> None:
        t = Traccia.nuova(Origine.AVVIO)
        assert t.durata_ms >= 0.0
        assert t.t0 > 0.0


# ── ② la guardia ─────────────────────────────────────────────────────────────


class TestLaGuardia:
    """Le tre regole. La seconda e la terza esistono per un difetto misurato."""

    def test_regola_1_ogni_chiamata_a_una_porta_passa_la_traccia(
        self, scansioni: dict[str, _Scansione]
    ) -> None:
        nudi = [f"  {m}:{riga}  {porta}(...)"
                for m, s in scansioni.items()
                for riga, porta, ok in s.chiamate if not ok]
        assert not nudi, (
            f"{len(nudi)} chiamate a una porta del registry senza `traccia=`:\n"
            + "\n".join(sorted(nudi))
            + "\n\nADR-011: ogni cosa che comincia porta una traccia. Il "
              "parametro e' opzionale nella firma perche' obbligatorio "
              "romperebbe ~60 chiamate nei test; qui e' obbligatorio davvero."
        )

    def test_regola_2_una_porta_passata_per_RIFERIMENTO_e_vietata(
        self, scansioni: dict[str, _Scansione]
    ) -> None:
        """Il punto cieco, chiuso.

        `self._ronda.esegui(p, registry.invoke, ...)` non e' una chiamata a
        `invoke`: e' `invoke` consegnato a qualcun altro perche' lo chiami. Una
        guardia che guarda solo i `Call` qui vede zero problemi.
        """
        scoperti = [f"  {m}:{riga}  {porta} passato per riferimento"
                    for m, s in scansioni.items()
                    for riga, porta, coperto in s.riferimenti if not coperto]
        assert not scoperti, (
            f"{len(scoperti)} riferimenti a una porta del registry non "
            f"coperti:\n" + "\n".join(sorted(scoperti))
            + "\n\nUna porta consegnata a qualcun altro perche' la chiami e' "
              "ammessa solo verso un INOLTRATORE dichiarato in INOLTRATORI, e "
              "solo se la chiamata gli passa `traccia=`. Aggiungerne uno "
              "significa scrivere perche'."
        )

    def test_regola_3_un_inoltratore_dichiarato_inoltra_DAVVERO(self) -> None:
        """La riga che rende vero il criterio 6 di ADR-011.

        Non basta che il chiamante passi `traccia=`: bisogna che il corpo
        dell'inoltratore la giri al callable che ha ricevuto. Togliendola da
        `Ronda.esegui`, **questo** test diventa rosso — e le regole 1 e 2
        restano verdi, che e' la dimostrazione di quanto valgono da sole.
        """
        for i in INOLTRATORI:
            albero = _alberi([RADICE / i.modulo])[RADICE / i.modulo]
            corpo = next(
                (n for n in ast.walk(albero)
                 if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                 and n.name == i.nome),
                None,
            )
            assert corpo is not None, f"{i.modulo}: {i.nome} non esiste piu'"
            parametri = {a.arg for a in (*corpo.args.args, *corpo.args.kwonlyargs)}
            assert i.parametro in parametri, (
                f"{i.modulo}:{i.nome} non ha piu' il parametro {i.parametro!r}"
            )
            assert PAROLA in parametri, (
                f"{i.modulo}:{i.nome} e' dichiarato inoltratore ma non prende "
                f"`{PAROLA}`: chi gli passa una porta del registry crede che la "
                "stia inoltrando, e non e' vero."
            )
            inoltra = [
                n for n in ast.walk(corpo)
                if isinstance(n, ast.Call)
                and _nome_chiamato(n.func) == i.parametro
                and _ha_kw(n)
            ]
            assert inoltra, (
                f"{i.modulo}:{i.nome} prende `{PAROLA}` e **non la passa** a "
                f"`{i.parametro}(...)`. La traccia muore qui, in silenzio, e "
                "tutto il percorso a valle risulta senza origine con la guardia "
                "verde. E' il difetto che questa regola esiste per trovare."
            )

    def test_le_due_porte_sono_coperte_entrambe(
        self, scansioni: dict[str, _Scansione]
    ) -> None:
        """Una guardia che copre `invoke` e non `invoke_da_gesture` lascia
        scoperto tutto il percorso delle gesture, che e' proprio quello che nel
        diario non lasciava niente."""
        viste = {porta for s in scansioni.values() for _, porta, _ in s.chiamate}
        assert set(PORTE) <= viste, (
            f"la scansione non ha visto {set(PORTE) - viste}: o il nome e' "
            "cambiato, o la porta non e' piu' chiamata da `core/` — e in "
            "entrambi i casi la guardia non sta guardando quello che crede."
        )

    def test_ogni_annota_di_core_porta_una_traccia(
        self, scansioni: dict[str, _Scansione]
    ) -> None:
        """`Diario.annota` la prende **obbligatoria**: cinque chiamanti, tutti in
        `core/engine.py`, e li' l'assenza e' davvero un errore di tipo. Questa
        regola prende il caso che il tipo non vede — `traccia=None` scritto per
        comodita' invece che per ragione."""
        senza = [f"  {m}:{riga}" for m, s in scansioni.items()
                 for riga, ha, _ in s.annotazioni if not ha]
        assert not senza, (
            "chiamate a `annota()` senza traccia:\n" + "\n".join(sorted(senza))
        )
        # ⚠️ **Il caso «ce l'ha ma e' vuota» NON si vede da qui**, e va detto:
        # `_annota_dialogo` passa `turno.traccia_id`, che vale `""` per gli
        # annunci, e nessuna analisi statica puo' sapere quando. Quella meta'
        # la misura `scripts/orfani.py --diario`, che legge le righe VERE e
        # chiede a ogni produttore senza traccia di essere dichiarato in
        # `SENZA_TRACCIA`. Una guardia di forma e una misura sui dati: due
        # domande diverse, due strumenti, nessuno dei due che finge di
        # rispondere anche all'altra.


# ── ③ il comportamento: che una traccia VERA scorra davvero ──────────────────
#
# La guardia sopra e' di FORMA: dice che il parametro c'e', non che dentro ci
# sia qualcosa. Questi sono i test che lo dicono.


class _MotoreFinto:
    """Le parti di `Engine` che scrivono nel diario, senza il resto del motore.

    Stessa forma dei finti di `tests/test_il_registro_dice_perche.py`: si
    prendono i metodi veri dalla classe vera, cosi' cio' che si misura e' il
    codice di produzione e non una sua imitazione.
    """

    _compito_di_sfondo = None       # riempiti sotto, per non importare in cima
    _annota_dialogo = None
    _annota_instradamento = None
    _annota_gesto = None

    def __init__(self, diario) -> None:
        self._diario, self._compiti = diario, set()


def _monta_finto():
    from core.engine import Engine

    for nome in ("_compito_di_sfondo", "_annota_dialogo",
                 "_annota_instradamento", "_annota_gesto"):
        setattr(_MotoreFinto, nome, getattr(Engine, nome))
    return _MotoreFinto


class TestUnTurnoSiRicongiunge:
    """Criterio 1 di ADR-011, per quanto e' verificabile senza microfono."""

    async def test_le_DUE_uscite_del_wake_portano_LA_STESSA_traccia(self) -> None:
        """Il difetto che il conio in `_turno()` esiste per evitare.

        Un wake produce **due** richiami verso il motore — `su_azione`, che
        finisce in `esegui_t0`, e `su_turno`, che finisce in `_annota_dialogo` e
        `_annota_instradamento`. Se ognuno coniasse il proprio id, le righe
        dello stesso turno porterebbero identificatori diversi: una traccia che
        non ricongiunge niente, con l'aggravante di sembrare a posto.
        """
        from core.voice.pipeline import VoicePipeline
        from core.voice.wake import Trigger

        azioni: list = []
        turni: list = []
        p = VoicePipeline.__new__(VoicePipeline)
        p._su_azione = lambda a, args, t: azioni.append(t)
        p._su_turno = turni.append
        p._audio = _AudioMuto()
        p._in_turno = True

        await p._turno(Trigger("jarvis", "scene:briefing", 0.0, 0.1))

        assert azioni and turni, "il turno non e' partito"
        assert azioni[0].id == turni[0].traccia_id, (
            "`su_azione` e `su_turno` hanno ricevuto due tracce diverse per lo "
            "stesso wake: le righe di quel turno non si ricongiungono."
        )
        assert azioni[0].origine is Origine.VOCE

    async def test_N_righe_di_diario_portano_lo_stesso_id(self, tmp_path) -> None:
        """La catena, dal turno alla riga: `dialogo` e instradamento insieme."""
        import asyncio

        from core.diario import Diario
        from core.voice.pipeline import Turno

        d = Diario(tmp_path)
        finto = _monta_finto()(d)
        t = Traccia.nuova(Origine.VOCE)
        turno = Turno(frase_wake="jarvis", azione=None, strada="t1",
                      testo_utente="apri il coso strano",
                      testo_detto="Vedo, Signore.", traccia_id=t.id)
        finto._annota_dialogo(turno)
        finto._annota_instradamento(turno)
        await asyncio.sleep(0)

        righe = d.leggi(flusso="dialogo") + d.leggi(flusso="azione")
        assert len(righe) == 3, "due battute e un instradamento"
        assert {r["traccia"] for r in righe} == {t.id}, (
            "le righe dello stesso turno portano id diversi"
        )

    async def test_un_ANNUNCIO_dichiara_di_non_avere_un_origine(
        self, tmp_path
    ) -> None:
        """E non se ne inventa una.

        `annuncia()` da' voce a una frase che il sistema dice di se' — il
        ripiego di §12, l'amnesia di ADR-003 — e non ha un turno che la causi.
        `Turno.traccia_id` resta `""`, e `Diario.scrivi` lo normalizza a `None`:
        la riga **dichiara** di non avere un'origine invece di portarne una
        finta. `""` sarebbe un terzo stato che non significa niente.
        """
        import asyncio

        from core.diario import Diario
        from core.voice.pipeline import Turno

        d = Diario(tmp_path)
        finto = _monta_finto()(d)
        finto._annota_dialogo(Turno(frase_wake="", azione=None,
                                    testo_detto="Passo a Whisper, Signore."))
        await asyncio.sleep(0)
        righe = d.leggi(flusso="dialogo")
        assert len(righe) == 1
        assert "traccia" in righe[0] and righe[0]["traccia"] is None


class TestUnGestoLasciaUnaRiga:
    """Criterio 3 — e il buco che esisteva **prima** di ADR-011."""

    async def test_prima_non_lasciava_NIENTE(self, tmp_path) -> None:
        from core.diario import Diario

        d = Diario(tmp_path)
        finto = _monta_finto()(d)
        t = Traccia.nuova(Origine.GESTURE)
        await finto._annota_gesto(t, "espandi_pannello", ok=True,
                                  strada="ui", errore=None)
        righe = d.leggi(flusso="azione")
        assert len(righe) == 1
        assert righe[0]["traccia"] == t.id
        assert righe[0]["da"] == "gesture", (
            "`da` e' gia' il campo che nomina l'origine — voce, conferma, "
            "risveglio — e `gesture` ne e' il quarto valore: FLUSSI non cambia"
        )

    async def test_anche_un_gesto_RIFIUTATO_lascia_la_sua_riga(
        self, tmp_path
    ) -> None:
        """Un intento non ammesso e' un errore di CABLAGGIO, ed e' la riga piu'
        utile che ci sia: `esegui_t0` lo dice gia' della voce."""
        from core.diario import Diario

        d = Diario(tmp_path)
        finto = _monta_finto()(d)
        t = Traccia.nuova(Origine.GESTURE)
        await finto._annota_gesto(t, "formatta_il_disco", ok=False,
                                  strada="nessuna", errore="non e' un tool")
        righe = d.leggi(flusso="azione")
        assert righe[0]["ok"] is False and righe[0]["errore"]
        assert righe[0]["traccia"] == t.id

    async def test_un_registro_che_cade_non_annulla_il_gesto(
        self, tmp_path
    ) -> None:
        """Il gesto **e' gia' avvenuto**: un diario rotto non deve poterlo
        trasformare in un errore. Stessa forma di `_esito_confermato`."""
        from core.diario import Diario

        class _Rotto(Diario):
            async def annota(self, *_a, **_k):
                raise OSError("disco pieno")

        finto = _monta_finto()(_Rotto(tmp_path))
        await finto._annota_gesto(Traccia.nuova(Origine.GESTURE), "x", ok=True,
                                  strada="ui", errore=None)


class TestIlProtocolloUsaIlRecordCheHaGIA:
    """Criterio 4 — e **nessuna** riga di diario in piu'."""

    def test_la_traccia_entra_in_initiatives(self, tmp_path) -> None:
        import json

        from core.memory.store import MemoryStore

        s = MemoryStore(tmp_path)
        t = Traccia.nuova(Origine.PROTOCOLLO)
        s.registra_iniziativa("protocollo", {"nome": "scaricati"}, traccia=t.id)
        riga = json.loads(next(s.initiatives.glob("*.jsonl")).read_text().strip())
        assert riga["traccia"] == t.id and riga["nome"] == "scaricati"

    def test_senza_traccia_la_chiave_c_e_lo_stesso(self, tmp_path) -> None:
        """Il consolidamento notturno scrive senza origine, e la riga lo
        **dichiara**: «vecchia» e «dichiarata senza» devono restare due cose
        diverse, o `--diario` non puo' distinguerle."""
        import json

        from core.memory.store import MemoryStore

        s = MemoryStore(tmp_path)
        s.registra_iniziativa("consolidamento", {"sessione": "2026-08-30"})
        riga = json.loads(next(s.initiatives.glob("*.jsonl")).read_text().strip())
        assert "traccia" in riga and riga["traccia"] is None


class TestLeRigheVecchieSiLeggonoAncora:
    """Criterio 7. Il campo e' **additivo**, e questo lo pinna."""

    def test_una_riga_senza_la_chiave_si_rilegge(self, tmp_path) -> None:
        import json
        import time

        from core.diario import Diario

        vecchia = {"ts": time.time(), "flusso": "azione", "intento": "open_panel",
                   "args": None, "ok": True, "da": "voce", "strada": "ui",
                   "errore": None}
        giorno = time.strftime("%Y-%m-%d")
        (tmp_path / f"{giorno}.jsonl").write_text(
            json.dumps(vecchia, ensure_ascii=False) + "\n", encoding="utf-8")

        righe = Diario(tmp_path).leggi(flusso="azione")
        assert len(righe) == 1 and "traccia" not in righe[0]

    def test_e_lo_script_le_STAMPA(self) -> None:
        """Un lettore che non trova il campo non deve rompersi."""
        import time

        from scripts.diario import _riga, _traccia

        vecchia = {"ts": time.time(), "flusso": "azione", "intento": "open_panel",
                   "ok": True, "da": "voce", "strada": "ui"}
        assert "open_panel" in _riga(vecchia)
        assert _traccia(vecchia).strip() == "", (
            "una riga d'archivio non ha la chiave, e la colonna resta vuota: "
            "non e' la stessa cosa di `None`, che e' una dichiarazione"
        )
        assert _traccia({"traccia": None}).startswith("—")
        assert _traccia({"traccia": "abc123def456"}) == "abc123def456"

    def test_lo_script_STAMPA_anche_una_riga_senza_intento(self) -> None:
        """⚠️ **Trovato provando la ricostruzione su un turno vero, e non da un
        test**: `scripts/diario.py` CADEVA.

        `_annota_instradamento` scrive `intento=None` — la chiave c'e' e vale
        `null` — quindi `d.get("intento", "?")` restituisce `None` e
        `f"{None:16}"` alza `TypeError`. Misurato il 30 agosto sul diario vero:
        **8 righe su 61**, e `--azioni --giorno 2026-08-27` moriva con uno
        stack trace.

        Il difetto e' anteriore ad ADR-011 e particolarmente crudele: quelle
        righe esistono per spiegare **perche' non e' successo niente**, e
        l'unico modo di rileggere un giorno passato si rompeva su quelle.
        """
        import time

        from scripts.diario import _riga

        riga = {"ts": time.time(), "flusso": "azione", "intento": None,
                "args": None, "ok": True, "da": "voce", "strada": "t1",
                "testo": "apri il coso strano"}
        reso = _riga(riga)
        assert "t1" in reso
        assert "apri il coso strano" in reso, (
            "il testo che non ha trovato un comando e' l'unica cosa utile in "
            "quella riga: senza, si legge «e' successo qualcosa» e basta"
        )

    def test_i_tre_stati_si_distinguono_sul_disco_VERO(self) -> None:
        """Le 61 righe scritte prima di ADR-011 stanno ancora li', e la
        scansione le chiama «vecchie» — non orfane.

        ⚠️ Salta se questa macchina non ha un diario: e' una misura sul disco
        dell'utente, e un test che PRETENDE dati veri passerebbe o fallirebbe a
        seconda della macchina. Saltarlo dichiarandolo e' l'unica forma onesta.
        """
        from core.platform import paths
        from scripts.orfani import STATI, scansiona_diario

        dati = paths().data_dir() / "memory_data"
        if not (dati / "diario").is_dir():
            pytest.skip("nessun diario su questa macchina")
        righe = scansiona_diario(dati / "diario", dati / "initiatives")
        if not righe:
            pytest.skip("il diario e' vuoto")
        orfane = [r for r in righe if not STATI[r.stato]]
        assert not orfane, (
            f"{len(orfane)} righe senza traccia e non dichiarate: "
            + ", ".join(sorted({f"{r.archivio}/{r.chiave}" for r in orfane}))
        )


class TestIlTimbroSuToolResult:
    """`invoke()` timbra **ogni** ramo, non solo quello riuscito."""

    @staticmethod
    def _registra():
        from pydantic import BaseModel

        from core.tools import registry as R

        class A(BaseModel):
            x: int = 1

        async def h(a):
            return R.ToolResult(ok=True, output=a.x)

        R.register(R.Tool(name="prova", description="d", args_schema=A,
                          side_effect=False, handler=h))
        return R

    async def test_il_ramo_riuscito(self) -> None:
        R = self._registra()
        t = Traccia.nuova(Origine.UI)
        assert (await R.invoke("prova", {"x": 3}, traccia=t)).traccia_id == t.id

    async def test_e_ANCHE_i_rami_falliti(self) -> None:
        """Sono quelli che contano di piu': spiegano perche' NON e' successo
        niente, ed e' la meta' che si va a cercare quando qualcosa va storto.
        `esegui_t0` lo dice gia' del diario — «un intento rifiutato e' la riga
        piu' utile che ci sia»."""
        R = self._registra()
        t = Traccia.nuova(Origine.VOCE)
        r = await R.invoke("prova", {"x": "non un numero"}, traccia=t)
        assert r.ok is False and r.traccia_id == t.id

    async def test_e_il_fail_closed_della_conferma(self) -> None:
        """Nessun meccanismo di conferma collegato: il tool distruttivo non
        gira (invariante 3), e la riga che lo dice porta la sua origine."""
        from pydantic import BaseModel

        from core.tools import registry as R
        from core.tools.confirm import Piano

        class A(BaseModel):
            x: int = 1

        async def h(a, piano=None):
            return R.ToolResult(ok=True)

        async def planner(a):
            return Piano(tool="d", riepilogo="", operazioni=())

        R.register(R.Tool(name="distruttivo", description="d", args_schema=A,
                          side_effect=True, planner=planner, handler=h))
        t = Traccia.nuova(Origine.GESTURE)
        r = await R.invoke("distruttivo", {}, traccia=t)
        assert r.ok is False and "conferma" in (r.error or "")
        assert r.traccia_id == t.id

    async def test_senza_traccia_resta_None_e_non_una_stringa_vuota(self) -> None:
        R = self._registra()
        assert (await R.invoke("prova", {"x": 1})).traccia_id is None


class _AudioMuto:
    """Un `AudioIO` che non riproduce niente: `_su_trigger` suona un tono."""

    async def play(self, *_a, **_k) -> None:
        return None


class TestIlVerdettoSiVedeNelDiario:
    """⚠️ Il criterio 1 di ADR-012 dice «si vede nel diario», e non si vedeva.

    Fino al 31 agosto 2026 `scripts/diario.py` non nominava `verdetto` in
    nessuna riga — zero occorrenze in tutto il file. `jarvis diario` stampava
    `ok create_file` anche quando il verificatore aveva detto `fallito`, cioe'
    proprio nel caso per cui ADR-012 esiste. Il campo c'era nel JSONL dal 30
    agosto; per leggerlo bisognava aprire il file a mano.
    """

    def _azione(self, **extra) -> dict:
        import time

        return {"ts": time.time(), "flusso": "azione", "intento": "create_file",
                "ok": True, "da": "voce", "strada": "t0", **extra}

    def test_un_ok_smentito_dal_verdetto_si_VEDE(self) -> None:
        from scripts.diario import _riga

        riga = _riga(self._azione(verdetto="fallito",
                                  osservato="il file ha 0 byte sul disco"))
        assert "FALLITO" in riga, "la riga diceva solo `ok`"
        assert "0 byte" in riga, "l'osservato spiega PERCHE', e serve"

    def test_il_verdetto_riuscito_non_ripete_l_osservato(self) -> None:
        """Su un riuscito l'osservato direbbe cio' che `ok` gia' dice, e questo
        e' un registro che si scorre con l'occhio."""
        from scripts.diario import _riga

        riga = _riga(self._azione(verdetto="riuscito", osservato="x" * 40))
        assert "riuscito" in riga and "x" * 40 not in riga

    def test_un_osservato_lunghissimo_si_TRONCA(self) -> None:
        from scripts.diario import LARGHEZZA_OSSERVATO, _riga

        riga = _riga(self._azione(verdetto="fallito", osservato="y" * 500))
        assert "…" in riga and "y" * (LARGHEZZA_OSSERVATO + 1) not in riga

    def test_una_riga_PRE_ADR_012_non_fa_cadere_il_comando(self) -> None:
        """⚠️ La regola e' l'OPPOSTA di quella di `_traccia()`, e va detto.

        Una riga senza traccia e' un orfano — un difetto. Una riga senza
        verdetto e' spesso una riga che non e' l'esecuzione di un tool:
        `_annota_instradamento` scrive `verdetto=None` di proposito. Marcarle
        riempirebbe il registro di trattini che non significano niente.
        """
        from scripts.diario import _riga

        assert "create_file" in _riga(self._azione())
        assert "create_file" in _riga(self._azione(verdetto=None,
                                                   osservato=None))
        assert "None" not in _riga(self._azione(verdetto=None))
