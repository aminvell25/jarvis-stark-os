"""Blocchi di dimensione ESATTA, da un flusso che non li garantisce.

## Perche' questo file esiste — misurato, non supposto

`core/platform/linux_audio.py` cattura con `pw-record` e legge cosi':

    blocco = await proc.stdout.read(BLOCCO)

`asyncio.StreamReader.read(n)` restituisce **fino a** `n` byte, non `n`. Su
questa macchina, quaranta letture da 640 byte contro il microfono vero:

    640 byte  19 volte        42 byte  13 volte
     44 byte   6 volte        24 byte   1 volta        626 byte  1 volta

**Ventuno blocchi su quaranta erano corti**, e un blocco da 42 byte e' **1,3 ms
di audio**. Chi li riceve non se ne accorge e non puo' accorgersene:

* `VAD.parla()` calcola l'energia media del blocco. Su 1,3 ms l'energia e' un
  numero senza significato — una consonante occlusiva ci sta dentro intera e la
  vocale che segue no. Il gate si apre e si chiude a caso.
* `PhraseWake.feed()` passa i byte a Vosk. Un blocco di lunghezza **dispari**
  spezza un campione a meta' fra due chiamate.
* E la latenza del wake, misurata per blocco, diventa incomparabile: 0,022 ms
  su 42 byte e 0,022 ms su 640 non sono la stessa misura.

Nessuno di questi guasti e' rumoroso. Sono tutti della specie che questo
progetto ha imparato a temere: **un numero plausibile che non significa niente**.

## Perche' sta in `core/voice/` e non in `core/platform/`

Perche' non e' una domanda sulla piattaforma. `pw-record` su Linux, WASAPI su
Windows e un file su disco hanno tutti e tre lo stesso comportamento — un flusso
di byte senza promesse sulla granularita' — e la risposta e' la stessa per tutti
e tre. L'invariante 29 chiede che la CHIAMATA specifica di piattaforma stia
dietro `core/platform/`, e ci sta: qui non si apre nessun dispositivo, si
riallinea un `AsyncIterator[bytes]` che qualcun altro ha aperto.

Il che vuol dire anche che la catena vocale si puo' provare **senza un
microfono**, che e' il motivo per cui `da_pcm()` esiste.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

import structlog

log = structlog.get_logger(__name__)

#: 20 ms e' il blocco su cui si ragiona in tutta la catena: `pipeline.py` conta
#: il silenzio in blocchi, e Vosk lavora bene con 10-30 ms. Non e' il blocco di
#: LETTURA — quello lo sceglie la piattaforma e vale 32 ms — ed e' proprio per
#: questo che serve un riallineamento: i due numeri non coincidono, e non c'e'
#: ragione perche' coincidano.
DURATA_BLOCCO_MS = 20

#: s16: due byte per campione. Vive qui e non in `linux_audio.py` perche' e'
#: l'aritmetica del riallineamento, non una scelta del dispositivo.
LARGHEZZA_CAMPIONE = 2


def byte_per_blocco(rate: int, ms: int = DURATA_BLOCCO_MS, canali: int = 1) -> int:
    """Quanti byte fanno `ms` millisecondi di audio.

    In un posto solo: il conto `rate * ms / 1000 * canali * 2` scritto due volte
    e' due opinioni su quanto dura un blocco, ed e' la specie di difetto che
    questo repo ha gia' pagato tre volte in due giorni.
    """
    if rate <= 0 or ms <= 0 or canali <= 0:
        raise ValueError(f"rate={rate} ms={ms} canali={canali}: nessuno puo' essere <= 0")
    campioni = rate * ms // 1000
    if campioni <= 0:
        raise ValueError(f"{ms} ms a {rate} Hz fanno zero campioni")
    return campioni * canali * LARGHEZZA_CAMPIONE


async def a_blocchi(
    sorgente: AsyncIterator[bytes],
    byte: int,
    *,
    riempi_la_coda: bool = True,
) -> AsyncIterator[bytes]:
    """Riallinea un flusso qualunque in blocchi di **esattamente** `byte`.

    ⚠️ **La coda si riempie di silenzio, non si scarta.**

    Alla fine del flusso resta quasi sempre un avanzo piu' corto di un blocco.
    Scartarlo perderebbe fino a 20 ms, e 20 ms alla fine di «papà è a casa» sono
    l'ultima sillaba: il wake sentirebbe «papà è a ca». Riempirlo di zeri
    aggiunge silenzio — che e' un dato onesto, non un segnaposto: e' cio' che
    c'era davvero dopo l'ultimo campione, cioe' niente.

    Con `riempi_la_coda=False` l'avanzo si perde, e serve solo a chi misura la
    latenza per blocco e non vuole un blocco finto nella distribuzione.

    Da un microfono il flusso non finisce mai, quindi la coda non esiste: e' il
    caso del file a farla comparire, ed e' l'unico in cui la scelta si vede.
    """
    if byte <= 0:
        raise ValueError(f"byte={byte}: un blocco vuoto non e' un blocco")
    avanzo = bytearray()
    corti = 0
    letti = 0
    async for pezzo in sorgente:
        if not pezzo:
            continue
        letti += 1
        if len(pezzo) != byte:
            corti += 1
        avanzo += pezzo
        while len(avanzo) >= byte:
            yield bytes(avanzo[:byte])
            del avanzo[:byte]
    if avanzo:
        if riempi_la_coda:
            yield bytes(avanzo) + b"\x00" * (byte - len(avanzo))
        else:
            log.debug("coda_scartata", byte=len(avanzo))
    if corti:
        # Non e' un errore: e' la ragione per cui questa funzione esiste, e
        # vederlo nei log dice quanto il flusso e' irregolare su QUESTA
        # macchina invece che in generale.
        log.debug("blocchi_riallineati", letti=letti, non_della_misura=corti,
                  byte=byte)


# ⚠️ **Qui c'era `da_pcm`, ed e' andata in `tests/conftest.py`.**
#
# Sorgente da byte gia' in memoria, per provare la catena `VAD -> wake -> T0`
# senza un microfono. Unici chiamanti: cinque righe di `tests/test_audio_io.py`.
# E' una comodita' per le prove scritta nel codice applicativo — la stessa
# specie di `Lettura.noti`, tolta il 28 agosto e finita nello stesso posto: un
# pezzo che sembra congiunto e non lo e'.
#
# La ragione per cui esiste NON cambia e resta scritta in cima a questo file:
# §5 di `docs/acceptance/T0-E-IL-MICROFONO.md` e' ancora aperto, e finche' lo
# resta la catena si prova su audio registrato. Cambia solo dove abita.


async def dal_microfono(
    audio,
    rate: int,
    ms: int = DURATA_BLOCCO_MS,
    canali: int = 1,
) -> AsyncIterator[bytes]:
    """Il microfono della piattaforma, riallineato.

    `audio` e' un `core.platform.base.AudioIO` — di solito `platform.audio()`.
    Arriva per parametro e non per import: cosi' un test passa una sorgente
    finta senza toccare il dispositivo, ed e' la stessa forma con cui il
    supervisore riceve `parla` e `pubblica`.
    """
    byte = byte_per_blocco(rate, ms, canali)
    log.info("ingresso_audio", rate=rate, ms=ms, byte=byte)
    async for b in a_blocchi(audio.input_stream(rate), byte):
        yield b
