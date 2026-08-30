"""Chi l'ha detto — l'attribuzione al confine della memoria durabile.

Il consolidamento notturno riassumeva gli scambi appiattiti in
`- utente -> jarvis` e ne scriveva un testo solo, in cui una preferenza che il
Signore aveva dichiarato e una che JARVIS aveva proposto erano la stessa riga.

La misura di riferimento (PASB, arXiv 2607.10526): la contaminazione a valle
passa dal **45 % al 71,9 %** quando un'affermazione attraversa quel confine, e
il **33,1 %** degli episodi cancella l'attribuzione. Tradotto: fra sei mesi
JARVIS Le da' ragione su tutto e nessuno se ne accorge, perche' Le da' ragione
su tutto.

⚠️ **Misurato il 30 agosto, e cambia dove va messa la regola.** «Solo
`dichiarato` puo' diventare un fatto fissato» **non morde sul consolidamento**:
`Consolidatore.esegui()` scrive solo in `topics/` e non ha mai toccato
`_fatti-fissati.md`. L'unico che ci scrive e' `MemoryStore.fissa()`, e il suo
unico chiamante e' il tool `pin_fact` — che T1 puo' invocare. **E' li' il
confine**, ed e' esattamente il passaggio che PASB descrive.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from core.memory.attribuzione import (
    SOGLIA,
    Attribuzione,
    classifica,
    intestazione,
    parole,
)
from core.memory.consolidate import Consolidatore
from core.memory.store import MemoryStore


class _Risultato:
    ok = True
    errore = None
    costo_usd = 0.01
    durata_s = 1.0

    def __init__(self, testo="una nota durevole"):
        self.testo = testo


class _T2:
    """Registra che cosa ha visto, per corpus."""

    def __init__(self, testi=None):
        self.visti: dict[str, str] = {}
        self._testi = testi or {}

    async def esegui(self, compito: str, etichetta: str):
        corpus = etichetta.rsplit("-", 1)[-1]
        self.visti[corpus] = compito
        return _Risultato(self._testi.get(corpus, f"nota da {corpus}"))


def _store_con_turni(tmp_path: Path, turni: list[dict], giorno="2026-01-01"):
    s = MemoryStore(tmp_path)
    p = s.sessions / f"{giorno}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for k, t in enumerate(turni):
            f.write(json.dumps({"ts": time.time() - 86400 + k, **t}) + "\n")
    return s


# ── ① il tipo ────────────────────────────────────────────────────────────────


class TestLeTreClassi:
    def test_sono_TRE_e_ognuna_ha_un_produttore(self) -> None:
        """L'elenco e' chiuso, come `Origine` (ADR-011) e `Verdetto` (ADR-012).

        I tre produttori:
          dichiarato            il riassunto del corpus `utente`, e `pin_fact`
                                quando le parole del Signore contengono il fatto
          proposto-e-accettato  il riassunto del corpus `jarvis`
          osservato             l'elenco delle azioni — **nessun modello** — e
                                `pin_fact` quando nessuno dei due l'ha detto
        """
        assert {a.value for a in Attribuzione} == {
            "dichiarato", "proposto-e-accettato", "osservato"
        }

    def test_le_parole_vuote_non_contano(self) -> None:
        assert parole("il gatto e' sul tavolo") == {"gatto", "tavolo"}


class TestLaDeduzione:
    """⚠️ E' **lessicale, quindi debole**, e la soglia e' scelta non misurata.

    Regge per l'asimmetria: da sola puo' solo NEGARE — un `proposto` costa
    l'apertura di un file — mentre per concedere serve ancora la conferma umana
    dell'invariante 3, alla quale si fa vedere la frase esatta.
    """

    TURNI = [
        {"utente": "ho due stampanti 3d in laboratorio", "jarvis": "Vedo, Signore."},
        {"utente": "che ore sono",
         "jarvis": "Le suggerisco di dormire di piu', Signore."},
    ]

    def test_cio_che_ha_detto_il_Signore_e_DICHIARATO(self) -> None:
        classe, prova = classifica("Le stampanti 3D sono due", self.TURNI)
        assert classe is Attribuzione.DICHIARATO
        assert "stampanti" in prova, "la prova cita la frase vera"

    def test_cio_che_ha_proposto_JARVIS_no(self) -> None:
        """**Il silenzio non e' un assenso.** Il Signore non ha obiettato, e non
        e' la stessa cosa di averlo detto."""
        classe, _ = classifica("Il Signore dovrebbe dormire di piu'", self.TURNI)
        assert classe is Attribuzione.PROPOSTO_E_ACCETTATO

    def test_cio_che_non_ha_detto_nessuno_e_OSSERVATO(self) -> None:
        classe, prova = classifica("Roma e' la capitale d'Italia", self.TURNI)
        assert classe is Attribuzione.OSSERVATO
        assert "nessun turno" in prova

    def test_nel_dubbio_il_fatto_e_DEL_SIGNORE(self) -> None:
        """Se compare in entrambi i corpora, l'ha detto lui e JARVIS l'ha
        ripetuto. Attribuirlo a JARVIS perche' ha parlato per ultimo sarebbe la
        cancellazione dell'attribuzione che PASB misura al 33,1 %."""
        turni = [{"utente": "le stampanti sono due",
                  "jarvis": "le stampanti sono due, Signore"}]
        classe, _ = classifica("le stampanti sono due", turni)
        assert classe is Attribuzione.DICHIARATO

    def test_la_prova_c_e_SEMPRE(self) -> None:
        """E' cio' che la conferma mostra: senza, la deduzione sarebbe un
        verdetto senza appello."""
        for fatto in ("Le stampanti sono due", "una cosa mai detta da nessuno"):
            _, prova = classifica(fatto, self.TURNI)
            assert prova.strip()

    def test_la_soglia_e_dichiarata_non_misurata(self) -> None:
        """Il numero e' una scelta. Questo test non lo valida: pinna che sia
        **una sola**, in un posto solo, invece che sparsa nel codice."""
        assert 0.0 < SOGLIA <= 1.0


# ── ② il confine: solo `dichiarato` diventa un fatto fissato ─────────────────


class TestIlConfineDellaMemoriaDurabile:
    def test_dichiarato_entra(self, tmp_path) -> None:
        s = MemoryStore(tmp_path)
        s.fissa("Le stampanti sono due", Attribuzione.DICHIARATO)
        assert s.fatti_fissati() == ["Le stampanti sono due"]

    @pytest.mark.parametrize("classe", [Attribuzione.PROPOSTO_E_ACCETTATO,
                                        Attribuzione.OSSERVATO])
    def test_il_resto_NON_entra(self, tmp_path, classe) -> None:
        s = MemoryStore(tmp_path)
        with pytest.raises(ValueError, match=classe.value):
            s.fissa("Dovrebbe dormire di piu'", classe)
        assert s.fatti_fissati() == [], "il file non e' stato toccato"

    def test_il_rifiuto_dice_la_via_di_scampo(self, tmp_path) -> None:
        """§5.5: i fatti fissati «si correggono aprendo questo file». Una
        persona che vuole fissare una proposta di JARVIS puo' farlo — deve solo
        farlo di persona, non per bocca di JARVIS."""
        s = MemoryStore(tmp_path)
        with pytest.raises(ValueError) as exc:
            s.fissa("x y z", Attribuzione.PROPOSTO_E_ACCETTATO)
        assert "_fatti-fissati.md" in str(exc.value)

    def test_l_attribuzione_e_OBBLIGATORIA(self, tmp_path) -> None:
        """Un default renderebbe la regola vera solo per chi si ricorda di
        passarlo, cioe' falsa. Stessa scelta di `Diario.annota` in ADR-011."""
        with pytest.raises(TypeError):
            MemoryStore(tmp_path).fissa("un fatto")


class TestIlCriterioDellaFetta:
    """«Una sessione in cui JARVIS propone qualcosa e l'utente non obietta
    produce una riga `proposto-e-accettato`, e quella riga **non** entra in
    `_fatti-fissati.md`.»"""

    async def test_il_giro_intero(self, tmp_path) -> None:
        store = _store_con_turni(tmp_path, [
            {"utente": "che ore sono",
             "jarvis": "Le suggerisco di dormire di piu', Signore."},
        ])
        t2 = _T2({"jarvis": "Propone al Signore di dormire di piu'."})
        await Consolidatore(store, t2).esegui(oggi="2026-06-01")

        # ① la riga esiste, ed e' nella sezione giusta
        topic = store.leggi_topic("sessione 2026-01-01")
        assert topic is not None
        assert intestazione(Attribuzione.PROPOSTO_E_ACCETTATO) in topic.contenuto
        assert "dormire" in topic.contenuto

        # ② e NON e' un fatto fissato
        assert store.fatti_fissati() == []
        classe, _ = classifica("Il Signore dovrebbe dormire di piu'",
                               store.turni_di("2026-01-01"))
        with pytest.raises(ValueError):
            store.fissa("Il Signore dovrebbe dormire di piu'", classe)
        assert store.fatti_fissati() == []


# ── ③ la classe viene dalla COSTRUZIONE, non dal modello ─────────────────────


class TestDueRiassuntiNonUno:
    async def test_ogni_corpus_vede_SOLO_le_sue_frasi(self, tmp_path) -> None:
        """E' cio' che rende la classe verificabile invece che dichiarata dal
        modello: la sezione `dichiarato` puo' contenere solo il riassunto di
        frasi che ha detto il Signore, perche' sono le uniche che il modello ha
        visto in quella chiamata. Stessa idea della `fonte` indipendente di
        ADR-012 — chiedere al modello di etichettare da solo sarebbe chiedere a
        chi propone di certificare la propria proposta.
        """
        store = _store_con_turni(tmp_path, [
            {"utente": "PAROLADELSIGNORE", "jarvis": "PAROLADIJARVIS"},
        ])
        t2 = _T2()
        await Consolidatore(store, t2).esegui(oggi="2026-06-01")
        assert "PAROLADELSIGNORE" in t2.visti["utente"]
        assert "PAROLADELSIGNORE" not in t2.visti["jarvis"]
        assert "PAROLADIJARVIS" in t2.visti["jarvis"]
        assert "PAROLADIJARVIS" not in t2.visti["utente"]

    async def test_al_corpus_di_jarvis_si_DICE_che_sono_sue(self, tmp_path) -> None:
        """Senza, il modello le riassumerebbe come se fossero del Signore — che
        e' la cancellazione dell'attribuzione."""
        store = _store_con_turni(tmp_path, [{"utente": "a", "jarvis": "b"}])
        t2 = _T2()
        await Consolidatore(store, t2).esegui(oggi="2026-06-01")
        assert "JARVIS" in t2.visti["jarvis"]
        assert "NON le ha confermate" in t2.visti["jarvis"]

    async def test_le_AZIONI_non_passano_da_nessun_modello(self, tmp_path) -> None:
        """La sezione piu' affidabile delle tre: e' l'elenco dei tool che sono
        girati davvero, non un riassunto di niente."""
        store = _store_con_turni(tmp_path, [
            {"utente": "apri il globo", "jarvis": "Subito.", "azione": "open_panel"},
            {"utente": "e la console", "jarvis": "Fatto.", "azione": "open_panel"},
            {"utente": "alza il volume", "jarvis": "Fatto.", "azione": "set_volume"},
        ])
        t2 = _T2()
        await Consolidatore(store, t2).esegui(oggi="2026-06-01")
        contenuto = store.leggi_topic("sessione 2026-01-01").contenuto
        sezione = contenuto.split(intestazione(Attribuzione.OSSERVATO))[1]
        assert "- open_panel" in sezione and "- set_volume" in sezione
        assert sezione.count("open_panel") == 1, "l'elenco e' un insieme"
        for compito in t2.visti.values():
            assert "open_panel" not in compito, (
                "le azioni non entrano in nessun prompt: non c'e' niente da "
                "riassumere, e farle passare da un modello vorrebbe dire "
                "renderle meno affidabili invece che piu'"
            )

    async def test_una_meta_caduta_NON_scrive_meta_topic(self, tmp_path) -> None:
        """Un topic con la sola sezione `dichiarato` piu' la riga in
        `initiatives/` marcherebbe la sessione come consolidata per sempre — e
        la meta' `proposto-e-accettato` non tornerebbe mai."""
        store = _store_con_turni(tmp_path, [{"utente": "a", "jarvis": "b"}])

        class _MetaCaduta(_T2):
            async def esegui(self, compito, etichetta):
                if etichetta.endswith("-jarvis"):
                    class _No:
                        ok = False
                        testo = ""
                        errore = "il modello non ha risposto"
                        costo_usd = 0.0
                        durata_s = 0.0
                    return _No()
                return await super().esegui(compito, etichetta)

        esito = await Consolidatore(store, _MetaCaduta()).esegui(oggi="2026-06-01")
        assert esito["topic"] == 0
        assert store.elenca_topic() == [], "niente topic a meta'"
        assert store.sessioni_consolidate() == set(), "la sessione si rifa' domani"


# ── ④ additivita': i topic vecchi si leggono ancora ──────────────────────────


class TestICampiSonoADDITIVI:
    def test_un_topic_scritto_PRIMA_si_rilegge(self, tmp_path) -> None:
        s = MemoryStore(tmp_path)
        s.scrivi_topic("sessione vecchia", "un riassunto senza intestazioni")
        t = s.leggi_topic("sessione vecchia")
        assert t is not None and "senza intestazioni" in t.contenuto

    def test_un_file_di_fatti_scritto_PRIMA_si_rilegge(self, tmp_path) -> None:
        """Le righe vecchie non portano l'attribuzione, e `fatti_fissati()`
        continua a restituirle: il campo e' sulla FIRMA, non nel file."""
        s = MemoryStore(tmp_path)
        f = s.topics / "_fatti-fissati.md"
        f.write_text("# Fatti fissati\n\n- Le stampanti sono due\n", encoding="utf-8")
        assert s.fatti_fissati() == ["Le stampanti sono due"]
