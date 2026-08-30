"""Chi l'ha detto — l'attribuzione al confine della memoria durabile.

## Perche' esiste

Il consolidamento notturno riassume gli scambi con un prompt che dice «solo
cio' che vale la pena ricordare», e **non distingue chi ha detto una cosa**.
Gli scambi entrano appiattiti — `- utente -> jarvis` — e ne esce un testo solo
in cui una preferenza che il Signore ha dichiarato e una che JARVIS ha proposto
sono la stessa riga.

La misura di riferimento (PASB, arXiv 2607.10526): la contaminazione a valle
passa dal **45 % al 71,9 %** quando un'affermazione attraversa il confine della
memoria durabile, su tutti e dodici i modelli testati; il 51,4 % degli episodi
promuove lo status dell'affermazione e il 33,1 % **cancella l'attribuzione**.

Tradotto: fra sei mesi JARVIS Le da' ragione su tutto e nessuno se ne accorge,
perche' Le da' ragione su tutto.

## La regola, e dove morde davvero

**Solo `dichiarato` puo' diventare un fatto fissato.**

⚠️ Misurato il 30 agosto: quella regola **non morde sul consolidamento**.
`Consolidatore.esegui()` scrive solo in `topics/` e non tocca mai
`_fatti-fissati.md`. L'unico che ci scrive e' `MemoryStore.fissa()`, e il suo
unico chiamante e' il tool `pin_fact` — che T1 puo' invocare. **E' li' il
confine**, ed e' esattamente il passaggio che PASB descrive.

## Come si deriva la classe, e perche' NON la decide l'LLM

`PROTOCOLLO-DI-LAVORO` §6: l'LLM non e' autorita' per «se un'informazione in
memoria e' vera». Quindi la classe non si chiede a lui.

**Nel consolidamento** viene dalla **costruzione**: si riassume due volte, una
sul corpus di cio' che ha detto il Signore e una su cio' che ha detto JARVIS.
La classe e' *quale corpus il modello ha visto*, non cio' che il modello
risponde — la stessa idea della `fonte` indipendente di ADR-012. Il terzo
corpus, le azioni, non passa da nessun modello: e' un elenco di tool che sono
girati davvero.

**In `pin_fact`** viene da un confronto lessicale con le parole vere del
Signore in quella sessione. ⚠️ **E' debole, e va detto.** La soglia qui sotto e'
**scelta, non misurata**.

La ragione per cui una soglia debole basta e' l'**asimmetria**, e sta tutta qui:

    classe dedotta      conseguenza
    proposto/osservato  `fissa()` RIFIUTA. Costa un fastidio: si apre il file
                        a mano, che e' la via che §5.5 gia' benedice
    dichiarato          `fissa()` accetta — e resta comunque la conferma
                        umana dell'invariante 3, che adesso MOSTRA la prova

Cioe': la deduzione puo' solo **negare** da sola. Per concedere serve ancora un
umano, e a quell'umano si fa vedere **la frase esatta** da cui la deduzione
viene. Se la prova non regge, si vede che non regge. Il sistema non decide:
dichiara.
"""

from __future__ import annotations

import re
from enum import StrEnum

#: Quanta parte delle parole di contenuto del fatto deve comparire nelle parole
#: vere del Signore. ⚠️ **Scelta, non misurata**: non esiste un corpus di fatti
#: fissati su cui tararla — ce ne sono meno di dieci su questa macchina. Vale
#: quanto vale perche' un errore in eccesso lo intercetta la conferma umana, e
#: un errore in difetto costa l'apertura di un file.
SOGLIA = 0.6

#: Parole che non distinguono niente. Elenco corto e volutamente incompleto: un
#: elenco lungo comincia a decidere, e qui si vuole solo togliere il rumore.
VUOTE = frozenset("""
il lo la i gli le un uno una di a da in con su per tra fra e o ma se che chi
cui non piu meno molto poco come dove quando perche mi ti si ci vi ne del
della dei delle dal dalla al alla nel nella sul sulla e' ho hai ha abbiamo
avete hanno sono sei siamo siete essere avere fare
""".split())


class Attribuzione(StrEnum):
    """Da dove viene un'affermazione che sta per durare.

    **Tre valori, e ognuno ha un produttore** — la stessa regola applicata a
    `Origine` (ADR-011) e a `Verdetto` (ADR-012). Un valore senza produttore
    e' un test rosso, non un posto tenuto caldo.
    """

    #: L'ha detto il Signore. Nel consolidamento: il riassunto del corpus
    #: `utente`. In `pin_fact`: le sue parole contengono il fatto.
    DICHIARATO = "dichiarato"
    #: L'ha proposto JARVIS e nessuno ha obiettato. Nel consolidamento: il
    #: riassunto del corpus `jarvis`. **Il silenzio non e' un assenso**, ed e'
    #: precisamente per questo che la classe esiste separata.
    PROPOSTO_E_ACCETTATO = "proposto-e-accettato"
    #: Viene da un tool, da una ronda, dal sistema. Nel consolidamento e'
    #: l'elenco delle azioni: **non passa da nessun modello**, quindi e' la
    #: sezione piu' affidabile delle tre pur essendo la meno interessante.
    OSSERVATO = "osservato"


def parole(testo: str) -> set[str]:
    """Le parole di contenuto, minuscole e senza punteggiatura."""
    grezze = re.findall(r"\w+", (testo or "").lower())
    return {p for p in grezze if len(p) >= 3 and p not in VUOTE}


def _sovrapposizione(fatto: set[str], corpus: str) -> float:
    if not fatto:
        return 0.0
    return len(fatto & parole(corpus)) / len(fatto)


def classifica(fatto: str, turni: list[dict]) -> tuple[Attribuzione, str]:
    """La classe di un fatto, e **la prova che la sostiene**.

    La prova non e' decorazione: e' cio' che il piano di conferma mostra
    all'umano dell'invariante 3, ed e' l'unica difesa contro una soglia
    lessicale che sbaglia. Se la prova non regge, si vede che non regge.

    Si guarda il Signore **per primo**: nel dubbio, un fatto che compare in
    entrambi i corpora e' suo — l'ha detto lui, e JARVIS l'ha ripetuto.
    Attribuirlo a JARVIS perche' l'ha ripetuto per ultimo sarebbe la
    cancellazione dell'attribuzione che PASB misura al 33,1 %.
    """
    cercate = parole(fatto)
    for chi, classe in (("utente", Attribuzione.DICHIARATO),
                        ("jarvis", Attribuzione.PROPOSTO_E_ACCETTATO)):
        migliore, quota = "", 0.0
        for t in turni:
            q = _sovrapposizione(cercate, t.get(chi) or "")
            if q > quota:
                migliore, quota = (t.get(chi) or ""), q
        if quota >= SOGLIA:
            return classe, f"«{migliore.strip()}» ({quota:.0%} delle parole)"

    # Nessuno dei due lo ha detto in questa sessione. Non e' «di nessuno»: e'
    # arrivato da un tool, da una ronda, o da una sessione che non stiamo
    # guardando — e in tutti e tre i casi non e' una dichiarazione del Signore.
    return Attribuzione.OSSERVATO, (
        "nessun turno di questa sessione contiene queste parole, ne' dette da "
        "Lei ne' da JARVIS")


def intestazione(a: Attribuzione) -> str:
    """L'intestazione di una sezione dentro un topic consolidato.

    ⚠️ **Qui c'era anche un `sezioni()` che rileggeva le tre sezioni, e non
    aveva un chiamante.** L'ha trovato `scripts/orfani.py` un minuto dopo che
    l'avevo scritto — «nessun riferimento, in nessun posto» — ed e' la firma
    esatta della famiglia di §5.29: un pezzo scritto, provato e mai congiunto.

    Non serve, e la ragione e' che le sezioni sono **markdown in un file**: una
    persona che apre il topic le legge, e T1 le vede inline quando `recall` gli
    restituisce il contenuto. Un lettore programmatico servira' il giorno in cui
    qualcuno vorra' MISURARE la contaminazione — la fetta 4, `eval_memoria` — e
    quel giorno si scrive, con il suo chiamante accanto.
    """
    return f"## {a.value}"
