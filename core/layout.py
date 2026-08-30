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
from dataclasses import dataclass
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
    #: ⚠️ **Se il pannello si VEDE**, e serve alla composizione (ADR-013).
    #:
    #: `Alt+H` nasconde in CSS: WinBox non toglie l'elemento, e `disposizione()`
    #: include i nascosti **di proposito** — filtrarli cancellerebbe dal disco
    #: tutti gli altri appena qualcuno muove un pannello con la scrivania
    #: nascosta (§26.10). Ma senza questo campo il core non li distingue, e la
    #: regola 1 di ADR-013 — «i pannelli gia' a schermo non si toccano» — li
    #: contava come muri.
    #:
    #: Misurato attraversando il confine il 30 agosto: con i sei pannelli che
    #: la scrivania apre all'avvio, **nessuna superficie si componeva mai**.
    #: Additivo: un `layout.json` di prima non ce l'ha e vale `False`.
    nascosto: bool = False


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

    #: ADR-013 regola 5 — **da dove viene questa composizione.** `None` quando
    #: l'ha disposta l'utente con le mani, che e' il caso normale.
    #:
    #: ⚠️ Additivi, come la traccia in ADR-011: un `layout.json` scritto prima
    #: non li ha, e deve continuare a caricarsi. Un test lo pinna.
    superficie: str | None = Field(default=None, max_length=64)
    #: ADR-011. CHI ha causato la composizione. Senza la traccia questa riga non
    #: si potrebbe scrivere, ed e' la ragione dell'ordine fra le fette.
    traccia_id: str | None = Field(default=None, max_length=32)

    # ⚠️ **Qui c'era `vuoto()`, ed e' TOLTO.** Tre `len()` mascherati da
    # predicato, con sei chiamanti tutti in `tests/test_layout.py` e nessuno in
    # `core/`. La domanda a cui rispondeva — «c'e' qualcosa da ripristinare?» —
    # ha gia' la sua risposta dove serve, in `ui/src/app.js:300-303`, e con una
    # forma DIVERSA: la' il fondo e i pannelli si contano separatamente, perche'
    # un fondo vuoto fa posare la scena dichiarata mentre un layout vuoto non fa
    # niente. Un secondo posto da guardare per sapere la stessa cosa e' il
    # difetto che questo progetto ha passato una settimana a togliere.


#: Quanto di un PANNELLO deve restare a schermo perche' la testa — la maniglia
#: con cui lo si riprende — sia afferrabile.
#: ⚠️ Gemello di `MIN_VISIBILE` in `ui/src/desk/geometria-area.js`. Non si puo'
#: importare attraverso il confine; l'accordo si misura, e lo misura
#: `tests/test_geometria_area.py::TestITreRitagliSonoUNO`.
MINIMO_PANNELLO = 80
#: Lo stesso per un'ICONA libera, che e' piu' piccola e non ha una testa da
#: afferrare: basta che si veda.
#: ⚠️ Gemello di `MIN_VISIBILE_ICONA`. Fino al 25 agosto 2026 qui non esisteva e
#: le icone prendevano gli 80 dei pannelli: restava una fascia di 40 px in cui
#: il renderer accettava una posizione e il core la spostava.
MINIMO_ICONA = 40


def adatta(layout: Layout, larghezza: int, altezza: int,
           minimo_visibile: int = MINIMO_PANNELLO, *,
           sinistra: int = 0, alto: int = 0,
           minimo_icona: int = MINIMO_ICONA) -> Layout:
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
    def dentro(v: int, comincia: int, quanto: int, minimo: int) -> int:
        return max(comincia, min(v, comincia + quanto - minimo))

    fuori: list[GeometriaPannello] = []
    for p in layout.pannelli:
        w = min(p.larghezza, larghezza)
        h = min(p.altezza, altezza)
        fuori.append(p.model_copy(update={
            "larghezza": w,
            "altezza": h,
            "x": dentro(p.x, sinistra, larghezza, minimo_visibile),
            "y": dentro(p.y, alto, altezza, minimo_visibile),
        }))
    return layout.model_copy(update={
        "pannelli": fuori,
        # ⚠️ Icone e cartelle hanno il minimo LORO, non quello dei pannelli.
        "icone": [i.model_copy(update={
            "x": dentro(i.x, sinistra, larghezza, minimo_icona),
            "y": dentro(i.y, alto, altezza, minimo_icona)})
            for i in layout.icone],
        "cartelle": [c.model_copy(update={
            "x": dentro(c.x, sinistra, larghezza, minimo_icona),
            "y": dentro(c.y, alto, altezza, minimo_icona)})
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
        #: L'ultimo layout riferito dalla scrivania, strozzatura o no.
        #: `None` finche' nessuno ha riferito: vedi `a_schermo_intero()`.
        self._ultimo: Layout | None = None
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

    def a_schermo_intero(self) -> bool | None:
        """Se un pannello copre la scrivania. `None` se non si sa ancora.

        ⚠️ **Il dato c'era gia' e non lo leggeva nessuno.**
        `GeometriaPannello.massimizzato` esiste da §26.2, la scrivania lo
        riempie da WinBox (`cornice.js`, `massimizzato: !!b.max`), il messaggio
        `ui.layout` lo porta e pydantic lo valida. Mancava il lettore, e
        `Contesto.pannello_a_schermo_intero` restava `None` per sempre:
        `core/news/gate.py` tratta l'ignoto come divieto, quindi in esercizio
        **nessuna card poteva passare** — mai, per costruzione.

        Non serve una soglia: non si stima quanta area copra un pannello, lo
        dice la scrivania. Una soglia sarebbe stata un numero scelto per
        rispondere a una domanda a cui qualcuno rispondeva gia'.

        `None` finche' nessuna scrivania ha mai riferito: «non lo so» non e'
        «non c'e'», e sull'ignoto §15 tace.
        """
        if self._ultimo is None:
            return None
        return any(p.massimizzato for p in self._ultimo.pannelli)

    def salva(self, layout: Layout, ora: float | None = None) -> bool:
        """Mette giu' il layout. Ritorna se ha toccato il disco.

        Sotto `MIN_INTERVALLO_S` non scrive e TIENE: il valore resta in attesa
        e va giu' col prossimo `salva()` o con `chiudi()`. Fondere e' diverso
        da scartare — con lo scarto l'ultima posizione di un trascinamento
        veloce si perderebbe, che e' esattamente il caso in cui l'utente sta
        guardando.
        """
        # ⚠️ **Prima della strozzatura.** `MIN_INTERVALLO_S` esiste per non
        # martellare il disco, e non ha niente a che vedere con il sapere:
        # sotto la soglia il layout resta in attesa di essere SCRITTO, ma e'
        # gia' lo stato vero della scrivania. Mettere questa riga dopo il
        # `return False` avrebbe reso `a_schermo_intero()` indietro di un
        # trascinamento — cioe' sbagliata proprio mentre l'utente lavora.
        self._ultimo = layout
        adesso = time.monotonic() if ora is None else ora
        if adesso - self._ultima_scrittura < self.MIN_INTERVALLO_S:
            self._in_attesa = layout
            return False
        self._in_attesa = None
        self._ultima_scrittura = adesso
        return self._scrivi(layout)

    # ── ADR-013 criterio 5: tornare alla composizione precedente ────────────

    @property
    def percorso_precedente(self) -> Path:
        """Dove sta la composizione di prima. Un file accanto, non una storia.

        ⚠️ **Uno slot, non N.** Una storia a piu' passi e' un meccanismo che
        nessuno ha chiesto per un problema che con tre superfici non si e'
        ancora presentato — e `ANALISI-SENIOR` §4.6③ misura questo tipo di
        allargamento come il primo rischio di allocazione del progetto.
        """
        return self._percorso.with_suffix(".precedente.json")

    def componi_e_salva(self, composizione: "Composizione") -> bool:
        """Mette giu' una composizione, **dopo aver messo da parte quella di
        prima**. Ritorna se ha toccato il disco.

        ⚠️ **La copia si fa PRIMA, e sempre.** ADR-013 ha una tensione fra la
        regola 1 — «la composizione manuale vince sempre» — e la regola 5, che
        vuole `superficie` e `traccia_id` nel `Layout` **salvato**: la seconda
        implica che la composizione automatica scriva sopra il lavoro manuale.
        Le due si conciliano solo se cio' che c'era prima resta recuperabile, e
        questo e' il file che lo rende vero.

        Salta la strozzatura di `salva()`: una composizione non e' un
        trascinamento, e' un evento singolo — fonderla col prossimo movimento
        del mouse vorrebbe dire perderne meta'.
        """
        if composizione.layout is None:
            return False
        prima = self.carica()
        try:
            self.percorso_precedente.parent.mkdir(parents=True, exist_ok=True)
            self.percorso_precedente.write_text(
                prima.model_dump_json(indent=1), encoding="utf-8")
            os.chmod(self.percorso_precedente, 0o600)
        except OSError as exc:
            # ⚠️ **Se non si puo' tornare indietro, non si va avanti.** Comporre
            # senza rete vorrebbe dire sovrascrivere il lavoro manuale
            # dell'utente senza modo di recuperarlo, ed e' proprio cio' che la
            # regola 1 vieta.
            log.error("composizione_senza_rete", errore=str(exc)[:120],
                      conseguenza="non si compone: il layout manuale resta")
            return False
        self._ultimo = composizione.layout
        self._in_attesa = None
        self._ultima_scrittura = time.monotonic()
        return self._scrivi(composizione.layout)

    def ripristina(self) -> Layout | None:
        """Rimette la composizione di prima. `None` se non ce n'e' una.

        Non e' un annullamento generale: e' la coppia di `componi_e_salva`, e
        vale una volta sola — dopo, il file precedente **resta** dov'e', quindi
        ripristinare due volte di fila non torna indietro di due passi. E'
        cio' che uno slot puo' fare, ed e' scritto qui perche' chi legge non se
        lo aspetti diverso.
        """
        p = self.percorso_precedente
        if not p.exists():
            return None
        try:
            prima = Layout.model_validate_json(p.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            log.warning("precedente_illeggibile", errore=str(exc)[:120])
            return None
        self._ultimo = prima
        self._in_attesa = None
        self._ultima_scrittura = time.monotonic()
        self._scrivi(prima)
        log.info("layout_ripristinato", superficie=prima.superficie)
        return prima

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


# ── ADR-013: l'LLM propone, il compositore dispone ───────────────────────────
#
# Manca(va) una cosa sola, e non e' un motore: il modo di **proporre** una
# composizione. `Layout` registra cio' che l'utente ha fatto con le mani; non
# esisteva niente che potesse dire «per questo compito servono questi pannelli».
#
# Il rischio, dichiarato per primo: un LLM che emette geometria e' un LLM che
# disegna, e un LLM che emette geometria VALIDA e' un LLM che disegna e non se
# ne accorge. La riga che separa questo progetto da una demo e' che **l'LLM non
# nomina mai un pixel** — e in questa fetta non nomina nemmeno un pannello,
# perche' gli intent sono scritti a mano qui sotto.


class LayoutIntent(_Stretto):
    """Che cosa serve a schermo, **senza dire dove**.

    ⚠️ **Nessun campo di geometria, e non e' una dimenticanza: e' la regola 3.**
    Niente `x`, `y`, `larghezza`, `z`. `_Stretto` ha `extra="forbid"`, quindi il
    giorno in cui un modello ne emettesse uno lo schema lo rifiuta **prima di
    guardarlo** — non e' una convenzione da ricordare, e' il tipo che non lo
    accetta.
    """

    #: Il nome della composizione. Finisce nel `Layout` salvato e nel diario.
    superficie: str = Field(min_length=1, max_length=64,
                            pattern=r"^[a-z0-9][a-z0-9_-]*$")
    #: ADR-011 — chi l'ha causata.
    traccia_id: str = Field(min_length=1, max_length=32)
    #: I nomi dei pannelli. Allowlist, invariante 2 applicata al layout.
    pannelli_richiesti: list[str] = Field(min_length=1, max_length=8)
    pannelli_secondari: list[str] = Field(default_factory=list, max_length=8)
    priorita: Literal["eroe", "affiancato", "sfondo"] = "affiancato"


@dataclass(frozen=True, slots=True)
class Area:
    """Il rettangolo su cui si compone: il pavimento, fra barra e dock.

    ⚠️ **Resta UN rettangolo.** Il pacchetto v3 chiama il multi-monitor
    «first-class architectural requirement»; non e' in SPEC, ADR-005 dice
    schermo intero, e nessuna evidenza lo richiede. Fuori perimetro, dichiarato
    in ADR-013 — e `componi` prende gia' l'area per parametro, quindi il giorno
    in cui servisse la strada e' aperta senza costare niente oggi.
    """

    sinistra: int
    alto: int
    larghezza: int
    altezza: int


@dataclass(frozen=True, slots=True)
class Composizione:
    """L'esito di `componi`. **`layout is None` vuol dire: non si muove nulla.**

    ADR-013 dichiarava `componi(...) -> Layout`. Non basta: la regola 4 dice che
    un intent rifiutato «non muove un pixel **e produce un advisory
    dichiarato**», e un `Layout` da solo non puo' portare il motivo del
    rifiuto. Restituirne uno vuoto sarebbe peggio: chi chiama non
    distinguerebbe «composto a vuoto» da «rifiutato», che e' esattamente la
    differenza che la regola esiste per tenere.
    """

    layout: Layout | None
    motivo: str | None
    superficie: str
    traccia_id: str

    @property
    def rifiutata(self) -> bool:
        return self.layout is None

    def advisory(self) -> dict[str, Any]:
        """L'annuncio della regola 4. Stessa forma degli altri `agent.advisory`."""
        return {"topic": "agent.advisory", "level": "info",
                "reason": "composizione_rifiutata",
                "dettaglio": self.motivo or "",
                "superficie": self.superficie, "traccia": self.traccia_id}


#: Quante celle prende un pannello, per priorita'. La griglia e' quella delle
#: scene — `COLONNE` x `RIGHE` — e non e' una duplicazione nuova: e' la stessa
#: copia gia' dichiarata e pinnata in `core/settings.py`, riusata qui perche'
#: una composizione automatica che si allineasse a una griglia DIVERSA da
#: quella delle scene dichiarate produrrebbe due scrivanie diverse dalla stessa
#: idea di ambiente.
CELLE_PER_PRIORITA: dict[str, tuple[int, int]] = {
    "eroe": (6, 4),
    "affiancato": (4, 2),
    "sfondo": (3, 2),
}
#: I secondari prendono sempre il taglio piu' piccolo: sono il contorno.
CELLE_SECONDARIE = CELLE_PER_PRIORITA["sfondo"]


def _griglia_occupata(corrente: Layout, area: Area,
                      colonne: int, righe: int,
                      chiesti: set[str] | frozenset[str] = frozenset(),
                      ) -> list[list[bool]]:
    """Le celle che i pannelli GIA' A SCHERMO coprono.

    ⚠️ **Ogni pannello di `corrente` conta come manuale**, ed e' la regola 1
    presa alla lettera e in senso conservativo: `GeometriaPannello` non porta
    una provenienza per pannello, quindi non c'e' modo di distinguere uno che
    l'utente ha mosso da uno che una composizione precedente ha messo li'.
    Nel dubbio non si tocca — muovere sotto le dita di qualcuno e' il secondo
    rischio che ADR-013 dichiara.

    Il prezzo e' dichiarato: comporre **sopra** una composizione quasi sempre
    rifiuta per mancanza di spazio. Si torna indietro con `ripristina()` e poi
    si compone l'altra superficie.
    """
    presa = [[False] * colonne for _ in range(righe)]
    if area.larghezza <= 0 or area.altezza <= 0:
        return presa
    lc = area.larghezza / colonne
    lr = area.altezza / righe
    for p in corrente.pannelli:
        # ⚠️ Due esclusioni, e tutt'e due si sono viste solo dal vivo.
        #
        # Un pannello **nascosto** non occupa niente: non si vede. Senza questa
        # riga «nascondi tutto» non liberava la scrivania, e con i sei pannelli
        # dell'avvio nessuna superficie si componeva mai.
        #
        # E un pannello che l'intent **chiede** non e' ostacolo a se' stesso:
        # chiedere che sia disposto e' chiedere che si muova. Rifiutare perche'
        # e' gia' aperto sarebbe la regola 1 applicata contro chi la invoca.
        if p.nascosto or p.id in chiesti:
            continue
        c0 = int((p.x - area.sinistra) // lc)
        c1 = int((p.x - area.sinistra + p.larghezza - 1) // lc)
        r0 = int((p.y - area.alto) // lr)
        r1 = int((p.y - area.alto + p.altezza - 1) // lr)
        for r in range(max(0, r0), min(righe - 1, r1) + 1):
            for c in range(max(0, c0), min(colonne - 1, c1) + 1):
                presa[r][c] = True
    return presa


def _primo_blocco(presa: list[list[bool]], quante_c: int, quante_r: int,
                  colonne: int, righe: int) -> tuple[int, int] | None:
    """Il primo blocco libero, scorrendo per righe. Deterministico."""
    for r in range(righe - quante_r + 1):
        for c in range(colonne - quante_c + 1):
            if all(not presa[r + dr][c + dc]
                   for dr in range(quante_r) for dc in range(quante_c)):
                return c, r
    return None


def componi(intent: LayoutIntent, area: Area, corrente: Layout,
            pannelli_ammessi: set[str] | frozenset[str],
            *, colonne: int | None = None,
            righe: int | None = None) -> Composizione:
    """Da un intento a una geometria. **Deterministico, e nessun LLM lo tocca.**

    Le cinque regole di ADR-013, e quattro sono divieti:

    1. **la composizione manuale vince sempre** — i pannelli gia' a schermo non
       si toccano, `componi` lavora sullo spazio rimasto, e se non ne resta
       abbastanza **non compone**: lo dichiara;
    2. **i nomi vengono da un'allowlist** — invariante 2 applicata al layout;
    3. **l'intent non contiene geometria** — lo impone `LayoutIntent`, non
       questa funzione;
    4. **un intent rifiutato non muove un pixel** e produce un advisory;
    5. **ogni composizione registra da dove viene** — `superficie` e
       `traccia_id` finiscono nel `Layout`.

    ⚠️ **`pannelli_ammessi` arriva per parametro, e non e' pigrizia.** ADR-013
    diceva «i nomi vengono dal registry dei pannelli»; quel registry nel core
    **non esiste**: l'elenco dei pannelli sta in `ui/src/desk/moduli.js`, e
    `core/settings.py` dichiara per iscritto che «il core non conosce
    `moduli.js` e non deve: e' interfaccia». Copiarlo qui sarebbe una seconda
    fonte di verita' su una lista che cambia.

    L'allowlist e' invece **cio' che l'utente ha dichiarato nelle proprie
    scene** (`settings.ui.scene`): una lista chiusa che il core possiede
    davvero. Il chiamante la passa; questa funzione non va a prendersela.
    """
    from core.settings import COLONNE, RIGHE

    colonne = COLONNE if colonne is None else colonne
    righe = RIGHE if righe is None else righe

    def no(motivo: str) -> Composizione:
        return Composizione(layout=None, motivo=motivo,
                            superficie=intent.superficie,
                            traccia_id=intent.traccia_id)

    # ── regola 2 ────────────────────────────────────────────────────────────
    chiesti = list(intent.pannelli_richiesti) + list(intent.pannelli_secondari)
    if not pannelli_ammessi:
        # ⚠️ **Il caso che rende la funzione muta, e va detto per nome.**
        # L'allowlist sono i pannelli dichiarati nelle scene di `settings.toml`;
        # un file senza scene la lascia vuota, e allora OGNI composizione
        # verrebbe rifiutata con «pannelli sconosciuti» — un messaggio che
        # manda a cercare il difetto dalla parte sbagliata. Misurato il 30
        # agosto: il `settings.toml` di questa macchina non ha nessuna scena.
        return no("nessuna scena dichiarata in settings.toml: l'allowlist "
                  "della composizione viene da li', e senza scene non c'e' "
                  "niente che si possa comporre. Si dichiarano con "
                  "[[ui.scene]], come nel config spedito col progetto")
    ignoti = [p for p in chiesti if p not in pannelli_ammessi]
    if ignoti:
        return no(f"pannelli sconosciuti: {', '.join(sorted(set(ignoti)))}. "
                  f"L'allowlist sono i pannelli dichiarati nelle scene di "
                  f"settings.toml, e un nome fuori da quella lista non e' un "
                  f"pannello vuoto: e' un intento rifiutato")
    if len(set(chiesti)) != len(chiesti):
        return no("lo stesso pannello e' chiesto due volte: una composizione "
                  "non puo' mettere due volte la stessa finestra")
    if area.larghezza <= 0 or area.altezza <= 0:
        return no(f"area non componibile: {area.larghezza}x{area.altezza}")

    # ── regola 1 ────────────────────────────────────────────────────────────
    presa = _griglia_occupata(corrente, area, colonne, righe, set(chiesti))
    lc = area.larghezza / colonne
    lr = area.altezza / righe
    nuovi: list[GeometriaPannello] = []
    for i, nome in enumerate(chiesti):
        forma = (CELLE_PER_PRIORITA[intent.priorita]
                 if nome in intent.pannelli_richiesti else CELLE_SECONDARIE)
        posto = _primo_blocco(presa, forma[0], forma[1], colonne, righe)
        if posto is None:
            # ⚠️ **Tutto o niente.** Comporre una meta' lascerebbe la scrivania
            # in uno stato che nessuno ha chiesto: ne' quello di prima ne'
            # quello proposto.
            return no(f"non c'e' spazio per «{nome}»: la composizione manuale "
                      f"occupa la scrivania, e i pannelli gia' a schermo non si "
                      f"toccano (regola 1). Se ne sposti uno, o torni alla "
                      f"composizione precedente")
        c, r = posto
        for dr in range(forma[1]):
            for dc in range(forma[0]):
                presa[r + dr][c + dc] = True
        nuovi.append(GeometriaPannello(
            id=nome,
            x=area.sinistra + round(c * lc),
            y=area.alto + round(r * lr),
            larghezza=max(MINIMO_PANNELLO, round(forma[0] * lc)),
            altezza=max(MINIMO_PANNELLO, round(forma[1] * lr)),
            z=i + 1,
        ))

    # ── regola 5 ────────────────────────────────────────────────────────────
    # I pannelli che l'intent ha (ri)disposto non restano anche nella loro
    # posizione di prima: sarebbero due finestre con lo stesso id.
    tenuti = [p for p in corrente.pannelli if p.id not in set(chiesti)]
    composto = Layout(
        versione=corrente.versione,
        pannelli=tenuti + nuovi,
        icone=list(corrente.icone), cartelle=list(corrente.cartelle),
        scena=corrente.scena,
        area_larghezza=area.larghezza, area_altezza=area.altezza,
        area_sinistra=area.sinistra, area_alto=area.alto,
        superficie=intent.superficie, traccia_id=intent.traccia_id,
    )
    # `adatta()` esisteva gia' e riporta dentro l'area cio' che ne e' uscito:
    # l'arrotondamento delle celle non deve poter produrre un pannello fuori.
    return Composizione(
        layout=adatta(composto, area.larghezza, area.altezza,
                      sinistra=area.sinistra, alto=area.alto),
        motivo=None, superficie=intent.superficie, traccia_id=intent.traccia_id)


#: Le superfici, **scritte a mano**. ADR-013: nella prima fetta gli intent sono
#: dichiarati in codice e nessun LLM li tocca.
#:
#: La ragione e' misurabile: il compilatore va provato contro un input che si
#: controlla, prima di provarlo contro uno che si negozia. Se `componi` ha un
#: difetto lo si vuole trovare con un intent scritto qui, non dedurlo da una
#: composizione strana la notte in cui T1 ne ha emesso uno.
#:
#: ⚠️ `traccia_id` e' un segnaposto: lo mette il chiamante, che ha la traccia
#: vera del turno che ha chiesto la composizione (ADR-011).
SUPERFICI: dict[str, dict[str, Any]] = {
    # ⚠️ `console` era qui, e la superficie nasceva MORTA: non compare in
    # nessuna scena di `config/settings.toml`, quindi l'allowlist lo rifiutava.
    # L'ha trovato il test del giro intero, non una rilettura. Un test pinna
    # che ogni nome qui sotto sia dichiarato nella configurazione spedita.
    "diagnostica": {"pannelli_richiesti": ["telemetria", "agenti"],
                    "pannelli_secondari": ["anelli"],
                    "priorita": "affiancato"},
    "briefing": {"pannelli_richiesti": ["news", "telemetria"],
                 "pannelli_secondari": ["agenti"],
                 "priorita": "affiancato"},
    "officina": {"pannelli_richiesti": ["globo"],
                 "pannelli_secondari": ["sorgente", "archivio"],
                 "priorita": "eroe"},
}


def intento(superficie: str, traccia_id: str) -> LayoutIntent:
    """Uno degli intent dichiarati, con la traccia di chi l'ha chiesto."""
    if superficie not in SUPERFICI:
        raise KeyError(
            f"{superficie!r} non e' una superficie dichiarata. "
            f"Ci sono: {', '.join(sorted(SUPERFICI))}"
        )
    return LayoutIntent(superficie=superficie, traccia_id=traccia_id,
                        **SUPERFICI[superficie])
