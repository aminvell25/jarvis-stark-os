"""Un backtick dentro un foglio di stile chiude il modulo, e non lo dice nessuno.

## Perche' questo test esiste

Ogni componente esporta il proprio CSS come **template literal**:

    export const css = `
    .pnl-x { ... }
    `;

Un backtick dentro quel blocco — tipicamente in un commento, per citare un
file o un token — **chiude il letterale**. Quel che segue diventa codice, e il
modulo non si carica piu'. L'errore che arriva e' `SyntaxError: Unexpected
identifier 'famiglia'`, cioe' il nome del file che si stava citando: non dice
ne' dove ne' perche', e la galleria mostra una pagina vuota.

E' successo **quindici volte** nel corso di una sola giornata di lavoro, sempre
allo stesso modo e sempre trovato a mano dopo che qualcosa era gia' rotto. Un
difetto che si ripete quindici volte non e' distrazione: e' una regola che
manca.

## Perche' non basta vietare i backtick nei file

Perche' i template literal servono: `crea()` li usa per comporre l'HTML, e
`rings.js` compone `css` da `cssDisegno`. Il divieto vale **solo dentro il
blocco di stile**, che e' esattamente dove non se ne ha mai bisogno — un foglio
CSS non contiene interpolazioni.
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
SORGENTI = RADICE / "ui" / "src"

#: L'apertura di un foglio: `export const css = \`` oppure una sua variante
#: composta, come `export const css = cssDisegno + \``.
APERTURA = re.compile(r"export const (css\w*) = (?:\w+ \+ )?`")


def fogli() -> list[tuple[Path, str, str]]:
    """Ogni blocco di stile del progetto: file, nome dell'export, contenuto."""
    fuori = []
    for f in sorted(SORGENTI.rglob("*.js")):
        testo = f.read_text(encoding="utf-8")
        for m in APERTURA.finditer(testo):
            i = m.end()
            j = testo.find("\n`;", i)
            if j < 0:
                continue
            fuori.append((f, m.group(1), testo[i:j]))
    return fuori


class TestIFogliDiStileSiChiudonoDoveDevono:
    def test_nessun_backtick_dentro_un_foglio_di_stile(self) -> None:
        """Il difetto che ha morso quindici volte in un giorno.

        Il messaggio nomina il file, l'export e la citazione incriminata,
        perche' la cosa che manca quando succede e' proprio sapere DOVE.
        """
        colpevoli = []
        for f, nome, corpo in fogli():
            if "`" not in corpo:
                continue
            citazioni = re.findall(r"`[^`\n]*`", corpo) or ["(backtick spaiato)"]
            colpevoli.append(
                f"  {f.relative_to(RADICE)} · {nome} · {', '.join(citazioni[:4])}"
            )
        assert not colpevoli, (
            "backtick dentro un foglio di stile: chiude il template literal e "
            "il modulo non si carica piu'.\n" + "\n".join(colpevoli) + "\n"
            "Nei commenti CSS si cita senza backtick — un foglio di stile non "
            "ha interpolazioni, quindi li' un backtick non serve mai."
        )

    def test_i_fogli_esistono_davvero(self) -> None:
        """Un test che non trova niente da controllare passa sempre.

        Senza questa riga, un giorno che l'espressione di apertura smettesse di
        combaciare — un `export const css` scritto diversamente — il controllo
        di sopra continuerebbe a passare su zero fogli.
        """
        trovati = fogli()
        assert len(trovati) >= 20, (
            f"trovati solo {len(trovati)} fogli di stile: l'espressione di "
            "apertura non combacia piu' con come li scrive il progetto."
        )
