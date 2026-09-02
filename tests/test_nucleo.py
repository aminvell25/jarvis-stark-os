"""Il nucleo Aurora: che cosa regge, e che cosa e' stato derogato dichiarandolo.

Il 1º settembre 2026 il proprietario ha portato un secondo riferimento — un
artifact «Jarvis Aurora» — e ha chiesto di eliminare il nucleo presente e
rifarlo su quella specifica, «anche se va contro le nostre specifiche». Il
nucleo HUD del giorno prima e' stato cancellato; sta al commit 427e48c.

Questi presidi NON verificano che il nucleo sia bello: verificano le tre cose
che una sostituzione autorizzata puo' ancora sbagliare in silenzio.

① **Le deroghe sono DICHIARATE.** Sei invarianti cedono. Una deroga scritta si
  puo' pesare e revocare; una deroga che si scopre leggendo il codice e' un
  difetto travestito da decisione.
② **Cio' che NON e' derogato regge davvero.** L'invariante 18 (nessun colore
  letterale) e l'invariante 23 (nessun dato inventato) non sono stati toccati,
  e qui si misura che sia vero.
③ **Il cancello perso ha un sostituto DICHIARATO.** L'invariante 22 chiedeva
  `qualityGate()` su ogni geometria; gli icosaedri di three.js non lo passano.
  Al suo posto c'e' un conteggio di vertici, ed e' verificato qui.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
AURORA = RADICE / "ui" / "src" / "hud" / "aurora"
SFONDO = RADICE / "ui" / "src" / "desk" / "sfondo.js"
ACCETTAZIONE = RADICE / "docs" / "acceptance" / "NUCLEO-AURORA.md"


def senza_commenti(testo: str) -> str:
    """Il sorgente senza commenti: i commenti CITANO i colori del riferimento
    per spiegare da dove vengono, e cercarli li' darebbe falsi positivi."""
    testo = re.sub(r"/\*.*?\*/", "", testo, flags=re.S)
    return re.sub(r"(?<![:'\"])//.*$", "", testo, flags=re.M)


class TestLaGeometriaEUNA:
    def test_il_viewbox_sta_in_un_posto_solo(self) -> None:
        """1024 e' il quadro del riferimento, e ogni raggio e' un numero preso
        da li'. Due copie divergono, e la divergenza si vede solo a schermo."""
        fuori = []
        for f in sorted(AURORA.glob("*.js")):
            if f.name == "geometria.js":
                continue
            corpo = senza_commenti(f.read_text(encoding="utf-8"))
            if re.search(r"\b1024\b", corpo):
                fuori.append(f.name)
        assert not fuori, (
            "1024 compare fuori da aurora/geometria.js, in " + ", ".join(fuori)
            + ".\nIl viewBox sta in un posto solo: e' la quota da cui dipende "
            "ogni raggio."
        )

    def test_i_gusci_sono_TRE_e_sfasati(self) -> None:
        """Tre gusci con raggi e fasi diversi. Con fasi uguali le creste di
        rumore coinciderebbero e la superficie leggerebbe come una membrana
        invece che come spessore — il motivo per cui sono tre."""
        corpo = (AURORA / "stati.js").read_text(encoding="utf-8")
        raggi = [float(x) for x in re.findall(r"raggio: ([\d.]+)", corpo)]
        fasi = [float(x) for x in re.findall(r"fase: ([\d.]+)", corpo)]
        assert len(raggi) == 3, f"i gusci sono {len(raggi)}, il riferimento ne da' tre"
        assert len(set(fasi)) == 3, f"due gusci condividono la fase: {fasi}"
        assert raggi == sorted(raggi), "i raggi non salgono: l'ordine e' il guscio"


class TestGliOttoStati:
    def test_sono_otto_e_gli_id_sono_UNICI(self) -> None:
        corpo = (AURORA / "stati.js").read_text(encoding="utf-8")
        ids = re.findall(r'id: "([A-Z]+)"', corpo)
        assert len(ids) == 8, f"gli stati sono {len(ids)}, il riferimento ne da' otto"
        assert len(set(ids)) == 8, f"due stati con lo stesso id: {ids}"

    def test_ogni_stato_deriva_da_un_FATTO_e_non_da_un_topic(self) -> None:
        """⚠️ La regola che il nucleo precedente aveva e che questo conserva:
        lo stato si DERIVA dalle cause, e nessun messaggio lo dichiara. Un
        topic che dicesse «adesso sei in ANALISI» sarebbe una seconda fonte di
        verita' — CLAUDE.md la vieta, e non e' un'astrazione: due fonti
        divergono, e a divergere sarebbe cio' che l'occhio legge."""
        corpo = senza_commenti((AURORA / "stati.js").read_text(encoding="utf-8"))
        assert "export function statoDa" in corpo, "manca il deduttore"
        deduttore = corpo[corpo.index("export function statoDa"):]
        for fatto in ("livello", "coreVivo", "attivo.parla", "attivo.ascolto"):
            assert fatto in deduttore, (
                f"`{fatto}` non entra nella derivazione dello stato: allora "
                "quello stato non ha una causa vera"
            )
        assert "topic" not in deduttore, (
            "il deduttore guarda un topic: lo stato si deriva dai FATTI, non "
            "si riceve gia' fatto"
        )

    def test_gli_alias_del_banco_risolvono_TUTTI(self) -> None:
        """`app/main.js`, `verifica:marchio` e `verifica:scrivania` pilotano il
        nucleo con i nomi di prima. Un alias che non risolve non da' errore:
        `fissa()` non trova lo stato, lascia quello corrente, e la misura
        fotografa due volte la stessa cosa credendo di vedere due stati."""
        moto = (AURORA / "moto.js").read_text(encoding="utf-8")
        ids = set(re.findall(r'id: "([A-Z]+)"', (AURORA / "stati.js").read_text(encoding="utf-8")))
        alias = dict(re.findall(r'(\w+): "([A-Z]+)"', moto[moto.index("const ALIAS"):]))
        assert alias, "la tabella degli alias non c'e' piu'"
        rotti = {k: v for k, v in alias.items() if v not in ids}
        assert not rotti, f"alias che non risolvono: {rotti}"
        usati = set(re.findall(r'fissa\("(\w+)"\)', (RADICE / "app" / "main.js").read_text(encoding="utf-8")))
        mancanti = {u for u in usati if u not in alias and u not in ids}
        assert not mancanti, (
            f"app/main.js pilota stati che il nucleo non conosce: {mancanti}"
        )


class TestCioCheNonEDerogato:
    def test_nessun_colore_LETTERALE_nel_nucleo(self) -> None:
        """L'invariante 18 e' l'unico che questa sostituzione non deroga, e il
        riferimento portava **55 colori scritti a mano**. Cinquantaquattro
        cadevano entro ~10 L da un gradino gia' in §10.1; per gli altri sono
        stati aggiunti nove token. Se un letterale rientra, quella misura e'
        stata aggirata."""
        colpevoli = []
        for f in sorted(AURORA.glob("*.js")) + [SFONDO]:
            corpo = senza_commenti(f.read_text(encoding="utf-8"))
            for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", corpo):
                colpevoli.append(f"{f.name}: {m.group(0)}")
        assert not colpevoli, (
            "colori letterali nel nucleo:\n  " + "\n  ".join(colpevoli)
            + "\nI colori del riferimento stanno in §10.1 come token --au-* e "
            "--cy-*; la misura che lo permette e' scritta li'."
        )

    def test_le_frasi_finte_del_riferimento_NON_sono_state_portate(self) -> None:
        """⚠️ L'invariante 23. Il riferimento riempie le corone con «REC248 |
        5NC0DE | MK-XL | PWR.98» e fa parlare JARVIS con un copione —
        «Buonasera signore. Tutti i sistemi sono operativi.» Sono decorazione:
        qui le corone portano la telemetria vera in base 16 e la cadenza delle
        sillabe viene dallo spettro TTS misurato."""
        sospetti = ["Buonasera", "MK-XL", "5NC0DE", "REC248", "PWR.9", "SYS.OK",
                    "Mark quaranta", "LNK.0"]
        #: Senza commenti, come il test dei colori: i commenti CITANO quelle
        #: stringhe per dire che non sono state portate, e cercarle li'
        #: boccerebbe il file proprio perche' spiega di essere pulito.
        colpevoli = []
        for f in sorted(AURORA.glob("*.js")) + [SFONDO]:
            corpo = senza_commenti(f.read_text(encoding="utf-8"))
            for s in sospetti:
                if s in corpo:
                    colpevoli.append(f"{f.name}: {s}")
        assert not colpevoli, (
            "dati segnaposto del riferimento entrati nel nucleo:\n  "
            + "\n  ".join(colpevoli)
        )

    def test_i_fronti_delle_sillabe_vengono_da_una_MISURA(self) -> None:
        """Il riferimento calcola le sillabe contando le vocali di un copione.
        Qui un fronte parte quando l'ampiezza VERA sale di scatto: e' un
        attacco misurato invece che previsto, ed e' la differenza fra
        un'animazione e uno strumento."""
        corpo = (AURORA / "moto.js").read_text(encoding="utf-8")
        assert "SOGLIA_ATTACCO" in corpo, "manca la soglia d'attacco"
        assert "function voce(" in corpo, (
            "manca l'ingresso dell'ampiezza vera: allora i fronti li genera "
            "qualcosa che non e' la voce"
        )


class TestIlCancelloSostituito:
    def test_il_conteggio_dei_vertici_e_DICHIARATO(self) -> None:
        """⚠️ L'invariante 22 chiedeva `qualityGate()`. Gli icosaedri sono
        primitive di three.js: la densita' la fissa `detail`, non
        `segmentsFor()`. Al posto del cancello resta un numero dichiarato, e un
        numero dichiarato che nessuno confronta non e' un cancello."""
        corpo = (AURORA / "nucleo3d.js").read_text(encoding="utf-8")
        assert "vertici: geo.attributes.position.count" in corpo, (
            "il nucleo non conta i propri vertici: il sostituto del cancello "
            "non esiste"
        )
        assert "IcosahedronGeometry(cfg.raggio, 4)" in corpo, (
            "il livello di suddivisione non e' piu' 4: il conteggio atteso "
            "cambia, e va cambiato anche qui"
        )


class TestIlCentroNonEPiuCABLATO:
    """Il difetto piu' silenzioso di questo lavoro, e il presidio che lo chiude.

    §25.13.5 misura quanto lontano dal centro del disco arriva l'inchiostro del
    marchio, e fino al 2 settembre 2026 quel centro era **scritto a mano** in
    `scripts/densita.mjs`: `[768, 422]`, il centro di una finestra 1536x843.

    Era giusto il giorno in cui e' stato scritto. Il guaio e' come ha smesso di
    esserlo: non con un errore, ma continuando a rispondere. Col disco fuori da
    quella posizione ogni distanza usciva sbagliata **della stessa quantita'**,
    e il referto diceva «inchiostro fino a r 350 px» in tutti e nove gli stati.
    Un numero identico fra stati che mostrano cose diverse e' l'unico segno che
    c'era, ed e' costato sette corse.

    Adesso il centro arriva da `data-disco` — che il DOM dichiara gia', e che
    `scripts/occlusione-dom.js` legge da mesi — e viaggia dentro `stati.json`
    insieme al viewport, perche' i pixel CSS e quelli dello scatto possono non
    coincidere.
    """

    def test_il_referto_dice_DA_DOVE_viene_il_centro(self) -> None:
        import json as _json
        esito = RADICE / "docs" / "acceptance" / "MARCHIO-STATI.json"
        assert esito.exists(), "manca MARCHIO-STATI.json — npm run verifica:marchio"
        d = _json.loads(esito.read_text(encoding="utf-8"))
        c = d.get("centro")
        assert c is not None, (
            "il referto non dichiara il centro usato. Un criterio che assume "
            "una posizione senza dirlo e' come e' nato questo difetto: rifai "
            "la misura con `npm run verifica:marchio`."
        )
        assert c.get("da") == "data-disco", (
            f"il centro viene da «{c.get('da')}», non da data-disco. Il "
            "ripiego cablato e' [768, 422], il centro di una finestra "
            "1536x843: vale finche' il disco sta li', e smette di valere "
            "SENZA DIRLO."
        )
        assert c.get("viewport"), (
            "manca il viewport accanto al centro: senza, i pixel CSS non si "
            "sanno convertire in pixel dello scatto, e le due misure possono "
            "non coincidere"
        )

    def test_lo_script_non_ha_piu_un_centro_come_PRIMA_scelta(self) -> None:
        corpo = (RADICE / "scripts" / "densita.mjs").read_text(encoding="utf-8")
        i = corpo.index("let centro = cattura.centro")
        #: Il ripiego resta — una misura che manca e' peggio di una che assume —
        #: ma deve stare DOPO la lettura dal dato e deve annunciarsi.
        coda = corpo[i:i + 900]
        assert "cattura.centro" in coda, "il centro non si legge piu' dal referto"
        assert "⚠️ centro" in coda, (
            "il ripiego cablato non annuncia piu' di essere un ripiego: "
            "un'assunzione silenziosa e' il difetto, non il valore"
        )


class TestLeDerogheSonoSCRITTE:
    def test_il_documento_di_accettazione_ESISTE(self) -> None:
        assert ACCETTAZIONE.exists(), (
            "manca docs/acceptance/NUCLEO-AURORA.md. Sei invarianti cedono: "
            "senza il documento sono sei difetti, non sei decisioni."
        )

    def test_le_sei_deroghe_sono_NOMINATE(self) -> None:
        testo = ACCETTAZIONE.read_text(encoding="utf-8")
        for regola in ["invariante 19", "§25.11", "invariante 25", "§25.5",
                       "invariante 22", "invariante 26"]:
            assert regola in testo, (
                f"«{regola}» cede nel codice e non e' nominata in "
                "NUCLEO-AURORA.md"
            )

    def test_il_codice_e_il_documento_dichiarano_LE_STESSE_deroghe(self) -> None:
        """Due elenchi divergono. Quello nel codice lo legge `window.__insegna
        .deroghe`, e serve a chi guarda la scrivania viva."""
        corpo = SFONDO.read_text(encoding="utf-8")
        i = corpo.index("deroghe: [")
        nel_codice = set(re.findall(r'"([^"]+)"', corpo[i:corpo.index("]", i)]))
        testo = ACCETTAZIONE.read_text(encoding="utf-8")
        fuori = {d for d in nel_codice if d.split(" e ")[0] not in testo}
        assert not fuori, (
            f"il codice dichiara deroghe che il documento non ha: {fuori}"
        )
