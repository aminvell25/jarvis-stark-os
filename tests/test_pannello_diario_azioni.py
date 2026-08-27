"""La colonna delle azioni sapeva rendere una sola riga su tre.

⚠️ **Questo file e' stato scritto due volte, e la prima l'ho persa io.**

Lo scrisse un agente della flotta il 27 agosto insieme al pannello. Mettendo da
parte i tre file — che si chiamano **tutti** `diario.js` — la copia in una sola
cartella li ha sovrascritti a vicenda, e del pannello non e' rimasto niente. I
test sono sopravvissuti, e sono serviti da specifica per riscriverlo: e' l'unico
motivo per cui la perdita e' costata un'ora invece di una giornata.

Il codice che verificavano — `ui/src/panels/diario.js`, la fixture e il mount —
e' stato scritto da un agente della flotta il 27 agosto e **l'ho distrutto io**
mettendolo da parte: i tre file si chiamano tutti `diario.js`, la mia copia in
una sola cartella li ha sovrascritti a vicenda, e ne e' sopravvissuto uno solo.
I tre file sono stati riportati a HEAD.

Il file resta perche' e' la **specifica** del lavoro da rifare, e perche' un
test saltato si vede a ogni giro mentre un documento non si legge. Chi lo
riprende deve anche eseguire il ciclo §11.7 e la checklist §11.8, che
quell'agente aveva dichiarato NON ESEGUITI: la verifica visiva non era
disponibile mentre sei agenti lavoravano in parallelo.


## Che cosa e' successo

Dal 27 agosto 2026 il topic `agent.diario` porta, nel flusso `azione`, tre
forme diverse. Il pannello ne conosceva una.

    intento   `esegui_t0` — un comando riconosciuto, con la sua destinazione
    delega    `_annota_instradamento` — T0 non ha morso, la frase e' andata a
              T1. `ok` VERO, `errore` nullo: e' il funzionamento normale
    caduta    lo stesso punto, ma senza T1: `ok` falso, `errore` t1_assente

E accanto a queste, il resoconto al risveglio (§5.5): `da="risveglio"`,
`strada="diario"`, un `testo` lungo una frase e un conto di `iniziative`.

`atto()` scriveva `(msg.intento ?? "?")`. Le due righe con intento nullo —
cioe' la delega e la caduta, che sono l'una il funzionamento e l'altra il
guasto — finivano **nella stessa cella con lo stesso punto interrogativo**, e
il `testo` che le distingue non veniva reso affatto. Il campo `da` non
compariva: un resoconto che JARVIS ha deciso da solo si leggeva come un
comando detto a voce.

## Le due meta' di questo file

**Il comportamento** lo prova `TestLaFormaDiUnaRiga`, eseguendo le funzioni
vere con `node --input-type=module` — lo stesso ponte di
`tests/test_orologio.py`. `formaAtto` ed `etichettaAtto` stanno fuori da
`crea()` proprio per questo: sono la parte giudicabile senza un DOM, e un test
che le interroga vale piu' di uno che ne legge il sorgente.

**Il resto** — che gli elementi esistano nel DOM, che i colori vengano dai
token, che una riga fallita si veda — resta un controllo sul SORGENTE, perche'
senza un DOM non c'e' modo di costruire l'elemento. E' un limite dichiarato:
questi test vedono che la regola c'e', non che si vede sullo schermo.

⚠️ **La verifica visiva §11.7 di questo giro NON e' stata eseguita** (la
galleria non era avviabile: porta occupata, agenti in parallelo). Nessuna
asserzione qui la sostituisce.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
PANNELLO = RADICE / "ui" / "src" / "panels" / "diario.js"
FIXTURE = RADICE / "ui" / "src" / "gallery" / "fixtures" / "diario.js"
MONTA = RADICE / "ui" / "src" / "gallery" / "mounts" / "diario.js"
TOKENS = RADICE / "ui" / "src" / "style" / "tokens.css"

#: Le righe VERE prese dal disco il 27 agosto 2026, verbatim.
#: Sono qui e non importate dal fixture di proposito: se qualcuno cambiasse il
#: fixture, questi test continuerebbero a misurare cio' che il core produce
#: davvero, che e' la domanda a cui il pannello deve rispondere.
RIGHE_VERE = [
    {"flusso": "azione", "intento": "open_panel", "args": {"panel": "telemetria"},
     "ok": True, "da": "voce", "strada": "ui", "errore": None},
    {"flusso": "azione", "intento": None, "args": None, "ok": True, "da": "voce",
     "strada": "t1", "testo": "il panetto della geometria.",
     "quasi_comando": None, "errore": None},
    {"flusso": "azione", "intento": "resoconto_al_risveglio", "args": None,
     "ok": True, "da": "risveglio", "strada": "diario",
     "testo": "Mentre non c'era, Signore: ho messo in ordine gli appunti di 1 sessione.",
     "iniziative": 1, "errore": None},
]


def _sorgente() -> str:
    return PANNELLO.read_text(encoding="utf-8")


def _css() -> str:
    """Il solo blocco CSS, senza commenti.

    ⚠️ Guardare i commenti invece del codice e' l'errore gia' costato tre
    asserzioni false nella stesura precedente di questo pannello: le regole che
    NON si usano piu' sono spiegate li' dentro, e una `assert ... not in`
    ingenua le ripesca.
    """
    blocco = _sorgente().split("export const css = `", 1)[1].split("`", 1)[0]
    return re.sub(r"/\*.*?\*/", "", blocco, flags=re.S)


def _corpo_di_atto() -> str:
    """Il corpo di `atto()`, dal nome della funzione al `inserisci` seguente."""
    return _sorgente().split("function atto(", 1)[1].split("function inserisci(", 1)[0]


def _nel_modulo(corpo: str) -> object:
    """Esegue `corpo` con il pannello importato come `P` e il fixture come `F`."""
    if shutil.which("node") is None:
        pytest.skip("node non disponibile")
    r = subprocess.run(
        ["node", "--input-type=module", "-e",
         f'import * as P from "{PANNELLO}";\n'
         f'import * as F from "{FIXTURE}";\n{corpo}'],
        capture_output=True, text=True, timeout=60, cwd=RADICE,
    )
    assert r.returncode == 0, r.stderr[-1200:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _classifica(righe: list[dict]) -> list[list]:
    """`[forma, etichetta]` per ogni riga, calcolati dal modulo VERO."""
    return _nel_modulo(
        f"const R = {json.dumps(righe)};"
        "console.log(JSON.stringify("
        "  R.map((r) => [P.formaAtto(r), P.etichettaAtto(r)])));"
    )


# ── il comportamento, eseguito ───────────────────────────────────────────────

class TestLaFormaDiUnaRiga:
    """Tre forme, e la distinzione la porta la STRADA.

    Non l'esito, non il testo: la strada. Un'euristica sull'esito direbbe che
    la delega e' riuscita e la caduta no — vero, ma per una ragione che il
    pannello non deve indovinare, e che smetterebbe di valere il giorno in cui
    una delega fallisse per un'altra causa.
    """

    def test_il_modulo_si_CARICA(self) -> None:
        """La trappola nota: un backtick dentro un commento CSS chiude il
        template literal e il modulo non parte piu'. `test_fogli_di_stile.py`
        lo dice per tutti i fogli in 0,04 s; qui si prova il modulo intero,
        import compresi."""
        assert _nel_modulo("console.log(JSON.stringify(P.meta.nome));") == "diario"

    def test_un_comando_riconosciuto_e_la_forma_INTENTO(self) -> None:
        forma, etichetta = _classifica([RIGHE_VERE[0]])[0]
        assert forma == "intento"
        assert etichetta == "open_panel telemetria", (
            "gli argomenti fanno parte del comando: `open_panel` da solo e' una "
            "categoria, non cio' che e' successo"
        )

    def test_la_DELEGA_a_T1_non_e_un_guasto(self) -> None:
        """⚠️ La riga per cui esiste questo file. Intento nullo e strada t1
        vuol dire che T0 non ha morso e la frase e' andata a T1: e' il
        funzionamento normale. Marcarla come errore direbbe una cosa falsa
        della meta' dei turni."""
        forma, etichetta = _classifica([RIGHE_VERE[1]])[0]
        assert forma == "delega"
        assert forma != "caduta", "una delega non e' una caduta"
        assert "?" not in etichetta, (
            "il punto interrogativo e' esattamente la risposta che non spiega "
            "niente, ed e' quella che c'era prima"
        )

    def test_la_CADUTA_si_distingue_dalla_delega(self) -> None:
        """Stesso intento nullo, strada diversa: T1 non c'era. E' un guasto, e
        il core lo scrive con `ok` falso ed `errore` t1_assente."""
        caduta = {"flusso": "azione", "intento": None, "args": None, "ok": False,
                  "da": "voce", "strada": "nessuna", "testo": "apri il coso strano",
                  "quasi_comando": "apri", "errore": "t1_assente"}
        forma, etichetta = _classifica([caduta])[0]
        assert forma == "caduta"
        assert "?" not in etichetta

    def test_il_RESOCONTO_al_risveglio_resta_un_intento(self) -> None:
        """Non viene dalla voce, ma un intento ce l'ha: la colonna `da` dice da
        dove viene, la forma dice che cosa e'."""
        forma, etichetta = _classifica([RIGHE_VERE[2]])[0]
        assert forma == "intento" and etichetta == "resoconto_al_risveglio"

    def test_le_TRE_righe_vere_non_producono_MAI_un_punto_interrogativo(self) -> None:
        """La misura del difetto: prima, due righe su tre finivano in «?»."""
        etichette = [e for _, e in _classifica(RIGHE_VERE)]
        assert not [e for e in etichette if "?" in e], etichette

    def test_una_riga_senza_argomenti_non_inventa_uno_spazio(self) -> None:
        got = _classifica([{"intento": "brief_me", "args": None, "ok": True,
                            "strada": "core"}])[0]
        assert got == ["intento", "brief_me"]

    def test_un_args_VUOTO_non_e_un_argomento(self) -> None:
        got = _classifica([{"intento": "brief_me", "args": {}, "ok": True,
                            "strada": "core"}])[0]
        assert got[1] == "brief_me"


class TestIlFixtureDellaGalleria:
    """Invariante 23 — righe REGISTRATE, non plausibili."""

    def test_porta_le_righe_VERE_del_27_agosto(self) -> None:
        """I tre campi che il pannello non sapeva rendere, verbatim."""
        s = FIXTURE.read_text(encoding="utf-8")
        assert 'testo: "il panetto della geometria."' in s, "manca la delega vera"
        assert 'intento: "resoconto_al_risveglio"' in s, "manca il risveglio vero"
        assert "iniziative: 1" in s
        assert 'da: "risveglio"' in s and 'strada: "diario"' in s
        assert "ho messo in ordine gli appunti di 1 sessione." in s

    def test_le_righe_registrate_PRIMA_sono_ancora_li(self) -> None:
        """Aggiungere non e' sostituire: la sessione del 26 agosto porta il
        barge-in e il detto stimato, che nessuna riga del 27 ha."""
        s = FIXTURE.read_text(encoding="utf-8")
        assert "duedici" in s and "il cero è blu" in s
        assert "interrotto: true" in s and "misurato: false" in s
        assert 'strada: "nessuna"' in s

    def test_copre_la_DELEGA_oltre_all_intento(self) -> None:
        """Il fixture si giudica per quello che il pannello ci legge dentro,
        non per quante righe ha: senza una delega, lo scatto del ciclo §11.7
        non puo' dire se una delega si veda come un errore."""
        forme = _nel_modulo(
            "console.log(JSON.stringify(F.RIGHE"
            '  .filter((r) => r.flusso === "azione")'
            "  .map((r) => P.formaAtto(r))));"
        )
        assert "delega" in forme, "nessuna delega: il caso nuovo non e' in galleria"
        assert "intento" in forme

    def test_e_DICHIARA_la_forma_che_NON_ha(self) -> None:
        """⚠️ La caduta non ha una riga registrata, e l'invariante 23 vieta di
        scriverne una plausibile. Un buco taciuto e' un buco che nessuno
        ricorda: il montaggio lo deve dire per iscritto."""
        forme = _nel_modulo(
            "console.log(JSON.stringify(F.RIGHE"
            '  .filter((r) => r.flusso === "azione")'
            "  .map((r) => P.formaAtto(r))));"
        )
        m = MONTA.read_text(encoding="utf-8")
        if "caduta" in forme:
            pytest.fail("adesso la caduta c'e': togli la dichiarazione dal montaggio")
        assert "CADUTA, non e' in galleria" in m, (
            "la forma mancante va dichiarata dov'e' mancante"
        )

    def test_una_riga_fallita_col_suo_errore_e_in_galleria(self) -> None:
        """Il caso su cui si guarda se una riga rotta si vede da lontano."""
        got = _nel_modulo(
            "console.log(JSON.stringify(F.RIGHE.filter("
            '  (r) => r.flusso === "azione" && r.ok === false && r.errore).length));'
        )
        assert got >= 1


# ── il DOM e il foglio: controlli sul SORGENTE ───────────────────────────────

class TestLaRigaSiLEGGE:
    """Che cosa finisce davvero nella cella, e in quale elemento.

    ⚠️ Limite dichiarato: senza un DOM questi guardano il sorgente. Vedono che
    la regola c'e', non che si vede.
    """

    def test_l_intento_passa_dalla_funzione_e_non_da_un_punto_interrogativo(self) -> None:
        corpo = _corpo_di_atto()
        assert "etichettaAtto(msg)" in corpo
        assert '(msg.intento ?? "?")' not in corpo, "il punto interrogativo e' tornato"

    def test_le_CINQUE_celle_esistono_nel_markup(self) -> None:
        """⚠️ Trovato perturbando: togliere una `span` dal template lasciava il
        test verde, perche' il `querySelector` che la cerca resta nel corpo
        della funzione. Sullo schermo la riga sparirebbe del tutto — quel
        `querySelector` torna `null` e la costruzione solleva."""
        celle = _corpo_di_atto().split("el.innerHTML = `", 1)[1].split("`", 1)[0]
        for c in ("pnl-dia__ora", "pnl-dia__esito", "pnl-dia__intento",
                  "pnl-dia__origine", "pnl-dia__strada"):
            assert f'class="{c}"' in celle, f"manca la cella {c}"

    def test_l_ORIGINE_e_una_colonna_sua(self) -> None:
        """`da` distingue un resoconto che JARVIS ha deciso da solo da un
        comando che gli e' stato detto. Prima non compariva affatto."""
        corpo = _corpo_di_atto()
        assert 'el.dataset.da = msg.da ?? "?"' in corpo
        assert '.pnl-dia__origine").textContent = msg.da' in corpo
        assert ".pnl-dia__origine" in _css(), "la colonna esiste e non ha regola"

    def test_l_ERRORE_ha_un_ELEMENTO_suo(self) -> None:
        """Prima era concatenato dentro la cella dell'intento, in
        --txt-primary: un guasto scritto col colore di ogni altra cosa."""
        corpo = _corpo_di_atto()
        assert "pnl-dia__errore" in corpo
        assert 'msg.errore ? " — " + msg.errore' not in corpo, (
            "l'errore e' di nuovo appiccicato all'intento"
        )

    def test_il_TESTO_arriva_nel_DOM(self) -> None:
        """Per la delega e' l'unica cosa che la riga ha da dire — e' l'ingresso
        da cui si ripara la grammatica."""
        corpo = _corpo_di_atto()
        assert '[msg.testo, "pnl-dia__detto"]' in corpo
        assert "riga.textContent = valore;" in corpo, (
            "svuotare questa riga lascerebbe il test verde e lo schermo vuoto"
        )

    def test_il_testo_entra_con_textContent_e_MAI_come_markup(self) -> None:
        """La stessa ragione del dialogo: `testo` e' una TRASCRIZIONE, cioe'
        testo che nessuno ha rivisto. Il CSP vieta l'esecuzione, non l'inganno."""
        corpo = _corpo_di_atto()
        assert not re.search(r"innerHTML\s*\+?=\s*(?!`)\S", corpo), (
            "qualcosa entra come markup dentro atto(): l'unico innerHTML ammesso "
            "e' il template letterale delle celle vuote, che non interpola nulla"
        )
        assert "msg.testo" not in corpo.split("el.innerHTML = `", 1)[1].split("`", 1)[0]

    def test_le_INIZIATIVE_sopravvivono_allo_ZERO(self) -> None:
        """«Non ho fatto niente» e' un resoconto come un altro: con un
        controllo di verita' la riga a zero perderebbe il proprio conto, che e'
        il caso in cui serve di piu' saperlo."""
        corpo = _corpo_di_atto()
        assert 'typeof msg.iniziative === "number"' in corpo
        assert '" iniziativa"' in corpo and '" iniziative"' in corpo

    def test_il_QUASI_COMANDO_si_vede(self) -> None:
        """Un comando mancato per poco: e' il dato da cui si ripara la
        grammatica, e stava nella riga senza arrivare sullo schermo."""
        corpo = _corpo_di_atto()
        assert "msg.quasi_comando" in corpo
        assert 'marca("quasi"' in corpo
        assert '.pnl-dia__marca[data-tipo="quasi"]' in _css()

    def test_la_cella_dell_intento_compone_davvero_la_parola(self) -> None:
        """Svuotare `textContent` del marcatore lo farebbe sparire dallo
        schermo lasciando le stringhe nel sorgente, e il test verde."""
        assert r'm.textContent = " \u2014 " + parola;' in _sorgente()


class TestUnaRigaFallitaSiVedeFallita:
    """Il colore su TRE punti, non su una sigla di due lettere."""

    def test_il_filetto_a_sinistra_e_ROSSO_solo_quando_ok_e_falso(self) -> None:
        css = _css()
        assert re.search(
            r'\.pnl-dia__atto\[data-ok="0"\]\s*\{\s*border-left-color:\s*var\(--rust\)',
            css), "manca il filetto della riga fallita"
        assert re.search(
            r"\.pnl-dia__atto\s*\{[^}]*border-left:\s*var\(--line-bold\)\s+solid\s+transparent",
            css, re.S), (
            "il filetto deve stare su OGNI riga, trasparente dove non serve: "
            "altrimenti le righe fallite scalano di due pixel"
        )

    def test_il_messaggio_d_errore_e_in_rust(self) -> None:
        assert re.search(r"\.pnl-dia__errore\s*\{\s*color:\s*var\(--rust\)", _css())

    def test_l_esito_resta_in_rust(self) -> None:
        assert re.search(
            r'\.pnl-dia__atto\[data-ok="0"\]\s+\.pnl-dia__esito\s*\{\s*color:\s*var\(--rust\)',
            _css())

    def test_la_DELEGA_non_prende_NESSUN_colore_di_allarme(self) -> None:
        """⚠️ Il difetto che questo file esiste per impedire, visto dal foglio:
        se una regola su `data-tipo="delega"` portasse --rust o --amber, il
        funzionamento normale si leggerebbe come un guasto."""
        for regola in re.findall(r'[^}]*\[data-tipo="delega"\][^{]*\{[^}]*\}', _css()):
            assert "--rust" not in regola and "--amber" not in regola, regola
        assert re.search(
            r'\[data-tipo="delega"\]\s+\.pnl-dia__intento\s*\{\s*color:\s*var\(--txt-dim\)',
            _css()), "la delega non ha un colore proprio, e cade in --txt-primary"

    def test_la_forma_finisce_nel_DOM_come_dato(self) -> None:
        """Senza `data-tipo` sull'elemento le regole qui sopra non hanno presa."""
        assert "el.dataset.tipo = formaAtto(msg);" in _corpo_di_atto()


class TestGliInvariantiDiDesign:
    """§10, invarianti 18, 19, 25 — misurati sul foglio del pannello."""

    def test_zero_valori_letterali(self) -> None:
        css = _css()
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css), "colore letterale"
        assert not re.search(r"\brgba?\(", css), "colore letterale"
        assert not re.search(r"[\s:]\d+(\.\d+)?(px|rem|pt|vh|vw)\b", css), (
            "spaziatura o tipografia letterale"
        )

    def test_ogni_token_usato_ESISTE_in_tokens_css(self) -> None:
        """Un `var(--sbagliato)` non fa rumore: il browser lascia il valore
        iniziale e il pannello si guarda senza accorgersene."""
        dichiarati = set(re.findall(r"(--[\w-]+)\s*:", TOKENS.read_text(encoding="utf-8")))
        usati = set(re.findall(r"var\(\s*(--[\w-]+)", _css()))
        # `--aug-*` li dichiara augmented-ui, non tokens.css.
        ignoti = {u for u in usati - dichiarati if not u.startswith("--aug-")}
        assert not ignoti, f"token inesistenti: {sorted(ignoti)}"

    def test_border_radius_sempre_zero(self) -> None:
        for v in re.findall(r"border-radius:\s*([^;]+);", _css()):
            assert v.strip() == "var(--radius)", v

    def test_zero_glow_zero_bloom_zero_alone(self) -> None:
        css = _css()
        for vietato in ("text-shadow", "drop-shadow", "box-shadow", "blur("):
            assert vietato not in css, (
                f"{vietato} nel diario: l'invariante 19 non ammette aloni, e qui "
                "nessuna superficie ne copre un'altra"
            )

    def test_nessuna_animazione_senza_causa(self) -> None:
        css = _css()
        for vietato in ("@keyframes", "animation:", "transition:"):
            assert vietato not in css, (
                f"{vietato}: l'invariante 25 vieta il moto ambientale, e un "
                "registro che scorre non ha una sorgente viva da mostrare"
            )

    def test_la_seconda_riga_occupa_TUTTE_le_colonne(self) -> None:
        """Una frase dentro una colonna elastica sposta tutte le altre a ogni
        riga nuova, e il registro smette di essere incolonnato."""
        css = _css()
        assert re.search(
            r"\.pnl-dia__detto,\s*\.pnl-dia__errore\s*\{[^}]*grid-column:\s*1\s*/\s*-1",
            css, re.S)
        assert re.search(
            r"\.pnl-dia__atto\s*\{[^}]*grid-template-columns:\s*auto auto 1fr auto auto",
            css, re.S), "cinque colonne: ora, esito, intento, origine, strada"
