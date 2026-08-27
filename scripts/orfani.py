"""Lo scanner degli orfani — chi in `core/` non ha nessuno che lo chiami.

    uv run python scripts/orfani.py                 # riepilogo leggibile
    uv run python scripts/orfani.py --tutti         # elenca anche i benigni
    uv run python scripts/orfani.py --json          # l'elenco, per la baseline

`docs/SPEC.md` riga 15 racconta cinque difetti della stessa famiglia — «pezzi
scritti, provati, mai congiunti» — trovati non per caso ma con una scansione.
Quello script non e' mai stato committato: e' stato eseguito e buttato, e la
traiettoria che la specifica cita (22, poi 11, poi 7) non e' piu' verificabile
da nessuno. Questo file lo rimette in piedi, e il test accanto gli impedisce
di sparire di nuovo.

⚠️ **I numeri storici NON si riproducono con questo scanner**, e va detto qui
invece che lasciarlo scoprire: lo script originale non esiste piu', quindi la
sua regola di conteggio e' ignota, e il codice e' cambiato di una trentina di
commit. Cio' che questo file ricostruisce e' la MISURA, non la cifra.

## La regola

Per ogni definizione pubblica di `core/` — `def`, `async def`, `class`, nome
che non comincia con `_` — si contano i riferimenti **fuori dal proprio
modulo** e **fuori da `tests/` e `scripts/`**. Zero riferimenti = orfano.

Un `import` NON e' un riferimento. `from .store import MemoryStore` in un
`__init__.py` che poi non lo usa e' una ri-esportazione, non un chiamante: se
contasse, ogni pacchetto nasconderebbe i propri orfani dietro il proprio
`__init__.py`, che e' esattamente il posto dove si nascondono meglio.

## Le categorie

Un orfano non e' automaticamente un difetto, e i falsi positivi noti si
CLASSIFICANO invece di sparire dal conto. Ogni orfano finisce in una
categoria, con la ragione, e ogni categoria dichiara se e' benigna:

- `usato_solo_nel_modulo` — ha chiamanti, tutti in casa propria. Benigno.
- `protocollo` — classe `Protocol`/`ABC`, o un suo membro: si implementa per
  struttura, e nessuno ne scrive il nome. Benigno.
- `implementazione_di_protocollo` — metodo il cui nome e' dichiarato da un
  protocollo di `core/`: lo chiama chi tiene il protocollo, non chi tiene la
  classe. Benigno.
- `eccezione` — classe che deriva da un'eccezione: si dichiara per essere
  sollevata e catturata altrove, e il nome puo' non comparire mai. Benigno.
- `callback_libreria` — nome nell'allowlist qui sotto, in una classe che
  eredita davvero da una base esterna. Lo chiama la libreria. Benigno.
- `solo_test` — ha chiamanti, e stanno tutti in `tests/` o `scripts/`.
  **NON benigno**: e' la firma esatta della famiglia di §5.29, un pezzo
  provato e mai congiunto.
- `da_esaminare` — nessun riferimento, in nessun posto. **NON benigno.**

«Metodi chiamati per attributo» NON e' una categoria, ed e' una scelta:
`R.pianifica(...)` e' un richiamo come un altro, e lo scanner conta gli
`Attribute` insieme ai `Name`. Quel punto cieco si chiude invece di
etichettarlo — una categoria per un caso che si puo' risolvere e' un modo
educato di non risolverlo.

## Cio' che questo scanner NON sa fare

I riferimenti si contano **per nome**, non per tipo: `x.stato()` conta come
richiamo per OGNI `stato` definito in `core/`, di qualunque classe. E' una
scelta, e il suo prezzo e' dichiarato: lo scanner e' generoso e puo' PERDERE
un orfano quando un nome e' comune, mai inventarne uno che non c'e'. Un
falso negativo tace, un falso positivo fa perdere tempo a chi indaga: con
una lista che qualcuno deve leggere davvero, il primo costa meno.

Gli alias di import SI risolvono (`from x import y as z` piu' `z()` conta per
`y`): quel buco c'era, ed e' costato un aggiramento scritto in
`core/engine.py`. L'import in se' continua a non contare.

Non risolve le stringhe: un nome raggiunto solo con `getattr(o, "nome")` o
scritto in un file JSON risulta orfano. Nel core di oggi non accade, ma se
accadesse la categoria giusta e' `da_esaminare` e la risposta e' guardarlo.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

RADICE = Path(__file__).resolve().parent.parent

#: Dove si cercano le definizioni.
SORGENTE = "core"

#: Dove NON si contano i riferimenti. Un test che chiama una funzione non la
#: rende viva: §5.29 e' nata proprio da pezzi che avevano solo test.
ESCLUSE = ("tests", "scripts")

#: Callback che chiama una libreria e non il nostro codice. Allowlist, mai
#: denylist (invariante 2): un nome entra qui solo se si sa CHI lo chiama, e
#: vale solo dentro una classe che eredita davvero da quella base.
CALLBACK_LIBRERIA: dict[str, str] = {
    "on_any_event": "watchdog.events.FileSystemEventHandler",
    "on_created": "watchdog.events.FileSystemEventHandler",
    "on_modified": "watchdog.events.FileSystemEventHandler",
    "on_deleted": "watchdog.events.FileSystemEventHandler",
    "on_moved": "watchdog.events.FileSystemEventHandler",
    "dispatch": "watchdog.events.FileSystemEventHandler",
    "connection_made": "asyncio.BaseProtocol",
    "connection_lost": "asyncio.BaseProtocol",
    "data_received": "asyncio.Protocol",
    "pipe_data_received": "asyncio.SubprocessProtocol",
    "process_exited": "asyncio.SubprocessProtocol",
    "run": "threading.Thread",
}

#: Le categorie che esistono, e quali sono benigne. E' un'allowlist: una
#: categoria che non compare qui non e' un caso nuovo da accogliere, e' un
#: errore dello scanner, e `scansiona()` alza `KeyError` invece di inventarsi
#: se fidarsi o no.
CATEGORIE: dict[str, bool] = {
    "usato_solo_nel_modulo": True,
    "protocollo": True,
    "implementazione_di_protocollo": True,
    "eccezione": True,
    "callback_libreria": True,
    "solo_test": False,
    "da_esaminare": False,
}

#: Basi che rendono una classe un protocollo. `Protocol` e `ABC` per nome,
#: perche' e' cosi' che sono scritte nel core.
BASI_PROTOCOLLO = frozenset({"Protocol", "ABC", "ABCMeta"})

#: Basi che rendono una classe un'eccezione senza bisogno di risolverle.
BASI_ECCEZIONE = frozenset({
    "Exception", "BaseException", "RuntimeError", "ValueError", "TypeError",
    "LookupError", "KeyError", "IndexError", "OSError", "IOError",
    "NotImplementedError", "TimeoutError", "ConnectionError", "PermissionError",
    "FileNotFoundError", "ArithmeticError", "AttributeError", "ImportError",
    "StopIteration", "StopAsyncIteration", "Warning", "UserWarning",
})

#: I nodi in cui una definizione resta raggiungibile da fuori. Dentro il corpo
#: di una funzione no: quella e' una variabile locale con un nome, e nessuno
#: da fuori puo' chiamarla.
CONTENITORI = (ast.Module, ast.ClassDef, ast.If, ast.Try, ast.With)

_DEFINIZIONI = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


@dataclass(frozen=True)
class Definizione:
    """Una `def`/`class` pubblica di `core/`, col posto dove sta."""

    modulo: str
    classe: str | None
    nome: str
    riga: int
    tipo: str


@dataclass(frozen=True)
class Orfano:
    """Una definizione senza richiami fuori casa, gia' classificata."""

    modulo: str
    classe: str | None
    nome: str
    riga: int
    tipo: str
    categoria: str
    ragione: str
    benigno: bool

    @property
    def chiave(self) -> tuple[str, str | None, str]:
        """Cio' che identifica l'orfano fra due esecuzioni.

        La riga NON entra: cambia ogni volta che qualcuno aggiunge un commento
        sopra, e una baseline che diventa rossa per un commento e' una baseline
        che qualcuno rigenera senza guardarla.
        """
        return (self.modulo, self.classe, self.nome)


@dataclass
class Rapporto:
    """L'esito di una scansione."""

    definizioni: int = 0
    orfani: list[Orfano] = field(default_factory=list)

    @property
    def sospetti(self) -> list[Orfano]:
        """Gli orfani che nessuna categoria benigna spiega."""
        return [o for o in self.orfani if not o.benigno]

    def per_categoria(self) -> dict[str, list[Orfano]]:
        fuori: dict[str, list[Orfano]] = {}
        for o in self.orfani:
            fuori.setdefault(o.categoria, []).append(o)
        return fuori


# ── lettura ──────────────────────────────────────────────────────────────────


def _sorgenti(radice: Path, sotto: str) -> list[Path]:
    base = radice / sotto
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def _alberi(percorsi: Iterable[Path]) -> dict[Path, ast.Module]:
    """Legge e analizza una volta sola: l'albero serve due volte."""
    alberi: dict[Path, ast.Module] = {}
    for p in percorsi:
        try:
            alberi[p] = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as exc:                       # pragma: no cover
            raise SyntaxError(f"{p}: {exc}") from exc
    return alberi


def _figli_raggiungibili(nodo: ast.AST) -> Iterator[ast.stmt]:
    """I figli in cui una definizione e' ancora visibile da fuori.

    Scende in `if`/`try`/`with` di livello modulo — un `def` dentro
    `if TYPE_CHECKING:` esiste eccome — e si ferma davanti al corpo di una
    funzione.
    """
    for figlio in ast.iter_child_nodes(nodo):
        if isinstance(figlio, _DEFINIZIONI):
            yield figlio
        elif isinstance(figlio, CONTENITORI):
            yield from _figli_raggiungibili(figlio)


def definizioni(alberi: dict[Path, ast.Module], radice: Path) -> list[Definizione]:
    """Ogni `def`/`class` pubblica, di modulo o di classe.

    I doppioni si tengono una volta sola: `@property` piu' `@x.setter` sono
    due `def` con lo stesso nome, e sono una cosa sola da chiamare.
    """
    viste: set[tuple[str, str | None, str]] = set()
    trovate: list[Definizione] = []
    for percorso, albero in alberi.items():
        modulo = percorso.relative_to(radice).as_posix()
        for nodo in _figli_raggiungibili(albero):
            _raccogli(nodo, modulo, None, viste, trovate)
    return sorted(trovate, key=lambda d: (d.modulo, d.classe or "", d.nome))


def _raccogli(
    nodo: ast.stmt,
    modulo: str,
    proprietario: str | None,
    viste: set[tuple[str, str | None, str]],
    fuori: list[Definizione],
) -> None:
    if not isinstance(nodo, _DEFINIZIONI):
        return
    if not nodo.name.startswith("_"):
        chiave = (modulo, proprietario, nodo.name)
        if chiave not in viste:
            viste.add(chiave)
            fuori.append(Definizione(
                modulo=modulo,
                classe=proprietario,
                nome=nodo.name,
                riga=nodo.lineno,
                tipo=("classe" if isinstance(nodo, ast.ClassDef)
                      else "metodo" if proprietario else "funzione"),
            ))
    if isinstance(nodo, ast.ClassDef):
        # Una classe annidata cambia proprietario; il corpo di un metodo no.
        for figlio in _figli_raggiungibili(nodo):
            _raccogli(figlio, modulo, nodo.name, viste, fuori)


def riferimenti(albero: ast.Module) -> dict[str, list[int]]:
    """I nomi che questo file USA, con le righe.

    `Name` copre `pianifica(...)` e `class X(Base)`; `Attribute` copre
    `R.pianifica(...)` e `self.metodo()`. Gli `import` non entrano: importare
    non e' chiamare, e un `__init__.py` che ri-esporta e basta non deve poter
    coprire un orfano.
    """
    # ⚠️ **Gli alias si RISOLVONO, e non e' un'eccezione alla regola sopra.**
    #
    # `from core.a import usata as u` seguito da `u()` produce un `Name` che
    # si chiama `u`: il richiamo esiste, e per lo scanner `usata` restava
    # «nessun riferimento, in nessun posto». Riprodotto su un albero
    # costruito apposta il 27 agosto.
    #
    # Il costo non era teorico: `core/engine.py` importa `core.log` come
    # MODULO invece che con `from ... import configura as configura_log`
    # proprio per aggirare questo buco, con cinque righe di commento a
    # spiegarlo. Un aggiramento scritto nel codice applicativo per un limite
    # dello strumento di misura e' il limite che va tolto.
    #
    # L'import in se' continua a non contare — importare non e' chiamare — e
    # un `__init__.py` che ri-esporta e basta non copre nulla: qui si registra
    # soltanto **che nome locale corrisponde a quale nome originale**.
    alias: dict[str, str] = {}
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.ImportFrom | ast.Import):
            for a in nodo.names:
                if a.asname:
                    alias[a.asname] = a.name.split(".")[-1]

    usi: dict[str, list[int]] = {}
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Name):
            nome = nodo.id
        elif isinstance(nodo, ast.Attribute):
            nome = nodo.attr
        else:
            continue
        usi.setdefault(nome, []).append(nodo.lineno)
        # Un uso dell'alias e' un uso dell'originale. Si registrano ENTRAMBI:
        # il nome locale puo' a sua volta coincidere con una definizione vera.
        vero = alias.get(nome)
        if vero and vero != nome:
            usi.setdefault(vero, []).append(nodo.lineno)
    return usi


# ── classificazione ──────────────────────────────────────────────────────────


def _basi(nodo: ast.ClassDef) -> list[str]:
    return [ast.unparse(b).split("[")[0].split(".")[-1] for b in nodo.bases]


@dataclass
class _Indice:
    """Cio' che serve per classificare, raccolto una volta sola."""

    protocolli: set[tuple[str, str]] = field(default_factory=set)
    membri_protocollo: set[str] = field(default_factory=set)
    eccezioni: set[str] = field(default_factory=set)
    basi_esterne: dict[tuple[str, str], list[str]] = field(default_factory=dict)


def _indicizza(alberi: dict[Path, ast.Module], radice: Path) -> _Indice:
    idx = _Indice()
    classi: dict[str, list[str]] = {}
    nodi: list[tuple[str, ast.ClassDef]] = []
    for percorso, albero in alberi.items():
        modulo = percorso.relative_to(radice).as_posix()
        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.ClassDef):
                classi[nodo.name] = _basi(nodo)
                nodi.append((modulo, nodo))

    def eccezione(nome: str, visti: frozenset[str] = frozenset()) -> bool:
        """Risale la catena: `class X(UnknownTool)` e' un'eccezione anche se
        `UnknownTool` e' di casa nostra. Il `visti` ferma i cicli, che in un
        file valido non ci sono ma in uno a meta' scrittura si'."""
        if nome in BASI_ECCEZIONE:
            return True
        if nome in visti or nome not in classi:
            return False
        return any(eccezione(b, visti | {nome}) for b in classi[nome])

    for modulo, nodo in nodi:
        basi = _basi(nodo)
        if any(b in BASI_PROTOCOLLO for b in basi):
            idx.protocolli.add((modulo, nodo.name))
            for membro in _figli_raggiungibili(nodo):
                if isinstance(membro, _DEFINIZIONI):
                    idx.membri_protocollo.add(membro.name)
        if any(eccezione(b) for b in basi):
            idx.eccezioni.add(nodo.name)
        esterne = [b for b in basi
                   if b not in classi and b not in BASI_PROTOCOLLO and b != "object"]
        if esterne:
            idx.basi_esterne[(modulo, nodo.name)] = esterne
    return idx


def _classifica(
    d: Definizione,
    idx: _Indice,
    in_casa: list[int],
    fuori_python: list[str],
) -> tuple[str, str]:
    """Categoria e ragione, nell'ordine in cui vanno provate.

    Il «benigno» non si restituisce: lo dice `CATEGORIE`, in un posto solo.

    L'ordine conta: `usato_solo_nel_modulo` viene per primo perche' un
    chiamante vero, anche se in casa, e' la spiegazione piu' forte che esista.
    """
    if in_casa:
        righe = ", ".join(str(r) for r in in_casa[:5])
        coda = " e altri" if len(in_casa) > 5 else ""
        return (
            "usato_solo_nel_modulo",
            f"{len(in_casa)} richiami dentro {d.modulo} (righe {righe}{coda})",
        )

    if d.classe is None and (d.modulo, d.nome) in idx.protocolli:
        return ("protocollo",
                "classe Protocol/ABC: la si implementa per struttura, "
                "nessuno ne scrive il nome")
    if d.classe is not None and (d.modulo, d.classe) in idx.protocolli:
        return ("protocollo",
                f"membro del protocollo {d.classe}: e' una firma, non un corpo")

    if d.classe is not None and d.nome in CALLBACK_LIBRERIA:
        esterne = idx.basi_esterne.get((d.modulo, d.classe), [])
        if esterne:
            return ("callback_libreria",
                    f"{CALLBACK_LIBRERIA[d.nome]} lo chiama: "
                    f"{d.classe} eredita da {', '.join(esterne)}")

    if d.tipo == "classe" and d.nome in idx.eccezioni:
        return ("eccezione",
                "eccezione dichiarata: si solleva e si cattura, "
                "il nome puo' non comparire mai")

    if d.classe is not None and d.nome in idx.membri_protocollo:
        return ("implementazione_di_protocollo",
                f"{d.nome} e' dichiarato da un protocollo di core/: "
                "lo chiama chi tiene il protocollo")

    if fuori_python:
        dove = ", ".join(fuori_python[:3])
        coda = f" e altri {len(fuori_python) - 3}" if len(fuori_python) > 3 else ""
        return ("solo_test",
                f"richiamato SOLO da {dove}{coda}: provato, mai congiunto")

    return ("da_esaminare", "nessun riferimento, in nessun posto")


# ── scansione ────────────────────────────────────────────────────────────────


def scansiona(radice: Path = RADICE) -> Rapporto:
    """La misura intera. Legge il disco una volta e non tocca niente."""
    percorsi = _sorgenti(radice, SORGENTE)
    alberi = _alberi(percorsi)
    idx = _indicizza(alberi, radice)
    usi_core = {p.relative_to(radice).as_posix(): riferimenti(a)
                for p, a in alberi.items()}

    usi_esclusi: dict[str, dict[str, list[int]]] = {}
    for sotto in ESCLUSE:
        for p, a in _alberi(_sorgenti(radice, sotto)).items():
            usi_esclusi[p.relative_to(radice).as_posix()] = riferimenti(a)

    rapporto = Rapporto(definizioni=0)
    trovate = definizioni(alberi, radice)
    rapporto.definizioni = len(trovate)

    for d in trovate:
        if any(d.nome in usi for modulo, usi in usi_core.items() if modulo != d.modulo):
            continue
        in_casa = [r for r in usi_core[d.modulo].get(d.nome, []) if r != d.riga]
        fuori_python = sorted(m for m, usi in usi_esclusi.items() if d.nome in usi)
        categoria, ragione = _classifica(d, idx, in_casa, fuori_python)
        rapporto.orfani.append(Orfano(
            modulo=d.modulo, classe=d.classe, nome=d.nome, riga=d.riga,
            tipo=d.tipo, categoria=categoria, ragione=ragione,
            benigno=CATEGORIE[categoria],       # allowlist: un refuso alza KeyError
        ))
    return rapporto


def come_json(r: Rapporto) -> dict[str, Any]:
    """La forma che finisce in `docs/acceptance/ORFANI.json`."""
    return {
        "definizioni": r.definizioni,
        "orfani_totali": len(r.orfani),
        "sospetti": len(r.sospetti),
        "elenco": [asdict(o) for o in sorted(
            r.orfani, key=lambda o: (o.benigno, o.modulo, o.classe or "", o.nome))],
    }


# ── stampa ───────────────────────────────────────────────────────────────────


def _nome_pieno(o: Orfano) -> str:
    return f"{o.classe}.{o.nome}" if o.classe else o.nome


def _riepilogo(r: Rapporto, tutti: bool) -> str:
    righe: list[str] = [
        f"{r.definizioni} definizioni pubbliche in {SORGENTE}/",
        f"{len(r.orfani)} senza richiami fuori dal proprio modulo "
        f"(esclusi {'/, '.join(ESCLUSE)}/)",
        "",
    ]
    per_cat = r.per_categoria()
    ordine = sorted(per_cat, key=lambda c: (per_cat[c][0].benigno, c))
    for categoria in ordine:
        gruppo = per_cat[categoria]
        segno = "·" if gruppo[0].benigno else "!"
        righe.append(f" {segno} {categoria:32} {len(gruppo):4}")
    righe.append("")

    sospetti = r.sospetti
    if not sospetti:
        righe.append("Nessun orfano sospetto: ogni orfano ha una categoria benigna.")
    else:
        righe.append(f"I {len(sospetti)} sospetti, uno per riga:")
        for o in sorted(sospetti, key=lambda o: (o.categoria, o.modulo, o.nome)):
            righe.append(f"   {o.modulo}:{o.riga}  {_nome_pieno(o)}")
            righe.append(f"      {o.categoria} — {o.ragione}")

    if tutti:
        righe.append("")
        righe.append("Gli orfani benigni:")
        for o in sorted(r.orfani, key=lambda o: (o.categoria, o.modulo, o.nome)):
            if o.benigno:
                righe.append(f"   {o.modulo}:{o.riga}  {_nome_pieno(o)}"
                             f"  [{o.categoria}]")
    return "\n".join(righe)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true",
                    help="l'elenco completo, la forma della baseline")
    ap.add_argument("--tutti", action="store_true",
                    help="nel riepilogo elenca anche gli orfani benigni")
    ap.add_argument("--radice", type=Path, default=RADICE,
                    help="la radice del progetto da scandire")
    a = ap.parse_args(argv)

    r = scansiona(a.radice)
    if a.json:
        print(json.dumps(come_json(r), indent=2, ensure_ascii=False))
    else:
        print(_riepilogo(r, a.tutti))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
