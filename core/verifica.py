"""«Eseguito» non e' «verificato» — ADR-012.

## Perche' esiste

`ToolResult(ok=True)` significa **una cosa sola**: la chiamata non ha sollevato
un'eccezione. Non significa che il file sia sul disco, che l'impostazione abbia
avuto effetto, che il cestino contenga cio' che doveva contenere.

Per la maggior parte dei tool la differenza e' teorica. Per tre categorie no:
quelli con `side_effect=True`, quelli che passano da un processo esterno, e —
il giorno in cui JARVIS agira' da solo — tutti quanti, perche' sara' l'unica
cosa che distingue un'azione riuscita da una raccontata.

Il progetto ci era gia' arrivato per conto suo, in **quattro** punti, e in tre
dei quattro nella forma giusta e nello scopo sbagliato:

    core/engine.py       `wake_model` (vivo) accanto a `wake_model_chiesto`
                         (atteso) — ma vale per UN campo
    core/doctor.py       ok / warn / fail — ma per SOTTOSISTEMI, non per azioni
    core/protocolli.py   `Esito(eseguito, cambiato, ...)` — ma confronta
                         osservato con osservato-DI-PRIMA: non c'e' un atteso
    core/tools/files.py  `_trash` cerca dove e' finito il file e riferisce
                         `verificato: bool` — **e poi restituisce `ok=True`
                         comunque**. La verifica c'era e nessuno la guardava.

Il quarto e' il piu' istruttivo: il campo esisteva, era corretto, e non
cambiava niente. Un'osservazione che non ha effetto non e' una verifica.

## Che cosa fa questo modulo, e che cosa NON fa

Prende la frase che `docs/SPEC.md` impone alle persone che scrivono un
documento di accettazione — *«Se non puoi verificare un criterio, lo DICHIARI.
Non lo dai per buono»* — e la rende vera per il codice a runtime.

⚠️ **Non sostituisce la conferma** (invariante 3). La conferma sta *prima*
dell'azione e la autorizza un umano; la verifica sta *dopo* e la fa la
macchina. Un tool `side_effect=True` continua a chiedere conferma col percorso
risolto, verificatore o no. Chi legge questo modulo come «adesso che
verifichiamo possiamo confermare meno» lo ha letto al contrario.

## Il difetto sottile, e va detto prima di tutto il resto

Un verificatore che rilegge cio' che il tool ha appena scritto **attraverso lo
stesso codice** non prova niente: prova che il codice e' coerente con se'
stesso. Se il tool scrive tramite un percorso sbagliato e il verificatore legge
tramite lo stesso percorso sbagliato, il verde e' una bugia con due firme.

Percio' `fonte` e' un campo obbligato e deve nominare **qualcosa di diverso dal
tool**: `os.stat`, il TOML riletto dal disco, i due `os.path.exists`. Dove una
fonte indipendente non esiste, si dichiara `NON_VERIFICATO` invece di
inventarsi una prova. **Un verificatore debole dichiarato vale piu' di un
verificatore forte finto.**
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class Verdetto(StrEnum):
    """Che cosa si sa davvero di un'azione, dopo averla fatta.

    ⚠️ **Si chiama `Verdetto` e non `Esito`, e la ragione e' misurata.** In
    `core/` `Esito` e' gia' il nome di **tre** classi diverse — la ronda dei
    protocolli, la conferma di §6.2, i collettori di news — e `scripts/orfani.py`
    conta gli `ast.Attribute` **per nome**: la sua intestazione dichiara che 52
    nomi pubblici sono gia' definiti da due o piu' moduli, e che due volte in un
    giorno quel punto cieco ha coperto un orfano vero. Un quarto omonimo
    avrebbe spostato il rinominare sui chiamanti — `from core.verifica import
    Esito as EsitoVerifica` — invece che sulla definizione. ADR-012 lo chiamava
    `Esito`, ed e' stato corretto prima della prima riga di codice.

    **Quattro valori, e ognuno ha un produttore.** ADR-012 ne elencava sei:
    `ANNULLATO` e `DEGRADATO` non li emetteva nessuno — niente annulla un tool
    (la conferma e' rifiutata o scaduta, e sono entrambe un blocco), e il
    ripiego annunciato dell'invariante 12 riguarda la VOCE, che non e' un tool.
    E' la stessa regola applicata a `Origine` nella fetta 1: un valore senza
    produttore e' un test rosso, non un posto tenuto caldo.
    """

    #: Atteso e osservato coincidono, e l'osservazione viene da fuori dal tool.
    RIUSCITO = "riuscito"
    #: Divergono. Il tool puo' aver detto `ok=True`: e' proprio il caso per cui
    #: questo modulo esiste.
    FALLITO = "fallito"
    #: Non e' stato fatto, e lo sa il registro: l'utente ha rifiutato, la
    #: domanda e' scaduta, o nessun meccanismo di conferma e' collegato.
    #: **Osservato da `invoke`**, non riferito dal tool.
    BLOCCATO = "bloccato"
    #: Nessuna fonte per saperlo. Non e' un fallimento e non e' un successo:
    #: e' l'unico esito onesto quando non si sa, e la sua esistenza e' tutto il
    #: valore di ADR-012. Senza, «non lo so» collassa su «si'» e JARVIS
    #: comincia a raccontare.
    NON_VERIFICATO = "non_verificato"


#: I due verdetti che significano «ho guardato e so com'e' andata». Gli altri
#: due sono onesti ma non sono una verifica: `NON_VERIFICATO` dice «non lo so»,
#: `BLOCCATO` che l'azione non e' partita.
#:
#: Vive qui e non in `core/doctor.py`, che e' il suo unico lettore, perche' e'
#: una proprieta' di `Verdetto`: scriverla la' vorrebbe dire una seconda
#: opinione su che cosa conti come verifica, in un file che di mestiere ne
#: conta un'altra.
CONCLUSIVI = frozenset({Verdetto.RIUSCITO, Verdetto.FALLITO})


#: Cio' che si scrive in `fonte` quando non c'e' niente da guardare. E' una
#: costante e non una stringa libera perche' `jarvis doctor` la conta.
NESSUNA_FONTE = "nessun verificatore dichiarato"


@dataclass(frozen=True, slots=True)
class Verifica:
    """Che cosa ci si aspettava, che cosa si e' visto, e **chi l'ha visto**."""

    #: In parole, non in codice: finisce nel diario e la rilegge una persona.
    atteso: str
    osservato: str
    verdetto: Verdetto
    #: Da dove viene l'osservazione. **Mai il tool stesso**: `registry.invoke`
    #: declassa a `NON_VERIFICATO` un verificatore che nomina il proprio tool,
    #: perche' rileggere attraverso lo stesso codice non e' una verifica.
    fonte: str
    quando: float
    #: ADR-011. Senza, una verifica non si ritrova — ed e' la ragione per cui
    #: la traccia veniva prima.
    traccia_id: str | None = None

    def __post_init__(self) -> None:
        if not self.fonte.strip():
            raise ValueError(
                "una verifica senza `fonte` non e' una verifica: il campo deve "
                "nominare da dove viene l'osservazione, e deve essere qualcosa "
                "di diverso dal tool che si sta verificando (ADR-012)."
            )

    # ── le tre forme in cui nasce ────────────────────────────────────────────
    #
    # Sono costruttori e non `Verifica(...)` a mano perche' i campi sono sei e
    # sbagliarne uno produce una verifica che sembra buona. Qui il verdetto lo
    # decide il costruttore, non chi lo chiama.

    @classmethod
    def confronta(cls, atteso: str, osservato: str, *, fonte: str,
                  traccia_id: str | None = None) -> "Verifica":
        """`RIUSCITO` se coincidono, `FALLITO` se no. Il caso normale."""
        return cls(atteso=atteso, osservato=osservato,
                   verdetto=Verdetto.RIUSCITO if atteso == osservato
                   else Verdetto.FALLITO,
                   fonte=fonte, quando=time.time(), traccia_id=traccia_id)

    @classmethod
    def non_verificata(cls, perche: str, *, fonte: str = NESSUNA_FONTE,
                       atteso: str = "", traccia_id: str | None = None) -> "Verifica":
        """«Non lo so», detto per esteso.

        `perche` finisce in `osservato`, ed e' voluto: chi rilegge il diario
        deve trovare **la ragione** dove si aspetta di trovare l'osservazione,
        non un campo vuoto accanto a un verdetto muto.
        """
        return cls(atteso=atteso, osservato=perche,
                   verdetto=Verdetto.NON_VERIFICATO, fonte=fonte,
                   quando=time.time(), traccia_id=traccia_id)

    @classmethod
    def bloccata(cls, perche: str, *, traccia_id: str | None = None) -> "Verifica":
        """Non e' stato fatto, e **il registro l'ha visto**.

        La fonte e' `registry.invoke` e non il tool: e' il registro ad aver
        posto la domanda di conferma e ad aver ricevuto il no. Questo e' l'unico
        verdetto che non ha bisogno di un verificatore per essere vero.
        """
        return cls(atteso="l'azione viene eseguita", osservato=perche,
                   verdetto=Verdetto.BLOCCATO, fonte="registry.invoke",
                   quando=time.time(), traccia_id=traccia_id)

    def con_traccia(self, traccia_id: str | None) -> "Verifica":
        """La stessa verifica, con la traccia attaccata.

        Serve a `registry.invoke`: un verificatore non conosce la traccia — non
        deve — e il registro gliela attacca all'uscita, come fa col
        `traccia_id` di `ToolResult`.
        """
        if traccia_id is None or self.traccia_id == traccia_id:
            return self
        return Verifica(atteso=self.atteso, osservato=self.osservato,
                        verdetto=self.verdetto, fonte=self.fonte,
                        quando=self.quando, traccia_id=traccia_id)
