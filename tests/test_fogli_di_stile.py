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
#: composta, come `export const css = cssDisegno + cssMesh + cssSpettro + \``.
#:
#: ⚠️ **QUANTI ADDENDI, ed e' la correzione del 31 agosto 2026.** La stesura
#: precedente era `(?:\w+ \+ )?` — al piu' UNO. `ui/src/desk/sfondo.js` ne
#: compone tre, e il file smetteva di essere coperto in silenzio: la guardia
#: non falliva, semplicemente non guardava. Un backtick e' finito nel suo CSS
#: due volte nello stesso turno e a trovarlo e' stato il browser, non il test.
#:
#: E' la stessa specie del difetto che questa guardia esiste per prendere: una
#: regola che c'e' ma non gira. Adesso gli addendi sono `*` invece che `?`, e
#: `test_ogni_foglio_e_COPERTO` conta che nessun file resti fuori.
APERTURA = re.compile(r"export const (css\w*) = (?:\w+ \+ )*`")


def fogli() -> list[tuple[Path, str, str]]:
    """Ogni blocco di stile del progetto: file, nome dell'export, contenuto."""
    fuori = []
    for f in sorted(SORGENTI.rglob("*.js")):
        testo = f.read_text(encoding="utf-8")
        for m in APERTURA.finditer(testo):
            i = m.end()
            # ⚠️ DUE FORME DI CHIUSURA, e la seconda mancava.
            #
            # Un foglio disteso su piu' righe chiude con `\n\`;` in colonna
            # zero, ed e' il caso normale. Ma un foglio che compone e basta —
            # `ui/src/gallery/mounts/chrome.js` — sta tutto su UNA riga e
            # chiude in fondo a quella: `find("\n\`;")` non lo trovava mai e il
            # `continue` lo scartava in silenzio. Un file scartato non e' un
            # file pulito, e la differenza non si vedeva da nessuna parte.
            #
            # L'ordine conta: si guarda PRIMA la riga di apertura. Cercare
            # `\`;` senza ancorarsi a inizio riga si fermerebbe al primo
            # backtick spaiato dentro il corpo — cioe' proprio al difetto che
            # questa guardia cerca — e il corpo tornerebbe troncato prima di
            # lui, facendo passare il test.
            fine_riga = testo.find("\n", i)
            resto = testo[i:fine_riga if fine_riga >= 0 else len(testo)]
            if "`;" in resto:
                fuori.append((f, m.group(1), resto[:resto.index("`;")]))
                continue
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

    def test_ogni_foglio_e_COPERTO(self) -> None:
        """⚠️ La guardia non deve poter diventare cieca in silenzio.

        `test_nessun_backtick...` non puo' bocciare un file che `APERTURA` non
        riconosce, e il 31 agosto 2026 e' successo: `sfondo.js` compone tre
        fogli e la regex ne ammetteva uno, quindi il file era fuori copertura
        senza che nulla lo dicesse. Il test era verde **per assenza del
        fenomeno** — §11.7 regola 4, `non misurabile` non conta come verde.

        Qui si confrontano due conteggi ottenuti in due modi diversi: chi
        dichiara un export di stile, e chi la regex riesce a leggere. Se
        divergono, e' la regex a essere indietro.
        """
        # ⚠️ A RISCHIO e' chi APRE un template literal, non chi esporta uno
        # stile. Venticinque mount di galleria fanno `export const css =
        # cssAnelli;` — un alias, senza letterale e senza backtick da chiudere:
        # includerli renderebbe questo test rumore, e un test rumoroso viene
        # allentato invece che ascoltato.
        # Il backtick sulla stessa riga della dichiarazione e' la forma di ogni
        # foglio di questo repo, ed e' esattamente cio' che `APERTURA` deve
        # saper leggere.
        dichiarano = {
            f.relative_to(RADICE).as_posix()
            for f in sorted(SORGENTI.rglob("*.js"))
            if re.search(r"^export const css\w* =[^\n]*`", f.read_text(encoding="utf-8"), re.M)
        }
        letti = {f.relative_to(RADICE).as_posix() for f, _, _ in fogli()}
        scoperti = sorted(dichiarano - letti)
        assert not scoperti, (
            f"{len(scoperti)} file esportano un foglio di stile che la guardia "
            f"dei backtick non legge: {scoperti}.\n"
            "Non e' un falso allarme innocuo: quei file NON sono protetti, e un "
            "backtick li' dentro rompe il modulo a runtime invece che in test. "
            "Allarga `APERTURA`."
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
