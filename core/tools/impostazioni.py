"""Scrivere `settings.toml` — SPEC §26.7.

`tomlkit` e' fra le dipendenze **dalla Fase 0**, col commento «TOML in lettura E
scrittura, commenti preservati». Fino a oggi `core/settings.py` lo usava solo
per `parse`: la scrittura era prevista e non e' mai stata fatta, e configurare
JARVIS voleva dire aprire un editor.

## Le cinque regole di §26.7, e dove stanno

1. **Scrive il core, mai il renderer** (invariante 1). Questo file e' il solo
   posto in cui `settings.toml` viene riscritto.
2. **Con `tomlkit`**, così che i commenti sopravvivano. Non e' un vezzo: quel
   file spiega *perche'* un valore e' quello, e meta' del suo valore sta li'.
   Un `tomllib.load` + `toml.dump` li cancellerebbe tutti al primo salvataggio.
3. **Un solo tool**, `imposta_valore`, `side_effect=True` e quindi con la
   conferma di §6.2: sta scrivendo nella configurazione di un sistema che apre
   un microfono e puo' eseguire codice.
4. **Quattro chiavi non si cambiano dall'interfaccia** — vedi `BLOCCATE`, che
   ne elenca cinque: la quinta e' aggiunta e dichiarata li'.
5. Il ricaricamento a caldo lo fa gia' `SettingsStore` con `watchdog`: qui non
   serve notificare nessuno, basta scrivere.

## L'allowlist si DERIVA dallo schema

`chiavi_modificabili()` cammina il modello pydantic invece di elencare a mano
le chiavi ammesse. Un elenco scritto a mano e' una seconda opinione su che cosa
esista, e diverge dal modello alla prima aggiunta — il difetto che questo
progetto ha gia' pagato coi tre ritagli, i due orologi e le due clamp.

Passano solo le **foglie scalari**: `int`, `float`, `bool`, `str`. Le strutture
— le scene, le frasi di wake, le radici consentite — non si toccano con un
`imposta_valore(chiave, valore)`, e fingere di poterlo fare produrrebbe un
errore a meta' scrittura invece che un rifiuto.

## Il file non si rompe mai a meta'

Due difese, e servono tutt'e due:

* **si valida prima di scrivere**: il documento modificato passa dal modello
  `Settings`, e se non passa non si scrive niente. Un `settings.toml` che non
  carica impedisce l'avvio del core, quindi qui un errore non e' un fastidio:
  e' un sistema che non parte piu';
* **si scrive per rinomina**: una scrittura interrotta a meta' lascerebbe il
  file troncato. Il come sta in `core/platform.scrivi_atomico`, e non qui:
  i bit di permesso che si conservano sono POSIX, e su Windows la stessa riga
  significherebbe un'altra cosa. Invariante 29, e l'ha trovato il suo
  controllo — `st_mode` scritto in questo file lo faceva scattare.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog
import tomlkit
from pydantic import BaseModel, Field, ValidationError

from core.platform import scrivi_atomico
from core.settings import SETTINGS_FILENAME, Settings
from core.tools.confirm import Operazione, Piano
from core.tools.registry import Tool, ToolResult, register

log = structlog.get_logger(__name__)

#: §26.7 regola 4. **Non si cambiano dall'interfaccia**, e non per prudenza
#: generica: sono gli interruttori che decidono se un sottosistema conseguente
#: **esiste**. `voice.enabled` apre un microfono, `code.enabled` mette
#: `esegui_codice` nell'allowlist, `vision.enabled` accende una telecamera, e
#: `fs.allowed_roots` decide quale parte del disco JARVIS possa vedere.
#:
#: Un clic distratto su una casella non e' il modo di prendere nessuna delle
#: quattro decisioni. La pagina le **mostra** e dice dove cambiarle.
BLOCCATE = frozenset({
    "voice.enabled",
    "code.enabled",
    "vision.enabled",
    "fs.allowed_roots",
    # ⚠️ **La quinta, aggiunta e dichiarata.** §26.7 ne nomina quattro; questa
    # ci sta per una ragione meccanica, non per prudenza: lo schema la dichiara
    # `Literal[True]` — invariante 4, «solo cestino, mai delete permanente» —
    # quindi l'unico cambiamento possibile e' uno che viene rifiutato. Un
    # comando che puo' solo fallire non e' un comando: e' un fatto, e i fatti
    # si mostrano.
    "fs.trash_only",
})

#: Non e' una chiave bloccata: e' un ramo che non deve nemmeno comparire.
#: `Secrets` porta `SecretStr`, e farlo passare di qui vorrebbe dire scrivere
#: una chiave API in chiaro in `settings.toml` — che per giunta e' il file coi
#: permessi larghi, mentre `secrets.toml` e' quello stretto.
RAMI_ESCLUSI = frozenset({"secrets"})

#: Le foglie che un `imposta_valore(chiave, valore)` sa scrivere.
_SCALARI = (bool, int, float, str)


def chiavi_modificabili(s: Settings) -> dict[str, Any]:
    """Le chiavi scalari che la pagina puo' offrire, col valore di adesso.

    Derivata dallo schema, non elencata: vedi l'intestazione. Le bloccate di
    §26.7 non compaiono — la pagina le mostra da `chiavi_bloccate()`, che e'
    un elenco diverso perche' e' una cosa diversa: quelle si guardano.
    """
    fuori: dict[str, Any] = {}

    def cammina(modello: BaseModel, prefisso: str) -> None:
        for nome in type(modello).model_fields:
            valore = getattr(modello, nome)
            chiave = f"{prefisso}{nome}"
            if chiave in RAMI_ESCLUSI or nome in RAMI_ESCLUSI:
                continue
            if isinstance(valore, BaseModel):
                cammina(valore, f"{chiave}.")
            # `bool` prima di `int`: in Python `True` E' un `int`, e senza
            # questo ordine un interruttore verrebbe offerto come numero.
            elif isinstance(valore, _SCALARI) and chiave not in BLOCCATE:
                fuori[chiave] = valore
        return

    cammina(s, "")
    return fuori


def chiavi_bloccate(s: Settings) -> dict[str, Any]:
    """Le quattro di §26.7 col loro valore, per mostrarle senza offrirle."""
    fuori: dict[str, Any] = {}
    for chiave in sorted(BLOCCATE):
        nodo: Any = s
        for pezzo in chiave.split("."):
            nodo = getattr(nodo, pezzo, None)
            if nodo is None:
                break
        if isinstance(nodo, (list, tuple)):
            nodo = [str(x) for x in nodo]
        elif isinstance(nodo, Path):
            nodo = str(nodo)
        fuori[chiave] = nodo
    return fuori


class ImpostaArgs(BaseModel):
    chiave: str = Field(min_length=3, max_length=64,
                        pattern=r"^[a-z_]+(?:\.[a-z_]+)+$")
    valore: bool | int | float | str


def _documento(percorso: Path) -> tomlkit.TOMLDocument:
    return tomlkit.parse(percorso.read_text(encoding="utf-8"))


def _tipo_atteso(s: Settings, chiave: str) -> type | None:
    """Il tipo della foglia secondo il modello, non secondo il file.

    Il file potrebbe non contenere ancora la chiave — un valore predefinito non
    scritto — e in quel caso il tipo lo sa solo lo schema.
    """
    valore = chiavi_modificabili(s).get(chiave)
    return type(valore) if valore is not None else None


def _converti(grezzo: Any, atteso: type | None) -> Any:
    """Porta il valore al tipo dello schema, o lo lascia stare.

    Serve perche' dall'interfaccia i numeri arrivano volentieri come stringhe.
    Non e' permissivita': se la conversione non riesce, il valore passa com'e'
    e sara' il modello a bocciarlo — con un messaggio suo, che e' migliore di
    uno inventato qui.
    """
    if atteso is None or isinstance(grezzo, atteso) and not (
            atteso is not bool and isinstance(grezzo, bool)):
        return grezzo
    try:
        if atteso is bool:
            if isinstance(grezzo, str):
                if grezzo.strip().lower() in {"true", "vero", "1", "si", "sì"}:
                    return True
                if grezzo.strip().lower() in {"false", "falso", "0", "no"}:
                    return False
                return grezzo
            return bool(grezzo)
        if atteso is int:
            return int(str(grezzo).strip())
        if atteso is float:
            return float(str(grezzo).strip())
        if atteso is str:
            return str(grezzo)
    except (TypeError, ValueError):
        return grezzo
    return grezzo


def _posa(doc: Any, chiave: str, valore: Any) -> None:
    """Scrive la foglia dentro il documento tomlkit, creando le tabelle che
    mancano. Una sezione assente e' il caso normale per le chiavi con un
    predefinito: `meteo` e `code` non sono nel file di chi non le usa."""
    pezzi = chiave.split(".")
    nodo = doc
    for p in pezzi[:-1]:
        if p not in nodo:
            nodo[p] = tomlkit.table()
        nodo = nodo[p]
    nodo[pezzi[-1]] = valore


def imposta(percorso: Path, chiave: str, valore: Any, *,
            corrente: Settings) -> Any:
    """Scrive UNA chiave. Ritorna il valore come e' stato scritto.

    Solleva `ValueError` con un messaggio leggibile — mai un'eccezione nuda —
    perche' il chiamante e' un tool e §*Stile codice* vieta che un'eccezione
    propaghi all'LLM.
    """
    if chiave in BLOCCATE:
        raise ValueError(
            f"{chiave} non si cambia dall'interfaccia (§26.7 regola 4): decide "
            f"se un sottosistema esiste. Si cambia in {percorso}, con un "
            "editor, deliberatamente."
        )
    ammesse = chiavi_modificabili(corrente)
    if chiave not in ammesse:
        raise ValueError(
            f"{chiave} non e' una chiave scalare delle impostazioni. "
            f"Modificabili: {len(ammesse)} chiavi, per esempio "
            f"{', '.join(sorted(ammesse)[:3])}."
        )

    convertito = _converti(valore, _tipo_atteso(corrente, chiave))
    doc = _documento(percorso)
    _posa(doc, chiave, convertito)

    # ⚠️ Si VALIDA prima di scrivere. Un `settings.toml` che non carica non e'
    # un fastidio: e' un core che non parte piu'.
    grezzo = doc.unwrap()
    grezzo.pop("secrets", None)
    try:
        Settings.model_validate(grezzo)
    except ValidationError as exc:
        prima = exc.errors()[0]
        raise ValueError(
            f"{chiave} = {convertito!r} non e' valido: "
            f"{prima.get('msg', 'valore rifiutato dallo schema')}"
        ) from exc

    scrivi_atomico(percorso, tomlkit.dumps(doc))
    log.info("impostazione_scritta", chiave=chiave, valore=convertito)
    return convertito


def register_settings_tool(leggi_settings: Callable[[], Settings],
                           leggi_config_dir: Callable[[], Path]) -> None:
    """§26.7 regola 3: **un solo tool**, e con la conferma."""

    def _percorso() -> Path:
        return leggi_config_dir() / SETTINGS_FILENAME

    async def _piano(a: ImpostaArgs) -> Piano:
        p = _percorso()
        adesso = chiavi_modificabili(leggi_settings()).get(a.chiave, "—")
        return Piano(
            tool="imposta_valore",
            riepilogo=f"cambia {a.chiave}: {adesso!r} → {a.valore!r}",
            # `destinazione` col percorso RISOLTO, come vuole l'invariante 3:
            # chi conferma deve vedere quale file sta per cambiare.
            operazioni=(Operazione(tipo="write", destinazione=p,
                                   dettaglio=f"{a.chiave} = {a.valore!r}"),),
        )

    async def _handler(a: ImpostaArgs, _piano: Piano) -> ToolResult:
        try:
            scritto = imposta(_percorso(), a.chiave, a.valore,
                              corrente=leggi_settings())
        except (ValueError, OSError) as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(ok=True, output={"chiave": a.chiave, "valore": scritto,
                                           "file": str(_percorso())})

    register(Tool(
        name="imposta_valore",
        description="Cambia una impostazione in settings.toml, conservando i commenti.",
        args_schema=ImpostaArgs, side_effect=True,
        planner=_piano, handler=_handler,
    ))
