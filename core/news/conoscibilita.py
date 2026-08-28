"""Perche' un campo del `Contesto` e' ignoto — §15, e la sera davanti allo schermo.

## Il problema che questo modulo risolve, e che non e' una funzionalita'

Il gate di §15 legge tre tri-stati, e su `None` tace. E' fail-closed, ed e'
giusto. Ma per **chi guarda** uno snapshot, un gate che non ha mai lasciato
passare niente ha due letture che il sistema non sapeva distinguere:

    non e' passata nessuna news        perche' non c'era niente di rilevante
    non e' passata nessuna news        perche' un campo era ignoto, e lo sara'
                                       per sempre finche' qualcuno non collega
                                       un pezzo che manca

E' l'ambiguita' in cui §15 si e' nascosta per sei turni di fila.

`MotoreNews.stato()` aveva gia' la cura, applicata a **un campo su tre**:
`voce_collegata`, con accanto scritto il perche'. Una riga gemella per il
secondo campo e nessuna per il terzo sarebbe lo stesso difetto in scala
ridotta — fra un mese qualcuno guarda lo stato, non vede il terzo campo, e
ricomincia. Quindi qui non si espone un campo: si espone la **conoscibilita'
dell'intero `Contesto`**, per costruzione, iterando i campi che `Contesto`
dichiara. Il quarto campo che qualcuno aggiungesse domani ci entra da solo.

## Le due cause che si confondevano, e che sono due cose diverse

«Non lo so» non e' una cosa sola:

  **configurazione** — la voce e' spenta, nessuna scrivania ha mai riferito,
  nessuno ha collegato il lettore. E' uno stato permanente finche' qualcuno
  non accende un interruttore, e si risolve accendendolo.

  **guasto** — il produttore c'e' e ha fallito ADESSO: ha sollevato, oppure ha
  risposto qualcosa che non e' un `bool`. E' un difetto da inseguire.

Per il **gate** sono la stessa cosa, e devono restarlo: su entrambe si tace, e
il divieto e' corretto in tutti e due i casi. Per chi **guarda** sono due
lavori diversi. Percio' la distinzione vive qui e **non entra nel `Contesto`**:
il gate continua a ricevere esattamente i tre tri-stati di prima.

## Un produttore per campo, e la causa esce dalla stessa lettura

`Sguardo` e' il valore **insieme** al perche', prodotto dalla stessa chiamata.
Non c'e' una seconda strada che vada a chiedere altrove com'e' andata: sarebbe
un secondo produttore, cioe' due posti da guardare per sapere chi ha deciso, ed
e' esattamente il difetto che i turni precedenti hanno tolto da questa giunzione.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from typing import Any

import structlog

from core.news.gate import Contesto

log = structlog.get_logger(__name__)

#: Il campo si sa.
NOTO = "noto"
#: Il produttore c'e' e dice «non lo so»: voce spenta, nessuna scrivania ha
#: mai riferito. **Configurazione**, non guasto.
NON_COMPOSTO = "non_composto"
#: Il produttore ha sollevato. **Guasto.**
HA_SOLLEVATO = "ha_sollevato"
#: Il produttore ha risposto qualcosa che non e' un `bool`. **Guasto.**
#:
#: ⚠️ Vale come ignoto e non come `bool(r)`: un attributo non inizializzato che
#: torna `0`, o un finto costruito male, diventerebbe `False` — cioe' «e' zitto,
#: interrompi pure». Qui il dubbio costa il silenzio, mai una parola.
RISPOSTA_STORTA = "risposta_storta"
#: Nessuno produce questo campo. E' il caso che `voce_collegata` diceva per uno
#: dei tre, ed e' il piu' importante da vedere: il gate restera' chiuso per
#: sempre, e senza questa parola non lo direbbe nessuno.
NON_PRODOTTO = "non_prodotto"
#: Nessun giro ha ancora guardato. Non e' una proprieta' del campo: e' l'eta'
#: della misura, e a giri zero e' l'unica cosa vera che si possa dire.
MAI_LETTO = "mai_letto"

#: Allowlist, mai denylist (invariante 2): una causa che non e' qui non e' un
#: caso nuovo da accogliere, e' un refuso, e `Sguardo` la rifiuta.
CAUSE = (NOTO, NON_COMPOSTO, HA_SOLLEVATO, RISPOSTA_STORTA, NON_PRODOTTO,
         MAI_LETTO)

#: Un pezzo che manca: si risolve collegando qualcosa.
CONFIGURAZIONI = frozenset({NON_COMPOSTO, NON_PRODOTTO})
#: Un difetto da inseguire: il produttore c'e' e non risponde.
GUASTI = frozenset({HA_SOLLEVATO, RISPOSTA_STORTA})

#: I campi del `Contesto`, nell'ordine in cui li dichiara. **Derivati, non
#: elencati**: e' cosi' che il quarto campo entra senza che nessuno se ne
#: ricordi.
CAMPI: tuple[str, ...] = tuple(f.name for f in fields(Contesto))


@dataclass(frozen=True)
class Sguardo:
    """Un campo letto una volta: che cosa vale, e se non vale, perche'."""

    valore: bool | None
    causa: str

    def __post_init__(self) -> None:
        if self.causa not in CAUSE:
            raise ValueError(f"causa sconosciuta: {self.causa!r}, "
                             f"ammesse {list(CAUSE)}")
        # ⚠️ Un valore e una causa che si contraddicono non si possono
        # costruire: `Sguardo(None, NOTO)` direbbe «lo so, ed e' ignoto», e
        # `Sguardo(True, HA_SOLLEVATO)` direbbe «e' rotto, ed ecco il valore».
        # La struttura lo impedisce, invece di raccomandarlo a chi scrive.
        if (self.valore is None) is not (self.causa != NOTO):
            raise ValueError(f"Sguardo({self.valore!r}, {self.causa!r}) si "
                             "contraddice: `noto` se e solo se c'e' un valore")


def guarda(leggi: Callable[[], Any], *, campo: str = "") -> Sguardo:
    """Legge un produttore e dice com'e' andata. Non solleva mai.

    I quattro esiti sono i quattro modi in cui un `bool | None` puo' arrivare,
    e nessuno di loro ferma chi legge: siamo dentro il giro dei feed, e un
    produttore rotto deve togliere il permesso di parlare, non fermare il
    motore.
    """
    try:
        r = leggi()
    except Exception as exc:
        # ANNUNCIATO: uno stato che diventa ignoto in silenzio e' indistinguibile
        # da uno che non e' mai stato collegato — il difetto di partenza.
        log.warning("stato_non_leggibile", campo=campo, errore=repr(exc))
        return Sguardo(None, HA_SOLLEVATO)
    if r is None:
        return Sguardo(None, NON_COMPOSTO)
    if not isinstance(r, bool):
        log.warning("stato_non_bool", campo=campo, tipo=type(r).__name__)
        return Sguardo(None, RISPOSTA_STORTA)
    return Sguardo(r, NOTO)


@dataclass(frozen=True)
class Lettura:
    """Il `Contesto` di un giro e il perche' di ciascun suo ignoto.

    Una cosa sola, prodotta da una lettura sola. Il gate riceve `contesto()` —
    gli stessi tre tri-stati di sempre — e chi guarda riceve `conoscibilita()`.
    """

    sguardi: Mapping[str, Sguardo] = field(default_factory=dict)

    def __post_init__(self) -> None:
        estranei = sorted(set(self.sguardi) - set(CAMPI))
        if estranei:
            raise ValueError(f"{estranei} non sono campi di Contesto: {list(CAMPI)}")

    def contesto(self) -> Contesto:
        """Cio' che il gate riceve, e non un byte di piu'."""
        return Contesto(**{n: s.valore for n, s in self.sguardi.items()})

    def conoscibilita(self) -> dict[str, str]:
        """Per ogni campo del `Contesto`: `noto`, o perche' no.

        Un campo senza `Sguardo` e' `non_prodotto` — nessuno lo riempie, e il
        gate restera' chiuso per sempre.
        """
        return {n: self.sguardi[n].causa if n in self.sguardi else NON_PRODOTTO
                for n in CAMPI}

    def con(self, **sguardi: Sguardo) -> "Lettura":
        """La stessa lettura, con qualche campo riempito da chi lo produce."""
        return Lettura({**self.sguardi, **sguardi})

# ⚠️ Qui c'erano `Sguardo.guasto` (`causa in GUASTI`, un'espressione sola) e
# `Lettura.noti(**valori)`, una scorciatoia per dichiarare valori gia' noti.
# La scansione degli orfani li ha trovati appena scritti: **nessun chiamante in
# `core/`**. Comodita' per i test scritte dentro il codice applicativo sono la
# stessa famiglia di difetto che questa fase insegue — un pezzo che sembra
# congiunto e non lo e'. La scorciatoia vive in `tests/conftest.py`, che e' la
# sua casa.


def mai_letto(prodotti: Mapping[str, bool]) -> dict[str, str]:
    """La conoscibilita' prima che un giro abbia guardato.

    ⚠️ Non si legge niente per rispondere, e non si puo': leggere qui sarebbe
    una seconda chiamata al produttore, con un valore diverso da quello che il
    giro ha usato. `mai_letto` non e' una proprieta' del campo, e' l'eta' della
    misura.

    Cio' che invece si sa **senza leggere** e' il cablaggio: se nessuno produce
    un campo, il gate restera' chiuso per sempre e va detto subito, non al primo
    giro. `prodotti` dice, campo per campo, se un produttore c'e'.
    """
    return {n: MAI_LETTO if prodotti.get(n, True) else NON_PRODOTTO
            for n in CAMPI}
