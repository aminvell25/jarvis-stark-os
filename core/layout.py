"""Il layout dell'ambiente — §26.10 punto 1, e il fondo di §26.5.

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
import re
import time
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

log = structlog.get_logger(__name__)

NOME_FILE = "layout.json"

#: Un identificatore dell'ambiente: id di pannello, di icona, di cartella.
#: Ristretto perche' finisce in un nome di chiave e in un log, e perche' un
#: id che puo' contenere qualunque cosa e' un id che un giorno conterra' un
#: percorso.
ID = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
#: La stessa forma, usabile a mano dove il campo non puo' portarla addosso
#: (vedi `IconaLibera.nome`, che e' stretto per i moduli e largo per i file).
_PARE_UN_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")

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

    ## R92 — il segnaposto aveva la forma sbagliata, e si e' visto costruendo

    La prima stesura aveva `id: str = ID` e basta. Due cose non tornavano, e
    nessuna delle due si vedeva finche' non c'e' stato un produttore:

    **1. `ID` non puo' contenere il nome di un file.** Il modello accetta
    `^[a-z0-9][a-z0-9_.-]*$`; un file vero si chiama `Relazione Q3 (bozza).pdf`.
    Con un validatore solo, la PRIMA icona di un file con una maiuscola
    avrebbe fatto rifiutare l'INTERO messaggio, e la scrivania avrebbe smesso
    di ricordare anche i pannelli. La difesa si sarebbe trasformata in un
    guasto — lo stesso errore che il preload evita non lasciando passare
    `{...layout}`.

    **2. Un identificatore non dice di CHE COSA e' icona.** `telemetria` e' il
    modulo o un file che si chiama cosi'? Con una sola stringa la domanda non
    ha risposta, e chi la legge deve indovinare.

    Quindi due campi: `tipo` dice a che famiglia appartiene, `nome` e' il
    riferimento dentro quella famiglia, e i due insieme sono l'identita'.

    ## ⚠️ `nome` NON e' un percorso, e non deve poterlo diventare

    Con `tipo="file"` questo campo e' **un'etichetta**, e il core non ci apre
    niente: non lo unisce a una radice, non lo passa a `pathlib`, non lo
    confronta con l'allowlist. Il percorso risolto che §26.5 vuole nel piede
    della cartella lo ricompone il renderer da `fs.list`, che il core manda
    gia' — cosi' **nel layout non finisce nessun percorso**, ed e' la stessa
    sicurezza strutturale di `timezones`, che non ha un parametro path perche'
    non deve poterlo avere.

    Il validatore rifiuta comunque separatori e caratteri di controllo: non
    perche' servano a questo file, ma perche' un campo che oggi nessuno tratta
    come un percorso e' un campo che fra un anno qualcuno trattera' come un
    percorso.

    ## Cosa NON viene rifiutato, e perche'

    Due icone identiche, o un `dentro` che nomina una cartella sparita, non
    fanno fallire la validazione. Sono situazioni che il renderer non produce,
    e rifiutare il messaggio intero significherebbe perdere tutta la
    disposizione per un dettaglio innocuo — di nuovo la difesa che diventa
    guasto. Il renderer disegna sul fondo l'icona orfana, come fa
    `scrivania.js` col pannello che non esiste piu'.
    """

    #: `modulo` -> `nome` e' l'id di `ui/src/desk/moduli.js`.
    #: `file`   -> `nome` e' il nome del file dentro la workspace. ETICHETTA.
    tipo: Literal["modulo", "file"] = "modulo"
    nome: str = Field(min_length=1, max_length=255)
    x: int = COORD
    y: int = COORD
    #: La cartella che la contiene, o `None` se sta sul fondo.
    dentro: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("nome")
    @classmethod
    def _un_nome_non_e_un_percorso(cls, v: str) -> str:
        if "/" in v or "\\" in v:
            raise ValueError("un nome di icona non contiene separatori di percorso")
        if v in {".", ".."}:
            raise ValueError("un nome di icona non e' una voce di directory")
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("un nome di icona non contiene caratteri di controllo")
        return v

    @model_validator(mode="after")
    def _un_modulo_si_chiama_come_un_modulo(self) -> "IconaLibera":
        """Il nome di un MODULO resta stretto: quello lo scriviamo noi.

        La larghezza serve ai nomi di file, che arrivano dal disco. Un id di
        modulo che non rispettasse la forma degli altri id sarebbe un errore
        nostro, e va visto subito.
        """
        if self.tipo == "modulo" and not _PARE_UN_ID.match(self.nome):
            raise ValueError(f"id di modulo non valido: {self.nome!r}")
        return self


class CartellaLibera(_Stretto):
    """§26.5 — una cartella manila sul fondo.

    ⚠️ **Non e' una cartella del filesystem.** E' un raggruppamento
    dell'ambiente: §26.5 lo dice a chiare lettere, ed e' la distinzione che
    impedisce di cancellare qualcosa credendo di riordinare una scrivania.
    Nessun percorso entra qui dentro — solo id di icone.

    Il contenuto non sta qui: sta in `IconaLibera.dentro`. Un elenco di id qui
    E un `dentro` la' sarebbero due contabilita' della stessa appartenenza, e
    le due divergerebbero al primo ramo dimenticato — e' gia' successo con la
    geometria di ripristino di WinBox (R85).

    `id` lo genera il renderer nella forma `cartella.N`, e resta stretto: e'
    nostro, non arriva dal disco.
    """

    id: str = ID
    x: int = COORD
    y: int = COORD
    #: L'etichetta la scrive l'utente. Nessun vincolo di forma oltre alla
    #: lunghezza: e' un nome, non un identificatore. I caratteri di controllo
    #: si tolgono lo stesso — finiscono in un log.
    etichetta: str = Field(default="", max_length=64)
    aperta: bool = False

    @field_validator("etichetta")
    @classmethod
    def _senza_caratteri_di_controllo(cls, v: str) -> str:
        if any(ord(c) < 32 or ord(c) == 127 for c in v):
            raise ValueError("l'etichetta non contiene caratteri di controllo")
        return v


class Layout(_Stretto):
    """Tutto cio' che l'ambiente ricorda di se stesso.

    `versione` esiste per poter cambiare idea: un file scritto oggi e letto da
    un domani che ha campi diversi deve poter essere riconosciuto e non solo
    rifiutato.
    """

    versione: Literal[1] = 1
    pannelli: list[GeometriaPannello] = Field(default_factory=list, max_length=64)
    #: §26.5, punto 5. Erano il posto vuoto lasciato al punto 1; adesso c'e'
    #: chi li riempie, ed e' `ui/src/desk/icone.js`.
    icone: list[IconaLibera] = Field(default_factory=list, max_length=256)
    cartelle: list[CartellaLibera] = Field(default_factory=list, max_length=64)
    #: §26.6 — la scena attiva, se ce n'e' una.
    scena: str | None = Field(default=None, max_length=64)
    #: L'area in cui questa geometria e' stata misurata. Serve al ripristino:
    #: uno schermo diverso non e' un errore, e senza sapere quanto era grande
    #: non si distingue «fuori area» da «area cambiata».
    area_larghezza: int | None = Field(default=None, ge=1, le=32768)
    area_altezza: int | None = Field(default=None, ge=1, le=32768)
    #: ⚠️ DOVE COMINCIA l'area, e senza questi due l'area era mezza dichiarata.
    #: `area_larghezza` e `area_altezza` descrivono il PAVIMENTO — lo spazio fra
    #: barra e dock — mentre pannelli e icone sono salvati in coordinate di
    #: FINESTRA. `adatta()` li tagliava contro `[0, altezza - minimo]`, cioe' una
    #: banda traslata in alto di quanto e' alta la barra: ammetteva una posizione
    #: DENTRO la barra e ne rifiutava una buona in fondo al pavimento.
    area_sinistra: int | None = Field(default=None, ge=0, le=32768)
    area_alto: int | None = Field(default=None, ge=0, le=32768)

    def vuoto(self) -> bool:
        return not (self.pannelli or self.icone or self.cartelle)


def adatta(layout: Layout, larghezza: int, altezza: int,
           minimo_visibile: int = 80, *,
           sinistra: int = 0, alto: int = 0) -> Layout:
    """Riporta dentro l'area cio' che ne e' uscito. **Non scarta.**

    Un pannello a `x = 3000` su uno schermo largo 1536 non e' un errore di cui
    incolpare l'utente: e' uno schermo cambiato, o una finestra rimpicciolita.
    Scartarlo vorrebbe dire perdere la disposizione proprio quando serve di
    piu'; lasciarlo dov'e' vorrebbe dire un pannello aperto e irraggiungibile,
    che e' peggio ancora.

    `minimo_visibile` e' quanto di un pannello deve restare a schermo perche'
    la sua testa — cioe' la maniglia con cui lo si riprende — sia afferrabile.

    ## ⚠️ `sinistra` e `alto`: l'area COMINCIA da qualche parte

    Fino al 25 agosto 2026 questa funzione tagliava contro `[0, altezza - min]`,
    e c'erano **due ritagli in due spazi di coordinate diversi** per la stessa
    proprieta':

        renderer, `ui/src/desk/geometria-area.js::dentroArea`
            y ammessa [alto, alto + altezza - min]
        core, qui
            y ammessa [0, altezza - min]

    `area_larghezza` e `area_altezza` sono il PAVIMENTO — lo spazio fra barra e
    dock — ma pannelli e icone sono salvati in coordinate di FINESTRA. Con una
    barra alta 32 px la banda del core era traslata di 32 px verso l'alto:
    ammetteva una posizione **dentro la barra** e ne spostava una buona a 32 px
    dal fondo del pavimento.

    Il difetto era latente e si e' visto quando il dock e' cresciuto di otto
    pixel: `tests/test_layout.py::TestIconeVere::test_10_riavviato_il_core_e_ANCORA_LI`
    e' caduto, e un'icona posata in fondo tornava piu' su a ogni riavvio.

    I valori predefiniti sono zero, cioe' il comportamento di prima: un
    messaggio che non dice dove comincia l'area viene trattato come se
    cominciasse in alto a sinistra.
    """
    def dentro(v: int, comincia: int, quanto: int) -> int:
        return max(comincia, min(v, comincia + quanto - minimo_visibile))

    fuori: list[GeometriaPannello] = []
    for p in layout.pannelli:
        w = min(p.larghezza, larghezza)
        h = min(p.altezza, altezza)
        fuori.append(p.model_copy(update={
            "larghezza": w,
            "altezza": h,
            "x": dentro(p.x, sinistra, larghezza),
            "y": dentro(p.y, alto, altezza),
        }))
    return layout.model_copy(update={
        "pannelli": fuori,
        "icone": [i.model_copy(update={"x": dentro(i.x, sinistra, larghezza),
                                       "y": dentro(i.y, alto, altezza)})
                  for i in layout.icone],
        "cartelle": [c.model_copy(update={"x": dentro(c.x, sinistra, larghezza),
                                          "y": dentro(c.y, alto, altezza)})
                     for c in layout.cartelle],
        "area_larghezza": larghezza,
        "area_altezza": altezza,
        "area_sinistra": sinistra,
        "area_alto": alto,
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
    #: Dove comincia il pavimento. Predefiniti a zero perche' un renderer che
    #: non li manda deve continuare a funzionare — con la banda di prima, che
    #: e' sbagliata di quanto e' alta la barra ma non e' una rottura.
    area_sinistra: int = Field(default=0, ge=0, le=32768)
    area_alto: int = Field(default=0, ge=0, le=32768)

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
            sinistra=self.area_sinistra, alto=self.area_alto,
        )


def messaggio_iniziale(store: LayoutStore) -> dict[str, Any]:
    """Il `ui.layout` che il core spinge a chi si collega.

    Come `state.snapshot` e i quattro topic di §13: **il renderer non chiede**
    (invariante 1, §6.3), il core manda.
    """
    layout = store.carica()
    return {"topic": "ui.layout", **json.loads(layout.model_dump_json())}
