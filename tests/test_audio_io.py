"""I blocchi hanno la dimensione che dicono di avere.

## Il difetto che questi test sorvegliano, misurato sul microfono vero

`core/platform/linux_audio.py` legge con `proc.stdout.read(BLOCCO)`, e
`asyncio.StreamReader.read(n)` restituisce **fino a** `n` byte. Quaranta letture
da 640 byte contro il microfono di questa macchina:

    640 byte  19 volte        42 byte  13 volte
     44 byte   6 volte        24 byte   1 volta        626 byte  1 volta

Ventuno su quaranta erano corti. Un blocco da 42 byte e' **1,3 ms di audio**: il
VAD ci calcola sopra un'energia media che non significa niente, e il gate si
apre e si chiude a caso.

Il guasto e' silenzioso — nessuno solleva, nessun log si accende — ed e' della
specie che questo progetto ha imparato a temere: **un numero plausibile che non
significa niente**.

`GRANULARITA_MISURATA` qui sotto e' quella distribuzione, non un caso inventato:
i test la riproducono invece di supporre un flusso ordinato.
"""

from __future__ import annotations

import pytest

from core.voice.audio_io import (
    DURATA_BLOCCO_MS,
    a_blocchi,
    byte_per_blocco,
    dal_microfono,
)

from tests.conftest import da_pcm

#: Le dimensioni vere restituite da `read(640)` sul microfono di questa
#: macchina, nell'ordine in cui sono arrivate.
GRANULARITA_MISURATA = [640, 42, 640, 44, 42, 640, 42, 626, 640, 24, 44, 640, 42]


async def _raccogli(it) -> list[bytes]:
    return [b async for b in it]


class TestAritmetica:
    def test_venti_millisecondi_a_16k_mono(self) -> None:
        """320 campioni da due byte. E' il numero che tutta la catena usa."""
        assert byte_per_blocco(16_000) == 640

    def test_il_conto_vive_in_un_posto_solo(self) -> None:
        assert byte_per_blocco(48_000, 20) == 1920
        assert byte_per_blocco(16_000, 30) == 960
        assert byte_per_blocco(16_000, 20, canali=2) == 1280

    @pytest.mark.parametrize("rate,ms,canali", [(0, 20, 1), (16_000, 0, 1),
                                                (16_000, 20, 0), (-1, 20, 1)])
    def test_rifiuta_l_impossibile(self, rate, ms, canali) -> None:
        """Un blocco da zero byte non e' un blocco, e un ciclo che lo aspetta
        non finisce mai."""
        with pytest.raises(ValueError):
            byte_per_blocco(rate, ms, canali)

    def test_rifiuta_una_durata_che_non_fa_nemmeno_un_campione(self) -> None:
        with pytest.raises(ValueError):
            byte_per_blocco(rate=100, ms=1)


class TestRiallineamento:
    async def test_la_granularita_VERA_diventa_regolare(self) -> None:
        """Il caso che conta: la distribuzione misurata sul microfono."""
        pezzi = [b"\x01\x02" * (n // 2) for n in GRANULARITA_MISURATA]
        blocchi = await _raccogli(da_pcm(pezzi, 640))
        assert blocchi, "nessun blocco da 4 700 byte di ingresso"
        assert all(len(b) == 640 for b in blocchi), \
            f"dimensioni: {sorted({len(b) for b in blocchi})}"

    async def test_NON_si_perde_un_campione(self) -> None:
        """Riallineare non e' filtrare: quello che entra deve uscire, e la
        coda si riempie di silenzio invece di sparire."""
        dati = bytes(range(256)) * 10          # 2560 byte, non multiplo di 640? lo e'
        dati = dati[:2000]                     # 2000 = 3 blocchi + 80 di coda
        blocchi = await _raccogli(da_pcm(dati, 640))
        assert len(blocchi) == 4
        insieme = b"".join(blocchi)
        assert insieme[:2000] == dati, "i byte sono cambiati"
        assert insieme[2000:] == b"\x00" * 560, "la coda non e' silenzio"

    async def test_la_coda_si_puo_scartare(self) -> None:
        """Chi misura la latenza per blocco non vuole un blocco meta' finto
        nella distribuzione."""
        async def sorgente():
            yield b"\x01" * 700
        blocchi = await _raccogli(a_blocchi(sorgente(), 640, riempi_la_coda=False))
        assert [len(b) for b in blocchi] == [640]

    async def test_un_flusso_gia_regolare_passa_intatto(self) -> None:
        """La meta' che conta di piu': non si deve rompere il caso buono."""
        pezzi = [bytes([i]) * 640 for i in range(5)]
        blocchi = await _raccogli(da_pcm(pezzi, 640))
        assert blocchi == pezzi

    async def test_un_pezzo_gigante_si_spezza(self) -> None:
        """`read(n)` puo' anche dare piu' del previsto se qualcuno cambia il
        blocco di lettura: 626 e' comparso nella misura vera."""
        blocchi = await _raccogli(da_pcm(b"\x07" * 6400, 640))
        assert len(blocchi) == 10 and all(len(b) == 640 for b in blocchi)

    async def test_i_pezzi_vuoti_non_producono_blocchi_vuoti(self) -> None:
        """`read()` torna `b""` a fine flusso, e un blocco vuoto passato a Vosk
        non e' un blocco: e' un no-op che sposta le statistiche."""
        async def sorgente():
            yield b""
            yield b"\x01" * 640
            yield b""
        blocchi = await _raccogli(a_blocchi(sorgente(), 640))
        assert [len(b) for b in blocchi] == [640]

    async def test_un_flusso_vuoto_non_produce_niente(self) -> None:
        async def sorgente():
            return
            yield b""                                        # pragma: no cover
        assert await _raccogli(a_blocchi(sorgente(), 640)) == []

    async def test_una_lunghezza_DISPARI_non_spezza_un_campione(self) -> None:
        """s16: due byte per campione. Un pezzo dispari, se passasse cosi'
        com'e', spezzerebbe un campione fra due chiamate a Vosk."""
        blocchi = await _raccogli(da_pcm([b"\x01" * 41, b"\x02" * 599], 640))
        assert [len(b) for b in blocchi] == [640]
        assert all(len(b) % 2 == 0 for b in blocchi)

    async def test_rifiuta_un_blocco_da_zero(self) -> None:
        async def sorgente():
            yield b"\x01"
        with pytest.raises(ValueError):
            await _raccogli(a_blocchi(sorgente(), 0))


class TestDalMicrofono:
    """`audio` arriva per parametro, non per import: cosi' si prova senza
    aprire un dispositivo — la stessa forma con cui il supervisore riceve
    `parla` e `pubblica`."""

    async def test_compone_la_piattaforma_col_riallineamento(self) -> None:
        visti = []

        class AudioFinto:
            def input_stream(self, sample_rate):
                visti.append(sample_rate)

                async def gen():
                    for n in GRANULARITA_MISURATA:
                        yield b"\x03" * n
                return gen()

        blocchi = await _raccogli(dal_microfono(AudioFinto(), 16_000))
        assert visti == [16_000], "il rate non arriva alla piattaforma"
        assert all(len(b) == byte_per_blocco(16_000) for b in blocchi)

    async def test_la_durata_predefinita_e_quella_della_catena(self) -> None:
        assert DURATA_BLOCCO_MS == 20
