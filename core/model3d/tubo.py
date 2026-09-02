"""Generatore ② di §17.4 — un tubo piegato, come lo si programma su una piegatrice.

## ⚠️ Che cosa c'era prima, e perche' e' stato buttato

La prima stesura, il 3 settembre 2026, faceva cio' che §17.4 ② dice alla
lettera: una spline Catmull-Rom **chiusa** su un guscio generato da due
armoniche, spazzata in tubo. La matematica era giusta — passava per i punti di
controllo a 1,5e-14 mm, il telaio si chiudeva senza cucitura, la topologia era
un toro — e **l'oggetto non era un pezzo**: un anello ondulato, con misure
risultanti invece che di progetto (214,9 x 202,0 x 67,6 mm) e un'asimmetria che
si leggeva come un errore invece che come una scelta. §11.10 regola 4 chiede
un'asimmetria PROGETTATA, e quella era casuale con la firma di una formula.

Il proprietario l'ha respinto guardandolo, ed e' la stessa regola di §11.7:
una violazione si riscrive, non si rattoppa. Il pezzo sta al commit `cd5dbbd`.

## Che cos'e' adesso

Un tubo piegato: **corse dritte raccordate da pieghe a raggio costante**. E'
esattamente come si programma un tubo su una macchina — corsa, rotazione,
angolo — e le tre parole sono i parametri di questo generatore. Le misure sono
tonde perche' sono di progetto, e non risultano da niente.

E la matematica dei segmenti ci sta meglio di prima: `segmenti_per(raggio,
arco)` e' nata per un arco di cerchio, e qui gli arcHI sono cerchi veri. Nella
stesura precedente si passava «il raggio del cerchio che ha la stessa
lunghezza della curva», che era una perifrasi.

## Che cosa non fa piu'

Il telaio non ha piu' bisogno di **chiudersi**: il percorso e' aperto, e il
residuo di torsione dopo un giro non esiste perche' non c'e' un giro. Il codice
che lo distribuiva se n'e' andato col guscio chiuso, e con lui il suo test:
teneva una proprieta' che questo pezzo non ha.

Il tubo e' **pieno**, non cavo: quello che si vede e' la sua superficie
esterna, chiusa da due tappi piatti. Una parete interna vorrebbe un secondo
tubo e due corone agli estremi, e nessuno l'ha ancora chiesta.
"""

from __future__ import annotations

import math

import numpy as np

from core.model3d.parametrico import (CORDA_MM, Modello, ModelloNonValido,
                                      Quota, segmenti_per)

NOME = "tubo-piegato"
VERSIONE = "v1"

#: Quante pieghe ha il pezzo. Il numero e' **fisso e dichiarato**, non un
#: parametro: ogni piega porta con se' un angolo e una rotazione, e un conteggio
#: variabile vorrebbe dire liste attraverso il ponte — che `app/preload.js`
#: vieta, e che ADR-013 ha gia' risolto una volta con un elemento per volta.
#: Tre pieghe sono il minimo per uscire dal piano, ed e' il punto.
PIEGHE = 3

#: I valori predefiniti, in millimetri e gradi. **Misure di progetto**: sono i
#: numeri che si scrivono su un disegno, non quelli che escono da una formula.
#: Le corse e gli angoli sono diversi fra loro — §11.10 regola 4, asimmetria
#: progettata — e la validazione lo impone invece di sperarci.
#: Il raggio di piega, in diametri. **Una piega «2D»**, che e' come si ordina
#: un tubo: la matrice della piegatrice si sceglie in base al tubo, non e' un
#: numero fisso. Sotto 1,5 diametri il tubo si schiaccia, e la validazione lo
#: rifiuta; due e' il valore comune, e resta un PARAMETRO per chi ne vuole uno
#: piu' largo.
PIEGA_SU_DIAMETRO = 2.0

DEFAULT: dict[str, float] = {
    "diametro": 12.0,
    "raggio_piega": 24.0,
    # Le quattro corse dritte, fra un raccordo e il successivo.
    "corsa_1": 90.0,
    "corsa_2": 70.0,
    "corsa_3": 45.0,
    "corsa_4": 60.0,
    # I tre angoli di piega, in gradi.
    "angolo_1": 90.0,
    "angolo_2": 60.0,
    "angolo_3": 90.0,
    # La rotazione attorno all'asse del tubo PRIMA di ogni piega: e' cio' che
    # porta il pezzo fuori dal piano, ed e' il terzo numero della piegatrice.
    "rotazione_1": 0.0,
    "rotazione_2": 90.0,
    "rotazione_3": 45.0,
    "corda_mm": CORDA_MM,
}

#: Quante generatrici si disegnano lungo il tubo. Una selezione, non tutte: con
#: trentadue lati il reticolo intero e' una macchia, e in un disegno tecnico se
#: ne tracciano poche.
GENERATRICI_DISEGNATE = 4


def _rodrigues(v: np.ndarray, asse: np.ndarray, angolo: float) -> np.ndarray:
    """Ruota `v` attorno ad `asse` (unitario) di `angolo` radianti."""
    c, s = math.cos(angolo), math.sin(angolo)
    return v * c + np.cross(asse, v) * s + asse * float(asse @ v) * (1.0 - c)


def _corse(p: dict[str, float]) -> list[float]:
    return [p[f"corsa_{i}"] for i in range(1, PIEGHE + 2)]


def _pieghe(p: dict[str, float]) -> list[tuple[float, float]]:
    """(angolo, rotazione) di ogni piega, in radianti."""
    return [(math.radians(p[f"angolo_{i}"]), math.radians(p[f"rotazione_{i}"]))
            for i in range(1, PIEGHE + 1)]


def _percorso(p: dict[str, float]) -> tuple[np.ndarray, list[int]]:
    """La linea d'asse, e gli indici dei punti di TANGENZA.

    Il pezzo comincia nell'origine diretto lungo +X, con il riferimento in +Z.
    Ogni piega: si ruota il riferimento attorno all'asse del tubo — la
    rotazione della piegatrice — poi si curva verso quel riferimento di
    `angolo`, a raggio costante.

    I punti di tangenza tornano a parte perche' sono i posti in cui un disegno
    tecnico mette un anello: e' li' che il pezzo smette di essere dritto.
    """
    R = p["raggio_piega"]
    pos = np.zeros(3)
    dir_ = np.array([1.0, 0.0, 0.0])
    rif = np.array([0.0, 0.0, 1.0])

    punti = [pos.copy()]
    tangenze: list[int] = []
    corse = _corse(p)

    for i, (angolo, rotazione) in enumerate(_pieghe(p)):
        pos = pos + corse[i] * dir_
        punti.append(pos.copy())
        tangenze.append(len(punti) - 1)          # inizio della piega

        rif = _rodrigues(rif, dir_, rotazione)
        rif = rif - float(rif @ dir_) * dir_     # ortogonale, sempre
        rif /= np.linalg.norm(rif)

        asse = np.cross(dir_, rif)
        centro = pos + R * rif
        n = segmenti_per(R, angolo, p["corda_mm"])
        for t in np.linspace(0.0, angolo, n + 1)[1:]:
            punti.append(centro + _rodrigues(-R * rif, asse, float(t)))
        pos = punti[-1].copy()
        dir_ = _rodrigues(dir_, asse, angolo)
        dir_ /= np.linalg.norm(dir_)
        rif = _rodrigues(rif, asse, angolo)
        tangenze.append(len(punti) - 1)          # fine della piega

    pos = pos + corse[-1] * dir_
    punti.append(pos.copy())
    return np.array(punti), tangenze


def _telaio(centri: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangente, normale e binormale lungo un percorso APERTO.

    ⚠️ Non la normale di Frenet: sulle corse dritte la curvatura e' zero e la
    normale di Frenet non e' definita — salterebbe a ogni raccordo. Si
    trasporta invece una normale iniziale lungo la linea, ruotandola con la
    tangente: e' il telaio a torsione minima, e su un tubo e' l'unico che non
    faccia attorcigliare la sezione fra una piega e l'altra.

    ⚠️ **Niente chiusura**, e non e' una dimenticanza: il percorso e' aperto.
    Il residuo dopo un giro esisteva sul guscio chiuso della stesura
    precedente, e se n'e' andato con lui.
    """
    n = len(centri)
    t = np.empty_like(centri)
    t[1:-1] = centri[2:] - centri[:-2]
    t[0] = centri[1] - centri[0]
    t[-1] = centri[-1] - centri[-2]
    lung = np.linalg.norm(t, axis=1, keepdims=True)
    if not np.all(lung > 0):
        raise ModelloNonValido("due punti consecutivi della linea d'asse coincidono")
    t /= lung

    seme = np.array([0.0, 0.0, 1.0])
    if abs(float(t[0] @ seme)) > 0.9:
        seme = np.array([0.0, 1.0, 0.0])
    nrm = np.empty_like(t)
    nrm[0] = seme - float(seme @ t[0]) * t[0]
    nrm[0] /= np.linalg.norm(nrm[0])

    for i in range(1, n):
        asse = np.cross(t[i - 1], t[i])
        sin_a = float(np.linalg.norm(asse))
        cos_a = float(np.clip(t[i - 1] @ t[i], -1.0, 1.0))
        if sin_a < 1e-12:
            nrm[i] = nrm[i - 1]                  # tratto dritto: non ruota
        else:
            nrm[i] = _rodrigues(nrm[i - 1], asse / sin_a, math.atan2(sin_a, cos_a))
        nrm[i] -= float(nrm[i] @ t[i]) * t[i]
        nrm[i] /= np.linalg.norm(nrm[i])
    return t, nrm, np.cross(t, nrm)


def _valida(p: dict[str, float]) -> None:
    for nome in ("diametro", "raggio_piega", "corda_mm"):
        if p[nome] <= 0:
            raise ModelloNonValido(f"{nome} deve essere positivo, non {p[nome]}")
    corse = _corse(p)
    for i, c in enumerate(corse, 1):
        if c <= 0:
            raise ModelloNonValido(f"corsa_{i} deve essere positiva, non {c}")
    for i in range(1, PIEGHE + 1):
        a = p[f"angolo_{i}"]
        if not 0 < a < 180:
            raise ModelloNonValido(
                f"angolo_{i} vale {a}: una piega sta fra 0 e 180 gradi esclusi")
        r = p[f"rotazione_{i}"]
        if not -180 <= r <= 180:
            raise ModelloNonValido(f"rotazione_{i} vale {r}: sta fra -180 e 180")

    raggio = p["diametro"] / 2.0
    # Il raggio di piega si misura sull'ASSE: sotto un diametro e mezzo il tubo
    # si schiaccia sulla piegatrice vera, e qui diventa una superficie che si
    # attraversa. E' la regola di officina, non un'invenzione.
    if p["raggio_piega"] < 1.5 * p["diametro"]:
        raise ModelloNonValido(
            f"raggio di piega {p['raggio_piega']} mm su un tubo da "
            f"{p['diametro']} mm: sotto 1,5 diametri il tubo si schiaccia")

    # Le corse devono lasciar posto ai raccordi: ogni piega si mangia una
    # tangente per lato, e due pieghe vicine non possono sovrapporsi.
    for i, (angolo, _) in enumerate(_pieghe(p)):
        tang = p["raggio_piega"] * math.tan(angolo / 2.0)
        for c, quale in ((corse[i], i + 1), (corse[i + 1], i + 2)):
            if c <= tang:
                raise ModelloNonValido(
                    f"corsa_{quale} e' {c} mm e la piega {i + 1} ne consuma "
                    f"{tang:.1f}: il tratto dritto sparirebbe")

    if len(set(corse)) == 1 and len({p[f'angolo_{i}'] for i in range(1, PIEGHE + 1)}) == 1:
        raise ModelloNonValido(
            "corse e angoli tutti uguali: §11.10 regola 4 chiede un'asimmetria "
            "PROGETTATA, non una spirale regolare")


def tubo_piegato(**parametri: float) -> Modello:
    """Un tubo: corse dritte, pieghe a raggio costante, due tappi. Millimetri.

    Non solleva verso l'LLM: `core/tools/model3d.py` traduce `ModelloNonValido`
    in `ToolResult(ok=False, error=...)`.
    """
    chiesti = {k: float(v) for k, v in parametri.items() if v is not None}
    if ignoti := set(chiesti) - set(DEFAULT):
        raise ModelloNonValido(f"parametri sconosciuti: {sorted(ignoti)}")
    p = {**DEFAULT, **chiesti}
    # ⚠️ **Il raggio di piega SEGUE il diametro**, se nessuno lo chiede.
    # Trovato provando la frase vera: «fammi un tubo da 20 millimetri» falliva
    # con «sotto 1,5 diametri il tubo si schiaccia», perche' il diametro
    # cambiava e il raggio restava quello del tubo predefinito. Su una
    # piegatrice la matrice si sceglie per il tubo, e chiedere un diametro
    # senza dire la piega vuol dire «la piega normale per questo tubo».
    if "diametro" in chiesti and "raggio_piega" not in chiesti:
        p["raggio_piega"] = p["diametro"] * PIEGA_SU_DIAMETRO
    _valida(p)

    centri, tangenze = _percorso(p)
    t, nrm, bin_ = _telaio(centri)
    raggio = p["diametro"] / 2.0
    lati = lati_di(p)
    sezioni = len(centri)

    phi = np.linspace(0.0, 2.0 * math.pi, lati, endpoint=False)
    anelli = (centri[:, None, :]
              + raggio * (np.cos(phi)[None, :, None] * nrm[:, None, :]
                          + np.sin(phi)[None, :, None] * bin_[:, None, :]))
    # I due tappi sono piatti: il loro centro e' l'estremo della linea d'asse.
    posizioni = np.vstack([anelli.reshape(-1, 3), centri[0], centri[-1]]).astype(np.float32)
    tappo_a, tappo_b = sezioni * lati, sezioni * lati + 1

    def idx(i: int, j: int) -> int:
        return i * lati + (j % lati)

    tri: list[tuple[int, int, int]] = []
    for i in range(sezioni - 1):
        for j in range(lati):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            # L'ordine manda le normali FUORI: il telaio e' destrorso (t, n, b).
            tri += [(a, d, c), (a, c, b)]
    for j in range(lati):
        # Tappo di partenza: la normale guarda indietro, quindi il verso e'
        # l'opposto di quello di arrivo.
        tri.append((tappo_a, idx(0, j + 1), idx(0, j)))
        tri.append((tappo_b, idx(sezioni - 1, j), idx(sezioni - 1, j + 1)))

    # ⚠️ **L'ingombro non e' «la linea d'asse piu' il raggio»**, e la prima
    # stesura lo diceva: il presidio di §11.10 regola 7 l'ha preso subito, con
    # 7,8 mm di scarto su X.
    #
    # Il disco della sezione sta nel piano PERPENDICOLARE alla tangente:
    # dove il tubo corre lungo un asse, su quell'asse il disco non sporge
    # affatto. La forma esatta esce dall'ortonormalita' del telaio — il punto
    # a `c + r(cos(phi) n + sin(phi) b)` ha estensione massima
    # `r*sqrt(n_k^2 + b_k^2)` sull'asse k, e `n_k^2 + b_k^2 = 1 - t_k^2`.
    #
    # Si calcola dalla sola TANGENTE, senza toccare ne' il telaio ne' i
    # vertici emessi: e' quindi una seconda affermazione indipendente, ed e'
    # cio' che rende §11.10 regola 7 un controllo invece di un'eco.
    sporgenza = raggio * np.sqrt(np.clip(1.0 - t * t, 0.0, None))
    lo = (centri - sporgenza).min(axis=0)
    hi = (centri + sporgenza).max(axis=0)
    tolleranza = 2.0 * raggio * (1.0 - math.cos(math.pi / lati))

    return Modello(
        nome=NOME, versione=VERSIONE, params=p,
        posizioni=posizioni, triangoli=np.array(tri, dtype=np.uint32),
        bbox=tuple(float(v) for v in (hi - lo)),
        linee=_linee(sezioni, lati, tangenze, idx),
        # ⚠️ Le quote di un tubo sono il DIAMETRO e il RAGGIO DI PIEGA, non i
        # tre lati dell'ingombro: quelli sono un risultato, e i loro angoli
        # stanno nel vuoto. Sono i due numeri che si ordinano, e sono tondi.
        # Il terzo e' la lunghezza sviluppata, cioe' quanto tubo serve —
        # l'unica misura d'insieme che conti su un pezzo cosi'.
        quote=(
            Quota(f"\u00d8{p['diametro']:g}", tuple(float(v) for v in centri[0])),
            Quota(f"R{p['raggio_piega']:g}",
                  tuple(float(v) for v in centri[(tangenze[0] + tangenze[1]) // 2])),
            Quota(f"sviluppo {_sviluppo(centri):.0f} mm",
                  tuple(float(v) for v in centri[-1])),
        ),
        tolleranza_mm=tolleranza,
        motivo_tolleranza=(
            f"la sezione e' un poligono di {lati} lati inscritto nel cerchio di "
            f"raggio {raggio:g} mm: tocca il raggio pieno solo dove un vertice "
            f"cade sull'asse, e altrove sta dentro di {tolleranza / 2:.3f} mm"),
    )


def _sviluppo(centri: np.ndarray) -> float:
    """Quanto tubo serve: la lunghezza della linea d'asse, dritti piu' pieghe.

    E' il numero che si ordina dal fornitore, e l'unica misura d'insieme che
    conti su un pezzo piegato — l'ingombro e' un risultato, questo no.
    """
    return float(np.linalg.norm(np.diff(centri, axis=0), axis=1).sum())


def _linee(sezioni: int, lati: int, tangenze: list[int], idx) -> np.ndarray:
    """§11.10 regola 3 — gli anelli dove il pezzo CAMBIA, e poche generatrici.

    Gli anelli non cadono a intervalli regolari: cadono ai **punti di
    tangenza**, cioe' dove una corsa dritta finisce e comincia un raccordo.
    Sono le uniche circonferenze che un disegno tecnico traccia, perche' sono
    le uniche che dicono qualcosa — dove il tubo si piega.
    """
    fuori: list[tuple[int, int]] = []
    for i in sorted({0, sezioni - 1, *tangenze}):
        fuori += [(idx(i, j), idx(i, j + 1)) for j in range(lati)]
    passo = max(1, lati // GENERATRICI_DISEGNATE)
    for j in range(0, lati, passo):
        fuori += [(idx(i, j), idx(i + 1, j)) for i in range(sezioni - 1)]
    return np.array(fuori, dtype=np.uint32)


def lati_di(p: dict[str, float]) -> int:
    """I lati della sezione, dalla curvatura del cerchio che la genera."""
    return segmenti_per(p["diametro"] / 2.0, 2.0 * math.pi, p["corda_mm"])


def sezioni_di(p: dict[str, float]) -> int:
    """Quanti anelli, **dagli argomenti e senza costruire niente**.

    Uno all'inizio, uno alla fine di ogni corsa dritta, e `segmenti_per` per
    ciascun raccordo — che qui e' un arco di cerchio vero, cioe' esattamente
    la cosa per cui quella formula e' nata.
    """
    n = 1 + len(_corse(p))                       # partenza + fine di ogni corsa
    for angolo, _ in _pieghe(p):
        n += segmenti_per(p["raggio_piega"], angolo, p["corda_mm"])
    return n


def conteggi_di(p: dict[str, float]) -> tuple[int, int]:
    """(vertici, triangoli) attesi. E' l'atteso del verificatore di ADR-012, e
    la ragione per cui `sezioni_di` e `lati_di` sono pubbliche."""
    s, l = sezioni_di(p), lati_di(p)
    return s * l + 2, (s - 1) * l * 2 + 2 * l
