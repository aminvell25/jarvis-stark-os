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

# ── l'imperativo con il pronome attaccato ────────────────────────────────────
#
# «Apriti i pannelli telemetria» e' la PRIMA frase che il Signore ha detto al
# microfono con l'intento di comandare, ed e' finita a T1 come conversazione.
# Non e' rumore di trascrizione: in italiano l'imperativo prende il pronome
# ENCLITICO — apri/aprimi/aprila/apriglielo, mostra/mostrami, chiudi/chiudilo —
# ed e' la forma normale del parlato. La grammatica conosceva solo la nuda.
#
# ⚠️ **Si allarga solo dove l'oggetto e' un'allowlist.** `t0_corpus.py` tiene
# gia' «apriti cielo» e «mostrati un po' piu' paziente» fra le frasi da NON
# rubare, e restano salve perche' `cielo` non e' un pannello: e' la stessa
# allowlist che chiuse il furto di «chiudi un occhio stavolta». Davanti a un
# oggetto a testo libero — la coda di `search_files`, la query di YouTube —
# questa estensione NON si applica: la' un pronome in piu' diventa una query,
# ed e' esattamente il difetto che quelle regole hanno gia' avuto una volta.
_ENCL = r"(?:mi|ti|ci|vi|lo|la|li|le|ne|si|gli|me|te|glie(?:lo|la|li|le))"


def _imp(*verbi: str) -> str:
    """Un imperativo, con o senza i pronomi attaccati."""
    return rf"(?:{'|'.join(verbi)})(?:{_ENCL})*"

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
_rule(rf"\b(?:{_imp('apri', 'mostra', 'metti', 'richiama')}|passa a)"
      rf"\s+(?:{_ART})?scena\s+(?:{_ART})?(?P<s>{_SCENA})\b",
      "scene", lambda m: {"nome": m.group("s").lower()})
_rule(rf"\bscena\s+(?P<s>{_SCENA})\b",
      "scene", lambda m: {"nome": m.group("s").lower()})

# ── superfici composte — ADR-013 ─────────────────────────────────────────────
#
# ⚠️ **Ancorate alla parola «superficie», come le scene lo sono a «scena».** La
# forma corta — `componi (?P<s>\w+)` — sarebbe piu' comoda da dire e
# prenderebbe «prepara il caffe'» come una richiesta di comporre la superficie
# «caffe'»: un intento rifiutato, quindi un advisory, per una frase che non
# chiedeva niente. Un'ancora costa due sillabe e toglie l'intera classe di
# falsi positivi — ed e' la scelta che §7.6 ha gia' fatto per le scene.
#
# ⚠️ «componi» NON entra in `VERBI_DI_COMANDO`: quell'elenco e' misurato contro
# il corpus (15,1 % di quasi-comandi), e allungarlo cambierebbe una misura
# pubblicata per un verbo che qui trova sempre la propria regola.
_SUPERFICIE = r"[a-z0-9][a-z0-9_-]{0,63}"
_rule(rf"\b(?:{_imp('componi', 'disponi', 'prepara')})"
      rf"\s+(?:{_ART})?superficie\s+(?:{_ART})?(?P<s>{_SUPERFICIE})\b",
      "componi_superficie", lambda m: {"nome": m.group("s").lower()})
_rule(r"\b(?:rimetti com'era|torna alla composizione precedente|"
      r"annulla la composizione)\b",
      "ripristina_layout")

_rule(rf"\b{_imp('apri', 'mostra')}\s+(?:{_ART})?(?:pannell[oi]\s+)?(?:{_ART})?"
      rf"(?P<p>{_PANNELLI})\b",
      "open_panel", lambda m: {"panel": m.group("p").lower()})
# ⚠️ `_PANNELLI` e non `\w+`, ed era un'ASIMMETRIA: `open_panel` accettava solo
# i pannelli veri, `close_panel` qualunque parola. Misurato sul corpus:
# «chiudi un occhio stavolta» diventava `close_panel {"panel": "occhio"}`.
# E' il guasto che t0_corpus.py sorveglia — rubare una frase a T1 — e chiudere
# un pannello che non esiste non e' nemmeno un comando utile: e' un errore
# silenzioso al posto di una conversazione.
_rule(rf"\b{_imp('chiudi')}\s+(?:{_ART})?(?:pannell[oi]\s+)?(?:{_ART})?"
      rf"(?P<p>{_PANNELLI})\b",
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
#: Intenti che non sono ne' azioni della scrivania ne' tool dell'allowlist: li
#: esegue la radice di composizione, perche' toccano stato che vive nel core.
#:
#: E' una **terza allowlist**, non un ramo che lascia passare il resto: chi
#: aggiunge un intento senza metterlo qui trova il rifiuto di `esegui_t0`, non
#: un varco.
INTENTI_CORE = frozenset({"silence_topic", "doctor",
                          "brief_me", "needs_attention",
                          # ADR-013. Non toccano niente di reale: dispongono
                          # finestre, come `scene`. Stanno fra i CORE e non fra
                          # gli UI perche' il compilatore e il file del layout
                          # vivono nel core — il renderer riceve una geometria
                          # gia' decisa, e non la calcola.
                          "componi_superficie", "ripristina_layout"})

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
# Il contrario, che mancava: si poteva zittire JARVIS e non riaccenderlo a
# voce. «Riattiva l'audio» e' un comando, non una conversazione.
_rule(r"\b(?:riattiva|riaccendi)\s+(?:l'audio|la voce|il volume|il suono)\b", "unmute")
_rule(r"\b(?:torna|puoi tornare)\s+a\s+parlare\b", "unmute")

# ── news: «non parlarmene piu'» (§15, regola 5) ──────────────────────────────
#
# §15 la elenca fra «le regole senza cui abbandonerà la funzione in tre
# giorni», e fino a oggi era l'unica delle cinque senza una strada: `Gate.
# silenzia()` esisteva, scriveva il file, ed era chiamata solo dai suoi test.
#
# Due forme, perche' si dice in due modi. **Anaforica** — «non parlarmene
# piu'» — che chiude cio' di cui si stava parlando adesso, e **esplicita** —
# «basta con il clima» — che nomina la cosa.
#
# ⚠️ I pattern sono STRETTI di proposito. «basta» da solo e' una delle parole
# piu' comuni della lingua, e una regola larga qui ruberebbe a T1 frasi come
# «basta cosi', grazie». Serve sempre un verbo di parola — parlare, sentire,
# dire — o il sostantivo «argomento».
_rule(r"\bnon\s+parlarmene\s+(?:piu'|piu|più)\b", "silence_topic")
_rule(rf"\bbasta\s+(?:parlare|sentire)\s+di\s+(?:{_ART})?(?P<t>[a-zàèéìòóù' ]{{3,40}})$",
      "silence_topic", lambda m: {"topic": m.group("t").strip()})
_rule(rf"\bnon\s+(?:voglio|vorrei)\s+(?:piu'|piu|più)\s+(?:sentire|sapere)\s+"
      rf"(?:parlare\s+)?di\s+(?:{_ART})?(?P<t>[a-zàèéìòóù' ]{{3,40}})$",
      "silence_topic", lambda m: {"topic": m.group("t").strip()})
_rule(rf"\bchiudi\s+(?:{_ART})?argomento(?:\s+(?P<t>[a-zàèéìòóù' ]{{3,40}}))?$",
      "silence_topic", lambda m: {"topic": (m.group("t") or "").strip()})

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
# ⚠️ E NON «cerca DI ...», che in italiano vuol dire «prova a».
# Misurato sul corpus: «cerca di capirmi» diventava
# `search_files {"query": "di capirmi"}` — JARVIS frugava nel filesystem invece
# di rispondere. Nessuno chiede una ricerca dicendo «cerca di X»: si dice
# «cerca X» o «cerca il file X», e le due forme restano intatte.
_rule(r"\bcerca\s+(?!di\s)(?:il\s+file\s+|i\s+file\s+)?(?P<q>.+?)(?:\s+nei file)?$",
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


# ── il quasi-comando ─────────────────────────────────────────────────────────
#
# Una frase che **comincia** con un imperativo che la grammatica conosce, e che
# `parse()` non ha riconosciuto. Non e' un intento e non ne diventera' uno: e'
# una riga di registro, e serve a una cosa sola — sapere QUALI comandi mancano
# senza doverli immaginare.
#
# Nasce da «apriti i pannelli telemetria», che a T0 non diceva niente e a T1
# arrivava come conversazione. Rileggendo il diario non c'era modo di
# distinguere quel caso da una chiacchierata: ho dovuto eseguire il parser a
# mano per sapere se T0 avesse anche solo visto la frase.
#
# ⚠️ **Si registra, e basta. Non entra nel contesto di T1.**
# Misurato sulle 53 frasi conversazionali di `t0_corpus.py`: 8 comincerebbero
# con un imperativo — «apriti cielo», «chiudi un occhio stavolta», «nascondi la
# delusione» — cioe' il **15,1 %**. Una frase su sette porterebbe a JARVIS un
# «nessun comando riconosciuto» in mezzo a un discorso. In un registro un falso
# positivo si vede e non costa niente; in bocca a JARVIS diventa un tic.
#
# `cerca` NON c'e', e non e' una dimenticanza: la sua regola prende qualunque
# coda (`cerca ...$`), quindi non puo' quasi-mancare — e «cerca di capirmi» e'
# gia' fra le frasi che il corpus sorveglia.
VERBI_DI_COMANDO: tuple[str, ...] = (
    "apri", "mostra", "metti", "richiama", "chiudi", "nascondi", "affianca",
    "riproduci", "riattiva", "riaccendi",
)

_QUASI = re.compile(
    rf"^(?P<v>(?:{'|'.join(VERBI_DI_COMANDO)})(?:{_ENCL})*)\b", re.IGNORECASE)


def quasi_comando(text: str) -> str | None:
    """Il verbo con cui la frase comincia, se e' un imperativo noto.

    Da consultare **solo** quando `parse()` ha gia' restituito `None`: qui non
    si decide niente, si etichetta una riga di diario.
    """
    if not isinstance(text, str):
        return None
    t = " ".join(text.strip().lower().split())
    m = _QUASI.match(t)
    return m.group("v") if m else None
