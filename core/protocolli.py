"""I protocolli dichiarati — cio' che JARVIS fa di sua iniziativa, e solo quello.

## Perche' esistono, e da dove viene la forma

Nei due film JARVIS non improvvisa mai un'azione che tocchi il mondo. Le due
volte in cui lo fa — *House Party Protocol*, *Clean Slate Protocol* — esegue un
comando **che Tony aveva scritto mesi prima** e che richiama per nome. Fuori da
un protocollo, riferisce e chiede.

E' la stessa forma dell'allowlist che questo progetto usa dappertutto: un
protocollo non e' una liberta', e' una dichiarazione. Chi lo scrive e' l'utente,
in `settings.toml`, versionato e ispezionabile; JARVIS lo esegue e basta.

## ⚠️ `side_effect=False` NON vuol dire «non agisce»

Il primo disegno di questo modulo filtrava i tool su `side_effect`. E' sbagliato,
ed e' misurato: `open_web` ha `side_effect=False` e la sua stessa descrizione
dice *«Apre una pagina https in un pannello browser»*; `youtube_search` ha
`side_effect=False` e *«lo fa partire»*.

In questo progetto `side_effect=True` significa **«c'e' un percorso risolto da
mostrare a chi conferma»** (invariante 3, §6.2) — cioe' «tocca il disco» — non
«cambia qualcosa». Un'allowlist costruita su quel campo avrebbe lasciato JARVIS
aprire pagine e far partire video di propria iniziativa.

Quindi `TOOL_OSSERVATIVI` e' **esplicita**, e un test la confronta col registro:
ogni nome deve esistere e non avere effetti sul disco, ed e' rosso se qualcuno
ce ne mette uno che agisce.

## Che cosa fa un protocollo

Guarda una cosa, e parla **solo quando quella cosa cambia**. E' la forma della
tossicita' del sangue di Iron Man 2: JARVIS sorveglia un numero e lo dice quando
si muove, non a ogni giro.

Il primo giro non dice niente: non c'e' un cambiamento, c'e' un primo valore.
Il silenzio di un protocollo che non ha trovato niente non e' un guasto — e non
resta muto per sempre, perche' il resoconto al risveglio dice «niente da
riferire» una volta al giorno comunque (vedi `core/memory/risveglio.py`).
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

#: Quando un protocollo puo' scattare. Allowlist: un innesco che non e' qui non
#: esiste, e la configurazione che lo nomina viene rifiutata a voce alta invece
#: di restare inerte in silenzio.
INNESCHI = ("risveglio", "notte")

#: I tool che un protocollo puo' invocare.
#:
#: ⚠️ **Esplicita, e non derivata da `side_effect`**: vedi il modulo. Sono i
#: tool che GUARDANO — leggono il disco dentro le radici consentite, lo stato
#: della macchina, la memoria di JARVIS o la propria finestra — e nessuno di
#: loro cambia qualcosa che il Signore possa vedere.
#:
#: Restano fuori, pur avendo `side_effect=False`: `open_web` e `youtube_search`
#: (aprono una pagina, fanno partire un video), `mute`, `unmute`, `set_volume`
#: (cambiano la voce), `read_screen` (fa una cattura vera, §12, e costa).
TOOL_OSSERVATIVI = frozenset({
    "list_dir", "read_file", "search_files", "stat_path",
    "system_status", "top_processes", "timezones",
    "source_tree", "archive_notes",
    "recall", "list_topics",
    "ask_state",
})

#: Il tipo di iniziativa che un protocollo registra. Uno solo per tutti: chi
#: rilegge `initiatives/` vuole sapere che e' stato un protocollo e quale, non
#: avere un tipo nuovo per ogni riga che qualcuno scrive nel TOML.
TIPO_INIZIATIVA = "protocollo"


class ProtocolloRifiutato(ValueError):
    """Una dichiarazione che non si puo' eseguire. Si dice, non si ignora."""


@dataclass(frozen=True)
class Protocollo:
    """Una dichiarazione, gia' validata."""

    nome: str
    innesco: str
    tool: str
    args: dict[str, Any]
    frase: str


@dataclass(frozen=True)
class Esito:
    """Che cosa e' successo eseguendone uno."""

    nome: str
    eseguito: bool
    cambiato: bool
    frase: str = ""
    errore: str | None = None


def _slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-") or "senza-nome"


def firma(uscita: Any) -> str:
    """Un'impronta stabile di cio' che un tool ha risposto.

    ⚠️ **Canonica**: `sort_keys` e separatori fissi, o due esecuzioni identiche
    darebbero impronte diverse a seconda dell'ordine di un dizionario e ogni
    giro sembrerebbe un cambiamento. Un sorvegliante che grida sempre e' un
    sorvegliante che si spegne.
    """
    testo = json.dumps(uscita, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), default=str)
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()[:16]


def valida(grezzo: Any, *, nomi_tool: frozenset[str] | set[str]) -> Protocollo:
    """Da dichiarazione a `Protocollo`, o `ProtocolloRifiutato`.

    Fail-closed su ogni campo: un protocollo che non si puo' eseguire non deve
    poter restare inerte in silenzio, o il Signore crederebbe che JARVIS
    sorvegli qualcosa che nessuno guarda.
    """
    nome = str(getattr(grezzo, "nome", "") or "").strip()
    if not nome:
        raise ProtocolloRifiutato("un protocollo senza nome non si puo' nominare")

    innesco = str(getattr(grezzo, "innesco", "") or "")
    if innesco not in INNESCHI:
        raise ProtocolloRifiutato(
            f"{nome}: innesco '{innesco}' sconosciuto, ammessi {list(INNESCHI)}")

    tool = str(getattr(grezzo, "tool", "") or "")
    if tool not in TOOL_OSSERVATIVI:
        raise ProtocolloRifiutato(
            f"{nome}: '{tool}' non e' un tool osservativo. ⚠️ Non basta che non "
            "abbia effetti sul disco: `open_web` non ne ha e apre una pagina. "
            f"Ammessi: {sorted(TOOL_OSSERVATIVI)}")
    if tool not in nomi_tool:
        raise ProtocolloRifiutato(
            f"{nome}: '{tool}' non e' registrato in questo avvio")

    frase = str(getattr(grezzo, "frase", "") or "").strip()
    if not frase:
        raise ProtocolloRifiutato(
            f"{nome}: senza una frase, un cambiamento trovato non si puo' dire")

    args = dict(getattr(grezzo, "args", None) or {})
    return Protocollo(nome=nome, innesco=innesco, tool=tool, args=args,
                      frase=frase)


def carica(dichiarati: list[Any], *, nomi_tool: frozenset[str] | set[str]
           ) -> list[Protocollo]:
    """I protocolli validi. Uno rifiutato non porta via gli altri.

    ⚠️ Il rifiuto e' **rumoroso**: `log.error`. Una dichiarazione storta che
    sparisse in silenzio sarebbe la peggiore delle tre uscite possibili — JARVIS
    non sorveglia, e nessuno lo sa.
    """
    buoni: list[Protocollo] = []
    for d in dichiarati:
        try:
            buoni.append(valida(d, nomi_tool=nomi_tool))
        except ProtocolloRifiutato as exc:
            log.error("protocollo_rifiutato", perche=str(exc))
    return buoni


class Ronda:
    """Esegue i protocolli e ricorda che cosa avevano visto l'ultima volta."""

    def __init__(self, radice: Path) -> None:
        self.radice = Path(radice)
        self.radice.mkdir(parents=True, exist_ok=True)

    def _memoria(self, nome: str) -> Path:
        return self.radice / f"{_slug(nome)}.json"

    def vista(self, nome: str) -> str | None:
        try:
            return json.loads(self._memoria(nome).read_text()).get("firma")
        except (OSError, ValueError):
            return None

    def _ricorda(self, nome: str, impronta: str) -> None:
        self._memoria(nome).write_text(
            json.dumps({"firma": impronta, "ts": time.time()}), encoding="utf-8")

    async def esegui(self, p: Protocollo, invoca) -> Esito:
        """Un giro. `invoca(tool, args)` e' `registry.invoke`.

        Non solleva: un protocollo e' un compito di sfondo, e un tool che cade
        non deve poter portare via il risveglio.
        """
        try:
            r = await invoca(p.tool, p.args)
        except Exception as exc:                          # pragma: no cover
            log.error("protocollo_caduto", nome=p.nome, errore=repr(exc))
            return Esito(nome=p.nome, eseguito=False, cambiato=False,
                         errore=repr(exc))
        if not getattr(r, "ok", False):
            errore = getattr(r, "error", None) or "il tool ha risposto ok=False"
            log.warning("protocollo_senza_risposta", nome=p.nome, errore=errore)
            return Esito(nome=p.nome, eseguito=False, cambiato=False,
                         errore=errore)

        adesso = firma(getattr(r, "output", None))
        prima = self.vista(p.nome)
        self._ricorda(p.nome, adesso)

        # ⚠️ Il PRIMO giro non e' un cambiamento: e' un primo valore. Dirlo
        # vorrebbe dire che ogni protocollo nuovo parla una volta per niente,
        # e la prima cosa che JARVIS dice di sua iniziativa sarebbe rumore.
        cambiato = prima is not None and prima != adesso
        log.info("protocollo_eseguito", nome=p.nome, innesco=p.innesco,
                 cambiato=cambiato, primo_giro=prima is None)
        return Esito(nome=p.nome, eseguito=True, cambiato=cambiato,
                     frase=p.frase if cambiato else "")
