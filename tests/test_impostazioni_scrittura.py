"""Scrivere `settings.toml` senza cancellarne il senso — SPEC §26.7.

## Perche' i commenti sono la meta' del file

`config/settings.toml` non contiene solo valori: contiene le ragioni. La riga
che accende la voce ha sopra

    # ⚠️ Con `true` il core apre il MICROFONO all'avvio e spawna un processo
    # `claude` persistente (§5.2). Parte spento di proposito: si accende qui.

Un salvataggio che li cancella lascia dietro un file di numeri senza memoria, e
la prossima persona che lo apre — fra sei mesi, e sara' lo stesso utente — non
sapra' piu' perche' `grid_px` valga 110. E' la ragione per cui §26.7 impone
`tomlkit` e non `tomllib` + un dump qualunque, ed e' il criterio 7 di §26.9:

> Cambiare la dimensione delle icone dalla pagina riscrive `settings.toml`
> **conservando i commenti**, e l'effetto si vede senza riavviare.

## E perche' si valida prima di scrivere

Un `settings.toml` che non carica non e' un fastidio: `load_settings` solleva e
**il core non parte piu'**. Un salvataggio sbagliato dall'interfaccia lascerebbe
un sistema che si ripara solo con un editor — cioe' esattamente la cosa che
questa pagina esiste per non richiedere.
"""

from __future__ import annotations

import pytest
import tomlkit

from core.settings import load_settings
from core.tools.impostazioni import (
    BLOCCATE,
    ImpostaArgs,
    chiavi_bloccate,
    chiavi_modificabili,
    imposta,
)


@pytest.fixture
def file_e_settings(short_paths):
    p = short_paths.config_dir() / "settings.toml"
    return p, load_settings(short_paths)


class TestICommentiSOPRAVVIVONO:
    def test_scrivere_non_cancella_i_commenti(self, file_e_settings) -> None:
        """Il criterio 7 di §26.9, alla lettera."""
        p, s = file_e_settings
        prima = p.read_text(encoding="utf-8")
        commenti_prima = [r for r in prima.splitlines() if r.lstrip().startswith("#")]
        assert len(commenti_prima) > 10, "il file di prova non ha commenti da salvare"

        imposta(p, "ui.grid_px", 128, corrente=s)

        dopo = p.read_text(encoding="utf-8")
        commenti_dopo = [r for r in dopo.splitlines() if r.lstrip().startswith("#")]
        assert commenti_dopo == commenti_prima, (
            "i commenti sono cambiati: il file ha perso le sue ragioni"
        )
        assert tomlkit.parse(dopo)["ui"]["grid_px"] == 128

    def test_cambia_SOLO_la_riga_toccata(self, file_e_settings) -> None:
        """Un salvataggio che riordina o riformatta il file rende illeggibile
        ogni diff futuro, e nasconde la modifica vera in mezzo al rumore."""
        p, s = file_e_settings
        prima = p.read_text(encoding="utf-8").splitlines()
        imposta(p, "ui.grid_px", 128, corrente=s)
        dopo = p.read_text(encoding="utf-8").splitlines()

        diverse = [(a, b) for a, b in zip(prima, dopo, strict=False) if a != b]
        assert len(prima) == len(dopo), "il numero di righe e' cambiato"
        assert len(diverse) == 1, f"righe cambiate: {diverse}"
        assert "grid_px" in diverse[0][1]


class TestNonSiScriveMaiUnFileCHE_NON_CARICA:
    def test_un_valore_invalido_e_RIFIUTATO(self, file_e_settings) -> None:
        p, s = file_e_settings
        with pytest.raises(ValueError, match="non e' valido"):
            imposta(p, "ui.grid_px", 0, corrente=s)     # Field(ge=1)

    def test_e_il_file_resta_INTATTO(self, file_e_settings) -> None:
        """La meta' che conta: rifiutare e poi aver gia' scritto sarebbe
        peggio che accettare."""
        p, s = file_e_settings
        prima = p.read_bytes()
        with pytest.raises(ValueError):
            imposta(p, "ui.grid_px", -5, corrente=s)
        assert p.read_bytes() == prima, "il file e' stato toccato lo stesso"

    def test_una_scena_iniziale_inesistente_e_rifiutata(self, file_e_settings) -> None:
        """Il validatore di `UISettings` esiste gia' e va rispettato anche da
        qui: un nome che non trova una scena si vedrebbe solo come una
        scrivania vuota al prossimo avvio."""
        p, s = file_e_settings
        with pytest.raises(ValueError):
            imposta(p, "ui.scena_iniziale", "non-esiste", corrente=s)

    def test_il_file_resta_CARICABILE_dopo_una_scrittura_buona(
            self, short_paths, file_e_settings) -> None:
        p, s = file_e_settings
        imposta(p, "ui.grid_px", 96, corrente=s)
        assert load_settings(short_paths).ui.grid_px == 96


class TestLeCinqueBLOCCATE:
    @pytest.mark.parametrize("chiave", sorted(BLOCCATE))
    def test_si_rifiutano_TUTTE(self, chiave, file_e_settings) -> None:
        p, s = file_e_settings
        with pytest.raises(ValueError, match="non si cambia dall'interfaccia"):
            imposta(p, chiave, False, corrente=s)

    def test_il_rifiuto_dice_DOVE_cambiarla(self, file_e_settings) -> None:
        """«Non si puo'» senza «ecco come» e' un vicolo cieco: §26.7 dice che
        la pagina deve mostrarle e dire dove si cambiano."""
        p, s = file_e_settings
        with pytest.raises(ValueError, match=r"settings\.toml.*editor"):
            imposta(p, "voice.enabled", False, corrente=s)

    def test_non_compaiono_fra_le_modificabili(self, file_e_settings) -> None:
        _, s = file_e_settings
        assert not (BLOCCATE & set(chiavi_modificabili(s)))

    def test_ma_si_MOSTRANO_col_loro_valore(self, file_e_settings) -> None:
        _, s = file_e_settings
        viste = chiavi_bloccate(s)
        assert set(viste) == BLOCCATE
        # Il valore mostrato e' quello VERO, non un segnaposto: la pagina le
        # espone per farle guardare, e una casella che dice il falso sarebbe
        # peggio di una casella assente.
        assert viste["voice.enabled"] == s.voice.enabled
        assert viste["fs.trash_only"] is True

    def test_fs_allowed_roots_NON_e_piu_bloccata(self, file_e_settings) -> None:
        """⚠️ **Decisione del 30 agosto 2026, e va vista qui.**

        Era la quarta delle bloccate perche' decide quale parte del disco JARVIS
        vede. Adesso si cambia dalla pagina, ma **un elemento per volta** e con
        la conferma di §6.2 che mostra il percorso **RISOLTO** — la difesa che
        si perde e' «dalla pagina non si puo' nemmeno chiedere», quella che
        resta e' l'invariante 3.

        Resta impossibile **sostituire** l'elenco in un colpo: il messaggio
        porta un elemento e un verbo, mai la lista.
        """
        from core.tools.impostazioni import chiavi_lista

        _, s = file_e_settings
        assert "fs.allowed_roots" not in BLOCCATE
        assert "fs.allowed_roots" in chiavi_lista(s)
        # E non fra le foglie: non e' uno scalare, e offrirla li' darebbe un
        # errore a meta' scrittura invece di un rifiuto.
        assert "fs.allowed_roots" not in chiavi_modificabili(s)


class TestLAllowlistVIENE_DALLO_SCHEMA:
    """Un elenco scritto a mano diverge dal modello alla prima aggiunta."""

    def test_nessun_segreto_e_offerto(self, file_e_settings) -> None:
        """`Secrets` porta `SecretStr`: farlo passare di qui scriverebbe una
        chiave API in chiaro nel file coi permessi larghi."""
        _, s = file_e_settings
        assert not [k for k in chiavi_modificabili(s) if k.startswith("secrets")]

    def test_il_ramo_e_escluso_PER_NOME_e_non_per_tipo(self) -> None:
        """⚠️ Il test qui sopra passa **anche togliendo `RAMI_ESCLUSI`**, e l'ho
        misurato: `SecretStr` non e' fra gli scalari, quindi oggi a proteggere
        e' il filtro di tipo e non l'esclusione. Un criterio vero per assenza
        del fenomeno non e' verde (§11.7 regola 4).

        Il giorno in cui una chiave diventasse una `str` semplice — un refuso,
        o una chiave nuova scritta in fretta — il filtro di tipo smetterebbe di
        proteggere **in silenzio**. Questo prova l'esclusione per quello che e':
        vale sul NOME del ramo, qualunque cosa contenga.
        """
        from pydantic import BaseModel

        class _Segreti(BaseModel):
            deepgram_api_key: str = "sk-in-chiaro"

        class _Finte(BaseModel):
            secrets: _Segreti = _Segreti()
            grid_px: int = 110

        offerte = chiavi_modificabili(_Finte())
        assert "grid_px" in offerte
        assert "secrets.deepgram_api_key" not in offerte, (
            "una chiave in chiaro sarebbe offerta come impostazione "
            "modificabile, e finirebbe in `settings.toml`"
        )

    def test_nessuna_struttura_e_offerta(self, file_e_settings) -> None:
        """Scene, frasi di wake e percorsi non sono scalari: offrirli
        produrrebbe un errore a meta' scrittura invece che un rifiuto."""
        _, s = file_e_settings
        offerte = chiavi_modificabili(s)
        assert "ui.scene" not in offerte
        assert "voice.wake.phrases" not in offerte
        assert "voice.wake.model" not in offerte     # e' un Path
        assert "fs.workspace" not in offerte         # idem

    def test_gli_INTERRUTTORI_restano_booleani(self, file_e_settings) -> None:
        """In Python `True` E' un `int`: senza l'ordine giusto nel controllo di
        tipo, un interruttore verrebbe offerto come numero."""
        _, s = file_e_settings
        assert chiavi_modificabili(s)["voice.fallback_on_error"] is True

    def test_una_chiave_inventata_e_rifiutata(self, file_e_settings) -> None:
        p, s = file_e_settings
        with pytest.raises(ValueError, match="non e' una chiave scalare"):
            imposta(p, "ui.colore_preferito", "rosso", corrente=s)


class TestIlValoreArrivaDallInterfaccia:
    """Dai campi di una pagina i numeri arrivano come stringhe."""

    def test_un_numero_scritto_come_stringa(self, file_e_settings) -> None:
        p, s = file_e_settings
        assert imposta(p, "ui.grid_px", "128", corrente=s) == 128
        assert tomlkit.parse(p.read_text(encoding="utf-8"))["ui"]["grid_px"] == 128

    def test_un_interruttore_scritto_come_stringa(self, file_e_settings) -> None:
        p, s = file_e_settings
        assert imposta(p, "voice.fallback_on_error", "false", corrente=s) is False

    def test_una_stringa_che_non_e_un_numero_viene_BOCCIATA(
            self, file_e_settings) -> None:
        """Non convertita a caso: rifiutata, e dal modello."""
        p, s = file_e_settings
        with pytest.raises(ValueError, match="non e' valido"):
            imposta(p, "ui.grid_px", "grande", corrente=s)

    def test_lo_schema_degli_argomenti_rifiuta_una_chiave_storta(self) -> None:
        from pydantic import ValidationError

        for storta in ("ui", "UI.grid_px", "ui..grid", "ui.grid px", "../etc"):
            with pytest.raises(ValidationError):
                ImpostaArgs(chiave=storta, valore=1)


class TestIlTOOL:
    """§26.7 regola 3: uno solo, e con la conferma."""

    def test_e_registrato_con_side_effect_e_planner(self, short_paths) -> None:
        from core.tools import registry
        from core.tools.impostazioni import register_settings_tool

        registry.clear()
        register_settings_tool(lambda: load_settings(short_paths),
                               short_paths.config_dir)
        t = registry.get("imposta_valore")
        assert t is not None and t.side_effect is True, (
            "senza `side_effect=True` scriverebbe la configurazione di un "
            "sistema che apre un microfono SENZA chiedere (invariante 3)"
        )
        assert t.planner is not None

    async def test_il_piano_mostra_il_percorso_RISOLTO(self, short_paths) -> None:
        from core.tools import registry
        from core.tools.impostazioni import register_settings_tool

        registry.clear()
        register_settings_tool(lambda: load_settings(short_paths),
                               short_paths.config_dir)
        t = registry.get("imposta_valore")
        piano = await t.planner(ImpostaArgs(chiave="ui.grid_px", valore=128))
        op = piano.operazioni[0]
        assert op.destinazione == short_paths.config_dir() / "settings.toml"
        assert op.destinazione.is_absolute()
        assert "110" in piano.riepilogo and "128" in piano.riepilogo, (
            f"il riepilogo non dice da cosa a cosa: {piano.riepilogo!r}"
        )

    async def test_un_errore_NON_propaga_ma_torna_come_esito(
            self, short_paths) -> None:
        """*Stile codice*: «Nessuna eccezione propaga all'LLM:
        `ToolResult(ok=False, error=...)`».

        ⚠️ **Passa da `invoke`, e non piu' da `planner` + `handler` a mano.**
        Dal 30 agosto il rifiuto di una chiave bloccata avviene nel PIANO, non
        nel handler: chiamare i due pezzi a mano provava una strada che la
        produzione non percorre. E la strada vera dice una cosa in piu', che il
        test adesso pinna — **non si chiede niente a nessuno**.

        Trovato dal vivo con Electron: chiedere una chiave che la pagina non
        offre apriva una finestra di conferma per un'operazione che sarebbe
        stata rifiutata dopo. E' il difetto che `core/tools/confirm.py` esiste
        per non avere.
        """
        from core.tools import registry
        from core.tools.impostazioni import register_settings_tool

        registry.clear()
        register_settings_tool(lambda: load_settings(short_paths),
                               short_paths.config_dir)
        chieste = []

        async def conferma(piano):
            chieste.append(piano)
            return "approvato"

        registry.set_confirm_hook(conferma)
        esito = await registry.invoke("imposta_valore",
                                      {"chiave": "voice.enabled", "valore": False})
        assert esito.ok is False and "interfaccia" in esito.error
        assert not chieste, (
            "una chiave bloccata non deve far nascere una conferma: si "
            "chiederebbe di approvare cio' che verra' rifiutato"
        )


class TestLaCatenaEATTACCATA:
    """Le giunzioni, che sono il punto in cui questo progetto si rompe.

    In una sola giornata: `_gradi()` componeva solo T1, il `Watcher` delle news
    non aveva chi lo azionasse, `PhraseWake.chiudi()` non esisteva, l'azione
    vocale andava su un topic che nessuno ascoltava, e le frasi nominavano una
    scena non dichiarata. Cinque volte lo stesso guasto: due pezzi scritti,
    provati, e mai congiunti.

    La pagina impostazioni ne attraversa **sei** — pannello, registro dei
    moduli, snapshot, preload, ponte IPC, allowlist in ingresso — e ognuna e'
    un posto in cui un clic puo' non arrivare da nessuna parte in silenzio.
    """

    def _sorgente(self, rel: str) -> str:
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent / rel).read_text(encoding="utf-8")

    def _voce_impostazioni(self) -> str:
        """La voce del registro, dal suo `id` a quello successivo.

        ⚠️ Non una finestra di N caratteri: la prima versione ne tagliava 600 e
        boccava perche' il commento della voce e' piu' lungo di cosi'. Un test
        appeso a un numero e' lo stesso difetto della riga 113 di `lettura.js`,
        fissata per numero e rotta da un import.
        """
        s = self._sorgente("ui/src/desk/moduli.js")
        dopo = s.split('id: "impostazioni"', 1)[1]
        fine = dopo.find('id: "')
        return dopo if fine < 0 else dopo[:fine]

    def test_il_pannello_non_e_piu_vuoto(self) -> None:
        s = self._sorgente("ui/src/panels/settings.js")
        assert len(s) > 1000, f"{len(s)} byte: era 0 dalla Fase 0"
        assert "export function crea" in s and "export const css" in s

    def test_e_registrato_fra_i_moduli(self) -> None:
        s = self._sorgente("ui/src/desk/moduli.js")
        assert 'from "../panels/settings.js"' in s
        assert 'id: "impostazioni"' in s
        assert "suRichiesta: true" in self._voce_impostazioni(), (
            "senza `suRichiesta` il pannello entra nella piastrellatura di una "
            "categoria che e' gia' piena, e nel dock degli otto moduli di §13"
        )

    def test_lo_snapshot_porta_le_due_liste(self) -> None:
        s = self._sorgente("core/engine.py")
        assert '"impostazioni": {' in s
        assert "chiavi_modificabili(s)" in s and "chiavi_bloccate(s)" in s

    def test_il_pannello_ascolta_ANCHE_l_esito(self) -> None:
        """Con solo `state.snapshot` un rifiuto lascerebbe a schermo un valore
        che sul disco non c'e' — il guasto muto, di nuovo."""
        blocco = self._voce_impostazioni()
        assert 'bus.su("state.snapshot"' in blocco
        assert 'bus.su("ui.impostazione"' in blocco

    def test_il_preload_espone_il_metodo(self) -> None:
        s = self._sorgente("app/preload.js")
        assert "impostaValore:" in s
        assert 'ipcRenderer.send("jarvis:impostazione"' in s

    def test_il_ponte_mette_LUI_il_topic(self) -> None:
        """La riga che impedisce al canale di diventare un «manda questo al
        core» generico: chi sta dall'altra parte sceglie QUALE impostazione,
        non a chi parlare."""
        s = self._sorgente("app/main.js")
        assert 'ipcMain.on("jarvis:impostazione"' in s
        assert 'topic: "ui.imposta"' in s

    def test_il_core_accetta_il_quarto_tipo(self) -> None:
        s = self._sorgente("core/ws_server.py")
        assert "class ImpostazioneMessage" in s
        assert 'Literal["ui.imposta"]' in s
        assert "ImpostazioneMessage.model_validate_json" in s, (
            "il tipo e' dichiarato e non provato in ingresso: un messaggio "
            "valido verrebbe scartato"
        )

    def test_il_valore_in_ingresso_e_un_UNIONE_STRETTA(self) -> None:
        """Un dizionario che arrivasse fin qui verrebbe scritto da tomlkit
        senza passare da nessuno schema di sezione: sarebbe un modo di
        riscrivere una struttura con un messaggio che dichiara uno scalare."""
        from pydantic import ValidationError

        from core.ws_server import ImpostazioneMessage

        ok = ImpostazioneMessage(topic="ui.imposta", chiave="ui.grid_px", valore=120)
        assert ok.valore == 120
        for cattivo in ({"a": 1}, [1, 2], None):
            with pytest.raises(ValidationError):
                ImpostazioneMessage(topic="ui.imposta", chiave="ui.grid_px",
                                    valore=cattivo)

    def test_il_topic_in_ingresso_e_FISSO(self) -> None:
        from pydantic import ValidationError

        from core.ws_server import ImpostazioneMessage

        with pytest.raises(ValidationError):
            ImpostazioneMessage(topic="ui.layout", chiave="ui.grid_px", valore=1)
