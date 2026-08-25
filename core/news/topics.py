"""Estrattore di argomenti — SPEC §15.

> conversazione → **[estrattore argomenti]** (haiku, batch = periodo dei giri,
> effort low)   ⚠️ «batch 60s» emendato nella rev 5.25: vedi in fondo
> → [watcher feed] → [gate rilevanza] → [budget]

Legge la CONVERSAZIONE — testo Suo — e produce le parole con cui il watcher
filtrera' i feed.

## ⚠️ Perche' rifiuta il contenuto non fidato

Se un giorno qualcuno desse in pasto all'estrattore anche il testo delle news
«per migliorare gli argomenti», si chiuderebbe un anello:

    articolo ostile → diventa un argomento → decide quali altri articoli
    superano il gate → altri articoli ostili → …

E' l'avvelenamento del ciclo di retroazione. Non somiglia a un attacco mentre
lo si scrive — somiglia a un miglioramento — ed e' esattamente per questo che
va reso impossibile invece che sconsigliato.

`estrai()` **solleva** davanti a un `Untrusted`.

## La regola locale: la POSIZIONE, non la lunghezza

⚠️ La prima versione teneva una parola se tornava due volte **oppure** se era
lunga almeno otto lettere. Su una frase sola ogni conteggio vale 1, quindi
l'`or` collassava a «e' lunga», e la lunghezza in italiano non dice niente
sull'essere un argomento: `clima` (5) e `governo` (7) cadevano, `pensando` (8)
passava. Misurato su `tests/eval_argomenti.py`: **precisione 0,171**.

La regola di adesso tiene una parola se e' **introdotta da un articolo o da
una preposizione** — «il bagno», «di musica», «un motore» — e la scarta
altrimenti. Non e' analisi grammaticale: e' una posizione, e `INTRODUCONO` e'
una allowlist di parole-funzione come `FERME` e' una lista di parole vuote.
Nessuna denylist di desinenze verbali: sarebbe un elenco di sconfitte gia'
subite, e l'invariante 2 dice il contrario.

Misurato sullo stesso banco: **precisione 0,421, richiamo 0,800**. Il perche'
di ogni cifra, e le due ipotesi scartate perche' misuravano peggio, stanno in
`docs/acceptance/ARGOMENTI-IL-BANCO.md`.

**E quando non trova niente, non restituisce niente.** Il ripiego «se il filtro
non tiene nessuno, tienili tutti» costava 0,155 di precisione; e una lista
vuota e' innocua, perche' `MotoreNews.un_giro()` senza argomenti non guarda
affatto.

## Perche' haiku e' collegato

La barra era **precisione > 2/3**, dichiarata prima di misurare e dedotta dal
budget: con 3 interruzioni all'ora, una precisione `P` ne lascia `3(1-P)` fuori
tema, e perche' ne resti meno di una serve `P > 0,67`. La regola locale
riparata arriva a **0,421**, e i suoi errori residui sono tutti sintagmi
regolari — «la luce», «la fantasia», «le orecchie» — che nessuna regola di
forma distingue da «il bagno». La differenza e' semantica.

Percio' l'estrattore vero e' `EstrattoreLLM` con un modello, e `estrai_locale`
resta il ripiego ANNUNCIATO che gira quando la quota e' finita o la rete non
c'e'.

## Il batch, dedotto invece che copiato

§15 dice «batch 60s», ma quel numero e' anteriore al Governor: 60 s vorrebbe
dire fino a 60 spawn all'ora contro un tetto di 15 (`MAX_PER_WINDOW`), quindi
tre estrazioni su quattro sarebbero rifiutate e cadrebbero sul ripiego. Non
sarebbe «haiku con un ripiego»: sarebbe il locale con qualche haiku.

Il batch **non ha ragione di essere piu' corto del periodo dei giri** — gli
argomenti si aggiornerebbero piu' spesso di quanto qualcuno li legga — **ne'
piu' lungo** — un giro girerebbe su una conversazione gia' finita. Quindi
batch = periodo dei giri, che `core/news/motore.py` deriva gia' dal tetto di
§15: con 3/ora fa 600 s, cioe' 6 estrazioni l'ora contro un tetto di 15.
Nessun numero nuovo. Lo passa `MotoreNews`, e si vede in una riga sola.
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from core.llm.untrusted import ContenutoNonFidato, Untrusted

log = structlog.get_logger(__name__)

#: §15: «argomenti scaduti dopo 30 minuti».
SCADENZA_S = 30 * 60
#: Il valore di §15. Resta come predefinito per chi costruisce l'estrattore da
#: solo; chi lo costruisce dentro il motore riceve il periodo dedotto.
BATCH_S = 60
MAX_ARGOMENTI = 8
MIN_LUNGHEZZA = 4

#: §15 nomina il modello. Non e' `llm.t2_model` — quello e' per il lavoro
#: lungo, questo e' una riga di testo ogni dieci minuti.
MODELLO_ARGOMENTI = "haiku"

#: ⚠️ L'apostrofo CHIUDE il token invece di farne parte. Con `'` dentro la
#: classe, `un'email` era **una** parola di otto lettere — abbastanza lunga da
#: passare la vecchia soglia — e l'argomento vero, `email`, non esisteva. Allo
#: stesso modo `perche'` sfuggiva a `FERME`, che contiene `perche` e `perché`
#: ma non la forma con l'apostrofo.
TOKEN = re.compile(r"[a-zàèéìòóù]+")

#: Parole che compaiono in ogni conversazione e non distinguono niente. Un
#: argomento «cosa» farebbe passare qualunque notizia.
FERME = frozenset("""
alla alle allo agli anche ancora avere bene come cosa dalla dalle dallo dagli
degli deve della delle dello dentro dopo dove durante essere fare fatto fatta
fosse grazie insieme intanto invece letto loro meno mentre molto niente nella
nelle nello negli oggi ogni oltre pero però perche perché piu più poco poi
prima proprio quale quando quanto quella quelle quello questa queste questo
qualcosa sempre senza solo sono stata stato stesso subito tanto tutta tutte
tutti tutto ultima ultimo vedere verso volta volte ciao jarvis
interessa interessante piace piaciuto sentito visto detto parlato
""".split())

#: Le parole-funzione che in italiano aprono un sintagma nominale. Chi le
#: segue e' quasi sempre la cosa di cui si parla; chi non le segue e' quasi
#: sempre un verbo o un modo di dire.
#:
#: Le forme elise stanno **senza apostrofo** (`l`, `un`, `dell`, `nell`) perche'
#: `TOKEN` taglia li': dopo `l'alluvione` il flusso e' `l`, `alluvione`.
INTRODUCONO = frozenset("""
il lo la i gli le l un uno una
di del dello della dei degli delle d dell
a al allo alla ai agli alle all
da dal dallo dalla dai dagli dalle dall
in nel nello nella nei negli nelle nell
su sul sullo sulla sui sugli sulle sull
con col coi per tra fra
questo questa questi queste quest quel quello quella quei quegli quelle quell
mio mia miei mie tuo tua tuoi tue suo sua suoi sue nostro nostra nostri nostre
""".split())


@dataclass(frozen=True)
class Argomento:
    parola: str
    peso: float = 1.0
    visto: float = field(default_factory=time.time)

    def scaduto(self, adesso: float | None = None, scadenza: float = SCADENZA_S) -> bool:
        return (adesso or time.time()) - self.visto > scadenza


def _controlla_fidato(testo: Any) -> str:
    """La barriera di R60. Una riga, e chiude l'anello di retroazione."""
    if isinstance(testo, Untrusted):
        raise ContenutoNonFidato(
            f"l'estrattore di argomenti ha ricevuto contenuto non fidato da "
            f"{testo.origine}. §15: gli argomenti vengono dalla CONVERSAZIONE. "
            "Se li estraesse dalle news, un articolo ostile potrebbe scegliere "
            "quali altri articoli La raggiungono."
        )
    return str(testo)


def estrai_locale(conversazione: str, massimo: int = MAX_ARGOMENTI,
                  adesso: float | None = None) -> list[Argomento]:
    """Il ripiego senza LLM: le parole introdotte da un articolo.

    Gira sempre — senza rete, senza quota, senza attesa — ed e' cio' che
    `EstrattoreLLM` usa quando il modello non risponde. E' anche il modo in cui
    i test misurano il resto della catena senza dipendere da un modello.

    La lista puo' essere **vuota**, ed e' un esito, non un guasto: senza
    argomenti `MotoreNews.un_giro()` non guarda i feed, che e' esattamente il
    comportamento giusto quando non si e' parlato di niente.
    """
    parole = TOKEN.findall(_controlla_fidato(conversazione).lower())
    conteggi: dict[str, int] = {}
    # `zip` con la lista sfasata di uno: `prima` e' la parola che precede, e
    # `""` per la prima del testo, che quindi non e' introdotta da niente.
    for prima, p in zip([""] + parole, parole):
        if prima not in INTRODUCONO or len(p) < MIN_LUNGHEZZA or p in FERME:
            continue
        conteggi[p] = conteggi.get(p, 0) + 1

    # La frequenza resta l'ordinamento: su una conversazione lunga cio' di cui
    # si e' parlato di piu' viene prima. Su una frase sola sono tutti a 1 e
    # decide l'ordine alfabetico, che e' arbitrario ma stabile.
    ordinate = sorted(conteggi.items(), key=lambda kv: (-kv[1], kv[0]))[:massimo]
    massimo_conteggio = ordinate[0][1] if ordinate else 1
    # `adesso` e non `time.time()` dentro il dataclass: la scadenza dei trenta
    # minuti di §15 e il batch devono leggere lo STESSO orologio, o l'uno misura
    # il tempo dei test e l'altro quello vero. L'ha trovato il test della
    # scadenza.
    ora = adesso if adesso is not None else time.time()
    return [Argomento(parola=p, peso=n / massimo_conteggio, visto=ora) for p, n in ordinate]


#: Il compito che va al modello. Chiede parole, non prosa, e dice esplicitamente
#: che «niente» e' una risposta ammessa — senza quella riga un modello educato
#: inventa un argomento pur di non lasciare vuota la risposta.
PROMPT = """Elenca gli ARGOMENTI di cui si parla qui sotto: le cose del mondo di \
cui si potrebbero leggere notizie.

Regole della risposta:
- una parola per argomento, in minuscolo, separate da virgola
- solo parole che compaiono nel testo, senza cambiarne la forma
- niente verbi, niente aggettivi di stato, niente modi di dire
- se non si parla di niente di preciso, rispondi con una riga vuota

TESTO:
{testo}"""


class EstrattoreLLM:
    """§15: haiku, batch dedotto, effort low.

    L'LLM arriva **per funzione** e non per import: cosi' i test lo misurano
    con un finto, e la radice di composizione gli passa lo spawn vero. Chi
    costruisce senza `chiedi` ottiene il ripiego locale, che e' quello che
    girava prima che qualcuno collegasse il modello.
    """

    def __init__(self, chiedi: Callable[[str], Awaitable[str]] | None = None,
                 batch_s: float = BATCH_S) -> None:
        self._chiedi = chiedi
        self._batch_s = batch_s
        self._ultimo = 0.0
        self._argomenti: list[Argomento] = []

    def argomenti_a(self, adesso: float | None = None) -> list[Argomento]:
        """Quelli non scaduti a un dato istante — §15, trenta minuti.

        L'istante e' un ARGOMENTO e non `time.time()` dentro il metodo: la
        prima versione lo leggeva da sola, e `aggiorna(adesso=X)` restituiva
        argomenti timbrati a X ma filtrati sull'orologio vero — due orologi
        nella stessa chiamata, e una lista sempre vuota nei test. Un solo
        orologio, e chi chiama decide quale.
        """
        return [a for a in self._argomenti if not a.scaduto(adesso)]

    @property
    def argomenti(self) -> list[Argomento]:
        return self.argomenti_a()

    def parole(self) -> list[str]:
        return [a.parola for a in self.argomenti]

    def _dalla_risposta(self, risposta: str, detto: str, ora: float) -> list[Argomento]:
        """La risposta del modello, filtrata con la stessa arma dell'invariante 2.

        ⚠️ **Solo parole che Lei ha davvero detto.** Non e' pignoleria di
        formato: senza questo vincolo il modello puo' proporre un argomento che
        nel testo non c'e' — per associazione, o perche' ha risposto in prosa —
        e quell'argomento andrebbe poi a scegliere quali notizie La raggiungono.
        Il vocabolario ammesso e' cio' che e' stato pronunciato: una allowlist,
        e per giunta una che si costruisce da sola.

        Ed e' anche cio' che rende innocua una risposta mal formata: «Non ci
        sono argomenti precisi» non contiene nessuna parola del testo, quindi
        non produce nessun argomento.
        """
        pronunciate = set(TOKEN.findall(detto.lower()))
        proposte = dict.fromkeys(TOKEN.findall(risposta.lower()))
        return [
            Argomento(parola=p, visto=ora)
            for p in proposte
            if len(p) >= MIN_LUNGHEZZA and p not in FERME and p in pronunciate
        ][:MAX_ARGOMENTI]

    async def aggiorna(self, conversazione: str, adesso: float | None = None) -> list[Argomento]:
        """Ricalcola, non piu' spesso di una volta per batch."""
        testo = _controlla_fidato(conversazione)
        ora = adesso if adesso is not None else time.time()
        if ora - self._ultimo < self._batch_s and self._argomenti:
            return self.argomenti_a(ora)
        self._ultimo = ora

        if self._chiedi is None:
            self._argomenti = estrai_locale(testo, adesso=ora)
            log.info("argomenti_estratti", modo="locale", quanti=len(self._argomenti))
            return self.argomenti_a(ora)

        try:
            risposta = await self._chiedi(PROMPT.format(testo=testo))
        except Exception as exc:
            # Ripiego ANNUNCIATO nei log (invariante 12): l'estrattore non deve
            # mai fermare la catena, ne' far finta di aver usato il modello.
            log.warning("estrattore_llm_fallito", errore=type(exc).__name__,
                        ripiego="estrai_locale")
            self._argomenti = estrai_locale(testo, adesso=ora)
            return self.argomenti_a(ora)

        self._argomenti = self._dalla_risposta(risposta, testo, ora)
        log.info("argomenti_estratti", modo="llm", quanti=len(self._argomenti))
        return self.argomenti_a(ora)
