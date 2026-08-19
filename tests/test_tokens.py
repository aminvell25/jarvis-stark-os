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

#: I sei ruoli aggiunti dalla rev 5.8, coi valori MISURATI sul riferimento
#: (`docs/DIVARIO-PREMIUM.md` §1, tabella dei colori dominanti di
#: `famiglia-a/01`). Ripetuti qui di proposito: se qualcuno cambia un valore in
#: tokens.css senza passare da una nuova misura, questo test lo ferma.
RIEMPIMENTI = {
    "--fill-1": "#13212a", "--fill-2": "#1e2631", "--fill-3": "#32464f",
    "--fill-4": "#336276", "--fill-5": "#4d6d78", "--manila": "#b48d64",
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


class TestLaBandaMedia:
    """Il motivo per cui la rev 5.8 esiste.

    La misura di `DIVARIO-PREMIUM.md` §1: fra `--bg-raised` (L 25) e
    `--cy-500` (L 181) non c'era **un solo token usato come riempimento**, e
    quel salto di 156 punti lo faceva un bordo da un pixel. Il riferimento
    vive per intero in quella banda.
    """

    @pytest.mark.parametrize("nome,valore", sorted(RIEMPIMENTI.items()))
    def test_il_ruolo_c_e_col_valore_misurato(self, nome: str, valore: str) -> None:
        assert custom().get(nome) == valore

    def test_la_scala_sale_senza_buchi(self) -> None:
        """`--fill-1..5` in ordine di luminanza crescente, e ognuno distinto.

        Non e' pedanteria: sono ruoli — riga alternata, cella attiva, pannello
        acceso — e un ruolo che non si distingue dal precedente non esiste.
        """
        c = custom()
        scala = [luminanza(c[f"--fill-{i}"]) for i in range(1, 6)]
        assert scala == sorted(scala), f"la scala non sale: {scala}"
        assert all(b - a >= 5 for a, b in zip(scala, scala[1:])), (
            f"due gradini troppo vicini per essere ruoli diversi: {scala}"
        )

    def test_la_banda_fra_bg_raised_e_cy_500_non_e_piu_vuota(self) -> None:
        """Il difetto misurato, enunciato come proprieta'."""
        c = custom()
        basso, alto = luminanza(c["--bg-raised"]), luminanza(c["--cy-500"])
        dentro = [n for n, v in RIEMPIMENTI.items() if basso < luminanza(v) < alto]
        assert len(dentro) >= 5, (
            f"solo {len(dentro)} riempimenti fra L {basso:.0f} e L {alto:.0f}"
        )

    def test_il_fondo_e_quello_del_riferimento(self) -> None:
        """`#0f1418`, misurato su `famiglia-a/01`. Un nero meno assoluto
        AUMENTA il contrasto percepito degli elementi chiari, non lo riduce —
        ed e' anche cio' che rende leggibile `--cy-900` come bordo (§3)."""
        assert custom()["--bg-void"] == "#0f1418"
        assert 18 <= luminanza("#0f1418") <= 20


class TestGliInvariantiScrittiNeiCommenti:
    """§10.1 contiene tre affermazioni assolute. Valgono ancora."""

    def test_il_raggio_e_sempre_zero(self) -> None:
        assert custom()["--radius"] == "0"          # invariante 18

    def test_i_pesi_di_linea_sono_TRE(self) -> None:
        assert sum(1 for n in custom() if n.startswith("--line-")) == 3

    def test_i_gradini_tipografici_sono_CINQUE(self) -> None:
        assert sum(1 for n in custom() if n.startswith("--t-")) == 5
