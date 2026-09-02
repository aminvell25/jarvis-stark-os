"""Il tool che genera un solido — SPEC §17.1-17.3, ADR-014.

Era **0 byte dal 18 agosto**, mentre `CLAUDE.md` prometteva «genera modelli
3D» in prima pagina e §17 gli dedicava una sezione. Zero byte e una sezione di
specifica sono la stessa cosa detta in due modi opposti, e ADR-014 ha scelto
quale delle due tenere.

La catena, tutta con pezzi che esistevano gia':

    frase T0 -> registry.invoke -> planner -> Piano col percorso RISOLTO
    -> conferma di §6.2 -> generatore in core/model3d/ -> trimesh scrive
    -> verificatore che rilegge il GLB con la libreria standard (ADR-012)
    -> fs.result, riga di diario col verdetto, model3d.preview al pannello

⚠️ **Nessun argomento `path`**, ed e' una scelta di sicurezza strutturale come
in `core/tools/introspect.py`: la destinazione la decide il core dentro
`fs.workspace/modelli/`, quindi non esiste una richiesta che possa nominare un
percorso. Il piano lo mostra RISOLTO, come l'invariante 3 impone.

⚠️ **Il modello e' un'ALLOWLIST di forme, non una geometria** (invariante 34,
proposto da ADR-014): l'LLM sceglie un nome da `GENERATORI` e propone
parametri in millimetri. Non esiste un modo di passare vertici.

⚠️ **Millimetri qui, metri nel file.** glTF 2.0 prescrive i metri, e un
visualizzatore esterno deve vedere il pezzo grande quanto e'. La conversione
sta in un posto solo — `_scrivi_glb` — e i parametri in mm viaggiano in
`asset.extras`, dove si leggono e non si credono: il verificatore usa i
`min`/`max` dell'accessor, non gli extras.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

from core.model3d import glb_lettore
from core.model3d.estrusione import TRIANGOLI, VERTICI, estrusione_45
from core.model3d.parametrico import MM_PER_METRO, Modello, ModelloNonValido
from core.model3d.tubo import PIEGHE, conteggi_di, tubo_piegato
from core.paths_policy import PathFuoriRadice, risolvi_sotto_radici
from core.settings import Settings
from core.tools.confirm import Operazione, Piano
from core.tools.registry import Tool, ToolResult, register
from core.verifica import Verifica

log = structlog.get_logger(__name__)

#: L'allowlist delle forme. Un nome per volta, come il registro dei tool e i
#: flussi del diario: un elenco chiuso, non una convenzione.
GENERATORI: dict[str, Callable[..., Modello]] = {
    "estrusione_45": estrusione_45,
    "tubo_piegato": tubo_piegato,
}

#: I conteggi attesi per forma, **dai parametri e senza costruire la mesh**.
#: Sono l'atteso del verificatore, e un atteso che venga dal codice verificato
#: non e' un atteso (ADR-012).
#:
#: ⚠️ Erano una costante finche' c'era solo `estrusione_45`, che ne ha sempre
#: 32 e 64. Un tubo no: la sua densita' viene dalla curvatura (§11.10 regola
#: 2), quindi il conteggio e' una FUNZIONE dei parametri — `conteggi_di`, che
#: applica la formula dei segmenti senza spazzare niente. Il controllo resta
#: quello di prima: due affermazioni indipendenti sullo stesso numero.
CONTEGGI: dict[str, Callable[[dict[str, float]], tuple[int, int]]] = {
    "estrusione_45": lambda _p: (VERTICI, TRIANGOLI),
    "tubo_piegato": conteggi_di,
}

#: Dove finiscono i file, dentro la workspace. Sotto una radice consentita per
#: costruzione: `fs.workspace` e' la prima di `fs.allowed_roots`.
SOTTOCARTELLA = "modelli"

#: Quanto puo' sbagliare il bbox riletto dal file rispetto a quello analitico.
#: Non e' una tolleranza di comodo: le posizioni sono `float32` e passano per
#: una divisione per mille, quindi l'errore vero e' dell'ordine di 1e-5 mm.
#: Dieci micron e' tre ordini di grandezza sopra il rumore e mille volte sotto
#: qualunque differenza che conti.
TOLLERANZA_MM = 0.01

TOPIC = "model3d.preview"


class GeneraModelloArgs(BaseModel):
    """I parametri, in millimetri. Nessun percorso: vedi l'intestazione.

    ⚠️ **`extra="forbid"`, e gli altri schemi di `core/tools/` non ce l'hanno.**
    Trovato da `tests/eval_tools.py` il 2 settembre 2026: `genera_modello`
    chiamato con `{"path": "/tmp/x.glb"}` **riusciva**, perche' pydantic scarta
    in silenzio i campi che non conosce. Il file finiva dove doveva — nella
    workspace — quindi non era una falla; era peggio in un modo sottile: chi
    aveva chiesto quel percorso riceveva `ok=True` e credeva di averlo
    ottenuto. Per un tool la cui intera storia di sicurezza e' «non esiste un
    argomento path», accettarlo e ignorarlo e' la risposta sbagliata: si
    rifiuta, e si dice quale campo non esiste.
    """

    model_config = ConfigDict(extra="forbid")

    forma: Literal["estrusione_45", "tubo_piegato"] = "estrusione_45"

    # ── estrusione_45 ───────────────────────────────────────────────────────
    larghezza: float | None = Field(default=None, gt=0, le=2000)
    altezza: float | None = Field(default=None, gt=0, le=2000)
    profondita: float | None = Field(default=None, gt=0, le=2000)
    smusso_bl: float | None = Field(default=None, ge=0, le=1000)
    smusso_br: float | None = Field(default=None, ge=0, le=1000)
    smusso_tr: float | None = Field(default=None, ge=0, le=1000)
    smusso_tl: float | None = Field(default=None, ge=0, le=1000)
    foro_larghezza: float | None = Field(default=None, gt=0, le=2000)
    foro_altezza: float | None = Field(default=None, gt=0, le=2000)
    smusso_foro: float | None = Field(default=None, ge=0, le=1000)

    # ── tubo_piegato — corsa, rotazione, angolo: i tre numeri della piegatrice
    diametro: float | None = Field(default=None, gt=0, le=1000)
    raggio_piega: float | None = Field(default=None, gt=0, le=2000)
    corsa_1: float | None = Field(default=None, gt=0, le=2000)
    corsa_2: float | None = Field(default=None, gt=0, le=2000)
    corsa_3: float | None = Field(default=None, gt=0, le=2000)
    corsa_4: float | None = Field(default=None, gt=0, le=2000)
    angolo_1: float | None = Field(default=None, gt=0, lt=180)
    angolo_2: float | None = Field(default=None, gt=0, lt=180)
    angolo_3: float | None = Field(default=None, gt=0, lt=180)
    rotazione_1: float | None = Field(default=None, ge=-180, le=180)
    rotazione_2: float | None = Field(default=None, ge=-180, le=180)
    rotazione_3: float | None = Field(default=None, ge=-180, le=180)
    corda_mm: float | None = Field(default=None, gt=0, le=100)

    def parametri(self) -> dict[str, float]:
        """I parametri non nulli. ⚠️ **Non si filtrano per forma**: un
        parametro dell'altra forma arriva al generatore, che lo rifiuta come
        «sconosciuto». Filtrare qui vorrebbe dire ignorare in silenzio ciò che
        qualcuno ha chiesto — lo stesso difetto che `extra="forbid"` chiude un
        livello più su."""
        return {k: v for k, v in self.model_dump().items()
                if k != "forma" and v is not None}


def _scrivi_glb(m: Modello, destinazione: Path) -> int:
    """Scrive il GLB e ritorna i byte. **L'unico posto che tocca `trimesh`.**

    ⚠️ La scala e' qui e in nessun altro posto: i vertici sono in millimetri
    ovunque nel core e nel renderer, il file e' in metri perche' glTF lo
    prescrive.
    """
    import numpy as np
    import trimesh

    mesh = trimesh.Trimesh(
        vertices=m.posizioni.astype(np.float64) / MM_PER_METRO,
        faces=m.triangoli,
        process=False,          # nessuna fusione di vertici: i conteggi sono l'atteso
    )

    def _extras(albero: dict) -> None:
        # I parametri viaggiano col pezzo: chi apre il file fra sei mesi vede
        # da che numeri e' nato. Si LEGGONO e non si credono — il verificatore
        # guarda i `min`/`max` dell'accessor, che non passano da qui.
        albero.setdefault("asset", {})["extras"] = {
            "generatore": m.nome, "versione": m.versione,
            "unita_parametri": "mm", "params": dict(m.params),
        }

    dati = trimesh.exchange.gltf.export_glb(mesh.scene(), tree_postprocessor=_extras)
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    destinazione.write_bytes(dati)
    return len(dati)


def register_model3d_tools(
    leggi_settings: Callable[[], Settings],
    pubblica: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> None:
    """Registra `genera_modello`.

    `leggi_settings` per funzione come in `core/tools/files.py`: le radici si
    ricaricano a caldo. `pubblica` chiude la catena tool -> socket -> pannello,
    come in `core/tools/web.py`: senza, il file si scrive e non si vede.
    """

    def destinazione(forma: str, quando: float | None = None) -> Path:
        s = leggi_settings()
        stampo = time.strftime("%Y%m%d-%H%M%S",
                               time.localtime(time.time() if quando is None else quando))
        p = Path(s.fs.workspace) / SOTTOCARTELLA / f"{forma}-{stampo}.glb"
        # Risolta contro le radici come qualunque altro percorso: la workspace
        # e' la prima radice per configurazione, e se un giorno non lo fosse
        # questo tool si rifiuterebbe invece di scrivere fuori.
        return risolvi_sotto_radici(p.parent, list(s.fs.allowed_roots)) / p.name

    async def _piano(a: GeneraModelloArgs) -> Piano:
        # ⚠️ Si GENERA nel planner, e non e' spreco: il piano deve poter dire
        # quanto e' grande il pezzo e quanti vertici ha, e parametri che non
        # producono un solido devono essere rifiutati PRIMA di chiedere una
        # conferma. Il modello si rigenera identico nell'handler — e' una
        # funzione pura degli argomenti.
        m = GENERATORI[a.forma](**a.parametri())
        p = destinazione(a.forma)
        dettaglio = (f"{m.bbox[0]:.0f}x{m.bbox[1]:.0f}x{m.bbox[2]:.0f} mm, "
                     f"{m.vertici} vertici, {len(m.triangoli)} triangoli, GLB")
        return Piano(tool="genera_modello",
                     riepilogo=f"genera un solido «{a.forma}» e lo scrive",
                     operazioni=(Operazione(tipo="create", destinazione=p,
                                            dettaglio=dettaglio),))

    async def _genera(a: GeneraModelloArgs, piano: Piano) -> ToolResult:
        p = piano.operazioni[0].destinazione
        if p.exists():
            # Il nome porta i secondi: succede solo se due richieste cadono
            # nello stesso secondo. Non si sovrascrive niente, mai.
            return ToolResult(ok=False, error=f"esiste gia': {p}")
        try:
            m = GENERATORI[a.forma](**a.parametri())
        except ModelloNonValido as exc:
            # Nessuna eccezione arriva all'LLM — stile codice di `CLAUDE.md`.
            return ToolResult(ok=False, error=f"parametri non validi: {exc}")
        try:
            byte = _scrivi_glb(m, p)
        except (OSError, ValueError) as exc:
            return ToolResult(ok=False,
                              error=f"non ho potuto scrivere {p}: {type(exc).__name__}: {exc}")
        log.info("modello_generato", forma=a.forma, path=str(p), byte=byte,
                 vertici=m.vertici, triangoli=len(m.triangoli))
        if pubblica is not None:
            try:
                await pubblica({"topic": TOPIC, "file": str(p), **m.per_il_renderer()})
            except Exception as exc:
                # Il file c'e': qui si perde la vista, non il pezzo.
                log.warning("preview_non_pubblicata", errore=repr(exc))
        return ToolResult(ok=True, output={
            "path": str(p), "forma": a.forma, "bytes": byte,
            "vertici": m.vertici, "triangoli": len(m.triangoli),
            "bbox_mm": [round(v, 3) for v in m.bbox], "params": dict(m.params),
        })

    def _verifica(a: GeneraModelloArgs, piano: Piano, r: ToolResult) -> Verifica:
        """Il file c'e', ha l'intestazione di un GLB, e contiene il pezzo che e'
        stato chiesto — misurato **rileggendolo con la libreria standard**.

        Le tre regole di ADR-012, una per riga:
        l'**atteso** viene dagli ARGOMENTI (`CONTEGGI` e il bbox analitico dei
        parametri), mai dal referto del tool; l'**osservato** viene dal
        **disco**, attraverso `core/model3d/glb_lettore.py`, che non importa
        `trimesh` — cioe' non e' il codice che ha scritto il file; il
        **percorso** viene dal PIANO congelato, non da `a`, che di percorsi non
        ne ha affatto.
        """
        if not r.ok:
            return Verifica.non_verificata(
                f"genera_modello dichiara di non aver eseguito ({r.error}); "
                "senza uno stato di partenza non si puo' distinguere «non "
                "fatto» da «fatto e disfatto»",
                fonte="registry.invoke")
        p = piano.operazioni[0].destinazione
        try:
            m = GENERATORI[a.forma](**a.parametri())
            # ⚠️ Il conteggio viene dalla FORMULA sui parametri, non da `m`:
            # `conteggi_di` applica la regola dei segmenti senza spazzare
            # niente, ed e' la seconda affermazione indipendente sullo stesso
            # numero. Se il generatore emettesse un vertice in piu' di quanti
            # la sua densita' implica, e' qui che si vedrebbe.
            vertici_attesi, _ = CONTEGGI[a.forma](m.params)
            atteso = (f"{p} e' un GLB 2 coerente, {vertici_attesi} vertici, "
                      f"{m.bbox[0]:.1f}x{m.bbox[1]:.1f}x{m.bbox[2]:.1f} mm")
        except (ModelloNonValido, KeyError) as exc:
            return Verifica.non_verificata(
                f"non so che cosa aspettarmi: {type(exc).__name__}: {exc}",
                fonte="i parametri della richiesta")
        try:
            letto = glb_lettore.leggi(p)
        except (OSError, glb_lettore.GlbIllegibile) as exc:
            osservato = f"{p} non si puo' rileggere: {type(exc).__name__}: {exc}"
        else:
            mm = letto.dimensioni_mm()
            # ⚠️ La tolleranza del modello si SOMMA a quella del formato, e non
            # e' un allentamento: un tubo dichiara il cilindro circoscritto —
            # la sezione e' un poligono inscritto — e la differenza ha una
            # forma chiusa che `core/model3d/tubo.py` scrive per esteso. Un
            # modello che non dichiara niente resta al rumore del `float32`.
            ammesso = TOLLERANZA_MM + m.tolleranza_mm
            combacia = all(abs(x - y) <= ammesso
                           for x, y in zip(mm, m.bbox, strict=True))
            stato = ("coerente" if letto.coerente else
                     f"INCOERENTE: dichiara {letto.lunghezza_dichiarata} byte "
                     f"su {letto.byte}")
            # ⚠️ Quando il bbox combacia si scrive quello ATTESO, non il
            # riletto: altrimenti `1,2e-05 mm` di arrotondamento del float32
            # farebbero divergere due stringhe che dicono la stessa misura, e
            # il verdetto sarebbe `FALLITO` per un pezzo giusto. La tolleranza
            # sta nel confronto, non nella formattazione.
            misura = (f"{m.bbox[0]:.1f}x{m.bbox[1]:.1f}x{m.bbox[2]:.1f}" if combacia
                      else f"{mm[0]:.1f}x{mm[1]:.1f}x{mm[2]:.1f}")
            osservato = (f"{p} e' un GLB {letto.versione} {stato}, "
                         f"{letto.vertici} vertici, {misura} mm")
        return Verifica.confronta(
            atteso, osservato,
            fonte="intestazione GLB letta con struct e accessor POSITION del "
                  "chunk JSON, sul percorso risolto del piano")

    register(Tool(
        name="genera_modello",
        description=(
            "Genera un solido parametrico in millimetri da un catalogo chiuso "
            "di forme e lo scrive come file GLB nella workspace. `estrusione_45` "
            "e' una piastra smussata con foro passante; `tubo_piegato` e' una "
            "linea di tubo con corse dritte e pieghe a raggio costante, come si "
            "programma su una piegatrice. Le misure sono in millimetri; nessun "
            "percorso: la destinazione la decide il core."
        ),
        args_schema=GeneraModelloArgs,
        side_effect=True,
        # Invariante 27: nessuna gesture puo' innescare un tool che scrive.
        gesture_allowed=False,
        planner=_piano,
        handler=_genera,
        verifica=_verifica,
    ))
