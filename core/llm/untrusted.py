"""Contenuto NON FIDATO — invariante 5, SPEC §12.

> «`<webview>`, news, ARGUS e file letti sono DATO NON FIDATO. Solo in contesti
> con zero tool. Marcati `<untrusted_source>`.»

Una regola cosi' non sopravvive se dipende dal ricordarsene a ogni chiamata:
basta un percorso nuovo, scritto di fretta fra sei mesi, e il testo di una
pagina web finisce in un prompt che ha i tool accesi. Qui la regola diventa un
TIPO, e la barriera la impone chi spawna.

Tre proprieta', e ognuna chiude un modo di sbagliare:

  1. **Non e' una stringa.** `Untrusted` non deriva da `str`, quindi non si
     concatena per distrazione. `__str__` e `__format__` SOLLEVANO: l'unico
     modo di ottenere il testo e' `avvolto()`, che marca, o `grezzo()`, che ha
     un nome che si nota in una revisione.

  2. **`__repr__` non mostra il contenuto.** Un log, un traceback o un
     `print()` di debug mostrano origine e lunghezza. Il testo di una pagina
     ostile non finisce nei log — dove qualcun altro potrebbe rileggerlo e
     darlo in pasto a qualcosa.

  3. **Il marcatore non si puo' chiudere dall'interno.** Un contenuto che
     contenesse `</untrusted_source>` uscirebbe dalla busta e il resto
     sembrerebbe testo fidato. E' l'attacco piu' ovvio contro questo schema, e
     `avvolto()` lo neutralizza.

La barriera vera e' in `core/llm/claude_t2.py`: uno spawn con tool attivi
RIFIUTA un `Untrusted`. Fail-closed come il registry di Fase 1 — dimenticare
la regola rende il sistema inerte, non permissivo.
"""

from __future__ import annotations

from dataclasses import dataclass

APERTURA = "<untrusted_source"
CHIUSURA = "</untrusted_source>"

# Cio' con cui si sostituisce un tentativo di chiudere la busta dall'interno.
# Resta leggibile — chi legge capisce cosa c'era — ma non e' piu' un tag.
NEUTRO = "&lt;/untrusted_source&gt;"


class ContenutoNonFidato(Exception):
    """Contenuto non fidato verso un contesto che ha dei tool."""


@dataclass(frozen=True)
class Untrusted:
    """Testo che viene da fuori: pagina web, OCR, news, file letto.

    `origine` finisce nell'attributo del marcatore e serve a chi legge — o a
    chi indaga dopo — per sapere da dove veniva.
    """

    origine: str
    _testo: str

    @staticmethod
    def da(origine: str, testo: str) -> Untrusted:
        if not origine or '"' in origine:
            raise ValueError(f"origine non valida: {origine!r}")
        return Untrusted(origine=origine, _testo=str(testo))

    # ── le tre proprieta' ────────────────────────────────────────────────────

    def __str__(self) -> str:  # pragma: no cover - deve solo sollevare
        raise ContenutoNonFidato(
            f"contenuto non fidato da {self.origine} usato come stringa. "
            "Usa avvolto() per il marcatore di §12, o grezzo() se sai perche'."
        )

    def __format__(self, _spec: str) -> str:  # pragma: no cover
        return self.__str__()

    def __repr__(self) -> str:
        return f"<Untrusted origine={self.origine!r} caratteri={len(self._testo)}>"

    def __len__(self) -> int:
        return len(self._testo)

    def avvolto(self) -> str:
        """Il marcatore di §12, con la busta che non si puo' chiudere da dentro."""
        dentro = self._testo.replace(CHIUSURA, NEUTRO).replace(APERTURA, "&lt;untrusted_source")
        return f'<untrusted_source origin="{self.origine}">\n{dentro}\n{CHIUSURA}'

    def grezzo(self) -> str:
        """Il testo com'e'. Per mostrarlo all'utente, mai per un prompt con tool."""
        return self._testo
