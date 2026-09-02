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
  ⚠️ «Eredita DAVVERO» vale anche per `implementazione_di_protocollo`, e li'
  non valeva: la categoria scusava per NOME NUDO, e dal 29 agosto chiede che
  la classe abbia **tutti** i membri pubblici del protocollo. Un `Protocol` e'
  strutturale — non lo si eredita — e la compatibilita' strutturale e' l'unica
  verifica possibile.
- `solo_test` — ha chiamanti, e stanno tutti in `tests/` o `scripts/`.
  **NON benigno**: e' la firma esatta della famiglia di §5.29, un pezzo
  provato e mai congiunto.
- `da_esaminare` — nessun riferimento, in nessun posto. **NON benigno.**

## La terza forma di allowlist: i DICHIARATI

Le categorie sono proprieta' del codice: si deducono guardandolo, e valgono per
chiunque le abbia. Restano fuori i casi in cui non c'e' niente da dedurre e la
risposta e' una **decisione di una persona**: `registry.pianifica` e' un'API per
le prove, e forzargli un chiamante vorrebbe dire inventare una funzione.

Percio' `DICHIARATI` non e' una categoria nuova. E' un elenco di **nomi
specifici, ciascuno firmato dalla sua ragione**, e la struttura impedisce di
aggiungerne uno senza scriverla — `Dichiarato` alza se la ragione manca o e'
un rumore («ok», «boh»). Un elenco che si potesse allungare in silenzio
diventerebbe il posto dove si nasconde l'orfano vero.

⚠️ **Un dichiarato che NON e' piu' orfano fa cadere la scansione.** Un'allowlist
che sopravvive alla sparizione del proprio motivo e' una lista di bugie in tre
mesi: se qualcuno collega `Governor.attivi`, la riga che dice «JARVIS lo sa e
non lo mostra a nessuno» e' diventata falsa e va tolta, non lasciata li'.

E il rumore conta: `gestures.emetti` era «l'unica uscita delle gesture verso il
resto del sistema» e non aveva un capo, e stava in mezzo a diciannove falsi
positivi. Ogni riga che si spiega da sola e' una riga in meno da rileggere.

«Metodi chiamati per attributo» NON e' una categoria, ed e' una scelta:
`R.pianifica(...)` e' un richiamo come un altro, e lo scanner conta gli
`Attribute` insieme ai `Name`. Quel punto cieco si chiude invece di
etichettarlo — una categoria per un caso che si puo' risolvere e' un modo
educato di non risolverlo.

## Cio' che questo scanner NON sa fare

**Gli `ast.Attribute` si contano per NOME**, e non c'e' altro modo: sapere se
`x.pianifica()` sia `registry.pianifica` vuol dire sapere il tipo di `x`, cioe'
un'inferenza di tipi, cioe' un altro strumento. Quindi `x.stato()` conta come
richiamo per OGNI `stato` definito in `core/`, di qualunque classe.

E' una scelta, e il prezzo e' dichiarato: lo scanner puo' PERDERE un orfano
quando un nome e' comune, mai inventarne uno che non c'e'. Un falso negativo
tace, un falso positivo fa perdere tempo a chi indaga: con una lista che
qualcuno deve leggere davvero, il primo costa meno.

⚠️ **E il prezzo non e' teorico: misurato il 29 agosto, 52 nomi pubblici sono
definiti da due o piu' moduli di `core/`** — 147 definizioni su 532, in 45
moduli su 71. Due volte in un giorno solo quel punto cieco ha coperto un orfano
vero: `Isteresi.gesto`, nascosta dal parametro omonimo di `alimenta()`, e
`tracker.percorso_modello`, sparita dall'elenco nell'istante in cui e' stata
scritta una `PhraseWake.percorso_modello` altrove (misurato: 170 -> 167 orfani
con una definizione in piu'). La prima l'ha chiusa l'analisi di scope qui sotto;
**la seconda no, e non la chiude niente di meno di un'inferenza di tipi.**

## Cio' che invece SA fare, da oggi: i nomi legati LOCALMENTE non contano

Un `ast.Name` che si risolve a un legame locale — un parametro, una variabile
assegnata, il bersaglio di un `for` o di un `with as`, la variabile di una
comprensione — **non e' un richiamo a una definizione di modulo**. Prima lo era:
`def alimenta(self, gesto)` faceva sembrare chiamata la property `Isteresi.gesto`
cinque volte, e la classificava benigna.

L'analisi e' **per scope** e non per file: lo stesso nome puo' essere legato in
una funzione e essere un richiamo vero in quella accanto. Tre regole che sono
costate un giro, e senza le quali lo scanner INVENTA orfani:

  1. **il corpo di una classe si esegue dall'alto in basso.** In
     `class C: default = carica()` seguito da `def carica(self)`, quel
     `carica()` e' un richiamo vero — la funzione non esiste ancora quando la
     riga gira. Legando il corpo in blocco, `carica` risultava orfana.
  2. **lo scope di classe non e' visibile dalle funzioni annidate.** In
     `class C: stato = 1` seguito da `def m(self): return stato()`, quel
     `stato` e' il nome globale.
  3. **un import NON lega.** `core/engine.py` importa dentro i metodi, e
     legando il nome importato l'uso della riga seguente smetteva di contare:
     misurato, **trentadue** classi di produzione dichiarate orfane, fra cui
     `ClaudeT1`, `VoicePipeline` e `PhraseWake`.

Default, annotazioni e decoratori si valutano nello scope di CHI DEFINISCE, non
dentro il corpo: un default che chiama una funzione del modulo e' un richiamo.

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
from typing import Any, ClassVar, Iterable, Iterator

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

@dataclass(frozen=True)
class Dichiarato:
    """Un orfano che una persona ha guardato e ha deciso di lasciare cosi'.

    ⚠️ La ragione e' un campo OBBLIGATO e validato, non una raccomandazione a
    chi scrive: un elenco che si potesse allungare con una riga muta sarebbe
    esattamente il posto dove si nasconde l'orfano vero.
    """

    modulo: str
    classe: str | None
    nome: str
    #: Perche' va bene cosi'. In italiano, e abbastanza da reggere fra tre mesi.
    perche: str

    #: Sotto questa lunghezza non e' una ragione, e' un timbro.
    MINIMO: ClassVar[int] = 30

    def __post_init__(self) -> None:
        if not self.nome or not self.modulo:
            raise ValueError("un dichiarato senza nome o senza modulo non si "
                             "puo' confrontare con niente")
        if len(self.perche.strip()) < self.MINIMO:
            raise ValueError(
                f"{self.modulo}:{self.nome} — la ragione e' lunga "
                f"{len(self.perche.strip())} caratteri, e sotto {self.MINIMO} "
                "non e' una ragione ma un timbro. Chi legge fra tre mesi deve "
                "poter decidere se e' ancora vera senza rileggere il codice."
            )

    @property
    def chiave(self) -> tuple[str, str | None, str]:
        return (self.modulo, self.classe, self.nome)


class DichiarazioneScaduta(RuntimeError):
    """Un dichiarato che non e' piu' orfano, o che non esiste piu'."""


#: I tre orfani guardati e lasciati stare. Ognuno con la firma della sua
#: ragione: un elenco di nomi nudi in tre mesi e' una lista di bugie.
DICHIARATI: tuple[Dichiarato, ...] = (
    Dichiarato(
        modulo="core/tools/registry.py", classe=None, nome="pianifica",
        perche="Raggiunto solo da tests/eval_tools.py: e' un'API per le prove, "
               "e il suo unico chiamante possibile sarebbe una funzione "
               "inventata apposta per non lasciarla sola.",
    ),
    Dichiarato(
        modulo="core/llm/governor.py", classe="Governor", nome="attivi",
        perche="Quanti spawn T2 sono in volo adesso. JARVIS lo sa e non lo "
               "mostra a nessuno: e' un numero senza un posto in cui andare, "
               "non un pezzo staccato dalla catena.",
    ),
    Dichiarato(
        modulo="core/tools/confirm.py", classe="ConfirmBroker", nome="pendenti",
        perche="Le conferme in attesa (invariante 3). JARVIS le sa e non le "
               "mostra a nessuno: la scrivania le riceve per messaggio quando "
               "nascono, non dallo snapshot, e nessuno gliele richiede. "
               "⚠️ Accanto ci sono due difetti VERI che non dipendono da lei — "
               "`fs.result` promesso e mai pubblicato, e la finestra che "
               "sopravvive alla propria scadenza — e si chiudono senza toccarla.",
    ),
    Dichiarato(
        modulo="core/voice/wake.py", classe="PhraseWake", nome="frasi_vive",
        perche="Introspezione sul riconoscitore vivo, per le prove. Il fatto che "
               "dichiara — quali frasi sono DAVVERO attive, contro quelle "
               "chieste — ha gia' il suo produttore nel solo istante in cui e' "
               "notizia: il log `wake_frasi_non_applicate`, campo `restano` "
               "(core/voice/wake.py:365). Esporlo altrove sarebbe un secondo "
               "posto da guardare per sapere la stessa cosa.",
    ),
    Dichiarato(
        modulo="core/news/gate.py", classe="Gate", nome="silenziati",
        perche="Gli argomenti chiusi con «non parlarmene piu'» (§15, regola 5). "
               "La regola e' imposta da `valuta()`; questo e' l'elenco, e "
               "nessuna scrivania lo chiede ancora.",
    ),
)


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
    #: La ragione firmata da una persona, se questo nome sta in `DICHIARATI`.
    #: NON e' una categoria: le categorie si deducono dal codice, questa e' una
    #: decisione, e va letta come tale da chi rilegge l'elenco.
    dichiarato: str | None = None

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
        """Gli orfani che nessuno ha spiegato: ne' una categoria, ne' una firma.

        ⚠️ `benigno` resta una proprieta' del CODICE e non cambia per un
        dichiarato: chi legge l'elenco deve poter vedere che `Governor.attivi`
        e' ancora `solo_test`, e che a toglierlo dai sospetti e' stata una
        persona. Confonderle vorrebbe dire perdere la differenza fra «lo
        strumento lo spiega» e «qualcuno ha deciso».
        """
        return [o for o in self.orfani
                if not o.benigno and o.dichiarato is None]

    @property
    def dichiarati(self) -> list[Orfano]:
        """Gli orfani che una persona ha guardato e lasciato stare."""
        return [o for o in self.orfani if o.dichiarato is not None]

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


@dataclass
class _Ambito:
    """Uno scope, coi nomi che ci sono LEGATI dentro."""

    genere: str                      # "funzione" | "classe" | "comprensione"
    legati: set[str] = field(default_factory=set)


def _legato(nome: str, pila: list[_Ambito]) -> bool:
    """Se `nome` si risolve a un legame locale, e non a una definizione.

    ⚠️ **Lo scope di CLASSE non e' visibile dalle funzioni annidate.** In
    `class C: stato = 1` seguito da `def m(self): return stato()`, quel
    `stato` NON e' `C.stato`: e' il nome globale, ed e' un richiamo. Saltando
    gli ambiti di classe che non siano quello immediato si evita di inventare
    un orfano — che e' l'unica cosa che questo scanner promette di non fare.
    """
    for i in range(len(pila) - 1, -1, -1):
        if pila[i].genere == "classe" and i != len(pila) - 1:
            continue
        if nome in pila[i].legati:
            return True
    return False


def _nomi_store(nodo: ast.AST) -> set[str]:
    """I nomi che un bersaglio LEGA: `a`, `a, b`, `[a, *resto]`, `a.b` (no)."""
    fuori: set[str] = set()
    for n in ast.walk(nodo):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store | ast.Del):
            fuori.add(n.id)
    return fuori


def _nomi_arg(nodo: ast.AST) -> set[str]:
    """Tutti i parametri, comprese le tre forme che si dimenticano."""
    a = getattr(nodo, "args", None)
    if not isinstance(a, ast.arguments):
        return set()
    fuori = {p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            fuori.add(extra.arg)
    return fuori


def _nomi_type_params(nodo: ast.AST) -> set[str]:
    """PEP 695: `def f[T](...)`, `class C[T]`. Vuoto sotto Python 3.11."""
    return {p.name for p in getattr(nodo, "type_params", ()) or ()}


def _fuori_dal_corpo(nodo: ast.AST) -> list[ast.AST]:
    """Cio' che si valuta nello scope di CHI DEFINISCE, non dentro."""
    fuori: list[ast.AST] = list(getattr(nodo, "decorator_list", ()) or ())
    a = getattr(nodo, "args", None)
    if isinstance(a, ast.arguments):
        fuori += [d for d in (*a.defaults, *a.kw_defaults) if d is not None]
        for p in (*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg):
            if p is not None and p.annotation is not None:
                fuori.append(p.annotation)
    if getattr(nodo, "returns", None) is not None:
        fuori.append(nodo.returns)
    return fuori


def _corpo(nodo: ast.AST) -> list[ast.AST]:
    corpo = getattr(nodo, "body", [])
    return corpo if isinstance(corpo, list) else [corpo]


def _legami(corpo: list[ast.AST]) -> tuple[set[str], set[str]]:
    """I nomi legati da un corpo, e quelli dichiarati `global`/`nonlocal`.

    Non scende nelle funzioni e nelle classi annidate: quelle hanno uno scope
    loro, e cio' che legano dentro non lega qui. Il loro NOME, invece, si'.
    """
    legati: set[str] = set()
    esterni: set[str] = set()

    def guarda(n: ast.AST) -> None:
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            legati.add(n.name)
            return                       # il corpo ha uno scope suo
        if isinstance(n, ast.Lambda):
            return
        if isinstance(n, ast.Global | ast.Nonlocal):
            esterni.update(n.names)
            return
        # ⚠️ **Un import NON lega**, e la prima stesura lo faceva: `core/engine.py`
        # importa dentro i metodi — `from core.voice.wake import PhraseWake` —
        # e legando quel nome l'uso della riga dopo smetteva di contare. Con
        # trentadue classi di produzione dichiarate orfane, fra cui `ClaudeT1`,
        # `VoicePipeline` e `PhraseWake`. Il nome importato **e'** il ponte
        # verso la definizione: legarlo taglia proprio il filo che si misura.
        if isinstance(n, ast.Import | ast.ImportFrom):
            return
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store | ast.Del):
            legati.add(n.id)
        for figlio in ast.iter_child_nodes(n):
            guarda(figlio)

    for s in corpo:
        guarda(s)
    return legati, esterni


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

    def registra(nome: str, riga: int) -> None:
        usi.setdefault(nome, []).append(riga)
        # Un uso dell'alias e' un uso dell'originale. Si registrano ENTRAMBI:
        # il nome locale puo' a sua volta coincidere con una definizione vera.
        vero = alias.get(nome)
        if vero and vero != nome:
            usi.setdefault(vero, []).append(riga)

    def cammina(nodo: ast.AST, pila: list[_Ambito]) -> None:
        if isinstance(nodo, ast.Name):
            # ⚠️ **La regola che chiude il punto cieco.** Un nome che si
            # risolve a un legame LOCALE non e' un richiamo a una definizione
            # di modulo: `def alimenta(self, gesto)` non chiama
            # `Isteresi.gesto`, ha un parametro che si chiama come lei.
            if pila and pila[-1].genere == "classe" and isinstance(
                    nodo.ctx, ast.Store | ast.Del):
                return           # `aperta: bool = False` e' un bersaglio
            if not _legato(nodo.id, pila):
                registra(nodo.id, nodo.lineno)
            return

        if isinstance(nodo, ast.Attribute):
            # ⚠️ **Gli `Attribute` restano contati per NOME**, e nient'altro
            # potrebbe: sapere se `x.pianifica()` sia `registry.pianifica`
            # vuol dire sapere il tipo di `x`. Vedi «Cio' che questo scanner
            # NON sa fare»: e' il limite che resta, ed e' dichiarato.
            registra(nodo.attr, nodo.lineno)
            cammina(nodo.value, pila)
            return

        if isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            # ⚠️ Default, annotazioni e decoratori si valutano FUORI dal corpo,
            # nello scope di chi definisce. Un default che chiama una funzione
            # del modulo e' un richiamo vero, e conta.
            for esterno in _fuori_dal_corpo(nodo):
                cammina(esterno, pila)
            legati, esterni = _legami(_corpo(nodo))
            dentro = pila + [_Ambito("funzione",
                                     (legati | _nomi_arg(nodo)
                                      | _nomi_type_params(nodo)) - esterni)]
            for figlio in _corpo(nodo):
                cammina(figlio, dentro)
            return

        if isinstance(nodo, ast.ClassDef):
            for d in nodo.decorator_list:
                cammina(d, pila)
            for b in [*nodo.bases, *nodo.keywords]:
                cammina(b, pila)
            # ⚠️ **Il corpo di una classe si esegue DALL'ALTO IN BASSO**, e
            # legarlo in blocco inventa richiami che non ci sono: in
            # `class C: default = carica()` seguito da `def carica(self)`,
            # quel `carica()` e' un richiamo vero — la funzione non esiste
            # ancora quando la riga gira. Legandolo in blocco lo scanner
            # dichiarerebbe `carica` orfana, cioe' **inventerebbe** un orfano:
            # esattamente cio' che promette di non fare.
            _, esterni = _legami(nodo.body)
            ambito = _Ambito("classe", _nomi_type_params(nodo) - esterni)
            dentro = pila + [ambito]
            for s in nodo.body:
                cammina(s, dentro)
                nuovi, _ = _legami([s])
                ambito.legati |= nuovi - esterni
            return

        if isinstance(nodo, ast.ListComp | ast.SetComp | ast.GeneratorExp
                      | ast.DictComp):
            # In Python 3 una comprensione ha uno scope suo. Il PRIMO
            # iterabile si valuta fuori: `[f(x) for x in f]` chiama `f`.
            legati: set[str] = set()
            for k, g in enumerate(nodo.generators):
                cammina(g.iter, pila if k == 0
                        else pila + [_Ambito("comprensione", set(legati))])
                legati |= _nomi_store(g.target)
            dentro = pila + [_Ambito("comprensione", legati)]
            for g in nodo.generators:
                for cond in g.ifs:
                    cammina(cond, dentro)
            for parte in ([nodo.key, nodo.value] if isinstance(nodo, ast.DictComp)
                          else [nodo.elt]):
                cammina(parte, dentro)
            return

        for figlio in ast.iter_child_nodes(nodo):
            cammina(figlio, pila)

    # Il livello di modulo NON lega: un richiamo a una funzione del proprio
    # file e' cio' che `usato_solo_nel_modulo` conta, e deve continuare a
    # contare.
    cammina(albero, [])
    return usi


# ── classificazione ──────────────────────────────────────────────────────────


def _basi(nodo: ast.ClassDef) -> list[str]:
    return [ast.unparse(b).split("[")[0].split(".")[-1] for b in nodo.bases]


@dataclass
class _Indice:
    """Cio' che serve per classificare, raccolto una volta sola."""

    protocolli: set[tuple[str, str]] = field(default_factory=set)
    #: Per ogni nome di membro, i protocolli che lo dichiarano — e i membri
    #: COMPLETI di ciascuno.
    #:
    #: ⚠️ Era un insieme di nomi nudi, e scusava per omonimia: qualunque classe
    #: con un metodo che si chiamasse come un membro di un protocollo diventava
    #: `implementazione_di_protocollo`, benigna, **con una spiegazione falsa**.
    #: Misurato il 29 agosto: `Diario.leggi` senza alcun chiamante tornava
    #: benigna perche' `leggi` e' dichiarato da `Ocr` — e `Diario` non e' un
    #: `Ocr`: non ha `disponibile`.
    membri_protocollo: dict[str, list[tuple[str, frozenset[str]]]] = field(
        default_factory=dict)
    #: I membri pubblici di ogni classe, per verificare la compatibilita'.
    membri_classe: dict[tuple[str, str], frozenset[str]] = field(
        default_factory=dict)
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
        membri = frozenset(
            m.name for m in _figli_raggiungibili(nodo)
            if isinstance(m, _DEFINIZIONI) and not m.name.startswith("_"))
        idx.membri_classe[(modulo, nodo.name)] = membri
        if any(b in BASI_PROTOCOLLO for b in basi):
            idx.protocolli.add((modulo, nodo.name))
            for nome_membro in membri:
                idx.membri_protocollo.setdefault(nome_membro, []).append(
                    (nodo.name, membri))
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

    # ⚠️ **Non basta l'omonimia: la classe deve IMPLEMENTARE il protocollo.**
    #
    # Un `Protocol` e' strutturale — chi lo implementa non lo eredita — quindi
    # l'unica verifica possibile e' quella: la classe ha TUTTI i membri
    # pubblici che il protocollo dichiara?
    #
    # Prima bastava il nome, e la categoria scusava per omonimia. Misurato:
    # `Diario.leggi` senza un solo chiamante tornava benigna, «`leggi` e'
    # dichiarato da un protocollo di core/» — vero alla lettera e falso nella
    # sostanza, perche' quel protocollo e' `Ocr` e `Diario` non ha
    # `disponibile`. Chi legge la spiegazione fra tre mesi va a cercare il
    # chiamante sbagliato.
    if d.classe is not None:
        suoi = idx.membri_classe.get((d.modulo, d.classe), frozenset())
        for nome_prot, richiesti in idx.membri_protocollo.get(d.nome, ()):
            if richiesti <= suoi:
                return ("implementazione_di_protocollo",
                        f"{d.classe} implementa {nome_prot} — ne ha tutti i "
                        f"{len(richiesti)} membri: lo chiama chi tiene il "
                        "protocollo, non chi tiene la classe")

    if fuori_python:
        dove = ", ".join(fuori_python[:3])
        coda = f" e altri {len(fuori_python) - 3}" if len(fuori_python) > 3 else ""
        return ("solo_test",
                f"richiamato SOLO da {dove}{coda}: provato, mai congiunto")

    return ("da_esaminare", "nessun riferimento, in nessun posto")


# ── scansione ────────────────────────────────────────────────────────────────


def scansiona(radice: Path = RADICE,
              dichiarati: Iterable[Dichiarato] | None = None) -> Rapporto:
    """La misura intera. Legge il disco una volta e non tocca niente.

    ⚠️ **Le firme di `DICHIARATI` parlano di QUESTO repository.** Puntare lo
    scanner altrove — `--radice`, o un albero costruito apposta per provarne le
    regole — e' un'altra misura, e portarsi dietro tre nomi che non possono
    corrispondere a niente la farebbe cadere per un motivo che non e' un
    difetto. Chi vuole provare le dichiarazioni le passa per argomento.
    """
    if dichiarati is None:
        dichiarati = DICHIARATI if radice == RADICE else ()
    percorsi = _sorgenti(radice, SORGENTE)
    alberi = _alberi(percorsi)
    idx = _indicizza(alberi, radice)
    usi_core = {p.relative_to(radice).as_posix(): riferimenti(a)
                for p, a in alberi.items()}

    usi_esclusi: dict[str, dict[str, list[int]]] = {}
    for sotto in ESCLUSE:
        for p, a in _alberi(_sorgenti(radice, sotto)).items():
            usi_esclusi[p.relative_to(radice).as_posix()] = riferimenti(a)

    firme = {d.chiave: d.perche for d in dichiarati}
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
            dichiarato=firme.get((d.modulo, d.classe, d.nome)),
        ))

    # ⚠️ Una dichiarazione che ha perso il proprio oggetto FA CADERE la
    # scansione. Un'allowlist che sopravvive alla sparizione del suo motivo
    # diventa una lista di bugie in tre mesi: se qualcuno ha collegato il nome,
    # o l'ha cancellato, la riga che lo spiega non e' piu' vera e va tolta —
    # non lasciata li' a coprire qualcosa che nessuno guarda piu'.
    scadute = sorted(set(firme) - {o.chiave for o in rapporto.orfani})
    if scadute:
        righe = "\n".join(
            f"  {m}:{(c + '.') if c else ''}{n}\n      {firme[(m, c, n)]}"
            for m, c, n in scadute)
        raise DichiarazioneScaduta(
            f"{len(scadute)} dichiarazioni in DICHIARATI non corrispondono piu' "
            f"a un orfano:\n{righe}\n\n"
            "O il nome ha trovato un chiamante — e allora e' una buona notizia, "
            "e la riga va tolta da scripts/orfani.py — o non esiste piu'. In "
            "nessuno dei due casi la ragione scritta qui sopra e' ancora vera."
        )
    return rapporto


def come_json(r: Rapporto) -> dict[str, Any]:
    """La forma che finisce in `docs/acceptance/ORFANI.json`."""
    return {
        "definizioni": r.definizioni,
        "orfani_totali": len(r.orfani),
        "sospetti": len(r.sospetti),
        "dichiarati": len(r.dichiarati),
        "elenco": [asdict(o) for o in sorted(
            r.orfani, key=lambda o: (o.benigno, o.modulo, o.classe or "", o.nome))],
    }


# ── il diario: una riga senza traccia e' un orfano (ADR-011) ─────────────────
#
# ⚠️ **E' una misura DIVERSA da quella qui sopra, e per questo e' un'altra
# modalita' e non una categoria in piu'.** `scansiona()` legge il CODICE e
# chiede «chi chiama questa definizione»; questa legge i `.jsonl` scritti dal
# core e chiede «da dove viene questa riga». Mescolarle vorrebbe dire un
# rapporto in cui due domande diverse hanno lo stesso conteggio.


@dataclass(frozen=True)
class RigaSenzaTraccia:
    """Un produttore di righe che oggi non ha un'origine, e la sua ragione.

    Stessa disciplina di `Dichiarato`: la ragione e' obbligata e validata. Un
    elenco che si potesse allungare in silenzio diventerebbe il posto in cui si
    nasconde il produttore che ha SMESSO di passare la traccia.
    """

    archivio: str          # "diario" | "initiatives"
    chiave: str            # il `da` di una riga di azione, il `tipo` di un'iniziativa
    perche: str

    MINIMO: ClassVar[int] = 30

    def __post_init__(self) -> None:
        if len(self.perche.strip()) < self.MINIMO:
            raise ValueError(
                f"{self.archivio}:{self.chiave} — la ragione e' lunga "
                f"{len(self.perche.strip())} caratteri, e sotto {self.MINIMO} "
                "non e' una ragione ma un timbro."
            )


#: I produttori che scrivono senza traccia, guardati e lasciati stare.
SENZA_TRACCIA: tuple[RigaSenzaTraccia, ...] = (
    RigaSenzaTraccia(
        archivio="diario", chiave="dialogo",
        perche="Le battute di un turno vocale portano l'id del turno. Restano "
               "senza gli ANNUNCI: `VoicePipeline.annuncia()` da' voce a una "
               "frase che il sistema dice di se' — il ripiego di §12, l'amnesia "
               "di ADR-003, il resoconto al risveglio — e non ha un turno che "
               "la causi. Un id inventato li' fingerebbe un'origine che non "
               "c'e', ed e' esattamente cio' che ADR-011 esiste per impedire.",
    ),
    RigaSenzaTraccia(
        archivio="initiatives", chiave="consolidamento",
        perche="Il consolidamento notturno (`core/memory/consolidate.py`) "
               "scrive qui e non ha ancora un'origine: dargliela vuol dire un "
               "parametro su `Consolidatore.esegui()`, che ADR-011 non nomina e "
               "la fetta 1 non anticipa. Dichiarato invece che nascosto, ed e' "
               "il passo piu' piccolo che viene dopo questa fetta.",
    ),
    RigaSenzaTraccia(
        archivio="diario", chiave="referto",
        perche="I guasti riferiti da chi non conosce il turno: la degradazione "
               "di T1 (`Supervisore.riferisci`, che T1 chiama senza una traccia "
               "perche' `claude_t1.py` non ne nomina una) e il microfono che si "
               "chiude da solo (`Engine._voce_e_finita`, un done-callback senza "
               "episodio). `Engine._annota_guasto` li scrive con `da=\"referto\"` "
               "e `traccia=None`: dichiarati, non nascosti. Dal 2 settembre 2026.",
    ),
)


@dataclass(frozen=True)
class RigaDiario:
    """Una riga letta da un archivio, gia' classificata."""

    archivio: str
    file: str
    numero: int
    chiave: str
    stato: str             # "tracciata" | "vecchia" | "dichiarata" | "orfana"
    perche: str | None = None


#: Gli stati, e quali sono benigni. Allowlist come `CATEGORIE`.
STATI: dict[str, bool] = {
    "tracciata": True,
    # ⚠️ La chiave ASSENTE, non nulla: la riga e' stata scritta prima di
    # ADR-011. Il campo e' additivo, e un lettore che non lo trova non deve
    # rompersi — e' il criterio 7 dell'ADR.
    "vecchia": True,
    "dichiarata": True,
    "orfana": False,
}


def _righe(percorso: Path) -> Iterator[tuple[int, dict]]:
    """Le righe di un `.jsonl`. Una riga malformata si salta, non fa cadere la
    scansione: stessa forma di `MemoryStore.iniziative_dal`."""
    if not percorso.exists():
        return
    testo = percorso.read_text(encoding="utf-8", errors="replace")
    for n, riga in enumerate(testo.splitlines(), 1):
        try:
            yield n, json.loads(riga)
        except json.JSONDecodeError:
            continue


def _chiave(archivio: str, d: dict) -> str:
    """Che cosa identifica il PRODUTTORE di questa riga.

    Nel diario e' `da` — il campo che nomina gia' l'origine, `voce`, `conferma`,
    `risveglio`, `gesture` — e per il flusso `dialogo`, che non ce l'ha, e' il
    flusso stesso. Nelle iniziative e' `tipo`.
    """
    if archivio == "initiatives":
        return str(d.get("tipo") or "?")
    if d.get("flusso") == "dialogo":
        return "dialogo"
    return str(d.get("da") or "?")


def scansiona_diario(diario: Path, initiatives: Path,
                     senza: Iterable[RigaSenzaTraccia] | None = None) -> list[RigaDiario]:
    """Ogni riga dei due archivi, con lo stato della sua traccia."""
    firme = {(r.archivio, r.chiave): r.perche
             for r in (SENZA_TRACCIA if senza is None else senza)}
    fuori: list[RigaDiario] = []
    for archivio, radice in (("diario", diario), ("initiatives", initiatives)):
        for percorso in sorted(radice.glob("*.jsonl")) if radice.is_dir() else []:
            for numero, d in _righe(percorso):
                chiave = _chiave(archivio, d)
                if "traccia" not in d:
                    stato, perche = "vecchia", None
                elif d["traccia"]:
                    stato, perche = "tracciata", None
                elif (archivio, chiave) in firme:
                    stato, perche = "dichiarata", firme[(archivio, chiave)]
                else:
                    stato, perche = "orfana", None
                fuori.append(RigaDiario(archivio, percorso.name, numero,
                                        chiave, stato, perche))
    return fuori


def _riepilogo_diario(righe: list[RigaDiario]) -> str:
    if not righe:
        return ("Nessuna riga nei due archivi: il core non ha ancora scritto, "
                "oppure la radice dei dati non e' questa.")
    per_stato: dict[str, int] = {}
    for r in righe:
        per_stato[r.stato] = per_stato.get(r.stato, 0) + 1
    fuori = [f"{len(righe)} righe in diario/ e initiatives/", ""]
    for stato in sorted(per_stato, key=lambda s: (STATI[s], s)):
        fuori.append(f" {'·' if STATI[stato] else '!'} {stato:24} "
                     f"{per_stato[stato]:6}")
    fuori.append("")
    orfane = [r for r in righe if not STATI[r.stato]]
    if not orfane:
        fuori.append("Nessuna riga orfana: ogni riga senza traccia e' o "
                     "d'archivio o dichiarata.")
    else:
        per_chiave: dict[tuple[str, str], int] = {}
        for r in orfane:
            per_chiave[(r.archivio, r.chiave)] = per_chiave.get(
                (r.archivio, r.chiave), 0) + 1
        fuori.append(f"{len(orfane)} righe SENZA traccia e non dichiarate, "
                     "per produttore:")
        for (archivio, chiave), quante in sorted(per_chiave.items()):
            fuori.append(f"   {archivio}/{chiave:20} {quante:6}")
        fuori.append("")
        fuori.append("O il produttore ha smesso di passare la traccia — ed e' "
                     "il difetto che ADR-011 esiste per trovare — o e' un caso "
                     "nuovo che va DICHIARATO in SENZA_TRACCIA, con la ragione.")
    return "\n".join(fuori)


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

    dichiarati = r.dichiarati
    if dichiarati:
        righe.append("")
        righe.append(f"E i {len(dichiarati)} DICHIARATI — guardati, e lasciati "
                     "stare da una persona:")
        for o in sorted(dichiarati, key=lambda o: (o.modulo, o.nome)):
            righe.append(f"   {o.modulo}:{o.riga}  {_nome_pieno(o)}  "
                         f"[{o.categoria}]")
            righe.append(f"      {o.dichiarato}")

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
    ap.add_argument("--diario", action="store_true",
                    help="le righe di diario/ e initiatives/ senza traccia "
                         "(ADR-011), invece delle definizioni senza chiamante")
    a = ap.parse_args(argv)

    if a.diario:
        # Sta qui e non in cima: `core.platform` non serve alla scansione del
        # codice, e importarlo sempre legherebbe la misura piu' usata a una
        # dipendenza che non le serve.
        sys.path.insert(0, str(RADICE))
        from core.platform import paths

        dati = paths().data_dir() / "memory_data"
        righe = scansiona_diario(dati / "diario", dati / "initiatives")
        if a.json:
            print(json.dumps([asdict(x) for x in righe], indent=2,
                             ensure_ascii=False))
        else:
            print(_riepilogo_diario(righe))
        return 0 if all(STATI[x.stato] for x in righe) else 1

    r = scansiona(a.radice)
    if a.json:
        print(json.dumps(come_json(r), indent=2, ensure_ascii=False))
    else:
        print(_riepilogo(r, a.tutti))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
