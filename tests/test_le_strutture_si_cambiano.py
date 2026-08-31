"""Le strutture dalla pagina — §26.7, il residuo dichiarato.

Il criterio ② della rev 1 diceva «**ogni** impostazione di `settings.toml`
modificabile dalla pagina». Era «ogni foglia scalare», e
`ui/src/panels/settings.js` lo dichiarava nel proprio commento: *«le STRUTTURE
— scene, frasi di wake, radici — non compaiono fra le modificabili:
`imposta_valore(chiave, valore)` sa scrivere una foglia, e fingere il contrario
darebbe un errore a meta' scrittura invece di un rifiuto»*.

## Un elemento per volta, e non e' una comodita': e' il confine

Tre strati vietavano una struttura, tutti e tre con la stessa ragione scritta.
`core/ws_server.py`:

> «Un dizionario o una lista che arrivassero fin qui verrebbero scritti in
> `settings.toml` da tomlkit **senza passare da nessuno schema di sezione**, e
> sarebbe una strada per riscrivere una struttura — le radici consentite, per
> dire — con un messaggio che dichiara di cambiare uno scalare.»

Quella frase **resta vera alla lettera**, e questo file lo verifica. Il canale
nuovo non porta mai l'elenco: porta un verbo e UN record, e il record passa da
**due** schemi prima del disco — il tipo dichiarato dell'elemento e `Settings`
intero.

## `fs.allowed_roots` esce dalle bloccate

⚠️ **Decisione del 30 agosto 2026.** Era la quarta delle sei di §26.7 regola 4
perche' decide quale parte del disco JARVIS vede. La condizione a cui e' uscita:
**la conferma di §6.2 mostra il percorso RISOLTO**, una riga sua. Chi approva
legge la cartella vera, non la stringa che ha digitato — `~/../..` e un symlink
si scrivono uguali e arrivano altrove.

La difesa che si perde e' «dalla pagina non si puo' nemmeno chiedere». Quella
che resta e' l'invariante 3, che e' la difesa che il progetto ha scelto ovunque
altro.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.settings import Settings, load_settings
from core.tools.impostazioni import (
    BLOCCATE,
    ImpostaArgs,
    chiavi_bloccate,
    chiavi_lista,
    chiavi_modificabili,
    imposta_elemento,
)
from core.ws_server import ElementoMessage

RADICE = Path(__file__).resolve().parent.parent


@pytest.fixture
def mondo(paths):
    """Il `settings.toml` VERO del repository, in una config temporanea."""
    shutil.copy(RADICE / "config" / "settings.toml",
                paths.config_dir() / "settings.toml")
    (paths.config_dir() / "settings.toml").chmod(0o600)
    s = load_settings(paths)
    return paths.config_dir() / "settings.toml", s, paths


def _commenti(p: Path) -> int:
    return sum(1 for r in p.read_text(encoding="utf-8").splitlines()
               if r.lstrip().startswith("#"))


# ── ① l'elenco viene dallo schema ────────────────────────────────────────────


class TestLeListeOfferte:
    def test_sono_DUE_e_il_filtro_e_derivato(self, mondo) -> None:
        """Una lista si offre solo se il suo elemento e' **piatto**: uno
        scalare, o un record i cui campi sono tutti scalari. Non un elenco
        scritto a mano — quello ci aveva gia' messo `protocolli`."""
        _, s, _ = mondo
        assert set(chiavi_lista(s)) == {"voice.wake.phrases", "fs.allowed_roots"}

    def test_le_liste_ANNIDATE_restano_fuori(self, mondo) -> None:
        """⚠️ **`protocolli` era dentro, ed era un difetto mio.**
        `ProtocolloSettings.args` e' un `dict`, e `ElementoMessage.elemento` e'
        un `dict[str, str]`: la pagina l'avrebbe offerto e il ponte l'avrebbe
        rifiutato a meta' — **esattamente il difetto che questa fetta chiude**,
        commesso mentre la si chiudeva. L'ha trovato un test, non una
        rilettura, e la cura non e' stata togliere quella riga: e' stato
        derivare il filtro, che toglie la classe intera di errore."""
        _, s, _ = mondo
        offerte = chiavi_lista(s)
        for annidata in ("ui.scene", "mcp.servers", "protocolli"):
            assert annidata not in offerte, annidata

    def test_una_lista_NON_e_una_foglia(self, mondo) -> None:
        """I due elenchi sono disgiunti: una lista offerta fra le foglie
        darebbe a `imposta()` un valore che non sa scrivere."""
        _, s, _ = mondo
        assert not (set(chiavi_lista(s)) & set(chiavi_modificabili(s)))

    def test_gli_elementi_hanno_una_forma_SOLA(self, mondo) -> None:
        """Un record diventa i suoi campi, uno scalare diventa
        `{"valore": ...}`. Due specie di lista, una forma: senza, ogni
        chiamante dovrebbe conoscerle."""
        _, s, _ = mondo
        liste = chiavi_lista(s)
        assert set(liste["voice.wake.phrases"][0]) == {"say", "action"}
        assert set(liste["fs.allowed_roots"][0]) == {"valore"}


class TestLeRadiciEsconoDalleBloccate:
    def test_non_e_piu_bloccata(self, mondo) -> None:
        _, s, _ = mondo
        assert "fs.allowed_roots" not in BLOCCATE
        assert "fs.allowed_roots" not in chiavi_bloccate(s)
        assert "fs.allowed_roots" in chiavi_lista(s)

    def test_le_altre_CINQUE_restano(self, mondo) -> None:
        """Erano sei. Le altre cinque decidono se un sottosistema **esiste** —
        un microfono che si apre, del codice che si esegue, una telecamera, dei
        programmi di terzi — o sono un fatto che si puo' solo guardare
        (`fs.trash_only`, `Literal[True]` per l'invariante 4)."""
        assert BLOCCATE == {"voice.enabled", "code.enabled", "vision.enabled",
                            "fs.trash_only", "mcp.enabled"}


# ── ② scrivere un elemento ───────────────────────────────────────────────────


class TestUnElementoPerVolta:
    def test_aggiunge_una_frase_di_wake(self, mondo) -> None:
        p, s, paths = mondo
        prima = len(s.voice.wake.phrases)
        imposta_elemento(p, "voice.wake.phrases", "aggiungi",
                         {"say": "buongiorno jarvis", "action": "scene:avvio"},
                         corrente=s)
        dopo = load_settings(paths)
        assert len(dopo.voice.wake.phrases) == prima + 1
        assert "buongiorno jarvis" in [f.say for f in dopo.voice.wake.phrases]

    def test_e_la_toglie(self, mondo) -> None:
        p, s, paths = mondo
        una = chiavi_lista(s)["voice.wake.phrases"][0]
        imposta_elemento(p, "voice.wake.phrases", "togli", una, corrente=s)
        dopo = load_settings(paths)
        assert una["say"] not in [f.say for f in dopo.voice.wake.phrases]

    def test_i_COMMENTI_del_toml_sopravvivono(self, mondo) -> None:
        """Il criterio della fetta lo chiede per nome. `settings.toml` e' un
        file che una persona legge e corregge a mano: perderne i commenti
        vorrebbe dire consegnare una configurazione muta."""
        p, s, _ = mondo
        prima = _commenti(p)
        assert prima > 50, "il file spedito ha molti commenti: il caso e' vero"
        imposta_elemento(p, "voice.wake.phrases", "aggiungi",
                         {"say": "ciao jarvis", "action": "listen"}, corrente=s)
        assert _commenti(p) == prima

    def test_una_radice_si_aggiunge(self, mondo, tmp_path) -> None:
        p, s, paths = mondo
        nuova = tmp_path / "una-cartella"
        nuova.mkdir()
        imposta_elemento(p, "fs.allowed_roots", "aggiungi",
                         {"valore": str(nuova)}, corrente=s)
        assert nuova in load_settings(paths).fs.allowed_roots

    @pytest.mark.parametrize("caso,chiave,operazione,elemento", [
        ("lista non offerta", "ui.scene", "aggiungi", {"valore": "x"}),
        ("operazione ignota", "voice.wake.phrases", "sostituisci",
         {"say": "x", "action": "listen"}),
        ("record incompleto", "voice.wake.phrases", "aggiungi", {"say": "x"}),
        ("scalare con campi", "fs.allowed_roots", "aggiungi", {"a": "b"}),
    ])
    def test_i_rifiuti(self, mondo, caso, chiave, operazione, elemento) -> None:
        p, s, _ = mondo
        with pytest.raises(ValueError):
            imposta_elemento(p, chiave, operazione, elemento, corrente=s)

    def test_un_doppione_si_rifiuta(self, mondo) -> None:
        p, s, _ = mondo
        una = chiavi_lista(s)["voice.wake.phrases"][0]
        with pytest.raises(ValueError, match="gia'"):
            imposta_elemento(p, "voice.wake.phrases", "aggiungi", una, corrente=s)

    def test_togliere_cio_che_non_c_e_si_rifiuta(self, mondo) -> None:
        p, s, _ = mondo
        with pytest.raises(ValueError, match="non contiene"):
            imposta_elemento(p, "fs.allowed_roots", "togli",
                             {"valore": "/mai-esistito"}, corrente=s)

    def test_un_rifiuto_non_TOCCA_il_file(self, mondo) -> None:
        """La validazione sta prima della scrittura, come in `imposta()`: un
        `settings.toml` che non carica non e' un fastidio, e' un core che non
        parte piu'."""
        p, s, _ = mondo
        prima = p.read_text(encoding="utf-8")
        with pytest.raises(ValueError):
            imposta_elemento(p, "voice.wake.phrases", "aggiungi", {"say": "x"},
                             corrente=s)
        assert p.read_text(encoding="utf-8") == prima

    def test_il_RECORD_e_validato_dal_suo_schema(self, mondo) -> None:
        """⚠️ **Questo test e' nato da un sabotaggio che non produceva rosso.**

        Togliendo `tipo.model_validate(elemento)`, un record incompleto passava
        di li' e veniva fermato **piu' avanti**, dalla validazione di `Settings`
        intero: il test dei rifiuti restava verde, e la validazione del record
        risultava provata senza esserlo.

        La differenza che resta e' il MESSAGGIO, ed e' la ragione per cui la
        validazione del record esiste: «l'elemento non e' un `WakePhrase`
        valido: action Field required» dice a chi legge quale campo manca; la
        validazione di `Settings` direbbe che una lista in fondo al file non e'
        valida. Un rifiuto che non dice dove guardare e' meta' rifiuto.
        """
        p, s, _ = mondo
        with pytest.raises(ValueError, match="WakePhrase"):
            imposta_elemento(p, "voice.wake.phrases", "aggiungi", {"say": "x"},
                             corrente=s)

    def test_NON_si_puo_togliere_l_ultima_radice(self, mondo, paths) -> None:
        """⚠️ **Anche questo viene da un sabotaggio muto.** Saltando la
        validazione di `Settings` intero, nessun test diventava rosso: il
        controllo del record copriva tutti i casi che avevo scritto.

        Questo e' il caso che solo la validazione del FILE puo' prendere:
        `allowed_roots` ha `min_length=1`, quindi svuotarlo passa il controllo
        dell'elemento — che guarda una stringa — e rompe lo schema. Un
        `settings.toml` senza radici non e' un fastidio: e' un core che non
        parte piu'.
        """
        p, _, _ = mondo
        s = load_settings(paths)
        for radice in list(s.fs.allowed_roots)[:-1]:
            imposta_elemento(p, "fs.allowed_roots", "togli",
                             {"valore": str(radice)}, corrente=load_settings(paths))
        rimasta = load_settings(paths).fs.allowed_roots
        assert len(rimasta) == 1
        with pytest.raises(ValueError, match="non e' valido dopo la modifica"):
            imposta_elemento(p, "fs.allowed_roots", "togli",
                             {"valore": str(rimasta[0])},
                             corrente=load_settings(paths))
        assert len(load_settings(paths).fs.allowed_roots) == 1

    def test_il_file_resta_VALIDO_dopo_ogni_scrittura(self, mondo, paths) -> None:
        """Si valida `Settings` INTERO prima di toccare il disco: e' cio' che
        risponde alla frase di `ws_server` — niente raggiunge tomlkit senza
        essere passato da uno schema di sezione."""
        p, s, _ = mondo
        imposta_elemento(p, "voice.wake.phrases", "aggiungi",
                         {"say": "jarvis buonasera", "action": "scene:avvio"},
                         corrente=s)
        assert Settings.model_validate(load_settings(paths).model_dump())

    def test_un_AZIONE_inventata_si_rifiuta(self, mondo) -> None:
        """`WakePhrase.action` non e' un campo libero per lo schema, ma la
        scena che nomina puo' non esistere: e' il caso che
        `LE-FRASI-PUNTANO-A-UNA-SCENA-CHE-ESISTE.md` sorveglia. Qui si pinna
        che almeno il RECORD sia valido — la scena la controlla chi la applica.
        """
        p, s, _ = mondo
        with pytest.raises(ValueError):
            imposta_elemento(p, "voice.wake.phrases", "aggiungi",
                             {"say": "", "action": "listen"}, corrente=s)


# ── ③ il confine: mai la lista intera ────────────────────────────────────────


class TestNessunoPuoSostituireUnaStruttura:
    def test_il_messaggio_porta_un_verbo_e_UN_record(self) -> None:
        m = ElementoMessage.model_validate({
            "topic": "ui.elemento", "chiave": "voice.wake.phrases",
            "operazione": "aggiungi", "elemento": {"say": "x", "action": "listen"}})
        assert set(ElementoMessage.model_fields) == {
            "topic", "chiave", "operazione", "elemento"}
        assert isinstance(m.elemento, dict), "un record, non un elenco"

    @pytest.mark.parametrize("cattivo", [
        {"topic": "ui.elemento", "chiave": "x", "operazione": "aggiungi",
         "elemento": {}},                                     # chiave storta
        {"topic": "ui.elemento", "chiave": "a.b", "operazione": "sostituisci",
         "elemento": {}},                                     # verbo inventato
        {"topic": "ui.elemento", "chiave": "a.b", "operazione": "aggiungi",
         "elemento": {"k": "x" * 600}},                       # valore lungo
        {"topic": "ui.elemento", "chiave": "a.b", "operazione": "aggiungi",
         "elemento": {f"k{i}": "v" for i in range(9)}},       # troppi campi
        {"topic": "ui.elemento", "chiave": "a.b", "operazione": "aggiungi",
         "elemento": {"k": "v"}, "extra": 1},                 # campo in piu'
    ])
    def test_lo_schema_e_stretto(self, cattivo) -> None:
        with pytest.raises(ValidationError):
            ElementoMessage.model_validate(cattivo)

    def test_il_canale_SCALARE_non_e_stato_allargato(self) -> None:
        """⚠️ La frase di `ws_server` resta vera perche' quel canale **non
        cambia**: `impostaValore` continua a non poter portare un array."""
        preload = (RADICE / "app" / "preload.js").read_text(encoding="utf-8")
        pezzo = preload.split("impostaValore:", 1)[1].split("impostaElemento:")[0]
        assert "Array" not in pezzo and "map(" not in pezzo

    def test_il_ponte_copia_i_campi_UNO_PER_UNO(self) -> None:
        """La terza copia dello stesso record — renderer, preload, main — e'
        la fragilita' che il 30 agosto ha fatto cadere `nascosto`. Qui i campi
        sono generici (`Object.entries`), quindi non c'e' un elenco da tenere
        allineato: e' l'unico modo di non ripetere quell'errore."""
        for f in ("app/preload.js", "app/main.js"):
            s = (RADICE / f).read_text(encoding="utf-8")
            pezzo = s.split("elemento:", 1)[1][:400]
            assert "slice(0, 8)" in pezzo, f"{f}: manca il tetto sui campi"
            assert "slice(0, 512)" in pezzo, f"{f}: manca il tetto sui valori"


class TestUnSoloToolDueForme:
    """§26.7 regola 3: **un solo tool**, e con la conferma."""

    def test_la_foglia(self) -> None:
        a = ImpostaArgs(chiave="ui.target_fps", valore=60)
        assert a.operazione is None and a.elemento is None

    def test_la_lista(self) -> None:
        a = ImpostaArgs(chiave="voice.wake.phrases", operazione="aggiungi",
                        elemento={"say": "x", "action": "listen"})
        assert a.valore is None

    @pytest.mark.parametrize("kw", [
        {"valore": 1, "operazione": "aggiungi", "elemento": {"a": "b"}},
        {"operazione": "aggiungi"},
        {"elemento": {"a": "b"}},
        {},
    ])
    def test_una_forma_sola_alla_volta(self, kw) -> None:
        with pytest.raises(ValidationError):
            ImpostaArgs(chiave="a.b", **kw)


# ── ④ il criterio della fetta ────────────────────────────────────────────────


class TestUnaFraseNuovaSiRiconosceACALDO:
    """«Aggiungere una frase di wake dalla pagina la fa riconoscere **a
    caldo**, senza riavviare il core, e i commenti del TOML sopravvivono.»

    Il ricarico a caldo esisteva gia' — `SettingsStore.subscribe` →
    `Engine._ricarica_frasi` → `PhraseWake.set_frasi`, chiuso il 25 agosto — e
    quello che mancava era la **strada di scrittura**. Qui si prova la
    giunzione: si scrive dalla pagina, e chi ascolta il file lo sa.
    """

    def test_chi_ascolta_il_file_riceve_la_frase_nuova(self, mondo) -> None:
        from core.settings import SettingsStore

        p, s, paths = mondo
        store = SettingsStore(paths)
        viste: list = []
        store.subscribe(lambda nuove: viste.append(nuove))

        imposta_elemento(p, "voice.wake.phrases", "aggiungi",
                         {"say": "jarvis buongiorno", "action": "scene:avvio"},
                         corrente=store.current)
        # `reload()` e' cio' che il thread di watchdog chiama quando il file
        # cambia: qui lo si chiama a mano perche' il test non aspetta l'inotify.
        store.reload()

        assert viste, "nessun ascoltatore e' stato avvisato"
        # `subscribe` consegna le `Settings` INTERE, non le frasi: e' il
        # motore a estrarne cio' che gli serve (`_ricarica_frasi`).
        assert "jarvis buongiorno" in [f.say for f in viste[-1].voice.wake.phrases]
        assert "jarvis buongiorno" in [f.say for f in store.current.voice.wake.phrases]

    def test_e_il_core_NON_e_stato_riavviato(self, mondo) -> None:
        """Lo stesso `SettingsStore` attraversa la scrittura: nessun oggetto
        nuovo, nessun processo nuovo. E' cio' che «a caldo» significa."""
        from core.settings import SettingsStore

        p, _, paths = mondo
        store = SettingsStore(paths)
        prima = id(store)
        imposta_elemento(p, "fs.allowed_roots", "togli",
                         {"valore": str(store.current.fs.allowed_roots[-1])},
                         corrente=store.current)
        store.reload()
        assert id(store) == prima
        assert len(store.current.fs.allowed_roots) == 2

    def test_i_commenti_sopravvivono_al_giro_intero(self, mondo) -> None:
        p, s, _ = mondo
        prima = _commenti(p)
        for i in range(3):
            imposta_elemento(p, "voice.wake.phrases", "aggiungi",
                             {"say": f"prova {i}", "action": "listen"},
                             corrente=load_settings(mondo[2]))
        assert _commenti(p) == prima, "tre scritture, zero commenti persi"


# ── ⑤ la conferma mostra il percorso RISOLTO ─────────────────────────────────


class TestLaConfermaMostraLaRadiceRISOLTA:
    """La condizione a cui `fs.allowed_roots` e' uscita dalle bloccate."""

    async def _piano(self, paths, elemento, operazione="aggiungi"):
        from core.settings import SettingsStore
        from core.tools import registry as R
        from core.tools.impostazioni import register_settings_tool

        store = SettingsStore(paths)
        register_settings_tool(lambda: store.current, paths.config_dir)
        return await R.pianifica("imposta_valore", {
            "chiave": "fs.allowed_roots", "operazione": operazione,
            "elemento": elemento})

    async def test_il_piano_porta_la_cartella_VERA(self, mondo, tmp_path) -> None:
        _, _, paths = mondo
        vera = tmp_path / "cartella-vera"
        vera.mkdir()
        storto = tmp_path / "altrove" / ".." / "cartella-vera"
        piano = await self._piano(paths, {"valore": str(storto)})

        perimetro = [o for o in piano.operazioni if o.tipo == "perimetro"]
        assert perimetro, "manca la riga che mostra la radice"
        assert perimetro[0].destinazione == vera.resolve(), (
            "chi approva deve leggere la cartella VERA: `~/../..` e un symlink "
            "si scrivono uguali e arrivano altrove"
        )
        assert "leggere e scrivere" in perimetro[0].dettaglio

    async def test_e_lo_dice_anche_quando_si_TOGLIE(self, mondo) -> None:
        """⚠️ Si toglie una radice che c'e' DAVVERO: dal 30 agosto il piano
        rifiuta senza aprire la conferma cio' che non e' in lista, e questo
        test chiedeva di togliere una cartella qualunque — verde per il motivo
        sbagliato finche' quel controllo non e' esistito."""
        _, s, paths = mondo
        vera = s.fs.allowed_roots[-1]
        piano = await self._piano(paths, {"valore": str(vera)}, "togli")
        perimetro = [o for o in piano.operazioni if o.tipo == "perimetro"]
        assert perimetro and "non vedra' piu'" in perimetro[0].dettaglio
        assert perimetro[0].destinazione == vera.resolve()

    async def test_una_frase_di_wake_NON_ha_quella_riga(self, mondo) -> None:
        """La riga del perimetro e' per le radici: metterla ovunque la
        renderebbe rumore, e il rumore si ignora."""
        from core.settings import SettingsStore
        from core.tools import registry as R
        from core.tools.impostazioni import register_settings_tool

        _, _, paths = mondo
        store = SettingsStore(paths)
        register_settings_tool(lambda: store.current, paths.config_dir)
        piano = await R.pianifica("imposta_valore", {
            "chiave": "voice.wake.phrases", "operazione": "aggiungi",
            "elemento": {"say": "x", "action": "listen"}})
        assert not [o for o in piano.operazioni if o.tipo == "perimetro"]
        assert len(piano.operazioni) == 1


class TestNonSiChiedeCioCheVerraRIFIUTATO:
    """⚠️ **Trovato dal vivo con Electron**, non da un test.

    Chiedere di aggiungere a `ui.scene` — che la pagina non offre — apriva una
    **finestra di conferma**, e solo dopo l'approvazione il handler rifiutava.
    I test qui sopra non lo vedevano: guardavano l'esito di `invoke`, che era
    gia' `ok=False`, e non se qualcuno fosse stato disturbato per arrivarci.

    E' il difetto che `core/tools/confirm.py` esiste per non avere: «il Signore
    agiva su una credenza falsa a proposito di un'operazione distruttiva».
    """

    async def _con_spia(self, paths):
        from core.settings import SettingsStore
        from core.tools import registry as R
        from core.tools.impostazioni import register_settings_tool

        store = SettingsStore(paths)
        register_settings_tool(lambda: store.current, paths.config_dir)
        chieste: list = []

        async def conferma(piano):
            chieste.append(piano)
            return "approvato"

        R.set_confirm_hook(conferma)
        return R, chieste

    async def test_una_lista_non_offerta_non_apre_NIENTE(self, mondo) -> None:
        _, _, paths = mondo
        R, chieste = await self._con_spia(paths)
        esito = await R.invoke("imposta_valore", {
            "chiave": "ui.scene", "operazione": "aggiungi",
            "elemento": {"valore": "x"}})
        assert esito.ok is False and "non e' una lista modificabile" in esito.error
        assert not chieste, "si e' aperta una conferma per un rifiuto"

    async def test_e_nemmeno_una_chiave_BLOCCATA(self, mondo) -> None:
        _, _, paths = mondo
        R, chieste = await self._con_spia(paths)
        esito = await R.invoke("imposta_valore",
                               {"chiave": "voice.enabled", "valore": True})
        assert esito.ok is False and not chieste

    async def test_ma_una_richiesta_VALIDA_la_apre(self, mondo) -> None:
        """La guardia nuova non deve aver spento la conferma: quella e'
        l'invariante 3, e vale per ogni scrittura."""
        _, _, paths = mondo
        R, chieste = await self._con_spia(paths)
        esito = await R.invoke("imposta_valore", {
            "chiave": "voice.wake.phrases", "operazione": "aggiungi",
            "elemento": {"say": "jarvis buonasera", "action": "listen"}})
        assert esito.ok, esito.error
        assert len(chieste) == 1, "una scrittura senza conferma non deve esistere"


class TestSiScriveCioCheSiEApprovato:
    """⚠️ **Trovato dal vivo con Electron.**

    Chiedendo `~/Documenti/../Scaricati`, la conferma mostrava
    `/home/…/Scaricati` — il piano risolve, §26.7 lo esige — e sul disco
    finiva la **stringa grezza**. Due difetti in uno: cio' che si approva non
    era cio' che si scriveva, ed e' la proprieta' che §6.2 tiene congelando il
    piano; e il doppione non si vedeva, perche' la forma grezza e' una stringa
    diversa da quella gia' in lista.
    """

    def test_un_percorso_storto_si_scrive_RISOLTO(self, mondo, tmp_path) -> None:
        p, s, paths = mondo
        vera = tmp_path / "vera"
        vera.mkdir()
        (tmp_path / "altrove").mkdir()
        storto = tmp_path / "altrove" / ".." / "vera"

        imposta_elemento(p, "fs.allowed_roots", "aggiungi",
                         {"valore": str(storto)}, corrente=s)
        radici = [str(x) for x in load_settings(paths).fs.allowed_roots]
        assert str(vera.resolve()) in radici
        assert str(storto) not in radici, "sul disco e' finita la forma grezza"

    def test_e_il_DOPPIONE_si_vede(self, mondo) -> None:
        """Due modi di scrivere la stessa cartella sono la stessa radice."""
        p, s, paths = mondo
        gia = load_settings(paths).fs.allowed_roots[-1]
        storto = f"{gia.parent}/../{gia.parent.name}/{gia.name}"
        with pytest.raises(ValueError, match="gia'"):
            imposta_elemento(p, "fs.allowed_roots", "aggiungi",
                             {"valore": storto}, corrente=s)

    def test_il_PIANO_e_il_FILE_dicono_la_stessa_cosa(self, mondo, tmp_path) -> None:
        """La riga della conferma e la riga del file devono combaciare: e'
        l'unica prova che «si esegue il piano, non gli argomenti» valga anche
        qui."""
        from core.tools.impostazioni import _normalizza_scalare

        _, s, _ = mondo
        (tmp_path / "x").mkdir()
        storto = str(tmp_path / "x" / ".." / "x")
        scritto = _normalizza_scalare(s, "fs.allowed_roots", storto)
        risolto = str(Path(storto).expanduser().resolve())
        assert scritto == risolto

    def test_una_lista_NON_di_percorsi_non_si_tocca(self, mondo) -> None:
        """La normalizzazione vale per i percorsi. Una frase di wake che
        contenesse un `..` e' testo, e resta com'e'."""
        from core.tools.impostazioni import _normalizza_scalare

        _, s, _ = mondo
        assert _normalizza_scalare(s, "voice.wake.phrases", "a/../b") == "a/../b"


class TestIlFileNonSiRISCRIVE_INTORNO:
    """⚠️ **Trovato dal vivo con Electron.**

    Aggiungere una radice riscriveva l'intero elenco nella forma **espansa**:
    `~/Documenti` diventava `/home/<qualcuno>/Documenti`. Il file smetteva di
    essere portabile — copiarlo su un'altra macchina o per un altro utente lo
    rompeva — e nessuno l'aveva chiesto.

    E' della stessa famiglia del perdere i commenti, che il criterio di questa
    fetta vieta per nome: `settings.toml` e' un file che una persona legge e
    corregge a mano, e cambiargli righe che non c'entrano e' un danno anche
    quando il TOML resta valido.
    """

    def test_le_altre_radici_restano_COME_SONO_SCRITTE(self, mondo, tmp_path
                                                       ) -> None:
        p, s, _ = mondo
        assert "~/Documenti" in p.read_text(encoding="utf-8"), "il caso e' vero"
        nuova = tmp_path / "nuova"
        nuova.mkdir()
        imposta_elemento(p, "fs.allowed_roots", "aggiungi",
                         {"valore": str(nuova)}, corrente=s)
        testo = p.read_text(encoding="utf-8")
        assert "~/Documenti" in testo, "una riga che non c'entrava e' cambiata"
        assert str(nuova.resolve()) in testo, "la nuova c'e', ed e' risolta"

    def test_e_si_toglie_quella_giusta_anche_se_scritta_con_la_tilde(
        self, mondo, paths
    ) -> None:
        """Il confronto e' per forma **espansa**: la pagina mostra
        `/home/…/Documenti`, il file dice `~/Documenti`, ed e' la stessa
        cartella."""
        p, s, _ = mondo
        espansa = str(s.fs.allowed_roots[1])
        assert espansa != "~/Documenti"
        imposta_elemento(p, "fs.allowed_roots", "togli", {"valore": espansa},
                         corrente=s)
        # ⚠️ Si guarda la RIGA di `allowed_roots`, non tutto il file:
        # `~/Documenti` compare anche negli `args` di un protocollo, che e'
        # un'altra impostazione e non c'entra. La prima stesura di questo test
        # cercava in tutto il testo ed era rossa per la riga sbagliata.
        riga = next(r for r in p.read_text(encoding="utf-8").splitlines()
                    if r.startswith("allowed_roots"))
        assert "~/Documenti" not in riga
        assert "~/.local/share/jarvis-os/workspace" in riga, (
            "le altre due sono rimaste come erano scritte"
        )
        assert "~/Scaricati" in riga


# ── ⑧ il ricarico a caldo, con l'inotify VERO ────────────────────────────────


class TestIlRicaricoPassaDavveroDallInotify:
    """⚠️ Il residuo ② di §26.7, che nascondeva un difetto.

    Diceva: «il ricarico a caldo e' provato con `store.reload()` a mano, non
    con l'inotify vero». Provando il **microfono vero** il 31 agosto 2026 si e'
    visto perche' quel residuo non era una pignoleria: attraverso l'inotify il
    ricarico **non funzionava affatto**, e per una ragione che solo la strada
    vera espone.

    `imposta_valore` LEGGE il TOML (`_documento`) prima di riscriverlo. inotify
    manda `IN_OPEN` anche a chi legge, l'antirimbalzo era sul fronte di salita,
    e la lettura si mangiava la finestra: la scrittura che arrivava un
    millisecondo dopo veniva scartata. Cambiare una frase di wake dalla pagina
    non la faceva arrivare al riconoscitore, **mai**.

    Chiamare `reload()` a mano saltava esattamente il pezzo rotto. Il perche'
    del difetto sta in `core/settings.py`; qui si prova che la strada intera —
    tool, conferma, disco, inotify, iscritto — arriva in fondo.
    """

    async def test_il_TOOL_scrive_e_l_iscritto_lo_viene_a_sapere(
            self, mondo) -> None:
        import asyncio
        import threading

        from core.settings import SettingsStore
        from core.tools import registry as R
        from core.tools.impostazioni import register_settings_tool

        _, _, paths = mondo
        # Il valore di esercizio: con un antirimbalzo da un centesimo la
        # lettura e la scrittura possono cadere in finestre diverse e il
        # difetto sparirebbe a caso.
        store = SettingsStore(paths, debounce_s=0.2)
        register_settings_tool(lambda: store.current, paths.config_dir)
        R.set_confirm_hook(lambda piano: asyncio.sleep(0, result="approvato"))

        visto = threading.Event()
        frasi: list[list[str]] = []
        store.subscribe(lambda s: (frasi.append([p.say for p in s.voice.wake.phrases]),
                                   visto.set()))
        with store:
            # `Observer.start()` ritorna prima che il watch sia attivo.
            await asyncio.sleep(0.5)
            esito = await R.invoke("imposta_valore", {
                "chiave": "voice.wake.phrases", "operazione": "aggiungi",
                "elemento": {"say": "accendi la scrivania",
                             "action": "scene:avvio"}})
            assert esito.ok, esito.error
            arrivato = await asyncio.get_running_loop().run_in_executor(
                None, visto.wait, 5.0)

        assert arrivato, (
            "il tool ha scritto e nessuno se n'e' accorto: e' il difetto del "
            "31 agosto, dove la lettura di `_documento` mangiava l'evento"
        )
        assert "accendi la scrivania" in frasi[-1]
        assert "accendi la scrivania" in [
            p.say for p in store.current.voice.wake.phrases]
