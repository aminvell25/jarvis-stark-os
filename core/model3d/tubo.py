"""Generatore ② di §17.4 — tubo su spline Catmull-Rom chiusa.

§17.4 ② prescriveva `THREE.CatmullRomCurve3`, e ADR-014 l'ha tolta insieme al
posto in cui girava: §11.10 regola 5 vieta le geometrie standard, e la
matematica resta — cambia chi la esegue. Qui la curva e' scritta per esteso,
nella forma **centripeta** (alfa 0,5) di Barry e Goldman.

## Perche' centripeta, e che cosa NON compra qui

Catmull-Rom uniforme, su punti di controllo a distanze molto diverse, produce
cuspidi e cappi: la curva esce dal guscio e torna indietro. La
parametrizzazione centripeta e' l'unica delle tre a garantire che non succeda,
e costa una radice quadrata per punto.

⚠️ **Su QUESTO guscio non compra quasi niente, ed e' misurato.** I punti di
controllo sono equispaziati in angolo su una formula liscia, quindi le corde
si somigliano e le tre parametrizzazioni quasi coincidono: lo scarto massimo
dalla poligonale dei punti e' **2,72 mm centripeta contro 2,92 uniforme e 3,16
cordale**. Su un guscio piu' duro — ondulazione 70 su raggio 90 — la
centripeta e' perfino **peggio** (10,16 contro 9,45), perche' la patologia da
cui protegge non e' questa.

Resta perche' e' la scelta giusta il giorno in cui i punti di controllo non
verranno piu' da una formula: la garanzia costa una radice quadrata e serve a
chi passera' parametri estremi. La prima stesura di questo commento diceva
«la garanzia serve davvero», e misurarla ha detto di no.

## La sezione e' un poligono, e il bbox lo dichiara

Un tubo di raggio `r` reso con `lati` lati e' un prisma inscritto nel
cilindro: i suoi vertici toccano il raggio, i suoi lati stanno dentro. A
seconda di dove cade la fase del poligono rispetto a un asse, l'ingombro su
quell'asse sta fra `r*cos(pi/lati)` e `r`. Il bbox dichiarato prende il
**limite superiore** — la curva piu' il raggio pieno — e la differenza e' una
tolleranza **con una forma chiusa**, non un margine di comodo:

    tolleranza = 2 * raggio_tubo * (1 - cos(pi / lati))

E' la stessa deroga che `ui/src/three/math/pointcloud.js` dichiara al gate del
renderer, per la stessa ragione: un campione discreto di una superficie
continua non tocca i propri estremi.
"""

from __future__ import annotations

import math

import numpy as np

from core.model3d.parametrico import (
    CORDA_MM,
    Modello,
    ModelloNonValido,
    segmenti_per,
)

NOME = "tubo-spline"
VERSIONE = "v1"

#: Quanti anelli e quante generatrici entrano nelle linee di costruzione.
#: **Una selezione, non il reticolo intero**: 256 anelli per 42 lati sono
#: ventunmila segmenti, e un tubo disegnato con tutte le sue isoparametriche
#: e' una macchia. In un disegno tecnico se ne tracciano alcune, ed e' quello
#: che dicono della forma — dove gira e quanto e' grossa.
ANELLI_DISEGNATI = 12
GENERATRICI_DISEGNATE = 6

#: I valori predefiniti, in millimetri. Due armoniche di ampiezza diversa: e'
#: cosi' che il guscio diventa asimmetrico per DISEGNO e non per caso
#: (§11.10 regola 4), ed e' la stessa regola dei quattro smussi
#: dell'estrusione.
DEFAULT: dict[str, float] = {
    "raggio_guida": 90.0,
    "ondulazione": 18.0,
    "torsione": 22.0,
    "torsione_2": 9.0,
    "lobi": 3.0,
    "punti_guida": 24.0,
    "raggio_tubo": 8.0,
    # ⚠️ **Non 1,2 mm, e la ragione e' misurata.** Con la corda predefinita di
    # §11.10 questo pezzo esce a 10.752 vertici e il messaggio `model3d.preview`
    # supera il mezzo megabyte — per un anello di 216 mm visto in un pannello
    # da 600 px, dove un segmento vale meno di un pixel. A 3,0 mm sono 3.024
    # vertici e la silhouette e' identica a schermo. La corda resta un
    # PARAMETRO: chi vuole la finezza di §11.10 la chiede, e il tetto dei
    # 20.000 vertici lo ferma prima che diventi un problema.
    "corda_mm": 3.0,
}


def _guscio(p: dict[str, float]) -> np.ndarray:
    """I punti di controllo, da una formula: nessun vertice scritto a mano.

    Due armoniche sullo stesso numero di lobi, con ampiezze diverse sul piano
    e in altezza. La seconda — `torsione_2`, a frequenza doppia — e' cio' che
    rompe la simmetria fra i lobi che salgono e quelli che scendono.
    """
    n = int(p["punti_guida"])
    m = p["lobi"]
    theta = np.linspace(0.0, 2.0 * math.pi, n, endpoint=False)
    r = p["raggio_guida"] + p["ondulazione"] * np.cos(m * theta)
    z = p["torsione"] * np.sin(m * theta) + p["torsione_2"] * np.sin(2.0 * m * theta)
    return np.stack([r * np.cos(theta), r * np.sin(theta), z], axis=1)


def _catmull_rom_chiusa(punti: np.ndarray, per_tratto: int,
                        alfa: float = 0.5) -> np.ndarray:
    """La curva chiusa che passa **esattamente** per i punti di controllo.

    Forma di Barry-Goldman: tre interpolazioni lineari annidate su nodi
    spaziati come `|P(i+1) - P(i)|^alfa`. Con `alfa = 0,5` e' la centripeta.

    Ritorna `len(punti) * per_tratto` campioni, senza ripetere gli estremi: il
    campione successivo all'ultimo e' di nuovo il primo, ed e' cio' che rende
    la sequenza un anello invece di una polilinea aperta.
    """
    n = len(punti)
    fuori = np.empty((n * per_tratto, 3), dtype=np.float64)
    for i in range(n):
        P = [punti[(i + k - 1) % n] for k in range(4)]      # P0..P3
        t = [0.0]
        for k in range(3):
            d = float(np.linalg.norm(P[k + 1] - P[k]))
            if d <= 0.0:
                raise ModelloNonValido(
                    "due punti di controllo coincidono: la curva centripeta "
                    "non e' definita")
            t.append(t[-1] + d ** alfa)
        # Il tratto vive fra t1 e t2 — fra P1 e P2 — e i due estremi servono
        # solo a dargli la tangente giusta.
        u = np.linspace(t[1], t[2], per_tratto, endpoint=False)[:, None]
        A1 = (t[1] - u) / (t[1] - t[0]) * P[0] + (u - t[0]) / (t[1] - t[0]) * P[1]
        A2 = (t[2] - u) / (t[2] - t[1]) * P[1] + (u - t[1]) / (t[2] - t[1]) * P[2]
        A3 = (t[3] - u) / (t[3] - t[2]) * P[2] + (u - t[2]) / (t[3] - t[2]) * P[3]
        B1 = (t[2] - u) / (t[2] - t[0]) * A1 + (u - t[0]) / (t[2] - t[0]) * A2
        B2 = (t[3] - u) / (t[3] - t[1]) * A2 + (u - t[1]) / (t[3] - t[1]) * A3
        fuori[i * per_tratto:(i + 1) * per_tratto] = (
            (t[2] - u) / (t[2] - t[1]) * B1 + (u - t[1]) / (t[2] - t[1]) * B2)
    return fuori


def _telaio(centri: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangente, normale e binormale lungo l'anello, **senza torsione propria**.

    ⚠️ Non si usa la normale di Frenet: dove la curva e' localmente dritta la
    curvatura va a zero e la normale salta di novanta gradi, e il tubo si
    attorciglia in un punto solo. Si trasporta invece una normale iniziale
    lungo la curva ruotandola con la tangente — il telaio a torsione minima —
    e alla fine si **chiude**.

    La chiusura e' il pezzo che si dimentica: dopo un giro il telaio torna
    ruotato di un angolo residuo, e se non lo si distribuisce il tubo ha una
    cucitura dove l'ultimo anello incontra il primo. Qui l'angolo si misura e
    si toglie in parti uguali su tutti gli anelli.
    """
    n = len(centri)
    # Tangenti per differenze centrali sull'anello: e' chiuso, quindi non ci
    # sono estremi da trattare a parte.
    t = np.roll(centri, -1, axis=0) - np.roll(centri, 1, axis=0)
    lung = np.linalg.norm(t, axis=1, keepdims=True)
    if not np.all(lung > 0):
        raise ModelloNonValido("due campioni consecutivi coincidono")
    t /= lung

    # Una normale iniziale qualunque, purche' non parallela alla tangente.
    seme = np.array([0.0, 0.0, 1.0])
    if abs(float(t[0] @ seme)) > 0.9:
        seme = np.array([1.0, 0.0, 0.0])
    nrm = np.empty_like(t)
    nrm[0] = seme - (seme @ t[0]) * t[0]
    nrm[0] /= np.linalg.norm(nrm[0])

    for i in range(1, n):
        # Rodrigues: la rotazione minima che porta t[i-1] su t[i].
        asse = np.cross(t[i - 1], t[i])
        sin_a = float(np.linalg.norm(asse))
        cos_a = float(np.clip(t[i - 1] @ t[i], -1.0, 1.0))
        if sin_a < 1e-12:
            nrm[i] = nrm[i - 1]
            continue
        asse = asse / sin_a
        v = nrm[i - 1]
        nrm[i] = (v * cos_a + np.cross(asse, v) * sin_a
                  + asse * (asse @ v) * (1.0 - cos_a))
        nrm[i] -= (nrm[i] @ t[i]) * t[i]
        nrm[i] /= np.linalg.norm(nrm[i])

    # La chiusura: si trasporta ancora una volta da t[n-1] a t[0] e si guarda
    # di quanto la normale manca il punto di partenza.
    asse = np.cross(t[-1], t[0])
    sin_a = float(np.linalg.norm(asse))
    cos_a = float(np.clip(t[-1] @ t[0], -1.0, 1.0))
    v = nrm[-1]
    if sin_a > 1e-12:
        a = asse / sin_a
        v = v * cos_a + np.cross(a, v) * sin_a + a * (a @ v) * (1.0 - cos_a)
    v -= (v @ t[0]) * t[0]
    v /= np.linalg.norm(v)
    b0 = np.cross(t[0], nrm[0])
    residuo = math.atan2(float(v @ b0), float(v @ nrm[0]))

    # ...e si distribuisce all'indietro, in parti uguali.
    passo = np.linspace(0.0, residuo, n, endpoint=False)
    bin_ = np.cross(t, nrm)
    c, s = np.cos(passo)[:, None], np.sin(passo)[:, None]
    nrm_r = nrm * c - bin_ * s
    bin_r = np.cross(t, nrm_r)
    return t, nrm_r, bin_r


def _valida(p: dict[str, float]) -> None:
    for nome in ("raggio_guida", "raggio_tubo", "corda_mm"):
        if p[nome] <= 0:
            raise ModelloNonValido(f"{nome} deve essere positivo, non {p[nome]}")
    for nome in ("ondulazione", "torsione", "torsione_2"):
        if p[nome] < 0:
            raise ModelloNonValido(f"{nome} non puo' essere negativa")
    n = p["punti_guida"]
    if n != int(n) or int(n) < 6:
        raise ModelloNonValido(
            f"punti_guida deve essere un intero >= 6, non {n}: sotto, la curva "
            "non ha abbastanza appoggi per chiudersi senza spigoli")
    m = p["lobi"]
    if m != int(m) or int(m) < 1:
        raise ModelloNonValido(f"lobi deve essere un intero >= 1, non {m}")
    if int(n) % int(m) != 0:
        raise ModelloNonValido(
            f"{int(n)} punti di controllo non si dividono in {int(m)} lobi: i "
            "campioni cadrebbero in punti diversi di ogni lobo e il guscio "
            "sarebbe irregolare per ARROTONDAMENTO, non per disegno")
    if p["ondulazione"] >= p["raggio_guida"]:
        raise ModelloNonValido(
            f"l'ondulazione ({p['ondulazione']} mm) mangia il raggio della "
            f"guida ({p['raggio_guida']} mm): la curva passerebbe per il centro")
    if p["ondulazione"] == p["torsione"] == p["torsione_2"]:
        # §11.10 regola 4, come i quattro smussi dell'estrusione.
        raise ModelloNonValido(
            "le tre ampiezze sono uguali: §11.10 regola 4 chiede "
            "un'asimmetria PROGETTATA, non un anello ondulato a caso")
    # Il tubo non deve mangiarsi la propria curva: il raggio di curvatura piu'
    # stretto del guscio e' quello del rientro fra due lobi.
    stretto = p["raggio_guida"] - p["ondulazione"]
    if p["raggio_tubo"] >= stretto:
        raise ModelloNonValido(
            f"il tubo (raggio {p['raggio_tubo']} mm) e' piu' grosso del rientro "
            f"della guida ({stretto} mm): si attraverserebbe")


def tubo_spline(**parametri: float) -> Modello:
    """Un anello: sezione poligonale spazzata lungo una spline chiusa.
    Millimetri.

    Non solleva verso l'LLM: `core/tools/model3d.py` traduce `ModelloNonValido`
    in `ToolResult(ok=False, error=...)`.
    """
    p = {**DEFAULT, **{k: float(v) for k, v in parametri.items() if v is not None}}
    if ignoti := set(p) - set(DEFAULT):
        raise ModelloNonValido(f"parametri sconosciuti: {sorted(ignoti)}")
    _valida(p)

    guscio = _guscio(p)
    sezioni, per_tratto = sezioni_di(p)
    centri = _catmull_rom_chiusa(guscio, per_tratto)
    assert len(centri) == sezioni

    lati = lati_di(p)
    t, nrm, bin_ = _telaio(centri)

    phi = np.linspace(0.0, 2.0 * math.pi, lati, endpoint=False)
    # (sezioni, lati, 3): ogni anello e' il centro piu' il poligono nel suo
    # piano normale.
    anelli = (centri[:, None, :]
              + p["raggio_tubo"] * (np.cos(phi)[None, :, None] * nrm[:, None, :]
                                    + np.sin(phi)[None, :, None] * bin_[:, None, :]))
    posizioni = anelli.reshape(-1, 3).astype(np.float32)

    def idx(i: int, j: int) -> int:
        return (i % sezioni) * lati + (j % lati)

    tri = np.empty((sezioni * lati * 2, 3), dtype=np.uint32)
    k = 0
    for i in range(sezioni):
        for j in range(lati):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            # L'ordine e' quello che manda le normali FUORI: il telaio e'
            # destrorso (t, n, b), e (a, b, d) darebbe l'interno.
            tri[k] = (a, d, c); tri[k + 1] = (a, c, b); k += 2

    linee = _linee(sezioni, lati, idx)

    # Il bbox: la curva piu' il raggio PIENO, che e' il cilindro circoscritto.
    lo = centri.min(axis=0) - p["raggio_tubo"]
    hi = centri.max(axis=0) + p["raggio_tubo"]
    ingombro = tuple(float(v) for v in (hi - lo))
    # E la tolleranza, in forma chiusa: il poligono inscritto tocca il raggio
    # solo dove un suo vertice cade sull'asse.
    tolleranza = 2.0 * p["raggio_tubo"] * (1.0 - math.cos(math.pi / lati))

    return Modello(
        nome=NOME, versione=VERSIONE, params=p,
        posizioni=posizioni, triangoli=tri, bbox=ingombro, linee=linee,
        tolleranza_mm=tolleranza,
        motivo_tolleranza=(
            f"la sezione e' un poligono di {lati} lati inscritto nel cerchio di "
            f"raggio {p['raggio_tubo']:g} mm: tocca il raggio pieno solo dove un "
            f"vertice cade sull'asse, e altrove sta dentro di "
            f"{tolleranza / 2:.3f} mm per lato"),
    )


def sezioni_di(p: dict[str, float]) -> tuple[int, int]:
    """Quanti anelli, e quanti campioni per tratto — dagli ARGOMENTI.

    ⚠️ Sta fuori da `tubo_spline` perche' il verificatore di ADR-012 ha bisogno
    del conteggio atteso **senza costruire la mesh**: un atteso che venga dal
    codice verificato non e' un atteso.

    §17.4 ② dice «segmenti da `segmentsFor()` sulla LUNGHEZZA della curva»,
    non sul raggio: si passa quindi il raggio del cerchio che ha la stessa
    lunghezza. La lunghezza si stima sul guscio, che e' una polilinea inscritta
    e quindi un po' piu' corta della curva — di meno dell'uno per cento con
    ventiquattro punti, e comunque dalla parte giusta: qualche segmento in
    piu', mai in meno.

    Il conteggio si arrotonda in su a un multiplo dei tratti, o l'ultimo tratto
    avrebbe una densita' diversa dagli altri.
    """
    guscio = _guscio(p)
    lung = float(np.linalg.norm(np.diff(guscio, axis=0, append=guscio[:1]),
                                axis=1).sum())
    chiesti = segmenti_per(lung / (2.0 * math.pi), 2.0 * math.pi, p["corda_mm"])
    n = int(p["punti_guida"])
    per_tratto = max(1, math.ceil(chiesti / n))
    return n * per_tratto, per_tratto


def lati_di(p: dict[str, float]) -> int:
    """I lati della sezione, dalla stessa regola: e' un cerchio di raggio
    `raggio_tubo`, e la densita' viene dalla sua curvatura."""
    return segmenti_per(p["raggio_tubo"], 2.0 * math.pi, p["corda_mm"])


def conteggi_di(p: dict[str, float]) -> tuple[int, int]:
    """(vertici, triangoli) attesi, **senza costruire niente**. E' l'atteso del
    verificatore, e la ragione per cui `sezioni_di` e `lati_di` sono pubbliche."""
    sezioni, _ = sezioni_di(p)
    lati = lati_di(p)
    return sezioni * lati, sezioni * lati * 2


def _linee(sezioni: int, lati: int, idx) -> np.ndarray:
    """§11.10 regola 3 — alcune isoparametriche, non il reticolo intero.

    Un tubo disegnato con tutti i suoi spigoli e' una macchia: qui alcuni
    anelli dicono dove gira, e alcune generatrici quanto e' grosso e come si
    avvolge. E' come si disegna un tubo su carta.
    """
    fuori: list[tuple[int, int]] = []
    passo_a = max(1, sezioni // ANELLI_DISEGNATI)
    for i in range(0, sezioni, passo_a):
        fuori += [(idx(i, j), idx(i, j + 1)) for j in range(lati)]
    passo_g = max(1, lati // GENERATRICI_DISEGNATE)
    for j in range(0, lati, passo_g):
        fuori += [(idx(i, j), idx(i + 1, j)) for i in range(sezioni)]
    return np.array(fuori, dtype=np.uint32)
