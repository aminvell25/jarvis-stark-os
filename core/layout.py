"""Il layout dell'ambiente — §26.10 punto 1, prerequisito di §26.5.

## Perche' non e' un tool

`tools/registry.py` e' l'allowlist di cio' che **l'LLM invoca**. Questo non lo
invoca nessuno: e' l'ambiente che ricorda se stesso, come il ricaricamento a
caldo delle impostazioni. Le due strade sbagliate si escludono da sole:

  `side_effect=True`   una conferma a ogni pannello spostato
  `side_effect=False`  un tool nell'elenco che l'LLM riceve, senza motivo

Quindi **non passa dal registry affatto**. Il canale e' `ui.layout` sul socket,
e chi lo riceve e' il `WsServer`.

## Perche' non sta in settings.toml

`settings.toml` e' **intenzione umana**: ogni valore ha accanto un commento che
spiega perche' e' quello, e `tomlkit` sta fra le dipendenze proprio per non
perderli. Questo file e' **stato della macchina**, cambia a ogni finestra
spostata, e nessuno lo legge per capire una decisione. Metterli insieme
vorrebbe dire riscrivere il primo a ogni trascinamento.

Sta in `paths.data_dir()`, accanto a `memory_data`, in JSON.

## L'invariante 1

Il renderer non scrive su disco. Manda la propria geometria e il core decide se
e come metterla giu' — compreso rifiutare quello che non passa lo schema.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

log = structlog.get_logger(__name__)

NOME_FILE = "layout.json"

#: Un identificatore dell'ambiente: id di pannello, di icona, di cartella.
#: Ristretto perche' finisce in un nome di chiave e in un log, e perche' un
#: id che puo' contenere qualunque cosa e' un id che un giorno conterra' un
#: percorso.
ID = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_.-]*$")

#: Coordinate. I limiti non sono prudenza generica: sono la ragione per cui un
#: renderer che sbaglia non puo' scrivere `x = 1e9` sul disco del core.
COORD = Field(ge=-32768, le=32768)
DIM = Field(ge=1, le=32768)


class _Stretto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeometriaPannello(_Stretto):
    """Dove sta un pannello, e in che stato."""

    id: str = ID
    x: int = COORD
    y: int = COORD
    larghezza: int = DIM
    altezza: int = DIM
    #: L'ordine di sovrapposizione. §26.2: la pila non si riordina da sola,
    #: quindi va ricordata com'era.
    z: int = Field(default=0, ge=0, le=10_000)
    massimizzato: bool = False


class IconaLibera(_Stretto):
    """§26.5 — un'icona lasciata sul fondo della scrivania.

    ⚠️ **Non c'e' ancora niente che la produca**, ed e' voluto: arriva al punto
    5 di §26.10. Sta qui adesso perche' aggiungere un campo a uno schema
    versionato dopo che il file esiste sul disco di qualcuno costa una
    migrazione, e questo file esistera' da domani.
    """

    id: str = ID
    x: int = COORD
    y: int = COORD
    #: La cartella che la contiene, o `None` se sta sul fondo.
    dentro: str | None = None


class CartellaLibera(_Stretto):
    """§26.5 — una cartella manila sul fondo.

    ⚠️ **Non e' una cartella del filesystem.** E' un raggruppamento
    dell'ambiente: §26.5 lo dice a chiare lettere, ed e' la distinzione che
    impedisce di cancellare qualcosa credendo di riordinare una scrivania.
    Nessun percorso entra qui dentro — solo id di icone.
    """

    id: str = ID
    x: int = COORD
    y: int = COORD
    etichetta: str = Field(default="", max_length=64)
    aperta: bool = False


class Layout(_Stretto):
    """Tutto cio' che l'ambiente ricorda di se stesso.

    `versione` esiste per poter cambiare idea: un file scritto oggi e letto da
    un domani che ha campi diversi deve poter essere riconosciuto e non solo
    rifiutato.
    """

    versione: Literal[1] = 1
    pannelli: list[GeometriaPannello] = Field(default_factory=list, max_length=64)
    #: Il posto per il punto 5. Vuoti finche' non c'e' chi li riempie.
    icone: list[IconaLibera] = Field(default_factory=list, max_length=256)
    cartelle: list[CartellaLibera] = Field(default_factory=list, max_length=64)
    #: §26.6 — la scena attiva, se ce n'e' una.
    scena: str | None = Field(default=None, max_length=64)
    #: L'area in cui questa geometria e' stata misurata. Serve al ripristino:
    #: uno schermo diverso non e' un errore, e senza sapere quanto era grande
    #: non si distingue «fuori area» da «area cambiata».
    area_larghezza: int | None = Field(default=None, ge=1, le=32768)
    area_altezza: int | None = Field(default=None, ge=1, le=32768)

    def vuoto(self) -> bool:
        return not (self.pannelli or self.icone or self.cartelle)


def adatta(layout: Layout, larghezza: int, altezza: int,
           minimo_visibile: int = 80) -> Layout:
    """Riporta dentro l'area cio' che ne e' uscito. **Non scarta.**

    Un pannello a `x = 3000` su uno schermo largo 1536 non e' un errore di cui
    incolpare l'utente: e' uno schermo cambiato, o una finestra rimpicciolita.
    Scartarlo vorrebbe dire perdere la disposizione proprio quando serve di
    piu'; lasciarlo dov'e' vorrebbe dire un pannello aperto e irraggiungibile,
    che e' peggio ancora.

    `minimo_visibile` e' quanto di un pannello deve restare a schermo perche'
    la sua testa — cioe' la maniglia con cui lo si riprende — sia afferrabile.
    """
    fuori: list[GeometriaPannello] = []
    for p in layout.pannelli:
        w = min(p.larghezza, larghezza)
        h = min(p.altezza, altezza)
        fuori.append(p.model_copy(update={
            "larghezza": w,
            "altezza": h,
            "x": max(0, min(p.x, larghezza - minimo_visibile)),
            "y": max(0, min(p.y, altezza - minimo_visibile)),
        }))
    dentro = lambda v, tetto: max(0, min(v, tetto - minimo_visibile))  # noqa: E731
    return layout.model_copy(update={
        "pannelli": fuori,
        "icone": [i.model_copy(update={"x": dentro(i.x, larghezza),
                                       "y": dentro(i.y, altezza)})
                  for i in layout.icone],
        "cartelle": [c.model_copy(update={"x": dentro(c.x, larghezza),
                                          "y": dentro(c.y, altezza)})
                     for c in layout.cartelle],
        "area_larghezza": larghezza,
        "area_altezza": altezza,
    })


class LayoutStore:
    """Legge e scrive `layout.json`. **Non solleva mai verso l'avvio.**

    Un core che non parte per una virgola di troppo in un file di stato e'
    inaccettabile: la disposizione delle finestre non e' un dato di cui valga
    la pena rifiutare di accendere il sistema.
    """

    #: Il tempo minimo fra due scritture su disco.
    #:
    #: ⚠️ **Il debounce del renderer non e' una difesa.** Il renderer aspetta
    #: 500 ms dopo l'ultimo movimento perche' e' educato; un renderer
    #: compromesso — e in Fase 6 ne ospita uno con `<webview>` — sceglie di non
    #: esserlo. Questo e' il freno che non dipende da chi parla: le scritture
    #: in eccesso si FONDONO, non si perdono, e l'ultima arriva col messaggio
    #: successivo o alla chiusura.
    MIN_INTERVALLO_S = 0.25

    def __init__(self, percorso: Path) -> None:
        self._percorso = Path(percorso)
        self._ultima_scrittura = 0.0
        self._in_attesa: Layout | None = None
        #: Dichiarato invece che taciuto: chi guarda lo snapshot deve poter
        #: sapere che c'e' stato un file corrotto e dove e' finito.
        self.corrotto_in: Path | None = None

    @property
    def percorso(self) -> Path:
        return self._percorso

    # ── lettura ──────────────────────────────────────────────────────────────

    def carica(self) -> Layout:
        """Il layout salvato, o uno vuoto. Quattro esiti, tutti dichiarati."""
        if not self._percorso.exists():
            log.info("layout_assente", file=str(self._percorso),
                     conseguenza="si parte dalla disposizione di moduli.js")
            return Layout()
        try:
            grezzo = self._percorso.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("layout_non_leggibile", errore=str(exc)[:120])
            return Layout()
        try:
            return Layout.model_validate_json(grezzo)
        except (ValidationError, ValueError) as exc:
            return self._metti_da_parte(exc)

    def _metti_da_parte(self, exc: Exception) -> Layout:
        """Rinomina il file illeggibile e riparte pulito, DICENDOLO.

        Non si cancella: se domani si vuole capire come si e' rotto, il file
        deve esistere ancora. Un solo `.corrotto` e non una collezione
        numerata — l'ultimo guasto e' quello che si va a guardare, e una
        directory che accumula file rotti e' un altro modo di perdere spazio in
        silenzio.
        """
        bersaglio = self._percorso.with_suffix(self._percorso.suffix + ".corrotto")
        try:
            os.replace(self._percorso, bersaglio)
            self.corrotto_in = bersaglio
        except OSError as errore:
            log.warning("layout_corrotto_non_spostabile", errore=str(errore)[:120])
            bersaglio = None
        log.warning("layout_corrotto", errore=str(exc)[:200],
                    spostato_in=str(bersaglio) if bersaglio else None,
                    conseguenza="si riparte dalla disposizione di moduli.js")
        return Layout()

    # ── scrittura ────────────────────────────────────────────────────────────

    def salva(self, layout: Layout, ora: float | None = None) -> bool:
        """Mette giu' il layout. Ritorna se ha toccato il disco.

        Sotto `MIN_INTERVALLO_S` non scrive e TIENE: il valore resta in attesa
        e va giu' col prossimo `salva()` o con `chiudi()`. Fondere e' diverso
        da scartare — con lo scarto l'ultima posizione di un trascinamento
        veloce si perderebbe, che e' esattamente il caso in cui l'utente sta
        guardando.
        """
        adesso = time.monotonic() if ora is None else ora
        if adesso - self._ultima_scrittura < self.MIN_INTERVALLO_S:
            self._in_attesa = layout
            return False
        self._in_attesa = None
        self._ultima_scrittura = adesso
        return self._scrivi(layout)

    def chiudi(self) -> bool:
        """Mette giu' cio' che era rimasto in attesa. Da chiamare allo stop."""
        if self._in_attesa is None:
            return False
        layout, self._in_attesa = self._in_attesa, None
        return self._scrivi(layout)

    def _scrivi(self, layout: Layout) -> bool:
        """Scrittura ATOMICA: temporaneo piu' `os.replace()`.

        Senza, un'interruzione a meta' lascia un JSON troncato — cioe'
        esattamente il file corrotto che `_metti_da_parte()` esiste per
        raccogliere. Meglio non produrlo.
        """
        tmp = self._percorso.with_suffix(self._percorso.suffix + ".tmp")
        try:
            self._percorso.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(layout.model_dump_json(indent=1), encoding="utf-8")
            os.chmod(tmp, 0o600)
            os.replace(tmp, self._percorso)
        except OSError as exc:
            log.warning("layout_non_salvato", errore=str(exc)[:120])
            tmp.unlink(missing_ok=True)
            return False
        log.debug("layout_salvato", pannelli=len(layout.pannelli))
        return True

    # ── verso lo snapshot ────────────────────────────────────────────────────

    def stato(self) -> dict[str, Any]:
        """Per `jarvis doctor` e per lo snapshot: dove sta e cosa e' successo."""
        return {
            "file": str(self._percorso),
            "esiste": self._percorso.exists(),
            "corrotto_in": str(self.corrotto_in) if self.corrotto_in else None,
        }


class LayoutMessage(Layout):
    """Il TERZO tipo in ingresso — e il **primo che il renderer INIZIA**.

    `ws_server.py` dichiara che i due tipi esistenti «per due anni saranno
    l'ultimo se nessuno dichiara perche' ne serve un terzo». Questa e' la
    dichiarazione, e sta nel codice e non in un messaggio di commit perche' e'
    la prossima persona a doverla leggere.

    ## In cosa e' diverso dai primi due, e perche' resta stretto

    `fs.confirm_response` e `argus.capture_response` sono **risposte**: portano
    l'`id` di una domanda che il core ha gia' posto, e non se ne possono
    inventare. E' la proprieta' che il preload dichiara — «non puo' CHIEDERE
    un'operazione».

    Questo non ha un `id` perche' non risponde a niente. La proprieta' che lo
    tiene innocuo e' un'altra, e va enunciata o la prossima aggiunta la usera'
    come precedente per un canale generico:

    > **Non chiede un'operazione: dichiara uno stato dell'ambiente.**
    > Il core non ESEGUE questo messaggio, lo RICORDA. Non nomina un percorso,
    > non nomina un tool, non ha un campo libero. Il peggio che un renderer
    > compromesso ottiene e' una scrivania disposta male al prossimo avvio.

    L'area e' obbligatoria qui e facoltativa in `Layout`: senza, `adatta()` non
    ha contro che cosa riportare dentro, e un messaggio che non dice quanto era
    grande lo schermo non e' una geometria — e' un elenco di numeri.
    """

    model_config = ConfigDict(extra="forbid")

    topic: Literal["ui.layout"]
    area_larghezza: int = Field(ge=1, le=32768)
    area_altezza: int = Field(ge=1, le=32768)

    def da_mettere_giu(self) -> Layout:
        """Il `Layout` da salvare, gia' riportato dentro l'area dichiarata.

        Il taglio avviene **prima** del disco, non dopo: cosi' un renderer che
        sbaglia non lascia dietro di se' un file che il prossimo avvio dovra'
        correggere.
        """
        return adatta(
            Layout(versione=self.versione, pannelli=self.pannelli,
                   icone=self.icone, cartelle=self.cartelle, scena=self.scena),
            self.area_larghezza, self.area_altezza,
        )


def messaggio_iniziale(store: LayoutStore) -> dict[str, Any]:
    """Il `ui.layout` che il core spinge a chi si collega.

    Come `state.snapshot` e i quattro topic di §13: **il renderer non chiede**
    (invariante 1, §6.3), il core manda.
    """
    layout = store.carica()
    return {"topic": "ui.layout", **json.loads(layout.model_dump_json())}
