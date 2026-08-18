"""Collector RSS e Atom — SPEC §15, «la base: gratis, illimitato».

Nessuna dipendenza nuova: `xml.etree` della libreria standard basta per
entrambi i formati. `feedparser` non e' in §4 e non lo aggiungo.

## Un feed e' un documento ostile potenziale

Non e' paranoia: e' la premessa di §15 — «un titolo e' testo controllato da
terzi». E prima ancora del titolo, e' **XML** scritto da terzi.

Due difese, entrambe di poche righe:

  **DOCTYPE rifiutato.** L'espansione delle entita' e' il modo classico di far
  esplodere un parser XML — un documento di due kilobyte che ne diventa
  qualche gigabyte in memoria. `defusedxml` sarebbe la risposta canonica ma e'
  un'altra dipendenza; rifiutare i documenti che dichiarano un DOCTYPE chiude
  il caso pratico, perche' senza DTD non ci sono entita' da espandere.

  **Dimensione massima.** Si legge fino a un tetto e non «tutto quello che
  arriva»: una risposta senza fine riempirebbe la memoria prima che qualcuno
  se ne accorga.

## User-Agent, e perche' il silenzio mente

Misurato su questa macchina: **Il Post risponde 403** al `Python-urllib`
predefinito, e continua a rifiutare anche con un User-Agent onesto — sta
dietro un filtro. **Reuters risponde 404**: l'URL che §15 cita non esiste piu'.
ANSA e BBC rispondono.

Un collector che restituisse una lista vuota in quei casi direbbe «non ci sono
notizie» invece di «questa fonte non risponde». La prima e' una giornata
tranquilla, la seconda e' un guasto: `Esito.fonti_in_errore` le tiene separate.
"""

from __future__ import annotations

import asyncio
import email.utils
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

import structlog

from core.llm.untrusted import Untrusted
from core.news.collectors.base import Esito, Item, rilevanza_per_parole

log = structlog.get_logger(__name__)

#: Un User-Agent che dice chi e'. Alcune testate rifiutano quello predefinito
#: di urllib, ed e' giusto: un lettore di feed si presenta.
USER_AGENT = "JARVIS-OS/1.0 (lettore di feed personale)"
TIMEOUT_S = 8.0
#: Un feed onesto sta sotto il megabyte. Oltre, non e' un feed.
MAX_BYTE = 4_000_000
MAX_ITEM = 40

#: Le fonti di §15 che rispondono davvero, verificate il 18 agosto 2026.
#: Il Post (403) e Reuters (404) sono in `FONTI_NOTE_ROTTE` e non qui: un
#: elenco predefinito che contiene sorgenti morte fa sembrare rotto il
#: collector invece della sorgente.
FONTI = {
    "ANSA": "https://www.ansa.it/sito/ansait_rss.xml",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
}
FONTI_NOTE_ROTTE = {
    "Il Post": "403 — dietro un filtro, anche con User-Agent dichiarato",
    "Reuters": "404 — l'URL di §15 non esiste piu'",
}

_ATOM = "{http://www.w3.org/2005/Atom}"


class DocumentoSospetto(Exception):
    """Il documento dichiara cose che un feed non ha motivo di dichiarare."""


def _testo(nodo: ET.Element | None) -> str:
    if nodo is None:
        return ""
    return "".join(nodo.itertext()).strip()


def _quando(grezzo: str) -> float:
    """RFC 822 (RSS) oppure ISO 8601 (Atom). Zero se non si capisce.

    Zero e non `time.time()`: una data inventata farebbe sembrare freschissima
    una notizia di tre giorni fa, ed e' il tipo di bugia che §11.9 vieta.
    """
    grezzo = grezzo.strip()
    if not grezzo:
        return 0.0
    try:
        return email.utils.parsedate_to_datetime(grezzo).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(grezzo.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def analizza(xml: str, fonte: str) -> list[Item]:
    """Da XML a `Item`. Solleva `DocumentoSospetto` su un DOCTYPE."""
    inizio = xml.lstrip()[:2000].lower()
    if "<!doctype" in inizio:
        raise DocumentoSospetto(
            f"{fonte}: il documento dichiara un DOCTYPE. Un feed non ne ha "
            "bisogno, e le entita' XML sono il modo classico di far esplodere "
            "un parser."
        )

    radice = ET.fromstring(xml)
    fuori: list[Item] = []

    # RSS: <rss><channel><item>. Atom: <feed><entry>.
    voci = radice.findall(".//item") or radice.findall(f".//{_ATOM}entry")
    for v in voci[:MAX_ITEM]:
        titolo = _testo(v.find("title")) or _testo(v.find(f"{_ATOM}title"))
        corpo = (
            _testo(v.find("description"))
            or _testo(v.find(f"{_ATOM}summary"))
            or _testo(v.find(f"{_ATOM}content"))
        )
        link = _testo(v.find("link"))
        if not link:
            a = v.find(f"{_ATOM}link")
            link = a.get("href", "") if a is not None else ""
        data = (
            _testo(v.find("pubDate"))
            or _testo(v.find(f"{_ATOM}updated"))
            or _testo(v.find(f"{_ATOM}published"))
        )
        if not titolo or not link:
            continue

        fuori.append(Item(
            fonte=fonte,
            url=link,
            # ⚠️ Qui, e in nessun altro posto, il testo di terzi diventa
            # `Untrusted`. Da questa riga in poi non puo' finire in un
            # contesto con tool nemmeno per sbaglio.
            testo=Untrusted.da(f"news:{fonte}", f"{titolo}\n{corpo}"),
            pubblicato=_quando(data),
        ))
    return fuori


def _scarica(url: str) -> str:
    richiesta = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(richiesta, timeout=TIMEOUT_S) as r:
        grezzo = r.read(MAX_BYTE)
    return grezzo.decode("utf-8", "replace")


class RssCollector:
    """Implementa il `Protocol` di §15."""

    name = "rss"

    def __init__(self, fonti: dict[str, str] | None = None) -> None:
        self._fonti = dict(fonti if fonti is not None else FONTI)

    def disponibile(self) -> tuple[bool, str]:
        """RSS non ha chiavi: e' disponibile se ha almeno una fonte."""
        if not self._fonti:
            return False, "nessuna fonte RSS configurata"
        return True, f"{len(self._fonti)} fonti"

    async def poll(self, topics: list[str]) -> Esito:
        esito = Esito(collector=self.name)
        for fonte, url in self._fonti.items():
            try:
                xml = await asyncio.to_thread(_scarica, url)
                item = analizza(xml, fonte)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
                # La fonte non risponde: e' un GUASTO, non una giornata
                # tranquilla. Va annunciato (§16).
                motivo = f"{fonte}: {type(exc).__name__} {getattr(exc, 'code', '')}".strip()
                log.warning("feed_non_raggiungibile", fonte=fonte, errore=type(exc).__name__)
                esito.fonti_in_errore.append(motivo)
                continue
            except (ET.ParseError, DocumentoSospetto) as exc:
                motivo = f"{fonte}: {type(exc).__name__}"
                log.warning("feed_illeggibile", fonte=fonte, errore=str(exc)[:120])
                esito.fonti_in_errore.append(motivo)
                continue

            for i in item:
                esito.item.append(i)

        if esito.fonti_in_errore and not esito.item:
            # Tutte giu': non e' «nessuna notizia», e' «nessuna fonte».
            esito.errore = "nessuna fonte raggiungibile: " + " · ".join(esito.fonti_in_errore)
        log.info("feed_letti", fonti=len(self._fonti), item=len(esito.item),
                 in_errore=len(esito.fonti_in_errore))
        return esito

    def relevance(self, item: Item, topics: list[str]) -> float:
        return rilevanza_per_parole(item, topics)
