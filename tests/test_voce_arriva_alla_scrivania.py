"""Una frase riconosciuta arriva alla scrivania.

## Il difetto: il topic non esisteva

`_voce_su_azione` trasmetteva

    {"topic": "ui.action", "azione": "scene:welcome_home", "args": {}}

e **nessuno ascolta `ui.action`**. Il renderer si iscrive a `ui.intent` con
`{intento, args}` (`ui/src/desk/scrivania.js:800`), e `applicaScena` legge
`args.nome`: la stringa `scene:welcome_home` va spezzata, non passata intera.

Dal vivo si vedeva cosi': detto «papà è a casa», il log scriveva

    wake_trigger    azione=scene:welcome_home  frase='papa e a casa'
    azione_diretta  azione=scene:welcome_home  latenza_ms=7.72

— cioe' JARVIS aveva sentito, riconosciuto e agito — **e sullo schermo non
succedeva niente.** Indistinguibile da «non mi ha sentito», ed e' il motivo per
cui la diagnosi e' partita dal microfono, che stava benissimo.

## E l'altra meta' era rotta pure lei

`esegui_t0()` produceva GIA' il messaggio giusto, e con due destinazioni:
`INTENTI_UI` verso il socket, e `registry.invoke()` per gli intenti che nominano
un tool — cioe' con la conferma umana dove serve (invariante 3). Trasmettendo a
mano, **un intento vocale che nominava un tool non lo invocava affatto**.

Due pezzi scritti, provati, e mai congiunti: la stessa specie di §13, del
`Watcher` delle news, e di `_gradi()` che componeva solo T1.
"""

from __future__ import annotations

import asyncio

import pytest

from core.engine import Engine


@pytest.fixture
def motore(short_paths):
    return Engine(short_paths)


async def _instrada(e: Engine, azione: str, args: dict | None = None) -> list[dict]:
    inviati: list[dict] = []

    async def falso(msg):
        inviati.append(msg)

    e._ws.broadcast = falso
    await e._instrada_voce(azione, args or {})
    return inviati


class TestLaFraseArrivaAlRENDERER:
    async def test_una_scena_diventa_un_INTENTO(self, motore) -> None:
        """Il difetto alla lettera: topic giusto, e la stringa spezzata."""
        inviati = await _instrada(motore, "scene:welcome_home")
        assert inviati == [{
            "topic": "ui.intent", "intento": "scene",
            "args": {"nome": "welcome_home"},
        }], inviati

    async def test_il_topic_MORTO_non_si_usa_piu(self, motore) -> None:
        inviati = await _instrada(motore, "scene:goodnight")
        assert all(m["topic"] != "ui.action" for m in inviati), (
            "`ui.action` e' tornato: nessuno lo ascolta, e una frase "
            "riconosciuta si perderebbe di nuovo in silenzio"
        )

    async def test_gli_ARGOMENTI_di_T0_arrivano_interi(self, motore) -> None:
        """L'altro chiamante: `_ascolta_e_rispondi` passa `intent.tool` con i
        suoi argomenti. `open_panel` senza `{"panel": ...}` non e' un comando,
        e' una categoria."""
        inviati = await _instrada(motore, "open_panel", {"panel": "globo"})
        assert inviati == [{
            "topic": "ui.intent", "intento": "open_panel",
            "args": {"panel": "globo"},
        }], inviati

    async def test_un_azione_SENZA_destinazione_si_dice(self, motore) -> None:
        """`mute` e' nella grammatica di §7 e non e' ne' in `INTENTI_UI` ne'
        nel registry. Prima non arrivava da nessuna parte **in silenzio**;
        adesso c'e' una riga che lo dice."""
        from structlog.testing import capture_logs

        with capture_logs() as righe:
            inviati = await _instrada(motore, "mute")
        assert inviati == [], inviati
        assert any(r.get("event") == "voce_senza_destinazione" for r in righe), righe

    async def test_un_intento_che_nomina_un_TOOL_lo_invoca(self, motore) -> None:
        """La meta' che il socket a mano saltava del tutto: `esegui_t0()`
        instrada verso `registry.invoke()`, che e' dove vive la conferma umana
        (invariante 3)."""
        from core.tools import registry

        chiamate: list[tuple[str, dict]] = []

        async def finto(nome, args):
            chiamate.append((nome, args))

            class _E:
                ok = True
                output = {}
                error = None
            return _E()

        nomi = registry.names()
        if "system_status" not in nomi:
            pytest.skip(f"registry senza system_status: {sorted(nomi)[:5]}")

        vero = registry.invoke
        registry.invoke = finto
        try:
            await _instrada(motore, "system_status")
        finally:
            registry.invoke = vero
        assert chiamate == [("system_status", {})], chiamate


class TestIlCallbackNonPerdeIlCompito:
    """`asyncio` tiene i task per riferimento debole: uno non referenziato puo'
    essere raccolto dal GC a meta' dell'instradamento, e l'azione sparirebbe
    senza un errore — di nuovo il guasto muto."""

    async def test_il_compito_e_tenuto(self, motore) -> None:
        visti: list[dict] = []

        async def falso(msg):
            await asyncio.sleep(0)
            visti.append(msg)

        motore._ws.broadcast = falso
        motore._voce_su_azione("scene:welcome_home", {})
        assert motore._annunci, "il compito non e' referenziato da nessuno"
        for _ in range(5):
            await asyncio.sleep(0)
        assert visti and visti[0]["intento"] == "scene"
