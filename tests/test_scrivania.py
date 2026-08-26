"""La meta' lato core di §13 — la scrivania.

Tre cose che prima non esistevano e che i pannelli aspettavano:

  1. `core/tools/introspect.py` — chi produce i sorgenti e l'archivio
  2. `Engine.stato_pannelli()` — cio' che il core spinge a chi si collega,
     perche' il renderer non puo' CHIEDERE niente (§6.3)
  3. `Engine.esegui_t0()` — gli intenti di §13 che dalla Fase 3 non avevano
     nessuna strada verso l'interfaccia

Il pezzo che NON si verifica qui e' il microfono in mezzo: `voice.enabled` e'
falso, e la `VoicePipeline` non e' composta nell'engine. Dichiarato in
`docs/acceptance/SEZIONE-13.md`.
"""

from __future__ import annotations

import pytest

from core.engine import Engine
from core.llm.grammar import INTENTI_UI, Intent, parse, regole
from core.tools import registry
from core.tools.introspect import (
    MAX_FILE,
    RADICE,
    SALTA,
    SALTA_FILE,
    leggi_albero,
    leggi_note,
)


@pytest.fixture
def engine(short_paths) -> Engine:
    return Engine(short_paths)


class TestIntrospezione:
    def test_l_albero_e_quello_vero_di_questo_progetto(self) -> None:
        file = leggi_albero()
        percorsi = {f["path"] for f in file}
        assert {"CLAUDE.md", "core/engine.py", "ui/src/app.js"} <= percorsi
        # Dimensioni vere, non zeri: una nuvola di punti costruita su file di
        # dimensione zero avrebbe la forma sbagliata (§17.4).
        assert all(f["bytes"] >= 0 for f in file)
        assert sum(f["bytes"] for f in file) > 100_000

    def test_pota_cio_che_non_e_il_progetto(self) -> None:
        """`node_modules` ha decine di migliaia di file: senza la potatura la
        nuvola mostrerebbe la forma delle dipendenze, non del progetto."""
        percorsi = [f["path"] for f in leggi_albero()]
        for cartella in SALTA:
            assert not any(p.startswith(f"{cartella}/") or f"/{cartella}/" in p
                           for p in percorsi), cartella
        assert not any(p.endswith(tuple(SALTA_FILE)) for p in percorsi)

    def test_ha_un_tetto(self) -> None:
        """Un albero senza limite riempirebbe un messaggio del socket."""
        assert len(leggi_albero()) <= MAX_FILE

    def test_le_note_sono_i_documenti_veri(self) -> None:
        note = leggi_note()
        assert note, "nessun documento di accettazione: l'archivio sarebbe vuoto"
        assert {"file", "titolo", "corpo", "byte"} == set(note[0])
        assert all(n["file"].endswith(".md") for n in note)
        assert all(n["titolo"] and not n["titolo"].startswith("#") for n in note)

    def test_una_cartella_assente_non_e_un_errore(self, tmp_path) -> None:
        """E' lo stato di un'installazione senza documenti, e i pannelli hanno
        gia' il proprio stato vuoto per dirlo (invariante 23)."""
        assert leggi_note(tmp_path / "non-esiste") == []

    def test_nessuno_dei_due_tool_ha_un_parametro_path(self, engine: Engine) -> None:
        """E' la ragione per cui e' sicuro leggere fuori dalle radici
        consentite: non c'e' input che possa spostare la radice altrove.

        Stessa difesa strutturale di `timezones`. Una validazione si dimentica,
        un argomento che non esiste no.
        """
        for nome in ("source_tree", "archive_notes"):
            campi = registry.get(nome).args_schema.model_fields
            assert campi == {}, f"{nome} ha acquisito degli argomenti: {campi}"

    def test_nessuno_dei_due_scrive(self, engine: Engine) -> None:
        for nome in ("source_tree", "archive_notes"):
            t = registry.get(nome)
            assert t.side_effect is False and t.planner is None

    async def test_il_tool_avvolge_il_corpo_delle_note(self, engine: Engine) -> None:
        """INVARIANTE 5. Un `ToolResult` puo' finire nel contesto di un LLM: il
        corpo e' contenuto di un file, e li' dentro va marcato."""
        esito = await registry.invoke("archive_notes", {})
        assert esito.ok and esito.output["untrusted"] is True
        for n in esito.output["note"]:
            assert n["corpo"].startswith("<untrusted_source ")
            assert n["corpo"].endswith("</untrusted_source>")

    def test_la_radice_e_l_installazione(self) -> None:
        assert (RADICE / "core" / "engine.py").is_file()


class TestStatoIniziale:
    """Cio' che il core spinge a chi si collega.

    Non e' un vezzo: il renderer NON PUO' CHIEDERE. L'unica funzione che il
    preload espone in uscita risponde a una domanda gia' posta (§6.3), quindi
    o li manda il core o quei pannelli restano allo stato vuoto per sempre.
    """

    async def test_manda_i_quattro_topic_dei_pannelli(self, engine: Engine) -> None:
        topic = {m["topic"] for m in await engine.stato_pannelli()}
        # `fs.list` puo' mancare: la workspace potrebbe non esistere su questa
        # macchina, ed e' un fatto della macchina, non un guasto del codice.
        assert {"source.tree", "archive.notes", "geo.timezones"} <= topic

    async def test_l_archivio_per_il_pannello_e_in_chiaro(self, engine: Engine) -> None:
        """Il TOOL avvolge, il messaggio per il DOM no.

        Due lettori della stessa sorgente, non una catena che apre una busta:
        se il pannello ricevesse l'involucro, lo mostrerebbe come testo.
        """
        msg = next(m for m in await engine.stato_pannelli()
                   if m["topic"] == "archive.notes")
        assert msg["note"], "archivio vuoto"
        assert all("<untrusted_source" not in n["corpo"] for n in msg["note"])

    async def test_i_fusi_hanno_la_forma_che_il_globo_aspetta(self, engine: Engine) -> None:
        msg = next(m for m in await engine.stato_pannelli()
                   if m["topic"] == "geo.timezones")
        assert len(msg["zone"]) > 100
        assert set(msg["zone"][0]) == {"nome", "lat", "lon"}

    async def test_i_fusi_portano_l_istante_del_campione(self, engine: Engine) -> None:
        """`quando`, e in ISO-8601 — non un float di secondi.

        `panels/globe.js` fa `new Date(msg.quando)`. Un float di secondi epoch
        verrebbe letto come MILLISECONDI e il globo disegnerebbe il 1970: un'
        immagine sbagliata e **stabile**, che passerebbe una misura invece di
        essere bocciata. Qui si verifica che si parsi e che sia recente.
        """
        from datetime import datetime, timezone

        msg = next(m for m in await engine.stato_pannelli()
                   if m["topic"] == "geo.timezones")
        assert "quando" in msg, "il globo prenderebbe l'ora dal renderer"
        q = datetime.fromisoformat(msg["quando"])
        assert q.tzinfo is not None, "senza fuso, `new Date()` lo legge come locale"
        scarto = abs((datetime.now(timezone.utc) - q).total_seconds())
        assert scarto < 60, f"l'istante non e' quello del campione: {scarto:.0f} s fa"

    async def test_una_sorgente_rotta_non_porta_via_le_altre(
        self, engine: Engine, monkeypatch
    ) -> None:
        """Un disco lento su una cartella non deve togliere il globo."""
        monkeypatch.setattr("core.engine.leggi_albero",
                            lambda: (_ for _ in ()).throw(OSError("disco")))
        topic = {m["topic"] for m in await engine.stato_pannelli()}
        assert "source.tree" not in topic
        assert {"archive.notes", "geo.timezones"} <= topic

    async def test_la_workspace_passa_dall_allowlist(
        self, engine: Engine, monkeypatch
    ) -> None:
        """Non un secondo `iterdir()`: sarebbe una seconda strada verso il
        disco, e l'invariante 2 dice che esistono solo i tool registrati."""
        chiamate: list[tuple] = []
        vero = registry.invoke

        async def spia(nome, args):
            chiamate.append((nome, args))
            return await vero(nome, args)

        monkeypatch.setattr(registry, "invoke", spia)
        await engine.stato_pannelli()
        assert [n for n, _ in chiamate] == ["list_dir"]


class TestT0VersoLaScrivania:
    """§13 chiede che «apri il globo» apra il globo.

    La grammatica lo riconosceva dalla Fase 3 e il corpus lo verificava, ma
    `build_router` compariva soltanto nei test: l'intento non aveva nessuna
    strada verso l'interfaccia.
    """

    async def test_un_intento_di_interfaccia_finisce_sul_socket(
        self, engine: Engine
    ) -> None:
        inviati = _intercetta(engine)
        esito = await engine.esegui_t0(parse("apri il globo"))
        assert esito["ok"] and esito["intento"] == "open_panel"
        assert inviati == [{"topic": "ui.intent", "intento": "open_panel",
                            "args": {"panel": "globo"}}]

    async def test_gli_argomenti_viaggiano_con_l_intento(self, engine: Engine) -> None:
        """`open_panel` senza `{"panel": ...}` non e' un comando, e' una
        categoria — ed e' cio' che si perdeva in `_su_azione`."""
        inviati = _intercetta(engine)
        await engine.esegui_t0(parse("workspace tre"))
        assert inviati[0]["args"] == {"n": 3}

    async def test_un_intento_che_nomina_un_tool_lo_esegue(self, engine: Engine) -> None:
        esito = await engine.esegui_t0(parse("come sta la cpu"))
        assert esito["ok"] and esito["tool"] == "system_status"

    async def test_un_intento_che_non_e_ne_l_uno_ne_l_altro_si_rifiuta(
        self, engine: Engine
    ) -> None:
        """Fail-closed. `set_volume`, `mute`, `brief_me`, `needs_attention` e
        `doctor` sono nella grammatica e non sono tool: oggi non hanno una
        destinazione, e la cosa giusta e' dirlo, non inventarne una.

        E non solleva: siamo sul percorso della voce, e un'eccezione qui
        zittirebbe JARVIS.
        """
        esito = await engine.esegui_t0(Intent(tool="autodistruzione", args={}))
        assert esito["ok"] is False and "non e'" in esito["error"]

    def test_le_TRE_strade_sono_TRE_allowlist(self, engine: Engine) -> None:
        """Nessuna quarta via. Un intento passa se e' un'azione dichiarata
        della scrivania, OPPURE un tool registrato, OPPURE un intento del core;
        il resto e' rifiutato.

        ⚠️ La terza strada e' nata con «non parlarmene piu'» (§15 regola 5),
        che non e' ne' una disposizione di finestre ne' un tool: tocca lo stato
        del gate, che vive nel core. **Questo test l'ha scoperta da solo** —
        aggiungendo l'intento senza aggiornarlo, e' diventato rosso — ed e'
        esattamente il suo mestiere.
        """
        from core.llm.grammar import INTENTI_CORE

        senza_destinazione = {
            tool for _, tool in regole()
            if tool not in INTENTI_UI
            and tool not in INTENTI_CORE
            and tool not in set(registry.names())
        }
        # Il test non pretende che l'insieme sia vuoto — non lo e', e §13 non
        # e' il posto dove costruire `set_volume`. Pretende che sia NOTO: un
        # intento nuovo senza destinazione fa fallire qui, non in esercizio.
        # ⚠️ **Vuoto**, e questa e' la novita'. I cinque intenti che questo
        # test elencava come «noti e senza destinazione» — `set_volume`,
        # `mute`, `brief_me`, `needs_attention`, `doctor` — ne hanno una:
        # i primi due sono tool (`core/tools/audio.py`), gli altri tre sono
        # intenti del core. Il test resta perche' il suo mestiere non e'
        # elencarli: e' accorgersi del prossimo.
        assert senza_destinazione == set(), (
            f"intenti senza esecutore: {sorted(senza_destinazione)}. JARVIS "
            "riconoscerebbe la frase e non farebbe niente, che e' "
            "indistinguibile da «non mi ha sentito»."
        )

    async def test_silence_topic_HA_una_destinazione(self, engine: Engine) -> None:
        """E la terza strada non e' un elenco: esegue davvero."""
        esito = await engine.esegui_t0(Intent(tool="silence_topic",
                                              args={"topic": "clima"}))
        assert esito["intento"] == "silence_topic"
        # A news spente l'esito e' un rifiuto DETTO, non un intento caduto.
        assert "error" in esito or esito["ok"]


def _intercetta(engine: Engine) -> list[dict]:
    """Prende il posto del socket. Il broadcast vero aprirebbe una connessione
    che qui non serve: si guarda COSA sarebbe partito."""
    inviati: list[dict] = []

    async def falso(msg: dict) -> None:
        inviati.append(msg)

    engine._ws.broadcast = falso        # type: ignore[method-assign]
    return inviati


class TestLaScalaVieneDalleIMPOSTAZIONI:
    """§26.9 criterio 7, la metà che mancava: «l'effetto si vede senza
    riavviare».

    `ui.grid_px` esisteva nello schema dalla Fase 0 e **non lo leggeva
    nessuno**, mentre `tokens.css` dichiarava `--grid: 110px`. Due proprietari
    per la stessa misura, che coincidevano per caso — entrambi 110 — e che al
    primo cambio si sarebbero separati in silenzio: la pagina avrebbe scritto
    128 nel file, il core lo avrebbe riletto a caldo, e sullo schermo non
    sarebbe cambiato niente.
    """

    def _app_js(self) -> str:
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent / "ui" / "src" / "app.js"
                ).read_text(encoding="utf-8")

    def test_i_due_token_sono_guidati_dalle_impostazioni(self) -> None:
        s = self._app_js()
        assert 'SCALA = [["grid_px", "--grid"], ["gap_px", "--gap"]]' in s
        assert 'bus.su("state.snapshot", (m) => applicaScala(m?.settings?.ui))' in s, (
            "nessuno applica la scala: il valore arriva nello snapshot e "
            "muore lì"
        )

    def test_il_valore_arriva_NELLO_SNAPSHOT(self) -> None:
        """L'altro capo del filo: se il core smettesse di mandarlo, il
        renderer applicherebbe `undefined` per sempre e nessuno lo saprebbe."""
        from pathlib import Path

        engine = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
                  ).read_text(encoding="utf-8")
        assert '"grid_px": s.ui.grid_px' in engine
        assert '"gap_px"' in engine, (
            "`gap_px` non è nello snapshot: il renderer lo applicherebbe mai"
        )

    def test_un_valore_NON_valido_lascia_il_predefinito(self) -> None:
        """Un `NaNpx` su `--grid` spegnerebbe mezza interfaccia senza un
        errore da leggere. Assente non è zero."""
        s = self._app_js()
        i = s.index("function applicaScala")
        corpo = s[i:s.index("\n}", i)]
        assert "Number.isFinite" in corpo and "v <= 0" in corpo

    def test_tokens_css_resta_il_PREDEFINITO(self) -> None:
        """Non si riscrive `tokens.css`: è legato a §10.1 byte a byte, e una
        custom property esiste esattamente per essere sovrascritta su `:root`."""
        from pathlib import Path

        tok = (Path(__file__).resolve().parent.parent / "ui" / "src" / "style"
               / "tokens.css").read_text(encoding="utf-8")
        assert "--grid:110px" in tok.replace(" ", "")
        s = self._app_js()
        assert "documentElement.style.setProperty" in s
