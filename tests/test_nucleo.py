"""Il nucleo fuso — §25.5, §25.6 e le due condizioni della deroga.

## Perche' questi tre controlli e non altri

Sono le tre cose che erano gia' state fatte una volta, e che sono sparite
senza che nulla lo dicesse. Non e' un sospetto: e' la storia scritta in
`docs/acceptance/DEROGHE-7dad2b8.md`.

1. La regola che riporta il tratto degli anelli a `--cy-900` nello strato di
   presenza **esisteva**, in `ui/src/desk/presenza.js`. Quel file e' stato
   cancellato e la regola se n'e' andata con lui. Nessun test parlava di lei,
   quindi il nucleo e' rimasto per giorni con un tratto da pannello — L 181
   contro il tetto di L 48 che §25.5 dichiara invalicabile.
2. `autoplay: false` e' la sola ragione per cui gli anelli non sono animazione
   ambientale. Toglierlo non rompe niente e non si vede in una schermata: si
   vede solo misurando quanti pixel cambiano fra due scatti.
3. La fusione ha senso finche' la geometria e' UNA. Il giorno che qualcuno
   ricopia la tabella degli anelli dentro l'insegna, i due nuclei tornano due
   e ricominciano a divergere — che e' esattamente il difetto che il turno 3
   e' servito a togliere.

Un test che grep-a del testo e' debole, e va detto: non prova che la regola
FUNZIONI, prova che c'e'. Ma il difetto da cui difende non era «la regola e'
sbagliata», era «la regola non c'e' piu' e nessuno se n'e' accorto», e contro
quello e' esattamente lo strumento giusto. Che poi funzioni lo dice la misura
sullo scatto vero (`docs/acceptance/NUCLEO-TURNO-3.md`), che pero' nessuno
esegue a ogni commit.
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
INSEGNA = RADICE / "ui" / "src" / "desk" / "sfondo.js"
ANELLI = RADICE / "ui" / "src" / "anim" / "rings.js"


class TestIlNucleoFuso:
    def test_la_scala_del_nucleo_e_quella_di_25_5(self) -> None:
        """§25.5, come emendata il 23 agosto 2026 — `docs/acceptance/CANCELLO-25.5.md`.

            riempimento del nucleo   L <= 48   (--cy-900 o piu' scuro)
            tratto a riposo          --cy-700  (L 100)
            anello attivo            --cy-500  (L 181), UNO per volta
            --cy-100                 vietato

        ⚠️ Il pannello di §10.3 non c'entra: disegna la stessa geometria e
        dichiara i propri colori per conto proprio. Questa e' la scala dello
        STRATO DI PRESENZA, che sta dietro il lavoro invece che dentro.

        La regola che questo test tiene in piedi era gia' sparita una volta,
        quando viveva in `presenza.js` e quel file e' stato cancellato: nessun
        test parlava di lei, e il nucleo e' rimasto per giorni col tratto del
        pannello. Il valore cambia, il presidio no.
        """
        css = INSEGNA.read_text(encoding="utf-8")

        def blocco(selettore: str) -> str:
            m = re.search(re.escape(selettore) + r"[^{]*\{([^}]*)\}", css)
            assert m, (
                f"manca del tutto la regola di scope «{selettore}» in "
                "ui/src/desk/sfondo.js. Senza, il nucleo eredita i colori del "
                "pannello, che sono quelli del dato."
            )
            return m.group(1)

        # ① Il tratto a riposo: esattamente il gradino che §25.5 nomina.
        for selettore in (".sfd .pnl-anelli__linea", ".sfd .pnl-anelli__costruzione"):
            b = blocco(selettore)
            assert "stroke: var(--cy-700)" in b, (
                f"«{selettore}» non ha il tratto a --cy-700:\n{b.strip()}\n"
                "§25.5 mette li' il tratto del nucleo a riposo."
            )

        # ② Il riempimento: fino a --cy-700 (L 100) dopo il secondo cancello
        #    del 23 agosto 2026. Sopra non si va: --cy-500 e' dell'anello
        #    attivo, --cy-100 e' del testo dei pannelli.
        AMMESSI = {"--cy-700", "--cy-900", "--bg-void", "--bg-deep",
                   "--bg-panel", "--bg-raised"}
        for prop, valore in re.findall(r"(fill):\s*var\((--[a-z0-9-]+)\)", css):
            assert valore in AMMESSI, (
                f"il nucleo si riempie con {valore}, che sta sopra --cy-700.\n"
                "§25.5, riga «Riempimento del nucleo». Una superficie ha area e "
                f"pesa piu' di un tratto. Ammessi: {sorted(AMMESSI)}."
            )

        # ②bis Una fascia riempita sopra L 48 inverte il proprio dettaglio.
        #      §25.5, riga «Tacche su una fascia riempita sopra L 48».
        #      Senza questa regola le tacche non spariscono in modo dichiarato:
        #      spariscono perche' fill e stroke coincidono, e tornano come
        #      fantasmi al primo che cambia uno dei due.
        m = re.search(r"\[data-chiara\][^{]*__costruzione[^{]*\{([^}]*)\}", css)
        assert m and "stroke: var(--cy-900)" in m.group(1), (
            "manca la regola che inverte il dettaglio sulle fasce chiare "
            "(«[data-chiara] .pnl-anelli__costruzione { stroke: var(--cy-900) }»).\n"
            "Una tacca si legge per contrasto contro il proprio fondo: su un "
            "fondo a --cy-700 va scura, o non si vede affatto."
        )

        # ③ L'anello attivo: --cy-500, che §25.5 ammette a UNA condizione — uno
        #    per volta. La condizione la verifica `npm run verifica:scrivania`
        #    in finestra vera, contando gli anelli in moto; qui si verifica solo
        #    che il colore sia quello dichiarato e non uno piu' alto.
        acceso = blocco(".sfd .pnl-anelli__linea--acceso")
        assert "stroke: var(--cy-500)" in acceso, (
            f"l'anello attivo non e' a --cy-500:\n{acceso.strip()}"
        )

        # ④ --cy-100 resta vietato: e' il livello del testo dei pannelli, e il
        #    dato sta nei pannelli. Si contano gli USI, non le menzioni.
        assert "var(--cy-100)" not in css, (
            "ui/src/desk/sfondo.js usa --cy-100. §25.5 lo vieta anche dopo "
            "l'emendamento del 23 agosto 2026: e' il livello del testo dei "
            "pannelli, e un nucleo che compete col dato e' decorazione."
        )

    def test_gli_anelli_nascono_in_pausa(self) -> None:
        """Invariante 25, e la condizione con cui la deroga 1 si e' sciolta.

        `docs/acceptance/DEROGHE-7dad2b8.md`: «Il turno 3 deve portarsi dietro
        anche il autoplay: false. Se la fusione mantenesse la rotazione
        continua applicandola agli anelli invece che ai punti, avremmo speso un
        turno per cambiare geometria e tenuto il difetto.»
        """
        js = ANELLI.read_text(encoding="utf-8")
        assert "autoplay: false" in js, (
            "ui/src/anim/rings.js non crea piu' le animazioni in pausa. Un "
            "anello che parte da solo e' animazione ambientale, che "
            "l'invariante 25 vieta: gira senza che nessuno stia lavorando."
        )
        i = js.index("export function costruisciDisco")
        j = js.index("export function crea(")
        assert "autoplay: false" in js[i:j], (
            "autoplay: false non sta piu' dentro costruisciDisco(), cioe' nel "
            "pezzo che i due montaggi condividono. Se ci fosse solo nel "
            "pannello, l'insegna partirebbe girando."
        )

    def test_la_geometria_e_UNA_e_l_insegna_la_importa(self) -> None:
        """La fusione: un nucleo solo, due montaggi.

        Se l'insegna ricopiasse la tabella degli anelli, i due nuclei
        tornerebbero due e ricomincerebbero a divergere a ogni modifica.
        """
        js = INSEGNA.read_text(encoding="utf-8")
        assert "costruisciDisco" in js and "../anim/rings.js" in js, (
            "ui/src/desk/sfondo.js non importa piu' la geometria da "
            "ui/src/anim/rings.js: o e' tornata la nuvola, o qualcuno ha "
            "ricopiato gli anelli."
        )
        assert "{ outerR" not in js, (
            "ui/src/desk/sfondo.js contiene una tabella «{ outerR ...», cioe' "
            "una seconda geometria di anelli. Sta in un posto solo: "
            "ui/src/anim/rings.js, funzione costruisciDisco()."
        )
        # ⚠️ E nemmeno i RAGGI si ricopiano. E' la stessa duplicazione, piu'
        # difficile da vedere: cinque numeri che sembrano innocui e che il
        # giorno che outerR cambia restano indietro in silenzio, spostando
        # l'onda su anelli dove non passa piu'. costruisciDisco li torna.
        assert "raggi" in js, (
            "sfondo.js non prende piu' i raggi da costruisciDisco(): se li "
            "ricalcola o li ricopia, invecchiano al primo cambio di outerR."
        )

    def test_le_cause_coprono_i_cinque_anelli(self) -> None:
        """§25.6 assegna una causa per anello, non un cursore fra due estremi.

        Cinque anelli, cinque cause. Se qualcuno ne aggiunge uno senza dargli
        una causa, quell'anello o non si muove mai o si muove senza motivo — e
        la seconda e' invariante 25.
        """
        insegna = INSEGNA.read_text(encoding="utf-8")
        anelli = ANELLI.read_text(encoding="utf-8")
        i = anelli.index("const ANELLI = [")
        j = anelli.index("];", i)
        quanti = anelli[i:j].count("{ outerR")
        k = insegna.index("const CAUSE = [")
        m = insegna.index("];", k)
        cause = insegna[k:m].count("{ chi:")
        assert cause == quanti, (
            f"{quanti} anelli in rings.js ma {cause} cause in sfondo.js. "
            "§25.6 vuole una causa per anello: se gira, sta lavorando."
        )
        # E le soglie di fase sono una per anello, o la scala non si accende.
        s = insegna.index("const SOGLIA_FASE = [")
        e = insegna.index("]", s)
        assert len(insegna[s:e].split(",")) == quanti, (
            "SOGLIA_FASE non ha una voce per anello: la fase accende dal mozzo "
            "verso il bordo e senza una soglia per anello salta un gradino."
        )
