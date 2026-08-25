"""Il cancello di ADR-007: **i server propongono, il registry dispone.**

## Il rischio, nelle parole dell'ADR

> Montando un server MCP, i suoi tool entrerebbero nel sistema **senza passare
> dalla revisione**. L'invariante 2 dice «solo i tool registrati esistono», e
> un server che ne annuncia quaranta la aggirerebbe in un colpo.
>
> Secondo rischio, distinto: le **descrizioni** dei tool MCP sono testo di
> terzi che finisce nel contesto dell'LLM. E' una classe di attacco
> documentata.

## Le tre decisioni, e dove sono imposte

1. **Un tool MCP non e' invocabile finche' non e' stato nominato.**
   `promuovi_mcp` prende UN nome per volta. Non esiste un
   `promuovi_tutti()`, e non e' una dimenticanza: sarebbe la riga che
   riaprirebbe il buco, e chi la volesse dovrebbe scriverla e giustificarla.
2. **Le descrizioni passano da `Untrusted`.** Cio' che arriva all'LLM e' il
   testo avvolto nel marcatore di §12, e la busta non si puo' chiudere da
   dentro.
3. **Un server che cambia elenco non ne guadagna.** La promozione fotografa
   ADESSO: il nome, lo schema, la descrizione. Se al prossimo `tools/list` il
   server annuncia qualcos'altro sotto lo stesso nome, cio' che e' registrato
   qui non cambia — e quel che non e' registrato non esiste.

## Due cose che ho aggiunto, e le dichiaro

**a. Anche i RISULTATI passano da `Untrusted`.** L'ADR nomina le descrizioni.
Ma un risultato e' testo del medesimo terzo, e finisce nello stesso posto: se
la descrizione e' un vettore, il risultato lo e' esattamente quanto lei — anzi
di piu', perche' la descrizione la legge un umano quando promuove, e il
risultato no.

**b. Lo schema si deriva, e in caso di dubbio si RIFIUTA.** Un tool il cui
`inputSchema` non sappiamo rappresentare non si promuove. Fail-closed come il
registry di Fase 1: dimenticare un caso rende il sistema inerte, non
permissivo. L'alternativa — accettare qualunque dizionario — vorrebbe dire che
gli argomenti non li valida nessuno da questa parte del filo.

## E la seconda strada al filesystem

Il criterio ④ del piano chiede che un server MCP «non aggiunga una seconda
strada al filesystem». Qui e' imposta cosi':

* **un nome gia' registrato non si puo' prendere.** `registry.register`
  solleva `DuplicateTool`, quindi un server che annuncia `read_file` non
  diventa `read_file`: quel nome ha gia' un proprietario, ed e'
  `core/tools/files.py` con la sua validazione dopo `resolve()`;
* **la strada resta una**, `registry.invoke`, con la stessa conferma;
* **e il piano lo DICE.** Per un tool locale la conferma mostra un percorso
  risolto che abbiamo validato noi. Per un tool MCP quel percorso non esiste:
  l'operazione avviene dentro un processo di terzi, e noi non possiamo
  guardarci dentro. Il piano lo scrive invece di far finta, perche' una
  conferma che sembra dire piu' di quanto sa e' peggio di nessuna conferma.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, create_model

from core.llm.untrusted import Untrusted
from core.mcp.client import ErroreMcp, ServerMcp
from core.tools.confirm import Operazione, Piano
from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

#: Prefisso obbligatorio del nome locale. Non e' cosmetico: chi legge
#: `state.snapshot` o un log deve vedere **da fuori** che quel tool non e'
#: nostro, senza dover ricordare quali nomi vengano da dove.
PREFISSO = "mcp"

#: I tipi JSON Schema che sappiamo rappresentare. Tutto il resto fa rifiutare
#: la promozione — vedi il punto b dell'intestazione.
_TIPI = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}

#: Tetto agli argomenti di un tool promosso. Un `inputSchema` con duecento
#: proprieta' non e' un tool: e' un'API, e non passa da un cancello che si
#: attraversa uno per volta.
MAX_PROPRIETA = 24


class SchemaNonRappresentabile(ValueError):
    """L'`inputSchema` annunciato usa qualcosa che non sappiamo validare."""


class NonAnnunciato(LookupError):
    """Il nome chiesto non e' fra quelli che il server propone."""


def _modello_da_schema(nome: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Un modello pydantic dallo `inputSchema` annunciato.

    ⚠️ Lo schema viene dal server, cioe' da un terzo — ma qui serve a
    **restringere**, non ad autorizzare: un modello sbagliato puo' solo far
    rifiutare argomenti, mai farne passare di piu' di quanti il server ne
    dichiari. Con `extra="forbid"`, un argomento non dichiarato non entra.
    """
    if not isinstance(schema, dict):
        raise SchemaNonRappresentabile(f"{nome}: inputSchema non e' un oggetto")
    if schema.get("type") not in (None, "object"):
        raise SchemaNonRappresentabile(
            f"{nome}: inputSchema di tipo {schema.get('type')!r}, atteso un oggetto")

    proprieta = schema.get("properties") or {}
    if not isinstance(proprieta, dict):
        raise SchemaNonRappresentabile(f"{nome}: `properties` non e' un oggetto")
    if len(proprieta) > MAX_PROPRIETA:
        raise SchemaNonRappresentabile(
            f"{nome}: {len(proprieta)} proprieta', tetto {MAX_PROPRIETA}")

    richiesti = set(schema.get("required") or [])
    campi: dict[str, Any] = {}
    for chiave, descrizione in proprieta.items():
        if not isinstance(chiave, str) or not chiave.isidentifier():
            raise SchemaNonRappresentabile(f"{nome}: nome di argomento non valido")
        if not isinstance(descrizione, dict):
            raise SchemaNonRappresentabile(f"{nome}.{chiave}: non e' un oggetto")
        tipo = _TIPI.get(descrizione.get("type"))
        if tipo is None:
            # Array, oggetti annidati, `anyOf`, `$ref`: non li sappiamo
            # rappresentare e non li indoviniamo.
            raise SchemaNonRappresentabile(
                f"{nome}.{chiave}: tipo {descrizione.get('type')!r} non "
                f"rappresentabile. Rappresentabili: {sorted(_TIPI)}")
        campi[chiave] = (tipo, ... if chiave in richiesti else Field(default=None))

    return create_model(  # type: ignore[call-overload]
        f"Mcp_{nome}_Args",
        __config__=ConfigDict(extra="forbid"),
        **campi,
    )


def _testo_del_risultato(risultato: dict[str, Any]) -> str:
    """Il `content` di `tools/call`, ridotto a testo. Solo le parti testuali:
    un'immagine o una risorsa non le sappiamo mostrare, e dirlo e' meglio che
    inventarne una rappresentazione."""
    pezzi: list[str] = []
    for elemento in risultato.get("content") or []:
        if isinstance(elemento, dict) and elemento.get("type") == "text":
            pezzi.append(str(elemento.get("text", "")))
    return "\n".join(pezzi)


def promuovi_mcp(server: ServerMcp, nome_tool: str, side_effect: bool) -> Tool:
    """Nomina UN tool di UN server, e lo registra. ADR-007 azione 2.

    Solleva `NonAnnunciato` se il server non lo propone, e
    `SchemaNonRappresentabile` se non sappiamo validarne gli argomenti.
    `registry.register` solleva `DuplicateTool` se il nome locale e' preso.

    `side_effect` lo decide **chi promuove**, non il server: un terzo non ha
    titolo per dichiarare che la propria operazione e' innocua.
    """
    annuncio = server.annunciato(nome_tool)
    if annuncio is None:
        raise NonAnnunciato(
            f"{server.nome} non annuncia {nome_tool!r}. Annunciati: "
            f"{sorted(server.nomi_annunciati())}"
        )

    schema = _modello_da_schema(nome_tool, annuncio.get("inputSchema") or {})
    locale = f"{PREFISSO}_{server.nome}_{nome_tool}"

    # ADR-007 decisione 2. La descrizione e' testo di terzi: quel che finisce
    # nel contesto e' la busta, non il testo nudo.
    descrizione = Untrusted.da(f"mcp:{server.nome}",
                               str(annuncio.get("description", "")))

    async def _piano(a: BaseModel) -> Piano:
        return Piano(
            tool=locale,
            riepilogo=(f"chiede a «{server.nome}» di eseguire {nome_tool!r}"),
            operazioni=(Operazione(
                tipo="mcp",
                # ⚠️ Nessun percorso: non c'e'. L'operazione avviene dentro un
                # processo che non e' nostro, e una conferma che mostrasse un
                # percorso inventato direbbe piu' di quanto sappiamo.
                dettaglio=(
                    f"server {server.nome} · tool {nome_tool} · "
                    f"argomenti {a.model_dump(exclude_none=True)} · "
                    "l'operazione avviene dentro il server: JARVIS non puo' "
                    "verificarne l'effetto prima"
                ),
            ),),
        )

    async def _handler(a: BaseModel, *_resto) -> ToolResult:
        try:
            risultato = await server.chiama(nome_tool, a.model_dump(exclude_none=True))
        except ErroreMcp as exc:
            # *Stile codice*: nessuna eccezione propaga all'LLM.
            return ToolResult(ok=False, error=str(exc))
        testo = Untrusted.da(f"mcp:{server.nome}", _testo_del_risultato(risultato))
        return ToolResult(
            ok=not risultato.get("isError", False),
            output={"server": server.nome, "tool": nome_tool,
                    # Punto a dell'intestazione: anche il risultato e' avvolto.
                    "contenuto": testo.avvolto()},
            error="il server ha segnalato un errore" if risultato.get("isError") else None,
        )

    strumento = Tool(
        name=locale,
        # Anche qui la busta: `describe_all()` finisce nello snapshot, e da li'
        # nel contesto di chi sceglie che tool chiamare.
        description=descrizione.avvolto(),
        args_schema=schema,
        side_effect=side_effect,
        planner=_piano if side_effect else None,
        handler=_handler,
        # Invariante 27: mai una gesture verso un tool di terzi. Anche per i
        # non distruttivi, perche' una gesture non ha modo di dire QUALE
        # server sta chiamando.
        gesture_allowed=False,
    )
    register(strumento)
    log.info("mcp_promosso", server=server.nome, tool=nome_tool, locale=locale,
             side_effect=side_effect, argomenti=sorted(schema.model_fields))
    return strumento
