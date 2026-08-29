"""Cambiare una frase di richiamo mentre JARVIS ascolta.

`PhraseWake.set_frasi()` esisteva dalla Fase 3 e la ricarica a caldo di
`settings.toml` non ci arrivava; adesso ci arriva, e
`LE-FRASI-PUNTANO-A-UNA-SCENA-CHE-ESISTE.md` §5.2 dichiarava perche' collegarla
non fosse una riga sola:

> `set_frasi` ricostruisce il `KaldiRecognizer` mentre `feed()` gira nel ciclo,
> e chiamarlo dal thread che sorveglia il file sarebbe una corsa su `self._rec`.

La corsa era chiusa **dal chiamante** — `engine.py` rimbalza sul loop con
`call_soon_threadsafe` — cioe' da una proprieta' di chi chiama, non di
`PhraseWake`. Basta che un domani il ciclo audio passi in un thread (Kaldi e'
CPU, e il budget e' 20 ms per blocco) perche' la garanzia sparisca **in
silenzio**: nessuna eccezione, nessun log, un riconoscitore sostituito a meta'
di un blocco.

Qui la garanzia si sposta dentro `PhraseWake`: la richiesta si **deposita**, e
`feed()` la applica al proprio inizio. Fra un blocco e l'altro, mai dentro, e
senza un lock che possa far aspettare il ciclo audio.

## Le misure che decidono il progetto

| | |
|---|---|
| `vosk.Model(...)` | **206,3 ms** — cio' che `set_frasi()` evita |
| `KaldiRecognizer` con grammatica | **0,08 ms** mediani, 0,31 il peggiore di dieci |
| `AcceptWaveform` su un blocco | **0,311 ms** |

Applicare il cambio dentro `feed()` costa **meno di un quarto di blocco**, in
un budget di 20 ms: e' il motivo per cui il posto giusto e' li' dentro e non in
un thread a parte.

⚠️ **E una misura che ha cambiato il codice**: `KaldiRecognizer(m, 16000, "[]")`
— grammatica vuota — **non solleva, termina il processo con SIGSEGV** (uscita
139, riprodotto in un sottoprocesso). Un `except` non lo prenderebbe. Non e'
raggiungibile, perche' la grammatica porta sempre `[unk]` in fondo, ed e' la
seconda ragione per cui quel `[unk]` c'e'. Sta scritto in `_crea_recognizer()`
perche' chi togliesse `[unk]` per «pulizia» spegnerebbe il core, non i log.

## Che cosa questi test NON provano

Il fallimento della ricostruzione e' **iniettato**. Provate contro il modello
vero, `jarvis\\n`, `jarvis!`, `3`, `€`, il byte nullo e una parola fuori
vocabolario danno tutte un riconoscitore valido: Kaldi ignora cio' che non
conosce e avvisa. L'unico rifiuto catchable trovato — `Exception: Failed to
create a recognizer` — vuole un elemento non-stringa nella grammatica, e li'
non ci arriva, perche' `set_frasi()` normalizza con `.lower()` e una chiave che
non e' una stringa solleva prima, sul thread di chi ha scritto il file.
Il guardiano resta necessario (un Vosk futuro, una memoria finita), ma la sua
prova e' costruita, e va detto.
"""

from __future__ import annotations

import json
import sys
import threading
import types

import pytest
from structlog.testing import capture_logs

from core.voice.wake import PhraseWake

#: 640 byte = 320 campioni a 16 kHz = 20 ms, il blocco di `audio_io`.
BLOCCO = b"\x01\x02" * 320


class _RecFinto:
    """Un `KaldiRecognizer` finto.

    Non imita Kaldi: imita cio' che `wake.py` gli chiede — la grammatica
    ricevuta alla costruzione, i blocchi, il finale. Serve a rispondere a una
    domanda che il riconoscitore vero non sa dire: **quale** oggetto ha
    ricevuto **quale** blocco.
    """

    def __init__(self, grammatica: str) -> None:
        self.frasi: list[str] = [f for f in json.loads(grammatica)
                                 if f != "[unk]"]
        self.blocchi: list[bytes] = []
        #: Cio' che dira' di aver sentito quando l'enunciato si chiude.
        self.sentito = ""

    def SetWords(self, quali: bool) -> None:
        self.parole = quali

    def AcceptWaveform(self, pcm: bytes) -> bool:
        self.blocchi.append(pcm)
        # `False` = come Kaldi a meta' di un enunciato. Il riconoscimento in
        # questi test passa da `chiudi()`, che e' anche la strada vera: vedi
        # `PhraseWake.chiudi()`.
        return False

    def Result(self) -> str:
        return json.dumps({"text": self.sentito})

    def FinalResult(self) -> str:
        return json.dumps({"text": self.sentito})


class _VoskFinto:
    """Il modulo `vosk`, ridotto a cio' che `PhraseWake` usa.

    `rifiuta`: le frasi che fanno fallire la costruzione, come farebbe una
    grammatica che Kaldi non accetta.
    """

    def __init__(self, rifiuta: tuple[str, ...] = ()) -> None:
        self.rifiuta = rifiuta
        self.creati: list[_RecFinto] = []
        self.modelli = 0

    # -- superficie del modulo ------------------------------------------
    def SetLogLevel(self, livello: int) -> None:
        self.livello = livello

    def Model(self, model_path: str | None = None, lang: str | None = None):
        self.modelli += 1
        return f"modello({model_path or lang})"

    def KaldiRecognizer(self, model, sample_rate: int, grammatica: str):
        frasi = json.loads(grammatica)
        if any(f in self.rifiuta for f in frasi):
            raise RuntimeError(f"grammatica rifiutata: {frasi}")
        rec = _RecFinto(grammatica)
        self.creati.append(rec)
        return rec

    def come_modulo(self) -> types.ModuleType:
        m = types.ModuleType("vosk")
        m.SetLogLevel = self.SetLogLevel
        m.Model = self.Model
        m.KaldiRecognizer = self.KaldiRecognizer
        return m


@pytest.fixture
def vosk_finto(monkeypatch):
    """Il finto al posto di `vosk` in `sys.modules`.

    `PhraseWake` fa `import vosk` dentro i metodi: la sostituzione qui arriva.
    Serve perche' il modello vero pesa 87 MiB e 206 ms, e queste prove
    riguardano **quando** il riconoscitore cambia, non che cosa sente.
    """
    def installa(rifiuta: tuple[str, ...] = ()) -> _VoskFinto:
        finto = _VoskFinto(rifiuta)
        monkeypatch.setitem(sys.modules, "vosk", finto.come_modulo())
        return finto

    return installa


def _wake(finto_installato, frasi=None, **kw) -> PhraseWake:
    return PhraseWake(frasi or {"jarvis": "listen"}, model_path="/finto", **kw)


class TestIlCambioAvvieneFraUnBloccoELAltro:
    """La richiesta si deposita; il ciclo audio la raccoglie quando puo'."""

    def test_set_frasi_NON_tocca_il_riconoscitore_vivo(self, vosk_finto) -> None:
        """Il difetto vero, quello che non solleva: `self._rec` sostituito da
        un altro thread mentre `feed()` lo sta usando."""
        finto = vosk_finto()
        wake = _wake(finto)
        prima = wake._rec

        wake.set_frasi({"jarvis buonasera": "scene:avvio"})

        assert wake._rec is prima, (
            "il riconoscitore e' stato sostituito dal chiamante: e' la corsa "
            "su `self._rec` che LE-FRASI-PUNTANO-A-UNA-SCENA dichiarava"
        )
        assert len(finto.creati) == 1, (
            "`set_frasi()` ha costruito una grammatica: il lavoro sta sul "
            "thread sbagliato, e il ciclo audio potrebbe doverlo aspettare"
        )
        assert wake.frasi_vive == {"jarvis": "listen"}

    def test_le_frasi_DICHIARATE_cambiano_subito(self, vosk_finto) -> None:
        """Chi ha appena tolto una frase dal file non deve vederla svegliare
        JARVIS un'altra volta, e chi legge `frasi` deve leggere cio' che ha
        chiesto — `engine.py` ci confronta il file per non riapplicarlo."""
        finto = vosk_finto()
        wake = _wake(finto)

        wake.set_frasi({"jarvis buonasera": "scene:avvio"})

        assert wake.frasi == {"jarvis buonasera": "scene:avvio"}

    def test_il_primo_blocco_APPLICA_il_cambio(self, vosk_finto) -> None:
        finto = vosk_finto()
        wake = _wake(finto)
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})

        wake.feed(BLOCCO)

        assert wake.frasi_vive == {"jarvis buonasera": "scene:avvio"}
        assert finto.creati[-1].frasi == ["jarvis buonasera"], (
            "il riconoscitore vivo ha ancora la grammatica di prima: la frase "
            "nuova non sveglierebbe nessuno"
        )
        assert wake._rec is finto.creati[-1]

    def test_il_riconoscimento_usa_le_frasi_NUOVE(self, vosk_finto) -> None:
        """Non basta che la grammatica cambi: l'azione che esce dal trigger
        dev'essere quella nuova."""
        finto = vosk_finto()
        visti: list[str] = []
        wake = _wake(finto, su_trigger=lambda t: visti.append(t.azione))
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})
        wake.feed(BLOCCO)
        finto.creati[-1].sentito = "jarvis buonasera"

        trigger = wake.chiudi()

        assert trigger is not None and trigger.frase == "jarvis buonasera"
        assert trigger.azione == "scene:avvio"
        assert visti == ["scene:avvio"]

    def test_NESSUN_blocco_si_perde_nel_cambio(self, vosk_finto) -> None:
        """Il cambio sta fra due blocchi, non al posto di uno: i sei blocchi
        dati in pasto arrivano tutti e sei a un riconoscitore."""
        finto = vosk_finto()
        wake = _wake(finto)
        blocchi = [bytes([i]) * 640 for i in range(6)]

        for b in blocchi[:3]:
            wake.feed(b)
        # Il confine fra i due enunciati: e' li' che il cambio entra.
        wake.chiudi()
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})
        for b in blocchi[3:]:
            wake.feed(b)

        ricevuti = [b for rec in finto.creati for b in rec.blocchi]
        assert ricevuti == blocchi, (
            "un blocco e' stato mangiato dal cambio: 20 ms di parlato spariti "
            "senza che niente sollevi"
        )
        assert finto.creati[0].blocchi == blocchi[:3]
        assert finto.creati[1].blocchi == blocchi[3:]

    def test_tre_cambi_di_seguito_costano_UN_riconoscitore(self, vosk_finto) -> None:
        """La casella e' una sola: vale l'ultima richiesta, che e' l'unica che
        descrive il file su disco. Il ciclo audio non paga i cambi intermedi."""
        finto = vosk_finto()
        wake = _wake(finto)

        wake.set_frasi({"uno due": "a"})
        wake.set_frasi({"tre quattro": "b"})
        wake.set_frasi({"cinque sei": "c"})
        wake.feed(BLOCCO)

        assert wake.frasi_vive == {"cinque sei": "c"}
        assert len(finto.creati) == 2, [r.frasi for r in finto.creati]

    def test_chiudi_NON_sostituisce_il_riconoscitore(self, vosk_finto) -> None:
        """Il finale deve uscire dal riconoscitore che ha ricevuto l'audio.
        Sostituirlo un istante prima butterebbe via l'enunciato appena detto —
        la frase pronunciata proprio mentre il file cambiava."""
        finto = vosk_finto()
        wake = _wake(finto)
        wake.feed(BLOCCO)
        finto.creati[-1].sentito = "jarvis"
        wake.set_frasi({"jarvis": "listen", "jarvis buonasera": "scene:avvio"})

        trigger = wake.chiudi()

        assert trigger is not None and trigger.frase == "jarvis", (
            "l'enunciato in corso e' stato buttato via dal cambio di frasi"
        )
        assert len(finto.creati) == 1
        assert wake._rec is finto.creati[0]

    def test_una_frase_TOLTA_dal_file_non_sveglia_piu(self, vosk_finto) -> None:
        """L'altra faccia, ed e' deliberata: `_riconosci()` guarda le frasi
        **dichiarate**, non quelle del riconoscitore che sta finendo
        l'enunciato. Chi ha appena cancellato una frase dal file non deve
        vederla svegliare JARVIS un'ultima volta perche' l'audio era gia'
        dentro Kaldi.

        Il prezzo e' dichiarato: la frase pronunciata **mentre** il file
        cambiava si perde. Vale solo per la frase cancellata — se sopravvive al
        cambio, l'enunciato in corso arriva lo stesso (test qui sopra), con
        l'azione **nuova**, perche' il file e' la verita'.
        """
        finto = vosk_finto()
        wake = _wake(finto)
        wake.feed(BLOCCO)
        finto.creati[-1].sentito = "jarvis"
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})

        assert wake.chiudi() is None

    def test_l_azione_NUOVA_vale_gia_per_l_enunciato_in_corso(
            self, vosk_finto) -> None:
        finto = vosk_finto()
        wake = _wake(finto, {"jarvis": "listen"})
        wake.feed(BLOCCO)
        finto.creati[-1].sentito = "jarvis"
        wake.set_frasi({"jarvis": "mute"})

        trigger = wake.chiudi()

        assert trigger is not None and trigger.azione == "mute"


class TestUnaFraseCheNonSiCostruisce:
    """Un `settings.toml` storto rende JARVIS ignaro della frase nuova, non
    sordo. Il fallimento e' iniettato: vedi l'intestazione del file."""

    def _wake_che_rifiutera(self, vosk_finto):
        finto = vosk_finto(rifiuta=("storta",))
        wake = _wake(finto, {"jarvis": "listen"})
        wake.feed(BLOCCO)                     # niente in attesa: nessun cambio
        # ⚠️ E si CHIUDE l'enunciato. Dal 27 agosto il cambio entra solo al
        # confine fra due enunciati, non fra due blocchi: senza questa riga il
        # `feed()` del test sarebbe il secondo blocco della stessa frase, e il
        # cambio resterebbe in attesa. Misurato col modello vero: applicandolo
        # a meta' enunciato la frase di richiamo spariva in 59 posizioni su 93.
        wake.chiudi()
        return finto, wake

    def test_resta_vivo_il_riconoscitore_di_PRIMA(self, vosk_finto) -> None:
        finto, wake = self._wake_che_rifiutera(vosk_finto)
        vivo = wake._rec

        wake.set_frasi({"storta": "scene:avvio"})
        wake.feed(BLOCCO)

        assert wake._rec is vivo, "il riconoscitore e' morto con la frase storta"
        assert wake.frasi_vive == {"jarvis": "listen"}

    def test_non_solleva_dentro_il_ciclo_audio_e_il_blocco_ARRIVA(
            self, vosk_finto) -> None:
        """Un'eccezione qui uscirebbe dall'`async for` di `pipeline.py` e la
        scrivania resterebbe sorda per il resto della sessione."""
        finto, wake = self._wake_che_rifiutera(vosk_finto)
        wake.set_frasi({"storta": "scene:avvio"})

        assert wake.feed(b"\x09" * 640) is None
        assert wake._rec.blocchi[-1] == b"\x09" * 640, (
            "il blocco e' stato perso nel fallimento: JARVIS ha smesso di "
            "ascoltare per 20 ms senza dirlo"
        )

    def test_le_frasi_dichiarate_TORNANO_INDIETRO(self, vosk_finto) -> None:
        """Due opinioni diverse su quali frasi siano vive fanno un trigger che
        non arriva senza un errore da leggere: `_riconosci()` cercherebbe in un
        elenco che Kaldi non puo' produrre."""
        finto, wake = self._wake_che_rifiutera(vosk_finto)

        wake.set_frasi({"storta": "scene:avvio"})
        assert wake.frasi == {"storta": "scene:avvio"}     # chiesto
        wake.feed(BLOCCO)

        assert wake.frasi == wake.frasi_vive == {"jarvis": "listen"}

    def test_lo_DICE(self, vosk_finto) -> None:
        finto, wake = self._wake_che_rifiutera(vosk_finto)
        wake.set_frasi({"storta": "scene:avvio"})

        with capture_logs() as righe:
            wake.feed(BLOCCO)

        detti = [r for r in righe if r["event"] == "wake_frasi_non_applicate"]
        assert len(detti) == 1, righe
        assert detti[0]["log_level"] == "error"
        assert detti[0]["chieste"] == ["storta"]
        assert detti[0]["restano"] == ["jarvis"]

    def test_il_cambio_DOPO_quello_fallito_si_applica(self, vosk_finto) -> None:
        """Un file corretto due volte non lascia il wake incastrato sul primo
        errore."""
        finto, wake = self._wake_che_rifiutera(vosk_finto)
        wake.set_frasi({"storta": "scene:avvio"})
        wake.feed(BLOCCO)
        wake.chiudi()

        wake.set_frasi({"jarvis buonasera": "scene:avvio"})
        wake.feed(BLOCCO)

        assert wake.frasi_vive == {"jarvis buonasera": "scene:avvio"}


class TestDalThreadDIVERSO:
    """`SettingsStore.reload()` gira sul thread di watchdog. Che la garanzia
    valga anche di la' e' il punto di tutto il resto."""

    #: Dove si smette di macinare. **Non e' un verdetto**: serve solo a non
    #: far crescere all'infinito la lista di blocchi del finto quando il
    #: watchdog resta indietro. Chi decide se c'e' un lock e' il `join()`.
    #: Sette volte il peggio misurato (27 311 giri, vedi il test).
    TETTO_GIRI = 200_000

    def test_duecento_cambi_da_un_altro_thread_mentre_il_ciclo_MACINA(
            self, vosk_finto) -> None:
        """Nessun blocco perso, nessun aggiornamento perso, e il ciclo torna.

        ⚠️ Un `x = self._pendenti; self._pendenti = None` al posto della
        `deque` supera questo test **quasi sempre**: la finestra e' di due
        bytecode. E' il motivo per cui l'ultima riga non guarda la corsa ma il
        suo esito — dopo l'ultimo `feed()` le frasi vive sono le ultime chieste
        — che e' vero o falso senza dipendere dal tempismo.

        ⚠️ **Il conteggio dei giri non dice se c'e' un lock, ed e' misurato.**
        Fino al 27 agosto qui c'era `if nutriti > 20_000: fail("c'e' un
        lock")`. Quel sentinella si e' rivelato cieco da tutt'e due gli occhi:

        | | giri (mediana / peggiore di 15) | durata |
        |---|---|---|
        | codice vero, nessun lock | 400 / **27 311** | 1,9 / **10,2 ms** |
        | con un `threading.Lock` vero in `feed()` e `set_frasi()` | 400 / 400 | 0,2 / 3,3 ms |

        Cioe': **falso allarme 1 volta su 8** senza alcun lock — il ciclo che
        macina affama il watchdog attraverso il GIL, e 27 311 giri sono 10 ms,
        non un'attesa — e **nessun allarme** quando il lock c'e' davvero,
        perche' su CPython chi aspetta un mutex conteso lo ottiene subito.
        Un contatore di giri non separa le due popolazioni: e' rumore.

        Percio' il verdetto si sposta dove e' deterministico. Qui restano le
        tre proprieta' che non dipendono dal tempismo — nessun blocco perso,
        nessun aggiornamento perso, il watchdog arriva in fondo appena il
        ciclo smette — e «nessun lock» ha due guardiani suoi, in
        `TestNessunLockSullaStradaDelCicloAudio`.
        """
        finto = vosk_finto()
        wake = _wake(finto)
        fatto = threading.Event()
        errore: list[BaseException] = []

        def watchdog() -> None:
            try:
                for i in range(200):
                    wake.set_frasi({f"frase numero {i}": "scene:avvio"})
            except BaseException as exc:       # pragma: no cover
                errore.append(exc)
            finally:
                fatto.set()

        t = threading.Thread(target=watchdog, name="watchdog-finto")
        t.start()
        nutriti = 0
        while not fatto.is_set() or nutriti < 400:
            wake.feed(BLOCCO)
            # Un enunciato per giro: e' il confine a cui il cambio entra, e
            # senza il ciclo macinerebbe per sempre senza applicarne nessuno.
            wake.chiudi()
            nutriti += 1
            if nutriti >= self.TETTO_GIRI:     # pragma: no cover
                break                          # non e' un verdetto: vedi sopra
        t.join(timeout=5)
        assert not t.is_alive(), (
            "il watchdog non e' arrivato in fondo nemmeno DOPO che il ciclo "
            "audio ha smesso di macinare: allora non era il GIL, e' "
            "`set_frasi()` che aspetta qualcuno"
        )
        assert not errore, errore

        wake.feed(BLOCCO)                      # l'ultimo deposito, se c'e'
        ricevuti = sum(len(r.blocchi) for r in finto.creati)
        assert ricevuti == nutriti + 1, (
            f"{nutriti + 1} blocchi dati, {ricevuti} arrivati: il cambio ne "
            "mangia qualcuno"
        )
        assert wake.frasi_vive == {"frase numero 199": "scene:avvio"}, (
            "l'ultimo deposito e' andato perso: il ciclo audio resta su una "
            "grammatica che il file non descrive piu'"
        )

    def test_la_casella_del_deposito_e_ATOMICA(self, vosk_finto) -> None:
        """⚠️ **Guardia sulla forma, e lo dichiara.**

        La proprieta' — un deposito che arriva **fra** la lettura e
        l'azzeramento non si perde — vive in una finestra di due bytecode.
        Provato: sostituendo la `deque` con `x = self._p; self._p = None`, il
        test qui sopra — duecento cambi da un altro thread mentre il ciclo
        macina — resta **VERDE**. Non e' osservabile dal di fuori con una prova
        deterministica, e allora si guarda cio' che la garantisce: `append` e
        `popleft` su una `deque` sono una sola chiamata C che non rilascia il
        GIL.

        `maxlen=1` e' l'altra meta', ed e' provata dal comportamento
        (`test_tre_cambi_di_seguito_costano_UN_riconoscitore`): sta qui perche'
        e' la stessa scelta.
        """
        from collections import deque

        finto = vosk_finto()
        wake = _wake(finto)

        assert isinstance(wake._pendenti, deque), (
            "il deposito non e' piu' atomico: un cambio che arriva mentre il "
            "ciclo lo raccoglie puo' sparire, e resterebbe una grammatica che "
            "il file non descrive piu' — senza un errore da leggere"
        )
        assert wake._pendenti.maxlen == 1


class TestNessunLockSullaStradaDelCicloAudio:
    """«E non c'e' un lock, di proposito» — `set_frasi()` lo dichiara, e il
    motivo e' il difetto del 26 e 27 agosto: il ciclo audio ha 20 ms per
    blocco, e farlo aspettare riempie la pipe di `pw-record`.

    Fino al 27 agosto quella frase era difesa da un contatore di giri dentro
    `test_duecento_cambi_...`, che **misurato** non separava un lock vero dal
    normale affamamento del GIL (la tabella e' nel docstring di quel test).
    Qui la stessa proprieta' ha due guardiani deterministici, e ciascuno dice
    che cosa NON copre:

    - la **sonda rientrante** coglie un `threading.Lock` — provato: si
      incastra — ma non un `RLock`, che dallo stesso thread rientra;
    - la **guardia sulla forma** coglie l'uno e l'altro, e qualunque attesa
      futura, ma guarda il sorgente, non il comportamento.

    Nessuno dei due e' sensibile al tempismo: non possono lampeggiare.
    """

    def test_set_frasi_chiamato_DA_DENTRO_feed_non_si_incastra(
            self, vosk_finto) -> None:
        """L'istante peggiore che il watchdog possa scegliere: il cambio
        arriva **mentre** il blocco e' dentro il riconoscitore.

        Se `feed()` e `set_frasi()` prendessero lo stesso lock, qui il ciclo
        audio si fermerebbe per sempre — ed e' esattamente la sordita' da cui
        viene tutto questo file. Il `feed()` gira in un thread suo con un
        `join()` a termine, cosi' un incastro diventa un rosso da leggere e
        non una suite appesa.
        """
        finto = vosk_finto()
        wake = _wake(finto)
        rec = wake._rec
        vero = rec.AcceptWaveform

        def rientra(pcm: bytes) -> bool:
            rec.AcceptWaveform = vero          # una volta sola: non ricorre
            wake.set_frasi({"da dentro il ciclo": "scene:avvio"})
            return vero(pcm)

        rec.AcceptWaveform = rientra
        tornato: list[str] = []
        t = threading.Thread(
            target=lambda: (wake.feed(BLOCCO), tornato.append("tornato")),
            name="ciclo-audio-finto", daemon=True)
        t.start()
        t.join(timeout=5)

        assert tornato == ["tornato"], (
            "`feed()` non e' tornato entro 5 s con un `set_frasi()` arrivato "
            "a meta' del blocco: c'e' un lock sulla strada del ciclo audio"
        )
        # E il deposito arrivato di la' non si e' perso: lo applica il blocco
        # dopo, come ogni altro.
        assert wake.frasi_vive == {"jarvis": "listen"}
        # Il confine: dal 27 agosto il cambio entra fra due ENUNCIATI, non fra
        # due blocchi. Il deposito arrivato di la' non si perde comunque.
        wake.chiudi()
        wake.feed(BLOCCO)
        assert wake.frasi_vive == {"da dentro il ciclo": "scene:avvio"}

    def test_ne_feed_ne_set_frasi_ASPETTANO_qualcuno(self) -> None:
        """⚠️ **Guardia sulla forma, e lo dichiara** — come
        `test_la_casella_del_deposito_e_ATOMICA`, e per la stessa ragione: un
        `RLock` non si incastra e non si vede da fuori, ma il ciclo audio lo
        aspetterebbe lo stesso.

        Qualunque `with` sulla strada del blocco viene segnalato, non solo i
        lock: dentro un budget di 20 ms, una cosa che si apre e si chiude va
        guardata da chi la scrive. Se un giorno ne servira' una legittima,
        questa riga si aggiorna **apposta** — ed e' il punto.
        """
        import ast
        import inspect

        from core.voice import wake as modulo

        classe = next(
            n for n in ast.walk(ast.parse(inspect.getsource(modulo)))
            if isinstance(n, ast.ClassDef) and n.name == "PhraseWake"
        )
        sulla_strada = {"feed", "set_frasi", "_applica_il_cambio_chiesto"}
        visti: set[str] = set()
        attese: dict[str, list[str]] = {}
        for m in classe.body:
            if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if m.name not in sulla_strada:
                continue
            visti.add(m.name)
            trovate = [
                f"riga {n.lineno}: with"
                if isinstance(n, (ast.With, ast.AsyncWith))
                else f"riga {n.lineno}: .{n.func.attr}()"
                for n in ast.walk(m)
                if isinstance(n, (ast.With, ast.AsyncWith))
                or (isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("acquire", "wait", "join"))
            ]
            if trovate:
                attese[m.name] = trovate

        assert visti == sulla_strada, (
            f"cercavo {sorted(sulla_strada)}, ho trovato {sorted(visti)}: un "
            "metodo sulla strada del ciclo audio e' stato rinominato o "
            "spostato, e questa guardia non guarda piu' niente"
        )
        assert attese == {}, (
            f"il ciclo audio adesso aspetta qualcuno: {attese}. Ha 20 ms per "
            "blocco; se aspetta, la pipe di `pw-record` si riempie e JARVIS "
            "diventa sordo senza che niente sollevi"
        )


class TestLeOmbreSiDiconoANCHE_a_caldo:
    """§7.2: «jarvis» oscura «jarvis silenzio». La sorveglianza esiste gia' —
    `frasi_oscurate()` — e questo test guarda che il cambio a caldo ci passi
    dentro invece di farsene una seconda."""

    def test_una_frase_scritta_a_caldo_che_ne_oscura_un_altra_lo_dice(
            self, vosk_finto) -> None:
        finto = vosk_finto()
        wake = _wake(finto, {"papa e a casa": "scene:avvio"})

        with capture_logs() as righe:
            wake.set_frasi({"jarvis": "listen", "jarvis silenzio": "mute"})

        ombre = [r for r in righe if r["event"] == "frase_wake_oscurata"]
        assert len(ombre) == 1, righe
        assert ombre[0]["prefisso"] == "jarvis"
        assert ombre[0]["irraggiungibili"] == ["jarvis silenzio"]


class TestColRiconoscitoreVERO:
    """La prova che il finto non puo' dare: che la grammatica nuova arrivi
    davvero a Kaldi, e che una frase aggiunta mentre il core gira svegli JARVIS.

    ⚠️ **Provenienza dell'audio.** `tests/fixtures/wake-jarvis.pcm.gz` e' la
    parola «Jarvis» sintetizzata da edge-tts, non una voce umana — vedi
    `test_wake_si_sveglia.py`. Prova la catena, non che riconosca Lei.

    ⚠️ **Senza il modello Vosk questo test si SALTA**, e un test saltato non e'
    un test verde (§11.7 regola 4). Il modello non sta nel repo: 87 MiB.
    """

    def _pcm(self) -> bytes:
        import gzip
        import hashlib
        from pathlib import Path

        radice = Path(__file__).resolve().parent / "fixtures"
        pcm = gzip.decompress((radice / "wake-jarvis.pcm.gz").read_bytes())
        meta = json.loads((radice / "wake-jarvis.json").read_text(encoding="utf-8"))
        assert hashlib.sha256(pcm).hexdigest() == meta["sha256_pcm"], (
            "l'audio non e' quello registrato: l'impronta non combacia"
        )
        return pcm

    def _dette(self, wake: PhraseWake, pcm: bytes) -> list[str]:
        """Un enunciato intero: i blocchi, poi la chiusura del gate."""
        dette = []
        for i in range(0, len(pcm) - 639, 640):
            t = wake.feed(pcm[i:i + 640])
            if t is not None:
                dette.append(t.frase)
        t = wake.chiudi()
        if t is not None:
            dette.append(t.frase)
        return dette

    def test_una_frase_aggiunta_A_CALDO_sveglia_JARVIS(self) -> None:
        from pathlib import Path

        from core.settings import load_settings

        modello = str(load_settings().voice.wake.model)
        if not Path(modello).exists():
            pytest.skip(f"modello Vosk assente: {modello} — SALTATO, non verde")

        pcm = self._pcm()
        # Si parte SENZA «jarvis»: e' lo stato in cui la frase non esiste.
        wake = PhraseWake({"papa e a casa": "scene:avvio"}, model_path=modello)
        assert "jarvis" not in self._dette(wake, pcm), (
            "la frase si riconosce senza essere in grammatica: questa prova "
            "non misura niente"
        )

        wake.set_frasi({"papa e a casa": "scene:avvio", "jarvis": "listen"})

        assert wake.frasi_vive == {"papa e a casa": "scene:avvio"}, (
            "il riconoscitore e' cambiato fuori dal ciclo audio"
        )
        assert self._dette(wake, pcm) == ["jarvis"], (
            "la frase scritta a caldo non sveglia JARVIS: il cambio non e' "
            "arrivato a Kaldi"
        )
        assert wake.frasi_vive == wake.frasi


class TestIlCambioAspettaIlCONFINE:
    """⚠️ La garanzia era scritta e non era imposta.

    `chiudi()` prometteva — testuale — «Il cambio aspetta il primo blocco del
    prossimo enunciato, che è il confine più pulito che ci sia». `feed()`
    applicava invece a OGNI blocco, anche a metà di una frase già cominciata: il
    riconoscitore nuovo riceveva solo la coda, e il finale usciva vuoto.

    Misurato dalla revisione del 27 agosto col modello Vosk vero, su 93 blocchi
    registrati, depositando il cambio in ogni posizione possibile:

        senza cambio:                  ['jarvis']
        depositi che cambiano l'esito: 59 su 93   (finestra continua)
        esiti distinti dentro:         {()}       ← la frase di richiamo sparisce

    Nessuna eccezione, e `wake_frasi_applicate` regolarmente nei log.

    Non era una regressione: prima `set_frasi()` sostituiva il riconoscitore
    all'istante e l'enunciato si perdeva **sempre**. Ciò che era nuovo, e falso,
    era la garanzia.
    """

    def test_a_META_enunciato_il_cambio_NON_entra(self, vosk_finto) -> None:
        finto = vosk_finto()
        wake = _wake(finto, {"jarvis": "listen"})
        wake.feed(BLOCCO)                       # l'enunciato comincia

        wake.set_frasi({"jarvis buonasera": "scene:avvio"})
        wake.feed(BLOCCO)                       # secondo blocco della STESSA frase

        assert wake.frasi_vive == {"jarvis": "listen"}, (
            "il riconoscitore e' stato sostituito a meta' enunciato: la coda "
            "arriva a una grammatica che non ha sentito l'inizio"
        )

    def test_e_al_CONFINE_entra(self, vosk_finto) -> None:
        finto = vosk_finto()
        wake = _wake(finto, {"jarvis": "listen"})
        wake.feed(BLOCCO)
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})

        wake.chiudi()                           # l'enunciato finisce
        wake.feed(BLOCCO)                       # il primo blocco del prossimo

        assert wake.frasi_vive == {"jarvis buonasera": "scene:avvio"}

    def test_il_PRIMO_blocco_in_assoluto_e_un_confine(self, vosk_finto) -> None:
        """Un wake appena costruito non ha un enunciato aperto: chi cambia le
        frasi prima che si parli non deve aspettare che qualcuno parli."""
        finto = vosk_finto()
        wake = _wake(finto, {"jarvis": "listen"})
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})
        wake.feed(BLOCCO)
        assert wake.frasi_vive == {"jarvis buonasera": "scene:avvio"}

    def test_chiudere_DUE_volte_non_apre_niente(self, vosk_finto) -> None:
        """`chiudi()` sul silenzio puro capita: non deve lasciare uno stato in
        cui il blocco dopo si comporta diversamente."""
        finto = vosk_finto()
        wake = _wake(finto, {"jarvis": "listen"})
        wake.chiudi()
        wake.chiudi()
        wake.set_frasi({"jarvis buonasera": "scene:avvio"})
        wake.feed(BLOCCO)
        assert wake.frasi_vive == {"jarvis buonasera": "scene:avvio"}


class TestIlMODELLONonSiRicaricaEAdessoLoDICE:
    """⚠️ `set_frasi()` cambia la grammatica e lascia il modello dov'è, per una
    ragione misurata: ricaricarlo costa **206 ms** sul thread di chi ha salvato
    il file. La scelta è giusta; il silenzio no.

    Chi cambiava `voice.wake.model` in `settings.toml` vedeva lo snapshot
    rispondere col percorso nuovo, `jarvis doctor` dire `ok` dopo aver
    verificato che quel file esiste, e il riconoscitore continuare col modello
    di prima **fino al riavvio**. §16 dice che nessuna soglia agisce senza
    annunciarlo: questa non agisce, e non annunciava nemmeno quello.
    """

    class _Wake:
        """Un riconoscitore vivo, costruito col modello vecchio."""

        modello_caricato_da = "/modelli/vecchio"

        def __init__(self) -> None:
            self._frasi = {"jarvis": "sveglia"}
            self.frasi = dict(self._frasi)
            self.chieste: list[dict] = []

        def set_frasi(self, frasi) -> None:
            self.chieste.append(dict(frasi))

    def _impostazioni(self, modello: str, frasi=("jarvis",)):
        class _F:
            def __init__(self, say): self.say, self.action = say, "sveglia"

        class _W:
            def __init__(self): self.model, self.phrases = modello, [_F(f) for f in frasi]

        class _V:
            def __init__(self): self.wake = _W()

        class _S:
            def __init__(self): self.voice = _V()

        return _S()

    def test_cambiare_il_MODELLO_si_annuncia(self, short_paths) -> None:
        from core.engine import Engine

        e = Engine(short_paths)
        avvisi: list[dict] = []
        e._advisory_sincrono = avvisi.append
        w = self._Wake()

        e._ricarica_frasi(w, self._impostazioni("/modelli/NUOVO"))

        assert avvisi, (
            "il modello è cambiato e il riconoscitore continua col vecchio "
            "fino al riavvio: nessuno lo dice"
        )
        assert avvisi[0]["reason"] == "wake_modello_non_ricaricato"
        assert "riavvia" in avvisi[0]["action"]

    def test_e_si_annuncia_ANCHE_se_le_frasi_non_cambiano(self, short_paths) -> None:
        """⚠️ È il caso da cui viene il difetto: chi cambia solo il modello non
        tocca le frasi, e il cancello «le frasi sono le stesse» tornava prima di
        guardare il modello."""
        from core.engine import Engine

        e = Engine(short_paths)
        avvisi: list[dict] = []
        e._advisory_sincrono = avvisi.append
        w = self._Wake()

        e._ricarica_frasi(w, self._impostazioni("/modelli/NUOVO", frasi=("jarvis",)))

        assert w.chieste == [], "le frasi non sono cambiate: non c'era da chiederle"
        assert avvisi, "il cancello sulle frasi ha ingoiato il cambio di modello"

    def test_lo_STESSO_modello_non_annuncia_niente(self, short_paths) -> None:
        from core.engine import Engine

        e = Engine(short_paths)
        avvisi: list[dict] = []
        e._advisory_sincrono = avvisi.append
        e._ricarica_frasi(self._Wake(), self._impostazioni("/modelli/vecchio"))
        assert avvisi == []

    def test_lo_snapshot_dice_il_modello_VIVO(self, short_paths) -> None:
        from core.engine import Engine

        e = Engine(short_paths)
        assert e._modello_wake_vivo() is None, "a voce spenta non si sa, e non si inventa"
        e._wake = self._Wake()
        assert e._modello_wake_vivo() == "/modelli/vecchio"

    def test_il_wake_VERO_dice_da_dove_ha_caricato(self, vosk_finto) -> None:
        """⚠️ La bocciatura l'ha detto: i test qui sopra usano un riconoscitore
        finto di comodo, quindi svuotando la proprietà vera restavano verdi.
        Qui il `PhraseWake` è quello di produzione — è solo Vosk a essere
        sostituito, perché il modello vero pesa 87 MiB e 206 ms."""
        finto = vosk_finto()
        w = _wake(finto)
        assert w.modello_caricato_da == "/finto"

    def test_e_senza_modello_non_INVENTA_un_percorso(self, vosk_finto) -> None:
        vosk_finto()
        assert PhraseWake({"jarvis": "sveglia"}).modello_caricato_da is None

    def test_lo_SNAPSHOT_porta_i_due_valori_accanto(self, short_paths) -> None:
        """⚠️ Anche questa l'ha trovata la bocciatura: rimettendo
        `str(s.voice.wake.model)` nello snapshot non cadeva niente, perché i
        test guardavano il lettore e non il campo che il Signore legge.

        I due valori stanno **accanto**: chi guarda distingue «non sto
        ascoltando» da «sto ascoltando con un altro modello».
        """
        from core.engine import Engine

        e = Engine(short_paths)
        v = e.state_snapshot()["voce"]
        assert v["wake_model"] is None, "a voce spenta non si sa, e non si inventa"
        assert v["wake_model_chiesto"] == str(e.settings.voice.wake.model)

        e._wake = self._Wake()
        v = e.state_snapshot()["voce"]
        assert v["wake_model"] == "/modelli/vecchio", (
            "lo snapshot risponde con l'impostazione: cambiandola, direbbe il "
            "modello nuovo mentre il riconoscitore continua col vecchio"
        )
        assert v["wake_frasi"] == 1

    def test_e_il_DOCTOR_non_dice_piu_ok(self) -> None:
        """La divergenza vale `fail` e non `warn`, per la stessa ragione di
        `_check_unit`: una configurazione che il file crede attiva e che sulla
        macchina non lo è è peggio di una che si sa spenta."""
        from core.doctor import _check_wake

        snap = {"voce": {"wake_model": "/modelli/vecchio",
                         "wake_model_chiesto": "/modelli/NUOVO", "wake_frasi": 1}}
        c = _check_wake(snap, None)
        assert c.stato == "fail"
        assert "vecchio" in c.dettaglio and "NUOVO" in c.dettaglio
        assert "riavvia" in c.dettaglio
