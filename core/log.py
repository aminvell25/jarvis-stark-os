"""La configurazione di structlog, e la redazione dei segreti dentro i log.

## Il difetto che questo modulo chiude

`core/settings.py` costruisce da tempo un registro dei segreti (`SECRETS`) e
un processore (`redact_secrets`). Il registro viene popolato davvero, a ogni
`load_settings()`. Il processore no: **in tutto `core/` non esisteva nessuna
chiamata a `structlog.configure()`**, quindi structlog girava con la catena
predefinita e nessun processore filtrava niente. Una protezione scritta, mai
installata, e' indistinguibile da nessuna protezione — con l'aggravante che
chi legge il codice la vede e la crede attiva.

Qui c'e' la catena vera, e dentro la catena la redazione.

## Che cosa aggiunge alla redazione che c'era

`redact_secrets` guarda **solo il primo livello** dell'evento e solo i valori
che sono gia' stringhe. Ma i log di questo progetto passano dizionari: uno
snapshot della mesh, un messaggio WebSocket, la risposta di un provider. Una
chiave dentro `payload={"auth": {"token": ...}}` non veniva toccata.
`redazione()` scende: dizionari, liste, tuple, insiemi, byte, e le chiavi dei
dizionari — non solo i valori.

## Che cosa NON fa, e perche'

Non maschera per sottostringa i segreti corti: vedi `SOGLIA_SOTTOSTRINGA`.

## Ordine nella catena

La redazione va **dopo** i processori che producono testo (`format_exc_info`
trasforma una eccezione in una stringa: se la redazione girasse prima, il
traceback uscirebbe intatto) e **prima** del renderer (dopo il renderer
l'evento e' una riga sola e la struttura e' persa). E' l'ultimo anello prima
della scrittura.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, MutableMapping
from typing import Any, Final, Literal, TextIO

import structlog
from pydantic import SecretStr

from core.settings import SECRETS, SecretRegistry

#: Lo stesso marcatore del registro: due maschere diverse per la stessa cosa
#: renderebbero i log difficili da leggere e i test difficili da scrivere.
MASCHERA: Final[str] = SecretRegistry.MASK


# ─────────────────────────────────────────────────────────────────────────────
# La soglia — perche' un segreto corto non si maschera per sottostringa
# ─────────────────────────────────────────────────────────────────────────────
#
# Mascherare per sottostringa vuol dire cercare il segreto DENTRO ogni testo.
# Con un segreto lungo e' cio' che serve: la chiave annegata in un URL sparisce.
# Con un segreto corto e' un disastro silenzioso — se qualcuno registrasse
# `"abc"`, ogni riga che contiene «abc» (in `traccia`, in un path, in un nome
# di tool) uscirebbe monca, e nessuno collegherebbe le due cose.
#
# La soglia non e' scelta a occhio: e' il piu' piccolo n per cui incontrare
# PER CASO un segreto di n caratteri dentro i log e' improbabile.

#: L'alfabeto piu' povero che prendono le chiavi vere: esadecimale. Le chiavi
#: di questo progetto sono piu' ricche (base62), quindi assumere 16 e' il caso
#: sfavorevole — la soglia che ne esce vale a maggior ragione per le altre.
ALFABETO_PEGGIORE: Final[int] = 16

#: L'ordine di grandezza dei caratteri di log che il processore attraversa in
#: una sessione lunga: un milione, cioe' circa 5.000 righe da 200 caratteri.
CARATTERI_PER_SESSIONE: Final[int] = 1_000_000

#: La probabilita' tollerata che, in quella sessione, una sequenza qualunque
#: coincida col segreto e si porti via del testo legittimo: una su mille.
FALSO_POSITIVO_TOLLERATO: Final[float] = 1e-3


def _soglia_sottostringa(
    alfabeto: int, caratteri: int, tolleranza: float
) -> int:
    """Il piu' piccolo n con `caratteri / alfabeto**n <= tolleranza`.

    Le occorrenze possibili di una sequenza di n caratteri in un testo di
    `caratteri` simboli sono ~`caratteri`; ognuna coincide col segreto con
    probabilita' `alfabeto**-n`. Il prodotto e' il numero atteso di falsi
    positivi, e lo vogliamo sotto `tolleranza`.
    """
    if alfabeto < 2:
        raise ValueError("l'alfabeto deve avere almeno due simboli")
    if tolleranza <= 0.0:
        raise ValueError("la tolleranza deve essere positiva")
    n = 1
    while caratteri / (alfabeto**n) > tolleranza:
        n += 1
        if n > 64:                                # nessuna chiave e' cosi' lunga
            raise ValueError("soglia irraggiungibile con questi parametri")
    return n


#: Sotto questa lunghezza un segreto si maschera **solo se e' il valore
#: intero** di un campo, mai come pezzo di una stringa piu' lunga. Con i
#: parametri qui sopra vale 8.
#:
#: ⚠️ Non e' un buco: le chiavi vere di §8 sono lunghe decine di caratteri.
#: E' il caso di un valore corto finito nel registro per errore, e in quel
#: caso il danno di mascherare mezzo log e' peggiore del rischio che il
#: valore corto compaia — un segreto di sette caratteri non e' un segreto.
SOGLIA_SOTTOSTRINGA: Final[int] = _soglia_sottostringa(
    ALFABETO_PEGGIORE, CARATTERI_PER_SESSIONE, FALSO_POSITIVO_TOLLERATO
)

#: Quanto scende la ricorsione prima di arrendersi. I valori di un evento
#: stanno a profondita' 1, un messaggio WebSocket annidato arriva a 3 o 4.
#: Oltre questa soglia il valore non viene lasciato passare com'e': viene
#: appiattito a testo e ripulito. Si perde la struttura, non il segreto — e
#: una struttura piu' profonda di cosi', in una riga di log, e' gia' illeggibile.
PROFONDITA_MASSIMA: Final[int] = 6


# ─────────────────────────────────────────────────────────────────────────────
# Lettura del registro esistente
# ─────────────────────────────────────────────────────────────────────────────


def _valori_registrati() -> tuple[str, ...] | None:
    """I valori del registro di `core/settings.py`. `None` se non leggibili.

    ⚠️ **Non esiste un secondo registro.** Questo modulo non tiene una copia
    dei segreti: una copia si disallineerebbe al primo `SECRETS.register()`
    fatto altrove (`doctor`, `ws_server`, i test) e mascherebbe meno di quanto
    promette. Legge quello che c'e'.

    `SecretRegistry` non espone un lettore pubblico, quindi la lettura passa
    dagli attributi interni. Se un domani cambiassero nome, `None` fa scattare
    la strada di ripiego del processore — `SECRETS.scrub()`, che e' API
    pubblica — invece di far smettere di mascherare. La degradazione e' verso
    il piu' stretto, non verso il piu' largo.
    """
    valori = getattr(SECRETS, "_values", None)
    if not isinstance(valori, set):
        return None
    lock = getattr(SECRETS, "_lock", None)
    if lock is None:
        return tuple(valori)
    with lock:
        return tuple(valori)


# ─────────────────────────────────────────────────────────────────────────────
# Oscuramento ricorsivo
# ─────────────────────────────────────────────────────────────────────────────


def _pulitore(
    lunghi: tuple[str, ...], corti: frozenset[str]
) -> Callable[[str], str]:
    """Costruisce la funzione che ripulisce UNA stringa.

    Passare una funzione invece della coppia (lunghi, corti) serve alla strada
    di ripiego: quando il registro non e' leggibile la ricorsione resta la
    stessa e cambia solo questa funzione, che diventa `SECRETS.scrub`.
    """

    def ripulisci(testo: str) -> str:
        if testo in corti:
            # I corti si mascherano SOLO come valore intero di un campo:
            # vedi `SOGLIA_SOTTOSTRINGA`.
            return MASCHERA
        for segreto in lunghi:
            if segreto in testo:
                testo = testo.replace(segreto, MASCHERA)
        return testo

    return ripulisci


def _oscura_byte(dati: bytes, ripulisci: Callable[[str], str]) -> bytes:
    """Come per il testo, ma su byte — l'uscita di un sottoprocesso lo e'.

    `surrogateescape` in andata e ritorno e' senza perdita anche su byte che
    non sono UTF-8 valido: nessun log viene alterato per il solo fatto di
    essere passato di qui.
    """
    testo = dati.decode("utf-8", "surrogateescape")
    pulito = ripulisci(testo)
    if pulito == testo:
        return dati
    return pulito.encode("utf-8", "surrogateescape")


def _oscura(valore: Any, ripulisci: Callable[[str], str], profondita: int) -> Any:
    """Ritorna il valore ripulito, o **lo stesso oggetto** se non e' cambiato.

    Restituire l'originale quando non c'e' niente da fare non e' solo
    un'economia: vuol dire che un log senza segreti attraversa il processore
    senza che nessuna struttura del chiamante venga copiata o modificata.
    """
    if valore is None or isinstance(valore, (bool, int, float)):
        return valore

    if isinstance(valore, SecretStr):
        # Anche vuoto: il tipo dichiara «questo e' un segreto», e la stringa
        # vuota di oggi puo' essere la chiave di domani.
        return MASCHERA

    if isinstance(valore, str):
        pulito = ripulisci(valore)
        return valore if pulito == valore else pulito

    if isinstance(valore, (bytes, bytearray)):
        return _oscura_byte(bytes(valore), ripulisci)

    if profondita >= PROFONDITA_MASSIMA:
        # Ripiego fail-closed: si perde la struttura, non il segreto.
        profondo = _testo_sicuro(valore)
        return MASCHERA if profondo is None else ripulisci(profondo)

    if isinstance(valore, dict):
        fuori: dict[Any, Any] = {}
        cambiato = False
        for chiave, dentro in valore.items():
            # Anche le CHIAVI: un dizionario indicizzato per token esiste, e
            # ripulirne i soli valori lascerebbe il segreto in bella vista.
            k = _oscura(chiave, ripulisci, profondita + 1)
            v = _oscura(dentro, ripulisci, profondita + 1)
            cambiato = cambiato or k is not chiave or v is not dentro
            try:
                fuori[k] = v
            except TypeError:                        # chiave non piu' hashabile
                fuori[_testo_sicuro(k) or MASCHERA] = v
                cambiato = True
        return fuori if cambiato else valore

    if isinstance(valore, (list, tuple, set, frozenset)):
        originali = list(valore)
        elementi = [_oscura(v, ripulisci, profondita + 1) for v in originali]
        if all(n is v for n, v in zip(elementi, originali)):
            return valore
        try:
            return type(valore)(elementi)            # set, frozenset, tuple...
        except TypeError:
            return list(elementi)

    # Oggetto qualunque. ⚠️ **Si guardano `str()` E `repr()`, e la ragione e'
    # misurata**: qui c'era scritto «il renderer lo stampera' con `str()`»,
    # ed e' falso. `JSONRenderer` serializza gli oggetti sconosciuti con
    # `repr`, e `ConsoleRenderer` rende con `repr` ogni valore che non sia
    # gia' una stringa. Una classe con `__str__` discreto e `__repr__` che
    # mostra i campi — la forma predefinita di ogni dataclass — usciva pulita
    # al giudizio e con la chiave in chiaro sulla riga.
    #
    # Riprodotto il 27 agosto su tutt'e due i renderer:
    #     {"o": "Furbo(key='finta_NON_REALE_...')"}      su json
    #     o=Furbo(key='finta_NON_REALE_...')             su console
    #
    # Se **una qualunque** delle due forme e' sporca, l'oggetto non esce.
    forme = [_testo_sicuro(valore), _testo_sicuro(valore, repr)]
    if any(f is None for f in forme):
        # Non si e' potuto guardare dentro: non si puo' dire che sia pulito.
        return MASCHERA
    if all(ripulisci(f) == f for f in forme):
        return valore
    # Sporco in almeno una forma: esce la sola forma che il renderer userebbe
    # per una stringa, gia' ripulita.
    return ripulisci(forme[0])


def _testo_sicuro(valore: Any, come=str) -> str | None:
    """`str()` — o `repr()` — che non puo' far fallire una riga di log.

    `None` se ha sollevato.

    Un `__str__` che solleva farebbe perdere l'evento intero. Chi chiama
    tratta il `None` come «contenuto ignoto», e il contenuto ignoto esce
    mascherato: non si dichiara pulito cio' che non si e' potuto leggere.
    """
    try:
        return come(valore)
    except Exception:                                # noqa: BLE001 — vedi sopra
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Il processore
# ─────────────────────────────────────────────────────────────────────────────


def redazione(
    _logger: Any, _metodo: str, evento: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Processore structlog: nessun segreto noto esce da qui.

    Va inserito per ultimo prima del renderer (vedi il docstring del modulo).
    Non solleva mai: un processore che solleva spegne il log del sistema.
    """
    try:
        valori = _valori_registrati()
        if valori is None:
            # Non sappiamo QUALI sono i segreti: la ricorsione resta la
            # stessa, ma ogni stringa passa dallo scrub pubblico del registro,
            # che maschera anche i corti. Piu' rumore nei log, zero chiavi
            # fuori.
            ripulisci: Callable[[str], str] = SECRETS.scrub
        else:
            lunghi = tuple(v for v in valori if len(v) >= SOGLIA_SOTTOSTRINGA)
            corti = frozenset(v for v in valori if len(v) < SOGLIA_SOTTOSTRINGA)
            ripulisci = _pulitore(lunghi, corti)

        # ⚠️ Nessuna scorciatoia a registro vuoto. Sarebbe la piu' ovvia — e
        # lascerebbe passare i `SecretStr`, che si mascherano per TIPO e non
        # perche' qualcuno li ha registrati. A registro vuoto la ricorsione
        # gira lo stesso e non cambia niente: `_oscura` ritorna gli oggetti
        # originali, quindi l'evento esce identico, campo per campo.

        if isinstance(evento, dict):
            # Profondita' 0: i valori dei campi stanno a 1, e le chiavi dei
            # campi vengono ripulite come tutto il resto.
            return _oscura(evento, ripulisci, 0)

        for chiave, valore in list(evento.items()):   # mapping non-dict
            ripulito = _oscura(valore, ripulisci, 1)
            if ripulito is not valore:
                evento[chiave] = ripulito
        return evento
    except Exception:                                 # noqa: BLE001
        # Ultimo argine. Se qualcosa qui dentro va storto non possiamo lasciar
        # uscire l'evento cosi' com'e': non sappiamo se conteneva una chiave.
        return {"event": "redazione_fallita", "originale": MASCHERA}


# ─────────────────────────────────────────────────────────────────────────────
# La catena
# ─────────────────────────────────────────────────────────────────────────────

Formato = Literal["auto", "json", "console"]

#: Il livello di ripiego quando il nome non si riconosce. Un refuso in una
#: variabile d'ambiente non deve impedire l'avvio del core.
LIVELLO_PREDEFINITO: Final[str] = "info"


def _e_un_terminale(flusso: TextIO) -> bool:
    try:
        return bool(flusso.isatty())
    except Exception:                                 # noqa: BLE001
        return False


def _livello_numerico(nome: str) -> tuple[int, bool]:
    """`(numero, riconosciuto)`. Sconosciuto -> INFO, e lo si dice dopo."""
    mappa = logging.getLevelNamesMapping()
    numero = mappa.get(nome.strip().upper())
    if numero is None:
        return mappa[LIVELLO_PREDEFINITO.upper()], False
    return numero, True


def configura(
    livello: str = LIVELLO_PREDEFINITO,
    formato: Formato = "auto",
    flusso: TextIO | None = None,
) -> None:
    """Installa la catena di produzione di structlog. Chiamare **una volta**.

    ⚠️ Va chiamata **prima** di qualunque altra cosa che logghi — in
    particolare prima di `load_settings()`, che scrive `settings_caricate` con
    l'elenco delle chiavi presenti. Non e' questione di estetica: prima di
    questa chiamata la redazione non c'e'.

    `formato="auto"` sceglie il renderer leggibile quando l'uscita e' un
    terminale (sviluppo) e JSON quando non lo e' (systemd, journal).

    Non tocca il registro dei segreti: quello lo popola `load_settings()`, e
    la redazione legge il registro a ogni evento, quindi una chiave registrata
    dopo l'avvio e' coperta lo stesso.
    """
    uscita: TextIO = flusso if flusso is not None else sys.stderr
    terminale = _e_un_terminale(uscita)
    come_json = formato == "json" or (formato == "auto" and not terminale)
    renderer: Any = (
        structlog.processors.JSONRenderer()
        if come_json
        else structlog.dev.ConsoleRenderer(colors=terminale)
    )

    numero, riconosciuto = _livello_numerico(livello)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # ⚠️ ULTIMO prima del renderer: dopo `format_exc_info`, che
            # trasforma il traceback in stringa, e prima che la struttura
            # dell'evento venga appiattita in una riga.
            redazione,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numero),
        logger_factory=structlog.WriteLoggerFactory(file=uscita),
        # `False`: i moduli prendono il proprio logger all'import, cioe' prima
        # di questa chiamata. Con la cache attiva il primo logger usato
        # resterebbe legato alla catena predefinita — senza redazione.
        cache_logger_on_first_use=False,
    )

    if not riconosciuto:
        structlog.get_logger(__name__).warning(
            "livello_di_log_sconosciuto",
            richiesto=livello,
            uso=LIVELLO_PREDEFINITO,
        )
