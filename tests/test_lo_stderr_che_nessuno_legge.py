"""`stderr=PIPE` era aperto e non lo leggeva nessuno.

## Due difetti nello stesso tubo

`ClaudeT1.start()` apre il processo con `stderr=asyncio.subprocess.PIPE`, e in
tutto il repository non c'era **una sola lettura** di quel flusso.

### ① Trecento kilobyte, e T1 resta appeso per sempre

Il tubo di Linux tiene 64 KiB; asyncio ne pompa altrettanti nel proprio
`StreamReader` anche se nessuno legge, e **poi** il controllo di flusso mette in
pausa la lettura, il tubo si riempie e il figlio si ferma sulla `write`.
Misurato, con un figlio che scrive N byte su stderr e poi risponde su stdout:

    200 000 byte   arriva in fondo
    300 000 byte   ⚠️ BLOCCATO

E con un `ClaudeT1` vero, lo stesso figlio, A/B sul solo lettore:

    senza lettore   ⚠️ BLOCCATO      (8 s, il timeout della prova)
    con lettore     risponde         11 ms

Il guasto è silenzioso: `ask()` andrebbe in timeout, JARVIS degraderebbe,
riavvierebbe — e il processo nuovo si fermerebbe allo stesso punto.

### ② Due criteri di rilevamento auth su tre erano irraggiungibili

`classifica(returncode, stderr)` riconosce l'autenticazione in tre modi:
`returncode == 41`, «authentication» nello stderr, «unauthorized» nello stderr.
`riavvia_dopo_guasto` la chiamava **con un solo argomento**, quindi lo stderr
era sempre `""`. Misurato su un figlio che muore dicendo
`Error: Unauthorized - token expired` con `returncode 1`:

    classifica(rc, stderr) -> auth        con la cura
    classifica(rc, "")     -> transient   com'era

Cioè un token scaduto veniva preso per un guasto passeggero e **riprovato in
ciclo** — che è testualmente ciò che §5.6 vieta.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from pathlib import Path

import pytest

from core.llm.claude_t1 import ATTESA_EOF_S, TETTO_STDERR, ClaudeT1, Uscita

def _script(stderr_byte: int = 0, risposta: str = "", codice: int = 0) -> str:
    """Un figlio che parla la lingua di Claude Code, quanto basta."""
    righe = ["import sys, json"]
    if stderr_byte:
        righe.append(f"sys.stderr.write('x' * {stderr_byte}); sys.stderr.flush()")
    if risposta:
        ev = json.dumps({"type": "stream_event", "event": {
            "delta": {"type": "text_delta", "text": risposta}}})
        righe.append(f"sys.stdout.write({ev!r} + chr(10))")
        righe.append(f"sys.stdout.write({json.dumps({'type': 'result'})!r} + chr(10))")
        righe.append("sys.stdout.flush()")
    righe.append(f"sys.exit({codice})")
    return "\n".join(righe)


class _T1(ClaudeT1):
    """Un `ClaudeT1` **vero**, con un figlio che non è `claude`.

    ⚠️ Si sovrascrive solo `argv()`: `start()`, `stop()`, il lettore, `ask()` e
    `classifica` sono quelli di produzione. Un finto della classe intera non
    potrebbe misurare un tubo che si riempie.
    """

    def __init__(self, script: str, cwd: Path, **kw) -> None:
        # ⚠️ Una cwd PROPRIA per ogni prova. Con una condivisa, due test in
        # parallelo — o in ordine casuale, che è come gira questa suite — si
        # vedono i residui l'uno dell'altro, e `start()` lo dice a voce alta
        # perché §5.2 vuole la cwd vuota.
        cwd.mkdir(parents=True, exist_ok=True)
        super().__init__(modello="x", cwd=cwd, **kw)
        self._script = script

    def argv(self) -> list[str]:
        return ["python3", "-c", self._script]


async def _turno(t1: ClaudeT1, timeout: float = 4.0) -> str | None:
    """La risposta, o `None` se T1 è rimasto appeso."""
    pezzi: list[str] = []

    async def giro() -> None:
        async for p in t1.ask("ciao", timeout=timeout):
            pezzi.append(p)

    try:
        await asyncio.wait_for(giro(), timeout=timeout + 2.0)
    except asyncio.TimeoutError:
        return None
    return "".join(pezzi)


class TestIlTuboNonSiRIEMPIE:
    async def test_trecento_kilobyte_di_stderr_NON_fermano_il_turno(self, tmp_path: Path) -> None:
        """⚠️ Il test che boccia. Senza il lettore, questo turno non finisce."""
        t1 = _T1(_script(stderr_byte=300_000, risposta="eccomi"), tmp_path)
        await t1.start()
        try:
            assert await _turno(t1) == "eccomi", (
                "T1 è rimasto appeso: il tubo dello stderr si è riempito e il "
                "figlio si è fermato sulla `write`"
            )
        finally:
            await t1.stop()

    async def test_e_SENZA_il_lettore_si_ferma_davvero(self, tmp_path: Path) -> None:
        """Il controllo del controllo: se togliendo il lettore il figlio
        arrivasse in fondo lo stesso, il test sopra sarebbe vero per assenza
        del fenomeno — e non proverebbe niente.

        ⚠️ Qui NON si passa da `ask()`, e non è pigrizia: un turno abbandonato
        lascia in volo `_drena()`, che legge lo stdout per novanta secondi. In
        una prova che finisce in due, quel compito sopravvive al test e il
        rumore dei suoi trasporti viene attribuito al test SUCCESSIVO — che
        diventa rosso senza averne colpa. Costato tre giri, e misurato: quattro
        trasporti aperti da questo test solo.

        Il figlio scrive lo stderr **e poi** lo stdout: se si ferma sulla
        `write`, la risposta non arriva mai.
        """
        t1 = _T1(_script(stderr_byte=300_000, risposta="eccomi"), tmp_path)
        await t1.start()
        t1._lettore.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t1._lettore
        t1._lettore = None
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(t1._proc.stdout.readline(), timeout=2.0)
        finally:
            # Si SBLOCCA, non si uccide: rimettendo un lettore il figlio
            # riparte, finisce e muore da solo, e i trasporti si chiudono come
            # in ogni altro turno.
            if t1._proc is not None and t1._proc.returncode is None:
                t1._lettore = asyncio.create_task(t1._leggi_stderr(t1._proc))
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(t1._proc.wait(), timeout=3.0)
            await t1.stop()

    async def test_si_tiene_la_CODA_e_non_tutto(self, tmp_path: Path) -> None:
        """Un processo persistente che accumulasse ogni byte di stderr
        crescerebbe finché c'è memoria."""
        t1 = _T1(_script(stderr_byte=300_000, risposta="x"), tmp_path)
        await t1.start()
        try:
            await _turno(t1)
            assert len(t1._stderr) == TETTO_STDERR
        finally:
            await t1.stop()

    async def test_e_il_lettore_MUORE_col_processo(self, tmp_path: Path) -> None:
        """Un compito che sopravvive al suo processo è un compito che nessuno
        fermerà."""
        t1 = _T1(_script(risposta="x"), tmp_path)
        await t1.start()
        lettore = t1._lettore
        await t1.stop()
        assert t1._lettore is None
        assert lettore.done(), "il lettore è rimasto in volo dopo `stop()`"


class TestLaCAUSADellaMorteSiLEGGE:
    async def test_unauthorized_sullo_stderr_e_un_AUTH(self, tmp_path: Path) -> None:
        """⚠️ `classifica` ha tre criteri e ne riceveva uno.

        Con `returncode 1` e «Unauthorized» sullo stderr, prima diceva
        `transient` — cioè si riprovava in ciclo contro un token scaduto, che è
        ciò che §5.6 vieta.
        """
        t1 = _T1("import sys\n"
                 "sys.stderr.write('Error: Unauthorized - token expired')\n"
                 "sys.stderr.flush()\nsys.exit(1)", tmp_path)
        await t1.start()
        try:
            await t1._proc.wait()
            rc = t1._proc.returncode
            testo = await t1.stderr_del_morto()
            assert "unauthorized" in testo.lower()
            assert t1.classifica(rc, testo) is Uscita.AUTH
            assert t1.classifica(rc, "") is Uscita.TRANSIENT, (
                "senza stderr sarebbe un guasto passeggero: è la misura di "
                "quanto costava non leggerlo"
            )
        finally:
            await t1.stop()

    async def test_riavvia_dopo_guasto_LO_PASSA(self, tmp_path: Path) -> None:
        """La giunzione: non basta che `classifica` sappia leggerlo, deve
        riceverlo dalla strada viva."""
        t1 = _T1("import sys\n"
                 "sys.stderr.write('authentication failed'); sys.stderr.flush()\n"
                 "sys.exit(1)", tmp_path)
        detti: list[str] = []
        t1._su_annuncio = detti.append
        await t1.start()
        try:
            await t1._proc.wait()
            assert await t1.riavvia_dopo_guasto() is Uscita.AUTH, (
                "un token scaduto è stato preso per un guasto passeggero, e si "
                "riproverà in ciclo"
            )
            assert detti and "autenticazione" in detti[0]
        finally:
            await t1.stop()

    async def test_si_ASPETTA_l_EOF_prima_di_classificare(self, tmp_path: Path) -> None:
        """⚠️ Senza l'attesa, `classifica` leggerebbe un buffer a metà proprio
        nell'istante in cui i byte che mancano sono quelli che spiegano la
        morte — e la corsa si perde più spesso quando il processo muore in
        fretta, cioè nel caso peggiore."""
        t1 = _T1("import sys\n"
                 "sys.stderr.write('Unauthorized'); sys.stderr.flush()\n"
                 "sys.exit(1)", tmp_path)
        await t1.start()
        try:
            # Nessuna attesa: si chiede subito, come farebbe la strada viva.
            testo = await t1.stderr_del_morto()
            assert "Unauthorized" in testo
        finally:
            await t1.stop()

    async def test_l_attesa_ha_un_TETTO(self, tmp_path: Path) -> None:
        """Un figlio che tiene aperto lo stderr per sempre non deve poter
        bloccare la classificazione: si decide con quello che c'è."""
        t1 = _T1("import sys, time\n"
                 "sys.stderr.write('Unauthorized'); sys.stderr.flush()\n"
                 "time.sleep(30)", tmp_path)
        await t1.start()
        try:
            await asyncio.sleep(0.2)      # scrive e resta vivo: non c'e' morte da attendere
            t0 = asyncio.get_running_loop().time()
            testo = await t1.stderr_del_morto()
            durata = asyncio.get_running_loop().time() - t0
            assert durata < ATTESA_EOF_S + 1.0, f"ha atteso {durata:.1f} s"
            assert "Unauthorized" in testo, "e classifica con quello che c'è"
        finally:
            await t1.stop()
