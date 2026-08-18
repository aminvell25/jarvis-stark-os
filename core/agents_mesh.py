"""Istantanea del grafo degli agenti — SPEC §13 «Mesh agenti».

Il DATO e' di Fase 4 (router, T1, Governor, subagent); il PANNELLO che lo
disegna e' di Fase 5. Questo modulo sta in mezzo: prende gli oggetti che
esistono nel processo e ne ricava una descrizione che il renderer possa
disegnare senza sapere nulla di come sono fatti.

⚠️ **Nessun nodo inventato.** Quando un tier non e' composto nel processo, il
suo stato e' `non collegato` e il pannello lo mostra cosi'. L'engine di oggi
(FASE = 1) compone allowlist, sandbox, GPU e server: T1 e T2 vivono nella
pipeline vocale, che e' un'altra radice di composizione. Dire «inerte» al
posto di «non collegato» sarebbe un dato falso — §11.9 — e nasconderebbe
proprio la cosa che si vuole vedere a colpo d'occhio.
"""

from __future__ import annotations

import time
from typing import Any, Protocol

# I quattro subagent di §5.3. `tests/test_agents_mesh.py` verifica che questa
# tupla corrisponda ai file veri in `.claude/agents/`: una costante che si
# scollega dalla realta' senza che nessuno se ne accorga e' peggio di niente.
SUBAGENTI = ("argus", "edith", "forge", "veronica")


class _ConStato(Protocol):
    def stato(self) -> dict[str, Any]: ...


def _nodo(id_: str, tipo: str, stato: str, dettaglio: str = "", attivo: bool = False) -> dict:
    return {"id": id_, "tipo": tipo, "stato": stato, "dettaglio": dettaglio, "attivo": attivo}


def snapshot(
    *,
    regole_t0: int,
    governor: _ConStato | None = None,
    t1: Any | None = None,
    tool_registrati: int = 0,
) -> dict[str, Any]:
    """Il grafo com'e' adesso.

    `regole_t0` e `tool_registrati` sono conteggi veri, non stime: il primo
    viene dalle regole compilate in `core/llm/grammar.py`, il secondo
    dall'allowlist.
    """
    nodi = [
        _nodo("router", "ingresso", "pronto", f"{tool_registrati} tool in allowlist"),
        _nodo("t0", "tier", "pronto", f"{regole_t0} regole · zero LLM"),
    ]

    if t1 is None:
        nodi.append(_nodo("t1", "tier", "non collegato", "pipeline vocale"))
    else:
        vivo = bool(getattr(t1, "vivo", False))
        occupato = bool(getattr(t1, "_occupato", False))
        nodi.append(
            _nodo(
                "t1", "tier",
                "genera" if occupato else ("in ascolto" if vivo else "spento"),
                "sessione persistente",
                attivo=occupato,
            )
        )

    if governor is None:
        nodi.append(_nodo("t2", "tier", "non collegato", "Governor assente"))
    else:
        g = governor.stato()
        nodi.append(
            _nodo(
                "t2", "tier",
                "sospeso" if g["sospeso"] else ("attivo" if g["attivi"] else "inerte"),
                f"{g['attivi']}/{g['max_concurrent']} · {g['restanti']} nella finestra",
                attivo=bool(g["attivi"]),
            )
        )

    # I subagent non hanno uno stato proprio finche' un T2 non li spawna: e'
    # il Governor a sapere se ce n'e' uno vivo. Senza Governor nel processo,
    # «non collegato» come i tier.
    for nome in SUBAGENTI:
        nodi.append(_nodo(nome, "subagent", "inerte" if governor else "non collegato"))

    archi = [
        ("router", "t0"),
        ("router", "t1"),
        ("t1", "t2"),
        *[("t2", nome) for nome in SUBAGENTI],
    ]

    return {
        "topic": "agent.mesh",
        "ts": time.time(),
        "nodi": nodi,
        "archi": [list(a) for a in archi],
    }
