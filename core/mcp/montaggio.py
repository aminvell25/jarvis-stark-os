"""Montare i server MCP dichiarati — ADR-007, l'ultimo miglio.

## Perche' questo file esiste

Senza, `client.py` e `promozione.py` sarebbero una libreria che nessuno chiama:
provata, corretta, e assente dal processo vero. E' il difetto che questo
progetto ha incontrato **cinque volte in due giorni** — i quattro tool di
memoria di §13, il `Watcher` delle news, `_gradi()` che componeva solo T1,
`PhraseWake.set_frasi()`, l'azione vocale su un topic che nessuno ascoltava.
Ogni volta: due pezzi scritti, provati, e mai congiunti.

## Che cosa monta, e che cosa no

Monta i server dichiarati in `settings.toml` e promuove **solo** i tool che
quel file nomina. Un server con `promossi = []` si avvia, si guarda cosa
propone, e non se ne usa niente — che e' uno stato utile: e' come si guarda un
server prima di fidarsene.

## Un guasto qui non ferma JARVIS

Un server MCP e' un programma di terzi. Se non parte, se parla male, se annuncia
uno schema che non sappiamo leggere, quello che si perde e' **quel server**.
Il core continua, e lo dice. La forma e' quella dei gradi in `engine.py`: cio'
che non si accende viene annunciato, non nascosto.
"""

from __future__ import annotations

from typing import Any

import structlog

from core.mcp.client import ErroreMcp, ServerMcp
from core.mcp.promozione import (
    NonAnnunciato,
    SchemaNonRappresentabile,
    promuovi_mcp,
)
from core.tools.registry import DuplicateTool

log = structlog.get_logger(__name__)


class MontaggioMcp:
    """I server montati, e come si spengono."""

    def __init__(self) -> None:
        self.server: list[ServerMcp] = []
        #: Cosa e' andato storto, per lo snapshot e per chi indaga. Un
        #: montaggio fallito che non lascia traccia e' un tool che non c'e'
        #: senza che nessuno sappia perche'.
        self.guasti: list[dict[str, str]] = []
        self.promossi: list[str] = []

    def stato(self) -> dict[str, Any]:
        return {
            "server": [s.nome for s in self.server],
            "promossi": sorted(self.promossi),
            "guasti": list(self.guasti),
        }

    async def ferma(self) -> None:
        for s in self.server:
            try:
                await s.ferma()
            except Exception as exc:                     # pragma: no cover
                log.warning("mcp_arresto_fallito", server=s.nome, errore=repr(exc))
        self.server.clear()


async def monta(impostazioni) -> MontaggioMcp:
    """Avvia i server dichiarati e promuove i tool nominati.

    `impostazioni` e' un `McpSettings`. Se `enabled` e' falso non si avvia
    niente, e non e' un caso da gestire: e' il caso normale.
    """
    montaggio = MontaggioMcp()
    if not impostazioni.enabled:
        log.info("grado_spento", grado="mcp",
                 perche="mcp.enabled = false: nessun server di terzi avviato")
        return montaggio

    for dichiarato in impostazioni.servers:
        server = ServerMcp(dichiarato.nome, list(dichiarato.comando))
        try:
            await server.avvia()
            annunciati = await server.elenca()
        except (ErroreMcp, OSError) as exc:
            montaggio.guasti.append({"server": dichiarato.nome,
                                     "errore": str(exc)[:200]})
            log.error("mcp_non_montato", server=dichiarato.nome, errore=str(exc)[:200])
            await server.ferma()
            continue

        montaggio.server.append(server)
        # ⚠️ Si registra QUANTI ne propone, non QUALI: i nomi vengono da un
        # terzo e finirebbero nei nostri log, dove qualcuno potrebbe
        # rileggerli. Chi vuole vederli usa `elenca()` e li guarda una volta.
        log.info("mcp_montato", server=dichiarato.nome, propone=len(annunciati),
                 nominati=len(dichiarato.promossi))

        for voce in dichiarato.promossi:
            try:
                strumento = promuovi_mcp(server, voce.tool, voce.side_effect)
            except (NonAnnunciato, SchemaNonRappresentabile, DuplicateTool) as exc:
                montaggio.guasti.append({"server": dichiarato.nome,
                                         "tool": voce.tool,
                                         "errore": str(exc)[:200]})
                log.error("mcp_promozione_fallita", server=dichiarato.nome,
                          tool=voce.tool, errore=str(exc)[:200])
                continue
            montaggio.promossi.append(strumento.name)

    log.info("grado_acceso", grado="mcp", server=len(montaggio.server),
             promossi=len(montaggio.promossi), guasti=len(montaggio.guasti))
    return montaggio
