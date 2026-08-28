"""Chi aziona il `Watcher` — §15, e la cadenza DEDOTTA dal tetto.

## Perche' questo file esiste

`Watcher.giro()` non aveva **un solo chiamante nel core**: solo un test e uno
script di fixture. Con `news.enabled = true` il `Watcher` si costruiva a ogni
avvio, lo snapshot diceva `giri_fatti: 0`, e nessun giro sui feed e' mai
avvenuto. Costruito e mai azionato, come i quattro tool di memoria di §13.

`Argomenti` era nello stesso stato, e il suo commento lo diceva gia':

> il giorno in cui la pipeline sara' composta bastera' passargliela.

## La cadenza, dedotta

⚠️ **§15 non dichiara ogni quanto si guardino i feed.** Dichiara una sola
frequenza: **3 interruzioni all'ora**, che e' il ritmo con cui JARVIS puo'
PARLARE, non quello con cui puo' GUARDARE. Il numero qui sotto non e' scritto
da nessuna parte, e non lo invento: lo derivo, e scrivo da che cosa.

**Il tetto superiore viene dagli argomenti.** Un argomento vive 30 minuti
(`news.topic_ttl_minutes`). Un giro piu' lento della vita di un argomento
vorrebbe dire che un argomento puo' nascere e scadere senza essere mai stato
guardato — la funzione non farebbe niente, in silenzio. Perche' ogni argomento
abbia almeno **due** occasioni: periodo <= TTL / 2.

**Il tetto inferiore viene dal budget.** Tre interruzioni all'ora fanno una
finestra di 1200 s l'una. Un giro esattamente lungo quanto la finestra da' un
solo candidato per finestra: se il gate lo scarta — poco rilevante, gia' visto,
Lei sta parlando — quella finestra e' persa fino al giro dopo. **Dimezzandola**
ce ne sono due:

    periodo = 3600 / (2 x tetto)     con tetto = 3  ->  600 s

**E un pavimento, che non viene dalla nostra aritmetica ma dall'educazione.**
Chi mettesse `max_interruptions_per_hour = 60` otterrebbe un giro ogni 30
secondi su server che non sono nostri. Sotto il minuto non si scende.

    periodo = min(max(3600 / (2 x tetto), 60), ttl / 2)

Il numero **cambia con l'impostazione**, ed e' la proprieta' che conta: non e'
una costante travestita da deduzione. Con 3/ora fa 600 s; con 6/ora, 300; con
1/ora sarebbe 1800 e il tetto degli argomenti lo riporta a 900.

## Lo stesso periodo e' anche il batch dell'estrattore

§15 dice «batch 60s» per l'estrattore di argomenti, ma quel numero e' anteriore
al Governor: 60 s vorrebbero dire fino a **60 spawn all'ora** contro un tetto
di **15** (`MAX_PER_WINDOW`), quindi tre estrazioni su quattro verrebbero
rifiutate e cadrebbero sul ripiego locale. Non sarebbe haiku con un ripiego:
sarebbe il locale con qualche haiku.

E il batch non ha ragione di essere piu' corto del periodo dei giri — gli
argomenti si aggiornerebbero piu' spesso di quanto qualcuno li legga — ne' piu'
lungo — un giro girerebbe sugli argomenti di una conversazione gia' finita.
Quindi **batch = periodo**, che con 3/ora fa 600 s, cioe' 6 estrazioni l'ora
dentro un tetto di 15. Nessun numero nuovo.

## Chi dice al gate se Lei sta parlando

Le regole 2 e 3 di §15 leggono un `Contesto`, e il `Contesto` e' un tri-stato
apposta: `None` non e' `False`, vuol dire **non lo so**, e non si interrompe.

Il campo `sta_parlando` non aveva un produttore. `docs/acceptance/FASE-08.md`
lo dichiarava fra i punti NON verificati — «oggi il core non sa se Lei sta
parlando, quindi in esercizio non interromperebbe mai» — e finche' resta cosi'
nessuna card puo' passare il gate in esercizio: il motore proattivo tace **per
costruzione**, e la cosa non si vede da nessuna parte.

Lo stato lo sa la pipeline vocale, e arriva qui **per funzione**, dalla radice
di composizione — non per attributo scritto da fuori, e non leggendo un campo
privato di un altro modulo. Una funzione ha tre modi di non rispondere: non
esserci, sollevare, tornare qualcosa che non e' un `bool`. Tutti e tre valgono
`None`, cioe' un divieto. Vedi `MotoreNews._parla_adesso`.

**Un produttore alla volta, non due.** Col lettore collegato e' lui a riempire
il campo, e vince su qualunque cosa ci fosse nel `Contesto` di partenza: se
vincesse il `Contesto`, tornerebbero a esserci due posti da guardare per sapere
chi ha deciso, che e' il difetto di prima in un punto nuovo. Senza lettore non
si tocca niente e resta cio' che la radice dichiara — per difetto `None`.

## E senza argomenti non si guarda affatto

`giro()` calcola la rilevanza **contro gli argomenti**. Senza, niente puo'
essere rilevante e niente puo' passare: un giro a lista vuota e' traffico su un
server di terzi in cambio di nulla. §15 vuole che le news seguano la
conversazione, e finche' non si e' parlato non c'e' conversazione da seguire.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import structlog

from core.news.conoscibilita import (
    NON_PRODOTTO, Lettura, Sguardo, guarda, mai_letto,
)
from core.news.feeds import Watcher
from core.news.gate import Contesto
from core.news.topics import EstrattoreLLM

log = structlog.get_logger(__name__)

#: Il pavimento dell'educazione. Vedi l'intestazione.
PERIODO_MINIMO_S = 60.0


def periodo_dei_giri(tetto_per_ora: int, ttl_minuti: int) -> float:
    """La cadenza, dai due numeri che §15 dichiara davvero.

    Solleva se i due numeri non hanno senso: un tetto a zero vorrebbe dire che
    JARVIS non puo' mai parlare, e allora guardare i feed non serve a niente —
    ed e' meglio dirlo che dividere per zero.
    """
    if tetto_per_ora <= 0:
        raise ValueError(
            f"max_interruptions_per_hour = {tetto_per_ora}: con un tetto a zero "
            "nessuna news puo' passare, e guardare i feed sarebbe traffico "
            "per niente. Spegni `news.enabled` invece."
        )
    if ttl_minuti <= 0:
        raise ValueError(f"topic_ttl_minutes = {ttl_minuti}: un argomento che "
                         "scade subito non arriva a nessun giro")
    dal_budget = 3600.0 / (2 * tetto_per_ora)
    dagli_argomenti = ttl_minuti * 60.0 / 2
    return min(max(dal_budget, PERIODO_MINIMO_S), dagli_argomenti)


class MotoreNews:
    """Tiene gli argomenti, aziona il `Watcher`, e conta i giri.

    Non decide niente su cosa passa: quello e' del `Gate`. Qui si decide solo
    **quando guardare**, e la risposta e' in `periodo_dei_giri`.
    """

    def __init__(self, watcher: Watcher, impostazioni, *,
                 contesto: Callable[[], Lettura] | None = None,
                 sta_parlando: Callable[[], bool | None] | None = None,
                 chiedi=None, orologio=time.time) -> None:
        self._watcher = watcher
        self._periodo = periodo_dei_giri(impostazioni.max_interruptions_per_hour,
                                         impostazioni.topic_ttl_minutes)
        #: Come si chiede «che cosa sta succedendo adesso». Arriva per funzione
        #: perche' lo sa la pipeline vocale, non le news.
        #: ⚠️ Torna una `Lettura`, non un `Contesto`: il valore di ogni campo
        #: e il PERCHE' del suo ignoto escono dalla stessa chiamata. Chiedere
        #: il perche' per una seconda strada sarebbe un secondo produttore.
        self._contesto: Callable[[], Lettura] = contesto or (lambda: Lettura())
        #: Come si chiede la SOLA cosa che la pipeline vocale sa davvero: se
        #: JARVIS ha voce in uscita adesso (§15, regola 2). Per funzione, per
        #: la stessa ragione di `contesto`: le news non devono sapere che cosa
        #: sia una `VoicePipeline`, ne' leggerne un campo privato.
        #:
        #: `None` qui vuol dire «nessuno l'ha collegata», e da li' in poi lo
        #: stato resta ignoto a ogni giro. Vedi `_parla_adesso`.
        self._sta_parlando = sta_parlando
        self._orologio = orologio
        #: ⚠️ **Il batch e' il periodo dei giri**, e non i 60 s scritti in §15.
        #: Vedi l'intestazione: 60 s vorrebbero dire fino a 60 spawn all'ora
        #: contro il tetto di 15 del Governor, quindi il modello verrebbe
        #: rifiutato tre volte su quattro. E un batch diverso dal periodo
        #: sarebbe comunque sbagliato in una delle due direzioni. Nessun numero
        #: nuovo: lo stesso, passato una volta sola.
        self.argomenti = EstrattoreLLM(chiedi, batch_s=self._periodo)
        self.giri = 0
        self.ultimo: float | None = None
        #: L'ultima lettura del contesto, per `conoscibilita()`. `None` finche'
        #: nessun giro ha guardato — e a quel punto l'unica cosa vera da dire
        #: e' `mai_letto`, non un valore riletto adesso.
        self._ultima: Lettura | None = None
        self._compito: asyncio.Task | None = None

    # ── gli argomenti vengono dalla conversazione (§15) ──────────────────────

    async def ascolta(self, detto: str) -> list[str]:
        """Una frase dell'utente diventa argomenti. Non solleva: siamo sul
        percorso della voce, e un'eccezione qui zittirebbe JARVIS."""
        if not detto or not detto.strip():
            return []
        try:
            await self.argomenti.aggiorna(detto)
        except Exception as exc:
            log.error("argomenti_non_estratti", errore=repr(exc))
            return []
        parole = self.argomenti.parole()
        log.info("argomenti_dalla_voce", quanti=len(parole), parole=sorted(parole))
        return parole

    # ── che cosa sta succedendo adesso (§15, regole 2 e 3) ───────────────────

    def _parla_adesso(self) -> Sguardo:
        """Se JARVIS sta parlando **adesso**, e se non si sa, perche'.

        Quattro esiti, e tutti e quattro tolgono il permesso di parlare tranne
        il primo — ma **non dicono la stessa cosa a chi guarda**:

        1. `noto` — il lettore ha risposto un `bool`;
        2. `non_prodotto` — nessuno l'ha collegato alla radice di composizione,
           ed e' lo stato in cui il core e' stato fino a ieri: il gate restera'
           chiuso per sempre, e va detto;
        3. `non_composto` — il lettore c'e' e risponde «non lo so»: la voce e'
           spenta. Configurazione, si risolve accendendola;
        4. `ha_sollevato` / `risposta_storta` — il lettore c'e' ed e' rotto.
           GUASTO, e si insegue.

        ⚠️ **La 3 e la 4 erano lo stesso `None`**, e a chi guardava lo snapshot
        una voce spenta e una pipeline rotta erano indistinguibili. Il gate le
        tratta ancora allo stesso modo, ed e' giusto; chi legge no.

        Non solleva mai: siamo dentro il giro dei feed, e un lettore rotto deve
        togliere il permesso di parlare, non fermare il motore.
        """
        if self._sta_parlando is None:
            return Sguardo(None, NON_PRODOTTO)
        return guarda(self._sta_parlando, campo="sta_parlando")

    def _contesto_adesso(self) -> Contesto:
        """Il contesto di questo giro, con `sta_parlando` letto **adesso**.

        **Col lettore collegato questo metodo e' l'unico produttore del
        campo**: quel che dice il lettore vince su qualunque cosa ci fosse
        nella `Lettura` di partenza. Fosse la `Lettura` a vincere, un valore
        ottimista dichiarato altrove aprirebbe il gate mentre la voce parla
        davvero.

        **Senza lettore non si tocca niente.** Il campo resta quello che la
        radice di composizione dichiara, e per difetto e' `non_prodotto` — cioe'
        il divieto, piu' la ragione. Azzerarlo d'ufficio non lo renderebbe piu'
        sicuro: toglierebbe alla radice il diritto di dichiarare cio' che sa, e
        aggiungerebbe un secondo produttore invece di toglierne uno.

        La lettura si tiene da parte per `conoscibilita()`: quel che si mostra
        e' cio' che il giro ha USATO, non un valore riletto dopo.
        """
        lettura = self._contesto()
        if self._sta_parlando is not None:
            lettura = lettura.con(sta_parlando=self._parla_adesso())
        self._ultima = lettura
        return lettura.contesto()

    def conoscibilita(self) -> dict[str, str]:
        """Per ogni campo del `Contesto`: `noto`, o perche' no.

        E' la meta' di §15 che mancava. Il gate tace sull'ignoto — corretto — e
        fino a ieri «non e' passata nessuna news» non si poteva distinguere da
        «non poteva passarne nessuna». Adesso una parola per campo lo dice, e
        distingue un interruttore da accendere (`non_prodotto`, `non_composto`)
        da un difetto da inseguire (`ha_sollevato`, `risposta_storta`).

        ⚠️ **Non legge i produttori.** Prima del primo giro la risposta e'
        `mai_letto`, tranne per il cablaggio — che si sa senza leggere niente.
        Rileggere qui darebbe un valore diverso da quello che il giro ha usato.
        """
        if self._ultima is not None:
            return self._ultima.conoscibilita()
        return mai_letto({"sta_parlando": self._sta_parlando is not None})

    # ── il ciclo ─────────────────────────────────────────────────────────────

    def stato(self) -> dict[str, Any]:
        return {
            "periodo_s": round(self._periodo, 1),
            "giri_fatti": self.giri,
            "argomenti": sorted(self.argomenti.parole()),
            "ultimo_giro": self.ultimo,
            # ⚠️ Perche' si vede da fuori: senza questa riga «non e' passata
            # nessuna news» e «un campo era ignoto, quindi non ne poteva passare
            # nessuna» sono lo stesso snapshot.
            #
            # Qui c'era `voce_collegata`, che lo diceva per UNO dei tre campi.
            # Non e' stata affiancata da una riga gemella per il secondo —
            # sarebbe lo stesso difetto in scala ridotta, col terzo scoperto:
            # `conoscibilita()` risponde per OGNI campo che `Contesto` dichiara,
            # e il quarto che qualcuno aggiungesse domani ci entra da solo.
            "conoscibilita": self.conoscibilita(),
        }

    async def un_giro(self) -> bool:
        """Un giro solo. `False` se non c'era niente da guardare.

        Ritorna un bool e non il `Giro` perche' chi chiama non deve decidere
        niente su cio' che e' passato: lo ha gia' deciso il gate, e le card
        sono gia' partite dal `pubblica` del `Watcher`. Questo file decide
        **quando guardare**, non che farsene di cio' che si trova.
        """
        parole = self.argomenti.parole()
        if not parole:
            # Vedi l'intestazione: senza argomenti niente puo' essere
            # rilevante, e un giro sarebbe traffico in cambio di nulla.
            return False
        try:
            g = await self._watcher.giro(parole, self._contesto_adesso())
        except Exception as exc:
            # Un feed di terzi che si comporta male non ferma il core.
            log.error("giro_news_fallito", errore=repr(exc))
            return False
        self.giri += 1
        self.ultimo = self._orologio()
        log.info("giro_news", letti=g.letti, passati=g.passati,
                 scartati=dict(g.scartati), argomenti=len(parole))
        return True

    async def gira(self) -> None:
        """Il ciclo, finche' non lo si annulla."""
        log.info("grado_acceso", grado="news_motore",
                 periodo_s=round(self._periodo, 1))
        while True:
            await asyncio.sleep(self._periodo)
            await self.un_giro()

    def avvia(self) -> asyncio.Task:
        self._compito = asyncio.create_task(self.gira())
        return self._compito

    async def ferma(self) -> None:
        if self._compito is None:
            return
        self._compito.cancel()
        try:
            await self._compito
        except asyncio.CancelledError:
            pass
        except Exception as exc:                         # pragma: no cover
            log.error("motore_news_caduto", errore=repr(exc))
        self._compito = None
