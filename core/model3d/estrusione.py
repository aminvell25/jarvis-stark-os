"""Generatore ③ di §17.4 — estrusione asimmetrica con foro passante.

**Perche' questo per primo, e non il tubo su spline.** Tre ragioni misurabili,
e tutt'e tre servono al verificatore di ADR-012 piu' che alla forma:

1. il **bbox e' analitico** dai parametri. Gli smussi tagliano gli angoli
   verso l'interno e non spostano gli estremi, quindi il bbox e' esattamente
   `larghezza x altezza x profondita`. Nessuna tolleranza inventata: §11.10
   regola 7 diventa un'uguaglianza, non un «entro il 2 %»;
2. la **topologia e' verificabile**: un solido con un foro passante ha
   `euler_number == 0` (32 vertici, 96 spigoli, 64 triangoli) ed e'
   `is_watertight`. Sono due domande a cui `trimesh` risponde di suo, e la
   risposta non passa da questo codice;
3. i **conteggi sono chiusi**: 32 vertici e 64 triangoli, sempre. Il
   verificatore li ricava dagli ARGOMENTI e li confronta con l'accessor del
   file, senza credere a niente che venga da qui.

⚠️ **Nessuna geometria standard** (§11.10 regola 5): §17.4 ③ prescriveva
`THREE.ExtrudeGeometry`, e ADR-014 l'ha tolta insieme al posto in cui girava.
Qui i vertici escono da due anelli e quattro strisce di quadrilateri.

⚠️ **L'asimmetria e' PROGETTATA** (§11.10 regola 4): i quattro smussi devono
essere diversi almeno in uno, e chi li passa tutti uguali riceve un rifiuto con
la ragione — non un pezzo simmetrico che sembra un errore di battitura.
"""

from __future__ import annotations

import numpy as np

from core.model3d.parametrico import Modello, ModelloNonValido

NOME = "estrusione-45"
VERSIONE = "v1"

#: Quanto materiale deve restare fra il foro e il bordo. Non e' una regola di
#: geometria — un solido con 0,1 mm di parete e' valido — ma di **pezzo**: sotto
#: questa soglia il modello non e' una staffa, e' un errore di battitura che
#: passa il gate. Il rifiuto lo dice.
PARETE_MINIMA_MM = 2.0

#: I valori predefiniti, in millimetri. Sono i parametri di un pezzo vero, non
#: numeri tondi: gli smussi sono quattro e diversi, come §11.10 regola 4 chiede.
DEFAULT: dict[str, float] = {
    "larghezza": 120.0,
    "altezza": 80.0,
    "profondita": 12.0,
    "smusso_bl": 6.0,
    "smusso_br": 14.0,
    "smusso_tr": 6.0,
    "smusso_tl": 10.0,
    "foro_larghezza": 40.0,
    "foro_altezza": 30.0,
    "smusso_foro": 4.0,
}

#: I conteggi, chiusi. Il verificatore di ADR-012 li usa come ATTESO e non
#: interroga il generatore per saperli.
VERTICI = 32
TRIANGOLI = 64


def _anello(w: float, h: float, c: tuple[float, float, float, float]) -> np.ndarray:
    """Gli otto punti di un rettangolo `w x h` centrato, con gli angoli tagliati.

    In senso antiorario visto da +Z, a partire dal lato basso. `c` sono gli
    smussi in ordine basso-sinistra, basso-destra, alto-destra, alto-sinistra.
    """
    x, y = w / 2.0, h / 2.0
    bl, br, tr, tl = c
    return np.array([
        (-x + bl, -y), (x - br, -y),          # lato basso
        (x, -y + br), (x, y - tr),            # lato destro
        (x - tr, y), (-x + tl, y),            # lato alto
        (-x, y - tl), (-x, -y + bl),          # lato sinistro
    ], dtype=np.float64)


def _valida(p: dict[str, float]) -> None:
    w, h, d = p["larghezza"], p["altezza"], p["profondita"]
    for nome in ("larghezza", "altezza", "profondita", "foro_larghezza", "foro_altezza"):
        if p[nome] <= 0:
            raise ModelloNonValido(f"{nome} deve essere positiva, non {p[nome]}")
    smussi = (p["smusso_bl"], p["smusso_br"], p["smusso_tr"], p["smusso_tl"])
    for nome in ("smusso_bl", "smusso_br", "smusso_tr", "smusso_tl", "smusso_foro"):
        if p[nome] < 0:
            raise ModelloNonValido(f"{nome} non puo' essere negativo")
    if len(set(smussi)) == 1:
        # §11.10 regola 4. Un pezzo simmetrico non e' vietato dalla geometria:
        # e' vietato dal disegno, e dirlo qui e' meglio che lasciarlo passare.
        raise ModelloNonValido(
            "i quattro smussi sono tutti uguali: §11.10 regola 4 chiede "
            "un'asimmetria PROGETTATA, non un rettangolo con gli angoli tagliati")
    bl, br, tr, tl = smussi
    for a, b, lato, quale in ((bl, br, w, "basso"), (tr, tl, w, "alto"),
                              (br, tr, h, "destro"), (tl, bl, h, "sinistro")):
        if a + b >= lato:
            raise ModelloNonValido(
                f"gli smussi del lato {quale} sommano {a + b} mm su {lato} mm: "
                "il lato sparirebbe")
    fw, fh, fc = p["foro_larghezza"], p["foro_altezza"], p["smusso_foro"]
    if 2 * fc >= min(fw, fh):
        raise ModelloNonValido(
            f"lo smusso del foro ({fc} mm) si mangia il foro {fw}x{fh} mm")
    parete = min((w - fw) / 2.0, (h - fh) / 2.0)
    if parete < PARETE_MINIMA_MM:
        raise ModelloNonValido(
            f"fra il foro {fw}x{fh} e il bordo {w}x{h} restano {parete:.1f} mm "
            f"di parete, sotto il minimo di {PARETE_MINIMA_MM} mm")
    if d <= 0:
        raise ModelloNonValido(f"profondita non positiva: {d}")


def estrusione_45(**parametri: float) -> Modello:
    """Un solido: sagoma rettangolare con quattro smussi a 45 gradi e foro
    passante, estrusa lungo Z. Millimetri.

    Non solleva verso l'LLM: chi la chiama e' `core/tools/model3d.py`, che
    traduce `ModelloNonValido` in `ToolResult(ok=False, error=...)`.
    """
    p = {**DEFAULT, **{k: float(v) for k, v in parametri.items() if v is not None}}
    if ignoti := set(p) - set(DEFAULT):
        raise ModelloNonValido(f"parametri sconosciuti: {sorted(ignoti)}")
    _valida(p)

    smussi = (p["smusso_bl"], p["smusso_br"], p["smusso_tr"], p["smusso_tl"])
    fc = p["smusso_foro"]
    fuori = _anello(p["larghezza"], p["altezza"], smussi)
    dentro = _anello(p["foro_larghezza"], p["foro_altezza"], (fc, fc, fc, fc))
    z = p["profondita"] / 2.0

    # 0-7 fuori/davanti · 8-15 dentro/davanti · 16-23 fuori/dietro · 24-31 dentro/dietro
    davanti = np.hstack([np.vstack([fuori, dentro]), np.full((16, 1), z)])
    dietro = np.hstack([np.vstack([fuori, dentro]), np.full((16, 1), -z)])
    posizioni = np.vstack([davanti, dietro]).astype(np.float32)

    F_FUORI, F_DENTRO, D_FUORI, D_DENTRO = 0, 8, 16, 24
    tri: list[tuple[int, int, int]] = []
    for i in range(8):
        j = (i + 1) % 8
        of, oj = F_FUORI + i, F_FUORI + j          # fuori, davanti
        if_, ij = F_DENTRO + i, F_DENTRO + j       # dentro, davanti
        pf, pj = D_FUORI + i, D_FUORI + j          # fuori, dietro
        qf, qj = D_DENTRO + i, D_DENTRO + j        # dentro, dietro
        # La faccia davanti e' una corona, non un disco: il foro passa.
        tri += [(of, oj, ij), (of, ij, if_)]                 # davanti, +Z
        tri += [(pf, qj, pj), (pf, qf, qj)]                  # dietro, -Z
        tri += [(of, pf, pj), (of, pj, oj)]                  # parete esterna
        tri += [(if_, qj, qf), (if_, ij, qj)]                # parete del foro
    triangoli = np.array(tri, dtype=np.uint32)

    # §11.10 regola 3 — le linee di costruzione sono gli spigoli VERI del
    # pezzo, non le diagonali della triangolazione: e' cio' che si disegna
    # sopra la faccia con `Line2` (regola 6, due materiali). I due profili
    # davanti e dietro, piu' le otto generatrici.
    linee: list[tuple[int, int]] = []
    for base in (F_FUORI, F_DENTRO, D_FUORI, D_DENTRO):
        linee += [(base + i, base + (i + 1) % 8) for i in range(8)]
    linee += [(F_FUORI + i, D_FUORI + i) for i in range(8)]
    linee += [(F_DENTRO + i, D_DENTRO + i) for i in range(8)]

    return Modello(
        nome=NOME, versione=VERSIONE, params=p,
        posizioni=posizioni, triangoli=triangoli,
        # ⚠️ ANALITICO: gli smussi tagliano verso l'interno e non spostano gli
        # estremi. Ricavarlo da `posizioni.max()` sarebbe misurare il codice
        # con se' stesso — vedi `parametrico.Modello`.
        bbox=(p["larghezza"], p["altezza"], p["profondita"]),
        linee=np.array(linee, dtype=np.uint32),
    )
