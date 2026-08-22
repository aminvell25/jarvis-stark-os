"""`ui/src/style/tokens.css` — la sorgente unica di verita' del design (§10.1).

`ui/src/style/fonts.css` dichiara, nella propria intestazione, che tokens.css
«e' la copia verbatim di SPEC §10.1 e non deve divergere di un byte dalla
specifica». Fino alla rev 5.8 quella frase era una promessa: **nessuno la
verificava.** Un invariante che la macchina non controlla decade, ed e' lo
stesso principio con cui `core/settings.py` impone gli invarianti 4, 11 e 27
dallo schema invece che dalla disciplina.

Il costo di lasciarlo scoperto non e' teorico: chi legge la specifica per
costruire un componente costruirebbe contro il documento sbagliato, e se ne
accorgerebbe solo guardando uno screenshot.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
TOKENS = RADICE / "ui" / "src" / "style" / "tokens.css"
SPEC = RADICE / "docs" / "SPEC.md"

#: I valori MISURATI sul riferimento (`docs/DIVARIO-PREMIUM.md` §1, tabella dei
#: colori dominanti di `famiglia-a/01`). Ripetuti qui di proposito: se qualcuno
#: cambia un valore in tokens.css senza passare da una nuova misura, questi
#: test lo fermano.
#:
#: ⚠️ Tre registri, non una rampa (rev 5.9). La 5.8 aveva dichiarato SEI
#: riempimenti, e i due piu' bassi erano duplicati delle superfici di base alla
#: luminanza giusta: la leva era `--bg-panel`, che copre il 71,2 % della
#: scrivania, non un token nuovo accanto a esso.
SUPERFICI = {
    "--bg-void": "#0f1418",                                   # L 19 pavimento
    "--bg-deep": "#1a1f23", "--bg-panel": "#13212a", "--bg-raised": "#1e2631",
}
RIEMPIMENTI = {
    "--fill-1": "#32464f", "--fill-2": "#336276", "--fill-3": "#4d6d78",
    "--manila": "#b48d64",
}


def blocco_di_spec() -> str:
    """Il blocco ```css di §10.1, senza le due righe di recinzione."""
    testo = SPEC.read_text(encoding="utf-8")
    i = testo.index("## 10.1 Token")
    apre = testo.index("```css", i) + len("```css\n")
    chiude = testo.index("\n```", apre)
    return testo[apre:chiude] + "\n"


def custom() -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", TOKENS.read_text(encoding="utf-8")))


def contrasto(a: str, b: str) -> float:
    """Rapporto WCAG: `(L1+0,05)/(L2+0,05)` su luminanza **linearizzata**.

    Non e' la Rec. 709 su 0-255 di `luminanza()`: quella misura quanta
    superficie e' accesa in uno screenshot, questa misura se un testo si legge.
    Confonderle e' l'errore che ha prodotto il numero sbagliato in
    `DIVARIO-PREMIUM.md` §3.
    """
    def rel(h: str) -> float:
        canali = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
               for s in canali]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    x, y = sorted((rel(a) + 0.05, rel(b) + 0.05), reverse=True)
    return x / y


def luminanza(hexa: str) -> float:
    """Rec. 709 su 0–255. La stessa formula di `scripts/densita.mjs`, che e'
    quella con cui sono stati misurati il riferimento e i nostri screenshot."""
    r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class TestNonDivergono:
    def test_tokens_css_e_spec_10_1_sono_lo_STESSO_testo(self) -> None:
        """Byte a byte, non «equivalenti».

        Non si confrontano i valori estratti: si confronta il testo. I commenti
        di §10.1 dicono cose che il codice non dice — «SEMPRE zero», «MAX 10%
        della superficie colorata», le luminanze accanto ai riempimenti — e
        sono meta' del valore della sezione. Due file che dichiarano gli stessi
        token con commenti diversi sono gia' divergenti.
        """
        assert blocco_di_spec() == TOKENS.read_text(encoding="utf-8"), (
            "tokens.css e docs/SPEC.md §10.1 sono divergenti. La specifica e' "
            "il documento che si legge PRIMA di costruire: chi la seguisse "
            "costruirebbe contro valori che non girano."
        )

    def test_la_specifica_dichiara_la_revisione_giusta(self) -> None:
        """§10.1 non si tocca senza una riga negli emendamenti: e' la tabella
        da cui si capisce PERCHE' un token esiste, mesi dopo."""
        testo = SPEC.read_text(encoding="utf-8")
        rev = re.search(r"\*\*Rev (\d+\.\d+) ·", testo)
        assert rev, "la SPEC non dichiara una revisione"
        assert f"| {rev.group(1)} |" in testo, (
            f"la rev {rev.group(1)} non ha una riga nella tabella degli emendamenti"
        )


class TestITreRegistri:
    """Il motivo per cui esistono la rev 5.8 e la sua correzione, la 5.9.

    La misura di `DIVARIO-PREMIUM.md` §1: fra `--bg-raised` e `--cy-500` (L
    181) non c'era **un solo token usato come riempimento**, e quel salto lo
    faceva un bordo da un pixel. Il riferimento vive in quella banda.

    La 5.8 ha risposto aggiungendo sei token accanto alle superfici. Sbagliato:
    le superfici erano gia' li' e bastava spostarle. La 5.9 le sposta e tiene
    tre riempimenti per gli STATI.
    """

    @pytest.mark.parametrize("nome,valore",
                             sorted(SUPERFICI.items()) + sorted(RIEMPIMENTI.items()))
    def test_il_ruolo_c_e_col_valore_misurato(self, nome: str, valore: str) -> None:
        assert custom().get(nome) == valore

    def test_la_scala_delle_superfici_NON_e_invertita(self) -> None:
        """R80, chiuso — e chiuso da un test, non da un commento.

        La 5.8 ha alzato il pavimento e lasciato dov'erano barra, dock e corpo
        del pannello: il fondo (L 19) e' finito **sopra** `--bg-deep` (15) e
        `--bg-panel` (18), e i pannelli si distinguevano solo per il bordo.
        E' caduta una volta, e ricadrebbe: il prossimo che tocca una di queste
        quattro righe non ha modo di accorgersene guardando il file.
        """
        c = custom()
        l = {n: luminanza(c[n]) for n in SUPERFICI}
        assert l["--bg-void"] < l["--bg-deep"], (
            f"il pavimento (L {l['--bg-void']:.0f}) e' sopra la barra "
            f"(L {l['--bg-deep']:.0f}): la scrivania e' piu' chiara di cio' "
            f"che ci sta sopra"
        )
        assert l["--bg-deep"] <= l["--bg-panel"] < l["--bg-raised"], (
            f"barra {l['--bg-deep']:.0f}, pannello {l['--bg-panel']:.0f}, "
            f"rilievo {l['--bg-raised']:.0f}: l'ordine non regge"
        )

    def test_barra_e_pannello_stanno_nella_STESSA_banda(self) -> None:
        """Non e' una svista da correggere: e' la misura del riferimento.

        La barra si distingue per **densita' d'inchiostro** — decine di
        micro-etichette su una linea di base, 28-37 % di pixel L>50 — non per
        il fondo. Chi "sistemasse" la rampa distruggerebbe la cosa misurata,
        e questo test glielo dice prima.
        """
        c = custom()
        delta = abs(luminanza(c["--bg-deep"]) - luminanza(c["--bg-panel"]))
        assert delta <= 4, (
            f"barra e pannello distano {delta:.0f} punti di luminanza: nel "
            f"riferimento stanno nella stessa banda (30-37)"
        )

    def test_i_riempimenti_stanno_SOPRA_la_banda_di_superficie(self) -> None:
        """Un riempimento dice uno STATO. Se sta dentro la banda delle
        superfici non dice niente: e' un'altra superficie con un altro nome,
        ed e' esattamente l'errore della 5.8."""
        c = custom()
        piu_alta = max(luminanza(c[n]) for n in SUPERFICI)
        piu_basso = min(luminanza(c[n]) for n in RIEMPIMENTI)
        assert piu_basso > piu_alta + 20, (
            f"il riempimento piu' basso e' L {piu_basso:.0f} e la superficie "
            f"piu' alta L {piu_alta:.0f}: troppo vicini per dire uno stato"
        )

    def test_la_scala_dei_riempimenti_sale_senza_buchi(self) -> None:
        """`--fill-1..3` in ordine crescente, e ognuno distinto: sono ruoli —
        cella attiva, pannello acceso, evidenza — e un ruolo che non si
        distingue dal precedente non esiste."""
        c = custom()
        scala = [luminanza(c[f"--fill-{i}"]) for i in range(1, 4)]
        assert scala == sorted(scala), f"la scala non sale: {scala}"
        assert all(b - a >= 5 for a, b in zip(scala, scala[1:])), (
            f"due gradini troppo vicini per essere ruoli diversi: {scala}"
        )

    def test_la_banda_fra_bg_raised_e_cy_500_non_e_piu_vuota(self) -> None:
        """Il difetto misurato in §1, enunciato come proprieta'."""
        c = custom()
        basso, alto = luminanza(c["--bg-raised"]), luminanza(c["--cy-500"])
        dentro = [n for n, v in RIEMPIMENTI.items() if basso < luminanza(v) < alto]
        assert len(dentro) >= 3, (
            f"solo {len(dentro)} riempimenti fra L {basso:.0f} e L {alto:.0f}"
        )

    def test_il_fondo_e_quello_del_riferimento(self) -> None:
        """`#0f1418`, misurato su `famiglia-a/01`."""
        assert custom()["--bg-void"] == "#0f1418"
        assert 18 <= luminanza("#0f1418") <= 20


class TestIlContrastoDelTesto:
    """⚠️ **Un pavimento, non un attestato.**

    Alzare `--bg-panel` da L 18 a L 31 ha fatto scendere il contrasto di tutto
    cio' che ci sta sopra, e tre soglie WCAG sono state attraversate. Il
    rilievo e' aperto e DICHIARATO in `docs/acceptance/TOKENS-RIEMPIMENTO.md`:
    questi numeri non sono il traguardo, sono il punto piu' basso a cui e'
    ammesso stare mentre il rilievo resta aperto.

    Servono perche' il passo successivo tocca 18 componenti: senza un pavimento
    misurato, un'altra erosione di mezzo punto passerebbe inosservata come e'
    passata questa.
    """

    #: (testo, fondo, minimo che NON si puo' scendere). Rialzati con la rev
    #: 5.10, quando R81 e' stata chiusa: adesso non sono piu' un pavimento
    #: sotto un difetto, sono la soglia WCAG dove la soglia si raggiunge.
    COPPIE = [
        ("--txt-primary", "--bg-panel", 13.0),
        ("--txt-dim", "--bg-panel", 4.5),      # WCAG testo normale ✅
        ("--txt-ghost", "--bg-panel", 3.0),    # WCAG UI / testo grande ✅
        ("--cy-500", "--bg-panel", 8.0),
        ("--cy-700", "--bg-panel", 3.0),       # WCAG UI ✅
        ("--txt-primary", "--bg-deep", 13.0),
        ("--txt-dim", "--bg-raised", 4.2),     # ⚠️ resta sotto 4,5: vedi R81b
        # I riempimenti di stato reggono il testo primario, e va detto:
        ("--txt-primary", "--fill-1", 8.0),
        ("--txt-primary", "--fill-2", 5.4),
        ("--txt-primary", "--fill-3", 4.5),
        ("--bg-void", "--manila", 6.1),        # testo scuro su manila
    ]

    @pytest.mark.parametrize("testo,fondo,minimo", COPPIE)
    def test_non_scende_sotto_il_pavimento_misurato(
        self, testo: str, fondo: str, minimo: float
    ) -> None:
        c = custom()
        r = contrasto(c[testo], c[fondo])
        assert r >= minimo, (
            f"{testo} su {fondo} e' sceso a {r:.2f}:1, sotto il pavimento di "
            f"{minimo}:1 misurato alla rev 5.9"
        )


class TestGliInvariantiScrittiNeiCommenti:
    """§10.1 contiene tre affermazioni assolute. Valgono ancora."""

    def test_il_raggio_e_sempre_zero(self) -> None:
        assert custom()["--radius"] == "0"          # invariante 18

    def test_i_pesi_di_linea_sono_TRE(self) -> None:
        assert sum(1 for n in custom() if n.startswith("--line-")) == 3

    def test_i_gradini_tipografici_sono_SEI(self) -> None:
        """⚠️ Erano CINQUE fino al 22 agosto 2026, e il cambio e' una decisione.

        §11.6 regola 1 diceva «due font, cinque corpi, nessuna deroga», e il
        numero era giusto finche' nessun pannello aveva bisogno di una lettura
        che occupasse il proprio riquadro. `panels/lettura.js` ce l'ha: il
        riferimento famiglia-a/03 porta una cifra alta 28 px su un'immagine
        larga 901, cioe' il **3,1 % della larghezza**, che sui nostri 1536 fa
        48 — e nessuno dei cinque gradini ci arrivava, perche' il piu' alto
        (--t-title, 20 px) e' il corpo dei numeri di UNA CELLA del calendario.

        La prima stesura lo derivava dentro il componente con
        «calc(--t-title * 2.4)»: stessa cifra, ma invisibile all'audit — che
        infatti la bocciava come 48 px letterali — e non contestabile, perche'
        per trovarla bisognava leggere quel file.

        Un gradino in piu' dichiarato e' peggio di cinque solo se non ha una
        misura accanto. Questo ce l'ha, ed e' scritta in tokens.css.
        """
        assert sum(1 for n in custom() if n.startswith("--t-")) == 6
        assert "--t-display" in custom(), (
            "il sesto gradino non e' --t-display: se ne e' stato aggiunto un "
            "altro, la misura che lo giustifica va scritta come per questo"
        )


# ── l'altro duplicato dichiarato ─────────────────────────────────────────────


class TestGliInvariantiNonDivergono:
    """SPEC §20 contiene `CLAUDE.md` **per intero**, dentro un blocco.

    E' lo stesso invariante di `tokens.css` ≡ §10.1, ed era scoperto allo
    stesso modo. Alla rev 5.13 il confronto ha trovato che erano divergenti
    **da diverse fasi**: a §20 mancavano 39 righe, fra cui l'invariante 30 sul
    copyright del codice di terzi — che e' una regola legale, non una
    preferenza di stile.

    Il documento che si legge PRIMA di costruire e' la specifica. Se dice meno
    di `CLAUDE.md`, chi la segue costruisce con meno regole di quelle che ci
    sono.
    """

    def blocco(self) -> str:
        testo = SPEC.read_text(encoding="utf-8")
        i = testo.index("# 20. `CLAUDE.md` completo")
        apre = testo.index("```markdown", i) + len("```markdown\n")
        chiude = testo.index("\n```", apre)
        return testo[apre:chiude] + "\n"

    def test_la_copia_in_SPEC_20_e_il_file_vero(self) -> None:
        claude = (RADICE / "CLAUDE.md").read_text(encoding="utf-8")
        assert self.blocco() == claude, (
            "CLAUDE.md e SPEC §20 sono divergenti. Chi legge la specifica "
            "costruirebbe con un elenco di invarianti diverso da quello che "
            "governa il progetto."
        )

    def test_l_invariante_19_ammette_l_ombra_e_vieta_l_alone(self) -> None:
        """Rev 5.13. La riformulazione, verificata dove vive — in tutte e due
        le copie, che il test qui sopra tiene uguali."""
        claude = (RADICE / "CLAUDE.md").read_text(encoding="utf-8")
        i = claude.index("19. **")
        diciannove = claude[i:claude.index("20. **", i)]
        assert "ZERO glow" in diciannove and "ZERO bloom" in diciannove
        assert "alone luminoso" in diciannove
        assert "nera, senza colore" in diciannove
        assert "drop-shadow" not in diciannove, (
            "l'invariante 19 non vieta piu' ogni ombra portata: vieta l'ALONE. "
            "Nominare drop-shadow qui rimetterebbe la contraddizione che §10.1 "
            "e app.css hanno portato per due fasi"
        )
