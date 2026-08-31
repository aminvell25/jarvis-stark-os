"""Allowlist tipizzata — SPEC §21.2, invariante 2.

**Solo i tool registrati esistono.** Non c'e' un elenco di cose vietate: c'e'
un elenco di cose che ci sono. I comandi utili sono finiti e si enumerano,
quelli dannosi sono infiniti e componibili, quindi una denylist e' una lista
di sconfitte gia' subite.

Quattro vincoli sono imposti QUI e non lasciati alla disciplina:

* invariante 27 — un tool `side_effect=True` non puo' essere `gesture_allowed`
* nome unico — registrare due volte lo stesso nome e' un errore, non una
  sostituzione: sovrascrivere in silenzio e' il modo in cui si perde un tool
  senza che nessuno se ne accorga
* **invariante 3** — un tool `side_effect=True` non si esegue senza conferma
  umana. Non e' il tool a doversela ricordare: e' `invoke()` a non poterla
  saltare. Un tool distruttivo senza `planner` non si registra nemmeno.
* **fail-closed** — se nessun meccanismo di conferma e' collegato, i tool
  distruttivi NON funzionano. Dimenticare di cablarlo rende il sistema inutile,
  non pericoloso: e' il verso giusto in cui sbagliare.
"""

from __future__ import annotations

import inspect
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from core.tools.confirm import Piano
from core.traccia import Traccia
from core.verifica import Verifica

log = structlog.get_logger(__name__)


class ToolResult(BaseModel):
    """L'esito di un tool. **Mai un'eccezione verso il chiamante.**"""

    ok: bool
    output: Any = None
    error: str | None = None

    #: ADR-011 — CHI ha chiesto questa esecuzione. Additivo e timbrato da
    #: `invoke()`, non dagli handler: la traccia appartiene a chi chiama, non
    #: al tool, e un tool che potesse scriversela addosso potrebbe anche
    #: sbagliarla. Nessuno dei quaranta handler cambia di una riga.
    traccia_id: str | None = None

    #: ADR-012 — che cosa si SA dell'azione, oltre a `ok`.
    #:
    #: ⚠️ **`ok` e `verifica` sono due assi diversi, e vanno letti insieme.**
    #: `ok=True` dice «la chiamata non ha sollevato»; `verifica.verdetto` dice
    #: se qualcuno e' andato a guardare, e che cosa ha visto. Un
    #: `ok=True` + `NON_VERIFICATO` e' il caso normale di un tool senza
    #: verificatore, ed e' onesto. Un `ok=True` + `FALLITO` e' il caso per cui
    #: ADR-012 esiste.
    verifica: Verifica | None = None


class Tool(BaseModel):
    name: str
    description: str
    args_schema: type[BaseModel]
    side_effect: bool
    gesture_allowed: bool = False

    #: Costruisce il PIANO risolto da sottoporre all'utente. Obbligatorio per i
    #: tool con `side_effect`, vietato per gli altri. Il piano contiene percorsi
    #: gia' risolti, ed e' cio' che verra' eseguito — non gli argomenti (§6.2).
    planner: Callable[[Any], Awaitable["Piano"]] | None = None

    #: Riceve `(args)` se in sola lettura, `(args, piano)` se distruttivo.
    handler: Callable[..., Awaitable[ToolResult]]

    #: ADR-012. `(args, piano, risultato) -> Verifica`, sincrono o asincrono.
    #: `None` significa **`NON_VERIFICATO`**, non «riuscito»: e' la regola che
    #: rende l'ADR non decorativo.
    #:
    #: ⚠️ **Riceve il PIANO, e ADR-012 diceva solo `(args, ToolResult)`.** La
    #: correzione non e' stilistica: tutti e tre i tool che l'ADR nomina sono
    #: `side_effect=True`, e i loro percorsi RISOLTI vivono nel piano
    #: congelato, non negli argomenti. Un verificatore che risolvesse di nuovo
    #: `a.path` rifarebbe esattamente cio' che §6.2 esiste per impedire — fra
    #: la conferma e l'esecuzione un symlink puo' essere cambiato — e
    #: verificherebbe un percorso diverso da quello toccato, con l'aria di
    #: aver verificato.
    verifica: Callable[..., Any] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UnknownTool(LookupError):
    """Nome non presente nell'allowlist."""


class ConfermaNonCollegata(RuntimeError):
    """Un tool distruttivo e' stato invocato senza un meccanismo di conferma."""


class DuplicateTool(ValueError):
    """Nome gia' registrato."""


_REGISTRY: dict[str, Tool] = {}

#: Chi pone la domanda all'utente. Lo collega la radice di composizione.
#: `None` significa che nessun tool distruttivo puo' girare (fail-closed).
_CONFERMA: Callable[["Piano"], Awaitable[str]] | None = None
#: Chi riferisce com'e' andata un'operazione confermata — §6.2, `fs.result`.
#: Vedi `set_result_hook`: la promessa c'era da sempre e non la teneva nessuno.
_ESITO: Callable[["Piano", "ToolResult"], Awaitable[None]] | None = None

#: I verdetti che ogni tool ha DAVVERO prodotto in questo processo, per nome e
#: per valore — ADR-012, criterio 4.
#:
#: ⚠️ **Esiste perche' «ha un verificatore» non e' «verifica».** Fino al 31
#: agosto 2026 `jarvis doctor` contava `t.verifica is not None`, cioe' i
#: verificatori **dichiarati**: tre `lambda: Verifica.non_verificata("todo")`
#: avrebbero portato il check da `warn` a `ok` con zero coperti a runtime.
#: L'unica misura che sorveglia l'onesta' di questo ADR era l'unica
#: falsificabile in tre righe. Adesso si contano i verdetti, e uno stub si
#: scopre al primo uso reale — che e' quando la bugia comincia a contare.
_VERDETTI: dict[str, Counter[str]] = defaultdict(Counter)


def set_confirm_hook(hook: Callable[["Piano"], Awaitable[str]] | None) -> None:
    """Collega il meccanismo di conferma. Solo la radice di composizione."""
    global _CONFERMA
    _CONFERMA = hook


def set_result_hook(hook: Callable[["Piano", "ToolResult"], Awaitable[None]]
                    | None) -> None:
    """Collega chi riferisce **com'e' andata**. Solo la radice di composizione.

    ⚠️ **§6.2 lo prometteva da sempre e non lo faceva nessuno.** Il diagramma in
    cima a `core/tools/confirm.py` e in `docs/SPEC.md` dice

        conferma -> esegue -> fs.result

    e in tutto il repository quella stringa comparivano **solo in quelle due
    righe di prosa**. Il Signore approvava di spostare duecento file e non
    sapeva piu' niente: la finestra si chiudeva al clic, e cio' che accadeva
    dopo non tornava indietro.

    Arriva per funzione e non per oggetto, come il gancio della conferma: il
    registro non deve sapere che cosa sia un socket ne' un diario.
    """
    global _ESITO
    _ESITO = hook


def register(tool: Tool) -> None:
    if tool.side_effect and not tool.planner:
        raise ValueError(
            f"{tool.name}: un tool con side_effect deve avere un `planner` che "
            f"costruisca il piano risolto da mostrare all'utente (invariante 3, "
            f"§6.2). Senza, non ci sarebbe nulla da confermare."
        )
    if not tool.side_effect and tool.planner:
        raise ValueError(
            f"{tool.name}: un tool senza side_effect non ha nulla da far "
            f"confermare, e un `planner` qui confonderebbe chi legge."
        )
    if tool.side_effect and tool.gesture_allowed:
        raise ValueError(
            f"{tool.name}: un tool con side_effect non puo' essere "
            f"gesture_allowed (invariante 27). Il vincolo e' imposto nel "
            f"registry proprio per non dipendere dalla disciplina."
        )
    if tool.name in _REGISTRY:
        raise DuplicateTool(
            f"{tool.name} e' gia' registrato. Registrare due volte lo stesso "
            f"nome non sostituisce: e' un errore."
        )
    _REGISTRY[tool.name] = tool
    log.debug("tool_registrato", nome=tool.name, side_effect=tool.side_effect)


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def names() -> list[str]:
    return sorted(_REGISTRY)


def describe_all() -> list[dict[str, Any]]:
    """Descrizione dei tool per `state.snapshot`. **Mai gli handler.**"""
    return [
        {
            "name": t.name,
            "description": t.description,
            "side_effect": t.side_effect,
            "gesture_allowed": t.gesture_allowed,
            # ADR-012, criterio 4: `jarvis doctor` conta quanti tool sanno
            # dire com'e' andata. Viaggia nello snapshot perche' il registro
            # vive nel processo del core e il dottore e' un altro processo.
            "verificabile": t.verifica is not None,
            # ⚠️ **E quanti verdetti ha DAVVERO prodotto**, perche' la riga
            # sopra dice solo che un verificatore e' dichiarato. Vedi
            # `_VERDETTI`: un `lambda: non_verificata("todo")` soddisfa
            # `verificabile` e non verifica niente.
            "verdetti": dict(_VERDETTI.get(t.name, {})),
        }
        for t in sorted(_REGISTRY.values(), key=lambda t: t.name)
    ]


class GestureVietata(Exception):
    """Una gesture ha provato a invocare un tool che non le e' concesso."""


async def invoke_da_gesture(name: str, args: dict[str, Any] | None = None, *,
                            traccia: Traccia | None = None) -> ToolResult:
    """L'UNICA via dalle gesture ai tool — invariante 27, seconda meta'.

    La prima meta' e' in `register()`: un tool `side_effect=True` non puo'
    dichiararsi `gesture_allowed`. Ma quella e' una regola su come si
    REGISTRA, e non impediva a un percorso gesture di chiamare `invoke()` su
    `trash_path` — che e' `side_effect=True` e `gesture_allowed=False`.

    Il registry sapeva gia' la risposta e nessuno gliela chiedeva. Adesso
    gliela chiede questa funzione, e `core/gestures/mapping.py` non ha altra
    strada verso i tool.

    ⚠️ **Solleva, non restituisce `ok=False`.** E' deliberato e diverso dal
    resto del modulo: un argomento invalido e' un esito che il chiamante deve
    poter leggere, ma una gesture che punta a un tool vietato e' un errore di
    CABLAGGIO — qualcuno ha scritto una mappatura che non doveva esistere — e
    un `ok=False` finirebbe in un ramo di gestione degli errori invece che
    sotto gli occhi di chi l'ha scritta.

    §14 lo dice in una riga: «Un falso positivo e' indistinguibile da un
    comando». E' per questo che il vincolo sta qui e non nella disciplina di
    chi scrive la tabella dei gesti.
    """
    tool = _REGISTRY.get(name)
    if tool is None:
        raise UnknownTool(
            f"{name!r} non e' nell'allowlist. Registrati: {', '.join(names()) or '(nessuno)'}"
        )
    if not tool.gesture_allowed:
        log.error("gesture_vietata", nome=name, side_effect=tool.side_effect)
        raise GestureVietata(
            f"il tool {name!r} non e' gesture_allowed (invariante 27). "
            f"side_effect={tool.side_effect}. Una gesture non puo' invocarlo: "
            "un falso positivo sarebbe indistinguibile da un comando."
        )
    return await invoke(name, args, traccia=traccia)


def _timbra(r: ToolResult, traccia: Traccia | None) -> ToolResult:
    """Attacca la traccia all'esito. **Idempotente**, e a valle di ogni ramo.

    ⚠️ **Anche sui rami `ok=False`**, e sono quelli che contano di piu': un
    argomento invalido, una conferma non collegata, un piano fallito, un
    rifiuto dell'utente. Sono le righe che spiegano perche' NON e' successo
    niente, e `esegui_t0` lo dice gia' del diario — «un intento rifiutato e' la
    riga piu' utile che ci sia». Timbrare solo il successo lascerebbe senza
    origine proprio la meta' che si va a cercare quando qualcosa va storto.
    """
    return r if traccia is None else r.model_copy(update={"traccia_id": traccia.id})


async def _verifica(tool: Tool, args: BaseModel, piano: "Piano | None",
                    r: ToolResult, traccia: Traccia | None) -> ToolResult:
    """Chiede al verificatore com'e' andata, e allega il verdetto.

    ⚠️ **Un tool senza verificatore torna `NON_VERIFICATO`, non `RIUSCITO`.** E'
    la regola che rende ADR-012 non decorativo: senza di essa «non lo so»
    collassa su «si'», e il registro comincia a raccontare.

    ⚠️ **Un verificatore che nomina il proprio tool viene DECLASSATO.**
    Rileggere attraverso lo stesso codice non prova che l'azione sia riuscita:
    prova che il codice e' coerente con se' stesso. ADR-012 lo affidava alla
    revisione umana — «viene rifiutato in revisione» — e una regola affidata
    alla disciplina e' una regola che regge finche' qualcuno ha fretta. Qui
    e' il registro a non poterla saltare, come per la conferma.

    Non solleva: cio' che e' stato fatto **e' gia' successo**, e un verificatore
    rotto non deve poterlo trasformare in un errore. Un guasto qui vale
    `NON_VERIFICATO` con la sua ragione, che e' esattamente cio' che si sa.

    ⚠️ **«Non solleva» vale per il RITORNO, non solo per l'eccezione.** Fino al
    31 agosto 2026 il controllo sull'autocertificazione stava **fuori** dal
    `try`, e un verificatore che *restituisse* un non-`Verifica` — `None` e' il
    caso ovvio, e `core/tools/files.py` tipizza gia' `_non_eseguito(...) ->
    Verifica | None` dentro questo stesso ADR — alzava `AttributeError` su
    `esito.fonte`. Quell'eccezione usciva da `invoke()` **dopo** la scrittura
    distruttiva e **prima** di `_riferisci`:

        _esegui -> _verifica ✗ -> ( _riferisci mai chiamato )
        azione avvenuta · nessun fs.result · nessuna riga di diario

    Cioe' il guasto peggiore che questo modulo possa produrre, per la sola
    ragione che due righe stavano dopo il `except` invece che dentro il `try`.
    Non era raggiungibile con i tre verificatori di oggi; il tipo non lo
    impediva, e una promessa mantenuta per fortuna non e' mantenuta.
    """
    if tool.verifica is None:
        return r.model_copy(update={"verifica": Verifica.non_verificata(
            f"{tool.name} non ha un verificatore dichiarato",
            traccia_id=traccia.id if traccia else None)})
    try:
        esito = tool.verifica(args, piano, r)
        if inspect.isawaitable(esito):
            esito = await esito
        # Un `None` qui non e' un verdetto: e' un verificatore che ha
        # dimenticato di darne uno. Si solleva **dentro** il try, cosi' finisce
        # nel ramo che lo trasforma in `NON_VERIFICATO` con la sua ragione.
        if not isinstance(esito, Verifica):
            raise TypeError(
                f"ha restituito {type(esito).__name__}, non una Verifica")
        if tool.name in esito.fonte:
            log.error("verificatore_si_autocertifica", nome=tool.name,
                      fonte=esito.fonte,
                      conseguenza="declassato a non_verificato: rileggere "
                                  "attraverso lo stesso codice non e' una verifica")
            esito = Verifica.non_verificata(
                f"il verificatore di {tool.name} dichiara come fonte se' stesso "
                f"({esito.fonte!r}): il verdetto non e' attendibile",
                fonte="registry.invoke")
    except Exception as exc:
        log.error("verificatore_caduto", nome=tool.name, errore=repr(exc),
                  exc_info=True,
                  conseguenza="l'azione e' avvenuta e non si sa com'e' andata")
        esito = Verifica.non_verificata(
            f"il verificatore e' caduto: {type(exc).__name__}: {exc}")
    # Il conto sta QUI perche' qui passa ogni verdetto prodotto da un
    # verificatore, compresi i declassamenti e le cadute: contarlo altrove
    # vorrebbe dire un secondo posto che puo' divergere. Vedi `_VERDETTI`.
    _VERDETTI[tool.name][str(esito.verdetto)] += 1
    return r.model_copy(update={"verifica": esito.con_traccia(
        traccia.id if traccia else None)})


def _bloccata(r: ToolResult, perche: str, traccia: Traccia | None) -> ToolResult:
    """L'azione non e' partita, e **il registro l'ha visto**.

    E' l'unico verdetto che non ha bisogno di un verificatore per essere vero:
    la domanda di conferma l'ha posta il registro, e il no l'ha ricevuto lui.

    ⚠️ **Timbra anche la traccia (ADR-011), e non solo il verdetto.** `invoke()`
    timbra al ritorno, cioe' DOPO il gancio dell'esito: sul ramo rifiutato la
    riga di diario nasceva con `traccia=None` e non si ricongiungeva a niente.
    E' lo stesso difetto che il ramo approvato aveva, chiuso il 30 agosto con la
    stessa cura — si timbra prima di riferire. Il secondo timbro in `invoke()`
    e' innocuo: `_timbra` e' idempotente.
    """
    return _timbra(r, traccia).model_copy(update={"verifica": Verifica.bloccata(
        perche, traccia_id=traccia.id if traccia else None)})


async def invoke(name: str, args: dict[str, Any] | None = None, *,
                 traccia: Traccia | None = None) -> ToolResult:
    """Esegue un tool dell'allowlist.

    **Solleva `UnknownTool` se il nome non e' registrato**, e questa e' l'unica
    eccezione che esce di qui. La distinzione e' voluta:

    * un nome sconosciuto e' un errore di INSTRADAMENTO — l'allowlist e' il
      contratto, e chiedere qualcosa che non c'e' significa che il chiamante e'
      rotto o ostile. Va rumoroso.
    * argomenti invalidi o un handler che fallisce sono ESITI: il chiamante
      deve poterli leggere e reagire, quindi tornano come `ToolResult(ok=False)`.

    ⚠️ Il `CLAUDE.md` impone che nessuna eccezione arrivi all'LLM. Non e' in
    contraddizione: `invoke()` e' l'API interna. La conversione di `UnknownTool`
    in `ToolResult` avviene al confine con l'LLM, cioe' nel router — **Fase 4**.
    """
    return _timbra(await _instrada(name, args, traccia), traccia)


async def _instrada(name: str, args: dict[str, Any] | None,
                    traccia: Traccia | None) -> ToolResult:
    """La decisione vera. `invoke` la avvolge per timbrarne ogni uscita."""
    tool = _REGISTRY.get(name)
    if tool is None:
        raise UnknownTool(
            f"{name!r} non e' nell'allowlist. Registrati: {', '.join(names()) or '(nessuno)'}"
        )

    try:
        parsed = tool.args_schema.model_validate(args or {})
    except ValidationError as exc:
        # Il tool non e' partito, e il registro lo sa con certezza: e' `bloccato`,
        # non «non si sa». La distinzione conta — `NON_VERIFICATO` vuol dire
        # «potrebbe essere successo e non l'ho guardato», e qui non e' successo.
        return _bloccata(ToolResult(ok=False, error=f"argomenti non validi: {exc}"),
                         "argomenti non validi: il tool non e' stato chiamato",
                         traccia)

    if not tool.side_effect:
        return await _verifica(tool, parsed, None,
                               await _esegui(tool, parsed), traccia)

    # ── da qui in poi: tool distruttivo, invariante 3 ────────────────────────
    if _CONFERMA is None:
        # Fail-closed. Meglio un sistema che non fa nulla di un sistema che
        # cancella senza chiedere.
        log.error("conferma_non_collegata", nome=name)
        return _bloccata(ToolResult(
            ok=False,
            error="nessun meccanismo di conferma collegato: i tool con "
                  "side_effect non possono girare (invariante 3)",
        ), "nessun meccanismo di conferma collegato (fail-closed)", traccia)

    try:
        piano = await tool.planner(parsed)
    except Exception as exc:
        log.error("piano_fallito", nome=name, errore=str(exc), exc_info=True)
        return _bloccata(ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}"),
                         f"il piano non si e' potuto costruire: {type(exc).__name__}",
                         traccia)

    if not piano.operazioni:
        # Niente da fare non e' «riuscito»: nessuno e' andato a guardare se
        # davvero non ci fosse niente da fare.
        return await _verifica(tool, parsed, piano, ToolResult(
            ok=True, output={"eseguite": 0, "nota": "niente da fare"}), traccia)

    esito = await _CONFERMA(piano)
    if esito != "approvato":
        log.info("operazione_non_eseguita", nome=name, esito=esito)
        r = _bloccata(ToolResult(ok=False, error=f"operazione {esito}"),
                      f"operazione {esito}: l'azione non e' stata eseguita",
                      traccia)
        # ⚠️ **Anche il NO passa dal gancio, e prima non passava.**
        #
        # `_ESITO` girava solo sul ramo approvato, quindi una domanda rifiutata
        # non lasciava **nessuna riga di diario**: il log l'aveva, il registro
        # che una persona rilegge no. E `Verdetto.BLOCCATO` — che ADR-012 ha
        # introdotto per questo — non poteva arrivarci per la via della pagina.
        #
        # Trovato provando il rifiuto dal vivo il 31 agosto 2026: le due
        # operazioni approvate avevano la loro riga, quella rifiutata no.
        #
        # `esegui_t0` lo dice gia' della voce: «ogni esito, non solo quelli
        # riusciti. Il registro serve a spiegare perche' qualcosa NON e'
        # successo: un intento rifiutato e' la riga piu' utile che ci sia».
        # Adesso e' vero anche per le domande di §6.2, da qualunque origine
        # arrivino: **un piano, una risposta**.
        await _riferisci(piano, r, name)
        return r

    # Si esegue il PIANO, non gli argomenti: fra la conferma e adesso il
    # filesystem puo' essere cambiato sotto (§6.2, piano congelato).
    # ⚠️ **Si timbra PRIMA del gancio, non dopo.** `_esito_confermato` legge
    # `r.traccia_id` per scrivere la riga di diario della conferma: timbrando
    # solo al ritorno di `invoke()`, quella riga nascerebbe senza origine e la
    # conferma sarebbe l'unico anello staccato della catena. Il secondo timbro
    # in `invoke()` e' innocuo: `_timbra` e' idempotente.
    # ⚠️ **Si verifica PRIMA del gancio dell'esito**, per la stessa ragione per
    # cui si timbra prima: `_esito_confermato` scrive la riga di diario della
    # conferma, e senza il verdetto quella riga direbbe solo `ok`, cioe'
    # esattamente la cosa che ADR-012 dichiara insufficiente.
    r = _timbra(await _verifica(tool, parsed, piano,
                                await _esegui(tool, parsed, piano), traccia),
                traccia)

    # ⚠️ **La seconda meta' di §6.2**, e non la faceva nessuno. Non solleva: cio'
    # che e' stato approvato E' GIA' SUCCESSO, e un referto che cade non deve
    # poter trasformare un'operazione riuscita in un errore.
    await _riferisci(piano, r, name)
    return r


async def _riferisci(piano: "Piano", r: ToolResult, nome: str) -> None:
    """Com'e' andata la domanda. **Non solleva.**

    Cio' che e' stato approvato E' GIA' SUCCESSO, e un referto che cade non
    deve poter trasformare un'operazione riuscita in un errore. Sul ramo
    rifiutato non e' successo niente, e vale lo stesso: un registro che cade
    non e' una ragione per fingere che la domanda non sia stata posta.
    """
    if _ESITO is None:
        return
    try:
        await _ESITO(piano, r)
    except Exception as exc:
        log.error("esito_non_riferito", id=piano.id, nome=nome, errore=repr(exc),
                  conseguenza="la domanda ha avuto una risposta e nessuno lo sa")


async def _esegui(tool: Tool, args: BaseModel, piano: "Piano | None" = None) -> ToolResult:
    try:
        return await (tool.handler(args, piano) if piano else tool.handler(args))
    except Exception as exc:                      # nessuna eccezione risale
        log.error("tool_fallito", nome=tool.name, errore=str(exc), exc_info=True)
        return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")


async def pianifica(name: str, args: dict[str, Any] | None = None) -> Piano:
    """Il piano che un tool distruttivo proporrebbe, **senza eseguirlo**.

    E' la prova a vuoto: mostra all'utente esattamente cosa accadrebbe. Non e'
    una simulazione separata che potrebbe divergere — e' lo stesso `planner`
    che `invoke()` userebbe, chiamato senza la parte che esegue.
    """
    tool = _REGISTRY.get(name)
    if tool is None:
        raise UnknownTool(f"{name!r} non e' nell'allowlist")
    if not tool.planner:
        raise ValueError(f"{name} non ha effetti: non c'e' nulla da pianificare")
    return await tool.planner(tool.args_schema.model_validate(args or {}))


def clear() -> None:
    """Svuota il registro e scollega la conferma. **Solo per i test.**

    ⚠️ **Anche i verdetti**, e non e' pulizia generica: il conto e' indicizzato
    per NOME di tool, e due prove che registrano `prova` sono due tool diversi
    con lo stesso nome. Senza questa riga il conto della seconda comincia dal
    residuo della prima — che e' esattamente il modo in cui una misura
    sull'onesta' altrui diventa disonesta lei.
    """
    _REGISTRY.clear()
    _VERDETTI.clear()
    set_confirm_hook(None)
    set_result_hook(None)
