"""Lo spettro a bande dell'audio vero — §11.5 Fase 3, §10.6 classe 2.

## Perche' sta nel core e non nel renderer

`ui/src/hud/onda.js` disegna un'onda alimentata da un array di ampiezze.
Quell'array poteva nascere in due posti, e la scelta non e' di gusto:

* **nel renderer**, con la Web Audio API su `getUserMedia`. Tre righe, e
  sbagliato: aprirebbe un SECONDO dispositivo audio accanto a quello che il
  core ha gia' aperto in `audio_io.dal_microfono()`. Due lettori sullo stesso
  microfono sono due fonti di verita' sull'audio — CLAUDE.md lo vieta senza un
  ADR — e l'invariante 1 dice che le operazioni reali le possiede il core;
* **qui**, sul PCM che sta gia' passando. Sul filo viaggiano trentadue numeri
  ogni cinquanta millisecondi, e il dispositivo resta uno.

## Che cosa misura, esattamente

Il modulo dei coefficienti di Fourier del blocco, raggruppati in bande
logaritmiche e portati in scala di decibel. Ogni passaggio e' una
TRASFORMAZIONE DICHIARATA di un segnale vero, non un abbellimento:

1. **finestra di Hann** — un blocco tagliato di netto ha due discontinuita'
   agli estremi, e la trasformata di una discontinuita' e' energia sparsa su
   tutte le frequenze. Senza finestra le bande alte leggerebbero il taglio
   invece del suono;
2. **raggruppamento logaritmico** — l'orecchio sente in ottave e la voce vive
   fra 80 Hz e 8 kHz. Bande lineari darebbero ventotto barre sopra i 4 kHz,
   dove in una voce non c'e' quasi niente, e quattro sotto i 500, dove c'e'
   tutto;
3. **scala in decibel** — l'ampiezza lineare di un parlato normale sta a
   qualche millesimo del fondo scala, e in lineare l'onda resterebbe piatta.
   `PAVIMENTO_DB` dichiara dove comincia il silenzio.

⚠️ **Nessun inviluppo e nessuna forma imposta.** Il riferimento ha un'onda che
si assottiglia ai bordi, e la si otterrebbe moltiplicando le bande per una
finestra: l'aspetto tornerebbe e ogni barra smetterebbe di essere una misura.
La simmetria la fa il disegno disponendo le bande dal centro verso i bordi
(`ui/src/hud/onda.js`), senza toccare un solo valore.

## Il costo, che e' il vincolo vero

Sta sul percorso caldo della voce, e `pipeline.py` e' pieno di cicatrici
lasciate da cose messe li' senza misurarle. `PIANO-FUI-ESITO.md` e' esplicito:
«una FFT a bande **solo se una sonda mostra che serve**, non perche' il
riferimento ha sedici barre».

La sonda e' `tests/test_spettro.py`, e il numero misurato sta in
`docs/acceptance/NUCLEO-AURORA.md`. Due difese, se dovesse pesare troppo:
`PASSO_SPETTRO` in `pipeline.py` calcola un blocco su tre, e `CAMPIONI` si puo'
dimezzare — la risoluzione in frequenza cala, il costo pure.
"""

from __future__ import annotations

import array
import cmath
import math

#: Quanti punti entrano nella trasformata. Potenza di due perche' l'algoritmo
#: e' radix-2, e 256 perche' a 16 kHz sono 16 ms — dentro il blocco da 20 ms di
#: `audio_io.DURATA_BLOCCO_MS`, quindi non serve accumulare fra un blocco e
#: l'altro. Un blocco piu' lungo darebbe piu' risoluzione in frequenza e meno
#: nel tempo: per un'onda che deve seguire una voce, il tempo conta di piu'.
CAMPIONI = 256

#: Quante bande escono. Trentadue perche' e' quante ne disegna
#: `ui/src/hud/onda.js`, e i due numeri devono restare d'accordo: un test lo
#: verifica leggendo tutti e due i file.
BANDE = 32

#: L'intervallo coperto. Non e' 0-Nyquist: sotto gli 80 Hz c'e' il ronzio di
#: rete e il rimbombo della stanza, sopra gli 8 kHz una voce non ha quasi
#: energia. Ventotto barre su niente non sono densita', sono rumore.
HZ_MIN = 80.0
HZ_MAX = 8000.0

#: Dove comincia il silenzio, in decibel sotto il fondo scala.
PAVIMENTO_DB = -60.0

#: Il fondo scala di un campione s16.
FONDO_SCALA = 32768.0

#: La finestra di Hann, calcolata UNA volta. Ricalcolarla a ogni blocco
#: sarebbe 256 coseni cinquanta volte al secondo per un vettore che non cambia
#: mai — il genere di spreco che non si vede in un profilo perche' e' diffuso.
_HANN: tuple[float, ...] = tuple(
    0.5 - 0.5 * math.cos(2.0 * math.pi * i / (CAMPIONI - 1)) for i in range(CAMPIONI)
)

#: I fattori di rotazione, anche loro una volta sola: sono meta' del costo di
#: una FFT scritta in Python. `cmath.exp` dentro il ciclo interno costerebbe
#: piu' della trasformata.
_ROTAZIONI: tuple[complex, ...] = tuple(
    cmath.exp(-2j * math.pi * k / CAMPIONI) for k in range(CAMPIONI // 2)
)


def _ordine_bit_rovesciati(n: int) -> tuple[int, ...]:
    """La permutazione della radix-2. Non dipende dai dati: solo da `n`."""
    bit = n.bit_length() - 1
    fuori = []
    for i in range(n):
        r = 0
        for b in range(bit):
            if i & (1 << b):
                r |= 1 << (bit - 1 - b)
        fuori.append(r)
    return tuple(fuori)


_ORDINE: tuple[int, ...] = _ordine_bit_rovesciati(CAMPIONI)


def fft(campioni: list[complex]) -> list[complex]:
    """Cooley-Tukey radix-2, iterativa, in loco.

    Scritta a mano e non presa da una libreria perche' `numpy` non e' fra le
    dipendenze di `pyproject.toml` e CLAUDE.md dice di non aggiungerne senza
    chiedere. Sono venti righe per un vettore di lunghezza costante nota: il
    prezzo di una dipendenza in piu' sarebbe piu' alto del prezzo di queste.

    ⚠️ Vuole ESATTAMENTE `CAMPIONI` valori: la permutazione e le rotazioni sono
    precalcolate per quella lunghezza. Una lunghezza diversa darebbe un
    risultato sbagliato invece di un errore, ed e' il genere di difetto che non
    si vede mai — quindi qui solleva.
    """
    n = len(campioni)
    if n != CAMPIONI:
        raise ValueError(f"fft() vuole {CAMPIONI} campioni, non {n}")

    a = [campioni[i] for i in _ORDINE]
    passo = 2
    while passo <= n:
        mezzo = passo // 2
        salto = n // passo
        for inizio in range(0, n, passo):
            k = 0
            for j in range(inizio, inizio + mezzo):
                t = _ROTAZIONI[k] * a[j + mezzo]
                u = a[j]
                a[j] = u + t
                a[j + mezzo] = u - t
                k += salto
        passo *= 2
    return a


def _bordi_bande(rate: int) -> list[tuple[int, int]]:
    """Gli indici di bin che compongono ogni banda, spaziati in logaritmo.

    Una banda vuota — succede alle frequenze basse, dove due bordi logaritmici
    cadono dentro lo stesso bin — prende comunque un bin: una banda senza bin
    resterebbe a zero per sempre, e il disegno avrebbe una barra morta che
    sembra un guasto.
    """
    nyquist = rate / 2.0
    passo_hz = nyquist / (CAMPIONI // 2)
    alto = min(HZ_MAX, nyquist)
    if alto <= HZ_MIN:
        raise ValueError(f"rate={rate}: Nyquist sotto {HZ_MIN} Hz, non c'e' banda")

    fuori: list[tuple[int, int]] = []
    rapporto = alto / HZ_MIN
    for b in range(BANDE):
        f0 = HZ_MIN * rapporto ** (b / BANDE)
        f1 = HZ_MIN * rapporto ** ((b + 1) / BANDE)
        i0 = max(1, int(f0 / passo_hz))
        i1 = max(i0 + 1, int(f1 / passo_hz))
        fuori.append((i0, min(i1, CAMPIONI // 2)))
    return fuori


#: I bordi dipendono solo dal rate, e il rate non cambia in una sessione.
_CACHE_BORDI: dict[int, list[tuple[int, int]]] = {}


def bande(pcm: bytes, rate: int) -> list[float]:
    """Le `BANDE` ampiezze, ognuna fra 0 e 1, dal PCM s16 mono di un blocco.

    Torna una lista di zeri se il blocco e' troppo corto o muto: uno stato
    vuoto e' un risultato valido, e chi chiama non deve distinguere «non c'e'
    audio» da «c'e' stato un errore» guardando un `None`.
    """
    if not pcm:
        return [0.0] * BANDE

    c = array.array("h")
    c.frombytes(pcm[: len(pcm) // 2 * 2])
    if len(c) < CAMPIONI:
        return [0.0] * BANDE

    # Gli ULTIMI campioni del blocco, non i primi: se un blocco ne porta piu'
    # del necessario, la parte piu' recente e' quella che l'occhio si aspetta.
    coda = c[len(c) - CAMPIONI:]

    # La media si toglie come la toglie `VAD.energia`, e per la stessa ragione
    # misurata: la polarizzazione continua del convertitore vale -8470 su 32768
    # su questa macchina, e senza toglierla il bin 0 e le sue perdite laterali
    # dominerebbero ogni banda bassa.
    media = sum(coda) / CAMPIONI

    spettro = fft([complex((coda[i] - media) * _HANN[i], 0.0) for i in range(CAMPIONI)])

    # La finestra di Hann ha guadagno coerente 0,5, e la trasformata di N punti
    # scala con N/2 su un tono reale: il prodotto e' il divisore che porta un
    # tono a fondo scala a modulo 1.
    scala = FONDO_SCALA * CAMPIONI * 0.25

    bordi = _CACHE_BORDI.get(rate)
    if bordi is None:
        bordi = _bordi_bande(rate)
        _CACHE_BORDI[rate] = bordi

    fuori: list[float] = []
    for i0, i1 in bordi:
        # Il MASSIMO del gruppo, non la media: una banda larga un'ottava che
        # media dieci bin annacqua un picco netto fino a farlo sparire, e un
        # picco netto e' esattamente cio' che una voce produce.
        picco = 0.0
        for k in range(i0, i1):
            m = abs(spettro[k])
            if m > picco:
                picco = m
        v = picco / scala
        if v <= 0.0:
            fuori.append(0.0)
            continue
        db = 20.0 * math.log10(v)
        fuori.append(0.0 if db <= PAVIMENTO_DB
                     else min(1.0, (db - PAVIMENTO_DB) / -PAVIMENTO_DB))
    return fuori
