"""Tool di memoria nell'allowlist — SPEC §5.5.

⚠️ **Non e' in §21.1**: aggiunto e dichiarato. §5.5 dice che il consolidamento
«legge e scrive solo tramite i tool memoria dell'allowlist, mai direttamente»,
e quei tool non esistevano.

Le scritture hanno `side_effect=True` e passano quindi dalla conferma di §6.2,
come ogni altra. La sola eccezione e' il consolidamento notturno, che usa
`MemoryStore` direttamente per la ragione dichiarata in `consolidate.py`.
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, Field

from core.memory.store import MemoryStore
from core.tools.confirm import Operazione, Piano
from core.tools.registry import Tool, ToolResult, register


class FattoArgs(BaseModel):
    fatto: str = Field(min_length=3, max_length=500)


class RicordaArgs(BaseModel):
    query: str = Field(min_length=1)
    limite: int = Field(default=5, ge=1, le=50)


class TopicArgs(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    contenuto: str = Field(min_length=1)


class VuotoArgs(BaseModel):
    pass


def register_memory_tools(leggi_store: Callable[[], MemoryStore]) -> None:
    async def _recall(a: RicordaArgs) -> ToolResult:
        s = leggi_store()
        return ToolResult(ok=True, output={
            "fatti": s.fatti_fissati(),
            "topic": [{"nome": t.nome, "percorso": str(t.percorso),
                       "estratto": t.contenuto[:400]}
                      for t in s.cerca(a.query, a.limite)],
        })

    async def _list_topics(_a: VuotoArgs) -> ToolResult:
        s = leggi_store()
        return ToolResult(ok=True, output={"topic": s.elenca_topic(),
                                           "fatti": len(s.fatti_fissati())})

    async def _piano_pin(a: FattoArgs) -> Piano:
        s = leggi_store()
        return Piano(tool="pin_fact", riepilogo="fissa un fatto permanente",
                     operazioni=(Operazione(tipo="create",
                                            destinazione=s.topics / "_fatti-fissati.md",
                                            dettaglio=a.fatto),))

    async def _pin(a: FattoArgs, _piano: Piano) -> ToolResult:
        leggi_store().fissa(a.fatto)
        return ToolResult(ok=True, output={"fatto": a.fatto})

    async def _piano_topic(a: TopicArgs) -> Piano:
        s = leggi_store()
        return Piano(tool="write_topic", riepilogo=f"scrive la nota «{a.nome}»",
                     operazioni=(Operazione(tipo="create",
                                            destinazione=s.topics / f"{a.nome}.md",
                                            dettaglio=f"{len(a.contenuto)} caratteri"),))

    async def _write_topic(a: TopicArgs, _piano: Piano) -> ToolResult:
        p = leggi_store().scrivi_topic(a.nome, a.contenuto)
        return ToolResult(ok=True, output={"percorso": str(p)})

    register(Tool(name="recall", description="Cerca fra fatti fissati e note.",
                  args_schema=RicordaArgs, side_effect=False, handler=_recall))
    register(Tool(name="list_topics", description="Elenca le note in memoria.",
                  args_schema=VuotoArgs, side_effect=False, handler=_list_topics))
    register(Tool(name="pin_fact", description="Fissa un fatto permanente.",
                  args_schema=FattoArgs, side_effect=True,
                  planner=_piano_pin, handler=_pin))
    register(Tool(name="write_topic", description="Scrive una nota a lungo termine.",
                  args_schema=TopicArgs, side_effect=True,
                  planner=_piano_topic, handler=_write_topic))
