"""Che cosa JARVIS ha fatto mentre non c'era nessuno — e che cosa si e' rotto.

`initiatives/` esiste dalla Fase 4 e la sua docstring dice «visibile al
risveglio». **Non lo era**: `registra_iniziativa` scriveva, e nessuno leggeva.
Il file il cui unico scopo e' essere letto al risveglio non aveva un lettore, e
la cartella e' rimasta a zero righe fino al 27 agosto.

Questo modulo e' il lettore, e la frase che ne esce.

## Dal 2 settembre 2026 legge anche il DIARIO

Fino ad allora il risveglio sapeva dire che cosa JARVIS aveva FATTO e non che
cosa si era ROTTO: un provider di ripiego, la sessione di Claude caduta, il
consolidamento saltato per quota, un protocollo senza il suo tool andavano
soltanto nel log — che senza systemd non viene nemmeno scritto. Misurato sul
disco vero: 91 righe di diario in otto giorni, **zero** con `ok=False`, zero
con un verdetto. Adesso i guasti entrano nel flusso `azione` da un emettitore
solo, `Engine._annota_guasto`, e il risveglio li rilegge da li' — insieme a
`core_avviato` e `core_fermato`, che dicono da quando a quando JARVIS era
spento invece di lasciarlo indovinare dai buchi fra le righe.

## ⚠️ Il resoconto NON passa da un modello

E' composto dai dati, con una tabella di frasi. Non e' un risparmio: e' una
proprieta'. Cio' che JARVIS dice di **aver fatto** non deve poter essere
inventato — un modello che riassume un registro puo' sbagliare un numero o
aggiungere una riga che non c'era, e sarebbe la peggiore bugia che questo
sistema possa dire. Il riassunto di una CONVERSAZIONE lo fa un modello (§5.5);
il rendiconto delle proprie azioni no.

Vale anche per i guasti, e per il loro «perche'»: la causa pronunciata viene
da `CAUSE`, un elenco chiuso di codici; il testo libero di un'eccezione resta
nel campo `dettaglio` della riga, si legge con `scripts/diario.py --azioni` o
`--traccia ID`, e **non si pronuncia**. Una causa fuori tabella si dice come
«per una ragione che e' nel diario», che e' vero, invece di una frase
inventata, che non lo sarebbe.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from core.memory.consolidate import PERIODO_S
from core.memory.store import MemoryStore

SEGNAPOSTO = "_ultimo-resoconto"

#: Le frasi, per tipo di iniziativa. **Allowlist, non formattatore generico**:
#: un tipo nuovo senza frase qui si vede — `tests/test_il_resoconto_al_risveglio.py`
#: confronta questa tabella con i tipi che il core registra davvero, e diventa
#: rosso invece di lasciare a JARVIS una frase che non sa dire.
FRASI = {
    # ⚠️ La frase la scrive l'UTENTE, in `settings.toml`, insieme al protocollo.
    # JARVIS non compone una spiegazione di una cosa che non ha deciso lui di
    # sorvegliare: dice quella che gli e' stata data, e se sono piu' d'una le
    # unisce in prosa (§5.7 vieta gli elenchi a voce).
    "protocollo": lambda v: _elenco(
        list(dict.fromkeys(str(r.get("frase") or r.get("nome") or "") for r in v
                           if r.get("frase") or r.get("nome")))),
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


# ── i guasti ─────────────────────────────────────────────────────────────────

#: Le CAUSE che si possono pronunciare, per tipo di guasto. Nella riga di
#: diario sta un CODICE chiuso — `Motivo` di `core/providers/health.py`,
#: `EventoT1` di `core/llm/supervisor.py`, `CAUSE_ESITO` di
#: `core/protocolli.py`, o una delle stringhe che l'emettitore dichiara — e
#: qui stanno le parole. Gli elenchi non si copiano a mano:
#: `tests/test_il_resoconto_al_risveglio.py` confronta queste chiavi con
#: quelle sorgenti, e un codice nuovo senza parole diventa rosso.
CAUSE: dict[str, dict[str, str]] = {
    "ripiego_voce": {
        "chiave assente": "non ho trovato la chiave del servizio vocale",
        "il primario ha fallito": "il servizio vocale non rispondeva",
    },
    "microfono_caduto": {
        "flusso finito": "il flusso del microfono e' finito da solo",
        "eccezione": "il microfono ha dato un errore",
    },
    "t1_degradato": {
        "riavviato": "ho dovuto riavviare la sessione di Claude",
        "riavvii_ripetuti": ("la sessione di Claude cadeva di continuo e ho "
                             "smesso di riavviarla"),
        "non_risponde": "la sessione di Claude non rispondeva",
        "auth_expired": "la mia sessione e' scaduta e serve un nuovo login",
    },
    "consolidamento": {
        "quota": "la quota era finita",
        "caduto": "qualcosa e' caduto a meta'",
    },
    "protocollo": {
        "non registrato": "il suo strumento non era registrato",
        "caduto": "il suo strumento e' caduto",
        "senza risposta": "il suo strumento non ha risposto",
    },
    "mcp": {
        "non montato": "non sono riuscito a montare",
        "promozione fallita": "non ho potuto promuovere i comandi di",
    },
    "resoconto": {"caduto": "il resoconto stesso e' caduto"},
}

#: Cio' che si dice quando il codice della causa non e' in `CAUSE`. E' vero,
#: e non spiega: meglio di una spiegazione inventata.
IGNOTA = "per una ragione che e' nel diario"

#: Le righe del flusso `azione` che non sono mai un guasto, per intento.
NON_GUASTI = frozenset({"resoconto_al_risveglio", "core_avviato", "core_fermato"})

#: Gli esiti di una conferma di §6.2 che il registro scrive come
#: `errore="operazione <esito>"`. Il no del Signore non e' un guasto: e' la
#: conferma che funziona. `tests/test_il_resoconto_al_risveglio.py` li
#: confronta con `core/tools/confirm.py`.
ESITI_DI_CONFERMA = ("rifiutato", "scaduto")

MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre")


def _quando(ts: float, adesso: float) -> str:
    """Un'ora che si pronuncia: «oggi alle 8:02», «ieri alle 23:10», «il 30
    agosto alle 4:00». Ore locali, senza lo zero davanti: «zero otto» non e'
    un orario che qualcuno dica."""
    t = time.localtime(ts)
    a = time.localtime(adesso)
    ora = f"{t.tm_hour}:{t.tm_min:02d}"
    if (t.tm_year, t.tm_yday) == (a.tm_year, a.tm_yday):
        return f"oggi alle {ora}"
    ieri = time.localtime(adesso - 86400)
    if (t.tm_year, t.tm_yday) == (ieri.tm_year, ieri.tm_yday):
        return f"ieri alle {ora}"
    return f"il {t.tm_mday} {MESI[t.tm_mon - 1]} alle {ora}"


def _causa(tipo: str, righe: list[dict]) -> str | None:
    """Le parole della causa, o `None` se il codice non e' in tabella."""
    e = righe[0].get("errore")
    return CAUSE.get(tipo, {}).get(str(e)) if e else None


def _perche(tipo: str, righe: list[dict]) -> str:
    """« perche' <causa>», oppure «, per una ragione che e' nel diario»: la
    seconda e' vera e non spiega, che e' meglio di una spiegazione inventata."""
    causa = _causa(tipo, righe)
    return f" perche' {causa}" if causa else f", {IGNOTA}"


def _volte(n: int) -> str:
    return "una volta" if n == 1 else f"{n} volte"


def _nomi(righe: list[dict], campo: str) -> list[str]:
    return list(dict.fromkeys(str(r.get(campo) or "") for r in righe if r.get(campo)))


def _ripiego_voce(v: list[dict], adesso: float) -> str:
    base = "sono partito con la voce di ripiego" + _perche("ripiego_voce", v)
    return base if len(v) == 1 else f"{len(v)} volte {base}"


def _microfono_caduto(v: list[dict], adesso: float) -> str:
    ultima = _quando(max(float(r.get("ts", 0) or 0) for r in v), adesso)
    if len(v) == 1:
        return f"il microfono si e' chiuso da solo {ultima}" + _perche("microfono_caduto", v)
    return (f"il microfono si e' chiuso da solo {len(v)} volte, l'ultima {ultima}"
            + _perche("microfono_caduto", v))


def _t1_degradato(v: list[dict], adesso: float) -> str:
    causa = _causa("t1_degradato", v)
    if causa is None:
        return f"la sessione di Claude ha avuto un problema, {IGNOTA}"
    if v[0].get("errore") == "riavviato" and len(v) > 1:
        return f"{causa} {len(v)} volte"
    return causa if len(v) == 1 else f"{causa}, {_volte(len(v))}"


def _consolidamento(v: list[dict], adesso: float) -> str:
    base = "non ho messo in ordine gli appunti" + _perche("consolidamento", v)
    return base if len(v) == 1 else f"per {len(v)} notti {base}"


def _protocollo(v: list[dict], adesso: float) -> str:
    nomi = _nomi(v, "nome")
    perche = _perche("protocollo", v)
    if len(nomi) <= 1:
        chi = f"il protocollo {nomi[0]}" if nomi else "un protocollo"
        return f"{chi} non e' potuto girare{perche}"
    return f"i protocolli {_elenco(nomi)} non sono potuti girare{perche}"


def _mcp(v: list[dict], adesso: float) -> str:
    nomi = _nomi(v, "server")
    chi = (f"il server {nomi[0]}" if len(nomi) == 1 else
           f"i server {_elenco(nomi)}" if nomi else "un server")
    parole = _causa("mcp", v)
    return f"{parole} {chi}" if parole else f"{chi} ha avuto un problema, {IGNOTA}"


def _resoconto(v: list[dict], adesso: float) -> str:
    causa = _causa("resoconto", v) or f"il resoconto stesso ha avuto un problema, {IGNOTA}"
    return causa if len(v) == 1 else f"{len(v)} volte {causa}"


def _comando_fallito(v: list[dict], adesso: float) -> str:
    base = "un comando non e' riuscito" if len(v) == 1 else f"{len(v)} comandi non sono riusciti"
    if all(r.get("strada") == "nessuna" for r in v):
        return base + (", perche' non sapevo dove mandarlo" if len(v) == 1
                       else ", perche' non sapevo dove mandarli")
    return f"{base}, {IGNOTA}"


def _comando_smentito(v: list[dict], adesso: float) -> str:
    if len(v) == 1:
        return "un comando e' riuscito ma la verifica l'ha smentito"
    return f"{len(v)} comandi sono riusciti ma la verifica li ha smentiti"


def _senza_risposta(v: list[dict], adesso: float) -> str:
    return f"{_volte(len(v))} mi ha parlato e la sessione di Claude non c'era"


def _laboratorio(v: list[dict], adesso: float) -> str:
    """ADR-015. La causa e' testo libero nell'`errore` — T2 caduto, manifesto
    assente, un file toccato fuori dalla bozza — e sta nel diario, non qui."""
    if len(v) == 1:
        return f"una bozza nel laboratorio non e' andata a buon fine, {IGNOTA}"
    return f"{len(v)} bozze nel laboratorio non sono andate a buon fine, {IGNOTA}"


#: Le frasi, per tipo di guasto. **Allowlist, non formattatore generico**,
#: come `FRASI`: `tests/test_il_resoconto_al_risveglio.py` confronta queste
#: chiavi con i tipi che `Engine._annota_guasto` emette davvero, e un tipo
#: nuovo senza frase diventa rosso. Gli ultimi tre sono DERIVATI: righe che il
#: registro scriveva gia' — un tool con `ok=False`, un verdetto `fallito`,
#: una frase caduta senza T1 — e che nessuno rileggeva.
GUASTI: dict[str, Callable[[list[dict], float], str]] = {
    "ripiego_voce": _ripiego_voce,
    "microfono_caduto": _microfono_caduto,
    "t1_degradato": _t1_degradato,
    "consolidamento": _consolidamento,
    "protocollo": _protocollo,
    "mcp": _mcp,
    "resoconto": _resoconto,
    "comando_fallito": _comando_fallito,
    "comando_smentito": _comando_smentito,
    "senza_risposta": _senza_risposta,
    "laboratorio": _laboratorio,
}

#: I tre tipi derivati: non li emette nessuno con quel nome, li deduce
#: `tipo_di_guasto` dalla forma della riga.
DERIVATI = frozenset({"comando_fallito", "comando_smentito", "senza_risposta"})


def righe_dal(diario: Any, da: float) -> list[dict]:
    """Le righe del diario dopo `da`, di tutti i giorni da quello di `da`.

    Stesso taglio stretto di `MemoryStore.iniziative_dal` — `> da` — per la
    stessa ragione: rileggendo con il proprio timbro non si riferisce due volte
    lo stesso guasto.

    ⚠️ `Diario.leggi()` ha `limite=200` per il pannello: qui si passa un limite
    che non tronca, o un giorno pieno perderebbe la mattina.
    """
    giorno_da = time.strftime("%Y-%m-%d", time.localtime(da)) if da > 0 else ""
    fuori: list[dict] = []
    for g in diario.giorni():
        if g < giorno_da:
            continue
        for r in diario.leggi(g, None, limite=10 ** 9):
            try:
                ts = float(r.get("ts", 0) or 0)
            except (TypeError, ValueError):
                continue
            if ts > da:
                fuori.append(r)
    return fuori


def tipo_di_guasto(riga: dict) -> str | None:
    """Che tipo di guasto e' questa riga, o `None` se non lo e'.

    Un guasto e' `ok=False` oppure un verdetto `fallito` (ADR-012: «riuscito
    ma smentito» e' la riga per cui quel contratto esiste). Non lo sono: il
    resoconto stesso e il ciclo di vita; il no del Signore a una conferma; e
    `non_verificato`, che e' onesto, non rotto.
    """
    if riga.get("flusso") != "azione":
        return None
    intento = riga.get("intento")
    if intento in NON_GUASTI:
        return None
    ok = riga.get("ok")
    verdetto = riga.get("verdetto")
    if not (ok is False or verdetto == "fallito"):
        return None
    errore = riga.get("errore")
    if isinstance(errore, str) and errore.startswith("operazione ") \
            and errore[len("operazione "):] in ESITI_DI_CONFERMA:
        return None
    if intento in GUASTI and intento not in DERIVATI:
        return str(intento)
    if verdetto == "fallito":
        return "comando_smentito"
    if errore == "t1_assente":
        return "senza_risposta"
    return "comando_fallito"


def classifica_guasti(righe: list[dict], avviato_a: float) -> list[tuple[str, list[dict]]]:
    """I guasti, raggruppati per tipo e causa, nell'ordine in cui sono
    successi.

    ⚠️ Un `ripiego_voce` di QUESTO avvio non si conta: l'invariante 12 l'ha
    appena fatto dire a voce, e ripeterlo nel resoconto sarebbe la stessa cosa
    detta due volte nello stesso minuto. Quello di un avvio precedente — un
    riavvio nella notte — invece si dice, perche' nessuno l'ha sentito.
    """
    gruppi: dict[tuple[str, str | None], list[dict]] = {}
    for r in righe:
        tipo = tipo_di_guasto(r)
        if tipo is None:
            continue
        if tipo == "ripiego_voce" and float(r.get("ts", 0) or 0) >= avviato_a:
            continue
        errore = r.get("errore") if tipo not in DERIVATI else None
        gruppi.setdefault((tipo, str(errore) if errore is not None else None), []).append(r)
    return [(tipo, v) for (tipo, _), v in gruppi.items()]


@dataclass(frozen=True)
class Spento:
    """Da quando a quando JARVIS non c'era, letto dal diario."""

    #: Quando si e' riacceso: questo avvio.
    a: float
    #: L'ultimo `core_fermato` prima di questo avvio, se c'e'.
    da: float | None = None
    #: Senza `core_fermato`: l'ultima riga scritta prima di questo avvio.
    ultima: float | None = None
    #: Altri `core_avviato` nella finestra, prima di questo.
    riavvii: int = 0

    @property
    def pulito(self) -> bool:
        return self.da is not None

    @property
    def durata_s(self) -> float | None:
        inizio = self.da if self.da is not None else self.ultima
        return None if inizio is None else max(0.0, self.a - inizio)


def intervallo_spento(righe: list[dict], avviato_a: float, da: float) -> Spento | None:
    """Quando JARVIS era spento, oppure `None` se all'ultimo resoconto era gia'
    acceso — cioe' non c'e' niente da dire.

    Dal ciclo di vita nel diario, **mai dai buchi fra le righe**: dieci ore di
    silenzio possono essere JARVIS acceso e muto. L'ultimo evento del ciclo di
    vita prima di questo avvio decide: un `core_fermato` e' uno spegnimento
    pulito, un `core_avviato` e' un processo morto senza dirlo — e allora si
    dice l'ultima cosa scritta, e che lo spegnimento non e' registrato.
    """
    if avviato_a <= da:
        return None
    prima = [r for r in righe if float(r.get("ts", 0) or 0) < avviato_a]
    if not prima:
        # Il PRIMO avvio di sempre, o il primo da quando il diario esiste:
        # non c'e' uno spegnimento di cui parlare. Trovato in laboratorio, dove
        # il primo giro diceva «non ho registrato lo spegnimento» di un
        # processo che non era mai esistito.
        return None
    vita = [r for r in prima if r.get("intento") in ("core_avviato", "core_fermato")]
    riavvii = sum(1 for r in vita if r.get("intento") == "core_avviato")
    ultimo = max(vita, key=lambda r: float(r.get("ts", 0) or 0), default=None)
    if ultimo is not None and ultimo.get("intento") == "core_fermato":
        return Spento(a=avviato_a, da=float(ultimo["ts"]), riavvii=riavvii)
    ultima = max((float(r.get("ts", 0) or 0) for r in prima), default=None)
    return Spento(a=avviato_a, ultima=ultima, riavvii=riavvii)


def _frase_spento(s: Spento, adesso: float) -> str:
    if s.pulito:
        frase = f"Sono stato spento da {_quando(s.da, adesso)} a {_quando(s.a, adesso)}"
    elif s.ultima is not None:
        frase = ("Non ho registrato lo spegnimento: l'ultima cosa che ho scritto "
                 f"e' di {_quando(s.ultima, adesso)}, e mi sono riacceso "
                 f"{_quando(s.a, adesso)}")
    else:
        frase = f"Non ho registrato lo spegnimento, e mi sono riacceso {_quando(s.a, adesso)}"
    if s.riavvii == 1:
        frase += ", e mi sono riavviato un'altra volta"
    elif s.riavvii > 1:
        frase += f", e mi sono riavviato altre {s.riavvii} volte"
    return frase


def componi(fatte: list[dict], guasti: list[tuple[str, list[dict]]] | tuple = (),
            spento: Spento | None = None, adesso: float | None = None) -> str:
    """La frase, dai dati. Prosa: §5.7 vieta elenchi e markdown a voce.

    Tre parti, ognuna solo se ha qualcosa da dire: cio' che JARVIS ha fatto,
    da quando a quando era spento, che cosa non e' andato. Senza nessuna delle
    tre: «Niente da riferire, Signore.»
    """
    ora = time.time() if adesso is None else adesso
    frasi: list[str] = []
    if fatte:
        per_tipo: dict[str, list[dict]] = {}
        for f in fatte:
            per_tipo.setdefault(str(f.get("tipo") or "ignoto"), []).append(f)
        pezzi = []
        for tipo, righe in per_tipo.items():
            frase = FRASI.get(tipo)
            # Il ripiego dice il NUMERO e non finge di spiegare: meglio «due
            # cose che non so ancora raccontare» di una frase inventata su un
            # tipo che nessuno ha descritto.
            n = len(righe)
            pezzi.append(frase(righe) if frase else
                         f"{n} cosa che non so ancora raccontare" if n == 1 else
                         f"{n} cose che non so ancora raccontare")
        frasi.append(f"Mentre non c'era, Signore: {_elenco(pezzi)}.")
    if spento is not None:
        frase = _frase_spento(spento, ora)
        # In apertura porta il vocativo, e la maiuscola passa al «Signore».
        frasi.append((frase if fatte else "Signore, " + frase[0].lower() + frase[1:]) + ".")
    if guasti:
        pezzi = []
        for tipo, righe in guasti:
            f = GUASTI.get(tipo)
            n = len(righe)
            pezzi.append(f(righe, ora) if f else
                         f"{n} cosa che non so ancora raccontare" if n == 1 else
                         f"{n} cose che non so ancora raccontare")
        intro = ("E c'e' qualcosa che non e' andato" if frasi
                 else "Signore, qualcosa non e' andato mentre non c'era")
        frasi.append(f"{intro}: {_elenco(pezzi)}.")
    if not frasi:
        return "Niente da riferire, Signore."
    if spento is not None and not fatte and not guasti:
        frasi.append("Per il resto, niente da riferire.")
    return " ".join(frasi)


def _elenco(pezzi: list[str]) -> str:
    if len(pezzi) == 1:
        return pezzi[0]
    return ", ".join(pezzi[:-1]) + " e " + pezzi[-1]
