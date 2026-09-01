"""Il nucleo HUD — le proprieta' che devono reggere, e perche' proprio queste.

## Che cosa e' cambiato il 31 agosto 2026

Questo file provava il nucleo a cinque anelli: la scala di §25.5 dentro
`desk/sfondo.js`, `autoplay: false`, la tabella delle cause, la geometria
importata da `anim/rings.js`. Quel nucleo non esiste piu': e' stato sostituito
dalla replica del riferimento HUD misurato, otto strati, geometria in
`ui/src/hud/geometria.js`.

**I presidi non si cancellano quando cambia l'oggetto: cambiano domanda.** Un
test tolto e' una regola che sparisce senza che nessuno lo sappia, ed e'
esattamente la storia che `DEROGHE-7dad2b8.md` racconta — una regola viveva in
`presenza.js`, il file e' stato cancellato, e la regola se n'e' andata con lui
in silenzio.

## Che cosa NON e' ancora qui

Moto (F2), onda (F3), globo (F4) e telemetria (F5) non sono costruiti. I loro
presidi arrivano con loro: un test scritto adesso su un comportamento che non
esiste sarebbe verde **per assenza del fenomeno**, che §11.7 regola 4 dice
esplicitamente non contare come verde.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
GEOMETRIA = RADICE / "ui" / "src" / "hud" / "geometria.js"
STRATI = RADICE / "ui" / "src" / "hud" / "strati.js"
INSEGNA = RADICE / "ui" / "src" / "desk" / "sfondo.js"
TOKENS = RADICE / "ui" / "src" / "style" / "tokens.css"
ESITO_MARCHIO = RADICE / "docs" / "acceptance" / "MARCHIO-STATI.json"


def senza_commenti(js: str) -> str:
    """Il JS senza commenti, per contare gli USI e non le menzioni.

    ⚠️ Serve per una ragione misurata. Il presidio che stava qui prima cercava
    `autoplay: false` nel testo di `rings.js` e passava — ma passava perche' la
    stringa era dentro un COMMENTO che spiegava la deroga, mentre il codice
    faceva l'opposto. Un presidio soddisfatto da cio' che il file racconta di
    se' non presidia niente.
    """
    fuori = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    # ⚠️ Anche quelli IN CODA RIGA, e la prima stesura li lasciava: i commenti
    # di `GRADI_AL_SECONDO` portano i valori VECCHI («era 6,0: 60 s era il
    # doppio esatto») e finivano fra i numeri estratti, facendo fallire il test
    # dei rapporti su periodi che non esistono. Un presidio che legge i propri
    # commenti misura il racconto, non il codice.
    return re.sub(r"//.*$", "", fuori, flags=re.M)


def numeri_di(blocco: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+\.?\d*", blocco)]


class TestLaGeometriaEUNA:
    def test_i_raggi_stanno_in_UN_FILE_SOLO(self) -> None:
        """Il difetto che il turno del 23 agosto 2026 ha speso un giorno a
        chiudere: due nuclei, due tabelle, e ogni modifica ne allineava una.

        Qui la tabella e' `STRATI` in `hud/geometria.js`. Chi la ricopiasse —
        in `strati.js`, in `sfondo.js`, in un mount — rimetterebbe la stessa
        divergenza con un altro nome.
        """
        for f in (STRATI, INSEGNA):
            corpo = senza_commenti(f.read_text(encoding="utf-8"))
            assert "const STRATI = [" not in corpo, (
                f"{f.relative_to(RADICE)} dichiara una seconda tabella STRATI. "
                "La geometria sta in ui/src/hud/geometria.js, in un posto solo."
            )
            assert "r: [" not in corpo, (
                f"{f.relative_to(RADICE)} contiene una tabella di raggi. "
                "I raggi si importano, non si ricopiano: al primo cambio di "
                "composizione la copia resta indietro in silenzio."
            )
        for f in (STRATI, INSEGNA):
            assert "geometria.js" in f.read_text(encoding="utf-8"), (
                f"{f.relative_to(RADICE)} non importa piu' la geometria"
            )

    def test_gli_otto_strati_ci_sono_TUTTI(self) -> None:
        """Il riferimento ha otto sistemi concentrici. Sette sarebbero un altro
        oggetto, e la differenza non si vede leggendo un diff."""
        js = GEOMETRIA.read_text(encoding="utf-8")
        i = js.index("export const STRATI = [")
        j = js.index("\n];", i)
        ids = re.findall(r'id:\s*"(\w+)"', js[i:j])
        assert ids == ["mirino", "logo", "segmentato", "quadranti",
                       "globo", "vetro", "tecnico", "hex"], (
            f"gli strati sono {ids}: il riferimento ne misura otto, "
            "dal mirino all'anello alfanumerico"
        )


class TestLeDueRegoleDelRiferimento:
    def test_NESSUNA_circonferenza_nuda(self) -> None:
        """La regola 3 del riferimento, ed e' la differenza fra un HUD e un
        diagramma: ogni anello porta graduazioni, segmenti, tacche, archi o
        dati. Un cerchio con un tratto uniforme e niente sopra e' sbagliato.

        Si conta sui CAMPI della tabella, non sull'aspetto: un campo di
        dettaglio o c'e' o non c'e', e un giudizio a occhio su otto strati
        cambierebbe da persona a persona.
        """
        js = GEOMETRIA.read_text(encoding="utf-8")
        i = js.index("export const STRATI = [")
        j = js.index("\n];", i)
        DETTAGLI = ("tacche:", "tratteggio:", "dash:", "archiParziali:",
                    "archiSolidi:", "guidaTesto:", "punti:", "varco:", "icone:")
        nudi = []
        for blocco in re.findall(r"\{\s*\n\s*id: \"(\w+)\",(.*?)\n  \},",
                                 js[i:j] + "\n  },", re.S):
            nome, corpo = blocco
            if not any(d in corpo for d in DETTAGLI):
                nudi.append(nome)
        assert not nudi, (
            f"strati senza un solo dettaglio: {nudi}.\n"
            "Il riferimento non ha circonferenze nude: ogni anello porta "
            "graduazioni, segmenti, tacche o dati. Un cerchio liscio legge come "
            "un diagramma, non come un HUD."
        )

    def test_i_periodi_NON_sono_multipli_fra_loro(self) -> None:
        """§10.3, e il riferimento ci cade dentro da solo.

        Le velocita' che il riferimento dichiara — 6, 12, −8, ±20, −3 °/s —
        danno 60 s e 30 s (rapporto 2,000) e 120 s e 60 s (idem). Anelli in
        rapporto intero si riallineano a cadenza fissa, e dopo un minuto
        l'occhio riconosce la ripetizione.

        Lo scostamento e' stato **cercato**, non scelto: 0,4 °/s in tutto, su
        due anelli. Chi lo «arrotonda per pulizia» rimette il difetto, e questo
        test glielo dice prima.
        """
        js = GEOMETRIA.read_text(encoding="utf-8")
        i = js.index("export const GRADI_AL_SECONDO = {")
        j = js.index("\n};", i)
        corpo = senza_commenti(js[i:j])
        gradi = [abs(float(v)) for v in re.findall(r":\s*(-?\d+\.?\d*)", corpo)]
        assert len(gradi) >= 5, f"meno di cinque velocita': {gradi}"

        periodi = [360.0 / g for g in gradi]
        vicini = []
        for a in range(len(periodi)):
            for b in range(a + 1, len(periodi)):
                r = max(periodi[a], periodi[b]) / min(periodi[a], periodi[b])
                if abs(r - round(r)) < 0.08:
                    vicini.append(f"{periodi[a]:.1f}s/{periodi[b]:.1f}s = {r:.3f}")
        assert not vicini, (
            "due periodi stanno in rapporto (quasi) intero: " + ", ".join(vicini) +
            ".\nSi riallineano a cadenza fissa, ed e' il ciclo visibile che "
            "§10.3 esiste per evitare."
        )

    def test_i_varchi_sono_TUTTI_DIVERSI(self) -> None:
        """§11.6 regola 6: «il varco nell'anello e' un parametro con un nome,
        non `Math.random()`». Due varchi uguali sembrano un errore di copia;
        due scelti a caso sembrano rumore. Vanno decisi, e vanno diversi."""
        js = senza_commenti(GEOMETRIA.read_text(encoding="utf-8"))
        # ⚠️ `archiSolidi` NE E' FUORI, ed e' una distinzione di sostanza.
        # I due archi di L6 sono la stessa forma opposta di 180°: il
        # riferimento li misura entrambi a ~70°, e farli diversi non sarebbe
        # asimmetria progettata — sarebbe una simmetria rotta a caso.
        # La regola vale sui VARCHI e sugli archi parziali, che sono le
        # aperture che l'occhio confronta fra un anello e l'altro.
        senza_solidi = re.sub(r"archiSolidi:\s*\[.*?\],", "", js, flags=re.S)
        ampiezze = [float(x) for x in re.findall(r"ampiezza:\s*([\d.]+)", senza_solidi)]
        doppie = [a for a in set(ampiezze) if ampiezze.count(a) > 1]
        assert not doppie, (
            f"aperture ripetute {doppie} fra {ampiezze}: l'asimmetria e' "
            "progettata, non copiata"
        )


class TestLaScalaDelNucleo:
    def test_la_palette_misurata_e_ENTRATA_NEI_TOKEN(self) -> None:
        """Invariante 18: la palette del riferimento non e' fatta di letterali.

        Cinque degli otto livelli misurati erano gia' nella rampa; tre no, e
        sono entrati come gradini. Se qualcuno li togliesse, il nucleo
        ricadrebbe sui letterali o cambierebbe aspetto senza dirlo.
        """
        css = TOKENS.read_text(encoding="utf-8")
        for token, valore in (("--cy-800", "#205463"),
                              ("--cy-600", "#5a9aab"),
                              ("--cy-200", "#94e5f4")):
            assert f"{token}:{valore}" in css.replace(" ", ""), (
                f"{token} non vale piu' {valore}: e' un livello MISURATO sul "
                "riferimento, non un colore scelto"
            )

    def test_la_rampa_ciano_resta_MONOTONA(self) -> None:
        """Numero che scende, luminanza che sale. Tre gradini nuovi in mezzo a
        cinque esistenti sono un'occasione di invertirne uno, e una rampa
        invertita non si vede leggendo il file — e' gia' successo con le
        superfici (R80)."""
        css = TOKENS.read_text(encoding="utf-8")
        rampa = {int(num): val
                 for _, num, val in re.findall(r"(--cy-(\d+)):\s*(#[0-9a-f]{6})", css)}

        def lum(h: str) -> float:
            r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        assert len(rampa) >= 8, f"la rampa ha {len(rampa)} gradini: attesi almeno 8"
        ordinati = [rampa[k] for k in sorted(rampa, reverse=True)]
        luminanze = [lum(v) for v in ordinati]
        assert luminanze == sorted(luminanze), (
            "la rampa ciano non e' monotona: "
            + ", ".join(f"{k}={lum(rampa[k]):.0f}" for k in sorted(rampa, reverse=True))
        )

    def test_il_nucleo_NON_usa_il_livello_del_testo_dei_pannelli(self) -> None:
        """§25.5, la meta' che la deroga NON tocca.

        Il tetto e' salito a `--cy-200` per il riferimento — deroga dichiarata
        in `NUCLEO-HUD.md` — ma `--cy-100` resta vietato: e' il livello del
        testo dei pannelli, e un nucleo che compete col dato e' decorazione.
        """
        for f in (INSEGNA, STRATI):
            corpo = senza_commenti(f.read_text(encoding="utf-8"))
            assert "var(--cy-100)" not in corpo, (
                f"{f.relative_to(RADICE)} usa --cy-100. §25.5 lo vieta anche "
                "dopo la deroga: e' il livello del testo dei pannelli."
            )


class TestIlBagliore:
    """⚠️ La deroga 1 — l'invariante 19 vieta glow e bloom, e qui ci sono.

    Il proprietario l'ha derogata per replicare il riferimento. Il presidio non
    sparisce: cambia domanda, e la domanda è **quanto si è diffusa**.

    Il pericolo non è il bagliore: è che l'audit NON LO VEDE.
    `gallery/audit.js` controlla la proprietà CSS `filter`; un
    `filter="url(#...)"` è un attributo SVG e `getComputedStyle` risponde
    `none`. Una deroga invisibile allo strumento che la dovrebbe contare non è
    una deroga — è un buco. Quindi la si conta qui.
    """

    def test_il_bagliore_vive_in_UN_FILE_SOLO(self) -> None:
        """Un id, una funzione, un file. Il giorno che un secondo componente
        monta un `feGaussianBlur`, questo test lo dice — e allora è un'altra
        decisione, non l'estensione silenziosa di questa."""
        colpevoli = []
        for f in sorted((RADICE / "ui" / "src").rglob("*.js")):
            corpo = senza_commenti(f.read_text(encoding="utf-8"))
            if "feGaussianBlur" in corpo or "UnrealBloom" in corpo:
                colpevoli.append(f.relative_to(RADICE).as_posix())
        assert colpevoli == ["ui/src/hud/strati.js"], (
            f"il bagliore è montato da {colpevoli}.\n"
            "La deroga all'invariante 19 vale per il NUCLEO e per un file solo. "
            "Un secondo montaggio non è un'estensione della deroga: è un'altra "
            "decisione, e va presa scrivendola in docs/acceptance/."
        )

    def test_il_bagliore_e_CONTABILE(self) -> None:
        """`contaGlow()` esiste, ed è la leva con cui la verifica in finestra
        vera conta quanti elementi brillano. Senza, la deroga sarebbe
        verificabile solo a occhio — e a occhio un bagliore in più su un
        pannello non si distingue da uno in meno sul nucleo."""
        js = STRATI.read_text(encoding="utf-8")
        assert "export function contaGlow" in js, (
            "ui/src/hud/strati.js non espone piu' contaGlow(): la deroga "
            "all'invariante 19 smette di essere misurabile."
        )


class TestIlMarchio:
    def test_regge_in_TUTTI_gli_stati_e_la_misura_e_FRESCA(self) -> None:
        """§25.13.5 non e' un numero, e' un numero PER STATO — e va rimisurato.

        Un'impronta dei sorgenti del nucleo viaggia dentro l'esito: se non
        combacia, qualcuno ha cambiato il nucleo senza rimisurare. Un esito
        vecchio e' peggio di nessun esito, perche' sembra una verifica.

        Si produce con: `npm run verifica:marchio`
        """
        import hashlib

        assert ESITO_MARCHIO.exists(), (
            "manca docs/acceptance/MARCHIO-STATI.json.\n"
            "Si produce con: npm run verifica:marchio"
        )
        d = json.loads(ESITO_MARCHIO.read_text(encoding="utf-8"))

        h = hashlib.sha256()
        for f in d["fonti"]:
            h.update((RADICE / f).read_bytes())
        assert h.hexdigest()[:16] == d["impronta"], (
            "il nucleo e' cambiato dopo l'ultima misura di §25.13.5.\n"
            f"impronta nell'esito {d['impronta']}, sorgenti adesso {h.hexdigest()[:16]}.\n"
            "Rimisura: npm run verifica:marchio\n"
            f"(l'impronta copre {', '.join(d['fonti'])})"
        )

        minimo, massimo = d["soglie"]["contrastoMin"], d["soglie"]["contrastoMax"]
        stati = {k: v for k, v in d["stati"].items() if not v["variante"]}
        for nome, v in sorted(stati.items()):
            assert minimo <= v["contrasto"] <= massimo, (
                f"§25.13.5 fuori forbice nello stato «{nome}»: "
                f"{v['contrasto']:.2f}:1, ammesso {minimo}-{massimo}:1."
            )

        assert d["franco"] > 0, (
            f"l'inchiostro del marchio arriva a r {d['inchiostroMax']} px e la "
            f"traccia comincia a {d['geometria']['raggioMinimoFascia']} px: "
            f"franco {d['franco']} px.\n"
            "Il nome deve stare dentro il proprio campo, o il contrasto di "
            "§25.13.5 smette di essere il rapporto fra due token dichiarati."
        )
