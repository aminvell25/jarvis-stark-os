"""EVAL — quanto JARVIS resta se' stesso.

## Perche' questo file NON spende

Ci sono quasi duemila test sul codice e zero sul comportamento. Le dodici sonde
della persona hanno pero' bisogno di un modello vero: dodici turni su T1 con la
persona iniettata, piu' altrettanti giudizi. **Un test che spende non e' un
test** — la regola l'ha stabilita `scripts/banco_haiku.py`, e questo file la
segue.

Chi spende e' `scripts/termometro.py --persona`, una volta. Qui si rilegge
`docs/acceptance/TERMOMETRO.json` a costo zero, e si controlla che sia una
misura e non un residuo.

## Che cosa si controlla, e che cosa NON si controlla

⚠️ **Nessuna soglia**, e non e' una dimenticanza. Il criterio della fetta dice:
«non serve che il numero sia buono, serve che esista, perche' oggi non c'e'
niente da confrontare». Una soglia scelta oggi sarebbe un numero inventato che
fra un mese qualcuno prenderebbe per una misura — lo stesso difetto che
`STATO-DEI-PIANI` documenta sull'entropia 2,40, che «fa il cancello e
l'obiettivo insieme, cioe' non misura».

Si controlla invece la cosa che rende il numero **leggibile fra sei mesi**: che
le regole citate dalle sonde esistano ancora, alla lettera, in
`config/voice-persona.md`. Una misura contro una regola che nel frattempo e'
cambiata non e' una misura vecchia: e' una misura di un'altra cosa.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
ESITO = RADICE / "docs" / "acceptance" / "TERMOMETRO.json"
PERSONA = RADICE / "config" / "voice-persona.md"


@pytest.fixture(scope="module")
def termometro() -> dict:
    if not ESITO.exists():
        pytest.skip("TERMOMETRO.json non c'e': "
                    "`uv run python scripts/termometro.py --persona`")
    return json.loads(ESITO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def persona(termometro: dict) -> dict:
    p = termometro.get("persona")
    if not p:
        pytest.skip("nessuna lettura della persona: gira con `--persona`")
    return p


class TestLaMisuraEsiste:
    """Il criterio della fetta, alla lettera."""

    def test_ha_una_data(self, termometro: dict) -> None:
        """Una misura senza data non si confronta con niente, ed e' proprio il
        confronto la ragione per cui questo banco esiste."""
        assert termometro.get("data")

    def test_dodici_sonde(self, persona: dict) -> None:
        assert persona["sonde"] == 12
        assert len(persona["dettaglio"]) == 12

    def test_i_due_giudici_hanno_ENTRAMBI_un_numero(self, persona: dict) -> None:
        """⚠️ **Due giudici, e non e' ridondanza.** Il meccanico e' riproducibile
        e non e' un LLM; il modello copre piaggeria e dissenso, che
        meccanicamente non si vedono. Dove i due discordano, il disaccordo e'
        un dato salvato — ed e' il piu' vicino a una «fonte indipendente»
        (ADR-012) che questa misura possa avere."""
        for chi in ("meccanico", "modello"):
            assert 0 <= persona[chi]["passate"] <= persona[chi]["su"]
        assert persona["meccanico"]["su"] == 12

    def test_le_risposte_grezze_ci_sono_TUTTE(self, persona: dict) -> None:
        """Le sonde che nessuna delle due rubriche copre bene le deve poter
        rileggere una persona. `banco_haiku` salva le risposte grezze per la
        stessa ragione."""
        for s in persona["dettaglio"]:
            assert s["risposta"].strip(), s["nome"]
            assert s["regola"].strip(), s["nome"]


class TestLaMisuraEANCORAdiQUESTAPersona:
    """La riga che rende il numero leggibile fra sei mesi."""

    def test_ogni_regola_citata_esiste_nel_file_della_persona(
        self, persona: dict
    ) -> None:
        """⚠️ **Le sonde citano la persona alla lettera, non la parafrasano.**
        Se `config/voice-persona.md` cambia, la citazione diventa falsa e il
        numero misura una regola che non c'e' piu'. Questo test lo scopre.

        Si confrontano i pezzi fra virgolette basse, che sono le citazioni
        vere; il resto della stringa e' l'etichetta della sezione (TONO, VOCE,
        LIMITI), che serve a chi legge e non al confronto.
        """
        import re
        import unicodedata

        testo = PERSONA.read_text(encoding="utf-8")

        def normale(x: str) -> str:
            """Solo le lettere, minuscole, senza accenti.

            ⚠️ **Gli accenti si piegano, e la ragione e' una convenzione del
            repository**: `config/voice-persona.md` e' prosa per un modello e
            porta gli accenti veri — «ciò», «è» — mentre il codice di `core/` e
            di `scripts/` scrive `cio'` e `e'` in ASCII, ovunque. Le sonde
            stanno nel codice e seguono il codice.

            Confrontare le due grafie alla lettera fa fallire questo controllo
            per una differenza tipografica invece che per una regola cambiata:
            misurato, tre citazioni su dodici. E' un rosso che si impara a
            ignorare, cioe' il modo in cui una guardia muore.

            Anche gli a capo si piegano: il file va a capo a settanta colonne,
            le citazioni no.
            """
            piatta = unicodedata.normalize("NFKD", x.replace("'", "'"))
            senza_accenti = "".join(c for c in piatta
                                    if not unicodedata.combining(c))
            return re.sub(r"[^\w]+", " ", senza_accenti).lower().strip()

        piatto = normale(testo)
        mancanti = []
        for s in persona["dettaglio"]:
            for citazione in re.findall(r"«([^»]+)»", s["regola"]):
                if normale(citazione) not in piatto:
                    mancanti.append((s["nome"], citazione[:60]))
        assert not mancanti, (
            "queste regole non stanno piu' in config/voice-persona.md, quindi "
            "il numero misura qualcosa che non e' piu' la persona:\n"
            + "\n".join(f"  {n}: «{c}…»" for n, c in mancanti)
        )


class TestIlTermometroDiceQualcosa:
    """⚠️ Nessuna soglia. Si legge il numero e si pinna che sia leggibile."""

    def test_le_sonde_bocciate_sono_NOMINATE(self, persona: dict) -> None:
        """Un banco che dice «11 su 12» e non dice quale e' un banco che non
        serve a riparare niente."""
        bocciate = [s["nome"] for s in persona["dettaglio"] if not s["meccanico"]]
        assert len(bocciate) == 12 - persona["meccanico"]["passate"]

    def test_i_disaccordi_sono_registrati(self, persona: dict) -> None:
        """Il disaccordo fra i due giudici e' il dato piu' informativo del
        banco: al primo giro ne ha prodotti due, e in **entrambi** aveva
        ragione il modello — la rubrica meccanica copriva meta' regola. Uno
        e' stato completato, l'altro dichiarato non meccanizzabile."""
        assert "discordi" in persona
        assert isinstance(persona["discordi"], list)
        for nome in persona["discordi"]:
            assert nome in {s["nome"] for s in persona["dettaglio"]}
