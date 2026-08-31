"""Il microfono VERO: una frase detta in aria sveglia JARVIS — §7.2, §11.7.

    XDG_CONFIG_HOME=<albero>/cfg XDG_DATA_HOME=<albero>/dati \\
      uv run python scripts/prova_microfono.py --voce sintetica
    ... --voce umana --secondi 30        # parla il Signore, e allora e' vera

E' l'ultimo `NON VERIFICATO` di §26.7: la scrittura di una frase di wake dalla
pagina e il ricarico a caldo sono provati dal vivo dal 30-31 agosto; che la
frase nuova **svegli JARVIS detta a un microfono** non lo era. Ne mancava
l'ultimo metro, quello che va dall'aria al riconoscitore.

## Che cosa attraversa

    imposta_valore  ->  conferma §6.2  ->  tomlkit  ->  settings.toml
      ->  inotify (watchdog VERO)  ->  SettingsStore.reload()
      ->  Engine._ricarica_frasi   ->  PhraseWake.set_frasi()
      ->  pw-record  ->  ARIA  ->  microfono  ->  Vosk  ->  Trigger

⚠️ **Il ricarico e' quello dell'Engine, non una copia.** Ci si iscrive con
`engine._ricarica_frasi`, che prende il wake per parametro: cosi' il cancello
«il file e' cambiato altrove», l'avviso sul modello che non si ricarica e il
rimbalzo sul loop sono quelli veri. Riscriverli qui vorrebbe dire provare la
copia invece dell'originale — ed e' il difetto che questo progetto ha gia'
misurato tre volte, l'ultima con `nascosto` che cadeva nella terza copia
campo-per-campo (fetta 5).

⚠️ **E l'inotify e' quello vero.** Il residuo ② di §26.7 diceva che il ricarico
a caldo era provato con `store.reload()` chiamato a mano. Qui non lo chiama
nessuno: si scrive il file e si aspetta che l'evento arrivi da solo.

## Perche' un banco e non `Engine` col grado voce acceso

`voice.enabled = true` costruisce il grado intero e **spawna T1**, un processo
`claude` persistente (§5.2). Il wake non tocca nessun LLM — sta prima di T0,
che gia' non ne tocca (invariante 14) — quindi accenderlo farebbe spendere
l'abbonamento per provare un percorso che non lo attraversa. E' la stessa
ragione per cui `scripts/banco_haiku.py` sta fuori da `pytest`: **un test che
spende non e' un test**.

Il banco monta i pezzi di produzione del solo percorso wake, e l'`Engine` c'e'
davvero: da lui vengono le impostazioni, il `SettingsStore` sorvegliato e
`audio()`, cioe' `pw-record`.

## Le due voci, e quale delle due prova che cosa

* `--voce sintetica` — espeak-ng via `spd-say` esce dall'**altoparlante** e
  rientra dal **microfono**. Attraversa l'aria per davvero, e' ripetibile e la
  puo' eseguire una macchina. Non e' una voce umana.
* `--voce umana` — il banco ascolta e basta, e parla il Signore. E' l'unica che
  prova cio' che §7.2 descrive davvero.

⚠️ **Il muto dell'altoparlante si tocca, e si rimette.** Con `--voce sintetica`
il banco toglie il muto, suona, e lo rimette com'era in un `finally`. E' la
sola cosa del sistema che questo file cambia, e lo dichiara perche' `AudioIO`
promette il contrario per il volume **di JARVIS**: quella promessa riguarda il
mixer durante l'esercizio, non un banco che deve produrre un suono.

## Il microfono di questa macchina, misurato il 31 agosto 2026

Due sorgenti, e una sola sente. Provate suonando un tono di 1 kHz
dall'altoparlante e guardando l'energia a quella frequenza:

    61  ALC257 analogico (presa jack)   0,01 -> 0,02    SORDA: non c'e' niente
    62  DMIC digitale    (predefinita)  0,22 -> 633     e' quella predefinita

⚠️ **E il DMIC apre il gate per 200 ms appena lo si accende.** L'energia del
VAD, finestre da 100 ms:

      0 ms   0,72766   ← 60 volte la soglia di apertura (0,012)
    100 ms   0,02041   ← ancora aperta
    200 ms   0,00325   ← stanza in quiete, gate chiuso

Cioe' **ogni apertura del microfono comincia con due blocchi di rumore dentro
Vosk**, a gate aperto, seguiti dalla chiusura e da un `FinalResult` su una
raffica. Non fa danno — la grammatica vincolata e `[unk]` scartano tutto — ma
c'e', e in esercizio non lo scarta nessuno. Il banco lo salta con
`ANTIPASTO_S` per non misurare quello.

La **polarizzazione continua** di questo convertitore, invece, e' cosa gia'
nota e gia' risolta: -8600 circa, e `VAD.energia` toglie la media proprio per
quello (vedi la sua docstring, misurata il 28 agosto).
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import subprocess
import sys
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import log as core_log  # noqa: E402
from core.engine import Engine  # noqa: E402
from core.tools import registry as R  # noqa: E402
from core.traccia import Origine, Traccia  # noqa: E402
from core.platform.linux_audio import tono  # noqa: E402
from core.voice.audio_io import dal_microfono  # noqa: E402
from core.voice.pipeline import VAD  # noqa: E402
from core.voice.wake import PhraseWake  # noqa: E402

RATE = 16_000
#: Quanto si butta via all'apertura del flusso: due volte e mezzo i 200 ms
#: della raffica d'avvio misurata nell'intestazione. E' una proprieta' di
#: QUESTA macchina, non una costante del progetto — per questo vive qui e non
#: in `linux_audio.py`, dove diventerebbe una decisione di piattaforma presa
#: da un banco.
ANTIPASTO_S = 0.5

#: La frase che si aggiunge. **Non comincia per «jarvis»**, e non e' una
#: preferenza: `PhraseWake` avvisa che una frase lunga con un prefisso gia'
#: noto e' irraggiungibile — «Kaldi puo' chiudere l'enunciato sulla frase
#: corta, che e' gia' valida». Misurato provando «jarvis buongiorno», che
#: infatti ha svegliato su «jarvis».
FRASE = "accendi la scrivania"
AZIONE = "scene:avvio"


def voce_sintetica(frase: str) -> None:
    """Lo dice l'altoparlante, a velocita' normale.

    ⚠️ **`-r -20` non serviva.** La prima stesura rallentava la voce
    credendo che le pause fra le parole facessero chiudere il gate a meta'
    frase. Misurato: 3 giri riusciti su 4 da lente, 4 su 6 da normali — cioe'
    nessuna differenza, e l'ipotesi era sbagliata. La causa vera era il
    momento in cui il cambio di frasi entra in vigore; vedi l'attesa su
    `frasi_vive` in `main()`.
    """
    subprocess.run(["spd-say", "-l", "it", "-w", "-r", "0", frase],
                   check=False)


#: Quanto forte parla il banco. Non e' una preferenza: col volume a 0,16 —
#: com'era su questa macchina il 31 agosto — la frase arriva al microfono
#: troppo debole e Vosk non chiude l'enunciato. Si rimette com'era, dopo.
VOLUME_PROVA = "0.7"


def _altoparlante() -> str:
    """Muto e volume, come sono adesso. Una riga sola, da rimettere identica."""
    return subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                          capture_output=True, text=True).stdout.strip()


def _accendi() -> None:
    """Toglie il muto e mette il volume del banco. Sempre in coppia con
    `_rimetti()`, dentro un `try`/`finally`."""
    subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"],
                   check=False)
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                    VOLUME_PROVA], check=False)


def _rimetti(riga: str) -> None:
    volume = riga.split()[1] if len(riga.split()) > 1 else "1.0"
    subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", volume],
                   check=False)
    subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@",
                    "1" if "MUTED" in riga else "0"], check=False)


async def ascolta(engine: Engine, wake: PhraseWake, trovati: list,
                  misura: dict, diagnosi: bool = False) -> None:
    """Il microfono di produzione, col gate di produzione, dentro Vosk.

    ⚠️ **Il gate non e' facoltativo, e la prima stesura di questo banco lo
    saltava.** Senza, `feed()` non ha mai un enunciato chiuso: `chiudi()` e'
    l'unico a riabbassare `_enunciato_aperto`, e un cambio di frasi depositato
    da `set_frasi()` **non entra mai in vigore**. Misurato il 31 agosto: la
    frase arrivava al wake — `frasi_ricaricate_a_caldo` nei log — e
    `frasi_vive` restava l'elenco di prima.

    Il `VAD` e' quello vero, importato da `pipeline.py`. Il ciclo ne
    rispecchia la forma (`pipeline.py:492-540`) meno il barge-in e il turno,
    che vogliono TTS e T1: qui non c'e' nessuno che parli sopra e nessun turno
    da tenere aperto.
    """
    vad = VAD()
    aperto = False
    gate_a = 0.0
    inizio = time.monotonic()
    async for blocco in dal_microfono(engine.audio, RATE):
        if time.monotonic() - inizio < ANTIPASTO_S:
            continue
        e = VAD.energia(blocco)
        # ⚠️ **Il massimo sta nel DIZIONARIO, e non anche in una variabile
        # locale.** Due stesure sbagliate di fila su tre righe, ed entrambe
        # rendevano falso proprio il numero che deve diagnosticare gli altri:
        #
        # 1. `misura["picco"] = picco` DOPO l'`async for` — un punto che non
        #    si raggiunge mai, perche' il compito viene cancellato. Riferiva
        #    sempre `0.0000`.
        # 2. `picco = misura["picco"] = max(picco, e)` — chi azzera il
        #    dizionario fra una ripetizione e l'altra non azzera la locale,
        #    che al blocco dopo ci riscrive dentro il massimo di TUTTA la
        #    sessione. Misurato: sette ripetizioni su dieci riferivano
        #    `0.0366` identico alla quarta cifra, che per dieci frasi dette da
        #    una persona non e' un dato, e' una firma.
        #
        # Una sola sede del massimo, e chi la azzera la azzera davvero.
        misura["picco"] = max(misura["picco"], e)
        if vad.parla(blocco):
            if not aperto:
                # Il primo blocco con voce dentro: e' l'unico capo che rende
                # `latenza_risveglio_ms` un numero invece di uno zero.
                gate_a = time.monotonic()
                if diagnosi:
                    print(f"   · gate APRE    energia={e:.4f}", flush=True)
            aperto = True
            t = wake.feed(blocco)
        elif aperto:
            aperto = False
            t = wake.chiudi()               # e' QUI che il cambio puo' entrare
            if diagnosi and t is None:
                print("   · gate CHIUDE  nessuna frase nota in questo enunciato",
                      flush=True)
        else:
            continue
        if t is not None:
            # ⚠️ **`aperto_a` lo riempie solo `pipeline.py:625`**, e questo
            # banco la pipeline non la usa: senza questa riga
            # `latenza_risveglio_ms` torna zero, e il banco riferirebbe solo
            # `latenza_ms` — che la docstring di `Trigger` dichiara «NON la
            # latenza di risveglio: il costo di UNA `AcceptWaveform` o di un
            # `FinalResult()`». Il numero di §7.5 e' l'altro.
            t = dataclasses.replace(t, aperto_a=gate_a)
            trovati.append(t)
            print(f"[SVEGLIATO] frase={t.frase!r} azione={t.azione!r} "
                  f"kaldi={t.latenza_ms:.1f} ms "
                  f"risveglio={t.latenza_risveglio_ms:.0f} ms", flush=True)


async def aggiungi_dalla_strada_vera(chiave: str, elemento: dict) -> None:
    """La frase entra col tool che invoca la pagina, conferma compresa.

    ⚠️ **La conferma si approva qui**, e non e' una scorciatoia sull'invariante
    3: che una persona veda il riepilogo e clicchi «approva» — o «rifiuta», e
    allora non succede niente — e' provato attraversando la finestra vera il
    30 e il 31 agosto (`docs/acceptance/LE-STRUTTURE-SI-CAMBIANO.md` §⑥ e
    §⑥bis). Cio' che questo banco prova sta **dopo** quel clic.
    """
    R.set_confirm_hook(lambda piano: asyncio.sleep(0, result="approvato"))
    r = await R.invoke("imposta_valore",
                       {"chiave": chiave, "operazione": "aggiungi",
                        "elemento": elemento},
                       traccia=Traccia.nuova(Origine.UI))
    print(f"[scritta] ok={r.ok} errore={r.error} "
          f"verdetto={getattr(r.verifica, 'verdetto', None)}", flush=True)
    if not r.ok:
        raise SystemExit(f"la frase non e' stata scritta: {r.error}")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voce", choices=("sintetica", "umana"), default="sintetica")
    ap.add_argument("--frase", default=FRASE)
    ap.add_argument("--secondi", type=float, default=25.0,
                    help="quanto si aspetta OGNI ripetizione")
    ap.add_argument("--ripetizioni", type=int, default=1,
                    help="un giro solo e' un fatto, non una statistica")
    ap.add_argument("--senza-aggiunta", action="store_true",
                    help="non aggiunge niente: prova solo le frasi gia' nel file")
    a = ap.parse_args()

    core_log.configura()
    engine = Engine()
    s = engine.settings
    frasi = {f.say: f.action for f in s.voice.wake.phrases}
    print(f"[frasi nel file] {sorted(frasi)}", flush=True)

    wake = PhraseWake(frasi, model_path=str(s.voice.wake.model))

    # ⚠️ Il ricarico e' `Engine._ricarica_frasi`, col rimbalzo sul loop che
    # `_gradi()` fa in esercizio: il thread del watchdog non entra nel wake.
    ciclo = asyncio.get_running_loop()
    engine._store.subscribe(
        lambda nuove: ciclo.call_soon_threadsafe(engine._ricarica_frasi,
                                                 wake, nuove))
    engine._store.start()

    trovati: list = []
    misura: dict = {"picco": 0.0}
    orecchio = asyncio.create_task(
        ascolta(engine, wake, trovati, misura, diagnosi=a.voce == "umana"))
    await asyncio.sleep(ANTIPASTO_S + 0.5)

    atteso = a.frase
    if not a.senza_aggiunta:
        await aggiungi_dalla_strada_vera(
            "voice.wake.phrases", {"say": a.frase, "action": AZIONE})
        # Non si chiama `reload()`: si aspetta l'inotify.
        for _ in range(100):
            if a.frase in wake.frasi:
                break
            await asyncio.sleep(0.1)
        print(f"[inotify] la frase e' arrivata al wake: {a.frase in wake.frasi}",
              flush=True)

        # ⚠️ **E poi si aspetta che sia VIVA, non solo dichiarata.**
        #
        # `set_frasi()` deposita; `feed()` applica, e solo a enunciato chiuso.
        # Finche' il gate resta aperto il riconoscitore in uso e' ancora quello
        # di prima, e una frase detta in quella finestra non sveglia nessuno.
        # Non e' un difetto — e' la garanzia scritta in `PhraseWake.chiudi()`,
        # che un enunciato gia' cominciato non venga buttato via — ma parlare
        # dentro quella finestra misura la vecchia grammatica credendo di
        # misurare la nuova.
        #
        # Misurato: senza questa attesa il banco riusciva **3 volte su 4**, e i
        # giri andati a vuoto erano quelli in cui la raffica d'avvio del DMIC
        # aveva lasciato il gate aperto fino a dopo la frase.
        for _ in range(150):
            if a.frase in wake.frasi_vive:
                break
            await asyncio.sleep(0.1)
        viva = a.frase in wake.frasi_vive
        print(f"[wake] la frase e' VIVA nel riconoscitore: {viva}", flush=True)
        if not viva:
            print("[wake] NON e' viva: dirla adesso proverebbe la grammatica "
                  "di prima", flush=True)
    else:
        # Con `--senza-aggiunta` si prova cio' che il file ha gia': se la frase
        # chiesta c'e' vale quella, altrimenti la prima in ordine.
        atteso = a.frase if a.frase in frasi else sorted(frasi)[0]

    # ── le ripetizioni, per misurare invece di constatare ───────────────────
    #
    # ⚠️ **Un giro solo non e' una misura, e il 31 agosto e' stato dichiarato
    # cosi': «un trigger solo, non ventiquattro: e' un fatto, non una
    # statistica».** Le ripetizioni stanno in UNA sessione e non in N processi
    # perche' chi parla non vede questo terminale: fuori di qui non c'e' modo
    # di dirgli «adesso», e il tono e' l'unico canale che arriva.
    esiti: list = []
    for n in range(1, a.ripetizioni + 1):
        fatti = len([t for t in trovati if t.frase == atteso])
        misura["picco"] = 0.0
        t0 = time.monotonic()

        if a.voce == "sintetica":
            prima = _altoparlante()
            _accendi()
            try:
                print(f"[{n}/{a.ripetizioni}] dico {atteso!r} dall'altoparlante",
                      flush=True)
                await asyncio.to_thread(voce_sintetica, atteso)
            finally:
                _rimetti(prima)
        else:
            # ⚠️ **Un tono, non una scritta.** Chi parla non guarda il
            # terminale. E' lo stesso `tono()` di §7.2 regola 2, per la stessa
            # ragione per cui esiste: «un tono, non una voce», perche' una voce
            # arriva quando l'utente sta gia' parlando.
            prima = _altoparlante()
            _accendi()
            try:
                await engine.audio.play(tono(880, 120))
            finally:
                _rimetti(prima)
            print(f"\n  ▶ {n}/{a.ripetizioni} — DILLO ADESSO: «{atteso}»\n",
                  flush=True)

        # Si smette appena la frase arriva: chi ha appena parlato vuole sapere
        # subito se e' stato sentito, e il silenzio dopo il successo somiglia a
        # un fallimento.
        scadenza = time.monotonic() + a.secondi
        preso = None
        while time.monotonic() < scadenza:
            giusti = [t for t in trovati if t.frase == atteso]
            if len(giusti) > fatti:
                preso = giusti[-1]
                break
            await asyncio.sleep(0.05)
        esiti.append((preso, misura["picco"], time.monotonic() - t0))
        if preso is None:
            print(f"[{n}/{a.ripetizioni}] ✗ niente, picco {misura['picco']:.4f}",
                  flush=True)
        # Un respiro fra una e l'altra: senza, il tono della prossima cade
        # dentro la coda di isteresi del gate appena chiuso.
        await asyncio.sleep(1.0)

    orecchio.cancel()
    # ⚠️ Si ASPETTA la cancellazione. Senza, il generatore di `dal_microfono`
    # non arriva al proprio `finally` — quello che uccide `pw-record` — e il
    # processo muore lasciando il trasporto da chiudere al garbage collector,
    # a loop gia' chiuso: «RuntimeError: Event loop is closed» su una prova
    # riuscita, che e' il modo migliore per far dubitare di una misura buona.
    await asyncio.gather(orecchio, return_exceptions=True)
    engine._store.stop()

    riusciti = [(t, e, d) for t, e, d in esiti if t is not None]
    print(f"\n═══ ESITO — {a.voce}, {len(riusciti)} su {a.ripetizioni} ═══",
          flush=True)
    print("   #    kaldi    risveglio    picco    dal tono", flush=True)
    for i, (t, e, d) in enumerate(esiti, 1):
        print(f"  {i:2d}   " + (f"{t.latenza_ms:6.2f} ms  {t.latenza_risveglio_ms:6.0f} ms"
                                if t else "     ✗            ✗   ")
              + f"   {e:.4f}   {d:6.2f} s", flush=True)
    if riusciti:
        lat = sorted(t.latenza_ms for t, _, _ in riusciti)
        m = lat[len(lat) // 2] if len(lat) % 2 else (lat[len(lat)//2-1]
                                                     + lat[len(lat)//2]) / 2
        print(f"\n  kaldi      mediana {m:.2f} ms   min {lat[0]:.2f}   "
              f"max {lat[-1]:.2f}", flush=True)
        # ⚠️ **E' QUESTA la latenza di §7.5**, non quella sopra: dal primo
        # blocco con voce al riconoscimento. Ha dentro i 240 ms di coda del
        # VAD (`coda_blocchi=12`), che e' il termine che domina tutto.
        ris = sorted(t.latenza_risveglio_ms for t, _, _ in riusciti)
        print(f"  risveglio  mediana {ris[len(ris)//2]:.0f} ms   min {ris[0]:.0f}"
              f"   max {ris[-1]:.0f}   (§7.5 — dentro ci sono i 240 ms di coda "
              f"del VAD)", flush=True)
        pic = sorted(e for _, e, _ in riusciti)
        print(f"  picco    mediana {pic[len(pic)//2]:.4f}   min {pic[0]:.4f}   "
              f"max {pic[-1]:.4f}   (apre a 0,0120)", flush=True)
    print(f"  frasi vive al wake: {sorted(wake.frasi_vive)}", flush=True)
    return 0 if len(riusciti) == a.ripetizioni else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
