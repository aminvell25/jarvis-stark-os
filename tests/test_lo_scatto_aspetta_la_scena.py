"""Il «DENSITÀ CONFORME» del 27 agosto era uno su cinque.

## La misura della misura

Cinque giri di `npm run verifica:densita` sugli **stessi identici sorgenti**, con
nessun altro Electron in competizione:

    giro      1      2      3      4      5     soglia
    entropia  2.300  2.320  2.335  2.430  2.335   2.4
    riempito  23.10  23.70  24.30  28.00  24.30   25
    dock      18.2   18.2   12.6   24.2   12.6    20
    esito     ❌     ❌     ❌     ✅     ❌

**Uno su cinque passava.** E il giro che passava è esattamente il profilo
committato in `2745cb2` con la dicitura «densità rimisurata — l'ultimo rosso
dichiarato è chiuso»: quel verde era il lancio di moneta.

## La causa

`scattaScrivania()` aspettava `attendiSilenzio()`, che guarda l'ultimo messaggio
arrivato dal riproduttore — il silenzio dell'**ingresso**. I pannelli si
compongono, si animano e il dock si riempie **dopo**. Il dock che oscilla fra
12,6 e 24,2 non è rumore della metrica: è la scrivania fotografata a metà
composizione.

## Dopo

    giro      1      2      3      4      5
    entropia  2.430  2.430  2.430  2.430  2.430
    riempito  28.00  28.00  28.00  28.00  28.00
    dock      24.2   24.2   24.2   24.2   24.2

Identici alla terza cifra. Da qui in poi un numero di §11.9 descrive il disegno
e non il momento dello scatto.
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _main_js() -> str:
    return (RADICE / "app" / "main.js").read_text(encoding="utf-8")


def _senza_commenti(s: str) -> str:
    """Il codice, non le spiegazioni. Settima volta che serve in questa sessione."""
    fuori, in_blocco = [], False
    for r in s.splitlines():
        t = r
        if in_blocco:
            if "*/" in t:
                t = t.split("*/", 1)[1]
                in_blocco = False
            else:
                t = ""
        if "/*" in t:
            testa, resto = t.split("/*", 1)
            if "*/" in resto:
                t = testa + resto.split("*/", 1)[1]
            else:
                t, in_blocco = testa, True
        t = t.split("//", 1)[0]
        fuori.append(t)
    return "\n".join(fuori)


class TestLoScattoAspettaLaScena:
    def test_la_funzione_ESISTE(self) -> None:
        assert "async function attendiScenaFerma(" in _senza_commenti(_main_js())

    def test_e_si_chiama_DOPO_il_silenzio_dei_dati(self) -> None:
        """L'ordine è la sostanza: il silenzio dell'ingresso è la precondizione,
        non la conclusione."""
        c = _senza_commenti(_main_js())
        corpo = c.split("async function scattaScrivania", 1)[1].split("\nasync function ", 1)[0]
        assert "attendiSilenzio()" in corpo and "attendiScenaFerma()" in corpo
        assert corpo.index("attendiSilenzio()") < corpo.index("attendiScenaFerma()")

    def test_e_PRIMA_di_qualunque_scatto(self) -> None:
        c = _senza_commenti(_main_js())
        corpo = c.split("async function scattaScrivania", 1)[1].split("\nasync function ", 1)[0]
        assert "capturePage()" in corpo
        assert corpo.index("attendiScenaFerma()") < corpo.index("capturePage()")

    def test_confronta_la_FIRMA_e_non_i_pixel(self) -> None:
        """⚠️ Due scatti byte a byte non convergono mai: gli orologi vivi
        cambiano un pixel al secondo per sempre. Si confronta ciò che varia fra
        un giro e l'altro — quali pannelli, dove, quanto grandi, e il dock."""
        c = _senza_commenti(_main_js())
        f = c.split("async function attendiScenaFerma", 1)[1].split("\nasync function ", 1)[0]
        assert "getBoundingClientRect()" in f and "dock" in f
        assert "toPNG" not in f and "capturePage" not in f

    def test_una_scena_che_non_si_ferma_lo_DICE(self) -> None:
        """Uno scatto preso a scena in movimento non è attribuibile, e un numero
        non attribuibile è peggio di nessun numero."""
        f = _main_js().split("async function attendiScenaFerma", 1)[1].split(
            "\nasync function ", 1)[0]
        assert "non si e' mai fermata" in f
        assert "return false" in _senza_commenti(f)

    def test_la_stabilita_richiede_PIU_di_un_campione(self) -> None:
        """Un solo campione uguale al precedente non è stabilità: è una
        coincidenza fra due istanti."""
        c = _senza_commenti(_main_js())
        f = c.split("async function attendiScenaFerma", 1)[1].split("\nasync function ", 1)[0]
        assert "uguali = 2" in f or "uguali=2" in f
        assert ">= uguali" in f
