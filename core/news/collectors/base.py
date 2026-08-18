"""L'interfaccia dei collector — SPEC §15.

> «Collector pluggabili. Non un modulo news monolitico: un file per sorgente in
> `core/news/collectors/`, ognuno con la stessa interfaccia. Aggiungere una
> sorgente = aggiungere un file.»

Il motore proattivo non sa nulla delle sorgenti: itera i collector registrati.

## Il testo di un Item non e' una stringa

§15, ultima riga: «un titolo e' testo controllato da terzi. Stesse regole di
§12 — contesti con zero tool, marcatura, mai verso T2 con tool attivi».

Quindi `Item.testo` e' un `Untrusted` (Fase 6), non `str`. Non e' una
precauzione in piu': e' la STESSA barriera della `<webview>`, riusata. Se le
news avessero avuto bisogno di un meccanismo nuovo, vorrebbe dire che quello di
Fase 6 era sbagliato.

Il titolo resta leggibile — serve alla card e alla frase vocale — ma passa
sempre da `Untrusted.grezzo()`, che ha un nome che si nota in una revisione.

## Zero item e fonte rotta non sono la stessa cosa

`Esito` le tiene separate. Un collector che restituisse una lista vuota quando
la sorgente lo respinge racconterebbe una bugia — «non ci sono notizie» invece
di «questa fonte non risponde» — e la prima e' normale mentre la seconda va
riparata. Misurato: meta' dei feed di §15 rifiuta il User-Agent predefinito o
ha cambiato URL.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol

from core.llm.untrusted import Untrusted


@dataclass(frozen=True)
class Item:
    """Una notizia. Il testo viene da fuori, e il tipo lo dice."""

    #: Da dove viene. Finisce nella card e nel marcatore `<untrusted_source>`.
    fonte: str
    #: L'URL originale, gia' validato dal collector.
    url: str
    #: Titolo e corpo, entrambi non fidati.
    testo: Untrusted
    #: Epoch secondi. Zero se la sorgente non lo dichiara — e allora si vede.
    pubblicato: float = 0.0
    #: Riempito dal gate, non dal collector.
    rilevanza: float = 0.0

    @property
    def id(self) -> str:
        """Identita' stabile, per non riproporre due volte la stessa notizia.

        Sull'URL e non sul titolo: le testate riscrivono i titoli nel corso
        della giornata, e un identificativo che cambia con essi farebbe
        ricomparire la stessa storia ogni ora.
        """
        return hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:16]

    def titolo(self) -> str:
        """Il titolo in chiaro, per la card e per la frase vocale.

        `grezzo()` ha un nome che si nota: chi lo scrive sta prendendo del
        testo non fidato e lo sta mostrando a qualcuno. Va bene mostrarlo —
        non va bene darlo a un LLM con dei tool.
        """
        return self.testo.grezzo().split("\n", 1)[0].strip()


@dataclass
class Esito:
    """Cosa ha prodotto un giro di `poll()`."""

    collector: str
    item: list[Item] = field(default_factory=list)
    #: `None` = tutto bene. Valorizzato = la fonte non ha risposto, e la cosa
    #: va annunciata (§16: «nessuna soglia agisce senza annunciarlo»).
    errore: str | None = None
    #: Per l'annuncio: quali sorgenti dentro il collector hanno fallito.
    fonti_in_errore: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.errore is None


class Collector(Protocol):
    """§15 verbatim, piu' `disponibile()`.

    `disponibile()` non e' un'aggiunta di comodo: due delle tre sorgenti di
    §15 vogliono una chiave API, e l'assenza di una chiave e' uno stato
    NORMALE da annunciare — non un errore da scoprire al primo giro. E' la
    stessa forma di `TesseractOcr.disponibile()` (Fase 6) e di
    `TrackerMediaPipe.disponibile()` (Fase 7).
    """

    name: str

    def disponibile(self) -> tuple[bool, str]: ...

    async def poll(self, topics: list[str]) -> Esito: ...

    def relevance(self, item: Item, topics: list[str]) -> float: ...


#: Quanti argomenti bastano perche' una notizia sia pienamente rilevante.
COLPI_PER_PIENO = 3


def rilevanza_per_parole(item: Item, topics: list[str]) -> float:
    """La rilevanza di base, condivisa dai collector che non ne hanno una loro.

    E' grossolana di proposito: il filtro fine lo fa il gate, e un collector
    che pretendesse di capire l'articolo dovrebbe darlo a un LLM — cioe' dare
    testo non fidato a un modello, che e' esattamente cio' che §15 vieta.

    ⚠️ **Non si divide per il numero di argomenti**, che era la prima versione.
    Dividere significa che piu' interessi si hanno, meno ogni notizia conta:
    con otto argomenti una notizia che ne colpisce uno valeva 0,125 e non
    passava la soglia. Ma una notizia che tocca UNA cosa che mi interessa e'
    rilevante — non lo e' un ottavo. Si satura invece a tre colpi.
    """
    if not topics:
        return 0.0
    testo = item.testo.grezzo().lower()
    colpiti = sum(1 for t in topics if t.lower().strip() and t.lower() in testo)
    return min(1.0, colpiti / COLPI_PER_PIENO)


def scarta_doppioni(item: list[Item], gia_visti: set[str]) -> list[Item]:
    """Toglie cio' che si e' gia' proposto. Aggiorna `gia_visti` sul posto."""
    fuori: list[Item] = []
    for i in item:
        if i.id in gia_visti:
            continue
        gia_visti.add(i.id)
        fuori.append(i)
    return fuori


def come_dizionario(i: Item) -> dict[str, Any]:
    """Per il socket e per il pannello.

    Il testo esce in chiaro perche' va MOSTRATO, e la card dice sempre da dove
    viene: e' l'equivalente del rettangolo di ARGUS in §12 — chi guarda deve
    sapere che quelle parole non sono di JARVIS.
    """
    return {
        "id": i.id,
        "fonte": i.fonte,
        "url": i.url,
        "titolo": i.titolo(),
        "pubblicato": i.pubblicato,
        "rilevanza": round(i.rilevanza, 3),
        "origine_non_fidata": i.testo.origine,
    }
