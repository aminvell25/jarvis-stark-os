"""Client MCP minimo — ADR-007, azione 1.

## Perche' scritto e non importato

L'SDK ufficiale sarebbe una dipendenza nuova, e `CLAUDE.md` dice di non
aggiungerne senza chiedere. Il trasporto stdio di MCP e' **JSON-RPC 2.0
delimitato da righe**: un oggetto JSON per riga su stdin e stdout. Quello che
serve qui sono tre chiamate — `initialize`, `tools/list`, `tools/call` — e
scriverle costa meno di centocinquanta righe.

E' la stessa scelta gia' fatta tre volte in questo progetto: `ws_probe.py`
invece di `websocat`, `pw-record` invece di `sounddevice`, un gate a energia
invece di Silero. Ogni volta scritta e dichiarata.

⚠️ **Invariante 30.** Questo file e' scritto dalla specifica pubblica del
protocollo, non copiato da nessuna implementazione. JSON-RPC 2.0 e i nomi dei
metodi sono formato, non codice.

## Che cosa NON fa

Non fa risorse, non fa prompt, non fa sampling, non fa notifiche dal server
verso di noi. Un client che fa meno e' un client che sbaglia meno, e ADR-007
chiede una cosa sola: **che i tool di un server possano essere proposti**.
Disporre e' del registry.

Non decide niente sulla sicurezza. Chi decide sta in `promozione.py`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

log = structlog.get_logger(__name__)

#: La versione di protocollo che dichiariamo. Un server che ne parla un'altra
#: risponde comunque con la propria: la si registra e la si mostra, non la si
#: contratta. Negoziare all'indietro vorrebbe dire supportare piu' dialetti, e
#: ognuno e' una superficie in piu'.
VERSIONE_PROTOCOLLO = "2024-11-05"

#: Quanto si aspetta una risposta. Un server MCP e' un processo di terzi: se
#: non risponde, l'attesa non deve diventare eterna dentro un turno vocale.
TIMEOUT_S = 20.0

#: Tetto alla riga letta. Un server che manda un megabyte su una riga sola
#: riempirebbe la memoria prima che qualcuno se ne accorga.
MAX_RIGA = 1 << 20


class ErroreMcp(RuntimeError):
    """Guasto di protocollo o di trasporto. Non propaga oltre `promozione.py`,
    che lo converte in `ToolResult(ok=False)` — *Stile codice*: nessuna
    eccezione arriva all'LLM."""


class ServerMcp:
    """Un server MCP parlato su stdio.

    Il processo si avvia con `avvia()` e si ferma con `ferma()`. Fra i due, tre
    metodi: `elenca()`, `chiama()`, e `nomi_annunciati()` che e' solo memoria
    dell'ultimo elenco.
    """

    def __init__(self, nome: str, argv: list[str], *,
                 cwd: str | None = None, env: dict[str, str] | None = None) -> None:
        if not argv:
            raise ValueError("un server MCP ha bisogno di un comando da eseguire")
        self.nome = nome
        self._argv = list(argv)
        self._cwd = cwd
        self._env = env
        self._proc: asyncio.subprocess.Process | None = None
        self._id = 0
        self._annunciati: dict[str, dict[str, Any]] = {}
        #: Una richiesta per volta. Il protocollo permette il parallelismo con
        #: gli `id`, ma qui non serve e un lettore condiviso fra piu' attese
        #: sarebbe un modo di consegnare la risposta sbagliata a chi aspetta.
        self._turno = asyncio.Lock()

    # ── ciclo di vita ────────────────────────────────────────────────────────

    @property
    def vivo(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def avvia(self) -> dict[str, Any]:
        """Avvia il processo e stringe la mano. Ritorna cio' che il server dice
        di se' — che e' **dato di terzi**, e chi lo mostra lo tratta come tale.
        """
        if self.vivo:
            raise ErroreMcp(f"{self.nome}: gia' avviato")
        self._proc = await asyncio.create_subprocess_exec(
            *self._argv, cwd=self._cwd, env=self._env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            # ⚠️ Lo stderr del server NON si mescola al nostro: e' testo di
            # terzi, e finirebbe nei nostri log dove qualcuno potrebbe
            # rileggerlo. Si scarta.
            stderr=asyncio.subprocess.DEVNULL,
        )
        risposta = await self._richiedi("initialize", {
            "protocolVersion": VERSIONE_PROTOCOLLO,
            "capabilities": {},
            "clientInfo": {"name": "jarvis-os", "version": "1"},
        })
        await self._notifica("notifications/initialized")
        log.info("mcp_avviato", server=self.nome,
                 protocollo=str(risposta.get("protocolVersion", "?"))[:32])
        return risposta

    async def ferma(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None or proc.returncode is not None:
            return
        try:
            if proc.stdin is not None and not proc.stdin.is_closing():
                proc.stdin.close()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except (asyncio.TimeoutError, ProcessLookupError, BrokenPipeError):
            # Un server che non se ne va da solo se ne va lo stesso. Non
            # aspettiamo: si uccide e basta, come `LinuxAudio.interrupt()`.
            with_kill = getattr(proc, "kill", None)
            if with_kill is not None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
        log.info("mcp_fermato", server=self.nome)

    # ── i tre metodi che servono ─────────────────────────────────────────────

    async def elenca(self) -> list[dict[str, Any]]:
        """`tools/list`. Ritorna cio' che il server **propone**.

        Proporre non e' esistere: finche' un umano non ne nomina uno in
        `promuovi_mcp`, nessuno di questi e' invocabile (ADR-007 decisione 1).
        """
        risposta = await self._richiedi("tools/list", {})
        grezzi = risposta.get("tools")
        if not isinstance(grezzi, list):
            raise ErroreMcp(f"{self.nome}: `tools/list` non ha restituito un elenco")
        self._annunciati = {}
        for t in grezzi:
            if isinstance(t, dict) and isinstance(t.get("name"), str):
                self._annunciati[t["name"]] = t
        log.info("mcp_elenco", server=self.nome, quanti=len(self._annunciati))
        return list(self._annunciati.values())

    def nomi_annunciati(self) -> set[str]:
        """I nomi dell'ultimo `elenca()`. Memoria, non verita': un server puo'
        cambiare elenco quando vuole, ed e' precisamente la ragione della
        decisione 3 di ADR-007."""
        return set(self._annunciati)

    def annunciato(self, nome: str) -> dict[str, Any] | None:
        return self._annunciati.get(nome)

    async def chiama(self, nome: str, argomenti: dict[str, Any]) -> dict[str, Any]:
        """`tools/call`. Nessun controllo qui: li fa `promozione.py`."""
        return await self._richiedi("tools/call",
                                    {"name": nome, "arguments": argomenti})

    # ── JSON-RPC ─────────────────────────────────────────────────────────────

    async def _richiedi(self, metodo: str, parametri: dict[str, Any]) -> dict[str, Any]:
        async with self._turno:
            self._id += 1
            mio = self._id
            await self._manda({"jsonrpc": "2.0", "id": mio,
                               "method": metodo, "params": parametri})
            while True:
                msg = await self._leggi()
                # Una notifica del server non ha `id`: non e' la nostra
                # risposta, e qui non se ne fa niente. Si salta invece di
                # scambiarla per la risposta e restituire il messaggio
                # sbagliato a chi aspetta.
                if "id" not in msg:
                    continue
                if msg.get("id") != mio:
                    continue
                if "error" in msg:
                    err = msg["error"] or {}
                    raise ErroreMcp(
                        f"{self.nome}.{metodo}: "
                        f"{str(err.get('message', 'errore senza messaggio'))[:200]}"
                    )
                risultato = msg.get("result")
                if not isinstance(risultato, dict):
                    raise ErroreMcp(f"{self.nome}.{metodo}: risultato non e' un oggetto")
                return risultato

    async def _notifica(self, metodo: str) -> None:
        await self._manda({"jsonrpc": "2.0", "method": metodo, "params": {}})

    async def _manda(self, oggetto: dict[str, Any]) -> None:
        if not self.vivo or self._proc is None or self._proc.stdin is None:
            raise ErroreMcp(f"{self.nome}: server non in esecuzione")
        riga = json.dumps(oggetto, ensure_ascii=False).encode() + b"\n"
        try:
            self._proc.stdin.write(riga)
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise ErroreMcp(f"{self.nome}: il server ha chiuso l'ingresso") from exc

    async def _leggi(self) -> dict[str, Any]:
        if self._proc is None or self._proc.stdout is None:
            raise ErroreMcp(f"{self.nome}: server non in esecuzione")
        try:
            riga = await asyncio.wait_for(self._proc.stdout.readline(),
                                          timeout=TIMEOUT_S)
        except asyncio.TimeoutError as exc:
            raise ErroreMcp(f"{self.nome}: nessuna risposta in {TIMEOUT_S:.0f} s") from exc
        if not riga:
            raise ErroreMcp(f"{self.nome}: il server ha chiuso l'uscita")
        if len(riga) > MAX_RIGA:
            raise ErroreMcp(f"{self.nome}: riga da {len(riga)} byte, tetto {MAX_RIGA}")
        try:
            msg = json.loads(riga)
        except json.JSONDecodeError as exc:
            # ⚠️ Il contenuto NON entra nel messaggio d'errore: e' testo di
            # terzi, e un errore finisce nei log.
            raise ErroreMcp(f"{self.nome}: riga non e' JSON valido") from exc
        if not isinstance(msg, dict):
            raise ErroreMcp(f"{self.nome}: riga JSON non e' un oggetto")
        return msg
