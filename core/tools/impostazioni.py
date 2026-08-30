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
from typing import Any, Literal

import structlog
import tomlkit
from pydantic import BaseModel, Field, ValidationError, model_validator

from core.platform import scrivi_atomico
from core.settings import SETTINGS_FILENAME, Settings
from core.tools.confirm import Operazione, Piano
from core.tools.registry import Tool, ToolResult, register
from core.verifica import Verifica

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
    # ⚠️ **`fs.allowed_roots` NON e' piu' qui, ed e' una decisione presa il 30
    # agosto 2026.** Decideva quale parte del disco JARVIS vede, e per questo
    # §26.7 regola 4 la teneva fra le bloccate. Adesso si cambia dalla pagina,
    # ma **un elemento per volta** e con la conferma di §6.2 che mostra il
    # percorso **RISOLTO**: chi approva legge la cartella vera, non la stringa
    # che ha digitato. La difesa che si perde e' «dalla pagina non si puo'
    # nemmeno chiedere»; quella che resta e' l'invariante 3, che e' la difesa
    # che il progetto ha scelto ovunque altro.
    #
    # E resta impossibile **sostituire** l'elenco in un colpo: il messaggio
    # porta un elemento e un verbo, mai la lista. Vedi `imposta_elemento`.
    # ⚠️ **La quinta, aggiunta e dichiarata.** §26.7 ne nomina quattro; questa
    # ci sta per una ragione meccanica, non per prudenza: lo schema la dichiara
    # `Literal[True]` — invariante 4, «solo cestino, mai delete permanente» —
    # quindi l'unico cambiamento possibile e' uno che viene rifiutato. Un
    # comando che puo' solo fallire non e' un comando: e' un fatto, e i fatti
    # si mostrano.
    "fs.trash_only",
    # ⚠️ **La sesta, ADR-007.** Accenderla vuol dire avviare PROGRAMMI DI
    # TERZI e mettere dei loro tool a portata dell'LLM: e' la stessa specie di
    # decisione di `voice.enabled` e `code.enabled`, e si prende nello stesso
    # modo — scrivendo nel file, non cliccando una casella.
    "mcp.enabled",
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


#: Le liste che si possono cambiare **un elemento per volta**, col tipo del
#: loro elemento. Derivate dallo schema come `chiavi_modificabili`, non
#: elencate a mano: un elenco scritto qui divergerebbe dal giorno in cui
#: qualcuno aggiunge una sezione.
def chiavi_lista(s: Settings) -> dict[str, list[Any]]:
    """Le liste offerte dalla pagina, col contenuto di adesso.

    ⚠️ **Non tutte le liste dello schema, e il filtro e' DERIVATO.**
    Una lista si offre solo se il suo elemento e' piatto: uno scalare, o un
    record i cui campi sono tutti scalari. `ElementoMessage.elemento` e' un
    `dict[str, str]` — un record e' quel che passa il ponte, e un campo
    annidato non ci sta.

    Escluse per costruzione, non per elenco: `ui.scene` (record dentro record),
    `mcp.servers` (idem, e si accende con `mcp.enabled`, che e' bloccata) e
    **`protocolli`**, che ha un `args: dict`.

    ⚠️ Il filtro era un elenco scritto a mano, e ci avevo messo `protocolli`:
    la pagina l'avrebbe offerto e il ponte l'avrebbe rifiutato a meta' —
    **esattamente il difetto che questa fetta chiude**, commesso mentre la si
    chiudeva. L'ha trovato un test, non una rilettura. Derivarlo dallo schema
    toglie la classe intera di errore.
    """
    fuori: dict[str, list[Any]] = {}

    def cammina(modello: BaseModel, prefisso: str) -> None:
        for nome in type(modello).model_fields:
            valore = getattr(modello, nome)
            chiave = f"{prefisso}{nome}"
            if chiave in RAMI_ESCLUSI or nome in RAMI_ESCLUSI:
                continue
            if isinstance(valore, BaseModel):
                cammina(valore, f"{chiave}.")
            elif isinstance(valore, (list, tuple)) and _piatta(s, chiave, valore):
                fuori[chiave] = [_come_dizionario(x) for x in valore]

    cammina(s, "")
    return fuori


def _piatta(s: Settings, chiave: str, valore: Any) -> bool:
    """Se gli elementi di questa lista attraversano il ponte.

    Scalari sempre; record solo se **tutti** i loro campi sono scalari.
    `mcp.enabled` blocca la propria sezione a monte, quindi `mcp.servers` non
    si offre nemmeno se un giorno diventasse piatta.
    """
    if chiave.split(".")[0] in {"mcp"}:
        return False
    tipo = _tipo_elemento(s, chiave)
    if tipo is None:
        # Lista di scalari: si offre solo se c'e' gia' un elemento o se lo
        # schema non dichiara un record. Una lista vuota e senza tipo non ha
        # una forma da mostrare, e offrirla darebbe un campo che non si sa
        # come si chiama.
        return bool(valore) or True
    return all(
        isinstance(campo.annotation, type)
        and issubclass(campo.annotation, (bool, int, float, str))
        for campo in tipo.model_fields.values()
    )


def _come_dizionario(elemento: Any) -> dict[str, Any]:
    """Un elemento di lista nella forma che la pagina mostra e rimanda.

    Le liste sono di due specie e vanno unificate qui, o ogni chiamante
    dovrebbe conoscerle: un record (`WakePhrase`) diventa i suoi campi, uno
    scalare (`Path`) diventa `{"valore": "..."}`.
    """
    if isinstance(elemento, BaseModel):
        return {k: (str(v) if isinstance(v, Path) else v)
                for k, v in elemento.model_dump().items()}
    return {"valore": str(elemento)}


def _tipo_elemento(s: Settings, chiave: str) -> Any:
    """Il tipo dichiarato degli elementi di una lista. `None` se scalare."""
    nodo: Any = s
    for pezzo in chiave.split("."):
        nodo = getattr(nodo, pezzo, None)
        if nodo is None:
            return None
    if isinstance(nodo, (list, tuple)) and nodo and isinstance(nodo[0], BaseModel):
        return type(nodo[0])
    # Una lista vuota non dice il proprio tipo: lo si chiede allo SCHEMA, che e'
    # l'unico posto in cui e' dichiarato anche quando non c'e' un elemento.
    padre: Any = s
    pezzi = chiave.split(".")
    for pezzo in pezzi[:-1]:
        padre = getattr(padre, pezzo)
    campo = type(padre).model_fields.get(pezzi[-1])
    dentro = getattr(campo, "annotation", None)
    argomenti = getattr(dentro, "__args__", ())
    for a in argomenti:
        if isinstance(a, type) and issubclass(a, BaseModel):
            return a
    return None


def imposta_elemento(percorso: Path, chiave: str, operazione: str,
                     elemento: dict[str, Any], *, corrente: Settings) -> list[Any]:
    """Aggiunge o toglie **UN** elemento da una lista. Mai la lista intera.

    ⚠️ **La differenza non e' di comodita': e' il confine.**
    `core/ws_server.py` dichiara perche' una lista non attraversa il ponte —
    «verrebbe scritta da tomlkit **senza passare da nessuno schema di
    sezione**, e sarebbe una strada per riscrivere una struttura con un
    messaggio che dichiara di cambiare uno scalare». Qui la struttura non si
    riscrive: arriva **un record**, lo si valida contro il tipo dichiarato
    dallo schema, lo si somma o sottrae alla lista che c'e' gia', e **poi** si
    valida `Settings` intero prima di toccare il disco. Nessun byte raggiunge
    `settings.toml` senza aver attraversato due schemi.

    Solleva `ValueError` con un messaggio leggibile: il chiamante e' un tool.
    """
    if operazione not in ("aggiungi", "togli"):
        raise ValueError(f"operazione {operazione!r} sconosciuta: "
                         "si aggiunge o si toglie")
    liste = chiavi_lista(corrente)
    if chiave not in liste:
        raise ValueError(
            f"{chiave} non e' una lista modificabile. Ci sono: "
            f"{', '.join(sorted(liste)) or '(nessuna)'}"
        )

    tipo = _tipo_elemento(corrente, chiave)
    if tipo is not None:
        try:
            nuovo = tipo.model_validate(elemento).model_dump()
        except ValidationError as exc:
            prima = exc.errors()[0]
            raise ValueError(
                f"l'elemento non e' un {tipo.__name__} valido: "
                f"{'.'.join(str(x) for x in prima.get('loc', ()))} "
                f"{prima.get('msg', '')}".strip()
            ) from exc
        nuovo = {k: (str(v) if isinstance(v, Path) else v) for k, v in nuovo.items()}
    else:
        if set(elemento) != {"valore"}:
            raise ValueError(
                f"{chiave} e' una lista di valori semplici: l'elemento si "
                'manda come {"valore": "..."}'
            )
        nuovo = {"valore": str(elemento["valore"])}

    adesso = list(liste[chiave])
    if operazione == "aggiungi":
        if nuovo in adesso:
            raise ValueError(f"{chiave} contiene gia' questo elemento")
        adesso.append(nuovo)
    else:
        if nuovo not in adesso:
            raise ValueError(f"{chiave} non contiene questo elemento")
        adesso.remove(nuovo)

    da_scrivere = ([d["valore"] for d in adesso] if tipo is None
                   else [dict(d) for d in adesso])
    doc = _documento(percorso)
    _posa(doc, chiave, da_scrivere)

    # ⚠️ Si VALIDA prima di scrivere, come `imposta()`. Un `settings.toml` che
    # non carica non e' un fastidio: e' un core che non parte piu'.
    grezzo = doc.unwrap()
    grezzo.pop("secrets", None)
    try:
        Settings.model_validate(grezzo)
    except ValidationError as exc:
        prima = exc.errors()[0]
        raise ValueError(
            f"{chiave} non e' valido dopo la modifica: "
            f"{prima.get('msg', 'rifiutato dallo schema')}"
        ) from exc

    scrivi_atomico(percorso, tomlkit.dumps(doc))
    log.info("elemento_impostato", chiave=chiave, operazione=operazione,
             elementi=len(da_scrivere))
    return da_scrivere


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
    """Due forme, e una sola alla volta.

    ⚠️ **Un solo tool** — §26.7 regola 3 — quindi le due strade stanno qui e
    non in due registrazioni. La foglia porta `valore`; la lista porta
    `operazione` piu' `elemento`, e **mai** l'elenco intero: vedi
    `imposta_elemento` per la ragione, che e' il confine e non la comodita'.
    """

    chiave: str = Field(min_length=3, max_length=64,
                        pattern=r"^[a-z_]+(?:\.[a-z_]+)+$")
    valore: bool | int | float | str | None = None
    operazione: Literal["aggiungi", "togli"] | None = None
    #: I campi del record, gia' come stringhe. Uno scalare viaggia come
    #: `{"valore": "..."}`: una forma sola per due specie di lista, o ogni
    #: chiamante dovrebbe conoscerle.
    elemento: dict[str, str] | None = None

    @model_validator(mode="after")
    def _una_forma_sola(self) -> "ImpostaArgs":
        lista = self.operazione is not None or self.elemento is not None
        if lista and self.valore is not None:
            raise ValueError("o si cambia una foglia (`valore`) o si tocca una "
                             "lista (`operazione` + `elemento`): non tutt'e due")
        if lista and (self.operazione is None or self.elemento is None):
            raise ValueError("per una lista servono sia `operazione` sia "
                             "`elemento`")
        if not lista and self.valore is None:
            raise ValueError("manca `valore`")
        return self


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
        if a.operazione is not None:
            return _piano_elemento(a, p)
        adesso = chiavi_modificabili(leggi_settings()).get(a.chiave, "—")
        return Piano(
            tool="imposta_valore",
            riepilogo=f"cambia {a.chiave}: {adesso!r} → {a.valore!r}",
            # `destinazione` col percorso RISOLTO, come vuole l'invariante 3:
            # chi conferma deve vedere quale file sta per cambiare.
            operazioni=(Operazione(tipo="write", destinazione=p,
                                   dettaglio=f"{a.chiave} = {a.valore!r}"),),
        )

    def _piano_elemento(a: ImpostaArgs, p: Path) -> Piano:
        """Il piano per una lista. **Due operazioni, non una.**

        ⚠️ **Il percorso RISOLTO, e per `fs.allowed_roots` e' il punto della
        decisione.** Quella chiave e' uscita dalle bloccate di §26.7 il 30
        agosto 2026, e la condizione era che «la conferma deve mostrarle
        risolte e una per una». Chi approva deve leggere la CARTELLA VERA, non
        la stringa che ha digitato: `~/../..` e un symlink si scrivono uguali e
        arrivano altrove.
        """
        elemento = dict(a.elemento or {})
        verbo = "aggiunge a" if a.operazione == "aggiungi" else "toglie da"
        descrizione = ", ".join(f"{k}={v!r}" for k, v in sorted(elemento.items()))
        operazioni = [Operazione(
            tipo="write", destinazione=p,
            dettaglio=f"{a.chiave}: {a.operazione} {descrizione}")]
        if a.chiave == "fs.allowed_roots" and "valore" in elemento:
            # La SECONDA operazione esiste per farsi leggere: il piano mostra
            # la radice risolta come una riga sua, non nascosta in una stringa
            # di dettaglio insieme al resto.
            risolta = Path(elemento["valore"]).expanduser()
            try:
                risolta = risolta.resolve()
            except OSError:                       # pragma: no cover
                pass
            operazioni.append(Operazione(
                tipo="perimetro", destinazione=risolta,
                dettaglio=("JARVIS potra' leggere e scrivere qui dentro"
                           if a.operazione == "aggiungi"
                           else "JARVIS non vedra' piu' questa cartella")))
        return Piano(
            tool="imposta_valore",
            riepilogo=f"{verbo} {a.chiave}: {descrizione}",
            operazioni=tuple(operazioni),
        )

    async def _handler(a: ImpostaArgs, _piano: Piano) -> ToolResult:
        try:
            if a.operazione is not None:
                scritto = imposta_elemento(_percorso(), a.chiave, a.operazione,
                                           dict(a.elemento or {}),
                                           corrente=leggi_settings())
            else:
                scritto = imposta(_percorso(), a.chiave, a.valore,
                                  corrente=leggi_settings())
        except (ValueError, OSError) as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(ok=True, output={"chiave": a.chiave, "valore": scritto,
                                           "file": str(_percorso())})

    def _verifica(a: ImpostaArgs, _piano: Piano, r: ToolResult) -> Verifica:
        """Il TOML riletto **dal disco** contiene il valore, e ha ancora commenti.

        Fonte indipendente: il file riaperto con `tomlkit`, non il valore che
        `imposta()` dice di aver scritto. Se `imposta()` scrivesse nel posto
        sbagliato, se la scrittura atomica lasciasse il temporaneo, se un
        `os.replace` fallisse a meta', questo se ne accorgerebbe — il referto
        del tool no, perche' il referto e' il tool che parla di se'.

        ⚠️ **La meta' sui commenti e' DEBOLE, e va detto.** ADR-012 chiede «e i
        commenti ci sono ancora». Senza un conteggio di PRIMA si puo' solo
        verificare che non siano spariti **tutti**. Il caso reale e' comunque
        coperto — un file di impostazioni i commenti li perde in blocco, quando
        qualcuno sostituisce `tomlkit` con un `toml.dump` che non li conserva —
        ma un commento perso su venti non lo vedrei.

        Dichiarato debole invece che spacciato per forte: e' la regola di
        ADR-012, ed e' l'unica riga di questo modulo che vale la pena rileggere
        fra sei mesi. Un verificatore debole dichiarato vale piu' di un
        verificatore forte finto.
        """
        if not r.ok:
            return Verifica.non_verificata(
                f"imposta_valore dichiara di non aver scritto ({r.error}); "
                "senza uno stato di partenza non si distingue «non fatto» da "
                "«fatto e disfatto»",
                fonte="registry.invoke")
        scritto = (r.output or {}).get("valore")
        percorso = _percorso()
        try:
            testo = percorso.read_text(encoding="utf-8")
            doc = tomlkit.parse(testo)
        except Exception as exc:
            return Verifica.non_verificata(
                f"il file non si e' potuto rileggere: {type(exc).__name__}: {exc}",
                fonte="settings.toml riletto dal disco")

        nodo: Any = doc
        for pezzo in a.chiave.split("."):
            nodo = nodo.get(pezzo) if hasattr(nodo, "get") else None
            if nodo is None:
                break
        letto = nodo.unwrap() if hasattr(nodo, "unwrap") else nodo
        commenti = sum(1 for riga in testo.splitlines()
                       if riga.lstrip().startswith("#"))
        return Verifica.confronta(
            atteso=f"{a.chiave} = {scritto!r} sul disco, con i commenti",
            osservato=f"{a.chiave} = {letto!r} sul disco, "
                      + ("con i commenti" if commenti
                         else "e i commenti sono SPARITI TUTTI"),
            fonte="settings.toml riletto dal disco con tomlkit")

    register(Tool(
        name="imposta_valore",
        description="Cambia una impostazione in settings.toml, conservando i commenti.",
        args_schema=ImpostaArgs, side_effect=True,
        planner=_piano, handler=_handler, verifica=_verifica,
    ))
