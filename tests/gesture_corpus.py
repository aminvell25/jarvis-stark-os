"""EVAL — il corpus dei gesti (§14, §22).

Stessa idea di `tests/t0_corpus.py`: un riconoscitore va misurato su casi
scritti, non provato a mano davanti alla webcam. Una prova dal vivo dice se
funziona **adesso, con la mia mano, con questa luce**; il corpus dice se
funziona ancora dopo la prossima modifica.

Il rischio che sorveglia non e' «il gesto non viene riconosciuto» — quello si
nota subito. E' il contrario: che un gesto venga riconosciuto **quando non c'e'**,
perche' §14 lo dice in una riga — «un falso positivo e' indistinguibile da un
comando». Per questo meta' dei casi sono sequenze che NON devono emettere
nulla.

I landmark sono sintetici e costruiti qui: MediaPipe restituisce ventuno terne
normalizzate, e ventuno terne normalizzate si possono scrivere. Cosi' il corpus
gira in millisecondi, senza telecamera e senza modello.
"""

from __future__ import annotations

from core.gestures.tracker import Fotogramma, Mano

# I 21 landmark di MediaPipe, nell'ordine ufficiale:
#   0 polso · 1-4 pollice · 5-8 indice · 9-12 medio · 13-16 anulare · 17-20 mignolo
_COLONNE = {5: -0.24, 9: -0.08, 13: 0.08, 17: 0.24}   # scarto orizzontale delle nocche


def mano(cx: float = 0.5, cy: float = 0.7, scala: float = 0.25, *,
         dita: float = 1.0, pollice_su_indice: bool = False,
         lato: str = "Right") -> Mano:
    """Una mano sintetica ma plausibile.

    `dita` e' quanto sono estese: 1,0 aperta, 0,35 chiusa. `pollice_su_indice`
    porta la punta del pollice su quella dell'indice — il pizzico.
    """
    punti: list[tuple[float, float, float]] = [(cx, cy, 0.0)]

    # Pollice: 1-4, che si allontana LATERALMENTE.
    #
    # La prima versione lo teneva a ridosso della colonna dell'indice, e la
    # punta finiva a un decimo di mano dalla punta dell'indice: ogni mano
    # risultava in pizzico, compreso un pugno. In una mano vera il pollice
    # aperto sta a piu' di mezza mano dall'indice, ed e' quella distanza a
    # rendere il pizzico un gesto e non uno stato di riposo.
    for q in (0.30, 0.55, 0.78, 1.0):
        punti.append((cx - 0.72 * scala * q, cy - 0.20 * scala * q, 0.0))

    # Le quattro dita: nocca, due falangi e la punta.
    #
    # `dita = 0,5` mette la punta ALLA nocca; sopra si estende, sotto si
    # arriccia verso il palmo — che e' cio' che fa una mano vera, e che la
    # prima versione sbagliava: teneva la punta sempre oltre la nocca, quindi
    # anche un pugno risultava «palmo aperto». L'ha trovato il corpus.
    for dx in _COLONNE.values():
        punta = 0.38 + 1.12 * (dita - 0.5)
        for q in (0.38, 0.38 + (punta - 0.38) * 0.45, 0.38 + (punta - 0.38) * 0.75, punta):
            punti.append((cx + dx * scala, cy - scala * q, 0.0))

    if pollice_su_indice:
        indice = punti[8]
        punti[4] = (indice[0] + 0.01, indice[1] + 0.01, 0.0)

    return Mano(lato=lato, punti=tuple(punti), fiducia=0.95)


def fotogramma(*mani: Mano, indice: int = 0) -> Fotogramma:
    return Fotogramma(mani=list(mani), ts=0.0, ms_inferenza=1.0, indice=indice)


def sequenza(costruisci, quanti: int) -> list[Fotogramma]:
    """`costruisci(i)` -> tupla di mani, per `quanti` fotogrammi."""
    return [fotogramma(*costruisci(i), indice=i) for i in range(quanti)]


# ── le sequenze etichettate ──────────────────────────────────────────────────

def palmo_aperto_fermo(n: int = 10):
    return sequenza(lambda i: (mano(dita=1.0),), n)


def pizzico_fermo(n: int = 10):
    return sequenza(lambda i: (mano(dita=0.9, pollice_su_indice=True),), n)


def spinta_laterale(n: int = 8):
    """Il polso attraversa: da 0,25 a 0,75 in otto fotogrammi, mano chiusa."""
    return sequenza(lambda i: (mano(cx=0.25 + 0.5 * i / (n - 1), dita=0.45),), n)


def rotazione_due_mani(n: int = 14):
    """Due polsi la cui congiungente ruota di ~40 gradi.

    Quattordici fotogrammi e non otto: la rotazione va RICONOSCIUTA per almeno
    cinque fotogrammi, e il riconoscimento parte solo quando la finestra ha
    accumulato abbastanza angolo. Otto fotogrammi ne davano tre, e l'isteresi
    — giustamente — non emetteva. Mezzo secondo per una rotazione a due mani e'
    il tempo che ci vuole davvero.
    """
    import math

    def costruisci(i):
        a = math.radians(-20 + 40 * i / (n - 1))
        return (
            mano(cx=0.5 - 0.18 * math.cos(a), cy=0.6 - 0.18 * math.sin(a),
                 dita=0.5, lato="Left"),
            mano(cx=0.5 + 0.18 * math.cos(a), cy=0.6 + 0.18 * math.sin(a),
                 dita=0.5, lato="Right"),
        )

    return sequenza(costruisci, n)


# ── e le sequenze che NON devono emettere niente ─────────────────────────────

def nessuna_mano(n: int = 10):
    return sequenza(lambda i: (), n)


def pizzico_troppo_breve(n: int = 4):
    """Quattro fotogrammi: uno meno dell'isteresi. Non deve contare."""
    return pizzico_fermo(n)


def tremolio(n: int = 12):
    """Pizzico e palmo alternati: una mano incerta, non un comando."""
    return sequenza(
        lambda i: (mano(dita=1.0) if i % 2 else mano(dita=0.9, pollice_su_indice=True),), n
    )


def mano_ferma_a_mezz_aria(n: int = 12):
    """Mano rilassata, punte all'altezza delle nocche: nessuno dei quattro."""
    return sequenza(lambda i: (mano(dita=0.5),), n)


def deriva_verticale(n: int = 8):
    """Il polso sale invece di attraversare: NON e' una spinta laterale."""
    return sequenza(lambda i: (mano(cy=0.85 - 0.5 * i / (n - 1), dita=0.45),), n)


#: (nome, sequenza, gesto atteso o None)
CORPUS = [
    ("palmo aperto fermo", palmo_aperto_fermo(), "espandi_pannello"),
    ("pizzico fermo", pizzico_fermo(), "sposta_pannello"),
    ("spinta laterale", spinta_laterale(), "cambia_workspace"),
    ("rotazione a due mani", rotazione_due_mani(), "ruota_mesh"),
    ("nessuna mano", nessuna_mano(), None),
    ("pizzico troppo breve", pizzico_troppo_breve(), None),
    ("tremolio fra due gesti", tremolio(), None),
    ("mano ferma a mezz'aria", mano_ferma_a_mezz_aria(), None),
    ("deriva verticale", deriva_verticale(), None),
]
