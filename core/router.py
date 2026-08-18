"""Router dei tre tier — SPEC §21.5, §3.3.

⚠️ **SCOSTAMENTO DA §21.5, e riguarda il cuore del router.**

§21.5 classifica con parole chiave:

    if any(k in t for k in ("apri","chiudi","pannello","cerca file", ...)):
        return {"tier": "t0"}

Ma `core/llm/grammar.py` **e' gia' il classificatore**: tredici regole ordinate,
con un corpus di cento frasi che verifica anche che non rubi frasi a T1. Due
classificatori divergerebbero al primo comando aggiunto, e quello di §21.5 non
ha corpus.

**Il router chiede a `parse()`**: se torna un `Intent`, e' T0. La sola logica
nuova e' distinguere T1 da T2, che §21.5 fa sui verbi di lavoro — quella parte
resta, perche' risponde a una domanda che il parser T0 non pone.

⚠️ **`LANGSMITH_TRACING` spento esplicitamente.** LangGraph porta con se'
`langsmith`, il client di tracciamento di LangChain. Non deve poter chiamare
casa da un sistema il cui §18.3 e' attento a cosa lascia la macchina, e
affidarsi al valore predefinito non e' una decisione: e' una speranza.
"""

from __future__ import annotations

import os
from typing import Any, Literal, TypedDict

import structlog

# Prima di importare langgraph: la variabile va letta all'import di langsmith.
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

from langgraph.graph import END, START, StateGraph  # noqa: E402

from core.llm.grammar import Intent, parse  # noqa: E402

log = structlog.get_logger(__name__)

MAX_STEPS = 6

#: Verbi che chiedono LAVORO, non conversazione (§21.5). Un compito che li usa
#: dura minuti e va a T2; tutto il resto e' T1.
VERBI_DI_LAVORO = (
    "scrivi", "scrivimi", "codice", "genera", "modello", "modella",
    "organizza", "analizza", "refattorizza", "compila", "esporta",
    "converti", "sistema", "riordina",
)


class AgentState(TypedDict, total=False):
    text: str
    tier: Literal["t0", "t1", "t2"] | None
    intent: Intent | None
    result: dict | None
    steps: int


def normalize(s: AgentState) -> dict:
    return {"text": s["text"].strip(), "steps": 0}


def classify(s: AgentState) -> dict:
    """T0 lo decide il parser a grammatica, non una lista di parole qui."""
    intent = parse(s["text"])
    if intent is not None:
        return {"tier": "t0", "intent": intent}
    basso = s["text"].lower()
    if any(v in basso for v in VERBI_DI_LAVORO):
        return {"tier": "t2", "intent": None}
    return {"tier": "t1", "intent": None}


def route(s: AgentState) -> Literal["t0", "t1", "t2"]:
    return s.get("tier") or "t1"


def build_router(esegui_t0=None, esegui_t1=None, esegui_t2=None):
    """Il grafo di §21.5. I tre esecutori arrivano per argomento: il router
    non sa cosa siano, e questo lo rende verificabile senza toccare un LLM."""

    async def t0(s: AgentState) -> dict:
        r = await esegui_t0(s["intent"]) if esegui_t0 else {"ok": True, "tier": "t0"}
        return {"result": r, "steps": s.get("steps", 0) + 1}

    async def t1(s: AgentState) -> dict:
        r = await esegui_t1(s["text"]) if esegui_t1 else {"ok": True, "tier": "t1"}
        return {"result": r, "steps": s.get("steps", 0) + 1}

    async def t2(s: AgentState) -> dict:
        r = await esegui_t2(s["text"]) if esegui_t2 else {"ok": True, "tier": "t2"}
        return {"result": r, "steps": s.get("steps", 0) + 1}

    g = StateGraph(AgentState)
    for nome, f in (("normalize", normalize), ("classify", classify),
                    ("t0", t0), ("t1", t1), ("t2", t2)):
        g.add_node(nome, f)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "classify")
    g.add_conditional_edges("classify", route, {"t0": "t0", "t1": "t1", "t2": "t2"})
    for nome in ("t0", "t1", "t2"):
        g.add_edge(nome, END)
    return g.compile()
