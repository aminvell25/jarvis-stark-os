"""Router T0: comandi deterministici senza LLM — SPEC §7.6, invariante 14.

Il linguaggio dei comandi e' finito: un parser a grammatica e' piu' veloce di
qualunque modello, gratuito, e non allucina. Copre circa l'80% di cio' che
l'utente dira' a JARVIS.

E' **il componente piu' critico per la latenza dell'intero sistema** e deve
stare sotto i 10 ms: niente LLM, niente embedding, niente regex compilate a
runtime. Le regole si compilano UNA VOLTA all'import.

Ed e' l'unico tier che sopravvive a tutto. Con la rete staccata, il token
scaduto e Deepgram irraggiungibile, T0 continua a funzionare: e' cio' che
rende `degraded_llm` e `offline` (§16) stati utilizzabili invece che eufemismi
per "rotto".
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Intent:
    tool: str
    args: dict = field(default_factory=dict)
    confidence: float = 1.0


#: Ogni regola: (pattern compilato, tool, mappatura dei gruppi).
_RULES: list[tuple[re.Pattern, str, Callable[[re.Match], dict]]] = []


def _rule(pattern: str, tool: str, mapper: Callable[[re.Match], dict] = lambda m: {}) -> None:
    _RULES.append((re.compile(pattern, re.IGNORECASE), tool, mapper))


_WORDS = {"uno": 1, "due": 2, "tre": 3, "quattro": 4}


def _num(s: str) -> int:
    return int(s) if s.isdigit() else _WORDS[s.lower()]


# ── pannelli ─────────────────────────────────────────────────────────────────
#
# Gli articoli italiani sono sette e le preposizioni articolate molte di piu'.
# Le regex di §7.6 ne prevedevano tre, e il corpus di `tests/t0_corpus.py` ha
# fatto cadere subito "apri le news", "mostra gli agenti" e "stato del
# sistema". Non e' pignoleria linguistica: sono le forme in cui una persona
# parla davvero, e un comando che non risponde a "apri le news" verrebbe letto
# come un guasto.
_ART = r"(?:il|lo|la|i|gli|le|l'|un|una|uno)\s*"
_PANNELLI = r"telemetria|console|file|globo|agenti|news|sorgente|impostazioni|browser|board|archivio"

# ── §26.6 — le scene ─────────────────────────────────────────────────────────
#
# PRIMA di `open_panel`, e non e' un caso: «apri la scena briefing» comincia
# con lo stesso verbo di «apri il globo», e la regola dei pannelli
# catturerebbe la parola `scena` come se fosse il nome di un pannello. Chi
# scrive una regola nuova qui sotto la metta dove il corpus dice, non dove sta
# comoda: e' cosi' che si e' scoperta la collisione fra youtube e i file.
#
# Il nome della scena e' ristretto alla forma degli identificatori. §26.6:
# JARVIS richiama scene DICHIARATE, e una che non esiste non fa niente — non
# c'e' nessun percorso per cui una parola qualunque diventi una geometria.
_SCENA = r"[a-z0-9][a-z0-9_.-]{0,63}"
_rule(rf"\b(?:apri|mostra|metti|richiama|passa a)\s+(?:{_ART})?scena\s+"
      rf"(?:{_ART})?(?P<s>{_SCENA})\b",
      "scene", lambda m: {"nome": m.group("s").lower()})
_rule(rf"\bscena\s+(?P<s>{_SCENA})\b",
      "scene", lambda m: {"nome": m.group("s").lower()})

_rule(rf"\b(?:apri|mostra)\s+(?:{_ART})?(?:pannello\s+)?(?:{_ART})?(?P<p>{_PANNELLI})\b",
      "open_panel", lambda m: {"panel": m.group("p").lower()})
_rule(rf"\bchiudi\s+(?:{_ART})?(?:pannello\s+)?(?:{_ART})?(?P<p>\w+)\b",
      "close_panel", lambda m: {"panel": m.group("p").lower()})
_rule(r"\b(?:nascondi tutto|via tutto)\b", "hide_all")
_rule(r"\baffianca\b", "tile_panels")

# ── web e YouTube — Fase 6, §6.3 ─────────────────────────────────────────────
#
# Stanno QUI, dopo i pannelli e prima di tutto il resto, per due motivi.
#
# Dopo i pannelli: "apri il browser" deve restare un pannello, non un URL.
#
# Prima della regola dei file: quella cattura qualunque frase che cominci per
# "cerca", e si mangerebbe "cerca synthwave su youtube".
#
# La frase del criterio di §22 e' "apri youtube e metti synthwave": una frase
# sola con due verbi, che nel parlato e' la forma normale. Il gruppo della
# query e' opzionale perche' "apri youtube" da solo deve funzionare lo stesso.
# L'ordine DENTRO il gruppo conta quanto l'ordine fra i gruppi. "metti
# synthwave su youtube" ha la query PRIMA del sito, "apri youtube e metti
# synthwave" dopo: sono due frasi diverse e vanno due regole, con quella a
# query anticipata per prima — altrimenti l'altra riconosce "youtube" e si
# porta via la frase con la query vuota. Se ne e' accorto il corpus.
_rule(r"\b(?:metti|cerca|riproduci|fai partire)\s+(?P<q>.+?)\s+su\s+youtube\b",
      "youtube_search", lambda m: {"query": m.group("q").strip()})
_rule(rf"\b(?:apri|vai su|metti)?\s*(?:{_ART})?youtube\b"
      rf"(?:.*?\b(?:metti|riproduci|fai partire|cerca)\s+(?P<q>.+?))?\s*$",
      "youtube_search", lambda m: {"query": (m.group("q") or "").strip()})
_rule(r"\bapri\s+(?P<u>https://\S+)",
      "open_web", lambda m: {"url": m.group("u")})

# ── workspace ────────────────────────────────────────────────────────────────
_rule(r"\bworkspace\s+(?P<n>[1-4]|uno|due|tre|quattro)\b",
      "switch_workspace", lambda m: {"n": _num(m.group("n"))})


#: Gli intenti che NON sono tool: sono azioni della scrivania (§13).
#:
#: Sta qui, accanto alle regole che li producono, e non nell'engine: due
#: elenchi in due file divergono al primo comando aggiunto. `core/engine.py` lo
#: importa per decidere che strada prende un intento, esattamente come
#: `core/gestures/mapping.py` fa con `INTENTI_UI` per §14 — e come li', e'
#: un'ALLOWLIST: cio' che non e' ne' qui dentro ne' nel registry non passa.
INTENTI_UI = frozenset({
    "open_panel", "close_panel", "hide_all", "tile_panels", "switch_workspace",
    # §26.6. Come gli altri: non tocca niente di reale, dispone finestre.
    "scene",
})

# ── sistema ──────────────────────────────────────────────────────────────────
# `stato della memoria`, `stato del sistema`: le preposizioni articolate sono
# il modo normale di dirlo in italiano.
_PREP = r"(?:del|della|dello|dei|delle|degli|di)\s+"
_rule(rf"\b(?:come sta|stato)\s+(?:{_ART}|{_PREP})?(?:cpu|memoria|ram|sistema)\b",
      "system_status")
_rule(r"\b(?:cosa|chi)\s+(?:sta\s+)?rallent\w+\b", "top_processes")
_rule(r"\bvolume\s+(?P<v>\d{1,3})\b",
      "set_volume", lambda m: {"level": min(100, int(m.group("v")))})
_rule(r"\b(?:silenzio|muto)\b", "mute")

# ── meta-comandi ─────────────────────────────────────────────────────────────
# Non chiedono UNA COSA, chiedono lo STATO. La frase e' deterministica (T0),
# l'esecuzione e' un fan-out di subagent (T2, Fase 4). Idea adottata da
# amanimran786/jarvis-ai, vedi docs/ANALISI-REPO-E-TECNOLOGIE.md §1.3③.
_rule(r"\b(?:riassumimi la giornata|briefing|fammi il punto)\b", "brief_me")
_rule(r"\bcosa (?:richiede|serve|vuole) la mia attenzione\b", "needs_attention")
_rule(r"\b(?:come stiamo|stato dei sistemi|diagnostica)\b", "doctor")

# ── file ─────────────────────────────────────────────────────────────────────
# ⚠️ ULTIMA, e non per caso. Il suo pattern e' il piu' permissivo di tutti: in
# cima catturerebbe qualunque frase che cominci per "cerca". L'ordine delle
# regole E' parte della grammatica.
_rule(r"\bcerca\s+(?:il\s+file\s+|i\s+file\s+)?(?P<q>.+?)(?:\s+nei file)?$",
      "search_files", lambda m: {"query": m.group("q").strip()})


def parse(text: str) -> Intent | None:
    """Intent se il testo e' un comando noto, altrimenti `None`.

    **`None` NON e' un errore**: e' la risposta corretta per il ~20% di frasi
    che devono andare a T1 o T2. Un parser che sollevasse costringerebbe il
    chiamante a trattare la conversazione come un guasto.

    Non solleva mai, nemmeno su input malformato: e' sul percorso della voce, e
    un'eccezione qui zittirebbe JARVIS.

    ⚠️ **Rifiuta cio' che non e' una stringa**, e in particolare `Untrusted`.
    Il parser trasforma testo in AZIONI: una pagina web che contenesse "apri il
    pannello file" ne uscirebbe come un intento vero. Il contratto di non
    sollevare resta — restituisce `None` — ma la cosa si registra, perche' un
    contenuto non fidato arrivato fin qui e' un errore di cablaggio, non un
    caso normale.
    """
    if not isinstance(text, str):
        log.warning("parse_rifiutato_non_stringa", tipo=type(text).__name__)
        return None
    try:
        t = " ".join(text.strip().lower().split())
        if not t:
            return None
        for pattern, tool, mapper in _RULES:
            m = pattern.search(t)
            if m:
                return Intent(tool=tool, args=mapper(m))
    except Exception:                      # una regola malscritta non zittisce
        return None
    return None


def regole() -> list[tuple[str, str]]:
    """(pattern, tool) di ogni regola, nell'ordine. Per la diagnosi e i test."""
    return [(p.pattern, tool) for p, tool, _ in _RULES]
