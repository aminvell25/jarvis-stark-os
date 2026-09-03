"""L'osservatore sulle bozze — la meta' «occhi» del laboratorio (ADR-015).

Quando uno STL dentro `bozze/<nome>/` cambia, il pannello lo mostra. Chi l'ha
scritto non importa: la sandbox dopo `esegui_bozza`, o il proprietario che ha
lanciato `genera.py` dal suo terminale, o un CAD che ha esportato li'. Questo
modulo **legge soltanto**: non esegue niente, non tocca il file, non decide
niente. Eseguire resta di `esegui_bozza`, con la conferma di §6.2 — e non
diventa automatico quando il file cambia, perche' il file in `bozze/` puo'
averlo scritto T2 e un innesco «e' cambiato» non distingue chi.

## Perche' un giro di `stat` e non inotify

`watchdog` c'e' gia' per le impostazioni. Ma i watch inotify sono contati
per utente, e su questa macchina la scrivania ne consuma abbastanza da far
cadere nove test; e un osservatore ricorsivo su `bozze/` ne vuole uno per
cartella. Un giro di `stat` su poche decine di file ogni secondo, in asyncio,
non ha limiti da esaurire, funziona anche se la cartella non esiste ancora,
e si prova con un intervallo di cinquanta millisecondi senza un thread.

## Che cosa conta come «cambiato»

Un file si pubblica quando il suo contenuto e' diverso dall'ultimo pubblicato
— l'hash, non l'mtime: rieseguire uno script deterministico riscrive gli
stessi byte, e riproporre lo stesso pezzo sarebbe rumore. E si pubblica solo
quando e' **fermo**: due giri consecutivi con la stessa dimensione e lo stesso
mtime. Uno STL da 80 KB si scrive in piu' chiamate, e a meta' scrittura non
torna coi conti.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import structlog

from core.tools.laboratorio import anteprima_di
from core.traccia import Origine, Traccia

log = structlog.get_logger(__name__)

#: L'intento della riga di diario. Non e' mai un guasto: uno STL che non si
#: puo' mostrare e' un fatto del file, e la riga lo dice con `mostrata=False`.
INTENTO = "anteprima_bozza"

_Impronta = tuple[int, int]


class OsservatoreBozze:
    """Guarda `bozze/*/*.stl` e pubblica `model3d.preview` quando uno cambia.

    `pubblica` e `annota` arrivano per funzione, come per il diario: questo
    modulo non sa che cosa sia un socket, e i test lo misurano senza aprirne
    uno.
    """

    def __init__(
        self,
        bozze: Callable[[], Path],
        pubblica: Callable[[dict[str, Any]], Awaitable[None]],
        annota: Callable[..., Awaitable[None]] | None = None,
        ogni_s: float = 1.0,
    ) -> None:
        self._bozze = bozze
        self._pubblica = pubblica
        self._annota = annota
        self._ogni_s = float(ogni_s)
        #: L'ultimo `(size, mtime_ns)` visto per file: serve a dire «fermo».
        self._visti: dict[Path, _Impronta] = {}
        #: L'hash dell'ultimo contenuto PUBBLICATO (o rifiutato) per file.
        self._pubblicati: dict[Path, str] = {}
        self._compito: asyncio.Task | None = None
        self.giri = 0
        self.pubblicazioni = 0

    # ── ciclo di vita ────────────────────────────────────────────────────────

    def avvia(self) -> None:
        if self._compito is None:
            # Il primo giro segna cio' che c'e' GIA' come visto e pubblicato:
            # all'avvio non si riapre il pannello per ogni pezzo di ieri.
            self._fotografa_senza_pubblicare()
            self._compito = asyncio.get_running_loop().create_task(self._ciclo())

    async def ferma(self) -> None:
        if self._compito is None:
            return
        self._compito.cancel()
        try:
            await self._compito
        except asyncio.CancelledError:
            pass
        self._compito = None

    # ── il giro ──────────────────────────────────────────────────────────────

    def _stl(self) -> list[Path]:
        radice = self._bozze()
        if not radice.is_dir():
            return []
        fuori: list[Path] = []
        for cartella in radice.iterdir():
            if not cartella.is_dir():
                continue
            fuori.extend(p for p in cartella.iterdir()
                         if p.is_file() and p.suffix.lower() == ".stl")
        return fuori

    @staticmethod
    def _impronta(p: Path) -> _Impronta | None:
        try:
            st = p.stat()
        except OSError:
            return None
        return (st.st_size, st.st_mtime_ns)

    def _fotografa_senza_pubblicare(self) -> None:
        for p in self._stl():
            imp = self._impronta(p)
            if imp is None:
                continue
            self._visti[p] = imp
            try:
                self._pubblicati[p] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue

    async def _ciclo(self) -> None:
        while True:
            try:
                await self.giro()
            except Exception as exc:                        # noqa: BLE001
                # Un giro che cade non ferma l'osservatore: il prossimo
                # ricomincia. E lo dice, perche' un osservatore muto e'
                # indistinguibile da uno spento.
                log.error("osservatore_bozze_giro_caduto", errore=repr(exc))
            await asyncio.sleep(self._ogni_s)

    async def giro(self) -> list[Path]:
        """Un giro solo, esposto per i test. Ritorna i file pubblicati."""
        self.giri += 1
        pubblicati: list[Path] = []
        presenti = set()
        for p in self._stl():
            presenti.add(p)
            imp = self._impronta(p)
            if imp is None:
                continue
            prima = self._visti.get(p)
            self._visti[p] = imp
            if prima != imp:
                continue                 # e' cambiato adesso: aspetto che sia fermo
            try:
                impronta = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
            if self._pubblicati.get(p) == impronta:
                continue                 # stessi byte dell'ultima volta
            self._pubblicati[p] = impronta
            if await self._pubblica_uno(p):
                pubblicati.append(p)
        # Un file sparito si dimentica: se ricompare, e' nuovo.
        for p in [q for q in self._visti if q not in presenti]:
            self._visti.pop(p, None)
            self._pubblicati.pop(p, None)
        return pubblicati

    async def _pubblica_uno(self, p: Path) -> bool:
        bozza = p.parent.name
        messaggio, esito = anteprima_di(p, bozza)
        # ADR-011: ogni cosa che comincia porta una traccia. Qui comincia un
        # cambiamento sul disco che nessuno ha chiesto a voce: l'origine e' la
        # stessa delle ronde, una sorveglianza che JARVIS tiene da solo.
        traccia = Traccia.nuova(Origine.PROTOCOLLO)
        if messaggio is not None:
            try:
                await self._pubblica(messaggio)
            except Exception as exc:                        # noqa: BLE001
                log.warning("anteprima_non_pubblicata", file=str(p), errore=repr(exc))
                esito = f"{p.name} non pubblicata: {type(exc).__name__}"
                messaggio = None
        mostrata = messaggio is not None
        if mostrata:
            self.pubblicazioni += 1
        log.info("anteprima_bozza", bozza=bozza, file=p.name, mostrata=mostrata, esito=esito)
        if self._annota is not None:
            await self._annota("azione", traccia.id, intento=INTENTO, ok=True,
                               verdetto=None, da=str(traccia.origine), strada="core",
                               bozza=bozza, file=p.name, mostrata=mostrata, esito=esito)
        return mostrata
