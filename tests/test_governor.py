"""ADR-004 — il sistema contava con precisione cio' che NON gli costa.

`core/llm/governor.py` accumulava `total_cost_usd` dagli eventi `result` dello
stream, cioe' l'LLM, che l'abbonamento copre gia'. §24.8 chiama Deepgram «la
sola voce di costo ricorrente del progetto», e i secondi di audio non li
contava nessuno: ne' `seconds`, ne' `fallback`, ne' la riga nel pannello.

⚠️ **Su questa macchina oggi Deepgram non costa niente**: nessuna chiave,
`edge-tts` gratuito — il docstring del Governor lo dice, e la registrazione
della fixture lo conferma (`chiavi_presenti: []`). Il contatore serve
**prima**: accendere il microfono e cominciare a spendere senza saper contare
e' esattamente il difetto per cui ADR-004 esiste, e un mese di consumo non
attribuito non si recupera.

Le prove del Governor sul resto — quota, finestra, sospensione — stanno in
`tests/test_fase4.py`, che e' dove sono nate. Qui c'e' solo ADR-004.
"""

from __future__ import annotations

from core.llm.governor import Governor

# ── ADR-004: i secondi di audio, per provider ────────────────────────────────


class TestIlConsumoVocale:
    """§24.8: «Deepgram e' la sola voce di costo ricorrente del progetto».

    Il sistema misurava con precisione `total_cost_usd` — l'LLM, che
    l'abbonamento copre gia' — e **non misurava l'unica cosa che gli costa**.
    ADR-004 lo chiama cosi': «il sistema conta con precisione cio' che non gli
    costa».

    ⚠️ Su questa macchina oggi non costa niente: nessuna chiave Deepgram,
    `edge-tts` gratuito. Il contatore serve PRIMA — accendere il microfono e
    cominciare a spendere senza saper contare e' il difetto per cui ADR-004
    esiste, e un mese di consumo non attribuito non si recupera.
    """

    def _gov(self, tmp_path):
        return Governor(dir_conso=tmp_path / "conso")

    def test_i_secondi_si_sommano_per_provider(self, tmp_path) -> None:
        g = self._gov(tmp_path)
        g.registra_voce("stt", "deepgram", 12.5)
        g.registra_voce("tts", "deepgram", 3.2)
        g.registra_voce("stt", "whisper", 8.0, fallback=True)
        c = g.consumo_voce_mese()
        assert c["secondi"] == {"deepgram": 15.7, "whisper": 8.0}
        assert c["sessioni"] == 3

    def test_il_RIPIEGO_si_conta_a_parte(self, tmp_path) -> None:
        """Non e' contabilita': e' la misura di quanto Deepgram sia davvero
        affidabile su questa rete. Se i minuti in ripiego sono molti,
        l'invariante 12 sta lavorando parecchio e nessuno lo saprebbe."""
        g = self._gov(tmp_path)
        g.registra_voce("stt", "deepgram", 10.0)
        g.registra_voce("stt", "whisper", 4.0, fallback=True)
        assert g.consumo_voce_mese()["fallback_s"] == 4.0

    def test_l_LLM_non_entra_nel_conto_della_voce(self, tmp_path) -> None:
        """`conso/` e' UN registro: `tier` separa «t2» da «stt»/«tts», e
        sommare i due darebbe secondi di audio che nessuno ha pronunciato."""
        g = self._gov(tmp_path)
        g.registra_risultato("compito", {"total_cost_usd": 0.01, "usage": {}})
        c = g.consumo_voce_mese()
        assert c["secondi"] == {} and c["sessioni"] == 0

    def test_senza_conso_non_esplode(self, tmp_path) -> None:
        """Il Governor si costruisce anche senza cartella — la galleria, un
        test — e chiedere il consumo non deve diventare un ramo che cade."""
        assert Governor().consumo_voce_mese() == {
            "secondi": {}, "fallback_s": 0.0, "sessioni": 0}

    def test_il_MESE_e_non_il_giorno(self, tmp_path) -> None:
        """E' l'unita' con cui Deepgram fattura. Un file di un altro mese non
        deve entrare nel totale di questo."""
        import json
        import time
        d = tmp_path / "conso"
        d.mkdir(parents=True)
        vecchio = time.strftime("%Y-%m", time.localtime(time.time() - 60 * 60 * 24 * 60))
        (d / f"{vecchio}-01.jsonl").write_text(json.dumps({
            "tier": "stt", "provider": "deepgram", "durata_s": 999.0,
            "fallback": False}) + "\n", encoding="utf-8")
        g = Governor(dir_conso=d)
        g.registra_voce("stt", "deepgram", 1.0)
        assert g.consumo_voce_mese()["secondi"] == {"deepgram": 1.0}

    def test_una_riga_rotta_non_ferma_il_conto(self, tmp_path) -> None:
        """Il log si scrive in append da un processo che puo' morire a meta'
        riga. Una riga tronca non deve azzerare un mese di misura."""
        import json
        import time
        d = tmp_path / "conso"
        d.mkdir(parents=True)
        oggi = time.strftime("%Y-%m-%d")
        (d / f"{oggi}.jsonl").write_text(
            '{"tier": "stt", "provider": "deepgram", "durata_s": 5.0}\n'
            '{"tier": "stt", "prov\n'
            + json.dumps({"tier": "tts", "provider": "deepgram",
                          "durata_s": 2.0}) + "\n", encoding="utf-8")
        assert Governor(dir_conso=d).consumo_voce_mese()["secondi"] == {"deepgram": 7.0}
