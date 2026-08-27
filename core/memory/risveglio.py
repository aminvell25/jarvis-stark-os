"""Che cosa JARVIS ha fatto mentre non c'era nessuno.

`initiatives/` esiste dalla Fase 4 e la sua docstring dice «visibile al
risveglio». **Non lo era**: `registra_iniziativa` scriveva, e nessuno leggeva.
Il file il cui unico scopo e' essere letto al risveglio non aveva un lettore, e
la cartella e' rimasta a zero righe fino al 27 agosto.

Questo modulo e' il lettore, e la frase che ne esce.

## ⚠️ Il resoconto NON passa da un modello

E' composto dai dati, con una tabella di frasi. Non e' un risparmio: e' una
proprieta'. Cio' che JARVIS dice di **aver fatto** non deve poter essere
inventato — un modello che riassume un registro puo' sbagliare un numero o
aggiungere una riga che non c'era, e sarebbe la peggiore bugia che questo
sistema possa dire. Il riassunto di una CONVERSAZIONE lo fa un modello (§5.5);
il rendiconto delle proprie azioni no.
"""

from __future__ import annotations

import time

from core.memory.consolidate import PERIODO_S
from core.memory.store import MemoryStore

SEGNAPOSTO = "_ultimo-resoconto"

#: Le frasi, per tipo di iniziativa. **Allowlist, non formattatore generico**:
#: un tipo nuovo senza frase qui si vede — `tests/test_il_resoconto_al_risveglio.py`
#: confronta questa tabella con i tipi che il core registra davvero, e diventa
#: rosso invece di lasciare a JARVIS una frase che non sa dire.
FRASI = {
    "consolidamento": lambda v: (
        "ho messo in ordine gli appunti di "
        + (f"{len(v)} sessione" if len(v) == 1 else f"{len(v)} sessioni")
    ),
}


def ultimo(store: MemoryStore) -> float:
    p = store.radice / f"{SEGNAPOSTO}.txt"
    try:
        return float(p.read_text().strip())
    except (OSError, ValueError):
        return 0.0


def segna(store: MemoryStore) -> None:
    (store.radice / f"{SEGNAPOSTO}.txt").write_text(str(time.time()))


def e_ora_di_dirlo(da: float, adesso: float | None = None) -> bool:
    """Se «niente da riferire» va detto lo stesso.

    Il silenzio non e' un resoconto: un JARVIS che tace e uno rotto si
    somigliano troppo. Ma dirlo a ogni riconnessione della scrivania —
    che capita a ogni riavvio del core, ventisette volte in tre giorni —
    lo trasformerebbe in rumore, e il rumore si ignora.

    **Il confine non e' scelto**: e' `PERIODO_S`, lo stesso di §5.5, e per la
    stessa ragione. L'unica cosa che JARVIS fa da solo ha periodo giornaliero,
    quindi un giorno senza iniziative nuove e' il piu' piccolo intervallo in cui
    «niente» sia davvero un'informazione.
    """
    ora = time.time() if adesso is None else adesso
    return (ora - da) > PERIODO_S


def componi(fatte: list[dict]) -> str:
    """La frase, dai dati. Prosa: §5.7 vieta elenchi e markdown a voce."""
    if not fatte:
        return "Niente da riferire, Signore."

    per_tipo: dict[str, list[dict]] = {}
    for f in fatte:
        per_tipo.setdefault(str(f.get("tipo") or "ignoto"), []).append(f)

    pezzi = []
    for tipo, righe in per_tipo.items():
        frase = FRASI.get(tipo)
        # Il ripiego dice il NUMERO e non finge di spiegare: meglio «due cose
        # che non so ancora raccontare» di una frase inventata su un tipo che
        # nessuno ha descritto.
        n = len(righe)
        pezzi.append(frase(righe) if frase else
                     f"{n} cosa che non so ancora raccontare" if n == 1 else
                     f"{n} cose che non so ancora raccontare")
    return f"Mentre non c'era, Signore: {_elenco(pezzi)}."


def _elenco(pezzi: list[str]) -> str:
    if len(pezzi) == 1:
        return pezzi[0]
    return ", ".join(pezzi[:-1]) + " e " + pezzi[-1]
